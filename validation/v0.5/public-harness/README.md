# 公开 Harness 会话证据

这些是原始真实会话的公开副本，保留用户输入、工具调用／结果、附件引用和用户可见最终回答；模型内部 reasoning blocks、deltas 和嵌套字段按结构删除。原文件未改写。各目录的 `public-trace-export-index.json` 记录原始／公开 SHA、字节数和删除计数。

- [最终两轮验收](evaluation/fixedtransport-evaluation.md)：完整执行与方法保持通过，科学解释需要校核；不是整体全绿。
- [真实两轮原回答](newark-fixedtransport/ecoco-followup-retry.json)：同一个官方 Session，首轮八次、第二轮一次 MATLAB 科学调用。
- [旧尝试失败与恢复记录](evaluation/initial-attempt.md)：不被后来的成功覆盖。
- [首次 continuation 启动失败](newark-fixedtransport/ecoco-followup.json)：新用户消息送达前失败，没有新科学调用。
- [修复后的跨进程 keyless 测试](resume-keyless-v2/resume-check.json)：实际官方 SDK／持久化 Session，脚本 provider，无真实模型推理或科学计算；不得当作真实模型自主性验收。
- [可移植 hash 核验](evaluation/portable-evidence-check-v2.json)和[归档索引](evaluation/fixedtransport-evidence-index.json)。完整科学文件位于完整版证据包的 `validation/v0.5/scientific-runs/`。

早期 keyless composition 与第一次 keyless 单轮断言失败也保留。实际主 Chat 图件显示、放大、刷新和原文件下载的证据在相邻 `validation/v0.5/web/`；SDK image 引用本身不能证明浏览器像素已显示，更不能证明科学解释正确。

原始 `validation/v0.5/harness/` 仅在执行环境保留，不进入发布包。人工校核讲稿与原模型原文分开，公开方案辅助测试也不称为盲测论文复现。
