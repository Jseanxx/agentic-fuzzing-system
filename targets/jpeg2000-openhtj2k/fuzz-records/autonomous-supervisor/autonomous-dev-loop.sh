#!/usr/bin/env bash
set -euo pipefail
PROMPT_PATH=/home/hermes/work/fuzzing-jpeg2000/fuzz-records/autonomous-supervisor/autonomous-dev-loop-prompt.txt
LOG_PATH=/home/hermes/work/fuzzing-jpeg2000/fuzz-records/autonomous-supervisor/autonomous-dev-loop.log
STATUS_PATH=/home/hermes/work/fuzzing-jpeg2000/fuzz-records/autonomous-supervisor/autonomous-dev-loop-status.json
STOP_PATH=/home/hermes/work/fuzzing-jpeg2000/fuzz-records/autonomous-supervisor/STOP
SLEEP_SECONDS=60
mkdir -p "$(dirname "$LOG_PATH")"
ITERATION=0
printf "{\"status\": \"prepared\", \"iteration_count\": 0}\n" > "$STATUS_PATH"
while [ ! -f "$STOP_PATH" ]; do
  ITERATION=$((ITERATION + 1))
  STARTED_AT=$(date --iso-8601=seconds)
  python3 - "$STATUS_PATH" "$ITERATION" "$STARTED_AT" <<'PY'
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
payload = {"status": "running", "iteration_count": int(sys.argv[2]), "last_started_at": sys.argv[3]}
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
PY
  PROMPT=$(cat "$PROMPT_PATH")
  ITERATION_OUTPUT=$(mktemp)
  printf "[autonomous-supervisor] iteration=%s status=running started_at=%s\n" "$ITERATION" "$STARTED_AT" | tee -a "$LOG_PATH"
  set +e
  hermes chat -q "$PROMPT" -Q > "$ITERATION_OUTPUT" 2>&1
  EXIT_CODE=$?
  set -e
  cat "$ITERATION_OUTPUT" >> "$LOG_PATH"
  rm -f "$ITERATION_OUTPUT"
  FINISHED_AT=$(date --iso-8601=seconds)
  printf "[autonomous-supervisor] iteration=%s status=finished exit_code=%s finished_at=%s\n" "$ITERATION" "$EXIT_CODE" "$FINISHED_AT" | tee -a "$LOG_PATH"
  python3 - "$STATUS_PATH" "$ITERATION" "$STARTED_AT" "$FINISHED_AT" "$EXIT_CODE" <<'PY'
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
payload = {
    "status": "sleeping",
    "iteration_count": int(sys.argv[2]),
    "last_started_at": sys.argv[3],
    "last_finished_at": sys.argv[4],
    "last_exit_code": int(sys.argv[5]),
}
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
PY
  sleep "$SLEEP_SECONDS"
done
python3 - "$STATUS_PATH" <<'PY'
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
payload = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
payload['status'] = 'stopped'
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
PY
