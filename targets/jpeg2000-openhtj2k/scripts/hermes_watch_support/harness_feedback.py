from __future__ import annotations

import json
import re
from pathlib import Path


def _load_registry(path: Path, default: dict[str, object]) -> dict[str, object]:
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


def _save_registry(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _append_unique_entry(entries: list[dict[str, object]], candidate: dict[str, object], unique_key: str) -> bool:
    for entry in entries:
        if entry.get(unique_key) == candidate.get(unique_key):
            return False
    entries.append(candidate)
    return True


def _record_refiner_entry(automation_dir: Path, *, registry_name: str, entry: dict[str, object]) -> tuple[bool, Path]:
    path = automation_dir / registry_name
    data = _load_registry(path, {"entries": []})
    entries = data.setdefault("entries", [])
    assert isinstance(entries, list)
    created = _append_unique_entry(entries, entry, "key")
    _save_registry(path, data)
    return created, path


def _slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return value.strip("-") or "target"


def _latest_probe_manifest(repo_root: Path) -> Path | None:
    probe_dir = repo_root / "fuzz-records" / "harness-probes"
    manifests = sorted(probe_dir.glob("*-harness-probe.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    return manifests[0] if manifests else None


def _select_feedback_action(manifest: dict[str, object]) -> dict[str, str]:
    build = manifest.get("build_probe_result") if isinstance(manifest.get("build_probe_result"), dict) else {}
    smoke = manifest.get("smoke_probe_result") if isinstance(manifest.get("smoke_probe_result"), dict) else {}
    build_status = str(build.get("status") or "unknown")
    smoke_status = str(smoke.get("status") or "unknown")
    seed_candidates = manifest.get("seed_candidates") if isinstance(manifest.get("seed_candidates"), list) else []

    if build_status == "failed":
        return {
            "action_code": "halt_and_review_harness",
            "registry_name": "harness_review_queue.json",
            "updated_label": "harness_reviews",
            "recommended_action": "Build probe failed; halt and review harness assumptions before continuing.",
            "reason": "build-probe-failed",
        }
    if smoke_status == "failed":
        return {
            "action_code": "halt_and_review_harness",
            "registry_name": "harness_review_queue.json",
            "updated_label": "harness_reviews",
            "recommended_action": "Smoke probe failed; halt and review harness/smoke assumptions before deeper execution.",
            "reason": "smoke-probe-failed",
        }
    if smoke_status == "skipped" and not seed_candidates:
        return {
            "action_code": "minimize_and_reseed",
            "registry_name": "corpus_refinements.json",
            "updated_label": "corpus_refinements",
            "recommended_action": "Smoke probe was skipped because no baseline seed was available; prioritize reseeding before continuing.",
            "reason": "smoke-skipped-missing-seed",
        }
    if smoke_status == "skipped":
        return {
            "action_code": "halt_and_review_harness",
            "registry_name": "harness_review_queue.json",
            "updated_label": "harness_reviews",
            "recommended_action": "Smoke probe was skipped despite build viability; review smoke harness wiring before deeper execution.",
            "reason": "smoke-skipped-review-required",
        }
    return {
        "action_code": "shift_weight_to_deeper_harness",
        "registry_name": "mode_refinements.json",
        "updated_label": "mode_refinements",
        "recommended_action": "Short probe passed cleanly; shift weight toward deeper harness candidates or the next execution depth.",
        "reason": "probe-passed",
    }


def render_probe_feedback_markdown(feedback: dict[str, object]) -> str:
    lines = [
        "# Harness Probe Feedback",
        "",
        f"- project: {feedback.get('generated_from_project')}",
        f"- source_probe_manifest: {feedback.get('source_probe_manifest')}",
        f"- action_code: {feedback.get('action_code')}",
        f"- bridge_reason: {feedback.get('bridge_reason')}",
        f"- registry_name: {feedback.get('registry_name')}",
        f"- feedback_json_path: {feedback.get('feedback_json_path')}",
        "",
        "## Recommendation",
        "",
        f"- recommended_action: {feedback.get('recommended_action')}",
        f"- build_probe_status: {feedback.get('build_probe_status')}",
        f"- smoke_probe_status: {feedback.get('smoke_probe_status')}",
        "",
        "## Candidate",
        "",
        f"- candidate_id: {feedback.get('candidate_id')}",
        f"- entrypoint_path: {feedback.get('entrypoint_path')}",
        "",
        "## Next Steps",
        "",
        "- Review the recorded feedback artifact before any destructive harness mutation.",
        "- Use the queued refinement entry as the next low-risk refinement substrate.",
        "- If the bridge reason is weak or ambiguous, refine recon/profile assumptions first.",
        "",
    ]
    return "\n".join(lines)


def bridge_harness_probe_feedback(repo_root: Path) -> dict[str, object]:
    manifest_path = _latest_probe_manifest(repo_root)
    if manifest_path is None:
        return {"bridged": False, "reason": "missing-probe-manifest"}

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        return {"bridged": False, "reason": "invalid-probe-manifest"}

    action = _select_feedback_action(manifest)
    automation_dir = repo_root / "fuzz-artifacts" / "automation"
    automation_dir.mkdir(parents=True, exist_ok=True)
    candidate = manifest.get("probe_candidate") if isinstance(manifest.get("probe_candidate"), dict) else {}
    project = str(manifest.get("generated_from_project") or repo_root.name)
    slug = _slugify(project)
    feedback_dir = repo_root / "fuzz-records" / "probe-feedback"
    feedback_dir.mkdir(parents=True, exist_ok=True)
    feedback_json_path = feedback_dir / f"{slug}-probe-feedback.json"
    feedback_plan_path = feedback_dir / f"{slug}-probe-feedback.md"

    run_dir = str(manifest.get("probe_plan_path") or manifest_path)
    entry = {
        "key": f"{action['action_code']}:{run_dir}",
        "action_code": action["action_code"],
        "run_dir": run_dir,
        "report_path": str(manifest.get("probe_plan_path") or manifest_path),
        "outcome": f"probe-{action['reason']}",
        "recommended_action": action["recommended_action"],
        "candidate_id": candidate.get("candidate_id"),
        "entrypoint_path": candidate.get("entrypoint_path"),
        "bridge_reason": action["reason"],
        "status": "recorded",
        "lifecycle": "queued",
    }
    created, registry_path = _record_refiner_entry(automation_dir, registry_name=action["registry_name"], entry=entry)

    feedback = {
        "bridged": True,
        "generated_from_project": project,
        "source_probe_manifest": str(manifest_path),
        "action_code": action["action_code"],
        "bridge_reason": action["reason"],
        "registry_name": action["registry_name"],
        "registry_path": str(registry_path),
        "recommended_action": action["recommended_action"],
        "candidate_id": candidate.get("candidate_id"),
        "entrypoint_path": candidate.get("entrypoint_path"),
        "build_probe_status": (manifest.get("build_probe_result") or {}).get("status") if isinstance(manifest.get("build_probe_result"), dict) else None,
        "smoke_probe_status": (manifest.get("smoke_probe_result") or {}).get("status") if isinstance(manifest.get("smoke_probe_result"), dict) else None,
        "feedback_json_path": str(feedback_json_path),
        "feedback_plan_path": str(feedback_plan_path),
        "updated": [action["updated_label"]] if created else [],
        "created": created,
    }
    feedback_json_path.write_text(json.dumps(feedback, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    feedback_plan_path.write_text(render_probe_feedback_markdown(feedback), encoding="utf-8")
    return feedback
