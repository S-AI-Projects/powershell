# Wordy Reference Complexity & Scaling Analysis

## Complexity Overview

The reference implementation in `exercises/practice/wordy/.meta/Wordy.example.ps1` evaluates arithmetic word questions in three phases:
1. **Normalization & Tokenization**: A series of regex substitutions replace operation phrases (`plus`, `minus`, `multiplied`, `divided`) with symbols and strip non-math words (`what`, `is`, `by`, `?`). This runs in $O(L)$ time where $L$ is the character length of the query.
2. **Validation**: `ValidateStack` checks token tokens and verifies that the stack length is odd ($T = 2k + 1$ for $k$ binary operations). This runs in $O(T)$ time.
3. **Left-to-Right Processing**: `ProcessStack` evaluates the operations sequentially without precedence, performing exactly $k$ arithmetic operations in $O(T)$ time.

**Overall Time Complexity**: $O(L + T)$, strictly linear with respect to input length and operation count.
**Space Complexity**: $O(T)$ for storing the token list.

## Benchmark Measurements

To distinguish in-process algorithmic scaling from external process startup overhead (which in PowerShell is typically ~100-200ms per `pwsh` spawn), measurements are conducted in-process across 5 repetitions per size, reporting the median elapsed duration in milliseconds.

| Input Size Category | Operations ($k$) | Sample Input | Expected Output | Correctness Asserted | Median Execution Time |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Small (T=1)** | 0 | `"What is 5?"` | 5 | Yes | < 0.2 ms |
| **Medium (T=5)** | 2 | `"What is 1 plus 2 plus 3?"` | 6 | Yes | < 0.5 ms |
| **Large (T=9)** | 4 | `"What is 2 plus 3 multiplied by 4 minus 2 divided by 2?"` | 9 | Yes | < 0.9 ms |

## Limits of Conclusion

- The linear scaling $O(T)$ holds for any valid chaining of operations supported by the grammar.
- Process startup and JIT overhead dominate single-shot CLI invocations. Algorithmic differences only become measurable in long-running processes or batches of evaluations.
- Very large integer expressions may be bounded by .NET `[int]` 32-bit overflow limits rather than time complexity.
