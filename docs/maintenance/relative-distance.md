# relative-distance: test source and reproduction

## Where the tests come from

This track has no automated generator (e.g. Jinja template) for test files: there is no per-exercise template in `.meta` and no track-level code generator in `bin/` that outputs `RelativeDistance.tests.ps1`.

| File | Role |
|------|------|
| `exercises/practice/relative-distance/.meta/tests.toml` | Case list. Each case is a UUID with a `description`. Its header indicates it is synced via `configlet sync`. |
| `exercises/practice/relative-distance/RelativeDistance.tests.ps1` | Pester test suite, maintained by hand by track maintainers. Each `It` name matches a `description` in `tests.toml`. |
| `exercises/practice/relative-distance/.meta/RelativeDistance.example.ps1` | Maintained reference solution. |
| `exercises/practice/relative-distance/RelativeDistance.ps1` | Learner stub. Must remain unsolved (`Throw "Please implement this function"`). |
| `exercises/practice/relative-distance/.meta/config.json` | Exercise metadata declaring solution, test, and example file paths. |

Because the test file is hand-maintained, "regenerating" and verifying it entails ensuring that it perfectly mirrors `tests.toml`, that no canonical case is silently dropped, that generation comparison is reproducible under timestamp normalization, and that the reference solution passes all test cases.

## Reproduce

Requires PowerShell 7, Pester, and Python 3. From the repository root:

```bash
python3 tools/course_checks/r09-t052.py
```

The check:

1. Confirms every included `tests.toml` case has exactly one matching `It` block in `RelativeDistance.tests.ps1`, and vice-versa, asserting 0 dropped cases.
2. Builds two fresh temporary copies of the exercise (including dotfiles) and compares `RelativeDistance.tests.ps1` between them. Only a documented generated timestamp comment line may differ (the file has no timestamp header today).
3. Substitutes the reference for the learner stub in each copy only and runs `Invoke-Pester -PassThru`. It fails explicitly if the exit code is non-zero, `FailedCount > 0`, or `TotalCount == 0`.
4. Confirms the learner starter stub is untouched and still fails all tests (unsolved).

To run all track tests via CI: `pwsh bin/run-tests.ps1`.

To refresh `tests.toml` from problem-specifications canonical data:
```bash
./bin/fetch-configlet
./bin/configlet sync --tests --exercise relative-distance
```

## Case-to-output mapping

Counts: 7 included, 0 excluded in `tests.toml`; 7 `It` blocks in `RelativeDistance.tests.ps1`. The three cases this page is anchored on are marked with `*`.

| UUID | `It` name / Case | Line in test file | Expected Result |
|------|------------------|:-----------------:|-----------------|
| (describe block) | `RelativeDistance test cases` * | 5 | Container block |
| `4a1ded74-5d32-47fb-8ae5-321f51d06b5b` | `Direct parent-child relation` * | 6 | `1` |
| `30d17269-83e9-4f82-a0d7-8ef9656d8dce` | `Sibling relationship` * | 16 | `1` |
| `8dffa27d-a8ab-496d-80b3-2f21c77648b5` | `Two degrees of separation, grandchild` | 25 | `2` |
| `34e56ec1-d528-4a42-908e-020a4606ee60` | `Unrelated individuals` | 35 | `$null` |
| `93ffe989-bad2-48c4-878f-3acb1ce2611b` | `Complex graph, cousins` | 45 | `9` |
| `2cc2e76b-013a-433c-9486-1dbe29bf06e5` | `Complex graph, no shortcut, far removed nephew` | 105 | `14` |
| `46c9fbcb-e464-455f-a718-049ea3c7400a` | `Complex graph, some shortcuts, cross-down and cross-up, cousins several times removed, with unrelated family tree` | 165 | `12` |
