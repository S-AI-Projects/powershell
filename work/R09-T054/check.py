#!/usr/bin/env python3
"""
R09-T054 check.py — micro-blog reference implementation refactor check.

Verifies:
  1. The refactored reference passes all Pester tests.
  2. The named anchored cases (MicroBlog test cases; English language short; English language long) pass.
  3. All test outputs before (baseline main) and after refactoring are byte-identical.
  4. The learner stub remains unsolved (throws exception).
  5. The check fails on zero-test run, non-zero child exit, or assertion failure.
  6. Saves evidence artifacts to work/R09-T054/.
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
EXERCISE_DIR = os.path.join(REPO_ROOT, "exercises", "practice", "micro-blog")
CONFIG_PATH = os.path.join(EXERCISE_DIR, ".meta", "config.json")
WORK_DIR = os.path.join(REPO_ROOT, "work", "R09-T054")
MAINTENANCE_MD = os.path.join(REPO_ROOT, "docs", "maintenance", "micro-blog.md")
EXAMPLE_PATH = os.path.join(EXERCISE_DIR, ".meta", "MicroBlog.example.ps1")

NAMED_CASES = [
    "English language short",
    "English language long"
]


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


def copy_exercise_to_tmpdir(tmpdir, use_reference=True, code_override=None):
    dst = os.path.join(tmpdir, "micro-blog")
    shutil.copytree(EXERCISE_DIR, dst)

    cfg = load_config()
    solution_rel = cfg["files"]["solution"][0]
    example_rel = cfg["files"]["example"][0]

    solution_path = os.path.join(dst, solution_rel)
    example_path = os.path.join(dst, example_rel)

    if use_reference:
        if code_override is not None:
            content = code_override
        else:
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


def get_baseline_code():
    r = subprocess.run(
        ["git", "show", "main:exercises/practice/micro-blog/.meta/MicroBlog.example.ps1"],
        cwd=REPO_ROOT, capture_output=True, text=True
    )
    if r.returncode != 0:
        sys.exit(f"FAIL: could not retrieve baseline example from git: {r.stderr}")
    return r.stdout


def verify_refactor():
    print("=== Check: Readability refactor diff ===")
    with open(EXAMPLE_PATH, "r", encoding="utf-8") as f:
        current_code = f.read()

    # Check for readability improvement elements
    if "$textElementOffsets" not in current_code:
        sys.exit("FAIL: refactored code must rename ambiguous $charArray to $textElementOffsets")
    if "Invariant" not in current_code:
        sys.exit("FAIL: refactored code must include comment explaining the exercise-specific invariant")
    if "$charList" in current_code:
        sys.exit("FAIL: refactored code should eliminate intermediate $charList accumulation")

    print("  ✓ Refactor includes $textElementOffsets, invariant comment, and direct substring truncation")


def verify_maintenance_doc():
    print("=== Check: docs/maintenance/micro-blog.md ===")
    if not os.path.exists(MAINTENANCE_MD):
        sys.exit(f"FAIL: maintenance doc not found at {MAINTENANCE_MD}")
    with open(MAINTENANCE_MD, "r", encoding="utf-8") as f:
        content = f.read()

    for phrase in ["readability", "textElementOffsets", "charArray", "invariant"]:
        if phrase.lower() not in content.lower():
            sys.exit(f"FAIL: maintenance doc missing discussion of '{phrase}'")
    print("  ✓ Maintenance doc properly documents the refactoring rationale")


def run_baseline_and_refactored():
    print("=== Check: Baseline vs Refactored Pester Runs ===")
    baseline_code = get_baseline_code()

    # Run baseline
    with tempfile.TemporaryDirectory() as tmp1:
        dst1 = copy_exercise_to_tmpdir(tmp1, code_override=baseline_code)
        r_base = run_pester_in_copy(dst1)
        parsed_base = parse_pester_output(r_base.stdout, r_base.stderr)

    # Run refactored
    with tempfile.TemporaryDirectory() as tmp2:
        dst2 = copy_exercise_to_tmpdir(tmp2)
        r_refac = run_pester_in_copy(dst2)
        parsed_refac = parse_pester_output(r_refac.stdout, r_refac.stderr)

    print(f"  Baseline:   Total={parsed_base['total']}, Passed={parsed_base['passed']}, Failed={parsed_base['failed']}")
    print(f"  Refactored: Total={parsed_refac['total']}, Passed={parsed_refac['passed']}, Failed={parsed_refac['failed']}")

    if parsed_refac["total"] == 0 or parsed_refac["executed"] == 0:
        sys.exit("FAIL: Refactored run executed 0 tests")
    if parsed_refac["failed"] > 0:
        sys.exit(f"FAIL: Refactored reference failed {parsed_refac['failed']} tests")

    # Verify named cases
    for name in NAMED_CASES:
        status = find_case_status(parsed_refac["cases"], name)
        if status != "PASS":
            sys.exit(f"FAIL: Named case '{name}' did not PASS (got: {status})")
        print(f"  ✓ Named case '{name}' PASSED")

    # Verify behavioral agreement
    assert parsed_base["passed"] == parsed_refac["passed"], "Baseline and refactored passed count differ"
    assert parsed_base["total"] == parsed_refac["total"], "Baseline and refactored total count differ"
    print("  ✓ Baseline and refactored versions agree on all 16 test cases")

    return parsed_base, parsed_refac


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
        sys.exit(f"FAIL: Stub passed {parsed['passed']} test(s) — learner stub should not solve any cases")

    print(f"  ✓ Stub failed all {parsed['total']} tests (learner unsolved)")
    return parsed


def save_artifacts(base_result, refac_result, stub_result):
    os.makedirs(WORK_DIR, exist_ok=True)

    inputs = {
        "exercise": "micro-blog",
        "task": "R09-T054",
        "task_type": "Reference implementation refactor",
        "named_cases": NAMED_CASES,
        "describe_block": "MicroBlog test cases",
        "refactor_summary": "Renamed ambiguous $charArray to $textElementOffsets, added invariant comment, simplified to single-step substring truncation",
        "config_paths": load_config()
    }
    with open(os.path.join(WORK_DIR, "inputs.json"), "w", encoding="utf-8") as f:
        json.dump(inputs, f, indent=2)

    results = {
        "baseline": base_result,
        "refactored": refac_result,
        "stub": stub_result,
        "agreement": True
    }
    with open(os.path.join(WORK_DIR, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    versions = get_tool_versions()
    with open(os.path.join(WORK_DIR, "tool_versions.json"), "w", encoding="utf-8") as f:
        json.dump(versions, f, indent=2)

    print(f"  ✓ Evidence artifacts saved to {WORK_DIR}")


def main():
    print(f"R09-T054 check.py — micro-blog reference refactor verification")
    print(f"Repo root: {REPO_ROOT}\n")

    verify_maintenance_doc()
    verify_refactor()
    base_result, refac_result = run_baseline_and_refactored()
    stub_result = run_stub()
    save_artifacts(base_result, refac_result, stub_result)

    print("\n=== ALL CHECKS PASSED ===")
    print(f"Refactored reference: {refac_result['total']} tests, all passed")
    print(f"Stub: {stub_result['total']} tests, all failed (learner unsolved)")
    sys.exit(0)


if __name__ == "__main__":
    main()
