---
title: "Agency Operations Install"
description: "说明在母库根目录内使用本子库、初始化私有运行区、升级和卸载时的数据保留边界。"
type: "installation-guide"
status: "Working"
owner: "AI"
created: "2026-08-01"
last_updated: "2026-08-01"
sources: ["Tony multi-client agency runtime decision 2026-08-01"]
related: ["README.md", "PLAYBOOK.md", "VERSION.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Install

本子库随母库源码存在，不单独安装为 Skill。用户在母库根目录运行初始化命令生成被 Git ignore 的 `customer-runtime/`。

升级子库不会自动改写已有 runtime。schema 变化必须通过显式迁移；没有迁移器时 BLOCK。卸载子库源码前先导出或保留 runtime，删除源码不等于删除客户数据；删除客户数据必须单独人工确认。
