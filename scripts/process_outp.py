#!/usr/bin/env python3
"""Extract MCNP6 pulse-height tally 8 data and build optional comparisons.

Usage:
    python process_outp.py path\\to\\case\\output\\outp

The script only reads the supplied outp and writes analysis artifacts below
the corresponding case directory. It never changes the original outp or i
file. ROI figures are created only through Origin/OriginPro.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


TARGET_ENERGY = 6.13
ROI_LOW = 6.09
ROI_HIGH = 6.17
EXPECTED_BINS = 1600
ORIGIN_EXE = Path(r"E:\Origin Pro2024\Origin64.exe")

NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"
DATA_RE = re.compile(rf"^\s*({NUMBER})\s+({NUMBER})\s+({NUMBER})\s*$")
TALLY_RE = re.compile(r"^\s*1tally\s+8\b", re.IGNORECASE)


def to_float(value: str) -> float:
    return float(value.replace("D", "E").replace("d", "e"))


def display_number(value: float | str) -> str:
    if isinstance(value, str):
        return value
    if value.is_integer():
        return str(int(value))
    return f"{value:.12g}"


def infer_case_dir(outp: Path) -> Path:
    """Infer Case/ from the conventional Case/output/outp layout."""
    if outp.parent.name.lower() == "output":
        return outp.parent.parent
    return outp.parent


def extract_nps(text: str) -> str:
    patterns = (
        rf"1tally\s+8\s+nps\s*=\s*({NUMBER})",
        rf"run\s+terminated\s+when\s*({NUMBER})\s+particle\s+histories",
        rf"^\s*nps\s+({NUMBER})\s*$",
        rf"original\s+number\s+of\s+histories\s+was\s*({NUMBER})",
        rf"number\s+of\s+histories\s+used\s+for\s+normalizing\s+tallies\s*=\s*({NUMBER})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return display_number(to_float(match.group(1)))
    return "Unknown"


def extract_tally(text: str) -> list[tuple[float, float, float]]:
    lines = text.splitlines()
    tally_line = next((i for i, line in enumerate(lines) if TALLY_RE.search(line)), None)
    if tally_line is None:
        raise ValueError("1tally 8 was not found")

    energy_header = next(
        (i for i in range(tally_line + 1, len(lines)) if lines[i].strip().lower() == "energy"),
        tally_line + 1,
    )
    rows: list[tuple[float, float, float]] = []
    for line in lines[energy_header + 1 :]:
        stripped = line.strip().lower()
        if stripped.startswith("total") or TALLY_RE.search(line):
            break
        match = DATA_RE.match(line)
        if not match:
            continue
        energy, response, relative_error = (to_float(group) for group in match.groups())
        if not all(math.isfinite(value) for value in (energy, response, relative_error)):
            continue
        rows.append((energy, response, relative_error))
        if len(rows) >= EXPECTED_BINS:
            break

    if not rows:
        raise ValueError("no numeric rows found after 1tally 8 energy header")
    if len(rows) != EXPECTED_BINS:
        raise ValueError(f"expected {EXPECTED_BINS} energy bins, found {len(rows)}")
    return rows


def write_spectrum(case_dir: Path, rows: list[tuple[float, float, float]]) -> Path:
    data_dir = case_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / "spec.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(("Energy_MeV", "F8_Response_per_source_neutron", "Relative_Error"))
        for energy, response, relative_error in rows:
            writer.writerow((f"{energy:.8g}", f"{response:.8g}", f"{relative_error:.8g}"))
    return path


def select_metrics(rows: list[tuple[float, float, float]]) -> dict[str, float | str]:
    target = min(rows, key=lambda row: abs(row[0] - TARGET_ENERGY))
    roi = [row for row in rows if ROI_LOW <= row[0] <= ROI_HIGH]
    if not roi:
        raise ValueError(f"no spectrum bins found in ROI {ROI_LOW}-{ROI_HIGH} MeV")
    roi_max = max(roi, key=lambda row: row[1])
    return {
        "target_energy": target[0],
        "target_f8": target[1],
        "target_re": target[2],
        "roi_sum": sum(row[1] for row in roi),
        "roi_max_energy": roi_max[0],
        "roi_max_f8": roi_max[1],
        "roi_max_re": roi_max[2],
    }


def write_roi(case_dir: Path, rows: list[tuple[float, float, float]]) -> Path:
    path = case_dir / "data" / "roi.csv"
    roi = [row for row in rows if ROI_LOW <= row[0] <= ROI_HIGH]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(("Energy_MeV", "F8_Response_per_source_neutron", "Relative_Error"))
        for energy, response, relative_error in roi:
            writer.writerow((f"{energy:.8g}", f"{response:.8g}", f"{relative_error:.8g}"))
    return path


def write_summary(case_dir: Path, nps: str, metrics: dict[str, float | str]) -> Path:
    path = case_dir / "data" / "summary.txt"
    lines = [
        f"Case: {case_dir.name}",
        f"NPS: {nps}",
        f"Target Energy: {TARGET_ENERGY:.2f} MeV",
        f"F8 @ 6.13 MeV: {metrics['target_f8']:.8E}",
        f"RE @ 6.13 MeV: {metrics['target_re']:.8g}",
        f"ROI Range: {ROI_LOW:.2f}-{ROI_HIGH:.2f} MeV",
        f"ROI Sum: {metrics['roi_sum']:.8E}",
        f"ROI Max Energy: {metrics['roi_max_energy']:.8g} MeV",
        f"ROI Max F8: {metrics['roi_max_f8']:.8E}",
        f"ROI Max RE: {metrics['roi_max_re']:.8g}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def format_nps_title(nps: str) -> str:
    try:
        value = float(nps)
    except (TypeError, ValueError):
        return str(nps)
    if value <= 0:
        return str(nps)
    exponent = int(math.floor(math.log10(value)))
    mantissa = value / (10 ** exponent)
    if abs(mantissa - round(mantissa)) < 1e-10:
        mantissa_text = str(int(round(mantissa)))
    else:
        mantissa_text = f"{mantissa:.3g}"
    superscript = str(exponent).translate(str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹"))
    return f"{mantissa_text}×10{superscript}"


def case_title(case_dir: Path, nps: str) -> str:
    nps_text = format_nps_title(nps)
    name = case_dir.name.lower()
    if "disk" in name:
        return f"Φ10 mm片源，NPS={nps_text}"
    if "point" in name:
        return f"点源，NPS={nps_text}"
    return f"{case_dir.name}，NPS={nps_text}"


def _start_origin() -> subprocess.Popen[bytes]:
    if not ORIGIN_EXE.is_file():
        raise FileNotFoundError(f"Origin executable not found: {ORIGIN_EXE}")
    return subprocess.Popen([str(ORIGIN_EXE)], cwd=str(ORIGIN_EXE.parent))


def _labtalk_path(path: Path) -> str:
    """Return a LabTalk-safe forward-slash path."""
    return str(path.resolve()).replace("\\", "/").replace('"', '""')


def _origin_commands(
    case_dir: Path,
    nps: str,
    roi_csv: Path,
    png: Path,
    roi_rows: list[tuple[float, float, float]] | None = None,
) -> list[str]:
    """Build the same LabTalk commands for originpro and COM automation."""
    title = case_title(case_dir, nps).replace('"', '""')
    csv_path = _labtalk_path(roi_csv)
    png_path = _labtalk_path(png)
    values = roi_rows or []
    if values:
        min_scaled = min(row[1] for row in values) * 1e6
        max_scaled = max(row[1] for row in values) * 1e6
        y_min = max(0.0, math.floor(min_scaled / 0.05) * 0.05) * 1e-6
        y_max = math.ceil((max_scaled + 0.05) / 0.05) * 0.05 * 1e-6
    else:
        y_min, y_max = 0.95e-6, 1.50e-6
    commands = [
        "newbook name:=ROI;",
        f'impCSV fname:="{csv_path}";',
        "plotxy iy:=(1,2) plot:=202 legend:=0;",
        "set %C -l 1; set %C -k 2; set %C -c color(31,78,121,1);",
        "label -r legend;",
        "page.baseColor=color(white); page.cntrl=16; system.extBackColor=0;",
        "layer.color=color(white);",
        "layer.x.from=6.09; layer.x.to=6.17; layer.x.inc=0.01;",
        "layer.x.label.decPlaces=2;",
        f"layer.y.from={y_min:.12g}; layer.y.to={y_max:.12g}; layer.y.inc=0.05e-6;",
        "label -xb (能量 / MeV);",
        "label -yl (F8响应 / 源中子);",
        "layer.y.label.numFormat=2;",
        "layer.y.label.decPlaces=2;",
        "layer.y.label.scientificnotationpower=-6;",
        "layer.y.label.scientificnotationpos=1;",
        "draw -n TargetLine -d 1 -w 1.5 -l -v 6.13;",
        f"label -a 6.145 {y_max * 0.93:.12g} -n TargetLabel (6.13 MeV);",
        f"label -a 6.145 {y_max * 0.985:.12g} -j 0 -n PlotTitle ({title});",
        f'expGraph type:=png filename:="{Path(png_path).stem}" path:="{Path(png_path).parent.as_posix()}" overwrite:=replace tr1.Unit:=2 tr1.Width:=1200;',
    ]
    if values:
        for index, (energy, response, _relative_error) in enumerate(values):
            mantissa = response * 1e6
            label = f"{mantissa:.2f}e-6"
            offset = 0.035e-6 if index % 2 == 0 else -0.045e-6
            label_y = response + offset
            commands.insert(
                -1,
                f"label -a {energy:.8g} {label_y:.12g} -n PointLabel{index} ({label}); "
                f"PointLabel{index}.fsize=9;",
            )
    return commands


def _originpro_plot(case_dir: Path, rows: list[tuple[float, float, float]], nps: str) -> tuple[Path, Path]:
    """Probe originpro, which is not usable for plotting on this install."""
    import originpro  # type: ignore  # noqa: F401

    raise RuntimeError(
        "originpro is installed, but OriginExt high-level worksheet/graph "
        "automation is unavailable on this Origin installation; use Origin COM"
    )


def _origin_com_plot(case_dir: Path, rows: list[tuple[float, float, float]], nps: str) -> tuple[Path, Path]:
    """Fallback plot through Origin's Windows COM automation interface."""
    import win32com.client  # type: ignore

    figures = case_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    png = figures / "roi_6.09_6.17.png"
    opju = figures / "roi_6.09_6.17.opju"
    roi = [row for row in rows if ROI_LOW <= row[0] <= ROI_HIGH]
    if not roi:
        raise ValueError("no ROI rows available for Origin COM plot")

    # COM imports the existing ROI CSV, creates a line+symbol graph, then
    # applies axis labels/range and saves the project and raster export.
    app = None
    process = _start_origin()
    try:
        last_error: Exception | None = None
        for _ in range(30):
            try:
                app = win32com.client.Dispatch("Origin.ApplicationSI")
                break
            except Exception as exc:
                last_error = exc
                time.sleep(1)
        if app is None:
            raise RuntimeError(f"Origin COM unavailable after launching Origin64.exe: {last_error}")
        app.Visible = False
        app.NewProject()
        commands = _origin_commands(case_dir, nps, case_dir / "data" / "roi.csv", png, roi)
        for command in commands:
            app.Execute(command)
        if not app.Save(str(opju)):
            raise RuntimeError("Origin COM Save() returned false")
    finally:
        if app is not None:
            try:
                app.Exit()
            except Exception:
                pass
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
    if not png.is_file() or not opju.is_file():
        raise RuntimeError("Origin COM did not create both PNG and OPJU files")
    return png, opju


def _origin_cli_plot(case_dir: Path, rows: list[tuple[float, float, float]], nps: str) -> tuple[Path, Path]:
    """Use Origin's documented -rs command-line LabTalk automation fallback."""
    figures = case_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    png = figures / "roi_6.09_6.17.png"
    opju = figures / "roi_6.09_6.17.opju"
    roi = [row for row in rows if ROI_LOW <= row[0] <= ROI_HIGH]
    if not roi:
        raise ValueError("no ROI rows available for Origin command-line plot")

    with tempfile.TemporaryDirectory(prefix="origin_roi_") as temp_dir:
        temp = Path(temp_dir)
        csv_path = temp / "roi.csv"
        temp_png = temp / png.name
        temp_opju = temp / opju.name
        with csv_path.open("w", newline="", encoding="ascii") as handle:
            writer = csv.writer(handle)
            writer.writerow(("Energy_MeV", "F8_Response_per_source_neutron"))
            writer.writerows((row[0], row[1]) for row in roi)
        commands = _origin_commands(case_dir, nps, csv_path, temp_png, roi)
        commands.extend([
            f'save -dix "{_labtalk_path(temp_opju)}";',
            "doc -s;",
            "exit;",
        ])
        script = temp / "plot.ogs"
        script.write_text("[Main]\n" + "\n".join(commands) + "\n", encoding="utf-8-sig")
        script_arg = script.as_posix().replace('"', '""')
        command = f'run.section("{script_arg}",Main)'
        completed = subprocess.run(
            [str(ORIGIN_EXE), "-H", "-rs", command],
            cwd=str(ORIGIN_EXE.parent),
            timeout=180,
            check=False,
        )
        if completed.returncode not in (0, None):
            raise RuntimeError(f"Origin command-line process returned {completed.returncode}")
        if not temp_png.is_file() or not temp_opju.is_file():
            raise RuntimeError("Origin command-line script did not create PNG and OPJU")
        shutil.copy2(temp_png, png)
        shutil.copy2(temp_opju, opju)
    return png, opju


def plot_roi_with_origin(case_dir: Path, rows: list[tuple[float, float, float]], nps: str) -> tuple[Path, Path]:
    """Try originpro, COM, then Origin command-line; no raster fallback."""
    errors: list[str] = []
    try:
        return _originpro_plot(case_dir, rows, nps)
    except Exception as exc:
        errors.append(f"originpro: {type(exc).__name__}: {exc}")
    try:
        return _origin_com_plot(case_dir, rows, nps)
    except Exception as exc:
        errors.append(f"Origin COM: {type(exc).__name__}: {exc}")
    try:
        return _origin_cli_plot(case_dir, rows, nps)
    except Exception as exc:
        errors.append(f"Origin CLI: {type(exc).__name__}: {exc}")
    raise RuntimeError(
        "Origin plotting unavailable; no raster-library fallback was used. " + " | ".join(errors)
    )


def read_summary(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip().split()[0]
    return values


def write_comparison(case_dir: Path) -> Path | None:
    root = case_dir.parent
    entries: list[dict[str, str]] = []
    for sibling in sorted(root.iterdir()):
        summary = sibling / "data" / "summary.txt"
        if sibling.is_dir() and sibling.name.lower() != "compare" and summary.is_file():
            values = read_summary(summary)
            entries.append(
                {
                    "Case": sibling.name,
                    "NPS": values.get("NPS", "Unknown"),
                    "F8_6.13": values.get("F8 @ 6.13 MeV", ""),
                    "RE_6.13": values.get("RE @ 6.13 MeV", ""),
                    "ROI_Sum": values.get("ROI Sum", ""),
                    "ROI_Max_Energy": values.get("ROI Max Energy", ""),
                    "ROI_Max_F8": values.get("ROI Max F8", ""),
                    "ROI_Max_RE": values.get("ROI Max RE", ""),
                }
            )
    if len(entries) < 2:
        return None

    disk = next((row for row in entries if "disk" in row["Case"].lower()), None)
    point = next((row for row in entries if "point" in row["Case"].lower()), None)
    delta = ""
    if disk and point:
        try:
            point_sum = float(point["ROI_Sum"])
            disk_sum = float(disk["ROI_Sum"])
            if point_sum != 0:
                delta = f"{(disk_sum - point_sum) / point_sum * 100:.8g}"
        except (TypeError, ValueError):
            delta = ""

    compare_dir = root / "Compare" / "data"
    compare_dir.mkdir(parents=True, exist_ok=True)
    path = compare_dir / "comparison.csv"
    fields = [
        "Case", "NPS", "F8_6.13", "RE_6.13", "ROI_Sum",
        "ROI_Max_Energy", "ROI_Max_F8", "ROI_Max_RE", "Delta_ROI_percent",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in entries:
            row["Delta_ROI_percent"] = delta
            writer.writerow(row)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outp", type=Path, help="MCNP6 outp file")
    parser.add_argument("--case-dir", type=Path, help="override inferred Case directory")
    parser.add_argument("--no-comparison", action="store_true", help="do not scan sibling cases")
    args = parser.parse_args()

    outp = args.outp.resolve()
    if not outp.is_file():
        parser.error(f"outp file not found: {outp}")
    case_dir = (args.case_dir or infer_case_dir(outp)).resolve()

    try:
        text = outp.read_text(encoding="utf-8", errors="replace")
        rows = extract_tally(text)
        nps = extract_nps(text)
        metrics = select_metrics(rows)
        spec_path = write_spectrum(case_dir, rows)
        roi_path = write_roi(case_dir, rows)
        summary_path = write_summary(case_dir, nps, metrics)
        png_path, opju_path = plot_roi_with_origin(case_dir, rows, nps)
        comparison_path = None if args.no_comparison else write_comparison(case_dir)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Case: {case_dir.name}")
    print(f"Bins: {len(rows)}")
    print(f"NPS: {nps}")
    print(f"spec.csv: {spec_path}")
    print(f"roi.csv: {roi_path}")
    print(f"summary.txt: {summary_path}")
    print(f"ROI figure: {png_path}")
    print(f"Origin project: {opju_path}")
    if comparison_path:
        print(f"comparison.csv: {comparison_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
