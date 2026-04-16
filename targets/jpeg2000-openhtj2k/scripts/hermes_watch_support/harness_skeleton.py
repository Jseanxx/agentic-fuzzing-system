from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable

from .harness_evaluation import build_harness_evaluation_draft, write_harness_evaluation_draft
from .harness_probe import _build_probe_command, _find_seed_candidates, _smoke_probe_command, _probe_status
from .profile_loading import load_target_profile, resolve_target_profile_path
from .profile_summary import build_target_profile_summary
from .target_adapter import get_target_adapter
from .llm_evidence import write_llm_evidence_packet

ProbeRunner = Callable[[list[str], Path], tuple[int, str]]


def _load_json(path: Path, default: dict[str, object]) -> dict[str, object]:
    if not path.exists():
        return dict(default)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(default)
    if not isinstance(data, dict):
        return dict(default)
    merged = dict(default)
    merged.update(data)
    return merged


def _latest_file(path: Path, pattern: str) -> Path | None:
    files = sorted(path.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-") or "target"


def _latest_feedback(repo_root: Path) -> dict[str, object] | None:
    feedback_dir = repo_root / "fuzz-records" / "probe-feedback"
    feedback_path = _latest_file(feedback_dir, "*-probe-feedback.json")
    if feedback_path is None:
        return None
    feedback = _load_json(feedback_path, {})
    return feedback if feedback else None


def _latest_skeleton_closure(repo_root: Path, candidate_id: str | None) -> dict[str, object] | None:
    if not candidate_id:
        return None
    closure_dir = repo_root / "fuzz-records" / "harness-skeleton-probes"
    closure_path = _latest_file(closure_dir, f"*-{candidate_id}-harness-skeleton-probe.json")
    if closure_path is None:
        return None
    closure = _load_json(closure_path, {})
    if str(closure.get("selected_candidate_id") or "") != str(candidate_id):
        return None
    return closure if closure else None


def _load_ranked_candidates(repo_root: Path) -> list[dict[str, object]]:
    registry_path = repo_root / "fuzz-records" / "harness-candidates" / "ranked-candidates.json"
    registry = _load_json(registry_path, {"candidates": []})
    candidates = registry.get("candidates") if isinstance(registry.get("candidates"), list) else []
    return [candidate for candidate in candidates if isinstance(candidate, dict)]


def _select_candidate(
    repo_root: Path,
    evaluation: dict[str, object],
    feedback: dict[str, object] | None,
) -> dict[str, object]:
    candidates = _load_ranked_candidates(repo_root)
    feedback_candidate_id = str((feedback or {}).get("candidate_id") or "")
    if feedback_candidate_id:
        matched = next((item for item in candidates if str(item.get("candidate_id") or "") == feedback_candidate_id), None)
        if matched is not None:
            return matched
    if candidates:
        candidates.sort(
            key=lambda item: (
                -int(item.get("effective_score") or item.get("score") or 0),
                -int(item.get("score") or 0),
                str(item.get("candidate_id") or ""),
            )
        )
        return candidates[0]
    evaluations = evaluation.get("evaluations") if isinstance(evaluation.get("evaluations"), list) else []
    selected = evaluations[0] if evaluations and isinstance(evaluations[0], dict) else {}
    return dict(selected)


def _latest_candidate_skeleton(repo_root: Path, candidate_id: str | None) -> dict[str, object] | None:
    if not candidate_id:
        return None
    skeleton_dir = repo_root / "fuzz-records" / "harness-skeletons"
    skeleton_path = _latest_file(skeleton_dir, f"*-{candidate_id}-harness-skeleton.json")
    if skeleton_path is None:
        return None
    skeleton = _load_json(skeleton_path, {})
    return skeleton if skeleton else None


def _skeleton_filename(project: str, candidate_id: str, extension: str) -> str:
    return f"{_slugify(project)}-{candidate_id}-harness-skeleton{extension}"


def _source_extension(entrypoint_path: str | None) -> str:
    suffix = Path(str(entrypoint_path or "")).suffix.lower()
    return ".c" if suffix == ".c" else ".cpp"


def _mode_label(mode: str | None) -> str:
    value = str(mode or "exploratory-auto-draft")
    if value == "parse":
        return "parse-oriented"
    if value == "decode":
        return "decode-oriented"
    if value == "deep-decode":
        return "deep-decode-oriented"
    return value


def _entry_symbol_hint(entrypoint_path: str | None) -> str:
    stem = Path(str(entrypoint_path or "entrypoint")).stem
    hint = re.sub(r"[^A-Za-z0-9_]+", "_", stem).strip("_")
    return hint or "target_entrypoint"


def _resolve_target_adapter(repo_root: Path):
    profile_path = resolve_target_profile_path(repo_root, None)
    if profile_path is None:
        return None
    profile = load_target_profile(profile_path)
    profile_summary = build_target_profile_summary(profile, profile_path)
    return get_target_adapter(profile_summary)


def _skeleton_entrypoint_name(repo_root: Path) -> str:
    target_adapter = _resolve_target_adapter(repo_root)
    if target_adapter and target_adapter.fuzz_entrypoint_names:
        return str(target_adapter.fuzz_entrypoint_names[0])
    return "LLVMFuzzerTestOneInput"


def _skeleton_guard_contract(repo_root: Path) -> tuple[str, str]:
    target_adapter = _resolve_target_adapter(repo_root)
    if target_adapter:
        return str(target_adapter.guard_condition), str(target_adapter.guard_return_statement)
    return "size < 4", "return 0;"


def _skeleton_call_contract(repo_root: Path) -> tuple[str, str]:
    target_adapter = _resolve_target_adapter(repo_root)
    if target_adapter:
        return str(target_adapter.target_call_todo), str(target_adapter.resource_lifetime_hint)
    return (
        "wire target entrypoint call before stage promotion",
        "borrow the fuzz input only for the current call; avoid retaining pointers or ownership across iterations",
    )


def _build_revision_loop(candidate: dict[str, object], feedback: dict[str, object] | None, *, draft_kind: str) -> list[str]:
    bridge_reason = str((feedback or {}).get("bridge_reason") or candidate.get("last_feedback_reason") or "")
    action_code = str((feedback or {}).get("action_code") or candidate.get("last_feedback_action") or "")
    steps = [
        "Record the exact build and smoke command assumptions beside the skeleton before trying to compile it.",
        "Keep the first harness body minimal: parse one input and exit cleanly on unsupported conditions.",
    ]
    if draft_kind == "revision":
        steps.append("Diff this revision against the previous skeleton and preserve only the smallest safe change set.")
    if "build" in bridge_reason or action_code == "halt_and_review_harness":
        steps.append("Re-check include paths, target linkage, and harness entrypoint naming before the next build attempt.")
    if "smoke" in bridge_reason:
        steps.append("Re-run the smoke seed under sanitizers and adjust the input gating logic before enabling loops or persistent mode.")
    if action_code == "minimize_and_reseed":
        steps.append("Refresh the baseline seed selection and keep the harness logic unchanged until a valid seed is confirmed.")
    if not any("smoke" in step.lower() for step in steps):
        steps.append("After build success, run one known-good smoke seed and only then consider deeper mode-specific revision.")
    return steps


def _build_revision_intelligence(
    candidate: dict[str, object],
    feedback: dict[str, object] | None,
    *,
    closure: dict[str, object] | None = None,
) -> dict[str, object]:
    feedback = feedback or {}
    closure = closure or {}
    if closure:
        build_status = str(closure.get("build_probe_status") or feedback.get("build_probe_status") or "unknown")
        smoke_status = str(closure.get("smoke_probe_status") or feedback.get("smoke_probe_status") or "unknown")
        signal_source = "skeleton-closure"
    else:
        build_status = str(feedback.get("build_probe_status") or "unknown")
        smoke_status = str(feedback.get("smoke_probe_status") or "unknown")
        signal_source = "probe-feedback" if feedback else "heuristic"
    candidate_status = str(candidate.get("status") or "")
    signals: list[str] = []
    if build_status != "unknown":
        signals.append(f"build:{build_status}")
    if smoke_status != "unknown":
        signals.append(f"smoke:{smoke_status}")
    if candidate_status:
        signals.append(f"candidate-status:{candidate_status}")

    priority = "low"
    focus = "confidence-raise"
    summary = "No hard failure was observed; keep the next revision conservative and evidence-seeking."
    if build_status == "failed":
        priority = "high"
        focus = "build-fix"
        summary = "Latest probe failed in the build step; revise compile/link assumptions before changing harness depth."
    elif smoke_status == "failed":
        priority = "high"
        focus = "smoke-fix"
        summary = "Latest probe built but failed in smoke execution; revise input gating and smoke-path assumptions first."
    elif smoke_status == "skipped":
        priority = "medium"
        focus = "smoke-enable"
        summary = "Smoke execution did not complete; enable a valid seed or smoke path before deeper harness changes."
    elif build_status == "passed" and smoke_status == "passed":
        priority = "medium"
        focus = "confidence-raise"
        summary = "Latest probe passed build and smoke; next revision can safely improve target reach or observability."

    return {
        "build_probe_status": build_status,
        "smoke_probe_status": smoke_status,
        "revision_priority": priority,
        "next_revision_focus": focus,
        "revision_signals": signals,
        "revision_summary": summary,
        "revision_signal_source": signal_source,
    }


def _build_correction_suggestions(draft: dict[str, object]) -> list[dict[str, str]]:
    focus = str(draft.get("next_revision_focus") or "confidence-raise")
    entrypoint = str(draft.get("entrypoint_path") or "unknown-entrypoint")
    suggestions: list[dict[str, str]] = []
    if focus == "build-fix":
        suggestions.extend(
            [
                {
                    "title": "Verify include/link boundary",
                    "rationale": f"The last closure failed before smoke; verify include and link assumptions for `{entrypoint}`.",
                    "suggested_change": "Add a BUILD-FIX comment near the includes and confirm the target symbol and compilation unit match the expected language/toolchain.",
                },
                {
                    "title": "Keep target call stubbed until compile assumptions are proven",
                    "rationale": "Do not widen harness behavior while the file may not build or link cleanly.",
                    "suggested_change": "Preserve the minimal input gate and add a TODO describing the exact header/library binding still missing.",
                },
            ]
        )
    elif focus == "smoke-fix":
        suggestions.extend(
            [
                {
                    "title": "Tighten input gating",
                    "rationale": f"The skeleton built but failed in smoke execution for `{entrypoint}`.",
                    "suggested_change": "Insert an early-return guard for undersized/invalid seed inputs before the target call placeholder.",
                },
                {
                    "title": "Isolate the first target touchpoint",
                    "rationale": "Smoke failure suggests the first call path needs stronger preconditions or a smaller step.",
                    "suggested_change": "Split the future target call into a tiny helper stub and document the exact seed assumptions around it.",
                },
            ]
        )
    elif focus == "smoke-enable":
        suggestions.append(
            {
                "title": "Enable a reproducible smoke seed",
                "rationale": "Without a usable smoke run, deeper harness correction is premature.",
                "suggested_change": "Add a seed-selection TODO and keep the harness body unchanged until one valid seed path is confirmed.",
            }
        )
    else:
        suggestions.append(
            {
                "title": "Raise confidence conservatively",
                "rationale": "Current evidence is not failing; prefer tiny, reviewable improvements over aggressive target wiring.",
                "suggested_change": "Add one small observability or stage-reaching TODO without changing the minimal safety gate.",
            }
        )
    return suggestions


def _render_skeleton_code(
    *,
    entrypoint_path: str | None,
    candidate_id: str,
    recommended_mode: str | None,
    target_stage: str | None,
    draft_kind: str,
    revision_number: int,
    extension: str,
    skeleton_entrypoint_name: str = "LLVMFuzzerTestOneInput",
    guard_condition: str = "size < 4",
    guard_return_statement: str = "return 0;",
    target_call_todo: str = "wire target entrypoint call before stage promotion",
    resource_lifetime_hint: str = "borrow the fuzz input only for the current call; avoid retaining pointers or ownership across iterations",
) -> str:
    mode_label = _mode_label(recommended_mode)
    entry_symbol_hint = _entry_symbol_hint(entrypoint_path)
    comment_prefix = "//" if extension == ".cpp" else "//"
    normalized_guard_condition = guard_condition.strip()
    normalized_guard_return = guard_return_statement.strip()
    if extension == ".c":
        return "\n".join(
            [
                f"{comment_prefix} Auto-generated Hermes harness skeleton draft",
                f"{comment_prefix} candidate_id: {candidate_id}",
                f"{comment_prefix} entrypoint_path: {entrypoint_path}",
                f"{comment_prefix} recommended_mode: {recommended_mode}",
                f"{comment_prefix} target_stage: {target_stage}",
                f"{comment_prefix} draft_kind: {draft_kind}",
                f"{comment_prefix} revision_number: {revision_number}",
                "#include <stddef.h>",
                "#include <stdint.h>",
                "",
                f"int {skeleton_entrypoint_name}(const uint8_t *data, size_t size) {{",
                "  if (data == NULL) {",
                f"    {normalized_guard_return}",
                "  }",
                f"  if ({normalized_guard_condition}) {{",
                f"    {normalized_guard_return}",
                "  }",
                f"  /* TODO: {target_call_todo}. */",
                f"  /* Lifetime hint: {resource_lifetime_hint}. */",
                f"  /* Target binding hint: {entry_symbol_hint} from {entrypoint_path} ({mode_label}). */",
                "  return 0;",
                "}",
                "",
            ]
        )
    return "\n".join(
        [
            f"{comment_prefix} Auto-generated Hermes harness skeleton draft",
            f"{comment_prefix} candidate_id: {candidate_id}",
            f"{comment_prefix} entrypoint_path: {entrypoint_path}",
            f"{comment_prefix} recommended_mode: {recommended_mode}",
            f"{comment_prefix} target_stage: {target_stage}",
            f"{comment_prefix} draft_kind: {draft_kind}",
            f"{comment_prefix} revision_number: {revision_number}",
            "#include <cstddef>",
            "#include <cstdint>",
            "",
            f"extern \"C\" int {skeleton_entrypoint_name}(const std::uint8_t* data, std::size_t size) {{",
            "  if (data == nullptr) {",
            f"    {normalized_guard_return}",
            "  }",
            f"  if ({normalized_guard_condition}) {{",
            f"    {normalized_guard_return}",
            "  }",
            f"  // TODO: {target_call_todo}.",
            f"  // Lifetime hint: {resource_lifetime_hint}.",
            f"  // Target binding hint: {entry_symbol_hint} from {entrypoint_path} ({mode_label}).",
            "  return 0;",
            "}",
            "",
        ]
    )


def build_harness_skeleton_draft(repo_root: Path) -> dict[str, object]:
    evaluation = build_harness_evaluation_draft(repo_root)
    feedback = _latest_feedback(repo_root)
    candidate = _select_candidate(repo_root, evaluation, feedback)
    project = str(evaluation.get("generated_from_project") or repo_root.name)
    candidate_id = str(candidate.get("candidate_id") or "candidate-1")
    entrypoint_path = candidate.get("entrypoint_path")
    recommended_mode = candidate.get("recommended_mode")
    target_stage = candidate.get("target_stage")
    previous = _latest_candidate_skeleton(repo_root, candidate_id)
    latest_closure = _latest_skeleton_closure(repo_root, candidate_id)
    action_code = str((feedback or {}).get("action_code") or "")
    draft_kind = "revision" if previous and action_code in {"halt_and_review_harness", "minimize_and_reseed"} else "initial"
    revision_number = int((previous or {}).get("revision_number") or 0) + 1 if previous else 1
    extension = _source_extension(str(entrypoint_path) if entrypoint_path else None)
    skeleton_entrypoint_name = _skeleton_entrypoint_name(repo_root)
    guard_condition, guard_return_statement = _skeleton_guard_contract(repo_root)
    target_call_todo, resource_lifetime_hint = _skeleton_call_contract(repo_root)
    skeleton_code = _render_skeleton_code(
        entrypoint_path=str(entrypoint_path) if entrypoint_path else None,
        candidate_id=candidate_id,
        recommended_mode=str(recommended_mode) if recommended_mode else None,
        target_stage=str(target_stage) if target_stage else None,
        draft_kind=draft_kind,
        revision_number=revision_number,
        extension=extension,
        skeleton_entrypoint_name=skeleton_entrypoint_name,
        guard_condition=guard_condition,
        guard_return_statement=guard_return_statement,
        target_call_todo=target_call_todo,
        resource_lifetime_hint=resource_lifetime_hint,
    )
    revision_loop = _build_revision_loop(candidate, feedback, draft_kind=draft_kind)
    intelligence = _build_revision_intelligence(candidate, feedback, closure=latest_closure)
    focus = str(intelligence.get("next_revision_focus") or "")
    if focus == "build-fix":
        revision_loop.insert(0, "Prioritize compile/link repairs before modifying harness behavior or target depth.")
    elif focus == "smoke-fix":
        revision_loop.insert(0, "Prioritize smoke-path repairs before expanding loops, persistence, or deeper target stages.")
    elif focus == "smoke-enable":
        revision_loop.insert(0, "Prioritize enabling a reproducible smoke run with one valid seed before revising harness depth.")
    elif focus == "confidence-raise":
        revision_loop.insert(0, "Build and smoke look viable; use the next revision to raise confidence with small stage-reaching improvements.")
    correction_suggestions = _build_correction_suggestions(
        {
            "entrypoint_path": entrypoint_path,
            "next_revision_focus": intelligence.get("next_revision_focus"),
        }
    )
    return {
        "generated_from_project": project,
        "selected_candidate_id": candidate_id,
        "entrypoint_path": entrypoint_path,
        "recommended_mode": recommended_mode,
        "target_stage": target_stage,
        "draft_kind": draft_kind,
        "revision_number": revision_number,
        "bridge_action_code": action_code or None,
        "bridge_reason": (feedback or {}).get("bridge_reason"),
        "build_probe_status": intelligence.get("build_probe_status"),
        "smoke_probe_status": intelligence.get("smoke_probe_status"),
        "revision_priority": intelligence.get("revision_priority"),
        "next_revision_focus": intelligence.get("next_revision_focus"),
        "revision_signals": intelligence.get("revision_signals"),
        "revision_summary": intelligence.get("revision_summary"),
        "revision_signal_source": intelligence.get("revision_signal_source"),
        "correction_strategy": intelligence.get("next_revision_focus"),
        "correction_suggestions": correction_suggestions,
        "skeleton_language": "c" if extension == ".c" else "c++",
        "skeleton_extension": extension,
        "skeleton_entrypoint_name": skeleton_entrypoint_name,
        "skeleton_guard_condition": guard_condition,
        "skeleton_guard_return_statement": guard_return_statement,
        "skeleton_target_call_todo": target_call_todo,
        "skeleton_resource_lifetime_hint": resource_lifetime_hint,
        "skeleton_basename": _skeleton_filename(project, candidate_id, extension),
        "revision_loop": revision_loop,
        "skeleton_code": skeleton_code,
        "selected_candidate": candidate,
        "latest_skeleton_closure": latest_closure,
        "evaluation": evaluation,
    }


def render_harness_skeleton_markdown(draft: dict[str, object], *, skeleton_source_path: str | None = None) -> str:
    lines = [
        "# Harness Skeleton Draft",
        "",
        f"- project: {draft.get('generated_from_project')}",
        f"- selected_candidate_id: {draft.get('selected_candidate_id')}",
        f"- entrypoint_path: {draft.get('entrypoint_path')}",
        f"- recommended_mode: {draft.get('recommended_mode')}",
        f"- target_stage: {draft.get('target_stage')}",
        f"- draft_kind: {draft.get('draft_kind')}",
        f"- revision_number: {draft.get('revision_number')}",
        f"- bridge_action_code: {draft.get('bridge_action_code')}",
        f"- bridge_reason: {draft.get('bridge_reason')}",
        f"- build_probe_status: {draft.get('build_probe_status')}",
        f"- smoke_probe_status: {draft.get('smoke_probe_status')}",
        f"- revision_priority: {draft.get('revision_priority')}",
        f"- next_revision_focus: {draft.get('next_revision_focus')}",
        f"- revision_signal_source: {draft.get('revision_signal_source')}",
        f"- correction_strategy: {draft.get('correction_strategy')}",
        f"- skeleton_entrypoint_name: {draft.get('skeleton_entrypoint_name')}",
        f"- skeleton_guard_condition: {draft.get('skeleton_guard_condition')}",
        f"- skeleton_guard_return_statement: {draft.get('skeleton_guard_return_statement')}",
        f"- skeleton_target_call_todo: {draft.get('skeleton_target_call_todo')}",
        f"- skeleton_resource_lifetime_hint: {draft.get('skeleton_resource_lifetime_hint')}",
        f"- skeleton_source_path: {skeleton_source_path}",
        "",
        "## Revision Intelligence",
        "",
        f"- revision_summary: {draft.get('revision_summary')}",
        "- revision_signals:",
    ]
    for signal in draft.get("revision_signals") or []:
        lines.append(f"  - {signal}")
    lines.extend(
        [
            "",
            "## Patch Suggestions",
            "",
        ]
    )
    for suggestion in draft.get("correction_suggestions") or []:
        if not isinstance(suggestion, dict):
            continue
        lines.append(f"- title: {suggestion.get('title')}")
        lines.append(f"  - rationale: {suggestion.get('rationale')}")
        lines.append(f"  - suggested_change: {suggestion.get('suggested_change')}")
    lines.extend(
        [
            "",
            "## Revision Loop",
            "",
        ]
    )
    for step in draft.get("revision_loop") or []:
        lines.append(f"- {step}")
    lines.extend(
        [
            "",
            "## Stub Policy",
            "",
            "- Keep this as a draft harness skeleton until build and smoke feedback prove the wiring is safe.",
            "- Prefer the smallest reversible change for each revision.",
            "- Treat every failed smoke or build attempt as evidence for the next revision note.",
            "",
            "## Skeleton Preview",
            "",
            "```",
            str(draft.get("skeleton_code") or "").rstrip(),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def write_harness_skeleton_draft(repo_root: Path) -> dict[str, object]:
    evaluation_result = write_harness_evaluation_draft(repo_root)
    draft = build_harness_skeleton_draft(repo_root)
    out_dir = repo_root / "fuzz-records" / "harness-skeletons"
    out_dir.mkdir(parents=True, exist_ok=True)
    project = str(draft.get("generated_from_project") or repo_root.name)
    candidate_id = str(draft.get("selected_candidate_id") or "candidate-1")
    extension = str(draft.get("skeleton_extension") or ".cpp")
    stem = _skeleton_filename(project, candidate_id, "")
    manifest_path = out_dir / f"{stem}.json"
    plan_path = out_dir / f"{stem}.md"
    source_path = out_dir / f"{stem}{extension}"
    correction_json_path = out_dir / f"{stem}-correction-draft.json"
    correction_md_path = out_dir / f"{stem}-correction-draft.md"
    source_path.write_text(str(draft.get("skeleton_code") or ""), encoding="utf-8")
    correction_payload = {
        "generated_from_project": project,
        "selected_candidate_id": candidate_id,
        "target_file_path": str(source_path),
        "correction_strategy": draft.get("correction_strategy"),
        "correction_suggestions": draft.get("correction_suggestions"),
        "revision_signal_source": draft.get("revision_signal_source"),
        "next_revision_focus": draft.get("next_revision_focus"),
    }
    correction_json_path.write_text(json.dumps(correction_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    correction_lines = [
        "# Harness Skeleton Correction Draft",
        "",
        f"- project: {project}",
        f"- selected_candidate_id: {candidate_id}",
        f"- target_file_path: {source_path}",
        f"- correction_strategy: {draft.get('correction_strategy')}",
        f"- revision_signal_source: {draft.get('revision_signal_source')}",
        "",
        "## Suggestions",
        "",
    ]
    for suggestion in draft.get("correction_suggestions") or []:
        if not isinstance(suggestion, dict):
            continue
        correction_lines.append(f"- title: {suggestion.get('title')}")
        correction_lines.append(f"  - rationale: {suggestion.get('rationale')}")
        correction_lines.append(f"  - suggested_change: {suggestion.get('suggested_change')}")
    correction_lines.append("")
    correction_md_path.write_text("\n".join(correction_lines), encoding="utf-8")
    manifest_payload = {
        **draft,
        "evaluation_manifest_path": evaluation_result.get("evaluation_manifest_path"),
        "evaluation_plan_path": evaluation_result.get("evaluation_plan_path"),
        "skeleton_source_path": str(source_path),
        "correction_draft_json_path": str(correction_json_path),
        "correction_draft_markdown_path": str(correction_md_path),
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    plan_path.write_text(render_harness_skeleton_markdown(draft, skeleton_source_path=str(source_path)), encoding="utf-8")
    return {
        "generated_from_project": draft.get("generated_from_project"),
        "selected_candidate_id": draft.get("selected_candidate_id"),
        "draft_kind": draft.get("draft_kind"),
        "revision_number": draft.get("revision_number"),
        "skeleton_manifest_path": str(manifest_path),
        "skeleton_plan_path": str(plan_path),
        "skeleton_source_path": str(source_path),
        "correction_draft_json_path": str(correction_json_path),
        "correction_draft_markdown_path": str(correction_md_path),
        "evaluation_manifest_path": str(evaluation_result.get("evaluation_manifest_path")),
        "evaluation_plan_path": str(evaluation_result.get("evaluation_plan_path")),
    }


def render_harness_skeleton_closure_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Harness Skeleton Closure Probe",
        "",
        f"- project: {payload.get('generated_from_project')}",
        f"- selected_candidate_id: {payload.get('selected_candidate_id')}",
        f"- entrypoint_path: {payload.get('entrypoint_path')}",
        f"- skeleton_source_path: {payload.get('skeleton_source_path')}",
        f"- build_probe_status: {payload.get('build_probe_status')}",
        f"- smoke_probe_status: {payload.get('smoke_probe_status')}",
        "",
        "## Revision Closure Meaning",
        "",
        "- This probe ties the latest skeleton artifact to real build/smoke evidence.",
        "- Use failed build/smoke status as stronger revision input than older advisory-only feedback.",
        "",
    ]
    return "\n".join(lines)


def _latest_correction_draft(repo_root: Path, candidate_id: str | None) -> dict[str, object] | None:
    if not candidate_id:
        return None
    draft_dir = repo_root / "fuzz-records" / "harness-skeletons"
    draft_path = _latest_file(draft_dir, f"*-{candidate_id}-harness-skeleton-correction-draft.json")
    if draft_path is None:
        return None
    draft = _load_json(draft_path, {})
    if str(draft.get("selected_candidate_id") or "") != str(candidate_id):
        return None
    draft["correction_draft_json_path"] = str(draft_path)
    markdown_path = draft_path.with_suffix(".md")
    if markdown_path.exists():
        draft["correction_draft_markdown_path"] = str(markdown_path)
    return draft if draft else None


def _build_correction_policy_payload(
    repo_root: Path,
    correction_draft: dict[str, object],
    closure: dict[str, object] | None,
) -> dict[str, object]:
    closure = closure or {}
    project = str(correction_draft.get("generated_from_project") or repo_root.name)
    candidate_id = str(correction_draft.get("selected_candidate_id") or "candidate-1")
    strategy = str(correction_draft.get("correction_strategy") or "confidence-raise")
    build_status = str(closure.get("build_probe_status") or "unknown")
    smoke_status = str(closure.get("smoke_probe_status") or "unknown")
    suggestions = correction_draft.get("correction_suggestions") if isinstance(correction_draft.get("correction_suggestions"), list) else []
    normalized_suggestions = [item for item in suggestions if isinstance(item, dict)]

    decision = "hold-missing-closure"
    disposition = "deferred"
    apply_policy = "none"
    rationale = "No closure evidence was available; keep the correction draft as advisory-only until build/smoke evidence exists."
    selected_suggestions: list[dict[str, object]] = []
    if build_status == "failed":
        decision = "promote-reviewable-correction"
        disposition = "promoted"
        apply_policy = "comment-only"
        rationale = "The latest skeleton closure failed during build, so preserve only reviewable compile/link correction hints."
        selected_suggestions = normalized_suggestions
    elif smoke_status == "failed":
        decision = "promote-reviewable-correction"
        disposition = "promoted"
        apply_policy = "comment-only"
        rationale = "The latest skeleton closure failed during smoke, so preserve only reviewable gating/touchpoint correction hints."
        selected_suggestions = normalized_suggestions
    elif build_status == "passed" and smoke_status == "passed":
        decision = "hold-no-change"
        disposition = "deferred"
        apply_policy = "none"
        rationale = "The latest skeleton closure already passed build and smoke; do not consume correction suggestions into a patch candidate."
        selected_suggestions = []
    elif smoke_status == "skipped":
        decision = "hold-await-smoke"
        disposition = "deferred"
        apply_policy = "none"
        rationale = "Smoke has not run successfully yet; keep correction suggestions on hold until a reproducible smoke result exists."
        selected_suggestions = []

    return {
        "generated_from_project": project,
        "selected_candidate_id": candidate_id,
        "entrypoint_path": correction_draft.get("entrypoint_path") or closure.get("entrypoint_path"),
        "target_file_path": correction_draft.get("target_file_path"),
        "correction_strategy": strategy,
        "decision": decision,
        "disposition": disposition,
        "apply_policy": apply_policy,
        "decision_rationale": rationale,
        "build_probe_status": build_status,
        "smoke_probe_status": smoke_status,
        "revision_signal_source": correction_draft.get("revision_signal_source"),
        "source_correction_draft_path": correction_draft.get("correction_draft_json_path"),
        "source_correction_markdown_path": correction_draft.get("correction_draft_markdown_path"),
        "source_closure_manifest_path": closure.get("closure_manifest_path"),
        "selected_suggestions": selected_suggestions,
        "selected_suggestion_titles": [str(item.get("title") or "") for item in selected_suggestions if str(item.get("title") or "")],
        "selected_suggestion_count": len(selected_suggestions),
    }


def render_harness_correction_policy_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Harness Correction Consumption Policy",
        "",
        f"- project: {payload.get('generated_from_project')}",
        f"- selected_candidate_id: {payload.get('selected_candidate_id')}",
        f"- target_file_path: {payload.get('target_file_path')}",
        f"- correction_strategy: {payload.get('correction_strategy')}",
        f"- source_correction_draft_path: {payload.get('source_correction_draft_path')}",
        f"- source_closure_manifest_path: {payload.get('source_closure_manifest_path')}",
        "",
        "## Consumption Decision",
        "",
        f"- decision: {payload.get('decision')}",
        f"- disposition: {payload.get('disposition')}",
        f"- apply_policy: {payload.get('apply_policy')}",
        f"- build_probe_status: {payload.get('build_probe_status')}",
        f"- smoke_probe_status: {payload.get('smoke_probe_status')}",
        f"- rationale: {payload.get('decision_rationale')}",
        "",
        "## Selected Suggestions",
        "",
    ]
    for suggestion in payload.get("selected_suggestions") or []:
        if not isinstance(suggestion, dict):
            continue
        lines.append(f"- title: {suggestion.get('title')}")
        lines.append(f"  - rationale: {suggestion.get('rationale')}")
        lines.append(f"  - suggested_change: {suggestion.get('suggested_change')}")
    if not payload.get("selected_suggestions"):
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- This policy is still source-adjacent and conservative; it does not auto-apply code changes.",
            "- Promote only closure-backed corrections, and prefer comments/TODO-level consumption before real wiring.",
            "",
        ]
    )
    return "\n".join(lines)


def write_harness_correction_policy(repo_root: Path) -> dict[str, object]:
    skeleton_result = write_harness_skeleton_draft(repo_root)
    candidate_id = str(skeleton_result.get("selected_candidate_id") or "candidate-1")
    correction_draft = _latest_correction_draft(repo_root, candidate_id)
    if correction_draft is None:
        manifest_path = skeleton_result.get("skeleton_manifest_path")
        if manifest_path:
            skeleton_manifest = _load_json(Path(str(manifest_path)), {})
            correction_draft = {
                "generated_from_project": skeleton_manifest.get("generated_from_project") or repo_root.name,
                "selected_candidate_id": skeleton_manifest.get("selected_candidate_id") or candidate_id,
                "entrypoint_path": skeleton_manifest.get("entrypoint_path"),
                "target_file_path": skeleton_manifest.get("skeleton_source_path"),
                "correction_strategy": skeleton_manifest.get("correction_strategy"),
                "correction_suggestions": skeleton_manifest.get("correction_suggestions"),
                "revision_signal_source": skeleton_manifest.get("revision_signal_source"),
                "correction_draft_json_path": skeleton_manifest.get("correction_draft_json_path"),
                "correction_draft_markdown_path": skeleton_manifest.get("correction_draft_markdown_path"),
            }
        else:
            correction_draft = {}
    closure = _latest_skeleton_closure(repo_root, candidate_id)
    payload = _build_correction_policy_payload(repo_root, correction_draft, closure)
    out_dir = repo_root / "fuzz-records" / "harness-correction-policies"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{_slugify(str(payload.get('generated_from_project') or repo_root.name))}-{candidate_id}-harness-correction-policy"
    manifest_path = out_dir / f"{stem}.json"
    plan_path = out_dir / f"{stem}.md"
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    plan_path.write_text(render_harness_correction_policy_markdown(payload), encoding="utf-8")
    return {
        "generated_from_project": payload.get("generated_from_project"),
        "selected_candidate_id": payload.get("selected_candidate_id"),
        "decision": payload.get("decision"),
        "disposition": payload.get("disposition"),
        "apply_policy": payload.get("apply_policy"),
        "selected_suggestion_titles": payload.get("selected_suggestion_titles"),
        "selected_suggestion_count": payload.get("selected_suggestion_count"),
        "policy_manifest_path": str(manifest_path),
        "policy_plan_path": str(plan_path),
        "source_correction_draft_path": payload.get("source_correction_draft_path"),
        "source_closure_manifest_path": payload.get("source_closure_manifest_path"),
    }


def _latest_correction_policy(repo_root: Path, candidate_id: str | None) -> dict[str, object] | None:
    if not candidate_id:
        return None
    policy_dir = repo_root / "fuzz-records" / "harness-correction-policies"
    policy_path = _latest_file(policy_dir, f"*-{candidate_id}-harness-correction-policy.json")
    if policy_path is None:
        return None
    policy = _load_json(policy_path, {})
    if str(policy.get("selected_candidate_id") or "") != str(candidate_id):
        return None
    policy["policy_manifest_path"] = str(policy_path)
    markdown_path = policy_path.with_suffix(".md")
    if markdown_path.exists():
        policy["policy_plan_path"] = str(markdown_path)
    return policy if policy else None


def _apply_candidate_scope(policy: dict[str, object]) -> str:
    strategy = str(policy.get("correction_strategy") or "")
    if strategy == "smoke-fix":
        return "guard-only"
    if strategy == "build-fix":
        return "comment-only"
    return "comment-only"


def _build_harness_apply_delegate_request(payload: dict[str, object]) -> dict[str, object]:
    context_lines = [
        f"repo_root: {payload.get('repo_root')}",
        f"selected_candidate_id: {payload.get('selected_candidate_id')}",
        f"entrypoint_path: {payload.get('entrypoint_path')}",
        f"target_file_path: {payload.get('target_file_path')}",
        f"source_policy_manifest_path: {payload.get('source_policy_manifest_path')}",
        f"source_correction_draft_path: {payload.get('source_correction_draft_path')}",
        f"source_closure_manifest_path: {payload.get('source_closure_manifest_path')}",
        f"apply_candidate_scope: {payload.get('apply_candidate_scope')}",
        f"llm_evidence_json_path: {payload.get('llm_evidence_json_path')}",
        f"llm_evidence_markdown_path: {payload.get('llm_evidence_markdown_path')}",
        f"llm_objective: {payload.get('llm_objective')}",
        f"failure_reason_codes: {payload.get('failure_reason_codes')}",
        "",
        "Requirements:",
        "- Read the LLM evidence packet first and use its failure_reasons/llm_objective as the primary decision frame.",
        "- Produce a guarded harness patch candidate only; do not modify source files directly.",
        "- Keep changes within comment/TODO, minimal input guards, or tiny helper extraction boundaries.",
        "- Do not widen harness depth, enable persistent mode, or rewrite build scripts.",
        "- Include a '## Evidence Response' section with exact lines for 'llm_objective:' and 'failure_reason_codes:'.",
        "- In that section, state which failure_reason_codes you are addressing and why the proposed patch is the smallest safe response.",
        "- Summarize the safest next patch candidate and the exact verification steps.",
    ]
    return {
        "goal": "Prepare a guarded harness patch candidate from the latest promoted correction policy using the latest LLM evidence packet as the primary input.",
        "context": "\n".join(context_lines).strip() + "\n",
        "toolsets": ["file", "terminal"],
        "skills": [],
    }


def render_harness_apply_candidate_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Harness Guarded Apply Candidate",
        "",
        f"- project: {payload.get('generated_from_project')}",
        f"- selected_candidate_id: {payload.get('selected_candidate_id')}",
        f"- entrypoint_path: {payload.get('entrypoint_path')}",
        f"- target_file_path: {payload.get('target_file_path')}",
        f"- source_policy_manifest_path: {payload.get('source_policy_manifest_path')}",
        f"- apply_candidate_scope: {payload.get('apply_candidate_scope')}",
        "",
        "## Guarded Apply Decision",
        "",
        f"- decision: {payload.get('decision')}",
        f"- trigger_delegate: {payload.get('trigger_delegate')}",
        f"- selected_suggestion_count: {payload.get('selected_suggestion_count')}",
        f"- rationale: {payload.get('decision_rationale')}",
        "",
        "## Selected Suggestions",
        "",
    ]
    for suggestion in payload.get("selected_suggestions") or []:
        if not isinstance(suggestion, dict):
            continue
        lines.append(f"- title: {suggestion.get('title')}")
        lines.append(f"  - rationale: {suggestion.get('rationale')}")
        lines.append(f"  - suggested_change: {suggestion.get('suggested_change')}")
    if not payload.get("selected_suggestions"):
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- This stage generates only a reviewable apply candidate and optional delegate request artifact.",
            "- Source mutation stays disabled at this stage.",
            "- Keep patch scope small enough to re-check with build/smoke immediately in the next stage.",
            "",
        ]
    )
    return "\n".join(lines)


def write_harness_apply_candidate(repo_root: Path) -> dict[str, object]:
    policy_result = write_harness_correction_policy(repo_root)
    candidate_id = str(policy_result.get("selected_candidate_id") or "candidate-1")
    policy = _latest_correction_policy(repo_root, candidate_id) or {}
    selected_suggestions = policy.get("selected_suggestions") if isinstance(policy.get("selected_suggestions"), list) else []
    selected_suggestions = [item for item in selected_suggestions if isinstance(item, dict)]
    trigger_delegate = (
        str(policy.get("decision") or "") == "promote-reviewable-correction"
        and str(policy.get("apply_policy") or "") == "comment-only"
        and bool(selected_suggestions)
    )
    llm_evidence = write_llm_evidence_packet(repo_root)
    payload = {
        "repo_root": str(repo_root),
        "generated_from_project": policy.get("generated_from_project") or repo_root.name,
        "selected_candidate_id": policy.get("selected_candidate_id") or candidate_id,
        "entrypoint_path": policy.get("entrypoint_path"),
        "target_file_path": policy.get("target_file_path"),
        "source_policy_manifest_path": policy.get("policy_manifest_path") or policy_result.get("policy_manifest_path"),
        "source_policy_plan_path": policy.get("policy_plan_path") or policy_result.get("policy_plan_path"),
        "source_correction_draft_path": policy.get("source_correction_draft_path"),
        "source_closure_manifest_path": policy.get("source_closure_manifest_path"),
        "llm_evidence_json_path": llm_evidence.get("llm_evidence_json_path"),
        "llm_evidence_markdown_path": llm_evidence.get("llm_evidence_markdown_path"),
        "llm_objective": llm_evidence.get("llm_objective"),
        "failure_reason_codes": llm_evidence.get("failure_reason_codes"),
        "decision": "draft-reviewable-apply-candidate" if trigger_delegate else "hold-no-apply-candidate",
        "decision_rationale": policy.get("decision_rationale") or "No promoted correction policy was available for a guarded apply candidate.",
        "apply_candidate_scope": _apply_candidate_scope(policy),
        "selected_suggestions": selected_suggestions if trigger_delegate else [],
        "selected_suggestion_count": len(selected_suggestions) if trigger_delegate else 0,
        "trigger_delegate": trigger_delegate,
    }
    out_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{_slugify(str(payload.get('generated_from_project') or repo_root.name))}-{candidate_id}-harness-apply-candidate"
    manifest_path = out_dir / f"{stem}.json"
    plan_path = out_dir / f"{stem}.md"
    delegate_request_path = out_dir / f"{stem}-delegate-request.json"
    if trigger_delegate:
        delegate_request = _build_harness_apply_delegate_request(payload)
        delegate_request_path.write_text(json.dumps(delegate_request, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        payload["delegate_request_path"] = str(delegate_request_path)
    else:
        payload["delegate_request_path"] = None
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    plan_path.write_text(render_harness_apply_candidate_markdown(payload), encoding="utf-8")
    return {
        "generated_from_project": payload.get("generated_from_project"),
        "selected_candidate_id": payload.get("selected_candidate_id"),
        "decision": payload.get("decision"),
        "apply_candidate_scope": payload.get("apply_candidate_scope"),
        "trigger_delegate": payload.get("trigger_delegate"),
        "delegate_request_path": payload.get("delegate_request_path"),
        "apply_candidate_manifest_path": str(manifest_path),
        "apply_candidate_plan_path": str(plan_path),
        "source_policy_manifest_path": payload.get("source_policy_manifest_path"),
    }


def run_harness_skeleton_closure(repo_root: Path, *, probe_runner: ProbeRunner) -> dict[str, object]:
    skeleton_result = write_harness_skeleton_draft(repo_root)
    skeleton_manifest_path = Path(str(skeleton_result.get("skeleton_manifest_path")))
    skeleton_manifest = _load_json(skeleton_manifest_path, {})
    project = str(skeleton_manifest.get("generated_from_project") or repo_root.name)
    candidate_id = str(skeleton_manifest.get("selected_candidate_id") or "candidate-1")
    build_system = str((skeleton_manifest.get("evaluation") or {}).get("build_system") or "unknown")
    build_command = _build_probe_command(repo_root, build_system)
    seed_candidates = _find_seed_candidates(repo_root)
    seed_path = seed_candidates[0] if seed_candidates else None
    smoke_command = _smoke_probe_command(repo_root, seed_path)
    build_result = _probe_status("build", build_command, repo_root, probe_runner)
    if build_result.get("status") == "passed":
        smoke_result = _probe_status("smoke", smoke_command, repo_root, probe_runner)
    else:
        smoke_result = {
            "status": "skipped",
            "command": smoke_command,
            "exit_code": None,
            "output": "",
            "label": "smoke",
            "reason": "build-probe-did-not-pass",
        }

    out_dir = repo_root / "fuzz-records" / "harness-skeleton-probes"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{_slugify(project)}-{candidate_id}-harness-skeleton-probe"
    manifest_path = out_dir / f"{stem}.json"
    plan_path = out_dir / f"{stem}.md"
    payload = {
        "generated_from_project": project,
        "selected_candidate_id": candidate_id,
        "entrypoint_path": skeleton_manifest.get("entrypoint_path"),
        "skeleton_source_path": skeleton_manifest.get("skeleton_source_path"),
        "skeleton_manifest_path": str(skeleton_manifest_path),
        "build_probe_status": build_result.get("status"),
        "smoke_probe_status": smoke_result.get("status"),
        "build_probe_result": build_result,
        "smoke_probe_result": smoke_result,
        "seed_candidates": [str(path) for path in seed_candidates],
        "closure_manifest_path": str(manifest_path),
        "closure_plan_path": str(plan_path),
    }
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    plan_path.write_text(render_harness_skeleton_closure_markdown(payload), encoding="utf-8")
    return {
        "generated_from_project": project,
        "selected_candidate_id": candidate_id,
        "build_probe_status": build_result.get("status"),
        "smoke_probe_status": smoke_result.get("status"),
        "closure_manifest_path": str(manifest_path),
        "closure_plan_path": str(plan_path),
        "skeleton_source_path": skeleton_manifest.get("skeleton_source_path"),
    }