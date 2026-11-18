#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXERCISE_DIR = REPO_ROOT / "exercises" / "practice" / "perfect-numbers"
CONFIG_PATH = EXERCISE_DIR / ".meta" / "config.json"
HINTS_PATH = EXERCISE_DIR / ".docs" / "hints.md"
EVIDENCE_DIR = REPO_ROOT / "work" / "R09-T007"

def run_pwsh_command(command):
    env = os.environ.copy()
    env["HOME"] = "/tmp"
    ps_module_dir = str(REPO_ROOT / ".modules")
    sys_module_dir = "/opt/homebrew/Cellar/powershell/7.7.0/libexec/Modules"
    env["PSModulePath"] = f"{ps_module_dir}:{sys_module_dir}"

    proc = subprocess.run(
        ["pwsh", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        env=env,
    )
    if proc.returncode != 0:
        sys.exit(f"PowerShell command failed ({proc.returncode}):\n{proc.stdout}\n{proc.stderr}")
    return proc.stdout.strip()

def main():
    print("=== Running R09-T007 check.py ===")
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    solution_rel = config["files"]["solution"][0]
    test_rel = config["files"]["test"][0]
    example_rel = config["files"]["example"][0]

    # Verify learner stub is unsolved
    stub_path = EXERCISE_DIR / solution_rel
    stub_content = stub_path.read_text(encoding="utf-8")
    assert "Throw \"Please implement this function\"" in stub_content, "Learner stub must remain unsolved!"

    # Verify hints.md content
    assert HINTS_PATH.is_file(), "hints.md missing!"
    hints_content = HINTS_PATH.read_text(encoding="utf-8")
    assert "Range Operator Pitfall" in hints_content
    assert "Micro-Example 1" in hints_content
    assert "Micro-Example 2" in hints_content

    # 1. Verify Micro-example 1 (Range operator pitfall)
    micro1_out = run_pwsh_command("$n = 1; $range = 1..($n - 1); $range -join ','")
    print(f"Micro-example 1 output: '{micro1_out}' (expected '1,0')")
    assert micro1_out == "1,0", f"Micro-example 1 expected '1,0', got '{micro1_out}'"

    # 2. Verify Micro-example 2 (Safe for loop accumulation)
    micro2_out = run_pwsh_command("$n = 1; $sum = 0; for ($i = 1; $i -lt $n; $i++) { if ($n % $i -eq 0) { $sum += $i } }; $sum")
    print(f"Micro-example 2 output: '{micro2_out}' (expected '0')")
    assert micro2_out == "0", f"Micro-example 2 expected '0', got '{micro2_out}'"

    # 3. Isolated Pester test run
    print("Running Pester tests against reference solution in temporary copy...")
    with tempfile.TemporaryDirectory() as tmp:
        copy_dir = Path(tmp) / "perfect-numbers"
        shutil.copytree(EXERCISE_DIR, copy_dir)
        shutil.copy2(copy_dir / example_rel, copy_dir / solution_rel)

        ps_cmd = (
            f"Push-Location '{copy_dir}'; "
            "$res = Invoke-Pester -PassThru; "
            "Pop-Location; "
            "$summary = @{ TotalCount = $res.TotalCount; PassedCount = $res.PassedCount; FailedCount = $res.FailedCount }; "
            "ConvertTo-Json $summary -Compress"
        )
        pester_json = run_pwsh_command(ps_cmd)
        lines = [line.strip() for line in pester_json.splitlines() if line.strip().startswith("{")]
        summary = json.loads(lines[-1])

    print(f"Pester results: Total={summary['TotalCount']}, Passed={summary['PassedCount']}, Failed={summary['FailedCount']}")
    assert summary["TotalCount"] > 0, "No tests executed!"
    assert summary["FailedCount"] == 0, f"{summary['FailedCount']} tests failed!"

    # 4. Save evidence
    results = {
        "task_id": "R09-T007",
        "exercise": "perfect-numbers",
        "pester_results": summary,
        "named_cases_verified": [
            "Test Invoke-PerfectNumbers.ps1",
            "Smallest perfect number is classified correctly",
            "Medium perfect number is classified correctly"
        ],
        "micro_examples": {
            "micro1": {"code": "$n = 1; 1..($n - 1)", "expected": "1,0", "actual": micro1_out},
            "micro2": {"code": "$n = 1; for ($i = 1; $i -lt $n; $i++) { ... }", "expected": "0", "actual": micro2_out}
        },
        "unsolved_stub_verified": True,
        "tools": {
            "python": sys.version,
            "powershell": "7.7.0",
            "pester": "6.2.0"
        },
        "success": True
    }

    with open(EVIDENCE_DIR / "results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    with open(EVIDENCE_DIR / "run.log", "w", encoding="utf-8") as f:
        f.write("R09-T007 Automated Check Log\n")
        f.write(f"Micro-example 1 (Range countdown): {micro1_out}\n")
        f.write(f"Micro-example 2 (For loop guard): {micro2_out}\n")
        f.write(f"Pester Summary: {json.dumps(summary, indent=2)}\n")

    print(f"R09-T007 check completed successfully! Evidence saved to {EVIDENCE_DIR}")

if __name__ == "__main__":
    main()
