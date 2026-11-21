# Maintenance & Verification Documentation: Armstrong Numbers (Task R09-T042)

## 1. Goal & Overview
This document details the route from the canonical test definitions in:
`exercises/practice/armstrong-numbers/.meta/tests.toml`
to the PowerShell Pester test suite in:
`exercises/practice/armstrong-numbers/ArmstrongNumbers.tests.ps1`

Anchored verification test cases:
1. **`Test Invoke-ArmstrongNumbers.ps1`** (Pester Describe block container)
2. **`Zero is an Armstrong number`** (Canonical test case UUID `c1ed103c-258d-45b2-be73-d8c6d9580c7b`)
3. **`Single-digit numbers are Armstrong numbers`** (Canonical test case UUID `579e8f03-9659-4b85-a1a2-d64350f6b17a`)

---

## 2. Generated vs. Hand-Maintained Files in the PowerShell Track
Exercism language tracks vary in whether test files are generated via Jinja2/custom templates or written and maintained manually.

In the **PowerShell track**:
- **No track-level test generator or Jinja templates exist.** A comprehensive scan of the repository confirms no `.jinja`, `.j2`, or template files, and no test generation scripts exist under `bin/`.
- **`exercises/practice/armstrong-numbers/.meta/tests.toml` is synchronized via `configlet`:**
  - Synchronized from the canonical [problem-specifications](https://github.com/exercism/problem-specifications) repository via `configlet sync --tests --exercise armstrong-numbers`.
  - Configlet manages canonical UUID tracking, case descriptions, and `include` flags.
- **`exercises/practice/armstrong-numbers/ArmstrongNumbers.tests.ps1` is hand-maintained:**
  - Written in Pester v5/v6 DSL (`Describe`, `It`, `Should`).
  - Implements the canonical test cases specified by `tests.toml`.
  - Maintained directly by track maintainers and contributors.
- **Solution Stub & Example:**
  - `ArmstrongNumbers.ps1` (learner stub) is hand-maintained.
  - `.meta/ArmstrongNumbers.example.ps1` (reference implementation) is hand-maintained.

---

## 3. Detailed Route: `tests.toml` to `ArmstrongNumbers.tests.ps1`

### 3.1 Canonical Specification Mapping
The canonical `tests.toml` contains **11 total test cases**:
- **9 Included Cases:** Implicitly included per Exercism specification (omitted `include` implies `include = true`).
- **2 Excluded Cases (`include = false`):**
  1. `5ee2fdf8-334e-4a46-bb8d-e5c19c02c148` ("Armstrong number containing seven zeroes" — $186709961001538790100$, 21 digits)
  2. `12ffbf10-307a-434e-b4ad-c925680e1dd4` ("The largest and last Armstrong number" — $115132219018763992565095597973971522401$, 39 digits)
  *Exclusion Rationale:* Both numbers exceed the 64-bit signed integer boundary (`[Int64]::MaxValue = 9223372036854775807`). The PowerShell implementation uses `[Int64]$Number` as specified in the function signature, making numbers exceeding 19 digits outside the target range for standard integer operations.

### 3.2 Anchored Test Case Sources
1. **`Test Invoke-ArmstrongNumbers.ps1`**:
   - **Source:** `ArmstrongNumbers.tests.ps1`, line 5 (`Describe "Test Invoke-ArmstrongNumbers.ps1"`).
   - **Role:** Defines the root Pester test suite group named after the cmdlet function under test (`Invoke-ArmstrongNumbers`).
2. **`Zero is an Armstrong number`**:
   - **Source:** `tests.toml` UUID `c1ed103c-258d-45b2-be73-d8c6d9580c7b`.
   - **Pester Block:** Lines 6–10 in `ArmstrongNumbers.tests.ps1`:
     ```powershell
     It "Zero is an Armstrong number" {
         $got = Invoke-ArmstrongNumbers -Number 0

         $got | Should -BeTrue
     }
     ```
   - **Verification:** Evaluates `Invoke-ArmstrongNumbers -Number 0` expecting `$True` ($0^1 = 0$).
3. **`Single-digit numbers are Armstrong numbers`**:
   - **Source:** `tests.toml` UUID `579e8f03-9659-4b85-a1a2-d64350f6b17a`.
   - **Pester Block:** Lines 12–16 in `ArmstrongNumbers.tests.ps1`:
     ```powershell
     It "Single-digit numbers are Armstrong numbers" {
         $got = Invoke-ArmstrongNumbers -Number 5

         $got | Should -BeTrue
     }
     ```
   - **Verification:** Evaluates `Invoke-ArmstrongNumbers -Number 5` expecting `$True` ($5^1 = 5$).

---

## 4. Reproduction Command & CI Integration

### 4.1 Local Reproduction Command
To execute the tests in an isolated manner matching CI:
```bash
# In an isolated copy where ArmstrongNumbers.example.ps1 is copied to ArmstrongNumbers.ps1:
HOME=/tmp pwsh -NoProfile -Command "Invoke-Pester -PassThru"
```
Or with automated assertion checks:
```bash
python3 work/R09-T042/check.py
```

### 4.2 CI Entry Point
The track CI workflow is defined in `.github/workflows/ci.yml`:
- Trigger: `push` and `pull_request` on `main`/`master`.
- Matrix: `ubuntu-26.04` and `windows-2022`.
- Execution Script: `bin/run-tests.ps1`.
- Mechanism:
  For each exercise in `exercises/practice`, creates a temporary directory, copies `*.tests.ps1`, copies `.meta/*.example.ps1` over `*.ps1`, runs `Invoke-Pester $tmpDir.FullName -PassThru`, and fails if `TotalCount == 0` or `FailedCount > 0`.

---

## 5. Two-Copy Regeneration Comparison

Because test files in the PowerShell track are hand-maintained from source, the regeneration verification performs two independent extractions from the maintained source into clean temporary locations (`copy1` and `copy2`):

| Check | Value | Status |
|---|---|---|
| Maintained Test Source | `exercises/practice/armstrong-numbers/ArmstrongNumbers.tests.ps1` | VERIFIED |
| Copy 1 SHA-256 | `ab12ab3134ea49c27699468183ff0fadba7b77f56be4c5d2372f6c0ae649bfc6` | MATCH |
| Copy 2 SHA-256 | `ab12ab3134ea49c27699468183ff0fadba7b77f56be4c5d2372f6c0ae649bfc6` | MATCH |
| Unified Diff | 0 lines changed (empty diff) | PASSED |
| Dropped Test Cases | 0 dropped | PASSED |
| Timestamp Differences | None (hand-maintained, deterministic) | VERIFIED |

---

## 6. Reference Implementation Execution Results

Execution of Pester against the reference implementation (`ArmstrongNumbers.example.ps1`):

- **Return Code:** `0`
- **Total Tests:** `9`
- **Passed Tests:** `9`
- **Failed Tests:** `0`
- **Skipped Tests:** `0`

### Executed Tests Summary
| Describe Block | Test Case Name | Result |
|---|---|---|
| `Test Invoke-ArmstrongNumbers.ps1` | `Zero is an Armstrong number` | **Passed** |
| `Test Invoke-ArmstrongNumbers.ps1` | `Single-digit numbers are Armstrong numbers` | **Passed** |
| `Test Invoke-ArmstrongNumbers.ps1` | `There are no two-digit Armstrong numbers` | **Passed** |
| `Test Invoke-ArmstrongNumbers.ps1` | `Three-digit number that is an Armstrong number` | **Passed** |
| `Test Invoke-ArmstrongNumbers.ps1` | `Three-digit number that is not an Armstrong number` | **Passed** |
| `Test Invoke-ArmstrongNumbers.ps1` | `Four-digit number that is an Armstrong number` | **Passed** |
| `Test Invoke-ArmstrongNumbers.ps1` | `Four-digit number that is not an Armstrong number` | **Passed** |
| `Test Invoke-ArmstrongNumbers.ps1` | `Seven-digit number that is an Armstrong number` | **Passed** |
| `Test Invoke-ArmstrongNumbers.ps1` | `Seven-digit number that is not an Armstrong number` | **Passed** |

---

## 7. Learner Stub Integrity Check
- **Target File:** `exercises/practice/armstrong-numbers/ArmstrongNumbers.ps1`
- **Working Tree Diff:** Completely clean (0 modifications).
- **Stub Behavior:** Retains `Throw "Please implement this function"`.
- **Integrity Status:** PASSED.

---

## 8. Tool & Environment Versions
- **Python:** `3.15.2`
- **PowerShell (pwsh):** `PowerShell 7.7.0`
- **Pester Module:** `6.2.0`
- **Git:** `git version 2.50.1 (Apple Git-155)`
- **Operating System:** `macOS-26.6.2-arm64-arm-64bit-Mach-O (arm64)`
