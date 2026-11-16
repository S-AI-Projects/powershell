#!/usr/bin/env python3
"""
Automated validation script for Task R09-T030 (clock).
Verifies decision table inputs/outputs and runs the complete Clock test suite.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    exercise_dir = os.path.join(repo_root, "exercises", "practice", "clock")
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
        evidence["learner_stub_unsolved"] = stub_run.returncode != 0 or "PES_PASSED=52" not in stub_run.stdout

    # Step 2: Reference solution check & Decision table validation
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

        # Decision table assertions
        decision_table_script = """
        . ./Clock.ps1
        $table = @(
            @{ Case = "on the hour"; H = 9; M = 0; Expected = "09:00" },
            @{ Case = "past the hour"; H = 10; M = 23; Expected = "10:23" },
            @{ Case = "hour rolls over"; H = 25; M = 0; Expected = "01:00" },
            @{ Case = "negative offset"; H = 0; M = -1; Expected = "23:59" }
        )
        $out = @()
        foreach ($entry in $table) {
            $clock = [Clock]::new($entry.H, $entry.M)
            $actual = $clock.ToString()
            if ($actual -ne $entry.Expected) {
                Write-Error "Decision table failure on $($entry.Case): expected $($entry.Expected), got $actual"
                exit 1
            }
            $out += [PSCustomObject]@{
                Case = $entry.Case
                Hour = $entry.H
                Minute = $entry.M
                Expected = $entry.Expected
                Actual = $actual
                Passed = $true
            }
        }
        $out | ConvertTo-Json
        """
        dt_run = subprocess.run(["pwsh", "-Command", decision_table_script], cwd=td, capture_output=True, text=True)
        if dt_run.returncode != 0:
            print(f"FAIL: Decision table verification failed:\n{dt_run.stderr}")
            sys.exit(1)

        evidence["decision_table"] = json.loads(dt_run.stdout)

    evidence_file = os.path.join(work_dir, "results.json")
    with open(evidence_file, "w") as f:
        json.dump(evidence, f, indent=2)

    print("SUCCESS: All assertions passed for R09-T030.")
    print(f"Total tests: {counts.get('total')}, Passed: {counts.get('passed')}, Failed: {counts.get('failed')}")
    print(f"Decision table cases verified: {len(evidence['decision_table'])}")

if __name__ == "__main__":
    main()
