#!/usr/bin/env node
import { randomUUID } from 'node:crypto';
import { existsSync, mkdirSync, renameSync } from 'node:fs';
import { join } from 'node:path';
import { assertDisplayText, assertTaskId, cleanup, defaultRuntimePath, getClient, injectTestFailure, loadCoreLock, loadEntities, markdownFrontMatter, nowIso, parseArgs, parseScopedIdList, readJson, readJsonl, validateTaskEntityScope, withRuntimeWriteLock, writeJsonAtomic, writeJsonlAtomic, writeTextAtomic } from './runtime-lib.mjs';

try {
  const args = parseArgs();
  const runtime = defaultRuntimePath(args);
  const clientId = args.client;
  const taskId = assertTaskId(args.task);
  const title = assertDisplayText(args.title, '--title');
  const productIds = parseScopedIdList(args.products, 'product', '--products');
  const channelIds = parseScopedIdList(args.channels, 'channel', '--channels');
  const accountIds = parseScopedIdList(args.accounts, 'account', '--accounts');

  withRuntimeWriteLock(runtime, `create-task:${clientId}/${taskId}`, () => {
    const { path: clientRoot } = getClient(runtime, clientId);
    const client = readJson(join(clientRoot, 'CLIENT.json'), 'CLIENT.json');
    const companyId = args.company ?? client.default_company_id;
    const { entities } = loadEntities(clientRoot);
    const tasksRoot = join(clientRoot, '30_tasks');
    const taskRoot = join(tasksRoot, taskId);
    if (existsSync(taskRoot)) throw new Error(`duplicate task_id or existing task directory: ${taskId}`);

    const createdAt = nowIso();
    const { lock } = loadCoreLock(runtime);
    const task = { schema_version: 1, task_id: taskId, client_id: clientId, company_id: companyId, product_ids: productIds, channel_ids: channelIds, account_ids: accountIds, title, status: 'planned', next_action: 'confirm scope, inputs and approval boundaries', blockers: [], prohibited_actions: ['external-send-without-approval','publish-without-approval','delete','cross-client-read'], created_at: createdAt, updated_at: createdAt, core_commit: lock.core_commit, runtime_schema_version: lock.runtime_schema_version, module_version: lock.modules?.['agency-operations'] ?? null };
    validateTaskEntityScope(task, entities);

    const staging = join(tasksRoot, `.staging-${taskId}-${process.pid}-${randomUUID()}`);
    const taskRegistryPath = join(runtime, '00_control', 'task-registry.jsonl');
    const activePath = join(runtime, '00_control', 'ACTIVE-CONTEXT.json');
    const originalTaskEvents = readJsonl(taskRegistryPath, 'task-registry.jsonl');
    if (originalTaskEvents.some((event) => event.event === 'task-created' && event.client_id === clientId && event.task_id === taskId)) throw new Error(`task registry already contains task-created for ${clientId}/${taskId}`);
    const originalActive = readJson(activePath, 'ACTIVE-CONTEXT.json');
    const nextTaskEvents = [...originalTaskEvents, { schema_version: 1, event: 'task-created', client_id: clientId, task_id: taskId, status: 'planned', occurred_at: createdAt, task_path: `10_clients/${clientId}/30_tasks/${taskId}/TASK.json` }];
    const nextActive = structuredClone(originalActive);
    if (args.activate) {
      nextActive.client_id = clientId;
      nextActive.company_id = task.company_id;
      nextActive.task_id = taskId;
      nextActive.authorized_by = assertDisplayText(args['authorized-by'] ?? 'local-user', '--authorized-by');
      nextActive.authorized_at = createdAt;
      nextActive.expires_at = null;
      nextActive.notes = 'Activation identifies read/write scope only; it does not authorize external actions.';
    }

    let taskPublished = false;
    let registryPublished = false;
    let activePublished = false;
    try {
      mkdirSync(staging, { recursive: false, mode: 0o700 });
      writeJsonAtomic(join(staging, 'TASK.json'), task);
      writeTextAtomic(join(staging, 'README.md'), `${markdownFrontMatter(title, `Task entry for ${clientId}/${taskId}.`)}# ${title}\n\n- task_id: \`${taskId}\`\n- client_id: \`${clientId}\`\n- [TASK.json](TASK.json)\n- [HANDOFF.md](HANDOFF.md)\n`);
      writeTextAtomic(join(staging, 'HANDOFF.md'), `---\ntitle: "${title.replaceAll('"', "'")} Handoff"\ndescription: "Current continuation summary for ${clientId}/${taskId}; TASK.json remains the machine state."\ntype: "writeback-record"\nstatus: "Working"\nowner: "User"\ncreated: "${createdAt.slice(0,10)}"\nlast_updated: "${createdAt.slice(0,10)}"\nsources: ["TASK.json"]\nrelated: ["TASK.json", "README.md"]\nvisibility: "private"\nredaction_status: "contains-private-data"\n---\n# Handoff\n\n## Current state\n\nPlanned. No external action is authorized.\n\n## Next action\n\nConfirm scope, inputs and approval boundaries.\n\n## Blockers\n\n- External actions remain denied until explicitly approved.\n\n## Evidence pointers\n\n- None.\n`);
      renameSync(staging, taskRoot);
      taskPublished = true;
      injectTestFailure('create-task-after-directory-publish');
      writeJsonlAtomic(taskRegistryPath, nextTaskEvents);
      registryPublished = true;
      if (args.activate) {
        writeJsonAtomic(activePath, nextActive);
        activePublished = true;
      }
    } catch (error) {
      const rollbackErrors = [];
      if (activePublished) {
        try { writeJsonAtomic(activePath, originalActive); } catch (rollbackError) { rollbackErrors.push(`active context rollback failed: ${rollbackError.message}`); }
      }
      if (registryPublished) {
        try { writeJsonlAtomic(taskRegistryPath, originalTaskEvents); } catch (rollbackError) { rollbackErrors.push(`task registry rollback failed: ${rollbackError.message}`); }
      }
      if (taskPublished) {
        try { cleanup(taskRoot); } catch (rollbackError) { rollbackErrors.push(`task rollback failed: ${rollbackError.message}`); }
      }
      cleanup(staging);
      if (rollbackErrors.length) throw new Error(`${error.message}; ${rollbackErrors.join('; ')}`);
      throw error;
    }
  });
  console.log(`TASK_CREATE_PASS:${clientId}/${taskId}`);
  console.error('NEXT: run sync-runtime-indexes.mjs before relying on generated indexes or search');
} catch (error) {
  console.error(`TASK_CREATE_BLOCK:${error.message}`);
  process.exit(error.exitCode ?? 1);
}
