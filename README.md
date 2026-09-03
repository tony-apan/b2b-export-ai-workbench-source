<!--
Repository metadata:
title: "B2B Export AI Workbench"
description: "给外贸人的增长工作台：把做外贸网站、B2B 文章、开发信、LinkedIn、SEO/GEO、询盘、展会、短视频的方法、模板和工具放在一个仓库里，让 AI 按你的资料直接帮你干活。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-09-02"
sources: ["AGENTS.md", "wiki/00_meta/private-master-and-sub-library-model.md", "Tony public MIT decision 2026-09-02"]
related: ["CONTEXT.md", "wiki/index.md", "AGENTS.md", "CLAUDE.md", "MANIFEST.md", "RELEASE.md", "wiki/00_meta/current-focus.md", "wiki/00_meta/in-repository-agency-runtime-model.md", "sub-libraries/README.md", "sub-libraries/agency-operations/README.md"]
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
-->
# B2B Export AI Workbench

一个给外贸人用的“增长工作台”。里面装的不是软件，而是**做外贸要用到的方法、模板和工具**：怎么建网站、怎么写 B2B 文章、怎么开发信、怎么做 LinkedIn、怎么弄 SEO/GEO、怎么回询盘、怎么参加展会、怎么做短视频——全都整理成了人和 AI 都能读的步骤。

**它最大的用法很简单：把这个仓库交给一个 AI，然后告诉它你要干什么，它照着里面的方法帮你干。**

---

## 🚀 快速上手（1 分钟看懂怎么用）

你只需要做两件事：

1. **装一个能读写本地文件的 AI**（例如 Claude Code、Codex 之类，或支持 skills 的 AI 助手）。
2. **把下面这一个代码块整体复制发给它，末尾补上你要干的事。**

```text
【B2B 外贸工作台 · 一键启动】把本块整体复制发给你的 AI。
■ 仓库：https://github.com/tony-apan/b2b-export-ai-workbench-source.git
■ 第一步：clone 后安装建站工具包并自测：
   python3 sub-libraries/website-content-ops/SKILL-INSTALL/install.py
   （Windows 用 install.cmd）缺 Node/Python 给我可复制命令，不要跳过。
■ 第二步：我要做的事是：______（例：建网站 / 写 B2B 文章 / 外贸增长建议）
■ 规则：建站类读 sub-libraries/website-content-ops/，方法类先读 wiki/index.md；
   删除/覆盖/发布先列清单等我逐条批准；凭据只进环境变量；情况不明先问不要猜。
```

装完之后直接用大白话提需求就行，AI 会自己路由到对应方法：

- **建网站 / 更新网站**：给它客户资料（PDF/DOCX/表格/网站/图片）+ AllinCMS 账号，其余全自动；
- **写 B2B 英文文章**：给它产品/公司资料，先出提纲和事实清单再动笔；
- **外贸增长咨询**（开发信/LinkedIn/SEO/展会…）：说清你的行业、目标市场和现状。

---

## 这个仓库里到底有什么

| 你想干什么 | 去哪里 | 成熟度 |
|---|---|---|
| **从资料建一个 B2B 网站**（AllinCMS，纯接口一条龙） | [website-content-ops（建站工具包）](sub-libraries/website-content-ops/README.md) | 最成熟，有真实建站证据 |
| **更新现有网站的产品 / 文章** | 同上 → [内容更新流程](sub-libraries/website-content-ops/TOOLS/interface-kit/NEW-SITE-ONEPASS.md) | 较成熟，需审查后写入 |
| **把公司资料写成英文 B2B 文章** | [B2B 文章规范](sub-libraries/website-content-ops/PLAYBOOKS/id-0001-b2b-seo-article-standard.md) | 方法成型，效果待真实数据 |
| **外贸增长各渠道打法**（开发信 / LinkedIn / SEO / GEO / Ads / 展会 / 短视频 / 询盘回复 / 销售电话） | [Playbooks 总入口](wiki/30_playbooks/index.md) | 多数为可用方法 + 部分待验证 |
| **整理公司业务事实**（客户是谁 / 卖什么 / 痛点 / 证据） | [Business 底座](wiki/40_business/index.md) | 框架可用，内容需自己填 |
| **按渠道看打法**（SEO、GEO、LinkedIn、外联、Ads、短视频…） | [Channels 总入口](wiki/50_channels/index.md) | 方法层 |
| **把做过的项目/对话沉淀成可复用课程** | [课程入口](wiki/90_outputs/courses/index.md) | 框架 + 少量内容 |
| **做多客户代运营（私域运行区管理）** | [Agency Operations](sub-libraries/agency-operations/README.md) | 草稿阶段，本地框架完成 |
| **注册成 AI 可直接调用的 Skill** | [Skill 安装说明](sub-libraries/website-content-ops/SKILL-INSTALL/README.md) | 源码可用 |

> 想看全部可独立交付模块的机器清单，去 [sub-libraries/README.md](sub-libraries/README.md)。

---

## 新手常见问题

**Q：我需要会编程吗？**
A：不用。装好 AI 后，复制上面的话发给它即可。仓库里的命令是给 AI 读的，不是给你背的。

**Q：它真的能帮我建一个能用的网站吗？**
A：能。已用真实客户资料从零建出过 B2B 站并通过审计；但这套流程需要：一个 AllinCMS 账号、一份客户资料、以及你对“上传/发布”的逐次批准。它不等于“一键生成”，而是“AI 按方法干 + 你点头 + 事后验收”。

**Q：我的客户资料 / 账号密码安全吗？**
A：仓库公开，但**真实客户资料、账号、密码、登录态绝不要提交进这个仓库**。资料和运行数据只放在你自己电脑上的私有目录，由你和 AI 处理。

**Q：这些方法靠谱吗？**
A：仓库对每块内容都标了成熟度：有真实证据的写“有证据”，只是框架的标“Seed / 待验证”，没效果数据的不吹。**别把“方法存在”当成“结果已验证”。** 详细的证据口径见 [check-mechanism-map.md](wiki/00_meta/check-mechanism-map.md)。

---

## 许可证

本仓库（B2B Export AI Workbench）母库原创内容以 **MIT License** 对外提供，可以自由使用、修改、再分发（保留版权声明即可）。完整文本见 [LICENSE](LICENSE)，范围说明见 [LICENSE.md](LICENSE.md)。

几点说明：

- 真实客户资料、账号、凭据不属于授权范围——它们本来就不该进仓库。
- 第三方名称/商标（AllinCMS、LinkedIn、Google 等）和通过外链加载的图片不随 MIT 授权。
- 各子库可独立声明自己的许可证；以该子库的 LICENSE 为准。
- 仓库仍在持续演进，`release_status: BLOCK` 表示还没有做过正式“稳定版”资格认定，不代表内容不可读或不可用。

---

## 面向维护者 / 想深入的人

- 仓库结构、发布状态与机器约束：[CONTEXT.md](CONTEXT.md)、[MANIFEST.md](MANIFEST.md)、[RELEASE.md](RELEASE.md)、[AGENTS.md](AGENTS.md)
- 知识导航：[wiki/index.md](wiki/index.md)
- 当前在做的事与卡点：[current-focus.md](wiki/00_meta/current-focus.md)
- 检查结果能证明什么：[check-mechanism-map.md](wiki/00_meta/check-mechanism-map.md)
- 本地全量校验（推送前必跑）：`bash scripts/pre-push-check.sh`，7 步全绿才推。

**边界**：即使仓库公开，真实客户数据、凭据和经营数据仍只进独立私有运行区，不进提交；一个模块的结构/测试通过不代表另一个模块或生产环境成立。
