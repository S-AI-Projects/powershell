#!/usr/bin/env python3
"""R09-T014: compare the baseline tournament reference (git ref main) with the
refactored one in temporary copies. Exits non-zero on any failed assertion."""
import json, os, re, shutil, subprocess, sys, tempfile, tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REL = "exercises/practice/tournament"
EX = ROOT / REL
BASE = "main"
NAMED = ["just the header if no input", "a win is three points, a loss is zero points"]
A, B, C, D = "Allegoric Alaskans", "Blithering Badgers", "Courageous Californians", "Devastating Donkeys"
CASES = [
    {"name": "empty", "input": []},
    {"name": "win", "input": [f"{A};{B};win"]},
    {"name": "loss", "input": [f"{B};{A};loss"]},
    {"name": "draw", "input": [f"{A};{B};draw"]},
    {"name": "typical", "input": [f"{A};{B};win", f"{D};{C};draw", f"{D};{A};win",
                                  f"{C};{B};loss", f"{B};{D};loss", f"{A};{C};win"]},
    {"name": "ties", "input": [f"{C};{D};win", f"{A};{B};win", f"{D};{A};loss",
                               f"{C};{B};win", f"{B};{D};draw", f"{A};{C};draw"]},
    {"name": "numeric sort", "input": ["Team A;Team B;win"] * 4 + ["Team C;Team D;draw"] * 10
                                      + ["Team E;Team F;win"] * 3},
]
PS = ('$r = Invoke-Pester -PassThru; "RESULT_JSON:" + ([pscustomobject]@{Result="$($r.Result)"; '
      'Total=$r.TotalCount; Passed=$r.PassedCount; Failed=$r.FailedCount; '
      'FailedContainers=$r.FailedContainersCount; PesterVersion="$($r.Version)"; '
      'PSVersion="$($r.PSVersion)"; Tests=@($r.Tests | ForEach-Object '
      '{ [pscustomobject]@{Name=$_.Name; Result="$($_.Result)"} })} | ConvertTo-Json -Depth 4 -Compress)')
PS_CASES = (". ./Tournament.ps1; $cases = Get-Content -Raw $env:CASES_PATH | ConvertFrom-Json; "
            "foreach ($c in $cases) { $r = Invoke-Tournament -Results @($c.input); "
            "'OUT:' + ([pscustomobject]@{name = $c.name; output = [string]$r} | ConvertTo-Json -Compress) }")
failures, ev = [], {}


def check(cond, msg):
    print(("PASS: " if cond else "FAIL: ") + msg)
    if not cond:
        failures.append(msg)
    return cond


def pwsh(script, folder, env=None):
    return subprocess.run(["pwsh", "-NoProfile", "-Command", script], cwd=folder,
                          capture_output=True, text=True, env=env)


def run_pester(folder):
    p = pwsh(PS, folder)
    lines = [l for l in p.stdout.splitlines() if l.startswith("RESULT_JSON:")]
    return p.returncode, (json.loads(lines[-1][12:]) if lines else None), p.stderr


def run_cases(folder, cases_file):
    p = pwsh(PS_CASES, folder, dict(os.environ, CASES_PATH=str(cases_file)))
    out = {}
    for line in p.stdout.splitlines():
        if line.startswith("OUT:"):
            d = json.loads(line[4:])
            out[d["name"]] = d["output"]
    return p.returncode, out


def make_copy(parent, kind, sol, exm, orig_text=None):
    dst = Path(parent) / "tournament"
    shutil.copytree(EX, dst)  # copies dotfiles too
    if kind == "new":
        shutil.copyfile(dst / exm[0], dst / sol[0])  # substitution only in the copy
    elif kind == "orig":
        (dst / sol[0]).write_text(orig_text)
    return dst


def rows(output):
    res = []
    for line in output.split("\n")[1:]:
        parts = [x.strip() for x in line.split("|")]
        if len(parts) == 6 and all(x.isdigit() for x in parts[1:]):
            res.append([int(x) for x in parts[1:]])
    return res


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def finish():
    (HERE / "results.json").write_text(json.dumps(ev, indent=2))
    print(f"\n{len(failures)} check(s) FAILED" if failures else "\nAll checks passed")
    sys.exit(1 if failures else 0)


def main():
    cfg = json.loads((EX / ".meta/config.json").read_text())
    sol, tst, exm = (cfg["files"][k] for k in ("solution", "test", "example"))
    cases_file = HERE / "cases.json"
    cases_file.write_text(json.dumps(CASES, indent=2))
    (HERE / "inputs.json").write_text(json.dumps(
        {"config_files": cfg["files"], "baseline_ref": BASE, "case_inputs_file": "cases.json",
         "named_cases": NAMED, "pester_command": "Invoke-Pester -PassThru"}, indent=2))
    pv = subprocess.run(["pwsh", "--version"], capture_output=True, text=True).stdout.strip()
    (HERE / "versions.txt").write_text(f"python: {sys.version.split()[0]}\npwsh: {pv}\n"
                                       f"git: {git('--version').stdout.strip()}\n")
    if not check(all((EX / f).is_file() for f in sol + tst + exm), f"config.json files exist ({sol}, {tst}, {exm})"):
        return finish()
    before = git("status", "--porcelain", "--", REL).stdout
    g = git("show", f"{BASE}:{REL}/{exm[0]}")
    if not check(g.returncode == 0, f"baseline reference available from git ref {BASE}"):
        return finish()
    old, new = g.stdout, (EX / exm[0]).read_text()
    check(new != old, "the reference differs from the baseline")
    changed = git("diff", "--name-only", BASE, "--", REL).stdout.split()
    check(changed == [f"{REL}/{exm[0]}"], f"only the reference file changed ({changed})")
    c1, c2 = "Function LineProcessing", "Function DrawTable"
    check(old[:old.index(c1)] == new[:new.index(c1)], "Invoke-Tournament (parameters and return) is unchanged")
    check(old[old.index(c2):] == new[new.index(c2):], "DrawTable is unchanged")
    fns = lambda t: re.findall(r"^Function\s+([\w-]+)", t, re.M | re.I)
    check(fns(old) == fns(new), f"same functions, no new API ({fns(new)})")
    lp_old, lp_new = old[old.index(c1):old.index(c2)], new[new.index(c1):new.index(c2)]
    idx = re.compile(r"\]\[-?\d+\]")
    check(idx.search(lp_old) and not idx.search(lp_new),
          f"bare numeric indexes replaced by names ({len(idx.findall(lp_old))} before, {len(idx.findall(lp_new))} after)")
    check("$played, $wins, $draws, $losses, $points = 0..4" in lp_new and "Invariants" in lp_new,
          "named positions and the invariant comment are present")
    toml = tomllib.loads((EX / ".meta/tests.toml").read_text())
    included = [v["description"] for v in toml.values() if v.get("include", True) is not False]
    text = (EX / tst[0]).read_text()
    names = re.findall(r'^\s*It\s+"([^"]+)"', text, re.M)
    print(f"tests.toml: {len(included)} included; test file: {len(names)} It blocks")
    check(len(included) == len(names), "tests.toml included count equals the It block count")
    check('Describe "Tournament test cases"' in text and all(n in names for n in NAMED), "named cases are in the test file")
    with tempfile.TemporaryDirectory() as tmp:
        o = make_copy(Path(tmp) / "o", "orig", sol, exm, old)
        n = make_copy(Path(tmp) / "n", "new", sol, exm)
        s = make_copy(Path(tmp) / "s", "stub", sol, exm)
        (rc_o, po, _), (rc_n, pn, err_n), (rc_s, ps, _) = run_pester(o), run_pester(n), run_pester(s)
        orc, out_o = run_cases(o, cases_file)
        nrc, out_n = run_cases(n, cases_file)
    for label, rc, p in (("before", rc_o, po), ("after", rc_n, pn)):
        check(rc == 0, f"{label}: pwsh exit code 0 (got {rc})")
        if not check(p is not None, f"{label}: Pester result parsed"):
            continue
        print(f"{label}: executed {p['Total']}, passed {p['Passed']}, failed {p['Failed']}")
        check(p["Total"] > 0 and p["Total"] == len(included), f"{label}: executed count matches the included cases")
        check(p["Failed"] == 0 and p["Result"] == "Passed", f"{label}: no failed tests")
        res = {t["Name"]: t["Result"] for t in p["Tests"]}
        for nm in NAMED:
            check(res.get(nm) == "Passed", f"{label}: named case '{nm}' passed")
    if po and pn:
        pairs = lambda p: [(t["Name"], t["Result"]) for t in p["Tests"]]
        check(pairs(po) == pairs(pn), "before and after give the same per-test results")
        print(f"Executed cases: {pn['Total']}")
        ev.update(executed_cases=pn["Total"], tool_versions={"pester": pn["PesterVersion"], "powershell": pn["PSVersion"]},
                  expected_vs_actual=[{"test": a, "before": b, "after": dict(pairs(pn))[a]} for a, b in pairs(po)])
    check(orc == 0 and nrc == 0 and len(out_o) == len(CASES) == len(out_n), "direct runs gave an output for every input")
    same = sum(1 for c in CASES if out_o.get(c["name"]) is not None and out_o.get(c["name"]) == out_n.get(c["name"]))
    print(f"Direct outputs compared: {same} of {len(CASES)} identical")
    check(same == len(CASES), "before and after outputs are identical for all inputs")
    allrows = [r for c in CASES for r in rows(out_n.get(c["name"], ""))]
    check(allrows and all(mp == w + d + l and p == 3 * w + d for mp, w, d, l, p in allrows),
          f"invariants MP = W + D + L and P = 3W + D hold in all {len(allrows)} output rows")
    ev.update(direct_outputs_identical=same, outputs_after=out_n)
    check(rc_s == 0 and ps is not None, "stub run: completed and parsed")
    if ps:
        check(ps["Failed"] > 0 or ps["FailedContainers"] > 0 or ps["Result"] == "Failed", "learner stub still fails the tests (unsolved)")
        ev["learner_stub"] = {k: ps[k] for k in ("Result", "Total", "Passed", "Failed")}
    check(git("diff", "--quiet", BASE, "--", *[f"{REL}/{x}" for x in sol]).returncode == 0, "learner stub file unchanged")
    check(git("status", "--porcelain", "--", REL).stdout == before, "the check did not change files under the exercise")
    finish()


main()
