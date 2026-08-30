#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import { assertPrivatePermissions, assertRuntime, assertRuntimeUnlocked, defaultRuntimePath, loadCoreLock, parseArgs, repoRoot } from './runtime-lib.mjs';

try {
  const args = parseArgs();
  if (!args.check || args.apply || args.pull || args.fetch) throw new Error('v1 supports only --check; fetch/pull/apply remain BLOCK until migration and rollback evidence exists');
  const runtime = defaultRuntimePath(args);
  assertRuntime(runtime);
  assertRuntimeUnlocked(runtime);
  assertPrivatePermissions(runtime);
  const { lock } = loadCoreLock(runtime);
  const head = spawnSync('git', ['rev-parse', 'HEAD'], { cwd: repoRoot, encoding: 'utf8' });
  if (head.status !== 0) throw new Error('mother core is not a readable Git checkout');
  const status = spawnSync('git', ['status', '--porcelain', '--untracked-files=no'], { cwd: repoRoot, encoding: 'utf8' });
  if (status.status !== 0) throw new Error('cannot inspect tracked core status');
  const result = { verdict: status.stdout.trim() ? 'BLOCK' : 'CHECK-PASS', reason: status.stdout.trim() ? 'tracked core has local modifications; do not auto-stash or pull' : 'tracked core is clean for a future fetch-only candidate check', current_commit: head.stdout.trim(), locked_commit: lock.core_commit, runtime_schema_version: lock.runtime_schema_version, apply_supported: false };
  console.log(JSON.stringify(result, null, 2));
  if (result.verdict === 'BLOCK') process.exit(2);
} catch (error) {
  console.error(`CORE_UPDATE_CHECK_BLOCK:${error.message}`);
  process.exit(error.exitCode ?? 1);
}
