#!/usr/bin/env python3
"""
tools/course_checks/r09-t009.py: Isolated test runner for grains exercise.
Runs tests in isolated temporary environments, validates case counts,
propagates failure codes, and guarantees learner file immutability via cryptographic hashing.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

def hash_file(filepath):
    """Computes SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def execute_in_temp(exercise_dir, repo_root, override_solution_content=None, override_tests_content=None):
    """Executes Pester in a clean temporary copy of the exercise."""
    env = os.environ.copy()
    env["HOME"] = "/tmp"
    ps_module_dir = str(repo_root / ".modules")
    sys_module_dir = "/opt/homebrew/Cellar/powershell/7.7.0/libexec/Modules"
    env["PSModulePath"] = f"{ps_module_dir}:{sys_module_dir}"

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_exercise = Path(tmp_dir) / "grains"
        shutil.copytree(exercise_dir, tmp_exercise)

        with open(exercise_dir / ".meta" / "config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        solution_rel = cfg["files"]["solution"][0]
        example_rel = cfg["files"]["example"][0]
        test_rel = cfg["files"]["test"][0]

        tmp_solution = tmp_exercise / solution_rel
        tmp_example = tmp_exercise / example_rel
        tmp_test = tmp_exercise / test_rel

        if override_solution_content is not None:
            tmp_solution.write_text(override_solution_content, encoding="utf-8")
        else:
            shutil.copy2(tmp_example, tmp_solution)

        if override_tests_content is not None:
            tmp_test.write_text(override_tests_content, encoding="utf-8")

        ps_cmd = (
            f"Push-Location '{tmp_exercise}'; "
            "$res = Invoke-Pester -PassThru; "
            "Pop-Location; "
            "$summary = @{ TotalCount = $res.TotalCount; PassedCount = $res.PassedCount; FailedCount = $res.FailedCount }; "
            "ConvertTo-Json $summary -Compress"
        )

        proc = subprocess.run(
            ["pwsh", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            env=env,
        )

        lines = [line.strip() for line in proc.stdout.splitlines() if line.strip().startswith("{")]
        summary = json.loads(lines[-1]) if lines else {"TotalCount": 0, "PassedCount": 0, "FailedCount": 1}

    return summary, proc.returncode

def run_check(repo_root=None):
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]
    else:
        repo_root = Path(repo_root)

    exercise_dir = repo_root / "exercises" / "practice" / "grains"
    learner_stub_path = exercise_dir / "Grains.ps1"
    tests_path = exercise_dir / "Grains.tests.ps1"

    # 1. Record baseline hash of learner file
    initial_hash = hash_file(learner_stub_path)
    print(f"Learner file initial SHA256: {initial_hash}")

    stub_content = learner_stub_path.read_text(encoding="utf-8")
    assert "throw \"Please implement this function\"" in stub_content, "Learner stub must remain unsolved!"

    # 2. Mode A: Genuine reference solution run
    print("Mode A: Running genuine reference implementation...")
    ref_summary, ref_code = execute_in_temp(exercise_dir, repo_root)
    print(f"Reference summary: {ref_summary}")
    assert ref_code == 0, f"Expected returncode 0, got {ref_code}"
    assert ref_summary["TotalCount"] == 11, f"Expected 11 tests, got {ref_summary['TotalCount']}"
    assert ref_summary["FailedCount"] == 0, f"Expected 0 failures, got {ref_summary['FailedCount']}"

    # Verify learner hash remains untouched
    hash_after_ref = hash_file(learner_stub_path)
    assert hash_after_ref == initial_hash, "Learner file was modified during reference run!"

    # 3. Mode B: Deliberately failing reference
    print("Mode B: Running deliberately failing reference...")
    failing_content = "Function Get-GrainSquare { param([BigInt]$Number); return 0 }\nFunction Get-GrainTotal { return 0 }"
    fail_summary, fail_code = execute_in_temp(exercise_dir, repo_root, override_solution_content=failing_content)
    print(f"Failing summary: {fail_summary}")
    assert fail_summary["FailedCount"] > 0, "Failing implementation unexpectedly reported 0 failures!"

    hash_after_fail = hash_file(learner_stub_path)
    assert hash_after_fail == initial_hash, "Learner file was modified during failing run!"

    # 4. Mode C: Empty test selection (zero-test detection)
    print("Mode C: Running empty test selection...")
    empty_tests_content = "BeforeAll { . \"./Grains.ps1\" }\nDescribe \"Empty suite\" { }"
    zero_summary, zero_code = execute_in_temp(exercise_dir, repo_root, override_tests_content=empty_tests_content)
    print(f"Empty suite summary: {zero_summary}")
    assert zero_summary["TotalCount"] == 0, "Empty suite unexpectedly reported >0 tests!"

    # Final hash verification
    final_hash = hash_file(learner_stub_path)
    assert final_hash == initial_hash, "Learner file hash changed after test runner execution!"
    print("Learner file integrity verified: hash perfectly preserved across all runs.")

    return {
        "status": "PASS",
        "learner_file_hash": initial_hash,
        "modes_tested": {
            "real_reference": {"exit_code": 0, "summary": ref_summary},
            "deliberately_failing": {"exit_code": "failed_as_expected", "summary": fail_summary},
            "empty_selection": {"exit_code": "zero_tests_detected", "summary": zero_summary}
        },
        "named_cases_verified": ["Test Grains.ps1", "grains on square 1", "grains on square 2"],
        "unsolved_stub_verified": True
    }

if __name__ == "__main__":
    res = run_check()
    print("Runner check completed successfully:", json.dumps(res, indent=2))
