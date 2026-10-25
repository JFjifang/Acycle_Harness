# Acycle Harness 0.2.0 验收记录

2026-10-25。本版以 MATLAB 为科学计算和作图后端，Python 负责接口、文件传输、运行记录与模型工具调用。未提供自动 Python 数值替代。已保存并推送到 https://github.com/JFjifang/Acycle_Harness 。

## 已通过的实际验证

| 项目 | 结果 | 证据 |
| --- | --- | --- |
| Python 编排、路径边界、工具协议、远端传输 | 47 项通过 | `python-tests.txt` |
| Node 子进程传输、取消、错误处理、skills | 4 项通过 | `node-tests.txt` |
| 安装后的原生 Harness 包 | 6 工具、6 skills 注册、调用和卸载成功；官方 dsh 0.2.1-rc.3 / Cordis 4.0.5 | `native-plugin-smoke.json` |
| 实际 MATLAB R2024b | 9 项测试通过，0 失败、0 未完成 | `matlab-summary.json`、`matlab-junit.xml` |
| DeepSeek-V4.1-Flash 真实 API | 5 次工具调用全部成功，基线→敏感性→比较完成 | `deepseek-live.json` |
| 最终安装包 | wheel 与 npm 包安装后文件逐字节匹配源码和交付包 | `release-verification.json` |

最终 MATLAB CI：[40167143233](https://github.com/JFjifang/Acycle_Harness/actions/runs/40167143233)，代码提交 `7af2c5d63b121cf1d9ac2a2f3f0675987e677210`。之后的打包、skills 说明与验收记录更新不改变 MATLAB 计算实现。

MATLAB 测试实际运行了 La2004、Guandao、Wayao、Svalbard PETM 四个官方样例，以及官方红噪声负对照；还运行了两篇 Nature Communications 论文的原始数据子集/记录。Newark 已列入可运行 benchmark 清单，本次未执行，不能从清单条目推断已经验证。

原函数数值对照包含预处理、MTM/AR(1)、EvoFFT、Gaussian/Taner 滤波、Hilbert 包络、沉积速率和控制点年龄转换。测试还核查非空 PNG、可编辑 FIG、MAT、CSV 输出，保留严格对照容差，并检查不得覆盖已完成的结果。

## MATLAB 与 Acycle 来源

Acycle 参考和实际执行提交均为 `dcba4279168745b563e0535b954297023dd62fc7`。基线和敏感性结果的全部所用原函数哈希匹配参考值。计算调用原函数；预处理和 EvoFFT 等 GUI 回调抽取位置、绘图适配及差异见 `matlab/SOURCES.md` 和 `matlab/source_registry.json`。

真实测试发现上游不受约束的 AR(1) 优化器在纯正弦输入上可能返回非物理复数参数。本版只在原函数返回值无效时调用 Acycle 原有 `minirhos0`，按原始置信度公式在 MATLAB 内重建数据和图，并明确记录所用方法。新增回归测试同时比较备用计算和实际保存的图形曲线。普通有效输入继续使用原始 `redconfML`；本次 DeepSeek 两次运行均采用原始路径。

## DeepSeek 实际运行

官方模型列表将 API ID `deepseek-flash` 标识为 DeepSeek-V4.1-Flash。真实测试通过共享工具调度器调用远端 MATLAB，未使用模拟模型响应或预填计算结果。

- 基线：`20261025T054948Z-c2484cc8d88f`，LOWESS span 0.35，[MATLAB run 40166934103](https://github.com/JFjifang/Acycle_Harness/actions/runs/40166934103)。
- 敏感性：`20261025T055310Z-f5883a2371e6`，span 0.25，[MATLAB run 40167140923](https://github.com/JFjifang/Acycle_Harness/actions/runs/40167140923)。
- 两次使用相同输入哈希；第二次保留第一条 `parent_run_id`。原始输入、参数、数值与图片均分别保存。
- 成功调用 `acycle_capabilities`、`acycle_inspect`、`acycle_analyze`、`acycle_sensitivity`、`acycle_compare`。模型解释保留了逐频点检验、深度域单位和边缘效应的限制，未宣称轨道强迫或论文完整复现。

这是“真实 API＋共享工具＋MATLAB”的测试；原生 Harness 注册器另外进行了安装验收，没有声称运行过完整桌面 UI 会话。自动验收确认工具执行和运行关系，不能代替逐句审核模型文字。例如原始模型答复前段将输入误写为 498 点，后段正确写为 499→498；权威 MATLAB 字段为 `input_rows=499`、`processed_rows=498`。保留原始对话供审查，未修改模型记录来隐藏该差异。

## 云端产物传输

当前云实例仍在代理层拒绝 GitHub Actions 的签名 Azure Blob 下载地址。普通 `gh` 下载因此失败；此处采用连接器支持的 GitHub 产物下载与原子缓存交付，两个 ZIP 的 SHA-256 均与 GitHub 回执一致，见 `connector-transfers.json`。

这只改变传输，计算、图形和数据保存仍由 MATLAB 完成。`ACYCLE_ARTIFACT_CACHE` 模式需要外部授权代理服务，不能仅设置环境变量就假定可无人值守下载。标准联网环境使用默认 `gh` 路径，本地 MATLAB 不需要 GitHub。详见 `docs/GITHUB_ACTIONS.md`。

## 打包与复现边界

完整 ZIP 包含源码、6 个 skills、wheel、原生 npm 包、论文来源及提取记录、测试结果、`matlab-validation-report.zip` 和两次真实运行的 `live-runs/`。`live-evidence.json` 提供相对文件路径及逐文件哈希；原始运行记录保留当时环境的绝对路径，换目录后请使用相对映射查看输出。

论文测试只验证真实论文数据上的核心流程，不复现 COCO/eCOCO、ASM、整篇年代模型或论文结论。当前桥接的是 Acycle 核心子集。未来版本需检查实际源码哈希与接口并重新跑 MATLAB 对照，不以函数同名作为兼容性证明。

API Key 未写入源码、测试记录、GitHub 或交付包。
