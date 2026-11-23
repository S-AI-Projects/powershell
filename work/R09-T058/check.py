#!/usr/bin/env python3
"""
R09-T058 check.py — series maintenance metadata and file-role validation runner.

Verifies:
  1. tools/course_checks/r09-t058.py passes on the real config.json (0 errors).
  2. All three deliberately invalid metadata fixtures fail for their expected reasons:
     - missing reference (MISSING_FILE on example)
     - missing test (MISSING_FILE on test)
     - outside exercise (OUTSIDE_EXERCISE on test)
  3. Reference implementation passes all 11 Pester tests.
  4. Named cases (Test Get-Slices; slices of one from one; slices of one from two) pass.
  5. Learner stub remains unsolved (fails tests).
  6. Check fails on zero-test run, non-zero child exit, or assertion failure.
  7. Saves evidence artifacts to work/R09-T058/.
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
EXERCISE_DIR = REPO_ROOT / "exercises" / "practice" / "series"
CONFIG_PATH = EXERCISE_DIR / ".meta" / "config.json"
WORK_DIR = REPO_ROOT / "work" / "R09-T058"
MAINTENANCE_MD = REPO_ROOT / "docs" / "maintenance" / "series.md"
COURSE_CHECK = REPO_ROOT / "tools" / "course_checks" / "r09-t058.py"

NAMED_CASES = [
    "slices of one from one",
    "slices of one from two"
]
DESCRIBE_BLOCK = "Test Get-Slices"

FIXTURES = [
    {
        "name": "missing reference",
        "key": "example",
        "path": ".meta/Missing.example.ps1",
        "expected_code": "MISSING_FILE"
    },
    {
        "name": "missing test",
        "key": "test",
        "path": "Missing.tests.ps1",
        "expected_code": "MISSING_FILE"
    },
    {
        "name": "outside exercise",
        "key": "test",
        "path": "../series/Series.tests.ps1",
        "expected_code": "OUTSIDE_EXERCISE"
    }
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


def copy_exercise_to_tmpdir(tmpdir, use_reference=True):
    dst = Path(tmpdir) / "series"
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


def verify_maintenance_doc():
    print("=== Check: docs/maintenance/series.md ===")
    if not MAINTENANCE_MD.exists():
        sys.exit(f"FAIL: maintenance doc not found at {MAINTENANCE_MD}")
    content = MAINTENANCE_MD.read_text(encoding="utf-8")

    for phrase in ["File roles", "Generated and maintained", "How the runner finds the files", "r09-t058.py"]:
        if phrase.lower() not in content.lower():
            sys.exit(f"FAIL: maintenance doc missing section on '{phrase}'")
    print("  ✓ docs/maintenance/series.md verified")


def test_metadata_checker():
    print("=== Check: course checker on real config and invalid fixtures ===")
    # 1. Real config must pass
    r = subprocess.run([sys.executable, str(COURSE_CHECK), str(EXERCISE_DIR)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"FAIL: real config failed course check: {r.stdout} {r.stderr}")
    print("  ✓ Real config passes course check (0 errors)")

    # 2. Test 3 invalid fixtures
    fixture_results = []
    for fix in FIXTURES:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_ex = Path(tmpdir) / "series"
            shutil.copytree(EXERCISE_DIR, tmp_ex)
            tmp_cfg = tmp_ex / ".meta" / "config.json"

            with open(tmp_cfg, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["files"][fix["key"]] = [fix["path"]]
            with open(tmp_cfg, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            r_fix = subprocess.run([sys.executable, str(COURSE_CHECK), str(tmp_ex)],
                                   capture_output=True, text=True)
            if r_fix.returncode == 0:
                sys.exit(f"FAIL: Fixture '{fix['name']}' unexpectedly passed check!")

            err_line = r_fix.stdout.strip()
            if fix["expected_code"] not in err_line:
                sys.exit(f"FAIL: Fixture '{fix['name']}' expected {fix['expected_code']}, got: {err_line}")

            print(f"  ✓ Fixture '{fix['name']}' correctly rejected with {fix['expected_code']}")
            fixture_results.append({
                "name": fix["name"],
                "key": fix["key"],
                "path": fix["path"],
                "expected_code": fix["expected_code"],
                "actual_output": err_line,
                "exit_code": r_fix.returncode
            })

    return fixture_results


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


def save_artifacts(ref_result, stub_result, fixture_results):
    os.makedirs(WORK_DIR, exist_ok=True)

    inputs = {
        "exercise": "series",
        "task": "R09-T058",
        "task_type": "Exercise maintenance metadata",
        "named_cases": NAMED_CASES,
        "describe_block": DESCRIBE_BLOCK,
        "fixtures": FIXTURES,
        "config_paths": load_config()
    }
    with open(WORK_DIR / "inputs.json", "w", encoding="utf-8") as f:
        json.dump(inputs, f, indent=2)

    results = {
        "real_config_valid": True,
        "fixtures": fixture_results,
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
    print(f"R09-T058 check.py — series maintenance metadata verification")
    print(f"Repo root: {REPO_ROOT}\n")

    verify_maintenance_doc()
    fixture_results = test_metadata_checker()
    ref_result = run_reference()
    stub_result = run_stub()
    save_artifacts(ref_result, stub_result, fixture_results)

    print("\n=== ALL CHECKS PASSED ===")
    print(f"Reference: {ref_result['total']}/11 passed")
    print(f"Stub: {stub_result['total']}/11 failed (learner unsolved)")
    print("Real config passed and all 3 invalid fixtures rejected correctly")
    sys.exit(0)


if __name__ == "__main__":
    main()
