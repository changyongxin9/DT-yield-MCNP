#!/usr/bin/env python3
"""Post-process the completed T04/T05 length scan using process_scan helpers."""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from pathlib import Path

from process_scan import (
    WINDOWS,
    CaseResult,
    extract_nps,
    extract_spectrum,
    inspect_tfc,
    select_window,
    write_raw,
)


CASE_RE = re.compile(r"^T(?P<T>04|05)_H(?P<H>20|25|30|35|40|45|50)_D01$")
EXPECTED = [
    f"T{thickness:02d}_H{height:02d}_D01"
    for thickness in (4, 5)
    for height in (20, 25, 30, 35, 40, 45, 50)
]


def parse_case(case_dir: Path) -> tuple[int, int]:
    match = CASE_RE.fullmatch(case_dir.name)
    if not match:
        raise ValueError(f"{case_dir.name}: expected T04/T05_H20..H50_D01")
    return int(match.group("T")), int(match.group("H"))


def write_case_sum(path: Path, result: CaseResult, height: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["Case", "T_cm", "H_cm", *(window[0] for window in WINDOWS)]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        writer.writerow(
            (
                result.case,
                result.thickness,
                height,
                *(f"{result.sums[field]:.8E}" for field in fields[3:]),
            )
        )


def write_comparison(path: Path, results: list[CaseResult], heights: dict[str, int]) -> None:
    fields = ["T_cm", "H_cm", *(window[0] for window in WINDOWS)]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        for result in sorted(results, key=lambda item: (item.thickness, heights[item.case])):
            writer.writerow(
                (
                    result.thickness,
                    heights[result.case],
                    *(f"{result.sums[field]:.8E}" for field in fields[2:]),
                )
            )


def pct(current: float, previous: float) -> float:
    return (current - previous) / previous * 100.0 if previous else math.nan


def trend(values: list[float]) -> str:
    changes = [right - left for left, right in zip(values, values[1:])]
    if all(change >= 0 for change in changes):
        return "总体单调增加"
    if all(change <= 0 for change in changes):
        return "总体单调下降"
    peak = max(range(len(values)), key=values.__getitem__)
    if all(change >= 0 for change in changes[:peak]) and all(
        change <= 0 for change in changes[peak:]
    ):
        return "先增加后趋稳或下降"
    return "存在局部波动"


def branch_platform(branch: list[CaseResult], heights: dict[str, int]) -> tuple[int | None, str]:
    branch = sorted(branch, key=lambda item: heights[item.case])
    roi = [item.sums["ROI_6.03_6.23"] for item in branch]
    if len(roi) < 2:
        return None, "样本不足"
    for index in range(len(branch) - 1):
        gains = [pct(roi[j], roi[j - 1]) for j in range(index + 1, len(roi))]
        z_values = []
        for j in range(index + 1, len(branch)):
            sigma = math.hypot(
                branch[j].sigmas["ROI_6.03_6.23"],
                branch[j - 1].sigmas["ROI_6.03_6.23"],
            )
            z_values.append(abs(roi[j] - roi[j - 1]) / sigma if sigma else math.inf)
        if gains and max(gains) <= 2.0 and all(z < 2.0 for z in z_values):
            return heights[branch[index].case], "后续增幅均不超过2%，且相邻差异处于约两倍合成不确定度内"
    return None, "本次H=20–50 cm采样内未建立明确平台"


def choose_recommendation(results: list[CaseResult], heights: dict[str, int]) -> tuple[CaseResult, list[CaseResult]]:
    peak = max(results, key=lambda item: item.sums["ROI_6.03_6.23"])
    near = []
    for result in results:
        sigma = math.hypot(
            result.sigmas["ROI_6.03_6.23"], peak.sigmas["ROI_6.03_6.23"]
        )
        if peak.sums["ROI_6.03_6.23"] - result.sums["ROI_6.03_6.23"] <= 2.0 * sigma:
            near.append(result)
    if not near:
        near = [peak]
    # Among statistically near-maximum cases, prefer the compact geometry:
    # lower CaO thickness first, then shorter H.
    recommendation = min(near, key=lambda item: (item.thickness, heights[item.case]))
    return recommendation, near


def write_conclusion(path: Path, results: list[CaseResult], heights: dict[str, int]) -> None:
    roi_key = "ROI_6.03_6.23"
    left_key = "Left_5.95_6.02"
    right_key = "Right_6.24_6.31"
    by_t = {t: sorted((r for r in results if r.thickness == t), key=lambda r: heights[r.case]) for t in (4, 5)}
    peaks = {t: max(items, key=lambda r: r.sums[roi_key]) for t, items in by_t.items()}
    overall = max(results, key=lambda r: r.sums[roi_key])
    recommendation, near = choose_recommendation(results, heights)
    near_text = "、".join(
        f"T={item.thickness} cm,H={heights[item.case]} cm" for item in near
    )
    tfc_issues = [item for item in results if not item.tfc_passed]
    max_re = max(item.max_roi_re for item in results)
    min_re = min(item.max_roi_re for item in results)

    lines = [
        "# CaO长度优化结果分析",
        "",
        "## 1. 优化条件与数据质量",
        "",
        "本次长度优化固定Rin = 5 cm、探测器距离D = 1 cm，分别考察T=4 cm（Rout=9 cm）"
        "和T=5 cm（Rout=10 cm）两条支线；每条支线扫描H=20、25、30、35、40、45、50 cm。"
        "14组计算均采用NPS=5×10^8、相同材料、探测器、F8和GEB设置。",
        f"14个outp均正常完成并成功提取完整F8谱。主ROI各bin相对误差的案例最大值范围为"
        f"{min_re * 100:.2f}%～{max_re * 100:.2f}%。",
    ]
    if tfc_issues:
        lines.append(
            "TFC诊断需单独说明：" + "；".join(
                f"{item.case}：{item.tfc_note}" for item in tfc_issues
            ) + "。TFC只针对选定波动图bin，不代表所有ROI bin。"
        )
    else:
        lines.append("14组F8波动图bin均通过10项TFC检查；仍需结合各能量bin相对误差判断。")

    for t in (4, 5):
        items = by_t[t]
        roi = [item.sums[roi_key] for item in items]
        left = [item.sums[left_key] for item in items]
        right = [item.sums[right_key] for item in items]
        gains = [pct(roi[i], roi[i - 1]) for i in range(1, len(roi))]
        platform_h, platform_note = branch_platform(items, heights)
        lines.extend(
            [
                "",
                f"## 2. T={t} cm支线",
                "",
                f"H从20 cm增加到50 cm时，主ROI呈{trend(roi)}；"
                f"最大值位于H={heights[peaks[t].case]} cm，为{peaks[t].sums[roi_key]:.8E}。",
                f"相邻H变化的Gross ROI增幅依次为：" + "、".join(f"{value:+.2f}%" for value in gains) + "。",
                f"左侧响应呈{trend(left)}（{left[0]:.8E}→{left[-1]:.8E}），"
                f"右侧响应呈{trend(right)}（{right[0]:.8E}→{right[-1]:.8E}）。",
                f"平台判断：{platform_note}。"
                + (f"可将H≈{platform_h} cm视作本次采样中平台起点。" if platform_h else ""),
            ]
        )

    lines.extend(["", "## 3. T04与T05同长度直接比较", ""])
    t04 = {heights[item.case]: item for item in by_t[4]}
    t05 = {heights[item.case]: item for item in by_t[5]}
    for height in sorted(t04):
        a, b = t04[height], t05[height]
        delta = b.sums[roi_key] - a.sums[roi_key]
        sigma = math.hypot(a.sigmas[roi_key], b.sigmas[roi_key])
        z = abs(delta) / sigma if sigma else math.inf
        winner = "T05更高" if delta > 0 else "T04更高" if delta < 0 else "两者相同"
        lines.append(
            f"H={height} cm：T04={a.sums[roi_key]:.8E}，T05={b.sums[roi_key]:.8E}，"
            f"T05相对T04变化={delta / a.sums[roi_key] * 100:+.2f}%；{winner}，"
            f"z={z:.2f}。"
        )
    lines.extend(
        [
            "",
            "整体上，T04与T05的优势应结合相邻统计不确定度判断；若差值对应的z值较小，"
            "只能表述为数值差异，不能宣称厚度优势已经被统计分辨。",
            "",
            "## 4. 推荐下一阶段距离优化条件",
            "",
            f"14组中Gross ROI最大组合为T={overall.thickness} cm、H={heights[overall.case]} cm，"
            f"响应为{overall.sums[roi_key]:.8E}。与该最大值在两倍合成统计不确定度内接近的组合为：{near_text}。",
            f"综合Gross ROI、相邻H变化、平台情况、左右侧响应，以及在结果接近时优先采用更紧凑、"
            f"CaO用量更少的结构，本次建议采用T={recommendation.thickness} cm、"
            f"H={heights[recommendation.case]} cm；该组合响应为{recommendation.sums[roi_key]:.8E}，"
            f"为14组最大值的{recommendation.sums[roi_key] / overall.sums[roi_key] * 100:.2f}%。",
            "",
            f"因此，后续距离优化建议固定 T = {recommendation.thickness} cm，H = {heights[recommendation.case]} cm。",
            "评价指标始终是6.03–6.23 MeV范围内的F8脉冲高度响应之和，即6.13 MeV峰区Gross ROI响应；"
            "本次未进行本底扣除、平滑、插值或峰形拟合，不将其称为净全能峰效率或LaBr3本征效率。",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def process_case(case_dir: Path) -> tuple[CaseResult, int]:
    thickness, height = parse_case(case_dir)
    outp = case_dir / "结果输出" / "outp"
    if not outp.is_file():
        raise FileNotFoundError(f"{case_dir.name}: missing {outp}")
    text = outp.read_text(encoding="utf-8", errors="replace")
    if re.search(r"(?i)fatal error|bad trouble|unexpected eof", text):
        raise ValueError(f"{case_dir.name}: fatal MCNP marker found in outp")
    nps = extract_nps(text, case_dir.name)
    rows = extract_spectrum(text, case_dir.name)
    tfc_passed, tfc_note = inspect_tfc(text)
    sums: dict[str, float] = {}
    sigmas: dict[str, float] = {}
    max_roi_re = 0.0
    for field, low, high, expected_count in WINDOWS:
        selected = select_window(rows, low, high, expected_count, case_dir.name)
        sums[field] = math.fsum(item.response for item in selected)
        sigmas[field] = math.sqrt(
            math.fsum((item.response * item.relative_error) ** 2 for item in selected)
        )
        if field == "ROI_6.03_6.23":
            max_roi_re = max(item.relative_error for item in selected)
    raw_name = f"T{thickness:02d}_H{height:02d}_F8_raw.csv"
    sum_name = f"T{thickness:02d}_H{height:02d}_sum.csv"
    write_raw(case_dir / "数据处理" / "原始数据" / raw_name, rows)
    result = CaseResult(
        case=case_dir.name,
        thickness=thickness,
        nps=nps,
        sums=sums,
        sigmas=sigmas,
        max_roi_re=max_roi_re,
        tfc_passed=tfc_passed,
        tfc_note=tfc_note,
    )
    write_case_sum(case_dir / "数据处理" / "分析结果" / sum_name, result, height)
    return result, height


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scan_dir",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "长度优化",
    )
    args = parser.parse_args()
    scan_dir = args.scan_dir.resolve()
    if not scan_dir.is_dir():
        parser.error(f"scan directory does not exist: {scan_dir}")
    found = [
        case_dir
        for group in ("T04", "T05")
        for case_dir in sorted((scan_dir / group).iterdir())
        if case_dir.is_dir() and CASE_RE.fullmatch(case_dir.name)
    ]
    found_names = [case_dir.name for case_dir in found]
    missing = sorted(set(EXPECTED) - set(found_names))
    extra = sorted(set(found_names) - set(EXPECTED))
    if missing or extra:
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("unexpected: " + ", ".join(extra))
        raise SystemExit("Case validation failed; " + "; ".join(details))

    results: list[CaseResult] = []
    heights: dict[str, int] = {}
    failures: list[str] = []
    for case_name in EXPECTED:
        group = case_name[:3]
        try:
            result, height = process_case(scan_dir / group / case_name)
            results.append(result)
            heights[result.case] = height
            print(
                f"PASS {case_name}: NPS={result.nps}, "
                f"ROI={result.sums['ROI_6.03_6.23']:.8E}, {result.tfc_note}"
            )
        except (OSError, ValueError) as exc:
            failures.append(str(exc))
            print(f"FAIL {exc}")
    if failures:
        raise SystemExit("Post-processing failed:\n" + "\n".join(failures))

    results.sort(key=lambda item: (item.thickness, heights[item.case]))
    summary_dir = scan_dir / "总结数据"
    comparison = summary_dir / "Length_compare.csv"
    conclusion = summary_dir / "Length_conclusion.md"
    write_comparison(comparison, results, heights)
    write_conclusion(conclusion, results, heights)
    print(f"PASS Length_compare.csv: {comparison}")
    print(f"PASS Length_conclusion.md: {conclusion}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
