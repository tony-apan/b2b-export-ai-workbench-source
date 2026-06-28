---
title: "Module Expansion SOP"
description: "定义如何新增视频制作、作图、短视频运营、skill 或其他外贸 B2B 模块，保证扩展时不破坏现有结构。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-06-28"
sources: ["User request"]
related: ["module-registry.md", "markdown-standard.md", "task-router.md"]
---

# Module Expansion SOP

当要新增一个模块，比如视频制作 SOP、作图 SOP、短视频运营、展会、渠道商、AI skill，不要只新建一个孤立页面。按下面流程扩展。

## Step 1: 判断模块类型

| 类型 | 放哪里 | 例子 |
|---|---|---|
| Channel | `wiki/50_channels/{module}/index.md` | LinkedIn、短视频、展会、Ads |
| Playbook | `wiki/30_playbooks/{module}.md` | 视频制作 SOP、作图 SOP、客户访谈 SOP |
| Business System | `wiki/40_business/{module}.md` | 产品内容系统、offer 系统 |
| Concept | `wiki/20_concepts/{module}.md` | UGC、social proof、buyer intent |
| Template | `wiki/_templates/{module}.md` | 视频 brief、图片 brief、脚本模板 |
| Skill | 独立 skill 仓库或 `wiki/30_playbooks/{skill-name}.md` 先定义 | 自动化图片生成、视频脚本生成 |

## Step 2: 新建最小文件集

新增一个正式模块至少创建或更新：

1. Raw folder：`raw/{module}/`
2. Module index：`wiki/50_channels/{module}/index.md` 或对应业务目录。
3. Playbook：`wiki/30_playbooks/{module}.md`
4. Template：如需要，放 `wiki/_templates/{module}-brief.md`
5. Registry：更新 [module-registry.md](module-registry.md)
6. Main index：更新 [../index.md](../index.md)、[../30_playbooks/index.md](../30_playbooks/index.md)、[../50_channels/index.md](../50_channels/index.md)
7. Source taxonomy：如出现新资料类型，更新 [source-taxonomy.md](source-taxonomy.md)

## Step 3: Front Matter

所有新增 Markdown 必须包含：

```yaml
---
title: ""
description: ""
type: ""
status: "Seed"
owner: "AI"
created: "YYYY-MM-DD"
last_updated: "YYYY-MM-DD"
sources: []
related: []
---
```

## Step 4: 模块 SOP 骨架

每个新增 playbook 必须回答：

- 什么时候用？
- 输入资料是什么？
- 输出是什么？
- 步骤是什么？
- 质量检查是什么？
- 指标是什么？
- 和哪些模块联动？
- 哪些情况不能使用？

## Step 5: Skill 判断

如果某个 SOP 需要反复调用工具、生成固定格式、读写特定文件、或需要多步自动化，可以考虑做成 skill。

先不要直接做 skill。先沉淀为 playbook，跑 3-5 次稳定后，再抽象成 skill。

## Example: 增加视频制作 SOP

最小变更：

- 新建 `raw/video-production/`
- 新建 `wiki/50_channels/video-production/index.md`
- 新建 `wiki/30_playbooks/video-production.md`
- 新建 `wiki/_templates/video-brief.md`
- 更新 `module-registry.md`
- 更新 `wiki/index.md`, `30_playbooks/index.md`, `50_channels/index.md`

## Example: 增加作图 SOP

最小变更：

- 新建 `raw/visual-design/`
- 新建 `wiki/50_channels/visual-design/index.md`
- 新建 `wiki/30_playbooks/visual-design.md`
- 新建 `wiki/_templates/image-brief.md`
- 定义图片用途：LinkedIn、Ads、网站、产品图、案例图、信息图。

