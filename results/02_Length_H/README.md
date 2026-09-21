# Length H Optimization

## 研究目的

研究 CaO 长度 H 对 6.13 MeV 氧峰区响应的影响。

## 模拟条件

- 自变量：`H=20,25,30,35,40,45,50 cm`
- 两条支线：`T=4 cm, Rout=9 cm` 与 `T=5 cm, Rout=10 cm`
- 固定参数：`Rin=5 cm`、`D=1 cm`
- 中子源：14.1 MeV、Phi10 mm 圆盘源
- NPS：`5E8`
- 历史扫描探测器：直径 5.08 cm、长度 5.08 cm 的 LaBr3 晶体及 Al 外壳

## 评价指标与结论

现有数据是 `6.03-6.23 MeV` 的 Gross ROI，不是净峰面积。两条支线均随 H 增大而增加并逐渐进入平台；数值最大值位于 H50。既有报告基于紧凑性与平台判断建议 `T=4 cm, H=30 cm` 进入距离优化。

当前项目主线采用 `T=4 cm, H=25 cm, D=1 cm`。这是与历史报告不同的工程选择，本目录只记录差异，不修改既有结论。

- 数据：`processed/T04_T05_H20_H25_H30_H35_H40_H45_H50_compare_6p13GrossROI.csv`
- 说明：`notes/T04_T05_H20_to_H50_6p13GrossROI_conclusion.md`
- 图：当前未归档

## Case 追踪表

| Case | Input | Output | T | H | D | NPS | Status |
|---|---|---|---:|---:|---:|---:|---|
| `T04_H20_D01` | `inputs/T04/T04_H20_D01.i` | `outputs/T04_H20_D01.outp` | 4 | 20 | 1 | 500000000 | Complete |
| `T04_H25_D01` | `inputs/T04/T04_H25_D01.i` | `outputs/T04_H25_D01.outp` | 4 | 25 | 1 | 500000000 | Complete |
| `T04_H30_D01` | `inputs/T04/T04_H30_D01.i` | `outputs/T04_H30_D01.outp` | 4 | 30 | 1 | 500000000 | Complete |
| `T04_H35_D01` | `inputs/T04/T04_H35_D01.i` | `outputs/T04_H35_D01.outp` | 4 | 35 | 1 | 500000000 | Complete |
| `T04_H40_D01` | `inputs/T04/T04_H40_D01.i` | `outputs/T04_H40_D01.outp` | 4 | 40 | 1 | 500000000 | Complete |
| `T04_H45_D01` | `inputs/T04/T04_H45_D01.i` | `outputs/T04_H45_D01.outp` | 4 | 45 | 1 | 500000000 | Complete |
| `T04_H50_D01` | `inputs/T04/T04_H50_D01.i` | `outputs/T04_H50_D01.outp` | 4 | 50 | 1 | 500000000 | Complete |
| `T05_H20_D01` | `inputs/T05/T05_H20_D01.i` | `outputs/T05_H20_D01.outp` | 5 | 20 | 1 | 500000000 | Complete |
| `T05_H25_D01` | `inputs/T05/T05_H25_D01.i` | `outputs/T05_H25_D01.outp` | 5 | 25 | 1 | 500000000 | Complete |
| `T05_H30_D01` | `inputs/T05/T05_H30_D01.i` | `outputs/T05_H30_D01.outp` | 5 | 30 | 1 | 500000000 | Complete |
| `T05_H35_D01` | `inputs/T05/T05_H35_D01.i` | `outputs/T05_H35_D01.outp` | 5 | 35 | 1 | 500000000 | Complete |
| `T05_H40_D01` | `inputs/T05/T05_H40_D01.i` | `outputs/T05_H40_D01.outp` | 5 | 40 | 1 | 500000000 | Complete |
| `T05_H45_D01` | `inputs/T05/T05_H45_D01.i` | `outputs/T05_H45_D01.outp` | 5 | 45 | 1 | 500000000 | Complete |
| `T05_H50_D01` | `inputs/T05/T05_H50_D01.i` | `outputs/T05_H50_D01.outp` | 5 | 50 | 1 | 500000000 | Complete |
