#!/usr/bin/env python3
"""Run an exercise's Pester tests against its reference in an isolated temporary copy.

Usage: python3 tools/course_checks/r09-t059.py [--exercise DIR] [--filter PATTERN]
                                              [--use-stub] [--pause SECONDS]
The reference named in .meta/config.json replaces the solution file in the copy only;
the working tree is never written. Prints "Executed cases: N". Exit codes:
0 passed, 1 test failure or child error, 2 no test executed, 130 interrupted.
"""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EX = ROOT / "exercises" / "practice" / "alphametics"

PS_SCRIPT = """
$p = @{ PassThru = $true }
if ($env:R09_FILTER) { $p.FullNameFilter = $env:R09_FILTER }
if ($env:R09_PAUSE) { Start-Sleep -Seconds ([int]$env:R09_PAUSE) }
$r = Invoke-Pester @p
$executed = ($r.Tests | Where-Object { $_.Executed }).Count
Write-Output ("RESULT_JSON:" + ([pscustomobject]@{
    Result = "$($r.Result)"
    Total = $r.TotalCount
    Passed = $r.PassedCount
    Failed = $r.FailedCount
    Skipped = $r.SkippedCount
    NotRun = $r.NotRunCount
    Executed = $executed
    Tests = @($r.Tests | ForEach-Object { [pscustomobject]@{ Name = $_.Name; Result = "$($_.Result)"; Executed = $_.Executed } })
} | ConvertTo-Json -Depth 4 -Compress))
"""


def _stop(signum, frame):
    raise KeyboardInterrupt


def parse_output(stdout):
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("RESULT_JSON:"):
            return json.loads(line[12:])
    return None


def run_isolated(exercise_dir, pester_filter=None, use_stub=False, pause=None):
    ex = Path(exercise_dir).resolve()
    cfg_file = ex / ".meta" / "config.json"
    if not cfg_file.is_file():
        print(f"ERROR: missing config at {cfg_file}", file=sys.stderr)
        return 1

    try:
        cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
        sol_rel = cfg["files"]["solution"][0]
        exm_rel = cfg["files"]["example"][0]
    except Exception as e:
        print(f"ERROR: failed parsing config: {e}", file=sys.stderr)
        return 1

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    tmp = None
    try:
        tmp = tempfile.mkdtemp(prefix="alphametics_run_")
        dst = Path(tmp) / ex.name
        shutil.copytree(ex, dst)

        if not use_stub:
            shutil.copyfile(dst / exm_rel, dst / sol_rel)

        env = dict(os.environ, HOME=tempfile.gettempdir())
        if pester_filter:
            env["R09_FILTER"] = pester_filter
        if pause:
            env["R09_PAUSE"] = str(pause)

        runner_file = dst / "_runner.ps1"
        runner_file.write_text(PS_SCRIPT, encoding="utf-8")

        p = subprocess.run(
            ["pwsh", "-NoProfile", "-File", "_runner.ps1"],
            cwd=dst, capture_output=True, text=True, env=env
        )

        r = parse_output(p.stdout)
        if p.returncode != 0 or r is None:
            print(f"ERROR: Pester child execution failed (exit {p.returncode})", file=sys.stderr)
            return 1

        executed = r.get("Executed", 0)
        print(f"Executed cases: {executed}")

        if executed == 0:
            return 2
        if r.get("Failed", 0) > 0 or r.get("Result") == "Failed":
            return 1
        return 0

    except KeyboardInterrupt:
        return 130
    finally:
        if tmp and os.path.exists(tmp):
            shutil.rmtree(tmp, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Isolated Pester test runner for alphametics.")
    parser.add_argument("--exercise", default=str(DEFAULT_EX), help="Path to exercise directory")
    parser.add_argument("--filter", default=None, help="Pester FullNameFilter pattern")
    parser.add_argument("--use-stub", action="store_true", help="Run with learner stub instead of reference")
    parser.add_argument("--pause", type=int, default=None, help="Pause seconds before testing")

    args = parser.parse_args()
    rc = run_isolated(args.exercise, pester_filter=args.filter, use_stub=args.use_stub, pause=args.pause)
    sys.exit(rc)


if __name__ == "__main__":
    main()
