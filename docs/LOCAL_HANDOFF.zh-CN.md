# 本地部署与续测 handoff

适用目标：在自己的电脑用 Codex 或 DeepSeek Harness 调用本地 MATLAB，测试 Acycle Harness 0.3 的 Newark、SWA、COCO、eCOCO，并继续调整参数。本文和 `local/` 是交接材料；它们不会自动改写你现有的 Codex/Harness 配置。

## 交接包应包含什么

保留完整 ZIP 的目录结构，不要只取 npm 包：

另提供轻量独立 handoff ZIP，包含同一版本源码、安装包、文档、本地工具和提取后的 CSV。它省略出版社原始附件及历史云端大体积输出；需要审计原始附件时使用完整包，或运行 `benchmarks/prepare_paper_data.py --download` 按固定哈希取回。

| 内容 | 用途 |
| --- | --- |
| `dist/acycle_deepseek-0.3.0-py3-none-any.whl` | 安装 Python 接口和随包 MATLAB 桥 |
| `dist/dsh-acycle-0.3.0.tgz` | DeepSeek Harness 原生插件和 skills |
| `matlab/`、`src/`、`tests/` | 可检查和修改的实现；MATLAB 桥调用外部 Acycle 原函数 |
| `benchmarks/`、`examples/` | 论文原始附件/提取记录、参考输入、请求示例 |
| `docs/USER_GUIDE.zh-CN.md` | 详细安装、参数、steering 和排错说明 |
| `local/HANDOFF_PROMPT.txt` | 可以直接粘贴给本地助手的完整任务文本 |
| `local/doctor.py`、`render_config.py`、`smoke.py` | 本地自检、生成配置片段、实际 smoke |
| `validation/` | 已有验收证据；本地新结果另写 `local-validation/` |

Acycle 原仓库和 MATLAB 商业安装不包含在这个包中。`ACYCLE_ROOT` 要单独指向原仓库，参考 SHA 为 `dcba4279168745b563e0535b954297023dd62fc7`。新版本 Acycle 可以另行验证，不能直接覆盖参考 checkout 后继续沿用旧验收结论。

## 交给本地助手

打开项目目录，在新会话中粘贴 [HANDOFF_PROMPT.txt](../local/HANDOFF_PROMPT.txt) 的全部内容。若客户端支持读取本地文件，也可以说：

> 请读取并执行当前项目 `local/HANDOFF_PROMPT.txt`。先确定本地路径与已安装环境，完成独立检查和小规模 MATLAB 测试，再给我实际结果。不要照抄历史云端的 `/workspace/...` 路径。

该任务文本包含环境定位、安装边界、9 个工具的检查、Newark/SWA/COCO/eCOCO 运行顺序、19 次 Monte Carlo 的诊断性质、客户端配置、敏感性分支、结果复查及本机验收报告要求。API Key 不在交接包中；需要真实模型时使用本地已有的运行环境凭据。

## 手工部署的最短路线

1. 打开完整包所在目录，按 [用户文档](USER_GUIDE.zh-CN.md) 安装 `.venv`、Python 包、参考 Acycle，设置 MATLAB 路径。
2. 运行 `python local/doctor.py --run-matlab --output local-validation/doctor.json`。失败时先解决实际许可证/工具箱/路径问题。
3. 运行 `python local/smoke.py --case analyze`，确认 Newark 原始输入和 MATLAB 输出。
4. 依次运行 `--case swa`、`--case coco --nsim 19`、`--case ecoco --nsim 19`。每次输出独立运行和回执。
5. 运行 `python local/render_config.py --workspace . --acycle-root /absolute/path/acycle --matlab /absolute/path/matlab`，检查生成片段。
6. 选择 Codex MCP 或 Harness 原生插件接入，刷新客户端后再做一次真实工具调用，避免只测 CLI 却声称客户端接入已验证。

`render_config.py` 只生成 `local/generated/` 中的片段；遇到与现有内容不同的同名文件会拒绝覆盖。只有明确要重生成这些片段时才使用 `--force`。它不会修改 `~/.codex/config.toml`、项目 `.codex/config.toml` 或 Harness profile。不要把生成片段连同本机绝对路径误当成适用于另一台电脑的配置。

## 本地验收表

| 检查 | 应保留的证据 |
| --- | --- |
| 包版本和解释器 | Python路径、包版本、所注册的9个工具；不要混装旧wheel和新npm包 |
| MATLAB实际运行 | release、工具箱、成功启动记录；不能用可执行文件存在代替 |
| Acycle来源 | checkout SHA、每个原函数hash、是否匹配参考 |
| Newark | 请求、summary、谱图、演化图、数值输出 |
| SWA | Lomb/MTM路径、原FDR含义、实际文件与图；非有限阈值的语义 |
| COCO/eCOCO | 目标周期来源、深度单位、cm/kyr网格、窗口/步长、nsim、seed、支持/失效信息 |
| 客户端 | Codex MCP或原生Harness实际工具调用回执，区分终端测试与客户端测试 |
| Steering | 原基线存在、输入hash一致、子运行parent正确、比较结果 |
| 研究解释 | 逐点/全局/选择后检验区分、未完成部分、论文复现边界 |

本地 smoke 的 COCO 网格和 210 Ma 中间年龄是执行示例。不得把其最优速率直接作为 Newark 的地质结论。只有与论文对应的完整输入、预处理、目标、搜索范围、模拟设置和检验准则一致，才可以进一步讨论定量复现。实际复现参照 [PAPER_VALIDATION.md](PAPER_VALIDATION.md) 和 benchmark 的来源记录。

## 遇到问题时需要回传的最小信息

提供操作系统、Python/MATLAB版本、`local-validation/doctor.json`、失败运行的 `request.json`/`result.json`、MATLAB日志和预期输出名称即可。先排除 API Key、许可证秘密、用户凭据和无关私有文件。纯本地计算不依赖 GitHub Actions，也不需要云端产物连接器；如果本机 MATLAB 可用，继续走本地路径。
