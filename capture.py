#!/usr/bin/env python3
"""Capture the WeAct listen sketch's CSV output to a SavvyCAN-importable file.

Usage: ./capture.py [label] [seconds]   -> captures/<timestamp>-<label>.csv
Ctrl-C to stop, or give a duration in seconds. Needs pyserial
(pip install -r requirements.txt). The board is found automatically
(macOS /dev/cu.usbmodem*, Linux /dev/ttyACM* or /dev/ttyUSB*); override
with CAN_PORT=/dev/... in the environment.

Resets the board on open so the timestamp column starts at zero, strips the
8-digit zero padding from the ID column (SavvyCAN's importer rejects it, same
fix as TrooperDuper's tools/decode.py --savvycan), drops the trailing comma,
and echoes a frame count so you can see it is alive.
"""
import glob, os, sys, time, serial

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

frames = 0
with open(path, "w") as f:
    try:
        t0 = time.time()
        while seconds is None or time.time() - t0 < seconds:
            line = s.readline().decode("utf-8", "replace").rstrip("\r\n")
            if not line:
                continue
            if line.startswith("Time Stamp"):
                f.write(line + "\n")
            elif line.startswith("#"):
                print(line, file=sys.stderr)          # driver alerts
            elif "," in line and not line.startswith(("ets ", "rst:", "load:", "entry", "configsip", "clk_drv", "mode:")):
                cols = line.rstrip(",").split(",")
                if len(cols) >= 6:
                    cols[1] = cols[1].lstrip("0") or "0"  # 00000625 -> 625
                    f.write(",".join(cols) + "\n")
                    frames += 1
                    if frames % 100 == 0:
                        print(f"\r{frames} frames", end="", file=sys.stderr)
    except KeyboardInterrupt:
        pass
print(f"\n{frames} frames -> {path}", file=sys.stderr)
