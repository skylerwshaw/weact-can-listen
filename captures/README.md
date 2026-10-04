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
| `20260925-124943-fail-start.csv`, `-125536-` | Earlier attempts at the 5-minute capture; superseded |
| `20260925-125604-fail-start.csv` | 310 s. Heater/Pro re-init at the start, start pressed at 19.7 s, safety-time fault at 257.9 s, after-run to 318 s. First 4 data rows are stale pre-reset lines (fixed in `capture.py` afterwards); skip them |
| `20260925-130553-clear-fault.csv` | 58 s. Fault cleared from the Pro at 15.2 s |
| `20260925-133019-temp-check.csv` | 30 s while the Pro's screen read 30 °C; the calibration capture |
| `20261003-131050-full-cycle.csv` | 1066 s. Heater powered up at 12.6 s (already at 69 °C from an earlier run), Pro read and cleared a stored DTC at 54 to 57 s, start at 88.0 s, control pause 302 to 422 s, stop at 988.4 s, after-run to 1048 s. First 4 rows are stale pre-reset lines; header is on line 5 |
| `20261003-141210-residual-heat.csv` | 42 s. Residual heat mode selected on the Pro at 18.1 s with the coolant at 41 °C; the heater declined within 5 s and the Pro showed nothing |
| `20261003-141857-warm-start-residual.csv` | 1285 s. Start at 24.0 s from 40 °C with a 20 min timer, control pause 723 to 843 s, timer stop at 1224.4 s, after-run to 1284.6 s. Residual heat was not attempted despite the name. Notes file alongside |
| `20261004-105319-cold-start-residual.csv` | 2184 s. First capture without the board reset (first row is a real reading, no re-init). Cold start at 4.8 s from 23.7 °C with a 30 min timer, pauses 973 to 1093 s and 1672 to 1792 s, timer stop at 1806 s with no after-run, residual heat accepted 1868 to 2143 s. Notes alongside |

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

### The fault, from the 5-minute capture

Start commanded at 19.7 s (`0x54` = `01 01 FE FF FE FF 00 00`), heater in
state `05` from 19.9 s. At **257.9 s**, 238 s later and matching the S3's
240 s safety time, `0x2C4` went straight to
`03 08 20 00 E9 02 00 00`: state `03` (idle), D2 = `08` (fault flag, as on
the Airtronic), D3 = `20` (flame loss / fuel starvation, the P00012A family;
the pump was dead). The Pro dropped its command to idle 0.2 s later.

Differences from the Airtronic's fault behaviour:

- No `0B` fault state in D1; the Hydronic reports the fault as `03` + D2 `08`.
- D3 held the code for **one frame** (0.4 s), not ~26 s. D2 = `08` stayed
  for 60 s (until 318.1 s), which is the after-run, then cleared.
- `0x625` D2 was `10` from 298.1 s to 318.0 s, the last 20 s of the
  after-run, then `00`. Not an alive toggle here; it marks a phase.

So on the Hydronic, "fault happened" is D2 = `08` for a minute and the code
is a single frame in D3. Anything decoding faults must latch D3 on the
first non-zero value.

### Fault clear, second time

Same exchange, seed `A6 95 54 D5`, key still `00 00 10 61`. **The key is
constant.** The WeAct (or ESPHome later) can clear the S3's fault memory
with four frames on `0x7A0`, and `0x19` ReadDTCInformation in session `0x61`
is the next thing to try for real P-codes.

### Heater power-up handshake (start of the 5-minute capture)

This looked like the heater's fuse being pulled and reinserted, but every
capture opened with `capture.py`'s board reset (this one onward) starts the
same way, and the morning captures without the reset do not: the WeAct
glitches the bus while the ESP32 boots and the heater re-initialises its
session. The reset is gone from `capture.py` as of 2026-10-04. Either way
it is a clean record of the heater re-initialising under a running Pro. The
first frames show the heater's `0x625` D3 session counter step
`10` → `11`, `0x2C4` D5/D6 at a placeholder `500` (`F4 01`) for the first
frames before the real reading appears, and the Pro repeating
`0x5C` to `0x63` four times at 150 ms. TrooperDuper only saw the long
burst (`0x5C` to `0x10A`) because his captures began with the Pro booting;
this short one is the Pro reconnecting to a heater that rebooted. An
emulator has to handle both.

### Temperature scale: (value − 500) / 10 °C

Calibrated 2026-09-25 13:30: the Pro's screen read **30 °C** while its
`0x65` D1/D2 was `20 03` = 800. (800 − 500) / 10 = 30.0. Same scale fits
every other reading: the Pro at 730 (23 °C) in the morning and 810/820
(31 to 32 °C) at 13:00; the heater's `0x2C4` D5/D6 at 677 to 700 (18 to
20 °C) in the morning and 765 (26.5 °C) at 13:30, cooler than the cabin as
a heater under the van should be; TrooperDuper's Airtronic captures decode
to a 5 to 13 °C garage; and the `500` placeholder at heater boot is 0.0 °C.

So `0x2C4` D5/D6 is the heater's temperature sensor (coolant side on the
Hydronic) in tenths of a degree with a −50 °C origin, and `0x54` D5/D6 on
the Airtronic is the Pro's room reading in the same scale. For HA:
`temperature_c = (D6 << 8 | D5) / 10.0 - 50.0`, ignore the value 500 for the
first seconds after heater power-up.

`0x65` bursts came at 7, 47, 86 and 200 s, not every 10 s, with D3 cycling
1, 2, 3 and D1/D2 carrying the Pro's current reading.

## Findings, 2026-10-03 (metering pump replaced, heater runs)

Two full heat runs (`full-cycle`, `warm-start-residual`) and one declined
residual-heat request.

### A heat run, on the bus

| Time (`warm-start-residual`) | Bus | Meaning |
|------|-----|---------|
| 24.0 s | `0x54` → `01 01 FE FF FE FF 00 00` | Pro commands heat |
| 24.2 s | `0x2C4` D1 `03` → `05`, D2 `00` | Heater running, burner start sequence |
| 60 to 90 s | D5/D6 jumps 44.7 → 64.5 °C | Burner lit; the only flame evidence there is |
| 723.2 s | D2 `00` → `08` at 82.7 °C | Control pause: burner and blower off, water pump on |
| 843.2 s | D2 `08` → `00` at 72.0 °C | Burner restart commanded; coolant keeps falling 2 to 2.5 min more, then jumps |
| 1224.4 s | `0x54` → idle, D1 `05` → `03`, D2 `08` | Pro's 20 min timer ends heating; after-run |
| 1264.4 s | `0x625` D2 `00` → `10` | Last 20 s of the after-run, as in September |
| 1284.6 s | D2 `08` → `00`, `0x625` D2 → `00` | Pump off, heater idle |

The `full-cycle` run matches: pause at 82.7 °C (302.3 s), restart at 75.5 °C
(422.3 s), 60 s after-run after the stop. So:

- **There is no flame bit.** D2 `00` in state `05` covers glow, ignition, and
  steady burning alike (the September dead-pump start sat in `05`/`00` for
  238 s with no flame). Burner-on is "state `05` and D2 `00`"; actual flame
  shows only as the coolant slope.
- **D2 `08` is "burner off, unit still active"**, not a fault flag: control
  pause during a run, after-run after a stop or a fault. The September fault
  was D3 `20` for one frame; D2 `08` after it was just the after-run. A
  decoder latches D3 and treats D2 on its own as burner state.
- **Regulation band**: pause at 82.7 °C both runs, restart commanded at 72
  to 75.5 °C. The TD's 75 °C is the middle of the band.
- Ignition shows up in D5/D6 about 40 to 60 s after a cold-ish start and
  2 to 2.5 min after a pause restart.

### Residual heat mode (pump plus cabin blower, no burner)

Enabled on this Pro (heater icon in a circle in the menu bar; LED ring
orange). Selected at 18.1 s of `residual-heat` with the coolant at 41 °C:

| Time | Bus |
|------|-----|
| 18.1 s | `0x54` → `01 03 FE FF FE FF 00 00`: D2 `03` is the residual-heat mode (heat is `01`) |
| 18.2 s | `0x2C4` D1 `03` → `41` |
| 23.2 s | D1 `41` → `C1`, one frame |
| 23.5 s | `0x54` back to idle; D1 → `03` |

Accepted on 2026-10-04 (`cold-start-residual`) with the coolant at 70 °C,
62 s after a heat run ended:

| Time | Bus |
|------|-----|
| 1867.9 s | `0x54` → `01 03 …`; `0x625` D3 blips `11` → `10` → `11` and `0x2C4` D5/D6 shows the `500` placeholder for one frame: the heater re-initialises on the mode change |
| 1868.7 s | `0x2C4` D1 `03` → `81`, D2 `00`, and stays there |
| 1868 to 2143 s | Coolant 66.2 → 57.5 °C, about 2 °C/min with the pump circulating and the cabin blower on |
| 2143.3 s | Pro OFF; D1 → `03` next frame, no after-run |

So D1 `0x81` is residual heat running, `0x41` the request being evaluated,
`0xC1` the request ending or declined. The decline threshold is somewhere
between 41 and 70 °C. A decoder should treat the one-frame `500` after any
mode change like the power-up placeholder.

### Cold start and the after-run

From 23.7 °C: state `05` at 5.0 s, coolant 39 °C at 60 s and 63.5 °C at
120 s, so ignition inside the first minute, no slower than the warm start.
Pauses at 82.7 °C both times (973 s, 1672 s), restarts commanded at 71.9 and
71.6 °C. The 30 min timer stopped it at 1806 s, 14 s after a restart was
commanded and before the burner had lit: D1 went `05` → `03` with D2 `00`,
**no after-run**. The 60 s after-run (D2 `08`) only follows a burning
burner.

### The Pro reads P-codes over UDS, and a listener sees it

At 54 s of `full-cycle` the Pro queried the heater before clearing it:

```
7A0  03 19 02 01 AA AA AA AA   ReadDTCInformation, reportDTCByStatusMask 0x01
73C  03 59 02 7B               none
7A0  03 19 02 08 AA AA AA AA   mask 0x08 (confirmed DTCs)
73C  07 59 02 7B 00 02 11 28   one DTC: 00 02 11, status 0x28
```

DTC bytes `00 02 11` are what the Pro shows as P000211, presumably the
dead-pump fault from September. The clear followed at 57.5 s (session
`0x61`, SecurityAccess level `0x65`, key `00 00 10 61` for the third time)
and the same query at 1044 s, after the stop, returned nothing. Padding byte
is `AA`. A read-only node therefore gets P-codes for free whenever the Pro
is used to look at them; sending `19 02 08` itself needs session `0x61`
first (the Pro opened it before the clear, not before the read, so the read
may work without it).

### Pro reconnect burst, second form

`warm-start-residual` has the Pro replaying `0x64 0x66 0x6D 0x10A 0x67 0x68`
alongside `0x5C` to `0x63`; the other captures only show the `0x5C` to
`0x63` plus `0x66`/`0x10A` set. Payloads: `0x64` `3C 00 05 00 C8 00 FF 03`,
`0x67`/`0x68` `BE 3E 27 00 01 1E 00 00`, `0x6D` `12 00 00 00 00 00 00 F0`.
Undecoded; only matters for step 3.

### Still to capture

- Residual heat left on until the heater ends it itself, for the cut-out
  temperature and whether it leaves via `0xC1`.
- `0x19 02 08` sent by the node itself, to see whether it needs session
  `0x61` first (needs a transmitting sketch).
- The Pro's own boot (power-cycle the Pro alone), only for step 3.
