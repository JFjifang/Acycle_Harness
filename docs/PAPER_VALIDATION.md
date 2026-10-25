# 论文数据验证与验收边界

本轮选择 SWA 方法论文及两篇 *Nature Communications* 应用论文：方法来源直接、原始数据公开、能给出可检验的数值或明确的运行流程。这里不以未经核实的引用次数宣称论文影响力。计算、预处理和绘图均由 MATLAB/Acycle 完成；Python 仅提取原表单元格、记录来源、调用工具并比较 MATLAB 返回的验收字段。

三个新案例列在 [manifest](../benchmarks/manifest.json)。其中预先声明的数值检查和实际执行结果分开保存：manifest 不表示已通过；运行回执中的 `checks[].passed` 才是本次结果。算法版本不同导致的未通过必须保留，不能通过选择更好看的区间或参数把它改成“复现成功”。

| 案例 | 数据 | 本次验收范围 |
| --- | --- | --- |
| `paper-weedon-swa` | Lavernock 原始磁化率，439 点 | 原始 SWA 数值一致性；约 0.81 m 峰且超过 5% FDR |
| `paper-petm-coco` | Howards Tract 不整合面以下磁化率，5027 点 | 原始 COCO 实现执行；2000 次模拟；最优速率与论文 8–15 cm/kyr 区间比较 |
| `paper-cambrian-ecoco` | Albjära-1 主分析 Al 指标，0–18 m、18001 点 | 预算缩减的原始现代 eCOCO 实现执行；8 个完整窗口与 MATLAB 图件 |
| `official-newark` | Acycle 官方完整 Newark depth-rank，2344 点 | 完整核心工作流、频谱和图件；不等同于独立重建 Newark 年代框架 |

COCO/eCOCO 的逐项原函数数值一致性由独立的合成数据测试覆盖；不重复计算论文案例的整套 2000/199 次模拟。论文案例另外检查其来源、完整执行和明确列出的结果指标。

## SWA：原始方法数据的谱峰检验

Weedon, Page & Jenkyns (2019), *Geological Magazine* **156**, 1469–1509，[DOI:10.1017/S0016756818000808](https://doi.org/10.1017/S0016756818000808)，是 Smoothed Window Averages 的方法来源之一；文章于 2018-12-17 在线发表，卷期年份为 2019。数据来自 [PANGAEA.896872](https://doi.org/10.1594/PANGAEA.896872)，保留未调谐的地层高度和原始磁化率，不使用其 tuned-time 或 E-filter 列。

Weedon (2020), *Boletín Geológico y Minero* **131**, 207–230，[DOI:10.21701/bolgeomin.131.2.001](https://doi.org/10.21701/bolgeomin.131.2.001) 的 Fig. 11 及正文给出 Lavernock 0–13.17 m 段的约 0.81 m 峰超过 5% FDR；原始存档实际观测范围为 0.03–13.17 m。本桥接调用 `specswafdr`，保持原始线性去趋势、两端各 5% 余弦锥化、三次 Hanning 平滑及不插值流程。

预先给定波长容差为 ±0.07 m：记录跨度 13.14 m 下，该峰附近一个独立谱分辨单元约为 0.05 m，并留出论文四舍五入余量。必须同时满足峰的位置和 5% FDR，单独超过点态 95% 阈值不够。不复现贝叶斯概率、天文调谐或阶的持续时间；2020 文献还修正了早期贝叶斯分析的预白化解释。

**实际发现：论文 FDR 特征尚未复现。** [首次扩展 MATLAB CI](https://github.com/JFjifang/Acycle_Harness/actions/runs/40172473806) 的原函数数值一致性检查通过，谱峰位于 1.21765601217656 cycles/m（约 0.82125 m），但原始函数返回的全部 FDR 阈值列均为 `NaN`，因此未满足预先声明的“超过 5% FDR”条件。[实际频谱表](../validation/artifacts/expanded-first/swa-lavernock-publication/swa-spectrum.csv) 与 [MATLAB 图件](../validation/artifacts/expanded-first/swa-lavernock-publication/swa-spectrum.png) 保留了这次未通过结果。`NaN` 表示原函数没有给出该阈值，不能解释成“显著”或改用点态阈值代替。

重新核对论文图、数据列、区间、去趋势和谱平滑后，没有找到支持修改输入以获得显著性的依据。一个需进一步溯源的具体差异是：2019 §3.b 和 2020 p.211 描述比较所有候选窗口的总体最小 RMSE；固定版本的 `specswafdr.m` 则优先减少背景斜率反转，在 `revmin == 0` 时提前停止窗口搜索，并限制末端平滑次数。该差异可能改变背景拟合，但目前没有证明它就是未复现的原因。本桥接保留原始实现和原验收条件，没有为了通过论文检查改动算法或缩短数据区间。

## COCO：PETM 论文参数与现代实现的速率比较

Li et al. (2022), “Astrochronology of the Paleocene-Eocene Thermal Maximum on the Atlantic Coastal Plain,” *Nature Communications* **13**, 5618，[论文](https://doi.org/10.1038/s41467-022-33390-x)、[开放全文 Methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC9509358/)。提取 `Ca & MS` 表 D/E 列，深度下界来自 `Lithology information` 的 Nanjemoy 基底 187.50380981408108 m，至最深 MS 观测 214.558 m。

本次采用论文的 20 m LOESS、线性插值、六个目标周期 `[125, 95, 39.8, 23.3, 22, 18.7]` kyr、经典红噪声处理、0.13–30 cm/kyr（步长 0.1）和 2000 次模拟；种子固定为 1。速率数组按 MATLAB 冒号语义生成，最后一点是 29.93。检查最优速率是否落在论文所报 COCO 的 8–15 cm/kyr 宽区间。

论文采用 Acycle 2.4.1，本次是固定版本源码的 COCO 2.0 `phase_averaged`。现代 Monte Carlo 检验和目标生成方式有变化，不能声称精确复现旧版 p 值、整篇 PETM 年代模型或事件持续时间。公开回执应同时保留实际最优速率、Monte Carlo p 值、区间和不一致结果。

## eCOCO：寒武纪论文主指标的缩减流程

Zhao et al. (2022), “Synchronizing rock clocks in the late Cambrian,” *Nature Communications* **13**, 1990，[论文](https://doi.org/10.1038/s41467-022-29651-4)、[开放全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC9007955/)、[补充说明](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-022-29651-4/MediaObjects/41467_2022_29651_MOESM1_ESM.pdf)。本次提取 S2 的作者校正深度与 Al 列，不取天文调谐年龄列。

原文使用 12 点平滑、全记录 8% LOESS。补充 Fig. 5 的完整 eCOCO 为 4 m 窗、0.01 m 步长、5000 次模拟，搜索 0.5–15 mm/kyr、步长 0.1 mm/kyr；正文 1–10 mm/kyr 是结果范围，不能误作搜索范围。

本次只取论文第一个 0–18 m 子段，使用约 6 m LOESS、4 m 窗、2 m 步长、199 次模拟和较粗速率网格；省略原文 12 点平滑，并采用 500 Ma 的现代九周期目标。子段 LOESS 的边缘效应也不同。因此它验证真实主指标上的接口和原函数一致性，不复现整幅已发表 eCOCO 图。约 1.85 m / 405 kyr 对应约 0.457 cm/kyr，仅作为图中尺度的诊断参照，不作为硬性通过条件。

COCO/eCOCO 的基础方法文献为 Li, Kump, Hinnov & Mann (2018), *Earth and Planetary Science Letters* **501**, 165–179，[DOI:10.1016/j.epsl.2018.08.041](https://doi.org/10.1016/j.epsl.2018.08.041)。本次没有另外宣称复现该论文的全部案例。

## 本地重跑与来源审计

配置本地 MATLAB 和 `ACYCLE_ROOT` 后，在仓库根目录执行：

```sh
python benchmarks/run.py --workspace . --case official-newark --receipt validation/newark-local.json
python benchmarks/run.py --workspace . --case paper-weedon-swa --receipt validation/weedon-local.json
python benchmarks/run.py --workspace . --case paper-petm-coco --receipt validation/petm-local.json
python benchmarks/run.py --workspace . --case paper-cambrian-ecoco --receipt validation/cambrian-local.json
```

2000 次 COCO 模拟通常比普通谱分析明显耗时；不要把减少模拟次数后的探索结果与该案例混为一谈。eCOCO 的窗口内速率搜索校正不代表跨所有窗口的全图显著性校正。

每个 CSV 的 `.provenance.json` 保存精确来源行号、列、筛选区间及 SHA-256；[下载清单](../benchmarks/sources/downloads.json) 固定原始发布文件。`python benchmarks/prepare_paper_data.py --download` 可重新获取并提取，依赖 `openpyxl`。源文件一旦变化，校验失败，不会静默接受新内容。PANGAEA 数据及两篇 Nature Communications 的相关开放数据按 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 署名使用，并遵循各文件的第三方材料署名说明。CSV 属于明确记录的列/行提取；未在 Python 中改变采样、拟合趋势或计算频谱。

实际运行证据位于 `validation/` 和每次独立 run 的 `result.json`、MATLAB `.mat`、数据表与图件。源代码逐项数值比较见 `matlab/tests/`；Newark 专项证据见 `validation/newark-result.json` 和 `validation/newark-evidence.json`。报告结果时必须区分“工作流完成”“原函数数值一致”“论文特征吻合”和“整篇论文复现”。
