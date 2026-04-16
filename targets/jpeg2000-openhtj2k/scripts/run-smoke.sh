#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target_arg="${1:-"${repo_root}/build-fuzz-asan"}"
shift || true
if [ -x "${target_arg}" ]; then
  harness="${target_arg}"
else
  harness="${target_arg}/bin/open_htj2k_decode_memory_harness"
fi

export ASAN_OPTIONS="${ASAN_OPTIONS:-abort_on_error=1:detect_leaks=1:strict_string_checks=1:check_initialization_order=1}"
export UBSAN_OPTIONS="${UBSAN_OPTIONS:-print_stacktrace=1:halt_on_error=1}"

if [ "$#" -gt 0 ]; then
  smoke_inputs=("$@")
else
  smoke_inputs=(
    "${repo_root}/conformance_data/ds0_ht_12_b11.j2k"
    "${repo_root}/conformance_data/p0_11.j2k"
  )
fi

for smoke_input in "${smoke_inputs[@]}"; do
  "${harness}" --expect-ok "${smoke_input}"
done

echo "Smoke test passed under ASan/UBSan."
