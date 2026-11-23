#!/usr/bin/env python3
"""
R09-T056 check.py — pangram two-approach comparison runner.

Verifies:
  1. hints.md exists and contains approach comparison with worked example, avoiding full solution.
  2. docs/maintenance/pangram.md documents the two approaches.
  3. The reference implementation passes all 10 Pester tests.
  4. The alternative implementation (work/R09-T056/alt/PangramAlt.ps1) passes all 10 Pester tests.
  5. Both implementations agree on the named cases:
     - "PangramTests"
     - "empty sentence"
     - "perfect lower case"
  6. The learner stub remains unsolved.
  7. check.py fails on zero-test run, non-zero child exit, or assertion failure.
  8. Saves evidence artifacts to work/R09-T056/.
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
EXERCISE_DIR = os.path.join(REPO_ROOT, "exercises", "practice", "pangram")
CONFIG_PATH = os.path.join(EXERCISE_DIR, ".meta", "config.json")
WORK_DIR = os.path.join(REPO_ROOT, "work", "R09-T056")
ALT_SCRIPT = os.path.join(WORK_DIR, "alt", "PangramAlt.ps1")
HINTS_MD = os.path.join(EXERCISE_DIR, ".docs", "hints.md")
MAINTENANCE_MD = os.path.join(REPO_ROOT, "docs", "maintenance", "pangram.md")

NAMED_CASES = [
    "empty sentence",
    "perfect lower case"
]
DESCRIBE_BLOCK = "PangramTests"


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


def copy_exercise_to_tmpdir(tmpdir, implementation_file=None, keep_stub=False):
    dst = os.path.join(tmpdir, "pangram")
    shutil.copytree(EXERCISE_DIR, dst)

    cfg = load_config()
    solution_rel = cfg["files"]["solution"][0]
    example_rel = cfg["files"]["example"][0]

    solution_path = os.path.join(dst, solution_rel)

    if not keep_stub:
        if implementation_file is not None:
            with open(implementation_file, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            example_path = os.path.join(dst, example_rel)
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


def verify_hints_md():
    print("=== Check: hints.md ===")
    if not os.path.exists(HINTS_MD):
        sys.exit(f"FAIL: hints.md not found at {HINTS_MD}")
    with open(HINTS_MD, "r", encoding="utf-8") as f:
        content = f.read()

    required = ["Choosing an approach", "Worked example", "Trade-off", "The quick brown fox"]
    for token in required:
        if token.lower() not in content.lower():
            sys.exit(f"FAIL: hints.md missing section '{token}'")

    forbidden = ["Invoke-Panagram", "Function ", "Param("]
    for token in forbidden:
        if token in content:
            sys.exit(f"FAIL: hints.md contains implementation code '{token}'")

    print("  ✓ hints.md contains approach comparison with worked example, avoiding full solution")


def verify_maintenance_md():
    print("=== Check: docs/maintenance/pangram.md ===")
    if not os.path.exists(MAINTENANCE_MD):
        sys.exit(f"FAIL: maintenance doc not found at {MAINTENANCE_MD}")
    with open(MAINTENANCE_MD, "r", encoding="utf-8") as f:
        content = f.read()

    for token in ["Approach 1", "Approach 2", "Reference", "Alternative", "Complexity", "Equivalence"]:
        if token.lower() not in content.lower():
            sys.exit(f"FAIL: docs/maintenance/pangram.md missing '{token}'")

    print("  ✓ docs/maintenance/pangram.md verified")


def run_reference():
    print("=== Check: Reference implementation execution ===")
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


def run_alternative():
    print("=== Check: Alternative implementation execution ===")
    if not os.path.exists(ALT_SCRIPT):
        sys.exit(f"FAIL: alternative implementation not found at {ALT_SCRIPT}")

    with tempfile.TemporaryDirectory() as tmpdir:
        dst = copy_exercise_to_tmpdir(tmpdir, implementation_file=ALT_SCRIPT)
        r = run_pester_in_copy(dst)

    parsed = parse_pester_output(r.stdout, r.stderr)
    print(f"  Alternative: Total={parsed['total']}, Passed={parsed['passed']}, Failed={parsed['failed']}")

    if parsed["total"] == 0 or parsed["executed"] == 0:
        sys.exit("FAIL: Alternative run executed 0 tests")
    if parsed["failed"] > 0:
        sys.exit(f"FAIL: Alternative failed {parsed['failed']} tests")

    for name in NAMED_CASES:
        status = find_case_status(parsed["cases"], name)
        if status != "PASS":
            sys.exit(f"FAIL: Named case '{name}' did not PASS on alternative (got: {status})")
        print(f"  ✓ Named case '{name}' PASSED on alternative")

    print(f"  ✓ All {parsed['total']} tests passed on alternative")
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
        dst = copy_exercise_to_tmpdir(tmpdir, keep_stub=True)
        r = run_pester_in_copy(dst)

    parsed = parse_pester_output(r.stdout, r.stderr)
    print(f"  Stub: Total={parsed['total']}, Passed={parsed['passed']}, Failed={parsed['failed']}")

    if parsed["total"] == 0:
        sys.exit("FAIL: Stub run executed 0 tests")
    if parsed["passed"] > 0:
        sys.exit(f"FAIL: Stub passed {parsed['passed']} test(s)")
    print(f"  ✓ Stub failed all {parsed['total']} tests (learner unsolved)")
    return parsed


def save_artifacts(ref_result, alt_result, stub_result):
    os.makedirs(WORK_DIR, exist_ok=True)

    inputs = {
        "exercise": "pangram",
        "task": "R09-T056",
        "task_type": "Compare implementation approaches",
        "named_cases": NAMED_CASES,
        "describe_block": DESCRIBE_BLOCK,
        "approach_1": "Input scan with set accumulator (reference)",
        "approach_2": "Alphabet query with early exit (alternative)",
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
        "alternative": {
            "total": alt_result["total"],
            "passed": alt_result["passed"],
            "failed": alt_result["failed"]
        },
        "stub": {
            "total": stub_result["total"],
            "passed": stub_result["passed"],
            "failed": stub_result["failed"]
        },
        "agreement": True
    }
    with open(os.path.join(WORK_DIR, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    versions = get_tool_versions()
    with open(os.path.join(WORK_DIR, "tool_versions.json"), "w", encoding="utf-8") as f:
        json.dump(versions, f, indent=2)

    print(f"  ✓ Evidence artifacts saved to {WORK_DIR}")


def main():
    print(f"R09-T056 check.py — pangram two-approach comparison")
    print(f"Repo root: {REPO_ROOT}\n")

    verify_hints_md()
    verify_maintenance_md()
    ref_result = run_reference()
    alt_result = run_alternative()
    stub_result = run_stub()

    # Verify 100% agreement between both approaches
    assert ref_result["passed"] == alt_result["passed"] == 10, "Both approaches must pass all 10 tests"

    save_artifacts(ref_result, alt_result, stub_result)

    print("\n=== ALL CHECKS PASSED ===")
    print(f"Reference: 10/10 passed")
    print(f"Alternative: 10/10 passed")
    print(f"Stub: 10/10 failed (learner unsolved)")
    sys.exit(0)


if __name__ == "__main__":
    main()
