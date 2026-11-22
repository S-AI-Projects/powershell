#!/usr/bin/env python3
"""R09-T018 check: the real connect config passes the path checker, three invalid
fixtures each fail for the intended reason, and the tests pass against the reference
while the learner stub still fails. Non-zero exit on any failed assertion."""
import importlib.util, json, re, shutil, subprocess, sys, tempfile, tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REL = "exercises/practice/connect"
EX = ROOT / REL
TOOL = ROOT / "tools" / "course_checks" / "r09-t018.py"
NAMED = ["an empty board has no winner", "X can win on a 1x1 board"]
FIXTURES = [
    ("missing reference", ("example", ".meta/Missing.example.ps1"), ("MISSING_FILE", "example")),
    ("missing test", ("test", "Missing.tests.ps1"), ("MISSING_FILE", "test")),
    ("outside exercise", ("test", "../connect/Connect.tests.ps1"), ("OUTSIDE_EXERCISE", "test")),
]
PS = ('$r = Invoke-Pester -PassThru; "RESULT_JSON:" + ([pscustomobject]@{Result="$($r.Result)"; '
      'Total=$r.TotalCount; Passed=$r.PassedCount; Failed=$r.FailedCount; '
      'FailedContainers=$r.FailedContainersCount; PesterVersion="$($r.Version)"; '
      'PSVersion="$($r.PSVersion)"; Tests=@($r.Tests | ForEach-Object '
      '{ [pscustomobject]@{Name=$_.Name; Result="$($_.Result)"} })} | ConvertTo-Json -Depth 4 -Compress)')
failures, ev = [], {}


def check(cond, msg):
    print(("PASS: " if cond else "FAIL: ") + msg)
    if not cond:
        failures.append(msg)
    return cond


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def load_tool():
    spec = importlib.util.spec_from_file_location("r09_t018", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_pester(folder):
    p = subprocess.run(["pwsh", "-NoProfile", "-Command", PS], cwd=folder, capture_output=True, text=True)
    lines = [l for l in p.stdout.splitlines() if l.startswith("RESULT_JSON:")]
    return p.returncode, (json.loads(lines[-1][12:]) if lines else None)


def make_copy(parent, use_reference, sol, exm):
    dst = Path(parent) / "connect"
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
        "fixtures": [{"name": n, "key": k, "path": p, "expected_error": list(e)} for n, (k, p), e in FIXTURES],
        "pester_command": "Invoke-Pester -PassThru"}, indent=2))
    pv = subprocess.run(["pwsh", "--version"], capture_output=True, text=True).stdout.strip()
    (HERE / "versions.txt").write_text(f"python: {sys.version.split()[0]}\npwsh: {pv}\n"
                                       f"git: {git('--version').stdout.strip()}\n")
    ok = TOOL.is_file() and all((EX / f).is_file() for f in sol + tst + exm)
    if not check(ok, "the checker and the config.json files exist"):
        return finish()
    before = git("status", "--porcelain", "--", REL).stdout
    tool = load_tool()
    real = tool.validate(EX) or tool.runner_agreement(EX)
    check(real == [], f"the real config passes the checker (errors: {real})")
    ev["real_config_errors"] = [list(e) for e in real]
    ev["fixtures"] = []
    for name, (key, path), (code, ekey) in FIXTURES:
        with tempfile.TemporaryDirectory() as tmp:
            ex = Path(tmp) / "connect"
            (ex / ".meta").mkdir(parents=True)
            bad = {"files": {k: list(v) for k, v in cfg["files"].items()}}
            bad["files"][key] = [path]
            (ex / ".meta" / "config.json").write_text(json.dumps(bad))
            for f in sol + tst + exm:  # real files, so only the one broken path is wrong
                (ex / f).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(EX / f, ex / f)
            errors = tool.validate(ex)
            p = subprocess.run([sys.executable, str(TOOL), str(ex)], capture_output=True, text=True)
        check(errors == [(code, ekey, path)], f"fixture '{name}' fails as intended: {errors}")
        check(p.returncode == 1 and f"ERROR {code} {ekey}:" in p.stdout, f"fixture '{name}': command exits 1 and names {code}")
        ev["fixtures"].append({"name": name, "errors": [list(e) for e in errors], "exit_code": p.returncode})
    doc = ROOT / "docs/maintenance/connect.md"
    dt = doc.read_text() if doc.is_file() else ""
    paths = [f"{REL}/{f}" for f in sol + tst + exm]
    check(all(p in dt for p in paths), "the maintenance page names the real stub, test and reference paths")
    check("auto-generated" in dt and "configlet sync" in dt and "bin/run-tests.ps1" in dt,
          "the maintenance page distinguishes generated files and explains the runner")
    check("python3 tools/course_checks/r09-t018.py" in dt, "the maintenance page gives the validation command")
    toml = tomllib.loads((EX / ".meta/tests.toml").read_text())
    n_inc = sum(1 for v in toml.values() if v.get("include", True) is not False)
    names = re.findall(r'^\s*It\s+"([^"]+)"', (EX / tst[0]).read_text(), re.M)
    print(f"tests.toml: {len(toml)} entries, {n_inc} included; test file: {len(names)} It blocks")
    check(n_inc == len(names) and all(n in names for n in NAMED), "included cases equal the It blocks; named cases present")
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
    check(git("diff", "--name-only", "main", "--", REL).stdout.split() == [], "no file under the exercise was changed")
    check(git("diff", "--quiet", "main", "--", *[f"{REL}/{x}" for x in sol]).returncode == 0, "learner stub file unchanged")
    check(git("status", "--porcelain", "--", REL).stdout == before, "the check did not change files under the exercise")
    finish()


main()
