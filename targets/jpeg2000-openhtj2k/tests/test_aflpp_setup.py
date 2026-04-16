import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_AFLPP = REPO_ROOT / "scripts" / "build-aflpp.sh"
RUN_AFLPP = REPO_ROOT / "scripts" / "run-aflpp-mode.sh"
RUN_SMOKE = REPO_ROOT / "scripts" / "run-smoke.sh"
TARGET_PROFILE = REPO_ROOT / "fuzz-records" / "profiles" / "openhtj2k-target-profile-v1.yaml"
PARSE_SEEDS = REPO_ROOT / "fuzz" / "corpus-afl" / "parse"
CLEANUP_SEEDS = REPO_ROOT / "fuzz" / "corpus-afl" / "cleanup"


class AflppSetupTests(unittest.TestCase):
    def test_build_aflpp_script_exists_and_mentions_targets(self):
        content = BUILD_AFLPP.read_text(encoding="utf-8")
        self.assertIn("afl-clang-fast++", content)
        self.assertIn("open_htj2k_parse_memory_harness", content)
        self.assertIn("open_htj2k_cleanup_memory_harness", content)

    def test_run_aflpp_script_exists_and_mentions_parse_and_cleanup_modes(self):
        content = RUN_AFLPP.read_text(encoding="utf-8")
        self.assertIn('mode="${1:-parse}"', content)
        self.assertIn("open_htj2k_parse_memory_harness", content)
        self.assertIn("open_htj2k_cleanup_memory_harness", content)
        self.assertIn("afl-fuzz", content)
        self.assertIn("@@", content)

    def test_run_aflpp_script_sets_asan_symbolize_off(self):
        content = RUN_AFLPP.read_text(encoding="utf-8")
        self.assertIn("symbolize=0", content)

    def test_run_smoke_script_uses_only_stable_valid_default_seeds(self):
        content = RUN_SMOKE.read_text(encoding="utf-8")
        self.assertIn("ds0_ht_12_b11.j2k", content)
        self.assertIn("p0_11.j2k", content)
        self.assertNotIn("p0_12.j2k", content)

    def test_run_smoke_script_accepts_direct_harness_path(self):
        content = RUN_SMOKE.read_text(encoding="utf-8")
        self.assertIn('target_arg="${1:-"${repo_root}/build-fuzz-asan"}"', content)
        self.assertIn('if [ -x "${target_arg}" ]', content)
        self.assertIn('harness="${target_arg}"', content)

    def test_openhtj2k_target_profile_declares_deep_decode_v3_adapter_contract(self):
        content = TARGET_PROFILE.read_text(encoding="utf-8")
        self.assertIn("primary_mode: deep-decode-v3", content)
        self.assertIn("primary_binary: open_htj2k_deep_decode_focus_v3_harness", content)
        self.assertIn("adapter:", content)
        self.assertIn("build-libfuzzer.sh", content)
        self.assertIn("run-fuzzer.sh", content)
        self.assertIn("deep_decode_focus_v3_fuzzer", content)
        self.assertIn("FUZZER_BIN=${FUZZER_BIN:-build-fuzz-libfuzzer/bin/open_htj2k_deep_decode_focus_v3_fuzzer}", content)
        self.assertIn("CORPUS_DIR=${CORPUS_DIR:-fuzz/corpus-afl/deep-decode-v3}", content)
        self.assertIn("build-fuzz-libfuzzer/bin/open_htj2k_deep_decode_focus_v3_harness", content)

    def test_afl_seed_directories_exist_with_at_least_one_seed(self):
        self.assertTrue(PARSE_SEEDS.is_dir())
        self.assertTrue(CLEANUP_SEEDS.is_dir())
        self.assertGreaterEqual(len([p for p in PARSE_SEEDS.iterdir() if p.is_file()]), 1)
        self.assertGreaterEqual(len([p for p in CLEANUP_SEEDS.iterdir() if p.is_file()]), 1)


if __name__ == "__main__":
    unittest.main()
