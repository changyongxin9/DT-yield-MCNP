# Generation 2: D50H75 Detector

当前探测器模型为直径 50 mm、长度 75 mm 的 LaBr3 晶体，外含名义 1 mm PTFE 和名义 1 mm Al。两层厚度均为 simulation assumption，不是 manufacturer specification。

当前基线为 `T04_H25_D01`：CaO 外半径 9 cm，晶体、PTFE 和 Al 前表面的 x 坐标分别为 10.0、9.90、9.80 cm。D 始终定义为 CaO 外表面到晶体前表面的距离。

本代目标是从高统计基准谱确定一次固定 6.13 MeV ROI，并用 Gaussian + linear background 得到净峰面积。尚未完成的新探测器 T/H/D 复核均标记为 Missing simulation，不生成虚假结果。A5075 analog-check 输入已恢复并保留；D5075 输入仍缺失。
