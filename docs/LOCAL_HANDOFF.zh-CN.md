# 本地部署与续测 handoff（0.5.0）

解压后，把 [local/HANDOFF_PROMPT.txt](../local/HANDOFF_PROMPT.txt) 的全部内容交给本机 Codex 或 DeepSeek Harness 即可开始。助手应定位本机已有的 MATLAB 和 Acycle，完成项目内安装、独立检查和实际运行，再交付验收报告。不要照抄历史回执中的云端绝对路径。

本版 Python/MCP 有 **12 个工具**，Harness 原生有 **13 个工具**，配套 **10 个 skills**。六项科学操作为 mini robot、SWA、COCO、eCOCO、Interpolation Pro、周期极值调谐；具体子功能及兼容边界见 [用户文档](USER_GUIDE.zh-CN.md#功能覆盖与兼容边界)。计算、数值 QA 和作图在 MATLAB 中完成，Python 处理接口、传输、结构检查和 Acycle 未实现的辅助功能。

## 交接包

保持交付 ZIP 的目录结构。轻量包包含同版安装包、实现、文档、本地工具、演示输入与提取后的论文 CSV；完整包另含原附件与更多历史证据。需要取回出版社附件时可运行 `benchmarks/prepare_paper_data.py --download` 并检查预先记录的哈希。

| 路径 | 用途 |
| --- | --- |
| `dist/acycle_deepseek-0.5.0-py3-none-any.whl` | Python/MCP 接口、MATLAB 桥和源文件清单 |
| `dist/dsh-acycle-0.5.0.tgz` | Harness 原生插件与 10 个 skills |
| `matlab/`、`src/`、`tests/` | 可审查实现和测试；原 Acycle 另行安装 |
| `demo/newark-0.5.0/` | 公开输入、明确先验、相对时间演示方案和独立用户提示 |
| `benchmarks/`、`examples/` | 论文来源与执行请求示例 |
| `local/install_check.py` | 安装文件、版本、12 个 MCP 工具；可选原生注册器检查 |
| `local/doctor.py` | 路径与来源检查；显式启动一次 MATLAB 检查许可证/工具箱 |
| `local/deploy_harness.py`、`launch_harness.py` | 项目内固定版本官方 Web/native 部署和启动 |
| `local/check_harness.py`、`harness_probe.mjs` | 实际 agent preset、技能消息、persona 与图像能力的无 Key 检查 |
| `local/render_config.py` | 只生成 Codex MCP 与环境片段，不覆盖客户端配置 |
| `local/smoke.py` | 六项科学操作的实际 MATLAB 诊断调用；支持 dry-run |
| `validation/v0.5/` | 本版按层区分的验收；本机新增结果另写 `local-validation/` |

MATLAB 商业安装、许可证、API Key 和 Acycle 完整源码不包含在交付包里。Acycle 参考提交为 `dcba4279168745b563e0535b954297023dd62fc7`。保留用户原目录的修改，必要时另建参考 checkout；不要重置用户研究目录。

## 最短本地路线

从解压后的项目目录运行。先按用户文档建立 `.venv`，安装匹配 wheel，并设置 `ACYCLE_ROOT`、`ACYCLE_BACKEND=local`、`MATLAB_EXECUTABLE`。macOS MATLAB 路径通常是 `/Applications/MATLAB_R2024b.app/bin/matlab`，Linux 通常在 `/usr/local/MATLAB/.../bin/matlab`，Windows 是实际安装目录下 `bin\matlab.exe`；以本机存在路径为准。

```sh
python local/install_check.py --output local-validation/install.json
python local/doctor.py --run-matlab --output local-validation/doctor.json
python local/smoke.py --case all --dry-run
python local/smoke.py --case analyze
python local/smoke.py --case swa
python local/smoke.py --case coco --nsim 19
python local/smoke.py --case ecoco --nsim 19
python local/smoke.py --case interpolate_pro
python local/smoke.py --case tune
```

每条实际 smoke 都会创建独立运行。`tune` 是三个调用：示例频带滤波、405 kyr 假设下极值调谐、同一年龄模型作用于**原始 proxy** 的时间诊断。它采用相对时间零点，不建立绝对年代；19 次 Monte Carlo 只用于诊断，不能支持发表级显著性结论。第一处失败即停止相应 smoke，保留失败记录。

Codex 接入使用 `python local/render_config.py --workspace . --acycle-root "$ACYCLE_ROOT" --matlab "$MATLAB_EXECUTABLE"`，检查并仅合并生成的 `acycle` 条目到受信任项目 `.codex/config.toml`，不覆盖其他配置。它保留虚拟环境解释器路径和足够的工具超时；刷新 MCP 后检查实际 12 个工具。Codex 不提供 Harness 专用的附件导入工具，数据按本地工作区路径接入，客户端图件显示需要单独验证。

Harness 的支持方案是 **Node.js ≥24.9 + 官方 0.2.1-rc.3 Web/native + 实际 `acycle` preset**：

```sh
python local/deploy_harness.py --workspace . --acycle-root "$ACYCLE_ROOT" --matlab "$MATLAB_EXECUTABLE" --install
python local/install_check.py --runtime local/generated/harness-web/runtime --output local-validation/install-harness.json
python local/check_harness.py --output local-validation/harness-composition.json
python local/launch_harness.py
```

PowerShell 用 `.\.venv\Scripts\python.exe`，环境变量写成 `$env:ACYCLE_ROOT` 和 `$env:MATLAB_EXECUTABLE`。只从同一操作系统调用 Python/MATLAB，避免混合 WSL 与 Windows 路径。所有命令显式采用本机路径，不依赖原云端工作目录。

生成器将 runtime、npm cache、私有 `DSH_HOME`、Web profile 和 deployment manifest 保存在 `local/generated/harness-web/`。旧 Desktop 0.1.2-rc.1 保持原样；不要用此 CLI 去修补或改写其标准 preset。部署可传 `--directory`、`--port`，已有同版本 runtime 可用 `--runtime`。`--force` 只重生成这些项目内文件；不清空已有会话或研究结果。

启动子进程继承模型凭据环境，并从 manifest 载入 MATLAB/Python 路径。官方路由 `deepseek-official/deepseek-flash` 明确声明 text/image；配置只引用 `DEEPSEEK_API_KEY`，绝不保存其值。无 Key 时照常完成安装、实际 agent 组合和 MATLAB 独立检查，真实模型步骤记为 `not_run`。

`check_harness.py` 不仅查根注册器：它创建实际 preset agent，检查 13 个原生工具、10 个 scoped skills、persona、可加载技能正文和模型图像能力，并捕获确定性 fixture 的真实 AgentLoop 请求，确认技能目录在官方 pre-step 后进入模型消息。这个检查不调用模型 API 或 MATLAB，也不证明浏览器已显示图件。可用 `doctor.py --harness-deployment local/generated/harness-web/deployment.json --check-harness` 联合检查。

## 实际对话与图件

在 Web 新会话中上传数据，用短提示提出问题；收到第一轮助手回复与 MATLAB 结果后，再发送独立的调整要求。缺少单位、年代范围、目标周期或速率搜索依据时，模型应先读取已有材料，再澄清必要信息，不应推测文件的隐藏身份。

`acycle_import_attachment` 只导入当前会话用户授权的文件。无参时选择最新含文件消息中的唯一附件；多文件须选择。8 位官方短句柄必须在会话内唯一；裸文件名优先匹配当前会话上传，旧工作区同名文件使用 `./文件名` 或绝对路径。保存原字节与输入哈希，每次导入另有 `.acycle/imports/<sha256>/.source-<uuid>.json` 记录实际 session/message。

修改已有分析使用 `acycle_rerun`：保留原输入、基线、方法和未改设置；跨分析类型的新操作独立开始，不伪造同类型 parent。调谐后用原始 proxy 和 `tuning_run_id` 做时间诊断；不用已强制赋予周期的滤波曲线证明该周期。输出保留 CSV/MAT/PNG/FIG/PDF 等实际产物与哈希，不能仅看成功退出码。

图件展示要检查**主 Chat 最终答案内真实 PNG 图片**、放大与刷新；官方 `present` 文件卡、Trajectory 工具事件和磁盘文件存在都不是主 Chat 大图。助手应引用工具返回的 `display_markdown`，不编造 URL。下载原文件并比对哈希。插件自动预览为 offloaded，模型可通过官方 `read_image` 和支持 image 的路由额外读图；用户画面可见、模型接收像素、模型解释正确要分开验收。

`presentation.status`、`presentation.delivery.status`、`skipped` 反映展示状态，不改变科学结果。单文件导入默认 32 MiB，单产物回传默认 64 MiB；超限保留原产物路径和跳过原因。展示失败先用 `acycle_get_run` 复用既存结果，不重新跑科学计算。

## 验收与失败记录

| 检查层 | 本机应保留的证据 |
| --- | --- |
| 安装 | 0.5.0 wheel/npm 哈希、安装解释器、12 shared / 13 native / 10 skills |
| 实际 agent | preset、persona、scoped skills、技能请求消息、解析后的 text/image 能力；不能只看全局注册器 |
| MATLAB | release、工具箱、启动标记、日志、真实运行结果和来源哈希 |
| 科学流程 | 实际参数、输入 SHA、运行 ID、原函数来源、产物；六操作分别记录 |
| 调谐 | 频带、完整周期、相位、锚点、控制点、端点策略；原 proxy 时间诊断与调谐假设分离 |
| 对话 | 独立用户提示与回复、会话 ID、澄清、基线/子运行及参数保持 |
| 图件 | 主 Chat img 成功加载、放大、刷新、原文件下载哈希；模型读图另记 |
| 科学解释 | 审查完整工具轨迹与文字；已有 MATLAB 能力的数值 QA 不得迁移到 Python |

doctor 失败日志持久保存在 `.acycle/diagnostics/doctor-<时间>-<唯一ID>/`，科学运行保存在 `.acycle/runs/<run_id>/`；保留 `matlab-launch.json`、`matlab.log`、请求、结果与启动标记。默认启动时限 180 秒、科学调用总时限 3600 秒。首次 MATLAB 启动失败后先读记录并定位原因，不自动重试、不从 sandbox shell 绕过桥、不删除失败证据。修复具体原因后的人工重试另建新记录。

本版状态看 [validation/v0.5/ACCEPTANCE.md](../validation/v0.5/ACCEPTANCE.md)。正式无 Key Web fixture [main-chat-final-fixture.json](../validation/v0.5/web/main-chat-final-fixture.json) 已验证主 Chat 两张既存 MATLAB 图、放大、刷新和 PNG/CSV/MAT/FIG 原字节下载；fixture 是 text-only scripted provider，没有调用真实模型或重算科学，也没有在用户 macOS Desktop 上验证。新的真实模型、MATLAB 和完整演示结果只能按各自正式回执表述。

真实模型图像验收还记录了两次 `read_image` 保留像素并通过官方 Files API 上传；原 live runner 的懒加载等待超时仍保留为失败。随后 [同会话浏览器重放](../validation/v0.5/web/main-chat-live-browser-replay.json) 已通过主 Chat、放大、刷新及原文件下载，没有新增模型请求、工具调用或科学计算。它证明该路由的图像传输和 Web 交付，不代表数值解释正确或用户的 Mac Desktop 已测试。

0.4 历史真实会话 [conversation-evaluation.md](../validation/v0.4/conversation-evaluation.md) 和 [interpretation-review.json](../validation/v0.4/interpretation-review.json) 保留：Newark 两轮核心完成但解释有误；SWA 两轮方法保持完成但 NumPy 数值 QA 越界；PETM 第二个 8 m/4 m 分支不可解析、没有第二图；未知元数据先澄清但有过度推断。它们不证明 0.5 新调谐功能，不能改写成全部通过。

论文差异仍须保留：Lavernock 峰约 0.82125 m 接近论文 0.81 m，但 5% FDR 未复现；PETM 首轮约 26.43 cm/kyr、校正 p≈0.103948，按原日志另跑约 28.93 cm/kyr、校正 p≈0.66967、仅 4/6 目标可解析，两者均未达到 8–15 cm/kyr 判据；Cambrian 只有预算缩减流程。不要归因于版本后停止溯源，或换参数掩盖失败。详见 [PAPER_VALIDATION.md](PAPER_VALIDATION.md)。

本机报告每项标记 `passed`、`failed`、`not_run` 或 `needs_human_clarification`，区分模拟、真实模型、MATLAB 科学、浏览器显示和论文定量复现。回传操作系统、版本、去除秘密的 doctor/运行回执和日志即可；不回传 API Key、许可证秘密、Web token 或无关私有文件。纯本地计算不依赖 GitHub Actions。
