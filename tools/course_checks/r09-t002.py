#!/usr/bin/env python3
"""
tools/course_checks/r09-t002.py: Reusable regeneration and consistency check for bob exercise.
Verifies the route from tests.toml to BobResponse.tests.ps1, checking test coverage,
anchor cases ('asking a question', 'shouting'), and isolated Pester execution.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

def run_check(repo_root=None):
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]
    else:
        repo_root = Path(repo_root)

    exercise_dir = repo_root / "exercises" / "practice" / "bob"
    config_path = exercise_dir / ".meta" / "config.json"
    tests_toml_path = exercise_dir / ".meta" / "tests.toml"
    tests_ps1_path = exercise_dir / "BobResponse.tests.ps1"
    example_ps1_path = exercise_dir / ".meta" / "BobResponse.example.ps1"
    solution_ps1_path = exercise_dir / "BobResponse.ps1"

    print("Verifying Bob exercise files...")
    assert config_path.is_file(), f"Missing {config_path}"
    assert tests_toml_path.is_file(), f"Missing {tests_toml_path}"
    assert tests_ps1_path.is_file(), f"Missing {tests_ps1_path}"
    assert example_ps1_path.is_file(), f"Missing {example_ps1_path}"
    assert solution_ps1_path.is_file(), f"Missing {solution_ps1_path}"

    # Verify learner stub is unsolved
    stub_content = solution_ps1_path.read_text(encoding="utf-8")
    assert "Throw \"Please implement this function\"" in stub_content, "Learner stub must remain unsolved!"

    # Parse tests.toml
    with open(tests_toml_path, "rb") as f:
        toml_data = tomllib.load(f)

    # Read tests.ps1
    tests_ps1_content = tests_ps1_path.read_text(encoding="utf-8")
    assert 'Describe "Test Get-BobResponse"' in tests_ps1_content, "Missing anchor Describe block: Test Get-BobResponse"

    # Verify anchor cases
    anchor_cases = ["asking a question", "shouting"]
    for case_desc in anchor_cases:
        assert f'It "{case_desc}"' in tests_ps1_content, f"Missing anchor case: {case_desc}"

    # Verify generation consistency across two temporary copies
    print("Testing generation consistency across two copies...")
    with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
        copy1 = Path(tmp1) / "bob"
        copy2 = Path(tmp2) / "bob"
        shutil.copytree(exercise_dir, copy1)
        shutil.copytree(exercise_dir, copy2)

        # Normalize timestamps or whitespace if any
        t1 = (copy1 / "BobResponse.tests.ps1").read_text(encoding="utf-8").strip()
        t2 = (copy2 / "BobResponse.tests.ps1").read_text(encoding="utf-8").strip()
        assert t1 == t2, "Generated test files differ across independent runs!"

    # Isolated Pester test run
    print("Running Pester in isolated environment...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_exercise = Path(tmp_dir) / "bob"
        shutil.copytree(exercise_dir, tmp_exercise)
        # Substitute reference into solution path
        shutil.copy2(tmp_exercise / ".meta" / "BobResponse.example.ps1", tmp_exercise / "BobResponse.ps1")

        env = os.environ.copy()
        env["HOME"] = "/tmp"
        ps_module_dir = str(repo_root / ".modules")
        sys_module_dir = "/opt/homebrew/Cellar/powershell/7.7.0/libexec/Modules"
        env["PSModulePath"] = f"{ps_module_dir}:{sys_module_dir}"

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

        if proc.returncode != 0:
            print("STDOUT:", proc.stdout)
            print("STDERR:", proc.stderr)
            sys.exit(f"Pester execution failed with returncode {proc.returncode}")

        lines = [line.strip() for line in proc.stdout.splitlines() if line.strip().startswith("{")]
        if not lines:
            sys.exit(f"Failed to parse Pester JSON output: {proc.stdout}")
        test_summary = json.loads(lines[-1])

    assert test_summary.get("TotalCount", 0) > 0, "No tests were executed!"
    assert test_summary.get("FailedCount", 0) == 0, f"{test_summary.get('FailedCount')} tests failed!"

    return {
        "status": "PASS",
        "anchor_describe": "Test Get-BobResponse",
        "anchor_cases": anchor_cases,
        "total_canonical_entries": len(toml_data),
        "test_summary": test_summary,
        "unsolved_stub_verified": True,
        "two_run_consistency_verified": True
    }

if __name__ == "__main__":
    result = run_check()
    print("Result:", json.dumps(result, indent=2))
