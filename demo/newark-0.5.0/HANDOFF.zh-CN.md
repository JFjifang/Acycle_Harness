# 本地接续：Newark 演示

这个目录包含原始数据、公开研究方案和专用 skill。实际计算需要配套的 Acycle Harness 0.5.0、Acycle 源代码，以及可运行的 MATLAB。它不包含 MATLAB、许可、API Key 或已生成的科学结果。

在已经安装配套运行环境的 Codex 或 DeepSeek Harness 工作区中，解压并保留本目录结构。核对 `manifest.json` 的 Acycle 提交和数据 SHA-256。Acycle 上游更新后应记录实际版本和源码差异，不能继承旧版本的数值验证结论。

## 一次安装后直接使用的 Web 演示 preset

从完整 Acycle Harness 交付包根目录运行，先按 `docs/USER_GUIDE.zh-CN.md` 建好 Python 虚拟环境并设置本机 `ACYCLE_ROOT`、`MATLAB_EXECUTABLE`。以下生成器把公开演示 skill 挂到真实 `acycle` agent preset，每个新会话都可发现它，不需要重复粘贴工具步骤。

```sh
python local/deploy_harness.py --workspace . --acycle-root "$ACYCLE_ROOT" --matlab "$MATLAB_EXECUTABLE" --directory local/generated/newark-web --port 3081 --newark-demo --install
python local/check_harness.py --deployment local/generated/newark-web/deployment.json --output local-validation/newark-agent-composition.json
python local/launch_harness.py --deployment local/generated/newark-web/deployment.json
```

PowerShell 使用本机虚拟环境 Python，变量改为 `$env:ACYCLE_ROOT` / `$env:MATLAB_EXECUTABLE`。启动进程继承运行环境中的模型 Key，生成文件不保存其值。默认普通部署不加载此演示；只有显式 `--newark-demo` 才启用。该模式仍有 13 个原生工具、10 个通用 Acycle skills，另加 1 个 `newark-relative-time-demo`，总共 11 个 scoped skills；无 Key 检查会核对技能实际进入 agent 请求。配置回执记录 manifest、SOURCES、skill 和只读 provider 的哈希，旧 Desktop 保持不变。

打开启动输出中的本机 Web 地址，在 `acycle` preset 新会话上传下述数据并发送简短提示即可。此模式属于有公开工作流辅助的演示（preset-assisted），不是无先验的盲测。数值、真实模型、主 Chat 图件和研究解释仍分别验收。

## Codex 或已有会话的显式接续

把下面这段交给本地代理作为一次性项目接续说明；随后即可只提供数据和简短研究目标：

> 当前目标是运行已选择的 Newark 演示。请读取本演示目录中的 README.zh-CN.md、manifest.json、SOURCES.md，以及 skills/newark-relative-time-demo/SKILL.md，并将该 skill 用于这次会话。它是公开的工作流与研究假设，不是通用数据分析默认值。使用已安装的 Acycle 0.5.0 工具；所有科学计算、控制点提取、插值、调谐和图件都在 MATLAB 中完成。保留原始文件与已有运行，结果不足时如实说明；不要用 Python 重算或用旧结果冒充本轮输出。请先确认工具和 MATLAB 后端可用，再等待我上传本目录的 Newark 数据并给出研究目标。不要请求或打印 API Key。

然后上传 `data/Example-LateTriassicNewarkDepthRank.txt`，发送：

> 按 Newark 演示方案，对附件完成从深度记录到相对时间轴的分析，并评估可靠性。

Codex 使用工作区路径时，可改为“对本目录 data 中的 Newark 文件……”；这是文件访问方式的区别，科学方案相同。DeepSeek Harness 的附件导入需要当前会话中的真实文件授权。不要把另一会话的附件 ID 复制到这里。

代理开始前应已具备本地 MATLAB 可执行路径、`ACYCLE_ROOT` 和配套 Python 环境。使用远程 MATLAB 后端时，应已配置对应仓库及授权。API 凭据继续由用户的运行环境提供，不能写入演示包、prompt、日志或 manifest。

首次本地运行至少确认：完整流程实际返回结果；时间域诊断链接到本轮调谐控制点和原始代理指标；关键图能在当前客户端显示并下载；一次窗口或相位追问保留原方法和原结果。后端运行成功不自动证明客户端已显示图像，方案文件也不自动证明完整流程已通过。

如使用发布者提供的专用演示配置自动加载此 skill，仍保留 manifest 可见，并在首次响应中说明核心假设。不要将上述项目接续说明或内部日志作为研究结果长篇输出给最终用户。
