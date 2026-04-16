from __future__ import annotations

from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - exercised indirectly when dependency is missing at runtime
    yaml = None


DEFAULT_TARGET_PROFILE_REL = Path("fuzz-records/profiles/openhtj2k-target-profile-v1.yaml")


def resolve_target_profile_path(repo_root: Path, explicit_path: Path | None) -> Path | None:
    if explicit_path is not None:
        return explicit_path.resolve()
    default_path = (repo_root / DEFAULT_TARGET_PROFILE_REL).resolve()
    if default_path.exists():
        return default_path
    return None


def _degraded_target_profile(profile_path: Path | None, *, error_code: str, error_detail: str | None = None) -> dict[str, object]:
    degraded = {
        "meta": {},
        "target": {"current_campaign": {}},
        "stages": [],
        "hotspots": {},
        "telemetry": {},
        "triggers": {},
        "actions": {},
        "__load_error__": error_code,
    }
    if profile_path is not None:
        degraded["__profile_path__"] = str(profile_path)
    if error_detail:
        degraded["__load_error_detail__"] = error_detail
    return degraded


def _normalize_target_profile_shape(data: dict[str, object], profile_path: Path | None) -> dict[str, object]:
    normalized = dict(data)
    shape_errors: list[str] = []

    if not isinstance(normalized.get("meta"), dict):
        if "meta" in normalized:
            shape_errors.append("meta")
        normalized["meta"] = {}
    if not isinstance(normalized.get("target"), dict):
        if "target" in normalized:
            shape_errors.append("target")
        normalized["target"] = {}
    target = normalized["target"]
    assert isinstance(target, dict)
    if not isinstance(target.get("current_campaign"), dict):
        if "current_campaign" in target:
            shape_errors.append("target.current_campaign")
        target["current_campaign"] = {}
    if not isinstance(normalized.get("stages"), list):
        if "stages" in normalized:
            shape_errors.append("stages")
        normalized["stages"] = []
    if not isinstance(normalized.get("hotspots"), dict):
        if "hotspots" in normalized:
            shape_errors.append("hotspots")
        normalized["hotspots"] = {}
    if not isinstance(normalized.get("telemetry"), dict):
        if "telemetry" in normalized:
            shape_errors.append("telemetry")
        normalized["telemetry"] = {}
    if not isinstance(normalized.get("triggers"), dict):
        if "triggers" in normalized:
            shape_errors.append("triggers")
        normalized["triggers"] = {}
    if not isinstance(normalized.get("actions"), dict):
        if "actions" in normalized:
            shape_errors.append("actions")
        normalized["actions"] = {}

    if shape_errors:
        degraded = _degraded_target_profile(
            profile_path,
            error_code="invalid-profile-shape",
            error_detail=",".join(shape_errors),
        )
        degraded.update(normalized)
        degraded["__shape_errors__"] = shape_errors
        return degraded
    return normalized


def load_target_profile(profile_path: Path | None) -> dict[str, object] | None:
    if profile_path is None:
        return None
    if not profile_path.exists():
        return _degraded_target_profile(profile_path, error_code="missing-file")
    if yaml is None:
        return _degraded_target_profile(profile_path, error_code="yaml-unavailable")
    try:
        data = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return _degraded_target_profile(profile_path, error_code="yaml-parse-error", error_detail=str(exc))
    if data is None:
        return _normalize_target_profile_shape({}, profile_path)
    if not isinstance(data, dict):
        return _degraded_target_profile(
            profile_path,
            error_code="invalid-top-level-type",
            error_detail=type(data).__name__,
        )
    return _normalize_target_profile_shape(data, profile_path)
