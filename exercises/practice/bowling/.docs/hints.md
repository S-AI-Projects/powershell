# Hints

## Approach Selection

When modeling a bowling game in PowerShell, two main data representation strategies can be used:

### 1. Frame-Centric Linked Structure (Reference Approach)
- **Data Representation**: A dedicated `Frame` class holding frame number, throw collection, completion status, and a pointer (`$this.Next`) to the subsequent frame.
- **Trade-offs**:
  - *Pros*: Direct modeling of the domain rules (10 discrete frames, frame-level validation, bonus roll rules isolated in the 10th frame).
  - *Cons*: Additional class hierarchy, pointer manipulation, and higher object allocation overhead in PowerShell.

### 2. Flat Roll List Indexing (Array/List Approach)
- **Data Representation**: A flat `[System.Collections.Generic.List[int]]` accumulating individual pin values sequentially.
- **Trade-offs**:
  - *Pros*: Minimal memory footprint, fast append operations during `Roll()`, and concise scoring via index pointers.
  - *Cons*: Scoring must maintain an explicit roll index `i` that advances by 1 on strikes and by 2 on open frames/spares, requiring careful bounds checking for bonus balls.

### Worked Example: Open Frame Scoring
Consider a game where the first two rolls are `3` and `6`, followed by zeros:
- **Frame-Centric**: Frame 1 records throws `[3, 6]` with frame score `9`. The frame is marked complete. Subsequent rolls populate frames 2 through 10. `Score()` sums each frame directly: `9 + 0 + ... = 9`.
- **Flat List**: Rolls are stored as `[3, 6, 0, 0, ...]`. During scoring at frame 1 (`i = 0`), since `rolls[0] + rolls[1] < 10`, frame score is `rolls[0] + rolls[1] = 9`, and `i` advances to `i + 2 = 2`. Total score is `9`.
