---
title: "AllinCMS Image Index E2E Verification"
description: "一张虚拟图片从本地 SHA-256 索引到 AllinCMS media ID、URL 和远端内容指纹的去敏端到端证据。"
type: "evidence"
status: "Verified"
owner: "AI"
created: "2026-07-27"
last_updated: "2026-07-27"
sources: ["Live signed-in AllinCMS image-index verification 2026-07-27", "upload-media-browser.mjs"]
related: ["README.md", "upload-media-browser.mjs", "../../../TEMPLATES/image-manifest.md"]
confidence: "high"
visibility: "public"
redaction_status: "safe-to-publish"
---
# AllinCMS 图片索引端到端验证

## 结论

2026-07-27，一张 1200×800 的虚拟 WebP 完成了以下闭环：

```text
生成本地图片
→ 计算源文件 SHA-256 和兼容 MD5
→ 建立私有语义卡与 prepared 事件
→ 在已打开的目标媒体页中零点击接口上传
→ 取得 media ID 和最终 HTTPS URL
→ 匿名下载并计算远端 SHA-256 / MD5
→ 原子写入 source hash → destination 映射
→ 同文件第二次调用在发请求前被同标题保护拦截
```

```yaml
status: verified_single_image_index_e2e
ui_clicks: 0
filechooser_events: 0
direct_interface_requests: 1
server_action_200: true
media_record_present: true
media_id_present: true
public_url_present: true
backend_reload_persists: true
anonymous_https_get: true
browser_image_decodes: true
source_dimensions: 1200x800
remote_dimensions: 1200x800
source_sha256_recorded: true
remote_sha256_recorded: true
source_and_remote_sha256_equal: false
server_side_transformation_observed: true
same_title_second_call_blocked_before_upload: true
cross_run_sha256_idempotency: not_verified
```

## 关键发现

**不能只存一个 MD5 或 SHA-256。** 本轮源文件与上传输入字节一致，但匿名下载到的远端 WebP 字节数和 SHA-256 不同；图片格式与 1200×800 尺寸保持一致。这说明当前链路中发生了服务端重编码或规范化。

因此图片资产至少要分开记录：

- `source_sha256`：本地源资产的稳定主键；
- `source_md5`：兼容旧系统或人工排查，不作为唯一主键；
- `normalized_upload_sha256`：实际交给上传接口的字节；
- `remote_sha256`：平台最终公开文件的内容指纹；
- `media_id + url + site_alias`：目标平台映射；
- 语义说明、alt、版权、用途：回答“这张图是什么、可在哪里用”。

推荐关系是“一张源资产可映射到多个目标”，而不是把 URL 当图片身份：

```text
source_sha256
└── destinations[]
    ├── cms / image host
    ├── site_alias
    ├── media_id
    ├── url
    ├── remote_sha256
    └── verified_at
```

## 重复保护边界

第二次使用同一本地文件调用当前 adapter 时，因为媒体库已有同标题卡片，调用在上传请求前停止，没有创建第二条媒体记录。

这只证明：

- 当前媒体页可按唯一标题阻止直接重复提交；
- 本次单线程闭环可以保持一一对应。

这不证明：

- 相同 SHA-256、不同文件名会自动复用；
- 两个 AI 或两个标签页并发时不会重复上传；
- 远端成功、本地事件尚未落盘时可以自动恢复；
- 跨站点、R2、GitHub、COS、OSS 能共享同一套远端哈希语义。

## 数据边界

真实站点 key、内部 site ID、媒体 ID、最终 URL和仓库外运行目录未写入本公开证据。完整映射保留在仓库外私有运行区；测试媒体未删除。
