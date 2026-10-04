#!/usr/bin/env python3
"""Capture the WeAct listen sketch's CSV output to a SavvyCAN-importable file.

Usage: ./capture.py [label] [seconds]   -> captures/<timestamp>-<label>.csv
Ctrl-C to stop, or give a duration in seconds. Needs pyserial
(pip install -r requirements.txt). The board is found automatically
(macOS /dev/cu.usbmodem*, Linux /dev/ttyACM* or /dev/ttyUSB*); override
with CAN_PORT=/dev/... in the environment.

Or, with the board running the ESPHome node (homelab esphome/van-heater.yaml)
and its "Frame log" switch on in HA, read the same CSV lines out of the
ESPHome log over Wi-Fi, no USB:
    CAN_SOURCE="esphome logs /path/to/van-heater.yaml" ./capture.py <label>
CAN_SOURCE is any shell command whose stdout carries the CSV lines; the
ESPHome log prefix ("[12:34:56][D][frame:123]: ") is stripped.

Does NOT reset the board: every capture that opened with a DTR/RTS reset
(2026-09-25 afternoon onward) begins with the heater re-initialising its bus
session (0x625 D3 steps, 0x2C4 reports the 500 placeholder, the Pro replays
its reconnect burst), and the morning captures without the reset do not. The
ESP32 glitches the bus while it boots. Instead the first frame's timestamp
becomes zero. Writes the SavvyCAN header itself, strips the 8-digit zero
padding from the ID column (SavvyCAN's importer rejects it, same fix as
TrooperDuper's tools/decode.py --savvycan), drops the trailing comma, and
echoes a frame count so you can see it is alive.

While capturing, type a note and press Enter to record what you are doing;
notes go to captures/<same name>.notes.txt with the capture time in seconds.
"""
import glob, os, re, subprocess, sys, threading, time

def find_port():
    if os.environ.get("CAN_PORT"):
        return os.environ["CAN_PORT"]
    for pat in ("/dev/cu.usbmodem*", "/dev/cu.wchusbserial*", "/dev/ttyACM*", "/dev/ttyUSB*"):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[0]
    sys.exit("no serial port found; plug the WeAct in or set CAN_PORT=/dev/...")

label = sys.argv[1] if len(sys.argv) > 1 else "capture"
seconds = float(sys.argv[2]) if len(sys.argv) > 2 else None
os.makedirs("captures", exist_ok=True)
path = f"captures/{time.strftime('%Y%m%d-%H%M%S')}-{label}.csv"

if os.environ.get("CAN_SOURCE"):
    print(f"source: {os.environ['CAN_SOURCE']}", file=sys.stderr)
    proc = subprocess.Popen(os.environ["CAN_SOURCE"], shell=True, stdout=subprocess.PIPE)
    def read_line():
        raw = proc.stdout.readline()
        if not raw:
            raise KeyboardInterrupt            # source ended
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        line = re.sub(r"\x1b\[[\d;]*m", "", line)          # ANSI colour
        return re.sub(r"^\[[^\]]*\]\[[^\]]*\]\[[^\]]*\]: ", "", line)   # [time][D][frame:123]:
else:
    import serial
    PORT = find_port()
    print(f"port {PORT}", file=sys.stderr)
    # pyserial asserts DTR and RTS together on open; the auto-reset circuit
    # only fires when they differ, so leave them alone (toggling them one at a
    # time is exactly the reset we are avoiding).
    s = serial.Serial(PORT, 115200, timeout=1)
    s.reset_input_buffer()
    def read_line():
        return s.readline().decode("utf-8", "replace").rstrip("\r\n")

HEADER = "Time Stamp,ID,Extended,Dir,Bus,LEN,D1,D2,D3,D4,D5,D6,D7,D8"
frames = 0
t_board0 = None   # first frame's board timestamp (µs), becomes zero
t_prev = None     # previous frame's zeroed timestamp, for gap warnings
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
            line = read_line()
            if not line or line.startswith("Time Stamp"):
                continue
            if line.startswith("#"):
                print(line, file=sys.stderr)          # driver alerts
            elif "," in line and not line.startswith(("ets ", "rst:", "load:", "entry", "configsip", "clk_drv", "mode:")):
                cols = line.rstrip(",").split(",")
                if len(cols) < 6 or not cols[0].isdigit():
                    continue
                if t_board0 is None:
                    t_board0 = int(cols[0])
                cols[0] = str((int(cols[0]) - t_board0) % (1 << 32))   # micros() wraps at 71 min
                if t_prev is not None and int(cols[0]) - t_prev > 1_000_000:
                    print(f"\n# gap of {(int(cols[0]) - t_prev) / 1e6:.1f} s at {int(cols[0]) / 1e6:.1f} s (link dropped?)", file=sys.stderr)
                t_prev = int(cols[0])
                cols[1] = cols[1].lstrip("0") or "0"  # 00000625 -> 625
                f.write(",".join(cols) + "\n")
                frames += 1
                if frames % 100 == 0:
                    print(f"\r{frames} frames", end="", file=sys.stderr)
    except KeyboardInterrupt:
        pass
print(f"\n{frames} frames -> {path}", file=sys.stderr)
