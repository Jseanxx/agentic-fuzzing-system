#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mode="${1:-parse}"
shift || true

build_dir="${BUILD_DIR:-${repo_root}/build-fuzz-aflpp}"
out_root="${OUT_ROOT:-${repo_root}/fuzz-artifacts/aflpp}"
timeout_ms="${AFL_TIMEOUT_MS:-1000}"
memory_limit="${AFL_MEMORY_LIMIT:-none}"

export AFL_SKIP_CPUFREQ="${AFL_SKIP_CPUFREQ:-1}"
export AFL_AUTORESUME="${AFL_AUTORESUME:-1}"
export AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES="${AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES:-1}"
export ASAN_OPTIONS="${ASAN_OPTIONS:-abort_on_error=1:detect_leaks=0:strict_string_checks=1:check_initialization_order=1:symbolize=0}"
export UBSAN_OPTIONS="${UBSAN_OPTIONS:-print_stacktrace=1:halt_on_error=1}"

case "${mode}" in
  parse)
    target_bin="${build_dir}/bin/open_htj2k_parse_memory_harness"
    in_dir="${IN_DIR:-${repo_root}/fuzz/corpus-afl/parse}"
    ;;
  cleanup)
    target_bin="${build_dir}/bin/open_htj2k_cleanup_memory_harness"
    in_dir="${IN_DIR:-${repo_root}/fuzz/corpus-afl/cleanup}"
    ;;
  decode)
    target_bin="${build_dir}/bin/open_htj2k_decode_memory_harness"
    in_dir="${IN_DIR:-${repo_root}/fuzz/corpus-afl/decode}"
    ;;
  deep-decode-v2)
    target_bin="${build_dir}/bin/open_htj2k_deep_decode_lifecycle_harness"
    in_dir="${IN_DIR:-${repo_root}/fuzz/corpus-afl/deep-decode-v2}"
    ;;
  deep-decode-v3)
    target_bin="${build_dir}/bin/open_htj2k_deep_decode_focus_v3_harness"
    in_dir="${IN_DIR:-${repo_root}/fuzz/corpus-afl/deep-decode-v3}"
    ;;
  *)
    echo "Unknown mode: ${mode}" >&2
    echo "Usage: bash scripts/run-aflpp-mode.sh [parse|cleanup|decode|deep-decode-v2|deep-decode-v3]" >&2
    exit 2
    ;;
esac

mkdir -p "${in_dir}"
mkdir -p "${out_root}"
out_dir="${out_root}/${mode}"

if [ ! -x "${target_bin}" ]; then
  echo "Missing target binary: ${target_bin}" >&2
  exit 2
fi

printf 'mode=%s\n' "${mode}"
printf 'target_bin=%s\n' "${target_bin}"
printf 'in_dir=%s\n' "${in_dir}"
printf 'out_dir=%s\n' "${out_dir}"
printf 'ASAN_OPTIONS=%s\n' "${ASAN_OPTIONS}"
printf 'UBSAN_OPTIONS=%s\n' "${UBSAN_OPTIONS}"

exec afl-fuzz -i "${in_dir}" -o "${out_dir}" -m "${memory_limit}" -t "${timeout_ms}" -- "${target_bin}" @@ "$@"
