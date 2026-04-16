# R15 Richer Candidate Debt Model Checklist

- [x] ranked candidate registry tracks richer debt counters
- [x] smoke/build/review/seed/instability debt buckets supported in registry updates
- [x] pass/fail streak fields maintained in candidate state
- [x] debt penalty and effective score computed for candidate ranking
- [x] selection uses debt-weighted effective score instead of raw score only
- [x] review route still preserves current-candidate selection behavior
- [x] verification-policy closure updates effective score/debt penalty fields
- [x] failing tests added first
- [x] targeted tests pass
- [x] py_compile passes
- [x] full watcher unittest passes
