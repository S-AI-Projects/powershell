## Description

Implements R09-T058: exercise maintenance metadata verification for `series`.

Maps and verifies the file roles declared in `exercises/practice/series/.meta/config.json`:
1. Establishes the file-role map (`solution`, `test`, `example`, `config.json`, `tests.toml`) and documents generated vs maintained files in `docs/maintenance/series.md`.
2. Implements `tools/course_checks/r09-t058.py` to validate that declared paths are relative, free of parent traversal, resolve within the exercise directory, exist on disk, and match the name patterns expected by the test runner (`bin/run-tests.ps1`).
3. Implements `work/R09-T058/check.py` to verify the real config and three deliberately invalid fixtures (missing reference, missing test, and path traversal outside the exercise).
4. Verifies that all 11 Pester tests pass on the reference implementation, while the learner stub remains unsolved.

## Related Issue
Fixes: #58

## Type of Change
- [x] Documentation
- [x] Tests
- [x] Refactoring / Maintenance

## Changes Made
- **`docs/maintenance/series.md`** — File-role mapping table, explanation of maintained vs generated files, runner discovery mechanics, and reproducible metadata validation command.
- **`tools/course_checks/r09-t058.py`** — Reusable validator for `config.json` path resolution and runner pattern matching.
- **`work/R09-T058/check.py`** — Automated validation script: checks maintenance documentation, validates real config and three invalid fixtures, runs reference against all 11 Pester tests, verifies learner stub remains unsolved, and fails on any zero-test or assertion error.
- **`work/R09-T058/inputs.json`** — Evidence: task metadata, fixture definitions, and paths.
- **`work/R09-T058/results.json`** — Evidence: fixture error outcomes and Pester execution results.
- **`work/R09-T058/tool_versions.json`** — Evidence: Python, PowerShell, and Pester versions.

## Screenshots / Recordings
Not applicable.

## Testing

```
python3 work/R09-T058/check.py
```

- Real config check: PASSED (0 errors)
- Invalid fixture 1 (missing reference): rejected with `MISSING_FILE`
- Invalid fixture 2 (missing test): rejected with `MISSING_FILE`
- Invalid fixture 3 (outside exercise): rejected with `OUTSIDE_EXERCISE`
- Reference tests: 11/11 passed
- Named cases (`Test Get-Slices`, `slices of one from one`, `slices of one from two`) passed
- Stub: 11/11 failed (unsolved)
- Exit code: 0

## Checklist
- [x] I have tested my changes locally.
- [x] I have added or updated tests, if needed.
- [x] I have updated documentation, if needed.
- [x] I have followed the project's coding guidelines.
- [x] I have run the relevant tests and checks.
- [x] I have addressed previous review feedback, if applicable.

## Additional Notes
The `work/R09-T058/` directory contains assignment verification artifacts and should be excluded from any later upstream PR.
