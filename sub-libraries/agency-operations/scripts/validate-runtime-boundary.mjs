#!/usr/bin/env node
import { existsSync, readFileSync, statSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { spawnSync } from 'node:child_process';
import { assertNoSymlinks, assertPrivatePermissions, assertRuntime, assertRuntimeUnlocked, defaultRuntimePath, getClient, isInside, loadClientsRegistry, loadCoreLock, loadEntities, MAX_INDEX_FILE_BYTES, parseArgs, readJson, readJsonl, repoRoot, TEXT_EXTENSIONS, validateActiveContext, validateTaskRegistry, walk } from './runtime-lib.mjs';

const secretPatterns = [
  { name: 'private-key', re: /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/ },
  { name: 'aws-access-key', re: /\bAKIA[0-9A-Z]{16}\b/ },
  { name: 'github-token', re: /\bgh[pousr]_[A-Za-z0-9]{30,}\b/ },
  { name: 'generic-secret-assignment', re: /\b(?:password|passwd|api[_-]?key|access[_-]?token|refresh[_-]?token|session[_-]?cookie)\s*[:=]\s*["']?[A-Za-z0-9+\/_=-]{12,}/i },
];

try {
  const args = parseArgs();
  const runtime = defaultRuntimePath(args);
  assertRuntime(runtime);
  assertRuntimeUnlocked(runtime);
  assertNoSymlinks(runtime);
  assertPrivatePermissions(runtime);
  loadCoreLock(runtime);
  const { registry } = loadClientsRegistry(runtime);
  for (const entry of registry.entries) {
    const client = getClient(runtime, entry.client_id);
    loadEntities(client.path);
  }
  const active = readJson(join(runtime, '00_control', 'ACTIVE-CONTEXT.json'), 'ACTIVE-CONTEXT.json');
  validateActiveContext(runtime, active, registry);
  const taskEvents = readJsonl(join(runtime, '00_control', 'task-registry.jsonl'), 'task-registry.jsonl');
  validateTaskRegistry(runtime, registry, taskEvents);

  for (const entry of walk(runtime)) {
    if (entry.type !== 'file' || !TEXT_EXTENSIONS.has(entry.path.slice(entry.path.lastIndexOf('.')).toLowerCase())) continue;
    const size = statSync(entry.path).size;
    if (size > MAX_INDEX_FILE_BYTES) throw new Error(`text file exceeds ${MAX_INDEX_FILE_BYTES} byte inspection limit: ${relative(runtime, entry.path)}`);
    const content = readFileSync(entry.path, 'utf8');
    const hit = secretPatterns.find((pattern) => pattern.re.test(content));
    if (hit) throw new Error(`secret shape ${hit.name} detected in ${relative(runtime, entry.path)}`);
  }

  if (isInside(repoRoot, runtime) && runtime !== repoRoot && existsSync(join(repoRoot, '.git'))) {
    const runtimeRel = relative(repoRoot, runtime).split(sep).join('/');
    const tracked = spawnSync('git', ['ls-files', '--', runtimeRel, 'credentials', 'secrets', 'browser-profiles'], { cwd: repoRoot, encoding: 'utf8' });
    if (tracked.status !== 0) throw new Error(`git ls-files boundary check failed: ${tracked.stderr.trim()}`);
    if (tracked.stdout.trim()) throw new Error(`reserved private paths are tracked by mother Git: ${tracked.stdout.trim().split(/\r?\n/).join(', ')}`);
    const ignored = spawnSync('git', ['check-ignore', '-q', `${runtimeRel}/`], { cwd: repoRoot });
    if (ignored.status !== 0) throw new Error(`${runtimeRel}/ is not ignored by mother Git`);
  }
  console.log(`RUNTIME_BOUNDARY_PASS:${registry.entries.length} clients`);
} catch (error) {
  console.error(`RUNTIME_BOUNDARY_BLOCK:${error.message}`);
  process.exit(error.exitCode ?? 1);
}
