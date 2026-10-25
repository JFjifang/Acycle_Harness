# 0.5 本地交付入口：独立安装与实际 agent 检查

最终复验对应提交 `cc3cdcb7ecfc20dd4f681a97aa1df777f543ee7b`，使用以下带 `cc3cdcb` 后缀的新回执；旧回执和 `SUMMARY-pre-cc3cdcb.json` 保留。最终 wheel/npm 哈希在 `SUMMARY.json`。

这些检查使用独立安装的 0.5.0 wheel、从发布 tgz 解出的原生插件，以及已安装的官方 Harness 0.2.1-rc.3。工作区与源码目录不同，清除了 `PYTHONPATH`、`PYTHONHOME` 和模型 Key。官方 npm 包通过私有 node_modules 链接复用；这里不声称重新从网络安装了全部 npm 依赖。

| 回执 | 实际检查 |
| --- | --- |
| `install-check-cc3cdcb.json` | wheel/npm 与安装文件逐字节一致；0.5.0、12 个 MCP 工具、13 个原生工具和 10 个技能；实际 capabilities |
| `generated-mcp-cc3cdcb.json` | 生成的 Codex command/args/env 在独立工作目录启动；保留虚拟环境 symlink 路径；0.5.0 与 12 工具 |
| `agent-composition-cc3cdcb.json` | 真实 Web preset agent：13 个工具、10 个 scoped skills、persona、官方 text/image 模型能力、作用域内 capabilities |
| `newark-agent-composition-cc3cdcb.json` | 显式 demo preset：相同 13 工具、10 通用技能加 1 个公开 demo 技能；可读取技能正文；全部 11 个技能进入真实 AgentLoop fixture 请求 |
| `doctor-failure-preservation-check.json` | 合成启动程序退出 7；只启动一次、不自动重试、日志持久保留；附 portable 日志与 launch receipt |
| `SUMMARY.json` | 检查层级、安装包与本地脚本 SHA、环境和限制 |

actual-agent 检查使用确定性的无 Key adapter 捕获真实请求消息，旁边的 `.prompt.txt` 和 `.request.json` 是证据；没有调用真实模型 API，也没有启动真实 MATLAB。普通和 demo 模式分别验收，demo 的公开来源哈希在 `newark-deployment-cc3cdcb.json`。部署配置和回执中的绝对路径只是本次验证机器的记录，用户应在本机重新生成。

`doctor-startup-failure-fixture.json` 的 `failed` 是预先设计的失败，不是实际 MATLAB 启动失败。可搬移的 `doctor-failure-fixture/` 保存合成程序、日志和单次 launch 记录。它验证“失败不丢证据”，不证明许可证或科学函数可用。

本检查不改旧 Desktop、全局客户端配置或 MATLAB 许可证；不执行科学数值计算，不验证 macOS 环境。真实 MATLAB、真实模型、Web 主 Chat 和科学解释应分别看 `validation/v0.5/ACCEPTANCE.md` 与对应记录。

传输修复后只重跑安装、生成的 MCP 和两种真实 agent 组合；此前合成 doctor 失败保留检查没有再次启动。上述检查不执行 GitHub 远程任务，也不修改完整 live 演示结论。
