#!/usr/bin/env python3
"""Capture the WeAct listen sketch's CSV output to a SavvyCAN-importable file.

Usage: ./capture.py [label] [seconds]   -> captures/<timestamp>-<label>.csv
Ctrl-C to stop, or give a duration in seconds. Needs pyserial
(pip install -r requirements.txt). The board is found automatically
(macOS /dev/cu.usbmodem*, Linux /dev/ttyACM* or /dev/ttyUSB*); override
with CAN_PORT=/dev/... in the environment.

Resets the board on open so the timestamp column starts at zero, writes the
SavvyCAN header itself and drops every row until the first post-reset frame
(timestamp under 5 s), strips the 8-digit zero padding from the ID column
(SavvyCAN's importer rejects it, same fix as TrooperDuper's tools/decode.py
--savvycan), drops the trailing comma, and echoes a frame count so you can
see it is alive.

While capturing, type a note and press Enter to record what you are doing;
notes go to captures/<same name>.notes.txt with the capture time in seconds.
"""
import glob, os, sys, threading, time, serial

def find_port():
    if os.environ.get("CAN_PORT"):
        return os.environ["CAN_PORT"]
    for pat in ("/dev/cu.usbmodem*", "/dev/cu.wchusbserial*", "/dev/ttyACM*", "/dev/ttyUSB*"):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[0]
    sys.exit("no serial port found; plug the WeAct in or set CAN_PORT=/dev/...")

PORT = find_port()
label = sys.argv[1] if len(sys.argv) > 1 else "capture"
seconds = float(sys.argv[2]) if len(sys.argv) > 2 else None
os.makedirs("captures", exist_ok=True)
path = f"captures/{time.strftime('%Y%m%d-%H%M%S')}-{label}.csv"

print(f"port {PORT}", file=sys.stderr)
s = serial.Serial(PORT, 115200, timeout=1)
s.setDTR(False); s.setRTS(True); time.sleep(0.1); s.setRTS(False)  # reset

HEADER = "Time Stamp,ID,Extended,Dir,Bus,LEN,D1,D2,D3,D4,D5,D6,D7,D8"
frames = 0
synced = False   # True once a frame with a post-reset timestamp has arrived
t_start = time.time()
notes_path = path[:-4] + ".notes.txt"

def note_reader():
    for line in sys.stdin:
        line = line.strip()
        if line:
            with open(notes_path, "a") as nf:
                nf.write(f"{time.time() - t_start:7.1f}s  {line}\n")
            print(f"  noted at {time.time() - t_start:.1f}s", file=sys.stderr)
threading.Thread(target=note_reader, daemon=True).start()

with open(path, "w") as f:
    f.write(HEADER + "\n")
    try:
        t0 = time.time()
        while seconds is None or time.time() - t0 < seconds:
            line = s.readline().decode("utf-8", "replace").rstrip("\r\n")
            if not line or line.startswith("Time Stamp"):
                continue
            if line.startswith("#"):
                print(line, file=sys.stderr)          # driver alerts
            elif "," in line and not line.startswith(("ets ", "rst:", "load:", "entry", "configsip", "clk_drv", "mode:")):
                cols = line.rstrip(",").split(",")
                if len(cols) < 6 or not cols[0].isdigit():
                    continue
                if not synced:
                    if int(cols[0]) > 5_000_000:      # µs; pre-reset leftover
                        continue
                    synced = True
                cols[1] = cols[1].lstrip("0") or "0"  # 00000625 -> 625
                f.write(",".join(cols) + "\n")
                frames += 1
                if frames % 100 == 0:
                    print(f"\r{frames} frames", end="", file=sys.stderr)
    except KeyboardInterrupt:
        pass
print(f"\n{frames} frames -> {path}", file=sys.stderr)
