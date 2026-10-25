# 0.5 本地问题修正与验证边界

本页记录 0.5.0 依据 `HARNESS_IMAGE_DIAGNOSIS.zh-CN.md` 完成的修复，分别覆盖模型读图、用户看图、实际 agent 配置及 MATLAB 启动。该轮使用 Harness Web 0.2.1-rc.3 验证。0.5.1 已增加当前 Desktop 的原生 preset 配置，最新安装入口见 [本地 handoff](LOCAL_HANDOFF.zh-CN.md)。

| 现象 | 0.5 的处理 | 已验证的范围 |
|---|---|---|
| 模型被识别为仅文本，无法读图 | 明确选择官方 `deepseek-flash` 路由及 `text,image`，并检查最终实际 agent | 真实模型成功执行两次 `read_image`，对应 Files API 上传存在；不把图片引用当成视觉输入 |
| 全局 persona/skills 存在，但实际会话没有加载 | 把 persona、原生工具、技能读取和文件/图片工具放入 `acycle` agent preset | 检查实际 agent 及发送前的请求消息：13 原生工具、10 通用 skills；显式演示配置额外加载 1 个公开 skill |
| 图件只出现在工具轨迹，主聊天不显示 | 最终回复使用插件返回的实际 PNG Markdown，保留原件下载链接 | 官方 Web 主聊天加载、点击放大、刷新恢复，PNG/CSV/MAT/FIG 下载校验一致；旧 Desktop 0.1.2 的渲染器未被修改 |
| MATLAB 在 Harness 的 shell 中启动失败，日志丢失 | 通过原生桥接启动一次；区分启动超时与计算超时；保留 launch JSON、合并日志、失败/取消运行记录 | 真实 MATLAB 科学功能由 GitHub R2024b 验证；Linux 模拟进程验证启动失败、取消、退出和证据保留。用户 Mac 的 ServiceHost/许可环境仍需本地 doctor 检查 |
| 取消 Python 时 MATLAB 子进程可能遗留 | Python 管理本次 MATLAB 进程组；Node 的强制终止宽限留足清理时间 | POSIX/Linux 真实子进程测试通过，包括忽略 TERM 的模拟进程；不声称 Windows 已验证 |
| MCP 只返回文件路径 | 增加已登记产物的 `resources/list`、`resources/read` 和 SHA/大小信息，拒绝越界路径与被修改的产物 | 安装后真实 stdio 协议与安全边界测试通过；是否嵌入主聊天图片仍取决于 MCP 客户端 |
| 远程滤波 CSV 不能作为下一阶段输入 | 对同仓库已登记产物使用原始 ZIP/成员引用，并校验来源、ZIP 与文件 SHA | 实际新链路已验证原字节复用；不再由模型裁列绕过 workflow 参数上限。未登记初始文件仍受编码大小限制 |
| GitHub 503 导致重复分派风险 | 有界重试只读请求；POST 仅发送一次，响应不确定时按唯一 token 查找既有任务 | 合约测试覆盖单次 POST 与恢复；首次排练中未被会话消费的任务另存证据，不冒充会话成功 |

最初浏览器验收脚本曾在长回复中等待尚未滚入视口的懒加载图片而超时。修正等待顺序后，对同一已完成会话做了浏览器复核，没有再次调用模型或 MATLAB；原失败回执保留。详见 [Web 验收记录](../validation/v0.5/web/REPORT.zh-CN.md)。

安装及本地入口检查见 [本地回执](../validation/v0.5/local/README.zh-CN.md)，完整交付状态见 [0.5 验收](../validation/v0.5/ACCEPTANCE.md)。数值执行、模型解释、文件交付、客户端显示和本机环境是不同的验收项，不能互相替代。
