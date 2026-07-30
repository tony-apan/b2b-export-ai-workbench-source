---
title: "Module Registry"
description: "用内容成熟度、当前焦点与执行状态三条轴登记业务模块，避免把优先级误当成可运行状态。"
type: "meta"
status: "Working"
owner: "AI"
created: "2026-06-28"
last_updated: "2026-07-27"
sources: ["User request", "Adversarial structure review 2026-07-26"]
related: ["current-focus.md", "module-expansion-sop.md", "../50_channels/index.md", "../30_playbooks/index.md"]
---
# Module Registry

模块“有页面”不等于“当前优先”或“可执行”，因此分开记录三种状态。

## 状态语义

### Lifecycle：内容成熟度

- `Seed`：只有骨架、问题或单一薄页；
- `Draft`：模型和流程已有，但证据或执行资产不足；
- `Working`：可支持实际任务，但还未经过稳定多轮验证；
- `Canonical`：已有重复验证，是当前权威做法。

### Focus：优先级

- `Current`：当前唯一业务焦点；
- `Backlog`：已登记但未进入当前焦点；
- `—`：本阶段不作为独立焦点。

### Execution：能否执行

- `Ready`：关键输入和权限齐备，可以开始单样本；
- `Blocked`：正在推进但缺外部决定、权限或关键条件；
- `Running`：已有获批单样本正在执行；
- `Validated`：按模块完成定义通过；
- `Dormant`：已有内容但本阶段不扩写。

同一时间原则上只有一个 `Current`，但它可以同时是 `Blocked`。当前焦点和验收闸见 [current-focus.md](current-focus.md)。

公开版说明：表中的 `Raw Folder` 是未来私有母库或客户运行区入口，当前公开仓库不存真实 raw。

## Existing Modules

| Module | Index | Main Playbook | Lifecycle | Focus | Execution | Owner | Evidence / next gate |
|---|---|---|---|---|---|---|---|
| Website Content Operations | [package](../../sub-libraries/website-content-ops/README.md) | [playbook](../../sub-libraries/website-content-ops/PLAYBOOK.md) | Draft | **Current** | **Blocked** | AI + Human | 虚拟实例、AllinCMS 单样本/10 张串行/文章与图片绑定证据已登记；当前部署范围内部分验证，跨部署、完整回滚和迁移仍待验证 |
| Website | [index](../50_channels/website/index.md) | [playbook](../30_playbooks/website-build.md) | Seed | — | Dormant | AI | 主 playbook 仍为 Seed；作为当前焦点依赖时局部补充 |
| LinkedIn | [index](../50_channels/linkedin/index.md) | [playbook](../30_playbooks/linkedin-content.md) | Working | — | Dormant | AI | 待未来独立运行与数据验证 |
| Email Outreach | [index](../50_channels/email-outreach/index.md) | [playbook](../30_playbooks/cold-email.md) | Seed | — | Dormant | AI | playbook 仍为 Seed |
| SEO | [index](../50_channels/seo/index.md) | [playbook](../30_playbooks/id-0011-seo-content.md) | Working | — | Dormant | AI | 只作为当前内容运营模块的意图与反馈依赖 |
| GEO / AI Search | [index](../50_channels/geo-ai-search/index.md) | [playbook](../30_playbooks/id-0010-geo-ai-search.md) | Working | — | Dormant | AI | 只作为当前内容运营模块的可引用性与测试依赖 |
| SEM / Ads | [index](../50_channels/sem-ads/index.md) | [playbook](../30_playbooks/sem-ads.md) | Working | — | Dormant | AI | 待未来独立实验闭环 |
| Sales | [playbook](../30_playbooks/sales-call.md) | [playbook](../30_playbooks/sales-call.md) | Seed | — | Dormant | AI | 尚无独立 module index 与运行证据 |
| Competitors | [index](../70_competitors/index.md) | [playbook](../30_playbooks/competitor-research.md) | Seed | — | Dormant | AI | playbook 仍为 Seed |
| Clients | [index](../60_clients/index.md) | [template](../_templates/client-profile.md) | Seed | — | Dormant | AI | 当前公开版不存真实客户资料 |
| Video Production | [index](../50_channels/video-production/index.md) | [playbook](../30_playbooks/video-production.md) | Seed | — | Dormant | AI | 不在当前阶段扩写 |
| Visual Design | [index](../50_channels/visual-design/index.md) | [playbook](../30_playbooks/visual-design.md) | Seed | — | Dormant | AI | 不在当前阶段扩写 |
| Short Video | [index](../50_channels/short-video/index.md) | [playbook](../30_playbooks/short-video-ops.md) | Working | — | Dormant | AI | 不在当前阶段扩写 |
| Trade Shows | [index](../50_channels/trade-shows/index.md) | [playbook](../30_playbooks/trade-show.md) | Seed | — | Dormant | AI | 不在当前阶段扩写 |
| Partners | [index](../50_channels/partners/index.md) | [playbook](../30_playbooks/partner-channel.md) | Seed | — | Dormant | AI | 不在当前阶段扩写 |
| B2B Marketplaces | [index](../50_channels/b2b-marketplaces/index.md) | [playbook](../30_playbooks/rfq-response.md) | Seed | — | Dormant | AI | 不在当前阶段扩写 |
| WhatsApp | [index](../50_channels/whatsapp/index.md) | [sales playbook](../30_playbooks/sales-call.md) | Seed | — | Dormant | AI | 不在当前阶段扩写 |

## Backlog Candidates

候选项只登记问题，不自动创建目录。当前保留一个候选：

| Candidate | Why | Promotion gate |
|---|---|---|
| Product Content System | 统一产品参数、应用、FAQ、证书、包装和质检内容 | Website Content Operations 已 `Validated`，且证明需要独立生命周期 |

## Module Index Minimum Fields

每个模块 index 至少包含：模块目标、适用场景、来源入口、主 playbook、常用模板、Lifecycle、Focus、Execution、owner、指标、完成定义和 open questions。
