#!/usr/bin/env node
import assert from 'node:assert/strict';
import { cpSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { parseFrontMatterText, stringField, stringListField } from '../lib/markdown-front-matter.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const sourceRoot = resolve(here, '../..');
const tempRoots = [];

function page({ title, description, type = 'page', status = 'Working', sources = '[]', related = '[]', extra = '', body = '' }) {
  return `---\ntitle: ${JSON.stringify(title)}\ndescription: ${JSON.stringify(description)}\ntype: ${JSON.stringify(type)}\nstatus: ${JSON.stringify(status)}\nowner: "AI"\ncreated: "2026-07-29"\nlast_updated: "2026-07-29"\nsources: ${sources}\nrelated: ${related}\n${extra}---\n# ${title}\n\n${body}\n`;
}

function write(root, rel, content) {
  const path = join(root, rel);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content);
}

function run(root, script, args = []) {
  return spawnSync(process.execPath, [join(root, script), ...args], { cwd: root, encoding: 'utf8' });
}

function output(result) { return `${result.stdout ?? ''}${result.stderr ?? ''}`; }
function accept(result, marker, label) {
  assert.equal(result.status, 0, `${label} unexpectedly failed\n${output(result)}`);
  assert.match(output(result), marker, `${label} omitted proof marker`);
}
function reject(result, marker, label) {
  assert.notEqual(result.status, 0, `${label} accepted the attack\n${output(result)}`);
  assert.match(output(result), marker, `${label} failed for an unrelated reason\n${output(result)}`);
}

function fixture() {
  const root = mkdtempSync(join(tmpdir(), '701-g3-attacks.'));
  tempRoots.push(root);
  for (const rel of ['scripts/sync-indexes.mjs', 'scripts/validate-indexes.mjs', 'scripts/validate-links.mjs', 'scripts/validate-document-ids.mjs', 'scripts/lib/markdown-front-matter.mjs', 'scripts/lib/markdown-links.mjs']) {
    const target = join(root, rel);
    mkdirSync(dirname(target), { recursive: true });
    cpSync(join(sourceRoot, rel), target);
  }
  write(root, 'wiki/index.md', page({
    title: 'Fixture Wiki',
    description: '面向需要定位测试文档的人和 AI，导航主题与治理入口；不包含任何生产结论。',
    type: 'index',
    extra: 'when_to_read: "需要验证索引与链接规则时。"\nkeywords: ["fixture", "索引", "链接"]\n',
  }));
  write(root, 'wiki/00_meta/index.md', page({
    title: 'Fixture Meta',
    description: '面向测试维护者导航元数据规则，帮助复现校验行为；不代表生产仓库规范。',
    type: 'index',
    extra: 'when_to_read: "需要读取测试元数据规则时。"\nkeywords: ["meta", "validator", "fixture"]\n',
  }));
  write(root, 'wiki/00_meta/markdown-standard.md', page({
    title: 'Fixture Markdown Standard',
    description: '为攻击测试提供最小字段枚举和解析对象，支持校验器启动；不替代正式规范。',
    type: 'meta',
    body: '```yaml\ntype: "index | meta | page | redirect"\nstatus: "Working | Archived"\nowner: "AI | Human | Team"\n```',
  }));
  write(root, 'wiki/topic/index.md', page({
    title: 'Topic Index',
    description: '导航当前测试主题的直接入口，帮助验证分层索引；不展开孙级正文。',
    type: 'index',
    extra: 'when_to_read: "需要进入测试主题时。"\nkeywords: ["topic", "direct entry", "fixture"]\n',
  }));
  write(root, 'wiki/topic/deep/index.md', page({
    title: 'Deep Index',
    description: '导航深层测试页面并提供直接入口，帮助验证父级边界；不承担上级导航。',
    type: 'index',
    extra: 'when_to_read: "需要进入深层测试页时。"\nkeywords: ["deep", "index", "fixture"]\n',
  }));
  write(root, 'wiki/topic/deep/page.md', page({
    title: 'Unicode 页面',
    description: '面向解析器验证中文对象、quoted comma 和生成表格，帮助确认元数据不被截断；不代表业务事实。',
    extra: 'when_to_read: >-\n  需要检查 quoted comma、Unicode，\n  以及 multiline 字段时。\nkeywords: ["Unicode", "quoted, comma", "multiline"]\n',
  }));
  write(root, 'wiki/topic/deep/canonical.md', page({
    title: 'Canonical Page',
    description: '承载攻击测试使用的稳定正文，帮助验证旧路径不会继续充当活动入口；不代表生产知识。',
  }));
  write(root, 'wiki/topic/deep/legacy.md', page({
    title: 'Legacy Page — Moved',
    description: '兼容攻击测试中的旧路径并指向稳定正文，帮助验证迁移行为；本页不承载第二份知识内容。',
    type: 'redirect',
    status: 'Archived',
    sources: '["canonical.md"]',
    related: '["canonical.md"]',
    extra: 'redirect_to: "canonical.md"\n',
    body: '[Canonical Page](canonical.md)',
  }));
  accept(run(root, 'scripts/sync-indexes.mjs'), /INDEXES_SYNCED:/, 'fixture sync');
  accept(run(root, 'scripts/validate-indexes.mjs', ['--strict']), /INDEX_VALIDATION_PASS:/, 'fixture index baseline');
  accept(run(root, 'scripts/validate-links.mjs', ['--release']), /LINK_VALIDATION_PASS:/, 'fixture link baseline');
  return root;
}

function writeAllowlist(root, legacyEntries = []) {
  write(root, 'scripts/document-id-legacy-allowlist.json', `${JSON.stringify({
    schema_version: 1,
    frozen_on: '2026-07-29',
    legacy_entries: legacyEntries,
    record_policies: [
      { type: 'verification-record', path_pattern: '^wiki/90_outputs/courses/verification/(VER-[0-9]{8}-[a-z0-9][a-z0-9-]*)\\.md$', id_field: 'verification_id' },
      { type: 'writeback-record', path_pattern: '^wiki/90_outputs/courses/writeback/(WB-[0-9]{8}-[a-z0-9][a-z0-9-]*)\\.md$', id_field: 'writeback_id' },
    ],
  }, null, 2)}\n`);
}
function idFixture() {
  const root = fixture();
  rmSync(join(root, 'wiki/topic/deep/legacy.md'), { force: true });
  writeAllowlist(root);
  return root;
}
function numberedPage(id = 'ID-0001') {
  return page({ title: 'Numbered Canonical', description: '承载文档编号与 redirect 攻击测试的稳定正文，帮助验证 canonical 绑定；不代表生产知识。', type: 'concept', extra: `doc_id: "${id}"\nwhen_to_read: "需要验证文档编号和 redirect 绑定时。"\nkeywords: ["document id", "redirect", "canonical"]\n` });
}

const cases = [
  ['front matter typed YAML coverage', () => {
    const meta = parseFrontMatterText(`---\ntitle: "中文, Unicode ✅"\ndescription: >-\n  面向解析器，处理 quoted comma，\n  并保留多行语义。\nowner: 42\nkeywords: ["quoted, comma", "中文", "multiline"]\ntitle: "重复"\n---\n# Body\n`);
    assert.equal(stringField(meta, 'description'), '面向解析器，处理 quoted comma， 并保留多行语义。');
    assert.equal(meta.data.get('owner'), 42);
    assert.deepEqual(meta.duplicateKeys, ['title']);
    assert.deepEqual(stringListField(meta, 'keywords').values, ['quoted, comma', '中文', 'multiline']);
  }],
  ['generator preserves quoted comma Unicode and multiline', () => {
    const root = fixture();
    const generated = readFileSync(join(root, 'wiki/topic/deep/index.md'), 'utf8');
    assert.match(generated, /Unicode 页面/);
    assert.match(generated, /quoted, comma/);
    assert.match(generated, /需要检查 quoted comma、Unicode， 以及 multiline 字段时。/);
    assert.match(generated, /\[Canonical Page\]\(canonical\.md\)/);
    assert.doesNotMatch(generated, /legacy\.md|Legacy Page — Moved/);
  }],
  ['active Markdown link to redirect is rejected', () => {
    const root = fixture();
    const path = join(root, 'wiki/topic/deep/page.md');
    writeFileSync(path, `${readFileSync(path, 'utf8')}\n[旧入口](legacy.md)\n`);
    reject(run(root, 'scripts/validate-indexes.mjs', ['--strict']), /active Markdown link targets type: redirect legacy page: wiki\/topic\/deep\/page\.md -> legacy\.md; use canonical\.md/, 'Markdown redirect validation');
  }],
  ['sources path to redirect is rejected', () => {
    const root = fixture();
    const path = join(root, 'wiki/topic/deep/page.md');
    writeFileSync(path, readFileSync(path, 'utf8').replace('sources: []', 'sources: ["wiki/topic/deep/legacy.md"]'));
    reject(run(root, 'scripts/validate-indexes.mjs', ['--strict']), /sources path targets type: redirect legacy page: wiki\/topic\/deep\/page\.md -> wiki\/topic\/deep\/legacy\.md; use canonical\.md/, 'sources redirect validation');
  }],
  ['related path to redirect is rejected', () => {
    const root = fixture();
    const path = join(root, 'wiki/topic/deep/page.md');
    writeFileSync(path, readFileSync(path, 'utf8').replace('related: []', 'related: ["legacy.md"]'));
    reject(run(root, 'scripts/validate-indexes.mjs', ['--strict']), /related path targets type: redirect legacy page: wiki\/topic\/deep\/page\.md -> legacy\.md; use canonical\.md/, 'related redirect validation');
  }],
  ['source registry path to redirect is rejected', () => {
    const root = fixture();
    write(root, 'wiki/topic/source-registry.md', page({
      title: 'Fixture Source Registry',
      description: '登记攻击测试来源到知识页的派生路径，帮助验证 registry 不接受旧入口；不代表生产来源。',
      body: '| Source ID | Pages Updated |\n|---|---|\n| SRC-TEST | `wiki/topic/deep/legacy.md` |',
    }));
    reject(run(root, 'scripts/validate-indexes.mjs', ['--strict']), /registry path targets type: redirect legacy page: wiki\/topic\/source-registry\.md -> wiki\/topic\/deep\/legacy\.md; use canonical\.md/, 'registry redirect validation');
  }],
  ['dynamic wiki canonical discovery blocks missing retrieval metadata', () => {
    const root = fixture();
    write(root, 'wiki/topic/catalog/index.md', page({
      title: 'Unregistered Catalog Index',
      description: '导航动态发现测试目录，帮助确认校验器不依赖硬编码入口清单；不提供生产导航。',
      type: 'index',
    }));
    accept(run(root, 'scripts/sync-indexes.mjs'), /INDEXES_SYNCED:/, 'dynamic canonical sync');
    reject(run(root, 'scripts/validate-indexes.mjs', ['--strict']), /canonical entry keywords must contain 3-8 retrieval terms: wiki\/topic\/catalog\/index\.md/, 'dynamic canonical metadata validation');
  }],
  ['duplicate metadata key blocks strict validation and sync', () => {
    const root = fixture();
    const path = join(root, 'wiki/topic/deep/page.md');
    writeFileSync(path, readFileSync(path, 'utf8').replace('owner: "AI"', 'owner: "AI"\nowner: "Human"'));
    reject(run(root, 'scripts/validate-indexes.mjs', ['--strict']), /duplicate metadata key owner:/, 'duplicate metadata validation');
    reject(run(root, 'scripts/sync-indexes.mjs', ['--check']), /duplicate metadata key\(s\): owner/, 'duplicate metadata sync');
  }],
  ['non-string required field blocks validation', () => {
    const root = fixture();
    const path = join(root, 'wiki/topic/deep/page.md');
    writeFileSync(path, readFileSync(path, 'utf8').replace('title: "Unicode 页面"', 'title: 42'));
    reject(run(root, 'scripts/validate-indexes.mjs', ['--strict']), /title must be a string, not number:/, 'typed metadata validation');
  }],
  ['generic long description blocks strict validation', () => {
    const root = fixture();
    const path = join(root, 'wiki/index.md');
    writeFileSync(path, readFileSync(path, 'utf8').replace(/description:.*\n/u, 'description: "这是一个关于 SEO 的文档，用来介绍 SEO 相关内容、基本页面说明和常规资料。"\n'));
    reject(run(root, 'scripts/validate-indexes.mjs', ['--strict']), /generic or semantically empty description: wiki\/index\.md/, 'description quality validation');
  }],
  ['reference-style descendant cannot bypass index boundary', () => {
    const root = fixture();
    const path = join(root, 'wiki/index.md');
    writeFileSync(path, `${readFileSync(path, 'utf8')}\n[深层页面][deep-page]\n\n[deep-page]: topic/deep/page.md\n`);
    reject(run(root, 'scripts/validate-indexes.mjs', ['--strict']), /index manual area recursively links to non-direct descendant: wiki\/index\.md -> topic\/deep\/page\.md/, 'reference descendant validation');
  }],
  ['reference-style broken target blocks release link validation', () => {
    const root = fixture();
    const path = join(root, 'wiki/topic/deep/page.md');
    writeFileSync(path, `${readFileSync(path, 'utf8')}\n[断链][missing]\n\n[missing]: missing.md\n`);
    reject(run(root, 'scripts/validate-links.mjs', ['--release']), /links to missing path: missing\.md/, 'reference broken-link validation');
  }],
  ['strict mode blocks navigable child without canonical entry', () => {
    const root = fixture();
    write(root, 'wiki/topic/orphan/note.md', page({
      title: 'Orphan Note',
      description: '记录缺少 canonical 入口的攻击样本，帮助验证目录闸门；不代表允许孤立发布。',
    }));
    reject(run(root, 'scripts/validate-indexes.mjs', ['--strict']), /navigable directory has no canonical entry: wiki\/topic\/orphan/, 'missing canonical validation');
  }],
  ['duplicate reference definition blocks release validation', () => {
    const root = fixture();
    const path = join(root, 'wiki/topic/deep/page.md');
    writeFileSync(path, `${readFileSync(path, 'utf8')}\n[x]: page.md\n[x]: index.md\n`);
    reject(run(root, 'scripts/validate-links.mjs', ['--release']), /duplicate reference definition: x/, 'duplicate reference validation');
  }],
  ['README-only canonical roots enforce one child entry and permit valid hierarchy', () => {
    const missing = fixture();
    write(missing, 'docs/README.md', page({ title: 'Docs Root', description: '导航 README-only 测试树并验证所有可导航子目录都有唯一入口；不提供生产文档。', type: 'index', extra: 'canonical_entry: "README.md"\nwhen_to_read: "需要验证 README-only canonical 子树时。"\nkeywords: ["README only", "canonical", "navigation"]\n' }));
    write(missing, 'docs/child/note.md', page({ title: 'Child Note', description: '制造缺少 canonical 入口的子目录样本，帮助确认 validator 不会漏扫 README-only 根。' }));
    reject(run(missing, 'scripts/validate-indexes.mjs', ['--strict']), /navigable directory has no canonical entry: docs\/child/, 'README-only missing child canonical');

    const duplicate = fixture();
    write(duplicate, 'docs/README.md', page({ title: 'Docs Root', description: '导航 README-only 测试树并验证子目录不能同时声明两个入口；不提供生产文档。', type: 'index', extra: 'canonical_entry: "README.md"\nwhen_to_read: "需要验证 README-only canonical 唯一性时。"\nkeywords: ["README only", "duplicate canonical", "navigation"]\n' }));
    write(duplicate, 'docs/child/README.md', page({ title: 'Child README', description: '作为重复入口攻击样本中的 README，帮助验证唯一 canonical 规则。', type: 'index', extra: 'canonical_entry: "README.md"\n' }));
    write(duplicate, 'docs/child/index.md', page({ title: 'Child Index', description: '作为重复入口攻击样本中的 index，帮助验证唯一 canonical 规则。', type: 'index' }));
    reject(run(duplicate, 'scripts/validate-indexes.mjs', ['--strict']), /duplicate canonical entry in docs\/child/, 'README-only duplicate child canonical');

    const valid = fixture();
    write(valid, 'docs/README.md', page({ title: 'Docs Root', description: '导航 README-only 测试树及其唯一子入口，帮助验证合法分层结构；不提供生产文档。', type: 'index', extra: 'canonical_entry: "README.md"\nwhen_to_read: "需要验证合法 README-only 分层时。"\nkeywords: ["README only", "hierarchy", "canonical"]\n' }));
    write(valid, 'docs/child/README.md', page({ title: 'Child README', description: '导航 README-only 子目录中的直接文件，帮助验证唯一入口可以向下分层。', type: 'index', extra: 'canonical_entry: "README.md"\n' }));
    write(valid, 'docs/child/note.md', page({ title: 'Child Note', description: '提供合法 README-only 层级中的直接正文样本，帮助验证结构不会被误拒。' }));
    accept(run(valid, 'scripts/sync-indexes.mjs'), /INDEXES_SYNCED:/, 'README-only valid sync');
    accept(run(valid, 'scripts/validate-indexes.mjs', ['--strict']), /INDEX_VALIDATION_PASS:/, 'README-only valid hierarchy');
  }],
  ['conversation-source requires explicit de-identified facets', () => {
    const missing = fixture();
    const missingPath = join(missing, 'wiki/topic/deep/page.md');
    writeFileSync(missingPath, readFileSync(missingPath, 'utf8').replace('type: "page"', 'type: "conversation-source"'));
    reject(run(missing, 'scripts/validate-indexes.mjs', ['--strict']), /conversation-source must explicitly declare subject_ref; an empty string is allowed:/, 'conversation subject_ref presence');

    const invalid = fixture();
    const invalidPath = join(invalid, 'wiki/topic/deep/page.md');
    writeFileSync(invalidPath, readFileSync(invalidPath, 'utf8').replace('type: "page"', 'type: "conversation-source"').replace('related: []', 'related: []\nsubject_ref: "Tony"\nclient_ref: "CLIENT-DEMO-01"'));
    reject(run(invalid, 'scripts/validate-indexes.mjs', ['--strict']), /subject_ref must be empty or a de-identified SUBJ reference:/, 'conversation subject_ref format');
  }],
  ['document ID allowlist and typed records fail closed', () => {
    const fresh = idFixture();
    write(fresh, 'wiki/20_concepts/new-page.md', page({ title: 'Unnumbered Durable', description: '模拟未经过编号流程新增的 durable page，帮助验证默认 fail-closed 行为。', type: 'concept' }));
    reject(run(fresh, 'scripts/validate-document-ids.mjs', ['--scope', 'mother']), /new or unregistered unnumbered durable page/, 'new unnumbered durable');

    const drift = idFixture();
    write(drift, 'wiki/20_concepts/legacy.md', page({ title: 'Legacy Concept', description: '模拟冻结 legacy 页面发生类型漂移，帮助验证 path 和 type 同时绑定。', type: 'playbook' }));
    writeAllowlist(drift, [{ path: 'wiki/20_concepts/legacy.md', type: 'concept' }]);
    reject(run(drift, 'scripts/validate-document-ids.mjs', ['--scope', 'mother']), /frozen legacy allowlist type drift/, 'legacy type drift');

    const record = idFixture();
    write(record, 'wiki/90_outputs/courses/verification/VER-20260729-wrong.md', page({ title: 'Wrong Record ID', description: '模拟 typed record 的声明 ID 与文件名不一致，帮助验证精确身份绑定。', type: 'verification-record', extra: 'verification_id: "VER-20260729-other"\n' }));
    reject(run(record, 'scripts/validate-document-ids.mjs', ['--scope', 'mother']), /verification_id must equal filename ID VER-20260729-wrong/, 'typed record ID binding');

    const wrongDirectory = idFixture();
    write(wrongDirectory, 'wiki/20_concepts/VER-20260729-misplaced.md', page({ title: 'Misplaced Record', description: '模拟 verification record 被放入错误 durable 目录，帮助验证记录类型不能绕过路径合同。', type: 'verification-record', extra: 'verification_id: "VER-20260729-misplaced"\n' }));
    reject(run(wrongDirectory, 'scripts/validate-document-ids.mjs', ['--scope', 'mother']), /verification-record is outside its allowed path:/, 'typed record directory binding');
  }],
  ['redirects reject missing self cycle multihop cross-scope and unnumbered target', () => {
    for (const [name, target, setup, marker] of [
      ['missing', 'missing.md', () => {}, /target does not exist as Markdown/],
      ['self', 'legacy.md', () => {}, /redirect_to cannot reference itself/],
      ['unnumbered', 'target.md', (root) => write(root, 'wiki/20_concepts/target.md', page({ title: 'Unnumbered Target', description: '模拟 redirect 指向未编号正文，帮助验证最终目标必须编号。', type: 'concept' })), /final target must be a numbered canonical durable page/],
    ]) {
      const root = idFixture();
      setup(root);
      write(root, 'wiki/20_concepts/legacy.md', page({ title: 'Legacy Redirect', description: '兼容旧入口并用于验证 redirect fail-closed 条件，不承载第二份业务知识。', type: 'redirect', status: 'Archived', extra: `redirect_to: "${target}"\n` }));
      writeAllowlist(root, [{ path: 'wiki/20_concepts/legacy.md', type: 'redirect' }]);
      reject(run(root, 'scripts/validate-document-ids.mjs', ['--scope', 'mother']), marker, `redirect ${name}`);
    }
    const cycle = idFixture();
    write(cycle, 'wiki/20_concepts/a.md', page({ title: 'Redirect A', description: '构造 redirect 环路的第一个冻结旧入口，用于验证 cycle 检测。', type: 'redirect', status: 'Archived', extra: 'redirect_to: "b.md"\n' }));
    write(cycle, 'wiki/20_concepts/b.md', page({ title: 'Redirect B', description: '构造 redirect 环路的第二个冻结旧入口，用于验证 cycle 检测。', type: 'redirect', status: 'Archived', extra: 'redirect_to: "a.md"\n' }));
    writeAllowlist(cycle, [{ path: 'wiki/20_concepts/a.md', type: 'redirect' }, { path: 'wiki/20_concepts/b.md', type: 'redirect' }]);
    reject(run(cycle, 'scripts/validate-document-ids.mjs', ['--scope', 'mother']), /redirect cycle detected/, 'redirect cycle');

    const multihop = idFixture();
    write(multihop, 'wiki/20_concepts/id-0001-target.md', numberedPage());
    write(multihop, 'wiki/20_concepts/a.md', page({ title: 'Redirect A', description: '构造 redirect 多跳链的第一个冻结旧入口，用于验证单跳限制。', type: 'redirect', status: 'Archived', extra: 'redirect_to: "b.md"\n' }));
    write(multihop, 'wiki/20_concepts/b.md', page({ title: 'Redirect B', description: '构造 redirect 多跳链的第二个冻结旧入口，用于验证单跳限制。', type: 'redirect', status: 'Archived', extra: 'redirect_to: "id-0001-target.md"\n' }));
    writeAllowlist(multihop, [{ path: 'wiki/20_concepts/a.md', type: 'redirect' }, { path: 'wiki/20_concepts/b.md', type: 'redirect' }]);
    reject(run(multihop, 'scripts/validate-document-ids.mjs', ['--scope', 'mother']), /redirect multihop is forbidden/, 'redirect multihop');

    const cross = idFixture();
    write(cross, 'wiki/20_concepts/legacy.md', page({ title: 'Cross Scope Redirect', description: '模拟母库旧入口指向子库正文，帮助验证发布 scope 不得跨越。', type: 'redirect', status: 'Archived', extra: 'redirect_to: "../../sub-libraries/example/knowledge/id-0001-target.md"\n' }));
    write(cross, 'sub-libraries/example/MANIFEST.md', 'durable_roots: ["knowledge"]\n');
    write(cross, 'sub-libraries/example/knowledge/id-0001-target.md', numberedPage());
    writeAllowlist(cross, [{ path: 'wiki/20_concepts/legacy.md', type: 'redirect' }]);
    reject(run(cross, 'scripts/validate-document-ids.mjs', ['--scope', 'mother']), /redirect_to crosses release scope/, 'redirect cross scope');
  }],
  ['legal single-hop redirect resolves to numbered canonical', () => {
    const root = idFixture();
    write(root, 'wiki/20_concepts/id-0001-target.md', numberedPage());
    write(root, 'wiki/20_concepts/legacy.md', page({ title: 'Legacy Redirect', description: '保留单一旧路径并精确指向编号 canonical，帮助验证合法单跳迁移。', type: 'redirect', status: 'Archived', extra: 'redirect_to: "id-0001-target.md"\n' }));
    writeAllowlist(root, [{ path: 'wiki/20_concepts/legacy.md', type: 'redirect' }]);
    accept(run(root, 'scripts/validate-document-ids.mjs', ['--scope', 'mother']), /DOCUMENT_ID_PASS/, 'legal single-hop redirect');
  }],

];

let passed = 0;
try {
  for (const [name, test] of cases) {
    test();
    passed += 1;
    console.log(`PASS: ${name}`);
  }
  console.log(`G3_ATTACK_TESTS_PASS: ${passed}/${cases.length}`);
} finally {
  for (const root of tempRoots) rmSync(root, { recursive: true, force: true });
}
