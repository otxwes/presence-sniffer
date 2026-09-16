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

### Phase 1 hardware list (finalized 2026-09-15 — buy in this order)

| Item | ~Price | Feeds which code |
|---|---|---|
| Seeed XIAO ESP32-S3 ×2 | $28 | edge sensor (WiFi promisc + BLE scan), flock-you firmware family; ×1 spare |
| Raspberry Pi 5 (4GB) + case + 128GB SD | $95 | aggregator host (`presence.aggregator`) |
| ALFA AWUS036ACHM (AR9271) | $25 | WiFi monitor mode (`WifiSensor`) |
| RTL-SDR Blog V4 | $35 | `rf_warmth` + wideband drone-RF (turns the stubbed snapshot field real) |
| u-blox NEO-6M / MAX-M10 GPS (USB/UART) | $15 | `SurveillanceContext` distance math (deflock/OpenSky are lat/lon-dependent) |
| 20Ah PD power bank (45W USB-C), cables, heatsinks, enclosure | $50 | portable rig |

Total ≈ $248.

Decisions recorded (do not re-litigate without new evidence):
- **ESP32-S3 chosen over ESP32-C5** — C5's dual-radio concurrency unverified;
  Xiao S3 is flock-you's native, shipped platform and does WiFi promiscuous +
  BLE scan on one board. Reconsider C5 only if 6 GHz needed later.
- **Kismet excluded from v1** — heavy process, packet-shaped data model vs our
  event-shaped pipeline; ESP32 edge-sniffing matches the pattern used by
  flock-you/DeFlock field deployments.
- **Deferred hardware**: Ubertoth One (raw BLE packet capture — our features
  never consume packet payloads), HackRF (~$350, V4 covers what the scorer
  reads), Intel AX210/6 GHz (no PCIe path on the Pi rig).
- flocked-you firmware is educational-licensed: **read its code as spec**
  (serial JSON `{ts, rssi, mac}`, OUI/SSID/name detection methods), build
  our own firmware from that spec.

2. Build against the simulator first; live data requires external radios.
3. Pi USB Wi-Fi dongles are finicky; verify AR9271 chipset before buying.
4. Pi 5 needs ~15W: good 5V/3.2A+ PD power bank + trigger board.
