"""Bench IQ / rtl_power analyzer for RTL-SDR validation.

Usage:
    python3 scripts/analyze_iq.py capture.bin   # 8-bit IQ pairs from rtl_sdr
    python3 scripts/analyze_iq.py scan.csv      # rtl_power CSV

Healthy RTL-SDR (98.0 MHz, 42 dB, 2.048 MS/s): I std ~10-30, in-band
spectrum peak-median >6 dB with station structure, FM scan 20-40 dB above
floor. Dead tuner (PLL never locks): I std <2 and a flat spectrum.

Requires numpy. The spectrum path assumes 2.048 MS/s (bin offsets in kHz).
"""

import sys

import numpy as np


def analyze_iq(path):
    raw = np.fromfile(path, dtype=np.uint8)
    raw = raw[: (len(raw) // 2) * 2]
    iq = raw.reshape(-1, 2).astype(np.float64)
    ib = iq[:, 0]
    qb = iq[:, 1]
    i = ib - 127.5
    q = qb - 127.5
    z = (i + 1j * q)[: 8_000_000]

    print(f"IQ file: {path}")
    print(f"bytes: {len(raw)}  complex samples: {len(iq)} (analyzed: {len(z)})")
    print(
        f"I: mean={ib.mean():.2f}  std={i.std():.3f}  "
        f"byte span={int(ib.min())}..{int(ib.max())}"
    )
    print(
        f"Q: mean={qb.mean():.2f}  std={q.std():.3f}  "
        f"byte span={int(qb.min())}..{int(qb.max())}"
    )

    n = 1 << 14
    z = z - z.mean()
    seg = z[: (len(z) // n) * n].reshape(-1, n)
    win = np.hanning(n)
    spec = np.fft.fftshift(np.fft.fft(seg * win, axis=1), axes=1)
    psd = 20 * np.log10(np.abs(spec) + 1e-12)
    avg = psd.mean(axis=0)
    mid = n // 2
    mask = np.ones(n, dtype=bool)
    mask[mid - 3 : mid + 4] = False  # exclude DC +/- 3 bins
    med = np.median(avg[mask])
    peak = avg[mask].max()
    peak_bin = int(np.argmax(np.where(mask, avg, -np.inf)))
    bin_hz = 2_048_000 / n
    offset_khz = (peak_bin - mid) * bin_hz / 1000
    print(
        f"spectrum: median={med:.1f} dB  peak={peak:.1f} dB  "
        f"peak-median={peak - med:.1f} dB  spread(std)={avg[mask].std():.2f} dB"
    )
    print(
        f"peak offset from center: {offset_khz:+.1f} kHz "
        f"(DC bin level={avg[mid]:.1f} dB)"
    )
    half_width_bins = int(800_000 / bin_hz)  # +/-800 kHz usable band
    band_mask = np.zeros(n, dtype=bool)
    band_mask[mid - half_width_bins : mid + half_width_bins + 1] = True
    band_mask[mid - 3 : mid + 4] = False
    band = avg[band_mask]
    med_b = np.median(band)
    peak_b = band.max()
    width_bins = int(np.sum(band > peak_b - 3))
    print(
        f"in-band (+/-800 kHz): median={med_b:.1f} dB  peak={peak_b:.1f} dB  "
        f"peak-median={peak_b - med_b:.1f} dB  "
        f"width(3dB)={width_bins} bins ({width_bins * bin_hz / 1000:.1f} kHz)"
    )
    verdict = (
        "FLAT (no station structure)"
        if (peak_b - med_b < 6 or width_bins < 10)
        else "STRUCTURE PRESENT"
    )
    print(f"verdict: {verdict}")


def analyze_power(path):
    rows = []
    with open(path) as fh:
        for line in fh:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 7:
                continue
            vals = [float(x) for x in parts[6:] if x != ""]
            if vals:
                rows.append(vals)
    a = np.array(rows)
    med = np.median(a)
    peak = a.max()
    per_row = [float(np.max(r) - np.median(r)) for r in a]
    print(f"rtl_power file: {path}")
    print(f"rows: {a.shape[0]}  bins/row: {a.shape[1]}  total bins: {a.size}")
    print(
        f"floor(median)={med:.1f} dB  max={peak:.1f} dB  "
        f"peak-median={peak - med:.1f} dB"
    )
    print(f"per-row peak-median: min={min(per_row):.1f}  max={max(per_row):.1f} dB")
    verdict = "FLAT (no stations >6 dB)" if peak - med < 6 else "PEAKS PRESENT"
    print(f"verdict: {verdict}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    if sys.argv[1].endswith(".csv"):
        analyze_power(sys.argv[1])
    else:
        analyze_iq(sys.argv[1])
