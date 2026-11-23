## Description

Implements R09-T060: contract examples and decision table for `all-your-base`.

Expands guidance and maintenance documentation around the contract specification:
1. Explains why the expected outcomes for `single bit one to decimal` (`@(1)`) and `binary to single decimal` (`@(5)`) follow directly from the mathematical positional notation specification ($1 \times 2^0 = 1 \times 10^0$; $1 \times 2^2 + 0 \times 2^1 + 1 \times 2^0 = 5 \times 10^0$).
2. Provides input/output walkthroughs and notes on PowerShell representation (arrays of `[int]`, ensuring single-element outputs remain arrays `@()`) in `exercises/practice/all-your-base/.docs/hints.md`.
3. Constructs a comprehensive decision table in `docs/maintenance/all-your-base.md` separating specified inputs from out-of-contract inputs (non-integers, fractional bases, non-array objects).
4. Includes an explicit statement on unspecified behaviors, cautioning against inventing non-standard exception hierarchies or coercions.
5. Verifies all 21 Pester tests pass on the reference implementation, while the learner stub remains unsolved.

## Related Issue
Fixes: #60

## Type of Change
- [x] Documentation
- [x] Tests
- [x] Refactoring / Maintenance

## Changes Made
- **`exercises/practice/all-your-base/.docs/hints.md`** — Input/output walkthrough for selected cases, PowerShell array return guidance, and error handling rules.
- **`docs/maintenance/all-your-base.md`** — Mathematical derivations, comprehensive decision table, and explicit statement on unspecified behaviors.
- **`work/R09-T060/check.py`** — Automated validation script: checks hints.md and maintenance documentation, reproduces exact outputs for selected cases, runs reference against all 21 Pester tests, verifies learner stub remains unsolved, and fails on any zero-test or assertion error.
- **`work/R09-T060/inputs.json`** — Evidence: task metadata, reproduced cases, and paths.
- **`work/R09-T060/results.json`** — Evidence: reproduction results and Pester execution results.
- **`work/R09-T060/tool_versions.json`** — Evidence: Python, PowerShell, and Pester versions.

## Screenshots / Recordings
Not applicable.

## Testing

```
python3 work/R09-T060/check.py
```

- Reproduction check:
  - `single bit one to decimal` -> `@(1)` PASS
  - `binary to single decimal` -> `@(5)` PASS
- Reference tests: 21/21 passed
- Named cases (`All your base test cases`, `single bit one to decimal`, `binary to single decimal`) passed
- Stub: 21/21 failed (unsolved)
- Exit code: 0

## Checklist
- [x] I have tested my changes locally.
- [x] I have added or updated tests, if needed.
- [x] I have updated documentation, if needed.
- [x] I have followed the project's coding guidelines.
- [x] I have run the relevant tests and checks.
- [x] I have addressed previous review feedback, if applicable.

## Additional Notes
The `work/R09-T060/` directory contains assignment verification artifacts and should be excluded from any later upstream PR.
