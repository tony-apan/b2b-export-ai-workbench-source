#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { basename, resolve } from 'node:path';
import { existsSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import {
  EVIDENCE_DIGEST_ALGORITHM,
  TRUSTED_EVIDENCE_SCHEMA,
  TRUSTED_EVIDENCE_SOURCE,
} from './lib/release-evidence-contract.mjs';

const args = process.argv.slice(2);
const flag = (name) => { const index = args.indexOf(name); return index >= 0 ? args[index + 1] : ''; };
const fail = (message) => { console.error(`BLOCK: ${message}`); process.exit(1); };
function canonicalJson(value) {
  if (value === null || ['boolean', 'string'].includes(typeof value)) return JSON.stringify(value);
  if (typeof value === 'number' && Number.isFinite(value)) return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  fail('approval or evidence contains a non-canonical JSON value');
}
const digest = (value) => createHash('sha256').update(canonicalJson(value), 'utf8').digest('hex');
const approvalPath = resolve(flag('--approval-intent') || '');
const evidencePath = resolve(flag('--evidence') || '');
const outputPath = resolve(flag('--output') || '');
for (const [label, path] of [['approval intent', approvalPath], ['evidence', evidencePath]]) {
  if (!path || !existsSync(path) || !statSync(path).isFile()) fail(`${label} is missing: ${path}`);
}
if (!outputPath) fail('--output is required');
let approval; let evidence;
try { approval = JSON.parse(readFileSync(approvalPath, 'utf8')); } catch { fail('approval intent is invalid JSON'); }
try { evidence = JSON.parse(readFileSync(evidencePath, 'utf8')); } catch { fail('trusted evidence is invalid JSON'); }
if (approval.schema !== 'release-approval/v1') fail('approval intent schema must be release-approval/v1');
if (evidence.schema !== TRUSTED_EVIDENCE_SCHEMA) fail(`evidence schema must be ${TRUSTED_EVIDENCE_SCHEMA}`);
const validation = approval.validation;
if (!validation || typeof validation !== 'object' || Array.isArray(validation)) fail('approval intent validation must be an object');
if (validation.profile !== evidence.profile) fail('approval intent validation.profile must match trusted evidence profile');
if (validation.evidence_source !== TRUSTED_EVIDENCE_SOURCE) fail(`approval intent validation.evidence_source must be ${TRUSTED_EVIDENCE_SOURCE}`);
if (validation.evidence_digest_algorithm !== EVIDENCE_DIGEST_ALGORITHM) fail(`approval intent validation.evidence_digest_algorithm must be ${EVIDENCE_DIGEST_ALGORITHM}`);
for (const field of ['evidence_bundle', 'evidence_digest', 'completed_at']) {
  if (validation[field] !== null) fail(`dispatcher approval intent must leave validation.${field}=null; final evidence is generated only by the trusted job`);
}
if (approval.scope?.kind !== evidence.scope?.kind || approval.scope?.id !== evidence.scope?.id || approval.scope?.package_kind !== evidence.scope?.package_kind) fail('approval intent scope does not match trusted evidence');
if (approval.source?.commit !== evidence.source?.commit || approval.source?.dirty !== evidence.source?.dirty) fail('approval intent source does not match trusted evidence');
if (approval.candidate?.content_digest !== evidence.candidate?.content_digest || approval.candidate?.manifest_sha256 !== evidence.candidate?.manifest_sha256 || approval.candidate?.sha256sums_sha256 !== evidence.candidate?.sha256sums_sha256) fail('approval intent candidate does not match trusted evidence');
const finalized = structuredClone(approval);
finalized.validation.evidence_bundle = basename(evidencePath);
finalized.validation.evidence_digest = digest(evidence);
finalized.validation.completed_at = evidence.completed_at;
writeFileSync(outputPath, `${JSON.stringify(finalized, null, 2)}\n`, { mode: 0o600 });
console.log(`FINALIZED_RELEASE_APPROVAL: ${outputPath}`);
console.log(`TRUSTED_EVIDENCE_SHA256: ${finalized.validation.evidence_digest}`);
