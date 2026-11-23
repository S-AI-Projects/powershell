## Description

Implements R09-T055: reference complexity study for `pig-latin`.

Analyzes and measures the computational cost of the reference implementation (`exercises/practice/pig-latin/.meta/PigLatin.example.ps1`):
1. Documents the algorithmic complexity ($O(N)$ total string length or $O(w)$ for $w$ space-separated words of bounded length) with a dedicated comment adjacent to the reference function.
2. Measures execution across three valid input sizes ($w = 10, 100, 1000$ words) with 7 repetitions each, asserting correctness before timing.
3. Distinguishes algorithmic execution from PowerShell process startup and module load overhead.
4. Explains the results and limitations in `docs/maintenance/pig-latin.md`.
5. Learner stub (`PigLatin.ps1`) remains untouched and unsolved.

## Related Issue
Fixes: #55

## Type of Change
- [x] Documentation
- [x] Refactoring / Maintenance
- [x] Tests

## Changes Made
- **`exercises/practice/pig-latin/.meta/PigLatin.example.ps1`** — Added precise complexity and invariant comments detailing the cost of string splitting, pipeline regex evaluation, and string assembly.
- **`docs/maintenance/pig-latin.md`** — Comprehensive complexity study documenting input size definitions, operation breakdown, benchmark results across 3 sizes, startup vs algorithm work distinction, and conclusion limits.
- **`work/R09-T055/check.py`** — Automated validation script: checks complexity comments, verifies all 23 Pester tests pass on the reference, measures scaling across 3 input sizes, checks process startup timing, verifies learner stub remains unsolved, and fails on any zero-test or assertion error.
- **`work/R09-T055/inputs.json`** — Evidence: task metadata, word sizes, and test names.
- **`work/R09-T055/results.json`** — Evidence: Pester results, scaling measurements, medians, ratios, and startup times.
- **`work/R09-T055/tool_versions.json`** — Evidence: Python, PowerShell, and Pester versions.

## Screenshots / Recordings
Not applicable.

## Testing

```
python3 work/R09-T055/check.py
```

- Reference: 23/23 tests passed
- Named cases (`PigLatin test cases`, `word beginning with *`) passed
- Scaling verified: $w=10$ (0.20 ms) < $w=100$ (0.86 ms) < $w=1000$ (8.51 ms)
- Learner stub: 23/23 tests failed (unsolved)
- Exit code: 0

## Checklist
- [x] I have tested my changes locally.
- [x] I have added or updated tests, if needed.
- [x] I have updated documentation, if needed.
- [x] I have followed the project's coding guidelines.
- [x] I have run the relevant tests and checks.
- [x] I have addressed previous review feedback, if applicable.

## Additional Notes
The `work/R09-T055/` directory contains assignment verification artifacts and should be excluded from any later upstream PR.
