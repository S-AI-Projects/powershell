## Description

Implements R09-T056: compare implementation approaches for `pangram`.

Compares two fundamentally different strategies for implementing the pangram contract in PowerShell:
1. **Approach 1 (Reference technique): Input scan with set accumulator** — iterates over characters in the input sentence and collects unique lowercase letters into an array until 26 letters are accumulated.
2. **Approach 2 (Alternative technique): Alphabet query with early exit** (`work/R09-T056/alt/PangramAlt.ps1`) — iterates over the 26 letters of the Latin alphabet (`'a'..'z'`) and queries whether the lowercased sentence contains each letter, returning `$false` immediately on the first missing letter.

Documents the data representation, trade-offs, and a worked example in `exercises/practice/pangram/.docs/hints.md` (avoiding a full solution listing).
Details the comparison analysis and complexity characteristics in `docs/maintenance/pangram.md`.
Verifies that both implementations pass all 10 Pester tests with 100% agreement, while the learner stub remains unsolved.

## Related Issue
Fixes: #56

## Type of Change
- [x] Documentation
- [x] Tests
- [x] Refactoring / Maintenance

## Changes Made
- **`exercises/practice/pangram/.docs/hints.md`** — Approach-selection guidance comparing set-accumulation vs alphabet query with early exit, including memory trade-offs and a worked example.
- **`docs/maintenance/pangram.md`** — In-depth architectural comparison of both techniques with complexity and behavioral equivalence records.
- **`work/R09-T056/alt/PangramAlt.ps1`** — Working alternative implementation using alphabet query and short-circuit evaluation.
- **`work/R09-T056/check.py`** — Automated validation script: checks hints and maintenance documentation, runs both reference and alternative implementations against all 10 Pester tests, asserts 100% agreement, verifies learner stub remains unsolved, and fails on any zero-test or assertion error.
- **`work/R09-T056/inputs.json`** — Evidence: task metadata, named cases, and paths.
- **`work/R09-T056/results.json`** — Evidence: execution results for reference, alternative, and stub modes.
- **`work/R09-T056/tool_versions.json`** — Evidence: Python, PowerShell, and Pester versions.

## Screenshots / Recordings
Not applicable.

## Testing

```
python3 work/R09-T056/check.py
```

- Reference: 10/10 tests passed
- Alternative: 10/10 tests passed (100% behavioral agreement)
- Named cases (`empty sentence`, `perfect lower case`) passed
- Stub: 10/10 tests failed (unsolved)
- Exit code: 0

## Checklist
- [x] I have tested my changes locally.
- [x] I have added or updated tests, if needed.
- [x] I have updated documentation, if needed.
- [x] I have followed the project's coding guidelines.
- [x] I have run the relevant tests and checks.
- [x] I have addressed previous review feedback, if applicable.

## Additional Notes
The `work/R09-T056/` directory contains assignment verification artifacts and should be excluded from any later upstream PR.
