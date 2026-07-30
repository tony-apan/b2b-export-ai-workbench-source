#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { existsSync, lstatSync, readFileSync, readdirSync, realpathSync, statSync } from 'node:fs';
import { isAbsolute, join, normalize, relative } from 'node:path';
import { isPrivateOrLocalHost } from './lib/public-network-policy.mjs';

const repoRoot = process.cwd();
const realRepoRoot = realpathSync(repoRoot);
const logsRoot = join(repoRoot, 'wiki/00_meta/logs');
const baselinePath = join(repoRoot, 'scripts/log-legacy-digest-baseline.json');
const pinnedBaselineFileSha256 = '06793ae8bd645720cbc00aaa4af3597fbd12d444fb09e41798f48dbe1f9836e7';
const args = process.argv.slice(2);
const releaseMode = args.includes('--release');
const closureJsonMode = args.includes('--closure-json');
const unknownArgs = args.filter((arg) => !['--release', '--closure-json'].includes(arg));

const eventIdPattern = /^EVT-(\d{4})(\d{2})(\d{2})-(\d{4})$/;
const scopeShardId = '[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?';
const dailyLogPathPattern = new RegExp(`^(\\d{4})/(\\d{2})/(\\d{4}-\\d{2}-\\d{2})(?:--(mother-library|sub-library-(${scopeShardId})|private-runtime-(${scopeShardId})))?\\.md$`);
const isoTimestampPattern = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/;
const sha256Pattern = /^sha256:[0-9a-f]{64}$/;
const futureToleranceMs = 5 * 60 * 1000;
const requiredValueFields = ['actor', 'scope', 'action', 'result', 'risk', 'next'];
const requiredPresenceFields = ['evidence', 'commands', 'files changed', 'writeback'];
const v2RequiredValueFields = [
  'occurred_at',
  'recorded_at',
  'correction_of',
  'evidence_summary_digest',
  'event_digest',
];

const legacyCutoffs = new Map([
  ['wiki/00_meta/logs/2026/07/2026-07-28.md', 'EVT-20260728-0017'],
  ['wiki/00_meta/logs/2026/07/2026-07-29.md', 'EVT-20260729-0008'],
]);

// These two events predate the evidence_role/evidence_refs naming clarification.
// Their event_digest remains valid because evidence_digest is accepted only for
// these exact IDs as a historical alias of evidence_summary_digest.
const legacyEvidenceSummaryAliases = new Set([
  'wiki/00_meta/logs/2026/07/2026-07-29.md#EVT-20260729-0009',
  'wiki/00_meta/logs/2026/07/2026-07-29.md#EVT-20260729-0010',
]);

const fieldAliases = new Map([
  ['actor', 'actor'],
  ['scope', 'scope'],
  ['action', 'action'],
  ['evidence', 'evidence'],
  ['commands', 'commands'],
  ['command', 'commands'],
  ['命令', 'commands'],
  ['files changed', 'files changed'],
  ['files_changed', 'files changed'],
  ['file changed', 'files changed'],
  ['变更文件', 'files changed'],
  ['文件变更', 'files changed'],
  ['result', 'result'],
  ['risk', 'risk'],
  ['risk / blocker', 'risk'],
  ['risk/blocker', 'risk'],
  ['风险', 'risk'],
  ['风险 / 阻塞', 'risk'],
  ['next', 'next'],
  ['writeback', 'writeback'],
  ['写回', 'writeback'],
  ['occurred_at', 'occurred_at'],
  ['occurred at', 'occurred_at'],
  ['time', 'occurred_at'],
  ['时间', 'occurred_at'],
  ['recorded_at', 'recorded_at'],
  ['recorded at', 'recorded_at'],
  ['correction_of', 'correction_of'],
  ['correction of', 'correction_of'],
  ['evidence_digest', 'evidence_summary_digest'],
  ['evidence digest', 'evidence_summary_digest'],
  ['evidence_summary_digest', 'evidence_summary_digest'],
  ['evidence summary digest', 'evidence_summary_digest'],
  ['evidence_role', 'evidence_role'],
  ['evidence role', 'evidence_role'],
  ['evidence_refs', 'evidence_refs'],
  ['evidence refs', 'evidence_refs'],
  ['evidence_bundle_digest', 'evidence_bundle_digest'],
  ['evidence bundle digest', 'evidence_bundle_digest'],
  ['event_digest', 'event_digest'],
  ['event digest', 'event_digest'],
]);

const warnings = [];
const failures = [];
const eventsById = new Map();
const eventRecords = [];
const legacyRecordsByKey = new Map();
let dailyLogFiles = 0;
let noEventLogFiles = 0;
let eventCount = 0;
let legacyEventCount = 0;
let v2EventCount = 0;
let qualificationEvidenceEvents = 0;
let legacyBaseline = null;
let correctionClosure = { schema_version: 1, effective: [], superseded: [] };

function fail(message) {
  failures.push(message);
}

function warn(message) {
  warnings.push(message);
}

function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

function normalizeFieldLabel(value) {
  return value.trim().toLowerCase().replace(/[_-]+/g, ' ').replace(/\s+/g, ' ');
}

function isValidDate(date) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date);
  if (!match) return false;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return parsed.getUTCFullYear() === year
    && parsed.getUTCMonth() === month - 1
    && parsed.getUTCDate() === day;
}

function parseFrontmatter(lines, displayPath) {
  if (lines[0]?.trim() !== '---') return new Map();
  const values = new Map();
  for (let index = 1; index < lines.length; index += 1) {
    if (lines[index].trim() === '---') break;
    const match = /^([A-Za-z0-9_-]+):\s*(.*)$/.exec(lines[index]);
    if (!match) continue;
    const key = match[1];
    const value = match[2].trim().replace(/^(["'])(.*)\1$/, '$2');
    if (values.has(key)) fail(`${displayPath}: front matter contains duplicate key \`${key}\``);
    else values.set(key, value);
  }
  return values;
}

function parseTimestamp(value, { legacy = false } = {}) {
  if (isoTimestampPattern.test(value)) {
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }
  if (!legacy) return null;
  if (/^\d{4}-\d{2}-\d{2}$/.test(value) && isValidDate(value)) {
    return new Date(`${value}T00:00:00+08:00`);
  }
  const cstMatch = /^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})(?::(\d{2}))?\s+CST$/.exec(value);
  if (cstMatch && isValidDate(cstMatch[1])) {
    const parsed = new Date(`${cstMatch[1]}T${cstMatch[2]}:${cstMatch[3] ?? '00'}+08:00`);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }
  return null;
}

function canonicalEventPayload(id, fields) {
  const payload = {
    event_id: id,
    occurred_at: fields.get('occurred_at'),
    recorded_at: fields.get('recorded_at'),
    actor: fields.get('actor'),
    scope: fields.get('scope'),
    action: fields.get('action'),
    evidence: fields.get('evidence'),
    commands: fields.get('commands'),
    files_changed: fields.get('files changed'),
    result: fields.get('result'),
    risk: fields.get('risk'),
    next: fields.get('next'),
    writeback: fields.get('writeback'),
    correction_of: fields.get('correction_of'),
    // Keep the historical canonical JSON property name so EVT-0009/0010 do
    // not need their event bodies rewritten merely for the naming correction.
    evidence_digest: fields.get('evidence_summary_digest'),
  };
  if (fields.has('evidence_role')) payload.evidence_role = fields.get('evidence_role');
  if (fields.has('evidence_refs')) payload.evidence_refs = fields.get('evidence_refs');
  if (fields.has('evidence_bundle_digest')) payload.evidence_bundle_digest = fields.get('evidence_bundle_digest');
  return JSON.stringify(payload);
}

function canonicalLegacyCard(headerLine, bodyLines) {
  const lines = [headerLine, ...bodyLines].map((line) => line.replace(/[ \t]+$/g, ''));
  while (lines.length > 0 && lines.at(-1).trim() === '') lines.pop();
  return lines.join('\n');
}

function walk(directory) {
  const files = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const fullPath = join(directory, entry.name);
    if (entry.isDirectory()) files.push(...walk(fullPath));
    else if (entry.isFile()) files.push(fullPath);
  }
  return files;
}

function addEventOccurrence(id, location) {
  const occurrences = eventsById.get(id) ?? [];
  occurrences.push(location);
  eventsById.set(id, occurrences);
}

function isLegacyAllowed(displayPath, id, declaredCutoff) {
  const configuredCutoff = legacyCutoffs.get(displayPath);
  if (!configuredCutoff || declaredCutoff !== configuredCutoff) return false;
  if (!eventIdPattern.test(id) || !eventIdPattern.test(configuredCutoff)) return false;
  return id <= configuredCutoff;
}

function canonicalizeEvidenceRefs(refs) {
  return refs
    .map((ref) => ({ kind: ref.kind, locator: ref.locator, sha256: ref.sha256 }))
    .sort((left, right) => {
      const leftKey = `${left.kind}\0${left.locator}\0${left.sha256}`;
      const rightKey = `${right.kind}\0${right.locator}\0${right.sha256}`;
      return leftKey < rightKey ? -1 : leftKey > rightKey ? 1 : 0;
    });
}


function validateEvidenceRef(ref, location) {
  if (!ref || typeof ref !== 'object' || Array.isArray(ref)) {
    fail(`${location}: every evidence_refs entry must be an object`);
    return false;
  }
  const keys = Object.keys(ref).sort();
  if (JSON.stringify(keys) !== JSON.stringify(['kind', 'locator', 'sha256'])) {
    fail(`${location}: evidence ref keys must be exactly kind, locator, sha256`);
    return false;
  }
  if (!['repository-relative', 'immutable-https'].includes(ref.kind)) {
    fail(`${location}: evidence ref kind must be repository-relative or immutable-https`);
    return false;
  }
  if (typeof ref.locator !== 'string' || !ref.locator) {
    fail(`${location}: evidence ref locator must be a non-empty string`);
    return false;
  }
  if (typeof ref.sha256 !== 'string' || !sha256Pattern.test(ref.sha256)) {
    fail(`${location}: evidence ref sha256 must use sha256:<64 lowercase hex>`);
    return false;
  }

  if (ref.kind === 'repository-relative') {
    if (isAbsolute(ref.locator) || ref.locator.includes('\\') || ref.locator.startsWith('~') || /[?#]/.test(ref.locator)) {
      fail(`${location}: repository-relative locator is not a clean repository path: ${ref.locator}`);
      return false;
    }
    const segments = ref.locator.split('/');
    if (segments.some((segment) => !segment || segment === '.' || segment === '..')) {
      fail(`${location}: repository-relative locator contains an empty or dot segment: ${ref.locator}`);
      return false;
    }
    const normalized = normalize(ref.locator).replaceAll('\\', '/');
    if (normalized !== ref.locator) {
      fail(`${location}: repository-relative locator is not normalized: ${ref.locator}`);
      return false;
    }
    let target = repoRoot;
    for (const segment of segments) {
      target = join(target, segment);
      if (!existsSync(target)) {
        fail(`${location}: repository evidence file does not exist: ${ref.locator}`);
        return false;
      }
      if (lstatSync(target).isSymbolicLink()) {
        fail(`${location}: repository evidence locator must not traverse a symlink: ${ref.locator}`);
        return false;
      }
    }
    if (!statSync(target).isFile()) {
      fail(`${location}: repository evidence locator is not a file: ${ref.locator}`);
      return false;
    }
    const resolved = realpathSync(target);
    const resolvedRelative = relative(realRepoRoot, resolved);
    if (!resolvedRelative || resolvedRelative.startsWith('..') || isAbsolute(resolvedRelative)) {
      fail(`${location}: repository evidence locator escapes repository root: ${ref.locator}`);
      return false;
    }
    const actual = `sha256:${sha256(readFileSync(target))}`;
    if (actual !== ref.sha256) {
      fail(`${location}: repository evidence digest mismatch for ${ref.locator}; expected ${actual}`);
      return false;
    }
    return true;
  }

  let url;
  try {
    url = new URL(ref.locator);
  } catch {
    fail(`${location}: immutable-https locator is not a valid URL`);
    return false;
  }
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash || isPrivateOrLocalHost(url.hostname)) {
    fail(`${location}: immutable-https locator must be public HTTPS without credentials, query, fragment, or private host`);
    return false;
  }
  let segments;
  try {
    segments = url.pathname.split('/').filter(Boolean).map((segment) => decodeURIComponent(segment).toLowerCase());
  } catch {
    fail(`${location}: immutable-https locator contains invalid percent-encoding`);
    return false;
  }
  if (segments.some((segment) => ['.', '..', 'latest', 'tmp', 'temp'].includes(segment))) {
    fail(`${location}: immutable-https locator contains a mutable or dot segment`);
    return false;
  }
  const digestHex = ref.sha256.slice('sha256:'.length);
  if (!url.pathname.toLowerCase().includes(digestHex)) {
    fail(`${location}: immutable-https locator path must contain the exact evidence sha256`);
    return false;
  }
  return true;
}

function validateEvidenceContract(id, displayPath, fields, labelsByCanonical, location) {
  const evidence = fields.get('evidence') ?? '';
  const expectedSummaryDigest = `sha256:${sha256(evidence)}`;
  const summaryDigest = fields.get('evidence_summary_digest');
  if (summaryDigest && !sha256Pattern.test(summaryDigest)) {
    fail(`${location}: evidence_summary_digest must use sha256:<64 lowercase hex>`);
  } else if (summaryDigest && summaryDigest !== expectedSummaryDigest) {
    fail(`${location}: evidence_summary_digest mismatch; expected ${expectedSummaryDigest}`);
  }

  const labels = labelsByCanonical.get('evidence_summary_digest') ?? [];
  const usedLegacyAlias = labels.some((label) => normalizeFieldLabel(label) === 'evidence digest');
  const eventKey = `${displayPath}#${id}`;
  if (usedLegacyAlias && !legacyEvidenceSummaryAliases.has(eventKey)) {
    fail(`${location}: evidence_digest is a frozen historical alias; new events must use evidence_summary_digest`);
  }

  const grandfathered = legacyEvidenceSummaryAliases.has(eventKey);
  const role = fields.get('evidence_role') ?? (grandfathered ? 'summary-only' : '');
  if (!grandfathered && !['summary-only', 'qualification'].includes(role)) {
    fail(`${location}: v2 event must declare evidence_role as summary-only or qualification`);
  }

  let refs = [];
  if (fields.has('evidence_refs')) {
    try {
      refs = JSON.parse(fields.get('evidence_refs'));
    } catch {
      fail(`${location}: evidence_refs must be a one-line JSON array`);
      return;
    }
    if (!Array.isArray(refs)) {
      fail(`${location}: evidence_refs must be a JSON array`);
      return;
    }
    const seen = new Set();
    for (let index = 0; index < refs.length; index += 1) {
      const ref = refs[index];
      validateEvidenceRef(ref, `${location}: evidence_refs[${index}]`);
      if (ref && typeof ref === 'object') {
        const key = `${ref.kind}\0${ref.locator}`;
        if (seen.has(key)) fail(`${location}: duplicate evidence ref ${ref.kind}:${ref.locator}`);
        seen.add(key);
      }
    }
  }

  const bundleDigest = fields.get('evidence_bundle_digest');
  if (role === 'qualification') {
    qualificationEvidenceEvents += 1;
    if (refs.length === 0) fail(`${location}: qualification evidence requires at least one evidence_refs entry`);
    if (!bundleDigest || !sha256Pattern.test(bundleDigest)) {
      fail(`${location}: qualification evidence requires evidence_bundle_digest using sha256:<64 lowercase hex>`);
    } else {
      const expected = `sha256:${sha256(JSON.stringify(canonicalizeEvidenceRefs(refs)))}`;
      if (bundleDigest !== expected) fail(`${location}: evidence_bundle_digest mismatch; expected ${expected}`);
    }
  } else {
    if (refs.length > 0 || bundleDigest) {
      fail(`${location}: summary-only evidence must not present evidence_refs or evidence_bundle_digest as qualification evidence`);
    }
  }
}

function inspectEvent({ id, lineNumber, headerLine, bodyLines, pathDate, displayPath, declaredCutoff, shardScope }) {
  eventCount += 1;
  const location = `${displayPath}:${lineNumber}`;
  addEventOccurrence(id, location);

  const idMatch = eventIdPattern.exec(id);
  if (!idMatch) {
    warn(`${location}: invalid event_id format \`${id}\`; expected EVT-YYYYMMDD-####`);
  } else {
    const idDate = `${idMatch[1]}-${idMatch[2]}-${idMatch[3]}`;
    if (!isValidDate(idDate)) warn(`${location}: event_id contains an invalid date \`${idDate}\``);
    if (idDate !== pathDate) warn(`${location}: event_id date \`${idDate}\` does not match daily-log path date \`${pathDate}\``);
  }

  const fields = new Map();
  const labelsByCanonical = new Map();
  for (const line of bodyLines) {
    const fieldMatch = /^\s*[-*]\s+\*\*([^*]+?)\*\*\s*[：:]\s*(.*)$/.exec(line);
    if (!fieldMatch) continue;
    const normalizedLabel = normalizeFieldLabel(fieldMatch[1]);
    const canonicalName = fieldAliases.get(normalizedLabel);
    if (!canonicalName) continue;
    const priorLabels = labelsByCanonical.get(canonicalName) ?? [];
    priorLabels.push(fieldMatch[1].trim());
    labelsByCanonical.set(canonicalName, priorLabels);
    if (fields.has(canonicalName)) {
      fail(`${location}: duplicate canonical field \`${canonicalName}\` via labels ${priorLabels.map((label) => `\`${label}\``).join(', ')}`);
      continue;
    }
    fields.set(canonicalName, fieldMatch[2].trim());
  }

  for (const field of requiredValueFields) {
    if (!fields.has(field)) warn(`${location}: missing required field \`${field}\``);
    else if (!fields.get(field)) warn(`${location}: required field \`${field}\` must not be empty`);
  }
  for (const field of requiredPresenceFields) {
    if (!fields.has(field)) warn(`${location}: missing explicit field \`${field}\` (an empty value is allowed)`);
  }
  if (shardScope && fields.get('scope') !== shardScope) {
    fail(`${location}: scope shard requires exact event scope \`${shardScope}\`, got \`${fields.get('scope') || '(missing)'}\``);
  }

  const legacy = isLegacyAllowed(displayPath, id, declaredCutoff);
  if (legacy) {
    legacyEventCount += 1;
    const legacyTime = fields.get('occurred_at');
    const parsedLegacyTime = legacyTime ? parseTimestamp(legacyTime, { legacy: true }) : null;
    if (legacyTime && !parsedLegacyTime) warn(`${location}: legacy time \`${legacyTime}\` is not parseable`);
    if (parsedLegacyTime && parsedLegacyTime.getTime() > Date.now() + futureToleranceMs) {
      fail(`${location}: occurred_at/time \`${legacyTime}\` is in the future beyond the 5 minute tolerance`);
    }
    const digest = `sha256:${sha256(canonicalLegacyCard(headerLine, bodyLines))}`;
    legacyRecordsByKey.set(`${displayPath}#${id}`, { id, displayPath, location, digest });
  } else {
    v2EventCount += 1;
    for (const field of v2RequiredValueFields) {
      if (!fields.has(field)) fail(`${location}: v2 event is missing required field \`${field}\``);
      else if (!fields.get(field)) fail(`${location}: v2 field \`${field}\` must not be empty`);
    }

    const occurredAt = fields.get('occurred_at');
    const recordedAt = fields.get('recorded_at');
    const occurredDate = occurredAt ? parseTimestamp(occurredAt) : null;
    const recordedDate = recordedAt ? parseTimestamp(recordedAt) : null;
    if (occurredAt && !occurredDate) fail(`${location}: occurred_at must be ISO 8601 with an explicit timezone`);
    if (recordedAt && !recordedDate) fail(`${location}: recorded_at must be ISO 8601 with an explicit timezone`);
    if (occurredAt && occurredAt.slice(0, 10) !== pathDate) {
      fail(`${location}: occurred_at calendar date \`${occurredAt.slice(0, 10)}\` does not match daily-log path date \`${pathDate}\``);
    }
    if (occurredDate && occurredDate.getTime() > Date.now() + futureToleranceMs) {
      fail(`${location}: occurred_at \`${occurredAt}\` is in the future beyond the 5 minute tolerance`);
    }
    if (recordedDate && recordedDate.getTime() > Date.now() + futureToleranceMs) {
      fail(`${location}: recorded_at \`${recordedAt}\` is in the future beyond the 5 minute tolerance`);
    }
    if (occurredDate && recordedDate && recordedDate.getTime() < occurredDate.getTime()) {
      fail(`${location}: recorded_at precedes occurred_at`);
    }

    validateEvidenceContract(id, displayPath, fields, labelsByCanonical, location);

    const eventDigest = fields.get('event_digest');
    const expectedEventDigest = `sha256:${sha256(canonicalEventPayload(id, fields))}`;
    if (eventDigest && !sha256Pattern.test(eventDigest)) {
      fail(`${location}: event_digest must use sha256:<64 lowercase hex>`);
    } else if (eventDigest && eventDigest !== expectedEventDigest) {
      fail(`${location}: event_digest mismatch; expected ${expectedEventDigest}`);
    }
  }

  eventRecords.push({ id, location, fields, legacy, sequence: eventRecords.length });
}

function inspectDailyLog(filePath, pathMatch) {
  dailyLogFiles += 1;
  const displayPath = relative(repoRoot, filePath).replaceAll('\\', '/');
  const [, pathYear, pathMonth, pathDate, shardLabel, subLibraryId, privateRuntimeId] = pathMatch;
  const shardScope = shardLabel === 'mother-library'
    ? 'mother-library'
    : subLibraryId
      ? `sub-library:${subLibraryId}`
      : privateRuntimeId
        ? `private-runtime:${privateRuntimeId}`
        : '';
  const lines = readFileSync(filePath, 'utf8').split(/\r?\n/);
  const frontmatter = parseFrontmatter(lines, displayPath);
  const declaredCutoff = frontmatter.get('legacy_event_cutoff') ?? '';
  const configuredCutoff = legacyCutoffs.get(displayPath) ?? '';

  if (!isValidDate(pathDate)) warn(`${displayPath}: daily-log filename contains an invalid date \`${pathDate}\``);
  if (pathDate.slice(0, 4) !== pathYear || pathDate.slice(5, 7) !== pathMonth) {
    warn(`${displayPath}: daily-log filename date \`${pathDate}\` does not match parent path \`${pathYear}/${pathMonth}\``);
  }
  if (configuredCutoff && declaredCutoff !== configuredCutoff) {
    fail(`${displayPath}: legacy_event_cutoff must equal the validator migration allowlist value \`${configuredCutoff}\``);
  }
  if (!configuredCutoff && declaredCutoff) {
    fail(`${displayPath}: legacy_event_cutoff is not permitted for this file`);
  }

  const eventHeaders = [];
  for (let index = 0; index < lines.length; index += 1) {
    const match = /^#{2,6}\s+(EVT-[^\s`]+)\b/.exec(lines[index]);
    if (match) eventHeaders.push({ id: match[1], index, headerLine: lines[index] });
  }

  const noEvents = frontmatter.get('no_events') === 'true';
  const noEventsReason = frontmatter.get('no_events_reason') ?? '';
  if (eventHeaders.length === 0) {
    if (!noEvents || !noEventsReason || /^(?:none|n\/a|todo|tbd)$/i.test(noEventsReason)) {
      fail(`${displayPath}: daily log has no events; set front matter no_events: true and a concrete no_events_reason`);
    } else {
      noEventLogFiles += 1;
    }
    return;
  }
  if (noEvents) fail(`${displayPath}: no_events: true conflicts with ${eventHeaders.length} event(s)`);
  if (noEventsReason) fail(`${displayPath}: no_events_reason is only allowed when no_events: true`);

  for (let index = 0; index < eventHeaders.length; index += 1) {
    const event = eventHeaders[index];
    const nextEvent = eventHeaders[index + 1];
    inspectEvent({
      id: event.id,
      lineNumber: event.index + 1,
      headerLine: event.headerLine,
      bodyLines: lines.slice(event.index + 1, nextEvent?.index ?? lines.length),
      pathDate,
      displayPath,
      declaredCutoff,
      shardScope,
    });
  }
}

function loadLegacyBaseline() {
  if (!existsSync(baselinePath) || !statSync(baselinePath).isFile()) {
    fail('legacy digest baseline is missing: scripts/log-legacy-digest-baseline.json');
    return;
  }
  const bytes = readFileSync(baselinePath);
  const fileDigest = sha256(bytes);
  if (fileDigest !== pinnedBaselineFileSha256) {
    fail(`legacy digest baseline file digest mismatch; expected sha256:${pinnedBaselineFileSha256}, got sha256:${fileDigest}`);
    return;
  }
  try {
    legacyBaseline = JSON.parse(bytes.toString('utf8'));
  } catch {
    fail('legacy digest baseline is not valid JSON');
    return;
  }
  if (legacyBaseline.schema_version !== 1 || !Array.isArray(legacyBaseline.entries)) {
    fail('legacy digest baseline must use schema_version 1 and contain entries[]');
    return;
  }
  const cutoffObject = Object.fromEntries(legacyCutoffs);
  if (JSON.stringify(legacyBaseline.cutoffs) !== JSON.stringify(cutoffObject)) {
    fail('legacy digest baseline cutoffs do not match validator allowlist');
  }
  const keys = new Set();
  for (const entry of legacyBaseline.entries) {
    if (!entry || typeof entry !== 'object'
      || !eventIdPattern.test(entry.event_id ?? '')
      || !legacyCutoffs.has(entry.path)
      || !sha256Pattern.test(entry.sha256 ?? '')) {
      fail('legacy digest baseline contains an invalid entry');
      continue;
    }
    const key = `${entry.path}#${entry.event_id}`;
    if (keys.has(key)) fail(`legacy digest baseline contains duplicate entry ${key}`);
    keys.add(key);
  }
  const canonicalEntries = [...legacyBaseline.entries]
    .map((entry) => ({ event_id: entry.event_id, path: entry.path, sha256: entry.sha256 }))
    .sort((left, right) => {
      const leftKey = `${left.path}\0${left.event_id}`;
      const rightKey = `${right.path}\0${right.event_id}`;
      return leftKey < rightKey ? -1 : leftKey > rightKey ? 1 : 0;
    });
  const expectedEntriesDigest = `sha256:${sha256(JSON.stringify(canonicalEntries))}`;
  if (legacyBaseline.entries_digest !== expectedEntriesDigest) {
    fail(`legacy digest baseline entries_digest mismatch; expected ${expectedEntriesDigest}`);
  }
}

function validateLegacyBaselineAgainstLogs() {
  if (!legacyBaseline?.entries) return;
  const expectedKeys = new Set();
  for (const entry of legacyBaseline.entries) {
    const key = `${entry.path}#${entry.event_id}`;
    expectedKeys.add(key);
    const record = legacyRecordsByKey.get(key);
    if (!record) {
      const message = `legacy baseline event is missing from logs: ${key}`;
      if (releaseMode) fail(message); else warn(message);
    } else if (record.digest !== entry.sha256) {
      const message = `${record.location}: frozen legacy event digest mismatch; baseline=${entry.sha256} actual=${record.digest}`;
      if (releaseMode) fail(message); else warn(message);
    }
  }
  for (const [key, record] of legacyRecordsByKey) {
    if (!expectedKeys.has(key)) {
      const message = `${record.location}: legacy event is not present in the independent digest baseline`;
      if (releaseMode) fail(message); else warn(message);
    }
  }
}

function buildCorrectionClosure(correctionEdges) {
  const correctedTargets = new Set(correctionEdges.values());
  const latestCorrectionByTarget = new Map();
  for (const [correction, target] of correctionEdges) latestCorrectionByTarget.set(target, correction);
  const superseded = [];
  for (const target of [...correctedTargets].sort()) {
    let effective = target;
    const seen = new Set();
    while (latestCorrectionByTarget.has(effective) && !seen.has(effective)) {
      seen.add(effective);
      effective = latestCorrectionByTarget.get(effective);
    }
    superseded.push({ event_id: target, effective_event_id: effective });
  }
  const effectiveIds = eventRecords
    .map((event) => event.id)
    .filter((id) => !correctedTargets.has(id))
    .sort();
  const effective = effectiveIds.map((eventId) => ({
    event_id: eventId,
    supersedes: superseded.filter((item) => item.effective_event_id === eventId).map((item) => item.event_id).sort(),
  }));
  return { schema_version: 1, effective, superseded };
}

loadLegacyBaseline();

if (unknownArgs.length > 0) {
  fail(`unsupported argument(s): ${unknownArgs.join(', ')}`);
} else if (!existsSync(logsRoot) || !statSync(logsRoot).isDirectory()) {
  fail(`logs root is missing or not a directory: ${relative(repoRoot, logsRoot)}`);
} else {
  for (const filePath of walk(logsRoot).sort()) {
    const displayPath = relative(logsRoot, filePath).replaceAll('\\', '/');
    if (!displayPath.toLowerCase().endsWith('.md')) continue;
    const parts = displayPath.split('/');
    const inMonthDirectory = parts.length >= 3 && /^\d{4}$/.test(parts[0]) && /^(?:0[1-9]|1[0-2])$/.test(parts[1]);
    if (!inMonthDirectory) continue;
    const [pathYear, pathMonth] = parts;
    const basename = parts.at(-1);
    if (parts.length === 3 && (basename === 'index.md' || basename === `${pathYear}-${pathMonth}-summary.md`)) continue;
    const pathMatch = dailyLogPathPattern.exec(displayPath);
    if (!pathMatch) {
      fail(`malformed daily log filename under YYYY/MM: ${displayPath}; expected YYYY-MM-DD.md or YYYY-MM-DD--{mother-library|sub-library-<id>|private-runtime-<id>}.md`);
      continue;
    }
    inspectDailyLog(filePath, pathMatch);
  }

  for (const [id, locations] of eventsById) {
    if (locations.length > 1) fail(`duplicate event_id \`${id}\`: ${locations.join('; ')}`);
  }

  const knownIds = new Set(eventRecords.map((event) => event.id));
  const firstRecordById = new Map();
  for (const event of eventRecords) {
    if (!firstRecordById.has(event.id)) firstRecordById.set(event.id, event);
  }

  const correctionEdges = new Map();
  for (const event of eventRecords.filter((record) => !record.legacy)) {
    const correctionOf = event.fields.get('correction_of');
    if (!correctionOf || correctionOf === 'none') continue;
    if (!eventIdPattern.test(correctionOf)) {
      fail(`${event.location}: correction_of must be \`none\` or EVT-YYYYMMDD-####`);
      continue;
    }
    if (correctionOf === event.id) {
      fail(`${event.location}: correction_of cannot reference the event itself`);
      continue;
    }
    if (!knownIds.has(correctionOf)) {
      fail(`${event.location}: correction_of references unknown event_id \`${correctionOf}\``);
      continue;
    }

    const target = firstRecordById.get(correctionOf);
    const existingCorrection = [...correctionEdges.entries()].find(([, targetId]) => targetId === correctionOf);
    if (existingCorrection) {
      fail(`${event.location}: correction target \`${correctionOf}\` already has direct correction \`${existingCorrection[0]}\`; append to the correction chain instead`);
    }
    correctionEdges.set(event.id, correctionOf);
    if (target && target.sequence >= event.sequence) {
      fail(`${event.location}: correction_of must reference an earlier event; \`${correctionOf}\` appears at or after the correction`);
    }

    const correctionOccurred = parseTimestamp(event.fields.get('occurred_at') ?? '');
    const targetOccurred = parseTimestamp(target?.fields.get('occurred_at') ?? '', { legacy: Boolean(target?.legacy) });
    if (correctionOccurred && targetOccurred && correctionOccurred.getTime() < targetOccurred.getTime()) {
      fail(`${event.location}: correction occurred_at precedes target event \`${correctionOf}\``);
    }
    const correctionRecorded = parseTimestamp(event.fields.get('recorded_at') ?? '');
    const targetRecorded = parseTimestamp(target?.fields.get('recorded_at') ?? '', { legacy: Boolean(target?.legacy) }) ?? targetOccurred;
    if (correctionRecorded && targetRecorded && correctionRecorded.getTime() < targetRecorded.getTime()) {
      fail(`${event.location}: correction recorded_at precedes target event \`${correctionOf}\``);
    }
  }

  const visitState = new Map();
  const stack = [];
  function visitCorrection(id) {
    const state = visitState.get(id) ?? 0;
    if (state === 2) return;
    if (state === 1) {
      const cycleStart = stack.indexOf(id);
      const cycle = [...stack.slice(cycleStart), id];
      fail(`correction_of cycle detected: ${cycle.join(' -> ')}`);
      return;
    }
    visitState.set(id, 1);
    stack.push(id);
    const target = correctionEdges.get(id);
    if (target) visitCorrection(target);
    stack.pop();
    visitState.set(id, 2);
  }
  for (const id of correctionEdges.keys()) visitCorrection(id);
  correctionClosure = buildCorrectionClosure(correctionEdges);
  validateLegacyBaselineAgainstLogs();
}

const blockingFailures = failures.length + (releaseMode ? warnings.length : 0);
const summary = `daily_logs=${dailyLogFiles} no_event_logs=${noEventLogFiles} events=${eventCount} legacy_events=${legacyEventCount} v2_events=${v2EventCount} qualification_evidence_events=${qualificationEvidenceEvents} effective_events=${correctionClosure.effective.length} superseded_events=${correctionClosure.superseded.length} warnings=${warnings.length} failures=${blockingFailures} release=${releaseMode}`;

if (closureJsonMode) console.log(`CORRECTION_CLOSURE_JSON:${JSON.stringify(correctionClosure)}`);
console.log('VALIDATION_SCOPE: structure-and-integrity-only; factual_claims=not_verified; human_identity=not_verified');

if (blockingFailures > 0) {
  console.log('LOG_VALIDATION_FAILURES');
  for (const message of failures) console.log(`- ${message}`);
  for (const message of warnings) console.log(`- ${message}`);
  console.log(`SUMMARY: ${summary}`);
  process.exitCode = 1;
} else if (warnings.length > 0) {
  console.log('LOG_VALIDATION_WARNINGS');
  for (const message of warnings) console.log(`- ${message}`);
  console.log(`SUMMARY: ${summary}`);
} else {
  console.log('LOG_VALIDATION_PASS');
  console.log('LOG_FACTUAL_VERDICT: not_verified');
  console.log(`SUMMARY: ${summary}`);
}
