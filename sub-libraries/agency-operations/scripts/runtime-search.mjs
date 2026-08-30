#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { assertPrivatePermissions, assertRuntimeUnlocked, defaultRuntimePath, getClient, isInside, loadClientsRegistry, MAX_SEARCH_QUERY_LENGTH, MAX_SEARCH_RESULTS, parseArgs, readJsonl, validateCatalogRows } from './runtime-lib.mjs';

try {
  const args = parseArgs();
  if (!args.client) throw new Error('--client is required; cross-client search is prohibited');
  if (typeof args.query !== 'string' || !args.query.trim()) throw new Error('--query is required');
  if (args.query.length > MAX_SEARCH_QUERY_LENGTH) throw new Error(`--query exceeds ${MAX_SEARCH_QUERY_LENGTH} characters`);
  const runtime = defaultRuntimePath(args);
  assertRuntimeUnlocked(runtime);
  assertPrivatePermissions(runtime);
  const { path: clientRoot } = getClient(runtime, args.client);
  const { registry } = loadClientsRegistry(runtime);
  const rows = readJsonl(join(runtime, '00_control', 'search-catalog.jsonl'), 'search-catalog.jsonl');
  validateCatalogRows(runtime, registry, rows, { requireCurrent: true });
  const query = args.query.trim().toLocaleLowerCase('en-US');
  const results = [];
  for (const row of rows) {
    if (row.client_id !== args.client) continue;
    const target = resolve(runtime, row.path);
    if (!isInside(clientRoot, target)) throw new Error(`catalog row escaped target client after validation: ${row.path}`);
    const lines = readFileSync(target, 'utf8').split(/\r?\n/);
    for (let index = 0; index < lines.length; index += 1) {
      const line = lines[index];
      if (!line.toLocaleLowerCase('en-US').includes(query)) continue;
      results.push({ client_id: args.client, path: row.path, line: index + 1, text: line.slice(0, 500) });
      if (results.length > MAX_SEARCH_RESULTS) throw new Error(`query exceeds ${MAX_SEARCH_RESULTS} results; narrow the scoped query`);
    }
  }
  assertRuntimeUnlocked(runtime);
  for (const result of results) console.log(JSON.stringify(result));
  console.error(`RUNTIME_SEARCH_PASS:${args.client}:${results.length}`);
} catch (error) {
  console.error(`RUNTIME_SEARCH_BLOCK:${error.message}`);
  process.exit(error.exitCode ?? 1);
}
