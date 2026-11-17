#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXERCISE_DIR = REPO_ROOT / "exercises" / "practice" / "hamming"
CONFIG_PATH = EXERCISE_DIR / ".meta" / "config.json"
EVIDENCE_DIR = REPO_ROOT / "work" / "R09-T003"

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
    print("=== Running R09-T003 check.py ===")
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

    # 1. Test genuine reference solution
    print("Testing original reference implementation...")
    with tempfile.TemporaryDirectory() as tmp1:
        copy1 = Path(tmp1) / "hamming"
        shutil.copytree(EXERCISE_DIR, copy1)
        shutil.copy2(copy1 / example_rel, copy1 / solution_rel)

        ref_summary, ref_stdout = run_pester(copy1)
        print(f"Reference results: Total={ref_summary['TotalCount']}, Passed={ref_summary['PassedCount']}, Failed={ref_summary['FailedCount']}")
        assert ref_summary["TotalCount"] > 0, "No tests executed on reference!"
        assert ref_summary["FailedCount"] == 0, f"Reference failed {ref_summary['FailedCount']} tests!"

    # 2. Test mutated reference solution
    print("Testing mutated reference implementation (condition inversion: -ne -> -eq)...")
    with tempfile.TemporaryDirectory() as tmp2:
        copy2 = Path(tmp2) / "hamming"
        shutil.copytree(EXERCISE_DIR, copy2)

        # Apply mutation: invert comparison condition
        mutant_code = (copy2 / example_rel).read_text(encoding="utf-8")
        assert "$first[$i] -ne $second[$i]" in mutant_code, "Comparison condition not found in reference!"
        mutated_code = mutant_code.replace("$first[$i] -ne $second[$i]", "$first[$i] -eq $second[$i]")
        (copy2 / solution_rel).write_text(mutated_code, encoding="utf-8")

        mutant_summary, mutant_stdout = run_pester(copy2)
        print(f"Mutant results: Total={mutant_summary['TotalCount']}, Passed={mutant_summary['PassedCount']}, Failed={mutant_summary['FailedCount']}")
        assert mutant_summary["FailedCount"] > 0, "Mutant unexpectedly passed all tests!"
        assert "single letter identical strands" in mutant_stdout, "Mutant was not rejected by expected test!"

    # 3. Save evidence
    results = {
        "task_id": "R09-T003",
        "exercise": "hamming",
        "reference_summary": ref_summary,
        "mutant_summary": mutant_summary,
        "mutant_description": "Inverted condition from -ne to -eq in nucleotide mismatch loop",
        "rejecting_test": "single letter identical strands",
        "minimal_input": {"strand1": "A", "strand2": "A"},
        "expected": 0,
        "mutant_output": 1,
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
        f.write("R09-T003 Automated Check Log\n")
        f.write(f"Reference Summary: {json.dumps(ref_summary)}\n")
        f.write(f"Mutant Summary: {json.dumps(mutant_summary)}\n")
        f.write(f"Mutant Pester Output:\n{mutant_stdout}\n")

    print(f"R09-T003 check completed successfully! Evidence saved to {EVIDENCE_DIR}")

if __name__ == "__main__":
    main()
