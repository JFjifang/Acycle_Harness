# Acycle Harness 0.5.1 用户文档

本工具把 Acycle 的核心 MATLAB 分析能力接到 Codex 和 DeepSeek Harness。模型负责理解问题、选择参数和解释结果；Python 负责工具接口、输入快照、文件传输和运行记录；科学计算、图形、CSV/MAT/PNG/FIG 输出在 MATLAB 中完成。原函数来源和版本写入每次运行。缺少 MATLAB 或所需函数时会报错，不会自动改用 Python 近似算法。

首次本地测试按“安装 → doctor → Desktop 插件 → 实际会话”进行；逐项 smoke 用于需要时的诊断。可直接交给本地 Codex/Harness 的交接文本见 [LOCAL_HANDOFF.zh-CN.md](LOCAL_HANDOFF.zh-CN.md)。0.5.1 版 Python/MCP 提供 **12 个工具**，Harness 加附件导入工具共 **13 个工具**，配套 **10 个 skills**。六项科学操作是 mini robot、SWA、COCO、eCOCO、Interpolation Pro 和周期极值调谐。

本版面向 **官方 Harness 0.2.1-rc.3**，这是 2026-10-25 核对的最新官方 release。更新 Desktop 后直接安装原生插件、选择 `Acycle MATLAB` agent；Desktop 自带运行时，不需额外安装 Node。项目 Web 模式另需 Node.js ≥24.9.0。新增适配与验证见 [0.5.1 验收记录](../validation/v0.5.1/ACCEPTANCE.md)，历史完整科学与会话证据保留在 [0.5 验收记录](../validation/v0.5/ACCEPTANCE.md)。

## 1. 安装条件与目录

| 项目 | 要求 |
| --- | --- |
| Python | 3.10 或更新；建议独立虚拟环境 |
| MATLAB | 已安装、可以运行 `-batch` 且有可用许可证；CI 使用 R2024b，其他版本须本地验证 |
| MATLAB 工具箱 | Signal Processing、Statistics and Machine Learning、Curve Fitting；doctor 会实际检查关键函数 |
| Acycle | 独立源码目录，验证参考提交 `dcba4279168745b563e0535b954297023dd62fc7` |
| Codex 路径 | 支持 stdio MCP 的本地 Codex；不需要 DeepSeek API Key 来使用 Acycle MCP |
| DeepSeek Harness | 官方 0.2.1-rc.3 Desktop 自带运行时；可选 Web 模式需要 Node.js ≥24.9.0；模型在宿主中配置 |

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
# 或：python -m pip install dist/acycle_deepseek-0.5.1-py3-none-any.whl
export ACYCLE_ROOT=/absolute/path/acycle
export ACYCLE_BACKEND=local
export MATLAB_EXECUTABLE=/Applications/MATLAB_R2024b.app/bin/matlab
# Linux 示例：/usr/local/MATLAB/R2024b/bin/matlab
export ACYCLE_MATLAB_TIMEOUT=3600
export ACYCLE_MATLAB_STARTUP_TIMEOUT=180
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
$env:ACYCLE_MATLAB_STARTUP_TIMEOUT = '180'
```

后续示例中的 `python` 在 Windows 可替换为 `.\.venv\Scripts\python.exe`。不要混用 WSL Python 路径与 Windows MATLAB 文件路径；先在同一操作系统内完成测试。

检查配置，并实际启动一次 MATLAB：

```sh
python local/install_check.py --workspace . --output local-validation/install.json
python local/doctor.py --workspace . --run-matlab --output local-validation/doctor.json
```

`install_check.py` 使用当前虚拟环境的隔离 Python 子进程核对 0.5.1、12 个共享工具、MATLAB 桥与实际 MCP 调用；存在交付包时还核对 wheel/npm 校验和及安装文件。它不调用模型 API 或 MATLAB，也不修改客户端配置。它与 doctor 分别检查软件安装和 MATLAB 运行条件。所有指定回执使用新路径，避免覆盖旧结果。

doctor 不会安装 MATLAB、改许可证或修改 Acycle。未加 `--run-matlab` 时只做静态检查，`configuration_detected` 不代表许可证可用。`runtime_ready` 表示 MATLAB 已启动且关键函数可见，也不代替后续科学分析测试。需要完整方法回归时，可从源码根目录运行：

```matlab
addpath('matlab');
run_validation(getenv('ACYCLE_ROOT'), fullfile(pwd,'local-validation','matlab-full'));
```

输出目录须为新的目录，避免防覆盖检查把重复运行当作错误。当前云端验收证明的是 Linux/Actions MATLAB 执行；macOS、Windows 和你自己的许可证环境需要上述本地测试。

## 3. 输入与公共工具

科学输入是两列数值文本（CSV/TXT/DAT/TSV）：第一列为深度或时间坐标，第二列为 proxy。文件必须位于指定工作区或 `ACYCLE_ROOT` 内。Excel 可先按明确的 sheet、行、列导出为两列文本；这种文件转换可以用 Python，但不应在转换时悄悄滤波、平滑或改动单位。

GitHub Actions 后端另有传输限制：初始文件不超过 1 MiB，并且 gzip 编码后的完整 workflow 请求不超过 60,000 字符。0.5 对**同一仓库前次运行中已注册、字节未改变的产物**自动使用 artifact 引用，避免把较大的过滤曲线重新塞进请求；原始字节、列数和精度保持不变，worker 核对来源 workflow、ZIP 与输入哈希及成员路径，1 MiB 文件上限仍适用。未注册的大初始输入仍受上述编码限制，应使用本地 MATLAB；过期 artifact 或文件变化会明确报错，不能靠删掉包络列或降低精度绕过。详情见 [GITHUB_ACTIONS.md](GITHUB_ACTIONS.md)。

| 工具 | 用途 |
| --- | --- |
| `acycle_capabilities` | 查看已配置后端与支持方法；不能单凭此结果认定 MATLAB 已执行 |
| `acycle_inspect` | 文件尺寸、哈希、文本预览；不是科学质量检验 |
| `acycle_analyze` | mini robot：预处理、MTM/AR(1)、EvoFFT，可选滤波/包络/年龄转换 |
| `acycle_swa` | 原 Acycle SWA：Smoothed Window Averages，平滑窗口平均及原 FDR 结果 |
| `acycle_coco` | 原 Acycle COCO：在给定目标周期和沉积速率网格上进行分析 |
| `acycle_ecoco` | 原 Acycle eCOCO：以完整深度窗口重复分析，保留位置变化 |
| `acycle_interpolate_pro` | 原 Interpolation Pro 回调：九种 MATLAB 插值方法，网格、缺口和端点策略 |
| `acycle_tune` | 原 getpks 极值和 depthtotime：显式周期/相位/锚点的相对或绝对时间模型 |
| `acycle_rerun` | 对已有运行应用参数修改，保留输入、其他设置与分析类型，生成独立子运行 |
| `acycle_sensitivity` | 基于已完成运行改变一个参数，生成独立子运行 |
| `acycle_compare` | 对照已保存参数、MATLAB summary、来源和输出 |
| `acycle_get_run` | 读取已保存运行 |

Harness 还提供 `acycle_import_attachment`，将当前会话授权的文件附件导入研究工作区。它属于 Harness 原生接入，不在 Python CLI 或 Codex MCP 的 12 个公共工具中。Codex 使用工作区内的数据路径；其客户端附件机制需要按实际客户端单独验证。

### 功能覆盖与兼容边界

| 科学操作 | 已桥接的具体功能 | 主要边界 / 来源 |
| --- | --- | --- |
| mini robot：预处理 | MATLAB 清理、排序、重复值处理；LOWESS/LOESS 及稳健版本、线性/均值/不去趋势；等距插值、原坐标截取 | `acycle_analyze`；不是完整 GUI 数据编辑器，数值 QA 在 MATLAB |
| mini robot：频谱 | 原 MTM、多种原 AR(1) 背景拟合和对应阈值、明确显示/拟合上限 | 默认 mini robot 流程；最强谱峰不自动成为轨道解释 |
| mini robot：演化/滤波 | EvoFFT；Gaussian 或 Taner/Hilbert 滤波与包络；MATLAB 图件与数组 | 显式窗口、步长、频带；不等同于任意 wavelet 或 Acycle 全部谱方法 |
| mini robot：时间转换 | 显式 cm/kyr 速率、深度—年龄控制点、或完成的 `tuning_run_id` | 目标周期、年龄和单位需要用户事实；调谐后的周期不是独立验证 |
| SWA | 原 Lomb–Scargle（保留不等距）和 MTM（均匀采样）的 Smoothed Window Averages 与 FDR | 原函数 `specswafdr` / `spectralswafdr`；阈值 NaN 不代表显著 |
| COCO | adaptive / phase_averaged；用户周期或原 `calculate_orbit9`；原 Monte Carlo；背景选项、相关类型、切片与显式 dt | adaptive 需要 9 个目标，phase_averaged 为 2–9；返回可解析目标数与原统计输出 |
| eCOCO | adaptive / blocked / interleaved；完整物理窗口；速率图和逐窗结果 | 9 个目标；不填补边缘窗口；保留不可解析失败，不能生成虚构速率图 |
| Interpolation Pro | linear、nearest、next、previous、pchip、cubic、v5cubic、makima、spline；中位步距默认值；缺口插值/置零；GUI/严格网格端点 | 提取 `interpolationGUI.m` 数值回调；缺口置零须显式，插值不增加独立信息 |
| 周期极值调谐 | 原 `getpks` 峰/谷/交替极值；显式完整周期、相位、锚点；原 `depthtotime`；trim/显式线性外推/error | 自动候选控制点需地质审查；不覆盖交互调谐 GUI、漏周期恢复或完整年龄误差模型 |
| 通用可追溯性 | 六操作的不可覆盖运行、rerun/敏感性、来源哈希、MATLAB 数组与图、附件与主 Chat 展示 | 工程完成、方法对照和论文定量复现分别验收 |

各桥接来源见 [UPSTREAM_COMPATIBILITY.md](UPSTREAM_COMPATIBILITY.md)、[SWA.md](SWA.md)、[COCO.md](COCO.md) 与 [INTERPOLATION_TUNING_SOURCES.md](INTERPOLATION_TUNING_SOURCES.md)。直接调用原函数和提取耦合 GUI 回调会明确区分；升级 Acycle 后应重新核对原文件哈希并运行对照，不能假定所有未来版本自动兼容。没有列出的 GUI 功能不应由模型承诺已经桥接。

专用 Web 研究预设提供 Acycle、文件读取和展示工具，没有默认开放通用 shell。需要现场 Python 转换或超出当前接口的开发时，可使用本地 Codex，或给该 Harness agent 明确配置开发工具；应继续保留其 Acycle 插件、技能与 MATLAB 后端。Python 可以做文件/接口及 Acycle 未实现的扩展，已有 Acycle 科学计算仍优先桥接回 MATLAB。安装包不会自动把一个未知需求替换成 Python 数值实现。

查看当前安装版本的完整参数 schema：

```sh
python -m acycle_deepseek.cli --workspace . tools
python -m acycle_deepseek.cli --workspace . call acycle_analyze --arguments-file examples/paper_petm.json
```

`examples/paper_petm.json` 指向随完整包提供的论文数据；npm 插件本身不携带整个 benchmark 数据集。原始测量行数看 `summary.input_rows`，mini robot/SWA 的处理后点数看 `summary.processed_rows`；COCO 的预处理详情看 `summary.preparation`。`acycle_inspect.line_count` 是文件结构统计，不能代替 MATLAB 的数据点数。

## 4. 可选：Newark 与各方法的诊断测试

以下脚本用于逐项检查，不是开始会话的前置要求。它们直接读取参考 Acycle 自带 `Example-LateTriassicNewarkDepthRank.txt`，无需复制路径到 JSON。`--dry-run` 只展示请求；去掉后才调用 MATLAB。

```sh
python local/smoke.py --workspace . --case all --dry-run
python local/smoke.py --workspace . --case analyze
python local/smoke.py --workspace . --case swa
python local/smoke.py --workspace . --case coco --nsim 19
python local/smoke.py --workspace . --case ecoco --nsim 19
python local/smoke.py --workspace . --case interpolate_pro
python local/smoke.py --workspace . --case tune
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

### Interpolation Pro 与周期调谐

独立预处理可调用 `acycle_interpolate_pro`，例如 `parameters={"method":"linear","dt":1,"coordinate_unit":"m","gap_policy":"interpolate","endpoint_policy":"strict_grid"}`。`dt` 以输入坐标单位表示；省略时沿用原 GUI 中位间隔。`gap_policy=zero` 是原 GUI 的显式缺口置零选项，阈值为 `dt * gap_multiplier`（默认 10）；这些零是合成值，会影响谱分析。`gui` 保留原端点回退，`strict_grid` 拒绝步距大于全记录跨度时的两端点回退。保存的 `interpolated_csv` 可继续送到 MATLAB 工具。

调谐先对深度 proxy 做有依据的 MATLAB 带通，再把该运行的 `filtered_csv`（两列，或第三列为未使用的包络）送给 `acycle_tune`。必须明确 `period_kyr`、`anchor_age_kyr`、`anchor_phase`、`extrema`、`depth_unit`；例如公开 Newark 演示采用 48–80 m 的示例频带、假设完整周期 405 kyr、第一峰相对时间 0、`extrema=peaks`、`endpoint_policy=trim`。这不是由数据自动测得 405 kyr，也没有赋予绝对年代。相邻同相位控制点间隔一个周期，交替峰谷间隔半周期；非交替或不明确极值会要求检查。

保存并审查 `control_points_csv`、`age_model_csv`、沉积速率表与三联诊断图。下一步对**原始 proxy** 调 `acycle_analyze`，在顶层提供 `tuning_run_id`，并设 `coordinate_unit=kyr`、适当的时间采样间隔与演化窗口；不要同时传 `age_model`、`sedimentation_rate` 或 `coordinate_range`。接口核对保存年龄模型的哈希，并在 MATLAB 中采用其覆盖区间与控制点。对已经滤波并调谐的曲线再找出所赋周期，不构成独立证明。

`local/smoke.py --case tune` 自动执行“原始深度分析/带通 → 405 kyr 假设下的调谐 → 原始 proxy 的时间诊断”三个 MATLAB 调用，`--dry-run` 显示动态 artifact/run 引用。5 kyr 重采样是网格选择，不代表独立时间分辨率。完整演示先验和用户提示见 [demo/newark-0.5.1/manifest.json](../demo/newark-0.5.1/manifest.json)；演示也需要保留未完成结果。

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

## 6. 接入新版 DeepSeek Harness

### 使用更新后的 Desktop

安装本版 Python wheel、完成第 2 节的 MATLAB 检查后，生成本机配置：

```sh
python local/render_config.py --workspace . --acycle-root "$ACYCLE_ROOT" --matlab "$MATLAB_EXECUTABLE"
```

在 Desktop 侧栏 **插件 → 添加插件** 中填入 `dist/dsh-acycle-0.5.1.tgz` 的本机绝对路径，点击 **安装 → 立即启用**。完全退出 Desktop，将生成的 `local/generated/desktop.preset.patch.yml` 配置项合并到 `~/.dsh/profiles/desktop/cordis.patch.yml`；自定义过 `DSH_HOME` 时使用对应目录。保留现有配置，更新 `preset-acycle` 条目即可。重新打开应用，新会话选择 **Acycle MATLAB**。

这个 patch 保存本机 Python、MATLAB、Acycle 和工作区路径，将它们传给 Acycle 子进程。从 Dock 启动不要求另行导入终端环境。模型与凭据沿用 Desktop 设置；使用支持图像的 `deepseek-flash`。生成器只写项目内片段，不直接改写客户端设置，也不保存 Key。

命令行安装是可选的：在 Desktop 菜单 **管理 dsh 命令…** 安装内置命令，首次启动并完全退出 Desktop 后执行 `dsh plugin --profile desktop add /absolute/path/to/dsh-acycle-0.5.1.tgz`，然后合并同一配置片段并重新打开应用。这里使用 Desktop 自带命令，无需为 Desktop 安装另一套 npm runtime。

### 可选：项目 Web 入口

独立 Web 路线需要 **Node.js ≥24.9.0**。安装器精确指定官方 `0.2.1-rc.3`，因为 npm 的 `latest` 标签仍指向 rc.2：

```sh
python local/deploy_harness.py --workspace . --acycle-root "$ACYCLE_ROOT" --matlab "$MATLAB_EXECUTABLE" --install
python local/check_harness.py --output local-validation/harness-composition.json
python local/launch_harness.py
```

配置、runtime 和 npm cache 默认在 `local/generated/harness-web/`。已有同版 runtime 可用 `--runtime` 复用，`--directory`、`--port` 可改位置与端口，`--force` 重生成部署配置并保留会话和结果。浏览器入口由启动器输出，默认 `127.0.0.1:3080`；启动器继承终端中的 `DEEPSEEK_API_KEY`。安装和 `check_harness.py` 不需要 Key。

Windows PowerShell 使用 `.\.venv\Scripts\python.exe`，环境变量改为 `$env:ACYCLE_ROOT`、`$env:MATLAB_EXECUTABLE`。Desktop 路线与 Web 路线共享原生插件、Acycle 工具和技能；`check_harness.py` 检查实际 Web agent 的 13 个工具、10 个 skills 及图像能力，不能替代本机 Electron 窗口验收。

官方依据：[Desktop 内置命令](https://github.com/deepseek-ai/deepseek-harness/blob/1f81c047fc48fa190a683e469daa699857e9afe8/apps/desktop/README.zh.md#bundled-command-runtime)、[插件界面](https://github.com/deepseek-ai/deepseek-harness/blob/1f81c047fc48fa190a683e469daa699857e9afe8/packages/client/ui-plugin-manager/README.zh.md)、[DeepSeek 图像输入](https://api-docs.deepseek.com/guides/vision/)。

### 加载 Newark 演示指引

Desktop 在 `render_config.py` 命令增加 `--newark-demo`，再合并生成的配置；Web 在 `deploy_harness.py` 命令增加同一选项。已有生成片段可用 `--force` 更新。

演示模式增加 `newark-relative-time-demo`，共 **13 个工具、10 个通用 skills + 1 个演示 skill**。该技能提供早期 Newark 长偏心率识别和 COCO 原始论文的方法线索。新会话上传演示数据，输入“参考 Newark 早期旋回研究和 COCO 方法，分析附件的轨道节律与沉积速率变化，并建立相对时间轴”即可。完整命令与文献见 [演示 handoff](../demo/newark-0.5.1/HANDOFF.zh-CN.md)。普通研究模式不加载这些特定地层先验。

### 上传附件与查看结果

上传两列 CSV/TXT/DAT/TSV 后，模型通过 `acycle_import_attachment` 导入当前会话的文件。唯一附件可自动选择，多文件需指定。导入保留原始字节、来源和哈希；每次导入另有来源记录。裸文件名优先匹配本会话附件，工作区内已有文件用 `./文件名` 或绝对路径。

每次分析返回 MATLAB PNG、可编辑 FIG、CSV、MAT 等实际产物。助手应把工具返回的 `display_markdown` 放入最终答案；点击主 Chat 图件可放大，并可下载原文件。`present` 文件卡和磁盘文件存在本身不证明主 Chat 图片已经显示。

插件默认最多预览 4 张图、回传 24 个文件；单文件导入上限为 32 MiB，单产物回传上限为 64 MiB。完整结果保存在运行目录。展示状态和跳过原因记录在 `presentation`；显示失败先用 `acycle_get_run` 读取已有结果，不必重新计算。

模型需要观察图形时可额外调用 `read_image`；自动回传预览本身不证明模型收到了像素。用户可见图件、模型读图和解释正确分别验证。历史官方 Web 与真实模型图像回执见 [0.5 验收记录](../validation/v0.5/ACCEPTANCE.md)，本机仍需检查图片加载、放大、刷新和下载。


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

### 连续会话的验证

实际验证应至少有两条独立用户消息：第一轮分析完成后，再修改参数。保存会话 ID、运行 ID、输入哈希、实际参数与图件，确认原结果、方法和未修改的设置保持。一次长提示里的多次工具调用不等于多轮对话。

[0.5 记录](../validation/v0.5/ACCEPTANCE.md) 包含完整 Newark 演练和独立的 eCOCO 窗口调整；[0.4 记录](../validation/v0.4/conversation-evaluation.md) 包含其他场景和已知失败。新版文献指引的实际复测情况以 [0.5.1 记录](../validation/v0.5.1/ACCEPTANCE.md) 为准，不用旧回执替代。

如需自动化真实会话，环境准备好后可运行：

```sh
node scripts/harness_conversation.mjs --runtime local/generated/harness-web/runtime --plugin local/generated/harness-web/runtime/node_modules/dsh-acycle/index.mjs --case newark_baseline_steering --workspace local-validation/newark-conversation --output local-validation/newark-conversation.json
```

它使用真实模型和 MATLAB；普通用户可直接在 Web 手工完成同样的两轮交互。其他场景、预期行为和澄清事实见 [conversation_scenarios.json](../tests/fixtures/conversation_scenarios.json)。判分规则留在测试端，不能充当模型的预期答案。会话 `completed` 后仍需核对科学输出和解释。


## 8. 保存、复查与常见问题

每次科学调用生成 `.acycle/runs/<run_id>/`。`request.json` 保存请求，`input.*` 冻结输入，`outputs/` 保存 MATLAB 文件，`result.json` 保存完成/失败状态、实际参数、summary 和 provenance。查看 `effective_parameters`，不要只看省略默认值的原始请求。敏感性分支带 `parent_run_id`。日志、失败运行和没有支持目标的窗口也属于可复现记录。

MATLAB 启动使用单次受控进程。默认启动标记时限为 `ACYCLE_MATLAB_STARTUP_TIMEOUT=180` 秒，总时限 `ACYCLE_MATLAB_TIMEOUT=3600` 秒；doctor 有对应 `--startup-timeout` / `--matlab-timeout`。doctor 的探针及失败日志保存在 `.acycle/diagnostics/doctor-<时间>-<唯一ID>/`，科学调用的日志随运行保留。首次失败不自动改走另一个 MATLAB 进程；保留启动标记、退出状态和 `matlab-launch.json`，区分启动失败与已进入科学计算后的失败。`doctor --run-matlab` 每次实际启动一次 MATLAB，不能为检查图件重复运行它。

| 现象 | 处理 |
| --- | --- |
| 找不到 MATLAB | 检查可执行文件路径，不能填 `.app` 目录本身；在同一终端跑 doctor |
| 找到 MATLAB 但启动失败 | 先读保留的 `matlab-launch.json` / `matlab.log`；检查许可证、启动时限与环境。不要循环重试、转到 sandbox shell 绕过桥或删除证据；修复明确原因后再手动重试一次 |
| MCP 一分钟后超时 | 设置 MCP 工具超时；同时检查 MATLAB 内部超时和实际 Monte Carlo 规模 |
| 模型看不到新增工具 | 核对 Python wheel 与 npm 包版本、解释器路径，刷新 MCP/重启 profile |
| Harness 附件尚未成为可分析路径 | 使用当前会话授权的附件导入；多文件时选定目标，检查附件与会话查询服务 |
| 工具完成但主 Chat 没有大图 | 核对是否选择 `Acycle MATLAB` agent、最终答案是否引用真实 `display_markdown` PNG 路径、官方文件加载是否成功；仅有 present 卡、Trajectory 或磁盘文件不够 |
| 展示状态为 `partial` | 查看 `presentation.skipped`、`warnings` 与 `delivery`；超限附件或展示失败不等于 MATLAB 计算失败，不要直接重算 |
| 输入超出工作区 | 把数据复制到研究工作区，或把工作区指向正确研究目录；不要关闭路径检查 |
| 源码哈希不匹配 | 对照是否使用另一个 Acycle 版本或本地改动；保留旧结果，单独运行升级验证 |
| SWA 的 FDR 阈值为空 | 阅读原函数输出说明；不要把 NaN 变成 0 或凭图形补阈值 |
| eCOCO 某些窗口无结果 | 检查样本数、完整窗口范围、周期支持和方法约束；保留 invalid/unsupported 信息 |
| GitHub 产物下载失败 | 本地执行不依赖 GitHub；远端模式另见 [GITHUB_ACTIONS.md](GITHUB_ACTIONS.md)，连接器缓存需要外部服务 |

对论文的验证分三层记录：原函数数值一致性、真实论文数据流程、论文定量结论。通过前两层不能自动声称完整复现第三层。已选论文与输入提取信息见 [PAPER_VALIDATION.md](PAPER_VALIDATION.md) 和 `benchmarks/`。

## 9. 论文与科学解释

论文验证分别记录原函数一致性、真实数据流程和论文定量结论。工程成功不自动证明论文结论复现；历史 SWA、PETM 和 Cambrian 案例的范围与未通过项见 [PAPER_VALIDATION.md](PAPER_VALIDATION.md)。

Newark 演示的文献线索用于形成可检验的处理方案。谱峰、周期组合、演化图、COCO 显著性及峰谷控制点都需依据实际输出审查；405 kyr 调谐后的同周期峰不是独立验证。保留不显著、不可解析和缺失窗口的结果。新增文献指引见 [Newark 演示资料](../demo/newark-0.5.1/SOURCES.md)，历史演练的科学校核见 [REVIEWED_NARRATIVE.zh-CN.md](../demo/newark-0.5.0/REVIEWED_NARRATIVE.zh-CN.md)。
