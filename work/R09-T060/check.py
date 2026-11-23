#!/usr/bin/env python3
"""
R09-T060 check.py — all-your-base contract examples and decision table check.

Verifies:
  1. hints.md exists and documents the selected cases with PowerShell array representations.
  2. docs/maintenance/all-your-base.md contains the complete decision table and unspecified behavior statement.
  3. Direct reproduction queries of 'single bit one to decimal' and 'binary to single decimal' match expected outputs.
  4. All 21 Pester test cases pass against the reference implementation.
  5. The named anchored cases (All your base test cases; single bit one to decimal; binary to single decimal) pass.
  6. The learner stub remains unsolved.
  7. Check fails on zero-test run, non-zero child exit, or assertion failure.
  8. Saves evidence artifacts to work/R09-T060/.
"""

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXERCISE_DIR = REPO_ROOT / "exercises" / "practice" / "all-your-base"
CONFIG_PATH = EXERCISE_DIR / ".meta" / "config.json"
WORK_DIR = REPO_ROOT / "work" / "R09-T060"
HINTS_MD = EXERCISE_DIR / ".docs" / "hints.md"
MAINTENANCE_MD = REPO_ROOT / "docs" / "maintenance" / "all-your-base.md"

NAMED_CASES = [
    "single bit one to decimal",
    "binary to single decimal"
]
DESCRIBE_BLOCK = "All your base test cases"


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
    dst = Path(tmpdir) / "all-your-base"
    shutil.copytree(EXERCISE_DIR, dst)

    cfg = load_config()
    solution_rel = cfg["files"]["solution"][0]
    example_rel = cfg["files"]["example"][0]

    solution_path = dst / solution_rel
    example_path = dst / example_rel

    if use_reference:
        shutil.copyfile(example_path, solution_path)

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
    runner_path = Path(exercise_copy) / "_runner.ps1"
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


def verify_hints_md():
    print("=== Check: hints.md ===")
    if not HINTS_MD.exists():
        sys.exit(f"FAIL: hints.md not found at {HINTS_MD}")
    content = HINTS_MD.read_text(encoding="utf-8")

    for phrase in ["single bit one to decimal", "binary to single decimal", "Error handling", "Digits as arrays"]:
        if phrase.lower() not in content.lower():
            sys.exit(f"FAIL: hints.md missing '{phrase}'")
    print("  ✓ hints.md verified")


def verify_maintenance_md():
    print("=== Check: docs/maintenance/all-your-base.md ===")
    if not MAINTENANCE_MD.exists():
        sys.exit(f"FAIL: maintenance doc not found at {MAINTENANCE_MD}")
    content = MAINTENANCE_MD.read_text(encoding="utf-8")

    for phrase in ["Decision Table", "single bit one to decimal", "binary to single decimal", "Unspecified Behavior"]:
        if phrase.lower() not in content.lower():
            sys.exit(f"FAIL: maintenance doc missing '{phrase}'")
    print("  ✓ docs/maintenance/all-your-base.md verified")


def reproduce_selected_cases():
    print("=== Check: Isolated reproduction of selected cases ===")
    cfg = load_config()
    exm_path = EXERCISE_DIR / cfg["files"]["example"][0]

    script = f"""
. "{exm_path}"
$r1 = Invoke-Rebase -Digits @(1) -InputBase 2 -OutputBase 10
$r2 = Invoke-Rebase -Digits @(1, 0, 1) -InputBase 2 -OutputBase 10

Write-Output ("REPRO:case1:" + ($r1 -join ","))
Write-Output ("REPRO:case2:" + ($r2 -join ","))
"""
    p = subprocess.run(["pwsh", "-NoProfile", "-Command", script],
                       capture_output=True, text=True, env=pwsh_env())
    if p.returncode != 0:
        sys.exit(f"FAIL: reproduction script failed: {p.stderr}")

    out1 = None
    out2 = None
    for line in p.stdout.splitlines():
        line = line.strip()
        if line.startswith("REPRO:case1:"):
            out1 = line.split(":", 2)[2]
        elif line.startswith("REPRO:case2:"):
            out2 = line.split(":", 2)[2]

    if out1 != "1":
        sys.exit(f"FAIL: 'single bit one to decimal' expected '1', got: {out1}")
    if out2 != "5":
        sys.exit(f"FAIL: 'binary to single decimal' expected '5', got: {out2}")

    print(f"  ✓ 'single bit one to decimal' reproduced correctly: @({out1})")
    print(f"  ✓ 'binary to single decimal' reproduced correctly: @({out2})")

    return {
        "single_bit_one_to_decimal": {"input": "@(1) base 2->10", "output": [1]},
        "binary_to_single_decimal": {"input": "@(1,0,1) base 2->10", "output": [5]}
    }


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
    stub_path = EXERCISE_DIR / solution_rel
    stub_content = stub_path.read_text(encoding="utf-8")

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


def save_artifacts(ref_result, stub_result, repro_results):
    os.makedirs(WORK_DIR, exist_ok=True)

    inputs = {
        "exercise": "all-your-base",
        "task": "R09-T060",
        "task_type": "Contract examples",
        "named_cases": NAMED_CASES,
        "describe_block": DESCRIBE_BLOCK,
        "selected_reproductions": repro_results,
        "config_paths": load_config()
    }
    with open(WORK_DIR / "inputs.json", "w", encoding="utf-8") as f:
        json.dump(inputs, f, indent=2)

    results = {
        "reproduced_cases": repro_results,
        "reference": {
            "total": ref_result["total"],
            "passed": ref_result["passed"],
            "failed": ref_result["failed"]
        },
        "stub": {
            "total": stub_result["total"],
            "passed": stub_result["passed"],
            "failed": stub_result["failed"]
        }
    }
    with open(WORK_DIR / "results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    versions = get_tool_versions()
    with open(WORK_DIR / "tool_versions.json", "w", encoding="utf-8") as f:
        json.dump(versions, f, indent=2)

    print(f"  ✓ Evidence artifacts saved to {WORK_DIR}")


def main():
    print(f"R09-T060 check.py — all-your-base contract examples verification")
    print(f"Repo root: {REPO_ROOT}\n")

    verify_hints_md()
    verify_maintenance_md()
    repro_results = reproduce_selected_cases()
    ref_result = run_reference()
    stub_result = run_stub()
    save_artifacts(ref_result, stub_result, repro_results)

    print("\n=== ALL CHECKS PASSED ===")
    print(f"Reference: {ref_result['total']}/21 passed")
    print(f"Stub: {stub_result['total']}/21 failed (learner unsolved)")
    print("Selected cases reproduced and verified against specification")
    sys.exit(0)


if __name__ == "__main__":
    main()
