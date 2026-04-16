import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CMAKE_PATH = REPO_ROOT / "CMakeLists.txt"
BUILD_SCRIPT_PATH = REPO_ROOT / "scripts" / "build-libfuzzer.sh"
PARSE_HARNESS_PATH = REPO_ROOT / "fuzz" / "parse_memory_harness.cpp"
CLEANUP_HARNESS_PATH = REPO_ROOT / "fuzz" / "cleanup_memory_harness.cpp"


class AdditionalHarnessPlanTests(unittest.TestCase):
    def test_cmake_defines_parse_harness_targets(self):
        cmake = CMAKE_PATH.read_text(encoding="utf-8")
        self.assertIn("add_executable(open_htj2k_parse_memory_harness fuzz/parse_memory_harness.cpp)", cmake)
        self.assertIn("add_executable(open_htj2k_parse_memory_fuzzer fuzz/parse_memory_harness.cpp)", cmake)
        self.assertIn("target_compile_definitions(open_htj2k_parse_memory_fuzzer PRIVATE OPENHTJ2K_LIBFUZZER)", cmake)

    def test_cmake_defines_cleanup_harness_targets(self):
        cmake = CMAKE_PATH.read_text(encoding="utf-8")
        self.assertIn("add_executable(open_htj2k_cleanup_memory_harness fuzz/cleanup_memory_harness.cpp)", cmake)
        self.assertIn("add_executable(open_htj2k_cleanup_memory_fuzzer fuzz/cleanup_memory_harness.cpp)", cmake)
        self.assertIn("target_compile_definitions(open_htj2k_cleanup_memory_fuzzer PRIVATE OPENHTJ2K_LIBFUZZER)", cmake)

    def test_build_script_builds_all_new_fuzz_targets(self):
        script = BUILD_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("open_htj2k_parse_memory_fuzzer", script)
        self.assertIn("open_htj2k_parse_memory_harness", script)
        self.assertIn("open_htj2k_cleanup_memory_fuzzer", script)
        self.assertIn("open_htj2k_cleanup_memory_harness", script)

    def test_parse_harness_source_contains_parser_entrypoints(self):
        content = PARSE_HARNESS_PATH.read_text(encoding="utf-8")
        self.assertIn("ParseStatus", content)
        self.assertIn("ParseOneInput", content)
        self.assertIn("decoder.parse();", content)
        self.assertIn("LLVMFuzzerTestOneInput", content)

    def test_cleanup_harness_source_contains_cleanup_entrypoints(self):
        content = CLEANUP_HARNESS_PATH.read_text(encoding="utf-8")
        self.assertIn("CleanupStatus", content)
        self.assertIn("CleanupStressOneInput", content)
        self.assertIn("FreePlanes", content)
        self.assertIn("decoder.invoke(", content)
        self.assertIn("LLVMFuzzerTestOneInput", content)


if __name__ == "__main__":
    unittest.main()
