# The Choir — a surveillance intervention installation

**Date:** 2026-11-08
**Status:** design draft for review; not approved for build
**Project:** presence-sniffer
**First context:** gallery / installation, 10-minute prototype loop
**Approach chosen:** The Choir (first prototype). The Purity Room is the control/fallback; The Mirror is a later gallery-scale evolution.

## 1. Intent and why

The piece is an intervention on surveillance, not a demo of sensors. Everyday personal
devices — phones, watches, earbuds, laptops — continuously broadcast signals that make
their owners visible to infrastructure. The installation makes that broadcast surface
audible and, through sound, gives the audience a felt choice: their devices both **augment**
the room (a choir of signals) and **corrode** it (a surveillance shadow), and deactivating a
device changes what the room becomes. The goal is awareness and agency: attendees should
leave noticing how much their devices render them visible, and having experienced that
turning something off changes the room.

The piece itself must not become the surveillance it critiques. It senses only broadcast
metadata, keeps raw identifiers at the sensor boundary, hashes what moves downstream, never
captures content, never identifies people, and never uploads. The visual shows aggregates,
not individuals. The police-detection / `surveillance_*` research lane is **not** part of
this installation; the subject is the everyday device broadcast surface, not a claim to
detect police or roles.

## 2. Goals, non-goals, anti-goals

### Goals

- A gallery/installation piece with a clear 10-minute loop and a legible audience journey.
- Devices audibly **augment** the sound (a choir/voices) and **corrode** it (a shadow), with
  deactivation producing an audible, rewarding change (clarity/intimacy), not just relief.
- Raise awareness of the devices' broadcast/visibility surface without identifying anyone.
- Use the existing sensing stack (XIAO WiFi + BLE, ALFA 5 GHz environment, Nooelec RF
  warmth), aggregator/OSC, and Max/Ableton; no new sensors are required for v1.
- Be reliable enough for a gallery prototype: auto-start, recover from ALFA/Nooelec
  hotplug, fail gracefully, and be operable by a non-author.
- Be testable with 3–5 people in a gallery-like setting before building the full visual and
  permanent enclosure.

### Non-goals (for this prototype)

- Detecting police, roles, or identity; using the `surveillance_*`/police-proxy lane.
- Capturing content, decrypting traffic, cameras, cloud uploads, or retaining raw MACs.
- A club/performance version; a phone-free staged performance; a commercial product.
- The full Mirror production, the final web visualizer, the permanent enclosure, the
  portable battery rig, GPS, or a calibrated spectrum analyzer.
- A perfect 1:1 map of every device in the room; the piece is a proxy for the surveillable
  surface, not a census.

### Anti-goals

- A punitive “turn off your phone” one-liner, or a piece that only makes noise.
- A piece that shames the audience, or that secretly surveils them.
- A piece that claims to detect police or to identify people.
- A piece that is unlistenable, that fails silently, or that requires technical knowledge.
- A piece whose “augment” is so pleasant that nobody experiments with deactivation, or whose
  “corrode” is so harsh that people leave.

## 3. Constraints

- **Venue:** gallery/installation with a captive audience, an intro/signage, and a listening
  room. The first prototype should be tested in a gallery-like space, not a loud club.
- **Duration:** 10-minute loop for the prototype; a longer gallery version later.
- **Sensors:** current stack is sufficient: board 1 WiFi probe requests (2.4 GHz), board 2
  BLE adverts (antenna attached), ALFA `wifi_aps`/`wifi_busy` (5 GHz environment), Nooelec
  `rf_warmth`. Live baseline at home: density 33–35, aps 4–8, busy 2–46, warmth 0.49–0.50.
- **Software:** aggregator + OSC + Max/Ableton; `purity`/`interference` lane already exists;
  `wifi_aps`/`wifi_busy`/`rf_warmth` live; 65 tests. The Max patch routes/displays the
  seven core addresses but does **not yet route `/purity` or `/interference`**.
- **Data:** aggregate/local only; hashed IDs downstream; no content; no identification; no
  cloud; no retention of raw identifiers. AP BSSIDs stay in the ALFA capture process.
- **Build scope:** a 10-minute prototype, not the final installation. The first visual can
  be a simple visibility meter; the full constellation/visualizer comes later.
- **Human:** the author can operate the Mac/Ableton and the Pi; the gallery may not have a
  technical operator. A runbook and fallback are required.

## 4. Approaches considered

### A. The Purity Room — corrosion-first

A clean ambient bed is the baseline; every device adds static/bitcrush/narrowband noise and
lowers `purity`; deactivating restores the bed. Visual: a clean room filling with signal
noise; a visibility meter.

- Pros: legible, strong deactivation incentive, quick to build, uses the existing `purity`
  lane.
- Cons: mostly punitive; the “augment” is weak; can read as a one-liner; people may turn off
  phones and leave; the piece may not sustain 10 minutes.

### B. The Choir — augment-first, with a shadow (chosen)

A warm drone/choir is the room. BLE devices add voices (density = voice count, churn = new
articulations, proximity = brightness). WiFi/RF signals add a parallel surveillance shadow
that detunes/corrodes the choir (`purity`/`interference` = corrosion, `wifi_aps`/`wifi_busy`
= shadow density, `rf_warmth` = RF bed/pitch drift). The choir gets richer with devices, but
the shadow makes it uncanny; deactivating thins the shadow and leaves a more intimate, clear
choir. Visual: a constellation/radar of aggregate signals and a visibility meter.

- Pros: uses both augment and corrode; compelling; fits the current feed; the audience feels
  agency; the deactivation reward is clarity, not silence.
- Cons: the incentive is ambiguous if the choir is too beautiful; the beauty/unease balance
  is the art; needs sound design and audience testing.

### C. The Mirror — narrative-first (later)

A live/field-recorded room sound is the “real” layer; the devices' signals become a parallel
broadcast choir, slightly delayed/detuned, that bleeds into the live layer as density rises.
Deactivating removes the ghost; the live room becomes present. Visual: a mirror/radar of the
broadcast cloud.

- Pros: the most explicit surveillance metaphor; strong gallery narrative; uses augment
  (ghost choir) and corrode (bleed).
- Cons: more production; needs a compelling live source and visual; can become didactic.

**Chosen:** The Choir for the first prototype. It uses both halves of the brief, fits the
current instrument, and can be tested before the Mirror's live-source/visual production. The
Purity Room is the control/fallback; the Mirror is the later gallery-scale evolution.

## 5. The Choir — experience and design

### 5.1 The 10-minute audience journey

1. **Enter — the clean room.** A warm, slowly breathing choir/drone. The room sounds
   beautiful and slightly empty. Signage explains the piece in one paragraph: the room is
   listening to anonymous device broadcasts; nothing is recorded or identified; devices can
   be turned off to hear the room change.
2. **Devices appear.** As the audience enters with phones/watches, voices join the choir.
   The room becomes richer; the constellation on the visual gains points. The `purity`
   meter starts high and begins to fall.
3. **The shadow arrives.** WiFi/RF signals add a parallel, detuned/noisy layer. The choir
   becomes crowded and slightly uncanny; the `purity`/`interference` drives the corrosion.
   The visual shows the signal cloud and a “visibility” meter; no identities.
4. **The experiment.** The audience notices that turning a device off thins the shadow and
   clarifies the choir. The `purity` recovers slowly; the clean state returns gradually, not
   instantly. The piece invites experimentation without instructions beyond the signage.
5. **The loop.** The piece returns to the clean room; the cycle can repeat. A 10-minute loop
   is the prototype; a gallery version can run longer with a slower arc.

**Prototype arc:** the 10-minute version is a composed state machine/sequencer (clean →
arrival → shadow → experiment → return) that sensor data modulates; the long-run gallery
version can be a reactive always-on mode once the arc is proven. Live sensing does not
produce a narrative by itself.

### 5.2 Signal → sound mapping (v1)

| Signal | Sound / visual role | Notes |
|---|---|---|
| `density` | Choir voice count (normalized, capped) | 33–35 at home; map via a moving average/percentile, cap at 8–12 voices; do not map 1:1. |
| `churn` | New voice articulations / onsets | New arrivals; rate-limited; not every BLE repeat. |
| `proximity` | Brightness / filter / register | Closest device; smooth; avoid jitter. |
| `band_balance` | BLE vs WiFi color | BLE-dominant = choir; WiFi-dominant = shadow; use as a slow color, not the only shadow control. |
| `purity` / `interference` | Master corrosion/clarity | The core mechanic; **fast attack (degrade quickly) / slow release (recover slowly)** — the code is the source of truth; route `/purity` and `/interference` into the Max patch. Baseline-relative (see §5.2b). |
| `wifi_aps` | Infrastructure/harmonic density | AP count; slow; adds shadow/harmonic weight. |
| `wifi_busy` | Shadow texture / delay / filter movement | Non-beacon frames/sec; dynamic; the “surveillance weather.” |
| `rf_warmth` | RF bed / pitch drift | 0..1; slow; the wideband RF weather. |
| `by_class` | Optional later | Current BLE class is unknown; a light name/company classifier could give phones/watches/earbuds different voices. Not required for v1. |
| `surveillance_*` | Not used | Police-proxy research stays out of the installation. |

### 5.2b Baseline, shadow gating, and legibility

- **Clean = baseline, not zero.** The room will already contain ambient BLE/WiFi from the
  building and neighbours (home baseline density 33–35; `PurityCalculator` currently
  saturates at 10 devices, giving purity ≈0.31 at rest). The prototype must capture a
  baseline at install/session start and map the audience's **delta** against it; otherwise
  the "clean" state is unreachable. The `PurityCalculator` needs a baseline/normalization
  step (implementation plan).
- **The environment sets character, not the amount.** `rf_warmth` (FM band), `wifi_aps`,
  and `wifi_busy` are audience-independent "weather." The shadow's **level** must be gated
  by the presence-derived `interference`/purity so deactivation audibly clears the room;
  the environment layers shape its timbre/texture.
- **Room-level, not per-person.** Density counts hashed endpoints, not people (one phone
  can be two ids; BLE randomizes). One person off in a group of 5 changes density by ~1/35.
  The prototype should use a small group (3–5), an RSSI/placement gate so the room's own
  devices dominate, and a room-level visual. Per-visitor feedback is not promised; the
  piece is an aggregate mirror.

### 5.3 Sound design

- **Base:** a warm, slowly evolving choir/drone (the room's own voice), in a fixed
  scale/key; long reverb; a clear, beautiful “clean” state that the audience wants to
  return to.
- **Voices:** a polyphonic synth/choir; each normalized density step adds a voice; a voice
  cap; panning; the proximity controls brightness/register; the churn triggers articulations;
  the timbre should feel human-ish but not literally vocal (avoid uncanny identity claims).
- **Shadow:** a parallel layer of detuned/narrowband noise, bitcrush, delay, and filtered
  feedback; driven by `purity`/`interference`, `wifi_aps`, `wifi_busy`, `rf_warmth`; it
  should be uncomfortable but musical, never just harsh noise.
- **Master:** the `purity`/`interference` is the master clarity/corrosion; the clean state
  is the reward; the deactivation recovery is slow enough to feel earned.
- **Smoothing/calibration:** moving averages, percentile normalization, voice caps, and a
  venue calibration step; the raw 33–35 density is not directly a voice count.
- **System:** stereo or quad; the gallery's speaker layout; Mac/Ableton/Max; a class-compliant
  audio interface; the `live.remote`/`live.numbox` mapping; the Max patch extended with
  `/purity` and `/interference`.

### 5.4 Visual

- **v1:** a simple visibility meter / constellation of aggregate signals; the `purity`
  bar; the `wifi_aps`/`wifi_busy`/`rf_warmth` as environmental bands; the words “signals,”
  not “people.”
- **Later:** the full constellation/radar (web visualizer or Max/Jitter); no individual
  identities; aggregate counts only; the aesthetic should feel like an instrument, not a
  security dashboard.
- **Signage:** a short, plain statement of what is sensed, what is not, and the invitation
  to experiment. The piece must be transparent; the irony of an artwork that senses devices
  is part of the work, not a secret.

### 5.5 Audience and ethics

- Aggregate/local only; raw MACs stay at the sensor boundary; hashed IDs downstream; no
  content; no cameras; no cloud; no retention of raw identifiers.
- The visual shows aggregates; the AP BSSIDs never leave the ALFA capture process.
- The police-proxy/`surveillance_*` research is not used; the piece is about everyday device
  visibility, not police detection.
- Signage/consent: the audience should know the room is listening before they participate;
  the piece should not secretly record or identify.
- The intervention is a mirror, not a scold: the clean state should be inviting, the shadow
  should be thought-provoking, and deactivation should feel like agency, not punishment.
- **Room-scale presence, building-scale weather.** The presence/voices are gated to the
  room (RSSI floor, antenna placement, excluding static infrastructure); the building's
  APs/RF are the background "weather" layer, not audience presence. This keeps the
  audience's actions dominant and makes the consent story about the room, not passers-by.

### 5.6 Technical architecture

- **Sensors:** Pi 5 + XIAO WiFi (2.4 GHz probe), XIAO BLE (adverts, antenna), ALFA 5 GHz
  environment (`wifi_env`, root), Nooelec RF (`rtl_power`, `rf_warmth`); hub + PSUs.
- **Aggregator:** `presence.aggregator` with `--serial-wifi`/`--serial-ble` by-id,
  `--wifi-env-port 9998`, `--rf-warmth`; OSC to the Mac; `--print` for logs.
- **Audio:** Mac/Ableton/Max; the Max patch routes `/density`, `/churn`, `/proximity`,
  `/band_balance`, `/rf_warmth`, `/wifi_aps`, `/wifi_busy`; **add `/purity` and
  `/interference`**; map to the Choir instrument. **Confirm Ableton Live Suite + Max for
  Live (or a Max 8 licence)**; if unavailable, the instrument/visual must be a Max
  standalone or Pd, which changes the auto-start/runbook.
- **Visual:** a simple meter first; the full visualizer later; the same OSC feed.
- **Reliability:** systemd target for the feed and the root `wifi_env`; ALFA monitor
  service/udev recovery; Nooelec/`rtl_power` watchdog; static IP/DHCP reservation for the
  Mac; macOS firewall; a fallback simulator/baseline so the room never goes silent; a
  runbook and a start/stop script.
- **Enclosure/placement:** antenna separation (ALFA/SDR ≥10 cm; BLE/WiFi antennas away
  from metal); the Pi/hub; the Mac; the audio interface; the speakers; the visual; the
  signage. The final enclosure is later.

### 5.7 Evaluation (first prototype)

- Test with 3–5 people in a gallery-like room for 10 minutes.
- Observe: Do they notice the shadow? Do they experiment with deactivation? Does the clean
  state feel like a reward? Do they understand what is sensed and what is not? Is the sound
  compelling for 10 minutes? Does the visual help or distract? Does the rig survive the
  session?
- Capture a **line-out/board recording of the piece's own audio** (not a room microphone;
  no visitor speech), the questionnaire/interview (consented), the `purity`/density logs,
  and the technical incidents. Iterate the mapping and the signage before the full
  visual/reliability build.

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Punitive/didactic | Choir's augment side; deactivation reward = clarity/intimacy; audience test; signage tone. |
| Ambiguous incentive | Balance the shadow; make the visibility meter legible; test whether people experiment. |
| The piece itself surveils | Aggregate/local; hashed IDs; no content/cameras/cloud; signage; no police-proxy lane. |
| Proxy mistaken for census | Label “signals,” not people; explain WiFi/BLE limits; no 1:1 claims. |
| Unreliable install | systemd/auto-start; ALFA/Nooelec watchdogs; fallback = composed "honest" bed + status cue (no simulator on the gallery floor; simulator test-only); runbook; test. |
| Club context | This design is for a gallery/installation; a club version is a different piece. |
| Sound design too pleasant/too harsh | Audience test; the `purity` fast attack/slow release; the shadow musical, not noise. |
| Class mapping absent | Aggregate voices for v1; optional BLE name/company classifier later. |
| Visual scope creep | Simple meter first; full constellation later. |

## 7. What is left to the builder

- The exact sound palette, scale, voice cap, and shadow timbre.
- The exact mapping curves/smoothing for `density`, `churn`, `proximity`, `band_balance`,
  `purity`, `wifi_aps`, `wifi_busy`, `rf_warmth`.
- The Max/Ableton instrument and the `/purity`/`/interference` routes.
- The v1 visual meter/constellation implementation and the signage copy.
- The systemd/auto-start/watchdog/fallback implementation and the runbook.
- The gallery calibration procedure and the 3–5 person test protocol.
- The optional BLE class classifier and the later Mirror/visualizer.
- Minor calls already settled: sensor failure = honest composed bed + status cue (no
  floor simulator); evaluation recording = line-out only; purity envelope = fast attack /
  slow release (the code is the source of truth).

## 8. Builder-check decisions (need the human)

The design reviewer found six decisions that change the build. My recommendation is in
brackets.

1. **Clean room = baseline or literal zero?** [Baseline/delta: capture the room at session
   start; the audience's additions are the signal; the `PurityCalculator` gets a baseline.]
2. **Do the environment layers recede when devices are off?** [No — they set the shadow's
   character; the presence-derived `interference`/purity gates the shadow's level so
   deactivation clears the room.]
3. **Per-visitor legibility or room-level?** [Room-level aggregate + small-group/RSSI-gated
   test; no per-person promise.]
4. **10-minute loop = composed arc or reactive?** [Composed state machine for the
   prototype; reactive always-on for the gallery later.]
5. **Sensing boundary: this room or the building?** [Room-scale presence; building APs/RF
   as background weather; venue consent/signage.]
6. **Ableton Suite + Max for Live available?** [Confirm; else Max standalone/Pd.]

### Design choices still open

- Venue/room, speaker layout, and audience flow.
- Sound world: ambient/meditative, choral/uncanny, or rhythmic.
- Signage tone: poetic vs direct.
- Visual v1: simple meter vs constellation/radar.
- Timeline and budget for the prototype vs the full installation.
- Choir only, or Choir plus the Purity Room as a side-by-side control.
