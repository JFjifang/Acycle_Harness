# Newark 官方样例验证

状态：**通过**。实际 MATLAB 运行：[40171879521](https://github.com/JFjifang/Acycle_Harness/actions/runs/40171879521)，运行 ID `20261025T071158Z-b0f32143454c`。

输入为固定 Acycle 提交 `dcba4279168745b563e0535b954297023dd62fc7` 中的完整 `Example-LateTriassicNewarkDepthRank.txt`，SHA-256 为 `1cd82c19c0de98a8c4d6f09d3af1fdb3ff2e07fe93c3ee241102dd75e4b65ac2`。该文件使用 CR 换行，包含 2344 行数值数据。

MATLAB R2024b 执行原始 mini-robot 核心：LOWESS span 0.35、MTM NW 2、25% 中值平滑、EvoFFT 开启，坐标单位 m。2344 行全部保留；无非有限值、重复坐标或插值；采样间隔为 0.85344 m。全部所用 Acycle 原函数的实际哈希与参考提交一致。

生成并检查了 14 个 MATLAB 产物，包括 CSV、MAT、PNG 和可编辑 FIG。谱图与 EvoFFT 图已经实际打开核查。模型拟合采用原始 `redconfML`，没有触发异常拟合备用路径。

`newark-result.json` 保留完整公共工具结果；`newark-evidence.json` 提供输入/输出哈希、运行参数、实际来源和相对路径。实际文件位于 `validation/artifacts/newark/20261025T071158Z-b0f32143454c/`；源记录保留执行时的绝对路径。

本测试完成官方 Newark 数据上的核心处理与作图验证，不等同于复现发表论文的轨道年代模型。谱峰是深度域特征，未作无年龄模型依据的 kyr 换算，也未把逐频点置信度解释为轨道强迫证据。

标准 GitHub 产物下载在当前云代理仍返回 403，因而采用已授权 GitHub 连接器下载。ZIP SHA-256 `65bcb06806067744c1beb5612b462762f36678dfd483b22ea8c7643ef438c88c` 与 GitHub 回执完全一致；计算与保存仍全部在 MATLAB 中完成。
