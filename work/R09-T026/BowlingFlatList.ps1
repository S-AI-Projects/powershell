<#
Alternative BowlingGame implementation using flat roll list indexing.
#>
Class BowlingGame {
    [System.Collections.Generic.List[int]] hidden $rolls
    [int] hidden $frame
    [int] hidden $rollInFrame
    [bool] hidden $isComplete

    BowlingGame() {
        $this.rolls = [System.Collections.Generic.List[int]]::new()
        $this.frame = 1
        $this.rollInFrame = 1
        $this.isComplete = $false
    }

    [void] Roll([int]$pins) {
        if ($pins -lt 0 -or $pins -gt 10) {
            Throw "Invalid number of pins"
        }
        if ($this.isComplete) {
            Throw "Game is already finished"
        }

        if ($this.frame -lt 10) {
            if ($this.rollInFrame -eq 1) {
                if ($pins -eq 10) {
                    $this.rolls.Add($pins)
                    $this.frame++
                } else {
                    $this.rolls.Add($pins)
                    $this.rollInFrame = 2
                }
            } else {
                $firstRoll = $this.rolls[$this.rolls.Count - 1]
                if ($firstRoll + $pins -gt 10) {
                    Throw "Two rolls in a frame cannot score more than 10 points"
                }
                $this.rolls.Add($pins)
                $this.frame++
                $this.rollInFrame = 1
            }
        } else {
            # 10th frame
            $tenthFrameRolls = $this.rolls.Count - $this.GetStartOfTenthFrame()
            if ($tenthFrameRolls -eq 0) {
                $this.rolls.Add($pins)
            } elseif ($tenthFrameRolls -eq 1) {
                $r1 = $this.rolls[$this.rolls.Count - 1]
                if ($r1 -lt 10 -and $r1 + $pins -gt 10) {
                    Throw "Two rolls in a frame cannot score more than 10 points"
                }
                $this.rolls.Add($pins)
                if ($r1 -lt 10 -and ($r1 + $pins -lt 10)) {
                    $this.isComplete = $true
                }
            } elseif ($tenthFrameRolls -eq 2) {
                $r1 = $this.rolls[$this.rolls.Count - 2]
                $r2 = $this.rolls[$this.rolls.Count - 1]
                if ($r1 -eq 10 -and $r2 -lt 10 -and ($r2 + $pins -gt 10)) {
                    Throw "Two bonus rolls after a strike cannot score more than 10 points"
                }
                $this.rolls.Add($pins)
                $this.isComplete = $true
            } else {
                Throw "Cannot roll after game complete"
            }
        }
    }

    [int] hidden GetStartOfTenthFrame() {
        $idx = 0
        for ($f = 1; $f -lt 10; $f++) {
            if ($this.rolls[$idx] -eq 10) {
                $idx += 1
            } else {
                $idx += 2
            }
        }
        return $idx
    }

    [int] Score() {
        if ($this.rolls.Count -eq 0) {
            Throw "Game has not started"
        }
        if (-not $this.isComplete) {
            Throw "Game is incomplete"
        }

        $total = 0
        $idx = 0
        for ($f = 1; $f -le 10; $f++) {
            if ($this.rolls[$idx] -eq 10) {
                # Strike
                $total += 10 + $this.rolls[$idx + 1] + $this.rolls[$idx + 2]
                $idx += 1
            } elseif ($this.rolls[$idx] + $this.rolls[$idx + 1] -eq 10) {
                # Spare
                $total += 10 + $this.rolls[$idx + 2]
                $idx += 2
            } else {
                # Open frame
                $total += $this.rolls[$idx] + $this.rolls[$idx + 1]
                $idx += 2
            }
        }
        return $total
    }
}
