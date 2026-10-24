# wifi_probe firmware

Passive 2.4 GHz probe-request scanner for the XIAO ESP32-S3 (board 1 / WiFi).
Receive-only: it never associates or transmits.

## Build + flash (on the Pi)

Toolchain: Arduino CLI 1.5.1 + `esp32` core 3.3.12; esptool v5.6.0 in
`~/.venvs/esptool` (the Debian `esptool` 4.7.0 package is broken for S3).

```sh
arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32S3 firmware/wifi_probe
```

The XIAO build is **DIO, 80 MHz, 8 MB flash**. Flash the build-cache images
directly with esptool (the verified path — `arduino-cli upload` hung during
bring-up):

```sh
B=$(find ~/.cache/arduino/sketches -name wifi_probe.ino.bin \
      -printf '%T@ %h\n' | sort -n | tail -1 | cut -d' ' -f2-)
ESPTOOL=~/.venvs/esptool/bin/esptool
$ESPTOOL --port /dev/ttyACM0 --chip esp32s3 write-flash \
  --flash-mode dio --flash-freq 80m --flash-size 8MB \
  0x0     "$B/wifi_probe.ino.bootloader.bin" \
  0x8000  "$B/wifi_probe.ino.partitions.bin" \
  0xe000  ~/.arduino15/packages/esp32/hardware/esp32/3.3.12/tools/partitions/boot_app0.bin \
  0x10000 "$B/wifi_probe.ino.bin"
```

**Do not pass `--flash-mode qio`.** esptool rewrites the bootloader header's
flash-mode byte; the ROM then hangs loading the second bootloader segment
(`TG0WDT_SYS_RST` / `ets_loader.c 78`) and the board boot-loops. `dio` matches
the compiled image.

The board enumerates as `303a:1001` (USB-Serial/JTAG); `Serial` is the Hardware
CDC port. Defaults: `USBMode=hwcdc`, `CDCOnBoot=default` (enabled).

## Output

One JSON object per probe request on USB serial (115200 baud nominal):

```json
{"ts_ms":12345,"mac":"a4:5e:60:1a:2b:3c","rssi":-63,"ch":6,"ssid":"Flock-1A2B3C"}
```

`ssid` is `null` for wildcard probes.

The firmware also emits a heartbeat every 5 s:

```json
{"hb":5001,"probes":0}
```

`probes` is the number of probe requests seen (not necessarily printed).
Probe lines are dropped when the USB TX buffer is nearly full, by design,
so a slow or absent reader can never stall the sniffer. Heartbeats are
ignored by the host adapter.

Read it with:

```sh
cat /dev/ttyACM0
# or, decoded into anonymized events:
python -m presence.sensors.serial_wifi --port /dev/ttyACM0
```
