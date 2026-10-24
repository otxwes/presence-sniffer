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
     **Boot-race fixed 2026-10-24:** the oneshot fired before USB enumeration
     ("Cannot find device wlan1" at boot → service stayed failed with no retry;
     wireless silently stayed in managed mode for days). Added an ExecStartPre
     wait loop (up to 30 s for `wlan1` to appear). Verified by reboot.
     **NM reclaim fixed 2026-10-24:** NetworkManager was forcing wlan1 back to
     managed ~4 s after the service ran (its supplicant attaches when NM
     startup completes; monitor mode ≠ managed mode so NM re-inits it). Created
     `/etc/NetworkManager/conf.d/wlan1-unmanaged.conf`:
     `[keyfile]` / `unmanaged-devices=interface-name:wlan1` + NM reload —
     wlan1 now never touched by NM (SSH stays on onboard wlan0). Verified by
     reboot: monitor mode ch1 persists with zero manual steps.
2. **RTL-SDR V3**: `sudo apt install rtl-sdr` (blacklist the DVB-T TV driver if
   prompted, first run). `rtl_test` → expect R860 tuner; watch gain outputs.
   Confirm tuning across our bands (VHF/UHF/ISM):
   `rtl_fm -f 88.5M -M fm -s 22050 - | aplay` or equivalent scan.
   - **⭐ RTL-SDR V3 leg: BOTH units DOA (2026-10-18 and 2026-10-24) — same
     failure signature.** The replacement unit arrived 2026-10-24 and failed
     its first test byte-identically: span 123..131, I std 0.83, `[R82XX] PLL
     not locked!`, 88–108 MHz scan flat (0 peaks >6 dB). Two units from the
     same listing with an identical fault = batch or counterfeit problem, not
     bad luck. (Final pre-return retest 2026-10-24 14:13 EDT: identical —
      I std 0.83, in-band ±800 kHz peak-median 2.6 dB, FM scan flat to
      1.4 dB.) **Replacement ordered 2026-10-24: Nooelec NESDR SMArt v5 Bundle
     (SKU 100700, $54.95, nooelec.com)** — different manufacturer/warehouse,
     R820T2, stock librtlsdr, 3 SMA antennas included. The official eBay V4L
     (`rtl-sdr-blog`, $37.95) was rejected: R828S needs the Blog driver fork
     and ships dongle-only. If ever considering another purchase from
     `B0BMKZCKTF`: verify Amazon
     "Sold by" is exactly `RTL-SDR Blog` and check physical clone tells
     (diagonal side screws = genuine; NSY QC batch sticker on back); if the
     seller is genuinely official, escalate to RTL-SDR Blog with both DOA
     units. Pi/ALFA environment ruled out (unit #1 failed identically on Mac
     with stock + official Blog-fork drivers). Preparatory work that STANDs
     for a good unit:
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
   - **Control-unit test (Nooelec SMArt v5) — 10 min, on arrival:** plug into
     the same Pi + powered hub, `rtl_test` (expect R820T and a locked PLL),
     then `rtl_sdr -f 98.0M -s 2048000 -g 42 -n 4194304 /tmp/iq.bin` (wrap in
     `timeout 8` — the tool may not stop on `-n`), then
     `rtl_power -f 88M:108M:200k -i 1 -e 10 -g 42 /tmp/fm.csv`. Analyze both
     with `python3 scripts/analyze_iq.py <file>` (handles .bin and .csv):
     healthy = I std ≥5 (typ 10–30), in-band spectrum peak-median >6 dB with
     station structure, FM scan 20–40 dB above floor. Optional demod:
     `rtl_fm -f <st>M -M fm -s 22050 -g 42 - | aplay`. **Pass → bench
     exonerated, this unit becomes the rf_warmth sensor, Stage 2b closes.
     Fail → the bench (not the source) is the suspect; stop buying dongles.**
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

## Stage 3 — ESP32 boards (~15 min each) ✅ firmware-verified 2026-10-24

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

**Progress log (2026-10-24):**
- **Board 1** — MAC `b8:1f:3f:d9:28:d8`; ESP32-S3 v0.2, 8 MB flash
  (GigaDevice `c8 4017`, quad), 8 MB PSRAM, USB-Serial/JTAG. SUNGUY cable =
  data cable. `flash-id` + 4 KB scratch write → read → byte-compare → restore
  at `0x7FF000` all verified through the powered hub. ✅ ready for firmware.
- **Board 2** — MAC `44:b1:76:b0:55:68`; same chip/flash; `flash-id` +
  scratch write/read/restore ✅.
- **Board 3** — MAC `44:b1:76:ae:d5:0c`; same chip/flash; `flash-id` +
  scratch write/read/restore ✅.

**All three boards verified 2026-10-24** — same ESP32-S3 v0.2, 8 MB flash,
8 MB PSRAM; all flash through the hub. Hardware side of Stage 3 done;
WiFi firmware verified live on board 3 (below).
- **Tooling:** apt `esptool` 4.7.0 is missing `stub_flasher_32s3.json`
  (Debian packaging bug); use `~/.venvs/esptool/bin/esptool` (v5.6.0,
  installed 2026-10-24). Stub flasher works; commands are hyphenated
  (`flash-id`, `read-flash`, `write-flash`).

**WiFi firmware live verification (2026-10-24, board 3 = spare):**
- `wifi_probe` compiles clean (Arduino CLI 1.5.1 + esp32 3.3.12; 839,804 B
  flash / 44,664 B RAM). First flash used esptool `--flash-mode qio`, which
  patched the DIO bootloader header → the ROM hung on the second bootloader
  segment (`TG0WDT_SYS_RST`, `ets_loader.c 78`). Reflashed with
  `--flash-mode dio` (matching the compiled image) → boots and stays up.
- Live serial: boot/ready lines plus `{"hb":...,"probes":...}` every 5 s.
  A Pi `iw dev wlan0 scan` produced real wildcard probe requests from the
  Pi's own `wlan0` (`88:a2:9e:6a:5a:94`) on channels 5/11, RSSI −91…−97 dBm;
  the board's probe counter reached 37.
- Host adapter: 7 probe lines parsed; stable anonymized id `ad136f4e2af4`;
  no raw MAC appeared in adapter output.
- Aggregator: `--serial-wifi /dev/ttyACM0 --print` → 20 `[event]` lines and
  89 `[snapshot]` lines in 45 s, no errors.
- Tests: **30 passed** in both the Mac `.venv` and the Pi venv.
- The TX-space guard can drop a few lines under pressure (counter advanced
  13→37 while the aggregator printed 20 events); acceptable for bench,
  revisit if exact delivery becomes a requirement.
- **Board 1 (WiFi role) still needs this image**; board 3 (spare) was the
  bring-up board. Board 2 (BLE) firmware remains next.

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
