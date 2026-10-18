# RTL-SDR Blog V3 (R860) — DOA return report

**Product:** RTL-SDR Blog V3 R860 dongle, bought as Amazon `B0BMKZCKTF`
(listed via the official RTL-SDR Blog storefront).
**Ordered/received:** ordered 2026-09-19 (see HARDWARE.md row 4).
**Verdict:** DOA on arrival — the tuner/RF section produces no signal.
Reproducible on two independent hosts. Replacement requested (same model).

## Symptom summary (for the seller)

The dongle enumerates fine over USB (`0bda:2838`, RTL2838UHIDIR) and its
driver loads, but it never produces usable RF data:

1. `rtl_test` reports `Found Rafael Micro R820T tuner` and then
   `[R82XX] PLL not locked!` — the tuner PLL never locks.
2. Captured IQ at any frequency is pinned to a constant DC rail
   (byte values 123–132 of 0–255, std ≈ 0.8–1.2 out of 127). A working
   dongle at the same settings shows std ≈ 10–30.
3. Gain sweep makes it worse, monotonic: std 3.7 (0 dB) → 0.5 (7.7 dB) →
   1.2 (49.6 dB). Raising RF gain drives the output harder onto the rail.
4. No FM broadcast station at 98.0 MHz appears in the spectrum at any gain
   (flat to ~0.3 dB across ±800 kHz); same at 433.92 MHz.
5. Cross-checked on a Mac with a different librtlsdr version — identical
   results. Zero USB errors on either host.

## What was ruled out

- Host/OS issue — reproduces on Raspberry Pi OS (librtlsdr 2.0.2) and macOS
  (Homebrew librtlsdr 2.0.3).
- USB link/power — no kernel USB errors, no disconnects, no over-current, on
  a powered USB hub with its own 5 V/4 A supply (same hub that drives an
  unrelated Wi-Fi adapter fine).
- Driver conflicts — the DVB-T kernel driver (`dvb_usb_rtl28xxu`) is
  blacklisted; the dongle is claimed directly by librtlsdr.
- Usage error — tested across the full gain range (0–49.6 dB) and multiple
  frequencies (88–434 MHz) with the supplied antenna.

## Secondary observation

The EEPROM is fully default/blank (`Manufacturer: Realtek`,
`Product: RTL2838UHIDIR`, `Serial number: 00000001`). Genuine RTL-SDR Blog V3
units normally ship with RTL-SDR Blog-specific EEPROM strings. Combined with
the dead RF section this raises a counterfeit concern; either way the unit is
unusable and needs replacement.

## Request

Replacement with a new RTL-SDR Blog V3 (R860) unit — or refund.

## Verification checklist for the replacement unit

1. `rtl_test` — expect the tuner to be found and stay locked (no persistent
   `PLL not locked!` spam during sampling).
2. `rtl_sdr -f 98.0M -s 2048000 -g 42 -n 4194304 /tmp/iq.bin` — file stops
   growing at ~4 MB and IQ byte spread is wide (std ≫ 4), not a rail.
3. `rtl_power -f 88M:108M:200k -i 1 -e 10 -g 42 /tmp/fm.csv` — local FM
   stations rise 20–40 dB above the noise floor.
4. Demodulate an identified station: `rtl_fm -f 98.0M -M fm -s 22050 -g 42 -`
   — audible audio, not silence/static.

(Full bench context and re-test recipe: BENCH.md Stage 2 item 2.)
