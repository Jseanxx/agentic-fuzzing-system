from __future__ import annotations

import json
from pathlib import Path


DEBT_FIELDS = (
    "seed_debt_count",
    "review_debt_count",
    "build_debt_count",
    "smoke_debt_count",
    "instability_debt_count",
    "verification_retry_debt",
    "verification_escalation_count",
    "pass_streak",
    "fail_streak",
    "probe_pass_count",
    "probe_fail_count",
    "build_pass_count",
    "build_fail_count",
    "smoke_pass_count",
    "smoke_fail_count",
    "verification_verified_count",
    "verification_unverified_count",
)


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


def _bootstrap_candidates(repo_root: Path) -> list[dict[str, object]]:
    draft_dir = repo_root / "fuzz-records" / "harness-drafts"
    draft_path = _latest_file(draft_dir, "*-harness-draft.json")
    if draft_path is None:
        return []
    draft = _load_json(draft_path, {"candidates": []})
    candidates = draft.get("candidates") if isinstance(draft.get("candidates"), list) else []
    result: list[dict[str, object]] = []
    base_score = 100
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            continue
        result.append(
            {
                "candidate_id": candidate.get("candidate_id"),
                "entrypoint_path": candidate.get("entrypoint_path"),
                "recommended_mode": candidate.get("recommended_mode"),
                "target_stage": candidate.get("target_stage"),
                "viability_score": int(candidate.get("viability_score") or 0),
                "build_viability": candidate.get("build_viability"),
                "smoke_viability": candidate.get("smoke_viability"),
                "callable_signal": candidate.get("callable_signal"),
                "score": base_score - (index * 5) + int(candidate.get("viability_score") or 0),
                "status": "active",
                "rank": index + 1,
            }
        )
    return result


def _latest_feedback(repo_root: Path) -> dict[str, object] | None:
    feedback_dir = repo_root / "fuzz-records" / "probe-feedback"
    feedback_path = _latest_file(feedback_dir, "*-probe-feedback.json")
    if feedback_path is None:
        return None
    feedback = _load_json(feedback_path, {})
    return feedback if feedback else None


def _ensure_candidate_debt_fields(candidate: dict[str, object]) -> None:
    for field in DEBT_FIELDS:
        candidate[field] = int(candidate.get(field) or 0)


def _compute_debt_penalty(candidate: dict[str, object]) -> int:
    _ensure_candidate_debt_fields(candidate)
    return (
        int(candidate.get("seed_debt_count") or 0) * 6
        + int(candidate.get("review_debt_count") or 0) * 10
        + int(candidate.get("build_debt_count") or 0) * 8
        + int(candidate.get("smoke_debt_count") or 0) * 5
        + int(candidate.get("instability_debt_count") or 0) * 7
        + int(candidate.get("verification_retry_debt") or 0) * 4
        + int(candidate.get("verification_escalation_count") or 0) * 6
        + int(candidate.get("fail_streak") or 0) * 3
        - int(candidate.get("pass_streak") or 0) * 2
    )


def _compute_execution_evidence_score(candidate: dict[str, object]) -> int:
    _ensure_candidate_debt_fields(candidate)
    return (
        int(candidate.get("probe_pass_count") or 0) * 8
        + int(candidate.get("build_pass_count") or 0) * 4
        + int(candidate.get("smoke_pass_count") or 0) * 6
        + int(candidate.get("verification_verified_count") or 0) * 7
        - int(candidate.get("probe_fail_count") or 0) * 6
        - int(candidate.get("build_fail_count") or 0) * 5
        - int(candidate.get("smoke_fail_count") or 0) * 6
        - int(candidate.get("verification_unverified_count") or 0) * 4
    )


def _feedback_reason_bucket(feedback: dict[str, object]) -> str:
    reason = str(feedback.get("bridge_reason") or "")
    if "build" in reason:
        return "build"
    if "smoke" in reason:
        return "smoke"
    if "stability" in reason or "duplicate" in reason or "nondetermin" in reason:
        return "instability"
    if "seed" in reason or "reseed" in reason:
        return "seed"
    return "generic"


def _apply_feedback(candidates: list[dict[str, object]], feedback: dict[str, object]) -> str | None:
    candidate_id = feedback.get("candidate_id")
    if not isinstance(candidate_id, str):
        return None
    action_code = str(feedback.get("action_code") or "")
    selected: dict[str, object] | None = None
    for candidate in candidates:
        if candidate.get("candidate_id") == candidate_id:
            selected = candidate
            break
    if selected is None:
        selected = {
            "candidate_id": candidate_id,
            "entrypoint_path": feedback.get("entrypoint_path"),
            "recommended_mode": None,
            "target_stage": None,
            "score": 0,
            "status": "new",
            "rank": len(candidates) + 1,
        }
        candidates.append(selected)

    _ensure_candidate_debt_fields(selected)
    current_score = int(selected.get("score") or 0)
    reason_bucket = _feedback_reason_bucket(feedback)
    build_status = str(feedback.get("build_probe_status") or "")
    smoke_status = str(feedback.get("smoke_probe_status") or "")
    if build_status == "passed":
        selected["build_pass_count"] = int(selected.get("build_pass_count") or 0) + 1
    elif build_status == "failed":
        selected["build_fail_count"] = int(selected.get("build_fail_count") or 0) + 1
    if smoke_status == "passed":
        selected["smoke_pass_count"] = int(selected.get("smoke_pass_count") or 0) + 1
    elif smoke_status == "failed":
        selected["smoke_fail_count"] = int(selected.get("smoke_fail_count") or 0) + 1

    if action_code == "shift_weight_to_deeper_harness":
        selected["score"] = current_score + 15
        selected["status"] = "promoted"
        selected["pass_streak"] = int(selected.get("pass_streak") or 0) + 1
        selected["fail_streak"] = 0
        selected["probe_pass_count"] = int(selected.get("probe_pass_count") or 0) + 1
        selected["verification_retry_debt"] = max(0, int(selected.get("verification_retry_debt") or 0) - 1)
    elif action_code == "halt_and_review_harness":
        selected["score"] = current_score - 15
        selected["status"] = "review_required"
        selected["review_debt_count"] = int(selected.get("review_debt_count") or 0) + 1
        selected["probe_fail_count"] = int(selected.get("probe_fail_count") or 0) + 1
        if reason_bucket == "build":
            selected["build_debt_count"] = int(selected.get("build_debt_count") or 0) + 1
        elif reason_bucket == "smoke":
            selected["smoke_debt_count"] = int(selected.get("smoke_debt_count") or 0) + 1
        else:
            selected["instability_debt_count"] = int(selected.get("instability_debt_count") or 0) + 1
        selected["fail_streak"] = int(selected.get("fail_streak") or 0) + 1
        selected["pass_streak"] = 0
    elif action_code == "minimize_and_reseed":
        selected["score"] = current_score - 5
        selected["status"] = "seed_debt"
        selected["seed_debt_count"] = int(selected.get("seed_debt_count") or 0) + 1
        selected["probe_fail_count"] = int(selected.get("probe_fail_count") or 0) + 1
        selected["fail_streak"] = int(selected.get("fail_streak") or 0) + 1
        selected["pass_streak"] = 0
    else:
        selected["status"] = "observed"
    selected["debt_penalty"] = _compute_debt_penalty(selected)
    selected["execution_evidence_score"] = _compute_execution_evidence_score(selected)
    selected["effective_score"] = int(selected.get("score") or 0) + int(selected.get("execution_evidence_score") or 0) - int(selected.get("debt_penalty") or 0)
    selected["last_feedback_action"] = action_code
    selected["last_feedback_reason"] = feedback.get("bridge_reason")
    return candidate_id


def _rerank(candidates: list[dict[str, object]]) -> None:
    for candidate in candidates:
        _ensure_candidate_debt_fields(candidate)
        candidate["debt_penalty"] = _compute_debt_penalty(candidate)
        candidate["execution_evidence_score"] = _compute_execution_evidence_score(candidate)
        candidate["effective_score"] = int(candidate.get("score") or 0) + int(candidate.get("execution_evidence_score") or 0) - int(candidate.get("debt_penalty") or 0)
    candidates.sort(
        key=lambda item: (
            -int(item.get("effective_score") or 0),
            -int(item.get("score") or 0),
            str(item.get("candidate_id") or ""),
        )
    )
    for index, candidate in enumerate(candidates, start=1):
        candidate["rank"] = index


def render_ranked_candidate_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Ranked Harness Candidates",
        "",
        f"- project: {payload.get('project')}",
        f"- selected_candidate_id: {payload.get('selected_candidate_id')}",
        f"- feedback_action_code: {payload.get('feedback_action_code')}",
        f"- feedback_reason: {payload.get('feedback_reason')}",
        "",
        "## Candidates",
        "",
    ]
    for candidate in payload.get("candidates") or []:
        if not isinstance(candidate, dict):
            continue
        lines.extend(
            [
                f"### rank-{candidate.get('rank')}: {candidate.get('candidate_id')}",
                f"- entrypoint_path: {candidate.get('entrypoint_path')}",
                f"- score: {candidate.get('score')}",
                f"- debt_penalty: {candidate.get('debt_penalty')}",
                f"- execution_evidence_score: {candidate.get('execution_evidence_score')}",
                f"- effective_score: {candidate.get('effective_score')}",
                f"- status: {candidate.get('status')}",
                f"- viability_score: {candidate.get('viability_score')}",
                f"- build_viability: {candidate.get('build_viability')}",
                f"- smoke_viability: {candidate.get('smoke_viability')}",
                f"- callable_signal: {candidate.get('callable_signal')}",
                f"- recommended_mode: {candidate.get('recommended_mode')}",
                f"- target_stage: {candidate.get('target_stage')}",
                f"- pass_streak: {candidate.get('pass_streak')}",
                f"- fail_streak: {candidate.get('fail_streak')}",
                f"- seed_debt_count: {candidate.get('seed_debt_count')}",
                f"- review_debt_count: {candidate.get('review_debt_count')}",
                f"- build_debt_count: {candidate.get('build_debt_count')}",
                f"- smoke_debt_count: {candidate.get('smoke_debt_count')}",
                f"- instability_debt_count: {candidate.get('instability_debt_count')}",
                f"- verification_retry_debt: {candidate.get('verification_retry_debt')}",
                f"- verification_escalation_count: {candidate.get('verification_escalation_count')}",
                "",
            ]
        )
    return "\n".join(lines)


def update_ranked_candidate_registry(repo_root: Path) -> dict[str, object]:
    registry_dir = repo_root / "fuzz-records" / "harness-candidates"
    registry_dir.mkdir(parents=True, exist_ok=True)
    registry_path = registry_dir / "ranked-candidates.json"
    plan_path = registry_dir / "ranked-candidates.md"

    registry = _load_json(registry_path, {"project": repo_root.name, "candidates": []})
    candidates = registry.get("candidates") if isinstance(registry.get("candidates"), list) else []
    normalized = [candidate for candidate in candidates if isinstance(candidate, dict)]
    if not normalized:
        normalized = _bootstrap_candidates(repo_root)

    feedback = _latest_feedback(repo_root) or {}
    selected_candidate_id = _apply_feedback(normalized, feedback) if feedback else None
    _rerank(normalized)

    payload = {
        "project": str(registry.get("project") or repo_root.name),
        "selected_candidate_id": selected_candidate_id,
        "feedback_action_code": feedback.get("action_code") if isinstance(feedback, dict) else None,
        "feedback_reason": feedback.get("bridge_reason") if isinstance(feedback, dict) else None,
        "candidates": normalized,
    }
    registry_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    plan_path.write_text(render_ranked_candidate_markdown(payload), encoding="utf-8")
    return {
        "updated": True,
        "registry_path": str(registry_path),
        "registry_plan_path": str(plan_path),
        "selected_candidate_id": selected_candidate_id,
        "top_candidate_id": normalized[0].get("candidate_id") if normalized else None,
        "candidate_count": len(normalized),
    }
