# R09-T051 · DnD Character — Canonical Case Decisions & Runner Isolation

## Architecture of `check.py`

The test runner `work/R09-T051/check.py` provides an isolated, failure-propagating harness for `dnd-character`:
1. **Dynamic Config Resolution:** Reads `exercises/practice/dnd-character/.meta/config.json` to resolve paths for `solution` (`DndCharacter.ps1`), `test` (`DndCharacter.tests.ps1`), and `example` (`.meta/DndCharacter.example.ps1`).
2. **Canonical Case Analysis:**
   - Validates `exercises/practice/dnd-character/.meta/tests.toml` parsing with `tomllib`.
   - Confirms exactly 20 canonical cases (19 included, 1 excluded).
   - Verifies target exclusion UUID `2ca77b9b-c099-46c3-a02c-0d0f68ffa0fe` has `include = false` and documents a concrete `comment` rationale referencing replacement UUID `dca2b2ec-f729-4551-84b9-078876bb4808` and PowerShell property semantics.
3. **Cryptographic Protection of Learner Files:**
   - Computes SHA-256 hashes of learner starter files (`DndCharacter.ps1`) before any operations.
   - Audits learner file hashes after Mode 1, Mode 2, and Mode 3 to assert zero mutations.
   - Learner stub retains the unaltered placeholder exceptions.
4. **Sandbox Isolation & Cleanup:**
   - Each test mode executes inside an independent `tempfile.mkdtemp()` directory.
   - Reference or mutant code is substituted only inside the temporary directory copy.
   - `try/finally` blocks guarantee cleanup of temporary workspaces upon completion, failure, or interruption.

---

## Verification Modes & Results

### Canonical Case Decisions & TOML Audit
- **Total Canonical Cases:** 20
- **Included Cases:** 19
- **Excluded Cases:** 1
- **Excluded UUID:** `2ca77b9b-c099-46c3-a02c-0d0f68ffa0fe` (`"each ability is only calculated once"`)
- **Replacement UUID:** `dca2b2ec-f729-4551-84b9-078876bb4808` (`reimplements = "2ca77b9b-c099-46c3-a02c-0d0f68ffa0fe"`)
- **Rationale Status:** Validated against PowerShell class property semantics.

### Mode 1: Real Reference Implementation
- **Implementation:** `.meta/DndCharacter.example.ps1`
- **Return Code:** `0` (Expected: 0)
- **Total Tests:** `19`
- **Passed:** `19`
- **Failed:** `0` (Expected: 0)
- **Executed:** `19`
- **Anchored Cases Verified:**
  - `DnD Character test cases`: **PASS**
  - `ability modifier for score 3 is -4`: **PASS**
  - `ability modifier for score 4 is -3`: **PASS**
- **Learner File Hash Check:** Verified unchanged.
- **Temp Directory Cleanup:** Verified cleaned up.

### Mode 2: Deliberately Failing Reference
- **Implementation:** Mutant returning `HitPoints = 999` and `GetModifier = 999`
- **Return Code:** `1` (Expected: non-zero, actual: 1)
- **Total Tests:** `19`
- **Failed:** `18` (Expected: > 0)
- **Learner File Hash Check:** Verified unchanged.
- **Temp Directory Cleanup:** Verified cleaned up.

### Mode 3: Empty Test Selection
- **Filter Applied:** `TagFilter = 'NonExistentTagFilter123'`
- **Return Code:** `42` (Expected: non-zero exit on 0 executed tests, actual: 42)
- **Executed Tests:** `0`
- **NotRun Count:** `19`
- **Zero-test Failure Propagation:** Successfully caught zero-run and exited non-zero.
- **Learner File Hash Check:** Verified unchanged.
- **Temp Directory Cleanup:** Verified cleaned up.

---

## Cryptographic Hash Audit

- File: `exercises/practice/dnd-character/DndCharacter.ps1`
- Algorithm: SHA-256
- Hash: `ae72913c5d91535ceefcb7bbdb3fca78249f51b3e577998ce92ae98ef34ee3cf`
- State across all test phases: **Identical** (no mutations detected).

---

## Note for Upstream Contribution

Remove `work/R09-T051/` before any branch aimed at upstream `exercism/powershell`.
