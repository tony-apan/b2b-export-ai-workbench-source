#!/usr/bin/env node
/**
 * Adversarial checks for Markdown metadata and hierarchical indexes.
 * This is intentionally separate from the release validator so it can be used
 * while a library is still BLOCK and before any artifact is built.
 */
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { dirname, extname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { readFrontMatter, stringField, stringListField } from './lib/markdown-front-matter.mjs';
import { extractMarkdownLinks } from './lib/markdown-links.mjs';

const scriptPath = fileURLToPath(import.meta.url);
const root = resolve(dirname(scriptPath), '..');
const checkOnly = process.argv.includes('--check');
const strictMode = process.argv.includes('--strict') || process.argv.includes('--release');
const ignoredDirs = new Set(['.git', '.obsidian', 'node_modules', 'dist', '.cache', 'runtime', 'customer-runtime', 'credentials', 'secrets', '.secrets', 'private', 'workspace']);
const failures = [];
const warnings = [];
function fail(message) { failures.push(message); }
function warn(message) { warnings.push(message); }
function walk(dir) {
  const result = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (ignoredDirs.has(entry.name)) continue;
    const target = join(dir, entry.name);
    if (entry.isDirectory()) result.push(...walk(target));
    else result.push(target);
  }
  return result;
}

const metadataCache = new Map();
function parseFrontMatter(filePath) {
  if (metadataCache.has(filePath)) return metadataCache.get(filePath);
  let parsed;
  try {
    parsed = readFrontMatter(filePath);
  } catch (error) {
    fail(`invalid YAML front matter: ${relative(root, filePath)} (${error.message})`);
    metadataCache.set(filePath, null);
    return null;
  }
  if (!parsed) {
    metadataCache.set(filePath, null);
    return null;
  }
  const keywords = stringListField(parsed, 'keywords');
  const sources = stringListField(parsed, 'sources', { inlineOnly: true, quotedMembers: true });
  const related = stringListField(parsed, 'related', { inlineOnly: true, quotedMembers: true });
  const fields = ['title', 'description', 'type', 'status', 'owner', 'created', 'last_updated', 'canonical_entry', 'doc_id', 'when_to_read', 'redirect_to', 'template_usage', 'subject_ref', 'client_ref'];
  const meta = {
    parsed,
    ...Object.fromEntries(fields.map((field) => [field, stringField(parsed, field)])),
    keywords: keywords.valid ? keywords.values : [], keywordsShape: keywords,
    sources: sources.valid ? sources.values : [], sourcesShape: sources,
    related: related.valid ? related.values : [], relatedShape: related,
    duplicateKeys: parsed.duplicateKeys,
  };
  metadataCache.set(filePath, meta);
  return meta;
}

function enumFromMarkdownStandard(field) {
  const standardPath = join(root, 'wiki', '00_meta', 'markdown-standard.md');
  if (!existsSync(standardPath)) { fail(`missing Markdown metadata authority: ${relative(root, standardPath)}`); return new Set(); }
  const text = readFileSync(standardPath, 'utf8');
  const candidates = [...text.matchAll(new RegExp(`^${field}:\\s*["']([^"']+)["']\\s*$`, 'gm'))].map((match) => match[1]);
  const enumLine = candidates.find((candidate) => candidate.includes('|'));
  if (!enumLine) { fail(`Markdown metadata authority has no parseable ${field} enum`); return new Set(); }
  return new Set(enumLine.split('|').map((item) => item.trim()).filter(Boolean));
}
function hasField(meta, field) { return meta.parsed.data.has(field); }
function fieldType(meta, field) {
  const value = meta.parsed.data.get(field);
  if (Array.isArray(value)) return 'array';
  if (value === null) return 'null';
  return typeof value;
}
function requireStringField(meta, field, rel) {
  if (hasField(meta, field) && typeof meta.parsed.data.get(field) !== 'string') fail(`${field} must be a string, not ${fieldType(meta, field)}: ${rel}`);
}
function isIsoDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.valueOf()) && parsed.toISOString().slice(0, 10) === value;
}
function canonicalCandidates(directory) {
  return [join(directory, 'index.md'), join(directory, 'README.md')].filter(existsSync);
}
function canonicalEntry(directory) {
  const candidates = canonicalCandidates(directory);
  return candidates.length === 1 ? candidates[0] : null;
}
function isReadmeOnlyDirectory(directory) {
  return existsSync(join(directory, 'README.md')) && !existsSync(join(directory, 'index.md'));
}
function containsMarkdown(directory) {
  return walk(directory).some((file) => extname(file).toLowerCase() === '.md');
}

function isNumberedDurable(rel) {
  return /(?:^|\/)id-\d{4}-[a-z0-9][a-z0-9-]*\.md$/.test(rel);
}
function isCanonicalKeywordExempt(rel, meta) {
  const parts = rel.split('/');
  return rel.startsWith('raw/')
    || rel.startsWith('wiki/00_meta/logs/')
    || parts.includes('TEMPLATES')
    || meta.type === 'template'
    || meta.type === 'log'
    || meta.type === 'log-summary'
    || meta.type === 'verification-record'
    || meta.type === 'writeback-record';
}
function parseRegistryCanonicalEntries() {
  const registryPath = join(root, 'sub-libraries/registry.json');
  if (!existsSync(registryPath)) return [];
  try {
    const registry = JSON.parse(readFileSync(registryPath, 'utf8'));
    return (Array.isArray(registry.entries) ? registry.entries : [])
      .filter((entry) => entry && typeof entry.path === 'string' && typeof entry.canonical_entry === 'string')
      .map((entry) => relative(root, join(root, entry.path, entry.canonical_entry)).split(sep).join('/'))
      .filter((entry) => !entry.startsWith('../') && entry !== '..');
  } catch {
    return [];
  }
}
function retrievalKeywords(meta) {
  return meta.keywords.filter((keyword) => keyword && keyword !== '—' && keyword !== '-');
}
const semanticPlaceholderPatterns = [
  /^(?:todo|tbd|placeholder|待补|待填写|请填写|未填写|n\/?a|none)$/iu,
  /(?:请|待|这里|在此)(?:填写|补充|说明)/u,
  /说明什么时候(?:应该)?读取/u,
  /(?:检索词|关键词)\s*\d+/u,
  /^词\s*\d+$/u,
];
function isSemanticPlaceholder(value) {
  const text = String(value ?? '').trim();
  return !text || semanticPlaceholderPatterns.some((pattern) => pattern.test(text));
}
function checkTemplateMetadata(filePath, meta) {
  if (meta.type !== 'template') return;
  const rel = relative(root, filePath).split(sep).join('/');
  if (!['creator-compatible', 'manual-copy'].includes(meta.template_usage)) {
    fail(`template_usage must be creator-compatible or manual-copy: ${rel}`);
  }
  if (isSemanticPlaceholder(meta.description)) fail(`template description contains a semantic placeholder: ${rel}`);
  if (isSemanticPlaceholder(meta.when_to_read) || meta.when_to_read.length < 12) fail(`template when_to_read must be a concrete reading condition: ${rel}`);
  if (!meta.keywordsShape.valid || meta.keywords.length < 3 || meta.keywords.length > 8) {
    fail(`template keywords must contain 3-8 concrete retrieval terms: ${rel}`);
  } else {
    for (const keyword of meta.keywords) if (isSemanticPlaceholder(keyword)) fail(`template keyword contains a semantic placeholder: ${rel} -> ${keyword}`);
  }
  const hasTargetKind = hasField(meta, 'template_target_kind');
  const hasTargetType = hasField(meta, 'template_target_type');
  if (meta.template_usage === 'creator-compatible' && (!hasTargetKind || !hasTargetType)) fail(`creator-compatible template must declare both template_target_kind and template_target_type: ${rel}`);
  if (meta.template_usage === 'manual-copy' && (hasTargetKind || hasTargetType)) fail(`manual-copy template must not declare creator target fields: ${rel}`);
}
function checkConversationFacets(filePath, meta) {
  if (meta.type !== 'conversation-source') return;
  const rel = relative(root, filePath).split(sep).join('/');
  const policies = [
    ['subject_ref', /^SUBJ-[A-Z0-9][A-Z0-9-]{2,31}$/],
    ['client_ref', /^CLIENT-[A-Z0-9][A-Z0-9-]{2,31}$/],
  ];
  for (const [field, pattern] of policies) {
    if (!hasField(meta, field)) {
      fail(`conversation-source must explicitly declare ${field}; an empty string is allowed: ${rel}`);
      continue;
    }
    requireStringField(meta, field, rel);
    const value = meta[field];
    if (value && !pattern.test(value)) fail(`${field} must be empty or a de-identified ${field === 'subject_ref' ? 'SUBJ' : 'CLIENT'} reference: ${rel}`);
  }
}
function isNavigableDirectory(directory) {
  const name = directory.split(sep).pop();
  if (!name || ignoredDirs.has(name) || name.startsWith('.')) return false;
  return true;
}
function isExternal(target) {
  return target.startsWith('#') || target.startsWith('//') || /^(?:https?:|mailto:|tel:|data:|obsidian:)/i.test(target);
}
function portableLocalTarget(filePath, raw, label) {
  if (!raw || isExternal(raw)) return null;
  const withoutQuery = raw.split('#', 1)[0].split('?', 1)[0];
  if (!withoutQuery || withoutQuery.startsWith('/')) {
    fail(`${relative(root, filePath)} has non-portable or empty local ${label}: ${raw}`);
    return null;
  }
  let decoded;
  try { decoded = decodeURIComponent(withoutQuery); }
  catch (error) {
    fail(`${relative(root, filePath)} has unreadable local ${label}: ${raw} (${error.message})`);
    return null;
  }
  return decoded;
}
function isHistoricalReferenceOwner(meta) {
  return meta?.status === 'Archived' || ['redirect', 'log', 'log-summary'].includes(meta?.type);
}
function redirectMeta(targetPath) {
  if (!existsSync(targetPath) || extname(targetPath).toLowerCase() !== '.md') return null;
  const meta = parseFrontMatter(targetPath);
  return meta?.type === 'redirect' ? meta : null;
}
function rejectActiveRedirectReference(filePath, ownerMeta, targetPath, raw, label) {
  if (isHistoricalReferenceOwner(ownerMeta)) return;
  const redirect = redirectMeta(targetPath);
  if (!redirect) return;
  fail(`${label} targets type: redirect legacy page: ${relative(root, filePath)} -> ${raw}; use ${redirect.redirect_to || 'the ID canonical target'}`);
}
function checkMarkdownLinks(filePath, content, ownerMeta) {
  const parsed = extractMarkdownLinks(content);
  for (const error of parsed.errors) fail(`${relative(root, filePath)} has invalid Markdown link syntax: ${error.message}${error.line ? ` (line ${error.line})` : ''}`);
  for (const link of parsed.links) {
    const target = portableLocalTarget(filePath, link.target, 'link');
    if (!target) continue;
    const resolved = resolve(dirname(filePath), target);
    if (!resolved.startsWith(`${root}${sep}`) && resolved !== root) fail(`${relative(root, filePath)} link escapes root: ${link.target}`);
    else if (!existsSync(resolved)) fail(`${relative(root, filePath)} links to missing path: ${link.target}`);
    else rejectActiveRedirectReference(filePath, ownerMeta, resolved, link.target, 'active Markdown link');
  }
}
function checkIndexManualDescendantLinks(filePath, content) {
  if (filePath.split(sep).pop() !== 'index.md') return;
  const manual = content.replace(/<!-- INDEX:BEGIN generated by scripts\/sync-indexes\.mjs; do not hand-edit -->[\s\S]*?<!-- INDEX:END -->/g, '');
  const parsed = extractMarkdownLinks(manual);
  for (const link of parsed.links) {
    const target = portableLocalTarget(filePath, link.target, 'index link');
    if (!target || !/\.md$/i.test(target)) continue;
    const relTarget = relative(dirname(filePath), resolve(dirname(filePath), target));
    if (!relTarget || relTarget === '.' || relTarget.startsWith(`..${sep}`) || relTarget === '..') continue;
    const parts = relTarget.split(sep);
    const isDirectFile = parts.length === 1;
    const isDirectChildCanonical = parts.length === 2 && ['index.md', 'README.md'].includes(parts[1]);
    if (!isDirectFile && !isDirectChildCanonical) {
      fail(`index manual area recursively links to non-direct descendant: ${relative(root, filePath)} -> ${link.target}`);
    }
  }
}
function checkFrontMatterReferencePaths(filePath, meta, field) {
  const shape = field === 'sources' ? meta.sourcesShape : meta.relatedShape;
  if (!shape.valid) return;
  for (const item of meta[field]) {
    const targetText = item.split('#')[0].split('?')[0];
    const markdownPath = /\.md$/i.test(targetText);
    if (field === 'sources' && !markdownPath) continue;
    if (/^(https?:|mailto:|data:|tel:)/i.test(item) || item.startsWith('/')) {
      if (field === 'related') fail(`related must contain portable repository-relative paths: ${relative(root, filePath)} -> ${item}`);
      continue;
    }
    const rootRelative = /^(?:wiki|raw|sub-libraries)\//.test(targetText);
    const resolved = resolve(rootRelative ? root : dirname(filePath), targetText);
    if ((!resolved.startsWith(`${root}${sep}`) && resolved !== root) || !existsSync(resolved)) {
      if (field === 'related') fail(`related path is missing or escapes root: ${relative(root, filePath)} -> ${item}`);
      continue;
    }
    rejectActiveRedirectReference(filePath, meta, resolved, item, `${field} path`);
  }
}
function checkRegistryPaths(filePath, content, meta) {
  if (filePath.split(sep).pop() !== 'source-registry.md' || isHistoricalReferenceOwner(meta)) return;
  for (const match of content.matchAll(/`([^`\n]+\.md(?:[?#][^`\n]*)?)`/g)) {
    const raw = match[1];
    const targetText = raw.split('#')[0].split('?')[0];
    const rootRelative = /^(?:wiki|raw|sub-libraries)\//.test(targetText);
    const resolved = resolve(rootRelative ? root : dirname(filePath), targetText);
    if (!resolved.startsWith(`${root}${sep}`) && resolved !== root) continue;
    if (!existsSync(resolved)) continue;
    rejectActiveRedirectReference(filePath, meta, resolved, raw, 'registry path');
  }
}
function checkIndexFreshness(filePath, content, meta) {
  if (filePath.split(sep).pop() !== 'index.md' || !isIsoDate(meta.last_updated)) return;
  const generated = content.match(/<!-- INDEX:BEGIN generated by scripts\/sync-indexes\.mjs; do not hand-edit -->([\s\S]*?)<!-- INDEX:END -->/)?.[1] ?? '';
  const dates = [];
  for (const link of extractMarkdownLinks(generated).links) {
    const targetText = link.target.split('#')[0].split('?')[0];
    if (!/\.md$/i.test(targetText)) continue;
    const target = resolve(dirname(filePath), targetText);
    if (!existsSync(target)) continue;
    const targetMeta = parseFrontMatter(target);
    if (targetMeta && isIsoDate(targetMeta.last_updated)) dates.push({ date: targetMeta.last_updated, path: relative(root, target) });
  }
  dates.sort((a, b) => b.date.localeCompare(a.date));
  if (dates[0] && meta.last_updated < dates[0].date) {
    fail(`index last_updated ${meta.last_updated} is older than direct entry ${dates[0].date}: ${relative(root, filePath)} <- ${dates[0].path}`);
  }
}

const genericDescriptionPatterns = [
  /^(?:这是|本页是|该页是)?(?:一个)?关于.+(?:的)?(?:文档|页面|资料)(?:，|。|$)/iu,
  /(?:页面说明|常规资料|基本页面|相关内容|资料介绍|内容介绍)/iu,
];
const descriptionTaskPattern = /(?:定义|规定|说明|解释|提供|指导|记录|登记|连接|映射|管理|追踪|核对|判断|定位|选择|执行|复盘|查找|导航|入口|帮助|用于|避免|确保|支持|生成|提炼|区分|统一)/iu;
const descriptionBoundaryPattern = /(?:不|仅|只|边界|范围|适用|例外|公开|私有|当前|状态|规则|规范|合同|待验证|未验证|不替代|不覆盖|不包含|不得|不能)/iu;
function descriptionFacets(description) {
  const generic = genericDescriptionPatterns.some((pattern) => pattern.test(description));
  const specific = description
    .replace(/(?:这是一个|本页是|该页是|关于|文档|页面|资料|用来|用于|介绍|相关内容|基本|常规|说明|的|和|一个)/gu, '')
    .replace(/[^\p{L}\p{N}]+/gu, '');
  return {
    generic,
    object: !generic && specific.length >= 8,
    task: descriptionTaskPattern.test(description),
    boundary: descriptionBoundaryPattern.test(description),
  };
}
function checkDescriptionQuality(rel, meta) {
  const description = meta.description;
  if (!description) return;
  const facets = descriptionFacets(description);
  if (facets.generic) {
    fail(`generic or semantically empty description: ${rel}`);
    return;
  }
  const retrievalCritical = isNumberedDurable(rel)
    || (canonicalKeywordEntries.has(rel) && !isCanonicalKeywordExempt(rel, meta));
  if (!retrievalCritical) return;
  const missing = ['object', 'task', 'boundary'].filter((field) => !facets[field]);
  if (!missing.length) return;
  const message = `retrieval-critical description missing ${missing.join('/')} facet(s): ${rel}`;
  if (strictMode) fail(message); else warn(message);
}

const allFiles = walk(root);
const markdownFiles = allFiles.filter((file) => extname(file).toLowerCase() === '.md');
const canonicalKeywordEntries = new Set([
  ...markdownFiles
    .filter((file) => {
      const rel = relative(root, file).split(sep).join('/');
      return rel.startsWith('wiki/') && canonicalEntry(dirname(file)) === file;
    })
    .map((file) => relative(root, file).split(sep).join('/')),
  ...(existsSync(join(root, 'sub-libraries', 'README.md')) ? ['sub-libraries/README.md'] : []),
  ...parseRegistryCanonicalEntries(),
]);
const allowedTypes = enumFromMarkdownStandard('type');
const allowedStatuses = enumFromMarkdownStandard('status');
const allowedOwners = enumFromMarkdownStandard('owner');
const requiredFields = ['title', 'description', 'type', 'status', 'owner', 'created', 'last_updated', 'sources', 'related'];
const requiredStringFields = ['title', 'description', 'type', 'status', 'owner', 'created', 'last_updated'];
const allDirs = [...new Set(allFiles.map((file) => dirname(file)))];
for (const directory of allDirs) {
  if (!isReadmeOnlyDirectory(directory)) continue;
  const relDir = relative(root, directory) || '.';
  const readmePath = join(directory, 'README.md');
  const meta = parseFrontMatter(readmePath);
  if (!meta) fail(`README-only canonical entry has no metadata block: ${relDir}/README.md`);
  else if (meta.canonical_entry !== 'README.md') fail(`README-only canonical entry must declare canonical_entry: "README.md": ${relDir}/README.md`);
}
for (const filePath of markdownFiles) {
  const meta = parseFrontMatter(filePath);
  const rel = relative(root, filePath);
  if (!meta) fail(`missing front matter or README metadata block: ${rel}`);
  else {
    for (const field of requiredFields) if (!hasField(meta, field)) fail(`missing required metadata field ${field}: ${rel}`);
    for (const field of requiredStringFields) requireStringField(meta, field, rel);
    for (const key of meta.duplicateKeys) fail(`duplicate metadata key ${key}: ${rel}`);
    if (!meta.sourcesShape.valid) fail(`sources must be an inline array of unique non-empty quoted strings: ${rel} (${meta.sourcesShape.reason})`);
    if (!meta.relatedShape.valid) fail(`related must be an inline array of unique non-empty quoted strings: ${rel} (${meta.relatedShape.reason})`);
    checkFrontMatterReferencePaths(filePath, meta, 'sources');
    checkFrontMatterReferencePaths(filePath, meta, 'related');
    if (!meta.title) fail(`missing title: ${rel}`);
    if (!meta.description) fail(`missing description: ${rel}`);
    else if (meta.description.length < 20) warn(`short description (<20 chars): ${rel}`);
    checkDescriptionQuality(rel, meta);
    checkTemplateMetadata(filePath, meta);
    checkConversationFacets(filePath, meta);
    if (!meta.type) fail(`missing type: ${rel}`);
    else if (allowedTypes.size && !allowedTypes.has(meta.type)) fail(`unknown type ${meta.type}: ${rel}; register it in wiki/00_meta/markdown-standard.md first`);
    if (!meta.status) fail(`missing status: ${rel}`);
    else if (allowedStatuses.size && !allowedStatuses.has(meta.status)) fail(`unknown status ${meta.status}: ${rel}`);
    if (!meta.owner) fail(`missing owner: ${rel}`);
    else if (allowedOwners.size && !allowedOwners.has(meta.owner)) fail(`unknown owner ${meta.owner}: ${rel}`);
    if (!(meta.type === 'template' && meta.created === 'YYYY-MM-DD') && !isIsoDate(meta.created)) fail(`created must be a valid YYYY-MM-DD date: ${rel}`);
    if (!(meta.type === 'template' && meta.last_updated === 'YYYY-MM-DD') && !isIsoDate(meta.last_updated)) fail(`last_updated must be a valid YYYY-MM-DD date: ${rel}`);
    if (isNumberedDurable(rel)) {
      const expected = `ID-${rel.match(/(?:^|\/)id-(\d{4})-/)[1]}`;
      if (meta.doc_id !== expected) fail(`numbered durable page doc_id must be ${expected}: ${rel}`);
      if (meta.keywords.length < 3 || meta.keywords.length > 8) fail(`numbered durable page keywords must contain 3-8 retrieval terms: ${rel}`);
      if (!meta.when_to_read) fail(`numbered durable page missing when_to_read: ${rel}`);
    }
    if (canonicalKeywordEntries.has(rel) && !isCanonicalKeywordExempt(rel, meta)) {
      const keywordCount = retrievalKeywords(meta).length;
      if (keywordCount < 3 || keywordCount > 8) {
        const message = `canonical entry keywords must contain 3-8 retrieval terms: ${rel}`;
        if (strictMode) fail(message); else warn(message);
      }
      if (rel.startsWith('wiki/') && !meta.when_to_read) {
        const message = `wiki canonical entry missing when_to_read: ${rel}`;
        if (strictMode) fail(message); else warn(message);
      }
    }
  }
  const content = readFileSync(filePath, 'utf8');
  checkMarkdownLinks(filePath, content, meta);
  if (meta) {
    checkRegistryPaths(filePath, content, meta);
    checkIndexManualDescendantLinks(filePath, content);
    checkIndexFreshness(filePath, content, meta);
  }
  if (/\/(?:Users|var\/folders|private\/var\/folders|tmp)\//.test(content)) fail(`machine-local path pattern found: ${rel}`);
}

for (const directory of allDirs) {
  const candidates = canonicalCandidates(directory);
  if (candidates.length > 1) {
    fail(`duplicate canonical entry in ${relative(root, directory) || '.'}: README.md and index.md; exactly one canonical entry is allowed`);
    continue;
  }
  if (candidates.length !== 1) continue;
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const child = join(directory, entry.name);
    if (!entry.isDirectory() || !isNavigableDirectory(child) || !containsMarkdown(child)) continue;
    const childCandidates = canonicalCandidates(child);
    if (childCandidates.length === 1) continue;
    const message = childCandidates.length === 0
      ? `navigable directory has no canonical entry: ${relative(root, child)}`
      : `navigable directory has multiple canonical entries: ${relative(root, child)} (README.md and index.md)`;
    if (strictMode || childCandidates.length > 1) fail(message); else warn(message);
  }
}

const syncScript = join(root, 'scripts/sync-indexes.mjs');
if (!existsSync(syncScript)) fail('missing scripts/sync-indexes.mjs');
else {
  const result = spawnSync(process.execPath, [syncScript, '--check'], { cwd: root, encoding: 'utf8' });
  if (result.status !== 0) fail(`generated index blocks are stale: ${(result.stderr || result.stdout || '').trim().split('\n').slice(0, 12).join(' | ')}`);
}

if (warnings.length) {
  console.log(`INDEX_WARNINGS: ${warnings.length}`);
  for (const message of warnings) console.log(`WARN: ${message}`);
}
if (failures.length) {
  console.error(`INDEX_FAILURES: ${failures.length}`);
  for (const message of failures) console.error(`BLOCK: ${message}`);
  process.exitCode = 1;
} else {
  console.log(`INDEX_VALIDATION_PASS: markdown=${markdownFiles.length}`);
  if (checkOnly) console.log('MODE: check-only');
}
