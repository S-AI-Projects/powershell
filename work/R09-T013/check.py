#!/usr/bin/env python3
"""R09-T013 check: leap mutation-driven regression.

Builds a one-token mutant of the reference in a temporary copy only, runs the
original and the mutant against the same Pester suite and the same year
inputs, and exits non-zero if any assertion fails.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REL = "exercises/practice/leap"
EX = ROOT / REL
DESCRIBE = "LeapYear Tests"
NAMED_FAIL = "year divisible by 2, not divisible by 4 in common year"
NAMED_PASS = "year not divisible by 4 in common year"
UUID = "ac227e82-ee82-4a09-9eb6-4f84331ffdb0"
KNOWN = {"year divisible by 400 is leap year": "year divisible by 400 in leap year"}
OLD = "$year % 4 -eq 0"
NEW = "$year % 2 -eq 0"
HINT_YEARS = {2: "False", 1970: "False", 1972: "True"}
PS = (
    '$r = Invoke-Pester -PassThru; '
    '"RESULT_JSON:" + ([pscustomobject]@{Result="$($r.Result)"; Total=$r.TotalCount; '
    'Passed=$r.PassedCount; Failed=$r.FailedCount; FailedContainers=$r.FailedContainersCount; '
    'PesterVersion="$($r.Version)"; PSVersion="$($r.PSVersion)"; '
    'Tests=@($r.Tests | ForEach-Object { [pscustomobject]@{Name=$_.Name; Result="$($_.Result)"} })} '
    '| ConvertTo-Json -Depth 4 -Compress)'
)
YEARS_PS = '. ./LeapYear.ps1; 1..2400 | ForEach-Object { "{0}:{1}" -f $_, (Test-LeapYear $_) }'
failures = []
ev = {}


def check(cond, msg):
    print(("PASS: " if cond else "FAIL: ") + msg)
    if not cond:
        failures.append(msg)
    return cond


def run_pester(folder):
    p = subprocess.run(["pwsh", "-NoProfile", "-Command", PS],
                       cwd=folder, capture_output=True, text=True)
    marked = [l for l in p.stdout.splitlines() if l.startswith("RESULT_JSON:")]
    data = json.loads(marked[-1][len("RESULT_JSON:"):]) if marked else None
    return p.returncode, data, p.stderr


def year_results(folder):
    p = subprocess.run(["pwsh", "-NoProfile", "-Command", YEARS_PS],
                       cwd=folder, capture_output=True, text=True)
    out = {}
    for line in p.stdout.splitlines():
        m = re.fullmatch(r"(\d+):(True|False)", line.strip())
        if m:
            out[int(m.group(1))] = m.group(2)
    return p.returncode, out


def make_copy(parent, use_reference, sol, exm):
    dst = Path(parent) / "leap"
    shutil.copytree(EX, dst)  # copies dotfiles too
    if use_reference:
        for s, e in zip(sol, exm):
            shutil.copyfile(dst / e, dst / s)  # substitution only in the copy
    return dst


def tool_version(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True)
        return (p.stdout or p.stderr).strip()
    except FileNotFoundError:
        return "not found"


def git_state():
    p = subprocess.run(["git", "status", "--porcelain", "--", REL],
                       cwd=ROOT, capture_output=True, text=True)
    return p.stdout


def finish():
    (HERE / "results.json").write_text(json.dumps(ev, indent=2))
    if failures:
        print(f"\n{len(failures)} check(s) FAILED")
        sys.exit(1)
    print("\nAll checks passed")
    sys.exit(0)


def main():
    cfg = json.loads((EX / ".meta/config.json").read_text())
    sol, tst, exm = cfg["files"]["solution"], cfg["files"]["test"], cfg["files"]["example"]
    (HERE / "inputs.json").write_text(json.dumps(
        {"config_files": cfg["files"], "mutation": {"old": OLD, "new": NEW},
         "rejecting_test": {"uuid": UUID, "name": NAMED_FAIL}, "years_compared": "1..2400",
         "pester_command": "Invoke-Pester -PassThru"}, indent=2))
    (HERE / "versions.txt").write_text(
        f"python: {sys.version.split()[0]}\n"
        f"pwsh: {tool_version(['pwsh', '--version'])}\n"
        f"git: {tool_version(['git', '--version'])}\n")
    if not check(len(sol) == len(exm) == len(tst) == 1 and all((EX / f).is_file() for f in sol + tst + exm),
                 f"config.json files exist (solution={sol}, test={tst}, example={exm})"):
        return finish()
    state_before = git_state()

    toml = tomllib.loads((EX / ".meta/tests.toml").read_text())
    included = [v["description"] for v in toml.values() if v.get("include", True) is not False]
    text = (EX / tst[0]).read_text()
    it_names = re.findall(r'^\s*It\s+"([^"]+)"', text, re.M)
    print(f"tests.toml: {len(included)} included; test file: {len(it_names)} It blocks")
    expected = [KNOWN.get(n, n) for n in included]
    for t, i in KNOWN.items():
        print(f"NOTE: known wording difference: tests.toml has '{t}', test file has '{i}'")
    check(set(expected) == set(it_names) and len(it_names) == len(included),
          "tests.toml cases match the It blocks one to one (allowing the documented wording difference)")
    check(f'Describe "{DESCRIBE}"' in text, f'test file has Describe "{DESCRIBE}"')
    check(toml.get(UUID, {}).get("description") == NAMED_FAIL, f"{UUID} is '{NAMED_FAIL}' in tests.toml")
    check(NAMED_PASS in included, f"named case '{NAMED_PASS}' is in tests.toml")

    hints = EX / ".docs/hints.md"
    htext = hints.read_text() if hints.is_file() else ""
    check(hints.is_file() and "1970" in htext, "hints.md exists and gives the 1970 diagnostic input")
    check("%" not in htext and "$year" not in htext and "-and" not in htext,
          "hints.md does not publish the reference condition")
    doc = ROOT / "docs/maintenance/leap.md"
    dtext = doc.read_text() if doc.is_file() else ""
    check(UUID in dtext and NAMED_FAIL in dtext and "% 2" in dtext,
          "docs/maintenance/leap.md records the mutant, test name and UUID")

    ref_text = (EX / exm[0]).read_text()
    check(ref_text.count(OLD) == 1, "reference contains the mutation target exactly once")
    mut_text = ref_text.replace(OLD, NEW)
    squash = lambda s: re.sub(r"\s+", "", s)
    check(squash(mut_text) != squash(ref_text), "mutation changes behavior, not only formatting")

    with tempfile.TemporaryDirectory() as tmp:
        o = make_copy(Path(tmp) / "orig", True, sol, exm)
        m = make_copy(Path(tmp) / "mut", True, sol, exm)
        (m / sol[0]).write_text(mut_text)
        s = make_copy(Path(tmp) / "stub", False, sol, exm)
        rc_o, orig, err_o = run_pester(o)
        rc_m, mut, err_m = run_pester(m)
        rc_s, stub, _ = run_pester(s)
        yrc_o, years_o = year_results(o)
        yrc_m, years_m = year_results(m)

    check(rc_o == 0, f"original: pwsh exit code 0 (got {rc_o})")
    if check(orig is not None, "original: Pester result parsed"):
        print(f"Executed cases: {orig['Total']}  Passed: {orig['Passed']}  Failed: {orig['Failed']}")
        check(orig["Total"] > 0, "original: at least one test executed")
        check(orig["Failed"] == 0 and orig["Result"] == "Passed", "original: no failed tests")
        r_o = {t["Name"]: t["Result"] for t in orig["Tests"]}
        check(set(r_o) == set(expected) and orig["Total"] == len(included),
              "original: executed tests match the included cases")
        check(r_o.get(NAMED_FAIL) == "Passed" and r_o.get(NAMED_PASS) == "Passed",
              "original: both named cases pass")
        ev["executed_cases"] = orig["Total"]
        ev["tool_versions"] = {"pester": orig["PesterVersion"], "powershell": orig["PSVersion"]}
    else:
        print(err_o)

    check(rc_m == 0, f"mutant: pwsh exit code 0 (got {rc_m})")
    if check(mut is not None, "mutant: Pester result parsed"):
        r_m = {t["Name"]: t["Result"] for t in mut["Tests"]}
        failed = sorted(n for n, r in r_m.items() if r != "Passed")
        print(f"Mutant: executed {mut['Total']}, passed {mut['Passed']}, failed {mut['Failed']}")
        check(mut["Total"] > 0, "mutant: at least one test executed")
        check(failed == [NAMED_FAIL], f"mutant fails exactly the named assertion (failed: {failed})")
        check(r_m.get(NAMED_PASS) == "Passed", f"mutant still passes '{NAMED_PASS}' (it does not distinguish this mutant)")
        if orig is not None:
            ev["expected_vs_actual"] = [
                {"test": t["Name"], "original": t["Result"], "mutant": r_m.get(t["Name"], "missing")}
                for t in orig["Tests"]]
    else:
        print(err_m)

    check(yrc_o == 0 and yrc_m == 0 and len(years_o) == 2400 and len(years_m) == 2400,
          "year comparison ran for 2400 inputs on both versions")
    diffs = sorted(y for y in years_o if years_o.get(y) != years_m.get(y))
    smallest = diffs[0] if diffs else None
    print(f"Years where original and mutant differ: {len(diffs)}; smallest: {smallest}")
    check(smallest == 2, "smallest differing year is 2 (original False, mutant True)")
    check(1970 in diffs and 2015 not in diffs, "1970 distinguishes the mutant, 2015 does not")
    check(all(years_o.get(y) == exp for y, exp in HINT_YEARS.items()), "hint table matches the original's results")
    ev["smallest_differing_year"] = smallest
    ev["differing_years"] = len(diffs)

    check(rc_s == 0 and stub is not None, "stub run: completed and parsed")
    if stub:
        check(stub["Failed"] > 0 or stub["FailedContainers"] > 0 or stub["Result"] == "Failed",
              "learner stub still fails the tests (unsolved)")
        ev["learner_stub"] = {k: stub[k] for k in ("Result", "Total", "Passed", "Failed")}
    d = subprocess.run(["git", "diff", "--quiet", "HEAD", "--"] + [f"{REL}/{x}" for x in sol], cwd=ROOT)
    check(d.returncode == 0, "learner stub file unchanged in the repo")
    check(git_state() == state_before, "files under the exercise were not changed by this check")
    finish()


main()
