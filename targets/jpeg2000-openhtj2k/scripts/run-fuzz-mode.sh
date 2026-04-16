#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mode="${1:-triage}"
shift || true

max_total_time="${MAX_TOTAL_TIME:-${FUZZ_MAX_TOTAL_TIME:-60}}"
no_progress_seconds="${NO_PROGRESS_SECONDS:-${FUZZ_NO_PROGRESS_SECONDS:-20}}"
progress_interval_seconds="${PROGRESS_INTERVAL_SECONDS:-${FUZZ_PROGRESS_INTERVAL_SECONDS:-10}}"

case "${mode}" in
  triage)
    corpus_dir="${CORPUS_DIR:-${repo_root}/fuzz/corpus/triage}"
    export ASAN_OPTIONS="${ASAN_OPTIONS:-abort_on_error=1:detect_leaks=1:strict_string_checks=1:check_initialization_order=1:symbolize=1}"
    export UBSAN_OPTIONS="${UBSAN_OPTIONS:-print_stacktrace=1:halt_on_error=1}"
    skip_smoke="${SKIP_SMOKE:-1}"
    ;;
  coverage)
    corpus_dir="${CORPUS_DIR:-${repo_root}/fuzz/corpus/coverage}"
    export ASAN_OPTIONS="${ASAN_OPTIONS:-abort_on_error=1:detect_leaks=0:strict_string_checks=1:check_initialization_order=1:symbolize=1}"
    export UBSAN_OPTIONS="${UBSAN_OPTIONS:-print_stacktrace=1:halt_on_error=1}"
    skip_smoke="${SKIP_SMOKE:-1}"
    ;;
  regression)
    corpus_dir="${CORPUS_DIR:-${repo_root}/fuzz/corpus/regression}"
    export ASAN_OPTIONS="${ASAN_OPTIONS:-abort_on_error=1:detect_leaks=1:strict_string_checks=1:check_initialization_order=1:symbolize=1}"
    export UBSAN_OPTIONS="${UBSAN_OPTIONS:-print_stacktrace=1:halt_on_error=1}"
    skip_smoke="${SKIP_SMOKE:-0}"
    ;;
  *)
    echo "Unknown mode: ${mode}" >&2
    echo "Usage: bash scripts/run-fuzz-mode.sh [triage|coverage|regression]" >&2
    exit 2
    ;;
esac

mkdir -p "${corpus_dir}"

run_stamp="$(date +%Y%m%d_%H%M%S)_${mode}"
export CORPUS_DIR="${corpus_dir}"
export RUN_DIR="${repo_root}/fuzz-artifacts/modes/${mode}/${run_stamp}"
export FUZZ_MODE="${mode}"

cmd=(python3 scripts/hermes_watch.py
  --max-total-time "${max_total_time}"
  --no-progress-seconds "${no_progress_seconds}"
  --progress-interval-seconds "${progress_interval_seconds}"
)

if [ "${skip_smoke}" = "1" ]; then
  cmd+=(--skip-smoke)
fi

printf 'mode=%s\n' "${mode}"
printf 'corpus_dir=%s\n' "${CORPUS_DIR}"
printf 'run_dir=%s\n' "${RUN_DIR}"
printf 'ASAN_OPTIONS=%s\n' "${ASAN_OPTIONS}"
printf 'UBSAN_OPTIONS=%s\n' "${UBSAN_OPTIONS}"
exec "${cmd[@]}" "$@"
