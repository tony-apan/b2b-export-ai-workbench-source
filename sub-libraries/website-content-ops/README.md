---
title: "Website Content Operations Sub-library"
description: "面向外贸企业和内容运营人员的 AI 建站内容运营入口：说明能做什么、如何直接交给 AI 执行、没有 AllinCMS 账号时如何联系支持，以及 Preview 阶段的单样本与生产边界。"
type: "sub-library"
status: "Working"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-09-01"
sources: ["Tony conversation 2026-07-26", "Tony README and AI onboarding decision 2026-07-30"]
related: ["START-HERE.md", "CONTACT.md", "COURSE-MAP.md", "MENTAL-MODEL.md", "AGENTS.md", "PLAYBOOK.md", "MANIFEST.md", "RUNTIME-CONTRACT.json", "RUNTIME-INTEGRATION.md", "SKILL.md", "ADAPTERS/image-upload-routing.md", "ADAPTERS/cms/allincms/AI-START-HERE.md", "ADAPTERS/cms/allincms/INTERFACE-INDEX.md", "ADAPTERS/cms/allincms/interface-registry.json"]
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
keywords: ["建站内容运营", "外贸网站", "AllinCMS", "CMS", "图片上传", "内容工作流", "AI 执行", "新手入门"]
state_source: "MANIFEST.md"
state_projection: ["release_status", "preview_publication_status", "license_status"]
release_status: "Preview"
preview_publication_status: "Published"
license_status: "cleared"
---
# AI 建站内容运营

把产品资料交给 AI，**全程 API** 自动建站、更新、验收 AllinCMS 网站——你不用懂 CMS，正常路径连浏览器都不用开。

## ✨ 它能干什么

| 能力 | 说明 |
|---|---|
| 🏗️ 一条龙建站 | 一份 PDF/表格 → 完整网站（产品、7 页主题、询盘表单、品牌色），半小时量级 |
| 🔄 网站更新 | 产品/图片/分类/页面模块接口直写 + 回读精确校验；批量改动零误差 |
| ✍️ B2B 文章 | 事实 → 提纲 → 成稿 → 对抗评审 → 写入（全新文章远程创建暂 BLOCK，已有文章可审查后更新） |
| 🔍 上线验收 | 7 层 61 项审计（结构/链接/SEO/表单/视口），交付即报告 |
| 🛠️ 遇阻自修 | 接口与文档不一致时，AI 开浏览器**只读摸索**定位根因，回接口层修复并沉淀配方 |
| 🧠 108 坑位库 | 实测问题可检索（现象→根因→修复），别的 AI 踩过的坑不用再踩 |

> **为什么全程 API？** 不模拟人点后台：快一个量级、可精确回读校验、不怕 CMS 界面改版。浏览器只是遇阻时的探索工具，不是执行通道（方法论见 [AI-START-HERE §0](ADAPTERS/cms/allincms/AI-START-HERE.md)）。

## 🚀 安装并启动（一次搞定）

**推荐：把下面整块复制给任何能读写文件的 AI（Claude Code / Codex 等），它替你装完并开始：**

```text
【B2B 建站工具包 · 一键启动】把本块整体复制发给你的 AI。
■ 仓库：https://github.com/tony-apan/b2b-export-ai-workbench-source
■ 第一步：clone 后运行 python3 sub-libraries/website-content-ops/SKILL-INSTALL/install.py
   （Windows 用 install.cmd）自动安装+自测；缺什么给我可复制命令，不要跳过。
■ 第二步：向我要 ① AllinCMS 账号（邮箱+密码，换 token 后密码即弃并提醒我改密）
   ② 客户资料（PDF/DOCX/表格/网站/图片）③ 想要的网址前缀（可选）。
■ 第三步：按 NEW-SITE-ONEPASS.md 13 步建站；事实与坑查 RUNBOOK-ANYONE.md。
■ 红线：删除/覆盖/发布必须逐条列清单等我批准；凭据只进环境变量；情况不明先问不要猜。
```

想手动装也只是一条命令（自测需 Node.js ≥ 20.9）：

```bash
git clone https://github.com/tony-apan/b2b-export-ai-workbench-source.git && \
python3 b2b-export-ai-workbench-source/sub-libraries/website-content-ops/SKILL-INSTALL/install.py
```

## ⚠️ 三条红线（人和 AI 都必须遵守）

1. **上传/覆盖/删除/发布**：AI 必须逐条列清单、等你点头，一个都不许先斩后奏；
2. **凭据**：只进环境变量，不写文件不入日志；没有 AllinCMS 账号 → [CONTACT.md](CONTACT.md) 联系开通；
3. **口径**：Public Preview（非 Stable）——先单样本验收，再批量；全新文章远程创建暂 BLOCK。

## 📖 进阶入口

| 想做什么 | 读什么 |
|---|---|
| 13 步从零建站 | [NEW-SITE-ONEPASS.md](TOOLS/interface-kit/NEW-SITE-ONEPASS.md) |
| 查坑 / 改动不生效诊断树 | [RUNBOOK-ANYONE.md](TOOLS/interface-kit/RUNBOOK-ANYONE.md) |
| 页面模块白名单（37 块） | [MODULES.md](TOOLS/interface-kit/MODULES.md) |
| 上线验收标准（61 项） | [site-acceptance-v2.md](TOOLS/interface-kit/templates/site-acceptance-v2.md) |
| AI 执行入口 / 登录与回落 | [START-HERE.md](START-HERE.md) · [AI-START-HERE.md](ADAPTERS/cms/allincms/AI-START-HERE.md) |
| 文章与 SEO 打法 | [PLAYBOOKS/](PLAYBOOKS/README.md) |
| 版本 / 状态 / 变更 | [MANIFEST.md](MANIFEST.md) · [CHANGELOG.md](CHANGELOG.md) |

**当前版本**：`0.4.0-preview.1` Public Preview（2026-09-03 发布；许可 cleared，三张 source card 已逐卡审查）。Stable 正式资格（真人批准链/签名 tag/外部 workflow）仍未闭合，继续阻断。
