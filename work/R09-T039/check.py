#!/usr/bin/env python3
"""Exercise the list-ops reference runner's pass, failure, and zero-test paths."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[2]
EXERCISE = ROOT / "exercises/practice/list-ops"
RUNNER = ROOT / "tools/course_checks/r09-t039.py"
SCENARIOS = ["reference", "failing-reference", "empty-selection"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "work/R09-T039/results.json")
    parser.add_argument("--log", type=Path, default=ROOT / "work/R09-T039/runner.log")
    args = parser.parse_args()
    output = args.output.resolve()
    log_path = args.log.resolve()
    config = json.loads((EXERCISE / ".meta/config.json").read_text(encoding="utf-8"))
    solution = EXERCISE / config["files"]["solution"][0]
    initial_hash = hashlib.sha256(solution.read_bytes()).hexdigest()
    declared_tests = len(re.findall(r"(?m)^\s*It\s+\"", (EXERCISE / config["files"]["test"][0]).read_text(encoding="utf-8")))
    evidence: dict[str, object] = {
        "status": "failed",
        "task": "R09-T039",
        "exercise": "list-ops",
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "declaredTestCount": declared_tests,
        "learnerSolutionHashBeforeAllRuns": initial_hash,
        "scenarios": {},
    }
    log_parts: list[str] = []
    errors: list[str] = []

    try:
        with tempfile.TemporaryDirectory(prefix="list-ops-runner-harness-") as temporary:
            temporary_root = Path(temporary)
            for mode in SCENARIOS:
                result_path = temporary_root / f"{mode}.json"
                log_path_for_run = temporary_root / f"{mode}.log"
                process = subprocess.run(
                    [
                        sys.executable,
                        str(RUNNER),
                        "--mode",
                        mode,
                        "--output",
                        str(result_path),
                        "--log",
                        str(log_path_for_run),
                    ],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=240,
                )
                log_parts.append(f"=== {mode} helper output ===\n{process.stdout}{process.stderr}")
                if log_path_for_run.is_file():
                    log_parts.append(f"=== {mode} Pester log ===\n{log_path_for_run.read_text(encoding='utf-8')}")
                if not result_path.is_file():
                    errors.append(f"{mode}: runner wrote no result evidence (exit {process.returncode})")
                    continue
                run_data = json.loads(result_path.read_text(encoding="utf-8"))
                run_data["helperExitCode"] = process.returncode
                evidence["scenarios"][mode] = run_data

                if run_data.get("learnerSolutionHashBefore") != initial_hash:
                    errors.append(f"{mode}: learner hash before run differed from baseline")
                if run_data.get("learnerSolutionHashAfter") != initial_hash:
                    errors.append(f"{mode}: learner hash after run differed from baseline")
                if not run_data.get("temporaryDirectoryCleaned"):
                    errors.append(f"{mode}: temporary directory was not cleaned")

                pester = run_data.get("pester") or {}
                if mode == "reference":
                    if process.returncode != 0 or run_data.get("status") != "passed":
                        errors.append("reference: expected successful runner exit")
                    if pester.get("totalCount") != declared_tests or pester.get("failedCount") != 0:
                        errors.append("reference: expected every declared case to pass")
                    probes = pester.get("probes", [])
                    if not probes or not all(probe.get("matchesExpected") for probe in probes):
                        errors.append("reference: expected named inputs did not match actual outputs")
                elif mode == "failing-reference":
                    if process.returncode == 0 or pester.get("failedCount", 0) <= 0:
                        errors.append("failing-reference: runner did not propagate an assertion failure")
                    if run_data.get("pesterChildExitCode") != 1:
                        errors.append("failing-reference: expected Pester child exit code 1")
                    list_case = next((probe for probe in pester.get("probes", []) if probe.get("name") == "list to empty list"), None)
                    if not list_case or list_case.get("matchesExpected"):
                        errors.append("failing-reference: deliberate append defect did not fail its expected/actual probe")
                else:
                    if process.returncode == 0 or pester.get("totalCount") != 0:
                        errors.append("empty-selection: runner did not reject a zero-test selection")
                    if run_data.get("pesterChildExitCode") != 2:
                        errors.append("empty-selection: expected Pester child exit code 2")

        final_hash = hashlib.sha256(solution.read_bytes()).hexdigest()
        evidence["learnerSolutionHashAfterAllRuns"] = final_hash
        if final_hash != initial_hash:
            errors.append("learner solution hash changed across the scenario suite")
        evidence["overallLearnerFileUnchanged"] = final_hash == initial_hash
        if errors:
            evidence["errors"] = errors
        else:
            evidence["status"] = "passed"
            reference = evidence["scenarios"]["reference"]["pester"]
            failing = evidence["scenarios"]["failing-reference"]["pester"]
            print(
                f"PASS: reference {reference['passedCount']}/{reference['totalCount']}; "
                f"failing reference propagated {failing['failedCount']} assertion failures; "
                "zero-test selection rejected; learner file unchanged after all runs."
            )
            return 0
        print("; ".join(errors), file=sys.stderr)
        return 1
    except Exception as exc:
        evidence["error"] = f"{type(exc).__name__}: {exc}"
        print(evidence["error"], file=sys.stderr)
        return 1
    finally:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        cleaned_log = "\n".join(part.rstrip() for part in log_parts if part and part.rstrip())
        log_path.write_text(cleaned_log + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
