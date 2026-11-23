## Description

Implements R09-T059: isolated test runner for `alphametics`.

Creates a dedicated, isolated test runner (`tools/course_checks/r09-t059.py`) that:
1. Executes Pester tests in a temporary isolated directory, substituting the reference implementation without ever modifying the working tree.
2. Accurately reports executed test counts (filtering out skipped / not-run tests).
3. Propagates exit codes correctly: 0 for all passed, 1 for test failure or child error, 2 for empty test selection (`Executed == 0`), and 130 for interruption.
4. Cleans up all temporary directories automatically.
5. Documents the command and maintenance notes in `docs/maintenance/alphametics.md`.
6. Preserves learner stub files (`Alphametics.ps1`) byte-for-byte before and after every run.

## Related Issue
Fixes: #59

## Type of Change
- [x] Documentation
- [x] Tests
- [x] Refactoring / Maintenance

## Changes Made
- **`tools/course_checks/r09-t059.py`** — Dedicated isolated test runner for `alphametics` with temporary workspace isolation, executed count reporting, and explicit exit code propagation (0/1/2/130).
- **`docs/maintenance/alphametics.md`** — File-role mapping table, runner documentation, exit code specification, empty selection handling, and verification instructions.
- **`work/R09-T059/check.py`** — Automated validation script: checks maintenance documentation, validates runner behavior across 4 modes (real reference, failing reference, empty selection, learner stub), verifies learner file SHA-256 hashes remain strictly identical before and after all runs, verifies named test cases pass, and fails on any zero-test or assertion error.
- **`work/R09-T059/inputs.json`** — Evidence: task metadata, runner modes, and paths.
- **`work/R09-T059/results.json`** — Evidence: run exit codes, outputs, and learner file hash integrity.
- **`work/R09-T059/tool_versions.json`** — Evidence: Python, PowerShell, and Pester versions.

## Screenshots / Recordings
Not applicable.

## Testing

```
python3 work/R09-T059/check.py
```

- Real reference: exit 0 (Executed cases: 9)
- Failing reference: exit 1 (Expected failure)
- Empty selection: exit 2 (Zero executed cases detected)
- Learner stub: exit 1 (Unsolved)
- Learner file hashes: strictly identical before and after all runs
- Named cases (`Alphametics test cases`, `puzzle with three letters`, `solution must have unique value for each letter`) passed
- Exit code: 0

## Checklist
- [x] I have tested my changes locally.
- [x] I have added or updated tests, if needed.
- [x] I have updated documentation, if needed.
- [x] I have followed the project's coding guidelines.
- [x] I have run the relevant tests and checks.
- [x] I have addressed previous review feedback, if applicable.

## Additional Notes
The `work/R09-T059/` directory contains assignment verification artifacts and should be excluded from any later upstream PR.
