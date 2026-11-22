#!/usr/bin/env python3
"""R09-T016: reference word-count (regex + hashtable) vs an independent character
scanner (work/R09-T016/alt/WordCountAlt.ps1), in temporary copies. Non-zero exit on failure."""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REL = "exercises/practice/word-count"
EX = ROOT / REL
ALT = HERE / "alt" / "WordCountAlt.ps1"
NAMED = ["count one word", "count one of each word"]
SPEC = "\"That's the password: 'PASSWORD 123'!\", cried the Special Agent.\nSo I fled."
AGREE = [
    ["worked example", "Go go, can't stop", {"go": 2, "can't": 1, "stop": 1}],
    ["cramped list", "one,two,three", {"one": 1, "two": 1, "three": 1}],
    ["apostrophes", "can, can't, 'can't'", {"can": 1, "can't": 2}],
    ["empty", "", {}],
]
DIFFER = [
    ["spec example", SPEC, {"123": 1, "agent": 1, "cried": 1, "fled": 1, "i": 1,
                            "password": 2, "so": 1, "special": 1, "that's": 1, "the": 2}],
    ["number 100", "It costs 100 dollars.", {"it": 1, "costs": 1, "100": 1, "dollars": 1}],
]
failures, ev = [], {}
PS = ('$r = Invoke-Pester -PassThru; "RESULT_JSON:" + ([pscustomobject]@{Result="$($r.Result)"; '
      'Total=$r.TotalCount; Passed=$r.PassedCount; Failed=$r.FailedCount; '
      'FailedContainers=$r.FailedContainersCount; PesterVersion="$($r.Version)"; '
      'PSVersion="$($r.PSVersion)"; Tests=@($r.Tests | ForEach-Object '
      '{ [pscustomobject]@{Name=$_.Name; Result="$($_.Result)"} })} | ConvertTo-Json -Depth 4 -Compress)')
PS_CASES = (". ./WordCount.ps1; $cases = Get-Content -Raw $env:CASES_PATH | ConvertFrom-Json; "
            "foreach ($c in $cases) { $r = Get-WordCount -Phrase $c.input; "
            "'OUT:' + ([pscustomobject]@{name = $c.name; result = $r} | ConvertTo-Json -Compress -Depth 4) }")


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
            out[d["name"]] = d["result"]
    return p.returncode, out


def make_copy(parent, kind, sol, exm):
    dst = Path(parent) / "word-count"
    shutil.copytree(EX, dst)  # copies dotfiles too
    if kind == "ref":
        shutil.copyfile(dst / exm[0], dst / sol[0])  # substitution only in the copy
    elif kind == "alt":
        shutil.copyfile(ALT, dst / sol[0])
    return dst


def finish():
    (HERE / "results.json").write_text(json.dumps(ev, indent=2))
    print(f"\n{len(failures)} check(s) FAILED" if failures else "\nAll checks passed")
    sys.exit(1 if failures else 0)


def main():
    cfg = json.loads((EX / ".meta/config.json").read_text())
    sol, tst, exm = (cfg["files"][k] for k in ("solution", "test", "example"))
    cases = HERE / "cases.json"
    cases.write_text(json.dumps([{"name": n, "input": i} for n, i, _ in AGREE + DIFFER], indent=2))
    (HERE / "inputs.json").write_text(json.dumps({"config_files": cfg["files"], "named_cases": NAMED,
        "alternative": "alt/WordCountAlt.ps1", "direct_cases_file": "cases.json"}, indent=2))
    pv = subprocess.run(["pwsh", "--version"], capture_output=True, text=True).stdout.strip()
    (HERE / "versions.txt").write_text(f"python: {sys.version.split()[0]}\npwsh: {pv}\n"
                                       f"git: {git('--version').stdout.strip()}\n")
    ok = all((EX / f).is_file() for f in sol + tst + exm) and ALT.is_file()
    if not check(ok, "config.json files and the alternative exist"):
        return finish()
    before = git("status", "--porcelain", "--", REL).stdout
    names = re.findall(r'^\s*It\s+"([^"]+)"', (EX / tst[0]).read_text(), re.M)
    check(all(n in names for n in NAMED), f"named cases are in the test file ({len(names)} It blocks)")
    ref, alt = (EX / exm[0]).read_text(), ALT.read_text()
    check("[regex]::Matches" in ref, "reference uses a regular expression")
    check(not re.search(r"regex|-match|Matches\(", alt, re.I) and "Group-Object" in alt,
          "alternative uses no regular expression: character scan, list, Group-Object")
    with tempfile.TemporaryDirectory() as tmp:
        dirs = {k: make_copy(Path(tmp) / k, k, sol, exm) for k in ("ref", "alt", "stub")}
        runs = {k: run_pester(d) for k, d in dirs.items()}
        direct = {k: run_cases(dirs[k], cases) for k in ("ref", "alt")}
    res = {}
    for k, label in (("ref", "reference"), ("alt", "alternative")):
        rc, p = runs[k]
        check(rc == 0, f"{label}: pwsh exit code 0 (got {rc})")
        if not check(p is not None, f"{label}: Pester result parsed"):
            continue
        print(f"{label}: executed {p['Total']}, passed {p['Passed']}, failed {p['Failed']}")
        check(p["Total"] > 0 and p["Total"] == len(names), f"{label}: executed count equals the It blocks")
        check(p["Failed"] == 0 and p["Result"] == "Passed", f"{label}: no failed tests")
        res[k] = {t["Name"]: t["Result"] for t in p["Tests"]}
        for nm in NAMED:
            check(res[k].get(nm) == "Passed", f"{label}: named case '{nm}' passed")
    if len(res) == 2:
        check(res["ref"] == res["alt"], "reference and alternative give the same per-test results")
        p = runs["ref"][1]
        print(f"Executed cases: {p['Total']}")
        ev.update(executed_cases=p["Total"], tool_versions={"pester": p["PesterVersion"], "powershell": p["PSVersion"]},
                  expected_vs_actual=[{"test": n, "reference": res["ref"].get(n), "alternative": res["alt"].get(n)} for n in names])
    (rc_r, dr), (rc_a, da) = direct["ref"], direct["alt"]
    check(rc_r == 0 and rc_a == 0 and len(dr) == len(da) == len(AGREE) + len(DIFFER),
          "direct runs gave a result for every input on both versions")
    for n, _, want in AGREE:
        check(dr.get(n) == want == da.get(n), f"both versions give the expected result for '{n}'")
    for n, _, want in DIFFER:
        a, b = dr.get(n), da.get(n)
        check(b == want, f"alternative matches the instructions for '{n}'")
        check(a != b, f"reference differs from the instructions for '{n}' (multi-digit number)")
        ev.setdefault("differences", []).append({"case": n, "instructions": want, "reference": a, "alternative": b})
        print(f"  {n}: reference {a} | alternative {b}")
    hint = EX / ".docs/hints.md"
    ht = hint.read_text() if hint.is_file() else ""
    check(all(s in ht for s in ("Go go, can't stop", "100", "Group-Object", "hashtable")),
          "hints.md has both approaches, the worked example and the multi-digit check")
    check(not any(s in ht for s in ("Function Get-WordCount", "[regex]::Matches", "Substring", "param(")),
          "hints.md does not print a solution")
    new = set(git("diff", "--name-only", "main", "--", REL).stdout.split()) | \
        set(git("ls-files", "--others", "--exclude-standard", "--", REL).stdout.split())
    check(new == {f"{REL}/.docs/hints.md"}, f"only hints.md is added or changed under the exercise ({sorted(new)})")
    rc_s, ps = runs["stub"]
    check(rc_s == 0 and ps is not None, "stub run: completed and parsed")
    if ps:
        check(ps["Failed"] > 0 or ps["FailedContainers"] > 0 or ps["Result"] == "Failed",
              "learner stub still fails the tests (unsolved)")
        ev["learner_stub"] = {k: ps[k] for k in ("Result", "Total", "Passed", "Failed")}
    check(git("diff", "--quiet", "main", "--", *[f"{REL}/{x}" for x in sol]).returncode == 0, "learner stub file unchanged")
    check(git("status", "--porcelain", "--", REL).stdout == before, "the check did not change files under the exercise")
    finish()


main()
