#!/usr/bin/env python3
"""Run an exercise's Pester tests against its reference in an isolated temporary copy.

Usage: python3 tools/course_checks/r09-t019.py [--exercise DIR] [--filter PATTERN]
                                              [--use-stub] [--pause SECONDS]
The reference named in .meta/config.json replaces the solution file in the copy only;
the working tree is never written. Prints "Executed cases: N". Exit codes:
0 passed, 1 test failure or child error, 2 no test executed, 130 interrupted.
"""
import argparse, json, os, shutil, signal, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PS = (
    '$p = @{PassThru = $true}; if ($env:R09_FILTER) { $p.FullNameFilter = $env:R09_FILTER }; '
    'if ($env:R09_PAUSE) { Start-Sleep -Seconds ([int]$env:R09_PAUSE) }; '
    '$r = Invoke-Pester @p; "RESULT_JSON:" + ([pscustomobject]@{Result="$($r.Result)"; '
    'Total=$r.TotalCount; Passed=$r.PassedCount; Failed=$r.FailedCount; NotRun=$r.NotRunCount; '
    'FailedContainers=$r.FailedContainersCount; Tests=@($r.Tests | ForEach-Object '
    '{ [pscustomobject]@{Name=$_.Name; Result="$($_.Result)"} })} | ConvertTo-Json -Depth 4 -Compress)'
)


def _stop(signum, frame):
    raise KeyboardInterrupt


def parse(stdout):
    lines = [l for l in stdout.splitlines() if l.startswith("RESULT_JSON:")]
    return json.loads(lines[-1][12:]) if lines else None


def report(p):
    r = parse(p.stdout)
    if p.returncode != 0 or r is None:
        print(f"ERROR: child process failed (exit code {p.returncode}) or gave no result")
        print(p.stderr.strip()[-500:])
        return 1
    executed = r["Passed"] + r["Failed"]
    print(f"Executed cases: {executed}  Passed: {r['Passed']}  Failed: {r['Failed']}  "
          f"Not run: {r['NotRun']}  Total: {r['Total']}")
    for t in r["Tests"]:
        print(f"  [{t['Result']}] {t['Name']}")
    if r["Failed"] > 0 or r["FailedContainers"] > 0 or r["Result"] == "Failed":
        print("FAILED: at least one test failed")
        return 1
    if r["Total"] == 0 or executed == 0:
        print("ERROR: no test was executed")
        return 2
    print("OK: all executed tests passed")
    return 0


def run(args):
    ex = Path(args.exercise).resolve()
    cfg = json.loads((ex / ".meta" / "config.json").read_text())["files"]
    sol, exm = cfg["solution"], cfg["example"]
    tmp = None
    try:
        tmp = tempfile.mkdtemp(prefix="r09t019-")
        dst = Path(tmp) / ex.name
        shutil.copytree(ex, dst)  # copies dotfiles too
        if not args.use_stub:
            shutil.copyfile(dst / exm[0], dst / sol[0])  # substitution in the copy only
        env = dict(os.environ, R09_FILTER=args.filter or "", R09_PAUSE=str(args.pause or ""))
        p = subprocess.run(["pwsh", "-NoProfile", "-Command", PS], cwd=dst,
                           capture_output=True, text=True, env=env)
        return report(p)
    except KeyboardInterrupt:
        print("INTERRUPTED: temporary copy removed, working tree untouched")
        return 130
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exercise", default=str(ROOT / "exercises" / "practice" / "house"))
    ap.add_argument("--filter")
    ap.add_argument("--use-stub", action="store_true")
    ap.add_argument("--pause", type=int, help="seconds to wait before testing (interruption tests)")
    signal.signal(signal.SIGTERM, _stop)
    return run(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
