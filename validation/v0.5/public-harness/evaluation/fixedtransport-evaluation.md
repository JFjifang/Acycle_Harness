# Newark 两轮真实会话验收

**工程接入、MATLAB 执行、完整数据谱系和后续参数保持通过；模型的科学解释需要人工审查和修正。** 这里不作“整体全绿”结论。测试为公开方案辅助的演示，模型可读专用 skill、manifest 和来源说明，不是盲测方法发现。

| 维度 | 结果与证据 |
| --- | --- |
| 官方 runtime／实际模型 | 真实 published SDK、AgentLoop、DeepSeek provider；模型实际可见 13 个 Acycle 工具、10 个 Acycle skills 加公开演示 skill |
| 用户输入 | 首条仅短自然语言目标和附件；第二条在同一 Session 独立要求 eCOCO 800/200；两条实际 user event 唯一且均与记录的提示一致 |
| 附件 | 原始 SHA、官方 Session 文件消息和授权 import 回执一致 |
| 首轮科学执行 | 六个必需阶段成功；模型主动增加两次峰／谷相位检查，首轮共八次 MATLAB 科学调用，无失败或外部 Python 数值分析 |
| 数据谱系 | 原始输入 → Pro → 同一 Pro 产物的深度分析／COCO／eCOCO → 实际完整滤波文件 → 实际调谐控制 → 原始代理的时间域诊断，全部核验通过 |
| 第二轮 | 一次 eCOCO rerun 成功；父运行、方法、原始来源、输入字节保持，仅有效 window 600→800、step 100→200 改变 |
| 原结果保留 | 全部原 artifact 角色及字节匹配首次 live tool 返回的 SHA；原输入也与首次见证一致，不以事后 result.json 自证 |
| 图件与文件 | 两轮均有官方 present、原文件和 image 引用；read_image 非 offloaded 图像与 Files API 上传证据匹配。主 Chat 像素／放大／刷新／下载见独立 Web 验收 |
| 可移植证据 | 强制使用科学归档路径的报告，与 live workspace 报告除生成时间外全部一致 |
| 科学解释 | **needs review**：原回答有非单调轨迹误称单调、控制点与周期段混淆、误述部分轨道目标检验、过度推断真实沉积变化和相位稳健性等问题 |

首轮已经明确披露 global p≥0.95、19 次模拟的限制、405 kyr 非独立证据、相对时间轴和小峰／漏峰风险。这些正确限制与具体解释错误同时保留。第二轮如实指出候选轨迹依赖窗长并收敛部分结论，但仍有重复错误。原模型回答没有改写；[人工校核讲稿](../../../../demo/newark-0.5.0/REVIEWED_NARRATIVE.zh-CN.md)是单独文档，不是模型解释已通过的证明。

新 800/200 结果有六个完整窗口，中心 400–1400 m，候选轨迹为 `5, 7, 5, 5, 5, 8` cm/kyr。其余有效参数不变。候选轨迹变化不能证明实际沉积速率变化；窗口覆盖不同、Monte Carlo 预算较小、每窗校正不是整图校正，均需保留。首轮的两个相位步骤不算第三条用户消息的验收。

首次跨进程 continuation 在发送新用户消息前因 SDK 恢复接口误用失败，没有产生新 user event、模型推理请求或科学调用；失败回执保留。修复使用官方 `resumeSession()` 后，先通过了真实 SDK 两个独立进程的无 API 测试，证实同 Session、原附件和前一轮工具结果可恢复；随后原 Session 的第二条实际用户消息只发送了一次。基线没有重算。

更早的旧运输方案尝试也独立保留：虽然六个科学阶段产出了结果，但调谐遇到传输失败，模型自行裁列后重提交，并在第九个科学请求时超出预算，最终未交付 final。它没有被后来的成功替换。

- [最终分维度 JSON](fixedtransport-evaluation.json)
- [首轮逐条解释校核](fixedtransport-first-turn-review.json)与[两轮解释校核](fixedtransport-two-turn-review.json)
- [原模型两轮公开回执](../newark-fixedtransport/ecoco-followup-retry.json)，[首次恢复失败](../newark-fixedtransport/ecoco-followup.json)
- [真实 SDK 跨进程恢复证据](../resume-keyless-v2/resume-check.json)
- [可移植逐字节核验](portable-evidence-check-v2.json)与[完整科学文件索引](fixedtransport-evidence-index.json)
- [旧失败尝试的 v2 审计](initial-attempt-v2.json)；旧 v1 结果仍保留

验收器只读取结构化记录、参数和文件字节，不重新计算科学结果。四个独立反例先证明旧验收器可能误判通过，再以定向回归验证修复；因此历史角色完整性、首次见证和后续实物产物分别检查，不从 `completed` 状态推断科学解释通过。
