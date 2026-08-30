#!/usr/bin/env node
import { randomUUID } from 'node:crypto';
import { existsSync, mkdirSync, renameSync } from 'node:fs';
import { join } from 'node:path';
import { assertClientId, assertDisplayText, assertEntityId, cleanup, clientMarkdown, defaultRuntimePath, injectTestFailure, loadClientsRegistry, markdownFrontMatter, nowIso, parseArgs, readJsonl, withRuntimeWriteLock, writeJsonAtomic, writeJsonlAtomic, writeTextAtomic } from './runtime-lib.mjs';

try {
  const args = parseArgs();
  const runtime = defaultRuntimePath(args);
  const clientId = assertClientId(args.client);
  const displayName = assertDisplayText(args.name, '--name');
  const companyId = assertEntityId('company', args.company ?? `co-${clientId.slice(4)}`);

  withRuntimeWriteLock(runtime, `create-client:${clientId}`, () => {
    const { path: registryPath, registry } = loadClientsRegistry(runtime);
    if (registry.entries.some((entry) => entry.client_id === clientId)) throw new Error(`duplicate client_id: ${clientId}`);
    const clientsRoot = join(runtime, '10_clients');
    const clientRoot = join(clientsRoot, clientId);
    if (existsSync(clientRoot)) throw new Error(`refusing to adopt or overwrite existing client directory: ${clientRoot}`);

    const staging = join(clientsRoot, `.staging-${clientId}-${process.pid}-${randomUUID()}`);
    const historyPath = join(runtime, '00_control', 'update-history.jsonl');
    const originalRegistry = structuredClone(registry);
    const nextRegistry = structuredClone(registry);
    const originalHistory = readJsonl(historyPath, 'update-history.jsonl');
    let clientPublished = false;
    let registryPublished = false;
    try {
      const dirs = ['00_control', '10_sources/conversations', '20_knowledge/companies', '20_knowledge/products', '20_knowledge/icp', '30_tasks', '40_channels/website', '40_channels/social', '40_channels/laifaxin', '40_channels/email', '50_outputs', '60_metrics', '70_evidence', '80_activity', '90_writeback'];
      for (const dir of dirs) mkdirSync(join(staging, dir), { recursive: true, mode: 0o700 });
      const createdAt = nowIso();
      const client = { schema_version: 1, client_id: clientId, display_name: displayName, default_company_id: companyId, status: 'active', created_at: createdAt, updated_at: createdAt, credential_policy: 'opaque-reference-only', external_actions_default: 'deny' };
      writeJsonAtomic(join(staging, 'CLIENT.json'), client);
      writeJsonAtomic(join(staging, '00_control', 'entities.json'), { schema_version: 1, companies: [{ company_id: companyId, display_name: displayName, status: 'active', created_at: createdAt, updated_at: createdAt }], products: [], channels: [], accounts: [] });
      writeTextAtomic(join(staging, 'README.md'), clientMarkdown(client));
      const indexes = [
        ['00_control','Client Control','Client-local policy and non-secret references.'], ['10_sources','Sources','Approved source pointers and conversation archives.'], ['10_sources/conversations','Conversations','Raw conversation records; not current task state.'], ['20_knowledge','Knowledge','Client facts, companies, products and ICP.'], ['20_knowledge/companies','Companies','Company records.'], ['20_knowledge/products','Products','Product records.'], ['20_knowledge/icp','ICP','Ideal customer profiles and segments.'], ['30_tasks','Tasks','Current task projections and handoffs.'], ['40_channels','Channels','Website, social, Laifaxin and email channel work.'], ['40_channels/website','Website','Website operations.'], ['40_channels/social','Social','Social planning; no automatic interaction.'], ['40_channels/laifaxin','Laifaxin','Laifaxin outreach tasks and logs.'], ['40_channels/email','Email','Email account-scoped tasks and logs.'], ['50_outputs','Outputs','Drafts and deliverables.'], ['60_metrics','Metrics','Metrics with explicit definitions.'], ['70_evidence','Evidence','Private evidence pointers and bundles.'], ['80_activity','Activity','Append-only daily activity.'], ['90_writeback','Writeback','De-identified reusable improvement candidates.']
      ];
      for (const [dir, title, description] of indexes) writeTextAtomic(join(staging, dir, 'index.md'), `${markdownFrontMatter(`${displayName} ${title}`, description)}# ${title}\n\n暂无记录。\n`);
      nextRegistry.entries.push({ client_id: clientId, display_name: displayName, path: `10_clients/${clientId}`, status: 'active', created_at: createdAt, updated_at: createdAt });
      const nextHistory = [...originalHistory, { schema_version: 1, event: 'client-created', client_id: clientId, occurred_at: createdAt }];

      renameSync(staging, clientRoot);
      clientPublished = true;
      injectTestFailure('create-client-after-directory-publish');
      writeJsonAtomic(registryPath, nextRegistry);
      registryPublished = true;
      writeJsonlAtomic(historyPath, nextHistory);
    } catch (error) {
      const rollbackErrors = [];
      if (registryPublished) {
        try { writeJsonAtomic(registryPath, originalRegistry); } catch (rollbackError) { rollbackErrors.push(`registry rollback failed: ${rollbackError.message}`); }
      }
      if (clientPublished) {
        try { cleanup(clientRoot); } catch (rollbackError) { rollbackErrors.push(`client rollback failed: ${rollbackError.message}`); }
      }
      cleanup(staging);
      if (rollbackErrors.length) throw new Error(`${error.message}; ${rollbackErrors.join('; ')}`);
      throw error;
    }
  });
  console.log(`CLIENT_CREATE_PASS:${clientId}`);
  console.error('NEXT: run sync-runtime-indexes.mjs before relying on generated indexes or search');
} catch (error) {
  console.error(`CLIENT_CREATE_BLOCK:${error.message}`);
  process.exit(error.exitCode ?? 1);
}
