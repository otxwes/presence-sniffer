# HARDWARE.md — Phase 1 Bill of Materials

Re-verified **2026-09-19** (SDR row re-verified 2026-09-15). Total ≈ **$275–315** (all in stock at listed sources).

> **STATUS: ✅ ALL ITEMS PURCHASED — 2026-09-15.** Full cart ordered (total ≈ $320 + shipping). Awaiting delivery for the bench sequence. See row notes for verified ASINs/sources. Do not re-order.

## Buy list

| # | Item | ~Price | Source (verified) | Notes |
|---|---|---|---|---|
| 1 | Seeed XIAO ESP32-S3 ×3 — **pre-soldered, plain non-Sense** | $25 (~$8 over unsoldered) | [seeedstudio.com US warehouse](https://www.seeedstudio.com/XIAO-ESP32S3-p-5627.html) ✅ **PURCHASED 2026-09-19 (pre-soldered ×3)** | 1 board → WiFi promiscuous, 1 → BLE, 1 → spare (S3 is single-radio). Pre-soldered: fewer assembly variables while prototyping; headers removable later if needed |
| 2 | Pi 5 **4GB board-only** + CanaKit 5A PD PSU ($14.95) + official Active Cooler ($11.95) + 32GB+ A1 microSD (Amazon) | ≈ $148 | canakit.com (cheapest in-stock 4GB; Vilros 4GB OOS, Adafruit $130) ✅ **PURCHASED 2026-09-19 (CanaKit 4GB + 5A PD PSU + Active Cooler)** | PSU must negotiate **5V/5A PD** or USB budget drops to ~600 mA. Active Cooler, not the CanaKit Mega+Fan bundle (that requires their Turbine case; ours is custom). Skip micro-HDMI: headless via SSH, WiFi/SSH pre-configured in Pi Imager |
| 3 | ALFA **AWUS036ACM** (MT7612U) | **$46.97** | [store.rokland.com](https://store.rokland.com/products/alfa-awus036acm-802-11ac-dual-band-2-4-5-ghz-wifi-usb-adapter) (authorized; Amazon sold-by-Rokland alt; Newegg scalped ~$90) ✅ **PURCHASED 2026-09-19 (Rokland)** | Verified on Rokland page 2026-09-19: MT7612U, dual-band, 2× RP-SMA detachable antennas included, in-kernel driver since 4.19 (no install needed on Pi OS). Price +$12 over our old $25–40 estimate; Newegg scalped, so this is the honest price |
| 4 | RTL-SDR Blog — **V3 R860, dongle-only (Black)** | ~$35 (Amazon hides price; click to see) | Amazon `dp/B0BMKZCKTF`, **sold via the official RTL-SDR Blog storefront** (verify seller + R860 in title; avoid all "V4"-titled Amazon listings — clones like SBJKBVMF use R828D) ✅ **PURCHASED 2026-09-19 (Amazon `dp/B0BMKZCKTF`, official storefront)** | Flip from V4L (2026-09-19 decision): V4L is NOT on Amazon US, and rtl-sdr.com's own store warns US buyers to use Amazon due to China-shipping + new tariffs (risk of surprise duties/customs on a $38 item). V4L's real deltas lost: HF upconversion (HF is unused here — our bands are VHF/UHF/ISM), sub-dB R828S tuning advantage (unmeasurable for rf_warmth). R860 covers same ~500 kHz–1.7 GHz ceiling. Do not buy the V3 clone listings under random brands either |
| 5 | GPS: Adafruit Ultimate **PA1616S** | $29.95 | [adafruit.com/product/746](https://www.adafruit.com/product/746) — low stock (~29 left) ✅ **PURCHASED 2026-09-19** | NMEA/UART → `gpsd` → `SurveillanceContext` distance math. Budget alt: Seeed L76K ($10.9), XIAO-shield format — only if GPS routes via an ESP32 |
| 6 | Hub, pass-through cables & ferrites | ~$30 | ✅ **ALL PURCHASED 2026-09-19:** [atolla 8-port USB 3.0 powered hub w/ per-port switches + 5V/4A adapter (`B07G8CMR18`)](https://www.amazon.com/dp/B07G8CMR18) + [EGSCST 25-pc ferrite kit (`B0H6N24XH6`)](https://www.amazon.com/dp/B0H6N24XH6) + [SUNGUY 1 ft USB-A M→USB-C M data cable, 3-pack (`B0D12JLQMT`)](https://www.amazon.com/dp/B0D12JLQMT) — sold by SUNGUY Direct, explicit "Data Transfer" spec (USB 2.0/480 Mbps-capable; ample for ESP32 serial/flashing) + [PANPEO USB 3.0 keystone coupler F/F, 2-pack (`B0FF41114Q`)](https://www.amazon.com/dp/B0FF41114Q) — Amazon's Choice, 5 Gbps F↔F pass-through, snap-in keystone form factor | Hub covers our ~1.5–2 A peak (ALFA+RTL-SDR+2×ESP32+GPS) with headroom; per-port bench switching. Ferrites on USB/power, NOT near antenna feeds. ❌ B0DLKPWF1G "11 in pigtail" rejected (power-only 2-pin bare wire); ❌ HuiKeTek `B0DPF82QC1` 6-in cable rejected (charge-only, no data spec). Keystone form factor → enclosure cutout is a keystone slot (~30×16 mm + retention lip), not the ~22.5 mm round hole originally assumed |

Power: mains via the CanaKit PSU. Portable option: 100W PD power bank (~$30–50 extra).

## Decisions recorded (do not re-litigate without new evidence)

1. **ESP32-S3 over ESP32-C5** — C5 dual-radio concurrency unverified. Watch: XIAO **ESP32-C6** (~$7, WiFi-6 dual-band + BLE5); flock-you C6 port exists (`storskegg/flock-you-c6`, immature Feb 2026). One C6 could replace the S3 pair if it matures. Not v1.
2. **Kismet excluded from v1** — heavy process, packet-shaped data vs our event-shaped pipeline.
3. **Deferred**: HackRF (~$350; V4 covers the scorer's inputs), Ubertooth One (payload-level BLE; features are event-shaped), AX210 6 GHz (no PCIe path). Note 2026-09-15: SDR platform downgraded to genuine **V3** (Amazon official storefront) — rtl-sdr.com's own checkout warns US buyers off direct orders (China ship + tariffs); V4L unavailable on Amazon; V4 deltas (HF upconversion, R828S) unused by our features. Top spec held in reserve if HF ever enters scope.
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