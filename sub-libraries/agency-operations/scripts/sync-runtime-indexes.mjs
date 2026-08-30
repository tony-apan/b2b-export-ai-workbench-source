#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { assertPrivatePermissions, assertRuntime, assertRuntimeUnlocked, catalogRows, defaultRuntimePath, getClient, listClientTasks, loadClientsRegistry, loadCoreLock, parseArgs, readJson, readJsonl, renderClientsIndex, renderControlIndex, renderTaskIndex, validateActiveContext, validateTaskRegistry, withRuntimeWriteLock, writeTextAtomic } from './runtime-lib.mjs';

function loadState(runtime) {
  loadCoreLock(runtime);
  const { registry } = loadClientsRegistry(runtime);
  const clients = new Map();
  const taskViews = [];
  for (const entry of registry.entries) {
    const { path: clientRoot } = getClient(runtime, entry.client_id);
    const client = readJson(join(clientRoot, 'CLIENT.json'), `${entry.client_id}/CLIENT.json`);
    clients.set(entry.client_id, client);
    taskViews.push([join(clientRoot, '30_tasks', 'index.md'), renderTaskIndex(client, listClientTasks(runtime, entry.client_id))]);
  }
  const active = readJson(join(runtime, '00_control', 'ACTIVE-CONTEXT.json'), 'ACTIVE-CONTEXT.json');
  validateActiveContext(runtime, active, registry);
  const tasks = readJsonl(join(runtime, '00_control', 'task-registry.jsonl'), 'task-registry.jsonl');
  validateTaskRegistry(runtime, registry, tasks);
  return { registry, active, tasks, taskViews };
}

try {
  const args = parseArgs();
  const runtime = defaultRuntimePath(args);
  assertRuntime(runtime);

  if (args.check) {
    assertRuntimeUnlocked(runtime);
    assertPrivatePermissions(runtime);
    const { registry, active, tasks, taskViews } = loadState(runtime);
    const generatedViews = [
      [join(runtime, '10_clients', 'index.md'), renderClientsIndex(runtime, registry)],
      [join(runtime, '00_control', 'index.md'), renderControlIndex(runtime, registry, active, tasks)],
      ...taskViews,
    ];
    const staleViews = generatedViews.filter(([path, expected]) => readFileSync(path, 'utf8') !== expected).map(([path]) => path);
    if (staleViews.length) throw new Error(`generated runtime views are stale: ${staleViews.join(', ')}`);
    const catalog = catalogRows(runtime, registry).map((row) => JSON.stringify(row)).join('\n');
    const catalogExpected = catalog ? `${catalog}\n` : '';
    const catalogPath = join(runtime, '00_control', 'search-catalog.jsonl');
    if (readFileSync(catalogPath, 'utf8') !== catalogExpected) throw new Error(`generated runtime catalog is stale: ${catalogPath}`);
    console.log(`RUNTIME_INDEX_CHECK_PASS:${runtime}`);
  } else {
    withRuntimeWriteLock(runtime, 'sync-runtime-indexes', () => {
      const { registry, active, tasks, taskViews } = loadState(runtime);
      for (const [path, content] of taskViews) writeTextAtomic(path, content);
      writeTextAtomic(join(runtime, '10_clients', 'index.md'), renderClientsIndex(runtime, registry));
      writeTextAtomic(join(runtime, '00_control', 'index.md'), renderControlIndex(runtime, registry, active, tasks));
      const catalog = catalogRows(runtime, registry).map((row) => JSON.stringify(row)).join('\n');
      writeTextAtomic(join(runtime, '00_control', 'search-catalog.jsonl'), catalog ? `${catalog}\n` : '');
    });
    console.log(`RUNTIME_INDEX_SYNC_PASS:${runtime}`);
  }
} catch (error) {
  console.error(`RUNTIME_INDEX_SYNC_BLOCK:${error.message}`);
  process.exit(error.exitCode ?? 1);
}
