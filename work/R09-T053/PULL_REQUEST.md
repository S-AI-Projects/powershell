## Description

Implements R09-T053: mutation-driven regression for the `transpose` exercise.

Creates a deliberate, semantic mutant of the reference implementation (`.TrimEnd()` → `.Trim()`), identifies the existing test case that rejects it (`second line longer than first line`), reduces the diagnostic input to its smallest form (`"AB\nDEF"` → expected last row `" F"`), and adds a hints page explaining the padding contract without revealing the full solution.

The automated check (`work/R09-T053/check.py`) verifies that:
- The reference passes all 13 Pester tests including the two named anchored cases (`empty string`, `two characters in a row`).
- The mutant fails exactly `second line longer than first line` while the named anchored cases still pass.
- The learner stub remains unsolved.
- The check exits non-zero on any failure.

## Related Issue
Fixes: #53

## Type of Change
- [x] New Feature
- [x] Tests
- [x] Documentation
- [x] Refactoring / Maintenance

## Changes Made
- **`exercises/practice/transpose/.docs/hints.md`** — New file. Explains the leading-space padding contract (shorter rows padded when a later row is longer) and provides the smallest diagnostic input (`"AB\nDEF"` → `" F"`) without publishing the reference implementation.
- **`docs/maintenance/transpose.md`** — New file. Records the mutation (`.TrimEnd()` → `.Trim()`), rejecting UUID (`984e2ec3-b3d3-4b53-8bd6-96f5ef404102`), test name (`second line longer than first line`), smallest diagnostic input, and which named cases do/do not distinguish the mutant.
- **`work/R09-T053/check.py`** — Automated runner: checks hints.md and maintenance doc, runs reference (all pass), runs mutant (named fail rejects it, named passes pass), runs stub (all fail), saves evidence artifacts.
- **`work/R09-T053/inputs.json`** — Evidence: mutation details, diagnostic input/output.
- **`work/R09-T053/results.json`** — Evidence: Pester run results for reference, mutant, and stub modes.
- **`work/R09-T053/tool_versions.json`** — Evidence: Python, PowerShell, Pester versions.

## Screenshots / Recordings
Not applicable.

## Testing

```
python3 work/R09-T053/check.py
```

- Reference mode: 13/13 Pester tests passed
- Mutant mode: `second line longer than first line` FAIL (expected); `empty string`, `two characters in a row` PASS (expected)
- Stub mode: all 13 tests failed (learner unsolved)
- Exit code: 0

## Checklist
- [x] I have tested my changes locally.
- [x] I have added or updated tests, if needed.
- [x] I have updated documentation, if needed.
- [x] I have followed the project's coding guidelines.
- [x] I have run the relevant tests and checks.
- [x] I have addressed previous review feedback, if applicable.

## Additional Notes

The mutation `.TrimEnd()` → `.Trim()` is semantic: `.Trim()` removes both leading and trailing whitespace, incorrectly stripping the leading spaces that represent padding for shorter input rows in the transposed output. Only trailing spaces should be removed.

The `hints.md` deliberately omits the word `TrimEnd` and the reference implementation syntax, so it explains the contract (leading-space padding) without solving the exercise for the learner.

The `work/R09-T053/` directory is evidence-only and should be removed from any later upstream PR.

