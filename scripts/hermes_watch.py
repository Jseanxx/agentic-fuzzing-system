#!/usr/bin/env python3
"""Stage-1 OpenHTJ2K fuzz watcher for Hermes.

Runs build/smoke/fuzz steps, parses libFuzzer output for crash and progress
signals, writes FUZZING_REPORT.md, and optionally sends a compact Discord
webhook notification via DISCORD_WEBHOOK_URL.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


FUZZ_RE = re.compile(
    r"cov:\s*(?P<cov>\d+).*?ft:\s*(?P<ft>\d+).*?corp:\s*(?P<corp_units>\d+)/(?P<corp_size>\S+)",
    re.IGNORECASE,
)
EXEC_RE = re.compile(r"exec/s:\s*(?P<execs>\d+)", re.IGNORECASE)
RSS_RE = re.compile(r"rss:\s*(?P<rss>\S+)", re.IGNORECASE)
CRASH_RE = re.compile(
    r"(ERROR: AddressSanitizer|ERROR: UndefinedBehaviorSanitizer|ERROR: libFuzzer|Test unit written to|SUMMARY: AddressSanitizer|SUMMARY: UndefinedBehaviorSanitizer)",
    re.IGNORECASE,
)
TIMEOUT_RE = re.compile(r"(timeout|deadly signal|libFuzzer: timeout)", re.IGNORECASE)


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
            if len(self.top_crash_lines) < 12:
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


def metrics_snapshot(
    *,
    outcome: str,
    metrics: Metrics,
    run_dir: Path,
    report_path: Path,
    start: float,
) -> dict[str, object]:
    now = time.monotonic()
    return {
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


def write_status(status_path: Path, snapshot: dict[str, object]) -> None:
    tmp_path = status_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(status_path)


def format_progress_message(snapshot: dict[str, object]) -> str:
    return "\n".join(
        [
            "[OpenHTJ2K fuzz] PROGRESS",
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


def send_discord(message: str) -> None:
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        print("[notify] DISCORD_WEBHOOK_URL not set; skipping Discord notification.")
        return
    payload = json.dumps({"content": message}).encode()
    req = urllib.request.Request(webhook, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as response:
        response.read()


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
                "- target: open_htj2k_decode_memory_fuzzer",
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
                recommended_action(outcome),
                "",
            ]
        ),
        encoding="utf-8",
    )


def recommended_action(outcome: str) -> str:
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
    parser.add_argument("--max-total-time", default=int(os.environ.get("MAX_TOTAL_TIME", "3600")), type=int)
    parser.add_argument("--no-progress-seconds", default=int(os.environ.get("NO_PROGRESS_SECONDS", "1800")), type=int)
    parser.add_argument(
        "--progress-interval-seconds",
        default=int(os.environ.get("PROGRESS_INTERVAL_SECONDS", "600")),
        type=int,
        help="Send/write progress snapshots at this interval; use 0 to disable interval notifications.",
    )
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--skip-smoke", action="store_true")
    args = parser.parse_args()

    repo_root = args.repo.resolve()
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    git_short = run_quiet(["git", "rev-parse", "--short", "HEAD"], repo_root)[1].strip() or "unknown"
    run_dir = repo_root / "fuzz-artifacts" / "runs" / f"{timestamp}_{git_short}"
    run_dir.mkdir(parents=True, exist_ok=True)
    build_log = run_dir / "build.log"
    smoke_log = run_dir / "smoke.log"
    fuzz_log = run_dir / "fuzz.log"
    report_path = run_dir / "FUZZING_REPORT.md"
    status_path = run_dir / "status.json"
    current_status_path = repo_root / "fuzz-artifacts" / "current_status.json"

    if not args.skip_build:
        build_code, build_output = run_quiet(["bash", "scripts/build-libfuzzer.sh"], repo_root)
        build_log.write_text(build_output, encoding="utf-8", errors="replace")
        if build_code != 0:
            write_report(
                report_path,
                outcome="build-failed",
                repo_root=repo_root,
                run_dir=run_dir,
                command=["bash", "scripts/build-libfuzzer.sh"],
                exit_code=build_code,
                metrics=Metrics(),
                duration_s=0,
                build_log=build_log,
                smoke_log=smoke_log,
                fuzz_log=fuzz_log,
            )
            send_discord(f"[OpenHTJ2K fuzz] BUILD FAILED\nreport: {report_path}")
            return build_code

    if not args.skip_smoke:
        smoke_code, smoke_output = run_quiet(["bash", "scripts/run-smoke.sh", str(repo_root / "build-fuzz-libfuzzer")], repo_root)
        smoke_log.write_text(smoke_output, encoding="utf-8", errors="replace")
        if smoke_code != 0:
            write_report(
                report_path,
                outcome="smoke-failed",
                repo_root=repo_root,
                run_dir=run_dir,
                command=["bash", "scripts/run-smoke.sh", str(repo_root / "build-fuzz-libfuzzer")],
                exit_code=smoke_code,
                metrics=Metrics(),
                duration_s=0,
                build_log=build_log,
                smoke_log=smoke_log,
                fuzz_log=fuzz_log,
            )
            send_discord(f"[OpenHTJ2K fuzz] SMOKE FAILED\nreport: {report_path}")
            return smoke_code

    command = ["bash", "scripts/run-fuzzer.sh"]
    env = os.environ.copy()
    env["MAX_TOTAL_TIME"] = str(args.max_total_time)
    env["RUN_DIR"] = str(run_dir)
    env["WATCHER_STDOUT_ONLY"] = "1"
    start = time.monotonic()
    metrics = Metrics()
    outcome = "ok"
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
            )
            write_status(status_path, snapshot)
            write_status(current_status_path, snapshot)
            if args.progress_interval_seconds > 0 and (
                time.monotonic() - last_progress_notify_at >= args.progress_interval_seconds
            ):
                message = format_progress_message(snapshot)
                print(f"[progress] {message.replace(chr(10), ' | ')}")
                send_discord(message)
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
    final_snapshot = metrics_snapshot(
        outcome=outcome,
        metrics=metrics,
        run_dir=run_dir,
        report_path=report_path,
        start=start,
    )
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
    )

    send_discord(
        "\n".join(
            [
                f"[OpenHTJ2K fuzz] {outcome.upper()}",
                f"cov: {metrics.cov} ft: {metrics.ft} corp: {metrics.corp_units}",
                f"report: {report_path}",
            ]
        )
    )
    return 0 if outcome in {"ok", "no-progress"} else exit_code or 1


if __name__ == "__main__":
    raise SystemExit(main())
