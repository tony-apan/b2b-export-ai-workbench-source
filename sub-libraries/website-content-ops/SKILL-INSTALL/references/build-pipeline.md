# 建站一条龙(工作区某站 → 上线)

把工作区里一个站,从「客户资料」走到「上线验收」的完整流水。现有的
`run_source_file_rehearsal.py` 是主编排引擎(inventory→extraction→source-wiki→package→
confirmation→execution);本文把它和**工作区结构**(`references/workspace-layout.md`)、
**三个质量闸**串成一条有阶段、有产物落点、可续跑的线。每步产物落这个站的 `run/`(或对应
子文件夹),`scripts/site_build_status.py` 读这些产物判断「到哪了 / 下一步 / 还欠哪个闸」。

## 阶段流水

| # | 阶段 | 输入 | 产物落点 | 该过的闸 |
|---|---|---|---|---|
| 1 | 提炼客户 wiki | `clients/<c>/raw/` 原始资料(只增不改) | `clients/<c>/wiki/`(客户级,跨站共享) | — |
| 2 | build source-wiki | 客户 wiki(取**本站**产品子集 + 站定制) | `sites/<s>/source-wiki/` | — |
| 3 | build package | source-wiki | `sites/<s>/package/` | — |
| 4 | **内容质量闸** | package | `run/content-quality-report.json` | `check_content_quality`(占位/库存图/缺 alt/幻觉规格/薄参数) |
| 5 | **定 run-mode** | `siteCreation.status` | `run/run-mode.json` | `resolve_run_mode`(已有站必问用户 · 决定第7步) |
| 6 | 授权浏览器建站 | package + run-mode | `run/site-live.json`(记 siteKey/URL) | 每步 `check_pre_mutation_gate` |
| 7 | **残留闸**(仅新建/改造站) | 全站前台文本 + `residue-blacklist.json` | `run/residue-report.json` | `check_template_residue`(incremental 跳过) |
| 8 | 上线验收 | run evidence | `run/launch-acceptance.json` | launch-acceptance |

## 三个闸各在哪一步、拦什么

- **内容质量闸(第4步 · 发布前)**:新内容对不对——每字段可追溯 sourceRef、无占位/库存图/缺 alt、
  无幻觉规格。**任何模式都过。**
- **run-mode(第5步)**:决定第7步残留闸适不适用。新建站(`from_scratch`)/ 改造站(`template_conversion`)
  = 要残留闸;日常更新自有干净站(`incremental_update`)= 跳过。**已有站分不清,必须问用户**(见其 confirmationPrompt)。
- **残留闸(第7步 · 上线前)**:旧模板内容清没清——喂全站每条路由的可见文本 + 旧内容黑名单,逐页扫,
  零命中才 launch。（`incremental` 模式此步自动跳过。）发现残留后,用
  `plan_residue_fixes.py --report run/residue-report.json` 把 hits 按类型分派成修复工作单
  (分类 chip→后台 tab、产品/文章→各自 JSON save、全局块→对应 designer layer、单页→theme page),
  逐组修 → 复验该组路由 → 再全站跑残留闸,到零才 launch。

## 看进度 / 续跑

```bash
python3 skills/allincms-bulk-content-upload/scripts/site_build_status.py \
  --site-dir <workspace>/clients/<c>/sites/<s>
```

输出「已完成阶段 + 下一步 + 还欠哪个闸」。多站各跑各的、互不干扰;新会话接手一个客户时,
先对它每个站跑一遍看进度,不丢线。这也是 workspace README「状态」列的事实来源。

## 安全 / 隐私

- 每步产物落**工作区**(私有),绝不进公开 skill 仓;真实 siteKey 记 `run/site-live.json` + README 索引,不进 skill。
- 提炼严守:每条知识回溯 raw 的 sourceRef,缺口标 gap,绝不编造 PII/联系方式/价格/认证。
