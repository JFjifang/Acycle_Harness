# 工程检查范围

`python-tests.txt` 是本地 Python 编排、协议、传输、来源校验、进程监督和验收器测试；不代替真实 MATLAB 数值测试。`node-tests.tap` 使用发布的官方 Harness 0.2.1-rc.3 服务和独立安装的 0.5 wheel，27 项通过、无跳过，包含进程取消和六项会话支持测试。

`node-tests-misconfigured-python.tap` 保留一次测试启动配置错误：指定的源码开发虚拟环境没有安装 `acycle_deepseek`，在临时工作目录调用时无法导入。随后改为已经独立安装并核验的 release-check Python 后通过；没有修改科学计算以消除这一失败。不要把这份早期日志当成最终安装检查。

最终 wheel/npm/源文件字节核对见上一级 `release-verification.json`；真实 agent 作用域检查见 `../local/`；MATLAB 与模型会话的结果见上一级 `ACCEPTANCE.md`。
