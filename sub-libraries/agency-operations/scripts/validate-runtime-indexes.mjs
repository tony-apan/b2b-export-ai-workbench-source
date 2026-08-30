#!/usr/bin/env node
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';
import { spawnSync } from 'node:child_process';
import { assertNoSymlinks, assertPrivatePermissions, assertRuntime, assertRuntimeUnlocked, defaultRuntimePath, getClient, loadClientsRegistry, loadCoreLock, loadEntities, parseArgs, readJson, readJsonl, validateActiveContext, validateCatalogRows, validateTaskRegistry } from './runtime-lib.mjs';

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
  const catalog = readJsonl(join(runtime, '00_control', 'search-catalog.jsonl'), 'search-catalog.jsonl');
  validateCatalogRows(runtime, registry, catalog, { requireCurrent: true });
  const check = spawnSync(process.execPath, [join(dirname(fileURLToPath(import.meta.url)), 'sync-runtime-indexes.mjs'), '--runtime', runtime, '--check'], { encoding: 'utf8' });
  if (check.status !== 0) throw new Error(`generated runtime views are stale: ${(check.stderr || check.stdout).trim()}`);
  console.log(`RUNTIME_INDEX_VALIDATE_PASS:${registry.entries.length} clients, ${taskEvents.length} task events, ${catalog.length} catalog rows`);
} catch (error) {
  console.error(`RUNTIME_INDEX_VALIDATE_BLOCK:${error.message}`);
  process.exit(error.exitCode ?? 1);
}
