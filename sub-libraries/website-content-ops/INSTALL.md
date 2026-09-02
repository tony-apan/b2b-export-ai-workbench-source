---
title: "Website Content Operations Installation"
description: "复制、安装、升级和卸载 website-content-ops 独立发布包的最小说明。"
type: "installation-guide"
status: "Working"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-31"
sources: ["MANIFEST.md", "RELEASE.md"]
related: ["README.md", "START-HERE.md", "VERSION.md", "MANIFEST.md", "RUNTIME-CONTRACT.json", "scripts/build-release.mjs", "scripts/validate-sub-library.mjs"]
visibility: "public"
redaction_status: "safe-to-publish"
state_source: "MANIFEST.md"
state_projection: ["release_status", "preview_publication_status"]
release_status: "Preview"
preview_publication_status: "Ready"
---
# Installation

既有 `v0.3.2-preview.1` 已作为 **Public Preview** 发布，可继续按该版本范围下载试用；当前源码候选因新增研究来源的 publication clearance pending 而保持 `BLOCK`，不得重新发布。Stable qualification、跨部署稳定性和生产批量使用继续 `BLOCK`。

## Source-only 安装

完整 `website-content-ops` clean clone 是唯一 canonical 安装来源；`vendor/` bundle 已退役且不随仓分发。不要只复制 `SKILL-INSTALL/`，否则安装器会以 `CANONICAL_WEBSITE_CONTENT_OPS_ROOT_REQUIRED` 阻断。

```bash
git clone <repository-url>
cd <repository>/sub-libraries/website-content-ops/SKILL-INSTALL
python3 install.py codex
# 或指定任意 Skills 目录：python3 install.py --dir=/path/to/skills
```

Windows 在同一目录运行：

```bat
install.cmd codex
```

`install.py` 要求 Python 3.10+、Node.js >=20.9.0 与 npm，并自动执行 `npm ci`、接口 Registry/索引校验、由 `runtime-test-plan.json` 驱动的完整测试及 `acorn`/`ajv`/`sharp` 加载检查；全部通过后才创建 Skill 链接。`install.sh` 只是 POSIX 薄包装，不是唯一入口。PDF/DOCX 解析依赖按需增加 `--docs-parse`。

正式候选包由以下命令生成：

```bash
node scripts/build-release.mjs
```

候选包输出到 `dist/latest/`，包含 `MANIFEST.json` 和 `SHA256SUMS`。对复制后的候选包运行 `node scripts/validate-artifact.mjs /path/to/latest`；安装者应从 `README.md` 和 `START-HERE.md` 开始，不应读取母库私有路径。

AllinCMS adapter 的 Node 依赖与本地自测由 `SKILL-INSTALL/install.py`（Windows 为 `install.cmd`）统一安装和执行，不再要求使用者手工进入 adapter 运行 `npm ci`。其运行时依赖 Node.js、npm 和 `sharp`，不是母库或客户凭据。

## Runtime 依赖

真实客户任务必须先安装并验证 `agency-operations` runtime contract；本包不提供独立多客户控制面。详见 [RUNTIME-INTEGRATION.md](RUNTIME-INTEGRATION.md)。

## 升级与回滚

- 升级前保存当前目录和 `VERSION.md`；
- 只替换同一发布线的 tracked core；真实客户运行必须由 `agency-operations` 管理在 `customer-runtime/`，升级不得复制 `WORKSPACE-TEMPLATE/` 覆盖 Registry、ACTIVE-CONTEXT、CLIENT、TASK、HANDOFF、日志、证据或输出；
- 升级后先运行 `node scripts/validate-sub-library.mjs`；若校验发布包本身，再运行 `node scripts/validate-artifact.mjs /path/to/latest`。安装依赖后只运行结构 validator 和测试，不要把已生成的 `node_modules/` 当作原始 artifact 校验；
- 失败时恢复上一份已验收目录和 checksum，不能用“命令成功”代替内容验收。

## 卸载

删除子库目录即可；客户私有运行区、上传记录和凭据不属于本包，必须按客户自己的数据保留和删除政策处理。
