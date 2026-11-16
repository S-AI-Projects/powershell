#!/usr/bin/env python3
"""
Automated validation script for Task R09-T026 (bowling).
Tests both the reference (Frame-centric linked structure) and the alternative
(Flat roll list indexing) against the full test suite.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    exercise_dir = os.path.join(repo_root, "exercises", "practice", "bowling")
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

    # Step 1: Unsolved stub check
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
        evidence["learner_stub_unsolved"] = stub_run.returncode != 0 or "PES_PASSED=31" not in stub_run.stdout

    # Step 2: Reference solution check (Approach 1: Linked Frame)
    with tempfile.TemporaryDirectory() as td:
        for item in os.listdir(exercise_dir):
            s = os.path.join(exercise_dir, item)
            d = os.path.join(td, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)

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
        ref_counts = {}
        for line in ref_run.stdout.splitlines():
            if line.startswith("PES_TOTAL="):
                ref_counts["total"] = int(line.split("=")[1])
            elif line.startswith("PES_FAILED="):
                ref_counts["failed"] = int(line.split("=")[1])
            elif line.startswith("PES_PASSED="):
                ref_counts["passed"] = int(line.split("=")[1])

        evidence["approach_1_linked_frames"] = {
            "returncode": ref_run.returncode,
            "counts": ref_counts
        }

        if ref_run.returncode != 0 or ref_counts.get("failed", 0) > 0 or ref_counts.get("total", 0) == 0:
            print(f"FAIL: Approach 1 (linked frames) failed: {ref_counts}")
            sys.exit(1)

    # Step 3: Alternative implementation check (Approach 2: Flat Roll List)
    alt_file = os.path.join(work_dir, "BowlingFlatList.ps1")
    with tempfile.TemporaryDirectory() as td:
        for item in os.listdir(exercise_dir):
            s = os.path.join(exercise_dir, item)
            d = os.path.join(td, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)

        shutil.copy2(alt_file, os.path.join(td, solution_file))

        alt_cmd = [
            "pwsh", "-Command",
            f"$res = Invoke-Pester -Path ./{test_file} -PassThru; "
            f"Write-Host \"PES_TOTAL=$($res.TotalCount)\"; "
            f"Write-Host \"PES_FAILED=$($res.FailedCount)\"; "
            f"Write-Host \"PES_PASSED=$($res.PassedCount)\"; "
            f"if ($res.FailedCount -gt 0 -or $res.TotalCount -eq 0) {{ exit 1 }} else {{ exit 0 }}"
        ]
        alt_run = subprocess.run(alt_cmd, cwd=td, capture_output=True, text=True)
        alt_counts = {}
        for line in alt_run.stdout.splitlines():
            if line.startswith("PES_TOTAL="):
                alt_counts["total"] = int(line.split("=")[1])
            elif line.startswith("PES_FAILED="):
                alt_counts["failed"] = int(line.split("=")[1])
            elif line.startswith("PES_PASSED="):
                alt_counts["passed"] = int(line.split("=")[1])

        evidence["approach_2_flat_list"] = {
            "returncode": alt_run.returncode,
            "counts": alt_counts
        }

        if alt_run.returncode != 0 or alt_counts.get("failed", 0) > 0 or alt_counts.get("total", 0) == 0:
            print(f"FAIL: Approach 2 (flat list) failed: {alt_counts}\n{alt_run.stdout}")
            sys.exit(1)

    evidence_file = os.path.join(work_dir, "results.json")
    with open(evidence_file, "w") as f:
        json.dump(evidence, f, indent=2)

    print("SUCCESS: Both approaches passed 100% of the Bowling test suite.")
    print(f"Approach 1 Passed: {ref_counts.get('passed')}/{ref_counts.get('total')}")
    print(f"Approach 2 Passed: {alt_counts.get('passed')}/{alt_counts.get('total')}")

if __name__ == "__main__":
    main()
