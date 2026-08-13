import { createHash } from 'node:crypto';
import { posix, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const CUSTOMER_RUNTIME_ROOT = 'customer-runtime';
const safeSegmentPattern = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;

export function calculateRuntimeScopeDigest({ client_id, company_id, task_id, root, client_root, task_root }) {
  const canonical = JSON.stringify({ client_id, company_id, task_id, root, client_root, task_root });
  return `sha256:${createHash('sha256').update(canonical).digest('hex')}`;
}

export function expectedRuntimeScope({ client_id, company_id, task_id }) {
  const root = CUSTOMER_RUNTIME_ROOT;
  const client_root = `${root}/10_clients/${client_id}`;
  const task_root = `${client_root}/30_tasks/${task_id}`;
  return {
    root,
    client_root,
    task_root,
    scope_digest: calculateRuntimeScopeDigest({ client_id, company_id, task_id, root, client_root, task_root }),
  };
}

export function validateRuntimeScopeBinding(record, { path = '$' } = {}) {
  const problems = [];
  const ids = ['client_id', 'company_id', 'task_id'];
  for (const key of ids) {
    const value = record?.[key];
    if (typeof value !== 'string' || !safeSegmentPattern.test(value) || value === '.' || value === '..') {
      problems.push(`${path}.${key} must be one safe path segment using letters, digits, dot, underscore, or hyphen`);
    }
  }
  if (problems.length > 0) return { problems, expected: null };

  const expected = expectedRuntimeScope(record);
  const actual = record?.runtime_scope;
  if (!actual || typeof actual !== 'object' || Array.isArray(actual)) {
    problems.push(`${path}.runtime_scope must be an object bound to client_id/company_id/task_id`);
    return { problems, expected };
  }
  for (const key of ['root', 'client_root', 'task_root', 'scope_digest']) {
    if (actual[key] !== expected[key]) problems.push(`${path}.runtime_scope.${key} must equal ${expected[key]}`);
  }
  return { problems, expected };
}

export function validateTaskRuntimePath(value, taskRoot, label, { nullable = false } = {}) {
  if (value === null && nullable) return [];
  if (typeof value !== 'string' || value.length === 0) return [`${label} must be a non-empty task-runtime path`];
  const problems = [];
  if (value.includes('\0')) problems.push(`${label} must not contain NUL`);
  if (value.includes('\\')) problems.push(`${label} must use POSIX separators and must not contain backslashes`);
  if (/[?#]/.test(value)) problems.push(`${label} must not contain a query or fragment`);
  if (/%[0-9A-Fa-f]{2}/.test(value)) problems.push(`${label} must not contain percent-encoded path bytes`);
  if (value.startsWith('/') || /^[A-Za-z][A-Za-z0-9+.-]*:/.test(value)) problems.push(`${label} must not be an absolute path or URL`);

  const segments = value.split('/');
  if (segments.some((segment) => segment === '' || segment === '.' || segment === '..')) problems.push(`${label} must not contain empty, dot, or parent path segments`);
  if (posix.normalize(value) !== value) problems.push(`${label} must already be a normalized relative POSIX path`);
  if (typeof taskRoot === 'string' && !value.startsWith(`${taskRoot}/`)) problems.push(`${label} must remain inside ${taskRoot}/`);
  return [...new Set(problems)];
}


if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [client_id, company_id, task_id] = process.argv.slice(2);
  const binding = validateRuntimeScopeBinding({
    client_id,
    company_id,
    task_id,
    runtime_scope: client_id && company_id && task_id ? expectedRuntimeScope({ client_id, company_id, task_id }) : null,
  });
  if (binding.problems.length > 0) {
    console.error('RUNTIME_SCOPE_BLOCK');
    for (const problem of binding.problems) console.error(`- ${problem}`);
    console.error('usage: node scripts/runtime-scope.mjs <client_id> <company_id> <task_id>');
    process.exit(1);
  }
  console.log(JSON.stringify(binding.expected, null, 2));
}
