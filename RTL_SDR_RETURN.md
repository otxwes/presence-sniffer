# RTL-SDR Blog V3 (R860) — DOA return report

**Product:** RTL-SDR Blog V3 R860 dongle, bought as Amazon `B0BMKZCKTF`
(listed via the official RTL-SDR Blog storefront).
**Ordered/received:** ordered 2026-09-19 (see HARDWARE.md row 4).
**Verdict:** DOA on arrival — the tuner/RF section produces no signal.
Reproducible across three driver/host setups, including the official RTL-SDR
Blog driver. Replacement requested (same model).

## Symptom summary (for the seller)

The dongle enumerates fine over USB (`0bda:2838`, RTL2838UHIDIR) and its
driver loads, but it never produces usable RF data:

1. `rtl_test` reports `Found Rafael Micro R820T tuner` and then
   `[R82XX] PLL not locked!` — the tuner PLL never locks, which means no
   local oscillator, no downconversion, and a constant rail at the ADC.
2. Captured IQ at any frequency is pinned to a constant DC rail
   (byte values 123–132 of 0–255, std ≈ 0.8–1.2 out of 127). A working
   dongle at the same settings shows std ≈ 10–30.
3. Gain behavior is inverted and monotonic: manual gain values 7.7 → 49.6 dB
   give std 0.53 → 1.16 (more gain, *more* pinning to the rail); automatic
   gain (AGC) gives std ≈ 3.7–5.5, still with no signal structure. Even the
   AGC figure is far below the noise variance a healthy receiver produces.
4. No FM broadcast station at 98.0 MHz appears in the spectrum at any gain
   setting (flat across ±800 kHz); same at 433.92 MHz.
5. Cross-checked on a Mac (different librtlsdr version, different USB stack)
   and with the official RTL-SDR Blog driver fork built from
   `rtlsdrblog/rtl-sdr-blog` — identical results in all three setups.
   Zero USB errors on either host.

## What was ruled out

- Host/OS issue — reproduces on Raspberry Pi OS (stock librtlsdr 2.0.2),
  macOS (Homebrew stock librtlsdr 2.0.3), and macOS with the official
  RTL-SDR Blog driver fork.
- USB link/power — no kernel USB errors, no disconnects, no over-current, on
  a powered USB hub with its own 5 V/4 A supply (same hub that drives an
  unrelated Wi-Fi adapter fine).
- Driver conflicts — the DVB-T kernel driver (`dvb_usb_rtl28xxu`) is
  blacklisted; the dongle is claimed directly by librtlsdr.
- Usage error — tested across the full gain range and multiple frequencies
  (88–434 MHz) with the supplied antenna. HF direct-sampling mode is not
  relevant: it only applies below 28.8 MHz and none of the tests or the
  intended use (VHF/UHF/ISM) are in that range. Bias tee is not used
  (passive antenna) and remains off.

## Secondary observation

The EEPROM is fully default/blank (`Manufacturer: Realtek`,
`Product: RTL2838UHIDIR`, `Serial number: 00000001`). Genuine RTL-SDR Blog V3
units normally ship with RTL-SDR Blog-specific EEPROM strings. Combined with
the dead RF section this matches the counterfeit warning in the official V3
user guide ("features may not work correctly, if at all — lodge a dispute
with the marketplace"), so we are raising both the DOA failure and the
identity question.

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
