# Hints

## Understanding the contract

The `all-your-base` exercise converts a positional number represented as an array of digit values from an `InputBase` to an `OutputBase`.

### Representation and ordering in PowerShell

1. **Digits as arrays**: Both inputs and outputs are arrays of integer digits (`[int[]]`). In positional notation, digits are ordered from most significant to least significant (big-endian).
2. **Single-element arrays**: When the output is a single digit (such as `5` or `1`), PowerShell can unwrap single-element pipelines into scalars. Always ensure the returned output is wrapped in an array `@(...)` so that tests using `Should -BeExactly $want` (where `$want` is an array) succeed.
3. **Zeros**: The number zero in any base is represented as a single zero digit `@(0)`. Leading zeros should not be present in the output.

### Walkthrough of selected cases

#### 1. Single bit one to decimal
- **Input**: `Digits = @(1)`, `InputBase = 2`, `OutputBase = 10`
- **Conversion**:
  - Evaluation in base 2: $1 \times 2^0 = 1$.
  - Decimal value $1$ converted to base 10 produces digit sequence $[1]$ since $1 = 1 \times 10^0$.
- **Expected Output**: `@(1)`

#### 2. Binary to single decimal
- **Input**: `Digits = @(1, 0, 1)`, `InputBase = 2`, `OutputBase = 10`
- **Conversion**:
  - Evaluation in base 2: $1 \times 2^2 + 0 \times 2^1 + 1 \times 2^0 = 4 + 0 + 1 = 5$.
  - Decimal value $5$ converted to base 10 produces digit sequence $[5]$ since $5 = 5 \times 10^0$.
- **Expected Output**: `@(5)`

### Error handling requirements

The specification explicitly requires throwing an error (`Throw`) in these conditions:
- `InputBase < 2`: an input base must be at least 2.
- `OutputBase < 2`: an output base must be at least 2.
- Any digit in `Digits` is negative ($< 0$) or not valid in the input base ($\ge \text{InputBase}$).
