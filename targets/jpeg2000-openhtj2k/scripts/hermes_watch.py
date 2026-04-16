#!/usr/bin/env python3
"""Stage-1 OpenHTJ2K fuzz watcher for Hermes.

Runs build/smoke/fuzz steps, parses libFuzzer output for crash and progress
signals, writes FUZZING_REPORT.md, and optionally sends a compact Discord
webhook notification via DISCORD_WEBHOOK_URL.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Callable

if __package__ in {None, ""}:
    _SCRIPT_DIR = Path(__file__).resolve().parent
    _REPO_ROOT = _SCRIPT_DIR.parent
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

from scripts.hermes_watch_support.profile_loading import (
    DEFAULT_TARGET_PROFILE_REL,
    load_target_profile as load_target_profile_impl,
    resolve_target_profile_path as resolve_target_profile_path_impl,
)
from scripts.hermes_watch_support.profile_summary import build_target_profile_summary as build_target_profile_summary_impl
from scripts.hermes_watch_support.profile_validation import (
    runtime_target_profile as runtime_target_profile_impl,
    validate_target_profile as validate_target_profile_impl,
)
from scripts.hermes_watch_support.reconnaissance import (
    build_target_reconnaissance as build_target_reconnaissance_impl,
    write_target_profile_auto_draft as write_target_profile_auto_draft_impl,
)
from scripts.hermes_watch_support.harness_draft import (
    build_harness_candidate_draft as build_harness_candidate_draft_impl,
    write_harness_candidate_draft as write_harness_candidate_draft_impl,
)
from scripts.hermes_watch_support.harness_evaluation import (
    build_harness_evaluation_draft as build_harness_evaluation_draft_impl,
    write_harness_evaluation_draft as write_harness_evaluation_draft_impl,
)
from scripts.hermes_watch_support.harness_skeleton import (
    build_harness_skeleton_draft as build_harness_skeleton_draft_impl,
    write_harness_skeleton_draft as write_harness_skeleton_draft_impl,
    run_harness_skeleton_closure as run_harness_skeleton_closure_impl,
    write_harness_correction_policy as write_harness_correction_policy_impl,
    write_harness_apply_candidate as write_harness_apply_candidate_impl,
)
from scripts.hermes_watch_support.harness_probe import (
    build_harness_probe_draft as build_harness_probe_draft_impl,
    run_short_harness_probe as run_short_harness_probe_impl,
)
from scripts.hermes_watch_support.harness_feedback import bridge_harness_probe_feedback as bridge_harness_probe_feedback_impl
from scripts.hermes_watch_support.harness_routing import (
    build_probe_routing_decision as build_probe_routing_decision_impl,
    write_probe_routing_handoff as write_probe_routing_handoff_impl,
    select_next_ranked_candidate as select_next_ranked_candidate_impl,
)
from scripts.hermes_watch_support.harness_candidates import (
    update_ranked_candidate_registry as update_ranked_candidate_registry_impl,
    render_ranked_candidate_markdown as render_ranked_candidate_markdown_impl,
)
from scripts.hermes_watch_support.target_adapter import (
    TargetAdapter,
    get_target_adapter,
    build_target_adapter_regression_smoke_matrix,
    write_target_adapter_regression_smoke_matrix,
)
from scripts.hermes_watch_support.llm_evidence import (
    build_llm_evidence_packet as build_llm_evidence_packet_impl,
    write_llm_evidence_packet as write_llm_evidence_packet_impl,
)

REFINER_QUEUE_REGISTRY_SPECS: list[tuple[str, str]] = [
    ("mode_refinements.json", "shift_weight_to_deeper_harness"),
    ("slow_lane_candidates.json", "split_slow_lane"),
    ("corpus_refinements.json", "minimize_and_reseed"),
    ("harness_review_queue.json", "halt_and_review_harness"),
    ("duplicate_crash_reviews.json", "review_duplicate_crash_replay"),
    ("harness_correction_regeneration_queue.json", "regenerate_harness_correction"),
]

REFINER_ORCHESTRATION_SPECS: dict[str, dict[str, object]] = {
    "shift_weight_to_deeper_harness": {
        "dispatch_channel": "subagent",
        "goal": "Review the latest shallow-heavy run and propose a deeper harness/mode shift plan.",
        "toolsets": ["terminal", "file"],
        "skills": ["subagent-driven-development"],
        "verification": [
            "Confirm the target profile primary mode and the proposed next mode align.",
            "Verify the change does not regress smoke coverage or basic decode validity.",
            "Keep the output low-risk: recommendation, patch plan, or command plan only.",
        ],
    },
    "split_slow_lane": {
        "dispatch_channel": "cron",
        "goal": "Prepare a slow-lane seed isolation and timeout triage plan for the latest run.",
        "cron_schedule": "30m",
        "cron_deliver": "local",
        "cron_repeat": 1,
        "verification": [
            "Identify which seeds or directories should move into a slow lane without deleting anything.",
            "List the exact commands or manual steps required for verification.",
            "Do not delete or overwrite corpus entries automatically.",
        ],
    },
    "minimize_and_reseed": {
        "dispatch_channel": "cron",
        "goal": "Prepare a conservative corpus minimization and reseed plan from the latest campaign state.",
        "cron_schedule": "30m",
        "cron_deliver": "local",
        "cron_repeat": 1,
        "verification": [
            "Produce self-contained maintenance instructions for a fresh Hermes session.",
            "Keep the workflow reversible until a human or later runner validates the result.",
            "Record post-action checks for corpus size, coverage, and crash-family retention.",
        ],
    },
    "halt_and_review_harness": {
        "dispatch_channel": "subagent",
        "goal": "Review harness stability and produce a deterministic debugging checklist for the suspicious run.",
        "toolsets": ["terminal", "file"],
        "skills": ["subagent-driven-development"],
        "bridge_timeout_seconds": 600,
        "verification": [
            "Focus on harness determinism, shallow duplicate-heavy crashes, and reproducibility signals.",
            "Do not modify code directly unless a later reviewer approves the exact patch.",
            "End with concrete follow-up tasks the main operator can execute safely.",
        ],
    },
    "review_duplicate_crash_replay": {
        "dispatch_channel": "subagent",
        "goal": "Review a repeated duplicate crash family and prepare a low-risk replay/minimization triage plan grounded in first-seen vs latest evidence.",
        "toolsets": ["terminal", "file"],
        "skills": ["subagent-driven-development"],
        "bridge_timeout_seconds": 600,
        "verification": [
            "Compare first-seen and latest duplicate evidence before proposing next steps.",
            "Prefer replay, minimization, and artifact-preserving triage over code edits.",
            "End with concrete bounded commands or checks the operator can run safely.",
        ],
    },
    "regenerate_harness_correction": {
        "dispatch_channel": "subagent",
        "goal": "Review the aborted guarded-apply attempt and regenerate a safer harness-correction plan with a bounded next step.",
        "toolsets": ["terminal", "file"],
        "skills": ["subagent-driven-development"],
        "verification": [
            "Explain why the previous guarded apply aborted or rolled back repeatedly.",
            "Produce a lower-risk correction/regeneration plan rather than editing code directly.",
            "End with concrete verification steps and bounded follow-up options for the operator.",
        ],
    },
}


FUZZ_RE = re.compile(
    r"cov:\s*(?P<cov>\d+).*?ft:\s*(?P<ft>\d+).*?corp:\s*(?P<corp_units>\d+)/(?P<corp_size>\S+)",
    re.IGNORECASE,
)
EXEC_RE = re.compile(r"exec/s:\s*(?P<execs>\d+)", re.IGNORECASE)
RSS_RE = re.compile(r"rss:\s*(?P<rss>\S+)", re.IGNORECASE)
CRASH_RE = re.compile(
    r"(ERROR: AddressSanitizer|ERROR: LeakSanitizer|ERROR: UndefinedBehaviorSanitizer|ERROR: libFuzzer|Test unit written to|SUMMARY: AddressSanitizer|SUMMARY: LeakSanitizer|SUMMARY: UndefinedBehaviorSanitizer)",
    re.IGNORECASE,
)
TIMEOUT_RE = re.compile(r"(timeout|deadly signal|libFuzzer: timeout)", re.IGNORECASE)
LOCATION_RE = re.compile(r"(?P<path>[^\s:'\"]+\.(?:c|cc|cpp|cxx|h|hpp|py)):(?P<line>\d+)(?::\d+)?")
ARTIFACT_RE = re.compile(r"Test unit written to\s+(?P<path>\S+)")
SUMMARY_RE = re.compile(r"SUMMARY:\s+(?:AddressSanitizer|LeakSanitizer|UndefinedBehaviorSanitizer|libFuzzer):\s*(?P<summary>.+)", re.IGNORECASE)
SMOKE_INPUT_RE = re.compile(r'"(?P<path>[^"\n]+\.(?:j2k|jp2|jph))"')
STACK_FRAME_RE = re.compile(
    r"#(?P<index>\d+)\s+0x[0-9a-fA-F]+\s+in\s+(?P<function>.+?)\s+(?P<path>/[^:\s]+\.(?:c|cc|cpp|cxx|h|hpp|py)):(?P<line>\d+)(?::(?P<column>\d+))?"
)
CRASH_CONTEXT_LINE_LIMIT = 20
LEAK_ALLOCATOR_FRAME_HINTS = (
    "posix_memalign",
    "malloc",
    "calloc",
    "realloc",
    "operator new",
    "alignedlargepool::alloc",
)
LEAK_ALLOCATOR_PATH_HINTS = (
    "/source/core/common/",
    "/source/core/memory/",
)

BRIDGE_SCRIPT_TIMEOUT_SECONDS = 120
PROBE_COMMAND_TIMEOUT_SECONDS = 120


class Metrics:
    def __init__(self) -> None:
        self.cov: int | None = None
        self.ft: int | None = None
        self.corp_units: int | None = None
        self.corp_size: str | None = None
        self.execs: int | None = None
        self.rss: str | None = None
        self.crash = False
        self.timeout = False
        self.last_progress_at = time.monotonic()
        self.top_crash_lines: list[str] = []

    def update_from_line(self, line: str) -> None:
        fuzz_match = FUZZ_RE.search(line)
        if fuzz_match:
            new_cov = int(fuzz_match.group("cov"))
            new_ft = int(fuzz_match.group("ft"))
            new_corp_units = int(fuzz_match.group("corp_units"))
            if (
                self.cov is None
                or new_cov > self.cov
                or self.ft is None
                or new_ft > self.ft
                or self.corp_units is None
                or new_corp_units > self.corp_units
            ):
                self.last_progress_at = time.monotonic()
            self.cov = new_cov
            self.ft = new_ft
            self.corp_units = new_corp_units
            self.corp_size = fuzz_match.group("corp_size")

        exec_match = EXEC_RE.search(line)
        if exec_match:
            self.execs = int(exec_match.group("execs"))

        rss_match = RSS_RE.search(line)
        if rss_match:
            self.rss = rss_match.group("rss")

        if CRASH_RE.search(line):
            self.crash = True
            crash_line = line.rstrip()
            if len(self.top_crash_lines) < CRASH_CONTEXT_LINE_LIMIT:
                self.top_crash_lines.append(crash_line)
            else:
                wants_summary = SUMMARY_RE.search(line) and not any(
                    SUMMARY_RE.search(existing) for existing in self.top_crash_lines
                )
                wants_artifact = ARTIFACT_RE.search(line) and not any(
                    ARTIFACT_RE.search(existing) for existing in self.top_crash_lines
                )
                if wants_summary or wants_artifact:
                    replace_index = len(self.top_crash_lines) - 1
                    for index in range(len(self.top_crash_lines) - 1, -1, -1):
                        existing = self.top_crash_lines[index]
                        if not SUMMARY_RE.search(existing) and not ARTIFACT_RE.search(existing):
                            replace_index = index
                            break
                    self.top_crash_lines[replace_index] = crash_line
        elif self.crash and len(self.top_crash_lines) < CRASH_CONTEXT_LINE_LIMIT:
            stripped = line.lstrip()
            if (
                stripped.startswith("#")
                or LOCATION_RE.search(line)
                or "Direct leak of" in line
            ):
                self.top_crash_lines.append(line.rstrip())

        if TIMEOUT_RE.search(line):
            self.timeout = True
            if len(self.top_crash_lines) < 12:
                self.top_crash_lines.append(line.rstrip())


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def resolve_target_profile_path(repo_root: Path, explicit_path: Path | None) -> Path | None:
    return resolve_target_profile_path_impl(repo_root, explicit_path)


def load_target_profile(profile_path: Path | None) -> dict[str, object] | None:
    return load_target_profile_impl(profile_path)


def validate_target_profile(profile: dict[str, object] | None) -> dict[str, object]:
    return validate_target_profile_impl(profile)


def runtime_target_profile(profile: dict[str, object] | None) -> dict[str, object] | None:
    return runtime_target_profile_impl(profile)


def build_target_profile_summary(
    profile: dict[str, object] | None,
    profile_path: Path | None,
) -> dict[str, object] | None:
    return build_target_profile_summary_impl(profile, profile_path)


def build_target_reconnaissance(repo_root: Path) -> dict[str, object]:
    return build_target_reconnaissance_impl(repo_root)


def write_target_profile_auto_draft(repo_root: Path) -> dict[str, object]:
    return write_target_profile_auto_draft_impl(repo_root)


def build_harness_candidate_draft(repo_root: Path) -> dict[str, object]:
    return build_harness_candidate_draft_impl(repo_root)


def write_harness_candidate_draft(repo_root: Path) -> dict[str, object]:
    return write_harness_candidate_draft_impl(repo_root)


def build_harness_evaluation_draft(repo_root: Path) -> dict[str, object]:
    return build_harness_evaluation_draft_impl(repo_root)


def write_harness_evaluation_draft(repo_root: Path) -> dict[str, object]:
    return write_harness_evaluation_draft_impl(repo_root)


def build_harness_skeleton_draft(repo_root: Path) -> dict[str, object]:
    return build_harness_skeleton_draft_impl(repo_root)


def write_harness_skeleton_draft(repo_root: Path) -> dict[str, object]:
    return write_harness_skeleton_draft_impl(repo_root)


def run_harness_skeleton_closure(
    repo_root: Path,
    *,
    probe_runner: Callable[[list[str], Path], tuple[int, str]] | None = None,
) -> dict[str, object]:
    return run_harness_skeleton_closure_impl(repo_root, probe_runner=probe_runner or run_probe_command)


def write_harness_correction_policy(repo_root: Path) -> dict[str, object]:
    return write_harness_correction_policy_impl(repo_root)


def write_harness_apply_candidate(repo_root: Path) -> dict[str, object]:
    return write_harness_apply_candidate_impl(repo_root)


def _resolve_runtime_target_adapter(repo_root: Path) -> TargetAdapter:
    target_profile_path = resolve_target_profile_path(repo_root, None)
    loaded_target_profile = load_target_profile(target_profile_path)
    target_profile_summary = build_target_profile_summary(loaded_target_profile, target_profile_path)
    return get_target_adapter(target_profile_summary)


def write_runtime_target_adapter_regression_smoke_matrix(repo_root: Path) -> dict[str, object]:
    target_profile_path = resolve_target_profile_path(repo_root, None)
    loaded_target_profile = load_target_profile(target_profile_path)
    target_profile_summary = build_target_profile_summary(loaded_target_profile, target_profile_path)
    return write_target_adapter_regression_smoke_matrix(repo_root, target_profile_summary)


def build_llm_evidence_packet(repo_root: Path) -> dict[str, object]:
    return build_llm_evidence_packet_impl(repo_root)


def write_llm_evidence_packet(repo_root: Path) -> dict[str, object]:
    return write_llm_evidence_packet_impl(repo_root)


def refresh_llm_evidence_packet_best_effort(repo_root: Path) -> dict[str, object] | None:
    try:
        return write_llm_evidence_packet(repo_root)
    except Exception as exc:  # pragma: no cover - defensive telemetry path
        print(f"[warn] failed to refresh llm evidence packet: {exc}", file=sys.stderr)
        return None


def queue_latest_evidence_review_followup(repo_root: Path) -> dict[str, object]:
    evidence_dir = repo_root / "fuzz-records" / "llm-evidence"
    evidence_paths = sorted(evidence_dir.glob("*-llm-evidence.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not evidence_paths:
        return {"queued": False, "reason": "no-llm-evidence-packet"}
    evidence_path = evidence_paths[0]
    packet = load_registry(evidence_path, {})
    action_code = str(packet.get("suggested_action_code") or "")
    candidate_route = str(packet.get("suggested_candidate_route") or "")
    if action_code != "halt_and_review_harness" or candidate_route != "review-current-candidate":
        return {
            "queued": False,
            "reason": "evidence-not-review-route",
            "suggested_action_code": action_code,
            "suggested_candidate_route": candidate_route,
            "llm_evidence_json_path": str(evidence_path),
        }

    current_status = packet.get("current_status") if isinstance(packet.get("current_status"), dict) else {}
    run_dir = str(current_status.get("run_dir") or "/runs/evidence-review")
    report_path = str(current_status.get("report") or "")
    project = str(packet.get("generated_from_project") or repo_root.name)
    crash_fingerprint = str(current_status.get("crash_fingerprint") or "")
    dedup_suffix = crash_fingerprint or slugify_run_dir(run_dir)
    recommended_action = " | ".join(
        part for part in [
            str(packet.get("objective_routing_linkage_summary") or "").strip(),
            str(packet.get("top_failure_reason_narrative") or "").strip(),
            str(current_status.get("policy_recommended_action") or "").strip(),
        ]
        if part
    )
    automation_dir = repo_root / "fuzz-artifacts" / "automation"
    entry = {
        "key": f"halt_and_review_harness:{project}:{dedup_suffix}",
        "action_code": "halt_and_review_harness",
        "status": "recorded",
        "run_dir": run_dir,
        "report_path": report_path,
        "outcome": str(current_status.get("outcome") or "review"),
        "recommended_action": recommended_action or "review latest deep crash candidate",
        "current_mode": current_status.get("target_profile_primary_mode"),
        "next_mode": "triage",
        "selected_candidate_id": current_status.get("selected_candidate_id") or f"evidence-review:{slugify_run_dir(run_dir)}",
        "selected_target_stage": current_status.get("crash_stage"),
        "generated_from_project": project,
        "candidate_route": candidate_route,
        "llm_evidence_json_path": str(evidence_path),
        "llm_evidence_markdown_path": str(packet.get("llm_evidence_markdown_path") or ""),
        "crash_fingerprint": crash_fingerprint,
        "policy_action_code": current_status.get("policy_action_code"),
        "queue_reason": "evidence-review-route",
    }
    result = record_refiner_entry(
        automation_dir,
        registry_name="harness_review_queue.json",
        unique_key="key",
        entry=entry,
    )
    revived = False
    if not bool(result.get("created")):
        registry_path = automation_dir / "harness_review_queue.json"
        registry = load_registry(registry_path, {"entries": []})
        entries = registry.get("entries") if isinstance(registry.get("entries"), list) else []
        existing = next((item for item in entries if isinstance(item, dict) and item.get("key") == entry["key"]), None)
        if isinstance(existing, dict) and str(existing.get("bridge_status") or "") == "failed":
            existing.update(entry)
            existing["status"] = "recorded"
            for field in [
                "completed_at",
                "executor_plan_path",
                "orchestration_status",
                "orchestration_manifest_path",
                "subagent_prompt_path",
                "cron_prompt_path",
                "orchestration_prepared_at",
                "dispatch_status",
                "dispatch_channel",
                "delegate_task_request_path",
                "cronjob_request_path",
                "dispatch_prepared_at",
                "bridge_status",
                "bridge_channel",
                "bridge_script_path",
                "bridge_prompt_path",
                "bridge_prepared_at",
                "launch_status",
                "bridge_exit_code",
                "bridge_launch_log_path",
                "bridge_launched_at",
                "delegate_session_id",
                "delegate_status",
                "delegate_artifact_path",
                "delegate_summary",
                "bridge_result_summary",
                "lifecycle",
            ]:
                existing.pop(field, None)
            sync_refiner_lifecycle(existing)
            save_registry(registry_path, registry)
            revived = True
    return {
        "queued": True,
        "created": bool(result.get("created")),
        "revived": revived,
        "count": int(result.get("count") or 0),
        "action_code": "halt_and_review_harness",
        "candidate_route": candidate_route,
        "path": str(automation_dir / "harness_review_queue.json"),
        "llm_evidence_json_path": str(evidence_path),
    }


def run_latest_evidence_review_followup_chain(repo_root: Path) -> dict[str, object]:
    automation_dir = repo_root / "fuzz-artifacts" / "automation"
    queue_result = queue_latest_evidence_review_followup(repo_root)
    if not queue_result.get("queued"):
        return {**queue_result, "prepared": False, "dispatched": False, "bridged": False, "launched": False}
    orchestration = prepare_next_refiner_orchestration(automation_dir, repo_root=repo_root)
    dispatch = dispatch_next_refiner_orchestration(automation_dir, repo_root=repo_root)
    bridge = bridge_next_refiner_dispatch(automation_dir, repo_root=repo_root)
    launch = launch_next_refiner_bridge(automation_dir, repo_root=repo_root)
    return {
        **queue_result,
        "prepared": orchestration is not None,
        "dispatched": dispatch is not None,
        "bridged": bridge is not None,
        "launched": launch is not None,
        "orchestration_status": (orchestration or {}).get("orchestration_status"),
        "dispatch_status": (dispatch or {}).get("dispatch_status"),
        "bridge_status": (bridge or {}).get("bridge_status"),
        "launch_status": (launch or {}).get("bridge_status"),
        "delegate_session_id": (launch or {}).get("delegate_session_id"),
        "delegate_artifact_path": (launch or {}).get("delegate_artifact_path"),
        "bridge_launch_log_path": (launch or {}).get("bridge_launch_log_path"),
        "orchestration_manifest_path": (orchestration or {}).get("manifest_path"),
        "delegate_task_request_path": (dispatch or {}).get("delegate_task_request_path"),
        "bridge_script_path": (bridge or {}).get("bridge_script_path"),
    }


def _latest_harness_apply_candidate_manifest(repo_root: Path) -> Path | None:
    apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
    manifests = sorted(apply_dir.glob("*-harness-apply-candidate.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    return manifests[0] if manifests else None


def _latest_harness_apply_result_manifest(repo_root: Path) -> Path | None:
    result_dir = repo_root / "fuzz-records" / "harness-apply-results"
    manifests = sorted(result_dir.glob("*-harness-apply-result.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    return manifests[0] if manifests else None


def _arm_harness_apply_bridge_from_manifest(manifest_path: Path, manifest: dict[str, object], *, repo_root: Path) -> dict[str, object]:
    delegate_request_path = Path(str(manifest.get("delegate_request_path") or "")) if manifest.get("delegate_request_path") else None
    bridge_dir = repo_root / "fuzz-records" / "harness-apply-bridge"
    bridge_dir.mkdir(parents=True, exist_ok=True)
    candidate_id = str(manifest.get("selected_candidate_id") or "candidate-1")
    project = str(manifest.get("generated_from_project") or repo_root.name)
    stem = f"{slugify_run_dir(project)}-{candidate_id}-harness-apply-bridge"
    prompt_path = bridge_dir / f"{stem}.txt"
    script_path = bridge_dir / f"{stem}.sh"
    if not delegate_request_path or not delegate_request_path.exists():
        manifest["bridge_status"] = "skipped"
        manifest["bridge_channel"] = None
        manifest["bridge_failure_reason"] = "missing-delegate-request"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {
            "selected_candidate_id": candidate_id,
            "bridge_status": "skipped",
            "bridge_channel": None,
            "apply_candidate_manifest_path": str(manifest_path),
        }
    prompt_text = build_delegate_bridge_prompt(action_code="guarded_harness_apply_candidate", request_path=delegate_request_path)
    prompt_path.write_text(prompt_text, encoding="utf-8")
    manifest.setdefault("delegate_expected_sections", ["## Patch Summary", "## Evidence Response", "## Verification Steps"])
    manifest.setdefault("delegate_quality_sections", ["## Patch Summary", "## Evidence Response", "## Verification Steps"])
    script_lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        f"PROMPT_PATH={shlex.quote(str(prompt_path))}",
        f"OUTPUT_PATH={shlex.quote(str(script_path.with_suffix('.log')))}",
        'PROMPT=$(cat "$PROMPT_PATH")',
        'hermes chat -q "$PROMPT" -Q -t delegation,file,terminal,skills -s subagent-driven-development | tee "$OUTPUT_PATH"',
    ]
    script_path.write_text("\n".join(script_lines) + "\n", encoding="utf-8")
    script_path.chmod(0o755)
    manifest["bridge_status"] = "armed"
    manifest["bridge_channel"] = "hermes-cli-delegate"
    manifest["bridge_prompt_path"] = str(prompt_path)
    manifest["bridge_script_path"] = str(script_path)
    manifest["bridge_prepared_at"] = dt.datetime.now().isoformat(timespec="seconds")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "selected_candidate_id": candidate_id,
        "bridge_status": "armed",
        "bridge_channel": "hermes-cli-delegate",
        "bridge_prompt_path": str(prompt_path),
        "bridge_script_path": str(script_path),
        "apply_candidate_manifest_path": str(manifest_path),
    }


def _recovery_route_spec(decision: str) -> dict[str, object]:
    if decision == "retry":
        return {
            "action_code": "requeue-guarded-apply-candidate",
            "registry_name": "harness_apply_retry_queue.json",
            "bridge_channel": "hermes-cli-delegate",
            "routing_disposition": "queued",
        }
    if decision == "hold":
        return {
            "action_code": "hold-guarded-apply-candidate",
            "registry_name": "harness_apply_hold_queue.json",
            "bridge_channel": None,
            "routing_disposition": "deferred",
        }
    if decision == "abort":
        return {
            "action_code": "abort-guarded-apply-candidate",
            "registry_name": "harness_apply_abort_queue.json",
            "bridge_channel": None,
            "routing_disposition": "terminal",
        }
    return {
        "action_code": "resolve-guarded-apply-candidate",
        "registry_name": "harness_apply_resolved.json",
        "bridge_channel": None,
        "routing_disposition": "resolved",
    }


def _reverse_linked_followup_routing_adjustment(manifest: dict[str, object], base_decision: str) -> dict[str, object]:
    failure_policy_status = str(manifest.get("recovery_followup_failure_policy_status") or "")
    failure_reason = str(manifest.get("recovery_followup_failure_policy_reason") or "")
    failure_action_code = str(manifest.get("recovery_followup_failure_action_code") or "")
    if base_decision != "retry" or failure_policy_status != "escalate":
        return {
            "decision": base_decision,
            "routing_risk_level": "normal" if base_decision != "retry" else "elevated",
            "routing_reverse_linkage_status": "not-applicable",
            "routing_reverse_linkage_reason": None,
        }
    hold_reasons = {"delegate-quality-gap", "candidate-review-required"}
    hold_actions = {"halt_and_review_harness"}
    adjusted_decision = "hold" if failure_reason in hold_reasons or failure_action_code in hold_actions else "abort"
    return {
        "decision": adjusted_decision,
        "routing_risk_level": "high" if adjusted_decision == "hold" else "critical",
        "routing_reverse_linkage_status": "override-from-followup-escalation",
        "routing_reverse_linkage_reason": failure_reason or failure_action_code or "followup-escalated",
    }


def _secondary_conflict_routing_adjustment(
    manifest: dict[str, object],
    result_payload: dict[str, object],
    base_decision: str,
) -> dict[str, object]:
    raw_status = result_payload.get("failure_reason_hunk_secondary_conflict_status")
    if raw_status is None:
        raw_status = manifest.get("failure_reason_hunk_secondary_conflict_status")
    status = str(raw_status or "none")
    raw_count = result_payload.get("failure_reason_hunk_secondary_conflict_count")
    if raw_count is None:
        raw_count = manifest.get("failure_reason_hunk_secondary_conflict_count")
    try:
        count = int(raw_count or 0)
    except (TypeError, ValueError):
        count = 0
    reasons = result_payload.get("failure_reason_hunk_secondary_conflict_reasons")
    if not isinstance(reasons, list):
        reasons = manifest.get("failure_reason_hunk_secondary_conflict_reasons")
    reasons = [str(reason) for reason in reasons or [] if str(reason).strip()]
    deferred_reason_codes = result_payload.get("failure_reason_hunk_deferred_reason_codes")
    if not isinstance(deferred_reason_codes, list):
        deferred_reason_codes = manifest.get("failure_reason_hunk_deferred_reason_codes")
    deferred_reason_codes = [str(code) for code in deferred_reason_codes or [] if str(code).strip()]
    severe_reason_codes = {
        "build-blocker",
        "build-log-memory-safety-signal",
        "harness-build-probe-failed",
        "guarded-apply-blocked",
    }
    severity = "none"
    actionability = "none"
    if base_decision != "retry":
        return {
            "decision": base_decision,
            "routing_risk_level": "normal",
            "routing_secondary_conflict_status": "not-applicable",
            "routing_secondary_conflict_severity": severity,
            "routing_secondary_conflict_actionability": actionability,
            "routing_secondary_conflict_count": count,
            "routing_secondary_conflict_reasons": reasons,
            "routing_secondary_conflict_deferred_reason_codes": deferred_reason_codes,
        }
    if status != "present" or count <= 0:
        return {
            "decision": base_decision,
            "routing_risk_level": "elevated",
            "routing_secondary_conflict_status": "none",
            "routing_secondary_conflict_severity": severity,
            "routing_secondary_conflict_actionability": actionability,
            "routing_secondary_conflict_count": 0,
            "routing_secondary_conflict_reasons": [],
            "routing_secondary_conflict_deferred_reason_codes": [],
        }
    severe = count >= 2 or any(code in severe_reason_codes for code in deferred_reason_codes)
    severity = "high" if severe else "medium"
    actionability = "corrective-regeneration" if severe else "review"
    adjusted_decision = "abort" if severe else "hold"
    return {
        "decision": adjusted_decision,
        "routing_risk_level": "critical" if severe else "high",
        "routing_secondary_conflict_status": "override-from-secondary-conflict-abort" if severe else "override-from-secondary-conflict-hold",
        "routing_secondary_conflict_severity": severity,
        "routing_secondary_conflict_actionability": actionability,
        "routing_secondary_conflict_count": count,
        "routing_secondary_conflict_reasons": reasons,
        "routing_secondary_conflict_deferred_reason_codes": deferred_reason_codes,
    }


def route_harness_apply_recovery(repo_root: Path) -> dict[str, object] | None:
    manifest_path = _latest_harness_apply_candidate_manifest(repo_root)
    if manifest_path is None:
        return None
    manifest = load_registry(manifest_path, {})
    result_path = Path(str(manifest.get("apply_result_manifest_path") or "")) if manifest.get("apply_result_manifest_path") else _latest_harness_apply_result_manifest(repo_root)
    if result_path is None or not result_path.exists():
        return None
    result_payload = load_registry(result_path, {})
    decision = str(result_payload.get("recovery_decision") or manifest.get("recovery_decision") or "")
    if not decision:
        return None
    reverse_linkage_adjustment = _reverse_linked_followup_routing_adjustment(manifest, decision)
    reverse_linkage_status = str(reverse_linkage_adjustment.get("routing_reverse_linkage_status") or "not-applicable")
    if reverse_linkage_status != "not-applicable":
        decision = str(reverse_linkage_adjustment.get("decision") or decision)
    secondary_conflict_adjustment = _secondary_conflict_routing_adjustment(manifest, result_payload, decision)
    if reverse_linkage_status == "not-applicable":
        decision = str(secondary_conflict_adjustment.get("decision") or decision)
        routing_risk_level = secondary_conflict_adjustment.get("routing_risk_level")
    else:
        routing_risk_level = reverse_linkage_adjustment.get("routing_risk_level")
    spec = _recovery_route_spec(decision)
    candidate_id = str(result_payload.get("selected_candidate_id") or manifest.get("selected_candidate_id") or "candidate-1")
    project = str(result_payload.get("generated_from_project") or manifest.get("generated_from_project") or repo_root.name)
    routing_dir = repo_root / "fuzz-records" / "harness-apply-recovery"
    routing_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{slugify_run_dir(project)}-{candidate_id}-harness-apply-recovery"
    routing_manifest_path = routing_dir / f"{stem}.json"
    routing_plan_path = routing_dir / f"{stem}.md"
    entry = {
        "key": f"{project}:{candidate_id}:{decision}",
        "generated_from_project": project,
        "selected_candidate_id": candidate_id,
        "target_file_path": result_payload.get("target_file_path") or manifest.get("target_file_path"),
        "apply_status": result_payload.get("apply_status") or manifest.get("apply_status"),
        "recovery_decision": decision,
        "recovery_status": result_payload.get("recovery_status") or manifest.get("recovery_status"),
        "recovery_summary": result_payload.get("recovery_summary") or manifest.get("recovery_summary"),
        "recovery_failure_streak": result_payload.get("recovery_failure_streak") or manifest.get("recovery_failure_streak") or 0,
        "recovery_attempt_count": result_payload.get("recovery_attempt_count") or manifest.get("recovery_attempt_count") or 0,
        "routing_risk_level": routing_risk_level,
        "routing_reverse_linkage_status": reverse_linkage_adjustment.get("routing_reverse_linkage_status"),
        "routing_reverse_linkage_reason": reverse_linkage_adjustment.get("routing_reverse_linkage_reason"),
        "routing_secondary_conflict_status": secondary_conflict_adjustment.get("routing_secondary_conflict_status"),
        "routing_secondary_conflict_severity": secondary_conflict_adjustment.get("routing_secondary_conflict_severity"),
        "routing_secondary_conflict_actionability": secondary_conflict_adjustment.get("routing_secondary_conflict_actionability"),
        "routing_secondary_conflict_count": secondary_conflict_adjustment.get("routing_secondary_conflict_count"),
        "routing_secondary_conflict_reasons": secondary_conflict_adjustment.get("routing_secondary_conflict_reasons"),
        "routing_secondary_conflict_deferred_reason_codes": secondary_conflict_adjustment.get("routing_secondary_conflict_deferred_reason_codes"),
        "action_code": spec.get("action_code"),
        "registry_name": spec.get("registry_name"),
        "bridge_channel": spec.get("bridge_channel"),
        "routing_disposition": spec.get("routing_disposition"),
        "apply_candidate_manifest_path": str(manifest_path),
        "apply_result_manifest_path": str(result_path),
        "recovery_route_manifest_path": str(routing_manifest_path),
        "recovery_route_plan_path": str(routing_plan_path),
    }
    routing_manifest_path.write_text(json.dumps(entry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    routing_plan_path.write_text(
        "\n".join(
            [
                "# Harness Apply Recovery Routing",
                "",
                f"- project: {project}",
                f"- selected_candidate_id: {candidate_id}",
                f"- apply_status: {entry.get('apply_status')}",
                f"- recovery_decision: {decision}",
                f"- recovery_status: {entry.get('recovery_status')}",
                f"- recovery_failure_streak: {entry.get('recovery_failure_streak')}",
                f"- action_code: {entry.get('action_code')}",
                f"- registry_name: {entry.get('registry_name')}",
                f"- bridge_channel: {entry.get('bridge_channel')}",
                f"- routing_risk_level: {entry.get('routing_risk_level')}",
                f"- routing_reverse_linkage_status: {entry.get('routing_reverse_linkage_status')}",
                f"- routing_reverse_linkage_reason: {entry.get('routing_reverse_linkage_reason')}",
                f"- routing_secondary_conflict_status: {entry.get('routing_secondary_conflict_status')}",
                f"- routing_secondary_conflict_severity: {entry.get('routing_secondary_conflict_severity')}",
                f"- routing_secondary_conflict_actionability: {entry.get('routing_secondary_conflict_actionability')}",
                f"- routing_secondary_conflict_count: {entry.get('routing_secondary_conflict_count')}",
                f"- routing_secondary_conflict_deferred_reason_codes: {entry.get('routing_secondary_conflict_deferred_reason_codes')}",
                "",
                "## Routing Intent",
                "",
                f"- disposition: {entry.get('routing_disposition')}",
                f"- summary: {entry.get('recovery_summary')}",
            ]
        ) + "\n",
        encoding="utf-8",
    )
    automation_dir = repo_root / "fuzz-artifacts" / "automation"
    automation_dir.mkdir(parents=True, exist_ok=True)
    registry_path = automation_dir / str(spec.get("registry_name"))
    registry = load_registry(registry_path, {"entries": []})
    entries = registry.setdefault("entries", [])
    assert isinstance(entries, list)
    if not any(isinstance(existing, dict) and existing.get("key") == entry["key"] for existing in entries):
        entries.append(entry)
    save_registry(registry_path, registry)
    manifest["recovery_route_status"] = "routed"
    manifest["recovery_route_action_code"] = entry["action_code"]
    manifest["recovery_route_registry"] = str(registry_path)
    manifest["recovery_route_manifest_path"] = str(routing_manifest_path)
    manifest["recovery_route_plan_path"] = str(routing_plan_path)
    manifest["recovery_route_bridge_channel"] = entry["bridge_channel"]
    manifest["recovery_route_risk_level"] = entry.get("routing_risk_level")
    manifest["recovery_route_reverse_linkage_status"] = entry.get("routing_reverse_linkage_status")
    manifest["recovery_route_reverse_linkage_reason"] = entry.get("routing_reverse_linkage_reason")
    manifest["recovery_route_secondary_conflict_status"] = entry.get("routing_secondary_conflict_status")
    manifest["recovery_route_secondary_conflict_severity"] = entry.get("routing_secondary_conflict_severity")
    manifest["recovery_route_secondary_conflict_actionability"] = entry.get("routing_secondary_conflict_actionability")
    manifest["recovery_route_secondary_conflict_count"] = entry.get("routing_secondary_conflict_count")
    manifest["recovery_route_secondary_conflict_reasons"] = entry.get("routing_secondary_conflict_reasons")
    manifest["recovery_route_secondary_conflict_deferred_reason_codes"] = entry.get("routing_secondary_conflict_deferred_reason_codes")
    manifest["recovery_routed_at"] = dt.datetime.now().isoformat(timespec="seconds")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result_payload["recovery_route_status"] = "routed"
    result_payload["recovery_route_action_code"] = entry["action_code"]
    result_payload["recovery_route_registry"] = str(registry_path)
    result_payload["recovery_route_manifest_path"] = str(routing_manifest_path)
    result_payload["recovery_route_plan_path"] = str(routing_plan_path)
    result_payload["recovery_route_bridge_channel"] = entry["bridge_channel"]
    result_payload["recovery_route_risk_level"] = entry.get("routing_risk_level")
    result_payload["recovery_route_reverse_linkage_status"] = entry.get("routing_reverse_linkage_status")
    result_payload["recovery_route_reverse_linkage_reason"] = entry.get("routing_reverse_linkage_reason")
    result_payload["recovery_route_secondary_conflict_status"] = entry.get("routing_secondary_conflict_status")
    result_payload["recovery_route_secondary_conflict_severity"] = entry.get("routing_secondary_conflict_severity")
    result_payload["recovery_route_secondary_conflict_actionability"] = entry.get("routing_secondary_conflict_actionability")
    result_payload["recovery_route_secondary_conflict_count"] = entry.get("routing_secondary_conflict_count")
    result_payload["recovery_route_secondary_conflict_reasons"] = entry.get("routing_secondary_conflict_reasons")
    result_payload["recovery_route_secondary_conflict_deferred_reason_codes"] = entry.get("routing_secondary_conflict_deferred_reason_codes")
    result_payload["recovery_routed_at"] = manifest["recovery_routed_at"]
    result_path.write_text(json.dumps(result_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "selected_candidate_id": candidate_id,
        "recovery_decision": decision,
        "action_code": entry["action_code"],
        "registry_name": str(spec.get("registry_name")),
        "bridge_channel": entry["bridge_channel"],
        "routing_risk_level": entry.get("routing_risk_level"),
        "routing_reverse_linkage_status": entry.get("routing_reverse_linkage_status"),
        "routing_reverse_linkage_reason": entry.get("routing_reverse_linkage_reason"),
        "routing_secondary_conflict_status": entry.get("routing_secondary_conflict_status"),
        "routing_secondary_conflict_severity": entry.get("routing_secondary_conflict_severity"),
        "routing_secondary_conflict_actionability": entry.get("routing_secondary_conflict_actionability"),
        "routing_secondary_conflict_count": entry.get("routing_secondary_conflict_count"),
        "routing_secondary_conflict_reasons": entry.get("routing_secondary_conflict_reasons"),
        "routing_secondary_conflict_deferred_reason_codes": entry.get("routing_secondary_conflict_deferred_reason_codes"),
        "recovery_route_manifest_path": str(routing_manifest_path),
        "recovery_route_plan_path": str(routing_plan_path),
        "apply_candidate_manifest_path": str(manifest_path),
        "apply_result_manifest_path": str(result_path),
    }


def consume_harness_apply_recovery_queue(repo_root: Path) -> dict[str, object] | None:
    automation_dir = repo_root / "fuzz-artifacts" / "automation"
    registry_specs = [
        ("harness_apply_retry_queue.json", "retry"),
        ("harness_apply_hold_queue.json", "hold"),
        ("harness_apply_abort_queue.json", "abort"),
        ("harness_apply_resolved.json", "resolved"),
    ]
    for registry_name, decision in registry_specs:
        registry_path = automation_dir / registry_name
        registry = load_registry(registry_path, {"entries": []})
        entries = registry.setdefault("entries", [])
        assert isinstance(entries, list)
        entry = next((item for item in entries if isinstance(item, dict) and item.get("consumer_status") not in {"consumed", "rearmed-bridge", "parked-for-review", "terminal-recorded", "resolved-recorded"}), None)
        if entry is None:
            save_registry(registry_path, registry)
            continue
        manifest_path = Path(str(entry.get("apply_candidate_manifest_path") or ""))
        if not manifest_path.exists():
            entry["consumer_status"] = "missing-apply-candidate"
            entry["consumed_at"] = dt.datetime.now().isoformat(timespec="seconds")
            save_registry(registry_path, registry)
            return {"consumed_decision": decision, "consumer_status": "missing-apply-candidate", "registry_name": registry_name}
        manifest = load_registry(manifest_path, {})
        if decision == "retry":
            arm_result = _arm_harness_apply_bridge_from_manifest(manifest_path, manifest, repo_root=repo_root)
            consumer_status = "rearmed-bridge" if arm_result.get("bridge_status") == "armed" else str(arm_result.get("bridge_status") or "retry-skipped")
            manifest = load_registry(manifest_path, {})
        elif decision == "hold":
            manifest["recovery_review_status"] = "pending-review"
            manifest["recovery_review_lane"] = "hold"
            manifest["recovery_consumed_at"] = dt.datetime.now().isoformat(timespec="seconds")
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            consumer_status = "parked-for-review"
        elif decision == "abort":
            manifest["recovery_terminal_status"] = "aborted"
            manifest["recovery_consumed_at"] = dt.datetime.now().isoformat(timespec="seconds")
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            consumer_status = "terminal-recorded"
        else:
            manifest["recovery_resolution_status"] = "resolved"
            manifest["recovery_consumed_at"] = dt.datetime.now().isoformat(timespec="seconds")
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            consumer_status = "resolved-recorded"
        entry["consumer_status"] = consumer_status
        entry["consumed_at"] = dt.datetime.now().isoformat(timespec="seconds")
        save_registry(registry_path, registry)
        return {
            "selected_candidate_id": manifest.get("selected_candidate_id") or entry.get("selected_candidate_id"),
            "consumed_decision": decision,
            "consumer_status": consumer_status,
            "registry_name": registry_name,
            "apply_candidate_manifest_path": str(manifest_path),
            "recovery_route_manifest_path": entry.get("recovery_route_manifest_path"),
            "recovery_route_plan_path": entry.get("recovery_route_plan_path"),
        }
    return None


def run_harness_apply_recovery_downstream_automation(repo_root: Path) -> dict[str, object] | None:
    consume_result = consume_harness_apply_recovery_queue(repo_root)
    if consume_result is None:
        return None
    manifest_path = Path(str(consume_result.get("apply_candidate_manifest_path") or "")) if consume_result.get("apply_candidate_manifest_path") else None
    if manifest_path is None or not manifest_path.exists():
        return consume_result
    manifest = load_registry(manifest_path, {})
    manifest.setdefault("apply_candidate_manifest_path", str(manifest_path))
    consumed_decision = str(consume_result.get("consumed_decision") or "")
    downstream_status = "noop"
    launch_result = None
    verification_result = None
    followup_result = None
    recovery_route_manifest_path = consume_result.get("recovery_route_manifest_path") or manifest.get("recovery_route_manifest_path")
    routing_entry = None
    if recovery_route_manifest_path:
        route_path = Path(str(recovery_route_manifest_path))
        if route_path.exists():
            routing_entry = load_registry(route_path, {})
    if consumed_decision == "retry" and consume_result.get("consumer_status") == "rearmed-bridge":
        launch_result = launch_harness_apply_candidate_bridge(repo_root)
        if launch_result and launch_result.get("bridge_status") == "succeeded":
            verification_result = verify_harness_apply_candidate_result(repo_root)
            downstream_status = str((verification_result or {}).get("verification_status") or "launch-only")
        else:
            downstream_status = str((launch_result or {}).get("bridge_status") or "launch-skipped")
    elif consumed_decision == "hold":
        downstream_status = "pending-review"
        followup_result = queue_harness_apply_recovery_followup(
            repo_root / "fuzz-artifacts" / "automation",
            repo_root=repo_root,
            recovery_decision="hold",
            manifest=manifest,
            routing_entry=routing_entry,
        )
    elif consumed_decision == "abort":
        downstream_status = "aborted"
        followup_result = queue_harness_apply_recovery_followup(
            repo_root / "fuzz-artifacts" / "automation",
            repo_root=repo_root,
            recovery_decision="abort",
            manifest=manifest,
            routing_entry=routing_entry,
        )
    elif consumed_decision == "resolved":
        downstream_status = "resolved"
    manifest["recovery_downstream_status"] = downstream_status
    manifest["recovery_downstream_checked_at"] = dt.datetime.now().isoformat(timespec="seconds")
    if launch_result is not None:
        manifest["recovery_downstream_launch_status"] = launch_result.get("bridge_status")
    if verification_result is not None:
        manifest["recovery_downstream_verification_status"] = verification_result.get("verification_status")
        manifest["recovery_downstream_verification_summary"] = verification_result.get("verification_summary")
    if followup_result is not None:
        manifest["recovery_followup_status"] = "queued" if followup_result.get("created") else "already-queued"
        manifest["recovery_followup_action_code"] = followup_result.get("action_code")
        manifest["recovery_followup_registry"] = followup_result.get("path")
        manifest["recovery_followup_reason"] = followup_result.get("reason")
        manifest["recovery_followup_entry_key"] = followup_result.get("entry_key")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        **consume_result,
        "downstream_status": downstream_status,
        "launch_status": (launch_result or {}).get("bridge_status"),
        "verification_status": (verification_result or {}).get("verification_status"),
        "verification_summary": (verification_result or {}).get("verification_summary"),
        "followup_action_code": (followup_result or {}).get("action_code"),
        "followup_status": ("queued" if (followup_result or {}).get("created") else ("already-queued" if followup_result is not None else None)),
        "followup_registry": (followup_result or {}).get("path"),
    }


def run_harness_apply_recovery_full_closed_loop_chaining(repo_root: Path) -> dict[str, object] | None:
    downstream_result = run_harness_apply_recovery_downstream_automation(repo_root)
    if downstream_result is None:
        return None
    manifest_path = Path(str(downstream_result.get("apply_candidate_manifest_path") or "")) if downstream_result.get("apply_candidate_manifest_path") else None
    if manifest_path is None or not manifest_path.exists():
        return downstream_result
    manifest = load_registry(manifest_path, {})
    full_chain_status = str(downstream_result.get("downstream_status") or "noop")
    apply_result = None
    reroute_result = None
    if downstream_result.get("verification_status") == "verified":
        apply_result = apply_verified_harness_patch_candidate(repo_root)
        if apply_result is not None:
            reroute_result = route_harness_apply_recovery(repo_root)
            full_chain_status = "rerouted" if reroute_result is not None else "applied-no-reroute"
        else:
            full_chain_status = "verified-no-apply"
    manifest["recovery_full_chain_status"] = full_chain_status
    manifest["recovery_full_chain_checked_at"] = dt.datetime.now().isoformat(timespec="seconds")
    if apply_result is not None:
        manifest["recovery_full_chain_apply_status"] = apply_result.get("apply_status")
    if reroute_result is not None:
        manifest["recovery_full_chain_reroute_decision"] = reroute_result.get("recovery_decision")
        manifest["recovery_full_chain_reroute_action_code"] = reroute_result.get("action_code")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        **downstream_result,
        "full_chain_status": full_chain_status,
        "apply_status": (apply_result or {}).get("apply_status"),
        "reroute_decision": (reroute_result or {}).get("recovery_decision"),
        "reroute_action_code": (reroute_result or {}).get("action_code"),
    }


def _cooldown_active(last_checked_at: str | None, *, cooldown_seconds: int) -> bool:
    checked_at = parse_iso_timestamp(last_checked_at)
    if checked_at is None:
        return False
    age = (dt.datetime.now() - checked_at).total_seconds()
    return age < cooldown_seconds


def _adaptive_recursive_chain_cooldown(manifest: dict[str, object]) -> tuple[int, str | None]:
    base_cooldown = int(manifest.get("recovery_recursive_chain_cooldown_seconds") or 300)
    risk_level = str(manifest.get("recovery_route_risk_level") or "")
    failure_reason = str(manifest.get("recovery_followup_failure_policy_reason") or "")
    if risk_level == "critical" or failure_reason == "retry-budget-exhausted":
        return max(base_cooldown, 1800), "critical-routing-risk"
    if risk_level == "high":
        return max(base_cooldown, 900), "high-routing-risk"
    return base_cooldown, None


def _adaptive_downstream_chain_budget(manifest: dict[str, object]) -> tuple[int, str | None]:
    base_budget = int(manifest.get("recovery_followup_chain_budget") or 2)
    risk_level = str(manifest.get("recovery_route_risk_level") or "")
    failure_reason = str(manifest.get("recovery_followup_failure_policy_reason") or "")
    if risk_level == "critical" or failure_reason == "retry-budget-exhausted":
        return min(base_budget, 1), "critical-routing-risk"
    if risk_level == "high":
        return min(base_budget, 1), "high-routing-risk"
    return base_budget, None


def _adaptive_downstream_chain_cooldown(manifest: dict[str, object]) -> tuple[int, str | None]:
    base_cooldown = int(manifest.get("recovery_followup_chain_cooldown_seconds") or 300)
    risk_level = str(manifest.get("recovery_route_risk_level") or "")
    failure_reason = str(manifest.get("recovery_followup_failure_policy_reason") or "")
    if risk_level == "critical" or failure_reason == "retry-budget-exhausted":
        return max(base_cooldown, 1800), "critical-routing-risk"
    if risk_level == "high":
        return max(base_cooldown, 900), "high-routing-risk"
    return base_cooldown, None


def run_harness_apply_retry_recursive_chaining(repo_root: Path, *, max_cycles: int = 3) -> dict[str, object] | None:
    manifest_path = _latest_harness_apply_candidate_manifest(repo_root)
    if manifest_path is not None and manifest_path.exists():
        manifest = load_registry(manifest_path, {})
        cooldown_seconds, adaptive_reason = _adaptive_recursive_chain_cooldown(manifest)
        manifest["recovery_recursive_chain_cooldown_seconds"] = cooldown_seconds
        if adaptive_reason is not None:
            manifest["recovery_recursive_chain_adaptive_reason"] = adaptive_reason
        if _cooldown_active(str(manifest.get("recovery_recursive_chain_checked_at") or ""), cooldown_seconds=cooldown_seconds):
            manifest["recovery_recursive_chain_status"] = "cooldown-active"
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return {
                "selected_candidate_id": manifest.get("selected_candidate_id"),
                "apply_candidate_manifest_path": str(manifest_path),
                "recursive_chain_status": "cooldown-active",
                "cycle_count": 0,
                "cooldown_seconds": cooldown_seconds,
                "adaptive_reason": adaptive_reason,
            }
    cycle_count = 0
    last_result = None
    while cycle_count < max_cycles:
        cycle_count += 1
        last_result = run_harness_apply_recovery_full_closed_loop_chaining(repo_root)
        if last_result is None:
            return None
        reroute_decision = str(last_result.get("reroute_decision") or "")
        if reroute_decision != "retry":
            manifest_path = Path(str(last_result.get("apply_candidate_manifest_path") or "")) if last_result.get("apply_candidate_manifest_path") else None
            if manifest_path and manifest_path.exists():
                manifest = load_registry(manifest_path, {})
                manifest["recovery_recursive_chain_status"] = reroute_decision or "stopped"
                manifest["recovery_recursive_chain_cycle_count"] = cycle_count
                manifest["recovery_recursive_chain_checked_at"] = dt.datetime.now().isoformat(timespec="seconds")
                manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return {
                **last_result,
                "recursive_chain_status": reroute_decision or "stopped",
                "cycle_count": cycle_count,
            }
    if last_result is not None:
        manifest_path = Path(str(last_result.get("apply_candidate_manifest_path") or "")) if last_result.get("apply_candidate_manifest_path") else None
        if manifest_path and manifest_path.exists():
            manifest = load_registry(manifest_path, {})
            manifest["recovery_recursive_chain_status"] = "max-cycles-reached"
            manifest["recovery_recursive_chain_cycle_count"] = cycle_count
            manifest["recovery_recursive_chain_checked_at"] = dt.datetime.now().isoformat(timespec="seconds")
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {
            **last_result,
            "recursive_chain_status": "max-cycles-reached",
            "cycle_count": cycle_count,
        }
    return None


def run_harness_apply_recovery_followup_auto_reingestion(repo_root: Path) -> dict[str, object] | None:
    automation_dir = repo_root / "fuzz-artifacts" / "automation"
    registry_specs = [
        ("harness_review_queue.json", "halt_and_review_harness", "correction-policy"),
        ("harness_correction_regeneration_queue.json", "regenerate_harness_correction", "apply-candidate"),
    ]
    for registry_name, action_code, reingestion_target in registry_specs:
        registry_path = automation_dir / registry_name
        data = load_registry(registry_path, {"entries": []})
        entries = data.setdefault("entries", [])
        assert isinstance(entries, list)
        entry = next(
            (
                item
                for item in entries
                if isinstance(item, dict)
                and item.get("action_code") == action_code
                and item.get("recovery_followup_reason")
                and item.get("verification_status") == "verified"
                and item.get("reingestion_status") not in {"reingested", "skipped", "failed"}
            ),
            None,
        )
        if entry is None:
            save_registry(registry_path, data)
            continue
        manifest_path = Path(str(entry.get("apply_candidate_manifest_path") or "")) if entry.get("apply_candidate_manifest_path") else None
        if manifest_path is None or not manifest_path.exists():
            entry["reingestion_status"] = "failed"
            entry["reingestion_reason"] = "missing-apply-candidate-manifest"
            entry["reingested_at"] = dt.datetime.now().isoformat(timespec="seconds")
            save_registry(registry_path, data)
            return {
                "followup_action_code": action_code,
                "reingestion_target": reingestion_target,
                "reingestion_status": "failed",
                "reason": "missing-apply-candidate-manifest",
            }
        manifest = load_registry(manifest_path, {})
        if action_code == "halt_and_review_harness":
            downstream = write_harness_correction_policy(repo_root)
            artifact_path = str(downstream.get("policy_manifest_path") or "")
        else:
            downstream = write_harness_apply_candidate(repo_root)
            artifact_path = str(downstream.get("apply_candidate_manifest_path") or "")
        entry["reingestion_status"] = "reingested"
        entry["reingestion_target"] = reingestion_target
        entry["reingestion_artifact_path"] = artifact_path
        entry["reingestion_checked_at"] = dt.datetime.now().isoformat(timespec="seconds")
        entry["reingestion_summary"] = str(entry.get("verification_summary") or "verified-followup-reingested")
        save_registry(registry_path, data)
        manifest["recovery_followup_reingestion_status"] = "reingested"
        manifest["recovery_followup_reingestion_target"] = reingestion_target
        manifest["recovery_followup_reingestion_artifact_path"] = artifact_path
        manifest["recovery_followup_reingestion_action_code"] = action_code
        manifest["recovery_followup_reingestion_checked_at"] = dt.datetime.now().isoformat(timespec="seconds")
        manifest["recovery_followup_verification_status"] = entry.get("verification_status")
        manifest["recovery_followup_verification_summary"] = entry.get("verification_summary")
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {
            "followup_action_code": action_code,
            "reingestion_target": reingestion_target,
            "reingestion_status": "reingested",
            "selected_candidate_id": manifest.get("selected_candidate_id") or entry.get("selected_candidate_id"),
            "apply_candidate_manifest_path": str(manifest_path),
            "reingestion_artifact_path": artifact_path,
        }
    return None


def run_harness_apply_reingested_downstream_chaining(repo_root: Path) -> dict[str, object] | None:
    reingestion_result = run_harness_apply_recovery_followup_auto_reingestion(repo_root)
    if reingestion_result is None:
        return None
    original_manifest_path = Path(str(reingestion_result.get("apply_candidate_manifest_path") or "")) if reingestion_result.get("apply_candidate_manifest_path") else None
    if original_manifest_path is None or not original_manifest_path.exists():
        return reingestion_result
    original_manifest = load_registry(original_manifest_path, {})
    downstream_budget, budget_adaptive_reason = _adaptive_downstream_chain_budget(original_manifest)
    downstream_attempt_count = int(original_manifest.get("recovery_followup_chain_attempt_count") or 0)
    cooldown_seconds, cooldown_adaptive_reason = _adaptive_downstream_chain_cooldown(original_manifest)
    original_manifest["recovery_followup_chain_budget"] = downstream_budget
    original_manifest["recovery_followup_chain_cooldown_seconds"] = cooldown_seconds
    adaptive_reason = budget_adaptive_reason or cooldown_adaptive_reason
    if adaptive_reason is not None:
        original_manifest["recovery_followup_chain_adaptive_reason"] = adaptive_reason
    if downstream_attempt_count >= downstream_budget:
        original_manifest["recovery_followup_chain_status"] = "budget-exhausted"
        original_manifest["recovery_followup_chain_attempt_count"] = downstream_attempt_count
        original_manifest["recovery_followup_chain_checked_at"] = dt.datetime.now().isoformat(timespec="seconds")
        original_manifest_path.write_text(json.dumps(original_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {
            **reingestion_result,
            "downstream_chain_status": "budget-exhausted",
            "downstream_budget": downstream_budget,
            "downstream_attempt_count": downstream_attempt_count,
            "adaptive_reason": adaptive_reason,
        }
    if _cooldown_active(str(original_manifest.get("recovery_followup_chain_checked_at") or ""), cooldown_seconds=cooldown_seconds):
        original_manifest["recovery_followup_chain_status"] = "cooldown-active"
        original_manifest_path.write_text(json.dumps(original_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {
            **reingestion_result,
            "downstream_chain_status": "cooldown-active",
            "downstream_budget": downstream_budget,
            "downstream_attempt_count": downstream_attempt_count,
            "cooldown_seconds": cooldown_seconds,
            "adaptive_reason": adaptive_reason,
        }
    original_manifest["recovery_followup_chain_attempt_count"] = downstream_attempt_count + 1

    downstream_candidate_path: Path | None = None
    downstream_seed_result: dict[str, object] | None = None
    if reingestion_result.get("reingestion_target") == "correction-policy":
        downstream_seed_result = write_harness_apply_candidate(repo_root)
        downstream_candidate_path = Path(str(downstream_seed_result.get("apply_candidate_manifest_path") or "")) if downstream_seed_result.get("apply_candidate_manifest_path") else None
    elif reingestion_result.get("reingestion_artifact_path"):
        downstream_candidate_path = Path(str(reingestion_result.get("reingestion_artifact_path") or ""))

    if downstream_candidate_path is None or not downstream_candidate_path.exists():
        original_manifest["recovery_followup_chain_status"] = "no-apply-candidate"
        original_manifest["recovery_followup_chain_checked_at"] = dt.datetime.now().isoformat(timespec="seconds")
        original_manifest_path.write_text(json.dumps(original_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {
            **reingestion_result,
            "downstream_chain_status": "no-apply-candidate",
        }

    downstream_manifest = load_registry(downstream_candidate_path, {})
    arm_result = _arm_harness_apply_bridge_from_manifest(downstream_candidate_path, downstream_manifest, repo_root=repo_root)
    chain_status = str(arm_result.get("bridge_status") or "bridge-skipped")
    launch_result = None
    verification_result = None
    apply_result = None
    reroute_result = None
    if arm_result.get("bridge_status") == "armed":
        launch_result = launch_harness_apply_candidate_bridge(repo_root)
        chain_status = str((launch_result or {}).get("bridge_status") or "launch-skipped")
        if chain_status == "succeeded":
            verification_result = verify_harness_apply_candidate_result(repo_root)
            chain_status = str((verification_result or {}).get("verification_status") or "launch-only")
            if chain_status == "verified":
                apply_result = apply_verified_harness_patch_candidate(repo_root)
                if apply_result is not None:
                    reroute_result = route_harness_apply_recovery(repo_root)
                    chain_status = "rerouted" if reroute_result is not None else str(apply_result.get("apply_status") or "verified-no-reroute")
    original_manifest["recovery_followup_chain_status"] = chain_status
    original_manifest["recovery_followup_chain_apply_candidate_manifest_path"] = str(downstream_candidate_path)
    original_manifest["recovery_followup_chain_checked_at"] = dt.datetime.now().isoformat(timespec="seconds")
    if reroute_result is not None:
        original_manifest["recovery_followup_chain_reroute_decision"] = reroute_result.get("recovery_decision")
        original_manifest["recovery_followup_chain_reroute_action_code"] = reroute_result.get("action_code")
    original_manifest_path.write_text(json.dumps(original_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        **reingestion_result,
        "downstream_chain_status": chain_status,
        "downstream_seed_status": (downstream_seed_result or {}).get("decision") or (downstream_seed_result or {}).get("apply_candidate_scope"),
        "downstream_apply_candidate_manifest_path": str(downstream_candidate_path),
        "launch_status": (launch_result or {}).get("bridge_status"),
        "verification_status": (verification_result or {}).get("verification_status"),
        "apply_status": (apply_result or {}).get("apply_status"),
        "reroute_decision": (reroute_result or {}).get("recovery_decision"),
        "reroute_action_code": (reroute_result or {}).get("action_code"),
    }


def _recovery_ecosystem_lane_priority(manifest: dict[str, object]) -> list[str]:
    if str(manifest.get("recovery_followup_failure_policy_status") or "") == "escalate":
        return ["downstream", "retry"]
    if str(manifest.get("recovery_followup_status") or "") in {"queued", "already-queued"}:
        return ["downstream", "retry"]
    if str(manifest.get("recovery_followup_reingestion_status") or "") == "reingested":
        return ["downstream", "retry"]
    return ["retry", "downstream"]


def _recovery_ecosystem_continue_decision(lane: str, result: dict[str, object]) -> tuple[bool, str]:
    if lane == "retry":
        status = str(result.get("recursive_chain_status") or "stopped")
        if status in {"hold", "abort"}:
            return True, f"retry-lane-{status}-followup-pending"
        return False, f"retry-lane-{status}"
    status = str(result.get("downstream_chain_status") or "stopped")
    reroute_decision = str(result.get("reroute_decision") or "")
    if status == "rerouted" and reroute_decision in {"retry", "hold", "abort"}:
        return True, f"downstream-lane-rerouted-{reroute_decision}"
    if status == "rerouted" and reroute_decision:
        return False, f"downstream-lane-{reroute_decision}"
    return False, f"downstream-lane-{status}"


def run_harness_apply_recovery_ecosystem_recursion(repo_root: Path, *, max_rounds: int = 4) -> dict[str, object] | None:
    manifest_path = _latest_harness_apply_candidate_manifest(repo_root)
    if manifest_path is None:
        return None
    lane_sequence: list[str] = []
    last_result: dict[str, object] | None = None
    stop_reason = "no-eligible-lane"
    ecosystem_status = "stopped"
    for round_index in range(1, max_rounds + 1):
        manifest_path = _latest_harness_apply_candidate_manifest(repo_root)
        manifest = load_registry(manifest_path, {}) if manifest_path is not None and manifest_path.exists() else {}
        round_result = None
        chosen_lane = None
        for lane in _recovery_ecosystem_lane_priority(manifest):
            if lane == "downstream":
                candidate_result = run_harness_apply_reingested_downstream_chaining(repo_root)
            else:
                candidate_result = run_harness_apply_retry_recursive_chaining(repo_root)
            if candidate_result is not None:
                round_result = candidate_result
                chosen_lane = lane
                break
        if round_result is None or chosen_lane is None:
            stop_reason = "no-eligible-lane"
            ecosystem_status = "stopped"
            break
        lane_sequence.append(chosen_lane)
        last_result = round_result
        continue_loop, stop_reason = _recovery_ecosystem_continue_decision(chosen_lane, round_result)
        result_manifest_path = Path(str(round_result.get("apply_candidate_manifest_path") or "")) if round_result.get("apply_candidate_manifest_path") else manifest_path
        if result_manifest_path is not None and result_manifest_path.exists():
            result_manifest = load_registry(result_manifest_path, {})
            result_manifest["recovery_ecosystem_status"] = "continuing" if continue_loop else "stopped"
            result_manifest["recovery_ecosystem_stop_reason"] = stop_reason
            result_manifest["recovery_ecosystem_round_count"] = round_index
            result_manifest["recovery_ecosystem_last_lane"] = chosen_lane
            result_manifest["recovery_ecosystem_lane_sequence"] = lane_sequence
            result_manifest["recovery_ecosystem_checked_at"] = dt.datetime.now().isoformat(timespec="seconds")
            result_manifest_path.write_text(json.dumps(result_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if not continue_loop:
            ecosystem_status = "stopped"
            break
    else:
        ecosystem_status = "round-budget-exhausted"
        stop_reason = "ecosystem-round-budget-exhausted"
        result_manifest_path = Path(str((last_result or {}).get("apply_candidate_manifest_path") or "")) if (last_result or {}).get("apply_candidate_manifest_path") else manifest_path
        if result_manifest_path is not None and result_manifest_path.exists():
            result_manifest = load_registry(result_manifest_path, {})
            result_manifest["recovery_ecosystem_status"] = ecosystem_status
            result_manifest["recovery_ecosystem_stop_reason"] = stop_reason
            result_manifest["recovery_ecosystem_round_count"] = max_rounds
            result_manifest["recovery_ecosystem_last_lane"] = lane_sequence[-1] if lane_sequence else None
            result_manifest["recovery_ecosystem_lane_sequence"] = lane_sequence
            result_manifest["recovery_ecosystem_checked_at"] = dt.datetime.now().isoformat(timespec="seconds")
            result_manifest_path.write_text(json.dumps(result_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if last_result is None:
        return None
    return {
        **last_result,
        "ecosystem_status": ecosystem_status,
        "ecosystem_stop_reason": stop_reason,
        "ecosystem_round_count": len(lane_sequence),
        "ecosystem_last_lane": lane_sequence[-1] if lane_sequence else None,
        "ecosystem_lane_sequence": lane_sequence,
    }


def prepare_harness_apply_candidate_bridge(repo_root: Path) -> dict[str, object]:
    apply_result = write_harness_apply_candidate(repo_root)
    manifest_path = Path(str(apply_result.get("apply_candidate_manifest_path") or ""))
    manifest = load_registry(manifest_path, {})
    return _arm_harness_apply_bridge_from_manifest(manifest_path, manifest, repo_root=repo_root)


def launch_harness_apply_candidate_bridge(repo_root: Path) -> dict[str, object] | None:
    manifest_path = _latest_harness_apply_candidate_manifest(repo_root)
    if manifest_path is None:
        return None
    manifest = load_registry(manifest_path, {})
    if manifest.get("bridge_status") != "armed":
        return None
    script_path = Path(str(manifest.get("bridge_script_path") or ""))
    if not script_path.exists():
        manifest["bridge_status"] = "failed"
        manifest["launch_status"] = "failed"
        manifest["bridge_exit_code"] = 127
        manifest["bridge_failure_reason"] = f"bridge script missing: {script_path}"
        manifest["bridge_launched_at"] = dt.datetime.now().isoformat(timespec="seconds")
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {
            "selected_candidate_id": manifest.get("selected_candidate_id"),
            "bridge_status": "failed",
            "exit_code": 127,
            "apply_candidate_manifest_path": str(manifest_path),
        }
    launch_dir = repo_root / "fuzz-records" / "harness-apply-launches"
    launch_dir.mkdir(parents=True, exist_ok=True)
    stem = manifest_path.stem.replace("-harness-apply-candidate", "-harness-apply-launch")
    log_path = launch_dir / f"{stem}.log"
    result = launch_bridge_script(script_path)
    output_text = str(result.get("output") or "")
    log_path.write_text(output_text, encoding="utf-8")
    exit_code = int(result.get("exit_code") or 0)
    bridge_status = "succeeded" if exit_code == 0 else "failed"
    parsed = parse_delegate_bridge_output(output_text)
    manifest["bridge_status"] = bridge_status
    manifest["launch_status"] = bridge_status
    manifest["bridge_exit_code"] = exit_code
    manifest["bridge_launch_log_path"] = str(log_path)
    manifest["bridge_launched_at"] = dt.datetime.now().isoformat(timespec="seconds")
    for key, value in parsed.items():
        if value is not None:
            manifest[key] = value
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "selected_candidate_id": manifest.get("selected_candidate_id"),
        "bridge_status": bridge_status,
        "exit_code": exit_code,
        "bridge_launch_log_path": str(log_path),
        "apply_candidate_manifest_path": str(manifest_path),
        **{key: value for key, value in parsed.items() if value is not None},
    }


def verify_harness_apply_candidate_result(
    repo_root: Path,
    *,
    probe_runner: Callable[[list[str], Path], tuple[int, str]] | None = None,
) -> dict[str, object] | None:
    manifest_path = _latest_harness_apply_candidate_manifest(repo_root)
    if manifest_path is None:
        return None
    manifest = load_registry(manifest_path, {})
    if manifest.get("bridge_status") != "succeeded":
        return None
    verification = verify_delegate_entry(manifest, repo_root=repo_root, probe_runner=probe_runner or run_probe_command)
    evidence_lineage = {
        "llm_objective": manifest.get("llm_objective"),
        "failure_reason_codes": manifest.get("failure_reason_codes"),
        "raw_signal_summary": manifest.get("raw_signal_summary"),
    }
    for key, value in verification.items():
        manifest[key] = value
    for key, value in evidence_lineage.items():
        if value is not None:
            manifest[key] = value
    manifest["verified_at"] = dt.datetime.now().isoformat(timespec="seconds")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "selected_candidate_id": manifest.get("selected_candidate_id"),
        "verification_status": verification.get("verification_status"),
        "verification_summary": verification.get("verification_summary"),
        "delegate_session_verified": verification.get("delegate_session_verified"),
        "delegate_artifact_verified": verification.get("delegate_artifact_verified"),
        "delegate_artifact_shape_verified": verification.get("delegate_artifact_shape_verified"),
        "delegate_artifact_quality_verified": verification.get("delegate_artifact_quality_verified"),
        "delegate_artifact_evidence_response_verified": verification.get("delegate_artifact_evidence_response_verified"),
        "delegate_artifact_patch_alignment_verified": verification.get("delegate_artifact_patch_alignment_verified"),
        "delegate_reported_llm_objective": verification.get("delegate_reported_llm_objective"),
        "delegate_reported_failure_reason_codes": verification.get("delegate_reported_failure_reason_codes"),
        "delegate_reported_response_summary": verification.get("delegate_reported_response_summary"),
        "delegate_reported_patch_summary": verification.get("delegate_reported_patch_summary"),
        "llm_objective": evidence_lineage.get("llm_objective"),
        "failure_reason_codes": evidence_lineage.get("failure_reason_codes"),
        "raw_signal_summary": evidence_lineage.get("raw_signal_summary"),
        "apply_candidate_manifest_path": str(manifest_path),
    }


def _build_guard_only_patch_plan(
    content: str,
    *,
    note: str,
    entrypoint_names: tuple[str, ...] | None = None,
    guard_condition: str = "size < 4",
    guard_return_statement: str = "return 0;",
) -> dict[str, str] | None:
    names = entrypoint_names or ("LLVMFuzzerTestOneInput",)
    lines = content.splitlines(keepends=True)
    c_comment = f"  /* Hermes guarded apply candidate: {note} */\n"
    cpp_comment = f"  // Hermes guarded apply candidate: {note}\n"
    normalized_return = guard_return_statement.strip()
    guard_lines = f"  if ({guard_condition}) {{\n    {normalized_return}\n  }}\n"
    for index, line in enumerate(lines):
        for name in names:
            escaped_name = re.escape(name)
            if re.fullmatch(
                rf'(?P<indent>\s*)(?:int\s+)?{escaped_name}\s*\(\s*const\s+(?:uint8_t|unsigned char)\s*\*\s*data\s*,\s*(?:size_t|unsigned long)\s+size\s*\)\s*\{{\n?',
                line,
            ):
                return {
                    "line_index": str(index),
                    "comment": c_comment,
                    "guard_lines": guard_lines,
                }
            if re.fullmatch(
                rf'(?P<indent>\s*)(?:extern\s+"C"\s+)?(?:int\s+)?{escaped_name}\s*\(\s*const\s+std::uint8_t\s*\*\s*data\s*,\s*std::size_t\s+size\s*\)\s*\{{\n?',
                line,
            ):
                return {
                    "line_index": str(index),
                    "comment": cpp_comment,
                    "guard_lines": guard_lines,
                }
    return None


def _inject_guarded_patch(
    content: str,
    *,
    scope: str,
    note: str,
    entrypoint_names: tuple[str, ...] | None = None,
    guard_condition: str = "size < 4",
    guard_return_statement: str = "return 0;",
) -> str:
    if "Hermes guarded apply candidate" in content:
        return content
    stripped = content.rstrip() + "\n"
    if scope == "guard-only" and guard_condition not in stripped:
        plan = _build_guard_only_patch_plan(
            stripped,
            note=note,
            entrypoint_names=entrypoint_names,
            guard_condition=guard_condition,
            guard_return_statement=guard_return_statement,
        )
        if isinstance(plan, dict):
            line_index = int(plan.get("line_index") or 0)
            lines = stripped.splitlines(keepends=True)
            lines[line_index] = lines[line_index] + str(plan.get("comment") or "") + str(plan.get("guard_lines") or "")
            return "".join(lines)
    comment = f"/* Hermes guarded apply candidate: {note} */\n"
    return stripped + comment


def _candidate_semantics_guardrails(scope: str, note: str) -> dict[str, object]:
    lowered = note.lower()
    dangerous_terms = (
        "rewrite build",
        "build script",
        "cmakelists",
        "meson.build",
        "makefile",
        "rename",
        "entrypoint",
        "persistent mode",
        "delete",
        "remove",
    )
    reasons: list[str] = []
    if any(term in lowered for term in dangerous_terms):
        reasons.append("delegate-summary-requested-out-of-scope-mutation")
    if scope == "comment-only":
        code_mutation_terms = (
            "return ",
            "change return",
            "replace return",
            "#include",
            "include ",
            "call helper",
            "call ",
            "invoke ",
            "helper",
            "before parse",
            "after parse",
            "signature",
            "logic",
        )
        if any(term in lowered for term in code_mutation_terms):
            reasons.append("comment-only-summary-requested-code-mutation")
    if scope == "guard-only":
        guard_terms = ("guard", "size", "small", "input", "smoke", "seed", "early return")
        if not any(term in lowered for term in guard_terms):
            reasons.append("guard-only-summary-missing-guard-intent")
    status = "passed" if not reasons else "blocked"
    return {
        "candidate_semantics_status": status,
        "candidate_semantics_summary": "scope-aligned-summary" if status == "passed" else ";".join(reasons),
        "candidate_semantics_reasons": reasons,
    }


def _find_fuzzer_entrypoint_region(content: str, entrypoint_names: tuple[str, ...] | None = None) -> tuple[int, int] | None:
    lines = content.splitlines()
    names = entrypoint_names or ("LLVMFuzzerTestOneInput",)
    start_index = None
    for index, line in enumerate(lines):
        if any(name in line for name in names):
            start_index = index
            break
    if start_index is None:
        return None
    balance = 0
    opened = False
    for index in range(start_index, len(lines)):
        line = lines[index]
        balance += line.count("{")
        if line.count("{"):
            opened = True
        balance -= line.count("}")
        if opened and balance <= 0:
            return start_index + 1, index + 1
    return start_index + 1, len(lines)


def _guard_only_line_allowed(
    stripped: str,
    entrypoint_names: tuple[str, ...] | None = None,
    guard_condition: str = "size < 4",
    guard_return_statement: str = "return 0;",
) -> bool:
    names = entrypoint_names or ("LLVMFuzzerTestOneInput",)
    if not stripped:
        return True
    if "Hermes guarded apply candidate" in stripped:
        return True
    if stripped == guard_return_statement.strip():
        return True
    if stripped == "}" or stripped == "{":
        return True
    for name in names:
        escaped_name = re.escape(name)
        if re.fullmatch(rf'(?:int\s+)?(?:extern\s+"C"\s+)?{escaped_name}\s*\(\s*const\s+(?:uint8_t|unsigned char|std::uint8_t)\s*\*\s*data\s*,\s*(?:size_t|unsigned long|std::size_t)\s+size\s*\)\s*\{{', stripped):
            return True
    escaped_guard_condition = re.escape(guard_condition.strip())
    if re.fullmatch(rf"if\s*\(\s*{escaped_guard_condition}\s*\)\s*\{{?", stripped):
        return True
    return False


def _diff_safety_guardrails(repo_root: Path, target_file: Path, original_content: str, patched_content: str, *, scope: str) -> dict[str, object]:
    reasons: list[str] = []
    target_adapter = _resolve_runtime_target_adapter(repo_root)
    editable_root = (repo_root / target_adapter.editable_harness_relpath).resolve()
    entrypoint_names = target_adapter.fuzz_entrypoint_names
    guard_condition = target_adapter.guard_condition
    guard_return_statement = target_adapter.guard_return_statement
    try:
        target_relative = target_file.resolve().relative_to(editable_root)
    except ValueError:
        target_relative = None
    if target_relative is None:
        reasons.append("target-file-outside-generated-harness-dir")
    diff_lines = [
        line
        for line in difflib.unified_diff(
            original_content.splitlines(),
            patched_content.splitlines(),
            fromfile="before",
            tofile="after",
            lineterm="",
        )
        if line.startswith("+") or line.startswith("-")
    ]
    changed_line_count = len([line for line in diff_lines if not line.startswith(("+++", "---"))])
    max_changed_lines = 6 if scope == "guard-only" else 2
    if changed_line_count > max_changed_lines:
        reasons.append(f"changed-line-count-exceeds-{max_changed_lines}")

    original_lines = original_content.splitlines()
    patched_lines = patched_content.splitlines()
    diff_ops = [
        (tag, i1, i2, j1, j2)
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=original_lines, b=patched_lines).get_opcodes()
        if tag != "equal"
    ]
    hunk_count = len(diff_ops)
    if hunk_count > 1:
        reasons.append("multi-hunk-diff-not-allowed")

    touched_region_status = "passed"
    touched_region_summary = "bounded-generated-harness-diff"
    if scope == "comment-only":
        if not diff_ops:
            touched_region_status = "blocked"
            reasons.append("comment-only-empty-diff")
        else:
            insert_only = all(tag == "insert" and i1 == len(original_lines) for tag, i1, i2, j1, j2 in diff_ops)
            inserted_lines = [line for tag, i1, i2, j1, j2 in diff_ops for line in patched_lines[j1:j2]]
            comment_only_ok = insert_only and inserted_lines and all(
                (not line.strip()) or ("Hermes guarded apply candidate" in line) for line in inserted_lines
            )
            if not comment_only_ok:
                touched_region_status = "blocked"
                reasons.append("comment-only-non-whitelisted-edit")
            else:
                touched_region_summary = "append-only-hermes-comment"
    elif scope == "guard-only":
        region = _find_fuzzer_entrypoint_region(original_content, entrypoint_names)
        if region is None:
            touched_region_status = "blocked"
            reasons.append("missing-fuzzer-entrypoint-region")
        else:
            start_line, end_line = region
            for tag, i1, i2, j1, j2 in diff_ops:
                touched_lines = list(range(i1 + 1, i2 + 1))
                if not touched_lines:
                    anchor_line = min(max(i1 + 1, start_line), max(end_line, start_line))
                    touched_lines = [anchor_line]
                if any(line_no < start_line or line_no > end_line for line_no in touched_lines):
                    touched_region_status = "blocked"
                    reasons.append("touched-region-outside-fuzzer-entrypoint")
                    break
            whitelist_ok = True
            for tag, i1, i2, j1, j2 in diff_ops:
                for line in patched_lines[j1:j2]:
                    stripped = line.strip()
                    if not _guard_only_line_allowed(
                        stripped,
                        entrypoint_names,
                        guard_condition=guard_condition,
                        guard_return_statement=guard_return_statement,
                    ):
                        whitelist_ok = False
                        break
                if not whitelist_ok:
                    break
            if not whitelist_ok:
                touched_region_status = "blocked"
                reasons.append("guard-only-non-whitelisted-edit")
            elif touched_region_status == "passed":
                touched_region_summary = "fuzzer-entrypoint-guard-whitelist"

    if touched_region_status == "blocked" and not any(reason.startswith("touched-region") or "whitelisted" in reason or reason.endswith("empty-diff") or reason.startswith("missing-fuzzer-entrypoint") for reason in reasons):
        touched_region_summary = "diff-scope-violated"
    elif touched_region_status == "passed":
        touched_region_summary = touched_region_summary

    status = "passed" if not reasons else "blocked"
    summary = touched_region_summary if status == "passed" else ";".join(reasons)
    return {
        "diff_safety_status": status,
        "diff_safety_summary": summary,
        "diff_safety_reasons": reasons,
        "diff_changed_line_count": changed_line_count,
        "diff_max_changed_lines": max_changed_lines,
        "diff_hunk_count": hunk_count,
        "diff_touched_region_status": touched_region_status,
        "diff_touched_region_summary": touched_region_summary,
    }


def _next_recovery_policy(
    manifest: dict[str, object],
    *,
    apply_status: str,
    apply_guardrail_status: str,
    build_status: str,
    smoke_status: str,
) -> dict[str, object]:
    previous_failure_streak = int(manifest.get("recovery_failure_streak") or 0)
    previous_attempt_count = int(manifest.get("recovery_attempt_count") or 0)
    attempt_count = previous_attempt_count + (1 if apply_status in {"applied", "rolled_back"} else 0)
    if apply_guardrail_status == "blocked" or apply_status == "blocked":
        return {
            "recovery_decision": "hold",
            "recovery_summary": "hold-blocked-by-pre-apply-guardrail",
            "recovery_failure_streak": 0,
            "recovery_attempt_count": previous_attempt_count,
            "recovery_status": "deferred",
        }
    if apply_status == "applied":
        return {
            "recovery_decision": "resolved",
            "recovery_summary": "apply-succeeded-no-recovery-needed",
            "recovery_failure_streak": 0,
            "recovery_attempt_count": attempt_count,
            "recovery_status": "resolved",
        }
    if apply_status == "rolled_back":
        failure_streak = previous_failure_streak + 1
        if failure_streak >= 2:
            decision = "abort"
            summary = "repeated-apply-failure-streak-abort"
            status = "terminal"
        else:
            decision = "retry"
            summary = "first-apply-failure-retry-allowed"
            status = "retryable"
        return {
            "recovery_decision": decision,
            "recovery_summary": summary,
            "recovery_failure_streak": failure_streak,
            "recovery_attempt_count": attempt_count,
            "recovery_status": status,
            "recovery_last_build_status": build_status,
            "recovery_last_smoke_status": smoke_status,
        }
    return {
        "recovery_decision": "hold",
        "recovery_summary": "unexpected-apply-state-held-for-review",
        "recovery_failure_streak": previous_failure_streak,
        "recovery_attempt_count": previous_attempt_count,
        "recovery_status": "deferred",
    }


def apply_verified_harness_patch_candidate(
    repo_root: Path,
    *,
    probe_runner: Callable[[list[str], Path], tuple[int, str]] | None = None,
) -> dict[str, object] | None:
    manifest_path = _latest_harness_apply_candidate_manifest(repo_root)
    if manifest_path is None:
        return None
    manifest = load_registry(manifest_path, {})
    if manifest.get("verification_status") != "verified":
        return None
    target_file = Path(str(manifest.get("target_file_path") or ""))
    if not target_file.exists():
        manifest["apply_status"] = "failed"
        manifest["apply_failure_reason"] = f"target file missing: {target_file}"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {
            "selected_candidate_id": manifest.get("selected_candidate_id"),
            "apply_status": "failed",
            "apply_candidate_manifest_path": str(manifest_path),
        }
    artifact_path = Path(str(manifest.get("delegate_artifact_path") or "")) if manifest.get("delegate_artifact_path") else None
    evidence_lineage = {
        "llm_objective": manifest.get("llm_objective"),
        "failure_reason_codes": manifest.get("failure_reason_codes"),
        "top_failure_reason_codes": manifest.get("top_failure_reason_codes"),
        "raw_signal_summary": manifest.get("raw_signal_summary"),
        "delegate_artifact_evidence_response_verified": manifest.get("delegate_artifact_evidence_response_verified"),
        "delegate_artifact_patch_alignment_verified": manifest.get("delegate_artifact_patch_alignment_verified"),
        "delegate_reported_llm_objective": manifest.get("delegate_reported_llm_objective"),
        "delegate_reported_failure_reason_codes": manifest.get("delegate_reported_failure_reason_codes"),
        "delegate_reported_response_summary": manifest.get("delegate_reported_response_summary"),
        "delegate_reported_patch_summary": manifest.get("delegate_reported_patch_summary"),
    }
    note = "verified patch candidate"
    if artifact_path and artifact_path.exists():
        lines = [line.strip('- ').strip() for line in artifact_path.read_text(encoding='utf-8').splitlines() if line.strip().startswith('- ')]
        if lines:
            note = lines[0]
    scope = str(manifest.get("apply_candidate_scope") or "comment-only")
    candidate_id = str(manifest.get("selected_candidate_id") or "candidate-1")
    project = str(manifest.get("generated_from_project") or repo_root.name)
    target_adapter = _resolve_runtime_target_adapter(repo_root)
    original_content = target_file.read_text(encoding="utf-8")
    try:
        patched_content = _inject_guarded_patch(
            original_content,
            scope=scope,
            note=note,
            entrypoint_names=target_adapter.fuzz_entrypoint_names,
            guard_condition=target_adapter.guard_condition,
            guard_return_statement=target_adapter.guard_return_statement,
        )
    except TypeError as exc:
        if not (
            "entrypoint_names" in str(exc)
            or "guard_condition" in str(exc)
            or "guard_return_statement" in str(exc)
        ):
            raise
        patched_content = _inject_guarded_patch(original_content, scope=scope, note=note)
    diff_alignment = _validate_delegate_diff_alignment(
        original_content=original_content,
        patched_content=patched_content,
        scope=scope,
        reported_patch_summary=str(evidence_lineage.get("delegate_reported_patch_summary") or note),
    )
    hunk_intent = _validate_delegate_hunk_intent(
        changed_hunk_added_lines_preview=list(diff_alignment.get("changed_hunk_added_lines_preview") or []),
        reported_patch_summary=str(evidence_lineage.get("delegate_reported_patch_summary") or note),
    )
    failure_reason_hunk = _validate_failure_reason_hunk_alignment(
        failure_reason_codes=evidence_lineage.get("failure_reason_codes") if isinstance(evidence_lineage.get("failure_reason_codes"), list) else [],
        top_failure_reason_codes=evidence_lineage.get("top_failure_reason_codes") if isinstance(evidence_lineage.get("top_failure_reason_codes"), list) else [],
        changed_hunk_added_lines_preview=list(diff_alignment.get("changed_hunk_added_lines_preview") or []),
    )
    semantics = _candidate_semantics_guardrails(scope, note)
    if semantics["candidate_semantics_status"] == "passed":
        diff_safety = _diff_safety_guardrails(repo_root, target_file, original_content, patched_content, scope=scope)
    else:
        diff_safety = {
            "diff_safety_status": "skipped",
            "diff_safety_summary": "skipped-because-semantics-blocked",
            "diff_safety_reasons": [],
            "diff_changed_line_count": None,
            "diff_max_changed_lines": 6 if scope == "guard-only" else 2,
            "diff_hunk_count": 0,
            "diff_touched_region_status": "skipped",
            "diff_touched_region_summary": "skipped-because-semantics-blocked",
        }
    guardrail_passed = semantics["candidate_semantics_status"] == "passed" and diff_safety["diff_safety_status"] == "passed"

    out_dir = repo_root / "fuzz-records" / "harness-apply-results"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{slugify_run_dir(project)}-{candidate_id}-harness-apply-result"
    result_path = out_dir / f"{stem}.json"

    if not guardrail_passed:
        recovery = _next_recovery_policy(
            manifest,
            apply_status="blocked",
            apply_guardrail_status="blocked",
            build_status="skipped",
            smoke_status="skipped",
        )
        result_payload = {
            "generated_from_project": project,
            "selected_candidate_id": candidate_id,
            "target_file_path": str(target_file),
            "apply_candidate_manifest_path": str(manifest_path),
            "apply_status": "blocked",
            "apply_guardrail_status": "blocked",
            "rollback_status": None,
            "backup_path": None,
            "build_probe_status": "skipped",
            "smoke_probe_status": "skipped",
            "build_probe_result": None,
            "smoke_probe_result": None,
            **evidence_lineage,
            **diff_alignment,
            **hunk_intent,
            **failure_reason_hunk,
            **semantics,
            **diff_safety,
            **recovery,
        }
        result_path.write_text(json.dumps(result_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest.update(
            {
                "apply_status": "blocked",
                "apply_guardrail_status": "blocked",
                "rollback_status": None,
                "backup_path": None,
                "apply_result_manifest_path": str(result_path),
                "build_probe_status": "skipped",
                "smoke_probe_status": "skipped",
                "applied_at": dt.datetime.now().isoformat(timespec="seconds"),
                **evidence_lineage,
                **diff_alignment,
                **hunk_intent,
                **failure_reason_hunk,
                **semantics,
                **diff_safety,
                **recovery,
            }
        )
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {
            "selected_candidate_id": candidate_id,
            "apply_status": "blocked",
            "apply_guardrail_status": "blocked",
            "candidate_semantics_status": semantics.get("candidate_semantics_status"),
            "candidate_semantics_summary": semantics.get("candidate_semantics_summary"),
            "candidate_semantics_reasons": semantics.get("candidate_semantics_reasons"),
            "diff_safety_status": diff_safety.get("diff_safety_status"),
            "diff_safety_reasons": diff_safety.get("diff_safety_reasons"),
            "diff_touched_region_status": diff_safety.get("diff_touched_region_status"),
            "diff_touched_region_summary": diff_safety.get("diff_touched_region_summary"),
            "recovery_decision": recovery.get("recovery_decision"),
            "recovery_failure_streak": recovery.get("recovery_failure_streak"),
            "llm_objective": evidence_lineage.get("llm_objective"),
            "failure_reason_codes": evidence_lineage.get("failure_reason_codes"),
            "top_failure_reason_codes": evidence_lineage.get("top_failure_reason_codes"),
            "raw_signal_summary": evidence_lineage.get("raw_signal_summary"),
            "delegate_artifact_evidence_response_verified": evidence_lineage.get("delegate_artifact_evidence_response_verified"),
            "delegate_artifact_patch_alignment_verified": evidence_lineage.get("delegate_artifact_patch_alignment_verified"),
            "delegate_reported_llm_objective": evidence_lineage.get("delegate_reported_llm_objective"),
            "delegate_reported_failure_reason_codes": evidence_lineage.get("delegate_reported_failure_reason_codes"),
            "delegate_reported_response_summary": evidence_lineage.get("delegate_reported_response_summary"),
            "delegate_reported_patch_summary": evidence_lineage.get("delegate_reported_patch_summary"),
            "delegate_diff_alignment_verified": diff_alignment.get("delegate_diff_alignment_verified"),
            "actual_mutation_shape": diff_alignment.get("actual_mutation_shape"),
            "changed_hunk_added_lines_preview": diff_alignment.get("changed_hunk_added_lines_preview"),
            "delegate_hunk_intent_alignment_verified": hunk_intent.get("delegate_hunk_intent_alignment_verified"),
            "failure_reason_hunk_alignment_verified": failure_reason_hunk.get("failure_reason_hunk_alignment_verified"),
            "failure_reason_hunk_alignment_summary": failure_reason_hunk.get("failure_reason_hunk_alignment_summary"),
            "failure_reason_hunk_alignment_reasons": failure_reason_hunk.get("failure_reason_hunk_alignment_reasons"),
            "failure_reason_hunk_intent": failure_reason_hunk.get("failure_reason_hunk_intent"),
            "failure_reason_hunk_primary_reason_code": failure_reason_hunk.get("failure_reason_hunk_primary_reason_code"),
            "failure_reason_hunk_priority_basis": failure_reason_hunk.get("failure_reason_hunk_priority_basis"),
            "failure_reason_hunk_secondary_conflict_status": failure_reason_hunk.get("failure_reason_hunk_secondary_conflict_status"),
            "failure_reason_hunk_secondary_conflict_count": failure_reason_hunk.get("failure_reason_hunk_secondary_conflict_count"),
            "failure_reason_hunk_secondary_conflict_reasons": failure_reason_hunk.get("failure_reason_hunk_secondary_conflict_reasons"),
            "failure_reason_hunk_deferred_reason_codes": failure_reason_hunk.get("failure_reason_hunk_deferred_reason_codes"),
            "build_probe_status": "skipped",
            "smoke_probe_status": "skipped",
            "apply_candidate_manifest_path": str(manifest_path),
            "apply_result_manifest_path": str(result_path),
        }

    backup_dir = repo_root / "fuzz-records" / "harness-apply-backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{slugify_run_dir(project)}-{candidate_id}-pre-apply.backup"
    backup_path.write_text(original_content, encoding="utf-8")
    target_file.write_text(patched_content, encoding="utf-8")

    probe_runner = probe_runner or run_probe_command
    probe_draft = build_harness_probe_draft(repo_root)
    build_probe = probe_draft.get("build_probe") if isinstance(probe_draft.get("build_probe"), dict) else {}
    smoke_probe = probe_draft.get("smoke_probe") if isinstance(probe_draft.get("smoke_probe"), dict) else {}
    build_command = build_probe.get("command") if isinstance(build_probe.get("command"), list) else ["true"]
    smoke_command = smoke_probe.get("command") if isinstance(smoke_probe.get("command"), list) else ["true"]
    build_exit, build_output = probe_runner(list(build_command), repo_root)
    build_status = "passed" if build_exit == 0 else "failed"
    if build_status == "passed":
        smoke_exit, smoke_output = probe_runner(list(smoke_command), repo_root)
        smoke_status = "passed" if smoke_exit == 0 else "failed"
    else:
        smoke_exit, smoke_output, smoke_status = None, "", "skipped"

    rollback_status = None
    apply_status = "applied"
    if build_status == "failed" or smoke_status == "failed":
        target_file.write_text(original_content, encoding="utf-8")
        rollback_status = "restored"
        apply_status = "rolled_back"
    recovery = _next_recovery_policy(
        manifest,
        apply_status=apply_status,
        apply_guardrail_status="passed",
        build_status=build_status,
        smoke_status=smoke_status,
    )

    result_payload = {
        "generated_from_project": project,
        "selected_candidate_id": candidate_id,
        "target_file_path": str(target_file),
        "apply_candidate_manifest_path": str(manifest_path),
        "apply_status": apply_status,
        "apply_guardrail_status": "passed",
        "rollback_status": rollback_status,
        "backup_path": str(backup_path),
        "build_probe_status": build_status,
        "smoke_probe_status": smoke_status,
        "build_probe_result": {"command": build_command, "exit_code": build_exit, "output": build_output},
        "smoke_probe_result": {"command": smoke_command, "exit_code": smoke_exit, "output": smoke_output},
        **evidence_lineage,
        **diff_alignment,
        **hunk_intent,
        **failure_reason_hunk,
        **semantics,
        **diff_safety,
        **recovery,
    }
    result_path.write_text(json.dumps(result_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["apply_status"] = apply_status
    manifest["apply_guardrail_status"] = "passed"
    manifest["rollback_status"] = rollback_status
    manifest["backup_path"] = str(backup_path)
    manifest["apply_result_manifest_path"] = str(result_path)
    manifest["build_probe_status"] = build_status
    manifest["smoke_probe_status"] = smoke_status
    manifest["applied_at"] = dt.datetime.now().isoformat(timespec="seconds")
    for key, value in {**evidence_lineage, **diff_alignment, **hunk_intent, **failure_reason_hunk, **semantics, **diff_safety, **recovery}.items():
        manifest[key] = value
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "selected_candidate_id": candidate_id,
        "apply_status": apply_status,
        "apply_guardrail_status": "passed",
        "candidate_semantics_status": semantics.get("candidate_semantics_status"),
        "diff_safety_status": diff_safety.get("diff_safety_status"),
        "recovery_decision": recovery.get("recovery_decision"),
        "recovery_failure_streak": recovery.get("recovery_failure_streak"),
        "llm_objective": evidence_lineage.get("llm_objective"),
        "failure_reason_codes": evidence_lineage.get("failure_reason_codes"),
        "raw_signal_summary": evidence_lineage.get("raw_signal_summary"),
        "delegate_artifact_evidence_response_verified": evidence_lineage.get("delegate_artifact_evidence_response_verified"),
        "delegate_artifact_patch_alignment_verified": evidence_lineage.get("delegate_artifact_patch_alignment_verified"),
        "delegate_reported_llm_objective": evidence_lineage.get("delegate_reported_llm_objective"),
        "delegate_reported_failure_reason_codes": evidence_lineage.get("delegate_reported_failure_reason_codes"),
        "delegate_reported_response_summary": evidence_lineage.get("delegate_reported_response_summary"),
        "delegate_reported_patch_summary": evidence_lineage.get("delegate_reported_patch_summary"),
        "delegate_diff_alignment_verified": diff_alignment.get("delegate_diff_alignment_verified"),
        "actual_mutation_shape": diff_alignment.get("actual_mutation_shape"),
        "changed_hunk_added_lines_preview": diff_alignment.get("changed_hunk_added_lines_preview"),
        "delegate_hunk_intent_alignment_verified": hunk_intent.get("delegate_hunk_intent_alignment_verified"),
        "failure_reason_hunk_alignment_verified": failure_reason_hunk.get("failure_reason_hunk_alignment_verified"),
        "failure_reason_hunk_alignment_summary": failure_reason_hunk.get("failure_reason_hunk_alignment_summary"),
        "failure_reason_hunk_alignment_reasons": failure_reason_hunk.get("failure_reason_hunk_alignment_reasons"),
        "failure_reason_hunk_intent": failure_reason_hunk.get("failure_reason_hunk_intent"),
        "failure_reason_hunk_primary_reason_code": failure_reason_hunk.get("failure_reason_hunk_primary_reason_code"),
        "failure_reason_hunk_priority_basis": failure_reason_hunk.get("failure_reason_hunk_priority_basis"),
        "failure_reason_hunk_secondary_conflict_status": failure_reason_hunk.get("failure_reason_hunk_secondary_conflict_status"),
        "failure_reason_hunk_secondary_conflict_count": failure_reason_hunk.get("failure_reason_hunk_secondary_conflict_count"),
        "failure_reason_hunk_secondary_conflict_reasons": failure_reason_hunk.get("failure_reason_hunk_secondary_conflict_reasons"),
        "failure_reason_hunk_deferred_reason_codes": failure_reason_hunk.get("failure_reason_hunk_deferred_reason_codes"),
        "rollback_status": rollback_status,
        "build_probe_status": build_status,
        "smoke_probe_status": smoke_status,
        "apply_candidate_manifest_path": str(manifest_path),
        "apply_result_manifest_path": str(result_path),
    }


def build_harness_probe_draft(repo_root: Path) -> dict[str, object]:
    return build_harness_probe_draft_impl(repo_root)


def run_short_harness_probe(
    repo_root: Path,
    *,
    probe_runner: Callable[[list[str], Path], tuple[int, str]] | None = None,
) -> dict[str, object]:
    return run_short_harness_probe_impl(repo_root, probe_runner=probe_runner or run_quiet)


def bridge_harness_probe_feedback(repo_root: Path) -> dict[str, object]:
    return bridge_harness_probe_feedback_impl(repo_root)


def route_harness_probe_feedback(repo_root: Path) -> dict[str, object]:
    decision = build_probe_routing_decision_impl(repo_root)
    if not decision.get("routed"):
        return decision
    automation_dir = repo_root / "fuzz-artifacts" / "automation"
    registry_name = decision.get("registry_name")
    if isinstance(registry_name, str):
        registry_path = automation_dir / registry_name
        registry = load_registry(registry_path, {"entries": []})
        entries = registry.get("entries") if isinstance(registry.get("entries"), list) else []
        action_code = decision.get("action_code")
        target_entry = next((entry for entry in entries if isinstance(entry, dict) and entry.get("action_code") == action_code), None)
        if isinstance(target_entry, dict):
            target_entry["selected_candidate_id"] = decision.get("selected_candidate_id")
            target_entry["selected_entrypoint_path"] = decision.get("selected_entrypoint_path")
            target_entry["selected_recommended_mode"] = decision.get("selected_recommended_mode")
            target_entry["selected_target_stage"] = decision.get("selected_target_stage")
            save_registry(registry_path, registry)
    orchestration = prepare_next_refiner_orchestration(automation_dir, repo_root=repo_root)
    dispatch = dispatch_next_refiner_orchestration(automation_dir, repo_root=repo_root)
    handoff = {
        **decision,
        "orchestration_status": orchestration.get("orchestration_status") if orchestration else None,
        "dispatch_status": dispatch.get("dispatch_status") if dispatch else None,
        "dispatch_channel": dispatch.get("dispatch_channel") if dispatch else (orchestration.get("dispatch_channel") if orchestration else None),
        "orchestration_manifest_path": orchestration.get("manifest_path") if orchestration else None,
        "delegate_task_request_path": dispatch.get("delegate_task_request_path") if dispatch else None,
        "cronjob_request_path": dispatch.get("cronjob_request_path") if dispatch else None,
    }
    return write_probe_routing_handoff_impl(repo_root, handoff)


def select_next_ranked_candidate(repo_root: Path) -> dict[str, object]:
    return select_next_ranked_candidate_impl(repo_root)


def update_ranked_candidate_registry(repo_root: Path) -> dict[str, object]:
    return update_ranked_candidate_registry_impl(repo_root)


def extract_stack_frames(lines: list[str]) -> list[dict[str, object]]:
    frames: list[dict[str, object]] = []
    seen: set[tuple[str | None, str, int]] = set()
    for raw_line in lines:
        line = raw_line.strip()
        stack_match = STACK_FRAME_RE.search(line)
        if stack_match:
            item = {
                "index": int(stack_match.group("index")),
                "function": stack_match.group("function").strip(),
                "path": stack_match.group("path"),
                "line": int(stack_match.group("line")),
            }
            key = (item["function"], str(item["path"]), int(item["line"]))
            if key not in seen:
                seen.add(key)
                frames.append(item)
            continue
        location_match = LOCATION_RE.search(line)
        if location_match:
            item = {
                "index": len(frames),
                "function": None,
                "path": location_match.group("path"),
                "line": int(location_match.group("line")),
            }
            key = (item["function"], str(item["path"]), int(item["line"]))
            if key not in seen:
                seen.add(key)
                frames.append(item)
    return frames


def _stage_meta_map(profile: dict[str, object] | None) -> dict[str, dict[str, object]]:
    if not isinstance(profile, dict):
        return {}
    stages = profile.get("stages")
    if not isinstance(stages, list):
        return {}
    result: dict[str, dict[str, object]] = {}
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        stage_id = stage.get("id")
        if isinstance(stage_id, str):
            result[stage_id] = stage
    return result


def _suffix_matches(candidate_path: str, configured_path: str) -> bool:
    normalized_candidate = candidate_path.replace("\\", "/")
    normalized_configured = configured_path.replace("\\", "/")
    return normalized_candidate.endswith(normalized_configured)


def classify_crash_stage(lines: list[str], profile: dict[str, object] | None) -> dict[str, object]:
    unknown = {
        "stage": None,
        "stage_class": "unknown",
        "depth_rank": None,
        "confidence": "none",
        "match_source": None,
        "reason": "no profile match",
    }
    if not isinstance(profile, dict):
        return unknown

    frames = extract_stack_frames(lines)
    text_blob = "\n".join(lines)
    stage_meta = _stage_meta_map(profile)
    candidates: list[dict[str, object]] = []

    hotspots = profile.get("hotspots") if isinstance(profile.get("hotspots"), dict) else {}
    hotspot_functions = hotspots.get("functions") if isinstance(hotspots.get("functions"), list) else []
    for frame in frames:
        function_name = frame.get("function")
        if not isinstance(function_name, str):
            continue
        for hotspot in hotspot_functions:
            if not isinstance(hotspot, dict):
                continue
            hotspot_name = hotspot.get("name")
            stage_id = hotspot.get("stage")
            if hotspot_name == function_name and isinstance(stage_id, str):
                candidates.append(
                    {
                        "stage": stage_id,
                        "score": 100 - int(frame.get("index", 0)),
                        "match_source": "function",
                        "reason": f"function match: {function_name}",
                    }
                )

    stages = profile.get("stages") if isinstance(profile.get("stages"), list) else []
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        stage_id = stage.get("id")
        if not isinstance(stage_id, str):
            continue
        expected_signals = stage.get("expected_signals") if isinstance(stage.get("expected_signals"), list) else []
        for signal in expected_signals:
            if isinstance(signal, str) and signal and signal in text_blob:
                candidates.append(
                    {
                        "stage": stage_id,
                        "score": 80,
                        "match_source": "signal",
                        "reason": f"expected signal match: {signal}",
                    }
                )

    telemetry = profile.get("telemetry") if isinstance(profile.get("telemetry"), dict) else {}
    stack_tagging = telemetry.get("stack_tagging") if isinstance(telemetry.get("stack_tagging"), dict) else {}
    stage_file_map = stack_tagging.get("stage_file_map") if isinstance(stack_tagging.get("stage_file_map"), dict) else {}
    for frame in frames:
        frame_path = frame.get("path")
        if not isinstance(frame_path, str):
            continue
        for stage_id, configured_paths in stage_file_map.items():
            if not isinstance(stage_id, str) or not isinstance(configured_paths, list):
                continue
            for configured_path in configured_paths:
                if isinstance(configured_path, str) and _suffix_matches(frame_path, configured_path):
                    candidates.append(
                        {
                            "stage": stage_id,
                            "score": 60 - int(frame.get("index", 0)),
                            "match_source": "file",
                            "reason": f"file map match: {configured_path}",
                        }
                    )

    if not candidates:
        return unknown

    best = max(candidates, key=lambda item: (int(item.get("score", 0)), -len(str(item.get("stage", "")))))
    stage_id = best["stage"]
    meta = stage_meta.get(stage_id, {})
    score = int(best.get("score", 0))
    confidence = "high" if score >= 90 else "medium" if score >= 60 else "low"
    return {
        "stage": stage_id,
        "stage_class": meta.get("stage_class", "unknown"),
        "depth_rank": meta.get("depth_rank"),
        "confidence": confidence,
        "match_source": best.get("match_source"),
        "reason": best.get("reason"),
    }


def enrich_crash_info_with_stage_info(
    crash_info: dict[str, object] | None,
    lines: list[str],
    profile: dict[str, object] | None,
) -> dict[str, object] | None:
    if crash_info is None:
        return None
    stage_info = classify_crash_stage(lines, profile)
    enriched = dict(crash_info)
    enriched["stage"] = stage_info.get("stage")
    enriched["stage_class"] = stage_info.get("stage_class")
    enriched["stage_depth_rank"] = stage_info.get("depth_rank")
    enriched["stage_confidence"] = stage_info.get("confidence")
    enriched["stage_match_source"] = stage_info.get("match_source")
    enriched["stage_reason"] = stage_info.get("reason")
    return enriched


def metrics_snapshot(
    *,
    outcome: str,
    metrics: Metrics,
    run_dir: Path,
    report_path: Path,
    start: float,
    crash_info: dict[str, object] | None = None,
    artifact_event: dict[str, object] | None = None,
    policy_action: dict[str, object] | None = None,
    policy_execution: dict[str, object] | None = None,
    target_profile_summary: dict[str, object] | None = None,
    notification_event: dict[str, object] | None = None,
) -> dict[str, object]:
    now = time.monotonic()
    snapshot = {
        "outcome": outcome,
        "duration_seconds": round(now - start, 1),
        "duration": format_duration(now - start),
        "seconds_since_progress": round(now - metrics.last_progress_at, 1),
        "since_progress": format_duration(now - metrics.last_progress_at),
        "cov": metrics.cov,
        "ft": metrics.ft,
        "corpus_units": metrics.corp_units,
        "corpus_size": metrics.corp_size,
        "exec_per_second": metrics.execs,
        "rss": metrics.rss,
        "crash_detected": metrics.crash,
        "timeout_detected": metrics.timeout,
        "run_dir": str(run_dir),
        "report": str(report_path),
        "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    if crash_info:
        snapshot.update(
            {
                "crash_fingerprint": crash_info.get("fingerprint"),
                "crash_kind": crash_info.get("kind"),
                "crash_location": crash_info.get("location"),
                "crash_summary": crash_info.get("summary"),
                "crash_artifact": crash_info.get("artifact_path"),
                "crash_artifact_sha1": crash_info.get("artifact_sha1"),
                "crash_is_duplicate": crash_info.get("is_duplicate"),
                "crash_occurrence_count": crash_info.get("occurrence_count"),
                "crash_first_seen_run": crash_info.get("first_seen_run"),
                "crash_stage": crash_info.get("stage"),
                "crash_stage_class": crash_info.get("stage_class"),
                "crash_stage_depth_rank": crash_info.get("stage_depth_rank"),
                "crash_stage_confidence": crash_info.get("stage_confidence"),
                "crash_stage_match_source": crash_info.get("stage_match_source"),
                "crash_stage_reason": crash_info.get("stage_reason"),
            }
        )
    if artifact_event:
        snapshot.update(
            {
                "artifact_category": artifact_event.get("category"),
                "artifact_reason": artifact_event.get("reason"),
            }
        )
    if policy_action:
        snapshot.update(
            {
                "policy_priority": policy_action.get("priority"),
                "policy_action_code": policy_action.get("action_code"),
                "policy_recommended_action": policy_action.get("recommended_action"),
                "policy_next_mode": policy_action.get("next_mode"),
                "policy_bucket": policy_action.get("bucket"),
                "policy_matched_triggers": policy_action.get("matched_triggers"),
                "policy_profile_severity": policy_action.get("profile_severity"),
                "policy_profile_labels": policy_action.get("profile_labels"),
            }
        )
    if policy_execution:
        snapshot.update(
            {
                "policy_execution_updated": policy_execution.get("updated"),
                "regression_trigger": policy_execution.get("regression_trigger"),
            }
        )
    if target_profile_summary:
        snapshot.update(
            {
                "target_profile_name": target_profile_summary.get("name"),
                "target_profile_path": target_profile_summary.get("path"),
                "target_profile_project": target_profile_summary.get("project"),
                "target_profile_primary_mode": target_profile_summary.get("primary_mode"),
                "target_profile_primary_binary": target_profile_summary.get("primary_binary"),
                "target_profile_stage_count": target_profile_summary.get("stage_count"),
                "target_profile_load_status": target_profile_summary.get("load_status"),
                "target_profile_load_error": target_profile_summary.get("load_error"),
                "target_profile_load_error_detail": target_profile_summary.get("load_error_detail"),
                "target_profile_validation_status": target_profile_summary.get("validation_status"),
                "target_profile_validation_severity": target_profile_summary.get("validation_severity"),
                "target_profile_validation_codes": target_profile_summary.get("validation_codes"),
            }
        )
    if notification_event:
        snapshot.update(
            {
                "notification_status": notification_event.get("status"),
                "notification_transport": notification_event.get("transport"),
                "notification_reason": notification_event.get("reason"),
                "notification_error": notification_event.get("error"),
                "notification_error_type": notification_event.get("error_type"),
                "notification_context": notification_event.get("context"),
            }
        )
    return snapshot


def write_status(status_path: Path, snapshot: dict[str, object]) -> None:
    tmp_path = status_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(status_path)


def classify_crash_kind(lines: list[str]) -> str:
    joined = "\n".join(lines)
    if "UndefinedBehaviorSanitizer" in joined:
        return "ubsan"
    if "LeakSanitizer" in joined:
        return "leak"
    if "AddressSanitizer" in joined:
        return "asan"
    if "libFuzzer" in joined or "deadly signal" in joined:
        return "libfuzzer"
    if TIMEOUT_RE.search(joined):
        return "timeout"
    return "unknown"


def extract_primary_location(lines: list[str]) -> str | None:
    stack_frames: list[tuple[str, str, str]] = []
    for line in lines:
        match = STACK_FRAME_RE.search(line)
        if match:
            stack_frames.append(
                (
                    match.group("function").strip(),
                    match.group("path"),
                    match.group("line"),
                )
            )

    if classify_crash_kind(lines) == "leak" and stack_frames:
        for function, path, line in stack_frames:
            lowered_function = function.lower()
            lowered_path = path.lower()
            if any(hint in lowered_function for hint in LEAK_ALLOCATOR_FRAME_HINTS):
                continue
            if any(hint in lowered_path for hint in LEAK_ALLOCATOR_PATH_HINTS):
                continue
            return f"{Path(path).name}:{line}"

    for _function, path, line in stack_frames:
        return f"{Path(path).name}:{line}"

    for line in lines:
        match = LOCATION_RE.search(line)
        if match:
            return f"{Path(match.group('path')).name}:{match.group('line')}"
    return None


def extract_summary_text(lines: list[str]) -> str | None:
    for line in lines:
        match = SUMMARY_RE.search(line)
        if match:
            return match.group("summary").strip()
    for line in lines:
        if "runtime error:" in line:
            return line.split("runtime error:", 1)[1].strip()
    return None


def extract_artifact_path(lines: list[str]) -> str | None:
    for line in lines:
        match = ARTIFACT_RE.search(line)
        if match:
            return match.group("path")
    return None


def sha1_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_crash_signature(lines: list[str]) -> dict[str, str | None]:
    kind = classify_crash_kind(lines)
    location = extract_primary_location(lines)
    summary = extract_summary_text(lines)
    artifact_path = extract_artifact_path(lines)
    artifact_sha1 = sha1_file(Path(artifact_path)) if artifact_path else None
    fingerprint = "|".join(
        [
            kind,
            location or "unknown-location",
            summary or "unknown-summary",
        ]
    )
    return {
        "kind": kind,
        "location": location,
        "summary": summary,
        "artifact_path": artifact_path,
        "artifact_sha1": artifact_sha1,
        "fingerprint": fingerprint,
    }


def load_crash_index(index_path: Path) -> dict[str, object]:
    default = {"fingerprints": {}}
    if not index_path.exists():
        return default
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {**default, "__load_error__": "json-decode-error"}
    if not isinstance(data, dict):
        return {**default, "__load_error__": "invalid-top-level-type"}
    fingerprints = data.get("fingerprints")
    if fingerprints is None:
        data["fingerprints"] = {}
    elif not isinstance(fingerprints, dict):
        data["fingerprints"] = {}
        data["__load_error__"] = "invalid-fingerprints-type"
    return data


def save_crash_index(index_path: Path, data: dict[str, object]) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = index_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(index_path)


def update_crash_index(
    index_path: Path,
    signature: dict[str, str | None],
    *,
    run_dir: str,
    report_path: str,
) -> dict[str, object]:
    data = load_crash_index(index_path)
    fingerprints = data.setdefault("fingerprints", {})
    fingerprint = signature["fingerprint"]
    assert fingerprint is not None
    record = fingerprints.get(fingerprint)
    if record is None:
        record = {
            "kind": signature.get("kind"),
            "location": signature.get("location"),
            "summary": signature.get("summary"),
            "artifact_sha1": signature.get("artifact_sha1"),
            "first_seen_run": run_dir,
            "first_seen_report": report_path,
            "last_seen_run": run_dir,
            "last_seen_report": report_path,
            "occurrence_count": 1,
            "artifacts": [signature.get("artifact_path")] if signature.get("artifact_path") else [],
        }
        fingerprints[fingerprint] = record
        is_duplicate = False
    else:
        record["occurrence_count"] = int(record.get("occurrence_count", 0)) + 1
        record["last_seen_run"] = run_dir
        record["last_seen_report"] = report_path
        artifact_path = signature.get("artifact_path")
        if artifact_path:
            artifacts = record.setdefault("artifacts", [])
            if artifact_path not in artifacts:
                artifacts.append(artifact_path)
        is_duplicate = True
    save_crash_index(index_path, data)
    return {
        "fingerprint": fingerprint,
        "is_duplicate": is_duplicate,
        "occurrence_count": record["occurrence_count"],
        "first_seen_run": record["first_seen_run"],
        "first_seen_report": record.get("first_seen_report"),
        "last_seen_run": record["last_seen_run"],
        "last_seen_report": record.get("last_seen_report"),
        "first_artifact_path": (record.get("artifacts") or [None])[0] if isinstance(record.get("artifacts"), list) and record.get("artifacts") else None,
        "artifacts": list(record.get("artifacts") or []) if isinstance(record.get("artifacts"), list) else [],
        "artifact_sha1": signature.get("artifact_sha1"),
        "artifact_path": signature.get("artifact_path"),
        "kind": signature.get("kind"),
        "location": signature.get("location"),
        "summary": signature.get("summary"),
    }


def repair_crash_index_entry(
    index_path: Path,
    *,
    previous_fingerprint: str | None,
    signature: dict[str, str | None],
    run_dir: str,
    report_path: str,
) -> dict[str, object]:
    data = load_crash_index(index_path)
    fingerprints = data.setdefault("fingerprints", {})
    target_fingerprint = str(signature.get("fingerprint") or "")
    if not target_fingerprint:
        raise ValueError("signature fingerprint required")

    previous_record = None
    if previous_fingerprint and previous_fingerprint != target_fingerprint:
        previous_record = fingerprints.pop(previous_fingerprint, None)
        if not isinstance(previous_record, dict):
            previous_record = None

    existing_record = fingerprints.get(target_fingerprint)
    if not isinstance(existing_record, dict):
        existing_record = None

    record = dict(existing_record or previous_record or {})
    record["kind"] = signature.get("kind")
    record["location"] = signature.get("location")
    record["summary"] = signature.get("summary")
    record["artifact_sha1"] = signature.get("artifact_sha1")
    record["first_seen_run"] = str(record.get("first_seen_run") or run_dir)
    record["first_seen_report"] = str(record.get("first_seen_report") or report_path)
    record["last_seen_run"] = run_dir
    record["last_seen_report"] = report_path
    record["occurrence_count"] = max(1, int(record.get("occurrence_count") or 0))
    merged_artifacts: list[str] = []
    for source in [previous_record, existing_record, record]:
        if not isinstance(source, dict):
            continue
        artifacts = source.get("artifacts")
        if isinstance(artifacts, list):
            for artifact in artifacts:
                if isinstance(artifact, str) and artifact and artifact not in merged_artifacts:
                    merged_artifacts.append(artifact)
    artifact_path = signature.get("artifact_path")
    if artifact_path and artifact_path not in merged_artifacts:
        merged_artifacts.append(str(artifact_path))
    record["artifacts"] = merged_artifacts
    fingerprints[target_fingerprint] = record
    save_crash_index(index_path, data)
    return {
        "fingerprint": target_fingerprint,
        "is_duplicate": int(record.get("occurrence_count") or 0) > 1 or str(record.get("first_seen_run") or "") != run_dir,
        "occurrence_count": record["occurrence_count"],
        "first_seen_run": record["first_seen_run"],
        "first_seen_report": record.get("first_seen_report"),
        "last_seen_run": record["last_seen_run"],
        "last_seen_report": record.get("last_seen_report"),
        "first_artifact_path": (record.get("artifacts") or [None])[0] if isinstance(record.get("artifacts"), list) and record.get("artifacts") else None,
        "artifacts": list(record.get("artifacts") or []) if isinstance(record.get("artifacts"), list) else [],
        "artifact_sha1": signature.get("artifact_sha1"),
        "artifact_path": signature.get("artifact_path"),
        "kind": signature.get("kind"),
        "location": signature.get("location"),
        "summary": signature.get("summary"),
    }


def classify_artifact_event(outcome: str, crash_info: dict[str, object] | None) -> dict[str, str | None]:
    if outcome == "no-progress":
        return {"category": "no-progress", "reason": "stalled-coverage-or-corpus"}
    if outcome == "timeout":
        return {"category": "timeout", "reason": "watcher-timeout"}
    if outcome == "smoke-failed":
        return {"category": "smoke-failed", "reason": "baseline-input-failed"}
    if outcome == "build-failed":
        return {"category": "build-failed", "reason": "build-or-config-error"}
    if crash_info:
        kind = crash_info.get("kind")
        if kind == "leak":
            return {"category": "leak", "reason": "sanitizer-leak"}
        if kind == "timeout":
            return {"category": "timeout", "reason": "sanitizer-timeout"}
        if kind in {"ubsan", "asan", "libfuzzer", "unknown"}:
            return {"category": "crash", "reason": "sanitizer-crash"}
    if outcome == "crash":
        return {"category": "crash", "reason": "generic-crash"}
    if outcome == "fuzzer-exit-nonzero":
        return {"category": "fuzzer-exit", "reason": "nonzero-exit-without-clear-signature"}
    return {"category": outcome, "reason": None}


def priority_rank(priority: str | None) -> int:
    ranks = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    return ranks.get(str(priority).lower(), 0)


def _infer_crash_labels(crash_info: dict[str, object] | None) -> set[str]:
    labels: set[str] = set()
    if not crash_info:
        return labels
    summary = str(crash_info.get("summary") or "").lower()
    stage = str(crash_info.get("stage") or "")
    stage_class = str(crash_info.get("stage_class") or "")

    if "use-after-free" in summary:
        labels.add("use-after-free")
    if "double-free" in summary:
        labels.add("double-free")
    if "invalid-free" in summary or "attempting free" in summary:
        labels.add("invalid-free")
    if "stack-buffer-overflow" in summary:
        labels.add("stack-buffer-overflow")
    if "heap-buffer-overflow" in summary:
        labels.add("heap-buffer-overflow")
        if "write" in summary:
            labels.add("heap-buffer-overflow-write")
    if "segv" in summary or " deadly signal" in summary or summary.startswith("segv"):
        if "write" in summary:
            labels.add("segv-write")
        else:
            labels.add("segv-read")
    if "null" in summary and stage_class == "deep":
        labels.add("null-deref-deep-stage")
    if "fpe" in summary and stage_class == "deep":
        labels.add("fpe-in-decode-stage")
    if stage == "parse-main-header" and "heap-buffer-overflow" in summary and "read" in summary:
        labels.add("parser-only heap read overflow")
    if stage == "parse-main-header" and "null" in summary:
        labels.add("parser-shallow-null-deref")
    if stage == "tile-part-load" and "write" in summary:
        labels.add("add_tile_part-write")
    if stage == "ht-block-decode" and "overflow" in summary:
        labels.add("ht-block-decode-overflow")
    if stage == "line-based-decode" and "overflow" in summary:
        labels.add("create_subbands-overflow")
    return labels


def evaluate_profile_policy(
    outcome: str,
    artifact_event: dict[str, str | None],
    crash_info: dict[str, object] | None,
    profile: dict[str, object] | None,
) -> dict[str, object]:
    result = {
        "severity": None,
        "labels": [],
        "matched_triggers": [],
        "override_action_code": None,
        "override_priority": None,
        "override_bucket": None,
    }
    if not isinstance(profile, dict):
        return result

    labels = _infer_crash_labels(crash_info)
    result["labels"] = sorted(labels)

    crash_policy = profile.get("crash_policy") if isinstance(profile.get("crash_policy"), dict) else {}
    buckets = crash_policy.get("buckets") if isinstance(crash_policy.get("buckets"), dict) else {}
    severity = None
    for bucket_name in ["critical", "high", "medium", "low"]:
        bucket_labels = buckets.get(bucket_name)
        if isinstance(bucket_labels, list) and any(label in labels for label in bucket_labels if isinstance(label, str)):
            severity = bucket_name
            break

    stage_bias = crash_policy.get("stage_bias") if isinstance(crash_policy.get("stage_bias"), dict) else {}
    stage = str(crash_info.get("stage") or "") if crash_info else ""
    bias = stage_bias.get(stage)
    if severity == "high" and bias == "strongly_raise":
        severity = "critical"
    elif severity == "medium" and bias in {"raise", "strongly_raise", "raise_if_write_flavor"}:
        severity = "high"
    elif severity == "high" and bias == "raise_if_write_flavor" and any(label in labels for label in {"segv-write", "heap-buffer-overflow-write", "add_tile_part-write"}):
        severity = "critical"
    elif severity in {"high", "medium"} and bias == "demote_if_only_read_flavor" and labels <= {"heap-buffer-overflow", "parser-only heap read overflow", "segv-read", "parser-shallow-null-deref"}:
        severity = "low"
    elif severity is None and stage == "parse-main-header" and "heap-buffer-overflow" in labels:
        severity = "low"

    result["severity"] = severity

    triggers = profile.get("triggers") if isinstance(profile.get("triggers"), dict) else {}
    matched_triggers: list[str] = []
    chosen_action = None

    deep_write = triggers.get("deep_write_crash") if isinstance(triggers.get("deep_write_crash"), dict) else None
    if deep_write and deep_write.get("enabled"):
        condition = deep_write.get("condition") if isinstance(deep_write.get("condition"), dict) else {}
        min_rank = int(condition.get("min_stage_depth_rank", 0) or 0)
        trigger_labels = {str(item) for item in condition.get("sanitizer_match", []) if isinstance(item, str)}
        stage_rank = int(crash_info.get("stage_depth_rank") or 0) if crash_info else 0
        if stage_rank >= min_rank and labels & trigger_labels:
            matched_triggers.append("deep_write_crash")
            chosen_action = str(deep_write.get("action") or chosen_action or "")

    deep_signal = triggers.get("deep_signal_emergence") if isinstance(triggers.get("deep_signal_emergence"), dict) else None
    if deep_signal and deep_signal.get("enabled") and crash_info:
        condition = deep_signal.get("condition") if isinstance(deep_signal.get("condition"), dict) else {}
        stage_any_of = {str(item) for item in condition.get("stage_any_of", []) if isinstance(item, str)}
        min_new = int(condition.get("min_new_reproducible_families", 0) or 0)
        is_new_family = not bool(crash_info.get("is_duplicate"))
        if stage in stage_any_of and is_new_family and min_new <= 1 and artifact_event.get("category") == "crash":
            matched_triggers.append("deep_signal_emergence")
            if chosen_action is None:
                chosen_action = str(deep_signal.get("action") or "")

    result["matched_triggers"] = matched_triggers

    if chosen_action:
        result["override_action_code"] = chosen_action
        result["override_priority"] = severity or "high"
        result["override_bucket"] = severity or "triage"
    return result


def decide_policy_action(
    outcome: str,
    artifact_event: dict[str, str | None],
    crash_info: dict[str, object] | None,
    profile: dict[str, object] | None = None,
    history: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    category = artifact_event.get("category")
    profile_eval = evaluate_profile_policy(outcome, artifact_event, crash_info, profile)
    history_eval = evaluate_history_triggers(history or [], profile)
    if category == "build-failed":
        action = {
            "priority": "high",
            "action_code": "fix-build-before-fuzzing",
            "recommended_action": "Fix build/config/compiler issues before any more fuzzing runs.",
            "next_mode": "regression",
            "bucket": "build",
        }
    elif category == "smoke-failed":
        action = {
            "priority": "high",
            "action_code": "promote-seed-to-regression-and-triage",
            "recommended_action": "Treat the failing baseline input as a regression/triage seed and investigate decoder stability.",
            "next_mode": "triage",
            "bucket": "regression",
        }
    elif category == "leak":
        action = {
            "priority": "medium",
            "action_code": "triage-leak-and-consider-coverage-policy",
            "recommended_action": "Record the leak, inspect allocation/free paths, and decide whether coverage mode should keep detect_leaks=0.",
            "next_mode": "coverage",
            "bucket": "triage",
        }
    elif category == "timeout":
        action = {
            "priority": "medium",
            "action_code": "inspect-slow-path-or-timeout-policy",
            "recommended_action": "Inspect timeout path, consider smaller limits or timeout-specific seeds, and keep the reproducer.",
            "next_mode": "triage",
            "bucket": "triage",
        }
    elif category == "no-progress":
        action = {
            "priority": "medium",
            "action_code": "improve-corpus-or-harness",
            "recommended_action": "Improve seed diversity or harness reachability before running longer campaigns.",
            "next_mode": "coverage",
            "bucket": "coverage",
        }
    elif category == "crash":
        is_duplicate = bool(crash_info.get("is_duplicate")) if crash_info else False
        if is_duplicate:
            occurrence_count = int(crash_info.get("occurrence_count") or 0) if crash_info else 0
            stage_class = str(crash_info.get("stage_class") or "") if crash_info else ""
            stage_depth_rank = int(crash_info.get("stage_depth_rank") or 0) if crash_info else 0
            repeated_duplicate_replay_candidate = occurrence_count >= 2 and (
                stage_class in {"medium", "deep"} or stage_depth_rank >= 2
            )
            if repeated_duplicate_replay_candidate:
                action = {
                    "priority": "high",
                    "action_code": "review_duplicate_crash_replay",
                    "recommended_action": "Preserve duplicate family evidence, compare first and latest repros, and prepare replay/minimization triage instead of only filing this as known-bad.",
                    "next_mode": "triage",
                    "bucket": "triage",
                }
            else:
                action = {
                    "priority": "medium",
                    "action_code": "record-duplicate-crash",
                    "recommended_action": "Record duplicate occurrence, keep regression coverage, and avoid over-prioritizing this known crash.",
                    "next_mode": "coverage",
                    "bucket": "known-bad",
                }
        else:
            action = {
                "priority": "high",
                "action_code": "triage-new-crash",
                "recommended_action": "Preserve artifact, inspect stack, and promote the reproducer into triage/regression tracking.",
                "next_mode": "triage",
                "bucket": "triage",
            }
    elif category == "fuzzer-exit":
        action = {
            "priority": "medium",
            "action_code": "inspect-nonzero-exit",
            "recommended_action": "Inspect fuzzer exit logs and determine whether the run should be reclassified into a clearer bucket.",
            "next_mode": "triage",
            "bucket": "triage",
        }
    else:
        action = {
            "priority": "low",
            "action_code": "continue-observing",
            "recommended_action": "No specific action selected; continue observing and recording outcomes.",
            "next_mode": None,
            "bucket": None,
        }

    action["profile_severity"] = profile_eval.get("severity")
    action["profile_labels"] = profile_eval.get("labels")
    action["matched_triggers"] = list(profile_eval.get("matched_triggers") or [])
    action["history_dominant_stage"] = history_eval.get("dominant_stage")
    action["semantic_summary"] = history_eval.get("semantic_summary")

    override_priority = profile_eval.get("override_priority")
    override_action_code = profile_eval.get("override_action_code")
    override_bucket = profile_eval.get("override_bucket")
    history_priority = history_eval.get("override_priority")
    history_action_code = history_eval.get("override_action_code")
    history_bucket = history_eval.get("override_bucket")
    if history_eval.get("matched_triggers"):
        action["matched_triggers"] = list(action["matched_triggers"]) + [
            item for item in history_eval.get("matched_triggers", []) if item not in action["matched_triggers"]
        ]
    if override_action_code and priority_rank(str(override_priority)) >= priority_rank(str(action.get("priority"))):
        action["priority"] = override_priority
        action["action_code"] = override_action_code
        action["bucket"] = override_bucket
        if override_action_code == "high_priority_alert":
            action["recommended_action"] = "Escalate immediately: preserve reproducer, alert, and prioritize deep write-flavor triage."
            action["next_mode"] = "triage"
        elif override_action_code == "continue_and_prioritize_triage":
            action["recommended_action"] = "Keep the run going but prioritize this new deep-stage crash family in triage."
    if history_action_code and priority_rank(str(history_priority)) >= priority_rank(str(action.get("priority"))):
        action["priority"] = history_priority
        action["action_code"] = history_action_code
        action["bucket"] = history_bucket
        if history_action_code == "shift_weight_to_deeper_harness":
            action["recommended_action"] = "Recent crash history is dominated by shallow parser-stage families; shift weight toward deeper harness/mode selection."
            action["next_mode"] = "coverage"
        elif history_action_code == "propose_harness_revision":
            action["recommended_action"] = "Recent runs show stagnant coverage with adequate throughput; propose harness or corpus revision."
            action["next_mode"] = "coverage"
        elif history_action_code == "split_slow_lane":
            action["recommended_action"] = "Recent runs show sustained timeout pressure; split slow seeds/hangs into a separate lane."
            action["next_mode"] = "coverage"
        elif history_action_code == "minimize_and_reseed":
            action["recommended_action"] = "Corpus is growing faster than useful coverage; minimize and reseed before continuing broad growth."
            action["next_mode"] = "coverage"
        elif history_action_code == "halt_and_review_harness":
            action["recommended_action"] = "Recent crash history looks unstable and shallow-heavy; halt and review harness determinism before continuing."
            action["next_mode"] = "coverage"
    return action


def load_registry(path: Path, default: dict[str, object]) -> dict[str, object]:
    if not path.exists():
        return dict(default)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {**dict(default), "__load_error__": "json-decode-error"}
    if not isinstance(data, dict):
        return {**dict(default), "__load_error__": "invalid-top-level-type"}
    merged = dict(default)
    merged.update(data)
    return merged


def save_registry(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def queue_harness_apply_recovery_followup(
    automation_dir: Path,
    *,
    repo_root: Path,
    recovery_decision: str,
    manifest: dict[str, object],
    routing_entry: dict[str, object] | None = None,
) -> dict[str, object] | None:
    action_code = ""
    registry_name = ""
    reason = ""
    if recovery_decision == "hold":
        action_code = "halt_and_review_harness"
        registry_name = "harness_review_queue.json"
        reason = "hold-review-lane"
    elif recovery_decision == "abort":
        action_code = "regenerate_harness_correction"
        registry_name = "harness_correction_regeneration_queue.json"
        reason = "abort-corrective-route"
    else:
        return None

    project = str(manifest.get("generated_from_project") or repo_root.name)
    candidate_id = str(manifest.get("selected_candidate_id") or "candidate-1")
    recovery_summary = str((routing_entry or {}).get("recovery_summary") or manifest.get("recovery_summary") or "")
    run_dir = f"/runs/harness-apply-{recovery_decision}-{candidate_id}"
    entry = {
        "key": f"{action_code}:{project}:{candidate_id}",
        "action_code": action_code,
        "run_dir": run_dir,
        "report_path": str((routing_entry or {}).get("recovery_route_plan_path") or manifest.get("recovery_route_plan_path") or ""),
        "outcome": str(manifest.get("apply_status") or recovery_decision),
        "recommended_action": recovery_summary or action_code.replace("_", "-"),
        "selected_candidate_id": candidate_id,
        "selected_entrypoint_path": manifest.get("selected_entrypoint_path"),
        "selected_recommended_mode": manifest.get("selected_recommended_mode"),
        "selected_target_stage": manifest.get("selected_target_stage"),
        "generated_from_project": project,
        "target_file_path": manifest.get("target_file_path"),
        "recovery_decision": recovery_decision,
        "recovery_summary": recovery_summary,
        "apply_candidate_manifest_path": manifest.get("apply_candidate_manifest_path"),
        "apply_result_manifest_path": manifest.get("apply_result_manifest_path"),
        "recovery_route_manifest_path": (routing_entry or {}).get("recovery_route_manifest_path") or manifest.get("recovery_route_manifest_path"),
        "recovery_route_plan_path": (routing_entry or {}).get("recovery_route_plan_path") or manifest.get("recovery_route_plan_path"),
        "recovery_followup_reason": reason,
    }
    result = record_refiner_entry(
        automation_dir,
        registry_name=registry_name,
        unique_key="key",
        entry=entry,
    )
    return {
        "action_code": action_code,
        "registry_name": registry_name,
        "created": bool(result.get("created")),
        "count": int(result.get("count") or 0),
        "reason": reason,
        "entry_key": entry["key"],
        "path": str(automation_dir / registry_name),
    }


def append_unique_entry(entries: list[dict[str, object]], candidate: dict[str, object], unique_key: str) -> bool:
    for entry in entries:
        if entry.get(unique_key) == candidate.get(unique_key):
            return False
    entries.append(candidate)
    return True



def _merge_refiner_entry(existing: dict[str, object], candidate: dict[str, object]) -> bool:
    updated = False
    for key, value in candidate.items():
        if value is None or value == "":
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        if existing.get(key) != value:
            existing[key] = value
            updated = True
    return updated



def record_refiner_entry(
    automation_dir: Path,
    *,
    registry_name: str,
    unique_key: str,
    entry: dict[str, object],
    merge_existing: bool = False,
) -> dict[str, object]:
    path = automation_dir / registry_name
    data = load_registry(path, {"entries": []})
    entries = data.setdefault("entries", [])
    created = False
    updated = False
    if merge_existing:
        for existing in entries:
            if existing.get(unique_key) == entry.get(unique_key):
                updated = _merge_refiner_entry(existing, entry)
                break
        else:
            entries.append(entry)
            created = True
    else:
        created = append_unique_entry(entries, entry, unique_key)
    save_registry(path, data)
    return {"path": str(path), "created": created, "updated": updated, "count": len(entries)}

def derive_refiner_lifecycle(entry: dict[str, object]) -> str:
    policy_status = str(entry.get("verification_policy_status") or "")
    if policy_status == "escalate":
        return "escalated"
    if policy_status == "retry":
        return "retry_requested"

    verification_status = str(entry.get("verification_status") or "")
    if verification_status == "verified":
        return "verified"
    if verification_status == "unverified":
        return "verification_failed"

    launch_status = str(entry.get("launch_status") or "")
    if launch_status == "succeeded":
        return "launch_succeeded"
    if launch_status == "failed":
        return "launch_failed"

    bridge_status = str(entry.get("bridge_status") or "")
    if bridge_status == "armed":
        return "bridge_armed"
    if bridge_status == "failed":
        return "bridge_failed"
    if bridge_status == "succeeded":
        return "launch_succeeded"

    dispatch_status = str(entry.get("dispatch_status") or "")
    if dispatch_status == "ready":
        return "dispatch_ready"

    orchestration_status = str(entry.get("orchestration_status") or "")
    if orchestration_status == "prepared":
        return "orchestration_prepared"

    status = str(entry.get("status") or "")
    if status == "recorded":
        return "queued"
    if status == "completed":
        return "planned"
    if status.startswith("skipped"):
        return "skipped"
    if status == "failed":
        return "failed"
    return "unknown"


def sync_refiner_lifecycle(entry: dict[str, object]) -> str:
    lifecycle = derive_refiner_lifecycle(entry)
    entry["lifecycle"] = lifecycle
    return lifecycle


def slugify_run_dir(run_dir: str | None) -> str:
    raw = (run_dir or "unknown-run").strip().strip("/")
    raw = raw.replace("/", "-")
    raw = re.sub(r"[^A-Za-z0-9._-]+", "-", raw)
    return raw or "unknown-run"


def _sha1_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _duplicate_replay_signal_lines(output: str, *, limit: int = 8) -> list[str]:
    lines: list[str] = []
    patterns = (
        "AddressSanitizer",
        "LeakSanitizer",
        "UndefinedBehaviorSanitizer",
        "runtime error:",
        "heap-buffer-overflow",
        "stack-buffer-overflow",
        "use-after-free",
        "SEGV",
        "SUMMARY:",
    )
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if any(pattern.lower() in lowered for pattern in patterns):
            lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def run_duplicate_crash_replay_command(cmd: list[str], cwd: Path) -> tuple[int, str]:
    env = os.environ.copy()
    existing_asan = str(env.get("ASAN_OPTIONS") or "")
    asan_parts = [part for part in existing_asan.split(":") if part and not part.startswith("symbolize=")]
    asan_parts.extend(
        [
            "abort_on_error=1",
            "detect_leaks=1",
            "strict_string_checks=1",
            "check_initialization_order=1",
            "symbolize=1",
        ]
    )
    env["ASAN_OPTIONS"] = ":".join(dict.fromkeys(asan_parts))
    env.setdefault("UBSAN_OPTIONS", "print_stacktrace=1:halt_on_error=1")
    symbolizer_path = shutil.which("llvm-symbolizer")
    if symbolizer_path:
        env.setdefault("ASAN_SYMBOLIZER_PATH", symbolizer_path)
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        timeout=30,
    )
    return proc.returncode, proc.stdout


def _resolve_duplicate_replay_harness_path(repo_root: Path, entry: dict[str, object]) -> Path:
    explicit = str(entry.get("replay_harness_path") or "").strip()
    if explicit:
        return Path(explicit)
    adapter = _resolve_runtime_target_adapter(repo_root)
    return repo_root / adapter.smoke_binary_relpath


def _optional_path(value: object) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    return Path(text)


def execute_duplicate_crash_replay_probe(
    repo_root: Path,
    entry: dict[str, object],
    *,
    replay_runner: Callable[[list[str], Path], tuple[int, str]] | None = None,
) -> dict[str, object]:
    replay_dir = repo_root / "fuzz-records" / "duplicate-crash-replays"
    replay_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify_run_dir(str(entry.get("run_dir") or entry.get("key") or "duplicate-crash-review"))
    json_path = replay_dir / f"{slug}.json"
    markdown_path = replay_dir / f"{slug}.md"
    first_log_path = replay_dir / f"{slug}-first.log"
    latest_log_path = replay_dir / f"{slug}-latest.log"

    harness_path = _resolve_duplicate_replay_harness_path(repo_root, entry)
    first_artifact = _optional_path(entry.get("first_artifact_path"))
    latest_artifact = _optional_path(entry.get("latest_artifact_path"))
    runner = replay_runner or run_duplicate_crash_replay_command

    missing_paths = []
    for path in (harness_path, first_artifact, latest_artifact):
        if path is None or not path.exists():
            missing_paths.append(str(path) if path is not None else "<missing-path>")

    result: dict[str, object] = {
        "action_code": "review_duplicate_crash_replay",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "run_dir": entry.get("run_dir"),
        "report_path": entry.get("report_path"),
        "crash_fingerprint": entry.get("crash_fingerprint"),
        "replay_harness_path": str(harness_path),
        "first_artifact_path": str(first_artifact) if first_artifact is not None else None,
        "latest_artifact_path": str(latest_artifact) if latest_artifact is not None else None,
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
    }

    if missing_paths:
        result["status"] = "skipped-missing-paths"
        result["missing_paths"] = missing_paths
    else:
        first_sha1 = _sha1_file(first_artifact)
        latest_sha1 = _sha1_file(latest_artifact)
        result["first_artifact_sha1"] = first_sha1
        result["latest_artifact_sha1"] = latest_sha1
        result["replay_artifact_bytes_equal"] = first_sha1 == latest_sha1

        first_cmd = [str(harness_path), str(first_artifact)]
        latest_cmd = [str(harness_path), str(latest_artifact)]
        try:
            first_exit, first_output = runner(first_cmd, repo_root)
            latest_exit, latest_output = runner(latest_cmd, repo_root)
            first_log_path.write_text(first_output, encoding="utf-8")
            latest_log_path.write_text(latest_output, encoding="utf-8")
            first_signature = build_crash_signature(first_output.splitlines())
            latest_signature = build_crash_signature(latest_output.splitlines())
            result.update(
                {
                    "status": "completed",
                    "first_replay_exit_code": first_exit,
                    "latest_replay_exit_code": latest_exit,
                    "first_replay_command": first_cmd,
                    "latest_replay_command": latest_cmd,
                    "first_replay_log_path": str(first_log_path),
                    "latest_replay_log_path": str(latest_log_path),
                    "first_replay_signal_lines": _duplicate_replay_signal_lines(first_output),
                    "latest_replay_signal_lines": _duplicate_replay_signal_lines(latest_output),
                    "first_replay_signature": first_signature,
                    "latest_replay_signature": latest_signature,
                }
            )
        except subprocess.TimeoutExpired as exc:
            result["status"] = "failed-timeout"
            result["timeout_seconds"] = exc.timeout
        except Exception as exc:
            result["status"] = "failed-execution"
            result["error_type"] = type(exc).__name__
            result["error"] = str(exc)

    entry["replay_execution_status"] = result.get("status")
    entry["replay_execution_json_path"] = str(json_path)
    entry["replay_execution_markdown_path"] = str(markdown_path)
    entry["replay_harness_path"] = str(harness_path)
    entry["replay_execution_checked_at"] = result.get("generated_at")
    for key in (
        "first_artifact_sha1",
        "latest_artifact_sha1",
        "replay_artifact_bytes_equal",
        "first_replay_exit_code",
        "latest_replay_exit_code",
        "first_replay_command",
        "latest_replay_command",
        "first_replay_log_path",
        "latest_replay_log_path",
        "first_replay_signal_lines",
        "latest_replay_signal_lines",
        "first_replay_signature",
        "latest_replay_signature",
        "missing_paths",
        "error_type",
        "error",
        "timeout_seconds",
    ):
        if key in result:
            entry[key] = result[key]

    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_lines = [
        "# Duplicate Crash Replay Execution",
        "",
        f"- status: {result.get('status')}",
        f"- crash_fingerprint: {result.get('crash_fingerprint')}",
        f"- replay_harness_path: {result.get('replay_harness_path')}",
        f"- first_artifact_path: {result.get('first_artifact_path')}",
        f"- latest_artifact_path: {result.get('latest_artifact_path')}",
        f"- replay_artifact_bytes_equal: {result.get('replay_artifact_bytes_equal')}",
        f"- first_replay_exit_code: {result.get('first_replay_exit_code')}",
        f"- latest_replay_exit_code: {result.get('latest_replay_exit_code')}",
        f"- first_replay_signature: {result.get('first_replay_signature')}",
        f"- latest_replay_signature: {result.get('latest_replay_signature')}",
        f"- first_replay_log_path: {result.get('first_replay_log_path')}",
        f"- latest_replay_log_path: {result.get('latest_replay_log_path')}",
    ]
    if result.get("missing_paths"):
        markdown_lines.extend(["", "## Missing Paths", "", *[f"- {item}" for item in result["missing_paths"]]])
    if result.get("first_replay_signal_lines") or result.get("latest_replay_signal_lines"):
        markdown_lines.extend(["", "## Replay Signals", ""])
        markdown_lines.append(f"- first: {result.get('first_replay_signal_lines')}")
        markdown_lines.append(f"- latest: {result.get('latest_replay_signal_lines')}")
    markdown_path.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    return result


def execute_corpus_refinement_probe(
    repo_root: Path,
    entry: dict[str, object],
    *,
    replay_runner: Callable[[list[str], Path], tuple[int, str]] | None = None,
) -> dict[str, object]:
    refinement_dir = repo_root / "fuzz-records" / "corpus-refinement-executions"
    refinement_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify_run_dir(str(entry.get("run_dir") or entry.get("key") or "corpus-refinement"))
    json_path = refinement_dir / f"{slug}.json"
    markdown_path = refinement_dir / f"{slug}.md"
    replay_log_path = refinement_dir / f"{slug}-retention-replay.log"

    harness_path = _resolve_duplicate_replay_harness_path(repo_root, entry)
    first_artifact = _optional_path(entry.get("first_artifact_path"))
    latest_artifact = _optional_path(entry.get("latest_artifact_path"))
    runner = replay_runner or run_duplicate_crash_replay_command

    result: dict[str, object] = {
        "action_code": "minimize_and_reseed",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "run_dir": entry.get("run_dir"),
        "report_path": entry.get("report_path"),
        "crash_fingerprint": entry.get("crash_fingerprint"),
        "replay_harness_path": str(harness_path),
        "first_artifact_path": str(first_artifact) if first_artifact is not None else None,
        "latest_artifact_path": str(latest_artifact) if latest_artifact is not None else None,
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
    }

    missing_paths = []
    if latest_artifact is None or not latest_artifact.exists():
        missing_paths.append(str(latest_artifact) if latest_artifact is not None else "<missing-latest-artifact>")
    if missing_paths:
        result["status"] = "skipped-missing-paths"
        result["missing_paths"] = missing_paths
    else:
        triage_bucket_path = copy_seed_into_bucket(latest_artifact, repo_root / "fuzz" / "corpus" / "triage")
        regression_bucket_path = copy_seed_into_bucket(latest_artifact, repo_root / "fuzz" / "corpus" / "regression")
        known_bad_bucket_path = copy_seed_into_bucket(latest_artifact, repo_root / "fuzz" / "corpus" / "known-bad")
        result["triage_bucket_path"] = str(triage_bucket_path) if triage_bucket_path else None
        result["regression_bucket_path"] = str(regression_bucket_path) if regression_bucket_path else None
        result["known_bad_bucket_path"] = str(known_bad_bucket_path) if known_bad_bucket_path else None
        result["latest_artifact_sha1"] = _sha1_file(latest_artifact)
        if first_artifact is not None and first_artifact.exists():
            result["first_artifact_sha1"] = _sha1_file(first_artifact)
            result["first_vs_latest_bytes_equal"] = result["first_artifact_sha1"] == result["latest_artifact_sha1"]
        if triage_bucket_path and triage_bucket_path.exists():
            result["triage_bucket_sha1"] = _sha1_file(triage_bucket_path)
        if regression_bucket_path and regression_bucket_path.exists():
            result["regression_bucket_sha1"] = _sha1_file(regression_bucket_path)
        if known_bad_bucket_path and known_bad_bucket_path.exists():
            result["known_bad_bucket_sha1"] = _sha1_file(known_bad_bucket_path)

        replay_missing_paths = [
            str(path)
            for path in (harness_path, regression_bucket_path)
            if not path or not str(path) or not Path(path).exists()
        ]
        if replay_missing_paths:
            result["status"] = "completed-without-retention-replay"
            result["retention_replay_status"] = "skipped-missing-paths"
            result["retention_replay_missing_paths"] = replay_missing_paths
        else:
            replay_cmd = [str(harness_path), str(regression_bucket_path)]
            replay_exit, replay_output = runner(replay_cmd, repo_root)
            replay_log_path.write_text(replay_output, encoding="utf-8")
            retention_signature = build_crash_signature(replay_output.splitlines())
            result.update(
                {
                    "status": "completed",
                    "retention_replay_status": "completed",
                    "retention_replay_command": replay_cmd,
                    "retention_replay_exit_code": replay_exit,
                    "retention_replay_log_path": str(replay_log_path),
                    "retention_replay_signal_lines": _duplicate_replay_signal_lines(replay_output),
                    "retention_replay_signature": retention_signature,
                }
            )

    entry["corpus_refinement_execution_status"] = result.get("status")
    entry["corpus_refinement_execution_json_path"] = str(json_path)
    entry["corpus_refinement_execution_markdown_path"] = str(markdown_path)
    entry["corpus_refinement_execution_checked_at"] = result.get("generated_at")
    for key in (
        "triage_bucket_path",
        "regression_bucket_path",
        "known_bad_bucket_path",
        "latest_artifact_sha1",
        "first_artifact_sha1",
        "first_vs_latest_bytes_equal",
        "triage_bucket_sha1",
        "regression_bucket_sha1",
        "known_bad_bucket_sha1",
        "retention_replay_status",
        "retention_replay_missing_paths",
        "retention_replay_command",
        "retention_replay_exit_code",
        "retention_replay_log_path",
        "retention_replay_signal_lines",
        "retention_replay_signature",
        "missing_paths",
    ):
        if key in result:
            entry[key] = result[key]

    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_lines = [
        "# Corpus Refinement Execution",
        "",
        f"- status: {result.get('status')}",
        f"- crash_fingerprint: {result.get('crash_fingerprint')}",
        f"- latest_artifact_path: {result.get('latest_artifact_path')}",
        f"- triage_bucket_path: {result.get('triage_bucket_path')}",
        f"- regression_bucket_path: {result.get('regression_bucket_path')}",
        f"- known_bad_bucket_path: {result.get('known_bad_bucket_path')}",
        f"- retention_replay_status: {result.get('retention_replay_status')}",
        f"- retention_replay_exit_code: {result.get('retention_replay_exit_code')}",
        f"- retention_replay_signature: {result.get('retention_replay_signature')}",
        f"- retention_replay_log_path: {result.get('retention_replay_log_path')}",
    ]
    if result.get("missing_paths"):
        markdown_lines.extend(["", "## Missing Paths", "", *[f"- {item}" for item in result["missing_paths"]]])
    if result.get("retention_replay_missing_paths"):
        markdown_lines.extend(
            ["", "## Retention Replay Missing Paths", "", *[f"- {item}" for item in result["retention_replay_missing_paths"]]]
        )
    if result.get("retention_replay_signal_lines"):
        markdown_lines.extend(["", "## Retention Replay Signals", ""])
        markdown_lines.append(f"- signals: {result.get('retention_replay_signal_lines')}")
    markdown_path.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    return result


def build_duplicate_replay_followup_entry(entry: dict[str, object]) -> dict[str, object] | None:
    if str(entry.get("action_code") or "") != "review_duplicate_crash_replay":
        return None
    if str(entry.get("replay_execution_status") or "") != "completed":
        return None
    first_exit = entry.get("first_replay_exit_code")
    latest_exit = entry.get("latest_replay_exit_code")
    if first_exit in {None, 0} or latest_exit in {None, 0}:
        return None
    if bool(entry.get("replay_artifact_bytes_equal")):
        return None
    first_signature = entry.get("first_replay_signature") if isinstance(entry.get("first_replay_signature"), dict) else {}
    latest_signature = entry.get("latest_replay_signature") if isinstance(entry.get("latest_replay_signature"), dict) else {}
    first_fingerprint = str(first_signature.get("fingerprint") or "")
    latest_fingerprint = str(latest_signature.get("fingerprint") or "")
    crash_fingerprint = str(entry.get("crash_fingerprint") or "")
    first_location = str(first_signature.get("location") or entry.get("crash_location") or "")
    latest_location = str(latest_signature.get("location") or entry.get("crash_location") or "")
    if not first_fingerprint or first_fingerprint != latest_fingerprint:
        return None
    if first_location and latest_location and first_location != latest_location:
        return None
    if crash_fingerprint and first_fingerprint != crash_fingerprint:
        crash_location = str(entry.get("crash_location") or "")
        if not crash_location or first_location != crash_location:
            return None
    return {
        "key": f"minimize_and_reseed:duplicate-replay:{first_fingerprint or crash_fingerprint or entry.get('key')}",
        "action_code": "minimize_and_reseed",
        "status": "recorded",
        "run_dir": entry.get("run_dir"),
        "report_path": entry.get("report_path"),
        "outcome": entry.get("outcome") or "crash",
        "recommended_action": (
            "Use the stable duplicate replay evidence to prepare bounded minimization and reseed planning "
            "instead of rediscovering the same crash family again."
        ),
        "policy_bucket": "triage",
        "candidate_route": "reseed-before-retry",
        "derived_from_action_code": "review_duplicate_crash_replay",
        "duplicate_replay_source_key": entry.get("key"),
        "crash_fingerprint": first_fingerprint or crash_fingerprint,
        "crash_location": entry.get("crash_location"),
        "crash_summary": entry.get("crash_summary"),
        "occurrence_count": entry.get("occurrence_count"),
        "first_artifact_path": entry.get("first_artifact_path"),
        "latest_artifact_path": entry.get("latest_artifact_path"),
        "replay_execution_status": entry.get("replay_execution_status"),
        "replay_execution_json_path": entry.get("replay_execution_json_path"),
        "replay_execution_markdown_path": entry.get("replay_execution_markdown_path"),
        "replay_harness_path": entry.get("replay_harness_path"),
        "replay_artifact_bytes_equal": entry.get("replay_artifact_bytes_equal"),
        "first_replay_exit_code": first_exit,
        "latest_replay_exit_code": latest_exit,
        "first_replay_signature": first_signature,
        "latest_replay_signature": latest_signature,
    }


def record_duplicate_replay_followup(automation_dir: Path, entry: dict[str, object]) -> dict[str, object] | None:
    followup_entry = build_duplicate_replay_followup_entry(entry)
    if followup_entry is None:
        return None
    result = record_refiner_entry(
        automation_dir,
        registry_name="corpus_refinements.json",
        unique_key="key",
        entry=followup_entry,
        merge_existing=True,
    )
    return {**result, "entry": followup_entry}


def _refiner_duplicate_crash_plan_sections(entry: dict[str, object]) -> list[str]:
    first_seen_run = str(entry.get("first_seen_run") or "")
    first_seen_report_path = str(entry.get("first_seen_report_path") or entry.get("first_seen_report") or "")
    first_artifact_path = str(entry.get("first_artifact_path") or "")
    latest_artifact_path = str(entry.get("latest_artifact_path") or "")
    occurrence_count = int(entry.get("occurrence_count") or 0)
    if not any([first_seen_run, first_seen_report_path, first_artifact_path, latest_artifact_path, occurrence_count]):
        return []

    lines = [
        "## Duplicate Crash Comparison",
        "",
        f"- occurrence_count: {occurrence_count or 'unknown'}",
        f"- crash_fingerprint: {entry.get('crash_fingerprint')}",
        f"- crash_location: {entry.get('crash_location')}",
        f"- crash_summary: {entry.get('crash_summary')}",
        f"- first_seen_run: {first_seen_run or 'unknown'}",
        f"- first_seen_report_path: {first_seen_report_path or 'unknown'}",
        f"- latest_run: {entry.get('run_dir')}",
        f"- latest_report_path: {entry.get('report_path')}",
        f"- first_artifact_path: {first_artifact_path or 'unknown'}",
        f"- latest_artifact_path: {latest_artifact_path or 'unknown'}",
    ]
    if first_artifact_path and latest_artifact_path:
        lines.extend(
            [
                "",
                "## Suggested Low-Risk Commands",
                "",
                f"- sha1sum {first_artifact_path} {latest_artifact_path}",
                f"- cmp -l {first_artifact_path} {latest_artifact_path} || true",
                f"- sed -n '1,160p' {first_seen_report_path or entry.get('report_path')}",
                f"- sed -n '1,160p' {entry.get('report_path')}",
            ]
        )
    if entry.get("replay_execution_status") or entry.get("replay_execution_markdown_path"):
        lines.extend(
            [
                "",
                "## Replay Execution",
                "",
                f"- replay_execution_status: {entry.get('replay_execution_status')}",
                f"- replay_execution_markdown_path: {entry.get('replay_execution_markdown_path')}",
                f"- replay_harness_path: {entry.get('replay_harness_path')}",
                f"- replay_artifact_bytes_equal: {entry.get('replay_artifact_bytes_equal')}",
                f"- first_replay_exit_code: {entry.get('first_replay_exit_code')}",
                f"- latest_replay_exit_code: {entry.get('latest_replay_exit_code')}",
                f"- first_replay_signature: {entry.get('first_replay_signature')}",
                f"- latest_replay_signature: {entry.get('latest_replay_signature')}",
            ]
        )
    return lines


def _refiner_corpus_refinement_plan_sections(repo_root: Path, entry: dict[str, object]) -> list[str]:
    candidate_route = str(entry.get("candidate_route") or "")
    derived_from_action_code = str(entry.get("derived_from_action_code") or "")
    duplicate_replay_source_key = str(entry.get("duplicate_replay_source_key") or "")
    crash_fingerprint = str(entry.get("crash_fingerprint") or "")
    crash_location = str(entry.get("crash_location") or "")
    crash_summary = str(entry.get("crash_summary") or "")
    occurrence_count = int(entry.get("occurrence_count") or 0)
    first_artifact_path = str(entry.get("first_artifact_path") or "")
    latest_artifact_path = str(entry.get("latest_artifact_path") or "")
    replay_execution_status = str(entry.get("replay_execution_status") or "")
    replay_execution_markdown_path = str(entry.get("replay_execution_markdown_path") or "")
    replay_harness_path = str(entry.get("replay_harness_path") or "")
    if not any(
        [
            candidate_route,
            derived_from_action_code,
            duplicate_replay_source_key,
            crash_fingerprint,
            first_artifact_path,
            latest_artifact_path,
            replay_execution_markdown_path,
        ]
    ):
        return []

    triage_dir = repo_root / "fuzz" / "corpus" / "triage"
    regression_dir = repo_root / "fuzz" / "corpus" / "regression"
    known_bad_dir = repo_root / "fuzz" / "corpus" / "known-bad"
    lines = [
        "## Corpus Refinement Context",
        "",
        f"- candidate_route: {candidate_route or 'unknown'}",
        f"- derived_from_action_code: {derived_from_action_code or 'unknown'}",
        f"- duplicate_replay_source_key: {duplicate_replay_source_key or 'unknown'}",
        f"- crash_fingerprint: {crash_fingerprint or 'unknown'}",
        f"- crash_location: {crash_location or 'unknown'}",
        f"- crash_summary: {crash_summary or 'unknown'}",
        f"- occurrence_count: {occurrence_count or 'unknown'}",
        f"- first_artifact_path: {first_artifact_path or 'unknown'}",
        f"- latest_artifact_path: {latest_artifact_path or 'unknown'}",
        f"- replay_execution_status: {replay_execution_status or 'unknown'}",
        f"- replay_execution_markdown_path: {replay_execution_markdown_path or 'unknown'}",
        f"- replay_harness_path: {replay_harness_path or 'unknown'}",
    ]
    if latest_artifact_path:
        quoted_latest = shlex.quote(latest_artifact_path)
        quoted_triage = shlex.quote(str(triage_dir))
        quoted_regression = shlex.quote(str(regression_dir))
        quoted_known_bad = shlex.quote(str(known_bad_dir))
        lines.extend(
            [
                "",
                "## Suggested Low-Risk Commands",
                "",
                f"- mkdir -p {quoted_triage} {quoted_regression} {quoted_known_bad}",
                f"- cp -n {quoted_latest} {quoted_triage}/",
                f"- cp -n {quoted_latest} {quoted_regression}/",
                f"- cp -n {quoted_latest} {quoted_known_bad}/",
            ]
        )
        if first_artifact_path:
            quoted_first = shlex.quote(first_artifact_path)
            lines.append(f"- sha1sum {quoted_first} {quoted_latest}")
            lines.append(f"- cmp -l {quoted_first} {quoted_latest} || true")
        if replay_execution_markdown_path:
            lines.append(f"- sed -n '1,200p' {shlex.quote(replay_execution_markdown_path)}")
    if entry.get("corpus_refinement_execution_status") or entry.get("corpus_refinement_execution_markdown_path"):
        lines.extend(
            [
                "",
                "## Corpus Refinement Execution",
                "",
                f"- corpus_refinement_execution_status: {entry.get('corpus_refinement_execution_status')}",
                f"- corpus_refinement_execution_markdown_path: {entry.get('corpus_refinement_execution_markdown_path')}",
                f"- triage_bucket_path: {entry.get('triage_bucket_path')}",
                f"- regression_bucket_path: {entry.get('regression_bucket_path')}",
                f"- known_bad_bucket_path: {entry.get('known_bad_bucket_path')}",
                f"- retention_replay_status: {entry.get('retention_replay_status')}",
                f"- retention_replay_exit_code: {entry.get('retention_replay_exit_code')}",
                f"- retention_replay_signature: {entry.get('retention_replay_signature')}",
            ]
        )
    return lines


def _refiner_extra_plan_sections(repo_root: Path, action_code: str, entry: dict[str, object]) -> list[str]:
    if action_code == "review_duplicate_crash_replay":
        return _refiner_duplicate_crash_plan_sections(entry)
    if action_code == "minimize_and_reseed":
        return _refiner_corpus_refinement_plan_sections(repo_root, entry)
    return []


def _refiner_extra_context_lines(action_code: str, entry: dict[str, object]) -> list[str]:
    if action_code == "review_duplicate_crash_replay":
        return [
            f"- crash_fingerprint: {entry.get('crash_fingerprint')}",
            f"- crash_location: {entry.get('crash_location')}",
            f"- crash_summary: {entry.get('crash_summary')}",
            f"- occurrence_count: {entry.get('occurrence_count')}",
            f"- first_seen_run: {entry.get('first_seen_run')}",
            f"- first_seen_report_path: {entry.get('first_seen_report_path') or entry.get('first_seen_report')}",
            f"- first_artifact_path: {entry.get('first_artifact_path')}",
            f"- latest_artifact_path: {entry.get('latest_artifact_path')}",
        ]
    if action_code == "minimize_and_reseed":
        return [
            f"- candidate_route: {entry.get('candidate_route')}",
            f"- derived_from_action_code: {entry.get('derived_from_action_code')}",
            f"- duplicate_replay_source_key: {entry.get('duplicate_replay_source_key')}",
            f"- crash_fingerprint: {entry.get('crash_fingerprint')}",
            f"- crash_location: {entry.get('crash_location')}",
            f"- crash_summary: {entry.get('crash_summary')}",
            f"- occurrence_count: {entry.get('occurrence_count')}",
            f"- first_artifact_path: {entry.get('first_artifact_path')}",
            f"- latest_artifact_path: {entry.get('latest_artifact_path')}",
            f"- replay_execution_markdown_path: {entry.get('replay_execution_markdown_path')}",
        ]
    return []


def write_refiner_plan(repo_root: Path, *, action_code: str, entry: dict[str, object]) -> Path:
    plans_dir = repo_root / "fuzz-records" / "refiner-plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify_run_dir(str(entry.get("run_dir") or "unknown-run"))
    path = plans_dir / f"{action_code}-{slug}.md"
    lines = [
        f"# Refiner Plan: {action_code}",
        "",
        f"- run_dir: {entry.get('run_dir')}",
        f"- report_path: {entry.get('report_path')}",
        f"- outcome: {entry.get('outcome')}",
        f"- recommended_action: {entry.get('recommended_action')}",
    ]
    extra_sections = _refiner_extra_plan_sections(repo_root, action_code, entry)
    if extra_sections:
        lines.extend(["", *extra_sections])
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Auto-generated low-risk executor draft.",
            "- Review this plan before any destructive corpus or harness mutation.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def get_refiner_orchestration_spec(action_code: str) -> dict[str, object]:
    spec = REFINER_ORCHESTRATION_SPECS.get(action_code, {})
    verification = spec.get("verification")
    toolsets = spec.get("toolsets")
    skills = spec.get("skills")
    return {
        "dispatch_channel": str(spec.get("dispatch_channel") or "subagent"),
        "goal": str(spec.get("goal") or "Review the refiner plan and produce a low-risk next-step plan."),
        "verification": list(verification) if isinstance(verification, list) else [],
        "toolsets": list(toolsets) if isinstance(toolsets, list) else ["terminal", "file"],
        "skills": list(skills) if isinstance(skills, list) else [],
        "cron_schedule": str(spec.get("cron_schedule") or "30m"),
        "cron_deliver": str(spec.get("cron_deliver") or "local"),
        "cron_repeat": int(spec.get("cron_repeat") or 1),
        "bridge_timeout_seconds": int(spec.get("bridge_timeout_seconds") or BRIDGE_SCRIPT_TIMEOUT_SECONDS),
    }


def build_refiner_subagent_prompt(action_code: str, entry: dict[str, object], plan_path: Path) -> str:
    spec = get_refiner_orchestration_spec(action_code)
    verification = [f"- {item}" for item in spec["verification"]]
    verification_block = "\n".join(verification) if verification else "- Keep the output low-risk and reviewable."
    context_lines = [
        "Context:",
        f"- run_dir: {entry.get('run_dir')}",
        f"- report_path: {entry.get('report_path')}",
        f"- executor_plan_path: {plan_path}",
        f"- current_mode: {entry.get('current_mode')}",
        f"- next_mode: {entry.get('next_mode')}",
        f"- recommended_action: {entry.get('recommended_action')}",
        f"- selected_candidate_id: {entry.get('selected_candidate_id')}",
        f"- selected_entrypoint_path: {entry.get('selected_entrypoint_path')}",
        f"- selected_recommended_mode: {entry.get('selected_recommended_mode')}",
        f"- selected_target_stage: {entry.get('selected_target_stage')}",
    ]
    context_lines.extend(_refiner_extra_context_lines(action_code, entry))
    return "\n".join(
        [
            f"Refiner action: {action_code}",
            f"Goal: {spec['goal']}",
            "",
            *context_lines,
            "",
            "Requirements:",
            "- Stay low-risk. Do not delete seeds, rewrite code, or force a mode switch automatically.",
            "- Turn the existing plan into a concise operator-ready follow-up note.",
            "- Include concrete verification steps and rollback notes where relevant.",
            "",
            "Verification checklist:",
            verification_block,
        ]
    ) + "\n"


def build_refiner_cron_prompt(action_code: str, entry: dict[str, object], plan_path: Path) -> str:
    spec = get_refiner_orchestration_spec(action_code)
    verification = [f"- {item}" for item in spec["verification"]]
    verification_block = "\n".join(verification) if verification else "- Keep the output low-risk and reviewable."
    context_lines = [
        "Known context:",
        f"- run_dir: {entry.get('run_dir')}",
        f"- report_path: {entry.get('report_path')}",
        f"- executor_plan_path: {plan_path}",
        f"- recommended_action: {entry.get('recommended_action')}",
        f"- current_mode: {entry.get('current_mode')}",
        f"- next_mode: {entry.get('next_mode')}",
        f"- selected_candidate_id: {entry.get('selected_candidate_id')}",
        f"- selected_entrypoint_path: {entry.get('selected_entrypoint_path')}",
        f"- selected_recommended_mode: {entry.get('selected_recommended_mode')}",
        f"- selected_target_stage: {entry.get('selected_target_stage')}",
    ]
    context_lines.extend(_refiner_extra_context_lines(action_code, entry))
    return "\n".join(
        [
            "This is a self-contained refiner follow-up prompt for a fresh Hermes session.",
            f"Action code: {action_code}",
            f"Primary goal: {spec['goal']}",
            "",
            *context_lines,
            "",
            "Constraints:",
            "- Keep this low-risk and reversible.",
            "- No destructive corpus mutation, no code edits, and no irreversible file moves.",
            "- Produce a short execution note or command plan that a human can review.",
            "",
            "Verification checklist:",
            verification_block,
        ]
    ) + "\n"


def write_refiner_orchestration_bundle(
    repo_root: Path,
    *,
    action_code: str,
    entry: dict[str, object],
    plan_path: Path,
) -> dict[str, object]:
    bundle_dir = repo_root / "fuzz-records" / "refiner-orchestration"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify_run_dir(str(entry.get("run_dir") or "unknown-run"))
    manifest_path = bundle_dir / f"{action_code}-{slug}.json"
    subagent_prompt_path = bundle_dir / f"{action_code}-{slug}-subagent.txt"
    cron_prompt_path = bundle_dir / f"{action_code}-{slug}-cron.txt"
    spec = get_refiner_orchestration_spec(action_code)

    subagent_prompt = build_refiner_subagent_prompt(action_code, entry, plan_path)
    cron_prompt = build_refiner_cron_prompt(action_code, entry, plan_path)
    subagent_prompt_path.write_text(subagent_prompt, encoding="utf-8")
    cron_prompt_path.write_text(cron_prompt, encoding="utf-8")

    manifest = {
        "schema_version": 1,
        "prepared_at": dt.datetime.now().isoformat(timespec="seconds"),
        "action_code": action_code,
        "dispatch_channel": spec["dispatch_channel"],
        "run_dir": entry.get("run_dir"),
        "report_path": entry.get("report_path"),
        "executor_plan_path": str(plan_path),
        "subagent_prompt_path": str(subagent_prompt_path),
        "cron_prompt_path": str(cron_prompt_path),
        "recommended_action": entry.get("recommended_action"),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "manifest_path": str(manifest_path),
        "subagent_prompt_path": str(subagent_prompt_path),
        "cron_prompt_path": str(cron_prompt_path),
        "dispatch_channel": str(spec["dispatch_channel"]),
    }


AUTONOMOUS_SUPERVISOR_DEFAULT_CHANNEL_ID = "1493631285027934419"


def build_autonomous_supervisor_prompt(repo_root: Path, *, channel_id: str | None = None) -> str:
    progress_channel = str(channel_id or AUTONOMOUS_SUPERVISOR_DEFAULT_CHANNEL_ID)
    return "\n".join(
        [
            f"Project root: {repo_root}",
            "",
            "Mission:",
            "- Keep building the fuzzing-jpeg2000 self-improving agentic fuzzing system toward the user's true goal.",
            "- Prioritize frequent LLM intervention, artifact-first evidence, and real loop quality over control-plane ornament.",
            "- Do not ask the user for routine confirmation. Choose the highest-leverage safe next step yourself.",
            "",
            "True north:",
            "- Discord command -> fuzzing/probe execution -> artifact preservation -> trigger -> LLM-guided harness/seed/strategy revision -> rerun -> repeat.",
            "- Remote/proxmox closure matters, but do not skip local evidence/triage quality on the way.",
            "",
            "Work loop for this session:",
            "1. Inspect fresh fuzz-artifacts and fuzz-records state.",
            "2. Pick one highest-leverage safe slice that improves the real autonomous fuzz loop.",
            "3. If code changes are needed, use TDD and systematic debugging.",
            "4. Run targeted tests and full pytest when warranted.",
            "5. Update fuzz-records/current-status.md, fuzz-records/progress-index.md, and write note/checklist docs.",
            f"6. If MCP Discord logging is available, post a concise progress update to channel {progress_channel} using mcp_discord_admin_log_server_event.",
            "7. Finish with a cold Korean summary including what changed, why it mattered, verification, what remains, and the next best move.",
            "",
            "Hard constraints:",
            "- No exploit code.",
            "- No destructive actions outside the project root.",
            "- No pretending full autonomy is solved when it is not.",
            "- Prefer triage/evidence/revision closure/remote bridge work over internal ornament.",
        ]
    ) + "\n"


def write_autonomous_supervisor_bundle(
    repo_root: Path,
    *,
    sleep_seconds: int = 600,
    channel_id: str | None = None,
) -> dict[str, object]:
    bundle_dir = repo_root / "fuzz-records" / "autonomous-supervisor"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = bundle_dir / "autonomous-dev-loop-prompt.txt"
    script_path = bundle_dir / "autonomous-dev-loop.sh"
    log_path = bundle_dir / "autonomous-dev-loop.log"
    status_path = bundle_dir / "autonomous-dev-loop-status.json"
    stop_path = bundle_dir / "STOP"
    normalized_sleep = max(10, int(sleep_seconds))
    prompt = build_autonomous_supervisor_prompt(repo_root, channel_id=channel_id)
    prompt_path.write_text(prompt, encoding="utf-8")
    if stop_path.exists():
        stop_path.unlink()
    script_lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        f"PROMPT_PATH={shlex.quote(str(prompt_path))}",
        f"LOG_PATH={shlex.quote(str(log_path))}",
        f"STATUS_PATH={shlex.quote(str(status_path))}",
        f"STOP_PATH={shlex.quote(str(stop_path))}",
        f"SLEEP_SECONDS={normalized_sleep}",
        'mkdir -p "$(dirname \"$LOG_PATH\")"',
        "ITERATION=0",
        'printf "{\\"status\\": \\"prepared\\", \\"iteration_count\\": 0}\\n" > "$STATUS_PATH"',
        'while [ ! -f "$STOP_PATH" ]; do',
        "  ITERATION=$((ITERATION + 1))",
        "  STARTED_AT=$(date --iso-8601=seconds)",
        "  python3 - \"$STATUS_PATH\" \"$ITERATION\" \"$STARTED_AT\" <<'PY'",
        "import json, pathlib, sys",
        "path = pathlib.Path(sys.argv[1])",
        "payload = {\"status\": \"running\", \"iteration_count\": int(sys.argv[2]), \"last_started_at\": sys.argv[3]}",
        "path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\\n', encoding='utf-8')",
        "PY",
        '  PROMPT=$(cat "$PROMPT_PATH")',
        '  ITERATION_OUTPUT=$(mktemp)',
        '  printf "[autonomous-supervisor] iteration=%s status=running started_at=%s\\n" "$ITERATION" "$STARTED_AT" | tee -a "$LOG_PATH"',
        "  set +e",
        '  hermes chat -q "$PROMPT" -Q > "$ITERATION_OUTPUT" 2>&1',
        "  EXIT_CODE=$?",
        "  set -e",
        '  cat "$ITERATION_OUTPUT" >> "$LOG_PATH"',
        '  rm -f "$ITERATION_OUTPUT"',
        "  FINISHED_AT=$(date --iso-8601=seconds)",
        '  printf "[autonomous-supervisor] iteration=%s status=finished exit_code=%s finished_at=%s\\n" "$ITERATION" "$EXIT_CODE" "$FINISHED_AT" | tee -a "$LOG_PATH"',
        "  python3 - \"$STATUS_PATH\" \"$ITERATION\" \"$STARTED_AT\" \"$FINISHED_AT\" \"$EXIT_CODE\" <<'PY'",
        "import json, pathlib, sys",
        "path = pathlib.Path(sys.argv[1])",
        "payload = {",
        "    \"status\": \"sleeping\",",
        "    \"iteration_count\": int(sys.argv[2]),",
        "    \"last_started_at\": sys.argv[3],",
        "    \"last_finished_at\": sys.argv[4],",
        "    \"last_exit_code\": int(sys.argv[5]),",
        "}",
        "path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\\n', encoding='utf-8')",
        "PY",
        '  sleep "$SLEEP_SECONDS"',
        'done',
        "python3 - \"$STATUS_PATH\" <<'PY'",
        "import json, pathlib, sys",
        "path = pathlib.Path(sys.argv[1])",
        "payload = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}",
        "payload['status'] = 'stopped'",
        "path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\\n', encoding='utf-8')",
        "PY",
    ]
    script_path.write_text("\n".join(script_lines) + "\n", encoding="utf-8")
    script_path.chmod(0o755)
    return {
        "prompt_path": str(prompt_path),
        "script_path": str(script_path),
        "log_path": str(log_path),
        "status_path": str(status_path),
        "stop_path": str(stop_path),
        "sleep_seconds": normalized_sleep,
        "channel_id": str(channel_id or AUTONOMOUS_SUPERVISOR_DEFAULT_CHANNEL_ID),
    }


def lookup_ranked_candidate_metrics(repo_root: Path, candidate_id: str | None) -> dict[str, object]:
    if not candidate_id:
        return {"candidate_found": False}
    registry_path = repo_root / "fuzz-records" / "harness-candidates" / "ranked-candidates.json"
    registry = load_registry(registry_path, {"candidates": []})
    candidates = registry.get("candidates") if isinstance(registry.get("candidates"), list) else []
    for candidate in candidates:
        if isinstance(candidate, dict) and str(candidate.get("candidate_id") or "") == str(candidate_id):
            return {
                "candidate_found": True,
                "candidate_score": int(candidate.get("score") or 0),
                "candidate_effective_score": int(candidate.get("effective_score") or 0),
                "candidate_status": candidate.get("status"),
                "candidate_debt_penalty": int(candidate.get("debt_penalty") or 0),
                "candidate_execution_evidence_score": int(candidate.get("execution_evidence_score") or 0),
                "candidate_viability_score": int(candidate.get("viability_score") or 0),
                "candidate_build_viability": candidate.get("build_viability"),
                "candidate_smoke_viability": candidate.get("smoke_viability"),
                "candidate_callable_signal": candidate.get("callable_signal"),
            }
    return {"candidate_found": False}


def summarize_refiner_history(automation_dir: Path) -> dict[str, object]:
    history_path = automation_dir / "run_history.json"
    history_data = load_registry(history_path, {"entries": []})
    history = history_data.get("entries") if isinstance(history_data.get("entries"), list) else []
    normalized = [entry for entry in history if isinstance(entry, dict)]
    recent = normalized[-20:]
    semantic = compute_semantic_history_summary(recent)
    timeout_count = sum(1 for entry in recent if entry.get("timeout_detected") or entry.get("outcome") == "timeout")
    return {
        "recent_count": len(recent),
        "timeout_rate": (timeout_count / len(recent)) if recent else 0.0,
        "semantic_summary": semantic,
    }


def compute_refiner_queue_weight(entry: dict[str, object], *, automation_dir: Path, repo_root: Path) -> dict[str, object]:
    action_code = str(entry.get("action_code") or "unknown")
    base_weights = {
        "halt_and_review_harness": 30,
        "shift_weight_to_deeper_harness": 24,
        "split_slow_lane": 20,
        "minimize_and_reseed": 18,
    }
    history = summarize_refiner_history(automation_dir)
    semantic = history.get("semantic_summary") if isinstance(history.get("semantic_summary"), dict) else {}
    shallow_ratio = float(semantic.get("shallow_ratio") or 0.0)
    recent_count = int(history.get("recent_count") or 0)
    timeout_rate = float(history.get("timeout_rate") or 0.0)
    candidate_metrics = lookup_ranked_candidate_metrics(repo_root, str(entry.get("selected_candidate_id") or ""))
    candidate_effective_score = int(candidate_metrics.get("candidate_effective_score") or 0)
    candidate_viability_score = int(candidate_metrics.get("candidate_viability_score") or 0)
    candidate_execution_evidence_score = int(candidate_metrics.get("candidate_execution_evidence_score") or 0)
    candidate_status = str(candidate_metrics.get("candidate_status") or entry.get("selected_candidate_status") or "")
    queue_weight = base_weights.get(action_code, 10) + candidate_effective_score
    reasons = [f"base:{base_weights.get(action_code, 10)}", f"candidate-effective:{candidate_effective_score}"]

    if candidate_execution_evidence_score:
        queue_weight += candidate_execution_evidence_score
        reasons.append(f"candidate-evidence:{candidate_execution_evidence_score}")
    if candidate_viability_score:
        queue_weight += candidate_viability_score
        reasons.append(f"candidate-viability:{candidate_viability_score}")
    if str(candidate_metrics.get("candidate_build_viability") or "") == "high":
        queue_weight += 4
        reasons.append("candidate-build-viability:high:+4")
    if str(candidate_metrics.get("candidate_smoke_viability") or "") == "high":
        queue_weight += 4
        reasons.append("candidate-smoke-viability:high:+4")
    if str(candidate_metrics.get("candidate_callable_signal") or "") == "likely-callable":
        queue_weight += 3
        reasons.append("candidate-callable-signal:+3")

    status_bonus = {
        "review_required": 12,
        "seed_debt": 6,
        "build_debt": 8,
        "smoke_debt": 7,
    }.get(candidate_status, 0)
    if status_bonus:
        queue_weight += status_bonus
        reasons.append(f"candidate-status:{candidate_status}:{status_bonus}")

    if action_code == "shift_weight_to_deeper_harness" and recent_count >= 3 and shallow_ratio >= 0.60:
        queue_weight += 14
        reasons.append("history:shallow-crash-dominance:+14")
    if action_code == "halt_and_review_harness" and recent_count >= 3 and shallow_ratio >= 0.60:
        queue_weight += 10
        reasons.append("history:repeated-review-signal:+10")
    if action_code == "split_slow_lane" and recent_count >= 3 and timeout_rate >= 0.40:
        queue_weight += 16
        reasons.append("history:timeout-surge:+16")
    if action_code == "minimize_and_reseed":
        corpus_pressure = int(entry.get("verification_retry_count") or 0)
        if corpus_pressure:
            queue_weight += corpus_pressure * 2
            reasons.append(f"history:retry-pressure:+{corpus_pressure * 2}")

    return {
        "queue_weight": queue_weight,
        "queue_reasons": reasons,
        "candidate_effective_score": candidate_effective_score,
        "candidate_status": candidate_status or None,
        "timeout_rate": timeout_rate,
        "shallow_ratio": shallow_ratio,
    }


def select_refiner_registry_entry(
    automation_dir: Path,
    *,
    repo_root: Path,
    matcher: Callable[[dict[str, object]], bool],
) -> tuple[Path, dict[str, object], dict[str, object]] | None:
    loaded: list[tuple[Path, dict[str, object], list[dict[str, object]]]] = []
    candidates: list[tuple[int, str, Path, dict[str, object], dict[str, object]]] = []
    for registry_name, expected_action in REFINER_QUEUE_REGISTRY_SPECS:
        path = automation_dir / registry_name
        data = load_registry(path, {"entries": []})
        entries = data.setdefault("entries", [])
        normalized = [item for item in entries if isinstance(item, dict)]
        loaded.append((path, data, normalized))
        for entry in normalized:
            entry.setdefault("action_code", expected_action)
            if not matcher(entry):
                continue
            weighting = compute_refiner_queue_weight(entry, automation_dir=automation_dir, repo_root=repo_root)
            entry["queue_weight"] = weighting["queue_weight"]
            entry["queue_reasons"] = list(weighting["queue_reasons"])
            entry["selected_effective_score"] = weighting["candidate_effective_score"]
            if weighting.get("candidate_status") is not None:
                entry["selected_candidate_status"] = weighting.get("candidate_status")
            candidates.append((
                int(weighting["queue_weight"]),
                str(entry.get("key") or ""),
                path,
                data,
                entry,
            ))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    for rank, (_, _, _, _, entry) in enumerate(candidates, start=1):
        entry["queue_rank"] = rank
    for path, data, _ in loaded:
        save_registry(path, data)
    if not candidates:
        return None
    _, _, path, data, entry = candidates[0]
    return path, data, entry


def prepare_next_refiner_orchestration(automation_dir: Path, *, repo_root: Path) -> dict[str, object] | None:
    execution = execute_next_refiner_action(automation_dir, repo_root=repo_root)
    if execution is None:
        return None

    registry_path = Path(str(execution["registry"]))
    data = load_registry(registry_path, {"entries": []})
    entries = data.setdefault("entries", [])
    entry = next((item for item in entries if item.get("key") == execution.get("entry_key")), None)
    if entry is None:
        return execution

    action_code = str(entry.get("action_code") or execution.get("action_code") or "unknown")
    plan_path = Path(str(entry.get("executor_plan_path") or execution.get("plan_path")))
    bundle = write_refiner_orchestration_bundle(repo_root, action_code=action_code, entry=entry, plan_path=plan_path)
    entry["orchestration_status"] = "prepared"
    sync_refiner_lifecycle(entry)
    entry["dispatch_channel"] = bundle["dispatch_channel"]
    entry["orchestration_manifest_path"] = bundle["manifest_path"]
    entry["subagent_prompt_path"] = bundle["subagent_prompt_path"]
    entry["cron_prompt_path"] = bundle["cron_prompt_path"]
    entry["orchestration_prepared_at"] = dt.datetime.now().isoformat(timespec="seconds")
    save_registry(registry_path, data)
    return {
        **execution,
        **bundle,
        "orchestration_status": entry.get("orchestration_status"),
    }


def find_prepared_refiner_entry(automation_dir: Path, *, repo_root: Path) -> tuple[Path, dict[str, object], dict[str, object]] | None:
    return select_refiner_registry_entry(
        automation_dir,
        repo_root=repo_root,
        matcher=lambda item: item.get("orchestration_status") == "prepared"
        and item.get("dispatch_status") not in {"ready", "dispatched", "completed", "skipped"},
    )


def build_delegate_task_request(action_code: str, entry: dict[str, object], repo_root: Path) -> dict[str, object]:
    spec = get_refiner_orchestration_spec(action_code)
    prompt_path = entry.get("subagent_prompt_path")
    context_lines = [
        f"repo_root: {repo_root}",
        f"run_dir: {entry.get('run_dir')}",
        f"report_path: {entry.get('report_path')}",
        f"executor_plan_path: {entry.get('executor_plan_path')}",
        f"subagent_prompt_path: {prompt_path}",
        f"selected_candidate_id: {entry.get('selected_candidate_id')}",
        f"selected_entrypoint_path: {entry.get('selected_entrypoint_path')}",
        f"selected_recommended_mode: {entry.get('selected_recommended_mode')}",
        f"selected_target_stage: {entry.get('selected_target_stage')}",
    ]
    if isinstance(prompt_path, str) and Path(prompt_path).exists():
        context_lines.extend(["", "Prompt:\n" + Path(prompt_path).read_text(encoding="utf-8")])
    return {
        "goal": str(spec["goal"]),
        "context": "\n".join(context_lines).strip() + "\n",
        "toolsets": list(spec["toolsets"]),
        "skills": list(spec["skills"]),
    }


def build_cronjob_request(action_code: str, entry: dict[str, object]) -> dict[str, object]:
    spec = get_refiner_orchestration_spec(action_code)
    prompt_path = entry.get("cron_prompt_path")
    prompt_text = ""
    if isinstance(prompt_path, str) and Path(prompt_path).exists():
        prompt_text = Path(prompt_path).read_text(encoding="utf-8")
    prompt = prompt_text or str(entry.get("recommended_action") or spec["goal"])
    prompt += "\n\n" + "\n".join(
        [
            f"selected_candidate_id: {entry.get('selected_candidate_id')}",
            f"selected_entrypoint_path: {entry.get('selected_entrypoint_path')}",
            f"selected_recommended_mode: {entry.get('selected_recommended_mode')}",
            f"selected_target_stage: {entry.get('selected_target_stage')}",
        ]
    )
    slug = slugify_run_dir(str(entry.get("run_dir") or "unknown-run"))
    return {
        "action": "create",
        "name": f"refiner-{action_code}-{slug}",
        "schedule": str(spec["cron_schedule"]),
        "repeat": int(spec["cron_repeat"]),
        "deliver": str(spec["cron_deliver"]),
        "prompt": prompt,
        "metadata": {
            "selected_candidate_id": entry.get("selected_candidate_id"),
            "selected_entrypoint_path": entry.get("selected_entrypoint_path"),
            "selected_recommended_mode": entry.get("selected_recommended_mode"),
            "selected_target_stage": entry.get("selected_target_stage"),
        },
    }


def write_refiner_dispatch_bundle(repo_root: Path, *, action_code: str, entry: dict[str, object]) -> dict[str, object]:
    dispatch_dir = repo_root / "fuzz-records" / "refiner-dispatch"
    dispatch_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify_run_dir(str(entry.get("run_dir") or "unknown-run"))
    spec = get_refiner_orchestration_spec(action_code)
    if spec["dispatch_channel"] == "cron":
        request = build_cronjob_request(action_code, entry)
        request_path = dispatch_dir / f"{action_code}-{slug}-cronjob-request.json"
        request_path.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {
            "dispatch_channel": "cron",
            "dispatch_status": "ready",
            "cronjob_request_path": str(request_path),
        }

    request = build_delegate_task_request(action_code, entry, repo_root)
    request_path = dispatch_dir / f"{action_code}-{slug}-delegate-request.json"
    request_path.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "dispatch_channel": "subagent",
        "dispatch_status": "ready",
        "delegate_task_request_path": str(request_path),
    }


def dispatch_next_refiner_orchestration(automation_dir: Path, *, repo_root: Path) -> dict[str, object] | None:
    found = find_prepared_refiner_entry(automation_dir, repo_root=repo_root)
    if found is None:
        return None
    registry_path, data, entry = found
    action_code = str(entry.get("action_code") or "unknown")
    bundle = write_refiner_dispatch_bundle(repo_root, action_code=action_code, entry=entry)
    entry["dispatch_status"] = bundle["dispatch_status"]
    sync_refiner_lifecycle(entry)
    entry["dispatch_channel"] = bundle["dispatch_channel"]
    entry["dispatch_prepared_at"] = dt.datetime.now().isoformat(timespec="seconds")
    if bundle.get("delegate_task_request_path"):
        entry["delegate_task_request_path"] = bundle["delegate_task_request_path"]
    if bundle.get("cronjob_request_path"):
        entry["cronjob_request_path"] = bundle["cronjob_request_path"]
    save_registry(registry_path, data)
    return {
        "registry": str(registry_path),
        "entry_key": entry.get("key"),
        "action_code": action_code,
        **bundle,
    }


def find_ready_refiner_entry(automation_dir: Path, *, repo_root: Path) -> tuple[Path, dict[str, object], dict[str, object]] | None:
    return select_refiner_registry_entry(
        automation_dir,
        repo_root=repo_root,
        matcher=lambda item: item.get("dispatch_status") == "ready"
        and item.get("bridge_status") not in {"armed", "launched", "completed", "skipped"},
    )


def build_delegate_bridge_prompt(*, action_code: str, request_path: Path) -> str:
    return "\n".join(
        [
            "Read the delegate_task request JSON from the path below and execute it immediately.",
            f"request_path: {request_path}",
            f"action_code: {action_code}",
            "Requirements:",
            "- Use the file tool to read the JSON.",
            "- If the request includes llm_evidence_json_path or llm_evidence_markdown_path in context, read that evidence before dispatching.",
            "- Prioritize failure_reasons and llm_objective over older generic bridge assumptions when forming the delegated task.",
            "- Call delegate_task with the exact goal/context/toolsets/skills from that file.",
            "- Return a compact status including success/failure and any dispatch identifier you can observe.",
            "- Do not mutate corpus or source files unless the delegated task explicitly requires safe inspection only.",
        ]
    ) + "\n"


def write_delegate_bridge_bundle(repo_root: Path, *, action_code: str, entry: dict[str, object]) -> dict[str, object]:
    bridge_dir = repo_root / "fuzz-records" / "refiner-bridge"
    bridge_dir.mkdir(parents=True, exist_ok=True)
    request_path = Path(str(entry.get("delegate_task_request_path") or ""))
    slug = slugify_run_dir(str(entry.get("run_dir") or "unknown-run"))
    prompt_path = bridge_dir / f"{action_code}-{slug}-delegate-bridge-prompt.txt"
    script_path = bridge_dir / f"{action_code}-{slug}-delegate-bridge.sh"
    prompt_text = build_delegate_bridge_prompt(action_code=action_code, request_path=request_path)
    prompt_path.write_text(prompt_text, encoding="utf-8")
    script_lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        f"PROMPT_PATH={shlex.quote(str(prompt_path))}",
        f"OUTPUT_PATH={shlex.quote(str(script_path.with_suffix('.log')))}",
        "PROMPT=$(cat \"$PROMPT_PATH\")",
        "hermes chat -q \"$PROMPT\" -Q -t delegation,file,terminal,skills -s subagent-driven-development | tee \"$OUTPUT_PATH\"",
    ]
    script_path.write_text("\n".join(script_lines) + "\n", encoding="utf-8")
    script_path.chmod(0o755)
    return {
        "bridge_channel": "hermes-cli-delegate",
        "bridge_status": "armed",
        "bridge_script_path": str(script_path),
        "bridge_prompt_path": str(prompt_path),
    }


def write_cron_bridge_bundle(repo_root: Path, *, action_code: str, entry: dict[str, object]) -> dict[str, object]:
    bridge_dir = repo_root / "fuzz-records" / "refiner-bridge"
    bridge_dir.mkdir(parents=True, exist_ok=True)
    request_path = Path(str(entry.get("cronjob_request_path") or ""))
    request = json.loads(request_path.read_text(encoding="utf-8"))
    slug = slugify_run_dir(str(entry.get("run_dir") or "unknown-run"))
    prompt_path = bridge_dir / f"{action_code}-{slug}-cron-bridge-prompt.txt"
    script_path = bridge_dir / f"{action_code}-{slug}-cron-bridge.sh"
    prompt_path.write_text(str(request.get("prompt") or ""), encoding="utf-8")
    script_lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        f"PROMPT_PATH={shlex.quote(str(prompt_path))}",
        f"SCHEDULE={shlex.quote(str(request.get('schedule') or '30m'))}",
        f"NAME={shlex.quote(str(request.get('name') or f'refiner-{action_code}-{slug}'))}",
        f"DELIVER={shlex.quote(str(request.get('deliver') or 'local'))}",
        f"REPEAT={shlex.quote(str(request.get('repeat') or 1))}",
        "PROMPT=$(cat \"$PROMPT_PATH\")",
        "hermes cron create --name \"$NAME\" --deliver \"$DELIVER\" --repeat \"$REPEAT\" \"$SCHEDULE\" \"$PROMPT\"",
    ]
    script_path.write_text("\n".join(script_lines) + "\n", encoding="utf-8")
    script_path.chmod(0o755)
    return {
        "bridge_channel": "hermes-cli-cron",
        "bridge_status": "armed",
        "bridge_script_path": str(script_path),
        "bridge_prompt_path": str(prompt_path),
    }


def bridge_next_refiner_dispatch(automation_dir: Path, *, repo_root: Path) -> dict[str, object] | None:
    found = find_ready_refiner_entry(automation_dir, repo_root=repo_root)
    if found is None:
        return None
    registry_path, data, entry = found
    action_code = str(entry.get("action_code") or "unknown")
    if entry.get("dispatch_channel") == "cron":
        bundle = write_cron_bridge_bundle(repo_root, action_code=action_code, entry=entry)
    else:
        bundle = write_delegate_bridge_bundle(repo_root, action_code=action_code, entry=entry)
    entry["bridge_status"] = bundle["bridge_status"]
    sync_refiner_lifecycle(entry)
    entry["bridge_channel"] = bundle["bridge_channel"]
    entry["bridge_script_path"] = bundle["bridge_script_path"]
    entry["bridge_prompt_path"] = bundle["bridge_prompt_path"]
    entry["bridge_prepared_at"] = dt.datetime.now().isoformat(timespec="seconds")
    save_registry(registry_path, data)
    return {
        "registry": str(registry_path),
        "entry_key": entry.get("key"),
        "action_code": action_code,
        **bundle,
    }


def find_armed_refiner_entry(automation_dir: Path, *, repo_root: Path) -> tuple[Path, dict[str, object], dict[str, object]] | None:
    return select_refiner_registry_entry(
        automation_dir,
        repo_root=repo_root,
        matcher=lambda item: item.get("bridge_status") == "armed"
        and item.get("launch_status") not in {"succeeded", "failed", "completed", "skipped"},
    )


def launch_bridge_script(script_path: Path, *, timeout_seconds: int = BRIDGE_SCRIPT_TIMEOUT_SECONDS) -> dict[str, object]:
    try:
        completed = subprocess.run(
            ["bash", str(script_path)],
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "exit_code": 124,
            "output": f"bridge script timed out after {int(exc.timeout or timeout_seconds)} seconds: {script_path}\n",
        }
    output = (completed.stdout or "") + (completed.stderr or "")
    return {
        "exit_code": completed.returncode,
        "output": output,
    }


def parse_cron_bridge_output(output: str) -> dict[str, object]:
    job_match = re.search(r"(?:job(?:\s+id)?|Created cron job)[:\s]+(?P<job_id>[A-Za-z0-9._:-]+)", output, re.IGNORECASE)
    job_id = job_match.group("job_id") if job_match else None
    summary = None
    if job_id:
        summary = "cron-job-created"
    return {
        "cron_job_id": job_id,
        "bridge_result_summary": summary,
    }


def parse_delegate_bridge_output(output: str) -> dict[str, object]:
    session_match = re.search(r"Child session:\s*(?P<session_id>\S+)", output, re.IGNORECASE)
    status_match = re.search(r"Delegate status:\s*(?P<status>[A-Za-z0-9._-]+)", output, re.IGNORECASE)
    artifact_match = re.search(r"Artifact path:\s*(?P<artifact_path>\S+)", output, re.IGNORECASE)
    summary_match = re.search(r"Summary:\s*(?P<summary>.+)", output, re.IGNORECASE)
    delegate_status = status_match.group("status") if status_match else None
    delegate_summary = summary_match.group("summary").strip() if summary_match else None
    return {
        "delegate_session_id": session_match.group("session_id") if session_match else None,
        "delegate_status": delegate_status,
        "delegate_artifact_path": artifact_match.group("artifact_path") if artifact_match else None,
        "delegate_summary": delegate_summary,
        "bridge_result_summary": delegate_summary or (f"delegate-{delegate_status}" if delegate_status else None),
    }


def extract_bridge_result_metadata(*, bridge_channel: str | None, output: str) -> dict[str, object]:
    if bridge_channel == "hermes-cli-cron":
        return parse_cron_bridge_output(output)
    if bridge_channel == "hermes-cli-delegate":
        return parse_delegate_bridge_output(output)
    return {}


def run_probe_command(command: list[str], *, cwd: Path | None = None) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            timeout=PROBE_COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        timeout_seconds = int(exc.timeout or PROBE_COMMAND_TIMEOUT_SECONDS)
        return 124, f"probe command timed out after {timeout_seconds} seconds: {shlex.join(command)}\n"
    output = (completed.stdout or "") + (completed.stderr or "")
    return completed.returncode, output


def env_int_default(name: str, fallback: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return fallback
    try:
        return int(str(raw).strip())
    except ValueError:
        return fallback


def cron_job_visible(job_id: str, output: str) -> bool:
    if not job_id:
        return False
    return job_id in output


def cron_metadata_visible(entry: dict[str, object], output: str) -> bool:
    expected_name = str(entry.get("cron_name") or "").strip()
    expected_schedule = str(entry.get("cron_schedule") or "").strip()
    expected_deliver = str(entry.get("cron_deliver") or "").strip()
    checks = []
    if expected_name:
        checks.append(expected_name in output)
    if expected_schedule:
        checks.append(expected_schedule in output)
    if expected_deliver:
        checks.append(expected_deliver in output)
    return bool(checks) and all(checks)


def cron_prompt_lineage_visible(entry: dict[str, object]) -> bool:
    prompt_path = entry.get("cron_prompt_path")
    tokens = entry.get("cron_prompt_lineage_tokens")
    if not prompt_path or not isinstance(tokens, list) or not tokens:
        return False
    path = Path(str(prompt_path))
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8")
    return all(str(token) in content for token in tokens)



def _parse_delegate_evidence_response(entry: dict[str, object]) -> dict[str, object]:
    artifact_path = entry.get("delegate_artifact_path")
    if not artifact_path:
        return {
            "delegate_artifact_evidence_response_verified": False,
            "delegate_reported_llm_objective": None,
            "delegate_reported_failure_reason_codes": [],
            "delegate_reported_response_summary": None,
        }
    path = Path(str(artifact_path))
    if not path.exists():
        return {
            "delegate_artifact_evidence_response_verified": False,
            "delegate_reported_llm_objective": None,
            "delegate_reported_failure_reason_codes": [],
            "delegate_reported_response_summary": None,
        }
    content = path.read_text(encoding="utf-8")
    marker = "## Evidence Response"
    start = content.find(marker)
    if start == -1:
        return {
            "delegate_artifact_evidence_response_verified": False,
            "delegate_reported_llm_objective": None,
            "delegate_reported_failure_reason_codes": [],
            "delegate_reported_response_summary": None,
        }
    body = content[start + len(marker):]
    next_heading = re.search(r"\n##?\s+", body)
    if next_heading:
        body = body[: next_heading.start()]
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    reported_objective = None
    reported_reason_codes: list[str] = []
    reported_response_summary = None
    for line in lines:
        lowered = line.lower()
        if lowered.startswith("- llm_objective:"):
            reported_objective = line.split(":", 1)[1].strip() or None
        elif lowered.startswith("- failure_reason_codes:"):
            raw_codes = line.split(":", 1)[1].strip()
            reported_reason_codes = [code.strip() for code in raw_codes.split(",") if code.strip()]
        elif lowered.startswith("- response_summary:"):
            reported_response_summary = line.split(":", 1)[1].strip() or None
    expected_objective = str(entry.get("llm_objective") or "").strip()
    expected_reason_codes = [str(code).strip() for code in (entry.get("failure_reason_codes") or []) if str(code).strip()]
    verified = bool(reported_objective and reported_objective == expected_objective)
    if expected_reason_codes:
        verified = verified and all(code in reported_reason_codes for code in expected_reason_codes)
    return {
        "delegate_artifact_evidence_response_verified": verified,
        "delegate_reported_llm_objective": reported_objective,
        "delegate_reported_failure_reason_codes": reported_reason_codes,
        "delegate_reported_response_summary": reported_response_summary,
    }



def _artifact_section_body(content: str, heading: str) -> str:
    start = content.find(heading)
    if start == -1:
        return ""
    body = content[start + len(heading):]
    next_heading = re.search(r"\n##?\s+", body)
    if next_heading:
        body = body[: next_heading.start()]
    return body.strip()



def _normalize_alignment_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9_-]+", text.lower())
        if len(token) >= 4 and token not in {"response", "summary", "patch", "candidate", "steps", "build", "run"}
    }



def _patch_summary_matches_objective(summary: str, objective: str) -> bool:
    lowered = summary.lower()
    if objective == "deeper-stage-reach":
        return not any(term in lowered for term in ["persistent mode", "rewrite build", "build script", "meson", "cmake"])
    if objective == "build-fix":
        return any(term in lowered for term in ["build", "compile", "include", "header", "type", "guard"])
    if objective == "smoke-enable-or-fix":
        return any(term in lowered for term in ["guard", "smoke", "input", "seed", "early return"])
    if objective == "narrow-next-mutation":
        return any(term in lowered for term in ["comment", "guard", "narrow", "minimal", "scope"])
    return True



def _validate_delegate_patch_alignment(entry: dict[str, object], evidence_response: dict[str, object]) -> dict[str, object]:
    artifact_path = entry.get("delegate_artifact_path")
    if not artifact_path:
        return {
            "delegate_artifact_patch_alignment_verified": False,
            "delegate_reported_patch_summary": None,
        }
    path = Path(str(artifact_path))
    if not path.exists():
        return {
            "delegate_artifact_patch_alignment_verified": False,
            "delegate_reported_patch_summary": None,
        }
    content = path.read_text(encoding="utf-8")
    patch_summary = _artifact_section_body(content, "## Patch Summary")
    response_summary = str(evidence_response.get("delegate_reported_response_summary") or "").strip()
    objective = str(evidence_response.get("delegate_reported_llm_objective") or entry.get("llm_objective") or "").strip()
    patch_tokens = _normalize_alignment_tokens(patch_summary)
    response_tokens = _normalize_alignment_tokens(response_summary)
    token_overlap = bool(patch_tokens and response_tokens and (patch_tokens & response_tokens))
    objective_match = _patch_summary_matches_objective(patch_summary or response_summary, objective)
    verified = bool(patch_summary) and bool(response_summary) and token_overlap and objective_match
    return {
        "delegate_artifact_patch_alignment_verified": verified,
        "delegate_reported_patch_summary": patch_summary or None,
    }



def _classify_actual_mutation_shape(original_content: str, patched_content: str, *, scope: str) -> str:
    if original_content == patched_content:
        return "no-change"
    if scope == "guard-only":
        return "guard-only"
    if scope == "comment-only":
        return "comment-only"
    return scope or "unknown"



def _summary_matches_mutation_shape(summary: str, mutation_shape: str) -> bool:
    lowered = summary.lower()
    if mutation_shape == "guard-only":
        return any(term in lowered for term in ["guard", "size", "input", "early return"])
    if mutation_shape == "comment-only":
        return any(term in lowered for term in ["comment", "note", "todo", "annotation"])
    return True



def _validate_delegate_diff_alignment(
    *,
    original_content: str,
    patched_content: str,
    scope: str,
    reported_patch_summary: str | None,
) -> dict[str, object]:
    mutation_shape = _classify_actual_mutation_shape(original_content, patched_content, scope=scope)
    verified = _summary_matches_mutation_shape(str(reported_patch_summary or ""), mutation_shape)
    diff_lines = list(
        difflib.unified_diff(
            original_content.splitlines(),
            patched_content.splitlines(),
            fromfile="before",
            tofile="after",
            lineterm="",
        )
    )
    added_lines = [line[1:].strip() for line in diff_lines if line.startswith("+") and not line.startswith("+++") and line[1:].strip()]
    return {
        "delegate_diff_alignment_verified": verified,
        "actual_mutation_shape": mutation_shape,
        "changed_hunk_added_lines_preview": added_lines[:6],
    }



def _changed_hunk_lines_match_summary(added_lines: list[str], summary: str) -> bool:
    lowered_summary = summary.lower()
    joined = " ".join(added_lines).lower()
    if not added_lines:
        return False
    if any(term in lowered_summary for term in ["guard", "size", "input"]):
        return any(term in joined for term in ["if (size", "if(size", "return 0;", "return -1;"])
    if any(term in lowered_summary for term in ["comment", "note", "todo", "annotation"]):
        return any("hermes guarded apply candidate" in line.lower() for line in added_lines)
    return True



def _validate_delegate_hunk_intent(
    *,
    changed_hunk_added_lines_preview: list[str],
    reported_patch_summary: str | None,
) -> dict[str, object]:
    verified = _changed_hunk_lines_match_summary(changed_hunk_added_lines_preview, str(reported_patch_summary or ""))
    return {
        "delegate_hunk_intent_alignment_verified": verified,
    }



def _classify_changed_hunk_intent(added_lines: list[str]) -> str:
    joined = " ".join(str(line).strip().lower() for line in added_lines if str(line).strip())
    if not joined:
        return "no-change"
    if "#include " in joined or "typedef " in joined or "extern " in joined:
        return "build-fix"
    if "if (size" in joined or "if(size" in joined or "return 0;" in joined or "return -1;" in joined:
        return "guard-only"
    if "hermes guarded apply candidate" in joined:
        return "comment-only"
    return "unknown"



def _expected_hunk_intents_for_failure_reason(reason_code: str) -> set[str]:
    normalized = str(reason_code or "").strip().lower()
    if normalized in {
        "smoke-log-memory-safety-signal",
        "smoke-invalid-or-harness-mismatch",
        "harness-probe-memory-safety-signal",
        "fuzz-log-memory-safety-signal",
    }:
        return {"guard-only"}
    if normalized in {"build-blocker"}:
        return {"build-fix"}
    return set()



def _validate_failure_reason_hunk_alignment(
    *,
    failure_reason_codes: list[str] | None,
    top_failure_reason_codes: list[str] | None = None,
    changed_hunk_added_lines_preview: list[str],
) -> dict[str, object]:
    reasons = [str(code).strip() for code in (failure_reason_codes or []) if str(code).strip()]
    prioritized = [str(code).strip() for code in (top_failure_reason_codes or []) if str(code).strip()]
    hunk_intent = _classify_changed_hunk_intent(changed_hunk_added_lines_preview)
    mapped_prioritized = [code for code in prioritized if _expected_hunk_intents_for_failure_reason(code)]
    alignment_reasons: list[str] = []
    secondary_conflict_reasons: list[str] = []
    checked = 0
    primary_reason_code = mapped_prioritized[0] if mapped_prioritized else None
    priority_basis = "top_failure_reason_codes" if mapped_prioritized else "failure_reason_codes"

    reason_stream = [primary_reason_code] if primary_reason_code else reasons
    for idx, reason_code in enumerate(reason_stream):
        if not reason_code:
            continue
        expected = _expected_hunk_intents_for_failure_reason(reason_code)
        if not expected:
            continue
        checked += 1
        prefix = f"{reason_code}: "
        if primary_reason_code and idx == 0:
            prefix = f"{reason_code}: priority winner "
        if hunk_intent in expected:
            alignment_reasons.append(
                f"{prefix}matched hunk intent {hunk_intent}"
            )
        else:
            expected_text = "/".join(sorted(expected))
            alignment_reasons.append(
                f"{prefix}expects {expected_text} hunk intent, got {hunk_intent}"
            )

    deferred_reason_codes: list[str] = []
    if primary_reason_code:
        for reason_code in mapped_prioritized[1:]:
            expected = _expected_hunk_intents_for_failure_reason(reason_code)
            if not expected:
                continue
            if hunk_intent not in expected:
                deferred_reason_codes.append(reason_code)
                expected_text = "/".join(sorted(expected))
                secondary_conflict_reasons.append(
                    f"{reason_code}: deferred secondary reason expects {expected_text} hunk intent, got {hunk_intent}"
                )

    secondary_conflict_status = "present" if secondary_conflict_reasons else "none"
    secondary_conflict_count = len(secondary_conflict_reasons)

    if checked == 0:
        return {
            "failure_reason_hunk_alignment_verified": True,
            "failure_reason_hunk_alignment_summary": "no-mapped-failure-reasons",
            "failure_reason_hunk_alignment_reasons": [],
            "failure_reason_hunk_intent": hunk_intent,
            "failure_reason_hunk_primary_reason_code": primary_reason_code,
            "failure_reason_hunk_priority_basis": priority_basis,
            "failure_reason_hunk_secondary_conflict_status": secondary_conflict_status,
            "failure_reason_hunk_secondary_conflict_count": secondary_conflict_count,
            "failure_reason_hunk_secondary_conflict_reasons": secondary_conflict_reasons,
            "failure_reason_hunk_deferred_reason_codes": deferred_reason_codes,
        }
    verified = all("matched hunk intent" in reason for reason in alignment_reasons)
    return {
        "failure_reason_hunk_alignment_verified": verified,
        "failure_reason_hunk_alignment_summary": "priority-reason-aligned" if verified and primary_reason_code else ("mapped-failure-reasons-aligned" if verified else "mapped-failure-reasons-mismatch"),
        "failure_reason_hunk_alignment_reasons": alignment_reasons,
        "failure_reason_hunk_intent": hunk_intent,
        "failure_reason_hunk_primary_reason_code": primary_reason_code,
        "failure_reason_hunk_priority_basis": priority_basis,
        "failure_reason_hunk_secondary_conflict_status": secondary_conflict_status,
        "failure_reason_hunk_secondary_conflict_count": secondary_conflict_count,
        "failure_reason_hunk_secondary_conflict_reasons": secondary_conflict_reasons,
        "failure_reason_hunk_deferred_reason_codes": deferred_reason_codes,
    }



def delegate_session_visible(session_id: str, output: str) -> bool:
    if not session_id:
        return False
    return session_id in output


def delegate_artifact_shape_visible(entry: dict[str, object]) -> bool:
    artifact_path = entry.get("delegate_artifact_path")
    expected_sections = entry.get("delegate_expected_sections")
    if not artifact_path or not isinstance(expected_sections, list) or not expected_sections:
        return False
    path = Path(str(artifact_path))
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8")
    return all(str(section) in content for section in expected_sections)


def delegate_artifact_quality_visible(entry: dict[str, object]) -> bool:
    artifact_path = entry.get("delegate_artifact_path")
    quality_sections = entry.get("delegate_quality_sections")
    if not artifact_path or not isinstance(quality_sections, list) or not quality_sections:
        return False
    path = Path(str(artifact_path))
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8")
    for section in quality_sections:
        marker = str(section)
        start = content.find(marker)
        if start == -1:
            return False
        body = content[start + len(marker):]
        next_heading = re.search(r"\n##?\s+", body)
        if next_heading:
            body = body[: next_heading.start()]
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        if not lines:
            return False
    return True


def find_verifiable_refiner_entry(automation_dir: Path, *, repo_root: Path) -> tuple[Path, dict[str, object], dict[str, object]] | None:
    return select_refiner_registry_entry(
        automation_dir,
        repo_root=repo_root,
        matcher=lambda item: item.get("bridge_status") == "succeeded"
        and item.get("verification_status") not in {"verified", "unverified", "failed", "skipped"},
    )


def verify_cron_entry(entry: dict[str, object], *, repo_root: Path, probe_runner) -> dict[str, object]:
    job_id = str(entry.get("cron_job_id") or "")
    exit_code, output = probe_runner(["hermes", "cron", "list", "--all"], cwd=repo_root)
    job_verified = exit_code == 0 and cron_job_visible(job_id, output)
    metadata_verified = exit_code == 0 and cron_metadata_visible(entry, output)
    needs_metadata = any(entry.get(key) for key in ["cron_name", "cron_schedule", "cron_deliver"])
    lineage_verified = cron_prompt_lineage_visible(entry)
    needs_lineage = bool(entry.get("cron_prompt_lineage_tokens"))
    verified = job_verified and (metadata_verified if needs_metadata else True) and (lineage_verified if needs_lineage else True)
    if verified and needs_metadata and needs_lineage:
        summary = "cron-job-metadata-and-lineage-visible"
    elif verified and needs_metadata:
        summary = "cron-job-and-metadata-visible"
    elif verified:
        summary = "cron-job-visible"
    else:
        summary = "cron-job-not-visible"
    return {
        "verification_status": "verified" if verified else "unverified",
        "cron_job_verified": job_verified,
        "cron_metadata_verified": metadata_verified if needs_metadata else None,
        "cron_prompt_lineage_verified": lineage_verified if needs_lineage else None,
        "verification_summary": summary,
        "verification_probe_output": output,
    }


def verify_delegate_entry(entry: dict[str, object], *, repo_root: Path, probe_runner) -> dict[str, object]:
    session_id = str(entry.get("delegate_session_id") or "")
    artifact_path = Path(str(entry.get("delegate_artifact_path") or "")) if entry.get("delegate_artifact_path") else None
    exit_code, output = probe_runner(["hermes", "sessions", "list", "--limit", "200"], cwd=repo_root)
    session_verified = exit_code == 0 and delegate_session_visible(session_id, output)
    artifact_verified = bool(artifact_path and artifact_path.exists())
    shape_verified = artifact_verified and delegate_artifact_shape_visible(entry)
    needs_shape = bool(entry.get("delegate_expected_sections"))
    quality_verified = artifact_verified and delegate_artifact_quality_visible(entry)
    needs_quality = bool(entry.get("delegate_quality_sections"))
    evidence_response = _parse_delegate_evidence_response(entry)
    evidence_response_verified = bool(evidence_response.get("delegate_artifact_evidence_response_verified"))
    needs_evidence_response = bool(entry.get("llm_objective") or entry.get("failure_reason_codes"))
    patch_alignment = _validate_delegate_patch_alignment(entry, evidence_response)
    patch_alignment_verified = bool(patch_alignment.get("delegate_artifact_patch_alignment_verified"))
    needs_patch_alignment = needs_evidence_response
    verified = (
        session_verified
        and artifact_verified
        and (shape_verified if needs_shape else True)
        and (quality_verified if needs_quality else True)
        and (evidence_response_verified if needs_evidence_response else True)
        and (patch_alignment_verified if needs_patch_alignment else True)
    )
    if verified and needs_shape and needs_quality and needs_evidence_response:
        summary = "delegate-session-artifact-shape-quality-and-evidence-visible"
    elif verified and needs_shape and needs_quality:
        summary = "delegate-session-artifact-shape-and-quality-visible"
    elif verified and needs_shape:
        summary = "delegate-session-artifact-and-shape-visible"
    elif verified:
        summary = "delegate-session-and-artifact-visible"
    elif session_verified and artifact_verified and needs_shape and needs_quality:
        summary = "delegate-session-artifact-visible-shape-or-quality-missing"
    elif session_verified and artifact_verified and needs_shape:
        summary = "delegate-session-artifact-visible-shape-missing"
    elif session_verified:
        summary = "delegate-session-visible-artifact-missing"
    elif artifact_verified:
        summary = "delegate-artifact-visible-session-missing"
    else:
        summary = "delegate-session-and-artifact-missing"
    return {
        "verification_status": "verified" if verified else "unverified",
        "delegate_session_verified": session_verified,
        "delegate_artifact_verified": artifact_verified,
        "delegate_artifact_shape_verified": shape_verified if needs_shape else None,
        "delegate_artifact_quality_verified": quality_verified if needs_quality else None,
        "delegate_artifact_evidence_response_verified": evidence_response_verified if needs_evidence_response else None,
        "delegate_artifact_patch_alignment_verified": patch_alignment_verified if needs_patch_alignment else None,
        "delegate_reported_llm_objective": evidence_response.get("delegate_reported_llm_objective") if needs_evidence_response else None,
        "delegate_reported_failure_reason_codes": evidence_response.get("delegate_reported_failure_reason_codes") if needs_evidence_response else None,
        "delegate_reported_response_summary": evidence_response.get("delegate_reported_response_summary") if needs_evidence_response else None,
        "delegate_reported_patch_summary": patch_alignment.get("delegate_reported_patch_summary") if needs_patch_alignment else None,
        "verification_summary": summary,
        "verification_probe_output": output,
    }


def verify_next_refiner_result(automation_dir: Path, *, repo_root: Path, probe_runner=None) -> dict[str, object] | None:
    found = find_verifiable_refiner_entry(automation_dir, repo_root=repo_root)
    if found is None:
        return None
    registry_path, data, entry = found
    action_code = str(entry.get("action_code") or "unknown")
    runner = probe_runner or run_probe_command
    if entry.get("bridge_channel") == "hermes-cli-cron":
        verification = verify_cron_entry(entry, repo_root=repo_root, probe_runner=runner)
    else:
        verification = verify_delegate_entry(entry, repo_root=repo_root, probe_runner=runner)
    entry["verification_status"] = verification["verification_status"]
    entry["verification_summary"] = verification["verification_summary"]
    sync_refiner_lifecycle(entry)
    entry["verification_checked_at"] = dt.datetime.now().isoformat(timespec="seconds")
    for key, value in verification.items():
        if key not in {"verification_status", "verification_summary"} and value is not None:
            entry[key] = value
    save_registry(registry_path, data)
    return {
        "registry": str(registry_path),
        "entry_key": entry.get("key"),
        "action_code": action_code,
        **{key: value for key, value in verification.items() if value is not None},
        "selected_candidate_id": entry.get("selected_candidate_id"),
        "selected_entrypoint_path": entry.get("selected_entrypoint_path"),
        "selected_recommended_mode": entry.get("selected_recommended_mode"),
        "selected_target_stage": entry.get("selected_target_stage"),
    }


def find_verification_policy_candidate(automation_dir: Path) -> tuple[Path, dict[str, object], dict[str, object]] | None:
    registry_specs = [
        ("mode_refinements.json", "shift_weight_to_deeper_harness"),
        ("slow_lane_candidates.json", "split_slow_lane"),
        ("corpus_refinements.json", "minimize_and_reseed"),
        ("harness_review_queue.json", "halt_and_review_harness"),
        ("harness_correction_regeneration_queue.json", "regenerate_harness_correction"),
    ]
    for registry_name, expected_action in registry_specs:
        path = automation_dir / registry_name
        data = load_registry(path, {"entries": []})
        entries = data.setdefault("entries", [])
        entry = next(
            (
                item
                for item in entries
                if item.get("verification_status") == "unverified"
                and item.get("verification_policy_status") not in {"retry", "escalate", "resolved", "skipped"}
            ),
            None,
        )
        if entry is None:
            save_registry(path, data)
            continue
        entry.setdefault("action_code", expected_action)
        return path, data, entry
    return None


def rerank_candidate_registry(candidates: list[dict[str, object]]) -> None:
    for candidate in candidates:
        _ensure_verification_candidate_debt_fields(candidate)
        candidate["debt_penalty"] = _verification_candidate_debt_penalty(candidate)
        candidate["effective_score"] = int(candidate.get("score") or 0) - int(candidate.get("debt_penalty") or 0)
    candidates.sort(
        key=lambda item: (
            -int(item.get("effective_score") or 0),
            -int(item.get("score") or 0),
            str(item.get("candidate_id") or ""),
        )
    )
    for index, candidate in enumerate(candidates, start=1):
        candidate["rank"] = index


VERIFICATION_DEBT_WEIGHTS = {
    "seed_debt_count": 6,
    "review_debt_count": 10,
    "build_debt_count": 8,
    "smoke_debt_count": 5,
    "instability_debt_count": 7,
    "verification_retry_debt": 4,
    "verification_escalation_count": 6,
    "fail_streak": 3,
    "pass_streak": -2,
    "probe_pass_count": 0,
    "probe_fail_count": 0,
    "build_pass_count": 0,
    "build_fail_count": 0,
    "smoke_pass_count": 0,
    "smoke_fail_count": 0,
    "verification_verified_count": 0,
    "verification_unverified_count": 0,
}

VERIFICATION_EVIDENCE_WEIGHTS = {
    "probe_pass_count": 8,
    "probe_fail_count": -6,
    "build_pass_count": 4,
    "build_fail_count": -5,
    "smoke_pass_count": 6,
    "smoke_fail_count": -6,
    "verification_verified_count": 7,
    "verification_unverified_count": -4,
}


def _ensure_verification_candidate_debt_fields(candidate: dict[str, object]) -> None:
    for field in VERIFICATION_DEBT_WEIGHTS:
        candidate[field] = int(candidate.get(field) or 0)


def _verification_candidate_debt_penalty(candidate: dict[str, object]) -> int:
    _ensure_verification_candidate_debt_fields(candidate)
    penalty = 0
    for field, weight in VERIFICATION_DEBT_WEIGHTS.items():
        penalty += int(candidate.get(field) or 0) * weight
    return penalty


def _verification_execution_evidence_score(candidate: dict[str, object]) -> int:
    _ensure_verification_candidate_debt_fields(candidate)
    evidence = 0
    for field, weight in VERIFICATION_EVIDENCE_WEIGHTS.items():
        evidence += int(candidate.get(field) or 0) * weight
    return evidence


def close_verification_policy_feedback_into_candidate_registry(
    repo_root: Path,
    *,
    entry: dict[str, object],
    decision: dict[str, object],
) -> dict[str, object]:
    registry_dir = repo_root / "fuzz-records" / "harness-candidates"
    registry_path = registry_dir / "ranked-candidates.json"
    markdown_path = registry_dir / "ranked-candidates.md"
    candidate_id = str(entry.get("selected_candidate_id") or "")
    if not candidate_id:
        return {"updated": False, "reason": "missing-selected-candidate-id", "registry_path": str(registry_path)}

    registry_dir.mkdir(parents=True, exist_ok=True)
    data = load_registry(registry_path, {"project": repo_root.name, "candidates": []})
    data.setdefault("project", repo_root.name)
    candidates = data.setdefault("candidates", [])
    if not isinstance(candidates, list):
        candidates = []
        data["candidates"] = candidates

    candidate = next((item for item in candidates if str(item.get("candidate_id") or "") == candidate_id), None)
    if candidate is None:
        candidate = {
            "candidate_id": candidate_id,
            "entrypoint_path": entry.get("selected_entrypoint_path"),
            "recommended_mode": entry.get("selected_recommended_mode"),
            "target_stage": entry.get("selected_target_stage"),
            "score": 0,
            "status": entry.get("selected_candidate_status") or "observed",
            "rank": len(candidates) + 1,
        }
        candidates.append(candidate)

    _ensure_verification_candidate_debt_fields(candidate)
    candidate.setdefault("entrypoint_path", entry.get("selected_entrypoint_path"))
    if entry.get("selected_entrypoint_path"):
        candidate["entrypoint_path"] = entry.get("selected_entrypoint_path")
    if entry.get("selected_recommended_mode") and not candidate.get("recommended_mode"):
        candidate["recommended_mode"] = entry.get("selected_recommended_mode")
    if entry.get("selected_target_stage") and not candidate.get("target_stage"):
        candidate["target_stage"] = entry.get("selected_target_stage")

    decision_name = str(decision.get("decision") or "")
    reason = str(decision.get("reason") or "")
    summary = str(entry.get("verification_summary") or "")
    verification_status = str(entry.get("verification_status") or "")
    current_score = int(candidate.get("score") or 0)
    candidate["last_verification_policy_decision"] = decision_name
    candidate["last_verification_policy_reason"] = reason
    candidate["verification_policy_updated_at"] = dt.datetime.now().isoformat(timespec="seconds")
    if verification_status == "verified":
        candidate["verification_verified_count"] = int(candidate.get("verification_verified_count") or 0) + 1
    elif verification_status == "unverified":
        candidate["verification_unverified_count"] = int(candidate.get("verification_unverified_count") or 0) + 1

    if decision_name == "retry":
        candidate["verification_retry_debt"] = int(candidate.get("verification_retry_debt") or 0) + 1
        candidate["fail_streak"] = int(candidate.get("fail_streak") or 0) + 1
        candidate["pass_streak"] = 0
        if reason == "candidate-seed-debt":
            candidate["seed_debt_count"] = int(candidate.get("seed_debt_count") or 0) + 1
            candidate["status"] = "seed_debt"
            candidate["score"] = current_score - 3
        elif "smoke" in summary:
            candidate["smoke_debt_count"] = int(candidate.get("smoke_debt_count") or 0) + 1
            candidate["status"] = "smoke_debt"
            candidate["score"] = current_score - 2
        elif "build" in summary:
            candidate["build_debt_count"] = int(candidate.get("build_debt_count") or 0) + 1
            candidate["status"] = "build_debt"
            candidate["score"] = current_score - 3
        else:
            candidate["instability_debt_count"] = int(candidate.get("instability_debt_count") or 0) + 1
            candidate["score"] = current_score - 1
    elif decision_name == "escalate":
        candidate["verification_escalation_count"] = int(candidate.get("verification_escalation_count") or 0) + 1
        candidate["review_debt_count"] = int(candidate.get("review_debt_count") or 0) + 1
        candidate["fail_streak"] = int(candidate.get("fail_streak") or 0) + 1
        candidate["pass_streak"] = 0
        if "smoke" in summary:
            candidate["smoke_debt_count"] = int(candidate.get("smoke_debt_count") or 0) + 1
        elif "build" in summary:
            candidate["build_debt_count"] = int(candidate.get("build_debt_count") or 0) + 1
        else:
            candidate["instability_debt_count"] = int(candidate.get("instability_debt_count") or 0) + 1
        candidate["status"] = "review_required"
        candidate["score"] = current_score - (10 if reason == "candidate-review-required" else 6)
    else:
        candidate["score"] = current_score

    candidate["debt_penalty"] = _verification_candidate_debt_penalty(candidate)
    candidate["execution_evidence_score"] = _verification_execution_evidence_score(candidate)
    candidate["effective_score"] = int(candidate.get("score") or 0) + int(candidate.get("execution_evidence_score") or 0) - int(candidate.get("debt_penalty") or 0)

    data["selected_candidate_id"] = candidate_id
    data["feedback_action_code"] = entry.get("action_code")
    data["feedback_reason"] = reason
    rerank_candidate_registry(candidates)
    save_registry(registry_path, data)
    markdown_path.write_text(render_ranked_candidate_markdown_impl(data) + "\n", encoding="utf-8")
    return {
        "updated": True,
        "registry_path": str(registry_path),
        "registry_plan_path": str(markdown_path),
        "selected_candidate_id": candidate_id,
        "selected_candidate_status": candidate.get("status"),
        "selected_candidate_score": candidate.get("score"),
        "policy_decision": decision_name,
        "policy_reason": reason,
    }


def decide_verification_policy(entry: dict[str, object]) -> dict[str, object]:
    retry_count = int(entry.get("verification_retry_count") or 0)
    summary = str(entry.get("verification_summary") or "")
    bridge_channel = str(entry.get("bridge_channel") or "")
    candidate_status = str(entry.get("selected_candidate_status") or "")
    if retry_count >= 2:
        return {"decision": "escalate", "reason": "retry-budget-exhausted"}
    if candidate_status == "review_required":
        return {"decision": "escalate", "reason": "candidate-review-required"}
    if candidate_status == "seed_debt":
        return {"decision": "retry", "reason": "candidate-seed-debt"}
    if bridge_channel == "hermes-cli-delegate" and ("shape" in summary or "quality" in summary):
        return {"decision": "escalate", "reason": "delegate-quality-gap"}
    return {"decision": "retry", "reason": "verification-evidence-missing"}


def write_verification_retry_artifact(repo_root: Path, *, action_code: str, entry: dict[str, object], reason: str) -> Path:
    policy_dir = repo_root / "fuzz-records" / "refiner-policy"
    policy_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify_run_dir(str(entry.get("run_dir") or "unknown-run"))
    path = policy_dir / f"{action_code}-{slug}-retry.md"
    path.write_text(
        "\n".join(
            [
                f"# Verification Retry Plan: {action_code}",
                "",
                f"- run_dir: {entry.get('run_dir')}",
                f"- verification_summary: {entry.get('verification_summary')}",
                f"- reason: {reason}",
                f"- prior_retry_count: {entry.get('verification_retry_count') or 0}",
                f"- selected_candidate_id: {entry.get('selected_candidate_id')}",
                f"- selected_entrypoint_path: {entry.get('selected_entrypoint_path')}",
                f"- selected_candidate_status: {entry.get('selected_candidate_status')}",
                "",
                "## Next Step",
                "- Re-run verification after the relevant cron/session/artifact evidence has had time to appear.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def write_verification_escalation_artifact(repo_root: Path, *, action_code: str, entry: dict[str, object], reason: str) -> Path:
    policy_dir = repo_root / "fuzz-records" / "refiner-policy"
    policy_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify_run_dir(str(entry.get("run_dir") or "unknown-run"))
    path = policy_dir / f"{action_code}-{slug}-escalation.md"
    path.write_text(
        "\n".join(
            [
                f"# Verification Escalation: {action_code}",
                "",
                f"- run_dir: {entry.get('run_dir')}",
                f"- verification_summary: {entry.get('verification_summary')}",
                f"- reason: {reason}",
                f"- retry_count: {entry.get('verification_retry_count') or 0}",
                f"- selected_candidate_id: {entry.get('selected_candidate_id')}",
                f"- selected_entrypoint_path: {entry.get('selected_entrypoint_path')}",
                f"- selected_candidate_status: {entry.get('selected_candidate_status')}",
                "",
                "## Escalation Note",
                "- Manual review is recommended before any further automated retry.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def apply_verification_failure_policy(automation_dir: Path, *, repo_root: Path) -> dict[str, object] | None:
    found = find_verification_policy_candidate(automation_dir)
    if found is None:
        return None
    registry_path, data, entry = found
    action_code = str(entry.get("action_code") or "unknown")
    decision = decide_verification_policy(entry)
    entry["verification_policy_status"] = decision["decision"]
    sync_refiner_lifecycle(entry)
    entry["verification_policy_checked_at"] = dt.datetime.now().isoformat(timespec="seconds")
    if decision["decision"] == "retry":
        entry["verification_retry_count"] = int(entry.get("verification_retry_count") or 0) + 1
        artifact_path = write_verification_retry_artifact(repo_root, action_code=action_code, entry=entry, reason=str(decision["reason"]))
        entry["verification_retry_plan_path"] = str(artifact_path)
    else:
        entry["verification_escalation_reason"] = str(decision["reason"])
        artifact_path = write_verification_escalation_artifact(repo_root, action_code=action_code, entry=entry, reason=str(decision["reason"]))
        entry["verification_escalation_path"] = str(artifact_path)

    reverse_linked_manifest_path = None
    apply_manifest_path = Path(str(entry.get("apply_candidate_manifest_path") or "")) if entry.get("apply_candidate_manifest_path") else None
    if entry.get("recovery_followup_reason") and apply_manifest_path and apply_manifest_path.exists():
        apply_manifest = load_registry(apply_manifest_path, {})
        apply_manifest["recovery_followup_failure_policy_status"] = decision["decision"]
        apply_manifest["recovery_followup_failure_policy_reason"] = decision["reason"]
        apply_manifest["recovery_followup_failure_action_code"] = action_code
        apply_manifest["recovery_followup_failure_summary"] = entry.get("verification_summary")
        apply_manifest["recovery_followup_failure_artifact_path"] = str(artifact_path)
        apply_manifest["recovery_followup_failure_checked_at"] = dt.datetime.now().isoformat(timespec="seconds")
        apply_manifest["recovery_followup_failure_registry"] = str(registry_path)
        apply_manifest["recovery_followup_failure_entry_key"] = entry.get("key")
        apply_manifest_path.write_text(json.dumps(apply_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        reverse_linked_manifest_path = str(apply_manifest_path)

    candidate_registry_update = close_verification_policy_feedback_into_candidate_registry(
        repo_root,
        entry=entry,
        decision=decision,
    )
    if candidate_registry_update.get("updated"):
        entry["selected_candidate_status"] = candidate_registry_update.get("selected_candidate_status")
        entry["candidate_registry_path"] = candidate_registry_update.get("registry_path")
        entry["candidate_registry_plan_path"] = candidate_registry_update.get("registry_plan_path")
    save_registry(registry_path, data)
    return {
        "registry": str(registry_path),
        "entry_key": entry.get("key"),
        "action_code": action_code,
        "policy_decision": decision["decision"],
        "policy_reason": decision["reason"],
        "artifact_path": str(artifact_path),
        "selected_candidate_id": entry.get("selected_candidate_id"),
        "selected_entrypoint_path": entry.get("selected_entrypoint_path"),
        "selected_candidate_status": entry.get("selected_candidate_status"),
        "candidate_registry_updated": bool(candidate_registry_update.get("updated")),
        "candidate_registry_path": candidate_registry_update.get("registry_path"),
        "candidate_registry_plan_path": candidate_registry_update.get("registry_plan_path"),
        "reverse_linked_apply_candidate_manifest_path": reverse_linked_manifest_path,
    }


def launch_next_refiner_bridge(automation_dir: Path, *, repo_root: Path) -> dict[str, object] | None:
    found = find_armed_refiner_entry(automation_dir, repo_root=repo_root)
    if found is None:
        return None
    registry_path, data, entry = found
    action_code = str(entry.get("action_code") or "unknown")
    script_path = Path(str(entry.get("bridge_script_path") or ""))
    if not script_path.exists():
        entry["bridge_status"] = "failed"
        entry["launch_status"] = "failed"
        sync_refiner_lifecycle(entry)
        entry["bridge_exit_code"] = 127
        entry["bridge_failure_reason"] = f"bridge script missing: {script_path}"
        entry["bridge_launched_at"] = dt.datetime.now().isoformat(timespec="seconds")
        save_registry(registry_path, data)
        return {
            "registry": str(registry_path),
            "entry_key": entry.get("key"),
            "action_code": action_code,
            "bridge_status": entry.get("bridge_status"),
            "exit_code": 127,
        }

    launch_dir = repo_root / "fuzz-records" / "refiner-launches"
    launch_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify_run_dir(str(entry.get("run_dir") or "unknown-run"))
    log_path = launch_dir / f"{action_code}-{slug}-launch.log"
    result = launch_bridge_script(
        script_path,
        timeout_seconds=int(entry.get("bridge_timeout_seconds") or get_refiner_orchestration_spec(action_code).get("bridge_timeout_seconds") or BRIDGE_SCRIPT_TIMEOUT_SECONDS),
    )
    output_text = str(result.get("output") or "")
    log_path.write_text(output_text, encoding="utf-8")

    exit_code = int(result.get("exit_code") or 0)
    bridge_status = "succeeded" if exit_code == 0 else "failed"
    parsed = extract_bridge_result_metadata(bridge_channel=str(entry.get("bridge_channel") or ""), output=output_text)
    entry["bridge_status"] = bridge_status
    entry["launch_status"] = bridge_status
    sync_refiner_lifecycle(entry)
    entry["bridge_exit_code"] = exit_code
    entry["bridge_launch_log_path"] = str(log_path)
    entry["bridge_launched_at"] = dt.datetime.now().isoformat(timespec="seconds")
    for key, value in parsed.items():
        if value is not None:
            entry[key] = value
    save_registry(registry_path, data)
    return {
        "registry": str(registry_path),
        "entry_key": entry.get("key"),
        "action_code": action_code,
        "bridge_status": bridge_status,
        "exit_code": exit_code,
        "bridge_launch_log_path": str(log_path),
        **{key: value for key, value in parsed.items() if value is not None},
    }


def execute_next_refiner_action(automation_dir: Path, *, repo_root: Path) -> dict[str, object] | None:
    found = select_refiner_registry_entry(
        automation_dir,
        repo_root=repo_root,
        matcher=lambda item: item.get("status") not in {"completed", "skipped"},
    )
    if found is None:
        return None
    path, data, entry = found
    action_code = str(entry.get("action_code") or "unknown")
    entry["status"] = "completed"
    sync_refiner_lifecycle(entry)
    entry["completed_at"] = dt.datetime.now().isoformat(timespec="seconds")
    replay_execution = None
    corpus_refinement_execution = None
    duplicate_followup = None
    if action_code == "review_duplicate_crash_replay":
        replay_execution = execute_duplicate_crash_replay_probe(repo_root, entry)
        duplicate_followup = record_duplicate_replay_followup(automation_dir, entry)
        if isinstance(duplicate_followup, dict) and isinstance(duplicate_followup.get("entry"), dict):
            followup_entry = duplicate_followup["entry"]
            entry["replay_followup_action_code"] = followup_entry.get("action_code")
            entry["replay_followup_registry"] = duplicate_followup.get("path")
            entry["replay_followup_entry_key"] = followup_entry.get("key")
            entry["replay_followup_candidate_route"] = followup_entry.get("candidate_route")
    elif action_code == "minimize_and_reseed":
        corpus_refinement_execution = execute_corpus_refinement_probe(repo_root, entry)
    plan_path = write_refiner_plan(repo_root, action_code=action_code, entry=entry)
    entry["executor_plan_path"] = str(plan_path)
    save_registry(path, data)
    llm_evidence_packet = refresh_llm_evidence_packet_best_effort(repo_root)
    result = {
        "registry": str(path),
        "registry_name": path.name,
        "entry_key": entry.get("key"),
        "action_code": action_code,
        "status": entry.get("status"),
        "plan_path": str(plan_path),
        "queue_weight": entry.get("queue_weight"),
        "queue_rank": entry.get("queue_rank"),
    }
    if isinstance(replay_execution, dict):
        result["replay_execution_status"] = replay_execution.get("status")
        result["replay_execution_json_path"] = replay_execution.get("json_path")
        result["replay_execution_markdown_path"] = replay_execution.get("markdown_path")
    if isinstance(corpus_refinement_execution, dict):
        result["corpus_refinement_execution_status"] = corpus_refinement_execution.get("status")
        result["corpus_refinement_execution_json_path"] = corpus_refinement_execution.get("json_path")
        result["corpus_refinement_execution_markdown_path"] = corpus_refinement_execution.get("markdown_path")
    if isinstance(duplicate_followup, dict) and isinstance(duplicate_followup.get("entry"), dict):
        followup_entry = duplicate_followup["entry"]
        result["replay_followup_action_code"] = followup_entry.get("action_code")
        result["replay_followup_registry"] = duplicate_followup.get("path")
        result["replay_followup_entry_key"] = followup_entry.get("key")
    if isinstance(llm_evidence_packet, dict):
        result["llm_evidence_json_path"] = llm_evidence_packet.get("llm_evidence_json_path")
        result["llm_evidence_markdown_path"] = llm_evidence_packet.get("llm_evidence_markdown_path")
    return result


def parse_iso_timestamp(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value)
    except ValueError:
        return None


def classify_stage_depth(stage: str | None) -> str:
    if not stage:
        return "unknown"
    if stage == "parse-main-header":
        return "shallow"
    return "deep"


def compute_semantic_history_summary(history: list[dict[str, object]]) -> dict[str, object]:
    crash_entries = [entry for entry in history if entry.get("outcome") == "crash"]
    stage_counts: dict[str, int] = {}
    deep_crash_count = 0
    shallow_crash_count = 0
    for entry in crash_entries:
        stage = entry.get("crash_stage")
        if isinstance(stage, str) and stage:
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
            depth_class = classify_stage_depth(stage)
            if depth_class == "deep":
                deep_crash_count += 1
            elif depth_class == "shallow":
                shallow_crash_count += 1
    dominant_stage = None
    if stage_counts:
        dominant_stage = max(stage_counts.items(), key=lambda item: item[1])[0]
    total_crashes = len(crash_entries)
    return {
        "total_crashes": total_crashes,
        "deep_crash_count": deep_crash_count,
        "shallow_crash_count": shallow_crash_count,
        "deep_ratio": (deep_crash_count / total_crashes) if total_crashes else 0.0,
        "shallow_ratio": (shallow_crash_count / total_crashes) if total_crashes else 0.0,
        "dominant_stage": dominant_stage,
        "stage_counts": stage_counts,
    }


def _history_entry_from_snapshot(snapshot: dict[str, object]) -> dict[str, object]:
    return {
        "updated_at": snapshot.get("updated_at"),
        "outcome": snapshot.get("outcome"),
        "cov": snapshot.get("cov"),
        "ft": snapshot.get("ft"),
        "exec_per_second": snapshot.get("exec_per_second"),
        "corpus_units": snapshot.get("corpus_units"),
        "corpus_size": snapshot.get("corpus_size"),
        "seconds_since_progress": snapshot.get("seconds_since_progress"),
        "timeout_detected": snapshot.get("timeout_detected"),
        "crash_stage": snapshot.get("crash_stage"),
        "crash_fingerprint": snapshot.get("crash_fingerprint"),
        "policy_profile_severity": snapshot.get("policy_profile_severity"),
        "policy_action_code": snapshot.get("policy_action_code"),
        "policy_matched_triggers": snapshot.get("policy_matched_triggers"),
        "run_dir": snapshot.get("run_dir"),
        "report": snapshot.get("report"),
    }


def append_run_history(automation_dir: Path, snapshot: dict[str, object], *, max_entries: int = 200) -> dict[str, object]:
    path = automation_dir / "run_history.json"
    data = load_registry(path, {"entries": []})
    entries = data.setdefault("entries", [])
    entries.append(_history_entry_from_snapshot(snapshot))
    if len(entries) > max_entries:
        data["entries"] = entries[-max_entries:]
    save_registry(path, data)
    return {"path": str(path), "appended": 1, "count": len(data["entries"])}


def upsert_run_history_entry(automation_dir: Path, snapshot: dict[str, object], *, max_entries: int = 200) -> dict[str, object]:
    path = automation_dir / "run_history.json"
    data = load_registry(path, {"entries": []})
    entries = data.get("entries") if isinstance(data.get("entries"), list) else []
    updated_entry = _history_entry_from_snapshot(snapshot)
    run_dir = str(snapshot.get("run_dir") or "")
    report = str(snapshot.get("report") or "")
    updated_entries: list[dict[str, object]] = []
    replaced = 0
    inserted = False
    for existing in entries:
        if not isinstance(existing, dict):
            continue
        existing_run_dir = str(existing.get("run_dir") or "")
        existing_report = str(existing.get("report") or "")
        matches = (run_dir and existing_run_dir == run_dir) or (report and existing_report == report)
        if matches:
            replaced += 1
            if not inserted:
                updated_entries.append(updated_entry)
                inserted = True
            continue
        updated_entries.append(existing)
    if not inserted:
        updated_entries.append(updated_entry)
    if len(updated_entries) > max_entries:
        updated_entries = updated_entries[-max_entries:]
    data["entries"] = updated_entries
    save_registry(path, data)
    return {
        "path": str(path),
        "appended": 0 if inserted else 1,
        "replaced": replaced,
        "count": len(updated_entries),
    }


def collect_metrics_from_log(log_path: Path) -> Metrics:
    metrics = Metrics()
    if not log_path.exists():
        return metrics
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        metrics.update_from_line(line)
    return metrics


def _select_rehydration_run_dir(repo_root: Path, explicit_run_dir: Path | None) -> Path | None:
    if explicit_run_dir is not None:
        return explicit_run_dir.resolve()
    current_status_path = repo_root / "fuzz-artifacts" / "current_status.json"
    current_status = load_registry(current_status_path, {})
    current_run_dir = current_status.get("run_dir")
    if isinstance(current_run_dir, str) and current_run_dir.strip():
        return Path(current_run_dir).resolve()
    runs_root = repo_root / "fuzz-artifacts" / "runs"
    if not runs_root.exists():
        return None
    candidates = sorted((path for path in runs_root.iterdir() if path.is_dir()), key=lambda path: path.name)
    return candidates[-1] if candidates else None


def _remove_stale_crash_records_for_run(
    index_path: Path,
    *,
    run_dir: str,
    report_path: str,
    artifact_path: str | None,
    stale_fingerprint: str | None,
    new_fingerprint: str,
) -> None:
    data = load_crash_index(index_path)
    fingerprints = data.setdefault("fingerprints", {})
    if not isinstance(fingerprints, dict):
        fingerprints = {}
        data["fingerprints"] = fingerprints
    for fingerprint, record in list(fingerprints.items()):
        if fingerprint == new_fingerprint or not isinstance(record, dict):
            continue
        artifacts = record.get("artifacts") if isinstance(record.get("artifacts"), list) else []
        matches_artifact = bool(artifact_path) and artifact_path in artifacts
        matches_run = str(record.get("first_seen_run") or "") == run_dir and str(record.get("last_seen_run") or "") == run_dir
        matches_report = str(record.get("first_seen_report") or "") == report_path and str(record.get("last_seen_report") or "") == report_path
        matches_stale = bool(stale_fingerprint) and fingerprint == stale_fingerprint
        if matches_stale or matches_artifact or matches_run or matches_report:
            occurrence_count = int(record.get("occurrence_count") or 0)
            if occurrence_count <= 1 or len(artifacts) <= 1:
                fingerprints.pop(fingerprint, None)
                continue
            cleaned_artifacts = [item for item in artifacts if item != artifact_path]
            record["artifacts"] = cleaned_artifacts
            record["occurrence_count"] = max(0, occurrence_count - 1)
            if str(record.get("first_seen_run") or "") == run_dir:
                record["first_seen_run"] = None
                record["first_seen_report"] = None
            if str(record.get("last_seen_run") or "") == run_dir:
                record["last_seen_run"] = None
                record["last_seen_report"] = None
    save_crash_index(index_path, data)


def _replace_report_section(report_text: str, heading: str, lines: list[str]) -> str:
    section_text = "\n".join([heading, "", *lines]).rstrip() + "\n"
    pattern = re.compile(rf"(?ms)^({re.escape(heading)}\n\n).*?(?=^##\s|\Z)")
    if pattern.search(report_text):
        return pattern.sub(section_text + "\n", report_text, count=1)
    trimmed = report_text.rstrip()
    if not trimmed:
        return section_text + "\n"
    return trimmed + "\n\n" + section_text + "\n"



def rewrite_rehydrated_report(
    report_path: Path,
    *,
    updated_snapshot: dict[str, object],
    metrics: Metrics,
    crash_info: dict[str, object],
    artifact_event: dict[str, object],
    policy_action: dict[str, object],
) -> bool:
    if not report_path.exists():
        return False
    report_text = report_path.read_text(encoding="utf-8", errors="replace")
    report_text = _replace_report_section(
        report_text,
        "## Artifact Classification",
        [
            f"- artifact_category: {artifact_event.get('category')}",
            f"- artifact_reason: {artifact_event.get('reason')}",
        ],
    )
    report_text = _replace_report_section(
        report_text,
        "## Policy Action",
        [
            f"- policy_priority: {policy_action.get('priority')}",
            f"- policy_action_code: {policy_action.get('action_code')}",
            f"- policy_next_mode: {policy_action.get('next_mode')}",
            f"- policy_bucket: {policy_action.get('bucket')}",
            f"- policy_recommended_action: {policy_action.get('recommended_action')}",
            f"- policy_matched_triggers: {policy_action.get('matched_triggers')}",
            f"- policy_profile_severity: {policy_action.get('profile_severity')}",
            f"- policy_profile_labels: {policy_action.get('profile_labels')}",
        ],
    )
    report_text = _replace_report_section(
        report_text,
        "## Crash Fingerprint",
        [
            f"- crash_kind: {crash_info.get('kind')}",
            f"- crash_location: {crash_info.get('location')}",
            f"- crash_summary: {crash_info.get('summary')}",
            f"- crash_stage: {crash_info.get('stage')}",
            f"- crash_stage_class: {crash_info.get('stage_class')}",
            f"- crash_stage_depth_rank: {crash_info.get('stage_depth_rank')}",
            f"- crash_stage_confidence: {crash_info.get('stage_confidence')}",
            f"- crash_stage_match_source: {crash_info.get('stage_match_source')}",
            f"- crash_stage_reason: {crash_info.get('stage_reason')}",
            f"- crash_fingerprint: {crash_info.get('fingerprint')}",
            f"- crash_is_duplicate: {crash_info.get('is_duplicate')}",
            f"- crash_occurrence_count: {crash_info.get('occurrence_count')}",
            f"- crash_first_seen_run: {crash_info.get('first_seen_run')}",
            f"- crash_artifact: {crash_info.get('artifact_path')}",
            f"- crash_artifact_sha1: {crash_info.get('artifact_sha1')}",
        ],
    )
    report_text = _replace_report_section(
        report_text,
        "## Crash Or Timeout Excerpt",
        [
            "```text",
            "\n".join(metrics.top_crash_lines) if metrics.top_crash_lines else "none",
            "```",
        ],
    )
    report_text = _replace_report_section(
        report_text,
        "## Recommended Next Action",
        [
            recommended_action(str(updated_snapshot.get("outcome") or ""), policy_action=policy_action),
        ],
    )
    report_path.write_text(report_text, encoding="utf-8")
    return True



def rehydrate_run_artifacts(repo_root: Path, *, run_dir: Path | None = None) -> dict[str, object]:
    selected_run_dir = _select_rehydration_run_dir(repo_root, run_dir)
    if selected_run_dir is None:
        return {"rehydrated": False, "reason": "no-run-dir-found"}

    status_path = selected_run_dir / "status.json"
    fuzz_log_path = selected_run_dir / "fuzz.log"
    report_path = selected_run_dir / "FUZZING_REPORT.md"
    if not status_path.exists():
        return {"rehydrated": False, "reason": "missing-status-json", "run_dir": str(selected_run_dir)}
    if not fuzz_log_path.exists():
        return {"rehydrated": False, "reason": "missing-fuzz-log", "run_dir": str(selected_run_dir)}

    snapshot = load_registry(status_path, {})
    if not isinstance(snapshot, dict):
        return {"rehydrated": False, "reason": "invalid-status-json", "run_dir": str(selected_run_dir)}

    metrics = collect_metrics_from_log(fuzz_log_path)
    if not metrics.top_crash_lines:
        return {"rehydrated": False, "reason": "no-crash-signature-found", "run_dir": str(selected_run_dir)}

    target_profile_path_value = snapshot.get("target_profile_path")
    target_profile_path = Path(target_profile_path_value) if isinstance(target_profile_path_value, str) and target_profile_path_value.strip() else resolve_target_profile_path(repo_root, None)
    loaded_target_profile = load_target_profile(target_profile_path)
    target_profile_summary = build_target_profile_summary(loaded_target_profile, target_profile_path)
    target_profile = runtime_target_profile(loaded_target_profile)

    signature = build_crash_signature(metrics.top_crash_lines)
    run_dir_str = str(selected_run_dir)
    report_path_str = str(report_path)
    artifact_path = str(signature.get("artifact_path") or snapshot.get("crash_artifact") or "") or None
    stale_fingerprint = str(snapshot.get("crash_fingerprint") or "") or None
    crash_index_path = repo_root / "fuzz-artifacts" / "crash_index.json"
    _remove_stale_crash_records_for_run(
        crash_index_path,
        run_dir=run_dir_str,
        report_path=report_path_str,
        artifact_path=artifact_path,
        stale_fingerprint=stale_fingerprint,
        new_fingerprint=str(signature.get("fingerprint") or ""),
    )
    crash_info = update_crash_index(
        crash_index_path,
        signature,
        run_dir=run_dir_str,
        report_path=report_path_str,
    )
    crash_info = enrich_crash_info_with_stage_info(crash_info, metrics.top_crash_lines, target_profile)
    outcome = str(snapshot.get("outcome") or "crash")
    artifact_event = classify_artifact_event(outcome, crash_info)

    automation_dir = repo_root / "fuzz-artifacts" / "automation"
    history_path = automation_dir / "run_history.json"
    history_entries = load_registry(history_path, {"entries": []}).get("entries")
    prior_history = []
    if isinstance(history_entries, list):
        for entry in history_entries:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("run_dir") or "") == run_dir_str or str(entry.get("report") or "") == report_path_str:
                continue
            prior_history.append(entry)
    current_history_entry = {
        "updated_at": snapshot.get("updated_at") or dt.datetime.now().isoformat(timespec="seconds"),
        "outcome": outcome,
        "cov": metrics.cov if metrics.cov is not None else snapshot.get("cov"),
        "ft": metrics.ft if metrics.ft is not None else snapshot.get("ft"),
        "exec_per_second": metrics.execs if metrics.execs is not None else snapshot.get("exec_per_second"),
        "crash_stage": crash_info.get("stage"),
        "crash_fingerprint": crash_info.get("fingerprint"),
        "policy_profile_severity": None,
    }
    policy_action = decide_policy_action(outcome, artifact_event, crash_info, target_profile, prior_history + [current_history_entry])

    updated_snapshot = dict(snapshot)
    updated_snapshot.update(
        {
            "updated_at": snapshot.get("updated_at") or dt.datetime.now().isoformat(timespec="seconds"),
            "run_dir": run_dir_str,
            "report": report_path_str,
            "cov": metrics.cov if metrics.cov is not None else snapshot.get("cov"),
            "ft": metrics.ft if metrics.ft is not None else snapshot.get("ft"),
            "corpus_units": metrics.corp_units if metrics.corp_units is not None else snapshot.get("corpus_units"),
            "corpus_size": metrics.corp_size if metrics.corp_size is not None else snapshot.get("corpus_size"),
            "exec_per_second": metrics.execs if metrics.execs is not None else snapshot.get("exec_per_second"),
            "rss": metrics.rss if metrics.rss is not None else snapshot.get("rss"),
            "crash_detected": metrics.crash,
            "timeout_detected": metrics.timeout,
            "crash_fingerprint": crash_info.get("fingerprint"),
            "crash_kind": crash_info.get("kind"),
            "crash_location": crash_info.get("location"),
            "crash_summary": crash_info.get("summary"),
            "crash_artifact": crash_info.get("artifact_path"),
            "crash_artifact_sha1": crash_info.get("artifact_sha1"),
            "crash_is_duplicate": crash_info.get("is_duplicate"),
            "crash_occurrence_count": crash_info.get("occurrence_count"),
            "crash_first_seen_run": crash_info.get("first_seen_run"),
            "crash_stage": crash_info.get("stage"),
            "crash_stage_class": crash_info.get("stage_class"),
            "crash_stage_depth_rank": crash_info.get("stage_depth_rank"),
            "crash_stage_confidence": crash_info.get("stage_confidence"),
            "crash_stage_match_source": crash_info.get("stage_match_source"),
            "crash_stage_reason": crash_info.get("stage_reason"),
            "artifact_category": artifact_event.get("category"),
            "artifact_reason": artifact_event.get("reason"),
            "policy_priority": policy_action.get("priority"),
            "policy_action_code": policy_action.get("action_code"),
            "policy_recommended_action": policy_action.get("recommended_action"),
            "policy_next_mode": policy_action.get("next_mode"),
            "policy_bucket": policy_action.get("bucket"),
            "policy_matched_triggers": policy_action.get("matched_triggers"),
            "policy_profile_severity": policy_action.get("profile_severity"),
            "policy_profile_labels": policy_action.get("profile_labels"),
            "rehydrated_at": dt.datetime.now().isoformat(timespec="seconds"),
            "rehydration_source": str(fuzz_log_path),
        }
    )
    if target_profile_summary:
        updated_snapshot.update(
            {
                "target_profile_name": target_profile_summary.get("name"),
                "target_profile_path": target_profile_summary.get("path"),
                "target_profile_project": target_profile_summary.get("project"),
                "target_profile_primary_mode": target_profile_summary.get("primary_mode"),
                "target_profile_primary_binary": target_profile_summary.get("primary_binary"),
                "target_profile_stage_count": target_profile_summary.get("stage_count"),
                "target_profile_load_status": target_profile_summary.get("load_status"),
                "target_profile_load_error": target_profile_summary.get("load_error"),
                "target_profile_load_error_detail": target_profile_summary.get("load_error_detail"),
                "target_profile_validation_status": target_profile_summary.get("validation_status"),
                "target_profile_validation_severity": target_profile_summary.get("validation_severity"),
                "target_profile_validation_codes": target_profile_summary.get("validation_codes"),
            }
        )

    write_status(status_path, updated_snapshot)
    current_status_path = repo_root / "fuzz-artifacts" / "current_status.json"
    current_status = load_registry(current_status_path, {})
    if not current_status or str(current_status.get("run_dir") or "") == run_dir_str:
        write_status(current_status_path, updated_snapshot)
    history_result = upsert_run_history_entry(automation_dir, updated_snapshot)
    updated_snapshot["history_appended"] = history_result.get("appended")
    write_status(status_path, updated_snapshot)
    if not current_status or str(current_status.get("run_dir") or "") == run_dir_str:
        write_status(current_status_path, updated_snapshot)
    report_rewritten = rewrite_rehydrated_report(
        report_path,
        updated_snapshot=updated_snapshot,
        metrics=metrics,
        crash_info=crash_info,
        artifact_event=artifact_event,
        policy_action=policy_action,
    )
    return {
        "rehydrated": True,
        "run_dir": run_dir_str,
        "status_path": str(status_path),
        "current_status_updated": (not current_status) or str(current_status.get("run_dir") or "") == run_dir_str,
        "history_replaced": history_result.get("replaced"),
        "report_rewritten": report_rewritten,
        "crash_fingerprint": updated_snapshot.get("crash_fingerprint"),
        "artifact_category": updated_snapshot.get("artifact_category"),
        "policy_action_code": updated_snapshot.get("policy_action_code"),
    }


def repair_run_history_entry(automation_dir: Path, snapshot: dict[str, object], *, max_entries: int = 200) -> dict[str, object]:
    path = automation_dir / "run_history.json"
    data = load_registry(path, {"entries": []})
    entries = data.setdefault("entries", [])
    entry = {
        "updated_at": snapshot.get("updated_at"),
        "outcome": snapshot.get("outcome"),
        "cov": snapshot.get("cov"),
        "ft": snapshot.get("ft"),
        "exec_per_second": snapshot.get("exec_per_second"),
        "corpus_units": snapshot.get("corpus_units"),
        "corpus_size": snapshot.get("corpus_size"),
        "seconds_since_progress": snapshot.get("seconds_since_progress"),
        "timeout_detected": snapshot.get("timeout_detected"),
        "crash_stage": snapshot.get("crash_stage"),
        "crash_fingerprint": snapshot.get("crash_fingerprint"),
        "policy_profile_severity": snapshot.get("policy_profile_severity"),
        "policy_action_code": snapshot.get("policy_action_code"),
        "policy_matched_triggers": snapshot.get("policy_matched_triggers"),
        "run_dir": snapshot.get("run_dir"),
        "report": snapshot.get("report"),
    }
    matched_index = None
    for index in range(len(entries) - 1, -1, -1):
        existing = entries[index]
        if not isinstance(existing, dict):
            continue
        if str(existing.get("run_dir") or "") == str(entry.get("run_dir") or "") and str(existing.get("report") or "") == str(entry.get("report") or ""):
            matched_index = index
            break
    if matched_index is None:
        entries.append(entry)
        updated = False
    else:
        entries[matched_index] = entry
        updated = True
    if len(entries) > max_entries:
        data["entries"] = entries[-max_entries:]
    save_registry(path, data)
    return {"path": str(path), "updated": updated, "count": len(data["entries"])}


def repair_latest_crash_state(repo_root: Path) -> dict[str, object]:
    current_status_path = repo_root / "fuzz-artifacts" / "current_status.json"
    crash_index_path = repo_root / "fuzz-artifacts" / "crash_index.json"
    automation_dir = repo_root / "fuzz-artifacts" / "automation"
    current_status = load_registry(current_status_path, {})
    run_dir_value = str(current_status.get("run_dir") or "")
    report_value = str(current_status.get("report") or "")
    if not run_dir_value:
        return {"repaired": False, "reason": "missing-run-dir"}
    run_dir = Path(run_dir_value)
    fuzz_log_path = run_dir / "fuzz.log"
    if not fuzz_log_path.exists():
        return {"repaired": False, "reason": "missing-fuzz-log", "run_dir": str(run_dir)}

    metrics = Metrics()
    for raw_line in fuzz_log_path.read_text(encoding="utf-8").splitlines():
        metrics.update_from_line(raw_line)
    if not metrics.top_crash_lines:
        return {"repaired": False, "reason": "no-crash-signature-in-log", "run_dir": str(run_dir)}

    signature = build_crash_signature(metrics.top_crash_lines)
    profile_path_value = current_status.get("target_profile_path")
    profile_path = Path(str(profile_path_value)) if profile_path_value else None
    target_profile = load_target_profile(profile_path)
    crash_info = repair_crash_index_entry(
        crash_index_path,
        previous_fingerprint=str(current_status.get("crash_fingerprint") or "") or None,
        signature=signature,
        run_dir=str(run_dir),
        report_path=report_value,
    )
    crash_info = enrich_crash_info_with_stage_info(crash_info, metrics.top_crash_lines, target_profile)
    artifact_event = classify_artifact_event(str(current_status.get("outcome") or "crash"), crash_info)

    history_path = automation_dir / "run_history.json"
    history_data = load_registry(history_path, {"entries": []})
    history_entries = history_data.get("entries") if isinstance(history_data.get("entries"), list) else []
    history_without_current = [
        entry
        for entry in history_entries
        if isinstance(entry, dict)
        and not (
            str(entry.get("run_dir") or "") == str(run_dir)
            and str(entry.get("report") or "") == report_value
        )
    ]
    current_history_entry = {
        "updated_at": current_status.get("updated_at"),
        "outcome": current_status.get("outcome"),
        "cov": current_status.get("cov"),
        "ft": current_status.get("ft"),
        "exec_per_second": current_status.get("exec_per_second"),
        "corpus_units": current_status.get("corpus_units"),
        "corpus_size": current_status.get("corpus_size"),
        "seconds_since_progress": current_status.get("seconds_since_progress"),
        "timeout_detected": current_status.get("timeout_detected"),
        "crash_stage": crash_info.get("stage") if crash_info else None,
        "crash_fingerprint": crash_info.get("fingerprint") if crash_info else None,
        "policy_profile_severity": None,
        "policy_action_code": None,
        "policy_matched_triggers": [],
        "run_dir": str(run_dir),
        "report": report_value,
    }
    policy_action = decide_policy_action(
        str(current_status.get("outcome") or "crash"),
        artifact_event,
        crash_info,
        target_profile,
        history_without_current + [current_history_entry],
    )
    current_history_entry["policy_profile_severity"] = policy_action.get("profile_severity")
    current_history_entry["policy_action_code"] = policy_action.get("action_code")
    current_history_entry["policy_matched_triggers"] = policy_action.get("matched_triggers")

    repaired_snapshot = dict(current_status)
    repaired_snapshot.update(
        {
            "crash_fingerprint": crash_info.get("fingerprint"),
            "crash_kind": crash_info.get("kind"),
            "crash_location": crash_info.get("location"),
            "crash_summary": crash_info.get("summary"),
            "crash_artifact": crash_info.get("artifact_path"),
            "crash_artifact_sha1": crash_info.get("artifact_sha1"),
            "crash_is_duplicate": crash_info.get("is_duplicate"),
            "crash_occurrence_count": crash_info.get("occurrence_count"),
            "crash_first_seen_run": crash_info.get("first_seen_run"),
            "crash_stage": crash_info.get("stage"),
            "crash_stage_class": crash_info.get("stage_class"),
            "crash_stage_depth_rank": crash_info.get("stage_depth_rank"),
            "crash_stage_confidence": crash_info.get("stage_confidence"),
            "crash_stage_match_source": crash_info.get("stage_match_source"),
            "crash_stage_reason": crash_info.get("stage_reason"),
            "artifact_category": artifact_event.get("category"),
            "artifact_reason": artifact_event.get("reason"),
            "policy_priority": policy_action.get("priority"),
            "policy_action_code": policy_action.get("action_code"),
            "policy_recommended_action": policy_action.get("recommended_action"),
            "policy_next_mode": policy_action.get("next_mode"),
            "policy_bucket": policy_action.get("bucket"),
            "policy_matched_triggers": policy_action.get("matched_triggers"),
            "policy_profile_severity": policy_action.get("profile_severity"),
            "policy_profile_labels": policy_action.get("profile_labels"),
        }
    )
    write_status(current_status_path, repaired_snapshot)
    run_status_path = run_dir / "status.json"
    if run_status_path.exists():
        write_status(run_status_path, repaired_snapshot)
    history_result = repair_run_history_entry(automation_dir, repaired_snapshot)
    repaired_snapshot["history_appended"] = 0
    write_status(current_status_path, repaired_snapshot)
    if run_status_path.exists():
        write_status(run_status_path, repaired_snapshot)
    return {
        "repaired": True,
        "run_dir": str(run_dir),
        "report": report_value,
        "previous_fingerprint": current_status.get("crash_fingerprint"),
        "new_fingerprint": crash_info.get("fingerprint"),
        "artifact_category": artifact_event.get("category"),
        "artifact_reason": artifact_event.get("reason"),
        "policy_action_code": policy_action.get("action_code"),
        "policy_next_mode": policy_action.get("next_mode"),
        "history_updated": history_result.get("updated"),
        "crash_index_path": str(crash_index_path),
        "current_status_path": str(current_status_path),
    }



def evaluate_history_triggers(history: list[dict[str, object]], profile: dict[str, object] | None) -> dict[str, object]:
    result = {
        "matched_triggers": [],
        "override_action_code": None,
        "override_priority": None,
        "override_bucket": None,
        "dominant_stage": None,
        "semantic_summary": compute_semantic_history_summary(history),
    }
    if not isinstance(profile, dict):
        return result

    triggers = profile.get("triggers") if isinstance(profile.get("triggers"), dict) else {}

    crash_entries = [entry for entry in history if entry.get("outcome") == "crash"]
    semantic_summary = result["semantic_summary"]
    shallow_trigger = triggers.get("shallow_crash_dominance") if isinstance(triggers.get("shallow_crash_dominance"), dict) else None
    if shallow_trigger and shallow_trigger.get("enabled") and crash_entries:
        condition = shallow_trigger.get("condition") if isinstance(shallow_trigger.get("condition"), dict) else {}
        dominant_stage = str(condition.get("dominant_stage") or "")
        min_ratio = float(condition.get("min_ratio", 1.0) or 1.0)
        min_families = int(condition.get("min_crash_families", 0) or 0)
        stage_count = sum(1 for entry in crash_entries if entry.get("crash_stage") == dominant_stage)
        unique_families = {entry.get("crash_fingerprint") for entry in crash_entries if entry.get("crash_fingerprint")}
        ratio = stage_count / len(crash_entries) if crash_entries else 0.0
        if len(unique_families) >= min_families and ratio >= min_ratio:
            result["matched_triggers"].append("shallow_crash_dominance")
            result["dominant_stage"] = dominant_stage
            result["override_action_code"] = str(shallow_trigger.get("action") or "")
            result["override_priority"] = "high"
            result["override_bucket"] = "coverage"

    plateau_trigger = triggers.get("coverage_plateau") if isinstance(triggers.get("coverage_plateau"), dict) else None
    if plateau_trigger and plateau_trigger.get("enabled") and len(history) >= 4:
        condition = plateau_trigger.get("condition") if isinstance(plateau_trigger.get("condition"), dict) else {}
        plateau_minutes = int(condition.get("plateau_minutes", 0) or 0)
        min_execs = int(condition.get("min_execs_per_sec", 0) or 0)
        max_new_high_value = int(condition.get("max_new_high_value_crashes", 0) or 0)
        recent = sorted(
            [entry for entry in history if parse_iso_timestamp(str(entry.get("updated_at") or "")) is not None],
            key=lambda item: parse_iso_timestamp(str(item.get("updated_at") or "")) or dt.datetime.min,
        )
        if len(recent) >= 4:
            window = recent[-4:]
            first_ts = parse_iso_timestamp(str(window[0].get("updated_at") or ""))
            last_ts = parse_iso_timestamp(str(window[-1].get("updated_at") or ""))
            if first_ts and last_ts:
                elapsed_minutes = (last_ts - first_ts).total_seconds() / 60.0
                cov_values = {entry.get("cov") for entry in window}
                execs_ok = all(int(entry.get("exec_per_second") or 0) >= min_execs for entry in window)
                high_value_new = sum(1 for entry in window if str(entry.get("policy_profile_severity") or "") == "critical")
                if elapsed_minutes >= plateau_minutes and len(cov_values) == 1 and execs_ok and high_value_new <= max_new_high_value:
                    result["matched_triggers"].append("coverage_plateau")
                    if result["override_action_code"] is None:
                        result["override_action_code"] = str(plateau_trigger.get("action") or "")
                        result["override_priority"] = "medium"
                        result["override_bucket"] = "coverage"

    timeout_trigger = triggers.get("timeout_surge") if isinstance(triggers.get("timeout_surge"), dict) else None
    if timeout_trigger and timeout_trigger.get("enabled") and len(history) >= 4:
        condition = timeout_trigger.get("condition") if isinstance(timeout_trigger.get("condition"), dict) else {}
        min_timeout_rate = float(condition.get("min_timeout_rate", 1.0) or 1.0)
        min_duration_minutes = int(condition.get("min_duration_minutes", 0) or 0)
        recent = sorted(
            [entry for entry in history if parse_iso_timestamp(str(entry.get("updated_at") or "")) is not None and entry.get("timeout_detected") is not None],
            key=lambda item: parse_iso_timestamp(str(item.get("updated_at") or "")) or dt.datetime.min,
        )
        if len(recent) >= 4:
            window = recent[-4:]
            first_ts = parse_iso_timestamp(str(window[0].get("updated_at") or ""))
            last_ts = parse_iso_timestamp(str(window[-1].get("updated_at") or ""))
            if first_ts and last_ts:
                elapsed_minutes = (last_ts - first_ts).total_seconds() / 60.0
                timeout_rate = sum(1 for entry in window if bool(entry.get("timeout_detected"))) / len(window)
                if elapsed_minutes >= min_duration_minutes and timeout_rate >= min_timeout_rate:
                    result["matched_triggers"].append("timeout_surge")
                    if result["override_action_code"] is None:
                        result["override_action_code"] = str(timeout_trigger.get("action") or "")
                        result["override_priority"] = "high"
                        result["override_bucket"] = "coverage"

    corpus_trigger = triggers.get("corpus_bloat_low_gain") if isinstance(triggers.get("corpus_bloat_low_gain"), dict) else None
    if corpus_trigger and corpus_trigger.get("enabled") and len(history) >= 4:
        condition = corpus_trigger.get("condition") if isinstance(corpus_trigger.get("condition"), dict) else {}
        min_corpus_growth = int(condition.get("min_corpus_growth", 0) or 0)
        max_coverage_gain_percent = float(condition.get("max_coverage_gain_percent", 0.0) or 0.0)
        recent = sorted(
            [entry for entry in history if parse_iso_timestamp(str(entry.get("updated_at") or "")) is not None and entry.get("corpus_units") is not None and entry.get("cov") is not None],
            key=lambda item: parse_iso_timestamp(str(item.get("updated_at") or "")) or dt.datetime.min,
        )
        if len(recent) >= 4:
            window = recent[-4:]
            corpus_growth = int(window[-1].get("corpus_units") or 0) - int(window[0].get("corpus_units") or 0)
            cov_start = float(window[0].get("cov") or 0.0)
            cov_end = float(window[-1].get("cov") or 0.0)
            coverage_gain_percent = cov_end - cov_start
            if corpus_growth >= min_corpus_growth and coverage_gain_percent <= max_coverage_gain_percent:
                result["matched_triggers"].append("corpus_bloat_low_gain")
                if result["override_action_code"] is None:
                    result["override_action_code"] = str(corpus_trigger.get("action") or "")
                    result["override_priority"] = "medium"
                    result["override_bucket"] = "coverage"

    stability_trigger = triggers.get("stability_drop") if isinstance(triggers.get("stability_drop"), dict) else None
    if stability_trigger and stability_trigger.get("enabled") and len(crash_entries) >= 4:
        duplicate_ratio = 0.0
        fingerprints = [entry.get("crash_fingerprint") for entry in crash_entries if entry.get("crash_fingerprint")]
        if fingerprints:
            duplicate_ratio = 1.0 - (len(set(fingerprints)) / len(fingerprints))
        dominant_stage = semantic_summary.get("dominant_stage")
        shallow_ratio = float(semantic_summary.get("shallow_ratio") or 0.0)
        if duplicate_ratio >= 0.40 and dominant_stage == "parse-main-header" and shallow_ratio >= 0.75:
            result["matched_triggers"].append("stability_drop")
            if result["override_action_code"] is None:
                result["override_action_code"] = str(stability_trigger.get("action") or "")
                result["override_priority"] = "high"
                result["override_bucket"] = "stability"

    return result


def extract_smoke_failure_input_path(smoke_output: str, repo_root: Path | None = None) -> str | None:
    matches = SMOKE_INPUT_RE.findall(smoke_output)
    if not matches:
        return None
    path = matches[-1]
    if repo_root is not None:
        path = path.replace("${repo_root}", str(repo_root))
    return path


def copy_seed_into_bucket(source_path: str | Path | None, bucket_dir: Path) -> Path | None:
    if not source_path:
        return None
    src = Path(source_path)
    if not src.exists() or not src.is_file():
        return None
    bucket_dir.mkdir(parents=True, exist_ok=True)
    dst = bucket_dir / src.name
    if src.resolve() == dst.resolve():
        return dst
    shutil.copy2(src, dst)
    return dst


def _resolve_profile_seed_example_path(
    repo_root: Path,
    *,
    example_name: str,
    seed_root_dirs: dict[str, object],
) -> Path | None:
    candidate_dirs: list[Path] = []
    for value in seed_root_dirs.values():
        if not isinstance(value, str) or not value:
            continue
        candidate_dir = Path(value)
        if not candidate_dir.is_absolute():
            candidate_dir = repo_root / candidate_dir
        if candidate_dir not in candidate_dirs:
            candidate_dirs.append(candidate_dir)
    candidate_dirs.extend(
        [
            repo_root / "fuzz" / "corpus" / "regression",
            repo_root / "fuzz" / "corpus" / "triage",
            repo_root / "fuzz" / "corpus" / "valid",
            repo_root / "conformance_data",
        ]
    )
    for candidate_dir in candidate_dirs:
        candidate = candidate_dir / example_name
        if candidate.exists() and candidate.is_file():
            return candidate
    for candidate in repo_root.rglob(example_name):
        if candidate.is_file():
            return candidate
    return None


def _collect_preferred_coverage_seed_paths(repo_root: Path) -> list[Path]:
    profile_path = resolve_target_profile_path(repo_root, None)
    profile = load_target_profile(profile_path)
    if not isinstance(profile, dict):
        return []
    target = profile.get("target") if isinstance(profile.get("target"), dict) else {}
    current_campaign = target.get("current_campaign") if isinstance(target.get("current_campaign"), dict) else {}
    primary_mode = str(current_campaign.get("primary_mode") or "")
    if not primary_mode:
        return []
    seeds = profile.get("seeds") if isinstance(profile.get("seeds"), dict) else {}
    seed_root_dirs = seeds.get("root_dirs") if isinstance(seeds.get("root_dirs"), dict) else {}
    classes = seeds.get("classes") if isinstance(seeds.get("classes"), dict) else {}
    preferred_paths: list[Path] = []
    seen_names: set[str] = set()
    for class_config in classes.values():
        if not isinstance(class_config, dict):
            continue
        preferred_modes = [str(item) for item in class_config.get("preferred_modes", []) if isinstance(item, str) and item]
        if preferred_modes and primary_mode not in preferred_modes:
            continue
        for example in class_config.get("examples", []):
            if not isinstance(example, str) or not example or example in seen_names:
                continue
            resolved = _resolve_profile_seed_example_path(
                repo_root,
                example_name=example,
                seed_root_dirs=seed_root_dirs,
            )
            if resolved is None:
                continue
            preferred_paths.append(resolved)
            seen_names.add(example)
    return preferred_paths


def _move_coverage_seed_to_quarantine(seed_path: Path, quarantine_dir: Path) -> Path:
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    destination = quarantine_dir / seed_path.name
    seed_sha1 = _sha1_file(seed_path)
    if destination.exists():
        if seed_sha1 and seed_sha1 == _sha1_file(destination):
            seed_path.unlink()
            return destination
        suffix = seed_path.suffix
        stem = seed_path.stem
        destination = quarantine_dir / f"{stem}-{(seed_sha1 or 'copy')[:8]}{suffix}"
    shutil.move(str(seed_path), str(destination))
    return destination


def sync_preferred_coverage_corpus(repo_root: Path) -> dict[str, object]:
    preferred_seed_paths = _collect_preferred_coverage_seed_paths(repo_root)
    if not preferred_seed_paths:
        return {"copied": 0, "quarantined": 0, "preferred_names": [], "quarantine_paths": []}

    coverage_dir = repo_root / "fuzz" / "corpus" / "coverage"
    quarantine_dir = repo_root / "fuzz" / "corpus" / "coverage-quarantine"
    coverage_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    preferred_names: set[str] = set()
    for source_path in preferred_seed_paths:
        destination = coverage_dir / source_path.name
        if not destination.exists() or _sha1_file(destination) != _sha1_file(source_path):
            copied += 1
        synced_path = copy_seed_into_bucket(source_path, coverage_dir)
        if synced_path is not None:
            preferred_names.add(synced_path.name)

    if not preferred_names:
        return {"copied": copied, "quarantined": 0, "preferred_names": [], "quarantine_paths": []}

    quarantine_paths: list[str] = []
    for candidate in sorted(coverage_dir.iterdir()):
        if not candidate.is_file() or candidate.name in preferred_names:
            continue
        quarantine_path = _move_coverage_seed_to_quarantine(candidate, quarantine_dir)
        quarantine_paths.append(str(quarantine_path))

    return {
        "copied": copied,
        "quarantined": len(quarantine_paths),
        "preferred_names": sorted(preferred_names),
        "quarantine_paths": quarantine_paths,
    }


def sync_corpus_from_registries(automation_dir: Path, *, repo_root: Path) -> dict[str, object]:
    updated: list[str] = []

    known_bad_path = automation_dir / "known_bad.json"
    known_bad = load_registry(known_bad_path, {"fingerprints": {}})
    known_bad_synced = False
    for record in known_bad.get("fingerprints", {}).values():
        synced_path = copy_seed_into_bucket(record.get("artifact_path"), repo_root / "fuzz" / "corpus" / "known-bad")
        if synced_path is not None:
            record["bucket_path"] = str(synced_path)
            known_bad_synced = True
    if known_bad_synced:
        save_registry(known_bad_path, known_bad)
        updated.append("known_bad")

    regression_path = automation_dir / "regression_candidates.json"
    regression = load_registry(regression_path, {"entries": []})
    regression_synced = False
    for entry in regression.get("entries", []):
        seed_path = entry.get("seed_path")
        if (not seed_path or "${repo_root}" in str(seed_path)) and entry.get("report_path"):
            smoke_log_path = Path(str(entry["report_path"])).with_name("smoke.log")
            if smoke_log_path.exists():
                smoke_output = smoke_log_path.read_text(encoding="utf-8", errors="replace")
                repaired_seed_path = extract_smoke_failure_input_path(smoke_output, repo_root=repo_root)
                if repaired_seed_path:
                    entry["seed_path"] = repaired_seed_path
                    seed_path = repaired_seed_path
        synced_path = copy_seed_into_bucket(seed_path, repo_root / "fuzz" / "corpus" / "regression")
        if synced_path is not None:
            entry["bucket_path"] = str(synced_path)
            regression_synced = True
    if regression_synced:
        save_registry(regression_path, regression)
        updated.append("regression")

    coverage_sync = sync_preferred_coverage_corpus(repo_root)
    if int(coverage_sync.get("copied") or 0) > 0:
        updated.append("coverage")
    if int(coverage_sync.get("quarantined") or 0) > 0:
        updated.append("coverage_quarantine")

    return {"updated": updated}


def should_trigger_regression(outcome: str, policy_action: dict[str, str | None]) -> bool:
    action_code = policy_action.get("action_code")
    return action_code in {
        "fix-build-before-fuzzing",
        "promote-seed-to-regression-and-triage",
        "continue_and_prioritize_triage",
        "high_priority_alert",
    }


def regression_trigger_priority(trigger_reason: str) -> int:
    if trigger_reason == "fix-build-before-fuzzing":
        return 100
    if trigger_reason == "high_priority_alert":
        return 95
    if trigger_reason == "continue_and_prioritize_triage":
        return 90
    if trigger_reason == "promote-seed-to-regression-and-triage":
        return 80
    return 50


def followup_trigger_command(trigger_reason: str) -> list[str]:
    if trigger_reason in {"continue_and_prioritize_triage", "high_priority_alert"}:
        return ["bash", "scripts/run-fuzz-mode.sh", "triage"]
    return ["bash", "scripts/run-fuzz-mode.sh", "regression"]


def regression_trigger_dedup_key(trigger_reason: str, seed_path: str | None = None) -> str:
    if trigger_reason == "promote-seed-to-regression-and-triage" and seed_path:
        return f"{trigger_reason}:{seed_path}"
    return trigger_reason


def sort_regression_trigger_entries(entries: list[dict[str, object]]) -> list[dict[str, object]]:
    entries.sort(
        key=lambda item: (
            -int(item.get("priority", 0)),
            str(item.get("first_seen_run", item.get("run_dir", ""))),
        )
    )
    for index, entry in enumerate(entries, start=1):
        entry["queue_rank"] = index
    return entries


def normalize_regression_triggers(automation_dir: Path, *, repo_root: Path) -> dict[str, object]:
    path = automation_dir / "regression_triggers.json"
    data = load_registry(path, {"entries": []})
    entries = data.setdefault("entries", [])
    normalized: list[dict[str, object]] = []
    updated_count = 0

    for entry in entries:
        trigger_reason = str(entry.get("trigger_reason", ""))
        seed_path = entry.get("seed_path")
        if (not seed_path or "${repo_root}" in str(seed_path)) and entry.get("report_path") and trigger_reason == "promote-seed-to-regression-and-triage":
            smoke_log_path = Path(str(entry["report_path"])).with_name("smoke.log")
            if smoke_log_path.exists():
                smoke_output = smoke_log_path.read_text(encoding="utf-8", errors="replace")
                repaired_seed_path = extract_smoke_failure_input_path(smoke_output, repo_root=repo_root)
                if repaired_seed_path:
                    entry["seed_path"] = repaired_seed_path
                    seed_path = repaired_seed_path
                    updated_count += 1
        entry.setdefault("priority", regression_trigger_priority(trigger_reason))
        entry.setdefault("occurrence_count", 1)
        entry.setdefault("first_seen_run", entry.get("run_dir"))
        entry.setdefault("first_seen_report", entry.get("report_path"))
        entry.setdefault("last_seen_run", entry.get("run_dir"))
        entry.setdefault("last_seen_report", entry.get("report_path"))
        dedup_key = regression_trigger_dedup_key(trigger_reason, seed_path)
        if entry.get("dedup_key") != dedup_key:
            entry["dedup_key"] = dedup_key
            updated_count += 1

        existing = next((item for item in normalized if item.get("dedup_key") == dedup_key), None)
        if existing is None:
            normalized.append(entry)
            continue
        existing["occurrence_count"] = int(existing.get("occurrence_count", 1)) + int(entry.get("occurrence_count", 1))
        existing["last_seen_run"] = entry.get("last_seen_run", entry.get("run_dir"))
        existing["last_seen_report"] = entry.get("last_seen_report", entry.get("report_path"))
        if seed_path:
            existing["seed_path"] = seed_path
        updated_count += 1

    sort_regression_trigger_entries(normalized)
    data["entries"] = normalized
    save_registry(path, data)
    return {"updated_count": updated_count, "path": str(path), "entries": len(normalized)}


def record_regression_trigger(
    automation_dir: Path,
    *,
    run_dir: str,
    report_path: str,
    trigger_reason: str,
    command: list[str],
    seed_path: str | None = None,
) -> dict[str, object]:
    path = automation_dir / "regression_triggers.json"
    data = load_registry(path, {"entries": []})
    entries = data.setdefault("entries", [])
    dedup_key = regression_trigger_dedup_key(trigger_reason, seed_path)
    existing = next((item for item in entries if item.get("dedup_key") == dedup_key), None)
    if existing is not None:
        existing["last_seen_run"] = run_dir
        existing["last_seen_report"] = report_path
        existing["occurrence_count"] = int(existing.get("occurrence_count", 1)) + 1
        existing["status"] = "recorded"
        if seed_path:
            existing["seed_path"] = seed_path
        sort_regression_trigger_entries(entries)
        save_registry(path, data)
        return {**existing, "path": str(path)}

    entry = {
        "key": f"{trigger_reason}:{run_dir}",
        "dedup_key": dedup_key,
        "run_dir": run_dir,
        "report_path": report_path,
        "last_seen_run": run_dir,
        "last_seen_report": report_path,
        "first_seen_run": run_dir,
        "first_seen_report": report_path,
        "trigger_reason": trigger_reason,
        "command": command,
        "priority": regression_trigger_priority(trigger_reason),
        "status": "recorded",
        "occurrence_count": 1,
        "seed_path": seed_path,
    }
    entries.append(entry)
    sort_regression_trigger_entries(entries)
    save_registry(path, data)
    return {**entry, "path": str(path)}


def execute_regression_trigger(
    automation_dir: Path,
    *,
    repo_root: Path,
    trigger: dict[str, object],
    current_mode: str | None = None,
) -> dict[str, object]:
    normalize_regression_triggers(automation_dir, repo_root=repo_root)
    path = automation_dir / "regression_triggers.json"
    data = load_registry(path, {"entries": []})
    trigger_key = trigger.get("key")
    entries = data.setdefault("entries", [])
    entry = next((item for item in entries if item.get("key") == trigger_key), None)
    if entry is None:
        entry = dict(trigger)
        entries.append(entry)

    command = [str(part) for part in trigger.get("command", [])]
    target_mode = command[-1] if command else None
    if current_mode and target_mode and current_mode == target_mode:
        entry["status"] = f"skipped-already-in-{current_mode}"
        sort_regression_trigger_entries(entries)
        save_registry(path, data)
        return {**entry, "path": str(path)}

    exit_code, output = run_quiet(command, repo_root)
    entry["status"] = "completed" if exit_code == 0 else "failed"
    entry["exit_code"] = exit_code
    entry["completed_at"] = dt.datetime.now().isoformat(timespec="seconds")
    entry["output_preview"] = output[-1000:]
    sort_regression_trigger_entries(entries)
    save_registry(path, data)
    return {**entry, "path": str(path)}


def execute_next_regression_trigger(
    automation_dir: Path,
    *,
    repo_root: Path,
    current_mode: str | None = None,
) -> dict[str, object] | None:
    normalize_regression_triggers(automation_dir, repo_root=repo_root)
    path = automation_dir / "regression_triggers.json"
    data = load_registry(path, {"entries": []})
    entries = data.setdefault("entries", [])
    sort_regression_trigger_entries(entries)
    next_trigger = next((entry for entry in entries if entry.get("status") == "recorded"), None)
    save_registry(path, data)
    if next_trigger is None:
        return None
    return execute_regression_trigger(
        automation_dir,
        repo_root=repo_root,
        trigger=next_trigger,
        current_mode=current_mode,
    )


def apply_policy_action(
    automation_dir: Path,
    *,
    run_dir: str,
    report_path: str,
    outcome: str,
    artifact_event: dict[str, str | None],
    policy_action: dict[str, str | None],
    crash_info: dict[str, object] | None,
    repo_root: Path | None = None,
    current_mode: str | None = None,
) -> dict[str, object]:
    updated: list[str] = []
    regression_trigger: dict[str, object] | None = None

    policy_log_path = automation_dir / "policy_actions.json"
    policy_log = load_registry(policy_log_path, {"entries": []})
    policy_log.setdefault("entries", []).append(
        {
            "run_dir": run_dir,
            "report_path": report_path,
            "outcome": outcome,
            "artifact_category": artifact_event.get("category"),
            "artifact_reason": artifact_event.get("reason"),
            "policy_action_code": policy_action.get("action_code"),
            "policy_priority": policy_action.get("priority"),
            "policy_next_mode": policy_action.get("next_mode"),
            "policy_bucket": policy_action.get("bucket"),
            "crash_fingerprint": crash_info.get("fingerprint") if crash_info else None,
        }
    )
    save_registry(policy_log_path, policy_log)
    updated.append("policy_log")

    action_code = policy_action.get("action_code")
    if action_code in {"record-duplicate-crash", "review_duplicate_crash_replay"} and crash_info and crash_info.get("fingerprint"):
        known_bad_path = automation_dir / "known_bad.json"
        known_bad = load_registry(known_bad_path, {"fingerprints": {}})
        fingerprints = known_bad.setdefault("fingerprints", {})
        fp = str(crash_info["fingerprint"])
        first_seen_run = crash_info.get("first_seen_run") or run_dir
        occurrence_count = int(crash_info.get("occurrence_count") or 1)
        if fp not in fingerprints:
            fingerprints[fp] = {
                "location": crash_info.get("location"),
                "summary": crash_info.get("summary"),
                "artifact_path": crash_info.get("artifact_path"),
                "first_seen_run": first_seen_run,
                "last_seen_run": run_dir,
                "occurrence_count": occurrence_count,
            }
        else:
            fingerprints[fp]["first_seen_run"] = fingerprints[fp].get("first_seen_run") or first_seen_run
            fingerprints[fp]["last_seen_run"] = run_dir
            fingerprints[fp]["occurrence_count"] = max(int(fingerprints[fp].get("occurrence_count") or 0), occurrence_count)
            if crash_info.get("artifact_path"):
                fingerprints[fp]["artifact_path"] = crash_info.get("artifact_path")
        save_registry(known_bad_path, known_bad)
        updated.append("known_bad")

    if action_code == "review_duplicate_crash_replay":
        refiner = record_refiner_entry(
            automation_dir,
            registry_name="duplicate_crash_reviews.json",
            unique_key="key",
            entry={
                "key": f"{action_code}:{crash_info.get('fingerprint') if crash_info else run_dir}",
                "action_code": action_code,
                "run_dir": run_dir,
                "report_path": report_path,
                "outcome": outcome,
                "artifact_category": artifact_event.get("category"),
                "recommended_action": policy_action.get("recommended_action"),
                "crash_fingerprint": crash_info.get("fingerprint") if crash_info else None,
                "crash_location": crash_info.get("location") if crash_info else None,
                "crash_summary": crash_info.get("summary") if crash_info else None,
                "occurrence_count": int(crash_info.get("occurrence_count") or 1) if crash_info else 1,
                "first_seen_run": crash_info.get("first_seen_run") if crash_info else None,
                "first_seen_report_path": crash_info.get("first_seen_report") if crash_info else None,
                "last_seen_run": crash_info.get("last_seen_run") if crash_info else run_dir,
                "latest_artifact_path": crash_info.get("artifact_path") if crash_info else None,
                "first_artifact_path": crash_info.get("first_artifact_path") if crash_info else None,
                "artifact_paths": crash_info.get("artifacts") if crash_info else None,
            },
            merge_existing=True,
        )
        if refiner.get("created") or refiner.get("updated"):
            updated.append("duplicate_crash_reviews")

    if action_code == "shift_weight_to_deeper_harness":
        refiner = record_refiner_entry(
            automation_dir,
            registry_name="mode_refinements.json",
            unique_key="key",
            entry={
                "key": f"{action_code}:{run_dir}",
                "action_code": action_code,
                "run_dir": run_dir,
                "report_path": report_path,
                "outcome": outcome,
                "current_bucket": policy_action.get("bucket"),
                "recommended_action": policy_action.get("recommended_action"),
                "crash_fingerprint": crash_info.get("fingerprint") if crash_info else None,
                "dominant_stage": policy_action.get("history_dominant_stage"),
            },
        )
        if refiner.get("created"):
            updated.append("mode_refinements")

    if action_code == "split_slow_lane":
        refiner = record_refiner_entry(
            automation_dir,
            registry_name="slow_lane_candidates.json",
            unique_key="key",
            entry={
                "key": f"{action_code}:{run_dir}",
                "action_code": action_code,
                "run_dir": run_dir,
                "report_path": report_path,
                "outcome": outcome,
                "artifact_category": artifact_event.get("category"),
                "recommended_action": policy_action.get("recommended_action"),
                "crash_fingerprint": crash_info.get("fingerprint") if crash_info else None,
            },
        )
        if refiner.get("created"):
            updated.append("slow_lane_candidates")

    if action_code == "minimize_and_reseed":
        refiner = record_refiner_entry(
            automation_dir,
            registry_name="corpus_refinements.json",
            unique_key="key",
            entry={
                "key": f"{action_code}:{run_dir}",
                "action_code": action_code,
                "run_dir": run_dir,
                "report_path": report_path,
                "outcome": outcome,
                "recommended_action": policy_action.get("recommended_action"),
                "policy_bucket": policy_action.get("bucket"),
            },
        )
        if refiner.get("created"):
            updated.append("corpus_refinements")

    if action_code == "halt_and_review_harness":
        refiner = record_refiner_entry(
            automation_dir,
            registry_name="harness_review_queue.json",
            unique_key="key",
            entry={
                "key": f"{action_code}:{run_dir}",
                "action_code": action_code,
                "run_dir": run_dir,
                "report_path": report_path,
                "outcome": outcome,
                "recommended_action": policy_action.get("recommended_action"),
                "history_dominant_stage": policy_action.get("history_dominant_stage"),
            },
        )
        if refiner.get("created"):
            updated.append("harness_reviews")

    if action_code == "promote-seed-to-regression-and-triage":
        regression_path = automation_dir / "regression_candidates.json"
        regression = load_registry(regression_path, {"entries": []})
        smoke_log_path = Path(report_path).with_name("smoke.log")
        smoke_output = smoke_log_path.read_text(encoding="utf-8", errors="replace") if smoke_log_path.exists() else ""
        seed_path = extract_smoke_failure_input_path(smoke_output, repo_root=repo_root)
        candidate = {
            "key": f"{outcome}:{run_dir}",
            "run_dir": run_dir,
            "report_path": report_path,
            "category": artifact_event.get("category"),
            "reason": artifact_event.get("reason"),
            "policy_action_code": action_code,
            "seed_path": seed_path,
        }
        if append_unique_entry(regression.setdefault("entries", []), candidate, "key"):
            save_registry(regression_path, regression)
            updated.append("regression_candidates")
        else:
            save_registry(regression_path, regression)

    if should_trigger_regression(outcome, policy_action):
        trigger_seed_path = None
        if action_code == "promote-seed-to-regression-and-triage":
            smoke_log_path = Path(report_path).with_name("smoke.log")
            smoke_output = smoke_log_path.read_text(encoding="utf-8", errors="replace") if smoke_log_path.exists() else ""
            trigger_seed_path = extract_smoke_failure_input_path(smoke_output, repo_root=repo_root)
        regression_trigger = record_regression_trigger(
            automation_dir,
            run_dir=run_dir,
            report_path=report_path,
            trigger_reason=action_code or outcome,
            command=followup_trigger_command(str(action_code or outcome)),
            seed_path=trigger_seed_path,
        )
        updated.append("regression_trigger")
        if repo_root is not None:
            regression_trigger = execute_next_regression_trigger(
                automation_dir,
                repo_root=repo_root,
                current_mode=current_mode,
            )
            if regression_trigger is not None:
                updated.append("regression_auto_run")

    if repo_root is not None:
        corpus_sync = sync_corpus_from_registries(automation_dir, repo_root=repo_root)
        updated.extend(item for item in corpus_sync.get("updated", []) if item not in updated)

    return {"updated": updated, "regression_trigger": regression_trigger}


def format_progress_message(snapshot: dict[str, object], *, target_label: str = "OpenHTJ2K fuzz") -> str:
    return "\n".join(
        [
            f"[{target_label}] PROGRESS",
            f"duration: {snapshot['duration']}",
            f"last progress: {snapshot['since_progress']} ago",
            f"cov: {snapshot['cov']} ft: {snapshot['ft']} corp: {snapshot['corpus_units']}",
            f"exec/s: {snapshot['exec_per_second']} rss: {snapshot['rss']}",
            f"status: {snapshot['outcome']}",
            f"run: {snapshot['run_dir']}",
        ]
    )


def run_quiet(cmd: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode, proc.stdout


def send_discord(message: str) -> dict[str, object]:
    message = message[:1900]
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if webhook:
        payload = json.dumps({"content": message}).encode()
        req = urllib.request.Request(webhook, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as response:
            response.read()
        return {"status": "sent", "transport": "webhook", "message_length": len(message)}

    channel_id = os.environ.get("DISCORD_PROGRESS_CHANNEL_ID") or os.environ.get("DISCORD_CHANNEL_ID")
    bot_token = os.environ.get("DISCORD_BOT_TOKEN") or os.environ.get("DISCORD_TOKEN")
    if not channel_id or not bot_token:
        print(
            "[notify] Set DISCORD_WEBHOOK_URL, or set both "
            "DISCORD_BOT_TOKEN and DISCORD_PROGRESS_CHANNEL_ID to enable Discord notifications."
        )
        return {
            "status": "skipped",
            "transport": "disabled",
            "reason": "missing-config",
            "message_length": len(message),
        }

    payload = json.dumps({"content": message}).encode()
    req = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{channel_id}/messages",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bot {bot_token}"},
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        response.read()
    return {"status": "sent", "transport": "bot-channel", "message_length": len(message)}


def send_discord_best_effort(message: str, *, context: str) -> dict[str, object]:
    try:
        event = dict(send_discord(message))
    except Exception as exc:
        print(f"[notify] Discord notification failed ({context}): {type(exc).__name__}: {exc}")
        return {
            "status": "failed",
            "transport": "discord",
            "reason": "exception",
            "error": str(exc),
            "error_type": type(exc).__name__,
            "context": context,
            "message_length": len(message[:1900]),
        }
    event.setdefault("status", "sent")
    event.setdefault("transport", "discord")
    event["context"] = context
    event.setdefault("message_length", len(message[:1900]))
    return event


def write_report(
    report_path: Path,
    *,
    outcome: str,
    repo_root: Path,
    run_dir: Path,
    command: list[str],
    exit_code: int,
    metrics: Metrics,
    duration_s: float,
    build_log: Path,
    smoke_log: Path,
    fuzz_log: Path,
    target_adapter: TargetAdapter,
    crash_info: dict[str, object] | None = None,
    artifact_event: dict[str, object] | None = None,
    policy_action: dict[str, object] | None = None,
    policy_execution: dict[str, object] | None = None,
    target_profile_summary: dict[str, object] | None = None,
    notification_event: dict[str, object] | None = None,
) -> None:
    branch_code, branch = run_quiet(["git", "branch", "--show-current"], repo_root)
    commit_code, commit = run_quiet(["git", "rev-parse", "HEAD"], repo_root)
    status_code, status = run_quiet(["git", "status", "--short"], repo_root)
    report_path.write_text(
        "\n".join(
            [
                "# FUZZING_REPORT",
                "",
                "## Summary",
                "",
                f"- outcome: {outcome}",
                f"- commit: {commit.strip() if commit_code == 0 else 'unknown'}",
                f"- branch: {branch.strip() if branch_code == 0 else 'unknown'}",
                f"- target: {target_adapter.report_target}",
                f"- target_profile_name: {target_profile_summary.get('name') if target_profile_summary else None}",
                f"- target_profile_path: {target_profile_summary.get('path') if target_profile_summary else None}",
                f"- target_profile_primary_mode: {target_profile_summary.get('primary_mode') if target_profile_summary else None}",
                f"- target_profile_stage_count: {target_profile_summary.get('stage_count') if target_profile_summary else None}",
                f"- target_profile_load_status: {target_profile_summary.get('load_status') if target_profile_summary else None}",
                f"- target_profile_load_error: {target_profile_summary.get('load_error') if target_profile_summary else None}",
                f"- target_profile_load_error_detail: {target_profile_summary.get('load_error_detail') if target_profile_summary else None}",
                f"- target_profile_validation_status: {target_profile_summary.get('validation_status') if target_profile_summary else None}",
                f"- target_profile_validation_severity: {target_profile_summary.get('validation_severity') if target_profile_summary else None}",
                f"- target_profile_validation_codes: {target_profile_summary.get('validation_codes') if target_profile_summary else None}",
                f"- duration_seconds: {duration_s:.1f}",
                f"- run_dir: {run_dir}",
                "",
                "## Command",
                "",
                "```bash",
                " ".join(command),
                "```",
                "",
                "## Build And Smoke",
                "",
                f"- build_log: {build_log}",
                f"- smoke_log: {smoke_log}",
                "",
                "## Fuzzing Metrics",
                "",
                f"- exit_code: {exit_code}",
                f"- cov: {metrics.cov}",
                f"- ft: {metrics.ft}",
                f"- corpus_units: {metrics.corp_units}",
                f"- corpus_size: {metrics.corp_size}",
                f"- exec_per_second: {metrics.execs}",
                f"- rss: {metrics.rss}",
                f"- crash_detected: {metrics.crash}",
                f"- timeout_detected: {metrics.timeout}",
                f"- fuzz_log: {fuzz_log}",
                "",
                "## Artifact Classification",
                "",
                f"- artifact_category: {artifact_event.get('category') if artifact_event else None}",
                f"- artifact_reason: {artifact_event.get('reason') if artifact_event else None}",
                "",
                "## Policy Action",
                "",
                f"- policy_priority: {policy_action.get('priority') if policy_action else None}",
                f"- policy_action_code: {policy_action.get('action_code') if policy_action else None}",
                f"- policy_next_mode: {policy_action.get('next_mode') if policy_action else None}",
                f"- policy_bucket: {policy_action.get('bucket') if policy_action else None}",
                f"- policy_recommended_action: {policy_action.get('recommended_action') if policy_action else None}",
                f"- policy_matched_triggers: {policy_action.get('matched_triggers') if policy_action else None}",
                f"- policy_profile_severity: {policy_action.get('profile_severity') if policy_action else None}",
                f"- policy_profile_labels: {policy_action.get('profile_labels') if policy_action else None}",
                "",
                "## Policy Execution",
                "",
                f"- policy_execution_updated: {policy_execution.get('updated') if policy_execution else None}",
                f"- regression_trigger: {policy_execution.get('regression_trigger') if policy_execution else None}",
                "",
                "## Notifications",
                "",
                f"- notification_status: {notification_event.get('status') if notification_event else None}",
                f"- notification_transport: {notification_event.get('transport') if notification_event else None}",
                f"- notification_reason: {notification_event.get('reason') if notification_event else None}",
                f"- notification_error_type: {notification_event.get('error_type') if notification_event else None}",
                f"- notification_error: {notification_event.get('error') if notification_event else None}",
                f"- notification_context: {notification_event.get('context') if notification_event else None}",
                "",
                "## Crash Fingerprint",
                "",
                f"- crash_kind: {crash_info.get('kind') if crash_info else None}",
                f"- crash_location: {crash_info.get('location') if crash_info else None}",
                f"- crash_summary: {crash_info.get('summary') if crash_info else None}",
                f"- crash_stage: {crash_info.get('stage') if crash_info else None}",
                f"- crash_stage_class: {crash_info.get('stage_class') if crash_info else None}",
                f"- crash_stage_depth_rank: {crash_info.get('stage_depth_rank') if crash_info else None}",
                f"- crash_stage_confidence: {crash_info.get('stage_confidence') if crash_info else None}",
                f"- crash_stage_match_source: {crash_info.get('stage_match_source') if crash_info else None}",
                f"- crash_stage_reason: {crash_info.get('stage_reason') if crash_info else None}",
                f"- crash_fingerprint: {crash_info.get('fingerprint') if crash_info else None}",
                f"- crash_is_duplicate: {crash_info.get('is_duplicate') if crash_info else None}",
                f"- crash_occurrence_count: {crash_info.get('occurrence_count') if crash_info else None}",
                f"- crash_first_seen_run: {crash_info.get('first_seen_run') if crash_info else None}",
                f"- crash_artifact: {crash_info.get('artifact_path') if crash_info else None}",
                f"- crash_artifact_sha1: {crash_info.get('artifact_sha1') if crash_info else None}",
                "",
                "## Crash Or Timeout Excerpt",
                "",
                "```text",
                "\n".join(metrics.top_crash_lines) if metrics.top_crash_lines else "none",
                "```",
                "",
                "## Git Status",
                "",
                "```text",
                status.strip() if status_code == 0 and status.strip() else "clean",
                "```",
                "",
                "## Recommended Next Action",
                "",
                recommended_action(outcome, policy_action=policy_action),
                "",
            ]
        ),
        encoding="utf-8",
    )


def recommended_action(outcome: str, *, policy_action: dict[str, object] | None = None) -> str:
    policy_text = str((policy_action or {}).get("recommended_action") or "").strip()
    if policy_text:
        return policy_text if policy_text.startswith("-") else f"- {policy_text}"
    if outcome == "crash":
        return "- Preserve crash artifact locally. Ask Codex to inspect the sanitizer stack before pushing any reproducer."
    if outcome == "timeout":
        return "- Inspect timeout path and consider reducing slow decode paths or adding timeout-specific seeds."
    if outcome == "no-progress":
        return "- Ask Codex to improve corpus or harness depth. Check whether inputs reach invoke/tile decode."
    if outcome == "build-failed":
        return "- Ask Codex to inspect the build log."
    if outcome == "smoke-failed":
        return "- Ask Codex to inspect the smoke log and seed handling."
    return "- Continue fuzzing or add coverage/reachability reporting next."


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=Path(__file__).resolve().parents[1], type=Path)
    parser.add_argument(
        "--target-profile",
        default=os.environ.get("TARGET_PROFILE_PATH"),
        type=Path,
        help="Optional target profile YAML path. Defaults to fuzz-records/profiles/openhtj2k-target-profile-v1.yaml when present.",
    )
    parser.add_argument("--max-total-time", default=env_int_default("MAX_TOTAL_TIME", 3600), type=int)
    parser.add_argument("--no-progress-seconds", default=env_int_default("NO_PROGRESS_SECONDS", 1800), type=int)
    parser.add_argument(
        "--progress-interval-seconds",
        default=env_int_default("PROGRESS_INTERVAL_SECONDS", 600),
        type=int,
        help="Send/write progress snapshots at this interval; use 0 to disable interval notifications.",
    )
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--skip-smoke", action="store_true")
    parser.add_argument(
        "--prepare-autonomous-supervisor",
        action="store_true",
        help="Write a long-running Hermes self-prompt supervisor bundle for continuous autonomous development, then exit.",
    )
    parser.add_argument(
        "--autonomous-supervisor-sleep-seconds",
        default=env_int_default("AUTONOMOUS_SUPERVISOR_SLEEP_SECONDS", 600),
        type=int,
        help="Sleep interval between autonomous supervisor iterations; minimum 10 seconds.",
    )
    parser.add_argument(
        "--autonomous-supervisor-channel-id",
        default=os.environ.get("AUTONOMOUS_SUPERVISOR_CHANNEL_ID") or AUTONOMOUS_SUPERVISOR_DEFAULT_CHANNEL_ID,
        help="Discord channel id for concise MCP progress logging when the autonomous supervisor prompt runs.",
    )
    parser.add_argument(
        "--prepare-refiner-orchestration",
        action="store_true",
        help="Consume one pending refiner entry, emit a low-risk plan plus subagent/cron prompt bundle, then exit.",
    )
    parser.add_argument(
        "--dispatch-refiner-orchestration",
        action="store_true",
        help="Consume one prepared refiner orchestration entry and emit tool-aligned delegate_task/cronjob request artifacts, then exit.",
    )
    parser.add_argument(
        "--bridge-refiner-dispatch",
        action="store_true",
        help="Consume one ready refiner dispatch entry and emit Hermes CLI bridge scripts that can perform the actual cron/delegate tool call when executed.",
    )
    parser.add_argument(
        "--launch-refiner-bridge",
        action="store_true",
        help="Execute one armed refiner bridge script, capture the result, and record launch status in the registry.",
    )
    parser.add_argument(
        "--verify-refiner-result",
        action="store_true",
        help="Verify one succeeded refiner result by checking cron visibility or delegate session/artifact evidence and record verification status.",
    )
    parser.add_argument(
        "--apply-verification-policy",
        action="store_true",
        help="Classify one unverified refiner result into retry or escalation and emit the corresponding policy artifact.",
    )
    parser.add_argument(
        "--draft-target-profile",
        action="store_true",
        help="Analyze the current repo conservatively and emit a draft target profile artifact plus reconnaissance manifest, then exit.",
    )
    parser.add_argument(
        "--draft-harness-plan",
        action="store_true",
        help="Generate a low-risk harness candidate draft from reconnaissance/profile artifacts, then exit.",
    )
    parser.add_argument(
        "--draft-harness-evaluation",
        action="store_true",
        help="Generate a low-risk evaluation plan for the top harness candidates, then exit.",
    )
    parser.add_argument(
        "--draft-harness-skeleton",
        action="store_true",
        help="Generate a low-risk harness skeleton draft plus revision loop artifact for the selected candidate, then exit.",
    )
    parser.add_argument(
        "--run-harness-skeleton-closure",
        action="store_true",
        help="Run build/smoke closure probes for the latest harness skeleton artifact, then exit.",
    )
    parser.add_argument(
        "--decide-harness-correction-policy",
        action="store_true",
        help="Consume the latest harness correction draft conservatively against closure evidence and emit a correction-policy artifact, then exit.",
    )
    parser.add_argument(
        "--prepare-harness-apply-candidate",
        action="store_true",
        help="Generate a guarded harness apply-candidate artifact and optional delegate request from the latest promoted correction policy, then exit.",
    )
    parser.add_argument(
        "--bridge-harness-apply-candidate",
        action="store_true",
        help="Create a delegate bridge prompt/script for the latest guarded harness apply candidate, then exit.",
    )
    parser.add_argument(
        "--launch-harness-apply-candidate",
        action="store_true",
        help="Launch the latest armed guarded harness apply bridge script and record delegate metadata, then exit.",
    )
    parser.add_argument(
        "--verify-harness-apply-candidate",
        action="store_true",
        help="Verify the latest succeeded guarded harness apply candidate artifact/session lineage and record verification status, then exit.",
    )
    parser.add_argument(
        "--apply-verified-harness-patch-candidate",
        action="store_true",
        help="Apply the latest verified guarded harness patch candidate within limited scope and rerun build/smoke probes, then exit.",
    )
    parser.add_argument(
        "--route-harness-apply-recovery",
        action="store_true",
        help="Route the latest harness apply recovery decision into queue/registry artifacts for follow-on handling, then exit.",
    )
    parser.add_argument(
        "--consume-harness-apply-recovery-queue",
        action="store_true",
        help="Consume one queued harness apply recovery entry and either rearm bridge work or park the candidate for review, then exit.",
    )
    parser.add_argument(
        "--run-harness-apply-recovery-downstream-automation",
        action="store_true",
        help="Consume one recovery queue entry and immediately continue retry downstream work through bridge launch and verification when applicable, then exit.",
    )
    parser.add_argument(
        "--run-harness-apply-recovery-full-closed-loop-chaining",
        action="store_true",
        help="Continue retry recovery from consume/rearm/launch/verify through guarded apply and reroute when verification succeeds, then exit.",
    )
    parser.add_argument(
        "--run-harness-apply-retry-recursive-chaining",
        action="store_true",
        help="Repeat retry full-chain recovery until reroute stops requesting retry or the recursion guard is hit, then exit.",
    )
    parser.add_argument(
        "--run-harness-apply-recovery-followup-auto-reingestion",
        action="store_true",
        help="Consume one verified hold/abort follow-up result and reingest it into the correction-policy or apply-candidate loop, then exit.",
    )
    parser.add_argument(
        "--run-harness-apply-reingested-downstream-chaining",
        action="store_true",
        help="Reingest one verified hold/abort follow-up result and continue its downstream apply chain through bridge/verify/apply/reroute when possible, then exit.",
    )
    parser.add_argument(
        "--run-short-harness-probe",
        action="store_true",
        help="Run a strict fail-fast short build/smoke probe for the top harness candidate, then exit.",
    )
    parser.add_argument(
        "--bridge-harness-probe-feedback",
        action="store_true",
        help="Bridge the latest harness probe outcome into refinement registries and feedback artifacts, then exit.",
    )
    parser.add_argument(
        "--route-harness-probe-feedback",
        action="store_true",
        help="Route the latest probe feedback into candidate handoff artifacts plus refiner orchestration/dispatch bundles, then exit.",
    )
    parser.add_argument(
        "--update-ranked-candidate-registry",
        action="store_true",
        help="Update the ranked harness candidate registry from the latest probe feedback, then exit.",
    )
    parser.add_argument(
        "--queue-latest-evidence-review-followup",
        action="store_true",
        help="Queue a harness review follow-up from the latest LLM evidence packet when it resolves to review-current-candidate, then exit.",
    )
    parser.add_argument(
        "--run-latest-evidence-review-followup-chain",
        action="store_true",
        help="Queue the latest review-route evidence packet and immediately prepare/dispatch/bridge/launch the refiner follow-up chain, then exit.",
    )
    parser.add_argument(
        "--write-llm-evidence-packet",
        action="store_true",
        help="Collect the latest run/probe/apply artifacts into an LLM-facing evidence packet, then exit.",
    )
    parser.add_argument(
        "--rehydrate-run-artifacts",
        action="store_true",
        help="Reparse an existing fuzz.log, repair crash metadata in status/history/index artifacts, and exit.",
    )
    parser.add_argument(
        "--rehydrate-run-dir",
        type=Path,
        help="Existing run directory to repair. Defaults to current_status.run_dir or the latest fuzz-artifacts/runs entry.",
    )
    parser.add_argument(
        "--repair-latest-crash-state",
        action="store_true",
        help="Backward-compatible alias: repair stale latest crash/leak metadata in current status, run status, history, and crash index, then exit.",
    )
    args = parser.parse_args()

    repo_root = args.repo.resolve()
    automation_dir = repo_root / "fuzz-artifacts" / "automation"
    if args.rehydrate_run_artifacts or getattr(args, "repair_latest_crash_state", False):
        result = rehydrate_run_artifacts(repo_root, run_dir=args.rehydrate_run_dir)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("rehydrated") else 1
    if args.queue_latest_evidence_review_followup:
        result = queue_latest_evidence_review_followup(repo_root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("queued") else 1
    if args.run_latest_evidence_review_followup_chain:
        result = run_latest_evidence_review_followup_chain(repo_root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("launched") else 1
    if args.prepare_autonomous_supervisor:
        result = write_autonomous_supervisor_bundle(
            repo_root,
            sleep_seconds=args.autonomous_supervisor_sleep_seconds,
            channel_id=args.autonomous_supervisor_channel_id,
        )
        print(json.dumps({"prepared_autonomous_supervisor": True, **result}, indent=2, sort_keys=True))
        return 0
    if args.prepare_refiner_orchestration:
        result = prepare_next_refiner_orchestration(automation_dir, repo_root=repo_root)
        if result is None:
            print(json.dumps({"prepared": False, "reason": "no-pending-refiner-work"}, indent=2, sort_keys=True))
            return 0
        print(json.dumps({"prepared": True, **result}, indent=2, sort_keys=True))
        return 0
    if args.dispatch_refiner_orchestration:
        result = dispatch_next_refiner_orchestration(automation_dir, repo_root=repo_root)
        if result is None:
            print(json.dumps({"dispatched": False, "reason": "no-prepared-refiner-work"}, indent=2, sort_keys=True))
            return 0
        print(json.dumps({"dispatched": True, **result}, indent=2, sort_keys=True))
        return 0
    if args.bridge_refiner_dispatch:
        result = bridge_next_refiner_dispatch(automation_dir, repo_root=repo_root)
        if result is None:
            print(json.dumps({"bridged": False, "reason": "no-ready-refiner-dispatch"}, indent=2, sort_keys=True))
            return 0
        print(json.dumps({"bridged": True, **result}, indent=2, sort_keys=True))
        return 0
    if args.launch_refiner_bridge:
        result = launch_next_refiner_bridge(automation_dir, repo_root=repo_root)
        if result is None:
            print(json.dumps({"launched": False, "reason": "no-armed-refiner-bridge"}, indent=2, sort_keys=True))
            return 0
        print(json.dumps({"launched": True, **result}, indent=2, sort_keys=True))
        return 0
    if args.verify_refiner_result:
        result = verify_next_refiner_result(automation_dir, repo_root=repo_root)
        if result is None:
            print(json.dumps({"verified": False, "reason": "no-succeeded-refiner-result"}, indent=2, sort_keys=True))
            return 0
        print(json.dumps({"verified": True, **result}, indent=2, sort_keys=True))
        return 0
    if args.apply_verification_policy:
        result = apply_verification_failure_policy(automation_dir, repo_root=repo_root)
        if result is None:
            print(json.dumps({"policy_applied": False, "reason": "no-unverified-refiner-result"}, indent=2, sort_keys=True))
            return 0
        print(json.dumps({"policy_applied": True, **result}, indent=2, sort_keys=True))
        return 0
    if args.draft_target_profile:
        result = write_target_profile_auto_draft(repo_root)
        print(json.dumps({"drafted": True, **result}, indent=2, sort_keys=True))
        return 0
    if args.draft_harness_plan:
        result = write_harness_candidate_draft(repo_root)
        print(json.dumps({"drafted_harness_plan": True, **result}, indent=2, sort_keys=True))
        return 0
    if args.draft_harness_evaluation:
        result = write_harness_evaluation_draft(repo_root)
        print(json.dumps({"drafted_harness_evaluation": True, **result}, indent=2, sort_keys=True))
        return 0
    if args.draft_harness_skeleton:
        result = write_harness_skeleton_draft(repo_root)
        print(json.dumps({"drafted_harness_skeleton": True, **result}, indent=2, sort_keys=True))
        return 0
    if args.run_harness_skeleton_closure:
        result = run_harness_skeleton_closure(repo_root)
        print(json.dumps({"ran_harness_skeleton_closure": True, **result}, indent=2, sort_keys=True))
        return 0 if result.get("build_probe_status") != "failed" and result.get("smoke_probe_status") != "failed" else 1
    if args.decide_harness_correction_policy:
        result = write_harness_correction_policy(repo_root)
        print(json.dumps({"decided_harness_correction_policy": True, **result}, indent=2, sort_keys=True))
        return 0
    if args.prepare_harness_apply_candidate:
        result = write_harness_apply_candidate(repo_root)
        print(json.dumps({"prepared_harness_apply_candidate": True, **result}, indent=2, sort_keys=True))
        return 0
    if args.bridge_harness_apply_candidate:
        result = prepare_harness_apply_candidate_bridge(repo_root)
        print(json.dumps({"bridged_harness_apply_candidate": True, **result}, indent=2, sort_keys=True))
        return 0 if result.get("bridge_status") in {"armed", "skipped"} else 1
    if args.launch_harness_apply_candidate:
        result = launch_harness_apply_candidate_bridge(repo_root)
        if result is None:
            print(json.dumps({"launched_harness_apply_candidate": False, "reason": "no-armed-harness-apply-candidate"}, indent=2, sort_keys=True))
            return 0
        print(json.dumps({"launched_harness_apply_candidate": True, **result}, indent=2, sort_keys=True))
        return 0 if result.get("bridge_status") == "succeeded" else 1
    if args.verify_harness_apply_candidate:
        result = verify_harness_apply_candidate_result(repo_root)
        if result is None:
            print(json.dumps({"verified_harness_apply_candidate": False, "reason": "no-succeeded-harness-apply-candidate"}, indent=2, sort_keys=True))
            return 0
        print(json.dumps({"verified_harness_apply_candidate": True, **result}, indent=2, sort_keys=True))
        return 0 if result.get("verification_status") == "verified" else 1
    if args.apply_verified_harness_patch_candidate:
        result = apply_verified_harness_patch_candidate(repo_root)
        if result is None:
            print(json.dumps({"applied_verified_harness_patch_candidate": False, "reason": "no-verified-harness-apply-candidate"}, indent=2, sort_keys=True))
            return 0
        print(json.dumps({"applied_verified_harness_patch_candidate": True, **result}, indent=2, sort_keys=True))
        return 0 if result.get("apply_status") == "applied" and result.get("build_probe_status") != "failed" and result.get("smoke_probe_status") != "failed" else 1
    if args.route_harness_apply_recovery:
        result = route_harness_apply_recovery(repo_root)
        if result is None:
            print(json.dumps({"routed_harness_apply_recovery": False, "reason": "no-routable-harness-apply-recovery"}, indent=2, sort_keys=True))
            return 0
        print(json.dumps({"routed_harness_apply_recovery": True, **result}, indent=2, sort_keys=True))
        return 0
    if args.consume_harness_apply_recovery_queue:
        result = consume_harness_apply_recovery_queue(repo_root)
        if result is None:
            print(json.dumps({"consumed_harness_apply_recovery_queue": False, "reason": "no-pending-harness-apply-recovery-queue"}, indent=2, sort_keys=True))
            return 0
        print(json.dumps({"consumed_harness_apply_recovery_queue": True, **result}, indent=2, sort_keys=True))
        return 0
    if args.run_harness_apply_recovery_downstream_automation:
        result = run_harness_apply_recovery_downstream_automation(repo_root)
        if result is None:
            print(json.dumps({"ran_harness_apply_recovery_downstream_automation": False, "reason": "no-pending-harness-apply-recovery-queue"}, indent=2, sort_keys=True))
            return 0
        print(json.dumps({"ran_harness_apply_recovery_downstream_automation": True, **result}, indent=2, sort_keys=True))
        return 0 if result.get("downstream_status") in {"verified", "pending-review", "aborted", "resolved", "launch-only", "launch-skipped"} else 1
    if args.run_harness_apply_recovery_full_closed_loop_chaining:
        result = run_harness_apply_recovery_full_closed_loop_chaining(repo_root)
        if result is None:
            print(json.dumps({"ran_harness_apply_recovery_full_closed_loop_chaining": False, "reason": "no-pending-harness-apply-recovery-queue"}, indent=2, sort_keys=True))
            return 0
        print(json.dumps({"ran_harness_apply_recovery_full_closed_loop_chaining": True, **result}, indent=2, sort_keys=True))
        return 0 if result.get("full_chain_status") in {"rerouted", "applied-no-reroute", "verified-no-apply", "pending-review", "aborted", "resolved", "launch-only", "launch-skipped"} else 1
    if args.run_harness_apply_retry_recursive_chaining:
        result = run_harness_apply_retry_recursive_chaining(repo_root)
        if result is None:
            print(json.dumps({"ran_harness_apply_retry_recursive_chaining": False, "reason": "no-pending-harness-apply-recovery-queue"}, indent=2, sort_keys=True))
            return 0
        print(json.dumps({"ran_harness_apply_retry_recursive_chaining": True, **result}, indent=2, sort_keys=True))
        return 0 if result.get("recursive_chain_status") in {"resolved", "aborted", "hold", "max-cycles-reached", "stopped", "cooldown-active"} else 1
    if args.run_harness_apply_recovery_followup_auto_reingestion:
        result = run_harness_apply_recovery_followup_auto_reingestion(repo_root)
        if result is None:
            print(json.dumps({"ran_harness_apply_recovery_followup_auto_reingestion": False, "reason": "no-verified-harness-apply-recovery-followup"}, indent=2, sort_keys=True))
            return 0
        print(json.dumps({"ran_harness_apply_recovery_followup_auto_reingestion": True, **result}, indent=2, sort_keys=True))
        return 0 if result.get("reingestion_status") == "reingested" else 1
    if args.run_harness_apply_reingested_downstream_chaining:
        result = run_harness_apply_reingested_downstream_chaining(repo_root)
        if result is None:
            print(json.dumps({"ran_harness_apply_reingested_downstream_chaining": False, "reason": "no-verified-harness-apply-recovery-followup"}, indent=2, sort_keys=True))
            return 0
        print(json.dumps({"ran_harness_apply_reingested_downstream_chaining": True, **result}, indent=2, sort_keys=True))
        return 0 if result.get("downstream_chain_status") in {"rerouted", "applied", "verified", "succeeded", "bridge-skipped", "launch-skipped", "no-apply-candidate", "budget-exhausted", "cooldown-active"} else 1
    if args.run_short_harness_probe:
        result = run_short_harness_probe(repo_root)
        print(json.dumps({"ran_short_harness_probe": True, **result}, indent=2, sort_keys=True))
        return 0 if result.get("build_probe_status") != "failed" and result.get("smoke_probe_status") != "failed" else 1
    if args.bridge_harness_probe_feedback:
        result = bridge_harness_probe_feedback(repo_root)
        print(json.dumps({"bridged_harness_probe_feedback": True, **result}, indent=2, sort_keys=True))
        return 0 if result.get("bridged") else 1
    if args.route_harness_probe_feedback:
        result = route_harness_probe_feedback(repo_root)
        print(json.dumps({"routed_harness_probe_feedback": True, **result}, indent=2, sort_keys=True))
        return 0 if result.get("routed") else 1
    if args.update_ranked_candidate_registry:
        result = update_ranked_candidate_registry(repo_root)
        print(json.dumps({"updated_ranked_candidate_registry": True, **result}, indent=2, sort_keys=True))
        return 0 if result.get("updated") else 1
    if args.write_llm_evidence_packet:
        result = write_llm_evidence_packet(repo_root)
        print(json.dumps({"wrote_llm_evidence_packet": True, **result}, indent=2, sort_keys=True))
        return 0

    target_profile_path = resolve_target_profile_path(repo_root, args.target_profile)
    loaded_target_profile = load_target_profile(target_profile_path)
    target_profile_summary = build_target_profile_summary(loaded_target_profile, target_profile_path)
    target_profile = runtime_target_profile(loaded_target_profile)
    target_adapter = get_target_adapter(target_profile_summary)
    build_command = target_adapter.build_command_list()
    smoke_command = target_adapter.smoke_command(repo_root)
    fuzz_command = target_adapter.fuzz_command_list()
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    git_short = run_quiet(["git", "rev-parse", "--short", "HEAD"], repo_root)[1].strip() or "unknown"
    run_dir_env = os.environ.get("RUN_DIR")
    if run_dir_env:
        run_dir = Path(run_dir_env)
    else:
        run_dir = repo_root / "fuzz-artifacts" / "runs" / f"{timestamp}_{git_short}"
    run_dir.mkdir(parents=True, exist_ok=True)
    build_log = run_dir / "build.log"
    smoke_log = run_dir / "smoke.log"
    fuzz_log = run_dir / "fuzz.log"
    report_path = run_dir / "FUZZING_REPORT.md"
    status_path = run_dir / "status.json"
    current_status_path = repo_root / "fuzz-artifacts" / "current_status.json"
    crash_index_path = repo_root / "fuzz-artifacts" / "crash_index.json"
    current_mode = os.environ.get("FUZZ_MODE")
    history_path = automation_dir / "run_history.json"
    run_history = load_registry(history_path, {"entries": []}).get("entries", [])

    if not args.skip_build:
        build_code, build_output = run_quiet(build_command, repo_root)
        build_log.write_text(build_output, encoding="utf-8", errors="replace")
        if build_code != 0:
            failure_metrics = Metrics()
            failure_artifact_event = classify_artifact_event("build-failed", None)
            failure_policy_action = decide_policy_action("build-failed", failure_artifact_event, None, target_profile, run_history)
            failure_policy_execution = apply_policy_action(
                automation_dir,
                run_dir=str(run_dir),
                report_path=str(report_path),
                outcome="build-failed",
                artifact_event=failure_artifact_event,
                policy_action=failure_policy_action,
                crash_info=None,
                repo_root=repo_root,
                current_mode=current_mode,
            )
            failure_snapshot = metrics_snapshot(
                outcome="build-failed",
                metrics=failure_metrics,
                run_dir=run_dir,
                report_path=report_path,
                start=time.monotonic(),
                artifact_event=failure_artifact_event,
                policy_action=failure_policy_action,
                policy_execution=failure_policy_execution,
                target_profile_summary=target_profile_summary,
            )
            write_status(status_path, failure_snapshot)
            write_status(current_status_path, failure_snapshot)
            history_result = append_run_history(automation_dir, failure_snapshot)
            failure_snapshot["history_appended"] = history_result.get("appended")
            write_status(status_path, failure_snapshot)
            write_status(current_status_path, failure_snapshot)
            write_report(
                report_path,
                outcome="build-failed",
                repo_root=repo_root,
                run_dir=run_dir,
                command=build_command,
                exit_code=build_code,
                metrics=failure_metrics,
                duration_s=0,
                build_log=build_log,
                smoke_log=smoke_log,
                fuzz_log=fuzz_log,
                target_adapter=target_adapter,
                artifact_event=failure_artifact_event,
                policy_action=failure_policy_action,
                policy_execution=failure_policy_execution,
                target_profile_summary=target_profile_summary,
            )
            notification_event = send_discord_best_effort(
                f"[{target_adapter.notification_label}] BUILD FAILED\nreport: {report_path}",
                context="build-failed",
            )
            failure_snapshot = metrics_snapshot(
                outcome="build-failed",
                metrics=failure_metrics,
                run_dir=run_dir,
                report_path=report_path,
                start=time.monotonic(),
                artifact_event=failure_artifact_event,
                policy_action=failure_policy_action,
                policy_execution=failure_policy_execution,
                target_profile_summary=target_profile_summary,
                notification_event=notification_event,
            )
            failure_snapshot["history_appended"] = history_result.get("appended")
            write_status(status_path, failure_snapshot)
            write_status(current_status_path, failure_snapshot)
            write_report(
                report_path,
                outcome="build-failed",
                repo_root=repo_root,
                run_dir=run_dir,
                command=build_command,
                exit_code=build_code,
                metrics=failure_metrics,
                duration_s=0,
                build_log=build_log,
                smoke_log=smoke_log,
                fuzz_log=fuzz_log,
                target_adapter=target_adapter,
                artifact_event=failure_artifact_event,
                policy_action=failure_policy_action,
                policy_execution=failure_policy_execution,
                target_profile_summary=target_profile_summary,
                notification_event=notification_event,
            )
            refresh_llm_evidence_packet_best_effort(repo_root)
            return build_code

    if not args.skip_smoke:
        smoke_code, smoke_output = run_quiet(smoke_command, repo_root)
        smoke_log.write_text(smoke_output, encoding="utf-8", errors="replace")
        if smoke_code != 0:
            failure_metrics = Metrics()
            failure_artifact_event = classify_artifact_event("smoke-failed", None)
            failure_policy_action = decide_policy_action("smoke-failed", failure_artifact_event, None, target_profile, run_history)
            failure_policy_execution = apply_policy_action(
                automation_dir,
                run_dir=str(run_dir),
                report_path=str(report_path),
                outcome="smoke-failed",
                artifact_event=failure_artifact_event,
                policy_action=failure_policy_action,
                crash_info=None,
                repo_root=repo_root,
                current_mode=current_mode,
            )
            failure_snapshot = metrics_snapshot(
                outcome="smoke-failed",
                metrics=failure_metrics,
                run_dir=run_dir,
                report_path=report_path,
                start=time.monotonic(),
                artifact_event=failure_artifact_event,
                policy_action=failure_policy_action,
                policy_execution=failure_policy_execution,
                target_profile_summary=target_profile_summary,
            )
            write_status(status_path, failure_snapshot)
            write_status(current_status_path, failure_snapshot)
            history_result = append_run_history(automation_dir, failure_snapshot)
            failure_snapshot["history_appended"] = history_result.get("appended")
            write_status(status_path, failure_snapshot)
            write_status(current_status_path, failure_snapshot)
            write_report(
                report_path,
                outcome="smoke-failed",
                repo_root=repo_root,
                run_dir=run_dir,
                command=smoke_command,
                exit_code=smoke_code,
                metrics=failure_metrics,
                duration_s=0,
                build_log=build_log,
                smoke_log=smoke_log,
                fuzz_log=fuzz_log,
                target_adapter=target_adapter,
                artifact_event=failure_artifact_event,
                policy_action=failure_policy_action,
                policy_execution=failure_policy_execution,
                target_profile_summary=target_profile_summary,
            )
            notification_event = send_discord_best_effort(
                f"[{target_adapter.notification_label}] SMOKE FAILED\nreport: {report_path}",
                context="smoke-failed",
            )
            failure_snapshot = metrics_snapshot(
                outcome="smoke-failed",
                metrics=failure_metrics,
                run_dir=run_dir,
                report_path=report_path,
                start=time.monotonic(),
                artifact_event=failure_artifact_event,
                policy_action=failure_policy_action,
                policy_execution=failure_policy_execution,
                target_profile_summary=target_profile_summary,
                notification_event=notification_event,
            )
            failure_snapshot["history_appended"] = history_result.get("appended")
            write_status(status_path, failure_snapshot)
            write_status(current_status_path, failure_snapshot)
            write_report(
                report_path,
                outcome="smoke-failed",
                repo_root=repo_root,
                run_dir=run_dir,
                command=smoke_command,
                exit_code=smoke_code,
                metrics=failure_metrics,
                duration_s=0,
                build_log=build_log,
                smoke_log=smoke_log,
                fuzz_log=fuzz_log,
                target_adapter=target_adapter,
                artifact_event=failure_artifact_event,
                policy_action=failure_policy_action,
                policy_execution=failure_policy_execution,
                target_profile_summary=target_profile_summary,
                notification_event=notification_event,
            )
            refresh_llm_evidence_packet_best_effort(repo_root)
            return smoke_code

    command = fuzz_command
    env = os.environ.copy()
    env["MAX_TOTAL_TIME"] = str(args.max_total_time)
    env["RUN_DIR"] = str(run_dir)
    env["WATCHER_STDOUT_ONLY"] = "1"
    start = time.monotonic()
    metrics = Metrics()
    outcome = "ok"
    crash_info: dict[str, object] | None = None
    artifact_event: dict[str, object] | None = None
    policy_action: dict[str, object] | None = None
    policy_execution: dict[str, object] | None = None
    last_progress_notify_at = start

    with fuzz_log.open("w", encoding="utf-8", errors="replace") as log:
        proc = subprocess.Popen(
            command,
            cwd=repo_root,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            start_new_session=True,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            log.write(line)
            log.flush()
            metrics.update_from_line(line)
            snapshot = metrics_snapshot(
                outcome=outcome,
                metrics=metrics,
                run_dir=run_dir,
                report_path=report_path,
                start=start,
                crash_info=crash_info,
                artifact_event=artifact_event,
                policy_action=policy_action,
                target_profile_summary=target_profile_summary,
            )
            write_status(status_path, snapshot)
            write_status(current_status_path, snapshot)
            if args.progress_interval_seconds > 0 and (
                time.monotonic() - last_progress_notify_at >= args.progress_interval_seconds
            ):
                message = format_progress_message(snapshot, target_label=target_adapter.notification_label)
                print(f"[progress] {message.replace(chr(10), ' | ')}")
                notification_event = send_discord_best_effort(message, context="progress")
                snapshot = metrics_snapshot(
                    outcome=outcome,
                    metrics=metrics,
                    run_dir=run_dir,
                    report_path=report_path,
                    start=start,
                    crash_info=crash_info,
                    artifact_event=artifact_event,
                    policy_action=policy_action,
                    target_profile_summary=target_profile_summary,
                    notification_event=notification_event,
                )
                write_status(status_path, snapshot)
                write_status(current_status_path, snapshot)
                last_progress_notify_at = time.monotonic()
            if time.monotonic() - metrics.last_progress_at > args.no_progress_seconds:
                outcome = "no-progress"
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                break
        exit_code = proc.wait()

    duration_s = time.monotonic() - start
    if metrics.crash:
        outcome = "crash"
    elif metrics.timeout:
        outcome = "timeout"
    elif exit_code != 0 and outcome == "ok":
        outcome = "fuzzer-exit-nonzero"

    if outcome in {"crash", "timeout", "fuzzer-exit-nonzero"} and metrics.top_crash_lines:
        signature = build_crash_signature(metrics.top_crash_lines)
        crash_info = update_crash_index(
            crash_index_path,
            signature,
            run_dir=str(run_dir),
            report_path=str(report_path),
        )
        crash_info = enrich_crash_info_with_stage_info(crash_info, metrics.top_crash_lines, target_profile)

    artifact_event = classify_artifact_event(outcome, crash_info)
    current_history_entry = {
        "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "outcome": outcome,
        "cov": metrics.cov,
        "ft": metrics.ft,
        "exec_per_second": metrics.execs,
        "crash_stage": crash_info.get("stage") if crash_info else None,
        "crash_fingerprint": crash_info.get("fingerprint") if crash_info else None,
        "policy_profile_severity": None,
    }
    policy_action = decide_policy_action(outcome, artifact_event, crash_info, target_profile, run_history + [current_history_entry])
    current_history_entry["policy_profile_severity"] = policy_action.get("profile_severity")
    policy_execution = apply_policy_action(
        automation_dir,
        run_dir=str(run_dir),
        report_path=str(report_path),
        outcome=outcome,
        artifact_event=artifact_event,
        policy_action=policy_action,
        crash_info=crash_info,
        repo_root=repo_root,
        current_mode=current_mode,
    )

    final_snapshot = metrics_snapshot(
        outcome=outcome,
        metrics=metrics,
        run_dir=run_dir,
        report_path=report_path,
        start=start,
        crash_info=crash_info,
        artifact_event=artifact_event,
        policy_action=policy_action,
        policy_execution=policy_execution,
        target_profile_summary=target_profile_summary,
    )
    write_status(status_path, final_snapshot)
    write_status(current_status_path, final_snapshot)
    history_result = append_run_history(automation_dir, final_snapshot)
    final_snapshot["history_appended"] = history_result.get("appended")
    write_status(status_path, final_snapshot)
    write_status(current_status_path, final_snapshot)

    write_report(
        report_path,
        outcome=outcome,
        repo_root=repo_root,
        run_dir=run_dir,
        command=command,
        exit_code=exit_code,
        metrics=metrics,
        duration_s=duration_s,
        build_log=build_log,
        smoke_log=smoke_log,
        fuzz_log=fuzz_log,
        target_adapter=target_adapter,
        crash_info=crash_info,
        artifact_event=artifact_event,
        policy_action=policy_action,
        policy_execution=policy_execution,
        target_profile_summary=target_profile_summary,
    )

    summary_line = f"cov: {metrics.cov} ft: {metrics.ft} corp: {metrics.corp_units}"
    if target_profile_summary:
        summary_line += (
            f"\nprofile: {target_profile_summary.get('name')}"
            f" mode: {target_profile_summary.get('primary_mode')}"
            f" stages: {target_profile_summary.get('stage_count')}"
        )
    if artifact_event:
        summary_line += f"\ncategory: {artifact_event.get('category')} reason: {artifact_event.get('reason')}"
    if policy_action:
        summary_line += f"\npolicy: {policy_action.get('action_code')} priority: {policy_action.get('priority')} next_mode: {policy_action.get('next_mode')}"
        summary_line += f"\ntriggers: {policy_action.get('matched_triggers')} severity: {policy_action.get('profile_severity')}"
    if policy_execution:
        summary_line += f"\nauto-updated: {policy_execution.get('updated')}"
        if policy_execution.get('regression_trigger'):
            summary_line += f"\nregression-trigger: {policy_execution.get('regression_trigger')}"
    if crash_info and crash_info.get("fingerprint"):
        summary_line += f"\nfingerprint: {crash_info['fingerprint']}"
        summary_line += f"\nduplicate: {crash_info.get('is_duplicate')} count: {crash_info.get('occurrence_count')}"
        summary_line += (
            f"\nstage: {crash_info.get('stage')}"
            f" class: {crash_info.get('stage_class')}"
            f" confidence: {crash_info.get('stage_confidence')}"
        )

    notification_event = send_discord_best_effort(
        "\n".join(
            [
                f"[{target_adapter.notification_label}] {outcome.upper()}",
                summary_line,
                f"report: {report_path}",
            ]
        ),
        context="final-summary",
    )
    final_snapshot = metrics_snapshot(
        outcome=outcome,
        metrics=metrics,
        run_dir=run_dir,
        report_path=report_path,
        start=start,
        crash_info=crash_info,
        artifact_event=artifact_event,
        policy_action=policy_action,
        policy_execution=policy_execution,
        target_profile_summary=target_profile_summary,
        notification_event=notification_event,
    )
    final_snapshot["history_appended"] = history_result.get("appended")
    write_status(status_path, final_snapshot)
    write_status(current_status_path, final_snapshot)
    write_report(
        report_path,
        outcome=outcome,
        repo_root=repo_root,
        run_dir=run_dir,
        command=command,
        exit_code=exit_code,
        metrics=metrics,
        duration_s=duration_s,
        build_log=build_log,
        smoke_log=smoke_log,
        fuzz_log=fuzz_log,
        target_adapter=target_adapter,
        crash_info=crash_info,
        artifact_event=artifact_event,
        policy_action=policy_action,
        policy_execution=policy_execution,
        target_profile_summary=target_profile_summary,
        notification_event=notification_event,
    )
    refresh_llm_evidence_packet_best_effort(repo_root)
    return 0 if outcome in {"ok", "no-progress"} else exit_code or 1


if __name__ == "__main__":
    raise SystemExit(main())
