from __future__ import annotations


def validate_target_profile(profile: dict[str, object] | None) -> dict[str, object]:
    if profile is None:
        return {
            "status": "absent",
            "severity": None,
            "codes": [],
            "messages": [],
            "fatal": False,
        }

    codes: list[str] = []
    messages: list[str] = []
    fatal = False

    def add_issue(code: str, message: str, *, is_fatal: bool) -> None:
        nonlocal fatal
        codes.append(code)
        messages.append(message)
        if is_fatal:
            fatal = True

    load_error = profile.get("__load_error__") if isinstance(profile.get("__load_error__"), str) else None
    if load_error:
        add_issue(f"load-error:{load_error}", f"loader degraded: {load_error}", is_fatal=True)

    schema_version = profile.get("schema_version")
    if schema_version is None:
        add_issue("missing-schema-version", "schema_version is missing", is_fatal=False)
    elif schema_version != "target-profile/v1":
        add_issue("unsupported-schema-version", f"unsupported schema_version: {schema_version}", is_fatal=True)

    meta = profile.get("meta") if isinstance(profile.get("meta"), dict) else {}
    if not meta.get("name"):
        add_issue("missing-profile-name", "meta.name is missing", is_fatal=False)

    target = profile.get("target") if isinstance(profile.get("target"), dict) else {}
    current_campaign = target.get("current_campaign") if isinstance(target.get("current_campaign"), dict) else {}
    if not current_campaign.get("primary_mode"):
        add_issue("missing-primary-mode", "target.current_campaign.primary_mode is missing", is_fatal=True)

    stages = profile.get("stages") if isinstance(profile.get("stages"), list) else []
    if not stages:
        add_issue("missing-stages", "stages list is empty", is_fatal=True)

    stage_ids: list[str] = []
    stage_depth_ranks: list[int] = []
    allowed_stage_classes = {"shallow", "medium", "deep"}
    for index, stage in enumerate(stages):
        if not isinstance(stage, dict):
            add_issue("invalid-stage-entry", f"stages[{index}] must be a mapping", is_fatal=True)
            continue
        stage_id = stage.get("id")
        if not isinstance(stage_id, str) or not stage_id:
            add_issue("missing-stage-id", f"stages[{index}].id is missing", is_fatal=True)
            continue
        stage_ids.append(stage_id)
        depth_rank = stage.get("depth_rank")
        if depth_rank is not None:
            if not isinstance(depth_rank, int) or depth_rank <= 0:
                add_issue("invalid-stage-depth-rank", f"stage {stage_id} has invalid depth_rank", is_fatal=True)
            else:
                stage_depth_ranks.append(depth_rank)
        stage_class = stage.get("stage_class")
        if stage_class is not None and stage_class not in allowed_stage_classes:
            add_issue("invalid-stage-class", f"stage {stage_id} has invalid stage_class {stage_class}", is_fatal=True)
        expected_signals = stage.get("expected_signals")
        if expected_signals is not None:
            if not isinstance(expected_signals, list) or any(not isinstance(item, str) or not item for item in expected_signals):
                add_issue("invalid-expected-signals", f"stage {stage_id} has invalid expected_signals", is_fatal=True)

    if len(stage_ids) != len(set(stage_ids)):
        add_issue("duplicate-stage-id", "stage ids must be unique", is_fatal=True)
    if len(stage_depth_ranks) != len(set(stage_depth_ranks)):
        add_issue("duplicate-stage-depth-rank", "stage depth_rank values must be unique", is_fatal=True)
    stage_id_set = set(stage_ids)

    hotspots = profile.get("hotspots") if isinstance(profile.get("hotspots"), dict) else {}
    hotspot_functions = hotspots.get("functions") if isinstance(hotspots.get("functions"), list) else []
    for index, hotspot in enumerate(hotspot_functions):
        if not isinstance(hotspot, dict):
            add_issue("invalid-hotspot-function-entry", f"hotspots.functions[{index}] must be a mapping", is_fatal=True)
            continue
        stage_ref = hotspot.get("stage")
        name = hotspot.get("name")
        if not isinstance(name, str) or not name:
            add_issue("missing-hotspot-function-name", f"hotspots.functions[{index}].name is missing", is_fatal=True)
        if not isinstance(stage_ref, str) or stage_ref not in stage_id_set:
            add_issue("unknown-hotspot-stage-ref", f"hotspot function {name or index} references unknown stage {stage_ref}", is_fatal=True)

    hotspot_files = hotspots.get("files") if isinstance(hotspots.get("files"), list) else []
    for index, hotspot in enumerate(hotspot_files):
        if not isinstance(hotspot, dict):
            add_issue("invalid-hotspot-file-entry", f"hotspots.files[{index}] must be a mapping", is_fatal=True)
            continue
        stage_ref = hotspot.get("stage")
        path = hotspot.get("path")
        if not isinstance(path, str) or not path:
            add_issue("missing-hotspot-file-path", f"hotspots.files[{index}].path is missing", is_fatal=True)
        if not isinstance(stage_ref, str) or stage_ref not in stage_id_set:
            add_issue("unknown-hotspot-stage-ref", f"hotspot file {path or index} references unknown stage {stage_ref}", is_fatal=True)

    telemetry = profile.get("telemetry") if isinstance(profile.get("telemetry"), dict) else {}
    stage_counters = telemetry.get("stage_counters") if isinstance(telemetry.get("stage_counters"), dict) else {}
    counter_names = stage_counters.get("names") if isinstance(stage_counters.get("names"), list) else []
    for name in counter_names:
        if isinstance(name, str) and name not in stage_id_set:
            add_issue("unknown-stage-counter-name", f"telemetry stage counter references unknown stage {name}", is_fatal=False)

    stack_tagging = telemetry.get("stack_tagging") if isinstance(telemetry.get("stack_tagging"), dict) else {}
    stage_file_map = stack_tagging.get("stage_file_map") if isinstance(stack_tagging.get("stage_file_map"), dict) else {}
    for stage_ref, mapped_paths in stage_file_map.items():
        if not isinstance(stage_ref, str) or stage_ref not in stage_id_set:
            add_issue("unknown-telemetry-stage-file-map-ref", f"telemetry stage_file_map references unknown stage {stage_ref}", is_fatal=True)
        if not isinstance(mapped_paths, list) or any(not isinstance(path, str) or not path for path in mapped_paths):
            add_issue("invalid-telemetry-stage-file-map", f"telemetry stage_file_map[{stage_ref}] must be a non-empty string list", is_fatal=True)

    triggers = profile.get("triggers") if isinstance(profile.get("triggers"), dict) else {}
    actions = profile.get("actions") if isinstance(profile.get("actions"), dict) else {}
    allowed_action_types = {
        "recommendation",
        "scheduler_change",
        "campaign_split",
        "corpus_maintenance",
        "safety_stop",
        "alert",
        "continue_run",
    }
    for action_name, action_spec in actions.items():
        if not isinstance(action_name, str) or not isinstance(action_spec, dict):
            add_issue("invalid-action-entry", f"action {action_name} must be a mapping", is_fatal=True)
            continue
        action_type = action_spec.get("type")
        if action_type not in allowed_action_types:
            add_issue("invalid-action-type", f"action {action_name} has invalid type {action_type}", is_fatal=True)
        if not isinstance(action_spec.get("requires_human_review"), bool):
            add_issue("invalid-action-human-review-flag", f"action {action_name} requires_human_review must be bool", is_fatal=True)
        outputs = action_spec.get("outputs")
        if not isinstance(outputs, list) or any(not isinstance(item, str) or not item for item in outputs):
            add_issue("invalid-action-outputs", f"action {action_name} outputs must be a non-empty string list", is_fatal=True)

    for trigger_name, trigger in triggers.items():
        if not isinstance(trigger_name, str) or not isinstance(trigger, dict):
            add_issue("invalid-trigger-entry", f"trigger {trigger_name} must be a mapping", is_fatal=True)
            continue
        action = trigger.get("action")
        if not isinstance(action, str) or not action:
            add_issue("missing-trigger-action", f"trigger {trigger_name} is missing action", is_fatal=True)
        elif action not in actions:
            add_issue("unknown-trigger-action", f"trigger {trigger_name} references unknown action {action}", is_fatal=True)
        condition = trigger.get("condition") if isinstance(trigger.get("condition"), dict) else {}
        dominant_stage = condition.get("dominant_stage")
        if dominant_stage is not None and dominant_stage not in stage_id_set:
            add_issue("unknown-trigger-stage-ref", f"trigger {trigger_name} references unknown dominant_stage {dominant_stage}", is_fatal=True)
        stage_any_of = condition.get("stage_any_of")
        if isinstance(stage_any_of, list):
            for stage_ref in stage_any_of:
                if isinstance(stage_ref, str) and stage_ref not in stage_id_set:
                    add_issue("unknown-trigger-stage-ref", f"trigger {trigger_name} references unknown stage {stage_ref}", is_fatal=True)

        condition_error = False
        if trigger_name == "coverage_plateau":
            if not isinstance(condition.get("plateau_minutes"), int):
                condition_error = True
            if not isinstance(condition.get("min_execs_per_sec"), int):
                condition_error = True
            if not isinstance(condition.get("max_new_high_value_crashes"), int):
                condition_error = True
        elif trigger_name == "shallow_crash_dominance":
            if not isinstance(condition.get("dominant_stage"), str):
                condition_error = True
            min_ratio = condition.get("min_ratio")
            if not isinstance(min_ratio, (int, float)):
                condition_error = True
            if not isinstance(condition.get("min_crash_families"), int):
                condition_error = True
        elif trigger_name == "timeout_surge":
            min_timeout_rate = condition.get("min_timeout_rate")
            if not isinstance(min_timeout_rate, (int, float)):
                condition_error = True
            if not isinstance(condition.get("min_duration_minutes"), int):
                condition_error = True
        elif trigger_name == "corpus_bloat_low_gain":
            if not isinstance(condition.get("min_corpus_growth"), int):
                condition_error = True
            max_gain = condition.get("max_coverage_gain_percent")
            if not isinstance(max_gain, (int, float)):
                condition_error = True
        elif trigger_name == "stability_drop":
            if not isinstance(condition.get("min_stability_percent"), int):
                condition_error = True
        elif trigger_name == "deep_write_crash":
            if not isinstance(condition.get("min_stage_depth_rank"), int):
                condition_error = True
            sanitizer_match = condition.get("sanitizer_match")
            if not isinstance(sanitizer_match, list) or any(not isinstance(item, str) or not item for item in sanitizer_match):
                condition_error = True
        elif trigger_name == "deep_signal_emergence":
            if not isinstance(stage_any_of, list) or any(not isinstance(item, str) or not item for item in stage_any_of):
                condition_error = True
            if not isinstance(condition.get("min_new_reproducible_families"), int):
                condition_error = True
        if condition_error:
            add_issue(f"invalid-trigger-condition:{trigger_name}", f"trigger {trigger_name} has invalid condition fields", is_fatal=True)

    status = "fatal" if fatal else "warning" if codes else "valid"
    severity = "fatal" if fatal else "warning" if codes else None
    return {
        "status": status,
        "severity": severity,
        "codes": codes,
        "messages": messages,
        "fatal": fatal,
    }


def runtime_target_profile(profile: dict[str, object] | None) -> dict[str, object] | None:
    validation = validate_target_profile(profile)
    return None if validation.get("fatal") else profile
