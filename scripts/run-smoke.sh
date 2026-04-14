#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="${1:-"${repo_root}/build-fuzz-asan"}"
harness="${build_dir}/bin/open_htj2k_decode_memory_harness"

export ASAN_OPTIONS="${ASAN_OPTIONS:-abort_on_error=1:detect_leaks=1:strict_string_checks=1:check_initialization_order=1}"
export UBSAN_OPTIONS="${UBSAN_OPTIONS:-print_stacktrace=1:halt_on_error=1}"

"${harness}" --expect-ok "${repo_root}/conformance_data/ds0_ht_12_b11.j2k"
"${harness}" --expect-ok "${repo_root}/conformance_data/p0_11.j2k"
"${harness}" --expect-ok "${repo_root}/conformance_data/p0_12.j2k"

echo "Smoke test passed under ASan/UBSan."
