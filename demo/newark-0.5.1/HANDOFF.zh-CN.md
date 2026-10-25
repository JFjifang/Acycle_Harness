# 本地接续：Newark 演示

这个目录包含原始数据、论文方法线索、公开研究方案和专用 skill。实际计算需要配套的 Acycle Harness 0.5.1、Acycle 源代码，以及可运行的 MATLAB。交付包另附明确标注的 0.5.0 排练结果；不附 MATLAB、许可或 API Key。0.5.1 更新了文献上下文与短提示，保留原数值预设，尚未重新进行完整模型会话排练。

在已经安装配套运行环境的 Codex 或 DeepSeek Harness 工作区中，解压并保留本目录结构。核对 `manifest.json` 的 Acycle 提交和数据 SHA-256。Acycle 上游更新后应记录实际版本和源码差异，不能继承旧版本的数值验证结论。

## 更新后的 Desktop：安装一次即可使用

先按 [本地 handoff](../../docs/LOCAL_HANDOFF.zh-CN.md) 安装配套 Python wheel、检查本机 MATLAB。使用已更新的官方 Harness **0.2.1-rc.3 Desktop**，它自带运行时，无需额外安装 Node。

在完整交付包根目录生成演示配置：

```sh
python local/render_config.py --workspace . --acycle-root "$ACYCLE_ROOT" --matlab "$MATLAB_EXECUTABLE" --newark-demo
```

在 Desktop 侧栏 **插件 → 添加插件** 中填入 `dist/dsh-acycle-0.5.1.tgz` 的本机绝对路径，安装并立即启用。完全退出应用，把生成的 `local/generated/desktop.preset.patch.yml` 配置项合并到 `~/.dsh/profiles/desktop/cordis.patch.yml`（自定义 `DSH_HOME` 则使用对应目录），保留其他配置。重新打开应用，新会话选择 **Acycle MATLAB**；沿用 Desktop 中已配置的图像模型与凭据。

配置已写入 Acycle 子进程的 Python/MATLAB/Acycle 路径，从 Dock 启动也不需要额外导入终端环境。模型 Key 不保存在生成文件里。普通模式有 13 个工具、10 个通用 skills；`--newark-demo` 再加载 `newark-relative-time-demo`，共 11 个 skills，并保存公开资料来源哈希。每个新会话都可发现演示技能，无需重复粘贴工具步骤。

## 可选：项目 Web 演示入口

需要独立 Web 入口时，准备 Node.js ≥24.9.0 后运行：

```sh
python local/deploy_harness.py --workspace . --acycle-root "$ACYCLE_ROOT" --matlab "$MATLAB_EXECUTABLE" --directory local/generated/newark-web --port 3081 --newark-demo --install
python local/check_harness.py --deployment local/generated/newark-web/deployment.json --output local-validation/newark-agent-composition.json
python local/launch_harness.py --deployment local/generated/newark-web/deployment.json
```

PowerShell 使用本机虚拟环境 Python，变量改为 `$env:ACYCLE_ROOT` / `$env:MATLAB_EXECUTABLE`。Web 启动器继承终端中的模型凭据，输出本机访问地址；安装器精确指定已核验的 rc.3。上述无 Key 检查验证实际 agent 组合，不代表本机 Electron 窗口或科学结果已经通过。

两条入口都使用公开方案辅助演示（preset-assisted）。在新会话上传下述数据并发送简短提示即可；数值、真实模型、图件显示和研究解释分别验收。

## Codex 或已有会话的显式接续

把下面这段交给本地代理作为一次性项目接续说明；随后即可只提供数据和简短研究目标：

> 当前目标是运行已选择的 Newark 演示。请读取本演示目录中的 README.zh-CN.md、manifest.json、SOURCES.md，以及 skills/newark-relative-time-demo/SKILL.md，并将该 skill 用于这次会话。结合早期 Newark 旋回研究与 Li 等（2018）的 COCO 方法，检查周期层级、沿剖面的变化，以及候选速率的相关性、校正显著性和分辨项数。文献提供方法线索，不能充当本轮的数值答案；当前现代算法及快速预算与历史论文的差异已列在 SOURCES。使用已安装的 Acycle 0.5.1 工具；所有科学计算、控制点提取、插值、调谐和图件都在 MATLAB 中完成。保留原始文件与已有运行，结果不足时如实说明。请先确认工具和 MATLAB 后端可用，再等待我上传本目录的 Newark 数据并给出研究目标。不要请求或打印 API Key。

然后上传 `data/Example-LateTriassicNewarkDepthRank.txt`，发送：

> 参考 Newark 早期旋回研究和 COCO 方法，分析附件的轨道节律与沉积速率变化，并建立相对时间轴。

Codex 使用工作区路径时，可改为“对本目录 data 中的 Newark 文件……”；这是文件访问方式的区别，科学方案相同。DeepSeek Harness 的附件导入需要当前会话中的真实文件授权。不要把另一会话的附件 ID 复制到这里。

代理开始前应已具备本地 MATLAB 可执行路径、`ACYCLE_ROOT` 和配套 Python 环境。使用远程 MATLAB 后端时，应已配置对应仓库及授权。API 凭据继续由用户的运行环境提供，不能写入演示包、prompt、日志或 manifest。

首次本地运行至少确认：完整流程实际返回结果；时间域诊断链接到本轮调谐控制点和原始代理指标；关键图能在当前客户端显示并下载；一次窗口或相位追问保留原方法和原结果。后端运行成功不自动证明客户端已显示图像，方案文件也不自动证明完整流程已通过。

如使用发布者提供的专用演示配置自动加载此 skill，仍保留 manifest 可见，并在首次响应中说明核心假设。不要将上述项目接续说明或内部日志作为研究结果长篇输出给最终用户。
