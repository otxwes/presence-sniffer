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

## Stage 1 — Pi standalone, headless (~20 min) — ✅ CLOSED 2026-10-04

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

**Lessons learned 2026-10-04 (for any future re-flash):**

- Imager v2 only exposes OS-customization via the **NEXT → "Edit Settings"**
  dialog and does not persist them between runs. If the Pi boots silent, mount
  `bootfs` and read `user-data`/`network-config` before debugging anything else.
- "Wireless LAN country: US" is mandatory; it lands in `cmdline.txt` as
  `cfg80211.ieee80211_regdom=US`.
- WiFi password sits plain-text in `network-config` until cloud-init's first
  successful boot wipes it. Don't leave the card loose.
- User: `otxwes` (1Password-generated password), hostname `sniffer`, key-based
  ssh from the Mac (`cline-agent` key) + NOPASSWD sudoers at
  `/etc/sudoers.d/010-otxwes-nopasswd`.
- `bootfs/cmdline.txt` retains Imager's `ds=nocloud;i=rpi-imager-...` plus our
  added `systemd.mask=systemd-rfkill.socket systemd.mask=systemd-rfkill.service`
  (recovery edit after an accidental `rfkill block wifi`; kept).

## Stage 2 — Radio validation, one device at a time (~30 min) — ALFA leg ✅ 2026-10-04

**Bench posture revision (2026-10-04):** the original blanket
`sudo rfkill block wifi bluetooth` **cannot work on a rig whose only management
path is that WiFi** — it cuts the SSH door mid-flight and persists across
reboots via `systemd-rfkill` (and blocks the USB ALFA too, since rfkill types
span devices). Revised posture:

- **Bluetooth**: `dtoverlay=disable-bt` appended to `/boot/firmware/config.txt`
  (firmware-level kill, permanent, survives everything; `hciuart.service` no
  longer exists — expected after the overlay). **Done 2026-10-04.**
- **WiFi internal (`wlan0`)**: stays up as the management channel
  (`sniffer.local` via mDNS). Passive, non-associating listener; tolerable RF
  footprint next to the ALFA. Revisit (`dtoverlay=disable-wifi`) only once a
  non-RF management channel exists (Ethernet cable / USB-serial console).
- **ALFA (`wlan1`)**: the only actively-driven RF device.

1. **ALFA AWUS036ACM** — the core of the rig; monitor mode is non-negotiable:
   **PROVEN 2026-10-04.**
   - Powers/works through the hub **only when the atolla's 5V/4A wall brick is
     connected** (bus-powered mode starves it; verified on the Mac via USB
     power budget). Enumerates as `ID 0e8d:7612 MediaTek MT7612U` behind the
     hub's Genesys tiers → `wlan1` (`00:c0:ca:be:24:0c`).
   - Driver `mt76x2u` module binds automatically (in-kernel), nothing to
     install. A vendor Windows/Mac driver download is irrelevant — skip it.
   - Monitor-mode recipe (note: `iw` lives in `/usr/sbin`; using tcpdump's
     `-I` flag *after* setting monitor manually errors with "doesn't support
     monitor mode" — set type via `iw`, run tcpdump **without** `-I`):
     ```bash
     sudo ip link set wlan1 down
     sudo iw dev wlan1 set type monitor
     sudo ip link set wlan1 up
     iw dev wlan1 info        # expect: type monitor / ch1 2412 MHz / 22 dBm
     ```
   - Smoke capture passed: `sudo tcpdump -i wlan1 -c 25 --immediate-mode` →
     25/25 frames, 0 kernel drops, dual-antenna RSSI −39…−88 dBm, neighbor
     beacons visible (incl. WiZ smart-bulb APs). Fully validated.
   - **Persistence**: `/etc/systemd/system/sniffer-monitor.service`
     (enabled; oneshot down → set type monitor → up at every boot).
2. **RTL-SDR V3**: `sudo apt install rtl-sdr` (blacklist the DVB-T TV driver if
   prompted, first run). `rtl_test` → expect R860 tuner; watch gain outputs.
   Confirm tuning across our bands (VHF/UHF/ISM):
   `rtl_fm -f 88.5M -M fm -s 22050 - | aplay` or equivalent scan.
   - **⭐ RTL-SDR V3 leg made first attempt 2026-10-18 — UNIT DOA, replacement
     in progress.** Preparatory work that STANDs for the replacement unit:
     - `rtl-sdr` pkg installed (Debian trixie `2.0.2`; fine for R820T/R860 —
       the R860 silicon IDs as "R820T" by design, it's the same R82xx family).
     - `/etc/modprobe.d/rtl-sdr-blacklist.conf` created (blacklist
       `dvb_usb_rtl28xxu` / `rtl2832` / `rtl2830` + `depmod`) so the kernel
       DVB-T driver never claims the stick.
     - `rtl_test -t` note: `-t` means "E4000 tuner benchmark"; R82xx-class
       dongles print `No E4000 tuner found, aborting` here — that line is
       EXPECTED, not a fault. Plain `rtl_test` runs a ringing loop (ctrl-c).
     - `[R82XX] PLL not locked!` alone is cosmetic in many field reports;
       the real test is capture data, below.
   - **DOA evidence (2026-10-18) — cross-host, identical:** Pi 5
     (librtlsdr 2.0.2 / trixie) and Mac (Homebrew librtlsdr 2.0.3) both:
     enumerate `0bda:2838 Realtek RTL2838UHIDIR SN: 00000001`; `rtl_test`
     finds "R820T" then PLL never locks; captured IQ is a constant rail
     (bytes 123–132, I std 0.81, flat spectrum ±800 kHz to ~0.3 dB — no FM
     station at 98.0 MHz, no signal anywhere); `rtl_sdr -n` never reaches
     its sample count (streams indefinitely). Zero USB-side kernel errors
     on either host — the failure is in the tuner/analog section, not USB.
     Full gain sweep at 98.0 MHz. NOTE: in `rtl_sdr`, `-g 0`/auto = AGC,
     not "0 dB manual". AGC → I std 3.72–5.54 but still flat, no market
     structure; manual 7.7/16.6/25.4/33.8/42.1/49.6 dB → std 0.53/0.54/
     0.57/0.66/0.82/1.16 — MORE gain, MORE pinned to the 127 rail
     (inverted); even AGC's std is far below the ~15–30 a healthy receiver
     shows from its own noise floor. Also tested 433.92 MHz (same rail).
     **Setup-vs-guide audit done 2026-10-18:** Linux/macOS driver choice
     correct, DVB-T blacklist in place, bias tee N/A (passive antenna; must
     stay off), HF direct sampling N/A — it's for <28.8 MHz only and all
     our bands/tests are ≥88 MHz. In-box advice is to use the RTL-SDR Blog
     driver fork → **built `rtlsdrblog/rtl-sdr-blog` on the Mac and re-tested:
     identical failure** (manual 42.1/49.6 dB → std 1.16/1.69; PLL never
     locks; flat spectrum). Coherent diagnosis: PLL never locks → no LO →
     no downconversion → constant ADC rail = synthesizer/tuner failure,
     not software.
     EEPROM/USB identity is the standard Realtek default (`RTL2838UHIDIR`,
     `Realtek`, SN `00000001`). **CORRECTION 2026-10-18: this is NORMAL for
     V3** — only V4/V4L units carry `RTLSDRBlog`/`Blog V4` EEPROM strings,
     which exist so drivers can distinguish them (per the manufacturer's own
     forum post); the default EEPROM is NOT counterfeit evidence — earlier
     note withdrawn. For a clone check use the official physical tells
     (side-panel screws diagonal = genuine; NSY QC batch sticker on back)
     and verify Amazon "Sold by" is exactly `RTL-SDR Blog`.
     Listing re-verified 2026-10-18: Amazon `B0BMKZCKTF` =
     "RTL-SDR Blog V3 R860 RTL2832U 1PPM TCXO SMA ... (Dongle Only)
     (Black)" — correct V3 listing; unit is V3-family silicon.
     → DOA return/replacement (see RTL_SDR_RETURN.md).
   - **Re-test recipe for the replacement unit (10 min):** plug in, `rtl_test`
     (expect tuner + no persistent PLL complaint), then
     `rtl_sdr -f 98.0M -s 2048000 -g 42 -n 4194304 /tmp/iq.bin` → analyze:
     healthy capture has byte spread well beyond 123–132 and a spectrum with
     dB-scale station structure. Then `rtl_power -f 88M:108M:200k -i 1 -e 10
     -g 42 /tmp/fm.csv` → real markets show stations 20–40 dB above floor;
     then demod an identified station with `rtl_fm -f <st>M -M fm -s 22050 -g
     42 - | aplay`. Analyzer script: saved this session as `analyze_iq.py`
     (bytes → byte-span / I-std / flat-spectrum verdict).
3. **GPS PA1616S**: 9600 baud NMEA/UART → `gpsd`:
   `sudo apt install gpsd gpsd-clients && sudo gpsmon` — expect NMEA frames with
   lat/lon. Cold start needs a window seat and can take **5–15 min**; don't
   debug it indoors in a basement.
   **Physical path reality (2026-10-18):** board = pin-header **#746**, no USB
   port (USB twin = #4279). The 16-pin header ships **loose** → requires
   **soldering** + 4× F-F Dupont jumpers to Pi GPIO (VIN→pin 1, GND→pin 6,
   TX→pin 10, RX→pin 8). Pi-side: `gpsd`+`gpsd-clients` installed 2026-10-18
   (USBAUTO=true, no serial console getty). **Plan (2026-10-18):** user has a
   soldering iron (solder session on a future bench day); **order 4+ F-F
   Dupont jumpers (~$7)**. `enable_uart=1` applied + rebooted same day →
   `/dev/ttyAMA0` live, `gpsd` pre-pointed at it — soldering day = wire + go.

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
own 5V/4A brick, Pi on the CanaKit PSU. **RESOLVED 2026-10-04: the Stage-2 "hub
can't power the ALFA" issue was missing/unpowered wall brick — bus-powered mode
gives only ~400 mA total (verified via `system_profiler SPUSBDataType` on the
Mac: `Current Available (mA): 500`, 100 of it consumed by the hub chip). With
the 5V/4A brick plugged in, per-port budget jumps to 900 mA and the ALFA
(0e8d:7612) enumerates through two Genesys hub tiers and captures normally.
Ferrite lesson if any hub question re-opens: diagnose power budget FIRST.** Watch for:
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
