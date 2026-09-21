from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import watts

ALLOWED_CATEGORIES = {"厚度优化", "长度优化", "距离优化", "总对比"}
NUMERIC_FIELDS = ("Rin", "Rout", "H", "d")


def parse_scalar(value: str):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def read_params(path: Path) -> dict:
    """Read the deliberately small YAML subset used by params.yaml."""
    config: dict = {"cases": []}
    current_case: dict | None = None

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        content = raw_line.split("#", 1)[0].rstrip()
        if not content.strip():
            continue

        stripped = content.strip()
        if stripped == "cases:":
            continue
        if stripped.startswith("- "):
            current_case = {}
            config["cases"].append(current_case)
            stripped = stripped[2:].strip()
            if not stripped:
                continue

        if ":" not in stripped:
            raise ValueError(f"Invalid params.yaml line {line_number}: {raw_line}")

        key, value = (part.strip() for part in stripped.split(":", 1))
        target = current_case if current_case is not None else config
        target[key] = parse_scalar(value)

    if not config["cases"]:
        raise ValueError("params.yaml does not define any cases")
    return config


def format_number(value: float) -> str:
    if abs(value) < 5e-13:
        value = 0.0
    return f"{value:.12g}"


def integer_code(value: float, label: str) -> str:
    rounded = round(value)
    if not math.isclose(value, rounded, abs_tol=1e-9):
        raise ValueError(f"{label}={value} cannot use the integer-centimetre naming rule")
    if rounded < 0 or rounded > 99:
        raise ValueError(f"{label}={value} is outside the T/H/D two-digit naming range")
    return f"{rounded:02d}"


def validate_case(case: dict) -> tuple[dict[str, float], float]:
    missing = [field for field in ("case", "category", *NUMERIC_FIELDS) if field not in case]
    if missing:
        raise ValueError(f"Missing case fields: {', '.join(missing)}")
    if case["category"] not in ALLOWED_CATEGORIES:
        raise ValueError(f"Unsupported category: {case['category']}")

    values = {field: float(case[field]) for field in NUMERIC_FIELDS}
    if not all(math.isfinite(value) for value in values.values()):
        raise ValueError(f"Case {case['case']} contains a non-finite parameter")

    rin, rout, height, distance = (
        values["Rin"],
        values["Rout"],
        values["H"],
        values["d"],
    )
    if rin <= 1.95:
        raise ValueError("Rin must be greater than the 1.95 cm source-region radius")
    if rout <= rin:
        raise ValueError("Rout must be greater than Rin")
    if height < 18.0:
        raise ValueError("H must not cut through the fixed 18 cm source-region height")
    if distance < 0.2:
        raise ValueError("d must be at least 0.2 cm to preserve the housing relationship")

    thickness = rout - rin
    expected_name = (
        f"T{integer_code(thickness, 'T')}_"
        f"H{integer_code(height, 'H')}_"
        f"D{integer_code(distance, 'D')}"
    )
    if case["case"] != expected_name:
        raise ValueError(
            f"Case name {case['case']} does not match parameters; expected {expected_name}"
        )
    return values, thickness


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    parser = argparse.ArgumentParser(description="Generate MCNP inputs from WATTS parameters")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("params.yaml"),
        help="parameter YAML file, relative to the WATTS template directory",
    )
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else script_dir / args.config
    config = read_params(config_path)
    template_path = script_dir / str(config.get("template", "template.i"))
    parameter_csv = (script_dir / str(config.get("parameter_csv", "../parameter.csv"))).resolve()
    renderer = watts.TemplateRenderer(template_path)
    rows = []
    if config.get("parameter_schema") == "dimensional":
        parameter_fields = ["Case", "T_cm", "H_cm", "D_cm", "Rin_cm", "Rout_cm"]
    else:
        parameter_fields = ["case", "T", "H", "D", "Rin", "Rout"]

    for case in config["cases"]:
        values, thickness = validate_case(case)
        case_name = str(case["case"])
        case_dir = project_dir / str(case["category"])
        group = case.get("group")
        if group:
            case_dir /= str(group)
        case_dir /= case_name
        input_dir = case_dir / "代码输入"
        for directory in (
            input_dir,
            case_dir / "结果输出",
            case_dir / "数据处理" / "原始数据",
            case_dir / "数据处理" / "分析结果",
            case_dir / "Origin",
        ):
            directory.mkdir(parents=True, exist_ok=True)

        output_path = input_dir / f"{case_name}.i"
        renderer(watts.Parameters(values), filename=output_path)
        rendered = output_path.read_text(encoding="utf-8")
        if "{{" in rendered or "}}" in rendered:
            raise ValueError(f"Unresolved template placeholder remains in {output_path}")
        if not rendered.endswith("\n"):
            output_path.write_text(rendered + "\n", encoding="utf-8", newline="\n")
        metadata = {
            "case": case_name,
            "Case": case_name,
            "T": format_number(thickness),
            "T_cm": format_number(thickness),
            "H": format_number(values["H"]),
            "H_cm": format_number(values["H"]),
            "D": format_number(values["d"]),
            "D_cm": format_number(values["d"]),
            "Rin": format_number(values["Rin"]),
            "Rin_cm": format_number(values["Rin"]),
            "Rout": format_number(values["Rout"]),
            "Rout_cm": format_number(values["Rout"]),
        }
        rows.append({field: metadata.get(field, "") for field in parameter_fields})
        print(f"Generated: {output_path}")

    parameter_csv.parent.mkdir(parents=True, exist_ok=True)
    with parameter_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=parameter_fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated: {parameter_csv}")


if __name__ == "__main__":
    main()
