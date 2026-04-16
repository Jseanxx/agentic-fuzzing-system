# Hermes Watch Leak Closure Evidence Slice v0.1 Checklist

- [x] fresh fuzz artifact state inspected
- [x] latest leak misclassification root cause identified in watcher crash excerpt logic
- [x] failing test added for LeakSanitizer line capture and leak signature extraction
- [x] failing test added for leak-aware LLM evidence routing from stale current-status + raw log body
- [x] watcher regex updated to capture `ERROR: LeakSanitizer`
- [x] watcher crash excerpt updated to retain stack/location lines after crash start
- [x] evidence packet raw signal summary updated to preserve `LeakSanitizer`
- [x] leak-specific failure reason/objective added (`leak-sanitizer-signal`, `cleanup-leak-closure`)
- [x] evidence packet now repairs stale leak classification from `fuzz.log` body and leak summary
- [x] targeted leak tests passed
- [x] full `tests/test_hermes_watch.py` passed
- [x] full `pytest -q` passed
- [x] fresh LLM evidence packet regenerated
- [x] canonical records updated (`current-status.md`, `progress-index.md`)
- [ ] historical run-history/current_status backfill performed (not done in this slice)
