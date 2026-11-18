# Hints

## Approach Selection: Gather vs. Scatter

When annotating the flower field, two main algorithmic paradigms can be chosen:

### Approach 1: Cell Inspection (Gathering)
- **Data Representation**: Convert the input strings to a jagged character array (`char[][]`).
- **Control Flow**: Iterate through every cell $(r, c)$. If the cell is empty (`' '`), inspect its up to 8 surrounding neighbors $(\Delta r \in \{-1, 0, 1\}, \Delta c \in \{-1, 0, 1\})$, count how many flowers (`*`) are found, and update the character in place if the count is greater than zero.
- **Trade-off**: Minimal additional memory overhead, but examines neighbors for all empty cells regardless of flower density.

### Approach 2: Accumulator Grid (Scattering)
- **Data Representation**: Allocate a 2D integer count matrix `[int[,]]` sized to the board's dimensions ($R \times C$).
- **Control Flow**: Iterate across the board. Whenever a flower (`*`) is located at $(r, c)$, increment each of its 8 valid adjacent neighbors in the accumulator grid. In a final pass, reconstruct each row by taking `'*'` where flowers exist, the count character where count > 0, or `' '` otherwise.
- **Trade-off**: Requires $O(R \times C)$ extra integer memory, but only performs neighbor lookups for actual flower locations, making it especially efficient when flowers are sparse.

### Worked Example: `@(" * * ")`
Consider single-row garden `@(" * * ")` (length 5):
1. **Index 0 (`' '`)**: Neighbor at index 1 is `'*'`. Total adjacent = `1`.
2. **Index 1 (`'*'`)**: Contains a flower, remains `'*'`.
3. **Index 2 (`' '`)**: Neighbors at index 1 and 3 are both `'*'`. Total adjacent = `2`.
4. **Index 3 (`'*'`)**: Contains a flower, remains `'*'`.
5. **Index 4 (`' '`)**: Neighbor at index 3 is `'*'`. Total adjacent = `1`.
- **Result**: `@("1*2*1")`.
