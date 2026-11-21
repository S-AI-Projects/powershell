# leap: mutation-driven regression

Records a deliberate mutant of the reference solution and the existing test that rejects it. This does not claim the current reference is buggy; the mutant is made only in a temporary copy.

## Mutant

Reference: `exercises/practice/leap/.meta/LeapYear.example.ps1`, the condition `$year % 4 -eq 0 -and $year % 100 -ne 0 -or $year % 400 -eq 0`.

Mutation: change the first operand `$year % 4` to `$year % 2`. This changes behavior, not formatting: every even year that is not a multiple of 100 would be treated as a leap year.

## Rejecting test

| Field | Value |
|-------|-------|
| Test name | year divisible by 2, not divisible by 4 in common year |
| UUID in `tests.toml` | `ac227e82-ee82-4a09-9eb6-4f84331ffdb0` |
| Input | `Test-LeapYear(1970)` |
| Expected | `False` |
| Mutant returns | `True` |

Running the suite against the mutant: 8 tests pass and 1 fails (this one). The other named case, "year not divisible by 4 in common year" (2015), still passes on the mutant because odd years are rejected either way, so it does not distinguish this mutant.

## Smallest diagnostic input

The smallest positive year on which the original and the mutant differ is `2`: the original returns `False`, the mutant returns `True`. The suite already rejects the mutant (with 1970), so no new case is proposed.

## Reproduce

From the repository root (coursework fork only; `work/` is not part of any upstream change):

~~~
python3 work/R09-T013/check.py
~~~

## Known wording difference

`.meta/tests.toml` names one case "year divisible by 400 is leap year", while `LeapYear.tests.ps1` names the matching test "year divisible by 400 in leap year" (input `2000`, expected `True`). It is the only name that differs, and only in wording. The check matches the two through this documented pair and still requires every other name to be identical. The test file is not edited here.
