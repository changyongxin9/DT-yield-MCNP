# GitHub 复现说明

仓库提供输入卡、脱敏 MCNP 输出、已处理 CSV、Origin 资料和 Python 脚本，但不提供 MCNP 软件、许可证或核数据库。

已使用的分析环境包括 `numpy`、`pandas`、`matplotlib`、`lmfit`、`becquerel` 和 `SciencePlots`。公共脚本统一位于 `scripts/`。

`*_public.outp` 是公开脱敏副本。物理内容与原始输出一致，仅账户路径被替换。可用 `docs/output_manifest.csv` 对照 SHA256 和来源。

历史 CSV 采用 Gross ROI。D50H75 的固定 ROI 尚未正式确定，`fixed_roi.json` 当前明确标记为 pending。确定后应先运行 Reference mode，再让所有模型通过 Apply mode 使用同一个 ROI。

本次目录整理没有运行 MCNP，也没有生成缺失模拟结果。缺少输入或正式 Net Peak 数据的目录使用说明文件标记，不以空 CSV 或虚假数值代替。
