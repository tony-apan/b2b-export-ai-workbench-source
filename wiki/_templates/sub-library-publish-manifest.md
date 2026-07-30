---
title: "Sub-library Publish Manifest Template"
description: "可发布子库的包含、排除、品牌变量、版本和验收清单模板。"
type: "template"
status: "Working"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-07-29"
when_to_read: "规划一个可独立发布子库，需要定义包含排除、版本、品牌变量、构建与验收清单时。"
keywords: ["子库发布", "publish manifest", "包含排除", "版本", "验收清单"]
template_usage: "manual-copy"
sources: ["../00_meta/sub-library-contract.md"]
related: ["../00_meta/private-master-and-sub-library-model.md", "../00_meta/sub-library-contract.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# 子库发布清单模板

```yaml
package_id: website-content-ops
package_name: "{{品牌名}} AI 建站内容运营子库"
source_path: sub-libraries/website-content-ops
output_name: website-content-ops-latest
version: 0.1.0
visibility: public
release_mode: latest-only

include:
  - README.md
  - START-HERE.md
  - AGENTS.md
  - INTAKE.md
  - PLAYBOOK.md
  - TOOLS.md
  - TEMPLATES/**
  - EXAMPLES/**
  - ADAPTERS/**
  - QA-CHECKLIST.md
  - SOURCES.md
  - BRAND.md
  - CONTACT.md
  - VERSION.md
  - WRITEBACK.md
  - MANIFEST.md

exclude:
  - "**/.DS_Store"
  - "**/.env*"
  - "**/*secret*"
  - "**/*token*"
  - "**/workspace/**"
  - "**/private/**"
  - "**/drafts/**"

required_placeholders:
  - 品牌名
  - 官网
  - 联系邮箱
  - 支持入口
  - 更新地址
  - 版权主体
  - 许可证

adapters:
  image_host: picgo
  cms: "{{首个CMS}}"

checks:
  - no_credentials
  - no_private_paths
  - no_client_data
  - fictional_examples_labeled
  - license_reviewed
  - internal_links_valid
  - end_to_end_demo_passed
  - human_release_approved
```

> `workspace/**` 是使用者运行时产生的公司资料和任务记录，默认不进入公开发布包，也不能自动回传。
