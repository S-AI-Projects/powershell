# connect: file roles and metadata check

## File roles

| Path | Role |
|------|------|
| `exercises/practice/connect/Connect.ps1` | learner stub, the `solution` file; must stay unsolved |
| `exercises/practice/connect/Connect.tests.ps1` | Pester tests, the `test` file |
| `exercises/practice/connect/.meta/Connect.example.ps1` | reference solution, the `example` file |
| `exercises/practice/connect/.meta/config.json` | metadata: blurb and the `files` object |
| `exercises/practice/connect/.meta/tests.toml` | canonical case list (UUID and description) |

## Generated and maintained files

`tests.toml` is generated: its header says it is an auto-generated file that `configlet sync` rewrites. No script in `bin/` writes `Connect.tests.ps1`, so it is maintained in the repository and matched to `tests.toml` by test name. The stub, the reference and `config.json` are also maintained in the repository.

`config.json` declares `solution`, `test` and `example` only. It has no `editor` list, so none is checked.

Counts: 12 cases in `tests.toml`, none excluded; 12 `It` blocks in `Connect.tests.ps1`.

## How the runner finds the files

`bin/run-tests.ps1` does not read `config.json`. For each exercise it copies every `*.tests.ps1` file into a temporary folder, takes the `*.example.ps1` file from `.meta`, and copies it into the same folder under its own name with `example.` removed (here `Connect.ps1`). It then runs `Invoke-Pester` there and fails if no test ran or any test failed.

## Validate the metadata

~~~
python3 tools/course_checks/r09-t018.py
~~~

It reads the `files` object and rejects absolute paths, parent traversal (`..`), paths that resolve outside the exercise, and files that do not exist. It also checks that the declared files agree with the name-based search above. Problems print as `ERROR <CODE> <key>: <detail>`, with codes such as `MISSING_FILE`, `OUTSIDE_EXERCISE`, `MISSING_KEY` and `RUNNER_MISMATCH`, and the exit code is 1.

## Checking the checker

`work/R09-T018/check.py` (coursework fork only, not part of any upstream change) runs the checker on the real config, which must pass, and on three deliberately invalid copies, each of which must fail for its own reason: a missing reference (`MISSING_FILE` on `example`), a missing test (`MISSING_FILE` on `test`) and a test path outside the exercise (`OUTSIDE_EXERCISE` on `test`). It also runs the tests against the reference and confirms the learner stub still fails.

~~~
python3 work/R09-T018/check.py
~~~
