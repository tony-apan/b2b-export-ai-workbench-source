import test from 'node:test';
import assert from 'node:assert/strict';
import { cp, mkdtemp, readFile, rm, symlink, writeFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { extractEsmExportBindings, validateInterfaceRegistry } from './scripts/validate-interface-registry.mjs';
import { renderInterfaceIndex } from './scripts/build-interface-index.mjs';

const loadRegistry = () => readFile(new URL('./interface-registry.json', import.meta.url), 'utf8').then(JSON.parse);
const loadPackage = () => readFile(new URL('./package.json', import.meta.url), 'utf8').then(JSON.parse);

test('Registry schema, references, safety declarations, source bindings, and package surface validate', async () => {
  const [result, registry, pkg] = await Promise.all([
    validateInterfaceRegistry(), loadRegistry(), loadPackage(),
  ]);
  assert.deepEqual(result.errors, []);
  assert.equal(result.ok, true);
  assert.deepEqual(result.summary, {
    interfaces: 108,
    esmBindings: 104,
    cliBindings: 4,
    canonical: 19,
    blocked: 4,
    referenceScope: 'source',
  });
  assert.deepEqual(pkg.dependencies, { acorn: '8.15.0', ajv: '8.20.0', sharp: '0.35.3' });
  assert.equal(pkg.devDependencies, undefined);
  const packageFiles = new Set(pkg.files);
  for (const item of registry.interfaces) {
    assert.ok(item.contract_refs.some((ref) => ref.availability === 'packaged' && packageFiles.has(ref.path)), item.interface_id);
    for (const ref of item.contract_refs) {
      assert.equal(packageFiles.has(ref.path), ref.availability === 'packaged', `${item.interface_id}: ${ref.path}`);
    }
    assert.ok(item.test_refs.every((ref) => ref.availability === 'source_only' && !packageFiles.has(ref.path)), item.interface_id);
    for (const ref of item.evidence.refs) {
      assert.equal(packageFiles.has(ref.path), ref.availability === 'packaged', `${item.interface_id}: ${ref.path}`);
    }
  }
});

test('runtime package closure rejects non-literal dynamic imports and unpackaged local imports', async () => {
  const sourceRoot = fileURLToPath(new URL('.', import.meta.url));
  const sourceNodeModules = join(sourceRoot, 'node_modules');
  const temporaryParent = await mkdtemp(join(tmpdir(), 'allincms-registry-negative-'));
  const temporaryAdapter = join(temporaryParent, 'adapter');
  try {
    await cp(sourceRoot, temporaryAdapter, {
      recursive: true,
      filter: (source) => source !== sourceNodeModules && !source.startsWith(`${sourceNodeModules}/`),
    });
    await symlink(sourceNodeModules, join(temporaryAdapter, 'node_modules'), 'dir');
    await writeFile(
      join(temporaryAdapter, 'verify-media.mjs'),
      `import './not-packaged.mjs';
const moduleName = 'sharp';
await import(moduleName);
`,
    );
    const check = spawnSync(process.execPath, ['scripts/validate-interface-registry.mjs'], {
      cwd: temporaryAdapter,
      encoding: 'utf8',
    });
    assert.equal(check.status, 1, `${check.stdout}\n${check.stderr}`);
    assert.match(check.stderr, /non-literal dynamic import\(s\); runtime closure cannot be proven/);
    assert.match(check.stderr, /imports local module not present in package files: \.\/not-packaged\.mjs/);
  } finally {
    await rm(temporaryParent, { recursive: true, force: true });
  }
});

test('Registry validator fails closed on runtime-distribution and capability-route tampering', async () => {
  const sourceRoot = fileURLToPath(new URL('.', import.meta.url));
  const sourceNodeModules = join(sourceRoot, 'node_modules');
  const temporaryParent = await mkdtemp(join(tmpdir(), 'allincms-registry-tamper-'));
  const temporaryAdapter = join(temporaryParent, 'adapter');
  try {
    await cp(sourceRoot, temporaryAdapter, {
      recursive: true,
      filter: (source) => source !== sourceNodeModules && !source.startsWith(`${sourceNodeModules}/`),
    });
    await symlink(sourceNodeModules, join(temporaryAdapter, 'node_modules'), 'dir');
    const registryPath = join(temporaryAdapter, 'interface-registry.json');
    const registry = JSON.parse(await readFile(registryPath, 'utf8'));
    registry.interfaces.find((item) => item.interface_id === 'allincms.content-run-controller.run-allin-cms-content-plan').runtime_availability = 'packaged';
    const deleteRoute = registry.capability_routes.find((route) => route.capability_id === 'allincms.article.delete');
    deleteRoute.availability = 'canonical';
    deleteRoute.execution_gate = 'fresh_live_verified_current_deployment';
    deleteRoute.execution_surface = 'full_source_checkout';
    deleteRoute.default_interface_id = 'allincms.article-operations.save-post-draft';
    deleteRoute.controller_interface_id = 'allincms.content-run-controller.validate-allin-cms-live-run-evidence';
    registry.capability_routes.push({
      ...structuredClone(registry.capability_routes.find((route) => route.capability_id === 'allincms.site.discover')),
      capability_id: 'allincms.site.publish',
      action: 'publish',
    });
    await writeFile(registryPath, `${JSON.stringify(registry, null, 2)}\n`);
    const check = spawnSync(process.execPath, ['scripts/validate-interface-registry.mjs'], {
      cwd: temporaryAdapter,
      encoding: 'utf8',
    });
    assert.equal(check.status, 1, `${check.stdout}\n${check.stderr}`);
    assert.match(check.stderr, /runtime_availability=packaged; expected source_only/);
    assert.match(check.stderr, /executable mutation route must use the canonical serial content controller/);
    assert.match(check.stderr, /unexpected capability route: site:publish/);
  } finally {
    await rm(temporaryParent, { recursive: true, force: true });
  }
});

test('verification contract and executable mutation routes reject profile and check drift', async () => {
  const sourceRoot = fileURLToPath(new URL('.', import.meta.url));
  const sourceNodeModules = join(sourceRoot, 'node_modules');
  const temporaryParent = await mkdtemp(join(tmpdir(), 'allincms-verification-contract-tamper-'));
  const temporaryAdapter = join(temporaryParent, 'adapter');
  try {
    await cp(sourceRoot, temporaryAdapter, {
      recursive: true,
      filter: (source) => source !== sourceNodeModules && !source.startsWith(`${sourceNodeModules}/`),
    });
    await symlink(sourceNodeModules, join(temporaryAdapter, 'node_modules'), 'dir');
    const registryPath = join(temporaryAdapter, 'interface-registry.json');
    const contractPath = join(temporaryAdapter, 'verification-evidence-contract.json');
    const baselineRegistry = JSON.parse(await readFile(registryPath, 'utf8'));
    const baselineContract = JSON.parse(await readFile(contractPath, 'utf8'));
    const cases = [
      {
        label: 'route drops required check',
        mutate(registry) {
          registry.capability_routes.find((route) => route.capability_id === 'allincms.article.update').verification_requirements.pop();
        },
        pattern: /verification requirements must exactly match its verification profile/,
      },
      {
        label: 'profile adds required check',
        mutate(_registry, contract) {
          contract.profiles.find((profile) => profile.capability_id === 'allincms.article.update').required_check_ids.push('article.public_url');
        },
        pattern: /verification requirements must exactly match its verification profile/,
      },
      {
        label: 'profile references unknown check',
        mutate(_registry, contract) {
          contract.profiles.find((profile) => profile.capability_id === 'allincms.article.update').required_check_ids.push('unknown.synthetic.check');
        },
        pattern: /references unknown check unknown.synthetic.check/,
      },
      {
        label: 'duplicate check ID',
        mutate(_registry, contract) {
          contract.check_definitions.push(structuredClone(contract.check_definitions[0]));
        },
        pattern: /duplicate verification check_id/,
      },
      {
        label: 'duplicate profile capability ID',
        mutate(_registry, contract) {
          contract.profiles.push(structuredClone(contract.profiles[0]));
        },
        pattern: /duplicate verification profile capability_id/,
      },
      {
        label: 'missing read-only verification profile',
        mutate(_registry, contract) {
          contract.read_only_profiles = contract.read_only_profiles.filter((profile) => profile.intent !== 'noop');
        },
        pattern: /missing read-only verification profile: noop/,
      },
      {
        label: 'duplicate read-only verification intent',
        mutate(_registry, contract) {
          contract.read_only_profiles.push(structuredClone(contract.read_only_profiles[0]));
        },
        pattern: /duplicate read-only verification profile intent/,
      },
      {
        label: 'read-only verification references unknown check',
        mutate(_registry, contract) {
          contract.read_only_profiles.find((profile) => profile.intent === 'explore').required_check_ids.push('unknown.read-only.check');
        },
        pattern: /read-only verification profile explore references unknown check unknown.read-only.check/,
      },
    ];
    for (const item of cases) {
      const registry = structuredClone(baselineRegistry);
      const contract = structuredClone(baselineContract);
      item.mutate(registry, contract);
      await writeFile(registryPath, `${JSON.stringify(registry, null, 2)}\n`);
      await writeFile(contractPath, `${JSON.stringify(contract, null, 2)}\n`);
      const check = spawnSync(process.execPath, ['scripts/validate-interface-registry.mjs'], {
        cwd: temporaryAdapter,
        encoding: 'utf8',
      });
      assert.equal(check.status, 1, `${item.label}\n${check.stdout}\n${check.stderr}`);
      assert.match(check.stderr, item.pattern, item.label);
    }
  } finally {
    await rm(temporaryParent, { recursive: true, force: true });
  }
});

test('every current ESM export binding is registered exactly once and CLI is separate', async () => {
  const [registry, exports] = await Promise.all([loadRegistry(), extractEsmExportBindings()]);
  const bindings = registry.interfaces.flatMap((item) => item.bindings.map((binding) => ({ id: item.interface_id, ...binding })));
  const esm = bindings.filter((binding) => binding.type === 'esm_export');
  const cli = bindings.filter((binding) => binding.type === 'cli');
  assert.equal(new Set(esm.map((binding) => `${binding.module}:${binding.export_name}`)).size, esm.length);
  assert.deepEqual(
    esm.map((binding) => `${binding.module}:${binding.export_name}`).sort(),
    exports.map((binding) => `${binding.module}:${binding.export_name}`).sort(),
  );
  assert.deepEqual(cli.map((binding) => binding.command).sort(), [
    'node verify-media.mjs',
    'npm run interfaces:index',
    'npm run interfaces:index:check',
    'npm run interfaces:validate',
  ]);
});

test('source-only controller bindings are registered without pretending to be in the minimal npm package', async () => {
  const [registry, pkg, exports] = await Promise.all([loadRegistry(), loadPackage(), extractEsmExportBindings()]);
  assert.deepEqual(registry.source_only_modules, ['content-run-controller.mjs']);
  assert.deepEqual(pkg.source_only_modules, registry.source_only_modules);
  assert.ok(!pkg.files.includes('content-run-controller.mjs'));
  assert.ok(!pkg.files.includes('live-run-evidence.schema.json'));
  assert.ok(exports.some((binding) => binding.module === 'content-run-controller.mjs' && binding.export_name === 'runAllinCmsContentPlan'));
  assert.ok(exports.some((binding) => binding.module === 'content-run-controller.mjs' && binding.export_name === 'validateAllinCmsLiveRunEvidence'));
  const runEntries = registry.interfaces.filter((item) => item.domain === 'run');
  assert.deepEqual(runEntries.map((item) => item.display_name).sort(), ['runAllinCmsContentPlan', 'validateAllinCmsLiveRunEvidence']);
  assert.ok(runEntries.every((item) => item.bindings.every((binding) => binding.module === 'content-run-controller.mjs')));
  assert.ok(runEntries.every((item) => item.contract_refs.some((ref) => ref.availability === 'source_only')));
  assert.ok(runEntries.every((item) => item.runtime_availability === 'source_only'));
  assert.ok(registry.interfaces.filter((item) => item.domain !== 'run').every((item) => item.runtime_availability === 'packaged'));
});

test('capability routes are complete, executable routes use the serial controller, and product stays exploration-only', async () => {
  const registry = await loadRegistry();
  const routes = new Map(registry.capability_routes.map((route) => [`${route.entity_type}:${route.action}`, route]));
  assert.equal(routes.size, 22);
  for (const key of [
    'site:discover', 'site:create', 'site:delete',
    'category:create', 'category:update', 'category:delete',
    'tag:create', 'tag:update', 'tag:delete',
    'media:create', 'media:update', 'media:delete',
    'article:create', 'article:update', 'article:publish', 'article:unpublish', 'article:delete',
    'product:discover', 'product:create', 'product:update', 'product:publish', 'product:delete',
  ]) assert.ok(routes.has(key), key);
  const controllerId = 'allincms.content-run-controller.run-allin-cms-content-plan';
  const exactDefaults = {
    'site:discover': 'allincms.workspace-preflight.run-allin-cms-workspace-preflight',
    'site:create': 'allincms.workspace-preflight.build-allin-cms-create-site-action-request',
    'category:create': 'allincms.article-operations.create-post-category',
    'category:update': 'allincms.article-operations.update-post-category',
    'tag:create': 'allincms.article-operations.create-post-tag',
    'tag:update': 'allincms.article-operations.update-post-tag',
    'media:create': 'allincms.upload-media-browser.upload-allin-cms-media-serial',
    'media:update': 'allincms.upload-media-browser.update-allin-cms-media-metadata-direct',
    'article:create': 'allincms.article-operations.create-post-draft',
    'article:update': 'allincms.article-operations.save-post-draft',
    'article:publish': 'allincms.article-operations.publish-post',
  };
  for (const [key, interfaceId] of Object.entries(exactDefaults)) assert.equal(routes.get(key).default_interface_id, interfaceId, key);
  for (const route of registry.capability_routes.filter((item) => item.execution_gate === 'fresh_live_verified_current_deployment')) {
    assert.equal(route.controller_interface_id, controllerId, route.capability_id);
    assert.ok(route.default_interface_id, route.capability_id);
    assert.equal(route.execution_surface, 'full_source_checkout', route.capability_id);
  }
  assert.equal(routes.get('site:discover').execution_surface, 'minimal_adapter');
  assert.equal(routes.get('site:create').availability, 'blocked');
  assert.equal(routes.get('article:create').availability, 'blocked');
  assert.equal(routes.get('media:update').availability, 'blocked');
  for (const key of ['site:delete', 'category:delete', 'tag:delete', 'media:delete', 'article:unpublish', 'article:delete']) {
    const route = routes.get(key);
    assert.equal(route.availability, 'blocked', key);
    assert.equal(route.execution_gate, 'blocked', key);
    assert.equal(route.execution_surface, 'none', key);
    assert.equal(route.controller_interface_id, null, key);
  }
  for (const route of registry.capability_routes.filter((item) => item.entity_type === 'product')) {
    assert.equal(route.availability, 'exploration_only');
    assert.equal(route.execution_gate, 'exploration_only');
    assert.equal(route.execution_surface, 'none');
    assert.equal(route.default_interface_id, null);
    assert.equal(route.controller_interface_id, null);
  }
  for (const route of registry.capability_routes.filter((item) => ['blocked', 'exploration_only'].includes(item.availability))) {
    assert.equal(route.execution_surface, 'none', route.capability_id);
  }
});

test('article format re-exports are explicit aliases and module-scoped _internal bindings stay separate', async () => {
  const registry = await loadRegistry();
  const aliases = registry.interfaces.filter((item) => item.alias_of);
  assert.equal(aliases.length, 9);
  assert.ok(aliases.every((item) => item.bindings.every((binding) => binding.role === 'reexport')));
  assert.ok(aliases.every((item) => item.alias_of.startsWith('allincms.article-content-formats.')));
  const internals = registry.interfaces.filter((item) => item.bindings.some((binding) => binding.export_name === '_internal'));
  assert.equal(internals.length, 2);
  assert.equal(new Set(internals.map((item) => item.interface_id)).size, 2);
  assert.ok(internals.every((item) => item.exposure === 'internal'));
});

test('blocked and compatibility interfaces cannot appear as canonical defaults', async () => {
  const registry = await loadRegistry();
  const blocked = registry.interfaces.filter((item) => item.exposure === 'blocked');
  assert.deepEqual(blocked.map((item) => item.display_name).sort(), [
    'buildAllinCmsCreateSiteActionRequest',
    'createPostDraft',
    'deleteAllinCmsMediaDirect',
    'updateAllinCmsMediaMetadataDirect',
  ]);
  assert.ok(blocked.every((item) => item.blocked_reason));
  assert.ok(registry.interfaces.filter((item) => item.exposure === 'canonical').every((item) => !item.alias_of));
  const siteRequestBuilder = blocked.find((item) => item.display_name === 'buildAllinCmsCreateSiteActionRequest');
  assert.equal(siteRequestBuilder.kind, 'builder');
  assert.equal(siteRequestBuilder.access, 'transform');
  assert.equal(siteRequestBuilder.safety.mutation, false);
  assert.equal(siteRequestBuilder.safety.network_access, 'none');
  assert.match(siteRequestBuilder.io_contract.output, /未发送/);
});

test('remote and local mutation interfaces declare their distinct safety semantics', async () => {
  const registry = await loadRegistry();
  for (const item of registry.interfaces.filter((candidate) => candidate.safety.mutation && candidate.safety.network_access === 'mutation')) {
    assert.equal(item.safety.authorization.required, true, item.interface_id);
    assert.notEqual(item.safety.readback, 'not_applicable', item.interface_id);
    assert.ok(item.safety.automatic_retry, item.interface_id);
    assert.ok(item.safety.ambiguous_result, item.interface_id);
    assert.ok(item.safety.request_may_have_succeeded, item.interface_id);
  }
  const localIndexWrite = registry.interfaces.find((item) => item.interface_id === 'allincms.registry.build-index-cli');
  assert.equal(localIndexWrite.safety.mutation, true);
  assert.equal(localIndexWrite.safety.network_access, 'none');
  assert.equal(localIndexWrite.safety.authorization.required, false);
  assert.equal(localIndexWrite.safety.idempotency, 'idempotent');
  assert.equal(localIndexWrite.safety.request_may_have_succeeded, 'false');
  assert.equal(localIndexWrite.safety.ambiguous_result, 'stop_manual');
  assert.equal(localIndexWrite.safety.readback, 'recommended');
});

test('generated human/AI index is deterministic, current, and contains every interface ID once', async () => {
  const registry = await loadRegistry();
  const first = renderInterfaceIndex(registry);
  const second = renderInterfaceIndex(structuredClone(registry));
  assert.equal(first, second);
  const current = await readFile(new URL('./INTERFACE-INDEX.md', import.meta.url), 'utf8');
  assert.equal(current, first);
  assert.match(current, /^---\ntitle: "AllinCMS Interface Index"\n/);
  assert.match(current, /\nwhen_to_read: "需要按接口名、导出名、领域、暴露层级或生命周期查询 AllinCMS Adapter 能力与限制时。"\n/);
  assert.match(current, /\nredaction_status: "safe-to-publish"\n---\n<!-- GENERATED FILE/);
  const bindings = registry.interfaces.flatMap((item) => item.bindings);
  const esmCount = bindings.filter((binding) => binding.type === 'esm_export').length;
  const cliCount = bindings.filter((binding) => binding.type === 'cli').length;
  assert.match(current, new RegExp(`固化范围：${registry.interfaces.length} 个接口记录（${esmCount} 个 ESM export binding \\+ ${cliCount} 个 CLI）`));
  const interfaceDirectory = current.split('## 接口目录\n', 2)[1].split('## 证据声明\n', 1)[0];
  for (const item of registry.interfaces) {
    assert.equal(interfaceDirectory.split(`\`${item.interface_id}\``).length - 1, 1, item.interface_id);
  }
  for (const route of registry.capability_routes) {
    assert.equal(current.split(`\`${route.capability_id}\``).length - 1, 1, route.capability_id);
  }
  const check = spawnSync(process.execPath, ['scripts/build-interface-index.mjs', '--check'], { cwd: new URL('.', import.meta.url), encoding: 'utf8' });
  assert.equal(check.status, 0, `${check.stdout}\n${check.stderr}`);
});
