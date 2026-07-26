# 验证记录

研究环境：Windows / Python 3.13.14 / uv 0.11.32 / Node 24.16.0。

| 验证 | 结果 | 备注 |
|---|---:|---|
| Samaya 官方 grader tests | 44 / 44 pass | 固定 commit `7d2d9c2…`，清除机器 SOCKS proxy 环境变量后 |
| 本项目 tests | 8 / 8 pass | XBRL、数值精度、数据集、官网 bundle 与 artifact hash 检查 |
| Ruff | pass | Python 静态检查 |
| Node syntax check | pass | `docs/app.js` |
| 全量数据 SHA-256 | pass | 与固定 HF 快照一致 |
| SEC-only Demo | completed_with_findings | 14/16，非官方裁判，2 个评分异常 |
| Pages desktop QA | pass | 动态 bundle、图表、表格、Demo、异常与时间线均渲染 |
| Pages 390px QA | pass after fix | 修复长标题导致的横向溢出 |
| 图表轴切换 | pass | `aria-pressed` 状态正确更新 |
| 浏览器 console | 0 errors / warnings | 本地 HTTP 服务验证 |

## 已记录的异常运行

1. SEC HTTP 403：自动客户端 User-Agent 缺少符合服务器规则的联系格式；归为
   `environment_anomaly`。
2. XBRL 空数字节点：初版解析器中止；归为 `agent_failure`。
3. XBRL 文本 `no` 的父节点样式含数字：原始“是否含数字”检查误判；归为
   `agent_failure`，现改为只检查可见文本。

这些异常运行与成功运行均保留 manifest、轨迹和产物哈希。原始 SEC 文件因体积和许可
不进入 Git，由 `source_manifest.json` 固定 URL、filing date、字节数和 SHA-256。
