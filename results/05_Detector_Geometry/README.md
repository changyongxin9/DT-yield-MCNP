# Detector Geometry Comparison

## 研究内容

规划比较早期探测器模型与 D50H75 LaBr3 + PTFE + Al 封装模型对 6.13 MeV ROI 净峰面积的影响。

当前 D50H75 几何定义为：

- LaBr3：直径 50 mm，长度 75 mm
- PTFE：模型中径向及前后方向厚度 1 mm
- Al：模型中位于 PTFE 外侧，径向及前后方向厚度 1 mm

PTFE 和 Al 的 1 mm 厚度均为 **simulation assumption**，不是 manufacturer specification。

本目录目前没有归档正式探测器对比 CSV 或图。此前的 `A5075.i` 和 `D5075.i` 已由用户主动从项目中删除，因此不恢复输入。两份对应历史输出已保留在 `outputs/`，inventory 中标记为 `input intentionally removed by user`。其中 A5075 输出标题写 5E7，但实际 NPS 为 1E8，不能按标题误标。后续数据必须使用固定的 6.13 MeV ROI 净峰面积评价，不能只比较整个 5-7 MeV 谱区。

## Case 追踪表

| Case | Input | Output | T | H | D | NPS | Status |
|---|---|---|---:|---:|---:|---:|---|
| `D50H75_PTFE_Al_A5075_NPS1E8` | - | `outputs/D50H75_PTFE_Al_A5075_NPS1E8.outp` | 4 | 25 | 1 | 100000000 | Missing input (intentionally removed) |
| `D50H75_PTFE_Al_D5075_NPS5E8` | - | `outputs/D50H75_PTFE_Al_D5075_NPS5E8.outp` | 4 | 25 | 1 | 500000000 | Missing input (intentionally removed) |
