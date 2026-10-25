# Acycle Harness 0.5.1 验收

本版面向当前官方 DeepSeek Harness 0.2.1-rc.3，简化部署并增加有出处的 Newark 文献指引。它没有修改 MATLAB 科学算法或 0.5.0 的排练结果。

## 本轮范围

- 统一采用当前 Harness 的 agent preset、system prompt、附件与技能接口，移除旧版能力探测分支。
- 最新 Desktop 原生插件部署与项目内 Web 部署共享 Acycle preset；Codex 保留 MCP 接入。
- Newark 0.5.1 增补早期长偏心率周期识别与 COCO 原文的方法线索；保留公开计算参数，区分文献中的原算法和当前 Acycle 实现。
- 用户文档与本地 handoff 收敛到必要安装、MATLAB 检查和启动步骤；详细研究记录通过链接保留。

## 验证状态

| 本轮检查 | 结果与回执 |
| --- | --- |
| 最新官方版本 | rc.3；GitHub 发布标签为 `dsh-v0.2.1-rc.3`，npm `latest` 仍为 rc.2、`next` 为 rc.3；[版本核对](harness/upstream-release.json) |
| Python 接口与编排 | 203 项通过；[日志](engineering/python-tests.txt) |
| 官方 Harness 插件合约 | 28 项通过，最终安装 wheel；[日志](harness/node-contracts-installed.tap) |
| 最终安装包 | 26 个 wheel 文件、16 个 npm 文件逐字节匹配源码与独立安装；实际 MCP 12 工具、原生 13 工具；[回执](release-verification.json) |
| Web 普通与演示配置 | 最终安装包均通过，分别 13 工具/10 技能、13 工具/11 技能；[普通](harness/web-normal-installed.json)、[演示](harness/web-demo-installed.json) |
| Desktop 原生 bundle 与生成 patch | 最终安装包在官方共享运行层通过相同两种配置；[普通](harness/desktop-shared-normal-installed.json)、[演示](harness/desktop-shared-demo-installed.json)。未运行 Electron/macOS 窗口 |
| 新文献 skill | 实际演示 agent 加载 `demo/newark-0.5.1`，记录 skill 正文及来源哈希；上述演示回执中可核查 |
| Web 图件交付 | Chromium 实际主 Chat 显示两张既存 MATLAB 图，放大、刷新及 PNG/CSV/MAT/FIG 原件下载哈希通过；[回执](web/main-chat-fixture.json)。使用 text-only scripted provider，没有模型 API 或科学重算 |
| 科学代码、输入与参数 | MATLAB 源码、原始输入字节及既有科学预设均保持不变；[比较回执](scientific-continuity.json) |

本轮没有重新运行真实 DeepSeek 科学会话或 MATLAB 计算。新文献提示的实际模型表现仍须本地排练，不将 0.5.0 的会话称为新提示词验收。Desktop 共享配置通过也不替代用户本机窗口、MATLAB 许可证和完整演示的检查。

新配置将 Python、Acycle 和 MATLAB 路径保存在 Acycle preset 中，仅传给该插件的子进程；不要求 Desktop 继承终端路径，也不改写其他 agent 的环境。Desktop 继续使用用户现有模型设置；项目 Web 路线独立引用环境中的凭据。

## 继承的科学证据

[0.5.0 验收](../v0.5/ACCEPTANCE.md)记录了 39 项 MATLAB 测试、Newark 两条独立用户消息和 9 次成功 MATLAB 计算，以及真实模型图像传输和 Web 显示检查。它仍保留原始解释错误与论文比较的未通过项。

Newark 演示沿用 405 kyr 相对年代假设和 19 次 Monte Carlo 的快速预算；此前全记录 COCO 不显著。新增论文指引不构成该数据已检出 405 kyr 的新证据，也不把现行 Adaptive COCO 写成 2018 年算法的精确复现。原始排练图件与经校核讲稿均明确标注其 0.5.0 来源。
