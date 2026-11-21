#!/usr/bin/env python3
"""R09-T011 check: say canonical case rationales.

Copies exercises/practice/say to a temp dir, substitutes the reference only in
that copy, runs Invoke-Pester there, and exits non-zero on any failed assertion.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REL = "exercises/practice/say"
EX = ROOT / REL
TOML_REL = f"{REL}/.meta/tests.toml"
UUIDS = {
    "5d22a120-ba0c-428c-bd25-8682235d83e8": "zero",
    "9b5eed77-dbf6-439d-b920-3f7eb58928f6": "one",
    "7c499be1-612e-4096-a5e1-43b2f719406d": "fourteen",
}
PS = (
    '$r = Invoke-Pester -PassThru; '
    '"RESULT_JSON:" + ([pscustomobject]@{Result="$($r.Result)"; Total=$r.TotalCount; '
    'Passed=$r.PassedCount; Failed=$r.FailedCount; FailedContainers=$r.FailedContainersCount; '
    'PesterVersion="$($r.Version)"; PSVersion="$($r.PSVersion)"; '
    'Tests=@($r.Tests | ForEach-Object { [pscustomobject]@{Name=$_.Name; Result="$($_.Result)"} })} '
    '| ConvertTo-Json -Depth 4 -Compress)'
)
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


def counts(d):
    excluded = sum(1 for v in d.values() if v.get("include", True) is False)
    return {"included": len(d) - excluded, "excluded": excluded}


def make_copy(parent, use_reference, sol, exm):
    dst = Path(parent) / "say"
    shutil.copytree(EX, dst)  # copies dotfiles too
    if use_reference:
        for s, e in zip(sol, exm):
            shutil.copyfile(dst / e, dst / s)  # substitution happens in the copy only
    return dst


def tool_version(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True)
        return (p.stdout or p.stderr).strip()
    except FileNotFoundError:
        return "not found"


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
        {"config_files": cfg["files"], "uuids": UUIDS, "pester_command": "Invoke-Pester -PassThru"},
        indent=2))
    (HERE / "versions.txt").write_text(
        f"python: {sys.version.split()[0]}\n"
        f"pwsh: {tool_version(['pwsh', '--version'])}\n"
        f"git: {tool_version(['git', '--version'])}\n")
    if not check(len(sol) == len(exm) >= 1 and all((EX / f).is_file() for f in sol + tst + exm),
                 f"config.json files exist (solution={sol}, test={tst}, example={exm})"):
        return finish()

    # 1. TOML: parses, counts unchanged, rationales present
    after = tomllib.loads((EX / ".meta/tests.toml").read_text())
    g = subprocess.run(["git", "show", f"HEAD:{TOML_REL}"], cwd=ROOT, capture_output=True, text=True)
    if not check(g.returncode == 0, "git show HEAD:tests.toml succeeded"):
        return finish()
    before = tomllib.loads(g.stdout)
    ev["toml_counts"] = {"before": counts(before), "after": counts(after)}
    print(f"Included/excluded before: {counts(before)}  after: {counts(after)}")
    check(counts(before) == counts(after), "included/excluded counts unchanged")
    check(counts(after)["excluded"] == 0, "no excluded cases")
    check({k: v.get("include") for k, v in before.items()} == {k: v.get("include") for k, v in after.items()},
          "include values unchanged")
    for u, name in UUIDS.items():
        entry = after.get(u, {})
        check(entry.get("description") == name and len(entry.get("comment", "")) > 20,
              f"{u} ({name}) has a rationale comment")

    # 2. Reference passes in a temp copy
    with tempfile.TemporaryDirectory() as tmp:
        rc, ref, err = run_pester(make_copy(Path(tmp) / "ref", True, sol, exm))
        rc2, stub, err2 = run_pester(make_copy(Path(tmp) / "stub", False, sol, exm))
    check(rc == 0, f"reference run: pwsh exit code 0 (got {rc})")
    if not check(ref is not None, "reference run: result parsed"):
        print(err)
        return finish()
    print(f"Executed cases: {ref['Total']}  Passed: {ref['Passed']}  Failed: {ref['Failed']}")
    check(ref["Total"] > 0, "reference run executed at least one test")
    check(ref["Failed"] == 0 and ref["Result"] == "Passed", "reference run: no failed tests")
    included = {v["description"] for v in after.values() if v.get("include", True) is not False}
    results = {t["Name"]: t["Result"] for t in ref["Tests"]}
    check(set(results) == included and ref["Total"] == len(included),
          "executed tests match the included TOML cases")
    for u, name in UUIDS.items():
        check(results.get(name) == "Passed", f"named case '{name}' passed")
    ev["expected_vs_actual"] = [
        {"test": n, "expected": "Passed", "actual": results.get(n, "missing")} for n in sorted(included)]
    ev["tool_versions"] = {"pester": ref["PesterVersion"], "powershell": ref["PSVersion"]}

    # 3. Learner stub is still unsolved
    check(rc2 == 0 and stub is not None, "stub run: completed and parsed")
    if stub:
        check(stub["Failed"] > 0 or stub["FailedContainers"] > 0 or stub["Result"] == "Failed",
              "learner stub still fails the tests (unsolved)")
        ev["learner_stub"] = {k: stub[k] for k in ("Result", "Total", "Passed", "Failed")}
    d = subprocess.run(["git", "diff", "--quiet", "HEAD", "--"] + [f"{REL}/{s}" for s in sol], cwd=ROOT)
    check(d.returncode == 0, "learner stub file unchanged in the repo")
    finish()


main()
