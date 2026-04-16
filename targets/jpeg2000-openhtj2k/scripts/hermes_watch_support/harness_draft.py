from __future__ import annotations

import json
from pathlib import Path

from .reconnaissance import build_target_reconnaissance, write_target_profile_auto_draft


def _has_smoke_script(repo_root: Path) -> bool:
    return any((repo_root / rel).exists() for rel in ("scripts/run-smoke.sh", "run-smoke.sh"))


def _has_baseline_seed(repo_root: Path) -> bool:
    for rel in ("fuzz/corpus", "corpus", "seeds", "testdata", "tests/data"):
        seed_dir = repo_root / rel
        if seed_dir.exists() and any(path.is_file() for path in seed_dir.rglob("*")):
            return True
    return False


def _callable_signal(entrypoint: str | None) -> str:
    value = str(entrypoint or "").lower()
    if any(token in value for token in ("parse", "decode", "load", "read", "process", "transform")):
        return "likely-callable"
    if value:
        return "uncertain"
    return "missing-entrypoint"


def _build_viability(build_system: str, entrypoint: str | None) -> str:
    if build_system != "unknown" and entrypoint:
        return "high"
    if build_system != "unknown" or entrypoint:
        return "medium"
    return "low"


def _smoke_viability(repo_root: Path) -> str:
    has_script = _has_smoke_script(repo_root)
    has_seed = _has_baseline_seed(repo_root)
    if has_script and has_seed:
        return "high"
    if has_script or has_seed:
        return "medium"
    return "low"


def _viability_score(*, callable_signal: str, build_viability: str, smoke_viability: str, recommended_mode: str) -> int:
    score = 0
    score += {"high": 10, "medium": 5, "low": 0}.get(build_viability, 0)
    score += {"high": 10, "medium": 5, "low": 0}.get(smoke_viability, 0)
    score += {"likely-callable": 6, "uncertain": 2, "missing-entrypoint": 0}.get(callable_signal, 0)
    score += {"parse": 4, "decode": 3, "deep-decode": 2}.get(recommended_mode, 0)
    return score


def infer_harness_candidates(recon: dict[str, object], *, repo_root: Path | None = None) -> list[dict[str, object]]:
    entrypoints = recon.get("entrypoint_candidates") if isinstance(recon.get("entrypoint_candidates"), list) else []
    stages = recon.get("stage_candidates") if isinstance(recon.get("stage_candidates"), list) else []
    candidates: list[dict[str, object]] = []
    if not entrypoints:
        entrypoints = [stage.get("examples", [None])[0] for stage in stages if isinstance(stage, dict) and stage.get("examples")]
    seen: set[str] = set()
    build_system = str(recon.get("build_system") or "unknown")
    repo_for_viability = repo_root if isinstance(repo_root, Path) else None
    shared_smoke_viability = _smoke_viability(repo_for_viability) if repo_for_viability is not None else "low"
    for index, entrypoint in enumerate(entrypoints):
        if not isinstance(entrypoint, str) or not entrypoint or entrypoint in seen:
            continue
        seen.add(entrypoint)
        stage_id = None
        recommended_mode = "exploratory-auto-draft"
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            examples = stage.get("examples") if isinstance(stage.get("examples"), list) else []
            if entrypoint in examples or str(stage.get("id") or "") in entrypoint:
                stage_id = stage.get("id")
                stage_class = stage.get("stage_class")
                if stage_class == "shallow":
                    recommended_mode = "parse"
                elif stage_class == "medium":
                    recommended_mode = "decode"
                elif stage_class == "deep":
                    recommended_mode = "deep-decode"
                break
        callable_signal = _callable_signal(entrypoint)
        build_viability = _build_viability(build_system, entrypoint)
        smoke_viability = shared_smoke_viability
        viability_score = _viability_score(
            callable_signal=callable_signal,
            build_viability=build_viability,
            smoke_viability=smoke_viability,
            recommended_mode=recommended_mode,
        )
        candidates.append(
            {
                "candidate_id": f"candidate-{index + 1}",
                "entrypoint_path": entrypoint,
                "target_stage": stage_id,
                "recommended_mode": recommended_mode,
                "smoke_seed_assumption": "needs manually-selected valid baseline input",
                "build_assumption": recon.get("build_system") or "unknown",
                "callable_signal": callable_signal,
                "build_viability": build_viability,
                "smoke_viability": smoke_viability,
                "viability_score": viability_score,
                "notes": [
                    "candidate derived from reconnaissance filename heuristics",
                    f"viability summary: callable={callable_signal}, build={build_viability}, smoke={smoke_viability}",
                    "requires human review before code generation",
                ],
            }
        )
    if not candidates:
        candidates.append(
            {
                "candidate_id": "candidate-1",
                "entrypoint_path": None,
                "target_stage": None,
                "recommended_mode": "exploratory-auto-draft",
                "smoke_seed_assumption": "unknown",
                "build_assumption": recon.get("build_system") or "unknown",
                "callable_signal": "missing-entrypoint",
                "build_viability": "low",
                "smoke_viability": shared_smoke_viability,
                "viability_score": _viability_score(
                    callable_signal="missing-entrypoint",
                    build_viability="low",
                    smoke_viability=shared_smoke_viability,
                    recommended_mode="exploratory-auto-draft",
                ),
                "notes": ["no concrete entrypoint inferred; manual review required"],
            }
        )
    return candidates[:5]


def build_harness_candidate_draft(repo_root: Path) -> dict[str, object]:
    recon = build_target_reconnaissance(repo_root)
    candidates = infer_harness_candidates(recon, repo_root=repo_root)
    return {
        "generated_from_project": recon.get("project_name"),
        "build_system": recon.get("build_system"),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "recon": recon,
    }


def render_harness_candidate_markdown(draft: dict[str, object], *, draft_profile_path: str | None = None, recon_manifest_path: str | None = None) -> str:
    lines = [
        "# Harness Candidate Draft",
        "",
        f"- project: {draft.get('generated_from_project')}",
        f"- build_system: {draft.get('build_system')}",
        f"- candidate_count: {draft.get('candidate_count')}",
        f"- draft_profile_path: {draft_profile_path}",
        f"- recon_manifest_path: {recon_manifest_path}",
        "",
        "## Candidate Harnesses",
        "",
    ]
    for candidate in draft.get("candidates") or []:
        if not isinstance(candidate, dict):
            continue
        lines.extend(
            [
                f"### {candidate.get('candidate_id')}",
                f"- entrypoint_path: {candidate.get('entrypoint_path')}",
                f"- target_stage: {candidate.get('target_stage')}",
                f"- recommended_mode: {candidate.get('recommended_mode')}",
                f"- smoke_seed_assumption: {candidate.get('smoke_seed_assumption')}",
                f"- build_assumption: {candidate.get('build_assumption')}",
                f"- callable_signal: {candidate.get('callable_signal')}",
                f"- build_viability: {candidate.get('build_viability')}",
                f"- smoke_viability: {candidate.get('smoke_viability')}",
                f"- viability_score: {candidate.get('viability_score')}",
                "- notes:",
            ]
        )
        for note in candidate.get("notes") or []:
            lines.append(f"  - {note}")
        lines.append("")
    lines.extend(
        [
            "## Next Steps",
            "",
            "- Pick 1-2 candidate harnesses for manual review before code generation.",
            "- Define a valid smoke seed and expected success condition.",
            "- Only after review, attempt low-risk harness stub generation.",
            "",
        ]
    )
    return "\n".join(lines)


def write_harness_candidate_draft(repo_root: Path) -> dict[str, object]:
    profile_result = write_target_profile_auto_draft(repo_root)
    draft = build_harness_candidate_draft(repo_root)
    out_dir = repo_root / "fuzz-records" / "harness-drafts"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_slug = str(draft.get("generated_from_project") or repo_root.name)
    manifest_path = out_dir / f"{project_slug}-harness-draft.json"
    plan_path = out_dir / f"{project_slug}-harness-draft.md"
    manifest_payload = {
        **draft,
        "draft_profile_path": profile_result.get("draft_profile_path"),
        "recon_manifest_path": profile_result.get("recon_manifest_path"),
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    plan_path.write_text(
        render_harness_candidate_markdown(
            draft,
            draft_profile_path=str(profile_result.get("draft_profile_path")),
            recon_manifest_path=str(profile_result.get("recon_manifest_path")),
        ),
        encoding="utf-8",
    )
    return {
        "generated_from_project": draft.get("generated_from_project"),
        "candidate_count": draft.get("candidate_count"),
        "harness_manifest_path": str(manifest_path),
        "harness_plan_path": str(plan_path),
        "draft_profile_path": str(profile_result.get("draft_profile_path")),
        "recon_manifest_path": str(profile_result.get("recon_manifest_path")),
    }
