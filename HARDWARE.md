# HARDWARE.md — Phase 1 Bill of Materials

Last re-verified **2026-09-19** against vendor sites and current research.
Total ≈ **$250–290**.

## Buy list (in order)

| # | Item | ~Price | Feeds which code | Verification notes |
|---|---|---|---|---|
| 1 | Seeed XIAO ESP32-S3 ×3 | $21 | edge sensors; **1 board → WiFi promiscuous, 1 → BLE scan, 1 → spare** | S3 is single-radio — cannot scan WiFi and BLE simultaneously, hence one board per radio |
| 2 | Raspberry Pi 5 (4 or 8GB) + active cooler + case | $80–110 | aggregator host | Requires **5V/5A (25W)** PD supply, else USB budget caps at 600 mA |
| 3 | ALFA AWUS036ACHM (MT7610U) *or* AWUS036ACM (MT7612U) | $25–35 | `WifiSensor` monitor mode | **ACHM is MT7610U, not AR9271** (that was the AWUS036NHA, EOL). Both support Linux monitor mode, dual-band. ACHM sold out direct — buy via Amazon/resellers |
| 4 | RTL-SDR Blog V4 (~$40, or V4L Lite cheaper) | $40 | `rf_warmth` + wideband drone-RF | Still current as of Aug 2026 |
| 5 | u-blox GPS (NEO-6M/7/M8N or PA1616S) | $12–25 | `SurveillanceContext` distance math | Commodity modules, any vendor |
| 6 | 100W PD power bank **or** 25W official PSU + powered USB hub | $30–50 | power | Pi 5 @ 5V/3A limits all USB to ~600 mA — our peripherals exceed that |
| 7 | USB-A extensions ×4, USB-C pigtails, ferrite chokes, enclosure | $20 | build | Antennas exit case; SDR ≥10 cm from WiFi adapter |

## Where to buy (re-validated live 2026-09-19)

| Component | Confirmed source | Status |
|---|---|---|
| XIAO ESP32-S3 (plain, non-Sense) | [seeedstudio.com](https://www.seeedstudio.com/XIAO-ESP32S3-p-5627.html) — US warehouse | **In stock**, ~$7.49–14 each (cheaper than our $21 est.). Skip the "Sense" camera version — not needed |
| Pi 5 (4GB) + 27W PSU + Active Cooler | canakit.com/raspberry-pi-5 | Pi 5 4GB from ~$110, PSU $14.95, Active Cooler $11.95 — all in stock. Budget crept up vs our $80–110 estimate |
| ALFA **AWUS036ACM** (MT7612U) | **store.rokland.com** (authorized distributor) or Amazon sold-by-Rokland; also Newegg/eBay (note: Newegg lists one at $90 — scalped) | ACM readily available. Prefer **ACM over ACHM** — ACHM (MT7610U) stock is spotty |
| RTL-SDR Blog V4 | rtl-sdr.com/store (ships worldwide, free ship) | V4 in stock ~$40; budget alt: **V4L Lite** (cheaper, latest release) |
| GPS: Adafruit Ultimate GPS PA1616S | [adafruit.com/product/746](https://www.adafruit.com/product/746) | **$29.95, 29 in stock**, NMEA/UART, works with `gpsd` directly |
| GPS budget alt | Seeed **L76K GNSS for XIAO** ($10.9) | Cheaper 3×, but it's an XIAO-shield format — only use if feeding GPS via an ESP32; for direct Pi `gpsd`, stick with Adafruit |
| Powered USB hub / cables / chokes | Amazon / PiShop | Commodity, any vendor |

Ordering note: Seeed US warehouse + Adafruit + RTL-SDR.com are all US-shipping → three orders, all in stock as of 2026-09-19.

## Decisions recorded (do not re-litigate without new evidence)

1. **ESP32-S3 over ESP32-C5** — C5's dual-radio concurrency unverified.
2. **Watch: XIAO ESP32-C6** (~$7, WiFi-6 dual-band + BLE5) — flock-you C6
   port exists (`storskegg/flock-you-c6`, immature Feb 2026). One C6 could
   replace the S3 pair if it matures. Not v1.
3. **Kismet excluded from v1** — heavy process, packet-shaped data model
   vs our event-shaped pipeline.
4. **Deferred**: HackRF (~$350; V4 covers the scorer's inputs), Ubertooth
   One (payload-level BLE; our features are event-shaped), AX210 6 GHz
   (no PCIe path).
5. **Firmware spec source (2026 research correction):** modern Flock ALPRs
   (Falcon/Sparrow) **do NOT beacon on BLE**. Productive path = WiFi probe
   requests: SSIDs `Flock-XXXXXX` / `test_flck`, OUIs `B4:1E:52` (Flock
   direct) and `E4:AA:EA` (Liteon); channel-hop 1–11 every 400 ms.
   Spec off `github.com/JakeSwiz/flock-you-wifi-recon`
   (`esp32_wrover_wifi_scan` env). Our `ouimatch`/SSID classifier already
   supports this — firmware work, not architecture work.
6. flock-you firmware is educational-licensed → read code as spec, build
   our own firmware.

## Physical assembly topology (Pi 5 rig)

```
enclosure lid    ALFA (RP-SMA out)   RTL-SDR (SMA out, ≥10 cm away)
                    │                      │
enclosure inside ─ Pi 5 ── powered USB hub ── GPS ── ESP32 ×2 (direct USB)
power: official 25W PSU (mains) | PD bank + hub (portable)
```

- ESP32 sensor boards on lid / pigtails, away from the Pi's switching
  noise, antennas out.
- **Disable the Pi's own WiFi/BT** (`rfkill block wifi bluetooth`) so the
  rig never counts itself. ESP32s don't advertise while scanning — the Pi
  would.
- Bench-first: validate with PSU + simulator, then build enclosure.
