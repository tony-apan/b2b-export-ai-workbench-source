#!/usr/bin/env node
/**
 * Keep the customer workspace template self-contained.
 *
 * TEMPLATES/ and PLAYBOOKS/ are canonical sources for the sub-library.
 * The selected files below are generated runtime-safe copies for
 * WORKSPACE-TEMPLATE/, whose consumer may receive only the workspace directory.
 */
import { createHash } from 'node:crypto';
import { existsSync, lstatSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptPath = fileURLToPath(import.meta.url);
const libraryRoot = resolve(dirname(scriptPath), '..');
const sourceDir = join(libraryRoot, 'TEMPLATES');
const runtimeDir = join(libraryRoot, 'WORKSPACE-TEMPLATE', 'TEMPLATES');
const playbookSourceDir = join(libraryRoot, 'PLAYBOOKS');
const runtimePlaybookDir = join(libraryRoot, 'WORKSPACE-TEMPLATE', '30_tasks');
const checkOnly = process.argv.includes('--check');

const runtimePlaybookFiles = new Map([
  ['id-0001-b2b-seo-article-standard.md', 'b2b-seo-article-standard.runtime.md'],
  ['id-0003-b2b-article-optimization-sop.md', 'b2b-article-optimization-sop.runtime.md'],
  ['id-0004-b2b-article-stage-patterns.md', 'b2b-article-stage-patterns.runtime.md'],
  ['id-0005-source-driven-cms-operation-sop.md', 'source-driven-cms-operation-sop.runtime.md'],
]);

const runtimeTemplateFiles = [
  'article-brief.md',
  'article-draft.md',
  'article-quality-review.md',
  'company-profile.md',
  'content-operation-plan.md',
  'customer-voice-to-content.md',
  'failure-diagnosis.md',
  'image-manifest.md',
  'product-record.md',
  'publish-record.md',
  'source-extraction.md',
  'source-register.md',
  'tool-field-map.md',
];

const runtimeTemplateTargets = new Set(['README.md', ...runtimeTemplateFiles]);
const runtimeTaskTargets = new Set(['index.md', ...runtimePlaybookFiles.values()]);

const linkReplacements = new Map([
  ['../INTAKE.md', '../00_intake/index.md'],
  ['../PLAYBOOK.md', '../30_tasks/index.md'],
  ['../PLAYBOOKS/id-0001-b2b-seo-article-standard.md', '../30_tasks/b2b-seo-article-standard.runtime.md'],
  ['../PLAYBOOKS/id-0003-b2b-article-optimization-sop.md', '../30_tasks/b2b-article-optimization-sop.runtime.md'],
  ['../PLAYBOOKS/id-0004-b2b-article-stage-patterns.md', '../30_tasks/b2b-article-stage-patterns.runtime.md'],
  ['../PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md', '../30_tasks/source-driven-cms-operation-sop.runtime.md'],
  ['../SCHEMAS/content-operation-plan.schema.json', '../30_tasks/source-driven-cms-operation-sop.runtime.md'],
  ['../SCHEMAS/source-extraction.schema.json', '../30_tasks/source-driven-cms-operation-sop.runtime.md'],
  ['../scripts/validate-content-operation-plan.mjs', '../30_tasks/source-driven-cms-operation-sop.runtime.md'],
  ['../scripts/validate-source-extraction.mjs', '../30_tasks/source-driven-cms-operation-sop.runtime.md'],
  ['../QA-CHECKLIST.md', '../40_outputs/index.md'],
  ['../MENTAL-MODEL.md', '../20_knowledge/index.md'],
  ['../ADAPTERS/README.md', '../30_tasks/index.md'],
  ['../COURSE-MAP.md', '../20_knowledge/index.md'],
  ['../SOURCES.md', '../10_sources/index.md'],
  ['../WRITEBACK.md', '../90_writeback/index.md'],
  ['../WORKSPACE-TEMPLATE/10_sources/index.md', '../10_sources/index.md'],
]);

const generatedBy = 'scripts/sync-workspace-template.mjs';
const runtimeReadmeGeneratedFrom = '../../scripts/sync-workspace-template.mjs#runtimeReadmeSource+runtimeIndexTable';

// Canonical pre-metadata source for the generated runtime template index.
// Its digest is calculated after the generated index table is inserted, so the
// README projection is bound to both this stable source and its template inputs.
const runtimeReadmeSource = `---
title: "Customer Workspace Template Runtime Templates"
description: "客户运行区内可直接复制的最小模板集合，覆盖来源登记、公司与产品事实、内容 brief、图片、发布、字段映射和失败诊断。"
type: "index"
status: "Draft"
owner: "AI"
created: "2026-07-28"
last_updated: "2026-07-31"
sources: []
related: ["../00_intake/index.md", "../10_sources/index.md", "../20_knowledge/index.md", "../30_tasks/index.md", "../40_outputs/index.md", "../90_writeback/index.md"]
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
runtime_visibility: "private"
---
# 运行区模板

本目录只放客户运行区需要的最小模板。它是由子库根目录的 \`TEMPLATES/\` 生成的运行时副本，不是第二个长期维护真源；源码模板更新后运行 \`node scripts/sync-workspace-template.mjs\` 重新生成。每份生成文件都带有 \`generated_from\`、\`generated_source_sha256\` 和 \`generated_by\`，AI 不得直接把运行区副本改成新的母版。

## 选择规则

- 来源进入 [来源登记模板](source-register.md)，不要只在聊天里留结论。
- 用户资料驱动的新建/更新先读 [Source-Driven CMS SOP](../30_tasks/source-driven-cms-operation-sop.runtime.md)，再填写 [Content Operation Plan](content-operation-plan.md)；站点、字段、taxonomy、产品结构与 Action ID 不得从示例写死。
- 公司和产品事实分别使用 [公司模板](company-profile.md) 与 [产品模板](product-record.md)。
- 客户语言先用 [客户语言模板](customer-voice-to-content.md)，再转成 [文章 brief](article-brief.md)，使用 [文章草稿](article-draft.md) 建立正文合同，草稿完成后再使用 [文章质量审查](article-quality-review.md)。
- 新写正式文章先读 [B2B SEO 文章标准](../30_tasks/b2b-seo-article-standard.runtime.md) 与 [B2B 文章阶段模式](../30_tasks/b2b-article-stage-patterns.runtime.md)；优化已有文章再读 [B2B 文章优化 SOP](../30_tasks/b2b-article-optimization-sop.runtime.md)。
- 图片和发布分别使用 [图片清单](image-manifest.md) 与 [发布记录](publish-record.md)；API 成功不能替代后台、编辑器和前台验收。
- 工具接入先完成 [字段映射](tool-field-map.md)；失败时使用 [失败诊断](failure-diagnosis.md)，不要盲目重试。

模板填写完成不等于执行完成；真实动作、后台或前台回读、人工审批、失败与写回仍按运行区各层入口执行。

<!-- INDEX:BEGIN generated by scripts/sync-workspace-template.mjs; do not hand-edit -->
<!-- INDEX:END -->
`;

function sha256(content) {
  return createHash('sha256').update(content).digest('hex');
}
function dedupeInlineArrayField(content, field) {
  return content.replace(new RegExp(`^${field}:\\s*\\[([^\\]]*)\\]\\s*$`, 'm'), (line, inner) => {
    const values = [...inner.matchAll(/["']([^"']+)["']/g)].map((match) => match[1]);
    const unique = [...new Set(values)];
    return `${field}: [${unique.map((value) => JSON.stringify(value)).join(', ')}]`;
  });
}
function generatedMetadata(generatedFrom, sourceContent) {
  return {
    generated_from: generatedFrom,
    generated_source_sha256: sha256(sourceContent),
    generated_by: generatedBy,
  };
}
function injectGeneratedMetadata(content, fields) {
  const end = content.indexOf('\n---', 4);
  if (end === -1) throw new Error('source document lacks front matter');
  const metadata = Object.entries(fields).map(([key, value]) => `${key}: ${JSON.stringify(value)}`).join('\n');
  return `${content.slice(0, end)}\n${metadata}${content.slice(end)}`;
}
function insertMarker(content, marker) {
  const end = content.indexOf('\n---', 4);
  if (end === -1) throw new Error('generated document lacks front matter');
  const insertAt = end + 4;
  return `${content.slice(0, insertAt)}\n${marker}${content.slice(insertAt)}`;
}
function transform(content, file) {
  let output = content;
  for (const [from, to] of linkReplacements) output = output.split(from).join(to);
  output = output.replace(/\.\.\/ADAPTERS\/[^"\s\])]+/g, '../30_tasks/index.md');
  if (file === 'tool-field-map.md') output = output.replace('transfer-exercise-record.md', 'failure-diagnosis.md');
  output = dedupeInlineArrayField(dedupeInlineArrayField(output, 'sources'), 'related');
  output = output.replace(/\n<!-- Generated runtime copy from TEMPLATES\/[^>]+ -->\n/g, '\n');
  output = injectGeneratedMetadata(output, generatedMetadata(`../../TEMPLATES/${file}`, content));
  return insertMarker(output, `<!-- Generated runtime copy from TEMPLATES/${file}; do not hand-edit this copy in the source package. -->`);
}
function replaceFrontMatterInlineArrayValue(content, field, from, to) {
  return content.replace(new RegExp(`^${field}:\\s*\\[([^\\]]*)\\]\\s*$`, 'm'), (line) => line
    .replaceAll(JSON.stringify(from), JSON.stringify(to))
    .replaceAll(`'${from}'`, `'${to}'`));
}
function transformPlaybook(content, sourceFile) {
  let output = content
    .replace(/^doc_id:\s*["']?([^\n"']+)["']?\s*$/m, 'source_doc_id: "$1"')
    .replaceAll('id-0001-b2b-seo-article-standard.md', 'b2b-seo-article-standard.runtime.md')
    .replaceAll('id-0003-b2b-article-optimization-sop.md', 'b2b-article-optimization-sop.runtime.md')
    .replaceAll('id-0004-b2b-article-stage-patterns.md', 'b2b-article-stage-patterns.runtime.md')
    .replaceAll('id-0005-source-driven-cms-operation-sop.md', 'source-driven-cms-operation-sop.runtime.md')
    .replaceAll('../REFERENCES/SRC-20260731-B2B-SEO-CONTENT-RESEARCH.md', '../10_sources/index.md')
    .replaceAll('../EXAMPLES/fluxpedal-motors/customer-voice.md', '../20_knowledge/index.md')
    .replaceAll('../TEMPLATES/content-operation-plan.md', '../TEMPLATES/content-operation-plan.md')
    .replaceAll('../SCHEMAS/content-operation-plan.schema.json', 'source-driven-cms-operation-sop.runtime.md')
    .replaceAll('../scripts/validate-content-operation-plan.mjs', 'source-driven-cms-operation-sop.runtime.md')
    .replaceAll('../AGENTS.md', '../README.md')
    .replaceAll('../INTAKE.md', '../00_intake/index.md')
    .replaceAll('../MENTAL-MODEL.md', '../20_knowledge/index.md')
    .replaceAll('../RUNTIME-CONTRACT.json', '../README.md')
    .replace(/\.\.\/ADAPTERS\/[^"\s\],)]+/g, 'index.md')
    .replaceAll('../QA-CHECKLIST.md', '../40_outputs/index.md');
  output = replaceFrontMatterInlineArrayValue(output, 'related', 'README.md', 'index.md');
  output = dedupeInlineArrayField(dedupeInlineArrayField(output, 'sources'), 'related');
  output = injectGeneratedMetadata(output, generatedMetadata(`../../PLAYBOOKS/${sourceFile}`, content));
  return insertMarker(output, `<!-- Generated runtime projection from PLAYBOOKS/${sourceFile}; canonical edits belong in the core package. -->`);
}

function metadata(content, field) {
  return content.match(new RegExp(`^${field}:\\s*["']?([^\\n"']+)["']?\\s*$`, 'm'))?.[1]?.trim() ?? '';
}
function runtimeIndexTable(sourceContents) {
  const rows = runtimeTemplateFiles.map((file) => {
    const content = sourceContents.get(file);
    const title = metadata(content, 'title') || file;
    const description = metadata(content, 'description') || '未填写 description';
    const type = metadata(content, 'type') || 'template';
    return `| [${title}](${file}) | ${description.replaceAll('|', '\\|')} | ${type} | 需要填写同类记录时 |`;
  });
  return `<!-- INDEX:BEGIN generated by scripts/sync-workspace-template.mjs; do not hand-edit -->
## 当前目录直接入口

> 本表只列当前目录的直接模板文件；需要继续执行时，请回到对应的工作区层级入口。

| 入口 | 内容说明（description） | 类型 | 什么时候读 |
|---|---|---|---|
${rows.join('\n')}

<!-- INDEX:END -->`;
}

function expectedFiles() {
  const sourceContents = new Map();
  const metadataByFile = new Map();
  for (const file of runtimeTemplateFiles) {
    const sourcePath = join(sourceDir, file);
    if (!existsSync(sourcePath)) throw new Error(`missing canonical template: ${relative(libraryRoot, sourcePath)}`);
    sourceContents.set(file, readFileSync(sourcePath, 'utf8'));
  }
  const readmeSource = runtimeReadmeSource.replace(/<!-- INDEX:BEGIN generated by scripts\/sync-workspace-template\.mjs; do not hand-edit -->[\s\S]*?<!-- INDEX:END -->/, runtimeIndexTable(sourceContents));
  const readmeMetadata = generatedMetadata(runtimeReadmeGeneratedFrom, readmeSource);
  const files = new Map([['README.md', injectGeneratedMetadata(readmeSource, readmeMetadata)]]);
  metadataByFile.set('README.md', readmeMetadata);
  for (const file of runtimeTemplateFiles) {
    const content = sourceContents.get(file);
    files.set(file, transform(content, file));
    metadataByFile.set(file, generatedMetadata(`../../TEMPLATES/${file}`, content));
  }
  return { files, metadataByFile };
}
function expectedPlaybookFiles() {
  const files = new Map();
  const metadataByFile = new Map();
  for (const [sourceFile, targetFile] of runtimePlaybookFiles) {
    const sourcePath = join(playbookSourceDir, sourceFile);
    if (!existsSync(sourcePath)) throw new Error(`missing canonical playbook: ${relative(libraryRoot, sourcePath)}`);
    const content = readFileSync(sourcePath, 'utf8');
    files.set(targetFile, transformPlaybook(content, sourceFile));
    metadataByFile.set(targetFile, generatedMetadata(`../../PLAYBOOKS/${sourceFile}`, content));
  }
  return { files, metadataByFile };
}
function inspectProjectionDirectory(directory, allowedTargets, readableTargets, label) {
  const files = new Map();
  const seen = new Set();
  const entryProblems = [];
  if (!existsSync(directory)) return { files, seen, entryProblems };

  const directoryStats = lstatSync(directory);
  if (directoryStats.isSymbolicLink() || !directoryStats.isDirectory()) {
    entryProblems.push(`non-directory generated projection root: ${label}`);
    return { files, seen, entryProblems };
  }

  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const entryLabel = `${label}/${entry.name}`;
    seen.add(entry.name);
    if (!allowedTargets.has(entry.name)) {
      entryProblems.push(`unexpected generated projection entry: ${entryLabel}`);
      continue;
    }

    const entryPath = join(directory, entry.name);
    const stats = lstatSync(entryPath);
    if (stats.isSymbolicLink() || !stats.isFile()) {
      entryProblems.push(`non-regular generated projection entry: ${entryLabel}`);
      continue;
    }
    if (readableTargets.has(entry.name)) files.set(entry.name, readFileSync(entryPath, 'utf8'));
  }
  return { files, seen, entryProblems };
}
function actualFiles() {
  return inspectProjectionDirectory(
    runtimeDir,
    runtimeTemplateTargets,
    runtimeTemplateTargets,
    'WORKSPACE-TEMPLATE/TEMPLATES',
  );
}
function actualPlaybookFiles() {
  return inspectProjectionDirectory(
    runtimePlaybookDir,
    runtimeTaskTargets,
    new Set(runtimePlaybookFiles.values()),
    'WORKSPACE-TEMPLATE/30_tasks',
  );
}
function frontMatterFieldValues(content, field) {
  const frontMatterMatch = content.match(/^---\n([\s\S]*?)\n---(?:\n|$)/);
  if (!frontMatterMatch) return [];
  return frontMatterMatch[1]
    .split('\n')
    .filter((line) => line.startsWith(`${field}:`))
    .map((line) => {
      const raw = line.slice(field.length + 1).trim();
      try {
        return JSON.parse(raw);
      } catch {
        return raw.replace(/^["']|["']$/g, '');
      }
    });
}
function generatedMetadataProblems(content, expectedMetadata, label) {
  const problems = [];
  for (const [field, expectedValue] of Object.entries(expectedMetadata)) {
    const values = frontMatterFieldValues(content, field);
    if (values.length !== 1) {
      problems.push(`${label} must contain exactly one ${field} field`);
    } else if (values[0] !== expectedValue) {
      problems.push(`${label} has invalid ${field}`);
    }
  }
  return problems;
}

const { files: expected, metadataByFile: expectedMetadata } = expectedFiles();
const { files: actual, entryProblems: runtimeTemplateEntryProblems } = actualFiles();
const { files: expectedPlaybooks, metadataByFile: expectedPlaybookMetadata } = expectedPlaybookFiles();
const {
  files: actualPlaybooks,
  seen: actualTaskEntries,
  entryProblems: runtimeTaskEntryProblems,
} = actualPlaybookFiles();
const problems = [];
const unexpectedProblems = [...runtimeTemplateEntryProblems, ...runtimeTaskEntryProblems];
for (const [file, content] of expected) {
  const label = `WORKSPACE-TEMPLATE/TEMPLATES/${file}`;
  const actualContent = actual.get(file);
  if (actualContent === undefined || actualContent !== content) problems.push(`stale or missing runtime template: ${label}`);
  if (actualContent !== undefined) problems.push(...generatedMetadataProblems(actualContent, expectedMetadata.get(file), label));
}
for (const [file, content] of expectedPlaybooks) {
  const label = `WORKSPACE-TEMPLATE/30_tasks/${file}`;
  const actualContent = actualPlaybooks.get(file);
  if (actualContent === undefined || actualContent !== content) problems.push(`stale or missing runtime playbook: ${label}`);
  if (typeof actualContent === 'string') problems.push(...generatedMetadataProblems(actualContent, expectedPlaybookMetadata.get(file), label));
}
if (!actualTaskEntries.has('index.md')) unexpectedProblems.push('missing canonical runtime task index: WORKSPACE-TEMPLATE/30_tasks/index.md');
problems.push(...unexpectedProblems);

if (checkOnly || unexpectedProblems.length) {
  if (problems.length) {
    for (const problem of problems) console.error(`FAIL: ${problem}`);
    process.exitCode = 1;
  } else {
    console.log(`WORKSPACE_TEMPLATE_SYNC_PASS: ${expected.size + expectedPlaybooks.size} generated files are current with verified metadata`);
  }
} else {
  mkdirSync(runtimeDir, { recursive: true });
  mkdirSync(runtimePlaybookDir, { recursive: true });
  for (const [file, content] of expected) writeFileSync(join(runtimeDir, file), content);
  for (const [file, content] of expectedPlaybooks) writeFileSync(join(runtimePlaybookDir, file), content);
  console.log(`WORKSPACE_TEMPLATE_SYNCED: ${expected.size + expectedPlaybooks.size} files`);
}
