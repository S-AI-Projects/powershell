#!/usr/bin/env python3
"""
tools/course_checks/r09-t008.py: Path and configuration validator for largest-series-product.
Validates that config.json declares valid paths, rejects directory traversal,
ensures all declared files exist, and validates failure behavior on 3 invalid test fixtures.
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

def validate_config(exercise_dir, config_data):
    """Validates the files section of config.json."""
    files_section = config_data.get("files", {})
    required_keys = ["solution", "test", "example"]
    for key in required_keys:
        if key not in files_section or not files_section[key]:
            raise ValueError(f"Missing or empty required file key: '{key}'")

    all_declared = []
    for category, file_list in files_section.items():
        if not isinstance(file_list, list):
            raise ValueError(f"File category '{category}' must be a list")
        for rel_path in file_list:
            # Traversal check: forbid any '..' components
            parts = Path(rel_path).parts
            if ".." in parts or rel_path.startswith("/"):
                raise ValueError(f"Directory traversal detected in '{category}': {rel_path}")

            resolved = (exercise_dir / rel_path).resolve()
            try:
                resolved.relative_to(exercise_dir.resolve())
            except ValueError:
                raise ValueError(f"File path escapes exercise root: {rel_path}")

            if not resolved.is_file():
                raise FileNotFoundError(f"Declared {category} file does not exist: {rel_path}")

            all_declared.append((category, rel_path, resolved))

    return all_declared

def run_pester_check(exercise_dir, repo_root):
    env = os.environ.copy()
    env["HOME"] = "/tmp"
    ps_module_dir = str(repo_root / ".modules")
    sys_module_dir = "/opt/homebrew/Cellar/powershell/7.7.0/libexec/Modules"
    env["PSModulePath"] = f"{ps_module_dir}:{sys_module_dir}"

    with tempfile.TemporaryDirectory() as tmp:
        copy_dir = Path(tmp) / "largest-series-product"
        shutil.copytree(exercise_dir, copy_dir)

        # Substitute reference into solution path
        with open(exercise_dir / ".meta" / "config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        shutil.copy2(copy_dir / cfg["files"]["example"][0], copy_dir / cfg["files"]["solution"][0])

        ps_cmd = (
            f"Push-Location '{copy_dir}'; "
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
            sys.exit(f"Pester execution failed:\n{proc.stdout}\n{proc.stderr}")

        lines = [line.strip() for line in proc.stdout.splitlines() if line.strip().startswith("{")]
        summary = json.loads(lines[-1])

    return summary

def run_check(repo_root=None):
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]
    else:
        repo_root = Path(repo_root)

    exercise_dir = repo_root / "exercises" / "practice" / "largest-series-product"
    config_path = exercise_dir / ".meta" / "config.json"
    solution_path = exercise_dir / "LargestSeriesProduct.ps1"

    # Verify learner stub is unsolved
    stub_content = solution_path.read_text(encoding="utf-8")
    assert "Throw \"Please implement this function.\"" in stub_content, "Learner stub must remain unsolved!"

    with open(config_path, "r", encoding="utf-8") as f:
        real_config = json.load(f)

    # 1. Validate real configuration passes
    print("Validating real largest-series-product config.json...")
    declared = validate_config(exercise_dir, real_config)
    print(f"Real config valid! Declared files: {[f[1] for f in declared]}")

    # 2. Test 3 deliberate invalid fixtures
    print("Testing deliberate invalid metadata fixtures...")
    fixtures_passed = []

    # Fixture A: Missing reference
    cfg_missing_ref = copy.deepcopy(real_config)
    cfg_missing_ref["files"]["example"] = [".meta/NonExistent.example.ps1"]
    try:
        validate_config(exercise_dir, cfg_missing_ref)
        sys.exit("ERROR: Missing reference fixture failed to raise FileNotFoundError")
    except FileNotFoundError as e:
        print(f"Fixture A (missing reference) caught: {e}")
        fixtures_passed.append("missing_reference_rejected")

    # Fixture B: Missing test
    cfg_missing_test = copy.deepcopy(real_config)
    cfg_missing_test["files"]["test"] = ["NonExistent.tests.ps1"]
    try:
        validate_config(exercise_dir, cfg_missing_test)
        sys.exit("ERROR: Missing test fixture failed to raise FileNotFoundError")
    except FileNotFoundError as e:
        print(f"Fixture B (missing test) caught: {e}")
        fixtures_passed.append("missing_test_rejected")

    # Fixture C: Path traversal escaping exercise directory
    cfg_traversal = copy.deepcopy(real_config)
    cfg_traversal["files"]["solution"] = ["../outside_solution.ps1"]
    try:
        validate_config(exercise_dir, cfg_traversal)
        sys.exit("ERROR: Path traversal fixture failed to raise ValueError")
    except ValueError as e:
        print(f"Fixture C (path traversal) caught: {e}")
        fixtures_passed.append("traversal_rejected")

    assert len(fixtures_passed) == 3, "Not all 3 invalid fixtures were rejected properly!"

    # 3. Run isolated Pester check
    print("Running Pester in isolated copy...")
    summary = run_pester_check(exercise_dir, repo_root)
    print(f"Pester results: Total={summary['TotalCount']}, Passed={summary['PassedCount']}, Failed={summary['FailedCount']}")
    assert summary["TotalCount"] > 0, "No tests executed!"
    assert summary["FailedCount"] == 0, f"{summary['FailedCount']} tests failed!"

    return {
        "status": "PASS",
        "real_config_declared_files": [f[1] for f in declared],
        "fixtures_tested": fixtures_passed,
        "test_summary": summary,
        "unsolved_stub_verified": True
    }

if __name__ == "__main__":
    res = run_check()
    print("Check result:", json.dumps(res, indent=2))
