# Portable Device-Presence Sniffer → Audio/Visual Instrument

Sensing nearby Wi-Fi / Bluetooth / BLE devices passively, turning RF activity into a
local event stream, and mapping it into Ableton Live (OSC) and visualizations.

**Framing (important):** this is a *crowd/presence-density instrument*. Passively
sensing that devices exist nearby (broadcast beacons / probe requests / BLE adverts +
RSSI) is legal almost everywhere. It does **not** and cannot identify specific people
or roles (e.g. "police"), and it must never be used for intercepting or decrypting
others' traffic. Design accordingly.

## Architecture

```
[Radio sensors: Wi-Fi/BT/BLE + SDR] → [Aggregator daemon (Python)] → [Local event bus]
                                                        ├→ Visualizer (Web / TouchDesigner)
                                                        └→ OSC bridge (UDP) → Ableton Live / Max for Live
```

Everything hangs off a single local event bus so sensors (Mac dev vs. Pi portable)
and consumers (visuals, audio) are independently swappable.

## Hardware plan

| Tier | Hardware | Covers | Cost |
|---|---|---|---|
| Starter | ESP32 (+ ESP32-C6) running sniffing firmware | 2.4GHz Wi-Fi probe requests + BLE adverts w/ RSSI | ~$15–30 |
| Portable | Raspberry Pi 5 + Nordic nRF52840 dongle (BT Sniffer) + monitor-mode Wi-Fi dongle (Atheros AR9271 / Panda PAU09) | Wi-Fi + Bluetooth discovery | ~$120 |
| RF layer | RTL-SDR Blog v3 (~$35) first; HackRF One (~$130) later for wideband spectrum | Arbitrary RF energy detection 24MHz–6GHz |

Note: macOS cannot put its internal Wi-Fi/BT into monitor/promiscuous mode — external
radios are required from day one. Mac runs dev + Ableton; Pi is the portable host,
bridged over its hotspot (OSC is network-transparent).

## Software stack

- **Wi-Fi (Pi):** Python + Scapy capturing probe-request frames w/ RSSI per device
- **Bluetooth BLE:** nRF Sniffer firmware / BLE advert listener (name, RSSI, class)
- **RF energy:** rtl-sdr / hackrf FFT → RMS noise-floor per band
- **Aggregator:** asyncio daemon publishing JSON events `{mac_hash, rssi, band, ts}` on the bus
- **Audio bridge:** Python → OSC over UDP → Max for Live
- **Visualizer:** Web UI (WebSocket + Canvas) — radial radar + density timeline
- **Portable runtime:** daemon + bridge on Pi; Ableton on laptop

## Phases

- **Phase 0 — dev environment:** project scaffold, event model, event bus, simulator,
  OSC bridge, EPS in Ableton via Max for Live. *(this scaffold)*
- **Phase 1 — sensors:** BLE adverts via ESP32 → daemon; Wi-Fi monitor mode on Pi dongle;
  **ADS-B helicopter-Proximity path (OpenSky) is the highest-reliability
  police-adjacent-proxy add** — it's Software-only and rides the existing
  `sensors/` interface via `crowd_proxy.py`.
- **Phase 2 — event model:** normalize to presence events: proximity bucket, churn
  (new devices/sec), density, band balance; RF "warmth" metric.
  **Surveillance-proxy feature stack** (`presence.sensors.crowd_proxy.SignalFeatures`):
  per-device/per-window row with OUI matches, SSID matches, RSSI delta/max,
  MAC persistence, band balance, time-of-day, distance-to-known-ALPR
  (deflock.me), helicopter proximity (OpenSky), dispatch activity
  (Broadcastify-weak-label training path); sklearn lr / GBDT on top planned.
- **Phase 2b:** outputs per device-class, including `surveillance_proxy`
  composite (eye-spy-style score with decay/cooldown), never a binary
  "police detected" flag.
- **Phase 3 — Ableton integration:** OSC → Max4Live macros:
  - proximity → volume / filter cutoff sweep
  - new-device churn → transient artifacts / bitcrush depth
  - density → delay feedback, granular glitch rate
  - RF warmth → pitch drift
- **Phase 4 — visualizer:** dark-mode radar + density timeline, glyph per device class.
- **Phase 5 — portable rig:** Pi hotspot + battery + small display; optional Pure Data
  fallback synth on Pi.

## Key risks / notes

1. Police presence is **not directly detectable** — the system reports
   probabilistic proxies (device classes with confidence, e.g. body cameras,
   ALPRs, law-enforcement helicopters) never identity. Framing in UI/audio
   copy must reflect that. See RESEARCH.md §5 for the proxy-layer plan.

### Phase 1 hardware list (re-verified 2026-09-15 against vendor sites — buy in this order)

| Item | ~Price | Feeds which code | Verification notes |
|---|---|---|---|
| Seeed XIAO ESP32-S3 ×3 | $21 | edge sensors; **1 board dedicated to WiFi promiscuous, 1 to BLE scan, 1 spare** | Current product, wiki live; S3 is single-radio → cannot do WiFi-mon + BLE simultaneously, hence one board per radio |
| Raspberry Pi 5 (4 or 8GB) + active cooler + case | $80–110 | aggregator host | Must be fed **5V/5A (25W)** via official PD supply, else USB port budget caps at 600 mA — see power note below |
| ALFA AWUS036ACHM (MT7610U, dual-band 2.4/5) *or* AWUS036ACM (MT7612U) | $25–35 | `WifiSensor` monitor mode | **Correction: ACHM is MT7610U, not AR9271** (that was the AWUS036NHA, now EOL). Both MT76xx adapters support Linux monitor mode; ACHM sold out direct from ALFA, buy via Amazon/resellers |
| RTL-SDR Blog V4 | $40 | `rf_warmth` + wideband | Still current (as of Aug 2026); cheaper **V4L "Lite"** variant now also available if budget-tight |
| u-blox GPS module (NEO-6M/7/M8N or PA1616S) | $12–25 | `SurveillanceContext` distance math | Generic modules fine; USB-ttl or I²C/UART |
| 100W-class PD power bank *or* official 25W PSU *plus* powered USB hub | $30–50 | portable vs mains power | Pi 5 with 5V/3A limits all USB to ~600 mA — our peripherals (WiFi ~500 mA, SDR ~250 mA, ESP32s, GPS) exceed it. Either 5V/5A PSU (mains) or a powered hub (portable) |
| USB-A extension cables ×4, USB-C pigtails, ferrite chokes, enclosure | $20 | physical build | Antennas must exit the case; keep SDR ≥10 cm from WiFi adapter (intermod) |

Total ≈ $250–290.

Decisions recorded (do not re-litigate without new evidence):
- **ESP32-S3 chosen over ESP32-C5** — C5's dual-radio concurrency unverified.
- **Watch item: XIAO ESP32-C6** (~$7, WiFi-6 dual-band + BLE5) — a flock-you
  C6 port exists (`storskegg/flock-you-c6`, immature as of Feb 2026). If it
  matures, one C6 could replace the S3 pair. Not v1.
- **Kismet excluded from v1** (heavy process, packet-shaped data model).
- **Deferred hardware**: HackRF (~$350, V4 covers the scorer's inputs),
  Ubertooth One (payload-level BLE, our features are event-shaped),
  AX210/6 GHz (no PCIe path).
- **Critical detection-time correction (2026 research):** modern Flock ALPRs
  (Falcon/Sparrow) **do NOT beacon on BLE** — the productive path is WiFi
  probe requests with SSIDs like `Flock-XXXXXX` / `test_flck` and OUIs
  `B4:1E:52` (Flock direct) / `E4:AA:EA` (Liteon contract mfr), channel-hop
  1–11 every 400 ms. Spec firmware off
  `github.com/JakeSwiz/flock-you-wifi-recon` (`esp32_wrover_wifi_scan`
  env), not the original BLE-only colonelpanichacks build. Our
  `ouimatch`/SSID classifier path already supports this — firmware work,
  not architecture work.
- flock-you firmware is educational-licensed: read code as spec, build own.

Physical assembly topology (Pi 5 rig):
```
enclosure lid          ALFA (RP-SMA exits)   RTL-SDR (SMA exit, ≥10cm away)
                          │                      │
enclosure inside ── Pi 5 ─┴─ powered USB hub ────┴── GPS ── ESP32 ×2 (direct USB)
power: official 25W PSU (mains) | PD bank + hub (portable)
```
- ESP32 sensor boards mounted on the enclosure lid or on pigtails, away
  from the Pi's board level components, antennas pointing out.
- **Disable the Pi's own WiFi/BT** (`rfkill block wifi bluetooth` or
  `dtparam=wifi_dt_params`) so the rig never counts itself; ESP32 boards
  don't advertise while scanning, so they don't self-count, but the Pi will.

2. Build against the simulator first; live data requires external radios.
3. Pi USB Wi-Fi dongles are finicky; verify AR9271 chipset before buying.
4. Pi 5 needs ~15W: good 5V/3.2A+ PD power bank + trigger board.
