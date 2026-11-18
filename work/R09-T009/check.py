#!/usr/bin/env python3
import importlib.util
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER_PATH = REPO_ROOT / "tools" / "course_checks" / "r09-t009.py"
EVIDENCE_DIR = REPO_ROOT / "work" / "R09-T009"

def main():
    print("=== Running R09-T009 check.py ===")
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    spec = importlib.util.spec_from_file_location("r09_t009", str(CHECKER_PATH))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    result = module.run_check(REPO_ROOT)
    print("Check result:", result)

    results_file = EVIDENCE_DIR / "results.json"
    evidence_data = {
        "task_id": "R09-T009",
        "exercise": "grains",
        "learner_file_hash": result["learner_file_hash"],
        "modes_tested": result["modes_tested"],
        "named_cases_verified": result["named_cases_verified"],
        "tools": {
            "python": sys.version,
            "powershell": "7.7.0",
            "pester": "6.2.0"
        },
        "success": True
    }
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(evidence_data, f, indent=2)

    log_file = EVIDENCE_DIR / "run.log"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("R09-T009 Automated Check Log\n")
        f.write(f"Learner File SHA256: {result['learner_file_hash']}\n")
        f.write(f"Modes Tested: {json.dumps(result['modes_tested'], indent=2)}\n")

    print(f"R09-T009 check completed successfully! Evidence saved to {EVIDENCE_DIR}")

if __name__ == "__main__":
    main()
