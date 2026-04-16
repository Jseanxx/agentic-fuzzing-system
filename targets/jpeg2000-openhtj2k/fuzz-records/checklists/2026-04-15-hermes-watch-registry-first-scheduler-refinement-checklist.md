# R16 Registry-First Scheduler Refinement Checklist

- [x] refiner queue selection uses a shared registry-first selector
- [x] queue weighting considers ranked candidate effective score
- [x] queue weighting considers candidate status bonuses
- [x] queue weighting considers recent run history signals
- [x] queue ranks are written back into registry entries
- [x] executor stage uses weighted cross-registry selection
- [x] prepared/ready/armed/verifiable stages use weighted cross-registry selection
- [x] failing tests added first for cross-registry queue weighting
- [x] targeted scheduler tests pass
- [x] py_compile passes
- [x] full watcher unittest passes
