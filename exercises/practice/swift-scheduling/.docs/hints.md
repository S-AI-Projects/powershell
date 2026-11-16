# Hints

## General

- Pay close attention to the duration offset specified for each schedule keyword (`NOW`, `ASAP`, `EOW`, `\d+M`, `Q\d`).

## Handling "NOW"

- The `NOW` description requires scheduling exactly two hours after the meeting start time.
- A common mistaken assumption is adding a single hour (1 hour offset) or failing to use standard 24-hour time addition.
- Diagnostic check: If a meeting starts at `2012-02-13 09:00:00`, a delivery described as `NOW` must resolve to `2012-02-13 11:00:00`.
- In PowerShell, you can use `$MeetingStart.AddHours(2)` on `[System.DateTime]` instances rather than manual string or timestamp arithmetic.
