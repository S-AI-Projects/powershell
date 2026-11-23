# R09-T052 · Relative Distance — Test-Generation Reproducibility & Runner Isolation

## Architecture of `check.py`

The test runner `work/R09-T052/check.py` provides an isolated, failure-propagating harness for `relative-distance`:
1. **Dynamic Config Resolution:** Reads `exercises/practice/relative-distance/.meta/config.json` to resolve paths for `solution` (`RelativeDistance.ps1`), `test` (`RelativeDistance.tests.ps1`), and `example` (`.meta/RelativeDistance.example.ps1`).
2. **Focused Regeneration Verification:** Executes `tools/course_checks/r09-t052.py` to confirm that all 7 canonical cases in `tests.toml` map 1-to-1 with `RelativeDistance.tests.ps1`, two independent generations yield identical test suites under timestamp normalization, and 0 cases are dropped.
3. **Cryptographic Protection of Learner Files:**
   - Computes SHA-256 hashes of learner starter files (`RelativeDistance.ps1`) before any operations.
   - Audits learner file hashes after Mode 1, Mode 2, and Mode 3 to assert zero mutations.
   - Learner stub retains the unaltered placeholder exceptions.
4. **Sandbox Isolation & Cleanup:**
   - Each test mode executes inside an independent `tempfile.mkdtemp()` directory.
   - Reference or mutant code is substituted only inside the temporary directory copy.
   - `try/finally` blocks guarantee cleanup of temporary workspaces upon completion, failure, or interruption.

---

## Verification Modes & Results

### Mode 1: Real Reference Implementation
- **Implementation:** `.meta/RelativeDistance.example.ps1`
- **Return Code:** `0` (Expected: 0)
- **Total Tests:** `7`
- **Passed:** `7`
- **Failed:** `0` (Expected: 0)
- **Executed:** `7`
- **Anchored Cases Verified:**
  - `RelativeDistance test cases`: **PASS**
  - `Direct parent-child relation`: **PASS**
  - `Sibling relationship`: **PASS**
- **Learner File Hash Check:** Verified unchanged.
- **Temp Directory Cleanup:** Verified cleaned up.

### Mode 2: Deliberately Failing Reference
- **Implementation:** Mutant returning `999`
- **Return Code:** `1` (Expected: non-zero, actual: 1)
- **Total Tests:** `7`
- **Failed:** `7` (Expected: > 0)
- **Learner File Hash Check:** Verified unchanged.
- **Temp Directory Cleanup:** Verified cleaned up.

### Mode 3: Empty Test Selection
- **Filter Applied:** `TagFilter = 'NonExistentTagFilter123'`
- **Return Code:** `42` (Expected: non-zero exit on 0 executed tests, actual: 42)
- **Executed Tests:** `0`
- **NotRun Count:** `7`
- **Zero-test Failure Propagation:** Successfully caught zero-run and exited non-zero.
- **Learner File Hash Check:** Verified unchanged.
- **Temp Directory Cleanup:** Verified cleaned up.

---

## Cryptographic Hash Audit

- File: `exercises/practice/relative-distance/RelativeDistance.ps1`
- Algorithm: SHA-256
- Hash: `22d267bc6a93e2191036284ddc67cbbbbe314218fadf183607a0ed0a861dfc38`
- State across all test phases: **Identical** (no mutations detected).

---

## Note for Upstream Contribution

Remove `work/R09-T052/` before any branch aimed at upstream `exercism/powershell`.
