# Captures

Eberspächer Hydronic S3 Economy B5E 12 V CS (petrol water heater), EasyStart
Pro, tapped at the Pro's 4-pin CAN drop with the listen-only sketch. Bus is
500 kbit/s, 11-bit IDs. Files are SavvyCAN generic CSV, timestamps in µs
from board reset.

## Index

| File | What |
|------|------|
| `20260925-092032-idle.csv` | Empty (header only); first run, board not yet on the bus |
| `20260925-092201-idle.csv` | 60 s. Pro idle; fault memory cleared at 19.7 s; start pressed at 32.6 s. Metering pump was dead (stuck valves, confirmed on the bench afterwards) |
| `20260925-092313-idle.csv` | The following 60 s of the failed start attempt |

## Findings, 2026-09-25

Compared against TrooperDuper's Airtronic S3 B2L captures and
[protocol-reference.md](https://github.com/TrooperDuper/espar-airtronic-esphome/blob/main/docs/protocol-reference.md).

### Same as the Airtronic

| ID | Dir | Rate | Note |
|----|-----|------|------|
| `0x54` | Pro → heater | 200 ms | Command; see below |
| `0x55` `0x56` `0x57` | Pro → heater | 200 ms | Byte-identical static config (`10 27 00…`, `10 27 00…`, `00 00 FE FF FE FF 00 00`) |
| `0x60D` | Pro → heater | 100 ms | `0D 10 DF 23 02 20 70 00`. Same shape as the Airtronic's `0D 10 82 B6 09 20 70 00`; D3 to D5 are controller identity. D2/D3 toggled (`11`, `DE`/`DF`) for the first 3.5 s while buttons were being pressed |
| `0x65` | Pro | 4-frame burst | `DA 02 02 00 00 00 00 00`; D1/D2 = 730 in the same scale as the heater's sensor below |
| `0x625` | Heater | 100 ms | `25 00 11 43 FD BB E4 01`. D4 to D8 differ from the Airtronic (unit identity). D2 never toggled in 2 min |
| `0x2C5` | Heater | 200 ms | All zeros |
| `0x2C6` | Heater | 200 ms | `F4 01 84 03 00 00 00 00` = 500, 900 LE. Airtronic B2L: `32 00 7C 01` = 50, 380. Model code |
| `0x2C4` | Heater | 200 ms | Status; see below. The Airtronic sends it at 100 to 220 ms |

### Hydronic-specific

1. **Heat command has no setpoint.** Idle `00 00 FE FF FE FF 00 00` (same as
   Airtronic). Heat `01 01 FE FF FE FF 00 00`: D2 = `01` is a mode value the
   Airtronic never uses (it sends `05` with a °C×10 setpoint in D3/D4 and its
   room reading in D5/D6). Temperature and counter are both `FE FF`, "not
   available".
2. **New heater state `0x05` in `0x2C4` D1.** 200 ms after the command the
   heater went `03` → `05` and stayed there with D2 = `00` (no flame) and
   D3 = `00` (no fault) for the 90 s captured. Start attempt: water pump,
   fan, glow plug, waiting for flame. Not in the Airtronic table
   (`02 03 08 09 0B 21`).
3. **`0x2C4` D5/D6 is a temperature, not a counter.** 16-bit LE, flickers
   between adjacent values and rose monotonically through the failed start:
   677 → 680 → 690 → 700 over two minutes with the glow plug on. The
   Airtronic "echoes the controller's counter" because the air heater
   regulates the room reading the Pro sends in `0x54` D5/D6; the Hydronic
   sends `FE FF` there and reports its own sensor. Scale undecided: 700 is
   70.0 °F (21.1 °C) as tenths of °F, or 30.0 °C with a 400 offset. The Pro's
   own reading is `0x65` D1/D2 = 730. Calibrate against the Pro's displayed
   temperature.

### Diagnostic protocol (UDS over ISO-TP)

Captured at 19.7 s when the fault memory was cleared from the Pro. Tester
`0x7A0`, heater `0x73C`, single frames, 3 ms turnaround:

```
7A0  02 10 61                DiagnosticSessionControl, session 0x61
73C  06 50 61 00 32 01 F4    positive, P2 = 0x0032, P2* = 0x01F4
7A0  02 27 65                SecurityAccess, requestSeed (level 0x65)
73C  06 67 65 AB E9 BD 8B    seed AB E9 BD 8B
7A0  06 27 66 00 00 10 61    sendKey 00 00 10 61
73C  02 67 66                unlocked
7A0  04 14 FF FF FF          ClearDiagnosticInformation, all groups
73C  01 54                   positive
```

The key does not obviously derive from the seed; a second clear will show
whether it is constant. If so, `0x19` ReadDTCInformation in the same
session should return P-codes, which the `0x2C4` D3 flag cannot.

### Still to capture

- A full 5-minute failed start (safety time is 240 s): expect `0x2C4` D1
  `05` → `0B` with D3 set, then `03`. `./capture.py fail-start 300`.
- A second fault clear: `./capture.py clear-fault 60`.
- A successful start once the pump is replaced: flame flag in D2, and
  whatever D5/D6 does as the coolant heats to 75 °C.
- The Pro's boot: the `0x5C` to `0x10A` init burst, absent here because the
  Pro was already running.
