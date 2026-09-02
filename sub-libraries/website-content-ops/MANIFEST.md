---
title: "Website Content Operations Manifest"
description: "建站内容运营子库源码包的包含、排除、占位符、适配器、阻断和发布状态。"
type: "manifest"
status: "Working"
owner: "AI"
created: "2026-07-26"
last_updated: "2026-09-03"
sources: ["Package contract compiled 2026-07-26", "Tony decisions 2026-07-27", "Tony structure upgrade decision 2026-07-28"]
related: ["README.md", "COURSE-MAP.md", "WORKSPACE-TEMPLATE/README.md", "MENTAL-MODEL.md", "ADAPTERS/cms/allincms-overview.md", "ADAPTERS/cms/allincms/README.md", "QA-CHECKLIST.md", "VERSION.md", "CHANGELOG.md", "RELEASE.md", "INSTALL.md", "REFERENCES/README.md", "scripts/README.md", "SCHEMAS/runtime-contract.schema.json", "BRAND.md", "CONTACT.md"]
visibility: "public"
redaction_status: "safe-to-publish"
repository_status: "public-preview"
preview_publication_status: "Published"
preview_version: "0.3.2-preview.1"
preview_tag: "v0.3.2-preview.1"
historical_published_version: "0.3.2-preview.1"
historical_published_tag: "v0.3.2-preview.1"
current_candidate_identity: "website-content-ops-0.4.0-preview.1"
current_candidate_snapshot: "clean-committed-tree"
current_candidate_version: "0.4.0-preview.1"
current_candidate_date: "2026-09-03"
release_status: "Preview"
maturity_status: "validated"
verification_status: "evidence-partial"
release_scope: "standalone-sub-library"
package_id: "website-content-ops"
package_kind: "standalone-sub-library"
delivery_modes: ["human-playbook", "ai-skill-draft", "toolkit"]
skill_entrypoint: "SKILL.md"
skill_status: "preview-adapter-not-installable"
package_scope: "."
runtime_contract: "RUNTIME-CONTRACT.json"
dependency_mode: "declared-external-runtime"
durable_roots: ["KNOWLEDGE", "PLAYBOOKS", "COURSES", "OUTPUTS"]
external_dependencies: ["Node.js >=20.9.0", "npm", "sharp 0.35.3 (AllinCMS adapter only)"]
source_package_only: true
license_status: "cleared"
license_record: "see body table License Records (tools/interface-kit Apache-2.0 UNOFFICIAL, recorded 2026-08-30); three source cards cleared 2026-09-03 (see REFERENCES/SOURCE-INVENTORY.json)"

approval_required: true
approval_status: "pending"
approval_record: "RELEASE-APPROVAL.json (external sidecar)"
tag_namespace: "sub-library/website-content-ops"
tag_prefix: "sub-library/website-content-ops/v"
included_in_mother: "source-only"
  # SKILL-INSTALL/：allincms-bulk-content-upload 合并目录（2026-08-30），MIT，working-source、不做可安装宣称；vendor 快照退役待 dist 管线（id-0073）
include: ["AGENTS.md", "LICENSE", "NOTICE", "THIRD-PARTY-NOTICES.md", "BRAND.md", "CHANGELOG.md", "CONTACT.md", "COURSE-MAP.md", "INSTALL.md", "INTAKE.md", "LICENSE.md", "MANIFEST.md", "MENTAL-MODEL.md", "PLAYBOOK.md", "QA-CHECKLIST.md", "README.md", "RELEASE.md", "RUNTIME-INTEGRATION.md", "SKILL.md", "SOURCES.md", "START-HERE.md", "TOOLS-INDEX.md", "VERSION.md", "WRITEBACK.md", ".gitignore", "RUNTIME-CONTRACT.json", "SCHEMAS/**", "REFERENCES/**", "PLAYBOOKS/**", "TEMPLATES/**", "EXAMPLES/**", "ADAPTERS/**", "WORKSPACE-TEMPLATE/**", "SKILL-INSTALL/**", "TOOLS/**", "scripts/**", "content-safety.allowlist.tsv"]
exclude: ["**/client-ids.local.txt", ".git/**", ".obsidian/**", "node_modules/**", "dist/**", "workspace/**", "customer-runtime/**", "credentials/**", "secrets/**", "browser-profiles/**", ".env*", "**/.env*", "*.secret", "**/*.secret", "*.credentials", "**/*.credentials", "*.sqlite*", "**/*.sqlite*", "*.db", "**/*.db", "*.p12", "**/*.p12", "*.pfx", "**/*.pfx", "*.crt", "**/*.crt", "*.token", "**/*.token", "*.cookie", "**/*.cookie", "*.key", "**/*.key", "*.pem", "**/*.pem", "*.png", "**/*.png", "*.jpg", "**/*.jpg", "*.jpeg", "**/*.jpeg", "*.webp", "**/*.webp", "*.gif", "**/*.gif", "*.mp4", "**/*.mp4", "*.mov", "**/*.mov", "*.mp3", "**/*.mp3", "*.wav", "**/*.wav", "TOOLS/**/*.py", "scripts/*.py", "scripts/**/*.py"]
---
# Package Manifest

## 当前交付判断

`v0.3.2-preview.1` 仍为 immutable historical published artifact（tag 与身份不重用）。2026-09-03 起：三张 bundled source card（AllinCMS official、PicGo image-hosts official、B2B SEO content research）已按 RELEASE.md 推荐流程第 2 步完成逐卡 publication review，三字段均为 `approved / PASS / cleared`（依据见各卡 Publication clearance 节；授权 actor Tony，human-asserted，reviewer identity `not_verified`）。因此 `release_status` 进入 `Preview`、`license_status: cleared`；发布事实：候选 `0.4.0-preview.1` 已随公开仓 main `4ccab49` 发布（2026-09-03），`preview_publication_status` 回写为 `Published`；当前候选分配 `current_candidate_version: 0.4.0-preview.1`（identity `website-content-ops-0.4.0-preview.1`，snapshot `clean-committed-tree`），与历史 version/tag 无碰撞。

`Preview` 口径边界不变：README 明确非 Stable、先单样本、生产动作需批准；`approval_status` 保持 `pending`、`release validator` 对 `Ready/Published`（Stable 口径）的正式 qualification（signed tag、approval sidecar、外部 workflow 注入）仍未执行，Stable 与 `Published` 继续阻断。若任一来源卡复审回到 `pending/BLOCK`，本状态必须回退 `BLOCK`。

## 学习层

- Why：[README.md](README.md) 与 [COURSE-MAP.md](COURSE-MAP.md)；
- Model：[MENTAL-MODEL.md](MENTAL-MODEL.md) 与 `TEMPLATES/`；
- Reference implementation：[PLAYBOOK.md](PLAYBOOK.md)、[TOOLS-INDEX.md](TOOLS-INDEX.md) 与 `ADAPTERS/`；
- Transfer exercise：[TEMPLATES/transfer-exercise-record.md](TEMPLATES/transfer-exercise-record.md) 与 [QA-CHECKLIST.md](QA-CHECKLIST.md)。

## 源码包包含

- 用户入口、逐课路线和 AI 协议；
- 可复制但未填数据的 `WORKSPACE-TEMPLATE/`；
- 公司、产品、客户语言、文章、图片、发布、来源、字段映射、失败和迁移模板；
- 工具中立 playbook 与 adapter 强制模板；
- 虚拟示例入口、QA、写回、品牌、联系、版本、变更记录、发布说明和静态检查入口。

## 源码包排除

- 已填入真实数据的 `customer-runtime/**`；本包只声明对 `agency-operations` 运行合同的外部依赖，不携带客户数据；
- 真实公司、产品、客户、聊天和经营数据；
- 凭据、PicGo 完整配置、cookie 和 session；
- Tony 私有母库路径和内部资料；
- 未授权课程原文和第三方素材；
- 把单个平台按钮步骤冒充为通用方法的教程。

## 占位符政策

- 虚拟品牌、`.example` 域名和演示邮箱已经注入，不是遗漏占位符；
- 真实品牌化发布前必须替换并人工验证；
- [ADAPTERS/_template.md](ADAPTERS/_template.md) 中的 `tool-name` 是模板变量，新建具体 adapter 时必须替换；
- 对外 release artifact 不允许出现未登记双花括号占位符、凭据或本地绝对路径。

## 检查与发布入口

- 结构与发布前静态检查：`node scripts/validate-sub-library.mjs`；
- latest-only 候选包：`node scripts/build-release.mjs`；
- 复制、升级和回滚：[INSTALL.md](INSTALL.md)；
- 独立来源副本：[REFERENCES/README.md](REFERENCES/README.md)；
- 当前发布边界和 latest-only 流程：[RELEASE.md](RELEASE.md)；
- 本版本变更：[CHANGELOG.md](CHANGELOG.md)。

## durable page 与编号范围

本子库不是把所有 Markdown 都编号。根入口、合同、adapter、模板、来源、验证记录和写回记录保留语义路径；需要跨任务复用的长期知识页放入 `KNOWLEDGE/`、`PLAYBOOKS/`、`COURSES/` 或 `OUTPUTS/`，使用 `id-####-slug.md`，并填写匹配的 `doc_id`、`description`、`when_to_read` 和 3-8 个 `keywords`。这些目录是未来扩展点，当前版本不因空目录制造占位噪声。

## 当前适配器

- 图片路由：目标为 AllinCMS 媒体库时优先零点击接口串行上传；[R2 / GitHub / 腾讯云 COS / 阿里云 OSS](ADAPTERS/image-hosts/README.md) 仅为外部图床备选；
- Virtual business：[FluxPedal Motors](EXAMPLES/fluxpedal-motors/README.md) 公司、产品、ICP、聊天和首条闭环已建立；
- CMS：首个参考实现为 AllinCMS；真实环境已验证站点发现、单图零点击直传、10 张严格串行直传、一次五图 UI 回退、匿名 URL 验证、零点击媒体记录删除，以及一张获批虚拟媒体的 `title / alt / caption` 最终持久化；本地实现已补只读对账、原子图片索引、断点恢复、源 / 上传 / 远端哈希、单写者锁、AI 元数据单次写入和停批规则，并通过 47 项媒体测试；文章 taxonomy 创建、全字段多轮 update / publish、真实封面与前台列表/详情也已有单样本证据；Markdown 正文图片 A/B/A 草稿绑定、后台回读、编辑器重载和 Caption 可见已有真实限定证据；本地控制器已升级为 manifest schema 2、逐 occurrence 双重复核、`bindingProof`、文章 operation lock 和整篇单次保存；当前 trusted runtime profile 固定四文件并通过 160/160（媒体 47、正文图片 52、正文格式 13、文章生命周期与 taxonomy 48）；历史 158/158 已陈旧，不具备当前 qualification 资格；
- 第二图床 / CMS：计划从四种图床中选择另一个完成迁移；
- Analytics / Search data：在真实站点阶段接入 Search Console、询盘和销售反馈。

## 既有 Preview 限制与当前发布阻断

1. AllinCMS 图片默认路线已固化并通过 47 项媒体测试；正文图片唯一 adapter 已通过 52 项文章图片测试；当前四文件 trusted profile 为 160/160，其中正文格式 13、文章生命周期与 taxonomy 48；历史 158/158 已陈旧并必须拒绝；新恢复层、自定义标题和跨部署元数据读后写稳定性仍需在下一次自然、获批的真实上传中顺带复验；
2. AllinCMS 文章单样本已完成 taxonomy、多轮保存/发布和前台渲染；A/B/A 正文图片草稿已验证，逐 occurrence 原位替换能力不再暂停。公开主题 Alt、表格等更多复杂节点、跨部署封面/正文稳定性、覆盖和完整回滚仍无完整证据；
3. 控制器不设图片数量上限，本地已验证 12 张仍严格串行；真实远程证据目前到 10 张。媒体并发永久禁止，一次请求多图不是默认路线；
4. PicGo + R2 / GitHub / COS / OSS 不再是 AllinCMS 上传前置，只作为外部图床和迁移能力；其真实单图参考实现尚未完成；
5. 第二工具与相邻业务任务迁移无验证证据；
6. Apache-2.0 许可证文本与公开联系入口已存在，但 AllinCMS official、PicGo image-host official 与 B2B SEO content research 三张 bundled source card 的 publication/license clearance 均未闭合；其中 B2B research reference 只获准用于内部方法研究。正式 Logo、Stable 人工批准、可信签名和 GitHub 服务端 qualification 也未闭合。机器可读 manifest、既有结构测试、latest-only 打包脚本和 checksum 校验不替代这些证据。

## 当前发布结论

**当前源码候选：Public Preview publication / release `BLOCK`；Stable：`BLOCK`。** 既有 `v0.3.2-preview.1` 独立公开仓事实不被撤销，但 AllinCMS official、PicGo image-host official 与 B2B SEO content research 三张 bundled source card 的 publication/license clearance 完成前，当前源码候选只能用于内部方法研究和 Working artifact，不得宣称新的 Preview publication、Stable、Published、production-ready、课程效果或跨部署迁移能力。既有结构测试仍只证明其原有结构 scope。

## License Records

| artifact | license | notice | recorded | reviewer | caveat |
|---|---|---|---|---|---|
| TOOLS/interface-kit | Apache-2.0 | UNOFFICIAL THIRD-PARTY CLIENT for AllinCMS/LAICMS; action ids from public bundles, may change without notice | 2026-08-30 | TERRA 69cf48a1 + flash 07ba67df | 3 bundled source cards (AllinCMS official, PicGo image-host, B2B SEO research) clearance still open; status stays pending/BLOCK until closed |
| SKILL-INSTALL/ | MIT（安装壳）/ 继承母库 source-only | 2026-08-30 合并；working-source 不做可安装宣称；vendor 退役待 dist 管线 | 2026-08-31 | TERRA 6afde8fc + flash b7baf83c | 3 张来源卡 clearance 未闭合前维持 pending/BLOCK |
