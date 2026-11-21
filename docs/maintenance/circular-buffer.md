# circular-buffer: test source and reproduction

## Where the tests come from

This track has no generator for test files: there is no template in `.meta` and no script in `bin/` that writes `CircularBuffer.tests.ps1`.

| File | Role |
|------|------|
| `exercises/practice/circular-buffer/.meta/tests.toml` | Case list. Each case is a UUID with a `description`. Its header says it is synced by `configlet sync`. |
| `exercises/practice/circular-buffer/CircularBuffer.tests.ps1` | Pester tests, maintained by hand. Each `It` name equals a `description` in `tests.toml`. |
| `exercises/practice/circular-buffer/.meta/CircularBuffer.example.ps1` | Reference solution. |
| `exercises/practice/circular-buffer/CircularBuffer.ps1` | Learner stub. Must stay unsolved. |
| `exercises/practice/circular-buffer/.meta/config.json` | Gives the solution, test and example file paths. |

Because the test file is hand-maintained, "regenerating" it means checking that it still matches `tests.toml` and that the reference passes it.

## Reproduce

Needs PowerShell 7, Pester and Python 3. From the repository root:

~~~
python3 tools/course_checks/r09-t012.py
~~~

The check:

1. Confirms every included `tests.toml` case has exactly one matching `It` block, and the other way round, so no case is dropped.
2. Builds two fresh temporary copies of the exercise (dotfiles included) and compares `CircularBuffer.tests.ps1` between them. Only a timestamp comment line may differ; the file has none today.
3. Substitutes the reference for the learner stub in each copy only and runs `Invoke-Pester -PassThru`. It fails on a non-zero exit code, `FailedCount > 0` or `TotalCount == 0`.
4. Confirms the learner stub is untouched and still fails the tests.

To run the tests for every exercise the way CI does: `pwsh bin/run-tests.ps1`.

To refresh `tests.toml` itself, fetch configlet with `bin/fetch-configlet` and see its own help for the `sync` command. Do not hand-edit generated test content.

## Case-to-output mapping

Counts: 14 included, 0 excluded in `tests.toml`; 14 `It` blocks in `CircularBuffer.tests.ps1`. The three cases this page is anchored on are marked with `*`.

| UUID | `It` name | Line in test file |
|------|-----------|-------------------|
| (describe block) | `CircularBuffer test cases` * | 5 |
| `28268ed4-4ff3-45f3-820e-895b44d53dfa` | reading empty buffer should fail * | 6 |
| `2e6db04a-58a1-425d-ade8-ac30b5f318f3` | can read an item just written * | 11 |
| `90741fe8-a448-45ce-be2b-de009a24c144` | each item may only be read once | 17 |
| `be0e62d5-da9c-47a8-b037-5db21827baa7` | items are read in the order they are written | 24 |
| `2af22046-3e44-4235-bfe6-05ba60439d38` | full buffer can't be written to | 32 |
| `547d192c-bbf0-4369-b8fa-fc37e71f2393` | a read frees up capacity for another write | 38 |
| `04a56659-3a81-4113-816b-6ecb659b4471` | read position is maintained even across multiple writes | 46 |
| `60c3a19a-81a7-43d7-bb0a-f07242b1111f` | items cleared out of buffer can't be read | 56 |
| `45f3ae89-3470-49f3-b50e-362e4b330a59` | clear frees up capacity for another write | 63 |
| `e1ac5170-a026-4725-bfbe-0cf332eddecd` | clear does nothing on empty buffer | 71 |
| `9c2d4f26-3ec7-453f-a895-7e7ff8ae7b5b` | overwrite acts like write on non-full buffer | 78 |
| `880f916b-5039-475c-bd5c-83463c36a147` | overwrite replaces the oldest item on full buffer | 86 |
| `bfecab5b-aca1-4fab-a2b0-cd4af2b053c3` | overwrite replaces the oldest item remaining in buffer following a read | 95 |
| `9cebe63a-c405-437b-8b62-e3fdc1ecec5a` | initial clear does not affect wrapping around | 108 |
