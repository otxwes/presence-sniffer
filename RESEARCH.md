# Prior-art research (2026-09-14)

Survey of existing projects/patches relevant to presence-sniffer, so we build the
right differentiators and reuse what's proven.

## 1. Sensing layer (closest prior art)

| Project | What it is | What we can reuse |
|---|---|---|
| **ruvnet/RuView** (94k★) | ESP32 CSI "WiFi sensing" platform: presence, breathing, pose through walls; MQTT/HA integrations | The *ambitious ceiling* — CSI gives motion/vitals, not just device counts. Its MQTT event schema is a good reference for our snapshot model. Heavy: needs ESP32-S3 + models. Note: overly-vital-signs claims are unproven at scale. |
| **simeononsecurity/eye-spy** | M5Stack/ESP32 passive BLE+WiFi surveillance detector: OUI/UUID/name matching for cameras, ALPR (Flock/Vigilant), AirTags, drones; confidence score with decay | **Directly relevant**: OUI/UUID classification tables (Flock, Axon body cams, Meta glasses, OpenDroneID) are exactly our `device_class` vocabulary. Passive-only scanning stance matches our design. PlatformIO firmware we can adapt — including an `Axon body cam` class feeding a dramatic audio mapping. GitHub rate-limit caveat: their identity classification of "police" hardware is probabilistic OUI matching, not identification of people. |
| **simeononsecurity/flock-you-esp32** | Sibling project focused on Flock safety camera detection | OUI table source. |
| **The-Masked-Bear/wifisense-pi**, **CSIght**, **SWEENEX** | ESP32 CSI motion/presence radar demos | If we want motion-reactive audio (gesture → filter sweeps) later. |
| **KaSaNaa/ESP32-WiFi-Sniffer**, **stalss/passive-wifi-crowd-counter**, **Grostl/esp32-mac-collector** (ESP32-C5 dual-band!) | Promiscuous-mode probe-request sniffers | Phase 1 firmware starting points; esp32-mac-collector conveniently targets the ESP32-C5 (dual-band 2.4/5G + BLE) recommended in our hardware table. |
| **MohRaouf/BLE-RTLS-Scanner** | ESP32 BLE RSSI scanner → server | Serial/HTTP event format reference for our `SerialBleSensor`. |
| **Nordic nRF Sniffer for BLE / 802.15.4** (nordicsemi) | Reference BT sniffer firmware | As planned in Phase 1. |
| **Kismet** (+ the `wid-dle-wemote` DEF CON art install) | Full multi-radio passive capture framework with MQTT/web APIs | The "industrial" path: a Pi running Kismet gives us WiFi+BT instantly; our aggregator could just consume Kismet's REST/MQTT instead of custom Scapy code. Worth prototyping before writing raw pcap code. |
| **sidechained/Amalgam** | Interactive sonification of wifi data (exact concept as ours) | Small repo (0★) — worth reading to avoid duplicating and to differentiate. |
| **simeononsecurity** scoring model | Score-with-decay / cooldown discipline | Pattern we should steal: `threat_level` style single-value outputs map beautifully to a single audio macro. |

## 2. Ableton / OSC layer (don't build what exists)

| Project | Stars | Notes |
|---|---|---|
| **ideoforms/AbletonOSC** | 803 | Python daemon providing a full OSC API *into* Live (play clips, set params). Complements ours: we send sensor OSC, it can drive Live's transport/params programmatically. |
| **Simon-Kansara/ableton-live-mcp-server** | 394 | MCP/LLM control of Live over OSC — shows the OSC API pattern again. |
| **stufisher/LiveOSC2**, **willrjmarshall/AbletonOSC** | 101/34 | Older generations of the same idea. |
| **grufkork/rkbx_link** | 116 | Ableton Link ↔ lights/OSC sync — useful if we later sync visuals. |
| Max built-ins | — | `udpreceive` + `OSC-route` (CNMAT) means a purpose-made M4L device is ~1 hour of wiring; the ecosystem doesn't need us to ship another OSC router, only our *mapping* is the value. |

## 3. Conclusions for our build

1. **Hybrid sensor strategy**: ESP32 (our own firmware forked from esp32-mac-collector /
   passive crowd counter) for cheap presence + reuse **eye-spy's OUI/UUID classification
   tables** as the device-class vocabulary → `device_class` becomes
   `body_camera/ALPR/tracker/airtag/drone/phone/...` without inventing anything.
2. **Consider Kismet as a Pi sensor backend** before writing raw Scapy capture code;
   wrap it behind our `sensors/` interface either way.
3. **Keep our OSC design** (small custom messages) — it feeds both our M4L patch and
   AbletonOSC simultaneously. Optionally add `AbletonOSC` as a plugin backend so the
   music can *self-perform* (launch clips) based on presence, not just modulate macros.
4. **Adopt a `threat_level`-style composite output** (eye-spy's score/decay/cooldown
   model) as an extra aggregated metric — it's a great single macro for Ableton and
   fits the honest "crowd/atmosphere" framing.
5. Differentiation vs. Amalgam/one-off art installs: a **portable, bus-abstracted,
   multi-radio (WiFi+BLE+SDR) instrument with a reusable OSC contract** — no one
   seems to have published that combo open-source.
