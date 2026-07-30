---
title: "AllinCMS Direct Serial 10 Verification"
description: "10 张虚拟图片通过单图 Server Action 串行调用上传的去敏证据、异常处置和未验证边界。"
type: "evidence"
status: "Verified"
owner: "AI"
created: "2026-07-27"
last_updated: "2026-07-27"
sources: ["Live signed-in AllinCMS media-library verification 2026-07-27", "observed-contract.redacted.json"]
related: ["README.md", "upload-media-browser.mjs", "observed-contract.redacted.json"]
confidence: "high"
visibility: "public"
redaction_status: "safe-to-publish"
---
# AllinCMS 10 张纯接口串行上传验证

## 结论

2026-07-27，在用户明确授权的虚拟演示站点中，10 张不同文件名的 1200×800 WebP 通过 `uploadAllinCmsMediaDirect()` **串行调用 10 次**完成上传与验收。

```yaml
direct_single_requests_serial_batch_10: verified
files: 10
uploaded_and_verified: 10/10
ui_clicks: 0
filechooser_events: 0
one_direct_interface_request_per_file: 10/10
server_action_200: 10/10
media_record_present: 10/10
media_id_present: 10/10
backend_reload_persists: 10/10
anonymous_https_get: 10/10
browser_image_decodes: 10/10
final_media_card_exactly_once: 10/10
one_multipart_request_with_10_files: not_verified
parallel_direct_batch: not_verified
cross_run_idempotency: not_verified
partial_failure_recovery: not_verified
```

## 执行方式

- 每张图单独调用一次当前部署的 Next Server Action；
- 完成该张的 HTTP、媒体记录、媒体 ID、刷新持久化、匿名 HTTPS 和图片解码验证后，才发送下一张；
- 没有点击上传按钮，没有触发文件选择器，没有导出 Cookie、Token 或 Authorization；
- 文件名、真实站点 key、内部 site ID、媒体 ID、对象 key、动作值和最终 URL 均未写入公开证据。

## 异常处置证据

第九张首次调用出现客户端 `playwright.evaluate exceeded its deadline`。系统没有立即重发，而是：

```text
停止后续发送
→ 刷新并读取媒体库
→ 按唯一标题确认第九张记录不存在
→ 在同一用户授权范围内受控继续第九张
→ 第九张全链验证通过后才发送第十张
```

这证明了“报错后先对账”的安全顺序。当前总控只在延迟后精确确认远端不存在时有限重试；若媒体库已经存在同标题记录，只补验证，不得再次上传。

## 可复用边界

本轮证明的是：10 张可以用单图纯接口**串行**完成。它不证明：

- 一次 multipart 请求携带 10 张；
- 多请求并发；
- 任意大批次真实远程长跑的总耗时和平台节流；当前控制器本地已覆盖 12 张且不设数量上限；
- 多次运行之间的幂等；
- 部分失败后的自动恢复；
- 删除、覆盖、孤儿对象清理；
- 产品 / 文章绑定和前台渲染。
