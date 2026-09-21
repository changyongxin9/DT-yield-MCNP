#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
mcnp_roi.py
MCNP F8 6.13 MeV oxygen-peak ROI analysis.

Method:
1) Parse F8:P spectrum and per-bin relative error R from MCNP output.
2) Parse FT8 GEB a,b,c and calculate theoretical FWHM at target energy:
       FWHM(E) = a + b*sqrt(E + c*E^2)
3) Fit local peak using Gaussian + linear background with lmfit.
4) Scan symmetric ROI = mu ± k*sigma_fit.
5) For each candidate ROI report:
       fitted Gaussian capture fraction
       gross F8 response
       fitted-background response
       net peak response
       approximate MC statistical uncertainty
       net/sigma figure
6) Recommended ROI:
       among candidates containing >=99% of the fitted Gaussian peak,
       choose the one with the smallest approximate relative statistical uncertainty.
   Also report the purely SNR-optimal ROI for comparison.

Important:
- F8 values are per source history, not absolute experimental counts.
- Summing F8 energy bins gives ROI response per source history.
- ROI uncertainty is an approximation using quadrature of bin uncertainties;
  MCNP bin-to-bin covariance is not available in the standard output.
"""

import argparse
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

try:
    from lmfit.models import GaussianModel, LinearModel
except ImportError as exc:
    raise SystemExit("lmfit 未安装。请运行: pip install lmfit") from exc


FLOAT = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?"


def read_text(path):
    for enc in ("utf-8", "gb18030", "latin-1"):
        try:
            return Path(path).read_text(encoding=enc, errors="strict")
        except UnicodeDecodeError:
            pass
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def parse_geb(text):
    # Accept "FT8 GEB a b c" or equivalent spacing/case.
    m = re.search(
        rf"(?im)^\s*FT8\s+GEB\s+({FLOAT})\s+({FLOAT})\s+({FLOAT})\s*$",
        text,
    )
    if not m:
        return None
    return tuple(float(v) for v in m.groups())


def parse_nps(text):
    m = re.search(r"(?im)^\s*NPS\s+(\d+)\s*$", text)
    if m:
        return int(m.group(1))
    m = re.search(r"(?i)\bnps\s*=\s*(\d+)", text)
    return int(m.group(1)) if m else None


def parse_f8(text, tally_number=8):
    lines = text.splitlines()
    start = None
    pat = re.compile(rf"^\s*1tally\s+{tally_number}\b", re.I)
    for i, line in enumerate(lines):
        if pat.search(line):
            start = i
            break
    if start is None:
        raise ValueError(f"没有找到 tally {tally_number}。")

    data = []
    in_energy = False
    row_re = re.compile(
        rf"^\s*({FLOAT})\s+({FLOAT})\s+({FLOAT})\s*$"
    )

    for line in lines[start + 1:]:
        if re.match(r"^\s*total\s+", line, re.I):
            if data:
                break
        if "energy" in line.lower():
            in_energy = True
            continue
        if not in_energy:
            continue

        m = row_re.match(line)
        if m:
            e, y, r = map(float, m.groups())
            data.append((e, y, r))
        elif data and line.strip() and re.match(r"^\s*1(?:analysis|tally|status)", line, re.I):
            break

    if not data:
        raise ValueError("找到了 F8 tally，但没有解析到能谱数据。")

    df = pd.DataFrame(data, columns=["energy_MeV", "f8_per_history", "rel_error_R"])
    return df


def geb_fwhm(E, a, b, c):
    inside = E + c * E * E
    if inside < 0:
        return np.nan
    return a + b * math.sqrt(inside)


def fit_peak(df, target, fwhm_theory=None, fit_halfwidth=None):
    if fit_halfwidth is None:
        # Physically anchored local fit window: ±3 theoretical FWHM.
        # If GEB is unavailable, use ±0.25 MeV as fallback only.
        fit_halfwidth = 3.0 * fwhm_theory if fwhm_theory and fwhm_theory > 0 else 0.25

    fit_min = target - fit_halfwidth
    fit_max = target + fit_halfwidth
    d = df[(df.energy_MeV >= fit_min) & (df.energy_MeV <= fit_max)].copy()

    if len(d) < 12:
        raise ValueError("拟合窗口中的能道太少。")

    x = d.energy_MeV.to_numpy()
    y = d.f8_per_history.to_numpy()
    r = d.rel_error_R.to_numpy()
    sy = y * r

    # Prevent zero/invalid weights.
    positive = sy[np.isfinite(sy) & (sy > 0)]
    fallback = np.median(positive) if len(positive) else 1.0
    sy = np.where(np.isfinite(sy) & (sy > 0), sy, fallback)
    weights = 1.0 / sy

    # Initial background from outer 20% of the local fit window.
    nedge = max(3, int(0.2 * len(d)))
    idx_bg = np.r_[0:nedge, len(d)-nedge:len(d)]
    p = np.polyfit(x[idx_bg], y[idx_bg], 1)
    bg0 = np.polyval(p, x)
    y_peak = np.maximum(y - bg0, 0)

    dx = float(np.median(np.diff(x)))
    peak_idx = int(np.argmax(y_peak))
    center0 = float(x[peak_idx])

    if fwhm_theory and fwhm_theory > 0:
        sigma0 = fwhm_theory / 2.354820045
    else:
        sigma0 = 0.035

    # GaussianModel amplitude is integral of the continuous Gaussian.
    amp0 = max(float(np.sum(y_peak) * dx), 1e-20)

    gmod = GaussianModel(prefix="g_")
    bmod = LinearModel(prefix="b_")
    model = gmod + bmod

    params = gmod.make_params(
        amplitude=amp0,
        center=center0,
        sigma=sigma0,
    )
    params.update(bmod.make_params(slope=p[0], intercept=p[1]))

    # Keep fit physically local and positive.
    params["g_amplitude"].min = 0
    params["g_center"].min = target - 0.08
    params["g_center"].max = target + 0.08
    params["g_sigma"].min = 0.005
    params["g_sigma"].max = 0.15

    result = model.fit(y, params, x=x, weights=weights)

    mu = result.params["g_center"].value
    sigma = abs(result.params["g_sigma"].value)
    fwhm = 2.354820045 * sigma

    # Evaluate fitted background at all spectrum bin centers.
    slope = result.params["b_slope"].value
    intercept = result.params["b_intercept"].value
    df = df.copy()
    df["fitted_background"] = slope * df.energy_MeV + intercept

    return result, df, (fit_min, fit_max), mu, sigma, fwhm


def scan_roi(df, mu, sigma, k_values):
    rows = []
    for k in k_values:
        lo = mu - k * sigma
        hi = mu + k * sigma
        m = (df.energy_MeV >= lo) & (df.energy_MeV <= hi)
        sub = df.loc[m].copy()
        if sub.empty:
            continue

        gross = float(sub.f8_per_history.sum())
        bg = float(sub.fitted_background.sum())
        net = gross - bg

        # Approximate MC uncertainty from per-bin R, treating bins as independent.
        # This is explicitly labelled approximate because MCNP bin covariance
        # is not provided by standard tally output.
        bin_sigma = sub.f8_per_history.to_numpy() * sub.rel_error_R.to_numpy()
        gross_sigma_approx = float(np.sqrt(np.sum(bin_sigma**2)))
        rel_unc_approx = gross_sigma_approx / net if net > 0 else np.nan
        snr_like = net / gross_sigma_approx if gross_sigma_approx > 0 else np.nan

        capture = math.erf(k / math.sqrt(2.0))

        rows.append({
            "k_sigma": k,
            "roi_low_MeV": float(sub.energy_MeV.min()),
            "roi_high_MeV": float(sub.energy_MeV.max()),
            "n_bins": int(len(sub)),
            "gaussian_capture_fraction": capture,
            "gross_F8_per_history": gross,
            "fitted_background_F8": bg,
            "net_peak_F8_per_history": net,
            "approx_sigma_F8": gross_sigma_approx,
            "approx_rel_uncertainty": rel_unc_approx,
            "snr_like": snr_like,
        })

    return pd.DataFrame(rows)


def choose_rois(scan):
    good = scan[
        (scan.gaussian_capture_fraction >= 0.99)
        & np.isfinite(scan.approx_rel_uncertainty)
        & (scan.net_peak_F8_per_history > 0)
    ]

    recommended = None
    if not good.empty:
        recommended = good.sort_values(
            ["approx_rel_uncertainty", "k_sigma"],
            ascending=[True, True]
        ).iloc[0]

    snr_valid = scan[np.isfinite(scan.snr_like) & (scan.net_peak_F8_per_history > 0)]
    snr_best = None if snr_valid.empty else snr_valid.sort_values("snr_like", ascending=False).iloc[0]
    return recommended, snr_best


def save_plot(df, result, fit_range, mu, sigma, rec, target, output_png):
    lo, hi = fit_range
    d = df[(df.energy_MeV >= lo) & (df.energy_MeV <= hi)].copy()
    x = d.energy_MeV.to_numpy()
    yfit = result.eval(x=x)
    bg = result.params["b_slope"].value * x + result.params["b_intercept"].value

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(d.energy_MeV, d.f8_per_history, marker="o", markersize=3, linewidth=1, label="MCNP F8")
    ax.plot(x, yfit, linewidth=1.5, label="Gaussian + linear background")
    ax.plot(x, bg, linestyle="--", linewidth=1, label="Fitted background")
    ax.axvline(target, linestyle=":", linewidth=1, label=f"Target {target:.3f} MeV")
    ax.axvline(mu, linestyle="-.", linewidth=1, label=f"Fit center {mu:.4f} MeV")

    if rec is not None:
        ax.axvspan(rec["roi_low_MeV"], rec["roi_high_MeV"], alpha=0.15, label="Recommended ROI")

    ax.set_xlabel("Energy (MeV)")
    ax.set_ylabel("F8 response per source history")
    ax.set_title("MCNP 6.13 MeV oxygen peak ROI analysis")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_png, dpi=300)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description="MCNP F8 6.13 MeV oxygen peak ROI analysis")
    ap.add_argument("outp", help="MCNP output file")
    ap.add_argument("--target", type=float, default=6.13, help="target peak energy in MeV")
    ap.add_argument("--tally", type=int, default=8, help="F8 tally number, default 8")
    ap.add_argument("--fit-halfwidth", type=float, default=None,
                    help="override local fit half-width in MeV")
    ap.add_argument("--k-min", type=float, default=1.5)
    ap.add_argument("--k-max", type=float, default=3.5)
    ap.add_argument("--k-step", type=float, default=0.1)
    args = ap.parse_args()

    path = Path(args.outp)
    text = read_text(path)
    df = parse_f8(text, args.tally)
    geb = parse_geb(text)
    nps = parse_nps(text)

    if geb:
        a, b, c = geb
        fwhm_th = geb_fwhm(args.target, a, b, c)
    else:
        a = b = c = np.nan
        fwhm_th = None

    result, df2, fit_range, mu, sigma, fwhm_fit = fit_peak(
        df,
        target=args.target,
        fwhm_theory=fwhm_th,
        fit_halfwidth=args.fit_halfwidth,
    )

    k_values = np.round(
        np.arange(args.k_min, args.k_max + args.k_step / 2, args.k_step),
        10
    )
    scan = scan_roi(df2, mu, sigma, k_values)
    rec, snr_best = choose_rois(scan)

    stem = path.stem
    out_csv = path.with_name(stem + "_roi_scan.csv")
    out_png = path.with_name(stem + "_roi_fit.png")
    out_txt = path.with_name(stem + "_roi_summary.txt")
    scan.to_csv(out_csv, index=False, encoding="utf-8-sig")

    save_plot(df2, result, fit_range, mu, sigma, rec, args.target, out_png)

    lines = []
    lines.append("MCNP 6.13 MeV ROI ANALYSIS")
    lines.append("=" * 60)
    lines.append(f"Input file          : {path}")
    lines.append(f"NPS                 : {nps if nps is not None else 'not found'}")
    lines.append(f"Target energy       : {args.target:.5f} MeV")
    if geb:
        lines.append(f"GEB (a,b,c)         : {a:g}, {b:g}, {c:g}")
        lines.append(f"GEB theoretical FWHM: {fwhm_th:.6f} MeV ({fwhm_th*1000:.2f} keV)")
    else:
        lines.append("GEB                  : not found")
    lines.append(f"Fit range           : {fit_range[0]:.5f} - {fit_range[1]:.5f} MeV")
    lines.append(f"Fitted centroid mu  : {mu:.6f} MeV")
    lines.append(f"Fitted sigma        : {sigma:.6f} MeV")
    lines.append(f"Fitted FWHM         : {fwhm_fit:.6f} MeV ({fwhm_fit*1000:.2f} keV)")
    if fwhm_th:
        lines.append(f"Fit/GEB FWHM ratio  : {fwhm_fit/fwhm_th:.4f}")

    lines.append("")
    if rec is not None:
        lines.append("RECOMMENDED ROI")
        lines.append("-" * 60)
        lines.append("Rule: capture >=99% of fitted Gaussian; among those,")
        lines.append("      choose the ROI with minimum approximate relative MC uncertainty.")
        lines.append(f"k sigma             : {rec['k_sigma']:.2f}")
        lines.append(f"ROI                 : {rec['roi_low_MeV']:.3f} - {rec['roi_high_MeV']:.3f} MeV")
        lines.append(f"Gaussian capture    : {rec['gaussian_capture_fraction']*100:.3f}%")
        lines.append(f"Gross F8            : {rec['gross_F8_per_history']:.8e} / history")
        lines.append(f"Fitted background   : {rec['fitted_background_F8']:.8e} / history")
        lines.append(f"Net peak F8         : {rec['net_peak_F8_per_history']:.8e} / history")
        lines.append(f"Approx rel unc.     : {rec['approx_rel_uncertainty']*100:.3f}%")
    else:
        lines.append("No ROI satisfied the >=99% capture rule.")

    if snr_best is not None:
        lines.append("")
        lines.append("SNR-OPTIMAL ROI (comparison only)")
        lines.append("-" * 60)
        lines.append(f"k sigma             : {snr_best['k_sigma']:.2f}")
        lines.append(f"ROI                 : {snr_best['roi_low_MeV']:.3f} - {snr_best['roi_high_MeV']:.3f} MeV")
        lines.append(f"Gaussian capture    : {snr_best['gaussian_capture_fraction']*100:.3f}%")
        lines.append(f"Net peak F8         : {snr_best['net_peak_F8_per_history']:.8e} / history")
        lines.append(f"Approx rel unc.     : {snr_best['approx_rel_uncertainty']*100:.3f}%")

    lines.append("")
    lines.append("NOTE")
    lines.append("-" * 60)
    lines.append("1) F8 is normalized per source history, not absolute experimental counts.")
    lines.append("2) ROI uncertainty is approximate because standard MCNP output does not")
    lines.append("   provide bin-to-bin covariance.")
    lines.append("3) Final thesis ROI should be fixed once using a high-statistics reference")
    lines.append("   spectrum, then applied unchanged to all T/H/D/detector cases.")
    lines.append("4) Do not re-fit and change ROI separately for every geometry when comparing")
    lines.append("   optimization cases; that would introduce an analysis-variable bias.")

    summary = "\n".join(lines)
    out_txt.write_text(summary, encoding="utf-8")

    print(summary)
    print("")
    print(f"Saved: {out_csv}")
    print(f"Saved: {out_png}")
    print(f"Saved: {out_txt}")


if __name__ == "__main__":
    main()
