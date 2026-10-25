# Acycle Harness 0.3.0 验收记录

2026-10-25。Newark 官方样例已完成；新增 SWA、COCO、eCOCO 原始 MATLAB 桥，合计 9 个工具、8 个 skills。计算、Monte Carlo、作图及科学数据保存均在 MATLAB 中完成。Python 负责接口、输入快照、文件传输与运行记录，没有自动数值替代路径。

## 工程验收

| 项目 | 实际结果 | 证据 |
| --- | --- | --- |
| Python 编排、协议和敏感性分支 | 55 项通过 | `python-tests.txt` |
| Node 传输、取消、错误和 skill 资源 | 4 项通过 | `node-tests.txt` |
| 实际 MATLAB R2024b | 23 项通过；独立论文判据另列 | `matlab-summary.json`、`matlab-junit.xml` |
| 安装后的原生 Harness 插件 | 9 工具、8 skills 注册、调用与卸载成功 | `native-plugin-smoke.json` |
| 安装后的 MCP stdio | 初始化、9 工具列表和实际 capabilities 调用成功 | `release-verification.json` |
| DeepSeek-V4.1-Flash 真实 API | 6 轮请求、7 次成功工具调用；SWA/COCO/eCOCO 均执行真实 MATLAB | `deepseek-v03-live.json` |
| 最终 wheel / npm 包 | 安装文件、包内文件和对应源码逐字节一致 | `release-verification.json` |

最终 MATLAB CI：[40174469745](https://github.com/JFjifang/Acycle_Harness/actions/runs/40174469745)，计算与绘图代码提交 `c55b1a2`。MATLAB 测试包括原函数数值对照、合成已知速率、单位转换、指定间隔插值、完整窗口、blocked/interleaved 模式、输入拒绝、原始图件及论文数据。测试成功只表示这些工程断言通过；`matlab-summary.json` 另外列出独立论文判据，没有将科研未通过项改写为通过。

原生插件验收使用官方 dsh 0.2.1-rc.3 的 tools/system-prompt/skill 注册器和 Cordis 4.0.5。MCP 验收使用实际安装后的 Python 子进程；未宣称运行过完整 Codex 或 Harness 桌面 UI。本云端没有本机 MATLAB，实际科学计算通过 GitHub Actions 执行；用户电脑上的 MATLAB 许可证和客户端接入需按 handoff 验收。

## Newark

完整官方 Newark 输入 2344 行全部保留，无重复、缺失删除或插值，间隔 0.85344 m。原始 mini-robot 处理生成 14 个 CSV、MAT、PNG、FIG 产物，谱图和 EvoFFT 图已打开检查。全部所用原函数哈希匹配，采用原始 `redconfML`。专项运行：[40171879521](https://github.com/JFjifang/Acycle_Harness/actions/runs/40171879521)。详见 `NEWARK.md`、`newark-evidence.json`；完整输出位于 `artifacts/newark/`。这不是对 Newark 已发表年代框架的重新建立。

## 论文验证：保留未复现结果

| 案例 | MATLAB 实际结果 | 科研状态 |
| --- | --- | --- |
| Weedon SWA / Lavernock | 0.82125 m 谱峰；原始 FDR 执行后未给出拒绝阈值 | 峰位置吻合，论文 5% FDR 条件未复现 |
| PETM 较宽区间首轮 | 2000 次模拟；最大相关速率 26.43 cm/kyr，速率网格全局 p≈0.10395 | 未落入事前 8–15 cm/kyr 比较区间；与原文协议也有差异 |
| PETM 补充日志协议 | 4364 个原始点，经 MATLAB 生成 2370 点、0.01 m 间隔；2000 次模拟；最大相关速率 28.93 cm/kyr，全局 p≈0.66967 | 仍未落入 8–15；最大相关处仅解析 4/6 个目标周期，不支持据此解释地质沉积速率 |
| Cambrian 主 Al 指标 eCOCO | 18001 点、8 个窗口、199 次模拟及原始 MATLAB 图件 | 缩减真实数据流程通过；未复现完整已发表速率图或年代模型 |

PETM 第二组按 Supplementary Text 3 的实际日志独立新增，采用指定区间、Pearson、NFFT 5000、频率上限 0.06、20 m LOESS 和六个周期，保留首轮失败。现代目标模型、零假设及未逐点核实的历史预处理仍限制比较；没有把差异唯一归因于版本，也没有截短速率网格或切换参数追求通过。该组全局 p 的 Monte Carlo 区间约为 [0.6486, 0.6898]，不是模拟次数太少导致无法判断。

来源、DOI、协议差异和实际比较见 `../docs/PAPER_VALIDATION.md`、`paper-validation.json`。公开 benchmark 保持原科学判据，未达到时仍返回 `acceptance_failed` 和非零退出码。早期失败 CI [40172473806](https://github.com/JFjifang/Acycle_Harness/actions/runs/40172473806) 与 [40173168648](https://github.com/JFjifang/Acycle_Harness/actions/runs/40173168648) 的证据保留，没有被最终工程通过状态覆盖。

## MATLAB 来源和兼容性

Acycle 固定参考提交为 `dcba4279168745b563e0535b954297023dd62fc7`。SWA 使用原 `specswafdr` / `spectralswafdr`；COCO/eCOCO 使用原现代计算核心和出版图函数。LOESS/LOWESS 的 GUI 回调抽取、原 `interpolate` 调用及显示适配均有来源说明。COCO 只扩大第一张图的图幅并处理标题下划线，保持原始曲线和统计量；数据、图和可编辑 FIG 由 MATLAB 保存。

`matlab/source_registry.json`、`swa_sources.json`、`coco_sources.json` 记录参考哈希；每次执行记录实际哈希和 adapter 哈希。未来 Acycle 版本的同名入口不构成已验证兼容，需重新运行对照。当前未覆盖全部 GUI、历史 COCO 算法或完整论文年代建模。

## 真实模型记录与交付

三次新工具运行均成功并保留原始输入、请求、输出及传输凭据：

- SWA：`20261025T072936Z-7dc390007a72`，Actions `40172963619`。
- COCO：`20261025T073241Z-98795147bb9a`，Actions `40173168574`。
- eCOCO：`20261025T073632Z-d9b4dcbd12d9`，Actions `40173414618`。

COCO/eCOCO 的这次模型 smoke 使用 19 次模拟，只检查执行链路。`live-v03-evidence.json` 列出完整输出的相对路径和 SHA-256。原始模型答复保留；`deepseek-v03-answer-audit.json` 单独纠正其 Newark 缩略 hash 的一处转录错误及“没有 global test result”的过强 FDR 表述。工具执行通过不代替科学解释审查。

当前云代理仍拒绝 GitHub 产物签名存储地址；通过已连接 GitHub 工具下载并核验 ZIP 哈希。该传输适配不参与计算。本地 MATLAB 路线不依赖 GitHub 或该连接器。

`dist/acycle-local-handoff-0.3.0.zip` 为独立本地交接包，包含源码、安装包、中文指南、配置生成器、自检、smoke、提取 CSV 和 `local/HANDOFF_PROMPT.txt`。完整 `acycle-deepseek-0.3.0-bundle.zip` 另含出版源文件、Newark 和模型实际输出、前后 CI 图表及历史证据。原始记录中的历史绝对路径保留，换目录后使用证据索引中的相对路径。Acycle checkout 与 MATLAB 商业安装需自行提供。

API Key 未写入源码、GitHub 或交付包；测试临时凭据文件已删除。0.2 的旧验收记录归档在 `validation/v0.2/`，其 9 项 MATLAB 测试与旧模型测试不能代替本轮结果。
