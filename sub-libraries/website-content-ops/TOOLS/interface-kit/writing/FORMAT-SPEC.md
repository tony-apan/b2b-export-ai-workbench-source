# 正文格式规范（FORMAT-SPEC.md）—— 单一真源，全部实测

> 来源：2026-08-29 编辑器截图+更新 payload 证据 + format-lab 1-6 轮实测。**凡本文档未列的格式，视为不支持（先 format-lab 验证再使用）**。

## 一、块类型清单（编辑器原生 vs 公网渲染，以公网为准）

> **类型词法（2026-08-30 与服务器存储形态统一）**：服务器对文章 content 的原生存储类型 = `p|h2|h3|blockquote`（read_post 实测 {p:22, h2:5, blockquote:1}）。下表以 `p` 为段落规范；旧词法 `paragraph` 仅作输入兼容（writing-module 会归一化为 p），`heading` 一律禁用。

| 格式 | 写法（JSON 模板） | 公网渲染 | 状态 |
|---|---|---|---|
| **H2 标题** | `{"type":"h2","children":[{"text":"QUICK ANSWER"}],"id":"IzlqkVwdg0"}` | `<h2 class="slate-h2 ... text-2xl font-semibold">` | ✅ **主用** |
| **H3 子标题** | `{"type":"h3","children":[{"text":"..."}],"id":"..."}` | `<h3 class="slate-h3 ...">` | ✅ 标题下分节 |
| **段落** | `{"type":"p","children":[{"text":"..."}],"id":"..."}`（旧词法 `paragraph` 输入兼容） | `<div data-slate-type="p" class="slate-p">` | ✅ |
| **加粗** | 段落内 `{"text":"...","bold":true}`（leaf） | `<strong>` | ✅ |
| **斜体/下划线** | `{"text":"...","italic":true}` / `{"underline":true}` | `<em>` / `<u>` | ✅ |
| **引用块（包裹）** | `{"children":[{"type":"p","children":[{"text":"..."}],"id":"..."}],"type":"blockquote","id":"..."}` | `<div class="slate-blockquote border-l-2 pl-6 italic">` | ✅ 重点/金句 |
| **空段（分隔）** | `{"type":"p","children":[{"text":""}],"id":"..."}` | 占行高（段落间距） | ✅ 每逻辑段后 |
| 编号/无序列表 | `{"type":"numbered-list"|"bulleted-list","children":[{list-item}]}` | 文本平铺（无 ul/ol 语义） | ❌ 禁用 |
| link / image / code / divider / table / todo / toggle / columns | 各类型 | 平铺或异常；link/image 无 `<a>/<img>` | ❌ 禁用（图片用 media 字段） |
| ~~heading~~ / ~~paragraph~~ | `{"type":"heading"}` / `{"type":"paragraph"}` | heading 无样式（编辑器不识别）；paragraph 为旧词法 | ❌ 勿用（用 h2 / p） |

## 二、id 与结构规则
- **每块带 id**：10 位字母数字（如 `c0gRgeKnnA`）；构建器自动生成
- **children 里 leaf**：`{"text":"...","bold":true}`（bold/italic/underline 可组合）
- **blockquote 必须包裹**：外层 `type:"blockquote"`、内层 `type:"p"`（扁平 children:[{text}] 无效）

## 三、范文章节（固定格式：标签→h2；说明紧跟）
```json
{"type":"h2","children":[{"text":"QUICK ANSWER"}],"id":"..."}
{"type":"p","children":[{"text":"For two adults on calm lakes ...","bold":true}],"id":"..."}
{"type":"p","children":[{"text":""}],"id":"..."}
{"type":"h2","children":[{"text":"01  LENGTH"}],"id":"..."}
{"type":"p","children":[{"text":"Why a longer hull ...","bold":true}],"id":"..."}
{"type":"p","children":[{"text":"...主段..."}],"id":"..."}
{"type":"p","children":[{"text":""}],"id":"..."}
```

## 四、禁用（违反即 audit/markdown 报错）
- 任何 Markdown 语法（`[text](url)` / `**` / `#`）——渲染为纯文本
- 单位不加空格（`5.2m`）→ 必须 `5.2 m / 68 cm / 220 kg`
- 绝对断言（无场景/边界限定的 always/usually/best）
- emoji 作图标（callout 组件自带 💡 → 弃用 callout，用 h2 标签段替代）
- 正文来源塞 alt（alt 只描述画面；credit 用独立段落+PHOTO CREDIT 标题）

## 五、工具链（生成/迁移/检查一次到位）
```bash
python3 writing/writing-module.py block h2 "QUICK ANSWER"        # 单块生成
python3 writing/writing-module.py skeleton <brief.json>          # 骨架（含空段/h2/credit/editorial）
python3 writing/writing-module.py check <article.json>           # 渐进+格式检查（三档）
python3 writing/writing-module.py migrate <article.json>        # 旧格式→原生 h2/blockquote 迁移
python3 site_pipeline.py audit <slug> --config 70_evidence/<slug>-audit-config.json   # 全站 13 项门（含 h2-semantic/root-home/form-render；必带每站 --config）
```
