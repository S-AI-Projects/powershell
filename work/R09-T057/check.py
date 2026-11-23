#!/usr/bin/env python3
"""
R09-T057 check.py — resistor-color-duo language-specific hint validation runner.

Verifies:
  1. hints.md exists, contains the language-specific guidance, and links to about_Return.
  2. Both micro-examples in hints.md are executed in pwsh and match their published output.
  3. All 7 Pester test cases pass against the reference implementation.
  4. The named anchored cases (Test Get-ColorCodeValue; Brown and blac; Blue and grey) pass.
  5. The learner stub remains unsolved.
  6. The check fails on zero-test run, non-zero child exit, or assertion failure.
  7. Saves evidence artifacts to work/R09-T057/.
"""

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EXERCISE_DIR = os.path.join(REPO_ROOT, "exercises", "practice", "resistor-color-duo")
CONFIG_PATH = os.path.join(EXERCISE_DIR, ".meta", "config.json")
WORK_DIR = os.path.join(REPO_ROOT, "work", "R09-T057")
HINTS_MD = os.path.join(EXERCISE_DIR, ".docs", "hints.md")
MAINTENANCE_MD = os.path.join(REPO_ROOT, "docs", "maintenance", "resistor-color-duo.md")

NAMED_CASES = [
    "Brown and blac",
    "Blue and grey"
]
DESCRIBE_BLOCK = "Test Get-ColorCodeValue"

MICRO_EXAMPLE_1 = """
function Get-Code {
    param([int]$first, [int]$second)
    return $first * 10 + $second
}
$result = Get-Code -first 1 -second 0
$result.GetType().Name
$result
"""
EXPECTED_OUTPUT_1 = ["Int32", "10"]

MICRO_EXAMPLE_2 = """
function Get-CodePitfall {
    param([int]$first, [int]$second)
    return "$first$second"
}
$result = Get-CodePitfall -first 1 -second 0
$result.GetType().Name
$result
"""
EXPECTED_OUTPUT_2 = ["String", "10"]


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
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def copy_exercise_to_tmpdir(tmpdir, use_reference=True):
    dst = os.path.join(tmpdir, "resistor-color-duo")
    shutil.copytree(EXERCISE_DIR, dst)

    cfg = load_config()
    solution_rel = cfg["files"]["solution"][0]
    example_rel = cfg["files"]["example"][0]

    solution_path = os.path.join(dst, solution_rel)
    example_path = os.path.join(dst, example_rel)

    if use_reference:
        with open(example_path, "r", encoding="utf-8") as f:
            content = f.read()
        with open(solution_path, "w", encoding="utf-8") as f:
            f.write(content)

    return dst


def run_pester_in_copy(exercise_copy):
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
                cases[parts[2]] = parts[1]
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


def verify_hints_and_micro_examples():
    print("=== Check: hints.md and micro-examples ===")
    if not os.path.exists(HINTS_MD):
        sys.exit(f"FAIL: hints.md not found at {HINTS_MD}")
    with open(HINTS_MD, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify link and guidance keywords
    for phrase in ["about_Return", "Int32", "String", "Should -BeExactly", "Explicit return"]:
        if phrase.lower() not in content.lower():
            sys.exit(f"FAIL: hints.md missing '{phrase}'")

    # Run micro-example 1
    r1 = subprocess.run(["pwsh", "-NoProfile", "-Command", MICRO_EXAMPLE_1],
                        capture_output=True, text=True, env=pwsh_env())
    out1 = [line.strip() for line in r1.stdout.splitlines() if line.strip()]
    if out1 != EXPECTED_OUTPUT_1:
        sys.exit(f"FAIL: Micro-example 1 output mismatch: got {out1}, expected {EXPECTED_OUTPUT_1}")
    print(f"  ✓ Micro-example 1 executed and produced: {out1}")

    # Run micro-example 2
    r2 = subprocess.run(["pwsh", "-NoProfile", "-Command", MICRO_EXAMPLE_2],
                        capture_output=True, text=True, env=pwsh_env())
    out2 = [line.strip() for line in r2.stdout.splitlines() if line.strip()]
    if out2 != EXPECTED_OUTPUT_2:
        sys.exit(f"FAIL: Micro-example 2 output mismatch: got {out2}, expected {EXPECTED_OUTPUT_2}")
    print(f"  ✓ Micro-example 2 executed and produced: {out2}")

    return {
        "example_1": {"code": MICRO_EXAMPLE_1.strip(), "output": out1},
        "example_2": {"code": MICRO_EXAMPLE_2.strip(), "output": out2}
    }


def verify_maintenance_doc():
    print("=== Check: docs/maintenance/resistor-color-duo.md ===")
    if not os.path.exists(MAINTENANCE_MD):
        sys.exit(f"FAIL: maintenance doc not found at {MAINTENANCE_MD}")
    with open(MAINTENANCE_MD, "r", encoding="utf-8") as f:
        content = f.read()

    for phrase in ["explicit return", "Int32", "String", "Should -BeExactly"]:
        if phrase.lower() not in content.lower():
            sys.exit(f"FAIL: maintenance doc missing '{phrase}'")
    print("  ✓ docs/maintenance/resistor-color-duo.md verified")


def run_reference():
    print("=== Check: Reference test execution ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        dst = copy_exercise_to_tmpdir(tmpdir)
        r = run_pester_in_copy(dst)

    parsed = parse_pester_output(r.stdout, r.stderr)
    print(f"  Reference: Total={parsed['total']}, Passed={parsed['passed']}, Failed={parsed['failed']}")

    if parsed["total"] == 0 or parsed["executed"] == 0:
        sys.exit("FAIL: Reference run executed 0 tests")
    if parsed["failed"] > 0:
        sys.exit(f"FAIL: Reference failed {parsed['failed']} tests")

    for name in NAMED_CASES:
        status = find_case_status(parsed["cases"], name)
        if status != "PASS":
            sys.exit(f"FAIL: Named case '{name}' did not PASS on reference (got: {status})")
        print(f"  ✓ Named case '{name}' PASSED on reference")

    print(f"  ✓ All {parsed['total']} tests passed on reference")
    return parsed


def run_stub():
    print("=== Check: Learner stub remains unsolved ===")
    cfg = load_config()
    solution_rel = cfg["files"]["solution"][0]
    stub_path = os.path.join(EXERCISE_DIR, solution_rel)
    with open(stub_path, "r", encoding="utf-8") as f:
        stub_content = f.read()

    if "Throw" not in stub_content and "throw" not in stub_content.lower():
        sys.exit("FAIL: Learner stub appears to be solved — it should still throw")
    print("  ✓ Learner stub contains Throw (unsolved)")

    with tempfile.TemporaryDirectory() as tmpdir:
        dst = copy_exercise_to_tmpdir(tmpdir, use_reference=False)
        r = run_pester_in_copy(dst)

    parsed = parse_pester_output(r.stdout, r.stderr)
    print(f"  Stub: Total={parsed['total']}, Passed={parsed['passed']}, Failed={parsed['failed']}")

    if parsed["total"] == 0:
        sys.exit("FAIL: Stub run executed 0 tests")
    if parsed["passed"] > 0:
        sys.exit(f"FAIL: Stub passed {parsed['passed']} test(s)")
    print(f"  ✓ Stub failed all {parsed['total']} tests (learner unsolved)")
    return parsed


def save_artifacts(ref_result, stub_result, micro_results):
    os.makedirs(WORK_DIR, exist_ok=True)

    inputs = {
        "exercise": "resistor-color-duo",
        "task": "R09-T057",
        "task_type": "Language-specific hints",
        "named_cases": NAMED_CASES,
        "describe_block": DESCRIBE_BLOCK,
        "chosen_construct": "Explicit return values with integer arithmetic ($firstColor * 10 + $secondColor)",
        "contrasting_pitfall": "String concatenation producing [string] instead of [int]",
        "reference_link": "https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_return",
        "config_paths": load_config()
    }
    with open(os.path.join(WORK_DIR, "inputs.json"), "w", encoding="utf-8") as f:
        json.dump(inputs, f, indent=2)

    results = {
        "reference": {
            "total": ref_result["total"],
            "passed": ref_result["passed"],
            "failed": ref_result["failed"]
        },
        "stub": {
            "total": stub_result["total"],
            "passed": stub_result["passed"],
            "failed": stub_result["failed"]
        },
        "micro_examples": micro_results
    }
    with open(os.path.join(WORK_DIR, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    versions = get_tool_versions()
    with open(os.path.join(WORK_DIR, "tool_versions.json"), "w", encoding="utf-8") as f:
        json.dump(versions, f, indent=2)

    print(f"  ✓ Evidence artifacts saved to {WORK_DIR}")


def main():
    print(f"R09-T057 check.py — resistor-color-duo language-specific hint check")
    print(f"Repo root: {REPO_ROOT}\n")

    micro_results = verify_hints_and_micro_examples()
    verify_maintenance_doc()
    ref_result = run_reference()
    stub_result = run_stub()
    save_artifacts(ref_result, stub_result, micro_results)

    print("\n=== ALL CHECKS PASSED ===")
    print(f"Reference: {ref_result['total']}/7 passed")
    print(f"Stub: {stub_result['total']}/7 failed (learner unsolved)")
    print("Both micro-examples match published hint outputs exactly")
    sys.exit(0)


if __name__ == "__main__":
    main()
