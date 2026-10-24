# ble_scan firmware

Passive BLE advertisement scanner for the XIAO ESP32-S3 (board 2 / BLE role).
Receive-only: the scan is passive (`setActiveScan(false)`), so the board never
transmits scan requests and never connects.

## Build + flash (on the Pi)

Toolchain: Arduino CLI 1.5.1 + `esp32` core 3.3.12; esptool v5.6.0 in
`~/.venvs/esptool` (the Debian `esptool` 4.7.0 package is broken for S3).

```sh
arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32S3 firmware/ble_scan
```

The XIAO build is **DIO, 80 MHz, 8 MB flash**. Verified sizes (2026-10-24):
556,748 B flash / 27,520 B RAM. Flash the build-cache images directly with
esptool (the verified path — `arduino-cli upload` hung during bring-up):

```sh
B=$(find ~/.cache/arduino/sketches -name ble_scan.ino.bin \
      -printf '%T@ %h\n' | sort -n | tail -1 | cut -d' ' -f2-)
ESPTOOL=~/.venvs/esptool/bin/esptool
$ESPTOOL --port /dev/ttyACM1 --chip esp32s3 write-flash \
  --flash-mode dio --flash-freq 80m --flash-size 8MB \
  0x0     "$B/ble_scan.ino.bootloader.bin" \
  0x8000  "$B/ble_scan.ino.partitions.bin" \
  0xe000  ~/.arduino15/packages/esp32/hardware/esp32/3.3.12/tools/partitions/boot_app0.bin \
  0x10000 "$B/ble_scan.ino.bin"
```

**Do not pass `--flash-mode qio`.** Same boot-race as wifi_probe — esptool
rewrites the bootloader header's flash-mode byte and the board boot-loops
(`TG0WDT_SYS_RST`, `ets_loader.c 78`). `dio` matches the compiled image.

For multi-board setups use the stable by-id path instead of `/dev/ttyACM1`:
`/dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit_<MAC>-if00`
(board 2 is `44:B1:76:B0:55:68`; keeping board 1/WiFi on `/dev/ttyACM0` from
being flashed while it streams is the point of the by-id form).

## Output

One JSON object per unique advertiser per 1 s scan window on USB serial
(115200 baud nominal):

```json
{"ts_ms":12345,"mac":"aa:bb:cc:dd:ee:ff","rssi":-79,"name":"iPhone"}
{"ts_ms":12345,"mac":"11:22:33:44:55:66","rssi":-95,"name":null}
```

`name` is null unless the advertised-name field fits the primary advertising
packet. Passive scan does not receive scan-response payloads, so many devices
report `null` names — expected, not a bug. BLE randomized (RPA) addresses are
the norm; the host adapter hashes whatever address the radio saw.

The firmware also emits a heartbeat every 5 s:

```json
{"hb":5001,"adverts":123}
```

`adverts` counts advertisements (raw, not deduped). Event lines are dropped
when the USB TX buffer is nearly full, by design, so a slow or absent reader
can never stall the sniffer. Heartbeats are ignored by the host adapter.

Read it with:

```sh
cat /dev/ttyACM1
# or, once wired in, decoded into anonymized events:
python -m presence.aggregator --serial-wifi /dev/ttyACM0 --serial-ble /dev/ttyACM1
```
