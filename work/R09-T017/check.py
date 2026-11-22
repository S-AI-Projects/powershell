#!/usr/bin/env python3
"""R09-T017: diamond hint check. Runs both micro-examples from hints.md and compares
their output with the published text, then runs the tests against the reference.
Non-zero exit on any failed assertion."""
import json, re, shutil, subprocess, sys, tempfile, tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REL = "exercises/practice/diamond"
EX = ROOT / REL
FENCE = chr(96) * 3
NAMED = ["single 'A' row", "no row containing 3 distinct groups of spaces"]
PS = ('$r = Invoke-Pester -PassThru; "RESULT_JSON:" + ([pscustomobject]@{Result="$($r.Result)"; '
      'Total=$r.TotalCount; Passed=$r.PassedCount; Failed=$r.FailedCount; '
      'FailedContainers=$r.FailedContainersCount; PesterVersion="$($r.Version)"; '
      'PSVersion="$($r.PSVersion)"; Tests=@($r.Tests | ForEach-Object '
      '{ [pscustomobject]@{Name=$_.Name; Result="$($_.Result)"} })} | ConvertTo-Json -Depth 4 -Compress)')
EARLY = ('$L = [char]"A"; $r = [char]"A"..[char]$L + [char]($L-1)..[char]"A" | ForEach-Object { "$_" }; '
         '(@($r) -join ",")')
failures, ev = [], {}


def check(cond, msg):
    print(("PASS: " if cond else "FAIL: ") + msg)
    if not cond:
        failures.append(msg)
    return cond


def pwsh(script, folder):
    return subprocess.run(["pwsh", "-NoProfile", "-Command", script], cwd=folder,
                          capture_output=True, text=True)


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def run_pester(folder):
    p = pwsh(PS, folder)
    lines = [l for l in p.stdout.splitlines() if l.startswith("RESULT_JSON:")]
    return p.returncode, (json.loads(lines[-1][12:]) if lines else None)


def make_copy(parent, use_reference, sol, exm):
    dst = Path(parent) / "diamond"
    shutil.copytree(EX, dst)  # copies dotfiles too
    if use_reference:
        shutil.copyfile(dst / exm[0], dst / sol[0])  # substitution only in the copy
    return dst


def finish():
    (HERE / "results.json").write_text(json.dumps(ev, indent=2))
    print(f"\n{len(failures)} check(s) FAILED" if failures else "\nAll checks passed")
    sys.exit(1 if failures else 0)


def main():
    cfg = json.loads((EX / ".meta/config.json").read_text())
    sol, tst, exm = (cfg["files"][k] for k in ("solution", "test", "example"))
    (HERE / "inputs.json").write_text(json.dumps({"config_files": cfg["files"], "named_cases": NAMED,
        "hint_file": f"{REL}/.docs/hints.md", "pester_command": "Invoke-Pester -PassThru"}, indent=2))
    pv = subprocess.run(["pwsh", "--version"], capture_output=True, text=True).stdout.strip()
    (HERE / "versions.txt").write_text(f"python: {sys.version.split()[0]}\npwsh: {pv}\n"
                                       f"git: {git('--version').stdout.strip()}\n")
    hint = EX / ".docs/hints.md"
    if not check(all((EX / f).is_file() for f in sol + tst + exm) and hint.is_file(),
                 "config.json files and hints.md exist"):
        return finish()
    before = git("status", "--porcelain", "--", REL).stdout
    ht = hint.read_text()
    blocks = [b.split("\n", 1) for b in ht.split(FENCE)[1::2]]
    langs = [b[0].strip() for b in blocks]
    check(langs == ["powershell", "text", "powershell", "text"], f"hint has two examples, each with an output ({langs})")
    ev["micro_examples"] = []
    for i in (0, 2):
        if len(blocks) < i + 2:
            break
        code, want = blocks[i][1], blocks[i + 1][1].strip().splitlines()
        p = pwsh(code, ROOT)
        got = p.stdout.strip().splitlines()
        check(p.returncode == 0 and got == want, f"micro-example {i // 2 + 1} output agrees with the hint ({got})")
        ev["micro_examples"].append({"code": code, "hint_output": want, "actual_output": got})
    ref = (EX / exm[0]).read_text()
    check("| ForEach-Object" in ref and "-join" in ref, "the reference collects ForEach-Object output and uses -join")
    check("ForEach-Object" in ht and "-join" in ht and "@( )" in ht and "learn.microsoft.com" in ht,
          "hint names ForEach-Object, -join and @( ) and links the language reference")
    check('return "A`n"' in ref, "the reference returns the one-row 'A' diamond before the pipeline")
    p = pwsh(EARLY, ROOT)
    check(p.stdout.strip() == "A,@,A", f"without that early return the expression gives extra rows ({p.stdout.strip()})")
    ev["rows_for_A_without_early_return"] = p.stdout.strip()
    toml = tomllib.loads((EX / ".meta/tests.toml").read_text())
    n_inc = sum(1 for v in toml.values() if v.get("include", True) is not False)
    names = re.findall(r'^\s*It\s+"([^"]+)"', (EX / tst[0]).read_text(), re.M)
    print(f"tests.toml: {len(toml)} entries, {n_inc} included; test file: {len(names)} It blocks")
    print(f"NOTE: {len(names) - n_inc} It block(s) have no entry in tests.toml (names differ in wording)")
    check(len(names) >= n_inc and all(n in names for n in NAMED), "named cases are in the test file")
    with tempfile.TemporaryDirectory() as tmp:
        rc, p = run_pester(make_copy(Path(tmp) / "r", True, sol, exm))
        rc_s, ps = run_pester(make_copy(Path(tmp) / "s", False, sol, exm))
    check(rc == 0, f"reference: pwsh exit code 0 (got {rc})")
    if check(p is not None, "reference: Pester result parsed"):
        print(f"Executed cases: {p['Total']}  Passed: {p['Passed']}  Failed: {p['Failed']}")
        check(p["Total"] > 0 and p["Total"] == len(names), "executed count equals the It blocks")
        check(p["Failed"] == 0 and p["Result"] == "Passed", "reference: no failed tests")
        res = {t["Name"]: t["Result"] for t in p["Tests"]}
        for nm in NAMED:
            check(res.get(nm) == "Passed", f"named case '{nm}' passed")
        ev.update(executed_cases=p["Total"], tool_versions={"pester": p["PesterVersion"], "powershell": p["PSVersion"]},
                  expected_vs_actual=[{"test": t["Name"], "expected": "Passed", "actual": t["Result"]} for t in p["Tests"]])
    check(rc_s == 0 and ps is not None, "stub run: completed and parsed")
    if ps:
        check(ps["Failed"] > 0 or ps["FailedContainers"] > 0 or ps["Result"] == "Failed",
              "learner stub still fails the tests (unsolved)")
        ev["learner_stub"] = {k: ps[k] for k in ("Result", "Total", "Passed", "Failed")}
    new = set(git("diff", "--name-only", "main", "--", REL).stdout.split()) | \
        set(git("ls-files", "--others", "--exclude-standard", "--", REL).stdout.split())
    check(new == {f"{REL}/.docs/hints.md"}, f"only hints.md is added or changed under the exercise ({sorted(new)})")
    check(git("diff", "--quiet", "main", "--", *[f"{REL}/{x}" for x in sol]).returncode == 0, "learner stub file unchanged")
    check(git("status", "--porcelain", "--", REL).stdout == before, "the check did not change files under the exercise")
    finish()


main()
