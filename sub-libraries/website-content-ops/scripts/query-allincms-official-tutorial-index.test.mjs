import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const root = join(scriptDir, '..');
const indexPath = join(root, 'REFERENCES', 'ALLINCMS-OFFICIAL-TUTORIAL-INDEX.json');
const queryScript = join(scriptDir, 'query-allincms-official-tutorial-index.mjs');
const index = JSON.parse(readFileSync(indexPath, 'utf8'));

function query(value) {
  const result = spawnSync(process.execPath, [queryScript, '--json', value], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}

test('official tutorial index is same-domain, unique and complete for the verified snapshot', () => {
  assert.equal(index.schema_version, 1);
  assert.equal(index.discovery_summary.docs_urls_indexed, 36);
  assert.equal(index.entries.length, 36);
  assert.equal(new Set(index.entries.map((entry) => entry.tutorial_id)).size, 36);
  assert.equal(new Set(index.entries.map((entry) => entry.official_url)).size, 36);
  for (const entry of index.entries) {
    const url = new URL(entry.official_url);
    assert.equal(url.origin, 'https://www.allincms.com');
    assert.ok(url.pathname === '/docs' || url.pathname.startsWith('/docs/'));
    assert.equal(entry.evidence_level, 'official_tutorial');
    assert.equal(entry.http_status, 200);
    assert.equal(entry.last_verified_at, index.last_verified_at);
    assert.ok(entry.problem_intents.length > 0);
    assert.ok(entry.content_scope.length > 0);
    assert.ok(entry.content_scope.length <= 100);
    assert.doesNotMatch(entry.content_scope, /<[^>]+>/);
    assert.deepEqual(Object.keys(entry).sort(), [
      'canonical_adapter_routes', 'content_scope', 'evidence_level', 'fallback', 'h1',
      'http_status', 'keywords', 'last_verified_at', 'official_url', 'problem_intents',
      'title', 'topic', 'tutorial_id',
    ]);
  }
});

test('article intent returns the official add-posts tutorial first', () => {
  const result = query('怎么新建文章并发布');
  assert.equal(result.related_ui_tutorials[0].official_url, 'https://www.allincms.com/docs/content/add-posts');
});

test('product category intent returns the official category tutorial first', () => {
  const result = query('如何创建产品分类和分类 slug');
  assert.equal(result.related_ui_tutorials[0].official_url, 'https://www.allincms.com/docs/content/product-categories');
});

test('API gap remains explicit instead of being inferred from UI tutorials', () => {
  const result = query('如何获取用户 id API');
  assert.equal(result.intent_classification, 'api_or_internal_contract');
  assert.equal(result.official_docs_gaps[0].gap_id, 'ALLINCMS-GAP-002');
  assert.equal(result.related_ui_tutorials.length, 0);
  const gapTopics = index.not_found_in_current_public_docs_inventory.map((item) => item.topic).join('\n');
  assert.match(gapTopics, /user\.id API/);
  assert.match(gapTopics, /website-list API/);
  assert.match(gapTopics, /create-site API/);
  assert.match(index.global_does_not_prove.join('\n'), /public_api/);
});


test('login-state preflight routes to the canonical contract instead of a UI login tutorial', () => {
  const result = query('现在是不是登录的');
  assert.equal(result.intent_classification, 'api_or_internal_contract');
  assert.equal(result.official_docs_gaps[0].gap_id, 'ALLINCMS-GAP-002');
});

test('generic field and payload words do not add unrelated API gaps', () => {
  const article = query('文章接口有哪些字段');
  assert.deepEqual(article.official_docs_gaps.map((gap) => gap.gap_id), ['ALLINCMS-GAP-007']);
  const media = query('图片上传接口 payload');
  assert.deepEqual(media.official_docs_gaps.map((gap) => gap.gap_id), ['ALLINCMS-GAP-006']);
});

test('article tag question reports a tutorial coverage gap before related tutorials', () => {
  const result = query('文章标签怎么创建');
  assert.equal(result.intent_classification, 'official_tutorial_gap');
  assert.equal(result.official_docs_gaps[0].gap_id, 'ALLINCMS-GAP-010');
  assert.equal(result.related_ui_tutorials[0].official_url, 'https://www.allincms.com/docs/content/add-posts');
});

test('the primary intent of every indexed tutorial routes back to that tutorial', () => {
  for (const entry of index.entries) {
    const result = query(entry.problem_intents[0]);
    assert.ok(result.related_ui_tutorials.length > 0, `${entry.tutorial_id} returned no tutorial match`);
    assert.equal(
      result.related_ui_tutorials[0].tutorial_id,
      entry.tutorial_id,
      `${JSON.stringify(entry.problem_intents[0])} routed to the wrong tutorial`,
    );
  }
});
