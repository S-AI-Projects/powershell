#!/usr/bin/env python3
"""R09-T019 check: runs tools/course_checks/r09-t019.py on the real reference (exit 0),
a deliberately failing reference (exit 1), an empty selection (exit 2), the unsolved stub
(exit 1) and an interrupted run (exit 130). Hashes the exercise before and after every
run and checks that no temporary copy is left behind. Non-zero exit on any failed assertion."""
import hashlib, json, os, re, shutil, signal, subprocess, sys, tempfile, time, tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REL = "exercises/practice/house"
EX = ROOT / REL
TOOL = ROOT / "tools" / "course_checks" / "r09-t019.py"
NAMED = ["verse one - the house that jack built", "verse two - the malt that lay"]
failures, ev = [], {"runs": []}


def check(cond, msg):
    print(("PASS: " if cond else "FAIL: ") + msg)
    if not cond:
        failures.append(msg)
    return cond


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def tree_hash(folder):
    out = {}
    for dp, _, fns in os.walk(folder):
        for fn in fns:
            p = Path(dp) / fn
            out[p.relative_to(folder).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def leftovers(tmpdir):
    return sorted(x.name for x in Path(tmpdir).iterdir() if x.name.startswith("r09t019-"))


def finish():
    (HERE / "results.json").write_text(json.dumps(ev, indent=2))
    print(f"\n{len(failures)} check(s) FAILED" if failures else "\nAll checks passed")
    sys.exit(1 if failures else 0)


def run_tool(label, args, exercise, want_exit, want_executed):
    with tempfile.TemporaryDirectory() as tmpdir:
        env = dict(os.environ, TMPDIR=tmpdir)
        before = tree_hash(exercise)
        p = subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True, env=env)
        after = tree_hash(exercise)
        left = leftovers(tmpdir)
    m = re.search(r"Executed cases: (\d+)", p.stdout)
    n = int(m.group(1)) if m else None
    check(p.returncode == want_exit, f"{label}: exit code {want_exit} (got {p.returncode})")
    check(n == want_executed, f"{label}: Executed cases is {want_executed} (got {n})")
    check(before == after, f"{label}: all {len(before)} exercise files identical before and after")
    check(left == [], f"{label}: no temporary copy left behind ({left})")
    ev["runs"].append({"run": label, "args": args, "expected_exit": want_exit, "actual_exit": p.returncode,
                       "executed_cases": n, "files_unchanged": before == after, "leftover_temp_dirs": left})
    return p


def run_interrupted(exercise):
    with tempfile.TemporaryDirectory() as tmpdir:
        env = dict(os.environ, TMPDIR=tmpdir)
        before = tree_hash(exercise)
        proc = subprocess.Popen([sys.executable, str(TOOL), "--pause", "30"], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, env=env)
        seen = False
        for _ in range(150):
            if leftovers(tmpdir):
                seen = True
                break
            time.sleep(0.1)
        time.sleep(1)
        proc.send_signal(signal.SIGTERM)
        try:
            out, _ = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate()
        after = tree_hash(exercise)
        left = leftovers(tmpdir)
    check(seen, "interrupted run: the temporary copy existed when the run was interrupted")
    check(proc.returncode == 130, f"interrupted run: exit code 130 (got {proc.returncode})")
    check("INTERRUPTED" in out, "interrupted run: reported as interrupted")
    check(before == after, f"interrupted run: all {len(before)} exercise files identical before and after")
    check(left == [], f"interrupted run: temporary copy removed ({left})")
    ev["runs"].append({"run": "interrupted run", "expected_exit": 130, "actual_exit": proc.returncode,
                       "files_unchanged": before == after, "leftover_temp_dirs": left})


def main():
    cfg = json.loads((EX / ".meta/config.json").read_text())["files"]
    sol, tst, exm = cfg["solution"], cfg["test"], cfg["example"]
    q = "(Get-Module -ListAvailable Pester | Sort-Object Version -Descending | Select-Object -First 1).Version.ToString()"
    pester = subprocess.run(["pwsh", "-NoProfile", "-Command", q], capture_output=True, text=True).stdout.strip()
    pwsh = subprocess.run(["pwsh", "--version"], capture_output=True, text=True).stdout.strip()
    ev["tool_versions"] = {"pester": pester, "powershell": pwsh}
    (HERE / "versions.txt").write_text(f"python: {sys.version.split()[0]}\npwsh: {pwsh}\npester: {pester}\n"
                                       f"git: {git('--version').stdout.strip()}\n")
    (HERE / "inputs.json").write_text(json.dumps({"config_files": cfg, "named_cases": NAMED,
        "runs": ["real reference", "failing reference", "empty selection", "learner stub", "interrupted run"],
        "expected_exit_codes": [0, 1, 2, 1, 130]}, indent=2))
    ok = TOOL.is_file() and all((EX / f).is_file() for f in sol + tst + exm)
    if not check(ok, "the runner and the config.json files exist"):
        return finish()
    status_before = git("status", "--porcelain", "--", REL).stdout
    h0 = tree_hash(EX)
    learner_before = {f: h0[f] for f in sol}
    toml = tomllib.loads((EX / ".meta/tests.toml").read_text())
    n_inc = sum(1 for v in toml.values() if v.get("include", True) is not False)
    text = (EX / tst[0]).read_text()
    names = re.findall(r'^\s*It\s+"([^"]+)"', text, re.M)
    print(f"tests.toml: {len(toml)} entries, {n_inc} included; test file: {len(names)} It blocks")
    check(n_inc == len(names) == len(set(names)), "included cases equal the unique It blocks")
    check('Describe "House test cases"' in text and all(n in names for n in NAMED), "named cases are in the test file")
    p = run_tool("real reference", [], EX, 0, len(names))
    check("OK: all executed tests passed" in p.stdout, "real reference: reported as passed")
    got = re.findall(r"^\s+\[(\w+)\] (.+)$", p.stdout, re.M)
    check(sorted(n for _, n in got) == sorted(names), "real reference: the executed tests are the It blocks")
    res = {n: r for r, n in got}
    for nm in NAMED:
        check(res.get(nm) == "Passed", f"real reference: named case '{nm}' passed")
    print(f"Executed cases: {len(got)}")
    ev["executed_cases"] = len(got)
    ev["expected_vs_actual"] = [{"test": n, "expected": "Passed", "actual": r} for r, n in got]
    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "house"
        shutil.copytree(EX, bad)
        line = '"This is $text"'
        txt = (bad / exm[0]).read_text()
        check(txt.count(line) == 1, "failing reference: the line to break exists exactly once")
        (bad / exm[0]).write_text(txt.replace(line, '"That is $text"'))
        pf = run_tool("failing reference", ["--exercise", str(bad)], bad, 1, len(names))
    fm = re.search(r"Failed: (\d+)", pf.stdout)
    check("FAILED: at least one test failed" in pf.stdout and fm and int(fm.group(1)) > 0,
          "failing reference: reported as a test failure")
    pe = run_tool("empty selection", ["--filter", "no such test"], EX, 2, 0)
    check("ERROR: no test was executed" in pe.stdout, "empty selection: reported as no test executed")
    pu = run_tool("learner stub", ["--use-stub"], EX, 1, len(names))
    fs = re.search(r"Failed: (\d+)", pu.stdout)
    check(fs and int(fs.group(1)) == len(names), "learner stub: every test fails (unsolved)")
    run_interrupted(EX)
    h1 = tree_hash(EX)
    after = {f: h1[f] for f in sol}
    check(after == learner_before, "learner files: hashes identical after all runs")
    ev["learner_hashes"] = {"before": learner_before, "after": after}
    check(git("status", "--porcelain", "--", REL).stdout == status_before, "git status of the exercise unchanged")
    check(git("diff", "--name-only", "main", "--", REL).stdout.split() == [], "no file under the exercise differs from main")
    finish()


main()
