from __future__ import annotations

from pathlib import Path

from .profile_validation import validate_target_profile


def _summarize_target_adapter(profile: dict[str, object] | None) -> dict[str, object] | None:
    if not isinstance(profile, dict):
        return None
    target = profile.get("target") if isinstance(profile.get("target"), dict) else {}
    adapter = target.get("adapter") if isinstance(target.get("adapter"), dict) else {}
    if not adapter:
        return None
    return {
        "key": adapter.get("key"),
        "notification_label": adapter.get("notification_label"),
        "report_target": adapter.get("report_target"),
        "build_command": adapter.get("build_command"),
        "smoke_binary_relpath": adapter.get("smoke_binary_relpath"),
        "smoke_command_prefix": adapter.get("smoke_command_prefix"),
        "fuzz_command": adapter.get("fuzz_command"),
        "editable_harness_relpath": adapter.get("editable_harness_relpath"),
        "fuzz_entrypoint_names": adapter.get("fuzz_entrypoint_names"),
        "guard_condition": adapter.get("guard_condition"),
        "guard_return_statement": adapter.get("guard_return_statement"),
        "target_call_todo": adapter.get("target_call_todo"),
        "resource_lifetime_hint": adapter.get("resource_lifetime_hint"),
    }


def build_target_profile_summary(
    profile: dict[str, object] | None,
    profile_path: Path | None,
) -> dict[str, object] | None:
    if profile is None or profile_path is None:
        return None
    meta = profile.get("meta") if isinstance(profile.get("meta"), dict) else {}
    target = profile.get("target") if isinstance(profile.get("target"), dict) else {}
    current_campaign = target.get("current_campaign") if isinstance(target.get("current_campaign"), dict) else {}
    stages = profile.get("stages") if isinstance(profile.get("stages"), list) else []
    load_error = profile.get("__load_error__") if isinstance(profile.get("__load_error__"), str) else None
    validation = validate_target_profile(profile)
    return {
        "name": meta.get("name") or profile_path.stem,
        "path": str(profile_path),
        "project": target.get("project"),
        "primary_mode": current_campaign.get("primary_mode"),
        "primary_binary": current_campaign.get("primary_binary"),
        "stage_count": len(stages),
        "schema_version": profile.get("schema_version"),
        "load_status": "degraded" if load_error else "loaded",
        "load_error": load_error,
        "load_error_detail": profile.get("__load_error_detail__"),
        "validation_status": validation.get("status"),
        "validation_severity": validation.get("severity"),
        "validation_codes": validation.get("codes"),
        "validation_messages": validation.get("messages"),
        "adapter": _summarize_target_adapter(profile),
    }
