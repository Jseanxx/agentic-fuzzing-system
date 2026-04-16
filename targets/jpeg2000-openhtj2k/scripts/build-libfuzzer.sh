#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="${1:-"${repo_root}/build-fuzz-libfuzzer"}"

: "${CC:=clang}"
: "${CXX:=clang++}"

cmake -S "${repo_root}" -B "${build_dir}" -G Ninja \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DBUILD_SHARED_LIBS=OFF \
  -DOPENHTJ2K_FUZZ_HARNESS=ON \
  -DOPENHTJ2K_FUZZ_LIBFUZZER=ON \
  -DOPENHTJ2K_FUZZ_SANITIZERS=address,undefined \
  -DCMAKE_DISABLE_FIND_PACKAGE_Threads=ON \
  -DENABLE_AVX2=OFF \
  -DCMAKE_C_COMPILER="${CC}" \
  -DCMAKE_CXX_COMPILER="${CXX}"

cmake --build "${build_dir}" --target open_htj2k_decode_memory_fuzzer -j"$(nproc)"
cmake --build "${build_dir}" --target open_htj2k_decode_memory_harness -j"$(nproc)"
cmake --build "${build_dir}" --target open_htj2k_deep_decode_lifecycle_fuzzer -j"$(nproc)"
cmake --build "${build_dir}" --target open_htj2k_deep_decode_lifecycle_harness -j"$(nproc)"
cmake --build "${build_dir}" --target open_htj2k_deep_decode_focus_v3_fuzzer -j"$(nproc)"
cmake --build "${build_dir}" --target open_htj2k_deep_decode_focus_v3_harness -j"$(nproc)"
cmake --build "${build_dir}" --target open_htj2k_parse_memory_fuzzer -j"$(nproc)"
cmake --build "${build_dir}" --target open_htj2k_parse_memory_harness -j"$(nproc)"
cmake --build "${build_dir}" --target open_htj2k_cleanup_memory_fuzzer -j"$(nproc)"
cmake --build "${build_dir}" --target open_htj2k_cleanup_memory_harness -j"$(nproc)"

echo "Built: ${build_dir}/bin/open_htj2k_decode_memory_fuzzer"
echo "Built: ${build_dir}/bin/open_htj2k_decode_memory_harness"
echo "Built: ${build_dir}/bin/open_htj2k_deep_decode_lifecycle_fuzzer"
echo "Built: ${build_dir}/bin/open_htj2k_deep_decode_lifecycle_harness"
echo "Built: ${build_dir}/bin/open_htj2k_deep_decode_focus_v3_fuzzer"
echo "Built: ${build_dir}/bin/open_htj2k_deep_decode_focus_v3_harness"
echo "Built: ${build_dir}/bin/open_htj2k_parse_memory_fuzzer"
echo "Built: ${build_dir}/bin/open_htj2k_parse_memory_harness"
echo "Built: ${build_dir}/bin/open_htj2k_cleanup_memory_fuzzer"
echo "Built: ${build_dir}/bin/open_htj2k_cleanup_memory_harness"
