# 论文数据验证与验收边界

本轮选择 SWA 方法论文及两篇 *Nature Communications* 应用论文：方法来源直接、原始数据公开、能给出可检验的数值或明确的运行流程。这里不以未经核实的引用次数宣称论文影响力。计算、预处理和绘图均由 MATLAB/Acycle 完成；Python 仅提取原表单元格、记录来源、调用工具并比较 MATLAB 返回的验收字段。

论文案例列在 [manifest](../benchmarks/manifest.json)。其中预先声明的数值检查和实际执行结果分开保存：manifest 不表示已通过；运行回执中的 `checks[].passed` 才是本次结果。未通过的数值比较必须保留，不能通过选择更好看的区间或参数把它改成“复现成功”。原始 CI 比较结果汇总在 [paper-validation.json](../validation/paper-validation.json)。

| 案例 | 数据 | 本次验收范围 |
| --- | --- | --- |
| `paper-weedon-swa` | Lavernock 原始磁化率，439 点 | 原始 SWA 数值一致性；约 0.81 m 峰且超过 5% FDR |
| `paper-petm-coco` | Howards Tract 较宽区间磁化率，5027 点 | 原始 COCO 实现执行；2000 次模拟；保留与论文 8–15 cm/kyr 区间不一致的结果 |
| `paper-petm-coco-published-protocol` | 补充材料指定区间的原始磁化率，4364 点 | 独立按补充材料日志校正协议；2370 个插值后点；仍使用现代 COCO 内核 |
| `paper-cambrian-ecoco` | Albjära-1 主分析 Al 指标，0–18 m、18001 点 | 预算缩减的原始现代 eCOCO 实现执行；8 个完整窗口与 MATLAB 图件 |
| `official-newark` | Acycle 官方完整 Newark depth-rank，2344 点 | 完整核心工作流、频谱和图件；不等同于独立重建 Newark 年代框架 |

COCO/eCOCO 的逐项原函数数值一致性由独立的合成数据测试覆盖；不重复计算论文案例的整套 2000/199 次模拟。论文案例另外检查其来源、完整执行和明确列出的结果指标。

[CI 40173168648](https://github.com/JFjifang/Acycle_Harness/actions/runs/40173168648) 的 22 项机械/论文测试为 21 通过、1 未通过：PETM 较宽区间速率比较失败。SWA 的论文显著性未复现另外作为科学比较结果保留，不能因其机械测试通过而忽略。Cambrian 缩减流程完成，不代表全文复现。

最终 [CI 40174469745](https://github.com/JFjifang/Acycle_Harness/actions/runs/40174469745) 完成 **23/23 项工程验证**；论文比较独立报告为 **三项未通过**：SWA 的 5% FDR、PETM 较宽区间和 PETM 补充日志协议的速率范围。工程验证覆盖接口执行、原函数一致性和比较记录保存，不将预期之外的科学结果改写为通过。Cambrian 仅通过缩减工作流验收。最终结果与此前补齐协议的 [CI 40174219143](https://github.com/JFjifang/Acycle_Harness/actions/runs/40174219143) 一致；各比较及 SHA-256 已汇入最终聚合回执。

## SWA：原始方法数据的谱峰检验

Weedon, Page & Jenkyns (2019), *Geological Magazine* **156**, 1469–1509，[DOI:10.1017/S0016756818000808](https://doi.org/10.1017/S0016756818000808)，是 Smoothed Window Averages 的方法来源之一；文章于 2018-12-17 在线发表，卷期年份为 2019。数据来自 [PANGAEA.896872](https://doi.org/10.1594/PANGAEA.896872)，保留未调谐的地层高度和原始磁化率，不使用其 tuned-time 或 E-filter 列。

Weedon (2020), *Boletín Geológico y Minero* **131**, 207–230，[DOI:10.21701/bolgeomin.131.2.001](https://doi.org/10.21701/bolgeomin.131.2.001) 的 Fig. 11 及正文给出 Lavernock 0–13.17 m 段的约 0.81 m 峰超过 5% FDR；原始存档实际观测范围为 0.03–13.17 m。本桥接调用 `specswafdr`，保持原始线性去趋势、两端各 5% 余弦锥化、三次 Hanning 平滑及不插值流程。

预先给定波长容差为 ±0.07 m：记录跨度 13.14 m 下，该峰附近一个独立谱分辨单元约为 0.05 m，并留出论文四舍五入余量。必须同时满足峰的位置和 5% FDR，单独超过点态 95% 阈值不够。不复现贝叶斯概率、天文调谐或阶的持续时间；2020 文献还修正了早期贝叶斯分析的预白化解释。

**实际发现：论文 FDR 特征尚未复现。** [首次扩展 MATLAB CI](https://github.com/JFjifang/Acycle_Harness/actions/runs/40172473806) 的原函数数值一致性检查通过，谱峰位于 1.21765601217656 cycles/m（约 0.82125 m），但原始函数返回的全部 FDR 阈值列均为 `NaN`，因此未满足预先声明的“超过 5% FDR”条件。[实际频谱表](../validation/artifacts/expanded-release/swa-lavernock-publication/swa-spectrum.csv) 与 [MATLAB 图件](../validation/artifacts/expanded-release/swa-lavernock-publication/swa-spectrum.png) 保留了这次未通过结果。`NaN` 表示原函数没有给出该阈值，不能解释成“显著”或改用点态阈值代替。

重新核对论文图、数据列、区间、去趋势和谱平滑后，没有找到支持修改输入以获得显著性的依据。一个需进一步溯源的具体差异是：2019 §3.b 和 2020 p.211 描述比较所有候选窗口的总体最小 RMSE；固定版本的 `specswafdr.m` 则优先减少背景斜率反转，在 `revmin == 0` 时提前停止窗口搜索，并限制末端平滑次数。该差异可能改变背景拟合，但目前没有证明它就是未复现的原因。本桥接保留原始实现和原验收条件，没有为了通过论文检查改动算法或缩短数据区间。

## COCO：PETM 论文参数与现代实现的速率比较

Li et al. (2022), “Astrochronology of the Paleocene-Eocene Thermal Maximum on the Atlantic Coastal Plain,” *Nature Communications* **13**, 5618，[论文](https://doi.org/10.1038/s41467-022-33390-x)、[开放全文 Methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC9509358/)。两个独立案例均提取 `Ca & MS` 表 D/E 列。

最初的 `paper-petm-coco` 选择整个 Nanjemoy 不整合面以下数据至 214.558 m，采用 20 m LOESS、六周期、经典红噪声处理、论文速率网格和 2000 次模拟，但保留现代默认采样/相关设置。实际完成 2000 次模拟，最终运行用时 75.59 秒，最优速率 **26.43 cm/kyr**、速率网格全局 Monte Carlo p = **0.103948025987**，没有落入预先声明的 8–15 cm/kyr 区间。[MATLAB 原始比较回执](../validation/artifacts/expanded-release/paper-petm-coco-2000/published-comparison.json) 和这一失败案例均保留。

补充材料的进一步审计找到明确差异：[Supplementary Text 3，pp.22–23](../benchmarks/sources/petm_2022_supplement.pdf) 含实际分析日志，[纯文本摘录](../benchmarks/sources/petm_2022_coco_protocol.txt) 可离线核对。原始文件名指定 187.54–211.24 m，经 20 m LOESS 和 0.01 m 线性插值后为 187.542–211.232 m、2370 点；采用 **Pearson**、NFFT **5000**、频率上限 **0.06 cycles/kyr**。初次案例实际使用更宽区间、0.005 m 中位间隔、Spearman、NFFT 8192 和 0.0641711 上限，因此不能把该次偏差仅归因于新旧算法，也不能声称其参数完整匹配原文。

独立的 `paper-petm-coco-published-protocol` 根据这份可核实日志新建，原始 CSV 为 4364 点、187.542–211.237 m；所有去趋势与插值仍在 MATLAB 中完成。其他固定参数为一片段、六周期 `[125, 95, 39.8, 23.3, 22, 18.7]` kyr、0.13–30 cm/kyr（步长 0.1）、经典 AR1 相减和 2000 次模拟；种子 1 是本项目的可重现性选择。保留同一 8–15 cm/kyr 事前比较条件；新案例不是覆盖旧结果，也没有搜索参数以追求匹配。速率数组按 MATLAB 冒号语义生成，最后一点是 29.93。

**独立协议案例仍未复现论文速率范围。** [实际比较回执](../validation/artifacts/expanded-release/paper-petm-published-protocol-coco-2000/published-comparison.json) 确认 MATLAB 处理后恰为 **2370 点、187.542–211.232 m**，且完成 **2000 次模拟**。全搜索最大相关位置为 **28.93 cm/kyr**，速率网格全局 p = **0.669665167416**，该 p 的 95% Monte Carlo 置信区间为 **0.64858–0.68977**；这不是沉积速率置信区间。区间远离 0.05，本次未检出显著结果不能解释成“模拟次数不足”，也不能换用局部 p 值取得显著结论。在这个搜索峰位置，六个请求周期仅 **4 个可分辨**，六周期同时可分辨的速率上界约为 **18.96 cm/kyr**。因此 **28.93 不能解释为完整六周期模型支持的实际地质沉积速率，也不支持显著天文强迫结论**。原始 8–15 cm/kyr 比较仍为未通过，没有截断搜索范围或改选次级峰来制造吻合。

论文采用 Acycle 2.4.1，本项目使用固定源码的 COCO 2.0 `phase_averaged`。现代实现逐谱重估振幅，以平稳 AR1 和完整速率搜索构造零假设，与历史随机谱检验不同。LOESS 的距离窗口以 Acycle 分数跨度映射，历史去趋势后逐点数据也未完全核对，不能声称恢复了全部历史预处理细节或精确复现旧版 p 值。这些是已知差异，不是已经确定的唯一失败原因；没有开展逐项控制实验或完整历史内核重演来分离它们的影响。每个案例须保留实际结果及差异，均不代表整篇 PETM 年代模型或事件持续时间复现。

## eCOCO：寒武纪论文主指标的缩减流程

Zhao et al. (2022), “Synchronizing rock clocks in the late Cambrian,” *Nature Communications* **13**, 1990，[论文](https://doi.org/10.1038/s41467-022-29651-4)、[开放全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC9007955/)、[补充说明](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-022-29651-4/MediaObjects/41467_2022_29651_MOESM1_ESM.pdf)。本次提取 S2 的作者校正深度与 Al 列，不取天文调谐年龄列。

原文使用 12 点平滑、全记录 8% LOESS。补充 Fig. 5 的完整 eCOCO 为 4 m 窗、0.01 m 步长、5000 次模拟，搜索 0.5–15 mm/kyr、步长 0.1 mm/kyr；正文 1–10 mm/kyr 是结果范围，不能误作搜索范围。

本次只取论文第一个 0–18 m 子段，使用约 6 m LOESS、4 m 窗、2 m 步长、199 次模拟和较粗速率网格；省略原文 12 点平滑，并采用 500 Ma 的现代九周期目标。子段 LOESS 的边缘效应也不同。因此它验证真实主指标上的原始实现执行，不复现整幅已发表 eCOCO 图。约 1.85 m / 405 kyr 对应约 0.457 cm/kyr，仅作为图中尺度的诊断参照，不作为硬性通过条件。

实际完成 **8 个窗口、199 次模拟**，最终运行用时 **12.81 秒**；跟踪速率依次为 0.50、1.15、0.20、1.50、1.30、1.30、0.80、0.20 cm/kyr。[MATLAB 比较回执](../validation/artifacts/expanded-release/paper-cambrian-ecoco-199/published-comparison.json) 保存完整差异说明。这些结果只能证明预算缩减的真实数据流程完成；没有通过已发表速率图或显著性结果的复现验收。

COCO/eCOCO 的基础方法文献为 Li, Kump, Hinnov & Mann (2018), *Earth and Planetary Science Letters* **501**, 165–179，[DOI:10.1016/j.epsl.2018.08.041](https://doi.org/10.1016/j.epsl.2018.08.041)。本次没有另外宣称复现该论文的全部案例。

## 本地重跑与来源审计

配置本地 MATLAB 和 `ACYCLE_ROOT` 后，在仓库根目录执行：

```sh
python benchmarks/run.py --workspace . --case official-newark --receipt validation/newark-local.json
python benchmarks/run.py --workspace . --case paper-weedon-swa --receipt validation/weedon-local.json
python benchmarks/run.py --workspace . --case paper-petm-coco --receipt validation/petm-local.json
python benchmarks/run.py --workspace . --case paper-petm-coco-published-protocol --receipt validation/petm-protocol-local.json
python benchmarks/run.py --workspace . --case paper-cambrian-ecoco --receipt validation/cambrian-local.json
```

2000 次 COCO 模拟通常比普通谱分析明显耗时；不要把减少模拟次数后的探索结果与该案例混为一谈。eCOCO 的窗口内速率搜索校正不代表跨所有窗口的全图显著性校正。

每个 CSV 的 `.provenance.json` 保存精确来源行号、列、筛选区间及 SHA-256；[下载清单](../benchmarks/sources/downloads.json) 固定原始发布文件。`python benchmarks/prepare_paper_data.py --download` 可重新获取并提取，依赖 `openpyxl`。源文件一旦变化，校验失败，不会静默接受新内容。PANGAEA 数据及两篇 Nature Communications 的相关开放数据按 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 署名使用，并遵循各文件的第三方材料署名说明。CSV 属于明确记录的列/行提取；未在 Python 中改变采样、拟合趋势或计算频谱。

实际运行证据位于 `validation/` 和每次独立 run 的 `result.json`、MATLAB `.mat`、数据表与图件。源代码逐项数值比较见 `matlab/tests/`；Newark 专项证据见 `validation/newark-result.json` 和 `validation/newark-evidence.json`。报告结果时必须区分“工作流完成”“原函数数值一致”“论文特征吻合”和“整篇论文复现”。
