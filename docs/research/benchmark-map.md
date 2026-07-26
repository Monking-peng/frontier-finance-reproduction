# FrontierFinance benchmark 全貌（公开证据版）

> 研究截点：2026-07-26。本文只把官方页面、官方数据集、官方 grader 和官方引用的
> Finance Agent v2 当作一手证据；没有公开的部分明确写为未知。

## 1. 对象消歧

本项目复刻的是 Samaya AI 的 **FrontierFinance: A Challenging Benchmark for
Measuring Frontier Intelligence of Finance Agents**：220 条开放式金融研究查询、
11,543 条专家 rubric、六类投资工作流。

搜索引擎同时会返回 2026 年 4 月的同名论文 *FrontierFinance: A Long-Horizon
Computer-Use Benchmark of Real-World Financial Tasks*。后者是 25 个 Excel/PPT 金融建模
任务，作者、任务形态、评分方式和发布方都不同，不能作为 Samaya 基准的实现证据。
Samaya 当前给出的正式引用对象仍是其 2026 年 7 月博客，并称技术报告“即将发布”。

官方入口：

- [Benchmark](https://research.samaya.ai/benchmarks/frontier-finance)
- [System Performance](https://research.samaya.ai/benchmarks/frontier-finance/system-performance)
- [发布博客](https://samaya.ai/blog/frontier-finance)
- [数据集](https://huggingface.co/datasets/samaya-ai/FrontierFinance)
- [grader](https://github.com/samaya-ai/frontier-finance)

## 2. 数据如何进入系统

公开数据是一个 JSONL 文件，每行一条查询：

```text
query_id ── 稳定标识
query ───── 投资者口吻的自然语言问题
query_date ─ 信息截点；禁止使用此日之后的信息
use_cases ─ 六类工作流之一
capabilities ─ 一个或多个能力标签
rubrics[] ─ 原子、可二元判断的专家标准
```

rubric 还带有 `must_have`、一级/二级 rubric 类别和一级/二级数据源类别。数据集没有
参考答案，也没有随附源文档；回答系统必须自行访问公开网络、SEC、公司材料、市场数据
等。公开文件的固定快照为 220 行、11,543 条 rubric、7,487 条 must-have，SHA-256 为
`a82874d7a587baf6f1ebe79b95fa1c3090260d3661c544f4496056d338e313c4`。

## 3. 回答系统与 Agent

官方比较三类 harness：

1. **Web Search**：模型厂商官方、带网页检索 grounding 的 API。
2. **Finance Agent v2**：官方引用 Vals AI 的开源实现，并声明增加 200 次工具调用上限，
   每次工具调用 300 秒上限。
3. **Samaya System**：Samaya 的私有模型、数据索引、检索引擎和 harness 优化组合。

公开对比只使用公开数据，不使用私有券商研报等专有来源。Samaya System 的内部模型、
路由、检索索引、缓存、提示词与轨迹没有公开，因此只能复刻输入输出契约与评测链，不能
声称复刻其私有系统。

### Finance Agent v2 公开实现

固定上游：`vals-ai/finance-agent-v2@e2a0446969a9b77c7613012744c15affe14a88d0`。

主 Agent 由一个 agentic LLM 和六个研究工具组成，另有一个终止工具：

| 工具 | 公开实现 |
|---|---|
| `web_search` | Tavily fast search |
| `edgar_search` | sec-api.io 全文检索 |
| `parse_html_page` | 下载并解析网页，将长文本存入 Agent state |
| `retrieve_information` | 让同一 LLM 针对 state 中的长文档二次提取 |
| `price_history` | Tiingo 的股票/ETF、加密货币、外汇日频 OHLCV |
| `calculator` | `simpleeval` 白名单算术函数 |
| `submit_final_result` | 必须调用的结束/提交工具 |

Agent 默认一小时墙钟上限；本地命令默认还设 50 turns，而 README 明确称正式 benchmark
只用时间限制。上下文溢出时删除最老历史；纯文本回复不会结束，系统会提示继续调用工具
或 `submit_final_result`。运行会保存逐题日志、token、错误、ATIF 轨迹与 `results.json`。

### 关键公开差异

当前 Finance Agent v2 的 system prompt 把“当前日期”硬编码为 2026-03-01，并把三个
带日期工具的最大日期也限制为 2026-03-01；但 FrontierFinance 的 `query_date` 分布为
2024-08-08 至 2026-04-30，且 `run_agent.py` 只接收问题文本、不接收 `query_date`。
官方性能页只公开了工具调用限制改动，没有公开这处日期适配。因此：

- 不能确认官方是否使用了未公开的 query-date adapter；
- 直接运行当前上游会对部分查询形成时间锚点偏差；
- 本项目把“逐题注入 query_date、所有工具强制 cutoff”列为正式复刻必须补齐的适配层。

## 4. 评分器

官方 grader 的输入是：

```text
frontier_finance_public.jsonl  +  system_summaries.json
                                          │
             按 query_id 连接 ─────────────┘
```

每条查询把 `query`、`query_date`、系统回答和最多 30 条 rubric 放入裁判提示词。官方推荐
三个裁判：Claude Sonnet 4.6、Gemini 3.1 Pro、GPT 5.4。每个裁判对每条 rubric 输出
`true/false`，再逐 rubric 多数票；偶数存活票平票时第一个模型决定。

错误语义很重要：

- 没有回答：系统失败，按零分进入“all queries”分母；
- 某个裁判失败：丢弃该裁判，用存活裁判投票；
- 所有裁判失败：grader 异常，该查询从所有计分分母排除；
- JSON 解析失败：追加格式提醒重试，仍失败才丢弃该裁判。

公开提示词要求裁判接受单位换算和“按回答精度正确四舍五入”的近似，但更精确且数值
不同的答案不能通过。

## 5. 指标

官网主指标是 **Rubric Qualification Rate**：先计算每条查询通过的 rubric 比例，再对
220 条查询做宏平均。另报告主 Agent 模型的平均成本/查询与平均完整延迟/查询。

grader 还输出：

- macro / micro；
- success queries / all queries；
- 全部 rubric / must-have rubric；
- rubric type、data source type 的 micro breakdown；
- 无回答、全裁判错误和各裁判漏判计数。

官网成本只统计 agentic model，不包含搜索 API、数据索引、grader 或其他工具成本；因此
不能视为系统完全成本。官网也只公开平均延迟，没有 p50/p95。

## 6. 结果保存和展示

- Finance Agent v2：日志目录、逐题 Agent 结果、ATIF 轨迹、`results.json`。
- 官方 grader：`metrics.json` 与 `per_item.json`。
- 官网公开：12 个系统的总分、平均成本、平均延迟及六类 use case / 六类 rubric 的分项。
- 官网未公开：基线逐题回答、裁判原始理由、逐题成本/延迟、完整 Agent 轨迹、运行配置
  manifest。

本项目在官方两个输出之外增加 `source_manifest.json`、`trace.jsonl`、`facts.json`、
`calculations.json`、`run_manifest.json`、`failure.json` 和 `artifact_hashes.json`，补足
证据链与故障归因。

## 7. 官方提交

截至研究截点，Benchmark 页面、Hugging Face 数据卡与 grader README 都只描述本地评分，
没有公开第三方上传、榜单审核、签名验证或结果接受接口。Vals 平台的 suite 提交流程属于
Vals 自己的 Finance Agent Benchmark，不等于 Samaya FrontierFinance 的官方提交。

因此本项目不会写出不存在的“官方提交命令”。可公开交付的正确做法是发布：回答文件、
官方 grader 输出、完整 manifest、原始轨迹、哈希、成本口径与不可复刻边界，并请 Samaya
另行确认是否接受第三方结果。

