# presence-sniffer

Portable device-presence sniffer → audio/visual instrument. See [PLAN.md](PLAN.md).

Passively senses nearby Wi-Fi / BLE / RF activity and maps it to Ableton Live
(via OSC) and a visualizer. **Crowd/presence-density instrument only** — it does not
and cannot identify specific people or device owners.

## Quick start (Mac dev, Phase 0)

```bash
./scripts/run.sh                  # creates .venv, installs deps
source .venv/bin/activate
python -m presence.aggregator --simulator          # runs sim + OSC bridge (Ctrl-C to stop)
python -m presence.aggregator --simulator --print  # also prints events to console
```

OSC output goes to `127.0.0.1:9090`. Open `maxforlive/presence_osc.maxpat` in Max
(or drop the `.amxd` equivalent into Live) to receive it.

## Layout

```
src/presence/          core package
  events.py            event dataclasses (PresenceEvent, DensityStats)
  bus.py               asyncio pub/sub event bus
  simulator.py         fake sensor for hardware-free dev
  aggregator.py        daemon: sensor -> bus -> subscribers (OSC, viz)
  osc_bridge.py        bus -> OSC UDP sender
  sensors/             real radio adapters (ESP32 serial, Scapy Wi-Fi, BLE)
  viz/                 web visualizer (Phase 4)
maxforlive/            Max for Live patch: OSC receiver + mapping macros
scripts/run.sh         env bootstrap
tests/                 unit tests
```

## Ethics

Passive sensing of broadcast signals only. Never intercept, decrypt, or deanonymize
traffic. Do not use to profile or track individuals.
