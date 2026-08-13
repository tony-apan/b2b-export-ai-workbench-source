#!/usr/bin/env node
import { createHash } from 'node:crypto';
import {
  existsSync,
  lstatSync,
  readFileSync,
  readdirSync,
  realpathSync,
} from 'node:fs';
import { basename, dirname, isAbsolute, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const SCRIPT_PATH = fileURLToPath(import.meta.url);
const SCRIPT_DIR = dirname(SCRIPT_PATH);
const CANONICAL_SCOPE = realpathSync(resolve(SCRIPT_DIR, '..'));
const REPOSITORY_ROOT = realpathSync(resolve(SCRIPT_DIR, '../../..'));
const CANONICAL_SCOPE_RELATIVE = toRepoRelative(CANONICAL_SCOPE);
const BUILDER_RELATIVE = `${CANONICAL_SCOPE_RELATIVE}/scripts/build-review-freeze.mjs`;

function fail(message) {
  throw new Error(message);
}

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function isWithin(parent, child) {
  const rel = relative(parent, child);
  return rel === '' || (!rel.startsWith(`..${sep}`) && rel !== '..' && !isAbsolute(rel));
}

function toPosix(value) {
  return value.split(sep).join('/');
}

function toRepoRelative(absolutePath) {
  if (!isWithin(REPOSITORY_ROOT, absolutePath)) fail(`path escapes repository root: ${absolutePath}`);
  const rel = toPosix(relative(REPOSITORY_ROOT, absolutePath));
  if (!rel || rel === '.') fail(`repository root cannot be represented as a frozen file: ${absolutePath}`);
  return rel;
}

function assertAbsolutePath(raw, option) {
  if (!raw || !isAbsolute(raw)) fail(`${option} must be an explicit absolute path`);
  return resolve(raw);
}

function assertExistingNonSymlink(raw, option, type) {
  const absolute = assertAbsolutePath(raw, option);
  if (!existsSync(absolute)) fail(`${option} does not exist: ${absolute}`);
  const stat = lstatSync(absolute);
  if (stat.isSymbolicLink()) fail(`${option} must not be a symlink: ${absolute}`);
  if (type === 'file' && !stat.isFile()) fail(`${option} must be a regular file: ${absolute}`);
  if (type === 'directory' && !stat.isDirectory()) fail(`${option} must be a directory: ${absolute}`);
  return realpathSync(absolute);
}

function parseArgs(argv) {
  const supported = new Set(['--freeze-root', '--manifest', '--file-list', '--expected-manifest-sha256', '--sha-file', '--roots-file', '--resources-file']);
  const values = new Map();
  for (let index = 0; index < argv.length; index += 1) {
    const option = argv[index];
    if (!supported.has(option)) fail(`unknown option: ${option}`);
    if (values.has(option)) fail(`duplicate option: ${option}`);
    const value = argv[index + 1];
    if (!value || value.startsWith('--')) fail(`${option} requires a value`);
    values.set(option, value);
    index += 1;
  }
  for (const required of ['--freeze-root', '--manifest', '--file-list', '--expected-manifest-sha256', '--roots-file']) {
    if (!values.has(required)) fail(`missing required option: ${required}`);
  }
  const expectedManifestSha256 = values.get('--expected-manifest-sha256');
  if (!/^[a-f0-9]{64}$/u.test(expectedManifestSha256)) {
    fail('--expected-manifest-sha256 must be a lowercase 64-character SHA-256 supplied by the controller');
  }
  const options = {
    freezeRoot: assertExistingNonSymlink(values.get('--freeze-root'), '--freeze-root', 'directory'),
    manifestPath: assertExistingNonSymlink(values.get('--manifest'), '--manifest', 'file'),
    fileListPath: assertExistingNonSymlink(values.get('--file-list'), '--file-list', 'file'),
    rootsFilePath: assertExistingNonSymlink(values.get('--roots-file'), '--roots-file', 'file'),
    resourcesFilePath: values.has('--resources-file') ? assertExistingNonSymlink(values.get('--resources-file'), '--resources-file', 'file') : null,
    expectedManifestSha256,
    shaFilePath: values.has('--sha-file') ? assertExistingNonSymlink(values.get('--sha-file'), '--sha-file', 'file') : null,
  };
  const controls = [
    options.manifestPath,
    options.fileListPath,
    options.rootsFilePath,
    ...(options.resourcesFilePath ? [options.resourcesFilePath] : []),
    ...(options.shaFilePath ? [options.shaFilePath] : []),
  ];
  if (new Set(controls).size !== controls.length) fail('manifest, file list, roots file, resources file, and SHA sidecar paths must be distinct');
  for (const control of controls) {
    if (isWithin(options.freezeRoot, control) || isWithin(control, options.freezeRoot)) {
      fail(`control path must not overlap freeze root: ${control}`);
    }
  }
  return options;
}

function assertPlainObject(value, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(`${label} must be an object`);
  return value;
}

function assertExactKeys(value, expected, label) {
  assertPlainObject(value, label);
  const actual = Object.keys(value).sort();
  const wanted = [...expected].sort();
  if (JSON.stringify(actual) !== JSON.stringify(wanted)) {
    fail(`${label} keys mismatch: expected ${wanted.join(', ')}; received ${actual.join(', ')}`);
  }
}

function assertNonEmptyString(value, label) {
  if (typeof value !== 'string' || value.trim() !== value || value.length === 0) fail(`${label} must be a non-empty trimmed string`);
}

function parseRepoRelativePath(raw, label) {
  assertNonEmptyString(raw, label);
  if (isAbsolute(raw) || /^[A-Za-z]:[\\/]/u.test(raw) || raw.includes('\\')) {
    fail(`${label} must be a repository-relative POSIX path: ${raw}`);
  }
  const parts = raw.split('/');
  if (parts.some((part) => part === '' || part === '.' || part === '..')) {
    fail(`${label} is not a canonical repository-relative path: ${raw}`);
  }
  const absolute = resolve(REPOSITORY_ROOT, ...parts);
  if (!isWithin(REPOSITORY_ROOT, absolute)) fail(`${label} escapes repository root: ${raw}`);
  if (toRepoRelative(absolute) !== raw) fail(`${label} is not canonical: ${raw}`);
  if (parts.includes('dist')) fail(`${label} contains forbidden dist path: ${raw}`);
  return raw;
}

function assertUniqueStrings(values, label, { repoPaths = false, sorted = false } = {}) {
  if (!Array.isArray(values)) fail(`${label} must be an array`);
  const normalized = values.map((value, index) => repoPaths
    ? parseRepoRelativePath(value, `${label}[${index}]`)
    : (assertNonEmptyString(value, `${label}[${index}]`), value));
  if (sorted && JSON.stringify(normalized) !== JSON.stringify([...normalized].sort())) fail(`${label} must be lexically sorted`);
  if (new Set(normalized).size !== normalized.length) fail(`${label} must not contain duplicates`);
  return normalized;
}

function assertNoDuplicateJsonKeys(source) {
  let index = 0;

  function skipWhitespace() {
    while (/\s/u.test(source[index] ?? '')) index += 1;
  }

  function parseString() {
    if (source[index] !== '"') fail(`manifest must be valid UTF-8 JSON: expected string at byte ${index}`);
    const start = index;
    index += 1;
    while (index < source.length) {
      const char = source[index];
      if (char === '"') {
        index += 1;
        try {
          return JSON.parse(source.slice(start, index));
        } catch (error) {
          fail(`manifest must be valid UTF-8 JSON: ${error.message}`);
        }
      }
      if (char === '\\') {
        index += 1;
        if (source[index] === 'u') {
          if (!/^[a-fA-F0-9]{4}$/u.test(source.slice(index + 1, index + 5))) {
            fail(`manifest must be valid UTF-8 JSON: invalid Unicode escape at byte ${index}`);
          }
          index += 5;
          continue;
        }
        if (!/["\\/bfnrt]/u.test(source[index] ?? '')) {
          fail(`manifest must be valid UTF-8 JSON: invalid escape at byte ${index}`);
        }
        index += 1;
        continue;
      }
      if (char.charCodeAt(0) < 0x20) fail(`manifest must be valid UTF-8 JSON: control character in string at byte ${index}`);
      index += 1;
    }
    fail('manifest must be valid UTF-8 JSON: unterminated string');
  }

  function parseValue(path) {
    skipWhitespace();
    const char = source[index];
    if (char === '{') return parseObject(path);
    if (char === '[') return parseArray(path);
    if (char === '"') {
      parseString();
      return;
    }
    const match = source.slice(index).match(/^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/u);
    if (!match) fail(`manifest must be valid UTF-8 JSON: invalid value at byte ${index}`);
    index += match[0].length;
  }

  function parseObject(path) {
    index += 1;
    skipWhitespace();
    const keys = new Set();
    if (source[index] === '}') {
      index += 1;
      return;
    }
    while (index < source.length) {
      skipWhitespace();
      const key = parseString();
      if (keys.has(key)) fail(`manifest contains duplicate JSON key at ${path}: ${JSON.stringify(key)}`);
      keys.add(key);
      skipWhitespace();
      if (source[index] !== ':') fail(`manifest must be valid UTF-8 JSON: expected colon at byte ${index}`);
      index += 1;
      parseValue(`${path}.${key}`);
      skipWhitespace();
      if (source[index] === '}') {
        index += 1;
        return;
      }
      if (source[index] !== ',') fail(`manifest must be valid UTF-8 JSON: expected comma at byte ${index}`);
      index += 1;
    }
    fail('manifest must be valid UTF-8 JSON: unterminated object');
  }

  function parseArray(path) {
    index += 1;
    skipWhitespace();
    if (source[index] === ']') {
      index += 1;
      return;
    }
    let item = 0;
    while (index < source.length) {
      parseValue(`${path}[${item}]`);
      item += 1;
      skipWhitespace();
      if (source[index] === ']') {
        index += 1;
        return;
      }
      if (source[index] !== ',') fail(`manifest must be valid UTF-8 JSON: expected comma at byte ${index}`);
      index += 1;
    }
    fail('manifest must be valid UTF-8 JSON: unterminated array');
  }

  parseValue('$');
  skipWhitespace();
  if (index !== source.length) fail(`manifest must be valid UTF-8 JSON: trailing content at byte ${index}`);
}

function parseControlPathList(bytes, label) {
  const seen = new Set();
  const entries = [];
  for (const [index, raw] of bytes.toString('utf8').split(/\r?\n/u).entries()) {
    const value = raw.trim();
    if (!value || value.startsWith('#')) continue;
    const parsed = parseRepoRelativePath(value, `${label}:${index + 1}`);
    if (seen.has(parsed)) continue;
    seen.add(parsed);
    entries.push(parsed);
  }
  return entries;
}

function validateControlFileRecord(record, label) {
  assertExactKeys(record, ['bytes', 'sha256', 'mode', 'entries'], label);
  if (!Number.isSafeInteger(record.bytes) || record.bytes < 0) fail(`${label}.bytes must be a non-negative safe integer`);
  if (!/^[a-f0-9]{64}$/u.test(record.sha256 ?? '')) fail(`${label}.sha256 must be a lowercase SHA-256`);
  if (record.mode !== '0444') fail(`${label}.mode must equal 0444`);
  return assertUniqueStrings(record.entries, `${label}.entries`, { repoPaths: true });
}

function parseManifest(bytes) {
  const source = bytes.toString('utf8');
  assertNoDuplicateJsonKeys(source);
  let manifest;
  try {
    manifest = JSON.parse(source);
  } catch (error) {
    fail(`manifest must be valid UTF-8 JSON: ${error.message}`);
  }
  assertExactKeys(manifest, [
    'schema_version',
    'freeze_id',
    'generated_at',
    'repository_root',
    'canonical_scope',
    'builder',
    'roots',
    'resources',
    'source_controls',
    'dependency_closure',
    'verification',
    'artifact_controls',
    'files',
  ], 'manifest');
  if (manifest.schema_version !== 2) fail('manifest.schema_version must equal 2');
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/u.test(manifest.freeze_id ?? '')) fail('manifest.freeze_id is invalid');
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/u.test(manifest.generated_at ?? '')
    || new Date(manifest.generated_at).toISOString() !== manifest.generated_at) {
    fail('manifest.generated_at must be a controller-supplied canonical UTC timestamp');
  }
  if (manifest.repository_root !== '.') fail('manifest.repository_root must equal .');
  if (manifest.canonical_scope !== CANONICAL_SCOPE_RELATIVE) {
    fail(`manifest.canonical_scope mismatch: expected ${CANONICAL_SCOPE_RELATIVE}`);
  }
  if (manifest.builder !== BUILDER_RELATIVE) fail(`manifest.builder mismatch: expected ${BUILDER_RELATIVE}`);

  const roots = assertUniqueStrings(manifest.roots, 'manifest.roots', { repoPaths: true });
  const resources = assertUniqueStrings(manifest.resources, 'manifest.resources', { repoPaths: true, sorted: true });
  const rootResourceOverlap = roots.find((path) => resources.includes(path));
  if (rootResourceOverlap) fail(`manifest roots/resources overlap: ${rootResourceOverlap}`);

  assertExactKeys(manifest.source_controls, ['roots_file', 'resources_file', 'direct_resources'], 'manifest.source_controls');
  const rootsFileEntries = validateControlFileRecord(manifest.source_controls.roots_file, 'manifest.source_controls.roots_file');
  if (JSON.stringify(rootsFileEntries) !== JSON.stringify(roots)) {
    fail('manifest.source_controls.roots_file.entries must exactly equal manifest.roots');
  }
  let resourcesFileEntries = [];
  if (manifest.source_controls.resources_file !== null) {
    resourcesFileEntries = validateControlFileRecord(manifest.source_controls.resources_file, 'manifest.source_controls.resources_file');
  }
  const directResources = assertUniqueStrings(manifest.source_controls.direct_resources, 'manifest.source_controls.direct_resources', { repoPaths: true });
  const projectedResources = [...new Set([...resourcesFileEntries, ...directResources])].sort();
  if (JSON.stringify(projectedResources) !== JSON.stringify(resources)) {
    fail('manifest.resources must exactly equal the sorted union of resources-file entries and direct resources');
  }

  assertExactKeys(manifest.dependency_closure, ['parser', 'scanned_code_files', 'local_dependency_edges', 'edges'], 'manifest.dependency_closure');
  if (manifest.dependency_closure.parser !== 'node:vm.SourceTextModule plus token-aware dynamic-import scanner') {
    fail('manifest.dependency_closure.parser mismatch');
  }
  if (!Number.isSafeInteger(manifest.dependency_closure.scanned_code_files) || manifest.dependency_closure.scanned_code_files < 1) {
    fail('manifest.dependency_closure.scanned_code_files must be a positive safe integer');
  }
  if (!Number.isSafeInteger(manifest.dependency_closure.local_dependency_edges) || manifest.dependency_closure.local_dependency_edges < 0) {
    fail('manifest.dependency_closure.local_dependency_edges must be a non-negative safe integer');
  }
  if (!Array.isArray(manifest.dependency_closure.edges)) fail('manifest.dependency_closure.edges must be an array');
  if (manifest.dependency_closure.local_dependency_edges !== manifest.dependency_closure.edges.length) {
    fail('manifest.dependency_closure.local_dependency_edges must equal edges.length');
  }
  const edgeFingerprints = [];
  for (const [index, edge] of manifest.dependency_closure.edges.entries()) {
    assertExactKeys(edge, ['importer', 'specifier', 'target', 'kind'], `manifest.dependency_closure.edges[${index}]`);
    parseRepoRelativePath(edge.importer, `manifest.dependency_closure.edges[${index}].importer`);
    parseRepoRelativePath(edge.target, `manifest.dependency_closure.edges[${index}].target`);
    assertNonEmptyString(edge.specifier, `manifest.dependency_closure.edges[${index}].specifier`);
    if (!['static', 'dynamic-literal'].includes(edge.kind)) fail(`manifest.dependency_closure.edges[${index}].kind is invalid`);
    edgeFingerprints.push(JSON.stringify(edge));
  }
  const sortedEdges = [...edgeFingerprints].sort();
  if (JSON.stringify(edgeFingerprints) !== JSON.stringify(sortedEdges)) fail('manifest.dependency_closure.edges must be sorted');
  if (new Set(edgeFingerprints).size !== edgeFingerprints.length) fail('manifest.dependency_closure.edges must not contain duplicates');

  assertExactKeys(manifest.verification, ['exact_file_set', 'bytes_verified', 'sha256_verified', 'symlinks', 'nonregular'], 'manifest.verification');
  if (manifest.verification.exact_file_set !== true) fail('manifest.verification.exact_file_set must equal true');
  if (manifest.verification.symlinks !== 0 || manifest.verification.nonregular !== 0) {
    fail('manifest.verification symlinks and nonregular must equal 0');
  }

  assertExactKeys(manifest.artifact_controls, [
    'freeze_file_mode',
    'freeze_directory_mode',
    'manifest_mode',
    'file_list',
    'sha_sidecar',
  ], 'manifest.artifact_controls');
  if (manifest.artifact_controls.freeze_file_mode !== '0444') fail('manifest.artifact_controls.freeze_file_mode must equal 0444');
  if (manifest.artifact_controls.freeze_directory_mode !== '0555') fail('manifest.artifact_controls.freeze_directory_mode must equal 0555');
  if (manifest.artifact_controls.manifest_mode !== '0444') fail('manifest.artifact_controls.manifest_mode must equal 0444');
  assertExactKeys(manifest.artifact_controls.file_list, ['bytes', 'sha256', 'mode', 'derivation'], 'manifest.artifact_controls.file_list');
  if (!Number.isSafeInteger(manifest.artifact_controls.file_list.bytes) || manifest.artifact_controls.file_list.bytes < 0) {
    fail('manifest.artifact_controls.file_list.bytes must be a non-negative safe integer');
  }
  if (!/^[a-f0-9]{64}$/u.test(manifest.artifact_controls.file_list.sha256 ?? '')) {
    fail('manifest.artifact_controls.file_list.sha256 must be a lowercase SHA-256');
  }
  if (manifest.artifact_controls.file_list.mode !== '0444') fail('manifest.artifact_controls.file_list.mode must equal 0444');
  if (manifest.artifact_controls.file_list.derivation !== 'manifest.files[].path joined by LF with one terminal LF') {
    fail('manifest.artifact_controls.file_list.derivation mismatch');
  }
  assertExactKeys(manifest.artifact_controls.sha_sidecar, ['present', 'mode', 'derivation'], 'manifest.artifact_controls.sha_sidecar');
  if (typeof manifest.artifact_controls.sha_sidecar.present !== 'boolean') {
    fail('manifest.artifact_controls.sha_sidecar.present must be boolean');
  }
  const expectedSidecarMode = manifest.artifact_controls.sha_sidecar.present ? '0444' : null;
  if (manifest.artifact_controls.sha_sidecar.mode !== expectedSidecarMode) {
    fail('manifest.artifact_controls.sha_sidecar.mode does not match presence');
  }
  if (manifest.artifact_controls.sha_sidecar.derivation !== 'controller-verified manifest SHA-256, two spaces, manifest basename, terminal LF') {
    fail('manifest.artifact_controls.sha_sidecar.derivation mismatch');
  }

  if (!Array.isArray(manifest.files) || manifest.files.length === 0) fail('manifest.files must be a non-empty array');
  const records = [];
  for (const [index, record] of manifest.files.entries()) {
    assertExactKeys(record, ['path', 'bytes', 'sha256'], `manifest.files[${index}]`);
    const path = parseRepoRelativePath(record.path, `manifest.files[${index}].path`);
    if (!Number.isSafeInteger(record.bytes) || record.bytes < 0) fail(`manifest.files[${index}].bytes must be a non-negative safe integer`);
    if (!/^[a-f0-9]{64}$/u.test(record.sha256 ?? '')) fail(`manifest.files[${index}].sha256 must be a lowercase SHA-256`);
    records.push({ path, bytes: record.bytes, sha256: record.sha256 });
  }
  const paths = records.map((record) => record.path);
  if (JSON.stringify(paths) !== JSON.stringify([...paths].sort())) fail('manifest.files must be lexically sorted by path');
  if (new Set(paths).size !== paths.length) fail('manifest.files must not contain duplicate paths');
  for (const path of [...roots, ...resources]) {
    if (!paths.includes(path)) fail(`manifest root/resource missing from files: ${path}`);
  }
  const codeFileCount = records.filter((record) => /\.(?:mjs|js)$/u.test(record.path)).length;
  if (manifest.dependency_closure.scanned_code_files !== codeFileCount) {
    fail('manifest.dependency_closure.scanned_code_files must equal the frozen .mjs/.js file count');
  }
  if (manifest.verification.bytes_verified !== records.length || manifest.verification.sha256_verified !== records.length) {
    fail('manifest.verification byte/SHA counts must equal manifest.files.length');
  }
  return { manifest, records };
}

function walkFreezeTree(root, prefix = '') {
  const files = [];
  const directories = [];
  for (const entry of readdirSync(root, { withFileTypes: true }).sort((left, right) => (left.name < right.name ? -1 : left.name > right.name ? 1 : 0))) {
    const absolute = join(root, entry.name);
    const rel = prefix ? `${prefix}/${entry.name}` : entry.name;
    const stat = lstatSync(absolute);
    if (stat.isSymbolicLink()) fail(`freeze root contains symlink: ${rel}`);
    if (stat.isDirectory()) {
      directories.push(absolute);
      const nested = walkFreezeTree(absolute, rel);
      files.push(...nested.files);
      directories.push(...nested.directories);
    } else if (stat.isFile()) {
      files.push({ path: rel, absolute });
    } else {
      fail(`freeze root contains non-regular entry: ${rel}`);
    }
  }
  return { files, directories };
}

function verifySidecar(path, digest, manifestPath) {
  const expected = `${digest}  ${basename(manifestPath)}\n`;
  const actual = readFileSync(path, 'utf8');
  if (actual !== expected) fail('SHA sidecar does not exactly match the controller-verified manifest digest and manifest basename');
}

function assertMode(path, expected, label) {
  const actual = lstatSync(path).mode & 0o777;
  if (actual !== expected) fail(`${label} read-only mode mismatch: expected ${expected.toString(8)}, received ${actual.toString(8)}`);
}

function verifyInitialControlModes(options) {
  assertMode(options.freezeRoot, 0o555, 'freeze root');
  assertMode(options.manifestPath, 0o444, 'manifest');
  assertMode(options.fileListPath, 0o444, 'file list');
  assertMode(options.rootsFilePath, 0o444, 'roots file');
  if (options.resourcesFilePath) assertMode(options.resourcesFilePath, 0o444, 'resources file');
  if (options.shaFilePath) assertMode(options.shaFilePath, 0o444, 'SHA sidecar');
}

function verifyFreezeTreeModes(tree) {
  for (const file of tree.files) assertMode(file.absolute, 0o444, `freeze file ${file.path}`);
  for (const directory of tree.directories) assertMode(directory, 0o555, `freeze directory ${directory}`);
}

function verifyControlFile(path, record, label) {
  const bytes = readFileSync(path);
  if (bytes.length !== record.bytes) fail(`${label} byte-count mismatch`);
  if (sha256(bytes) !== record.sha256) fail(`${label} SHA-256 mismatch`);
  const entries = parseControlPathList(bytes, label);
  if (JSON.stringify(entries) !== JSON.stringify(record.entries)) {
    fail(`${label} parsed entries do not exactly match manifest evidence`);
  }
}

function verifyReviewFreeze(options) {
  verifyInitialControlModes(options);
  const manifestBytes = readFileSync(options.manifestPath);
  const manifestSha256 = sha256(manifestBytes);
  if (manifestSha256 !== options.expectedManifestSha256) {
    fail(`controller manifest SHA-256 mismatch: expected ${options.expectedManifestSha256}; received ${manifestSha256}`);
  }
  const { manifest, records } = parseManifest(manifestBytes);
  const resourcesFileExpected = manifest.source_controls.resources_file !== null;
  if (Boolean(options.resourcesFilePath) !== resourcesFileExpected) {
    fail('resources file argument presence must exactly match manifest.source_controls.resources_file');
  }
  if (Boolean(options.shaFilePath) !== manifest.artifact_controls.sha_sidecar.present) {
    fail('SHA sidecar argument presence must exactly match manifest.artifact_controls.sha_sidecar.present');
  }
  verifyControlFile(options.rootsFilePath, manifest.source_controls.roots_file, 'roots file');
  if (options.resourcesFilePath) {
    verifyControlFile(options.resourcesFilePath, manifest.source_controls.resources_file, 'resources file');
  }

  const tree = walkFreezeTree(options.freezeRoot);
  tree.files.sort((left, right) => (left.path < right.path ? -1 : left.path > right.path ? 1 : 0));
  verifyFreezeTreeModes(tree);
  const actualPaths = tree.files.map((file) => file.path);
  const expectedPaths = records.map((record) => record.path);
  if (JSON.stringify(actualPaths) !== JSON.stringify(expectedPaths)) {
    fail('freeze root exact file set mismatch');
  }
  for (const [index, record] of records.entries()) {
    const bytes = readFileSync(tree.files[index].absolute);
    if (bytes.length !== record.bytes) fail(`freeze root byte-count mismatch: ${record.path}`);
    if (sha256(bytes) !== record.sha256) fail(`freeze root SHA-256 mismatch: ${record.path}`);
  }
  const expectedFileList = Buffer.from(`${expectedPaths.join('\n')}\n`);
  const actualFileList = readFileSync(options.fileListPath);
  if (actualFileList.length !== manifest.artifact_controls.file_list.bytes) fail('file list byte-count mismatch against manifest evidence');
  if (sha256(actualFileList) !== manifest.artifact_controls.file_list.sha256) fail('file list SHA-256 mismatch against manifest evidence');
  if (!actualFileList.equals(expectedFileList)) fail('file list must exactly match manifest file order and set');
  if (options.shaFilePath) verifySidecar(options.shaFilePath, manifestSha256, options.manifestPath);
  return {
    freezeId: manifest.freeze_id,
    generatedAt: manifest.generated_at,
    files: records.length,
    manifestSha256,
  };
}

function runCli() {
  try {
    const result = verifyReviewFreeze(parseArgs(process.argv.slice(2)));
    process.stdout.write(`REVIEW_FREEZE_VERIFY_PASS freeze_id=${result.freezeId} generated_at=${result.generatedAt} files=${result.files} manifest_sha256=${result.manifestSha256} trust_scope=local-review-immutability-only\n`);
  } catch (error) {
    process.stderr.write(`REVIEW_FREEZE_VERIFY_BLOCK: ${error.message}\n`);
    process.exitCode = 1;
  }
}

const isMain = process.argv[1] && realpathSync(process.argv[1]) === realpathSync(SCRIPT_PATH);
if (isMain) runCli();
