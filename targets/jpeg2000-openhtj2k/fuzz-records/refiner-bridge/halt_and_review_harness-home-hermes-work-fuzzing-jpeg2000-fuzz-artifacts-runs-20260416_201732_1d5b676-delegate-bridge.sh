#!/usr/bin/env bash
set -euo pipefail
PROMPT_PATH=/home/hermes/work/fuzzing-jpeg2000/fuzz-records/refiner-bridge/halt_and_review_harness-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_201732_1d5b676-delegate-bridge-prompt.txt
OUTPUT_PATH=/home/hermes/work/fuzzing-jpeg2000/fuzz-records/refiner-bridge/halt_and_review_harness-home-hermes-work-fuzzing-jpeg2000-fuzz-artifacts-runs-20260416_201732_1d5b676-delegate-bridge.log
PROMPT=$(cat "$PROMPT_PATH")
hermes chat -q "$PROMPT" -Q -t delegation,file,terminal,skills -s subagent-driven-development | tee "$OUTPUT_PATH"
