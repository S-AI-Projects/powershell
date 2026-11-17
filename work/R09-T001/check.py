#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXERCISE_DIR = REPO_ROOT / "exercises" / "practice" / "ledger"
CONFIG_PATH = EXERCISE_DIR / ".meta" / "config.json"
TESTS_TOML_PATH = EXERCISE_DIR / ".meta" / "tests.toml"
EVIDENCE_DIR = REPO_ROOT / "work" / "R09-T001"

def main():
    print("=== Running R09-T001 automated checks ===")
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    results = {}

    # 1. Parse config.json
    if not CONFIG_PATH.is_file():
        sys.exit(f"ERROR: config.json not found at {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    solution_files = config.get("files", {}).get("solution", [])
    test_files = config.get("files", {}).get("test", [])
    example_files = config.get("files", {}).get("example", [])

    if not solution_files or not test_files or not example_files:
        sys.exit(f"ERROR: Incomplete file declarations in config.json: {config}")

    solution_rel = solution_files[0]
    test_rel = test_files[0]
    example_rel = example_files[0]

    solution_file = EXERCISE_DIR / solution_rel
    example_file = EXERCISE_DIR / example_rel
    test_file = EXERCISE_DIR / test_rel

    assert solution_file.is_file(), f"Missing solution stub: {solution_file}"
    assert example_file.is_file(), f"Missing example reference: {example_file}"
    assert test_file.is_file(), f"Missing test file: {test_file}"

    # Check learner stub is still unsolved
    stub_content = solution_file.read_text(encoding="utf-8")
    assert "The code below is an attempt of creating a printer for a ledger" in stub_content, "Learner stub was modified!"

    # 2. Parse tests.toml and verify canonical coverage
    with open(TESTS_TOML_PATH, "rb") as f:
        tests_toml = tomllib.load(f)

    total_cases = len(tests_toml)
    included_cases = sum(1 for v in tests_toml.values() if v.get("include", True))
    excluded_cases = sum(1 for v in tests_toml.values() if not v.get("include", True))

    target_uuid = "502c4106-0371-4e7c-a7d8-9ce33f16ccb1"
    assert target_uuid in tests_toml, f"Target UUID {target_uuid} not found in tests.toml"
    target_entry = tests_toml[target_uuid]
    assert target_entry.get("include") is False, f"Target UUID {target_uuid} should be excluded"
    assert "comment" in target_entry and len(target_entry["comment"]) > 10, "Target UUID rationale missing"

    print(f"tests.toml: total={total_cases}, included={included_cases}, excluded={excluded_cases}")
    print(f"Target {target_uuid} rationale: {target_entry['comment']}")

    # 3. Isolated Pester execution
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_exercise = Path(tmp_dir) / "ledger"
        shutil.copytree(EXERCISE_DIR, tmp_exercise)

        # Substitute reference into solution path inside temp copy only
        tmp_solution = tmp_exercise / solution_rel
        tmp_example = tmp_exercise / example_rel
        shutil.copy2(tmp_example, tmp_solution)

        # Environment setup for isolated, reproducible pwsh execution
        env = os.environ.copy()
        env["HOME"] = "/tmp"
        ps_module_dir = str(REPO_ROOT / ".modules")
        sys_module_dir = "/opt/homebrew/Cellar/powershell/7.7.0/libexec/Modules"
        env["PSModulePath"] = f"{ps_module_dir}:{sys_module_dir}"

        ps_cmd = (
            f"Push-Location '{tmp_exercise}'; "
            "$res = Invoke-Pester -PassThru; "
            "Pop-Location; "
            "$summary = @{ TotalCount = $res.TotalCount; PassedCount = $res.PassedCount; FailedCount = $res.FailedCount; SkippedCount = $res.SkippedCount }; "
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
            sys.exit(f"ERROR: pwsh execution failed with returncode {proc.returncode}")

        # Parse JSON summary from stdout
        lines = [line.strip() for line in proc.stdout.splitlines() if line.strip().startswith("{")]
        if not lines:
            sys.exit(f"ERROR: Could not parse test summary from stdout: {proc.stdout}")
        test_summary = json.loads(lines[-1])

    total_count = test_summary.get("TotalCount", 0)
    passed_count = test_summary.get("PassedCount", 0)
    failed_count = test_summary.get("FailedCount", 0)

    print(f"Pester results: Total={total_count}, Passed={passed_count}, Failed={failed_count}")
    if total_count == 0:
        sys.exit("ERROR: Zero tests were executed!")
    if failed_count > 0:
        sys.exit(f"ERROR: {failed_count} tests failed!")

    # 4. Save evidence to work/R09-T001
    results = {
        "task_id": "R09-T001",
        "exercise": "ledger",
        "target_uuid": target_uuid,
        "rationale": target_entry["comment"],
        "tests_toml_stats": {
            "total": total_cases,
            "included": included_cases,
            "excluded": excluded_cases,
        },
        "pester_results": test_summary,
        "tools": {
            "python": sys.version,
            "powershell": "7.7.0",
            "pester": "6.2.0"
        },
        "success": True
    }

    results_file = EVIDENCE_DIR / "results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    log_file = EVIDENCE_DIR / "run.log"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"R09-T001 check run\n")
        f.write(f"Target UUID: {target_uuid}\n")
        f.write(f"Rationale: {target_entry['comment']}\n")
        f.write(f"Pester execution output:\n{proc.stdout}\n")

    print(f"Check passed successfully! Evidence saved to {EVIDENCE_DIR}")

if __name__ == "__main__":
    main()
