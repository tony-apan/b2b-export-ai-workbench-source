#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import {
  AUTO_IGNORED_DIRS,
  isManifestExcluded,
  isManifestIncluded,
  manifestArray,
  mayContainManifestInclude,
  parseManifestFrontMatter,
} from './manifest-policy.mjs';

const scriptPath = fileURLToPath(import.meta.url);
const sourceRoot = resolve(dirname(scriptPath), '..');
const releaseDir = join(sourceRoot, 'dist');
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
function fail(message) {
  rmSync(stagingRoot, { recursive: true, force: true });
  console.error(`FAIL: ${message}`);
  process.exit(1);
}
const manifestText = readFileSync(join(sourceRoot, 'MANIFEST.md'), 'utf8');
let manifestFront;
try {
  manifestFront = parseManifestFrontMatter(manifestText, { source: 'MANIFEST.md' });
} catch (error) {
  fail(error.message);
}
const version = readFileSync(join(sourceRoot, 'VERSION.md'), 'utf8').match(/Version：`([^`]+)`/)?.[1] ?? 'unknown';
const status = typeof manifestFront.release_status === 'string' ? manifestFront.release_status.trim() : 'unknown';
let includePatterns;
let excludePatterns;
let durableRoots;
try {
  includePatterns = manifestArray(manifestFront, 'include');
  excludePatterns = manifestArray(manifestFront, 'exclude');
  durableRoots = manifestArray(manifestFront, 'durable_roots');
} catch (error) {
  fail(error.message);
}
function isExcluded(path) { return isManifestExcluded(path, excludePatterns); }
function isIncluded(path) { return isManifestIncluded(path, includePatterns); }
function mayContainIncluded(path) { return mayContainManifestInclude(path, includePatterns); }
function sha256(path) { return createHash('sha256').update(readFileSync(path)).digest('hex'); }
const approvalStatus = typeof manifestFront.approval_status === 'string' ? manifestFront.approval_status.trim() : 'unknown';
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
const repositoryPrefix = (gitText(['rev-parse', '--show-prefix']) ?? '').replace(/\\/g, '/').replace(/\/$/, '');
const repositoryRoot = gitText(['rev-parse', '--show-toplevel']);
if (!repositoryRoot) fail('sub-library build requires a Git checkout with a discoverable repository root');
const sourceScope = repositoryPrefix || 'repository-root';
const sourceDirty = Boolean(gitText(['status', '--porcelain', '--untracked-files=all']));
function commitTreeEntries(commit) {
  const result = gitResult(['ls-tree', '-r', '-z', '--full-tree', commit]);
  if (result.status !== 0) fail(`could not read source commit tree ${commit}`);
  const entries = new Map();
  const prefix = repositoryPrefix ? `${repositoryPrefix}/` : '';
  for (const record of result.stdout.toString('utf8').split('\0').filter(Boolean)) {
    const tab = record.indexOf('\t');
    const metadata = record.slice(0, tab).split(' ');
    const repositoryPath = record.slice(tab + 1);
    if (tab < 0 || metadata.length !== 3) fail(`could not parse Git tree entry for ${repositoryPath || 'unknown path'}`);
    if (prefix && !repositoryPath.startsWith(prefix)) continue;
    const packagePath = prefix ? repositoryPath.slice(prefix.length) : repositoryPath;
    entries.set(packagePath, { mode: metadata[0], type: metadata[1], object: metadata[2], repository_path: repositoryPath });
  }
  return entries;
}
const sourceCommitTree = commitTreeEntries(sourceCommit);
const commitBlobSha256Cache = new Map();
function commitBlobSha256(object) {
  if (commitBlobSha256Cache.has(object)) return commitBlobSha256Cache.get(object);
  const result = gitResult(['cat-file', 'blob', object]);
  if (result.status !== 0) fail(`could not read Git blob ${object} from source commit`);
  const digest = createHash('sha256').update(result.stdout).digest('hex');
  commitBlobSha256Cache.set(object, digest);
  return digest;
}
function repositoryPath(path) { return repositoryPrefix ? `${repositoryPrefix}/${path}` : path; }
function isGitIgnored(path) {
  return gitResult(['check-ignore', '-q', '--', repositoryPath(path)]).status === 0;
}
function contentDigest(root, files) {
  const hash = createHash('sha256');
  for (const file of files) hash.update(`${file}\0${sha256(join(root, file))}\n`);
  return hash.digest('hex');
}
function collectSourceFiles(source, prefix = '') {
  const result = [];
  for (const entry of readdirSync(source, { withFileTypes: true })) {
    const rel = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isSymbolicLink()) fail(`symlink is not allowed in release source: ${rel}`);
    if (entry.isDirectory()) {
      if (!AUTO_IGNORED_DIRS.has(entry.name)) result.push(...collectSourceFiles(join(source, entry.name), rel));
    } else result.push(rel);
  }
  return result;
}
function assertSourceCompleteness() {
  for (const file of collectSourceFiles(sourceRoot)) {
    if (isExcluded(file) || isIncluded(file)) continue;
    fail(`source file is not covered by manifest include/exclude rules: ${file}`);
  }
}
function copySelected(source, target, prefix = '') {
  mkdirSync(target, { recursive: true });
  for (const entry of readdirSync(source, { withFileTypes: true })) {
    const rel = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isSymbolicLink()) fail(`symlink is not allowed in release source: ${rel}`);
    if (AUTO_IGNORED_DIRS.has(entry.name)) continue;
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
function containsAutoIgnoredSegment(path) {
  return path.split('/').some((segment) => AUTO_IGNORED_DIRS.has(segment));
}
function fileProvenance(files) {
  const records = files.map((path) => {
    const fileSha256 = sha256(join(stagingRoot, path));
    const treeEntry = sourceCommitTree.get(path);
    if (!treeEntry) {
      return {
        path,
        repository_path: repositoryPath(path),
        sha256: fileSha256,
        git_state: isGitIgnored(path) ? 'ignored' : 'untracked',
        commit_bound: false,
        commit_blob: null,
      };
    }
    if (treeEntry.type !== 'blob') fail(`selected source path is not a Git blob in ${sourceCommit}: ${treeEntry.repository_path}`);
    const committedSha256 = commitBlobSha256(treeEntry.object);
    return {
      path,
      repository_path: treeEntry.repository_path,
      sha256: fileSha256,
      git_state: committedSha256 === fileSha256 ? 'committed' : 'modified',
      commit_bound: committedSha256 === fileSha256,
      commit_blob: treeEntry.object,
      commit_sha256: committedSha256,
    };
  });
  const selected = new Set(files);
  const missingCommitFiles = [...sourceCommitTree.keys()]
    .filter((path) => !containsAutoIgnoredSegment(path) && isIncluded(path) && !isExcluded(path) && !selected.has(path))
    .sort();
  return {
    schema: 'git-file-provenance/v1',
    source_commit: sourceCommit,
    source_scope: sourceScope,
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
  fail(`selected sub-library release inputs are not reproducible from source commit ${sourceCommit}: ${details.join(', ')}${total > details.length ? `, ... ${total - details.length} more` : ''}`);
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

const validator = spawnSync(process.execPath, [join(sourceRoot, 'scripts/validate-sub-library.mjs'), ...(prepareMode ? ['--prepare'] : [])], { encoding: 'utf8' });
process.stdout.write(validator.stdout ?? '');
process.stderr.write(validator.stderr ?? '');
if (validator.status !== 0) fail('source sub-library validation failed; no release candidate created');
if (prepareMode && status !== 'Ready') fail('prepare mode requires release_status Ready');
if (prepareMode && approvalStatus !== 'pending') fail('prepare mode requires approval_status pending');
assertSourceCompleteness();

rmSync(stagingRoot, { recursive: true, force: true });
mkdirSync(stagingRoot, { recursive: true });
copySelected(sourceRoot, stagingRoot);
const files = collect(stagingRoot).sort();
for (const file of files) {
  if (!isIncluded(file)) fail(`candidate file is outside manifest include patterns: ${file}`);
  if (isExcluded(file)) fail(`candidate file matches manifest exclude pattern: ${file}`);
}
const provenance = fileProvenance(files);
if (requireCommitProvenance || finalRelease) assertCommitProvenance(provenance);
const manifest = {
  package_id: 'website-content-ops',
  package_kind: 'sub-library-release-candidate',
  version,
  release_status: status,
  maturity_status: typeof manifestFront.maturity_status === 'string' ? manifestFront.maturity_status.trim() : 'unknown',
  verification_status: typeof manifestFront.verification_status === 'string' ? manifestFront.verification_status.trim() : 'unknown',
  release_scope: typeof manifestFront.release_scope === 'string' ? manifestFront.release_scope.trim() : 'standalone-sub-library',
  license_status: typeof manifestFront.license_status === 'string' ? manifestFront.license_status.trim() : 'unknown',
  approval_required: manifestFront.approval_required === true,
  approval_status: approvalStatus,
  approval_record: typeof manifestFront.approval_record === 'string' ? manifestFront.approval_record.trim() : null,
  tag_namespace: typeof manifestFront.tag_namespace === 'string' ? manifestFront.tag_namespace.trim() : null,
  tag_prefix: typeof manifestFront.tag_prefix === 'string' ? manifestFront.tag_prefix.trim() : null,
  durable_roots: durableRoots,
  delivery_modes: manifestArray(manifestFront, 'delivery_modes'),
  skill_entrypoint: typeof manifestFront.skill_entrypoint === 'string' ? manifestFront.skill_entrypoint.trim() : null,
  skill_status: typeof manifestFront.skill_status === 'string' ? manifestFront.skill_status.trim() : null,
  external_dependencies: manifestArray(manifestFront, 'external_dependencies'),
  release_mode: 'latest-only',
  qualification_state: prepareMode ? 'prepared-unapproved' : 'working-candidate',
  dependency_mode: typeof manifestFront.dependency_mode === 'string' ? manifestFront.dependency_mode.trim() : 'unknown',
  runtime_contract: typeof manifestFront.runtime_contract === 'string' ? manifestFront.runtime_contract.trim() : null,
  source_package_only: manifestFront.source_package_only === true,
  included_in_mother: typeof manifestFront.included_in_mother === 'string' ? manifestFront.included_in_mother.trim() : null,
  source_scope: sourceScope,
  source_commit: sourceCommit,
  source_dirty: sourceDirty,
  source_selected_dirty: !provenance.commit_rebuildable,
  source_commit_rebuildable: provenance.commit_rebuildable,
  source_snapshot_kind: provenance.commit_rebuildable ? 'source-commit' : 'working-tree-snapshot',
  source_provenance: provenance,
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
const candidateValidator = spawnSync(process.execPath, [join(stagingRoot, 'scripts/validate-sub-library.mjs'), ...(prepareMode ? ['--prepare'] : [])], { encoding: 'utf8' });
process.stdout.write(candidateValidator.stdout ?? '');
process.stderr.write(candidateValidator.stderr ?? '');
if (candidateValidator.status !== 0) fail('generated sub-library candidate failed its own validation');
const artifactValidator = spawnSync(process.execPath, [join(stagingRoot, 'scripts/validate-artifact.mjs'), ...(prepareMode ? ['--prepare'] : []), stagingRoot], {
  encoding: 'utf8',
  env: { ...process.env },
});
process.stdout.write(artifactValidator.stdout ?? '');
process.stderr.write(artifactValidator.stderr ?? '');
if (artifactValidator.status !== 0) fail('generated sub-library candidate failed artifact validation');
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
