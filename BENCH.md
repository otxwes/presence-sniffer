# Bench bring-up guide (Phase 1 hardware)

Companion to **[HARDWARE.md](HARDWARE.md)** (authoritative BOM + decisions).
This is the step-by-step sequence once the parts arrive. Order matters: each
stage is validated in isolation before the next, so any failure is localizable.
All purchases completed **2026-09-19** — see plan-issued at that commit.

## Stage 0 — Unbox / inspect (~10 min)

1. Verify contents against HARDWARE.md rows. Watch the two error-prone items:
   - XIAO ESP32-S3: tiny board, **ESP32-S3** silkscreen, plain non-Sense (no
     camera/mic module), **pre-soldered headers**, ×3.
   - RTL-SDR: **V3 (R860)** — box label V3, dongle-only Black. Reject-and-return
     immediately if a V4-related label appears (clone).
2. Ferrite kit: keep bagged until Stage 4; they snap on USB/power lines only,
   never on the ALFA antenna or GPS antenna feeds.

## Stage 1 — Pi standalone, headless (~20 min)

Peripherals: CanaKit 5A PD PSU + microSD only. This isolates PSU/SD failures.

1. Flash the microSD with **Raspberry Pi Imager**: Raspberry Pi 5 → Pi OS Lite
   (64-bit) is sufficient for a daemon host.
2. Imager gear/settings: hostname (e.g. `sniffer`), **SSH enabled with
   password**, WiFi + locale pre-configured (headless, no HDMI — no micro-HDMI
   cable in the BOM by design).
3. Boot; expect red LED steady + green LED flicker. **Cycling red LED = PSU/PD
   negotiation failure** — first thing to diagnose, before blaming anything else.
4. From the Mac: `ssh pi@sniffer.local`. Sanity check:
   ```bash
   vcgencmd measure_volts && vcgencmd get_throttled   # 0x0 = clean
   ```

## Stage 2 — Radio validation, one device at a time (~30 min)

**First**, disable the Pi's own radios — permanent config, not just bench; the
rig must never count/sense itself (it advertises; the ESP32s don't):

```bash
sudo rfkill block wifi bluetooth
```

1. **ALFA AWUS036ACM** — the core of the rig; monitor mode is non-negotiable:
   - Plug into hub, `dmesg | tail` → expect `mt7612u` binding (in-kernel since
     4.19, nothing to install on Pi OS).
   - ```bash
     sudo ip link set wlan1 down && sudo iw dev wlan1 set type monitor && iw dev wlan1
     ```
     Output must show **type monitor**. If yes → ALFA fully validated.
   - Smoke test: `sudo tcpdump -i wlan1 -c 50` with your phone nearby —
     streaming frames = done.
2. **RTL-SDR V3**: `sudo apt install rtl-sdr` (blacklist the DVB-T TV driver if
   prompted, first run). `rtl_test` → expect R860 tuner; watch gain outputs.
   Confirm tuning across our bands (VHF/UHF/ISM):
   `rtl_fm -f 88.5M -M fm -s 22050 - | aplay` or equivalent scan.
3. **GPS PA1616S**: 9600 baud NMEA/UART → `gpsd`:
   `sudo apt install gpsd gpsd-clients && sudo gpsmon` — expect NMEA frames with
   lat/lon. Cold start needs a window seat and can take **5–15 min**; don't
   debug it indoors in a basement.

## Stage 3 — ESP32 boards (~15 min each)

1. **First: flash a trivial sketch through each SUNGUY cable** — a successful
   esptool flash is the physical proof the cable is a data cable (spec says
   USB 2.0/480 Mbps, which is ample; verify anyway, we were burned by
   charge-only cables during ordering).
2. Wire each XIAO through the hub's per-port switches; flash a serial-loopback
   firmware via esptool/Arduino framework. Confirms flashing + serial both hog
   the hub without hiccups.
3. Firmware work follows (Phase 1 sensors — WiFi promiscuous probe-request
   scanner + BLE listener). Board roles per the architecture: S3 is
   single-radio → **board 1 = WiFi, board 2 = BLE, board 3 = spare**. WiFi side
   targets: SSIDs `Flock-XXXXXX` / `test_flck`, OUIs `B4:1E:52` (Flock direct)
   + `E4:AA:EA` (Liteon), channel-hop 1–11 @ 400 ms. Spec reading (not
   importing code — educational license): `github.com/JakeSwiz/flock-you-wifi-recon`.

## Stage 4 — Full integration (~30 min)

All devices on the atolla 8-port powered hub (per-port switches on), hub on its
own 5V/4A brick, Pi on the CanaKit PSU. Watch for:
- CPU load and thermal (`vcgencmd measure_temp`).
- Hub brownout / device re-enumeration (`dmesg` errors, ports dropping).
- ALFA ↔ RTL-SDR proximity interference (both live in ~1.7 GHz range; keep ≥10 cm
  separation as the topology note in HARDWARE.md says).
- WiFi/BT coexistence weirdness between the two ESP32s and ALFA.

Ferrites now: snap them onto the hub's upstream USB cable and the ESP32 cables
**if** you observe noise/hiccups. Start clean; add only if evidence appears.

## Stage 5 — Smoke test with our own software

Bring the pipeline's sensor input layer (`sensors/`) online against the real
boards and the event bus feed. First closing of the hardware loop before any
enclosure work.

## Enclosure — only after Stage 5 passes

- Caliper the actual parts (especially hub and brick dimensions, and the
  PANPEO keystone coupler).
- Cutout is a **keystone slot (~30×16 mm + retention lip)** — not the ~22.5 mm
  round hole originally assumed. Snap-in from outside, includes retention lip.
- Vent cutout over the Active Cooler blower.
- Enclosure printed last so any late hardware-swap doesn't force a reprint.
