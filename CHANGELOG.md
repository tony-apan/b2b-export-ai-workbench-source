---
title: "Mother Library Changelog"
description: "记录母库版本范围内已经发生的结构与发布合同变化；未发布工作只进入 Unreleased，不把校验结果写成发布事实。"
type: "changelog"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-30"
sources: ["Mother-library and sub-library release architecture decision 2026-07-28", "Repository routing synchronization 2026-07-29"]
related: ["README.md", "MANIFEST.md", "RELEASE.md", "VERSION.md", "wiki/00_meta/current-focus.md"]
visibility: "private"
redaction_status: "private-source-reviewed"
---
# Mother Library Changelog

## 0.2.0-working — 2026-07-30

- 母库身份改为私有 canonical source；私有仓库同步与公开 Stable release 分开判定。
- canonical 仓库命名为 `b2b-export-ai-workbench-source`，不含 `-private`，也不覆盖既有公开仓或旧私有仓历史。
- `website-content-ops` 升级为 `0.3.2-preview.1` Public Preview，采用 Apache-2.0，保留非 Stable 和单样本边界。


## Unreleased — 2026-07-29

- 将根 `README.md`、`AGENTS.md`、`CLAUDE.md` 和 `CONTEXT.md` 收敛为一致的入口与边界路由，详细 SOP 继续由 wiki、manifest、release guide 和子库合同维护。
- 同步母库/子库独立发布、index canonical、raw→wiki→course、日志、Skill 条件性交付和外部证据边界。
- 明确 `APPROVAL_RECORD_PASS` 只证明记录结构与候选绑定，不能证明批准者真人身份；实际 tag object SHA、signer fingerprint、canonical annotation 与 approval digest 需要外部 workflow 真实值精确比对。
- 修正远端表述：本地 `origin` 于 2026-07-29 指向 `https://github.com/suxuemi/b2b-export-ai-workbench.git`；未修改 remote，也不把本地 URL 当作远端所有权、可见性或保护配置证明。
- 母库与已注册子库仍为 `release_status: BLOCK`、`license_status: pending`、`approval_status: pending`；本节不表示已经发布。

## 0.1.1-draft — 2026-07-28

- 增加候选包外批准记录、母库与子库独立 tag namespace，以及两阶段 prepare→qualify 合同。
- approval validator 校验 sidecar 结构、scope、commit、content digest、manifest/checksum 摘要、locator 与 tag 声明绑定；名称字段过滤不构成真人身份验证。
- 强化 registry/manifest 同步、source completeness、artifact 文件集合与 checksum 校验，并保持 dirty source、许可或批准未闭环时 fail closed。

## 0.1.0-draft — 2026-07-28

- 增加母库 manifest、release guide、版本、changelog、构建器和制品校验入口。
- 明确母库与子库是独立发布 scope；母库携带子库源码不授予子库发布资格。
- 构建范围改为 manifest 驱动 allowlist/denylist，并增加 registry 机器真源和敏感路径保护。
- 初始版本保持 `BLOCK`，未宣称许可证、人工批准、独立复现或正式发布完成。
