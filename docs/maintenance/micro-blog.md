# Maintenance Notes: micro-blog

## Exercise metadata

- Track: PowerShell
- Slug: `micro-blog`
- Exercise directory: `exercises/practice/micro-blog/`
- Reference implementation: `exercises/practice/micro-blog/.meta/MicroBlog.example.ps1`

## Reference Implementation Refactor (R09-T054)

### Problem with baseline implementation

The previous reference implementation had two main readability issues:

1. **Misleading variable name:** It stored the result of `[System.Globalization.StringInfo]::ParseCombiningCharacters($Post)` in a variable named `$charArray`. In .NET, `ParseCombiningCharacters` does **not** return an array of characters; it returns an `int[]` containing the zero-based starting character offsets of each text element (grapheme cluster) in the string. Naming this `$charArray` caused reader confusion by implying each element was a character or string.

2. **Unnecessary iterative extraction and rejoining:** It ran a `while` loop that sliced each individual character via `$Post.Substring($start, $end - $start)`, pushed each substring into an array (`$charList += $character`), and finally executed `-join $charList`. This was computationally wasteful and obscured the underlying invariant: truncation at a grapheme boundary.

### Scoped readability refactor

The refactored reference:
- Renames `$charArray` to `$textElementOffsets`, explicitly communicating that each entry is an integer offset into `$Post`.
- Adds a clear invariant comment:
  `# Invariant: a micro-blog post is limited to at most 5 Unicode text elements (grapheme clusters).`
- Directly inspects the count:
  - If `$textElementOffsets.Length -le 5`, `$Post` already satisfies the constraint and is returned unchanged.
  - Otherwise, the start index of the 6th text element (`$textElementOffsets[5]`) defines the exact truncation boundary, and `$Post.Substring(0, $cutoffOffset)` produces the result in a single, clear operation.

### Verification of Behavioral Equivalence

All 16 test cases in `MicroBlog.tests.ps1` produce byte-identical outputs before and after the refactoring:
- `English language short` ("Hi" → "Hi")
- `English language long` ("Hello there" → "Hello")
- `German language short (broth)` ("brühe" → "brühe")
- `German language long (bear carpet → beards)` ("Bärteppich" → "Bärte")
- `Bulgarian language short (good)` ("Добър" → "Добър")
- `Greek language short (health)` ("υγειά" → "υγειά")
- `Maths short` ("a=πr²" → "a=πr²")
- `Maths long` ("∅⊊ℕ⊊ℤ⊊ℚ⊊ℝ⊊ℂ" → "∅⊊ℕ⊊ℤ")
- `English and emoji short` ("Fly 🛫" → "Fly 🛫")
- `Emoji short` ("💇" → "💇")
- `Emoji long` ("❄🌡🤧🤒🏥🕰😀" → "❄🌡🤧🤒🏥")
- `Royal Flush?` ("🃎🂸🃅🃋🃍🃁🃊" → "🃎🂸🃅🃋🃍")
- `Chess pieces` ("♜♞♝♛♚♟︎" → "♜♞♝♛♚")
- `Zodiac signs` ("♈︎♉︎♊︎♋︎♌︎♍︎♎︎♏︎♐︎♑︎♒︎♓︎" → "♈︎♉︎♊︎♋︎♌︎")
- `Music notes` ("𝄠♭𝅘𝅥𝆕♫♬𝅘𝅥𝅯♯" → "𝄠♭𝅘𝅥𝆕♫")
- `Egyptian Hieroglyphs` ("𓂀𓅁𓅊𓁁☥𓁏" → "𓂀𓅁𓅊𓁁☥")
