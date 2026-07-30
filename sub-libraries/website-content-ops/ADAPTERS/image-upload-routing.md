---
title: "Image Upload Routing"
description: "统一决定图片进入 AllinCMS 媒体库还是外部图床，固定小白默认路线、接口优先级、回退和停止条件。"
type: "tooling"
status: "Working"
owner: "AI"
created: "2026-07-27"
last_updated: "2026-07-27"
sources: ["Tony decision 2026-07-27", "cms/allincms/media-operations-contract.redacted.json"]
related: ["README.md", "cms/allincms/AI-START-HERE.md", "cms/allincms/media-metadata-and-ai-vision-sop.md", "image-hosts/README.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# 图片上传统一路由

## 先判断图片最终要去哪里

| 目标 | 默认方案 | 不需要先做 |
|---|---|---|
| 图片要进入 AllinCMS 媒体库，并用于 AllinCMS 产品、文章或页面 | **AllinCMS 零点击接口逐张串行上传** | 不需要 PicGo，不需要先建 R2 / GitHub / COS / OSS |
| 图片要获得与 CMS 解耦的外部公开 URL，或要跨多个系统复用 | PicGo + R2 / GitHub / COS / OSS | 不需要先进入 AllinCMS |
| AllinCMS 内部接口发生漂移 | 停止写入，先只读对账；用户明确批准后才使用语义化 UI 回退 | 不允许偷偷切换坐标点击或重复上传 |

## 面向小白的默认路线

只要用户说“把图片上传到 AllinCMS”，AI 就按下面顺序执行，不再让用户选择图床：

```text
1. 用户登录并打开准确的 https://workspace.laicms.com/{site_key}/media
2. AI 逐张读图，结合公司 / 产品 / 页面知识生成候选 title、alt、caption 和结构化 metadata
3. AI 运行只读环境预检
4. AI 调用 uploadAllinCmsMediaSerial()，永久禁止并发
5. 每张：写 prepared → 单张接口上传 → 自动刷新 → 验证卡片、media ID、URL、匿名访问和解码
6. 原子写入本地私有 image-index.json
7. 若用户授权且本项提供 alt / caption：只发 1 次元数据更新请求，再做有限次数只读刷新复核
8. 当前图片的上传、索引和所请求元数据全部闭环后，才进入下一张
9. 元数据结果不明确：保留媒体记录，停止本批，禁止重发元数据、禁止重传图片
10. 上传报错：先延迟并只读对账；确认已存在则补齐，确认不存在才由总控有限重试当前图片；对账不明确则停止
```

“自动刷新”是 adapter 的页面导航，不是模拟点击。若该媒体页保持在前台，用户会看到图片卡逐张增加；adapter 不承诺强制抢焦点或保持某个滚动位置。

## AllinCMS 固定优先级

```text
P1  uploadAllinCmsMediaSerial()       默认批次入口，任意数量、严格串行
P2  uploadAllinCmsMediaDirect()       总控内部使用的单张上传原语
P3  updateAllinCmsMediaMetadataDirect() 单张元数据接口，只写一次并有限只读复核
P4  reconcileAllinCmsMediaDirect()    只读上传对账和断点恢复，不发上传请求
P5  uploadAllinCmsMediaBatch()        语义化 UI 回退，仅接口漂移且用户明确同意
P6  PicGo + 外部图床                 仅目标不是 AllinCMS 媒体库或用户明确指定
```

不得把 UI 回退或外部图床当成 P1 失败后的自动降级。

## 本地图片索引

`imageIndexPath` 必须位于客户自己的私有运行区，不得提交公开母库。索引用源文件 SHA-256 作为主键，并分别保存：

- 源文件 SHA-256 / MD5；
- 规范化上传文件 SHA-256 / MD5；
- AllinCMS media ID、标题、URL 和 MIME；
- 匿名下载内容 SHA-256 / MD5；
- 图片 description、alt、caption、用途备注和结构化 AI metadata；
- 上传状态，以及 `metadata_verified / metadata_update_failed_before_request / metadata_update_ambiguous` 元数据状态和时间线。

同一源文件即使改名，只要已有 verified 映射，默认复用，不重复上传。`prepared` 阶段尚未发请求，若恢复时发现远端同标题记录，必须停止为预存标题冲突，不能自动认领；`request_started` 对账成功时保留规范化上传哈希。同一站点索引使用 `.lock` 单写者锁，避免两个 AI 同时操作。结束时还必须检查 `cleanup.imageIndexLockReleased === true`；若锁清理失败，保留本轮结果但阻断下一轮，先人工检查客户私有运行区。


## AI 读图和 AllinCMS 字段边界

- 上传弹窗本身没有 title、alt、说明输入框；
- 上传后编辑弹窗已观察到 `title`、`alt`、`caption`；
- adapter 已提供 `updateAllinCmsMediaMetadataDirect()`，并在一次获授权虚拟样本中验证稍后刷新后三个字段持久化；
- `description` 没有对应 AllinCMS 字段，只保留在私有索引，必要时改写为短 `caption`；
- 元数据写入只允许一次；写后有限刷新重读，不因短暂延迟自动重发；
- 元数据更新失败不得删除或重新上传图片，并停止下一张；
- 同一源 SHA-256 已有 verified 映射时，只更新本地元数据并复用原 media ID / URL；
- 完整规则见 [AllinCMS 图片元数据与 AI 读图 SOP](cms/allincms/media-metadata-and-ai-vision-sop.md)。

## 何时使用外部图床

只有以下情况才进入 [PicGo 图床选择](image-hosts/README.md)：

- 用户明确要 R2、GitHub、COS 或 OSS；
- 图片需要独立于 AllinCMS 生命周期；
- 需要跨多个 CMS / 社媒 /文档复用同一公开 URL；
- AllinCMS 不适用，且用户接受外部存储的权限、成本和迁移责任。

外部图床是独立能力和迁移练习，不是 AllinCMS 图片上传的默认前置条件。
