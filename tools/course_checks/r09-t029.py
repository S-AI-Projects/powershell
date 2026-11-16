#!/usr/bin/env python3
"""
Isolated test runner for rotational-cipher (R09-T029).
Guarantees that learner stub and test files in the repository working tree
are never modified by computing and verifying SHA-256 hashes before and after every execution.
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

def get_learner_hashes(exercise_dir):
    hashes = {}
    for fname in ["RotationalCipher.ps1", "RotationalCipher.tests.ps1"]:
        fpath = os.path.join(exercise_dir, fname)
        if os.path.exists(fpath):
            hashes[fname] = compute_file_hash(fpath)
    return hashes

def run_in_isolation(exercise_dir, example_override=None, empty_tests=False):
    """
    Executes tests in an isolated temporary directory.
    Returns (returncode, total_count, failed_count, passed_count).
    """
    with open(os.path.join(exercise_dir, ".meta", "config.json")) as f:
        config = json.load(f)

    solution_file = config["files"]["solution"][0]
    example_file = config["files"]["example"][0]
    test_file = config["files"]["test"][0]

    with tempfile.TemporaryDirectory() as td:
        for item in os.listdir(exercise_dir):
            s = os.path.join(exercise_dir, item)
            d = os.path.join(td, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)

        # Apply override
        if empty_tests:
            with open(os.path.join(td, test_file), "w") as f:
                f.write("# empty test file\n")
        elif example_override is not None:
            with open(os.path.join(td, solution_file), "w") as f:
                f.write(example_override)
        else:
            shutil.copy2(os.path.join(td, example_file), os.path.join(td, solution_file))

        cmd = [
            "pwsh", "-Command",
            f"$res = Invoke-Pester -Path ./{test_file} -PassThru; "
            f"Write-Host \"PES_TOTAL=$($res.TotalCount)\"; "
            f"Write-Host \"PES_FAILED=$($res.FailedCount)\"; "
            f"Write-Host \"PES_PASSED=$($res.PassedCount)\"; "
            f"if ($res.FailedCount -gt 0 -or $res.TotalCount -eq 0) {{ exit 1 }} else {{ exit 0 }}"
        ]
        proc = subprocess.run(cmd, cwd=td, capture_output=True, text=True)

        total, failed, passed = 0, 0, 0
        for line in proc.stdout.splitlines():
            if line.startswith("PES_TOTAL="):
                total = int(line.split("=")[1])
            elif line.startswith("PES_FAILED="):
                failed = int(line.split("=")[1])
            elif line.startswith("PES_PASSED="):
                passed = int(line.split("=")[1])

        return proc.returncode, total, failed, passed

def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    exercise_dir = os.path.join(repo_root, "exercises", "practice", "rotational-cipher")

    before_hashes = get_learner_hashes(exercise_dir)

    try:
        # Case 1: Real reference (must succeed 100%)
        code, total, failed, passed = run_in_isolation(exercise_dir)
        if code != 0 or failed > 0 or total == 0:
            print(f"FAIL: Reference run failed (exit {code}, total={total}, failed={failed})")
            sys.exit(1)
        print(f"OK: Reference passed all {total} cases.")

        # Case 2: Assertion failure test (must fail)
        failing_code = 'function Rotate($text, $shift) { return "wrong" }'
        f_code, f_total, f_failed, f_passed = run_in_isolation(exercise_dir, example_override=failing_code)
        if f_code == 0 or f_failed == 0:
            print(f"FAIL: Deliberate failure was not caught (exit {f_code})")
            sys.exit(1)
        print("OK: Deliberately failing reference correctly exited non-zero.")

        # Case 3: Zero-test run (must fail)
        z_code, z_total, z_failed, z_passed = run_in_isolation(exercise_dir, empty_tests=True)
        if z_code == 0:
            print("FAIL: Zero-test run did not exit non-zero")
            sys.exit(1)
        print("OK: Zero-test run correctly exited non-zero.")

    finally:
        after_hashes = get_learner_hashes(exercise_dir)
        if before_hashes != after_hashes:
            print("CRITICAL: Learner files were modified!")
            sys.exit(1)
        print("OK: File hash integrity preserved before and after execution.")

    print("SUCCESS: All isolation and integrity checks passed.")

if __name__ == "__main__":
    main()
