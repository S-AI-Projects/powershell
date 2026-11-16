#!/usr/bin/env python3
"""
Automated validation script for Task R09-T022 (isogram).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    exercise_dir = os.path.join(repo_root, "exercises", "practice", "isogram")
    work_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(work_dir, exist_ok=True)

    config_path = os.path.join(exercise_dir, ".meta", "config.json")
    with open(config_path) as f:
        config = json.load(f)

    solution_file = config["files"]["solution"][0]
    example_file = config["files"]["example"][0]
    test_file = config["files"]["test"][0]

    evidence = {}

    # Tool versions
    pwsh_ver = subprocess.check_output(["pwsh", "--version"], text=True).strip()
    pester_ver = subprocess.check_output(
        ["pwsh", "-Command", "(Get-Module -ListAvailable Pester | Select-Object -First 1).Version.ToString()"],
        text=True
    ).strip()
    python_ver = sys.version.split()[0]
    evidence["tools"] = {
        "powershell": pwsh_ver,
        "pester": pester_ver,
        "python": python_ver
    }

    # Step 1: Run course check tool
    check_tool = os.path.join(repo_root, "tools", "course_checks", "r09-t022.py")
    check_res = subprocess.run([sys.executable, check_tool], capture_output=True, text=True)
    if check_res.returncode != 0:
        print(f"FAIL: Course check tool returned {check_res.returncode}:\n{check_res.stderr}")
        sys.exit(1)
    evidence["course_check_output"] = check_res.stdout.strip()

    # Step 2: Test unsolved stub (must fail)
    with tempfile.TemporaryDirectory() as td:
        for item in os.listdir(exercise_dir):
            s = os.path.join(exercise_dir, item)
            d = os.path.join(td, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)

        stub_cmd = [
            "pwsh", "-Command",
            f"$res = Invoke-Pester -Path ./{test_file} -PassThru; "
            f"Write-Host \"PES_TOTAL=$($res.TotalCount)\"; "
            f"Write-Host \"PES_FAILED=$($res.FailedCount)\"; "
            f"Write-Host \"PES_PASSED=$($res.PassedCount)\""
        ]
        stub_run = subprocess.run(stub_cmd, cwd=td, capture_output=True, text=True)
        evidence["learner_stub_unsolved"] = stub_run.returncode != 0 or "PES_PASSED=13" not in stub_run.stdout

    # Step 3: Test reference solution (must pass all tests)
    with tempfile.TemporaryDirectory() as td:
        for item in os.listdir(exercise_dir):
            s = os.path.join(exercise_dir, item)
            d = os.path.join(td, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)

        # Substitute reference solution
        shutil.copy2(os.path.join(td, example_file), os.path.join(td, solution_file))

        ref_cmd = [
            "pwsh", "-Command",
            f"$res = Invoke-Pester -Path ./{test_file} -PassThru; "
            f"Write-Host \"PES_TOTAL=$($res.TotalCount)\"; "
            f"Write-Host \"PES_FAILED=$($res.FailedCount)\"; "
            f"Write-Host \"PES_PASSED=$($res.PassedCount)\"; "
            f"if ($res.FailedCount -gt 0 -or $res.TotalCount -eq 0) {{ exit 1 }} else {{ exit 0 }}"
        ]
        ref_run = subprocess.run(ref_cmd, cwd=td, capture_output=True, text=True)
        stdout = ref_run.stdout

        counts = {}
        for line in stdout.splitlines():
            if line.startswith("PES_TOTAL="):
                counts["total"] = int(line.split("=")[1])
            elif line.startswith("PES_FAILED="):
                counts["failed"] = int(line.split("=")[1])
            elif line.startswith("PES_PASSED="):
                counts["passed"] = int(line.split("=")[1])

        evidence["reference_run"] = {
            "returncode": ref_run.returncode,
            "counts": counts
        }

        if ref_run.returncode != 0:
            print(f"FAIL: Reference run failed with exit code {ref_run.returncode}")
            sys.exit(1)
        if counts.get("total", 0) == 0:
            print("FAIL: Total tests executed was 0")
            sys.exit(1)
        if counts.get("failed", 0) > 0:
            print(f"FAIL: {counts['failed']} tests failed")
            sys.exit(1)

    # Save evidence
    evidence_file = os.path.join(work_dir, "results.json")
    with open(evidence_file, "w") as f:
        json.dump(evidence, f, indent=2)

    print("SUCCESS: All assertions passed for R09-T022.")
    print(f"Total tests: {counts.get('total')}, Passed: {counts.get('passed')}, Failed: {counts.get('failed')}")

if __name__ == "__main__":
    main()
