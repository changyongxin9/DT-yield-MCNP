from __future__ import annotations

import csv
import re
from pathlib import Path

import matplotlib.pyplot as plt
import scienceplots  # noqa: F401


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTP = PROJECT_ROOT / "reference" / "T05_H25_D01_5E8" / "outp"
FIG_DIR = OUTP.parent.parent / "figs"
FIG_DIR.mkdir(parents=True, exist_ok=True)

row_pattern = re.compile(
    r"^\s*(?P<energy>[+-]?\d+(?:\.\d+)?E[+-]?\d+)\s+"
    r"(?P<value>[+-]?\d+(?:\.\d+)?E[+-]?\d+)\s+"
    r"(?P<relerr>[+-]?\d+(?:\.\d+)?)\s*$",
    re.IGNORECASE,
)

lines = OUTP.read_text(encoding="ascii", errors="replace").splitlines()
start = next(
    i
    for i, line in enumerate(lines)
    if "tally type 8    pulse height distribution" in line.lower()
)
end = next(
    (i for i in range(start + 1, len(lines)) if re.match(r"^\s*1tally\s+", lines[i])),
    len(lines),
)

rows = []
for line in lines[start:end]:
    match = row_pattern.match(line)
    if not match:
        continue
    energy = float(match.group("energy"))
    if 5.0 <= energy <= 7.0:
        value = float(match.group("value"))
        relerr = float(match.group("relerr"))
        rows.append((energy, value, relerr, value * relerr))

if not rows:
    raise RuntimeError("No tally-8 data found in the requested 5-7 MeV range")

csv_path = FIG_DIR / "energy_5_7MeV.csv"
with csv_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle)
    writer.writerow(["Energy_MeV", "Tally_Value", "Relative_Error", "One_Sigma"])
    writer.writerows(rows)

energy = [row[0] for row in rows]
value = [row[1] for row in rows]
sigma = [row[3] for row in rows]
lower = [max(v - s, 0.0) for v, s in zip(value, sigma)]
upper = [v + s for v, s in zip(value, sigma)]

plt.style.use(["science", "no-latex"])
fig, ax = plt.subplots(figsize=(7.2, 4.6), constrained_layout=True)
ax.plot(energy, value, color="#1f5a94", linewidth=1.25, label="MCNP tally 8")
ax.fill_between(
    energy,
    lower,
    upper,
    color="#1f5a94",
    alpha=0.16,
    linewidth=0,
    label=r"$\pm 1\sigma$",
)
ax.set_xlim(5.0, 7.0)
ax.set_xticks([5.0, 5.5, 6.0, 6.5, 7.0])
ax.set_xlabel("Energy (MeV)")
ax.set_ylabel("Pulse-height tally (number)")
ax.ticklabel_format(axis="y", style="sci", scilimits=(0, 0), useMathText=True)
ax.grid(True, which="major", linewidth=0.45, alpha=0.35)
ax.legend(frameon=False, loc="upper right")

png_path = FIG_DIR / "energy_5_7MeV.png"
pdf_path = FIG_DIR / "energy_5_7MeV.pdf"
fig.savefig(png_path, dpi=600, bbox_inches="tight")
fig.savefig(pdf_path, bbox_inches="tight")
plt.close(fig)

print(f"rows={len(rows)}")
print(f"energy_min={energy[0]:.4f} MeV")
print(f"energy_max={energy[-1]:.4f} MeV")
print(f"csv={csv_path}")
print(f"png={png_path}")
print(f"pdf={pdf_path}")
