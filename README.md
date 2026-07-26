# FrontierFinance 可审计复现

这是一个独立研究项目，目标是在公开信息与合法可得数据范围内，尽可能完整复刻
Samaya AI 的 FrontierFinance system-performance benchmark。项目不隶属于 Samaya AI
或 Vals AI，也不会把离线审计分数冒充官方排行榜成绩。

## 在线入口

- [项目展示页](https://monking-peng.github.io/frontier-finance-reproduction/)
- [中文研究报告](https://monking-peng.github.io/frontier-finance-reproduction/report.html)
- [GitHub 仓库](https://github.com/Monking-peng/frontier-finance-reproduction)

公开仓库是从开发仓库提交 `8230bf1ae4b894a2be20d31fe45e8f633646aaa9` 生成的
白名单快照。本机绝对路径、原始 SEC 大文件、缓存、凭证和开发历史均未发布；公开
运行记录中的命令路径已做等价脱敏，相关产物哈希已重新计算。

## 当前结论

- 正确研究对象是 Samaya 在 2026 年 7 月发布的 220 条开放式金融研究查询基准，
  共 11,543 条专家 rubric；不是搜索结果里同名的 25 个 Excel 建模任务论文。
- 官方公开了完整 rubric 数据集和 grader；公开基线的回答生成 harness 是 Web Search
  API、Finance Agent v2 与 Samaya 私有系统三类。
- 官方分数是“每条查询内 rubric 通过率的宏平均”，每条 rubric 由三个独立 LLM
  裁判多数票决定。官方推荐裁判是 Claude Sonnet 4.6、Gemini 3.1 Pro 与 GPT 5.4。
- 官方网站没有披露第三方上传榜单的 API 或审核流程。这里仅复刻本地回答生成、评分、
  结果保存、证据链与展示，不虚构官方提交通道。
- 当前机器没有三家裁判 API key，因此首条 Demo 使用透明的确定性审计裁判跑通官方
  `Grader`、多数票和 `MetricsReport` 代码；其分数明确标记为不可与官方榜单比较。

## 一条可运行的关键 Demo

Demo 使用公开查询 `097d482fc529c5f0`：截至 2025-02-04，提取 Tesla 最近季度的
收入拆分。它实时下载查询日之前已公开的 Tesla 2024 10-K 与 2024 Q3 10-Q，解析内联
XBRL，以 `FY 2024 - 9M 2024` 推导 Q4，执行两组会计勾稽，再走评分链并保存哈希。

```powershell
uv sync --python 3.13.14
$env:SEC_USER_AGENT="Your Name your.email@example.com"
uv run ffrepro demo
```

SEC 要求自动化客户端提供可联系的身份；请在公开或持续运行前把示例值替换成真实联系信息。

输出位于 `runs/<timestamp>-tsla-q4-2024/`，包含：

- `answer.md`：系统答案；
- `facts.json`、`calculations.json`：数据与计算证据；
- `source_manifest.json`：来源、时间截点、字节数与 SHA-256；
- `trace.jsonl`：工具与 Agent 轨迹；
- `system_summaries.json`：官方 grader 兼容的回答格式；
- `metrics.json`、`per_item.json`：官方指标结构；
- `rubric_audit.json`：发现的 rubric/来源冲突；
- `run_manifest.json`、`artifact_hashes.json`：运行配置、版本与产物哈希。

## 官方三裁判评分

配置三家 API key 后，安装可选依赖并运行官方 grader：

```powershell
uv sync --extra official-judges
uv run frontier-finance-grader --config configs/grader.official.example.yaml
```

只有同时满足以下条件才应称为“官方可比”：完整 220 条查询、相同公开数据时间边界、
官方三裁判模型、相同多数票与宏平均逻辑，并完整披露 Agent 模型、推理档位、工具限制、
成本口径和失败查询。

## 上游版本

| 组件 | 固定版本 |
|---|---|
| Samaya grader | `7d2d9c2a54816e94fb9e2e6a1cb033cc9dfcb589` |
| FrontierFinance dataset | `21da0514a15c51774ff836c46f290681c0ad91ee` |
| Finance Agent v2 | `e2a0446969a9b77c7613012744c15affe14a88d0` |
| 数据集文件 SHA-256 | `a82874d7a587baf6f1ebe79b95fa1c3090260d3661c544f4496056d338e313c4` |

详细事实与未决项见 `docs/research/`。许可与署名见 [NOTICE.md](NOTICE.md)。
