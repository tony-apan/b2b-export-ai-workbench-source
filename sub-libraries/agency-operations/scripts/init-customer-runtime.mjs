#!/usr/bin/env node
import { randomUUID } from 'node:crypto';
import { existsSync, readFileSync, renameSync } from 'node:fs';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { assertNoSymlinks, assertPrivatePermissions, cleanup, copyWorkspaceTemplate, defaultRuntimePath, hardenPrivatePermissions, nowIso, PACKAGE_VERSION, parseArgs, repoRoot, withExclusiveFileLock, writeJsonAtomic } from './runtime-lib.mjs';

let staging = null;
try {
  const args = parseArgs();
  const runtime = defaultRuntimePath(args);
  if (existsSync(runtime)) throw new Error(`refusing to overwrite existing runtime: ${runtime}`);
  const lockPath = `${runtime}.init.lock`;
  withExclusiveFileLock(lockPath, 'init-customer-runtime', () => {
    if (existsSync(runtime)) throw new Error(`runtime appeared while acquiring init lock: ${runtime}`);
    staging = `${runtime}.init-staging-${process.pid}-${randomUUID()}`;
    copyWorkspaceTemplate(staging);
    const git = spawnSync('git', ['rev-parse', 'HEAD'], { cwd: repoRoot, encoding: 'utf8' });
    const coreCommit = git.status === 0 ? git.stdout.trim() : null;
    const versionText = existsSync(join(repoRoot, 'VERSION.md')) ? readFileSync(join(repoRoot, 'VERSION.md'), 'utf8') : '';
    const coreVersion = versionText.match(/Version：`([^`]+)`/)?.[1] ?? null;
    const createdAt = nowIso();
    writeJsonAtomic(join(staging, 'RUNTIME.json'), { runtime_schema_version: 1, runtime_id: `runtime-${createdAt.replace(/[^0-9]/g, '').slice(0, 14)}`, created_at: createdAt, core_lock: '00_control/CORE-LOCK.json', clients_registry: '00_control/clients-registry.json', task_registry: '00_control/task-registry.jsonl', search_catalog: '00_control/search-catalog.jsonl', private_runtime: true, tracked_by_mother_git: false });
    writeJsonAtomic(join(staging, '00_control', 'CORE-LOCK.json'), { schema_version: 1, core_commit: coreCommit, core_version: coreVersion, knowledge_revision: coreCommit, runtime_schema_version: 1, locked_at: createdAt, modules: { 'agency-operations': PACKAGE_VERSION } });
    assertNoSymlinks(staging);
    hardenPrivatePermissions(staging);
    assertPrivatePermissions(staging);
    renameSync(staging, runtime);
    staging = null;
  });
  console.log(`RUNTIME_INIT_PASS:${runtime}`);
} catch (error) {
  if (staging) cleanup(staging);
  console.error(`RUNTIME_INIT_BLOCK:${error.message}`);
  process.exit(error.exitCode ?? 1);
}
