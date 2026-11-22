# Hints

## Choosing an approach

Two representations work for this exercise. Both can pass the tests; they differ in what they keep in memory and in how easy it is to see the rules.

### Pattern plus a running tally

Describe what a word looks like with a regular expression, find every match, and keep a hashtable that maps each lowercased word to its count, adding one for every match. Memory stays proportional to the number of distinct words. The rules are in one pattern, so it is short; the cost is that the pattern is dense and every rule has to fit in it.

### Scan, collect, then group

Walk the phrase one character at a time with an index. Build up each word by hand, put every word in a list, and count the list at the end with `Group-Object`. Memory is proportional to the total number of words, because the list keeps repeats until the end. Each rule is its own `if`, so it is easy to step through and change, but it takes more code.

### Worked example

Take `Go go, can't stop`.

| Step | Pattern plus tally | Scan, collect, group |
|------|--------------------|----------------------|
| Words found, in order | `Go`, `go`, `can't`, `stop` | `Go`, `go`, `can't`, `stop` |
| After lowercasing | `go`, `go`, `can't`, `stop` | `go`, `go`, `can't`, `stop` |
| What is stored | tally: go = 2, can't = 1, stop = 1 | list of 4 words, grouped at the end |
| Result | go = 2, can't = 1, stop = 1 | go = 2, can't = 1, stop = 1 |

### Check numbers with more than one digit

The instructions say numbers are words, so `100` should be one word, not three. A tally that is updated once per matched character can split it. Try `It costs 100 dollars.` and check that `100` appears once.
