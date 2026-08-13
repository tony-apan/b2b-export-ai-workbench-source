import test from 'node:test';
import assert from 'node:assert/strict';
import { calculateRuntimeScopeDigest, expectedRuntimeScope, validateRuntimeScopeBinding, validateTaskRuntimePath } from './runtime-scope.mjs';

const identity = { client_id: 'synthetic-client-a', company_id: 'synthetic-company-a', task_id: 'synthetic-task-a' };
const expected = expectedRuntimeScope(identity);

test('runtime scope uses the canonical task path and a deterministic company-bound digest', () => {
  assert.equal(expected.root, 'customer-runtime');
  assert.equal(expected.client_root, 'customer-runtime/10_clients/synthetic-client-a');
  assert.equal(expected.task_root, 'customer-runtime/10_clients/synthetic-client-a/30_tasks/synthetic-task-a');
  assert.equal(expected.scope_digest, calculateRuntimeScopeDigest({ ...identity, ...expected }));
  assert.equal(validateRuntimeScopeBinding({ ...identity, runtime_scope: expected }).problems.length, 0);
});
test('company identity changes the digest even though company is not a directory layer', () => {
  assert.notEqual(expected.scope_digest, expectedRuntimeScope({ ...identity, company_id: 'synthetic-company-b' }).scope_digest);
});
test('unsafe identity segments are blocked', () => {
  for (const bad of ['../client', 'client/name', '', '.', '..', 'client name']) {
    const result = validateRuntimeScopeBinding({ ...identity, client_id: bad, runtime_scope: expected });
    assert.match(result.problems.join('\n'), /safe path segment/);
  }
});
test('only normalized descendants of the task root pass', () => {
  assert.deepEqual(validateTaskRuntimePath(`${expected.task_root}/40_evidence/readback.json`, expected.task_root, '$.ref'), []);
  for (const bad of [
    expected.task_root,
    `${expected.task_root}/../other/file.json`,
    `${expected.task_root}/40_evidence\\file.json`,
    `${expected.task_root}/40_evidence/file.json?x=1`,
    `${expected.task_root}/40_evidence/%2e%2e/file.json`,
    '/tmp/file.json',
    'https://example.invalid/file.json',
    'customer-runtime/10_clients/other/30_tasks/synthetic-task-a/file.json',
  ]) assert.notEqual(validateTaskRuntimePath(bad, expected.task_root, '$.ref').length, 0, bad);
});
