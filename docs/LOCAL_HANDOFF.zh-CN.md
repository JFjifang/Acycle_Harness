# 本地部署与续测 handoff

适用目标：在自己的电脑用 Codex 或 DeepSeek Harness 调用本地 MATLAB，测试 Acycle Harness 0.4 的 Newark、SWA、COCO、eCOCO，以及“提供数据 → 简短提示 → 查看图件 → 连续对话调整”。本文和 `local/` 是交接材料；它们不会自动改写你现有的 Codex/Harness 配置。

## 交接包应包含什么

保留完整 ZIP 的目录结构，不要只取 npm 包：

另提供轻量独立 handoff ZIP，包含同一版本源码、安装包、文档、本地工具和提取后的 CSV。它省略出版社原始附件及历史云端大体积输出；需要审计原始附件时使用完整包，或运行 `benchmarks/prepare_paper_data.py --download` 按固定哈希取回。

| 内容 | 用途 |
| --- | --- |
| `dist/acycle_deepseek-0.4.0-py3-none-any.whl` | 安装 Python 接口和随包 MATLAB 桥 |
| `dist/dsh-acycle-0.4.0.tgz` | DeepSeek Harness 原生插件和 skills |
| `matlab/`、`src/`、`tests/` | 可检查和修改的实现；MATLAB 桥调用外部 Acycle 原函数 |
| `benchmarks/`、`examples/` | 论文原始附件/提取记录、参考输入、请求示例 |
| `tests/fixtures/conversation_scenarios.json` | 4 组预先声明的自然语言会话与独立验收规则 |
| `docs/USER_GUIDE.zh-CN.md` | 详细安装、参数、steering 和排错说明 |
| `local/HANDOFF_PROMPT.txt` | 可以直接粘贴给本地助手的完整任务文本 |
| `local/install_check.py`、`doctor.py`、`render_config.py`、`smoke.py` | 安装/MCP/可选原生检查、MATLAB 自检、生成配置片段、实际 smoke |
| `validation/` | 已有验收证据；本地新结果另写 `local-validation/` |

Acycle 原仓库和 MATLAB 商业安装不包含在这个包中。`ACYCLE_ROOT` 要单独指向原仓库，参考 SHA 为 `dcba4279168745b563e0535b954297023dd62fc7`。新版本 Acycle 可以另行验证，不能直接覆盖参考 checkout 后继续沿用旧验收结论。

## 交给本地助手

打开项目目录，在新会话中粘贴 [HANDOFF_PROMPT.txt](../local/HANDOFF_PROMPT.txt) 的全部内容。若客户端支持读取本地文件，也可以说：

> 请读取并执行当前项目 `local/HANDOFF_PROMPT.txt`。先确定本地路径与已安装环境，完成独立检查和小规模 MATLAB 测试，再给我实际结果。不要照抄历史云端的 `/workspace/...` 路径。

该任务文本包含环境定位、安装边界、Python/MCP 的 10 个工具、Harness 的 11 个工具与 8 个 skills 的检查，以及 Newark/SWA/COCO/eCOCO、附件导入、图件回传、独立用户消息中的连续调整。19 次 Monte Carlo 仅用于诊断。API Key 不在交接包中；需要真实模型时使用本地已有的运行环境凭据。

## 手工部署的最短路线

1. 打开完整包所在目录，按 [用户文档](USER_GUIDE.zh-CN.md) 安装 `.venv`、Python 包、参考 Acycle，设置 MATLAB 路径。
2. 运行 `python local/install_check.py --output local-validation/install.json` 核对软件安装，再运行 `python local/doctor.py --run-matlab --output local-validation/doctor.json` 检查许可证/工具箱/路径。
3. 运行 `python local/smoke.py --case analyze`，确认 Newark 原始输入和 MATLAB 输出。
4. 依次运行 `--case swa`、`--case coco --nsim 19`、`--case ecoco --nsim 19`。每次输出独立运行和回执。
5. 运行 `python local/render_config.py --workspace . --acycle-root /absolute/path/acycle --matlab /absolute/path/matlab`，检查生成片段。
6. 选择 Codex MCP 或 Harness 原生插件接入，刷新客户端后再做一次真实工具调用，避免只测 CLI 却声称客户端接入已验证。
7. 在 Harness 真实会话中上传数据，以短提示开始；收到回复后再发送调整要求。核对附件导入、图件事件、客户端可见的图、独立子运行和比较结果，不能用一条预先写好全部参数的提示代替。

若需要独立 Harness 检查环境，按用户文档第 6 节将固定版本官方 npm 包和本版插件安装到 `local/harness-runtime`，再为安装检查加 `--runtime local/harness-runtime`。注册器检查和 `--mode mock` 无需 API Key；真实 `--case` 会调用模型和科学工具，须单独记录。所有命令显式使用本机 runtime、工作区和回执路径；不改全局 npm、真实用户 profile 或模型设置。

`render_config.py` 只生成 `local/generated/` 中的片段；遇到与现有内容不同的同名文件会拒绝覆盖。只有明确要重生成这些片段时才使用 `--force`。它不会修改 `~/.codex/config.toml`、项目 `.codex/config.toml` 或 Harness profile。不要把生成片段连同本机绝对路径误当成适用于另一台电脑的配置。

Harness 上传测试应使用当前会话的真实文件附件。`acycle_import_attachment` 不带参数时只自动选择最近含文件用户消息中的唯一附件，多文件必须明确选择；导入后的原字节位于工作区 `.acycle/imports/`。附件/会话查询服务缺失时不能宣称上传路径通过，可继续独立验证工作区文件模式。图件通过官方图片/文件引用返回；`present` 不可用时会报告 `links_only`。插件自动预览是 `offloaded`，不会通过这一步把像素交给模型；宿主 `read_image` 与支持图像的模型路由可额外提供读图能力，须单独核对真实调用和模型输入，不能把文字解释或自动预览直接当作视觉核验。

附件短句柄必须在本会话内唯一；裸文件名优先选择会话上传数据，读取旧工作区同名文件须显式用 `./文件名` 或绝对路径。每次导入的 `import_receipt` 是新的来源记录，即使原字节按哈希复用，也应核对本次 session/message，不能覆盖旧记录。

## 本地验收表

| 检查 | 应保留的证据 |
| --- | --- |
| 包版本和解释器 | Python 路径、包版本；Python/MCP 10 个工具，Harness 11 个工具、8 个 skills；不要混装旧 wheel 和新 npm 包 |
| MATLAB实际运行 | release、工具箱、成功启动记录；不能用可执行文件存在代替 |
| 模型额外代码 | 检查完整工具轨迹；不能仅凭 Acycle 后端为 MATLAB 就忽略模型另用 Python 统计、质量检查或作图的行为 |
| Acycle来源 | checkout SHA、每个原函数hash、是否匹配参考 |
| Newark | 请求、summary、谱图、演化图、数值输出 |
| SWA | Lomb/MTM路径、原FDR含义、实际文件与图；非有限阈值的语义 |
| COCO/eCOCO | 目标周期来源、深度单位、cm/kyr网格、窗口/步长、nsim、seed、支持/失效信息 |
| 附件 | 当前会话授权的附件 ref、导入后路径与输入哈希；其他会话附件不能靠猜 ID 读取 |
| 客户端与图件 | 实际工具调用、官方图片/文件回传事件、`presentation.status`/`delivery.status`/`skipped`；在 Web/Desktop 中打开图件与下载文件的结果另外记录 |
| 连续对话 | 每条独立用户提示、回复、澄清内容、后续调整及会话 ID；工具往返轮数不能当作用户轮数 |
| Steering | 原基线存在、输入 hash 一致、子运行 parent 正确；`acycle_rerun` 保持分析类型与未改参数，比较结果可追溯 |
| 研究解释 | 逐点/全局/选择后检验区分、未完成部分、论文复现边界 |

本地 smoke 的 COCO 网格和 210 Ma 中间年龄是执行示例。不得把其最优速率直接作为 Newark 的地质结论。只有与论文对应的完整输入、预处理、目标、搜索范围、模拟设置和检验准则一致，才可以进一步讨论定量复现。实际复现参照 [PAPER_VALIDATION.md](PAPER_VALIDATION.md) 和 benchmark 的来源记录。

0.4 的真实 Harness 场景已执行，结果并非全部通过：Newark 两轮核心流程完成但解释有问题；SWA 两轮与方法保持完成，但模型用 NumPy 作数值 QA，违反 MATLAB 计算要求，且读取了旧论文结果；PETM 的第二个窗口设置在原 MATLAB 中不可解析，没有第二张速率图；未知元数据先澄清的行为通过，但文本仍有过度推断和接口承诺错误。参见 [conversation-evaluation.md](../validation/v0.4/conversation-evaluation.md) 与 [interpretation-review.json](../validation/v0.4/interpretation-review.json)。末次 3 项附件边界修复只补了官方服务接口测试，未再次执行真实 API/MATLAB；GUI 渲染未测。

请本机报告逐项记录 `passed`、`failed`、`not_run`，把真实模型、模拟模型、MATLAB 执行和 GUI 目视检查分开。遇到缺少单位或年代背景的短提示时，应看到针对必要科学信息的澄清；用户补充后仍应在同一会话继续。不能用工程通过覆盖模型违规，也不能把如实报告计算失败写成完整任务已完成。

使用 `tests/fixtures/conversation_scenarios.json` 可依次测试 Newark 去趋势调整、Lavernock FDR 图示范围调整、PETM eCOCO 多参数调整和缺少科学背景的澄清。每个场景使用新的会话与工作区；只把 `user_prompt` 和附件交给模型，接受规则、原数据隐藏身份和既有结果用于验收，不进入模型上下文。若模型提出合理澄清，只补充场景中已有的用户事实；没有事实可回答时标记 `needs_human_clarification`，不能为了跑通而编造条件。

## 已知科研差异必须随交接保留

本轮新增论文检查并非全绿：Lavernock SWA 的约 0.82125 m 峰位置接近论文约 0.81 m，但没有复现其 5% FDR 条件；PETM COCO 首轮较宽输入区间在 2000 次模拟下约 26.43 cm/kyr、速率搜索校正 p 约 0.103948，未落入论文 8–15 cm/kyr 区间。原始日志核对发现首轮的输入区间、插值和相关类型不一致，首轮结果已保留；按日志独立复跑得到 28.93 cm/kyr、全速率网格校正 p 约 0.66967，仅解析 4/6 个周期，同样未通过原判据。不能直接归因于算法版本，也不能据此推断可靠地质速率。Cambrian eCOCO 只进行了预算缩减的数据流程验证。详见用户文档第 9 节与当前版本验收回执。

请本地助手区分工程执行、原函数对照和论文判据；不要删除未通过的科学检查，也不要为了把它变成通过而隐含改变输入、参数、显著性定义或接受区间。`phase_averaged` 接口现限制 2–9 个显式周期，不能沿用早期草稿中 2–32 个周期的描述。云端历史路径只出现在原始回执中，本地脚本根据本机 `ACYCLE_ROOT`、当前工作区和解释器生成路径。

## 遇到问题时需要回传的最小信息

提供操作系统、Python/MATLAB版本、`local-validation/doctor.json`、失败运行的 `request.json`/`result.json`、MATLAB日志和预期输出名称即可。先排除 API Key、许可证秘密、用户凭据和无关私有文件。纯本地计算不依赖 GitHub Actions，也不需要云端产物连接器；如果本机 MATLAB 可用，继续走本地路径。
