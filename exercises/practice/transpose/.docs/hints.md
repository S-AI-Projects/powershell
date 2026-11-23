# Hints

## General

- The spec says shorter rows should be padded on the **right** to match longer rows, but the resulting **output columns** may have a trailing shorter element. The key rule: if a row is shorter than a row that comes **after** it, pad it with spaces. If a row is shorter than a row that comes **before** it (and no later row is longer), do **not** pad — trim trailing spaces from each output row instead.
- If your function drops **leading** spaces from an output row, check your trimming strategy. Only trailing spaces should be removed from each transposed row.
- Try this small input and compare with the expected output:

| Input rows | Expected output rows |
|---|---|
| `"AB"` | `"AD"` |
| `"DEF"` | `"BE"` |
|  | `" F"` ← note the **leading space** |

The last output row `" F"` has a leading space because the first input row (`"AB"`) is shorter than the second (`"DEF"`), so column 2 (0-indexed) has only one character, from the second row, and the missing character from the first row becomes a space.

- Similarly, for input `"The first line."` / `"The second line."`, the last output row is `" ."` — a space followed by a period — because only the second input row has a character at that position.

