# pig-latin: cost of the reference

Cost study of `exercises/practice/pig-latin/.meta/PigLatin.example.ps1`. It describes how computational work scales with input size. It does not claim the reference is fast or slow, and no speedup is claimed.

## Input size

In Pig Latin, the input is an English word or space-separated phrase. The natural measure of input size is:
- $w$: the number of space-delimited words in the input phrase.
- $N$: total character length of the input ($N \approx w \times m$, where $m$ is the average word length).

This study evaluated three input sizes across the problem domain:
- $w = 10$ words (phrase composed of 10 representative words spanning all phonetic rules: vowels, consonants, clusters, `y`, and `qu`)
- $w = 100$ words (10 repetitions of the representative word list)
- $w = 1000$ words (100 repetitions of the representative word list)

## What each part costs

| Operation | Complexity | Description |
|-----------|------------|-------------|
| `$Text -split " "` | $O(N)$ | Splits the input string into an array of $w$ word tokens. |
| `ForEach-Object` pipeline | $O(N)$ | Processes each word of length $L_i$: evaluates an anchored regex match ($O(L_i)$ deterministic matching with no catastrophic backtracking) and string concatenation (`$Matches[2] + $Matches[1] + 'ay'`). |
| `$translated -join " "` | $O(N)$ | Concatenates the $w$ translated words back into a single space-separated string. |

Overall time complexity is $O(N)$, which is linear in total characters, or $O(w)$ for words of bounded length. Auxiliary memory complexity is $O(N)$ to hold the split tokens and output string.

## Measurement

Representative word sequence: `"quick fast run apple pig chair queen rhythm yellow under"` (contains 10 words exercising rules 1 through 4).

Before timing, correctness is asserted by verifying that `Invoke-PigLatin` translates `"quick fast run"` to `"ickquay astfay unray"`.

Each size is measured 7 times inside an active PowerShell process after the function definition is loaded, reporting the median, minimum, and maximum elapsed times.

| $w$ (words) | Median (ms) | Min (ms) | Max (ms) |
|---|---|---|---|
| 10 | 0.20 | 0.19 | 0.50 |
| 100 | 0.86 | 0.82 | 4.30 |
| 1000 | 8.51 | 8.27 | 8.99 |

Ratio of medians:
- $w = 100$ vs $w = 10$: $\approx 4.3\times$ (dominated by pipeline overhead at small $w$)
- $w = 1000$ vs $w = 100$: $\approx 9.9\times$ (approaches expected linear scaling factor of 10)

## Algorithm work versus process startup

Starting PowerShell took a median of ~66 ms, and defining the function took an additional ~10 ms. In comparison, executing the function on a 100-word phrase takes under 1 ms. Isolating algorithmic measurement from process startup is essential; measuring full process execution would measure PowerShell startup rather than algorithmic work.

## Limits of the conclusion

- Three input sizes, 7 repetitions, single execution environment (macOS, PowerShell 7.7.0).
- At smaller sizes ($w \le 10$), PowerShell cmdlet and pipeline invocation overhead constitutes a significant portion of execution time, resulting in lower ratios than the theoretical $10\times$. At larger sizes ($w \ge 100$), string processing dominates and exhibits near-linear $O(w)$ scaling.
- No algorithmic optimization or speedup is claimed; the study documents the baseline computational characteristics of the reference implementation.

## Reproduce

```bash
python3 work/R09-T055/check.py
```
