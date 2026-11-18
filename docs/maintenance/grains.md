# Grains Isolated Test Runner & Maintenance

## Overview
This document specifies the architecture and execution protocol of the isolated test runner for `exercises/practice/grains`.

## Design Goal & Invariant Protection
The runner isolates test execution completely from the repository's working tree:
1. **Learner File Immutability**: The learner starter file (`Grains.ps1`) contains unsolved boilerplate with `throw "Please implement this function"`. The runner computes SHA-256 hashes of `Grains.ps1` before and after all test executions to guarantee that the working tree is never altered or solved in place.
2. **Sandbox Isolation**: Tests are copied into transient temporary directories (`tempfile.TemporaryDirectory()`). The exemplar reference (`.meta/Grains.example.ps1`) is substituted only inside that temporary directory.
3. **Execution Modes Validated**:
   - **Mode A (Genuine Reference)**: All 11 tests pass with zero failures and exit code 0.
   - **Mode B (Deliberately Failing Reference)**: Propagates non-zero test failure count.
   - **Mode C (Empty Test Selection)**: Detects zero-test execution and raises an error.

## Tool Requirements
- **PowerShell**: Version 7.4+ (`pwsh`)
- **Pester**: Version 5.x / 6.x
- **Python**: Version 3.11+

## Execution Commands
```bash
python3 tools/course_checks/r09-t009.py
# or
python3 work/R09-T009/check.py
```

## Test Case Coverage
The runner validates the Pester Describe block:
`Describe "Test Grains.ps1"`
and asserts execution of all 11 canonical cases:
- `grains on square 1`
- `grains on square 2`
- `grains on square 3`
- `grains on square 4`
- `grains on square 16`
- `grains on square 32`
- `grains on square 64`
- `returns the total number of grains on the board`
- `zero is an error`
- `negative value is an error`
- `exceeds maximum square`
