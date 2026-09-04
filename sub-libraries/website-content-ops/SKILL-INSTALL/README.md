---
title: "AllinCMS Skill 安装壳（合并进母库）"
description: "allincms-bulk-content-upload 的安装壳与运维参考；2026-08-30 起独立仓封存，本目录为唯一真源。"
type: "doc"
status: "Working"
owner: "AI"
created: "2026-08-30"
last_updated: "2026-08-30"
canonical_entry: "README.md"
visibility: "public"
redaction_status: "safe-to-publish"
sources: ["self"]
related: ["../README.md"]
---

# allincms-bulk-content-upload
> **身份边界**：本目录为母库 **Working 源码（source-only）**，不构成可安装 Public Preview/Release 宣称；3 张来源卡 clearance 未闭合前（见 MANIFEST），安装路径仅供本机母库环境使用。


一个面向 AI 编程助手的 **AllinCMS / LAICMS 内容运营薄 Skill**：把用户提供的 PDF、DOCX、表格、网站、图片、brief 或现有 CMS 记录转换为可追溯事实、平台无关 desired state 和精确 `create / update / noop` 计划，再由当前 canonical Adapter 通过已登录会话执行已批准的 API / Server Action 操作并验收。

## 架构与唯一真源

```text
website-content-ops 完整 canonical source checkout
  > SKILL-INSTALL 的宿主路由与编排
  > references/ 和 scripts/ 中的历史辅助材料
```

**source-only 是唯一 canonical 安装路径。** `vendor/website-content-ops-runtime` bundle 已退役且不随仓分发；安装器只接受自身父目录就是完整 `website-content-ops` 源码树的布局。resolver 按 `--root` → `WEBSITE_CONTENT_OPS_ROOT` → 已安装 Skill 相邻完整源码（`SKILL_ROOT.parent`）→ 并列/向上发现的顺序解析；无效的显式高优先级路径必须 fail-closed，不能回落到历史 payload、旧 UI 流程或 retired helper。找不到完整源码时返回：

```text
CANONICAL_WEBSITE_CONTENT_OPS_ROOT_REQUIRED
```

不能回落到历史 payload、旧 UI 流程或 retired helper。完整源码与依赖自测 PASS 只证明本地运行时可执行，不证明 CMS 登录、当前部署接口、用户授权、远程写入、Stable 或 production-ready。

## 用户资料怎样参与新建或更新

Skill 不能直接把示例内容发进 CMS。标准链路是：

```text
用户资料 / 当前 CMS
→ 原始 bytes 或 snapshot digest
→ 私有 Source Extraction
→ owner / rights / clearance / freshness
→ extraction_id + unit_id + locator + digest
→ claim ledger
→ desired state
→ 当前 CMS capability + current-state fingerprint
→ 精确 diff
→ digest-bound authorization
→ 严格串行 mutation
→ 后台 / 编辑器 / 前台验收
```

以下值必须动态：客户与品牌事实、站点与语言、taxonomy、CTA、文章/产品字段、图片和关系、ID、当前字段枚举、Action ID、deployment/build ID、路由和请求参数。

以下不应被“通用化”为任意配置：Schema/fact-state 语义、Plan A / Plan B、精确身份与 fingerprint、授权摘要和最长 30 分钟有效期、严格串行、无盲目重试、publication effect、证据边界和冻结 qualification 口径。对象类型和 action vocabulary 通过 canonical 的版本升级扩展，不接受调用方随意注入未知对象绕过 Adapter capability。

### 更新现有内容

现有 CMS 记录也要先做只读 `cms_snapshot`，并进入同一证据链。用户没要求修改的字段保持原值；清空必须显式；用户资料与当前 CMS 冲突时先记为 `conflicting`，不能用模板默认值静默覆盖。更新必须绑定 exact ID，或站点内唯一 natural key，并带 `expected_current_fingerprint`。

### 新建网站

必须两阶段：

1. **Plan A / `site_bootstrap`**：账号 scope，仅创建一个站点资源；未来 `site_id/site_key` 为 `null`；回读真实站点身份。
2. **Plan B / `site_operation`**：引用 Plan A digest 与私有回读证据，绑定真实站点，重新发现 capability/current state，再创建 taxonomy、媒体、文章、产品或主题页。

当前 Registry 将 `site.create` 与 product create/update/publish 纳入 canonical `fresh_live_verified_current_deployment` gate；`product.discover` 仍为 exploration，`product.delete` 仍为 blocked。以运行时 `MANIFEST.md`、Interface Registry 和当前部署 capability 为准。

## 安装与依赖

### 一次安装

从完整 `website-content-ops` clean clone 运行安装器。Python 3.9+、Node.js >=20.9.0 和 npm 为必需前置；安装器自动执行 `npm ci`、接口 Registry/索引校验、由 `runtime-test-plan.json` 驱动的测试套件及 `acorn`/`ajv`/`sharp` 加载检查，全部通过后才创建 Skill 链接。

```bash
cd sub-libraries/website-content-ops/SKILL-INSTALL
python3 install.py codex
python3 install.py --dir="$HOME/.agents/skills"
```

Windows：

```bat
cd sub-libraries\website-content-ops\SKILL-INSTALL
install.cmd codex
```

`install.sh` 仅是 POSIX 薄包装，行为与 `python3 install.py` 相同。PDF/DOCX 解析依赖默认不安装，需要时增加 `--docs-parse`；仅验证链接逻辑可用 `--skip-self-test`，该模式不会安装 Node 依赖、运行自测或写 ready marker，因此不能据此宣称 controller 可执行。

检查完整源码解析与依赖状态：

```bash
python3 scripts/resolve_website_content_ops_root.py --start "$PWD" --json
```

正常完成安装后结果包含：

```json
{
  "source": "upward-discovery",
  "sourceCheckoutValidated": true,
  "runtimeBundleValidated": false,
  "runtimeDependenciesInstalled": true,
  "controllerExecutable": true
}
```

只 clone/copy 而未运行正常安装时，resolver 会返回 `runtimeDependenciesInstalled: false` 和 `controllerExecutable: false`。vendor bundle 已退役且不随仓分发；无完整 source checkout 时必须返回 `CANONICAL_WEBSITE_CONTENT_OPS_ROOT_REQUIRED`，不能回落 UI 或历史 helper。

## 使用

在支持 Skills 的 AI 中明确调用：

```text
使用 $allincms-bulk-content-upload，先解析 canonical Website Content Operations 包，结合我提供的资料和当前 CMS 只读快照生成可追溯 Source Extraction 与精确 create/update/noop 计划；没有登录就打开登录页引导我登录；在能力、身份、摘要授权或验收不满足时停止，不要回落历史接口。
```

宿主需要具备与输入相符的真实能力，例如 PDF、DOCX、表格、图像、浏览器或 HTTP/API。Skill 只路由这些能力，不复制解析器。先通过 canonical API preflight 判定：只有 `login_required` 才在内置浏览器打开登录页；`authenticated` 不导航，`http_error`、`contract_drift`、`pagination_incomplete` 分别 BLOCK。登录完成后必须丢弃旧结果，通过 API 重新读取 `user.id`、完整网站列表、精确目标站点和当前部署能力。

## 非官方第三方客户端声明（UNOFFICIAL）

- 本目录是与 AllinCMS / LAICMS **无授权关系、无背书**的第三方操作层；所有能力描述来自对公开前端行为的逆向观察。
- 逆向观察所得的 server action ID 绑定具体部署、**可随平台任意更新失效**，且部分自动化行为可能被视为违反供应商当时有效的服务条款。
- 使用者自担风险：账号限制、数据丢失、服务中断等后果不由本目录作者承担（见 LICENSE 的 NO WARRANTY 条款）。
- 凭证只由使用者自己提供（推荐 `WS_TOKEN` 环境变量），**绝不入仓、不入日志、不入示例**。
- 在任何批量/自动化操作前，使用者有责任确认供应商现行条款允许该操作。

## 网络出口声明

本能力只与以下域名通信：`workspace.laicms.com`（工作台/Server Actions，携带登录态）与 `<site-key>.web.allincms.com`（公开站只读验证）。`*.preview.laicms.com` 为平台预览域预留（当前工具代码未调用）。不与其他第三方端点通信。

## 破坏性操作门禁（白名单）

以下操作**永远要求用户单条显式批准**（逐条列出目标 + 数量，禁止打包授权）：删除站点、删除产品/文章/分类/标签/媒体、主题 unpublish/delete、`delete-demo-content.py` 全链路清理、任何 `--force`/`--confirm` 类参数触发的批量写。canonical 侧的 mutation 授权（authorizationContext，30 分钟 TTL）叠加在此规则之上，不替代它。

## 执行与授权

- 默认只读；用户可以对一个不可变、有序、精确 target 的完整计划授权一次。
- `authorizationContext` 必须绑定 plan digest、target scope/key、operation IDs、actor 声明与不超过 30 分钟的有效期。
- controller 在**每个请求前**机器重验同一上下文；这不是每个接口都重新打断用户。
- 资料字节、站点、字段、图片、顺序、publication effect、capability 或 current fingerprint 漂移，旧授权立即失效。
- mutation 严格串行；请求可能已发送但结果不明时，只读对账，禁止盲目重发。
- UI 只用于登录、动态合同探索、明确批准的回退或验收；不能把 UI 当自动降级通道。

## 证据边界

本地 Schema、validator、测试通过只证明本地合同。真实 mutation 还需要当前登录态、精确 target、未过期 `live_verified_current_deployment` capability、接口执行、后台回读、编辑器重开和前台验收。

不得把以下结果混为一谈：

- local structure PASS；
- Adapter local tests PASS；
- 真实 CMS 写入；
- 发布成功；
- Stable / Published；
- SEO、排名、询盘或转化效果。

客户资料、operation plan、凭据以外的 session 证据、请求结果和截图只能进入绑定的 `customer-runtime/`，不能写入本公开 Skill 或 canonical 公共源树。

## Upgrade & drift policy（升级与漂移策略）

- 本目录是 source-only 唯一安装来源；升级必须更新完整 canonical source checkout 后重新运行 `install.py` / `install.cmd`，不得复制旧目录覆盖。
- `vendor/` bundle 已退役且不随仓分发；resolver 只默认发现完整 source checkout。


## 合并说明（2026-08-30）

- 独立仓 `tony-apan/allincms-bulk-content-upload` 已**封存**（GitHub archived，保留历史）；本目录（母库 `sub-libraries/website-content-ops/SKILL-INSTALL/`）为唯一真源。
- **vendor bundle 已退役且不随仓分发**：resolver 的 full-source 路径（母库 `sub-libraries/website-content-ops/` 本体）是唯一 canonical 安装来源。
- 合并前已清：母库实名×2（00da9e0）、客户名大小写变形×3（3b6c573 两处 + 31191ea 全大写一处）；历史字节仍存于封存仓与 git 历史。
- 安装：运行本目录 `python3 install.py`；Windows 运行 `install.cmd`。`install.sh` 仅转发给 Python 安装器。
