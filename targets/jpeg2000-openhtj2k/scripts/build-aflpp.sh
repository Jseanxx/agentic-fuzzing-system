#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="${1:-"${repo_root}/build-fuzz-aflpp"}"
san_mode="${SAN_MODE:-asan}"

: "${CC:=afl-clang-fast}"
: "${CXX:=afl-clang-fast++}"

case "${san_mode}" in
  asan)
    export AFL_USE_ASAN=1
    unset AFL_USE_UBSAN || true
    fuzz_sanitizers="address"
    ;;
  ubsan)
    unset AFL_USE_ASAN || true
    export AFL_USE_UBSAN=1
    fuzz_sanitizers="undefined"
    ;;
  none)
    unset AFL_USE_ASAN || true
    unset AFL_USE_UBSAN || true
    fuzz_sanitizers=""
    ;;
  *)
    echo "Unknown SAN_MODE: ${san_mode}" >&2
    echo "Use SAN_MODE=asan|ubsan|none" >&2
    exit 2
    ;;
esac

cmake_args=(
  -S "${repo_root}"
  -B "${build_dir}"
  -G Ninja
  -DCMAKE_BUILD_TYPE=RelWithDebInfo
  -DBUILD_SHARED_LIBS=OFF
  -DOPENHTJ2K_FUZZ_HARNESS=ON
  -DOPENHTJ2K_FUZZ_LIBFUZZER=OFF
  -DCMAKE_DISABLE_FIND_PACKAGE_Threads=ON
  -DENABLE_AVX2=OFF
  -DCMAKE_C_COMPILER="${CC}"
  -DCMAKE_CXX_COMPILER="${CXX}"
)

if [ -n "${fuzz_sanitizers}" ]; then
  cmake_args+=( -DOPENHTJ2K_FUZZ_SANITIZERS="${fuzz_sanitizers}" )
fi

cmake "${cmake_args[@]}"

cmake --build "${build_dir}" --target open_htj2k_parse_memory_harness -j"$(nproc)"
cmake --build "${build_dir}" --target open_htj2k_cleanup_memory_harness -j"$(nproc)"
cmake --build "${build_dir}" --target open_htj2k_decode_memory_harness -j"$(nproc)"
cmake --build "${build_dir}" --target open_htj2k_deep_decode_lifecycle_harness -j"$(nproc)"
cmake --build "${build_dir}" --target open_htj2k_deep_decode_focus_v3_harness -j"$(nproc)"

echo "Built: ${build_dir}/bin/open_htj2k_parse_memory_harness"
echo "Built: ${build_dir}/bin/open_htj2k_cleanup_memory_harness"
echo "Built: ${build_dir}/bin/open_htj2k_decode_memory_harness"
echo "Built: ${build_dir}/bin/open_htj2k_deep_decode_lifecycle_harness"
echo "Built: ${build_dir}/bin/open_htj2k_deep_decode_focus_v3_harness"
