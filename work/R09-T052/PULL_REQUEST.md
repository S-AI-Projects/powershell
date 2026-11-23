## Description
Resolves **R09-T052** (Issue #52) for `exercises/practice/relative-distance` submitted by **Jash tolwani** (Roll No / URN: `e26b07f0743`) on branch `student/e26b07f0743/R09-T052` targeting `S-AI-Projects/powershell` (`main`). Documents the route from `tests.toml` to `RelativeDistance.tests.ps1`, implements the reusable course check tool `tools/course_checks/r09-t052.py` verifying test suite reproducibility across independent generations under timestamp normalization without dropping cases, constructs the maintenance guide and case mapping in `docs/maintenance/relative-distance.md`, and validates complete test execution in an isolated temporary runner (`work/R09-T052/check.py`) while preserving learner starter stubs.

## Related Issue
Fixes: #52

## Type of Change
- Tests
- Documentation
- Refactoring / Maintenance

## Changes Made
- Documented test generation command, inputs, and case-to-output mapping in `docs/maintenance/relative-distance.md`.
- Implemented reusable focused regeneration check `tools/course_checks/r09-t052.py` confirming 1-to-1 canonical case mapping, identical reproduction across temporary copies under timestamp normalization, and learner stub failure verification.
- Added isolated runner `work/R09-T052/check.py` with failure propagation, empty selection detection, and SHA-256 learner stub immutability verification.
- Generated evidence artifacts in `work/R09-T052/` (`inputs.json`, `expected_vs_actual.json`, `tool_versions.json`, `results.json`, `maintenance.md`).
- Confirmed learner starter stub `exercises/practice/relative-distance/RelativeDistance.ps1` remains completely untouched.

## Screenshots / Recordings
Not applicable.

## Testing
- Automated test harness: `python3 work/R09-T052/check.py`
  - Reusable check: `python3 tools/course_checks/r09-t052.py` passed all assertions (7/7 cases mapped, 2 independent generations byte-identical).
  - Mode 1 (Reference implementation): 7 executed, 7 passed, 0 failed, exit code 0.
    - Verified anchored cases: `RelativeDistance test cases`, `Direct parent-child relation`, `Sibling relationship`.
  - Mode 2 (Deliberately failing mutant): FailedCount=7, exit code 1 (failure correctly propagated).
  - Mode 3 (Empty selection / zero tests): Executed=0, exit code 42 (zero-test run rejected).
  - Learner starter stub immutability: SHA-256 hash `d377bcf7a695e2978051280d4c1daea6c83df60ea608cfb5e135e5d38a4270d4` verified invariant before and after all test phases.

## Checklist
- [x] I have tested my changes locally.
- [x] I have added or updated tests, if needed.
- [x] I have updated documentation, if needed.
- [x] I have followed the project's coding guidelines.
- [x] I have run the relevant tests and checks.
- [x] I have addressed previous review feedback, if applicable.

## Additional Notes
- Scoped strictly to Task R09-T052; all learner stub files remain unsolved.
- Evidence artifacts stored under `work/R09-T052/` are excluded from upstream `exercism/powershell` submission.
