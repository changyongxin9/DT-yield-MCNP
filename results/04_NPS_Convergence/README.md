# NPS Convergence

## 研究目的

验证 Monte Carlo 结果随粒子历史数增加的稳定性，不以单个 6.13 MeV bin 代替谱区收敛性判断。

## 比较条件

- 几何：`T04_H25_D01` 与 `T05_H25_D01`
- NPS：`1E8, 3E8, 5E8, 7E8, 1E9`
- 源：14.1 MeV、Phi10 mm 圆盘源
- 历史最终计数输入使用 5.08 cm x 5.08 cm LaBr3 + Al 模型

## 评价内容

- F8 谱和总响应
- `6.03-6.23 MeV` Gross ROI
- 各 bin 相对误差 R
- Gross ROI 随 NPS 的稳定性

现有结果显示 5E8 与 7E8、1E9 的 Gross ROI 差异较小。T04 五档 TFC 均通过；T05 的 7E8 和 1E9 存在 TFC 未全部通过的提示，解读时需保守。

- `processed/T04_NPS_1E8_3E8_5E8_7E8_1E9_compare_6p13GrossROI.csv`
- `processed/T05_NPS_1E8_3E8_5E8_7E8_1E9_compare_6p13GrossROI.csv`
- `processed/T04_vs_T05_NPS_1E8_3E8_5E8_7E8_1E9_6p13GrossROI.csv`

第三个文件同时比较相同 NPS 下 T04 与 T05 的左侧、Gross ROI 和右侧响应，因此归入本目录，而不是作为单独的净峰结论。

## Case 追踪表

| Case | Input | Output | T | H | D | NPS | Status |
|---|---|---|---:|---:|---:|---:|---|
| `T04_H25_D01_NPS1E8` | `inputs/T04_H25_D01_NPS1E8.i` | `outputs/T04_H25_D01_NPS1E8.outp` | 4 | 25 | 1 | 100000000 | Complete |
| `T04_H25_D01_NPS3E8` | `inputs/T04_H25_D01_NPS3E8.i` | `outputs/T04_H25_D01_NPS3E8.outp` | 4 | 25 | 1 | 300000000 | Complete |
| `T04_H25_D01_NPS5E8` | `inputs/T04_H25_D01_NPS5E8.i` | `outputs/T04_H25_D01_NPS5E8.outp` | 4 | 25 | 1 | 500000000 | Complete |
| `T04_H25_D01_NPS7E8` | `inputs/T04_H25_D01_NPS7E8.i` | `outputs/T04_H25_D01_NPS7E8.outp` | 4 | 25 | 1 | 700000000 | Complete |
| `T04_H25_D01_NPS1E9` | `inputs/T04_H25_D01_NPS1E9.i` | `outputs/T04_H25_D01_NPS1E9.outp` | 4 | 25 | 1 | 1000000000 | Complete |
| `T05_H25_D01_NPS1E8` | `inputs/T05_H25_D01_NPS1E8.i` | `outputs/T05_H25_D01_NPS1E8.outp` | 5 | 25 | 1 | 100000000 | Complete |
| `T05_H25_D01_NPS3E8` | `inputs/T05_H25_D01_NPS3E8.i` | `outputs/T05_H25_D01_NPS3E8.outp` | 5 | 25 | 1 | 300000000 | Complete |
| `T05_H25_D01_NPS5E8` | `inputs/T05_H25_D01_NPS5E8.i` | `outputs/T05_H25_D01_NPS5E8.outp` | 5 | 25 | 1 | 500000000 | Complete |
| `T05_H25_D01_NPS7E8` | `inputs/T05_H25_D01_NPS7E8.i` | `outputs/T05_H25_D01_NPS7E8.outp` | 5 | 25 | 1 | 700000000 | Complete |
| `T05_H25_D01_NPS1E9` | `inputs/T05_H25_D01_NPS1E9.i` | `outputs/T05_H25_D01_NPS1E9.outp` | 5 | 25 | 1 | 1000000000 | Complete |
