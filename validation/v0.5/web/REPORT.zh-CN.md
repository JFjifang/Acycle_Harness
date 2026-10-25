# 0.5 官方 Web 图件交付验收

环境为项目内独立的 DeepSeek Harness `0.2.1-rc.3` 官方 Web profile，使用实际 `acycle` agent preset 与 Chromium。没有修改官方运行时源码，也没有启动新的 MATLAB 科学计算。仅取回既有运行 `20261025T071158Z-b0f32143454c` 的原始输出。本报告不代表旧版 `0.1.2-rc.1` Desktop/MCP 已获得同样能力。

## 实际模型轮与浏览器重验

- `main-chat-live.agent.json`：一次真实 `deepseek-official/deepseek-flash` 模型轮完成。实际 agent 挂载 13 个 Acycle 工具、10 个普通 skills，并有 persona 和 Acycle 工作流规则。模型调用 `acycle_get_run`、skill 和两次 `read_image`，后两者返回保留像素的 image block；官方 FilesAPI 上传索引保存对应两个原始 PNG 的记录。科学计算工具调用数为 0。
- `main-chat-live.json`：保留第一次脚本失败记录。模型轮已完成；浏览器等待未滚动到视口的懒加载图片，触发超时。不能将此记录描述为一次端到端通过。
- 修复验收脚本为先滚动目标图，再检查 `naturalWidth`。`--reuse` 只重开同一个持久 Session，不新建会话、不发送 user prompt；删除服务进程 API key，额外拒绝 `llm/stream`。
- `main-chat-live-browser-final.json`：上述同一 Session 在重启 Web 后通过浏览器验收；观测新增模型请求 0、工具调用 0，也没有触发拒绝执行的模型或工具请求。主 Chat 中频谱图 831×656、演化图 1707×1113，均由官方 `/api/file` 返回 HTTP 200；放大图正常，刷新后仍恢复。下载 PNG、CSV、MAT、FIG 与原文件 SHA-256 完全一致；浏览器 page error 为 0。此前 `browser-replay` 与 `browser-verified` 通过记录一并保留；最终脚本还消除了 DOM 变化期间等待定位器和 lightbox 图片解码的竞速。
- 对应 `*.chat-spectrum.png`、`*.chat-evolution.png`、`*.lightbox.png`、`*.chat-refreshed.png` 为真实浏览器截图，图件位于主 Chat，不只是 Trajectory 或侧栏卡片。

真实模型收到像素、用户看到图片与科学解释准确性是不同结论。本验收验证前两项及传输完整性，不验证模型对每个谱峰或 EvoFFT 条带的因果解释；视觉意见仍应保留方法和统计限制。

## 非 API 的官方集成验证

`main-chat-final-fixture.json` 使用明确标识的文字脚本适配器驱动官方 AgentLoop、现有运行工具和 Web UI，验证实际作用域 13 工具、10 skills、persona、主 Chat 图件、lightbox、刷新与下载；它不构成模型自主性或视觉能力证据。

`native-plugin-tests.tap` 保存当前原生插件的 21 项测试全部通过、0 跳过的逐项记录。取消集成测试启动真实 Python `run_matlab` 监督器和忽略 SIGTERM 的模拟计算子进程；约 5.03 秒后记录 `interrupted`、返回码 `-9`、一次启动、无自动重试，子进程已回收。模拟进程没有进行 MATLAB 科学计算。

最终插件将 Node 强制结束 Python 前的宽限从 5 秒调为 20 秒，让 Python 有时间完成自己的 5 秒终止宽限、强制结束独立 MATLAB 进程组及保存中断回执。真实图件模型轮使用此前插件版本；该最终差异由上述进程测试覆盖，不声称再次调用过模型。

## 复核命令

首次 fixture 或 live 调用使用 `scripts/harness_web_acceptance.mjs`，live 的 API key 只通过进程环境提供。不要把 key 写入命令、patch、报告或截图。

```bash
PYTHONPATH=src node scripts/harness_web_acceptance.mjs \
  --deployment local/generated/harness-web-ui/deployment.json \
  --run-id 20261025T071158Z-b0f32143454c \
  --output validation/v0.5/web/main-chat-live-browser-recheck.json \
  --mode live --reuse validation/v0.5/web/main-chat-live.json
```

复验时应使用新的 `--output`，保存既有证据；同一部署的 Web 端口必须空闲。该命令不需要 API key，复用的 Session 和附件须仍在同一部署的私有 home 中。
