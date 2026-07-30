#!/usr/bin/env node
/**
 * Create one Markdown document from an explicit DOCUMENT_TEMPLATE payload.
 * Only the first/front template front matter is parsed as template metadata;
 * fenced examples and body text can never override the generated document.
 */
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { basename, dirname, extname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
const get = (name, fallback = '') => {
  const i = args.indexOf(`--${name}`);
  return i === -1 ? fallback : args[i + 1] || fallback;
};
const has = (name) => args.includes(`--${name}`);

if (has('help') || !args.length) {
  console.log(`Usage: node scripts/create-document.mjs --dir <directory> --slug <slug> --title <title> --description <description> [--template <path>] [--type <type>] [--when-to-read <condition>] [--keywords "term1,term2,term3"] [--source-id SRC-YYYYMMDD-####] [--raw-path <path>] [--date YYYY-MM-DD] [--dry-run]\n\nTemplates must declare template_target_kind/template_target_type in their real front matter and contain explicit DOCUMENT_TEMPLATE_START/END markers.`);
  process.exit(0);
}

const dirArg = get('dir');
const slug = get('slug').toLowerCase();
const title = get('title');
const description = get('description');
const templateArg = get('template', 'wiki/_templates/page.md');
const requestedType = get('type');
const requestedSourceId = get('source-id');
const rawPathArg = get('raw-path');
const whenToRead = get('when-to-read');
const keywordsArg = get('keywords');
const requestedDate = get('date');
if (!dirArg || !slug || !title || !description) {
  console.error('BLOCK: --dir, --slug, --title and --description are required');
  process.exit(1);
}
if (!/^[a-z0-9][a-z0-9-]*$/.test(slug)) {
  console.error('BLOCK: --slug must use lowercase letters, numbers and hyphens');
  process.exit(1);
}
if (description.length < 20) {
  console.error('BLOCK: --description must be a human-readable sentence of at least 20 characters');
  process.exit(1);
}

const normalizedDirArg = dirArg.replaceAll('\\', '/').replace(/^\.\//, '').replace(/\/+$/, '');
const dir = resolve(root, normalizedDirArg);
const template = resolve(root, templateArg);
const dirRelative = relative(root, dir).replaceAll('\\', '/');
const templateRelative = relative(root, template).replaceAll('\\', '/');
function insideRoot(path) { return path === root || path.startsWith(`${root}${sep}`); }
if (!insideRoot(dir) || !insideRoot(template)) {
  console.error('BLOCK: paths must stay inside the repository');
  process.exit(1);
}
if (!existsSync(template)) {
  console.error(`BLOCK: template not found: ${templateRelative}`);
  process.exit(1);
}

function parseFrontMatter(content, label) {
  if (!content.startsWith('---\n')) throw new Error(`${label}: missing real front matter at byte 0`);
  const end = content.indexOf('\n---', 4);
  if (end < 0) throw new Error(`${label}: unclosed front matter`);
  const body = content.slice(4, end);
  const fields = new Map();
  for (const line of body.split('\n')) {
    const match = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
    if (!match) continue;
    if (fields.has(match[1])) throw new Error(`${label}: duplicate front matter key ${match[1]}`);
    fields.set(match[1], match[2].trim());
  }
  const value = (field) => {
    const raw = fields.get(field) ?? '';
    return raw.match(/^["'](.*)["']$/)?.[1]?.trim() ?? raw.trim();
  };
  return { fields, value, end: end + 4 };
}

function inlineArray(raw) {
  const match = raw?.match(/^\[(.*)\]$/);
  if (!match) return null;
  if (!match[1].trim()) return [];
  return [...match[1].matchAll(/["']([^"']*)["']/g)].map((item) => item[1]);
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
function parseKeywords(value) {
  const items = value.split(',').map((item) => item.trim()).filter(Boolean);
  if (items.length < 3 || items.length > 8) throw new Error('--keywords must contain 3-8 comma-separated retrieval terms');
  if (new Set(items).size !== items.length) throw new Error('--keywords must not contain duplicate retrieval terms');
  for (const item of items) if (isSemanticPlaceholder(item)) throw new Error(`--keywords contains a semantic placeholder: ${item}`);
  return items;
}

const templateContent = readFileSync(template, 'utf8');
let templateMeta;
try { templateMeta = parseFrontMatter(templateContent, templateRelative); }
catch (error) { console.error(`BLOCK: ${error.message}`); process.exit(1); }
const templateUsage = templateMeta.value('template_usage');
if (templateUsage !== 'creator-compatible') {
  console.error(`BLOCK: ${templateRelative} is ${templateUsage || 'unclassified'}; create-document accepts only template_usage: creator-compatible`);
  process.exit(1);
}
for (const field of ['description', 'when_to_read']) {
  if (isSemanticPlaceholder(templateMeta.value(field))) {
    console.error(`BLOCK: ${templateRelative} has a semantic placeholder in template metadata ${field}`);
    process.exit(1);
  }
}
const templateKeywords = inlineArray(templateMeta.fields.get('keywords'));
if (!templateKeywords || templateKeywords.length < 3 || templateKeywords.length > 8 || templateKeywords.some(isSemanticPlaceholder)) {
  console.error(`BLOCK: ${templateRelative} template metadata keywords must contain 3-8 concrete retrieval terms`);
  process.exit(1);
}
const targetKind = templateMeta.value('template_target_kind');
const declaredTargetType = templateMeta.value('template_target_type');
const targetType = requestedType || declaredTargetType;
if (!targetKind || !declaredTargetType || !targetType) {
  console.error(`BLOCK: ${templateRelative} must declare template_target_kind and template_target_type in its real front matter`);
  process.exit(1);
}
if (requestedType && requestedType !== declaredTargetType) {
  console.error(`BLOCK: --type ${requestedType} conflicts with template_target_type ${declaredTargetType}`);
  process.exit(1);
}
const startMarker = '<!-- DOCUMENT_TEMPLATE_START -->';
const endMarker = '<!-- DOCUMENT_TEMPLATE_END -->';
const start = templateContent.indexOf(startMarker, templateMeta.end);
const end = templateContent.indexOf(endMarker, start + startMarker.length);
if (start < 0 || end < 0 || end <= start) {
  console.error(`BLOCK: ${templateRelative} must contain one explicit DOCUMENT_TEMPLATE_START/END payload`);
  process.exit(1);
}
if (templateContent.indexOf(startMarker, start + startMarker.length) >= 0 || templateContent.indexOf(endMarker, end + endMarker.length) >= 0) {
  console.error(`BLOCK: ${templateRelative} contains multiple document template payload markers`);
  process.exit(1);
}
const payload = templateContent.slice(start + startMarker.length, end).trim();

function manifestList(filePath, field) {
  if (!existsSync(filePath)) return [];
  const content = readFileSync(filePath, 'utf8');
  const line = content.match(new RegExp(`^${field}:\\s*\\[([^\\]]*)\\]\\s*$`, 'm'))?.[1];
  return line ? line.split(',').map((item) => item.trim().replace(/^['"]|['"]$/g, '')).filter(Boolean) : [];
}

const motherDurableRoots = ['wiki/20_concepts', 'wiki/30_playbooks', 'wiki/40_business', 'wiki/50_channels', 'wiki/60_clients', 'wiki/70_competitors', 'wiki/80_metrics', 'wiki/90_outputs'];
const subLibraryMatch = dirRelative.match(/^sub-libraries\/([^/]+)(?:\/.*)?$/);
const isSubLibrary = Boolean(subLibraryMatch);
const subLibraryRoot = isSubLibrary ? `sub-libraries/${subLibraryMatch[1]}` : '';
const subLibraryDurableRoots = isSubLibrary ? manifestList(resolve(root, subLibraryRoot, 'MANIFEST.md'), 'durable_roots') : [];
const durableTarget = targetKind === 'durable';
const sourceTarget = targetKind === 'source-note';
const rawTarget = targetKind === 'raw-source';
let generatedKeywords = [];
if (durableTarget) {
  if (isSemanticPlaceholder(whenToRead) || whenToRead.length < 12) {
    console.error('BLOCK: durable creation requires --when-to-read with a concrete reading condition');
    process.exit(1);
  }
  try { generatedKeywords = parseKeywords(keywordsArg); }
  catch (error) { console.error(`BLOCK: ${error.message}`); process.exit(1); }
}
if (![durableTarget, sourceTarget, rawTarget].some(Boolean)) {
  console.error(`BLOCK: unsupported template_target_kind ${targetKind}`);
  process.exit(1);
}
if (isSubLibrary) {
  if (!durableTarget) {
    console.error('BLOCK: sub-library create-document currently supports durable targets only');
    process.exit(1);
  }
  if (!templateRelative.startsWith(`${subLibraryRoot}/`)) {
    console.error(`BLOCK: sub-library durable pages must use a template inside the same sub-library: ${templateRelative}`);
    process.exit(1);
  }
  const insideSubLibrary = dirRelative.slice(`${subLibraryRoot}/`.length);
  if (!subLibraryDurableRoots.some((prefix) => insideSubLibrary === prefix || insideSubLibrary.startsWith(`${prefix}/`))) {
    console.error(`BLOCK: --dir inside a sub-library must be under one of its MANIFEST.md durable_roots: ${subLibraryDurableRoots.join(', ') || 'missing'}`);
    process.exit(1);
  }
} else if (durableTarget && !motherDurableRoots.some((prefix) => dirRelative === prefix || dirRelative.startsWith(`${prefix}/`))) {
  console.error('BLOCK: durable --dir must be inside a declared mother durable root');
  process.exit(1);
} else if (sourceTarget && dirRelative !== 'wiki/10_sources') {
  console.error('BLOCK: source-note templates must target wiki/10_sources');
  process.exit(1);
} else if (rawTarget && dirRelative !== 'raw/10_conversations') {
  console.error('BLOCK: raw-source templates must target raw/10_conversations');
  process.exit(1);
}

const ignoredNames = new Set(['.git', '.obsidian', 'node_modules', 'dist', '.cache', 'runtime', 'customer-runtime', 'credentials', 'secrets', '.secrets', 'private', 'workspace']);
function walk(current) {
  if (!existsSync(current)) return [];
  const result = [];
  for (const entry of readdirSync(current, { withFileTypes: true })) {
    if (ignoredNames.has(entry.name)) continue;
    const target = join(current, entry.name);
    if (entry.isDirectory()) result.push(...walk(target));
    else if (extname(entry.name).toLowerCase() === '.md') result.push(target);
  }
  return result;
}
const durableScopeDirs = isSubLibrary
  ? subLibraryDurableRoots.map((durableRoot) => resolve(root, subLibraryRoot, durableRoot))
  : motherDurableRoots.map((durableRoot) => resolve(root, durableRoot));
const ids = durableTarget ? durableScopeDirs.flatMap((scopeDir) => walk(scopeDir)).flatMap((file) => file.split('/').pop().match(/^id-(\d{4})-/)?.[1] ?? []).map(Number) : [];
const nextNumber = (ids.length ? Math.max(...ids) : 0) + 1;
if (durableTarget && nextNumber > 9999) {
  console.error(`BLOCK: four-digit document ID space is exhausted for ${isSubLibrary ? subLibraryRoot : 'mother durable roots'}; define a migration before creating another durable page`);
  process.exit(1);
}
const nextId = String(nextNumber).padStart(4, '0');
const today = requestedDate || new Date().toISOString().slice(0, 10);
if (!/^\d{4}-\d{2}-\d{2}$/.test(today) || Number.isNaN(new Date(`${today}T00:00:00Z`).valueOf()) || new Date(`${today}T00:00:00Z`).toISOString().slice(0, 10) !== today) {
  console.error('BLOCK: --date must be a valid YYYY-MM-DD date');
  process.exit(1);
}
const compactToday = today.replaceAll('-', '');
function nextSourceId() {
  if (requestedSourceId) {
    if (!/^SRC-\d{8}-\d{4}$/.test(requestedSourceId)) throw new Error('--source-id must use SRC-YYYYMMDD-####');
    return requestedSourceId;
  }
  const pattern = new RegExp(`SRC-${compactToday}-(\\d{4})`, 'g');
  const numbers = walk(root).flatMap((file) => [...readFileSync(file, 'utf8').matchAll(pattern)].map((match) => Number(match[1])));
  return `SRC-${compactToday}-${String((numbers.length ? Math.max(...numbers) : 0) + 1).padStart(4, '0')}`;
}
let sourceId = '';
try { sourceId = sourceTarget || rawTarget || requestedSourceId ? nextSourceId() : ''; }
catch (error) { console.error(`BLOCK: ${error.message}`); process.exit(1); }
if (sourceTarget && !rawPathArg) {
  console.error('BLOCK: source-note creation requires --raw-path pointing to its raw source');
  process.exit(1);
}
if (rawPathArg) {
  const normalizedRawPath = rawPathArg.replaceAll('\\', '/').replace(/^\.\//, '');
  const rawResolved = resolve(root, normalizedRawPath);
  if (!insideRoot(rawResolved) || !existsSync(rawResolved)) {
    console.error(`BLOCK: --raw-path must exist inside the repository: ${rawPathArg}`);
    process.exit(1);
  }
  if (!normalizedRawPath.startsWith('raw/') || /(?:^|\/)index\.md$/i.test(normalizedRawPath) || normalizedRawPath.startsWith('raw/_templates/')) {
    console.error(`BLOCK: --raw-path must point to a concrete source record under raw/, not ${rawPathArg}`);
    process.exit(1);
  }
  let rawMeta;
  try { rawMeta = parseFrontMatter(readFileSync(rawResolved, 'utf8'), normalizedRawPath); }
  catch (error) { console.error(`BLOCK: --raw-path is not a valid front-matter source record: ${error.message}`); process.exit(1); }
  if (sourceTarget && rawMeta.value('source_id') !== sourceId) {
    console.error(`BLOCK: --raw-path source_id ${rawMeta.value('source_id') || 'missing'} does not equal requested ${sourceId}`);
    process.exit(1);
  }
}

let target;
let docId = '';
if (durableTarget) {
  docId = `ID-${nextId}`;
  target = join(dir, `id-${nextId}-${slug}.md`);
} else if (sourceTarget) target = join(dir, `${sourceId}.md`);
else {
  const match = sourceId.match(/^SRC-(\d{8})-(\d{4})$/);
  target = join(dir, `src-${match[1]}-${match[2]}-${slug}.md`);
}
if (existsSync(target)) {
  console.error(`BLOCK: target already exists: ${relative(root, target)}`);
  process.exit(1);
}

const yamlString = (value) => `"${String(value).replaceAll('\\', '\\\\').replaceAll('"', '\\"').replaceAll('\n', ' ')}"`;
const replacements = new Map([
  ['doc_id', docId],
  ['source_id', sourceId],
  ['title', title],
  ['description', description],
  ['when_to_read', whenToRead],
  ['keywords', generatedKeywords.length ? `[${generatedKeywords.map(yamlString).join(', ')}]` : '[]'],
  ['type', targetType],
  ['today', today],
  ['captured_at', `${today}T00:00:00+08:00`],
  ['raw_path', rawPathArg.replaceAll('\\', '/')],
  ['sources', sourceId && durableTarget ? `[${yamlString(sourceId)}]` : '[]'],
]);
let content = payload;
for (const [key, value] of replacements) content = content.replaceAll(`{{${key}}}`, value);
if (/\{\{[A-Za-z0-9_-]+\}\}/.test(content)) {
  console.error(`BLOCK: unresolved structured template placeholder in ${templateRelative}`);
  process.exit(1);
}

const validationFailures = [];
let generated;
try { generated = parseFrontMatter(content, relative(root, target).replaceAll('\\', '/')); }
catch (error) { validationFailures.push(error.message); }
if (generated) {
  const required = ['title', 'description', 'type', 'status', 'owner', 'created', 'last_updated', 'sources', 'related', ...(durableTarget ? ['when_to_read', 'keywords'] : [])];
  for (const field of required) if (!generated.fields.has(field) || (field !== 'sources' && field !== 'related' && !generated.value(field))) validationFailures.push(`missing required field ${field}`);
  if (generated.value('type') !== targetType) validationFailures.push(`type ${generated.value('type')} does not match template_target_type ${targetType}`);
  if (!new Set(['Seed', 'Draft', 'Working', 'Verified', 'Canonical', 'Stale', 'Archived']).has(generated.value('status'))) validationFailures.push(`invalid status ${generated.value('status')}`);
  for (const field of ['sources', 'related']) if (inlineArray(generated.fields.get(field)) === null) validationFailures.push(`${field} must be an inline quoted array`);
  if (isSemanticPlaceholder(generated.value('description'))) validationFailures.push('description contains a semantic placeholder');
  if (durableTarget) {
    if (generated.value('doc_id') !== docId) validationFailures.push(`doc_id must equal ${docId}`);
    if (!basename(target).startsWith(`id-${nextId}-`)) validationFailures.push('durable filename/doc_id mismatch');
    if (isSemanticPlaceholder(generated.value('when_to_read')) || generated.value('when_to_read').length < 12) validationFailures.push('when_to_read must explain when the durable page should be read');
    const keywords = inlineArray(generated.fields.get('keywords'));
    if (!keywords || keywords.length < 3 || keywords.length > 8 || keywords.some(isSemanticPlaceholder)) validationFailures.push('keywords must be an inline quoted array with 3-8 concrete values');
  } else if (generated.fields.has('doc_id')) validationFailures.push(`${targetKind} records must not claim a durable doc_id`);
  if ((sourceTarget || rawTarget) && generated.value('source_id') !== sourceId) validationFailures.push(`source_id must equal ${sourceId}`);
  if (rawTarget) {
    for (const field of ['source_kind', 'synthetic', 'consent_status', 'ingestion_status', 'visibility', 'sensitivity', 'redaction_status']) if (!generated.value(field)) validationFailures.push(`raw source missing ${field}`);
    for (const [field, pattern] of [['subject_ref', /^(?:|SUBJ-[A-Z0-9][A-Z0-9-]{2,31})$/], ['client_ref', /^(?:|CLIENT-[A-Z0-9][A-Z0-9-]{2,31})$/]]) {
      if (!generated.fields.has(field)) validationFailures.push(`raw source missing ${field}`);
      else if (!pattern.test(generated.value(field))) validationFailures.push(`${field} must be empty or a de-identified uppercase reference`);
    }
    if (!new Set(['inbox', 'classified', 'registered', 'extracted', 'linked', 'ingested', 'derived', 'verified', 'archived']).has(generated.value('ingestion_status'))) validationFailures.push(`unknown raw ingestion_status ${generated.value('ingestion_status')}`);
  }
  const related = inlineArray(generated.fields.get('related')) ?? [];
  for (const link of related) {
    if (/^(?:https?:|mailto:|#)/.test(link)) continue;
    const linked = resolve(dirname(target), link.split('#')[0]);
    if (!insideRoot(linked) || !existsSync(linked)) validationFailures.push(`related path does not resolve: ${link}`);
  }
}
if (validationFailures.length) {
  for (const failure of validationFailures) console.error(`BLOCK: generated document validation failed: ${failure}`);
  process.exit(1);
}

const targetRel = relative(root, target).replaceAll('\\', '/');
console.log(`VALIDATED: ${targetRel} type=${targetType} kind=${targetKind}`);
if (has('dry-run')) console.log(`DRY_RUN: ${targetRel}\n\n${content}`);
else {
  mkdirSync(dir, { recursive: true });
  writeFileSync(target, `${content.trim()}\n`);
  console.log(`CREATED: ${targetRel} (${isSubLibrary ? subLibraryRoot : 'mother'})`);
  console.log('NEXT: update the source/derived bindings, then run the scope validators before treating the document as complete.');
}
