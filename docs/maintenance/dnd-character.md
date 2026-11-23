# Maintenance Guide: DnD Character (`dnd-character`)

## Canonical Test Case Coverage & Mapping

This document tracks the canonical test cases defined in Exercism's problem specifications for `dnd-character` and explains how they map to PowerShell implementations and test assertions in `exercises/practice/dnd-character/DndCharacter.tests.ps1`.

### Canonical Test Mapping Table

| Canonical UUID | Description | Status | PowerShell Target / Implementation | Rationale |
|---|---|---|---|---|
| `1e9ae1dc-35bd-43ba-aa08-e4b94c20fa37` | ability modifier for score 3 is -4 | Included | `[Character]::GetModifier(3)` | Direct static method calculation: `[Math]::Floor(($Score - 10)/2)` |
| `cc9bb24e-56b8-4e9e-989d-a0d1a29ebb9c` | ability modifier for score 4 is -3 | Included | `[Character]::GetModifier(4)` | Direct static method calculation: `[Math]::Floor(($Score - 10)/2)` |
| `5b519fcd-6946-41ee-91fe-34b4f9808326` | ability modifier for score 5 is -3 | Included | `[Character]::GetModifier(5)` | Direct static method calculation: `[Math]::Floor(($Score - 10)/2)` |
| `dc2913bd-6d7a-402e-b1e2-6d568b1cbe21` | ability modifier for score 6 is -2 | Included | `[Character]::GetModifier(6)` | Direct static method calculation: `[Math]::Floor(($Score - 10)/2)` |
| `099440f5-0d66-4b1a-8a10-8f3a03cc499f` | ability modifier for score 7 is -2 | Included | `[Character]::GetModifier(7)` | Direct static method calculation: `[Math]::Floor(($Score - 10)/2)` |
| `cfda6e5c-3489-42f0-b22b-4acb47084df0` | ability modifier for score 8 is -1 | Included | `[Character]::GetModifier(8)` | Direct static method calculation: `[Math]::Floor(($Score - 10)/2)` |
| `c70f0507-fa7e-4228-8463-858bfbba1754` | ability modifier for score 9 is -1 | Included | `[Character]::GetModifier(9)` | Direct static method calculation: `[Math]::Floor(($Score - 10)/2)` |
| `6f4e6c88-1cd9-46a0-92b8-db4a99b372f7` | ability modifier for score 10 is 0 | Included | `[Character]::GetModifier(10)` | Direct static method calculation: `[Math]::Floor(($Score - 10)/2)` |
| `e00d9e5c-63c8-413f-879d-cd9be9697097` | ability modifier for score 11 is 0 | Included | `[Character]::GetModifier(11)` | Direct static method calculation: `[Math]::Floor(($Score - 10)/2)` |
| `eea06f3c-8de0-45e7-9d9d-b8cab4179715` | ability modifier for score 12 is +1 | Included | `[Character]::GetModifier(12)` | Direct static method calculation: `[Math]::Floor(($Score - 10)/2)` |
| `9c51f6be-db72-4af7-92ac-b293a02c0dcd` | ability modifier for score 13 is +1 | Included | `[Character]::GetModifier(13)` | Direct static method calculation: `[Math]::Floor(($Score - 10)/2)` |
| `94053a5d-53b6-4efc-b669-a8b5098f7762` | ability modifier for score 14 is +2 | Included | `[Character]::GetModifier(14)` | Direct static method calculation: `[Math]::Floor(($Score - 10)/2)` |
| `8c33e7ca-3f9f-4820-8ab3-65f2c9e2f0e2` | ability modifier for score 15 is +2 | Included | `[Character]::GetModifier(15)` | Direct static method calculation: `[Math]::Floor(($Score - 10)/2)` |
| `c3ec871e-1791-44d0-b3cc-77e5fb4cd33d` | ability modifier for score 16 is +3 | Included | `[Character]::GetModifier(16)` | Direct static method calculation: `[Math]::Floor(($Score - 10)/2)` |
| `3d053cee-2888-4616-b9fd-602a3b1efff4` | ability modifier for score 17 is +3 | Included | `[Character]::GetModifier(17)` | Direct static method calculation: `[Math]::Floor(($Score - 10)/2)` |
| `bafd997a-e852-4e56-9f65-14b60261faee` | ability modifier for score 18 is +4 | Included | `[Character]::GetModifier(18)` | Direct static method calculation: `[Math]::Floor(($Score - 10)/2)` |
| `4f28f19c-2e47-4453-a46a-c0d365259c14` | random ability is within range | Included | `$character.Ability()` | Range check: 3 <= ability <= 18 |
| `385d7e72-864f-4e88-8279-81a7d75b04ad` | random character is valid | Included | `[Character]::New()` | Validates all 6 ability properties and HitPoints calculation |
| `2ca77b9b-c099-46c3-a02c-0d0f68ffa0fe` | each ability is only calculated once | **Excluded** (`include = false`) | Replaced by `dca2b2ec-f729-4551-84b9-078876bb4808` | Canonical test replaced by track-specific test. In PowerShell, abilities are assigned as class instance properties in the constructor. Repeated member accesses return stable values. |
| `dca2b2ec-f729-4551-84b9-078876bb4808` | each ability is only calculated once | Included (`reimplements`) | `$character.<Ability> \| Should -BeExactly $character.<Ability>` | Re-implements `2ca77b9b-c099-46c3-a02c-0d0f68ffa0fe` to verify property stability upon consecutive reads. |

### Rationale for Exclusion of `2ca77b9b-c099-46c3-a02c-0d0f68ffa0fe`

In Exercism's canonical problem-specifications, the test `each ability is only calculated once` expects abilities to remain invariant after initial creation.

In languages with dynamic getters or function-based properties, this test checks that calling a property or method repeatedly does not re-roll dice. In PowerShell, `Class Character` stores abilities as standard class fields:
```powershell
Class Character {
    [int]$Strength
    [int]$Dexterity
    [int]$Constitution
    [int]$Intelligence
    [int]$Wisdom
    [int]$Charisma
    [int]$HitPoints
    ...
}
```
Because PowerShell fields are assigned in `Character()` via `$this.Strength = $this.Ability()`, they are not recalculated on property read. The PowerShell track provides a track-specific replacement test (`dca2b2ec-f729-4551-84b9-078876bb4808`) that asserts:
```powershell
It "each ability is calculated once" {
    $character = [Character]::New()

    $character.Strength     | Should -BeExactly $character.Strength
    $character.Dexterity    | Should -BeExactly $character.Dexterity
    $character.Constitution | Should -BeExactly $character.Constitution
    $character.Intelligence | Should -BeExactly $character.Intelligence
    $character.Wisdom       | Should -BeExactly $character.Wisdom
    $character.Charisma     | Should -BeExactly $character.Charisma
}
```
Therefore, `2ca77b9b-c099-46c3-a02c-0d0f68ffa0fe` is properly marked `include = false` with a `reimplements` entry to avoid duplicate or misaligned canonical generators.
