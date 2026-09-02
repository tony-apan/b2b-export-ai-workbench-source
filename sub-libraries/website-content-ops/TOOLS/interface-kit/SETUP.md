---
title: "安装与依赖指南（SETUP.md）—— 新电脑/新环境必读"
type: "doc"
status: "Working"
owner: "AI"
last_updated: "2026-09-01"
description: AllinCMS 建站工具包文档（SETUP.md）
created: 2026-08-31
visibility: "public"
redaction_status: "safe-to-publish"
sources: ["self"]
related: ["README.md"]
---

# 安装与依赖指南（SETUP.md）—— 新电脑/新环境必读

> 目标：**5 分钟到可用**。步骤 1-4 必做（约 3 分钟）；文档解析依赖按需；canonical 校验按需。

## 依赖全景（先看这张表）

| 层 | 依赖 | 用途 | 缺了会怎样 |
|---|---|---|---|
| runtime | **Python 3.8+（stdlib）** | 全部工具（建站/索引/监控/图片门） | 无法运行任何脚本 |
| docs-parse | pypdf / python-docx / python-pptx / openpyxl（或系统 poppler） | 解析用户 PDF/Word/PPT/Excel → Markdown | 资料解析跳级/降级（txt/md/html 仍可用） |
| canonical | Node.js ≥18 | 子库校验（validate-links/validate-sub-library） | 无法运行 canonical 校验（可选） |
| visual | Chrome（headless） | 截图复核（ID-0007 B2） | 无截图（可用 curl 替代验证） |

**注意：建站核心零第三方依赖**——所有功能（写/读/模块/索引/监控/图片门）只要 Python 3 即可。

## 安装步骤

```bash
# ① 复制工具包到新机器（整个 interface-kit/ 目录自包含）
# ② 检查 Python
python3 --version        # ≥3.8 即可（mac/win/linux 通用）
# ③ 安装依赖（一键：检测+安装+复检）
python3 install-deps.py --yes
python3 install-deps.py --verify      # 复检输出 PASS 即环境就绪
# ④ 工具自检
python3 index/registry_tools.py verify        # 索引完整性（路径/枚举/id 唯一）
python3 site_pipeline.py diff a.json b.json   # 深度比对工具冒烟（任意两个 json）
# ⑤ 平台冒烟（需 token）
python3 allincms_api.py <token> read-sites    # 预期：站点列表 JSON
```

## 各平台补充

| 平台 | 说明 |
|---|---|
| macOS | 系统自带 Python3（若缺失 pip 用 `python3 -m ensurepip`）；Chrome 已装有 headless；Node 用 `brew install node` |
| Windows | Python 3 官网安装（勾选 Add to PATH）；所有命令用 `python` 或 `python3` 均可；路径用反斜杠无碍（脚本内部 os.path 自适应） |
| Linux | `apt install -y python3 python3-pip`；poppler：`apt install -y poppler-utils` |

## 常见问题

- **pip 安装权限**：用 `--user`（install-deps.py 已带）；公司镜像慢可加 `-i https://pypi.tuna.tsinghua.edu.cn/simple`
- **macOS 系统 Python 受限**：装 `python3-docx` 失败时先 `python3 -m ensurepip` 再重试
- **Node 不想装**：跳过 ④ 的 canonical 校验即可；界面校验不影响建站工具
- **token 从哪来**（三种取法，推荐①，真源 [TOKEN-AUTH.md](../../ADAPTERS/cms/allincms/docs/TOKEN-AUTH.md)）：① `AllinCMS(email, password)` 纯 API 登录自动提取；② 工作台登录 → DevTools → Application → Cookies → `payload-token`（兜底）；③ 浏览器配置文件提取（未实测）。取到后**推荐 `export WS_TOKEN=<token>` 环境变量**；或 token 文件 chmod 600 后传路径，**不要提交到 git/公开目录**。
- **audit/gate/contact 三门依赖公网可达**：`site_pipeline.py audit/gate/contact` 会 `urllib` 抓取 `https://<site-key>.web.allincms.com` 做 200/空态/模板词/SSR 检查。**受限/离线/无公网环境会卡或超时**——此时别等它，改用：浏览器直接访问 `.web.allincms.com` 各路径实测 200 + 截图，配合 `read_product`/`read_lists`/`read_page_document` 后台回读对抗验收，并在审计报告注明"公网抓取受限，已用浏览器+readback 替代"（BOUNDARY 记录）。
- **新电脑建站前先 `find` 关键坑（迭代自证）**：`python3 index/registry_tools.py find 产品` 会列出 ISS-105（media 用 url 非 oss / specs≤200 / 无 create action 走 update）；`find globals` 列 ISS-106（globals 读原值改单字段 / CTA 弹窗 anchorId / 站点级 publish 刷 CDN）。先读再动手，避免重踩。

## 安装后顺序（每次干活前）

```text
① 复制工具包（若新环境）
② install-deps.py --yes --verify        # 依赖门
③ registry_tools.py verify              # 索引门
④ index/registry_tools.py find <关键词>  # 查坑/查文档（索引优先）
⑤ 按 ONBOARDING-PIPELINE.md 执行
```
