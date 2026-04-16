import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CMAKE_PATH = REPO_ROOT / "CMakeLists.txt"
BUILD_LIBFUZZER = REPO_ROOT / "scripts" / "build-libfuzzer.sh"
BUILD_AFLPP = REPO_ROOT / "scripts" / "build-aflpp.sh"
RUN_AFLPP = REPO_ROOT / "scripts" / "run-aflpp-mode.sh"
HARNESS_PATH = REPO_ROOT / "fuzz" / "deep_decode_lifecycle_harness.cpp"
SEED_DIR = REPO_ROOT / "fuzz" / "corpus-afl" / "deep-decode-v2"


class DeepDecodeV2HarnessTests(unittest.TestCase):
    def test_cmake_defines_deep_decode_v2_targets(self):
        cmake = CMAKE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "add_executable(open_htj2k_deep_decode_lifecycle_harness fuzz/deep_decode_lifecycle_harness.cpp)",
            cmake,
        )
        self.assertIn(
            "add_executable(open_htj2k_deep_decode_lifecycle_fuzzer fuzz/deep_decode_lifecycle_harness.cpp)",
            cmake,
        )
        self.assertIn(
            "target_compile_definitions(open_htj2k_deep_decode_lifecycle_fuzzer PRIVATE OPENHTJ2K_LIBFUZZER)",
            cmake,
        )

    def test_build_scripts_include_deep_decode_v2_targets(self):
        libfuzzer_script = BUILD_LIBFUZZER.read_text(encoding="utf-8")
        aflpp_script = BUILD_AFLPP.read_text(encoding="utf-8")
        self.assertIn("open_htj2k_deep_decode_lifecycle_fuzzer", libfuzzer_script)
        self.assertIn("open_htj2k_deep_decode_lifecycle_harness", libfuzzer_script)
        self.assertIn("open_htj2k_deep_decode_lifecycle_harness", aflpp_script)

    def test_run_script_mentions_deep_decode_v2_mode(self):
        script = RUN_AFLPP.read_text(encoding="utf-8")
        self.assertIn("deep-decode-v2", script)
        self.assertIn("open_htj2k_deep_decode_lifecycle_harness", script)

    def test_harness_source_uses_deep_lifecycle_entrypoints(self):
        content = HARNESS_PATH.read_text(encoding="utf-8")
        self.assertIn("enable_single_tile_reuse(true)", content)
        self.assertIn("decoder.init(", content)
        self.assertIn("decoder.parse();", content)
        self.assertIn("decoder.invoke_line_based_stream(", content)
        self.assertIn("decoder.invoke_line_based_predecoded(", content)
        self.assertIn("DeepDecodeLifecycleOneInput", content)
        self.assertIn("LLVMFuzzerTestOneInput", content)

    def test_seed_directory_exists_with_at_least_two_files(self):
        self.assertTrue(SEED_DIR.is_dir())
        self.assertGreaterEqual(len([p for p in SEED_DIR.iterdir() if p.is_file()]), 2)


if __name__ == "__main__":
    unittest.main()
