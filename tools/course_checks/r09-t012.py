#!/usr/bin/env python3
"""R09-T012: circular-buffer test-source round trip check.

This track has no generator for the test files. CircularBuffer.tests.ps1 is
maintained by hand and is matched to .meta/tests.toml by test description
(tests.toml itself is synced by configlet). This check:
  1. checks every included tests.toml case has exactly one matching It block
  2. builds two fresh temporary copies and compares the test file (only a
     timestamp comment line may differ; none exists today)
  3. runs the reference solution with Pester in each copy
  4. checks the learner stub is untouched and still unsolved
Usage: python3 tools/course_checks/r09-t012.py [--evidence-dir DIR]
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SLUG = "circular-buffer"
REL = f"exercises/practice/{SLUG}"
EX = ROOT / REL
DESCRIBE = "CircularBuffer test cases"
NAMED = ["reading empty buffer should fail", "can read an item just written"]
STAMP = re.compile(r"^[ \t]*#.*\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}.*$", re.M)
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


def make_copy(parent, use_reference, sol, exm):
    dst = Path(parent) / SLUG
    shutil.copytree(EX, dst)  # copies dotfiles too
    if use_reference:
        for s, e in zip(sol, exm):
            shutil.copyfile(dst / e, dst / s)  # substitution only in the copy
    return dst


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalize(text):
    return STAMP.sub("", text)


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


def finish(evidence_dir):
    if evidence_dir:
        (evidence_dir / "results.json").write_text(json.dumps(ev, indent=2))
    if failures:
        print(f"\n{len(failures)} check(s) FAILED")
        sys.exit(1)
    print("\nAll checks passed")
    sys.exit(0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence-dir")
    args = ap.parse_args()
    evd = Path(args.evidence_dir) if args.evidence_dir else None
    cfg = json.loads((EX / ".meta/config.json").read_text())
    sol, tst, exm = cfg["files"]["solution"], cfg["files"]["test"], cfg["files"]["example"]
    if evd:
        (evd / "inputs.json").write_text(json.dumps(
            {"exercise": REL, "config_files": cfg["files"], "described_block": DESCRIBE,
             "named_cases": NAMED, "pester_command": "Invoke-Pester -PassThru"}, indent=2))
        (evd / "versions.txt").write_text(
            f"python: {sys.version.split()[0]}\n"
            f"pwsh: {tool_version(['pwsh', '--version'])}\n"
            f"git: {tool_version(['git', '--version'])}\n")
    if not check(len(sol) == len(exm) == len(tst) == 1 and all((EX / f).is_file() for f in sol + tst + exm),
                 f"config.json files exist (solution={sol}, test={tst}, example={exm})"):
        return finish(evd)
    state_before = git_state()

    # 1. tests.toml cases <-> It blocks in the hand-maintained test file
    toml = tomllib.loads((EX / ".meta/tests.toml").read_text())
    included = [v["description"] for v in toml.values() if v.get("include", True) is not False]
    text = (EX / tst[0]).read_text()
    it_names = re.findall(r'^\s*It\s+"([^"]+)"', text, re.M)
    ev["toml"] = {"included": len(included), "excluded": len(toml) - len(included)}
    print(f"tests.toml: {len(included)} included, {len(toml) - len(included)} excluded; "
          f"test file: {len(it_names)} It blocks")
    check(len(set(included)) == len(included), "tests.toml descriptions are unique")
    check(len(set(it_names)) == len(it_names), "It names in the test file are unique")
    check(set(included) == set(it_names), "every included case has a matching It block and vice versa (none dropped)")
    check(f'Describe "{DESCRIBE}"' in text, f'test file has Describe "{DESCRIBE}"')
    for n in NAMED:
        check(n in included and n in it_names, f"named case '{n}' is in tests.toml and the test file")
    check(len(STAMP.findall(text)) == 0, "test file has no generated-timestamp comment line")

    # 2. two fresh copies: compare the test file
    with tempfile.TemporaryDirectory() as tmp:
        a = make_copy(Path(tmp) / "a", True, sol, exm)
        b = make_copy(Path(tmp) / "b", True, sol, exm)
        ha, hb, hr = sha(a / tst[0]), sha(b / tst[0]), sha(EX / tst[0])
        na = normalize((a / tst[0]).read_text())
        nb = normalize((b / tst[0]).read_text())
        check(ha == hb == hr, "test file is byte-identical in both copies and in the repo")
        check(na == nb, "test file is identical after timestamp normalization")
        ev["test_file_sha256"] = {"copy_a": ha, "copy_b": hb, "repo": hr}

        # 3. reference passes in both copies
        runs = {}
        for label, folder in (("copy_a", a), ("copy_b", b)):
            rc, ref, err = run_pester(folder)
            runs[label] = ref
            check(rc == 0, f"{label}: pwsh exit code 0 (got {rc})")
            if not check(ref is not None, f"{label}: Pester result parsed"):
                print(err)
                continue
            print(f"{label}: executed cases {ref['Total']}, passed {ref['Passed']}, failed {ref['Failed']}")
            check(ref["Total"] > 0, f"{label}: at least one test executed")
            check(ref["Failed"] == 0 and ref["Result"] == "Passed", f"{label}: no failed tests")
            results = {t["Name"]: t["Result"] for t in ref["Tests"]}
            check(set(results) == set(included) and ref["Total"] == len(included),
                  f"{label}: executed tests match the included cases")
            for n in NAMED:
                check(results.get(n) == "Passed", f"{label}: named case '{n}' passed")
        ra, rb = runs.get("copy_a"), runs.get("copy_b")
        if ra and rb:
            same = [(t["Name"], t["Result"]) for t in ra["Tests"]] == [(t["Name"], t["Result"]) for t in rb["Tests"]]
            check(same, "both copies give the same per-test results")
            ev["executed_cases"] = ra["Total"]
            ev["expected_vs_actual"] = [
                {"test": t["Name"], "expected": "Passed", "actual": t["Result"]} for t in ra["Tests"]]
            ev["tool_versions"] = {"pester": ra["PesterVersion"], "powershell": ra["PSVersion"]}

        # 4. learner stub still unsolved
        c = make_copy(Path(tmp) / "c", False, sol, exm)
        rc3, stub, _ = run_pester(c)
    check(rc3 == 0 and stub is not None, "stub run: completed and parsed")
    if stub:
        check(stub["Failed"] > 0 or stub["FailedContainers"] > 0 or stub["Result"] == "Failed",
              "learner stub still fails the tests (unsolved)")
        ev["learner_stub"] = {k: stub[k] for k in ("Result", "Total", "Passed", "Failed")}
    d = subprocess.run(["git", "diff", "--quiet", "HEAD", "--"] + [f"{REL}/{s}" for s in sol], cwd=ROOT)
    check(d.returncode == 0, "learner stub file unchanged in the repo")
    check(git_state() == state_before, "files under the exercise were not changed by this check")
    finish(evd)


main()
