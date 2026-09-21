# Detector Distance D Optimization

## 距离定义

`D` 是 **CaO 外表面到 LaBr3 晶体前表面的距离**，不是 CaO 到 Al 外壳前表面的距离。

在当前 D50H75 + PTFE + Al 几何定义中，当 `D=1 cm` 时：

- LaBr3 晶体前表面距 CaO：`1.0 cm`
- PTFE 前表面距 CaO：`0.9 cm`（当前模拟假设）
- Al 外壳前表面距 CaO：`0.8 cm`（当前模拟假设）

上述 1 mm PTFE 和 1 mm Al 层是 simulation assumption，不是 manufacturer specification。

## 历史扫描条件

- 自变量：`D=1,2,3,4 cm`
- 支线：`T=4 cm` 与 `T=5 cm`
- 固定：`H=25 cm`、`Rin=5 cm`
- 源：14.1 MeV、Phi10 mm 圆盘源
- NPS：`5E8`
- 扫描输入使用早期 5.08 cm x 5.08 cm LaBr3 + Al 探测器模型

现有评价指标为 6.13 MeV 峰区 Gross ROI。两条支线均随 D 增加而下降，当前最终采用 `D=1 cm`。

- 数据：`processed/T04_T05_D01_D02_D03_D04_compare_6p13GrossROI.csv`
- 说明：`notes/T04_T05_D01_to_D04_6p13GrossROI_conclusion.md`
- 图：当前未归档

## Case 追踪表

| Case | Input | Output | T | H | D | NPS | Status |
|---|---|---|---:|---:|---:|---:|---|
| `T04_H25_D01` | `inputs/T04_H25/T04_H25_D01.i` | `outputs/T04_H25_D01.outp` | 4 | 25 | 1 | 500000000 | Complete |
| `T04_H25_D02` | `inputs/T04_H25/T04_H25_D02.i` | `outputs/T04_H25_D02.outp` | 4 | 25 | 2 | 500000000 | Complete |
| `T04_H25_D03` | `inputs/T04_H25/T04_H25_D03.i` | `outputs/T04_H25_D03.outp` | 4 | 25 | 3 | 500000000 | Complete |
| `T04_H25_D04` | `inputs/T04_H25/T04_H25_D04.i` | `outputs/T04_H25_D04.outp` | 4 | 25 | 4 | 500000000 | Complete |
| `T05_H25_D01` | `inputs/T05_H25/T05_H25_D01.i` | `outputs/T05_H25_D01.outp` | 5 | 25 | 1 | 500000000 | Complete |
| `T05_H25_D02` | `inputs/T05_H25/T05_H25_D02.i` | `outputs/T05_H25_D02.outp` | 5 | 25 | 2 | 500000000 | Complete |
| `T05_H25_D03` | `inputs/T05_H25/T05_H25_D03.i` | `outputs/T05_H25_D03.outp` | 5 | 25 | 3 | 500000000 | Complete |
| `T05_H25_D04` | `inputs/T05_H25/T05_H25_D04.i` | `outputs/T05_H25_D04.outp` | 5 | 25 | 4 | 500000000 | Complete |
