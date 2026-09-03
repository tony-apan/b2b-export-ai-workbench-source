#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { readFrontMatter } from './lib/markdown-front-matter.mjs';

const scriptPath = fileURLToPath(import.meta.url);
const sourceRoot = resolve(dirname(scriptPath), '..');
const releaseDir = join(sourceRoot, 'dist', 'mother');
let outputRoot = join(releaseDir, 'latest');
const stagingRoot = join(releaseDir, `.staging-${process.pid}`);
const releaseMode = process.argv.includes('--release');
const prepareMode = process.argv.includes('--prepare');
const requireCommitProvenance = releaseMode || prepareMode || process.argv.includes('--require-commit-provenance');
const approvalFlag = process.argv.indexOf('--approval');
const approvalPath = approvalFlag >= 0 ? resolve(process.argv[approvalFlag + 1] ?? '') : '';
const evidenceFlag = process.argv.indexOf('--evidence');
const evidencePath = evidenceFlag >= 0 ? resolve(process.argv[evidenceFlag + 1] ?? '') : '';
if (releaseMode) {
  console.error('FAIL: builder --release is retired; run --prepare once, freeze that candidate, then run validate-artifact.mjs --release <frozen-candidate> with external approval/evidence');
  process.exit(1);
}
if (prepareMode && (approvalPath || evidencePath)) {
  console.error('FAIL: --prepare must not receive approval or evidence; approval is created only after the candidate digest is frozen');
  process.exit(1);
}
const manifestPath = join(sourceRoot, 'MANIFEST.md');
const manifestText = readFileSync(manifestPath, 'utf8');
let manifestMetadata;
try { manifestMetadata = readFrontMatter(manifestPath, { rejectDuplicates: true }).data; } catch (error) {
  console.error(`FAIL: MANIFEST.md front matter is invalid: ${error.message}`);
  process.exit(1);
}
const runtimeApplicability = manifestMetadata.get('runtime_applicability');
const runtimeContract = manifestMetadata.get('runtime_contract');
if (runtimeApplicability !== 'none' || runtimeContract !== null) {
  console.error('FAIL: mother MANIFEST.md must declare runtime_applicability: none and runtime_contract: null');
  process.exit(1);
}
if (existsSync(join(sourceRoot, 'RUNTIME-CONTRACT.json'))) {
  console.error('FAIL: mother runtime N/A is invalid while root RUNTIME-CONTRACT.json exists');
  process.exit(1);
}
const version = readFileSync(join(sourceRoot, 'VERSION.md'), 'utf8').match(/Version：`([^`]+)`/)?.[1] ?? 'unknown';
const status = manifestText.match(/^release_status:\s*["']?([^\n"']+)/m)?.[1]?.trim() ?? 'unknown';
function manifestArray(field) {
  const line = manifestText.match(new RegExp(`^${field}:\\s*(\\[[^\\n]*\\])`, 'm'))?.[1] ?? '[]';
  return [...line.matchAll(/"([^"]*)"|'([^']*)'/g)].map((m) => m[1] ?? m[2]);
}
const includePatterns = manifestArray('include');
const excludePatterns = manifestArray('exclude');
const rawFixtureDigestEntries = manifestArray('raw_fixture_digests');
const posix = (value) => value.split('\\').join('/');
function matchesPattern(value, pattern) {
  const candidatePath = posix(value);
  const rule = posix(pattern);
  const candidate = rule.includes('/') ? candidatePath : candidatePath.split('/').pop();
  let source = '';
  for (let i = 0; i < rule.length; i += 1) {
    if (rule.startsWith('**', i)) { source += '.*'; i += 1; continue; }
    if (rule[i] === '*' && i === 0 && rule[1] === '.') { source += '.*'; continue; }
    if (rule[i] === '*') { source += '[^/]*'; continue; }
    source += rule[i].replace(/[.+^${}()|[\]\\]/g, '\\$&');
  }
  return new RegExp(`^${source}$`).test(candidate);
}
const publicRawNavigationDirs = new Set(['raw/00_inbox', 'raw/10_conversations', 'raw/20_web', 'raw/30_documents', 'raw/40_media', 'raw/50_exports', 'raw/90_archive', 'raw/_templates']);
const publicRawFixtures = new Set([
  'raw/10_conversations/src-20260728-0001-knowledge-base-structure-closure.md',
]);
const publicRawNavigation = new Set([
  'raw/index.md',
  'raw/00_inbox/index.md',
  'raw/10_conversations/index.md',
  'raw/20_web/index.md',
  'raw/30_documents/index.md',
  'raw/40_media/index.md',
  'raw/50_exports/index.md',
  'raw/90_archive/index.md',
  'raw/_templates/index.md',
  'raw/_templates/conversation-source.md',
  // Explicitly allowlisted public-safe synthetic fixtures used by governance tests.
  ...publicRawFixtures,
]);
function isExplicitlyAllowed(path) {
  return publicRawNavigation.has(path);
}
function isExcluded(path) {
  // The public mother release includes raw's taxonomy/index/template layer,
  // plus only explicitly allowlisted safe synthetic fixtures. All other raw
  // sources remain excluded so navigation cannot accidentally publish private
  // conversations, exports or media.
  if (publicRawNavigation.has(path) || publicRawNavigationDirs.has(path)) return false;
  if (path.startsWith('raw/')) return true;
  return excludePatterns.some((pattern) => matchesPattern(path, pattern));
}
function isIncluded(path) { return includePatterns.some((pattern) => matchesPattern(path, pattern)); }
function mayContainIncluded(path) {
  if (!path) return true;
  return includePatterns.some((pattern) => {
    const rule = posix(pattern);
    if (rule.endsWith('/**')) {
      const base = rule.slice(0, -3);
      return path === base || path.startsWith(`${base}/`);
    }
    return rule.startsWith(`${path}/`) || rule.startsWith('**/') || rule.startsWith('*');
  });
}
function fail(message) {
  rmSync(stagingRoot, { recursive: true, force: true });
  console.error(`FAIL: ${message}`);
  process.exit(1);
}
function sha256(path) { return createHash('sha256').update(readFileSync(path)).digest('hex'); }
const approvalStatus = manifestText.match(/^approval_status:\s*["']?([^\n"']+)/m)?.[1]?.trim() ?? 'unknown';
const finalRelease = ['Ready', 'Published'].includes(status) || approvalStatus === 'approved';
function gitResult(args, options = {}) {
  return spawnSync('git', args, { cwd: sourceRoot, ...options });
}
function gitText(args) {
  const result = gitResult(args, { encoding: 'utf8' });
  return result.status === 0 ? result.stdout.trim() : null;
}
const sourceCommit = gitText(['rev-parse', 'HEAD']);
if (!sourceCommit) fail('release candidate build requires Git metadata; build from a Git checkout so source_commit is traceable');
const sourceDirty = Boolean(gitText(['status', '--porcelain', '--untracked-files=all']));
function commitTreeEntries(commit) {
  const result = gitResult(['ls-tree', '-r', '-z', '--full-tree', commit]);
  if (result.status !== 0) fail(`could not read source commit tree ${commit}`);
  const entries = new Map();
  for (const record of result.stdout.toString('utf8').split('\0').filter(Boolean)) {
    const tab = record.indexOf('\t');
    const metadata = record.slice(0, tab).split(' ');
    const path = record.slice(tab + 1);
    if (tab < 0 || metadata.length !== 3) fail(`could not parse Git tree entry for ${path || 'unknown path'}`);
    entries.set(path, { mode: metadata[0], type: metadata[1], object: metadata[2] });
  }
  return entries;
}
const sourceCommitTree = commitTreeEntries(sourceCommit);
function commitBlobSha256Batch(objects) {
  const uniqueObjects = [...new Set(objects)];
  if (!uniqueObjects.length) return new Map();

  const input = Buffer.from(`${uniqueObjects.join('\n')}\n`, 'utf8');
  const check = gitResult(
    ['cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)'],
    {
      input,
      encoding: 'utf8',
      maxBuffer: Math.max(1024 * 1024, uniqueObjects.length * 128 + 1024),
    },
  );
  if (check.error) fail(`could not inspect Git blobs from source commit: ${check.error.message}`);
  if (check.status !== 0) fail('could not inspect Git blobs from source commit');

  const lines = check.stdout.trimEnd().split('\n');
  if (lines.length !== uniqueObjects.length) fail('Git blob batch-check returned an unexpected object count');

  let totalBlobBytes = 0;
  for (const [index, line] of lines.entries()) {
    const expectedObject = uniqueObjects[index];
    const match = line.match(/^([a-f0-9]{40,64}) blob ([0-9]+)$/);
    if (!match || match[1] !== expectedObject) fail(`Git blob batch-check did not bind expected object ${expectedObject}`);
    const size = Number(match[2]);
    if (!Number.isSafeInteger(size) || size < 0) fail(`Git blob batch-check returned an unsafe size for ${expectedObject}`);
    if (!Number.isSafeInteger(totalBlobBytes + size)) fail('Git blob batch exceeds the safe in-memory size range');
    totalBlobBytes += size;
  }

  const result = gitResult(['cat-file', '--batch'], {
    input,
    maxBuffer: totalBlobBytes + uniqueObjects.length * 128 + 1024,
  });
  if (result.error) fail(`could not batch-read Git blobs from source commit: ${result.error.message}`);
  if (result.status !== 0) fail('could not batch-read Git blobs from source commit');

  const output = result.stdout;
  const digests = new Map();
  let offset = 0;
  for (const expectedObject of uniqueObjects) {
    const headerEnd = output.indexOf(0x0a, offset);
    if (headerEnd < 0) fail(`Git blob batch output is missing a header for ${expectedObject}`);
    const header = output.subarray(offset, headerEnd).toString('utf8');
    const match = header.match(/^([a-f0-9]{40,64}) blob ([0-9]+)$/);
    if (!match || match[1] !== expectedObject) fail(`Git blob batch output did not bind expected object ${expectedObject}`);
    const size = Number(match[2]);
    if (!Number.isSafeInteger(size) || size < 0) fail(`Git blob batch output returned an unsafe size for ${expectedObject}`);
    const contentStart = headerEnd + 1;
    const contentEnd = contentStart + size;
    if (contentEnd >= output.length || output[contentEnd] !== 0x0a) fail(`Git blob batch output is truncated for ${expectedObject}`);
    digests.set(expectedObject, createHash('sha256').update(output.subarray(contentStart, contentEnd)).digest('hex'));
    offset = contentEnd + 1;
  }
  if (offset !== output.length) fail('Git blob batch output contains unexpected trailing bytes');
  return digests;
}
function isGitIgnored(path) {
  return gitResult(['check-ignore', '-q', '--', path]).status === 0;
}
function rawFixtureDigestContract() {
  const contract = new Map();
  for (const entry of rawFixtureDigestEntries) {
    const separator = entry.lastIndexOf('=');
    const path = separator >= 0 ? entry.slice(0, separator) : '';
    const digest = separator >= 0 ? entry.slice(separator + 1) : '';
    if (!path || !/^[a-f0-9]{64}$/.test(digest)) fail(`raw_fixture_digests entry must use path=<64 lowercase hex>: ${entry}`);
    if (contract.has(path)) fail(`duplicate raw fixture digest contract: ${path}`);
    contract.set(path, digest);
  }
  for (const path of publicRawFixtures) {
    if (!contract.has(path)) fail(`public raw fixture is missing a manifest digest contract: ${path}`);
    if (!existsSync(join(sourceRoot, path))) fail(`public raw fixture is missing: ${path}`);
    if (sha256(join(sourceRoot, path)) !== contract.get(path)) fail(`public raw fixture digest does not match MANIFEST.md contract: ${path}`);
  }
  for (const path of contract.keys()) {
    if (!publicRawFixtures.has(path)) fail(`MANIFEST.md declares an unrecognized public raw fixture digest: ${path}`);
  }
  return Object.fromEntries([...contract.entries()].sort(([left], [right]) => left.localeCompare(right)));
}
const rawFixtureDigests = rawFixtureDigestContract();
function contentDigest(root, files) {
  const hash = createHash('sha256');
  for (const file of files) hash.update(`${file}\0${sha256(join(root, file))}\n`);
  return hash.digest('hex');
}
const autoIgnoredDirs = new Set(['.git', '.obsidian', '.v2c', '.video_agent', 'node_modules', 'dist', 'secrets', '.secrets', 'private', 'runtime', 'customer-runtime', 'credentials', 'workspace']);
function collectSourceFiles(source, prefix = '') {
  const result = [];
  for (const entry of readdirSync(source, { withFileTypes: true })) {
    const rel = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isSymbolicLink()) fail(`symlink is not allowed in release source: ${rel}`);
    if (entry.isDirectory()) {
      if (!autoIgnoredDirs.has(entry.name)) result.push(...collectSourceFiles(join(source, entry.name), rel));
    } else result.push(rel);
  }
  return result;
}
function assertSourceCompleteness() {
  for (const file of collectSourceFiles(sourceRoot)) {
    if (isExcluded(file) || isIncluded(file) || isExplicitlyAllowed(file)) continue;
    fail(`source file is not covered by manifest include/exclude rules: ${file}`);
  }
}
function assertChildManifestBoundaries() {
  let childRegistry;
  try { childRegistry = JSON.parse(readFileSync(join(sourceRoot, 'sub-libraries/registry.json'), 'utf8')); } catch { fail('sub-libraries/registry.json is not valid JSON'); return; }
  for (const child of Array.isArray(childRegistry.entries) ? childRegistry.entries : []) {
    if (child.included_in_mother !== 'source-only') continue;
    const childRoot = join(sourceRoot, child.path ?? `sub-libraries/${child.id}`);
    const childManifestPath = join(childRoot, 'MANIFEST.md');
    if (!existsSync(childManifestPath)) { fail(`mother candidate cannot enforce missing child manifest: ${child.id}`); continue; }
    const childManifest = readFileSync(childManifestPath, 'utf8');
    const childIncludes = [...(childManifest.match(/^include:\s*(\[[^\n]*\])/m)?.[1] ?? '[]').matchAll(/"([^"]*)"|'([^']*)'/g)].map((m) => m[1] ?? m[2]);
    const childExcludes = [...(childManifest.match(/^exclude:\s*(\[[^\n]*\])/m)?.[1] ?? '[]').matchAll(/"([^"]*)"|'([^']*)'/g)].map((m) => m[1] ?? m[2]);
    for (const childFile of collectSourceFiles(childRoot)) {
      const motherFile = `sub-libraries/${child.id}/${childFile}`;
      const childIncluded = childIncludes.some((pattern) => matchesPattern(childFile, pattern));
      const childExcluded = childExcludes.some((pattern) => matchesPattern(childFile, pattern));
      const childSelected = childIncluded && !childExcluded;
      const motherSelected = isIncluded(motherFile) && !isExcluded(motherFile);
      if (childSelected !== motherSelected) fail(`mother/child release boundary mismatch: ${child.id}/${childFile} child=${childSelected} mother=${motherSelected}`);
    }
  }
}
function copySelected(source, target, prefix = '') {
  mkdirSync(target, { recursive: true });
  for (const entry of readdirSync(source, { withFileTypes: true })) {
    const rel = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isSymbolicLink()) fail(`symlink is not allowed in release source: ${rel}`);
    if (['.git', '.obsidian', '.v2c', '.video_agent', 'node_modules', 'dist', 'secrets', '.secrets', 'private', 'runtime', 'customer-runtime', 'credentials', 'workspace'].includes(entry.name)) continue;
    if (isExcluded(rel)) continue;
    const from = join(source, entry.name);
    const to = join(target, entry.name);
    if (entry.isDirectory()) {
      if (mayContainIncluded(rel)) copySelected(from, to, rel);
    } else if (isIncluded(rel)) {
      mkdirSync(dirname(to), { recursive: true });
      cpSync(from, to);
    }
  }
}
function collect(dir) {
  const result = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) result.push(...collect(path));
    else result.push(relative(stagingRoot, path));
  }
  return result;
}
function fileProvenance(files) {
  const commitObjects = [];
  for (const path of files) {
    const treeEntry = sourceCommitTree.get(path);
    if (!treeEntry) continue;
    if (treeEntry.type !== 'blob') fail(`selected source path is not a Git blob in ${sourceCommit}: ${path}`);
    commitObjects.push(treeEntry.object);
  }
  const commitSha256ByObject = commitBlobSha256Batch(commitObjects);

  const records = files.map((path) => {
    const fileSha256 = sha256(join(stagingRoot, path));
    const treeEntry = sourceCommitTree.get(path);
    if (!treeEntry) {
      return {
        path,
        sha256: fileSha256,
        git_state: isGitIgnored(path) ? 'ignored' : 'untracked',
        commit_bound: false,
        commit_blob: null,
      };
    }
    const committedSha256 = commitSha256ByObject.get(treeEntry.object);
    if (!committedSha256) fail(`missing batched Git blob digest for ${path} at ${treeEntry.object}`);
    return {
      path,
      sha256: fileSha256,
      git_state: committedSha256 === fileSha256 ? 'committed' : 'modified',
      commit_bound: committedSha256 === fileSha256,
      commit_blob: treeEntry.object,
      commit_sha256: committedSha256,
    };
  });
  const selected = new Set(files);
  const missingCommitFiles = [...sourceCommitTree.keys()]
    .filter((path) => isIncluded(path) && !isExcluded(path) && !selected.has(path))
    .sort();
  return {
    schema: 'git-file-provenance/v1',
    source_commit: sourceCommit,
    commit_rebuildable: records.every((record) => record.commit_bound) && missingCommitFiles.length === 0,
    selected_file_count: records.length,
    commit_bound_file_count: records.filter((record) => record.commit_bound).length,
    unbound_files: records.filter((record) => !record.commit_bound),
    missing_commit_files: missingCommitFiles,
    files: records,
  };
}
function assertCommitProvenance(provenance) {
  if (provenance.commit_rebuildable) return;
  const unbound = provenance.unbound_files.slice(0, 8).map((item) => `${item.path}(${item.git_state})`);
  const missing = provenance.missing_commit_files.slice(0, 8).map((path) => `${path}(deleted)`);
  const details = [...unbound, ...missing];
  const total = provenance.unbound_files.length + provenance.missing_commit_files.length;
  fail(`selected release inputs are not reproducible from source commit ${sourceCommit}: ${details.join(', ')}${total > details.length ? `, ... ${total - details.length} more` : ''}`);
}
function verifyChecksums(root, checksumPath) {
  const lines = readFileSync(checksumPath, 'utf8').trim().split('\n').filter(Boolean);
  let bad = 0;
  for (const line of lines) {
    const match = line.match(/^([a-f0-9]{64})  (.+)$/);
    if (!match || !existsSync(join(root, match[2])) || sha256(join(root, match[2])) !== match[1]) bad += 1;
  }
  if (bad) fail(`checksum verification failed: ${bad} bad entr${bad === 1 ? 'y' : 'ies'}`);
  return lines.length;
}

if (prepareMode && !/release_status:\s*["']?Ready["']?/m.test(manifestText)) fail('prepare mode requires release_status Ready');
if (prepareMode && !/^approval_status:\s*["']?pending["']?/m.test(manifestText)) fail('prepare mode requires approval_status pending');
rmSync(stagingRoot, { recursive: true, force: true });
mkdirSync(stagingRoot, { recursive: true });
copySelected(sourceRoot, stagingRoot);
const files = collect(stagingRoot).sort();
for (const file of files) {
  if (!isIncluded(file) && !isExplicitlyAllowed(file)) fail(`candidate file is outside manifest include patterns: ${file}`);
  if (isExcluded(file)) fail(`candidate file matches manifest exclude pattern: ${file}`);
}
const provenance = fileProvenance(files);
if (requireCommitProvenance || finalRelease) assertCommitProvenance(provenance);
assertSourceCompleteness();
assertChildManifestBoundaries();
const validator = spawnSync(process.execPath, [scriptPath.replace('build-mother-release.mjs', 'validate-mother-library.mjs'), ...(prepareMode ? ['--prepare'] : [])], { encoding: 'utf8' });
process.stdout.write(validator.stdout ?? '');
process.stderr.write(validator.stderr ?? '');
if (validator.status !== 0) fail('source mother-library validation failed; no release candidate created');
let childRegistry = { entries: [] };
try { childRegistry = JSON.parse(readFileSync(join(sourceRoot, 'sub-libraries/registry.json'), 'utf8')); } catch { fail('sub-libraries/registry.json is not valid JSON'); }
const children = (Array.isArray(childRegistry.entries) ? childRegistry.entries : []).map(({ id, path, version, maturity_status, verification_status, release_status, license_status, approval_required, approval_status, tag_namespace, tag_prefix, release_scope, runtime_contract, dependency_mode, durable_roots, source_package_only, package_kind, delivery_modes, skill_entrypoint, skill_status, canonical_entry, included_in_mother }) => ({ id, path, version, maturity_status, verification_status, release_status, license_status, approval_required, approval_status, tag_namespace, tag_prefix, release_scope, runtime_contract, dependency_mode, durable_roots: durable_roots ?? [], source_package_only, package_kind, delivery_modes, skill_entrypoint, skill_status, canonical_entry, included_in_mother: included_in_mother ?? 'source-only' }));
const manifest = {
  package_id: 'b2b-export-ai-workbench-mother-library',
  package_kind: 'mother-library-release-candidate',
  version,
  release_status: status,
  maturity_status: manifestText.match(/^maturity_status:\s*["']?([^\n"']+)/m)?.[1]?.trim() ?? 'unknown',
  verification_status: manifestText.match(/^verification_status:\s*["']?([^\n"']+)/m)?.[1]?.trim() ?? 'unknown',
  release_scope: manifestText.match(/^release_scope:\s*["']?([^\n"']+)/m)?.[1]?.trim() ?? 'source-index',
  license_status: manifestText.match(/^license_status:\s*["']?([^\n"']+)/m)?.[1]?.trim() ?? 'unknown',
  approval_required: manifestText.match(/^approval_required:\s*(true|false)/m)?.[1] === 'true',
  approval_status: manifestText.match(/^approval_status:\s*["']?([^\n"']+)/m)?.[1]?.trim() ?? 'unknown',
  approval_record: manifestText.match(/^approval_record:\s*["']?([^\n"']+)/m)?.[1]?.trim() ?? null,
  tag_namespace: manifestText.match(/^tag_namespace:\s*["']?([^\n"']+)/m)?.[1]?.trim() ?? null,
  tag_prefix: manifestText.match(/^tag_prefix:\s*["']?([^\n"']+)/m)?.[1]?.trim() ?? null,
  delivery_modes: ['mother-library-source'],
  runtime_applicability: runtimeApplicability,
  runtime_contract: runtimeContract,
  children,
  release_mode: 'latest-only',
  qualification_state: prepareMode ? 'prepared-unapproved' : 'working-candidate',
  source_scope: 'repository-root',
  source_commit: sourceCommit,
  source_dirty: sourceDirty,
  source_selected_dirty: !provenance.commit_rebuildable,
  source_commit_rebuildable: provenance.commit_rebuildable,
  source_snapshot_kind: provenance.commit_rebuildable ? 'source-commit' : 'working-tree-snapshot',
  source_provenance: provenance,
  raw_fixture_digests: rawFixtureDigests,
  content_digest: contentDigest(stagingRoot, files),
  includes: includePatterns,
  excludes: excludePatterns,
  generated_at: process.env.SOURCE_DATE_EPOCH ? new Date(Number(process.env.SOURCE_DATE_EPOCH) * 1000).toISOString() : new Date().toISOString(),
  files,
};
writeFileSync(join(stagingRoot, 'MANIFEST.json'), JSON.stringify(manifest, null, 2) + '\n');
const checksums = files.map((file) => `${sha256(join(stagingRoot, file))}  ${file}`);
checksums.push(`${sha256(join(stagingRoot, 'MANIFEST.json'))}  MANIFEST.json`);
writeFileSync(join(stagingRoot, 'SHA256SUMS'), checksums.join('\n') + '\n');
const checksumCount = verifyChecksums(stagingRoot, join(stagingRoot, 'SHA256SUMS'));
if (prepareMode) outputRoot = join(releaseDir, 'prepared', `v${version}`, manifest.content_digest);
// The artifact validator executes the embedded mother-library validator after
// integrity, provenance, and path checks pass. Running that same embedded
// validator directly here would duplicate the candidate-wide validation while
// adding no independent gate.
const artifactValidator = spawnSync(process.execPath, [join(stagingRoot, 'scripts/validate-artifact.mjs'), ...(prepareMode ? ['--prepare'] : []), stagingRoot], {
  encoding: 'utf8',
  env: { ...process.env },
});
process.stdout.write(artifactValidator.stdout ?? '');
process.stderr.write(artifactValidator.stderr ?? '');
if (artifactValidator.status !== 0) fail('generated mother-library candidate failed artifact validation');
// In release mode both structure and artifact validators have already run with --release.
// Activation below only happens after every staging gate passes, so a failed candidate
// cannot replace an existing latest artifact.
if (prepareMode && existsSync(outputRoot)) {
  const existingManifestPath = join(outputRoot, 'MANIFEST.json');
  const existingSumsPath = join(outputRoot, 'SHA256SUMS');
  const identical = existsSync(existingManifestPath) && existsSync(existingSumsPath)
    && readFileSync(existingManifestPath, 'utf8') === readFileSync(join(stagingRoot, 'MANIFEST.json'), 'utf8')
    && readFileSync(existingSumsPath, 'utf8') === readFileSync(join(stagingRoot, 'SHA256SUMS'), 'utf8');
  rmSync(stagingRoot, { recursive: true, force: true });
  if (!identical) fail(`prepared candidate path already exists with different frozen bytes: ${outputRoot}`);
  console.log(`PREPARED_CANDIDATE_REUSED: ${outputRoot}`);
  process.exit(0);
}
mkdirSync(dirname(outputRoot), { recursive: true });
const backupRoot = join(releaseDir, `.previous-${process.pid}`);
rmSync(backupRoot, { recursive: true, force: true });
if (existsSync(outputRoot)) renameSync(outputRoot, backupRoot);
try {
  renameSync(stagingRoot, outputRoot);
} catch (error) {
  if (existsSync(backupRoot) && !existsSync(outputRoot)) renameSync(backupRoot, outputRoot);
  fail(`failed to activate release candidate: ${error.message}`);
}
rmSync(backupRoot, { recursive: true, force: true });
console.log(`${prepareMode ? 'PREPARED_UNAPPROVED_CANDIDATE' : 'RELEASE_CANDIDATE'}: ${outputRoot}`);
console.log(`VERSION: ${version}`);
console.log(`STATUS: ${status}`);
console.log(`FILES: ${files.length + 2}`);
console.log(`SHA256SUMS: ${checksumCount} entries, bad=0`);
