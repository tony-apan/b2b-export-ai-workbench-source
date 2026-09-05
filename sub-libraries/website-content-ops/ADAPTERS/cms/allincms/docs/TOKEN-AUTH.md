---
title: "AllinCMS 认证与 Token 获取指南"
description: "三种获取 payload-token 的方式：纯 API 登录 / 浏览器 Cookie / 脚本半自动。适用于任何自动化客户端。"
type: "tooling"
status: "Working"
owner: "AI"
created: "2026-08-30"
last_updated: "2026-09-06"
sources: ["示例客户 全流程实战 2026-08-29/30（纯 API 登录成功+失败双路径实测）", "ISS-083"]
related: ["../../../../TOOLS/interface-kit/RUNBOOK-ANYONE.md", "../../../../TOOLS/interface-kit/NEW-SITE-ONEPASS.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---

# AllinCMS 认证与 Token 获取

所有读写接口都需要 `payload-token`（JWT）。本文档梳理三种获取方式——按推荐顺序排列。

---

## 方式一：纯 API 登录（推荐，零浏览器）

```python
from allincms_api import AllinCMS

api = AllinCMS(email="user@example.com", password="<your-password>")
print(api.token)  # 357 字符 JWT——登录成功即自动提取
```

**原理**：客户端 POST sign-in server action → 服务端返回 `Set-Cookie: payload-token=<JWT>` → 客户端从响应头提取。全程 HTTP 请求，不开浏览器。

**实测记录**（2026-08-30，双路径）：
- ✅ 正确凭据 → 提取 JWT → 读（read_sites 返回站点列表）+ 写（set_home_page）权限完整
- ✅ 错误凭据 → 干净报错 `"The email or password provided is incorrect."`（不崩溃、不静默）

**凭据传递**（密码不落盘的两种给法）：

| 方法 | 操作 | 适用 |
|---|---|---|
| A. 直接提供 | 用户在对话/工单里给 AI 邮箱+密码 | 信任环境、快速验证 |
| B. 文件传递 | 用户自己执行 `printf 'email\npassword' > <tmp>/ws-creds.txt`，AI 读取后删除 | 密码不想出现在对话记录里 |

**AI 拿到凭据后的标准动作**：

```python
api = AllinCMS(email=..., password=...)
# 推荐：export WS_TOKEN=<token>（跨平台）；或写 token 文件（chmod 600）后传路径，后续工具复用
import os; os.remove("<tmp>/ws-creds.txt")          # 如果用了方式 B，用完即删
```

**注意事项**：
- 密码只在内存中用于发一次登录请求，不写入任何持久化文件
- 推荐 `export WS_TOKEN=<token>` 环境变量（跨平台）；或写 token 文件（chmod 600）
- `/tmp` 重启后清空——每台新机器/重启后需重新获取

---

## 方式二：用户浏览器手动获取 Cookie（兜底，已验证）

用户在浏览器登录后手动复制 Cookie 给 AI。

**步骤**：
1. 打开 `https://workspace.laicms.com` 并登录
2. DevTools（F12 / Cmd+Option+I）→ Application（应用）→ Cookies → `https://workspace.laicms.com`
3. 找到 `payload-token` 行，复制 Value 列（一长串 `eyJ...` 开头的 JWT）
4. 交给 AI（贴对话或 `export WS_TOKEN=<token>`；写文件必须 chmod 600）

**适用场景**：
- API 登录路径出问题（如平台改了登录接口）
- 用户已在浏览器登录、不想再输一次密码
- 调试时快速验证 token 是否有效

---

## 方式三：用户浏览器登录后 AI 从浏览器配置文件提取（半自动）

用户在浏览器登录后（不需要手动开 DevTools），AI 从本地浏览器的 Cookie 存储中自动提取。

**前提**：用户已在浏览器（Chrome/Safari/Edge）登录过 workspace.laicms.com。

**macOS Chrome 示例**（Cookie 存储为 SQLite，需解密）：

```bash
# 1. 定位 Cookie 数据库
cp ~/Library/Application\ Support/Google/Chrome/Default/Cookies <tmp>/chrome-cookies.db

# 2. 用 Python 解密提取（Chrome Safe Storage key 在 Keychain）
python3 - <<'EOF'
import sqlite3, subprocess, base64
# Chrome v10+ 加密：Keychain 取 "Chrome Safe Storage" 密钥 → PBKDF2 派生 → AES-CBC 解密
# （此路径依赖本机 Keychain 权限，可能弹窗要求授权）
db = sqlite3.connect('<tmp>/chrome-cookies.db')
row = db.execute(
    "SELECT encrypted_value FROM cookies WHERE host_key LIKE '%workspace.laicms.com%' AND name='payload-token'"
).fetchone()
# 解密逻辑...
EOF
```

**适用场景**：
- 用户不方便复制 Cookie（移动设备 / 不熟悉 DevTools）
- 需要频繁刷新 token 的长时任务

**限制**：
- macOS 会弹 Keychain 授权窗口（需要用户点确认）
- Chrome v127+ 的 Cookie 加密有变动（application-bound encryption），可能需要额外处理
- 多浏览器多 Profile 时定位复杂

> 方式三当前为方向指引，未在本部署实测——优先用方式一/二。

---

## Token 有效性验证（拿到后必做）

```python
from allincms_api import AllinCMS

import os; token = os.environ["WS_TOKEN"]   # export WS_TOKEN=<token>
api = AllinCMS(token=token)
sites = api.read_sites()
print([s["name"] for s in sites.get("sites", [])])   # 能列出站点 = token 有效
```

---

## 安全要点

| 要点 | 说明 |
|---|---|
| 密码不落盘 | 只在内存中用于一次登录请求；文件传递用完即删 |
| token 是凭据 | 等同登录态——不推送到公开仓库、不贴到公开文档 |
| token 有效期 | Payload 默认 JWT 有过期时间——过期后 read 会 401/空，重取即可 |
| 凭据位置 | 推荐 `WS_TOKEN` 环境变量（跨平台）；token 文件须 chmod 600（/tmp 重启清空） |
| 用完作废 | 任务收尾/凭据交接完成时**提醒用户退出登录或轮换改密作废本次 token**（口径对齐子库 README 一键块："换 token 后密码即弃并提醒我改密"） |
| 多账号 | 每个账号的 token 独立，不要混用——切换账号时重取 |

---

## 故障排查

| 症状 | 原因 | 解法 |
|---|---|---|
| `login failed: The email or password provided is incorrect.` | 凭据错误 | 检查邮箱/密码 |
| login 后 `响应无 payload-token` | 平台改了登录返回格式 | 改用方式二（浏览器手动取 Cookie） |
| read 返回 401 / 空 | token 过期或无效 | 重取 token |
| Server action not found | 部署已更新（action id 变了） | 用 `scan-actions.py` 重扫 action id |
