# 会话回落模板（conversation-writeback.md）

> 规则：**问题即时回落**（遇到新坑 → 当天在 issues.tsv 加一行）；**会话收尾统一回落**（本模板追加到 HANDOFF.md）。
> 目的：其他 AI 从旁观者角度能 10 分钟内理解"做了什么/为什么/未决什么"，不依赖聊天记录。

## 触发时机
1. 发现新问题/新坑（第一时间，记 issues.tsv：现象/根因/修复/规避/文档/脚本/证据）
2. 每完成一个任务段（追加 HANDOFF 一段：日期/主题/决策/问题/产物）
3. 每 3 次会话或每次大改动（跑一次"旁观审查"，见 OUTSIDER-REVIEW.md）

## 回落段格式（HANDOFF.md 追加）
```markdown
## <YYYY-MM-DD> <主题一句话>
- 需求/决策：...（为什么这么做）
- 完成：...(产物指针：文件/索引 id/公网链接)
- 问题与解决：...(引用 ISS-xxx；无则新建)
- 平台边界类（勿再处理）：...
- 未决（下一位）：...
- 旁观审查状态：SOL/TERRA/OUTSIDER 结论指针
```

## 问题回落格式（issues.tsv 一行）
```
<ID>	<fixed|boundary|pending>	<categories>	<现象>	<根因>	<修复>	<规避>	<doc/script refs>	<evidence ref>
```

## 自我检查（回落质量）
- [ ] 事实可追溯（产物有指针，不靠记忆）
- [ ] 未决明确（不能有"大概/也许"）
- [ ] 新 AI 不依赖本会话上下文也能继续（仅读 HANDOFF+TASK+索引）
- [ ] 无凭据/无敏感值入档（token 只走 WS_TOKEN 环境变量或 chmod 600 文件，不入档）
