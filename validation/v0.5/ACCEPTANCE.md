# Acycle Harness 0.5.0 验收

2026-10-25。新增 Interpolation Pro 和峰谷天文调谐，修正本地 Harness 配置、图片交付、失败记录及远程阶段间传输。六个科学操作均在 MATLAB 中执行；Python 负责接口、文件、来源和进程/传输管理。共享接口 12 个工具，Harness 原生接口 13 个工具、10 个通用 skills；明确选择 Newark 演示时另加载 1 个公开 skill。

**完整计算链与两轮对话调参通过；模型科研解释仍需人工审核。** 不把本次公开预设演示称为盲选方法验证或 Newark 已发表年代模型复现。

完整科学原件随独立 Newark 演示包和完整研究包提供；轻量本地 handoff 提供安装材料、文档和验收回执。

| 验收项 | 结果与证据 |
|---|---|
| MATLAB 原函数、提取回调及实例 | 39 项通过，含 Pro 7 项、调谐 8 项、原始 proxy 按控制点覆盖范围转时间的集成测试。见 [最终代码 CI](matlab-release-ci.json)；参考 Acycle `dcba4279168745b563e0535b954297023dd62fc7`、MATLAB R2024b |
| Python 编排/边界/进程/验收器 | 203 项通过；[日志](engineering/python-tests.txt)。不把 mock 编排测试当成数值验证 |
| 官方 Harness 服务与插件 | 27 项通过、无跳过；[日志](engineering/node-tests.tap) |
| 独立安装 | wheel/npm/源码逐文件一致、MCP 实际 stdio、原生注册与调用；[回执](release-verification.json) |
| 实际 agent 配置 | 普通 13 工具/10 技能，演示 13 工具/11 技能；确认技能进入实际请求、persona 和图像路由生效；[本地配置检查](local/SUMMARY.json) |
| 模型读图与用户看图 | 真实 `read_image`/Files API 传输；官方 Web 主 Chat 图片、放大、刷新、原件下载通过；[范围与原始超时记录](web/REPORT.zh-CN.md) |
| Newark 完整会话 | 两条独立用户消息、同一 Session，9 次 MATLAB 科学运行成功；[完整分维度验收](public-harness/evaluation/fixedtransport-two-turn.json) |
| 原件与谱系 | 原始输入→Pro→深度/COCO/eCOCO→完整三列滤波→调谐→原始 proxy 时间诊断；首次工具回执哈希与后续原件一致；[独立传输核验](artifact-transfers.json) |
| 科研解释 | `needs_human_review`；[逐项校核](public-harness/evaluation/fixedtransport-two-turn-review.json) 与 [经校核讲稿](../../demo/newark-0.5.0/REVIEWED_NARRATIVE.zh-CN.md) |

第一条测试消息是“按 Newark 演示方案，对附件完成从深度记录到相对时间轴的分析，并评估可靠性。”模型读取公开方案，自行调用原生工具，完成六阶段主线，并主动增加谷值调谐及其原始 proxy 时间诊断，共 8 次成功计算。第二条消息仅要求把 eCOCO 窗口改为 800 m、步长改为 200 m；模型调用一次 `acycle_rerun`，实际只有这两项有效参数变化，保留 adaptive、目标、速率网格、去趋势、种子、模拟次数及原基线。原件哈希复核通过。

首轮 GitHub 后端排练用时 1413 秒，追问计算及回复用时 228 秒。它包含每阶段 Actions/MATLAB 启动与托管制品交付，不能据此承诺本地耗时或 3–5 分钟实时演示。发布会应先在本地 MATLAB 预演；附带已完成排练的原件可作明确标注的回放。

模型正确指出 19 次模拟不能支持 p<0.05、全记录 COCO 未通过全局检验、405 kyr 峰受调谐假设影响，以及弱振幅小峰可能造成多计周期。但它也误写了 Pro 输入哈希、单调速率变化、未解析目标的具体类别、35 个控制点与周期段数，并夸大相位一致性及共享数据分支的独立性。第二轮虽承认窗口依赖，仍残留部分过强表述。原回复完整保留，校核讲稿另列，不把改写后的文本冒充模型原始回答。

初次排练的失败也保留：[记录](public-harness/evaluation/initial-attempt.md)。其滤波文件触及 workflow 参数大小限制；模型自行做了两列结构投影，遇到 HTTP 503 后又重新提交，违反失败后停止的规则，最后在追加相位分析时超出预算，没有最终回复。现已改为原字节 artifact 引用、只读请求有界重试和单次 POST 的 token 查询恢复。同一 Session 的跨进程测试还暴露了 SDK 恢复句柄错误，修正后经真实无 Key 双进程检查，再完成实际第二用户轮；没有重算原基线。

此次 Web 验证使用官方 0.2.1-rc.3，不能当作旧 Desktop 0.1.2 或用户 Mac 的执行证据。Mac 的 MATLAB ServiceHost、许可及本机路径需运行交付的 doctor 检查；进程取消测试覆盖 POSIX/Linux。普通 MCP 客户端是否嵌入图片仍须客户端单独验证。

历史论文比较仍按原标准保留未通过：Lavernock 谱峰位置接近文献，但 5% FDR 未复现；两个 PETM 协议案例未复现预声明速率区间；Cambrian 仅为缩减预算流程。39 项工程/数值测试通过不改变这些科学结论。公开会话副本省略私有 reasoning 字段，保留用户消息、工具参数、结果、错误及最终回答；科学产物没有改写。
