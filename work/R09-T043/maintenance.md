# Maintenance & Verification Documentation: Error Handling (Task R09-T043)

## 1. Goal & Anchored Cases
This document details the error-handling contract in `exercises/practice/error-handling`, presents deliberate mutant analysis against the reference implementation, reduces the rejecting input to the minimal input allowed by the specification, and documents any testing gaps.

Anchored verification test cases:
1. **`ErrorHandling test cases`** (Root Pester Describe block)
2. **`non terminal error`** (Pester test verifying non-terminating error handling via `$Error` collection and `Write-Error`)
3. **`ValueErrorHandling : valid input`** (Pester test verifying successful validation and delegation for valid age inputs)

---

## 2. PowerShell Error-Handling Contract Explanation

PowerShell distinguishes between two core classes of errors:

### 2.1 Terminating vs. Non-Terminating Errors
1. **Non-Terminating Errors (`Write-Error`):**
   - Issued when a command encounters an error that affects only an individual item or pipeline element, allowing processing to continue.
   - Appends an `[ErrorRecord]` to the automatic `$Error` collection.
   - Does not trigger a `try/catch` block unless `-ErrorAction Stop` or `$ErrorActionPreference = "Stop"` elevates it to a terminating error.
   - Tested by `non terminal error`:
     ```powershell
     $ErrorActionPreference = "SilentlyContinue"
     NonTerminationError
     $Error.Count | Should -BeGreaterThan 0
     $Error[0].Exception.Message | Should -Contain "Error: This is a non termination error"
     ```

2. **Terminating Errors (`throw` or `[CmdletBinding()]` Parameter Validation):**
   - Halts normal execution immediately and transfers control to the nearest enclosing `try/catch` or terminates the runspace.
   - `ValidateAge` enforces parameter constraints via:
     ```powershell
     [ValidateScript({$_ -ge 18}, ErrorMessage = "'{0}' is not a valid age. Valid value is 18 and up")]
     [int] $Age
     ```
   - If `$Age` cannot be converted to `[int]` or fails `$_ -ge 18`, PowerShell throws a terminating `ParameterBindingValidationException` or `ActionPreferenceStopException`.

3. **Catch and Error Suppression in `ValueErrorHandling`:**
   - Encloses `ValidateAge -Age $Age` within `try { ... } catch { ... }`.
   - On valid inputs, outputs the string produced by `ValidateAge`: `"I'm $Age years old!"`.
   - On terminating errors caught by `catch`, returns the friendly error string: `"Error: Age need to be 18 and up"`.

---

## 3. Deliberate Mutation Details

A small, meaningful mutant was introduced into the reference implementation in a temporary copy:
- **Target Function:** `ValueErrorHandling`
- **Mutated Element:** Argument calculation / delegation expression in `try` block.
- **Original Code:**
  ```powershell
  Function ValueErrorHandling {
      param (
          $Age
      )
      try {
          ValidateAge -Age $Age
      }
      catch {
          Write-Output "Error: Age need to be 18 and up"
      }
  }
  ```
- **Mutated Code (ONE expression boundary/calculation change):**
  ```powershell
  Function ValueErrorHandling {
      param (
          $Age
      )
      try {
          ValidateAge -Age ($Age + 1)
      }
      catch {
          Write-Output "Error: Age need to be 18 and up"
      }
  }
  ```

### 3.1 Rejection by Existing Test Suite
Running the full Pester test suite against the deliberate mutant yields:
- **Total Tests:** 6
- **Passed Tests:** 5
- **Failed Tests:** 1
- **Rejecting Test Case:** `ValueErrorHandling : valid input`
- **Failure Diagnostic:**
  ```text
  [-] ErrorHandling test cases.ValueErrorHandling : valid input
   Expected strings to be the same, but they were different.
   String lengths are both 17.
   Strings differ at index 5.
   Expected: 'I'm 25 years old!'
   But was:  'I'm 26 years old!'
   at $got | Should -BeExactly $want
  ```
- **Unmutated Anchored Case:** `non terminal error` passed cleanly (`Passed`).

---

## 4. Minimal Rejecting Input Reduction

The existing test case tests `$Age = 25`.

### Specification Boundary Analysis:
From `ValidateAge` parameter definition:
- Constraint: `[ValidateScript({$_ -ge 18})]` on `[int] $Age`.
- Specification rule: "An integer represent the age, it should be 18 or up."
- The **smallest input allowed by the specification** for a valid age is **`18`**.

### Input Reduction Comparison:
| Environment | Input (`-Age`) | Expected Output | Actual Output | Result |
|---|---|---|---|---|
| Existing Test Case | `25` | `"I'm 25 years old!"` | `"I'm 26 years old!"` | **FAILED** |
| Minimal Allowed Input | `18` | `"I'm 18 years old!"` | `"I'm 19 years old!"` | **FAILED** |

Both inputs reject the mutant, with `18` being the minimal valid input allowed by the specification.

---

## 5. Test Suite Gap & Proposed Test Case

### 5.1 Analysis of Potential Mutant Missed by Existing Suite
In `ErrorHandling.tests.ps1`, the test cases for `ValueErrorHandling` are:
1. `ValueErrorHandling : valid input` with `Age = 25` (an interior point well above 18).
2. `ValueErrorHandling : invalid inputs` with `Age = "ten"` (type failure) and `Age = 14` (interior failure point well below 18).

If a student or implementation introduces an off-by-one boundary check:
```powershell
Function ValueErrorHandling {
    param ($Age)
    try {
        if ($Age -gt 18) {
            ValidateAge -Age $Age
        } else {
            throw "Age must be greater than 18"
        }
    }
    catch {
        Write-Output "Error: Age need to be 18 and up"
    }
}
```
- **Existing suite outcome:** All 6 existing tests **PASS**. The existing suite completely misses this boundary condition because it never tests boundary value `18` or `17`.
- **Note:** The current reference implementation correctly delegates to `ValidateAge` and is **not buggy**. The omission is purely a boundary-test gap in the test suite.

### 5.2 Proposed Test Case
To close this boundary testing gap, the following test case is proposed:

```powershell
It "ValueErrorHandling : valid boundary input (18)" {
    $got  = ValueErrorHandling -Age 18
    $want = "I'm 18 years old!"

    $got | Should -BeExactly $want
}
```
- **Explicit Input:** `ValueErrorHandling -Age 18`
- **Expected Result:** `"I'm 18 years old!"`

---

## 6. Learner Diagnostic Hint (Without Publishing Reference Solution)

> **Learner Hint: Understanding Error Handling & Pipeline Output**
> - In PowerShell, `ValidateAge` is pre-configured with `[ValidateScript({$_ -ge 18})]` and returns a formatted string upon success.
> - Remember that expressions executed in PowerShell automatically write to the output stream. When wrapping `ValidateAge` in a `try/catch` block, ensure that valid calls pass the input through unchanged so that the exact string produced by `ValidateAge` is output.
> - For non-terminating errors, use `Write-Error` rather than `Write-Output` or `throw`. `Write-Error` records the message in `$Error` while allowing the function to continue running without terminating.
> - **Diagnostic Check:** Verify your function with `$res = ValueErrorHandling -Age 18`. It should return `"I'm 18 years old!"` without errors, while `-Age 17` should yield `"Error: Age need to be 18 and up"`.

---

## 7. Tool & Environment Versions
- **Python:** `3.15.2`
- **PowerShell (pwsh):** `PowerShell 7.7.0`
- **Pester Module:** `6.2.0`
- **Git:** `git version 2.50.1 (Apple Git-155)`
- **Operating System:** `macOS-26.6.2-arm64-arm-64bit-Mach-O (arm64)`
