---
title: "Release Checklist"
description: "发布到 GitHub、公开网页、社媒或客户材料前使用的去敏、版权、事实、授权和下架检查清单。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-29"
sources: ["Risk review", "Release governance synchronization 2026-07-29"]
related: ["publishing-and-redaction.md", "sensitive-data-inventory.md", "check-mechanism-map.md", "release-state-machine.md", "release-approval-and-tag-namespaces.md", "../10_sources/license-and-consent-register.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# Release Checklist

本清单同时覆盖一般公开内容和仓库正式发布。先明确 scope；不适用项写 `N/A + reason`，不能留空后默认通过。

## Scope

- Release kind：content publication / mother library / sub-library
- Scope / package ID：
- Version / content digest：
- Source commit / candidate path：
- Target channel / exact remote or platform：
- Reviewer：
- `reviewer_identity`：verified / not_verified
- `independence_status`：verified / not_verified
- Approval decision / time：

## Hard Blocks

以下任一项成立即 `BLOCK`：

- [ ] scope、version、candidate、目标 remote/平台或负责人不明确。
- [ ] 包含真实 `raw/`、客户、账号、课程原文、经营资料或私有运行证据；或者 synthetic fixture 未同时命中 manifest/builder/metadata/content/digest allowlist。
- [ ] 包含姓名、邮箱、电话、微信、LinkedIn URL、合同、报价、CRM/广告后台、账户截图或未授权指标。
- [ ] 包含 API key、cookie、session、密码、验证码、恢复码、token、私钥或本地绝对路径。
- [ ] 包含未授权 PDF、截图、课件、录音、图片、Logo 或大段第三方原文。
- [ ] 计划用 AI 内置浏览器或脚本直接登录、发帖、评论、点赞、关注、加好友、私信或批量浏览社媒账号。
- [ ] 当前 scope 的 manifest 为 `BLOCK`、license/approval 未闭环，却准备对外宣称 Ready、Published 或稳定可用。
- [ ] 只有本地测试、HTTP 200、toast、作者自评、archive/checksum 或字段齐全，没有目标系统/发布平台回读。

## 内容、去敏与权利

- [ ] 已检查 [publishing-and-redaction.md](publishing-and-redaction.md) 和 [sensitive-data-inventory.md](sensitive-data-inventory.md)。
- [ ] 每个公开 source 已在 [license-and-consent-register.md](../10_sources/license-and-consent-register.md) 登记，许可范围覆盖本次使用。
- [ ] 客户名、联系方式、本地路径、具体金额/预算/转化率和截图已删除、范围化或获得明确授权。
- [ ] 课程和第三方材料已原创提炼，没有超范围复制。
- [ ] 虚拟示例显著标注为 synthetic/virtual，不会被误解为真实客户、案例、指标或效果承诺。
- [ ] 涉及社媒时已检查 [social-account-safety.md](social-account-safety.md)，最终账号动作由人确认和执行。

## 母库 / 子库候选

一般内容发布不适用时写 `N/A + reason`。

- [ ] 只选择一个母库或一个注册子库 scope；母库与子库 PASS 未串用。
- [ ] 已从目标 scope 的 manifest、release guide 和 [scripts/README.md](../../scripts/README.md) 读取当前命令，没有依赖根入口中的历史复制。
- [ ] source commit、candidate content digest、manifest digest、`SHA256SUMS` 和文件集合精确绑定。
- [ ] clean source、tag namespace、license、runtime applicability 和当前 release state 满足目标阶段；不满足时保持 BLOCK。
- [ ] `APPROVAL_RECORD_PASS` 只记录为 sidecar 结构/候选绑定 PASS，没有写成真人身份已验证。

## 外部 approval、tag 与 qualification

- [ ] 外部 workflow 读取并精确比对实际 annotated tag object SHA、target commit、signer fingerprint、canonical annotation bytes/digest 和 approval binding digest。
- [ ] signer fingerprint 来自 `git verify-tag --raw` 的真实结果并命中外部可信 allowlist；名称字符串没有被当作身份或授权证明。
- [ ] 目标远端的 Protected Environment、required reviewers、branch/tag ruleset、pinned workflow SHA 和服务端 run 有当前证据；workflow 文件中的字段名不算配置证明。
- [ ] approval/evidence、candidate、runtime test subject、archive、checksum 和 qualification attestation 均绑定同一 scope/commit/digest，候选字节在 qualification 前后不变。
- [ ] `qualified-not-published` 没有被写成 Published；缺任何外部证据时保持 BLOCK。

## 实际发布与验收

- [ ] 有权批准者针对精确 scope/version/digest、目标和时间作出明确决定；身份/授权证据状态已如实记录。
- [ ] 目标平台已产生并回读精确发布 URL/ID、版本、时间和对象摘要。
- [ ] 发布后前台/后台或下载制品与批准对象一致；必要时验证安装、升级、回滚或 CMS 前后台状态。
- [ ] 已记录下架/回滚条件、责任人和入口。
- [ ] 只对本次 scope 和时间窗口声明 Published，不外推到其他子库、部署、课程效果或未来稳定性。

## Publication Record

```md
## [YYYY-MM-DD] Publication

- release_kind:
- scope:
- package_id:
- version:
- source_commit:
- content_digest:
- target:
- publication_url_or_id:
- approved_by_claim:
- approval_identity_evidence:
- reviewer_identity: verified | not_verified
- independence_status: verified | not_verified
- tag_object_sha: N/A | <sha>
- signer_fingerprint: N/A | <fingerprint>
- canonical_annotation_digest: N/A | <sha256>
- approval_binding_digest: N/A | <sha256>
- redaction_and_license_status:
- published_at:
- takedown_or_rollback:
- residual_risks:
```

AI 生成或校验本记录不等于真人批准；AI 复审也不等于正式发布决定。
