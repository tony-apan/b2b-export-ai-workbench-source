import { randomUUID } from 'node:crypto';
import { chmodSync, closeSync, cpSync, existsSync, lstatSync, mkdirSync, openSync, readFileSync, realpathSync, readdirSync, renameSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { dirname, extname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

export const scriptDir = dirname(fileURLToPath(import.meta.url));
export const libraryRoot = resolve(scriptDir, '..');
export const repoRoot = resolve(libraryRoot, '..', '..');
export const templateRoot = join(libraryRoot, 'WORKSPACE-TEMPLATE');
export const RUNTIME_SCHEMA_VERSION = 1;
export const PACKAGE_VERSION = '0.1.0-draft.1';
export const CLIENT_ID_RE = /^cli-[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])$/;
export const TASK_ID_RE = /^tsk-[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])$/;
export const ENTITY_ID_PATTERNS = { company: /^co-[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])$/, product: /^prd-[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])$/, channel: /^chn-[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])$/, account: /^acct-[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])$/ };
export const CHANNEL_TYPES = new Set(['website', 'social', 'laifaxin', 'email']);
export const SECRET_REF_RE = /^(?:keychain|1password|secret-manager|env-ref|manual-login):\/\/[A-Za-z0-9._/@:-]+$/;
export const TEXT_EXTENSIONS = new Set(['.md', '.json', '.jsonl', '.txt', '.csv', '.html', '.xml', '.yaml', '.yml']);
export const MAX_INDEX_FILE_BYTES = 2 * 1024 * 1024;
export const MAX_SEARCH_RESULTS = 500;
export const MAX_SEARCH_QUERY_LENGTH = 200;
export const PRIVATE_DIRECTORY_MODE = 0o700;
export const PRIVATE_FILE_MODE = 0o600;

export function fail(message, code = 1) {
  const error = new Error(message);
  error.exitCode = code;
  throw error;
}

export function injectTestFailure(point) {
  if (process.env.NODE_ENV === 'test' && process.env.AGENCY_OPS_TEST_FAIL_AT === point) fail(`synthetic test failure at ${point}`);
}

export function parseArgs(argv = process.argv.slice(2)) {
  const result = { _: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith('--')) { result._.push(token); continue; }
    const key = token.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith('--')) result[key] = true;
    else { result[key] = next; i += 1; }
  }
  return result;
}

export function assertDisplayText(value, optionName, maxLength = 200) {
  const text = typeof value === 'string' ? value.trim() : '';
  if (!text) fail(`${optionName} is required`);
  if (text.length > maxLength) fail(`${optionName} exceeds ${maxLength} characters`);
  if(/[\u0000-\u001f\u007f]/.test(text)) fail(`${optionName} must not contain control characters or newlines`);
  return text;
}

export function defaultRuntimePath(args = {}) {
  return resolve(args.runtime ? String(args.runtime) : join(repoRoot, 'customer-runtime'));
}

export function nowIso() { return new Date().toISOString(); }

export function compareCodePoint(a, b) {
  return a < b ? -1 : a > b ? 1 : 0;
}

export function readJson(path, label = path) {
  let parsed;
  try { parsed = JSON.parse(readFileSync(path, 'utf8')); }
  catch (error) { fail(`${label} is not valid JSON: ${error.message}`); }
  return parsed;
}

export function writeJsonAtomic(path, value) {
  mkdirSync(dirname(path), { recursive: true, mode: PRIVATE_DIRECTORY_MODE });
  const temp = `${path}.tmp-${process.pid}-${randomUUID()}`;
  writeFileSync(temp, `${JSON.stringify(value, null, 2)}\n`, { encoding: 'utf8', mode: 0o600 });
  renameSync(temp, path);
}

export function writeTextAtomic(path, value) {
  mkdirSync(dirname(path), { recursive: true, mode: PRIVATE_DIRECTORY_MODE });
  const temp = `${path}.tmp-${process.pid}-${randomUUID()}`;
  writeFileSync(temp, value, { encoding: 'utf8', mode: 0o600 });
  renameSync(temp, path);
}

export function writeJsonlAtomic(path, rows) {
  writeTextAtomic(path, rows.length ? `${rows.map((row) => JSON.stringify(row)).join('\n')}\n` : '');
}

export function runtimeWriteLockPath(runtime) {
  return join(runtime, '00_control', '.runtime-write.lock');
}

export function assertRuntimeUnlocked(runtime) {
  const lockPath = runtimeWriteLockPath(runtime);
  if (existsSync(lockPath)) fail(`runtime write lock exists: ${lockPath}; another writer may be active or recovery may be required`);
}

export function withExclusiveFileLock(lockPath, operation, callback) {
  mkdirSync(dirname(lockPath), { recursive: true, mode: PRIVATE_DIRECTORY_MODE });
  let fd;
  try {
    fd = openSync(lockPath, 'wx', 0o600);
    writeFileSync(fd, `${JSON.stringify({ schema_version: 1, operation, pid: process.pid, acquired_at: nowIso() })}\n`, 'utf8');
  } catch (error) {
    if (fd !== undefined) {
      closeSync(fd);
      rmSync(lockPath, { force: true });
    }
    fail(`cannot acquire exclusive lock ${lockPath}: ${error.message}`);
  }
  closeSync(fd);
  try {
    return callback();
  } finally {
    rmSync(lockPath, { force: true });
  }
}

export function withRuntimeWriteLock(runtime, operation, callback) {
  assertRuntime(runtime);
  assertNoSymlinks(runtime);
  assertPrivatePermissions(runtime);
  return withExclusiveFileLock(runtimeWriteLockPath(runtime), operation, callback);
}

export function isInside(parent, candidate) {
  const p = resolve(parent);
  const c = resolve(candidate);
  return c === p || c.startsWith(`${p}${sep}`);
}

export function assertClientId(id) {
  if (typeof id !== 'string' || !CLIENT_ID_RE.test(id)) fail(`invalid client_id: ${id ?? 'missing'}; expected cli-[a-z0-9-]`);
  return id;
}

export function assertTaskId(id) {
  if (typeof id !== 'string' || !TASK_ID_RE.test(id)) fail(`invalid task_id: ${id ?? 'missing'}; expected tsk-[a-z0-9-]`);
  return id;
}

export function parseScopedIdList(value, type, optionName) {
  if (value === undefined || value === null || value === '') return [];
  if (typeof value !== 'string') fail(`${optionName} must be a comma-separated string`);
  const ids = value.split(',').map((item) => item.trim()).filter(Boolean);
  if (!ids.length) return [];
  const unique = new Set();
  for (const id of ids) {
    assertEntityId(type, id);
    if (unique.has(id)) fail(`duplicate ${type}_id in ${optionName}: ${id}`);
    unique.add(id);
  }
  return ids;
}

export function assertRuntime(runtime) {
  if (!existsSync(runtime)) fail(`runtime does not exist: ${runtime}; run init-customer-runtime.mjs first`);
  if (lstatSync(runtime).isSymbolicLink()) fail(`runtime root must not be a symlink: ${runtime}`);
  const marker = join(runtime, 'RUNTIME.json');
  if (!existsSync(marker)) fail(`runtime marker missing: ${marker}`);
  const config = readJson(marker, 'RUNTIME.json');
  if (config.runtime_schema_version !== RUNTIME_SCHEMA_VERSION) fail(`unsupported runtime_schema_version ${config.runtime_schema_version}; expected ${RUNTIME_SCHEMA_VERSION}`);
  if (config.private_runtime !== true || config.tracked_by_mother_git !== false) fail('RUNTIME.json does not declare the required private Git boundary');
  const expectedPointers = { core_lock: '00_control/CORE-LOCK.json', clients_registry: '00_control/clients-registry.json', task_registry: '00_control/task-registry.jsonl', search_catalog: '00_control/search-catalog.jsonl' };
  for (const [field, expected] of Object.entries(expectedPointers)) if (config[field] !== expected) fail(`RUNTIME.json ${field} must be ${expected}`);
  if (typeof config.runtime_id !== 'string' || !/^runtime-[a-zA-Z0-9-]+$/.test(config.runtime_id)) fail('RUNTIME.json runtime_id is invalid');
  if (typeof config.created_at !== 'string' || !Number.isFinite(Date.parse(config.created_at))) fail('RUNTIME.json created_at must be an ISO timestamp');
  return config;
}

export function loadCoreLock(runtime) {
  const path = join(runtime, '00_control', 'CORE-LOCK.json');
  const lock = readJson(path, 'CORE-LOCK.json');
  if (lock.schema_version !== 1) fail('CORE-LOCK.json schema_version must be 1');
  if (lock.runtime_schema_version !== RUNTIME_SCHEMA_VERSION) fail(`CORE-LOCK runtime_schema_version must be ${RUNTIME_SCHEMA_VERSION}`);
  if (lock.core_commit !== null && (typeof lock.core_commit !== 'string' || !/^[0-9a-f]{40}$/.test(lock.core_commit))) fail('CORE-LOCK core_commit must be null or a 40-character Git SHA');
  if (lock.knowledge_revision !== lock.core_commit) fail('CORE-LOCK knowledge_revision must match core_commit in v1');
  if (typeof lock.locked_at !== 'string' || !Number.isFinite(Date.parse(lock.locked_at))) fail('CORE-LOCK locked_at must be an ISO timestamp');
  if (lock.modules?.['agency-operations'] !== PACKAGE_VERSION) fail(`CORE-LOCK agency-operations module must be ${PACKAGE_VERSION}`);
  return { path, lock };
}

export function walk(root, { includeDirs = false } = {}) {
  const output = [];
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    const target = join(root, entry.name);
    if (entry.isSymbolicLink()) { output.push({ path: target, type: 'symlink' }); continue; }
    if (entry.isDirectory()) {
      if (includeDirs) output.push({ path: target, type: 'directory' });
      output.push(...walk(target, { includeDirs }));
    } else output.push({ path: target, type: 'file' });
  }
  return output;
}

export function assertNoSymlinks(root) {
  if (lstatSync(root).isSymbolicLink()) fail(`symlink is prohibited: ${root}`);
  const hit = walk(root, { includeDirs: true }).find((entry) => entry.type === 'symlink');
  if (hit) fail(`symlink is prohibited inside runtime: ${relative(root, hit.path)}`);
}

export function hardenPrivatePermissions(root) {
  if (!existsSync(root)) fail(`private runtime path does not exist: ${root}`);
  assertNoSymlinks(root);
  chmodSync(root, PRIVATE_DIRECTORY_MODE);
  for (const entry of walk(root, { includeDirs: true })) {
    chmodSync(entry.path, entry.type === 'directory' ? PRIVATE_DIRECTORY_MODE : PRIVATE_FILE_MODE);
  }
}

export function assertPrivatePermissions(root) {
  if (!existsSync(root)) fail(`private runtime path does not exist: ${root}`);
  const entries = [{ path: root, type: 'directory' }, ...walk(root, { includeDirs: true })];
  for (const entry of entries) {
    if (entry.type === 'symlink') fail(`symlink is prohibited inside runtime: ${relative(root, entry.path)}`);
    const expected = entry.type === 'directory' ? PRIVATE_DIRECTORY_MODE : PRIVATE_FILE_MODE;
    const stat = statSync(entry.path);
    const actual = stat.mode & 0o777;
    if (actual !== expected) fail(`private runtime permissions must be ${expected.toString(8).padStart(4, '0')}: ${relative(root, entry.path) || '.'} is ${actual.toString(8).padStart(4, '0')}`);
    if (typeof process.getuid === 'function' && stat.uid !== process.getuid()) fail(`private runtime owner must match the current user: ${relative(root, entry.path) || '.'} uid ${stat.uid} != ${process.getuid()}`);
  }
}


export function assertEntityId(type, id) {
  const pattern = ENTITY_ID_PATTERNS[type];
  if (!pattern || typeof id !== 'string' || !pattern.test(id)) fail(`invalid ${type}_id: ${id ?? 'missing'}`);
  return id;
}

export function loadEntities(clientRoot) {
  const path = join(clientRoot, '00_control', 'entities.json');
  const entities = readJson(path, 'entities.json');
  if (entities.schema_version !== 1) fail('entities.json schema_version must be 1');
  for (const key of ['companies', 'products', 'channels', 'accounts']) if (!Array.isArray(entities[key])) fail(`entities.json ${key} must be an array`);
  const scopes = [['company','companies','company_id'],['product','products','product_id'],['channel','channels','channel_id'],['account','accounts','account_id']];
  for (const [type,key,idField] of scopes) {
    const seen = new Set();
    for (const entry of entities[key]) {
      assertEntityId(type, entry?.[idField]);
      if (seen.has(entry[idField])) fail(`duplicate ${idField}: ${entry[idField]}`);
      seen.add(entry[idField]);
    }
  }
  const companies = new Set(entities.companies.map((entry) => entry.company_id));
  const channels = new Map(entities.channels.map((entry) => [entry.channel_id, entry]));
  for (const product of entities.products) if (!companies.has(product.company_id)) fail(`product ${product.product_id} references unknown company ${product.company_id}`);
  for (const channel of entities.channels) {
    if (!companies.has(channel.company_id)) fail(`channel ${channel.channel_id} references unknown company ${channel.company_id}`);
    if (!CHANNEL_TYPES.has(channel.channel_type)) fail(`channel ${channel.channel_id} has invalid channel_type ${channel.channel_type}`);
  }
  for (const account of entities.accounts) {
    if (!companies.has(account.company_id)) fail(`account ${account.account_id} references unknown company ${account.company_id}`);
    const channel = channels.get(account.channel_id);
    if (!channel) fail(`account ${account.account_id} references unknown channel ${account.channel_id}`);
    if (channel.company_id !== account.company_id) fail(`account ${account.account_id} crosses company/channel scope`);
    if (account.secret_ref !== null && !SECRET_REF_RE.test(account.secret_ref)) fail(`account ${account.account_id} secret_ref must be an opaque supported reference`);
  }
  return { path, entities };
}

export function validateTaskEntityScope(task, entities) {
  if (task?.schema_version !== 1) fail('TASK.json schema_version must be 1');
  assertClientId(task?.client_id);
  assertTaskId(task?.task_id);
  assertDisplayText(task?.title, 'TASK.json title');
  assertEntityId('company', task?.company_id);
  if (typeof task.status !== 'string' || !task.status) fail(`task ${task.task_id} status is required`);
  if (!Array.isArray(task.prohibited_actions) || !task.prohibited_actions.includes('cross-client-read')) fail(`task ${task.task_id} must prohibit cross-client-read`);
  if (!entities.companies.some((entry) => entry.company_id === task.company_id)) fail(`task ${task.task_id} references unknown company ${task.company_id}`);
  const specifications = [
    ['product', 'product_ids', 'products', 'product_id'],
    ['channel', 'channel_ids', 'channels', 'channel_id'],
    ['account', 'account_ids', 'accounts', 'account_id'],
  ];
  for (const [type, taskField, collection, idField] of specifications) {
    if (!Array.isArray(task[taskField])) fail(`task ${task.task_id} ${taskField} must be an array`);
    const seen = new Set();
    for (const id of task[taskField]) {
      assertEntityId(type, id);
      if (seen.has(id)) fail(`task ${task.task_id} has duplicate ${idField}: ${id}`);
      seen.add(id);
      const record = entities[collection].find((entry) => entry[idField] === id);
      if (!record) fail(`task ${task.task_id} references unknown ${idField}: ${id}`);
      if (record.company_id !== task.company_id) fail(`task ${task.task_id} ${idField} crosses company scope: ${id}`);
      if (type === 'account' && !task.channel_ids.includes(record.channel_id)) fail(`task ${task.task_id} account ${id} requires explicit channel scope ${record.channel_id}`);
    }
  }
  return task;
}

export function loadClientsRegistry(runtime) {
  const path = join(runtime, '00_control', 'clients-registry.json');
  const registry = readJson(path, 'clients-registry.json');
  if (registry.schema_version !== 1 || !Array.isArray(registry.entries)) fail('clients-registry.json schema is invalid');
  const ids = new Set();
  for (const entry of registry.entries) {
    assertClientId(entry?.client_id);
    if (ids.has(entry.client_id)) fail(`duplicate client_id in registry: ${entry.client_id}`);
    ids.add(entry.client_id);
    const expected = `10_clients/${entry.client_id}`;
    if (entry.path !== expected) fail(`client registry path mismatch for ${entry.client_id}: ${entry.path}`);
  }
  const clientsRoot = join(runtime, '10_clients');
  if (!existsSync(clientsRoot) || lstatSync(clientsRoot).isSymbolicLink()) fail('10_clients root is missing or is a symlink');
  const registered = new Set(registry.entries.map((entry) => entry.client_id));
  for (const entry of readdirSync(clientsRoot, { withFileTypes: true })) {
    if (entry.name === 'index.md') {
      if (!entry.isFile()) fail('10_clients/index.md must be a file');
      continue;
    }
    if (entry.isSymbolicLink()) fail(`client root entry must not be a symlink: ${entry.name}`);
    if (!entry.isDirectory()) fail(`unexpected non-directory in 10_clients: ${entry.name}`);
    assertClientId(entry.name);
    if (!registered.has(entry.name)) fail(`unregistered client directory: 10_clients/${entry.name}`);
  }
  return { path, registry };
}

export function getClient(runtime, clientId, { requireExists = true } = {}) {
  assertRuntime(runtime);
  assertNoSymlinks(runtime);
  assertClientId(clientId);
  const { registry } = loadClientsRegistry(runtime);
  const record = registry.entries.find((entry) => entry.client_id === clientId);
  if (!record) fail(`unregistered client_id: ${clientId}`);
  const clientsRoot = join(runtime, '10_clients');
  const target = resolve(runtime, record.path);
  if (!isInside(clientsRoot, target) || dirname(target) !== clientsRoot) fail(`client path escapes canonical root: ${record.path}`);
  if (requireExists && !existsSync(target)) fail(`registered client directory is missing: ${record.path}`);
  if (requireExists) {
    if (lstatSync(target).isSymbolicLink()) fail(`client directory must not be a symlink: ${record.path}`);
    const realClients = realpathSync(clientsRoot);
    const realTarget = realpathSync(target);
    if (!isInside(realClients, realTarget) || dirname(realTarget) !== realClients) fail(`client realpath escapes canonical root: ${record.path}`);
    const client = readJson(join(target, 'CLIENT.json'), `${clientId}/CLIENT.json`);
    if (client.client_id !== clientId) fail(`CLIENT.json client_id mismatch for ${clientId}`);
    if (client.schema_version !== 1) fail(`CLIENT.json schema_version mismatch for ${clientId}`);
    assertDisplayText(client.display_name, `${clientId} display_name`);
    assertEntityId('company', client.default_company_id);
    if (client.credential_policy !== 'opaque-reference-only' || client.external_actions_default !== 'deny') fail(`CLIENT.json safety policy mismatch for ${clientId}`);
    if (record.display_name !== client.display_name || record.status !== client.status) fail(`client registry projection mismatch for ${clientId}`);
    const { entities } = loadEntities(target);
    if (!entities.companies.some((entry) => entry.company_id === client.default_company_id)) fail(`CLIENT.json default_company_id is not registered for ${clientId}`);
  }
  return { record, path: target };
}

export function validateActiveContext(runtime, active, registry = loadClientsRegistry(runtime).registry) {
  if (active?.schema_version !== 1) fail('ACTIVE-CONTEXT.json schema_version must be 1');
  if (active.client_id === null) {
    if (active.company_id !== null || active.task_id !== null) fail('ACTIVE-CONTEXT without a client must not retain company_id or task_id');
    return null;
  }
  assertClientId(active.client_id);
  if (!registry.entries.some((entry) => entry.client_id === active.client_id)) fail(`ACTIVE-CONTEXT client is not registered: ${active.client_id}`);
  assertEntityId('company', active.company_id);
  assertTaskId(active.task_id);
  if (typeof active.authorized_by !== 'string' || !active.authorized_by.trim()) fail('ACTIVE-CONTEXT authorized_by is required for an active task');
  if (typeof active.authorized_at !== 'string' || !Number.isFinite(Date.parse(active.authorized_at))) fail('ACTIVE-CONTEXT authorized_at must be an ISO timestamp');
  if (active.expires_at !== null) {
    if (typeof active.expires_at !== 'string' || !Number.isFinite(Date.parse(active.expires_at))) fail('ACTIVE-CONTEXT expires_at must be null or an ISO timestamp');
    if (Date.parse(active.expires_at) <= Date.now()) fail(`ACTIVE-CONTEXT authorization expired at ${active.expires_at}`);
  }
  const { path: clientRoot } = getClient(runtime, active.client_id);
  const { entities } = loadEntities(clientRoot);
  if (!entities.companies.some((entry) => entry.company_id === active.company_id)) fail(`ACTIVE-CONTEXT company is not registered for ${active.client_id}: ${active.company_id}`);
  const { task } = taskProjection(runtime, active.client_id, active.task_id);
  if (task.company_id !== active.company_id) fail(`ACTIVE-CONTEXT company/task mismatch: ${active.company_id} vs ${task.company_id}`);
  validateTaskEntityScope(task, entities);
  return task;
}

export function copyWorkspaceTemplate(destination) {
  if (existsSync(destination)) fail(`refusing to overwrite existing runtime: ${destination}`);
  mkdirSync(dirname(destination), { recursive: true });
  cpSync(templateRoot, destination, { recursive: true, errorOnExist: true, force: false });
}

export function markdownFrontMatter(title, description, type = 'index') {
  const date = nowIso().slice(0, 10);
  return `---\ntitle: "${title.replaceAll('"', "'")}"\ndescription: "${description.replaceAll('"', "'")}"\ntype: "${type}"\nstatus: "Working"\nowner: "User"\ncreated: "${date}"\nlast_updated: "${date}"\nsources: ["local private runtime"]\nrelated: []\nvisibility: "private"\nredaction_status: "contains-private-data"\ncanonical_entry: "index.md"\n---\n`;
}

export function clientMarkdown(client) {
  return `---\ntitle: "${String(client.display_name).replaceAll('"', "'")}"\ndescription: "Private runtime entry for ${client.client_id}; current state is sourced from CLIENT.json and task files."\ntype: "client"\nstatus: "Working"\nowner: "User"\ncreated: "${client.created_at.slice(0, 10)}"\nlast_updated: "${client.updated_at.slice(0, 10)}"\nsources: ["CLIENT.json"]\nrelated: ["CLIENT.json", "00_control/entities.json", "30_tasks/index.md", "80_activity/index.md"]\nvisibility: "private"\nredaction_status: "contains-private-data"\ncanonical_entry: "README.md"\n---\n# ${client.display_name}\n\n- client_id: \`${client.client_id}\`\n- default_company_id: \`${client.default_company_id}\`\n- status: \`${client.status}\`\n\n客户状态只读 [CLIENT.json](CLIENT.json)，公司、产品、渠道和账号状态只读 [entities.json](00_control/entities.json)。任务入口见 [30_tasks/index.md](30_tasks/index.md)。\n`;
}

export function renderClientsIndex(runtime, registry) {
  const lines = [markdownFrontMatter('Runtime Clients Index', 'Generated client navigation; machine state remains in clients-registry.json.'), '# Clients', '', '<!-- GENERATED:START -->'];
  if (!registry.entries.length) lines.push('尚无客户。');
  for (const entry of [...registry.entries].sort((a, b) => compareCodePoint(a.client_id, b.client_id))) lines.push(`- [${entry.display_name}](${entry.client_id}/README.md) — \`${entry.client_id}\` — ${entry.status}`);
  lines.push('<!-- GENERATED:END -->', '');
  return lines.join('\n');
}

export function renderControlIndex(runtime, registry, active, tasks) {
  const lines = [markdownFrontMatter('Runtime Control Index', 'Generated navigation for active context, clients, tasks, core lock, updates and search catalog.'), '# Runtime Control', '', '<!-- GENERATED:START -->', `- Active client: \`${active.client_id ?? 'none'}\``, `- Active task: \`${active.task_id ?? 'none'}\``, `- Registered clients: ${registry.entries.length}`, `- Task registry events: ${tasks.length}`, '- [Clients](../10_clients/index.md)', '- [ACTIVE-CONTEXT.json](ACTIVE-CONTEXT.json)', '- [CORE-LOCK.json](CORE-LOCK.json)', '- [clients-registry.json](clients-registry.json)', '- [task-registry.jsonl](task-registry.jsonl)', '- [search-catalog.jsonl](search-catalog.jsonl)', '<!-- GENERATED:END -->', ''];
  return lines.join('\n');
}

export function renderTaskIndex(client, tasks) {
  const lines = [markdownFrontMatter(`${client.display_name} Tasks`, 'Generated task navigation; TASK.json and HANDOFF.md remain the task truth.'), '# Tasks', '', '<!-- GENERATED:START -->'];
  if (!tasks.length) lines.push('尚无任务。');
  for (const task of [...tasks].sort((a, b) => compareCodePoint(a.task_id, b.task_id))) {
    lines.push(`- [${task.title}](${task.task_id}/README.md) — \`${task.task_id}\` — ${task.status} — company \`${task.company_id}\``);
  }
  lines.push('<!-- GENERATED:END -->', '');
  return lines.join('\n');
}

export function readJsonl(path, label = path) {
  if (!existsSync(path)) return [];
  return readFileSync(path, 'utf8').split(/\r?\n/).filter(Boolean).map((line, index) => {
    try { return JSON.parse(line); }
    catch (error) { fail(`${label} line ${index + 1} is invalid JSON: ${error.message}`); }
  });
}

export function appendJsonl(path, value) {
  const existing = existsSync(path) ? readFileSync(path, 'utf8') : '';
  writeTextAtomic(path, `${existing}${JSON.stringify(value)}\n`);
}

export function catalogRows(runtime, registry) {
  const rows = [];
  for (const record of registry.entries) {
    const { path: clientRoot } = getClient(runtime, record.client_id);
    for (const entry of walk(clientRoot)) {
      if (entry.type !== 'file' || !TEXT_EXTENSIONS.has(extname(entry.path).toLowerCase())) continue;
      const rel = relative(runtime, entry.path).split(sep).join('/');
      if (!rel.startsWith(`10_clients/${record.client_id}/`)) fail(`catalog source escaped client scope: ${rel}`);
      const stat = statSync(entry.path);
      if (stat.size > MAX_INDEX_FILE_BYTES) fail(`text file exceeds ${MAX_INDEX_FILE_BYTES} byte catalog limit: ${rel}`);
      rows.push({ schema_version: 1, client_id: record.client_id, path: rel, kind: extname(entry.path).slice(1) || 'text', size: stat.size, mtime_ms: Math.trunc(stat.mtimeMs) });
    }
  }
  return rows.sort((a, b) => compareCodePoint(a.path, b.path));
}

export function validateCatalogRows(runtime, registry, rows, { requireCurrent = false } = {}) {
  const registered = new Set(registry.entries.map((entry) => entry.client_id));
  const seenPaths = new Set();
  for (const row of rows) {
    if (row?.schema_version !== 1) fail('catalog row schema_version must be 1');
    assertClientId(row.client_id);
    if (!registered.has(row.client_id)) fail(`catalog row references unregistered client: ${row.client_id}`);
    const { path: clientRoot } = getClient(runtime, row.client_id);
    if (typeof row.path !== 'string' || row.path.startsWith('/') || row.path.split('/').some((part) => part === '' || part === '.' || part === '..')) fail(`catalog path is non-portable: ${row.path}`);
    const expectedPrefix = `10_clients/${row.client_id}/`;
    const target = resolve(runtime, row.path);
    if (!row.path.startsWith(expectedPrefix) || !isInside(clientRoot, target)) fail(`catalog path escapes declared client scope: ${row.client_id} -> ${row.path}`);
    if (!existsSync(target)) fail(`catalog path is missing: ${row.path}`);
    if (lstatSync(target).isSymbolicLink()) fail(`catalog target must not be a symlink: ${row.path}`);
    const realClient = realpathSync(clientRoot);
    const realTarget = realpathSync(target);
    if (!isInside(realClient, realTarget)) fail(`catalog target realpath escapes client scope: ${row.path}`);
    const stat = statSync(target);
    if (!stat.isFile()) fail(`catalog target is not a file: ${row.path}`);
    if (!TEXT_EXTENSIONS.has(extname(target).toLowerCase())) fail(`catalog target extension is not allowlisted: ${row.path}`);
    if (stat.size > MAX_INDEX_FILE_BYTES) fail(`catalog target exceeds ${MAX_INDEX_FILE_BYTES} byte limit: ${row.path}`);
    if (!Number.isInteger(row.size) || row.size !== stat.size) fail(`catalog size is stale for ${row.path}`);
    if (!Number.isInteger(row.mtime_ms) || row.mtime_ms !== Math.trunc(stat.mtimeMs)) fail(`catalog mtime is stale for ${row.path}`);
    if (seenPaths.has(row.path)) fail(`duplicate catalog path: ${row.path}`);
    seenPaths.add(row.path);
  }
  if (requireCurrent) {
    const expected = catalogRows(runtime, registry);
    if (JSON.stringify(rows) !== JSON.stringify(expected)) fail('search catalog is stale, incomplete, reordered, or contains extra rows; run sync-runtime-indexes.mjs');
  }
  return rows;
}

export function taskProjection(runtime, clientId, taskId) {
  const { path: clientRoot } = getClient(runtime, clientId);
  assertTaskId(taskId);
  const taskRoot = join(clientRoot, '30_tasks', taskId);
  if (!existsSync(taskRoot)) fail(`task directory does not exist: ${taskId}`);
  if (lstatSync(taskRoot).isSymbolicLink()) fail(`task directory must not be a symlink: ${taskId}`);
  for (const required of ['TASK.json', 'README.md', 'HANDOFF.md']) {
    const path = join(taskRoot, required);
    if (!existsSync(path) || lstatSync(path).isSymbolicLink() || !statSync(path).isFile()) fail(`task continuation file is missing or unsafe: ${clientId}/${taskId}/${required}`);
  }
  const task = readJson(join(taskRoot, 'TASK.json'), `${taskId}/TASK.json`);
  if (task.client_id !== clientId || task.task_id !== taskId) fail(`TASK.json scope mismatch: ${clientId}/${taskId}`);
  return { taskRoot, task };
}

export function listClientTasks(runtime, clientId) {
  const { path: clientRoot } = getClient(runtime, clientId);
  const tasksRoot = join(clientRoot, '30_tasks');
  const tasks = [];
  for (const entry of readdirSync(tasksRoot, { withFileTypes: true })) {
    if (entry.name === 'index.md') continue;
    if (entry.isSymbolicLink()) fail(`task entry must not be a symlink: ${clientId}/${entry.name}`);
    if (!entry.isDirectory()) fail(`unexpected non-directory in task root: ${clientId}/${entry.name}`);
    assertTaskId(entry.name);
    const { task } = taskProjection(runtime, clientId, entry.name);
    const { entities } = loadEntities(clientRoot);
    validateTaskEntityScope(task, entities);
    tasks.push(task);
  }
  return tasks.sort((a, b) => compareCodePoint(a.task_id, b.task_id));
}

export function validateTaskRegistry(runtime, registry, events) {
  const created = new Set();
  for (const event of events) {
    if (event?.schema_version !== 1 || event.event !== 'task-created') fail(`unsupported task registry event: ${event?.event ?? 'missing'}`);
    assertClientId(event.client_id);
    assertTaskId(event.task_id);
    if (!registry.entries.some((entry) => entry.client_id === event.client_id)) fail(`task registry references unregistered client: ${event.client_id}`);
    const key = `${event.client_id}/${event.task_id}`;
    if (created.has(key)) fail(`duplicate task-created event: ${key}`);
    created.add(key);
    const expectedPath = `10_clients/${event.client_id}/30_tasks/${event.task_id}/TASK.json`;
    if (event.task_path !== expectedPath) fail(`task registry path mismatch for ${key}: ${event.task_path}`);
    const { task } = taskProjection(runtime, event.client_id, event.task_id);
    const { path: clientRoot } = getClient(runtime, event.client_id);
    const { entities } = loadEntities(clientRoot);
    validateTaskEntityScope(task, entities);
  }
  for (const client of registry.entries) {
    for (const task of listClientTasks(runtime, client.client_id)) {
      const key = `${client.client_id}/${task.task_id}`;
      if (!created.has(key)) fail(`task directory has no task-created registry event: ${key}`);
    }
  }
  return events;
}

export function cleanup(path) { if (existsSync(path)) rmSync(path, { recursive: true, force: true }); }
