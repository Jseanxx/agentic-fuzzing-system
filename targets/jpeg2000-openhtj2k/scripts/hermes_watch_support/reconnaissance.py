from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

SOURCE_GLOBS = ("*.c", "*.cc", "*.cpp", "*.cxx", "*.h", "*.hpp")
STAGE_RULES = [
    ("parse", "parse-main", "shallow"),
    ("header", "parse-header", "shallow"),
    ("decode", "decode", "medium"),
    ("transform", "transform", "deep"),
    ("cleanup", "cleanup-finalize", "deep"),
    ("final", "cleanup-finalize", "deep"),
]
ENTRYPOINT_KEYWORDS = ("parse", "decode", "load", "read", "process", "cleanup", "final")


def detect_build_system(repo_root: Path) -> str:
    if (repo_root / "CMakeLists.txt").exists():
        return "cmake"
    if (repo_root / "meson.build").exists():
        return "meson"
    if (repo_root / "Makefile").exists() or (repo_root / "makefile").exists():
        return "make"
    if (repo_root / "configure.ac").exists() or (repo_root / "configure").exists():
        return "autotools"
    return "unknown"


def collect_source_files(repo_root: Path, *, limit: int = 200) -> list[Path]:
    files: list[Path] = []
    for pattern in SOURCE_GLOBS:
        files.extend(repo_root.rglob(pattern))
    files = [path for path in files if path.is_file()]
    files.sort(key=lambda p: len(p.parts))
    return files[:limit]


def infer_project_name(repo_root: Path) -> str:
    return repo_root.name.replace("_", "-")


def infer_stage_candidates(source_files: list[Path]) -> list[dict[str, object]]:
    stage_map: dict[str, dict[str, object]] = {}
    for path in source_files:
        name = path.stem.lower()
        rel = str(path)
        for keyword, stage_id, stage_class in STAGE_RULES:
            if keyword in name or keyword in rel.lower():
                item = stage_map.setdefault(
                    stage_id,
                    {
                        "id": stage_id,
                        "stage_class": stage_class,
                        "examples": [],
                    },
                )
                examples = item["examples"]
                assert isinstance(examples, list)
                if len(examples) < 3:
                    examples.append(rel)
    if not stage_map:
        stage_map["parse-main"] = {"id": "parse-main", "stage_class": "shallow", "examples": []}
    ordered: list[dict[str, object]] = []
    for depth_rank, stage_id in enumerate(sorted(stage_map), start=1):
        item = dict(stage_map[stage_id])
        item["depth_rank"] = depth_rank
        ordered.append(item)
    return ordered


def infer_entrypoint_candidates(source_files: list[Path], *, limit: int = 12) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for path in source_files:
        stem = path.stem.lower()
        if any(keyword in stem for keyword in ENTRYPOINT_KEYWORDS):
            rel = str(path)
            if rel not in seen:
                seen.add(rel)
                candidates.append(rel)
        if len(candidates) >= limit:
            break
    return candidates


def build_target_reconnaissance(repo_root: Path) -> dict[str, object]:
    source_files = collect_source_files(repo_root)
    rel_files = [str(path.relative_to(repo_root)) for path in source_files]
    stage_candidates = infer_stage_candidates([Path(path) for path in rel_files])
    entrypoints = infer_entrypoint_candidates([Path(path) for path in rel_files])
    return {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "repo_root": str(repo_root),
        "project_name": infer_project_name(repo_root),
        "build_system": detect_build_system(repo_root),
        "source_file_count": len(source_files),
        "sample_source_files": rel_files[:20],
        "entrypoint_candidates": entrypoints,
        "stage_candidates": stage_candidates,
        "notes": [
            "auto-draft only: requires human review before production use",
            "stage candidates inferred from filenames and shallow repository heuristics",
        ],
    }


def render_target_profile_auto_draft(recon: dict[str, object]) -> str:
    stage_candidates = recon.get("stage_candidates") if isinstance(recon.get("stage_candidates"), list) else []
    telemetry_names = [stage.get("id") for stage in stage_candidates if isinstance(stage, dict) and isinstance(stage.get("id"), str)]
    stage_file_map = {
        stage["id"]: list(stage.get("examples") or [])
        for stage in stage_candidates
        if isinstance(stage, dict) and isinstance(stage.get("id"), str)
    }
    draft = {
        "schema_version": "target-profile/v1",
        "meta": {
            "name": f"{recon.get('project_name')}-target-profile-auto-draft",
            "generated_by": "hermes-watch-recon",
            "generated_at": recon.get("generated_at"),
            "draft": True,
        },
        "target": {
            "project": recon.get("project_name"),
            "build_system": recon.get("build_system"),
            "current_campaign": {
                "primary_mode": "exploratory-auto-draft",
                "primary_binary": None,
            },
        },
        "stages": [
            {
                "id": stage.get("id"),
                "depth_rank": stage.get("depth_rank"),
                "stage_class": stage.get("stage_class"),
                "expected_signals": [],
            }
            for stage in stage_candidates
            if isinstance(stage, dict)
        ],
        "hotspots": {
            "functions": [],
            "files": [
                {
                    "path": example,
                    "stage": stage.get("id"),
                }
                for stage in stage_candidates
                if isinstance(stage, dict)
                for example in list(stage.get("examples") or [])[:1]
            ],
        },
        "triggers": {},
        "actions": {},
        "telemetry": {
            "stage_counters": {
                "enabled": True,
                "names": telemetry_names,
            },
            "stack_tagging": {
                "enabled": True,
                "file_to_stage_map": True,
                "stage_file_map": stage_file_map,
            },
        },
        "notes": {
            "auto_draft": True,
            "entrypoint_candidates": recon.get("entrypoint_candidates") or [],
            "review_required": True,
        },
    }
    if yaml is None:
        return json.dumps(draft, indent=2, sort_keys=True) + "\n"
    return yaml.safe_dump(draft, sort_keys=False, allow_unicode=True)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "target"


def write_target_profile_auto_draft(repo_root: Path) -> dict[str, object]:
    recon = build_target_reconnaissance(repo_root)
    draft_dir = repo_root / "fuzz-records" / "profiles" / "auto-drafts"
    draft_dir.mkdir(parents=True, exist_ok=True)
    slug = _slugify(str(recon.get("project_name") or repo_root.name))
    draft_path = draft_dir / f"{slug}-target-profile-draft.yaml"
    manifest_path = draft_dir / f"{slug}-target-recon.json"
    draft_path.write_text(render_target_profile_auto_draft(recon), encoding="utf-8")
    manifest_path.write_text(json.dumps(recon, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "draft_profile_path": str(draft_path),
        "recon_manifest_path": str(manifest_path),
        "project_name": recon.get("project_name"),
        "build_system": recon.get("build_system"),
        "source_file_count": recon.get("source_file_count"),
        "stage_candidate_count": len(recon.get("stage_candidates") or []),
        "entrypoint_candidate_count": len(recon.get("entrypoint_candidates") or []),
    }
