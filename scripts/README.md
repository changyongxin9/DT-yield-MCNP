# 公共脚本

本目录集中保存输入生成、F8 提取、扫描汇总和 ROI 分析脚本。脚本不复制到各工况目录。

`mcnp_roi.py` 当前保留原状。未来升级应明确分为 Reference mode 和 Apply mode：Reference mode 生成一次 `fixed_roi.json`，Apply mode 对全部 T/H/D/Detector 模型读取同一 ROI，不允许逐模型重新选区间。
