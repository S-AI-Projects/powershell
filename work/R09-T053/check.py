#!/usr/bin/env python3
"""
R09-T053 check.py — transpose mutation-driven regression runner.

Verifies:
  1. hints.md exists and contains the diagnostic input without publishing the full solution.
  2. docs/maintenance/transpose.md contains the mutation UUID and mutation description.
  3. The reference implementation passes all Pester test cases.
  4. The documented mutant (.TrimEnd() → .Trim()) fails exactly the named test
     "second line longer than first line" and passes the named anchored cases.
  5. The learner stub still fails (unsolved).
  6. check.py itself fails on a zero-test run, non-zero child exit, or assertion failure.

Saves evidence artifacts:
  - work/R09-T053/inputs.json
  - work/R09-T053/results.json
  - work/R09-T053/tool_versions.json
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

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EXERCISE_DIR = os.path.join(REPO_ROOT, "exercises", "practice", "transpose")
CONFIG_PATH = os.path.join(EXERCISE_DIR, ".meta", "config.json")
WORK_DIR = os.path.join(REPO_ROOT, "work", "R09-T053")
HINTS_MD = os.path.join(EXERCISE_DIR, ".docs", "hints.md")
MAINTENANCE_MD = os.path.join(REPO_ROOT, "docs", "maintenance", "transpose.md")

# Mutation details
OLD_STR = ".TrimEnd()"
NEW_STR = ".Trim()"

# Named test cases per issue spec
NAMED_PASS_1 = "empty string"
NAMED_PASS_2 = "two characters in a row"
NAMED_FAIL = "second line longer than first line"
REJECTING_UUID = "984e2ec3-b3d3-4b53-8bd6-96f5ef404102"
DESCRIBE_BLOCK = "Transpose test cases"

# Smallest diagnostic input that distinguishes original from mutant
DIAG_INPUT = "AB\nDEF"
DIAG_EXPECTED_ORIGINAL = "AD\nBE\n F"
DIAG_EXPECTED_MUTANT = "AD\nBE\nF"


def pwsh_env():
    return dict(os.environ, HOME=tempfile.gettempdir())


def get_tool_versions():
    env = pwsh_env()
    v = {"python": platform.python_version(), "platform": platform.platform()}
    try:
        r = subprocess.run(
            ["pwsh", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
            capture_output=True, text=True, env=env, timeout=30
        )
        v["powershell"] = r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception as e:
        v["powershell"] = f"error: {e}"
    try:
        r = subprocess.run(
            ["pwsh", "-NoProfile", "-Command",
             "(Get-Module Pester -ListAvailable | Select-Object -First 1).Version.ToString()"],
            capture_output=True, text=True, env=env, timeout=30
        )
        v["pester"] = r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception as e:
        v["pester"] = f"error: {e}"
    return v


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def copy_exercise_to_tmpdir(tmpdir, example_override=None, keep_stub=False):
    """Copy exercise directory to tmpdir, optionally replacing the example file and substituting into solution."""
    dst = os.path.join(tmpdir, "transpose")
    shutil.copytree(EXERCISE_DIR, dst)

    cfg = load_config()
    solution_rel = cfg["files"]["solution"][0]
    example_rel = cfg["files"]["example"][0]

    solution_path = os.path.join(dst, solution_rel)
    example_path = os.path.join(dst, example_rel)

    if not keep_stub:
        if example_override is not None:
            with open(example_path, "w", encoding="utf-8") as f:
                f.write(example_override)
            with open(solution_path, "w", encoding="utf-8") as f:
                f.write(example_override)
        else:
            with open(example_path, "r", encoding="utf-8") as f:
                content = f.read()
            with open(solution_path, "w", encoding="utf-8") as f:
                f.write(content)

    return dst


def read_example():
    cfg = load_config()
    example_rel = cfg["files"]["example"][0]
    example_path = os.path.join(EXERCISE_DIR, example_rel)
    with open(example_path, "r", encoding="utf-8") as f:
        return f.read()


def make_mutant_code(original_code):
    assert OLD_STR in original_code, f"Mutation target '{OLD_STR}' not found in reference code"
    count = original_code.count(OLD_STR)
    assert count == 1, f"Expected exactly 1 occurrence of '{OLD_STR}', found {count}"
    return original_code.replace(OLD_STR, NEW_STR, 1)


def run_pester_in_copy(exercise_copy):
    """Run Pester tests inside exercise_copy using _runner.ps1 and return execution details."""
    cfg = load_config()
    test_rel = cfg["files"]["test"][0]

    runner = f"""
$c = New-PesterConfiguration
$c.Run.Path = './{test_rel}'
$c.Run.PassThru = $true
$c.Output.Verbosity = 'Detailed'

$r = Invoke-Pester -Configuration $c
$executed = ($r.Tests | Where-Object {{ $_.Executed }}).Count

Write-Output ("TOTAL:"    + $r.TotalCount)
Write-Output ("FAILED:"   + $r.FailedCount)
Write-Output ("PASSED:"   + $r.PassedCount)
Write-Output ("SKIPPED:"  + $r.SkippedCount)
Write-Output ("NOTRUN:"   + $r.NotRunCount)
Write-Output ("EXECUTED:" + $executed)

foreach ($t in $r.Tests) {{
    $s = if ($t.Result -eq 'Passed') {{ 'PASS' }} elseif ($t.Result -eq 'Failed') {{ 'FAIL' }} else {{ $t.Result }}
    Write-Output ("CASE:" + $s + ":" + $t.ExpandedName)
}}

if ($r.FailedCount -gt 0) {{
    exit 1
}}
if ($executed -eq 0 -or $r.TotalCount -eq 0) {{
    exit 42
}}
"""
    runner_path = os.path.join(exercise_copy, "_runner.ps1")
    with open(runner_path, "w", encoding="utf-8") as f:
        f.write(runner)

    r = subprocess.run(
        ["pwsh", "-NoProfile", "-File", "_runner.ps1"],
        capture_output=True, text=True,
        cwd=exercise_copy, env=pwsh_env()
    )
    return r


def parse_pester_output(stdout, stderr):
    total = failed = passed = skipped = notrun = executed = 0
    cases = {}
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("TOTAL:"):
            total = int(line.split(":", 1)[1])
        elif line.startswith("FAILED:"):
            failed = int(line.split(":", 1)[1])
        elif line.startswith("PASSED:"):
            passed = int(line.split(":", 1)[1])
        elif line.startswith("SKIPPED:"):
            skipped = int(line.split(":", 1)[1])
        elif line.startswith("NOTRUN:"):
            notrun = int(line.split(":", 1)[1])
        elif line.startswith("EXECUTED:"):
            executed = int(line.split(":", 1)[1])
        elif line.startswith("CASE:"):
            parts = line.split(":", 2)
            if len(parts) == 3:
                status = parts[1]
                name = parts[2]
                cases[name] = status
    return {
        "total": total,
        "failed": failed,
        "passed": passed,
        "skipped": skipped,
        "notrun": notrun,
        "executed": executed,
        "cases": cases,
    }


def find_case_status(cases, case_name):
    for name, status in cases.items():
        if case_name in name:
            return status
    return None


def run_reference():
    """Run original reference — expect all tests to pass."""
    print("=== Mode: REFERENCE (original) ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        dst = copy_exercise_to_tmpdir(tmpdir)
        r = run_pester_in_copy(dst)

    parsed = parse_pester_output(r.stdout, r.stderr)
    print(f"  Total: {parsed['total']}, Passed: {parsed['passed']}, Failed: {parsed['failed']}, ReturnCode: {r.returncode}")

    if parsed["total"] == 0 or parsed["executed"] == 0:
        print(f"STDOUT:\n{r.stdout}")
        print(f"STDERR:\n{r.stderr}")
        sys.exit("FAIL: Reference run executed 0 tests")

    if r.returncode != 0:
        print(f"STDOUT:\n{r.stdout}")
        print(f"STDERR:\n{r.stderr}")
        sys.exit(f"FAIL: Reference run failed with returncode {r.returncode}")

    # Named anchored cases must pass
    for name in [NAMED_PASS_1, NAMED_PASS_2]:
        status = find_case_status(parsed["cases"], name)
        if status != "PASS":
            sys.exit(f"FAIL: Named case '{name}' did not PASS on reference (got: {status})")
        print(f"  ✓ '{name}' PASS on reference")

    if parsed["failed"] > 0:
        sys.exit(f"FAIL: Reference failed {parsed['failed']} test(s)")

    print(f"  ✓ All {parsed['total']} tests passed on reference")
    return parsed


def run_mutant():
    """Run mutant — expect exactly the named test to fail."""
    print("=== Mode: MUTANT (.TrimEnd() → .Trim()) ===")
    original_code = read_example()
    mutant_code = make_mutant_code(original_code)

    with tempfile.TemporaryDirectory() as tmpdir:
        dst = copy_exercise_to_tmpdir(tmpdir, example_override=mutant_code)
        r = run_pester_in_copy(dst)

    parsed = parse_pester_output(r.stdout, r.stderr)
    print(f"  Total: {parsed['total']}, Passed: {parsed['passed']}, Failed: {parsed['failed']}, ReturnCode: {r.returncode}")

    if parsed["total"] == 0:
        sys.exit("FAIL: Mutant run executed 0 tests")

    # Named pass cases must still pass on mutant
    for name in [NAMED_PASS_1, NAMED_PASS_2]:
        status = find_case_status(parsed["cases"], name)
        if status != "PASS":
            sys.exit(f"FAIL: Named case '{name}' should PASS on mutant (got: {status})")
        print(f"  ✓ '{name}' PASS on mutant (expected)")

    # Named failing case must fail on mutant
    fail_status = find_case_status(parsed["cases"], NAMED_FAIL)
    if fail_status != "FAIL":
        sys.exit(f"FAIL: Named case '{NAMED_FAIL}' should FAIL on mutant (got: {fail_status})")
    print(f"  ✓ '{NAMED_FAIL}' FAIL on mutant (expected — mutant correctly rejected)")

    if parsed["failed"] == 0:
        sys.exit("FAIL: Mutant passed all tests — mutation has no effect, choose a different mutation")

    return parsed


def run_stub():
    """Run learner stub — expect all tests to fail."""
    print("=== Mode: STUB (learner — unsolved) ===")
    cfg = load_config()
    solution_rel = cfg["files"]["solution"][0]
    stub_path = os.path.join(EXERCISE_DIR, solution_rel)
    with open(stub_path, "r", encoding="utf-8") as f:
        stub_content = f.read()

    # Confirm stub is unsolved
    if "Throw" not in stub_content and "throw" not in stub_content.lower():
        sys.exit("FAIL: Learner stub appears to be solved — it should still throw")
    print("  ✓ Learner stub contains Throw (unsolved)")

    with tempfile.TemporaryDirectory() as tmpdir:
        dst = copy_exercise_to_tmpdir(tmpdir, keep_stub=True)
        r = run_pester_in_copy(dst)

    parsed = parse_pester_output(r.stdout, r.stderr)
    print(f"  Total: {parsed['total']}, Passed: {parsed['passed']}, Failed: {parsed['failed']}, ReturnCode: {r.returncode}")

    if parsed["total"] == 0:
        sys.exit("FAIL: Stub run executed 0 tests")
    if parsed["passed"] > 0:
        sys.exit(f"FAIL: Stub passed {parsed['passed']} test(s) — stub should not solve any cases")
    print(f"  ✓ Stub failed all {parsed['total']} tests (learner still unsolved)")
    return parsed


def check_hints_md():
    """Verify hints.md exists, contains diagnostic context, does not contain full solution."""
    print("=== Check: hints.md ===")
    if not os.path.exists(HINTS_MD):
        sys.exit(f"FAIL: hints.md not found at {HINTS_MD}")
    with open(HINTS_MD, "r", encoding="utf-8") as f:
        content = f.read()

    if " F" not in content:
        sys.exit('FAIL: hints.md must mention the diagnostic output " F" (leading space)')

    forbidden = [".TrimEnd()", "TrimEnd", "$lines = $Text -replace"]
    for token in forbidden:
        if token in content:
            sys.exit(f"FAIL: hints.md must not contain '{token}' (reveals implementation detail)")

    print("  ✓ hints.md exists and contains diagnostic context without publishing the full solution")


def check_maintenance_md():
    """Verify docs/maintenance/transpose.md contains required fields."""
    print("=== Check: docs/maintenance/transpose.md ===")
    if not os.path.exists(MAINTENANCE_MD):
        sys.exit(f"FAIL: maintenance doc not found at {MAINTENANCE_MD}")
    with open(MAINTENANCE_MD, "r", encoding="utf-8") as f:
        content = f.read()

    required = [
        (REJECTING_UUID, "rejecting UUID"),
        (NAMED_FAIL, "rejecting test name"),
        ("TrimEnd", "mutation description (TrimEnd)"),
        ("Trim()", "mutation description (Trim())"),
        ("AB", "smallest diagnostic input"),
    ]
    for token, label in required:
        if token not in content:
            sys.exit(f"FAIL: docs/maintenance/transpose.md missing {label} ('{token}')")
    print(f"  ✓ docs/maintenance/transpose.md contains all required fields")


def save_artifacts(ref_result, mutant_result, stub_result):
    os.makedirs(WORK_DIR, exist_ok=True)

    inputs = {
        "exercise": "transpose",
        "task": "R09-T053",
        "mutation": {"old": OLD_STR, "new": NEW_STR},
        "rejecting_uuid": REJECTING_UUID,
        "rejecting_test_name": NAMED_FAIL,
        "named_pass": [NAMED_PASS_1, NAMED_PASS_2],
        "diagnostic_input": DIAG_INPUT,
        "diagnostic_expected_original": DIAG_EXPECTED_ORIGINAL,
        "diagnostic_expected_mutant": DIAG_EXPECTED_MUTANT,
    }
    with open(os.path.join(WORK_DIR, "inputs.json"), "w", encoding="utf-8") as f:
        json.dump(inputs, f, indent=2)

    results = {
        "reference": ref_result,
        "mutant": mutant_result,
        "stub": stub_result,
    }
    with open(os.path.join(WORK_DIR, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    versions = get_tool_versions()
    with open(os.path.join(WORK_DIR, "tool_versions.json"), "w", encoding="utf-8") as f:
        json.dump(versions, f, indent=2)

    print(f"  ✓ Artifacts saved to {WORK_DIR}")


def main():
    print(f"R09-T053 check.py — transpose mutation-driven regression")
    print(f"Repo root: {REPO_ROOT}\n")

    check_hints_md()
    check_maintenance_md()

    ref_result = run_reference()
    mutant_result = run_mutant()
    stub_result = run_stub()

    save_artifacts(ref_result, mutant_result, stub_result)

    print("\n=== ALL CHECKS PASSED ===")
    print(f"Reference: {ref_result['total']} tests, all passed")
    print(f"Mutant: {mutant_result['total']} tests, {mutant_result['failed']} failed (expected)")
    print(f"Stub: {stub_result['total']} tests, all failed (learner unsolved)")
    sys.exit(0)


if __name__ == "__main__":
    main()
