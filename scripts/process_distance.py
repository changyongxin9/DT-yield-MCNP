#!/usr/bin/env python3
"""Summarize the completed D01-D04 scan with the existing F8 parser."""

from __future__ import annotations

import argparse
import csv
import math
import re
from pathlib import Path

from process_scan import (
    WINDOWS,
    extract_nps,
    extract_spectrum,
    inspect_tfc,
    select_window,
    write_raw,
)

ROI = "ROI_6.03_6.23"
CASES = [(t, d, f"T{t:02d}_H25_D{d:02d}") for t in (4, 5) for d in (1, 2, 3, 4)]


def case_paths(root: Path, t: int, d: int, name: str) -> tuple[Path, Path, Path]:
    case = root / f"T{t:02d}_H25" / name
    return (
        case / "结果输出" / "outp",
        case / "数据处理" / "原始数据" / f"T{t:02d}_H25_D{d:02d}_F8_raw.csv",
        case / "数据处理" / "分析结果" / f"T{t:02d}_H25_D{d:02d}_sum.csv",
    )


def process(root: Path) -> list[dict]:
    found = sorted(
        path.name
        for group in ("T04_H25", "T05_H25")
        for path in (root / group).iterdir()
        if path.is_dir()
    )
    expected = sorted(name for _, _, name in CASES)
    if found != expected:
        raise ValueError(f"Case mismatch: missing={sorted(set(expected)-set(found))}, "
                         f"extra={sorted(set(found)-set(expected))}")

    summary = root / "总结数据"
    compare = summary / "Distance_compare.csv"
    conclusion = summary / "Distance_conclusion.md"
    targets = [compare, conclusion]
    for t, d, name in CASES:
        outp, raw, case_sum = case_paths(root, t, d, name)
        if not outp.is_file():
            raise FileNotFoundError(f"{name}: missing {outp}")
        targets.extend((raw, case_sum))
    existing = [str(path) for path in targets if path.exists()]
    if existing:
        raise FileExistsError("Refusing to overwrite existing results: " + ", ".join(existing))

    results = []
    for t, d, name in CASES:
        outp, raw, case_sum = case_paths(root, t, d, name)
        text = outp.read_text(encoding="utf-8", errors="replace")
        if re.search(r"(?i)fatal error|bad trouble|unexpected eof", text):
            raise ValueError(f"{name}: MCNP failure marker found")
        if not re.search(rf"(?m)^\s*i={re.escape(name)}\.i\b", text):
            raise ValueError(f"{name}: outp input name does not match the case")
        nps = extract_nps(text, name)
        if nps != 500_000_000:
            raise ValueError(f"{name}: NPS={nps}, expected 500000000")
        rows = extract_spectrum(text, name)
        tfc, tfc_note = inspect_tfc(text)
        sums, sigmas = {}, {}
        for field, low, high, count in WINDOWS:
            window = select_window(rows, low, high, count, name)
            sums[field] = math.fsum(row.response for row in window)
            sigmas[field] = math.sqrt(math.fsum(
                (row.response * row.relative_error) ** 2 for row in window
            ))
            if field == ROI:
                max_re = max(row.relative_error for row in window)
                if any(row.response <= 0 for row in window):
                    raise ValueError(f"{name}: zero/negative response in ROI")
        results.append(dict(name=name, t=t, d=d, rows=rows, sums=sums,
                            sigmas=sigmas, max_re=max_re, tfc=tfc, tfc_note=tfc_note,
                            raw=raw, case_sum=case_sum))
    for result in results:
        result["raw"].parent.mkdir(parents=True, exist_ok=True)
        result["case_sum"].parent.mkdir(parents=True, exist_ok=True)
        write_raw(result["raw"], result["rows"])
        with result["case_sum"].open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(("Case", "T_cm", "H_cm", "D_cm", *(w[0] for w in WINDOWS)))
            writer.writerow((result["name"], result["t"], 25, result["d"],
                             *(f"{result['sums'][w[0]]:.8E}" for w in WINDOWS)))
        print(f"PASS {result['name']}: ROI={result['sums'][ROI]:.8E}, "
              f"max bin RE={result['max_re']:.4f}, {result['tfc_note']}")
    summary.mkdir(parents=True, exist_ok=True)
    with compare.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("T_cm", "H_cm", "D_cm", *(w[0] for w in WINDOWS)))
        for result in results:
            writer.writerow((result["t"], 25, result["d"],
                             *(f"{result['sums'][w[0]]:.8E}" for w in WINDOWS)))
    write_conclusion(conclusion, results)
    print(f"PASS {compare}")
    print(f"PASS {conclusion}")
    return results


def write_conclusion(path: Path, results: list[dict]) -> None:
    lines = [
        "# CaO探测器距离优化第一轮结果",
        "",
        "## 数据与统计方法",
        "",
        "两条支线固定H=25 cm、Rin=5 cm；T04的Rout=9 cm，T05的Rout=10 cm。"
        "各支线扫描晶体前端至CaO外表面的距离D=1、2、3、4 cm，NPS均为5×10^8。",
        "从完整F8:P能谱直接对5.95–6.02 MeV（8 bin）、6.03–6.23 MeV（21 bin）"
        "和6.24–6.31 MeV（8 bin）分别求和；不乘能道宽度，不作平滑、拟合或本底扣除。"
        "主指标是6.13 MeV峰区Gross ROI响应，不是净峰效率或实验测定的绝对效率。",
        "ROI的近似标准不确定度由各bin的F8响应×相对误差按平方和开方估计。"
        "相邻案例以两者标准不确定度平方和开方估计差值的z值；"
        "未获得跨能道及跨计算的协方差，z值仅作近似统计判断。",
        "",
    ]
    roi = ROI
    for t in (4, 5):
        branch = [r for r in results if r["t"] == t]
        values = [r["sums"][roi] for r in branch]
        errors = [r["sigmas"][roi] for r in branch]
        lines.extend([f"## T={t} cm、H=25 cm", "",
                      f"D=1至4 cm的Gross ROI响应依次为："
                      + "、".join(f"{v:.8E}" for v in values) + "。"
                      + ("随距离增加严格递减。" if all(a > b for a, b in zip(values, values[1:]))
                         else "未呈严格单调递减，需核对局部波动。")])
        changes = []
        for before, after in zip(branch, branch[1:]):
            previous, current = before["sums"][roi], after["sums"][roi]
            change = (current - previous) / previous * 100
            denom = math.hypot(before["sigmas"][roi], after["sigmas"][roi])
            z = abs(current - previous) / denom if denom else math.inf
            verdict = ("差异超过约2倍合成统计不确定度" if z >= 2 else
                       "差异与统计误差处于相同量级，暂不能认为差异显著")
            lines.append(f"D{before['d']:02d}→D{after['d']:02d}：{change:+.2f}%，"
                         f"近似z={z:.2f}；{verdict}。")
            changes.append((change, before["d"], after["d"]))
        fastest = min(changes)
        lines.append(f"以相邻绝对百分比降幅计，D={fastest[1]}→{fastest[2]} cm下降最快"
                     f"（{fastest[0]:+.2f}%）。")
        lines.append(f"最大ROI bin相对误差随D依次为："
                     + "、".join(f"{r['max_re']*100:.2f}%" for r in branch)
                     + "；ROI求和的近似相对不确定度依次为："
                     + "、".join(f"{r['sigmas'][roi]/r['sums'][roi]*100:.2f}%" for r in branch)
                     + "。")
        for field, label in (("Left_5.95_6.02", "左侧"),
                             ("Right_6.24_6.31", "右侧")):
            lines.append(f"{label}独立能区响应由{branch[0]['sums'][field]:.8E}"
                         f"变化到{branch[-1]['sums'][field]:.8E}；不作为本底扣除。")
        lines.append("")
    lines += ["## 同距离厚度比较与后续扫描", ""]
    for d in range(1, 5):
        a = next(r for r in results if r["t"] == 4 and r["d"] == d)
        b = next(r for r in results if r["t"] == 5 and r["d"] == d)
        change = (b["sums"][roi] - a["sums"][roi]) / a["sums"][roi] * 100
        denom = math.hypot(a["sigmas"][roi], b["sigmas"][roi])
        z = abs(b["sums"][roi] - a["sums"][roi]) / denom if denom else math.inf
        lines.append(f"D={d} cm：T04={a['sums'][roi]:.8E}、T05={b['sums'][roi]:.8E}，"
                     f"T05相对T04变化{change:+.2f}%，近似z={z:.2f}；"
                     + ("两者差异超过约2倍合成统计不确定度。" if z >= 2 else
                        "暂不能认为厚度差异显著。"))
    lines += [
        "", "两条支线的D=1–4 cm结果足以观察当前采样范围内的距离响应趋势，"
        "但不能外推更远距离或宣称存在内部最优。若工程安装需要D≥5 cm，"
        "或要确定响应保留阈值对应距离，再补充D=5 cm及更远点；"
        "仅为判断本轮下降趋势，无需自动扩大扫描。",
        "", "## 物理与统计限制", "",
        "各输出的F8波动图bin通过10项TFC检查；该结论不保证ROI每个bin均通过。"
        "La/Br .71c库提示缺少γ产生截面；MCNP还报告中子非模拟输运下F8可能不可靠、"
        "强制模拟俘获及关闭F8方差缩减，并提示部分全谱bin相对误差较高。"
        "因此本轮优先用于相同物理设置下的相对距离趋势比较，"
        "不得表述为已实验验证的绝对探测效率；F8相关警告仍需后续物理核查。",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scan_dir", nargs="?", type=Path,
                        default=Path(__file__).resolve().parent.parent / "距离优化")
    args = parser.parse_args()
    process(args.scan_dir.resolve())


if __name__ == "__main__":
    main()
