# 6.13 MeV ROI Definition

## GEB 与理论峰宽

当前 GEB 为：

```text
FT8 GEB 0.01723 0.02424 0
```

MCNP 使用：

```text
FWHM(E) = a + b * sqrt(E + c*E^2)
```

在 `E=6.13 MeV` 时，理论 `FWHM=0.077245420 MeV`，约 `77.25 keV`。

## 固定 ROI 工作流

```text
MCNP outp
-> 提取 F8:P 能谱与 Relative Error
-> 读取 GEB 参数
-> 计算 6.13 MeV 理论 FWHM
-> 提取局部谱
-> Gaussian + linear background 拟合
-> 得到 mu、sigma、FWHM
-> 扫描 1.5sigma 至 3.5sigma
-> 比较 Gaussian capture fraction、gross、background、net peak area 和统计误差
-> 使用高统计基准谱确定一次固定 ROI
-> 对所有 T/H/D/探测器模型应用同一 ROI
```

禁止为每个模型分别重新拟合并选择不同 ROI，否则分析方法本身会成为变量。

实现脚本：`../../scripts/mcnp_roi.py`。当前目录尚未生成正式 ROI 扫描数据、拟合图或固定 ROI 结论。

