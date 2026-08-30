#!/usr/bin/env node
import { join } from 'node:path';
import { assertDisplayText, assertTaskId, defaultRuntimePath, getClient, loadEntities, nowIso, parseArgs, readJson, taskProjection, validateTaskEntityScope, withRuntimeWriteLock, writeJsonAtomic } from './runtime-lib.mjs';

try {
  const args = parseArgs();
  const runtime = defaultRuntimePath(args);

  withRuntimeWriteLock(runtime, args.clear ? 'clear-active-context' : `activate-task:${args.client}/${args.task}`, () => {
    const activePath = join(runtime, '00_control', 'ACTIVE-CONTEXT.json');
    const active = readJson(activePath, 'ACTIVE-CONTEXT.json');
    if (args.clear) {
      if (args.client || args.task) throw new Error('--clear cannot be combined with --client or --task');
      writeJsonAtomic(activePath, { schema_version: 1, client_id: null, company_id: null, task_id: null, authorized_by: null, authorized_at: null, expires_at: null, notes: 'No active client. AI must fail closed.' });
      return;
    }

    if (!args.client) throw new Error('--client is required unless --clear is used');
    const taskId = assertTaskId(args.task);
    const { path: clientRoot } = getClient(runtime, args.client);
    const { task } = taskProjection(runtime, args.client, taskId);
    const { entities } = loadEntities(clientRoot);
    validateTaskEntityScope(task, entities);
    let expiresAt = null;
    if (args['expires-at'] !== undefined) {
      expiresAt = String(args['expires-at']);
      if (!Number.isFinite(Date.parse(expiresAt))) throw new Error('--expires-at must be an ISO timestamp');
      if (Date.parse(expiresAt) <= Date.now()) throw new Error('--expires-at must be in the future');
    }
    writeJsonAtomic(activePath, {
      schema_version: 1,
      client_id: args.client,
      company_id: task.company_id,
      task_id: taskId,
      authorized_by: assertDisplayText(args['authorized-by'] ?? 'local-user', '--authorized-by'),
      authorized_at: nowIso(),
      expires_at: expiresAt,
      notes: 'Activation identifies read/write scope only; it does not authorize external actions.',
    });
  });
  console.log(args.clear ? 'ACTIVE_CONTEXT_CLEAR_PASS' : `TASK_ACTIVATE_PASS:${args.client}/${args.task}`);
  console.error('NEXT: run sync-runtime-indexes.mjs before relying on generated control indexes');
} catch (error) {
  console.error(`TASK_ACTIVATE_BLOCK:${error.message}`);
  process.exit(error.exitCode ?? 1);
}
