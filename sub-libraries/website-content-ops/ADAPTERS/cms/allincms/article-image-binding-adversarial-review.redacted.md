---
title: "AllinCMS 正文图片逐 occurrence 原位替换对抗复核"
description: "记录正文图片恢复后的本地控制器证据、负向探针、唯一执行入口和真实远程验证边界。"
type: "evidence"
status: "Working"
owner: "AI"
created: "2026-07-27"
last_updated: "2026-07-27"
sources: ["article-image-binding.mjs", "article-image-binding.test.mjs", "article-image-binding-contract.json", "Observed A/B/A draft binding 2026-07-27"]
related: ["AI-START-HERE.md", "README.md", "article-operations.md", "media-metadata-and-ai-vision-sop.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# AllinCMS 正文图片逐 occurrence 原位替换对抗复核

> **历史审查快照：** 本页记录审查当时的状态；当前子库状态以根 `MANIFEST.md`、`VERSION.md` 和 `RELEASE.md` 为准。

## 结论

```yaml
review_scope: local_controller_and_sop
verdict: PASS
article_image_tests: 50/50
all_adapter_tests: 115/115
real_remote_mutation_in_this_review: false
published_article_in_this_review: false
cross_deployment_claim: not_made
```

“正文图片现在不能用”不再是正确结论。当前应使用以下分层表述：

> 正文图片逐 occurrence 原位替换能力已经恢复并加固；本地控制器和 SOP 通过对抗复核。2026-07-27 已有当前部署 A/B/A 虚拟草稿的限定真实证据；本次加固没有再次写入远端，因此新部署或新站点仍需在下一篇获批草稿中做一次限定复验。

本结论只放行**草稿正文图片绑定控制器**，不等于整个 `website-content-ops` 子库可发布。子库 `MANIFEST.md` 继续保持 `release_status: BLOCK`。

## 唯一稳定流程

```text
创建 manifest schema 2
→ 严格串行上传或复用独立资产
→ 复核媒体记录、media ID、URL、匿名响应、图片解码和源 SHA-256
→ 打开精确且已登录的文章 update 页面
→ bindAndSaveAllinCmsArticleDraftDirect()
  → 逐 occurrence 重读源图并校验 SHA-256 / MD5
  → 逐 occurrence 按原位置绑定 URL、Alt、Caption
  → audit 全部为 0
  → 生成 bindingProof
  → 保存边界再次逐 occurrence 重读和校验
  → 整篇草稿只发送一次 mode=update
  → 后台完整回读
  → 编辑器非 500、图片数量、解码、Caption、草稿标识健康检查
  → operation lock 内原子写 manifest
```

“逐图”是逐 occurrence 校验、绑定和进度展示，不是逐图远程保存文章。正文无论有几张图片，远程文章写请求始终只有一次。

## 对抗探针

| 探针 | 预期 | 当前结果 |
|---|---|---|
| 相同字节来自两个路径，只修改第二个路径 | 保存前阻断 | PASS |
| 手写合法 Slate 图片节点但没有 proof | 请求前阻断 | PASS |
| 有合法 proof/context，但绕过总入口直接调用 direct save | 因缺 operation guard 阻断 | PASS |
| build 后修改源图 | 请求前阻断 | PASS |
| build 后修改 content 或 proof | 请求前阻断 | PASS |
| 不同源资产手工共用 media ID 或 URL | 构建时阻断 | PASS |
| schema 1、缺 occurrence MD5、asset 缺 occurrence 路径 | 要求重建 manifest | PASS |
| 相对 manifest/lock 路径或不安全 site/post 路由段 | 建锁前阻断 | PASS |
| 第二个文章写任务 | 构建和请求前阻断 | PASS |
| 合法双图流程 | 逐 occurrence 进度不重叠，整篇只请求一次 | PASS |
| 远程保存已完成但 manifest 写失败 | 禁止自动重发 | PASS |

## 数据完整性合同

### Manifest schema 2

- `asset` 可以为相同字节复用同一远端媒体，但必须保存全部 `sourceFiles[]`；
- 每个 `occurrence` 独立保存 `sourceReference`、绝对 `sourceFile`、SHA-256、MD5、位置、锚点、Alt、Caption 和语境；
- 每个 occurrence 的当前字节必须同时匹配 `occurrence.assetId`、occurrence 哈希和 asset 哈希；
- schema 1 不静默兼容，必须重建。

### Binding proof

含图片正文必须使用 `buildAllinCmsSlateContent()` 在 operation 内生成的 `bindingProof`。proof 绑定：

- 文章与原始 Markdown 哈希；
- occurrence 顺序、源路径和源 SHA-256；
- asset、media ID、URL；
- 最终 Slate 内容哈希；
- audit 和 proof 哈希。

其他 AI 不得手写或修改 proof，也不得直接使用 `saveAllinCmsArticleDraftDirect()` 保存图片正文。

### 两层锁

- `${manifestPath}.${siteKey}.${postId}.operation.lock`：覆盖构建、proof、一次保存、回读、编辑器健康检查和 manifest 落盘；
- `${manifestPath}.lock`：保护 manifest 的原子临时文件写入和 rename。

任一锁存在都默认停止。禁止自动删除、抢锁或另开标签页绕过。

## 故障语义

如果文章请求可能已经发出，任何错误都不得自动重发。特别是远程保存和回读完成、但本地 manifest 写失败时：

```yaml
status: article_manifest_write_failed_after_save
requestMayHaveSucceeded: true
automaticRetryAllowed: false
```

下一步只能只读核对远端草稿和本地运行记录，再由人决定如何修复本地 manifest；不能再次保存文章来“补 manifest”。

## 当前仍未证明

- 本次加固后的真实远程写入复验；
- 新部署、新站点或 Server Action 合同漂移后的兼容性；
- 公开主题是否正确输出正文图片 Alt；
- HTML `<img>`、引用式 Markdown 图片、一行多图、图文同一行、表格内图片和更复杂 Slate 节点；
- 发布动作；正文图片绑定默认只允许草稿 `mode=update`。

这些是明确验证边界，不构成“正文图片必须暂停使用”。下一次获批草稿只需按唯一入口做一个限定复验，不需要重新抓接口或回退模拟点击。

## 当前验证命令

```bash
cd ADAPTERS/cms/allincms
npm run test:article-images
npm test
node --check article-image-binding.mjs
node --check article-image-binding.test.mjs
python3 -m json.tool article-image-binding-contract.json
```
