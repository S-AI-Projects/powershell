# Bob Exercise Maintenance & Test Generation

## Overview
This document specifies the test-generation and synchronization route from `exercises/practice/bob/.meta/tests.toml` to `exercises/practice/bob/BobResponse.tests.ps1` in the Exercism PowerShell track.

## Track Test Generation Architecture
In the Exercism PowerShell track:
- Canonical test specifications originate from Exercism's `problem-specifications/exercises/bob/canonical-data.json`.
- `configlet sync --tests -e bob` syncs upstream canonical UUIDs into `exercises/practice/bob/.meta/tests.toml`.
- While some tracks use Jinja2 templates (`.meta/template.j2`), the PowerShell track maintains track-idiomatic Pester test suites (`BobResponse.tests.ps1`) directly mapped to the canonical cases recorded in `tests.toml`.

## Exact Generation & Synchronization Commands

### 1. Synchronize Canonical Data & tests.toml
```bash
bin/configlet sync --tests -e bob
```
This inspects the cached `problem-specifications` repository and updates `.meta/tests.toml`, preserving track-specific `include = false` or `comment` entries.

### 2. Verify Exercise Configuration & Formatting
```bash
bin/configlet lint -e bob
bin/configlet fmt -e bob --update
```

### 3. Automated Route & Regeneration Verification
```bash
python3 tools/course_checks/r09-t002.py
# or
python3 work/R09-T002/check.py
```

## Input and Maintained Files

| Role | Path | Generated / Maintained | Purpose |
|---|---|---|---|
| Canonical Specification | `problem-specifications/exercises/bob/canonical-data.json` | Upstream Reference | Defines canonical cases and UUIDs |
| Exercise Configuration | `exercises/practice/bob/.meta/config.json` | Maintained by hand | Declares authors, files, and blurb |
| Test Manifest | `exercises/practice/bob/.meta/tests.toml` | Synced via `configlet` | Records inclusion/exclusion per UUID |
| Test Suite | `exercises/practice/bob/BobResponse.tests.ps1` | Maintained Pester suite | Executable Pester 5/6 test assertions |
| Reference Solution | `exercises/practice/bob/.meta/BobResponse.example.ps1` | Maintained by hand | Exemplar reference implementation |
| Learner Solution | `exercises/practice/bob/BobResponse.ps1` | Maintained starter stub | Unsolved initial code with `Throw` |

## Case-to-Output Mapping

The Pester test suite uses the root Describe block:
```powershell
Describe "Test Get-BobResponse" { ... }
```

### Anchor Cases

| Case Name | Canonical UUID | Input (`-HeyBob`) | Expected Output | Assertion in `BobResponse.tests.ps1` |
|---|---|---|---|---|
| **Describe Block** | N/A | N/A | N/A | `Describe "Test Get-BobResponse"` |
| **asking a question** | `8a2e771d-d6f1-4e3f-b6c6-b41495556e37` | `"Does this cryogenic chamber make me look fat?"` | `"Sure."` | `Get-BobResponse -HeyBob "Does this cryogenic chamber make me look fat?" \| Should -BeExactly "Sure."` |
| **shouting** | `73a966dc-8017-47d6-bb32-cf07d1a5fcd9` | `"WATCH OUT!"` | `"Whoa, chill out!"` | `Get-BobResponse -HeyBob "WATCH OUT!" \| Should -BeExactly "Whoa, chill out!"` |

### Complete Mapping Table

| Canonical UUID | Canonical Description | In tests.ps1 |
|---|---|---|
| `8a2e771d-d6f1-4e3f-b6c6-b41495556e37` | asking a question | Yes (`"Sure."`) |
| `73a966dc-8017-47d6-bb32-cf07d1a5fcd9` | shouting | Yes (`"Whoa, chill out!"`) |
| `a5193c61-4a92-4f68-93e2-f554eb385ec6` | forceful question | Yes (`"Calm down, I know what I'm doing!"`) |
| `bc39f7c6-f543-41be-9a43-fd1c2f753fc0` | silence | Yes (`"Fine. Be that way!"`) |
| `e162fead-606f-437a-a166-d051915cea8e` | stating something | Yes (`"Whatever."`) |
| `81080c62-4e4d-4066-b30a-48d8d76920d9` | asking a numeric question | Yes (`"Sure."`) |
| `2a02716d-685b-4e2e-a804-2adaf281c01e` | asking gibberish | Yes (`"Sure."`) |
| `bb0011c5-cd52-4a5b-8bfb-a87b6283b0e2` | question with no letters | Yes (`"Sure."`) |
| `9bfc677d-ea3a-45f2-be44-35bc8fa3753e` | non-letters with question | Yes (`"Sure."`) |
| `8608c508-f7de-4b17-985b-811878b3cf45` | prattling on | Yes (`"Sure."`) |
| `05b304d6-f83b-46e7-81e0-4cd3ca647900` | ending with whitespace | Yes (`"Sure."`) |
| `66953780-165b-4e7e-8ce3-4bcb80b6385a` | multiple line question (superseded) | Excluded (reimplemented) |
| `2c7278ac-f955-4eb4-bf8f-e33eb4116a15` | multiple line question | Yes (`"Sure."`) |
| `51b2a9e8-466a-4d9f-a88a-d52ea6487e9c` | shouting gibberish | Yes (`"Whoa, chill out!"`) |
| `45ea885a-8b65-4d22-b9e7-40adfbba4817` | shouting a statement containing a question mark | Yes (`"Whoa, chill out!"`) |
| `5c70ba22-83b5-4b08-8e6f-fb94e1e839e9` | shouting numbers | Yes (`"Whoa, chill out!"`) |
| `14f52601-3b74-4b5b-9b43-228bf58a01f6` | shouting with special characters | Yes (`"Whoa, chill out!"`) |
| `b5cf2e5c-0ae1-4470-a35b-1ec627d42ea0` | shouting with no exclamation mark | Yes (`"Whoa, chill out!"`) |
| `b99912ad-fe4f-4d20-b4b1-e24c4382aa7e` | talking forcefully | Yes (`"Whatever."`) |
| `4eb3844a-95ab-4959-9065-ce90d405a396` | prolonged silence | Yes (`"Fine. Be that way!"`) |
| `346452ea-3cb6-47c0-8d54-a32ee01171ca` | alternate silence | Yes (`"Fine. Be that way!"`) |
| `e700a4fb-2786-455b-ab5f-d2e85abdd8df` | multiple line silence | Yes (`"Fine. Be that way!"`) |
| `b248a3f5-674b-4a57-9dbf-193c66f57161` | other whitespace | Yes (`"Fine. Be that way!"`) |
| `0e6b528a-86c5-433b-82cf-e00f9129e794` | non-question ending with whitespace | Yes (`"Whatever."`) |
| `9e4719b2-3e05-4f40-84c1-4ef43d4d420f` | only whitespace | Yes (`"Fine. Be that way!"`) |
| `286aa5a7-76ae-4a8b-a48f-aaee2ecbaef6` | starting with whitespace | Yes (`"Whatever."`) |
