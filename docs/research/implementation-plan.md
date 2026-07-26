# 实施计划

## 已完成：可执行核心

- [x] 独立 Git 仓库与 Python 3.13 锁定环境
- [x] 固定官方 grader、数据集、Finance Agent v2 提交
- [x] 官方 grader 原样 44/44 单元测试
- [x] 全量数据文件 SHA-256 与统计复算
- [x] SEC-only TSLA 端到端 Demo
- [x] 工具轨迹、来源、公式、失败分类与产物哈希
- [x] 透明标记非官方裁判与不可比成绩

## 下一阶段：回答 harness

1. 加一层 FrontierFinance adapter：保留 `query_id`，把 `query_date` 注入 Agent prompt，
   强制所有工具 `end_date <= query_date`。
2. 为公开 FA v2 提供可替换的免费 SEC/公司 IR adapter，商业 API adapter 保持兼容。
3. 将 200 次工具调用、300 秒单工具 timeout、查询总时限、并发、模型推理档位全部配置化。
4. 按 ATIF 保存每次模型消息、工具参数/返回、token、价格表版本与失败归因。
5. 先跑一个六类工作流分层小样，再决定全量 220 条成本预算。

## 下一阶段：官方评分

1. 配置三家裁判 key；对一条 query 做三裁判 smoke test。
2. 保存每个裁判原始 JSON、token、延迟和价格，而不仅是官方布尔输出。
3. 检测 partial-judge failure 和 all-judge failure；任何全裁判失败都单独报警。
4. 全量运行前冻结模型快照或记录 API alias 解析结果。
5. 同时发布官方原始指标和 bootstrap 置信区间；后者是补充，不替换官方指标。

## GitHub / Pages

- [x] 静态审计页数据与设计方向
- [ ] GitHub Actions：tests、ruff、Page deploy、artifact hash check
- [ ] 将完整中文报告导出 PDF
- [ ] 远程仓库创建后替换链接并开启 Pages
- [ ] 若要进入官方榜单，先向 Samaya 确认第三方提交流程

