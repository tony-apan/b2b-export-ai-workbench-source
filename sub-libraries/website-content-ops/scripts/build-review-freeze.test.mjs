import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { chmodSync, copyFileSync, existsSync, lstatSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const SOURCE_BUILDER = join(dirname(fileURLToPath(import.meta.url)), 'build-review-freeze.mjs');

function write(path, content) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content);
}

function makeWritable(path) {
  let stat;
  try {
    stat = lstatSync(path);
  } catch {
    return;
  }
  if (stat.isSymbolicLink() || stat.isFile()) {
    if (!stat.isSymbolicLink()) chmodSync(path, 0o644);
    return;
  }
  chmodSync(path, 0o755);
  for (const entry of readdirSync(path)) makeWritable(join(path, entry));
}

function makeFixture(t) {
  const base = mkdtempSync(join(tmpdir(), 'wco-review-freeze-test-'));
  t.after(() => {
    makeWritable(base);
    rmSync(base, { recursive: true, force: true });
  });
  const repo = join(base, 'repo');
  const scope = join(repo, 'sub-libraries/website-content-ops');
  const scripts = join(scope, 'scripts');
  const controls = join(base, 'controls');
  const outputs = join(base, 'outputs');
  mkdirSync(scripts, { recursive: true });
  mkdirSync(controls, { recursive: true });
  mkdirSync(outputs, { recursive: true });
  copyFileSync(SOURCE_BUILDER, join(scripts, 'build-review-freeze.mjs'));
  return { base, repo, scope, scripts, controls, outputs, builder: join(scripts, 'build-review-freeze.mjs') };
}

function commandArgs(fixture, {
  roots,
  resources = [],
  directResources = [],
  freezeId = 'TEST-FREEZE',
  generatedAt = '2026-08-02T00:00:00.000Z',
  sha = true,
} = {}) {
  const rootsFile = join(fixture.controls, 'roots.txt');
  const resourcesFile = join(fixture.controls, 'resources.txt');
  writeFileSync(rootsFile, `${roots.join('\n')}\n`);
  writeFileSync(resourcesFile, `${resources.join('\n')}\n`);
  const args = [
    fixture.builder,
    '--freeze-id', freezeId,
    '--generated-at', generatedAt,
    '--manifest', join(fixture.outputs, 'manifest.json'),
    '--freeze-root', join(fixture.outputs, 'freeze-root'),
    '--file-list', join(fixture.outputs, 'files.txt'),
    '--roots-file', rootsFile,
    '--resources-file', resourcesFile,
  ];
  if (sha) args.push('--sha-file', join(fixture.outputs, 'manifest.sha256'));
  for (const resource of directResources) args.push('--resource-file', resource);
  return args;
}

function run(fixture, config) {
  return spawnSync(process.execPath, commandArgs(fixture, config), {
    cwd: fixture.base,
    encoding: 'utf8',
    timeout: 20_000,
    maxBuffer: 4 * 1024 * 1024,
  });
}

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function assertBlockedWithoutArtifacts(fixture, result, branch) {
  assert.notEqual(result.status, 0);
  assert.doesNotMatch(result.stdout, /REVIEW_FREEZE_PASS/);
  assert.match(result.stderr, branch);
  for (const path of [
    join(fixture.outputs, 'freeze-root'),
    join(fixture.outputs, 'manifest.json'),
    join(fixture.outputs, 'files.txt'),
    join(fixture.outputs, 'manifest.sha256'),
  ]) assert.equal(existsSync(path), false, `blocked build must not leave output: ${path}`);
  assert.deepEqual(readdirSync(fixture.outputs), []);
}

function walkFiles(root, prefix = '') {
  const files = [];
  for (const entry of readdirSync(root, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
    const absolute = join(root, entry.name);
    const rel = prefix ? `${prefix}/${entry.name}` : entry.name;
    const stat = lstatSync(absolute);
    assert.equal(stat.isSymbolicLink(), false, `unexpected symlink: ${rel}`);
    if (stat.isDirectory()) files.push(...walkFiles(absolute, rel));
    else {
      assert.equal(stat.isFile(), true, `unexpected non-regular entry: ${rel}`);
      files.push(rel);
    }
  }
  return files;
}

test('syntax-level closure covers multiline static import, export-from, literal dynamic import, exact edges, and exact copy', (t) => {
  const fixture = makeFixture(t);
  write(join(fixture.scripts, 'root.mjs'), `import {\n  alpha\n} from './multi.mjs';\nexport { beta } from './exported.mjs';\nexport async function load() { return import('./dynamic.mjs'); }\n`);
  write(join(fixture.scripts, 'multi.mjs'), `export { nested as alpha } from './nested.mjs';\n`);
  write(join(fixture.scripts, 'nested.mjs'), `export const nested = 1;\n`);
  write(join(fixture.scripts, 'exported.mjs'), `export const beta = 2;\n`);
  write(join(fixture.scripts, 'dynamic.mjs'), `export const dynamic = 3;\n`);
  write(join(fixture.repo, 'mother-harness.mjs'), `export const harness = true;\n`);
  write(join(fixture.scope, 'README.md'), `fixture resource\n`);
  write(join(fixture.scope, 'runtime.json'), `{ \"fixture\": true }\n`);
  write(join(fixture.scope, 'DIRECT.txt'), `direct resource\n`);

  const roots = [
    'sub-libraries/website-content-ops/scripts/root.mjs',
    'sub-libraries/website-content-ops/scripts/build-review-freeze.mjs',
    'mother-harness.mjs',
  ];
  const result = run(fixture, {
    roots,
    resources: ['sub-libraries/website-content-ops/README.md', 'sub-libraries/website-content-ops/runtime.json'],
    directResources: ['sub-libraries/website-content-ops/DIRECT.txt'],
  });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
  assert.match(result.stdout, /REVIEW_FREEZE_PASS/);

  const manifestPath = join(fixture.outputs, 'manifest.json');
  const manifestBytes = readFileSync(manifestPath);
  const manifest = JSON.parse(manifestBytes);
  assert.equal(manifest.schema_version, 2);
  assert.equal(manifest.generated_at, '2026-08-02T00:00:00.000Z');
  assert.deepEqual(manifest.source_controls.roots_file.entries, roots);
  assert.deepEqual(manifest.source_controls.resources_file.entries, [
    'sub-libraries/website-content-ops/README.md',
    'sub-libraries/website-content-ops/runtime.json',
  ]);
  assert.deepEqual(manifest.source_controls.direct_resources, ['sub-libraries/website-content-ops/DIRECT.txt']);
  const expectedEdges = [
    { importer: 'sub-libraries/website-content-ops/scripts/multi.mjs', specifier: './nested.mjs', target: 'sub-libraries/website-content-ops/scripts/nested.mjs', kind: 'static' },
    { importer: 'sub-libraries/website-content-ops/scripts/root.mjs', specifier: './dynamic.mjs', target: 'sub-libraries/website-content-ops/scripts/dynamic.mjs', kind: 'dynamic-literal' },
    { importer: 'sub-libraries/website-content-ops/scripts/root.mjs', specifier: './exported.mjs', target: 'sub-libraries/website-content-ops/scripts/exported.mjs', kind: 'static' },
    { importer: 'sub-libraries/website-content-ops/scripts/root.mjs', specifier: './multi.mjs', target: 'sub-libraries/website-content-ops/scripts/multi.mjs', kind: 'static' },
  ].sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));
  assert.deepEqual(manifest.dependency_closure.edges, expectedEdges);
  assert.equal(manifest.dependency_closure.local_dependency_edges, 4);

  const manifestPaths = manifest.files.map((record) => record.path).sort();
  const frozenPaths = walkFiles(join(fixture.outputs, 'freeze-root')).sort();
  assert.deepEqual(frozenPaths, manifestPaths);
  assert.deepEqual(readFileSync(join(fixture.outputs, 'files.txt'), 'utf8').trim().split('\n').sort(), manifestPaths);
  for (const record of manifest.files) {
    const source = readFileSync(join(fixture.repo, record.path));
    const frozen = readFileSync(join(fixture.outputs, 'freeze-root', record.path));
    assert.deepEqual(frozen, source);
    assert.equal(record.bytes, source.length);
    assert.equal(record.sha256, sha256(source));
  }
  assert.equal(readFileSync(join(fixture.outputs, 'manifest.sha256'), 'utf8'), `${sha256(manifestBytes)}  manifest.json\n`);
  for (const path of [
    manifestPath,
    join(fixture.outputs, 'files.txt'),
    join(fixture.outputs, 'manifest.sha256'),
    join(fixture.controls, 'roots.txt'),
    join(fixture.controls, 'resources.txt'),
  ]) assert.equal(lstatSync(path).mode & 0o777, 0o444, `${path} must be builder-frozen`);
  assert.equal(lstatSync(join(fixture.outputs, 'freeze-root')).mode & 0o777, 0o555);
});

test('controller-supplied generated_at is required, canonical UTC, and deterministic', (t) => {
  const invalid = makeFixture(t);
  write(join(invalid.scripts, 'root.mjs'), `export {};\n`);
  const blocked = run(invalid, {
    roots: ['sub-libraries/website-content-ops/scripts/root.mjs'],
    generatedAt: '2026-08-02T08:00:00+08:00',
  });
  assert.notEqual(blocked.status, 0);
  assert.match(blocked.stderr, /--generated-at must be a controller-supplied canonical UTC timestamp/);

  const left = makeFixture(t);
  const right = makeFixture(t);
  for (const fixture of [left, right]) write(join(fixture.scripts, 'root.mjs'), `export {};\n`);
  const config = {
    roots: ['sub-libraries/website-content-ops/scripts/root.mjs'],
    generatedAt: '2026-08-02T12:34:56.789Z',
  };
  assert.equal(run(left, config).status, 0);
  assert.equal(run(right, config).status, 0);
  assert.deepEqual(readFileSync(join(left.outputs, 'manifest.json')), readFileSync(join(right.outputs, 'manifest.json')));
});

test('missing local dependency blocks without creating outputs', (t) => {
  const fixture = makeFixture(t);
  write(join(fixture.scripts, 'root.mjs'), `import './missing.mjs';\n`);
  const result = run(fixture, { roots: ['sub-libraries/website-content-ops/scripts/root.mjs'] });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /missing local dependency/);
  assert.equal(readdirSync(fixture.outputs).length, 0);
});

test('ambiguous extension resolution blocks', (t) => {
  const fixture = makeFixture(t);
  write(join(fixture.scripts, 'root.mjs'), `import './ambiguous';\n`);
  write(join(fixture.scripts, 'ambiguous.mjs'), `export {};\n`);
  write(join(fixture.scripts, 'ambiguous.js'), `export {};\n`);
  const result = run(fixture, { roots: ['sub-libraries/website-content-ops/scripts/root.mjs'] });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /ambiguous local dependency/);
});

test('canonical scope escape blocks unless the target is an explicit mother-level root', (t) => {
  const blocked = makeFixture(t);
  write(join(blocked.scripts, 'root.mjs'), `import '../../../mother-helper.mjs';\n`);
  write(join(blocked.repo, 'mother-helper.mjs'), `export {};\n`);
  const denied = run(blocked, { roots: ['sub-libraries/website-content-ops/scripts/root.mjs'] });
  assert.notEqual(denied.status, 0);
  assert.match(denied.stderr, /escapes canonical scope/);

  const allowed = makeFixture(t);
  write(join(allowed.scripts, 'root.mjs'), `import '../../../mother-helper.mjs';\n`);
  write(join(allowed.repo, 'mother-helper.mjs'), `export {};\n`);
  const accepted = run(allowed, {
    roots: ['sub-libraries/website-content-ops/scripts/root.mjs', 'mother-helper.mjs'],
  });
  assert.equal(accepted.status, 0, `${accepted.stdout}\n${accepted.stderr}`);
});

test('symlink dependency blocks', (t) => {
  const fixture = makeFixture(t);
  write(join(fixture.scripts, 'root.mjs'), `import './linked.mjs';\n`);
  symlinkSync('missing-target.mjs', join(fixture.scripts, 'linked.mjs'));
  const result = run(fixture, { roots: ['sub-libraries/website-content-ops/scripts/root.mjs'] });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /symlink/);
});

test('non-regular dependency blocks', (t) => {
  const fixture = makeFixture(t);
  write(join(fixture.scripts, 'root.mjs'), `import './directory.mjs';\n`);
  mkdirSync(join(fixture.scripts, 'directory.mjs'));
  const result = run(fixture, { roots: ['sub-libraries/website-content-ops/scripts/root.mjs'] });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /non-regular/);
});

test('unsupported local dependency type blocks', (t) => {
  const fixture = makeFixture(t);
  write(join(fixture.scripts, 'root.mjs'), `import data from './data.json' with { type: 'json' };\n`);
  write(join(fixture.scripts, 'data.json'), `{ "ok": true }\n`);
  const result = run(fixture, { roots: ['sub-libraries/website-content-ops/scripts/root.mjs'] });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /unsupported local dependency type/);
});

test('non-literal dynamic import blocks fail closed', (t) => {
  const fixture = makeFixture(t);
  write(join(fixture.scripts, 'root.mjs'), `const target = './dynamic.mjs';\nexport const load = () => import(target);\n`);
  write(join(fixture.scripts, 'dynamic.mjs'), `export {};\n`);
  const result = run(fixture, { roots: ['sub-libraries/website-content-ops/scripts/root.mjs'] });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /non-literal dynamic import/);
});

test('dynamic-import text in comments, strings, regex, and template text is ignored while template expressions are scanned', (t) => {
  const fixture = makeFixture(t);
  write(join(fixture.scripts, 'root.mjs'), `// import(variable)\nconst a = "import(variable)";\nconst b = /import\\(variable\\)/;\nconst c = \`import(variable)\`;\nconst d = \`value: \${import('./inside.mjs')}\`;\nexport { a, b, c, d };\n`);
  write(join(fixture.scripts, 'inside.mjs'), `export default 1;\n`);
  const result = run(fixture, { roots: ['sub-libraries/website-content-ops/scripts/root.mjs'] });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
  const manifest = JSON.parse(readFileSync(join(fixture.outputs, 'manifest.json'), 'utf8'));
  assert.deepEqual(manifest.dependency_closure.edges, [{
    importer: 'sub-libraries/website-content-ops/scripts/root.mjs',
    specifier: './inside.mjs',
    target: 'sub-libraries/website-content-ops/scripts/inside.mjs',
    kind: 'dynamic-literal',
  }]);
});

test('CLI requires every explicit output/control path and refuses workspace outputs', (t) => {
  const fixture = makeFixture(t);
  const missing = spawnSync(process.execPath, [fixture.builder, '--freeze-id', 'X'], { encoding: 'utf8' });
  assert.notEqual(missing.status, 0);
  assert.match(missing.stderr, /missing required option/);

  write(join(fixture.scripts, 'root.mjs'), `export {};\n`);
  const rootsFile = join(fixture.controls, 'roots.txt');
  writeFileSync(rootsFile, `sub-libraries/website-content-ops/scripts/root.mjs\n`);
  const inside = spawnSync(process.execPath, [
    fixture.builder,
    '--freeze-id', 'X',
    '--generated-at', '2026-08-02T00:00:00.000Z',
    '--manifest', join(fixture.repo, 'manifest.json'),
    '--freeze-root', join(fixture.outputs, 'freeze-root'),
    '--file-list', join(fixture.outputs, 'files.txt'),
    '--roots-file', rootsFile,
  ], { encoding: 'utf8' });
  assert.notEqual(inside.status, 0);
  assert.match(inside.stderr, /must be outside/);
});

test('code listed only as a runtime resource blocks because its dependency closure would be unscanned', (t) => {
  const fixture = makeFixture(t);
  write(join(fixture.scripts, 'root.mjs'), `export {};\n`);
  write(join(fixture.scripts, 'hidden.mjs'), `import './missing.mjs';\n`);
  const result = run(fixture, {
    roots: ['sub-libraries/website-content-ops/scripts/root.mjs'],
    resources: ['sub-libraries/website-content-ops/scripts/hidden.mjs'],
  });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /code resource must be listed in --roots-file/);
});

test('explicit code root and resources exact overlap blocks on the classification branch', (t) => {
  const fixture = makeFixture(t);
  const root = 'sub-libraries/website-content-ops/scripts/root.mjs';
  write(join(fixture.scripts, 'root.mjs'), `export {};\n`);
  const result = run(fixture, { roots: [root], resources: [root] });
  assert.notEqual(result.status, 0);
  assert.doesNotMatch(result.stdout, /REVIEW_FREEZE_PASS/);
  assert.match(result.stderr, /REVIEW_FREEZE_BLOCK: code dependency closure\/resources exact overlap is not allowed: sub-libraries\/website-content-ops\/scripts\/root\.mjs/);
});

test('transitive code dependency and resources exact overlap blocks on the closure classification branch', (t) => {
  const fixture = makeFixture(t);
  write(join(fixture.scripts, 'root.mjs'), `import './helper.mjs';\n`);
  write(join(fixture.scripts, 'helper.mjs'), `export {};\n`);
  const result = run(fixture, {
    roots: ['sub-libraries/website-content-ops/scripts/root.mjs'],
    resources: ['sub-libraries/website-content-ops/scripts/helper.mjs'],
  });
  assert.notEqual(result.status, 0);
  assert.doesNotMatch(result.stdout, /REVIEW_FREEZE_PASS/);
  assert.match(result.stderr, /REVIEW_FREEZE_BLOCK: code dependency closure\/resources exact overlap is not allowed: sub-libraries\/website-content-ops\/scripts\/helper\.mjs/);
});

test('.cjs runtime resource blocks as an unscanned executable resource', (t) => {
  const fixture = makeFixture(t);
  write(join(fixture.scripts, 'root.mjs'), `export {};\n`);
  write(join(fixture.scripts, 'hidden.cjs'), `require('./missing.cjs');\n`);
  const result = run(fixture, {
    roots: ['sub-libraries/website-content-ops/scripts/root.mjs'],
    resources: ['sub-libraries/website-content-ops/scripts/hidden.cjs'],
  });
  assert.notEqual(result.status, 0);
  assert.doesNotMatch(result.stdout, /REVIEW_FREEZE_PASS/);
  assert.match(result.stderr, /REVIEW_FREEZE_BLOCK: unsupported unscanned executable resource type is not allowed: .*hidden\.cjs/);
});

test('CommonJS and node:module-derived runtime loaders fail closed without artifacts', async (t) => {
  const safeSource = `export const safe = true;\n`;
  const cases = [
    {
      name: 'createRequire returned require call',
      source: `import { createRequire } from 'node:module';\nconst require = createRequire(import.meta.url);\nexport const hidden = require('./hidden.json');\n`,
      branch: /REVIEW_FREEZE_BLOCK: createRequire runtime loader is not allowed/,
    },
    {
      name: 'direct require call',
      source: `export const hidden = require('./hidden.json');\n`,
      branch: /REVIEW_FREEZE_BLOCK: require runtime loader is not allowed/,
    },
    {
      name: 'module.require alias',
      source: `const localRequire = module.require;\nexport const hidden = localRequire('./hidden.json');\n`,
      branch: /REVIEW_FREEZE_BLOCK: require runtime loader is not allowed/,
    },
    {
      name: 'require.resolve',
      source: `export const hiddenPath = require.resolve('./hidden.json');\n`,
      branch: /REVIEW_FREEZE_BLOCK: require\.resolve runtime loader is not allowed/,
    },
    {
      name: 'process.getBuiltinModule derived loader',
      source: `const nodeModule = process.getBuiltinModule('node:module');\nconst localRequire = nodeModule.createRequire(import.meta.url);\nexport const hidden = localRequire('./hidden.json');\n`,
      branch: /REVIEW_FREEZE_BLOCK: process\.getBuiltinModule runtime loader is not allowed/,
    },
    {
      name: 'computed process.getBuiltinModule derived loader',
      source: `const nodeModule = process['get' + 'BuiltinModule']('node:module');\nexport const hidden = nodeModule['create' + 'Require'](import.meta.url)('./hidden.json');\n`,
      branch: /REVIEW_FREEZE_BLOCK: process\.getBuiltinModule runtime loader is not allowed via computed property/,
    },
  ];
  for (const mutation of cases) {
    await t.test(mutation.name, (t) => {
      const fixture = makeFixture(t);
      const root = join(fixture.scripts, 'root.mjs');
      assert.notEqual(mutation.source, safeSource, 'mutation must change the safe source');
      assert.match(mutation.source, /require|Require|getBuiltinModule|BuiltinModule/, 'mutation must contain a runtime-loader path');
      write(root, mutation.source);
      write(join(fixture.scripts, 'hidden.json'), `{ \"hidden\": true }\n`);
      assert.equal(readFileSync(root, 'utf8'), mutation.source, 'mutation must be written exactly');
      const result = run(fixture, { roots: ['sub-libraries/website-content-ops/scripts/root.mjs'] });
      assertBlockedWithoutArtifacts(fixture, result, mutation.branch);
    });
  }
});

test('computed runtime-loader property folding and unknown sensitive targets fail closed', async (t) => {
  const safeSource = `export const safe = true;\n`;
  const cases = [
    {
      name: 'globalThis Function string concatenation',
      source: `const RuntimeFunction = globalThis['Fun' + 'ction'];\nRuntimeFunction("return import('./missing.mjs')")();\n`,
      branch: /REVIEW_FREEZE_BLOCK: Function runtime loader is not allowed via computed property/,
    },
    {
      name: 'computed createRequire string concatenation',
      source: `const loaderFactory = nodeModule['create' + 'Require'];\nexport const loader = loaderFactory(import.meta.url);\n`,
      branch: /REVIEW_FREEZE_BLOCK: createRequire runtime loader is not allowed via computed property/,
    },
    {
      name: 'unknown globalThis computed target',
      source: `const runtimeName = getRuntimeName();\nconst RuntimeLoader = globalThis[runtimeName];\nexport { RuntimeLoader };\n`,
      branch: /REVIEW_FREEZE_BLOCK: computed runtime loader target cannot be statically proven safe/,
    },
  ];
  for (const mutation of cases) {
    await t.test(mutation.name, (t) => {
      const fixture = makeFixture(t);
      const root = join(fixture.scripts, 'root.mjs');
      assert.notEqual(mutation.source, safeSource, 'mutation must change the safe source');
      assert.match(mutation.source, /\[/, 'mutation must retain computed property syntax');
      write(root, mutation.source);
      assert.equal(readFileSync(root, 'utf8'), mutation.source, 'mutation must be written exactly');
      const result = run(fixture, { roots: ['sub-libraries/website-content-ops/scripts/root.mjs'] });
      assertBlockedWithoutArtifacts(fixture, result, mutation.branch);
    });
  }
});

test('eval, Function, computed string loaders, and timer strings hit their specific runtime-loader branches', async (t) => {
  const cases = [
    {
      name: 'direct eval',
      source: `eval("import('./missing.mjs')");\n`,
      branch: /REVIEW_FREEZE_BLOCK: eval runtime loader is not allowed/,
    },
    {
      name: 'Function constructor',
      source: `new Function("return import('./missing.mjs')");\n`,
      branch: /REVIEW_FREEZE_BLOCK: Function runtime loader is not allowed/,
    },
    {
      name: 'computed eval',
      source: `globalThis['eval']("import('./missing.mjs')");\n`,
      branch: /REVIEW_FREEZE_BLOCK: eval runtime loader is not allowed/,
    },
    {
      name: 'string timer',
      source: `setTimeout("import('./missing.mjs')", 0);\n`,
      branch: /REVIEW_FREEZE_BLOCK: string runtime loader setTimeout is not allowed/,
    },
    {
      name: 'template-string interval',
      source: "setInterval(`import('./missing.mjs')`, 0);\n",
      branch: /REVIEW_FREEZE_BLOCK: string runtime loader setInterval is not allowed/,
    },
    {
      name: 'computed string timer',
      source: `globalThis['setTimeout']("import('./missing.mjs')", 0);\n`,
      branch: /REVIEW_FREEZE_BLOCK: string runtime loader setTimeout is not allowed/,
    },
  ];
  for (const mutation of cases) {
    await t.test(mutation.name, (t) => {
      const fixture = makeFixture(t);
      write(join(fixture.scripts, 'root.mjs'), mutation.source);
      const result = run(fixture, { roots: ['sub-libraries/website-content-ops/scripts/root.mjs'] });
      assert.notEqual(result.status, 0);
      assert.doesNotMatch(result.stdout, /REVIEW_FREEZE_PASS/);
      assert.match(result.stderr, mutation.branch);
    });
  }
});

test('Worker, SharedWorker, and ServiceWorker URL dependencies hit specific fail-closed branches', async (t) => {
  const cases = [
    {
      name: 'Worker',
      source: `new Worker(new URL('./missing-worker.mjs', import.meta.url), { type: 'module' });\n`,
      branch: /REVIEW_FREEZE_BLOCK: Worker URL dependency is not allowed/,
    },
    {
      name: 'SharedWorker',
      source: `new SharedWorker(new URL('./missing-worker.mjs', import.meta.url), { type: 'module' });\n`,
      branch: /REVIEW_FREEZE_BLOCK: SharedWorker URL dependency is not allowed/,
    },
    {
      name: 'ServiceWorker',
      source: `navigator.serviceWorker.register(new URL('./missing-worker.mjs', import.meta.url));\n`,
      branch: /REVIEW_FREEZE_BLOCK: ServiceWorker URL dependency is not allowed/,
    },
  ];
  for (const mutation of cases) {
    await t.test(mutation.name, (t) => {
      const fixture = makeFixture(t);
      write(join(fixture.scripts, 'root.mjs'), mutation.source);
      const result = run(fixture, { roots: ['sub-libraries/website-content-ops/scripts/root.mjs'] });
      assert.notEqual(result.status, 0);
      assert.doesNotMatch(result.stdout, /REVIEW_FREEZE_PASS/);
      assert.match(result.stderr, mutation.branch);
    });
  }
});

test('dist paths block for roots, resources, and transitive dependencies', async (t) => {
  const cases = [
    {
      name: 'root under dist',
      setup(fixture) {
        write(join(fixture.scope, 'dist/root.mjs'), `export {};\n`);
      },
      config: { roots: ['sub-libraries/website-content-ops/dist/root.mjs'] },
      branch: /REVIEW_FREEZE_BLOCK: code root contains forbidden dist path/,
    },
    {
      name: 'resource under dist',
      setup(fixture) {
        write(join(fixture.scripts, 'root.mjs'), `export {};\n`);
        write(join(fixture.scope, 'dist/generated.md'), `generated\n`);
      },
      config: {
        roots: ['sub-libraries/website-content-ops/scripts/root.mjs'],
        resources: ['sub-libraries/website-content-ops/dist/generated.md'],
      },
      branch: /REVIEW_FREEZE_BLOCK: runtime resource contains forbidden dist path/,
    },
    {
      name: 'dependency under dist',
      setup(fixture) {
        write(join(fixture.scripts, 'root.mjs'), `import '../dist/hidden.mjs';\n`);
        write(join(fixture.scope, 'dist/hidden.mjs'), `export {};\n`);
      },
      config: { roots: ['sub-libraries/website-content-ops/scripts/root.mjs'] },
      branch: /REVIEW_FREEZE_BLOCK: code root or dependency contains forbidden dist path/,
    },
  ];
  for (const mutation of cases) {
    await t.test(mutation.name, (t) => {
      const fixture = makeFixture(t);
      mutation.setup(fixture);
      const result = run(fixture, mutation.config);
      assert.notEqual(result.status, 0);
      assert.doesNotMatch(result.stdout, /REVIEW_FREEZE_PASS/);
      assert.match(result.stderr, mutation.branch);
    });
  }
});

test('runtime-loader names in comments, strings, regexes, and template text do not trigger code branches', (t) => {
  const fixture = makeFixture(t);
  write(join(fixture.scripts, 'root.mjs'), `// eval Function Worker SharedWorker ServiceWorker serviceWorker\nconst a = "eval Function Worker";\nconst b = /SharedWorker|serviceWorker/;\nconst c = \`ServiceWorker setTimeout('code')\`;\nexport { a, b, c };\n`);
  const result = run(fixture, { roots: ['sub-libraries/website-content-ops/scripts/root.mjs'] });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
  assert.match(result.stdout, /REVIEW_FREEZE_PASS/);
});
