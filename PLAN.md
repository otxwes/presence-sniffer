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

### Bench bring-up

See **[BENCH.md](BENCH.md)** — step-by-step once parts are in hand: Pi
standalone headless → ALFA monitor mode → RTL-SDR / GPS → ESP32 flashing
through cables → full-hub integration → pipeline smoke test → enclosure last.

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

### Phase 1 hardware

See **[HARDWARE.md](HARDWARE.md)** — single authoritative BOM, vendor list,
recorded decisions, and physical build topology.

## Progress state (durable memory — update at each session end)

**As of 2026-10-24** — **BENCH.md is the live bring-up source of truth**;
its stage headers carry the ✅/⏳ status.

- **Hardware: 1 OPEN ORDER.** Original cart purchased 2026-09-19 (≈ $320 +
  shipping) and delivered. Both RTL-SDR Blog V3 units were DOA, so a
  **Nooelec NESDR SMArt v5 Bundle** was ordered 2026-10-24 ($54.95 +
  shipping, nooelec.com) as the replacement sensor + bench control. ASINs +
  decision history live in HARDWARE.md; do not re-order the original cart.
- **Bench progress:**
  - Stage 0 (unbox/inspect): ✅
  - Stage 1 (Pi 5 headless, `sniffer.local`, user `otxwes`): ✅ closed 2026-10-04
    (Imager lessons recorded in BENCH.md).
  - Stage 2a (ALFA AWUS036ACM): ✅ proven 2026-10-04 — monitor mode via
    `sniffer-monitor.service` (enabled at boot); hub must run on its own 5V/4A
    wall brick. BT killed at firmware level (`dtoverlay=disable-bt`); Pi's wlan0
    stays up as management channel (revised posture in BENCH.md).
  - Stage 2b (RTL-SDR): ⚠️ **both units DOA** — unit #1 2026-10-18, unit #2
    (Amazon replacement) 2026-10-24, byte-identical tuner-PLL failure;
    cross-host proof (Pi + Mac, stock + official Blog-fork drivers). Refund
    in progress. **Nooelec NESDR SMArt v5 Bundle ordered 2026-10-24** as the
    replacement + control; on arrival run the 4-check test in BENCH.md
    Stage 2 — pass closes 2b and exonerates the bench, fail points at the
    bench. `rtl-sdr` pkg + DVB blacklist on the Pi stand.
  - Stage 2c (GPS PA1616S): ⏳ not started.
  - Stage 3 (XIAO ESP32-S3 ×3): ✅ **2026-10-24** — all three boards
    flash-verified (MACs `b8:1f:3f:d9:28:d8` = WiFi, `44:b1:76:b0:55:68` =
    BLE, `44:b1:76:ae:d5:0c` = spare; 8 MB flash + 8 MB PSRAM each). WiFi
    `wifi_probe` firmware verified live on board 3 (spare): real probe
    requests captured, host adapter + aggregator end-to-end, 30 tests pass.
    Flash the same image to board 1 for the WiFi role; BLE listener next.
  - Stage 4 (full hub integration): ⏳.
  - Stage 5 (smoke test with `presence/sensors`): ⏳.
- **Known enclosure consequence:** PANPEO couplers are keystone snap-in →
  `case.scad` cutout is a **keystone slot (~30×16 mm + retention lip)**, not the
  previously assumed ~22.5 mm round hole. Active Cooler blower vent also required.
- **Approved next slice (2026-10-24) — BLE listener vertical:** board 2 verified
  on the Pi (`44:B1:76:B0:55:68` → `/dev/ttyACM1`; board 1/WiFi stays
  `/dev/ttyACM0`). Scope:
  1) ✅ **2026-10-24** `firmware/ble_scan` v0.1 (core BLE lib, no new
  dependency): **passive** BLE scan, per-address dedupe/report at ~1 Hz, JSON
  `{ts_ms, mac, rssi, name|null}` (v1 drops `addr_type` — randomized RPA
  addresses are the norm) + heartbeat; 556,748 B / 27,520 B RAM; flashed and
  live-verified (4 distinct devices, anonymized events flow; BENCH.md);
  2) ✅ **2026-10-24** `SerialBleSensor` parser + 18 TDD tests (anonymize,
  `band="ble"`, `source="ble-esp32"`, no raw MAC downstream); live-verified
  on board 2 (53 events / 15 s, 4 devices; suite 48 passed both venvs);
  3) ✅ **2026-10-24** aggregator `--serial-ble` running both sensors
  concurrently (`build_serial_sensors`, 6 TDD tests; suite 54 passed);
  stable by-id ports chosen instead of extra udev rules (MAC-derived);
  4) ✅ **2026-10-24** bench evidence of both boards live: 45 events / 14 s,
  snapshots sustained at density=4 (BLE keeps the window fed where WiFi-only
  sat at 0); OSC unchanged; BENCH.md.
  Caveat recorded: BLE random MACs inflate density/churn — density counts
  radio endpoints, not people.
- **ALFA environment slice (decided 2026-10-24, not started):** use the ALFA
  (`wlan1`, monitor) as a **WiFi-environment sensor**, not a second presence
  sensor. First metrics: `wifi_aps` (unique BSSIDs) and `wifi_busy`
  (non-beacon frame rate/airtime, excluding the Pi's own MAC/BSSID), 5 GHz
  first; optional 2.4 GHz AP beacons and `wifi_5g_share` later. Root Scapy
  capture → localhost UDP → aggregator → OSC `/wifi_aps`, `/wifi_busy`;
  existing density/churn/proximity untouched. Evidence: 45 s idle capture
  saw **1 unique 5 GHz probe device vs 18 BSSIDs and ~27 frames/s**
  (BENCH.md) — the environment layer is the real enrichment.
  Nooelec SDR later: Stage 2b four-check control test first (unit #2 refund
  held), then `rf_warmth`/RF environment; it cannot see 2.4/5 GHz WiFi/BLE.
- **Then:** enclosure last — caliper real parts, print, snap in keystones.
- **Standing decisions locked** (see HARDWARE.md §Decisions): S3 pair over C5/C6
  for v1; Kismet excluded; HackRF/Ubertooth/AX210 deferred; SDR replacement =
  Nooelec SMArt v5 Bundle (2026-10-24) after both Blog V3 units were DOA;
  V4L rejected (needs Blog driver fork, dongle-only).

