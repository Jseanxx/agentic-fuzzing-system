from __future__ import annotations

import json
import re
from pathlib import Path


DEBT_WEIGHT_FIELDS = {
    "seed_debt_count": 6,
    "review_debt_count": 10,
    "build_debt_count": 8,
    "smoke_debt_count": 5,
    "instability_debt_count": 7,
    "verification_retry_debt": 4,
    "verification_escalation_count": 6,
    "fail_streak": 3,
    "pass_streak": -2,
}


def _slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return value.strip("-") or "target"


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


def _latest_feedback_manifest(repo_root: Path) -> Path | None:
    feedback_dir = repo_root / "fuzz-records" / "probe-feedback"
    manifests = sorted(feedback_dir.glob("*-probe-feedback.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    return manifests[0] if manifests else None


def _candidate_route(action_code: str) -> str:
    if action_code == "shift_weight_to_deeper_harness":
        return "promote-next-depth"
    if action_code == "halt_and_review_harness":
        return "review-current-candidate"
    if action_code == "minimize_and_reseed":
        return "reseed-before-retry"
    return "observe-and-hold"


def _candidate_debt_penalty(candidate: dict[str, object]) -> int:
    penalty = 0
    for field, weight in DEBT_WEIGHT_FIELDS.items():
        value = int(candidate.get(field) or 0)
        penalty += value * weight
    return penalty


def _candidate_effective_score(candidate: dict[str, object]) -> int:
    return int(candidate.get("effective_score") or (int(candidate.get("score") or 0) - _candidate_debt_penalty(candidate)))


def select_next_ranked_candidate(repo_root: Path) -> dict[str, object]:
    feedback_path = _latest_feedback_manifest(repo_root)
    if feedback_path is None:
        return {"selected": False, "reason": "missing-feedback-manifest"}
    feedback = _load_json(feedback_path, {})
    if not feedback:
        return {"selected": False, "reason": "invalid-feedback-manifest"}
    candidate_route = _candidate_route(str(feedback.get("action_code") or "unknown"))
    registry_path = repo_root / "fuzz-records" / "harness-candidates" / "ranked-candidates.json"
    registry = _load_json(registry_path, {"candidates": []})
    candidates = registry.get("candidates") if isinstance(registry.get("candidates"), list) else []
    normalized = [candidate for candidate in candidates if isinstance(candidate, dict)]

    selected: dict[str, object] | None = None
    skipped: dict[str, object] | None = None
    if candidate_route == "review-current-candidate":
        candidate_id = feedback.get("candidate_id")
        if isinstance(candidate_id, str):
            selected = next((item for item in normalized if item.get("candidate_id") == candidate_id), None)
    else:
        eligible: list[dict[str, object]] = []
        for item in normalized:
            status = str(item.get("status") or "")
            if status in {"review_required"}:
                continue
            eligible.append(item)
        ranked = sorted(
            eligible,
            key=lambda item: (
                -_candidate_effective_score(item),
                -int(item.get("score") or 0),
                str(item.get("candidate_id") or ""),
            ),
        )
        if ranked:
            selected = ranked[0]
            skipped = ranked[1] if len(ranked) > 1 else None
    if selected is None and normalized:
        fallback = sorted(
            normalized,
            key=lambda item: (
                -_candidate_effective_score(item),
                -int(item.get("score") or 0),
                str(item.get("candidate_id") or ""),
            ),
        )
        selected = fallback[0]
        skipped = fallback[1] if len(fallback) > 1 else None
    if selected is None:
        return {
            "selected": False,
            "reason": "missing-ranked-candidates",
            "candidate_route": candidate_route,
        }
    return {
        "selected": True,
        "candidate_route": candidate_route,
        "selected_candidate_id": selected.get("candidate_id"),
        "selected_entrypoint_path": selected.get("entrypoint_path"),
        "selected_recommended_mode": selected.get("recommended_mode"),
        "selected_target_stage": selected.get("target_stage"),
        "selected_effective_score": _candidate_effective_score(selected),
        "selected_debt_penalty": _candidate_debt_penalty(selected),
        "skipped_candidate_id": skipped.get("candidate_id") if skipped else None,
        "skipped_candidate_effective_score": _candidate_effective_score(skipped) if skipped else None,
        "source_feedback_manifest": str(feedback_path),
    }


def build_probe_routing_decision(repo_root: Path) -> dict[str, object]:
    feedback_path = _latest_feedback_manifest(repo_root)
    if feedback_path is None:
        return {"routed": False, "reason": "missing-feedback-manifest"}

    feedback = json.loads(feedback_path.read_text(encoding="utf-8"))
    if not isinstance(feedback, dict):
        return {"routed": False, "reason": "invalid-feedback-manifest"}

    action_code = str(feedback.get("action_code") or "unknown")
    project = str(feedback.get("generated_from_project") or repo_root.name)
    selection = select_next_ranked_candidate(repo_root)
    return {
        "routed": True,
        "generated_from_project": project,
        "source_feedback_manifest": str(feedback_path),
        "action_code": action_code,
        "candidate_route": _candidate_route(action_code),
        "bridge_reason": feedback.get("bridge_reason"),
        "registry_name": feedback.get("registry_name"),
        "candidate_id": feedback.get("candidate_id"),
        "entrypoint_path": feedback.get("entrypoint_path"),
        "recommended_action": feedback.get("recommended_action"),
        "selected_candidate_id": selection.get("selected_candidate_id"),
        "selected_entrypoint_path": selection.get("selected_entrypoint_path"),
        "selected_recommended_mode": selection.get("selected_recommended_mode"),
        "selected_target_stage": selection.get("selected_target_stage"),
    }


def render_probe_routing_markdown(handoff: dict[str, object]) -> str:
    lines = [
        "# Harness Probe Routing Handoff",
        "",
        f"- project: {handoff.get('generated_from_project')}",
        f"- source_feedback_manifest: {handoff.get('source_feedback_manifest')}",
        f"- action_code: {handoff.get('action_code')}",
        f"- candidate_route: {handoff.get('candidate_route')}",
        f"- bridge_reason: {handoff.get('bridge_reason')}",
        f"- registry_name: {handoff.get('registry_name')}",
        f"- orchestration_status: {handoff.get('orchestration_status')}",
        f"- dispatch_status: {handoff.get('dispatch_status')}",
        f"- dispatch_channel: {handoff.get('dispatch_channel')}",
        "",
        "## Candidate",
        "",
        f"- candidate_id: {handoff.get('candidate_id')}",
        f"- entrypoint_path: {handoff.get('entrypoint_path')}",
        f"- selected_candidate_id: {handoff.get('selected_candidate_id')}",
        f"- selected_entrypoint_path: {handoff.get('selected_entrypoint_path')}",
        f"- recommended_action: {handoff.get('recommended_action')}",
        "",
        "## Handoff Artifacts",
        "",
        f"- orchestration_manifest_path: {handoff.get('orchestration_manifest_path')}",
        f"- delegate_task_request_path: {handoff.get('delegate_task_request_path')}",
        f"- cronjob_request_path: {handoff.get('cronjob_request_path')}",
        "",
        "## Next Steps",
        "",
        "- Treat this as a routing artifact, not final execution success.",
        "- Review the selected route and queued handoff before launching bridge scripts.",
        "- If routing looks wrong, patch feedback mapping before attempting harness generation.",
        "",
    ]
    return "\n".join(lines)


def write_probe_routing_handoff(repo_root: Path, handoff: dict[str, object]) -> dict[str, object]:
    out_dir = repo_root / "fuzz-records" / "probe-routing"
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = _slugify(str(handoff.get("generated_from_project") or repo_root.name))
    manifest_path = out_dir / f"{slug}-probe-routing.json"
    plan_path = out_dir / f"{slug}-probe-routing.md"
    manifest_path.write_text(json.dumps(handoff, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    plan_path.write_text(render_probe_routing_markdown(handoff), encoding="utf-8")
    return {
        **handoff,
        "handoff_manifest_path": str(manifest_path),
        "handoff_plan_path": str(plan_path),
    }
