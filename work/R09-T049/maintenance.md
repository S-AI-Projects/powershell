# R09-T049 · Prime Factors — Runner Isolation & Immutability Verification

## Architecture of `check.py`

The test runner `work/R09-T049/check.py` provides an isolated, failure-propagating harness for `prime-factors`:
1. **Dynamic Config Resolution:** Reads `exercises/practice/prime-factors/.meta/config.json` to resolve paths for `solution` (`PrimeFactors.ps1`), `test` (`PrimeFactors.tests.ps1`), and `example` (`.meta/PrimeFactors.example.ps1`).
2. **Cryptographic Protection of Learner Files:**
   - Computes SHA-256 hashes of learner starter files before any operations.
   - Audits learner file hashes after Mode 1, Mode 2, and Mode 3 to assert zero mutations.
   - Learner stub contains the unaltered `throw "Please implement this function"` placeholder.
3. **Sandbox Isolation & Cleanup:**
   - Each test mode executes inside an independent `tempfile.mkdtemp()` directory.
   - Reference or mutant code is substituted only inside the temporary directory copy.
   - `try/finally` blocks guarantee cleanup of temporary workspaces upon completion, failure, or interruption.

---

## Verification Modes & Results

### Mode 1: Real Reference Implementation
- **Implementation:** `.meta/PrimeFactors.example.ps1`
- **Return Code:** `0` (Expected: 0)
- **Total Tests:** `12`
- **Passed:** `12`
- **Failed:** `0` (Expected: 0)
- **Executed:** `12`
- **Anchored Cases Verified:**
  - `Test Invoke-PrimeFactors.ps1` (Describe block): **PASS**
  - `no factors`: **PASS**
  - `prime number`: **PASS**
- **Learner File Hash Check:** Verified unchanged.
- **Temp Directory Cleanup:** Verified cleaned up.

### Mode 2: Deliberately Failing Reference
- **Implementation:** Mutant returning `@(999999)`
- **Return Code:** `1` (Expected: non-zero, actual: 1)
- **Total Tests:** `12`
- **Failed:** `12` (Expected: > 0)
- **Learner File Hash Check:** Verified unchanged.
- **Temp Directory Cleanup:** Verified cleaned up.

### Mode 3: Empty Test Selection
- **Filter Applied:** `TagFilter = 'NonExistentTagFilter123'`
- **Return Code:** `42` (Expected: non-zero exit on 0 executed tests, actual: 42)
- **Executed Tests:** `0`
- **NotRun Count:** `12`
- **Zero-test Failure Propagation:** Successfully caught zero-run and exited non-zero.
- **Learner File Hash Check:** Verified unchanged.
- **Temp Directory Cleanup:** Verified cleaned up.

---

## Cryptographic Hash Audit

- File: `exercises/practice/prime-factors/PrimeFactors.ps1`
- Algorithm: SHA-256
- Hash: `a0994c21644d06d3f293da94fd61baff0abaeae9216000bc986b4ff6ef337d49`
- State across all test phases: **Identical** (no mutations detected).

---

## Note for Upstream Contribution

Remove `work/R09-T049/` before any branch aimed at upstream `exercism/powershell`.
