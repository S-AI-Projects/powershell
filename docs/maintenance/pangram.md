# Maintenance Notes: pangram

## Exercise metadata

- Track: PowerShell
- Slug: `pangram`
- Exercise directory: `exercises/practice/pangram/`
- Reference implementation: `exercises/practice/pangram/.meta/Pangram.example.ps1`

## Approach Comparison Study (R09-T056)

This study compares two fundamentally distinct algorithmic strategies for satisfying the pangram contract in PowerShell.

### Approach 1: Input scan with set accumulator (Reference technique)

- **Source**: `exercises/practice/pangram/.meta/Pangram.example.ps1`
- **Method**: Converts the input sentence to lowercase, splits into a `char[]` array, and iterates through each character. If a character matches `[a-z]` and has not yet been recorded in `$FoundLetters`, it is appended (`$FoundLetters += $item`). At the end, it checks `$FoundLetters.Count -eq 26`.
- **Complexity**:
  - Time: $O(n \times k)$ where $n$ is sentence length and $k \le 26$ is the current count of unique letters (due to array `-notcontains` scanning).
  - Memory: $O(k)$ auxiliary space for the `$FoundLetters` array. In PowerShell, array concatenation (`+=`) reallocates the array on each insertion.

### Approach 2: Alphabet query with early exit (Alternative technique)

- **Source**: `work/R09-T056/alt/PangramAlt.ps1`
- **Method**: Iterates over the 26 letters of the Latin alphabet (`[char]97..[char]122`). For each letter, it queries whether the lowercased sentence contains that letter using `$lower.Contains($letter)`. If any letter is missing, it immediately short-circuits and returns `$false`.
- **Complexity**:
  - Time: Best case $O(n)$ when the first letter is missing (e.g. empty string or missing `'a'`). Worst case $O(26 \times n)$ for full pangrams.
  - Memory: $O(1)$ auxiliary space beyond the lowercased string.
- **Advantage**: Rejects non-pangrams rapidly with zero memory allocations for tracking seen letters.

### Behavioral Equivalence Verification

Both implementations were tested against all 10 test cases in `Pangram.tests.ps1`:
1. `empty sentence` → both return `$false` (Approach 2 exits at letter `'a'`).
2. `perfect lower case` → both return `$true` (exercises all 26 letters).
3. `only lower case` → both return `$true`.
4. `missing the letter 'x'` → both return `$false`.
5. `missing the letter 'h'` → both return `$false`.
6. `with underscores` → both return `$true`.
7. `with numbers` → both return `$true`.
8. `missing letters replaced by numbers` → both return `$false`.
9. `mixed case and punctuation` → both return `$true`.
10. `a-m and A-M are 26 different characters but not a pangram` → both return `$false`.

Both implementations achieved 100% agreement and 10/10 passing tests.
