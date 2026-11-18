#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXERCISE_DIR = REPO_ROOT / "exercises" / "practice" / "reverse-string"
CONFIG_PATH = EXERCISE_DIR / ".meta" / "config.json"
EVIDENCE_DIR = REPO_ROOT / "work" / "R09-T004"

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
        "$summary = @{ TotalCount = $res.TotalCount; PassedCount = $res.PassedCount; FailedCount = $res.FailedCount; SkippedCount = $res.SkippedCount }; "
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

def test_wide_characters(example_file):
    env = os.environ.copy()
    env["HOME"] = "/tmp"
    ps_cmd = f". '{example_file}'; Get-ReverseString -Forward '子猫'"
    proc = subprocess.run(
        ["pwsh", "-NoProfile", "-Command", ps_cmd],
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.stdout.strip()

def main():
    print("=== Running R09-T004 check.py ===")
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

    # 1. Test reference solution in isolated copy
    print("Testing refactored reference implementation in temporary directory...")
    with tempfile.TemporaryDirectory() as tmp:
        copy_dir = Path(tmp) / "reverse-string"
        shutil.copytree(EXERCISE_DIR, copy_dir)
        shutil.copy2(copy_dir / example_rel, copy_dir / solution_rel)

        summary, stdout = run_pester(copy_dir)
        print(f"Pester results: Total={summary['TotalCount']}, Passed={summary['PassedCount']}, Failed={summary['FailedCount']}, Skipped={summary.get('SkippedCount', 0)}")
        assert summary["TotalCount"] > 0, "No tests executed!"
        assert summary["FailedCount"] == 0, f"{summary['FailedCount']} tests failed!"

    # 2. Verify wide character support directly
    wide_res = test_wide_characters(EXERCISE_DIR / example_rel)
    print(f"Wide characters test ('子猫' -> expected '猫子'): got '{wide_res}'")
    assert wide_res == "猫子", f"Wide character test failed: expected '猫子', got '{wide_res}'"

    # 3. Save evidence
    readability_diff = (
        "- Clarified variable names from ambiguous `$textElements` and `$graphemes` to `$elementEnumerator` and `$reversedGraphemes`.\n"
        "- Added explicit documentation comment explaining the Unicode grapheme cluster invariant.\n"
        "- Added explicit `return` statement to clarify pipeline exit."
    )

    results = {
        "task_id": "R09-T004",
        "exercise": "reverse-string",
        "pester_results": summary,
        "wide_characters_result": wide_res,
        "readability_improvement": readability_diff,
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
        f.write("R09-T004 Automated Check Log\n")
        f.write(f"Pester output:\n{stdout}\n")
        f.write(f"Wide characters verification: {wide_res}\n")
        f.write(f"Readability diff explanation:\n{readability_diff}\n")

    print(f"R09-T004 check completed successfully! Evidence saved to {EVIDENCE_DIR}")

if __name__ == "__main__":
    main()
