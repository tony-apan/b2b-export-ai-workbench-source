---
title: "Source Note: PicGo And Image Hosts"
description: "登记 PicGo、Cloudflare R2、GitHub、腾讯云 COS 和阿里云 OSS 的官方能力、课程适配边界与复查要求。"
type: "source"
status: "Working"
owner: "AI"
created: "2026-07-27"
last_updated: "2026-07-29"
sources: ["https://picgo.github.io/PicGo-Doc/zh/guide/config.html", "https://github.com/Molunerfinn/PicGo/releases/tag/v3.0.1", "https://developers.cloudflare.com/r2/api/s3/api/", "https://developers.cloudflare.com/r2/buckets/public-buckets/", "https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github", "https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits", "https://cloud.tencent.com/document/product/436/36638", "https://help.aliyun.com/zh/oss/user-guide/map-custom-domain-names-5"]
related: ["../../sub-libraries/website-content-ops/TOOLS-INDEX.md", "../../sub-libraries/website-content-ops/ADAPTERS/image-hosts/README.md"]
confidence: "high"
review_after: "2026-10-27"
when_to_read: "选择 PicGo 或 R2、GitHub、COS、OSS 图床方案并核对限制时读本页；价格、配额和发布状态仍需临用前复查。"
keywords: ["PicGo", "Cloudflare R2", "GitHub Pages", "腾讯云 COS", "阿里云 OSS", "图床"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Source Note: PicGo And Image Hosts

## 当前结论

PicGo 是上传客户端，不是图床本身。课程把图片工作流拆成两个可替换层：

1. PicGo GUI、CLI 或 Skill 负责选择文件、命名和发起上传；
2. R2、GitHub、腾讯云 COS、阿里云 OSS 等负责存储、访问域名、权限和生命周期。

PicGo 官方配置文档覆盖 GitHub、腾讯云 COS、阿里云 OSS 等 uploader。Cloudflare R2 提供 S3 兼容 API和公开 bucket / 自定义域名能力，但 PicGo 端需要采用经过核验的 S3 兼容插件、Skill 或其他 adapter，不能假设所有 PicGo 版本原生支持 R2。

## 四种方案的课程定位

| 方案 | 课程定位 | 主要边界 |
|---|---|---|
| Cloudflare R2 | 国际公开站点的推荐候选 | 需要配置公开访问或自定义域名；PicGo 接入方式需单独验证 |
| GitHub | 无敏感演示、小规模文档和迁移练习 | 仓库与 GitHub Pages 有文件、仓库和带宽边界，不应默认当生产图片 CDN |
| 腾讯云 COS | 面向中国团队、已有腾讯云资产的候选 | bucket 权限、地域、加速域名、HTTPS 和跨域需逐项确认 |
| 阿里云 OSS | 面向中国团队、已有阿里云资产的候选 | endpoint、bucket、权限、自定义域名和 HTTPS 需逐项确认 |

## 不写入知识库的内容

- AccessKey、SecretKey、token、cookie、完整 PicGo 配置；
- 真实 bucket 名、账号 ID 或未经允许的生产域名；
- 未经单图验证的批量上传命令；
- 把 GitHub raw 地址、R2 开发域名或临时签名 URL 当成永久公开 URL 的强结论。

## 每次演示的复查项

- PicGo 版本和实际 uploader；
- GUI 与 CLI 是否读取同一份配置；
- 目标 bucket / repository 是否为课程演示环境；
- 自定义域名、HTTPS、公开权限、缓存和删除恢复；
- 单图 URL 是否在未登录浏览器中打开；
- 批量上传的成功、失败、跳过、重名和重试记录。
