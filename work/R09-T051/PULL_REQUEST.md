## Description
Resolves **R09-T051** (Issue #6) for `exercises/practice/dnd-character` submitted by **Jash tolwani** (Roll No / URN: `e26b07f0743`) on branch `student/e26b07f0743/R09-T051` targeting `S-AI-Projects/powershell` (`main`). Audits all 20 canonical cases in `tests.toml`, documents the formal exclusion rationale for UUID `2ca77b9b-c099-46c3-a02c-0d0f68ffa0fe` ("each ability is only calculated once") replaced by track-specific test `dca2b2ec-f729-4551-84b9-078876bb4808`, creates a canonical mapping table in `docs/maintenance/dnd-character.md`, and validates complete test execution in an isolated temporary runner (`work/R09-T051/check.py`) without modifying learner starter files.

## Related Issue
Fixes: #6

## Type of Change
- Tests
- Documentation
- Refactoring / Maintenance

## Changes Made
- Documented exclusion rationale for UUID `2ca77b9b-c099-46c3-a02c-0d0f68ffa0fe` under the `comment` key in `exercises/practice/dnd-character/.meta/tests.toml`, clarifying that PowerShell models abilities as class instance properties initialized once in `Character()`, verifying persistence via replacement UUID `dca2b2ec-f729-4551-84b9-078876bb4808`.
- Added canonical test mapping table and architectural notes in `docs/maintenance/dnd-character.md`.
- Implemented isolated verification harness in `work/R09-T051/check.py` reading paths dynamically from `.meta/config.json`.
- Generated evidence artifacts in `work/R09-T051/` (`inputs.json`, `expected_vs_actual.json`, `tool_versions.json`, `maintenance.md`).
- Confirmed learner starter stub `exercises/practice/dnd-character/DndCharacter.ps1` remains completely untouched.

## Screenshots / Recordings
Not applicable.

## Testing
- Automated test harness: `python3 work/R09-T051/check.py`
  - Tool versions: Python 3.14.7, PowerShell 7.7.0, Pester 6.2.0, git 2.55.0 on macOS arm64.
  - Mode 1 (Reference implementation): 19 executed, 19 passed, 0 failed, exit code 0.
    - Verified anchored cases: `DnD Character test cases`, `ability modifier for score 3 is -4`, `ability modifier for score 4 is -3`.
  - Mode 2 (Deliberately failing mutant): FailedCount=18, exit code 1 (failure correctly propagated).
  - Mode 3 (Empty selection / zero tests): Executed=0, exit code 42 (zero-test run rejected).
  - Learner starter stub immutability: SHA-256 hash `ae72913c5d91535ceefcb7bbdb3fca78249f51b3e577998ce92ae98ef34ee3cf` verified invariant before and after all test phases.
  - TOML syntax validation: Validated with Python `tomllib` (20 cases, 19 included, 1 excluded).

## Checklist
- [x] I have tested my changes locally.
- [x] I have added or updated tests, if needed.
- [x] I have updated documentation, if needed.
- [x] I have followed the project's coding guidelines.
- [x] I have run the relevant tests and checks.
- [x] I have addressed previous review feedback, if applicable.

## Additional Notes
- Scoped strictly to Task R09-T051; all learner stub files remain unsolved.
- Evidence artifacts stored under `work/R09-T051/` are excluded from upstream `exercism/powershell` submission.
