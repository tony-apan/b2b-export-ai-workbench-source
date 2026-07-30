---
title: "PicGo Image Host Adapters"
description: "为 Cloudflare R2、GitHub、腾讯云 COS 和阿里云 OSS 提供统一选择、单图验证和迁移合同。"
type: "adapter-index"
status: "Draft"
owner: "AI"
created: "2026-07-27"
last_updated: "2026-07-27"
sources: ["../../REFERENCES/SRC-20260727-PICGO-IMAGE-HOSTS-OFFICIAL.md"]
related: ["../../TOOLS.md", "../_template.md", "picgo-r2.md", "picgo-github.md", "picgo-cos.md", "picgo-oss.md"]
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
---
# PicGo 图床适配器

> **不是 AllinCMS 默认上传路线。** 图片要进入 AllinCMS 媒体库时，先走 [图片上传统一路由](../image-upload-routing.md) 中的零点击接口串行方案。只有需要与 CMS 解耦的公开 URL、跨系统复用、迁移练习或用户明确指定时，才使用本页。

## 用户先做一个选择

| 你的情况 | 建议先选 |
|---|---|
| 面向全球网站，希望使用对象存储和自定义域名 | [Cloudflare R2](picgo-r2.md) |
| 已有腾讯云账号和 COS 资源 | [腾讯云 COS](picgo-cos.md) |
| 已有阿里云账号和 OSS 资源 | [阿里云 OSS](picgo-oss.md) |
| 只做无敏感、小规模课程演示 | [GitHub](picgo-github.md) |

没有“永远最好”的图床。课程统一使用同一套图片记录和验收，服务商变化只修改 adapter。

## 所有方案共用的通过闸

1. 不在 Markdown 或聊天中保存密钥；
2. 明确 PicGo GUI / CLI / Skill 使用哪份配置；
3. 先上传一张虚拟演示图；
4. 在未登录浏览器中验证最终 HTTPS URL；
5. 在 Markdown 和 CMS 草稿中各引用一次；
6. 记录文件名、hash、目标 key、URL、时间和 uploader；
7. 人工确认后才批量；
8. 批量必须记录成功、失败、跳过、重名和重试。

## 外部图床内部优先级

- 仅在已确定需要外部图床后，国际站演示优先评估 R2；
- 中国云已有资产时直接选择 COS 或 OSS，避免无必要迁移；
- GitHub 仅作教学和迁移练习候选，不作为默认生产图床；
- 当前尚未创建或修改任何真实 bucket、repository、token 或 PicGo 配置。
