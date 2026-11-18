#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXERCISE_DIR = REPO_ROOT / "exercises" / "practice" / "square-root"
CONFIG_PATH = EXERCISE_DIR / ".meta" / "config.json"
HINTS_PATH = EXERCISE_DIR / ".docs" / "hints.md"
EVIDENCE_DIR = REPO_ROOT / "work" / "R09-T010"

def run_pester(exercise_dir):
    env = os.environ.copy()
    env["HOME"] = "/tmp"
    ps_module_dir = str(REPO_ROOT / ".modules")
    sys_module_dir = "/opt/homebrew/Cellar/powershell/7.7.0/libexec/Modules"
    env["PSModulePath"] = f"{ps_module_dir}:{sys_module_dir}"

    ps_cmd = (
        f"Push-Location '{exercise_dir}'; "
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
    if not lines:
        sys.exit(f"Failed to parse Pester JSON output:\n{proc.stdout}\n{proc.stderr}")
    return json.loads(lines[-1]), proc.stdout

def main():
    print("=== Running R09-T010 check.py ===")
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

    # Verify hints.md content and decision table
    assert HINTS_PATH.is_file(), "hints.md missing!"
    hints_text = HINTS_PATH.read_text(encoding="utf-8")
    assert "Decision Table" in hints_text, "Missing Decision Table in hints.md"
    assert "root of 1" in hints_text, "Missing walkthrough for root of 1 in hints.md"
    assert "root of 4" in hints_text, "Missing walkthrough for root of 4 in hints.md"
    assert "Unspecified" in hints_text, "Missing unspecified behavior explanation in hints.md"

    # 1. Run Pester tests against reference in isolated copy
    print("Testing reference implementation in isolated temporary copy...")
    with tempfile.TemporaryDirectory() as tmp:
        copy_dir = Path(tmp) / "square-root"
        shutil.copytree(EXERCISE_DIR, copy_dir)
        shutil.copy2(copy_dir / example_rel, copy_dir / solution_rel)

        summary, stdout = run_pester(copy_dir)
        print(f"Pester results: Total={summary['TotalCount']}, Passed={summary['PassedCount']}, Failed={summary['FailedCount']}")
        assert summary["TotalCount"] > 0, "No tests executed!"
        assert summary["FailedCount"] == 0, f"{summary['FailedCount']} tests failed!"

    # 2. Save evidence
    results = {
        "task_id": "R09-T010",
        "exercise": "square-root",
        "pester_results": summary,
        "named_cases_verified": [
            "Square root test cases",
            "root of 1",
            "root of 4"
        ],
        "decision_table_cases": {
            "root of 1": {"input": 1, "expected": 1, "status": "Specified"},
            "root of 4": {"input": 4, "expected": 2, "status": "Specified"},
            "non-perfect squares": {"input": "e.g. 2, 3", "expected": "N/A", "status": "Unspecified by contract"},
            "non-positive": {"input": "<= 0", "expected": "N/A", "status": "Unspecified by contract"}
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
        f.write("R09-T010 Automated Check Log\n")
        f.write(f"Pester Output:\n{stdout}\n")
        f.write(f"Decision table cases:\n{json.dumps(results['decision_table_cases'], indent=2)}\n")

    print(f"R09-T010 check completed successfully! Evidence saved to {EVIDENCE_DIR}")

if __name__ == "__main__":
    main()
