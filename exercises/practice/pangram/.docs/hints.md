# Hints

## Choosing an approach

Two distinct representations and control flows work well for determining whether a sentence is a pangram in PowerShell. Both pass all tests; they differ in data representation, memory usage, and early-termination characteristics.

### Approach 1: Input scan with set accumulator (reference technique)

Walk through the characters of the input sentence, filtering for lowercase letters `[a-z]` and collecting each unique letter into a collection (such as an array or HashSet). Once the collection reaches 26 elements, the sentence is confirmed as a pangram.

- **Data representation**: Dynamic collection of seen letters ($O(k)$ auxiliary space where $k \le 26$).
- **Control flow**: Input-driven. The loop processes characters from the sentence until all 26 distinct letters are accumulated or the string ends.
- **Trade-off**: Requires allocating and maintaining a collection of seen letters. In PowerShell with array addition (`+=`), each new character creates a new array copy unless a generic `HashSet[char]` is used.

### Approach 2: Alphabet query with early exit (alternative technique)

Iterate over the 26 letters of the Latin alphabet (`'a'..'z'`). For each letter, query whether the lowercased sentence contains that letter (for example using `.Contains()` or `.IndexOf()`). If any single letter is not found, **immediately return `$false` without inspecting remaining letters**.

- **Data representation**: Fixed 26-character sequence ($O(1)$ auxiliary space beyond the normalized string).
- **Control flow**: Alphabet-driven with early exit. If the sentence is missing an early letter (like `'a'` or `'b'`), the search terminates after only one or two queries.
- **Trade-off**: Very fast rejection for non-pangrams and near-zero auxiliary memory. On full pangrams, it performs 26 substring searches across the sentence.

### Worked example

Consider the sentence: `"The quick brown fox"` (not a pangram, missing several letters including `'a'`).

| Step | Approach 1 (Set Accumulator) | Approach 2 (Alphabet Query) |
|---|---|---|
| Initial state | Seen: `{}` | Alphabet: `'a'..'z'` |
| Processing | Scans `T`, `h`, `e`, ` `, `q`, `u`, ... adds each letter to seen collection. | Checks if sentence contains `'a'`. |
| Finding | Scans all 19 characters, collects 16 distinct letters. | Letter `'a'` is not in `"The quick brown fox"`. |
| Exit point | Loop finishes; checks `Seen.Count == 26` (16 != 26). | **Immediate early return `$false`** after first letter query. |
| Result | `$false` | `$false` |

Notice that Approach 2 rejects the sentence on the very first letter checked, avoiding the work of collecting and deduplicating the other letters.
