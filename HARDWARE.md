# HARDWARE.md — Phase 1 Bill of Materials

Re-verified **2026-09-19**. Total ≈ **$260–300** (all in stock at listed sources).

## Buy list

| # | Item | ~Price | Source (verified) | Notes |
|---|---|---|---|---|
| 1 | Seeed XIAO ESP32-S3 ×3 — **pre-soldered, plain non-Sense** | $25 (~$8 over unsoldered) | [seeedstudio.com US warehouse](https://www.seeedstudio.com/XIAO-ESP32S3-p-5627.html) | 1 board → WiFi promiscuous, 1 → BLE, 1 → spare (S3 is single-radio). Pre-soldered: fewer assembly variables while prototyping; headers removable later if needed |
| 2 | Pi 5 **4GB board-only** + CanaKit 5A PD PSU ($14.95) + official Active Cooler ($11.95) + 32GB+ A1 microSD (Amazon) | ≈ $148 | canakit.com (cheapest in-stock 4GB; Vilros 4GB OOS, Adafruit $130) | PSU must negotiate **5V/5A PD** or USB budget drops to ~600 mA. Active Cooler, not the CanaKit Mega+Fan bundle (that requires their Turbine case; ours is custom). Skip micro-HDMI: headless via SSH, WiFi/SSH pre-configured in Pi Imager |
| 3 | ALFA **AWUS036ACM** (MT7612U) | $25–40 | [store.rokland.com](https://store.rokland.com) (authorized; Amazon sold-by-Rokland alt; Newegg scalped ~$90) | Linux monitor mode, dual-band. ACM > ACHM (MT7610U, stock spotty; AR9271 NHA is EOL) |
| 4 | RTL-SDR Blog **V4** (budget alt: V4L Lite) | $40 | [rtl-sdr.com/store](https://www.rtl-sdr.com/store/) | `rf_warmth` + wideband drone-RF; current as of Aug 2026 |
| 5 | GPS: Adafruit Ultimate **PA1616S** | $29.95 | [adafruit.com/product/746](https://www.adafruit.com/product/746) — low stock (~29 left) | NMEA/UART → `gpsd` → `SurveillanceContext` distance math. Budget alt: Seeed L76K ($10.9), XIAO-shield format — only if GPS routes via an ESP32 |
| 6 | Powered USB hub + USB-A extensions ×4 + USB-C pigtails + ferrite chokes | ~$30 | Amazon / PiShop | Commodity. Antennas exit case; SDR ≥10 cm from the ALFA |

Power: mains via the CanaKit PSU. Portable option: 100W PD power bank (~$30–50 extra).

## Decisions recorded (do not re-litigate without new evidence)

1. **ESP32-S3 over ESP32-C5** — C5 dual-radio concurrency unverified. Watch: XIAO **ESP32-C6** (~$7, WiFi-6 dual-band + BLE5); flock-you C6 port exists (`storskegg/flock-you-c6`, immature Feb 2026). One C6 could replace the S3 pair if it matures. Not v1.
2. **Kismet excluded from v1** — heavy process, packet-shaped data vs our event-shaped pipeline.
3. **Deferred**: HackRF (~$350; V4 covers the scorer's inputs), Ubertooth One (payload-level BLE; features are event-shaped), AX210 6 GHz (no PCIe path).
4. **Firmware spec source:** modern Flock ALPRs (Falcon/Sparrow) do NOT beacon on BLE. Productive path = WiFi probe requests: SSIDs `Flock-XXXXXX` / `test_flck`, OUIs `B4:1E:52` (Flock direct) and `E4:AA:EA` (Liteon); channel-hop 1–11 every 400 ms. Spec off `github.com/JakeSwiz/flock-you-wifi-recon` (`esp32_wrover_wifi_scan` env). Our `ouimatch`/SSID classifier already supports this — firmware work, not architecture work. Educational license → read code as spec, build our own firmware.

## Physical assembly topology (Pi 5 rig)

```
enclosure lid    ALFA (RP-SMA out)   RTL-SDR (SMA out, ≥10 cm away)
                    │                      │
enclosure inside ─ Pi 5 ── powered USB hub ── GPS ── ESP32 ×2 (direct USB)
power: CanaKit 5A PSU (mains) | PD bank + hub (portable)
```

- ESP32 sensor boards on lid / pigtails, away from the Pi's switching noise, antennas out. Vent the print over the Active Cooler blower.
- **Disable the Pi's own WiFi/BT** (`rfkill block wifi bluetooth`) so the rig never counts itself. ESP32s don't advertise while scanning — the Pi would.
- Bench-first: validate with PSU + simulator, then build enclosure.