import test from 'node:test';
import assert from 'node:assert/strict';
import { validateSourceExtraction, validateSourceExtractionSchema } from './validate-source-extraction.mjs';
import { expectedRuntimeScope } from './runtime-scope.mjs';

const H = (char) => `sha256:${char.repeat(64)}`;
const TASK_ROOT = 'customer-runtime/10_clients/synthetic-client/30_tasks/synthetic-task';
const NOW = new Date('2026-08-12T08:00:00Z');
function fixture() {
  return {
    schema_version: '1.1', extraction_id: 'SX-synthetic-001',
    client_id: 'synthetic-client', company_id: 'synthetic-company', task_id: 'synthetic-task',
    runtime_scope: expectedRuntimeScope({ client_id: 'synthetic-client', company_id: 'synthetic-company', task_id: 'synthetic-task' }),
    source_id: 'SRC-001', source_kind: 'pdf', source_location: `${TASK_ROOT}/10_sources/catalog.pdf`, source_digest: H('a'),
    source_owner: 'synthetic-owner', rights_status: 'owned', method_use_clearance: 'approved', publication_clearance: 'approved',
    source_date: '2026-08-01T00:00:00Z', review_after: null, source_scope: 'synthetic-client/synthetic-company/synthetic-task',
    captured_at: '2026-08-12T07:55:00Z',
    extractor: { capability: 'pdf-read', implementation: 'host-pdf-runtime', version: 'runtime-observed', mode: 'native_text' },
    status: 'complete',
    units: [{ unit_id: 'UNIT-001', locator: 'page=2;paragraph=3', content_kind: 'text', value: 'Synthetic source text.', extraction_digest: H('b'), confidence: 'high', warnings: [] }],
    warnings: [], visibility: 'private-runtime',
  };
}
function validate(value) { return validateSourceExtraction(value, { now: NOW }); }
test('source-extraction Schema uses supported constructs', () => assert.deepEqual(validateSourceExtractionSchema(), []));
test('complete private extraction passes', () => { const r = validate(fixture()); assert.equal(r.ok, true, r.problems.join('\n')); });
test('complete extraction requires units', () => { const f = fixture(); f.units = []; const r = validate(f); assert.equal(r.ok, false); assert.match(r.problems.join('\n'), /requires at least one/); });
test('partial extraction requires warnings', () => { const f = fixture(); f.status = 'partial'; const r = validate(f); assert.equal(r.ok, false); assert.match(r.problems.join('\n'), /partial extraction requires/); });
test('blocked extraction cannot expose usable units', () => { const f = fixture(); f.status = 'blocked'; f.warnings = ['Parser unavailable.']; const r = validate(f); assert.equal(r.ok, false); assert.match(r.problems.join('\n'), /must not expose units/); });
test('low-confidence unit requires warning', () => { const f = fixture(); f.units[0].confidence = 'low'; const r = validate(f); assert.equal(r.ok, false); assert.match(r.problems.join('\n'), /requires a warning/); });
test('credential-like material is rejected', () => { const f = fixture(); f.units[0].value = ['Coo', 'kie', ': session', '=se', 'cret'].join(''); const r = validate(f); assert.equal(r.ok, false); assert.match(r.problems.join('\n'), /cookie header/); });
test('future capture time is rejected', () => { const f = fixture(); f.captured_at = '2026-08-12T09:00:00Z'; const r = validate(f); assert.equal(r.ok, false); assert.match(r.problems.join('\n'), /cannot be in the future/); });

test('pending method-use clearance blocks extraction consumption', () => { const f = fixture(); f.method_use_clearance = 'pending'; const r = validate(f); assert.equal(r.ok, false); assert.match(r.problems.join('\n'), /method_use_clearance=pending/); });
test('approved publication requires owned authorized or public rights', () => { const f = fixture(); f.rights_status = 'unknown'; const r = validate(f); assert.equal(r.ok, false); assert.match(r.problems.join('\n'), /publication_clearance=approved/); });
test('review-due source blocks extraction consumption', () => { const f = fixture(); f.review_after = '2026-08-12T07:59:59Z'; const r = validate(f); assert.equal(r.ok, false); assert.match(r.problems.join('\n'), /review_after is due or expired/); });

test('source extraction source scope must match client company and task', () => {
  const f = fixture(); f.source_scope = 'synthetic-client/other-company/synthetic-task';
  const r = validate(f); assert.equal(r.ok, false); assert.match(r.problems.join('\n'), /source_scope must exactly match/);
});
test('source extraction path cannot cross clients', () => {
  const f = fixture(); f.source_location = 'customer-runtime/10_clients/other-client/30_tasks/synthetic-task/catalog.pdf';
  const r = validate(f); assert.equal(r.ok, false); assert.match(r.problems.join('\n'), /must remain inside/);
});
test('source extraction blocks path traversal and URLs', () => {
  for (const bad of [`${TASK_ROOT}/10_sources/../catalog.pdf`, 'https://example.invalid/catalog.pdf']) {
    const f = fixture(); f.source_location = bad;
    const r = validate(f); assert.equal(r.ok, false); assert.match(r.problems.join('\n'), /parent path segments|absolute path or URL|must remain inside/);
  }
});
test('source extraction runtime scope digest binds company identity', () => {
  const f = fixture(); f.company_id = 'other-company';
  const r = validate(f); assert.equal(r.ok, false); assert.match(r.problems.join('\n'), /runtime_scope\.scope_digest must equal|source_scope must exactly match/);
});
