# Robot Name Exercise Maintenance

## Canonical Data Status

The `robot-name` exercise does not maintain a `canonical-data.json` file in upstream `exercism/problem-specifications`. Because the exercise involves pseudorandom generation, in-memory state tracking, and collision prevention across instance allocations, tests are defined at track level in `RobotName.tests.ps1`.

- Canonical cases in `tests.toml`: 0
- Excluded canonical cases: 0
- Included canonical cases: 0

## Track Test Case Mapping

| Test Name | Pester Assertion | PowerShell Language Context / Rationale |
| :--- | :--- | :--- |
| `robot has a name` | `Should -MatchExactly "^[A-Z]{2}\d{3}$"` | Validates pattern match on initial instantiation via `[Robot]::new()`. |
| `name is the same each time` | `Should -BeExactly $robot.Name` | Verifies that property getter is idempotent and does not regenerate the name on each access. |
| `different robot has different name` | `Should -Not -Be $robot.Name` | Asserts distinct instances do not receive duplicate identifiers. |
| `name can be reset` | `Should -Not -Be $initialName` | Verifies `.Reset()` invokes internal regeneration, changing the current name. |
| `name is valid after many reset` | Loop 100x checking format and distinctness | Stress test ensuring repeated resets produce valid patterns without crashing. |
| `robot name are unique` | 1000 names added to `[System.Collections.Generic.HashSet[string]]` | Asserts large-batch collision resistance using .NET HashSet. |

## Verification Command

```powershell
pwsh -Command "Invoke-Pester -Path ./exercises/practice/robot-name/RobotName.tests.ps1 -PassThru"
```
