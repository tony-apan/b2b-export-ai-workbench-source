---
title: "Version"
description: "建站内容运营子库的版本、兼容性、变更和更新入口。"
type: "version"
status: "Working"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-07-28"
sources: []
related: ["CONTACT.md", "MANIFEST.md", "MENTAL-MODEL.md", "CHANGELOG.md", "RELEASE.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Version

- Package ID：`website-content-ops`
- Version：`0.3.2-preview.1`
- Publication：Public Preview / Published（2026-07-30）
- Changelog：[CHANGELOG.md](CHANGELOG.md)
- Release guide：[RELEASE.md](RELEASE.md)
- Update URL：`https://fluxpedal.example/content-lab/updates`（虚拟演示）
- Compatibility：本地 Markdown；Obsidian 仅为参考查看器；可读取本地文件的 AI agent；图床与 CMS 通过 adapter 接入。

## 0.3.2-preview.1

- 当前目录是可独立发布的任务子库；母库只作为可选的治理与来源上游，不是运行时依赖；
- 注入 FluxPedal Motors 虚拟品牌、电动自行车电机公司与产品示例；
- PicGo 图床范围确定为 Cloudflare R2、GitHub、腾讯云 COS 和阿里云 OSS；
- 课程入口收缩为“工具 → 知识 → 小样 → 验证写回”四步；
- 新增客户聊天到 SEO/GEO 内容的第一条虚拟闭环；
- 已有 AllinCMS 限定部署与本地 Adapter 证据，Public Preview 已独立发布；Stable qualification、跨部署迁移和生产稳定性仍未完成。

## 0.2.0-draft

- 把课程目标从“学会参考工具按钮”升级为“理解底层模型并迁移到陌生工具”；
- 新增 `MENTAL-MODEL.md`；
- 建立 Why / Model / Reference implementation / Transfer exercise 四层教学结构；
- 新增陌生工具调查、对象字段映射、单样本和能力验收规则；
- 将 Obsidian、PicGo 和首个 CMS 明确为参考实现；
- 发布前除真实链路外，还必须完成第二工具迁移验证；
- 增加从建站到 SEO、社媒或主动营销等相邻业务任务的重映射要求。

## 0.1.0-draft

- 建立子库统一入口、AI 协议、intake、playbook、QA 和写回规则；
- 建立公司、产品、文章、图片和发布记录模板；
- 定义 PicGo 单图测试、CMS 单条草稿和浏览器验证闸；
- 尚未完成品牌注入和真实 CMS 端到端演示。
