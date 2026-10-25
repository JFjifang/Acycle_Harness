# 本地部署与续测 handoff（0.5.1）

解压后，把 [local/HANDOFF_PROMPT.txt](../local/HANDOFF_PROMPT.txt) 交给本机 Codex 或 DeepSeek Harness 即可。助手应按本机路径安装、检查 MATLAB、启动 Harness，再在真实会话中验证数据和图件。

本版面向 **官方 Harness 0.2.1-rc.3**，这是 2026-10-25 核对的最新官方 release。你更新 Desktop 后，可直接安装本版原生插件并选择 `Acycle MATLAB` agent；Desktop 自带运行时，无需额外安装 Node。项目 Web 入口作为可选路线。

## 1. 安装 Python 接口并检查 MATLAB

在解压后的项目目录运行以下命令。MATLAB、许可证、工具箱和 Acycle 源码需本机已有；参考 Acycle 提交为 `dcba4279168745b563e0535b954297023dd62fc7`。将示例路径换成本机路径，`ACYCLE_ROOT` 应包含 `code/` 与 `data/`。

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install dist/acycle_deepseek-0.5.1-py3-none-any.whl
export ACYCLE_ROOT=/absolute/path/to/acycle
export ACYCLE_BACKEND=local
export MATLAB_EXECUTABLE=/Applications/MATLAB_R2024b.app/bin/matlab
python local/install_check.py --output local-validation/install.json
python local/doctor.py --run-matlab --output local-validation/doctor.json
python local/render_config.py --workspace . --acycle-root "$ACYCLE_ROOT" --matlab "$MATLAB_EXECUTABLE"
```

Linux 的 MATLAB 路径按实际安装设置，例如 `/usr/local/MATLAB/R2024b/bin/matlab`。Windows PowerShell 使用 `.\.venv\Scripts\python.exe`，环境变量采用 `$env:ACYCLE_ROOT`、`$env:MATLAB_EXECUTABLE`；完整示例见 [用户文档](USER_GUIDE.zh-CN.md#2-安装-python-接口与设置-matlab)。

## 2. 安装到更新后的 Desktop

1. 在 Harness 侧栏打开 **插件 → 添加插件**，填入 `dist/dsh-acycle-0.5.1.tgz` 的本机绝对路径，点击 **安装 → 立即启用**。
2. 完全退出 Desktop。将刚生成的 `local/generated/desktop.preset.patch.yml` 中的配置项合并到 `~/.dsh/profiles/desktop/cordis.patch.yml`；若设置过 `DSH_HOME`，使用该目录下的同一路径。保留已有配置，只更新 `preset-acycle` 条目。这一步可交给本地 Codex 完成。
3. 重新打开 Desktop，在新会话选择 **Acycle MATLAB**，模型沿用 Desktop 中已配置的 DeepSeek 模型与凭据，选择支持图像的 `deepseek-flash`。

生成配置已包含本机 Python、MATLAB、Acycle 和研究工作区路径，供 Acycle 子进程使用。从 Dock 启动也无需另外导入终端环境。配置不保存模型凭据；`render_config.py` 只生成片段，不直接改写用户的 Harness 配置。

如偏好命令行，可在 Desktop 菜单 **管理 dsh 命令…** 安装它自带的命令，首次打开并完全退出 Desktop 后执行：

```sh
dsh plugin --profile desktop add /absolute/path/to/dsh-acycle-0.5.1.tgz
```

使用 Desktop 自带的命令管理其插件。官方依据见 [Desktop 内置命令](https://github.com/deepseek-ai/deepseek-harness/blob/1f81c047fc48fa190a683e469daa699857e9afe8/apps/desktop/README.zh.md#bundled-command-runtime) 与 [插件管理界面](https://github.com/deepseek-ai/deepseek-harness/blob/1f81c047fc48fa190a683e469daa699857e9afe8/packages/client/ui-plugin-manager/README.zh.md)。

## 3. Newark 演示

Desktop 演示配置在第 1 节的 `render_config.py` 命令增加 `--newark-demo`，再合并生成的 patch。该模式在实际 agent 中加载文献与研究指引：**13 个工具、10 个通用 skills 加 1 个演示 skill**。普通研究模式为 13 个工具和 10 个 skills。已生成普通片段时，可用 `--force` 更新这些项目内片段。

上传 `demo/newark-0.5.1/data/Example-LateTriassicNewarkDepthRank.txt`，输入：

> 参考 Newark 早期旋回研究和 COCO 方法，分析附件的轨道节律与沉积速率变化，并建立相对时间轴。

收到完整回复后，再独立发送：

> 保留原结果，把 eCOCO 的窗口改成 800 米、步长改成 200 米，看看速率变化是否稳健。

文献依据、假设和详细演示步骤见 [演示 handoff](../demo/newark-0.5.1/HANDOFF.zh-CN.md)。405 kyr 是有文献背景的调谐假设；当前文件的识别证据、COCO 检验和调谐后的时间谱需分别解释。

## 可选：项目 Web 入口

使用独立 Web 入口时需要 Node.js **≥24.9.0**。安装器精确指定 Harness `0.2.1-rc.3`；npm 的 `latest` 标签仍指向 rc.2。沿用第 1 节的 Python/MATLAB 设置后执行：

```sh
python local/deploy_harness.py --workspace . --acycle-root "$ACYCLE_ROOT" --matlab "$MATLAB_EXECUTABLE" --install
python local/check_harness.py --output local-validation/harness-composition.json
python local/launch_harness.py
```

需要演示模式时在 deploy 命令增加 `--newark-demo`。已有同版 runtime 可用 `--runtime` 复用；`--directory`、`--port` 修改目录和端口。配置默认在 `local/generated/harness-web/`，`--force` 重生成部署配置并保留会话、结果。启动器输出本机浏览器入口，并继承终端中的 `DEEPSEEK_API_KEY`；安装和检查无需 Key。

## 可选：Codex 与逐项诊断

Codex 使用同一套 MATLAB 桥，经 stdio MCP 提供 **12 个工具**。第 1 节还生成 `local/generated/codex-mcp.toml`；检查后仅合并 `acycle` 条目到受信任项目的 `.codex/config.toml`。

刷新 MCP 后调用 `acycle_capabilities` 并分析一个工作区文件。Codex 使用本地文件路径，不需要 Harness 专用附件导入。

需要定位具体科学操作时，运行 `python local/smoke.py --case all --dry-run` 查看请求，再选择 `analyze`、`swa`、`coco`、`ecoco`、`interpolate_pro` 或 `tune`。`tune` 包含滤波、极值调谐和原始 proxy 的时间域诊断三个 MATLAB 调用。19 次模拟用于快速检查；逐项 smoke 是可选诊断，不是启动对话的前置要求。

## 本机验收与记录

| 检查 | 预期记录 |
| --- | --- |
| 安装与 agent | 0.5.1 安装文件、12 shared / 13 native 工具、实际技能目录与模型图像能力 |
| MATLAB | doctor 的实际启动、许可证/工具箱状态、科学运行和来源记录 |
| 会话调整 | 两条独立用户消息、原结果保留、输入与方法保持、实际参数变化 |
| 图件 | 主 Chat 图片加载、放大、刷新；PNG/CSV/MAT/FIG 原文件下载 |
| 科学解释 | 依据实际输出区分候选、显著性与调谐假设；审查控制点和异常窗口 |

每次运行保存在 `.acycle/runs/<run_id>/`，doctor 诊断在 `.acycle/diagnostics/`。MATLAB 启动失败先读 `matlab-launch.json` 和 `matlab.log`，修复明确原因后再运行；图件显示失败先读取已有结果。计算、数值 QA 和作图使用 MATLAB，Python 负责接口、传输及 Acycle 未提供的辅助功能。

本版验证见 [0.5.1 验收记录](../validation/v0.5.1/ACCEPTANCE.md)。完整 Newark 演练、真实模型图像传输和官方 Web 显示的历史证据见 [0.5 验收记录](../validation/v0.5/ACCEPTANCE.md)；Desktop 的官方共享配置已单独检查；本机 Electron 窗口、MATLAB 和新版文献指引仍按实际本地结果验收。论文结论的未复现项见 [论文验证说明](PAPER_VALIDATION.md)。本机新增报告写入 `local-validation/`，标记 `passed`、`failed` 或 `not_run`，保留失败证据，不回传凭据或无关私有文件。
