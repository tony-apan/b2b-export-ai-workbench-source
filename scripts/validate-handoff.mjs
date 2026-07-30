#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { existsSync, lstatSync, readFileSync, realpathSync, statSync } from 'node:fs';
import { isAbsolute, join, normalize, relative } from 'node:path';
import { isPrivateOrLocalHost } from './lib/public-network-policy.mjs';

const repoRoot = process.cwd();
const realRepoRoot = realpathSync(repoRoot);
const schemaPath = join(repoRoot, 'scripts/schemas/handoff.schema.json');
const pinnedSchemaSha256 = '86c6123e1ea00c7d5b1742ee8d42abecf65b94212c8be72662373e4aa091bb07';
const sha256Pattern = /^sha256:[0-9a-f]{64}$/;
const commitPattern = /^[0-9a-f]{40}$/;
const handoffIdPattern = /^HND-[0-9]{8}-[A-Z0-9-]+-[0-9]{4}$/;
const args = process.argv.slice(2);
const releaseMode = args.includes('--release');
const fileIndex = args.indexOf('--file');
const recordArg = fileIndex >= 0 ? args[fileIndex + 1] : null;
const consumed = new Set(releaseMode ? ['--release'] : []);
if (fileIndex >= 0) {
  consumed.add('--file');
  if (recordArg) consumed.add(recordArg);
}
const unknownArgs = args.filter((arg) => !consumed.has(arg));
const failures = [];

function fail(message) {
  failures.push(message);
}

function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

function exactKeys(value, expected, location) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    fail(`${location} must be an object`);
    return false;
  }
  const actual = Object.keys(value).sort();
  const wanted = [...expected].sort();
  if (JSON.stringify(actual) !== JSON.stringify(wanted)) {
    fail(`${location} keys must be exactly: ${wanted.join(', ')}`);
    return false;
  }
  return true;
}

function nonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

function compareText(left, right) {
  return left < right ? -1 : left > right ? 1 : 0;
}

function canonicalizeRefs(refs) {
  return refs
    .map((ref) => ({ kind: ref.kind, locator: ref.locator, sha256: ref.sha256 }))
    .sort((left, right) => compareText(
      `${left.kind}\0${left.locator}\0${left.sha256}`,
      `${right.kind}\0${right.locator}\0${right.sha256}`,
    ));
}

function refKey(ref) {
  return `${ref.kind}\0${ref.locator}\0${ref.sha256}`;
}


function validateRef(ref, location, { externalOnly = false } = {}) {
  if (!exactKeys(ref, ['kind', 'locator', 'sha256'], location)) return false;
  if (!['repository-relative', 'immutable-https'].includes(ref.kind)) {
    fail(`${location}.kind must be repository-relative or immutable-https`);
    return false;
  }
  if (externalOnly && ref.kind !== 'immutable-https') {
    fail(`${location} must be an external immutable-https attestation`);
    return false;
  }
  if (!nonEmptyString(ref.locator)) {
    fail(`${location}.locator must be a non-empty string`);
    return false;
  }
  if (!sha256Pattern.test(ref.sha256 ?? '')) {
    fail(`${location}.sha256 must use sha256:<64 lowercase hex>`);
    return false;
  }

  if (ref.kind === 'repository-relative') {
    if (isAbsolute(ref.locator) || ref.locator.includes('\\') || ref.locator.startsWith('~') || /[?#]/.test(ref.locator)) {
      fail(`${location}.locator is not a clean repository-relative path`);
      return false;
    }
    const segments = ref.locator.split('/');
    if (segments.some((segment) => !segment || segment === '.' || segment === '..')) {
      fail(`${location}.locator contains an empty or dot segment`);
      return false;
    }
    if (normalize(ref.locator).replaceAll('\\', '/') !== ref.locator) {
      fail(`${location}.locator is not normalized`);
      return false;
    }
    let target = repoRoot;
    for (const segment of segments) {
      target = join(target, segment);
      if (!existsSync(target)) {
        fail(`${location} repository evidence file does not exist: ${ref.locator}`);
        return false;
      }
      if (lstatSync(target).isSymbolicLink()) {
        fail(`${location} repository evidence locator must not traverse a symlink: ${ref.locator}`);
        return false;
      }
    }
    if (!statSync(target).isFile()) {
      fail(`${location} repository evidence locator is not a file: ${ref.locator}`);
      return false;
    }
    const resolved = realpathSync(target);
    const resolvedRelative = relative(realRepoRoot, resolved);
    if (!resolvedRelative || resolvedRelative.startsWith('..') || isAbsolute(resolvedRelative)) {
      fail(`${location} repository evidence locator escapes repository root: ${ref.locator}`);
      return false;
    }
    const actual = `sha256:${sha256(readFileSync(target))}`;
    if (actual !== ref.sha256) {
      fail(`${location} repository evidence digest mismatch; expected ${actual}`);
      return false;
    }
    return true;
  }

  let url;
  try {
    url = new URL(ref.locator);
  } catch {
    fail(`${location}.locator is not a valid URL`);
    return false;
  }
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash || isPrivateOrLocalHost(url.hostname)) {
    fail(`${location}.locator must be public HTTPS without credentials, query, fragment, or private host`);
    return false;
  }
  let segments;
  try {
    segments = url.pathname.split('/').filter(Boolean).map((segment) => decodeURIComponent(segment).toLowerCase());
  } catch {
    fail(`${location}.locator contains invalid percent-encoding`);
    return false;
  }
  if (segments.some((segment) => ['.', '..', 'latest', 'tmp', 'temp'].includes(segment))) {
    fail(`${location}.locator contains a mutable or dot segment`);
    return false;
  }
  if (!url.pathname.toLowerCase().includes(ref.sha256.slice(7))) {
    fail(`${location}.locator path must contain the exact sha256`);
    return false;
  }
  return true;
}

function validateParty(value, location) {
  if (!exactKeys(value, ['name', 'agent_id'], location)) return;
  if (!nonEmptyString(value.name)) fail(`${location}.name must be non-empty`);
  if (!(value.agent_id === null || nonEmptyString(value.agent_id))) fail(`${location}.agent_id must be null or a non-empty string`);
}

function expectedBinding(record) {
  return {
    handoff_id: record.handoff_id,
    scope: record.scope,
    reviewer_agent_id: record.reviewer?.agent_id,
    source_commit: record.scope_binding?.source_commit,
    content_digest: record.scope_binding?.content_digest,
    verdict: record.verdict,
  };
}

function validateBinding(binding, record, location) {
  if (!exactKeys(binding, ['handoff_id', 'scope', 'reviewer_agent_id', 'source_commit', 'content_digest', 'verdict'], location)) return false;
  const expected = expectedBinding(record);
  let valid = true;
  for (const key of Object.keys(expected)) {
    if (binding[key] !== expected[key]) {
      fail(`${location}.${key} does not bind the handoff scope/reviewer/source exactly`);
      valid = false;
    }
  }
  return valid;
}

function canonicalExternalStatement(record, claimType) {
  return JSON.stringify({ schema_version: 1, claim_type: claimType, ...expectedBinding(record) });
}

function validateExternalStatementRef(ref, record, claimType, location) {
  const expectedDigest = `sha256:${sha256(canonicalExternalStatement(record, claimType))}`;
  if (ref?.sha256 !== expectedDigest) {
    fail(`${location}.sha256 does not bind the canonical ${claimType} statement; expected ${expectedDigest}`);
    return false;
  }
  return true;
}

function validateAttestation(attestation, record, name, location) {
  if (attestation === null) return false;
  if (!exactKeys(attestation, ['ref', 'binding'], location)) return false;
  const validRef = validateRef(attestation.ref, `${location}.ref`, { externalOnly: true });
  const validBinding = validateBinding(attestation.binding, record, `${location}.binding`);
  const validDigestBinding = validateExternalStatementRef(attestation.ref, record, `attestation:${name}`, location);
  return validRef && validBinding && validDigestBinding;
}

function validateSchemaIntegrity() {
  if (!existsSync(schemaPath) || !statSync(schemaPath).isFile()) {
    fail('handoff schema is missing: scripts/schemas/handoff.schema.json');
    return;
  }
  const bytes = readFileSync(schemaPath);
  const digest = sha256(bytes);
  if (digest !== pinnedSchemaSha256) {
    fail(`handoff schema digest mismatch; expected sha256:${pinnedSchemaSha256}, got sha256:${digest}`);
    return;
  }
  try {
    const schema = JSON.parse(bytes.toString('utf8'));
    if (schema.$id !== 'urn:701-kecheng:handoff:v1' || schema.type !== 'object') fail('handoff schema identity is invalid');
  } catch {
    fail('handoff schema is not valid JSON');
  }
}

function validateScopeManifestBinding(scopeBinding) {
  if (!scopeBinding || scopeBinding.source_commit_binding !== 'content-bound') return;
  const ref = scopeBinding.scope_manifest;
  if (!ref || ref.kind !== 'repository-relative') {
    fail('content-bound scope_manifest must be repository-relative so its commit and bytes can be verified locally');
    return;
  }
  let manifest;
  try {
    manifest = JSON.parse(readFileSync(join(repoRoot, ref.locator), 'utf8'));
  } catch {
    fail('content-bound scope_manifest must be valid JSON');
    return;
  }
  if (!manifest || typeof manifest !== 'object' || Array.isArray(manifest)) {
    fail('content-bound scope_manifest must be a JSON object');
    return;
  }
  const declaredCommits = [manifest.source_commit, manifest.head].filter((value) => value !== undefined);
  if (declaredCommits.length === 0 || declaredCommits.some((value) => !commitPattern.test(value))) {
    fail('content-bound scope_manifest must declare a 40-hex source_commit or head');
  } else if (new Set(declaredCommits).size !== 1) {
    fail('content-bound scope_manifest source_commit and head disagree');
  } else if (declaredCommits[0] !== scopeBinding.source_commit) {
    fail('scope_binding.source_commit does not match the content-bound scope_manifest commit');
  }
  if (scopeBinding.content_digest !== ref.sha256) {
    fail('scope_binding.content_digest must equal the verified scope_manifest byte digest');
  }
}

function validateRecord(record) {
  const topKeys = [
    'schema_version', 'handoff_id', 'scope', 'producer', 'reviewer', 'reviewer_provenance',
    'identity_status', 'independence_status', 'scope_binding', 'original_verdict',
    'attestations', 'verdict', 'blocks_next_step', 'evidence_refs', 'evidence_bundle_digest',
    'not_verified', 'return_to', 'approval_required',
  ];
  if (!exactKeys(record, topKeys, 'handoff record')) return;
  if (record.schema_version !== 1) fail('schema_version must be 1');
  if (!handoffIdPattern.test(record.handoff_id ?? '')) fail('handoff_id must match HND-YYYYMMDD-NAME-####');
  if (!nonEmptyString(record.scope)) fail('scope must be non-empty');
  validateParty(record.producer, 'producer');
  validateParty(record.reviewer, 'reviewer');
  if (!['producer-reported', 'reviewer-authored', 'externally-attested'].includes(record.reviewer_provenance)) {
    fail('reviewer_provenance is invalid');
  }
  if (!['verified', 'not_verified'].includes(record.identity_status)) fail('identity_status is invalid');
  if (!['verified', 'not_verified'].includes(record.independence_status)) fail('independence_status is invalid');
  if (!['pass', 'warn', 'block', 'needs_tony'].includes(record.verdict)) fail('verdict is invalid');
  if (typeof record.blocks_next_step !== 'boolean') fail('blocks_next_step must be boolean');
  if (['block', 'needs_tony'].includes(record.verdict) && record.blocks_next_step !== true) fail(`${record.verdict} must set blocks_next_step=true`);
  if (['pass', 'warn'].includes(record.verdict) && record.blocks_next_step !== false) fail(`${record.verdict} must set blocks_next_step=false`);

  if (exactKeys(record.scope_binding, ['scope_manifest', 'source_commit', 'source_commit_binding', 'content_digest'], 'scope_binding')) {
    validateRef(record.scope_binding.scope_manifest, 'scope_binding.scope_manifest');
    if (!(record.scope_binding.source_commit === null || commitPattern.test(record.scope_binding.source_commit))) fail('scope_binding.source_commit must be null or 40 lowercase hex');
    if (!['content-bound', 'context-only', 'not-recorded'].includes(record.scope_binding.source_commit_binding)) fail('scope_binding.source_commit_binding is invalid');
    if (!(record.scope_binding.content_digest === null || sha256Pattern.test(record.scope_binding.content_digest))) fail('scope_binding.content_digest must be null or sha256:<64 lowercase hex>');
    validateScopeManifestBinding(record.scope_binding);
  }

  if (exactKeys(record.original_verdict, ['available', 'immutable', 'ref', 'binding'], 'original_verdict')) {
    if (typeof record.original_verdict.available !== 'boolean' || typeof record.original_verdict.immutable !== 'boolean') fail('original_verdict available/immutable must be boolean');
    if (record.original_verdict.ref !== null) {
      validateRef(record.original_verdict.ref, 'original_verdict.ref', { externalOnly: record.original_verdict.immutable });
      validateExternalStatementRef(record.original_verdict.ref, record, 'original-verdict', 'original_verdict.ref');
    }
    if (record.original_verdict.binding !== null) validateBinding(record.original_verdict.binding, record, 'original_verdict.binding');
    if (!record.original_verdict.available && (record.original_verdict.immutable || record.original_verdict.ref !== null || record.original_verdict.binding !== null)) {
      fail('unavailable original_verdict must not claim immutable ref or binding');
    }
    if (record.original_verdict.available && (!record.original_verdict.ref || !record.original_verdict.binding)) fail('available original_verdict requires ref and exact binding');
    if (record.original_verdict.immutable && record.original_verdict.ref?.kind !== 'immutable-https') fail('immutable original_verdict requires immutable-https ref');
  }

  const attestationsPresent = {};
  if (exactKeys(record.attestations, ['identity', 'independence', 'reviewer_authorship'], 'attestations')) {
    for (const name of ['identity', 'independence', 'reviewer_authorship']) {
      attestationsPresent[name] = validateAttestation(record.attestations[name], record, name, `attestations.${name}`);
    }
  }
  if (record.identity_status === 'verified' && !attestationsPresent.identity) fail('identity_status=verified requires external identity attestation');
  if (record.independence_status === 'verified' && !attestationsPresent.independence) fail('independence_status=verified requires external independence attestation');
  if (['reviewer-authored', 'externally-attested'].includes(record.reviewer_provenance) && !attestationsPresent.reviewer_authorship) {
    fail(`${record.reviewer_provenance} requires external reviewer_authorship attestation`);
  }
  if (record.reviewer_provenance === 'reviewer-authored' && !(record.original_verdict?.available && record.original_verdict?.immutable)) {
    fail('reviewer-authored provenance requires an available immutable original verdict');
  }

  let refs = [];
  if (!Array.isArray(record.evidence_refs) || record.evidence_refs.length === 0) {
    fail('evidence_refs must be a non-empty array');
  } else {
    refs = record.evidence_refs;
    const seen = new Set();
    for (let index = 0; index < refs.length; index += 1) {
      validateRef(refs[index], `evidence_refs[${index}]`);
      if (refs[index] && typeof refs[index] === 'object') {
        const key = refKey(refs[index]);
        if (seen.has(key)) fail(`duplicate evidence_refs entry at index ${index}`);
        seen.add(key);
      }
    }
  }
  if (!sha256Pattern.test(record.evidence_bundle_digest ?? '')) {
    fail('evidence_bundle_digest must use sha256:<64 lowercase hex>');
  } else {
    const expected = `sha256:${sha256(JSON.stringify(canonicalizeRefs(refs)))}`;
    if (record.evidence_bundle_digest !== expected) fail(`evidence_bundle_digest mismatch; expected ${expected}`);
  }

  const bundleKeys = new Set(refs.filter((ref) => ref && typeof ref === 'object').map(refKey));
  const requiredRefs = [record.scope_binding?.scope_manifest, record.original_verdict?.ref];
  for (const name of ['identity', 'independence', 'reviewer_authorship']) requiredRefs.push(record.attestations?.[name]?.ref);
  for (const ref of requiredRefs.filter(Boolean)) {
    if (!bundleKeys.has(refKey(ref))) fail(`qualification ref is outside evidence_refs bundle: ${ref.locator}`);
  }

  if (!Array.isArray(record.not_verified) || record.not_verified.length === 0 || record.not_verified.some((item) => !nonEmptyString(item))) {
    fail('not_verified must be a non-empty array of explicit boundaries');
  }
  if (!nonEmptyString(record.return_to)) fail('return_to must be non-empty');
  if (!nonEmptyString(record.approval_required)) fail('approval_required must be non-empty');

  if (record.verdict === 'pass') {
    if (record.reviewer_provenance === 'producer-reported') fail('pass cannot use producer-reported reviewer provenance');
    if (record.identity_status !== 'verified' || record.independence_status !== 'verified') fail('pass requires verified identity_status and independence_status');
    if (!nonEmptyString(record.reviewer?.agent_id)) fail('pass requires reviewer.agent_id bound by external attestations');
    if (record.producer?.agent_id && record.producer.agent_id === record.reviewer?.agent_id) fail('pass reviewer and producer agent_id must differ');
    if (record.producer?.name === record.reviewer?.name) fail('pass reviewer and producer names must differ');
    if (!commitPattern.test(record.scope_binding?.source_commit ?? '') || record.scope_binding?.source_commit_binding !== 'content-bound') fail('pass requires a content-bound 40-hex source_commit');
    if (!sha256Pattern.test(record.scope_binding?.content_digest ?? '')) fail('pass requires content_digest');
    if (!(record.original_verdict?.available && record.original_verdict?.immutable && record.original_verdict?.ref?.kind === 'immutable-https')) fail('pass requires an available immutable external original verdict');
    for (const name of ['identity', 'independence', 'reviewer_authorship']) {
      if (!attestationsPresent[name]) fail(`pass requires external ${name} attestation`);
    }
  }
}

validateSchemaIntegrity();
if (unknownArgs.length > 0) fail(`unknown arguments: ${unknownArgs.join(' ')}`);
if (!recordArg) fail('usage: node scripts/validate-handoff.mjs --file <repository-relative-json> [--release]');

let record = null;
if (recordArg) {
  if (isAbsolute(recordArg) || recordArg.includes('\\') || recordArg.startsWith('~') || /[?#]/.test(recordArg)
    || recordArg.split('/').some((segment) => !segment || segment === '.' || segment === '..')) {
    fail('--file must be a clean repository-relative path');
  } else {
    const recordPath = join(repoRoot, recordArg);
    if (!existsSync(recordPath) || !statSync(recordPath).isFile()) fail(`handoff file does not exist: ${recordArg}`);
    else {
      try {
        record = JSON.parse(readFileSync(recordPath, 'utf8'));
      } catch {
        fail(`handoff file is not valid JSON: ${recordArg}`);
      }
    }
  }
}
if (record) validateRecord(record);
if (releaseMode && record?.verdict !== 'pass') fail('release mode requires verdict=pass and all pass cross-constraints');

console.log('HANDOFF_VALIDATION_SCOPE: schema-integrity-and-declared-binding-only; remote_locator_retrieval=not_performed; human_identity=not_verified_locally; independence=not_verified_locally');
if (failures.length > 0) {
  console.log('HANDOFF_VALIDATION_FAILURES');
  for (const message of failures) console.log(`- ${message}`);
  console.log(`SUMMARY: failures=${failures.length} release=${releaseMode}`);
  process.exitCode = 1;
} else {
  console.log('HANDOFF_RECORD_STRUCTURE_PASS');
  console.log('HANDOFF_FACTUAL_VERDICT: not_verified');
  console.log(`SUMMARY: verdict=${record.verdict} evidence_refs=${record.evidence_refs.length} release=${releaseMode}`);
}
