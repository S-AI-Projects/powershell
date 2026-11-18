# Hints

## Contract & Decision Table

The `square-root` exercise specifies calculating the integer square root of a given positive integer without using built-in math functions like `[Math]::Sqrt()`.

### Specification Scope vs. Unspecified Inputs

| Input Condition | Domain Example | Required Result | Contract Status |
|---|---|---|---|
| Single unit square | `Radicand = 1` | `1` ($1^2 = 1$) | Specified & Tested (`root of 1`) |
| Small even square | `Radicand = 4` | `2` ($2^2 = 4$) | Specified & Tested (`root of 4`) |
| Medium squares | `Radicand = 25`, `81`, `196` | `5`, `9`, `14` | Specified & Tested |
| Large integer square | `Radicand = 65025` | `255` ($255^2 = 65025$) | Specified & Tested (`root of 65025`) |
| Non-perfect squares | `Radicand = 2`, `3`, `5` | N/A | **Unspecified**: The specification explicitly states you are only required to handle cases where the result is a positive whole number. No fractional or floating-point rounding is required. |
| Non-positive integers | `Radicand <= 0` | N/A | **Unspecified**: Inputs are guaranteed to be natural numbers ($N \ge 1$); no error or exception throwing is mandated. |

### Case Walkthroughs

#### 1. Case: `root of 1`
- **Input**: `-Radicand 1`
- **Analysis**: $1 \times 1 = 1$. The smallest positive integer radicand yields $1$.
- **PowerShell Call**:
  ```powershell
  Get-SquareRoot -Radicand 1 # Returns 1
  ```

#### 2. Case: `root of 4`
- **Input**: `-Radicand 4`
- **Analysis**: $2 \times 2 = 4$.
- **PowerShell Call**:
  ```powershell
  Get-SquareRoot -Radicand 4 # Returns 2
  ```

### Implementation Strategies
Because pre-existing math libraries should be avoided:
- **Binary Search**: Search within $1 \le x \le \text{Radicand}$, evaluating $x \times x$ against $\text{Radicand}$.
- **Heron's / Newton's Method**: Iteratively refine $x_{k+1} = \frac{1}{2}(x_k + \frac{\text{Radicand}}{x_k})$ using integer arithmetic.
- **Binary Bit-by-Bit Shift**: As implemented in the reference solution, shift bits to determine the root digit-by-digit in $O(\log N)$ time.
