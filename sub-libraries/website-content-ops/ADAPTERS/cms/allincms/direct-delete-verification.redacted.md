---
title: "AllinCMS Direct Media Record Delete Verification"
description: "AllinCMS 零点击媒体记录删除的去敏真实验证、证据边界与公开资产未清理风险。"
type: "evidence"
status: "Working"
owner: "AI"
created: "2026-07-27"
last_updated: "2026-07-27"
sources: ["User-authorized virtual media upload and delete run 2026-07-27", "Private runtime event outside public repository"]
related: ["AI-START-HERE.md", "media-operations-contract.redacted.json", "observed-contract.redacted.json", "upload-media-browser.mjs"]
confidence: "high"
review_after: "2026-08-27"
visibility: "public"
redaction_status: "safe-to-publish"
---
# AllinCMS 零点击媒体记录删除验证

> **历史证据说明：** 本页保留 2026-07-27 当时的完整观察链，便于追溯接口边界。当前默认 SOP 的删除完成口径已经收窄为“精确媒体卡消失 + 精确 RSC 媒体记录消失”；不再执行、讨论或阻断于匿名 URL、对象存储或 CDN 的物理资产复查。

## 结论

2026-07-27 使用一张唯一命名、虚拟生成、用户授权的 WebP 完成：

```text
零点击接口上传
→ media ID / 标题 / URL 四项对账
→ 零点击接口删除
→ 刷新媒体页
→ 媒体卡与 RSC 媒体记录消失
→ 匿名复查原公开 URL
```

结果：**AllinCMS 媒体记录删除成功。** 后续资产 URL 观察只作为历史背景，不属于当前删除完成口径。

## 去敏证据

```yaml
upload:
  status: uploaded_and_verified
  ui_clicks: 0
  filechooser_events: 0
  direct_requests: 1
  server_action_200: true
  media_id_and_url_verified: true

delete:
  status: media_record_deleted_asset_cleanup_unverified
  ui_clicks: 0
  dialog_opens: 0
  direct_requests: 1
  server_action_200: true
  media_card_removed: true
  media_record_removed: true
  contract_verified: true
asset_after_delete:
  anonymous_http_status: 200
  content_type: image/webp
  immediate_check_still_public: true
  later_cache_busted_check_still_public: true
```

公开证据不保存真实站点 key、site ID、media ID、最终 URL、完整 action ID或私有运行目录。

## 观察到的删除合同

```yaml
method: POST
route: /{site_key}/media
request_content_type: text/plain;charset=UTF-8
accept: text/x-component
action_export_name: deleteMediaAction
body:
  - id: "<media_id>"
    siteId: "<site_id>"
dynamic_headers:
  - next-action
  - next-router-state-tree
  - x-deployment-id
response:
  status: 200
  content_type: text/x-component
```

动作 ID、deployment、site ID 和 router tree 都由 adapter 从当前已登录媒体页动态发现，禁止写死。

## 对抗审查

### 可以声称

- 零 UI 点击、零确认框完成了一次直接删除请求；
- 目标媒体卡已从后台消失；
- 刷新后的 RSC 媒体记录中已不存在该目标；
- 删除使用 `mediaId + title + URL + siteKey` 四项精确约束。

### 不可以声称

- OSS / 对象存储中的图片已物理删除；
- 原图片 URL 已失效；
- CDN 缓存已清除；
- 该动作可作为 GDPR、隐私擦除或存储清理证明；
- 对任意媒体、批量删除、关联内容中的引用清理已经验证。

## 强制停止规则

- 删除请求发出后结果不明：不自动重发；
- 四项身份条件有一项不一致：不删除；
- 匹配到零条或多条媒体卡：不删除；
- 用户没有对本次具体媒体明确授权：不删除；
- 需要彻底删除公开资产：停止，改为调查对象存储清理、CDN 失效和引用审计能力。
