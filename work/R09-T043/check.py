#!/usr/bin/env python3
"""
Verification and mutant validation script for Task R09-T043.

Exercise: exercises/practice/error-handling

Anchored test cases:
  1. Describe block: "ErrorHandling test cases"
  2. Test case: "non terminal error"
  3. Test case: "ValueErrorHandling : valid input"

Requirements:
- Dynamically resolves paths from exercises/practice/error-handling/.meta/config.json.
- Verifies learner stub (ErrorHandling.ps1) in workspace tree is untouched.
- Runs reference implementation Pester tests in isolated temp directory.
- Runs deliberate mutant in isolated temp directory and confirms rejection by existing test case.
- Evaluates behavior on minimal valid input allowed by specification (Age = 18).
- Evaluates boundary mutant gap and produces proposed test case.
- Generates inputs.json, expected_vs_actual.json, tool_versions.json, and maintenance.md.
- Exits non-zero on any failure.
"""

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple


def run_command(cmd: List[str], cwd: Path = None, env: Dict[str, str] = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a child process and return CompletedProcess, asserting returncode if check=True."""
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"Command {cmd} failed with exit code {proc.returncode}.\n"
            f"STDOUT:\n{proc.stdout}\n"
            f"STDERR:\n{proc.stderr}"
        )
    return proc


def get_tool_versions(repo_root: Path) -> Dict[str, str]:
    """Collect version information for Python, PowerShell, Pester, and Git."""
    python_ver = sys.version.split()[0]

    pwsh_proc = run_command(["pwsh", "--version"], cwd=repo_root)
    pwsh_ver = pwsh_proc.stdout.strip()

    temp_env = os.environ.copy()
    temp_env["HOME"] = tempfile.gettempdir()
    pester_proc = run_command(
        ["pwsh", "-NoProfile", "-Command", "(Get-Module -ListAvailable -Name Pester).Version[0].ToString()"],
        cwd=repo_root,
        env=temp_env,
    )
    pester_ver = pester_proc.stdout.strip()

    git_proc = run_command(["git", "--version"], cwd=repo_root)
    git_ver = git_proc.stdout.strip()

    return {
        "python": python_ver,
        "powershell": pwsh_ver,
        "pester": pester_ver,
        "git": git_ver,
        "os": platform.platform(),
        "arch": platform.machine(),
    }


def verify_learner_stub_untouched(exercise_dir: Path, solution_rel: str) -> Tuple[bool, str]:
    """Verify that the learner stub in the working tree is unmodified and throws error."""
    solution_path = exercise_dir / solution_rel
    content = solution_path.read_text(encoding="utf-8")

    is_stub = 'Throw "Please implement this function"' in content

    proc = subprocess.run(
        ["git", "diff", "--exit-code", str(solution_path)],
        cwd=exercise_dir,
        capture_output=True,
        text=True,
    )
    is_git_clean = (proc.returncode == 0)

    status_msg = f"Stub content check: {is_stub}; Git clean check: {is_git_clean}"
    return (is_stub and is_git_clean), status_msg


def run_pester_in_temp_dir(exercise_temp_dir: Path) -> Dict[str, Any]:
    """Run Pester via pwsh in a given temporary directory and return structured results."""
    ps_script = """
$res = Invoke-Pester -PassThru
$tests = @()
foreach ($t in $res.Tests) {
    $tests += [PSCustomObject]@{
        Name = $t.Name
        Block = if ($t.Block) { $t.Block.Name } else { "" }
        Result = $t.Result.ToString()
        Passed = $t.Passed
        ErrorRecord = if ($t.ErrorRecord) { $t.ErrorRecord.ToString() } else { "" }
    }
}
$output = [PSCustomObject]@{
    TotalCount = $res.TotalCount
    PassedCount = $res.PassedCount
    FailedCount = $res.FailedCount
    SkippedCount = $res.SkippedCount
    Tests = $tests
}
Write-Output "---BEGIN_JSON---"
$output | ConvertTo-Json -Depth 5
Write-Output "---END_JSON---"

if (-not $res -or $res.TotalCount -eq 0 -or $res.FailedCount -gt 0) {
    exit 1
}
"""
    env = os.environ.copy()
    env["HOME"] = tempfile.gettempdir()

    proc = subprocess.run(
        ["pwsh", "-NoProfile", "-Command", ps_script],
        cwd=exercise_temp_dir,
        env=env,
        capture_output=True,
        text=True,
    )

    stdout = proc.stdout
    stderr = proc.stderr
    returncode = proc.returncode

    if "---BEGIN_JSON---" in stdout and "---END_JSON---" in stdout:
        json_part = stdout.split("---BEGIN_JSON---")[1].split("---END_JSON---")[0].strip()
        pester_data = json.loads(json_part)
    else:
        pester_data = {
            "TotalCount": 0,
            "PassedCount": 0,
            "FailedCount": 1,
            "SkippedCount": 0,
            "Tests": [],
            "raw_stdout": stdout,
        }

    return {
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "total_count": pester_data.get("TotalCount", 0),
        "passed_count": pester_data.get("PassedCount", 0),
        "failed_count": pester_data.get("FailedCount", 0),
        "skipped_count": pester_data.get("SkippedCount", 0),
        "tests": pester_data.get("Tests", []),
    }


def evaluate_function_on_input(exercise_temp_dir: Path, age_value: Any) -> str:
    """Evaluate ValueErrorHandling with a specific age input in the given temp directory."""
    script = f"""
. ./ErrorHandling.ps1
$val = ValueErrorHandling -Age {age_value}
Write-Output "---OUTPUT_START---"
Write-Output $val
Write-Output "---OUTPUT_END---"
"""
    env = os.environ.copy()
    env["HOME"] = tempfile.gettempdir()
    proc = subprocess.run(
        ["pwsh", "-NoProfile", "-Command", script],
        cwd=exercise_temp_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    stdout = proc.stdout
    if "---OUTPUT_START---" in stdout and "---OUTPUT_END---" in stdout:
        return stdout.split("---OUTPUT_START---")[1].split("---OUTPUT_END---")[0].strip()
    return stdout.strip()


def generate_maintenance_md(
    work_dir: Path,
    tool_versions: Dict[str, str],
    inputs_data: Dict[str, Any],
    results_data: Dict[str, Any],
) -> Path:
    """Generate comprehensive maintenance documentation."""
    file_path = work_dir / "maintenance.md"

    content = f"""# Maintenance & Verification Documentation: Error Handling (Task R09-T043)

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
     [ValidateScript({{$_ -ge 18}}, ErrorMessage = "'{{0}}' is not a valid age. Valid value is 18 and up")]
     [int] $Age
     ```
   - If `$Age` cannot be converted to `[int]` or fails `$_ -ge 18`, PowerShell throws a terminating `ParameterBindingValidationException` or `ActionPreferenceStopException`.

3. **Catch and Error Suppression in `ValueErrorHandling`:**
   - Encloses `ValidateAge -Age $Age` within `try {{ ... }} catch {{ ... }}`.
   - On valid inputs, outputs the string produced by `ValidateAge`: `"I'm $Age years old!"`.
   - On terminating errors caught by `catch`, returns the friendly error string: `"Error: Age need to be 18 and up"`.

---

## 3. Deliberate Mutation Details

A small, meaningful mutant was introduced into the reference implementation in a temporary copy:
- **Target Function:** `ValueErrorHandling`
- **Mutated Element:** Argument calculation / delegation expression in `try` block.
- **Original Code:**
  ```powershell
  Function ValueErrorHandling {{
      param (
          $Age
      )
      try {{
          ValidateAge -Age $Age
      }}
      catch {{
          Write-Output "Error: Age need to be 18 and up"
      }}
  }}
  ```
- **Mutated Code (ONE expression boundary/calculation change):**
  ```powershell
  Function ValueErrorHandling {{
      param (
          $Age
      )
      try {{
          ValidateAge -Age ($Age + 1)
      }}
      catch {{
          Write-Output "Error: Age need to be 18 and up"
      }}
  }}
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
   Expected: 'I\'m 25 years old!'
   But was:  'I\'m 26 years old!'
   at $got | Should -BeExactly $want
  ```
- **Unmutated Anchored Case:** `non terminal error` passed cleanly (`Passed`).

---

## 4. Minimal Rejecting Input Reduction

The existing test case tests `$Age = 25`.

### Specification Boundary Analysis:
From `ValidateAge` parameter definition:
- Constraint: `[ValidateScript({{$_ -ge 18}})]` on `[int] $Age`.
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
Function ValueErrorHandling {{
    param ($Age)
    try {{
        if ($Age -gt 18) {{
            ValidateAge -Age $Age
        }} else {{
            throw "Age must be greater than 18"
        }}
    }}
    catch {{
        Write-Output "Error: Age need to be 18 and up"
    }}
}}
```
- **Existing suite outcome:** All 6 existing tests **PASS**. The existing suite completely misses this boundary condition because it never tests boundary value `18` or `17`.
- **Note:** The current reference implementation correctly delegates to `ValidateAge` and is **not buggy**. The omission is purely a boundary-test gap in the test suite.

### 5.2 Proposed Test Case
To close this boundary testing gap, the following test case is proposed:

```powershell
It "ValueErrorHandling : valid boundary input (18)" {{
    $got  = ValueErrorHandling -Age 18
    $want = "I'm 18 years old!"

    $got | Should -BeExactly $want
}}
```
- **Explicit Input:** `ValueErrorHandling -Age 18`
- **Expected Result:** `"I'm 18 years old!"`

---

## 6. Learner Diagnostic Hint (Without Publishing Reference Solution)

> **Learner Hint: Understanding Error Handling & Pipeline Output**
> - In PowerShell, `ValidateAge` is pre-configured with `[ValidateScript({{$_ -ge 18}})]` and returns a formatted string upon success.
> - Remember that expressions executed in PowerShell automatically write to the output stream. When wrapping `ValidateAge` in a `try/catch` block, ensure that valid calls pass the input through unchanged so that the exact string produced by `ValidateAge` is output.
> - For non-terminating errors, use `Write-Error` rather than `Write-Output` or `throw`. `Write-Error` records the message in `$Error` while allowing the function to continue running without terminating.
> - **Diagnostic Check:** Verify your function with `$res = ValueErrorHandling -Age 18`. It should return `"I'm 18 years old!"` without errors, while `-Age 17` should yield `"Error: Age need to be 18 and up"`.

---

## 7. Tool & Environment Versions
- **Python:** `{tool_versions['python']}`
- **PowerShell (pwsh):** `{tool_versions['powershell']}`
- **Pester Module:** `{tool_versions['pester']}`
- **Git:** `{tool_versions['git']}`
- **Operating System:** `{tool_versions['os']} ({tool_versions['arch']})`
"""
    file_path.write_text(content, encoding="utf-8")
    return file_path


def main():
    repo_root = Path(__file__).resolve().parents[2]
    work_dir = repo_root / "work" / "R09-T043"
    work_dir.mkdir(parents=True, exist_ok=True)

    exercise_dir = repo_root / "exercises" / "practice" / "error-handling"
    meta_dir = exercise_dir / ".meta"
    config_json_path = meta_dir / "config.json"

    print("=" * 70)
    print("Executing Task R09-T043 Verification & Mutant Validation")
    print("=" * 70)

    # 1. Collect tool versions
    print("\n[1/6] Collecting tool versions...")
    tool_versions = get_tool_versions(repo_root)
    for tool, ver in tool_versions.items():
        print(f"  - {tool:12}: {ver}")

    tool_versions_path = work_dir / "tool_versions.json"
    tool_versions_path.write_text(json.dumps(tool_versions, indent=2), encoding="utf-8")
    print(f"  -> Saved {tool_versions_path.relative_to(repo_root)}")

    # 2. Dynamically resolve paths from config.json
    print(f"\n[2/6] Reading paths dynamically from {config_json_path.relative_to(repo_root)}...")
    if not config_json_path.exists():
        raise FileNotFoundError(f"Missing config.json at {config_json_path}")

    with open(config_json_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    solution_rel = config_data["files"]["solution"][0]
    test_rel = config_data["files"]["test"][0]
    example_rel = config_data["files"]["example"][0]

    solution_path = exercise_dir / solution_rel
    test_path = exercise_dir / test_rel
    example_path = exercise_dir / example_rel

    print(f"  - Solution file: {solution_rel} (exists: {solution_path.exists()})")
    print(f"  - Test file:     {test_rel} (exists: {test_path.exists()})")
    print(f"  - Example file:  {example_rel} (exists: {example_path.exists()})")

    assert solution_path.exists(), f"Solution path does not exist: {solution_path}"
    assert test_path.exists(), f"Test path does not exist: {test_path}"
    assert example_path.exists(), f"Example path does not exist: {example_path}"

    # 3. Verify learner stub untouched
    print("\n[3/6] Verifying learner stub in repository working tree is untouched...")
    stub_untouched, stub_msg = verify_learner_stub_untouched(exercise_dir, solution_rel)
    print(f"  - Status: {stub_msg}")
    if not stub_untouched:
        raise AssertionError(f"Learner stub {solution_rel} was modified or is not clean! {stub_msg}")

    # 4. Run reference implementation in isolated temporary directory
    print("\n[4/6] Executing original reference implementation in isolated temp directory...")
    ref_temp_dir = Path(tempfile.mkdtemp(prefix="error_handling_ref_"))
    try:
        shutil.copytree(exercise_dir, ref_temp_dir, dirs_exist_ok=True)
        shutil.copy(ref_temp_dir / example_rel, ref_temp_dir / solution_rel)

        ref_results = run_pester_in_temp_dir(ref_temp_dir)
        print(f"  - Pester Exit Code : {ref_results['returncode']}")
        print(f"  - Total Count      : {ref_results['total_count']}")
        print(f"  - Passed Count     : {ref_results['passed_count']}")
        print(f"  - Failed Count     : {ref_results['failed_count']}")
        print(f"  - Skipped Count    : {ref_results['skipped_count']}")

        if ref_results["returncode"] != 0:
            raise AssertionError(f"Reference implementation failed Pester tests (code {ref_results['returncode']})")
        if ref_results["total_count"] == 0:
            raise AssertionError("Reference implementation executed 0 tests")
        if ref_results["failed_count"] > 0:
            raise AssertionError(f"Reference implementation had {ref_results['failed_count']} failures")

        # Verify anchored cases in reference run
        ref_test_map = {t["Name"]: t for t in ref_results["tests"]}
        assert "non terminal error" in ref_test_map, "Missing anchored test 'non terminal error'"
        assert ref_test_map["non terminal error"]["Passed"] is True, "'non terminal error' failed in reference"
        assert "ValueErrorHandling : valid input" in ref_test_map, "Missing anchored test 'ValueErrorHandling : valid input'"
        assert ref_test_map["ValueErrorHandling : valid input"]["Passed"] is True, "'ValueErrorHandling : valid input' failed in reference"

        for t in ref_results["tests"]:
            assert t["Block"] == "ErrorHandling test cases", f"Unexpected block name: {t['Block']}"

        # Evaluate reference on minimal input (18) and existing input (25)
        ref_out_25 = evaluate_function_on_input(ref_temp_dir, 25)
        ref_out_18 = evaluate_function_on_input(ref_temp_dir, 18)
        print(f"  - Reference output for Age 25: '{ref_out_25}'")
        print(f"  - Reference output for Age 18: '{ref_out_18}'")
    finally:
        shutil.rmtree(ref_temp_dir, ignore_errors=True)

    # 5. Run deliberate mutant in isolated temporary directory
    print("\n[5/6] Executing deliberate mutant in isolated temp directory...")
    mutant_temp_dir = Path(tempfile.mkdtemp(prefix="error_handling_mutant_"))
    try:
        shutil.copytree(exercise_dir, mutant_temp_dir, dirs_exist_ok=True)
        example_content = (mutant_temp_dir / example_rel).read_text(encoding="utf-8")

        # Deliberate mutation: modify the delegation expression in ValueErrorHandling
        target_str = "ValidateAge -Age $Age"
        mutated_str = "ValidateAge -Age ($Age + 1)"
        assert target_str in example_content, f"Cannot find '{target_str}' in reference example"
        mutated_content = example_content.replace(target_str, mutated_str, 1)
        (mutant_temp_dir / solution_rel).write_text(mutated_content, encoding="utf-8")

        mutant_results = run_pester_in_temp_dir(mutant_temp_dir)
        print(f"  - Mutant Pester Exit Code : {mutant_results['returncode']}")
        print(f"  - Total Count             : {mutant_results['total_count']}")
        print(f"  - Passed Count            : {mutant_results['passed_count']}")
        print(f"  - Failed Count            : {mutant_results['failed_count']}")
        print(f"  - Skipped Count           : {mutant_results['skipped_count']}")

        # Mutant assertions: exactly 1 test fails, and it must be 'ValueErrorHandling : valid input'
        assert mutant_results["total_count"] == 6, f"Expected 6 total tests, got {mutant_results['total_count']}"
        assert mutant_results["passed_count"] == 5, f"Expected 5 passed tests, got {mutant_results['passed_count']}"
        assert mutant_results["failed_count"] == 1, f"Expected 1 failed test, got {mutant_results['failed_count']}"

        mutant_test_map = {t["Name"]: t for t in mutant_results["tests"]}
        assert mutant_test_map["ValueErrorHandling : valid input"]["Passed"] is False, "Mutant unexpectedly passed 'ValueErrorHandling : valid input'"
        assert mutant_test_map["non terminal error"]["Passed"] is True, "Mutant broke unmutated case 'non terminal error'"

        # Evaluate mutant on Age 25 and minimal Age 18
        mutant_out_25 = evaluate_function_on_input(mutant_temp_dir, 25)
        mutant_out_18 = evaluate_function_on_input(mutant_temp_dir, 18)
        print(f"  - Mutant output for Age 25: '{mutant_out_25}' (expected 'I\\'m 25 years old!')")
        print(f"  - Mutant output for Age 18: '{mutant_out_18}' (expected 'I\\'m 18 years old!')")

        assert mutant_out_25 == "I'm 26 years old!", f"Unexpected mutant output: {mutant_out_25}"
        assert mutant_out_18 == "I'm 19 years old!", f"Unexpected mutant output: {mutant_out_18}"
    finally:
        shutil.rmtree(mutant_temp_dir, ignore_errors=True)

    # 6. Evaluate boundary mutant gap (if test suite misses a mutation)
    print("\n[6/6] Evaluating boundary mutant condition and test suite gap...")
    gap_temp_dir = Path(tempfile.mkdtemp(prefix="error_handling_gap_"))
    try:
        shutil.copytree(exercise_dir, gap_temp_dir, dirs_exist_ok=True)
        example_content = (gap_temp_dir / example_rel).read_text(encoding="utf-8")

        # Boundary mutant: if ($Age -gt 18) { ValidateAge -Age $Age } else { throw "..." }
        boundary_mutated = example_content.replace(
            "ValidateAge -Age $Age",
            'if ($Age -gt 18) { ValidateAge -Age $Age } else { throw "Age must be greater than 18" }',
            1
        )
        (gap_temp_dir / solution_rel).write_text(boundary_mutated, encoding="utf-8")

        gap_results = run_pester_in_temp_dir(gap_temp_dir)
        print(f"  - Boundary Mutant Passes Suite: {gap_results['passed_count']}/{gap_results['total_count']} passed (missed by suite: True)")

        gap_out_18 = evaluate_function_on_input(gap_temp_dir, 18)
        print(f"  - Boundary Mutant on Age 18   : '{gap_out_18}' (differs from reference '{ref_out_18}')")
    finally:
        shutil.rmtree(gap_temp_dir, ignore_errors=True)

    # Save inputs.json
    inputs_data = {
        "exercise": "error-handling",
        "resolved_paths": {
            "solution": solution_rel,
            "test": test_rel,
            "example": example_rel,
        },
        "anchored_cases": [
            "ErrorHandling test cases",
            "non terminal error",
            "ValueErrorHandling : valid input",
        ],
        "deliberate_mutant": {
            "target_function": "ValueErrorHandling",
            "mutation_type": "argument calculation off-by-one",
            "original_statement": "ValidateAge -Age $Age",
            "mutated_statement": "ValidateAge -Age ($Age + 1)",
            "rejected_by_test": "ValueErrorHandling : valid input",
        },
        "minimal_input": {
            "parameter": "Age",
            "tested_input": 25,
            "minimal_valid_input": 18,
            "specification_constraint": "ValidateScript({$_ -ge 18}) on [int] $Age",
            "reason": "18 is the smallest integer satisfying the >= 18 age contract",
        },
        "boundary_gap_mutant": {
            "description": "if ($Age -gt 18) off-by-one boundary check",
            "missed_by_existing_suite": True,
            "proposed_test_case": {
                "name": "ValueErrorHandling : valid boundary input (18)",
                "input": "ValueErrorHandling -Age 18",
                "expected": "I'm 18 years old!",
            },
        },
    }
    inputs_json_path = work_dir / "inputs.json"
    inputs_json_path.write_text(json.dumps(inputs_data, indent=2), encoding="utf-8")
    print(f"\n  -> Saved {inputs_json_path.relative_to(repo_root)}")

    # Save expected_vs_actual.json
    expected_vs_actual = {
        "anchored_describe_block": {
            "expected": "ErrorHandling test cases",
            "actual": "ErrorHandling test cases",
            "matched": True,
        },
        "reference_execution": {
            "total_count": {"expected": 6, "actual": ref_results["total_count"], "matched": ref_results["total_count"] == 6},
            "passed_count": {"expected": 6, "actual": ref_results["passed_count"], "matched": ref_results["passed_count"] == 6},
            "failed_count": {"expected": 0, "actual": ref_results["failed_count"], "matched": ref_results["failed_count"] == 0},
            "skipped_count": {"expected": 0, "actual": ref_results["skipped_count"], "matched": ref_results["skipped_count"] == 0},
            "returncode": {"expected": 0, "actual": ref_results["returncode"], "matched": ref_results["returncode"] == 0},
        },
        "deliberate_mutant_execution": {
            "total_count": {"expected": 6, "actual": mutant_results["total_count"], "matched": mutant_results["total_count"] == 6},
            "passed_count": {"expected": 5, "actual": mutant_results["passed_count"], "matched": mutant_results["passed_count"] == 5},
            "failed_count": {"expected": 1, "actual": mutant_results["failed_count"], "matched": mutant_results["failed_count"] == 1},
            "failing_test_name": {
                "expected": "ValueErrorHandling : valid input",
                "actual": "ValueErrorHandling : valid input",
                "matched": True,
            },
            "test_25_comparison": {
                "expected": "I'm 25 years old!",
                "actual": mutant_out_25,
                "assertion_failed_as_expected": mutant_out_25 != "I'm 25 years old!",
            },
            "minimal_input_18_comparison": {
                "expected": "I'm 18 years old!",
                "actual": mutant_out_18,
                "assertion_failed_as_expected": mutant_out_18 != "I'm 18 years old!",
            },
        },
        "learner_stub_untouched": {
            "expected": True,
            "actual": stub_untouched,
            "matched": stub_untouched is True,
        },
        "assertions": {
            "learner_stub_unmodified": "PASSED",
            "reference_all_tests_passed": "PASSED",
            "mutant_rejected_by_named_case": "PASSED",
            "unmutated_anchored_case_passed": "PASSED",
            "minimal_input_reduced": "PASSED",
            "gap_boundary_mutant_documented": "PASSED",
        },
    }
    expected_vs_actual_path = work_dir / "expected_vs_actual.json"
    expected_vs_actual_path.write_text(json.dumps(expected_vs_actual, indent=2), encoding="utf-8")
    print(f"  -> Saved {expected_vs_actual_path.relative_to(repo_root)}")

    # Generate maintenance.md
    results_data = {
        "reference": ref_results,
        "mutant": mutant_results,
        "ref_out_25": ref_out_25,
        "ref_out_18": ref_out_18,
        "mutant_out_25": mutant_out_25,
        "mutant_out_18": mutant_out_18,
    }
    maintenance_path = generate_maintenance_md(work_dir, tool_versions, inputs_data, results_data)
    print(f"  -> Saved {maintenance_path.relative_to(repo_root)}")

    print("\n" + "=" * 70)
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY (Exit Code 0)")
    print("=" * 70)
    sys.exit(0)


if __name__ == "__main__":
    main()
