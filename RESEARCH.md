# Prior-art research (2026-09-14; re-verified 2026-09-15)

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

## 4. Verification sweep (2026-09-15)

Every referenced repo was re-checked live. **Verdict: the research conclusions
still hold** — the OUI/vocab, scoring/decay, ESP32-C5, and AbletonOSC strategies
are all based on things still current or newer than when notes were written.

### Confirmed active / relevant

| Project | Status at re-check | Impact on us |
|---|---|---|
| ruvnet/RuView | Still very active (94.1k★, 1,356 commits; now includes wifi-densepose pose/vitals models + Rust/C++ CSI stack). Note: CSI claims (through-wall pose/vitals) are demo-grade, not proven at scale — keep as ceiling only. | Ceiling reference only; our scope (passive presence/density) unchanged. |
| simeononsecurity/eye-spy | Active (9★, v1.1). **New since first research: now has experimental LILYGO T-Dongle C5 build** — ESP32-C5 dual-band WiFi 6 + BT 5, the exact chip family in our hardware plan. Detection tables now well structured: 35 FLOCK_OUIS, 6 FLOCK_MFR_OUIS, 31 CAM_OUIS, RSSIDB −90dBm cutoff, −1 point/60s decay, host-side native test suite (32 Unity tests). | **Best candidate firmware base.** Testable OUI tables we can import directly; its confidence/decay/cooldown model is even more solid than assumed. |
| simeononsecurity/flock-you-esp32 | Active (18★; port of colonelpanichacks/flock-you, which is the real root repo). Full BOM ($9–11), datasets/ dir, and multiple OUI sources credited (NitekryDPaul, DeFlockJoplin, Will Greenberg BLE mfg IDs). | OUI dataset provenance now documented — good for sourcing ethically/verifiably. |
| **bennjordan/flock-you** (flagged 2026-09-15) | 112★; another actively-maintained port of colonelpanichacks/flock-you (Xiao ESP32-S3). Ties together DeFlock + GainSec datasets in its `datasets/` + `oui.txt`; output is **structured JSON over serial** (`{ts, rssi, mac}`) + web dashboard, plus CSV via Python tool in `api/`. Detection: WiFi promiscuous + BLE scan + MAC OUI + SSID pattern + BLE device-name pattern matching. | **The most complete flock-you family repo for our purposes** — for our `esp32_serial` sensor this is the best single source: serial JSON already structurally matches our `PresenceEvent` (ts, rssi, mac), removing parse work. |
| **JakeSwiz/flock-you-wifi-recon** (flagged 2026-09-15) | 106★; focused ESP32-WROVER firmware for **WiFi-only Flock ALPR detection** (informs the whole flock-you family that Falcon/Sparrow ALPR cameras are WiFi-only, not BLE — BLE hits are only Ravens/gunshot detectors + bonnet-mounted). Documented false-negative story on a real OSM-located ALPR; matches probe requests via SSID patterns (`Flock-XXXXXX`, `test_flck` from CVE-2025-59409) + the flock-you OUI list; line format `MATCH(oui_flock) src:MAC ssid:... rssi:-70 ch:2 hits:8`. Cites upstream chain explicitly: colonelpanichacks/flock-you → wgreenberg/flock-you (BLE mfg-ID research, XUNTONG 0x09C8) → GainSec (Jon Gaines' 2025 writeups). | Very useful methodology reference: confirms (a) the flock-you OUI list is a live curated upstream we should import, (b) probe-request-based WiFi detection works **without** the camera's hotspot being on, and (c) SSID substring matching is a workable secondary signal class to add to our OUI table. Most transparent licensing/credit chain in the family. |
| Grostl/esp32-mac-collector | Active (2★, MIT). ESP32-C5 Arduino sketch, dual-band channel sweep + NimBLE concurrent BLE ads, MAC dedup (30s), log rotation, CSV to SD; prebuilt `.bin` available. Captures Data/QoS-Data/Null frames → real hardware MACs (vs randomized probe MACs). | Still our Phase 1 firmware starting point — now more useful (prebuilt binary + frame-type insight: randomised MAC randomization strategy matters). |
| stalss/passive-wifi-crowd-counter | Active (2★, ESP-IDF v5.1+, host-mocked native tests). Serial CSV report every 5 s (count/peak/rolling-avg/channel), OUI Phone/Laptop/IoT breakdown, configurable RSSI threshold + MAC expiry. | Event-report format reference; the "count/peak/rolling avg" shape maps well to our DensityStats. |
| KaSaNaa/ESP32-WiFi-Sniffer | Exists (6★, standard ESP32, ESP-IDF/PlatformIO). Basic probe-request sniffer, educational. | Noted, low priority; superseded by both eye-spy & esp32-mac-collector. |
| MohRaouf/BLE-RTLS-Scanner | Exists (11★, tiny 5-commit Arduino sketch, HTTP to server). | Serial/HTTP format reference, thin but fine for its purpose. |
| kismetwireless/kismet | Active mirror (2.2k★). Capture sources now include NRF52840, TI CC2540, sniffle-BLE, HackRF sweep, RTL433/ADSB/AMR, wifi_coconut — the multi-radio story is even stronger. | Kismet-as-Pi-backend plan is more valid than ever. |
| ideoforms/AbletonOSC | Active (803★). **Explicitly requires Ableton Live 11+** (Live 12 still supported as of re-check). Full LOM-mapped OSC API incl. `/live/device/set/parameter/value`. | Our planned "AbletonOSC self-performance backend" plugin idea is fully viable. |
| Simon-Kansara/ableton-live-mcp-server | Exists (394★, MIT; built directly on AbletonOSC). | Confirms AbletonOSC-based control pattern; not on our critical path. |
| stufisher/LiveOSC2 / willrjmarshall/AbletonOSC | Exist but stale (Live 9-era, 23/34 commits). | Keep as historical references only; don't base designs on them. |
| grufkork/rkbx_link | Active, 116★ (commercial-ish; Rust/Ableton Link & OSC to Rekordbox). | Useful for visual-sync ideas later, not core. |
| sidechained/Amalgam | Exists; dead (0★, SuperCollider + Pcapy, HTTP/transport-layer sonification). | Still just a prior-art reference for concept, not code to reuse. |

### Corrections to the original notes

- **wifisense-pi (The-Masked-Bear)** — repo exists (115★) but was **archived Sep 6,
  2026**, now read-only. Still a great CSI-DSP reference (it moved us from "CSI is
  aspirational" to "CSI with working breathing/pose numbers"), but do not expect
  upstream fixes. High educational value for `/dsp/` architecture regardless.
- **CSIght** — the GitHub repo name could not be confirmed on re-check; it appears
  to be a **research-group paper/website**, not a repo we can pull from. Downgrade
  to paper-citation status; don't plan around its code.
- **SWEENEX** — name not resolvable as a repo URL from our notes; keep flagged
  as needing a proper source link before it can be cited in docs.
- **nRF Sniffer for BLE** — official Nordic GitHub repo name could not be
  confirmed with the tooling available (403/404s on multiple guessed names). The
  product itself is alive per Kismet's `capture_nrf_52840` support, but verify the
  exact repo URL + firmware license before buying hardware around it.
- **flock-you family licensing** — colonelpanichacks/flock-you and
  simeononsecurity's fork are Apache/CC-BY-SA, but **bennjordan/flock-you carries
  a custom "educational and research purposes" notice, not a standard OSS
  license**. Import its *OUI/SSID datasets* (facts, sourced from deflock.me /
  GainSec) with credit; **do not copy its firmware code** into our repo unless
  the license is clarified. JakeSwiz's repo is a fork of colonelpanichacks —
  inherit licenses from that root after review.

### Hardware-market re-check (late 2026)

- **ESP32-C5** (dual-band 2.4/5 GHz + BLE) is now shipping and appears in TWO of
  the active repos above (eye-spy LILYGO T-Dongle C5 build, esp32-mac-collector).
  Recommendation: make ESP32-C5 the sensor tier standard going forward — it
  replaces the two-chip ESP32+ESP32-C6 starter tier from PLAN.md with one board.
- **Kismet now natively supports the nRF52840 dongle** (`capture_nrf_52840`),
  meaning the Pi-side BLE capture and Pi-side Wi-Fi capture can both be Kismet
  data sources, and our aggregator needs only ONE backend adapter for the whole
  Pi rig — a likely simplification of Phase 1/2.

## 5. Police-presence proxy layer (2026-09-15)

**Framing (restated precisely):** we cannot detect "police"; we can only detect
*proxies* — hardware and signals statistically correlated with public-safety
activity. The system reports **device classes with confidence**, never identity.
This layer's output is a `surveillance_proxy` composite, not a police-detector claim.

### A. Crowdsourced / public data feeds

| Source | What you get | Access reality (verified 2026-09-15) |
|---|---|---|
| **Waze** | User-reported "police visible" alerts | Official "Waze for Cities" program is **municipal/agency-only** (application-gated to public agencies/event operators). App scraping violates ToS; no public police-report API. **Not available — do not plan around it.** |
| **City open data (CAD/RMS via Socrata/CKAN)** — NYC, SF, Seattle, Chicago, etc. | Timestamped 911-incident records with type + lat/long | Public REST endpoints in most large cities; some delayed minutes–hours |
| **State 511 / traveler-info APIs** | Live road incidents incl. "police activity" markers | Public REST per state; fragmented but machine-readable |
| **Citizen app** (60+ cities, 911-integrated) | Real-time geolocated incident alerts | Per-incident public web pages; official API partner-gated |
| **Broadcastify archives** | Timestamped dispatch archives for many US agencies | Freemium; use as a **weak-label** source (below), not realtime fusion |
| **OpenSky / ADS-B Exchange** | Aircraft ADS-B w/ type+registration; law-enforcement helicopters broadcast openly | Free public APIs; **highest-reliability single proxy** — aircraft don't randomize IDs |
| **deflock.me** | Crowdsourced ALPR/Flock camera map + API | Public; static locations → known-location priors |

**Fusion rule:** every feed above enters as a `crowd`-source `PresenceEvent`
(device_class `incident` or the feed's inferable class) carrying its own honest
timestamp — delayed sources are never backdated. All access must respect ToS.

### B. Higher-confidence inference (model plan)

Level 1 — lookup/fingerprint layer (no learning):
- OUI/SSID/BLE-name pattern tables (eye-spy + flock-you vocab), per-table weights.
- Known-location priors from deflock.me + city CAD locations.

Level 2 — supervised, trained on our own logs:
1. **Feature stack **per device/time-window: OUI matches, SSID matches, RSSI
   delta/churn (movement pattern), MAC persistence, band balance, time-of-day,
   distance to known Flock/Axon device, helicopter proximity (OpenSky),
   dispatch-channel activity (Broadcastify alignment). Implemented as
   `SignalFeatures` / `build_feature_stack()` in `presence.sensors.crowd_proxy`.
2. **Weak labels:** Broadcastify archive *timestamps* for an agency channel →
   periods of active dispatch; RF detections co-occurring with dispatch spikes
   become labeled "police-adjacent".
3. **Model class:** logistic regression / gradient-boosted tree over ~15
   features (sklearn is already the stack). Expectation: OUI/SSID layer alone
   reaches ~80–90% precision on *device class* for well-represented vendors
   (Axon per eye-spy's data); event-level confidence only becomes meaningful
   once ADS-B + dispatch *context* fusion is in. Temporal encoders are
   premature until Level 2 works.

### C. Plan changes adopted

1. PLAN.md Key risks #1 reworded: detection is a probabilistic proxy via
   device-class inference; the system reports device classes with confidence,
   never identity.
2. `device_class` vocabulary extended: `body_camera`, `alpr`, `police_helo`,
   `drone`, `tracker`, `incident` (feed-derived).
3. New Phase-1-adjacent sensor: `crowd_proxy.py` (crowd-feed adapter; future
   `adsb_sensor.py` for the ADS-B path).



## Wardriving-design verification (2026-09-15)

Sources checked against our Phase 1 BOL and event pipeline:

1. **Kismet datasources documentation** (kismetwireless.net/docs/readme/datasources/)
   Their standard wardrive rig checklist maps onto ours:
   - WiFi: Linux monitor-mode adapters → **our ALFA MT7610U/MT7612U matches**
   - GPS: `gpsd`/serial GPS → **our u-blox module matches** (plugs into `SurveillanceContext`)
   - BLE: Linux HCI scanning is their baseline → our ESP32-BLE board is equivalent capability
   - Fancier radios (Ubertooth, nRF52840, Wifi Coconut, Zigbee SDR) are their
     optional extensions — mirrors our deferred list (Ubertooth etc.)
   - RTL-SDR as Kismet datasource (rtl_433/Zigbee) → validates our SDR lane
   - Kismet "wardrive mode" exists → if we ever want formal wardriver mode,
     Kismet could even be an *optional* passenger process on the Pi 5 for
     WiGLE-format logging; not v1.

2. **Wardriver.uk rev3** (wardriver.uk) — closest open-source analog:
   rev3 rig = **2× ESP32 (one for 2.4 GHz WiFi scan, one for BLE) + GPS + SD**,
   with IPEX external antennas, producing WiGLE-uploadable CSV.
   - **Directly validates our radio split**: two ESP32s, one per radio,
     is the exact architecture the mature DIY wardriver community converged on.
   - Deviation: they store CSV to SD card and upload to WiGLE; we ingest over
     serial JSON into the event bus with a decaying window. Same sensing,
     different retention (ours is ephemeral by design).
   - If a WiGLE-submission mode is ever wanted, their GitHub source defines
     the CSV field format to write.

3. **WiGLE FAQ / EULA** (wigle.net/faq):
   - Confirms accepted formats (Kismet netxml/nettxt/csv, Android app csv…)
     — sets the export contract if we ever emit a wardriver mode.
   - Community etiquette: submission not paired to people; fake data = ban;
     AP owners can request record removal by BSSID. Our design (hashed,
     decaying-window, no persistent person-scale history) is **stricter** than
     the community norm — good for the exhibition framing.
   - Notable: they warn users that anyone asking them to wardrive *for them*
     may be soliciting SIGINT for illegal acts — consistent with our
     "never a person/role identifier" stance in RESEARCH §5.

**Verification verdict:** hardware capability matrix matches the standard
wardriving literature with no gaps and two conscious deviations
(event-shaped serial ingestion; ephemeral retention). The rig *is*
wardriver-capable hardware; our v1 software is deliberately not a
wardriver (see PLAN mode-boundaries).

Retention caveat: current design stores no per-AP location history. If
we later implement `--log-formal wifi` (wardriver mode), reuse
Wardriver.uk's CSV format for WiGLE compatibility and honor the
removal-by-BSSID norm.

