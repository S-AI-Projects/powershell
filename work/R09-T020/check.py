#!/usr/bin/env python3
"""R09-T020: roman-numerals hint check. Reads the decision tables from hints.md, runs the same
inputs against the reference in a temporary copy, and compares. Non-zero exit on any failure."""
import json, os, re, shutil, subprocess, sys, tempfile, tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REL = "exercises/practice/roman-numerals"
EX = ROOT / REL
MSG = "Number has to be positive integer in range of 1-3999."
failures, ev = [], {}
PS = ('$r = Invoke-Pester -PassThru; "RESULT_JSON:" + ([pscustomobject]@{Result="$($r.Result)"; '
      'Total=$r.TotalCount; Passed=$r.PassedCount; Failed=$r.FailedCount; '
      'FailedContainers=$r.FailedContainersCount; PesterVersion="$($r.Version)"; '
      'PSVersion="$($r.PSVersion)"; Tests=@($r.Tests | ForEach-Object '
      '{ [pscustomobject]@{Name=$_.Name; Expanded="$($_.ExpandedName)"; Result="$($_.Result)"} })} '
      '| ConvertTo-Json -Depth 4 -Compress)')
PS_CASES = (". ./RomanNumerals.ps1; $cases = Get-Content -Raw $env:CASES_PATH | ConvertFrom-Json; "
            "foreach ($c in $cases) { try { $v = Get-RomanNumerals -Number $c; "
            "$o = [pscustomobject]@{n=$c; ok=$true; value=[string]$v} } catch { "
            "$o = [pscustomobject]@{n=$c; ok=$false; value=$_.Exception.Message} }; "
            "'OUT:' + ($o | ConvertTo-Json -Compress) }")
T1 = re.compile(r"^\|\s*`(-?\d+)`\s*\|\s*`([A-Z]+)`\s*\|\s*$", re.M)
T2 = re.compile(r"^\|\s*`(-?\d+)`\s*\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|\s*$", re.M)
ROWS = re.compile(r'@\{\s*Number\s*=\s*(\d+);\s*Result\s*=\s*"([A-Z]+)"\s*\}')
INV = re.compile(r'It "([^"]+)"\s*\{\s*\{\s*Get-RomanNumerals -Number\s+(-?\d+)\s*\}')


def check(cond, msg):
    print(("PASS: " if cond else "FAIL: ") + msg)
    if not cond:
        failures.append(msg)
    return cond


def pwsh(script, folder, env=None):
    return subprocess.run(["pwsh", "-NoProfile", "-Command", script], cwd=folder,
                          capture_output=True, text=True, env=env)


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def run_pester(folder):
    p = pwsh(PS, folder)
    lines = [l for l in p.stdout.splitlines() if l.startswith("RESULT_JSON:")]
    return p.returncode, (json.loads(lines[-1][12:]) if lines else None)


def run_cases(folder, path):
    p = pwsh(PS_CASES, folder, dict(os.environ, CASES_PATH=str(path)))
    out = {}
    for line in p.stdout.splitlines():
        if line.startswith("OUT:"):
            d = json.loads(line[4:])
            out[d["n"]] = d
    return p.returncode, out


def make_copy(parent, use_reference, sol, exm):
    dst = Path(parent) / "roman-numerals"
    shutil.copytree(EX, dst)  # copies dotfiles too
    if use_reference:
        shutil.copyfile(dst / exm[0], dst / sol[0])  # substitution only in the copy
    return dst


def finish():
    (HERE / "results.json").write_text(json.dumps(ev, indent=2))
    print(f"\n{len(failures)} check(s) FAILED" if failures else "\nAll checks passed")
    sys.exit(1 if failures else 0)


def main():
    cfg = json.loads((EX / ".meta/config.json").read_text())["files"]
    sol, tst, exm = cfg["solution"], cfg["test"], cfg["example"]
    hint = EX / ".docs/hints.md"
    pv = subprocess.run(["pwsh", "--version"], capture_output=True, text=True).stdout.strip()
    (HERE / "versions.txt").write_text(f"python: {sys.version.split()[0]}\npwsh: {pv}\n"
                                       f"git: {git('--version').stdout.strip()}\n")
    ok = hint.is_file() and all((EX / f).is_file() for f in sol + tst + exm)
    if not check(ok, "config.json files and hints.md exist"):
        return finish()
    before = git("status", "--porcelain", "--", REL).stdout
    text, ht = (EX / tst[0]).read_text(), hint.read_text()
    rows = [(int(n), r) for n, r in ROWS.findall(text)]
    inv = [(name, int(n)) for name, n in INV.findall(text)]
    t1 = [(int(n), r) for n, r in T1.findall(ht)]
    t2 = [(int(n), name, res) for n, name, res in T2.findall(ht)]
    toml = tomllib.loads((EX / ".meta/tests.toml").read_text())
    desc = [v["description"] for v in toml.values() if v.get("include", True) is not False]
    pairs = sorted((int(m.group(1)), m.group(2)) for d in desc if (m := re.fullmatch(r"(\d+) is ([A-Z]+)", d)))
    print(f"tests.toml: {len(toml)} entries, {len(desc)} included; test file: {len(rows)} numbers, {len(inv)} invalid-input tests")
    check(len(pairs) == len(desc) == len(rows) and pairs == sorted(rows), "tests.toml cases match the test rows one to one (no case dropped)")
    check([n for _, n in inv] == [0, -12, 9999], f"the invalid-input tests use 0, -12 and 9999 ({inv})")
    check(len(t1) >= 4 and all(p in rows for p in t1), f"every number in the hint's first table is a test input with the same result ({t1})")
    check(sorted(t2) == sorted((n, nm, "an error") for nm, n in inv), f"the hint's second table lists exactly the invalid-input tests ({t2})")
    check("*" + MSG + "*" in ht and text.count("*" + MSG + "*") == 3, "the hint quotes the message pattern that all 3 invalid-input tests use")
    check("Should -BeExactly $Result" in text, "the tests compare numerals with -BeExactly, as the hint says")
    check("### Not specified" in ht and "3,999" in ht, "the hint has a 'Not specified' section and states the 3,999 limit")
    check('Describe "Roman Numerals Test Cases"' in text, 'test file has Describe "Roman Numerals Test Cases"')
    cases = [n for n, _ in rows] + [n for _, n in inv]
    cases_file = HERE / "cases.json"
    cases_file.write_text(json.dumps(cases))
    (HERE / "inputs.json").write_text(json.dumps({"config_files": cfg, "hint_table_1": t1, "hint_table_2": t2,
        "direct_inputs_file": "cases.json", "pester_command": "Invoke-Pester -PassThru"}, indent=2))
    with tempfile.TemporaryDirectory() as tmp:
        ref = make_copy(Path(tmp) / "r", True, sol, exm)
        stub = make_copy(Path(tmp) / "s", False, sol, exm)
        rc, p = run_pester(ref)
        rc_s, ps = run_pester(stub)
        crc, direct = run_cases(ref, cases_file)
    check(rc == 0, f"reference: pwsh exit code 0 (got {rc})")
    expected = len(rows) + len(inv)
    if check(p is not None, "reference: Pester result parsed"):
        print(f"Executed cases: {p['Total']}  Passed: {p['Passed']}  Failed: {p['Failed']}")
        check(p["Total"] > 0 and p["Total"] == expected, f"executed count equals {len(rows)} numbers + {len(inv)} invalid-input tests")
        check(p["Failed"] == 0 and p["Result"] == "Passed" and p["Passed"] == p["Total"], "reference: no failed tests")
        res = [(t["Name"], t["Result"]) for t in p["Tests"]]
        gi = [r for n, r in res if n == "Given <Number> it outputs <Result>"]
        check(len(gi) == len(rows) and all(r == "Passed" for r in gi), f"'Given <Number> it outputs <Result>' ran {len(gi)} times, all passed")
        check(dict(res).get("Number is zero") == "Passed", "named case 'Number is zero' passed")
        ev.update(executed_cases=p["Total"], tool_versions={"pester": p["PesterVersion"], "powershell": p["PSVersion"]},
                  expected_vs_actual=[{"test": t["Expanded"] or t["Name"], "expected": "Passed", "actual": t["Result"]} for t in p["Tests"]])
    check(crc == 0 and len(direct) == len(cases), f"direct runs gave a result for all {len(cases)} inputs")
    bad = [n for n, w in rows if not (direct.get(n, {}).get("ok") and direct[n]["value"] == w)]
    check(not bad, f"the reference returns the expected numeral for all {len(rows)} numbers in the tests (mismatches: {bad})")
    for name, n in inv:
        d = direct.get(n, {})
        check(d.get("ok") is False and MSG in d.get("value", ""), f"'{name}': input {n} throws with the required message")
    ev["direct_results"] = {str(k): v for k, v in direct.items()}
    check(rc_s == 0 and ps is not None, "stub run: completed and parsed")
    if ps:
        check(ps["Failed"] > 0 or ps["FailedContainers"] > 0 or ps["Result"] == "Failed", "learner stub still fails the tests (unsolved)")
        ev["learner_stub"] = {k: ps[k] for k in ("Result", "Total", "Passed", "Failed")}
    new = set(git("diff", "--name-only", "main", "--", REL).stdout.split()) | \
        set(git("ls-files", "--others", "--exclude-standard", "--", REL).stdout.split())
    check(new == {f"{REL}/.docs/hints.md"}, f"only hints.md is added or changed under the exercise ({sorted(new)})")
    check(git("diff", "--quiet", "main", "--", *[f"{REL}/{x}" for x in sol]).returncode == 0, "learner stub file unchanged")
    check(git("status", "--porcelain", "--", REL).stdout == before, "the check did not change files under the exercise")
    finish()


main()
