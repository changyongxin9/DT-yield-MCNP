#!/usr/bin/env python3
"""Build the final T04/T05 Disk count comparison from existing outp files.

The F8 parser and fixed-window definitions are reused from process_scan.py.
Existing T04 per-case artifacts are never overwritten; this script writes the
new unified comparison artifacts and fills only missing T05 per-case data.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from pathlib import Path

from process_scan import extract_nps, extract_spectrum, inspect_tfc, select_window, write_raw, WINDOWS

NPS_LEVELS = (("1E8", 100_000_000), ("3E8", 300_000_000), ("5E8", 500_000_000),
              ("7E8", 700_000_000), ("1E9", 1_000_000_000))
ROI = "ROI_6.03_6.23"


def output_path(root: Path, t: int, label: str) -> Path:
    return root / f"T{t:02d}_H25_D01" / f"CaO_SourceCompare_{label}" / "Disk_D10" / "output" / "outp"


def parse_outp(path: Path, case: str, expected_nps: int) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    if re.search(r"(?i)fatal error|bad trouble|unexpected eof", text):
        raise ValueError(f"{case}: fatal MCNP marker found in outp")
    nps = extract_nps(text, case)
    if nps != expected_nps:
        raise ValueError(f"{case}: NPS {nps}, expected {expected_nps}")
    rows = extract_spectrum(text, case)
    tfc, tfc_note = inspect_tfc(text)
    sums, sigmas, max_re = {}, {}, 0.0
    windows = {}
    for field, low, high, count in WINDOWS:
        selected = select_window(rows, low, high, count, case)
        windows[field] = selected
        sums[field] = math.fsum(row.response for row in selected)
        sigmas[field] = math.sqrt(math.fsum((row.response * row.relative_error) ** 2 for row in selected))
        if field == ROI:
            max_re = max(row.relative_error for row in selected)
    return {"case": case, "nps": nps, "rows": rows, "sums": sums, "sigmas": sigmas,
            "max_re": max_re, "tfc": tfc, "tfc_note": tfc_note}


def write_case_outputs(case_dir: Path, result: dict, write_files: bool) -> None:
    data = case_dir / "data"
    data.mkdir(parents=True, exist_ok=True)
    if not write_files:
        return
    for name in ("spec.csv", "roi.csv", "summary.txt"):
        target = data / name
        if target.exists():
            raise FileExistsError(f"Refusing to overwrite {target}")
    write_raw(data / "spec.csv", result["rows"])
    with (data / "roi.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("Energy_MeV", "F8_Response", "Relative_Error"))
        for row in result["rows"]:
            if 6.09 - 5e-7 <= row.energy <= 6.17 + 5e-7:
                writer.writerow((f"{row.energy:.4f}", f"{row.response:.8E}", f"{row.relative_error:.6g}"))
    with (data / "summary.txt").open("w", encoding="utf-8") as handle:
        handle.write(f"Case: Disk_D10\nNPS: {result['nps']}\nTarget Energy: 6.13 MeV\n")
        target = next(row for row in result["rows"] if math.isclose(row.energy, 6.13, abs_tol=5e-7))
        handle.write(f"F8 @ 6.13 MeV: {target.response:.8E}\nRE @ 6.13 MeV: {target.relative_error:.6g}\n")
        handle.write("ROI Range: 6.09-6.17 MeV\n")
        handle.write(f"ROI Sum: {sum(row.response for row in result['rows'] if 6.09 <= row.energy <= 6.17):.8E}\n")
        peak = max((row for row in result["rows"] if 6.09 <= row.energy <= 6.17), key=lambda row: row.response)
        handle.write(f"ROI Max Energy: {peak.energy:.2f} MeV\nROI Max F8: {peak.response:.8E}\nROI Max RE: {peak.relative_error:.6g}\n")


def write_nps_compare(path: Path, results: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("NPS", *(window[0] for window in WINDOWS)))
        for result in results:
            writer.writerow((result["nps"], *(f"{result['sums'][window[0]]:.8E}" for window in WINDOWS)))


def write_full_spectrum(path: Path, result: dict) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("Energy_MeV", "F8_Response", "Relative_Error"))
        for row in result["rows"]:
            writer.writerow((f"{row.energy:.4f}", f"{row.response:.8E}", f"{row.relative_error:.6g}"))


def write_final_compare(path: Path, t04: list[dict], t05: list[dict]) -> None:
    by04 = {result["nps"]: result for result in t04}
    by05 = {result["nps"]: result for result in t05}
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("NPS", "T04_Left", "T04_ROI", "T04_Right", "T05_Left", "T05_ROI", "T05_Right", "T04_vs_T05_ROI_Difference_percent"))
        for _, nps in NPS_LEVELS:
            a, b = by04[nps], by05[nps]
            delta = (a["sums"][ROI] - b["sums"][ROI]) / b["sums"][ROI] * 100.0
            writer.writerow((nps, f"{a['sums']['Left_5.95_6.02']:.8E}", f"{a['sums'][ROI]:.8E}", f"{a['sums']['Right_6.24_6.31']:.8E}", f"{b['sums']['Left_5.95_6.02']:.8E}", f"{b['sums'][ROI]:.8E}", f"{b['sums']['Right_6.24_6.31']:.8E}", f"{delta:+.4f}"))


def write_conclusion(path: Path, t04: list[dict], t05: list[dict]) -> None:
    def by_nps(rows): return {r["nps"]: r for r in rows}
    a, b = by_nps(t04), by_nps(t05)
    lines = ["# 最终计数收敛性与厚度对比", "", "## 数据范围与方法", "",
             "本次仅处理T04_H25_D01和T05_H25_D01的Disk圆片源结果；源为Φ10 mm、14.1 MeV，H=25 cm、D=1 cm。"
             "T04为Rout=9 cm、T=4 cm，T05为Rout=10 cm、T=5 cm。所有原始outp均保留不动。",
             "主指标为6.03–6.23 MeV范围内的F8脉冲高度响应之和（21个bin）；左、右邻近能区分别为5.95–6.02 MeV和6.24–6.31 MeV，均直接求和，不乘能道宽度。", ""]
    for t, data in ((4, a), (5, b)):
        ref = data[500_000_000]["sums"][ROI]
        lines += [f"## T={t} cm的NPS收敛", "", "| NPS | Gross ROI | 相对5E8差异 |"]
        lines += ["|---:|---:|---:|"]
        for label, nps in NPS_LEVELS:
            value = data[nps]["sums"][ROI]
            diff = (value - ref) / ref * 100.0
            lines.append(f"| {label} | {value:.8E} | {diff:+.3f}% |" )
        d71 = (data[700_000_000]["sums"][ROI] - data[500_000_000]["sums"][ROI]) / data[500_000_000]["sums"][ROI] * 100
        d91 = (data[1_000_000_000]["sums"][ROI] - data[500_000_000]["sums"][ROI]) / data[500_000_000]["sums"][ROI] * 100
        lines.append(f"5E8→7E8变化为{d71:+.3f}%，5E8→1E9变化为{d91:+.3f}%。")
        lines.append("该差异需结合各ROI bin的相对误差解释；本表用于收敛性判断，不以单个6.13 MeV bin代替Gross ROI。")
        lines.append("")
    lines += ["## T04与T05同NPS比较", "", "| NPS | T04 ROI | T05 ROI | T04相对T05 |"]
    lines += ["|---:|---:|---:|---:|"]
    for _, nps in NPS_LEVELS:
        delta = (a[nps]["sums"][ROI] - b[nps]["sums"][ROI]) / b[nps]["sums"][ROI] * 100
        lines.append(f"| {nps:.0f} | {a[nps]['sums'][ROI]:.8E} | {b[nps]['sums'][ROI]:.8E} | {delta:+.3f}% |")
    d = (a[500_000_000]["sums"][ROI] - b[500_000_000]["sums"][ROI]) / b[500_000_000]["sums"][ROI] * 100
    lines += ["", f"在5E8条件下，T04的Gross ROI为{a[500_000_000]['sums'][ROI]:.8E}，T05为{b[500_000_000]['sums'][ROI]:.8E}，T04相对T05高{d:.3f}%。", "",
              "两组左右邻近能区也随厚度和几何变化同步列入CSV；这些区间仅作响应形状对照，不作本底扣除。",
              "前面的厚度优化同样显示T=4 cm在H=25 cm下的Gross ROI高于T=5 cm，本次五档NPS结果与该趋势一致。",
              "", "## 结论与限制", "",
              "若将5E8与7E8、1E9的Gross ROI差异与统计误差相比处于可接受范围，则5E8可作为后续正式比较的统计量；最终采用时应同时查看各bin Relative_Error，而不能只依据单个峰值bin。",
              "MCNP输出中的La/Br .71c γ产生截面缺失和F8可靠性警告仍然存在。因此本结果适用于相同模型下的NPS收敛与T04/T05相对比较，不能表述为实验验证的绝对探测效率或净全能峰效率。"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parent.parent / "最终计数")
    args = parser.parse_args()
    root = args.root.resolve()
    parsed = {t: [] for t in (4, 5)}
    for t in (4, 5):
        for label, nps in NPS_LEVELS:
            case = f"T{t:02d}_H25_D01"
            outp = output_path(root, t, label)
            if not outp.is_file(): raise FileNotFoundError(outp)
            result = parse_outp(outp, case + "_" + label, nps)
            parsed[t].append(result)
            case_dir = outp.parents[1]
            write_case_outputs(case_dir, result, write_files=(t == 5))
            print(f"PASS {case} {label}: NPS={result['nps']}, rows={len(result['rows'])}, TFC={result['tfc']}")
    summary = root / "总结数据"
    summary.mkdir(parents=True, exist_ok=True)
    t04, t05 = parsed[4], parsed[5]
    write_nps_compare(root / "T04_H25_D01" / "T04_NPS_compare.csv", t04)
    write_nps_compare(root / "T05_H25_D01" / "T05_NPS_compare.csv", t05)
    write_full_spectrum(summary / "T04_H25_D01_5E8_full_spectrum.csv", t04[2])
    write_full_spectrum(summary / "T05_H25_D01_5E8_full_spectrum.csv", t05[2])
    write_final_compare(summary / "Final_T04_T05_compare.csv", t04, t05)
    write_conclusion(summary / "Final_count_conclusion.md", t04, t05)
    print("PASS final count outputs")


if __name__ == "__main__":
    main()
