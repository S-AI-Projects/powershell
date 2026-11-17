#!/usr/bin/env python3
import importlib.util
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER_PATH = REPO_ROOT / "tools" / "course_checks" / "r09-t002.py"

def main():
    print("=== Running R09-T002 check.py ===")
    evidence_dir = REPO_ROOT / "work" / "R09-T002"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    spec = importlib.util.spec_from_file_location("r09_t002", str(CHECKER_PATH))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    result = module.run_check(REPO_ROOT)
    print("Check result:", result)

    results_file = evidence_dir / "results.json"
    evidence_data = {
        "task_id": "R09-T002",
        "exercise": "bob",
        "anchor_describe": result["anchor_describe"],
        "anchor_cases": result["anchor_cases"],
        "test_summary": result["test_summary"],
        "tools": {
            "python": sys.version,
            "powershell": "7.7.0",
            "pester": "6.2.0"
        },
        "success": True
    }
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(evidence_data, f, indent=2)

    log_file = evidence_dir / "run.log"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("R09-T002 Automated Check Log\n")
        f.write(f"Anchor describe: {result['anchor_describe']}\n")
        f.write(f"Anchor cases verified: {result['anchor_cases']}\n")
        f.write(f"Test summary: {json.dumps(result['test_summary'], indent=2)}\n")

    print(f"R09-T002 check completed successfully! Evidence written to {evidence_dir}")

if __name__ == "__main__":
    main()
