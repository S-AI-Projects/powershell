# Hints

## Overview & PowerShell Representation

The `Clock` class manages clock times without dates in 24-hour format. Instances are created via `[Clock]::new([int]$hour, [int]$minute)` and converted to strings formatted as `"HH:mm"` using `$clock.ToString()`.

In PowerShell, 2-digit zero-padding can be achieved cleanly with composite string formatting:
```powershell
[string] ToString() {
    return "{0:D2}:{1:D2}" -f $this.Hour, $this.Minute
}
```

## Input/Output Walkthrough for Selected Cases

### 1. "on the hour"
- **Input**: `[Clock]::new(9, 0)`
- **Calculation**: Hour = 9, Minute = 0. Total minutes = $9 \times 60 + 0 = 540$. Normalization within a 1440-minute day gives Hour = 9, Minute = 0.
- **Output (`ToString()`)**: `'09:00'`

### 2. "past the hour"
- **Input**: `[Clock]::new(10, 23)`
- **Calculation**: Hour = 10, Minute = 23. Total minutes = $10 \times 60 + 23 = 623$. Normalization within a 1440-minute day gives Hour = 10, Minute = 23.
- **Output (`ToString()`)**: `'10:23'`

## Contract Decision Table

| Input Condition | Sample Input (`Hour`, `Minute`) | Required String Result | Notes / Contract Status |
| :--- | :--- | :--- | :--- |
| **On the hour** ($0 \le H < 24$, $M = 0$) | `9, 0` | `'09:00'` | Directly formatted with leading zero. |
| **Past the hour** ($0 \le H < 24$, $0 < M < 60$) | `10, 23` | `'10:23'` | Direct hour and minute presentation. |
| **Rollover** ($H \ge 24$ or $M \ge 60$) | `25, 0` | `'01:00'` | Normalized via modulo 24 hours / 60 minutes. |
| **Negative offset** ($H < 0$ or $M < 0$) | `0, -1` | `'23:59'` | Wrapped backward from 1440 minutes. |
| **Unspecified Inputs** (null / non-integer) | N/A | Outside specification | No extra custom exceptions required; rely on typed PowerShell parameters. |
