#!/usr/bin/env python3
"""
Automated validation script for Task R09-T029 (rotational-cipher).
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

def compute_file_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    exercise_dir = os.path.join(repo_root, "exercises", "practice", "rotational-cipher")
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

    # Step 1: Run isolated runner check tool
    check_tool = os.path.join(repo_root, "tools", "course_checks", "r09-t029.py")
    tool_run = subprocess.run([sys.executable, check_tool], capture_output=True, text=True)
    if tool_run.returncode != 0:
        print(f"FAIL: Course check runner failed:\n{tool_run.stderr}")
        sys.exit(1)
    evidence["runner_tool_output"] = tool_run.stdout.strip()

    # Step 2: Unsolved stub check
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

    # Step 3: Reference run & hash immutability assertion
    stub_path = os.path.join(exercise_dir, solution_file)
    test_path = os.path.join(exercise_dir, test_file)

    before_hashes = {
        solution_file: compute_file_hash(stub_path),
        test_file: compute_file_hash(test_path)
    }

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

    after_hashes = {
        solution_file: compute_file_hash(stub_path),
        test_file: compute_file_hash(test_path)
    }

    evidence["file_hashes"] = {
        "before": before_hashes,
        "after": after_hashes,
        "match": before_hashes == after_hashes
    }

    if before_hashes != after_hashes:
        print("FAIL: Learner files were modified during check run!")
        sys.exit(1)

    evidence_file = os.path.join(work_dir, "results.json")
    with open(evidence_file, "w") as f:
        json.dump(evidence, f, indent=2)

    print("SUCCESS: All assertions passed for R09-T029.")
    print(f"Total tests: {counts.get('total')}, Passed: {counts.get('passed')}, Failed: {counts.get('failed')}")
    print(f"File integrity preserved: {evidence['file_hashes']['match']}")

if __name__ == "__main__":
    main()
