#!/usr/bin/env node
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { dirname, extname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const releaseMode = process.argv.includes('--release');
const failures = [];
const warnings = [];
const requiredFiles = [
  'README.md','START-HERE.md','COURSE-MAP.md','MENTAL-MODEL.md','AGENTS.md','INTAKE.md','PLAYBOOK.md','TOOLS.md','QA-CHECKLIST.md','SOURCES.md','BRAND.md','CONTACT.md','WRITEBACK.md','VERSION.md','CHANGELOG.md','RELEASE.md','INSTALL.md','LICENSE.md','MANIFEST.md','RUNTIME-CONTRACT.json',
  'TEMPLATES/README.md','EXAMPLES/README.md','ADAPTERS/README.md','WORKSPACE-TEMPLATE/README.md','WORKSPACE-TEMPLATE/AGENTS.md','WORKSPACE-TEMPLATE/RUNTIME.json','WORKSPACE-TEMPLATE/00_control/ACTIVE-CONTEXT.json','WORKSPACE-TEMPLATE/00_control/CORE-LOCK.json','WORKSPACE-TEMPLATE/00_control/clients-registry.json','WORKSPACE-TEMPLATE/00_control/task-registry.jsonl','WORKSPACE-TEMPLATE/00_control/update-history.jsonl','WORKSPACE-TEMPLATE/00_control/search-catalog.jsonl','WORKSPACE-TEMPLATE/00_control/index.md','WORKSPACE-TEMPLATE/10_clients/index.md','migrations/registry.json',
  'scripts/README.md','scripts/runtime-lib.mjs','scripts/init-customer-runtime.mjs','scripts/create-client.mjs','scripts/register-entity.mjs','scripts/create-task.mjs','scripts/activate-task.mjs','scripts/sync-runtime-indexes.mjs','scripts/validate-runtime-indexes.mjs','scripts/runtime-search.mjs','scripts/validate-runtime-boundary.mjs','scripts/update-core.mjs','scripts/runtime-boundary.test.mjs','scripts/validate-sub-library.mjs'
];
function fail(message) { failures.push(message); }
function warn(message) { warnings.push(message); }
function walk(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    return entry.isDirectory() ? walk(path) : [path];
  });
}
function field(text, name) { return text.match(new RegExp(`^${name}:\\s*["']?([^\\n"']+)["']?\\s*$`, 'm'))?.[1]?.trim() ?? null; }

for (const file of requiredFiles) if (!existsSync(join(root, file))) fail(`missing required file: ${file}`);
if (existsSync(join(root, 'SKILL.md'))) fail('SKILL.md must not exist while skill_entrypoint is null and no stable execution evidence exists');

const manifest = existsSync(join(root, 'MANIFEST.md')) ? readFileSync(join(root, 'MANIFEST.md'), 'utf8') : '';
const expectedFields = {
  package_id: 'agency-operations', version: '0.1.0-draft.1', maturity_status: 'draft', verification_status: 'structure-pass', preparation_status: 'complete', preparation_scope: 'local-structure-and-synthetic', release_status: 'BLOCK', license_status: 'pending', approval_status: 'pending', release_scope: 'standalone-sub-library', runtime_contract: 'RUNTIME-CONTRACT.json', dependency_mode: 'self-contained', source_package_only: 'true', package_kind: 'standalone-sub-library', skill_entrypoint: 'null', canonical_entry: 'README.md', included_in_mother: 'source-only'
};
for (const [name, expected] of Object.entries(expectedFields)) if (field(manifest, name) !== expected) fail(`MANIFEST.md ${name} must be ${expected}, got ${field(manifest, name) ?? 'missing'}`);
for (const token of ['"human-playbook"','"toolkit"','"template-pack"']) if (!manifest.includes(token)) fail(`MANIFEST.md delivery_modes missing ${token}`);
if (/^skill_status:/m.test(manifest)) fail('MANIFEST.md must omit skill_status when skill_entrypoint is null');

try {
  const runtime = JSON.parse(readFileSync(join(root, 'RUNTIME-CONTRACT.json'), 'utf8'));
  for (const key of ['contract_version','package_id','inputs','outputs','required_permissions','network_access','external_side_effects','human_approval_points','rollback_strategy','writeback_scope','private_runtime_required']) if (runtime[key] === undefined) fail(`RUNTIME-CONTRACT.json missing ${key}`);
  if (runtime.package_id !== 'agency-operations') fail('RUNTIME-CONTRACT.json package_id mismatch');
  if (runtime.private_runtime_required !== true) fail('private_runtime_required must be true');
  if (!runtime.unsupported_claims?.includes('Published release')) fail('RUNTIME-CONTRACT.json must explicitly reject Published release claims');
} catch (error) { fail(`RUNTIME-CONTRACT.json invalid: ${error.message}`); }

for (const json of ['WORKSPACE-TEMPLATE/RUNTIME.json','WORKSPACE-TEMPLATE/00_control/ACTIVE-CONTEXT.json','WORKSPACE-TEMPLATE/00_control/CORE-LOCK.json','WORKSPACE-TEMPLATE/00_control/clients-registry.json','migrations/registry.json']) {
  try { JSON.parse(readFileSync(join(root, json), 'utf8')); } catch (error) { fail(`${json} invalid JSON: ${error.message}`); }
}

const files = walk(root);
for (const path of files) {
  const rel = relative(root, path).split('\\').join('/');
  if (['.md','.json','.jsonl','.mjs','.txt'].includes(extname(path))) {
    const text = readFileSync(path, 'utf8');
    if (/\/Users\/[A-Za-z0-9._-]+\//.test(text)) fail(`non-portable absolute user path: ${rel}`);
    if (/-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/.test(text)) fail(`private key shape in source: ${rel}`);
    if (/\bAKIA[0-9A-Z]{16}\b/.test(text)) fail(`AWS key shape in source: ${rel}`);
  }
}

for (const path of files.filter((path) => extname(path) === '.mjs')) {
  const result = spawnSync(process.execPath, ['--check', path], { cwd: root, encoding: 'utf8' });
  if (result.status !== 0) fail(`syntax check failed: ${relative(root, path)}: ${(result.stderr || result.stdout).trim()}`);
}
const tests = spawnSync(process.execPath, ['--test', join(root, 'scripts/runtime-boundary.test.mjs')], { cwd: root, encoding: 'utf8' });
if (tests.status !== 0) fail(`runtime adversarial tests failed: ${(tests.stdout || '')}\n${(tests.stderr || '')}`);
if (releaseMode) fail('release qualification is BLOCK: Draft maturity, pending license/approval, and missing real-customer evidence');
else {
  warnings.push('preparation complete is limited to local source, template, tooling, Git boundary, permission checks, indexes, and synthetic two-client tests');
  warnings.push('real customer isolation, ACL/external copies, multi-operator authorization, remote update apply, backup/restore, release, and production stability are post-preparation scopes');
}

for (const warning of warnings) console.warn(`WARN: ${warning}`);
if (failures.length) {
  for (const message of failures) console.error(`FAIL: ${message}`);
  console.error(`AGENCY_OPERATIONS_BLOCK:${failures.length}`);
  process.exit(1);
}
console.log('AGENCY_OPERATIONS_STRUCTURE_PASS');
console.log('AGENCY_OPERATIONS_PREPARATION_PASS');
