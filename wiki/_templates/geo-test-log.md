---
title: "GEO Test Log Template"
description: "记录 AI 搜索测试题、平台、答案摘要、是否提及品牌、引用、准确性和纠偏动作。"
type: "template"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: ["Subagent adversarial review"]
related: ["../30_playbooks/geo-ai-search.md", "../50_channels/geo-ai-search/index.md"]
---

# GEO Test Log Template

| Date | Platform | Prompt | Location / Account | Mentioned? | Citation? | Accuracy Score | Error | Fix Action | Source |
|---|---|---|---|---|---|---|---|---|---|
| YYYY-MM-DD | ChatGPT/Perplexity/Gemini/Google |  |  | yes/no | yes/no | 1-5 |  |  |  |

## Accuracy Score

| Score | Meaning |
|---|---|
| 1 | 完全错误或误导 |
| 2 | 提到但关键信息错误 |
| 3 | 大致正确但缺重要上下文 |
| 4 | 正确且有少量缺口 |
| 5 | 准确、完整、引用良好 |

