# 分析与复现约定

## 单变量比较

几何优化按厚度 `T`、长度 `H`、探测距离 `D` 分阶段进行。每一阶段只改变目标参数，材料、源、探测器、能量网格、GEB 和统计设置应保持一致。输入文件位于 `inputs/optimization/`。

## 固定 ROI

1. 选择高统计基准谱。
2. 读取 GEB 参数并计算 6.13 MeV 理论 FWHM。
3. 用 Gaussian + linear background 拟合峰形。
4. 扫描 `k*sigma`，综合峰包含率、净峰面积和统计误差确定一次 ROI。
5. 锁定 ROI 后，对所有 T/H/D 和探测器模型使用同一区间。

逐模型重新选择 ROI 会把分析区间变化混入几何变化，不用于最终单变量比较。

## 结果语义

- `F8_Response`：每个源历史的脉冲高度响应。
- Gross ROI：固定能区内 F8 bin 的直接求和，未扣本底。
- Net peak area：固定 ROI 内 Gross 响应减去统一模型估计的本底。
- 标准 MCNP 输出通常不提供能道间协方差；逐 bin 误差平方和仅是近似不确定度。

## 仓库安全边界

不提交 MCNP 软件本体、许可证、核数据库、`xsdir`、SSH 密钥、服务器账号配置或大体积运行文件。新增文件在提交前应检查：

```powershell
git status
git diff --cached
```

正式 input/output 对应关系见 `simulation_inventory.csv`，原始输出复制映射见 `output_copy_map.csv`。无法匹配的候选输出及排除范围见 `unmatched_outputs.md`。
