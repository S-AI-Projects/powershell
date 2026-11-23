## Description

Implements R09-T054: scoped reference implementation refactoring for `micro-blog`.

Clarifies `exercises/practice/micro-blog/.meta/MicroBlog.example.ps1` by:
1. Renaming the ambiguous variable `$charArray` to `$textElementOffsets` to accurately reflect that `[System.Globalization.StringInfo]::ParseCombiningCharacters` returns an `int[]` of character index offsets (grapheme cluster boundaries), not an array of characters.
2. Adding a clear comment explaining the exercise-specific invariant:
   `# Invariant: a micro-blog post is limited to at most 5 Unicode text elements (grapheme clusters).`
3. Eliminating the inefficient while-loop character slicing and array rebuilding (`$charList += $character; -join $charList`), replacing it with direct single-step substring truncation at the 6th text element offset (`$Post.Substring(0, $cutoffOffset)`).

Behavioral equivalence is strictly maintained across all 16 test cases, including all Unicode, emoji, and mathematics cases.

The learner stub (`MicroBlog.ps1`) remains untouched and unsolved.

## Related Issue
Fixes: #54

## Type of Change
- [x] Refactoring / Maintenance
- [x] Documentation
- [x] Tests

## Changes Made
- **`exercises/practice/micro-blog/.meta/MicroBlog.example.ps1`** — Renamed `$charArray` to `$textElementOffsets`, added invariant comment, simplified to direct single-substring truncation.
- **`docs/maintenance/micro-blog.md`** — Documented the refactoring rationale, variable naming clarification, and behavioral equivalence verification across all 16 test cases.
- **`work/R09-T054/check.py`** — Automated validation script: checks maintenance notes, compares baseline vs refactored outputs, verifies all 16 Pester tests pass on the reference, checks that learner stub remains unsolved, and fails on any zero-test or assertion error.
- **`work/R09-T054/inputs.json`** — Evidence: task metadata, named cases, and paths.
- **`work/R09-T054/results.json`** — Evidence: baseline, refactored, and stub test execution results.
- **`work/R09-T054/tool_versions.json`** — Evidence: Python, PowerShell, and Pester versions.

## Screenshots / Recordings
Not applicable.

## Testing

```
python3 work/R09-T054/check.py
```

- Baseline: 16/16 tests passed
- Refactored reference: 16/16 tests passed (100% behavioral equivalence)
- Named cases (`English language short`, `English language long`) passed
- Stub: 16/16 tests failed with exception (unsolved)
- Exit code: 0

## Checklist
- [x] I have tested my changes locally.
- [x] I have added or updated tests, if needed.
- [x] I have updated documentation, if needed.
- [x] I have followed the project's coding guidelines.
- [x] I have run the relevant tests and checks.
- [x] I have addressed previous review feedback, if applicable.

## Additional Notes
The `work/R09-T054/` directory contains assignment verification artifacts and should be excluded from any later upstream PR.
