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

### ESPHome alternative

The board can instead run a listen-only ESPHome node that logs the same CSV
lines, so captures can be taken over Wi-Fi with no USB cable (see
`CAN_SOURCE` below). That node's YAML is not in this repo. Flash it over
USB-C with the tap unplugged from the harness, since the ESP32 glitches the
bus while it boots:

```sh
uvx --from esphome esphome run path/to/your-node.yaml
```

Then plug the tap back in and watch the log for idle traffic and a sane
coolant temperature.

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

To read from an ESPHome node's log over Wi-Fi instead of USB, set
`CAN_SOURCE` to any command that prints the CSV lines; the ESPHome log prefix
is stripped:

```sh
CAN_SOURCE="uvx --from esphome esphome logs path/to/your-node.yaml" ./capture.py idle
```

The script does not reset the board (a reset makes the heater re-initialise
its bus session); the first frame's timestamp becomes zero instead. It writes
the SavvyCAN header, strips the zero-padded IDs SavvyCAN's importer rejects,
prints a running frame count, and warns on any gap over 1 s between frames
(a dropped link). Type a note and press Enter while capturing to log what you
are doing to `captures/<same name>.notes.txt`, stamped with the capture time.

Load the CSV in SavvyCAN with File -> Load. Bitrate is fixed at 500 kbit/s in
`src/main.cpp`; change `TWAI_TIMING_CONFIG_500KBITS()` for other buses.
