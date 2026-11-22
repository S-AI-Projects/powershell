# hangman: cost of the reference

Cost study of `exercises/practice/hangman/.meta/Hangman.example.ps1`. It describes how the work grows with the input. It does not claim the reference is fast or slow, and no speedup is claimed.

## Input size

n is the length of the secret word. The specification does not bound n (the tests use short words such as `test`), so this study picked three sizes: 100, 1000 and 10000 letters. These are much longer than real words and were chosen only to make the growth visible. The number of guesses in a game is bounded separately: a game is lost after 10 wrong or repeated guesses, and each distinct letter can be guessed correctly once.

## What each part costs

| Operation | Work (passes over n) |
|-----------|----------------------|
| `[Hangman]::new` | one pass to build the masked array |
| `Display()` | one pass |
| `GetStatus()` | one pass over the masked array |
| `Guess($char)` | `GetStatus()` plus up to two scans (the second is skipped when the letter is not in the word), plus one more pass when the letter is new and correct |

So a whole game costs about n times (distinct letters + 10). The comment above `Class Hangman` in the reference states this.

## Measurement

Word: `abcdefghij` repeated n/10 times (10 distinct letters). Each timed run creates a game and guesses each of the 10 letters once. Before any timing, the check asserts the result is correct: the display equals the word, the status is WIN and 9 guesses remain. Each size is timed 7 times inside one PowerShell process, after the class is already defined, and the median is reported. Tools: PowerShell 7.7.0, Pester 6.2.0.

| n | median (ms) | min (ms) | max (ms) |
|---|-------------|----------|----------|
| 100 | 0.22 | 0.21 | 4.90 |
| 1000 | 1.10 | 1.08 | 4.25 |
| 10000 | 10.48 | 10.37 | 10.93 |

Ratios of medians for a word 10 times longer: 4.9 (n = 100 to 1000) and 9.5 (n = 1000 to 10000).

Slowest repetition at each size: n=100: repetition 2, n=1000: repetition 4, n=10000: repetition 1. Slow outliers show in the max column; this study did not investigate their cause.

## Algorithm work versus startup

Starting PowerShell took a median of 66 ms, and starting it and defining the class took 76 ms (5 repetitions each). None of this is in the timings above, which are all measured after the class is defined, so startup and class definition are not counted as algorithm cost. Compare them with the medians in the table: timing whole processes would mostly measure startup.

## Limits of the conclusion

- Three sizes, one word shape (10 distinct letters), 7 repetitions and one machine (hardware not recorded). Timings vary from run to run, so rerunning the check gives slightly different numbers.
- For a word 10 times longer, work proportional to n would give a ratio near 10. The measured ratios are given above; a lower ratio at the small end can come from costs that do not depend on n, which this study did not isolate.
- Three points do not prove an exact growth rate. The bound in the reference comment comes from reading the code; the timings are a consistency check, not a proof.
- No speedup is claimed.

## Reproduce

From the repository root (coursework fork only; `work/` is not part of any upstream change):

~~~
python3 work/R09-T015/check.py
~~~
