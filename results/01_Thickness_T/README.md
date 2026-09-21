# Thickness T Optimization

## 研究目的

研究 CaO 转换层厚度 `T = Rout - Rin` 对 6.13 MeV 氧峰区响应的影响。

## 模拟条件

- 自变量：`T = 1, 2, ..., 10 cm`
- 固定参数：`Rin=5 cm`、`H=25 cm`、`D=1 cm`
- 中子源：14.1 MeV、Phi10 mm 圆盘源
- NPS：`5E8`
- 历史扫描探测器：输入卡中为直径 5.08 cm、长度 5.08 cm 的 LaBr3 晶体及 Al 外壳，不是当前 D50H75 + PTFE + Al 模型
- GEB：`0.01723 0.02424 0`

## 评价指标

当前表格使用 `6.03-6.23 MeV` 的 21 个 F8 bin 直接求和，即 **6.13 MeV 峰区 Gross ROI 响应**。没有本底扣除，因此不是净峰面积。

## 当前结果

历史数据的数值最大值位于 `T=4 cm`，T4 与 T5 在两倍合成统计不确定度内接近。既有报告选择 `T=4 cm` 进入下一阶段。

- 数据：`processed/T01_T02_T03_T04_T05_T06_T07_T08_T09_T10_compare_6p13GrossROI.csv`
- 说明：`notes/T01_to_T10_6p13GrossROI_conclusion.md`
- 图：当前未归档

论文最终比较需在固定 ROI 确定后改用净峰面积，不能直接把本目录 Gross ROI 改名为净峰结果。

## Case 追踪表

| Case | Input | Output | T | H | D | NPS | Status |
|---|---|---|---:|---:|---:|---:|---|
| `T01_H25_D01` | `inputs/T01_H25_D01.i` | `outputs/T01_H25_D01.outp` | 1 | 25 | 1 | 500000000 | Complete |
| `T02_H25_D01` | `inputs/T02_H25_D01.i` | `outputs/T02_H25_D01.outp` | 2 | 25 | 1 | 500000000 | Complete |
| `T03_H25_D01` | `inputs/T03_H25_D01.i` | `outputs/T03_H25_D01.outp` | 3 | 25 | 1 | 500000000 | Complete |
| `T04_H25_D01` | `inputs/T04_H25_D01.i` | `outputs/T04_H25_D01.outp` | 4 | 25 | 1 | 500000000 | Complete |
| `T05_H25_D01` | `inputs/T05_H25_D01.i` | `outputs/T05_H25_D01.outp` | 5 | 25 | 1 | 500000000 | Complete |
| `T06_H25_D01` | `inputs/T06_H25_D01.i` | `outputs/T06_H25_D01.outp` | 6 | 25 | 1 | 500000000 | Complete |
| `T07_H25_D01` | `inputs/T07_H25_D01.i` | `outputs/T07_H25_D01.outp` | 7 | 25 | 1 | 500000000 | Complete |
| `T08_H25_D01` | `inputs/T08_H25_D01.i` | `outputs/T08_H25_D01.outp` | 8 | 25 | 1 | 500000000 | Complete |
| `T09_H25_D01` | `inputs/T09_H25_D01.i` | `outputs/T09_H25_D01.outp` | 9 | 25 | 1 | 500000000 | Complete |
| `T10_H25_D01` | `inputs/T10_H25_D01.i` | `outputs/T10_H25_D01.outp` | 10 | 25 | 1 | 500000000 | Complete |
