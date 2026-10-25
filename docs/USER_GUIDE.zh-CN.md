# Acycle Harness 0.4 用户文档

本工具把 Acycle 的核心 MATLAB 分析能力接到 Codex 和 DeepSeek Harness。模型负责理解问题、选择参数和解释结果；Python 负责工具接口、输入快照、文件传输和运行记录；科学计算、图形、CSV/MAT/PNG/FIG 输出在 MATLAB 中完成。原函数来源和版本写入每次运行。缺少 MATLAB 或所需函数时会报错，不会自动改用 Python 近似算法。

首次本地测试建议按“安装 → doctor → Newark smoke → 接入客户端 → 上传数据并连续对话”的顺序进行。可直接交给另一个本地 Codex/Harness 会话执行的交接文本见 [LOCAL_HANDOFF.zh-CN.md](LOCAL_HANDOFF.zh-CN.md)。0.4 版的 Python/MCP 提供 10 个工具，Harness 另有附件导入工具，合计 11 个；8 个 skills 不变。具体测试结果应查阅 `validation/` 中对应版本的验收记录。0.2/0.3 的计算和工具调用证据不能代替 0.4 的附件、图件回传及真实用户多轮会话验收。

## 1. 安装条件与目录

| 项目 | 要求 |
| --- | --- |
| Python | 3.10 或更新；建议独立虚拟环境 |
| MATLAB | 已安装、可以运行 `-batch` 且有可用许可证；CI 使用 R2024b，其他版本须本地验证 |
| MATLAB 工具箱 | Signal Processing、Statistics and Machine Learning、Curve Fitting；doctor 会实际检查关键函数 |
| Acycle | 独立源码目录，验证参考提交 `dcba4279168745b563e0535b954297023dd62fc7` |
| Codex 路径 | 支持 stdio MCP 的本地 Codex；不需要 DeepSeek API Key 来使用 Acycle MCP |
| DeepSeek Harness 路径 | 对照官方 Harness 0.2.1-rc.3；该版本要求 Node.js ≥24.9，模型由 Harness 单独配置 |

MATLAB Optimization Toolbox 并非此安装清单中的必要项；上游 `redconfML` 在不能使用其优化器时自带网格搜索路径。本桥还检查优化器是否返回无效拟合，并记录实际采用的路径。不同 MATLAB/toolbox 环境可能使所走路径不同，比较结果时应读 `provenance`，不要只比较一个峰值。

建议保留三个目录：项目源代码 `Acycle_Harness/`、Acycle 原始代码 `acycle/`、研究工作区。首次测试可直接把 `Acycle_Harness/` 当工作区，以使用随包提供的 benchmark 数据。`ACYCLE_ROOT` 指向包含 `code/`、`data/` 的 Acycle 根目录，不是 `code/` 子目录。

取得并固定参考 Acycle：

```sh
git clone https://github.com/mingsongli/acycle.git /absolute/path/acycle
git -C /absolute/path/acycle checkout dcba4279168745b563e0535b954297023dd62fc7
```

已有 Acycle 工作目录中若有自己的修改，请保留原目录，另建参考 checkout。初始 smoke 使用固定版本；以后升级按 [UPSTREAM_COMPATIBILITY.md](UPSTREAM_COMPATIBILITY.md) 做原函数对照。

## 2. 安装 Python 接口与设置 MATLAB

以下命令在解压后的完整交付目录内运行。源码安装与 wheel 安装二选一；本地调试推荐前者，核对交付包推荐后者。

macOS/Linux：

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
# 或：python -m pip install dist/acycle_deepseek-0.4.0-py3-none-any.whl
export ACYCLE_ROOT=/absolute/path/acycle
export ACYCLE_BACKEND=local
export MATLAB_EXECUTABLE=/Applications/MATLAB_R2024b.app/bin/matlab
# Linux 示例：/usr/local/MATLAB/R2024b/bin/matlab
export ACYCLE_MATLAB_TIMEOUT=3600
```

Windows PowerShell：

```powershell
py -3 -m venv .venv
# 可以不激活，始终使用虚拟环境的 Python，避免执行策略影响。
.\.venv\Scripts\python.exe -m pip install .
$env:ACYCLE_ROOT = 'C:\research\acycle'
$env:ACYCLE_BACKEND = 'local'
$env:MATLAB_EXECUTABLE = 'C:\Program Files\MATLAB\R2024b\bin\matlab.exe'
$env:ACYCLE_MATLAB_TIMEOUT = '3600'
```

后续示例中的 `python` 在 Windows 可替换为 `.\.venv\Scripts\python.exe`。不要混用 WSL Python 路径与 Windows MATLAB 文件路径；先在同一操作系统内完成测试。

检查配置，并实际启动一次 MATLAB：

```sh
python local/doctor.py --workspace . --run-matlab --output local-validation/doctor.json
python local/smoke.py --workspace . --case analyze
```

doctor 不会安装 MATLAB、改许可证或修改 Acycle。未加 `--run-matlab` 时只做静态检查，`configuration_detected` 不代表许可证可用。`runtime_ready` 表示 MATLAB 已启动且关键函数可见，也不代替后续科学分析测试。完整数值测试从源码根目录运行：

```matlab
addpath('matlab');
run_validation(getenv('ACYCLE_ROOT'), fullfile(pwd,'local-validation','matlab-full'));
```

输出目录须为新的目录，避免防覆盖检查把重复运行当作错误。当前云端验收证明的是 Linux/Actions MATLAB 执行；macOS、Windows 和你自己的许可证环境需要上述本地测试。

## 3. 输入与公共工具

科学输入是两列数值文本（CSV/TXT/DAT/TSV）：第一列为深度或时间坐标，第二列为 proxy。文件必须位于指定工作区或 `ACYCLE_ROOT` 内。Excel 可先按明确的 sheet、行、列导出为两列文本；这种文件转换可以用 Python，但不应在转换时悄悄滤波、平滑或改动单位。

| 工具 | 用途 |
| --- | --- |
| `acycle_capabilities` | 查看已配置后端与支持方法；不能单凭此结果认定 MATLAB 已执行 |
| `acycle_inspect` | 文件尺寸、哈希、文本预览；不是科学质量检验 |
| `acycle_analyze` | mini robot：预处理、MTM/AR(1)、EvoFFT，可选滤波/包络/年龄转换 |
| `acycle_swa` | 原 Acycle SWA：Smoothed Window Averages，平滑窗口平均及原 FDR 结果 |
| `acycle_coco` | 原 Acycle COCO：在给定目标周期和沉积速率网格上进行分析 |
| `acycle_ecoco` | 原 Acycle eCOCO：以完整深度窗口重复分析，保留位置变化 |
| `acycle_rerun` | 对已有运行应用参数修改，保留输入、其他设置与分析类型，生成独立子运行 |
| `acycle_sensitivity` | 基于已完成运行改变一个参数，生成独立子运行 |
| `acycle_compare` | 对照已保存参数、MATLAB summary、来源和输出 |
| `acycle_get_run` | 读取已保存运行 |

Harness 还提供 `acycle_import_attachment`，将当前会话授权的文件附件导入研究工作区。它属于 Harness 原生接入，不在 Python CLI 或 Codex MCP 的 10 个公共工具中。Codex 使用工作区内的数据路径；其客户端附件机制需要按实际客户端单独验证。

查看当前安装版本的完整参数 schema：

```sh
python -m acycle_deepseek.cli --workspace . tools
python -m acycle_deepseek.cli --workspace . call acycle_analyze --arguments-file examples/paper_petm.json
```

`examples/paper_petm.json` 指向随完整包提供的论文数据；npm 插件本身不携带整个 benchmark 数据集。原始测量行数看 `summary.input_rows`，mini robot/SWA 的处理后点数看 `summary.processed_rows`；COCO 的预处理详情看 `summary.preparation`。`acycle_inspect.line_count` 是文件结构统计，不能代替 MATLAB 的数据点数。

## 4. Newark 与新增方法的首次测试

以下脚本直接读取参考 Acycle 自带 `Example-LateTriassicNewarkDepthRank.txt`，无需复制路径到 JSON。`--dry-run` 只展示请求；去掉后才调用 MATLAB。

```sh
python local/smoke.py --workspace . --case all --dry-run
python local/smoke.py --workspace . --case analyze
python local/smoke.py --workspace . --case swa
python local/smoke.py --workspace . --case coco --nsim 19
python local/smoke.py --workspace . --case ecoco --nsim 19
```

默认 COCO/eCOCO smoke 使用 `middle_age_ma=210`、8–16 cm/kyr 的网格、步长 1 cm/kyr、固定 seed 1；eCOCO 用 500 m 窗口和 500 m 步长，只保留完整窗口。这些是明确标记的低成本连通/执行检查参数，不是对 Newark 年代模型的预设结论。`nsim=19` 的模拟次数不能支持精细尾部显著性判断；正式研究需根据所需 p 值精度增加模拟次数，并做网格、窗口和数据处理敏感性分析。增加到 999 次不自动构成论文复现。

### SWA

SWA 是 Smoothed Window Averages，不是 spectral weighted average，也不是小波分析。`method=lomb` 调用原始 Lomb–Scargle/SWA/FDR 路径，保留不等距坐标；该原程序自行执行其规定的去趋势、taper 和 Hanning 步骤。不要向 Lomb 路径传入 MTM 专用设置来期待改变这些内部步骤。

`method=mtm` 调用原 MTM/SWA/FDR 路径，要求均匀采样；可设 `mtm_nw`、`pad_factor` 和 `detrend`。两条路径要求至少 66 个有效点；某些短序列仍可能触发上游旧算法的窗口限制，此时报告原函数限制，不会改用另一种算法。原 FDR 列出现 NaN 可能表示没有独立拒绝阈值或阈值合并，不能解释为零阈值。参数与来源详见 [SWA.md](SWA.md)。

### COCO / eCOCO

必须明确 `depth_unit`，以及以 **cm/kyr** 表示的 `sedimentation_rate_min`、`sedimentation_rate_max`、`sedimentation_rate_step`。`middle_age_ma` 与 `orbital_periods_kyr` 二选一：前者交由 Acycle 计算该年龄的目标周期，后者显式给出以 kyr 为单位的目标。不要把以 Ma 表示的年龄与以 kyr 表示的周期混用。

COCO 默认 `method=adaptive` 调用原 adaptive9b，需要 9 个目标周期；`phase_averaged` 对接另一条原 adaptive 路径，可使用 2–9 个显式周期。eCOCO 提供 `adaptive`、`blocked`、`interleaved`，均要求 9 个目标周期；`window`、`step` 以输入深度单位表示，不能误写成 kyr。完整窗口之外不自动补零。方法之间有不同的目标分辨率与统计含义，不应仅凭曲线高度比较“哪种更显著”。

共享参数包括 `nsim`、`seed`、`correlation`（默认 Spearman，可选 Pearson）、`red_noise`、可选 `nfft` 和以 cycles/kyr 表示的 `max_frequency`。`red_noise=0` 表示不扣除背景，不是关闭 Monte Carlo；模拟次数仍由 `nsim` 控制。这与 SWA 的 reciprocal-coordinate `fmax` 不同。只有 COCO 支持 `slices` 和可选的 `dt`；`dt` 以输入深度单位指定去趋势后的等距插值间隔，省略时沿用原函数的中位采样间隔。深度统一转换为 m 后送入原算法，返回的 eCOCO 深度轴也为 m，即使输入原来是 cm 或 ft。

默认使用原算法内部线性去趋势。可选 `detrend=lowess` 或 `loess` 时必须明确 `span`（全记录比例）或 `detrend_window`（输入深度单位）的其中一个；这属于全局预处理假设，Monte Carlo 不会在每条替代序列上重新估计该趋势。blocked/interleaved 不接受这种全局非线性预处理。以 [COCO.md](COCO.md) 和当前 schema 为准；Monte Carlo 结果、支持目标数量及失效窗口都应保留，不能只导出一条看起来平滑的最优速率曲线。

## 5. 接入 Codex

本地 Codex 通过 stdio MCP 调用同一套工具，无需安装原生 Harness npm 包。先生成配置片段，检查路径，再合并到这个受信任项目的 `.codex/config.toml`；不要用片段覆盖已有配置文件。

```sh
python local/render_config.py --workspace . --acycle-root "$ACYCLE_ROOT" --matlab "$MATLAB_EXECUTABLE"
```

PowerShell 中用以下等价命令读取环境变量：

```powershell
.\.venv\Scripts\python.exe local/render_config.py --workspace . --acycle-root $env:ACYCLE_ROOT --matlab $env:MATLAB_EXECUTABLE
```

生成的 `local/generated/codex-mcp.toml` 使用当前虚拟环境的绝对 Python 路径、绝对工作区和 Acycle 路径，并把工具超时设置为 3600 秒。MCP 默认 60 秒可能不足以完成 MATLAB 启动和 Monte Carlo 分析。若需要其他时限，同时调整 `tool_timeout_sec` 和 `ACYCLE_MATLAB_TIMEOUT`。

也可以用 Codex CLI 注册用户级服务器，然后检查其配置并补上超时：

```sh
codex mcp add acycle --env ACYCLE_BACKEND=local --env "ACYCLE_ROOT=$ACYCLE_ROOT" --env "MATLAB_EXECUTABLE=$MATLAB_EXECUTABLE" -- python -m acycle_deepseek.mcp --workspace "$PWD"
codex mcp get acycle
```

CLI 示例中的 `python` 必须是已安装本包的解释器；实际部署更推荐生成片段中的绝对路径。不要同时注册同名项目级与用户级条目却不检查配置优先级。重启/刷新 MCP 后，在新会话先调用 `acycle_capabilities`，再运行一次 Newark 分析。官方配置依据：[Codex MCP 文档](https://developers.openai.com/codex/mcp/)；本地命令语法另以 `codex mcp add --help` 为准。

## 6. 接入 DeepSeek Harness

先确认 `dsh --version` 与插件声明的 `engines.dsh` 范围兼容。对已安装的官方 Harness，使用拟运行的 profile 安装原生包；Web、headless 和 Desktop 是不同 profile，安装到其中一个不会自动安装到其他 profile。

```sh
. local/generated/runtime.env.sh
dsh plugin --profile web add /absolute/path/Acycle_Harness/dist/dsh-acycle-0.4.0.tgz
dsh web
```

Windows 使用 `. .\local\generated\runtime.env.ps1`，然后执行对应 `dsh` 命令。没有全局 `dsh` 时，可使用官方 npm 入口并固定测试过的运行时版本：

```sh
npx --yes @deepseek-ai/dsh@0.2.1-rc.3 plugin --profile web add /absolute/path/dsh-acycle-0.4.0.tgz
npx --yes @deepseek-ai/dsh@0.2.1-rc.3 web
```

模型在 Harness 的 provider 设置中单独选择，官方 API 模型 ID 为 `deepseek-flash`。API Key 仅放运行环境/已有安全凭据机制，不写进这个项目、handoff 或 MCP 配置。启动 Harness 的进程必须继承 `ACYCLE_PYTHON`、`ACYCLE_ROOT`、`MATLAB_EXECUTABLE` 等设置；从桌面图标启动的应用不一定继承终端变量。

Desktop profile 由桌面程序管理：先打开一次桌面程序使其初始化，完全退出后，用该安装附带的 `dsh` 管理 `desktop` profile，再重新启动；不要用另一套 npm CLI 修改它。命令和 profile 依据：[官方 CLI 说明](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/apps/cli/README.md)。

### 上传附件与查看结果

在当前会话上传 CSV/TXT/DAT/TSV 后，模型可通过 `acycle_import_attachment` 导入工作区。无参数调用选择最近一条含文件的用户消息中的唯一文件；若该消息有多个文件，会返回 `selection_required` 和候选项，模型应根据你的指示选择。显式 `attachment_id` 也只能引用本会话用户提供的附件，不能用另一个会话的 ID 读取文件。

导入保留原始字节，保存到工作区 `.acycle/imports/<sha256>/<filename>`，并记录附件来源、会话/消息标识和哈希。普通分析请求中的 `input_path` 若匹配本会话授权附件的官方路径或无歧义文件名，也可自动导入。原上传对象不被修改；单文件默认导入上限为 32 MiB，超限会拒绝导入。原生插件需要 Harness 的附件和会话查询服务；缺少这些服务时，工作区内已有文件仍可分析，附件导入会明确报告缺失依赖。

MATLAB 图件通过官方图片/文件引用和 Markdown 链接返回。配置了官方 `present` 且存在调用 agent 时，插件还会提交最多 4 个关键交付文件；否则回执标记为 `links_only`。默认最多预览 4 张图、回传 24 个文件、递交 3 个运行的产物，单产物上限 64 MiB；完整结果仍应从相应运行目录复查。

科学执行与展示分别记录：`presentation.status` 为 `available`、`partial` 或 `paths_only`，`presentation.delivery.status` 标记 `presented`、`failed`、`links_only` 或 `not_requested`。超大产物仅跳过该附件，在 `presentation.skipped` 保留路径和原因，原始科学结果不受影响；`present` 失败也不要求重新计算，应先重新读取已有运行并修复展示问题。

图片预览面向用户，模型不会收到其像素；模型可以解释 MATLAB 返回的数值，但不能因此声称已经看过图像。请在实际 Web/Desktop 客户端打开图件，并检查文件下载内容。图片事件已发出、客户端已显示，以及用户已核对坐标和曲线，是不同的验收项目。

## 7. 用户可以怎样提出研究问题

完成安装后，预期使用方式是在 Harness 中附上两列数据，用简短提示提出分析要求，随后在同一会话中继续修改。首次输入建议说明第一列单位、代理指标和希望回答的问题；年代范围或独立控制点用于后续轨道解释，不应让模型根据谱峰自行猜出。可以先上传文件并输入：

> 这是深度—磁化率数据，第一列是 m。先看看周期结构，给我谱图，暂时不要解释为轨道周期。

等待模型完成并返回图件后，再发独立的下一条消息：

> 保留刚才的结果，把去趋势窗口改为原来的两倍，再比较一次。

缺少单位、年龄范围、目标周期或沉积速率搜索依据时，模型应先检查附件中的说明；仍不足时澄清必要信息，不能默默补造科学假设。操作已经明确时应直接调用工具。用户不必输入工具名或 JSON；模型负责把需求转成参数，并说明实际采用的设置。

`acycle_rerun` 接受 `run_id`、`parameter_patch` 和可选 `label`，保留基线的冻结输入和分析类型。例如对 SWA 的修改仍运行 SWA，对 COCO 的修改仍运行 COCO；只有明确修改 `method` 才切换该类型内的方法。未修改的显式设置继续保留；确实依赖所改参数的默认值可由 MATLAB 重新计算，例如改变 eCOCO 窗口后重新确定未显式指定的 `nfft`，重置原因记录在 `steering.removed_or_reset_parameters`。可选参数的 `null` 表示移除该设置或恢复 MATLAB 默认值，但 `method`、`detrend` 必须明确选择，不能用 `null` 隐式重置。多个单参数取值可用 `acycle_sensitivity`；结果用 `acycle_compare` 对照，基线不会覆盖。

需要更完整的研究指令时，也可以使用：

> 先检查 `data/section.csv`。第一列是 m，第二列是磁化率。先运行 mini robot 和 SWA，保存参数、原函数来源、CSV、MAT、PNG、FIG。不要把谱峰直接解释为轨道周期。随后依据我给的年代范围提出 COCO 速率范围，解释目标周期和 Monte Carlo 设置，再运行明确的参数组；如需调整，保留基线并创建子运行。

steering 示例：

> 保留运行 `<run_id>`。只把 LOWESS span 改为 0.25 和 0.45，比较哪些峰和结论稳定；不要覆盖原始输入。

> 保留 COCO 基线。把速率网格加密并增加模拟次数，保持目标周期和 seed 可追溯。把探索性筛选和最终检验区分开来，不用最强的一次试验替代多次选择后的不确定性。

不在 Acycle 中的任务可以由模型写辅助 Python，例如格式转换或额外统计，但要标记额外方法及来源；后续谱分析与作图仍优先通过现有接口回到 MATLAB。需要新 MATLAB 桥时应读取已安装源码，记录提取位置，不能凭函数名猜测数值兼容。

### 连续会话的验收边界

真实会话验收需要多条独立用户消息，并保存每轮的提示、工具调用、运行 ID、参数变化和图件事件。一次长提示中要求“先分析、再修改、再比较”，即使触发多次模型请求，也不等于用户多轮对话测试。模拟模型、CLI smoke、MCP 初始化以及插件注册器测试分别验证其对应层面。

0.4 的真实 Harness 连续会话验收正在进行，现阶段不能根据 0.3 的工具回执宣称新流程已经通过。SDK 会话中的官方图片/文件事件也不等于浏览器或桌面端已经人工检查过画面；本机验收应在实际客户端打开图件和下载文件，分别记录通过、失败及未执行项目。

预先声明的场景位于 [conversation_scenarios.json](../tests/fixtures/conversation_scenarios.json)。其中用户提示和验收规则分开保存；真实模型只接收用户提示和附件，不能把预期工具、参数字段或判分规则额外塞进提示。场景不要求得到某个谱峰、显著性结果或地质速率。

| 场景 | 首轮要求 | 下一轮或预期行为 |
| --- | --- | --- |
| Newark 初步分析 | 上传完整原始数据，要求谱图和随深度变化图 | 将平滑去趋势跨度改为 25%，保留基线与其他设置并比较 |
| Lavernock 误发现率 | 保留原采样坐标，由研究要求选择 FDR 方法 | 只将图示上限改为 2 cycles/m，保留方法与完整频谱的显著性计算 |
| PETM 速率随深度变化 | 按明确年龄、速率范围、窗口和 19 次模拟做诊断 | 同时修改窗口及移动间隔，保留 eCOCO 类型、其他设置和原结果 |
| 缺少科学背景 | 上传中性文件名的无表头数据，要求速率图 | 先澄清单位、年龄/目标和速率范围；不凭隐藏数据来源猜测，不运行依赖这些前提的分析 |

## 8. 保存、复查与常见问题

每次科学调用生成 `.acycle/runs/<run_id>/`。`request.json` 保存请求，`input.*` 冻结输入，`outputs/` 保存 MATLAB 文件，`result.json` 保存完成/失败状态、实际参数、summary 和 provenance。查看 `effective_parameters`，不要只看省略默认值的原始请求。敏感性分支带 `parent_run_id`。日志、失败运行和没有支持目标的窗口也属于可复现记录。

| 现象 | 处理 |
| --- | --- |
| 找不到 MATLAB | 检查可执行文件路径，不能填 `.app` 目录本身；在同一终端跑 doctor |
| 找到 MATLAB 但启动失败 | 运行 `matlab -batch "ver"`，核查许可证、工具箱和本机登录环境 |
| MCP 一分钟后超时 | 设置 MCP 工具超时；同时检查 MATLAB 内部超时和实际 Monte Carlo 规模 |
| 模型看不到新增工具 | 核对 Python wheel 与 npm 包版本、解释器路径，刷新 MCP/重启 profile |
| Harness 附件尚未成为可分析路径 | 使用当前会话授权的附件导入；多文件时选定目标，检查附件与会话查询服务 |
| 工具完成但聊天里没有图件卡片 | 先看回传的图片/文件引用及 `links_only` 状态，再检查官方 `present` 和客户端；磁盘产物与界面显示分别核对 |
| 展示状态为 `partial` | 查看 `presentation.skipped`、`warnings` 与 `delivery`；超限附件或展示失败不等于 MATLAB 计算失败，不要直接重算 |
| 输入超出工作区 | 把数据复制到研究工作区，或把工作区指向正确研究目录；不要关闭路径检查 |
| 源码哈希不匹配 | 对照是否使用另一个 Acycle 版本或本地改动；保留旧结果，单独运行升级验证 |
| SWA 的 FDR 阈值为空 | 阅读原函数输出说明；不要把 NaN 变成 0 或凭图形补阈值 |
| eCOCO 某些窗口无结果 | 检查样本数、完整窗口范围、周期支持和方法约束；保留 invalid/unsupported 信息 |
| GitHub 产物下载失败 | 本地执行不依赖 GitHub；远端模式另见 [GITHUB_ACTIONS.md](GITHUB_ACTIONS.md)，连接器缓存需要外部服务 |

对论文的验证分三层记录：原函数数值一致性、真实论文数据流程、论文定量结论。通过前两层不能自动声称完整复现第三层。已选论文与输入提取信息见 [PAPER_VALIDATION.md](PAPER_VALIDATION.md) 和 `benchmarks/`。

## 9. 本轮论文检查的实际状态

新增 benchmark **并非全部达到论文判据**。这些未通过结果被保留，不能当作本地安装故障，也不能通过改换区间或挑选参数抹去。

| 案例 | 已得到的结果 | 应如何表述 |
| --- | --- | --- |
| Newark | 官方全记录的实际 MATLAB 流程与相关数值/图件检查已运行；细项看当前回执 | 可以报告相应接口和原函数验证，不声称重新建立整套 Newark 年代框架 |
| Weedon/Lavernock SWA | 找到约 0.82125 m 的峰，吻合论文约 0.81 m 的位置；原函数未给出支持该峰的 5% FDR 阈值 | 峰位置吻合，但预先声明的 5% FDR 条件未复现；NaN 不能解释成显著 |
| PETM COCO 首轮 | 较宽输入区间上的 2000 次模拟得到最优速率约 26.43 cm/kyr，速率搜索校正后的 p 约 0.103948；没有落入论文的 8–15 cm/kyr 区间 | 首轮未复现论文速率判据；核对原始日志后发现输入区间、插值和相关类型不一致，已按日志独立复跑并另行保留结果，不能把差异直接归因于版本 |
| PETM COCO 补充日志协议 | 2370 个处理后点、0.01 m 间隔、2000 次模拟；最大相关点约 28.93 cm/kyr，全速率网格校正 p 约 0.66967，仅解析 4/6 个周期 | 仍未达到 8–15 cm/kyr 判据；不支持据此解释地质沉积速率，保留现代实现与历史流程的差异 |
| Cambrian eCOCO | 使用论文主 Al 指标的 0–18 m 子段、缩减窗口/步长/模拟设置 | 属于预算缩减的真实数据流程验证，不是已发表整幅 eCOCO 图或完整年代学结论复现 |

本地重跑应分别保存执行状态与科学判据。若工程测试通过而论文特征检查未通过，原样报告两者；继续溯源方法版本、完整预处理和目标设定，不能把“程序成功结束”改写成“论文复现成功”。
