# D-T 中子源产额与氧 6.13 MeV gamma 峰 MCNP 仿真

本项目整理 14.1 MeV D-T 中子源经 CaO 转换体产生氧特征 gamma 射线、由 LaBr3 探测器记录 F8 脉冲高度谱，并通过 6.13 MeV 氧特征峰净峰面积反演中子源产额的建模与数据分析流程。

## 当前研究主线

- 中子源：14.1 MeV D-T 中子，Phi10 mm 均匀圆盘源（半径 0.5 cm）。
- 转换体：CaO，当前工程优化几何为 `T4/H25/D1`。
- 几何定义：`T = Rout - Rin`；当前 `Rin=5 cm`、`Rout=9 cm`、`H=25 cm`。
- 探测距离：`D` 定义为 CaO 外表面到 LaBr3 晶体前表面的距离，当前 `D=1 cm`。
- 当前探测器方向：D50H75 LaBr3 + PTFE + Al。对应探测器输入未纳入当前仓库，后续正式归档时需补充经过确认的模型。
- 能量展宽：`FT8 GEB 0.01723 0.02424 0`。
- 核心目标：利用 **6.13 MeV 氧特征峰净峰面积**建立与 D-T 中子源产额之间的关系。
- 完整 gamma 能谱主要用于峰定位、输运模型检查和异常诊断，不作为研究终点。
- T/H/D 和探测器优化最终统一使用 6.13 MeV ROI 净峰面积作为比较指标。

仓库中的早期 T/H/D 扫描输入保留了优化过程中的探测器配置，用于复现参数趋势；D50H75 + PTFE + Al 是当前探测器配置。比较不同阶段结果时应先核对输入卡中的探测器几何。

## 目录结构

```text
scripts/    Python/WATTS 输入生成、F8 解析、ROI 与汇总脚本
inputs/     顶层预留；正式输入已与结果一起归档到 results/*/inputs/
reference/  两份脱敏的 5E8 MCNP outp，仅用于解析器测试
results/    按 T/H/D、NPS、探测器、ROI 和最终总结分类的小型结果
docs/       分析约定与复现说明
```

## ROI 分析原则

`scripts/mcnp_roi.py` 的目标流程为：

```text
MCNP outp
-> 提取F8谱
-> 读取GEB参数
-> 根据GEB计算6.13 MeV理论FWHM
-> Gaussian + linear background拟合
-> 得到mu、sigma、FWHM
-> 扫描不同k*sigma ROI
-> 比较峰包含率、净峰面积和统计误差
-> 用高统计基准谱确定一次固定ROI
-> 所有T/H/D和探测器模型使用同一个ROI
```

不允许为每个模型分别重新选择不同 ROI。模型之间必须使用同一高统计基准谱确定的固定 ROI，否则会引入额外分析变量并破坏单变量比较原则。

MCNP F8 是按源历史归一化的脉冲高度响应。对能量 bin 求和时不再次除以 NPS，也不乘能道宽度。净峰面积需要使用统一的峰形和本底定义，不能与未扣本底的 Gross ROI 混用。

## Python 环境

当前分析环境使用：

```text
numpy
pandas
matplotlib
lmfit
becquerel
SciencePlots
```

WATTS 输入批量生成还需要可用的 `watts` Python 包。

## 快速测试

```powershell
python scripts/mcnp_roi.py reference/T04_H25_D01_5E8/outp
```

该命令会在参考文件目录生成分析产物。Git 默认忽略这些派生图和临时结果时，应在提交前检查 `git status`。

## 数据与软件边界

本仓库不包含 MCNP 可执行程序、安装包、许可证、核数据库、`xsdir`、服务器密钥、账号凭据、`runtp*`、`mctal`、`meshtal` 或批量原始输出。运行 MCNP 需要用户在合法授权环境中自行配置软件和核数据。

`reference/` 中的样例仅用于测试解析器，远程账号路径已脱敏；这些输出不能替代正式数据归档。

## 结果目录说明

现有 T/H/D 与 NPS 汇总表使用的是 `6.03-6.23 MeV` 范围内 F8 bin 的直接求和，属于 **Gross ROI**。这些历史数据用于趋势检查，不应被标为净峰面积。论文主线所需的净峰面积将在 `results/06_ROI_6p13MeV/` 中通过固定 ROI 和统一本底方法生成。

历史长度分析报告建议 `T=4 cm, H=30 cm` 进入距离优化，而当前项目主线采用 `T=4 cm, H=25 cm, D=1 cm`。该差异保留在结果说明中，未擅自改写任何既有结论。

## 科研数据可追溯性

MCNP input 用于定义模型，MCNP output 是论文数据的原始计算证据。一个完整模拟数据点应同时保存 input 与经过严格匹配的 output。后续的 F8 能谱提取、Gross ROI、Gaussian 拟合、本底扣除、Net Peak Area、Relative Error 和 ROI 优化均应能够从保存的 `outp` 重新生成。

每个正式研究阶段按 `inputs/`、`outputs/`、`processed/`、`figures/`、`notes/` 分类。完整对应关系记录在 `docs/simulation_inventory.csv`。

当前正式 `outp` 原样副本包含超算用户目录路径。为同时满足“原始结果不修改”和“GitHub 不泄露账号信息”，这些文件已保存在本地 `outputs/`，但暂不进入 Git 索引；待确定脱敏副本策略后再决定是否上传。
