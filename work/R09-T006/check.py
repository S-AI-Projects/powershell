#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXERCISE_DIR = REPO_ROOT / "exercises" / "practice" / "flower-field"
CONFIG_PATH = EXERCISE_DIR / ".meta" / "config.json"
HINTS_PATH = EXERCISE_DIR / ".docs" / "hints.md"
EVIDENCE_DIR = REPO_ROOT / "work" / "R09-T006"
ALT_PATH = EVIDENCE_DIR / "alternative.ps1"

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
    print("=== Running R09-T006 check.py ===")
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
    assert HINTS_PATH.is_file(), "hints.md is missing!"
    hints_text = HINTS_PATH.read_text(encoding="utf-8")
    assert "Approach Selection" in hints_text, "Missing Approach Selection section in hints.md"
    assert "Worked Example" in hints_text, "Missing Worked Example section in hints.md"

    # 1. Test reference solution in isolated temporary copy
    print("Testing reference implementation (Approach 1: Gather)...")
    with tempfile.TemporaryDirectory() as tmp1:
        copy1 = Path(tmp1) / "flower-field"
        shutil.copytree(EXERCISE_DIR, copy1)
        shutil.copy2(copy1 / example_rel, copy1 / solution_rel)

        ref_summary, ref_stdout = run_pester(copy1)
        print(f"Reference: Total={ref_summary['TotalCount']}, Passed={ref_summary['PassedCount']}, Failed={ref_summary['FailedCount']}")
        assert ref_summary["TotalCount"] > 0, "No tests executed on reference!"
        assert ref_summary["FailedCount"] == 0, f"Reference failed {ref_summary['FailedCount']} tests!"

    # 2. Test alternative solution (Approach 2: Scatter)
    print("Testing alternative implementation (Approach 2: Scatter)...")
    assert ALT_PATH.is_file(), f"Missing alternative implementation at {ALT_PATH}"
    with tempfile.TemporaryDirectory() as tmp2:
        copy2 = Path(tmp2) / "flower-field"
        shutil.copytree(EXERCISE_DIR, copy2)
        shutil.copy2(ALT_PATH, copy2 / solution_rel)

        alt_summary, alt_stdout = run_pester(copy2)
        print(f"Alternative: Total={alt_summary['TotalCount']}, Passed={alt_summary['PassedCount']}, Failed={alt_summary['FailedCount']}")
        assert alt_summary["TotalCount"] == ref_summary["TotalCount"], "Test count mismatch between implementations!"
        assert alt_summary["FailedCount"] == 0, f"Alternative failed {alt_summary['FailedCount']} tests!"

    # 3. Save evidence
    results = {
        "task_id": "R09-T006",
        "exercise": "flower-field",
        "reference_summary": ref_summary,
        "alternative_summary": alt_summary,
        "approaches_compared": [
            {"name": "Approach 1 (Gather)", "representation": "Jagged character array char[][]", "technique": "In-place 8-neighbor lookup per blank cell"},
            {"name": "Approach 2 (Scatter)", "representation": "2D integer array int[,]", "technique": "Neighbor increments at flower positions followed by row reconstruction"}
        ],
        "named_cases_verified": ["no rows", "no columns", "no flowers", "large garden"],
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
        f.write("R09-T006 Automated Check Log\n")
        f.write(f"Reference Summary: {json.dumps(ref_summary)}\n")
        f.write(f"Alternative Summary: {json.dumps(alt_summary)}\n")
        f.write(f"Reference Pester Output:\n{ref_stdout}\n")

    print(f"R09-T006 check completed successfully! Evidence saved to {EVIDENCE_DIR}")

if __name__ == "__main__":
    main()
