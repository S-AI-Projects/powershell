# Say: canonical case mapping

Maps selected UUIDs in `exercises/practice/say/.meta/tests.toml` to the tests in `exercises/practice/say/Say.tests.ps1` and to the reference in `exercises/practice/say/.meta/Say.example.ps1`.

| UUID | Test name | Call | Expected (`Should -BeExactly`) | Reference behavior |
|------|-----------|------|--------------------------------|--------------------|
| `5d22a120-ba0c-428c-bd25-8682235d83e8` | zero | `Invoke-Say -Number 0` | `zero` | Early return for numbers below 20 yields `$ONES[0]` |
| `9b5eed77-dbf6-439d-b920-3f7eb58928f6` | one | `Invoke-Say -Number 1` | `one` | Early return for numbers below 20 yields `$ONES[1]` |
| `7c499be1-612e-4096-a5e1-43b2f719406d` | fourteen | `Invoke-Say -Number 14` | `fourteen` | Early return for numbers below 20 yields `$ONES[14]` |

## Case counts

All 19 canonical cases are included and none are excluded. This is unchanged by the rationale comments.
