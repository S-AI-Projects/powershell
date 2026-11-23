# Hints

## What the tests require

The instructions say you convert a number from Arabic numerals to Roman numerals, and that the largest number is MMMCMXCIX (3,999). The tests add the details below. Every input and result in the tables comes from `RomanNumerals.tests.ps1`.

### Numbers that have a numeral

The test `Given <Number> it outputs <Result>` runs 27 numbers, from 1 to 3999. Pester compares the returned string with `-BeExactly`, so the result must be exactly the capital letters shown, with nothing added.

| Number | Required result |
|--------|-----------------|
| `1` | `I` |
| `4` | `IV` |
| `9` | `IX` |
| `3999` | `MMMCMXCIX` |

Reading `3999` as `3000 + 900 + 90 + 9` gives `MMM`, `CM`, `XC` and `IX`, which joined in that order is `MMMCMXCIX`. In `4` and `9` a smaller symbol sits before a larger one, so it is subtracted.

### Numbers outside 1 to 3999

| Number | Test | Required result |
|--------|------|-----------------|
| `0` | `Number is zero` | an error |
| `-12` | `Negative number` | an error |
| `9999` | `Number larger than 3999` | an error |

The instructions only say that 3999 is the largest number. They do not say what to do with 0, a negative number or a number above 3999. It is the tests that ask for an error: each one checks that the code throws and that the message matches `*Number has to be positive integer in range of 1-3999.*`, where `*` stands for any text. So the error has to be thrown, not returned, and its message has to contain that sentence.

### Not specified

Nothing in the instructions or the tests says what to do with anything else, for example a decimal number or text, so this hint does not define it.
