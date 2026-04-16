#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="${BUILD_DIR:-"${repo_root}/build-fuzz-libfuzzer"}"
fuzzer="${FUZZER_BIN:-"${build_dir}/bin/open_htj2k_decode_memory_fuzzer"}"
corpus_dir="${CORPUS_DIR:-"${repo_root}/fuzz/corpus/valid"}"
artifact_root="${ARTIFACT_ROOT:-"${repo_root}/fuzz-artifacts"}"
max_total_time="${MAX_TOTAL_TIME:-3600}"
timestamp="$(date +%Y%m%d_%H%M%S)"
git_sha="$(git -C "${repo_root}" rev-parse --short HEAD 2>/dev/null || echo unknown)"
run_dir="${RUN_DIR:-"${artifact_root}/runs/${timestamp}_${git_sha}"}"
crash_dir="${run_dir}/crashes"
log_file="${LOG_FILE:-"${run_dir}/fuzz.log"}"

mkdir -p "${corpus_dir}" "${crash_dir}"

if [ ! -x "${fuzzer}" ]; then
  echo "Missing fuzzer binary: ${fuzzer}" >&2
  echo "Run: bash scripts/build-libfuzzer.sh" >&2
  exit 2
fi

if [ -z "$(find "${corpus_dir}" -type f -print -quit 2>/dev/null)" ]; then
  cp "${repo_root}/conformance_data/ds0_ht_12_b11.j2k" "${corpus_dir}/"
  cp "${repo_root}/conformance_data/p0_11.j2k" "${corpus_dir}/"
  cp "${repo_root}/conformance_data/p0_12.j2k" "${corpus_dir}/"
fi

export ASAN_OPTIONS="${ASAN_OPTIONS:-abort_on_error=1:detect_leaks=1:strict_string_checks=1:check_initialization_order=1:symbolize=1}"
export UBSAN_OPTIONS="${UBSAN_OPTIONS:-print_stacktrace=1:halt_on_error=1}"

echo "run_dir=${run_dir}"
echo "log_file=${log_file}"

fuzzer_cmd=(
  "${fuzzer}" "${corpus_dir}"
  "-artifact_prefix=${crash_dir}/"
  "-max_total_time=${max_total_time}"
  "-print_final_stats=1"
  "-use_value_profile=1"
)

set +e
if [ "${WATCHER_STDOUT_ONLY:-0}" = "1" ]; then
  "${fuzzer_cmd[@]}" 2>&1
  exit_code="$?"
else
  "${fuzzer_cmd[@]}" 2>&1 | tee "${log_file}"
  exit_code="${PIPESTATUS[0]}"
fi
set -e

echo "${exit_code}" > "${run_dir}/exit_code.txt"
exit "${exit_code}"
