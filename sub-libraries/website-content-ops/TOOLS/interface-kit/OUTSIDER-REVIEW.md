---
title: "旁观审查机制（OUTSIDER-REVIEW.md）—— 外部 AI 从旁观者角度审查完善"
type: "doc"
status: "Working"
owner: "AI"
last_updated: "2026-08-31"
description: AllinCMS 建站工具包文档（OUTSIDER-REVIEW.md）
created: 2026-08-31
visibility: "public"
redaction_status: "safe-to-publish"
sources: ["self"]
related: ["README.md"]
---

# 旁观审查机制（OUTSIDER-REVIEW.md）—— 外部 AI 从旁观者角度审查完善

> 与双审（SOL/TERRA，审查"产物是否正确/安全"）互补：**旁观审查 = 无外部上下文的独立 AI，只看回落产物**（HANDOFF/TASK.json/索引/evidence），审查"回落与机制本身"（是否完整可接手/有无自说自话/是否夸大/流程是否闭环）。

## 触发时机
1. 每次大任务收尾（建站/体系建设/接口攻破完成后）
2. 每 3 次会话（例行）
3. 用户要求时（随时）
4. 回落产物变更后（HANDOFF/索引被更新）

## 输入（只给这些，不给对话）
- `TASK.json`（状态）+ `HANDOFF.md`（时间线）
- `interface-kit/index/*.tsv`（doc-registry/issues/modules）+ INDEX.md
- `interface-kit/index/registry_tools.py`（工具自检）
- `interface-kit/RUNBOOK-ANYONE.md`（零上下文总入口——审查它本身是否可执行）
- 关键 evidence 指针（DELIVERY/DUAL-REVIEW/IMPROVEMENT-PLAN 的路径与头 30 行）

## 旁观者视角清单（审查什么）
| 维度 | 问句 |
|---|---|
| 接手性 | 0 上下文 AI 按 HANDOFF 能否 10 分钟开始干活？缺哪块说明？ |
| 完整性 | 最近会话的每个"问题/决策/产物"是否都在回落里？有没有"只做了没写"？ |
| 自证性 | 是否有"我说过了所以对了"的自说自话（无指针/无验证结果）？ |
| 可追溯 | 每个结论能否找到 evidence 指针？断言与证据是否匹配（夸张/缩小）？ |
| 矛盾 | HANDOFF 与 TASK.json/索引/内容状态是否互相矛盾？ |
| 流程闭环 | "坏了→修了→回填了→验证了"链条是否完整？缺哪环？ |
| 可执行 | 下一位 AI 照文档能跑通吗（命令/路径是否存在）？ |

## 输出与回填
- 输出 `70_evidence/OUTSIDER-REVIEW-<date>.md`：[P0|P1|P2] 列表 + `OUTSIDER_VERDICT: PASS|PASS_WITH_FIXES|FAIL`
- 本人按 P0/P1 修复 → 修复记录追加同一文件 → 引用进 HANDOFF 未决段
- 新问题回填 issues.tsv（带 `outsider-review` category）

## 执行方式（无记忆 subagent）
```text
派 1 个 subagent（不给会话上下文，只给上述输入文件路径 + 本清单）+ 它输出报告
与 SOL/TERMA 区别：双审看"产物对不对"，旁观者看"回落好不好/新 AI 接不接得住"
```

## 3. 对抗评审协议（2026-08-29 多轮评审后新增——重要）
0. **先跑 audit 门（必带每站 --config）**：收到外部评审/AI 复核前，先 `python3 site_pipeline.py audit <slug> --config 70_evidence/<slug>-audit-config.json --out 70_evidence/audit-report-<date>.json` 拿事实（13 项机检——含 root-home 与 form-render；审计范围以 site_pipeline.py 代码为唯一真源），以报告为回应基准，避免重复评审已闭环项。**--config 基线（pages/count/faq_answers/cta/units）必须从该站内容计划(COP)取实建数，不得沿用他站**——audit 默认基线是 Demo，缺 config 会对新站产生假 FAIL（ISS-063）。
1. **先建事实矩阵再回应**：收到外部评审/AI 复核后，第一步抓最新线上快照，逐点标"当前真实状态"（✅/❌/平台边界），并**标注评审引用版本**（多轮评审会基于旧快照——曾出现"FAQ 无答案/alt 未修"的误判，实为评审缓存旧版；以最新抓取证据回应，不盲从也不傲慢）
2. **完成声明=三点验证**：任何"已完成"必须提供 ①HTML grep 证据 ②DOM/结构检查 ③无 JS 抓取（curl）结果——三者一致才算
3. **采纳分级**：真实未修项=立即修；平台边界=记录反馈；评审旧快照点=证据回应+记录（防对方反复）
4. **评审沉淀**：每轮评审的 P0/P1 必须落到规则/skill（否则下篇重蹈）——本仓库以此累计 8+ 条规则
