# Hints

## Choosing an output approach

For this exercise's fixed greeting, returning the literal is the clearest choice: it creates one string and directly expresses the required output. If a greeting were assembled from many pieces over time, a `System.Text.StringBuilder` could hold those pieces in a mutable buffer and produce one final string. For example, appending `"Hello, "` and `"World!"` yields `"Hello, World!"`. A builder adds an object and method calls, so it is unnecessary overhead for this one constant greeting; it becomes useful when code repeatedly assembles a longer string.
