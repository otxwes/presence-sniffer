# Max for Live integration

- `presence_osc.maxpat` — starter patch: listens for OSC on UDP 9090 and routes
  the five addresses (`/density /churn /proximity /band_balance /rf_warmth`).

## Wiring into Ableton

1. Drop `presence_osc.maxpat` into a Max for Live MIDI/audio effect slot (or open
   it in Max 8 and save as `.amxd`).
2. Max 8 includes the `OSC-route` object (from the CNMAT / JazzMutant extras —
   add via the Max Package Manager if missing); otherwise use `udpreceive` +
   `route` on the raw OSC form.
3. Map the signals like this (Phase 3 plan):
   - `/proximity`  → volume or filter cutoff sweep
   - `/churn`      → bitcrush depth / transient artifacts
   - `/density`    → delay feedback, granular glitch rate
   - `/rf_warmth`  → pitch drift
4. Use `live.object` / `live.remote` for parameter automation without baking to clips.

The python daemon must be running: `python -m presence.aggregator --simulator`.
