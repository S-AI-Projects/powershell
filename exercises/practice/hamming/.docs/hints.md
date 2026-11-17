# Hints

## General

- The Hamming distance measures the number of **differences** (mismatches) between corresponding characters of two equal-length strands, not the number of matches or identical positions.
- Remember that two identical strands of any length (for example, `'A'` and `'A'`) have a distance of `0` because there are zero mismatched nucleotides.
- When iterating through characters by index, check that your comparison increments the counter only when characters differ (`-ne`), rather than when they match (`-eq`).
- Small diagnostic input: testing `'A'` against `'A'` should return `0`. If your solution returns `1`, verify your equality/inequality condition inside the loop.
