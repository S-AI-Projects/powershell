#!/usr/bin/env python3
"""R09-T015: hangman reference cost study. Asserts correctness first, then times
the reference at three word lengths (median of repeated runs, measured inside one
pwsh process after the class is defined). Exits non-zero on any failed assertion."""
import json, re, shutil, statistics, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REL = "exercises/practice/hangman"
EX = ROOT / REL
BASE = "main"
NAMED = ["test initially 9 failures are allowed"]
SIZES = [100, 1000, 10000]
REPS = 7
STARTUP_REPS = 5
PS = ('$r = Invoke-Pester -PassThru; "RESULT_JSON:" + ([pscustomobject]@{Result="$($r.Result)"; '
      'Total=$r.TotalCount; Passed=$r.PassedCount; Failed=$r.FailedCount; '
      'FailedContainers=$r.FailedContainersCount; PesterVersion="$($r.Version)"; '
      'PSVersion="$($r.PSVersion)"; Tests=@($r.Tests | ForEach-Object '
      '{ [pscustomobject]@{Name=$_.Name; Result="$($_.Result)"} })} | ConvertTo-Json -Depth 4 -Compress)')
BENCH = r'''
. ./Hangman.ps1
$word10 = "abcdefghij"
function Play([int]$n) {
    $word = $word10 * [int]($n / 10)
    $g = [Hangman]::new($word)
    foreach ($c in $word10.ToCharArray()) { $g.Guess([string]$c) }
    return [pscustomobject]@{ word = $word; display = $g.Display(); status = [string]$g.GetStatus(); remaining = $g.RemainingGuesses }
}
$out = foreach ($n in @(%SIZES%)) {
    $first = Play $n
    $ms = foreach ($i in 1..%REPS%) { $sw = [Diagnostics.Stopwatch]::StartNew(); $null = Play $n; $sw.Stop(); $sw.Elapsed.TotalMilliseconds }
    [pscustomobject]@{ n = $n; correct = ($first.display -ceq $first.word -and $first.status -ceq 'WIN' -and $first.remaining -eq 9); ms = @($ms) }
}
"BENCH_JSON:" + ($out | ConvertTo-Json -Depth 4 -Compress)
'''
failures, ev = [], {}


def check(cond, msg):
    print(("PASS: " if cond else "FAIL: ") + msg)
    if not cond:
        failures.append(msg)
    return cond


def pwsh(script, folder):
    return subprocess.run(["pwsh", "-NoProfile", "-Command", script], cwd=folder,
                          capture_output=True, text=True)


def run_pester(folder):
    p = pwsh(PS, folder)
    lines = [l for l in p.stdout.splitlines() if l.startswith("RESULT_JSON:")]
    return p.returncode, (json.loads(lines[-1][12:]) if lines else None)


def make_copy(parent, use_reference, sol, exm):
    dst = Path(parent) / "hangman"
    shutil.copytree(EX, dst)  # copies dotfiles too
    if use_reference:
        shutil.copyfile(dst / exm[0], dst / sol[0])  # substitution only in the copy
    return dst


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def timed(cmd, folder, reps):
    ts = []
    for _ in range(reps):
        t = time.perf_counter()
        p = subprocess.run(cmd, cwd=folder, capture_output=True, text=True)
        ts.append((time.perf_counter() - t) * 1000)
        if p.returncode != 0:
            return None
    return ts


def finish():
    (HERE / "results.json").write_text(json.dumps(ev, indent=2))
    print(f"\n{len(failures)} check(s) FAILED" if failures else "\nAll checks passed")
    sys.exit(1 if failures else 0)


def main():
    cfg = json.loads((EX / ".meta/config.json").read_text())
    sol, tst, exm = (cfg["files"][k] for k in ("solution", "test", "example"))
    (HERE / "inputs.json").write_text(json.dumps(
        {"config_files": cfg["files"], "input_size": "n = length of the secret word",
         "sizes": SIZES, "repetitions": REPS, "startup_repetitions": STARTUP_REPS,
         "word": "abcdefghij repeated n/10 times; each of its 10 letters guessed once",
         "named_cases": NAMED, "pester_command": "Invoke-Pester -PassThru"}, indent=2))
    pv = subprocess.run(["pwsh", "--version"], capture_output=True, text=True).stdout.strip()
    (HERE / "versions.txt").write_text(f"python: {sys.version.split()[0]}\npwsh: {pv}\n"
                                       f"git: {git('--version').stdout.strip()}\n")
    if not check(all((EX / f).is_file() for f in sol + tst + exm), f"config.json files exist ({sol}, {tst}, {exm})"):
        return finish()
    before = git("status", "--porcelain", "--", REL).stdout
    ref_text = (EX / exm[0]).read_text()
    check("# Cost, with n = length of the secret word" in ref_text and "O(n)" in ref_text,
          "the reference carries the cost and invariant comment")
    changed = git("diff", "--name-only", BASE, "--", REL).stdout.split()
    check(changed == [f"{REL}/{exm[0]}"], f"only the reference file changed ({changed})")
    d = git("diff", "-U0", BASE, "--", f"{REL}/{exm[0]}").stdout.splitlines()
    added = [l[1:] for l in d if l.startswith("+") and not l.startswith("+++")]
    removed = [l for l in d if l.startswith("-") and not l.startswith("---")]
    check(added and not removed and all(l.lstrip().startswith("#") for l in added),
          f"the reference change is comment-only ({len(added)} lines added, {len(removed)} removed)")
    names = re.findall(r'^\s*It\s+"([^"]+)"', (EX / tst[0]).read_text(), re.M)
    print(f"test file: {len(names)} It blocks (this exercise has no tests.toml)")
    check(all(n in names for n in NAMED), "named case is in the test file")
    with tempfile.TemporaryDirectory() as tmp:
        ref = make_copy(Path(tmp) / "r", True, sol, exm)
        stub = make_copy(Path(tmp) / "s", False, sol, exm)
        rc, p = run_pester(ref)
        rc_s, ps = run_pester(stub)
        check(rc == 0, f"reference: pwsh exit code 0 (got {rc})")
        if check(p is not None, "reference: Pester result parsed"):
            print(f"Executed cases: {p['Total']}  Passed: {p['Passed']}  Failed: {p['Failed']}")
            check(p["Total"] > 0 and p["Total"] == len(names), "executed count matches the It blocks")
            check(p["Failed"] == 0 and p["Result"] == "Passed", "reference: no failed tests")
            res = {t["Name"]: t["Result"] for t in p["Tests"]}
            for nm in NAMED:
                check(res.get(nm) == "Passed", f"named case '{nm}' passed")
            ev.update(executed_cases=p["Total"],
                      tool_versions={"pester": p["PesterVersion"], "powershell": p["PSVersion"]},
                      expected_vs_actual=[{"test": t["Name"], "expected": "Passed", "actual": t["Result"]} for t in p["Tests"]])
        check(rc_s == 0 and ps is not None, "stub run: completed and parsed")
        if ps:
            check(ps["Failed"] > 0 or ps["FailedContainers"] > 0 or ps["Result"] == "Failed",
                  "learner stub still fails the tests (unsolved)")
            ev["learner_stub"] = {k: ps[k] for k in ("Result", "Total", "Passed", "Failed")}
        script = BENCH.replace("%SIZES%", ",".join(map(str, SIZES))).replace("%REPS%", str(REPS))
        b = pwsh(script, ref)
        lines = [l for l in b.stdout.splitlines() if l.startswith("BENCH_JSON:")]
        check(b.returncode == 0 and len(lines) == 1, f"benchmark ran in one pwsh process (exit code {b.returncode})")
        bench = json.loads(lines[0][11:]) if lines else []
        start_only = timed(["pwsh", "-NoProfile", "-Command", "1"], ref, STARTUP_REPS)
        start_define = timed(["pwsh", "-NoProfile", "-Command", ". ./Hangman.ps1"], ref, STARTUP_REPS)
    check(len(bench) == len(SIZES), "benchmark returned a result for every size")
    med = {}
    for r in bench:
        check(r["correct"] is True, f"n={r['n']}: correctness asserted before timing (display, WIN, 9 guesses left)")
        check(len(r["ms"]) == REPS, f"n={r['n']}: {REPS} repetitions")
        med[r["n"]] = statistics.median(r["ms"])
        print(f"n={r['n']:>6}: median {med[r['n']]:.2f} ms  (min {min(r['ms']):.2f}, max {max(r['ms']):.2f})")
    check(len(med) == 3 and med[SIZES[0]] < med[SIZES[1]] < med[SIZES[2]], "median time grows with the word length")
    check(start_only is not None and start_define is not None, "startup measurements ran")
    if start_only and start_define:
        so, sd = statistics.median(start_only), statistics.median(start_define)
        print(f"pwsh start only: median {so:.0f} ms; start + define class: median {sd:.0f} ms (not algorithm cost)")
        ev["startup_ms"] = {"pwsh_start_only_median": so, "start_and_define_class_median": sd}
    ev["timings_ms"], ev["medians_ms"] = bench, med
    if len(med) == 3:
        ev["ratios"] = {"1000_over_100": med[1000] / med[100], "10000_over_1000": med[10000] / med[1000]}
        print(f"ratios of medians: 1000/100 = {ev['ratios']['1000_over_100']:.1f}, 10000/1000 = {ev['ratios']['10000_over_1000']:.1f}")
    check(git("diff", "--quiet", BASE, "--", *[f"{REL}/{x}" for x in sol]).returncode == 0, "learner stub file unchanged")
    check(git("status", "--porcelain", "--", REL).stdout == before, "the check did not change files under the exercise")
    finish()


main()
