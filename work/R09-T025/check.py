#!/usr/bin/env python3
"""
Automated validation script for Task R09-T025 (wordy).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    exercise_dir = os.path.join(repo_root, "exercises", "practice", "wordy")
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
        evidence["learner_stub_unsolved"] = stub_run.returncode != 0 or "PES_PASSED=26" not in stub_run.stdout

    # Step 2: Reference solution test run
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

        # Step 3: Scaling benchmark with 3 input sizes, 5 repetitions
        benchmark_script = """
        . ./Wordy.ps1
        $tests = @(
            @{ Name = "Small (T=1)"; Question = "What is 5?"; Expected = 5 },
            @{ Name = "Medium (T=5)"; Question = "What is 1 plus 2 plus 3?"; Expected = 6 },
            @{ Name = "Large (T=9)"; Question = "What is 2 plus 3 multiplied by 4 minus 2 divided by 2?"; Expected = 9 }
        )
        $out = @()
        foreach ($t in $tests) {
            # Correctness assertion first
            $ans = Get-Answer -Question $t.Question
            if ($ans -ne $t.Expected) {
                Write-Error "Assertion failure: $($t.Question) gave $ans != $($t.Expected)"
                exit 1
            }
            # 5 repetitions
            $times = @()
            for ($i = 0; $i -lt 5; $i++) {
                $sw = [System.Diagnostics.Stopwatch]::StartNew()
                $null = Get-Answer -Question $t.Question
                $sw.Stop()
                $times += $sw.Elapsed.TotalMilliseconds
            }
            $sorted = $times | Sort-Object
            $median = $sorted[2]
            $out += [PSCustomObject]@{
                Name = $t.Name
                Operations = if ($t.Name -match 'T=1') { 0 } elseif ($t.Name -match 'T=5') { 2 } else { 4 }
                MedianMs = $median
                Correct = $true
            }
        }
        $out | ConvertTo-Json
        """
        bench_run = subprocess.run(["pwsh", "-Command", benchmark_script], cwd=td, capture_output=True, text=True)
        if bench_run.returncode != 0:
            print(f"FAIL: Benchmark failed:\n{bench_run.stderr}")
            sys.exit(1)

        evidence["benchmarks"] = json.loads(bench_run.stdout)

    evidence_file = os.path.join(work_dir, "results.json")
    with open(evidence_file, "w") as f:
        json.dump(evidence, f, indent=2)

    print("SUCCESS: All assertions passed for R09-T025.")
    print(f"Total tests: {counts.get('total')}, Passed: {counts.get('passed')}, Failed: {counts.get('failed')}")
    print(f"Benchmarks: {json.dumps(evidence['benchmarks'], indent=2)}")

if __name__ == "__main__":
    main()
