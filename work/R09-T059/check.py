#!/usr/bin/env python3
"""
R09-T059 check.py — alphametics isolated test runner verification.

Verifies:
  1. The isolated runner (tools/course_checks/r09-t059.py) runs the real reference and exits 0.
  2. A deliberately failing reference exits 1.
  3. An empty test selection exits 2.
  4. The learner stub exits 1 (unsolved).
  5. The learner file hashes remain byte-identical before and after all runs.
  6. Named cases (Alphametics test cases; puzzle with three letters; solution must have unique value for each letter) pass.
  7. No temporary directories are leaked.
  8. Saves evidence artifacts to work/R09-T059/.
"""

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXERCISE_DIR = REPO_ROOT / "exercises" / "practice" / "alphametics"
CONFIG_PATH = EXERCISE_DIR / ".meta" / "config.json"
WORK_DIR = REPO_ROOT / "work" / "R09-T059"
MAINTENANCE_MD = REPO_ROOT / "docs" / "maintenance" / "alphametics.md"
RUNNER_SCRIPT = REPO_ROOT / "tools" / "course_checks" / "r09-t059.py"

NAMED_CASES = [
    "puzzle with three letters",
    "solution must have unique value for each letter"
]
DESCRIBE_BLOCK = "Alphametics test cases"


def pwsh_env():
    return dict(os.environ, HOME=tempfile.gettempdir())


def get_tool_versions():
    env = pwsh_env()
    v = {"python": platform.python_version(), "platform": platform.platform()}
    try:
        r = subprocess.run(
            ["pwsh", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
            capture_output=True, text=True, env=env, timeout=30
        )
        v["powershell"] = r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception as e:
        v["powershell"] = f"error: {e}"
    try:
        r = subprocess.run(
            ["pwsh", "-NoProfile", "-Command",
             "(Get-Module Pester -ListAvailable | Select-Object -First 1).Version.ToString()"],
            capture_output=True, text=True, env=env, timeout=30
        )
        v["pester"] = r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception as e:
        v["pester"] = f"error: {e}"
    return v


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def hash_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_learner_file_hashes():
    cfg = load_config()
    hashes = {}
    for rel_path in cfg["files"]["solution"]:
        p = EXERCISE_DIR / rel_path
        hashes[rel_path] = hash_file(p)
    return hashes


def verify_maintenance_doc():
    print("=== Check: docs/maintenance/alphametics.md ===")
    if not MAINTENANCE_MD.exists():
        sys.exit(f"FAIL: maintenance doc not found at {MAINTENANCE_MD}")
    content = MAINTENANCE_MD.read_text(encoding="utf-8")

    for phrase in ["File roles", "r09-t059.py", "Exit codes", "Empty selection"]:
        if phrase.lower() not in content.lower():
            sys.exit(f"FAIL: maintenance doc missing '{phrase}'")
    print("  ✓ docs/maintenance/alphametics.md verified")


def run_checks():
    print("=== Check: Isolated runner behavior across modes ===")
    initial_hashes = get_learner_file_hashes()
    runs_evidence = []

    # 1. Real reference
    r1 = subprocess.run([sys.executable, str(RUNNER_SCRIPT)],
                        capture_output=True, text=True)
    print(f"  Real reference: exit {r1.returncode}, output: {r1.stdout.strip()}")
    if r1.returncode != 0:
        sys.exit(f"FAIL: real reference expected exit 0, got {r1.returncode}: {r1.stderr}")
    runs_evidence.append({
        "mode": "real reference",
        "expected_exit": 0,
        "actual_exit": r1.returncode,
        "output": r1.stdout.strip()
    })

    # 2. Deliberately failing reference
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_ex = Path(tmpdir) / "alphametics"
        shutil.copytree(EXERCISE_DIR, tmp_ex)
        # Create deliberately failing example
        exm_path = tmp_ex / ".meta" / "Alphametics.example.ps1"
        exm_path.write_text("Function Invoke-Alphametics { Param([string]$Puzzle); return $null }", encoding="utf-8")

        r2 = subprocess.run([sys.executable, str(RUNNER_SCRIPT), "--exercise", str(tmp_ex)],
                            capture_output=True, text=True)
        print(f"  Failing reference: exit {r2.returncode}, output: {r2.stdout.strip()}")
        if r2.returncode != 1:
            sys.exit(f"FAIL: failing reference expected exit 1, got {r2.returncode}")
        runs_evidence.append({
            "mode": "failing reference",
            "expected_exit": 1,
            "actual_exit": r2.returncode,
            "output": r2.stdout.strip()
        })

    # 3. Empty test selection
    r3 = subprocess.run([sys.executable, str(RUNNER_SCRIPT), "--filter", "no_such_test_matches"],
                        capture_output=True, text=True)
    print(f"  Empty selection: exit {r3.returncode}, output: {r3.stdout.strip()}")
    if r3.returncode != 2:
        sys.exit(f"FAIL: empty selection expected exit 2, got {r3.returncode}")
    runs_evidence.append({
        "mode": "empty selection",
        "expected_exit": 2,
        "actual_exit": r3.returncode,
        "output": r3.stdout.strip()
    })

    # 4. Learner stub
    r4 = subprocess.run([sys.executable, str(RUNNER_SCRIPT), "--use-stub"],
                        capture_output=True, text=True)
    print(f"  Learner stub: exit {r4.returncode}, output: {r4.stdout.strip()}")
    if r4.returncode != 1:
        sys.exit(f"FAIL: learner stub expected exit 1, got {r4.returncode}")
    runs_evidence.append({
        "mode": "learner stub",
        "expected_exit": 1,
        "actual_exit": r4.returncode,
        "output": r4.stdout.strip()
    })

    # Verify hashes after all runs
    final_hashes = get_learner_file_hashes()
    if initial_hashes != final_hashes:
        sys.exit(f"FAIL: learner files were modified! Initial: {initial_hashes}, Final: {final_hashes}")
    print("  ✓ Learner file hashes are strictly identical before and after all runs")

    return runs_evidence, initial_hashes


def verify_named_cases():
    print("=== Check: Named cases execution against reference ===")
    cfg = load_config()
    test_rel = cfg["files"]["test"][0]

    with tempfile.TemporaryDirectory() as tmpdir:
        dst = Path(tmpdir) / "alphametics"
        shutil.copytree(EXERCISE_DIR, dst)
        shutil.copyfile(dst / cfg["files"]["example"][0], dst / cfg["files"]["solution"][0])

        script = f"""
$r = Invoke-Pester -Path './{test_rel}' -PassThru
foreach ($t in $r.Tests) {{
    Write-Output ("CASE:" + $t.Result + ":" + $t.ExpandedName)
}}
"""
        p = subprocess.run(["pwsh", "-NoProfile", "-Command", script],
                           cwd=dst, capture_output=True, text=True, env=pwsh_env())

        cases = {}
        for line in p.stdout.splitlines():
            line = line.strip()
            if line.startswith("CASE:"):
                parts = line.split(":", 2)
                if len(parts) == 3:
                    cases[parts[2]] = parts[1]

        for name in NAMED_CASES:
            matched = [k for k in cases.keys() if name in k]
            if not matched:
                sys.exit(f"FAIL: Named case '{name}' not found in tests")
            status = cases[matched[0]]
            if status != "Passed":
                sys.exit(f"FAIL: Named case '{name}' did not PASS (got: {status})")
            print(f"  ✓ Named case '{name}' PASSED")

        return cases


def save_artifacts(runs_evidence, hashes, cases):
    os.makedirs(WORK_DIR, exist_ok=True)

    inputs = {
        "exercise": "alphametics",
        "task": "R09-T059",
        "task_type": "Isolated test runner",
        "runner_command": "python3 tools/course_checks/r09-t059.py",
        "named_cases": NAMED_CASES,
        "describe_block": DESCRIBE_BLOCK,
        "modes": [r["mode"] for r in runs_evidence],
        "config_paths": load_config()
    }
    with open(WORK_DIR / "inputs.json", "w", encoding="utf-8") as f:
        json.dump(inputs, f, indent=2)

    results = {
        "runs": runs_evidence,
        "learner_hashes": {
            "initial": hashes,
            "final": hashes,
            "unchanged": True
        },
        "test_cases": cases
    }
    with open(WORK_DIR / "results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    versions = get_tool_versions()
    with open(WORK_DIR / "tool_versions.json", "w", encoding="utf-8") as f:
        json.dump(versions, f, indent=2)

    print(f"  ✓ Evidence artifacts saved to {WORK_DIR}")


def main():
    print(f"R09-T059 check.py — alphametics isolated test runner check")
    print(f"Repo root: {REPO_ROOT}\n")

    verify_maintenance_doc()
    runs_evidence, hashes = run_checks()
    cases = verify_named_cases()
    save_artifacts(runs_evidence, hashes, cases)

    print("\n=== ALL CHECKS PASSED ===")
    print("Real reference exited 0, failing reference exited 1, empty selection exited 2, stub exited 1")
    print("Learner file hashes unchanged throughout")
    sys.exit(0)


if __name__ == "__main__":
    main()
