from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


def _normalize_command(value: object) -> tuple[str, ...] | None:
    if isinstance(value, (list, tuple)) and value and all(isinstance(item, str) and item for item in value):
        return tuple(value)
    return None


def _adapter_from_summary(profile_summary: dict[str, object] | None) -> TargetAdapter | None:
    if not isinstance(profile_summary, dict):
        return None
    adapter = profile_summary.get("adapter") if isinstance(profile_summary.get("adapter"), dict) else {}
    if not adapter:
        return None
    key = adapter.get("key") if isinstance(adapter.get("key"), str) and adapter.get("key") else None
    notification_label = adapter.get("notification_label") if isinstance(adapter.get("notification_label"), str) and adapter.get("notification_label") else None
    report_target = adapter.get("report_target") if isinstance(adapter.get("report_target"), str) and adapter.get("report_target") else None
    smoke_binary_relpath = adapter.get("smoke_binary_relpath") if isinstance(adapter.get("smoke_binary_relpath"), str) and adapter.get("smoke_binary_relpath") else None
    editable_harness_relpath = adapter.get("editable_harness_relpath") if isinstance(adapter.get("editable_harness_relpath"), str) and adapter.get("editable_harness_relpath") else "fuzz-records/harness-skeletons"
    fuzz_entrypoint_names_raw = adapter.get("fuzz_entrypoint_names")
    guard_condition = adapter.get("guard_condition") if isinstance(adapter.get("guard_condition"), str) and adapter.get("guard_condition") else "size < 4"
    guard_return_statement = adapter.get("guard_return_statement") if isinstance(adapter.get("guard_return_statement"), str) and adapter.get("guard_return_statement") else "return 0;"
    target_call_todo = adapter.get("target_call_todo") if isinstance(adapter.get("target_call_todo"), str) and adapter.get("target_call_todo") else "wire target entrypoint call before stage promotion"
    resource_lifetime_hint = adapter.get("resource_lifetime_hint") if isinstance(adapter.get("resource_lifetime_hint"), str) and adapter.get("resource_lifetime_hint") else "borrow the fuzz input only for the current call; avoid retaining pointers or ownership across iterations"
    if isinstance(fuzz_entrypoint_names_raw, (list, tuple)) and fuzz_entrypoint_names_raw:
        fuzz_entrypoint_names = tuple(
            item for item in fuzz_entrypoint_names_raw if isinstance(item, str) and item
        )
    else:
        fuzz_entrypoint_names = ("LLVMFuzzerTestOneInput",)
    build_command = _normalize_command(adapter.get("build_command"))
    smoke_command_prefix = _normalize_command(adapter.get("smoke_command_prefix"))
    fuzz_command = _normalize_command(adapter.get("fuzz_command"))
    if not all([key, notification_label, report_target, smoke_binary_relpath, build_command, smoke_command_prefix, fuzz_command, editable_harness_relpath, fuzz_entrypoint_names]):
        return None
    return TargetAdapter(
        key=key,
        notification_label=notification_label,
        report_target=report_target,
        build_command=build_command,
        smoke_binary_relpath=smoke_binary_relpath,
        smoke_command_prefix=smoke_command_prefix,
        fuzz_command=fuzz_command,
        editable_harness_relpath=editable_harness_relpath,
        fuzz_entrypoint_names=fuzz_entrypoint_names,
        guard_condition=guard_condition,
        guard_return_statement=guard_return_statement,
        target_call_todo=target_call_todo,
        resource_lifetime_hint=resource_lifetime_hint,
    )


@dataclass(frozen=True)
class TargetAdapter:
    key: str
    notification_label: str
    report_target: str
    build_command: tuple[str, ...]
    smoke_binary_relpath: str
    smoke_command_prefix: tuple[str, ...]
    fuzz_command: tuple[str, ...]
    editable_harness_relpath: str = "fuzz-records/harness-skeletons"
    fuzz_entrypoint_names: tuple[str, ...] = ("LLVMFuzzerTestOneInput",)
    guard_condition: str = "size < 4"
    guard_return_statement: str = "return 0;"
    target_call_todo: str = "wire target entrypoint call before stage promotion"
    resource_lifetime_hint: str = "borrow the fuzz input only for the current call; avoid retaining pointers or ownership across iterations"

    def smoke_command(self, repo_root: Path) -> list[str]:
        return [*self.smoke_command_prefix, str(repo_root / self.smoke_binary_relpath)]

    def build_command_list(self) -> list[str]:
        return list(self.build_command)

    def fuzz_command_list(self) -> list[str]:
        return list(self.fuzz_command)


OPENHTJ2K_ADAPTER = TargetAdapter(
    key="openhtj2k",
    notification_label="OpenHTJ2K fuzz",
    report_target="open_htj2k_decode_memory_fuzzer",
    build_command=("bash", "scripts/build-libfuzzer.sh"),
    smoke_binary_relpath="build-fuzz-libfuzzer",
    smoke_command_prefix=("bash", "scripts/run-smoke.sh"),
    fuzz_command=("bash", "scripts/run-fuzzer.sh"),
)


def get_target_adapter(profile_summary: dict[str, object] | None = None) -> TargetAdapter:
    adapter = _adapter_from_summary(profile_summary)
    if adapter is not None:
        return adapter
    project = None
    if isinstance(profile_summary, dict):
        project = profile_summary.get("project")
    if project in {None, "openhtj2k"}:
        return OPENHTJ2K_ADAPTER
    return OPENHTJ2K_ADAPTER


def build_target_adapter_regression_smoke_matrix(repo_root: Path, profile_summary: dict[str, object] | None = None) -> dict[str, object]:
    adapter = get_target_adapter(profile_summary)
    rows = [
        {
            "id": "main-build",
            "kind": "build",
            "surface": "main",
            "command": adapter.build_command_list(),
            "expected_outcome": "build-command-resolves",
        },
        {
            "id": "main-smoke",
            "kind": "smoke",
            "surface": "main",
            "command": adapter.smoke_command(repo_root),
            "expected_outcome": "smoke-command-resolves",
        },
        {
            "id": "main-fuzz",
            "kind": "fuzz",
            "surface": "main",
            "command": adapter.fuzz_command_list(),
            "expected_outcome": "fuzz-command-resolves",
        },
        {
            "id": "harness-probe-build",
            "kind": "build",
            "surface": "harness-probe",
            "command": adapter.build_command_list(),
            "expected_outcome": "probe-build-command-matches-adapter",
        },
        {
            "id": "harness-probe-smoke",
            "kind": "smoke",
            "surface": "harness-probe",
            "command": adapter.smoke_command(repo_root),
            "expected_outcome": "probe-smoke-command-matches-adapter",
        },
        {
            "id": "skeleton-closure-build",
            "kind": "build",
            "surface": "skeleton-closure",
            "command": adapter.build_command_list(),
            "expected_outcome": "closure-build-command-matches-adapter",
        },
        {
            "id": "skeleton-closure-smoke",
            "kind": "smoke",
            "surface": "skeleton-closure",
            "command": adapter.smoke_command(repo_root),
            "expected_outcome": "closure-smoke-command-matches-adapter",
        },
    ]
    return {
        "generated_from_project": str((profile_summary or {}).get("project") or repo_root.name),
        "adapter_key": adapter.key,
        "notification_label": adapter.notification_label,
        "report_target": adapter.report_target,
        "editable_harness_relpath": adapter.editable_harness_relpath,
        "fuzz_entrypoint_names": list(adapter.fuzz_entrypoint_names),
        "guard_condition": adapter.guard_condition,
        "guard_return_statement": adapter.guard_return_statement,
        "target_call_todo": adapter.target_call_todo,
        "resource_lifetime_hint": adapter.resource_lifetime_hint,
        "row_count": len(rows),
        "rows": rows,
    }


def render_target_adapter_regression_smoke_matrix_markdown(matrix: dict[str, object]) -> str:
    rows = matrix.get("rows") if isinstance(matrix.get("rows"), list) else []
    lines = [
        "# Target Adapter Regression Smoke Matrix",
        "",
        f"- project: {matrix.get('generated_from_project')}",
        f"- adapter_key: {matrix.get('adapter_key')}",
        f"- notification_label: {matrix.get('notification_label')}",
        f"- report_target: {matrix.get('report_target')}",
        f"- editable_harness_relpath: {matrix.get('editable_harness_relpath')}",
        f"- fuzz_entrypoint_names: {matrix.get('fuzz_entrypoint_names')}",
        f"- guard_condition: {matrix.get('guard_condition')}",
        f"- guard_return_statement: {matrix.get('guard_return_statement')}",
        f"- target_call_todo: {matrix.get('target_call_todo')}",
        f"- resource_lifetime_hint: {matrix.get('resource_lifetime_hint')}",
        "",
        "| id | surface | kind | expected_outcome | command |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"| {row.get('id')} | {row.get('surface')} | {row.get('kind')} | {row.get('expected_outcome')} | `{row.get('command')}` |"
        )
    return "\n".join(lines) + "\n"


def write_target_adapter_regression_smoke_matrix(repo_root: Path, profile_summary: dict[str, object] | None = None) -> dict[str, object]:
    matrix = build_target_adapter_regression_smoke_matrix(repo_root, profile_summary)
    out_dir = repo_root / "fuzz-records" / "policies"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{matrix.get('generated_from_project')}-target-adapter-regression-smoke-matrix"
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"
    json_path.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_target_adapter_regression_smoke_matrix_markdown(matrix), encoding="utf-8")
    return {
        **matrix,
        "matrix_json_path": str(json_path),
        "matrix_markdown_path": str(md_path),
    }
