# Hermes Watch Duplicate Crash Compare Plan Enrichment v0.1 Checklist

- [x] fresh duplicate crash review rail의 weak point가 plan/context 빈약함인지 확인
- [x] failing regression test로 duplicate review plan compare section 부재 확인
- [x] crash index return payload에 first/last report + artifact lineage 보강
- [x] `review_duplicate_crash_replay` registry entry에 first report/artifact lineage 저장
- [x] duplicate review refiner plan이 `Duplicate Crash Comparison` 섹션을 자동 생성
- [x] duplicate review refiner plan이 low-risk compare commands를 자동 생성
- [x] duplicate review subagent/cron prompt가 enriched context를 포함
- [x] targeted pytest GREEN 확인
- [x] `pytest -q`
- [x] live duplicate review plan artifact 재생성 및 compare section 확인
- [ ] duplicate review 결과가 actual triage execution artifact로 다시 닫힘
