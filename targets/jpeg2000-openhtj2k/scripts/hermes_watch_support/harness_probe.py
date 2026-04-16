from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from .harness_evaluation import build_harness_evaluation_draft, write_harness_evaluation_draft
from .profile_loading import load_target_profile, resolve_target_profile_path
from .profile_summary import build_target_profile_summary
from .target_adapter import get_target_adapter

ProbeRunner = Callable[[list[str], Path], tuple[int, str]]

SEED_DIR_CANDIDATES = (
    "fuzz/corpus",
    "corpus",
    "seeds",
    "testdata",
    "tests/data",
)
SEED_FILE_EXTENSIONS = (".bin", ".jp2", ".j2k", ".jph", ".jpg", ".jpeg", ".png", ".gif", ".txt", ".json", ".xml")


def _find_seed_candidates(repo_root: Path, *, limit: int = 5) -> list[Path]:
    candidates: list[Path] = []
    for rel_dir in SEED_DIR_CANDIDATES:
        root = repo_root / rel_dir
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() in SEED_FILE_EXTENSIONS or not path.suffix:
                candidates.append(path)
            if len(candidates) >= limit:
                return candidates
    return candidates


def _resolve_target_adapter(repo_root: Path):
    profile_path = resolve_target_profile_path(repo_root, None)
    if profile_path is None:
        return None
    profile = load_target_profile(profile_path)
    profile_summary = build_target_profile_summary(profile, profile_path)
    return get_target_adapter(profile_summary)


def _build_probe_command(repo_root: Path, build_system: str) -> list[str] | None:
    target_adapter = _resolve_target_adapter(repo_root)
    adapter_build_command = target_adapter.build_command_list() if target_adapter else None
    if adapter_build_command:
        return adapter_build_command
    probe_build_dir = repo_root / "build" / "hermes-short-probe"
    if build_system == "cmake":
        return ["cmake", "-S", str(repo_root), "-B", str(probe_build_dir)]
    if build_system == "meson":
        return ["meson", "setup", str(probe_build_dir), str(repo_root)]
    if build_system == "make":
        return ["make", "-n"]
    if build_system == "autotools":
        configure = repo_root / "configure"
        if configure.exists():
            return [str(configure), "--help"]
    return None


def _smoke_probe_command(repo_root: Path, seed_path: Path | None) -> list[str] | None:
    target_adapter = _resolve_target_adapter(repo_root)
    adapter_smoke_command = target_adapter.smoke_command(repo_root) if target_adapter else None
    if adapter_smoke_command:
        return adapter_smoke_command
    if seed_path is None:
        return None
    for rel_script in ("scripts/run-smoke.sh", "run-smoke.sh"):
        script_path = repo_root / rel_script
        if script_path.exists():
            return [str(script_path), str(seed_path)]
    return None


def build_harness_probe_draft(repo_root: Path) -> dict[str, object]:
    evaluation = build_harness_evaluation_draft(repo_root)
    evaluations = evaluation.get("evaluations") if isinstance(evaluation.get("evaluations"), list) else []
    probe_candidate = evaluations[0] if evaluations and isinstance(evaluations[0], dict) else {}
    build_system = str(evaluation.get("build_system") or "unknown")
    build_command = _build_probe_command(repo_root, build_system)
    seed_candidates = _find_seed_candidates(repo_root)
    seed_path = seed_candidates[0] if seed_candidates else None
    smoke_command = _smoke_probe_command(repo_root, seed_path)
    return {
        "generated_from_project": evaluation.get("generated_from_project"),
        "build_system": build_system,
        "probe_candidate": probe_candidate,
        "seed_candidates": [str(path) for path in seed_candidates],
        "build_probe": {
            "status": "planned" if build_command else "skipped",
            "command": build_command,
            "reason": None if build_command else "unsupported-build-system",
            "timeout_seconds": 120,
        },
        "smoke_probe": {
            "status": "planned" if smoke_command else "skipped",
            "command": smoke_command,
            "seed_path": str(seed_path) if seed_path else None,
            "reason": None if smoke_command else "missing-smoke-script-or-seed",
            "timeout_seconds": 60,
        },
        "evaluation": evaluation,
    }


def render_harness_probe_markdown(
    draft: dict[str, object],
    *,
    evaluation_manifest_path: str | None = None,
    evaluation_plan_path: str | None = None,
) -> str:
    candidate = draft.get("probe_candidate") if isinstance(draft.get("probe_candidate"), dict) else {}
    build_probe = draft.get("build_probe") if isinstance(draft.get("build_probe"), dict) else {}
    smoke_probe = draft.get("smoke_probe") if isinstance(draft.get("smoke_probe"), dict) else {}
    lines = [
        "# Harness Short Probe",
        "",
        f"- project: {draft.get('generated_from_project')}",
        f"- build_system: {draft.get('build_system')}",
        f"- evaluation_manifest_path: {evaluation_manifest_path}",
        f"- evaluation_plan_path: {evaluation_plan_path}",
        "",
        "## Selected Candidate",
        "",
        f"- candidate_id: {candidate.get('candidate_id')}",
        f"- entrypoint_path: {candidate.get('entrypoint_path')}",
        f"- recommended_mode: {candidate.get('recommended_mode')}",
        f"- expected_success_signal: {candidate.get('expected_success_signal')}",
        "",
        "## Build Probe",
        "",
        f"- status: {build_probe.get('status')}",
        f"- command: {build_probe.get('command')}",
        f"- timeout_seconds: {build_probe.get('timeout_seconds')}",
        f"- reason: {build_probe.get('reason')}",
        "",
        "## Smoke Probe",
        "",
        f"- status: {smoke_probe.get('status')}",
        f"- command: {smoke_probe.get('command')}",
        f"- seed_path: {smoke_probe.get('seed_path')}",
        f"- timeout_seconds: {smoke_probe.get('timeout_seconds')}",
        f"- reason: {smoke_probe.get('reason')}",
        "",
        "## Policy",
        "",
        "- Execute at most one selected candidate.",
        "- Stop immediately on build failure or smoke ambiguity.",
        "- Use only one baseline seed for the first smoke probe.",
        "- Feed failures back into recon/profile refinement before any harness generation.",
        "",
    ]
    return "\n".join(lines)


def _probe_status(label: str, command: list[str] | None, repo_root: Path, probe_runner: ProbeRunner) -> dict[str, object]:
    if not command:
        return {"status": "skipped", "command": command, "exit_code": None, "output": "", "label": label}
    exit_code, output = probe_runner(command, repo_root)
    return {
        "status": "passed" if exit_code == 0 else "failed",
        "command": command,
        "exit_code": exit_code,
        "output": output,
        "label": label,
    }


def run_short_harness_probe(repo_root: Path, *, probe_runner: ProbeRunner) -> dict[str, object]:
    evaluation_result = write_harness_evaluation_draft(repo_root)
    draft = build_harness_probe_draft(repo_root)
    out_dir = repo_root / "fuzz-records" / "harness-probes"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_slug = str(draft.get("generated_from_project") or repo_root.name)
    manifest_path = out_dir / f"{project_slug}-harness-probe.json"
    plan_path = out_dir / f"{project_slug}-harness-probe.md"

    build_probe = draft.get("build_probe") if isinstance(draft.get("build_probe"), dict) else {}
    smoke_probe = draft.get("smoke_probe") if isinstance(draft.get("smoke_probe"), dict) else {}
    build_result = _probe_status("build", build_probe.get("command") if isinstance(build_probe.get("command"), list) else None, repo_root, probe_runner)
    smoke_result: dict[str, object]
    if build_result.get("status") == "passed":
        smoke_result = _probe_status("smoke", smoke_probe.get("command") if isinstance(smoke_probe.get("command"), list) else None, repo_root, probe_runner)
    else:
        smoke_result = {
            "status": "skipped",
            "command": smoke_probe.get("command") if isinstance(smoke_probe.get("command"), list) else None,
            "exit_code": None,
            "output": "",
            "label": "smoke",
            "reason": "build-probe-did-not-pass",
        }

    result = {
        "generated_from_project": draft.get("generated_from_project"),
        "probe_candidate": draft.get("probe_candidate"),
        "build_probe_status": build_result.get("status"),
        "smoke_probe_status": smoke_result.get("status"),
        "build_probe_exit_code": build_result.get("exit_code"),
        "smoke_probe_exit_code": smoke_result.get("exit_code"),
        "build_probe_command": build_result.get("command"),
        "smoke_probe_command": smoke_result.get("command"),
        "probe_manifest_path": str(manifest_path),
        "probe_plan_path": str(plan_path),
        "evaluation_manifest_path": str(evaluation_result.get("evaluation_manifest_path")),
        "evaluation_plan_path": str(evaluation_result.get("evaluation_plan_path")),
    }
    manifest_payload = {
        **draft,
        "build_probe_result": build_result,
        "smoke_probe_result": smoke_result,
        "evaluation_manifest_path": evaluation_result.get("evaluation_manifest_path"),
        "evaluation_plan_path": evaluation_result.get("evaluation_plan_path"),
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    plan_path.write_text(
        render_harness_probe_markdown(
            draft,
            evaluation_manifest_path=str(evaluation_result.get("evaluation_manifest_path")),
            evaluation_plan_path=str(evaluation_result.get("evaluation_plan_path")),
        )
        + "\n## Probe Result\n\n"
        + f"- build_probe_status: {build_result.get('status')}\n"
        + f"- smoke_probe_status: {smoke_result.get('status')}\n",
        encoding="utf-8",
    )
    return result
