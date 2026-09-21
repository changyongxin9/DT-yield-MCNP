#!/usr/bin/env python3
"""Post-process completed MCNP F8 parameter scans without running MCNP.

The existing WATTS/Jinja workflow owns parameter metadata, case naming and
input generation. This script covers the missing MCNP outp-specific tasks:
extract tally 8, sum fixed energy windows and build a scan comparison/report.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from dataclasses import dataclass
from pathlib import Path


NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"
DATA_RE = re.compile(rf"^\s*({NUMBER})\s+({NUMBER})\s+({NUMBER})\s*$")
TALLY_RE = re.compile(r"^\s*1tally\s+8\b", re.IGNORECASE)
CASE_RE = re.compile(r"^T(?P<T>\d+)_H(?P<H>\d+)_D(?P<D>\d+)$")

EXPECTED_ENERGIES = 1601
ENERGY_MIN = 0.0
ENERGY_MAX = 16.0
ENERGY_STEP = 0.01
WINDOWS = (
    ("Left_5.95_6.02", 5.95, 6.02, 8),
    ("ROI_6.03_6.23", 6.03, 6.23, 21),
    ("Right_6.24_6.31", 6.24, 6.31, 8),
)


@dataclass(frozen=True)
class SpectrumRow:
    energy: float
    response: float
    relative_error: float


@dataclass
class CaseResult:
    case: str
    thickness: int
    nps: int
    sums: dict[str, float]
    sigmas: dict[str, float]
    max_roi_re: float
    tfc_passed: bool
    tfc_note: str


def to_float(value: str) -> float:
    return float(value.replace("D", "E").replace("d", "e"))


def extract_nps(text: str, case: str) -> int:
    match = re.search(r"(?im)^\s*1tally\s+8\s+nps\s*=\s*(\d+)", text)
    if not match:
        raise ValueError(f"{case}: tally 8 NPS was not found")
    nps = int(match.group(1))
    completion = re.search(
        rf"(?i)run terminated when\s+{nps}\s+particle histories were done", text
    )
    if not completion:
        raise ValueError(f"{case}: completed-history line for NPS={nps} was not found")
    return nps


def extract_spectrum(text: str, case: str) -> list[SpectrumRow]:
    lines = text.splitlines()
    tally_index = next((i for i, line in enumerate(lines) if TALLY_RE.match(line)), None)
    if tally_index is None:
        raise ValueError(f"{case}: 1tally 8 was not found")

    descriptor = "\n".join(lines[tally_index : tally_index + 8]).lower()
    if "tally type 8" not in descriptor or "pulse height distribution" not in descriptor:
        raise ValueError(f"{case}: tally 8 is not identified as a pulse-height tally")
    if "photons" not in descriptor:
        raise ValueError(f"{case}: tally 8 is not identified as a photon tally")

    energy_index = next(
        (
            i
            for i in range(tally_index + 1, min(tally_index + 20, len(lines)))
            if lines[i].strip().lower() == "energy"
        ),
        None,
    )
    if energy_index is None:
        raise ValueError(f"{case}: tally 8 energy header was not found")

    rows: list[SpectrumRow] = []
    for line in lines[energy_index + 1 :]:
        if line.strip().lower().startswith("total"):
            break
        match = DATA_RE.match(line)
        if not match:
            continue
        values = tuple(to_float(group) for group in match.groups())
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"{case}: NaN or infinite tally value was found")
        energy, response, relative_error = values
        if response < 0 or relative_error < 0:
            raise ValueError(f"{case}: negative F8 response or relative error was found")
        rows.append(SpectrumRow(energy, response, relative_error))

    if len(rows) != EXPECTED_ENERGIES:
        raise ValueError(
            f"{case}: expected {EXPECTED_ENERGIES} F8 energy rows, found {len(rows)}"
        )
    for index, row in enumerate(rows):
        expected = ENERGY_MIN + index * ENERGY_STEP
        if not math.isclose(row.energy, expected, abs_tol=5e-7):
            raise ValueError(
                f"{case}: energy grid mismatch at row {index + 1}: "
                f"expected {expected:.2f}, found {row.energy:.8g}"
            )
    if not math.isclose(rows[-1].energy, ENERGY_MAX, abs_tol=5e-7):
        raise ValueError(f"{case}: F8 spectrum does not end at 16 MeV")
    return rows


def inspect_tfc(text: str) -> tuple[bool, str]:
    if re.search(r"(?i)passed the 10 statistical checks", text):
        return True, "F8 TFC bin passed all 10 statistical checks"
    missed = re.search(r"(?im)^\s*8\s+missed\s+(.+)$", text)
    if missed:
        return False, "F8 TFC bin " + " ".join(missed.group(1).split())
    return False, "F8 TFC status was not found"


def select_window(
    rows: list[SpectrumRow], low: float, high: float, expected_count: int, case: str
) -> list[SpectrumRow]:
    selected = [
        row
        for row in rows
        if row.energy >= low - 5e-7 and row.energy <= high + 5e-7
    ]
    if len(selected) != expected_count:
        raise ValueError(
            f"{case}: {low:.2f}-{high:.2f} MeV expected {expected_count} bins, "
            f"found {len(selected)}"
        )
    return selected


def write_raw(path: Path, rows: list[SpectrumRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(("Energy_MeV", "F8_Response", "Relative_Error"))
        writer.writerows(
            (f"{row.energy:.4f}", f"{row.response:.8E}", f"{row.relative_error:.6g}")
            for row in rows
        )


def write_case_sum(path: Path, result: CaseResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["Case", "T_cm", *(window[0] for window in WINDOWS)]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        writer.writerow(
            (
                result.case,
                result.thickness,
                *(f"{result.sums[field]:.8E}" for field in fields[2:]),
            )
        )


def write_comparison(path: Path, results: list[CaseResult]) -> None:
    fields = ["T_cm", *(window[0] for window in WINDOWS)]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        for result in results:
            writer.writerow(
                (
                    result.thickness,
                    *(f"{result.sums[field]:.8E}" for field in fields[1:]),
                )
            )


def percent_change(current: float, previous: float) -> float:
    return (current - previous) / previous * 100.0 if previous else math.nan


def classify_trend(values: list[float]) -> str:
    changes = [right - left for left, right in zip(values, values[1:])]
    if all(change >= 0 for change in changes):
        return "总体单调增加"
    peak = max(range(len(values)), key=values.__getitem__)
    if all(change >= 0 for change in changes[:peak]) and all(
        change <= 0 for change in changes[peak:]
    ):
        return "先增加后下降"
    return "存在局部波动"


def choose_recommendation(results: list[CaseResult]) -> tuple[CaseResult, list[CaseResult]]:
    roi_key = "ROI_6.03_6.23"
    peak = max(results, key=lambda result: result.sums[roi_key])
    near_peak = []
    for result in results:
        combined_sigma = math.hypot(result.sigmas[roi_key], peak.sigmas[roi_key])
        if peak.sums[roi_key] - result.sums[roi_key] <= 2.0 * combined_sigma:
            near_peak.append(result)

    # Prefer the first statistically near-maximum point. If that region is a
    # single late point, use the first point reaching 95% of the sampled peak
    # once subsequent gains have already fallen below 2%.
    if len(near_peak) >= 2:
        return min(near_peak, key=lambda result: result.thickness), near_peak
    threshold = 0.95 * peak.sums[roi_key]
    for index, result in enumerate(results):
        later_gains = [
            percent_change(results[j].sums[roi_key], results[j - 1].sums[roi_key])
            for j in range(index + 1, len(results))
        ]
        if result.sums[roi_key] >= threshold and later_gains and max(later_gains) <= 2.0:
            return result, near_peak
    return peak, near_peak


def write_conclusion(path: Path, results: list[CaseResult]) -> tuple[int, int]:
    roi_key = "ROI_6.03_6.23"
    left_key = "Left_5.95_6.02"
    right_key = "Right_6.24_6.31"
    peak = max(results, key=lambda result: result.sums[roi_key])
    recommended, near_peak = choose_recommendation(results)
    roi_values = [result.sums[roi_key] for result in results]
    left_values = [result.sums[left_key] for result in results]
    right_values = [result.sums[right_key] for result in results]
    gains = [
        percent_change(results[index].sums[roi_key], results[index - 1].sums[roi_key])
        for index in range(1, len(results))
    ]
    last_gains = gains[-3:]
    tfc_issues = [result for result in results if not result.tfc_passed]
    re_min = min(result.max_roi_re for result in results)
    re_max = max(result.max_roi_re for result in results)
    near_text = "、".join(f"T={result.thickness} cm" for result in near_peak) or "无其他厚度"

    lines = [
        "# CaO厚度优化结果分析",
        "",
        "## 1. 厚度优化条件",
        "",
        "本组计算固定CaO内半径 Rin = 5 cm、装置高度 H = 25 cm、探测器距离 D = 1 cm，"
        "扫描CaO厚度 T = 1～10 cm，对应外半径 Rout = 6～15 cm。各模型采用相同的"
        "材料、探测器、F8脉冲高度计数和GEB设置，计算规模均为 NPS = 5×10^8。",
        "",
        "## 2. 评价指标",
        "",
        "主评价指标为6.03～6.23 MeV范围内各能量bin的F8响应直接求和，即6.13 MeV峰区"
        "Gross ROI响应。辅助指标为5.95～6.02 MeV左侧响应和6.24～6.31 MeV右侧响应。"
        "三段能区相互独立，未实施本底扣除、平滑、插值或峰形拟合。",
        "",
        "## 3. 数据质量与结果趋势",
        "",
        f"10组输出均正常完成5×10^8个粒子历史并包含完整F8:P tally。主ROI各bin相对误差"
        f"的案例最大值范围为{re_min * 100:.2f}%～{re_max * 100:.2f}%。",
    ]
    if tfc_issues:
        issue_text = "；".join(
            f"{result.case}：{result.tfc_note}" for result in tfc_issues
        )
        lines.append(
            f"统计诊断中需注意：{issue_text}。TFC检查只针对MCNP选定的波动图bin，"
            "并不代表主ROI内每个能量bin的统计状态，因此本报告同时保留并核对了各bin的相对误差。"
        )
    else:
        lines.append(
            "所有案例的F8波动图bin均通过10项TFC检查；该检查不等同于主ROI内每个bin均通过，"
            "因此仍应结合各bin相对误差理解趋势。"
        )
    lines.extend(
        [
            "",
            f"主ROI随厚度变化呈{classify_trend(roi_values)}。从T=1 cm到T=10 cm，"
            f"Gross ROI响应由{roi_values[0]:.8E}变化至{roi_values[-1]:.8E}。"
            f"最后三个相邻厚度增幅分别为{last_gains[0]:+.2f}%、{last_gains[1]:+.2f}%和"
            f"{last_gains[2]:+.2f}%，用于判断高厚度区是否出现收益递减。",
            f"左侧响应呈{classify_trend(left_values)}，由{left_values[0]:.8E}变化至"
            f"{left_values[-1]:.8E}；右侧响应呈{classify_trend(right_values)}，由"
            f"{right_values[0]:.8E}变化至{right_values[-1]:.8E}。这些辅助区仅用于观察"
            "峰区邻近响应变化，不作为本底估计。",
            "",
            "## 4. 数值最大厚度",
            "",
            f"在当前1～10 cm离散扫描范围内，6.03～6.23 MeV Gross ROI响应最大值出现在"
            f"T = {peak.thickness} cm，对应响应为{peak.sums[roi_key]:.8E}。该结论是当前"
            "采样范围内的数值最大值，不外推为扫描范围之外的全局最优。",
            "",
            "## 5. 后续长度优化的厚度建议",
            "",
            f"以两倍合成统计不确定度判断，与峰值统计上接近的厚度区域为：{near_text}。"
            f"综合主ROI响应、相邻厚度增幅、左右侧响应及装置紧凑性，建议采用"
            f"T = {recommended.thickness} cm进入后续长度优化；该点的Gross ROI响应为"
            f"{recommended.sums[roi_key]:.8E}，达到本次扫描最大值的"
            f"{recommended.sums[roi_key] / peak.sums[roi_key] * 100:.2f}%。",
            "",
            f"因此，后续长度优化建议固定CaO厚度为 T = {recommended.thickness} cm。",
            "",
            "需要强调的是，上述量为6.03～6.23 MeV范围内的F8脉冲高度响应之和，"
            "不等同于净全能峰效率或LaBr3本征效率。",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return peak.thickness, recommended.thickness


def process_case(case_dir: Path) -> CaseResult:
    case_match = CASE_RE.fullmatch(case_dir.name)
    if not case_match:
        raise ValueError(f"{case_dir.name}: case name does not match Txx_Hxx_Dxx")
    thickness = int(case_match.group("T"))
    outp = case_dir / "结果输出" / "outp"
    if not outp.is_file():
        raise FileNotFoundError(f"{case_dir.name}: missing result file {outp}")
    text = outp.read_text(encoding="utf-8", errors="replace")
    if re.search(r"(?i)fatal error|bad trouble|unexpected eof", text):
        raise ValueError(f"{case_dir.name}: fatal MCNP marker found in outp")
    nps = extract_nps(text, case_dir.name)
    rows = extract_spectrum(text, case_dir.name)
    tfc_passed, tfc_note = inspect_tfc(text)

    sums: dict[str, float] = {}
    sigmas: dict[str, float] = {}
    roi_relative_errors: list[float] = []
    for field, low, high, expected_count in WINDOWS:
        selected = select_window(rows, low, high, expected_count, case_dir.name)
        sums[field] = math.fsum(row.response for row in selected)
        sigmas[field] = math.sqrt(
            math.fsum((row.response * row.relative_error) ** 2 for row in selected)
        )
        if field == "ROI_6.03_6.23":
            roi_relative_errors = [row.relative_error for row in selected]

    prefix = f"T{thickness:02d}"
    write_raw(case_dir / "数据处理" / "原始数据" / f"{prefix}_F8_raw.csv", rows)
    result = CaseResult(
        case=case_dir.name,
        thickness=thickness,
        nps=nps,
        sums=sums,
        sigmas=sigmas,
        max_roi_re=max(roi_relative_errors),
        tfc_passed=tfc_passed,
        tfc_note=tfc_note,
    )
    write_case_sum(case_dir / "数据处理" / "分析结果" / f"{prefix}_sum.csv", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scan_dir",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "厚度优化",
        help="scan directory containing Txx_Hxx_Dxx cases",
    )
    args = parser.parse_args()
    scan_dir = args.scan_dir.resolve()
    if not scan_dir.is_dir():
        parser.error(f"scan directory does not exist: {scan_dir}")

    expected = [f"T{value:02d}_H25_D01" for value in range(1, 11)]
    found = sorted(
        path.name for path in scan_dir.iterdir() if path.is_dir() and CASE_RE.fullmatch(path.name)
    )
    missing = sorted(set(expected) - set(found))
    extra = sorted(set(found) - set(expected))
    if missing or extra:
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("unexpected: " + ", ".join(extra))
        raise SystemExit("Case validation failed; " + "; ".join(details))

    results: list[CaseResult] = []
    failures: list[str] = []
    for case_name in expected:
        try:
            result = process_case(scan_dir / case_name)
            results.append(result)
            print(
                f"PASS {case_name}: NPS={result.nps}, "
                f"ROI={result.sums['ROI_6.03_6.23']:.8E}, {result.tfc_note}"
            )
        except (OSError, ValueError) as exc:
            failures.append(str(exc))
            print(f"FAIL {exc}")
    if failures:
        raise SystemExit("Post-processing failed:\n" + "\n".join(failures))

    results.sort(key=lambda result: result.thickness)
    summary_dir = scan_dir / "总结数据"
    comparison = summary_dir / "Thickness_compare.csv"
    conclusion = summary_dir / "Thickness_conclusion.md"
    write_comparison(comparison, results)
    peak_t, recommended_t = write_conclusion(conclusion, results)
    print(f"PASS Thickness_compare.csv: {comparison}")
    print(f"PASS Thickness_conclusion.md: {conclusion}")
    print(f"Peak thickness: T={peak_t} cm")
    print(f"Recommended thickness: T={recommended_t} cm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
