# Maintenance Notes: all-your-base

## Exercise metadata

- Track: PowerShell
- Slug: `all-your-base`
- Exercise directory: `exercises/practice/all-your-base/`
- Reference implementation: `exercises/practice/all-your-base/.meta/AllYourBase.example.ps1`

## Specification Derivation and Decision Table (R09-T060)

### Derivation for Selected Cases

#### 1. `single bit one to decimal`
- **Inputs**: `Digits = @(1)`, `InputBase = 2`, `OutputBase = 10`
- **Mathematical derivation**:
  - Value: $1 \times 2^0 = 1$.
  - In base 10: $1 = 1 \times 10^0$.
- **Expected outcome**: `@(1)`
- **Contract status**: Specified.

#### 2. `binary to single decimal`
- **Inputs**: `Digits = @(1, 0, 1)`, `InputBase = 2`, `OutputBase = 10`
- **Mathematical derivation**:
  - Value: $1 \times 2^2 + 0 \times 2^1 + 1 \times 2^0 = 4 + 0 + 1 = 5$.
  - In base 10: $5 = 5 \times 10^0$.
- **Expected outcome**: `@(5)`
- **Contract status**: Specified.

---

### Decision Table

| Condition | Input `Digits` | `InputBase` | `OutputBase` | Required Outcome | Contract Status |
|-----------|----------------|-------------|--------------|------------------|-----------------|
| Single bit one | `@(1)` | `2` | `10` | `@(1)` | **Specified** |
| Multi-digit binary to single decimal | `@(1, 0, 1)` | `2` | `10` | `@(5)` | **Specified** |
| General valid conversion | Non-empty digits $\in [0, \text{InputBase}-1]$ | $\ge 2$ | $\ge 2$ | Positional digits in `OutputBase` | **Specified** |
| Zero value (single/multiple/leading) | `@(0)` or `@(0,0)` | $\ge 2$ | $\ge 2$ | `@(0)` | **Specified** |
| Empty digit list | `@()` | $\ge 2$ | $\ge 2$ | `@(0)` | **Specified** |
| Invalid input base | Any | $< 2$ | $\ge 2$ | Throw exception (`"input base must be >= 2"`) | **Specified** |
| Invalid output base | Any | $\ge 2$ | $< 2$ | Throw exception (`"output base must be >= 2"`) | **Specified** |
| Invalid digit value | Contains $< 0$ or $\ge \text{InputBase}$ | $\ge 2$ | $\ge 2$ | Throw exception (`"all digits must satisfy 0 <= digit < input base"`) | **Specified** |
| Non-integer / fractional base | e.g. `2.5` | Unspecified | Unspecified | Undefined / Unspecified | **Out-of-Contract** |
| Non-array argument | e.g. `"101"` | Unspecified | Unspecified | Undefined / Unspecified | **Out-of-Contract** |

---

### Explicit Statement on Unspecified Behavior

The exercise specification defines behavior strictly for positional integer digits across integer bases $\ge 2$.

The following behaviors are **unspecified** by the canonical specification:
1. **Non-integer bases or digits**: Passing floating-point values, complex numbers, or non-numeric types is outside the exercise contract. Implementations are not required to provide custom coercion or error messages for these inputs.
2. **Specific exception classes or message text**: The track requires throwing an error (`Throw`) on invalid bases or invalid digits; no specific .NET exception type hierarchy is mandated.
3. **Alternative input collections**: Inputs are specified as collections of integer digits. Passing formatted strings or non-enumerable objects is out-of-contract.

Maintainers and learners should **not** impose arbitrary extra validations, coercions, or ordering requirements beyond the canonical test suite.
