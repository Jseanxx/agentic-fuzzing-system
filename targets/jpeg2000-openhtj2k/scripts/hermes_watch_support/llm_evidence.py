from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path


REASON_LABELS: dict[str, str] = {
    "build-blocker": "Latest run failed during build; fix the build or harness wiring before fuzzing again.",
    "smoke-invalid-or-harness-mismatch": "Latest run failed during smoke; fix seed validity or harness assumptions before deeper fuzzing.",
    "leak-sanitizer-signal": "The latest run produced a LeakSanitizer-style memory leak; inspect allocation/free closure and harness cleanup before chasing deeper-stage novelty.",
    "no-crash-yet": "The system has not produced a crash yet; bias the next iteration toward stage reach and observability.",
    "no-progress-stall": "The latest run stalled without meaningful progress; inspect why coverage/corpus stopped moving before retrying blindly.",
    "coverage-plateau": "Recent runs show flat coverage despite healthy execution speed; the next iteration should change stage reach rather than just rerun.",
    "corpus-bloat-low-gain": "Corpus size is growing with little signal gain; reseed or redirect the loop instead of letting low-value growth continue.",
    "repeated-crash-family": "The latest crash family is repeating; reduce shallow rediscovery and push toward distinct/deeper signal.",
    "shallow-crash-dominance": "Recent crash signal is still shallow; increase deeper-stage reach instead of replaying shallow-only paths.",
    "shallow-crash-recurrence": "Recent crash history is dominated by shallow-stage crashes; treat this as a stage-reach problem, not as proof of useful progress.",
    "stage-reach-blocked": "The current campaign still looks blocked before the intended deeper stage; bias the next LLM step toward stage advancement.",
    "harness-build-probe-failed": "The latest harness probe could not build cleanly; correct candidate build assumptions first.",
    "harness-smoke-probe-failed": "The latest harness probe built but failed during smoke; revise smoke path and early input assumptions.",
    "guarded-apply-blocked": "The latest guarded apply was blocked by semantics/diff safety; narrow the proposed mutation and keep it within rail.",
    "build-log-memory-safety-signal": "The latest build log already contains sanitizer-style runtime signals; treat the build break as a concrete correctness clue, not just a generic toolchain issue.",
    "fuzz-log-memory-safety-signal": "The latest fuzz log already contains sanitizer-style memory-safety signals; use that body-level clue to guide the next corrective step.",
    "harness-probe-memory-safety-signal": "The latest harness probe output already contains sanitizer-style memory-safety signals; the probe is surfacing a concrete bug shape, not just a pass/fail bit.",
    "apply-comment-scope-mismatch-signal": "The latest guarded apply result explicitly says the candidate escaped the comment-only rail; narrow the mutation scope before trying again.",
}

OBJECTIVE_BY_REASON: dict[str, str] = {
    "build-blocker": "build-fix",
    "smoke-invalid-or-harness-mismatch": "smoke-enable-or-fix",
    "leak-sanitizer-signal": "cleanup-leak-closure",
    "harness-build-probe-failed": "build-fix",
    "harness-smoke-probe-failed": "smoke-enable-or-fix",
    "guarded-apply-blocked": "narrow-next-mutation",
    "build-log-memory-safety-signal": "build-fix",
    "apply-comment-scope-mismatch-signal": "narrow-next-mutation",
    "shallow-crash-dominance": "deeper-stage-reach",
    "shallow-crash-recurrence": "deeper-stage-reach",
    "stage-reach-blocked": "deeper-stage-reach",
    "repeated-crash-family": "deeper-stage-reach",
    "no-progress-stall": "deeper-stage-reach",
    "coverage-plateau": "deeper-stage-reach",
    "corpus-bloat-low-gain": "deeper-stage-reach",
    "no-crash-yet": "stage-reach-or-new-signal",
}

OBJECTIVE_PRIORITY = (
    "build-fix",
    "smoke-enable-or-fix",
    "cleanup-leak-closure",
    "narrow-next-mutation",
    "deeper-stage-reach",
    "stage-reach-or-new-signal",
)

REASON_PRIORITY = (
    "build-blocker",
    "build-log-memory-safety-signal",
    "harness-build-probe-failed",
    "smoke-invalid-or-harness-mismatch",
    "smoke-log-memory-safety-signal",
    "leak-sanitizer-signal",
    "harness-smoke-probe-failed",
    "harness-probe-memory-safety-signal",
    "fuzz-log-memory-safety-signal",
    "guarded-apply-blocked",
    "apply-comment-scope-mismatch-signal",
    "stage-reach-blocked",
    "shallow-crash-dominance",
    "shallow-crash-recurrence",
    "repeated-crash-family",
    "coverage-plateau",
    "corpus-bloat-low-gain",
    "no-progress-stall",
    "no-crash-yet",
)

RAW_SIGNAL_PATTERNS = (
    "LeakSanitizer",
    "AddressSanitizer",
    "UndefinedBehaviorSanitizer",
    "heap-buffer-overflow",
    "stack-buffer-overflow",
    "use-after-free",
    "heap-use-after-free",
    "runtime error:",
    "deadly signal",
)

APPLY_SCOPE_SIGNAL_PATTERNS = (
    "comment-only",
    "requested-code-mutation",
    "code mutation",
    "outside allowed rail",
    "outside comment-only rail",
    "scope mismatch",
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



def _find_duplicate_crash_review(repo_root: Path, current_status: dict[str, object]) -> dict[str, object]:
    policy_action_code = str(current_status.get("policy_action_code") or "")
    repeated_duplicate_context = bool(current_status.get("crash_is_duplicate")) and int(current_status.get("crash_occurrence_count") or 0) >= 2
    if policy_action_code != "review_duplicate_crash_replay" and not repeated_duplicate_context:
        return {}
    registry_path = repo_root / "fuzz-artifacts" / "automation" / "duplicate_crash_reviews.json"
    registry = _load_json(registry_path, {"entries": []})
    entries = registry.get("entries") if isinstance(registry.get("entries"), list) else []
    fingerprint = str(current_status.get("crash_fingerprint") or "")
    run_dir = str(current_status.get("run_dir") or "")
    report_path = str(current_status.get("report") or "")
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if fingerprint and str(entry.get("crash_fingerprint") or "") == fingerprint:
            return dict(entry)
        if run_dir and str(entry.get("run_dir") or "") == run_dir:
            return dict(entry)
        if report_path and str(entry.get("report_path") or "") == report_path:
            return dict(entry)
    return {}



def _slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-") or "target"



def _append_reason(reasons: list[dict[str, object]], *, code: str, summary: str, source: str, evidence: dict[str, object] | None = None) -> None:
    if any(existing.get("code") == code for existing in reasons):
        return
    reasons.append(
        {
            "code": code,
            "summary": summary,
            "source": source,
            "evidence": evidence or {},
        }
    )



def _reason_summary(code: str) -> str:
    return REASON_LABELS.get(code, code)



def _parse_iso_timestamp(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(str(value))
    except ValueError:
        return None



def _classify_stage_depth(stage: str | None) -> str | None:
    text = str(stage or "").lower()
    if not text:
        return None
    if "parse" in text or "header" in text:
        return "shallow"
    if "decode" in text or "cleanup" in text or "tile" in text or "transform" in text:
        return "deep"
    return None



def _match_signal_lines(lines: list[str], patterns: tuple[str, ...], *, limit: int = 8) -> list[str]:
    matched: list[str] = []
    seen: set[str] = set()
    lowered_patterns = tuple(pattern.lower() for pattern in patterns)
    for line in lines:
        normalized = line.strip()
        if not normalized:
            continue
        lowered_line = normalized.lower()
        if any(pattern in lowered_line for pattern in lowered_patterns):
            label = _signal_label(normalized)
            dedup_key = (label or re.sub(r"\s+", " ", lowered_line)).lower()
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            matched.append(normalized)
        if len(matched) >= limit:
            break
    return matched



def _signal_label(line: str) -> str | None:
    lowered = str(line or "").lower()
    if "leaksanitizer" in lowered:
        return "LeakSanitizer"
    if "addresssanitizer" in lowered:
        return "AddressSanitizer"
    if "undefinedbehaviorsanitizer" in lowered:
        return "UndefinedBehaviorSanitizer"
    if "runtime error:" in lowered:
        return "runtime error"
    if "heap-buffer-overflow" in lowered:
        return "heap-buffer-overflow"
    if "stack-buffer-overflow" in lowered:
        return "stack-buffer-overflow"
    if "heap-use-after-free" in lowered:
        return "heap-use-after-free"
    if "use-after-free" in lowered:
        return "use-after-free"
    if "deadly signal" in lowered:
        return "deadly signal"
    return None



def _summarize_signal_lines(lines: list[str], *, limit: int = 3) -> str | None:
    labels: list[str] = []
    seen: set[str] = set()
    for line in lines:
        label = _signal_label(str(line))
        if not label or label in seen:
            continue
        seen.add(label)
        labels.append(label)
        if len(labels) >= limit:
            break
    return ", ".join(labels) if labels else None



def _body_signal_priority(summary: dict[str, object]) -> list[str]:
    ordered = [
        ("smoke_log", int(summary.get("smoke_log_signal_count") or 0)),
        ("build_log", int(summary.get("build_log_signal_count") or 0)),
        ("fuzz_log", int(summary.get("fuzz_log_signal_count") or 0)),
        ("probe", int(summary.get("probe_signal_count") or 0)),
        ("apply", int(summary.get("apply_signal_count") or 0)),
    ]
    return [name for name, count in ordered if count > 0]



def _reason_priority_index(code: str) -> int:
    try:
        return REASON_PRIORITY.index(code)
    except ValueError:
        return len(REASON_PRIORITY)



def _prioritize_failure_reasons(reasons: list[dict[str, object]]) -> list[dict[str, object]]:
    indexed = list(enumerate(reasons))
    indexed.sort(key=lambda item: (_reason_priority_index(str(item[1].get("code") or "")), item[0]))
    return [reason for _, reason in indexed]



def _signal_summary_key_for_reason(code: str) -> tuple[str, str] | None:
    mapping = {
        "build-blocker": ("build_log_signal_summary", "build_log"),
        "build-log-memory-safety-signal": ("build_log_signal_summary", "build_log"),
        "smoke-invalid-or-harness-mismatch": ("smoke_log_signal_summary", "smoke_log"),
        "smoke-log-memory-safety-signal": ("smoke_log_signal_summary", "smoke_log"),
        "fuzz-log-memory-safety-signal": ("fuzz_log_signal_summary", "fuzz_log"),
        "harness-probe-memory-safety-signal": ("probe_signal_summary", "probe"),
        "apply-comment-scope-mismatch-signal": ("apply_signal_summary", "apply"),
    }
    return mapping.get(str(code or ""))



def _explain_failure_reason(reason: dict[str, object], raw_signal_summary: dict[str, object]) -> str:
    code = str(reason.get("code") or "")
    base = str(reason.get("summary") or _reason_summary(code))
    mapping = _signal_summary_key_for_reason(code)
    if not mapping:
        return base
    summary_key, plane = mapping
    signal_summary = str(raw_signal_summary.get(summary_key) or "").strip()
    if not signal_summary:
        return base
    return f"{base} Evidence focus: {summary_key}={signal_summary} from {plane}."



def _annotate_failure_reasons(
    reasons: list[dict[str, object]],
    raw_signal_summary: dict[str, object],
) -> list[dict[str, object]]:
    annotated: list[dict[str, object]] = []
    for reason in reasons:
        enriched = dict(reason)
        enriched["explanation"] = _explain_failure_reason(enriched, raw_signal_summary)
        annotated.append(enriched)
    return annotated



def _build_reason_causal_chain(reason: dict[str, object], raw_signal_summary: dict[str, object]) -> str:
    code = str(reason.get("code") or "")
    source = str(reason.get("source") or "derived")
    evidence = reason.get("evidence") if isinstance(reason.get("evidence"), dict) else {}
    outcome = str(evidence.get("outcome") or evidence.get("artifact_reason") or "").strip()
    mapping = _signal_summary_key_for_reason(code)
    if mapping:
        summary_key, plane = mapping
        signal_summary = str(raw_signal_summary.get(summary_key) or "").strip()
        if signal_summary and outcome:
            return f"{source} => {outcome} => {summary_key}={signal_summary} => {code}"
        if signal_summary:
            return f"{source} => {summary_key}={signal_summary} => {code}"
    if outcome:
        return f"{source} => {outcome} => {code}"
    return f"{source} => {code}"



def _annotate_failure_reason_chains(
    reasons: list[dict[str, object]],
    raw_signal_summary: dict[str, object],
) -> list[dict[str, object]]:
    annotated: list[dict[str, object]] = []
    for reason in reasons:
        enriched = dict(reason)
        enriched["causal_chain"] = _build_reason_causal_chain(enriched, raw_signal_summary)
        annotated.append(enriched)
    return annotated



def _reason_narrative_role(index: int) -> str:
    if index <= 0:
        return "primary"
    if index == 1:
        return "supporting"
    return "deferred"



def _build_top_failure_reason_narrative_steps(reasons: list[dict[str, object]]) -> list[dict[str, object]]:
    steps: list[dict[str, object]] = []
    for idx, reason in enumerate(reasons[:3]):
        code = str(reason.get("code") or "")
        role = _reason_narrative_role(idx)
        explanation = str(reason.get("explanation") or reason.get("summary") or "")
        causal_chain = str(reason.get("causal_chain") or explanation or code)
        if role == "primary":
            narrative = f"primary {code} sets the first corrective frame because {explanation}"
        elif role == "supporting":
            narrative = f"supporting {code} sharpens or corroborates that frame via {causal_chain}"
        else:
            narrative = f"deferred {code} remains a lower-priority tension via {causal_chain}"
        steps.append(
            {
                "role": role,
                "code": code,
                "narrative": narrative,
                "explanation": explanation,
                "causal_chain": causal_chain,
            }
        )
    return steps



def _build_top_failure_reason_narrative(reasons: list[dict[str, object]]) -> str:
    steps = _build_top_failure_reason_narrative_steps(reasons)
    if not steps:
        return "no explicit multi-reason narrative was extracted"
    return "; ".join(str(step.get("narrative") or "") for step in steps if str(step.get("narrative") or "").strip())



def _summarize_finding_efficiency(current_status: dict[str, object], run_history: list[dict[str, object]], failure_reason_codes: list[str]) -> dict[str, object]:
    window = _history_window(run_history, minimum=4)
    cov_values = [float(entry.get("cov")) for entry in window if entry.get("cov") is not None]
    corpus_values = [int(entry.get("corpus_units") or 0) for entry in window if entry.get("corpus_units") is not None]
    fingerprint_values = [str(entry.get("crash_fingerprint") or "") for entry in window if str(entry.get("crash_fingerprint") or "").strip()]
    coverage_delta = round((cov_values[-1] - cov_values[0]), 3) if len(cov_values) >= 2 else None
    corpus_growth = (corpus_values[-1] - corpus_values[0]) if len(corpus_values) >= 2 else None
    unique_crash_fingerprints = len(set(fingerprint_values)) if fingerprint_values else 0
    weak_signals: list[str] = []
    if "coverage-plateau" in failure_reason_codes:
        weak_signals.append("coverage plateau under healthy exec/s")
    if "corpus-bloat-low-gain" in failure_reason_codes:
        weak_signals.append("corpus growth with low gain")
    if "shallow-crash-recurrence" in failure_reason_codes or "shallow-crash-dominance" in failure_reason_codes:
        weak_signals.append("shallow crash dominance")
    if "repeated-crash-family" in failure_reason_codes:
        weak_signals.append("repeated crash family with low novelty")
    status = "weak" if weak_signals else "healthy"
    recommendation = "bias-llm-toward-novelty-and-stage-reach" if weak_signals else "maintain-current-loop-and-collect-more-signal"
    summary = "; ".join(weak_signals) if weak_signals else "recent run history does not yet show an obvious finding-efficiency bottleneck"
    return {
        "status": status,
        "summary": summary,
        "coverage_delta": coverage_delta,
        "corpus_growth": corpus_growth,
        "unique_crash_fingerprints": unique_crash_fingerprints,
        "recent_window_size": len(window),
        "weak_signals": weak_signals,
        "recommendation": recommendation,
    }



def _link_objective_to_routing(
    llm_objective: str,
    failure_reason_codes: list[str],
    finding_efficiency_recommendation: str,
    top_failure_reason_narrative: str,
    current_status: dict[str, object] | None = None,
) -> dict[str, str]:
    action_code = "halt_and_review_harness"
    candidate_route = "review-current-candidate"
    current_status = current_status if isinstance(current_status, dict) else {}
    deep_stage_already_reached = bool(current_status.get("crash_detected")) and str(current_status.get("outcome") or "") == "crash" and (
        str(current_status.get("policy_profile_severity") or "") in {"high", "critical"}
        or str(current_status.get("crash_stage_class") or "") == "deep"
        or int(current_status.get("crash_stage_depth_rank") or 0) >= 3
    )
    override_reason = None
    if deep_stage_already_reached and llm_objective in {"deeper-stage-reach", "stage-reach-or-new-signal"}:
        action_code = "halt_and_review_harness"
        candidate_route = "review-current-candidate"
        override_reason = "deep-stage-crash-already-reached"
    elif llm_objective == "deeper-stage-reach":
        action_code = "shift_weight_to_deeper_harness"
        candidate_route = "promote-next-depth"
    elif llm_objective == "stage-reach-or-new-signal":
        if "corpus-bloat-low-gain" in failure_reason_codes:
            action_code = "minimize_and_reseed"
            candidate_route = "reseed-before-retry"
        else:
            action_code = "shift_weight_to_deeper_harness"
            candidate_route = "promote-next-depth"
    summary = (
        f"llm objective {llm_objective} links to {action_code} / {candidate_route}; "
        f"finding recommendation={finding_efficiency_recommendation}; "
        f"top failure narrative={top_failure_reason_narrative}"
    )
    if override_reason:
        summary += f"; override={override_reason}"
    return {
        "suggested_action_code": action_code,
        "suggested_candidate_route": candidate_route,
        "objective_routing_linkage_summary": summary,
    }


def _duplicate_replay_routing_override(duplicate_crash_review: dict[str, object]) -> dict[str, str] | None:
    if not isinstance(duplicate_crash_review, dict) or not duplicate_crash_review:
        return None
    if str(duplicate_crash_review.get("replay_execution_status") or "") != "completed":
        return None
    first_exit = duplicate_crash_review.get("first_replay_exit_code")
    latest_exit = duplicate_crash_review.get("latest_replay_exit_code")
    if first_exit in {None, 0} or latest_exit in {None, 0}:
        return None
    if bool(duplicate_crash_review.get("replay_artifact_bytes_equal")):
        return None
    first_signature = duplicate_crash_review.get("first_replay_signature") if isinstance(duplicate_crash_review.get("first_replay_signature"), dict) else {}
    latest_signature = duplicate_crash_review.get("latest_replay_signature") if isinstance(duplicate_crash_review.get("latest_replay_signature"), dict) else {}
    first_fingerprint = str(first_signature.get("fingerprint") or "")
    latest_fingerprint = str(latest_signature.get("fingerprint") or "")
    crash_fingerprint = str(duplicate_crash_review.get("crash_fingerprint") or "")
    first_location = str(first_signature.get("location") or duplicate_crash_review.get("crash_location") or "")
    latest_location = str(latest_signature.get("location") or duplicate_crash_review.get("crash_location") or "")
    if not first_fingerprint or first_fingerprint != latest_fingerprint:
        return None
    if first_location and latest_location and first_location != latest_location:
        return None
    if crash_fingerprint and first_fingerprint != crash_fingerprint:
        crash_location = str(duplicate_crash_review.get("crash_location") or "")
        if not crash_location or first_location != crash_location:
            return None
    summary = (
        "stable duplicate replay across distinct artifacts confirms the same crash family; "
        "prefer bounded minimization and reseed planning before another blind rerun"
    )
    return {
        "suggested_action_code": "minimize_and_reseed",
        "suggested_candidate_route": "reseed-before-retry",
        "objective_routing_linkage_summary": summary,
    }



def _text_lines(value: object) -> list[str]:
    if isinstance(value, str):
        return value.splitlines()
    if isinstance(value, list):
        lines: list[str] = []
        for item in value:
            if isinstance(item, str):
                lines.extend(item.splitlines())
        return lines
    return []



def _history_window(history: list[dict[str, object]], *, minimum: int = 4) -> list[dict[str, object]]:
    recent = [entry for entry in history if _parse_iso_timestamp(str(entry.get("updated_at") or "")) is not None]
    recent.sort(key=lambda item: _parse_iso_timestamp(str(item.get("updated_at") or "")) or dt.datetime.min)
    return recent[-minimum:] if len(recent) >= minimum else []



def _semantic_history_summary(history: list[dict[str, object]]) -> dict[str, object]:
    crash_entries = [entry for entry in history if entry.get("outcome") == "crash"]
    stage_counts: dict[str, int] = {}
    deep_crash_count = 0
    shallow_crash_count = 0
    for entry in crash_entries:
        stage = str(entry.get("crash_stage") or "")
        if not stage:
            continue
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
        depth = _classify_stage_depth(stage)
        if depth == "deep":
            deep_crash_count += 1
        elif depth == "shallow":
            shallow_crash_count += 1
    total_crashes = len(crash_entries)
    dominant_stage = max(stage_counts.items(), key=lambda item: item[1])[0] if stage_counts else None
    return {
        "total_crashes": total_crashes,
        "deep_crash_count": deep_crash_count,
        "shallow_crash_count": shallow_crash_count,
        "deep_ratio": (deep_crash_count / total_crashes) if total_crashes else 0.0,
        "shallow_ratio": (shallow_crash_count / total_crashes) if total_crashes else 0.0,
        "dominant_stage": dominant_stage,
        "stage_counts": stage_counts,
    }



def _extract_raw_log_signals(
    current_status: dict[str, object],
    probe_manifest: dict[str, object] | None = None,
    apply_result: dict[str, object] | None = None,
) -> dict[str, object]:
    report_path = Path(str(current_status.get("report") or "")) if current_status.get("report") else None
    smoke_log_path = report_path.with_name("smoke.log") if report_path else None
    build_log_path = report_path.with_name("build.log") if report_path else None
    fuzz_log_path = report_path.with_name("fuzz.log") if report_path else None

    def read_lines(path: Path | None) -> list[str]:
        if path is None or not path.exists():
            return []
        return path.read_text(encoding="utf-8", errors="replace").splitlines()

    smoke_signals = _match_signal_lines(read_lines(smoke_log_path), RAW_SIGNAL_PATTERNS)
    build_signals = _match_signal_lines(read_lines(build_log_path), RAW_SIGNAL_PATTERNS)
    fuzz_signals = _match_signal_lines(read_lines(fuzz_log_path), RAW_SIGNAL_PATTERNS)

    probe_manifest = probe_manifest if isinstance(probe_manifest, dict) else {}
    build_probe = probe_manifest.get("build_probe_result") if isinstance(probe_manifest.get("build_probe_result"), dict) else {}
    smoke_probe = probe_manifest.get("smoke_probe_result") if isinstance(probe_manifest.get("smoke_probe_result"), dict) else {}
    probe_lines = _text_lines(build_probe.get("output")) + _text_lines(smoke_probe.get("output"))
    probe_signals = _match_signal_lines(probe_lines, RAW_SIGNAL_PATTERNS)

    apply_result = apply_result if isinstance(apply_result, dict) else {}
    apply_lines = (
        _text_lines(apply_result.get("candidate_semantics_summary"))
        + _text_lines(apply_result.get("verification_summary"))
        + _text_lines(apply_result.get("candidate_semantics_reasons"))
        + _text_lines(apply_result.get("diff_safety_reasons"))
    )
    apply_signals = _match_signal_lines(apply_lines, APPLY_SCOPE_SIGNAL_PATTERNS)

    summary = {
        "smoke_log_path": str(smoke_log_path) if smoke_log_path and smoke_log_path.exists() else None,
        "build_log_path": str(build_log_path) if build_log_path and build_log_path.exists() else None,
        "fuzz_log_path": str(fuzz_log_path) if fuzz_log_path and fuzz_log_path.exists() else None,
        "smoke_log_signals": smoke_signals,
        "build_log_signals": build_signals,
        "fuzz_log_signals": fuzz_signals,
        "smoke_log_signal_count": len(smoke_signals),
        "build_log_signal_count": len(build_signals),
        "fuzz_log_signal_count": len(fuzz_signals),
        "probe_signals": probe_signals,
        "probe_signal_count": len(probe_signals),
        "apply_signals": apply_signals,
        "apply_signal_count": len(apply_signals),
        "smoke_log_signal_summary": _summarize_signal_lines(smoke_signals),
        "build_log_signal_summary": _summarize_signal_lines(build_signals),
        "fuzz_log_signal_summary": _summarize_signal_lines(fuzz_signals),
        "probe_signal_summary": _summarize_signal_lines(probe_signals),
        "apply_signal_summary": _summarize_signal_lines(apply_signals),
    }
    summary["body_signal_priority"] = _body_signal_priority(summary)
    return summary



def _extract_history_failure_reasons(
    current_status: dict[str, object],
    run_history: list[dict[str, object]],
) -> list[dict[str, object]]:
    reasons: list[dict[str, object]] = []
    outcome = str(current_status.get("outcome") or "")
    artifact_reason = str(current_status.get("artifact_reason") or "")
    seconds_since_progress = float(current_status.get("seconds_since_progress") or 0)
    primary_mode = str(current_status.get("target_profile_primary_mode") or "")
    window = _history_window(run_history, minimum=4)

    if outcome == "no-progress" or artifact_reason == "stalled-coverage-or-corpus":
        _append_reason(
            reasons,
            code="no-progress-stall",
            summary=_reason_summary("no-progress-stall"),
            source="current_status",
            evidence={
                "outcome": outcome,
                "artifact_reason": artifact_reason,
                "seconds_since_progress": seconds_since_progress,
            },
        )

    if window:
        first_ts = _parse_iso_timestamp(str(window[0].get("updated_at") or ""))
        last_ts = _parse_iso_timestamp(str(window[-1].get("updated_at") or ""))
        elapsed_minutes = ((last_ts - first_ts).total_seconds() / 60.0) if first_ts and last_ts else 0.0
        cov_values = [entry.get("cov") for entry in window if entry.get("cov") is not None]
        exec_values = [int(entry.get("exec_per_second") or 0) for entry in window]
        corpus_values = [int(entry.get("corpus_units") or 0) for entry in window if entry.get("corpus_units") is not None]

        if len(cov_values) == len(window) and len(set(cov_values)) == 1 and exec_values and min(exec_values) >= 200 and elapsed_minutes >= 60:
            _append_reason(
                reasons,
                code="coverage-plateau",
                summary=_reason_summary("coverage-plateau"),
                source="run_history",
                evidence={
                    "elapsed_minutes": round(elapsed_minutes, 1),
                    "cov_values": cov_values,
                    "exec_values": exec_values,
                },
            )

        if len(corpus_values) == len(window) and len(cov_values) == len(window):
            corpus_growth = corpus_values[-1] - corpus_values[0]
            coverage_gain = float(cov_values[-1]) - float(cov_values[0])
            if corpus_growth >= 100 and coverage_gain <= 0.5:
                _append_reason(
                    reasons,
                    code="corpus-bloat-low-gain",
                    summary=_reason_summary("corpus-bloat-low-gain"),
                    source="run_history",
                    evidence={
                        "corpus_growth": corpus_growth,
                        "coverage_gain": round(coverage_gain, 3),
                    },
                )

    semantic = _semantic_history_summary(run_history)
    if semantic.get("total_crashes") and float(semantic.get("shallow_ratio") or 0.0) >= 0.75:
        _append_reason(
            reasons,
            code="shallow-crash-recurrence",
            summary=_reason_summary("shallow-crash-recurrence"),
            source="run_history",
            evidence={
                "dominant_stage": semantic.get("dominant_stage"),
                "shallow_ratio": semantic.get("shallow_ratio"),
                "stage_counts": semantic.get("stage_counts"),
            },
        )

    if primary_mode.startswith("deep") and any(
        code in {"no-progress-stall", "coverage-plateau", "corpus-bloat-low-gain", "shallow-crash-recurrence", "no-crash-yet"}
        for code in [str(reason.get("code") or "") for reason in reasons]
    ):
        _append_reason(
            reasons,
            code="stage-reach-blocked",
            summary=_reason_summary("stage-reach-blocked"),
            source="derived",
            evidence={
                "target_profile_primary_mode": primary_mode,
                "dominant_stage": semantic.get("dominant_stage"),
            },
        )

    return reasons



def _extract_failure_reasons(
    current_status: dict[str, object],
    probe_feedback: dict[str, object],
    apply_result: dict[str, object],
    run_history: list[dict[str, object]] | None = None,
    raw_signal_summary: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    reasons: list[dict[str, object]] = []
    outcome = str(current_status.get("outcome") or "")
    artifact_reason = str(current_status.get("artifact_reason") or "")

    if outcome == "build-failed":
        _append_reason(
            reasons,
            code="build-blocker",
            summary=_reason_summary("build-blocker"),
            source="current_status",
            evidence={"outcome": outcome, "artifact_reason": artifact_reason},
        )
    if outcome == "smoke-failed":
        _append_reason(
            reasons,
            code="smoke-invalid-or-harness-mismatch",
            summary=_reason_summary("smoke-invalid-or-harness-mismatch"),
            source="current_status",
            evidence={"outcome": outcome, "artifact_reason": artifact_reason},
        )
    leak_signal_detected = False
    if str(current_status.get("artifact_category") or "") == "leak" or str(current_status.get("artifact_reason") or "") == "sanitizer-leak" or str(current_status.get("crash_kind") or "") == "leak":
        leak_signal_detected = True
    if raw_signal_summary and any("LeakSanitizer" in str(line) for line in raw_signal_summary.get("fuzz_log_signals") or []):
        leak_signal_detected = True
    if not leak_signal_detected and "leaked in" in str(current_status.get("crash_summary") or "").lower():
        leak_signal_detected = True
    if leak_signal_detected:
        _append_reason(
            reasons,
            code="leak-sanitizer-signal",
            summary=_reason_summary("leak-sanitizer-signal"),
            source="current_status",
            evidence={
                "outcome": outcome,
                "artifact_reason": artifact_reason,
                "crash_kind": current_status.get("crash_kind"),
                "crash_summary": current_status.get("crash_summary"),
                "fuzz_log_signals": raw_signal_summary.get("fuzz_log_signals") if raw_signal_summary else None,
            },
        )
    if not bool(current_status.get("crash_detected")):
        _append_reason(
            reasons,
            code="no-crash-yet",
            summary=_reason_summary("no-crash-yet"),
            source="current_status",
            evidence={"outcome": outcome, "artifact_reason": artifact_reason},
        )
    crash_occurrence_count = int(current_status.get("crash_occurrence_count") or 0)
    if crash_occurrence_count > 1:
        _append_reason(
            reasons,
            code="repeated-crash-family",
            summary=_reason_summary("repeated-crash-family"),
            source="current_status",
            evidence={
                "crash_occurrence_count": crash_occurrence_count,
                "crash_fingerprint": current_status.get("crash_fingerprint"),
            },
        )
    if str(current_status.get("crash_stage_class") or "") == "shallow":
        _append_reason(
            reasons,
            code="shallow-crash-dominance",
            summary=_reason_summary("shallow-crash-dominance"),
            source="current_status",
            evidence={
                "crash_stage": current_status.get("crash_stage"),
                "crash_stage_class": current_status.get("crash_stage_class"),
                "crash_stage_depth_rank": current_status.get("crash_stage_depth_rank"),
            },
        )

    bridge_reason = str(probe_feedback.get("bridge_reason") or "")
    if bridge_reason == "build-probe-failed":
        _append_reason(
            reasons,
            code="harness-build-probe-failed",
            summary=_reason_summary("harness-build-probe-failed"),
            source="probe_feedback",
            evidence={
                "bridge_reason": bridge_reason,
                "action_code": probe_feedback.get("action_code"),
                "candidate_id": probe_feedback.get("candidate_id"),
            },
        )
    if bridge_reason == "smoke-probe-failed":
        _append_reason(
            reasons,
            code="harness-smoke-probe-failed",
            summary=_reason_summary("harness-smoke-probe-failed"),
            source="probe_feedback",
            evidence={
                "bridge_reason": bridge_reason,
                "action_code": probe_feedback.get("action_code"),
                "candidate_id": probe_feedback.get("candidate_id"),
            },
        )

    if str(apply_result.get("apply_status") or "") == "blocked":
        _append_reason(
            reasons,
            code="guarded-apply-blocked",
            summary=_reason_summary("guarded-apply-blocked"),
            source="apply_result",
            evidence={
                "candidate_semantics_status": apply_result.get("candidate_semantics_status"),
                "candidate_semantics_reasons": apply_result.get("candidate_semantics_reasons"),
                "diff_safety_status": apply_result.get("diff_safety_status"),
            },
        )

    if raw_signal_summary and int(raw_signal_summary.get("smoke_log_signal_count") or 0) > 0:
        _append_reason(
            reasons,
            code="smoke-log-memory-safety-signal",
            summary="The latest smoke log already contains sanitizer-style memory-safety signals; treat this as a concrete debugging clue, not just a generic smoke failure.",
            source="smoke_log",
            evidence={
                "smoke_log_path": raw_signal_summary.get("smoke_log_path"),
                "smoke_log_signals": raw_signal_summary.get("smoke_log_signals"),
            },
        )

    if raw_signal_summary and int(raw_signal_summary.get("build_log_signal_count") or 0) > 0:
        _append_reason(
            reasons,
            code="build-log-memory-safety-signal",
            summary=_reason_summary("build-log-memory-safety-signal"),
            source="build_log",
            evidence={
                "build_log_path": raw_signal_summary.get("build_log_path"),
                "build_log_signals": raw_signal_summary.get("build_log_signals"),
            },
        )

    if raw_signal_summary and int(raw_signal_summary.get("fuzz_log_signal_count") or 0) > 0:
        _append_reason(
            reasons,
            code="fuzz-log-memory-safety-signal",
            summary=_reason_summary("fuzz-log-memory-safety-signal"),
            source="fuzz_log",
            evidence={
                "fuzz_log_path": raw_signal_summary.get("fuzz_log_path"),
                "fuzz_log_signals": raw_signal_summary.get("fuzz_log_signals"),
            },
        )

    if raw_signal_summary and int(raw_signal_summary.get("probe_signal_count") or 0) > 0:
        _append_reason(
            reasons,
            code="harness-probe-memory-safety-signal",
            summary=_reason_summary("harness-probe-memory-safety-signal"),
            source="probe_manifest",
            evidence={
                "probe_signals": raw_signal_summary.get("probe_signals"),
            },
        )

    if raw_signal_summary and int(raw_signal_summary.get("apply_signal_count") or 0) > 0:
        _append_reason(
            reasons,
            code="apply-comment-scope-mismatch-signal",
            summary=_reason_summary("apply-comment-scope-mismatch-signal"),
            source="apply_result",
            evidence={
                "apply_signals": raw_signal_summary.get("apply_signals"),
            },
        )

    history_reasons = _extract_history_failure_reasons(current_status, list(run_history or []))
    for reason in history_reasons:
        _append_reason(
            reasons,
            code=str(reason.get("code") or ""),
            summary=str(reason.get("summary") or ""),
            source=str(reason.get("source") or "derived"),
            evidence=reason.get("evidence") if isinstance(reason.get("evidence"), dict) else {},
        )

    return reasons



def _choose_llm_objective(reasons: list[dict[str, object]]) -> str:
    present = {OBJECTIVE_BY_REASON.get(str(reason.get("code") or "")) for reason in reasons}
    for objective in OBJECTIVE_PRIORITY:
        if objective in present:
            return objective
    return "stage-reach-or-new-signal"



def build_llm_evidence_packet(repo_root: Path) -> dict[str, object]:
    current_status_path = repo_root / "fuzz-artifacts" / "current_status.json"
    current_status = _load_json(current_status_path, {})

    probe_feedback_dir = repo_root / "fuzz-records" / "probe-feedback"
    probe_feedback_path = _latest_file(probe_feedback_dir, "*-probe-feedback.json")
    probe_feedback = _load_json(probe_feedback_path, {}) if probe_feedback_path else {}

    run_history_path = repo_root / "fuzz-artifacts" / "automation" / "run_history.json"
    run_history_registry = _load_json(run_history_path, {"entries": []})
    run_history = run_history_registry.get("entries") if isinstance(run_history_registry.get("entries"), list) else []

    probe_dir = repo_root / "fuzz-records" / "harness-probes"
    probe_manifest_path = _latest_file(probe_dir, "*-harness-probe.json")
    probe_manifest = _load_json(probe_manifest_path, {}) if probe_manifest_path else {}

    apply_candidate_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
    apply_candidate_path = _latest_file(apply_candidate_dir, "*-harness-apply-candidate.json")
    apply_candidate = _load_json(apply_candidate_path, {}) if apply_candidate_path else {}

    apply_result_dir = repo_root / "fuzz-records" / "harness-apply-results"
    apply_result_path = _latest_file(apply_result_dir, "*-harness-apply-result.json")
    apply_result = _load_json(apply_result_path, {}) if apply_result_path else {}

    raw_signal_summary = _extract_raw_log_signals(current_status, probe_manifest, apply_result)
    duplicate_crash_review = _find_duplicate_crash_review(repo_root, current_status)

    failure_reasons = _extract_failure_reasons(current_status, probe_feedback, apply_result, run_history, raw_signal_summary)
    failure_reasons = _prioritize_failure_reasons(failure_reasons)
    failure_reasons = _annotate_failure_reasons(failure_reasons, raw_signal_summary)
    failure_reasons = _annotate_failure_reason_chains(failure_reasons, raw_signal_summary)
    top_failure_reason_narrative_steps = _build_top_failure_reason_narrative_steps(failure_reasons)
    top_failure_reason_narrative = _build_top_failure_reason_narrative(failure_reasons)
    failure_reason_codes = [str(reason.get("code") or "") for reason in failure_reasons]
    finding_efficiency_summary = _summarize_finding_efficiency(current_status, run_history, failure_reason_codes)
    finding_efficiency_recommendation = str(finding_efficiency_summary.get("recommendation") or "maintain-current-loop-and-collect-more-signal")
    llm_objective = _choose_llm_objective(failure_reasons)
    objective_routing_linkage = _link_objective_to_routing(
        llm_objective,
        failure_reason_codes,
        finding_efficiency_recommendation,
        top_failure_reason_narrative,
        current_status,
    )
    duplicate_replay_override = _duplicate_replay_routing_override(duplicate_crash_review)
    if duplicate_replay_override:
        objective_routing_linkage = dict(duplicate_replay_override)
    project = str(
        current_status.get("target_profile_project")
        or probe_feedback.get("generated_from_project")
        or probe_manifest.get("generated_from_project")
        or repo_root.name
    )

    packet = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "generated_from_project": project,
        "llm_objective": llm_objective,
        "failure_reasons": failure_reasons,
        "failure_reason_codes": failure_reason_codes,
        "top_failure_reason_codes": [str(reason.get("code") or "") for reason in failure_reasons[:3]],
        "top_failure_reason_explanations": [
            {"code": str(reason.get("code") or ""), "explanation": str(reason.get("explanation") or reason.get("summary") or "")}
            for reason in failure_reasons[:3]
        ],
        "top_failure_reason_chains": [
            {"code": str(reason.get("code") or ""), "causal_chain": str(reason.get("causal_chain") or reason.get("explanation") or reason.get("summary") or "")}
            for reason in failure_reasons[:3]
        ],
        "top_failure_reason_narrative_steps": top_failure_reason_narrative_steps,
        "top_failure_reason_narrative": top_failure_reason_narrative,
        "finding_efficiency_summary": finding_efficiency_summary,
        "finding_efficiency_recommendation": finding_efficiency_recommendation,
        "suggested_action_code": objective_routing_linkage.get("suggested_action_code"),
        "suggested_candidate_route": objective_routing_linkage.get("suggested_candidate_route"),
        "objective_routing_linkage_summary": objective_routing_linkage.get("objective_routing_linkage_summary"),
        "current_status_path": str(current_status_path),
        "current_status": current_status,
        "probe_feedback_manifest_path": str(probe_feedback_path) if probe_feedback_path else None,
        "probe_feedback": probe_feedback,
        "run_history_path": str(run_history_path),
        "run_history": run_history,
        "probe_manifest_path": str(probe_manifest_path) if probe_manifest_path else None,
        "probe_manifest": probe_manifest,
        "raw_signal_summary": raw_signal_summary,
        "duplicate_crash_review": duplicate_crash_review,
        "apply_candidate_manifest_path": str(apply_candidate_path) if apply_candidate_path else None,
        "apply_candidate": apply_candidate,
        "apply_result_manifest_path": str(apply_result_path) if apply_result_path else None,
        "apply_result": apply_result,
        "suggested_next_inputs": [
            "latest build/smoke/fuzz outcome",
            "top failure reasons with evidence",
            "latest harness probe/apply lineage",
            "target scope and bounded action expectations",
        ],
    }
    if duplicate_crash_review:
        packet["suggested_next_inputs"].append("duplicate crash review plan and lineage")
    return packet



def render_llm_evidence_markdown(packet: dict[str, object]) -> str:
    reasons = packet.get("failure_reasons") if isinstance(packet.get("failure_reasons"), list) else []
    current_status = packet.get("current_status") if isinstance(packet.get("current_status"), dict) else {}
    probe_feedback = packet.get("probe_feedback") if isinstance(packet.get("probe_feedback"), dict) else {}
    apply_result = packet.get("apply_result") if isinstance(packet.get("apply_result"), dict) else {}
    run_history = packet.get("run_history") if isinstance(packet.get("run_history"), list) else []
    raw_signal_summary = packet.get("raw_signal_summary") if isinstance(packet.get("raw_signal_summary"), dict) else {}
    duplicate_crash_review = packet.get("duplicate_crash_review") if isinstance(packet.get("duplicate_crash_review"), dict) else {}
    lines = [
        "# LLM Evidence Packet",
        "",
        f"- generated_from_project: {packet.get('generated_from_project')}",
        f"- generated_at: {packet.get('generated_at')}",
        f"- llm_objective: {packet.get('llm_objective')}",
        f"- top_failure_reason_codes: {packet.get('top_failure_reason_codes')}",
        f"- top_failure_reason_explanations: {packet.get('top_failure_reason_explanations')}",
        f"- top_failure_reason_chains: {packet.get('top_failure_reason_chains')}",
        f"- top_failure_reason_narrative_steps: {packet.get('top_failure_reason_narrative_steps')}",
        f"- top_failure_reason_narrative: {packet.get('top_failure_reason_narrative')}",
        f"- finding_efficiency_summary: {packet.get('finding_efficiency_summary')}",
        f"- finding_efficiency_recommendation: {packet.get('finding_efficiency_recommendation')}",
        f"- suggested_action_code: {packet.get('suggested_action_code')}",
        f"- suggested_candidate_route: {packet.get('suggested_candidate_route')}",
        f"- objective_routing_linkage_summary: {packet.get('objective_routing_linkage_summary')}",
        f"- current_status_path: {packet.get('current_status_path')}",
        f"- probe_feedback_manifest_path: {packet.get('probe_feedback_manifest_path')}",
        f"- run_history_path: {packet.get('run_history_path')}",
        f"- probe_manifest_path: {packet.get('probe_manifest_path')}",
        f"- apply_candidate_manifest_path: {packet.get('apply_candidate_manifest_path')}",
        f"- apply_result_manifest_path: {packet.get('apply_result_manifest_path')}",
        "",
        "## Current Status",
        "",
        f"- outcome: {current_status.get('outcome')}",
        f"- artifact_reason: {current_status.get('artifact_reason')}",
        f"- crash_detected: {current_status.get('crash_detected')}",
        f"- crash_fingerprint: {current_status.get('crash_fingerprint')}",
        f"- crash_stage: {current_status.get('crash_stage')}",
        f"- target_profile_primary_mode: {current_status.get('target_profile_primary_mode')}",
        "",
        "## Failure Reasons",
        "",
    ]
    if reasons:
        for reason in reasons:
            lines.append(f"- {reason.get('code')}: {reason.get('summary')}")
    else:
        lines.append("- none: no explicit failure reason was extracted; inspect raw artifacts.")
    lines.extend(
        [
            "",
            "## Latest Probe Feedback",
            "",
            f"- action_code: {probe_feedback.get('action_code')}",
            f"- bridge_reason: {probe_feedback.get('bridge_reason')}",
            f"- candidate_id: {probe_feedback.get('candidate_id')}",
            f"- smoke_probe_status: {probe_feedback.get('smoke_probe_status')}",
            "",
            "## Latest Apply Result",
            "",
            f"- apply_status: {apply_result.get('apply_status')}",
            f"- candidate_semantics_status: {apply_result.get('candidate_semantics_status')}",
            f"- candidate_semantics_reasons: {apply_result.get('candidate_semantics_reasons')}",
            f"- diff_safety_status: {apply_result.get('diff_safety_status')}",
            "",
            "## Recent Run History",
            "",
            f"- run_history_entries: {len(run_history)}",
            f"- last_run_outcome: {(run_history[-1] if run_history else {}).get('outcome') if run_history else None}",
            f"- last_run_cov: {(run_history[-1] if run_history else {}).get('cov') if run_history else None}",
            f"- last_run_corpus_units: {(run_history[-1] if run_history else {}).get('corpus_units') if run_history else None}",
            "",
            "## Raw Log Signals",
            "",
            f"- smoke_log_path: {raw_signal_summary.get('smoke_log_path')}",
            f"- smoke_log_signal_count: {raw_signal_summary.get('smoke_log_signal_count')}",
            f"- smoke_log_signals: {raw_signal_summary.get('smoke_log_signals')}",
            f"- smoke_log_signal_summary: {raw_signal_summary.get('smoke_log_signal_summary')}",
            f"- build_log_signal_count: {raw_signal_summary.get('build_log_signal_count')}",
            f"- build_log_signals: {raw_signal_summary.get('build_log_signals')}",
            f"- build_log_signal_summary: {raw_signal_summary.get('build_log_signal_summary')}",
            f"- fuzz_log_signal_count: {raw_signal_summary.get('fuzz_log_signal_count')}",
            f"- fuzz_log_signals: {raw_signal_summary.get('fuzz_log_signals')}",
            f"- fuzz_log_signal_summary: {raw_signal_summary.get('fuzz_log_signal_summary')}",
            f"- probe_signal_count: {raw_signal_summary.get('probe_signal_count')}",
            f"- probe_signals: {raw_signal_summary.get('probe_signals')}",
            f"- probe_signal_summary: {raw_signal_summary.get('probe_signal_summary')}",
            f"- apply_signal_count: {raw_signal_summary.get('apply_signal_count')}",
            f"- apply_signals: {raw_signal_summary.get('apply_signals')}",
            f"- apply_signal_summary: {raw_signal_summary.get('apply_signal_summary')}",
            f"- body_signal_priority: {raw_signal_summary.get('body_signal_priority')}",
            "",
            "## Duplicate Crash Review",
            "",
            f"- action_code: {duplicate_crash_review.get('action_code')}",
            f"- status: {duplicate_crash_review.get('status')}",
            f"- occurrence_count: {duplicate_crash_review.get('occurrence_count')}",
            f"- first_seen_run: {duplicate_crash_review.get('first_seen_run')}",
            f"- last_seen_run: {duplicate_crash_review.get('last_seen_run')}",
            f"- executor_plan_path: {duplicate_crash_review.get('executor_plan_path')}",
            f"- replay_execution_status: {duplicate_crash_review.get('replay_execution_status')}",
            f"- replay_execution_markdown_path: {duplicate_crash_review.get('replay_execution_markdown_path')}",
            f"- first_replay_exit_code: {duplicate_crash_review.get('first_replay_exit_code')}",
            f"- latest_replay_exit_code: {duplicate_crash_review.get('latest_replay_exit_code')}",
            f"- artifact_paths: {duplicate_crash_review.get('artifact_paths')}",
            "",
            "## Finding Efficiency",
            "",
            f"- status: {(packet.get('finding_efficiency_summary') or {}).get('status') if isinstance(packet.get('finding_efficiency_summary'), dict) else None}",
            f"- summary: {(packet.get('finding_efficiency_summary') or {}).get('summary') if isinstance(packet.get('finding_efficiency_summary'), dict) else None}",
            f"- coverage_delta: {(packet.get('finding_efficiency_summary') or {}).get('coverage_delta') if isinstance(packet.get('finding_efficiency_summary'), dict) else None}",
            f"- corpus_growth: {(packet.get('finding_efficiency_summary') or {}).get('corpus_growth') if isinstance(packet.get('finding_efficiency_summary'), dict) else None}",
            f"- unique_crash_fingerprints: {(packet.get('finding_efficiency_summary') or {}).get('unique_crash_fingerprints') if isinstance(packet.get('finding_efficiency_summary'), dict) else None}",
            f"- weak_signals: {(packet.get('finding_efficiency_summary') or {}).get('weak_signals') if isinstance(packet.get('finding_efficiency_summary'), dict) else None}",
            f"- finding_efficiency_recommendation: {packet.get('finding_efficiency_recommendation')}",
            "",
            "## Suggested LLM Use",
            "",
            "- Read the failure reasons first, not raw logs first.",
            "- Propose the smallest change that improves build, smoke, or deeper-stage reach.",
            "- Stay within bounded mutation scope unless the evidence explicitly justifies widening it.",
            "",
        ]
    )
    return "\n".join(lines)



def write_llm_evidence_packet(repo_root: Path) -> dict[str, object]:
    packet = build_llm_evidence_packet(repo_root)
    out_dir = repo_root / "fuzz-records" / "llm-evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{_slugify(str(packet.get('generated_from_project') or repo_root.name))}-llm-evidence"
    json_path = out_dir / f"{stem}.json"
    markdown_path = out_dir / f"{stem}.md"
    packet["llm_evidence_json_path"] = str(json_path)
    packet["llm_evidence_markdown_path"] = str(markdown_path)
    json_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_llm_evidence_markdown(packet), encoding="utf-8")
    return packet
