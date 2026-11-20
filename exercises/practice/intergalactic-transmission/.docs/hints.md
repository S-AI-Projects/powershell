# Hints

## Empty and zero-byte messages

The PowerShell interface accepts a `[byte[]]` sequence. An empty sequence has no data bits to frame, so both transmitting and receiving `@()` produce an empty sequence.

| Operation and input | Specification rule | Required output |
| --- | --- | --- |
| Transmit `@()` | There are no seven-bit data groups to send. | `@()` |
| Receive `@()` | There are no parity-protected bytes to decode. | `@()` |
| Transmit `@(0x00)` | The eight zero data bits cross a seven-bit boundary. The first seven zeros form one frame; the remaining zero is padded with six zero data bits. Both frames have even parity. | `@(0x00, 0x00)` |

In PowerShell, `0x00` is written as a hexadecimal integer literal; the function's `[byte[]]` parameter binds it as one byte. `@()` is an empty array. The transmitter emits its encoded bytes as an ordered sequence. The zero byte is not a special case: it still occupies eight input bits, so it becomes two seven-bit data groups with parity framing.

The exercise specifies byte sequences and parity behavior. It does not establish a coercion or error rule for values outside the byte range; do not infer one from PowerShell parameter conversion. See the checked-in Pester cases for the contract, including the required `wrong parity` errors on invalid received bytes.
