---
title: "API-DISCOVERY.md —— AllinCMS 平台更新后 AI 摸索接口的标准流程"
description: "当 AllinCMS 部署升级导致 action id 或接口变化时，任何 AI 按本流程重新发现并适配 API。"
type: "runbook"
status: "Working"
owner: "AI"
created: "2026-08-30"
last_updated: "2026-08-30"
sources: ["Example 全流程实战（set_home_page/update_page/delete_category 均为逆向发现）", "ISS-070/073/074/076"]
related: ["RUNBOOK-ANYONE.md", "allincms_api.py", "scan/scan-actions.py"]
---

# API-DISCOVERY：AllinCMS 平台更新后的接口摸索流程

> **场景**：AllinCMS 部署升级 → action id 变了 / 接口字段变了 / 新功能出现了 → 你的工具突然不工作。
> **本流程告诉你怎么系统性重新摸索**，不是靠猜。

---

## 第一步：确认变化类型

| 症状 | 变化类型 | 跳到 |
|---|---|---|
| 请求返回 404 "Server action not found" | action id 变了 | 第二步：重扫 |
| 请求 200 但无效果（静默失败） | action 路径或参数变了 | 第三步：反编译 |
| 返回 `validationErrors` 新字段 | schema 变了 | 第四步：对比 |
| readback 出现新字段/新块 | 平台加了新功能 | 第五步：发现 |
| 突然多了 demo 内容 | 平台改了 default 模板 | 第六步：适配 |

---

## 第二步：重扫 action id（最常见场景）

### 2.1 扫描工具

```bash
cd <interface-kit>
python3 scan/scan-actions.py - /sites                          # 站点域
python3 scan/scan-actions.py - /<slug>/themes                  # 主题域（含页面管理）
python3 scan/scan-actions.py - /<slug>/themes/<theme_id>       # 主题概览页（页面 CRUD + setHomePage）
python3 scan/scan-actions.py - /<slug>/posts?tab=categories    # 分类/标签域
python3 scan/scan-actions.py - /<slug>/posts                   # 文章域
python3 scan/scan-actions.py - /<slug>/products                # 产品域
python3 scan/scan-actions.py - /<slug>/forms                   # 表单域
python3 scan/scan-actions.py - /<slug>/media                   # 媒体域
```

> **关键**：每个页面加载的 chunk 不同，**必须扫多个页面**才能覆盖全部 action。
> 懒加载域（如主题概览页的页面管理块）只在特定路由加载——扫不到就说明你要去那个页面看。

### 2.2 扫描结果

输出格式：`actionName = actionId`（42 位小写 hex）

```text
### /<your-site-key>/themes/6a9308e1.../design
  applyThemeRouteMappingAction = 7f1d7009b7d91ad4...
  createThemeAction = 7f3203f59ef09aa7...
  deleteThemeAction = 7fee07b6135885e8...
  setThemeActiveAction = 7f7f3eda0e33ad89...
  updateThemeAction = 7fe46f6230d01d08...
  setHomePageAction = 7f94c780f5f262f8...    ← 根路径设置
  createPageAction = 7fc39d5397233416...
  deletePageAction = 7f423eaf832c83717...
  updatePageAction = 7f75d7522d0cf2660...    ← 页面 meta description
  setPageEnabledAction = 7f35aa21ed412796...
  duplicatePageAction = 7fae37e87c404869...
```

### 2.3 对比 & 更新

```bash
# 把扫出的 id 与 allincms_api.py 里的常量对比
python3 - <<'PY'
# 示例：自动对比并报告差异
import re, sys
sys.path.insert(0, '.')
from allincms_api import AllinCMS

# 已知常量
known = {}
known.update(AllinCMS.THEME_ACTION_IDS)
known.update(AllinCMS.PAGE_ACTION_IDS)
known.update(AllinCMS.TAXONOMY_ACTION_IDS)

# 扫描结果（粘贴到这里）
scanned = {
    'setHomePageAction': '7f94c780f5f262f8...',  # 从 scan-actions.py 输出复制
    'updatePageAction': '7f75d7522d0cf2660...',
    # ...
}

# 方法：把 known 里的 key 映射到 action 名
key_to_name = {
    'createTheme': 'createThemeAction', 'updateTheme': 'updateThemeAction',
    'deleteTheme': 'deleteThemeAction', 'setActive': 'setThemeActiveAction',
    'applyRoutes': 'applyThemeRouteMappingAction',
    'setHomePage': 'setHomePageAction', 'updatePage': 'updatePageAction',
    'deletePage': 'deletePageAction', 'createPage': 'createPageAction',
    'setPageEnabled': 'setPageEnabledAction', 'duplicatePage': 'duplicatePageAction',
    'deleteCategory': 'deleteCategoryAction', 'deleteTag': 'deleteTagAction',
    # ...
}

for key, old_id in known.items():
    name = key_to_name.get(key, key + 'Action')
    new_id = scanned.get(name)
    if new_id and new_id != old_id:
        print(f'⚠️ {name}: {old_id[:14]}... → {new_id[:14]}...  需要更新！')
    elif not new_id:
        print(f'❓ {name}: 未扫描到（可能在本页 chunk 之外）')
    else:
        print(f'✅ {name}: 一致')
PY
```

### 2.4 更新 allincms_api.py

发现差异后，直接改常量：

```python
# allincms_api.py 顶部常量区
CREATE_SITE_A   = "7fedc609bd55e075..."   # ← 换新 id
```

或改 PAGE_ACTION_IDS / THEME_ACTION_IDS / TAXONOMY_ACTION_IDS 字典。

---

## 第三步：反编译 chunk（发现新接口或参数变化）

当扫描发现**新的 action 名**（不在已知列表），或已知 action 参数疑似变化：

### 3.1 下载 chunk

```bash
# 从工作台页面 HTML 提取 chunk URL
TOKEN="$WS_TOKEN"
curl -s -H "Cookie: payload-token=$TOKEN" "https://workspace.laicms.com/<slug>/themes/<theme_id>" | \
  grep -oE '/_next/static/chunks/[a-zA-Z0-9_.-]+\.js' | sort -u

# 下载可疑 chunk（通常新功能的 chunk 只在特定页面加载）
curl -s "https://workspace.laicms.com/_next/static/chunks/<chunk_name>.js" -o /tmp/chunk.js
```

### 3.2 提取关键信息

```python
# 三类必提信息：
import re
s = open('/tmp/chunk.js', encoding='utf-8', errors='replace').read()

# ① action id + 名字
for m in re.finditer(r'createServerReference\)\("([0-9a-f]{42})",[^)]{0,160}?,"([A-Za-z0-9_$.]{4,100})"', s):
    print(f'{m.group(2)} = {m.group(1)}')

# ② zod schema（接口参数格式）
for m in re.finditer(r'z\.object\(\{([^}]{10,500})\}', s):
    schema = m.group(1)
    if any(k in schema for k in ('siteId', 'name', 'slug', 'id')):
        print(f'SCHEMA: {schema[:300]}')

# ③ 调用 payload（客户端怎么传参）
# 找 createServerReference 后面的变量被调用的地方
# 例如：ej({id: e.id, siteId: w, themeId: a}) → 说明参数是 {id, siteId, themeId}
```

### 3.3 实际例子（Example set_home_page 的发现过程）

```text
1. 在主题概览页 chunk (12rhvrcyv9te_.js) 发现 setHomePageAction = 7f94c780...
2. 在同 chunk 找到调用处：ej({id: e.id, siteId: w, themeId: a})
3. 推断参数：{id: pageId, siteId, themeId}
4. 但 POST 到 /{slug}/themes 返回 200 静默无效
5. 改 POST 到 /{slug}/themes/{themeId} → 成功！
6. 结论：action 的 URL 路径绑定到页面路由（不是固定的）
```

**关键教训**：action 的 URL 路径 = 你在哪个页面调用它。同一个 action 在不同路径可能行为不同。

---

## 第四步：Schema 变化对比

平台升级后字段可能变。用 readback 对比：

```python
# 读一个产品/文章/页面的当前 schema
from allincms_api import AllinCMS
import os; api = AllinCMS(token=os.environ["WS_TOKEN"])  # export WS_TOKEN=<token>（或 token 文件路径）

# 产品 schema
prod = api.read_product('slug', 'product_id')
print(json.dumps(prod, indent=1, ensure_ascii=False)[:2000])

# 页面 schema
page = api.read_page_document('slug', 'theme_id', 'page_id')
print(json.dumps(page['initialPayload']['page'].keys()))

# 表单 schema
forms = api.read_page_document('slug', 'theme_id', 'home_page_id')
print(json.dumps(forms['initialPayload'].get('initialForms', {}), indent=1)[:1000])
```

**发现新字段** → 试着在 create/publish payload 里传，看是否报错或生效。
**发现字段消失** → 检查是否被重命名或废弃。

---

## 第五步：发现新功能

### 5.1 新页面/新块类型

```python
# 读主题页面的全部块类型
r = api.read_pages('slug', 'theme_id')
for p in r['pages']:
    doc = api.read_page_document('slug', 'theme_id', p['id'])
    types = set()
    for el in doc['initialPayload']['page']['document']['elements'].values():
        types.add(el.get('type'))
    print(f"{p['path']}: {types}")
```

### 5.2 新 action（扫到了但不知道干什么）

```python
# 用无害参数试探（比如传空对象）
import json
s, t = api._req('/slug/some_path', 'unknown_action_id_42hex', [{}])
print(s, t[:200])
# 看返回：validationErrors 会告诉你必填字段名！
```

**技巧**：`validationErrors` 是最好的 API 文档——它会精确告诉你每个字段期望什么类型。

---

## 第六步：平台改了 default 模板（demo 内容变了）

```bash
# 建站后立即对比 demo 内容清单
python3 - <<'PY'
from allincms_api import AllinCMS
import os; api = AllinCMS(token=os.environ["WS_TOKEN"])  # export WS_TOKEN=<token>（或 token 文件路径）
for kind in ('products', 'posts'):
    items = api.read_lists('slug', kind)['data']
    demo = [x for x in items if x['slug'] in (
        'modular-packing-pouch', 'stackable-desk-tray-set', 'waxed-canvas-weekender',
        'small-entryway-system', 'material-care-buying-decision', 'choose-a-weekender-bag')]
    if demo:
        print(f'{kind} demo: {[x["slug"] for x in demo]}')
        # 如果 slug 变了 → 更新 delete-demo-content.py 的 DEMO_*_SLUGS 常量
PY
```

---

## 第七步：验证更新

改完 allincms_api.py 后必须验证：

```bash
# 1. 语法
python3 -c "import ast; ast.parse(open('allincms_api.py').read()); print('OK')"

# 2. 每个 action id 长度 = 42
python3 -c "
from allincms_api import AllinCMS
for name, ids in [('THEME', AllinCMS.THEME_ACTION_IDS), ('PAGE', AllinCMS.PAGE_ACTION_IDS), ('TAXONOMY', AllinCMS.TAXONOMY_ACTION_IDS)]:
    for k, v in ids.items():
        assert len(v) == 42, f'{name}.{k} = {len(v)} chars!'
print('All action IDs = 42 chars ✓')
"

# 3. 用一个只读 action 实测（如 read_sites）
python3 -c "
from allincms_api import AllinCMS
import os; api = AllinCMS(token=os.environ["WS_TOKEN"])  # export WS_TOKEN=<token>（或 token 文件路径）
print('sites:', len(api.read_sites().get('sites', [])))
"

# 4. 用一个幂等写 action 实测（如 set_home_page 重设当前值）
# 5. 跑全站审计
python3 site_pipeline.py audit <slug> --config <cfg>
```

---

## 快速参考卡（打印给 AI）

```
┌──────────────────────────────────────────────────────────────┐
│  API 变了？三分钟诊断流程                                        │
├──────────────────────────────────────────────────────────────┤
│  1. 跑 scan-actions.py 扫多个页面 → 新 id？                     │
│     → 更新 allincms_api.py 常量                               │
│                                                              │
│  2. id 没变但不生效？                                          │
│     → 下载 chunk 反编译看 zod schema + 调用 payload            │
│     → 检查 URL 路径（action 绑定到页面路由）                    │
│                                                              │
│  3. 传空对象 {} 看返回的 validationErrors                       │
│     → 它会告诉你每个字段的期望类型                               │
│                                                              │
│  4. readback 对比旧数据 → 发现新字段/新块/新功能                │
│                                                              │
│  5. 改完后必跑：语法 + 42位校验 + 只读实测 + audit              │
└──────────────────────────────────────────────────────────────┘
```
