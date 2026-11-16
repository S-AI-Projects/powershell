#!/usr/bin/env python3
"""
Automated validation script for Task R09-T027 (saddle-points).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    exercise_dir = os.path.join(repo_root, "exercises", "practice", "saddle-points")
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
        evidence["learner_stub_unsolved"] = stub_run.returncode != 0 or "PES_PASSED=10" not in stub_run.stdout

    # Step 2: Reference solution check
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
        counts = {}
        for line in ref_run.stdout.splitlines():
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

        if ref_run.returncode != 0 or counts.get("failed", 0) > 0 or counts.get("total", 0) == 0:
            print(f"FAIL: Reference run failed: {counts}")
            sys.exit(1)

    # Step 3: Micro-examples assertions
    micro_script = """
    Class SaddlePoint {
        [int]$Row
        [int]$Column
        SaddlePoint($r, $c) { $this.Row = $r; $this.Column = $c }
    }
    function Get-SinglePoint {
        $points = @([SaddlePoint]::new(1, 2))
        $points
    }
    function Get-NoPoints {
        $points = @()
        $points
    }
    
    # Check 1: Scalar unrolling
    $res1 = Get-SinglePoint
    $type1 = $res1.GetType().Name
    
    # Check 2: Array subexpression preservation
    $res2 = @(Get-SinglePoint)
    $type2 = $res2.GetType().Name
    $count2 = $res2.Count
    
    # Check 3: Empty array handling
    $res3 = @(Get-NoPoints)
    $count3 = $res3.Count
    
    [PSCustomObject]@{
        Micro1Type = $type1
        Micro2Type = $type2
        Micro2Count = $count2
        Micro3Count = $count3
    } | ConvertTo-Json
    """
    micro_run = subprocess.run(["pwsh", "-Command", micro_script], capture_output=True, text=True)
    if micro_run.returncode != 0:
        print(f"FAIL: Micro-example script failed:\n{micro_run.stderr}")
        sys.exit(1)

    micro_results = json.loads(micro_run.stdout)
    evidence["micro_examples"] = micro_results

    if micro_results["Micro1Type"] != "SaddlePoint":
        print(f"FAIL: Expected Micro1Type == SaddlePoint, got {micro_results['Micro1Type']}")
        sys.exit(1)
    if micro_results["Micro2Type"] != "Object[]" or micro_results["Micro2Count"] != 1:
        print(f"FAIL: Expected Micro2Type == Object[] and Count == 1, got {micro_results}")
        sys.exit(1)
    if micro_results["Micro3Count"] != 0:
        print(f"FAIL: Expected Micro3Count == 0, got {micro_results['Micro3Count']}")
        sys.exit(1)

    evidence_file = os.path.join(work_dir, "results.json")
    with open(evidence_file, "w") as f:
        json.dump(evidence, f, indent=2)

    print("SUCCESS: All assertions passed for R09-T027.")
    print(f"Total tests: {counts.get('total')}, Passed: {counts.get('passed')}, Failed: {counts.get('failed')}")
    print(f"Micro-examples verified: {micro_results}")

if __name__ == "__main__":
    main()
