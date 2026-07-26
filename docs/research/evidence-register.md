# 证据登记表

| 判断 | 类型 | 一手证据 | 置信度 |
|---|---|---|---:|
| 数据集为 220 queries / 11,543 rubrics | 官方事实 | [数据卡](https://huggingface.co/datasets/samaya-ai/FrontierFinance)、本地 SHA-256 验证 | 高 |
| 六类投资工作流 | 官方事实 | [发布博客](https://samaya.ai/blog/frontier-finance) | 高 |
| 主分数是逐查询宏平均 rubric 通过率 | 官方事实 | [System Performance](https://research.samaya.ai/benchmarks/frontier-finance/system-performance)、grader 代码 | 高 |
| 三裁判多数票 | 官方事实 | [grader README](https://github.com/samaya-ai/frontier-finance) 与 `grading.py` | 高 |
| 推荐裁判为 Sonnet 4.6 / Gemini 3.1 Pro / GPT 5.4 | 官方事实 | grader `eval.example.yaml` | 高 |
| FA v2 有六个研究工具 | 代码事实 | [Finance Agent v2](https://github.com/vals-ai/finance-agent-v2) `VALID_TOOLS` | 高 |
| 官网运行增加 200 tool calls、单次 300s | 官方事实 | [System Performance notes](https://research.samaya.ai/benchmarks/frontier-finance/system-performance) | 高 |
| Samaya 内部检索/路由不可复刻 | 公开边界 | 发布博客只给高层描述，未公开实现 | 高 |
| 没有公开官方提交流程 | 未发现公开证据 | 官网、数据卡、grader README 均无入口 | 中高 |
| 官网分项使用的数据类别计数与当前数据文件有 2 条差异 | 本项目验证 | `run-breakdowns.json` 对比固定 HF 数据快照 | 高 |
| TSLA rubric 4、7 与查询日前 SEC 披露冲突 | 本项目实跑 | Tesla 2024 10-K、2024 Q3 10-Q、计算与哈希 | 高 |
| 官方可能有未公开 query-date adapter | 推断/未知 | FA v2 固定 2026-03-01，而公开查询日期跨越该日 | 低（仅可能性） |

## 固定版本

| 资产 | 提交 / 哈希 |
|---|---|
| Samaya grader | `7d2d9c2a54816e94fb9e2e6a1cb033cc9dfcb589` |
| Finance Agent v2 | `e2a0446969a9b77c7613012744c15affe14a88d0` |
| FrontierFinance HF repo | `21da0514a15c51774ff836c46f290681c0ad91ee` |
| `frontier_finance_public.jsonl` | `a82874d7a587baf6f1ebe79b95fa1c3090260d3661c544f4496056d338e313c4` |
| 官网 `system-performance.json`（2026-07-26 捕获） | 见 `docs/data/provenance.json` |

