# weact-can-listen

Listen-only CAN sniffer for the WeAct CAN485 V1 (ESP32) that prints frames as
SavvyCAN-format CSV over USB, plus a capture script that writes a file
SavvyCAN imports directly. Built to capture an Eberspächer Hydronic S3
heater's EasyStart Pro bus; works on any 500 kbit/s CAN bus.

The firmware is TrooperDuper's `CAN_CSV_WeAct_Listen.ino` from
[espar-airtronic-esphome](https://github.com/TrooperDuper/espar-airtronic-esphome)
(MIT), wrapped in a PlatformIO project so it builds and flashes with one
command. The CAN driver runs in `TWAI_MODE_LISTEN_ONLY`: the board never
transmits, not even ACKs.

## Hardware

- WeAct CAN485 V1: CAN RX GPIO26, TX GPIO27. Termination switch K3 **off**
  when tapping a bus that is already terminated at both ends.
- Wire CAN H, CAN L, and GND to the board's screw terminals. Power over USB.

## Flash

```sh
pio run -e weact -t upload      # TF card slot must be empty
```

Set `upload_port` / `monitor_port` in `platformio.ini` to your board's port. Only needed to reflash; capturing needs no PlatformIO.

## Capture

On any machine with Python 3 (the board is already flashed; PlatformIO is
not needed for capturing):

```sh
git clone https://github.com/skylerwshaw/weact-can-listen.git
cd weact-can-listen
python3 -m pip install -r requirements.txt   # pyserial
./capture.py idle 60            # 60 s to captures/<timestamp>-idle.csv
./capture.py heat-cycle         # open-ended, Ctrl-C to stop
```

The board is found automatically (macOS `/dev/cu.usbmodem*`, Linux
`/dev/ttyACM*` or `/dev/ttyUSB*`); override with `CAN_PORT=/dev/...`. On
Linux add yourself to the `dialout` group (or `uucp` on Arch) and log in
again for port access.

The script resets the board (timestamps start at zero), strips the zero-padded
IDs SavvyCAN's importer rejects, and prints a running frame count. Load the
CSV in SavvyCAN with File -> Load. Bitrate is fixed at 500 kbit/s in
`src/main.cpp`; change `TWAI_TIMING_CONFIG_500KBITS()` for other buses.
