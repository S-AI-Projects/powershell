## Description

Implements R09-T057: language-specific guidance for `resistor-color-duo`.

Provides targeted guidance on PowerShell explicit return values and scalar typing:
1. Explains how the reference implementation uses an explicit `return` with numeric arithmetic (`return $firstColor * 10 + $secondColor`) to produce an integer scalar (`Int32`).
2. Illustrates with executable micro-examples the difference between integer arithmetic and string concatenation (`"$first$second"`), explaining why Pester's `Should -BeExactly` rejects a string when an integer is expected.
3. Links to official Microsoft documentation on PowerShell return semantics (`about_Return`).
4. Documents maintenance notes in `docs/maintenance/resistor-color-duo.md`.
5. Learner stub (`ResistorColorDuo.ps1`) remains untouched and unsolved.

## Related Issue
Fixes: #57

## Type of Change
- [x] Documentation
- [x] Tests
- [x] Refactoring / Maintenance

## Changes Made
- **`exercises/practice/resistor-color-duo/.docs/hints.md`** — Language-specific guidance on explicit return values vs string concatenation pitfall, with two executable micro-examples and a link to `about_Return`.
- **`docs/maintenance/resistor-color-duo.md`** — Explains the language construct used in the reference and the typing considerations for learners.
- **`work/R09-T057/check.py`** — Automated validation script: checks hints.md and maintenance documentation, executes both micro-examples to verify output agreement, runs all 7 Pester tests on the reference, verifies learner stub remains unsolved, and fails on any zero-test or assertion error.
- **`work/R09-T057/inputs.json`** — Evidence: task metadata, construct details, and paths.
- **`work/R09-T057/results.json`** — Evidence: Pester run results and micro-example outputs.
- **`work/R09-T057/tool_versions.json`** — Evidence: Python, PowerShell, and Pester versions.

## Screenshots / Recordings
Not applicable.

## Testing

```
python3 work/R09-T057/check.py
```

- Reference: 7/7 tests passed
- Named cases (`Test Get-ColorCodeValue`, `Brown and blac`, `Blue and grey`) passed
- Both micro-examples executed and verified against published text
- Stub: 7/7 tests failed (unsolved)
- Exit code: 0

## Checklist
- [x] I have tested my changes locally.
- [x] I have added or updated tests, if needed.
- [x] I have updated documentation, if needed.
- [x] I have followed the project's coding guidelines.
- [x] I have run the relevant tests and checks.
- [x] I have addressed previous review feedback, if applicable.

## Additional Notes
The `work/R09-T057/` directory contains assignment verification artifacts and should be excluded from any later upstream PR.
