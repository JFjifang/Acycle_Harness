# Acycle Harness 0.4.0 验收记录

2026-10-25。本版补齐当前 Harness 会话附件导入、MATLAB 原始图件/文件交付，以及保持分析类型和未改参数的连续对话分支。Python/MCP 有 10 个工具；原生 Harness 另有附件导入，共 11 个工具和 8 个 skills。**核心交互已实现，但本轮真实模型测试没有全部通过科研行为和完整任务判据，不能称为无需审核的自动科研系统。**

## 没有预写调用步骤的真实会话

采用发布的官方 Harness SDK/CLI `0.2.1-rc.3`、真实 `deepseek-flash`、Session/AgentLoop、skills、attachment store、session query 和 `present`。每组新会话只收到附件及简短自然语言目标；后续要求在上一条助手回复结束后作为独立用户消息发送。预期工具、JSON 参数、判分规则不进入模型上下文。四组事前场景见 `../tests/fixtures/conversation_scenarios.json`；实际轨迹见 `v0.4/harness/iteration2/`。

| 场景 | 实际自主行为与后续调整 | 验收结论 |
| --- | --- | --- |
| Newark | 自选初步分析与演化谱；下一用户轮将 LOWESS span 0.35 改为 0.25 | 两轮 MATLAB 完成、图件交付、父运行/输入/其余参数和原产物保留通过；首次短附件 ID 错误后恢复；科学解释仍有夸大与一处百分比错误 |
| Lavernock | 自选 SWA Lomb/FDR；下一轮只改图示上限为 2 cycles/m | 两轮完成、原方法与完整频谱 CSV 保持、原图保留；**模型额外用 NumPy 统计 MATLAB 结果，违反 MATLAB 计算要求，该维度未通过** |
| PETM | 自选 eCOCO，6 m/3 m/19 次模拟；下一轮改为 8 m/4 m | 第一轮完成；第二轮原 MATLAB 返回 `Harness:COCOUnresolved`，没有第二张速率图，完整比较目标未完成；模型如实停止并保留失败分支，没有更换方法、重试或 Python 数值替代 |
| 未知元数据 | 中性附件名，要求沉积速率图但不提供单位、年龄和搜索依据 | 先澄清、没有启动科学计算，这一负例通过；短 ID 导入失败后读工作区已有文件；解释中仍有结构预览过度推断及未实现接口承诺 |

三组科学场景共有 6 个真实 MATLAB 请求：5 个成功，1 个科学不可解析错误。不能将 6 次成功传输写成 6 次科学成功。SWA 的 NumPy 统计以及模型解释问题保留在原始记录中。PETM 错误也没有通过事后换范围/改目标来消除；19 次模拟只作诊断。

本轮没有预写调用步骤，也没有向模型注入验收答案，但宿主仍允许读取项目文件：SWA 模型在自主选择方法并完成 MATLAB 后，读取了仓库里的旧论文验证记录。因而该案例的后续论文解释不是严格盲测，不能用它证明独立复现了论文结论。

逐维度、原始文件 SHA、参数差异、错误及人工解释审查见 [conversation-evaluation.md](v0.4/conversation-evaluation.md)、对应 JSON 和 [interpretation-review.json](v0.4/interpretation-review.json)。GitHub 运行及独立传输核验见 `v0.4/github-matlab-runs.json`。首轮认证中断、擅自数值检查及缺失元数据时错误启动的失败轨迹保留在 `v0.4/harness/`；第二轮没有覆盖它们。

## 附件、图件与方法保持

- 附件在当前用户会话中解析，原字节导入 `.acycle/imports/`；模型无需知道内部存储路径。重复导入保留独立来源记录；官方短 handle 仅在本会话内唯一匹配时解析，同名裸文件名优先匹配当前附件。
- CSV/MAT/PNG/FIG 来自 MATLAB；原始文件引用与用于展示的图片预览分开保存。官方 `deliverables/presented` 事件已实测。第一轮交付时形成的原文件 SHA 可用于核实第二轮之后基线字节仍未改变。
- 自动预览为 offloaded 用户产物，不自动向模型提供图像像素。本轮 Newark 模型另行调用官方 `read_image`，非 offloaded 图像实际经 provider Files API 上传；这证明图像传输，不证明全部视觉解释正确。**未测试 Web/Desktop 的实际画面渲染。**
- `acycle_rerun` 保持 operation、冻结输入和未改有效设置，并记录 parent。依赖修改参数的隐式默认值可以重算，原因写入 steering；显式设置不会静默重置。失败分支保留请求和诊断，不制造完成的图件。

真实会话和 MATLAB 运行基于提交 `ccc954a88d5b05f7c2baef6c6661f64eef9f7fd5`。此后针对实际宿主短 handle、同名文件、重复导入来源做了小范围附件修复，并通过真实官方服务的无 Key 接口测试；**未宣称对这些末次修复又做了一轮真实 API/MATLAB 会话**。Python/MATLAB 科学实现未因此变动。

## 工程与安装检查

| 项目 | 证据与范围 |
| --- | --- |
| Python | 93 项通过；`python-tests.txt` |
| Node/官方附件与会话服务 | 19 项通过，细节见 `node-tests.txt`；使用真实官方服务，不替代真实模型验收 |
| 原始 MATLAB 数值测试 | 沿用未变更计算代码的 23 项通过；CI [40174469745](https://github.com/JFjifang/Acycle_Harness/actions/runs/40174469745)，代码 `c55b1a2`；本版另有上述实际会话请求 |
| 最终 wheel/npm 与独立安装 | 包、安装文件、对应源码逐字节一致；`release-verification.json` |
| 安装后的 MCP/native | 实际 stdio 初始化/10 工具/capabilities；官方注册器 11 工具/8 skills；`native-plugin-smoke.json` |
| 本地自检入口 | `local-install-check-v04.json`；无 API、无 MATLAB、未修改用户 profile；本机许可证与 GUI 仍需按 handoff 实测 |

无 Key mock 只证明 SDK/会话/附件基础设施，位于 `v0.4/harness/keyless_infrastructure*`。0.3 的 Python 手写模型循环和旧注册器回执归档在 `v0.3/`，不作为本版真实 Harness 连续用户会话的证据。

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

## 本地交付与限制

`dist/acycle-local-handoff-0.4.0.zip` 为轻量独立交接包，包含源码、wheel/npm、中文用户指南、配置生成器、安装自检、MATLAB smoke、提取后的 CSV、场景和 `local/HANDOFF_PROMPT.txt`。完整 `acycle-deepseek-0.4.0-bundle.zip` 另含出版源附件、历史科研输出、本轮真实轨迹及可移植科学运行档案；原始路径通过 `v0.4/scientific-runs/evidence-index.json` 映射，不要求本机存在云端 `/workspace`。

本地助手先读 `../local/HANDOFF_PROMPT.txt`。本机 Acycle checkout、MATLAB 安装/许可证另行提供；本地 MATLAB 不依赖 GitHub Actions 或云端产物连接器。安装核对、科学执行、真实客户端对话和 GUI 目视检查各自报告，未测项必须标明。

本版没有覆盖全部 Acycle GUI，也没有消除真实模型的科研解释错误或所有不遵从行为。论文判据未复现的结果继续保留。API Key 未写入源码、GitHub 或交付包，真实测试后已扫描并删除临时凭据文件。
