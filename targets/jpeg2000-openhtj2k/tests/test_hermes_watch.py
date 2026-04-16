import json
import tempfile
import unittest
import subprocess
from pathlib import Path
import importlib.util


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hermes_watch.py"
spec = importlib.util.spec_from_file_location("hermes_watch", MODULE_PATH)
hermes_watch = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(hermes_watch)


class HermesWatchFingerprintTests(unittest.TestCase):
    def test_build_crash_signature_extracts_kind_location_and_summary(self):
        lines = [
            "/tmp/project/source/core/coding/ht_block_decoding.cpp:60:9: runtime error: shift exponent -2 is negative",
            "SUMMARY: UndefinedBehaviorSanitizer: undefined-behavior /tmp/project/source/core/coding/ht_block_decoding.cpp:60:9",
            "artifact_prefix='/tmp/crashes/'; Test unit written to /tmp/crashes/crash-deadbeef",
        ]

        sig = hermes_watch.build_crash_signature(lines)

        self.assertEqual(sig["kind"], "ubsan")
        self.assertEqual(sig["location"], "ht_block_decoding.cpp:60")
        self.assertEqual(sig["summary"], "undefined-behavior /tmp/project/source/core/coding/ht_block_decoding.cpp:60:9")
        self.assertEqual(sig["fingerprint"], "ubsan|ht_block_decoding.cpp:60|undefined-behavior /tmp/project/source/core/coding/ht_block_decoding.cpp:60:9")

    def test_metrics_capture_leaksanitizer_lines_so_leaks_are_classified_correctly(self):
        metrics = hermes_watch.Metrics()
        for line in [
            "==1==ERROR: LeakSanitizer: detected memory leaks",
            "    #0 0x123 in j2k_tile::decode /tmp/project/source/core/coding/coding_units.cpp:3927:53",
            "SUMMARY: AddressSanitizer: 12312 byte(s) leaked in 1 allocation(s).",
            "artifact_prefix='/tmp/crashes/'; Test unit written to /tmp/crashes/leak-deadbeef",
        ]:
            metrics.update_from_line(line)

        self.assertTrue(any("LeakSanitizer" in line for line in metrics.top_crash_lines))
        sig = hermes_watch.build_crash_signature(metrics.top_crash_lines)
        self.assertEqual(sig["kind"], "leak")
        self.assertEqual(sig["location"], "coding_units.cpp:3927")
        self.assertEqual(sig["summary"], "12312 byte(s) leaked in 1 allocation(s).")
        self.assertEqual(sig["fingerprint"], "leak|coding_units.cpp:3927|12312 byte(s) leaked in 1 allocation(s).")

    def test_metrics_preserve_leak_summary_artifact_and_deep_project_frame_when_allocator_frames_are_first(self):
        metrics = hermes_watch.Metrics()
        for line in [
            "==535925==ERROR: LeakSanitizer: detected memory leaks",
            "Direct leak of 12312 byte(s) in 1 object(s) allocated from:",
            "    #0 0xaaa in posix_memalign (/tmp/project/build/bin/fuzzer+0x1689ab)",
            "    #1 0xbbb in AlignedLargePool::alloc(unsigned long, unsigned long) /tmp/project/source/core/common/utils.hpp:252:9",
            "    #2 0xccc in j2k_tile::decode() /tmp/project/source/core/coding/coding_units.cpp:3927:53",
            "    #3 0xddd in open_htj2k::openhtj2k_decoder_impl::invoke(...) /tmp/project/source/core/interface/decoder.cpp:358:16",
            "    #4 0xeee in (anonymous namespace)::InvokeFull(...) /tmp/project/fuzz/deep_decode_focus_v3_harness.cpp:72:11",
            "    #5 0xfff in (anonymous namespace)::RunStage(...) /tmp/project/fuzz/deep_decode_focus_v3_harness.cpp:100:7",
            "    #6 0x111 in (anonymous namespace)::DeepDecodeFocusV3OneInput(...) /tmp/project/fuzz/deep_decode_focus_v3_harness.cpp:157:9",
            "    #7 0x222 in LLVMFuzzerTestOneInput /tmp/project/fuzz/deep_decode_focus_v3_harness.cpp:195:9",
            "    #8 0x333 in fuzzer::Fuzzer::ExecuteCallback(unsigned char const*, unsigned long) (/tmp/project/build/bin/fuzzer+0xb3d94)",
            "    #9 0x444 in fuzzer::Fuzzer::RunOne(unsigned char const*, unsigned long, bool, fuzzer::InputInfo*, bool, bool*) (/tmp/project/build/bin/fuzzer+0xb3489)",
            "    #10 0x555 in fuzzer::Fuzzer::MutateAndTestOne() (/tmp/project/build/bin/fuzzer+0xb4c75)",
            "    #11 0x666 in fuzzer::Fuzzer::Loop(std::vector<fuzzer::SizedFile, std::allocator<fuzzer::SizedFile>>&) (/tmp/project/build/bin/fuzzer+0xb57d5)",
            "    #12 0x777 in fuzzer::FuzzerDriver(int*, char***, int (*)(unsigned char const*, unsigned long)) (/tmp/project/build/bin/fuzzer+0xa2aaf)",
            "    #13 0x888 in main (/tmp/project/build/bin/fuzzer+0xcd136)",
            "    #14 0x999 in __libc_start_main (/lib/x86_64-linux-gnu/libc.so.6+0x2a28a)",
            "    #15 0xabc in _start (/tmp/project/build/bin/fuzzer+0x97a94)",
            "    #16 0xdef in trailing_frame_for_limit_check (/tmp/project/build/bin/fuzzer+0x98123)",
            "SUMMARY: AddressSanitizer: 12312 byte(s) leaked in 1 allocation(s).",
            "artifact_prefix='/tmp/crashes/'; Test unit written to /tmp/crashes/leak-deadbeef",
        ]:
            metrics.update_from_line(line)

        sig = hermes_watch.build_crash_signature(metrics.top_crash_lines)
        self.assertEqual(sig["kind"], "leak")
        self.assertEqual(sig["location"], "coding_units.cpp:3927")
        self.assertEqual(sig["summary"], "12312 byte(s) leaked in 1 allocation(s).")
        self.assertEqual(sig["artifact_path"], "/tmp/crashes/leak-deadbeef")
        self.assertEqual(sig["fingerprint"], "leak|coding_units.cpp:3927|12312 byte(s) leaked in 1 allocation(s).")

    def test_load_registry_returns_default_with_error_note_for_malformed_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "broken.json"
            path.write_text("{not-json", encoding="utf-8")

            result = hermes_watch.load_registry(path, {"entries": []})

            self.assertEqual(result["entries"], [])
            self.assertEqual(result["__load_error__"], "json-decode-error")

    def test_load_registry_returns_default_with_error_note_for_wrong_top_level_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "wrong.json"
            path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

            result = hermes_watch.load_registry(path, {"entries": []})

            self.assertEqual(result["entries"], [])
            self.assertEqual(result["__load_error__"], "invalid-top-level-type")

    def test_load_crash_index_returns_default_with_error_note_for_malformed_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "crash-index.json"
            path.write_text("{broken", encoding="utf-8")

            result = hermes_watch.load_crash_index(path)

            self.assertEqual(result["fingerprints"], {})
            self.assertEqual(result["__load_error__"], "json-decode-error")

    def test_update_crash_index_repairs_wrong_type_fingerprint_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "crash-index.json"
            path.write_text(json.dumps({"fingerprints": []}), encoding="utf-8")
            signature = {
                "kind": "heap-buffer-overflow",
                "location": "foo.cpp:10",
                "summary": "WRITE of size 4",
                "artifact_path": "/tmp/artifact",
                "artifact_sha1": "abc123",
                "fingerprint": "fp-1",
            }

            result = hermes_watch.update_crash_index(path, signature, run_dir="/runs/one", report_path="/runs/one/FUZZING_REPORT.md")

            self.assertEqual(result["fingerprint"], "fp-1")
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("fp-1", stored["fingerprints"])

    def test_update_crash_index_marks_first_and_duplicate_occurrences(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "crash-index.json"
            signature = {
                "kind": "heap-buffer-overflow",
                "location": "foo.cpp:10",
                "summary": "WRITE of size 4",
                "artifact_path": "/tmp/artifact",
                "artifact_sha1": "sha1-deadbeef",
                "fingerprint": "heap-buffer-overflow|foo.cpp:10|WRITE of size 4",
            }

            first = hermes_watch.update_crash_index(index_path, signature, run_dir="/runs/one", report_path="/runs/one/FUZZING_REPORT.md")
            second = hermes_watch.update_crash_index(index_path, signature, run_dir="/runs/two", report_path="/runs/two/FUZZING_REPORT.md")

            self.assertFalse(first["is_duplicate"])
            self.assertEqual(first["occurrence_count"], 1)
            self.assertTrue(second["is_duplicate"])
            self.assertEqual(second["occurrence_count"], 2)
            index = json.loads(index_path.read_text(encoding="utf-8"))
            record = index["fingerprints"][signature["fingerprint"]]
            self.assertEqual(record["first_seen_run"], "/runs/one")
            self.assertEqual(record["last_seen_run"], "/runs/two")
            self.assertEqual(record["occurrence_count"], 2)

    def test_rehydrate_run_artifacts_reclassifies_stale_leak_metadata_without_duplicating_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            run_dir = repo_root / "fuzz-artifacts" / "runs" / "20260416_183444_1d5b676"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            run_dir.mkdir(parents=True)
            automation_dir.mkdir(parents=True)

            stale_snapshot = {
                "updated_at": "2026-04-16T18:34:44",
                "outcome": "crash",
                "cov": 42,
                "ft": 121,
                "exec_per_second": 0,
                "corpus_units": 3,
                "corpus_size": "672b",
                "seconds_since_progress": 0.2,
                "timeout_detected": False,
                "run_dir": str(run_dir),
                "report": str(run_dir / "FUZZING_REPORT.md"),
                "crash_fingerprint": "asan|unknown-location|12312 byte(s) leaked in 1 allocation(s).",
                "crash_kind": "asan",
                "crash_location": None,
                "crash_summary": "12312 byte(s) leaked in 1 allocation(s).",
                "crash_artifact": str(run_dir / "crashes" / "leak-272a1b"),
                "crash_is_duplicate": False,
                "crash_occurrence_count": 1,
                "artifact_category": "crash",
                "artifact_reason": "sanitizer-crash",
                "policy_action_code": "triage-new-crash",
                "policy_priority": "high",
                "policy_bucket": "triage",
                "policy_next_mode": "triage",
                "policy_recommended_action": "Preserve artifact, inspect stack, and promote the reproducer into triage/regression tracking.",
                "policy_matched_triggers": [],
                "policy_profile_severity": None,
                "target_profile_path": None,
            }
            (run_dir / "status.json").write_text(json.dumps(stale_snapshot), encoding="utf-8")
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(json.dumps(stale_snapshot), encoding="utf-8")
            (automation_dir / "run_history.json").write_text(
                json.dumps({"entries": [
                    {
                        "updated_at": stale_snapshot["updated_at"],
                        "outcome": stale_snapshot["outcome"],
                        "cov": stale_snapshot["cov"],
                        "ft": stale_snapshot["ft"],
                        "exec_per_second": stale_snapshot["exec_per_second"],
                        "corpus_units": stale_snapshot["corpus_units"],
                        "corpus_size": stale_snapshot["corpus_size"],
                        "seconds_since_progress": stale_snapshot["seconds_since_progress"],
                        "timeout_detected": stale_snapshot["timeout_detected"],
                        "crash_stage": None,
                        "crash_fingerprint": stale_snapshot["crash_fingerprint"],
                        "policy_profile_severity": None,
                        "policy_action_code": stale_snapshot["policy_action_code"],
                        "policy_matched_triggers": [],
                        "run_dir": stale_snapshot["run_dir"],
                        "report": stale_snapshot["report"],
                    }
                ]}),
                encoding="utf-8",
            )
            (repo_root / "fuzz-artifacts" / "crash_index.json").write_text(
                json.dumps({
                    "fingerprints": {
                        stale_snapshot["crash_fingerprint"]: {
                            "artifact_sha1": None,
                            "artifacts": [stale_snapshot["crash_artifact"]],
                            "first_seen_report": stale_snapshot["report"],
                            "first_seen_run": stale_snapshot["run_dir"],
                            "kind": "asan",
                            "last_seen_report": stale_snapshot["report"],
                            "last_seen_run": stale_snapshot["run_dir"],
                            "location": None,
                            "occurrence_count": 1,
                            "summary": stale_snapshot["crash_summary"],
                        }
                    }
                }),
                encoding="utf-8",
            )
            (run_dir / "fuzz.log").write_text(
                "\n".join(
                    [
                        "==1==ERROR: LeakSanitizer: detected memory leaks",
                        "Direct leak of 12312 byte(s) in 1 object(s) allocated from:",
                        "    #0 0xaaa in posix_memalign (/tmp/project/build/bin/fuzzer+0x1689ab)",
                        "    #1 0xbbb in AlignedLargePool::alloc(unsigned long, unsigned long) /tmp/project/source/core/common/utils.hpp:252:9",
                        "    #2 0xccc in j2k_tile::decode() /tmp/project/source/core/coding/coding_units.cpp:3927:53",
                        f"artifact_prefix='{run_dir / 'crashes'}'; Test unit written to {run_dir / 'crashes' / 'leak-272a1b'}",
                        "SUMMARY: AddressSanitizer: 12312 byte(s) leaked in 1 allocation(s).",
                    ]
                ) + "\n",
                encoding="utf-8",
            )
            (run_dir / "FUZZING_REPORT.md").write_text(
                "\n".join(
                    [
                        "# FUZZING_REPORT",
                        "",
                        "## Artifact Classification",
                        "",
                        "- artifact_category: crash",
                        "- artifact_reason: sanitizer-crash",
                        "",
                        "## Policy Action",
                        "",
                        "- policy_priority: high",
                        "- policy_action_code: triage-new-crash",
                        "- policy_next_mode: triage",
                        "- policy_bucket: triage",
                        "- policy_recommended_action: Preserve artifact, inspect stack, and promote the reproducer into triage/regression tracking.",
                        "- policy_matched_triggers: []",
                        "- policy_profile_severity: None",
                        "- policy_profile_labels: []",
                        "",
                        "## Crash Fingerprint",
                        "",
                        "- crash_kind: asan",
                        "- crash_location: None",
                        "- crash_summary: 12312 byte(s) leaked in 1 allocation(s).",
                        "- crash_stage: None",
                        "- crash_stage_class: unknown",
                        "- crash_stage_depth_rank: None",
                        "- crash_stage_confidence: none",
                        "- crash_stage_match_source: None",
                        "- crash_stage_reason: no profile match",
                        "- crash_fingerprint: asan|unknown-location|12312 byte(s) leaked in 1 allocation(s).",
                        "- crash_is_duplicate: False",
                        "- crash_occurrence_count: 1",
                        f"- crash_first_seen_run: {run_dir}",
                        f"- crash_artifact: {run_dir / 'crashes' / 'leak-272a1b'}",
                        "- crash_artifact_sha1: None",
                        "",
                        "## Crash Or Timeout Excerpt",
                        "",
                        "```text",
                        "SUMMARY: AddressSanitizer: 12312 byte(s) leaked in 1 allocation(s).",
                        "```",
                        "",
                        "## Recommended Next Action",
                        "",
                        "- Preserve crash artifact locally. Ask Codex to inspect the sanitizer stack before pushing any reproducer.",
                        "",
                    ]
                ) + "\n",
                encoding="utf-8",
            )

            result = hermes_watch.rehydrate_run_artifacts(repo_root, run_dir=run_dir)

            self.assertTrue(result["rehydrated"])
            self.assertEqual(result["crash_fingerprint"], "leak|coding_units.cpp:3927|12312 byte(s) leaked in 1 allocation(s).")
            updated_status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(updated_status["crash_kind"], "leak")
            self.assertEqual(updated_status["crash_location"], "coding_units.cpp:3927")
            self.assertEqual(updated_status["artifact_category"], "leak")
            self.assertEqual(updated_status["artifact_reason"], "sanitizer-leak")
            self.assertEqual(updated_status["policy_action_code"], "triage-leak-and-consider-coverage-policy")
            current_status = json.loads((repo_root / "fuzz-artifacts" / "current_status.json").read_text(encoding="utf-8"))
            self.assertEqual(current_status["crash_fingerprint"], updated_status["crash_fingerprint"])
            history = json.loads((automation_dir / "run_history.json").read_text(encoding="utf-8"))
            self.assertEqual(len(history["entries"]), 1)
            self.assertEqual(history["entries"][0]["crash_fingerprint"], updated_status["crash_fingerprint"])
            crash_index = json.loads((repo_root / "fuzz-artifacts" / "crash_index.json").read_text(encoding="utf-8"))
            self.assertNotIn(stale_snapshot["crash_fingerprint"], crash_index["fingerprints"])
            self.assertIn(updated_status["crash_fingerprint"], crash_index["fingerprints"])
            updated_report = (run_dir / "FUZZING_REPORT.md").read_text(encoding="utf-8")
            self.assertIn("- artifact_category: leak", updated_report)
            self.assertIn("- artifact_reason: sanitizer-leak", updated_report)
            self.assertIn("- policy_action_code: triage-leak-and-consider-coverage-policy", updated_report)
            self.assertIn("- policy_next_mode: coverage", updated_report)
            self.assertIn("- crash_kind: leak", updated_report)
            self.assertIn("- crash_location: coding_units.cpp:3927", updated_report)
            self.assertIn("- crash_fingerprint: leak|coding_units.cpp:3927|12312 byte(s) leaked in 1 allocation(s).", updated_report)
            self.assertIn("==1==ERROR: LeakSanitizer: detected memory leaks", updated_report)
            self.assertIn("artifact_prefix='", updated_report)
            self.assertIn(
                "- Record the leak, inspect allocation/free paths, and decide whether coverage mode should keep detect_leaks=0.",
                updated_report,
            )
            self.assertNotIn("Ask Codex to inspect the sanitizer stack", updated_report)

    def test_write_report_uses_policy_recommended_action_in_recommended_next_action_section(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            report_path = repo_root / "FUZZING_REPORT.md"
            build_log = repo_root / "build.log"
            smoke_log = repo_root / "smoke.log"
            fuzz_log = repo_root / "fuzz.log"
            for path in (build_log, smoke_log, fuzz_log):
                path.write_text("", encoding="utf-8")

            metrics = hermes_watch.Metrics()
            metrics.crash = True
            metrics.top_crash_lines = [
                "==1==ERROR: LeakSanitizer: detected memory leaks",
                "SUMMARY: AddressSanitizer: 12312 byte(s) leaked in 1 allocation(s).",
            ]
            adapter = hermes_watch.get_target_adapter(None)

            hermes_watch.write_report(
                report_path,
                outcome="crash",
                repo_root=repo_root,
                run_dir=repo_root / "fuzz-artifacts" / "runs" / "demo",
                command=["bash", "scripts/run-fuzzer.sh"],
                exit_code=77,
                metrics=metrics,
                duration_s=0.3,
                build_log=build_log,
                smoke_log=smoke_log,
                fuzz_log=fuzz_log,
                target_adapter=adapter,
                crash_info={
                    "kind": "leak",
                    "location": "coding_units.cpp:3927",
                    "summary": "12312 byte(s) leaked in 1 allocation(s).",
                    "stage": "tile-part-load",
                    "stage_class": "medium",
                    "stage_depth_rank": 2,
                    "stage_confidence": "medium",
                    "stage_match_source": "signal",
                    "stage_reason": "expected signal match: coding_units.cpp",
                    "fingerprint": "leak|coding_units.cpp:3927|12312 byte(s) leaked in 1 allocation(s).",
                    "is_duplicate": True,
                    "occurrence_count": 3,
                    "first_seen_run": "/runs/demo",
                    "artifact_path": "/runs/demo/crashes/leak-demo",
                    "artifact_sha1": "deadbeef",
                },
                artifact_event={"category": "leak", "reason": "sanitizer-leak"},
                policy_action={
                    "priority": "medium",
                    "action_code": "triage-leak-and-consider-coverage-policy",
                    "next_mode": "coverage",
                    "bucket": "triage",
                    "recommended_action": "Record the leak, inspect allocation/free paths, and decide whether coverage mode should keep detect_leaks=0.",
                    "matched_triggers": [],
                    "profile_severity": None,
                    "profile_labels": [],
                },
                policy_execution={"updated": ["policy_log"], "regression_trigger": None},
                target_profile_summary=None,
                notification_event={"status": "skipped", "transport": "disabled", "reason": "missing-config", "error_type": None, "error": None, "context": "final-summary"},
            )

            report_text = report_path.read_text(encoding="utf-8")
            self.assertIn(
                "- Record the leak, inspect allocation/free paths, and decide whether coverage mode should keep detect_leaks=0.",
                report_text,
            )
            self.assertNotIn("Ask Codex to inspect the sanitizer stack", report_text)

    def test_classify_artifact_event_prefers_leak_over_generic_crash(self):
        crash_info = {
            "kind": "leak",
            "fingerprint": "leak|coding_units.cpp:3927|12312 bytes leaked",
        }
        event = hermes_watch.classify_artifact_event("crash", crash_info)
        self.assertEqual(event["category"], "leak")
        self.assertEqual(event["reason"], "sanitizer-leak")

    def test_classify_artifact_event_marks_timeout(self):
        event = hermes_watch.classify_artifact_event("timeout", None)
        self.assertEqual(event["category"], "timeout")
        self.assertEqual(event["reason"], "watcher-timeout")

    def test_classify_artifact_event_marks_no_progress(self):
        event = hermes_watch.classify_artifact_event("no-progress", None)
        self.assertEqual(event["category"], "no-progress")
        self.assertEqual(event["reason"], "stalled-coverage-or-corpus")

    def test_classify_artifact_event_defaults_ubsan_to_crash(self):
        crash_info = {
            "kind": "ubsan",
            "fingerprint": "ubsan|block_decoding.cpp:86|undefined-behavior ...",
        }
        event = hermes_watch.classify_artifact_event("crash", crash_info)
        self.assertEqual(event["category"], "crash")
        self.assertEqual(event["reason"], "sanitizer-crash")

    def test_decide_policy_action_prioritizes_new_crash(self):
        artifact_event = {"category": "crash", "reason": "sanitizer-crash"}
        crash_info = {
            "is_duplicate": False,
            "fingerprint": "ubsan|block_decoding.cpp:86|undefined-behavior ...",
        }
        action = hermes_watch.decide_policy_action("crash", artifact_event, crash_info)
        self.assertEqual(action["priority"], "high")
        self.assertEqual(action["action_code"], "triage-new-crash")
        self.assertEqual(action["next_mode"], "triage")
        self.assertEqual(action["bucket"], "triage")

    def test_decide_policy_action_downgrades_duplicate_crash(self):
        artifact_event = {"category": "crash", "reason": "sanitizer-crash"}
        crash_info = {
            "is_duplicate": True,
            "fingerprint": "ubsan|block_decoding.cpp:86|undefined-behavior ...",
        }
        action = hermes_watch.decide_policy_action("crash", artifact_event, crash_info)
        self.assertEqual(action["priority"], "medium")
        self.assertEqual(action["action_code"], "record-duplicate-crash")

    def test_decide_policy_action_escalates_repeated_deep_critical_duplicate_to_replay_review(self):
        artifact_event = {"category": "crash", "reason": "sanitizer-crash"}
        crash_info = {
            "is_duplicate": True,
            "fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow ...",
            "occurrence_count": 2,
            "stage_class": "deep",
        }
        action = hermes_watch.decide_policy_action("crash", artifact_event, crash_info)
        self.assertEqual(action["priority"], "high")
        self.assertEqual(action["action_code"], "review_duplicate_crash_replay")
        self.assertEqual(action["next_mode"], "triage")
        self.assertEqual(action["bucket"], "triage")

    def test_decide_policy_action_escalates_repeated_medium_duplicate_to_replay_review(self):
        artifact_event = {"category": "crash", "reason": "sanitizer-crash"}
        crash_info = {
            "is_duplicate": True,
            "fingerprint": "asan|coding_units.cpp:3076|SEGV ...",
            "occurrence_count": 2,
            "stage_class": "medium",
            "stage_depth_rank": 2,
        }
        action = hermes_watch.decide_policy_action("crash", artifact_event, crash_info)
        self.assertEqual(action["priority"], "high")
        self.assertEqual(action["action_code"], "review_duplicate_crash_replay")
        self.assertEqual(action["next_mode"], "triage")
        self.assertEqual(action["bucket"], "triage")

    def test_decide_policy_action_handles_leak(self):
        artifact_event = {"category": "leak", "reason": "sanitizer-leak"}
        action = hermes_watch.decide_policy_action("crash", artifact_event, None)
        self.assertEqual(action["action_code"], "triage-leak-and-consider-coverage-policy")
        self.assertEqual(action["next_mode"], "coverage")

    def test_decide_policy_action_handles_no_progress(self):
        artifact_event = {"category": "no-progress", "reason": "stalled-coverage-or-corpus"}
        action = hermes_watch.decide_policy_action("no-progress", artifact_event, None)
        self.assertEqual(action["action_code"], "improve-corpus-or-harness")
        self.assertEqual(action["priority"], "medium")

    def test_repair_latest_crash_state_reclassifies_stale_leak_across_status_history_and_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            run_dir = repo_root / "fuzz-artifacts" / "runs" / "run-1"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            run_dir.mkdir(parents=True)
            automation_dir.mkdir(parents=True)
            artifact_path = run_dir / "crashes" / "leak-deadbeef"
            artifact_path.parent.mkdir(parents=True)
            artifact_path.write_text("boom", encoding="utf-8")
            report_path = run_dir / "FUZZING_REPORT.md"
            report_path.write_text("# report\n", encoding="utf-8")
            fuzz_log_path = run_dir / "fuzz.log"
            fuzz_log_path.write_text(
                "INFO: Loaded 1 modules\n"
                "==1==ERROR: LeakSanitizer: detected memory leaks\n"
                "Direct leak of 12312 byte(s) in 1 object(s) allocated from:\n"
                "    #0 0xaaa in posix_memalign (/tmp/project/build/bin/fuzzer+0x1689ab)\n"
                "    #1 0xbbb in AlignedLargePool::alloc(unsigned long, unsigned long) /tmp/project/source/core/common/utils.hpp:252:9\n"
                f"    #2 0xccc in j2k_tile::decode() {repo_root}/source/core/coding/coding_units.cpp:3927:53\n"
                "SUMMARY: AddressSanitizer: 12312 byte(s) leaked in 1 allocation(s).\n"
                f"artifact_prefix='{artifact_path.parent}/'; Test unit written to {artifact_path}\n",
                encoding="utf-8",
            )
            stale_snapshot = {
                "outcome": "crash",
                "cov": 42,
                "ft": 121,
                "corpus_units": 3,
                "corpus_size": "672b",
                "exec_per_second": 0,
                "rss": "38Mb",
                "crash_detected": True,
                "timeout_detected": False,
                "run_dir": str(run_dir),
                "report": str(report_path),
                "updated_at": "2026-04-16T18:34:44",
                "crash_fingerprint": "asan|unknown-location|12312 byte(s) leaked in 1 allocation(s).",
                "crash_kind": "asan",
                "crash_location": None,
                "crash_summary": "12312 byte(s) leaked in 1 allocation(s).",
                "crash_artifact": str(artifact_path),
                "crash_artifact_sha1": hermes_watch.sha1_file(artifact_path),
                "crash_is_duplicate": False,
                "crash_occurrence_count": 1,
                "crash_first_seen_run": str(run_dir),
                "crash_stage": None,
                "crash_stage_class": "unknown",
                "crash_stage_depth_rank": None,
                "crash_stage_confidence": "none",
                "crash_stage_match_source": None,
                "crash_stage_reason": "no profile match",
                "artifact_category": "crash",
                "artifact_reason": "sanitizer-crash",
                "policy_priority": "high",
                "policy_action_code": "triage-new-crash",
                "policy_recommended_action": "Preserve artifact, inspect stack, and promote the reproducer into triage/regression tracking.",
                "policy_next_mode": "triage",
                "policy_bucket": "triage",
                "policy_matched_triggers": [],
                "policy_profile_severity": None,
                "policy_profile_labels": [],
                "target_profile_path": str(repo_root / "fuzz-records" / "profiles" / "openhtj2k-target-profile-v1.yaml"),
            }
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(json.dumps(stale_snapshot), encoding="utf-8")
            (run_dir / "status.json").write_text(json.dumps(stale_snapshot), encoding="utf-8")
            (repo_root / "fuzz-artifacts" / "crash_index.json").write_text(
                json.dumps(
                    {
                        "fingerprints": {
                            "asan|unknown-location|12312 byte(s) leaked in 1 allocation(s).": {
                                "artifact_sha1": hermes_watch.sha1_file(artifact_path),
                                "artifacts": [str(artifact_path)],
                                "first_seen_report": str(report_path),
                                "first_seen_run": str(run_dir),
                                "kind": "asan",
                                "last_seen_report": str(report_path),
                                "last_seen_run": str(run_dir),
                                "location": None,
                                "occurrence_count": 1,
                                "summary": "12312 byte(s) leaked in 1 allocation(s).",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            (automation_dir / "run_history.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "updated_at": "2026-04-16T18:34:44",
                                "outcome": "crash",
                                "cov": 42,
                                "ft": 121,
                                "exec_per_second": 0,
                                "corpus_units": 3,
                                "corpus_size": "672b",
                                "seconds_since_progress": 0.2,
                                "timeout_detected": False,
                                "crash_stage": None,
                                "crash_fingerprint": "asan|unknown-location|12312 byte(s) leaked in 1 allocation(s).",
                                "policy_profile_severity": None,
                                "policy_action_code": "triage-new-crash",
                                "policy_matched_triggers": [],
                                "run_dir": str(run_dir),
                                "report": str(report_path),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            original_load = hermes_watch.load_target_profile
            try:
                hermes_watch.load_target_profile = lambda _path: {
                    "stages": [{"id": "tile-decode", "stage_class": "deep", "depth_rank": 4}],
                    "telemetry": {"stack_tagging": {"stage_file_map": {"tile-decode": ["source/core/coding/coding_units.cpp"]}}},
                }
                result = hermes_watch.repair_latest_crash_state(repo_root)
            finally:
                hermes_watch.load_target_profile = original_load

            self.assertTrue(result["repaired"])
            self.assertEqual(result["new_fingerprint"], "leak|coding_units.cpp:3927|12312 byte(s) leaked in 1 allocation(s).")
            repaired_status = json.loads((repo_root / "fuzz-artifacts" / "current_status.json").read_text(encoding="utf-8"))
            self.assertEqual(repaired_status["artifact_category"], "leak")
            self.assertEqual(repaired_status["artifact_reason"], "sanitizer-leak")
            self.assertEqual(repaired_status["crash_kind"], "leak")
            self.assertEqual(repaired_status["crash_location"], "coding_units.cpp:3927")
            self.assertEqual(repaired_status["policy_action_code"], "triage-leak-and-consider-coverage-policy")
            self.assertEqual(repaired_status["policy_next_mode"], "coverage")
            repaired_run_status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(repaired_run_status["crash_fingerprint"], "leak|coding_units.cpp:3927|12312 byte(s) leaked in 1 allocation(s).")
            repaired_history = json.loads((automation_dir / "run_history.json").read_text(encoding="utf-8"))
            self.assertEqual(repaired_history["entries"][-1]["crash_fingerprint"], "leak|coding_units.cpp:3927|12312 byte(s) leaked in 1 allocation(s).")
            self.assertEqual(repaired_history["entries"][-1]["policy_action_code"], "triage-leak-and-consider-coverage-policy")
            repaired_index = json.loads((repo_root / "fuzz-artifacts" / "crash_index.json").read_text(encoding="utf-8"))
            self.assertNotIn("asan|unknown-location|12312 byte(s) leaked in 1 allocation(s).", repaired_index["fingerprints"])
            self.assertIn("leak|coding_units.cpp:3927|12312 byte(s) leaked in 1 allocation(s).", repaired_index["fingerprints"])

    def test_decide_policy_action_handles_build_failed(self):
        artifact_event = {"category": "build-failed", "reason": "build-or-config-error"}
        action = hermes_watch.decide_policy_action("build-failed", artifact_event, None)
        self.assertEqual(action["action_code"], "fix-build-before-fuzzing")
        self.assertEqual(action["next_mode"], "regression")

    def test_apply_policy_action_records_duplicate_crash_in_known_bad_and_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_action = {
                "action_code": "record-duplicate-crash",
                "bucket": "known-bad",
                "priority": "medium",
                "next_mode": "coverage",
                "recommended_action": "Record duplicate occurrence",
            }
            artifact_event = {"category": "crash", "reason": "sanitizer-crash"}
            crash_info = {
                "fingerprint": "ubsan|block_decoding.cpp:86|undefined-behavior ...",
                "artifact_path": "/tmp/crashes/crash-1",
                "location": "block_decoding.cpp:86",
                "summary": "undefined-behavior ...",
            }
            result = hermes_watch.apply_policy_action(
                root,
                run_dir="/runs/one",
                report_path="/runs/one/FUZZING_REPORT.md",
                outcome="crash",
                artifact_event=artifact_event,
                policy_action=policy_action,
                crash_info=crash_info,
            )
            self.assertIn("known_bad", result["updated"])
            self.assertIn("policy_log", result["updated"])
            known_bad = json.loads((root / "known_bad.json").read_text(encoding="utf-8"))
            self.assertIn(crash_info["fingerprint"], known_bad["fingerprints"])

    def test_apply_policy_action_routes_duplicate_crash_replay_review_into_refiner_queue(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_action = {
                "action_code": "review_duplicate_crash_replay",
                "bucket": "triage",
                "priority": "high",
                "next_mode": "triage",
                "recommended_action": "Preserve duplicate family evidence and prepare replay/minimization triage.",
            }
            artifact_event = {"category": "crash", "reason": "sanitizer-crash"}
            crash_info = {
                "fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                "artifact_path": "/tmp/crashes/crash-2",
                "first_artifact_path": "/tmp/crashes/crash-1",
                "artifacts": ["/tmp/crashes/crash-1", "/tmp/crashes/crash-2"],
                "location": "j2kmarkers.cpp:52",
                "summary": "heap-buffer-overflow",
                "occurrence_count": 2,
                "first_seen_run": "/runs/first",
                "first_seen_report": "/runs/first/FUZZING_REPORT.md",
                "last_seen_run": "/runs/dup-two",
            }
            result = hermes_watch.apply_policy_action(
                root,
                run_dir="/runs/dup-two",
                report_path="/runs/dup-two/FUZZING_REPORT.md",
                outcome="crash",
                artifact_event=artifact_event,
                policy_action=policy_action,
                crash_info=crash_info,
            )
            self.assertIn("known_bad", result["updated"])
            self.assertIn("duplicate_crash_reviews", result["updated"])
            registry = json.loads((root / "duplicate_crash_reviews.json").read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["action_code"], "review_duplicate_crash_replay")
            self.assertEqual(entry["crash_fingerprint"], crash_info["fingerprint"])
            self.assertEqual(entry["occurrence_count"], 2)
            self.assertEqual(entry["first_seen_report_path"], "/runs/first/FUZZING_REPORT.md")
            self.assertEqual(entry["first_artifact_path"], "/tmp/crashes/crash-1")

    def test_apply_policy_action_refreshes_existing_duplicate_crash_review_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            existing_registry = {
                "entries": [
                    {
                        "key": "review_duplicate_crash_replay:asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                        "action_code": "review_duplicate_crash_replay",
                        "run_dir": "/runs/dup-two",
                        "report_path": "/runs/dup-two/FUZZING_REPORT.md",
                        "outcome": "crash",
                        "artifact_category": "crash",
                        "recommended_action": "Preserve duplicate family evidence and prepare replay/minimization triage.",
                        "crash_fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                        "crash_location": "j2kmarkers.cpp:52",
                        "crash_summary": "heap-buffer-overflow",
                        "occurrence_count": 2,
                        "first_seen_run": "/runs/first",
                        "first_seen_report_path": "/runs/first/FUZZING_REPORT.md",
                        "last_seen_run": "/runs/dup-two",
                        "latest_artifact_path": "/tmp/crashes/crash-2",
                        "first_artifact_path": "/tmp/crashes/crash-1",
                        "artifact_paths": ["/tmp/crashes/crash-1", "/tmp/crashes/crash-2"],
                        "status": "completed",
                        "executor_plan_path": "/plans/dup-two.md",
                    }
                ]
            }
            (root / "duplicate_crash_reviews.json").write_text(json.dumps(existing_registry), encoding="utf-8")
            policy_action = {
                "action_code": "review_duplicate_crash_replay",
                "bucket": "triage",
                "priority": "high",
                "next_mode": "triage",
                "recommended_action": "Preserve duplicate family evidence and prepare replay/minimization triage.",
            }
            artifact_event = {"category": "crash", "reason": "sanitizer-crash"}
            crash_info = {
                "fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                "artifact_path": "/tmp/crashes/crash-4",
                "first_artifact_path": "/tmp/crashes/crash-1",
                "artifacts": ["/tmp/crashes/crash-1", "/tmp/crashes/crash-2", "/tmp/crashes/crash-4"],
                "location": "j2kmarkers.cpp:52",
                "summary": "heap-buffer-overflow",
                "occurrence_count": 4,
                "first_seen_run": "/runs/first",
                "first_seen_report": "/runs/first/FUZZING_REPORT.md",
                "last_seen_run": "/runs/dup-four",
            }

            result = hermes_watch.apply_policy_action(
                root,
                run_dir="/runs/dup-four",
                report_path="/runs/dup-four/FUZZING_REPORT.md",
                outcome="crash",
                artifact_event=artifact_event,
                policy_action=policy_action,
                crash_info=crash_info,
            )

            self.assertIn("duplicate_crash_reviews", result["updated"])
            registry = json.loads((root / "duplicate_crash_reviews.json").read_text(encoding="utf-8"))
            self.assertEqual(len(registry["entries"]), 1)
            entry = registry["entries"][0]
            self.assertEqual(entry["run_dir"], "/runs/dup-four")
            self.assertEqual(entry["report_path"], "/runs/dup-four/FUZZING_REPORT.md")
            self.assertEqual(entry["last_seen_run"], "/runs/dup-four")
            self.assertEqual(entry["occurrence_count"], 4)
            self.assertEqual(entry["latest_artifact_path"], "/tmp/crashes/crash-4")
            self.assertEqual(entry["artifact_paths"], ["/tmp/crashes/crash-1", "/tmp/crashes/crash-2", "/tmp/crashes/crash-4"])
            self.assertEqual(entry["executor_plan_path"], "/plans/dup-two.md")

    def test_apply_policy_action_records_smoke_failed_in_regression_candidates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_action = {
                "action_code": "promote-seed-to-regression-and-triage",
                "bucket": "regression",
                "priority": "high",
                "next_mode": "triage",
                "recommended_action": "Promote failing baseline input",
            }
            artifact_event = {"category": "smoke-failed", "reason": "baseline-input-failed"}
            result = hermes_watch.apply_policy_action(
                root,
                run_dir="/runs/smoke",
                report_path="/runs/smoke/FUZZING_REPORT.md",
                outcome="smoke-failed",
                artifact_event=artifact_event,
                policy_action=policy_action,
                crash_info=None,
            )
            self.assertIn("regression_candidates", result["updated"])
            reg = json.loads((root / "regression_candidates.json").read_text(encoding="utf-8"))
            self.assertEqual(reg["entries"][0]["category"], "smoke-failed")

    def test_apply_policy_action_records_critical_crash_triage_trigger_and_auto_runs_it(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            policy_action = {
                "action_code": "continue_and_prioritize_triage",
                "bucket": "critical",
                "priority": "critical",
                "next_mode": "triage",
                "recommended_action": "Prioritize deep-stage triage",
            }
            artifact_event = {"category": "crash", "reason": "sanitizer-crash"}
            crash_info = {
                "fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                "location": "j2kmarkers.cpp:52",
                "summary": "heap-buffer-overflow",
                "artifact_path": "/runs/crash/crashes/crash-seed",
            }

            original_run_quiet = hermes_watch.run_quiet
            calls = []

            def fake_run_quiet(cmd, cwd):
                calls.append({"cmd": cmd, "cwd": str(cwd)})
                return 0, "TRIAGE_OK"

            hermes_watch.run_quiet = fake_run_quiet
            try:
                result = hermes_watch.apply_policy_action(
                    root,
                    run_dir="/runs/crash",
                    report_path="/runs/crash/FUZZING_REPORT.md",
                    outcome="crash",
                    artifact_event=artifact_event,
                    policy_action=policy_action,
                    crash_info=crash_info,
                    repo_root=repo_root,
                    current_mode="fuzz",
                )
            finally:
                hermes_watch.run_quiet = original_run_quiet

            self.assertIn("regression_trigger", result["updated"])
            self.assertIn("regression_auto_run", result["updated"])
            self.assertEqual(calls[0]["cmd"], ["bash", "scripts/run-fuzz-mode.sh", "triage"])
            reg = json.loads((root / "regression_triggers.json").read_text(encoding="utf-8"))
            self.assertEqual(reg["entries"][0]["trigger_reason"], "continue_and_prioritize_triage")
            self.assertEqual(reg["entries"][0]["status"], "completed")
            self.assertEqual(reg["entries"][0]["exit_code"], 0)

    def test_should_trigger_regression_returns_true_for_build_failed(self):
        policy_action = {"action_code": "fix-build-before-fuzzing"}
        self.assertTrue(hermes_watch.should_trigger_regression("build-failed", policy_action))

    def test_should_trigger_regression_returns_true_for_smoke_failed(self):
        policy_action = {"action_code": "promote-seed-to-regression-and-triage"}
        self.assertTrue(hermes_watch.should_trigger_regression("smoke-failed", policy_action))

    def test_should_trigger_regression_returns_false_for_duplicate_crash(self):
        policy_action = {"action_code": "record-duplicate-crash"}
        self.assertFalse(hermes_watch.should_trigger_regression("crash", policy_action))

    def test_should_trigger_regression_returns_true_for_continue_and_prioritize_triage(self):
        policy_action = {"action_code": "continue_and_prioritize_triage"}
        self.assertTrue(hermes_watch.should_trigger_regression("crash", policy_action))

    def test_record_regression_trigger_writes_registry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = hermes_watch.record_regression_trigger(
                root,
                run_dir="/runs/example",
                report_path="/runs/example/FUZZING_REPORT.md",
                trigger_reason="build-failed",
                command=["bash", "scripts/run-fuzz-mode.sh", "regression"],
            )
            self.assertEqual(result["status"], "recorded")
            reg = json.loads((root / "regression_triggers.json").read_text(encoding="utf-8"))
            self.assertEqual(reg["entries"][0]["trigger_reason"], "build-failed")

    def test_record_regression_trigger_deduplicates_same_seed_and_tracks_occurrence_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            first = hermes_watch.record_regression_trigger(
                root,
                run_dir="/runs/one",
                report_path="/runs/one/FUZZING_REPORT.md",
                trigger_reason="promote-seed-to-regression-and-triage",
                command=["bash", "scripts/run-fuzz-mode.sh", "regression"],
                seed_path="/repo/conformance_data/p0_12.j2k",
            )
            second = hermes_watch.record_regression_trigger(
                root,
                run_dir="/runs/two",
                report_path="/runs/two/FUZZING_REPORT.md",
                trigger_reason="promote-seed-to-regression-and-triage",
                command=["bash", "scripts/run-fuzz-mode.sh", "regression"],
                seed_path="/repo/conformance_data/p0_12.j2k",
            )

            reg = json.loads((root / "regression_triggers.json").read_text(encoding="utf-8"))
            self.assertEqual(len(reg["entries"]), 1)
            self.assertEqual(reg["entries"][0]["occurrence_count"], 2)
            self.assertEqual(reg["entries"][0]["last_seen_run"], "/runs/two")
            self.assertEqual(first["dedup_key"], second["dedup_key"])

    def test_record_regression_trigger_assigns_priority_and_queue_rank(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            hermes_watch.record_regression_trigger(
                root,
                run_dir="/runs/smoke",
                report_path="/runs/smoke/FUZZING_REPORT.md",
                trigger_reason="promote-seed-to-regression-and-triage",
                command=["bash", "scripts/run-fuzz-mode.sh", "regression"],
                seed_path="/repo/conformance_data/p0_12.j2k",
            )
            hermes_watch.record_regression_trigger(
                root,
                run_dir="/runs/build",
                report_path="/runs/build/FUZZING_REPORT.md",
                trigger_reason="fix-build-before-fuzzing",
                command=["bash", "scripts/run-fuzz-mode.sh", "regression"],
            )

            reg = json.loads((root / "regression_triggers.json").read_text(encoding="utf-8"))
            self.assertEqual(reg["entries"][0]["trigger_reason"], "fix-build-before-fuzzing")
            self.assertEqual(reg["entries"][0]["queue_rank"], 1)
            self.assertEqual(reg["entries"][1]["queue_rank"], 2)
            self.assertGreater(reg["entries"][0]["priority"], reg["entries"][1]["priority"])

    def test_execute_regression_queue_runs_only_top_pending_trigger(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            hermes_watch.record_regression_trigger(
                root,
                run_dir="/runs/smoke",
                report_path="/runs/smoke/FUZZING_REPORT.md",
                trigger_reason="promote-seed-to-regression-and-triage",
                command=["bash", "scripts/run-fuzz-mode.sh", "regression"],
                seed_path="/repo/conformance_data/p0_12.j2k",
            )
            hermes_watch.record_regression_trigger(
                root,
                run_dir="/runs/build",
                report_path="/runs/build/FUZZING_REPORT.md",
                trigger_reason="fix-build-before-fuzzing",
                command=["bash", "scripts/run-fuzz-mode.sh", "regression"],
            )

            original_run_quiet = hermes_watch.run_quiet
            calls = []

            def fake_run_quiet(cmd, cwd):
                calls.append({"cmd": cmd, "cwd": str(cwd)})
                return 0, "QUEUE_OK"

            hermes_watch.run_quiet = fake_run_quiet
            try:
                result = hermes_watch.execute_next_regression_trigger(root, repo_root=repo_root, current_mode="triage")
            finally:
                hermes_watch.run_quiet = original_run_quiet

            self.assertEqual(result["trigger_reason"], "fix-build-before-fuzzing")
            self.assertEqual(len(calls), 1)
            reg = json.loads((root / "regression_triggers.json").read_text(encoding="utf-8"))
            self.assertEqual(reg["entries"][0]["status"], "completed")
            self.assertEqual(reg["entries"][1]["status"], "recorded")

    def test_normalize_regression_triggers_repairs_legacy_seedless_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            automation_dir = root / "automation"
            run_dir = repo_root / "fuzz-artifacts" / "runs" / "example"
            run_dir.mkdir(parents=True)
            report_path = run_dir / "FUZZING_REPORT.md"
            report_path.write_text("dummy", encoding="utf-8")
            (run_dir / "smoke.log").write_text(
                'run-smoke.sh: line 13: 1 Aborted "${harness}" --expect-ok "${repo_root}/conformance_data/p0_12.j2k"\n',
                encoding="utf-8",
            )
            seed = repo_root / "conformance_data" / "p0_12.j2k"
            seed.parent.mkdir(parents=True)
            seed.write_bytes(b"seed")
            automation_dir.mkdir(parents=True)
            (automation_dir / "regression_triggers.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "promote-seed-to-regression-and-triage:/runs/example",
                                "trigger_reason": "promote-seed-to-regression-and-triage",
                                "report_path": str(report_path),
                                "run_dir": "/runs/example",
                                "status": "recorded",
                                "priority": 80,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.normalize_regression_triggers(automation_dir, repo_root=repo_root)
            self.assertGreaterEqual(result["updated_count"], 1)
            reg = json.loads((automation_dir / "regression_triggers.json").read_text(encoding="utf-8"))
            self.assertEqual(reg["entries"][0]["seed_path"], str(seed))
            self.assertEqual(
                reg["entries"][0]["dedup_key"],
                f"promote-seed-to-regression-and-triage:{seed}",
            )

    def test_execute_regression_trigger_runs_command_and_updates_registry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            hermes_watch.record_regression_trigger(
                root,
                run_dir="/runs/example",
                report_path="/runs/example/FUZZING_REPORT.md",
                trigger_reason="build-failed",
                command=["bash", "scripts/run-fuzz-mode.sh", "regression"],
            )
            trigger = json.loads((root / "regression_triggers.json").read_text(encoding="utf-8"))["entries"][0]

            original_run_quiet = hermes_watch.run_quiet
            calls = []

            def fake_run_quiet(cmd, cwd):
                calls.append({"cmd": cmd, "cwd": str(cwd)})
                return 0, "REGRESSION_OK"

            hermes_watch.run_quiet = fake_run_quiet
            try:
                result = hermes_watch.execute_regression_trigger(root, repo_root=repo_root, trigger=trigger, current_mode="triage")
            finally:
                hermes_watch.run_quiet = original_run_quiet

            self.assertEqual(result["status"], "completed")
            self.assertEqual(calls[0]["cmd"], ["bash", "scripts/run-fuzz-mode.sh", "regression"])
            self.assertEqual(calls[0]["cwd"], str(repo_root))
            reg = json.loads((root / "regression_triggers.json").read_text(encoding="utf-8"))
            self.assertEqual(reg["entries"][0]["status"], "completed")
            self.assertEqual(reg["entries"][0]["exit_code"], 0)

    def test_execute_regression_trigger_skips_when_already_in_regression_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            hermes_watch.record_regression_trigger(
                root,
                run_dir="/runs/example",
                report_path="/runs/example/FUZZING_REPORT.md",
                trigger_reason="smoke-failed",
                command=["bash", "scripts/run-fuzz-mode.sh", "regression"],
            )
            trigger = json.loads((root / "regression_triggers.json").read_text(encoding="utf-8"))["entries"][0]

            original_run_quiet = hermes_watch.run_quiet
            calls = []

            def fake_run_quiet(cmd, cwd):
                calls.append({"cmd": cmd, "cwd": str(cwd)})
                return 0, "SHOULD_NOT_RUN"

            hermes_watch.run_quiet = fake_run_quiet
            try:
                result = hermes_watch.execute_regression_trigger(root, repo_root=repo_root, trigger=trigger, current_mode="regression")
            finally:
                hermes_watch.run_quiet = original_run_quiet

            self.assertEqual(result["status"], "skipped-already-in-regression")
            self.assertEqual(calls, [])
            reg = json.loads((root / "regression_triggers.json").read_text(encoding="utf-8"))
            self.assertEqual(reg["entries"][0]["status"], "skipped-already-in-regression")

    def test_execute_regression_trigger_skips_when_already_in_triage_mode_for_triage_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            hermes_watch.record_regression_trigger(
                root,
                run_dir="/runs/example",
                report_path="/runs/example/FUZZING_REPORT.md",
                trigger_reason="continue_and_prioritize_triage",
                command=["bash", "scripts/run-fuzz-mode.sh", "triage"],
            )
            trigger = json.loads((root / "regression_triggers.json").read_text(encoding="utf-8"))["entries"][0]

            original_run_quiet = hermes_watch.run_quiet
            calls = []

            def fake_run_quiet(cmd, cwd):
                calls.append({"cmd": cmd, "cwd": str(cwd)})
                return 0, "SHOULD_NOT_RUN"

            hermes_watch.run_quiet = fake_run_quiet
            try:
                result = hermes_watch.execute_regression_trigger(root, repo_root=repo_root, trigger=trigger, current_mode="triage")
            finally:
                hermes_watch.run_quiet = original_run_quiet

            self.assertEqual(result["status"], "skipped-already-in-triage")
            self.assertEqual(calls, [])
            reg = json.loads((root / "regression_triggers.json").read_text(encoding="utf-8"))
            self.assertEqual(reg["entries"][0]["status"], "skipped-already-in-triage")

    def test_extract_smoke_failure_input_path_finds_failing_seed(self):
        smoke_output = """decoder accepted input: 1 component(s)\nrun-smoke.sh: line 13: 15772 Aborted                 \"${harness}\" --expect-ok \"/tmp/project/conformance_data/p0_12.j2k\"\n"""
        self.assertEqual(
            hermes_watch.extract_smoke_failure_input_path(smoke_output),
            "/tmp/project/conformance_data/p0_12.j2k",
        )

    def test_extract_smoke_failure_input_path_expands_repo_root_placeholder(self):
        smoke_output = 'run-smoke.sh: line 13: 15772 Aborted "${harness}" --expect-ok "${repo_root}/conformance_data/p0_12.j2k"\n'
        self.assertEqual(
            hermes_watch.extract_smoke_failure_input_path(smoke_output, repo_root=Path("/tmp/project")),
            "/tmp/project/conformance_data/p0_12.j2k",
        )

    def test_sync_corpus_from_registry_copies_known_bad_and_regression_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            automation_dir = root / "automation"
            known_bad_dir = repo_root / "fuzz" / "corpus" / "known-bad"
            regression_dir = repo_root / "fuzz" / "corpus" / "regression"
            known_bad_dir.mkdir(parents=True)
            regression_dir.mkdir(parents=True)

            known_bad_src = root / "artifacts" / "crash-seed.j2k"
            known_bad_src.parent.mkdir(parents=True)
            known_bad_src.write_bytes(b"known-bad")

            regression_src = repo_root / "conformance_data" / "p0_12.j2k"
            regression_src.parent.mkdir(parents=True)
            regression_src.write_bytes(b"regression-seed")

            (automation_dir / "known_bad.json").parent.mkdir(parents=True)
            (automation_dir / "known_bad.json").write_text(
                json.dumps(
                    {
                        "fingerprints": {
                            "fp1": {
                                "artifact_path": str(known_bad_src),
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            (automation_dir / "regression_candidates.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "smoke-failed:/runs/one",
                                "seed_path": str(regression_src),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.sync_corpus_from_registries(automation_dir, repo_root=repo_root)

            self.assertIn("known_bad", result["updated"])
            self.assertIn("regression", result["updated"])
            self.assertTrue((known_bad_dir / "crash-seed.j2k").exists())
            self.assertTrue((regression_dir / "p0_12.j2k").exists())
            self.assertEqual((known_bad_dir / "crash-seed.j2k").read_bytes(), b"known-bad")
            self.assertEqual((regression_dir / "p0_12.j2k").read_bytes(), b"regression-seed")

    def test_sync_corpus_from_registries_repairs_seed_path_from_smoke_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            automation_dir = root / "automation"
            regression_dir = repo_root / "fuzz" / "corpus" / "regression"
            regression_dir.mkdir(parents=True)

            seed = repo_root / "conformance_data" / "p0_12.j2k"
            seed.parent.mkdir(parents=True)
            seed.write_bytes(b"seed")

            run_dir = repo_root / "fuzz-artifacts" / "runs" / "example"
            run_dir.mkdir(parents=True)
            (run_dir / "smoke.log").write_text(
                'run-smoke.sh: line 13: 15772 Aborted "${harness}" --expect-ok "${repo_root}/conformance_data/p0_12.j2k"\n',
                encoding="utf-8",
            )
            report_path = run_dir / "FUZZING_REPORT.md"
            report_path.write_text("dummy", encoding="utf-8")

            (automation_dir / "regression_candidates.json").parent.mkdir(parents=True)
            (automation_dir / "regression_candidates.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "smoke-failed:/runs/example",
                                "report_path": str(report_path),
                                "seed_path": "${repo_root}/conformance_data/p0_12.j2k",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.sync_corpus_from_registries(automation_dir, repo_root=repo_root)

            self.assertIn("regression", result["updated"])
            reg = json.loads((automation_dir / "regression_candidates.json").read_text(encoding="utf-8"))
            self.assertEqual(reg["entries"][0]["seed_path"], str(seed))
            self.assertEqual(reg["entries"][0]["bucket_path"], str(regression_dir / "p0_12.j2k"))

    def test_sync_corpus_from_registries_curates_coverage_corpus_from_profile_examples(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            automation_dir = root / "automation"
            coverage_dir = repo_root / "fuzz" / "corpus" / "coverage"
            quarantine_dir = repo_root / "fuzz" / "corpus" / "coverage-quarantine"
            source_dir = repo_root / "fuzz" / "corpus-afl" / "deep-decode-v3"
            coverage_dir.mkdir(parents=True)
            source_dir.mkdir(parents=True)
            (automation_dir / "known_bad.json").parent.mkdir(parents=True)
            (automation_dir / "known_bad.json").write_text(json.dumps({"fingerprints": {}}), encoding="utf-8")
            (automation_dir / "regression_candidates.json").write_text(json.dumps({"entries": []}), encoding="utf-8")

            (coverage_dir / "opaque-seed").write_bytes(b"opaque")
            (source_dir / "good-a.j2k").write_bytes(b"good-a")
            (source_dir / "good-tail.j2k").write_bytes(b"good-tail")

            profile_path = repo_root / "fuzz-records" / "profiles" / "openhtj2k-target-profile-v1.yaml"
            profile_path.parent.mkdir(parents=True)
            profile_path.write_text(
                "\n".join(
                    [
                        "schema_version: target-profile/v1",
                        "meta:",
                        "  name: openhtj2k-target-profile-v1",
                        "target:",
                        "  current_campaign:",
                        "    primary_mode: deep-decode-v3",
                        "seeds:",
                        "  root_dirs:",
                        "    deep_decode_v3: fuzz/corpus-afl/deep-decode-v3",
                        "  classes:",
                        "    stable-valid:",
                        "      examples:",
                        "        - good-a.j2k",
                        "      preferred_modes:",
                        "        - deep-decode-v3",
                        "    near-valid-tailcut:",
                        "      examples:",
                        "        - good-tail.j2k",
                        "      preferred_modes:",
                        "        - deep-decode-v3",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = hermes_watch.sync_corpus_from_registries(automation_dir, repo_root=repo_root)

            self.assertIn("coverage", result["updated"])
            self.assertIn("coverage_quarantine", result["updated"])
            self.assertTrue((coverage_dir / "good-a.j2k").exists())
            self.assertTrue((coverage_dir / "good-tail.j2k").exists())
            self.assertFalse((coverage_dir / "opaque-seed").exists())
            self.assertTrue((quarantine_dir / "opaque-seed").exists())

    def test_sync_corpus_from_registries_falls_back_to_existing_repo_seed_for_profile_example(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            automation_dir = root / "automation"
            coverage_dir = repo_root / "fuzz" / "corpus" / "coverage"
            regression_dir = repo_root / "fuzz" / "corpus" / "regression"
            coverage_dir.mkdir(parents=True)
            regression_dir.mkdir(parents=True)
            (automation_dir / "known_bad.json").parent.mkdir(parents=True)
            (automation_dir / "known_bad.json").write_text(json.dumps({"fingerprints": {}}), encoding="utf-8")
            (automation_dir / "regression_candidates.json").write_text(json.dumps({"entries": []}), encoding="utf-8")

            latebodyflip = regression_dir / "p0_11.latebodyflip.j2k"
            latebodyflip.write_bytes(b"latebodyflip")

            profile_path = repo_root / "fuzz-records" / "profiles" / "openhtj2k-target-profile-v1.yaml"
            profile_path.parent.mkdir(parents=True)
            profile_path.write_text(
                "\n".join(
                    [
                        "schema_version: target-profile/v1",
                        "meta:",
                        "  name: openhtj2k-target-profile-v1",
                        "target:",
                        "  current_campaign:",
                        "    primary_mode: deep-decode-v3",
                        "seeds:",
                        "  root_dirs:",
                        "    deep_decode_v3: fuzz/corpus-afl/deep-decode-v3",
                        "  classes:",
                        "    late-bodyflip:",
                        "      examples:",
                        "        - p0_11.latebodyflip.j2k",
                        "      preferred_modes:",
                        "        - deep-decode-v3",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = hermes_watch.sync_corpus_from_registries(automation_dir, repo_root=repo_root)

            self.assertIn("coverage", result["updated"])
            self.assertTrue((coverage_dir / "p0_11.latebodyflip.j2k").exists())
            self.assertEqual((coverage_dir / "p0_11.latebodyflip.j2k").read_bytes(), b"latebodyflip")


class HermesWatchTargetProfileTests(unittest.TestCase):
    def test_resolve_target_profile_path_prefers_explicit_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            explicit = root / "custom-profile.yaml"
            explicit.write_text("schema_version: target-profile/v1\n", encoding="utf-8")

            resolved = hermes_watch.resolve_target_profile_path(root, explicit)

            self.assertEqual(resolved, explicit)

    def test_resolve_target_profile_path_uses_default_profile_location(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            default_profile = root / "fuzz-records" / "profiles" / "openhtj2k-target-profile-v1.yaml"
            default_profile.parent.mkdir(parents=True)
            default_profile.write_text("schema_version: target-profile/v1\n", encoding="utf-8")

            resolved = hermes_watch.resolve_target_profile_path(root, None)

            self.assertEqual(resolved, default_profile)

    def test_load_target_profile_reads_yaml_and_extracts_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            profile_path = root / "fuzz-records" / "profiles" / "openhtj2k-target-profile-v1.yaml"
            profile_path.parent.mkdir(parents=True)
            profile_path.write_text(
                "\n".join(
                    [
                        "schema_version: target-profile/v1",
                        "meta:",
                        "  name: openhtj2k-target-profile-v1",
                        "target:",
                        "  project: openhtj2k",
                        "  current_campaign:",
                        "    primary_mode: deep-decode-v3",
                        "stages:",
                        "  - id: parse-main-header",
                        "  - id: ht-block-decode",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            profile = hermes_watch.load_target_profile(profile_path)
            summary = hermes_watch.build_target_profile_summary(profile, profile_path)

            self.assertEqual(profile["meta"]["name"], "openhtj2k-target-profile-v1")
            self.assertEqual(summary["name"], "openhtj2k-target-profile-v1")
            self.assertEqual(summary["primary_mode"], "deep-decode-v3")
            self.assertEqual(summary["stage_count"], 2)
            self.assertEqual(summary["path"], str(profile_path))
            self.assertEqual(summary["load_status"], "loaded")
            self.assertIsNone(summary["load_error"])
            self.assertEqual(summary["validation_status"], "valid")
            self.assertIsNone(summary["validation_severity"])

    def test_load_target_profile_marks_missing_schema_version_as_warning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            profile_path = root / "warning-profile.yaml"
            profile_path.write_text(
                "\n".join(
                    [
                        "meta:",
                        "  name: warning-profile",
                        "target:",
                        "  current_campaign:",
                        "    primary_mode: deep-decode-v3",
                        "stages:",
                        "  - id: parse-main-header",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            profile = hermes_watch.load_target_profile(profile_path)
            summary = hermes_watch.build_target_profile_summary(profile, profile_path)

            self.assertEqual(summary["load_status"], "loaded")
            self.assertEqual(summary["validation_status"], "warning")
            self.assertEqual(summary["validation_severity"], "warning")
            self.assertIn("missing-schema-version", summary["validation_codes"])

    def test_load_target_profile_marks_invalid_schema_version_as_fatal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            profile_path = root / "fatal-schema-profile.yaml"
            profile_path.write_text(
                "\n".join(
                    [
                        "schema_version: target-profile/v0",
                        "meta:",
                        "  name: fatal-schema-profile",
                        "target:",
                        "  current_campaign:",
                        "    primary_mode: deep-decode-v3",
                        "stages:",
                        "  - id: parse-main-header",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            profile = hermes_watch.load_target_profile(profile_path)
            summary = hermes_watch.build_target_profile_summary(profile, profile_path)

            self.assertEqual(summary["validation_status"], "fatal")
            self.assertEqual(summary["validation_severity"], "fatal")
            self.assertIn("unsupported-schema-version", summary["validation_codes"])

    def test_load_target_profile_marks_missing_primary_mode_as_fatal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            profile_path = root / "fatal-primary-mode-profile.yaml"
            profile_path.write_text(
                "\n".join(
                    [
                        "schema_version: target-profile/v1",
                        "meta:",
                        "  name: fatal-primary-mode-profile",
                        "target:",
                        "  current_campaign: {}",
                        "stages:",
                        "  - id: parse-main-header",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            profile = hermes_watch.load_target_profile(profile_path)
            summary = hermes_watch.build_target_profile_summary(profile, profile_path)

            self.assertEqual(summary["validation_status"], "fatal")
            self.assertEqual(summary["validation_severity"], "fatal")
            self.assertIn("missing-primary-mode", summary["validation_codes"])

    def test_load_target_profile_marks_unknown_hotspot_stage_reference_as_fatal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            profile_path = root / "bad-hotspot-stage.yaml"
            profile_path.write_text(
                "\n".join(
                    [
                        "schema_version: target-profile/v1",
                        "meta:",
                        "  name: bad-hotspot-stage",
                        "target:",
                        "  current_campaign:",
                        "    primary_mode: deep-decode-v3",
                        "stages:",
                        "  - id: parse-main-header",
                        "    depth_rank: 1",
                        "    stage_class: shallow",
                        "hotspots:",
                        "  functions:",
                        "    - name: helper_fn",
                        "      stage: unknown-stage",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            profile = hermes_watch.load_target_profile(profile_path)
            summary = hermes_watch.build_target_profile_summary(profile, profile_path)

            self.assertEqual(summary["validation_status"], "fatal")
            self.assertIn("unknown-hotspot-stage-ref", summary["validation_codes"])

    def test_load_target_profile_marks_unknown_trigger_action_as_fatal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            profile_path = root / "bad-trigger-action.yaml"
            profile_path.write_text(
                "\n".join(
                    [
                        "schema_version: target-profile/v1",
                        "meta:",
                        "  name: bad-trigger-action",
                        "target:",
                        "  current_campaign:",
                        "    primary_mode: deep-decode-v3",
                        "stages:",
                        "  - id: parse-main-header",
                        "    depth_rank: 1",
                        "    stage_class: shallow",
                        "triggers:",
                        "  shallow_crash_dominance:",
                        "    enabled: true",
                        "    condition:",
                        "      dominant_stage: parse-main-header",
                        "      min_ratio: 0.7",
                        "      min_crash_families: 2",
                        "    action: missing_action",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            profile = hermes_watch.load_target_profile(profile_path)
            summary = hermes_watch.build_target_profile_summary(profile, profile_path)

            self.assertEqual(summary["validation_status"], "fatal")
            self.assertIn("unknown-trigger-action", summary["validation_codes"])

    def test_load_target_profile_marks_unknown_stage_counter_name_as_warning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            profile_path = root / "telemetry-warning.yaml"
            profile_path.write_text(
                "\n".join(
                    [
                        "schema_version: target-profile/v1",
                        "meta:",
                        "  name: telemetry-warning",
                        "target:",
                        "  current_campaign:",
                        "    primary_mode: deep-decode-v3",
                        "stages:",
                        "  - id: parse-main-header",
                        "    depth_rank: 1",
                        "    stage_class: shallow",
                        "telemetry:",
                        "  stage_counters:",
                        "    enabled: true",
                        "    names:",
                        "      - parse-main-header",
                        "      - ghost-stage",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            profile = hermes_watch.load_target_profile(profile_path)
            summary = hermes_watch.build_target_profile_summary(profile, profile_path)

            self.assertEqual(summary["validation_status"], "warning")
            self.assertIn("unknown-stage-counter-name", summary["validation_codes"])

    def test_load_target_profile_marks_duplicate_stage_depth_rank_as_fatal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            profile_path = root / "duplicate-stage-depth.yaml"
            profile_path.write_text(
                "\n".join(
                    [
                        "schema_version: target-profile/v1",
                        "meta:",
                        "  name: duplicate-stage-depth",
                        "target:",
                        "  current_campaign:",
                        "    primary_mode: deep-decode-v3",
                        "stages:",
                        "  - id: parse-main-header",
                        "    depth_rank: 1",
                        "    stage_class: shallow",
                        "  - id: tile-part-load",
                        "    depth_rank: 1",
                        "    stage_class: medium",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            profile = hermes_watch.load_target_profile(profile_path)
            summary = hermes_watch.build_target_profile_summary(profile, profile_path)

            self.assertEqual(summary["validation_status"], "fatal")
            self.assertIn("duplicate-stage-depth-rank", summary["validation_codes"])

    def test_load_target_profile_marks_unknown_telemetry_stage_file_map_ref_as_fatal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            profile_path = root / "telemetry-fatal.yaml"
            profile_path.write_text(
                "\n".join(
                    [
                        "schema_version: target-profile/v1",
                        "meta:",
                        "  name: telemetry-fatal",
                        "target:",
                        "  current_campaign:",
                        "    primary_mode: deep-decode-v3",
                        "stages:",
                        "  - id: parse-main-header",
                        "    depth_rank: 1",
                        "    stage_class: shallow",
                        "telemetry:",
                        "  stack_tagging:",
                        "    enabled: true",
                        "    file_to_stage_map: true",
                        "    stage_file_map:",
                        "      ghost-stage:",
                        "        - source/core/ghost.cpp",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            profile = hermes_watch.load_target_profile(profile_path)
            summary = hermes_watch.build_target_profile_summary(profile, profile_path)

            self.assertEqual(summary["validation_status"], "fatal")
            self.assertIn("unknown-telemetry-stage-file-map-ref", summary["validation_codes"])

    def test_load_target_profile_marks_invalid_coverage_plateau_condition_as_fatal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            profile_path = root / "bad-coverage-plateau.yaml"
            profile_path.write_text(
                "\n".join(
                    [
                        "schema_version: target-profile/v1",
                        "meta:",
                        "  name: bad-coverage-plateau",
                        "target:",
                        "  current_campaign:",
                        "    primary_mode: deep-decode-v3",
                        "stages:",
                        "  - id: parse-main-header",
                        "    depth_rank: 1",
                        "    stage_class: shallow",
                        "triggers:",
                        "  coverage_plateau:",
                        "    enabled: true",
                        "    condition:",
                        "      plateau_minutes: nope",
                        "      min_execs_per_sec: 50",
                        "      max_new_high_value_crashes: 0",
                        "    action: propose_harness_revision",
                        "actions:",
                        "  propose_harness_revision:",
                        "    type: recommendation",
                        "    requires_human_review: false",
                        "    outputs:",
                        "      - hotspot_summary",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            profile = hermes_watch.load_target_profile(profile_path)
            summary = hermes_watch.build_target_profile_summary(profile, profile_path)

            self.assertEqual(summary["validation_status"], "fatal")
            self.assertIn("invalid-trigger-condition:coverage_plateau", summary["validation_codes"])

    def test_load_target_profile_marks_invalid_deep_signal_emergence_condition_as_fatal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            profile_path = root / "bad-deep-signal.yaml"
            profile_path.write_text(
                "\n".join(
                    [
                        "schema_version: target-profile/v1",
                        "meta:",
                        "  name: bad-deep-signal",
                        "target:",
                        "  current_campaign:",
                        "    primary_mode: deep-decode-v3",
                        "stages:",
                        "  - id: parse-main-header",
                        "    depth_rank: 1",
                        "    stage_class: shallow",
                        "triggers:",
                        "  deep_signal_emergence:",
                        "    enabled: true",
                        "    condition:",
                        "      stage_any_of: ghost-stage",
                        "      min_new_reproducible_families: 1",
                        "    action: continue_and_prioritize_triage",
                        "actions:",
                        "  continue_and_prioritize_triage:",
                        "    type: continue_run",
                        "    requires_human_review: false",
                        "    outputs:",
                        "      - triage_priority_update",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            profile = hermes_watch.load_target_profile(profile_path)
            summary = hermes_watch.build_target_profile_summary(profile, profile_path)

            self.assertEqual(summary["validation_status"], "fatal")
            self.assertIn("invalid-trigger-condition:deep_signal_emergence", summary["validation_codes"])

    def test_load_target_profile_marks_invalid_action_contract_as_fatal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            profile_path = root / "bad-action-contract.yaml"
            profile_path.write_text(
                "\n".join(
                    [
                        "schema_version: target-profile/v1",
                        "meta:",
                        "  name: bad-action-contract",
                        "target:",
                        "  current_campaign:",
                        "    primary_mode: deep-decode-v3",
                        "stages:",
                        "  - id: parse-main-header",
                        "    depth_rank: 1",
                        "    stage_class: shallow",
                        "actions:",
                        "  propose_harness_revision:",
                        "    type: mystery",
                        "    requires_human_review: nope",
                        "    outputs: broken",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            profile = hermes_watch.load_target_profile(profile_path)
            summary = hermes_watch.build_target_profile_summary(profile, profile_path)

            self.assertEqual(summary["validation_status"], "fatal")
            self.assertIn("invalid-action-type", summary["validation_codes"])
            self.assertIn("invalid-action-human-review-flag", summary["validation_codes"])
            self.assertIn("invalid-action-outputs", summary["validation_codes"])

    def test_load_target_profile_returns_degraded_mapping_for_malformed_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            profile_path = root / "broken-profile.yaml"
            profile_path.write_text("meta: [unterminated\n", encoding="utf-8")

            profile = hermes_watch.load_target_profile(profile_path)
            summary = hermes_watch.build_target_profile_summary(profile, profile_path)

            self.assertEqual(profile["__load_error__"], "yaml-parse-error")
            self.assertEqual(summary["load_status"], "degraded")
            self.assertEqual(summary["load_error"], "yaml-parse-error")
            self.assertEqual(summary["path"], str(profile_path))

    def test_load_target_profile_repairs_wrong_top_level_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            profile_path = root / "wrong-top-level.yaml"
            profile_path.write_text("- just\n- a\n- list\n", encoding="utf-8")

            profile = hermes_watch.load_target_profile(profile_path)
            summary = hermes_watch.build_target_profile_summary(profile, profile_path)

            self.assertEqual(profile["__load_error__"], "invalid-top-level-type")
            self.assertEqual(summary["load_status"], "degraded")
            self.assertEqual(summary["load_error"], "invalid-top-level-type")

    def test_load_target_profile_repairs_invalid_section_shapes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            profile_path = root / "wrong-shape.yaml"
            profile_path.write_text(
                "\n".join(
                    [
                        "schema_version: target-profile/v1",
                        "meta: nope",
                        "target: []",
                        "stages: broken",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            profile = hermes_watch.load_target_profile(profile_path)
            summary = hermes_watch.build_target_profile_summary(profile, profile_path)

            self.assertEqual(profile["meta"], {})
            self.assertEqual(profile["target"], {"current_campaign": {}})
            self.assertEqual(profile["stages"], [])
            self.assertEqual(profile["__load_error__"], "invalid-profile-shape")
            self.assertEqual(summary["load_status"], "degraded")
            self.assertEqual(summary["stage_count"], 0)

    def test_metrics_snapshot_includes_target_profile_summary(self):
        metrics = hermes_watch.Metrics()
        snapshot = hermes_watch.metrics_snapshot(
            outcome="ok",
            metrics=metrics,
            run_dir=Path("/tmp/run"),
            report_path=Path("/tmp/run/FUZZING_REPORT.md"),
            start=0.0,
            target_profile_summary={
                "name": "openhtj2k-target-profile-v1",
                "path": "/tmp/profile.yaml",
                "primary_mode": "deep-decode-v3",
                "stage_count": 6,
            },
        )

        self.assertEqual(snapshot["target_profile_name"], "openhtj2k-target-profile-v1")
        self.assertEqual(snapshot["target_profile_path"], "/tmp/profile.yaml")
        self.assertEqual(snapshot["target_profile_primary_mode"], "deep-decode-v3")
        self.assertEqual(snapshot["target_profile_stage_count"], 6)

    def test_metrics_snapshot_includes_notification_event(self):
        metrics = hermes_watch.Metrics()
        snapshot = hermes_watch.metrics_snapshot(
            outcome="ok",
            metrics=metrics,
            run_dir=Path("/tmp/run"),
            report_path=Path("/tmp/run/FUZZING_REPORT.md"),
            start=0.0,
            notification_event={
                "status": "failed",
                "transport": "webhook",
                "reason": "exception",
                "error_type": "RuntimeError",
                "error": "boom",
                "context": "final-summary",
            },
        )

        self.assertEqual(snapshot["notification_status"], "failed")
        self.assertEqual(snapshot["notification_transport"], "webhook")
        self.assertEqual(snapshot["notification_reason"], "exception")
        self.assertEqual(snapshot["notification_error_type"], "RuntimeError")
        self.assertEqual(snapshot["notification_context"], "final-summary")


class HermesWatchTargetAdapterTests(unittest.TestCase):
    def test_format_progress_message_uses_target_adapter_label(self):
        message = hermes_watch.format_progress_message(
            {
                "duration": "00:10:00",
                "since_progress": "00:01:00",
                "cov": 12,
                "ft": 34,
                "corpus_units": 56,
                "exec_per_second": 78,
                "rss": "90Mb",
                "outcome": "ok",
                "run_dir": "/tmp/run",
            },
            target_label="Custom fuzz",
        )
        self.assertIn("[Custom fuzz] PROGRESS", message)

    def test_get_target_adapter_uses_custom_profile_adapter_spec(self):
        adapter = hermes_watch.get_target_adapter(
            {
                "project": "custom-project",
                "adapter": {
                    "key": "custom-project",
                    "notification_label": "Custom Project fuzz",
                    "report_target": "custom_project_harness",
                    "build_command": ["bash", "scripts/custom-build.sh"],
                    "smoke_binary_relpath": "build/custom-harness",
                    "smoke_command_prefix": ["bash", "scripts/custom-smoke.sh"],
                    "fuzz_command": ["bash", "scripts/custom-fuzz.sh"],
                },
            }
        )

        self.assertEqual(adapter.key, "custom-project")
        self.assertEqual(adapter.notification_label, "Custom Project fuzz")
        self.assertEqual(adapter.report_target, "custom_project_harness")
        self.assertEqual(adapter.build_command_list(), ["bash", "scripts/custom-build.sh"])
        self.assertEqual(adapter.smoke_command(Path("/tmp/repo")), ["bash", "scripts/custom-smoke.sh", "/tmp/repo/build/custom-harness"])
        self.assertEqual(adapter.fuzz_command_list(), ["bash", "scripts/custom-fuzz.sh"])

    def test_get_target_adapter_uses_custom_editable_region_policy_fields(self):
        adapter = hermes_watch.get_target_adapter(
            {
                "project": "custom-project",
                "adapter": {
                    "key": "custom-project",
                    "notification_label": "Custom Project fuzz",
                    "report_target": "custom_project_harness",
                    "build_command": ["bash", "scripts/custom-build.sh"],
                    "smoke_binary_relpath": "build/custom-harness",
                    "smoke_command_prefix": ["bash", "scripts/custom-smoke.sh"],
                    "fuzz_command": ["bash", "scripts/custom-fuzz.sh"],
                    "editable_harness_relpath": "custom-artifacts/generated-harnesses",
                    "fuzz_entrypoint_names": ["CustomFuzzEntry"],
                    "guard_condition": "size <= 8",
                    "guard_return_statement": "return -1;",
                    "target_call_todo": "call custom_decode_entry(data, size) before stage promotion",
                    "resource_lifetime_hint": "input buffer is borrowed-only; do not retain pointers past the fuzz call",
                },
            }
        )

        self.assertEqual(adapter.editable_harness_relpath, "custom-artifacts/generated-harnesses")
        self.assertEqual(adapter.fuzz_entrypoint_names, ("CustomFuzzEntry",))
        self.assertEqual(adapter.guard_condition, "size <= 8")
        self.assertEqual(adapter.guard_return_statement, "return -1;")
        self.assertEqual(adapter.target_call_todo, "call custom_decode_entry(data, size) before stage promotion")
        self.assertEqual(adapter.resource_lifetime_hint, "input buffer is borrowed-only; do not retain pointers past the fuzz call")

    def test_inject_guarded_patch_uses_custom_entrypoint_name(self):
        content = (
            "#include <stddef.h>\n"
            "#include <stdint.h>\n"
            "int CustomFuzzEntry(const uint8_t *data, size_t size) {\n"
            "  return 0;\n"
            "}\n"
        )

        patched = hermes_watch._inject_guarded_patch(
            content,
            scope="guard-only",
            note="add size guard",
            entrypoint_names=("CustomFuzzEntry",),
        )

        self.assertEqual(
            patched,
            "#include <stddef.h>\n"
            "#include <stdint.h>\n"
            "int CustomFuzzEntry(const uint8_t *data, size_t size) {\n"
            "  /* Hermes guarded apply candidate: add size guard */\n"
            "  if (size < 4) {\n"
            "    return 0;\n"
            "  }\n"
            "  return 0;\n"
            "}\n",
        )

    def test_inject_guarded_patch_uses_custom_cpp_entrypoint_name(self):
        content = (
            "#include <cstddef>\n"
            "#include <cstdint>\n"
            "extern \"C\" int CustomFuzzEntry(const std::uint8_t* data, std::size_t size) {\n"
            "  return 0;\n"
            "}\n"
        )

        patched = hermes_watch._inject_guarded_patch(
            content,
            scope="guard-only",
            note="add size guard",
            entrypoint_names=("CustomFuzzEntry",),
        )

        self.assertEqual(
            patched,
            "#include <cstddef>\n"
            "#include <cstdint>\n"
            "extern \"C\" int CustomFuzzEntry(const std::uint8_t* data, std::size_t size) {\n"
            "  // Hermes guarded apply candidate: add size guard\n"
            "  if (size < 4) {\n"
            "    return 0;\n"
            "  }\n"
            "  return 0;\n"
            "}\n",
        )

    def test_inject_guarded_patch_uses_custom_guard_policy(self):
        content = (
            "#include <stddef.h>\n"
            "#include <stdint.h>\n"
            "int CustomFuzzEntry(const uint8_t *data, size_t size) {\n"
            "  return 0;\n"
            "}\n"
        )

        patched = hermes_watch._inject_guarded_patch(
            content,
            scope="guard-only",
            note="add size guard",
            entrypoint_names=("CustomFuzzEntry",),
            guard_condition="size <= 8",
            guard_return_statement="return -1;",
        )

        self.assertEqual(
            patched,
            "#include <stddef.h>\n"
            "#include <stdint.h>\n"
            "int CustomFuzzEntry(const uint8_t *data, size_t size) {\n"
            "  /* Hermes guarded apply candidate: add size guard */\n"
            "  if (size <= 8) {\n"
            "    return -1;\n"
            "  }\n"
            "  return 0;\n"
            "}\n",
        )

    def test_build_target_adapter_regression_smoke_matrix_uses_custom_adapter_commands(self):
        repo_root = Path("/tmp/repo")
        matrix = hermes_watch.build_target_adapter_regression_smoke_matrix(
            repo_root,
            {
                "project": "custom-project",
                "adapter": {
                    "key": "custom-project",
                    "notification_label": "Custom Project fuzz",
                    "report_target": "custom_project_harness",
                    "build_command": ["bash", "scripts/custom-build.sh"],
                    "smoke_binary_relpath": "build/custom-harness",
                    "smoke_command_prefix": ["bash", "scripts/custom-smoke.sh"],
                    "fuzz_command": ["bash", "scripts/custom-fuzz.sh"],
                    "editable_harness_relpath": "custom-artifacts/generated-harnesses",
                    "fuzz_entrypoint_names": ["CustomFuzzEntry"],
                    "guard_condition": "size <= 8",
                    "guard_return_statement": "return -1;",
                    "target_call_todo": "call custom_decode_entry(data, size) before stage promotion",
                    "resource_lifetime_hint": "input buffer is borrowed-only; do not retain pointers past the fuzz call",
                },
            },
        )

        self.assertEqual(matrix["adapter_key"], "custom-project")
        self.assertEqual(matrix["editable_harness_relpath"], "custom-artifacts/generated-harnesses")
        self.assertEqual(matrix["fuzz_entrypoint_names"], ["CustomFuzzEntry"])
        self.assertEqual(matrix["guard_condition"], "size <= 8")
        self.assertEqual(matrix["guard_return_statement"], "return -1;")
        self.assertEqual(matrix["target_call_todo"], "call custom_decode_entry(data, size) before stage promotion")
        self.assertEqual(matrix["resource_lifetime_hint"], "input buffer is borrowed-only; do not retain pointers past the fuzz call")
        row_map = {row["id"]: row for row in matrix["rows"]}
        self.assertEqual(row_map["main-build"]["command"], ["bash", "scripts/custom-build.sh"])
        self.assertEqual(row_map["main-smoke"]["command"], ["bash", "scripts/custom-smoke.sh", "/tmp/repo/build/custom-harness"])
        self.assertEqual(row_map["skeleton-closure-smoke"]["command"], ["bash", "scripts/custom-smoke.sh", "/tmp/repo/build/custom-harness"])

    def test_write_target_adapter_regression_smoke_matrix_writes_policy_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            repo_root.mkdir(parents=True)
            result = hermes_watch.write_target_adapter_regression_smoke_matrix(
                repo_root,
                {
                    "project": "custom-project",
                    "adapter": {
                        "key": "custom-project",
                        "notification_label": "Custom Project fuzz",
                        "report_target": "custom_project_harness",
                        "build_command": ["bash", "scripts/custom-build.sh"],
                        "smoke_binary_relpath": "build/custom-harness",
                        "smoke_command_prefix": ["bash", "scripts/custom-smoke.sh"],
                        "fuzz_command": ["bash", "scripts/custom-fuzz.sh"],
                        "editable_harness_relpath": "custom-artifacts/generated-harnesses",
                        "fuzz_entrypoint_names": ["CustomFuzzEntry"],
                    },
                },
            )

            json_path = Path(result["matrix_json_path"])
            md_path = Path(result["matrix_markdown_path"])
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("Target Adapter Regression Smoke Matrix", md_path.read_text(encoding="utf-8"))
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["adapter_key"], "custom-project")
            self.assertEqual(payload["row_count"], 7)

    def test_write_runtime_target_adapter_regression_smoke_matrix_uses_default_profile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            repo_root.mkdir(parents=True)
            default_profile_path = repo_root / "fuzz-records" / "profiles" / "openhtj2k-target-profile-v1.yaml"
            default_profile_path.parent.mkdir(parents=True)
            default_profile_path.write_text(
                """
schema_version: target-profile/v1
meta:
  name: custom-target-profile
target:
  project: custom-project
  current_campaign:
    primary_mode: custom-mode
    primary_binary: custom_project_harness
  adapter:
    key: custom-project
    notification_label: Custom Project fuzz
    report_target: custom_project_harness
    build_command:
      - bash
      - scripts/custom-build.sh
    smoke_binary_relpath: build/custom-harness
    smoke_command_prefix:
      - bash
      - scripts/custom-smoke.sh
    fuzz_command:
      - bash
      - scripts/custom-fuzz.sh
    editable_harness_relpath: custom-artifacts/generated-harnesses
    fuzz_entrypoint_names:
      - CustomFuzzEntry
stages:
  - id: parse
    description: parse
    stage_class: shallow
    depth_rank: 1
""".strip()
                + "\n",
                encoding="utf-8",
            )

            result = hermes_watch.write_runtime_target_adapter_regression_smoke_matrix(repo_root)

            self.assertEqual(result["adapter_key"], "custom-project")
            self.assertTrue(Path(result["matrix_json_path"]).exists())
            payload = json.loads(Path(result["matrix_json_path"]).read_text(encoding="utf-8"))
            self.assertEqual(payload["report_target"], "custom_project_harness")

    def test_main_smoke_success_and_final_summary_use_profile_selected_adapter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            automation_dir.mkdir(parents=True)
            profile_path = repo_root / "fuzz-records" / "profiles" / "custom-target.yaml"
            profile_path.parent.mkdir(parents=True)

            profile = {
                "schema_version": "target-profile/v1",
                "meta": {"name": "custom-target-profile"},
                "target": {
                    "project": "custom-project",
                    "current_campaign": {
                        "primary_mode": "custom-mode",
                        "primary_binary": "custom_project_harness",
                    },
                    "adapter": {
                        "key": "custom-project",
                        "notification_label": "Custom Project fuzz",
                        "report_target": "custom_project_harness",
                        "build_command": ["bash", "scripts/custom-build.sh"],
                        "smoke_binary_relpath": "build/custom-harness",
                        "smoke_command_prefix": ["bash", "scripts/custom-smoke.sh"],
                        "fuzz_command": ["bash", "scripts/custom-fuzz.sh"],
                    },
                },
                "stages": [{"id": "parse", "description": "parse", "stage_class": "shallow", "depth_rank": 1}],
            }

            original_argv = list(hermes_watch.sys.argv)
            original_run_quiet = hermes_watch.run_quiet
            original_send_discord = hermes_watch.send_discord
            original_apply_policy_action = hermes_watch.apply_policy_action
            original_resolve_target_profile_path = hermes_watch.resolve_target_profile_path
            original_load_target_profile = hermes_watch.load_target_profile
            original_popen = hermes_watch.subprocess.Popen
            discord_messages = []
            commands = []

            class FakeStdout:
                def __iter__(self):
                    return iter([])

            class FakePopen:
                def __init__(self, command, cwd, env, text, stdout, stderr, bufsize, start_new_session):
                    commands.append(command)
                    self.pid = 4242
                    self.stdout = FakeStdout()

                def wait(self):
                    return 0

            def fake_run_quiet(cmd, cwd):
                commands.append(cmd)
                if cmd[:3] == ["git", "rev-parse", "--short"]:
                    return 0, "abc123\n"
                if cmd == ["bash", "scripts/custom-build.sh"]:
                    return 0, "CUSTOM BUILD OK\n"
                if cmd == ["bash", "scripts/custom-smoke.sh", str(repo_root / "build" / "custom-harness")]:
                    return 0, "CUSTOM SMOKE OK\n"
                if cmd == ["git", "branch", "--show-current"]:
                    return 0, "main\n"
                if cmd == ["git", "rev-parse", "HEAD"]:
                    return 0, "deadbeef\n"
                if cmd == ["git", "status", "--short"]:
                    return 0, ""
                raise AssertionError(f"unexpected command: {cmd}")

            hermes_watch.sys.argv = [
                "hermes_watch.py",
                "--repo",
                str(repo_root),
                "--max-total-time",
                "0",
                "--no-progress-seconds",
                "999999",
                "--progress-interval-seconds",
                "0",
            ]
            hermes_watch.run_quiet = fake_run_quiet
            hermes_watch.send_discord = lambda message: discord_messages.append(message) or {"status": "sent", "transport": "webhook"}
            hermes_watch.apply_policy_action = lambda *args, **kwargs: {"updated": False, "regression_trigger": None}
            hermes_watch.resolve_target_profile_path = lambda repo, explicit: profile_path
            hermes_watch.load_target_profile = lambda path: profile
            hermes_watch.subprocess.Popen = FakePopen
            try:
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv
                hermes_watch.run_quiet = original_run_quiet
                hermes_watch.send_discord = original_send_discord
                hermes_watch.apply_policy_action = original_apply_policy_action
                hermes_watch.resolve_target_profile_path = original_resolve_target_profile_path
                hermes_watch.load_target_profile = original_load_target_profile
                hermes_watch.subprocess.Popen = original_popen

            self.assertEqual(exit_code, 0)
            self.assertIn(["bash", "scripts/custom-build.sh"], commands)
            self.assertIn(["bash", "scripts/custom-smoke.sh", str(repo_root / "build" / "custom-harness")], commands)
            self.assertIn(["bash", "scripts/custom-fuzz.sh"], commands)
            self.assertTrue(any("[Custom Project fuzz] OK" in message for message in discord_messages))
            report_text = next((repo_root / "fuzz-artifacts" / "runs").glob("*/FUZZING_REPORT.md")).read_text(encoding="utf-8")
            self.assertIn("target: custom_project_harness", report_text)

    def test_main_build_failure_uses_target_adapter_commands_and_report_target(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            automation_dir.mkdir(parents=True)

            original_argv = list(hermes_watch.sys.argv)
            original_run_quiet = hermes_watch.run_quiet
            original_send_discord = hermes_watch.send_discord
            original_apply_policy_action = hermes_watch.apply_policy_action
            original_resolve_target_profile_path = hermes_watch.resolve_target_profile_path
            original_load_target_profile = hermes_watch.load_target_profile
            original_build_target_profile_summary = hermes_watch.build_target_profile_summary
            original_get_target_adapter = hermes_watch.get_target_adapter

            custom_adapter = hermes_watch.TargetAdapter(
                key="custom",
                notification_label="Custom fuzz",
                report_target="custom_target_bin",
                build_command=("bash", "scripts/custom-build.sh"),
                smoke_binary_relpath="custom-build",
                smoke_command_prefix=("bash", "scripts/custom-smoke.sh"),
                fuzz_command=("bash", "scripts/custom-fuzz.sh"),
            )

            def fake_run_quiet(cmd, cwd):
                if cmd[:3] == ["git", "rev-parse", "--short"]:
                    return 0, "abc123\n"
                if cmd == ["bash", "scripts/custom-build.sh"]:
                    return 7, "CUSTOM BUILD BROKEN\n"
                if cmd == ["git", "branch", "--show-current"]:
                    return 0, "main\n"
                if cmd == ["git", "rev-parse", "HEAD"]:
                    return 0, "deadbeef\n"
                if cmd == ["git", "status", "--short"]:
                    return 0, ""
                raise AssertionError(f"unexpected command: {cmd}")

            hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--skip-smoke"]
            hermes_watch.run_quiet = fake_run_quiet
            hermes_watch.send_discord = lambda message: {"status": "sent", "transport": "webhook"}
            hermes_watch.apply_policy_action = lambda *args, **kwargs: {"updated": False, "regression_trigger": None}
            hermes_watch.resolve_target_profile_path = lambda repo, explicit: None
            hermes_watch.load_target_profile = lambda path: None
            hermes_watch.build_target_profile_summary = lambda profile, path: {"project": "custom"}
            hermes_watch.get_target_adapter = lambda summary=None: custom_adapter
            try:
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv
                hermes_watch.run_quiet = original_run_quiet
                hermes_watch.send_discord = original_send_discord
                hermes_watch.apply_policy_action = original_apply_policy_action
                hermes_watch.resolve_target_profile_path = original_resolve_target_profile_path
                hermes_watch.load_target_profile = original_load_target_profile
                hermes_watch.build_target_profile_summary = original_build_target_profile_summary
                hermes_watch.get_target_adapter = original_get_target_adapter

            self.assertEqual(exit_code, 7)
            report_text = next((repo_root / "fuzz-artifacts" / "runs").glob("*/FUZZING_REPORT.md")).read_text(encoding="utf-8")
            self.assertIn("target: custom_target_bin", report_text)


    def test_main_build_failure_writes_llm_evidence_packet_automatically(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            automation_dir.mkdir(parents=True)

            original_argv = list(hermes_watch.sys.argv)
            original_run_quiet = hermes_watch.run_quiet
            original_send_discord = hermes_watch.send_discord
            original_apply_policy_action = hermes_watch.apply_policy_action
            original_resolve_target_profile_path = hermes_watch.resolve_target_profile_path
            original_load_target_profile = hermes_watch.load_target_profile
            original_build_target_profile_summary = hermes_watch.build_target_profile_summary
            original_get_target_adapter = hermes_watch.get_target_adapter

            custom_adapter = hermes_watch.TargetAdapter(
                key="custom",
                notification_label="Custom fuzz",
                report_target="custom_target_bin",
                build_command=("bash", "scripts/custom-build.sh"),
                smoke_binary_relpath="custom-build",
                smoke_command_prefix=("bash", "scripts/custom-smoke.sh"),
                fuzz_command=("bash", "scripts/custom-fuzz.sh"),
            )

            def fake_run_quiet(cmd, cwd):
                if cmd[:3] == ["git", "rev-parse", "--short"]:
                    return 0, "abc123\n"
                if cmd == ["bash", "scripts/custom-build.sh"]:
                    return 7, "CUSTOM BUILD BROKEN\n"
                if cmd == ["git", "branch", "--show-current"]:
                    return 0, "main\n"
                if cmd == ["git", "rev-parse", "HEAD"]:
                    return 0, "deadbeef\n"
                if cmd == ["git", "status", "--short"]:
                    return 0, ""
                raise AssertionError(f"unexpected command: {cmd}")

            hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--skip-smoke"]
            hermes_watch.run_quiet = fake_run_quiet
            hermes_watch.send_discord = lambda message: {"status": "sent", "transport": "webhook"}
            hermes_watch.apply_policy_action = lambda *args, **kwargs: {"updated": False, "regression_trigger": None}
            hermes_watch.resolve_target_profile_path = lambda repo, explicit: None
            hermes_watch.load_target_profile = lambda path: None
            hermes_watch.build_target_profile_summary = lambda profile, path: {"project": "custom"}
            hermes_watch.get_target_adapter = lambda summary=None: custom_adapter
            try:
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv
                hermes_watch.run_quiet = original_run_quiet
                hermes_watch.send_discord = original_send_discord
                hermes_watch.apply_policy_action = original_apply_policy_action
                hermes_watch.resolve_target_profile_path = original_resolve_target_profile_path
                hermes_watch.load_target_profile = original_load_target_profile
                hermes_watch.build_target_profile_summary = original_build_target_profile_summary
                hermes_watch.get_target_adapter = original_get_target_adapter

            self.assertEqual(exit_code, 7)
            evidence_dir = repo_root / "fuzz-records" / "llm-evidence"
            self.assertTrue(any(evidence_dir.glob("*-llm-evidence.json")))
            packet_path = next(evidence_dir.glob("*-llm-evidence.json"))
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            self.assertEqual(packet["current_status"]["outcome"], "build-failed")
            self.assertEqual(packet["current_status"]["report"], str(next((repo_root / "fuzz-artifacts" / "runs").glob("*/FUZZING_REPORT.md"))))


class HermesWatchReconnaissanceDraftTests(unittest.TestCase):
    def test_build_target_reconnaissance_collects_build_system_and_stage_candidates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "source").mkdir(parents=True)
            (repo_root / "CMakeLists.txt").write_text("project(sample_target)\n", encoding="utf-8")
            (repo_root / "source" / "parse_main.cpp").write_text("int parse_main() { return 0; }\n", encoding="utf-8")
            (repo_root / "source" / "decode_tile.cpp").write_text("int decode_tile() { return 0; }\n", encoding="utf-8")
            (repo_root / "source" / "cleanup.cpp").write_text("int cleanup() { return 0; }\n", encoding="utf-8")

            recon = hermes_watch.build_target_reconnaissance(repo_root)

            self.assertEqual(recon["project_name"], "sample-target")
            self.assertEqual(recon["build_system"], "cmake")
            self.assertGreaterEqual(recon["source_file_count"], 3)
            self.assertIn("parse-main", [stage["id"] for stage in recon["stage_candidates"]])
            self.assertIn("decode", [stage["id"] for stage in recon["stage_candidates"]])

    def test_write_target_profile_auto_draft_writes_yaml_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parser.c").write_text("int parser() { return 0; }\n", encoding="utf-8")
            (repo_root / "src" / "decoder.c").write_text("int decoder() { return 0; }\n", encoding="utf-8")

            result = hermes_watch.write_target_profile_auto_draft(repo_root)

            draft_path = Path(result["draft_profile_path"])
            manifest_path = Path(result["recon_manifest_path"])
            self.assertTrue(draft_path.exists())
            self.assertTrue(manifest_path.exists())
            draft_text = draft_path.read_text(encoding="utf-8")
            self.assertIn("schema_version: target-profile/v1", draft_text)
            self.assertIn("project: sample-target", draft_text)
            self.assertIn("stages:", draft_text)

    def test_main_draft_target_profile_emits_artifact_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "meson.build").write_text("project('sample-target', 'c')\n", encoding="utf-8")
            (repo_root / "src" / "parse.c").write_text("int parse() { return 0; }\n", encoding="utf-8")

            original_argv = list(hermes_watch.sys.argv)
            try:
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--draft-target-profile"]
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv

            self.assertEqual(exit_code, 0)
            draft_dir = repo_root / "fuzz-records" / "profiles" / "auto-drafts"
            self.assertTrue(any(draft_dir.glob("*-target-profile-draft.yaml")))


class HermesWatchHarnessDraftTests(unittest.TestCase):
    def test_build_harness_candidate_draft_generates_candidates_from_recon(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "CMakeLists.txt").write_text("project(sample_target)\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.cpp").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "src" / "decode_frame.cpp").write_text("int decode_frame() { return 0; }\n", encoding="utf-8")

            hermes_watch.write_target_profile_auto_draft(repo_root)
            result = hermes_watch.build_harness_candidate_draft(repo_root)

            self.assertGreaterEqual(result["candidate_count"], 1)
            self.assertTrue(any("entrypoint_path" in candidate for candidate in result["candidates"]))
            self.assertTrue(any(candidate.get("recommended_mode") for candidate in result["candidates"]))

    def test_build_harness_candidate_draft_assigns_viability_signals(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            (repo_root / "CMakeLists.txt").write_text("project(sample_target)\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.cpp").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")

            result = hermes_watch.build_harness_candidate_draft(repo_root)

            candidate = result["candidates"][0]
            self.assertEqual(candidate["callable_signal"], "likely-callable")
            self.assertEqual(candidate["build_viability"], "high")
            self.assertEqual(candidate["smoke_viability"], "high")
            self.assertGreater(candidate["viability_score"], 0)

    def test_write_harness_candidate_draft_emits_manifest_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")

            hermes_watch.write_target_profile_auto_draft(repo_root)
            result = hermes_watch.write_harness_candidate_draft(repo_root)

            manifest_path = Path(result["harness_manifest_path"])
            plan_path = Path(result["harness_plan_path"])
            self.assertTrue(manifest_path.exists())
            self.assertTrue(plan_path.exists())
            self.assertIn("Harness Candidate Draft", plan_path.read_text(encoding="utf-8"))

    def test_main_draft_harness_plan_emits_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "meson.build").write_text("project('sample-target', 'c')\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")

            original_argv = list(hermes_watch.sys.argv)
            try:
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--draft-harness-plan"]
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv

            self.assertEqual(exit_code, 0)
            draft_dir = repo_root / "fuzz-records" / "harness-drafts"
            self.assertTrue(any(draft_dir.glob("*-harness-draft.md")))


class HermesWatchHarnessEvaluationDraftTests(unittest.TestCase):
    def test_build_harness_evaluation_draft_selects_top_candidates_with_execution_plan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "CMakeLists.txt").write_text("project(sample_target)\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.cpp").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "src" / "decode_frame.cpp").write_text("int decode_frame() { return 0; }\n", encoding="utf-8")
            (repo_root / "src" / "cleanup.cpp").write_text("int cleanup() { return 0; }\n", encoding="utf-8")

            result = hermes_watch.build_harness_evaluation_draft(repo_root)

            self.assertGreaterEqual(result["evaluation_count"], 1)
            self.assertLessEqual(result["evaluation_count"], 2)
            top_candidate = result["evaluations"][0]
            self.assertIn("candidate_id", top_candidate)
            self.assertIn("execution_plan", top_candidate)
            self.assertIn("expected_success_signal", top_candidate)
            self.assertTrue(top_candidate["execution_plan"])

    def test_build_harness_evaluation_draft_prefers_more_viable_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            (repo_root / "meson.build").write_text("project('sample-target', 'c')\n", encoding="utf-8")
            (repo_root / "src" / "decode_frame.cpp").write_text("int decode_frame() { return 0; }\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.cpp").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")

            result = hermes_watch.build_harness_evaluation_draft(repo_root)

            top_candidate = result["evaluations"][0]
            self.assertEqual(top_candidate["entrypoint_path"], "src/parse_input.cpp")
            self.assertIn("viability", " ".join(top_candidate["notes"]).lower())

    def test_write_harness_evaluation_draft_emits_manifest_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")

            result = hermes_watch.write_harness_evaluation_draft(repo_root)

            manifest_path = Path(result["evaluation_manifest_path"])
            plan_path = Path(result["evaluation_plan_path"])
            self.assertTrue(manifest_path.exists())
            self.assertTrue(plan_path.exists())
            self.assertIn("Harness Candidate Evaluation Draft", plan_path.read_text(encoding="utf-8"))

    def test_main_draft_harness_evaluation_emits_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "meson.build").write_text("project('sample-target', 'c')\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")

            original_argv = list(hermes_watch.sys.argv)
            try:
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--draft-harness-evaluation"]
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv

            self.assertEqual(exit_code, 0)
            draft_dir = repo_root / "fuzz-records" / "harness-evaluations"
            self.assertTrue(any(draft_dir.glob("*-harness-evaluation.md")))


class HermesWatchHarnessSkeletonDraftTests(unittest.TestCase):
    def test_build_harness_skeleton_draft_generates_stub_and_revision_loop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            (repo_root / "CMakeLists.txt").write_text("project(sample_target)\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.cpp").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")

            result = hermes_watch.build_harness_skeleton_draft(repo_root)

            self.assertEqual(result["draft_kind"], "initial")
            self.assertEqual(result["selected_candidate_id"], "candidate-1")
            self.assertEqual(result["entrypoint_path"], "src/parse_input.cpp")
            self.assertIn("LLVMFuzzerTestOneInput", result["skeleton_code"])
            self.assertIn("src/parse_input.cpp", result["skeleton_code"])
            self.assertTrue(result["revision_loop"])

    def test_build_harness_skeleton_draft_uses_profile_selected_adapter_entrypoint_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            (repo_root / "CMakeLists.txt").write_text("project(sample_target)\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.cpp").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            default_profile_path = repo_root / "fuzz-records" / "profiles" / "openhtj2k-target-profile-v1.yaml"
            default_profile_path.parent.mkdir(parents=True)
            default_profile_path.write_text(
                """
schema_version: target-profile/v1
meta:
  name: custom-target-profile
target:
  project: custom-project
  current_campaign:
    primary_mode: custom-mode
    primary_binary: custom_project_harness
  adapter:
    key: custom-project
    notification_label: Custom Project fuzz
    report_target: custom_project_harness
    build_command:
      - bash
      - scripts/custom-build.sh
    smoke_binary_relpath: build/custom-harness
    smoke_command_prefix:
      - bash
      - scripts/custom-smoke.sh
    fuzz_command:
      - bash
      - scripts/custom-fuzz.sh
    editable_harness_relpath: custom-artifacts/generated-harnesses
    fuzz_entrypoint_names:
      - CustomFuzzEntry
stages:
  - id: parse
    description: parse
    stage_class: shallow
    depth_rank: 1
""".strip()
                + "\n",
                encoding="utf-8",
            )

            result = hermes_watch.build_harness_skeleton_draft(repo_root)

            self.assertEqual(result["draft_kind"], "initial")
            self.assertEqual(result["entrypoint_path"], "src/parse_input.cpp")
            self.assertEqual(result["skeleton_entrypoint_name"], "CustomFuzzEntry")
            self.assertIn("CustomFuzzEntry", result["skeleton_code"])
            self.assertNotIn("LLVMFuzzerTestOneInput", result["skeleton_code"])

    def test_build_harness_skeleton_draft_uses_profile_selected_guard_policy_in_body(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            default_profile_path = repo_root / "fuzz-records" / "profiles" / "openhtj2k-target-profile-v1.yaml"
            default_profile_path.parent.mkdir(parents=True)
            default_profile_path.write_text(
                """
schema_version: target-profile/v1
meta:
  name: custom-target-profile
target:
  project: custom-project
  current_campaign:
    primary_mode: custom-mode
    primary_binary: custom_project_harness
  adapter:
    key: custom-project
    notification_label: Custom Project fuzz
    report_target: custom_project_harness
    build_command:
      - bash
      - scripts/custom-build.sh
    smoke_binary_relpath: build/custom-harness
    smoke_command_prefix:
      - bash
      - scripts/custom-smoke.sh
    fuzz_command:
      - bash
      - scripts/custom-fuzz.sh
    editable_harness_relpath: custom-artifacts/generated-harnesses
    fuzz_entrypoint_names:
      - CustomFuzzEntry
    guard_condition: size <= 8
    guard_return_statement: return -1;
stages:
  - id: parse
    description: parse
    stage_class: shallow
    depth_rank: 1
""".strip()
                + "\n",
                encoding="utf-8",
            )

            result = hermes_watch.build_harness_skeleton_draft(repo_root)

            self.assertIn("if (size <= 8)", result["skeleton_code"])
            self.assertIn("return -1;", result["skeleton_code"])
            self.assertNotIn("if (hermes_prepare_input(data, size) != 0)", result["skeleton_code"])

    def test_build_harness_skeleton_draft_uses_profile_selected_call_todo_and_lifetime_hint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            default_profile_path = repo_root / "fuzz-records" / "profiles" / "openhtj2k-target-profile-v1.yaml"
            default_profile_path.parent.mkdir(parents=True)
            default_profile_path.write_text(
                """
schema_version: target-profile/v1
meta:
  name: custom-target-profile
target:
  project: custom-project
  current_campaign:
    primary_mode: custom-mode
    primary_binary: custom_project_harness
  adapter:
    key: custom-project
    notification_label: Custom Project fuzz
    report_target: custom_project_harness
    build_command:
      - bash
      - scripts/custom-build.sh
    smoke_binary_relpath: build/custom-harness
    smoke_command_prefix:
      - bash
      - scripts/custom-smoke.sh
    fuzz_command:
      - bash
      - scripts/custom-fuzz.sh
    editable_harness_relpath: custom-artifacts/generated-harnesses
    fuzz_entrypoint_names:
      - CustomFuzzEntry
    guard_condition: size <= 8
    guard_return_statement: return -1;
    target_call_todo: call custom_decode_entry(data, size) before stage promotion
    resource_lifetime_hint: input buffer is borrowed-only; do not retain pointers past the fuzz call
stages:
  - id: parse
    description: parse
    stage_class: shallow
    depth_rank: 1
""".strip()
                + "\n",
                encoding="utf-8",
            )

            result = hermes_watch.build_harness_skeleton_draft(repo_root)

            self.assertEqual(result["skeleton_target_call_todo"], "call custom_decode_entry(data, size) before stage promotion")
            self.assertEqual(result["skeleton_resource_lifetime_hint"], "input buffer is borrowed-only; do not retain pointers past the fuzz call")
            self.assertIn("TODO: call custom_decode_entry(data, size) before stage promotion", result["skeleton_code"])
            self.assertIn("Lifetime hint: input buffer is borrowed-only; do not retain pointers past the fuzz call", result["skeleton_code"])

    def test_build_harness_skeleton_draft_marks_revision_from_review_feedback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            registry_dir = repo_root / "fuzz-records" / "harness-candidates"
            feedback_dir = repo_root / "fuzz-records" / "probe-feedback"
            skeleton_dir = repo_root / "fuzz-records" / "harness-skeletons"
            registry_dir.mkdir(parents=True)
            feedback_dir.mkdir(parents=True)
            skeleton_dir.mkdir(parents=True)
            (registry_dir / "ranked-candidates.json").write_text(
                json.dumps(
                    {
                        "project": "sample-target",
                        "candidates": [
                            {
                                "candidate_id": "candidate-1",
                                "entrypoint_path": "src/parse_input.cpp",
                                "recommended_mode": "parse",
                                "target_stage": "parse",
                                "score": 18,
                                "effective_score": 20,
                                "status": "review_required",
                                "rank": 1,
                                "review_debt_count": 1,
                                "smoke_debt_count": 1,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (feedback_dir / "sample-target-probe-feedback.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "action_code": "halt_and_review_harness",
                        "bridge_reason": "smoke-probe-failed",
                        "candidate_id": "candidate-1",
                        "entrypoint_path": "src/parse_input.cpp",
                        "build_probe_status": "passed",
                        "smoke_probe_status": "failed",
                    }
                ),
                encoding="utf-8",
            )
            (skeleton_dir / "sample-target-candidate-1-harness-skeleton.json").write_text(
                json.dumps(
                    {
                        "selected_candidate_id": "candidate-1",
                        "revision_number": 1,
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.build_harness_skeleton_draft(repo_root)

            self.assertEqual(result["draft_kind"], "revision")
            self.assertEqual(result["revision_number"], 2)
            self.assertEqual(result["revision_priority"], "high")
            self.assertEqual(result["next_revision_focus"], "smoke-fix")
            self.assertIn("smoke:failed", result["revision_signals"])
            self.assertTrue(any("smoke" in step.lower() for step in result["revision_loop"]))

    def test_build_harness_skeleton_draft_prioritizes_build_fix_from_failed_probe_feedback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            registry_dir = repo_root / "fuzz-records" / "harness-candidates"
            feedback_dir = repo_root / "fuzz-records" / "probe-feedback"
            registry_dir.mkdir(parents=True)
            feedback_dir.mkdir(parents=True)
            (registry_dir / "ranked-candidates.json").write_text(
                json.dumps(
                    {
                        "project": "sample-target",
                        "candidates": [
                            {
                                "candidate_id": "candidate-1",
                                "entrypoint_path": "src/parse_input.cpp",
                                "recommended_mode": "parse",
                                "target_stage": "parse",
                                "score": 22,
                                "effective_score": 17,
                                "status": "review_required",
                                "rank": 1,
                                "review_debt_count": 2,
                                "build_debt_count": 1,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (feedback_dir / "sample-target-probe-feedback.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "action_code": "halt_and_review_harness",
                        "bridge_reason": "build-probe-failed",
                        "candidate_id": "candidate-1",
                        "entrypoint_path": "src/parse_input.cpp",
                        "build_probe_status": "failed",
                        "smoke_probe_status": "skipped",
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.build_harness_skeleton_draft(repo_root)

            self.assertEqual(result["revision_priority"], "high")
            self.assertEqual(result["next_revision_focus"], "build-fix")
            self.assertIn("build:failed", result["revision_signals"])
            self.assertTrue(any("build" in step.lower() for step in result["revision_loop"]))
            self.assertEqual(result["correction_strategy"], "build-fix")
            self.assertTrue(result["correction_suggestions"])
            self.assertTrue(any("include" in suggestion["rationale"].lower() or "link" in suggestion["rationale"].lower() for suggestion in result["correction_suggestions"]))

    def test_write_harness_skeleton_draft_emits_manifest_markdown_and_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")

            result = hermes_watch.write_harness_skeleton_draft(repo_root)

            manifest_path = Path(result["skeleton_manifest_path"])
            plan_path = Path(result["skeleton_plan_path"])
            source_path = Path(result["skeleton_source_path"])
            self.assertTrue(manifest_path.exists())
            self.assertTrue(plan_path.exists())
            self.assertTrue(source_path.exists())
            self.assertIn("Harness Skeleton Draft", plan_path.read_text(encoding="utf-8"))
            self.assertIn("LLVMFuzzerTestOneInput", source_path.read_text(encoding="utf-8"))
            self.assertIn("Revision Intelligence", plan_path.read_text(encoding="utf-8"))
            self.assertIn("Patch Suggestions", plan_path.read_text(encoding="utf-8"))
            self.assertTrue(Path(result["correction_draft_json_path"]).exists())
            self.assertTrue(Path(result["correction_draft_markdown_path"]).exists())

    def test_write_harness_skeleton_draft_emits_custom_adapter_entrypoint_name_into_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            default_profile_path = repo_root / "fuzz-records" / "profiles" / "openhtj2k-target-profile-v1.yaml"
            default_profile_path.parent.mkdir(parents=True)
            default_profile_path.write_text(
                """
schema_version: target-profile/v1
meta:
  name: custom-target-profile
target:
  project: custom-project
  current_campaign:
    primary_mode: custom-mode
    primary_binary: custom_project_harness
  adapter:
    key: custom-project
    notification_label: Custom Project fuzz
    report_target: custom_project_harness
    build_command:
      - bash
      - scripts/custom-build.sh
    smoke_binary_relpath: build/custom-harness
    smoke_command_prefix:
      - bash
      - scripts/custom-smoke.sh
    fuzz_command:
      - bash
      - scripts/custom-fuzz.sh
    editable_harness_relpath: custom-artifacts/generated-harnesses
    fuzz_entrypoint_names:
      - CustomFuzzEntry
stages:
  - id: parse
    description: parse
    stage_class: shallow
    depth_rank: 1
""".strip()
                + "\n",
                encoding="utf-8",
            )

            result = hermes_watch.write_harness_skeleton_draft(repo_root)

            source_path = Path(result["skeleton_source_path"])
            source_text = source_path.read_text(encoding="utf-8")
            self.assertIn("CustomFuzzEntry", source_text)
            self.assertNotIn("LLVMFuzzerTestOneInput", source_text)

    def test_write_harness_skeleton_draft_emits_custom_guard_policy_into_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            default_profile_path = repo_root / "fuzz-records" / "profiles" / "openhtj2k-target-profile-v1.yaml"
            default_profile_path.parent.mkdir(parents=True)
            default_profile_path.write_text(
                """
schema_version: target-profile/v1
meta:
  name: custom-target-profile
target:
  project: custom-project
  current_campaign:
    primary_mode: custom-mode
    primary_binary: custom_project_harness
  adapter:
    key: custom-project
    notification_label: Custom Project fuzz
    report_target: custom_project_harness
    build_command:
      - bash
      - scripts/custom-build.sh
    smoke_binary_relpath: build/custom-harness
    smoke_command_prefix:
      - bash
      - scripts/custom-smoke.sh
    fuzz_command:
      - bash
      - scripts/custom-fuzz.sh
    editable_harness_relpath: custom-artifacts/generated-harnesses
    fuzz_entrypoint_names:
      - CustomFuzzEntry
    guard_condition: size <= 8
    guard_return_statement: return -1;
stages:
  - id: parse
    description: parse
    stage_class: shallow
    depth_rank: 1
""".strip()
                + "\n",
                encoding="utf-8",
            )

            result = hermes_watch.write_harness_skeleton_draft(repo_root)

            source_path = Path(result["skeleton_source_path"])
            source_text = source_path.read_text(encoding="utf-8")
            self.assertIn("if (size <= 8)", source_text)
            self.assertIn("return -1;", source_text)
            self.assertNotIn("if (hermes_prepare_input(data, size) != 0)", source_text)

    def test_write_harness_skeleton_draft_emits_custom_call_todo_and_lifetime_hint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            default_profile_path = repo_root / "fuzz-records" / "profiles" / "openhtj2k-target-profile-v1.yaml"
            default_profile_path.parent.mkdir(parents=True)
            default_profile_path.write_text(
                """
schema_version: target-profile/v1
meta:
  name: custom-target-profile
target:
  project: custom-project
  current_campaign:
    primary_mode: custom-mode
    primary_binary: custom_project_harness
  adapter:
    key: custom-project
    notification_label: Custom Project fuzz
    report_target: custom_project_harness
    build_command:
      - bash
      - scripts/custom-build.sh
    smoke_binary_relpath: build/custom-harness
    smoke_command_prefix:
      - bash
      - scripts/custom-smoke.sh
    fuzz_command:
      - bash
      - scripts/custom-fuzz.sh
    editable_harness_relpath: custom-artifacts/generated-harnesses
    fuzz_entrypoint_names:
      - CustomFuzzEntry
    guard_condition: size <= 8
    guard_return_statement: return -1;
    target_call_todo: call custom_decode_entry(data, size) before stage promotion
    resource_lifetime_hint: input buffer is borrowed-only; do not retain pointers past the fuzz call
stages:
  - id: parse
    description: parse
    stage_class: shallow
    depth_rank: 1
""".strip()
                + "\n",
                encoding="utf-8",
            )

            result = hermes_watch.write_harness_skeleton_draft(repo_root)

            source_path = Path(result["skeleton_source_path"])
            source_text = source_path.read_text(encoding="utf-8")
            plan_text = Path(result["skeleton_plan_path"]).read_text(encoding="utf-8")
            self.assertIn("TODO: call custom_decode_entry(data, size) before stage promotion", source_text)
            self.assertIn("Lifetime hint: input buffer is borrowed-only; do not retain pointers past the fuzz call", source_text)
            self.assertIn("skeleton_target_call_todo: call custom_decode_entry(data, size) before stage promotion", plan_text)
            self.assertIn("skeleton_resource_lifetime_hint: input buffer is borrowed-only; do not retain pointers past the fuzz call", plan_text)

    def test_write_harness_skeleton_draft_emits_revision_intelligence_into_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            registry_dir = repo_root / "fuzz-records" / "harness-candidates"
            feedback_dir = repo_root / "fuzz-records" / "probe-feedback"
            (repo_root / "src").mkdir(parents=True)
            registry_dir.mkdir(parents=True)
            feedback_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (registry_dir / "ranked-candidates.json").write_text(
                json.dumps(
                    {
                        "project": "sample-target",
                        "candidates": [
                            {
                                "candidate_id": "candidate-1",
                                "entrypoint_path": "src/parse_input.c",
                                "recommended_mode": "parse",
                                "target_stage": "parse",
                                "score": 30,
                                "effective_score": 26,
                                "status": "review_required",
                                "rank": 1,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (feedback_dir / "sample-target-probe-feedback.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "action_code": "halt_and_review_harness",
                        "bridge_reason": "smoke-probe-failed",
                        "candidate_id": "candidate-1",
                        "entrypoint_path": "src/parse_input.c",
                        "build_probe_status": "passed",
                        "smoke_probe_status": "failed",
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.write_harness_skeleton_draft(repo_root)

            manifest = json.loads(Path(result["skeleton_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["next_revision_focus"], "smoke-fix")
            self.assertEqual(manifest["revision_priority"], "high")
            self.assertIn("smoke:failed", manifest["revision_signals"])
            self.assertEqual(manifest["correction_strategy"], "smoke-fix")
            self.assertTrue(manifest["correction_suggestions"])
            self.assertTrue(manifest["correction_draft_json_path"].endswith("-correction-draft.json"))

    def test_run_harness_skeleton_closure_executes_build_then_smoke_and_writes_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            calls: list[list[str]] = []

            def probe(command: list[str], cwd: Path) -> tuple[int, str]:
                calls.append(command)
                return 0, "ok\n"

            result = hermes_watch.run_harness_skeleton_closure(repo_root, probe_runner=probe)

            self.assertEqual(result["build_probe_status"], "passed")
            self.assertEqual(result["smoke_probe_status"], "passed")
            self.assertEqual(calls[0], ["make", "-n"])
            self.assertEqual(calls[1][0], str(repo_root / "scripts" / "run-smoke.sh"))
            self.assertTrue(Path(result["closure_manifest_path"]).exists())
            self.assertTrue(Path(result["closure_plan_path"]).exists())

    def test_run_harness_skeleton_closure_uses_profile_selected_adapter_commands(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            default_profile_path = repo_root / "fuzz-records" / "profiles" / "openhtj2k-target-profile-v1.yaml"
            default_profile_path.parent.mkdir(parents=True)
            default_profile_path.write_text(
                """
schema_version: target-profile/v1
meta:
  name: custom-target-profile
target:
  project: custom-project
  current_campaign:
    primary_mode: custom-mode
    primary_binary: custom_project_harness
  adapter:
    key: custom-project
    notification_label: Custom Project fuzz
    report_target: custom_project_harness
    build_command:
      - bash
      - scripts/custom-build.sh
    smoke_binary_relpath: build/custom-harness
    smoke_command_prefix:
      - bash
      - scripts/custom-smoke.sh
    fuzz_command:
      - bash
      - scripts/custom-fuzz.sh
stages:
  - id: parse
    description: parse
    stage_class: shallow
    depth_rank: 1
""".strip()
                + "\n",
                encoding="utf-8",
            )
            calls: list[list[str]] = []

            def probe(command: list[str], cwd: Path) -> tuple[int, str]:
                calls.append(command)
                return 0, "ok\n"

            result = hermes_watch.run_harness_skeleton_closure(repo_root, probe_runner=probe)

            self.assertEqual(result["build_probe_status"], "passed")
            self.assertEqual(result["smoke_probe_status"], "passed")
            self.assertEqual(calls[0], ["bash", "scripts/custom-build.sh"])
            self.assertEqual(calls[1], ["bash", "scripts/custom-smoke.sh", str(repo_root / "build" / "custom-harness")])

    def test_build_harness_skeleton_draft_prefers_latest_skeleton_closure_for_revision_focus(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            closure_dir = repo_root / "fuzz-records" / "harness-skeleton-probes"
            (repo_root / "src").mkdir(parents=True)
            closure_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (closure_dir / "sample-target-candidate-1-harness-skeleton-probe.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "entrypoint_path": "src/parse_input.c",
                        "build_probe_status": "passed",
                        "smoke_probe_status": "failed",
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.build_harness_skeleton_draft(repo_root)

            self.assertEqual(result["next_revision_focus"], "smoke-fix")
            self.assertIn("smoke:failed", result["revision_signals"])
            self.assertEqual(result["revision_signal_source"], "skeleton-closure")

    def test_main_run_harness_skeleton_closure_emits_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            (repo_root / "meson.build").write_text("project('sample-target', 'c')\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")

            original_argv = list(hermes_watch.sys.argv)
            original_run_probe = hermes_watch.run_probe_command
            try:
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--run-harness-skeleton-closure"]
                hermes_watch.run_probe_command = lambda command, cwd=None: (0, "ok\n")
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv
                hermes_watch.run_probe_command = original_run_probe

            self.assertEqual(exit_code, 0)
            closure_dir = repo_root / "fuzz-records" / "harness-skeleton-probes"
            self.assertTrue(any(closure_dir.glob("*-harness-skeleton-probe.md")))

    def test_write_harness_correction_policy_promotes_smoke_failed_closure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")

            skeleton_result = hermes_watch.write_harness_skeleton_draft(repo_root)
            closure_dir = repo_root / "fuzz-records" / "harness-skeleton-probes"
            closure_dir.mkdir(parents=True, exist_ok=True)
            closure_path = closure_dir / "sample-target-candidate-1-harness-skeleton-probe.json"
            closure_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "entrypoint_path": "src/parse_input.c",
                        "skeleton_source_path": skeleton_result["skeleton_source_path"],
                        "build_probe_status": "passed",
                        "smoke_probe_status": "failed",
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.write_harness_correction_policy(repo_root)

            self.assertEqual(result["decision"], "promote-reviewable-correction")
            self.assertEqual(result["disposition"], "promoted")
            self.assertEqual(result["apply_policy"], "comment-only")
            self.assertTrue(result["selected_suggestion_titles"])
            self.assertTrue(Path(result["policy_manifest_path"]).exists())
            plan_text = Path(result["policy_plan_path"]).read_text(encoding="utf-8")
            self.assertIn("Consumption Decision", plan_text)
            self.assertIn("promote-reviewable-correction", plan_text)

    def test_write_harness_correction_policy_holds_when_closure_already_passes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")

            skeleton_result = hermes_watch.write_harness_skeleton_draft(repo_root)
            closure_dir = repo_root / "fuzz-records" / "harness-skeleton-probes"
            closure_dir.mkdir(parents=True, exist_ok=True)
            (closure_dir / "sample-target-candidate-1-harness-skeleton-probe.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "entrypoint_path": "src/parse_input.c",
                        "skeleton_source_path": skeleton_result["skeleton_source_path"],
                        "build_probe_status": "passed",
                        "smoke_probe_status": "passed",
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.write_harness_correction_policy(repo_root)

            self.assertEqual(result["decision"], "hold-no-change")
            self.assertEqual(result["disposition"], "deferred")
            self.assertEqual(result["apply_policy"], "none")
            self.assertEqual(result["selected_suggestion_titles"], [])
            manifest = json.loads(Path(result["policy_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["selected_suggestion_count"], 0)

    def test_main_decide_harness_correction_policy_emits_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")

            skeleton_result = hermes_watch.write_harness_skeleton_draft(repo_root)
            closure_dir = repo_root / "fuzz-records" / "harness-skeleton-probes"
            closure_dir.mkdir(parents=True, exist_ok=True)
            (closure_dir / "sample-target-candidate-1-harness-skeleton-probe.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "entrypoint_path": "src/parse_input.c",
                        "skeleton_source_path": skeleton_result["skeleton_source_path"],
                        "build_probe_status": "failed",
                        "smoke_probe_status": "skipped",
                    }
                ),
                encoding="utf-8",
            )

            original_argv = list(hermes_watch.sys.argv)
            try:
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--decide-harness-correction-policy"]
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv

            self.assertEqual(exit_code, 0)
            policy_dir = repo_root / "fuzz-records" / "harness-correction-policies"
            self.assertTrue(any(policy_dir.glob("*-harness-correction-policy.md")))

    def test_write_harness_apply_candidate_promoted_policy_emits_delegate_request(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")

            skeleton_result = hermes_watch.write_harness_skeleton_draft(repo_root)
            closure_dir = repo_root / "fuzz-records" / "harness-skeleton-probes"
            closure_dir.mkdir(parents=True, exist_ok=True)
            (closure_dir / "sample-target-candidate-1-harness-skeleton-probe.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "entrypoint_path": "src/parse_input.c",
                        "skeleton_source_path": skeleton_result["skeleton_source_path"],
                        "build_probe_status": "passed",
                        "smoke_probe_status": "failed",
                    }
                ),
                encoding="utf-8",
            )
            hermes_watch.write_harness_correction_policy(repo_root)

            result = hermes_watch.write_harness_apply_candidate(repo_root)

            self.assertEqual(result["decision"], "draft-reviewable-apply-candidate")
            self.assertEqual(result["apply_candidate_scope"], "guard-only")
            self.assertTrue(result["delegate_request_path"])
            self.assertTrue(Path(result["apply_candidate_manifest_path"]).exists())
            request = json.loads(Path(result["delegate_request_path"]).read_text(encoding="utf-8"))
            self.assertIn("guarded harness patch candidate", request["goal"].lower())
            self.assertIn("source_policy_manifest_path", request["context"])
            self.assertIn("llm_evidence_json_path", request["context"])
            self.assertIn("llm_objective", request["context"])
            self.assertIn("failure_reason_codes", request["context"])
            plan_text = Path(result["apply_candidate_plan_path"]).read_text(encoding="utf-8")
            self.assertIn("Guarded Apply Decision", plan_text)

    def test_write_harness_apply_candidate_hold_policy_skips_delegate_request(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")

            skeleton_result = hermes_watch.write_harness_skeleton_draft(repo_root)
            closure_dir = repo_root / "fuzz-records" / "harness-skeleton-probes"
            closure_dir.mkdir(parents=True, exist_ok=True)
            (closure_dir / "sample-target-candidate-1-harness-skeleton-probe.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "entrypoint_path": "src/parse_input.c",
                        "skeleton_source_path": skeleton_result["skeleton_source_path"],
                        "build_probe_status": "passed",
                        "smoke_probe_status": "passed",
                    }
                ),
                encoding="utf-8",
            )
            hermes_watch.write_harness_correction_policy(repo_root)

            result = hermes_watch.write_harness_apply_candidate(repo_root)

            self.assertEqual(result["decision"], "hold-no-apply-candidate")
            self.assertEqual(result["delegate_request_path"], None)
            manifest = json.loads(Path(result["apply_candidate_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["selected_suggestion_count"], 0)

    def test_main_prepare_harness_apply_candidate_emits_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")

            skeleton_result = hermes_watch.write_harness_skeleton_draft(repo_root)
            closure_dir = repo_root / "fuzz-records" / "harness-skeleton-probes"
            closure_dir.mkdir(parents=True, exist_ok=True)
            (closure_dir / "sample-target-candidate-1-harness-skeleton-probe.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "entrypoint_path": "src/parse_input.c",
                        "skeleton_source_path": skeleton_result["skeleton_source_path"],
                        "build_probe_status": "failed",
                        "smoke_probe_status": "skipped",
                    }
                ),
                encoding="utf-8",
            )
            hermes_watch.write_harness_correction_policy(repo_root)

            original_argv = list(hermes_watch.sys.argv)
            try:
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--prepare-harness-apply-candidate"]
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv

            self.assertEqual(exit_code, 0)
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            self.assertTrue(any(apply_dir.glob("*-harness-apply-candidate.md")))

    def test_prepare_harness_apply_candidate_bridge_writes_prompt_and_script(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")

            skeleton_result = hermes_watch.write_harness_skeleton_draft(repo_root)
            closure_dir = repo_root / "fuzz-records" / "harness-skeleton-probes"
            closure_dir.mkdir(parents=True, exist_ok=True)
            (closure_dir / "sample-target-candidate-1-harness-skeleton-probe.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "entrypoint_path": "src/parse_input.c",
                        "skeleton_source_path": skeleton_result["skeleton_source_path"],
                        "build_probe_status": "passed",
                        "smoke_probe_status": "failed",
                    }
                ),
                encoding="utf-8",
            )
            hermes_watch.write_harness_apply_candidate(repo_root)

            result = hermes_watch.prepare_harness_apply_candidate_bridge(repo_root)

            self.assertEqual(result["bridge_status"], "armed")
            self.assertEqual(result["bridge_channel"], "hermes-cli-delegate")
            prompt_path = Path(result["bridge_prompt_path"])
            script_path = Path(result["bridge_script_path"])
            self.assertTrue(prompt_path.exists())
            self.assertTrue(script_path.exists())
            prompt_text = prompt_path.read_text(encoding="utf-8")
            self.assertIn("delegate_task request JSON", prompt_text)
            self.assertIn("llm_evidence_json_path", prompt_text)
            self.assertIn("failure_reasons", prompt_text)

    def test_launch_harness_apply_candidate_bridge_executes_script_and_updates_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            bridge_dir = repo_root / "fuzz-records" / "harness-apply-bridge"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            bridge_dir.mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            artifact_path = apply_dir / "candidate-note.md"
            script_path = bridge_dir / "sample-target-candidate-1-harness-apply-bridge.sh"
            script_path.write_text(
                "#!/usr/bin/env bash\nset -euo pipefail\ncat <<'EOF'\nDelegate status: success\nChild session: session_apply_123\nArtifact path: {}\nSummary: guarded apply candidate emitted\nEOF\n".format(artifact_path),
                encoding="utf-8",
            )
            script_path.chmod(0o755)
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "bridge_status": "armed",
                        "bridge_channel": "hermes-cli-delegate",
                        "bridge_script_path": str(script_path),
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.launch_harness_apply_candidate_bridge(repo_root)

            self.assertEqual(result["bridge_status"], "succeeded")
            self.assertEqual(result["delegate_session_id"], "session_apply_123")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["bridge_status"], "succeeded")
            self.assertEqual(manifest["delegate_status"], "success")
            self.assertEqual(manifest["delegate_artifact_path"], str(artifact_path))

    def test_main_prepare_harness_apply_candidate_bridge_emits_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")

            skeleton_result = hermes_watch.write_harness_skeleton_draft(repo_root)
            closure_dir = repo_root / "fuzz-records" / "harness-skeleton-probes"
            closure_dir.mkdir(parents=True, exist_ok=True)
            (closure_dir / "sample-target-candidate-1-harness-skeleton-probe.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "entrypoint_path": "src/parse_input.c",
                        "skeleton_source_path": skeleton_result["skeleton_source_path"],
                        "build_probe_status": "failed",
                        "smoke_probe_status": "skipped",
                    }
                ),
                encoding="utf-8",
            )
            hermes_watch.write_harness_apply_candidate(repo_root)

            original_argv = list(hermes_watch.sys.argv)
            try:
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--bridge-harness-apply-candidate"]
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv

            self.assertEqual(exit_code, 0)
            bridge_dir = repo_root / "fuzz-records" / "harness-apply-bridge"
            self.assertTrue(any(bridge_dir.glob("*-harness-apply-bridge.sh")))

    def test_verify_harness_apply_candidate_result_marks_verified_when_delegate_artifact_has_expected_sections(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- add early return guard\n\n## Evidence Response\n- llm_objective: deeper-stage-reach\n- failure_reason_codes: stage-reach-blocked, shallow-crash-recurrence\n- response_summary: add a minimal guard before deeper decode logic\n\n## Verification Steps\n- run build\n",
                encoding="utf-8",
            )
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "bridge_status": "succeeded",
                        "delegate_session_id": "session_apply_123",
                        "delegate_artifact_path": str(artifact_path),
                        "delegate_expected_sections": ["## Patch Summary", "## Evidence Response", "## Verification Steps"],
                        "delegate_quality_sections": ["## Patch Summary", "## Evidence Response", "## Verification Steps"],
                        "llm_objective": "deeper-stage-reach",
                        "failure_reason_codes": ["stage-reach-blocked", "shallow-crash-recurrence"],
                        "raw_signal_summary": {"smoke_log_signal_count": 2},
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.verify_harness_apply_candidate_result(
                repo_root,
                probe_runner=lambda command, cwd: (0, "session_apply_123\n"),
            )

            self.assertEqual(result["verification_status"], "verified")
            self.assertTrue(result["delegate_artifact_shape_verified"])
            self.assertTrue(result["delegate_artifact_quality_verified"])
            self.assertEqual(result["llm_objective"], "deeper-stage-reach")
            self.assertIn("stage-reach-blocked", result["failure_reason_codes"])
            self.assertEqual(result["raw_signal_summary"]["smoke_log_signal_count"], 2)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["verification_status"], "verified")
            self.assertEqual(manifest["verification_summary"], "delegate-session-artifact-shape-quality-and-evidence-visible")
            self.assertEqual(manifest["llm_objective"], "deeper-stage-reach")

    def test_verify_harness_apply_candidate_result_marks_unverified_when_evidence_response_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- add early return guard\n\n## Verification Steps\n- run build\n",
                encoding="utf-8",
            )
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "bridge_status": "succeeded",
                        "delegate_session_id": "session_apply_123",
                        "delegate_artifact_path": str(artifact_path),
                        "delegate_expected_sections": ["## Patch Summary", "## Evidence Response", "## Verification Steps"],
                        "delegate_quality_sections": ["## Patch Summary", "## Evidence Response", "## Verification Steps"],
                        "llm_objective": "deeper-stage-reach",
                        "failure_reason_codes": ["stage-reach-blocked", "shallow-crash-recurrence"],
                        "raw_signal_summary": {"smoke_log_signal_count": 2},
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.verify_harness_apply_candidate_result(
                repo_root,
                probe_runner=lambda command, cwd: (0, "session_apply_123\n"),
            )

            self.assertEqual(result["verification_status"], "unverified")
            self.assertFalse(result["delegate_artifact_evidence_response_verified"])
            self.assertEqual(result["delegate_reported_llm_objective"], None)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["verification_status"], "unverified")
            self.assertFalse(manifest["delegate_artifact_evidence_response_verified"])

    def test_verify_harness_apply_candidate_result_marks_verified_when_evidence_response_matches_objective_and_failure_codes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- add early return guard\n\n## Evidence Response\n- llm_objective: deeper-stage-reach\n- failure_reason_codes: stage-reach-blocked, shallow-crash-recurrence\n- response_summary: add a minimal guard before deeper decode logic\n\n## Verification Steps\n- run build\n- run smoke\n",
                encoding="utf-8",
            )
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "bridge_status": "succeeded",
                        "delegate_session_id": "session_apply_123",
                        "delegate_artifact_path": str(artifact_path),
                        "delegate_expected_sections": ["## Patch Summary", "## Evidence Response", "## Verification Steps"],
                        "delegate_quality_sections": ["## Patch Summary", "## Evidence Response", "## Verification Steps"],
                        "llm_objective": "deeper-stage-reach",
                        "failure_reason_codes": ["stage-reach-blocked", "shallow-crash-recurrence"],
                        "raw_signal_summary": {"smoke_log_signal_count": 2},
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.verify_harness_apply_candidate_result(
                repo_root,
                probe_runner=lambda command, cwd: (0, "session_apply_123\n"),
            )

            self.assertEqual(result["verification_status"], "verified")
            self.assertTrue(result["delegate_artifact_evidence_response_verified"])
            self.assertTrue(result["delegate_artifact_patch_alignment_verified"])
            self.assertEqual(result["delegate_reported_llm_objective"], "deeper-stage-reach")
            self.assertEqual(
                result["delegate_reported_failure_reason_codes"],
                ["stage-reach-blocked", "shallow-crash-recurrence"],
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertTrue(manifest["delegate_artifact_evidence_response_verified"])
            self.assertTrue(manifest["delegate_artifact_patch_alignment_verified"])
            self.assertEqual(manifest["delegate_reported_llm_objective"], "deeper-stage-reach")

    def test_verify_harness_apply_candidate_result_marks_unverified_when_patch_summary_conflicts_with_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- rewrite build scripts and enable persistent mode\n\n## Evidence Response\n- llm_objective: deeper-stage-reach\n- failure_reason_codes: stage-reach-blocked, shallow-crash-recurrence\n- response_summary: add a minimal guard before deeper decode logic\n\n## Verification Steps\n- run build\n",
                encoding="utf-8",
            )
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "bridge_status": "succeeded",
                        "delegate_session_id": "session_apply_123",
                        "delegate_artifact_path": str(artifact_path),
                        "delegate_expected_sections": ["## Patch Summary", "## Evidence Response", "## Verification Steps"],
                        "delegate_quality_sections": ["## Patch Summary", "## Evidence Response", "## Verification Steps"],
                        "llm_objective": "deeper-stage-reach",
                        "failure_reason_codes": ["stage-reach-blocked", "shallow-crash-recurrence"],
                        "raw_signal_summary": {"smoke_log_signal_count": 2},
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.verify_harness_apply_candidate_result(
                repo_root,
                probe_runner=lambda command, cwd: (0, "session_apply_123\n"),
            )

            self.assertEqual(result["verification_status"], "unverified")
            self.assertTrue(result["delegate_artifact_evidence_response_verified"])
            self.assertFalse(result["delegate_artifact_patch_alignment_verified"])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["verification_status"], "unverified")
            self.assertFalse(manifest["delegate_artifact_patch_alignment_verified"])

    def test_verify_harness_apply_candidate_result_marks_unverified_when_quality_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n\n## Evidence Response\n- llm_objective: deeper-stage-reach\n- failure_reason_codes: stage-reach-blocked, shallow-crash-recurrence\n- response_summary: \n\n## Verification Steps\n\n",
                encoding="utf-8",
            )
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "bridge_status": "succeeded",
                        "delegate_session_id": "session_apply_123",
                        "delegate_artifact_path": str(artifact_path),
                        "delegate_expected_sections": ["## Patch Summary", "## Evidence Response", "## Verification Steps"],
                        "delegate_quality_sections": ["## Patch Summary", "## Evidence Response", "## Verification Steps"],
                        "llm_objective": "deeper-stage-reach",
                        "failure_reason_codes": ["stage-reach-blocked", "shallow-crash-recurrence"],
                        "raw_signal_summary": {"smoke_log_signal_count": 2},
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.verify_harness_apply_candidate_result(
                repo_root,
                probe_runner=lambda command, cwd: (0, "session_apply_123\n"),
            )

            self.assertEqual(result["verification_status"], "unverified")
            self.assertTrue(result["delegate_artifact_shape_verified"])
            self.assertFalse(result["delegate_artifact_quality_verified"])

    def test_main_verify_harness_apply_candidate_result_emits_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- add early return guard\n\n## Verification Steps\n- run build\n",
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "bridge_status": "succeeded",
                        "delegate_session_id": "session_apply_123",
                        "delegate_artifact_path": str(artifact_path),
                        "delegate_expected_sections": ["## Patch Summary", "## Verification Steps"],
                        "delegate_quality_sections": ["## Patch Summary", "## Verification Steps"],
                    }
                ),
                encoding="utf-8",
            )

            original_argv = list(hermes_watch.sys.argv)
            original_run_probe = hermes_watch.run_probe_command
            try:
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--verify-harness-apply-candidate"]
                hermes_watch.run_probe_command = lambda command, cwd=None: (0, "session_apply_123\n")
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv
                hermes_watch.run_probe_command = original_run_probe

            self.assertEqual(exit_code, 0)

    def test_apply_verified_harness_patch_candidate_comment_only_updates_source_and_reruns_probes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            skeleton_dir = repo_root / "fuzz-records" / "harness-skeletons"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            skeleton_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            target_file = skeleton_dir / "sample-target-candidate-1-harness-skeleton.c"
            target_file.write_text(
                "#include <stddef.h>\n#include <stdint.h>\nint LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {\n  return 0;\n}\n",
                encoding="utf-8",
            )
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- comment only note\n\n## Verification Steps\n- run build\n",
                encoding="utf-8",
            )
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_candidate_scope": "comment-only",
                        "verification_status": "verified",
                        "delegate_artifact_path": str(artifact_path),
                        "llm_objective": "smoke-enable-or-fix",
                        "failure_reason_codes": ["smoke-invalid-or-harness-mismatch", "smoke-log-memory-safety-signal"],
                        "raw_signal_summary": {"smoke_log_signal_count": 2, "smoke_log_path": "/tmp/run/smoke.log"},
                        "delegate_artifact_evidence_response_verified": True,
                        "delegate_artifact_patch_alignment_verified": True,
                        "delegate_reported_llm_objective": "smoke-enable-or-fix",
                        "delegate_reported_failure_reason_codes": ["smoke-invalid-or-harness-mismatch", "smoke-log-memory-safety-signal"],
                    }
                ),
                encoding="utf-8",
            )
            calls: list[list[str]] = []

            def probe(command: list[str], cwd: Path) -> tuple[int, str]:
                calls.append(command)
                return 0, "ok\n"

            result = hermes_watch.apply_verified_harness_patch_candidate(repo_root, probe_runner=probe)

            self.assertEqual(result["apply_status"], "applied")
            self.assertEqual(result["build_probe_status"], "passed")
            self.assertEqual(result["smoke_probe_status"], "passed")
            self.assertEqual(result["llm_objective"], "smoke-enable-or-fix")
            self.assertTrue(result["delegate_artifact_evidence_response_verified"])
            self.assertTrue(result["delegate_artifact_patch_alignment_verified"])
            self.assertTrue(result["delegate_diff_alignment_verified"])
            self.assertEqual(result["actual_mutation_shape"], "comment-only")
            self.assertTrue(result["delegate_hunk_intent_alignment_verified"])
            self.assertTrue(any("Hermes guarded apply candidate" in line for line in result["changed_hunk_added_lines_preview"]))
            self.assertIn("smoke-log-memory-safety-signal", result["failure_reason_codes"])
            self.assertEqual(result["raw_signal_summary"]["smoke_log_signal_count"], 2)
            self.assertIn("Hermes guarded apply candidate", target_file.read_text(encoding="utf-8"))
            self.assertEqual(calls[0], ["make", "-n"])
            self.assertEqual(calls[1][0], str(repo_root / "scripts" / "run-smoke.sh"))
            self.assertTrue(Path(result["apply_result_manifest_path"]).exists())
            result_manifest = json.loads(Path(result["apply_result_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(result_manifest["llm_objective"], "smoke-enable-or-fix")
            self.assertTrue(result_manifest["delegate_artifact_evidence_response_verified"])
            self.assertTrue(result_manifest["delegate_artifact_patch_alignment_verified"])
            self.assertTrue(result_manifest["delegate_diff_alignment_verified"])
            self.assertEqual(result_manifest["actual_mutation_shape"], "comment-only")
            self.assertTrue(result_manifest["delegate_hunk_intent_alignment_verified"])
            self.assertTrue(any("Hermes guarded apply candidate" in line for line in result_manifest["changed_hunk_added_lines_preview"]))
            self.assertIn("smoke-log-memory-safety-signal", result_manifest["failure_reason_codes"])

    def test_apply_verified_harness_patch_candidate_guard_only_inserts_min_size_guard(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            skeleton_dir = repo_root / "fuzz-records" / "harness-skeletons"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            skeleton_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            target_file = skeleton_dir / "sample-target-candidate-1-harness-skeleton.c"
            target_file.write_text(
                "#include <stddef.h>\n#include <stdint.h>\nint LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {\n  return 0;\n}\n",
                encoding="utf-8",
            )
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- add size guard\n\n## Verification Steps\n- run smoke\n",
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_candidate_scope": "guard-only",
                        "verification_status": "verified",
                        "delegate_artifact_path": str(artifact_path),
                        "delegate_artifact_evidence_response_verified": True,
                        "delegate_artifact_patch_alignment_verified": True,
                        "delegate_reported_patch_summary": "add size guard",
                        "delegate_reported_response_summary": "add a minimal size guard before decode",
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verified_harness_patch_candidate(repo_root, probe_runner=lambda command, cwd: (0, "ok\n"))

            self.assertEqual(result["apply_status"], "applied")
            self.assertTrue(result["delegate_diff_alignment_verified"])
            self.assertEqual(result["actual_mutation_shape"], "guard-only")
            self.assertTrue(result["delegate_hunk_intent_alignment_verified"])
            self.assertTrue(any("if (size < 4)" in line for line in result["changed_hunk_added_lines_preview"]))
            content = target_file.read_text(encoding="utf-8")
            self.assertIn("size < 4", content)
            self.assertIn("Hermes guarded apply candidate", content)

    def test_apply_verified_harness_patch_candidate_marks_diff_alignment_failure_when_summary_conflicts_with_actual_mutation_shape(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            skeleton_dir = repo_root / "fuzz-records" / "harness-skeletons"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            skeleton_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            target_file = skeleton_dir / "sample-target-candidate-1-harness-skeleton.c"
            target_file.write_text(
                "#include <stddef.h>\n#include <stdint.h>\nint LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {\n  return 0;\n}\n",
                encoding="utf-8",
            )
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- add size guard\n\n## Verification Steps\n- run build\n",
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_candidate_scope": "comment-only",
                        "verification_status": "verified",
                        "delegate_artifact_path": str(artifact_path),
                        "delegate_artifact_evidence_response_verified": True,
                        "delegate_artifact_patch_alignment_verified": True,
                        "delegate_reported_patch_summary": "add size guard",
                        "delegate_reported_response_summary": "add a minimal size guard before decode",
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verified_harness_patch_candidate(repo_root, probe_runner=lambda command, cwd: (0, "ok\n"))

            self.assertEqual(result["apply_status"], "applied")
            self.assertFalse(result["delegate_diff_alignment_verified"])
            self.assertEqual(result["actual_mutation_shape"], "comment-only")
            self.assertFalse(result["delegate_hunk_intent_alignment_verified"])
            self.assertTrue(any("Hermes guarded apply candidate" in line for line in result["changed_hunk_added_lines_preview"]))
            result_manifest = json.loads(Path(result["apply_result_manifest_path"]).read_text(encoding="utf-8"))
            self.assertFalse(result_manifest["delegate_diff_alignment_verified"])
            self.assertEqual(result_manifest["actual_mutation_shape"], "comment-only")
            self.assertFalse(result_manifest["delegate_hunk_intent_alignment_verified"])

    def test_apply_verified_harness_patch_candidate_marks_failure_reason_hunk_alignment_for_smoke_memory_safety_guard(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            skeleton_dir = repo_root / "fuzz-records" / "harness-skeletons"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            skeleton_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            target_file = skeleton_dir / "sample-target-candidate-1-harness-skeleton.c"
            target_file.write_text(
                "#include <stddef.h>\n#include <stdint.h>\nint LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {\n  return 0;\n}\n",
                encoding="utf-8",
            )
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- add size guard\n\n## Verification Steps\n- run smoke\n",
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_candidate_scope": "guard-only",
                        "verification_status": "verified",
                        "delegate_artifact_path": str(artifact_path),
                        "failure_reason_codes": ["smoke-log-memory-safety-signal"],
                        "delegate_artifact_evidence_response_verified": True,
                        "delegate_artifact_patch_alignment_verified": True,
                        "delegate_reported_patch_summary": "add size guard",
                        "delegate_reported_response_summary": "add a minimal size guard before decode",
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verified_harness_patch_candidate(repo_root, probe_runner=lambda command, cwd: (0, "ok\n"))

            self.assertTrue(result["failure_reason_hunk_alignment_verified"])
            self.assertIn("smoke-log-memory-safety-signal", result["failure_reason_hunk_alignment_reasons"][0])
            result_manifest = json.loads(Path(result["apply_result_manifest_path"]).read_text(encoding="utf-8"))
            self.assertTrue(result_manifest["failure_reason_hunk_alignment_verified"])

    def test_apply_verified_harness_patch_candidate_marks_failure_reason_hunk_alignment_failure_for_smoke_signal_comment_patch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            skeleton_dir = repo_root / "fuzz-records" / "harness-skeletons"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            skeleton_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            target_file = skeleton_dir / "sample-target-candidate-1-harness-skeleton.c"
            target_file.write_text(
                "#include <stddef.h>\n#include <stdint.h>\nint LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {\n  return 0;\n}\n",
                encoding="utf-8",
            )
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- comment only note\n\n## Verification Steps\n- run smoke\n",
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_candidate_scope": "comment-only",
                        "verification_status": "verified",
                        "delegate_artifact_path": str(artifact_path),
                        "failure_reason_codes": ["smoke-log-memory-safety-signal"],
                        "delegate_artifact_evidence_response_verified": True,
                        "delegate_artifact_patch_alignment_verified": True,
                        "delegate_reported_patch_summary": "comment only note",
                        "delegate_reported_response_summary": "leave a comment about the current guardrail",
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verified_harness_patch_candidate(repo_root, probe_runner=lambda command, cwd: (0, "ok\n"))

            self.assertFalse(result["failure_reason_hunk_alignment_verified"])
            self.assertTrue(any("expects guard" in reason for reason in result["failure_reason_hunk_alignment_reasons"]))
            result_manifest = json.loads(Path(result["apply_result_manifest_path"]).read_text(encoding="utf-8"))
            self.assertFalse(result_manifest["failure_reason_hunk_alignment_verified"])

    def test_apply_verified_harness_patch_candidate_prefers_top_failure_reason_codes_for_multi_reason_conflict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            skeleton_dir = repo_root / "fuzz-records" / "harness-skeletons"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            skeleton_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            target_file = skeleton_dir / "sample-target-candidate-1-harness-skeleton.c"
            target_file.write_text(
                "#include <stddef.h>\n#include <stdint.h>\nint LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {\n  return 0;\n}\n",
                encoding="utf-8",
            )
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- add size guard\n\n## Verification Steps\n- run smoke\n",
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_candidate_scope": "guard-only",
                        "verification_status": "verified",
                        "delegate_artifact_path": str(artifact_path),
                        "failure_reason_codes": ["build-blocker", "smoke-log-memory-safety-signal"],
                        "top_failure_reason_codes": ["smoke-log-memory-safety-signal", "build-blocker"],
                        "delegate_artifact_evidence_response_verified": True,
                        "delegate_artifact_patch_alignment_verified": True,
                        "delegate_reported_patch_summary": "add size guard",
                        "delegate_reported_response_summary": "add a minimal size guard before decode",
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verified_harness_patch_candidate(repo_root, probe_runner=lambda command, cwd: (0, "ok\n"))

            self.assertTrue(result["failure_reason_hunk_alignment_verified"])
            self.assertEqual(result["failure_reason_hunk_priority_basis"], "top_failure_reason_codes")
            self.assertEqual(result["failure_reason_hunk_primary_reason_code"], "smoke-log-memory-safety-signal")
            self.assertIn("priority winner", result["failure_reason_hunk_alignment_reasons"][0])
            result_manifest = json.loads(Path(result["apply_result_manifest_path"]).read_text(encoding="utf-8"))
            self.assertTrue(result_manifest["failure_reason_hunk_alignment_verified"])
            self.assertEqual(result_manifest["failure_reason_hunk_primary_reason_code"], "smoke-log-memory-safety-signal")

    def test_apply_verified_harness_patch_candidate_marks_priority_conflict_when_top_failure_reason_disagrees_with_hunk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            skeleton_dir = repo_root / "fuzz-records" / "harness-skeletons"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            skeleton_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            target_file = skeleton_dir / "sample-target-candidate-1-harness-skeleton.c"
            target_file.write_text(
                "#include <stddef.h>\n#include <stdint.h>\nint LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {\n  return 0;\n}\n",
                encoding="utf-8",
            )
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- comment only note\n\n## Verification Steps\n- run smoke\n",
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_candidate_scope": "comment-only",
                        "verification_status": "verified",
                        "delegate_artifact_path": str(artifact_path),
                        "failure_reason_codes": ["smoke-log-memory-safety-signal", "build-blocker"],
                        "top_failure_reason_codes": ["smoke-log-memory-safety-signal", "build-blocker"],
                        "delegate_artifact_evidence_response_verified": True,
                        "delegate_artifact_patch_alignment_verified": True,
                        "delegate_reported_patch_summary": "comment only note",
                        "delegate_reported_response_summary": "leave a comment about the current guardrail",
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verified_harness_patch_candidate(repo_root, probe_runner=lambda command, cwd: (0, "ok\n"))

            self.assertFalse(result["failure_reason_hunk_alignment_verified"])
            self.assertEqual(result["failure_reason_hunk_priority_basis"], "top_failure_reason_codes")
            self.assertEqual(result["failure_reason_hunk_primary_reason_code"], "smoke-log-memory-safety-signal")
            self.assertTrue(any("priority winner" in reason and "expects guard-only" in reason for reason in result["failure_reason_hunk_alignment_reasons"]))
            result_manifest = json.loads(Path(result["apply_result_manifest_path"]).read_text(encoding="utf-8"))
            self.assertFalse(result_manifest["failure_reason_hunk_alignment_verified"])
            self.assertEqual(result_manifest["failure_reason_hunk_primary_reason_code"], "smoke-log-memory-safety-signal")

    def test_apply_verified_harness_patch_candidate_surfaces_deferred_secondary_reason_conflict_when_primary_matches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            skeleton_dir = repo_root / "fuzz-records" / "harness-skeletons"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            skeleton_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            target_file = skeleton_dir / "sample-target-candidate-1-harness-skeleton.c"
            target_file.write_text(
                "#include <stddef.h>\n#include <stdint.h>\nint LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {\n  return 0;\n}\n",
                encoding="utf-8",
            )
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- add size guard\n\n## Verification Steps\n- run smoke\n",
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_candidate_scope": "guard-only",
                        "verification_status": "verified",
                        "delegate_artifact_path": str(artifact_path),
                        "failure_reason_codes": ["build-blocker", "smoke-log-memory-safety-signal"],
                        "top_failure_reason_codes": ["smoke-log-memory-safety-signal", "build-blocker"],
                        "delegate_artifact_evidence_response_verified": True,
                        "delegate_artifact_patch_alignment_verified": True,
                        "delegate_reported_patch_summary": "add size guard",
                        "delegate_reported_response_summary": "add a minimal size guard before decode",
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verified_harness_patch_candidate(repo_root, probe_runner=lambda command, cwd: (0, "ok\n"))

            self.assertTrue(result["failure_reason_hunk_alignment_verified"])
            self.assertEqual(result["failure_reason_hunk_secondary_conflict_status"], "present")
            self.assertEqual(result["failure_reason_hunk_secondary_conflict_count"], 1)
            self.assertIn("build-blocker", result["failure_reason_hunk_deferred_reason_codes"])
            self.assertTrue(any("deferred secondary reason" in reason for reason in result["failure_reason_hunk_secondary_conflict_reasons"]))
            result_manifest = json.loads(Path(result["apply_result_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(result_manifest["failure_reason_hunk_secondary_conflict_status"], "present")

    def test_apply_verified_harness_patch_candidate_marks_no_secondary_conflict_when_reasons_agree(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            skeleton_dir = repo_root / "fuzz-records" / "harness-skeletons"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            skeleton_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            target_file = skeleton_dir / "sample-target-candidate-1-harness-skeleton.c"
            target_file.write_text(
                "#include <stddef.h>\n#include <stdint.h>\nint LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {\n  return 0;\n}\n",
                encoding="utf-8",
            )
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- add size guard\n\n## Verification Steps\n- run smoke\n",
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_candidate_scope": "guard-only",
                        "verification_status": "verified",
                        "delegate_artifact_path": str(artifact_path),
                        "failure_reason_codes": ["smoke-log-memory-safety-signal", "harness-probe-memory-safety-signal"],
                        "top_failure_reason_codes": ["smoke-log-memory-safety-signal", "harness-probe-memory-safety-signal"],
                        "delegate_artifact_evidence_response_verified": True,
                        "delegate_artifact_patch_alignment_verified": True,
                        "delegate_reported_patch_summary": "add size guard",
                        "delegate_reported_response_summary": "add a minimal size guard before decode",
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verified_harness_patch_candidate(repo_root, probe_runner=lambda command, cwd: (0, "ok\n"))

            self.assertTrue(result["failure_reason_hunk_alignment_verified"])
            self.assertEqual(result["failure_reason_hunk_secondary_conflict_status"], "none")
            self.assertEqual(result["failure_reason_hunk_secondary_conflict_count"], 0)
            self.assertEqual(result["failure_reason_hunk_secondary_conflict_reasons"], [])
            result_manifest = json.loads(Path(result["apply_result_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(result_manifest["failure_reason_hunk_secondary_conflict_status"], "none")

    def test_apply_verified_harness_patch_candidate_marks_failure_reason_hunk_alignment_failure_for_build_blocker_guard_patch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            skeleton_dir = repo_root / "fuzz-records" / "harness-skeletons"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            skeleton_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            target_file = skeleton_dir / "sample-target-candidate-1-harness-skeleton.c"
            target_file.write_text(
                "#include <stddef.h>\n#include <stdint.h>\nint LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {\n  return 0;\n}\n",
                encoding="utf-8",
            )
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- add size guard\n\n## Verification Steps\n- run build\n",
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_candidate_scope": "guard-only",
                        "verification_status": "verified",
                        "delegate_artifact_path": str(artifact_path),
                        "failure_reason_codes": ["build-blocker"],
                        "delegate_artifact_evidence_response_verified": True,
                        "delegate_artifact_patch_alignment_verified": True,
                        "delegate_reported_patch_summary": "add size guard",
                        "delegate_reported_response_summary": "add a minimal size guard before decode",
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verified_harness_patch_candidate(repo_root, probe_runner=lambda command, cwd: (0, "ok\n"))

            self.assertFalse(result["failure_reason_hunk_alignment_verified"])
            self.assertTrue(any("build-blocker" in reason for reason in result["failure_reason_hunk_alignment_reasons"]))
            result_manifest = json.loads(Path(result["apply_result_manifest_path"]).read_text(encoding="utf-8"))
            self.assertFalse(result_manifest["failure_reason_hunk_alignment_verified"])

    def test_main_apply_verified_harness_patch_candidate_emits_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            skeleton_dir = repo_root / "fuzz-records" / "harness-skeletons"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            skeleton_dir.mkdir(parents=True)
            (repo_root / "meson.build").write_text("project('sample-target', 'c')\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            target_file = skeleton_dir / "sample-target-candidate-1-harness-skeleton.c"
            target_file.write_text(
                "#include <stddef.h>\n#include <stdint.h>\nint LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {\n  return 0;\n}\n",
                encoding="utf-8",
            )
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- comment only note\n\n## Verification Steps\n- run build\n",
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_candidate_scope": "comment-only",
                        "verification_status": "verified",
                        "delegate_artifact_path": str(artifact_path),
                    }
                ),
                encoding="utf-8",
            )

            original_argv = list(hermes_watch.sys.argv)
            original_run_probe = hermes_watch.run_probe_command
            try:
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--apply-verified-harness-patch-candidate"]
                hermes_watch.run_probe_command = lambda command, cwd=None: (0, "ok\n")
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv
                hermes_watch.run_probe_command = original_run_probe

            self.assertEqual(exit_code, 0)
            apply_results_dir = repo_root / "fuzz-records" / "harness-apply-results"
            self.assertTrue(any(apply_results_dir.glob("*-harness-apply-result.json")))

    def test_apply_verified_harness_patch_candidate_rolls_back_on_build_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            skeleton_dir = repo_root / "fuzz-records" / "harness-skeletons"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            skeleton_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            target_file = skeleton_dir / "sample-target-candidate-1-harness-skeleton.c"
            original_content = "#include <stddef.h>\n#include <stdint.h>\nint LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {\n  return 0;\n}\n"
            target_file.write_text(original_content, encoding="utf-8")
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- comment only note\n\n## Verification Steps\n- run build\n",
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_candidate_scope": "comment-only",
                        "verification_status": "verified",
                        "delegate_artifact_path": str(artifact_path),
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verified_harness_patch_candidate(
                repo_root,
                probe_runner=lambda command, cwd: (1, "build failed\n") if command[0] in {"make", "cmake", "meson"} else (0, "ok\n"),
            )

            self.assertEqual(result["apply_status"], "rolled_back")
            self.assertEqual(result["build_probe_status"], "failed")
            self.assertEqual(result["rollback_status"], "restored")
            self.assertEqual(result["recovery_decision"], "retry")
            self.assertEqual(result["recovery_failure_streak"], 1)
            self.assertEqual(target_file.read_text(encoding="utf-8"), original_content)

    def test_apply_verified_harness_patch_candidate_escalates_repeated_failures_to_abort(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            skeleton_dir = repo_root / "fuzz-records" / "harness-skeletons"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            skeleton_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            target_file = skeleton_dir / "sample-target-candidate-1-harness-skeleton.c"
            original_content = "#include <stddef.h>\n#include <stdint.h>\nint LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {\n  return 0;\n}\n"
            target_file.write_text(original_content, encoding="utf-8")
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- comment only note\n\n## Verification Steps\n- run build\n",
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_candidate_scope": "comment-only",
                        "verification_status": "verified",
                        "delegate_artifact_path": str(artifact_path),
                        "recovery_failure_streak": 1,
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verified_harness_patch_candidate(
                repo_root,
                probe_runner=lambda command, cwd: (1, "build failed\n") if command[0] in {"make", "cmake", "meson"} else (0, "ok\n"),
            )

            self.assertEqual(result["apply_status"], "rolled_back")
            self.assertEqual(result["recovery_decision"], "abort")
            self.assertEqual(result["recovery_failure_streak"], 2)
            self.assertEqual(target_file.read_text(encoding="utf-8"), original_content)

    def test_apply_verified_harness_patch_candidate_blocks_scope_semantics_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            skeleton_dir = repo_root / "fuzz-records" / "harness-skeletons"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            skeleton_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            target_file = skeleton_dir / "sample-target-candidate-1-harness-skeleton.c"
            original_content = "#include <stddef.h>\n#include <stdint.h>\nint LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {\n  return 0;\n}\n"
            target_file.write_text(original_content, encoding="utf-8")
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- rewrite build scripts and rename the harness entrypoint\n\n## Verification Steps\n- run build\n",
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_candidate_scope": "guard-only",
                        "verification_status": "verified",
                        "delegate_artifact_path": str(artifact_path),
                    }
                ),
                encoding="utf-8",
            )
            calls: list[list[str]] = []

            def probe(command: list[str], cwd: Path) -> tuple[int, str]:
                calls.append(command)
                return 0, "ok\n"

            result = hermes_watch.apply_verified_harness_patch_candidate(repo_root, probe_runner=probe)

            self.assertEqual(result["apply_status"], "blocked")
            self.assertEqual(result["apply_guardrail_status"], "blocked")
            self.assertEqual(result["candidate_semantics_status"], "blocked")
            self.assertEqual(result["diff_safety_status"], "skipped")
            self.assertEqual(result["recovery_decision"], "hold")
            self.assertEqual(result["recovery_failure_streak"], 0)
            self.assertEqual(calls, [])
            self.assertEqual(target_file.read_text(encoding="utf-8"), original_content)

    def test_apply_verified_harness_patch_candidate_blocks_target_outside_generated_harness_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            target_file = repo_root / "src" / "parse_input.c"
            original_content = "int parse_input() { return 0; }\n"
            target_file.write_text(original_content, encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- add comment only note\n\n## Verification Steps\n- run build\n",
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_candidate_scope": "comment-only",
                        "verification_status": "verified",
                        "delegate_artifact_path": str(artifact_path),
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verified_harness_patch_candidate(repo_root, probe_runner=lambda command, cwd: (0, "ok\n"))

            self.assertEqual(result["apply_status"], "blocked")
            self.assertEqual(result["apply_guardrail_status"], "blocked")
            self.assertEqual(result["candidate_semantics_status"], "passed")
            self.assertEqual(result["diff_safety_status"], "blocked")
            self.assertEqual(target_file.read_text(encoding="utf-8"), original_content)

    def test_apply_verified_harness_patch_candidate_blocks_comment_only_summary_requesting_return_mutation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            skeleton_dir = repo_root / "fuzz-records" / "harness-skeletons"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            skeleton_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            target_file = skeleton_dir / "sample-target-candidate-1-harness-skeleton.c"
            original_content = "#include <stddef.h>\n#include <stdint.h>\nint LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {\n  return 0;\n}\n"
            target_file.write_text(original_content, encoding="utf-8")
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- change return 0 to return 1 for smoke fix\n\n## Verification Steps\n- run build\n",
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_candidate_scope": "comment-only",
                        "verification_status": "verified",
                        "delegate_artifact_path": str(artifact_path),
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verified_harness_patch_candidate(repo_root, probe_runner=lambda command, cwd: (0, "ok\n"))

            self.assertEqual(result["apply_status"], "blocked")
            self.assertEqual(result["candidate_semantics_status"], "blocked")
            self.assertEqual(result["diff_safety_status"], "skipped")
            self.assertIn("comment-only-summary-requested-code-mutation", result["candidate_semantics_reasons"])
            self.assertEqual(target_file.read_text(encoding="utf-8"), original_content)

    def test_apply_verified_harness_patch_candidate_blocks_comment_only_summary_requesting_include_and_helper_call(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            skeleton_dir = repo_root / "fuzz-records" / "harness-skeletons"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            skeleton_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            target_file = skeleton_dir / "sample-target-candidate-1-harness-skeleton.c"
            original_content = "#include <stddef.h>\n#include <stdint.h>\nint LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {\n  return 0;\n}\n"
            target_file.write_text(original_content, encoding="utf-8")
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- add include for vector and call helper before parse\n\n## Verification Steps\n- run build\n",
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_candidate_scope": "comment-only",
                        "verification_status": "verified",
                        "delegate_artifact_path": str(artifact_path),
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verified_harness_patch_candidate(repo_root, probe_runner=lambda command, cwd: (0, "ok\n"))

            self.assertEqual(result["apply_status"], "blocked")
            self.assertEqual(result["candidate_semantics_status"], "blocked")
            self.assertEqual(result["diff_safety_status"], "skipped")
            self.assertIn("comment-only-summary-requested-code-mutation", result["candidate_semantics_reasons"])
            self.assertEqual(target_file.read_text(encoding="utf-8"), original_content)

    def test_apply_verified_harness_patch_candidate_blocks_guard_only_touch_outside_fuzzer_entrypoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            skeleton_dir = repo_root / "fuzz-records" / "harness-skeletons"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            skeleton_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            target_file = skeleton_dir / "sample-target-candidate-1-harness-skeleton.c"
            original_content = (
                "#include <stddef.h>\n"
                "#include <stdint.h>\n"
                "static int helper(void) {\n"
                "  return 1;\n"
                "}\n"
                "int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {\n"
                "  return 0;\n"
                "}\n"
            )
            target_file.write_text(original_content, encoding="utf-8")
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- add size guard\n\n## Verification Steps\n- run smoke\n",
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_candidate_scope": "guard-only",
                        "verification_status": "verified",
                        "delegate_artifact_path": str(artifact_path),
                    }
                ),
                encoding="utf-8",
            )
            original_inject = hermes_watch._inject_guarded_patch
            try:
                hermes_watch._inject_guarded_patch = lambda content, scope, note: content.replace("return 1;", "return 2;", 1)
                result = hermes_watch.apply_verified_harness_patch_candidate(repo_root, probe_runner=lambda command, cwd: (0, "ok\n"))
            finally:
                hermes_watch._inject_guarded_patch = original_inject

            self.assertEqual(result["apply_status"], "blocked")
            self.assertEqual(result["diff_safety_status"], "blocked")
            self.assertIn("touched-region-outside-fuzzer-entrypoint", result["diff_safety_reasons"])
            self.assertEqual(target_file.read_text(encoding="utf-8"), original_content)

    def test_apply_verified_harness_patch_candidate_uses_custom_editable_region_policy_from_profile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            custom_harness_dir = repo_root / "custom-artifacts" / "generated-harnesses"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            custom_harness_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            default_profile_path = repo_root / "fuzz-records" / "profiles" / "openhtj2k-target-profile-v1.yaml"
            default_profile_path.parent.mkdir(parents=True)
            default_profile_path.write_text(
                """
schema_version: target-profile/v1
meta:
  name: custom-target-profile
target:
  project: custom-project
  current_campaign:
    primary_mode: custom-mode
    primary_binary: custom_project_harness
  adapter:
    key: custom-project
    notification_label: Custom Project fuzz
    report_target: custom_project_harness
    build_command:
      - bash
      - scripts/custom-build.sh
    smoke_binary_relpath: build/custom-harness
    smoke_command_prefix:
      - bash
      - scripts/custom-smoke.sh
    fuzz_command:
      - bash
      - scripts/custom-fuzz.sh
    editable_harness_relpath: custom-artifacts/generated-harnesses
    fuzz_entrypoint_names:
      - CustomFuzzEntry
    guard_condition: size <= 8
    guard_return_statement: return -1;
stages:
  - id: parse
    description: parse
    stage_class: shallow
    depth_rank: 1
""".strip()
                + "\n",
                encoding="utf-8",
            )
            target_file = custom_harness_dir / "sample-target-candidate-1-harness-skeleton.c"
            original_content = (
                "#include <stddef.h>\n"
                "#include <stdint.h>\n"
                "int CustomFuzzEntry(const uint8_t *data, size_t size) {\n"
                "  return 0;\n"
                "}\n"
            )
            target_file.write_text(original_content, encoding="utf-8")
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- add size guard\n\n## Verification Steps\n- run smoke\n",
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_candidate_scope": "guard-only",
                        "verification_status": "verified",
                        "delegate_artifact_path": str(artifact_path),
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verified_harness_patch_candidate(repo_root, probe_runner=lambda command, cwd: (0, "ok\n"))

            self.assertEqual(result["apply_status"], "applied")
            self.assertEqual(result["diff_safety_status"], "passed")
            self.assertEqual(target_file.read_text(encoding="utf-8"), "#include <stddef.h>\n#include <stdint.h>\nint CustomFuzzEntry(const uint8_t *data, size_t size) {\n  /* Hermes guarded apply candidate: add size guard */\n  if (size <= 8) {\n    return -1;\n  }\n  return 0;\n}\n")

    def test_apply_verified_harness_patch_candidate_blocks_comment_only_non_whitelisted_edit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            skeleton_dir = repo_root / "fuzz-records" / "harness-skeletons"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            skeleton_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            target_file = skeleton_dir / "sample-target-candidate-1-harness-skeleton.c"
            original_content = "#include <stddef.h>\n#include <stdint.h>\nint LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {\n  return 0;\n}\n"
            target_file.write_text(original_content, encoding="utf-8")
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- comment only note\n\n## Verification Steps\n- run build\n",
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_candidate_scope": "comment-only",
                        "verification_status": "verified",
                        "delegate_artifact_path": str(artifact_path),
                    }
                ),
                encoding="utf-8",
            )
            original_inject = hermes_watch._inject_guarded_patch
            try:
                hermes_watch._inject_guarded_patch = lambda content, scope, note: content.replace("return 0;", "  return 1;\n", 1)
                result = hermes_watch.apply_verified_harness_patch_candidate(repo_root, probe_runner=lambda command, cwd: (0, "ok\n"))
            finally:
                hermes_watch._inject_guarded_patch = original_inject

            self.assertEqual(result["apply_status"], "blocked")
            self.assertEqual(result["diff_safety_status"], "blocked")
            self.assertIn("comment-only-non-whitelisted-edit", result["diff_safety_reasons"])
            self.assertEqual(target_file.read_text(encoding="utf-8"), original_content)

    def test_apply_verified_harness_patch_candidate_blocks_guard_only_signature_mutation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            skeleton_dir = repo_root / "fuzz-records" / "harness-skeletons"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            skeleton_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            target_file = skeleton_dir / "sample-target-candidate-1-harness-skeleton.c"
            original_content = (
                "#include <stddef.h>\n"
                "#include <stdint.h>\n"
                "int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {\n"
                "  return 0;\n"
                "}\n"
            )
            target_file.write_text(original_content, encoding="utf-8")
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- add size guard\n\n## Verification Steps\n- run smoke\n",
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_candidate_scope": "guard-only",
                        "verification_status": "verified",
                        "delegate_artifact_path": str(artifact_path),
                    }
                ),
                encoding="utf-8",
            )
            original_inject = hermes_watch._inject_guarded_patch
            try:
                hermes_watch._inject_guarded_patch = lambda content, scope, note: content.replace(
                    "int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {",
                    "int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size, int mode) {",
                    1,
                )
                result = hermes_watch.apply_verified_harness_patch_candidate(repo_root, probe_runner=lambda command, cwd: (0, "ok\n"))
            finally:
                hermes_watch._inject_guarded_patch = original_inject

            self.assertEqual(result["apply_status"], "blocked")
            self.assertEqual(result["diff_safety_status"], "blocked")
            self.assertIn("guard-only-non-whitelisted-edit", result["diff_safety_reasons"])
            self.assertEqual(target_file.read_text(encoding="utf-8"), original_content)

    def test_apply_verified_harness_patch_candidate_blocks_guard_only_inline_side_effect(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            skeleton_dir = repo_root / "fuzz-records" / "harness-skeletons"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            skeleton_dir.mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            target_file = skeleton_dir / "sample-target-candidate-1-harness-skeleton.c"
            original_content = (
                "#include <stddef.h>\n"
                "#include <stdint.h>\n"
                "int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {\n"
                "  return 0;\n"
                "}\n"
            )
            target_file.write_text(original_content, encoding="utf-8")
            artifact_path = apply_dir / "candidate-note.md"
            artifact_path.write_text(
                "# Guarded Patch Candidate\n\n## Patch Summary\n- add size guard\n\n## Verification Steps\n- run smoke\n",
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_candidate_scope": "guard-only",
                        "verification_status": "verified",
                        "delegate_artifact_path": str(artifact_path),
                    }
                ),
                encoding="utf-8",
            )
            original_inject = hermes_watch._inject_guarded_patch
            try:
                hermes_watch._inject_guarded_patch = lambda content, scope, note: content.replace(
                    "  return 0;",
                    "  if (size < 4) { helper(); return 0; }",
                    1,
                )
                result = hermes_watch.apply_verified_harness_patch_candidate(repo_root, probe_runner=lambda command, cwd: (0, "ok\n"))
            finally:
                hermes_watch._inject_guarded_patch = original_inject

            self.assertEqual(result["apply_status"], "blocked")
            self.assertEqual(result["diff_safety_status"], "blocked")
            self.assertIn("guard-only-non-whitelisted-edit", result["diff_safety_reasons"])
            self.assertEqual(target_file.read_text(encoding="utf-8"), original_content)

    def test_route_harness_apply_recovery_requeues_retry_decision(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            result_dir = repo_root / "fuzz-records" / "harness-apply-results"
            apply_dir.mkdir(parents=True)
            result_dir.mkdir(parents=True)
            target_file = repo_root / "fuzz-records" / "harness-skeletons" / "sample-target-candidate-1-harness-skeleton.c"
            target_file.parent.mkdir(parents=True)
            target_file.write_text("int LLVMFuzzerTestOneInput(const unsigned char *data, unsigned long size) { return 0; }\n", encoding="utf-8")
            result_path = result_dir / "sample-target-candidate-1-harness-apply-result.json"
            result_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_status": "rolled_back",
                        "recovery_decision": "retry",
                        "recovery_failure_streak": 1,
                        "recovery_status": "retryable",
                    }
                ),
                encoding="utf-8",
            )
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_result_manifest_path": str(result_path),
                        "recovery_decision": "retry",
                        "recovery_failure_streak": 1,
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.route_harness_apply_recovery(repo_root)

            self.assertEqual(result["recovery_decision"], "retry")
            self.assertEqual(result["action_code"], "requeue-guarded-apply-candidate")
            self.assertEqual(result["registry_name"], "harness_apply_retry_queue.json")
            registry = json.loads((repo_root / "fuzz-artifacts" / "automation" / "harness_apply_retry_queue.json").read_text(encoding="utf-8"))
            self.assertEqual(len(registry["entries"]), 1)
            self.assertEqual(registry["entries"][0]["recovery_decision"], "retry")

    def test_route_harness_apply_recovery_routes_hold_without_bridge_channel(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            result_dir = repo_root / "fuzz-records" / "harness-apply-results"
            apply_dir.mkdir(parents=True)
            result_dir.mkdir(parents=True)
            target_file = repo_root / "fuzz-records" / "harness-skeletons" / "sample-target-candidate-1-harness-skeleton.c"
            target_file.parent.mkdir(parents=True)
            target_file.write_text("int LLVMFuzzerTestOneInput(const unsigned char *data, unsigned long size) { return 0; }\n", encoding="utf-8")
            result_path = result_dir / "sample-target-candidate-1-harness-apply-result.json"
            result_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_status": "blocked",
                        "recovery_decision": "hold",
                        "recovery_failure_streak": 0,
                        "recovery_status": "deferred",
                    }
                ),
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_result_manifest_path": str(result_path),
                        "recovery_decision": "hold",
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.route_harness_apply_recovery(repo_root)

            self.assertEqual(result["recovery_decision"], "hold")
            self.assertEqual(result["action_code"], "hold-guarded-apply-candidate")
            self.assertIsNone(result["bridge_channel"])
            registry = json.loads((repo_root / "fuzz-artifacts" / "automation" / "harness_apply_hold_queue.json").read_text(encoding="utf-8"))
            self.assertEqual(registry["entries"][0]["bridge_channel"], None)

    def test_route_harness_apply_recovery_escalated_hold_followup_overrides_retry_routing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            result_dir = repo_root / "fuzz-records" / "harness-apply-results"
            apply_dir.mkdir(parents=True)
            result_dir.mkdir(parents=True)
            target_file = repo_root / "fuzz-records" / "harness-skeletons" / "sample-target-candidate-1-harness-skeleton.c"
            target_file.parent.mkdir(parents=True)
            target_file.write_text("int LLVMFuzzerTestOneInput(const unsigned char *data, unsigned long size) { return 0; }\n", encoding="utf-8")
            result_path = result_dir / "sample-target-candidate-1-harness-apply-result.json"
            result_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_status": "rolled_back",
                        "recovery_decision": "retry",
                        "recovery_failure_streak": 1,
                        "recovery_status": "retryable",
                    }
                ),
                encoding="utf-8",
            )
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_result_manifest_path": str(result_path),
                        "recovery_decision": "retry",
                        "recovery_followup_failure_policy_status": "escalate",
                        "recovery_followup_failure_policy_reason": "delegate-quality-gap",
                        "recovery_followup_failure_action_code": "halt_and_review_harness",
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.route_harness_apply_recovery(repo_root)

            self.assertEqual(result["recovery_decision"], "hold")
            self.assertEqual(result["routing_risk_level"], "high")
            self.assertEqual(result["routing_reverse_linkage_status"], "override-from-followup-escalation")
            registry = json.loads((repo_root / "fuzz-artifacts" / "automation" / "harness_apply_hold_queue.json").read_text(encoding="utf-8"))
            self.assertEqual(registry["entries"][0]["recovery_decision"], "hold")
            self.assertEqual(registry["entries"][0]["routing_reverse_linkage_reason"], "delegate-quality-gap")

    def test_route_harness_apply_recovery_escalated_abort_followup_overrides_retry_routing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            result_dir = repo_root / "fuzz-records" / "harness-apply-results"
            apply_dir.mkdir(parents=True)
            result_dir.mkdir(parents=True)
            target_file = repo_root / "fuzz-records" / "harness-skeletons" / "sample-target-candidate-1-harness-skeleton.c"
            target_file.parent.mkdir(parents=True)
            target_file.write_text("int LLVMFuzzerTestOneInput(const unsigned char *data, unsigned long size) { return 0; }\n", encoding="utf-8")
            result_path = result_dir / "sample-target-candidate-1-harness-apply-result.json"
            result_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_status": "rolled_back",
                        "recovery_decision": "retry",
                        "recovery_failure_streak": 2,
                        "recovery_status": "retryable",
                    }
                ),
                encoding="utf-8",
            )
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_result_manifest_path": str(result_path),
                        "recovery_decision": "retry",
                        "recovery_followup_failure_policy_status": "escalate",
                        "recovery_followup_failure_policy_reason": "retry-budget-exhausted",
                        "recovery_followup_failure_action_code": "regenerate_harness_correction",
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.route_harness_apply_recovery(repo_root)

            self.assertEqual(result["recovery_decision"], "abort")
            self.assertEqual(result["routing_risk_level"], "critical")
            self.assertEqual(result["routing_reverse_linkage_status"], "override-from-followup-escalation")
            registry = json.loads((repo_root / "fuzz-artifacts" / "automation" / "harness_apply_abort_queue.json").read_text(encoding="utf-8"))
            self.assertEqual(registry["entries"][0]["recovery_decision"], "abort")
            self.assertEqual(registry["entries"][0]["routing_reverse_linkage_reason"], "retry-budget-exhausted")

    def test_route_harness_apply_recovery_secondary_conflict_overrides_retry_to_hold_for_reviewable_tension(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            result_dir = repo_root / "fuzz-records" / "harness-apply-results"
            apply_dir.mkdir(parents=True)
            result_dir.mkdir(parents=True)
            target_file = repo_root / "fuzz-records" / "harness-skeletons" / "sample-target-candidate-1-harness-skeleton.c"
            target_file.parent.mkdir(parents=True)
            target_file.write_text("int LLVMFuzzerTestOneInput(const unsigned char *data, unsigned long size) { return 0; }\n", encoding="utf-8")
            result_path = result_dir / "sample-target-candidate-1-harness-apply-result.json"
            result_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_status": "rolled_back",
                        "recovery_decision": "retry",
                        "recovery_failure_streak": 1,
                        "recovery_status": "retryable",
                        "failure_reason_hunk_secondary_conflict_status": "present",
                        "failure_reason_hunk_secondary_conflict_count": 1,
                        "failure_reason_hunk_secondary_conflict_reasons": [
                            "stage-reach-blocked: deferred secondary reason expects deeper-stage-reach hunk intent, got guard-only"
                        ],
                        "failure_reason_hunk_deferred_reason_codes": ["stage-reach-blocked"],
                    }
                ),
                encoding="utf-8",
            )
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_result_manifest_path": str(result_path),
                        "recovery_decision": "retry",
                        "failure_reason_hunk_secondary_conflict_status": "present",
                        "failure_reason_hunk_secondary_conflict_count": 1,
                        "failure_reason_hunk_secondary_conflict_reasons": [
                            "stage-reach-blocked: deferred secondary reason expects deeper-stage-reach hunk intent, got guard-only"
                        ],
                        "failure_reason_hunk_deferred_reason_codes": ["stage-reach-blocked"],
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.route_harness_apply_recovery(repo_root)

            self.assertEqual(result["recovery_decision"], "hold")
            self.assertEqual(result["routing_risk_level"], "high")
            self.assertEqual(result["routing_secondary_conflict_status"], "override-from-secondary-conflict-hold")
            self.assertEqual(result["routing_secondary_conflict_severity"], "medium")
            self.assertEqual(result["routing_secondary_conflict_actionability"], "review")
            self.assertEqual(result["routing_secondary_conflict_count"], 1)
            self.assertEqual(result["routing_secondary_conflict_deferred_reason_codes"], ["stage-reach-blocked"])
            registry = json.loads((repo_root / "fuzz-artifacts" / "automation" / "harness_apply_hold_queue.json").read_text(encoding="utf-8"))
            self.assertEqual(registry["entries"][0]["recovery_decision"], "hold")
            self.assertEqual(registry["entries"][0]["routing_secondary_conflict_status"], "override-from-secondary-conflict-hold")
            self.assertEqual(registry["entries"][0]["routing_secondary_conflict_severity"], "medium")
            self.assertEqual(registry["entries"][0]["routing_secondary_conflict_actionability"], "review")

    def test_route_harness_apply_recovery_secondary_conflict_overrides_retry_to_abort_for_severe_build_tension(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            result_dir = repo_root / "fuzz-records" / "harness-apply-results"
            apply_dir.mkdir(parents=True)
            result_dir.mkdir(parents=True)
            target_file = repo_root / "fuzz-records" / "harness-skeletons" / "sample-target-candidate-1-harness-skeleton.c"
            target_file.parent.mkdir(parents=True)
            target_file.write_text("int LLVMFuzzerTestOneInput(const unsigned char *data, unsigned long size) { return 0; }\n", encoding="utf-8")
            result_path = result_dir / "sample-target-candidate-1-harness-apply-result.json"
            result_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_status": "rolled_back",
                        "recovery_decision": "retry",
                        "recovery_failure_streak": 1,
                        "recovery_status": "retryable",
                        "failure_reason_hunk_secondary_conflict_status": "present",
                        "failure_reason_hunk_secondary_conflict_count": 1,
                        "failure_reason_hunk_secondary_conflict_reasons": [
                            "build-blocker: deferred secondary reason expects build-fix hunk intent, got guard-only"
                        ],
                        "failure_reason_hunk_deferred_reason_codes": ["build-blocker"],
                    }
                ),
                encoding="utf-8",
            )
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_result_manifest_path": str(result_path),
                        "recovery_decision": "retry",
                        "failure_reason_hunk_secondary_conflict_status": "present",
                        "failure_reason_hunk_secondary_conflict_count": 1,
                        "failure_reason_hunk_secondary_conflict_reasons": [
                            "build-blocker: deferred secondary reason expects build-fix hunk intent, got guard-only"
                        ],
                        "failure_reason_hunk_deferred_reason_codes": ["build-blocker"],
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.route_harness_apply_recovery(repo_root)

            self.assertEqual(result["recovery_decision"], "abort")
            self.assertEqual(result["routing_risk_level"], "critical")
            self.assertEqual(result["routing_secondary_conflict_status"], "override-from-secondary-conflict-abort")
            self.assertEqual(result["routing_secondary_conflict_severity"], "high")
            self.assertEqual(result["routing_secondary_conflict_actionability"], "corrective-regeneration")
            self.assertEqual(result["routing_secondary_conflict_deferred_reason_codes"], ["build-blocker"])
            registry = json.loads((repo_root / "fuzz-artifacts" / "automation" / "harness_apply_abort_queue.json").read_text(encoding="utf-8"))
            self.assertEqual(registry["entries"][0]["recovery_decision"], "abort")
            self.assertEqual(registry["entries"][0]["routing_secondary_conflict_status"], "override-from-secondary-conflict-abort")
            self.assertEqual(registry["entries"][0]["routing_secondary_conflict_severity"], "high")
            self.assertEqual(registry["entries"][0]["routing_secondary_conflict_actionability"], "corrective-regeneration")

    def test_route_harness_apply_recovery_marks_no_secondary_conflict_when_retry_path_is_clean(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            result_dir = repo_root / "fuzz-records" / "harness-apply-results"
            apply_dir.mkdir(parents=True)
            result_dir.mkdir(parents=True)
            target_file = repo_root / "fuzz-records" / "harness-skeletons" / "sample-target-candidate-1-harness-skeleton.c"
            target_file.parent.mkdir(parents=True)
            target_file.write_text("int LLVMFuzzerTestOneInput(const unsigned char *data, unsigned long size) { return 0; }\n", encoding="utf-8")
            result_path = result_dir / "sample-target-candidate-1-harness-apply-result.json"
            result_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_status": "rolled_back",
                        "recovery_decision": "retry",
                        "recovery_failure_streak": 1,
                        "recovery_status": "retryable",
                        "failure_reason_hunk_secondary_conflict_status": "none",
                        "failure_reason_hunk_secondary_conflict_count": 0,
                        "failure_reason_hunk_secondary_conflict_reasons": [],
                        "failure_reason_hunk_deferred_reason_codes": [],
                    }
                ),
                encoding="utf-8",
            )
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_result_manifest_path": str(result_path),
                        "recovery_decision": "retry",
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.route_harness_apply_recovery(repo_root)

            self.assertEqual(result["recovery_decision"], "retry")
            self.assertEqual(result["routing_secondary_conflict_status"], "none")
            self.assertEqual(result["routing_secondary_conflict_severity"], "none")
            self.assertEqual(result["routing_secondary_conflict_actionability"], "none")
            self.assertEqual(result["routing_secondary_conflict_count"], 0)
            self.assertEqual(result["routing_secondary_conflict_deferred_reason_codes"], [])
            registry = json.loads((repo_root / "fuzz-artifacts" / "automation" / "harness_apply_retry_queue.json").read_text(encoding="utf-8"))
            self.assertEqual(registry["entries"][0]["recovery_decision"], "retry")
            self.assertEqual(registry["entries"][0]["routing_secondary_conflict_status"], "none")
            self.assertEqual(registry["entries"][0]["routing_secondary_conflict_severity"], "none")
            self.assertEqual(registry["entries"][0]["routing_secondary_conflict_actionability"], "none")

    def test_main_route_harness_apply_recovery_emits_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            result_dir = repo_root / "fuzz-records" / "harness-apply-results"
            apply_dir.mkdir(parents=True)
            result_dir.mkdir(parents=True)
            target_file = repo_root / "fuzz-records" / "harness-skeletons" / "sample-target-candidate-1-harness-skeleton.c"
            target_file.parent.mkdir(parents=True)
            target_file.write_text("int LLVMFuzzerTestOneInput(const unsigned char *data, unsigned long size) { return 0; }\n", encoding="utf-8")
            result_path = result_dir / "sample-target-candidate-1-harness-apply-result.json"
            result_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_status": "rolled_back",
                        "recovery_decision": "retry",
                        "recovery_failure_streak": 1,
                        "recovery_status": "retryable",
                    }
                ),
                encoding="utf-8",
            )
            (apply_dir / "sample-target-candidate-1-harness-apply-candidate.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "target_file_path": str(target_file),
                        "apply_result_manifest_path": str(result_path),
                        "recovery_decision": "retry",
                    }
                ),
                encoding="utf-8",
            )

            original_argv = list(hermes_watch.sys.argv)
            try:
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--route-harness-apply-recovery"]
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv

            self.assertEqual(exit_code, 0)
            recovery_dir = repo_root / "fuzz-records" / "harness-apply-recovery"
            self.assertTrue(any(recovery_dir.glob("*-harness-apply-recovery.json")))

    def test_consume_harness_apply_retry_queue_rearms_bridge(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            bridge_dir = repo_root / "fuzz-records" / "harness-apply-bridge"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            recovery_dir = repo_root / "fuzz-records" / "harness-apply-recovery"
            automation_dir.mkdir(parents=True)
            bridge_dir.mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            recovery_dir.mkdir(parents=True)
            delegate_request_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate-delegate-request.json"
            delegate_request_path.write_text(json.dumps({"goal": "retry patch candidate", "context": "minimal"}), encoding="utf-8")
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "delegate_request_path": str(delegate_request_path),
                        "recovery_decision": "retry",
                    }
                ),
                encoding="utf-8",
            )
            recovery_manifest_path = recovery_dir / "sample-target-candidate-1-harness-apply-recovery.json"
            recovery_manifest_path.write_text(
                json.dumps(
                    {
                        "key": "sample-target:candidate-1:retry",
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "recovery_decision": "retry",
                        "action_code": "requeue-guarded-apply-candidate",
                        "registry_name": "harness_apply_retry_queue.json",
                        "bridge_channel": "hermes-cli-delegate",
                        "apply_candidate_manifest_path": str(manifest_path),
                        "recovery_route_manifest_path": str(recovery_manifest_path),
                    }
                ),
                encoding="utf-8",
            )
            (automation_dir / "harness_apply_retry_queue.json").write_text(
                json.dumps({"entries": [json.loads(recovery_manifest_path.read_text(encoding="utf-8"))]}),
                encoding="utf-8",
            )

            result = hermes_watch.consume_harness_apply_recovery_queue(repo_root)

            self.assertEqual(result["consumed_decision"], "retry")
            self.assertEqual(result["consumer_status"], "rearmed-bridge")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["bridge_status"], "armed")
            self.assertTrue(Path(manifest["bridge_script_path"]).exists())

    def test_consume_harness_apply_hold_queue_marks_review_lane(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            recovery_dir = repo_root / "fuzz-records" / "harness-apply-recovery"
            automation_dir.mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            recovery_dir.mkdir(parents=True)
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(json.dumps({"generated_from_project": "sample-target", "selected_candidate_id": "candidate-1"}), encoding="utf-8")
            recovery_manifest_path = recovery_dir / "sample-target-candidate-1-harness-apply-recovery.json"
            recovery_manifest_path.write_text(
                json.dumps(
                    {
                        "key": "sample-target:candidate-1:hold",
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "recovery_decision": "hold",
                        "action_code": "hold-guarded-apply-candidate",
                        "registry_name": "harness_apply_hold_queue.json",
                        "bridge_channel": None,
                        "apply_candidate_manifest_path": str(manifest_path),
                        "recovery_route_manifest_path": str(recovery_manifest_path),
                    }
                ),
                encoding="utf-8",
            )
            (automation_dir / "harness_apply_hold_queue.json").write_text(
                json.dumps({"entries": [json.loads(recovery_manifest_path.read_text(encoding="utf-8"))]}),
                encoding="utf-8",
            )

            result = hermes_watch.consume_harness_apply_recovery_queue(repo_root)

            self.assertEqual(result["consumed_decision"], "hold")
            self.assertEqual(result["consumer_status"], "parked-for-review")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["recovery_review_status"], "pending-review")

    def test_main_consume_harness_apply_recovery_queue_emits_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            recovery_dir = repo_root / "fuzz-records" / "harness-apply-recovery"
            automation_dir.mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            recovery_dir.mkdir(parents=True)
            delegate_request_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate-delegate-request.json"
            delegate_request_path.write_text(json.dumps({"goal": "retry patch candidate", "context": "minimal"}), encoding="utf-8")
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "delegate_request_path": str(delegate_request_path),
                        "recovery_decision": "retry",
                    }
                ),
                encoding="utf-8",
            )
            recovery_manifest_path = recovery_dir / "sample-target-candidate-1-harness-apply-recovery.json"
            recovery_manifest_path.write_text(
                json.dumps(
                    {
                        "key": "sample-target:candidate-1:retry",
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "recovery_decision": "retry",
                        "action_code": "requeue-guarded-apply-candidate",
                        "registry_name": "harness_apply_retry_queue.json",
                        "bridge_channel": "hermes-cli-delegate",
                        "apply_candidate_manifest_path": str(manifest_path),
                        "recovery_route_manifest_path": str(recovery_manifest_path),
                    }
                ),
                encoding="utf-8",
            )
            (automation_dir / "harness_apply_retry_queue.json").write_text(
                json.dumps({"entries": [json.loads(recovery_manifest_path.read_text(encoding="utf-8"))]}),
                encoding="utf-8",
            )

            original_argv = list(hermes_watch.sys.argv)
            try:
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--consume-harness-apply-recovery-queue"]
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv

            self.assertEqual(exit_code, 0)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["bridge_status"], "armed")

    def test_run_harness_apply_recovery_downstream_automation_launches_and_verifies_retry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            recovery_dir = repo_root / "fuzz-records" / "harness-apply-recovery"
            automation_dir.mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            recovery_dir.mkdir(parents=True)
            delegate_request_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate-delegate-request.json"
            delegate_request_path.write_text(json.dumps({"goal": "retry patch candidate", "context": "minimal"}), encoding="utf-8")
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "delegate_request_path": str(delegate_request_path),
                        "recovery_decision": "retry",
                    }
                ),
                encoding="utf-8",
            )
            recovery_manifest_path = recovery_dir / "sample-target-candidate-1-harness-apply-recovery.json"
            recovery_manifest_path.write_text(
                json.dumps(
                    {
                        "key": "sample-target:candidate-1:retry",
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "recovery_decision": "retry",
                        "action_code": "requeue-guarded-apply-candidate",
                        "registry_name": "harness_apply_retry_queue.json",
                        "bridge_channel": "hermes-cli-delegate",
                        "apply_candidate_manifest_path": str(manifest_path),
                        "recovery_route_manifest_path": str(recovery_manifest_path),
                    }
                ),
                encoding="utf-8",
            )
            (automation_dir / "harness_apply_retry_queue.json").write_text(
                json.dumps({"entries": [json.loads(recovery_manifest_path.read_text(encoding="utf-8"))]}),
                encoding="utf-8",
            )
            original_launch = hermes_watch.launch_harness_apply_candidate_bridge
            original_verify = hermes_watch.verify_harness_apply_candidate_result
            try:
                hermes_watch.launch_harness_apply_candidate_bridge = lambda repo_root_arg: {
                    "selected_candidate_id": "candidate-1",
                    "bridge_status": "succeeded",
                    "delegate_session_id": "session_retry_123",
                }
                hermes_watch.verify_harness_apply_candidate_result = lambda repo_root_arg, probe_runner=None: {
                    "selected_candidate_id": "candidate-1",
                    "verification_status": "verified",
                    "verification_summary": "delegate-session-and-artifact-visible",
                }
                result = hermes_watch.run_harness_apply_recovery_downstream_automation(repo_root)
            finally:
                hermes_watch.launch_harness_apply_candidate_bridge = original_launch
                hermes_watch.verify_harness_apply_candidate_result = original_verify

            self.assertEqual(result["consumer_status"], "rearmed-bridge")
            self.assertEqual(result["downstream_status"], "verified")
            self.assertEqual(result["launch_status"], "succeeded")
            self.assertEqual(result["verification_status"], "verified")

    def test_run_harness_apply_recovery_downstream_automation_enqueues_hold_review_consumer(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            recovery_dir = repo_root / "fuzz-records" / "harness-apply-recovery"
            automation_dir.mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            recovery_dir.mkdir(parents=True)
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "selected_entrypoint_path": "src/lib/fuzz.cpp",
                        "selected_recommended_mode": "coverage",
                        "selected_target_stage": "parse-main-header",
                        "recovery_decision": "hold",
                        "recovery_summary": "guard-only diff intent mismatch",
                    }
                ),
                encoding="utf-8",
            )
            recovery_manifest_path = recovery_dir / "sample-target-candidate-1-harness-apply-recovery.json"
            recovery_manifest_path.write_text(
                json.dumps(
                    {
                        "key": "sample-target:candidate-1:hold",
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "recovery_decision": "hold",
                        "recovery_summary": "guard-only diff intent mismatch",
                        "action_code": "hold-guarded-apply-candidate",
                        "registry_name": "harness_apply_hold_queue.json",
                        "bridge_channel": None,
                        "apply_candidate_manifest_path": str(manifest_path),
                        "recovery_route_manifest_path": str(recovery_manifest_path),
                    }
                ),
                encoding="utf-8",
            )
            (automation_dir / "harness_apply_hold_queue.json").write_text(
                json.dumps({"entries": [json.loads(recovery_manifest_path.read_text(encoding="utf-8"))]}),
                encoding="utf-8",
            )

            result = hermes_watch.run_harness_apply_recovery_downstream_automation(repo_root)

            self.assertEqual(result["consumed_decision"], "hold")
            self.assertEqual(result["downstream_status"], "pending-review")
            self.assertEqual(result["followup_action_code"], "halt_and_review_harness")
            review_registry = json.loads((automation_dir / "harness_review_queue.json").read_text(encoding="utf-8"))
            self.assertEqual(review_registry["entries"][0]["action_code"], "halt_and_review_harness")
            self.assertEqual(review_registry["entries"][0]["selected_candidate_id"], "candidate-1")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["recovery_followup_status"], "queued")
            self.assertEqual(manifest["recovery_followup_action_code"], "halt_and_review_harness")

    def test_run_harness_apply_recovery_downstream_automation_enqueues_abort_corrective_consumer(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            recovery_dir = repo_root / "fuzz-records" / "harness-apply-recovery"
            automation_dir.mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            recovery_dir.mkdir(parents=True)
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "selected_entrypoint_path": "src/lib/fuzz.cpp",
                        "selected_recommended_mode": "coverage",
                        "selected_target_stage": "parse-main-header",
                        "recovery_decision": "abort",
                        "recovery_summary": "repeated rollback after guarded apply",
                    }
                ),
                encoding="utf-8",
            )
            recovery_manifest_path = recovery_dir / "sample-target-candidate-1-harness-apply-recovery.json"
            recovery_manifest_path.write_text(
                json.dumps(
                    {
                        "key": "sample-target:candidate-1:abort",
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "recovery_decision": "abort",
                        "recovery_summary": "repeated rollback after guarded apply",
                        "action_code": "abort-guarded-apply-candidate",
                        "registry_name": "harness_apply_abort_queue.json",
                        "bridge_channel": None,
                        "apply_candidate_manifest_path": str(manifest_path),
                        "recovery_route_manifest_path": str(recovery_manifest_path),
                    }
                ),
                encoding="utf-8",
            )
            (automation_dir / "harness_apply_abort_queue.json").write_text(
                json.dumps({"entries": [json.loads(recovery_manifest_path.read_text(encoding="utf-8"))]}),
                encoding="utf-8",
            )

            result = hermes_watch.run_harness_apply_recovery_downstream_automation(repo_root)

            self.assertEqual(result["consumed_decision"], "abort")
            self.assertEqual(result["downstream_status"], "aborted")
            self.assertEqual(result["followup_action_code"], "regenerate_harness_correction")
            corrective_registry = json.loads((automation_dir / "harness_correction_regeneration_queue.json").read_text(encoding="utf-8"))
            self.assertEqual(corrective_registry["entries"][0]["action_code"], "regenerate_harness_correction")
            self.assertEqual(corrective_registry["entries"][0]["selected_candidate_id"], "candidate-1")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["recovery_followup_status"], "queued")
            self.assertEqual(manifest["recovery_followup_action_code"], "regenerate_harness_correction")

    def test_run_harness_apply_recovery_followup_auto_reingestion_rehydrates_hold_review_into_correction_policy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            automation_dir.mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "selected_entrypoint_path": "src/lib/fuzz.cpp",
                        "selected_recommended_mode": "coverage",
                        "selected_target_stage": "parse-main-header",
                    }
                ),
                encoding="utf-8",
            )
            review_registry_path = automation_dir / "harness_review_queue.json"
            review_registry_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "halt_and_review_harness:sample-target:candidate-1",
                                "action_code": "halt_and_review_harness",
                                "verification_status": "verified",
                                "verification_summary": "delegate-session-artifact-shape-and-quality-visible",
                                "recovery_followup_reason": "hold-review-lane",
                                "apply_candidate_manifest_path": str(manifest_path),
                                "selected_candidate_id": "candidate-1",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            policy_dir = repo_root / "fuzz-records" / "harness-correction-policies"
            policy_dir.mkdir(parents=True)
            policy_manifest_path = policy_dir / "sample-target-candidate-1-harness-correction-policy.json"
            policy_manifest_path.write_text(json.dumps({"decision": "promote-reviewable-correction"}), encoding="utf-8")
            original_write_policy = hermes_watch.write_harness_correction_policy
            try:
                hermes_watch.write_harness_correction_policy = lambda repo_root_arg: {
                    "decision": "promote-reviewable-correction",
                    "policy_manifest_path": str(policy_manifest_path),
                }
                result = hermes_watch.run_harness_apply_recovery_followup_auto_reingestion(repo_root)
            finally:
                hermes_watch.write_harness_correction_policy = original_write_policy

            self.assertEqual(result["followup_action_code"], "halt_and_review_harness")
            self.assertEqual(result["reingestion_target"], "correction-policy")
            self.assertEqual(result["reingestion_status"], "reingested")
            registry = json.loads(review_registry_path.read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["reingestion_status"], "reingested")
            self.assertEqual(entry["reingestion_target"], "correction-policy")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["recovery_followup_reingestion_status"], "reingested")
            self.assertEqual(manifest["recovery_followup_reingestion_target"], "correction-policy")
            self.assertEqual(manifest["recovery_followup_reingestion_artifact_path"], str(policy_manifest_path))

    def test_run_harness_apply_recovery_followup_auto_reingestion_rehydrates_abort_regeneration_into_apply_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            automation_dir.mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "selected_entrypoint_path": "src/lib/fuzz.cpp",
                        "selected_recommended_mode": "coverage",
                        "selected_target_stage": "parse-main-header",
                    }
                ),
                encoding="utf-8",
            )
            corrective_registry_path = automation_dir / "harness_correction_regeneration_queue.json"
            corrective_registry_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "regenerate_harness_correction:sample-target:candidate-1",
                                "action_code": "regenerate_harness_correction",
                                "verification_status": "verified",
                                "verification_summary": "delegate-session-artifact-shape-and-quality-visible",
                                "recovery_followup_reason": "abort-corrective-route",
                                "apply_candidate_manifest_path": str(manifest_path),
                                "selected_candidate_id": "candidate-1",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            new_apply_manifest_path = apply_dir / "sample-target-candidate-2-harness-apply-candidate.json"
            new_apply_manifest_path.write_text(json.dumps({"selected_candidate_id": "candidate-2"}), encoding="utf-8")
            original_write_apply = hermes_watch.write_harness_apply_candidate
            try:
                hermes_watch.write_harness_apply_candidate = lambda repo_root_arg: {
                    "decision": "draft-reviewable-apply-candidate",
                    "apply_candidate_manifest_path": str(new_apply_manifest_path),
                }
                result = hermes_watch.run_harness_apply_recovery_followup_auto_reingestion(repo_root)
            finally:
                hermes_watch.write_harness_apply_candidate = original_write_apply

            self.assertEqual(result["followup_action_code"], "regenerate_harness_correction")
            self.assertEqual(result["reingestion_target"], "apply-candidate")
            self.assertEqual(result["reingestion_status"], "reingested")
            registry = json.loads(corrective_registry_path.read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["reingestion_status"], "reingested")
            self.assertEqual(entry["reingestion_target"], "apply-candidate")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["recovery_followup_reingestion_status"], "reingested")
            self.assertEqual(manifest["recovery_followup_reingestion_target"], "apply-candidate")
            self.assertEqual(manifest["recovery_followup_reingestion_artifact_path"], str(new_apply_manifest_path))

    def test_main_run_harness_apply_recovery_followup_auto_reingestion_emits_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            automation_dir.mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(json.dumps({"selected_candidate_id": "candidate-1"}), encoding="utf-8")
            review_registry_path = automation_dir / "harness_review_queue.json"
            review_registry_path.write_text(
                json.dumps({"entries": [{
                    "key": "halt_and_review_harness:sample-target:candidate-1",
                    "action_code": "halt_and_review_harness",
                    "verification_status": "verified",
                    "recovery_followup_reason": "hold-review-lane",
                    "apply_candidate_manifest_path": str(manifest_path),
                    "selected_candidate_id": "candidate-1",
                }]}),
                encoding="utf-8",
            )
            original_argv = list(hermes_watch.sys.argv)
            original_reingest = hermes_watch.run_harness_apply_recovery_followup_auto_reingestion
            try:
                hermes_watch.run_harness_apply_recovery_followup_auto_reingestion = lambda repo_root_arg: {
                    "followup_action_code": "halt_and_review_harness",
                    "reingestion_target": "correction-policy",
                    "reingestion_status": "reingested",
                    "selected_candidate_id": "candidate-1",
                    "apply_candidate_manifest_path": str(manifest_path),
                }
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--run-harness-apply-recovery-followup-auto-reingestion"]
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv
                hermes_watch.run_harness_apply_recovery_followup_auto_reingestion = original_reingest

            self.assertEqual(exit_code, 0)

    def test_run_harness_apply_reingested_downstream_chaining_chains_hold_reingestion_into_apply_and_reroute(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            original_manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            original_manifest_path.write_text(json.dumps({"selected_candidate_id": "candidate-1"}), encoding="utf-8")
            reingested_manifest_path = apply_dir / "sample-target-candidate-2-harness-apply-candidate.json"
            reingested_manifest_path.write_text(json.dumps({"selected_candidate_id": "candidate-2"}), encoding="utf-8")
            original_reingest = hermes_watch.run_harness_apply_recovery_followup_auto_reingestion
            original_write_apply = hermes_watch.write_harness_apply_candidate
            original_arm = hermes_watch._arm_harness_apply_bridge_from_manifest
            original_launch = hermes_watch.launch_harness_apply_candidate_bridge
            original_verify = hermes_watch.verify_harness_apply_candidate_result
            original_apply = hermes_watch.apply_verified_harness_patch_candidate
            original_route = hermes_watch.route_harness_apply_recovery
            try:
                hermes_watch.run_harness_apply_recovery_followup_auto_reingestion = lambda repo_root_arg: {
                    "followup_action_code": "halt_and_review_harness",
                    "reingestion_target": "correction-policy",
                    "reingestion_status": "reingested",
                    "selected_candidate_id": "candidate-1",
                    "apply_candidate_manifest_path": str(original_manifest_path),
                    "reingestion_artifact_path": str(original_manifest_path),
                }
                hermes_watch.write_harness_apply_candidate = lambda repo_root_arg: {
                    "decision": "draft-reviewable-apply-candidate",
                    "apply_candidate_manifest_path": str(reingested_manifest_path),
                }
                hermes_watch._arm_harness_apply_bridge_from_manifest = lambda manifest_path_arg, manifest_arg, repo_root: {
                    "selected_candidate_id": "candidate-2",
                    "bridge_status": "armed",
                    "apply_candidate_manifest_path": str(reingested_manifest_path),
                }
                hermes_watch.launch_harness_apply_candidate_bridge = lambda repo_root_arg: {
                    "selected_candidate_id": "candidate-2",
                    "bridge_status": "succeeded",
                }
                hermes_watch.verify_harness_apply_candidate_result = lambda repo_root_arg, probe_runner=None: {
                    "selected_candidate_id": "candidate-2",
                    "verification_status": "verified",
                }
                hermes_watch.apply_verified_harness_patch_candidate = lambda repo_root_arg: {
                    "selected_candidate_id": "candidate-2",
                    "apply_status": "applied",
                }
                hermes_watch.route_harness_apply_recovery = lambda repo_root_arg: {
                    "selected_candidate_id": "candidate-2",
                    "recovery_decision": "resolved",
                    "action_code": "resolve-guarded-apply-candidate",
                }
                result = hermes_watch.run_harness_apply_reingested_downstream_chaining(repo_root)
            finally:
                hermes_watch.run_harness_apply_recovery_followup_auto_reingestion = original_reingest
                hermes_watch.write_harness_apply_candidate = original_write_apply
                hermes_watch._arm_harness_apply_bridge_from_manifest = original_arm
                hermes_watch.launch_harness_apply_candidate_bridge = original_launch
                hermes_watch.verify_harness_apply_candidate_result = original_verify
                hermes_watch.apply_verified_harness_patch_candidate = original_apply
                hermes_watch.route_harness_apply_recovery = original_route

            self.assertEqual(result["reingestion_target"], "correction-policy")
            self.assertEqual(result["downstream_chain_status"], "rerouted")
            self.assertEqual(result["reroute_decision"], "resolved")
            original_manifest = json.loads(original_manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(original_manifest["recovery_followup_chain_status"], "rerouted")
            self.assertEqual(original_manifest["recovery_followup_chain_apply_candidate_manifest_path"], str(reingested_manifest_path))

    def test_run_harness_apply_reingested_downstream_chaining_chains_abort_reingestion_into_apply_and_reroute(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            original_manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            original_manifest_path.write_text(json.dumps({"selected_candidate_id": "candidate-1"}), encoding="utf-8")
            reingested_manifest_path = apply_dir / "sample-target-candidate-2-harness-apply-candidate.json"
            reingested_manifest_path.write_text(json.dumps({"selected_candidate_id": "candidate-2"}), encoding="utf-8")
            original_reingest = hermes_watch.run_harness_apply_recovery_followup_auto_reingestion
            original_arm = hermes_watch._arm_harness_apply_bridge_from_manifest
            original_launch = hermes_watch.launch_harness_apply_candidate_bridge
            original_verify = hermes_watch.verify_harness_apply_candidate_result
            original_apply = hermes_watch.apply_verified_harness_patch_candidate
            original_route = hermes_watch.route_harness_apply_recovery
            try:
                hermes_watch.run_harness_apply_recovery_followup_auto_reingestion = lambda repo_root_arg: {
                    "followup_action_code": "regenerate_harness_correction",
                    "reingestion_target": "apply-candidate",
                    "reingestion_status": "reingested",
                    "selected_candidate_id": "candidate-1",
                    "apply_candidate_manifest_path": str(original_manifest_path),
                    "reingestion_artifact_path": str(reingested_manifest_path),
                }
                hermes_watch._arm_harness_apply_bridge_from_manifest = lambda manifest_path_arg, manifest_arg, repo_root: {
                    "selected_candidate_id": "candidate-2",
                    "bridge_status": "armed",
                    "apply_candidate_manifest_path": str(reingested_manifest_path),
                }
                hermes_watch.launch_harness_apply_candidate_bridge = lambda repo_root_arg: {
                    "selected_candidate_id": "candidate-2",
                    "bridge_status": "succeeded",
                }
                hermes_watch.verify_harness_apply_candidate_result = lambda repo_root_arg, probe_runner=None: {
                    "selected_candidate_id": "candidate-2",
                    "verification_status": "verified",
                }
                hermes_watch.apply_verified_harness_patch_candidate = lambda repo_root_arg: {
                    "selected_candidate_id": "candidate-2",
                    "apply_status": "applied",
                }
                hermes_watch.route_harness_apply_recovery = lambda repo_root_arg: {
                    "selected_candidate_id": "candidate-2",
                    "recovery_decision": "resolved",
                    "action_code": "resolve-guarded-apply-candidate",
                }
                result = hermes_watch.run_harness_apply_reingested_downstream_chaining(repo_root)
            finally:
                hermes_watch.run_harness_apply_recovery_followup_auto_reingestion = original_reingest
                hermes_watch._arm_harness_apply_bridge_from_manifest = original_arm
                hermes_watch.launch_harness_apply_candidate_bridge = original_launch
                hermes_watch.verify_harness_apply_candidate_result = original_verify
                hermes_watch.apply_verified_harness_patch_candidate = original_apply
                hermes_watch.route_harness_apply_recovery = original_route

            self.assertEqual(result["reingestion_target"], "apply-candidate")
            self.assertEqual(result["downstream_chain_status"], "rerouted")
            self.assertEqual(result["reroute_decision"], "resolved")
            original_manifest = json.loads(original_manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(original_manifest["recovery_followup_chain_status"], "rerouted")
            self.assertEqual(original_manifest["recovery_followup_chain_apply_candidate_manifest_path"], str(reingested_manifest_path))

    def test_main_run_harness_apply_reingested_downstream_chaining_emits_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(json.dumps({"selected_candidate_id": "candidate-1"}), encoding="utf-8")
            original_argv = list(hermes_watch.sys.argv)
            original_chain = hermes_watch.run_harness_apply_reingested_downstream_chaining
            try:
                hermes_watch.run_harness_apply_reingested_downstream_chaining = lambda repo_root_arg: {
                    "reingestion_target": "apply-candidate",
                    "downstream_chain_status": "rerouted",
                    "reroute_decision": "resolved",
                    "apply_candidate_manifest_path": str(manifest_path),
                }
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--run-harness-apply-reingested-downstream-chaining"]
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv
                hermes_watch.run_harness_apply_reingested_downstream_chaining = original_chain

            self.assertEqual(exit_code, 0)

    def test_run_harness_apply_retry_recursive_chaining_respects_cooldown_window(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "selected_candidate_id": "candidate-1",
                        "recovery_recursive_chain_checked_at": hermes_watch.dt.datetime.now().isoformat(timespec="seconds"),
                    }
                ),
                encoding="utf-8",
            )
            original_full = hermes_watch.run_harness_apply_recovery_full_closed_loop_chaining
            calls = []
            try:
                def fake_full(repo_root_arg):
                    calls.append(1)
                    return {
                        "selected_candidate_id": "candidate-1",
                        "apply_candidate_manifest_path": str(manifest_path),
                        "full_chain_status": "rerouted",
                        "reroute_decision": "retry",
                    }
                hermes_watch.run_harness_apply_recovery_full_closed_loop_chaining = fake_full
                result = hermes_watch.run_harness_apply_retry_recursive_chaining(repo_root, max_cycles=3)
            finally:
                hermes_watch.run_harness_apply_recovery_full_closed_loop_chaining = original_full

            self.assertEqual(calls, [])
            self.assertEqual(result["recursive_chain_status"], "cooldown-active")

    def test_run_harness_apply_retry_recursive_chaining_adapts_cooldown_from_routing_risk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "selected_candidate_id": "candidate-1",
                        "recovery_recursive_chain_checked_at": hermes_watch.dt.datetime.now().isoformat(timespec="seconds"),
                        "recovery_route_risk_level": "critical",
                    }
                ),
                encoding="utf-8",
            )
            original_full = hermes_watch.run_harness_apply_recovery_full_closed_loop_chaining
            calls = []
            try:
                def fake_full(repo_root_arg):
                    calls.append(1)
                    return None
                hermes_watch.run_harness_apply_recovery_full_closed_loop_chaining = fake_full
                result = hermes_watch.run_harness_apply_retry_recursive_chaining(repo_root, max_cycles=3)
            finally:
                hermes_watch.run_harness_apply_recovery_full_closed_loop_chaining = original_full

            self.assertEqual(calls, [])
            self.assertEqual(result["recursive_chain_status"], "cooldown-active")
            self.assertEqual(result["cooldown_seconds"], 1800)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["recovery_recursive_chain_cooldown_seconds"], 1800)
            self.assertEqual(manifest["recovery_recursive_chain_adaptive_reason"], "critical-routing-risk")

    def test_run_harness_apply_reingested_downstream_chaining_respects_budget_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            original_manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            original_manifest_path.write_text(
                json.dumps(
                    {
                        "selected_candidate_id": "candidate-1",
                        "recovery_followup_chain_attempt_count": 2,
                    }
                ),
                encoding="utf-8",
            )
            original_reingest = hermes_watch.run_harness_apply_recovery_followup_auto_reingestion
            original_launch = hermes_watch.launch_harness_apply_candidate_bridge
            try:
                hermes_watch.run_harness_apply_recovery_followup_auto_reingestion = lambda repo_root_arg: {
                    "followup_action_code": "regenerate_harness_correction",
                    "reingestion_target": "apply-candidate",
                    "reingestion_status": "reingested",
                    "selected_candidate_id": "candidate-1",
                    "apply_candidate_manifest_path": str(original_manifest_path),
                    "reingestion_artifact_path": str(original_manifest_path),
                }
                hermes_watch.launch_harness_apply_candidate_bridge = lambda repo_root_arg: (_ for _ in ()).throw(AssertionError("launch should not run when budget exhausted"))
                result = hermes_watch.run_harness_apply_reingested_downstream_chaining(repo_root)
            finally:
                hermes_watch.run_harness_apply_recovery_followup_auto_reingestion = original_reingest
                hermes_watch.launch_harness_apply_candidate_bridge = original_launch

            self.assertEqual(result["downstream_chain_status"], "budget-exhausted")
            manifest = json.loads(original_manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["recovery_followup_chain_status"], "budget-exhausted")

    def test_run_harness_apply_reingested_downstream_chaining_adapts_budget_from_routing_risk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            original_manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            original_manifest_path.write_text(
                json.dumps(
                    {
                        "selected_candidate_id": "candidate-1",
                        "recovery_followup_chain_attempt_count": 1,
                        "recovery_route_risk_level": "critical",
                    }
                ),
                encoding="utf-8",
            )
            original_reingest = hermes_watch.run_harness_apply_recovery_followup_auto_reingestion
            original_launch = hermes_watch.launch_harness_apply_candidate_bridge
            try:
                hermes_watch.run_harness_apply_recovery_followup_auto_reingestion = lambda repo_root_arg: {
                    "followup_action_code": "regenerate_harness_correction",
                    "reingestion_target": "apply-candidate",
                    "reingestion_status": "reingested",
                    "selected_candidate_id": "candidate-1",
                    "apply_candidate_manifest_path": str(original_manifest_path),
                    "reingestion_artifact_path": str(original_manifest_path),
                }
                hermes_watch.launch_harness_apply_candidate_bridge = lambda repo_root_arg: (_ for _ in ()).throw(AssertionError("launch should not run when adaptive budget is exhausted"))
                result = hermes_watch.run_harness_apply_reingested_downstream_chaining(repo_root)
            finally:
                hermes_watch.run_harness_apply_recovery_followup_auto_reingestion = original_reingest
                hermes_watch.launch_harness_apply_candidate_bridge = original_launch

            self.assertEqual(result["downstream_chain_status"], "budget-exhausted")
            self.assertEqual(result["downstream_budget"], 1)
            manifest = json.loads(original_manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["recovery_followup_chain_budget"], 1)
            self.assertEqual(manifest["recovery_followup_chain_adaptive_reason"], "critical-routing-risk")

    def test_main_run_harness_apply_recovery_downstream_automation_emits_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            recovery_dir = repo_root / "fuzz-records" / "harness-apply-recovery"
            automation_dir.mkdir(parents=True)
            apply_dir.mkdir(parents=True)
            recovery_dir.mkdir(parents=True)
            delegate_request_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate-delegate-request.json"
            delegate_request_path.write_text(json.dumps({"goal": "retry patch candidate", "context": "minimal"}), encoding="utf-8")
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "delegate_request_path": str(delegate_request_path),
                        "recovery_decision": "retry",
                    }
                ),
                encoding="utf-8",
            )
            recovery_manifest_path = recovery_dir / "sample-target-candidate-1-harness-apply-recovery.json"
            recovery_manifest_path.write_text(
                json.dumps(
                    {
                        "key": "sample-target:candidate-1:retry",
                        "generated_from_project": "sample-target",
                        "selected_candidate_id": "candidate-1",
                        "recovery_decision": "retry",
                        "action_code": "requeue-guarded-apply-candidate",
                        "registry_name": "harness_apply_retry_queue.json",
                        "bridge_channel": "hermes-cli-delegate",
                        "apply_candidate_manifest_path": str(manifest_path),
                        "recovery_route_manifest_path": str(recovery_manifest_path),
                    }
                ),
                encoding="utf-8",
            )
            (automation_dir / "harness_apply_retry_queue.json").write_text(
                json.dumps({"entries": [json.loads(recovery_manifest_path.read_text(encoding="utf-8"))]}),
                encoding="utf-8",
            )
            original_argv = list(hermes_watch.sys.argv)
            original_launch = hermes_watch.launch_harness_apply_candidate_bridge
            original_verify = hermes_watch.verify_harness_apply_candidate_result
            try:
                hermes_watch.launch_harness_apply_candidate_bridge = lambda repo_root_arg: {
                    "selected_candidate_id": "candidate-1",
                    "bridge_status": "succeeded",
                    "delegate_session_id": "session_retry_123",
                }
                hermes_watch.verify_harness_apply_candidate_result = lambda repo_root_arg, probe_runner=None: {
                    "selected_candidate_id": "candidate-1",
                    "verification_status": "verified",
                    "verification_summary": "delegate-session-and-artifact-visible",
                }
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--run-harness-apply-recovery-downstream-automation"]
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv
                hermes_watch.launch_harness_apply_candidate_bridge = original_launch
                hermes_watch.verify_harness_apply_candidate_result = original_verify

            self.assertEqual(exit_code, 0)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["recovery_downstream_status"], "verified")

    def test_run_harness_apply_recovery_full_closed_loop_chaining_applies_and_reroutes_after_verified_retry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(json.dumps({"selected_candidate_id": "candidate-1"}), encoding="utf-8")
            original_downstream = hermes_watch.run_harness_apply_recovery_downstream_automation
            original_apply = hermes_watch.apply_verified_harness_patch_candidate
            original_route = hermes_watch.route_harness_apply_recovery
            try:
                hermes_watch.run_harness_apply_recovery_downstream_automation = lambda repo_root_arg: {
                    "selected_candidate_id": "candidate-1",
                    "apply_candidate_manifest_path": str(manifest_path),
                    "consumer_status": "rearmed-bridge",
                    "consumed_decision": "retry",
                    "downstream_status": "verified",
                    "verification_status": "verified",
                }
                hermes_watch.apply_verified_harness_patch_candidate = lambda repo_root_arg: {
                    "selected_candidate_id": "candidate-1",
                    "apply_status": "applied",
                    "build_probe_status": "passed",
                    "smoke_probe_status": "passed",
                }
                hermes_watch.route_harness_apply_recovery = lambda repo_root_arg: {
                    "selected_candidate_id": "candidate-1",
                    "recovery_decision": "resolved",
                    "action_code": "resolve-guarded-apply-candidate",
                }
                result = hermes_watch.run_harness_apply_recovery_full_closed_loop_chaining(repo_root)
            finally:
                hermes_watch.run_harness_apply_recovery_downstream_automation = original_downstream
                hermes_watch.apply_verified_harness_patch_candidate = original_apply
                hermes_watch.route_harness_apply_recovery = original_route

            self.assertEqual(result["downstream_status"], "verified")
            self.assertEqual(result["apply_status"], "applied")
            self.assertEqual(result["reroute_decision"], "resolved")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["recovery_full_chain_status"], "rerouted")

    def test_main_run_harness_apply_recovery_full_closed_loop_chaining_emits_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(json.dumps({"selected_candidate_id": "candidate-1"}), encoding="utf-8")
            original_argv = list(hermes_watch.sys.argv)
            original_downstream = hermes_watch.run_harness_apply_recovery_downstream_automation
            original_apply = hermes_watch.apply_verified_harness_patch_candidate
            original_route = hermes_watch.route_harness_apply_recovery
            try:
                hermes_watch.run_harness_apply_recovery_downstream_automation = lambda repo_root_arg: {
                    "selected_candidate_id": "candidate-1",
                    "apply_candidate_manifest_path": str(manifest_path),
                    "consumer_status": "rearmed-bridge",
                    "consumed_decision": "retry",
                    "downstream_status": "verified",
                    "verification_status": "verified",
                }
                hermes_watch.apply_verified_harness_patch_candidate = lambda repo_root_arg: {
                    "selected_candidate_id": "candidate-1",
                    "apply_status": "applied",
                    "build_probe_status": "passed",
                    "smoke_probe_status": "passed",
                }
                hermes_watch.route_harness_apply_recovery = lambda repo_root_arg: {
                    "selected_candidate_id": "candidate-1",
                    "recovery_decision": "resolved",
                    "action_code": "resolve-guarded-apply-candidate",
                }
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--run-harness-apply-recovery-full-closed-loop-chaining"]
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv
                hermes_watch.run_harness_apply_recovery_downstream_automation = original_downstream
                hermes_watch.apply_verified_harness_patch_candidate = original_apply
                hermes_watch.route_harness_apply_recovery = original_route

            self.assertEqual(exit_code, 0)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["recovery_full_chain_status"], "rerouted")

    def test_run_harness_apply_recovery_recursive_chaining_stops_at_resolved(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(json.dumps({"selected_candidate_id": "candidate-1"}), encoding="utf-8")
            original_full = hermes_watch.run_harness_apply_recovery_full_closed_loop_chaining
            calls = []
            try:
                def fake_full(repo_root_arg):
                    calls.append(1)
                    if len(calls) == 1:
                        Path(manifest_path).write_text(json.dumps({"selected_candidate_id": "candidate-1"}), encoding="utf-8")
                        return {
                            "selected_candidate_id": "candidate-1",
                            "apply_candidate_manifest_path": str(manifest_path),
                            "full_chain_status": "rerouted",
                            "reroute_decision": "retry",
                        }
                    return {
                        "selected_candidate_id": "candidate-1",
                        "apply_candidate_manifest_path": str(manifest_path),
                        "full_chain_status": "rerouted",
                        "reroute_decision": "resolved",
                    }
                hermes_watch.run_harness_apply_recovery_full_closed_loop_chaining = fake_full
                result = hermes_watch.run_harness_apply_retry_recursive_chaining(repo_root, max_cycles=3)
            finally:
                hermes_watch.run_harness_apply_recovery_full_closed_loop_chaining = original_full

            self.assertEqual(len(calls), 2)
            self.assertEqual(result["recursive_chain_status"], "resolved")
            self.assertEqual(result["cycle_count"], 2)

    def test_run_harness_apply_recovery_recursive_chaining_stops_at_max_cycles(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(json.dumps({"selected_candidate_id": "candidate-1"}), encoding="utf-8")
            original_full = hermes_watch.run_harness_apply_recovery_full_closed_loop_chaining
            calls = []
            try:
                def fake_full(repo_root_arg):
                    calls.append(1)
                    return {
                        "selected_candidate_id": "candidate-1",
                        "apply_candidate_manifest_path": str(manifest_path),
                        "full_chain_status": "rerouted",
                        "reroute_decision": "retry",
                    }
                hermes_watch.run_harness_apply_recovery_full_closed_loop_chaining = fake_full
                result = hermes_watch.run_harness_apply_retry_recursive_chaining(repo_root, max_cycles=2)
            finally:
                hermes_watch.run_harness_apply_recovery_full_closed_loop_chaining = original_full

            self.assertEqual(len(calls), 2)
            self.assertEqual(result["recursive_chain_status"], "max-cycles-reached")
            self.assertEqual(result["cycle_count"], 2)

    def test_run_harness_apply_recovery_ecosystem_recursion_prefers_downstream_lane_after_followup_escalation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "selected_candidate_id": "candidate-1",
                        "recovery_followup_failure_policy_status": "escalate",
                        "recovery_followup_failure_policy_reason": "delegate-quality-gap",
                    }
                ),
                encoding="utf-8",
            )
            original_retry = hermes_watch.run_harness_apply_retry_recursive_chaining
            original_downstream = hermes_watch.run_harness_apply_reingested_downstream_chaining
            try:
                hermes_watch.run_harness_apply_retry_recursive_chaining = lambda repo_root_arg, max_cycles=3: (_ for _ in ()).throw(AssertionError("retry lane should not run first when followup escalation exists"))
                hermes_watch.run_harness_apply_reingested_downstream_chaining = lambda repo_root_arg: {
                    "selected_candidate_id": "candidate-1",
                    "apply_candidate_manifest_path": str(manifest_path),
                    "downstream_chain_status": "rerouted",
                    "reroute_decision": "resolved",
                    "reroute_action_code": "resolve-guarded-apply-candidate",
                }
                result = hermes_watch.run_harness_apply_recovery_ecosystem_recursion(repo_root, max_rounds=2)
            finally:
                hermes_watch.run_harness_apply_retry_recursive_chaining = original_retry
                hermes_watch.run_harness_apply_reingested_downstream_chaining = original_downstream

            self.assertEqual(result["ecosystem_stop_reason"], "downstream-lane-resolved")
            self.assertEqual(result["ecosystem_round_count"], 1)
            self.assertEqual(result["ecosystem_lane_sequence"], ["downstream"])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["recovery_ecosystem_last_lane"], "downstream")

    def test_run_harness_apply_recovery_ecosystem_recursion_crosses_from_retry_into_downstream_lane(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(json.dumps({"selected_candidate_id": "candidate-1"}), encoding="utf-8")
            original_retry = hermes_watch.run_harness_apply_retry_recursive_chaining
            original_downstream = hermes_watch.run_harness_apply_reingested_downstream_chaining
            retry_calls = []
            downstream_calls = []
            try:
                def fake_retry(repo_root_arg, max_cycles=3):
                    retry_calls.append(1)
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    manifest["recovery_followup_failure_policy_status"] = "escalate"
                    manifest["recovery_followup_failure_policy_reason"] = "delegate-quality-gap"
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    return {
                        "selected_candidate_id": "candidate-1",
                        "apply_candidate_manifest_path": str(manifest_path),
                        "recursive_chain_status": "hold",
                        "cycle_count": 1,
                    }

                def fake_downstream(repo_root_arg):
                    downstream_calls.append(1)
                    return {
                        "selected_candidate_id": "candidate-1",
                        "apply_candidate_manifest_path": str(manifest_path),
                        "downstream_chain_status": "rerouted",
                        "reroute_decision": "resolved",
                        "reroute_action_code": "resolve-guarded-apply-candidate",
                    }

                hermes_watch.run_harness_apply_retry_recursive_chaining = fake_retry
                hermes_watch.run_harness_apply_reingested_downstream_chaining = fake_downstream
                result = hermes_watch.run_harness_apply_recovery_ecosystem_recursion(repo_root, max_rounds=3)
            finally:
                hermes_watch.run_harness_apply_retry_recursive_chaining = original_retry
                hermes_watch.run_harness_apply_reingested_downstream_chaining = original_downstream

            self.assertEqual(retry_calls, [1])
            self.assertEqual(downstream_calls, [1])
            self.assertEqual(result["ecosystem_lane_sequence"], ["retry", "downstream"])
            self.assertEqual(result["ecosystem_stop_reason"], "downstream-lane-resolved")
            self.assertEqual(result["ecosystem_round_count"], 2)

    def test_run_harness_apply_recovery_ecosystem_recursion_stops_at_round_budget(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(json.dumps({"selected_candidate_id": "candidate-1"}), encoding="utf-8")
            original_retry = hermes_watch.run_harness_apply_retry_recursive_chaining
            original_downstream = hermes_watch.run_harness_apply_reingested_downstream_chaining
            calls = []
            try:
                hermes_watch.run_harness_apply_retry_recursive_chaining = lambda repo_root_arg, max_cycles=3: calls.append(1) or {
                    "selected_candidate_id": "candidate-1",
                    "apply_candidate_manifest_path": str(manifest_path),
                    "recursive_chain_status": "hold",
                    "cycle_count": 1,
                }
                hermes_watch.run_harness_apply_reingested_downstream_chaining = lambda repo_root_arg: None
                result = hermes_watch.run_harness_apply_recovery_ecosystem_recursion(repo_root, max_rounds=2)
            finally:
                hermes_watch.run_harness_apply_retry_recursive_chaining = original_retry
                hermes_watch.run_harness_apply_reingested_downstream_chaining = original_downstream

            self.assertEqual(calls, [1, 1])
            self.assertEqual(result["ecosystem_status"], "round-budget-exhausted")
            self.assertEqual(result["ecosystem_stop_reason"], "ecosystem-round-budget-exhausted")
            self.assertEqual(result["ecosystem_round_count"], 2)

    def test_main_run_harness_apply_retry_recursive_chaining_emits_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            manifest_path.write_text(json.dumps({"selected_candidate_id": "candidate-1"}), encoding="utf-8")
            original_argv = list(hermes_watch.sys.argv)
            original_recursive = hermes_watch.run_harness_apply_retry_recursive_chaining
            try:
                hermes_watch.run_harness_apply_retry_recursive_chaining = lambda repo_root_arg, max_cycles=3: {
                    "selected_candidate_id": "candidate-1",
                    "apply_candidate_manifest_path": str(manifest_path),
                    "recursive_chain_status": "resolved",
                    "cycle_count": 2,
                }
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--run-harness-apply-retry-recursive-chaining"]
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv
                hermes_watch.run_harness_apply_retry_recursive_chaining = original_recursive

            self.assertEqual(exit_code, 0)

    def test_main_draft_harness_skeleton_emits_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "meson.build").write_text("project('sample-target', 'c')\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")

            original_argv = list(hermes_watch.sys.argv)
            try:
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--draft-harness-skeleton"]
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv

            self.assertEqual(exit_code, 0)
            draft_dir = repo_root / "fuzz-records" / "harness-skeletons"
            self.assertTrue(any(draft_dir.glob("*-harness-skeleton.md")))


class HermesWatchHarnessProbeTests(unittest.TestCase):
    def test_build_harness_probe_draft_infers_build_and_smoke_probe(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            (repo_root / "CMakeLists.txt").write_text("project(sample_target)\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.cpp").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")

            result = hermes_watch.build_harness_probe_draft(repo_root)

            self.assertEqual(result["probe_candidate"]["candidate_id"], "candidate-1")
            self.assertEqual(result["build_probe"]["status"], "planned")
            self.assertEqual(result["build_probe"]["command"][0], "cmake")
            self.assertEqual(result["smoke_probe"]["status"], "planned")
            self.assertTrue(result["smoke_probe"]["seed_path"].endswith("seeds/valid.bin"))
            self.assertEqual(result["smoke_probe"]["command"][0], str(repo_root / "scripts" / "run-smoke.sh"))

    def test_build_harness_probe_draft_uses_profile_selected_adapter_commands(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            default_profile_path = repo_root / "fuzz-records" / "profiles" / "openhtj2k-target-profile-v1.yaml"
            default_profile_path.parent.mkdir(parents=True)
            default_profile_path.write_text(
                """
schema_version: target-profile/v1
meta:
  name: custom-target-profile
target:
  project: custom-project
  current_campaign:
    primary_mode: custom-mode
    primary_binary: custom_project_harness
  adapter:
    key: custom-project
    notification_label: Custom Project fuzz
    report_target: custom_project_harness
    build_command:
      - bash
      - scripts/custom-build.sh
    smoke_binary_relpath: build/custom-harness
    smoke_command_prefix:
      - bash
      - scripts/custom-smoke.sh
    fuzz_command:
      - bash
      - scripts/custom-fuzz.sh
stages:
  - id: parse
    description: parse
    stage_class: shallow
    depth_rank: 1
""".strip()
                + "\n",
                encoding="utf-8",
            )

            result = hermes_watch.build_harness_probe_draft(repo_root)

            self.assertEqual(result["build_probe"]["command"], ["bash", "scripts/custom-build.sh"])
            self.assertEqual(result["smoke_probe"]["command"], ["bash", "scripts/custom-smoke.sh", str(repo_root / "build" / "custom-harness")])

    def test_run_short_harness_probe_executes_build_then_smoke(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            (repo_root / "Makefile").write_text("all:\n\tcc main.c\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")
            calls: list[list[str]] = []

            def probe(command: list[str], cwd: Path) -> tuple[int, str]:
                calls.append(command)
                return 0, "ok\n"

            result = hermes_watch.run_short_harness_probe(repo_root, probe_runner=probe)

            self.assertEqual(result["build_probe_status"], "passed")
            self.assertEqual(result["smoke_probe_status"], "passed")
            self.assertEqual(calls[0], ["make", "-n"])
            self.assertEqual(calls[1][0], str(repo_root / "scripts" / "run-smoke.sh"))
            self.assertTrue(Path(result["probe_manifest_path"]).exists())
            self.assertTrue(Path(result["probe_plan_path"]).exists())

    def test_main_run_short_harness_probe_emits_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            (repo_root / "meson.build").write_text("project('sample-target', 'c')\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")

            original_argv = list(hermes_watch.sys.argv)
            original_run_quiet = hermes_watch.run_quiet
            try:
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--run-short-harness-probe"]
                hermes_watch.run_quiet = lambda command, cwd: (0, "ok\n")
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv
                hermes_watch.run_quiet = original_run_quiet

            self.assertEqual(exit_code, 0)
            draft_dir = repo_root / "fuzz-records" / "harness-probes"
            self.assertTrue(any(draft_dir.glob("*-harness-probe.md")))


class HermesWatchLLMEvidencePacketTests(unittest.TestCase):
    def test_build_llm_evidence_packet_extracts_failure_reasons_from_latest_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "fuzz-artifacts").mkdir(parents=True)
            (repo_root / "fuzz-records" / "probe-feedback").mkdir(parents=True)
            (repo_root / "fuzz-records" / "harness-apply-results").mkdir(parents=True)
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(
                json.dumps(
                    {
                        "outcome": "smoke-failed",
                        "artifact_reason": "smoke-seed-invalidity",
                        "crash_detected": False,
                        "policy_action_code": "promote-seed-to-regression-and-triage",
                        "target_profile_primary_mode": "deep-decode-v3",
                    }
                ),
                encoding="utf-8",
            )
            (repo_root / "fuzz-records" / "probe-feedback" / "sample-target-probe-feedback.json").write_text(
                json.dumps(
                    {
                        "candidate_id": "candidate-1",
                        "bridge_reason": "smoke-probe-failed",
                        "action_code": "halt_and_review_harness",
                        "smoke_probe_status": "failed",
                    }
                ),
                encoding="utf-8",
            )
            (repo_root / "fuzz-records" / "harness-apply-results" / "sample-target-harness-apply-result.json").write_text(
                json.dumps(
                    {
                        "apply_status": "blocked",
                        "candidate_semantics_status": "blocked",
                        "candidate_semantics_reasons": ["comment-only-summary-requested-code-mutation"],
                        "diff_safety_status": "skipped",
                    }
                ),
                encoding="utf-8",
            )

            packet = hermes_watch.build_llm_evidence_packet(repo_root)

            self.assertEqual(packet["current_status"]["outcome"], "smoke-failed")
            self.assertEqual(packet["llm_objective"], "smoke-enable-or-fix")
            self.assertIn("smoke-invalid-or-harness-mismatch", packet["failure_reason_codes"])
            self.assertIn("harness-smoke-probe-failed", packet["failure_reason_codes"])
            self.assertIn("guarded-apply-blocked", packet["failure_reason_codes"])
            self.assertTrue(str(packet["probe_feedback_manifest_path"]).endswith("sample-target-probe-feedback.json"))
            self.assertTrue(str(packet["apply_result_manifest_path"]).endswith("sample-target-harness-apply-result.json"))

    def test_build_llm_evidence_packet_includes_duplicate_crash_review_context(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            automation_dir.mkdir(parents=True)
            plan_path = repo_root / "fuzz-records" / "refiner-plans" / "review_duplicate_crash_replay-run-7.md"
            plan_path.parent.mkdir(parents=True)
            plan_path.write_text("# duplicate review plan\n", encoding="utf-8")
            report_path = repo_root / "fuzz-artifacts" / "runs" / "run-7" / "FUZZING_REPORT.md"
            report_path.parent.mkdir(parents=True)
            report_path.write_text("# report\n", encoding="utf-8")
            current_status = {
                "outcome": "crash",
                "artifact_reason": "sanitizer-crash",
                "crash_detected": True,
                "crash_occurrence_count": 3,
                "crash_fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                "crash_stage": "ht-block-decode",
                "crash_stage_class": "deep",
                "crash_stage_depth_rank": 4,
                "policy_action_code": "review_duplicate_crash_replay",
                "policy_recommended_action": "compare first and latest duplicate repros",
                "report": str(report_path),
                "run_dir": str(report_path.parent),
                "target_profile_primary_mode": "deep-decode-v3",
            }
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(json.dumps(current_status), encoding="utf-8")
            (automation_dir / "duplicate_crash_reviews.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "review_duplicate_crash_replay:asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                                "action_code": "review_duplicate_crash_replay",
                                "status": "completed",
                                "crash_fingerprint": current_status["crash_fingerprint"],
                                "report_path": str(report_path),
                                "run_dir": str(report_path.parent),
                                "executor_plan_path": str(plan_path),
                                "first_seen_run": "/runs/first",
                                "last_seen_run": str(report_path.parent),
                                "occurrence_count": 3,
                                "artifact_paths": ["/runs/first/crash-a", "/runs/run-7/crash-b"],
                                "replay_execution_status": "completed",
                                "replay_execution_markdown_path": "/records/duplicate-crash-replays/run-7.md",
                                "replay_artifact_bytes_equal": False,
                                "first_replay_exit_code": 134,
                                "latest_replay_exit_code": 134,
                                "first_replay_signature": {"fingerprint": current_status["crash_fingerprint"]},
                                "latest_replay_signature": {"fingerprint": current_status["crash_fingerprint"]},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            packet = hermes_watch.write_llm_evidence_packet(repo_root)
            markdown = Path(packet["llm_evidence_markdown_path"]).read_text(encoding="utf-8")

            self.assertEqual(packet["current_status"]["policy_action_code"], "review_duplicate_crash_replay")
            self.assertEqual(packet["duplicate_crash_review"]["executor_plan_path"], str(plan_path))
            self.assertEqual(packet["duplicate_crash_review"]["occurrence_count"], 3)
            self.assertEqual(packet["suggested_action_code"], "minimize_and_reseed")
            self.assertEqual(packet["suggested_candidate_route"], "reseed-before-retry")
            self.assertIn("stable duplicate replay", packet["objective_routing_linkage_summary"])
            self.assertIn("duplicate crash review plan and lineage", packet["suggested_next_inputs"])
            self.assertIn("- replay_execution_status: completed", markdown)
            self.assertIn("- replay_execution_markdown_path: /records/duplicate-crash-replays/run-7.md", markdown)

    def test_build_llm_evidence_packet_recovers_duplicate_review_context_for_repeated_duplicate_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            automation_dir.mkdir(parents=True)
            plan_path = repo_root / "fuzz-records" / "refiner-plans" / "review_duplicate_crash_replay-run-9.md"
            plan_path.parent.mkdir(parents=True)
            plan_path.write_text("# duplicate review plan\n", encoding="utf-8")
            report_path = repo_root / "fuzz-artifacts" / "runs" / "run-9" / "FUZZING_REPORT.md"
            report_path.parent.mkdir(parents=True)
            report_path.write_text("# report\n", encoding="utf-8")
            current_status = {
                "outcome": "crash",
                "artifact_reason": "sanitizer-crash",
                "crash_detected": True,
                "crash_is_duplicate": True,
                "crash_occurrence_count": 2,
                "crash_fingerprint": "asan|coding_units.cpp:3076|SEGV",
                "crash_stage": "tile-part-load",
                "crash_stage_class": "medium",
                "crash_stage_depth_rank": 2,
                "policy_action_code": "record-duplicate-crash",
                "policy_recommended_action": "record duplicate occurrence",
                "report": str(report_path),
                "run_dir": str(report_path.parent),
                "target_profile_primary_mode": "deep-decode-v3",
            }
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(json.dumps(current_status), encoding="utf-8")
            (automation_dir / "duplicate_crash_reviews.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "review_duplicate_crash_replay:asan|coding_units.cpp:3076|SEGV",
                                "action_code": "review_duplicate_crash_replay",
                                "status": "completed",
                                "crash_fingerprint": current_status["crash_fingerprint"],
                                "report_path": str(report_path),
                                "run_dir": str(report_path.parent),
                                "executor_plan_path": str(plan_path),
                                "first_seen_run": "/runs/first",
                                "last_seen_run": str(report_path.parent),
                                "occurrence_count": 2,
                                "artifact_paths": ["/runs/first/crash-a", "/runs/run-9/crash-b"],
                                "replay_execution_status": "completed",
                                "replay_execution_markdown_path": "/records/duplicate-crash-replays/run-9.md",
                                "replay_artifact_bytes_equal": False,
                                "first_replay_exit_code": 139,
                                "latest_replay_exit_code": 139,
                                "first_replay_signature": {"fingerprint": current_status["crash_fingerprint"]},
                                "latest_replay_signature": {"fingerprint": current_status["crash_fingerprint"]},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            packet = hermes_watch.write_llm_evidence_packet(repo_root)

            self.assertEqual(packet["current_status"]["policy_action_code"], "record-duplicate-crash")
            self.assertEqual(packet["duplicate_crash_review"]["executor_plan_path"], str(plan_path))
            self.assertEqual(packet["suggested_action_code"], "minimize_and_reseed")
            self.assertEqual(packet["suggested_candidate_route"], "reseed-before-retry")
            self.assertIn("stable duplicate replay", packet["objective_routing_linkage_summary"])

    def test_main_write_llm_evidence_packet_emits_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "fuzz-artifacts").mkdir(parents=True)
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(
                json.dumps(
                    {
                        "outcome": "build-failed",
                        "artifact_reason": "build-command-failed",
                        "policy_action_code": "fix-build-before-fuzzing",
                        "crash_detected": False,
                    }
                ),
                encoding="utf-8",
            )

            original_argv = list(hermes_watch.sys.argv)
            try:
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--write-llm-evidence-packet"]
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv

            self.assertEqual(exit_code, 0)
            evidence_dir = repo_root / "fuzz-records" / "llm-evidence"
            self.assertTrue(any(evidence_dir.glob("*-llm-evidence.json")))
            self.assertTrue(any(evidence_dir.glob("*-llm-evidence.md")))


class HermesWatchLLMEvidencePacketV02Tests(unittest.TestCase):
    def test_build_llm_evidence_packet_v2_extracts_no_progress_plateau_and_corpus_stagnation_reasons(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            automation_dir.mkdir(parents=True)
            (repo_root / "fuzz-artifacts").mkdir(parents=True, exist_ok=True)
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(
                json.dumps(
                    {
                        "outcome": "no-progress",
                        "artifact_reason": "stalled-coverage-or-corpus",
                        "crash_detected": False,
                        "seconds_since_progress": 5400,
                        "target_profile_primary_mode": "deep-decode-v3",
                    }
                ),
                encoding="utf-8",
            )
            (automation_dir / "run_history.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {"updated_at": "2026-04-16T07:00:00", "outcome": "ok", "cov": 100.0, "corpus_units": 100, "exec_per_second": 500},
                            {"updated_at": "2026-04-16T08:00:00", "outcome": "ok", "cov": 100.0, "corpus_units": 180, "exec_per_second": 510},
                            {"updated_at": "2026-04-16T09:00:00", "outcome": "ok", "cov": 100.0, "corpus_units": 240, "exec_per_second": 505},
                            {"updated_at": "2026-04-16T10:10:00", "outcome": "ok", "cov": 100.0, "corpus_units": 320, "exec_per_second": 520},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            packet = hermes_watch.build_llm_evidence_packet(repo_root)

            self.assertIn("no-progress-stall", packet["failure_reason_codes"])
            self.assertIn("coverage-plateau", packet["failure_reason_codes"])
            self.assertIn("corpus-bloat-low-gain", packet["failure_reason_codes"])
            self.assertIn("stage-reach-blocked", packet["failure_reason_codes"])
            self.assertEqual(packet["llm_objective"], "deeper-stage-reach")
            self.assertTrue(str(packet["run_history_path"]).endswith("run_history.json"))

    def test_build_llm_evidence_packet_v2_extracts_shallow_crash_recurrence_from_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            automation_dir.mkdir(parents=True)
            (repo_root / "fuzz-artifacts").mkdir(parents=True, exist_ok=True)
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(
                json.dumps(
                    {
                        "outcome": "crash",
                        "artifact_reason": "sanitizer-crash",
                        "crash_detected": True,
                        "crash_stage": "parse-main-header",
                        "target_profile_primary_mode": "deep-decode-v3",
                    }
                ),
                encoding="utf-8",
            )
            (automation_dir / "run_history.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {"updated_at": "2026-04-16T07:00:00", "outcome": "crash", "crash_stage": "parse-main-header", "crash_fingerprint": "fp-1"},
                            {"updated_at": "2026-04-16T08:00:00", "outcome": "crash", "crash_stage": "parse-main-header", "crash_fingerprint": "fp-2"},
                            {"updated_at": "2026-04-16T09:00:00", "outcome": "crash", "crash_stage": "parse-main-header", "crash_fingerprint": "fp-3"},
                            {"updated_at": "2026-04-16T10:00:00", "outcome": "crash", "crash_stage": "ht-block-decode", "crash_fingerprint": "fp-4"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            packet = hermes_watch.build_llm_evidence_packet(repo_root)

            self.assertIn("shallow-crash-recurrence", packet["failure_reason_codes"])
            self.assertIn("stage-reach-blocked", packet["failure_reason_codes"])
            self.assertEqual(packet["llm_objective"], "deeper-stage-reach")


class HermesWatchLLMEvidencePacketV03Tests(unittest.TestCase):
    def test_build_llm_evidence_packet_v3_extracts_smoke_log_body_signals(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            run_dir = repo_root / "fuzz-artifacts" / "runs" / "run-1"
            run_dir.mkdir(parents=True)
            report_path = run_dir / "FUZZING_REPORT.md"
            report_path.write_text("# report\n", encoding="utf-8")
            (run_dir / "smoke.log").write_text(
                '==1==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x0\nSUMMARY: AddressSanitizer: heap-buffer-overflow /tmp/project/source/core/parse.cpp:10:3\n',
                encoding="utf-8",
            )
            (repo_root / "fuzz-artifacts").mkdir(parents=True, exist_ok=True)
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(
                json.dumps(
                    {
                        "outcome": "smoke-failed",
                        "artifact_reason": "baseline-input-failed",
                        "crash_detected": False,
                        "report": str(report_path),
                    }
                ),
                encoding="utf-8",
            )

            packet = hermes_watch.build_llm_evidence_packet(repo_root)

            self.assertIn("smoke-log-memory-safety-signal", packet["failure_reason_codes"])
            self.assertGreaterEqual(packet["raw_signal_summary"]["smoke_log_signal_count"], 1)
            self.assertTrue(any("heap-buffer-overflow" in line for line in packet["raw_signal_summary"]["smoke_log_signals"]))

    def test_script_entrypoint_can_run_write_llm_evidence_packet_directly(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "fuzz-artifacts").mkdir(parents=True)
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(
                json.dumps(
                    {
                        "outcome": "build-failed",
                        "artifact_reason": "build-or-config-error",
                        "crash_detected": False,
                    }
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                ["python", str(MODULE_PATH), "--repo", str(repo_root), "--write-llm-evidence-packet"],
                text=True,
                capture_output=True,
                cwd=str(repo_root.parents[0]),
            )

            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            self.assertIn('"wrote_llm_evidence_packet": true', completed.stdout)
            evidence_dir = repo_root / "fuzz-records" / "llm-evidence"
            self.assertTrue(any(evidence_dir.glob("*-llm-evidence.json")))


class HermesWatchLLMEvidencePacketV04Tests(unittest.TestCase):
    def test_build_llm_evidence_packet_v4_extracts_build_and_fuzz_log_body_signals(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            run_dir = repo_root / "fuzz-artifacts" / "runs" / "run-1"
            run_dir.mkdir(parents=True)
            report_path = run_dir / "FUZZING_REPORT.md"
            report_path.write_text("# report\n", encoding="utf-8")
            (run_dir / "build.log").write_text(
                "../src/codec.c:44: runtime error: signed integer overflow\nSUMMARY: UndefinedBehaviorSanitizer: undefined-behavior ../src/codec.c:44\n",
                encoding="utf-8",
            )
            (run_dir / "fuzz.log").write_text(
                "INFO: Loaded 1 modules\n==1==ERROR: AddressSanitizer: heap-use-after-free on address 0x0\nSUMMARY: AddressSanitizer: heap-use-after-free /tmp/project/source/core/decode.c:88:2\n",
                encoding="utf-8",
            )
            (repo_root / "fuzz-artifacts").mkdir(parents=True, exist_ok=True)
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(
                json.dumps(
                    {
                        "outcome": "build-failed",
                        "artifact_reason": "build-or-config-error",
                        "crash_detected": False,
                        "report": str(report_path),
                    }
                ),
                encoding="utf-8",
            )

            packet = hermes_watch.build_llm_evidence_packet(repo_root)

            self.assertIn("build-log-memory-safety-signal", packet["failure_reason_codes"])
            self.assertIn("fuzz-log-memory-safety-signal", packet["failure_reason_codes"])
            self.assertGreaterEqual(packet["raw_signal_summary"]["build_log_signal_count"], 1)
            self.assertGreaterEqual(packet["raw_signal_summary"]["fuzz_log_signal_count"], 1)
            self.assertTrue(any("signed integer overflow" in line for line in packet["raw_signal_summary"]["build_log_signals"]))
            self.assertTrue(any("heap-use-after-free" in line for line in packet["raw_signal_summary"]["fuzz_log_signals"]))

    def test_build_llm_evidence_packet_v4_extracts_probe_and_apply_body_signals(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "fuzz-artifacts").mkdir(parents=True)
            (repo_root / "fuzz-records" / "harness-probes").mkdir(parents=True)
            (repo_root / "fuzz-records" / "harness-apply-results").mkdir(parents=True)
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(
                json.dumps(
                    {
                        "outcome": "smoke-failed",
                        "artifact_reason": "baseline-input-failed",
                        "crash_detected": False,
                    }
                ),
                encoding="utf-8",
            )
            (repo_root / "fuzz-records" / "harness-probes" / "sample-target-harness-probe.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "build_probe_result": {"status": "passed", "output": "ok"},
                        "smoke_probe_result": {
                            "status": "failed",
                            "output": "AddressSanitizer: stack-buffer-overflow\nSUMMARY: AddressSanitizer: stack-buffer-overflow /tmp/project/source/core/smoke.c:12:4\n",
                        },
                    }
                ),
                encoding="utf-8",
            )
            (repo_root / "fuzz-records" / "harness-apply-results" / "sample-target-harness-apply-result.json").write_text(
                json.dumps(
                    {
                        "apply_status": "blocked",
                        "candidate_semantics_status": "blocked",
                        "candidate_semantics_summary": "comment-only request still proposed code mutation outside allowed rail",
                        "candidate_semantics_reasons": ["comment-only-summary-requested-code-mutation"],
                        "verification_summary": "delegate artifact proposed mutation outside comment-only rail",
                    }
                ),
                encoding="utf-8",
            )

            packet = hermes_watch.build_llm_evidence_packet(repo_root)

            self.assertIn("harness-probe-memory-safety-signal", packet["failure_reason_codes"])
            self.assertIn("apply-comment-scope-mismatch-signal", packet["failure_reason_codes"])
            self.assertGreaterEqual(packet["raw_signal_summary"]["probe_signal_count"], 1)
            self.assertGreaterEqual(packet["raw_signal_summary"]["apply_signal_count"], 1)
            self.assertTrue(any("stack-buffer-overflow" in line for line in packet["raw_signal_summary"]["probe_signals"]))
            self.assertTrue(any("comment-only" in line for line in packet["raw_signal_summary"]["apply_signals"]))


class HermesWatchLLMEvidencePacketV05Tests(unittest.TestCase):
    def test_build_llm_evidence_packet_v5_dedups_noisy_signal_lines_and_reduces_body_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            run_dir = repo_root / "fuzz-artifacts" / "runs" / "run-1"
            run_dir.mkdir(parents=True)
            report_path = run_dir / "FUZZING_REPORT.md"
            report_path.write_text("# report\n", encoding="utf-8")
            duplicate_smoke = "==1==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x0\n"
            (run_dir / "smoke.log").write_text(
                duplicate_smoke * 2
                + "SUMMARY: AddressSanitizer: heap-buffer-overflow /tmp/project/source/core/parse.cpp:10:3\n"
                + "runtime error: signed integer overflow\n",
                encoding="utf-8",
            )
            (repo_root / "fuzz-records" / "harness-probes").mkdir(parents=True)
            (repo_root / "fuzz-records" / "harness-probes" / "sample-target-harness-probe.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "build_probe_result": {"status": "passed", "output": "ok"},
                        "smoke_probe_result": {
                            "status": "failed",
                            "output": duplicate_smoke + duplicate_smoke,
                        },
                    }
                ),
                encoding="utf-8",
            )
            (repo_root / "fuzz-artifacts").mkdir(parents=True, exist_ok=True)
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(
                json.dumps(
                    {
                        "outcome": "smoke-failed",
                        "artifact_reason": "baseline-input-failed",
                        "crash_detected": False,
                        "report": str(report_path),
                    }
                ),
                encoding="utf-8",
            )

            packet = hermes_watch.build_llm_evidence_packet(repo_root)

            self.assertEqual(packet["raw_signal_summary"]["smoke_log_signal_count"], 2)
            self.assertEqual(packet["raw_signal_summary"]["probe_signal_count"], 1)
            self.assertEqual(packet["raw_signal_summary"]["smoke_log_signal_summary"], "AddressSanitizer, runtime error")
            self.assertEqual(packet["raw_signal_summary"]["probe_signal_summary"], "AddressSanitizer")
            self.assertEqual(
                packet["raw_signal_summary"]["body_signal_priority"],
                ["smoke_log", "probe"],
            )

    def test_build_llm_evidence_packet_v5_prioritizes_reason_codes_and_exposes_top_reason_codes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            run_dir = repo_root / "fuzz-artifacts" / "runs" / "run-1"
            run_dir.mkdir(parents=True)
            report_path = run_dir / "FUZZING_REPORT.md"
            report_path.write_text("# report\n", encoding="utf-8")
            (run_dir / "build.log").write_text(
                "runtime error: signed integer overflow\nSUMMARY: UndefinedBehaviorSanitizer: undefined-behavior ../src/codec.c:44\n",
                encoding="utf-8",
            )
            (repo_root / "fuzz-artifacts").mkdir(parents=True, exist_ok=True)
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(
                json.dumps(
                    {
                        "outcome": "build-failed",
                        "artifact_reason": "build-or-config-error",
                        "crash_detected": False,
                        "report": str(report_path),
                    }
                ),
                encoding="utf-8",
            )

            packet = hermes_watch.build_llm_evidence_packet(repo_root)

            self.assertEqual(
                packet["failure_reason_codes"][:3],
                ["build-blocker", "build-log-memory-safety-signal", "no-crash-yet"],
            )
            self.assertEqual(
                packet["top_failure_reason_codes"],
                ["build-blocker", "build-log-memory-safety-signal", "no-crash-yet"],
            )
            self.assertEqual(packet["llm_objective"], "build-fix")


class HermesWatchLLMEvidencePacketV06Tests(unittest.TestCase):
    def test_build_llm_evidence_packet_v6_adds_body_to_reason_explanation_for_build_signal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            run_dir = repo_root / "fuzz-artifacts" / "runs" / "run-1"
            run_dir.mkdir(parents=True)
            report_path = run_dir / "FUZZING_REPORT.md"
            report_path.write_text("# report\n", encoding="utf-8")
            (run_dir / "build.log").write_text(
                "runtime error: signed integer overflow\nSUMMARY: UndefinedBehaviorSanitizer: undefined-behavior ../src/codec.c:44\n",
                encoding="utf-8",
            )
            (repo_root / "fuzz-artifacts").mkdir(parents=True, exist_ok=True)
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(
                json.dumps(
                    {
                        "outcome": "build-failed",
                        "artifact_reason": "build-or-config-error",
                        "crash_detected": False,
                        "report": str(report_path),
                    }
                ),
                encoding="utf-8",
            )

            packet = hermes_watch.build_llm_evidence_packet(repo_root)

            build_reason = next(reason for reason in packet["failure_reasons"] if reason["code"] == "build-log-memory-safety-signal")
            self.assertIn("runtime error", build_reason["explanation"])
            self.assertIn("build_log", build_reason["explanation"])
            self.assertEqual(packet["top_failure_reason_explanations"][0]["code"], "build-blocker")
            self.assertIn("build_log_signal_summary", packet["top_failure_reason_explanations"][0]["explanation"])

    def test_build_llm_evidence_packet_v6_adds_body_to_reason_explanation_for_smoke_signal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            run_dir = repo_root / "fuzz-artifacts" / "runs" / "run-1"
            run_dir.mkdir(parents=True)
            report_path = run_dir / "FUZZING_REPORT.md"
            report_path.write_text("# report\n", encoding="utf-8")
            (run_dir / "smoke.log").write_text(
                "==1==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x0\nSUMMARY: AddressSanitizer: heap-buffer-overflow /tmp/project/source/core/parse.cpp:10:3\n",
                encoding="utf-8",
            )
            (repo_root / "fuzz-artifacts").mkdir(parents=True, exist_ok=True)
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(
                json.dumps(
                    {
                        "outcome": "smoke-failed",
                        "artifact_reason": "baseline-input-failed",
                        "crash_detected": False,
                        "report": str(report_path),
                    }
                ),
                encoding="utf-8",
            )

            packet = hermes_watch.build_llm_evidence_packet(repo_root)

            smoke_reason = next(reason for reason in packet["failure_reasons"] if reason["code"] == "smoke-log-memory-safety-signal")
            self.assertIn("AddressSanitizer", smoke_reason["explanation"])
            self.assertIn("smoke_log_signal_summary", smoke_reason["explanation"])
            self.assertEqual(packet["top_failure_reason_explanations"][0]["code"], "smoke-invalid-or-harness-mismatch")
            self.assertIn("smoke_log_signal_summary", packet["top_failure_reason_explanations"][0]["explanation"])


class HermesWatchLLMEvidencePacketV07Tests(unittest.TestCase):
    def test_build_llm_evidence_packet_v7_adds_causal_chain_for_build_reason(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            run_dir = repo_root / "fuzz-artifacts" / "runs" / "run-1"
            run_dir.mkdir(parents=True)
            report_path = run_dir / "FUZZING_REPORT.md"
            report_path.write_text("# report\n", encoding="utf-8")
            (run_dir / "build.log").write_text(
                "runtime error: signed integer overflow\nSUMMARY: UndefinedBehaviorSanitizer: undefined-behavior ../src/codec.c:44\n",
                encoding="utf-8",
            )
            (repo_root / "fuzz-artifacts").mkdir(parents=True, exist_ok=True)
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(
                json.dumps(
                    {
                        "outcome": "build-failed",
                        "artifact_reason": "build-or-config-error",
                        "crash_detected": False,
                        "report": str(report_path),
                    }
                ),
                encoding="utf-8",
            )

            packet = hermes_watch.build_llm_evidence_packet(repo_root)

            build_reason = next(reason for reason in packet["failure_reasons"] if reason["code"] == "build-log-memory-safety-signal")
            self.assertIn("build_log_signal_summary", build_reason["causal_chain"])
            self.assertIn("runtime error", build_reason["causal_chain"])
            self.assertIn("=>", build_reason["causal_chain"])
            self.assertEqual(packet["top_failure_reason_chains"][0]["code"], "build-blocker")
            self.assertIn("build-failed", packet["top_failure_reason_chains"][0]["causal_chain"])

    def test_build_llm_evidence_packet_v7_adds_causal_chain_for_smoke_reason(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            run_dir = repo_root / "fuzz-artifacts" / "runs" / "run-1"
            run_dir.mkdir(parents=True)
            report_path = run_dir / "FUZZING_REPORT.md"
            report_path.write_text("# report\n", encoding="utf-8")
            (run_dir / "smoke.log").write_text(
                "==1==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x0\nSUMMARY: AddressSanitizer: heap-buffer-overflow /tmp/project/source/core/parse.cpp:10:3\n",
                encoding="utf-8",
            )
            (repo_root / "fuzz-artifacts").mkdir(parents=True, exist_ok=True)
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(
                json.dumps(
                    {
                        "outcome": "smoke-failed",
                        "artifact_reason": "baseline-input-failed",
                        "crash_detected": False,
                        "report": str(report_path),
                    }
                ),
                encoding="utf-8",
            )

            packet = hermes_watch.build_llm_evidence_packet(repo_root)

            smoke_reason = next(reason for reason in packet["failure_reasons"] if reason["code"] == "smoke-log-memory-safety-signal")
            self.assertIn("smoke_log_signal_summary", smoke_reason["causal_chain"])
            self.assertIn("AddressSanitizer", smoke_reason["causal_chain"])
            self.assertEqual(packet["top_failure_reason_chains"][0]["code"], "smoke-invalid-or-harness-mismatch")
            self.assertIn("smoke-failed", packet["top_failure_reason_chains"][0]["causal_chain"])


class HermesWatchLLMEvidencePacketFindingEfficiencyTests(unittest.TestCase):
    def test_build_llm_evidence_packet_adds_finding_efficiency_summary_for_plateau_and_corpus_bloat(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            automation_dir.mkdir(parents=True)
            (repo_root / "fuzz-artifacts").mkdir(parents=True, exist_ok=True)
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(
                json.dumps(
                    {
                        "outcome": "no-progress",
                        "artifact_reason": "stalled-coverage-or-corpus",
                        "crash_detected": False,
                        "seconds_since_progress": 5400,
                        "target_profile_primary_mode": "deep-decode-v3",
                    }
                ),
                encoding="utf-8",
            )
            (automation_dir / "run_history.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {"updated_at": "2026-04-16T07:00:00", "outcome": "ok", "cov": 100.0, "corpus_units": 100, "exec_per_second": 500},
                            {"updated_at": "2026-04-16T08:00:00", "outcome": "ok", "cov": 100.0, "corpus_units": 180, "exec_per_second": 510},
                            {"updated_at": "2026-04-16T09:00:00", "outcome": "ok", "cov": 100.0, "corpus_units": 240, "exec_per_second": 505},
                            {"updated_at": "2026-04-16T10:10:00", "outcome": "ok", "cov": 100.0, "corpus_units": 320, "exec_per_second": 520},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            packet = hermes_watch.build_llm_evidence_packet(repo_root)

            self.assertIn("finding_efficiency_summary", packet)
            self.assertEqual(packet["finding_efficiency_summary"]["status"], "weak")
            self.assertEqual(packet["finding_efficiency_summary"]["coverage_delta"], 0.0)
            self.assertEqual(packet["finding_efficiency_summary"]["corpus_growth"], 220)
            self.assertIn("coverage plateau under healthy exec/s", packet["finding_efficiency_summary"]["summary"])
            self.assertIn("corpus growth with low gain", packet["finding_efficiency_summary"]["summary"])
            self.assertIn("finding_efficiency_recommendation", packet)
            self.assertEqual(packet["finding_efficiency_recommendation"], "bias-llm-toward-novelty-and-stage-reach")

    def test_write_llm_evidence_packet_includes_finding_efficiency_markdown_block(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            automation_dir.mkdir(parents=True)
            run_dir = repo_root / "fuzz-artifacts" / "runs" / "run-1"
            run_dir.mkdir(parents=True)
            report_path = run_dir / "FUZZING_REPORT.md"
            report_path.write_text("# report\n", encoding="utf-8")
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(
                json.dumps(
                    {
                        "outcome": "crash",
                        "artifact_reason": "sanitizer-crash",
                        "crash_detected": True,
                        "crash_stage": "parse-main-header",
                        "target_profile_primary_mode": "deep-decode-v3",
                        "report": str(report_path),
                    }
                ),
                encoding="utf-8",
            )
            (automation_dir / "run_history.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {"updated_at": "2026-04-16T07:00:00", "outcome": "crash", "crash_stage": "parse-main-header", "crash_fingerprint": "fp-1", "cov": 30.0, "corpus_units": 10, "exec_per_second": 400},
                            {"updated_at": "2026-04-16T08:00:00", "outcome": "crash", "crash_stage": "parse-main-header", "crash_fingerprint": "fp-1", "cov": 30.1, "corpus_units": 12, "exec_per_second": 390},
                            {"updated_at": "2026-04-16T09:00:00", "outcome": "crash", "crash_stage": "parse-main-header", "crash_fingerprint": "fp-1", "cov": 30.1, "corpus_units": 14, "exec_per_second": 405},
                            {"updated_at": "2026-04-16T10:00:00", "outcome": "crash", "crash_stage": "parse-main-header", "crash_fingerprint": "fp-2", "cov": 30.2, "corpus_units": 16, "exec_per_second": 395},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            packet = hermes_watch.write_llm_evidence_packet(repo_root)
            markdown = Path(packet["llm_evidence_markdown_path"]).read_text(encoding="utf-8")

            self.assertEqual(packet["finding_efficiency_summary"]["status"], "weak")
            self.assertIn("shallow crash dominance", packet["finding_efficiency_summary"]["summary"])
            self.assertIn("## Finding Efficiency", markdown)
            self.assertIn("finding_efficiency_recommendation", markdown)
            self.assertIn("bias-llm-toward-novelty-and-stage-reach", markdown)


class HermesWatchLLMEvidencePacketV09Tests(unittest.TestCase):
    def test_build_llm_evidence_packet_v9_links_deeper_stage_objective_to_promote_route(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            automation_dir.mkdir(parents=True)
            (repo_root / "fuzz-artifacts").mkdir(parents=True, exist_ok=True)
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(
                json.dumps(
                    {
                        "outcome": "no-progress",
                        "artifact_reason": "stalled-coverage-or-corpus",
                        "crash_detected": False,
                        "seconds_since_progress": 5400,
                        "target_profile_primary_mode": "deep-decode-v3",
                    }
                ),
                encoding="utf-8",
            )
            (automation_dir / "run_history.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {"updated_at": "2026-04-16T07:00:00", "outcome": "ok", "cov": 100.0, "corpus_units": 100, "exec_per_second": 500},
                            {"updated_at": "2026-04-16T08:00:00", "outcome": "ok", "cov": 100.0, "corpus_units": 180, "exec_per_second": 510},
                            {"updated_at": "2026-04-16T09:00:00", "outcome": "ok", "cov": 100.0, "corpus_units": 240, "exec_per_second": 505},
                            {"updated_at": "2026-04-16T10:10:00", "outcome": "ok", "cov": 100.0, "corpus_units": 320, "exec_per_second": 520},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            packet = hermes_watch.build_llm_evidence_packet(repo_root)

            self.assertEqual(packet["llm_objective"], "deeper-stage-reach")
            self.assertEqual(packet["suggested_action_code"], "shift_weight_to_deeper_harness")
            self.assertEqual(packet["suggested_candidate_route"], "promote-next-depth")
            self.assertIn("deeper-stage-reach", packet["objective_routing_linkage_summary"])
            self.assertIn("shift_weight_to_deeper_harness", packet["objective_routing_linkage_summary"])
            self.assertIn("top failure narrative", packet["objective_routing_linkage_summary"])

    def test_build_llm_evidence_packet_v9_routes_leak_signal_to_reviewable_cleanup_objective(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            run_dir = repo_root / "fuzz-artifacts" / "runs" / "run-1"
            run_dir.mkdir(parents=True)
            report_path = run_dir / "FUZZING_REPORT.md"
            report_path.write_text("# report\n", encoding="utf-8")
            (run_dir / "fuzz.log").write_text(
                "INFO: Loaded 1 modules\n"
                "==1==ERROR: LeakSanitizer: detected memory leaks\n"
                "    #0 0x123 in j2k_tile::decode /tmp/project/source/core/coding/coding_units.cpp:3927:53\n"
                "SUMMARY: AddressSanitizer: 12312 byte(s) leaked in 1 allocation(s).\n",
                encoding="utf-8",
            )
            (repo_root / "fuzz-artifacts").mkdir(parents=True, exist_ok=True)
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(
                json.dumps(
                    {
                        "outcome": "crash",
                        "artifact_category": "crash",
                        "artifact_reason": "sanitizer-crash",
                        "crash_detected": True,
                        "crash_kind": "asan",
                        "crash_summary": "12312 byte(s) leaked in 1 allocation(s).",
                        "report": str(report_path),
                    }
                ),
                encoding="utf-8",
            )

            packet = hermes_watch.build_llm_evidence_packet(repo_root)

            self.assertIn("leak-sanitizer-signal", packet["failure_reason_codes"])
            self.assertEqual(packet["raw_signal_summary"]["fuzz_log_signal_summary"], "LeakSanitizer, AddressSanitizer")
            self.assertEqual(packet["llm_objective"], "cleanup-leak-closure")
            self.assertEqual(packet["suggested_action_code"], "halt_and_review_harness")
            self.assertEqual(packet["suggested_candidate_route"], "review-current-candidate")

    def test_write_llm_evidence_packet_v9_links_build_fix_to_review_route_in_markdown(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            run_dir = repo_root / "fuzz-artifacts" / "runs" / "run-1"
            run_dir.mkdir(parents=True)
            report_path = run_dir / "FUZZING_REPORT.md"
            report_path.write_text("# report\n", encoding="utf-8")
            (run_dir / "build.log").write_text(
                "runtime error: signed integer overflow\nSUMMARY: UndefinedBehaviorSanitizer: undefined-behavior ../src/codec.c:44\n",
                encoding="utf-8",
            )
            (repo_root / "fuzz-artifacts").mkdir(parents=True, exist_ok=True)
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(
                json.dumps(
                    {
                        "outcome": "build-failed",
                        "artifact_reason": "build-or-config-error",
                        "crash_detected": False,
                        "report": str(report_path),
                    }
                ),
                encoding="utf-8",
            )

            packet = hermes_watch.write_llm_evidence_packet(repo_root)
            markdown = Path(packet["llm_evidence_markdown_path"]).read_text(encoding="utf-8")

            self.assertEqual(packet["llm_objective"], "build-fix")
            self.assertEqual(packet["suggested_action_code"], "halt_and_review_harness")
            self.assertEqual(packet["suggested_candidate_route"], "review-current-candidate")
            self.assertIn("- suggested_action_code: halt_and_review_harness", markdown)
            self.assertIn("- suggested_candidate_route: review-current-candidate", markdown)
            self.assertIn("objective_routing_linkage_summary", markdown)

    def test_build_llm_evidence_packet_v9_does_not_push_deeper_when_deep_critical_crash_already_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            run_dir = repo_root / "fuzz-artifacts" / "runs" / "run-1"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            run_dir.mkdir(parents=True)
            automation_dir.mkdir(parents=True)
            report_path = run_dir / "FUZZING_REPORT.md"
            report_path.write_text("# report\n", encoding="utf-8")
            (run_dir / "fuzz.log").write_text(
                "==1==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x0\n"
                "SUMMARY: AddressSanitizer: heap-buffer-overflow /tmp/project/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()\n",
                encoding="utf-8",
            )
            (repo_root / "fuzz-artifacts").mkdir(parents=True, exist_ok=True)
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(
                json.dumps(
                    {
                        "outcome": "crash",
                        "artifact_category": "crash",
                        "artifact_reason": "sanitizer-crash",
                        "crash_detected": True,
                        "crash_kind": "asan",
                        "crash_stage": "ht-block-decode",
                        "crash_stage_class": "deep",
                        "crash_stage_depth_rank": 4,
                        "policy_profile_severity": "critical",
                        "target_profile_primary_mode": "deep-decode-v3",
                        "report": str(report_path),
                    }
                ),
                encoding="utf-8",
            )
            (automation_dir / "run_history.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "updated_at": "2026-04-16T20:08:59",
                                "outcome": "crash",
                                "cov": 45,
                                "ft": 137,
                                "exec_per_second": 0,
                                "corpus_units": 5,
                                "corpus_size": "1066b",
                                "seconds_since_progress": 1.0,
                                "timeout_detected": False,
                                "crash_stage": "ht-block-decode",
                                "crash_fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow ...",
                                "policy_profile_severity": "critical",
                                "policy_action_code": "continue_and_prioritize_triage",
                                "policy_matched_triggers": ["deep_signal_emergence"],
                                "run_dir": str(run_dir),
                                "report": str(report_path),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            packet = hermes_watch.build_llm_evidence_packet(repo_root)

            self.assertEqual(packet["llm_objective"], "stage-reach-or-new-signal")
            self.assertEqual(packet["suggested_action_code"], "halt_and_review_harness")
            self.assertEqual(packet["suggested_candidate_route"], "review-current-candidate")
            self.assertIn("deep-stage-crash-already-reached", packet["objective_routing_linkage_summary"])

    def test_queue_latest_evidence_review_followup_records_harness_review_for_review_route(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            automation_dir.mkdir(parents=True)
            evidence_dir = repo_root / "fuzz-records" / "llm-evidence"
            evidence_dir.mkdir(parents=True)
            evidence_path = evidence_dir / "sample-target-llm-evidence.json"
            evidence_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "llm_evidence_json_path": str(evidence_path),
                        "llm_evidence_markdown_path": str(evidence_dir / "sample-target-llm-evidence.md"),
                        "suggested_action_code": "halt_and_review_harness",
                        "suggested_candidate_route": "review-current-candidate",
                        "objective_routing_linkage_summary": "override=deep-stage-crash-already-reached",
                        "top_failure_reason_narrative": "primary deep crash family already reached",
                        "current_status": {
                            "run_dir": "/runs/deep-critical",
                            "report": "/runs/deep-critical/FUZZING_REPORT.md",
                            "outcome": "crash",
                            "crash_fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                            "crash_stage": "ht-block-decode",
                            "crash_stage_class": "deep",
                            "policy_profile_severity": "critical",
                            "policy_action_code": "record-duplicate-crash",
                            "policy_recommended_action": "review deep crash family",
                            "target_profile_primary_mode": "deep-decode-v3",
                        },
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.queue_latest_evidence_review_followup(repo_root)

            self.assertTrue(result["queued"])
            self.assertEqual(result["action_code"], "halt_and_review_harness")
            registry = json.loads((automation_dir / "harness_review_queue.json").read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["action_code"], "halt_and_review_harness")
            self.assertEqual(entry["run_dir"], "/runs/deep-critical")
            self.assertEqual(entry["llm_evidence_json_path"], str(evidence_path))
            self.assertEqual(entry["candidate_route"], "review-current-candidate")
            self.assertIn("deep-stage-crash-already-reached", entry["recommended_action"])

    def test_run_latest_evidence_review_followup_chain_prepares_dispatches_bridges_and_launches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            automation_dir.mkdir(parents=True)
            evidence_dir = repo_root / "fuzz-records" / "llm-evidence"
            evidence_dir.mkdir(parents=True)
            evidence_path = evidence_dir / "sample-target-llm-evidence.json"
            evidence_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "llm_evidence_json_path": str(evidence_path),
                        "llm_evidence_markdown_path": str(evidence_dir / "sample-target-llm-evidence.md"),
                        "suggested_action_code": "halt_and_review_harness",
                        "suggested_candidate_route": "review-current-candidate",
                        "objective_routing_linkage_summary": "override=deep-stage-crash-already-reached",
                        "top_failure_reason_narrative": "primary deep crash family already reached",
                        "current_status": {
                            "run_dir": "/runs/deep-critical",
                            "report": "/runs/deep-critical/FUZZING_REPORT.md",
                            "outcome": "crash",
                            "crash_fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                            "crash_stage": "ht-block-decode",
                            "crash_stage_class": "deep",
                            "policy_profile_severity": "critical",
                            "policy_action_code": "record-duplicate-crash",
                            "policy_recommended_action": "review deep crash family",
                            "target_profile_primary_mode": "deep-decode-v3",
                        },
                    }
                ),
                encoding="utf-8",
            )
            original_launch = hermes_watch.launch_bridge_script
            try:
                hermes_watch.launch_bridge_script = lambda _script_path, **_kwargs: {
                    "exit_code": 0,
                    "output": "Child session: child-123\nDelegate status: success\nArtifact path: /tmp/review-artifact.md\nSummary: review-ready\n",
                }
                result = hermes_watch.run_latest_evidence_review_followup_chain(repo_root)
            finally:
                hermes_watch.launch_bridge_script = original_launch

            self.assertTrue(result["queued"])
            self.assertEqual(result["launch_status"], "succeeded")
            self.assertEqual(result["delegate_session_id"], "child-123")
            registry = json.loads((automation_dir / "harness_review_queue.json").read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["launch_status"], "succeeded")
            self.assertEqual(entry["delegate_session_id"], "child-123")

    def test_run_latest_evidence_review_followup_chain_revives_failed_review_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            automation_dir.mkdir(parents=True)
            evidence_dir = repo_root / "fuzz-records" / "llm-evidence"
            evidence_dir.mkdir(parents=True)
            evidence_path = evidence_dir / "sample-target-llm-evidence.json"
            crash_fp = "asan|j2kmarkers.cpp:52|heap-buffer-overflow"
            evidence_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "llm_evidence_json_path": str(evidence_path),
                        "llm_evidence_markdown_path": str(evidence_dir / "sample-target-llm-evidence.md"),
                        "suggested_action_code": "halt_and_review_harness",
                        "suggested_candidate_route": "review-current-candidate",
                        "objective_routing_linkage_summary": "override=deep-stage-crash-already-reached",
                        "top_failure_reason_narrative": "primary deep crash family already reached",
                        "current_status": {
                            "run_dir": "/runs/deep-critical",
                            "report": "/runs/deep-critical/FUZZING_REPORT.md",
                            "outcome": "crash",
                            "crash_fingerprint": crash_fp,
                            "crash_stage": "ht-block-decode",
                            "crash_stage_class": "deep",
                            "policy_profile_severity": "critical",
                            "policy_action_code": "record-duplicate-crash",
                            "policy_recommended_action": "review deep crash family",
                            "target_profile_primary_mode": "deep-decode-v3",
                        },
                    }
                ),
                encoding="utf-8",
            )
            registry_path = automation_dir / "harness_review_queue.json"
            registry_path.write_text(
                json.dumps(
                    {"entries": [{
                        "key": f"halt_and_review_harness:sample-target:{crash_fp}",
                        "action_code": "halt_and_review_harness",
                        "status": "completed",
                        "run_dir": "/runs/deep-critical",
                        "report_path": "/runs/deep-critical/FUZZING_REPORT.md",
                        "bridge_status": "failed",
                        "launch_status": "failed",
                        "lifecycle": "launch_failed",
                    }]},
                    indent=2,
                ),
                encoding="utf-8",
            )
            original_launch = hermes_watch.launch_bridge_script
            try:
                hermes_watch.launch_bridge_script = lambda _script_path, **_kwargs: {
                    "exit_code": 0,
                    "output": "Child session: child-456\nDelegate status: success\nArtifact path: /tmp/review-artifact-2.md\nSummary: review-ready\n",
                }
                result = hermes_watch.run_latest_evidence_review_followup_chain(repo_root)
            finally:
                hermes_watch.launch_bridge_script = original_launch

            self.assertTrue(result["prepared"])
            self.assertEqual(result["launch_status"], "succeeded")
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["launch_status"], "succeeded")
            self.assertEqual(entry["delegate_session_id"], "child-456")


class HermesWatchLLMEvidencePacketV08Tests(unittest.TestCase):
    def test_build_llm_evidence_packet_v8_adds_multi_reason_narrative_for_build_packet(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            run_dir = repo_root / "fuzz-artifacts" / "runs" / "run-1"
            run_dir.mkdir(parents=True)
            report_path = run_dir / "FUZZING_REPORT.md"
            report_path.write_text("# report\n", encoding="utf-8")
            (run_dir / "build.log").write_text(
                "runtime error: signed integer overflow\nSUMMARY: UndefinedBehaviorSanitizer: undefined-behavior ../src/codec.c:44\n",
                encoding="utf-8",
            )
            (repo_root / "fuzz-artifacts").mkdir(parents=True, exist_ok=True)
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(
                json.dumps(
                    {
                        "outcome": "build-failed",
                        "artifact_reason": "build-or-config-error",
                        "crash_detected": False,
                        "report": str(report_path),
                    }
                ),
                encoding="utf-8",
            )

            packet = hermes_watch.build_llm_evidence_packet(repo_root)

            self.assertIn("top_failure_reason_narrative", packet)
            self.assertIn("top_failure_reason_narrative_steps", packet)
            self.assertEqual(packet["top_failure_reason_narrative_steps"][0]["role"], "primary")
            self.assertEqual(packet["top_failure_reason_narrative_steps"][0]["code"], "build-blocker")
            self.assertEqual(packet["top_failure_reason_narrative_steps"][1]["role"], "supporting")
            self.assertEqual(packet["top_failure_reason_narrative_steps"][1]["code"], "build-log-memory-safety-signal")
            self.assertIn("primary build-blocker", packet["top_failure_reason_narrative"])
            self.assertIn("supporting build-log-memory-safety-signal", packet["top_failure_reason_narrative"])

    def test_render_llm_evidence_markdown_v8_includes_multi_reason_narrative(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            run_dir = repo_root / "fuzz-artifacts" / "runs" / "run-1"
            run_dir.mkdir(parents=True)
            report_path = run_dir / "FUZZING_REPORT.md"
            report_path.write_text("# report\n", encoding="utf-8")
            (repo_root / "fuzz-artifacts").mkdir(parents=True, exist_ok=True)
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(
                json.dumps(
                    {
                        "outcome": "no-progress",
                        "artifact_reason": "stalled-coverage-or-corpus",
                        "crash_detected": False,
                        "target_profile_primary_mode": "deeper",
                        "seconds_since_progress": 7200,
                        "report": str(report_path),
                    }
                ),
                encoding="utf-8",
            )
            (repo_root / "fuzz-artifacts" / "run_history.json").write_text(
                json.dumps(
                    [
                        {"updated_at": "2026-04-16T00:00:00", "outcome": "no-progress", "cov": 10.0, "exec_per_second": 300, "corpus_units": 100},
                        {"updated_at": "2026-04-16T01:00:00", "outcome": "no-progress", "cov": 10.0, "exec_per_second": 320, "corpus_units": 130},
                        {"updated_at": "2026-04-16T02:00:00", "outcome": "no-progress", "cov": 10.0, "exec_per_second": 310, "corpus_units": 170},
                        {"updated_at": "2026-04-16T03:00:00", "outcome": "no-progress", "cov": 10.0, "exec_per_second": 305, "corpus_units": 230},
                    ]
                ),
                encoding="utf-8",
            )

            packet = hermes_watch.build_llm_evidence_packet(repo_root)
            write_result = hermes_watch.write_llm_evidence_packet(repo_root)
            markdown = Path(write_result["llm_evidence_markdown_path"]).read_text(encoding="utf-8")

            self.assertEqual(packet["top_failure_reason_narrative_steps"][0]["code"], "stage-reach-blocked")
            self.assertIn("supporting no-progress-stall", packet["top_failure_reason_narrative"])
            self.assertIn("deferred no-crash-yet", packet["top_failure_reason_narrative"])
            self.assertIn("- top_failure_reason_narrative:", markdown)
            self.assertIn("stage-reach-blocked", markdown)


class HermesWatchHarnessProbeFeedbackTests(unittest.TestCase):
    def test_bridge_harness_probe_feedback_records_harness_review_for_failed_smoke(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            probe_dir = repo_root / "fuzz-records" / "harness-probes"
            automation_dir.mkdir(parents=True)
            probe_dir.mkdir(parents=True)
            manifest_path = probe_dir / "sample-target-harness-probe.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "probe_candidate": {"candidate_id": "candidate-1", "entrypoint_path": "src/parse_input.c"},
                        "seed_candidates": [str(repo_root / "seeds" / "valid.bin")],
                        "build_probe_result": {"status": "passed", "command": ["make", "-n"], "exit_code": 0, "output": "ok"},
                        "smoke_probe_result": {"status": "failed", "command": ["scripts/run-smoke.sh"], "exit_code": 1, "output": "boom"},
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.bridge_harness_probe_feedback(repo_root)

            self.assertEqual(result["action_code"], "halt_and_review_harness")
            self.assertIn("harness_reviews", result["updated"])
            registry = json.loads((automation_dir / "harness_review_queue.json").read_text(encoding="utf-8"))
            self.assertEqual(registry["entries"][0]["action_code"], "halt_and_review_harness")
            self.assertTrue(Path(result["feedback_plan_path"]).exists())

    def test_bridge_harness_probe_feedback_records_mode_refinement_for_passed_probe(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            probe_dir = repo_root / "fuzz-records" / "harness-probes"
            automation_dir.mkdir(parents=True)
            probe_dir.mkdir(parents=True)
            manifest_path = probe_dir / "sample-target-harness-probe.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "probe_candidate": {"candidate_id": "candidate-1", "entrypoint_path": "src/parse_input.c"},
                        "seed_candidates": [str(repo_root / "seeds" / "valid.bin")],
                        "build_probe_result": {"status": "passed", "command": ["make", "-n"], "exit_code": 0, "output": "ok"},
                        "smoke_probe_result": {"status": "passed", "command": ["scripts/run-smoke.sh"], "exit_code": 0, "output": "ok"},
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.bridge_harness_probe_feedback(repo_root)

            self.assertEqual(result["action_code"], "shift_weight_to_deeper_harness")
            self.assertIn("mode_refinements", result["updated"])
            registry = json.loads((automation_dir / "mode_refinements.json").read_text(encoding="utf-8"))
            self.assertEqual(registry["entries"][0]["action_code"], "shift_weight_to_deeper_harness")

    def test_main_bridge_harness_probe_feedback_emits_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            (repo_root / "meson.build").write_text("project('sample-target', 'c')\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")

            original_argv = list(hermes_watch.sys.argv)
            original_run_quiet = hermes_watch.run_quiet
            try:
                hermes_watch.run_quiet = lambda command, cwd: (0, "ok\n")
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--run-short-harness-probe"]
                probe_exit = hermes_watch.main()
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--bridge-harness-probe-feedback"]
                bridge_exit = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv
                hermes_watch.run_quiet = original_run_quiet

            self.assertEqual(probe_exit, 0)
            self.assertEqual(bridge_exit, 0)
            feedback_dir = repo_root / "fuzz-records" / "probe-feedback"
            self.assertTrue(any(feedback_dir.glob("*-probe-feedback.md")))


class HermesWatchHarnessRoutingTests(unittest.TestCase):
    def test_route_harness_probe_feedback_prepares_and_dispatches_mode_refinement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            feedback_dir = repo_root / "fuzz-records" / "probe-feedback"
            automation_dir.mkdir(parents=True)
            feedback_dir.mkdir(parents=True)
            feedback_path = feedback_dir / "sample-target-probe-feedback.json"
            feedback_path.write_text(
                json.dumps(
                    {
                        "bridged": True,
                        "generated_from_project": "sample-target",
                        "action_code": "shift_weight_to_deeper_harness",
                        "bridge_reason": "probe-passed",
                        "candidate_id": "candidate-1",
                        "entrypoint_path": "src/parse_input.c",
                        "registry_name": "mode_refinements.json",
                        "updated": ["mode_refinements"],
                    }
                ),
                encoding="utf-8",
            )
            (automation_dir / "mode_refinements.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "shift_weight_to_deeper_harness:/tmp/probe-plan.md",
                                "action_code": "shift_weight_to_deeper_harness",
                                "run_dir": "/tmp/probe-plan.md",
                                "report_path": "/tmp/probe-plan.md",
                                "outcome": "probe-probe-passed",
                                "recommended_action": "Shift weight toward deeper harness candidates or the next execution depth.",
                                "status": "recorded",
                                "lifecycle": "queued",
                                "candidate_id": "candidate-1",
                                "entrypoint_path": "src/parse_input.c",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.route_harness_probe_feedback(repo_root)

            self.assertEqual(result["candidate_route"], "promote-next-depth")
            self.assertEqual(result["action_code"], "shift_weight_to_deeper_harness")
            self.assertEqual(result["dispatch_channel"], "subagent")
            self.assertTrue(Path(result["handoff_manifest_path"]).exists())
            self.assertTrue(Path(result["handoff_plan_path"]).exists())
            registry = json.loads((automation_dir / "mode_refinements.json").read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["dispatch_status"], "ready")
            self.assertEqual(entry["orchestration_status"], "prepared")

    def test_route_harness_probe_feedback_prepares_and_dispatches_review_handoff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            feedback_dir = repo_root / "fuzz-records" / "probe-feedback"
            automation_dir.mkdir(parents=True)
            feedback_dir.mkdir(parents=True)
            feedback_path = feedback_dir / "sample-target-probe-feedback.json"
            feedback_path.write_text(
                json.dumps(
                    {
                        "bridged": True,
                        "generated_from_project": "sample-target",
                        "action_code": "halt_and_review_harness",
                        "bridge_reason": "smoke-probe-failed",
                        "candidate_id": "candidate-1",
                        "entrypoint_path": "src/parse_input.c",
                        "registry_name": "harness_review_queue.json",
                        "updated": ["harness_reviews"],
                    }
                ),
                encoding="utf-8",
            )
            (automation_dir / "harness_review_queue.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "halt_and_review_harness:/tmp/probe-plan.md",
                                "action_code": "halt_and_review_harness",
                                "run_dir": "/tmp/probe-plan.md",
                                "report_path": "/tmp/probe-plan.md",
                                "outcome": "probe-smoke-probe-failed",
                                "recommended_action": "Smoke probe failed; halt and review harness assumptions.",
                                "status": "recorded",
                                "lifecycle": "queued",
                                "candidate_id": "candidate-1",
                                "entrypoint_path": "src/parse_input.c",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.route_harness_probe_feedback(repo_root)

            self.assertEqual(result["candidate_route"], "review-current-candidate")
            self.assertEqual(result["action_code"], "halt_and_review_harness")
            self.assertEqual(result["dispatch_channel"], "subagent")
            registry = json.loads((automation_dir / "harness_review_queue.json").read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["dispatch_status"], "ready")
            self.assertEqual(entry["orchestration_status"], "prepared")

    def test_main_route_harness_probe_feedback_emits_handoff_artifact(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            (repo_root / "meson.build").write_text("project('sample-target', 'c')\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")

            original_argv = list(hermes_watch.sys.argv)
            original_run_quiet = hermes_watch.run_quiet
            try:
                hermes_watch.run_quiet = lambda command, cwd: (0, "ok\n")
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--run-short-harness-probe"]
                probe_exit = hermes_watch.main()
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--bridge-harness-probe-feedback"]
                bridge_exit = hermes_watch.main()
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--route-harness-probe-feedback"]
                route_exit = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv
                hermes_watch.run_quiet = original_run_quiet

            self.assertEqual(probe_exit, 0)
            self.assertEqual(bridge_exit, 0)
            self.assertEqual(route_exit, 0)
            handoff_dir = repo_root / "fuzz-records" / "probe-routing"
            self.assertTrue(any(handoff_dir.glob("*-probe-routing.md")))


class HermesWatchHarnessCandidateRegistryTests(unittest.TestCase):
    def test_update_ranked_candidate_registry_promotes_passed_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            registry_dir = repo_root / "fuzz-records" / "harness-candidates"
            feedback_dir = repo_root / "fuzz-records" / "probe-feedback"
            registry_dir.mkdir(parents=True)
            feedback_dir.mkdir(parents=True)
            (registry_dir / "ranked-candidates.json").write_text(
                json.dumps(
                    {
                        "project": "sample-target",
                        "candidates": [
                            {"candidate_id": "candidate-1", "entrypoint_path": "src/parse_input.c", "score": 10, "status": "active", "rank": 2},
                            {"candidate_id": "candidate-2", "entrypoint_path": "src/decode_input.c", "score": 8, "status": "active", "rank": 1},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (feedback_dir / "sample-target-probe-feedback.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "action_code": "shift_weight_to_deeper_harness",
                        "bridge_reason": "probe-passed",
                        "candidate_id": "candidate-1",
                        "entrypoint_path": "src/parse_input.c",
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.update_ranked_candidate_registry(repo_root)

            self.assertTrue(result["updated"])
            self.assertEqual(result["selected_candidate_id"], "candidate-1")
            registry = json.loads((registry_dir / "ranked-candidates.json").read_text(encoding="utf-8"))
            self.assertEqual(registry["candidates"][0]["candidate_id"], "candidate-1")
            self.assertEqual(registry["candidates"][0]["status"], "promoted")
            self.assertTrue(Path(result["registry_plan_path"]).exists())

    def test_update_ranked_candidate_registry_demotes_failed_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            registry_dir = repo_root / "fuzz-records" / "harness-candidates"
            feedback_dir = repo_root / "fuzz-records" / "probe-feedback"
            registry_dir.mkdir(parents=True)
            feedback_dir.mkdir(parents=True)
            (registry_dir / "ranked-candidates.json").write_text(
                json.dumps(
                    {
                        "project": "sample-target",
                        "candidates": [
                            {"candidate_id": "candidate-1", "entrypoint_path": "src/parse_input.c", "score": 20, "status": "active", "rank": 1},
                            {"candidate_id": "candidate-2", "entrypoint_path": "src/decode_input.c", "score": 12, "status": "active", "rank": 2},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (feedback_dir / "sample-target-probe-feedback.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "action_code": "halt_and_review_harness",
                        "bridge_reason": "smoke-probe-failed",
                        "candidate_id": "candidate-1",
                        "entrypoint_path": "src/parse_input.c",
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.update_ranked_candidate_registry(repo_root)

            self.assertTrue(result["updated"])
            registry = json.loads((registry_dir / "ranked-candidates.json").read_text(encoding="utf-8"))
            demoted = next(item for item in registry["candidates"] if item["candidate_id"] == "candidate-1")
            self.assertEqual(demoted["status"], "review_required")
            self.assertGreater(next(item for item in registry["candidates"] if item["candidate_id"] == "candidate-2")["score"], demoted["score"])

    def test_update_ranked_candidate_registry_tracks_smoke_debt_and_fail_streak(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            registry_dir = repo_root / "fuzz-records" / "harness-candidates"
            feedback_dir = repo_root / "fuzz-records" / "probe-feedback"
            registry_dir.mkdir(parents=True)
            feedback_dir.mkdir(parents=True)
            (registry_dir / "ranked-candidates.json").write_text(
                json.dumps(
                    {
                        "project": "sample-target",
                        "candidates": [
                            {"candidate_id": "candidate-1", "entrypoint_path": "src/parse_input.c", "score": 50, "status": "active", "rank": 1, "pass_streak": 2},
                            {"candidate_id": "candidate-2", "entrypoint_path": "src/decode_input.c", "score": 47, "status": "active", "rank": 2},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (feedback_dir / "sample-target-probe-feedback.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "action_code": "halt_and_review_harness",
                        "bridge_reason": "smoke-probe-failed",
                        "candidate_id": "candidate-1",
                        "entrypoint_path": "src/parse_input.c",
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.update_ranked_candidate_registry(repo_root)

            self.assertTrue(result["updated"])
            registry = json.loads((registry_dir / "ranked-candidates.json").read_text(encoding="utf-8"))
            candidate = next(item for item in registry["candidates"] if item["candidate_id"] == "candidate-1")
            self.assertEqual(candidate["smoke_debt_count"], 1)
            self.assertEqual(candidate["fail_streak"], 1)
            self.assertEqual(candidate["pass_streak"], 0)
            self.assertGreater(candidate["debt_penalty"], 0)

    def test_update_ranked_candidate_registry_bootstraps_viability_weighted_score(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            draft_dir = repo_root / "fuzz-records" / "harness-drafts"
            feedback_dir = repo_root / "fuzz-records" / "probe-feedback"
            draft_dir.mkdir(parents=True)
            feedback_dir.mkdir(parents=True)
            (draft_dir / "sample-target-harness-draft.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "candidates": [
                            {"candidate_id": "candidate-1", "entrypoint_path": "src/parse_input.c", "recommended_mode": "parse", "target_stage": "parse-main", "viability_score": 18, "build_viability": "high", "smoke_viability": "high", "callable_signal": "likely-callable"},
                            {"candidate_id": "candidate-2", "entrypoint_path": "src/decode_input.c", "recommended_mode": "decode", "target_stage": "decode", "viability_score": 4, "build_viability": "medium", "smoke_viability": "low", "callable_signal": "uncertain"}
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.update_ranked_candidate_registry(repo_root)

            self.assertTrue(result["updated"])
            registry = json.loads((repo_root / "fuzz-records" / "harness-candidates" / "ranked-candidates.json").read_text(encoding="utf-8"))
            top = registry["candidates"][0]
            self.assertEqual(top["candidate_id"], "candidate-1")
            self.assertEqual(top["viability_score"], 18)
            self.assertGreater(top["effective_score"], next(item for item in registry["candidates"] if item["candidate_id"] == "candidate-2")["effective_score"])

    def test_update_ranked_candidate_registry_adds_execution_evidence_score_from_probe_feedback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            registry_dir = repo_root / "fuzz-records" / "harness-candidates"
            feedback_dir = repo_root / "fuzz-records" / "probe-feedback"
            registry_dir.mkdir(parents=True)
            feedback_dir.mkdir(parents=True)
            (registry_dir / "ranked-candidates.json").write_text(
                json.dumps(
                    {
                        "project": "sample-target",
                        "candidates": [
                            {"candidate_id": "candidate-1", "entrypoint_path": "src/parse_input.c", "score": 40, "status": "active", "rank": 1}
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (feedback_dir / "sample-target-probe-feedback.json").write_text(
                json.dumps(
                    {
                        "generated_from_project": "sample-target",
                        "action_code": "shift_weight_to_deeper_harness",
                        "bridge_reason": "probe-passed",
                        "candidate_id": "candidate-1",
                        "entrypoint_path": "src/parse_input.c",
                        "build_probe_status": "passed",
                        "smoke_probe_status": "passed"
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.update_ranked_candidate_registry(repo_root)

            self.assertTrue(result["updated"])
            registry = json.loads((registry_dir / "ranked-candidates.json").read_text(encoding="utf-8"))
            candidate = registry["candidates"][0]
            self.assertGreater(candidate["execution_evidence_score"], 0)
            self.assertEqual(candidate["probe_pass_count"], 1)
            self.assertEqual(candidate["build_pass_count"], 1)
            self.assertEqual(candidate["smoke_pass_count"], 1)

    def test_main_update_ranked_candidate_registry_emits_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            (repo_root / "meson.build").write_text("project('sample-target', 'c')\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")

            original_argv = list(hermes_watch.sys.argv)
            original_run_quiet = hermes_watch.run_quiet
            try:
                hermes_watch.run_quiet = lambda command, cwd: (0, "ok\n")
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--run-short-harness-probe"]
                probe_exit = hermes_watch.main()
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--bridge-harness-probe-feedback"]
                bridge_exit = hermes_watch.main()
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--update-ranked-candidate-registry"]
                registry_exit = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv
                hermes_watch.run_quiet = original_run_quiet

            self.assertEqual(probe_exit, 0)
            self.assertEqual(bridge_exit, 0)
            self.assertEqual(registry_exit, 0)
            registry_dir = repo_root / "fuzz-records" / "harness-candidates"
            self.assertTrue(any(registry_dir.glob("ranked-candidates.md")))


class HermesWatchHarnessSelectionTests(unittest.TestCase):
    def test_route_harness_probe_feedback_uses_ranked_registry_top_candidate_for_next_handoff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            feedback_dir = repo_root / "fuzz-records" / "probe-feedback"
            registry_dir = repo_root / "fuzz-records" / "harness-candidates"
            automation_dir.mkdir(parents=True)
            feedback_dir.mkdir(parents=True)
            registry_dir.mkdir(parents=True)
            (feedback_dir / "sample-target-probe-feedback.json").write_text(
                json.dumps(
                    {
                        "bridged": True,
                        "generated_from_project": "sample-target",
                        "action_code": "shift_weight_to_deeper_harness",
                        "bridge_reason": "probe-passed",
                        "candidate_id": "candidate-1",
                        "entrypoint_path": "src/parse_input.c",
                        "registry_name": "mode_refinements.json",
                    }
                ),
                encoding="utf-8",
            )
            (registry_dir / "ranked-candidates.json").write_text(
                json.dumps(
                    {
                        "project": "sample-target",
                        "selected_candidate_id": "candidate-2",
                        "candidates": [
                            {"candidate_id": "candidate-2", "entrypoint_path": "src/decode_input.c", "score": 120, "status": "promoted", "rank": 1, "recommended_mode": "decode", "target_stage": "decode"},
                            {"candidate_id": "candidate-1", "entrypoint_path": "src/parse_input.c", "score": 90, "status": "active", "rank": 2, "recommended_mode": "parse", "target_stage": "parse-main"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (automation_dir / "mode_refinements.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "shift_weight_to_deeper_harness:/tmp/probe-plan.md",
                                "action_code": "shift_weight_to_deeper_harness",
                                "run_dir": "/tmp/probe-plan.md",
                                "report_path": "/tmp/probe-plan.md",
                                "outcome": "probe-probe-passed",
                                "recommended_action": "Shift weight toward deeper harness candidates or the next execution depth.",
                                "status": "recorded",
                                "lifecycle": "queued",
                                "candidate_id": "candidate-1",
                                "entrypoint_path": "src/parse_input.c"
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.route_harness_probe_feedback(repo_root)

            self.assertEqual(result["selected_candidate_id"], "candidate-2")
            self.assertEqual(result["selected_entrypoint_path"], "src/decode_input.c")
            registry = json.loads((automation_dir / "mode_refinements.json").read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["selected_candidate_id"], "candidate-2")
            self.assertEqual(entry["selected_entrypoint_path"], "src/decode_input.c")

    def test_select_next_ranked_candidate_keeps_review_route_on_current_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            feedback_dir = repo_root / "fuzz-records" / "probe-feedback"
            registry_dir = repo_root / "fuzz-records" / "harness-candidates"
            feedback_dir.mkdir(parents=True)
            registry_dir.mkdir(parents=True)
            (feedback_dir / "sample-target-probe-feedback.json").write_text(
                json.dumps(
                    {
                        "bridged": True,
                        "generated_from_project": "sample-target",
                        "action_code": "halt_and_review_harness",
                        "bridge_reason": "smoke-probe-failed",
                        "candidate_id": "candidate-1",
                        "entrypoint_path": "src/parse_input.c",
                        "registry_name": "harness_review_queue.json",
                    }
                ),
                encoding="utf-8",
            )
            (registry_dir / "ranked-candidates.json").write_text(
                json.dumps(
                    {
                        "project": "sample-target",
                        "selected_candidate_id": "candidate-2",
                        "candidates": [
                            {"candidate_id": "candidate-2", "entrypoint_path": "src/decode_input.c", "score": 120, "status": "promoted", "rank": 1},
                            {"candidate_id": "candidate-1", "entrypoint_path": "src/parse_input.c", "score": 90, "status": "review_required", "rank": 2},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.select_next_ranked_candidate(repo_root)

            self.assertEqual(result["candidate_route"], "review-current-candidate")
            self.assertEqual(result["selected_candidate_id"], "candidate-1")
            self.assertEqual(result["selected_entrypoint_path"], "src/parse_input.c")

    def test_select_next_ranked_candidate_prefers_lower_debt_weighted_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            feedback_dir = repo_root / "fuzz-records" / "probe-feedback"
            registry_dir = repo_root / "fuzz-records" / "harness-candidates"
            feedback_dir.mkdir(parents=True)
            registry_dir.mkdir(parents=True)
            (feedback_dir / "sample-target-probe-feedback.json").write_text(
                json.dumps(
                    {
                        "bridged": True,
                        "generated_from_project": "sample-target",
                        "action_code": "shift_weight_to_deeper_harness",
                        "bridge_reason": "probe-passed",
                        "candidate_id": "candidate-1",
                        "entrypoint_path": "src/parse_input.c",
                        "registry_name": "mode_refinements.json",
                    }
                ),
                encoding="utf-8",
            )
            (registry_dir / "ranked-candidates.json").write_text(
                json.dumps(
                    {
                        "project": "sample-target",
                        "candidates": [
                            {
                                "candidate_id": "candidate-1",
                                "entrypoint_path": "src/parse_input.c",
                                "score": 100,
                                "status": "seed_debt",
                                "rank": 1,
                                "recommended_mode": "parse",
                                "target_stage": "parse-main",
                                "seed_debt_count": 4,
                                "verification_retry_debt": 2,
                                "smoke_debt_count": 1,
                            },
                            {
                                "candidate_id": "candidate-2",
                                "entrypoint_path": "src/decode_input.c",
                                "score": 94,
                                "status": "active",
                                "rank": 2,
                                "recommended_mode": "decode",
                                "target_stage": "decode",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.select_next_ranked_candidate(repo_root)

            self.assertEqual(result["selected_candidate_id"], "candidate-2")
            self.assertEqual(result["selected_entrypoint_path"], "src/decode_input.c")
            self.assertGreater(result["selected_effective_score"], result["skipped_candidate_effective_score"])

    def test_main_route_harness_probe_feedback_reports_selected_candidate_from_registry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "seeds").mkdir(parents=True)
            (repo_root / "meson.build").write_text("project('sample-target', 'c')\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.c").write_text("int parse_input() { return 0; }\n", encoding="utf-8")
            (repo_root / "scripts" / "run-smoke.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (repo_root / "seeds" / "valid.bin").write_bytes(b"seed")

            original_argv = list(hermes_watch.sys.argv)
            original_run_quiet = hermes_watch.run_quiet
            try:
                hermes_watch.run_quiet = lambda command, cwd: (0, "ok\n")
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--run-short-harness-probe"]
                probe_exit = hermes_watch.main()
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--bridge-harness-probe-feedback"]
                bridge_exit = hermes_watch.main()
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--update-ranked-candidate-registry"]
                registry_exit = hermes_watch.main()
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--route-harness-probe-feedback"]
                route_exit = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv
                hermes_watch.run_quiet = original_run_quiet

            self.assertEqual(probe_exit, 0)
            self.assertEqual(bridge_exit, 0)
            self.assertEqual(registry_exit, 0)
            self.assertEqual(route_exit, 0)
            handoff = json.loads((repo_root / "fuzz-records" / "probe-routing" / "sample-target-probe-routing.json").read_text(encoding="utf-8"))
            self.assertEqual(handoff["selected_candidate_id"], "candidate-1")


class HermesWatchNotificationHardeningTests(unittest.TestCase):
    def test_send_discord_best_effort_returns_failure_metadata_instead_of_raising(self):
        original_send_discord = hermes_watch.send_discord

        def fake_send_discord(message):
            raise RuntimeError("webhook offline")

        hermes_watch.send_discord = fake_send_discord
        try:
            result = hermes_watch.send_discord_best_effort("hello", context="progress")
        finally:
            hermes_watch.send_discord = original_send_discord

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "exception")
        self.assertEqual(result["error_type"], "RuntimeError")
        self.assertEqual(result["context"], "progress")

    def test_main_build_failure_treats_notification_error_as_non_critical(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            automation_dir.mkdir(parents=True)

            original_argv = list(hermes_watch.sys.argv)
            original_run_quiet = hermes_watch.run_quiet
            original_send_discord = hermes_watch.send_discord
            original_apply_policy_action = hermes_watch.apply_policy_action
            original_resolve_target_profile_path = hermes_watch.resolve_target_profile_path
            original_load_target_profile = hermes_watch.load_target_profile
            original_build_target_profile_summary = hermes_watch.build_target_profile_summary

            def fake_run_quiet(cmd, cwd):
                if cmd[:3] == ["git", "rev-parse", "--short"]:
                    return 0, "abc123\n"
                if cmd == ["bash", "scripts/build-libfuzzer.sh"]:
                    return 7, "BUILD BROKEN\n"
                if cmd == ["git", "branch", "--show-current"]:
                    return 0, "main\n"
                if cmd == ["git", "rev-parse", "HEAD"]:
                    return 0, "deadbeef\n"
                if cmd == ["git", "status", "--short"]:
                    return 0, ""
                raise AssertionError(f"unexpected command: {cmd}")

            def fake_send_discord(message):
                raise RuntimeError("discord down")

            hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--skip-smoke"]
            hermes_watch.run_quiet = fake_run_quiet
            hermes_watch.send_discord = fake_send_discord
            hermes_watch.apply_policy_action = lambda *args, **kwargs: {"updated": False, "regression_trigger": None}
            hermes_watch.resolve_target_profile_path = lambda repo, explicit: None
            hermes_watch.load_target_profile = lambda path: None
            hermes_watch.build_target_profile_summary = lambda profile, path: None
            try:
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv
                hermes_watch.run_quiet = original_run_quiet
                hermes_watch.send_discord = original_send_discord
                hermes_watch.apply_policy_action = original_apply_policy_action
                hermes_watch.resolve_target_profile_path = original_resolve_target_profile_path
                hermes_watch.load_target_profile = original_load_target_profile
                hermes_watch.build_target_profile_summary = original_build_target_profile_summary

            self.assertEqual(exit_code, 7)
            status = json.loads((repo_root / "fuzz-artifacts" / "current_status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["outcome"], "build-failed")
            self.assertEqual(status["notification_status"], "failed")
            self.assertEqual(status["notification_error_type"], "RuntimeError")
            report_text = next((repo_root / "fuzz-artifacts" / "runs").glob("*/FUZZING_REPORT.md")).read_text(encoding="utf-8")
            self.assertIn("notification_status: failed", report_text)
            self.assertIn("notification_context: build-failed", report_text)

    def test_main_build_failure_treats_malformed_target_profile_as_non_critical(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            automation_dir.mkdir(parents=True)
            profile_path = repo_root / "broken-profile.yaml"
            profile_path.write_text("meta: [unterminated\n", encoding="utf-8")

            original_argv = list(hermes_watch.sys.argv)
            original_run_quiet = hermes_watch.run_quiet
            original_send_discord = hermes_watch.send_discord
            original_apply_policy_action = hermes_watch.apply_policy_action

            def fake_run_quiet(cmd, cwd):
                if cmd[:3] == ["git", "rev-parse", "--short"]:
                    return 0, "abc123\n"
                if cmd == ["bash", "scripts/build-libfuzzer.sh"]:
                    return 7, "BUILD BROKEN\n"
                if cmd == ["git", "branch", "--show-current"]:
                    return 0, "main\n"
                if cmd == ["git", "rev-parse", "HEAD"]:
                    return 0, "deadbeef\n"
                if cmd == ["git", "status", "--short"]:
                    return 0, ""
                raise AssertionError(f"unexpected command: {cmd}")

            hermes_watch.sys.argv = [
                "hermes_watch.py",
                "--repo",
                str(repo_root),
                "--target-profile",
                str(profile_path),
                "--skip-smoke",
            ]
            hermes_watch.run_quiet = fake_run_quiet
            hermes_watch.send_discord = lambda message: {"status": "sent", "transport": "webhook"}
            hermes_watch.apply_policy_action = lambda *args, **kwargs: {"updated": False, "regression_trigger": None}
            try:
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv
                hermes_watch.run_quiet = original_run_quiet
                hermes_watch.send_discord = original_send_discord
                hermes_watch.apply_policy_action = original_apply_policy_action

            self.assertEqual(exit_code, 7)
            status = json.loads((repo_root / "fuzz-artifacts" / "current_status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["outcome"], "build-failed")
            self.assertEqual(status["target_profile_load_status"], "degraded")
            self.assertEqual(status["target_profile_load_error"], "yaml-parse-error")
            self.assertEqual(status["target_profile_validation_status"], "fatal")
            self.assertEqual(status["target_profile_validation_severity"], "fatal")
            report_text = next((repo_root / "fuzz-artifacts" / "runs").glob("*/FUZZING_REPORT.md")).read_text(encoding="utf-8")
            self.assertIn("target_profile_load_status: degraded", report_text)
            self.assertIn("target_profile_load_error: yaml-parse-error", report_text)
            self.assertIn("target_profile_validation_status: fatal", report_text)

    def test_main_build_failure_records_warning_validation_for_partial_profile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            automation_dir.mkdir(parents=True)
            profile_path = repo_root / "warning-profile.yaml"
            profile_path.write_text(
                "\n".join(
                    [
                        "meta:",
                        "  name: warning-profile",
                        "target:",
                        "  current_campaign:",
                        "    primary_mode: deep-decode-v3",
                        "stages:",
                        "  - id: parse-main-header",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            original_argv = list(hermes_watch.sys.argv)
            original_run_quiet = hermes_watch.run_quiet
            original_send_discord = hermes_watch.send_discord
            original_apply_policy_action = hermes_watch.apply_policy_action

            def fake_run_quiet(cmd, cwd):
                if cmd[:3] == ["git", "rev-parse", "--short"]:
                    return 0, "abc123\n"
                if cmd == ["bash", "scripts/build-libfuzzer.sh"]:
                    return 7, "BUILD BROKEN\n"
                if cmd == ["git", "branch", "--show-current"]:
                    return 0, "main\n"
                if cmd == ["git", "rev-parse", "HEAD"]:
                    return 0, "deadbeef\n"
                if cmd == ["git", "status", "--short"]:
                    return 0, ""
                raise AssertionError(f"unexpected command: {cmd}")

            hermes_watch.sys.argv = [
                "hermes_watch.py",
                "--repo",
                str(repo_root),
                "--target-profile",
                str(profile_path),
                "--skip-smoke",
            ]
            hermes_watch.run_quiet = fake_run_quiet
            hermes_watch.send_discord = lambda message: {"status": "sent", "transport": "webhook"}
            hermes_watch.apply_policy_action = lambda *args, **kwargs: {"updated": False, "regression_trigger": None}
            try:
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv
                hermes_watch.run_quiet = original_run_quiet
                hermes_watch.send_discord = original_send_discord
                hermes_watch.apply_policy_action = original_apply_policy_action

            self.assertEqual(exit_code, 7)
            status = json.loads((repo_root / "fuzz-artifacts" / "current_status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["target_profile_load_status"], "loaded")
            self.assertEqual(status["target_profile_validation_status"], "warning")
            self.assertEqual(status["target_profile_validation_severity"], "warning")
            self.assertIn("missing-schema-version", status["target_profile_validation_codes"])


class HermesWatchStageTaggingTests(unittest.TestCase):
    def make_profile(self):
        return {
            "stages": [
                {"id": "parse-main-header", "depth_rank": 1, "stage_class": "shallow", "expected_signals": ["j2k_main_header::read"]},
                {"id": "tile-part-load", "depth_rank": 2, "stage_class": "medium", "expected_signals": ["j2k_tile::add_tile_part"]},
                {"id": "line-based-decode", "depth_rank": 3, "stage_class": "deep", "expected_signals": ["j2k_tile::decode_line_based", "j2k_resolution::create_subbands"]},
                {"id": "ht-block-decode", "depth_rank": 4, "stage_class": "deep", "expected_signals": ["htj2k_decode"]},
            ],
            "hotspots": {
                "functions": [
                    {"name": "j2k_tile::add_tile_part", "stage": "tile-part-load"},
                    {"name": "j2k_tile::decode_line_based", "stage": "line-based-decode"},
                    {"name": "j2k_resolution::create_subbands", "stage": "line-based-decode"},
                    {"name": "htj2k_decode", "stage": "ht-block-decode"},
                ]
            },
            "telemetry": {
                "stack_tagging": {
                    "enabled": True,
                    "file_to_stage_map": True,
                    "stage_file_map": {
                        "parse-main-header": ["source/core/codestream/j2kmarkers.cpp"],
                        "tile-part-load": ["source/core/coding/coding_units.cpp"],
                        "line-based-decode": ["source/core/coding/line_decode.cpp"],
                        "ht-block-decode": ["source/core/transform/ht_block_decoding.cpp"],
                    },
                }
            },
        }

    def test_extract_stack_frames_parses_function_and_path(self):
        lines = [
            "#0 0x1234 in htj2k_decode /tmp/project/source/core/transform/ht_block_decoding.cpp:1126:7",
            "#1 0x1235 in j2k_tile::decode_line_based /tmp/project/source/core/coding/line_decode.cpp:4661:3",
        ]

        frames = hermes_watch.extract_stack_frames(lines)

        self.assertEqual(frames[0]["function"], "htj2k_decode")
        self.assertTrue(frames[0]["path"].endswith("source/core/transform/ht_block_decoding.cpp"))
        self.assertEqual(frames[0]["line"], 1126)
        self.assertEqual(frames[1]["function"], "j2k_tile::decode_line_based")

    def test_classify_crash_stage_prefers_function_signal_over_file_signal(self):
        profile = self.make_profile()
        lines = [
            "#0 0x1234 in j2k_tile::decode_line_based /tmp/project/source/core/coding/line_decode.cpp:4661:3",
            "#1 0x1235 in helper /tmp/project/source/core/coding/coding_units.cpp:3076:9",
            "SUMMARY: AddressSanitizer: SEGV /tmp/project/source/core/coding/line_decode.cpp:4661:3",
        ]

        stage_info = hermes_watch.classify_crash_stage(lines, profile)

        self.assertEqual(stage_info["stage"], "line-based-decode")
        self.assertEqual(stage_info["stage_class"], "deep")
        self.assertEqual(stage_info["depth_rank"], 3)
        self.assertEqual(stage_info["confidence"], "high")
        self.assertEqual(stage_info["match_source"], "function")

    def test_classify_crash_stage_uses_file_map_fallback(self):
        profile = self.make_profile()
        lines = [
            "#0 0x1234 in some_helper /tmp/project/source/core/transform/ht_block_decoding.cpp:1126:7",
            "SUMMARY: AddressSanitizer: stack-buffer-overflow /tmp/project/source/core/transform/ht_block_decoding.cpp:1126:7",
        ]

        stage_info = hermes_watch.classify_crash_stage(lines, profile)

        self.assertEqual(stage_info["stage"], "ht-block-decode")
        self.assertEqual(stage_info["stage_class"], "deep")
        self.assertEqual(stage_info["confidence"], "medium")
        self.assertEqual(stage_info["match_source"], "file")

    def test_classify_crash_stage_returns_unknown_when_no_profile_match(self):
        profile = self.make_profile()
        lines = [
            "#0 0x1234 in some_helper /tmp/project/source/other/random.cpp:10:2",
            "SUMMARY: AddressSanitizer: SEGV /tmp/project/source/other/random.cpp:10:2",
        ]

        stage_info = hermes_watch.classify_crash_stage(lines, profile)

        self.assertIsNone(stage_info["stage"])
        self.assertEqual(stage_info["stage_class"], "unknown")
        self.assertEqual(stage_info["confidence"], "none")

    def test_enrich_crash_info_with_stage_info_adds_profile_fields(self):
        profile = self.make_profile()
        crash_info = {
            "kind": "asan",
            "location": "ht_block_decoding.cpp:1126",
            "summary": "stack-buffer-overflow",
            "fingerprint": "asan|ht_block_decoding.cpp:1126|stack-buffer-overflow",
        }
        lines = [
            "#0 0x1234 in htj2k_decode /tmp/project/source/core/transform/ht_block_decoding.cpp:1126:7",
            "SUMMARY: AddressSanitizer: stack-buffer-overflow /tmp/project/source/core/transform/ht_block_decoding.cpp:1126:7",
        ]

        enriched = hermes_watch.enrich_crash_info_with_stage_info(crash_info, lines, profile)

        self.assertEqual(enriched["stage"], "ht-block-decode")
        self.assertEqual(enriched["stage_class"], "deep")
        self.assertEqual(enriched["stage_depth_rank"], 4)
        self.assertEqual(enriched["stage_match_source"], "function")

    def test_metrics_snapshot_includes_crash_stage_fields(self):
        metrics = hermes_watch.Metrics()
        snapshot = hermes_watch.metrics_snapshot(
            outcome="crash",
            metrics=metrics,
            run_dir=Path("/tmp/run"),
            report_path=Path("/tmp/run/FUZZING_REPORT.md"),
            start=0.0,
            crash_info={
                "fingerprint": "asan|ht_block_decoding.cpp:1126|stack-buffer-overflow",
                "kind": "asan",
                "location": "ht_block_decoding.cpp:1126",
                "summary": "stack-buffer-overflow",
                "stage": "ht-block-decode",
                "stage_class": "deep",
                "stage_depth_rank": 4,
                "stage_confidence": "high",
                "stage_match_source": "function",
            },
        )

        self.assertEqual(snapshot["crash_stage"], "ht-block-decode")
        self.assertEqual(snapshot["crash_stage_class"], "deep")
        self.assertEqual(snapshot["crash_stage_depth_rank"], 4)
        self.assertEqual(snapshot["crash_stage_confidence"], "high")


class HermesWatchTriggerEvaluationTests(unittest.TestCase):
    def make_profile(self):
        return {
            "triggers": {
                "deep_write_crash": {
                    "enabled": True,
                    "condition": {
                        "min_stage_depth_rank": 2,
                        "sanitizer_match": [
                            "use-after-free",
                            "double-free",
                            "invalid-free",
                            "stack-buffer-overflow",
                            "heap-buffer-overflow-write",
                            "segv-write",
                        ],
                    },
                    "action": "high_priority_alert",
                },
                "deep_signal_emergence": {
                    "enabled": True,
                    "condition": {
                        "stage_any_of": ["ht-block-decode", "idwt-transform", "cleanup-finalize"],
                        "min_new_reproducible_families": 1,
                    },
                    "action": "continue_and_prioritize_triage",
                },
            },
            "actions": {
                "high_priority_alert": {"type": "alert", "requires_human_review": False},
                "continue_and_prioritize_triage": {"type": "continue_run", "requires_human_review": False},
            },
            "crash_policy": {
                "buckets": {
                    "critical": ["use-after-free", "double-free", "invalid-free", "stack-buffer-overflow", "segv-write"],
                    "high": ["heap-buffer-overflow-write", "heap-buffer-overflow", "add_tile_part-write", "ht-block-decode-overflow"],
                    "medium": ["segv-read", "null-deref-deep-stage"],
                    "low": ["parser-shallow-null-deref", "parser-only heap read overflow"],
                },
                "stage_bias": {
                    "parse-main-header": "demote_if_only_read_flavor",
                    "tile-part-load": "raise_if_write_flavor",
                    "ht-block-decode": "strongly_raise",
                },
            },
        }

    def test_evaluate_profile_policy_promotes_deep_write_crash(self):
        profile = self.make_profile()
        crash_info = {
            "kind": "asan",
            "summary": "stack-buffer-overflow on address 0x123",
            "stage": "ht-block-decode",
            "stage_class": "deep",
            "stage_depth_rank": 4,
            "is_duplicate": False,
        }
        artifact_event = {"category": "crash", "reason": "sanitizer-crash"}

        result = hermes_watch.evaluate_profile_policy("crash", artifact_event, crash_info, profile)

        self.assertEqual(result["severity"], "critical")
        self.assertEqual(result["matched_triggers"], ["deep_write_crash", "deep_signal_emergence"])
        self.assertEqual(result["override_action_code"], "high_priority_alert")
        self.assertEqual(result["override_priority"], "critical")

    def test_evaluate_profile_policy_does_not_overpromote_shallow_parser_read_crash(self):
        profile = self.make_profile()
        crash_info = {
            "kind": "asan",
            "summary": "heap-buffer-overflow on address 0x123 READ of size 4",
            "stage": "parse-main-header",
            "stage_class": "shallow",
            "stage_depth_rank": 1,
            "is_duplicate": False,
        }
        artifact_event = {"category": "crash", "reason": "sanitizer-crash"}

        result = hermes_watch.evaluate_profile_policy("crash", artifact_event, crash_info, profile)

        self.assertEqual(result["severity"], "low")
        self.assertEqual(result["matched_triggers"], [])
        self.assertIsNone(result["override_action_code"])

    def test_decide_policy_action_uses_profile_override(self):
        profile = self.make_profile()
        artifact_event = {"category": "crash", "reason": "sanitizer-crash"}
        crash_info = {
            "kind": "asan",
            "summary": "stack-buffer-overflow on address 0x123",
            "stage": "ht-block-decode",
            "stage_class": "deep",
            "stage_depth_rank": 4,
            "is_duplicate": False,
        }

        action = hermes_watch.decide_policy_action("crash", artifact_event, crash_info, profile)

        self.assertEqual(action["action_code"], "high_priority_alert")
        self.assertEqual(action["priority"], "critical")
        self.assertEqual(action["bucket"], "critical")
        self.assertEqual(action["matched_triggers"], ["deep_write_crash", "deep_signal_emergence"])
        self.assertEqual(action["profile_severity"], "critical")

    def test_metrics_snapshot_includes_profile_trigger_results(self):
        metrics = hermes_watch.Metrics()
        snapshot = hermes_watch.metrics_snapshot(
            outcome="crash",
            metrics=metrics,
            run_dir=Path("/tmp/run"),
            report_path=Path("/tmp/run/FUZZING_REPORT.md"),
            start=0.0,
            policy_action={
                "priority": "critical",
                "action_code": "high_priority_alert",
                "recommended_action": "Escalate",
                "next_mode": "triage",
                "bucket": "critical",
                "matched_triggers": ["deep_write_crash"],
                "profile_severity": "critical",
            },
        )

        self.assertEqual(snapshot["policy_matched_triggers"], ["deep_write_crash"])
        self.assertEqual(snapshot["policy_profile_severity"], "critical")


class HermesWatchHistoryTriggerTests(unittest.TestCase):
    def make_profile(self):
        return {
            "triggers": {
                "coverage_plateau": {
                    "enabled": True,
                    "condition": {
                        "plateau_minutes": 180,
                        "min_execs_per_sec": 50,
                        "max_new_high_value_crashes": 0,
                    },
                    "action": "propose_harness_revision",
                },
                "shallow_crash_dominance": {
                    "enabled": True,
                    "condition": {
                        "dominant_stage": "parse-main-header",
                        "min_ratio": 0.70,
                        "min_crash_families": 3,
                    },
                    "action": "shift_weight_to_deeper_harness",
                },
            }
        }

    def test_append_run_history_records_completed_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            automation_dir = Path(tmpdir)
            snapshot = {
                "updated_at": "2026-04-15T10:00:00",
                "outcome": "crash",
                "cov": 100,
                "ft": 200,
                "exec_per_second": 120,
                "crash_stage": "parse-main-header",
                "crash_fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                "policy_profile_severity": "low",
            }

            result = hermes_watch.append_run_history(automation_dir, snapshot)

            self.assertEqual(result["appended"], 1)
            data = json.loads((automation_dir / "run_history.json").read_text(encoding="utf-8"))
            self.assertEqual(data["entries"][0]["outcome"], "crash")
            self.assertEqual(data["entries"][0]["crash_stage"], "parse-main-header")

    def test_evaluate_history_triggers_detects_shallow_crash_dominance(self):
        profile = self.make_profile()
        history = [
            {"outcome": "crash", "crash_stage": "parse-main-header", "crash_fingerprint": "fp1", "updated_at": "2026-04-15T10:00:00", "cov": 100, "exec_per_second": 120},
            {"outcome": "crash", "crash_stage": "parse-main-header", "crash_fingerprint": "fp2", "updated_at": "2026-04-15T10:10:00", "cov": 100, "exec_per_second": 120},
            {"outcome": "crash", "crash_stage": "parse-main-header", "crash_fingerprint": "fp3", "updated_at": "2026-04-15T10:20:00", "cov": 101, "exec_per_second": 120},
            {"outcome": "crash", "crash_stage": "ht-block-decode", "crash_fingerprint": "fp4", "updated_at": "2026-04-15T10:30:00", "cov": 101, "exec_per_second": 120},
        ]

        result = hermes_watch.evaluate_history_triggers(history, profile)

        self.assertIn("shallow_crash_dominance", result["matched_triggers"])
        self.assertEqual(result["override_action_code"], "shift_weight_to_deeper_harness")
        self.assertEqual(result["dominant_stage"], "parse-main-header")

    def test_evaluate_history_triggers_detects_coverage_plateau(self):
        profile = self.make_profile()
        history = [
            {"outcome": "ok", "updated_at": "2026-04-15T07:00:00", "cov": 100, "exec_per_second": 120, "policy_profile_severity": None},
            {"outcome": "ok", "updated_at": "2026-04-15T08:00:00", "cov": 100, "exec_per_second": 120, "policy_profile_severity": None},
            {"outcome": "ok", "updated_at": "2026-04-15T09:00:00", "cov": 100, "exec_per_second": 120, "policy_profile_severity": None},
            {"outcome": "ok", "updated_at": "2026-04-15T10:10:00", "cov": 100, "exec_per_second": 120, "policy_profile_severity": None},
        ]

        result = hermes_watch.evaluate_history_triggers(history, profile)

        self.assertIn("coverage_plateau", result["matched_triggers"])
        self.assertEqual(result["override_action_code"], "propose_harness_revision")

    def test_evaluate_history_triggers_requires_enough_samples(self):
        profile = self.make_profile()
        history = [
            {"outcome": "crash", "crash_stage": "parse-main-header", "crash_fingerprint": "fp1", "updated_at": "2026-04-15T10:00:00", "cov": 100, "exec_per_second": 120},
            {"outcome": "crash", "crash_stage": "parse-main-header", "crash_fingerprint": "fp2", "updated_at": "2026-04-15T10:10:00", "cov": 100, "exec_per_second": 120},
        ]

        result = hermes_watch.evaluate_history_triggers(history, profile)

        self.assertEqual(result["matched_triggers"], [])
        self.assertIsNone(result["override_action_code"])


class HermesWatchTimeoutCorpusTriggerTests(unittest.TestCase):
    def make_profile(self):
        return {
            "triggers": {
                "timeout_surge": {
                    "enabled": True,
                    "condition": {
                        "min_timeout_rate": 0.50,
                        "min_duration_minutes": 60,
                    },
                    "action": "split_slow_lane",
                },
                "corpus_bloat_low_gain": {
                    "enabled": True,
                    "condition": {
                        "min_corpus_growth": 200,
                        "max_coverage_gain_percent": 0.5,
                    },
                    "action": "minimize_and_reseed",
                },
            }
        }

    def test_append_run_history_records_timeout_and_corpus_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            automation_dir = Path(tmpdir)
            snapshot = {
                "updated_at": "2026-04-15T10:00:00",
                "outcome": "timeout",
                "cov": 100,
                "corpus_units": 250,
                "seconds_since_progress": 400,
                "timeout_detected": True,
            }

            hermes_watch.append_run_history(automation_dir, snapshot)

            data = json.loads((automation_dir / "run_history.json").read_text(encoding="utf-8"))
            self.assertTrue(data["entries"][0]["timeout_detected"])
            self.assertEqual(data["entries"][0]["corpus_units"], 250)
            self.assertEqual(data["entries"][0]["seconds_since_progress"], 400)

    def test_evaluate_history_triggers_detects_timeout_surge(self):
        profile = self.make_profile()
        history = [
            {"updated_at": "2026-04-15T07:00:00", "outcome": "timeout", "timeout_detected": True},
            {"updated_at": "2026-04-15T08:00:00", "outcome": "timeout", "timeout_detected": True},
            {"updated_at": "2026-04-15T09:00:00", "outcome": "ok", "timeout_detected": False},
            {"updated_at": "2026-04-15T10:10:00", "outcome": "timeout", "timeout_detected": True},
        ]

        result = hermes_watch.evaluate_history_triggers(history, profile)

        self.assertIn("timeout_surge", result["matched_triggers"])
        self.assertEqual(result["override_action_code"], "split_slow_lane")

    def test_evaluate_history_triggers_detects_corpus_bloat_low_gain(self):
        profile = self.make_profile()
        history = [
            {"updated_at": "2026-04-15T07:00:00", "outcome": "ok", "cov": 100.0, "corpus_units": 100},
            {"updated_at": "2026-04-15T08:00:00", "outcome": "ok", "cov": 100.1, "corpus_units": 180},
            {"updated_at": "2026-04-15T09:00:00", "outcome": "ok", "cov": 100.2, "corpus_units": 240},
            {"updated_at": "2026-04-15T10:10:00", "outcome": "ok", "cov": 100.3, "corpus_units": 320},
        ]

        result = hermes_watch.evaluate_history_triggers(history, profile)

        self.assertIn("corpus_bloat_low_gain", result["matched_triggers"])
        self.assertEqual(result["override_action_code"], "minimize_and_reseed")

    def test_evaluate_history_triggers_skips_when_data_is_missing(self):
        profile = self.make_profile()
        history = [
            {"updated_at": "2026-04-15T07:00:00", "outcome": "ok", "cov": 100.0},
            {"updated_at": "2026-04-15T08:00:00", "outcome": "ok", "cov": 100.1},
            {"updated_at": "2026-04-15T09:00:00", "outcome": "ok", "cov": 100.2},
            {"updated_at": "2026-04-15T10:10:00", "outcome": "ok", "cov": 100.3},
        ]

        result = hermes_watch.evaluate_history_triggers(history, profile)

        self.assertNotIn("timeout_surge", result["matched_triggers"])
        self.assertNotIn("corpus_bloat_low_gain", result["matched_triggers"])


class HermesWatchStabilitySemanticTests(unittest.TestCase):
    def make_profile(self):
        return {
            "triggers": {
                "stability_drop": {
                    "enabled": True,
                    "condition": {
                        "min_stability_percent": 95,
                    },
                    "action": "halt_and_review_harness",
                }
            }
        }

    def test_compute_semantic_history_summary_counts_deep_and_shallow(self):
        history = [
            {"outcome": "crash", "crash_stage": "parse-main-header"},
            {"outcome": "crash", "crash_stage": "parse-main-header"},
            {"outcome": "crash", "crash_stage": "ht-block-decode"},
            {"outcome": "ok", "crash_stage": None},
        ]

        summary = hermes_watch.compute_semantic_history_summary(history)

        self.assertEqual(summary["shallow_crash_count"], 2)
        self.assertEqual(summary["deep_crash_count"], 1)
        self.assertEqual(summary["dominant_stage"], "parse-main-header")

    def test_evaluate_history_triggers_detects_stability_drop_from_duplicate_recurrence(self):
        profile = self.make_profile()
        history = [
            {"updated_at": "2026-04-15T10:00:00", "outcome": "crash", "crash_stage": "parse-main-header", "crash_fingerprint": "fp1"},
            {"updated_at": "2026-04-15T10:10:00", "outcome": "crash", "crash_stage": "parse-main-header", "crash_fingerprint": "fp1"},
            {"updated_at": "2026-04-15T10:20:00", "outcome": "crash", "crash_stage": "parse-main-header", "crash_fingerprint": "fp1"},
            {"updated_at": "2026-04-15T10:30:00", "outcome": "crash", "crash_stage": "parse-main-header", "crash_fingerprint": "fp2"},
        ]

        result = hermes_watch.evaluate_history_triggers(history, profile)

        self.assertIn("stability_drop", result["matched_triggers"])
        self.assertEqual(result["override_action_code"], "halt_and_review_harness")
        self.assertEqual(result["semantic_summary"]["dominant_stage"], "parse-main-header")

    def test_evaluate_history_triggers_skips_stability_drop_when_history_is_diverse(self):
        profile = self.make_profile()
        history = [
            {"updated_at": "2026-04-15T10:00:00", "outcome": "crash", "crash_stage": "parse-main-header", "crash_fingerprint": "fp1"},
            {"updated_at": "2026-04-15T10:10:00", "outcome": "crash", "crash_stage": "ht-block-decode", "crash_fingerprint": "fp2"},
            {"updated_at": "2026-04-15T10:20:00", "outcome": "crash", "crash_stage": "line-based-decode", "crash_fingerprint": "fp3"},
            {"updated_at": "2026-04-15T10:30:00", "outcome": "ok", "crash_stage": None, "crash_fingerprint": None},
        ]

        result = hermes_watch.evaluate_history_triggers(history, profile)

        self.assertNotIn("stability_drop", result["matched_triggers"])

    def test_decide_policy_action_includes_semantic_quality_summary(self):
        profile = self.make_profile()
        artifact_event = {"category": "crash", "reason": "sanitizer-crash"}
        crash_info = {
            "kind": "asan",
            "summary": "heap-buffer-overflow on address 0x123 READ of size 4",
            "stage": "parse-main-header",
            "stage_class": "shallow",
            "stage_depth_rank": 1,
            "is_duplicate": True,
        }
        history = [
            {"updated_at": "2026-04-15T10:00:00", "outcome": "crash", "crash_stage": "parse-main-header", "crash_fingerprint": "fp1"},
            {"updated_at": "2026-04-15T10:10:00", "outcome": "crash", "crash_stage": "parse-main-header", "crash_fingerprint": "fp1"},
            {"updated_at": "2026-04-15T10:20:00", "outcome": "crash", "crash_stage": "ht-block-decode", "crash_fingerprint": "fp2"},
            {"updated_at": "2026-04-15T10:30:00", "outcome": "ok", "crash_stage": None, "crash_fingerprint": None},
        ]

        action = hermes_watch.decide_policy_action("crash", artifact_event, crash_info, profile, history)

        self.assertIn("semantic_summary", action)
        self.assertEqual(action["semantic_summary"]["shallow_crash_count"], 2)
        self.assertEqual(action["semantic_summary"]["deep_crash_count"], 1)


class HermesWatchRefinerActionExecutionTests(unittest.TestCase):
    def test_apply_policy_action_records_shift_weight_to_deeper_harness(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_action = {
                "action_code": "shift_weight_to_deeper_harness",
                "bucket": "coverage",
                "priority": "high",
                "next_mode": "coverage",
                "recommended_action": "Shift toward deeper harness",
            }
            artifact_event = {"category": "crash", "reason": "sanitizer-crash"}
            crash_info = {
                "fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                "stage": "parse-main-header",
            }

            result = hermes_watch.apply_policy_action(
                root,
                run_dir="/runs/one",
                report_path="/runs/one/FUZZING_REPORT.md",
                outcome="crash",
                artifact_event=artifact_event,
                policy_action=policy_action,
                crash_info=crash_info,
            )

            self.assertIn("mode_refinements", result["updated"])
            data = json.loads((root / "mode_refinements.json").read_text(encoding="utf-8"))
            self.assertEqual(data["entries"][0]["action_code"], "shift_weight_to_deeper_harness")

    def test_apply_policy_action_records_split_slow_lane(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_action = {
                "action_code": "split_slow_lane",
                "bucket": "coverage",
                "priority": "high",
                "next_mode": "coverage",
                "recommended_action": "Split slow lane",
            }
            artifact_event = {"category": "timeout", "reason": "watcher-timeout"}

            result = hermes_watch.apply_policy_action(
                root,
                run_dir="/runs/slow",
                report_path="/runs/slow/FUZZING_REPORT.md",
                outcome="timeout",
                artifact_event=artifact_event,
                policy_action=policy_action,
                crash_info=None,
            )

            self.assertIn("slow_lane_candidates", result["updated"])
            data = json.loads((root / "slow_lane_candidates.json").read_text(encoding="utf-8"))
            self.assertEqual(data["entries"][0]["action_code"], "split_slow_lane")

    def test_apply_policy_action_records_minimize_and_reseed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_action = {
                "action_code": "minimize_and_reseed",
                "bucket": "coverage",
                "priority": "medium",
                "next_mode": "coverage",
                "recommended_action": "Minimize corpus",
            }
            artifact_event = {"category": "ok", "reason": None}

            result = hermes_watch.apply_policy_action(
                root,
                run_dir="/runs/corpus",
                report_path="/runs/corpus/FUZZING_REPORT.md",
                outcome="ok",
                artifact_event=artifact_event,
                policy_action=policy_action,
                crash_info=None,
            )

            self.assertIn("corpus_refinements", result["updated"])
            data = json.loads((root / "corpus_refinements.json").read_text(encoding="utf-8"))
            self.assertEqual(data["entries"][0]["action_code"], "minimize_and_reseed")

    def test_apply_policy_action_records_halt_and_review_harness(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            policy_action = {
                "action_code": "halt_and_review_harness",
                "bucket": "stability",
                "priority": "high",
                "next_mode": "coverage",
                "recommended_action": "Review harness",
            }
            artifact_event = {"category": "crash", "reason": "sanitizer-crash"}

            result = hermes_watch.apply_policy_action(
                root,
                run_dir="/runs/review",
                report_path="/runs/review/FUZZING_REPORT.md",
                outcome="crash",
                artifact_event=artifact_event,
                policy_action=policy_action,
                crash_info=None,
            )

            self.assertIn("harness_reviews", result["updated"])
            data = json.loads((root / "harness_review_queue.json").read_text(encoding="utf-8"))
            self.assertEqual(data["entries"][0]["action_code"], "halt_and_review_harness")


class HermesWatchRefinerLifecycleTests(unittest.TestCase):
    def test_derive_refiner_lifecycle_maps_major_phases(self):
        self.assertEqual(hermes_watch.derive_refiner_lifecycle({"status": "recorded"}), "queued")
        self.assertEqual(hermes_watch.derive_refiner_lifecycle({"status": "completed"}), "planned")
        self.assertEqual(hermes_watch.derive_refiner_lifecycle({"orchestration_status": "prepared"}), "orchestration_prepared")
        self.assertEqual(hermes_watch.derive_refiner_lifecycle({"dispatch_status": "ready"}), "dispatch_ready")
        self.assertEqual(hermes_watch.derive_refiner_lifecycle({"bridge_status": "armed"}), "bridge_armed")
        self.assertEqual(hermes_watch.derive_refiner_lifecycle({"launch_status": "succeeded"}), "launch_succeeded")
        self.assertEqual(hermes_watch.derive_refiner_lifecycle({"verification_status": "verified"}), "verified")
        self.assertEqual(hermes_watch.derive_refiner_lifecycle({"verification_policy_status": "retry"}), "retry_requested")
        self.assertEqual(hermes_watch.derive_refiner_lifecycle({"verification_policy_status": "escalate"}), "escalated")

    def test_execute_next_refiner_action_sets_planned_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            registry_path = root / "mode_refinements.json"
            registry_path.write_text(
                json.dumps({"entries": [{"key": "shift_weight_to_deeper_harness:/runs/one", "action_code": "shift_weight_to_deeper_harness", "run_dir": "/runs/one"}]}),
                encoding="utf-8",
            )

            hermes_watch.execute_next_refiner_action(root, repo_root=repo_root)

            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            self.assertEqual(registry["entries"][0]["lifecycle"], "planned")

    def test_refiner_pipeline_updates_canonical_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            artifact_path = repo_root / "fuzz-records" / "delegate-notes" / "review-note.md"
            artifact_path.parent.mkdir(parents=True)
            artifact_path.write_text("# Harness Review\n\n## Findings\n- issue\n\n## Next Steps\n- action\n", encoding="utf-8")
            registry_path = root / "harness_review_queue.json"
            registry_path.write_text(
                json.dumps({"entries": [{
                    "key": "halt_and_review_harness:/runs/review",
                    "action_code": "halt_and_review_harness",
                    "run_dir": "/runs/review",
                    "bridge_status": "succeeded",
                    "bridge_channel": "hermes-cli-delegate",
                    "delegate_session_id": "session_987xyz",
                    "delegate_artifact_path": str(artifact_path),
                    "delegate_expected_sections": ["# Harness Review", "## Findings", "## Next Steps"],
                    "delegate_quality_sections": ["## Findings", "## Next Steps"],
                }]}),
                encoding="utf-8",
            )

            def probe(command: list[str], cwd: Path | None = None) -> tuple[int, str]:
                return 0, "Preview  Last Active Src ID\nsomething 1m ago cli session_987xyz\n"

            hermes_watch.verify_next_refiner_result(root, repo_root=repo_root, probe_runner=probe)
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            self.assertEqual(registry["entries"][0]["lifecycle"], "verified")

            registry_path.write_text(
                json.dumps({"entries": [{
                    "key": "halt_and_review_harness:/runs/review",
                    "action_code": "halt_and_review_harness",
                    "run_dir": "/runs/review",
                    "verification_status": "unverified",
                    "verification_summary": "delegate-session-artifact-visible-shape-or-quality-missing",
                    "bridge_channel": "hermes-cli-delegate",
                }]}),
                encoding="utf-8",
            )
            hermes_watch.apply_verification_failure_policy(root, repo_root=repo_root)
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            self.assertEqual(registry["entries"][0]["lifecycle"], "escalated")


class HermesWatchRefinerExecutorTests(unittest.TestCase):
    def test_execute_next_refiner_action_processes_mode_refinement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            (root / "mode_refinements.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "shift_weight_to_deeper_harness:/runs/one",
                                "action_code": "shift_weight_to_deeper_harness",
                                "run_dir": "/runs/one",
                                "report_path": "/runs/one/FUZZING_REPORT.md",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.execute_next_refiner_action(root, repo_root=repo_root)

            self.assertEqual(result["action_code"], "shift_weight_to_deeper_harness")
            self.assertEqual(result["status"], "completed")
            plan = repo_root / "fuzz-records" / "refiner-plans" / "shift_weight_to_deeper_harness-runs-one.md"
            self.assertTrue(plan.exists())

    def test_execute_next_refiner_action_processes_slow_lane_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            (root / "slow_lane_candidates.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "split_slow_lane:/runs/slow",
                                "action_code": "split_slow_lane",
                                "run_dir": "/runs/slow",
                                "report_path": "/runs/slow/FUZZING_REPORT.md",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.execute_next_refiner_action(root, repo_root=repo_root)

            self.assertEqual(result["action_code"], "split_slow_lane")
            self.assertEqual(result["status"], "completed")

    def test_execute_next_refiner_action_processes_corpus_refinement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            (root / "corpus_refinements.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "minimize_and_reseed:/runs/corpus",
                                "action_code": "minimize_and_reseed",
                                "run_dir": "/runs/corpus",
                                "report_path": "/runs/corpus/FUZZING_REPORT.md",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.execute_next_refiner_action(root, repo_root=repo_root)

            self.assertEqual(result["action_code"], "minimize_and_reseed")
            self.assertEqual(result["status"], "completed")

    def test_execute_next_refiner_action_writes_duplicate_replay_derived_corpus_refinement_plan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            (root / "corpus_refinements.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "minimize_and_reseed:/runs/corpus",
                                "action_code": "minimize_and_reseed",
                                "run_dir": "/runs/corpus",
                                "report_path": "/runs/corpus/FUZZING_REPORT.md",
                                "recommended_action": "Prepare a duplicate-aware minimization plan.",
                                "candidate_route": "reseed-before-retry",
                                "derived_from_action_code": "review_duplicate_crash_replay",
                                "duplicate_replay_source_key": "review_duplicate_crash_replay:asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                                "crash_fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                                "crash_location": "j2kmarkers.cpp:52",
                                "crash_summary": "heap-buffer-overflow",
                                "occurrence_count": 3,
                                "first_artifact_path": "/runs/dup-first/crashes/crash-a",
                                "latest_artifact_path": "/runs/dup-latest/crashes/crash-c",
                                "replay_execution_status": "completed",
                                "replay_execution_markdown_path": "/records/dup-replay.md",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            hermes_watch.execute_next_refiner_action(root, repo_root=repo_root)

            plan = repo_root / "fuzz-records" / "refiner-plans" / "minimize_and_reseed-runs-corpus.md"
            plan_text = plan.read_text(encoding="utf-8")
            self.assertIn("## Corpus Refinement Context", plan_text)
            self.assertIn("- candidate_route: reseed-before-retry", plan_text)
            self.assertIn("- derived_from_action_code: review_duplicate_crash_replay", plan_text)
            self.assertIn("- duplicate_replay_source_key: review_duplicate_crash_replay:asan|j2kmarkers.cpp:52|heap-buffer-overflow", plan_text)
            self.assertIn("- replay_execution_markdown_path: /records/dup-replay.md", plan_text)
            self.assertIn("cp -n /runs/dup-latest/crashes/crash-c", plan_text)
            self.assertIn("sha1sum /runs/dup-first/crashes/crash-a /runs/dup-latest/crashes/crash-c", plan_text)

    def test_execute_corpus_refinement_probe_copies_seed_and_verifies_replay_retention(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            latest_artifact = repo_root / "latest-crash.j2k"
            first_artifact = repo_root / "first-crash.j2k"
            latest_artifact.write_bytes(b"latest-crash")
            first_artifact.write_bytes(b"first-crash")
            fake_harness = repo_root / "fake-harness"
            fake_harness.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_harness.chmod(0o755)
            entry = {
                "run_dir": "/runs/corpus",
                "report_path": "/runs/corpus/FUZZING_REPORT.md",
                "crash_fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                "first_artifact_path": str(first_artifact),
                "latest_artifact_path": str(latest_artifact),
                "replay_harness_path": str(fake_harness),
            }

            def fake_runner(cmd: list[str], cwd: Path) -> tuple[int, str]:
                self.assertEqual(cwd, repo_root)
                self.assertEqual(cmd[0], str(fake_harness))
                self.assertEqual(Path(cmd[1]).name, latest_artifact.name)
                return (
                    134,
                    "ERROR: AddressSanitizer: heap-buffer-overflow\n"
                    "SUMMARY: AddressSanitizer: heap-buffer-overflow /tmp/project/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()\n",
                )

            result = hermes_watch.execute_corpus_refinement_probe(repo_root, entry, replay_runner=fake_runner)

            self.assertEqual(result["status"], "completed")
            triage_bucket_path = Path(result["triage_bucket_path"])
            regression_bucket_path = Path(result["regression_bucket_path"])
            known_bad_bucket_path = Path(result["known_bad_bucket_path"])
            self.assertTrue(triage_bucket_path.exists())
            self.assertTrue(regression_bucket_path.exists())
            self.assertTrue(known_bad_bucket_path.exists())
            self.assertEqual(triage_bucket_path.read_bytes(), latest_artifact.read_bytes())
            self.assertEqual(result["retention_replay_exit_code"], 134)
            self.assertEqual(
                result["retention_replay_signature"]["fingerprint"],
                "asan|j2kmarkers.cpp:52|heap-buffer-overflow /tmp/project/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()",
            )
            self.assertTrue(Path(result["json_path"]).exists())
            self.assertTrue(Path(result["markdown_path"]).exists())
            self.assertEqual(entry["corpus_refinement_execution_status"], "completed")
            self.assertEqual(entry["triage_bucket_path"], str(triage_bucket_path))
            self.assertEqual(entry["regression_bucket_path"], str(regression_bucket_path))
            self.assertEqual(entry["known_bad_bucket_path"], str(known_bad_bucket_path))

    def test_execute_next_refiner_action_records_corpus_refinement_execution_lineage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            latest_artifact = repo_root / "latest-crash.j2k"
            first_artifact = repo_root / "first-crash.j2k"
            latest_artifact.write_bytes(b"latest-crash")
            first_artifact.write_bytes(b"first-crash")
            fake_harness = repo_root / "fake-harness"
            fake_harness.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_harness.chmod(0o755)
            (root / "corpus_refinements.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "minimize_and_reseed:/runs/corpus",
                                "action_code": "minimize_and_reseed",
                                "run_dir": "/runs/corpus",
                                "report_path": "/runs/corpus/FUZZING_REPORT.md",
                                "recommended_action": "Prepare a duplicate-aware minimization plan.",
                                "first_artifact_path": str(first_artifact),
                                "latest_artifact_path": str(latest_artifact),
                                "replay_harness_path": str(fake_harness),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            patched_probe = hermes_watch.execute_corpus_refinement_probe

            def fake_probe(repo_root_arg: Path, entry: dict[str, object], replay_runner=None):
                return patched_probe(repo_root_arg, entry, replay_runner=lambda cmd, cwd: (
                    134,
                    "ERROR: AddressSanitizer: heap-buffer-overflow\n"
                    "SUMMARY: AddressSanitizer: heap-buffer-overflow /tmp/project/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()\n",
                ))

            original_probe = hermes_watch.execute_corpus_refinement_probe
            hermes_watch.execute_corpus_refinement_probe = fake_probe
            try:
                result = hermes_watch.execute_next_refiner_action(root, repo_root=repo_root)
            finally:
                hermes_watch.execute_corpus_refinement_probe = original_probe

            self.assertEqual(result["action_code"], "minimize_and_reseed")
            self.assertEqual(result["corpus_refinement_execution_status"], "completed")
            plan = repo_root / "fuzz-records" / "refiner-plans" / "minimize_and_reseed-runs-corpus.md"
            plan_text = plan.read_text(encoding="utf-8")
            self.assertIn("## Corpus Refinement Execution", plan_text)
            self.assertIn("- corpus_refinement_execution_status: completed", plan_text)
            self.assertIn("- triage_bucket_path:", plan_text)
            self.assertIn("- retention_replay_signature:", plan_text)

    def test_execute_next_refiner_action_refreshes_llm_evidence_after_corpus_refinement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            latest_artifact = repo_root / "latest-crash.j2k"
            latest_artifact.write_bytes(b"latest-crash")
            fake_harness = repo_root / "fake-harness"
            fake_harness.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_harness.chmod(0o755)
            (root / "corpus_refinements.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "minimize_and_reseed:/runs/corpus-refresh",
                                "action_code": "minimize_and_reseed",
                                "status": "recorded",
                                "run_dir": "/runs/corpus-refresh",
                                "report_path": "/runs/corpus-refresh/FUZZING_REPORT.md",
                                "recommended_action": "Prepare a duplicate-aware minimization plan.",
                                "latest_artifact_path": str(latest_artifact),
                                "replay_harness_path": str(fake_harness),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            original_probe = hermes_watch.execute_corpus_refinement_probe
            original_refresh = hermes_watch.refresh_llm_evidence_packet_best_effort
            refresh_calls = []

            def fake_probe(repo_root_arg: Path, entry: dict[str, object], replay_runner=None):
                entry["corpus_refinement_execution_status"] = "completed"
                entry["triage_bucket_path"] = str(repo_root_arg / "fuzz/corpus/triage/latest-crash.j2k")
                return {
                    "status": "completed",
                    "json_path": str(repo_root_arg / "fuzz-records/corpus-refinement-executions/fake.json"),
                    "markdown_path": str(repo_root_arg / "fuzz-records/corpus-refinement-executions/fake.md"),
                }

            def fake_refresh(repo_root_arg: Path):
                refresh_calls.append(str(repo_root_arg))
                return {"llm_evidence_json_path": str(repo_root_arg / "fuzz-records/llm-evidence/fake.json")}

            hermes_watch.execute_corpus_refinement_probe = fake_probe
            hermes_watch.refresh_llm_evidence_packet_best_effort = fake_refresh
            try:
                result = hermes_watch.execute_next_refiner_action(root, repo_root=repo_root)
            finally:
                hermes_watch.execute_corpus_refinement_probe = original_probe
                hermes_watch.refresh_llm_evidence_packet_best_effort = original_refresh

            self.assertEqual(result["action_code"], "minimize_and_reseed")
            self.assertEqual(refresh_calls, [str(repo_root)])

    def test_execute_next_refiner_action_processes_harness_review(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            (root / "harness_review_queue.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "halt_and_review_harness:/runs/review",
                                "action_code": "halt_and_review_harness",
                                "run_dir": "/runs/review",
                                "report_path": "/runs/review/FUZZING_REPORT.md",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.execute_next_refiner_action(root, repo_root=repo_root)

            self.assertEqual(result["action_code"], "halt_and_review_harness")
            self.assertEqual(result["status"], "completed")

    def test_execute_next_refiner_action_processes_duplicate_crash_replay_review(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            (root / "duplicate_crash_reviews.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "review_duplicate_crash_replay:asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                                "action_code": "review_duplicate_crash_replay",
                                "run_dir": "/runs/dup-review",
                                "report_path": "/runs/dup-review/FUZZING_REPORT.md",
                                "crash_fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.execute_next_refiner_action(root, repo_root=repo_root)

            self.assertEqual(result["action_code"], "review_duplicate_crash_replay")
            self.assertEqual(result["status"], "completed")
            plan = repo_root / "fuzz-records" / "refiner-plans" / "review_duplicate_crash_replay-runs-dup-review.md"
            self.assertTrue(plan.exists())

    def test_execute_next_refiner_action_writes_duplicate_crash_compare_and_replay_plan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            (root / "duplicate_crash_reviews.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "review_duplicate_crash_replay:asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                                "action_code": "review_duplicate_crash_replay",
                                "run_dir": "/runs/dup-latest",
                                "report_path": "/runs/dup-latest/FUZZING_REPORT.md",
                                "outcome": "crash",
                                "recommended_action": "Compare first and latest duplicate repros before triage.",
                                "crash_fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                                "crash_location": "j2kmarkers.cpp:52",
                                "crash_summary": "heap-buffer-overflow",
                                "occurrence_count": 3,
                                "first_seen_run": "/runs/dup-first",
                                "first_seen_report_path": "/runs/dup-first/FUZZING_REPORT.md",
                                "first_artifact_path": "/runs/dup-first/crashes/crash-a",
                                "latest_artifact_path": "/runs/dup-latest/crashes/crash-c",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            hermes_watch.execute_next_refiner_action(root, repo_root=repo_root)

            plan = repo_root / "fuzz-records" / "refiner-plans" / "review_duplicate_crash_replay-runs-dup-latest.md"
            plan_text = plan.read_text(encoding="utf-8")
            self.assertIn("## Duplicate Crash Comparison", plan_text)
            self.assertIn("- occurrence_count: 3", plan_text)
            self.assertIn("- first_seen_run: /runs/dup-first", plan_text)
            self.assertIn("- latest_run: /runs/dup-latest", plan_text)
            self.assertIn("- first_artifact_path: /runs/dup-first/crashes/crash-a", plan_text)
            self.assertIn("- latest_artifact_path: /runs/dup-latest/crashes/crash-c", plan_text)
            self.assertIn("sha1sum /runs/dup-first/crashes/crash-a /runs/dup-latest/crashes/crash-c", plan_text)
            self.assertIn("cmp -l /runs/dup-first/crashes/crash-a /runs/dup-latest/crashes/crash-c || true", plan_text)

    def test_execute_duplicate_crash_replay_probe_writes_execution_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            first_artifact = repo_root / "first-crash.j2k"
            latest_artifact = repo_root / "latest-crash.j2k"
            first_artifact.write_bytes(b"first-crash")
            latest_artifact.write_bytes(b"latest-crash")
            fake_harness = repo_root / "fake-harness"
            fake_harness.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_harness.chmod(0o755)
            entry = {
                "run_dir": "/runs/dup-latest",
                "report_path": "/runs/dup-latest/FUZZING_REPORT.md",
                "crash_fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                "first_artifact_path": str(first_artifact),
                "latest_artifact_path": str(latest_artifact),
                "replay_harness_path": str(fake_harness),
            }
            outputs = iter(
                [
                    (
                        134,
                        "ERROR: AddressSanitizer: heap-buffer-overflow\n"
                        "SUMMARY: AddressSanitizer: heap-buffer-overflow /tmp/project/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()\n",
                    ),
                    (
                        134,
                        "ERROR: AddressSanitizer: heap-buffer-overflow\n"
                        "SUMMARY: AddressSanitizer: heap-buffer-overflow /tmp/project/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()\n",
                    ),
                ]
            )

            result = hermes_watch.execute_duplicate_crash_replay_probe(
                repo_root,
                entry,
                replay_runner=lambda cmd, cwd: next(outputs),
            )

            self.assertEqual(result["status"], "completed")
            self.assertTrue(Path(result["json_path"]).exists())
            self.assertTrue(Path(result["markdown_path"]).exists())
            self.assertEqual(entry["replay_execution_status"], "completed")
            self.assertEqual(entry["first_replay_exit_code"], 134)
            self.assertEqual(entry["latest_replay_exit_code"], 134)
            self.assertEqual(entry["first_replay_signature"]["location"], "j2kmarkers.cpp:52")
            self.assertEqual(entry["latest_replay_signature"]["location"], "j2kmarkers.cpp:52")
            self.assertFalse(entry["replay_artifact_bytes_equal"])
            markdown = Path(result["markdown_path"]).read_text(encoding="utf-8")
            self.assertIn("# Duplicate Crash Replay Execution", markdown)
            self.assertIn("- first_replay_exit_code: 134", markdown)
            self.assertIn("- latest_replay_exit_code: 134", markdown)
            self.assertIn("- replay_artifact_bytes_equal: False", markdown)

    def test_run_duplicate_crash_replay_command_enables_symbolized_replay(self):
        captured = {}

        class FakeProc:
            returncode = 0
            stdout = "ok"

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            captured["env"] = kwargs.get("env")
            captured["timeout"] = kwargs.get("timeout")
            return FakeProc()

        original_run = hermes_watch.subprocess.run
        hermes_watch.subprocess.run = fake_run
        try:
            hermes_watch.run_duplicate_crash_replay_command(["/tmp/fake-harness", "/tmp/crash-a"], Path("/tmp"))
        finally:
            hermes_watch.subprocess.run = original_run

        self.assertEqual(captured["timeout"], 30)
        self.assertIn("symbolize=1", captured["env"]["ASAN_OPTIONS"])
        self.assertEqual(captured["env"]["ASAN_SYMBOLIZER_PATH"], "/usr/bin/llvm-symbolizer")

    def test_execute_next_refiner_action_records_duplicate_crash_replay_execution_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            first_artifact = repo_root / "first-crash.j2k"
            latest_artifact = repo_root / "latest-crash.j2k"
            first_artifact.write_bytes(b"first-crash")
            latest_artifact.write_bytes(b"latest-crash")
            harness = repo_root / "fake-harness.sh"
            harness.write_text(
                "#!/bin/sh\n"
                "echo 'ERROR: AddressSanitizer: heap-buffer-overflow'\n"
                "echo 'SUMMARY: AddressSanitizer: heap-buffer-overflow /tmp/project/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()'\n"
                "exit 134\n",
                encoding="utf-8",
            )
            harness.chmod(0o755)
            (root / "duplicate_crash_reviews.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "review_duplicate_crash_replay:asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                                "action_code": "review_duplicate_crash_replay",
                                "run_dir": "/runs/dup-exec",
                                "report_path": "/runs/dup-exec/FUZZING_REPORT.md",
                                "outcome": "crash",
                                "recommended_action": "Compare first and latest duplicate repros before triage.",
                                "crash_fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                                "crash_location": "j2kmarkers.cpp:52",
                                "crash_summary": "heap-buffer-overflow",
                                "occurrence_count": 3,
                                "first_seen_run": "/runs/dup-first",
                                "first_seen_report_path": "/runs/dup-first/FUZZING_REPORT.md",
                                "first_artifact_path": str(first_artifact),
                                "latest_artifact_path": str(latest_artifact),
                                "replay_harness_path": str(harness),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.execute_next_refiner_action(root, repo_root=repo_root)

            self.assertEqual(result["action_code"], "review_duplicate_crash_replay")
            self.assertEqual(result["replay_execution_status"], "completed")
            registry = json.loads((root / "duplicate_crash_reviews.json").read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["replay_execution_status"], "completed")
            self.assertEqual(entry["first_replay_exit_code"], 134)
            self.assertEqual(entry["latest_replay_exit_code"], 134)
            plan = repo_root / "fuzz-records" / "refiner-plans" / "review_duplicate_crash_replay-runs-dup-exec.md"
            plan_text = plan.read_text(encoding="utf-8")
            self.assertIn("## Replay Execution", plan_text)
            self.assertIn("- replay_execution_status: completed", plan_text)
            self.assertIn("- first_replay_exit_code: 134", plan_text)
            self.assertIn("- latest_replay_exit_code: 134", plan_text)

    def test_duplicate_replay_followup_entry_promotes_stable_distinct_duplicate_family_to_minimize_and_reseed(self):
        entry = {
            "key": "review_duplicate_crash_replay:asan|j2kmarkers.cpp:52|heap-buffer-overflow",
            "action_code": "review_duplicate_crash_replay",
            "run_dir": "/runs/dup-exec",
            "report_path": "/runs/dup-exec/FUZZING_REPORT.md",
            "outcome": "crash",
            "crash_fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow",
            "crash_location": "j2kmarkers.cpp:52",
            "crash_summary": "heap-buffer-overflow",
            "occurrence_count": 3,
            "first_artifact_path": "/runs/dup-first/crashes/crash-a",
            "latest_artifact_path": "/runs/dup-exec/crashes/crash-c",
            "replay_execution_status": "completed",
            "replay_execution_markdown_path": "/records/duplicate-crash-replays/run-7.md",
            "replay_artifact_bytes_equal": False,
            "first_replay_exit_code": 134,
            "latest_replay_exit_code": 134,
            "first_replay_signature": {"fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow"},
            "latest_replay_signature": {"fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow"},
        }

        followup = hermes_watch.build_duplicate_replay_followup_entry(entry)

        self.assertEqual(followup["action_code"], "minimize_and_reseed")
        self.assertEqual(followup["candidate_route"], "reseed-before-retry")
        self.assertEqual(followup["derived_from_action_code"], "review_duplicate_crash_replay")
        self.assertEqual(followup["duplicate_replay_source_key"], entry["key"])
        self.assertIn("stable duplicate replay", followup["recommended_action"])
        self.assertEqual(followup["replay_execution_markdown_path"], "/records/duplicate-crash-replays/run-7.md")

    def test_execute_next_refiner_action_records_duplicate_replay_followup_corpus_refinement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            first_artifact = repo_root / "first-crash.j2k"
            latest_artifact = repo_root / "latest-crash.j2k"
            first_artifact.write_bytes(b"first-crash")
            latest_artifact.write_bytes(b"latest-crash")
            harness = repo_root / "fake-harness.sh"
            harness.write_text(
                "#!/bin/sh\n"
                "echo 'ERROR: AddressSanitizer: heap-buffer-overflow'\n"
                "echo 'SUMMARY: AddressSanitizer: heap-buffer-overflow /tmp/project/source/core/codestream/j2kmarkers.cpp:52:17 in j2k_marker_io_base::get_byte()'\n"
                "exit 134\n",
                encoding="utf-8",
            )
            harness.chmod(0o755)
            (root / "duplicate_crash_reviews.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "review_duplicate_crash_replay:asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                                "action_code": "review_duplicate_crash_replay",
                                "run_dir": "/runs/dup-exec",
                                "report_path": "/runs/dup-exec/FUZZING_REPORT.md",
                                "outcome": "crash",
                                "recommended_action": "Compare first and latest duplicate repros before triage.",
                                "crash_fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                                "crash_location": "j2kmarkers.cpp:52",
                                "crash_summary": "heap-buffer-overflow",
                                "occurrence_count": 3,
                                "first_seen_run": "/runs/dup-first",
                                "first_seen_report_path": "/runs/dup-first/FUZZING_REPORT.md",
                                "first_artifact_path": str(first_artifact),
                                "latest_artifact_path": str(latest_artifact),
                                "replay_harness_path": str(harness),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.execute_next_refiner_action(root, repo_root=repo_root)

            self.assertEqual(result["action_code"], "review_duplicate_crash_replay")
            corpus_registry = json.loads((root / "corpus_refinements.json").read_text(encoding="utf-8"))
            followup = corpus_registry["entries"][0]
            self.assertEqual(followup["action_code"], "minimize_and_reseed")
            self.assertEqual(followup["derived_from_action_code"], "review_duplicate_crash_replay")
            self.assertEqual(followup["duplicate_replay_source_key"], "review_duplicate_crash_replay:asan|j2kmarkers.cpp:52|heap-buffer-overflow")
            self.assertEqual(followup["replay_execution_status"], "completed")
            self.assertEqual(followup["candidate_route"], "reseed-before-retry")

    def test_execute_next_refiner_action_processes_harness_correction_regeneration(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            (root / "harness_correction_regeneration_queue.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "regenerate_harness_correction:candidate-1",
                                "action_code": "regenerate_harness_correction",
                                "run_dir": "/runs/apply-abort-candidate-1",
                                "report_path": "/runs/apply-abort-candidate-1/FUZZING_REPORT.md",
                                "selected_candidate_id": "candidate-1",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.execute_next_refiner_action(root, repo_root=repo_root)

            self.assertEqual(result["action_code"], "regenerate_harness_correction")
            self.assertEqual(result["status"], "completed")
            plan = repo_root / "fuzz-records" / "refiner-plans" / "regenerate_harness_correction-runs-apply-abort-candidate-1.md"
            self.assertTrue(plan.exists())

    def test_execute_next_refiner_action_prefers_higher_queue_weight_across_registries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            (root / "mode_refinements.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "shift_weight_to_deeper_harness:/runs/one",
                                "action_code": "shift_weight_to_deeper_harness",
                                "run_dir": "/runs/one",
                                "report_path": "/runs/one/FUZZING_REPORT.md",
                                "selected_candidate_id": "candidate-1",
                                "selected_candidate_status": "active",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / "harness_review_queue.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "halt_and_review_harness:/runs/review",
                                "action_code": "halt_and_review_harness",
                                "run_dir": "/runs/review",
                                "report_path": "/runs/review/FUZZING_REPORT.md",
                                "selected_candidate_id": "candidate-2",
                                "selected_candidate_status": "review_required",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / "run_history.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {"outcome": "crash", "crash_stage": "parse-main-header", "updated_at": "2026-04-15T10:00:00"},
                            {"outcome": "crash", "crash_stage": "parse-main-header", "updated_at": "2026-04-15T10:10:00"},
                            {"outcome": "crash", "crash_stage": "parse-main-header", "updated_at": "2026-04-15T10:20:00"}
                        ]
                    }
                ),
                encoding="utf-8",
            )
            candidate_registry_dir = repo_root / "fuzz-records" / "harness-candidates"
            candidate_registry_dir.mkdir(parents=True)
            (candidate_registry_dir / "ranked-candidates.json").write_text(
                json.dumps(
                    {
                        "project": "repo",
                        "candidates": [
                            {"candidate_id": "candidate-1", "score": 30, "effective_score": 18, "status": "active", "rank": 1},
                            {"candidate_id": "candidate-2", "score": 55, "effective_score": 44, "status": "review_required", "rank": 2},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.execute_next_refiner_action(root, repo_root=repo_root)

            self.assertEqual(result["action_code"], "halt_and_review_harness")
            self.assertGreater(result["queue_weight"], 0)
            registry = json.loads((root / "harness_review_queue.json").read_text(encoding="utf-8"))
            self.assertEqual(registry["entries"][0]["queue_rank"], 1)

    def test_compute_refiner_queue_weight_rewards_viable_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            candidate_registry_dir = repo_root / "fuzz-records" / "harness-candidates"
            candidate_registry_dir.mkdir(parents=True)
            (candidate_registry_dir / "ranked-candidates.json").write_text(
                json.dumps(
                    {
                        "project": "repo",
                        "candidates": [
                            {"candidate_id": "candidate-1", "score": 40, "effective_score": 40, "status": "active", "viability_score": 18, "build_viability": "high", "smoke_viability": "high", "callable_signal": "likely-callable"},
                            {"candidate_id": "candidate-2", "score": 40, "effective_score": 40, "status": "active", "viability_score": 2, "build_viability": "low", "smoke_viability": "low", "callable_signal": "uncertain"}
                        ]
                    }
                ),
                encoding="utf-8",
            )

            strong = hermes_watch.compute_refiner_queue_weight(
                {"action_code": "shift_weight_to_deeper_harness", "selected_candidate_id": "candidate-1"},
                automation_dir=root,
                repo_root=repo_root,
            )
            weak = hermes_watch.compute_refiner_queue_weight(
                {"action_code": "shift_weight_to_deeper_harness", "selected_candidate_id": "candidate-2"},
                automation_dir=root,
                repo_root=repo_root,
            )

            self.assertGreater(strong["queue_weight"], weak["queue_weight"])
            self.assertTrue(any("candidate-viability" in reason for reason in strong["queue_reasons"]))

    def test_compute_refiner_queue_weight_rewards_measured_execution_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            candidate_registry_dir = repo_root / "fuzz-records" / "harness-candidates"
            candidate_registry_dir.mkdir(parents=True)
            (candidate_registry_dir / "ranked-candidates.json").write_text(
                json.dumps(
                    {
                        "project": "repo",
                        "candidates": [
                            {"candidate_id": "candidate-1", "score": 40, "effective_score": 48, "execution_evidence_score": 14, "status": "active"},
                            {"candidate_id": "candidate-2", "score": 40, "effective_score": 40, "execution_evidence_score": 0, "status": "active"}
                        ]
                    }
                ),
                encoding="utf-8",
            )

            strong = hermes_watch.compute_refiner_queue_weight(
                {"action_code": "shift_weight_to_deeper_harness", "selected_candidate_id": "candidate-1"},
                automation_dir=root,
                repo_root=repo_root,
            )
            weak = hermes_watch.compute_refiner_queue_weight(
                {"action_code": "shift_weight_to_deeper_harness", "selected_candidate_id": "candidate-2"},
                automation_dir=root,
                repo_root=repo_root,
            )

            self.assertGreater(strong["queue_weight"], weak["queue_weight"])
            self.assertTrue(any("candidate-evidence" in reason for reason in strong["queue_reasons"]))


class HermesWatchRefinerOrchestrationTests(unittest.TestCase):
    def test_prepare_next_refiner_orchestration_creates_subagent_bundle_for_mode_refinement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            registry_path = root / "mode_refinements.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "shift_weight_to_deeper_harness:/runs/one",
                                "action_code": "shift_weight_to_deeper_harness",
                                "run_dir": "/runs/one",
                                "report_path": "/runs/one/FUZZING_REPORT.md",
                                "current_mode": "parser",
                                "next_mode": "deep-decode-v3",
                                "recommended_action": "Shift weight to deeper harness.",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.prepare_next_refiner_orchestration(root, repo_root=repo_root)

            self.assertEqual(result["action_code"], "shift_weight_to_deeper_harness")
            self.assertEqual(result["dispatch_channel"], "subagent")
            manifest_path = repo_root / "fuzz-records" / "refiner-orchestration" / "shift_weight_to_deeper_harness-runs-one.json"
            self.assertTrue(manifest_path.exists())
            prompt_path = repo_root / "fuzz-records" / "refiner-orchestration" / "shift_weight_to_deeper_harness-runs-one-subagent.txt"
            self.assertTrue(prompt_path.exists())
            self.assertIn("deep-decode-v3", prompt_path.read_text(encoding="utf-8"))

            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["orchestration_status"], "prepared")
            self.assertEqual(entry["dispatch_channel"], "subagent")

    def test_prepare_next_refiner_orchestration_creates_cron_bundle_for_corpus_refinement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            registry_path = root / "corpus_refinements.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "minimize_and_reseed:/runs/corpus",
                                "action_code": "minimize_and_reseed",
                                "run_dir": "/runs/corpus",
                                "report_path": "/runs/corpus/FUZZING_REPORT.md",
                                "recommended_action": "Minimize and reseed the corpus.",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.prepare_next_refiner_orchestration(root, repo_root=repo_root)

            self.assertEqual(result["action_code"], "minimize_and_reseed")
            self.assertEqual(result["dispatch_channel"], "cron")
            cron_prompt = repo_root / "fuzz-records" / "refiner-orchestration" / "minimize_and_reseed-runs-corpus-cron.txt"
            self.assertTrue(cron_prompt.exists())
            self.assertIn("self-contained", cron_prompt.read_text(encoding="utf-8"))

            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["orchestration_status"], "prepared")
            self.assertEqual(entry["dispatch_channel"], "cron")

    def test_prepare_next_refiner_orchestration_includes_duplicate_replay_context_for_corpus_refinement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            registry_path = root / "corpus_refinements.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "minimize_and_reseed:/runs/corpus",
                                "action_code": "minimize_and_reseed",
                                "run_dir": "/runs/corpus",
                                "report_path": "/runs/corpus/FUZZING_REPORT.md",
                                "recommended_action": "Minimize and reseed the duplicate family.",
                                "candidate_route": "reseed-before-retry",
                                "derived_from_action_code": "review_duplicate_crash_replay",
                                "duplicate_replay_source_key": "review_duplicate_crash_replay:asan|j2kmarkers.cpp:52|heap-buffer-overflow",
                                "first_artifact_path": "/runs/dup-first/crashes/crash-a",
                                "latest_artifact_path": "/runs/dup-latest/crashes/crash-c",
                                "replay_execution_markdown_path": "/records/dup-replay.md",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            hermes_watch.prepare_next_refiner_orchestration(root, repo_root=repo_root)

            cron_prompt = repo_root / "fuzz-records" / "refiner-orchestration" / "minimize_and_reseed-runs-corpus-cron.txt"
            prompt_text = cron_prompt.read_text(encoding="utf-8")
            self.assertIn("candidate_route: reseed-before-retry", prompt_text)
            self.assertIn("derived_from_action_code: review_duplicate_crash_replay", prompt_text)
            self.assertIn("duplicate_replay_source_key: review_duplicate_crash_replay:asan|j2kmarkers.cpp:52|heap-buffer-overflow", prompt_text)
            self.assertIn("first_artifact_path: /runs/dup-first/crashes/crash-a", prompt_text)
            self.assertIn("replay_execution_markdown_path: /records/dup-replay.md", prompt_text)

    def test_prepare_next_refiner_orchestration_returns_none_when_no_pending_work_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            (root / "mode_refinements.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "done",
                                "action_code": "shift_weight_to_deeper_harness",
                                "run_dir": "/runs/done",
                                "status": "completed",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.prepare_next_refiner_orchestration(root, repo_root=repo_root)

            self.assertIsNone(result)


class HermesWatchRefinerDispatchDraftTests(unittest.TestCase):
    def test_dispatch_next_refiner_orchestration_writes_delegate_task_request(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            registry_path = root / "mode_refinements.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "shift_weight_to_deeper_harness:/runs/one",
                                "action_code": "shift_weight_to_deeper_harness",
                                "run_dir": "/runs/one",
                                "status": "completed",
                                "orchestration_status": "prepared",
                                "dispatch_channel": "subagent",
                                "executor_plan_path": "/tmp/plan.md",
                                "subagent_prompt_path": "/tmp/subagent.txt",
                                "cron_prompt_path": "/tmp/cron.txt",
                                "selected_candidate_id": "candidate-2",
                                "selected_entrypoint_path": "src/decode_input.c",
                                "selected_recommended_mode": "decode",
                                "selected_target_stage": "decode",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.dispatch_next_refiner_orchestration(root, repo_root=repo_root)

            self.assertEqual(result["dispatch_channel"], "subagent")
            request_path = repo_root / "fuzz-records" / "refiner-dispatch" / "shift_weight_to_deeper_harness-runs-one-delegate-request.json"
            self.assertTrue(request_path.exists())
            request = json.loads(request_path.read_text(encoding="utf-8"))
            self.assertEqual(request["goal"], "Review the latest shallow-heavy run and propose a deeper harness/mode shift plan.")
            self.assertIn("terminal", request["toolsets"])
            self.assertIn("selected_candidate_id: candidate-2", request["context"])
            self.assertIn("selected_entrypoint_path: src/decode_input.c", request["context"])

            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["dispatch_status"], "ready")
            self.assertEqual(entry["delegate_task_request_path"], str(request_path))

    def test_dispatch_next_refiner_orchestration_writes_cronjob_request(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            registry_path = root / "corpus_refinements.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "minimize_and_reseed:/runs/corpus",
                                "action_code": "minimize_and_reseed",
                                "run_dir": "/runs/corpus",
                                "status": "completed",
                                "orchestration_status": "prepared",
                                "dispatch_channel": "cron",
                                "executor_plan_path": "/tmp/plan.md",
                                "subagent_prompt_path": "/tmp/subagent.txt",
                                "cron_prompt_path": "/tmp/cron.txt",
                                "selected_candidate_id": "candidate-3",
                                "selected_entrypoint_path": "src/reseed_input.c",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.dispatch_next_refiner_orchestration(root, repo_root=repo_root)

            self.assertEqual(result["dispatch_channel"], "cron")
            request_path = repo_root / "fuzz-records" / "refiner-dispatch" / "minimize_and_reseed-runs-corpus-cronjob-request.json"
            self.assertTrue(request_path.exists())
            request = json.loads(request_path.read_text(encoding="utf-8"))
            self.assertEqual(request["action"], "create")
            self.assertEqual(request["deliver"], "local")
            self.assertTrue(request["name"].startswith("refiner-minimize_and_reseed"))
            self.assertIn("candidate-3", request["prompt"])
            self.assertIn("src/reseed_input.c", request["prompt"])

            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["dispatch_status"], "ready")
            self.assertEqual(entry["cronjob_request_path"], str(request_path))

    def test_dispatch_next_refiner_orchestration_returns_none_when_nothing_prepared(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            (root / "harness_review_queue.json").write_text(
                json.dumps({"entries": [{"key": "x", "action_code": "halt_and_review_harness", "status": "completed"}]}),
                encoding="utf-8",
            )

            result = hermes_watch.dispatch_next_refiner_orchestration(root, repo_root=repo_root)

            self.assertIsNone(result)

    def test_dispatch_next_refiner_orchestration_prefers_higher_queue_weight_prepared_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            (root / "mode_refinements.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "shift_weight_to_deeper_harness:/runs/one",
                                "action_code": "shift_weight_to_deeper_harness",
                                "run_dir": "/runs/one",
                                "status": "completed",
                                "orchestration_status": "prepared",
                                "dispatch_channel": "subagent",
                                "executor_plan_path": "/tmp/plan-one.md",
                                "subagent_prompt_path": "/tmp/subagent-one.txt",
                                "cron_prompt_path": "/tmp/cron-one.txt",
                                "selected_candidate_id": "candidate-1",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / "harness_review_queue.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "halt_and_review_harness:/runs/review",
                                "action_code": "halt_and_review_harness",
                                "run_dir": "/runs/review",
                                "status": "completed",
                                "orchestration_status": "prepared",
                                "dispatch_channel": "subagent",
                                "executor_plan_path": "/tmp/plan-review.md",
                                "subagent_prompt_path": "/tmp/subagent-review.txt",
                                "cron_prompt_path": "/tmp/cron-review.txt",
                                "selected_candidate_id": "candidate-2",
                                "selected_candidate_status": "review_required",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            candidate_registry_dir = repo_root / "fuzz-records" / "harness-candidates"
            candidate_registry_dir.mkdir(parents=True)
            (candidate_registry_dir / "ranked-candidates.json").write_text(
                json.dumps(
                    {
                        "project": "repo",
                        "candidates": [
                            {"candidate_id": "candidate-1", "score": 24, "effective_score": 12, "status": "active", "rank": 1},
                            {"candidate_id": "candidate-2", "score": 60, "effective_score": 48, "status": "review_required", "rank": 2},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.dispatch_next_refiner_orchestration(root, repo_root=repo_root)

            self.assertEqual(result["action_code"], "halt_and_review_harness")
            self.assertEqual(result["dispatch_channel"], "subagent")
            registry = json.loads((root / "harness_review_queue.json").read_text(encoding="utf-8"))
            self.assertEqual(registry["entries"][0]["dispatch_status"], "ready")
            self.assertEqual(registry["entries"][0]["queue_rank"], 1)


class HermesWatchRefinerBridgeDraftTests(unittest.TestCase):
    def test_bridge_next_refiner_dispatch_writes_delegate_bridge_script(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            dispatch_dir = repo_root / "fuzz-records" / "refiner-dispatch"
            dispatch_dir.mkdir(parents=True)
            request_path = dispatch_dir / "shift_weight_to_deeper_harness-runs-one-delegate-request.json"
            request_path.write_text(
                json.dumps(
                    {
                        "goal": "Review the latest shallow-heavy run and propose a deeper harness/mode shift plan.",
                        "context": "repo_root: /tmp/repo\n",
                        "toolsets": ["terminal", "file"],
                        "skills": ["subagent-driven-development"],
                    }
                ),
                encoding="utf-8",
            )
            registry_path = root / "mode_refinements.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "shift_weight_to_deeper_harness:/runs/one",
                                "action_code": "shift_weight_to_deeper_harness",
                                "run_dir": "/runs/one",
                                "dispatch_status": "ready",
                                "dispatch_channel": "subagent",
                                "delegate_task_request_path": str(request_path),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.bridge_next_refiner_dispatch(root, repo_root=repo_root)

            self.assertEqual(result["bridge_channel"], "hermes-cli-delegate")
            script_path = repo_root / "fuzz-records" / "refiner-bridge" / "shift_weight_to_deeper_harness-runs-one-delegate-bridge.sh"
            prompt_path = repo_root / "fuzz-records" / "refiner-bridge" / "shift_weight_to_deeper_harness-runs-one-delegate-bridge-prompt.txt"
            self.assertTrue(script_path.exists())
            self.assertTrue(prompt_path.exists())
            self.assertIn("delegate_task", prompt_path.read_text(encoding="utf-8"))
            self.assertIn("hermes chat -q", script_path.read_text(encoding="utf-8"))

            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["bridge_status"], "armed")
            self.assertEqual(entry["bridge_script_path"], str(script_path))

    def test_bridge_next_refiner_dispatch_writes_cron_bridge_script(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            dispatch_dir = repo_root / "fuzz-records" / "refiner-dispatch"
            dispatch_dir.mkdir(parents=True)
            request_path = dispatch_dir / "minimize_and_reseed-runs-corpus-cronjob-request.json"
            request_path.write_text(
                json.dumps(
                    {
                        "action": "create",
                        "name": "refiner-minimize_and_reseed-runs-corpus",
                        "schedule": "30m",
                        "repeat": 1,
                        "deliver": "local",
                        "prompt": "This is a self-contained refiner follow-up prompt.",
                    }
                ),
                encoding="utf-8",
            )
            registry_path = root / "corpus_refinements.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "minimize_and_reseed:/runs/corpus",
                                "action_code": "minimize_and_reseed",
                                "run_dir": "/runs/corpus",
                                "dispatch_status": "ready",
                                "dispatch_channel": "cron",
                                "cronjob_request_path": str(request_path),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.bridge_next_refiner_dispatch(root, repo_root=repo_root)

            self.assertEqual(result["bridge_channel"], "hermes-cli-cron")
            script_path = repo_root / "fuzz-records" / "refiner-bridge" / "minimize_and_reseed-runs-corpus-cron-bridge.sh"
            self.assertTrue(script_path.exists())
            self.assertIn("hermes cron create", script_path.read_text(encoding="utf-8"))

            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["bridge_status"], "armed")
            self.assertEqual(entry["bridge_script_path"], str(script_path))

    def test_bridge_next_refiner_dispatch_returns_none_when_nothing_ready(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            (root / "corpus_refinements.json").write_text(
                json.dumps({"entries": [{"key": "x", "action_code": "minimize_and_reseed", "dispatch_status": "completed"}]}),
                encoding="utf-8",
            )

            result = hermes_watch.bridge_next_refiner_dispatch(root, repo_root=repo_root)

            self.assertIsNone(result)


class HermesWatchAutonomousSupervisorTests(unittest.TestCase):
    def test_write_autonomous_supervisor_bundle_writes_prompt_and_script(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            repo_root.mkdir()

            result = hermes_watch.write_autonomous_supervisor_bundle(
                repo_root,
                sleep_seconds=45,
                channel_id="1493631285027934419",
            )

            prompt_path = Path(result["prompt_path"])
            script_path = Path(result["script_path"])
            self.assertTrue(prompt_path.exists())
            self.assertTrue(script_path.exists())
            self.assertIn("1493631285027934419", prompt_path.read_text(encoding="utf-8"))
            script_text = script_path.read_text(encoding="utf-8")
            self.assertIn("hermes chat -q", script_text)
            self.assertIn("SLEEP_SECONDS=45", script_text)
            self.assertIn("STOP_PATH=", script_text)

    def test_autonomous_supervisor_script_keeps_hermes_error_lines_out_of_stdout_watch_stream(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            repo_root.mkdir()
            result = hermes_watch.write_autonomous_supervisor_bundle(
                repo_root,
                sleep_seconds=10,
                channel_id="1493631285027934419",
            )
            script_path = Path(result["script_path"])
            stop_path = Path(result["stop_path"])
            log_path = Path(result["log_path"])
            fake_bin = Path(tmpdir) / "bin"
            fake_bin.mkdir()
            fake_hermes = fake_bin / "hermes"
            fake_hermes.write_text(
                "#!/usr/bin/env bash\n"
                f"touch '{stop_path}'\n"
                "printf '==1==ERROR: LeakSanitizer: detected memory leaks\\n'\n"
                "printf 'SUMMARY: AddressSanitizer: 12312 byte(s) leaked in 1 allocation(s).\\n'\n",
                encoding="utf-8",
            )
            fake_hermes.chmod(0o755)
            script_text = script_path.read_text(encoding="utf-8").replace('  sleep "$SLEEP_SECONDS"', '  sleep 0')
            script_path.write_text(script_text, encoding="utf-8")

            completed = subprocess.run(
                ["bash", str(script_path)],
                capture_output=True,
                text=True,
                env={**hermes_watch.os.environ, "PATH": f"{fake_bin}:{hermes_watch.os.environ.get('PATH', '')}"},
                check=False,
            )

            self.assertEqual(completed.returncode, 0)
            self.assertNotIn("LeakSanitizer", completed.stdout)
            self.assertNotIn("ERROR:", completed.stdout)
            self.assertIn("LeakSanitizer", log_path.read_text(encoding="utf-8"))

    def test_main_prepare_autonomous_supervisor_writes_bundle_and_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            repo_root.mkdir()
            original_argv = list(hermes_watch.sys.argv)
            try:
                hermes_watch.sys.argv = [
                    "hermes_watch.py",
                    "--repo",
                    str(repo_root),
                    "--prepare-autonomous-supervisor",
                    "--autonomous-supervisor-sleep-seconds",
                    "15",
                    "--autonomous-supervisor-channel-id",
                    "1493631285027934419",
                ]
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv

            self.assertEqual(exit_code, 0)
            bundle_dir = repo_root / "fuzz-records" / "autonomous-supervisor"
            self.assertTrue((bundle_dir / "autonomous-dev-loop-prompt.txt").exists())
            self.assertTrue((bundle_dir / "autonomous-dev-loop.sh").exists())

    def test_main_repair_latest_crash_state_returns_zero_for_stale_leak(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            run_dir = repo_root / "fuzz-artifacts" / "runs" / "run-1"
            automation_dir = repo_root / "fuzz-artifacts" / "automation"
            run_dir.mkdir(parents=True)
            automation_dir.mkdir(parents=True)
            artifact_path = run_dir / "crashes" / "leak-deadbeef"
            artifact_path.parent.mkdir(parents=True)
            artifact_path.write_text("boom", encoding="utf-8")
            report_path = run_dir / "FUZZING_REPORT.md"
            report_path.write_text("# report\n", encoding="utf-8")
            (run_dir / "fuzz.log").write_text(
                "==1==ERROR: LeakSanitizer: detected memory leaks\n"
                f"    #0 0xccc in j2k_tile::decode() {repo_root}/source/core/coding/coding_units.cpp:3927:53\n"
                "SUMMARY: AddressSanitizer: 12312 byte(s) leaked in 1 allocation(s).\n"
                f"artifact_prefix='{artifact_path.parent}/'; Test unit written to {artifact_path}\n",
                encoding="utf-8",
            )
            stale_snapshot = {
                "outcome": "crash",
                "run_dir": str(run_dir),
                "report": str(report_path),
                "updated_at": "2026-04-16T18:34:44",
                "crash_detected": True,
                "timeout_detected": False,
                "crash_fingerprint": "asan|unknown-location|12312 byte(s) leaked in 1 allocation(s).",
                "crash_kind": "asan",
                "artifact_category": "crash",
                "artifact_reason": "sanitizer-crash",
                "policy_action_code": "triage-new-crash",
                "target_profile_path": str(repo_root / "fuzz-records" / "profiles" / "openhtj2k-target-profile-v1.yaml"),
            }
            (repo_root / "fuzz-artifacts" / "current_status.json").write_text(json.dumps(stale_snapshot), encoding="utf-8")
            (run_dir / "status.json").write_text(json.dumps(stale_snapshot), encoding="utf-8")
            (repo_root / "fuzz-artifacts" / "crash_index.json").write_text(
                json.dumps({"fingerprints": {stale_snapshot["crash_fingerprint"]: {"occurrence_count": 1, "first_seen_run": str(run_dir), "first_seen_report": str(report_path), "last_seen_run": str(run_dir), "last_seen_report": str(report_path), "artifacts": [str(artifact_path)]}}}),
                encoding="utf-8",
            )
            (automation_dir / "run_history.json").write_text(json.dumps({"entries": []}), encoding="utf-8")

            original_load = hermes_watch.load_target_profile
            original_argv = list(hermes_watch.sys.argv)
            try:
                hermes_watch.load_target_profile = lambda _path: {
                    "stages": [{"id": "tile-decode", "stage_class": "deep", "depth_rank": 4}],
                    "telemetry": {"stack_tagging": {"stage_file_map": {"tile-decode": ["source/core/coding/coding_units.cpp"]}}},
                }
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--repair-latest-crash-state"]
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.load_target_profile = original_load
                hermes_watch.sys.argv = original_argv

            self.assertEqual(exit_code, 0)
            repaired_status = json.loads((repo_root / "fuzz-artifacts" / "current_status.json").read_text(encoding="utf-8"))
            self.assertEqual(repaired_status["artifact_category"], "leak")

    def test_main_queue_latest_evidence_review_followup_returns_zero_for_review_route(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            (repo_root / "fuzz-artifacts" / "automation").mkdir(parents=True)
            evidence_dir = repo_root / "fuzz-records" / "llm-evidence"
            evidence_dir.mkdir(parents=True)
            evidence_path = evidence_dir / "repo-llm-evidence.json"
            evidence_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "repo",
                        "llm_evidence_json_path": str(evidence_path),
                        "llm_evidence_markdown_path": str(evidence_dir / "repo-llm-evidence.md"),
                        "suggested_action_code": "halt_and_review_harness",
                        "suggested_candidate_route": "review-current-candidate",
                        "objective_routing_linkage_summary": "override=deep-stage-crash-already-reached",
                        "top_failure_reason_narrative": "primary deep crash family already reached",
                        "current_status": {"run_dir": "/runs/deep-critical", "report": "/runs/deep-critical/FUZZING_REPORT.md", "outcome": "crash", "crash_fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow"},
                    }
                ),
                encoding="utf-8",
            )
            original_argv = list(hermes_watch.sys.argv)
            try:
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--queue-latest-evidence-review-followup"]
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv

            self.assertEqual(exit_code, 0)
            registry = json.loads((repo_root / "fuzz-artifacts" / "automation" / "harness_review_queue.json").read_text(encoding="utf-8"))
            self.assertEqual(registry["entries"][0]["action_code"], "halt_and_review_harness")

    def test_main_run_latest_evidence_review_followup_chain_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            (repo_root / "fuzz-artifacts" / "automation").mkdir(parents=True)
            evidence_dir = repo_root / "fuzz-records" / "llm-evidence"
            evidence_dir.mkdir(parents=True)
            evidence_path = evidence_dir / "repo-llm-evidence.json"
            evidence_path.write_text(
                json.dumps(
                    {
                        "generated_from_project": "repo",
                        "llm_evidence_json_path": str(evidence_path),
                        "llm_evidence_markdown_path": str(evidence_dir / "repo-llm-evidence.md"),
                        "suggested_action_code": "halt_and_review_harness",
                        "suggested_candidate_route": "review-current-candidate",
                        "objective_routing_linkage_summary": "override=deep-stage-crash-already-reached",
                        "top_failure_reason_narrative": "primary deep crash family already reached",
                        "current_status": {"run_dir": "/runs/deep-critical", "report": "/runs/deep-critical/FUZZING_REPORT.md", "outcome": "crash", "crash_fingerprint": "asan|j2kmarkers.cpp:52|heap-buffer-overflow"},
                    }
                ),
                encoding="utf-8",
            )
            original_launch = hermes_watch.launch_bridge_script
            original_argv = list(hermes_watch.sys.argv)
            try:
                hermes_watch.launch_bridge_script = lambda _script_path, **_kwargs: {
                    "exit_code": 0,
                    "output": "Child session: child-123\nDelegate status: success\nArtifact path: /tmp/review-artifact.md\nSummary: review-ready\n",
                }
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--run-latest-evidence-review-followup-chain"]
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.launch_bridge_script = original_launch
                hermes_watch.sys.argv = original_argv

            self.assertEqual(exit_code, 0)
            registry = json.loads((repo_root / "fuzz-artifacts" / "automation" / "harness_review_queue.json").read_text(encoding="utf-8"))
            self.assertEqual(registry["entries"][0]["launch_status"], "succeeded")


class HermesWatchRuntimeHardeningTests(unittest.TestCase):
    def test_launch_bridge_script_returns_timeout_result_when_subprocess_hangs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "bridge.sh"
            script_path.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            original_run = hermes_watch.subprocess.run

            def fake_run(*args, **kwargs):
                raise hermes_watch.subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout", 0))

            try:
                hermes_watch.subprocess.run = fake_run
                result = hermes_watch.launch_bridge_script(script_path)
            finally:
                hermes_watch.subprocess.run = original_run

            self.assertEqual(result["exit_code"], 124)
            self.assertIn("timed out", result["output"])

    def test_run_probe_command_returns_timeout_result_when_subprocess_hangs(self):
        original_run = hermes_watch.subprocess.run

        def fake_run(*args, **kwargs):
            raise hermes_watch.subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout", 0))

        try:
            hermes_watch.subprocess.run = fake_run
            exit_code, output = hermes_watch.run_probe_command(["bash", "-lc", "sleep 999"])
        finally:
            hermes_watch.subprocess.run = original_run

        self.assertEqual(exit_code, 124)
        self.assertIn("timed out", output)

    def test_main_uses_safe_default_when_env_int_is_invalid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "sample-target"
            (repo_root / "src").mkdir(parents=True)
            (repo_root / "CMakeLists.txt").write_text("project(sample_target)\n", encoding="utf-8")
            (repo_root / "src" / "parse_input.cpp").write_text("int parse_input() { return 0; }\n", encoding="utf-8")

            original_argv = list(hermes_watch.sys.argv)
            previous = {name: hermes_watch.os.environ.get(name) for name in ("MAX_TOTAL_TIME", "NO_PROGRESS_SECONDS", "PROGRESS_INTERVAL_SECONDS")}
            hermes_watch.os.environ["MAX_TOTAL_TIME"] = "not-an-int"
            hermes_watch.os.environ["NO_PROGRESS_SECONDS"] = "also-bad"
            hermes_watch.os.environ["PROGRESS_INTERVAL_SECONDS"] = "still-bad"
            try:
                hermes_watch.sys.argv = ["hermes_watch.py", "--repo", str(repo_root), "--draft-target-profile"]
                exit_code = hermes_watch.main()
            finally:
                hermes_watch.sys.argv = original_argv
                for name, value in previous.items():
                    if value is None:
                        hermes_watch.os.environ.pop(name, None)
                    else:
                        hermes_watch.os.environ[name] = value

            self.assertEqual(exit_code, 0)
            self.assertTrue((repo_root / "fuzz-records" / "profiles" / "auto-drafts" / "sample-target-target-recon.json").exists())


class HermesWatchRefinerLauncherDraftTests(unittest.TestCase):
    def test_launch_next_refiner_bridge_executes_script_and_records_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            bridge_dir = repo_root / "fuzz-records" / "refiner-bridge"
            bridge_dir.mkdir(parents=True)
            output_path = bridge_dir / "delegate.out"
            script_path = bridge_dir / "shift_weight_to_deeper_harness-runs-one-delegate-bridge.sh"
            script_path.write_text(
                "#!/usr/bin/env bash\nset -euo pipefail\nprintf 'delegate-ok' > \"{}\"\necho delegate-launched\n".format(output_path),
                encoding="utf-8",
            )
            script_path.chmod(0o755)
            registry_path = root / "mode_refinements.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "shift_weight_to_deeper_harness:/runs/one",
                                "action_code": "shift_weight_to_deeper_harness",
                                "run_dir": "/runs/one",
                                "bridge_status": "armed",
                                "bridge_channel": "hermes-cli-delegate",
                                "bridge_script_path": str(script_path),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.launch_next_refiner_bridge(root, repo_root=repo_root)

            self.assertEqual(result["bridge_status"], "succeeded")
            self.assertEqual(result["exit_code"], 0)
            self.assertTrue(output_path.exists())
            launch_log = Path(result["bridge_launch_log_path"])
            self.assertTrue(launch_log.exists())
            self.assertIn("delegate-launched", launch_log.read_text(encoding="utf-8"))

            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["bridge_status"], "succeeded")
            self.assertEqual(entry["bridge_exit_code"], 0)

    def test_launch_next_refiner_bridge_uses_specified_bridge_timeout_seconds(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            bridge_dir = repo_root / "fuzz-records" / "refiner-bridge"
            bridge_dir.mkdir(parents=True)
            script_path = bridge_dir / "halt_and_review_harness-runs-review-delegate-bridge.sh"
            script_path.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            script_path.chmod(0o755)
            registry_path = root / "harness_review_queue.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "halt_and_review_harness:/runs/review",
                                "action_code": "halt_and_review_harness",
                                "run_dir": "/runs/review",
                                "bridge_status": "armed",
                                "bridge_channel": "hermes-cli-delegate",
                                "bridge_script_path": str(script_path),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            observed = {}
            original_launch = hermes_watch.launch_bridge_script
            try:
                def fake_launch(path, *, timeout_seconds=0):
                    observed["timeout_seconds"] = timeout_seconds
                    return {"exit_code": 0, "output": "Child session: child-123\nDelegate status: success\nSummary: review-ready\n"}
                hermes_watch.launch_bridge_script = fake_launch
                result = hermes_watch.launch_next_refiner_bridge(root, repo_root=repo_root)
            finally:
                hermes_watch.launch_bridge_script = original_launch

            self.assertEqual(result["bridge_status"], "succeeded")
            self.assertEqual(observed["timeout_seconds"], 600)

    def test_launch_next_refiner_bridge_records_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            bridge_dir = repo_root / "fuzz-records" / "refiner-bridge"
            bridge_dir.mkdir(parents=True)
            script_path = bridge_dir / "minimize_and_reseed-runs-corpus-cron-bridge.sh"
            script_path.write_text(
                "#!/usr/bin/env bash\nset -euo pipefail\necho bridge-failed >&2\nexit 7\n",
                encoding="utf-8",
            )
            script_path.chmod(0o755)
            registry_path = root / "corpus_refinements.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "minimize_and_reseed:/runs/corpus",
                                "action_code": "minimize_and_reseed",
                                "run_dir": "/runs/corpus",
                                "bridge_status": "armed",
                                "bridge_channel": "hermes-cli-cron",
                                "bridge_script_path": str(script_path),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.launch_next_refiner_bridge(root, repo_root=repo_root)

            self.assertEqual(result["bridge_status"], "failed")
            self.assertEqual(result["exit_code"], 7)
            launch_log = Path(result["bridge_launch_log_path"])
            self.assertTrue(launch_log.exists())
            self.assertIn("bridge-failed", launch_log.read_text(encoding="utf-8"))

            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["bridge_status"], "failed")
            self.assertEqual(entry["bridge_exit_code"], 7)

    def test_launch_next_refiner_bridge_parses_cron_job_id_and_registry_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            bridge_dir = repo_root / "fuzz-records" / "refiner-bridge"
            bridge_dir.mkdir(parents=True)
            script_path = bridge_dir / "split_slow_lane-runs-slow-cron-bridge.sh"
            script_path.write_text(
                "#!/usr/bin/env bash\nset -euo pipefail\necho 'Created cron job: job_123abc'\n",
                encoding="utf-8",
            )
            script_path.chmod(0o755)
            registry_path = root / "slow_lane_candidates.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "split_slow_lane:/runs/slow",
                                "action_code": "split_slow_lane",
                                "run_dir": "/runs/slow",
                                "bridge_status": "armed",
                                "bridge_channel": "hermes-cli-cron",
                                "bridge_script_path": str(script_path),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.launch_next_refiner_bridge(root, repo_root=repo_root)

            self.assertEqual(result["bridge_status"], "succeeded")
            self.assertEqual(result["cron_job_id"], "job_123abc")

            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["cron_job_id"], "job_123abc")
            self.assertEqual(entry["bridge_result_summary"], "cron-job-created")

    def test_launch_next_refiner_bridge_parses_delegate_child_result_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            bridge_dir = repo_root / "fuzz-records" / "refiner-bridge"
            bridge_dir.mkdir(parents=True)
            artifact_path = repo_root / "fuzz-records" / "delegate-notes" / "review-note.md"
            script_path = bridge_dir / "halt_and_review_harness-runs-review-delegate-bridge.sh"
            script_path.write_text(
                "#!/usr/bin/env bash\nset -euo pipefail\ncat <<'EOF'\nDelegate status: success\nChild session: session_987xyz\nArtifact path: {}\nSummary: harness review note emitted\nEOF\n".format(artifact_path),
                encoding="utf-8",
            )
            script_path.chmod(0o755)
            registry_path = root / "harness_review_queue.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "halt_and_review_harness:/runs/review",
                                "action_code": "halt_and_review_harness",
                                "run_dir": "/runs/review",
                                "bridge_status": "armed",
                                "bridge_channel": "hermes-cli-delegate",
                                "bridge_script_path": str(script_path),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.launch_next_refiner_bridge(root, repo_root=repo_root)

            self.assertEqual(result["bridge_status"], "succeeded")
            self.assertEqual(result["delegate_session_id"], "session_987xyz")
            self.assertEqual(result["delegate_status"], "success")
            self.assertEqual(result["delegate_artifact_path"], str(artifact_path))
            self.assertIn("harness review note emitted", result["delegate_summary"])

            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["delegate_session_id"], "session_987xyz")
            self.assertEqual(entry["delegate_status"], "success")
            self.assertEqual(entry["delegate_artifact_path"], str(artifact_path))
            self.assertIn("harness review note emitted", entry["delegate_summary"])

    def test_launch_next_refiner_bridge_returns_none_when_nothing_armed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            (root / "harness_review_queue.json").write_text(
                json.dumps({"entries": [{"key": "x", "action_code": "halt_and_review_harness", "bridge_status": "completed"}]}),
                encoding="utf-8",
            )

            result = hermes_watch.launch_next_refiner_bridge(root, repo_root=repo_root)

            self.assertIsNone(result)


class HermesWatchRefinerVerificationDraftTests(unittest.TestCase):
    def test_verify_next_refiner_result_confirms_cron_job_existence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            registry_path = root / "slow_lane_candidates.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "split_slow_lane:/runs/slow",
                                "action_code": "split_slow_lane",
                                "run_dir": "/runs/slow",
                                "bridge_status": "succeeded",
                                "bridge_channel": "hermes-cli-cron",
                                "cron_job_id": "job_123abc",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            def probe(command: list[str], cwd: Path | None = None) -> tuple[int, str]:
                self.assertEqual(command, ["hermes", "cron", "list", "--all"])
                return 0, "Created cron job: irrelevant\njob_123abc [active]\n"

            result = hermes_watch.verify_next_refiner_result(root, repo_root=repo_root, probe_runner=probe)

            self.assertEqual(result["verification_status"], "verified")
            self.assertTrue(result["cron_job_verified"])

            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["verification_status"], "verified")
            self.assertTrue(entry["cron_job_verified"])
            self.assertEqual(entry["verification_summary"], "cron-job-visible")

    def test_verify_next_refiner_result_confirms_cron_metadata_shape(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            prompt_path = repo_root / "fuzz-records" / "refiner-orchestration" / "minimize_and_reseed-runs-corpus-cron.txt"
            prompt_path.parent.mkdir(parents=True)
            prompt_path.write_text(
                "Action code: minimize_and_reseed\nrun_dir: /runs/corpus\nrecommended_action: Minimize and reseed the corpus.\n",
                encoding="utf-8",
            )
            registry_path = root / "corpus_refinements.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "minimize_and_reseed:/runs/corpus",
                                "action_code": "minimize_and_reseed",
                                "run_dir": "/runs/corpus",
                                "bridge_status": "succeeded",
                                "bridge_channel": "hermes-cli-cron",
                                "cron_job_id": "job_abc999",
                                "dispatch_channel": "cron",
                                "cron_schedule": "30m",
                                "cron_deliver": "local",
                                "cron_name": "refiner-minimize_and_reseed-runs-corpus",
                                "cron_prompt_path": str(prompt_path),
                                "cron_prompt_lineage_tokens": ["minimize_and_reseed", "/runs/corpus", "Minimize and reseed the corpus."],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            def probe(command: list[str], cwd: Path | None = None) -> tuple[int, str]:
                self.assertEqual(command, ["hermes", "cron", "list", "--all"])
                return 0, (
                    "job_abc999 [active]\n"
                    "  Name:      refiner-minimize_and_reseed-runs-corpus\n"
                    "  Schedule:  30m\n"
                    "  Deliver:   local\n"
                )

            result = hermes_watch.verify_next_refiner_result(root, repo_root=repo_root, probe_runner=probe)

            self.assertEqual(result["verification_status"], "verified")
            self.assertTrue(result["cron_metadata_verified"])
            self.assertTrue(result["cron_prompt_lineage_verified"])
            self.assertEqual(result["verification_summary"], "cron-job-metadata-and-lineage-visible")

            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertTrue(entry["cron_metadata_verified"])
            self.assertTrue(entry["cron_prompt_lineage_verified"])
            self.assertEqual(entry["verification_summary"], "cron-job-metadata-and-lineage-visible")

    def test_verify_next_refiner_result_confirms_delegate_artifact_and_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            artifact_path = repo_root / "fuzz-records" / "delegate-notes" / "review-note.md"
            artifact_path.parent.mkdir(parents=True)
            artifact_path.write_text("ok", encoding="utf-8")
            registry_path = root / "harness_review_queue.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "halt_and_review_harness:/runs/review",
                                "action_code": "halt_and_review_harness",
                                "run_dir": "/runs/review",
                                "bridge_status": "succeeded",
                                "bridge_channel": "hermes-cli-delegate",
                                "delegate_session_id": "session_987xyz",
                                "delegate_artifact_path": str(artifact_path),
                                "selected_candidate_id": "candidate-4",
                                "selected_entrypoint_path": "src/review_target.c",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            def probe(command: list[str], cwd: Path | None = None) -> tuple[int, str]:
                self.assertEqual(command, ["hermes", "sessions", "list", "--limit", "200"])
                return 0, "Preview  Last Active Src ID\nsomething 1m ago cli session_987xyz\n"

            result = hermes_watch.verify_next_refiner_result(root, repo_root=repo_root, probe_runner=probe)

            self.assertEqual(result["verification_status"], "verified")
            self.assertTrue(result["delegate_session_verified"])
            self.assertTrue(result["delegate_artifact_verified"])
            self.assertEqual(result["selected_candidate_id"], "candidate-4")
            self.assertEqual(result["selected_entrypoint_path"], "src/review_target.c")

            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["verification_status"], "verified")
            self.assertTrue(entry["delegate_session_verified"])
            self.assertTrue(entry["delegate_artifact_verified"])
            self.assertEqual(entry["verification_summary"], "delegate-session-and-artifact-visible")

    def test_verify_next_refiner_result_confirms_delegate_artifact_shape(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            artifact_path = repo_root / "fuzz-records" / "delegate-notes" / "review-note.md"
            artifact_path.parent.mkdir(parents=True)
            artifact_path.write_text(
                "# Harness Review\n\n## Findings\n- shallow duplicate pattern\n\n## Next Steps\n- add deterministic smoke path\n",
                encoding="utf-8",
            )
            registry_path = root / "harness_review_queue.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "halt_and_review_harness:/runs/review",
                                "action_code": "halt_and_review_harness",
                                "run_dir": "/runs/review",
                                "bridge_status": "succeeded",
                                "bridge_channel": "hermes-cli-delegate",
                                "delegate_session_id": "session_987xyz",
                                "delegate_artifact_path": str(artifact_path),
                                "delegate_expected_sections": ["# Harness Review", "## Findings", "## Next Steps"],
                                "delegate_quality_sections": ["## Findings", "## Next Steps"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            def probe(command: list[str], cwd: Path | None = None) -> tuple[int, str]:
                self.assertEqual(command, ["hermes", "sessions", "list", "--limit", "200"])
                return 0, "Preview  Last Active Src ID\nsomething 1m ago cli session_987xyz\n"

            result = hermes_watch.verify_next_refiner_result(root, repo_root=repo_root, probe_runner=probe)

            self.assertEqual(result["verification_status"], "verified")
            self.assertTrue(result["delegate_artifact_shape_verified"])
            self.assertTrue(result["delegate_artifact_quality_verified"])
            self.assertEqual(result["verification_summary"], "delegate-session-artifact-shape-and-quality-visible")

            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertTrue(entry["delegate_artifact_shape_verified"])
            self.assertTrue(entry["delegate_artifact_quality_verified"])
            self.assertEqual(entry["verification_summary"], "delegate-session-artifact-shape-and-quality-visible")

    def test_verify_next_refiner_result_returns_none_when_nothing_succeeded(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            (root / "mode_refinements.json").write_text(
                json.dumps({"entries": [{"key": "x", "action_code": "shift_weight_to_deeper_harness", "bridge_status": "failed"}]}),
                encoding="utf-8",
            )

            result = hermes_watch.verify_next_refiner_result(root, repo_root=repo_root)

            self.assertIsNone(result)


class HermesWatchRefinerRetryEscalationTests(unittest.TestCase):
    def test_apply_verification_failure_policy_closes_retry_feedback_into_candidate_registry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            registry_path = root / "slow_lane_candidates.json"
            registry_path.write_text(
                json.dumps(
                    {"entries": [{
                        "key": "split_slow_lane:/runs/slow",
                        "action_code": "split_slow_lane",
                        "run_dir": "/runs/slow",
                        "verification_status": "unverified",
                        "verification_summary": "cron-job-not-visible",
                        "bridge_channel": "hermes-cli-cron",
                        "selected_candidate_id": "candidate-7",
                        "selected_entrypoint_path": "src/slow_path.c",
                        "selected_candidate_status": "seed_debt",
                    }]}
                ),
                encoding="utf-8",
            )
            candidate_registry_dir = repo_root / "fuzz-records" / "harness-candidates"
            candidate_registry_dir.mkdir(parents=True)
            (candidate_registry_dir / "ranked-candidates.json").write_text(
                json.dumps(
                    {
                        "project": "repo",
                        "candidates": [
                            {
                                "candidate_id": "candidate-7",
                                "entrypoint_path": "src/slow_path.c",
                                "score": 55,
                                "status": "promoted",
                                "rank": 1,
                            },
                            {
                                "candidate_id": "candidate-8",
                                "entrypoint_path": "src/other_path.c",
                                "score": 54,
                                "status": "active",
                                "rank": 2,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verification_failure_policy(root, repo_root=repo_root)

            self.assertEqual(result["policy_decision"], "retry")
            self.assertTrue(result["candidate_registry_updated"])
            registry = json.loads((candidate_registry_dir / "ranked-candidates.json").read_text(encoding="utf-8"))
            candidate = next(item for item in registry["candidates"] if item["candidate_id"] == "candidate-7")
            self.assertEqual(candidate["status"], "seed_debt")
            self.assertEqual(candidate["seed_debt_count"], 1)
            self.assertEqual(candidate["verification_retry_debt"], 1)
            self.assertEqual(candidate["last_verification_policy_decision"], "retry")
            self.assertEqual(candidate["last_verification_policy_reason"], "candidate-seed-debt")
            self.assertLess(candidate["score"], 55)

    def test_apply_verification_failure_policy_closes_escalation_feedback_into_candidate_registry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            registry_path = root / "harness_review_queue.json"
            registry_path.write_text(
                json.dumps(
                    {"entries": [{
                        "key": "halt_and_review_harness:/runs/review",
                        "action_code": "halt_and_review_harness",
                        "run_dir": "/runs/review",
                        "verification_status": "unverified",
                        "verification_summary": "delegate-session-visible-artifact-missing",
                        "bridge_channel": "hermes-cli-delegate",
                        "selected_candidate_id": "candidate-4",
                        "selected_entrypoint_path": "src/review_target.c",
                        "selected_candidate_status": "review_required",
                    }]}
                ),
                encoding="utf-8",
            )
            candidate_registry_dir = repo_root / "fuzz-records" / "harness-candidates"
            candidate_registry_dir.mkdir(parents=True)
            (candidate_registry_dir / "ranked-candidates.json").write_text(
                json.dumps(
                    {
                        "project": "repo",
                        "candidates": [
                            {
                                "candidate_id": "candidate-4",
                                "entrypoint_path": "src/review_target.c",
                                "score": 70,
                                "status": "promoted",
                                "rank": 1,
                            },
                            {
                                "candidate_id": "candidate-5",
                                "entrypoint_path": "src/fallback.c",
                                "score": 63,
                                "status": "active",
                                "rank": 2,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verification_failure_policy(root, repo_root=repo_root)

            self.assertEqual(result["policy_decision"], "escalate")
            self.assertTrue(result["candidate_registry_updated"])
            registry = json.loads((candidate_registry_dir / "ranked-candidates.json").read_text(encoding="utf-8"))
            candidate = next(item for item in registry["candidates"] if item["candidate_id"] == "candidate-4")
            self.assertEqual(candidate["status"], "review_required")
            self.assertEqual(candidate["review_debt_count"], 1)
            self.assertEqual(candidate["verification_escalation_count"], 1)
            self.assertEqual(candidate["last_verification_policy_decision"], "escalate")
            self.assertEqual(candidate["last_verification_policy_reason"], "candidate-review-required")
            self.assertLess(candidate["score"], 70)

    def test_apply_verification_failure_policy_records_reverse_linkage_for_followup_retry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            apply_manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            apply_manifest_path.write_text(json.dumps({"selected_candidate_id": "candidate-1"}), encoding="utf-8")
            registry_path = root / "harness_correction_regeneration_queue.json"
            registry_path.write_text(
                json.dumps(
                    {"entries": [{
                        "key": "regenerate_harness_correction:sample-target:candidate-1",
                        "action_code": "regenerate_harness_correction",
                        "run_dir": "/runs/regenerate",
                        "verification_status": "unverified",
                        "verification_summary": "delegate-session-and-artifact-missing",
                        "bridge_channel": "hermes-cli-delegate",
                        "recovery_followup_reason": "abort-corrective-route",
                        "apply_candidate_manifest_path": str(apply_manifest_path),
                        "selected_candidate_id": "candidate-1",
                    }]}
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verification_failure_policy(root, repo_root=repo_root)

            self.assertEqual(result["policy_decision"], "retry")
            manifest = json.loads(apply_manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["recovery_followup_failure_policy_status"], "retry")
            self.assertEqual(manifest["recovery_followup_failure_policy_reason"], "verification-evidence-missing")
            self.assertEqual(manifest["recovery_followup_failure_action_code"], "regenerate_harness_correction")

    def test_apply_verification_failure_policy_records_reverse_linkage_for_followup_escalation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            apply_dir = repo_root / "fuzz-records" / "harness-apply-candidates"
            apply_dir.mkdir(parents=True)
            apply_manifest_path = apply_dir / "sample-target-candidate-1-harness-apply-candidate.json"
            apply_manifest_path.write_text(json.dumps({"selected_candidate_id": "candidate-1"}), encoding="utf-8")
            registry_path = root / "harness_review_queue.json"
            registry_path.write_text(
                json.dumps(
                    {"entries": [{
                        "key": "halt_and_review_harness:sample-target:candidate-1",
                        "action_code": "halt_and_review_harness",
                        "run_dir": "/runs/review",
                        "verification_status": "unverified",
                        "verification_summary": "delegate-session-artifact-visible-shape-or-quality-missing",
                        "bridge_channel": "hermes-cli-delegate",
                        "recovery_followup_reason": "hold-review-lane",
                        "apply_candidate_manifest_path": str(apply_manifest_path),
                        "selected_candidate_id": "candidate-1",
                    }]}
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verification_failure_policy(root, repo_root=repo_root)

            self.assertEqual(result["policy_decision"], "escalate")
            manifest = json.loads(apply_manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["recovery_followup_failure_policy_status"], "escalate")
            self.assertEqual(manifest["recovery_followup_failure_policy_reason"], "delegate-quality-gap")
            self.assertEqual(manifest["recovery_followup_failure_action_code"], "halt_and_review_harness")

    def test_apply_verification_failure_policy_marks_cron_unverified_as_retry_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            registry_path = root / "slow_lane_candidates.json"
            registry_path.write_text(
                json.dumps(
                    {"entries": [{
                        "key": "split_slow_lane:/runs/slow",
                        "action_code": "split_slow_lane",
                        "run_dir": "/runs/slow",
                        "verification_status": "unverified",
                        "verification_summary": "cron-job-not-visible",
                        "bridge_channel": "hermes-cli-cron",
                        "selected_candidate_id": "candidate-7",
                        "selected_entrypoint_path": "src/slow_path.c",
                        "selected_candidate_status": "promoted",
                    }]}
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verification_failure_policy(root, repo_root=repo_root)

            self.assertEqual(result["policy_decision"], "retry")
            self.assertEqual(result["selected_candidate_id"], "candidate-7")
            retry_path = repo_root / "fuzz-records" / "refiner-policy" / "split_slow_lane-runs-slow-retry.md"
            self.assertTrue(retry_path.exists())
            self.assertIn("candidate-7", retry_path.read_text(encoding="utf-8"))
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["verification_policy_status"], "retry")
            self.assertEqual(entry["verification_retry_count"], 1)

    def test_apply_verification_failure_policy_escalates_review_required_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            registry_path = root / "harness_review_queue.json"
            registry_path.write_text(
                json.dumps(
                    {"entries": [{
                        "key": "halt_and_review_harness:/runs/review",
                        "action_code": "halt_and_review_harness",
                        "run_dir": "/runs/review",
                        "verification_status": "unverified",
                        "verification_summary": "delegate-session-visible-artifact-missing",
                        "bridge_channel": "hermes-cli-delegate",
                        "selected_candidate_id": "candidate-4",
                        "selected_entrypoint_path": "src/review_target.c",
                        "selected_candidate_status": "review_required",
                    }]}
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verification_failure_policy(root, repo_root=repo_root)

            self.assertEqual(result["policy_decision"], "escalate")
            self.assertEqual(result["policy_reason"], "candidate-review-required")
            self.assertEqual(result["selected_candidate_id"], "candidate-4")
            note_path = repo_root / "fuzz-records" / "refiner-policy" / "halt_and_review_harness-runs-review-escalation.md"
            self.assertTrue(note_path.exists())
            self.assertIn("candidate-4", note_path.read_text(encoding="utf-8"))
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["verification_policy_status"], "escalate")
            self.assertEqual(entry["verification_escalation_reason"], "candidate-review-required")

    def test_apply_verification_failure_policy_escalates_delegate_quality_issue(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            registry_path = root / "harness_review_queue.json"
            registry_path.write_text(
                json.dumps(
                    {"entries": [{
                        "key": "halt_and_review_harness:/runs/review",
                        "action_code": "halt_and_review_harness",
                        "run_dir": "/runs/review",
                        "verification_status": "unverified",
                        "verification_summary": "delegate-session-artifact-visible-shape-or-quality-missing",
                        "bridge_channel": "hermes-cli-delegate",
                    }]}
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verification_failure_policy(root, repo_root=repo_root)

            self.assertEqual(result["policy_decision"], "escalate")
            note_path = repo_root / "fuzz-records" / "refiner-policy" / "halt_and_review_harness-runs-review-escalation.md"
            self.assertTrue(note_path.exists())
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["verification_policy_status"], "escalate")
            self.assertEqual(entry["verification_escalation_reason"], "delegate-quality-gap")

    def test_apply_verification_failure_policy_escalates_repeated_cron_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            registry_path = root / "corpus_refinements.json"
            registry_path.write_text(
                json.dumps(
                    {"entries": [{
                        "key": "minimize_and_reseed:/runs/corpus",
                        "action_code": "minimize_and_reseed",
                        "run_dir": "/runs/corpus",
                        "verification_status": "unverified",
                        "verification_summary": "cron-job-not-visible",
                        "bridge_channel": "hermes-cli-cron",
                        "verification_retry_count": 2,
                    }]}
                ),
                encoding="utf-8",
            )

            result = hermes_watch.apply_verification_failure_policy(root, repo_root=repo_root)

            self.assertEqual(result["policy_decision"], "escalate")
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            entry = registry["entries"][0]
            self.assertEqual(entry["verification_policy_status"], "escalate")
            self.assertEqual(entry["verification_escalation_reason"], "retry-budget-exhausted")


if __name__ == "__main__":
    unittest.main()
