# D-T 中子源产额与氧 6.13 MeV 特征峰 MCNP 项目

本项目研究 14.1 MeV D-T 中子照射 CaO 后产生的氧特征 gamma 射线，并利用 LaBr3 探测器记录的 6.13 MeV 峰建立后续中子源产额定量关系。源模型为直径 10 mm 的圆盘源，GEB 参数固定为 `FT8 GEB 0.01723 0.02424 0`。

## 两代探测器数据

### Generation 1: Legacy Detector

[`01_旧探测器模拟总数据/`](01_旧探测器模拟总数据/) 保存早期厚度 T、长度 H、距离 D 和 NPS 收敛计算。历史输入中的 LaBr3 晶体直径和长度均为 5.08 cm，外部只有 Al 壳，没有 D50H75 模型中的 PTFE 层。

这些结果主要采用 `6.03-6.23 MeV` 内 F8 bin 直接求和的 **Gross ROI** 判断趋势。它们不能称为 D50H75 探测器的最终优化结果，也不能称为 6.13 MeV 净峰面积。

历史记录保留两个不同事实：长度阶段曾建议 `T=4 cm, H=30 cm`；后续距离扫描和当前工作基线实际采用 `T=4 cm, H=25 cm, D=1 cm`。项目不改写这一差异，等待统一 Net Peak Area 方法复核。

### Generation 2: D50H75 Detector

[`02_D50H75新探测器/`](02_D50H75新探测器/) 面向当前正式探测器：

- LaBr3：直径 50 mm，长度 75 mm；
- PTFE：名义 1 mm，属于 simulation assumption；
- Al：名义 1 mm，属于 simulation assumption；
- 当前几何基线：`T=4 cm, H=25 cm, D=1 cm`；
- `D` 定义为 CaO 外表面到 LaBr3 晶体前表面的距离。

当 `Rout=9 cm, D=1 cm` 时，晶体、PTFE 和 Al 前表面的 x 坐标分别约为 10.0、9.90 和 9.80 cm。`A5075.i` 已由用户恢复并归入探测器对比工况；`D5075.i` 仍未恢复。A5075 输入卡为 NPS=5E7，而对应历史 output 实际为 NPS=1E8，清单中保留该不一致。

## 正式 6.13 MeV 指标

最终论文指标为氧峰净峰面积 `A_6.13_net`，不是整个高能 gamma 能谱，也不是历史 Gross ROI。完整能谱主要用于峰定位和模型检查。

在 `E=6.13 MeV`，当前 GEB 给出的理论 FWHM 约为 `0.077245 MeV`。固定 ROI 工作流为：

```text
高统计参考谱
-> Gaussian + linear background
-> mu、sigma、FWHM
-> 扫描不同 k*sigma
-> 确定一次固定 ROI
-> 保存 fixed_roi.json
-> 所有 T/H/D/Detector 模型应用同一 ROI
```

未来 `scripts/mcnp_roi.py` 应区分 Reference mode 和 Apply mode。Reference mode 只运行一次并写出固定 ROI；Apply mode 仅读取固定 ROI。禁止每个模型分别选择 ROI。

## 目录

```text
DT_yield_project/
├─ 01_旧探测器模拟总数据/
├─ 02_D50H75新探测器/
├─ scripts/
├─ docs/
├─ README.md
└─ .gitignore
```

每个模拟工况按 `Origin/代码输入/结果输出/数据处理/` 归档。跨工况结果只放在相应阶段的 `总结数据/`。

## 数据安全与公开规则

原始历史数据位于 `F:\东华理工大学研究生\MCNP\mcnp5\模拟总数据`，本项目只复制和整理，未修改原 input、outp、CSV 或 Origin 文件。公开输出文件名以 `_public.outp` 结尾，只替换超算账户路径，MCNP 输入回显、物理模型、F8、统计结果、warning 和结束状态保持不变。原始与公开 SHA256 见 [`docs/output_manifest.csv`](docs/output_manifest.csv)。

本仓库不包含 MCNP 可执行程序、许可证、核数据库、`xsdir`、runtp、meshtal 或 mctal。
