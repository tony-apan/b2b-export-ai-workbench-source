---
title: "Website Content Operations Installation"
description: "复制、安装、升级和卸载 website-content-ops 独立发布包的最小说明。"
type: "installation-guide"
status: "Draft"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-28"
sources: ["MANIFEST.md", "RELEASE.md"]
related: ["README.md", "START-HERE.md", "VERSION.md", "MANIFEST.md", "RUNTIME-CONTRACT.json", "scripts/build-release.mjs", "scripts/validate-sub-library.mjs"]
visibility: "public"
redaction_status: "safe-to-publish"
release_status: "BLOCK"
---
# Installation

当前子库仍为 `BLOCK` 源码候选，以下步骤用于复制和验收，不代表已经批准对外安装。

## 复制源码或 latest 包

```bash
cp -R website-content-ops /path/to/target/website-content-ops
cd /path/to/target/website-content-ops
node scripts/validate-sub-library.mjs
```

正式候选包由以下命令生成：

```bash
node scripts/build-release.mjs
```

候选包输出到 `dist/latest/`，包含 `MANIFEST.json` 和 `SHA256SUMS`。对复制后的候选包运行 `node scripts/validate-artifact.mjs /path/to/latest`；安装者应从 `README.md` 和 `START-HERE.md` 开始，不应读取母库私有路径。

AllinCMS 图片 adapter 的工具测试位于 `ADAPTERS/cms/allincms/`；在该目录执行 `npm ci --ignore-scripts --no-audit --no-fund` 和 `npm test`。其运行时依赖 Node.js、npm 和 `sharp`，不是母库或客户凭据。

## 升级与回滚

- 升级前保存当前目录和 `VERSION.md`；
- 只替换同一发布线的 `latest` 包，不把客户 `workspace/` 数据覆盖进去；
- 升级后先运行 `node scripts/validate-sub-library.mjs`；若校验发布包本身，再运行 `node scripts/validate-artifact.mjs /path/to/latest`。安装依赖后只运行结构 validator 和测试，不要把已生成的 `node_modules/` 当作原始 artifact 校验；
- 失败时恢复上一份已验收目录和 checksum，不能用“命令成功”代替内容验收。

## 卸载

删除子库目录即可；客户私有运行区、上传记录和凭据不属于本包，必须按客户自己的数据保留和删除政策处理。
