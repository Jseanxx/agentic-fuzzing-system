# Hermes Watch Deep Crash Routing Override v0.1 Checklist

- [x] latest deep critical crash packet misrouting 확인
- [x] failing regression test added for deep critical crash routing override
- [x] objective-to-routing helper now reads `current_status`
- [x] deeper-stage / new-signal objective가 already-deep crash면 review route로 override
- [x] override reason `deep-stage-crash-already-reached` linkage summary에 기록
- [x] targeted V09 tests passed
- [x] `python -m py_compile scripts/hermes_watch_support/llm_evidence.py tests/test_hermes_watch.py`
- [x] `python -m pytest tests/test_hermes_watch.py -q`
- [x] `python -m pytest tests -q`
- [x] real repo packet regenerated and review route 확인
- [ ] deep crash review route가 실제 follow-up triage artifact로 더 직접 연결됨
