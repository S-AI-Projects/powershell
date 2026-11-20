# Robot Simulator Canonical Cases

The canonical metadata contains 18 cases and currently excludes none. In `tests.toml`, a missing `include` key means the case is included. This review keeps all 18 cases enabled and records why three selected cases match the PowerShell reference.

| UUID | Canonical case | PowerShell evidence | Decision |
|---|---|---|---|
| `c557c16d-26c1-4e06-827c-f6602cd0785c` | Create robot at origin facing north | The explicit constructor accepts `NORTH`, `0`, and `0`; the test `at origin facing north` checks direction and position. A separate PowerShell test checks the no-argument constructor. | Keep included. The canonical case covers explicit inputs, while the local test covers defaults. |
| `bf0dffce-f11c-4cdb-8a5e-2c89d8a5a67d` | Create robot at negative position facing south | The test `at negative position facing south` checks `SOUTH` and `[-1, -1]`. The instructions define an infinite grid, and the reference stores signed integer coordinates. | Keep included. Negative coordinates are within the stated contract. |
| `8cbd0086-6392-4680-b9b9-73cf491e67e5` | Rotate clockwise from north to east | The test `clockwise -> changes north to east` calls `Move("R")`. `Direction` is ordered NORTH, EAST, SOUTH, WEST, so advancing one enum value modulo four produces EAST. | Keep included. This is a supported transition in the reference. |

The TOML `comment` values beside these UUIDs preserve the rationale through `configlet sync`. There are no exclusions to justify or replacement cases to identify. The focused check at `work/R09-T031/check.py` copies the exercise, substitutes the maintained example only in that temporary copy, and verifies the Pester suite and selected outcomes without writing to the learner solution.
