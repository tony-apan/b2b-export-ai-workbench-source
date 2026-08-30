import test from 'node:test';
import assert from 'node:assert/strict';
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { MAX_INDEX_FILE_BYTES } from './runtime-lib.mjs';

const scripts = dirname(fileURLToPath(import.meta.url));
function run(name, args = [], env = {}) {
  return spawnSync(process.execPath, [join(scripts, name), ...args], { encoding: 'utf8', env: { ...process.env, ...env } });
}
function ok(result, label) { assert.equal(result.status, 0, `${label}\nstdout=${result.stdout}\nstderr=${result.stderr}`); }
function blocked(result, label) { assert.notEqual(result.status, 0, `${label} unexpectedly passed\nstdout=${result.stdout}\nstderr=${result.stderr}`); }
function readJson(path) { return JSON.parse(readFileSync(path, 'utf8')); }
function writeJson(path, value) { writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`); }


test('two-client runtime remains scoped, recoverable, and fail-closed', () => {
  const parent = mkdtempSync(join(tmpdir(), 'agency-runtime-'));
  const runtime = join(parent, 'customer-runtime');
  try {
    ok(run('init-customer-runtime.mjs', ['--runtime', runtime]), 'init');
    blocked(run('init-customer-runtime.mjs', ['--runtime', runtime]), 'duplicate init');
    assert.deepEqual(readdirSync(parent).sort(), ['customer-runtime'], 'init must not leave lock or staging directories');
    if (process.platform !== 'win32') {
      assert.equal(statSync(runtime).mode & 0o777, 0o700, 'runtime root must be private');
      assert.equal(statSync(join(runtime, '00_control')).mode & 0o777, 0o700, 'control directory must be private');
      assert.equal(statSync(join(runtime, 'RUNTIME.json')).mode & 0o777, 0o600, 'runtime marker must be private');
      assert.equal(statSync(join(runtime, '00_control/ACTIVE-CONTEXT.json')).mode & 0o777, 0o600, 'active context must be private');
      if (typeof process.getuid === 'function') {
        assert.equal(statSync(runtime).uid, process.getuid(), 'runtime root owner must match the current user');
        assert.equal(statSync(join(runtime, '00_control/ACTIVE-CONTEXT.json')).uid, process.getuid(), 'runtime files must be owned by the current user');
      }
      chmodSync(join(runtime, '00_control/ACTIVE-CONTEXT.json'), 0o644);
      blocked(run('validate-runtime-boundary.mjs', ['--runtime', runtime]), 'world-readable runtime control file');
      blocked(run('sync-runtime-indexes.mjs', ['--runtime', runtime, '--check']), 'index check rejects unsafe permissions');
      chmodSync(join(runtime, '00_control/ACTIVE-CONTEXT.json'), 0o600);
    }

    ok(run('create-client.mjs', ['--runtime', runtime, '--client', 'cli-acme', '--name', 'Acme Synthetic']), 'create acme');
    ok(run('create-client.mjs', ['--runtime', runtime, '--client', 'cli-beta', '--name', 'Beta Synthetic']), 'create beta');
    const clientsRegistryPath = join(runtime, '00_control/clients-registry.json');
    const clientsRegistryBeforeRollbackTest = readFileSync(clientsRegistryPath, 'utf8');
    blocked(run('create-client.mjs', ['--runtime', runtime, '--client', 'cli-rollback', '--name', 'Rollback Synthetic'], { NODE_ENV: 'test', AGENCY_OPS_TEST_FAIL_AT: 'create-client-after-directory-publish' }), 'client transaction rollback after directory publish');
    assert.equal(existsSync(join(runtime, '10_clients/cli-rollback')), false, 'rolled-back client directory must be removed');
    assert.equal(readFileSync(clientsRegistryPath, 'utf8'), clientsRegistryBeforeRollbackTest, 'rolled-back client must not alter registry');
    blocked(run('create-client.mjs', ['--runtime', runtime, '--client', 'cli-acme', '--name', 'Duplicate']), 'duplicate client');
    blocked(run('create-client.mjs', ['--runtime', runtime, '--client', '../escape', '--name', 'Escape']), 'path traversal id');
    blocked(run('create-client.mjs', ['--runtime', runtime, '--client', 'cli-newline', '--name', 'Bad\nName']), 'newline display name');
    assert.equal(existsSync(join(runtime, '10_clients/cli-newline')), false, 'invalid client must not leave a partial directory');

    ok(run('register-entity.mjs', ['--runtime', runtime, '--client', 'cli-acme', '--type', 'product', '--id', 'prd-750w-motor', '--name', '750W Motor', '--company', 'co-acme']), 'register acme product');
    ok(run('register-entity.mjs', ['--runtime', runtime, '--client', 'cli-beta', '--type', 'product', '--id', 'prd-750w-motor', '--name', '750W Motor', '--company', 'co-beta']), 'register beta product');
    ok(run('register-entity.mjs', ['--runtime', runtime, '--client', 'cli-acme', '--type', 'company', '--id', 'co-acme-two', '--name', 'Acme Second Company']), 'register second acme company');
    ok(run('register-entity.mjs', ['--runtime', runtime, '--client', 'cli-acme', '--type', 'product', '--id', 'prd-other-company', '--name', 'Other Company Product', '--company', 'co-acme-two']), 'register cross-company test product');
    ok(run('register-entity.mjs', ['--runtime', runtime, '--client', 'cli-acme', '--type', 'channel', '--id', 'chn-laifaxin', '--name', 'Laifaxin', '--company', 'co-acme', '--channel-type', 'laifaxin']), 'register acme channel');
    ok(run('register-entity.mjs', ['--runtime', runtime, '--client', 'cli-beta', '--type', 'channel', '--id', 'chn-laifaxin', '--name', 'Laifaxin', '--company', 'co-beta', '--channel-type', 'laifaxin']), 'register beta channel');
    ok(run('register-entity.mjs', ['--runtime', runtime, '--client', 'cli-acme', '--type', 'account', '--id', 'acct-laifaxin-main', '--name', 'Main Laifaxin', '--company', 'co-acme', '--channel', 'chn-laifaxin', '--secret-ref', 'manual-login://laifaxin/acme-main']), 'register opaque account ref');
    blocked(run('register-entity.mjs', ['--runtime', runtime, '--client', 'cli-beta', '--type', 'account', '--id', 'acct-bad', '--name', 'Bad', '--company', 'co-beta', '--channel', 'chn-laifaxin', '--secret-ref', 'raw-password-value']), 'reject raw secret value');

    const taskRegistryPath = join(runtime, '00_control/task-registry.jsonl');
    const taskRegistryBefore = readFileSync(taskRegistryPath, 'utf8');
    blocked(run('create-task.mjs', ['--runtime', runtime, '--client', 'cli-acme', '--task', 'tsk-missing-channel', '--title', 'Missing channel', '--accounts', 'acct-laifaxin-main']), 'account task without explicit channel scope');
    blocked(run('create-task.mjs', ['--runtime', runtime, '--client', 'cli-acme', '--task', 'tsk-cross-company', '--title', 'Cross company', '--products', 'prd-other-company']), 'cross-company product scope');
    assert.equal(existsSync(join(runtime, '10_clients/cli-acme/30_tasks/tsk-missing-channel')), false, 'failed task must not leave a directory');
    assert.equal(existsSync(join(runtime, '10_clients/cli-acme/30_tasks/tsk-cross-company')), false, 'failed cross-company task must not leave a directory');
    assert.equal(readFileSync(taskRegistryPath, 'utf8'), taskRegistryBefore, 'failed tasks must not mutate task registry');

    blocked(run('create-task.mjs', ['--runtime', runtime, '--client', 'cli-acme', '--task', 'tsk-rollback', '--title', 'Rollback task'], { NODE_ENV: 'test', AGENCY_OPS_TEST_FAIL_AT: 'create-task-after-directory-publish' }), 'task transaction rollback after directory publish');
    assert.equal(existsSync(join(runtime, '10_clients/cli-acme/30_tasks/tsk-rollback')), false, 'rolled-back task directory must be removed');
    assert.equal(readFileSync(taskRegistryPath, 'utf8'), taskRegistryBefore, 'rolled-back task must not alter task registry');

    ok(run('create-task.mjs', ['--runtime', runtime, '--client', 'cli-acme', '--task', 'tsk-first-outreach', '--title', 'First outreach', '--products', 'prd-750w-motor', '--channels', 'chn-laifaxin', '--accounts', 'acct-laifaxin-main', '--activate']), 'create scoped task');
    ok(run('create-task.mjs', ['--runtime', runtime, '--client', 'cli-beta', '--task', 'tsk-beta-review', '--title', 'Beta review', '--products', 'prd-750w-motor', '--channels', 'chn-laifaxin']), 'create beta task');
    blocked(run('create-task.mjs', ['--runtime', runtime, '--client', 'cli-beta', '--task', '../escape', '--title', 'Escape']), 'task traversal');
    blocked(run('activate-task.mjs', ['--runtime', runtime, '--client', 'cli-acme', '--task', 'tsk-beta-review']), 'activate task from wrong client');
    blocked(run('activate-task.mjs', ['--runtime', runtime, '--client', 'cli-beta', '--task', 'tsk-beta-review', '--expires-at', '2020-01-01T00:00:00.000Z']), 'expired active context');
    ok(run('activate-task.mjs', ['--runtime', runtime, '--client', 'cli-beta', '--task', 'tsk-beta-review']), 'activate existing beta task');
    assert.equal(readJson(join(runtime, '00_control/ACTIVE-CONTEXT.json')).client_id, 'cli-beta');
    ok(run('activate-task.mjs', ['--runtime', runtime, '--clear']), 'clear active context');
    assert.equal(readJson(join(runtime, '00_control/ACTIVE-CONTEXT.json')).client_id, null);
    ok(run('activate-task.mjs', ['--runtime', runtime, '--client', 'cli-acme', '--task', 'tsk-first-outreach']), 'restore acme active task');

    const acme = join(runtime, '10_clients/cli-acme/20_knowledge/products/id-0001-750w-motor.md');
    const beta = join(runtime, '10_clients/cli-beta/20_knowledge/products/id-0001-750w-motor.md');
    writeFileSync(acme, '# 750W Motor\nmarker-acme-only\nchannel: laifaxin\n', { mode: 0o600 });
    writeFileSync(beta, '# 750W Motor\nmarker-beta-only\nchannel: laifaxin\n', { mode: 0o600 });
    ok(run('sync-runtime-indexes.mjs', ['--runtime', runtime]), 'sync');
    ok(run('validate-runtime-indexes.mjs', ['--runtime', runtime]), 'validate indexes');
    ok(run('validate-runtime-boundary.mjs', ['--runtime', runtime]), 'validate boundary');
    assert.match(readFileSync(join(runtime, '10_clients/cli-acme/30_tasks/index.md'), 'utf8'), /tsk-first-outreach/);

    const orphanClient = join(runtime, '10_clients/cli-orphan');
    mkdirSync(orphanClient, { mode: 0o700 });
    blocked(run('runtime-search.mjs', ['--runtime', runtime, '--client', 'cli-acme', '--query', 'marker']), 'unregistered client directory blocks scoped search');
    rmSync(orphanClient, { recursive: true });

    const runtimeMarkerPath = join(runtime, 'RUNTIME.json');
    const runtimeMarker = readJson(runtimeMarkerPath);
    writeJson(runtimeMarkerPath, { ...runtimeMarker, clients_registry: '../outside.json' });
    blocked(run('validate-runtime-boundary.mjs', ['--runtime', runtime]), 'tampered runtime pointer');
    writeJson(runtimeMarkerPath, runtimeMarker);

    const coreLockPath = join(runtime, '00_control/CORE-LOCK.json');
    const coreLock = readJson(coreLockPath);
    writeJson(coreLockPath, { ...coreLock, modules: { ...coreLock.modules, 'agency-operations': 'unexpected-version' } });
    blocked(run('validate-runtime-indexes.mjs', ['--runtime', runtime]), 'tampered core lock');
    writeJson(coreLockPath, coreLock);

    const handoffPath = join(runtime, '10_clients/cli-acme/30_tasks/tsk-first-outreach/HANDOFF.md');
    const handoff = readFileSync(handoffPath, 'utf8');
    rmSync(handoffPath);
    blocked(run('validate-runtime-indexes.mjs', ['--runtime', runtime]), 'missing task handoff');
    writeFileSync(handoffPath, handoff, { mode: 0o600 });
    ok(run('sync-runtime-indexes.mjs', ['--runtime', runtime]), 'sync after machine truth restoration');

    blocked(run('runtime-search.mjs', ['--runtime', runtime, '--query', 'marker']), 'unscoped search');
    const acmeSearch = run('runtime-search.mjs', ['--runtime', runtime, '--client', 'cli-acme', '--query', 'marker']);
    ok(acmeSearch, 'acme search');
    assert.match(acmeSearch.stdout, /marker-acme-only/);
    assert.doesNotMatch(acmeSearch.stdout, /marker-beta-only/);
    const betaSearch = run('runtime-search.mjs', ['--runtime', runtime, '--client', 'cli-beta', '--query', 'marker']);
    ok(betaSearch, 'beta search');
    assert.match(betaSearch.stdout, /marker-beta-only/);
    assert.doesNotMatch(betaSearch.stdout, /marker-acme-only/);

    const activePath = join(runtime, '00_control/ACTIVE-CONTEXT.json');
    const active = readJson(activePath);
    writeJson(activePath, { ...active, company_id: 'co-acme-two' });
    blocked(run('validate-runtime-indexes.mjs', ['--runtime', runtime]), 'active context company/task mismatch');
    writeJson(activePath, active);
    ok(run('sync-runtime-indexes.mjs', ['--runtime', runtime]), 'repair views after active restoration');

    const catalogPath = join(runtime, '00_control/search-catalog.jsonl');
    const originalRows = readFileSync(catalogPath, 'utf8').trim().split('\n').map(JSON.parse);
    const tamperedRows = structuredClone(originalRows);
    const betaRow = tamperedRows.find((row) => row.client_id === 'cli-beta');
    betaRow.path = '10_clients/cli-acme/CLIENT.json';
    writeFileSync(catalogPath, `${tamperedRows.map(JSON.stringify).join('\n')}\n`);
    blocked(run('validate-runtime-indexes.mjs', ['--runtime', runtime]), 'cross-client catalog');
    blocked(run('runtime-search.mjs', ['--runtime', runtime, '--client', 'cli-acme', '--query', 'acme']), 'search validates non-target catalog rows before filtering');
    ok(run('sync-runtime-indexes.mjs', ['--runtime', runtime]), 'repair catalog');

    const lockPath = join(runtime, '00_control/.runtime-write.lock');
    writeFileSync(lockPath, '{"operation":"synthetic-lock"}\n', { mode: 0o600 });
    blocked(run('register-entity.mjs', ['--runtime', runtime, '--client', 'cli-acme', '--type', 'product', '--id', 'prd-locked', '--name', 'Locked', '--company', 'co-acme']), 'writer lock blocks concurrent mutation');
    blocked(run('runtime-search.mjs', ['--runtime', runtime, '--client', 'cli-acme', '--query', 'marker']), 'writer lock blocks search during mutation');
    blocked(run('sync-runtime-indexes.mjs', ['--runtime', runtime]), 'writer lock blocks index mutation');
    rmSync(lockPath);

    const tooLarge = join(runtime, '10_clients/cli-beta/10_sources/conversations/oversized.txt');
    writeFileSync(tooLarge, 'x'.repeat(MAX_INDEX_FILE_BYTES + 1), { mode: 0o600 });
    blocked(run('sync-runtime-indexes.mjs', ['--runtime', runtime]), 'oversized text is not silently indexed');
    rmSync(tooLarge);
    ok(run('sync-runtime-indexes.mjs', ['--runtime', runtime]), 'sync after oversized file removal');

    const secretFile = join(runtime, '10_clients/cli-beta/70_evidence/secret-shape.txt');
    writeFileSync(secretFile, `${['pass', 'word'].join('')}=syntheticsecretvalue123\n`, { mode: 0o600 });
    blocked(run('validate-runtime-boundary.mjs', ['--runtime', runtime]), 'secret shape scan');
    rmSync(secretFile);

    const link = join(runtime, '10_clients/cli-acme/70_evidence/escape-link');
    symlinkSync(join(runtime, '10_clients/cli-beta'), link);
    blocked(run('validate-runtime-boundary.mjs', ['--runtime', runtime]), 'symlink escape');
    rmSync(link);
    ok(run('sync-runtime-indexes.mjs', ['--runtime', runtime]), 'final sync');
    ok(run('validate-runtime-indexes.mjs', ['--runtime', runtime]), 'final index validation');
    ok(run('validate-runtime-boundary.mjs', ['--runtime', runtime]), 'boundary after repair');
  } finally {
    rmSync(parent, { recursive: true, force: true });
  }
});
