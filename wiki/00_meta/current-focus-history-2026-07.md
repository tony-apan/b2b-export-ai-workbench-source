---
title: "Current Focus History 2026-07"
description: "无损保存 2026 年 7 月 current-focus 中的结构治理、AllinCMS 真实验证、已解除阻断与剩余边界，供追溯历史判断；日常执行请读取 current-focus.md。"
type: "meta"
status: "Archived"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-07-29"
sources: ["Tony conversation 2026-07-26", "Tony decisions 2026-07-27", "Adversarial structure review 2026-07-26", "Adversarial structure review 2026-07-28"]
related: ["current-focus.md", "module-registry.md", "module-expansion-sop.md", "open-questions.md", "../../sub-libraries/website-content-ops/COURSE-MAP.md", "structure-adversarial-review-20260728-discovery-v2.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Current Focus History — 2026-07

> 本页是从 `current-focus.md` 无损迁出的历史证据，不再承担当前任务路由。当前状态只以 [current-focus.md](current-focus.md) 为准。


## Current Focus

**Website Content Operations**：从网站、资料和客户聊天建立公司 / 产品 / ICP / 客户语言知识，再完成内容、图片、图床、CMS 草稿、验证、迁移和写回。

入口：[从这里开始](../../sub-libraries/website-content-ops/START-HERE.md)

## Execution State

`Blocked`：它是当前唯一焦点。AllinCMS 图片默认路线已经固定为“运行预检 → AI 逐图读图并生成候选 → `uploadAllinCmsMediaSerial()` 严格串行零点击上传 → 自动刷新验收 → 原子写入私有索引 → 获批后单次写入 `title / alt / caption` → 有限只读复核”；媒体单图和 10 张串行已有真实远程证据，文章当前部署又完成 11 篇完整字段串行 `update → publish` 真实远程验证。Markdown 正文图片已固定使用 `article-image-binding.mjs`，按资产层与 occurrence 层完成 A/B/A 原位绑定草稿真实验证；字符串 Caption 导致编辑页 500 的风险已转化为请求前预检和保存后编辑器健康闸。媒体 29 项、文章图片 50 项与文章生命周期 36 项本地测试合计 115 项通过；编辑器健康闸现要求 Slate 编辑器存在、图片数量精确、全部解码、Caption 顺序一致且草稿标识仍存在。当前仍阻塞的是跨部署正文/封面合同、表格与更多复杂 Slate、失败回滚、公开主题 Alt 产品缺口、任意大于 11 篇的文章长跑、失败恢复和外部图床迁移正式课程。PicGo、R2、GitHub、COS、OSS 仍是外部图床备选，不再阻塞 AllinCMS 默认上传与草稿正文绑定。

## 2026-07-28 知识库结构治理闸

- **已通过**：分层 index、文档 ID 重复/格式检查、母库与 `website-content-ops` 子库结构检查、母库/子库候选包构建、checksum 和制品验收。
- **已修复**：`.gitignore` 现在放行 raw 分类入口和对话模板，但继续忽略实际 raw source；`create-document.mjs` 现在按 scope 独立取号，拒绝治理目录、raw、日志、模板、来源页和生成产物。
- **仍为 WARN**：41 个 durable page 还是 legacy 文件名；老页面的 `when_to_read` / `keywords` 不批量伪造，按修改渐进补齐。
- **仍为 BLOCK**：母库和子库 `release_status` 都是 `BLOCK`，许可证为 `pending`；清洁目录独立复现、安装/运行、失败恢复、人工批准和正式课程第二场景仍未闭环。
- **下一步边界**：只推进一个编号迁移样本和一个去敏 synthetic raw → source → concept/playbook → course → exercise → verification → writeback 样本，不扩张平级课程或自动化系统。证据详情见 [structure-adversarial-review-20260728-discovery-v2.md](structure-adversarial-review-20260728-discovery-v2.md)。


## 2026-07-28 第五轮严格闸门结果

- **已通过**：`node scripts/validate-logs.mjs`（14 个事件、0 warnings）；`node scripts/validate-indexes.mjs --strict`；raw 五类目录扫描；verification/writeback 的事件引用与 dirty snapshot 指针。
- **结构语义已收紧**：`synthetic`、`source_kind`、`consent_status` 和真实验证状态不允许互相矛盾；普通知识链命令只表示结构通过，不表示课程效果已验证。
- **仍为 WARN**：`id-0004-structure-to-course-closure.md` 尚未提交练习、尚无明确人工 reviewer、`verification_status` 仍为 `partially_verified`。
- **仍为 BLOCK**：`node scripts/validate-knowledge-chain.mjs --release`；母库和子库 `release_status: BLOCK`、许可证 `pending`、工作树 dirty、跨环境运行和人工批准均未完成。机械层面的独立候选包安装、115 项 AllinCMS 本地测试、checksum 篡改阻断和上一份候选包恢复演练已通过，但不替代跨部署运行、客户 workspace 升级兼容性或正式发布审批。
- **规则同步**：`AGENTS.md`、`CLAUDE.md`、`README.md` 已补充日志、知识链和 strict index 命令；CI 的 tag release gate 已接入 strict index、log release 和 knowledge-chain release 检查。
- **本轮新增**：母库与子库各自携带 `scripts/validate-links.mjs`，源码和 latest-only 候选包均已通过本地链接/ scope 边界闸门；该 PASS 不替代外部 URL、人工阅读、许可证或跨环境运行验收。

## 2026-07-28 第六轮链接与 scope 边界闸门

- **已通过**：母库源码 `265` 个 Markdown / `969` 个本地链接；`website-content-ops` 子库 `81` 个 Markdown / `194` 个本地链接；两个 latest-only 候选包复制后均通过同一闸门。
- **已验证失败停止**：隔离副本故意注入 `missing.md` 时，`validate-links.mjs --release` 以非零退出并报告唯一断链，不会把结构 PASS 当成导航 PASS。
- **边界**：该闸门只验证本地 Markdown 路径和母库/子库 scope，不抓取外部 URL、不证明标题锚点、许可证、跨环境运行、真实课程效果或人工发布批准。
- **当前结论**：新增链接闸门已闭环，但母库与子库仍保持 `release_status: BLOCK`，许可证仍为 `pending`。 父级 `--release` 也会向链接子闸门传递严格模式，避免 warning 降级。

## 2026-07-28 第七轮 release fail-closed 与 artifact 扩展名闸门

- **已通过**：母库与 `website-content-ops` 普通候选包重建；母库 `299` 文件 / `298` checksum、子库 `102` 文件 / `101` checksum；两份普通 artifact 均 `ARTIFACT_PASS`。
- **已修复**：`build-*-release.mjs --release` 在源码、staging candidate、artifact 三层都使用严格模式；失败时不激活 `latest`，旧 latest digest 保持不变且不残留 staging。
- **已修复**：artifact 文件类型改为 fail-closed allowlist，仅允许 `.md`、`.json`、`.mjs`、`.yml`、`.yaml` 和显式 `.gitignore`；未知扩展名即使已登记并重算摘要/校验和也会 BLOCK。
- **已验证**：母库 artifact release 独立执行 strict index、links、logs、knowledge-chain 和 mother validator；子库 artifact 独立执行 links、workspace template sync 和 sub-library validator。未知 `probe.docx` 负向测试、dirty + `BLOCK` release 构建失败保留 latest、独立候选包安装/115 项测试、篡改检测和机械回滚均通过。
- **仍为 WARN**：41 个 legacy durable page 未渐进编号；外部 URL/标题锚点未抓取验证；未来二进制制品需逐文件授权；approval event/digest 绑定和母库/子库 tag namespace 已完成第一版机器闸；仍需真实人工 approval sidecar 和 clean release snapshot 才能放行。
- **仍为 BLOCK**：两套 manifest 的 `release_status: BLOCK`、`license_status: pending`、工作树 dirty；课程真人练习/reviewer/真实效果证据、真实 CMS 跨部署/失败恢复/客户 workspace 升级兼容、许可证和最终人工批准仍未闭合；approval sidecar 机制和 tag namespace 已落地但当前状态仍为 pending。详情见 [structure-adversarial-review-20260728-final.md](structure-adversarial-review-20260728-final.md) 的 Final Addendum 6。

## 2026-07-27 正文图片稳定化结论

- `article-image-binding.mjs` 成为 Markdown 正文图片唯一入口；禁止全局替换和手写 Slate 图片节点；
- 真实虚拟草稿验证 `A → B → A`：2 个唯一资产、3 个 occurrence，顺序、位置、URL、后台 Alt / Caption、编辑器重载、Caption 可见和图片解码均通过；
- Caption 必须使用 `[{"text":"..."}]`；字符串 Caption 虽可被后端持久化，但会导致当前编辑器 500；
- 草稿保存完成口径从“HTTP 200 + 后台回读”升级为“后台回读 + 编辑器非 500 + 图片解码 + Caption 可见”；
- 当前只确认 Alt 后台持久化；编辑器 DOM 3/3 缺失 `<img alt>`，本轮未发布，公开主题 Alt 不得宣称已验证；
- 保存请求可能发出后禁止自动重发；清单锁冲突默认停止，陈旧锁只允许经私有证据人工恢复。

## 2026-07-27 已解除的阻断

- 当前根目录确认为逻辑母库，`sub-libraries/` 作为子库；
- 虚拟品牌确认为 `FluxPedal Motors / 驱轮动力`；
- 虚拟演示行业确认为电动自行车电机出口；
- PicGo 图床范围确认为 R2、GitHub、腾讯云 COS、阿里云 OSS；
- 课程入口从十一课收束为工具、知识、小样、验证写回四阶段；
- 已建立公司、产品、ICP、虚拟聊天和第一条 SEO/GEO 内容闭环；
- 已将本仓库注册为 Obsidian Vault，并验证 Codex 修改 `START-HERE.md` 后 Obsidian 可直接看到更新；
- 第一条 CMS 图片参考实现已明确为 **AllinCMS 自身媒体库零点击接口上传**；Cloudflare R2 仅作为第一种外部图床备选与迁移练习；
- 已为 AllinCMS 建立“站点发现 + 媒体上传”的观察型内部接口规范，采用首次 UI 抓协议、后续接口回放、漂移时重新捕获；
- 已在真实登录会话中验证 `/sites`：站点列表随 `200 text/html` document 返回，并嵌入 `SitesClient.props.data` RSC 数据；未观察到单独的站点列表 JSON API 或 Server Action，DOM 作为只读回退。
- 已在用户确认的通用测试站点完成单图和一次五图真实上传：五张图片一次选择、一次提交、一个目标 Next Server Action，生成五条媒体记录；5/5 后台记录、媒体 ID、最终公开 URL、匿名 HTTPS、图片解码和刷新持久化均通过；未观察到独立预签名 PUT。
- 已用另一张虚拟图片完成单图零点击接口直传：不点击上传按钮、不触发文件选择器、不读取或导出 cookie / token；动态发现当前部署的 Server Action、deployment、site ID 与 router tree，同源请求返回 `200 text/x-component`，刷新后媒体记录持久化，媒体 ID、匿名 HTTPS、Content-Type 和图片解码均通过。
- 已完成 10 张虚拟 WebP 的单图接口严格串行调用验证：10/10 上传并全链验收，UI 点击 0、文件选择器 0；第九张首次客户端超时后先停并查库，确认未生成才受控继续，没有盲目重传。永久禁止媒体并发；一次 multipart 多文件不是默认路线，也不作为当前发布缺口。
- 已跑通一张图片的私有索引闭环：源 SHA-256 / MD5 → 零点击接口上传 → media ID / URL → 匿名下载远端 SHA-256 / MD5 → 原子事件与目标映射；本轮确认 AllinCMS 会重编码该 WebP，因此源哈希、上传输入哈希和远端哈希必须分开保存。
- 批量观察暴露并修正三类 adapter 缺陷：相邻 RSC 记录串行错配、受控 evaluate 环境缺少 `new Image()`、固定 500 ms 导航竞态。
- 已验证一条媒体记录的零点击接口删除：请求 1 次、UI 点击 0、确认框 0，刷新后精确媒体卡和精确 RSC 记录均消失。当前删除完成口径到此为止；不检查、不讨论、不阻断于 OSS、对象存储、公开 URL 或 CDN 是否物理删除。
- 已建立 `AI-START-HERE.md` + 机器可读合同作为其他 AI 的唯一执行入口，默认函数为 `uploadAllinCmsMediaSerial()`；禁止重新抓接口、手写单张循环、模拟点击、未精确确认缺失时盲目重试或自动改走外部图床；真实账号、站点 key、媒体 ID 和 URL 未写入公开库。
- 已实现运行预检、源 SHA-256 跨文件名复用、`prepared / request_started` 状态、预存标题冲突防误认领、规范化上传哈希保留、只读对账、原子索引、单写者锁、锁释放结果、断点恢复和 AI 元数据单次写入；29/29 本地故障测试通过。一张获批虚拟媒体已真实验证自定义 `title / alt / caption` 最终持久化；新恢复层和自定义标题仍需在后续自然、获批的真实上传中顺带复验，不能为了测试而重复写入。

## 当前剩余阻断

1. AllinCMS 单篇文章已完成 taxonomy 创建、全字段 JSON 多轮保存/发布、真实封面和前台闭环；Markdown 正文图片又完成 2 资产 / 3 occurrence 的 A/B/A 草稿原位绑定、后台回读、编辑器重载、Caption 可见和 3/3 解码。跨部署稳定性、表格节点、公开主题 Alt 与失败回滚仍无完整证据；
2. 串行媒体总控 29 项、文章图片绑定 50 项与文章生命周期 36 项测试合计 115 项通过；新媒体恢复层与自定义标题仍需在下一次自然、获批的真实上传中顺带复验；
3. 控制器已取消文件数上限并以 12 张本地测试证明仍严格串行；正文内容绑定的当前部署草稿已验证，但任意大批次真实远程长跑、跨部署绑定、覆盖和完整回滚仍未验证；媒体并发永久禁止，一次请求多图不属于默认路线；
4. PicGo + R2 / GitHub / COS / OSS 仅为外部图床备选；其账号、插件、配置和真实上传尚未获批，因此只阻塞外部图床迁移能力，不阻塞 AllinCMS 默认上传；
5. 第二图床或 CMS 迁移尚未完成；
6. 正式 Logo、真实联系和最终许可证只完成虚拟版本。

因此总评仍为 `BLOCK`（跨部署封面稳定性、复杂正文、任意大批次远程长跑、迁移与回滚仍未闭合），但 AllinCMS 图片严格串行上传、AI 元数据单次写入和媒体记录删除口径已固化，不再被并发、一次请求多图或物理资产清理阻断。

## Validated 完成闸

- 用户按四阶段完成一个虚拟纵向闭环；
- Obsidian、Codex 和 AllinCMS 默认图片路线均有真实验证证据，新增恢复层也完成获批的真实端到端复验；
- 作为备选能力，PicGo + R2 / GitHub / COS / OSS 至少一个外部图床参考实现和一个迁移实现通过；
- 同一知识迁移到一个相邻业务任务；
- 品牌、联系、许可、版本、打包和发布检查通过。

## 禁止扩张

在本模块达到 `Validated` 前，不新建平级课程或大型自动化系统。新需求优先作为当前闭环的 adapter、模板或迁移练习。

## 2026-07-27 AllinCMS taxonomy 与文章多轮接口验证

- 已在文章模块真实创建一个虚拟根分类和一个虚拟标签；创建请求均为当前页面的 Next Server Action，返回 `200 text/x-component`，刷新后名称、slug、描述和唯一内部 ID 均持久化。
- 已用新分类/标签创建一篇专用测试文章草稿，并以完整字段 `title`、`slug`、`excerpt`、`order`、`coverImage`、`categories`、`tags`、Slate `content`、`siteId`、`postId`、`mode` 完成 A/B/C/D 四轮：完整保存、重复保存、改正文后保存并发布、重复发布。
- 后台刷新通过：分类、标签、摘要、排序、正文和真实媒体库封面均未丢失；前台列表和详情各重复打开两次，标题、摘要、分类、正文、真实 WebP 封面均出现。
- 封面验收纠偏：不能只凭媒体对象名称猜 `path`，也不能把接口 200 当作图片通过；本轮发现一次实际 404 后，重新从媒体库取得完整对象并重新 `update` → `publish`，最终匿名下载和解码通过（WebP，1200×800，6242 bytes）。
- 主题边界：当前文章详情主题不把标签渲染成可见文本；标签以后台/RSC 绑定证据验收，不能用前台是否显示标签作为唯一判断。

当前焦点仍保持 `Blocked`，因为失败恢复、跨部署 Slate/封面、大批量和限流尚未闭合；文章删除/取消发布已在本轮闭合，但不代表跨部署回滚能力已完成。


## 2026-07-27 AllinCMS 前 4 项接口闭环检查

- 前 4 项已完成真实接口闭环：分类编辑、隐藏/恢复、排序、根/子分类 `parent`、删除；标签编辑、删除、重复 slug 前置校验；文章 `unpublish`、`publish` 恢复和删除。
- 每种动作均区分了 UI 抓包、接口实际回放、后台刷新重读和前台验收；不以 HTTP 200 单独判定成功。
- 文章使用全字段 payload：`title`、`slug`、`excerpt`、`order`、`coverImage`、`categories`、`tags`、Slate `content`、`siteId`、`postId`、`mode`；真实 WebP 封面经过后台绑定、匿名 HTTPS、MIME 和图片解码检查。
- 测试文章删除后后台行消失、前台详情返回 404；临时标签和临时子分类已清理。用于验证分类编辑/隐藏/排序的根测试分类按本轮记录保留，未与文章删除测试混用。
- 分类/标签创建曾出现 transaction state mismatch，后续固定“单次创建 → 等待响应 → 刷新 → 重读确认”，不得连续重发状态不明的创建请求。

当前焦点仍为 `Blocked`：跨部署合同、复杂 Slate、失败回滚和大批量远程长跑尚未闭合；但本轮前 4 项不再是阻塞项。


## 2026-07-27 AllinCMS 复杂 Slate 回归与清理复核

- 通过当前编辑器 UI 捕获并确认无序列表的真实节点合同：`ul` + `listStyleType: "disc"` + `li`；有序列表为 `ol` + `listStyleType: "decimal"` + `listStart: 1`。
- 复杂文章用全字段接口恢复后再次 `publish`，后台刷新显示“已发布”；前台正文的标题、marks、链接、引用、列表文本、真实 WebP 图片和封面均可见，图片资源匿名 HTTPS、`image/webp`、可解码。
- 主题边界已具体化：当前前台无序列表不是语义 `<ul>`，而是嵌套 `div`；正文图片 payload 中的 `alt` 未透传到前台 `<img>`。数据保存通过，但主题层无障碍/语义渲染不能宣称 PASS。
- 删除请求先通过精确目标行和确认文案核对，再只发送一次当前部署删除动作；后台列表目标行消失，原详情页返回 404。另一次误打开的非目标删除确认已取消，未删除既有文章。

因此当前焦点仍为 `Blocked`：当前部署单篇文章接口链已较完整，但跨部署合同、主题语义修复、失败恢复、回滚和大批量远程长跑仍未闭合。

## 2026-07-27 AllinCMS 文章 11 篇串行真实接口验证

- 当前部署连续创建 11 篇临时文章草稿，每篇使用完整字段 `title`、`slug`、`excerpt`、`order`、`coverImage`、`categories`、`tags`、Slate `content`、`siteId`、`postId`、`mode`；
- 逐篇执行 `mode=update → 后台刷新 → mode=publish → 后台刷新 → 前台详情验收`，11/11 发布状态、标题、正文和列表文本通过；
- 11 篇共 55 张图片均加载并解码，封面均为真实 1200×800 WebP；
- 中途一次批量 CDP 调用超时，没有重发，先回读后台确认 11 篇均已发布，再继续只读验收；
- 11 篇临时文章已全部清理，后台刷新后标题消失；误打开的一次非目标删除确认已取消，既有“勿发布”虚拟草稿未被修改。

这把文章批量证据从“超过 10 篇未验证”推进到“当前部署 11 篇串行已验证”。当前焦点仍为 `Blocked`：任意更大批次、503/transaction state mismatch 失败恢复、回滚、跨部署合同以及主题语义/Alt 修复仍未闭合。


## 2026-07-27 AllinCMS 对抗审查最终口径

### 权威层级

```text
701_kecheng 当前 AllinCMS Adapter + 当前部署证据
  > 共享 allincms-bulk-content-upload 编排/SOP
  > server-action-save-api.md 中性/历史模板
```

共享 skill 已明确不得覆盖当前 Adapter；已登录后台只是执行前提，不是接口合同证明，也不作为额外敏感阻断。真实凭据、Action、部署、站点和对象标识继续只留私有运行区。

### 当前 PASS

- 当前知识库 Adapter 本地控制器：`115/115`。
- 当前部署限定范围：已有 11 篇完整字段文章的串行 `update → publish`、后台/前台/图片验收证据。
- 分类/标签及文章生命周期的动作、状态和恢复代码已 fail-closed 加固；空回读不会自动重发已有文章。

### 当前 BLOCK

- `postCreate` 当前部署 create 合同未重新捕获、回放并用精确新 `postId` 验证。
- 文章级远程 503/transaction mismatch/请求可能成功恢复没有注入证据。
- 跨部署/跨站点和大于 11 篇远程长跑没有证据。
- 当前主题无序列表语义及正文图片 `alt` 透传仍为表现层缺口。

**最终审查结论：`BLOCK`。** 这不是因为敏感问题，而是因为远程合同、失败恢复、外推范围和主题表现证据尚未全部闭合；未闭合前不得写成整体 PASS。
