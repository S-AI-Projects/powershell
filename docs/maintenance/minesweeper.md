# Minesweeper test maintenance

## Sources and scope

`Minesweeper.tests.ps1` is the maintained Pester source for this exercise. There is no per-exercise Jinja, Go-template, or `.tpl` file that generates it. The track's Configlet sync updates exercise metadata, including canonical cases in `.meta/tests.toml`; it does not generate this PowerShell test file. The exercise is marked deprecated in the track config, so exercise-only Configlet sync is not available. Use the track-wide sync command in an isolated copy when checking reproducibility:

```sh
bin/configlet sync --tests include --update --yes
```

The command checks metadata against problem specifications and can update other track metadata. Run it from a disposable track copy with a separate cache. The task checker does this twice, with the second run offline, and compares the maintained Pester file byte-for-byte after each run. No timestamp normalization is needed because that source contains no generated timestamp.

## Cases covered

The canonical metadata contains 12 cases. The maintained Pester suite, `Describe "Minesweeper test cases"`, has 14 cases: those 12 canonical behaviors plus the track-specific `annotate 9` and invalid-character checks.

| Canonical case | Metadata ID | Pester behavior | Expected edge behavior |
| --- | --- | --- | --- |
| no rows | `0c5ec4bd-dea7-4138-8651-1203e1cb9f44` | `It "no rows"` | `Get-Annotate -Minefield @()` returns no rows; `Should -BeNullOrEmpty` accepts the empty result. |
| no columns | `650ac4c0-ad6b-4b41-acde-e4ea5852c3b8` | `It "no columns"` | The input is one empty string, `@("")`, and the expected output is one empty string. |

The no-columns input is deliberately `@("")`: it means a board with one row and zero columns. Keep it distinct from `@()`, which has no rows. The exact assertion `Should -BeExactly $want` preserves that one-row shape.

## Running the reference check

The track CI runner is `bin/run-tests.ps1`. For this exercise, `work/R09-T032/check.py` resolves the solution, test, and example paths from `.meta/config.json`, copies the exercise including hidden files, and substitutes `.meta/Minesweeper.example.ps1` for the learner solution only in that temporary copy. It invokes the maintained Pester suite, fails when no tests run or any test fails, records the two selected cases and tool versions, and checks that the learner solution in the checkout was not changed. Use PowerShell 7 with Pester installed.

```sh
python3 work/R09-T032/check.py
```

The same checker invokes `tools/course_checks/r09-t032.py` to perform the two isolated Configlet syncs and preserve generation evidence under `work/R09-T032/generation.json`.
