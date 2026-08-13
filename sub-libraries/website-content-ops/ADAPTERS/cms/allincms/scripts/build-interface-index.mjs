#!/usr/bin/env node
import { readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { validateInterfaceRegistry, ADAPTER_ROOT } from './validate-interface-registry.mjs';

const INDEX_PATH = resolve(ADAPTER_ROOT, 'INTERFACE-INDEX.md');
const DOMAIN_LABELS = {
  authorization: '授权', workspace: '登录、用户与站点', media: '媒体',
  article_format: '文章格式', article_image: '文章正文图片', article: '文章',
  taxonomy: '分类与标签', product: '产品', run: '计划运行与证据', batch: '批处理', registry: '接口 Registry 工具', cli: '命令行',
};
const EXPOSURE_ORDER = ['canonical', 'supported', 'compatibility', 'internal', 'blocked'];
const escapeCell = (value) => String(value ?? '').replace(/\|/g, '\\|').replace(/\r?\n/g, ' ');
const bindingText = (item) => item.bindings.map((binding) => binding.type === 'esm_export'
  ? `\`${binding.module}#${binding.export_name}\``
  : `\`${binding.command}\``).join('<br>');
const refsText = (item) => item.contract_refs.map((ref) => `\`${ref.path}${ref.pointer || ''}\` [${ref.availability}]`).join('<br>');

export function renderInterfaceIndex(registry) {
  const counts = Object.fromEntries(EXPOSURE_ORDER.map((key) => [key, registry.interfaces.filter((item) => item.exposure === key).length]));
  const bindings = registry.interfaces.flatMap((item) => item.bindings);
  const esmCount = bindings.filter((binding) => binding.type === 'esm_export').length;
  const cliCount = bindings.filter((binding) => binding.type === 'cli').length;
  const lines = [
    '---',
    'title: "AllinCMS Interface Index"',
    'description: "由 interface-registry.json 确定性生成的 AllinCMS 人类与 AI 接口查询索引；只负责接口身份、分层和导航，不替代专项合同与部署证据。"',
    'type: "tooling"',
    'status: "Working"',
    'owner: "AI"',
    'created: "2026-08-11"',
    'last_updated: "2026-08-12"',
    'sources: ["interface-registry.json"]',
    'related: ["README.md", "AI-START-HERE.md", "interface-registry.schema.json"]',
    'when_to_read: "需要按接口名、导出名、领域、暴露层级或生命周期查询 AllinCMS Adapter 能力与限制时。"',
    'keywords: ["AllinCMS", "接口索引", "interface registry", "ESM export", "API lifecycle", "AI routing"]',
    'visibility: "public"',
    'redaction_status: "safe-to-publish"',
    '---',
    '<!-- GENERATED FILE. DO NOT EDIT. Run: npm run interfaces:index -->',
    '',
    '# AllinCMS 接口索引',
    '',
    '> 机器真源：`interface-registry.json`。本页完全生成，供人和 AI 快速查找；payload、transport、错误和部署证据仍以专项合同为准。',
    '',
    '## 当前边界',
    '',
    `- Registry：v${registry.registry_version}`,
    `- Adapter package：\`${registry.adapter.package_version}\``,
    `- Release scope：\`${registry.adapter.release_scope}\``,
    `- 固化范围：${registry.interfaces.length} 个接口记录（${esmCount} 个 ESM export binding + ${cliCount} 个 CLI）`,
    `- 审查：\`${registry.review.verdict}\`，${registry.review.reviewed_on}；${registry.review.scope}`,
    `- 暴露分层：canonical ${counts.canonical} / supported ${counts.supported} / compatibility ${counts.compatibility} / internal ${counts.internal} / blocked ${counts.blocked}`,
    '',
    '### 必须保留的限制',
    '',
    ...registry.review.limitations.map((item) => `- ${item}`),
    '',
    '## 查询方法',
    '',
    '- 人：按下方 domain 查表；默认业务路径只选 `canonical`，辅助能力选 `supported`。',
    '- AI：读取 `interface-registry.json`，按 `interface_id`、`display_name`、`bindings[].export_name`、`domain`、`exposure` 或 `keywords` 过滤。',
    '- 禁止把 `internal`、`compatibility` 或 `blocked` 当成默认入口。',
    '- 严格只读任务还必须要求 `safety.mutation=false`；`network_access=none` 只表示不联网，不保证没有本地文件写入。',
    '- CLI 范围只登记 4 个可直接操作的 Adapter 命令；`npm test` 与 `test:*` 是验证 harness，不是业务/查询接口。',
    '- 引用可用性必须读 `availability`：`packaged` 保证进入最小 npm 包；`source_only` 只在源码 checkout 中提供，最小包不得伪装为已携带。',
    '- 校验：`npm run interfaces:validate`；重建：`npm run interfaces:index`；漂移检查：`npm run interfaces:index:check`。',
    '',
    '## 能力路由',
    '',
    '> 路由回答“某个实体动作是否可执行、默认走哪个接口、受什么门禁约束”。它不是永久 capability，也不替代当前 deployment 的新鲜 capability snapshot。',
    '',
    '| Capability | 可用性 | 执行门禁 | 执行面 | 默认接口 | 串行 Controller | 验收要求 | 原因与限制 |',
    '|---|---|---|---|---|---|---|---|',
    ...registry.capability_routes.map((route) => {
      const defaultInterface = route.default_interface_id ? `\`${route.default_interface_id}\`` : '—';
      const controller = route.controller_interface_id ? `\`${route.controller_interface_id}\`` : '—';
      const requirements = route.verification_requirements.map(escapeCell).join('<br>');
      const boundary = [route.reason, ...route.limitations].map(escapeCell).join('<br>');
      return `| \`${route.capability_id}\` | **${route.availability}** | ${route.execution_gate} | ${route.execution_surface} | ${defaultInterface} | ${controller} | ${requirements} | ${boundary} |`;
    }),
    '',
    '## 接口目录',
    '',
  ];
  const domains = Object.keys(DOMAIN_LABELS);
  for (const domain of domains) {
    const items = registry.interfaces.filter((item) => item.domain === domain)
      .sort((a, b) => EXPOSURE_ORDER.indexOf(a.exposure) - EXPOSURE_ORDER.indexOf(b.exposure) || a.display_name.localeCompare(b.display_name));
    if (!items.length) continue;
    lines.push(`### ${DOMAIN_LABELS[domain]}（${items.length}）`, '');
    lines.push('| Interface ID | Binding | 类型 | 访问 | 暴露 | 生命周期 | 运行分发 | 证据 | 何时使用 | 合同与可用性 |');
    lines.push('|---|---|---|---|---|---|---|---|---|---|');
    for (const item of items) {
      const use = item.blocked_reason ? `${item.when_to_use} BLOCK：${item.blocked_reason}` : item.when_to_use;
      lines.push(`| \`${escapeCell(item.interface_id)}\` | ${bindingText(item)} | ${item.kind} | ${item.access} | **${item.exposure}** | ${item.lifecycle} | ${item.runtime_availability} | ${item.evidence.level} | ${escapeCell(use)} | ${refsText(item)} |`);
    }
    lines.push('');
  }
  lines.push('## 证据声明', '', '- 本索引只表示接口已被登记和分类，不表示所有接口 public、stable、production-ready 或跨部署兼容。', '- 当前本地测试通过只能支撑 `local_tested`；远程写入仍必须按接口合同完成授权、请求、后台回读及需要时的前台验收。', '- Registry 中的 `source_only` 测试或证据引用是源码 provenance，不属于最小 npm 运行包；`interfaces:validate` 会在源码模式要求其存在，在最小包模式只放行明确标注的缺失。', '');
  return `${lines.join('\n').replace(/\n+$/, '')}\n`;
}

async function main() {
  const check = process.argv.includes('--check');
  const validation = await validateInterfaceRegistry();
  if (!validation.ok) {
    console.error(validation.errors.join('\n'));
    process.exitCode = 1;
    return;
  }
  const rendered = renderInterfaceIndex(validation.registry);
  if (check) {
    let current = '';
    try { current = await readFile(INDEX_PATH, 'utf8'); } catch {}
    if (current !== rendered) {
      console.error('INTERFACE-INDEX.md is stale; run npm run interfaces:index');
      process.exitCode = 1;
      return;
    }
    console.log('INTERFACE-INDEX.md is current');
    return;
  }
  await writeFile(INDEX_PATH, rendered, 'utf8');
  console.log(`wrote ${INDEX_PATH}`);
}

if (import.meta.url === pathToFileURL(process.argv[1] || '').href) await main();
