# Rotational Cipher Exercise Maintenance & Isolated Runner

## Overview

Maintenance testing for `exercises/practice/rotational-cipher` requires verifying the reference implementation without modifying the starter learner files (`RotationalCipher.ps1` and `RotationalCipher.tests.ps1`) in the repository working tree.

## Tool Requirements

- **Python**: Version 3.8+
- **PowerShell**: PowerShell 7 (`pwsh`)
- **Pester**: Pester 5+ (module for test execution)

## Execution Command

Run the isolated test runner tool:

```bash
python3 tools/course_checks/r09-t029.py
```

Or execute the task verification wrapper:

```bash
python3 work/R09-T029/check.py
```

## Runner Guarantees

1. **Working Tree Immutability**: Takes SHA-256 digests of `RotationalCipher.ps1` and `RotationalCipher.tests.ps1` before test execution and confirms identical hashes upon completion.
2. **Temporary Directory Isolation**: All substitution and testing occur inside an ephemeral temporary directory (`tempfile.TemporaryDirectory`), automatically cleaned up upon test termination.
3. **Failure Propagation**: Exits with a non-zero status code if tests fail, if zero tests are discovered, or if a child process terminates with an error code.
4. **Mutant & Zero-Test Regression**: Verifies that assertion failures and empty test selections fail explicitly with non-zero exit codes.
