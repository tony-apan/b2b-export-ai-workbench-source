import test from 'node:test';
import assert from 'node:assert/strict';
import { copyFileSync, mkdirSync, mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { tmpdir } from 'node:os';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { articlePackageValidatorTestHooks, validateArticlePackage } from './validate-article-package.mjs';
import { parseMarkdownFrontMatter } from './front-matter.mjs';
import { extractPublishableArticleMarkdown, publishableArticleMarkdownToAllinCmsSlate } from '../ADAPTERS/cms/allincms/article-content-formats.mjs';

const libraryRoot = new URL('../', import.meta.url);
const exampleRoot = new URL('../EXAMPLES/fluxpedal-motors/', import.meta.url);
const fixtureNames = {
  briefPath: 'b2b-seo-article-brief.md',
  draftPath: 'b2b-seo-article-draft.md',
  reviewPath: 'b2b-seo-article-review.md',
  publishPath: 'b2b-seo-publish-record.md',
};
const templateNames = {
  briefPath: 'article-brief.md',
  draftPath: 'article-draft.md',
  reviewPath: 'article-quality-review.md',
  publishPath: 'publish-record.md',
};

function decodeSequenceItem(raw) {
  const value = raw.trim();
  if (value.startsWith('"')) return JSON.parse(value);
  if (value.startsWith("'") && value.endsWith("'")) return value.slice(1, -1).replace(/''/g, "'");
  return value;
}

function normalizeFrontMatterSequences(content) {
  const lines = content.replace(/\r\n?/g, '\n').split('\n');
  const closing = lines.indexOf('---', 1);
  assert.notEqual(closing, -1, 'canonical fixture must have closing front matter delimiter');
  const output = [lines[0]];
  const anchors = new Map();
  for (let index = 1; index < closing; index += 1) {
    const line = lines[index];
    const alias = line.match(/^([A-Za-z_][A-Za-z0-9_-]*):\s*\*([A-Za-z_][A-Za-z0-9_-]*)\s*$/);
    if (alias) {
      assert.equal(anchors.has(alias[2]), true, `fixture alias ${alias[2]} must resolve`);
      output.push(`${alias[1]}: ${JSON.stringify(anchors.get(alias[2]))}`);
      continue;
    }
    const sequence = line.match(/^([A-Za-z_][A-Za-z0-9_-]*):(?:\s*&([A-Za-z_][A-Za-z0-9_-]*))?\s*$/);
    if (!sequence || !/^  -\s+/.test(lines[index + 1] || '')) {
      output.push(line);
      continue;
    }
    const items = [];
    while (index + 1 < closing && /^  -\s+/.test(lines[index + 1])) {
      index += 1;
      items.push(decodeSequenceItem(lines[index].replace(/^  -\s+/, '')));
    }
    if (sequence[2]) anchors.set(sequence[2], items);
    output.push(`${sequence[1]}: ${JSON.stringify(items)}`);
  }
  output.push(...lines.slice(closing));
  return output.join('\n');
}

function fieldPattern(field) {
  return new RegExp(`^${field}:.*$`, 'm');
}

function replaceField(content, field, value) {
  assert.match(content, fieldPattern(field), `canonical fixture must contain ${field}`);
  return content.replace(fieldPattern(field), `${field}: ${value}`);
}

function replaceRequiredLiteral(content, search, replacement, label = String(search)) {
  assert.notEqual(search, replacement, `${label} mutation must not be a no-op`);
  const matches = typeof search === 'string'
    ? content.split(search).length - 1
    : [...content.matchAll(new RegExp(search.source, search.flags.includes('g') ? search.flags : `${search.flags}g`))].length;
  assert.ok(matches > 0, `required mutation must match ${label}`);
  const output = content.replace(search, replacement);
  assert.notEqual(output, content, `required mutation must change ${label}`);
  return output;
}

function mutateJsonArrayField(content, field, mutate) {
  const match = fieldPattern(field).exec(content);
  assert.ok(match, `canonical fixture must contain ${field}`);
  const value = JSON.parse(match[0].slice(match[0].indexOf(':') + 1).trim());
  assert.equal(Array.isArray(value), true, `${field} must be a JSON array in normalized fixtures`);
  const mutated = mutate([...value]);
  assert.equal(Array.isArray(mutated), true, `${field} mutation must return an array`);
  assert.notDeepEqual(mutated, value, `${field} mutation must change at least one row`);
  return replaceField(content, field, JSON.stringify(mutated));
}

function removeField(content, field) {
  const pattern = new RegExp(`^${field}:.*\n?`, 'm');
  assert.match(content, pattern, `canonical fixture must contain ${field}`);
  return content.replace(pattern, '');
}

function insertFields(content, fields) {
  const closing = content.indexOf('\n---\n', 4);
  assert.notEqual(closing, -1);
  const lines = Object.entries(fields).map(([field, value]) => `${field}: ${value}`).join('\n');
  return `${content.slice(0, closing)}\n${lines}${content.slice(closing)}`;
}

function transformDocumentBody(content, transform) {
  const closing = content.indexOf('\n---\n', 4);
  assert.notEqual(closing, -1);
  const bodyStart = closing + 5;
  return `${content.slice(0, bodyStart)}${transform(content.slice(bodyStart))}`;
}

function transformBody(content, transform) {
  const closing = content.indexOf('\n---\n', 4);
  assert.notEqual(closing, -1);
  const bodyStart = content.indexOf('<!-- PUBLISHABLE_BODY_START -->', closing + 5);
  const bodyEnd = content.indexOf('<!-- PUBLISHABLE_BODY_END -->', bodyStart + 1);
  assert.notEqual(bodyStart, -1, 'canonical Draft fixture must contain PUBLISHABLE_BODY_START');
  assert.notEqual(bodyEnd, -1, 'canonical Draft fixture must contain PUBLISHABLE_BODY_END');
  const contentStart = bodyStart + '<!-- PUBLISHABLE_BODY_START -->'.length;
  return `${content.slice(0, contentStart)}${transform(content.slice(contentStart, bodyEnd))}${content.slice(bodyEnd)}`;
}

function transformMarkdownSection(content, heading, nextHeading, transform) {
  const start = content.indexOf(heading);
  assert.notEqual(start, -1, `fixture must contain section heading ${heading}`);
  const end = content.indexOf(nextHeading, start + heading.length);
  assert.notEqual(end, -1, `fixture must contain following section heading ${nextHeading}`);
  return `${content.slice(0, start)}${transform(content.slice(start, end))}${content.slice(end)}`;
}

function topLevelFrontMatterFields(content) {
  const closing = content.indexOf('\n---\n', 4);
  assert.notEqual(closing, -1);
  return new Set([...content.slice(4, closing).matchAll(/^([A-Za-z_][A-Za-z0-9_-]*):/gm)].map((match) => match[1]));
}

function flatFrontMatter(content) {
  const normalized = normalizeFrontMatterSequences(content);
  const closing = normalized.indexOf('\n---\n', 4);
  assert.notEqual(closing, -1);
  const fields = new Map();
  for (const line of normalized.slice(4, closing).split('\n')) {
    const match = /^([A-Za-z_][A-Za-z0-9_-]*):(.*)$/.exec(line);
    if (match) fields.set(match[1], match[2]);
  }
  return { fields, body: normalized.slice(closing + 5) };
}

let projectedCtaMeasurementFields;

function canonicalProjectedCtaMeasurementFields() {
  if (projectedCtaMeasurementFields) return projectedCtaMeasurementFields;
  const canonical = flatFrontMatter(normalizeFrontMatterSequences(readFileSync(new URL(fixtureNames.briefPath, exampleRoot), 'utf8'))).fields;
  projectedCtaMeasurementFields = new Map();
  for (const field of ['cta_measurement_map', 'conversion_measurement_plan_status', 'measurement_window', 'cta_abandonment_measurement_status', 'cta_measurement_plan_verdict']) {
    assert.equal(canonical.has(field), true, `canonical fixture must contain ${field}`);
    projectedCtaMeasurementFields.set(field, canonical.get(field).trim());
  }
  projectedCtaMeasurementFields.set('cta_abandonment_measurement_refs', JSON.stringify(['cta-measurement-evidence.md#cta-measurement-plan']));
  return projectedCtaMeasurementFields;
}

function projectToCurrentTemplate(content, templateName) {
  const template = flatFrontMatter(readFileSync(new URL(`../TEMPLATES/${templateName}`, import.meta.url), 'utf8'));
  const source = flatFrontMatter(content);
  const explanationFields = new Set(['template_usage', 'when_to_read', 'keywords']);
  const frontMatter = [...template.fields].filter(([field]) => !explanationFields.has(field)).map(([field, templateValue]) => {
    const value = source.fields.has(field) ? source.fields.get(field) : templateValue;
    return `${field}:${value}`;
  }).join('\n');
  let output = `---\n${frontMatter}\n---\n${source.body}`;
  for (const [field, value] of canonicalProjectedCtaMeasurementFields()) output = setField(output, field, value);
  return output;
}

function makeFixture(t, mutations = {}, setup = null) {
  const dir = mkdtempSync(join(tmpdir(), 'canonical-article-package-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  const paths = {};
  for (const [key, name] of Object.entries(fixtureNames)) {
    let content = normalizeFrontMatterSequences(readFileSync(new URL(name, exampleRoot), 'utf8'));
    if (mutations[key]) content = mutations[key](content);
    const target = join(dir, name);
    writeFileSync(target, content);
    paths[key] = target;
  }
  for (const name of ['customer-voice.md', 'products.md', 'icp.md', 'search-evidence.md']) {
    writeFileSync(join(dir, name), readFileSync(new URL(name, exampleRoot), 'utf8'));
  }
  const briefFields = flatFrontMatter(readFileSync(paths.briefPath, 'utf8')).fields;
  const rawCtaMeasurementMap = briefFields.get('cta_measurement_map');
  let ctaMeasurementRows = [];
  try {
    const parsed = rawCtaMeasurementMap ? JSON.parse(rawCtaMeasurementMap.trim()) : [];
    if (Array.isArray(parsed)) ctaMeasurementRows = parsed;
  } catch {
    // Keep malformed or missing-field negative fixtures constructible so the validator, not the fixture builder, owns the BLOCK.
  }
  const ctaMeasurementRowDigests = ctaMeasurementRows.map((row) => `sha256:${createHash('sha256').update(String(row).trim()).digest('hex')}`);
  const ctaMeasurementBody = `# CTA measurement plan

This independently reviewable measurement-plan binds the primary, soft, and fallback surfaces to distinct start, submit, success, failure, abandonment, qualification, and commercial-acceptance events over a declared observation window. It records a planned measurement contract only; it does not claim observed rankings, inquiries, conversions, revenue, or production performance.

${ctaMeasurementRowDigests.map((digest) => `measurement_row_sha256: ${digest}`).join('\n')}
`;
  const ctaMeasurementDigest = createHash('sha256').update(ctaMeasurementBody).digest('hex');
  writeFileSync(join(dir, 'cta-measurement-evidence.md'), `---
title: CTA measurement plan evidence
record_type: evidence-record
evidence_scope: production
source: independent CTA measurement-contract review
observed_at: 2026-08-02T00:00:00Z
digest: sha256:${ctaMeasurementDigest}
evidence_kind: measurement-plan
---
${ctaMeasurementBody}`);
  if (setup) setup(dir, paths);
  return paths;
}

function expectPass(paths) {
  const result = validateArticlePackage(paths);
  assert.equal(result.ok, true, result.problems.join('\n'));
  return result;
}

function expectBlock(t, mutations, { match = null, assertProblems = null, setup = null } = {}) {
  const hasMatcher = match instanceof RegExp;
  const hasAssertion = typeof assertProblems === 'function';
  assert.equal(hasMatcher || hasAssertion, true, 'blocked fixture requires a branch-specific problem oracle');
  const result = validateArticlePackage(makeFixture(t, mutations, setup));
  assert.equal(result.ok, false, 'adversarial canonical package unexpectedly passed');
  assert.ok(result.problems.length > 0);
  if (hasMatcher) assert.match(result.problems.join('\n'), match);
  if (hasAssertion) assertProblems(result.problems);
  return result;
}

function allRecords(field, value) {
  return Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => replaceField(content, field, value)]));
}

function overrideMutationFields(mutations, values, keys = Object.keys(fixtureNames)) {
  const output = { ...mutations };
  for (const key of keys) {
    const base = output[key] || ((content) => content);
    output[key] = (content) => {
      let result = base(content);
      for (const [field, value] of Object.entries(values)) result = replaceIfPresent(result, field, JSON.stringify(value));
      return result;
    };
  }
  return output;
}

function expectBlockMatching(t, mutations, pattern, setup = null) {
  return expectBlock(t, mutations, { match: pattern, setup });
}

function expectBlockSatisfying(t, mutations, assertProblems, setup = null) {
  return expectBlock(t, mutations, { assertProblems, setup });
}


test('V14 required literal mutation fails closed on zero matches', () => {
  assert.throws(() => replaceRequiredLiteral('alpha beta', 'missing literal', 'replacement', 'zero-match probe'), /required mutation must match zero-match probe/);
});

test('V14 JSON-array mutation fails closed when no row changes', () => {
  assert.throws(() => mutateJsonArrayField('items: ["alpha"]\n', 'items', (rows) => rows), /items mutation must change at least one row/);
});

test('oracle audit rejects any-failure-only block assertions before fixture construction', () => {
  assert.throws(() => expectBlock(null, {}), /blocked fixture requires a branch-specific problem oracle/);
});

const legalFirstRoundInputs = [
  'loaded vehicle mass and payload range',
  'target wheel diameter and tire envelope',
  'route grade and repeated-duty profile',
  'battery voltage plus explicitly typed battery-current and phase-current limits',
  'axle, dropout, and brake interface summary',
];
const legalSecondRoundInputs = [
  'target speed, controller speed limit, and controller strategy',
  'detailed duty-cycle, ambient, repetition, and thermal test method',
  'exact axle and dropout drawing plus connector, sensor, cable, and controller-interface details',
  'target market and vehicle category',
  'sample timeline and acceptance criteria',
];
const syntheticFictionalDisclosure = 'Illustrative example: FluxPedal Motors and all named owners are fictional; nothing here proves product or service capability.';

function secondaryIntentContracts(supportingQueries, stage, commercialCommitment, buyerTaskPrefix) {
  return supportingQueries.map((query) => `${query}|${buyerTaskPrefix} for ${query}|${stage}|${commercialCommitment}|this-article|supports`);
}

function terminalActionContractFromDominant(dominantTask) {
  const [action, decisionObject, expectedOutput, stage, commercialCommitment] = dominantTask.split('|');
  assert.equal([action, decisionObject, expectedOutput, stage, commercialCommitment].every(Boolean), true, 'dominant task must have five non-empty parts');
  return [action, decisionObject, expectedOutput, stage, commercialCommitment].join('|');
}
const legalInternalLinkContracts = [
  'solution|https://example.test/solutions/cargo-hub-motor-candidates|review the cargo hub-motor solution family and unresolved inputs|review the solution family boundary and unresolved inputs|Engineer|candidate-or-stop section|reserved-synthetic-target|Synthetic Product Content owner|search-evidence.md#reserved-targets-and-acceptance-contracts',
  'technical-review|https://example.test/guides/cargo-ebike-sample-validation|define the next sample-validation evidence|validate cargo hub-motor candidate readiness with sample evidence|Quality|next-validation section|reserved-synthetic-target|Synthetic Quality review owner|search-evidence.md#reserved-targets-and-acceptance-contracts',
];
const canonicalRouteAndPolicyFallback = `No production-verified technical-review route is available. Keep the completed local readiness worksheet on your device; do not send, submit, upload, share, attach, paste, copy it into another system, transmit it, or hand off control. Through your organization’s approved supplier-contact process, ask Avery Chen, Applications Engineering Lead, only for the production-verified technical-review route, its buyer-visible data boundary, and the responsible responder. Do not attach or paste the worksheet to that request. When the route, boundary, and responder are confirmed, use the single worksheet prepared above. The first-round return is packet completeness, a missing-evidence list, and the next review step. Candidate-or-stop still requires the complete second-round package and named technical-owner review. This is not an RFQ.`;
const canonicalBriefRouteAndPolicyFallback = canonicalRouteAndPolicyFallback;

function canonicalRouteAndPolicyFallbackFor(key) {
  return key === 'briefPath' ? canonicalBriefRouteAndPolicyFallback : canonicalRouteAndPolicyFallback;
}
const legalFallback = `No verified primary or fallback route is available. Keep the single local readiness worksheet prepared above on your device; do not send, submit, upload, share, attach, paste, copy it into another system, transmit it, or hand off control. Through your organization's approved supplier-contact process, request only a verified technical-review route, its buyer-visible data boundary, and the responsible responder from Applications Engineering. Do not attach or paste the worksheet to that request. After the route, boundary, and responder are confirmed, use the single worksheet prepared above. Requested review output: packet completeness, a missing-evidence list, and the next review step. Candidate-or-stop requires the complete second-round package and named technical-owner review; this is not an RFQ.`;

function replaceIfPresent(content, field, value) {
  return fieldPattern(field).test(content) ? replaceField(content, field, value) : content;
}

function setField(content, field, value) {
  return fieldPattern(field).test(content) ? replaceField(content, field, value) : insertFields(content, { [field]: value });
}

function setProjectedFields(baseMutations, values, keys = Object.keys(fixtureNames)) {
  const output = { ...baseMutations };
  for (const key of keys) {
    const base = output[key] || ((content) => content);
    output[key] = (content) => {
      let result = base(content);
      for (const [field, value] of Object.entries(values)) result = setField(result, field, JSON.stringify(value));
      return result;
    };
  }
  return output;
}

function mutateProjectedArray(baseMutations, field, mutate, keys = Object.keys(fixtureNames)) {
  const output = { ...baseMutations };
  for (const key of keys) {
    const base = output[key] || ((content) => content);
    output[key] = (content) => mutateJsonArrayField(base(content), field, mutate);
  }
  return output;
}

function bindProjectedCtaMapsToInventory(content, { pageVersion, stagePrefix, surfaces, technicalQualification = false, commercialAcceptance = false }) {
  const fields = flatFrontMatter(content).fields;
  const rawInventory = fields.get('buyer_visible_cta_inventory');
  assert.ok(rawInventory, 'buyer_visible_cta_inventory must exist before binding conversion and measurement maps');
  const inventoryRows = JSON.parse(rawInventory.trim());
  const inventoryById = new Map(inventoryRows.map((row) => {
    const parts = String(row).split('|').map((part) => part.trim());
    assert.equal(parts.length, 10, `buyer_visible_cta_inventory row must expose ten slots: ${row}`);
    return [parts[0], { locator: parts[2], owner: parts[5], interaction: parts[6] }];
  }));
  const conversionRows = surfaces.map(({ id, role, outcome, routeId }) => {
    const inventory = inventoryById.get(id);
    assert.ok(inventory, `buyer_visible_cta_inventory must contain mapped surface ${id}`);
    return `${id}|${role}|${outcome}|${inventory.locator}|${inventory.interaction}|${routeId}`;
  });
  const measurementRows = surfaces.map(({ id, role }) => {
    const inventory = inventoryById.get(id);
    const eventStem = `cta_${stagePrefix}_${role}`;
    const qualificationEvent = technicalQualification && role === 'primary' ? `${eventStem}_technical_qualified` : 'not-applicable';
    const commercialEvent = commercialAcceptance && role === 'primary' ? `${eventStem}_sales_accepted` : 'not-applicable';
    return [
      id,
      role,
      pageVersion,
      `${stagePrefix}-${role}-surface-v1`,
      `${eventStem}_start`,
      `${eventStem}_submit`,
      `${eventStem}_success`,
      `${eventStem}_failure`,
      `${role} start without completion success or failure within 30 minutes`,
      qualificationEvent,
      commercialEvent,
      'production-analytics-spec',
      'prior-30-days-baseline',
      '30-days-after-production-enable',
      inventory.owner,
      'cta-measurement-evidence.md#cta-measurement-plan',
    ].join('|');
  });
  let output = setField(content, 'conversion_surface_map', JSON.stringify(conversionRows));
  output = setField(output, 'cta_measurement_map', JSON.stringify(measurementRows));
  return output;
}

function legalSyntheticMutations(extra = {}) {
  const common = {
    first_round_inquiry_inputs: JSON.stringify(legalFirstRoundInputs),
    second_round_inquiry_inputs: JSON.stringify(legalSecondRoundInputs),
    stage_primary_outcome: '"packet completeness, a missing-evidence list, and the next review step"',
    stage_cta_mode: '"bounded-engineering-review"',
    stage_required_link_roles: '["technical-review"]',
    stage_sales_qualification_requirement: '"not-applicable-without-commercial-intent"',
    internal_link_targets: JSON.stringify(legalInternalLinkContracts.map((row) => row.split('|').slice(0, 3).join('|'))),
    internal_link_targets_snapshot: JSON.stringify(legalInternalLinkContracts.map((row) => row.split('|').slice(0, 3).join('|'))),
    internal_link_buyer_task_contracts: JSON.stringify(legalInternalLinkContracts),
    internal_link_buyer_task_contracts_snapshot: JSON.stringify(legalInternalLinkContracts),
    inventory_snapshot_ref: '"positive-evidence.md#synthetic-inventory-zero-result"',
    inventory_zero_result_evidence_refs: '["positive-evidence.md#synthetic-inventory-zero-result"]',
    cta_fallback_message_template: JSON.stringify(legalFallback),
  };
  const mutations = {};
  for (const key of Object.keys(fixtureNames)) {
    mutations[key] = (content) => {
      let output = projectToCurrentTemplate(content, templateNames[key]);
      for (const [field, value] of Object.entries(common)) output = replaceIfPresent(output, field, value);
      output = replaceIfPresent(output, 'required_inquiry_inputs', JSON.stringify([...legalFirstRoundInputs, ...legalSecondRoundInputs]));
      output = replaceIfPresent(output, 'cta_required_inputs', JSON.stringify(legalFirstRoundInputs));
      output = replaceIfPresent(output, 'cta_progressive_profiling_omitted_inputs', JSON.stringify(legalSecondRoundInputs));
      output = replaceIfPresent(output, 'cta_trigger', '"all five first-round engineering inputs are available for a bounded readiness review"');
      output = replaceIfPresent(output, 'cta_expected_output', '"packet completeness, missing-evidence list, and next review step"');
      output = replaceIfPresent(output, 'cta_validation_boundary', '"the output does not prove product performance, compliance, availability, pricing, production capability, or sales acceptance"');
      output = replaceIfPresent(output, 'cta_destination', '"not-applicable"');
      output = mutateJsonArrayField(output, 'buyer_visible_cta_inventory', (rows) => rows.map((row) => {
        if (!row.startsWith('fallback-copyable-message-01|')) return row;
        const parts = row.split('|');
        parts[3] = legalFallback;
        return parts.join('|');
      }));
      if (key === 'draftPath') output = transformBody(output, (body) => replaceRequiredLiteral(body, canonicalRouteAndPolicyFallback, legalFallback, 'canonical copyable fallback packet'));
      if (key === 'briefPath' || key === 'publishPath') output = transformDocumentBody(output, (body) => replaceRequiredLiteral(body, canonicalRouteAndPolicyFallbackFor(key), legalFallback, 'canonical control-record fallback message'));
      if (extra[key]) output = extra[key](output);
      return output;
    };
  }
  return mutations;
}

const legalSyntheticPrimaryEndpoint = 'https://example.test/contact/engineering-readiness-review';

function syntheticPrimaryEndpointMutations({ anchor = 'Request a bounded cargo hub-motor engineering-readiness review', plainText = false } = {}) {
  return legalSyntheticMutations(Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => {
    let output = replaceIfPresent(content, 'cta_destination', JSON.stringify(legalSyntheticPrimaryEndpoint));
    if (key === 'draftPath') {
      const visible = plainText
        ? `${anchor} at ${legalSyntheticPrimaryEndpoint}`
        : `[${anchor}](${legalSyntheticPrimaryEndpoint}).`;
      output = transformBody(output, (body) => replaceRequiredLiteral(body, canonicalCtaInstruction('primary-bounded-review-01'), visible, 'synthetic primary endpoint test insertion'));
    }
    return output;
  }])));
}

function setupLegalSyntheticEvidence(dir) {
  writeFileSync(join(dir, 'positive-evidence.md'), `---
title: Positive fixture evidence
record_type: fixture-evidence
evidence_scope: synthetic-fixture
---
# Positive fixture evidence

## Synthetic inventory zero result

checked_at: '2026-08-01T00:00:00Z'
scope: 'United States; English; cargo hub motor engineering readiness checklist query dimensions'
retrieval_dimensions: 'owner URL and slug, title, primary query, buyer task, stage and commercial commitment, category tag taxonomy, market, language'
candidate_count: 0
snapshot_ref: 'synthetic-inventory-snapshot.json'
snapshot_digest: 'sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
conflict_candidates: []
observed_result: 'No matching owner page was found in the bounded synthetic inventory snapshot.'

This independent synthetic inventory zero-result evidence covers matching owner pages only; it does not claim a live-site result.
`);
}

function setupProductionInformationGainEvidence(dir, { omit = '', checkedAt = '2026-08-01T00:00:00Z' } = {}) {
  const marketRows = [
    ['date', `checked_at: ${checkedAt}`],
    ['market', 'market: United States'],
    ['language', 'language: en'],
    ['query set', 'query_set: cargo hub motor engineering readiness checklist'],
    ['snapshot/corpus', 'snapshot: immutable dated search corpus'],
    ['difference', 'difference: compared with current owner pages and competing result formats'],
    ['reviewer', 'reviewer: Independent Market Evidence Reviewer'],
  ].filter(([label]) => label !== omit).map(([, row]) => row).join('\n');
  writeFileSync(join(dir, 'production-information-gain.md'), `---
title: Production information gain evidence
record_type: evidence-record
evidence_scope: production
source: independent market corpus review
observed_at: ${checkedAt}
digest: sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
evidence_kind: information-gain
---
# Production information gain

## Artifact

Decision artifact: a candidate-or-stop worksheet that changes the next validation route.

## Market

${marketRows}
`);
}

test('V9 legal synthetic package with distinct wording passes the closed Template schema', (t) => {
  const result = expectPass(makeFixture(t, legalSyntheticMutations(), setupLegalSyntheticEvidence));
  assert.equal(result.releaseDecision, 'blocked');
  assert.equal(result.evidenceScope, 'synthetic-fixture');
});

test('canonical FluxPedal command exits zero with ARTICLE_PACKAGE_STRUCTURE_PASS', () => {
  const command = spawnSync(process.execPath, [
    'scripts/validate-article-package.mjs',
    '--brief', 'EXAMPLES/fluxpedal-motors/b2b-seo-article-brief.md',
    '--draft', 'EXAMPLES/fluxpedal-motors/b2b-seo-article-draft.md',
    '--review', 'EXAMPLES/fluxpedal-motors/b2b-seo-article-review.md',
    '--publish', 'EXAMPLES/fluxpedal-motors/b2b-seo-publish-record.md',
  ], { cwd: new URL('.', libraryRoot), encoding: 'utf8' });
  assert.equal(command.status, 0, command.stderr);
  assert.match(command.stdout, /ARTICLE_PACKAGE_STRUCTURE_PASS/);
});

test('canonical FluxPedal baseline passes without fixture field injection', () => {
  const paths = Object.fromEntries(Object.entries(fixtureNames).map(([key, name]) => [key, fileURLToPath(new URL(name, exampleRoot))]));
  const result = expectPass(paths);
  assert.equal(result.releaseDecision, 'blocked');
  assert.equal(result.evidenceScope, 'synthetic-fixture');
});

test('FluxPedal projected to current template fields still passes without hidden requirements', (t) => {
  const mutations = Object.fromEntries(Object.keys(fixtureNames).map((key) => [
    key,
    (content) => projectToCurrentTemplate(content, templateNames[key]),
  ]));
  const result = expectPass(makeFixture(t, mutations));
  assert.equal(result.releaseDecision, 'blocked');
  assert.equal(result.evidenceScope, 'synthetic-fixture');
});

for (const [recordKey, field] of [
  ['briefPath', 'stage'], ['draftPath', 'dominant_task_contract'], ['reviewPath', 'market_information_gain_status'],
  ['publishPath', 'inventory_zero_result_evidence_refs'], ['publishPath', 'role_handoff_contracts'],
]) {
  test(`template-required canonical field ${field} cannot be omitted from ${recordKey}`, (t) => {
    expectBlockMatching(t, { [recordKey]: (content) => removeField(content, field) }, new RegExp(`field ${field} is required`));
  });
}

for (const [recordKey, field, value] of [
  ['briefPath', 'supporting_query_variants', '"not-an-array"'],
  ['publishPath', 'production_evidence_score', '[]'],
  ['reviewPath', 'structure_score', '[]'],
  ['publishPath', 'cms_mutation_status', '[]'],
]) {
  test(`template canonical type is enforced for ${recordKey}.${field}`, (t) => {
    expectBlockMatching(t, { [recordKey]: (content) => replaceField(content, field, value) }, new RegExp(`field ${field} must be`));
  });
}

const deprecatedAttacks = [
  ['qualified_inquiry_definition', '"legacy hidden requirement"'],
  ['minimum_completeness_threshold', '"legacy hidden requirement"'],
  ['qualified_inquiry_contract_status', '"confirmed"'],
  ['project_stage', '"Validate"'],
  ['technical_review_owner', '"Legacy owner"'],
  ['sales_owner', '"Legacy sales owner"'],
  ['commercial_intent_signals', '["RFQ"]'],
  ['commercial_next_step', '"Legacy next step"'],
  ['sales_acceptance_reason_codes', '["accepted|legacy|route"]'],
  ['internal_link_reference_parity_status', '"pass"'],
  ['internal_link_reachability_status', '"pass"'],
  ['internal_link_task_acceptance_status', '"pass"'],
  ['cta_capability_proof_status', '"pass"'],
  ['cta_capability_proof_refs', '["search-evidence.md#x"]'],
  ['cta_destination_reference_parity_status', '"pass"'],
  ['cta_destination_reachability_status', '"pass"'],
  ['cta_destination_reachability_refs', '["search-evidence.md#x"]'],
  ['fabricated_claims', 'false'],
  ['unsupported_performance_claims', 'false'],
  ['reviewer', '"legacy reviewer"'],
];
for (const [field, value] of deprecatedAttacks) {
  test(`deprecated hidden field ${field} is rejected instead of becoming schema`, (t) => {
    expectBlockMatching(t, { briefPath: (content) => insertFields(content, { [field]: value }) }, new RegExp(`field ${field} is a normalized deprecated alias`));
  });
}

for (const [field, value] of [
  ['stage', '"Buy"'],
  ['dominant_task_contract', '"buy|cargo motor|purchase order|Buy|sales-accepted"'],
  ['market_information_gain_status', '"confirmed"'],
  ['information_gain_artifact_status', '"missing"'],
  ['role_handoff_contracts', '[]'],
  ['inventory_zero_result_evidence_refs', '[]'],
]) {
  test(`canonical cross-record field ${field} cannot drift`, (t) => {
    expectBlockMatching(t, { draftPath: (content) => replaceField(content, field, value) }, new RegExp(`${field} must (?:exactly )?match (?:the canonical )?Brief(?: projection across all records using [\w-]+)?`));
  });
}

test('reviewed_at rejects impossible calendar dates', (t) => {
  expectBlockMatching(t, { reviewPath: (content) => replaceField(content, 'reviewed_at', '"2026-02-30T00:00:00Z"') }, /field reviewed_at must be an ISO date or timestamp/);
});

test('reviewed_at rejects future timestamps', (t) => {
  expectBlockMatching(t, { reviewPath: (content) => replaceField(content, 'reviewed_at', '"2999-01-01T00:00:00Z"') }, /field reviewed_at must not be in the future/);
});

test('reviewer_identity rejects template placeholders', (t) => {
  expectBlockMatching(t, { reviewPath: (content) => replaceField(content, 'reviewer_identity', '"replace-with-independent-reviewer"') }, /field reviewer_identity must replace the template placeholder|reviewer_identity.*placeholder/i);
});

test('reviewer_identity must remain independent from the Draft owner', (t) => {
  expectBlockMatching(t, { reviewPath: (content) => replaceField(content, 'reviewer_identity', '"AI"') }, /reviewer_identity must be independent from the Draft owner/);
});

test('semantic emphasis plan rejects malformed canonical rows', (t) => {
  const invalid = '["condition|Incomplete judgment without placement"]';
  expectBlockMatching(t, {
    briefPath: (content) => replaceField(content, 'semantic_emphasis_plan', invalid),
    draftPath: (content) => replaceField(content, 'semantic_emphasis_plan', invalid),
  }, /semantic_emphasis_plan entry 1 must use role\|complete_judgment\|placement/);
});

test('semantic emphasis plan cannot drift between Brief and Draft', (t) => {
  expectBlockMatching(t, {
    draftPath: (content) => replaceField(content, 'semantic_emphasis_plan', '["decision|Reject the candidate when thermal evidence is unavailable.|decision section"]'),
  }, /semantic_emphasis_plan must match exactly between Brief and Draft/);
});

test('semantic emphasis judgments must be materially implemented in the Draft', (t) => {
  const unrelated = '["risk|Quarantine azurite vials whenever cryogenic spectroscopy remains unavailable.|opening section"]';
  expectBlockMatching(t, {
    briefPath: (content) => replaceField(content, 'semantic_emphasis_plan', unrelated),
    draftPath: (content) => replaceField(content, 'semantic_emphasis_plan', unrelated),
  }, /must materially implement semantic_emphasis_plan judgment 1/);
});

test('semantic emphasis requires at least one planned bold judgment in the Draft', (t) => {
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => body.replace(/\*\*/g, '')) }, /must visibly strong-emphasize every planned decision-scanning judgment|every semantic_emphasis_plan judgment must be implemented as an exact Markdown strong span/);
});

test('semantic emphasis review verdict must pass', (t) => {
  expectBlockMatching(t, { reviewPath: (content) => replaceField(content, 'semantic_emphasis_verdict', '"block"') }, /semantic_emphasis_verdict must be pass/);
});

test('dominant task contract cannot pack competing task families', (t) => {
  const packed = '"learn compare validate buy|cargo motor selection|mixed research RFQ and purchase output|Validate|technical-review"';
  expectBlockMatching(t, allRecords('dominant_task_contract', packed), /noncommercial-stage dominant_task_contract must not contain a terminal commercial action, partner appointment, preferred-source decision, or program nomination/);
});

test('query arrays reject duplicate and excluded commercial modifiers', (t) => {
  expectBlockMatching(t, {
    briefPath: (content) => replaceField(content, 'supporting_query_variants', '["cargo hub motor engineering readiness checklist","cargo hub motor engineering readiness checklist"]'),
  }, /supporting_query_variants must not contain duplicate items|query contract mixes excluded modifier/);
});

test('canonical evidence status vocabulary rejects invented values', (t) => {
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'search_demand_evidence_status', '"verified-ish"') }, /search_demand_evidence_status must use the canonical fact-status vocabulary/);
});

test('confirmed canonical evidence status requires a reference', (t) => {
  expectBlockMatching(t, { briefPath: (content) => replaceField(replaceField(content, 'first_party_proof_status', '"confirmed"'), 'first_party_proof_refs', '[]') }, /confirmed first_party_proof_status requires first_party_proof_refs/);
});

test('synthetic fixture cannot claim market information gain', (t) => {
  expectBlockMatching(t, allRecords('market_information_gain_status', '"confirmed"'), /synthetic market_information_gain_status must remain missing/);
});

test('synthetic fixture requires a completed structural information-gain artifact', (t) => {
  expectBlockMatching(t, allRecords('information_gain_artifact_status', '"missing"'), /synthetic information_gain_artifact_status must be confirmed-for-fixture-structure/);
});

test('role handoff rejects malformed rows', (t) => {
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'role_handoff_contracts', '["Engineer|Quality|missing parts"]') }, /role_handoff_contracts entry must use from_role\|to_role\|url\|retained_task\|receiving_task\|receiving_owner\|acceptance_evidence_ref/);
});

test('role handoff rejects non-HTTPS destinations', (t) => {
  const row = 'Engineer|Quality|http://example.test/guide|retain candidate readiness|define validation evidence|Quality owner|search-evidence.md#reserved-targets-and-acceptance-contracts';
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'role_handoff_contracts', JSON.stringify([row])) }, /field role_handoff_contracts url must be an absolute HTTPS URL for a published package/);
});

test('role handoff evidence cannot escape package root', (t) => {
  const row = 'Engineer|Quality|https://example.test/guide|retain candidate readiness|define validation evidence|Quality owner|../outside.md#evidence';
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'role_handoff_contracts', JSON.stringify([row])) }, /field role_handoff_contracts acceptance_evidence_ref evidence path escapes package evidence root/);
});

test('product decision map rejects malformed rows', (t) => {
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'product_decision_map', '["condition|variable|evidence"]') }, /product_decision_map entry must use condition\|variable\|evidence\|no-fit\|remaining-inputs\|candidate-or-stop\|candidate-target-url-or-N\/A\|next-validation-target-url\|placement/);
});

test('product decision map rejects navigation disguised as a candidate', (t) => {
  const row = 'loaded cargo duty|vehicle load and route duty|bounded synthetic evidence|stop when interface constraints are absent|thermal and sample inputs|catalog|https://example.test/products/catalog|https://example.test/guides/validation|candidate section';
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'product_decision_map', JSON.stringify([row])) }, /product_decision_map candidate must be a conditional product or solution direction, not a navigation page/);
});

test('internal-link target rejects generic anchors', (t) => {
  const rows = ['solution|https://example.test/solutions/cargo-hub-motor-candidates|click here', 'technical-review|https://example.test/guides/cargo-ebike-sample-validation|define next validation evidence'];
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'internal_link_targets', JSON.stringify(rows)) }, /internal-link anchor must describe the buyer task, evidence, decision, or expected output; promotional navigation text is rejected/i);
});

test('internal-link contract must match a declared target', (t) => {
  const rows = ['product|https://example.test/products/other|other product|inspect other product|Engineer|decision section|reserved|Product owner|search-evidence.md#reserved-targets-and-acceptance-contracts'];
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'internal_link_buyer_task_contracts', JSON.stringify(rows)) }, /internal_link_target .* is missing its buyer-task contract|internal-link buyer-task contract .* has no matching internal_link_target/i);
});

test('planned internal-link URL must remain buyer-invisible while any publication gate is blocked', (t) => {
  const url = 'https://example.test/solutions/cargo-hub-motor-candidates';
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => `${body}

Blocked target leak: ${url}
`) }, /internal-link URL must not be buyer-visible until reference, reachability, and capability gates all pass/);
});

test('CTA destination must be HTTPS and visible in Draft', (t) => {
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'cta_destination', '"http://example.test/contact"') }, /field cta_destination must be an absolute HTTPS URL for a published package|CTA destination must be a real Markdown-to-Slate link node/);
});

for (const [field, value] of [
  ['cta_required_inputs', '["input","input","input"]'],
  ['required_inquiry_inputs', '["1","2","3"]'],
  ['cta_trigger', '"TBD"'],
  ['cta_expected_output', '"todo"'],
  ['cta_validation_boundary', '"placeholder"'],
  ['cta_owner', '"owner"'],
]) {
  test(`canonical CTA or inquiry contract rejects weak ${field}`, (t) => {
    expectBlockMatching(t, { briefPath: (content) => replaceField(content, field, value) }, new RegExp(`${field}.*(?:non-concrete|low-entropy|placeholder|concrete|buyer role|owner)`, 'i'));
  });
}

test('CTA inputs cannot drift from first-round inquiry inputs', (t) => {
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'cta_required_inputs', '["loaded vehicle mass","wheel diameter","route grade"]') }, /cta_required_inputs must exactly equal the stage-specific first_round_inquiry_inputs/);
});

test('qualification reason codes require technical, follow-up, and no-fit routes', (t) => {
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'qualification_reason_codes', '["accepted|complete|review","accepted-two|complete|review","accepted-three|complete|review"]') }, /qualification_reason_codes requires an explicit technical no-fit disqualified route/);
});

test('missing inquiry input cannot be classified as a disqualifier', (t) => {
  const rows = ['technical-review-ready|packet complete|perform review', 'needs-follow-up|missing evidence|request missing evidence', 'disqualified|required input is missing|stop'];
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'qualification_reason_codes', JSON.stringify(rows)) }, /missing first\/second-round inputs must route to needs-follow-up, never disqualified/);
});

for (const [label, transform] of [
  ['Markdown H1', (body) => `# Duplicate title\n\n${body}`],
  ['H3 before H2', (body) => `### Premature subsection\n\n${body}`],
  ['raw HTML', (body) => `${body}\n<div>unsupported</div>\n`],
  ['fenced code', (body) => `${body}\n\`\`\`js\nalert(1)\n\`\`\`\n`],
  ['Markdown image', (body) => `${body}\n![hero](https://example.test/hero.jpg)\n`],
  ['HTML comment', (body) => `${body}\n<!-- hidden -->\n`],
]) {
  test(`actual Draft rejects unsupported ${label}`, (t) => {
    const patterns = {
      'Markdown H1': /publishable-body extraction failed closed: Markdown H1 is not allowed when the CMS title is supplied separately/,
      'H3 before H2': /first body heading must be H2|heading hierarchy skips/,
      'raw HTML': /AllinCMS Markdown-to-Slate validation failed: Raw HTML is unsupported/,
      'fenced code': /AllinCMS Markdown-to-Slate validation failed: Markdown code blocks are unsupported-current-shape/,
      'Markdown image': /Markdown image must be declared by and bound to exactly one required image-like visual_decision_assets row/,
      'HTML comment': /AllinCMS Markdown-to-Slate validation failed: Raw HTML is unsupported/,
    };
    expectBlockMatching(t, { draftPath: (content) => transformBody(content, transform) }, patterns[label]);
  });
}

test('direct answer must remain visible near the opening', (t) => {
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => body.replace(/^[\s\S]*?(?=^##\s)/m, 'A general introduction explains that engineering review requires context, but it deliberately omits the action, decision object, route, condition, and evidence boundary from the opening.\n\n')) }, /opening 80-120 words|direct-answer action slot|decision-object slot|expected output\/route slot|evidence boundary slot/);
});

test('duplicate long article sentences are rejected', (t) => {
  const sentence = 'This deliberately repeated sentence is long enough to create a duplicate-content scanning failure in the article package.';
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => `${body}\n${sentence}\n\n${sentence}\n`) }, /repeats the same full sentence 2 times/);
});

for (const claim of [
  'Publishing this article will guarantee a number one ranking.',
  'This article will increase qualified inquiries by 40%.',
  'The workflow will double conversion without additional evidence.',
  'Publishing this article w\u200bill r\u200bank first.',
  'Publishing this article ｗｉｌｌ ｒａｎｋ first.',
  'Publishing this article w**ill** r**ank** first.',
]) {
  test(`unsupported outcome claim is blocked: ${claim.slice(0, 36)}`, (t) => {
    expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => `${body}\n\n${claim}\n`) }, /contains an unsupported ranking, inquiry, or conversion outcome claim/);
  });
}

for (const [label, table] of [
  ['blank cells', '| Field | Candidate A | Candidate B | Why |\n|---|---|---|---|\n| Load |  |  | boundary |\n| Duty |  |  | boundary |'],
  ['placeholder cells', '| Field | Candidate A | Candidate B | Why |\n|---|---|---|---|\n| Load | To be supplied | To be supplied | boundary |\n| Duty | TBD | TBD | boundary |'],
  ['low-entropy repeated cells', '| Field | Candidate A | Candidate B | Why |\n|---|---|---|---|\n| Load | Pending | Pending | boundary |\n| Duty | Pending | Pending | boundary |'],
]) {
  test(`Candidate A/B information-gain table rejects ${label}`, (t) => {
    expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => `${body}\n\n## Candidate comparison\n\n${table}\n`) }, /comparison\/decision table candidate columns .* must contain enough materially different non-placeholder evidence/i);
  });
}

test('local evidence reference cannot escape the package root', (t) => {
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'buyer_task_evidence_refs', '["../outside.md#evidence"]') }, /buyer_task_evidence_refs evidence path escapes package evidence root/);
});

test('local evidence reference must resolve to an existing file', (t) => {
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'buyer_task_evidence_refs', '["missing.md#evidence"]') }, /buyer_task_evidence_refs evidence path does not exist as a file/);
});

test('symlink evidence cannot escape the package root', (t) => {
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'buyer_task_evidence_refs', '["escape.md#evidence"]') }, /buyer_task_evidence_refs evidence path resolves outside package evidence root/, (dir) => {
    const outside = join(dirname(dir), 'outside-evidence.md');
    t.after(() => rmSync(outside, { force: true }));
    writeFileSync(outside, '# Evidence\n');
    symlinkSync(outside, join(dir, 'escape.md'));
  });
});

for (const [field, value] of [
  ['production_evidence_review_verdict', '"pass"'],
  ['fatal_gate_verdict', '"pass"'],
  ['production_readiness', '"ready"'],
  ['release_decision', '"published"'],
  ['operation_mode', '"publish"'],
]) {
  test(`synthetic fixture cannot promote ${field}`, (t) => {
    expectBlockMatching(t, { publishPath: (content) => replaceField(content, field, value) }, new RegExp(`synthetic fixture requires ${field}=`));
  });
}

for (const [field, value, expectedSyntheticState] of [
  ['cms_mutation_status', '"pass"', 'not-run'], ['backend_readback_status', '"pass"', 'not-run'], ['editor_reopen_status', '"pass"', 'not-run'],
  ['anonymous_frontend_status', '"pass"', 'not-run'], ['desktop_acceptance_status', '"pass"', 'not-run'], ['mobile_acceptance_status', '"pass"', 'not-run'],
  ['image_fetch_decode_status', '"pass"', 'not-run'], ['html_lang_status', '"pass"', 'deferred-block'], ['canonical_status', '"pass"', 'deferred-block'],
  ['article_json_ld_status', '"pass"', 'deferred-block'], ['final_dom_image_alt_renderer_status', '"pass"', 'block'],
]) {
  test(`synthetic lifecycle rejects ${field}=${value}`, (t) => {
    expectBlockMatching(t, { publishPath: (content) => replaceField(content, field, value) }, new RegExp(`synthetic fixture requires ${field}=${expectedSyntheticState}`));
  });
}

for (const [field, value] of [
  ['publication_status', '"published"'], ['api_write_status', '"pass"'], ['authorization_status', '"pass"'],
  ['frontend_acceptance_status', '"pass"'], ['cms_action_status', '"pass"'],
]) {
  test(`synthetic fixture rejects shadow lifecycle ${field}=${value}`, (t) => {
    expectBlockMatching(t, { publishPath: (content) => replaceField(content, field, value) }, new RegExp(`synthetic fixture requires ${field}=`));
  });
}

test('synthetic fixture requires rollback_ready=false', (t) => {
  expectBlockMatching(t, { publishPath: (content) => replaceField(content, 'rollback_ready', 'true') }, /synthetic fixture requires rollback_ready=false/);
});

test('synthetic evidence cannot masquerade as production', (t) => {
  expectBlockMatching(t, allRecords('evidence_scope', '"production"'), /production query_evidence_status must be confirmed|production .* axis requires|production evidence/i);
});

test('production axes fail closed on synthetic-only reference evidence', (t) => {
  const mutations = allRecords('evidence_scope', '"production"');
  for (const key of Object.keys(mutations)) {
    const base = mutations[key];
    mutations[key] = (content) => replaceField(base(content), 'internal_link_reference_evidence_result', '"synthetic-only"');
  }
  expectBlockMatching(t, mutations, /production internal_link_reference axis requires executed \+ confirmed \+ pass|internal_link_reference_evidence_result must be confirmed/);
});

test('production lifecycle cannot publish without all production verdicts and acceptance evidence', (t) => {
  const mutations = allRecords('evidence_scope', '"production"');
  mutations.publishPath = (content) => {
    let output = replaceField(content, 'evidence_scope', '"production"');
    output = replaceField(output, 'release_decision', '"published"');
    output = replaceField(output, 'operation_mode', '"publish"');
    return output;
  };
  expectBlockSatisfying(t, mutations, (problems) => {
    const message = problems.join('\n');
    assert.match(message, /published production package requires publication_status=published/);
    assert.match(message, /published production package requires (?:cms_mutation_status|api_write_status|authorization_status|frontend_acceptance_status)=pass/);
    assert.match(message, /published production package requires rollback_ready=true/);
  });
});

test('production published gate consumes canonical publication, API, authorization, frontend, rollback, and CMS action fields', (t) => {
  const mutations = {};
  for (const key of Object.keys(fixtureNames)) {
    mutations[key] = (content) => {
      let output = projectToCurrentTemplate(content, templateNames[key]);
      output = replaceField(output, 'evidence_scope', '"production"');
      output = replaceField(output, 'structure_review_verdict', '"pass"');
      output = replaceField(output, 'production_evidence_review_verdict', '"pass"');
      output = replaceField(output, 'fatal_gate_verdict', '"pass"');
      output = replaceField(output, 'production_readiness', '"ready"');
      output = replaceField(output, 'release_decision', '"published"');
      output = replaceField(output, 'operation_mode', '"publish"');
      return output;
    };
  }
  expectBlockSatisfying(t, mutations, (problems) => {
    const message = problems.join('\n');
    for (const field of ['publication_status', 'api_write_status', 'authorization_status', 'frontend_acceptance_status', 'rollback_ready', 'cms_action_status']) {
      assert.match(message, new RegExp(`published production package requires ${field}=`));
    }
  });
});

test('production published path explicitly requires every canonical acceptance field', (t) => {
  const mutations = {};
  for (const key of Object.keys(fixtureNames)) {
    mutations[key] = (content) => {
      let output = replaceField(content, 'evidence_scope', '"production"');
      output = replaceField(output, 'structure_review_verdict', '"pass"');
      output = replaceField(output, 'production_evidence_review_verdict', '"pass"');
      output = replaceField(output, 'fatal_gate_verdict', '"pass"');
      output = replaceField(output, 'production_readiness', '"ready"');
      output = replaceField(output, 'release_decision', '"published"');
      output = replaceField(output, 'operation_mode', '"publish"');
      return output;
    };
  }
  expectBlockSatisfying(t, mutations, (problems) => {
    const message = problems.join('\n');
    for (const field of [
      'cms_mutation_status', 'backend_readback_status', 'editor_reopen_status', 'anonymous_frontend_status',
      'desktop_acceptance_status', 'mobile_acceptance_status', 'image_fetch_decode_status', 'html_lang_status',
      'canonical_status', 'article_json_ld_status', 'final_dom_image_alt_renderer_status', 'api_write_status',
      'authorization_status', 'frontend_acceptance_status', 'cms_action_status',
    ]) assert.match(message, new RegExp(`published production package requires ${field}=pass`));
    assert.match(message, /published production package requires publication_status=published/);
    assert.match(message, /published production package requires rollback_ready=true/);
  });
});

test('production published path requires operation_mode=publish', (t) => {
  const mutations = {};
  for (const key of Object.keys(fixtureNames)) mutations[key] = (content) => {
    let output = replaceField(content, 'evidence_scope', '"production"');
    output = replaceField(output, 'structure_review_verdict', '"pass"');
    output = replaceField(output, 'production_evidence_review_verdict', '"pass"');
    output = replaceField(output, 'fatal_gate_verdict', '"pass"');
    output = replaceField(output, 'production_readiness', '"ready"');
    output = replaceField(output, 'release_decision', '"published"');
    output = replaceField(output, 'operation_mode', '"draft"');
    return output;
  };
  expectBlockMatching(t, mutations, /published production package requires operation_mode=publish/);
});


test('V9 closed schema rejects unknown top-level record fields', (t) => {
  expectBlockMatching(t, { briefPath: (content) => insertFields(content, { hidden_control_plane: '"pass"' }) }, /unknown top-level field hidden_control_plane/);
});

test('V9 Template explanation metadata cannot become record control fields', (t) => {
  expectBlockMatching(t, { briefPath: (content) => insertFields(projectToCurrentTemplate(content, templateNames.briefPath), { template_usage: '"hidden control"' }) }, /Template explanation metadata/);
});

for (const alias of ['Sales-Owner', 'salesOwner', 'ＳａｌｅｓＯｗｎｅｒ', 'sаles_owner']) {
  test(`V9 normalized deprecated alias ${alias} is rejected`, (t) => {
    expectBlockMatching(t, { briefPath: (content) => insertFields(content, { [alias]: '"Legacy sales owner"' }) }, /normalized deprecated alias of sales_owner/);
  });
}

test('V9 normalized duplicate canonical keys are rejected', (t) => {
  expectBlockMatching(t, { briefPath: (content) => insertFields(content, { stageRequiredLinkRoles: '["technical-review"]' }) }, /confusable or separator\/case-equivalent fields/);
});

test('V9 Validate cannot hide transactional RFQ and price modifiers', (t) => {
  expectBlockMatching(t, allRecords('primary_query', '"cargo hub motor RFQ price"'), /transactional query modifiers cannot masquerade/);
});

test('V9 Validate commercial commitment must remain none', (t) => {
  const mutations = allRecords('commercial_commitment', '"technical-review"');
  for (const key of Object.keys(mutations)) {
    const base = mutations[key];
    mutations[key] = (content) => replaceField(base(content), 'dominant_task_contract', '"validate|cargo e-bike hub-motor candidate readiness|bounded engineering review and input-readiness result|Validate|technical-review"');
  }
  expectBlockMatching(t, mutations, /Validate stage requires commercial_commitment=none/);
});

test('V9 cannibalization clear cannot carry conflict candidates', (t) => {
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'conflict_candidates', '["https://example.test/posts/overlap|same buyer task|merge"]') }, /cannibalization_status=clear requires empty/);
});

test('V9 cannibalization clear requires zero-result evidence', (t) => {
  expectBlockMatching(t, allRecords('inventory_zero_result_evidence_refs', '[]'), /cannibalization_status=clear requires independent/);
});

test('V9 unresolved cannibalization is fatal', (t) => {
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'cannibalization_status', '"unresolved"') }, /unresolved cannibalization is a fatal/);
});

test('V9 token-bag pain chain is blocked', (t) => {
  const fields = {
    pain_trigger: '"When an engineer receives a motor request."',
    surface_problem: '"The motor input is unclear."',
    operational_friction: '"The motor review causes manual delay."',
    business_consequence: '"The motor delay creates schedule risk."',
    desired_decision: '"Choose the motor sample."',
  };
  const mutate = (content) => Object.entries(fields).reduce((out, [field, value]) => replaceField(out, field, value), content);
  expectBlockMatching(t, { briefPath: mutate, draftPath: mutate }, /pain chain lacks concrete causal continuity|surface_problem must name|three-layer pain/);
});

test('V9 direct-answer keyword bag is not a strong answer', (t) => {
  expectBlockMatching(t, { draftPath: (content) => replaceField(content, 'direct_answer', '"motor candidate evidence review boundary selection"') }, /direct_answer must contain an action|concrete bounded judgment/);
});

test('V9 product candidate URL must bind to visible internal-link contract', (t) => {
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'product_decision_map', '["loaded cargo duty with complete inputs|vehicle load and route duty|synthetic bounded evidence|stop for evidenced incompatibility outside the supported envelope|thermal test packet|candidate|https://example.test/products/unrelated-motor|https://example.test/guides/cargo-ebike-sample-validation|candidate-or-stop section"]') }, /candidate target must bind to a declared solution internal-link contract/);
});

test('V9 Quality cannot receive procurement or price approval', (t) => {
  const row = 'Engineer|Quality|https://example.test/guides/cargo-ebike-sample-validation|retain technical candidate assumptions|approve price quotation and supplier selection|Quality owner|search-evidence.md#reserved-targets-and-acceptance-contracts';
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'role_handoff_contracts', JSON.stringify([row])) }, /Quality cannot receive procurement/);
});

test('V9 missing technical inputs cannot route to disqualified', (t) => {
  const rows = ['disqualified|one or more first-round inputs are missing|required input missing','needs-follow-up|buyer asks a question|request details','disqualified|evidenced incompatibility outside supported envelope|stop'];
  const mutate = (content) => replaceField(content, 'qualification_reason_codes', JSON.stringify(rows));
  expectBlockMatching(t, { briefPath: mutate, draftPath: mutate }, /missing first\/second-round inputs must route to needs-follow-up/);
});

test('V9 RFQ price or timeline intent cannot route to disqualified', (t) => {
  const rows = ['first-round-complete|all first-round inputs complete|engineering-review-ready','needs-follow-up|inputs missing|request missing inputs','disqualified|RFQ price timeline and supplier selection intent|stop request'];
  const mutate = (content) => replaceField(content, 'qualification_reason_codes', JSON.stringify(rows));
  expectBlockMatching(t, { briefPath: mutate, draftPath: mutate }, /RFQ\/price\/timeline\/order\/supplier-selection intent/);
});

test('V9 second-round relationship rows must cover the declared second-round set', (t) => {
  const second = '["loaded vehicle mass and payload range","detailed thermal test method"]';
  expectBlockMatching(t, allRecords('second_round_inquiry_inputs', second), /second_round_input_relationships must contain exactly one row/);
});

test('V9 first-round-only definition cannot produce technical-qualified', (t) => {
  const value = '"technical-qualified when all five first-round inputs are complete and reviewed"';
  const mutations = Object.fromEntries(['briefPath','draftPath','publishPath'].map((key) => [key, (content) => replaceField(content, 'technical_qualification_definition', value)]));
  expectBlockMatching(t, mutations, /technical-qualified requires a complete second-round packet/);
});

test('V9 production search evidence fails closed when query evidence is unconfirmed', (t) => {
  expectBlockMatching(t, allRecords('evidence_scope', '"production"'), /production requires buyer_task_evidence_status=confirmed|production requires search_demand_evidence_status=confirmed/);
});


// V10 Buyer/SEO red-team regression suite.
for (const modifier of [
  'cost', 'cost estimate', 'estimate', 'proposal', 'request for proposal', 'RFP',
  'price', 'quote', 'RFQ', 'order', 'MOQ', 'lead time', 'purchase', 'supplier selection',
]) {
  test(`V10 Validate non-commercial query cannot hide ${modifier}`, (t) => {
    expectBlockMatching(t, allRecords('primary_query', JSON.stringify(`cargo e-bike hub motor ${modifier}`)), /transactional query modifiers cannot masquerade/);
  });
}

test('V10 mixed-script commercial modifier qυote fails closed', (t) => {
  expectBlockMatching(t, allRecords('primary_query', '"cargo e-bike hub motor qυote"'), /mixed-script Latin plus Greek\/Cyrillic\/Armenian/);
});

for (const [script, modifier] of [
  ['Cyrillic', 'quоte'],
  ['Armenian', 'quոte'],
]) {
  test(`V10 mixed-script ${script} commercial modifier fails closed`, (t) => {
    expectBlockMatching(t, allRecords('primary_query', JSON.stringify(`cargo e-bike hub motor ${modifier}`)), /mixed-script Latin plus Greek\/Cyrillic\/Armenian/);
  });
}

test('V10 mixed-script unsupported ranking claim fails closed', (t) => {
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => `${body}\n\nThis article wιll raոk fιrst for every buyer query.\n`) }, /mixed-script Latin plus Greek\/Cyrillic\/Armenian|unsupported ranking/);
});

test('V10 standalone Greek technical symbols remain legal', (t) => {
  expectPass(makeFixture(t, { draftPath: (content) => transformBody(content, (body) => `${body}\n\nFor a standalone technical notation example, α and β remain separately measured coefficients.\n`) }));
});

test('V10 explicitly negated ranking guarantee remains legal', (t) => {
  expectPass(makeFixture(t, { draftPath: (content) => transformBody(content, (body) => `${body}\n\nThis article does not guarantee rankings.\n`) }));
});

for (const [field, value, pattern] of [
  ['stage', '"Validate"', /stage must be exact lowercase/],
  ['intent_class', '"Commercial-Investigation"', /intent_class must be exact lowercase/],
  ['commercial_commitment', '"None"', /commercial_commitment must be exact lowercase/],
]) {
  test(`V10 ${field} accepts canonical lowercase enums only`, (t) => {
    expectBlockMatching(t, allRecords(field, value), pattern);
  });
}

test('V10 blocked internal-link URL in plain text cannot bypass publication gates', (t) => {
  const url = 'https://example.test/solutions/cargo-hub-motor-candidates';
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => `${body}

cargo hub-motor solution family ${url}
`) }, /internal-link URL must not be buyer-visible until reference, reachability, and capability gates all pass/);
});

test('V10 CTA URL in plain text cannot impersonate a Slate link node', (t) => {
  expectBlockMatching(t, syntheticPrimaryEndpointMutations({ plainText: true }), /CTA destination must be a real Markdown-to-Slate link node/, setupLegalSyntheticEvidence);
});

test('V10 generic CTA anchor Click here is blocked', (t) => {
  expectBlockMatching(t, syntheticPrimaryEndpointMutations({ anchor: 'Click here' }), /CTA link anchor must be action\/output specific/, setupLegalSyntheticEvidence);
});

for (const anchor of ['Learn more', 'Read more']) {
  test(`V10 generic CTA anchor ${anchor} is blocked`, (t) => {
    expectBlockMatching(t, syntheticPrimaryEndpointMutations({ anchor }), /CTA link anchor must be action\/output specific/, setupLegalSyntheticEvidence);
  });
}

test('V10 blocked internal-link URL with an unrelated anchor cannot bypass publication gates', (t) => {
  const link = '[Annual report archive](https://example.test/solutions/cargo-hub-motor-candidates)';
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => `${body}

${link}
`) }, /internal-link URL must not be buyer-visible until reference, reachability, and capability gates all pass/);
});

test('V10 blocked internal-link URL in the wrong H2 section cannot bypass publication gates', (t) => {
  const canonicalLink = '[cargo hub-motor solution family](https://example.test/solutions/cargo-hub-motor-candidates)';
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => replaceRequiredLiteral(body, '## Use five decision blocks before the first review', `## Use five decision blocks before the first review\n\n${canonicalLink}\n`, 'blocked wrong-H2 insertion point')) }, /internal-link URL must not be buyer-visible until reference, reachability, and capability gates all pass/);
});

const productionInternalLinkRefs = {
  reference: ['internal-link-reference-evidence.md#solution-target', 'internal-link-reference-evidence.md#technical-review-target'],
  reachability: ['internal-link-reachability-evidence.md#solution-target', 'internal-link-reachability-evidence.md#technical-review-target'],
  capability: ['internal-link-capability-evidence.md#solution-target', 'internal-link-capability-evidence.md#technical-review-target'],
};

const canonicalSolutionMarkdownLink = '[Review the cargo hub-motor solution family and unresolved inputs](https://example.test/solutions/cargo-hub-motor-candidates)';
const canonicalTechnicalMarkdownLink = '[Define the next sample-validation evidence](https://example.test/guides/cargo-ebike-sample-validation)';

function productionInternalLinkMutations({ solutionAnchor = 'Review the cargo hub-motor solution family and unresolved inputs', solutionPlacement = 'candidate' } = {}) {
  const linkContracts = [
    'solution|https://example.test/solutions/cargo-hub-motor-candidates|review the cargo hub-motor solution family and unresolved inputs|review the solution family boundary and unresolved inputs|Engineer|candidate-or-stop section|confirmed|Morgan Lee, Product Content Lead|internal-link-acceptance-evidence.md#solution-target',
    'technical-review|https://example.test/guides/cargo-ebike-sample-validation|define the next sample-validation evidence|prepare the next bench and vehicle validation task|Quality|next-validation section|confirmed|Jordan Rivera, Quality Validation Lead|internal-link-acceptance-evidence.md#technical-review-target',
  ];
  const optionalFields = new Set([
    'internal_link_buyer_task_contracts',
    'internal_link_buyer_task_contracts_snapshot',
    'internal_link_reference_evidence_refs',
    'internal_link_reachability_evidence_refs',
    'internal_link_capability_evidence_refs',
  ]);
  return Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => {
    let output = content;
    for (const [field, value] of Object.entries({
      evidence_scope: 'production',
      internal_link_buyer_task_contracts: linkContracts,
      internal_link_buyer_task_contracts_snapshot: linkContracts,
      internal_link_reference_check_execution_status: 'executed', internal_link_reference_evidence_result: 'confirmed', internal_link_reference_gate_verdict: 'pass', internal_link_reference_evidence_refs: productionInternalLinkRefs.reference,
      internal_link_reachability_check_execution_status: 'executed', internal_link_reachability_evidence_result: 'confirmed', internal_link_reachability_gate_verdict: 'pass', internal_link_reachability_evidence_refs: productionInternalLinkRefs.reachability,
      internal_link_capability_check_execution_status: 'executed', internal_link_capability_evidence_result: 'confirmed', internal_link_capability_gate_verdict: 'pass', internal_link_capability_evidence_refs: productionInternalLinkRefs.capability,
    })) {
      output = optionalFields.has(field)
        ? replaceIfPresent(output, field, JSON.stringify(value))
        : replaceField(output, field, JSON.stringify(value));
    }
    if (key === 'draftPath') output = transformBody(output, (body) => {
      const solutionLink = `[${solutionAnchor}](https://example.test/solutions/cargo-hub-motor-candidates)`;
      const solutionHeading = solutionPlacement === 'candidate'
        ? '## Candidate or stop: make the boundary visible'
        : '## Why wattage-first selection may create avoidable rework';
      let visible = replaceRequiredLiteral(body, solutionHeading, `${solutionHeading}\n\n${solutionLink}`, 'production solution-link placement');
      visible = replaceRequiredLiteral(visible, '## Hand the candidate to the next validation task', `## Hand the candidate to the next validation task\n\n${canonicalTechnicalMarkdownLink}`, 'production technical-link placement');
      return visible;
    });
    if (key === 'briefPath' || key === 'publishPath') output = transformDocumentBody(output, (body) => {
      const solutionLink = `[${solutionAnchor}](https://example.test/solutions/cargo-hub-motor-candidates)`;
      const marker = key === 'briefPath' ? '## 7. Internal-link task contracts' : '### Content-navigation links';
      return replaceRequiredLiteral(
        body,
        marker,
        `${marker}\n\n- ${solutionLink}\n- ${canonicalTechnicalMarkdownLink}`,
        `production ${key} internal-link narrative`,
      );
    });
    return output;
  }]));
}

function setupProductionInternalLinkEvidence(dir) {
  const targets = [
    {
      slug: 'solution-target',
      heading: 'Solution target',
      url: 'https://example.test/solutions/cargo-hub-motor-candidates',
      role: 'solution',
      task: 'review the solution family boundary and unresolved inputs',
      owner: 'Morgan Lee, Product Content Lead',
    },
    {
      slug: 'technical-review-target',
      heading: 'Technical review target',
      url: 'https://example.test/guides/cargo-ebike-sample-validation',
      role: 'technical-review',
      task: 'prepare the next bench and vehicle validation task',
      owner: 'Jordan Rivera, Quality Validation Lead',
    },
  ];
  mkdirSync(join(dir, 'artifacts'), { recursive: true });
  const section = ({ target, checkId, kind, observedResult }) => {
    const artifactRef = `artifacts/${kind}-${target.slug}.txt`;
    const artifactBytes = `Independent ${kind} evidence for ${target.slug}, ${target.url}, and the declared buyer task captured at 2026-08-02T00:00:00Z.\n`;
    writeFileSync(join(dir, artifactRef), artifactBytes);
    const artifactDigest = `sha256:${createHash('sha256').update(artifactBytes).digest('hex')}`;
    return `## ${target.heading}\n\ncheck_id: ${checkId}\ntarget_url: ${target.url}\ntarget_role: ${target.role}\ntarget_task: ${target.task}\naccountable_owner: ${target.owner}\nobserved_at: 2026-08-02T00:00:00Z\nmethod: independent endpoint-specific ${kind} inspection against the declared buyer task\nobserved_result: ${observedResult}\nartifact_ref: ${artifactRef}\nartifact_digest: ${artifactDigest}\nproducer: Internal Link Evidence Producer\nproducer_id: wco-internal-link-producer-001\nindependent_reviewer: Morgan Lee, Independent Internal Link Reviewer\nindependent_reviewer_id: wco-internal-link-reviewer-001\n`;
  };
  const writeRecord = ({ file, title, kind, checkId, observedResult }) => {
    const body = `# ${title}\n\n${targets.map((target) => section({ target, checkId, kind, observedResult })).join('\n')}`;
    const digest = createHash('sha256').update(body).digest('hex');
    writeFileSync(join(dir, file), `---\ntitle: ${title}\nrecord_type: evidence-record\nevidence_scope: production\nsource: independent endpoint-specific internal-link verification\nobserved_at: 2026-08-02T00:00:00Z\ndigest: sha256:${digest}\nevidence_kind: ${kind}\n---\n${body}`);
  };
  writeRecord({
    file: 'internal-link-acceptance-evidence.md',
    title: 'Internal-link acceptance evidence',
    kind: 'internal-link-acceptance',
    checkId: 'internal-link-acceptance',
    observedResult: 'confirmed the destination accepts and advances the declared internal-link buyer task',
  });
  for (const axis of ['reference', 'reachability', 'capability']) {
    writeRecord({
      file: `internal-link-${axis}-evidence.md`,
      title: `Internal-link ${axis} evidence`,
      kind: `internal-link-${axis}`,
      checkId: `internal-link-${axis}`,
      observedResult: `confirmed the exact target identity and ${axis} behavior for the declared internal-link buyer task`,
    });
  }
}

const internalLinkFocusedPattern = /internal-link URL|internal-link anchor|canonical placement section|product_decision_map .*actual Markdown link|content-navigation destination|internal_link_(?:reference|reachability|capability).*evidence|production internal_link_(?:reference|reachability|capability)/i;

test('V10 all three internal-link gates PASS requires real links in both canonical H2 placements', (t) => {
  expectAxisHasNoFocusedProblem(t, productionInternalLinkMutations(), internalLinkFocusedPattern, setupProductionInternalLinkEvidence);
});

test('V10 all three internal-link gates PASS rejects a plain-text URL that impersonates a link node', (t) => {
  const mutations = productionInternalLinkMutations();
  const base = mutations.draftPath;
  mutations.draftPath = (content) => transformBody(base(content), (body) => replaceRequiredLiteral(body, canonicalSolutionMarkdownLink, 'Review the cargo hub-motor solution family and unresolved inputs https://example.test/solutions/cargo-hub-motor-candidates', 'production plain-text internal-link mutation'));
  expectBlockMatching(t, mutations, /internal-link URL must be a real Markdown-to-Slate link node/, setupProductionInternalLinkEvidence);
});

test('V10 all three internal-link gates PASS rejects unrelated anchor text', (t) => {
  expectBlockMatching(t, productionInternalLinkMutations({ solutionAnchor: 'Annual report archive' }), /internal-link anchor must preserve target identity and buyer-task parity/, setupProductionInternalLinkEvidence);
});

test('V10 all three internal-link gates PASS rejects the right URL in the wrong H2', (t) => {
  expectBlockMatching(t, productionInternalLinkMutations({ solutionPlacement: 'readiness' }), /must appear in its canonical placement section/, setupProductionInternalLinkEvidence);
});

test('V10 Quality cannot approve a cost estimate', (t) => {
  const row = 'Engineer|Quality|https://example.test/guides/cargo-ebike-sample-validation|retain technical candidate assumptions|approve cost estimate and RFQ response|Synthetic Quality owner|search-evidence.md#reserved-targets-and-acceptance-contracts';
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'role_handoff_contracts', JSON.stringify([row])) }, /Quality cannot receive procurement, cost/);
});

test('V10 technical owner cannot be sole sales acceptance owner', (t) => {
  expectBlockMatching(t, Object.fromEntries(['briefPath','draftPath','publishPath'].map((key) => [key, (content) => replaceField(content, 'sales_acceptance_owner', '"Avery Chen, Applications Engineering Lead"')])), /technical owner cannot be the sole sales_acceptance_owner|commercial owner/);
});

test('V10 qualification reason code rejects four-part legacy grammar', (t) => {
  const mutate = (content) => mutateJsonArrayField(content, 'qualification_reason_codes', (rows) => rows.map((row, index) => index ? row : 'needs-follow-up|missing-input|request missing inputs|Avery Chen'));
  expectBlockMatching(t, { briefPath: mutate, draftPath: mutate }, /exact five-part cause-first grammar/);
});

test('V10 missing inputs can route only to needs-follow-up', (t) => {
  const mutate = (content) => mutateJsonArrayField(content, 'qualification_reason_codes', (rows) => rows.map((row) => row.startsWith('disqualified|') ? 'disqualified|missing-input|required inputs are missing|Avery Chen, Applications Engineering Lead|stop the request' : row));
  expectBlockMatching(t, { briefPath: mutate, draftPath: mutate }, /missing inputs may route only to needs-follow-up|disqualified must use cause-category/);
});

test('V10 commercial intent cannot route to disqualified', (t) => {
  const mutate = (content) => mutateJsonArrayField(content, 'qualification_reason_codes', (rows) => rows.map((row) => row.startsWith('disqualified|') ? 'disqualified|evidenced-technical-no-fit|RFQ quote price is requested|Avery Chen, Applications Engineering Lead|stop the request' : row));
  expectBlockMatching(t, { briefPath: mutate, draftPath: mutate }, /commercial intent may route only to commercial-qualification-required/);
});

for (const [field, value, pattern] of [
  ['technical_qualification_gates', '["first-round-complete","second-round-complete","no-evidenced-no-fit"]', /technical_qualification_gates must exactly equal/],
  ['technical_qualification_gates', '["first-round-complete","second-round-complete","no-evidenced-no-fit","named-technical-owner-accepted","management-approved"]', /technical_qualification_gates must exactly equal/],
  ['sales_acceptance_gates', '["explicit-commercial-intent","commercial-qualification-required","commercial-inputs-complete"]', /sales_acceptance_gates must exactly equal/],
  ['sales_acceptance_gates', '["explicit-commercial-intent","commercial-qualification-required","commercial-inputs-complete","named-commercial-owner-reviewed-and-accepted","technical-owner-approved"]', /sales_acceptance_gates must exactly equal/],
]) {
  test(`V10 ${field} rejects missing or extra exact gates: ${value}`, (t) => {
    expectBlockMatching(t, allRecords(field, value), pattern);
  });
}

test('V10 technical-qualified evidence-rule rejects missing exact gate', (t) => {
  const mutate = (content) => mutateJsonArrayField(content, 'qualification_reason_codes', (rows) => rows.map((row) => row.startsWith('technical-qualified|') ? 'technical-qualified|technical-gates-satisfied|first-round-complete, second-round-complete, and named-technical-owner-accepted are evidenced|Avery Chen, Applications Engineering Lead|continue technical review' : row));
  expectBlockMatching(t, { briefPath: mutate, draftPath: mutate }, /technical-qualified evidence-rule must contain exactly/);
});

test('V10 sales-accepted evidence-rule rejects extra gate', (t) => {
  const mutate = (content) => mutateJsonArrayField(content, 'qualification_reason_codes', (rows) => rows.map((row) => row.startsWith('sales-accepted|') ? 'sales-accepted|commercial-gates-satisfied|explicit-commercial-intent, commercial-qualification-required, commercial-inputs-complete, named-commercial-owner-reviewed-and-accepted, and management-approved are evidenced|Morgan Lee, Commercial Account Owner|continue accepted commercial step' : row));
  expectBlockMatching(t, { briefPath: mutate, draftPath: mutate }, /sales-accepted evidence-rule must contain exactly/);
});

test('V10 visible direct answer rejects slot-token word salad', (t) => {
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => body.replace(/^\s*[\s\S]*?\n\n/, '\nAssemble wallpaper for the cargo hub-motor candidate-readiness packet with banana route evidence, lantern inputs, random candidate-or-stop output, and an unrelated synthetic boundary before the review can applaud the controller.\n\n')) }, /word-salad|opening 80-120 words|coherently connect/);
});

test('V10 pain chain rejects structured banana-lantern word salad', (t) => {
  const value = '"cargo e-bike program engineer|must choose a cargo motor banana|missing evidence lantern data input|rework wallpaper assumptions and interface|program delay random review cycle|assemble packet and decide candidate-or-stop"';
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'pain_chain_contract', value), draftPath: (content) => replaceField(content, 'pain_chain_contract', value) }, /word-salad|structured parity/);
});

test('V10 zero-result fragment rejects contradictory non-zero overlap claim', (t) => {
  expectBlockMatching(t, {}, /contradictory non-zero\/overlap/, (dir) => {
    const p = join(dir, 'search-evidence.md');
    const content = readFileSync(p, 'utf8').replace('## 6. Independent gate records', 'Found 12 overlapping owner pages in this bounded result.\n\n## 6. Independent gate records');
    writeFileSync(p, content);
  });
});

test('V10 zero-result fragment requires candidate_count uniquely equal to zero', (t) => {
  expectBlockMatching(t, {}, /candidate_count uniquely equal to 0/, (dir) => {
    const p = join(dir, 'search-evidence.md');
    writeFileSync(p, readFileSync(p, 'utf8').replace('candidate_count: 0', 'candidate_count: 0\ncandidate_count: 4'));
  });
});

test('V10 production query evidence cannot be replaced by buyer-task evidence', (t) => {
  const mutations = allRecords('evidence_scope', '"production"');
  mutations.briefPath = (content) => {
    let out = replaceField(content, 'evidence_scope', '"production"');
    out = replaceField(out, 'query_evidence_status', '"confirmed"');
    out = replaceField(out, 'query_evidence_refs', '["search-evidence.md#fixture-buyer-task-evidence"]');
    return out;
  };
  expectBlockMatching(t, mutations, /buyer-task evidence cannot substitute|query evidence .* must bind/);
});

test('V10 production information-gain axes cannot share one fragment', (t) => {
  const mutations = allRecords('evidence_scope', '"production"');
  mutations.briefPath = (content) => {
    let out = replaceField(content, 'evidence_scope', '"production"');
    out = replaceField(out, 'information_gain_artifact_refs', '["search-evidence.md#fixture-artifact-status-versus-market-information-gain"]');
    out = replaceField(out, 'information_gain_market_refs', '["search-evidence.md#fixture-artifact-status-versus-market-information-gain"]');
    return out;
  };
  expectBlockMatching(t, mutations, /must use different fragments/);
});

function syncBuilderPublishSearchProjection(content, key, title, pageH1 = title) {
  if (key !== 'publishPath') return content;
  let output = mutatePublishSearchFieldTableValue(content, 'SEO title', title);
  output = mutatePublishSearchFieldTableValue(output, 'H1', pageH1);
  return output;
}

function notApplicableSyntheticMutations() {
  const supportingQueries = ['how cargo e-bike hub motors work', 'cargo hub motor engineering concepts'];
  const dominantTask = 'complete|cargo e-bike hub-motor concept input self-check|concept input self-check|learn|none';
  const values = {
    content_action: '"create"',
    stage: '"learn"', intent_class: '"informational"', stage_intake_contract: '"none"', second_round_input_relationships: '[]',
    working_article_title: '"Complete a Cargo E-Bike Hub Motor Concept Input Self-Check"', article_title: '"Complete a Cargo E-Bike Hub Motor Concept Input Self-Check"',
    page_h1: '"Complete a Cargo E-Bike Hub Motor Concept Input Self-Check"',
    slug: '"cargo-ebike-hub-motor-engineering-basics"',
    published_article_title: '"Complete a Cargo E-Bike Hub Motor Concept Input Self-Check"',
    published_slug: '"cargo-ebike-hub-motor-engineering-basics"',
    primary_query: '"cargo e-bike hub motor engineering basics"',
    supporting_query_variants: JSON.stringify(supportingQueries),
    secondary_intent_contracts: JSON.stringify(secondaryIntentContracts(supportingQueries, 'learn', 'none', 'complete the bounded concept self-check')),
    expected_content_type: '"self-contained concept checklist with bounded learning decisions"', expected_content_type_snapshot: '"self-contained concept checklist with bounded learning decisions"',
    content_family_matches: '["checklist"]', content_family_singleton_verdict: '"pass"', body_content_family_implementation_verdict: '"pass"',
    commercial_commitment: '"none"', dominant_search_intent: '"complete a cargo e-bike hub-motor concept input self-check"', dominant_task_contract: JSON.stringify(dominantTask), terminal_action_contract: JSON.stringify(terminalActionContractFromDominant(dominantTask)),
    direct_answer_action: '"complete"',
    direct_answer_object: '"the five cargo hub-motor concept inputs"',
    direct_answer_condition_or_boundary: '"before interpreting wattage labels or treating a concept as project-ready"',
    direct_answer_required_inputs_or_evidence: '["loaded vehicle mass and payload range","target wheel diameter and tire envelope","route grade and repeated-duty profile","battery voltage plus explicitly typed battery-current and phase-current limits","axle, dropout, and brake interface summary"]',
    direct_answer_expected_output_or_route: '"a concept-level list of complete assumptions, missing assumptions, and questions for later evidence work"',
    direct_answer_evidence_boundary: '"the self-check explains input relationships only and does not prove product fit measured performance compliance availability price or supplier acceptance"',
    direct_answer: '"Complete the five cargo hub-motor concept inputs before interpreting wattage labels or treating a concept as project-ready; if any assumption is missing, return a concept-level list of complete assumptions, missing assumptions, and questions for later evidence work without claiming product fit, measured performance, compliance, availability, price, or supplier acceptance."',
    pain_trigger: '"when an Engineer is learning how cargo e-bike hub-motor load route controller and interface assumptions relate"',
    surface_problem: '"supplier wattage labels appear comparable even though load wheel route controller and interface assumptions are missing or incomplete"',
    operational_friction: '"Engineering may repeatedly reinterpret and rework the same motor label because the missing load wheel route controller and interface assumptions keep changing"',
    business_consequence: '"the team may carry an unsupported concept into sample validation and delay the cargo e-bike program schedule with avoidable technical rework"',
    desired_decision: '"separate complete assumptions missing assumptions and later evidence questions before treating a concept as project-ready"',
    pain_chain_contract: '"Engineer|when an Engineer is learning how cargo e-bike hub-motor load route controller and interface assumptions relate|supplier wattage labels appear comparable even though load wheel route controller and interface assumptions are missing or incomplete|Engineering may repeatedly reinterpret and rework the same motor label because the missing load wheel route controller and interface assumptions keep changing|the team may carry an unsupported concept into sample validation and delay the cargo e-bike program schedule with avoidable technical rework|separate complete assumptions missing assumptions and later evidence questions before treating a concept as project-ready"',
    visible_pain_chain: '["Actor|An Engineer is learning how cargo e-bike hub-motor load, route, controller, and interface assumptions relate.","Trigger|When that Engineer is learning how those cargo e-bike hub-motor assumptions relate, supplier wattage labels may appear comparable even though the operating basis is incomplete.","Evidence gap|Because load, wheel, route, controller, and interface assumptions are missing or incomplete, the supplier wattage labels do not have one defensible comparison basis.","Rework|The missing load, wheel, route, controller, and interface assumptions may therefore force Engineering to repeatedly reinterpret and rework the same motor label as those assumptions change.","Consequence|The repeated rework may carry an unsupported concept into sample validation and delay the cargo e-bike program schedule.","Decision|Separate complete assumptions, missing assumptions, and later evidence questions before treating a concept as project-ready."]',
    visible_pain_chain_sequence_verdict: '"pass"',
    pain_trigger_snapshot: '"when an Engineer is learning how cargo e-bike hub-motor load route controller and interface assumptions relate"',
    surface_problem_snapshot: '"supplier wattage labels appear comparable even though load wheel route controller and interface assumptions are missing or incomplete"',
    operational_friction_snapshot: '"Engineering may repeatedly reinterpret and rework the same motor label because the missing load wheel route controller and interface assumptions keep changing"',
    business_consequence_snapshot: '"the team may carry an unsupported concept into sample validation and delay the cargo e-bike program schedule with avoidable technical rework"',
    desired_decision_snapshot: '"separate complete assumptions missing assumptions and later evidence questions before treating a concept as project-ready"',
    stage_primary_outcome: '"complete a bounded concept self-check without submitting project data"',
    first_round_expected_output: '"not-applicable"', candidate_decision_required_gates: '["not-applicable"]',
    stage_cta_mode: '"education"', stage_required_link_roles: '[]', stage_sales_qualification_requirement: '"not-applicable"',
    cta_interaction_type: '"inline-no-input"', cta_input_collection_applicability: '"not-applicable"',
    cta_data_purpose: '"not-applicable"', cta_data_retention_period: '"not-applicable"',
    cta_data_deletion_path: '"not-applicable"', cta_data_retention_owner: '"not-applicable"',
    cta_data_policy_contract_id: '"not-applicable"', cta_data_policy_status: '"not-applicable"',
    cta_data_policy_effective_at: '"not-applicable"', cta_data_policy_checked_at: '"not-applicable"',
    cta_data_policy_owner_acceptance: '"not-applicable"', cta_data_policy_evidence_refs: '[]',
    cta_data_deletion_capability_evidence_refs: '[]',
    cta_from_role: '"not-applicable"', cta_to_role: '"not-applicable"', cta_receiving_task: '"not-applicable"', cta_receiving_owner: '"not-applicable"',
    cta_input_collection_not_applicable_reason: '"This educational page explains concepts and does not collect or hand off buyer inputs."',
    cta_contract_status: '"not-applicable"', cta_input_collection_mode: '"not-applicable"', cta_input_alignment_status: '"not-applicable"',
    cta_required_inputs: '[]', cta_required_inputs_snapshot: '[]', cta_progressive_profiling_status: '"not-applicable"', cta_progressive_profiling_omitted_inputs: '[]',
    cta_progressive_profiling_followup_action: '"not-applicable"', cta_progressive_profiling_followup_owner: '"not-applicable"',
    cta_complete_over_six_justification: '"not-applicable"', cta_soft_path: '"not-applicable"',
    cta_abandonment_measurement_status: '"planned"', cta_abandonment_measurement_refs: '["cta-measurement-evidence.md#cta-measurement-plan"]',
    cta_trigger: '"not-applicable"', cta_expected_output: '"not-applicable"', cta_validation_boundary: '"not-applicable"',
    cta_destination: '"not-applicable"', cta_owner: '"not-applicable"', cta_fallback_message_template: '"not-applicable"',
    cta_fallback_route_contract: '"not-applicable|not-applicable|not-applicable|not-applicable|not-applicable|not-applicable|not-applicable|not-applicable|not-applicable|not-applicable|not-applicable|not-applicable|not-applicable|not-applicable|not-applicable|not-applicable|not-applicable"',
    buyer_visible_cta_inventory: '["primary-inline-self-check-01|paragraph|optional self-check|Use the inline self-check and submit no project data.|not-applicable|Riley Morgan, Engineering Reader|inline-no-input|not-applicable|not-applicable|not-applicable","soft-immediate-self-check-01|paragraph|optional self-check|No human response is promised; this is an immediate self-check only.|not-applicable|Riley Morgan, Engineering Reader|inline-no-input|not-applicable|not-applicable|not-applicable","fallback-data-boundary-01|paragraph|optional self-check|Do not submit confidential drawings, credentials, personal data, or controlled files.|not-applicable|Riley Morgan, Engineering Reader|inline-no-input|not-applicable|not-applicable|not-applicable"]',
    buyer_language_seeds: '["how cargo e-bike hub motors work","cargo hub motor engineering basics"]',
    query_language_transformation_reason: '"Preserve buyer wording about how cargo e-bike hub motors work while normalizing it into cargo hub motor engineering basics."',
    visual_decision_assets: '["decision-table|learn cargo e-bike hub motor load route controller and interface assumptions|the five inputs explain sample validation rework concepts|search-evidence.md#fixture-artifact-status-versus-market-information-gain|five-input readiness checklist|Five inputs that determine whether a cargo hub-motor assumption is ready for concept review|not-applicable-for-semantic-table|stack each row as labeled key-value groups at 320px without hiding the decision column|required"]',
    semantic_emphasis_plan: '["decision|Separate complete assumptions, missing assumptions, and later evidence questions before treating a concept as project-ready.|five-input readiness self-check","boundary|This self-check explains input relationships only; it does not prove product fit, measured performance, compliance, availability, price, or supplier acceptance.|learning boundary"]',
    article_decision_sequence_map: '["hook|State the five concept inputs and the learning boundary before the first section.|opening direct answer","diagnose|Connect incomplete assumptions to repeated reinterpretation of wattage labels.|buyer pain chain","decide|Separate complete assumptions missing assumptions and later evidence questions.|five-input readiness self-check","de-risk|Separate concept learning from proof of fit performance compliance availability price or supplier acceptance.|learning boundary","act|Complete the inline self-check without submitting project data.|optional self-check"]',
    article_decision_sequence_verdict: '"pass"',
    conversion_surface_map: '["primary-inline-self-check-01|primary|review the five cargo hub-motor concept inputs without submitting project data|optional self-check|inline-no-input|not-applicable","soft-immediate-self-check-01|soft|separate complete assumptions missing assumptions and later evidence questions|optional self-check|inline-no-input|not-applicable","fallback-data-boundary-01|fallback|retain the concept notes locally because this stage exposes no external route|optional self-check|inline-no-input|not-applicable"]',
    cta_measurement_map: '["primary-inline-self-check-01|primary|learn-article-v1|learn-primary-self-check-v1|cta_learn_primary_start|cta_learn_primary_complete|cta_learn_primary_success|cta_learn_primary_failure|primary start without completion success or failure within 30 minutes|not-applicable|not-applicable|synthetic-analytics-spec|not-run-no-production-baseline|30-days-after-production-enable|Riley Morgan, Engineering Reader|cta-measurement-evidence.md#cta-measurement-plan","soft-immediate-self-check-01|soft|learn-article-v1|learn-soft-self-check-v1|cta_learn_soft_start|cta_learn_soft_complete|cta_learn_soft_success|cta_learn_soft_failure|soft start without completion success or failure within 30 minutes|not-applicable|not-applicable|synthetic-analytics-spec|not-run-no-production-baseline|30-days-after-production-enable|Riley Morgan, Engineering Reader|cta-measurement-evidence.md#cta-measurement-plan","fallback-data-boundary-01|fallback|learn-article-v1|learn-fallback-boundary-v1|cta_learn_fallback_start|cta_learn_fallback_complete|cta_learn_fallback_success|cta_learn_fallback_failure|fallback start without completion success or failure within 30 minutes|not-applicable|not-applicable|synthetic-analytics-spec|not-run-no-production-baseline|30-days-after-production-enable|Riley Morgan, Engineering Reader|cta-measurement-evidence.md#cta-measurement-plan"]',
    conversion_surface_map_verdict: '"pass"',
    cta_value_exchange: '"A self-service checklist for reviewing cargo hub-motor evidence-input concepts without submitting project data."',
    cta_response_expectation: '"No human response is promised; this is an immediate self-check only."',
    cta_submission_method: '"Use the inline self-check and submit no data."',
    cta_confidentiality_or_data_boundary: '"Do not submit confidential drawings, credentials, personal data, or controlled files."',
    cta_commitment_boundary: '"Completing the self-check creates no review, quote, order, or supplier commitment."',
    cta_buyer_visible_owner: '"Riley Morgan, Engineering Reader"',
    product_link_evidence_level: '"none"',
    stage_link_requirement_status: '"not-applicable"',
    stage_link_not_applicable_reason: '"The educational stage is self-contained and requires no destination link."',
    internal_link_targets: '[]', internal_link_targets_snapshot: '[]', internal_link_buyer_task_contracts: '[]', internal_link_buyer_task_contracts_snapshot: '[]',
    product_decision_map_status: '"not-applicable"', product_decision_map: '[]', product_decision_map_snapshot: '[]',
    internal_link_plan_status: '"not-applicable"', role_handoff_contracts: '[]', required_inquiry_inputs: '[]', first_round_inquiry_inputs: '[]',
    first_round_input_specifications: '[]', first_round_input_specifications_snapshot: '[]',
    cta_buyer_visible_capability_proofs: '[]', cta_buyer_visible_capability_proofs_snapshot: '[]',
    second_round_inquiry_inputs: '[]', technical_qualification_gates: '[]', sales_acceptance_gates: '[]', qualification_reason_codes: '[]',
    disqualifiers: '[]',
    technical_qualification_requirement: '"not-applicable"', technical_qualification_contract_status: '"not-applicable"',
    technical_qualification_definition: '"not-applicable"', technical_qualification_owner: '"not-applicable"', technical_qualification_next_step: '"not-applicable"',
    sales_acceptance_requirement: '"not-applicable"', sales_acceptance_contract_status: '"not-applicable"',
    sales_acceptance_owner: '"not-applicable"', sales_acceptance_definition: '"not-applicable"', sales_acceptance_next_step: '"not-applicable"',
    sales_commercial_intent_required: '"not-applicable"', sales_commercial_intent_status: '"not-applicable"',
    sales_commercial_inputs_status: '"not-applicable"', sales_commercial_inputs: '[]',
    product_decision_map_verdict: '"not-applicable"', internal_link_stage_contract_verdict: '"not-applicable"',
    cta_stage_contract_verdict: '"not-applicable"', technical_qualification_verdict: '"not-applicable"', sales_acceptance_verdict: '"not-applicable"',
  };
  for (const prefix of ['internal_link_reference', 'internal_link_reachability', 'internal_link_capability', 'cta_reference', 'cta_reachability', 'cta_capability']) {
    values[`${prefix}_check_execution_status`] = '"not-applicable"';
    values[`${prefix}_evidence_result`] = '"not-applicable"';
    values[`${prefix}_gate_verdict`] = '"not-applicable"';
    values[`${prefix}_evidence_refs`] = '[]';
  }
  return Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => {
    let output = projectToCurrentTemplate(content, templateNames[key]);
    for (const [field, value] of Object.entries(values)) output = replaceIfPresent(output, field, value);
    output = setField(output, 'first_round_expected_output', '"not-applicable"');
    output = setField(output, 'candidate_decision_required_gates', '["not-applicable"]');
    if (key === 'draftPath') output = transformBody(output, () => `
Complete the five cargo hub-motor concept inputs before interpreting wattage labels or treating a concept as project-ready: loaded vehicle mass and payload range; target wheel diameter and tire envelope; route grade and repeated-duty profile; battery voltage plus explicitly typed battery-current and phase-current limits; and axle, dropout, and brake interface summary. If any assumption is missing, return a concept-level list of complete assumptions, missing assumptions, and questions for later evidence work. This educational self-check explains input relationships only; it does not prove product fit, measured performance, compliance, availability, price, or supplier acceptance.

${syntheticFictionalDisclosure}

## Buyer pain chain

1. An Engineer is learning how cargo e-bike hub-motor load, route, controller, and interface assumptions relate.
2. When that Engineer is learning how those cargo e-bike hub-motor assumptions relate, supplier wattage labels may appear comparable even though the operating basis is incomplete.
3. Because load, wheel, route, controller, and interface assumptions are missing or incomplete, the supplier wattage labels do not have one defensible comparison basis.
4. The missing load, wheel, route, controller, and interface assumptions may therefore force Engineering to repeatedly reinterpret and rework the same motor label as those assumptions change.
5. The repeated rework may carry an unsupported concept into sample validation and delay the cargo e-bike program schedule.
6. **Separate complete assumptions, missing assumptions, and later evidence questions before treating a concept as project-ready.**

## Five-input readiness checklist

| Concept input | Assumption to record | Concept decision effect |
|---|---|---|
| Loaded vehicle mass and payload range | Record the bounded loaded-mass assumption | Explains the load basis behind a concept |
| Target wheel diameter and tire envelope | Record the effective wheel and packaging assumption | Makes the mechanical leverage assumption visible |
| Route grade and repeated-duty profile | Record grade, duration, and repetition | Separates a short peak from repeated operating duty |
| Battery voltage plus explicitly typed battery-current and phase-current limits | Record voltage, battery-current, and phase-current boundaries separately | Makes the electrical assumption visible without conflating battery and phase current |
| Axle dropout and brake interface summary | Record the interface boundary | Makes the mechanical boundary visible |

For each item, mark the assumption as complete, missing, or reserved for later evidence work.

## Learning boundary

**This self-check explains input relationships only; it does not prove product fit, measured performance, compliance, availability, price, or supplier acceptance.**

## Optional self-check

Use the inline self-check and submit no project data.

No human response is promised; this is an immediate self-check only.

Do not submit confidential drawings, credentials, personal data, or controlled files.

Completing the self-check creates no review, quote, order, or supplier commitment. Riley Morgan, Engineering Reader, owns this private self-check.
`);
    output = syncBuilderPublishSearchProjection(output, key, 'Complete a Cargo E-Bike Hub Motor Concept Input Self-Check');
    return output;
  }]));
}

test('V10 real not-applicable Learn path passes without inputs targets handoff or qualification', (t) => {
  expectPass(makeFixture(t, notApplicableSyntheticMutations()));
});


function completeNoIntakeStageMutations({
  stage, intent, title, slug, primaryQuery, supportingQueries, dominantTask,
  outcome, ctaMode, direct, pain, visual, emphasis, expectedContentType, body,
}) {
  const base = notApplicableSyntheticMutations();
  const values = {
    content_action: '"create"',
    stage: JSON.stringify(stage),
    intent_class: JSON.stringify(intent),
    title: JSON.stringify(title),
    working_article_title: JSON.stringify(title),
    article_title: JSON.stringify(title),
    page_h1: JSON.stringify(title),
    published_article_title: JSON.stringify(title),
    slug: JSON.stringify(slug),
    published_slug: JSON.stringify(slug),
    primary_query: JSON.stringify(primaryQuery),
    supporting_query_variants: JSON.stringify(supportingQueries),
    secondary_intent_contracts: JSON.stringify(secondaryIntentContracts(supportingQueries, stage, 'none', `complete the bounded ${stage} decision task`)),
    dominant_search_intent: JSON.stringify(`${direct.action} ${direct.object} through the bounded ${primaryQuery} evidence task`),
    dominant_task_contract: JSON.stringify(dominantTask),
    terminal_action_contract: JSON.stringify(terminalActionContractFromDominant(dominantTask)),
    stage_primary_outcome: JSON.stringify(outcome),
    stage_cta_mode: JSON.stringify(ctaMode),
    stage_sales_qualification_requirement: '"not-applicable-without-commercial-intent"',
    first_round_expected_output: '"not-applicable"',
    candidate_decision_required_gates: '["not-applicable"]',
    direct_answer_action: JSON.stringify(direct.action),
    direct_answer_object: JSON.stringify(direct.object),
    direct_answer_condition_or_boundary: JSON.stringify(direct.condition),
    direct_answer_evidence_boundary: JSON.stringify(direct.boundary),
    direct_answer_required_inputs_or_evidence: JSON.stringify(direct.inputs),
    direct_answer_expected_output_or_route: JSON.stringify(direct.output),
    direct_answer: JSON.stringify(direct.answer),
    pain_trigger: JSON.stringify(pain.trigger),
    surface_problem: JSON.stringify(pain.surface),
    operational_friction: JSON.stringify(pain.friction),
    business_consequence: JSON.stringify(pain.consequence),
    desired_decision: JSON.stringify(pain.decision),
    pain_chain_contract: JSON.stringify(`Engineer|${pain.trigger}|${pain.surface}|${pain.friction}|${pain.consequence}|${pain.decision}`),
    pain_trigger_snapshot: JSON.stringify(pain.trigger),
    surface_problem_snapshot: JSON.stringify(pain.surface),
    operational_friction_snapshot: JSON.stringify(pain.friction),
    business_consequence_snapshot: JSON.stringify(pain.consequence),
    desired_decision_snapshot: JSON.stringify(pain.decision),
    visual_decision_assets: JSON.stringify([visual]),
    semantic_emphasis_plan: JSON.stringify([emphasis]),
    article_decision_sequence_map: JSON.stringify([
      `hook|State the bounded ${stage} answer and evidence boundary before the first section.|opening direct answer`,
      `diagnose|Connect the buyer trigger to the evidence gap and repeatable rework mechanism.|buyer pain chain`,
      `decide|Return the declared ${stage} decision route without claiming unsupported fit or acceptance.|decision matrix`,
      `de-risk|Separate the self-check result from proof of fit, performance, commercial terms, or supplier acceptance.|boundaries section`,
      `act|Complete the local ${stage} self-check without submitting project data.|optional self-check`,
    ]),
    article_decision_sequence_verdict: '"pass"',
    conversion_surface_map: JSON.stringify([
      ['primary-inline-self-check-01', 'primary', direct.ctaValue, 'optional self-check', 'inline-no-input', 'not-applicable'].join('|'),
      ['soft-immediate-self-check-01', 'soft', `review the ${stage} evidence matrix locally before any route decision`, 'optional self-check', 'inline-no-input', 'not-applicable'].join('|'),
      ['fallback-data-boundary-01', 'fallback', `retain the ${stage} record locally because this stage exposes no external route`, 'optional self-check', 'inline-no-input', 'not-applicable'].join('|'),
    ]),
    cta_measurement_map: JSON.stringify([
      ['primary-inline-self-check-01', 'primary', `${stage}-article-v1`, `${stage}-primary-self-check-v1`, `cta_${stage}_primary_start`, `cta_${stage}_primary_complete`, `cta_${stage}_primary_success`, `cta_${stage}_primary_failure`, 'primary start without completion success or failure within 30 minutes', 'not-applicable', 'not-applicable', 'synthetic-analytics-spec', 'not-run-no-production-baseline', '30-days-after-production-enable', 'Riley Morgan, Engineering Reader', 'cta-measurement-evidence.md#cta-measurement-plan'].join('|'),
      ['soft-immediate-self-check-01', 'soft', `${stage}-article-v1`, `${stage}-soft-self-check-v1`, `cta_${stage}_soft_start`, `cta_${stage}_soft_complete`, `cta_${stage}_soft_success`, `cta_${stage}_soft_failure`, 'soft start without completion success or failure within 30 minutes', 'not-applicable', 'not-applicable', 'synthetic-analytics-spec', 'not-run-no-production-baseline', '30-days-after-production-enable', 'Riley Morgan, Engineering Reader', 'cta-measurement-evidence.md#cta-measurement-plan'].join('|'),
      ['fallback-data-boundary-01', 'fallback', `${stage}-article-v1`, `${stage}-fallback-boundary-v1`, `cta_${stage}_fallback_start`, `cta_${stage}_fallback_complete`, `cta_${stage}_fallback_success`, `cta_${stage}_fallback_failure`, 'fallback start without completion success or failure within 30 minutes', 'not-applicable', 'not-applicable', 'synthetic-analytics-spec', 'not-run-no-production-baseline', '30-days-after-production-enable', 'Riley Morgan, Engineering Reader', 'cta-measurement-evidence.md#cta-measurement-plan'].join('|'),
    ]),
    conversion_surface_map_verdict: '"pass"',
    cta_value_exchange: JSON.stringify(direct.ctaValue),
    cta_response_expectation: '"No human response is promised; this is an immediate self-check only."',
    cta_submission_method: '"Use the inline self-check and submit no project data."',
    cta_confidentiality_or_data_boundary: '"Do not submit confidential drawings, credentials, personal data, or controlled files."',
    cta_commitment_boundary: '"Completing the self-check creates no review, quote, order, or supplier commitment."',
    cta_buyer_visible_owner: '"Riley Morgan, Engineering Reader"',
    buyer_language_seeds: JSON.stringify([primaryQuery, ...supportingQueries.slice(0, 1)]),
    query_language_transformation_reason: JSON.stringify(`Preserve buyer wording from ${primaryQuery} while normalizing it into the declared ${stage} decision task.`),
    expected_content_type: JSON.stringify(expectedContentType),
    expected_content_type_snapshot: JSON.stringify(expectedContentType),
    content_family_matches: JSON.stringify([stage === 'troubleshoot' ? 'diagnostic' : 'comparison']),
    content_family_singleton_verdict: '"pass"',
    body_content_family_implementation_verdict: '"pass"',
  };
  return Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => {
    let output = base[key](content);
    for (const [field, value] of Object.entries(values)) output = replaceIfPresent(output, field, value);
    output = setField(output, 'first_round_expected_output', '"not-applicable"');
    output = setField(output, 'candidate_decision_required_gates', '["not-applicable"]');
    if (key === 'draftPath') output = transformBody(output, () => `\n${syntheticFictionalDisclosure}\n\n${body.trim()}\n`);
    output = syncBuilderPublishSearchProjection(output, key, title);
    return output;
  }]));
}

function completeTroubleshootNoIntakeMutations() {
  return completeNoIntakeStageMutations({
    stage: 'troubleshoot',
    intent: 'troubleshooting',
    title: 'Diagnose a Cargo Hub Motor Controller Fault with an Evidence Matrix',
    slug: 'cargo-hub-motor-controller-fault-diagnosis-checklist',
    primaryQuery: 'cargo hub motor controller fault diagnosis checklist',
    supportingQueries: ['cargo hub motor fault troubleshooting evidence', 'diagnose cargo e-bike motor controller fault'],
    dominantTask: 'diagnose|cargo hub-motor controller fault|diagnostic evidence matrix|troubleshoot|none',
    outcome: 'a bounded diagnostic evidence route for the observed cargo hub-motor controller fault',
    ctaMode: 'self-check',
    direct: {
      action: 'diagnose',
      object: 'cargo hub-motor controller fault',
      condition: 'when the symptom can be reproduced under a recorded operating condition',
      boundary: 'the self-check does not prove root cause, repair safety, or component suitability',
      inputs: ['observed fault symptom', 'operating condition', 'controller and interface evidence'],
      output: 'a diagnostic evidence matrix and the next safe evidence route',
      answer: 'Diagnose the cargo hub-motor controller fault only when the symptom can be reproduced with the observed fault symptom, operating condition, and controller and interface evidence; return a diagnostic evidence matrix and next safe evidence route without claiming root cause, repair safety, or component suitability.',
      ctaValue: 'A self-service diagnostic evidence checklist that separates reproducible fault observations from unsupported guesses.',
    },
    pain: {
      trigger: 'when an Engineer receives a recurring cargo hub-motor controller fault after a loaded route event',
      surface: 'the Engineer cannot compare the recurring fault because the operating condition and controller evidence are missing',
      friction: 'missing operating-condition evidence may force the Engineer to repeat broad fault checks instead of isolating one reproducible pattern',
      consequence: 'repeated diagnostic cycles may delay the cargo e-bike program schedule and sample approval while the observed controller fault remains unresolved',
      decision: 'choose the next safe diagnostic evidence route before another broad fault check',
    },
    visual: 'decision-table|troubleshoot cargo hub-motor controller fault|diagnostic evidence separates reproducible fault observations from unsupported guesses|search-evidence.md#fixture-artifact-status-versus-market-information-gain|diagnostic evidence matrix|Diagnostic evidence matrix for a cargo hub-motor controller fault|not-applicable-for-semantic-table|retain readable table cells on a 320px viewport|required',
    emphasis: 'decision|Choose the next safe diagnostic evidence route before another broad fault check.|diagnostic evidence matrix',
    expectedContentType: 'diagnostic troubleshooting workflow with a bounded next-check route',
    body: `Diagnose the cargo hub-motor controller fault only when the symptom can be reproduced with the observed fault symptom, operating condition, and controller and interface evidence. Return a diagnostic evidence matrix and the next safe evidence route. If any observation is missing, record the gap rather than guessing a cause. This bounded self-check does not prove root cause, repair safety, measured performance, or component suitability, and it does not replace an approved service procedure.

## Buyer pain chain

1. An Engineer owns the recurring cargo hub-motor controller fault review.
2. When the fault appears again after a loaded route event, that Engineer needs one reproducible comparison basis.
3. Because the operating condition and controller evidence are missing, the recurring fault cannot be compared reliably.
4. That evidence gap may force the Engineer to repeat broad diagnostic checks without isolating one reproducible pattern.
5. The repeated diagnostic cycles may delay the cargo e-bike program schedule and sample approval while the observed controller fault remains unresolved.
6. Therefore, **choose the next safe diagnostic evidence route before another broad fault check.**

## Fault troubleshooting evidence matrix

Diagnostic evidence matrix for a cargo hub-motor controller fault:

| Diagnose cargo hub-motor controller fault | Diagnostic evidence that separates reproducible fault observations from unsupported guesses | Safe next route |
|---|---|---|
| Symptom repeats under one operating condition | Record the observed fault symptom, operating condition, and controller and interface evidence | Compare the reproducible pattern against an approved service procedure |
| Symptom cannot be reproduced | Record the missing evidence instead of assigning a cause | Continue local observation without a repair claim |
| Evidence indicates a safety concern | Stop local checks and follow the approved safety escalation route | Do not energize or repair the system from this article |

## Boundaries before action

This checklist separates observations from guesses. It cannot authorize disassembly, electrical work, firmware changes, or continued operation after a safety concern.

## Optional self-check

A self-service diagnostic evidence checklist separates reproducible fault observations from unsupported guesses. Use the inline self-check and submit no project data. No human response is promised; this is an immediate self-check only. Do not submit confidential drawings, credentials, personal data, or controlled files. Completing the self-check creates no review, quote, order, or supplier commitment. The Reader owns the local decision record.`,
  });
}

function completeCompareNoIntakeMutations() {
  return completeNoIntakeStageMutations({
    stage: 'compare',
    intent: 'commercial-investigation',
    title: 'Compare Cargo Hub Motors with a Duty and Interface Decision Matrix',
    slug: 'cargo-hub-motor-comparison-duty-interface-decision-matrix',
    primaryQuery: 'cargo hub motor comparison decision matrix',
    supportingQueries: ['compare cargo e-bike hub motors by duty profile', 'cargo hub motor interface comparison'],
    dominantTask: 'compare|cargo hub-motor candidates for loaded route duty|comparison decision matrix|compare|none',
    outcome: 'a bounded comparison matrix that exposes which candidate evidence remains missing',
    ctaMode: 'self-check',
    direct: {
      action: 'compare',
      object: 'cargo hub-motor candidates for loaded route duty',
      condition: 'only when every candidate uses the same load route electrical and interface evidence',
      boundary: 'the matrix does not prove fit, measured performance, availability, price, or supplier acceptance',
      inputs: ['loaded route duty', 'electrical limits', 'mechanical interface evidence'],
      output: 'a comparison decision matrix with comparable, missing-evidence, or stop routes',
      answer: 'Compare cargo hub-motor candidates for loaded route duty only when every candidate uses the same loaded route duty, electrical limits, and mechanical interface evidence; return a comparison decision matrix with comparable, missing-evidence, or stop routes without claiming fit, measured performance, availability, price, or supplier acceptance.',
      ctaValue: 'A self-service comparison worksheet that keeps candidate assumptions aligned before a shortlist decision.',
    },
    pain: {
      trigger: 'when Procurement asks an Engineer to compare cargo hub-motor candidates for the same loaded route duty',
      surface: 'the Engineer cannot compare candidates because load, electrical, and mechanical interface assumptions differ',
      friction: 'different candidate assumptions may force Procurement and Engineering to repeatedly rebuild and reconcile the comparison instead of reviewing one aligned matrix',
      consequence: 'repeated comparison rebuilds may delay the supplier shortlist and cargo e-bike sample approval schedule while an unsupported candidate direction remains visible',
      decision: 'choose comparable, missing-evidence, or stop for each candidate before a shortlist decision',
    },
    visual: 'decision-table|compare cargo hub-motor candidates|aligned duty and interface evidence supports a comparable missing-evidence or stop route|search-evidence.md#fixture-artifact-status-versus-market-information-gain|candidate comparison decision matrix|Cargo hub-motor candidate comparison decision matrix|not-applicable-for-semantic-table|retain readable table cells on a 320px viewport|required',
    emphasis: 'decision|Choose comparable, missing-evidence, or stop for each candidate before a shortlist decision.|candidate comparison decision matrix',
    expectedContentType: 'comparison matrix with a bounded shortlist-or-stop route',
    body: `Compare cargo hub-motor candidates for loaded route duty only when every candidate uses the same loaded route duty, electrical limits, and mechanical interface evidence. Return a comparison decision matrix with comparable, missing-evidence, or stop routes. If one evidence set is absent, label the gap instead of ranking the candidate. This bounded worksheet does not prove fit, measured performance, availability, price, or supplier acceptance, and it does not select a supplier.

## Buyer pain chain

1. An Engineer owns the evidence comparison requested by Procurement.
2. When Procurement asks that Engineer to compare cargo hub-motor candidates for the same loaded route duty, every candidate needs one aligned evidence basis.
3. Because the load, electrical, and mechanical interface assumptions differ, the candidates cannot be compared on one basis.
4. That evidence gap may force Procurement and Engineering to repeatedly rebuild and reconcile the comparison instead of reviewing one aligned matrix.
5. The repeated comparison rebuilds may delay the supplier shortlist and cargo e-bike sample approval schedule while an unsupported candidate direction remains visible.
6. Therefore, **choose comparable, missing-evidence, or stop for each candidate before a shortlist decision.**

## Candidate comparison decision matrix

Cargo hub-motor candidate comparison decision matrix:

| Compare cargo hub-motor candidates | Aligned duty and interface evidence | Comparable, missing-evidence, or stop route |
|---|---|---|
| Loaded route duty, electrical limits, and mechanical interface evidence use the same basis | Candidate evidence is comparable | Retain for an evidence-based shortlist discussion |
| One or more assumptions differ or are missing | Candidate evidence is not comparable yet | Record the missing evidence before ranking |
| Documented interface evidence conflicts with the required envelope | Candidate direction has an evidenced stop condition | Remove the unsupported direction from this comparison |

## Boundaries before a shortlist

This worksheet compares evidence structure only. It cannot establish model fit, measured performance, compliance, commercial terms, availability, or supplier acceptance.

## Optional self-check

A self-service comparison worksheet keeps candidate assumptions aligned before a shortlist decision.

Use the inline self-check and submit no project data.

No human response is promised; this is an immediate self-check only.

Do not submit confidential drawings, credentials, personal data, or controlled files.

Completing the self-check creates no review, quote, order, or supplier commitment. Riley Morgan, Engineering Reader, owns the local comparison record.`,
  });
}

for (const [label, mutations] of [
  ['Troubleshoot', completeTroubleshootNoIntakeMutations],
  ['Compare', completeCompareNoIntakeMutations],
]) test(`V16 complete ${label} Brief Draft Review Publish package passes its own stage branch`, (t) => {
  expectPass(makeFixture(t, mutations()));
});

const v16BuyInputs = ['requested quantity range', 'delivery destination', 'required delivery window'];
const v16BuySpecifications = [
  'requested quantity range|sets the commercial volume basis for MOQ and quotation review|range in units for minimum, target, and maximum quantity|500-1200 units|required|do not include customer names or confidential contract identifiers',
  'delivery destination|sets the country and logistics basis for a bounded quotation route|country and postal-code format without a street address|United States, 90210|required|do not submit personal names or a private street address',
  'required delivery window|sets the requested commercial timing boundary without promising availability|ISO 8601 date range|2026-10-01 to 2026-11-15|required|use project dates only and remove confidential launch identifiers',
];
const v16BuyReasonCodes = [
  'commercial-qualification-required|explicit-commercial-intent|a cargo hub-motor RFQ requests price, MOQ, delivery, and quotation review|Morgan Lee, Commercial Account Owner|review the commercial packet without treating submission as acceptance',
  'sales-accepted|commercial-gates-satisfied|explicit-commercial-intent, commercial-qualification-required, commercial-inputs-complete, and named-commercial-owner-reviewed-and-accepted are all evidenced|Morgan Lee, Commercial Account Owner|continue only the commercially accepted next step',
];

function completeBuyCommercialMutations() {
  const title = 'Complete a Cargo Hub Motor RFQ Quote Packet and Missing-Input Check';
  const slug = 'complete-cargo-hub-motor-rfq-quote-packet-missing-input-check';
  const commercialGuideUrl = 'https://example.test/guides/cargo-hub-motor-rfq-preparation';
  const reservedSubmissionEndpoint = 'https://example.test/workflows/cargo-hub-motor-rfq-intake';
  const productUrl = 'https://example.test/solutions/cargo-hub-motor-candidates';
  const handoffTask = 'complete and submit the cargo hub-motor RFQ packet for price, MOQ, delivery, and a bounded quotation route';
  const buyerReceivingOwner = 'Riley Brooks, Procurement Lead';
  const owner = 'Morgan Lee, Commercial Account Owner';
  const dataPurpose = 'Use the three RFQ inputs only to perform the bounded commercial packet review and identify missing quotation inputs.';
  const retentionPeriod = 'not-applicable';
  const deletionPath = 'not-applicable';
  const retentionOwner = 'not-applicable';
  const roleHandoff = `Engineer|Procurement|${reservedSubmissionEndpoint}|retain engineering authority for the final configuration boundary without promising an order|${handoffTask}|${buyerReceivingOwner}|search-evidence.md#reserved-targets-and-acceptance-contracts`;
  const linkTargets = [
    `solution|${productUrl}|cargo hub-motor product-family boundary before quotation`,
    `commercial|${commercialGuideUrl}|cargo hub-motor RFQ preparation and commercial evidence boundary`,
  ];
  const linkContracts = [
    `solution|${productUrl}|cargo hub-motor product-family boundary before quotation|review the product candidate boundary before commercial submission|Engineer|decision-path|reserved-synthetic-target|Synthetic Product Content owner|search-evidence.md#reserved-targets-and-acceptance-contracts`,
    `commercial|${commercialGuideUrl}|cargo hub-motor RFQ preparation and commercial evidence boundary|prepare the complete commercial packet without using an unverified submission route|Procurement|decision-path|reserved-synthetic-target|${owner}|search-evidence.md#reserved-targets-and-acceptance-contracts`,
  ];
  const productMap = [
    `cargo hub-motor RFQ with a complete quantity, destination, and delivery-window packet|requested quantity range, delivery destination, required delivery window|synthetic product-family page plus the buyer-supplied commercial packet; price and availability remain unverified|stop only when the requested commercial scope is explicitly unsupported|target configuration, required commercial documentation, and any approved secure-file route|cargo hub-motor solution family for commercial review when the three-input RFQ packet is complete|${productUrl}|${commercialGuideUrl}|opening, decision-path, and final CTA`,
  ];
  const proofCopy = 'The commercial owner reviews quantity, destination, and delivery-window inputs and returns missing items or a bounded quotation route; no price, availability, or acceptance is promised by submission.';
  const fallbackMessage = 'No verified primary or fallback route is available. Do not send or submit this packet. Save this message locally, then use your organization’s existing approved supplier-contact process to request a verified route from the Commercial Account Owner. After a verified route is returned, use this cargo hub-motor RFQ packet: requested quantity range 500-1200 units; delivery destination United States, 90210; required delivery window 2026-10-01 to 2026-11-15. Please return missing commercial inputs or a bounded quotation route. Do not treat this submission as an order or acceptance.';
  const openingInstruction = 'Complete the cargo hub-motor RFQ packet by recording the requested quantity range, delivery destination, and required delivery window on one comparable basis. Mark any missing commercial input before the packet reaches its route-verification step. The resulting local record supports a missing-commercial-input list or a bounded commercial qualification path. This preparation does not prove price, availability, delivery acceptance, supplier award, order acceptance, or sales acceptance, and the local packet is not a purchase order.';
  const productNavigationInstruction = 'The cargo hub-motor product-family boundary supports category-level product review before quotation.';
  const guideNavigationInstruction = 'The cargo hub-motor RFQ preparation guide supports local commercial-packet preparation; it is content-navigation, not a submission endpoint.';
  const productNavigationCopy = productNavigationInstruction;
  const guideNavigationCopy = guideNavigationInstruction;
  const primaryRouteBoundary = 'No verified primary or fallback route is available in this example. Do not send or submit the packet. Save it locally, then use your organization’s existing approved supplier-contact process to request a verified route from the Commercial Account Owner. Until your organization verifies a route through its approved supplier-contact process, no response or bounded quotation route is assumed; response timing is not evidenced and must be confirmed. Do not submit confidential contracts, credentials, personal data, or controlled drawings while the route is unverified; keep them local until a secure route has been confirmed. Preparing the packet requests no commercial commitment and does not create a quote, order, supplier award, delivery promise, or sales acceptance.';
  const fallbackInstruction = `If the RFQ route is unavailable: ${primaryRouteBoundary}`;
  const values = {
    content_action: 'create',
    stage: 'buy', intent_class: 'transactional', stage_intake_contract: 'buy-commercial', commercial_commitment: 'commercial',
    working_article_title: title, article_title: title, page_h1: title, published_article_title: title,
    slug, published_slug: slug,
    primary_query: 'cargo hub motor RFQ quote',
    excluded_query_modifiers: ['repair', 'troubleshooting', 'definition'],
    supporting_query_variants: ['cargo e-bike hub motor quotation request', 'cargo hub motor MOQ and delivery quote'],
    secondary_intent_contracts: secondaryIntentContracts(['cargo e-bike hub motor quotation request', 'cargo hub motor MOQ and delivery quote'], 'buy', 'commercial', 'complete the bounded commercial packet'),
    dominant_search_intent: 'complete a cargo hub-motor RFQ packet for commercial qualification',
    dominant_task_contract: 'complete|cargo hub-motor RFQ packet|complete commercial packet and missing-input list before route verification|buy|commercial',
    terminal_action_contract: 'complete|cargo hub-motor RFQ packet|complete commercial packet and missing-input list before route verification|buy|commercial',
    stage_primary_outcome: 'a complete local cargo hub-motor RFQ packet and missing-commercial-input list before route verification',
    first_round_expected_output: 'not-applicable', candidate_decision_required_gates: ['not-applicable'],
    stage_cta_mode: 'rfq', stage_required_link_roles: ['solution', 'commercial'], stage_sales_qualification_requirement: 'required',
    cta_interaction_type: 'commercial', cta_from_role: 'Engineer', cta_to_role: 'Procurement', cta_receiving_task: handoffTask, cta_receiving_owner: buyerReceivingOwner,
    cta_input_collection_applicability: 'applicable', cta_input_collection_not_applicable_reason: 'not-applicable',
    stage_link_requirement_status: 'applicable', stage_link_not_applicable_reason: 'not-applicable',
    first_round_inquiry_inputs: v16BuyInputs, second_round_inquiry_inputs: [], second_round_input_relationships: [],
    required_inquiry_inputs: v16BuyInputs, cta_required_inputs: v16BuyInputs, cta_progressive_profiling_omitted_inputs: [],
    first_round_input_specifications: v16BuySpecifications, first_round_input_specifications_snapshot: v16BuySpecifications,
    cta_contract_status: 'confirmed-for-fixture-structure', cta_input_collection_mode: 'complete', cta_input_alignment_status: 'confirmed-for-fixture-structure',
    cta_progressive_profiling_status: 'not-used', cta_progressive_profiling_followup_action: 'not-applicable', cta_progressive_profiling_followup_owner: 'not-applicable',
    cta_complete_over_six_justification: 'not-applicable', cta_soft_path: 'not-applicable', cta_abandonment_measurement_status: 'planned',
    cta_trigger: 'when the Engineer has the exact quantity range, delivery destination, and required delivery window for a cargo hub-motor RFQ',
    cta_expected_output: 'missing-commercial-input list or a bounded cargo hub-motor quotation route',
    cta_validation_boundary: 'the output does not prove price, availability, delivery acceptance, supplier award, order acceptance, or sales acceptance',
    cta_destination: 'not-applicable', cta_owner: owner,
    cta_data_purpose: dataPurpose, cta_data_retention_period: retentionPeriod,
    cta_data_deletion_path: deletionPath, cta_data_retention_owner: retentionOwner,
    cta_data_policy_contract_id: 'not-applicable', cta_data_policy_effective_at: 'not-applicable', cta_data_policy_checked_at: 'not-applicable',
    cta_data_policy_status: 'missing', cta_data_policy_owner_acceptance: 'pending', cta_data_policy_evidence_refs: [], cta_data_deletion_capability_evidence_refs: [],
    cta_fallback_message_template: fallbackMessage,
    cta_fallback_route_contract: `unverified-unavailable|not-applicable|${owner}|same-as-cta-required-inputs|Saving the packet locally and requesting a verified route creates no quote, order, supplier award, delivery promise, or sales acceptance.|not-run|missing|block|not-applicable|not-run|missing|block|not-applicable|not-run|missing|block|not-applicable`,
    cta_value_exchange: 'The commercial owner checks the three-input RFQ packet and returns missing commercial inputs or a bounded quotation route.',
    cta_response_expectation: 'Response timing is not evidenced in this synthetic fixture and must be confirmed before a live service promise is published.',
    cta_submission_method: 'No verified primary or fallback route is available in this example. Do not send the packet; save it locally and use the buyer organization’s existing approved supplier-contact process to request a verified route from the Commercial Account Owner.',
    cta_confidentiality_or_data_boundary: 'Do not submit confidential contracts, credentials, personal data, or controlled drawings while the route is unverified; keep them local until a secure route has been confirmed through the buyer organization’s approved supplier-contact process.',
    cta_commitment_boundary: 'Submitting the RFQ packet requests commercial review only; it does not create a quote, order, supplier award, delivery promise, or sales acceptance.',
    cta_buyer_visible_owner: 'Commercial Account Owner',
    buyer_visible_cta_inventory: [
      `primary-opening-rfq-boundary-01|pre-h2|opening direct answer|${openingInstruction}|not-applicable|${owner}|local-tool|not-applicable|not-applicable|not-applicable`,
      `soft-product-navigation-01|link|product decision path|${productNavigationInstruction}|${productUrl}|Morgan Lee, Synthetic Product Content Lead|content-navigation|not-applicable|search-evidence.md#reserved-targets-and-acceptance-contracts|not-applicable`,
      `soft-commercial-guide-01|link|product decision path|${guideNavigationInstruction}|${commercialGuideUrl}|${owner}|content-navigation|not-applicable|search-evidence.md#reserved-targets-and-acceptance-contracts|not-applicable`,
      `primary-route-boundary-01|paragraph|request the bounded quotation route|${fallbackInstruction}|not-applicable|${owner}|commercial|unverified-unavailable|not-applicable|cta_fallback_route_contract`,
      `fallback-copyable-rfq-01|blockquote|copyable fallback message|${fallbackMessage}|not-applicable|${owner}|commercial|unverified-unavailable|not-applicable|cta_fallback_route_contract`,
    ],
    technical_qualification_requirement: 'not-applicable', technical_qualification_contract_status: 'not-applicable', technical_qualification_gates: [],
    technical_qualification_definition: 'not-applicable', technical_qualification_owner: 'not-applicable', technical_qualification_next_step: 'not-applicable',
    sales_acceptance_requirement: 'required', sales_acceptance_contract_status: 'confirmed-for-fixture-structure',
    sales_acceptance_gates: ['explicit-commercial-intent', 'commercial-qualification-required', 'commercial-inputs-complete', 'named-commercial-owner-reviewed-and-accepted'],
    sales_acceptance_definition: 'sales-accepted requires explicit-commercial-intent, commercial-qualification-required, commercial-inputs-complete, and named-commercial-owner-reviewed-and-accepted',
    sales_commercial_intent_required: 'explicit cargo hub-motor RFQ, quote, price, MOQ, delivery, purchase, or order intent',
    sales_commercial_intent_status: 'confirmed-for-fixture-structure', sales_commercial_inputs_status: 'confirmed-for-fixture-structure',
    sales_acceptance_owner: owner, sales_acceptance_next_step: 'review the complete commercial packet and continue only after the named commercial owner records acceptance',
    sales_commercial_inputs: v16BuyInputs, qualification_reason_codes: v16BuyReasonCodes,
    role_handoff_contracts: [roleHandoff], secondary_buyer_roles: [], secondary_buyer_role_contracts: [],
    internal_link_targets: linkTargets, internal_link_buyer_task_contracts: linkContracts, internal_link_buyer_task_contracts_snapshot: linkContracts,
    product_decision_map: productMap, product_decision_map_snapshot: productMap,
    direct_answer_action: 'complete', direct_answer_object: 'the cargo hub-motor RFQ packet',
    direct_answer_required_inputs_or_evidence: v16BuyInputs,
    direct_answer_condition_or_boundary: 'only after a verified route is returned and requested quantity range, delivery destination, and required delivery window are complete; until then do not send or submit the packet',
    direct_answer_expected_output_or_route: 'a missing-commercial-input list or bounded commercial qualification and quotation route',
    direct_answer_evidence_boundary: 'the review does not prove price, availability, delivery acceptance, supplier award, order acceptance, or sales acceptance',
    direct_answer: openingInstruction,
    pain_trigger: 'when an Engineer must request a cargo hub-motor quote before the program purchasing window',
    surface_problem: 'the Engineer cannot request a comparable quotation because the commercial input evidence for requested quantity range, delivery destination, and required delivery window is missing',
    operational_friction: 'missing commercial inputs may force Engineering and Procurement to repeatedly rebuild and reconcile the RFQ packet before quotation review',
    business_consequence: 'repeated RFQ packet rebuilds may therefore delay the cargo e-bike purchasing schedule, supplier shortlist, and sample-order approval',
    desired_decision: 'do not submit the exact three-input RFQ packet until a verified collection route and endpoint-bound policy both pass; otherwise stop before requesting a quotation',
    pain_chain_contract: 'Engineer|must request a cargo hub-motor quote before the program purchasing window|commercial input evidence for requested quantity range, delivery destination, and required delivery window is missing|Engineering and Procurement repeatedly rebuild and reconcile the RFQ packet|repeated RFQ packet rebuilds may therefore delay the cargo e-bike purchasing schedule, supplier shortlist, and sample-order approval|do not submit the exact three-input RFQ packet until a verified collection route and endpoint-bound policy both pass; otherwise stop before requesting a quotation',
    visual_decision_assets: ['decision-table|submit cargo hub-motor RFQ packet|quantity destination and delivery-window evidence supports missing-input or quotation routing|search-evidence.md#fixture-artifact-status-versus-market-information-gain|RFQ packet decision table|Cargo hub-motor RFQ packet decision table|not-applicable-for-semantic-table|retain readable table cells on a 320px viewport|required'],
    semantic_emphasis_plan: ['decision|Do not submit the exact three-input RFQ packet until a verified collection route and endpoint-bound policy both pass; otherwise stop before requesting a quotation.|RFQ packet decision table'],
    article_decision_sequence_map: [
      'hook|State the exact three-input commercial packet and bounded quotation boundary before the first section.|opening direct answer',
      'diagnose|Connect missing quantity destination or delivery-window evidence to repeated RFQ rework.|buyer pain chain',
      'decide|Do not submit the exact three-input RFQ packet until a verified collection route and endpoint-bound policy both pass; otherwise stop before requesting a quotation.|RFQ packet decision table',
      'de-risk|Separate quotation review from price availability delivery acceptance supplier award order or sales acceptance.|product decision path and validation boundary',
      'act|Prepare the packet locally and request a verified Commercial Account route before any submission.|request the bounded quotation route',
    ],
    article_decision_sequence_verdict: 'pass',
    conversion_surface_map: [
      'primary-route-boundary-01|primary|receive missing commercial inputs or a bounded quotation route|request the bounded quotation route|commercial|not-applicable',
      'soft-product-navigation-01|soft|prepare and self-check the exact three-input RFQ packet locally|product decision path|content-navigation|not-applicable',
      'fallback-copyable-rfq-01|fallback|request a verified Commercial Account route through the buyer organization approved supplier-contact process|copyable fallback message|commercial|not-applicable',
    ],
    cta_measurement_map: [
      `primary-route-boundary-01|primary|buy-article-v1|buy-primary-commercial-v1|cta_buy_primary_start|cta_buy_primary_submit|cta_buy_primary_success|cta_buy_primary_failure|primary start without success or failure within 30 minutes|not-applicable|cta_buy_primary_sales_accepted|synthetic-analytics-spec|not-run-no-production-baseline|30-days-after-production-enable|${owner}|cta-measurement-evidence.md#cta-measurement-plan`,
      'soft-product-navigation-01|soft|buy-article-v1|buy-soft-navigation-v1|cta_buy_soft_start|cta_buy_soft_click|cta_buy_soft_success|cta_buy_soft_failure|soft start without navigation success or failure within 30 minutes|not-applicable|not-applicable|synthetic-analytics-spec|not-run-no-production-baseline|30-days-after-production-enable|Morgan Lee, Synthetic Product Content Lead|cta-measurement-evidence.md#cta-measurement-plan',
      `fallback-copyable-rfq-01|fallback|buy-article-v1|buy-fallback-rfq-v1|cta_buy_fallback_start|cta_buy_fallback_copy|cta_buy_fallback_success|cta_buy_fallback_failure|fallback start without copy success or failure within 30 minutes|not-applicable|not-applicable|synthetic-analytics-spec|not-run-no-production-baseline|30-days-after-production-enable|${owner}|cta-measurement-evidence.md#cta-measurement-plan`,
    ],
    conversion_surface_map_verdict: 'pass',
    cta_buyer_visible_capability_proofs: [`commercial-review-method|submit cargo hub-motor RFQ packet|review method returns missing inputs or a bounded quotation route without promising acceptance|search-evidence.md#reserved-targets-and-acceptance-contracts|${proofCopy}|required`],
    pain_trigger_snapshot: 'when an Engineer must request a cargo hub-motor quote before the program purchasing window',
    surface_problem_snapshot: 'the Engineer cannot request a comparable quotation because the commercial input evidence for requested quantity range, delivery destination, and required delivery window is missing',
    operational_friction_snapshot: 'missing commercial inputs may force Engineering and Procurement to repeatedly rebuild and reconcile the RFQ packet before quotation review',
    business_consequence_snapshot: 'repeated RFQ packet rebuilds may therefore delay the cargo e-bike purchasing schedule, supplier shortlist, and sample-order approval',
    desired_decision_snapshot: 'do not submit the exact three-input RFQ packet until a verified collection route and endpoint-bound policy both pass; otherwise stop before requesting a quotation',
    internal_link_targets_snapshot: linkTargets,
    cta_required_inputs_snapshot: v16BuyInputs,
    cta_buyer_visible_capability_proofs_snapshot: [`commercial-review-method|submit cargo hub-motor RFQ packet|review method returns missing inputs or a bounded quotation route without promising acceptance|search-evidence.md#reserved-targets-and-acceptance-contracts|${proofCopy}|required`],
    buyer_language_seeds: ['cargo hub motor RFQ quote', 'cargo hub motor MOQ delivery quote'],
    query_language_transformation_reason: 'Preserve the buyer RFQ, quote, MOQ, and delivery wording while normalizing it into one Buy-stage commercial packet task.',
    expected_content_type: 'product landing page with a bounded RFQ decision path',
    expected_content_type_snapshot: 'product landing page with a bounded RFQ decision path',
    content_family_matches: ['product-landing'], content_family_singleton_verdict: 'pass', body_content_family_implementation_verdict: 'pass',
  };
  const body = `${syntheticFictionalDisclosure}

${openingInstruction}

## Buyer pain chain

1. An Engineer owns the cargo hub-motor RFQ packet.
2. When that Engineer must request a cargo hub-motor quote before the program purchasing window, the packet needs one comparable commercial basis.
3. Because evidence for the requested quantity range, delivery destination, and required delivery window is missing, the Engineer cannot request a comparable quotation.
4. That evidence gap may force Engineering and Procurement to repeatedly rebuild and reconcile the RFQ packet before quotation review.
5. The repeated RFQ packet rebuilds may therefore delay the purchasing schedule, supplier shortlist, and sample-order approval.
6. Therefore, **do not submit the exact three-input RFQ packet until a verified collection route and endpoint-bound policy both pass; otherwise stop before requesting a quotation.**

## RFQ packet decision table

Cargo hub-motor RFQ packet decision table:

| RFQ packet status | Quantity, destination, and delivery-window evidence | Missing-input or quotation route |
|---|---|---|
| Requested quantity range, delivery destination, and required delivery window are complete | The packet supports bounded commercial review after route verification | Route to the commercial owner for missing inputs or quotation review |
| One or more required commercial inputs are missing | The quotation basis is incomplete | Return the missing-commercial-input list before quoting |
| The requested commercial scope is explicitly unsupported | The packet has a documented stop boundary | Stop the quotation route and record the unsupported scope |

## Product decision path

${productNavigationCopy}

${guideNavigationCopy}

These reserved content-navigation targets do not prove model fit, measured performance, price, availability, delivery capability, or route capability. The commercial candidate review uses the buyer-supplied requested quantity range, delivery destination, and required delivery window; target configuration, required commercial documentation, and an approved secure-file route may remain for follow-up. Stop only when the requested commercial scope is explicitly unsupported.

## Request the bounded quotation route

Trigger: This RFQ review applies only when the Engineer has the exact cargo hub-motor quantity range, delivery destination, and required delivery window.

Required inputs: The exact first-round commercial packet is:

| Required input | Accepted format | Concrete example |
|---|---|---|
| requested quantity range | range in units for minimum, target, and maximum quantity | 500-1200 units |
| delivery destination | country and postal-code format without a street address | United States, 90210 |
| required delivery window | ISO 8601 date range | 2026-10-01 to 2026-11-15 |

Expected output: ${proofCopy}

Validation boundary: This review does not prove price, availability, delivery acceptance, supplier award, order acceptance, or sales acceptance.

- Data purpose: ${dataPurpose}
- Retention period: ${retentionPeriod}
- Deletion path: ${deletionPath}
- Retention owner: ${retentionOwner}

${fallbackInstruction}

> ${fallbackMessage}`;
  return Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => {
    let output = content;
    for (const [field, value] of Object.entries(values)) output = replaceIfPresent(output, field, JSON.stringify(value));
    output = setField(output, 'first_round_expected_output', '"not-applicable"');
    output = setField(output, 'candidate_decision_required_gates', '["not-applicable"]');
    if (key === 'briefPath' || key === 'publishPath') output = transformDocumentBody(output, (documentBody) => {
      let narrative = replaceRequiredLiteral(documentBody, canonicalRouteAndPolicyFallbackFor(key), fallbackMessage, 'Buy control-record fallback message');
      assert.ok(narrative.includes('https://example.test/guides/cargo-ebike-sample-validation'), 'Buy control-record must contain the old technical content-navigation URL before projection');
      narrative = narrative.split('https://example.test/guides/cargo-ebike-sample-validation').join(commercialGuideUrl);
      return narrative;
    });
    if (key === 'draftPath') output = transformBody(output, () => `\n${body}\n`);
    output = syncBuilderPublishSearchProjection(output, key, title);
    return output;
  }]));
}

test('V16 complete Buy Brief Draft Review Publish package passes its independent commercial branch', (t) => {
  expectPass(makeFixture(t, completeBuyCommercialMutations()));
});

function mutateBuyControlRecordBody(recordKey, transform) {
  const mutations = completeBuyCommercialMutations();
  const base = mutations[recordKey];
  mutations[recordKey] = (content) => transformDocumentBody(base(content), transform);
  return mutations;
}

for (const [label, recordKey] of [['Brief', 'briefPath'], ['Publish', 'publishPath']]) {
  test(`V16 ${label} narrative blocks exposure of an unverified reserved CTA endpoint`, (t) => {
    const reserved = 'https://example.test/workflows/cargo-hub-motor-rfq-intake';
    const mutations = mutateBuyControlRecordBody(recordKey, (body) => `${body}\n\nReserved submission endpoint: ${reserved}\n`);
    expectBlockMatching(t, mutations, new RegExp(`narrative cannot expose an unverified reserved CTA endpoint: ${reserved.replace(/[.*+?^${}()|[\\]\\]/g, '\\$&')}`));
  });
}

for (const [label, variant] of [
  ['default HTTPS port', 'https://example.test:443/workflows/cargo-hub-motor-rfq-intake'],
  ['dot segment', 'https://example.test/workflows/./cargo-hub-motor-rfq-intake'],
  ['parent dot segment', 'https://example.test/workflows/staging/../cargo-hub-motor-rfq-intake'],
  ['unreserved percent encoding', 'https://example.test/%77orkflows/%63argo-hub-motor-rfq-intake'],
  ['trailing-dot host', 'https://example.test./workflows/cargo-hub-motor-rfq-intake'],
]) {
  test(`P1 unverified reserved CTA endpoint blocks ${label} equivalence variant`, (t) => {
    const canonical = 'https://example.test/workflows/cargo-hub-motor-rfq-intake';
    const mutations = mutateBuyControlRecordBody('briefPath', (body) => `${body}\n\nReserved submission endpoint: ${variant}\n`);
    expectBlockMatching(t, mutations, /narrative cannot expose an unverified reserved CTA endpoint/);
    assert.ok(canonical);
  });
}


for (const [label, recordKey] of [['Brief', 'briefPath'], ['Publish', 'publishPath']]) {
  test(`V16 ${label} narrative must retain the canonical copyable fallback exactly`, (t) => {
    const mutations = mutateBuyControlRecordBody(recordKey, (body) => replaceRequiredLiteral(
      body,
      'No verified primary or fallback route is available.',
      'No verified primary or alternate route is available.',
      `${label} control-record canonical fallback`,
    ));
    expectBlockMatching(t, mutations, /control-record narrative must include the exact cta_fallback_message_template/);
  });
}

test('V16 internal-link narrative blocks worksheet or conversion endpoints mixed into content navigation', (t) => {
  const mutations = completeBuyCommercialMutations();
  const base = mutations.briefPath;
  const worksheet = 'https://example.test/tools/cargo-hub-motor-rfq-worksheet';
  mutations.briefPath = (content) => transformMarkdownSection(
    base(content),
    '## 7. Internal-link task contracts',
    '## 8. Progressive CTA contract',
    (section) => `${section}\nWorksheet conversion endpoint: ${worksheet}\n`,
  );
  expectBlockMatching(t, mutations, new RegExp(`internal-link narrative URL must belong to internal_link_targets and must not mix worksheet or conversion endpoints: ${worksheet.replace(/[.*+?^${}()|[\\]\\]/g, '\\$&')}`));
});

test('V16 content-navigation and CTA submission endpoints cannot reuse the same target', (t) => {
  const productUrl = 'https://example.test/solutions/cargo-hub-motor-candidates';
  const sharedHandoff = `Engineer|Procurement|${productUrl}|retain engineering authority for the final configuration boundary without promising an order|complete and submit the cargo hub-motor RFQ packet for price, MOQ, delivery, and a bounded quotation route|Riley Brooks, Procurement Lead (synthetic)|search-evidence.md#reserved-targets-and-acceptance-contracts`;
  const mutations = overrideMutationFields(completeBuyCommercialMutations(), { role_handoff_contracts: [sharedHandoff] });
  expectBlockMatching(t, mutations, new RegExp(`narrative cannot expose an unverified reserved CTA endpoint: ${productUrl.replace(/[.*+?^${}()|[\\]\\]/g, '\\$&')}`));
});

test('V16 decision-table cannot drift into a five-input list asset', (t) => {
  const mutate = (content) => mutateJsonArrayField(content, 'visual_decision_assets', (rows) => rows.map((row) => row.replace(/^decision-table\|/, 'decision-list|')));
  expectBlockMatching(t, {
    briefPath: mutate,
    draftPath: mutate,
    reviewPath: mutate,
    publishPath: mutate,
  }, /visual_decision_assets asset type must use the closed enum/);
});

for (const legacyRole of ['delegation', 'route']) {
  test(`V16 semantic emphasis rejects legacy ${legacyRole} role vocabulary`, (t) => {
    const mutate = (content) => mutateJsonArrayField(content, 'semantic_emphasis_plan', (rows) => {
      const parts = rows[0].split('|');
      parts[0] = legacyRole;
      rows[0] = parts.join('|');
      return rows;
    });
    expectBlockMatching(t, { briefPath: mutate, draftPath: mutate }, /semantic_emphasis_plan entry 1 role must be condition, risk, evidence, no-fit, boundary, action, or decision/);
  });
}

test('V16 canonical template vocabulary stays aligned with validator enums and conditional intake defaults', () => {
  const briefTemplate = readFileSync(new URL('../TEMPLATES/article-brief.md', import.meta.url), 'utf8');
  const reviewTemplate = readFileSync(new URL('../TEMPLATES/article-quality-review.md', import.meta.url), 'utf8');
  assert.doesNotMatch(briefTemplate, /query evidence status.*synthetic-only.*(?:or )?missing/i);
  assert.match(briefTemplate, /`troubleshoot` \| `none` by default; `troubleshoot-support` only with a real support destination and accepted receiving task/);
  assert.match(briefTemplate, /`compare` \| `none` by default; `compare-handoff` only with dated `mixed-commercial` evidence, a real destination, named owner and accepted receiving task/);
  assert.match(reviewTemplate, /`missing` \/ `inferred` \/ `confirmed` \/ `confirmed-for-fixture-structure`/);
  assert.match(reviewTemplate, /`missing` \/ `inferred` \/ `confirmed` \/ `not-applicable`/);
  assert.doesNotMatch(reviewTemplate, /Artifact exists and is usable \| missing \/ synthetic-only \/ confirmed/);
  assert.doesNotMatch(reviewTemplate, /Market difference is evidenced \| missing \/ hypothesis \/ confirmed/);
});

test('V16 Buy blocks a commercial CTA that reuses a technical-only destination even when all records agree', (t) => {
  const technicalUrl = 'https://example.test/contact/engineering-readiness-review';
  const mutations = overrideMutationFields(completeBuyCommercialMutations(), { cta_destination: technicalUrl });
  const base = mutations.draftPath;
  mutations.draftPath = (content) => transformBody(base(content), (body) => body.replace(
    'No verified primary or fallback route is available in this example.',
    `[Request the cargo hub-motor commercial quotation route](${technicalUrl}). No verified fallback route is available in this synthetic fixture.`,
  ));
  expectBlockMatching(t, mutations, /commercial CTA destination must not use a technical-only or engineering-only route/);
});

test('V16 Buy separates buyer-side Procurement receiving owner from external commercial route owner', (t) => {
  const mutations = completeBuyCommercialMutations();
  const buyerOwner = 'Riley Brooks, Procurement Lead';
  const externalOwner = 'Morgan Lee, Commercial Account Owner';
  for (const key of Object.keys(mutations)) {
    const base = mutations[key];
    mutations[key] = (content) => base(content).replaceAll(buyerOwner, externalOwner);
  }
  expectBlockMatching(t, mutations, /commercial CTA must separate the buyer-side receiving owner from the external route owner/);
});

test('V16 collecting CTA blocks a fallback that exists only in frontmatter', (t) => {
  const mutations = completeBuyCommercialMutations();
  const base = mutations.draftPath;
  mutations.draftPath = (content) => transformBody(base(content), (body) => replaceRequiredLiteral(
    body,
    /^> No verified primary or fallback route is available\..+$/m,
    '> Prepare the commercial packet offline and ask the route owner for next steps.',
    'buyer-visible canonical fallback blockquote',
  ));
  expectBlockMatching(t, mutations, /must display the exact copyable fallback message instead of hiding it only in frontmatter/);
});

test('V16 Troubleshoot support blocks Validate and commercial lifecycle states', (t) => {
  const injected = [
    'needs-diagnostic-follow-up|missing-diagnostic-evidence|observed fault evidence is incomplete|Casey Morgan, Support Engineering Lead (synthetic)|request missing diagnostic evidence',
    'technical-qualified|technical-gates-satisfied|technical gates are asserted|Casey Morgan, Support Engineering Lead (synthetic)|continue technical qualification',
    'sales-accepted|commercial-gates-satisfied|commercial gates are asserted|Morgan Lee, Commercial Account Owner|continue commercial acceptance',
  ];
  expectBlockMatching(t, overrideMutationFields(completeTroubleshootNoIntakeMutations(), {
    stage_intake_contract: 'troubleshoot-support',
    cta_input_collection_applicability: 'applicable',
    qualification_reason_codes: injected,
  }), /troubleshoot-support qualification_reason_codes may contain only diagnostic follow-up or evidenced-stop states/);
});

test('V16 Compare none intake blocks residual first-round inputs', (t) => {
  expectBlockMatching(t, overrideMutationFields(completeCompareNoIntakeMutations(), {
    first_round_inquiry_inputs: ['target duty profile'],
  }, ['briefPath']), /stage_intake_contract=none requires empty first_round_inquiry_inputs/);
});

test('V16 Compare handoff blocks sales-accepted state', (t) => {
  const reasonCodes = ['sales-accepted|commercial-gates-satisfied|commercial gates are asserted|Morgan Lee, Commercial Account Owner|continue supplier acceptance'];
  expectBlockMatching(t, v14StageMutations({ stage: 'compare', intent: 'mixed-commercial', intake: 'compare-handoff', firstRound: v14CompareInputs, reasonCodes }), /compare-handoff qualification_reason_codes must not inherit technical qualification or sales acceptance states/);
});

test('V16 Buy blocks a missing commercial-qualification-required state', (t) => {
  expectBlockMatching(t, overrideMutationFields(completeBuyCommercialMutations(), {
    qualification_reason_codes: [v16BuyReasonCodes[1]],
  }), /buy-commercial qualification_reason_codes requires exact commercial state commercial-qualification-required/);
});

test('V16 Buy blocks a missing sales-accepted state', (t) => {
  expectBlockMatching(t, overrideMutationFields(completeBuyCommercialMutations(), {
    qualification_reason_codes: [v16BuyReasonCodes[0]],
  }), /buy-commercial qualification_reason_codes requires exact commercial state sales-accepted/);
});

test('V16 Buy blocks Validate technical-qualified lifecycle injection', (t) => {
  expectBlockMatching(t, overrideMutationFields(completeBuyCommercialMutations(), {
    qualification_reason_codes: [...v16BuyReasonCodes, 'technical-qualified|technical-gates-satisfied|technical gates are asserted|Casey Morgan, Support Engineering Lead (synthetic)|continue technical qualification'],
  }), /buy-commercial qualification_reason_codes must not inherit technical qualification states/);
});

test('V16 stage-specific input minima block undersized Validate Buy Troubleshoot and Compare packets', (t) => {
  expectBlockMatching(t, allRecords('first_round_inquiry_inputs', JSON.stringify(legalFirstRoundInputs.slice(0, 3))), /first_round_inquiry_inputs must contain at least 4 distinct concrete input|validate-technical.*4-6/);
  expectBlockMatching(t, overrideMutationFields(completeBuyCommercialMutations(), {
    first_round_inquiry_inputs: v16BuyInputs.slice(0, 2),
    required_inquiry_inputs: v16BuyInputs.slice(0, 2),
    cta_required_inputs: v16BuyInputs.slice(0, 2),
    cta_required_inputs_snapshot: v16BuyInputs.slice(0, 2),
    sales_commercial_inputs: v16BuyInputs.slice(0, 2),
    first_round_input_specifications: v16BuySpecifications.slice(0, 2),
    first_round_input_specifications_snapshot: v16BuySpecifications.slice(0, 2),
  }), /stage-appropriate 3-6|at least three distinct concrete inputs|requires at least 3 concrete inputs for buy-commercial/);
  expectBlockMatching(t, v14StageMutations({ stage: 'troubleshoot', intent: 'informational', intake: 'troubleshoot-support', firstRound: [] }), /requires at least 1 item|stage-appropriate 1-6/);
  expectBlockMatching(t, v14StageMutations({ stage: 'compare', intent: 'mixed-commercial', intake: 'compare-handoff', firstRound: [] }), /requires at least 1 item|stage-appropriate 1-6/);
});

test('V16 every stage-specific first-round packet blocks more than six inputs', (t) => {
  const seven = [...legalFirstRoundInputs, 'additional controller firmware boundary', 'additional packaging constraint'];
  expectBlockMatching(t, v14StageMutations({ stage: 'validate', intent: 'informational', intake: 'validate-technical', firstRound: seven, secondRound: legalSecondRoundInputs, technicalActive: true }), /first-round intake must remain at most six|at most 6 item/);
});

test('V16 Review and Publish qualification reason-code drift blocks canonical projection', (t) => {
  expectBlockMatching(t, overrideMutationFields(completeBuyCommercialMutations(), {
    qualification_reason_codes: [v16BuyReasonCodes[0]],
  }, ['reviewPath']), /qualification_reason_codes must (?:exactly )?match|canonical field qualification_reason_codes/);
  expectBlockMatching(t, overrideMutationFields(completeBuyCommercialMutations(), {
    qualification_reason_codes: [v16BuyReasonCodes[0]],
  }, ['publishPath']), /qualification_reason_codes must (?:exactly )?match|canonical field qualification_reason_codes/);
});

test('V16 Troubleshoot diagnose action cannot be replaced by unrelated imperative word salad', (t) => {
  expectBlockMatching(t, overrideMutationFields(completeTroubleshootNoIntakeMutations(), {
    direct_answer_action: 'applaud',
  }), /complete opening block must implement the direct-answer action slot|single bounded buyer action/);
});

test('V16 Buy buyer-visible CTA blocks automatic sales acceptance by submission', (t) => {
  const mutations = completeBuyCommercialMutations();
  const base = mutations.draftPath;
  mutations.draftPath = (content) => transformBody(base(content), (body) => body.replace(
    'Preparing the packet requests no commercial commitment and does not create a quote, order, supplier award, delivery promise, or sales acceptance.',
    'Submitting the packet automatically creates sales acceptance and order acceptance.',
  ));
  expectBlockMatching(t, mutations, /CTA must not claim that submission automatically creates a quote, order, supplier award, delivery promise, or sales acceptance/);
});

test('V14 Learn package rejects Validate-heavy lifecycle copy in the publishable body', (t) => {
  const mutations = notApplicableSyntheticMutations();
  const base = mutations.draftPath;
  mutations.draftPath = (content) => replaceRequiredLiteral(
    base(content),
    '<!-- PUBLISHABLE_BODY_END -->',
    'Technical qualification begins after the second round.\n\n<!-- PUBLISHABLE_BODY_END -->',
    'Learn-to-Validate lifecycle injection',
  );
  expectBlockMatching(t, mutations, /learn metadata cannot relabel body\/lifecycle copy from another stage/);
});

test('V10 not-applicable CTA cannot retain fabricated required inputs', (t) => {
  const mutations = notApplicableSyntheticMutations();
  mutations.briefPath = ((base) => (content) => replaceField(base(content), 'cta_required_inputs', JSON.stringify(legalFirstRoundInputs)))(mutations.briefPath);
  expectBlockMatching(t, mutations, /not-applicable input collection must not fabricate cta_required_inputs/);
});

test('V10 not-applicable CTA cannot retain omitted second-round inputs', (t) => {
  const mutations = notApplicableSyntheticMutations();
  mutations.briefPath = ((base) => (content) => replaceField(base(content), 'cta_progressive_profiling_omitted_inputs', JSON.stringify(legalSecondRoundInputs)))(mutations.briefPath);
  expectBlockMatching(t, mutations, /not-applicable input collection must not fabricate cta_progressive_profiling_omitted_inputs/);
});

test('V10 not-applicable CTA cannot retain progressive follow-up owner', (t) => {
  const mutations = notApplicableSyntheticMutations();
  mutations.briefPath = ((base) => (content) => replaceField(base(content), 'cta_progressive_profiling_followup_owner', '"Synthetic Technical Owner"'))(mutations.briefPath);
  expectBlockMatching(t, mutations, /not-applicable input collection requires cta_progressive_profiling_followup_owner=not-applicable/);
});

test('V10 not-applicable CTA cannot retain sales acceptance definition', (t) => {
  const mutations = notApplicableSyntheticMutations();
  mutations.briefPath = ((base) => (content) => replaceField(base(content), 'sales_acceptance_definition', '"sales-accepted after commercial review"'))(mutations.briefPath);
  expectBlockMatching(t, mutations, /not-applicable input collection requires sales_acceptance_definition=not-applicable/);
});

test('V10 not-applicable stage link cannot retain fabricated target roles', (t) => {
  const mutations = notApplicableSyntheticMutations();
  mutations.briefPath = ((base) => (content) => replaceField(base(content), 'stage_required_link_roles', '["educational"]'))(mutations.briefPath);
  expectBlockMatching(t, mutations, /not-applicable stage link must not fabricate stage_required_link_roles|must not declare/);
});

test('V10 not-applicable stage link cannot retain a confirmed product map status', (t) => {
  const mutations = notApplicableSyntheticMutations();
  mutations.briefPath = ((base) => (content) => replaceField(base(content), 'product_decision_map_status', '"confirmed"'))(mutations.briefPath);
  expectBlockMatching(t, mutations, /not-applicable stage link requires product_decision_map_status=not-applicable/);
});

test('V10 copyable fallback must reference the canonical prepared worksheet when it does not repeat the first-round exact set', (t) => {
  const mutations = legalSyntheticMutations({ briefPath: (content) => replaceField(content, 'cta_fallback_message_template', JSON.stringify('Request a bounded review through the verified route after preparing the packet locally. Second-round inputs follow after the first review.')) });
  expectBlockMatching(t, mutations, /copyable CTA fallback must contain the first-round exact set or reference the canonical prepared worksheet/);
});

test('V10 copyable fallback cannot pull a second-round input forward', (t) => {
  const mutations = legalSyntheticMutations({ briefPath: (content) => replaceField(content, 'cta_fallback_message_template', JSON.stringify(`${legalFallback} ${legalSecondRoundInputs[0]}`)) });
  expectBlockMatching(t, mutations, /copyable CTA fallback must not collect second-round inputs/);
});

test('V10 final CTA cannot collect second-round inputs', (t) => {
  const mutations = legalSyntheticMutations({ draftPath: (content) => transformBody(content, (body) => body.replace('## Request a bounded engineering-readiness review', `## Request a bounded engineering-readiness review\n\n${legalSecondRoundInputs[0]}`)) });
  expectBlockMatching(t, mutations, /final CTA must not collect second-round inputs/, setupLegalSyntheticEvidence);
});

test('V10 first-round checklist cannot collect second-round inputs', (t) => {
  const mutations = legalSyntheticMutations({ draftPath: (content) => transformBody(content, (body) => body.replace('## Use five decision blocks before the first review', `## Use five decision blocks before the first review\n\n${legalSecondRoundInputs[0]}`)) });
  expectBlockMatching(t, mutations, /checklist must not collect second-round inputs/, setupLegalSyntheticEvidence);
});

test('V10 soft CTA cannot collect second-round inputs', (t) => {
  const mutations = legalSyntheticMutations({ draftPath: (content) => transformBody(content, (body) => replaceRequiredLiteral(body, '## Assemble the readiness worksheet locally', `## Assemble the readiness worksheet locally\n\n${legalSecondRoundInputs[0]}`, 'soft CTA second-round insertion anchor')) });
  expectBlockMatching(t, mutations, /soft CTA must not collect second-round inputs/, setupLegalSyntheticEvidence);
});

test('V10 technical-owner prose requires the second-round exact set', (t) => {
  const mutations = legalSyntheticMutations({ draftPath: (content) => transformBody(content, (body) => {
    const section = body.match(/## What Applications Engineering requests in round two\n[\s\S]*?(?=\n## Hand the candidate to the next validation task)/);
    assert.ok(section, 'technical-owner round-two section must be locatable');
    return replaceRequiredLiteral(
      body,
      section[0],
      '## What Applications Engineering requests in round two\n\nApplications Engineering will collect generic details later.',
      'technical-owner round-two exact-set attack',
    );
  }) });
  expectBlockMatching(t, mutations, /technical-owner round-two prose must visibly contain the second-round exact set/, setupLegalSyntheticEvidence);
});

test('V10 technical-owner round two cannot request the exact same first-round value again', (t) => {
  const repeated = legalFirstRoundInputs[0];
  const relationships = JSON.stringify([`${repeated}|refines|${repeated}|incorrectly requests the same submitted value again`]);
  const mutations = Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => {
    let output = replaceField(content, 'second_round_inquiry_inputs', JSON.stringify([repeated]));
    if (fieldPattern('second_round_input_relationships').test(output)) output = replaceField(output, 'second_round_input_relationships', relationships);
    return output;
  }]));
  expectBlockMatching(t, mutations, /second-round intake must not request the same value again/, setupLegalSyntheticEvidence);
});

test('V10 canonical inventory zero-result ref is the real section-5 fragment', () => {
  const content = normalizeFrontMatterSequences(readFileSync(new URL('b2b-seo-article-brief.md', exampleRoot), 'utf8'));
  assert.match(content, /inventory_zero_result_evidence_refs: \["search-evidence\.md#5-synthetic-inventory-zero-result-evidence"\]/);
});

test('V10 zero-result fragment requires a valid checked_at date', (t) => {
  expectBlockMatching(t, {}, /zero-result evidence .* checked_at must be an ISO date or timestamp/, (dir) => {
    const p = join(dir, 'search-evidence.md');
    const content = readFileSync(p, 'utf8');
    writeFileSync(p, transformMarkdownSection(content, '## 5. Synthetic inventory zero-result evidence', '## 6. Independent gate records', (section) => section.replace("checked_at: '2026-08-01'", "checked_at: 'not-a-date'")));
  });
});

test('V10 zero-result fragment rejects a future checked_at date', (t) => {
  expectBlockMatching(t, {}, /zero-result evidence .* checked_at must not be in the future/, (dir) => {
    const p = join(dir, 'search-evidence.md');
    const content = readFileSync(p, 'utf8');
    writeFileSync(p, transformMarkdownSection(content, '## 5. Synthetic inventory zero-result evidence', '## 6. Independent gate records', (section) => section.replace("checked_at: '2026-08-01'", "checked_at: '2999-01-01'")));
  });
});

test('V10 zero-result retrieval dimensions require taxonomy coverage', (t) => {
  expectBlockMatching(t, {}, /retrieval_dimensions requires taxonomy/, (dir) => {
    const p = join(dir, 'search-evidence.md');
    writeFileSync(p, readFileSync(p, 'utf8').replace('    - "category/tag/taxonomy labels"\n', ''));
  });
});

test('V10 production query evidence fragment must resolve', (t) => {
  const mutations = allRecords('evidence_scope', '"production"');
  mutations.briefPath = (content) => {
    let out = replaceField(content, 'evidence_scope', '"production"');
    out = replaceField(out, 'query_evidence_status', '"confirmed"');
    out = replaceField(out, 'query_evidence_refs', '["search-evidence.md#missing-query-fragment"]');
    return out;
  };
  expectBlockMatching(t, mutations, /query evidence .* must resolve to a valid non-empty fragment/);
});

test('V10 production query evidence confirmed status requires non-empty refs', (t) => {
  const mutations = allRecords('evidence_scope', '"production"');
  mutations.briefPath = (content) => {
    let out = replaceField(content, 'evidence_scope', '"production"');
    out = replaceField(out, 'query_evidence_status', '"confirmed"');
    out = replaceField(out, 'query_evidence_refs', '[]');
    return out;
  };
  expectBlockMatching(t, mutations, /production requires non-empty query_evidence_refs/);
});

test('V10 production query evidence requires a valid datetime', (t) => {
  const mutations = allRecords('evidence_scope', '"production"');
  mutations.briefPath = (content) => {
    let out = replaceField(content, 'evidence_scope', '"production"');
    out = replaceField(out, 'query_evidence_status', '"confirmed"');
    out = replaceField(out, 'query_evidence_refs', '["production-evidence.md#query-evidence"]');
    return out;
  };
  expectBlockMatching(t, mutations, /field observed_at\/date must be an ISO date or timestamp|checked_at.*valid.*date/i, (dir) => {
    writeFileSync(join(dir, 'production-evidence.md'), `---
title: Query evidence datetime attack
record_type: evidence-record
evidence_scope: production
source: independent query evidence capture
observed_at: not-a-date
digest: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
evidence_kind: query-evidence
---
# Production evidence

## Query evidence

checked_at: not-a-date
device: desktop
market: United States
language: en
query: cargo hub motor engineering readiness checklist
stage: validate
commercial_commitment: none
check_id: query-evidence
target_url: https://example.test/posts/cargo-ebike-hub-motor-selection-checklist
target_role: query-evidence
target_task: cargo hub motor engineering readiness checklist | United States | query-evidence
method: independent desktop query capture
observed_result: query intent and stage were reviewed against the bounded target page
artifact_digest: sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
producer: independent fixture producer
independent_reviewer: independent fixture reviewer
`);
  });
});

test('V10 production query evidence rejects a future datetime', (t) => {
  const mutations = allRecords('evidence_scope', '"production"');
  mutations.briefPath = (content) => {
    let out = replaceField(content, 'evidence_scope', '"production"');
    out = replaceField(out, 'query_evidence_status', '"confirmed"');
    out = replaceField(out, 'query_evidence_refs', '["production-evidence.md#query-evidence"]');
    return out;
  };
  expectBlockMatching(t, mutations, /field observed_at\/date must not be in the future|field observed_at\/date must not be later than reviewed_at|checked_at.*future/i, (dir) => {
    writeFileSync(join(dir, 'production-evidence.md'), `---
title: Query evidence future-datetime attack
record_type: evidence-record
evidence_scope: production
source: independent query evidence capture
observed_at: 2999-01-01T00:00:00Z
digest: sha256:eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee
evidence_kind: query-evidence
---
# Production evidence

## Query evidence

checked_at: 2999-01-01T00:00:00Z
device: desktop
market: United States
language: en
query: cargo hub motor engineering readiness checklist
stage: validate
commercial_commitment: none
check_id: query-evidence
target_url: https://example.test/posts/cargo-ebike-hub-motor-selection-checklist
target_role: query-evidence
target_task: cargo hub motor engineering readiness checklist | United States | query-evidence
method: independent desktop query capture
observed_result: query intent and stage were reviewed against the bounded target page
artifact_digest: sha256:ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff
producer: independent fixture producer
independent_reviewer: independent fixture reviewer
`);
  });
});

for (const [field, value, pattern] of [
  ['information_gain_artifact_refs', '[]', /production information gain requires non-empty artifact and market refs/],
  ['information_gain_market_refs', '[]', /production information gain requires non-empty artifact and market refs/],
  ['information_gain_artifact_refs', '["production-information-gain.md#missing-artifact"]', /artifact information-gain ref .* must resolve to a valid non-empty fragment/],
  ['information_gain_market_refs', '["production-information-gain.md#missing-market"]', /market information-gain ref .* must resolve to a valid non-empty fragment/],
]) {
  test(`V10 production ${field} rejects ${value}`, (t) => {
    const mutations = allRecords('evidence_scope', '"production"');
    mutations.briefPath = (content) => {
      let out = replaceField(content, 'evidence_scope', '"production"');
      out = replaceField(out, 'information_gain_artifact_refs', '["production-information-gain.md#artifact"]');
      out = replaceField(out, 'information_gain_market_refs', '["production-information-gain.md#market"]');
      return replaceField(out, field, value);
    };
    expectBlockMatching(t, mutations, pattern, (dir) => setupProductionInformationGainEvidence(dir));
  });
}

for (const requirement of ['date', 'market', 'language', 'query set', 'snapshot/corpus', 'difference']) {
  test(`V10 production market information-gain evidence requires ${requirement}`, (t) => {
    const mutations = allRecords('evidence_scope', '"production"');
    mutations.briefPath = (content) => {
      let out = replaceField(content, 'evidence_scope', '"production"');
      out = replaceField(out, 'information_gain_artifact_refs', '["production-information-gain.md#artifact"]');
      out = replaceField(out, 'information_gain_market_refs', '["production-information-gain.md#market"]');
      return out;
    };
    expectBlockMatching(t, mutations, new RegExp(`market information-gain ref .* requires ${requirement.replace('/', '\\/')}`), (dir) => setupProductionInformationGainEvidence(dir, { omit: requirement }));
  });
}

for (const checkedAt of ['not-a-date', '2999-01-01T00:00:00Z']) {
  test(`V10 production market information-gain evidence rejects date ${checkedAt}`, (t) => {
    const mutations = allRecords('evidence_scope', '"production"');
    mutations.briefPath = (content) => {
      let out = replaceField(content, 'evidence_scope', '"production"');
      out = replaceField(out, 'information_gain_artifact_refs', '["production-information-gain.md#artifact"]');
      out = replaceField(out, 'information_gain_market_refs', '["production-information-gain.md#market"]');
      return out;
    };
    expectBlockMatching(t, mutations, /market information-gain ref .* date must (?:be an ISO date or timestamp|not be in the future)/, (dir) => setupProductionInformationGainEvidence(dir, { checkedAt }));
  });
}

test('V10 production market information-gain evidence requires reviewer', (t) => {
  const mutations = allRecords('evidence_scope', '"production"');
  mutations.briefPath = (content) => {
    let out = replaceField(content, 'evidence_scope', '"production"');
    out = replaceField(out, 'information_gain_artifact_refs', '["production-evidence.md#artifact"]');
    out = replaceField(out, 'information_gain_market_refs', '["production-evidence.md#market"]');
    return out;
  };
  expectBlockMatching(t, mutations, /market information-gain ref .* requires reviewer/, (dir) => {
    writeFileSync(join(dir, 'production-evidence.md'), `---
title: Production information gain reviewer attack
record_type: evidence-record
evidence_scope: production
source: independent market corpus review
observed_at: 2026-08-01T00:00:00Z
digest: sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd
evidence_kind: information-gain
---
# Production evidence

## Artifact

Decision artifact: candidate-or-stop worksheet.

## Market

checked_at: 2026-08-01T00:00:00Z
market: United States
language: en
query_set: cargo motor selection
snapshot: local dated corpus
difference: compared with current owner pages
`);
  });
});

// V11 adversarial regressions. These preserve the V10 suite and pin the newly closed bypasses.
test('V11 zero-width plus Cyrillic confusable cannot bypass commercial query classification', (t) => {
  const attack = 'cargo e-bike hub motor l\u200Bе\u200Bad_time';
  expectBlockMatching(t, allRecords('primary_query', JSON.stringify(attack)), /mixed-script|transactional query modifiers cannot masquerade/);
});

test('V11 zero-width plus Cyrillic confusable cannot bypass unsupported outcome claims', (t) => {
  expectBlockMatching(t, {
    draftPath: (content) => transformBody(content, (body) => `${body}\n\nThis workflow will double qualified inqui\u200Bг\u200Bies.`),
  }, /mixed-script|unsupported ranking, inquiry, or conversion outcome claim/);
});

test('V11 visible CTA generic anchor rejects Markdown emphasis camouflage', (t) => {
  expectBlockMatching(t, syntheticPrimaryEndpointMutations({ anchor: 'Open **page**' }), /CTA link anchor must be action\/output specific, not generic/, setupLegalSyntheticEvidence);
});

test('V11 commercial classifier routes lead_time away from Quality and technical-only owners', (t) => {
  const mutations = Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => mutateJsonArrayField(content, 'role_handoff_contracts', (rows) => rows.map((row) => row.replace(
    'define project-specific bench and vehicle acceptance evidence after technical qualification',
    'approve cargo program lead_time and quality acceptance evidence after technical qualification',
  )))]));
  expectBlockMatching(t, mutations, /Quality cannot receive|commercial receiving_task must route to Procurement/);
});

test('V11 technical and sales exact gates reject false negative status camouflage', (t) => {
  const falseTechnical = 'first-round-complete=false, second-round-complete=false, no-evidenced-no-fit=false, named-technical-owner-accepted=false';
  const mutations = Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => mutateJsonArrayField(content, 'qualification_reason_codes', (rows) => rows.map((row) => row.startsWith('technical-qualified|') ? row.replace(row.split('|')[2], falseTechnical) : row))]));
  expectBlockMatching(t, mutations, /exact gates must be affirmative|negative or missing states fail closed/);
});

test('V11 first-round-complete rejects absent unavailable or omitted input evidence', (t) => {
  const mutations = Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => mutateJsonArrayField(content, 'qualification_reason_codes', (rows) => rows.map((row) => row.startsWith('first-round-complete|') ? row.replace(row.split('|')[2], 'all five canonical first-round inputs are absent and not received') : row))]));
  expectBlockMatching(t, mutations, /first-round-complete evidence must affirm|negative or missing states fail closed/);
});

test('V11 zero-result fragment rejects English number-word overlap contradictions', (t) => {
  expectBlockMatching(t, {}, /English-number overlap\/conflict\/duplicate-owner conclusion/, (dir) => {
    const path = join(dir, 'search-evidence.md');
    const content = readFileSync(path, 'utf8').replace('## 6. Independent gate records', 'The bounded search found overlap across twelve owner pages.\n\n## 6. Independent gate records');
    writeFileSync(path, content);
  });
});

test('V11 outcome status uses closed exact lowercase enums', (t) => {
  const mutations = {
    reviewPath: (content) => replaceField(content, 'actual_ranking_status', '"Observed Improvement"'),
    publishPath: (content) => replaceField(content, 'actual_ranking_status', '"Observed Improvement"'),
  };
  expectBlockMatching(t, mutations, /actual_ranking_status must be exact lowercase/);
});

test('V11 observed outcome requires dated window metric result refs and named reviewer', (t) => {
  const mutations = {
    reviewPath: (content) => replaceField(content, 'actual_inquiry_status', '"observed-improvement"'),
    publishPath: (content) => replaceField(content, 'actual_inquiry_status', '"observed-improvement"'),
  };
  expectBlockMatching(t, mutations, /observation_window must contain a dated start and end|requires non-empty actual_outcome_evidence_refs|must be concrete/);
});

test('V11 owner identity rejects a pure role or department', (t) => {
  expectBlockMatching(t, allRecords('technical_qualification_owner', '"Engineering"'), /stable owner ID or person name plus role/);
});

test('V11 qualification reason owner must exactly equal canonical owner identity', (t) => {
  const mutations = Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => mutateJsonArrayField(content, 'qualification_reason_codes', (rows) => rows.map((row) => row.startsWith('technical-qualified|') ? row.replace('Avery Chen, Applications Engineering Lead', 'Avery Chen, Technical Lead') : row))]));
  expectBlockMatching(t, mutations, /owner must exactly equal canonical technical_qualification_owner/);
});

function setupV11QueryRows(dir, { omitLast = false, extra = false, duplicate = false, prefixRows = [], additionalRows = [], header = '', duplicateHeader = false } = {}) {
  const queries = [
    'cargo hub motor engineering readiness checklist',
    'cargo e-bike hub motor engineering readiness checklist',
    'cargo hub motor engineering review inputs',
    '20 inch cargo hub motor engineering readiness inputs',
  ];
  if (omitLast) queries.pop();
  if (extra) queries.push('extra unrelated query');
  if (duplicate) queries.push(queries[0]);
  const ref = 'v11-query-evidence.md#exact-query-rows';
  const canonicalHeader = 'query|action|object|observable-output|stage|commercial-commitment|market|language|device|checked_at|evidence_ref';
  const rows = [...queries.map((query) => `${query}|assemble|cargo e-bike hub-motor engineering-readiness packet|packet completeness, missing-evidence list, and next review step|validate|none|United States|en|desktop|2026-08-01|${ref}`), ...additionalRows].join('\n');
  writeFileSync(join(dir, 'v11-query-evidence.md'), `---
title: V11 query evidence
record_type: evidence-record
evidence_scope: production
observed_at: 2026-08-01T00:00:00Z
evidence_kind: query-evidence
---
# V11 query evidence

## Exact query rows

${prefixRows.join('\n')}
${header || canonicalHeader}
${duplicateHeader ? canonicalHeader : ''}
${rows}
`);
}

function v11ProductionQueryMutations() {
  const mutations = allRecords('evidence_scope', '"production"');
  mutations.briefPath = (content) => {
    let output = replaceField(content, 'evidence_scope', '"production"');
    output = replaceField(output, 'query_evidence_status', '"confirmed"');
    return replaceField(output, 'query_evidence_refs', '["v11-query-evidence.md#exact-query-rows"]');
  };
  return mutations;
}

test('V11 production query evidence requires exact primary-plus-variant row set', (t) => {
  expectBlockMatching(t, v11ProductionQueryMutations(), /query evidence row query set must exactly equal/, (dir) => setupV11QueryRows(dir, { omitLast: true }));
});

test('V11 production exact 11-slot query rows are accepted by the query-axis validator', (t) => {
  const result = validateArticlePackage(makeFixture(t, v11ProductionQueryMutations(), (dir) => setupV11QueryRows(dir)));
  assert.equal(result.problems.some((problem) => /production query (?:evidence row query set|row .* must exactly|evidence ref .*11-slot|row .* evidence_ref)/.test(problem)), false, result.problems.join('\n'));
});

for (const [field, value, pattern] of [
  ['stage', '"consider"', /stage must use exact lowercase canonical enum/],
  ['intent_class', '"commercial_research"', /intent_class must use exact lowercase canonical enum/],
  ['commercial_commitment', '"technical-review"', /commercial_commitment must use exact lowercase canonical enum/],
  ['cta_interaction_type', '"form"', /cta_interaction_type must use exact lowercase canonical enum/],
]) {
  test(`V11 canonical vocabulary rejects legacy alias ${field}=${value}`, (t) => {
    expectBlockMatching(t, allRecords(field, value), pattern);
  });
}

test('V11 role handoff rejects fabricated rows when links remain same-role and no delegation exists', (t) => {
  const mutations = Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => {
    let output = replaceField(content, 'cta_from_role', '"not-applicable"');
    output = replaceField(output, 'cta_to_role', '"not-applicable"');
    output = replaceField(output, 'cta_receiving_task', '"not-applicable"');
    if (key === 'briefPath' || key === 'draftPath') output = mutateJsonArrayField(output, 'internal_link_buyer_task_contracts', (rows) => rows.map((row) => {
      const parts = row.split('|');
      parts[4] = 'Engineer';
      return parts.join('|');
    }));
    return output;
  }]));
  expectBlockMatching(t, mutations, /role_handoff_contracts must be empty when all targets remain same-role/);
});

test('V11 preserves direct-answer semantic parity against visible word salad', (t) => {
  const mutations = {
    draftPath: (content) => replaceField(content, 'direct_answer', '"validate banana lantern wallpaper and return a bounded random output"'),
  };
  expectBlockMatching(t, mutations, /direct[_ ]answer|slot parity|visible/i);
});

// V12 adversarial regressions. These tests pin the current validator implementation
// and the synchronized canonical Templates/FluxPedal records.
for (const [label, ignorable] of [
  ['U+FFF9 interlinear annotation anchor', '\uFFF9'],
  ['supplementary-plane tag character', '\u{E0001}'],
]) {
  test(`V12 ${label} cannot bypass mixed-script commercial, outcome, or generic CTA checks`, (t) => {
    expectBlockMatching(t, allRecords('primary_query', JSON.stringify(`cargo e-bike hub motor l${ignorable}е${ignorable}ad_time`)), /mixed-script|transactional query modifiers cannot masquerade/);
    expectBlockMatching(t, {
      draftPath: (content) => transformBody(content, (body) => `${body}\n\nThis workflow will double qualified inqui${ignorable}г${ignorable}ies.`),
    }, /mixed-script|unsupported ranking, inquiry, or conversion outcome claim/);
    expectBlockMatching(t, syntheticPrimaryEndpointMutations({ anchor: `Open${ignorable} page` }), /CTA link anchor must be action\/output specific, not generic/, setupLegalSyntheticEvidence);
  });
}

test('V12 first-round-complete rejects negated submission followed by a complete claim', (t) => {
  const mutations = Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => mutateJsonArrayField(content, 'qualification_reason_codes', (rows) => rows.map((row) => row.startsWith('first-round-complete|') ? row.replace(row.split('|')[2], 'all five canonical first-round inputs have not been submitted but are complete') : row))]));
  expectBlockMatching(t, mutations, /first-round-complete evidence must affirm|negative or missing states fail closed/);
});

test('V12 technical-qualified rejects self-declared unsubstantiated exact gate names', (t) => {
  const attack = 'first-round-complete, second-round-complete, no-evidenced-no-fit, and named-technical-owner-accepted are all self-declared but not independently substantiated';
  const mutations = Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => mutateJsonArrayField(content, 'qualification_reason_codes', (rows) => rows.map((row) => row.startsWith('technical-qualified|') ? row.replace(row.split('|')[2], attack) : row))]));
  expectBlockMatching(t, mutations, /exact affirmative canonical gate definition|negative or missing states fail closed/);
});

test('V12 legacy internal-link role diagnosis is rejected while diagnostic remains canonical', (t) => {
  expectBlockMatching(t, {
    briefPath: (content) => mutateJsonArrayField(content, 'internal_link_targets', (rows) => rows.map((row, index) => index === 0 ? row.replace(/^solution\|/, 'diagnosis|') : row)),
  }, /internal link role must be one of|internal-link role/);
});

function v12SetAllFields(fields) {
  return Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => Object.entries(fields)
    .reduce((output, [field, value]) => replaceField(output, field, value), content)]));
}

function v12RemoveAllFields(fields) {
  return Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => fields
    .reduce((output, field) => removeField(output, field), content)]));
}

const v12CtaRoleFields = {
  cta_from_role: '"Engineer"',
  cta_to_role: '"Applications Engineering"',
  cta_receiving_task: '"return packet completeness, a missing-evidence list, and the next review step; do not return candidate-or-stop before the complete second-round package is reviewed"',
  cta_receiving_owner: '"Avery Chen, Applications Engineering Lead"',
};

test('V12 human-handoff CTA cannot pass after deleting every role handoff contract', (t) => {
  const mutations = v12SetAllFields(v12CtaRoleFields);
  for (const key of Object.keys(mutations)) {
    const prior = mutations[key];
    mutations[key] = (content) => replaceField(prior(content), 'role_handoff_contracts', '[]');
  }
  expectBlockMatching(t, mutations, /must match exactly one role_handoff_contracts row|requires role_handoff_contracts/);
});

test('V12 CTA role parity positive control matches the canonical handoff row', (t) => {
  const result = validateArticlePackage(makeFixture(t, v12SetAllFields(v12CtaRoleFields)));
  assert.equal(result.problems.some((problem) => /CTA must match exactly one role_handoff_contracts row|requires a concrete cta_|distinct cta_from_role/.test(problem)), false, result.problems.join('\n'));
});

test('V12 deleting all CTA role fields from all four records still fails closed', (t) => {
  expectBlockMatching(t, v12RemoveAllFields(['cta_from_role', 'cta_to_role', 'cta_receiving_task', 'cta_receiving_owner']), /field cta_from_role is required|field cta_to_role is required|field cta_receiving_task is required|field cta_receiving_owner is required|V12 CTA role schema requires/);
});

const v12SecondaryBuyerFields = {
  secondary_buyer_role_contracts: '["Quality|search-evidence.md#reserved-targets-and-acceptance-contracts|Quality needs project-specific validation evidence and acceptance thresholds|The article defines the bounded next bench and vehicle validation evidence task"]',
};

test('V12 secondary buyer role contracts reject a missing Quality contract', (t) => {
  expectBlockMatching(t, v12SetAllFields({ secondary_buyer_role_contracts: '[]' }), /secondary_buyer_role_contracts is missing secondary role Quality/);
});

test('V12 secondary buyer role contract positive control reaches the active validation flow', (t) => {
  const result = validateArticlePackage(makeFixture(t, v12SetAllFields(v12SecondaryBuyerFields)));
  assert.equal(result.problems.some((problem) => /secondary_buyer_role_contracts (?:is missing|contains unexpected|must contain|entry must use|must contain role-specific)/.test(problem)), false, result.problems.join('\n'));
});

test('V12 deleting secondary buyer role contracts from all four records still fails closed', (t) => {
  expectBlockMatching(t, v12RemoveAllFields(['secondary_buyer_role_contracts']), /field secondary_buyer_role_contracts is required|V12 secondary buyer schema requires/);
});

test('V12 retired buyer_role_matrix alias fails closed', (t) => {
  expectBlockMatching(t, {
    briefPath: (content) => insertFields(content, { buyer_role_matrix: '["Quality|objection|answer|N/A|reason"]' }),
  }, /deprecated field buyer_role_matrix|unknown top-level field buyer_role_matrix/);
});

function setupV12SerpEvidence(dir, {
  querySet = [
    'cargo hub motor engineering readiness checklist',
    'cargo e-bike hub motor engineering readiness checklist',
    'cargo hub motor engineering review inputs',
    '20 inch cargo hub motor engineering readiness inputs',
  ],
  market = 'United States', language = 'en', device = 'desktop', checkedAt = '2026-08-01', resultTypes = [
    'checklist', 'checklist', 'checklist', 'checklist', 'checklist', 'checklist', 'checklist',
    'guide', 'guide', 'guide',
  ],
  primaryQuery = 'cargo hub motor engineering readiness checklist', primarySampleSize = 10,
  primaryDominantType = 'checklist', primaryDominantCount = 7, primaryDominanceThreshold = 0.60,
  supportingDominantTypes = [],
} = {}) {
  setupV11QueryRows(dir);
  const supportingTypes = querySet.slice(1).map((_, index) => supportingDominantTypes[index] || 'checklist');
  const supportingResultTypes = supportingTypes.map((dominantType) => {
    const alternateType = dominantType === 'checklist' ? 'guide' : 'checklist';
    return [dominantType, dominantType, dominantType, alternateType, alternateType];
  });
  const supportingRows = querySet.slice(1).map((query, index) => `${query}|5|${supportingTypes[index]}|3|0.60|pass|v12-serp-evidence.md#supporting-query-${index + 1}`);
  const supportingFragments = querySet.slice(1).map((query, index) => `## Supporting query ${index + 1}

query: ${query}
market: ${market}
language: ${language}
device: ${device}
checked_at: ${checkedAt}
result_types: ${JSON.stringify(supportingResultTypes[index])}
sample_size: 5
dominant_result_type: ${supportingTypes[index]}
dominant_result_count: 3
dominance_threshold: 0.60
dominance_verdict: pass`).join('\n\n');
  writeFileSync(join(dir, 'v12-serp-evidence.md'), `---
title: V12 SERP evidence
record_type: evidence-record
evidence_scope: production
source: independent bounded SERP format capture
observed_at: 2026-08-01T00:00:00Z
digest: sha256:1212121212121212121212121212121212121212121212121212121212121212
evidence_kind: serp-format
---
# V12 SERP evidence

## Exact SERP format

query_set: ${JSON.stringify(querySet)}
market: ${market}
language: ${language}
device: ${device}
checked_at: ${checkedAt}
result_types: ${JSON.stringify(resultTypes)}
primary_query: ${primaryQuery}
primary_query_sample_size: ${primarySampleSize}
primary_query_result_type_counts: ${JSON.stringify([...new Map(resultTypes.map((type) => [type, resultTypes.filter((item) => item === type).length])).entries()].map(([type, count]) => `${type}|${count}`))}
primary_query_dominant_result_type: ${primaryDominantType}
primary_query_dominant_result_count: ${primaryDominantCount}
primary_query_dominance_threshold: ${primaryDominanceThreshold.toFixed(2)}
primary_query_dominance_verdict: pass
supporting_query_result_type_rows: ${JSON.stringify(supportingRows)}

${supportingFragments}
`);
}

function v12ProductionSerpMutations({
  primaryQuery = 'cargo hub motor engineering readiness checklist',
  primarySampleSize = '10',
  primaryDominantType = 'checklist',
  primaryDominantCount = '7',
  primaryDominanceThreshold = '0.60',
  resultTypeCounts = ['checklist|7', 'guide|3'],
  supportingRows = [
    'cargo e-bike hub motor engineering readiness checklist|5|checklist|3|0.60|pass|v12-serp-evidence.md#supporting-query-1',
    'cargo hub motor engineering review inputs|5|checklist|3|0.60|pass|v12-serp-evidence.md#supporting-query-2',
    '20 inch cargo hub motor engineering readiness inputs|5|checklist|3|0.60|pass|v12-serp-evidence.md#supporting-query-3',
  ],
} = {}) {
  const mutations = v11ProductionQueryMutations();
  for (const key of Object.keys(fixtureNames)) {
    const prior = mutations[key] || ((content) => content);
    mutations[key] = (content) => {
      let output = prior(content);
      output = replaceField(output, 'evidence_scope', '"production"');
      output = replaceField(output, 'serp_format_evidence_status', '"confirmed"');
      output = replaceField(output, 'serp_format_evidence_refs', '["v12-serp-evidence.md#exact-serp-format"]');
      output = replaceField(output, 'serp_primary_query', JSON.stringify(primaryQuery));
      output = replaceField(output, 'serp_primary_query_sample_size', JSON.stringify(primarySampleSize));
      output = replaceField(output, 'serp_primary_query_dominant_result_type', JSON.stringify(primaryDominantType));
      output = replaceField(output, 'serp_primary_query_dominant_result_count', JSON.stringify(primaryDominantCount));
      output = replaceField(output, 'serp_primary_query_dominance_threshold', JSON.stringify(primaryDominanceThreshold));
      output = replaceField(output, 'serp_primary_query_dominance_verdict', '"pass"');
      output = replaceField(output, 'serp_primary_query_result_type_counts', JSON.stringify(resultTypeCounts));
      output = replaceField(output, 'serp_supporting_query_result_type_rows', JSON.stringify(supportingRows));
      return output;
    };
  }
  return mutations;
}

for (const size of [3, 4]) {
  test(`P1 primary SERP sample size ${size} remains below the production minimum`, (t) => {
    const resultTypes = Array.from({ length: size }, (_, index) => index < Math.floor(size / 2) + 1 ? 'checklist' : 'guide');
    const dominantCount = resultTypes.filter((value) => value === 'checklist').length;
    expectBlockMatching(
      t,
      v12ProductionSerpMutations({ primarySampleSize: String(size), primaryDominantCount: String(dominantCount), resultTypeCounts: [`checklist|${dominantCount}`, `guide|${size - dominantCount}`] }),
      /primary_query_sample_size must be an integer >= 5/,
      (dir) => setupV12SerpEvidence(dir, { resultTypes, primarySampleSize: size, primaryDominantCount: dominantCount }),
    );
  });
}

test('P1 primary SERP sample size 5 with a 3-of-5 strict majority reaches the canonical SERP gate', (t) => {
  const resultTypes = ['checklist', 'checklist', 'checklist', 'guide', 'guide'];
  expectAxisHasNoFocusedProblem(
    t,
    v12ProductionSerpMutations({ primarySampleSize: '5', primaryDominantCount: '3', resultTypeCounts: ['checklist|3', 'guide|2'] }),
    /primary_query_sample_size|result_types observation count|strict majority|dominant count must satisfy/,
    (dir) => setupV12SerpEvidence(dir, { resultTypes, primarySampleSize: 5, primaryDominantCount: 3 }),
  );
});

test('V12 SERP structured evidence rejects device drift from exact query rows', (t) => {
  expectBlockMatching(t, v12ProductionSerpMutations(), /SERP-format evidence .* device must exactly match the 11-slot query evidence rows/, (dir) => setupV12SerpEvidence(dir, { device: 'mobile' }));
});

test('V12 SERP structured evidence rejects query-set and locale drift', (t) => {
  expectBlockMatching(t, v12ProductionSerpMutations(), /SERP-format evidence .* query_set must exactly equal|language must exactly match Brief/, (dir) => setupV12SerpEvidence(dir, { querySet: ['cargo hub motor engineering readiness checklist'], language: 'en-US' }));
});

test('V12 SERP structured evidence positive control preserves exact query, locale, device, date, and result types', (t) => {
  const result = validateArticlePackage(makeFixture(t, v12ProductionSerpMutations(), (dir) => setupV12SerpEvidence(dir)));
  assert.equal(result.problems.some((problem) => /SERP-format evidence .* (?:requires one non-empty exact|query_set must exactly equal|must exactly match Brief|device must|checked_at|result_types)/.test(problem)), false, result.problems.join('\n'));
});

for (const [label, options] of [
  ['10-slot row', { additionalRows: ['malformed|validate|object|output|validate|none|United States|en|desktop|2026-08-01'] }],
  ['12-slot row', { additionalRows: ['malformed|validate|object|output|validate|none|United States|en|desktop|2026-08-01|v11-query-evidence.md#exact-query-rows|EXTRA'] }],
  ['empty-slot row', { additionalRows: ['malformed|validate||output|validate|none|United States|en|desktop|2026-08-01|v11-query-evidence.md#exact-query-rows'] }],
  ['duplicate header', { duplicateHeader: true }],
  ['aliased header', { header: 'query|action|object|observable_output|stage|commercial_commitment|market|language|device|checked-at|evidence-ref' }],
]) {
  test(`V12 production query parser fails closed on ${label}`, (t) => {
    expectBlockMatching(t, v11ProductionQueryMutations(), /production query evidence ref .* (?:exact 11-slot query row header|data row|duplicate|aliased|non-canonical)/, (dir) => setupV11QueryRows(dir, options));
  });
}

for (const [label, row] of [
  ['11-slot row', 'malformed candidate|select|cargo motor|bounded result|validate|none|United States|en|desktop|2026-08-01|v11-query-evidence.md#exact-query-rows'],
  ['12-slot row', 'malformed candidate|select|cargo motor|bounded result|validate|none|United States|en|desktop|2026-08-01|v11-query-evidence.md#exact-query-rows|EXTRA'],
]) {
  test(`V12 production query parser rejects a ${label} before the canonical header`, (t) => {
    expectBlockMatching(t, v11ProductionQueryMutations(), /data row appears before the exact canonical header/, (dir) => setupV11QueryRows(dir, { prefixRows: [row] }));
  });
}

test('V12 technical and sales definition fields require exact canonical gate definitions', (t) => {
  expectBlockMatching(t, allRecords('technical_qualification_definition', '"technical-qualified requires all gates to be self-declared"'), /technical_qualification_definition must use the exact canonical gate definition/);
  expectBlockMatching(t, allRecords('sales_acceptance_definition', '"sales-accepted requires commercial gates to be asserted"'), /sales_acceptance_definition must use the exact canonical gate definition/);
});

test('V12 production secondary-buyer evidence is fragment-bound, dated, and non-synthetic', (t) => {
  const mutations = v12SetAllFields(v12SecondaryBuyerFields);
  for (const key of Object.keys(mutations)) {
    const prior = mutations[key];
    mutations[key] = (content) => replaceField(prior(content), 'evidence_scope', '"production"');
  }
  expectBlockMatching(t, mutations, /production secondary_buyer_role_contracts Quality evidence fragment requires|must be non-synthetic|references synthetic evidence/);
});

for (const [label, options] of [
  ['extra query', { extra: true }],
  ['duplicate query', { duplicate: true }],
]) {
  test(`V12 production query parser rejects ${label}`, (t) => {
    expectBlockMatching(t, v11ProductionQueryMutations(), /query evidence row query set must exactly equal/, (dir) => setupV11QueryRows(dir, options));
  });
}

// V14 focused coverage: stage-specific intake, title/H1, bounded pain,
// production search-demand evidence, and the publishable-body integration gate.
const v14TechnicalScalarFields = [
  'technical_qualification_requirement',
  'technical_qualification_contract_status',
  'technical_qualification_definition',
  'technical_qualification_owner',
  'technical_qualification_next_step',
];
const v14SalesScalarFields = [
  'sales_acceptance_requirement',
  'sales_acceptance_contract_status',
  'sales_acceptance_definition',
  'sales_acceptance_owner',
  'sales_acceptance_next_step',
  'sales_commercial_intent_required',
  'sales_commercial_intent_status',
  'sales_commercial_inputs_status',
];

function v14StageMutations({
  stage,
  intent,
  intake,
  commitment = 'none',
  firstRound = [],
  secondRound = [],
  relationships = [],
  technicalActive = false,
  salesActive = false,
  salesInputs = [],
  reasonCodes = [],
}) {
  const mutations = {};
  for (const key of Object.keys(fixtureNames)) {
    mutations[key] = (content) => {
      let output = content;
      for (const [field, value] of [
        ['stage', JSON.stringify(stage)],
        ['intent_class', JSON.stringify(intent)],
        ['stage_intake_contract', JSON.stringify(intake)],
        ['commercial_commitment', JSON.stringify(commitment)],
        ['first_round_inquiry_inputs', JSON.stringify(firstRound)],
        ['second_round_inquiry_inputs', JSON.stringify(secondRound)],
        ['second_round_input_relationships', JSON.stringify(relationships)],
        ['required_inquiry_inputs', JSON.stringify(firstRound)],
        ['cta_required_inputs', JSON.stringify(firstRound)],
        ['cta_progressive_profiling_omitted_inputs', JSON.stringify(secondRound)],
        ['cta_input_collection_applicability', JSON.stringify(intake === 'none' ? 'not-applicable' : 'applicable')],
        ['technical_qualification_gates', JSON.stringify(technicalActive ? ['first-round-complete', 'second-round-complete', 'no-evidenced-no-fit', 'named-technical-owner-accepted'] : [])],
        ['sales_acceptance_gates', JSON.stringify(salesActive ? ['explicit-commercial-intent', 'commercial-qualification-required', 'commercial-inputs-complete', 'named-commercial-owner-reviewed-and-accepted'] : [])],
        ['sales_commercial_inputs', JSON.stringify(salesInputs)],
        ['qualification_reason_codes', JSON.stringify(reasonCodes)],
      ]) output = replaceIfPresent(output, field, value);
      for (const field of v14TechnicalScalarFields) {
        output = replaceIfPresent(output, field, JSON.stringify(technicalActive ? `active-${field}` : 'not-applicable'));
      }
      for (const field of v14SalesScalarFields) {
        output = replaceIfPresent(output, field, JSON.stringify(salesActive ? `active-${field}` : 'not-applicable'));
      }
      return output;
    };
  }
  return mutations;
}

function expectAxisHasNoFocusedProblem(t, mutations, pattern, setup = null) {
  const result = validateArticlePackage(makeFixture(t, mutations, setup));
  assert.equal(result.problems.some((problem) => pattern.test(problem)), false, result.problems.join('\n'));
  return result;
}

const v14SupportInputs = ['observed fault symptom', 'operating condition when the fault appears'];
const v14CompareInputs = ['target duty profile', 'must-fit interface constraint'];
const v14CommercialInputs = ['requested quantity range', 'delivery destination', 'required delivery window'];

test('V14 complete Learn none-intake package is a clean positive baseline', (t) => {
  expectPass(makeFixture(t, notApplicableSyntheticMutations()));
});

test('V14 none intake rejects retained input and lifecycle state', (t) => {
  expectBlockMatching(t, {
    briefPath: (content) => replaceField(replaceField(content, 'stage', '"learn"'), 'stage_intake_contract', '"none"'),
  }, /stage_intake_contract=none requires (?:empty|required|technical|sales|cta_input)/);
});

test('V14 complete Troubleshoot package is a clean positive baseline', (t) => {
  expectPass(makeFixture(t, completeTroubleshootNoIntakeMutations()));
});

test('V14 troubleshoot-support rejects a second-round packet', (t) => {
  const mutations = v14StageMutations({ stage: 'troubleshoot', intent: 'informational', intake: 'troubleshoot-support', firstRound: v14SupportInputs, secondRound: ['oscilloscope trace under reproduced fault'] });
  expectBlockMatching(t, mutations, /only stage_intake_contract=validate-technical may use second_round_inquiry_inputs/);
});

test('V14 troubleshoot-support rejects the Validate technical-qualified lifecycle', (t) => {
  const technicalQualified = ['technical-qualified|technical-gates-satisfied|all technical gates are evidenced|Casey Morgan, Support Engineering Lead|preserve evidence and continue'];
  const mutations = v14StageMutations({ stage: 'troubleshoot', intent: 'informational', intake: 'troubleshoot-support', firstRound: v14SupportInputs, reasonCodes: technicalQualified });
  expectBlockMatching(t, mutations, /troubleshoot-support must not use the Validate technical-qualified lifecycle/);
});

test('V14 complete Compare package is a clean positive baseline', (t) => {
  expectPass(makeFixture(t, completeCompareNoIntakeMutations()));
});

test('V14 compare-handoff rejects non-mixed-commercial intent', (t) => {
  const mutations = v14StageMutations({ stage: 'compare', intent: 'commercial-investigation', intake: 'compare-handoff', firstRound: v14CompareInputs });
  expectBlockMatching(t, mutations, /compare-handoff may be used only with intent_class=mixed-commercial|requires stage_intake_contract=none/);
});

test('V14 compare-handoff rejects inherited Validate technical lifecycle', (t) => {
  const mutations = v14StageMutations({ stage: 'compare', intent: 'mixed-commercial', intake: 'compare-handoff', firstRound: v14CompareInputs, technicalActive: true });
  expectBlockMatching(t, mutations, /compare-handoff must not inherit Validate technical qualification gates/);
});

test('V14 validate-technical positive accepts canonical summary-to-detail refines relationships', (t) => {
  expectPass(makeFixture(t));
});

test('V14 validate-technical rejects a missing second-round relationship row', (t) => {
  const mutations = {};
  for (const key of Object.keys(fixtureNames)) mutations[key] = (content) => replaceIfPresent(content, 'second_round_input_relationships', '[]');
  expectBlockMatching(t, mutations, /second_round_input_relationships must contain exactly one row for every second_round_inquiry_inputs item/);
});

test('V14 validate-technical rejects re-requesting the exact same first-round value', (t) => {
  const repeated = legalFirstRoundInputs[0];
  const second = [repeated, ...legalSecondRoundInputs.slice(1)];
  const relationships = [
    `${repeated}|refines|${repeated}|attempts to request the identical value again after first-round review`,
    ...legalSecondRoundInputs.slice(1).map((item, index) => `${item}|new|not-applicable|adds a distinct decision input after first-round review ${index + 1}`),
  ];
  const mutations = {};
  for (const key of Object.keys(fixtureNames)) mutations[key] = (content) => replaceIfPresent(replaceIfPresent(content, 'second_round_inquiry_inputs', JSON.stringify(second)), 'second_round_input_relationships', JSON.stringify(relationships));
  expectBlockMatching(t, mutations, /second-round intake must not request the same value again/);
});

test('V14 complete Buy commercial package is a clean positive baseline', (t) => {
  expectPass(makeFixture(t, completeBuyCommercialMutations()));
});

test('V14 buy-commercial rejects inherited technical qualification gates and lifecycle', (t) => {
  const mutations = v14StageMutations({ stage: 'buy', intent: 'transactional', intake: 'buy-commercial', commitment: 'commercial', firstRound: v14CommercialInputs, technicalActive: true, salesActive: true, salesInputs: v14CommercialInputs });
  expectBlockMatching(t, mutations, /buy-commercial intake must not inherit technical qualification gates/);
});

test('V14 buy-commercial rejects an empty commercial sales packet', (t) => {
  const mutations = v14StageMutations({ stage: 'buy', intent: 'transactional', intake: 'buy-commercial', commitment: 'commercial', firstRound: v14CommercialInputs, salesActive: true, salesInputs: [] });
  expectBlockMatching(t, mutations, /buy-commercial intake requires a commercial\/RFQ packet in sales_commercial_inputs/);
});

test('V14 semantic Title/H1 positive control passes the canonical query, task, and stage gates', (t) => {
  expectPass(makeFixture(t));
});

test('V14 working title and article title drift is fatal', (t) => {
  expectBlockMatching(t, { draftPath: (content) => replaceField(content, 'article_title', '"Cargo Hub Motor Candidate Readiness Review Inputs"') }, /article_title must exactly match the approved Brief working_article_title/);
});

test('V14 unrelated word-salad title is blocked', (t) => {
  const title = '"Banana Lantern Wallpaper Cargo Hub Motor Readiness Checklist Review"';
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'working_article_title', title), draftPath: (content) => replaceField(content, 'article_title', title) }, /article_title contains unrelated word-salad terms/);
});

test('V14 wrong-stage title is blocked even when it retains query nouns', (t) => {
  const title = '"Cargo Hub Motor Engineering Overview and Core Concepts"';
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'working_article_title', title), draftPath: (content) => replaceField(content, 'article_title', title) }, /article_title does not express the declared validate stage/);
});

test('V14 transactional modifiers are blocked from a non-Buy title', (t) => {
  const title = '"Cargo Hub Motor Engineering Readiness Pricing and RFQ Checklist"';
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'working_article_title', title), draftPath: (content) => replaceField(content, 'article_title', title) }, /non-Buy article_title must not use transactional or commercial modifiers/);
});

test('V14 repeated title keyword stuffing is blocked', (t) => {
  const title = '"Cargo Cargo Cargo Hub Motor Engineering Readiness Checklist Review"';
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'working_article_title', title), draftPath: (content) => replaceField(content, 'article_title', title) }, /article_title contains query stuffing or repeated keyword tokens/);
});

for (const field of ['title_primary_query_parity_verdict', 'title_dominant_task_parity_verdict', 'title_stage_parity_verdict', 'h1_title_task_parity_verdict', 'hierarchy_scan_verdict', 'six_node_causal_chain_verdict']) {
  test(`V14 Review ${field}=block is a fatal article-structure gate`, (t) => {
    expectBlockMatching(t, { reviewPath: (content) => replaceField(content, field, '"block"') }, new RegExp(`${field} must be pass and is a fatal article-structure gate`));
  });
}

test('V14 legacy five-node causal-chain verdict cannot replace the six-node gate', (t) => {
  expectBlockMatching(t, { reviewPath: (content) => insertFields(content, { five_node_causal_chain_verdict: '"pass"' }) }, /unknown top-level field five_node_causal_chain_verdict/);
});


test('V14 legacy direct_answer_verdict cannot replace the six-slot gate', (t) => {
  expectBlockMatching(t, {
    reviewPath: (content) => insertFields(content, { direct_answer_verdict: '"pass"' }),
  }, /deprecated field direct_answer_verdict|unknown top-level field direct_answer_verdict/);
});

test('V14 missing direct_answer_six_slot_verdict fails closed', (t) => {
  expectBlockMatching(t, {
    reviewPath: (content) => removeField(content, 'direct_answer_six_slot_verdict'),
  }, /field direct_answer_six_slot_verdict is required|required field direct_answer_six_slot_verdict/);
});

for (const field of [
  'publishable_body_boundary_verdict', 'stage_intake_contract_verdict', 'title_slug_stage_parity_verdict',
  'buyer_visible_editorial_language_verdict', 'internal_control_term_leakage_verdict',
  'cta_value_exchange_verdict', 'product_link_claim_parity_verdict',
]) {
  test(`V14 Review ${field}=block is fatal or incompatible with an applicable contract`, (t) => {
    expectBlockMatching(t, {
      reviewPath: (content) => replaceField(content, field, '"block"'),
    }, new RegExp(`${field} must be pass|${field} must be pass when an applicable`));
  });
}

for (const term of ['technical-qualified', 'needs-follow-up', 'Soft CTA', 'Final CTA']) {
  test(`V14 buyer-visible body blocks internal control term ${term}`, (t) => {
    expectBlockMatching(t, {
      draftPath: (content) => transformBody(content, (body) => `${body}\n\nInternal marker attack: ${term}.\n`),
    }, /publishable body leaks internal workflow\/control terminology/);
  });
}

test('V14 family-level evidence cannot use a product-role target', (t) => {
  expectBlockMatching(t, {
    briefPath: (content) => mutateJsonArrayField(content, 'internal_link_targets', (rows) => rows.map((row, index) => index === 0 ? row.replace(/^solution\|/, 'product|') : row)),
  }, /family-level evidence must link a solution\/category target rather than a specific product target/);
});

test('V14 family-level evidence with a solution-role target remains valid', (t) => {
  expectPass(makeFixture(t));
});

test('V14 sku-level evidence without a product-role target fails closed', (t) => {
  expectBlockMatching(t, allRecords('product_link_evidence_level', '"sku-level"'), /sku-level evidence requires a product target/);
});

test('V14 malformed visual decision asset row fails closed', (t) => {
  expectBlockMatching(t, allRecords('visual_decision_assets', '["decision-table|buyer task|claim|evidence|section|caption|alt|mobile"]'), /visual_decision_assets requires exact/);
});

test('V14 visual decision asset requires a concrete mobile contract', (t) => {
  const mutate = (content) => mutateJsonArrayField(content, 'visual_decision_assets', (rows) => rows.map((row) => {
    const parts = row.split('|');
    parts[7] = 'readable layout';
    return parts.join('|');
  }));
  expectBlockMatching(t, Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, mutate])), /visual_decision_assets must declare a concrete mobile readability requirement/);
});

test('V14 CTA value exchange cannot be a placeholder', (t) => {
  expectBlockMatching(t, allRecords('cta_value_exchange', '"TBD"'), /cta_value_exchange must be at least|placeholder|publishable body must visibly communicate cta_value_exchange/);
});

test('V14 CTA value exchange must be visible in the publishable body', (t) => {
  expectBlockMatching(t, allRecords('cta_value_exchange', '"Receive a custom procurement cost forecast and private finance model"'), /publishable body must visibly communicate cta_value_exchange/);
});

test('V14 Validate slug cannot drift back to a Compare-style selection checklist', (t) => {
  expectBlockMatching(t, {
    draftPath: (content) => replaceField(content, 'slug', '"cargo-ebike-hub-motor-selection-checklist"'),
  }, /slug must preserve primary-query, decision-object, and observable-output parity|slug does not express the declared validate stage/);
});

test('V14 buyer language seeds require at least two concrete phrases', (t) => {
  expectBlockMatching(t, allRecords('buyer_language_seeds', '["motor"]'), /buyer_language_seeds requires at least two concrete buyer phrases/);
});

test('V14 query language transformation reason is mandatory and meaningful', (t) => {
  expectBlockMatching(t, allRecords('query_language_transformation_reason', '"TBD"'), /query_language_transformation_reason must be at least|placeholder/);
});

test('V14 deterministic synthetic pain language is blocked', (t) => {
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'pain_trigger', '"Wattage-first selection causes engineering rework and delays approval"') }, /inferred or synthetic pain language must use a bounded modal/);
});

test('V14 deterministic synthetic pain heading is blocked', (t) => {
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => body.replace('Why wattage-first selection may create avoidable rework', 'Why wattage-first selection creates avoidable rework')) }, /inferred or synthetic pain language must use a bounded modal/);
});

test('V14 bounded may/can/could pain language remains valid', (t) => {
  expectPass(makeFixture(t));
});

test('V14 production confirmed pain does not trigger the inferred-only modal rule', (t) => {
  const mutations = {};
  for (const key of Object.keys(fixtureNames)) {
    mutations[key] = (content) => {
      let output = replaceIfPresent(content, 'evidence_scope', '"production"');
      output = replaceIfPresent(output, 'pain_evidence_status', '"confirmed"');
      output = replaceIfPresent(output, 'pain_trigger', '"Wattage-first selection causes engineering rework and delays approval"');
      return output;
    };
  }
  expectAxisHasNoFocusedProblem(t, mutations, /inferred or synthetic pain language must use a bounded modal/);
});

const v14DemandQueries = [
  'cargo hub motor engineering readiness checklist',
  'cargo e-bike hub motor engineering readiness checklist',
  'cargo hub motor engineering review inputs',
  '20 inch cargo hub motor engineering readiness inputs',
];

function v14ProductionDemandMutations() {
  const mutations = {};
  for (const key of Object.keys(fixtureNames)) {
    mutations[key] = (content) => {
      let output = replaceIfPresent(content, 'evidence_scope', '"production"');
      output = replaceIfPresent(output, 'search_demand_evidence_status', '"confirmed"');
      output = replaceIfPresent(output, 'search_demand_evidence_refs', '["v14-demand-evidence.md#exact-search-demand"]');
      output = replaceIfPresent(output, 'search_demand_observation_start_at', '"2026-06-01T00:00:00Z"');
      output = replaceIfPresent(output, 'search_demand_observation_end_at', '"2026-07-31T23:59:59Z"');
      return output;
    };
  }
  return mutations;
}

function setupV14DemandEvidence(dir, overrides = {}) {
  const queries = overrides.exactQueries || v14DemandQueries;
  const rows = overrides.rows || v14DemandQueries.map((query, index) => `${query}|${120 - index * 20}|impressions`);
  const snapshotFile = 'gsc-export-2026-07-31.json';
  const snapshotDigest = writeProductionSnapshotArtifact(dir, {
    file: snapshotFile,
    kind: 'search-demand',
    payload: { query_set: queries, metric_type: 'search impressions', observation_window: '2026-06-01 to 2026-07-31' },
  });
  const fields = {
    exact_query_set: queries.join('; '),
    source_or_platform: 'Google Search Console immutable export',
    market: 'United States',
    language: 'en',
    device: 'desktop',
    observation_window: '2026-06-01 to 2026-07-31',
    observation_window_start: '2026-06-01T00:00:00Z',
    observation_window_end: '2026-07-31T23:59:59Z',
    metric_type: 'search impressions',
    brand_non_brand_boundary: 'Brand queries are excluded; non-brand queries are measured in this exact set.',
    zero_or_low_demand_decision: 'Keep the bounded target because non-zero demand was observed; reframe if the next window becomes zero.',
    seasonality_or_trend_note: 'Seasonality reviewed; trend was stable across the observation window.',
    analyst_conclusion: 'Observed search impressions across the exact query set support a bounded validation-stage target.',
    independent_reviewer: 'Riley Morgan, Independent Search Analyst',
    snapshot_ref: snapshotFile,
    snapshot_digest: snapshotDigest,
    ...overrides.fields,
  };
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'v14-demand-evidence.md',
    title: 'V14 production search demand evidence',
    kind: 'search-demand',
    heading: 'Exact search demand',
    section: `${Object.entries(fields).map(([key, value]) => `${key}: ${value}`).join('\n')}
observed_value_per_query:
${rows.map((row) => `  - ${row}`).join('\n')}
check_id: v14-production-search-demand
query: ${queries[0]}
target_url: https://search.google.com/search-console
 target_role: search-demand-source
target_task: confirm bounded non-brand search demand for the exact declared query set
observed_at: 2026-08-02T00:00:00Z
method: independently export exact-query Search Console impressions and compare every declared query row
observed_result: confirmed non-zero search impressions for the exact declared query set without inferring ranking, inquiry, or conversion outcomes
producer: Search Demand Evidence Producer
${snapshotBindingText('search-demand', queries[0])}`.replace('\n target_role:', '\ntarget_role:'),
  });
}

function expectV14DemandFocusedPositive(t, overrides = {}) {
  const paths = makeFixture(t, v14ProductionDemandMutations(), (dir) => setupV14DemandEvidence(dir, overrides));
  const records = ['briefPath', 'draftPath', 'reviewPath', 'publishPath'].map((key) => {
    const source = paths[key];
    const parsed = parseMarkdownFrontMatter(readFileSync(source, 'utf8'), { source });
    return { source, attributes: parsed.attributes, body: parsed.body };
  });
  const problems = [];
  records[2].attributes.reviewed_at = '2026-08-02T16:00:00Z';
  articlePackageValidatorTestHooks.validateProductionSearchDemandEvidence(
    records,
    records[0],
    records[2],
    'production',
    dirname(paths.briefPath),
    problems,
  );
  assert.deepEqual(problems, []);
  return problems;
}

test('V14 production search-demand exact schema focused positive consumes every query and evidence field', (t) => {
  expectV14DemandFocusedPositive(t);
});

test('V14 production search-demand rejects the wrong exact query set', (t) => {
  expectBlockMatching(t, v14ProductionDemandMutations(), /search-demand evidence .* wrong-query/, (dir) => setupV14DemandEvidence(dir, { exactQueries: v14DemandQueries.slice(0, -1) }));
});

test('V14 production search-demand rejects wrong market', (t) => {
  expectBlockMatching(t, v14ProductionDemandMutations(), /search-demand evidence .* wrong-market/, (dir) => setupV14DemandEvidence(dir, { fields: { market: 'Canada' } }));
});

test('V14 production search-demand rejects language drift', (t) => {
  expectBlockMatching(t, v14ProductionDemandMutations(), /search-demand evidence .* language must exactly match/, (dir) => setupV14DemandEvidence(dir, { fields: { language: 'de' } }));
});

test('V14 production search-demand rejects undeclared device vocabulary', (t) => {
  expectBlockMatching(t, v14ProductionDemandMutations(), /search-demand evidence .* device must be one exact declared device/, (dir) => setupV14DemandEvidence(dir, { fields: { device: 'smartwatch' } }));
});

test('V14 production search-demand rejects opinion-only source', (t) => {
  expectBlockMatching(t, v14ProductionDemandMutations(), /search-demand evidence .* opinion-only source cannot confirm demand/, (dir) => setupV14DemandEvidence(dir, { fields: { source_or_platform: 'sales opinion only' } }));
});

test('V14 production search-demand rejects a non-objective metric', (t) => {
  expectBlockMatching(t, v14ProductionDemandMutations(), /search-demand evidence .* no-metric/, (dir) => setupV14DemandEvidence(dir, { fields: { metric_type: 'analyst confidence score' } }));
});

test('V14 production search-demand rejects a missing per-query row', (t) => {
  expectBlockMatching(t, v14ProductionDemandMutations(), /observed_value_per_query must cover every exact query once/, (dir) => setupV14DemandEvidence(dir, { rows: v14DemandQueries.slice(0, -1).map((query) => `${query}|10|impressions`) }));
});

test('V14 production search-demand rejects duplicate and extra per-query rows', (t) => {
  const rows = [...v14DemandQueries.map((query) => `${query}|10|impressions`), `${v14DemandQueries[0]}|8|impressions`, 'unrelated cargo query|5|impressions'];
  expectBlockMatching(t, v14ProductionDemandMutations(), /observed_value_per_query must cover every exact query once/, (dir) => setupV14DemandEvidence(dir, { rows }));
});

test('V14 production search-demand rejects all-zero evidence that still keeps the target', (t) => {
  const rows = v14DemandQueries.map((query) => `${query}|0|impressions`);
  expectBlockMatching(t, v14ProductionDemandMutations(), /zero-demand falsely confirmed/, (dir) => setupV14DemandEvidence(dir, { rows, fields: { zero_or_low_demand_decision: 'Keep the target and publish it as planned.' } }));
});

test('V14 production search-demand rejects stale observation windows', (t) => {
  expectBlockMatching(t, v14ProductionDemandMutations(), /stale-window/, (dir) => setupV14DemandEvidence(dir, { fields: { observation_window: '2024-01-01 to 2024-12-31' } }));
});

test('V14 production search-demand rejects omitted seasonality assessment', (t) => {
  expectBlockMatching(t, v14ProductionDemandMutations(), /seasonality omitted or not explicitly assessed/, (dir) => setupV14DemandEvidence(dir, { fields: { seasonality_or_trend_note: 'Cyclical effects were not assessed in this export.' } }));
});

test('V14 production search-demand rejects self or AI review', (t) => {
  expectBlockMatching(t, v14ProductionDemandMutations(), /requires a distinct independent_reviewer/, (dir) => setupV14DemandEvidence(dir, { fields: { independent_reviewer: 'AI assistant self-review' } }));
});

test('V14 production search-demand rejects a placeholder snapshot reference', (t) => {
  expectBlockMatching(t, v14ProductionDemandMutations(), /requires non-placeholder snapshot_ref/, (dir) => setupV14DemandEvidence(dir, { fields: { snapshot_ref: 'placeholder' } }));
});

test('V14 production search-demand rejects a malformed digest', (t) => {
  expectBlockMatching(t, v14ProductionDemandMutations(), /digest must be sha256:<64-hex>/, (dir) => setupV14DemandEvidence(dir, { fields: { snapshot_digest: 'sha256:abc' } }));
});

function v14SwapPublishableMarkers(content) {
  return content
    .replace('<!-- PUBLISHABLE_BODY_START -->', '<!-- V14_TEMP_MARKER -->')
    .replace('<!-- PUBLISHABLE_BODY_END -->', '<!-- PUBLISHABLE_BODY_START -->')
    .replace('<!-- V14_TEMP_MARKER -->', '<!-- PUBLISHABLE_BODY_END -->');
}

test('V14 article-package integration blocks a missing publishable start marker', (t) => {
  expectBlockMatching(t, { draftPath: (content) => content.replace('<!-- PUBLISHABLE_BODY_START -->', '') }, /publishable-body extraction failed closed: .*found start=0, end=1/);
});

test('V14 article-package integration blocks a missing publishable end marker', (t) => {
  expectBlockMatching(t, { draftPath: (content) => content.replace('<!-- PUBLISHABLE_BODY_END -->', '') }, /publishable-body extraction failed closed: .*found start=1, end=0/);
});

test('V14 article-package integration blocks duplicate publishable markers', (t) => {
  expectBlockMatching(t, { draftPath: (content) => content.replace('<!-- PUBLISHABLE_BODY_START -->', '<!-- PUBLISHABLE_BODY_START -->\n<!-- PUBLISHABLE_BODY_START -->') }, /publishable-body extraction failed closed: .*found start=2, end=1/);
});

test('V14 article-package integration blocks reversed publishable markers', (t) => {
  expectBlockMatching(t, { draftPath: v14SwapPublishableMarkers }, /publishable-body extraction failed closed: Publishable article body markers are reversed/);
});

test('V14 article-package integration blocks an empty bounded body', (t) => {
  expectBlockMatching(t, { draftPath: (content) => {
    const start = content.indexOf('<!-- PUBLISHABLE_BODY_START -->') + '<!-- PUBLISHABLE_BODY_START -->'.length;
    const end = content.indexOf('<!-- PUBLISHABLE_BODY_END -->', start);
    return `${content.slice(0, start)}\n\n${content.slice(end)}`;
  } }, /publishable-body extraction failed closed: Publishable article body must not be empty/);
});

test('V14 control records outside publishable markers never enter buyer-facing validation', (t) => {
  const paths = makeFixture(t, { draftPath: (content) => content.replace('<!-- PUBLISHABLE_BODY_START -->', 'release_status: BLOCK\nrenderer_status: BLOCK\nreplace-with-internal-control-value\n<!-- PUBLISHABLE_BODY_START -->') });
  expectPass(paths);
});

test('V14 internal release status inside publishable body is blocked', (t) => {
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => `\nrelease_status: BLOCK\n${body}`) }, /publishable-body extraction failed closed: .*internal release status control data/);
});

test('V14 replace-with placeholder inside publishable body is blocked', (t) => {
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => `\nUse replace-with-real-product before publishing.\n${body}`) }, /publishable-body extraction failed closed: .*replace-with-\* placeholders/);
});


// V15 adversarial coverage: projection integrity, buyer-visible formatting,
// decision-asset placement, input/proof contracts, search gates, and source anchors.
function fixtureArray(name, field) {
  const content = normalizeFrontMatterSequences(readFileSync(new URL(name, exampleRoot), 'utf8'));
  const match = fieldPattern(field).exec(content);
  assert.ok(match, `canonical fixture must contain ${field}`);
  const value = JSON.parse(match[0].slice(match[0].indexOf(':') + 1).trim());
  assert.equal(Array.isArray(value), true, `${field} must be a JSON array`);
  return value;
}

function canonicalCtaInstruction(surfaceId) {
  const rows = fixtureArray(fixtureNames.briefPath, 'buyer_visible_cta_inventory');
  const matches = rows.filter((row) => row.startsWith(`${surfaceId}|`));
  assert.equal(matches.length, 1, `${surfaceId} must occur exactly once`);
  const parts = matches[0].split('|');
  assert.equal(parts.length, 10, `${surfaceId} must use the 10-slot CTA inventory schema`);
  return parts[3];
}

function setInputSpecificationRows(rows) {
  return {
    briefPath: (content) => replaceField(content, 'first_round_input_specifications', JSON.stringify(rows)),
    draftPath: (content) => replaceField(content, 'first_round_input_specifications', JSON.stringify(rows)),
    reviewPath: (content) => replaceField(content, 'first_round_input_specifications', JSON.stringify(rows)),
    publishPath: (content) => replaceField(content, 'first_round_input_specifications_snapshot', JSON.stringify(rows)),
  };
}

function setCapabilityProofRows(rows) {
  return {
    briefPath: (content) => replaceField(content, 'cta_buyer_visible_capability_proofs', JSON.stringify(rows)),
    draftPath: (content) => replaceField(content, 'cta_buyer_visible_capability_proofs', JSON.stringify(rows)),
    reviewPath: (content) => replaceField(content, 'cta_buyer_visible_capability_proofs', JSON.stringify(rows)),
    publishPath: (content) => replaceField(content, 'cta_buyer_visible_capability_proofs_snapshot', JSON.stringify(rows)),
  };
}

function mutateFirstInputSpecification(mutator) {
  const rows = fixtureArray(fixtureNames.briefPath, 'first_round_input_specifications');
  rows[0] = mutator(rows[0]);
  return setInputSpecificationRows(rows);
}

function mutateCapabilityProof(mutator) {
  const rows = fixtureArray(fixtureNames.briefPath, 'cta_buyer_visible_capability_proofs');
  rows[0] = mutator(rows[0]);
  return setCapabilityProofRows(rows);
}

test('V15 Draft pain trigger cannot drift from the Brief', (t) => {
  expectBlockMatching(t, { draftPath: (content) => replaceField(content, 'pain_trigger', '"a different buyer event with unrelated operating conditions"') }, /pain_trigger must match the canonical Brief projection/);
});

test('V15 Review pain snapshot cannot drift from the Brief', (t) => {
  expectBlockMatching(t, { reviewPath: (content) => replaceField(content, 'surface_problem_snapshot', '"a different review snapshot that no longer matches the approved buyer problem"') }, /projection surface_problem_snapshot must exactly match/);
});

test('V15 Publish pain-chain contract cannot drift across records', (t) => {
  expectBlockMatching(t, { publishPath: (content) => replaceField(content, 'pain_chain_contract', '"Engineer|different event|different gap|different rework|different consequence|different decision"') }, /pain_chain_contract must match the canonical Brief projection/);
});

test('V15 low-entropy Publish pain snapshot is rejected', (t) => {
  expectBlockMatching(t, { publishPath: (content) => replaceField(content, 'pain_trigger_snapshot', '"aaaaaaaaaaaaaaaaaaaa"') }, /pain_trigger_snapshot must be a concrete non-placeholder value|projection pain_trigger_snapshot must exactly match/);
});

test('V15 applicable Publish CTA input snapshot cannot be emptied', (t) => {
  expectBlockMatching(t, { publishPath: (content) => replaceField(content, 'cta_required_inputs_snapshot', '[]') }, /cta_required_inputs_snapshot must not be empty when .* cta_required_inputs is applicable/);
});

test('V15 Draft product decision map cannot drift from the Brief', (t) => {
  expectBlockMatching(t, { draftPath: (content) => mutateJsonArrayField(content, 'product_decision_map', (rows) => rows.map((row) => `${row} altered`)) }, /product_decision_map must match the canonical Brief projection/);
});

test('V15 Draft internal-link target cannot drift from the Brief', (t) => {
  expectBlockMatching(t, { draftPath: (content) => mutateJsonArrayField(content, 'internal_link_targets', (rows) => rows.map((row, index) => index ? row : row.replace('identify unresolved inputs in the cargo hub-motor solution-family boundary before selecting or stopping a candidate direction', 'read a different generic destination'))) }, /internal_link_targets must match the canonical Brief projection/);
});

for (const [label, field, value, pattern] of [
  ['title', 'published_article_title', '"Different Published Title"', /projection published_article_title must exactly match/],
  ['slug', 'published_slug', '"different-published-slug"', /projection published_slug must exactly match/],
  ['meta description', 'published_meta_description', '"Different published metadata that does not match the approved draft."', /projection published_meta_description must exactly match/],
  ['excerpt', 'published_excerpt', '"Different published excerpt that does not match the approved draft."', /projection published_excerpt must exactly match/],
]) {
  test(`V15 Publish ${label} cannot drift from the approved Draft`, (t) => {
    expectBlockMatching(t, { publishPath: (content) => replaceField(content, field, value) }, pattern);
  });
}

test('V15 keyed-row projections reject duplicate keys even when rows are duplicated consistently', (t) => {
  const rows = fixtureArray(fixtureNames.briefPath, 'product_decision_map');
  const duplicated = [...rows, rows[0]];
  expectBlockMatching(t, {
    briefPath: (content) => replaceField(content, 'product_decision_map', JSON.stringify(duplicated)),
    draftPath: (content) => replaceField(content, 'product_decision_map', JSON.stringify(duplicated)),
    reviewPath: (content) => replaceField(content, 'product_decision_map_snapshot', JSON.stringify(duplicated)),
    publishPath: (content) => replaceField(content, 'product_decision_map_snapshot', JSON.stringify(duplicated)),
  }, /contains duplicate keyed rows/);
});

test('V15 exact-sequence projections reject reordered CTA inputs', (t) => {
  expectBlockMatching(t, { publishPath: (content) => mutateJsonArrayField(content, 'cta_required_inputs_snapshot', (rows) => [rows[1], rows[0], ...rows.slice(2)]) }, /cta_required_inputs_snapshot must exactly match .* using exact-sequence/);
});

for (const [label, injected] of [
  ['bold', 'technical-**qualified**'],
  ['link', 'technical-[qualified](https://example.test/qualification)'],
  ['inline code', 'technical-`qualified`'],
  ['underline HTML', 'technical-<u>qualified</u>'],
]) {
  test(`V15 buyer-visible internal control term cannot hide behind ${label} styling`, (t) => {
    expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => `${injected} is an internal state and must not appear here.\n\n${body}`) }, /leaks internal workflow\/control terminology/);
  });
}

function mutateVisualPlacement(content, placement) {
  return mutateJsonArrayField(content, 'visual_decision_assets', (rows) => rows.map((row, index) => {
    if (index) return row;
    const parts = row.split('|');
    parts[4] = placement;
    return parts.join('|');
  }));
}

test('V15 visual decision placement cannot point at another real H2 while the decision table remains elsewhere', (t) => {
  expectBlockMatching(t, allRecords('visual_decision_assets', JSON.stringify(fixtureArray(fixtureNames.briefPath, 'visual_decision_assets').map((row) => {
    const parts = row.split('|'); parts[4] = 'after the hand the candidate to the next validation task section'; return parts.join('|');
  }))), /decision-table asset (?:requires exactly five distinct decision blocks|must be bound to exactly one semantic table or five valid decision blocks) inside its declared H2 section/);
});

test('V15 decision table moved out of its declared H2 section is blocked', (t) => {
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => {
    const section = body.match(/## Use five decision blocks before the first review\n[\s\S]*?(?=\n## Candidate or stop: make the boundary visible)/);
    assert.ok(section, 'canonical decision-table section must be locatable');
    const block = section[0].match(/^### Establish the load context\n[\s\S]*?(?=\n### Define the rolling geometry)/m);
    assert.ok(block, 'canonical decision-table section must contain the first decision block');
    let output = replaceRequiredLiteral(body, block[0], '', 'declared decision block');
    output = replaceRequiredLiteral(output, '## Candidate or stop: make the boundary visible', `## Candidate or stop: make the boundary visible\n\n${block[0].trim()}`, 'decision-block destination H2');
    return output;
  }) }, /decision-table asset requires exactly five distinct decision blocks|decision-table asset must be bound to exactly one semantic table or five valid decision blocks/);
});

test('V15 decision table must itself support the declared buyer task and claim', (t) => {
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => {
    const section = body.match(/## Use five decision blocks before the first review\n[\s\S]*?(?=\n## Candidate or stop: make the boundary visible)/);
    assert.ok(section, 'canonical decision-table section must be locatable');
    const generic = section[0].replace(/(^### .+$)\n[\s\S]*?(?=\n### |$)/gm, '$1\nGeneric note. Continue.');
    assert.notEqual(generic, section[0], 'generic decision-block mutation must be non-noop');
    return replaceRequiredLiteral(body, section[0], generic, 'decision-block task and claim attack');
  }) }, /decision block .* concrete buyer-visible decision guidance|five decision blocks must collectively support the declared buyer task and claim|decision-table asset must be bound/);
});

test('V15 five empty decision headings cannot satisfy the semantic decision asset', (t) => {
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => body.replace(
    /(^### (?:Establish|Define|Describe|Separate|Summarize).+$)\n[^\n]+/gm,
    '$1\n',
  )) }, /decision-table asset requires five non-repeated decision blocks|decision block .* concrete buyer-visible decision guidance|condition or evidence gap and a next action/);
});

test('V15 input specifications reject a missing row', (t) => {
  const rows = fixtureArray(fixtureNames.briefPath, 'first_round_input_specifications').slice(0, -1);
  expectBlockMatching(t, setInputSpecificationRows(rows), /must contain exactly one row for every first_round_inquiry_inputs item/);
});

test('V15 input specifications reject a duplicate input and order drift', (t) => {
  const rows = fixtureArray(fixtureNames.briefPath, 'first_round_input_specifications');
  rows[1] = rows[0];
  expectBlockMatching(t, setInputSpecificationRows(rows), /contains duplicate input|input order must exactly follow/);
});

test('V15 input specifications reject five-slot rows', (t) => {
  expectBlockMatching(t, mutateFirstInputSpecification((row) => row.split('|').slice(0, 5).join('|')), /requires exact input\|why-needed\|accepted-unit-or-format\|example\|required-or-conditional\|confidentiality-boundary rows/);
});

test('V15 input specifications reject seven-slot rows', (t) => {
  expectBlockMatching(t, mutateFirstInputSpecification((row) => `${row}|extra`), /requires exact input\|why-needed\|accepted-unit-or-format\|example\|required-or-conditional\|confidentiality-boundary rows/);
});

test('V15 input specifications reject an empty example', (t) => {
  expectBlockMatching(t, mutateFirstInputSpecification((row) => { const parts = row.split('|'); parts[3] = ''; return parts.join('|'); }), /requires exact input\|why-needed|example must be concrete/);
});

test('V15 input specifications reject a generic unit or format', (t) => {
  expectBlockMatching(t, mutateFirstInputSpecification((row) => { const parts = row.split('|'); parts[2] = 'send useful details'; return parts.join('|'); }), /accepted-unit-or-format must name a concrete unit or format/);
});

test('V15 input specifications reject an unsafe missing data boundary', (t) => {
  expectBlockMatching(t, mutateFirstInputSpecification((row) => { const parts = row.split('|'); parts[5] = 'send every available file without restriction'; return parts.join('|'); }), /confidentiality-boundary must state an explicit safe-data boundary/);
});

test('V15 input specifications in frontmatter must be visible in the real CTA section', (t) => {
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => {
    const example = '38 kg bicycle + 82 kg rider + 60 kg payload = 180 kg maximum';
    const index = body.lastIndexOf(example);
    assert.notEqual(index, -1, 'final CTA concrete input example must be locatable');
    return `${body.slice(0, index)}example intentionally removed${body.slice(index + example.length)}`;
  }) }, /CTA section must visibly show the concrete example|decision asset matching input row must visibly show the concrete example/);
});

test('V15 capability proof rejects a generic brand slogan', (t) => {
  expectBlockMatching(t, mutateCapabilityProof((row) => { const parts = row.split('|'); parts[2] = 'We are the trusted global innovation leader for every customer'; parts[4] = 'Choose our trusted global innovation leadership for your project'; return parts.join('|'); }), /cannot be a generic brand slogan/);
});

test('V15 capability proof task must match the dominant buyer task', (t) => {
  expectBlockMatching(t, mutateCapabilityProof((row) => { const parts = row.split('|'); parts[1] = 'negotiate annual freight contracts and payment terms'; return parts.join('|'); }), /buyer task must match the dominant task and CTA value exchange/);
});

test('V15 capability proof evidence fragment must resolve', (t) => {
  expectBlockMatching(t, mutateCapabilityProof((row) => { const parts = row.split('|'); parts[3] = 'search-evidence.md#missing-capability-proof-fragment'; return parts.join('|'); }), /fragment .* (?:was not found|does not resolve|does not match an evidence section)/);
});

test('V15 production capability proof cannot rely on synthetic fixture evidence', (t) => {
  const base = mutateCapabilityProof((row) => row);
  for (const key of Object.keys(base)) {
    const prior = base[key];
    base[key] = (content) => replaceField(prior(content), 'evidence_scope', '"production"');
  }
  expectBlockMatching(t, base, /references synthetic evidence|production .* must not use synthetic/);
});

test('V15 capability proof copy must appear in the actual CTA section', (t) => {
  expectBlockMatching(t, mutateCapabilityProof((row) => { const parts = row.split('|'); parts[4] = 'The response includes a redacted torque audit and named acceptance matrix for this buyer task'; return parts.join('|'); }), /buyer-visible capability proof copy must be materially present in the actual CTA section/);
});

test('V15 collecting CTA cannot mark every capability proof not-applicable', (t) => {
  expectBlockMatching(t, mutateCapabilityProof((row) => { const parts = row.split('|'); parts[5] = 'not-applicable'; return parts.join('|'); }), /requires at least one applicable capability proof/);
});

for (const field of ['query_evidence_status', 'buyer_task_evidence_status', 'search_demand_evidence_status', 'serp_format_evidence_status']) {
  test(`V15 closed schema rejects a missing search-axis field ${field}`, (t) => {
    expectBlockMatching(t, { briefPath: (content) => removeField(content, field) }, new RegExp(`field ${field} is required`));
  });
}

test('V15 search-axis status vocabulary rejects invented values', (t) => {
  expectBlockMatching(t, { briefPath: (content) => replaceField(content, 'search_demand_evidence_status', '"probably-good"') }, /search_demand_evidence_status must use canonical fact-status vocabulary|must be one of/);
});

test('V15 synthetic package cannot mark the production search evidence gate pass', (t) => {
  expectBlockMatching(t, { publishPath: (content) => replaceField(content, 'production_search_evidence_gate_verdict', '"pass"') }, /synthetic fixture requires production_search_evidence_gate_verdict=block/);
});

test('V15 production package cannot leave the production search evidence gate blocked', (t) => {
  const mutations = allRecords('evidence_scope', '"production"');
  expectBlockMatching(t, mutations, /production requires production_search_evidence_gate_verdict=pass/);
});

test('V15 Review and Publish search evidence refs cannot drift', (t) => {
  expectBlockMatching(t, { reviewPath: (content) => replaceField(content, 'buyer_task_evidence_refs', '["search-evidence.md#fixture-buyer-task-evidence","search-evidence.md#fixture-artifact-status-versus-market-information-gain"]') }, /buyer_task_evidence_refs must match the canonical Brief projection across all records/);
});

function setupAnchoredSyntheticEvidence(dir, { duplicate = false } = {}) {
  setupLegalSyntheticEvidence(dir);
  const path = join(dir, 'positive-evidence.md');
  let content = readFileSync(path, 'utf8');
  const anchor = '<a id="synthetic-inventory-zero-result"></a>';
  content = content.replace('## Synthetic inventory zero result', `${anchor}\n${duplicate ? `${anchor}\n` : ''}## Synthetic inventory zero result`);
  writeFileSync(path, content);
}

test('V15 evidence refs may resolve through one narrow source-only anchor before the matching heading', (t) => {
  expectPass(makeFixture(t, legalSyntheticMutations(), (dir) => setupAnchoredSyntheticEvidence(dir)));
});

test('V15 duplicate source-only evidence anchors fail closed', (t) => {
  expectBlockMatching(t, legalSyntheticMutations(), /fragment #?synthetic-inventory-zero-result is ambiguous|duplicate/, (dir) => setupAnchoredSyntheticEvidence(dir, { duplicate: true }));
});

test('V15 arbitrary raw HTML in the publishable article remains blocked', (t) => {
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => `<div data-attack="true">unsupported wrapper</div>\n\n${body}`) }, /raw html|unsupported.*html|publishable-body extraction failed closed/i);
});

test('V15 source-only anchors are stripped before AllinCMS Slate conversion', () => {
  const source = readFileSync(new URL(fixtureNames.draftPath, exampleRoot), 'utf8');
  const markdown = extractPublishableArticleMarkdown(source);
  assert.equal(markdown.includes('<a id='), false);
  const slate = publishableArticleMarkdownToAllinCmsSlate(source);
  assert.equal(JSON.stringify(slate).includes('<a id='), false);
});

test('V16 canonical example bodies reject legacy evidence-axis table values', (t) => {
  expectBlockMatching(t, {
    reviewPath: (content) => transformMarkdownSection(content, '## 8. Gate matrix', '## 9. Outcome evidence contract', (section) => section.replace('`executed`', '`completed-local`')),
  }, /evidence-axis table execution value must use the closed canonical allowlist; received completed-local/);
});

test('V16 canonical FluxPedal docs contain only the canonical three-axis vocabulary', () => {
  const legacy = /\b(?:completed-local|pass-local-structure-only|pass-fixture-only|not-applicable-to-synthetic-reserved-url)\b/i;
  for (const name of ['README.md', 'b2b-seo-article-review.md', 'b2b-seo-publish-record.md']) {
    assert.doesNotMatch(readFileSync(new URL(name, exampleRoot), 'utf8'), legacy, `${name} must not teach a legacy evidence-axis value`);
  }
});

test('V16 unverified fallback cannot self-certify a verified engineering channel', (t) => {
  expectBlockMatching(t, {
    draftPath: (content) => transformBody(content, (body) => replaceRequiredLiteral(
      body,
      canonicalCtaInstruction('fallback-route-request-01'),
      'If the primary route is unavailable, send the packet through the verified engineering channel owned by Applications Engineering.',
      'current unverified fallback instruction',
    )),
  }, /unverified fallback contract is contradicted by an unsafe buyer-visible CTA section/);
});

test('V16 unverified fallback must explicitly disclose that no verified route exists', (t) => {
  expectBlockMatching(t, {
    draftPath: (content) => transformBody(content, (body) => replaceRequiredLiteral(
      body,
      canonicalCtaInstruction('fallback-route-request-01'),
      "If the primary route is unavailable, do not send or submit the packet. Save it locally, then use your organization's existing approved supplier-contact process to request next steps from Applications Engineering.",
      'current no-verified disclosure',
    )),
  }, /every buyer-visible fallback instruction must explicitly disclose that no verified route is available|must explicitly state that no verified fallback route is available/);
});

const verifiedFallbackEndpoint = 'https://example.test/contact/engineering-fallback';
const verifiedFallbackEvidenceRefs = {
  reference: 'fallback-route-evidence.md#fallback-reference',
  reachability: 'fallback-route-evidence.md#fallback-reachability',
  capability: 'fallback-route-evidence.md#fallback-capability',
};

function verifiedFallbackContract({
  endpoint = verifiedFallbackEndpoint,
  refs = verifiedFallbackEvidenceRefs,
  commitmentBoundary = 'Using the fallback route requests bounded technical review only and creates no RFQ, quote, order, supplier award, delivery promise, or sales acceptance.',
} = {}) {
  return [
    'verified',
    endpoint,
    'Avery Chen, Applications Engineering Lead',
    'same-as-cta-required-inputs',
    commitmentBoundary,
    'executed', 'confirmed', 'pass', refs.reference,
    'executed', 'confirmed', 'pass', refs.reachability,
    'executed', 'confirmed', 'pass', refs.capability,
  ].join('|');
}

function setupVerifiedFallbackEvidence(dir, {
  endpoint = verifiedFallbackEndpoint,
  referenceEndpoint = endpoint,
  reachabilityEndpoint = endpoint,
  capabilityEndpoint = endpoint,
} = {}) {
  const owner = 'Avery Chen, Applications Engineering Lead';
  mkdirSync(join(dir, 'artifacts'), { recursive: true });
  const section = (name, target, observedResult) => {
    const artifactRef = `artifacts/fallback-${name}.txt`;
    const artifactBytes = `Independent fallback ${name} evidence for ${target} and bounded technical review captured at 2026-08-01T00:00:00Z.\n`;
    writeFileSync(join(dir, artifactRef), artifactBytes);
    const artifactDigest = `sha256:${createHash('sha256').update(artifactBytes).digest('hex')}`;
    return `## Fallback ${name}

check_id: fallback-${name}
target_url: ${target}
target_role: fallback-route
target_task: verify fallback ${name} for bounded technical review
accountable_owner: ${owner}
observed_at: 2026-08-01T00:00:00Z
method: independent endpoint-specific ${name} verification process
observed_result: ${observedResult}
acceptance_criteria: The exact fallback ${name} check must bind this endpoint, owner, task, and affirmative observed result.
capability_acceptance: The exact fallback ${name} route is accepted only for the bounded technical-review task without commercial commitment.
artifact_ref: ${artifactRef}
artifact_digest: ${artifactDigest}
producer: Synthetic Route Evidence Producer
producer_id: wco-fallback-route-producer-001
independent_reviewer: Taylor Morgan, Independent Route Reviewer
independent_reviewer_id: wco-fallback-route-reviewer-001
`;
  };
  const body = `# Verified fallback route evidence

${section('reference', referenceEndpoint, 'Confirmed the exact fallback endpoint reference is bound to the declared bounded technical-review route.')}
${section('reachability', reachabilityEndpoint, 'Confirmed the exact fallback endpoint responded through the independently checked route process.')}
${section('capability', capabilityEndpoint, 'Confirmed the exact fallback endpoint accepted the bounded technical-review task and returned the expected route acknowledgement.')}
`;
  const digest = createHash('sha256').update(body).digest('hex');
  writeFileSync(join(dir, 'fallback-route-evidence.md'), `---
title: Verified fallback route evidence
record_type: evidence-record
evidence_scope: production
source: independent fallback route verification
observed_at: 2026-08-01T00:00:00Z
digest: sha256:${digest}
evidence_kind: fallback-route
---
${body}`);
}


function replaceOwnerRouteSection(body, replacement) {
  const ownerHeadings = ['### Owner, output, and route boundary', '## Request a bounded engineering-readiness review'];
  const matchedOwnerHeadings = ownerHeadings.filter((heading) => body.split(heading).length - 1 === 1);
  const nextHeading = '### Validation boundary';
  const nextCount = body.split(nextHeading).length - 1;
  assert.equal(matchedOwnerHeadings.length, 1, `required owner-route heading must occur exactly once across current and legacy anchors; observed ${matchedOwnerHeadings.length}`);
  assert.equal(nextCount, 1, `required validation-boundary heading must occur exactly once; observed ${nextCount}`);
  const ownerHeading = matchedOwnerHeadings[0];
  const start = body.indexOf(ownerHeading);
  const end = body.indexOf(nextHeading, start + ownerHeading.length);
  assert.ok(end > start, 'required owner-route section must precede validation boundary');
  const current = body.slice(start, end);
  const next = `${ownerHeading}\n\n${replacement.trim()}\n\n`;
  assert.notEqual(current, next, 'required owner-route mutation must not be a no-op');
  return `${body.slice(0, start)}${next}${body.slice(end)}`;
}

function verifiedFallbackCopy({
  endpoint = verifiedFallbackEndpoint,
  approved = true,
  includeEndpoint = true,
  alternateEndpoint = null,
} = {}) {
  const visibleEndpoint = includeEndpoint ? (alternateEndpoint || endpoint) : '';
  const qualifier = approved ? 'approved fallback form' : 'fallback form';
  const linkedQualifier = visibleEndpoint ? `[${qualifier}](${visibleEndpoint})` : qualifier;
  const verifiedStrong = `After the ${qualifier} is confirmed, submit the packet only through that endpoint.`;
  const verifiedParagraph = `If the primary route is unavailable, after the ${qualifier} is confirmed, use only that endpoint for the bounded engineering-readiness review owned by Avery Chen, Applications Engineering Lead.`;
  const verifiedFallbackMessage = `If the primary route is unavailable, after the ${qualifier} is confirmed, use only that endpoint for Avery Chen, Applications Engineering Lead. Use the single prepared local worksheet. Return first-round packet completeness, assumptions, missing inputs, and the next validation task. This is not an RFQ.`;
  const verifiedPost = `After the ${qualifier} is confirmed, copy the single prepared local worksheet into that endpoint for Avery Chen, Applications Engineering Lead. Request only packet-completeness review, assumptions, missing inputs, and the next validation task; this is not an RFQ.`;
  const link = (value) => value.replace(qualifier, linkedQualifier);
  return {
    visibleEndpoint,
    verifiedStrong,
    verifiedParagraph,
    verifiedFallbackMessage,
    verifiedPost,
    verifiedStrongMarkdown: link(verifiedStrong),
    verifiedParagraphMarkdown: link(verifiedParagraph),
    verifiedFallbackMessageMarkdown: link(verifiedFallbackMessage),
    verifiedPostMarkdown: link(verifiedPost),
  };
}

function replaceVerifiedFallbackBody(content, options = {}) {
  const copy = verifiedFallbackCopy(options);
  const dataPurpose = 'Use the five engineering inputs only to perform the bounded engineering-readiness review and identify missing validation evidence.';
  const retentionPeriod = 'Retain the packet only until the review closes or 30 days after the last review activity, whichever comes first.';
  const deletionPath = 'After a verified route exists, request deletion through that route; while no route exists, the buyer controls and may delete the local copy.';
  const retentionOwner = 'Avery Chen, Applications Engineering Lead';
  return transformBody(content, (body) => replaceOwnerRouteSection(body, `**${copy.verifiedStrongMarkdown}**

- Owner: Avery Chen, Applications Engineering Lead.
- Expected output: packet completeness, a missing-evidence list, and the next review step; only after the complete second-round package and named technical-owner review may Applications Engineering return candidate-or-stop.
- Boundary: no final suitability, compliance, measured performance, production readiness, MOQ, lead time, price, order acceptance, or response-time claim.
- Data purpose: ${dataPurpose}
- Retention period: ${retentionPeriod}
- Deletion path: ${deletionPath}
- Retention owner: ${retentionOwner}

${copy.verifiedParagraphMarkdown}

> ${copy.verifiedFallbackMessageMarkdown}

${copy.verifiedPostMarkdown}`));
}

function verifiedFallbackEvidenceMutations(bodyOptions = {}) {
  const contract = verifiedFallbackContract(bodyOptions.contractOptions);
  const copy = verifiedFallbackCopy(bodyOptions);
  const instructionById = new Map([
    ['fallback-do-not-send-01', copy.verifiedStrong],
    ['fallback-route-request-01', copy.verifiedParagraph],
    ['fallback-copyable-message-01', copy.verifiedFallbackMessage],
    ['primary-bounded-review-01', copy.verifiedPost],
  ]);
  return Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => {
    let output = replaceField(content, 'cta_fallback_route_contract', JSON.stringify(contract));
    output = replaceIfPresent(output, 'cta_fallback_message_template', JSON.stringify(copy.verifiedFallbackMessage));
    output = mutateJsonArrayField(output, 'buyer_visible_cta_inventory', (rows) => rows.map((row) => {
      const parts = row.split('|');
      const originalId = parts[0];
      const instruction = instructionById.get(originalId);
      if (instruction) {
        if (originalId === 'primary-bounded-review-01') parts[0] = 'fallback-bounded-review-01';
        parts[3] = instruction;
        parts[4] = copy.visibleEndpoint;
        parts[5] = 'Avery Chen, Applications Engineering Lead';
        parts[6] = 'human-handoff';
        parts[7] = 'verified';
        parts[8] = verifiedFallbackEvidenceRefs.capability;
        parts[9] = 'cta_fallback_route_contract';
      }
      return parts.join('|');
    }));
    if (key === 'briefPath' || key === 'draftPath') {
      output = mutateJsonArrayField(output, 'semantic_emphasis_plan', (rows) => rows.map((row) => /^(?:route|action)\|/.test(row)
        ? `action|${copy.verifiedStrongMarkdown}|request a bounded engineering-readiness review`
        : row));
    }
    if (key === 'draftPath') output = replaceVerifiedFallbackBody(output, bodyOptions);
    if (key === 'briefPath' || key === 'publishPath') output = transformDocumentBody(output, (body) => replaceRequiredLiteral(body, canonicalRouteAndPolicyFallbackFor(key), copy.verifiedFallbackMessage, 'verified control-record fallback message'));
    return output;
  }]));
}

test('V16 verified fallback contract accepts independent evidence and the same approved endpoint in every buyer-visible fallback section', (t) => {
  expectPass(makeFixture(t, completeProductionValidateMutations(), setupCompleteProductionValidateEvidence));
});

test('V16 verified fallback contract blocks buyer-visible fallback instructions without the exact endpoint', (t) => {
  expectBlockMatching(
    t,
    verifiedFallbackEvidenceMutations({ includeEndpoint: false }),
    /every buyer-visible fallback instruction must display the exact verified contract endpoint/,
    (dir) => setupVerifiedFallbackEvidence(dir),
  );
});

test('V16 verified fallback contract blocks a concrete endpoint that is not identified as verified or approved', (t) => {
  expectBlockMatching(
    t,
    verifiedFallbackEvidenceMutations({ approved: false }),
    /every buyer-visible fallback instruction must identify the concrete route as verified or approved/,
    (dir) => setupVerifiedFallbackEvidence(dir),
  );
});

for (const [label, surfaceId, from, to, pattern] of [
  ['do-not-send instruction', 'fallback-do-not-send-01', 'Do not send or submit the worksheet until', 'Hold the worksheet until', /buyer_visible_cta_inventory .* unverified route instruction must visibly preserve the do-not-send or verified-route boundary|unverified fallback branch must tell the buyer not to send the packet|every buyer-visible fallback instruction must prohibit transmitting the packet/],
  ['local-save instruction', 'fallback-copyable-message-01', 'Keep the completed local readiness worksheet on your device;', 'Keep the completed readiness worksheet available;', /unverified fallback branch must tell the buyer to save the packet locally|every buyer-visible fallback instruction must keep the packet local/],
  ["buyer approved supplier-contact process", 'fallback-route-request-01', 'through the buyer organization’s existing approved supplier-contact process', 'by contacting Applications Engineering directly', /every buyer-visible fallback instruction must use the buyer's existing approved supplier-contact process/],
  ['verified-route request', 'fallback-route-request-01', 'Request only a production-verified technical-review route, buyer-visible data boundary, and responsible responder', 'Request only next steps', /unverified fallback branch must tell the buyer to request a verified route|every buyer-visible fallback instruction must request a verified route/],
]) {
  test(`V16 unverified fallback fails closed without the ${label}`, (t) => {
    const canonicalInstruction = canonicalCtaInstruction(surfaceId);
    const mutatedInstruction = replaceRequiredLiteral(canonicalInstruction, from, to, `current ${label} clause`);
    const mutations = Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => {
      let output = mutateJsonArrayField(content, 'buyer_visible_cta_inventory', (rows) => rows.map((row) => {
        if (!row.startsWith(`${surfaceId}|`)) return row;
        const parts = row.split('|');
        parts[3] = mutatedInstruction;
        return parts.join('|');
      }));
      if ((key === 'briefPath' || key === 'draftPath') && surfaceId === 'fallback-do-not-send-01') {
        output = mutateJsonArrayField(output, 'semantic_emphasis_plan', (rows) => rows.map((row) => row.includes(canonicalInstruction)
          ? row.replace(canonicalInstruction, mutatedInstruction)
          : row));
      }
      if (key === 'draftPath') output = transformBody(output, (body) => replaceRequiredLiteral(body, canonicalInstruction, mutatedInstruction, `current ${label}`));
      return output;
    }]));
    expectBlockMatching(t, mutations, pattern);
  });
}


function fallbackContractParts(content) {
  const match = fieldPattern('cta_fallback_route_contract').exec(content);
  assert.ok(match, 'canonical fixture must contain cta_fallback_route_contract');
  const raw = match[0].slice(match[0].indexOf(':') + 1).trim();
  const value = raw.startsWith('"') ? JSON.parse(raw) : raw;
  return value.split('|');
}

function mutateFallbackContract(content, mutate) {
  const parts = fallbackContractParts(content);
  const next = mutate([...parts]);
  assert.equal(Array.isArray(next), true, 'fallback contract mutation must return slots');
  return replaceField(content, 'cta_fallback_route_contract', JSON.stringify(next.join('|')));
}

for (const [label, mutate, pattern] of [
  ['16 slots', (parts) => parts.slice(0, -1), /must contain exactly 17 non-empty pipe-delimited slots/],
  ['18 slots', (parts) => [...parts, 'extra'], /must contain exactly 17 non-empty pipe-delimited slots/],
  ['unknown route status', (parts) => (parts[0] = 'route-ready', parts), /route-status must be verified\|unverified-unavailable\|not-applicable/],
  ['invalid required-inputs mode', (parts) => (parts[3] = 'copy-primary-inputs', parts), /required-inputs-mode must be same-as-cta-required-inputs\|none/],
  ['unverified endpoint', (parts) => (parts[1] = 'https://example.test/contact/unverified', parts), /unverified-unavailable requires endpoint=not-applicable/],
  ['unverified noncanonical axis', (parts) => (parts[5] = 'executed', parts), /unverified-unavailable reference axis must be not-run\|missing\|block\|not-applicable/],
]) {
  test(`V16 fallback-route closed schema rejects ${label}`, (t) => {
    expectBlockMatching(t, Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => mutateFallbackContract(content, mutate)])), pattern);
  });
}

test('V16 fallback-route closed schema requires the field in every record', (t) => {
  expectBlockMatching(t, { publishPath: (content) => removeField(content, 'cta_fallback_route_contract') }, /closed fallback-route schema requires cta_fallback_route_contract|field cta_fallback_route_contract is required/);
});

test('V16 fallback-route contract requires exact four-record parity', (t) => {
  expectBlockMatching(t, {
    reviewPath: (content) => mutateFallbackContract(content, (parts) => (parts[4] = `${parts[4]} Review drift.`, parts)),
  }, /cta_fallback_route_contract must match the canonical Brief projection|cta_fallback_route_contract mismatch/);
});

test('V16 fallback-route not-applicable status requires all 17 slots to be not-applicable', (t) => {
  const invalid = Array(17).fill('not-applicable');
  invalid[4] = 'No external fallback is needed for this local self-check.';
  expectBlockMatching(t, allRecords('cta_fallback_route_contract', JSON.stringify(invalid.join('|'))), /route-status=not-applicable requires all 17 slots to be exact not-applicable/);
});

test('V16 verified fallback evidence fragment must contain its own exact endpoint', (t) => {
  expectBlockMatching(
    t,
    verifiedFallbackEvidenceMutations(),
    /verified capability evidence fragment .* must contain the exact fallback endpoint/,
    (dir) => setupVerifiedFallbackEvidence(dir, { capabilityEndpoint: 'https://example.test/contact/wrong-fallback' }),
  );
});

test('V16 verified fallback evidence cannot borrow a primary CTA evidence ref', (t) => {
  const primaryRef = 'search-evidence.md#reference-parity-gate';
  const refs = { ...verifiedFallbackEvidenceRefs, reference: primaryRef };
  const mutations = verifiedFallbackEvidenceMutations({ contractOptions: { refs } });
  for (const key of Object.keys(mutations)) {
    const prior = mutations[key];
    mutations[key] = (content) => replaceField(prior(content), 'cta_reference_evidence_refs', JSON.stringify([primaryRef]));
  }
  expectBlockMatching(
    t,
    mutations,
    /verified reference evidence ref must be independent from primary CTA evidence/,
    (dir) => setupVerifiedFallbackEvidence(dir),
  );
});

test('V16 verified fallback contract requires non-empty local refs for every evidence axis', (t) => {
  const refs = { ...verifiedFallbackEvidenceRefs, reference: 'not-applicable' };
  expectBlockMatching(
    t,
    verifiedFallbackEvidenceMutations({ contractOptions: { refs } }),
    /verified reference-refs requires one or more comma-separated local evidence refs|reference-refs (?:is missing; )?requires one or more comma-separated local evidence refs|reference-refs is missing; one or more comma-separated local evidence refs are required/,
    (dir) => setupVerifiedFallbackEvidence(dir),
  );
});

test('V16 different verified fallback endpoint cannot hide behind borrowed primary-route evidence', (t) => {
  const refs = { ...verifiedFallbackEvidenceRefs, reference: 'search-evidence.md#reference-parity-gate' };
  const mutations = verifiedFallbackEvidenceMutations({
    alternateEndpoint: 'https://example.test/contact/different-fallback',
    contractOptions: { refs },
  });
  for (const key of Object.keys(mutations)) {
    const prior = mutations[key];
    mutations[key] = (content) => replaceField(prior(content), 'cta_reference_evidence_refs', JSON.stringify([refs.reference]));
  }
  const result = validateArticlePackage(makeFixture(
    t,
    mutations,
    (dir) => setupVerifiedFallbackEvidence(dir),
  ));
  assert.equal(result.ok, false, 'different endpoint plus borrowed primary evidence must block');
  const problems = result.problems.join('\n');
  assert.match(problems, /verified reference evidence ref must be independent from primary CTA evidence/);
  assert.match(problems, /every buyer-visible fallback instruction must display the exact verified contract endpoint|buyer-visible verified fallback endpoint .* must exactly match/);
  assert.doesNotMatch(problems, /synthetic cta_(?:reachability|capability) axis must be not-run \+ missing \+ block/);
});

test('V16 verified fallback buyer-visible endpoint must exactly match the contract endpoint', (t) => {
  expectBlockMatching(
    t,
    verifiedFallbackEvidenceMutations({ alternateEndpoint: 'https://example.test/contact/different-fallback' }),
    /every buyer-visible fallback instruction must display the exact verified contract endpoint|buyer-visible verified fallback endpoint .* must exactly match/,
    (dir) => setupVerifiedFallbackEvidence(dir),
  );
});

test('V16 early unsafe CTA is blocked even when the final CTA remains safe', (t) => {
  expectBlockMatching(t, {
    draftPath: (content) => transformBody(content, (body) => replaceRequiredLiteral(
      body,
      canonicalCtaInstruction('fallback-route-request-01'),
      'If the primary route is unavailable, do not send the packet through an unverified channel. Alternatively, send it through the verified engineering channel owned by Applications Engineering.',
      'early unsafe CTA',
    )),
  }, /unverified fallback contract is contradicted by an unsafe buyer-visible CTA section/);
});

test('V16 unverified fallback blocks the two-sentence verified-channel route instruction', (t) => {
  expectBlockMatching(t, {
    draftPath: (content) => transformBody(content, (body) => replaceRequiredLiteral(
      body,
      canonicalCtaInstruction('fallback-route-request-01'),
      'If the primary route is unavailable, do not send the packet through an unverified channel. A verified engineering channel is available from Applications Engineering. Route the packet there.',
      'two-sentence verified route attack',
    )),
  }, /unverified fallback contract is contradicted by an unsafe buyer-visible CTA section/);
});

test('V16 cta_receiving_owner rejects a pure job title across all records', (t) => {
  expectBlockMatching(t, allRecords('cta_receiving_owner', '"Applications Engineering Lead"'), /cta_receiving_owner must be a stable owner ID or person name plus role|field cta_receiving_owner must be a stable owner ID or person name plus role/);
});

test('V16 role_handoff_contracts receiving_owner rejects a pure job title', (t) => {
  const mutations = Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => mutateJsonArrayField(content, 'role_handoff_contracts', (rows) => rows.map((row, index) => {
    if (index !== 0) return row;
    const parts = row.split('|');
    parts[5] = 'Applications Engineering Lead';
    return parts.join('|');
  }))]));
  expectBlockMatching(t, mutations, /role_handoff_contracts receiving_owner must be a stable owner ID or person name plus role|field role_handoff_contracts receiving_owner must be a stable owner ID or person name plus role/);
});

test('V16 stable owner ID is accepted by both CTA and role-handoff owner gates', (t) => {
  const stableOwner = 'owner:avery-chen-001';
  const mutations = Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => {
    let output = replaceField(content, 'cta_receiving_owner', JSON.stringify(stableOwner));
    output = mutateJsonArrayField(output, 'role_handoff_contracts', (rows) => rows.map((row, index) => {
      if (index !== 0) return row;
      const parts = row.split('|');
      parts[5] = stableOwner;
      return parts.join('|');
    }));
    return output;
  }]));
  const result = validateArticlePackage(makeFixture(t, mutations));
  assert.equal(result.problems.some((problem) => /stable owner ID or person name plus role/.test(problem)), false, result.problems.join('\n'));
});

test('V16 Review gate matrix rejects done-locally through the closed execution allowlist', (t) => {
  expectBlockMatching(t, {
    reviewPath: (content) => replaceRequiredLiteral(content, '| `executed` | `synthetic-only` | `pass` |', '| `done-locally` | `synthetic-only` | `pass` |', 'done-locally table axis'),
  }, /evidence-axis table execution value must use the closed canonical allowlist; received done-locally/);
});

test('V16 Review inline-code evidence axis rejects done-locally', (t) => {
  expectBlockMatching(t, {
    reviewPath: (content) => `${content}\n\nAdversarial probe: \`cta_reference_check_execution_status=done-locally\`.\n`,
  }, /inline-code cta_reference_check_execution_status must use the closed canonical allowlist; received done-locally/);
});

function expectedContentTypeFamily(value) {
  const normalized = String(value).toLowerCase();
  if (/\b(?:calculator|estimator|calculation|sizing tool|roi tool|cost model)\b/.test(normalized)) return 'calculator';
  if (/\b(?:diagnostic|diagnosis|troubleshoot(?:ing)?|root[- ]cause|fault[- ]isolation|failure analysis)\b/.test(normalized)) return 'diagnostic';
  if (/\b(?:checklist|check list|readiness check|audit checklist|inspection checklist)\b/.test(normalized)) return 'checklist';
  if (/\b(?:comparison|compare|versus|vs\.?|matrix|decision table|selection table)\b/.test(normalized)) return 'comparison';
  if (/\b(?:case study|customer story|success story|implementation story|project story)\b/.test(normalized)) return 'case-study';
  if (/\b(?:product(?: page)?|category(?: page| hub)?|landing page|solution page|product hub|collection page)\b/.test(normalized)) return 'product-landing';
  if (/\b(?:guide|how[- ]to|tutorial|playbook|step[- ]by[- ]step|handbook|explainer)\b/.test(normalized)) return 'guide';
  return '';
}

function expectedContentTypeMutations(value, draftAppend = '') {
  const family = expectedContentTypeFamily(value);
  return Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => {
    const field = key === 'briefPath' || key === 'draftPath' ? 'expected_content_type' : 'expected_content_type_snapshot';
    let output = replaceField(content, field, JSON.stringify(value));
    if ((key === 'briefPath' || key === 'publishPath') && family) output = replaceField(output, 'content_family_matches', JSON.stringify([family]));
    if (key === 'draftPath' && draftAppend) output = transformBody(output, (body) => `${body.trimEnd()}

${draftAppend.trim()}
`);
    return output;
  }]));
}

for (const [label, value, appendix] of [
  ['calculator', 'calculator with bounded engineering inputs and output', `## Engineering sizing calculator\n\nInputs: loaded mass in kg and duty percentage. Output: a bounded load estimate.\n\nEstimated load = 180 kg * 20 percent.`],
  ['guide/how-to', 'guide/how-to for preparing a bounded readiness packet', `## How-to guide\n\n1. Record the operating boundary.\n2. Check the required evidence.\n3. Stop when an input is missing.`],
  ['case study', 'case study with a bounded evidence lesson', `## Challenge\n\nThe input packet was incomplete.\n\n## Approach\n\nThe team aligned the evidence fields.\n\n## Result\n\nThe next validation task became explicit without a performance claim.`],
  ['product/category/landing', 'product/category/landing page with a bounded candidate route', `## Product category options\n\n| Product category | Application boundary | Next decision |\n|---|---|---|\n| Cargo hub-motor candidate family | Repeated-grade cargo e-bike application | Review load, wheel, duty, electrical, and interface evidence |\n| Unsupported commercial scope | Outside the documented candidate boundary | Stop and record the unsupported scope |`],
]) {
  test(`V16 synthetic expected content type observably supports ${label}`, (t) => {
    expectAxisHasNoFocusedProblem(t, expectedContentTypeMutations(value, appendix), /expected_content_type|content family|SERP result_type/);
  });
}

test('V16 expected content type is required in Brief and Draft', (t) => {
  expectBlockMatching(t, { briefPath: (content) => removeField(content, 'expected_content_type') }, /expected_content_type/);
  expectBlockMatching(t, { draftPath: (content) => removeField(content, 'expected_content_type') }, /expected_content_type/);
});

test('V16 Brief and Draft expected content type cannot drift', (t) => {
  expectBlockMatching(t, { draftPath: (content) => replaceField(content, 'expected_content_type', '"guide/how-to"') }, /expected_content_type must match the canonical Brief projection|expected_content_type mismatch/);
});

test('V16 Review and Publish expected content type snapshots must project the Brief exactly', (t) => {
  expectBlockMatching(t, { reviewPath: (content) => replaceField(content, 'expected_content_type_snapshot', '"guide/how-to"') }, /expected_content_type.*projection mismatch|expected_content_type_snapshot/);
  expectBlockMatching(t, { publishPath: (content) => replaceField(content, 'expected_content_type_snapshot', '"guide/how-to"') }, /expected_content_type.*projection mismatch|expected_content_type_snapshot/);
});

test('V16 expected content type rejects unsupported tokens and unimplemented Draft shape', (t) => {
  expectBlockMatching(t, expectedContentTypeMutations('news carousel'), /expected_content_type must map to exactly one content family/);
  expectBlockMatching(t, expectedContentTypeMutations('calculator with bounded engineering inputs and output'), /does not observably implement declared expected_content_type family calculator/);
});

for (const field of [
  'serp_content_type_parity_verdict',
  'soft_path_route_safety_verdict',
  'all_buyer_visible_cta_sections_evidence_parity_verdict',
  'cross_cta_instruction_consistency_verdict',
]) {
  test(`V16 fatal ${field} must be pass and exact across Review and Publish`, (t) => {
    const isSerpParity = field === 'serp_content_type_parity_verdict';
    const base = isSerpParity ? completeProductionLearnMutations() : {};
    const setup = isSerpParity ? setupCompleteProductionLearnEvidence : undefined;
    const passPattern = isSerpParity
      ? /serp_content_type_parity_verdict must be pass for the available SERP evidence scope/
      : new RegExp(`applicable article requires fatal ${field}=pass`);
    const applyBase = (key, content) => base[key] ? base[key](content) : content;
    expectBlockMatching(t, {
      ...base,
      reviewPath: (content) => replaceField(applyBase('reviewPath', content), field, '"block"'),
      publishPath: (content) => replaceField(applyBase('publishPath', content), field, '"block"'),
    }, passPattern, setup);
    expectBlockMatching(t, {
      ...base,
      reviewPath: (content) => replaceField(applyBase('reviewPath', content), field, '"block"'),
    }, new RegExp(`${field} must match the canonical Brief projection|${field} mismatch`), setup);
  });
}

test('V16 production SERP checklist result type matches the declared expected content family', (t) => {
  expectAxisHasNoFocusedProblem(
    t,
    v12ProductionSerpMutations(),
    /expected_content_type|SERP-format evidence .* result_type cannot be mapped|conflicts with production SERP result_types/,
    (dir) => setupV12SerpEvidence(dir, { resultTypes: ['checklist'] }),
  );
});

test('V16 production SERP result type conflicts with the declared expected content family', (t) => {
  expectBlockMatching(
    t,
    v12ProductionSerpMutations({ primaryDominantType: 'guide' }),
    /expected_content_type family checklist conflicts with primary query dominant SERP family guide/,
    (dir) => setupV12SerpEvidence(dir, { resultTypes: ['checklist', 'guide'], primaryDominantType: 'guide' }),
  );
});

test("V16 production SERP raw result types must use the canonical enum", (t) => {
  const serpResultTypes = ["checklist", "checklist", "checklist", "guide", "news carousel"];
  const expectedProblem = /SERP-format evidence production-serp-format-evidence\.md#serp-format result_types item 5 must be an exact canonical SERP result type/;
  expectBlockSatisfying(
    t,
    overrideMutationFields(completeProductionLearnMutations(), {
      serp_primary_query_dominant_result_type: "checklist",
      serp_primary_query_result_type_counts: ["checklist|3", "guide|1", "news carousel|1"],
    }),
    (problems) => {
      assert.equal(problems.length, 1, `non-canonical raw-result fixture must have exactly one problem:\n${problems.join("\n")}`);
      assert.match(problems[0], expectedProblem);
    },
    (dir) => setupCompleteProductionLearnEvidence(dir, {
      serpResultTypes,
      serpPrimaryDominantType: "checklist",
    }),
  );
});

test('V16 production evidence_result cannot use verified as a second canonical enum', (t) => {
  const mutations = {};
  for (const key of Object.keys(fixtureNames)) {
    mutations[key] = (content) => {
      let output = replaceField(content, 'evidence_scope', '"production"');
      output = replaceField(output, 'cta_reachability_check_execution_status', '"executed"');
      output = replaceField(output, 'cta_reachability_evidence_result', '"verified"');
      output = replaceField(output, 'cta_reachability_gate_verdict', '"pass"');
      return output;
    };
  }
  expectBlockMatching(t, mutations, /production cta_reachability axis requires executed \+ confirmed \+ pass/);
});

test('V16 SOP keeps buyer receiving owner separate from external route owner', () => {
  const sop = readFileSync(new URL('../PLAYBOOKS/id-0003-b2b-article-optimization-sop.md', import.meta.url), 'utf8');
  assert.match(sop, /四记录必须 exact parity 投影 `cta_from_role`、`cta_to_role`、`cta_receiving_task`、`cta_receiving_owner`/);
  assert.match(sop, /第六段 `receiving_owner == cta_receiving_owner`/);
  assert.match(sop, /`cta_owner` 单独表示 external route/);
  assert.doesNotMatch(sop, /`owner == cta_owner`/);
  assert.doesNotMatch(sop, /CTA 非跨角色时三个字段/);
});

// P1 contract matrix: canonical decision/conversion maps, evidence-backed SERP counts,
// fail-closed CLI portability, verdict consistency, CTA inventory, and mobile evidence.

function setFieldAcrossAllRecords(field, value) {
  return Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => replaceField(content, field, value)]));
}

function mutateArrayAcrossAllRecords(field, mutate) {
  return Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => mutateJsonArrayField(content, field, mutate)]));
}

test('P1 absolute copied validator under tmp fails closed on a missing package file through stderr', (t) => {
  const root = mkdtempSync(join(tmpdir(), 'article-validator-copy-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const scriptsDir = join(root, 'scripts');
  const adapterDir = join(root, 'ADAPTERS', 'cms', 'allincms');
  mkdirSync(scriptsDir, { recursive: true });
  mkdirSync(adapterDir, { recursive: true });
  copyFileSync(fileURLToPath(new URL('./validate-article-package.mjs', import.meta.url)), join(scriptsDir, 'validate-article-package.mjs'));
  copyFileSync(fileURLToPath(new URL('./front-matter.mjs', import.meta.url)), join(scriptsDir, 'front-matter.mjs'));
  copyFileSync(fileURLToPath(new URL('../ADAPTERS/cms/allincms/article-content-formats.mjs', import.meta.url)), join(adapterDir, 'article-content-formats.mjs'));
  const missing = join(root, 'missing.md');
  const result = spawnSync(process.execPath, [
    join(scriptsDir, 'validate-article-package.mjs'),
    '--brief', missing, '--draft', missing, '--review', missing, '--publish', missing,
  ], { encoding: 'utf8' });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /ARTICLE_PACKAGE_BLOCK/);
  assert.equal(result.stdout.includes('ARTICLE_PACKAGE_BLOCK'), false, 'BLOCK marker must be written to stderr');
});

const canonicalDecisionMap = fixtureArray(fixtureNames.briefPath, 'article_decision_sequence_map');
const canonicalCtaMeasurementMap = fixtureArray(fixtureNames.briefPath, 'cta_measurement_map');

test('P1 CTA measurement contract baseline is consumed by the active validator', (t) => {
  expectAxisHasNoFocusedProblem(t, {}, /cta_measurement_map|conversion_measurement_plan_status|cta_measurement_plan_verdict/);
});

for (const key of Object.keys(fixtureNames)) {
  test(`P1 ${key} cannot omit cta_measurement_map`, (t) => {
    expectBlockMatching(t, { [key]: (content) => removeField(content, 'cta_measurement_map') }, /missing required CTA measurement field cta_measurement_map/);
  });
}

test('P1 CTA measurement projection must be byte-exact across all four records', (t) => {
  expectBlockMatching(t, {
    reviewPath: (content) => mutateJsonArrayField(content, 'cta_measurement_map', (rows) => rows.map((row, index) => index === 1 ? row.replace('30-days-after-production-enable', '31-days-after-production-enable') : row)),
  }, /cta_measurement_map must match the canonical Brief projection across all records using exact-raw-sequence/);
});

test('P1 applicable CTA measurement plan cannot use not-applicable', (t) => {
  expectBlockMatching(t, setFieldAcrossAllRecords('conversion_measurement_plan_status', '"not-applicable"'), /applicable CTA surfaces require conversion_measurement_plan_status=planned or active/);
});

test('P1 CTA measurement event names cannot be reused across lifecycle slots', (t) => {
  const attacked = canonicalCtaMeasurementMap.map((row, index) => index === 0 ? row.replace('cta_primary_review_submit', 'cta_primary_review_start') : row);
  expectBlockMatching(t, mutateArrayAcrossAllRecords('cta_measurement_map', () => attacked), /event names must not be reused across surfaces or lifecycle slots/);
});

test('P1 CTA measurement surface roles are ordered and exact', (t) => {
  const attacked = canonicalCtaMeasurementMap.map((row, index) => index === 1 ? row.replace('|soft|', '|fallback|') : row);
  expectBlockMatching(t, mutateArrayAcrossAllRecords('cta_measurement_map', () => attacked), /row 2 surface-role must exactly be soft/);
});

test('P1 CTA measurement evidence refs are required for the plan', (t) => {
  expectBlockMatching(t, mutateArrayAcrossAllRecords('cta_abandonment_measurement_refs', () => []), /CTA measurement plan requires local evidence refs/);
});

const canonicalConversionMap = fixtureArray(fixtureNames.briefPath, 'conversion_surface_map');

test('P1 canonical decision and conversion maps pass as exact four-record projections', (t) => {
  expectAxisHasNoFocusedProblem(t, {}, /article_decision_sequence_map|conversion_surface_map/);
});

for (const [label, mutate] of [
  ['missing row', (rows) => rows.slice(0, -1)],
  ['reordered rows', (rows) => [rows[1], rows[0], ...rows.slice(2)]],
  ['duplicate role', (rows) => [rows[0], rows[0], ...rows.slice(2)]],
  ['aliased role', (rows) => rows.map((row, index) => index === 0 ? row.replace(/^hook\|/, 'opening|') : row)],
]) {
  test(`P1 article decision sequence rejects ${label}`, (t) => {
    expectBlockMatching(t, mutateArrayAcrossAllRecords('article_decision_sequence_map', mutate), /article_decision_sequence_map/);
  });
}

test('P1 article decision sequence rejects downstream single-record drift', (t) => {
  expectBlockMatching(t, { publishPath: (content) => mutateJsonArrayField(content, 'article_decision_sequence_map', (rows) => rows.map((row, index) => index === 4 ? row.replace(/^act\|/, 'hook|') : row)) }, /article_decision_sequence_map.*(?:match|mismatch)|role must be act/);
});

test('P1 article decision sequence verdict block is consumed by fatal consistency', (t) => {
  expectBlockMatching(t, fatalConflictMutations('article_decision_sequence_verdict'), /fatal_gate_verdict=pass cannot coexist|overall_verdict=pass cannot coexist|production_readiness=ready cannot coexist/);
});

for (const [label, mutate] of [
  ['missing row', (rows) => rows.slice(0, -1)],
  ['reordered rows', (rows) => [rows[1], rows[0], rows[2]]],
  ['duplicate role', (rows) => [rows[0], rows[0], rows[2]]],
  ['aliased role', (rows) => rows.map((row, index) => index === 0 ? row.replace(/\|primary\|/, '|main|') : row)],
]) {
  test(`P1 conversion surface map rejects ${label}`, (t) => {
    expectBlockMatching(t, mutateArrayAcrossAllRecords('conversion_surface_map', mutate), /conversion_surface_map/);
  });
}

test('P1 conversion surface map rejects downstream single-record drift', (t) => {
  expectBlockMatching(t, { reviewPath: (content) => mutateJsonArrayField(content, 'conversion_surface_map', (rows) => rows.map((row, index) => index === 1 ? row.replace(/\|soft\|/, '|fallback|') : row)) }, /conversion_surface_map.*(?:match|mismatch)|role must be soft/);
});

test('P1 conversion surface verdict block is consumed by fatal consistency', (t) => {
  expectBlockMatching(t, fatalConflictMutations('conversion_surface_map_verdict'), /fatal_gate_verdict=pass cannot coexist|overall_verdict=pass cannot coexist|production_readiness=ready cannot coexist/);
});

test('P1 conversion surface not-applicable route still requires stage-specific rationale', (t) => {
  const attack = canonicalConversionMap.map((row, index) => {
    if (index !== 1) return row;
    const parts = row.split('|');
    parts[1] = 'generic outcome later'; parts[2] = 'somewhere later'; parts[3] = 'generic interaction'; parts[4] = 'not-applicable';
    return parts.join('|');
  });
  expectBlockMatching(t, setFieldAcrossAllRecords('conversion_surface_map', JSON.stringify(attack)), /route not-applicable requires a concrete stage-specific rationale/);
});

test('P1 production readiness scope is exact and cannot imply deferred frontend SEO pass', (t) => {
  expectBlockMatching(t, setFieldAcrossAllRecords('production_readiness_scope', '"full-seo-production"'), /production_readiness_scope must be cms-draft-content-contract/);
});

const fatalReviewVerdicts = [
  'query_contract_verdict', 'dominant_task_verdict', 'stage_contract_verdict', 'buyer_role_scope_verdict',
  'cross_role_delegation_verdict', 'cannibalization_verdict', 'information_gain_artifact_verdict',
  'information_gain_market_verdict', 'article_decision_sequence_verdict', 'conversion_surface_map_verdict',
  'hierarchy_scan_verdict', 'semantic_emphasis_verdict', 'overall_verdict',
];

function fatalConflictMutations(targetField) {
  const projectedVerdict = ['article_decision_sequence_verdict', 'conversion_surface_map_verdict'].includes(targetField);
  return Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => {
    let output = replaceField(content, 'fatal_gate_verdict', '"pass"');
    output = replaceField(output, 'production_readiness', '"ready"');
    if (projectedVerdict) output = replaceField(output, targetField, '"block"');
    if (key === 'reviewPath') {
      output = replaceField(output, 'overall_verdict', targetField === 'overall_verdict' ? '"block"' : '"pass"');
      if (!projectedVerdict && targetField !== 'overall_verdict') output = replaceField(output, targetField, '"block"');
    }
    return output;
  }]));
}
for (const field of fatalReviewVerdicts) {
  test(`P1 fatal verdict ${field}=block conflicts with forged fatal pass and readiness`, (t) => {
    expectBlockMatching(t, fatalConflictMutations(field), /fatal_gate_verdict=pass cannot coexist|production_readiness=ready cannot coexist|overall_verdict=pass cannot coexist|requires applicable fatal/);
  });
}

for (const invalid of ['pass-for-fixture-structure', 'PASS', 'approved', 'true', 'pending', '']) {
  for (const field of ['hierarchy_scan_verdict', 'semantic_emphasis_verdict', 'article_decision_sequence_verdict', 'conversion_surface_map_verdict']) {
    test(`P1 closed verdict enum rejects ${JSON.stringify(invalid)} for ${field}`, (t) => {
      expectBlockMatching(t, { reviewPath: (content) => replaceField(content, field, JSON.stringify(invalid)) }, /closed verdict enum pass, block, or not-applicable|must be pass or block/);
    });
  }
}

const sixFourTypes = ['checklist', 'checklist', 'checklist', 'checklist', 'checklist', 'checklist', 'guide', 'guide', 'guide', 'guide'];
const fiveFiveTypes = ['checklist', 'checklist', 'checklist', 'checklist', 'checklist', 'guide', 'guide', 'guide', 'guide', 'guide'];
const fourSixTypes = ['checklist', 'checklist', 'checklist', 'checklist', 'guide', 'guide', 'guide', 'guide', 'guide', 'guide'];

test('P1 primary SERP minority cannot pass because a supporting content type matches', (t) => {
  expectBlockMatching(
    t,
    v12ProductionSerpMutations({ primaryDominantType: 'guide', primaryDominantCount: '6', resultTypeCounts: ['checklist|4', 'guide|6'] }),
    /expected_content_type family checklist conflicts with primary query dominant SERP family|primary-query dominant/,
    (dir) => setupV12SerpEvidence(dir, { resultTypes: fourSixTypes, primaryDominantType: 'guide', primaryDominantCount: 6 }),
  );
});

test('P1 primary SERP 0.50 boundary remains blocked', (t) => {
  expectBlockMatching(
    t,
    v12ProductionSerpMutations({ primaryDominantCount: '5', primaryDominanceThreshold: '0.50', resultTypeCounts: ['checklist|5', 'guide|5'] }),
    /dominance_threshold must be > 0\.50|strict majority|dominant count must satisfy/,
    (dir) => setupV12SerpEvidence(dir, { resultTypes: fiveFiveTypes, primaryDominantCount: 5, primaryDominanceThreshold: 0.50 }),
  );
});

test('P1 forged SERP result type counts cannot override observed result_types', (t) => {
  expectBlockMatching(
    t,
    v12ProductionSerpMutations({ primaryDominantCount: '6', resultTypeCounts: ['checklist|7', 'guide|3'] }),
    /result_type_counts must exactly equal counts recomputed/,
    (dir) => setupV12SerpEvidence(dir, { resultTypes: sixFourTypes, primaryDominantCount: 6 }),
  );
});

test('P1 self-reported SERP dominant type cannot override recomputed observations', (t) => {
  expectBlockMatching(
    t,
    v12ProductionSerpMutations({ primaryDominantType: 'guide', primaryDominantCount: '7' }),
    /dominant_result_type must equal the recomputed dominant result type checklist/,
    (dir) => setupV12SerpEvidence(dir, { primaryDominantType: 'guide', primaryDominantCount: 7 }),
  );
});


const supportingSerpFamilyConflictRows = [
  'cargo e-bike hub motor engineering readiness checklist|5|guide|3|0.60|pass|v12-serp-evidence.md#supporting-query-1',
  'cargo hub motor engineering review inputs|5|checklist|3|0.60|pass|v12-serp-evidence.md#supporting-query-2',
  '20 inch cargo hub motor engineering readiness inputs|5|checklist|3|0.60|pass|v12-serp-evidence.md#supporting-query-3',
];

for (const [label, oracle] of [
  ['primary-query dominant family', /supporting SERP row 1 family guide conflicts with primary query dominant SERP family checklist/],
  ['expected_content_type family', /supporting SERP row 1 family guide conflicts with expected_content_type family checklist/],
]) {
  test(`P1 supporting SERP dominant family independently matches ${label}`, (t) => {
    expectBlockMatching(
      t,
      v12ProductionSerpMutations({ supportingRows: supportingSerpFamilyConflictRows }),
      oracle,
      (dir) => setupV12SerpEvidence(dir, { supportingDominantTypes: ['guide', 'checklist', 'checklist'] }),
    );
  });
}

const unsafeEndpoint = 'https://example.test/contact/unverified-direct';
for (const [label, injected] of [
  ['before first H2', `Submit the packet now through ${unsafeEndpoint}.\n\n`],
  ['ordinary paragraph', `Send the project data through ${unsafeEndpoint}.`],
  ['list', `- Share the controlled files through ${unsafeEndpoint}.`],
  ['table', `| Action | Route |\n| --- | --- |\n| Upload the packet | ${unsafeEndpoint} |`],
  ['strong', `**Contact the engineering team through ${unsafeEndpoint}.**`],
  ['Markdown link', `[Submit the engineering packet](${unsafeEndpoint}).`],
  ['request Markdown link', `[Request the engineering review](${unsafeEndpoint}).`],
  ['book action', `Book the engineering review through ${unsafeEndpoint}.`],
  ['download action', `Download the submission form from ${unsafeEndpoint}.`],
]) {
  test(`P1 CTA inventory blocks early unsafe ${label} even with safe final fallback`, (t) => {
    expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => label === 'before first H2' ? `${injected}${body}` : body.replace('## Why wattage-first selection may create avoidable rework', `## Why wattage-first selection may create avoidable rework\n\n${injected}`)) }, /unverified primary CTA route must not directly link or instruct/);
  });
}

test('P1 CTA inventory blocks a synchronized row deletion when the body surface remains', (t) => {
  const rows = fixtureArray(fixtureNames.briefPath, 'buyer_visible_cta_inventory');
  expectBlockMatching(t, allRecords('buyer_visible_cta_inventory', JSON.stringify(rows.slice(1))), /buyer-visible CTA instruction is missing from buyer_visible_cta_inventory|body CTA surface count/);
});

test('P1 CTA inventory blocks synchronized reorder across all four records', (t) => {
  const rows = fixtureArray(fixtureNames.briefPath, 'buyer_visible_cta_inventory');
  const reordered = [rows[1], rows[0], ...rows.slice(2)];
  expectBlockMatching(t, allRecords('buyer_visible_cta_inventory', JSON.stringify(reordered)), /rows must follow publishable-body order|reordered or duplicated/);
});

test('P1 CTA inventory blocks synchronized duplicate surface rows', (t) => {
  const rows = fixtureArray(fixtureNames.briefPath, 'buyer_visible_cta_inventory');
  expectBlockMatching(t, allRecords('buyer_visible_cta_inventory', JSON.stringify([...rows, rows[0]])), /surface-id must be unique|reordered or duplicated|instruction must appear exactly once/);
});

for (const [label, slot, replacement, pattern] of [
  ['instruction', 3, 'Create and send a different unverified packet now.', /buyer_visible_cta_inventory must match the canonical Brief projection|instruction must (?:appear|resolve) exactly once|missing from buyer_visible_cta_inventory/],
  ['destination', 4, 'https://example.test/solutions/drifted-destination', /buyer_visible_cta_inventory must match the canonical Brief projection|destination|planned internal-link target/],
  ['owner', 5, 'Different Route Owner (synthetic)', /buyer_visible_cta_inventory must match the canonical Brief projection|owner|canonical cta_owner/],
]) {
  test(`P1 CTA inventory blocks single-record ${label} drift`, (t) => {
    expectBlockMatching(t, { publishPath: (content) => mutateJsonArrayField(content, 'buyer_visible_cta_inventory', (rows) => rows.map((row, index) => {
      if (index !== 0) return row;
      const parts = row.split('|');
      parts[slot] = replacement;
      return parts.join('|');
    })) }, pattern);
  });
}

test('P1 CTA inventory blocks a newly inserted unenumerated early buyer action', (t) => {
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => body.replace('## Why wattage-first selection may create avoidable rework', '## Why wattage-first selection may create avoidable rework\n\nCreate a separate readiness request worksheet for the supplier review.')) }, /buyer-visible CTA instruction is missing from buyer_visible_cta_inventory/);
});

test('P1 undeclared URL or email endpoint text is blocked even without a direct-action verb', (t) => {
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => body.replace('## Why wattage-first selection may create avoidable rework', `## Why wattage-first selection may create avoidable rework\n\nReference identifiers only: https://example.test/contact/reference-only and route-owner@example.com.`)) }, /buyer-visible plain or linked URL is undeclared|unverified primary CTA route must not directly link or instruct/);
});


test('P1 a safe route-status sentence cannot launder a separate unverified endpoint instruction', (t) => {
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => body.replace(
    '## Why wattage-first selection may create avoidable rework',
    `## Why wattage-first selection may create avoidable rework

After a verified route is returned, the review status will be recorded. Send the packet through ${unsafeEndpoint}.`,
  )) }, /unverified primary CTA route must not directly link or instruct/);
});

test('P1 the canonical post-verification CTA boundary remains accepted', (t) => {
  expectAxisHasNoFocusedProblem(t, {}, /primary-bounded-review-01 unverified route instruction must visibly preserve/);
});

test('P1 a post-verification CTA boundary without the verified qualifier is blocked', (t) => {
  const unsafeInstruction = 'After a route is returned, copy this five-input packet into that route for Avery Chen, Applications Engineering Lead; the request is not an RFQ.';
  const mutations = Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => {
    let output = mutateJsonArrayField(content, 'buyer_visible_cta_inventory', (rows) => rows.map((row) => {
      if (!row.startsWith('primary-bounded-review-01|')) return row;
      const parts = row.split('|');
      parts[3] = unsafeInstruction;
      return parts.join('|');
    }));
    if (key === 'draftPath') output = transformBody(output, (body) => replaceRequiredLiteral(body, canonicalCtaInstruction('primary-bounded-review-01'), unsafeInstruction, 'missing verified qualifier'));
    return output;
  }]));
  expectBlockMatching(t, mutations, /primary-bounded-review-01 unverified route instruction must visibly preserve the do-not-send or verified-route boundary/);
});

test('P1 diagnostic prose using can build evidence is not misclassified as an imperative CTA', (t) => {
  expectAxisHasNoFocusedProblem(t, { draftPath: (content) => transformBody(content, (body) => body.replace(
    '## Why wattage-first selection may create avoidable rework',
    `## Why wattage-first selection may create avoidable rework

The engineering team can build evidence over time as validated duty-cycle results arrive.`,
  )) }, /buyer-visible CTA instruction is missing from buyer_visible_cta_inventory/);
});

for (const field of [
  'cta_destination', 'cta_owner',
  'cta_reference_check_execution_status', 'cta_reference_evidence_result', 'cta_reference_gate_verdict', 'cta_reference_evidence_refs',
  'cta_reachability_check_execution_status', 'cta_reachability_evidence_result', 'cta_reachability_gate_verdict', 'cta_reachability_evidence_refs',
  'cta_capability_check_execution_status', 'cta_capability_evidence_result', 'cta_capability_gate_verdict', 'cta_capability_evidence_refs',
]) {
  test(`P1 primary CTA canonical projection rejects single-record drift in ${field}`, (t) => {
    const current = field.endsWith('_refs') ? '["search-evidence.md#fixture-buyer-task-evidence"]' : '"drifted-value"';
    expectBlockMatching(t, { publishPath: (content) => replaceField(content, field, current) }, new RegExp(`${field}.*(?:match|mismatch)`));
  });
}

for (const [label, mutation] of [
  ['missing field', { briefPath: (content) => removeField(content, 'frontend_deferred_blocks') }],
  ['extra item', { briefPath: (content) => mutateJsonArrayField(content, 'frontend_deferred_blocks', (rows) => [...rows, 'open-graph']) }],
  ['single-record drift', { publishPath: (content) => mutateJsonArrayField(content, 'frontend_deferred_blocks', (rows) => rows.slice(0, -1)) }],
]) {
  test(`P1 frontend_deferred_blocks rejects ${label}`, (t) => {
    expectBlockMatching(t, mutation, /frontend_deferred_blocks/);
  });
}

function rewriteEvidenceDigest(content) {
  const closing = content.indexOf('\n---\n', 4);
  assert.notEqual(closing, -1, 'evidence record must have closing frontmatter');
  const body = content.slice(closing + 5);
  const digest = createHash('sha256').update(body).digest('hex');
  return replaceField(content, 'digest', `sha256:${digest}`);
}

function mutateEvidenceFile(path, mutateBody) {
  const content = readFileSync(path, 'utf8');
  const closing = content.indexOf('\n---\n', 4);
  assert.notEqual(closing, -1);
  const body = content.slice(closing + 5);
  const mutatedBody = mutateBody(body);
  assert.notEqual(mutatedBody, body, 'evidence body mutation must change content');
  writeFileSync(path, rewriteEvidenceDigest(`${content.slice(0, closing + 5)}${mutatedBody}`));
}

for (const [label, linePattern] of [
  ['check_id', /^check_id:.*\n/m],
  ['target_task', /^target_task:.*\n/m],
  ['accountable_owner', /^accountable_owner:.*\n/m],
  ['method/process', /^method:.*\n/m],
  ['observed_result', /^observed_result:.*\n/m],
  ['acceptance_criteria', /^acceptance_criteria:.*\n/m],
  ['capability_acceptance', /^capability_acceptance:.*\n/m],
]) {
  test(`P1 verified fallback structured evidence blocks missing ${label}`, (t) => {
    const missingFieldPattern = label === 'accountable_owner'
      ? /requires one non-empty accountable_owner|accountable_owner must exactly match (?:the canonical CTA owner|the declared accountable owner)/
      : new RegExp(`requires one non-empty ${label === 'method/process' ? 'method' : label}|check_id must be`);
    expectBlockMatching(t, verifiedFallbackEvidenceMutations(), missingFieldPattern, (dir) => {
      setupVerifiedFallbackEvidence(dir);
      mutateEvidenceFile(join(dir, 'fallback-route-evidence.md'), (body) => replaceRequiredLiteral(body, linePattern, '', `fallback ${label}`));
    });
  });
}

test('P1 verified fallback blocks a missing local evidence ref', (t) => {
  const refs = { ...verifiedFallbackEvidenceRefs, reference: 'not-applicable' };
  expectBlockMatching(t, verifiedFallbackEvidenceMutations({ contractOptions: { refs } }), /reference-refs.*(?:local evidence refs|local relative evidence paths|must contain one local ref|fragment)/, setupVerifiedFallbackEvidence);
});

function productionReadyMobileMutations(overrides = {}) {
  const defaults = {
    evidence_scope: 'production', structure_review_verdict: 'pass', production_evidence_review_verdict: 'pass',
    fatal_gate_verdict: 'pass', production_readiness: 'ready', release_decision: 'ready-for-cms-draft', operation_mode: 'dry-run',
    mobile_visual_check_execution_status: 'executed', mobile_visual_evidence_result: 'confirmed', mobile_visual_gate_verdict: 'pass',
    mobile_visual_evidence_refs: ['mobile-readability-evidence.md#mobile-readability'],
  };
  const values = { ...defaults, ...overrides };
  const mutations = Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => {
    let output = content;
    for (const [field, value] of Object.entries(values)) output = replaceField(output, field, JSON.stringify(value));
    if (key === 'reviewPath') {
      output = replaceField(output, 'reviewer_identity', '"Taylor Morgan, Independent Buyer Review Lead"');
      output = replaceField(output, 'visual_decision_assets_verdict', '"pass"');
      for (const field of fatalReviewVerdicts) output = replaceField(output, field, '"pass"');
    }
    return output;
  }]));
  return mutations;
}

function setupMobileReadabilityEvidence(dir, overrides = {}) {
  const values = {
    evidenceKind: 'mobile-readability', checkId: 'mobile-readability',
    targetUrl: 'https://example.test/guides/cargo-hub-motor-engineering-readiness-checklist',
    targetRole: 'article-page',
    targetTaskField: 'target_task',
    targetTask: '320px mobile readability review for Cargo Hub Motor Engineering Readiness Checklist: 5 Inputs Before Review',
    accountableOwnerField: 'accountable_owner',
    accountableOwner: 'Taylor Morgan, Independent Buyer Review Lead',
    methodField: 'method',
    viewportField: 'viewport_width_px', viewportValue: '320',
    renderTarget: 'https://example.test/guides/cargo-hub-motor-engineering-readiness-checklist',
    screenshotOrTraceField: 'screenshot_or_trace_ref',
    screenshotOrTraceRef: 'mobile-readability-trace.json',
    artifactDigest: '',
    ...overrides,
  };
  const trace = JSON.stringify({ viewport_width_px: 320, target_url: values.targetUrl, result: 'readable' }, null, 2);
  writeFileSync(join(dir, 'mobile-readability-trace.json'), trace);
  const artifactDigest = values.artifactDigest || createHash('sha256').update(trace).digest('hex');
  const body = `# Mobile readability evidence

## Mobile readability

check_id: ${values.checkId}
target_url: ${values.targetUrl}
target_role: ${values.targetRole}
${values.targetTaskField}: ${values.targetTask}
${values.accountableOwnerField}: ${values.accountableOwner}
observed_at: 2026-08-02T00:00:00Z
${values.methodField}: independently rendered and inspected the article at the exact narrow mobile viewport
observed_result: headings, paragraphs, lists, tables, and CTA copy remained readable without hidden content
acceptance_criteria: all publishable article hierarchy and conversion copy remains readable without horizontal page scrolling
capability_acceptance: the exact article render passed the bounded 320px readability acceptance review
${values.viewportField}: ${values.viewportValue}
render_target: ${values.renderTarget}
readability_result: readable hierarchy, stacked decision content, and usable CTA copy were confirmed at the target viewport
${values.screenshotOrTraceField}: ${values.screenshotOrTraceRef}
artifact_digest: sha256:${artifactDigest}
producer: Mobile Rendering Evidence Producer
producer_id: wco-mobile-render-producer-001
independent_reviewer: Independent Mobile Readability Reviewer
independent_reviewer_id: wco-mobile-reviewer-001
`;
  const digest = createHash('sha256').update(body).digest('hex');
  writeFileSync(join(dir, 'mobile-readability-evidence.md'), `---
title: Mobile readability evidence
record_type: evidence-record
evidence_scope: production
source: independent endpoint-specific mobile render review
observed_at: 2026-08-02T00:00:00Z
captured_at: 2026-08-02T00:00:00Z
digest: sha256:${digest}
evidence_kind: ${values.evidenceKind}
---
${body}`);
}

test('P1 production-ready mobile evidence complete positive reaches the canonical mobile gate', (t) => {
  expectAxisHasNoFocusedProblem(t, productionReadyMobileMutations(), /mobile_visual|mobile-readability|viewport_width|render_target/, setupMobileReadabilityEvidence);
});


test('P1 mobile artifact digest must match the referenced trace bytes', (t) => {
  expectBlockMatching(t, productionReadyMobileMutations(), /artifact_digest must exactly match (?:artifact_ref|screenshot_or_trace_ref) bytes/g, (dir) => {
    setupMobileReadabilityEvidence(dir);
    writeFileSync(join(dir, 'mobile-readability-trace.json'), '{"viewport_width_px":320,"result":"replaced-after-review"}');
  });
});

test('P1 mobile evidence rejects a stale but well-formed artifact digest', (t) => {
  expectBlockMatching(t, productionReadyMobileMutations(), /artifact_digest must exactly match (?:artifact_ref|screenshot_or_trace_ref) bytes/g, (dir) => {
    setupMobileReadabilityEvidence(dir, { artifactDigest: '0'.repeat(64) });
  });
});

test('P1 mobile evidence rejects a truncated artifact with the old digest', (t) => {
  expectBlockMatching(t, productionReadyMobileMutations(), /artifact_digest must exactly match (?:artifact_ref|screenshot_or_trace_ref) bytes/g, (dir) => {
    setupMobileReadabilityEvidence(dir);
    const target = join(dir, 'mobile-readability-trace.json');
    writeFileSync(target, readFileSync(target, 'utf8').slice(0, 16));
  });
});

for (const [label, mutations, evidenceOptions, pattern] of [
  ['missing refs', productionReadyMobileMutations({ mobile_visual_evidence_refs: [] }), null, /production-ready mobile visual axis requires/],
  ['not-run execution', productionReadyMobileMutations({ mobile_visual_check_execution_status: 'not-run' }), null, /production-ready mobile visual axis requires/],
  ['block verdict', productionReadyMobileMutations({ mobile_visual_gate_verdict: 'block' }), null, /production-ready mobile visual axis requires/],
  ['wrong evidence kind alias', productionReadyMobileMutations(), { evidenceKind: 'mobile-visual' }, /evidence_kind=mobile-visual does not match required kind mobile-readability/],
  ['wrong task alias', productionReadyMobileMutations(), { targetTaskField: 'task' }, /task is a rejected alias|requires one non-empty target_task/],
  ['wrong owner alias', productionReadyMobileMutations(), { accountableOwnerField: 'owner' }, /owner is a rejected alias|requires one non-empty accountable_owner/],
  ['wrong process alias', productionReadyMobileMutations(), { methodField: 'process' }, /process is a rejected alias|requires one non-empty method/],
  ['wrong viewport alias', productionReadyMobileMutations(), { viewportField: 'viewport_width', viewportValue: '320' }, /viewport_width is a rejected alias|requires one non-empty viewport_width_px/],
  ['missing screenshot or trace ref', productionReadyMobileMutations(), { screenshotOrTraceRef: '' }, /requires one non-empty screenshot_or_trace_ref/],
  ['missing screenshot or trace artifact', productionReadyMobileMutations(), { screenshotOrTraceRef: 'missing-mobile-trace.json' }, /(?:artifact_ref|screenshot_or_trace_ref) evidence path does not exist as a file/],
  ['wrong viewport width', productionReadyMobileMutations(), { viewportValue: '375' }, /viewport_width_px must be exactly 320/],
  ['wrong render target', productionReadyMobileMutations(), { renderTarget: 'https://example.test/guides/another-page' }, /render_target must exactly match canonical owner_page/],
  ['wrong accountable owner', productionReadyMobileMutations(), { accountableOwner: 'Different Mobile Owner (synthetic)' }, /accountable_owner must exactly match (?:the canonical CTA owner|the declared accountable owner)/],
]) {
  test(`P1 production-ready mobile blocks ${label}`, (t) => {
    expectBlockMatching(t, mutations, pattern, evidenceOptions ? (dir) => setupMobileReadabilityEvidence(dir, evidenceOptions) : null);
  });
}

test('P1 synthetic mobile canonical not-run missing block empty evidence remains valid', (t) => {
  expectAxisHasNoFocusedProblem(t, {}, /synthetic mobile visual axis/);
});

for (const [label, overrides] of [
  ['forged executed', { mobile_visual_check_execution_status: 'executed' }],
  ['forged confirmed', { mobile_visual_evidence_result: 'confirmed' }],
  ['forged pass', { mobile_visual_gate_verdict: 'pass' }],
  ['fake evidence refs', { mobile_visual_evidence_refs: ['search-evidence.md#fixture-buyer-task-evidence'] }],
]) {
  test(`P1 synthetic mobile blocks ${label}`, (t) => {
    expectBlockMatching(t, setFieldsAcrossAll(overrides), /synthetic mobile visual axis must be not-run \+ missing \+ block \+ empty refs/);
  });
}

function setFieldsAcrossAll(values) {
  return Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => Object.entries(values).reduce((output, [field, value]) => replaceField(output, field, JSON.stringify(value)), content)]));
}

const verifiedPrimaryRefs = {
  reference: 'primary-reference-evidence.md#cta-reference',
  reachability: 'primary-reachability-evidence.md#cta-reachability',
  capability: 'primary-capability-evidence.md#cta-capability',
};

function verifiedPrimaryRouteMutations() {
  const mutations = syntheticPrimaryEndpointMutations();
  for (const key of Object.keys(mutations)) {
    const prior = mutations[key];
    mutations[key] = (content) => {
      let output = prior(content);
      for (const [field, value] of Object.entries({
        evidence_scope: 'production',
        cta_reference_check_execution_status: 'executed', cta_reference_evidence_result: 'confirmed', cta_reference_gate_verdict: 'pass', cta_reference_evidence_refs: [verifiedPrimaryRefs.reference],
        cta_reachability_check_execution_status: 'executed', cta_reachability_evidence_result: 'confirmed', cta_reachability_gate_verdict: 'pass', cta_reachability_evidence_refs: [verifiedPrimaryRefs.reachability],
        cta_capability_check_execution_status: 'executed', cta_capability_evidence_result: 'confirmed', cta_capability_gate_verdict: 'pass', cta_capability_evidence_refs: [verifiedPrimaryRefs.capability],
      })) output = replaceField(output, field, JSON.stringify(value));
      return output;
    };
  }
  return mutations;
}

function setupVerifiedPrimaryRouteEvidence(dir) {
  const destination = legalSyntheticPrimaryEndpoint;
  const owner = 'Avery Chen, Applications Engineering Lead';
  const role = 'bounded-engineering-review';
  const task = 'all five first-round engineering inputs are available for a bounded readiness review candidate-or-stop, missing-input list, and bounded next-validation target';
  for (const axis of ['reference', 'reachability', 'capability']) {
    const capability = axis === 'capability'
      ? '\ncapability_acceptance: accepted the bounded candidate-or-stop review task at this exact endpoint without commercial commitment'
      : '';
    writeCompleteProductionEvidenceRecord(dir, {
      file: `primary-${axis}-evidence.md`,
      title: `Primary CTA ${axis} evidence`,
      kind: `cta-${axis}`,
      heading: `CTA ${axis}`,
      section: `check_id: cta-${axis}\ntarget_url: ${destination}\ntarget_role: ${role}\ntarget_task: ${task}\naccountable_owner: ${owner}\nobserved_at: 2026-08-01T00:00:00Z\nmethod: independent endpoint-specific ${axis} verification process\nobserved_result: confirmed the exact primary CTA endpoint ${axis} for the declared bounded engineering review task${capability}\nproducer: Primary Route Evidence Producer\nproducer_id: wco-primary-route-producer-001\nindependent_reviewer: Taylor Morgan, Independent Primary Route Reviewer\nindependent_reviewer_id: wco-primary-route-reviewer-001`,
    });
  }
}

test('P1 verified primary route with complete endpoint evidence is not killed by direct-action scanning', (t) => {
  expectAxisHasNoFocusedProblem(
    t,
    verifiedPrimaryRouteMutations(),
    /unverified primary CTA route|production cta_(?:reference|reachability|capability)|cta_(?:reference|reachability|capability)_evidence_refs.*(?:requires|must cover)|actual CTA section must use the canonical visible CTA channel/,
    (dir) => { setupLegalSyntheticEvidence(dir); setupVerifiedPrimaryRouteEvidence(dir); },
  );
});

test('P1 semantic emphasis blocks one legal strong plus one decorative garbage strong', (t) => {
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => body.replace('## Why wattage-first selection may create avoidable rework', '## Why wattage-first selection may create avoidable rework\n\n**Best motor keyword**')) }, /unplanned or decorative strong is blocked|keyword, label, or fragment/);
});

test('P1 semantic emphasis blocks a planned judgment that is not actually strong', (t) => {
  const planned = canonicalDecisionMap.length && fixtureArray(fixtureNames.briefPath, 'semantic_emphasis_plan')[0].split('|')[1];
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => replaceRequiredLiteral(body, `**${planned}**`, planned, 'planned strong removal')) }, /every semantic_emphasis_plan judgment must be implemented as an exact Markdown strong span/);
});


test('P1 semantic emphasis blocks a planned judgment wrapped in triple stars', (t) => {
  const planned = canonicalDecisionMap.length && fixtureArray(fixtureNames.briefPath, 'semantic_emphasis_plan')[0].split('|')[1];
  expectBlockMatching(t, {
    draftPath: (content) => transformBody(content, (body) => replaceRequiredLiteral(body, `**${planned}**`, `***${planned}***`, 'planned triple-star strong')),
  }, /triple-star emphasis renders literal outer stars|must be implemented as an exact Markdown strong span/);
});

for (const [label, injected] of [
  ['decorative keyword', '**Engineering readiness**'],
  ['decorative triple-asterisk keyword', '***Decorative engineering keyword***'],
  ['decorative triple-underscore keyword', '___Decorative engineering keyword___'],
  ['decorative pain label outside a numbered node', '**Decision:**'],
  ['unplanned whole paragraph', '**This entire unplanned paragraph is bold only for decoration and does not correspond to any approved semantic judgment.**'],
]) {
  test(`P1 semantic emphasis blocks ${label}`, (t) => {
    expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => body.replace('## Why wattage-first selection may create avoidable rework', `## Why wattage-first selection may create avoidable rework\n\n${injected}`)) }, /underscore emphasis is unsupported by the canonical AllinCMS converter|triple-star emphasis renders literal outer stars|unplanned or decorative strong is blocked|must not bold an entire prose paragraph|keyword, label, or fragment/);
  });
}

test('P1 semantic emphasis blocks a pain label outside the pain-chain section', (t) => {
  expectBlockMatching(t, {
    draftPath: (content) => transformBody(content, (body) => replaceRequiredLiteral(
      body,
      '## Use five decision blocks before the first review',
      '## Use five decision blocks before the first review\n\n**Decision:**',
      'pain label outside pain-chain section',
    )),
  }, /unplanned or decorative strong is blocked: Decision:/);
});

const canonicalNaturalPainNodes = [
  '1. An application engineer owns the first readiness review for a loaded, repeated-grade cargo e-bike candidate.',
  '2. When a 20-inch cargo e-bike program needs a hub-motor and controller direction for repeated-duty routes, that engineer may receive a candidate request based mainly on a wattage label.',
  '3. Because the label omits comparable load, wheel, duty, electrical, or interface evidence, Engineering cannot defend the comparison basis.',
  '4. That evidence gap can force Engineering to rebuild the comparison and Quality to revisit the same assumptions.',
  '5. The repeated review may allow a weak or mismatched candidate to enter sample validation before the decision basis is defensible.',
  '6. Therefore, complete one readiness worksheet, identify missing evidence, and define the next review step—not select or reject a candidate from the first-round packet.',
];

function replaceCanonicalPainNodes(body, nodes) {
  return replaceRequiredLiteral(body, canonicalNaturalPainNodes.join('\n'), nodes.join('\n'), 'canonical pain-chain replacement');
}

function painMutation(nodes) {
  return { draftPath: (content) => transformBody(content, (body) => replaceCanonicalPainNodes(body, nodes)) };
}

test('P1 visible pain chain duplicate test isolates the unique six-node run', (t) => {
  const nodes = [...canonicalNaturalPainNodes];
  nodes.splice(2, 0, nodes[1]);
  expectBlockMatching(t, painMutation(nodes), /visible pain chain requires exactly one buyer-visible H2 section with six ordered natural-language nodes.*found 0/);
});

test('P1 visible pain chain reversed test blocks semantic slot-order drift', (t) => {
  const nodes = [...canonicalNaturalPainNodes];
  [nodes[1], nodes[2]] = [nodes[2], nodes[1]];
  expectBlockMatching(t, painMutation(nodes), /visible pain chain requires exactly one buyer-visible H2 section with six ordered natural-language nodes.*found 0/);
});

for (const [label, mutate, oracle] of [
  ['deleted number', (nodes) => nodes.map((row, index) => index === 2 ? row.replace('3. ', '') : row), /visible pain chain requires exactly one buyer-visible H2 section with six ordered natural-language nodes.*found 0/],
  ['parenthesis numbering', (nodes) => nodes.map((row, index) => index === 3 ? row.replace('4. ', '4) ') : row), /visible pain chain requires exactly one buyer-visible H2 section with six ordered natural-language nodes.*found 0/],
  ['exposed audit label', (nodes) => nodes.map((row, index) => index === 0 ? row.replace('1. ', '1. **Actor:** ') : row), /buyer-visible pain chain must use natural buyer language and must not expose internal Actor\/Trigger\/Evidence gap\/Rework\/Consequence\/Decision audit labels/],
]) {
  test(`P1 visible pain chain blocks ${label}`, (t) => {
    expectBlockMatching(t, painMutation(mutate([...canonicalNaturalPainNodes])), oracle);
  });
}

test('P1 visible pain chain body value must preserve pain_chain_contract parity', (t) => {
  const nodes = [...canonicalNaturalPainNodes];
  nodes[5] = '6. Therefore, select the supplier immediately and request an order.';
  expectBlockMatching(t, painMutation(nodes), /visible pain chain requires exactly one buyer-visible H2 section|visible pain chain Decision node lacks contract parity/);
});

for (const key of ['draftPath', 'reviewPath']) {
  test(`P1 ${key} requires visible_pain_chain four-record projection`, (t) => {
    expectBlockMatching(t, { [key]: (content) => removeField(content, 'visible_pain_chain') }, /missing required field visible_pain_chain|visible_pain_chain must contain exactly six rows/);
  });
}

test('P1 visible_pain_chain projection is byte-exact across four records', (t) => {
  expectBlockMatching(t, {
    reviewPath: (content) => mutateJsonArrayField(content, 'visible_pain_chain', (rows) => rows.map((row, index) => index === 0 ? `${row} drift` : row)),
  }, /visible_pain_chain must match the canonical Brief projection across all records using exact-raw-sequence/);
});

test('P1 dominant_search_intent rejects a packed multi-stage objective after Brief and Draft synchronization', (t) => {
  const packed = 'learn, compare, validate, buy, and troubleshoot every unrelated buyer objective at once';
  expectBlockMatching(t, {
    briefPath: (content) => replaceField(content, 'dominant_search_intent', JSON.stringify(packed)),
    draftPath: (content) => replaceField(content, 'dominant_search_intent', JSON.stringify(packed)),
  }, /dominant_search_intent|one dominant|packed|enumeration|single dominant/i);
});

test('P1 synchronized unrelated meta description and excerpt cannot pass projection-only checks', (t) => {
  const meta = 'Indoor orchid wallpaper care advice for apartment kitchens with decorative lantern placement and unrelated watering schedules.';
  const excerpt = 'A practical guide to choosing banana-pattern wallpaper, orchid pots, and kitchen lanterns for small apartments.';
  expectBlockMatching(t, {
    draftPath: (content) => replaceField(replaceField(content, 'meta_description', JSON.stringify(meta)), 'excerpt', JSON.stringify(excerpt)),
    publishPath: (content) => replaceField(replaceField(content, 'published_meta_description', JSON.stringify(meta)), 'published_excerpt', JSON.stringify(excerpt)),
  }, /meta_description|excerpt.*(?:primary query|dominant|article title|publishable body)|semantic/i);
});

test('P1 deterministic conversion-outcome promise is blocked without requiring a number or modal', (t) => {
  expectBlockMatching(t, {
    draftPath: (content) => transformBody(content, (body) => `${body}\n\nThis checklist increases qualified inquiries and conversion rates.\n`),
  }, /unsupported.*outcome|qualified inquiries|conversion rates/i);
});

test('P1 synchronized ICP contracts cannot make the same buyer both included and excluded', (t) => {
  const fit = 'Mid-market cargo e-bike OEMs evaluating a 48 V cargo hub-motor before sample validation, with an engineer able to supply five readiness inputs, including price-only buyers and projects unable to supply those inputs.';
  const exclusion = 'Mid-market cargo e-bike OEMs evaluating a 48 V cargo hub-motor before sample validation with an engineer able to supply five readiness inputs are outside this article contract.';
  expectBlockMatching(t, {
    briefPath: (content) => replaceField(replaceField(content, 'icp_fit_contract', JSON.stringify(fit)), 'icp_exclusion_contract', JSON.stringify(exclusion)),
    draftPath: (content) => replaceField(replaceField(content, 'icp_fit_contract_snapshot', JSON.stringify(fit)), 'icp_exclusion_contract_snapshot', JSON.stringify(exclusion)),
    reviewPath: (content) => replaceField(replaceField(content, 'icp_fit_contract_snapshot', JSON.stringify(fit)), 'icp_exclusion_contract_snapshot', JSON.stringify(exclusion)),
    publishPath: (content) => replaceField(replaceField(content, 'icp_fit_contract_snapshot', JSON.stringify(fit)), 'icp_exclusion_contract_snapshot', JSON.stringify(exclusion)),
  }, /icp_fit_contract|icp_exclusion_contract|contradict|positive fit|same buyer/i);
});

for (const [label, injected] of [
  ['transmit link', 'Transmit the completed five-input packet through [this intake endpoint](https://capture.vendor.invalid/intake).'],
  ['deliver plain URL', 'Deliver the completed five-input packet through https://capture.vendor.invalid/intake.'],
  ['provide email', 'Provide the completed five-input packet to intake@capture.vendor.invalid.'],
  ['endpoint declaration without action verb', 'The packet destination is [the engineering intake endpoint](https://capture.vendor.invalid/intake).'],
]) {
  test(`P1 unverified CTA route blocks ${label}`, (t) => {
    expectBlockMatching(t, {
      draftPath: (content) => transformBody(content, (body) => body.replace('## Why wattage-first selection may create avoidable rework', `## Why wattage-first selection may create avoidable rework\n\n${injected}`)),
    }, /buyer-visible (?:link URL|plain or linked URL) is undeclared|unverified primary CTA route must not directly link or instruct/i);
  });
}

test('P1 undeclared product or solution link is blocked outside the internal-link contract closed set', (t) => {
  expectBlockMatching(t, {
    draftPath: (content) => transformBody(content, (body) => body.replace('## Why wattage-first selection may create avoidable rework', '## Why wattage-first selection may create avoidable rework\n\n[Cargo hub-motor candidate catalog](https://capture.vendor.invalid/solutions/cargo-hub-motors)')),
  }, /buyer-visible link URL is undeclared|buyer-visible plain or linked URL is undeclared/i);
});

test('P1 replacement product URL cannot inherit the approval of a different internal-link target', (t) => {
  const mutations = productionInternalLinkMutations();
  const prior = mutations.draftPath;
  mutations.draftPath = (content) => transformBody(prior(content), (body) => replaceRequiredLiteral(body, 'https://example.test/solutions/cargo-hub-motor-candidates', 'https://capture.vendor.invalid/solutions/cargo-hub-motors', 'approved internal-link target replacement'));
  expectBlockMatching(t, mutations, /buyer-visible link URL is undeclared|buyer-visible plain or linked URL is undeclared|internal-link URL must be a real Markdown-to-Slate link node/i, setupProductionInternalLinkEvidence);
});


function applyMutationSets(...sets) {
  return Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => {
    let output = content;
    for (const set of sets) if (set?.[key]) output = set[key](output);
    return output;
  }]));
}

function overrideMutationSetField(base, field, value) {
  return Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => {
    const output = base[key] ? base[key](content) : content;
    return replaceIfPresent(output, field, value);
  }]));
}

const requiredImageVisualRow = 'diagram|compare the five engineering-readiness inputs on one basis|each input changes a bounded candidate-or-stop decision|search-evidence.md#fixture-artifact-status-versus-market-information-gain|inside the use five decision blocks before the first review section|Five inputs that determine whether a cargo hub-motor candidate can enter engineering review|five engineering readiness inputs determine cargo hub motor candidate or stop decision|stack the diagram labels and arrows without horizontal scrolling at 320px|required';
const requiredImageVisualUrl = 'https://cdn.acme-industrial-assets.com/diagrams/cargo-hub-readiness-flow.png';
const requiredImageVisualAlt = 'Five engineering readiness inputs determine cargo hub motor candidate or stop decision';

function requiredImageLikeVisualMutations({
  row = requiredImageVisualRow,
  image = `![${requiredImageVisualAlt}](${requiredImageVisualUrl})`,
  placement = 'correct',
  extraImage = '',
  keepOriginalDeclaration = false,
} = {}) {
  return Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => {
    let output = content;
    if (!keepOriginalDeclaration) output = replaceField(output, 'visual_decision_assets', JSON.stringify([row]));
    if (key !== 'draftPath') return output;
    if (placement === 'correct' && image) output = transformBody(output, (body) => body.replace('## Use five decision blocks before the first review', `## Use five decision blocks before the first review\n\n${image}`));
    if (placement === 'wrong' && image) output = transformBody(output, (body) => body.replace('## Candidate or stop: make the boundary visible', `## Candidate or stop: make the boundary visible\n\n${image}`));
    if (extraImage) output = transformBody(output, (body) => body.replace('## Candidate or stop: make the boundary visible', `## Candidate or stop: make the boundary visible\n\n${extraImage}`));
    return output;
  }]));
}

test('P1 required image-like visual has a clean HTTPS informative-alt positive baseline', (t) => {
  expectPass(makeFixture(t, requiredImageLikeVisualMutations()));
});

for (const [label, options, pattern] of [
  ['missing image', { image: '' }, /required diagram asset must bind to exactly one Markdown image inside its declared H2 section/],
  ['empty alt', { image: `![](${requiredImageVisualUrl})` }, /Markdown image alt must be non-empty, specific, non-placeholder, and information-bearing/],
  ['generic alt', { image: `![diagram](${requiredImageVisualUrl})` }, /Markdown image alt must be non-empty, specific, non-placeholder, and information-bearing/],
  ['HTTP source', { image: `![${requiredImageVisualAlt}](http://cdn.acme-industrial-assets.com/diagrams/cargo-hub-readiness-flow.png)` }, /required diagram Markdown image source must use HTTPS/],
  ['reserved source', { image: `![${requiredImageVisualAlt}](https://example.test/diagram.png)` }, /required diagram Markdown image source cannot use a placeholder, reserved synthetic fixture, loopback, or credential-bearing URL/],
  ['wrong H2 placement', { placement: 'wrong' }, /required diagram asset must bind to exactly one Markdown image inside its declared H2 section/],
  ['duplicate source', { extraImage: `![${requiredImageVisualAlt}](${requiredImageVisualUrl})` }, /required diagram Markdown image must occur exactly once in the publishable body and only inside its declared H2 section/],
  ['undeclared image', { keepOriginalDeclaration: true }, /undeclared Markdown image|image-like visual/],
]) {
  test(`P1 required image-like visual blocks ${label}`, (t) => {
    expectBlockMatching(t, requiredImageLikeVisualMutations(options), pattern);
  });
}

test('P1 ICP projection drift in any downstream record is fatal', (t) => {
  expectBlockMatching(t, { publishPath: (content) => replaceField(content, 'icp_fit_contract_snapshot', '"A different industrial buyer with no matching purchase trigger or implementation capability."') }, /icp_fit_contract.*projection mismatch|projection icp_fit_contract_snapshot/);
});

test('P1 production ICP cannot remain inferred', (t) => {
  const mutations = allRecords('evidence_scope', '"production"');
  expectBlockMatching(t, mutations, /production requires icp_evidence_status=confirmed/);
});

test('P1 production ICP confirmed status requires non-empty evidence refs', (t) => {
  const mutations = allRecords('evidence_scope', '"production"');
  mutations.briefPath = (content) => replaceField(replaceField(replaceField(content, 'evidence_scope', '"production"'), 'icp_evidence_status', '"confirmed"'), 'icp_evidence_refs', '[]');
  expectBlockMatching(t, mutations, /icp_evidence_refs must contain at least one local evidence reference/);
});

for (const field of ['cta_data_purpose', 'cta_data_retention_period', 'cta_data_deletion_path', 'cta_data_retention_owner']) {
  test(`P1 collecting CTA blocks missing ${field} across the canonical package`, (t) => {
    expectBlockMatching(t, overrideMutationSetField(completeBuyCommercialMutations(), field, '""'), new RegExp(field));
  });
}

for (const [label, contractField, pattern] of [
  ['Data purpose', 'purpose', /buyer-visible CTA must display an explicit cta_data_purpose label and the exact canonical value/],
  ['Retention period', 'retention', /buyer-visible CTA must display an explicit cta_data_retention_period label and the exact canonical value/],
  ['Deletion path', 'deletion', /buyer-visible CTA must display an explicit cta_data_deletion_path label and the exact canonical value/],
  ['Retention owner', 'owner', /buyer-visible CTA must display an explicit cta_data_retention_owner label and the exact canonical value/],
]) {
  test(`P1 collecting CTA body blocks missing ${label} label and value`, (t) => {
    const line = `- ${label}: ${productionCtaDataContract[contractField]}`;
    const base = productionCollectingPolicyMutations();
    const prior = base.draftPath;
    base.draftPath = (content) => transformBody(prior(content), (body) => replaceRequiredLiteral(body, line, '', `${label} buyer-visible data-policy line`));
    expectBlockMatching(t, base, pattern, setupProductionCollectingPolicyEvidence);
  });
}

for (const [surface, mutations] of [
  ['title', {
    briefPath: (content) => replaceField(content, 'working_article_title', '"Cargo Hub Motor Checklist That Increases Qualified Inquiries"'),
    draftPath: (content) => replaceField(content, 'article_title', '"Cargo Hub Motor Checklist That Increases Qualified Inquiries"'),
    publishPath: (content) => replaceField(content, 'published_article_title', '"Cargo Hub Motor Checklist That Increases Qualified Inquiries"'),
  }],
  ['meta description', {
    draftPath: (content) => replaceField(content, 'meta_description', '"This cargo hub motor engineering readiness checklist increases qualified inquiries and conversion rates for industrial suppliers."'),
    publishPath: (content) => replaceField(content, 'published_meta_description', '"This cargo hub motor engineering readiness checklist increases qualified inquiries and conversion rates for industrial suppliers."'),
  }],
  ['excerpt', {
    draftPath: (content) => replaceField(content, 'excerpt', '"Use this cargo hub motor checklist because it increases qualified inquiries and conversion rates for industrial suppliers."'),
    publishPath: (content) => replaceField(content, 'published_excerpt', '"Use this cargo hub motor checklist because it increases qualified inquiries and conversion rates for industrial suppliers."'),
  }],
  ['body', { draftPath: (content) => transformBody(content, (body) => `${body}\n\nThis checklist increases qualified inquiries and conversion rates.\n`) }],
]) {
  test(`P1 unsupported outcome claim is blocked on the ${surface} surface`, (t) => {
    expectBlockMatching(t, mutations, /contains an unsupported ranking, inquiry, or conversion outcome claim/);
  });
}

for (const claim of [
  'This guide secures first-page rankings.',
  'This guide wins more qualified inquiries.',
  'This guide lifts qualified inquiries by 30 percent.',
  'This guide yields more qualified inquiries.',
  'This guide brings more qualified inquiries.',
  'This guide gains more qualified inquiries.',
  'This guide achieves first-page rankings.',
]) {
  test(`P1 unsupported outcome synonym fails closed: ${claim}`, (t) => {
    expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => `${body}

${claim}
`) }, /contains an unsupported ranking, inquiry, or conversion outcome claim/);
  });
}

for (const safeBoundary of [
  'This guide does not secure first-page rankings.',
  'More qualified inquiries remain unverified.',
  'Qualified-inquiry and conversion effects have not been verified.',
]) {
  test(`P1 explicit negative outcome boundary remains allowed: ${safeBoundary}`, (t) => {
    expectPass(makeFixture(t, { draftPath: (content) => transformBody(content, (body) => `${body}

${safeBoundary}
`) }));
  });
}

test('P1 Learn dominant intent cannot hide a vendor-sourcing and bid-award objective', (t) => {
  const mixedIntent = 'Learn how cargo hub motors work and source vendors for a bid award';
  expectBlockMatching(t, {
    briefPath: (content) => replaceField(content, 'dominant_search_intent', JSON.stringify(mixedIntent)),
    draftPath: (content) => replaceField(content, 'dominant_search_intent', JSON.stringify(mixedIntent)),
  }, /Learn dominant_search_intent.*commercial_commitment=none.*vendor sourcing|bid|procurement/i);
});

test('P1 Learn dominant intent cannot hide quotation, pricing, tender, or procurement actions', (t) => {
  for (const action of ['solicit bids', 'prepare a tender', 'build a vendor shortlist', 'request a proposal', 'compare quotation pricing', 'procure and purchase motors']) {
    const mixedIntent = `Learn how cargo hub motors work and ${action}`;
    expectBlockMatching(t, {
      briefPath: (content) => replaceField(content, 'dominant_search_intent', JSON.stringify(mixedIntent)),
      draftPath: (content) => replaceField(content, 'dominant_search_intent', JSON.stringify(mixedIntent)),
    }, /noncommercial dominant_search_intent with commercial_commitment=none must not contain sourcing, bid, tender, proposal, quotation, pricing, procurement, purchase/i);
  }
});

test('P1 production query rows older than 395 days are stale', (t) => {
  expectBlockMatching(t, v11ProductionQueryMutations(), /production query row .* checked_at is stale; it must be no more than 395 days old/, (dir) => {
    setupV11QueryRows(dir);
    const target = join(dir, 'v11-query-evidence.md');
    writeFileSync(target, readFileSync(target, 'utf8').replaceAll('2026-08-01', '2024-01-01'));
  });
});

test('P1 production SERP evidence older than 395 days is stale', (t) => {
  expectBlockMatching(t, v12ProductionSerpMutations(), /SERP-format evidence .* checked_at is stale; it must be no more than 395 days old/, (dir) => setupV12SerpEvidence(dir, { checkedAt: '2024-01-01' }));
});

const productionLearnQueries = [
  'cargo e-bike hub motor engineering basics',
  'how cargo e-bike hub motors work',
  'cargo hub motor engineering concepts',
];
const productionLearnOwnerPage = 'https://www.fluxpedal-motors.com/guides/cargo-hub-motor-engineering-readiness-checklist';
const productionLearnTitle = 'Cargo E-Bike Hub Motor Engineering Basics: Inputs and Sample-Validation Concepts';


function productionSupportingSerpRows(queries, file = 'production-serp-format-evidence.md') {
  return queries.slice(1).map((query, index) => `${query}|5|checklist|3|0.60|pass|${file}#supporting-query-${index + 1}`);
}

function productionSupportingSerpFragments(queries) {
  return queries.slice(1).map((query, index) => `## Supporting query ${index + 1}

query: ${query}
market: United States
language: en
device: desktop
checked_at: 2026-08-02
result_types: ${JSON.stringify(['checklist', 'checklist', 'checklist', 'guide', 'guide'])}
sample_size: 5
dominant_result_type: checklist
dominant_result_count: 3
dominance_threshold: 0.60
dominance_verdict: pass`).join('\n\n');
}

function productionMarketComparisonPayload(queries, { prefix, acceptedInformationGain }) {
  const ids = [`${prefix}-01`, `${prefix}-02`, `${prefix}-03`];
  return {
    query_set: queries, market: 'United States', language: 'en', device: 'desktop', checked_at: '2026-08-02',
    comparison_corpus_ids: ids,
    comparison_corpus_rows: [
      `${ids[0]}|https://www.fluxpedal-motors.com/research/${prefix}-wattage-overview|guide|existing wattage selection overview`,
      `${ids[1]}|https://www.fluxpedal-motors.com/research/${prefix}-engineering-guide|guide|existing hub motor engineering guide`,
      `${ids[2]}|https://www.fluxpedal-motors.com/research/${prefix}-readiness-checklist|checklist|existing readiness checklist decision artifact`,
    ],
    difference_dimensions: ['input completeness boundary', 'next decision ownership', 'sample validation handoff'],
    accepted_information_gain: acceptedInformationGain,
    boundary: 'This comparison does not prove ranking, traffic, inquiry, conversion, product fit, supplier acceptance, or commercial acceptance.',
  };
}

function productionMarketComparisonEvidence(payload) {
  return [`query_set: ${payload.query_set.join("; ")}`, `market: ${payload.market}`, `language: ${payload.language}`, `device: ${payload.device}`, `checked_at: ${payload.checked_at}`, `comparison_corpus_ids: ${JSON.stringify(payload.comparison_corpus_ids)}`, `comparison_corpus_rows: ${JSON.stringify(payload.comparison_corpus_rows)}`, `difference_dimensions: ${JSON.stringify(payload.difference_dimensions)}`, `accepted_information_gain: ${payload.accepted_information_gain}`, `difference: ${payload.accepted_information_gain}`, `boundary: ${payload.boundary}`].join("\n");
}

function writeCompleteProductionEvidenceRecord(dir, {
  file, title, kind, heading, section,
}) {
  let normalizedSection = section.trim();
  const supportingBoundary = normalizedSection.indexOf("\n## ");
  let primarySection = supportingBoundary < 0 ? normalizedSection : normalizedSection.slice(0, supportingBoundary);
  const supportingSections = supportingBoundary < 0 ? "" : normalizedSection.slice(supportingBoundary);
  if (/^check_id:/m.test(primarySection)) {
    const declaredRef = (/^(?:artifact_ref|screenshot_or_trace_ref):\s*(.+)$/m.exec(primarySection) || [])[1]?.trim() || "";
    let artifactRef = declaredRef;
    if (!artifactRef) {
      artifactRef = `artifacts/${file.replace(/\.md$/i, "")}-${heading.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}.txt`;
      const artifactBytes = `Immutable production acceptance artifact for ${kind} / ${heading} captured at 2026-08-02T00:00:00Z.\n`;
      mkdirSync(join(dir, "artifacts"), { recursive: true });
      writeFileSync(join(dir, artifactRef), artifactBytes);
      primarySection += `\nartifact_ref: ${artifactRef}`;
    }
    const artifactPath = join(dir, artifactRef);
    assert.equal(readFileSync(artifactPath).length > 0, true, `declared production evidence artifact must contain bytes: ${artifactRef}`);
    const artifactDigest = `sha256:${createHash("sha256").update(readFileSync(artifactPath)).digest("hex")}`;
    primarySection = /^artifact_digest:/m.test(primarySection)
      ? primarySection.replace(/^artifact_digest:.*$/m, `artifact_digest: ${artifactDigest}`)
      : `${primarySection}\nartifact_digest: ${artifactDigest}`;
    if (!/^producer_id:/m.test(primarySection)) primarySection += "\nproducer_id: wco-production-evidence-producer-001";
    if (!/^independent_reviewer_id:/m.test(primarySection)) primarySection += "\nindependent_reviewer_id: wco-independent-reviewer-001";
  }
  normalizedSection = `${primarySection}${supportingSections}`;
  const body = `# ${title}\n\n## ${heading}\n\n${normalizedSection}\n`;
  const digest = createHash("sha256").update(body).digest("hex");
  writeFileSync(join(dir, file), `---\ntitle: ${title}\nrecord_type: evidence-record\nevidence_scope: production\nsource: independently captured production acceptance evidence\nobserved_at: 2026-08-02T00:00:00Z\ncaptured_at: 2026-08-02T00:00:00Z\ndigest: sha256:${digest}\nevidence_kind: ${kind}\n---\n${body}`);
}

function snapshotBindingText(kind, subjectId) {
  return `snapshot_subject_id: ${subjectId}\nsnapshot_scope_id: United States|en|desktop\nsnapshot_capture_method: ${kind}-independent-export\nsnapshot_producer_id: wco-${kind}-snapshot-producer-001\nsnapshot_independent_reviewer_id: wco-${kind}-snapshot-reviewer-001`;
}

function writeProductionSnapshotArtifact(dir, { file, kind, payload }) {
  const subjectId = payload.query_set?.[0] || payload.query;
  const content = `${JSON.stringify({
    schema_version: 'website-content-ops.snapshot.v1',
    artifact_kind: kind,
    evidence_scope: 'production',
    captured_at: '2026-08-02T00:00:00Z',
    subject_id: subjectId,
    scope_id: 'United States|en|desktop',
    capture_method: `${kind}-independent-export`,
    producer_id: `wco-${kind}-snapshot-producer-001`,
    independent_reviewer_id: `wco-${kind}-snapshot-reviewer-001`,
    payload,
  }, null, 2)}\n`;
  writeFileSync(join(dir, file), content);
  return `sha256:${createHash('sha256').update(content).digest('hex')}`;
}

function completeProductionLearnMutations() {
  const base = notApplicableSyntheticMutations();
  const common = {
    package_id: 'PROD-CARGO-MOTOR-LEARN-001',
    owner_page: productionLearnOwnerPage,
    evidence_scope: 'production',
    evidence_origin: 'live-production',
    fixture_identity: 'not-applicable',
    production_proof_eligible: true,
    author_id: 'wco-content-author-001',
    producer_id: 'wco-evidence-producer-001',
    independent_reviewer_id: 'wco-independent-reviewer-001',
    remediation_participant_ids: [],
    identity_provenance_observed_at: '2026-08-02T00:00:00Z',
    identity_provenance_reviewed_at: '2026-08-02T12:00:00Z',
    identity_provenance_review_ceiling: '2026-08-02T16:00:00Z',
    identity_provenance_evidence_refs: ['production-identity-provenance.md#identity-provenance'],
    reviewer_separation_verdict: 'pass',
    primary_icp: 'mid-market cargo e-bike OEM or fleet-integrator engineering teams able to provide bounded readiness inputs',
    explicit_icp_exclusions: ['consumer replacement shoppers', 'price-only sourcing teams'],
    icp_fit_contract: 'Mid-market cargo e-bike OEM or fleet-integrator engineering teams before candidate review, when a cargo program has bounded load, wheel, duty, electrical, and interface records ready for engineering-readiness review.',
    icp_exclusion_contract: 'Consumer replacement shoppers and price-only sourcing teams without the declared engineering inputs are excluded.',
    icp_fit_contract_snapshot: 'Mid-market cargo e-bike OEM or fleet-integrator engineering teams before candidate review, when a cargo program has bounded load, wheel, duty, electrical, and interface records ready for engineering-readiness review.',
    icp_exclusion_contract_snapshot: 'Consumer replacement shoppers and price-only sourcing teams without the declared engineering inputs are excluded.',
    cta_route_transmission_verdict: 'pass',
    icp_evidence_status: 'confirmed',
    icp_evidence_refs: ['production-icp-evidence.md#icp-evidence'],
    icp_evidence_status_snapshot: 'confirmed',
    icp_evidence_refs_snapshot: ['production-icp-evidence.md#icp-evidence'],
    query_evidence_status: 'confirmed',
    query_evidence_refs: ['production-query-evidence.md#query-evidence'],
    buyer_task_evidence_status: 'confirmed',
    buyer_task_evidence_refs: ['production-buyer-task-evidence.md#buyer-task'],
    search_demand_evidence_status: 'confirmed',
    search_demand_observation_start_at: '2026-06-01T00:00:00Z',
    search_demand_observation_end_at: '2026-07-31T23:59:59Z',
    search_demand_evidence_refs: ['production-search-demand-evidence.md#search-demand'],
    serp_format_evidence_status: 'confirmed',
    serp_format_evidence_refs: ['production-serp-format-evidence.md#serp-format'],
    serp_gap_status: 'confirmed',
    serp_gap_refs: ['production-serp-gap-evidence.md#serp-gap'],
    customer_language_status: 'confirmed',
    customer_language_refs: ['production-customer-language-evidence.md#customer-language'],
    customer_language_gate_verdict: 'pass',
    pain_evidence_status: 'confirmed',
    pain_evidence_refs: ['production-pain-evidence.md#pain-evidence'],
    pain_evidence_gate_verdict: 'pass',
    first_party_proof_status: 'inferred',
    first_party_proof_refs: [],
    primary_buyer_evidence_refs: ['production-buyer-task-evidence.md#buyer-task'],
    secondary_buyer_roles: [],
    secondary_buyer_role_contracts: [],
    secondary_buyer_role_contracts_snapshot: [],
    content_inventory_refs: ['production-inventory-evidence.md#inventory-zero-result'],
    serp_evidence_ref: 'production-serp-format-evidence.md#serp-format',
    information_gain_artifact_status: 'confirmed',
    information_gain_artifact_refs: ['production-information-gain-artifact.md#decision-artifact'],
    market_information_gain_status: 'confirmed',
    information_gain_market_refs: ['production-information-gain-market.md#market-information-gain'],
    content_inventory_status: 'confirmed',
    inventory_snapshot_ref: 'production-inventory-evidence.md#inventory-zero-result',
    inventory_zero_result_evidence_refs: ['production-inventory-evidence.md#inventory-zero-result'],
    production_search_evidence_gate_verdict: 'pass',
    structure_review_verdict: 'pass',
    production_evidence_review_verdict: 'pass',
    serp_content_type_parity_verdict: 'pass',
    fatal_gate_verdict: 'pass',
    production_readiness: 'ready',
    release_decision: 'ready-for-cms-draft',
    operation_mode: 'dry-run',
    mobile_visual_check_execution_status: 'executed',
    mobile_visual_evidence_result: 'confirmed',
    mobile_visual_gate_verdict: 'pass',
    mobile_visual_evidence_refs: ['mobile-readability-evidence.md#mobile-readability'],
    serp_primary_query: productionLearnQueries[0],
    serp_primary_query_sample_size: '5',
    serp_primary_query_dominant_result_type: 'checklist',
    serp_primary_query_dominant_result_count: '3',
    serp_primary_query_dominance_threshold: '0.60',
    serp_primary_query_dominance_verdict: 'pass',
    serp_primary_query_result_type_counts: ['checklist|3', 'guide|2'],
    serp_supporting_query_result_type_rows: productionSupportingSerpRows(productionLearnQueries),
  };
  return Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => {
    let output = base[key](content);
    for (const [field, value] of Object.entries(common)) output = replaceIfPresent(output, field, JSON.stringify(value));
    if (key === 'reviewPath') {
      output = replaceField(output, 'reviewer_identity', '"Taylor Morgan, Independent Buyer Review Lead"');
      output = replaceField(output, 'reviewed_at', '"2026-08-03T00:00:00+08:00"');
      output = replaceIfPresent(output, 'production_evidence_score', '"100"');
      output = replaceIfPresent(output, 'visual_decision_assets_verdict', '"pass"');
      for (const field of fatalReviewVerdicts) output = replaceIfPresent(output, field, '"pass"');
    }
    if (key === 'draftPath') output = transformBody(output, (body) => `
Prepare this bounded readiness self-check for mid-market cargo e-bike OEM or fleet-integrator engineering teams before candidate review, when load, wheel, duty, electrical, and interface records are ready. This article is not for consumer replacement shoppers or price-only sourcing teams.
${body}`);
    return output;
  }]));
}

function completeProductionStructuredSection({ checkId, role, task, targetUrl = productionLearnOwnerPage, extra = '' }) {
  return `check_id: ${checkId}\ntarget_url: ${targetUrl}\ntarget_role: ${role}\ntarget_task: ${task}\nobserved_at: 2026-08-02T00:00:00Z\nmethod: independent bounded production evidence review\nobserved_result: confirmed the declared buyer task and evidence boundary for this exact article owner page\nartifact_digest: sha256:${'d'.repeat(64)}\nproducer: Production Evidence Producer\nindependent_reviewer: Taylor Morgan, Independent Buyer Review Lead\n${extra}`;
}

function writeProductionIdentityProvenance(dir, packageId) {
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-identity-provenance.md',
    title: 'Production identity provenance',
    kind: 'identity-provenance',
    heading: 'Identity provenance',
    section: `package_id: ${packageId}
author_id: wco-content-author-001
producer_id: wco-evidence-producer-001
independent_reviewer_id: wco-independent-reviewer-001
remediation_participant_ids: []
verification_method: independent identity registry and task-assignment record comparison
observed_at: 2026-08-02T00:00:00Z`,
  });
}

function writeProductionCustomerLanguageAndPainEvidence(dir, targetUrl) {
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-customer-language-evidence.md',
    title: 'Production customer-language evidence',
    kind: 'customer-language',
    heading: 'Customer language',
    section: completeProductionStructuredSection({
      checkId: 'customer-language',
      role: 'customer-language',
      task: 'confirm the exact buyer wording used for cargo hub-motor readiness and missing-input rework',
      targetUrl,
      extra: 'customer_language_sample: We need to know which five inputs are required before engineering can review a cargo hub-motor candidate without restarting the sample discussion.\nsource_boundary: independently reviewed first-party buyer-language sample; no ranking or conversion outcome is claimed',
    }),
  });
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-pain-evidence.md',
    title: 'Production buyer-pain evidence',
    kind: 'pain-evidence',
    heading: 'Pain evidence',
    section: completeProductionStructuredSection({
      checkId: 'pain-evidence',
      role: 'pain-evidence',
      task: 'confirm the observed rework caused by incomplete cargo hub-motor engineering inputs',
      targetUrl,
      extra: 'observed_pain: incomplete load, duty, electrical, and interface inputs caused repeated clarification and delayed candidate-or-stop review\nconsequence_boundary: evidence confirms the buyer problem only; it does not prove inquiry or revenue lift',
    }),
  });
}

function setupCompleteProductionLearnEvidence(dir, {
  serpResultTypes = ['checklist', 'checklist', 'checklist', 'guide', 'guide'],
  serpPrimaryDominantType = 'checklist',
} = {}) {
  writeProductionIdentityProvenance(dir, 'PROD-CARGO-MOTOR-LEARN-001');
  writeProductionCustomerLanguageAndPainEvidence(dir, productionLearnOwnerPage);
  const targetTask = (kind) => `${productionLearnQueries[0]} | United States | ${kind}`;
  const searchDemandSnapshotDigest = writeProductionSnapshotArtifact(dir, {
    file: 'gsc-export-2026-07-31.json', kind: 'search-demand',
    payload: { query_set: productionLearnQueries, metric_type: 'search impressions', observation_window: '2026-06-01 to 2026-07-31' },
  });
  const serpFormatSnapshotDigest = writeProductionSnapshotArtifact(dir, {
    file: 'serp-format-corpus-2026-08-02.json', kind: 'serp-format',
    payload: { query_set: productionLearnQueries, market: 'United States', language: 'en', device: 'desktop', result_types: serpResultTypes },
  });
  const serpPrimaryResultTypeCounts = [...new Map(serpResultTypes.map((type) => [type, serpResultTypes.filter((item) => item === type).length])).entries()].map(([type, count]) => `${type}|${count}`);
  const serpPrimaryDominantCount = serpPrimaryResultTypeCounts.find((row) => row.startsWith(`${serpPrimaryDominantType}|`))?.split(`|`)[1] || `0`;
  const marketComparisonPayload = productionMarketComparisonPayload(productionLearnQueries, { prefix: 'learn-corpus', acceptedInformationGain: 'One bounded five-input concept checklist connects missing assumptions to the next sample-validation evidence task.' });
  const marketComparisonSnapshotDigest = writeProductionSnapshotArtifact(dir, {
    file: 'independent-serp-corpus-2026-08-02.json', kind: 'market-comparison', payload: marketComparisonPayload,
  });
  const contentInventorySnapshotDigest = writeProductionSnapshotArtifact(dir, {
    file: 'production-content-inventory-2026-08-02.json', kind: 'content-inventory',
    payload: { query: productionLearnQueries[0], candidate_count: 0, retrieval_dimensions: ['url', 'slug', 'title', 'query', 'buyer-task', 'stage', 'taxonomy'] },
  });
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-icp-evidence.md', title: 'Production ICP evidence', kind: 'icp-evidence', heading: 'ICP evidence',
    section: completeProductionStructuredSection({
      checkId: 'icp-evidence',
      role: 'icp-evidence',
      task: 'confirm mid-market cargo e-bike OEM or fleet-integrator fit and exclude consumer replacement, final-certified procurement, price-only sourcing, and incomplete-input projects',
      targetUrl: productionLearnOwnerPage,
      extra: 'icp_fit: mid-market cargo e-bike OEM engineering teams able to document loaded mass, wheel envelope, route duty, controller limits, and mechanical interfaces before sample-validation planning\nicp_exclusion: consumer replacements, price-only sourcing, final-certified procurement, and teams unable to provide the five bounded assumptions are excluded',
    }),
  });
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-buyer-task-evidence.md', title: 'Production buyer task evidence', kind: 'buyer-task', heading: 'Buyer task',
    section: completeProductionStructuredSection({ checkId: 'buyer-task', role: 'buyer-task', task: targetTask('buyer-task'), extra: 'buyer_task: learn how five cargo e-bike hub-motor assumptions affect later sample-validation evidence work\nbuyer_role: Engineer' }),
  });
  const queryRows = productionLearnQueries.map((query) => `${query}|complete|cargo e-bike hub-motor concept input self-check|concept input self-check|learn|none|United States|en|desktop|2026-08-02|production-query-evidence.md#query-evidence`).join('\n');
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-query-evidence.md', title: 'Production query evidence', kind: 'query-evidence', heading: 'Query evidence',
    section: `${completeProductionStructuredSection({ checkId: 'query-evidence', role: 'query-evidence', task: `validate the ${productionLearnQueries[0]} query for United States query-evidence` })}\nquery|action|object|observable-output|stage|commercial-commitment|market|language|device|checked_at|evidence_ref\n${queryRows}`,
  });
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-search-demand-evidence.md', title: 'Production search demand evidence', kind: 'search-demand', heading: 'Search demand',
    section: `${completeProductionStructuredSection({ checkId: 'search-demand', role: 'search-demand', task: targetTask('search-demand') })}\nexact_query_set: ${productionLearnQueries.join('; ')}\nsource_or_platform: Google Search Console immutable export\nmarket: United States\nlanguage: en\ndevice: desktop\nobservation_window: 2026-06-01 to 2026-07-31\nmetric_type: search impressions\nbrand_non_brand_boundary: branded queries excluded and non-brand queries measured\nzero_or_low_demand_decision: keep the bounded target because non-zero demand was observed\nseasonality_or_trend_note: seasonality reviewed and trend remained stable\nanalyst_conclusion: observed search impressions support this bounded educational query set\nsnapshot_ref: gsc-export-2026-07-31.json\nsnapshot_digest: ${searchDemandSnapshotDigest}
${snapshotBindingText('search-demand', productionLearnQueries[0])}
observed_value_per_query:
${productionLearnQueries.map((query, index) => `  - ${query}|${90 - index * 15}|impressions`).join('\n')}`,
  });
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-serp-format-evidence.md', title: 'Production SERP format evidence', kind: 'serp-format', heading: 'SERP format',
    section: `${completeProductionStructuredSection({ checkId: 'serp-format', role: 'serp-format', task: targetTask('serp-format') })}\nquery_set: ${JSON.stringify(productionLearnQueries)}\nmarket: United States\nlanguage: en\ndevice: desktop\nchecked_at: 2026-08-02\nresult_types: ${JSON.stringify(serpResultTypes)}\nprimary_query: ${productionLearnQueries[0]}\nprimary_query_sample_size: 5\nprimary_query_result_type_counts: ${JSON.stringify(serpPrimaryResultTypeCounts)}\nprimary_query_dominant_result_type: ${serpPrimaryDominantType}\nprimary_query_dominant_result_count: ${serpPrimaryDominantCount}\nprimary_query_dominance_threshold: 0.60\nprimary_query_dominance_verdict: pass\nsupporting_query_result_type_rows: ${JSON.stringify(productionSupportingSerpRows(productionLearnQueries))}\nsnapshot_ref: serp-format-corpus-2026-08-02.json\nsnapshot_digest: ${serpFormatSnapshotDigest}
${snapshotBindingText('serp-format', productionLearnQueries[0])}\n\n${productionSupportingSerpFragments(productionLearnQueries)}`,
  });
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-serp-gap-evidence.md', title: 'Production SERP gap evidence', kind: 'serp-gap', heading: 'SERP gap',
    section: completeProductionStructuredSection({ checkId: 'serp-gap', role: 'serp-gap', task: targetTask('serp-gap'), extra: 'gap_finding: sampled results explain motor basics but do not connect the five bounded assumptions to later sample-validation evidence work\naccepted_information_gain: one self-contained concept checklist with explicit non-fit and no-commercial boundaries' }),
  });
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-information-gain-artifact.md', title: 'Production decision artifact evidence', kind: 'information-gain-artifact', heading: 'Decision artifact',
    section: 'The article contains a five-input checklist decision artifact that separates complete assumptions, missing assumptions, and later evidence questions before project-readiness interpretation.',
  });
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-information-gain-market.md', title: 'Production market information gain evidence', kind: 'market-information-gain', heading: 'Market information gain',
    section: `observed_at: 2026-08-02T00:00:00Z
${productionMarketComparisonEvidence(marketComparisonPayload)}
snapshot_ref: independent-serp-corpus-2026-08-02.json
snapshot_digest: ${marketComparisonSnapshotDigest}
${snapshotBindingText('market-comparison', productionLearnQueries[0])}
reviewer: Taylor Morgan, Independent Buyer Review Lead
An independent market review confirmed buyer-usable information within the declared boundary.`,
  });
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-inventory-evidence.md', title: 'Production inventory zero result evidence', kind: 'inventory-zero-result', heading: 'Inventory zero result',
    section: `${completeProductionStructuredSection({ checkId: 'inventory-zero-result', role: 'owner-page', task: `${productionLearnQueries[0]} inventory zero-result check` })}\nscope: United States English production article inventory\nchecked_at: 2026-08-02T00:00:00Z\nretrieval_dimensions: ["url","slug","title","query","buyer-task","stage","taxonomy"]\nsnapshot_ref: production-content-inventory-2026-08-02.json\nsnapshot_digest: ${contentInventorySnapshotDigest}
${snapshotBindingText('content-inventory', productionLearnQueries[0])}\nquery: ${productionLearnQueries[0]}\nmarket: United States\nlanguage: en\nstage: learn\ncandidate_count: 0\nconflict_candidates: []\nThe independent inventory review found no matching competing owner page for this exact intent.`,
  });
  setupMobileReadabilityEvidence(dir, {
    targetUrl: productionLearnOwnerPage,
    renderTarget: productionLearnOwnerPage,
    targetTask: `320px mobile readability review for ${productionLearnTitle}`,
  });
}

test('P1 live-production-shaped Learn baseline passes structural validator-branch checks only and does not prove real production', (t) => {
  expectPass(makeFixture(t, completeProductionLearnMutations(), setupCompleteProductionLearnEvidence));
});

const productionCtaDataContract = {
  destination: 'https://www.fluxpedal-motors.com/contact/engineering-readiness-review',
  mode: 'technical-review',
  trigger: 'all five first-round engineering inputs are available for a bounded readiness review',
  output: 'packet completeness, a missing-evidence list, and the next review step in round one; only after the complete second-round package and named technical-owner review may the owner return candidate-or-stop',
  purpose: 'Use the five engineering inputs only to perform the bounded engineering-readiness review and identify missing validation evidence.',
  retention: 'Retain the packet only until the review closes or 30 days after the last review activity, whichever comes first.',
  deletion: 'After a verified route exists, request deletion through that route; while no route exists, the buyer controls and may delete the local copy.',
  owner: 'Avery Chen, Applications Engineering Lead',
  id: 'CTA-DATA-PROD-ENGINEERING-001',
  version: '2026.08.01',
  effectiveAt: '2026-08-01T00:00:00Z',
  checkedAt: '2026-08-02T00:00:00Z',
  observedAt: '2026-08-02T00:00:00Z',
  reviewedAt: '2026-08-02T12:00:00Z',
  reviewCeiling: '2026-08-02T16:00:00Z',
  policyArtifactRef: 'artifacts/cta-data-policy-contract.txt',
  policyArtifactBytes: 'CTA-DATA-PROD-ENGINEERING-001|2026.08.01|bounded engineering-readiness review|30-day-or-review-close retention|verified deletion path\n',
  policyRef: 'production-cta-data-policy.md#cta-data-policy',
  deletionRef: 'production-cta-deletion-capability.md#cta-deletion-capability',
};
productionCtaDataContract.digest = `sha256:${createHash('sha256').update(productionCtaDataContract.policyArtifactBytes).digest('hex')}`;

const productionFallbackCtaDataContract = {
  ...productionCtaDataContract,
  id: 'CTA-DATA-PROD-FALLBACK-001',
  version: '2026.08.01-fallback',
  policyArtifactRef: 'artifacts/cta-data-fallback-policy-contract.txt',
  policyArtifactBytes: 'CTA-DATA-PROD-FALLBACK-001|2026.08.01-fallback|bounded engineering-readiness fallback|30-day-or-review-close retention|verified deletion path\n',
  policyRef: 'production-fallback-data-policy.md#fallback-data-policy',
  deletionRef: 'production-fallback-deletion-capability.md#fallback-deletion-capability',
};
productionFallbackCtaDataContract.digest = `sha256:${createHash('sha256').update(productionFallbackCtaDataContract.policyArtifactBytes).digest('hex')}`;


const productionValidateQueries = [
  'cargo hub motor engineering readiness checklist',
  'cargo e-bike hub motor engineering readiness checklist',
  'cargo hub motor engineering review inputs',
  '20 inch cargo hub motor engineering readiness inputs',
];
const productionValidateOwnerPage = productionLearnOwnerPage;
const productionValidateSolutionUrl = 'https://www.fluxpedal-motors.com/solutions/cargo-hub-motor-candidates';
const productionValidateTechnicalUrl = 'https://www.fluxpedal-motors.com/guides/cargo-ebike-sample-validation';
const productionValidateFallbackUrl = 'https://www.fluxpedal-motors.com/contact/engineering-fallback';
const productionValidateFallbackPolicyRef = 'production-fallback-data-policy.md#fallback-data-policy';
const productionValidateFallbackDeletionRef = 'production-fallback-deletion-capability.md#fallback-deletion-capability';

function productionCollectionPolicyRows({
  primaryRequiredInputsMode = 'same-as-cta-required-inputs',
  fallbackRequiredInputsMode = 'same-as-cta-required-inputs',
  fallbackEndpoint = productionValidateFallbackUrl,
  fallbackPolicyRefs = [productionValidateFallbackPolicyRef],
  fallbackDeletionRefs = [productionValidateFallbackDeletionRef],
} = {}) {
  const row = ({ routeId, endpoint, requiredInputsMode, contract, policyRefs, deletionRefs }) => [
    routeId,
    endpoint,
    requiredInputsMode,
    contract.purpose,
    contract.retention,
    contract.deletion,
    contract.owner,
    contract.id,
    contract.version,
    contract.digest,
    contract.checkedAt,
    contract.observedAt,
    contract.reviewedAt,
    contract.reviewCeiling,
    'confirmed',
    'accepted',
    policyRefs.join(','),
    deletionRefs.join(','),
  ].join('|');
  const rows = [];
  if (primaryRequiredInputsMode !== 'none') rows.push(row({
    routeId: 'primary',
    endpoint: productionCtaDataContract.destination,
    requiredInputsMode: primaryRequiredInputsMode,
    contract: productionCtaDataContract,
    policyRefs: [productionCtaDataContract.policyRef],
    deletionRefs: [productionCtaDataContract.deletionRef],
  }));
  if (fallbackRequiredInputsMode !== 'none') rows.push(row({
    routeId: 'fallback',
    endpoint: fallbackEndpoint,
    requiredInputsMode: fallbackRequiredInputsMode,
    contract: productionFallbackCtaDataContract,
    policyRefs: fallbackPolicyRefs,
    deletionRefs: fallbackDeletionRefs,
  }));
  return rows;
}

const productionValidateInternalLinkRefs = {
  acceptance: ['production-internal-link-acceptance-evidence.md#solution-target', 'production-internal-link-acceptance-evidence.md#technical-review-target'],
  reference: ['production-internal-link-reference-evidence.md#solution-target', 'production-internal-link-reference-evidence.md#technical-review-target'],
  reachability: ['production-internal-link-reachability-evidence.md#solution-target', 'production-internal-link-reachability-evidence.md#technical-review-target'],
  capability: ['production-internal-link-capability-evidence.md#solution-target', 'production-internal-link-capability-evidence.md#technical-review-target'],
};
const productionValidateCapabilityProofCopy = 'Applications Engineering applies the same five-input basis and returns packet completeness, a missing-evidence list, and the next review step in round one; only after the complete second-round package and named technical-owner review may it return candidate-or-stop. This does not prove product fit, commercial acceptance, or response timing.';
const productionValidateBuyerCondition = '20-inch cargo e-bike program with a complete five-input first-round packet and no observed interface conflict';
const productionValidateDecisionVariable = 'loaded vehicle mass and payload range, target wheel diameter and tire envelope, route grade and repeated-duty profile, battery voltage and controller current limits, axle/dropout/brake interface summary';
const productionValidateNoFit = 'stop only when an evidenced axle/dropout/brake incompatibility, out-of-envelope controller or measured-duty result, or explicitly unsupported technical scope is established';
const productionValidateRemainingInputs = 'target speed and controller speed limit; detailed duty-cycle, ambient, repetition, and thermal test method; exact axle and dropout drawing plus connector, sensor, cable, and controller-interface details; target market and vehicle category; sample timeline and acceptance criteria';
const productionValidateProductDecisionRef = 'production-product-decision-evidence.md#cargo-hub-motor-candidate-decision';
const productionValidateProductDecisionRow = `${productionValidateBuyerCondition}|${productionValidateDecisionVariable}|${productionValidateProductDecisionRef}|${productionValidateNoFit}|${productionValidateRemainingInputs}|candidate|${productionValidateSolutionUrl}|${productionValidateTechnicalUrl}|direct-answer section, candidate-or-stop section, and final CTA`;
const productionValidateSecondaryBuyerRoleRow = 'Quality|production-secondary-buyer-role-evidence.md#quality-role|Quality needs explicit project-specific bench and vehicle acceptance evidence before accepting a technically qualified candidate for sample validation.|The article preserves assumptions and unresolved risks, then routes the accepted technical boundary to Quality for the next validation-evidence task.';
const productionValidateActionJudgment = 'A bounded engineering-readiness review should start only after all five first-round inputs are complete.';
const productionValidateCommitmentBoundary = 'The output is limited to a technical readiness assessment; commercial contracting and transaction decisions remain outside this review.';
const productionValidateSubmissionMethod = 'Submit the complete five-input packet only through the verified primary route shown in this CTA; a separately verified contingency route is provided below.';
const productionValidatePrimaryRequestInstruction = 'Request the bounded engineering-readiness review with the complete five-input packet.';
const productionValidatePrimaryInventoryInstruction = `${productionValidateActionJudgment} ${productionValidatePrimaryRequestInstruction}`;
const productionValidateSolutionInstruction = 'Review the cargo hub-motor solution-family boundary and unresolved inputs before selecting a candidate.';
const productionValidateTechnicalInstruction = 'Define the next cargo e-bike sample-validation evidence before treating the candidate as technically qualified.';
const canonicalWithheldInternalLinksParagraph = 'This demonstration intentionally withholds product and validation links. Those links should appear only after the target content, destination availability, receiving capability, and buyer-task fit have all been verified; a placeholder would imply evidence that does not yet exist.';
const canonicalTechnicalReadinessBoundary = '**Technical readiness advances the engineering task. It does not automatically advance the buying task.**';

function completeProductionValidateMutations() {
  const fallbackCopy = verifiedFallbackCopy({ endpoint: productionValidateFallbackUrl });
  const fallbackContract = verifiedFallbackContract({
    endpoint: productionValidateFallbackUrl,
    commitmentBoundary: productionValidateCommitmentBoundary,
  });
  const internalTargets = [
    `solution|${productionValidateSolutionUrl}|identify unresolved inputs in the cargo hub-motor solution-family boundary before selecting or stopping a candidate direction`,
    `technical-review|${productionValidateTechnicalUrl}|define the next sample-validation evidence`,
  ];
  const internalContracts = [
    `solution|${productionValidateSolutionUrl}|identify unresolved inputs in the cargo hub-motor solution-family boundary before selecting or stopping a candidate direction|review the solution family boundary and unresolved inputs|Engineer|candidate-or-stop section|confirmed|Morgan Lee, Product Content Lead|${productionValidateInternalLinkRefs.acceptance[0]}`,
    `technical-review|${productionValidateTechnicalUrl}|define the next sample-validation evidence|prepare the next bench and vehicle validation task|Quality|next-validation section|confirmed|Jordan Rivera, Quality Validation Lead|${productionValidateInternalLinkRefs.acceptance[1]}`,
  ];
  const roleHandoffs = [
    `Engineer|Applications Engineering|${productionCtaDataContract.destination}|provide the five-input readiness packet and keep commercial commitment at none|return packet completeness, a missing-evidence list, and the next review step; do not return candidate-or-stop before the complete second-round package and named technical-owner review|${productionCtaDataContract.owner}|production-role-handoff-acceptance-evidence.md#engineering-review-handoff`,
    `Engineer|Quality|${productionValidateTechnicalUrl}|retain the technical-qualified candidate boundary, duty assumptions, and unresolved risks|define project-specific bench and vehicle acceptance evidence after technical qualification|Jordan Rivera, Quality Validation Lead|production-role-handoff-acceptance-evidence.md#quality-validation-handoff`,
  ];
  const capabilityProofs = [
    `review-method|prepare a bounded cargo hub-motor candidate-readiness review|the technical owner returns packet completeness, a missing-evidence list, and the next review step in round one; only after the complete second-round package and named technical-owner review may the owner return candidate-or-stop|production-capability-proof-evidence.md#bounded-engineering-review-capability|${productionValidateCapabilityProofCopy}|required`,
  ];
  const fallbackRows = new Map([
    ['fallback-do-not-send-01', fallbackCopy.verifiedStrong],
    ['fallback-route-request-01', fallbackCopy.verifiedParagraph],
    ['fallback-copyable-message-01', fallbackCopy.verifiedFallbackMessage],
    ['primary-bounded-review-01', fallbackCopy.verifiedPost],
  ]);
  const common = {
    package_id: 'PROD-CARGO-MOTOR-VALIDATE-001',
    owner_page: productionValidateOwnerPage,
    evidence_scope: 'production',
    evidence_origin: 'live-production',
    fixture_identity: 'not-applicable',
    production_proof_eligible: true,
    author_id: 'wco-content-author-001',
    producer_id: 'wco-evidence-producer-001',
    independent_reviewer_id: 'wco-independent-reviewer-001',
    remediation_participant_ids: [],
    identity_provenance_observed_at: '2026-08-02T00:00:00Z',
    identity_provenance_reviewed_at: '2026-08-02T12:00:00Z',
    identity_provenance_review_ceiling: '2026-08-02T16:00:00Z',
    identity_provenance_evidence_refs: ['production-identity-provenance.md#identity-provenance'],
    reviewer_separation_verdict: 'pass',
    primary_icp: 'mid-market cargo e-bike OEM or fleet-integrator engineering teams able to provide bounded readiness inputs',
    explicit_icp_exclusions: ['consumer replacement shoppers', 'price-only sourcing teams'],
    icp_fit_contract: 'Mid-market cargo e-bike OEM or fleet-integrator engineering teams before candidate review, when a cargo program has bounded load, wheel, duty, electrical, and interface records ready for engineering-readiness review.',
    icp_exclusion_contract: 'Consumer replacement shoppers and price-only sourcing teams without the declared engineering inputs are excluded.',
    icp_fit_contract_snapshot: 'Mid-market cargo e-bike OEM or fleet-integrator engineering teams before candidate review, when a cargo program has bounded load, wheel, duty, electrical, and interface records ready for engineering-readiness review.',
    icp_exclusion_contract_snapshot: 'Consumer replacement shoppers and price-only sourcing teams without the declared engineering inputs are excluded.',
    cta_route_transmission_verdict: 'pass',
    cta_from_role: 'Engineer',
    cta_to_role: 'Applications Engineering',
    cta_receiving_task: 'return packet completeness, a missing-evidence list, and the next review step; do not return candidate-or-stop before the complete second-round package and named technical-owner review',
    cta_receiving_owner: productionCtaDataContract.owner,
    icp_evidence_status: 'confirmed',
    icp_evidence_refs: ['production-icp-evidence.md#icp-evidence'],
    icp_evidence_status_snapshot: 'confirmed',
    icp_evidence_refs_snapshot: ['production-icp-evidence.md#icp-evidence'],
    query_evidence_status: 'confirmed',
    query_evidence_refs: ['production-query-evidence.md#query-evidence'],
    buyer_task_evidence_status: 'confirmed',
    buyer_task_evidence_refs: ['production-buyer-task-evidence.md#buyer-task'],
    search_demand_evidence_status: 'confirmed',
    search_demand_observation_start_at: '2026-06-01T00:00:00Z',
    search_demand_observation_end_at: '2026-07-31T23:59:59Z',
    search_demand_evidence_refs: ['production-search-demand-evidence.md#search-demand'],
    serp_format_evidence_status: 'confirmed',
    serp_format_evidence_refs: ['production-serp-format-evidence.md#serp-format'],
    serp_gap_status: 'confirmed',
    serp_gap_refs: ['production-serp-gap-evidence.md#serp-gap'],
    customer_language_status: 'confirmed', customer_language_refs: ['production-customer-language-evidence.md#customer-language'], customer_language_gate_verdict: 'pass',
    pain_evidence_status: 'confirmed', pain_evidence_refs: ['production-pain-evidence.md#pain-evidence'], pain_evidence_gate_verdict: 'pass',
    first_party_proof_status: 'inferred', first_party_proof_refs: [],
    primary_buyer_evidence_refs: ['production-buyer-task-evidence.md#buyer-task'],
    content_inventory_refs: ['production-inventory-evidence.md#inventory-zero-result'],
    serp_evidence_ref: 'production-serp-format-evidence.md#serp-format',
    information_gain_artifact_status: 'confirmed',
    information_gain_artifact_refs: ['production-information-gain-artifact.md#decision-artifact'],
    market_information_gain_status: 'confirmed',
    information_gain_market_refs: ['production-information-gain-market.md#market-information-gain'],
    content_inventory_status: 'confirmed',
    inventory_snapshot_ref: 'production-inventory-evidence.md#inventory-zero-result',
    inventory_zero_result_evidence_refs: ['production-inventory-evidence.md#inventory-zero-result'],
    production_search_evidence_gate_verdict: 'pass',
    structure_review_verdict: 'pass', production_evidence_review_verdict: 'pass', serp_content_type_parity_verdict: 'pass', fatal_gate_verdict: 'pass',
    production_readiness: 'ready', release_decision: 'ready-for-cms-draft', operation_mode: 'dry-run',
    mobile_visual_check_execution_status: 'executed', mobile_visual_evidence_result: 'confirmed', mobile_visual_gate_verdict: 'pass',
    mobile_visual_evidence_refs: ['mobile-readability-evidence.md#mobile-readability'],
    serp_primary_query: productionValidateQueries[0],
    serp_primary_query_sample_size: '5', serp_primary_query_dominant_result_type: 'checklist', serp_primary_query_dominant_result_count: '3',
    serp_primary_query_dominance_threshold: '0.60', serp_primary_query_dominance_verdict: 'pass', serp_primary_query_result_type_counts: ['checklist|3', 'guide|2'],
    serp_supporting_query_result_type_rows: productionSupportingSerpRows(productionValidateQueries),
    role_handoff_contracts: roleHandoffs,
    internal_link_targets: internalTargets, internal_link_targets_snapshot: internalTargets,
    internal_link_buyer_task_contracts: internalContracts, internal_link_buyer_task_contracts_snapshot: internalContracts,
    internal_link_reference_check_execution_status: 'executed', internal_link_reference_evidence_result: 'confirmed', internal_link_reference_gate_verdict: 'pass', internal_link_reference_evidence_refs: productionValidateInternalLinkRefs.reference,
    internal_link_reachability_check_execution_status: 'executed', internal_link_reachability_evidence_result: 'confirmed', internal_link_reachability_gate_verdict: 'pass', internal_link_reachability_evidence_refs: productionValidateInternalLinkRefs.reachability,
    internal_link_capability_check_execution_status: 'executed', internal_link_capability_evidence_result: 'confirmed', internal_link_capability_gate_verdict: 'pass', internal_link_capability_evidence_refs: productionValidateInternalLinkRefs.capability,
    cta_interaction_type: 'human-handoff', cta_input_collection_applicability: 'applicable', cta_input_collection_not_applicable_reason: 'not-applicable',
    stage_cta_mode: productionCtaDataContract.mode, cta_owner: productionCtaDataContract.owner, cta_destination: productionCtaDataContract.destination,
    cta_trigger: productionCtaDataContract.trigger, cta_expected_output: productionCtaDataContract.output,
    cta_submission_method: productionValidateSubmissionMethod,
    cta_commitment_boundary: productionValidateCommitmentBoundary,
    cta_data_purpose: productionCtaDataContract.purpose, cta_data_retention_period: productionCtaDataContract.retention,
    cta_data_deletion_path: productionCtaDataContract.deletion, cta_data_retention_owner: productionCtaDataContract.owner,
    cta_data_policy_contract_id: productionCtaDataContract.id, cta_data_policy_status: 'confirmed',
    cta_data_policy_effective_at: productionCtaDataContract.effectiveAt, cta_data_policy_checked_at: productionCtaDataContract.checkedAt,
    cta_data_policy_version: productionCtaDataContract.version, cta_data_policy_digest: productionCtaDataContract.digest,
    cta_data_policy_observed_at: productionCtaDataContract.observedAt, cta_data_policy_reviewed_at: productionCtaDataContract.reviewedAt,
    cta_data_policy_review_ceiling: productionCtaDataContract.reviewCeiling,
    cta_data_policy_owner_acceptance: 'accepted', cta_data_policy_evidence_refs: [productionCtaDataContract.policyRef],
    cta_data_deletion_capability_evidence_refs: [productionCtaDataContract.deletionRef],
    cta_reference_check_execution_status: 'executed', cta_reference_evidence_result: 'confirmed', cta_reference_gate_verdict: 'pass', cta_reference_evidence_refs: ['production-cta-reference-evidence.md#cta-reference'],
    cta_reachability_check_execution_status: 'executed', cta_reachability_evidence_result: 'confirmed', cta_reachability_gate_verdict: 'pass', cta_reachability_evidence_refs: ['production-cta-reachability-evidence.md#cta-reachability'],
    cta_capability_check_execution_status: 'executed', cta_capability_evidence_result: 'confirmed', cta_capability_gate_verdict: 'pass', cta_capability_evidence_refs: ['production-cta-capability-evidence.md#cta-capability'],
    cta_fallback_route_contract: fallbackContract,
    cta_collection_route_policy_contracts: productionCollectionPolicyRows(),
    cta_fallback_message_template: fallbackCopy.verifiedFallbackMessage,
    cta_buyer_visible_capability_proofs: capabilityProofs, cta_buyer_visible_capability_proofs_snapshot: capabilityProofs,
    secondary_buyer_role_contracts: [productionValidateSecondaryBuyerRoleRow],
    product_decision_map: [productionValidateProductDecisionRow],
    product_decision_map_snapshot: [productionValidateProductDecisionRow],
  };
  return Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => {
    let output = projectToCurrentTemplate(content, templateNames[key]);
    output = output
      .replaceAll('https://example.test/contact/engineering-readiness-review', productionCtaDataContract.destination)
      .replaceAll('https://example.test/solutions/cargo-hub-motor-candidates', productionValidateSolutionUrl)
      .replaceAll('https://example.test/guides/cargo-ebike-sample-validation', productionValidateTechnicalUrl)
      .replaceAll('Jordan Rivera, Quality Validation Lead (synthetic)', 'Jordan Rivera, Quality Validation Lead')
      .replaceAll('Morgan Lee, Commercial Account Owner (synthetic)', 'Morgan Lee, Commercial Account Owner')
      .replaceAll('synthetic product card', 'confirmed product capability record')
      .replaceAll('search-evidence.md#buyer-visible-capability-proof-fixture', 'production-capability-proof-evidence.md#bounded-engineering-review-capability');
    for (const [field, value] of Object.entries(common)) output = replaceIfPresent(output, field, JSON.stringify(value));
    output = mutateJsonArrayField(output, 'buyer_visible_cta_inventory', (rows) => {
      const adjusted = rows.map((row) => {
        const parts = row.split('|');
        if (fallbackRows.has(parts[0])) {
          const originalId = parts[0];
          if (originalId === 'primary-bounded-review-01') parts[0] = 'fallback-bounded-review-01';
          parts[3] = fallbackRows.get(originalId);
          parts[4] = productionValidateFallbackUrl;
          parts[5] = productionCtaDataContract.owner;
          parts[6] = 'human-handoff';
          parts[7] = 'verified';
          parts[8] = verifiedFallbackEvidenceRefs.capability;
          parts[9] = 'cta_fallback_route_contract';
        }
        if (parts[0] === 'soft-solution-family-01') { parts[3] = productionValidateSolutionInstruction; parts[4] = productionValidateSolutionUrl; parts[8] = productionValidateInternalLinkRefs.acceptance[0]; }
        if (parts[0] === 'soft-sample-validation-01') { parts[3] = productionValidateTechnicalInstruction; parts[4] = productionValidateTechnicalUrl; parts[5] = 'Jordan Rivera, Quality Validation Lead'; parts[8] = productionValidateInternalLinkRefs.acceptance[1]; }
        return parts.join('|');
      });
      adjusted.push(`primary-engineering-review-01|paragraph|owner output and route boundary|${productionValidatePrimaryInventoryInstruction}|${productionCtaDataContract.destination}|${productionCtaDataContract.owner}|human-handoff|verified|production-cta-capability-evidence.md#cta-capability|cta_fallback_route_contract`);
      const byId = new Map(adjusted.map((row) => [row.split('|')[0], row]));
      const bodyOrder = [
        'soft-opening-readiness-01',
        'soft-solution-family-01',
        'soft-sample-validation-01',
        'soft-local-worksheet-01',
        'primary-engineering-review-01',
        'fallback-do-not-send-01',
        'fallback-route-request-01',
        'fallback-copyable-message-01',
        'fallback-bounded-review-01',
      ];
      assert.equal(byId.size, bodyOrder.length, 'production CTA inventory must contain exactly the expected buyer-visible surfaces');
      return bodyOrder.map((id) => {
        assert.ok(byId.has(id), `production CTA inventory is missing ${id}`);
        return byId.get(id);
      });
    });
    output = bindProjectedCtaMapsToInventory(output, {
      pageVersion: 'cargo-motor-validate-article-v1',
      stagePrefix: 'validate',
      technicalQualification: true,
      commercialAcceptance: false,
      surfaces: [
        { id: 'primary-engineering-review-01', role: 'primary', outcome: 'receive packet completeness, a missing-evidence list, and the next review step after the complete five-input review', routeId: 'engineering-review-primary-v1' },
        { id: 'soft-solution-family-01', role: 'soft', outcome: 'review the cargo hub-motor solution-family boundary and unresolved inputs before selecting a candidate', routeId: 'solution-family-navigation-v1' },
        { id: 'fallback-bounded-review-01', role: 'fallback', outcome: 'use the verified contingency route for the same bounded engineering-readiness output if the primary route is unavailable', routeId: 'engineering-review-fallback-v1' },
      ],
    });
    if (key === 'briefPath' || key === 'draftPath') {
      output = mutateJsonArrayField(output, 'semantic_emphasis_plan', (rows) => rows.map((row) => /^(?:route|action)\|/.test(row)
        ? `action|${productionValidateActionJudgment}|request a bounded engineering-readiness review`
        : row));
    }
    if (key === 'draftPath') {
      output = transformBody(output, (body) => replaceRequiredLiteral(
        replaceRequiredLiteral(
          body,
          canonicalWithheldInternalLinksParagraph,
          `[${productionValidateSolutionInstruction}](${productionValidateSolutionUrl})`,
          'production solution-family internal link',
        ),
        canonicalTechnicalReadinessBoundary,
        `${canonicalTechnicalReadinessBoundary}\n\n[${productionValidateTechnicalInstruction}](${productionValidateTechnicalUrl})`,
        'production sample-validation internal link',
      ));
      output = transformBody(output, (body) => replaceOwnerRouteSection(body, `### When to request the review

Trigger: When the local readiness worksheet is complete and all five first-round engineering inputs are available for a bounded readiness review.

**${productionValidateActionJudgment}** [${productionValidatePrimaryRequestInstruction}](${productionCtaDataContract.destination})

### What to keep ready

Required inputs: Keep the completed readiness worksheet ready for the verified route. Do not recreate the five input fields in this section.

- Owner: ${productionCtaDataContract.owner}.
- Data purpose: ${productionCtaDataContract.purpose}
- Retention period: ${productionCtaDataContract.retention}
- Deletion path: ${productionCtaDataContract.deletion}
- Retention owner: ${productionCtaDataContract.owner}.
- Expected output: packet completeness, a missing-evidence list, and the next review step; only after the complete second-round package and named technical-owner review may Applications Engineering return candidate-or-stop.
- Response expectation: Response timing has not been verified and must be confirmed before any service promise is made.
- Submission method: ${productionValidateSubmissionMethod}
- Confidentiality boundary: Do not send confidential drawings, credentials, personal data, or controlled files unless the verified route and its handling controls cover them.
- Commitment boundary: ${productionValidateCommitmentBoundary}

${productionValidateCapabilityProofCopy}

### What Applications Engineering should return

Expected engineering output: packet completeness, a missing-evidence list, and the next review step; only after the complete second-round package and named technical-owner review may Applications Engineering return candidate-or-stop.

### Verified contingency route

${fallbackCopy.verifiedStrongMarkdown}

${fallbackCopy.verifiedParagraphMarkdown}

### Copyable local fallback

> ${fallbackCopy.verifiedFallbackMessageMarkdown}

${fallbackCopy.verifiedPostMarkdown}`));
      const publishableBody = extractPublishableArticleMarkdown(output);
      assert.equal(publishableBody.split(`[${productionValidateSolutionInstruction}](${productionValidateSolutionUrl})`).length - 1, 1, 'production solution-family internal link must exist exactly once in the publishable body');
      assert.equal(publishableBody.split(`[${productionValidateTechnicalInstruction}](${productionValidateTechnicalUrl})`).length - 1, 1, 'production sample-validation internal link must exist exactly once in the publishable body');
      assert.equal(publishableBody.includes(canonicalWithheldInternalLinksParagraph), false, 'production publishable body must remove the withheld-link negative-fixture paragraph');
    }
    if (key === 'briefPath' || key === 'publishPath') {
      output = transformDocumentBody(output, (body) => replaceRequiredLiteral(body, canonicalRouteAndPolicyFallbackFor(key), fallbackCopy.verifiedFallbackMessage, `production ${key} fallback narrative`));
      if (key === 'briefPath') {
        output = transformMarkdownSection(output, '## 7. Internal-link task contracts', '## 8. Progressive CTA contract', () => `## 7. Internal-link task contracts

| Link | Buyer task advanced | Owner | Acceptance requirement |
|---|---|---|---|
| [${productionValidateSolutionInstruction}](${productionValidateSolutionUrl}) | Review the solution-family direction and unresolved inputs after the readiness check. | Morgan Lee, Product Content Lead | Present the candidate scope and unresolved evidence without acting as a submission route. |
| [${productionValidateTechnicalInstruction}](${productionValidateTechnicalUrl}) | Define the next bench and vehicle evidence after the candidate becomes technically qualified. | Jordan Rivera, Quality Validation Lead | Preserve the first-round boundary and define project-specific validation evidence. |

These are content-navigation links only; neither is a submission endpoint. The engineering-review submission route is governed separately by \`cta_fallback_route_contract\`.

`);
      } else {
        output = transformMarkdownSection(output, '## 3. Internal-link targets and CTA route status', '## 3A. Semantic contract projection', () => `## 3. Internal-link targets and CTA route status

### Content-navigation links

| Target | Assigned task | Reference parity | Reachability | Capability / task acceptance |
|---|---|---|---|---|
| [${productionValidateSolutionInstruction}](${productionValidateSolutionUrl}) | Review the solution-family direction and unresolved inputs. | \`executed / confirmed / pass\` | \`executed / confirmed / pass\` | \`executed / confirmed / pass\` |
| [${productionValidateTechnicalInstruction}](${productionValidateTechnicalUrl}) | Define the next bench and vehicle evidence after technical qualification. | \`executed / confirmed / pass\` | \`executed / confirmed / pass\` | \`executed / confirmed / pass\` |

These two URLs are content-navigation targets only; neither is a submission endpoint. CTA submission routing is recorded separately.

### CTA route status

- Route status: \`verified\`.
- Endpoint: verified canonical CTA route recorded outside this content-navigation section.
- Accountable output owner: ${productionCtaDataContract.owner}.
- Production reference, reachability, and capability gates: \`executed / confirmed / pass\`.

`);
      }
    }
    if (key === 'reviewPath') {
      output = replaceField(output, 'reviewer_identity', '"Taylor Morgan, Independent Buyer Review Lead"');
      output = replaceField(output, 'reviewed_at', '"2026-08-03T00:00:00+08:00"');
      output = replaceIfPresent(output, 'production_evidence_score', '"100"');
      output = replaceIfPresent(output, 'visual_decision_assets_verdict', '"pass"');
      for (const field of fatalReviewVerdicts) output = replaceIfPresent(output, field, '"pass"');
    }
    return output;
  }]));
}

function productionCollectingPolicyMutations() {
  const base = completeProductionLearnMutations();
  const values = {
    stage: 'validate',
    stage_intake_contract: 'validate-technical',
    cta_interaction_type: 'human-handoff',
    cta_input_collection_applicability: 'applicable',
    cta_input_collection_not_applicable_reason: 'not-applicable',
    stage_cta_mode: productionCtaDataContract.mode,
    cta_owner: productionCtaDataContract.owner,
    cta_destination: productionCtaDataContract.destination,
    cta_trigger: productionCtaDataContract.trigger,
    cta_expected_output: productionCtaDataContract.output,
    cta_data_purpose: productionCtaDataContract.purpose,
    cta_data_retention_period: productionCtaDataContract.retention,
    cta_data_deletion_path: productionCtaDataContract.deletion,
    cta_data_retention_owner: productionCtaDataContract.owner,
    cta_data_policy_contract_id: productionCtaDataContract.id,
    cta_data_policy_status: 'confirmed',
    cta_data_policy_effective_at: productionCtaDataContract.effectiveAt,
    cta_data_policy_checked_at: productionCtaDataContract.checkedAt,
    cta_data_policy_owner_acceptance: 'accepted',
    cta_data_policy_evidence_refs: [productionCtaDataContract.policyRef],
    cta_data_deletion_capability_evidence_refs: [productionCtaDataContract.deletionRef],
    cta_reference_check_execution_status: 'executed',
    cta_reference_evidence_result: 'confirmed',
    cta_reference_gate_verdict: 'pass',
    cta_reference_evidence_refs: ['production-cta-reference-evidence.md#cta-reference'],
    cta_reachability_check_execution_status: 'executed',
    cta_reachability_evidence_result: 'confirmed',
    cta_reachability_gate_verdict: 'pass',
    cta_reachability_evidence_refs: ['production-cta-reachability-evidence.md#cta-reachability'],
    cta_capability_check_execution_status: 'executed',
    cta_capability_evidence_result: 'confirmed',
    cta_capability_gate_verdict: 'pass',
    cta_capability_evidence_refs: ['production-cta-capability-evidence.md#cta-capability'],
  };
  return Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => {
    let output = base[key](content);
    for (const [field, value] of Object.entries(values)) output = replaceIfPresent(output, field, JSON.stringify(value));
    if (key === 'draftPath') output = transformBody(output, (body) => `${body.trim()}

## Request the engineering-readiness review

Trigger: ${productionCtaDataContract.trigger}.

Expected output: ${productionCtaDataContract.output}.

- Data purpose: ${productionCtaDataContract.purpose}
- Retention period: ${productionCtaDataContract.retention}
- Deletion path: ${productionCtaDataContract.deletion}
- Retention owner: ${productionCtaDataContract.owner}

[Request the bounded engineering-readiness review](${productionCtaDataContract.destination})
`);
    return output;
  }]));
}

function writeProductionPolicyArtifact(dir, contract) {
  mkdirSync(join(dir, 'artifacts'), { recursive: true });
  writeFileSync(join(dir, contract.policyArtifactRef), contract.policyArtifactBytes);
  return contract.digest;
}

function productionPolicyEvidenceSection({ contract, endpoint, targetRole, task, traceRef, traceDigest, checkId, observedResult, acceptance, reviewer }) {
  return `check_id: ${checkId}
target_url: ${endpoint}
target_role: ${targetRole}
target_task: ${task}
accountable_owner: ${contract.owner}
observed_at: ${contract.observedAt}
method: independent policy and capability acceptance test bound to the exact public CTA endpoint
observed_result: ${observedResult}
capability_acceptance: ${acceptance}
policy_contract_id: ${contract.id}
policy_version: ${contract.version}
policy_digest: ${contract.digest}
policy_artifact_ref: ${contract.policyArtifactRef}
policy_artifact_digest: ${contract.digest}
cta_mode: ${contract.mode}
data_purpose: ${contract.purpose}
retention_period: ${contract.retention}
deletion_path: ${contract.deletion}
policy_effective_at: ${contract.effectiveAt}
policy_checked_at: ${contract.checkedAt}
screenshot_or_trace_ref: ${traceRef}
artifact_digest: ${traceDigest}
producer: Production CTA Data Evidence Producer
producer_id: wco-production-cta-data-producer-001
independent_reviewer: ${reviewer}
independent_reviewer_id: wco-production-cta-data-reviewer-001`;
}

function writeProductionCtaDataEvidence(dir, {
  policyKind = 'cta-data-policy',
  deletionKind = 'cta-deletion-capability',
  policyReviewer = 'Taylor Morgan, Independent Data Policy Reviewer',
  deletionObservedResult = 'The test record was deleted through the declared deletion path, and the post-deletion read returned not found so the record was no longer readable.',
  deletionCapabilityAcceptance = 'accepted and verified deletion completion plus a blocked post-deletion read',
} = {}) {
  const task = `${productionCtaDataContract.trigger} ${productionCtaDataContract.output}`;
  const traceRef = 'traces/cta-data-policy-acceptance.txt';
  const traceBytes = 'Bounded production CTA data-policy and deletion-capability acceptance trace captured on 2026-08-02.\n';
  mkdirSync(join(dir, 'traces'), { recursive: true });
  writeFileSync(join(dir, traceRef), traceBytes);
  const traceDigest = `sha256:${createHash('sha256').update(traceBytes).digest('hex')}`;
  writeProductionPolicyArtifact(dir, productionCtaDataContract);
  const common = (checkId, observedResult, acceptance) => productionPolicyEvidenceSection({
    contract: productionCtaDataContract,
    endpoint: productionCtaDataContract.destination,
    targetRole: productionCtaDataContract.mode,
    task,
    traceRef,
    traceDigest,
    checkId,
    observedResult,
    acceptance,
    reviewer: policyReviewer,
  });
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-cta-data-policy.md', title: 'Production CTA data policy evidence', kind: policyKind, heading: 'CTA data policy',
    section: common('cta-data-policy', 'The exact data purpose, bounded retention, deletion path, accountable owner, and effective policy contract were confirmed for this CTA.', 'accepted the exact policy contract for the declared CTA task'),
  });
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-cta-deletion-capability.md', title: 'Production CTA deletion capability evidence', kind: deletionKind, heading: 'CTA deletion capability',
    section: common('cta-deletion-capability', deletionObservedResult, deletionCapabilityAcceptance),
  });
}

function writeProductionFallbackDataEvidence(dir, endpoint = productionValidateFallbackUrl) {
  const task = `fallback collection for ${productionCtaDataContract.trigger}`;
  const traceRef = 'traces/cta-data-fallback-policy-acceptance.txt';
  const traceBytes = 'Bounded production fallback CTA data-policy and deletion-capability acceptance trace captured on 2026-08-02.\n';
  mkdirSync(join(dir, 'traces'), { recursive: true });
  writeFileSync(join(dir, traceRef), traceBytes);
  const traceDigest = `sha256:${createHash('sha256').update(traceBytes).digest('hex')}`;
  writeProductionPolicyArtifact(dir, productionFallbackCtaDataContract);
  const common = (checkId, observedResult, acceptance) => productionPolicyEvidenceSection({
    contract: productionFallbackCtaDataContract,
    endpoint,
    targetRole: 'fallback-route',
    task,
    traceRef,
    traceDigest,
    checkId,
    observedResult,
    acceptance,
    reviewer: 'Taylor Morgan, Independent Fallback Data Reviewer',
  });
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-fallback-data-policy.md', title: 'Production fallback data policy evidence', kind: 'cta-data-policy', heading: 'Fallback data policy',
    section: common('cta-data-policy', 'confirmed the exact fallback endpoint policy contract and retention owner', 'accepted the fallback collection policy for the bounded task'),
  });
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-fallback-deletion-capability.md', title: 'Production fallback deletion capability evidence', kind: 'cta-deletion-capability', heading: 'Fallback deletion capability',
    section: common('cta-deletion-capability', 'confirmed deletion completion and a blocked post-deletion read at the fallback endpoint so the record was no longer readable', 'accepted and verified deletion completion plus a blocked post-deletion read for the fallback endpoint'),
  });
}

function setupProductionCollectingPolicyEvidence(dir, options = {}) {
  setupCompleteProductionLearnEvidence(dir);
  writeProductionCtaDataEvidence(dir, options);
  const task = `${productionCtaDataContract.trigger} ${productionCtaDataContract.output}`;
  for (const axis of ['reference', 'reachability', 'capability']) {
    writeCompleteProductionEvidenceRecord(dir, {
      file: `production-cta-${axis}-evidence.md`,
      title: `Production CTA ${axis} evidence`,
      kind: `cta-${axis}`,
      heading: `CTA ${axis}`,
      section: `check_id: cta_${axis}\ntarget_url: ${productionCtaDataContract.destination}\ntarget_role: ${productionCtaDataContract.mode}\ntarget_task: ${task}\naccountable_owner: ${productionCtaDataContract.owner}\nobserved_at: 2026-08-02T00:00:00Z\nmethod: independent endpoint-specific ${axis} verification bound to the exact public CTA route\nobserved_result: confirmed the exact production CTA endpoint ${axis} for the declared bounded engineering review task${axis === 'capability' ? '\ncapability_acceptance: accepted the bounded engineering-readiness review task at this exact endpoint without commercial commitment' : ''}\nproducer: Production CTA Route Evidence Producer\nproducer_id: wco-production-cta-route-producer-001\nindependent_reviewer: Taylor Morgan, Independent CTA Route Reviewer\nindependent_reviewer_id: wco-production-cta-route-reviewer-001`,
    });
  }
}


function setupCompleteProductionValidateEvidence(dir) {
  writeProductionIdentityProvenance(dir, 'PROD-CARGO-MOTOR-VALIDATE-001');
  writeProductionCustomerLanguageAndPainEvidence(dir, productionValidateOwnerPage);
  const targetTask = (kind) => `${productionValidateQueries[0]} | United States | ${kind}`;
  const structured = ({ checkId, role, task, extra = '' }) => completeProductionStructuredSection({
    checkId, role, task, targetUrl: productionValidateOwnerPage, extra,
  });
  const searchDemandSnapshotDigest = writeProductionSnapshotArtifact(dir, {
    file: 'gsc-export-2026-07-31.json', kind: 'search-demand',
    payload: { query_set: productionValidateQueries, metric_type: 'search impressions', observation_window: '2026-06-01 to 2026-07-31' },
  });
  const serpFormatSnapshotDigest = writeProductionSnapshotArtifact(dir, {
    file: 'serp-format-corpus-2026-08-02.json', kind: 'serp-format',
    payload: { query_set: productionValidateQueries, market: 'United States', language: 'en', device: 'desktop', result_types: ['checklist', 'checklist', 'checklist', 'guide', 'guide'] },
  });
  const marketComparisonPayload = productionMarketComparisonPayload(productionValidateQueries, { prefix: 'validate-corpus', acceptedInformationGain: 'One copyable readiness packet separates incomplete evidence, the bounded first-round result, and the exact next validation handoff.' });
  const marketComparisonSnapshotDigest = writeProductionSnapshotArtifact(dir, {
    file: 'independent-serp-corpus-2026-08-02.json', kind: 'market-comparison', payload: marketComparisonPayload,
  });
  const contentInventorySnapshotDigest = writeProductionSnapshotArtifact(dir, {
    file: 'production-content-inventory-2026-08-02.json', kind: 'content-inventory',
    payload: { query: productionValidateQueries[0], candidate_count: 0, retrieval_dimensions: ['url', 'slug', 'title', 'query', 'buyer-task', 'stage', 'taxonomy'] },
  });
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-icp-evidence.md', title: 'Production ICP evidence', kind: 'icp-evidence', heading: 'ICP evidence',
    section: structured({
      checkId: 'icp-evidence',
      role: 'icp-evidence',
      task: 'confirm mid-market cargo e-bike OEM or fleet-integrator fit and exclude consumer replacement, final-certified procurement, price-only sourcing, and incomplete-input projects',
      extra: 'icp_fit: mid-market cargo e-bike OEM and fleet-integrator engineering teams preparing a bounded 48 V repeated-grade cargo hub-motor readiness review\nicp_exclusion: consumer replacement buyers, price-only sourcing, final-certified procurement, and teams unable to provide the five readiness inputs are excluded',
    }),
  });
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-buyer-task-evidence.md', title: 'Production buyer task evidence', kind: 'buyer-task', heading: 'Buyer task',
    section: structured({ checkId: 'buyer-task', role: 'buyer-task', task: targetTask('buyer-task'), extra: 'buyer_task: prepare the minimum engineering input packet required for a bounded cargo hub-motor candidate-readiness review\nbuyer_role: Engineer' }),
  });
  const queryRows = productionValidateQueries.map((query) => `${query}|assemble|cargo e-bike hub-motor engineering-readiness packet|packet completeness, missing-evidence list, and next review step|validate|none|United States|en|desktop|2026-08-02|production-query-evidence.md#query-evidence`).join('\n');
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-query-evidence.md', title: 'Production query evidence', kind: 'query-evidence', heading: 'Query evidence',
    section: `${structured({ checkId: 'query-evidence', role: 'query-evidence', task: `validate the ${productionValidateQueries[0]} query for United States query evidence` })}\nquery|action|object|observable-output|stage|commercial-commitment|market|language|device|checked_at|evidence_ref\n${queryRows}`,
  });
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-search-demand-evidence.md', title: 'Production search demand evidence', kind: 'search-demand', heading: 'Search demand',
    section: `${structured({ checkId: 'search-demand', role: 'search-demand', task: targetTask('search-demand') })}\nexact_query_set: ${productionValidateQueries.join('; ')}\nsource_or_platform: Google Search Console immutable export\nmarket: United States\nlanguage: en\ndevice: desktop\nobservation_window: 2026-06-01 to 2026-07-31\nmetric_type: search impressions\nbrand_non_brand_boundary: branded queries excluded and non-brand queries measured\nzero_or_low_demand_decision: keep the bounded target because non-zero demand was observed\nseasonality_or_trend_note: seasonality reviewed and trend remained stable\nanalyst_conclusion: observed search impressions support this bounded Validate-stage query set\nsnapshot_ref: gsc-export-2026-07-31.json\nsnapshot_digest: ${searchDemandSnapshotDigest}
${snapshotBindingText('search-demand', productionValidateQueries[0])}\nobserved_value_per_query:\n${productionValidateQueries.map((query, index) => `  - ${query}|${120 - index * 20}|impressions`).join('\n')}`,
  });
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-serp-format-evidence.md', title: 'Production SERP format evidence', kind: 'serp-format', heading: 'SERP format',
    section: `${structured({ checkId: 'serp-format', role: 'serp-format', task: targetTask('serp-format') })}\nquery_set: ${JSON.stringify(productionValidateQueries)}\nmarket: United States\nlanguage: en\ndevice: desktop\nchecked_at: 2026-08-02\nresult_types: ${JSON.stringify(['checklist', 'checklist', 'checklist', 'guide', 'guide'])}\nprimary_query: ${productionValidateQueries[0]}\nprimary_query_sample_size: 5\nprimary_query_result_type_counts: ${JSON.stringify(['checklist|3', 'guide|2'])}\nprimary_query_dominant_result_type: checklist\nprimary_query_dominant_result_count: 3\nprimary_query_dominance_threshold: 0.60\nprimary_query_dominance_verdict: pass\nsupporting_query_result_type_rows: ${JSON.stringify(productionSupportingSerpRows(productionValidateQueries))}\nsnapshot_ref: serp-format-corpus-2026-08-02.json\nsnapshot_digest: ${serpFormatSnapshotDigest}
${snapshotBindingText('serp-format', productionValidateQueries[0])}\n\n${productionSupportingSerpFragments(productionValidateQueries)}`,
  });
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-serp-gap-evidence.md', title: 'Production SERP gap evidence', kind: 'serp-gap', heading: 'SERP gap',
    section: structured({ checkId: 'serp-gap', role: 'serp-gap', task: targetTask('serp-gap'), extra: 'gap_finding: sampled results discuss wattage or generic selection but do not close the five-input evidence gap, candidate-or-stop rule, and exact next-validation handoff\naccepted_information_gain: one copyable readiness packet with explicit stop conditions, progressive profiling, technical qualification, and non-commercial boundaries' }),
  });
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-information-gain-artifact.md', title: 'Production decision artifact evidence', kind: 'information-gain-artifact', heading: 'Decision artifact',
    section: 'The article contains a copyable five-input readiness packet that changes the next action by separating incomplete evidence, an evidenced stop, a bounded candidate direction, and the exact second-round validation request.',
  });
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-information-gain-market.md', title: 'Production market information gain evidence', kind: 'market-information-gain', heading: 'Market information gain',
    section: `observed_at: 2026-08-02T00:00:00Z
${productionMarketComparisonEvidence(marketComparisonPayload)}
snapshot_ref: independent-serp-corpus-2026-08-02.json
snapshot_digest: ${marketComparisonSnapshotDigest}
${snapshotBindingText('market-comparison', productionValidateQueries[0])}
reviewer: Taylor Morgan, Independent Buyer Review Lead
An independent market review confirmed buyer-usable information within the declared boundary.`,
  });
  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-inventory-evidence.md', title: 'Production inventory zero result evidence', kind: 'inventory-zero-result', heading: 'Inventory zero result',
    section: `${structured({ checkId: 'inventory-zero-result', role: 'owner-page', task: `${productionValidateQueries[0]} inventory zero-result check` })}\nscope: United States English production article inventory\nchecked_at: 2026-08-02T00:00:00Z\nretrieval_dimensions: ["url","slug","title","query","buyer-task","stage","taxonomy"]\nsnapshot_ref: production-content-inventory-2026-08-02.json\nsnapshot_digest: ${contentInventorySnapshotDigest}
${snapshotBindingText('content-inventory', productionValidateQueries[0])}\nquery: ${productionValidateQueries[0]}\nmarket: United States\nlanguage: en\nstage: validate\ncandidate_count: 0\nconflict_candidates: []\nThe independent inventory review found no matching competing owner page for this exact Validate-stage intent.`,
  });

  const internalTargets = [
    { slug: 'solution-target', heading: 'Solution target', url: productionValidateSolutionUrl, role: 'solution', task: 'review the solution family boundary and unresolved inputs', owner: 'Morgan Lee, Product Content Lead' },
    { slug: 'technical-review-target', heading: 'Technical review target', url: productionValidateTechnicalUrl, role: 'technical-review', task: 'prepare the next bench and vehicle validation task', owner: 'Jordan Rivera, Quality Validation Lead' },
  ];
  const writeInternalRecord = ({ file, title, kind, checkId, observedResult }) => {
    mkdirSync(join(dir, 'artifacts'), { recursive: true });
    const sections = internalTargets.map((target) => {
      const artifactRef = `artifacts/${kind}-${target.slug}.txt`;
      const artifactBytes = `Independent ${kind} evidence for ${target.slug}, ${target.url}, and the declared buyer task captured at 2026-08-02T00:00:00Z.\n`;
      writeFileSync(join(dir, artifactRef), artifactBytes);
      const artifactDigest = `sha256:${createHash('sha256').update(artifactBytes).digest('hex')}`;
      return `## ${target.heading}\n\ncheck_id: ${checkId}\ntarget_url: ${target.url}\ntarget_role: ${target.role}\ntarget_task: ${target.task}\naccountable_owner: ${target.owner}\nobserved_at: 2026-08-02T00:00:00Z\nmethod: independent endpoint-specific ${kind} inspection against the declared buyer task\nobserved_result: ${observedResult}\nartifact_ref: ${artifactRef}\nartifact_digest: ${artifactDigest}\nproducer: Production Internal Link Evidence Producer\nproducer_id: wco-production-internal-link-producer-001\nindependent_reviewer: Morgan Lee, Independent Internal Link Reviewer\nindependent_reviewer_id: wco-production-internal-link-reviewer-001\n`;
    });
    const body = `# ${title}\n\n${sections.join('\n')}`;
    const digest = createHash('sha256').update(body).digest('hex');
    writeFileSync(join(dir, file), `---\ntitle: ${title}\nrecord_type: evidence-record\nevidence_scope: production\nsource: independent endpoint-specific internal-link verification\nobserved_at: 2026-08-02T00:00:00Z\ndigest: sha256:${digest}\nevidence_kind: ${kind}\n---\n${body}`);
  };
  writeInternalRecord({ file: 'production-internal-link-acceptance-evidence.md', title: 'Production internal-link acceptance evidence', kind: 'internal-link-acceptance', checkId: 'internal-link-acceptance', observedResult: 'confirmed the destination accepts and advances the declared internal-link buyer task' });
  for (const axis of ['reference', 'reachability', 'capability']) writeInternalRecord({ file: `production-internal-link-${axis}-evidence.md`, title: `Production internal-link ${axis} evidence`, kind: `internal-link-${axis}`, checkId: `internal-link-${axis}`, observedResult: `confirmed the exact target identity and ${axis} behavior for the declared internal-link buyer task` });

  mkdirSync(join(dir, 'artifacts'), { recursive: true });
  const handoffSections = [
    ['engineering-review-handoff', 'Engineering review handoff', productionCtaDataContract.destination, 'Applications Engineering', 'return packet completeness a missing-evidence list and the next review step; only after the complete second-round package and named technical-owner review return candidate-or-stop', productionCtaDataContract.owner],
    ['quality-validation-handoff', 'Quality validation handoff', productionValidateTechnicalUrl, 'Quality', 'define project-specific bench and vehicle acceptance evidence after technical qualification', 'Jordan Rivera, Quality Validation Lead'],
  ].map(([slug, heading, url, role, task, owner]) => {
    const artifactRef = `artifacts/target-acceptance-${slug}.txt`;
    const artifactBytes = `Independent target-acceptance evidence for ${url}, ${role}, and ${task} captured at 2026-08-02T00:00:00Z.\n`;
    writeFileSync(join(dir, artifactRef), artifactBytes);
    const artifactDigest = `sha256:${createHash('sha256').update(artifactBytes).digest('hex')}`;
    return `## ${heading}\n\ncheck_id: target-acceptance\ntarget_url: ${url}\ntarget_role: ${role}\ntarget_task: ${task}\naccountable_owner: ${owner}\nobserved_at: 2026-08-02T00:00:00Z\nmethod: independent target-acceptance review bound to the exact receiving task and owner\nobserved_result: confirmed the target accepts the declared cross-role handoff without creating commercial commitment\ncapability_acceptance: accepted the exact receiving task under the named owner and stated technical boundary\nartifact_ref: ${artifactRef}\nartifact_digest: ${artifactDigest}\nproducer: Production Handoff Evidence Producer\nproducer_id: wco-production-handoff-producer-001\nindependent_reviewer: Taylor Morgan, Independent Handoff Reviewer\nindependent_reviewer_id: wco-production-handoff-reviewer-001`;
  }).join('\n\n');
  const handoffBody = `# Production role-handoff acceptance evidence\n\n${handoffSections}\n`;
  writeFileSync(join(dir, 'production-role-handoff-acceptance-evidence.md'), `---\ntitle: Production role-handoff acceptance evidence\nrecord_type: evidence-record\nevidence_scope: production\nsource: independent target acceptance review\nobserved_at: 2026-08-02T00:00:00Z\ndigest: sha256:${createHash('sha256').update(handoffBody).digest('hex')}\nevidence_kind: target-acceptance\n---\n${handoffBody}`);

  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-secondary-buyer-role-evidence.md', title: 'Production secondary buyer role evidence', kind: 'secondary-buyer-role', heading: 'Quality role',
    section: 'reviewed_at: 2026-08-02T00:00:00Z\nbuyer_role: Quality\nconcrete_objection: Quality requires project-specific bench and vehicle acceptance evidence before a technically qualified candidate can advance to sample validation.\narticle_owned_answer: The article preserves duty assumptions, interface boundaries, unresolved risks, and the next validation-evidence task for Quality.',
  });

  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-product-decision-evidence.md', title: 'Production product decision evidence', kind: 'product-decision', heading: 'Cargo hub-motor candidate decision',
    section: completeProductionStructuredSection({
      checkId: 'product-decision',
      role: 'solution',
      task: `${productionValidateBuyerCondition} ${productionValidateDecisionVariable} candidate`,
      targetUrl: productionValidateSolutionUrl,
      extra: `buyer_condition: ${productionValidateBuyerCondition}\ndecision_variable: ${productionValidateDecisionVariable}\nno_fit_condition: ${productionValidateNoFit}\nremaining_inputs: ${productionValidateRemainingInputs}\ncandidate_direction: candidate`,
    }),
  });

  writeCompleteProductionEvidenceRecord(dir, {
    file: 'production-capability-proof-evidence.md', title: 'Production bounded engineering review capability evidence', kind: 'capability-proof', heading: 'Bounded engineering review capability',
    section: `buyer_task: prepare a bounded cargo hub-motor candidate-readiness review\nreview_method: compare every candidate against the same five-input basis\nobservable_output: packet completeness, a missing-evidence list, and the next review step; only after the complete second-round package and named technical-owner review may the technical owner return candidate-or-stop\nboundary: no product fit, commercial acceptance, or response-timing claim\n${productionValidateCapabilityProofCopy}`,
  });

  writeProductionCtaDataEvidence(dir);
  writeProductionFallbackDataEvidence(dir);
  const ctaTask = `${productionCtaDataContract.trigger} ${productionCtaDataContract.output}`;
  for (const axis of ['reference', 'reachability', 'capability']) writeCompleteProductionEvidenceRecord(dir, {
    file: `production-cta-${axis}-evidence.md`, title: `Production CTA ${axis} evidence`, kind: `cta-${axis}`, heading: `CTA ${axis}`,
    section: `check_id: cta_${axis}\ntarget_url: ${productionCtaDataContract.destination}\ntarget_role: ${productionCtaDataContract.mode}\ntarget_task: ${ctaTask}\naccountable_owner: ${productionCtaDataContract.owner}\nobserved_at: 2026-08-02T00:00:00Z\nmethod: independent endpoint-specific ${axis} verification bound to the exact public CTA route\nobserved_result: confirmed the exact production CTA endpoint ${axis} for the declared bounded engineering review task${axis === 'capability' ? '\ncapability_acceptance: accepted the bounded engineering-readiness review task at this exact endpoint without commercial commitment' : ''}\nproducer: Production CTA Route Evidence Producer\nproducer_id: wco-production-cta-route-producer-001\nindependent_reviewer: Taylor Morgan, Independent CTA Route Reviewer\nindependent_reviewer_id: wco-production-cta-route-reviewer-001`,
  });
  setupVerifiedFallbackEvidence(dir, { endpoint: productionValidateFallbackUrl });
  setupMobileReadabilityEvidence(dir, { targetUrl: productionValidateOwnerPage, renderTarget: productionValidateOwnerPage, targetTask: '320px mobile readability review for Cargo Hub Motor Engineering Readiness Checklist: 5 Inputs Before Review' });
}

test('P1 live-production-shaped Validate baseline passes structural validator-branch checks only and does not prove real production', (t) => {
  expectPass(makeFixture(t, completeProductionValidateMutations(), setupCompleteProductionValidateEvidence));
});

function mutateCompleteProductionValidateInventory(surfaceId, mutateParts) {
  const base = completeProductionValidateMutations();
  return Object.fromEntries(Object.keys(base).map((key) => [key, (content) => mutateJsonArrayField(base[key](content), 'buyer_visible_cta_inventory', (rows) => rows.map((row) => {
    const parts = row.split('|');
    if (parts[0] !== surfaceId) return row;
    const next = [...parts];
    mutateParts(next);
    assert.notDeepEqual(next, parts, `inventory mutation for ${surfaceId} must not be a no-op`);
    return next.join('|');
  }))]));
}

test('P1 production Validate inventory blocks verified fallback destination drift', (t) => {
  expectBlockMatching(t, mutateCompleteProductionValidateInventory('fallback-route-request-01', (parts) => {
    parts[4] = 'https://www.fluxpedal-motors.com/contact/drifted-fallback';
  }), /fallback-route-request-01 verified destination must exactly match cta_fallback_route_contract endpoint/, setupCompleteProductionValidateEvidence);
});

test('P1 production Validate inventory blocks verified fallback owner drift', (t) => {
  expectBlockMatching(t, mutateCompleteProductionValidateInventory('fallback-copyable-message-01', (parts) => {
    parts[5] = 'Morgan Lee, Different Fallback Owner';
  }), /fallback-copyable-message-01 verified owner must exactly match cta_fallback_route_contract owner/, setupCompleteProductionValidateEvidence);
});

test('P1 production Validate inventory blocks fallback route-status drift from the verified contract', (t) => {
  expectBlockMatching(t, mutateCompleteProductionValidateInventory('fallback-bounded-review-01', (parts) => {
    parts[4] = 'not-applicable';
    parts[7] = 'unverified-unavailable';
    parts[8] = 'not-applicable';
  }), /fallback-bounded-review-01 route-status must exactly match cta_fallback_route_contract/, setupCompleteProductionValidateEvidence);
});

test('P1 production Validate inventory blocks a missing verified fallback evidence ref', (t) => {
  expectBlockMatching(t, mutateCompleteProductionValidateInventory('fallback-do-not-send-01', (parts) => {
    parts[8] = 'not-applicable';
  }), /fallback-do-not-send-01 verified route requires endpoint-specific evidence-bundle-ref/, setupCompleteProductionValidateEvidence);
});

test('P1 production Validate inventory blocks a wrong verified fallback evidence fragment', (t) => {
  expectBlockMatching(t, mutateCompleteProductionValidateInventory('fallback-route-request-01', (parts) => {
    parts[8] = 'fallback-route-evidence.md#missing-fallback-capability';
  }), /fragment #missing-fallback-capability (?:does not match|does not exist)|missing fragment #missing-fallback-capability/, setupCompleteProductionValidateEvidence);
});

test('P1 production Validate primary inventory cannot reuse the verified fallback endpoint', (t) => {
  expectBlockMatching(t, mutateCompleteProductionValidateInventory('primary-engineering-review-01', (parts) => {
    parts[4] = productionValidateFallbackUrl;
  }), /primary-engineering-review-01 verified destination must exactly match canonical cta_destination/, setupCompleteProductionValidateEvidence);
});

const ctaPolicyFocusedPattern = /cta_data_|data-policy|deletion-capability|public absolute HTTPS URL|production cta_(?:reference|reachability|capability)|cta_(?:reference|reachability|capability)_evidence_refs/;

test('P1 production collecting CTA data-policy contract has a complete focused positive branch', () => {
  const canonical = {
    source: 'brief',
    policyEffectiveAt: '2026-08-01T00:00:00Z',
    policyCheckedAt: '2026-08-02T00:00:00Z',
    policyObservedAt: '2026-08-02T00:00:00Z',
    policyReviewedAt: '2026-08-02T12:00:00Z',
    policyReviewCeiling: '2026-08-02T16:00:00Z',
    canonicalReviewedAt: '2026-08-03T00:00:00+08:00',
  };
  const problems = [];
  articlePackageValidatorTestHooks.validateCtaPolicyTemporalContract({ ...canonical, problems });
  const expected = {
    policy_contract_id: 'CTA-DATA-POLICY-2026-08-01',
    policy_version: '2026.08.01',
    policy_digest: `sha256:${'a'.repeat(64)}`,
  };
  articlePackageValidatorTestHooks.validateCtaPolicyEvidenceProjection(new Map(Object.entries(expected)), expected, 'brief', 'policy.md#policy', problems);
  assert.deepEqual(problems, []);
});

test('P1 non-collecting CTA requires all policy fields to remain not-applicable and empty', (t) => {
  expectPass(makeFixture(t, notApplicableSyntheticMutations()));
  expectBlockMatching(t, overrideMutationFields(notApplicableSyntheticMutations(), {
    cta_data_policy_contract_id: 'CTA-DATA-FABRICATED-001',
  }), /cta_data_policy_contract_id must be not-applicable for inline-no-input or local-tool-only CTA packages/);
});

test('P1 CTA data-policy scalar drift across one canonical record is blocked', (t) => {
  expectBlockMatching(t, { publishPath: (content) => replaceField(content, 'cta_data_policy_status', '"confirmed"') }, /cta_data_policy_status must match/);
});

test('P1 CTA data-policy evidence-ref order drift is blocked', (t) => {
  const base = completeBuyCommercialMutations();
  for (const key of Object.keys(base)) {
    const prior = base[key];
    base[key] = (content) => replaceIfPresent(prior(content), 'cta_data_policy_evidence_refs', '["search-evidence.md#cta-data-policy-structure","search-evidence.md#reserved-targets-and-acceptance-contracts"]');
  }
  const prior = base.publishPath;
  base.publishPath = (content) => replaceField(prior(content), 'cta_data_policy_evidence_refs', '["search-evidence.md#reserved-targets-and-acceptance-contracts","search-evidence.md#cta-data-policy-structure"]');
  expectBlockMatching(t, base, /cta_data_policy_evidence_refs must match/);
});

for (const [label, field, value, pattern] of [
  ['synthetic policy status', 'cta_data_policy_status', 'synthetic-structure-only', /production collecting CTA requires cta_data_policy_status=confirmed/],
  ['pending owner acceptance', 'cta_data_policy_owner_acceptance', 'pending', /production collecting CTA requires cta_data_policy_owner_acceptance=accepted/],
  ['future effective date', 'cta_data_policy_effective_at', '2026-08-03', /must not be in the future|must not be after|must not be later than/],
  ['999-year retention', 'cta_data_retention_period', 'Retain the packet for 999 years after the review closes.', /must be bounded and cannot use/],
  ['placeholder contract id', 'cta_data_policy_contract_id', 'example-policy-id', /stable non-placeholder identifier/],
]) {
  test(`P1 production collecting CTA blocks ${label}`, (t) => {
    expectBlockMatching(t, overrideMutationFields(productionCollectingPolicyMutations(), { [field]: value }), pattern, setupProductionCollectingPolicyEvidence);
  });
}

for (const [label, destination] of [
  ['reserved example host', 'https://example.com/contact'],
  ['credential-bearing URL', 'https://user:pass' + '@www.fluxpedal-motors.com/contact'],
  ['IP literal', 'https://127.0.0.1/contact'],
  ['non-default port', 'https://www.fluxpedal-motors.com:8443/contact'],
  ['localhost', 'https://localhost/contact'],
]) {
  test(`P1 production collecting CTA rejects ${label}`, (t) => {
    expectBlockMatching(t, overrideMutationFields(productionCollectingPolicyMutations(), { cta_destination: destination }), /public absolute HTTPS URL/, setupProductionCollectingPolicyEvidence);
  });
}

test('P1 production collecting CTA rejects wrong policy evidence kind', (t) => {
  expectBlockMatching(t, productionCollectingPolicyMutations(), /evidence_kind=.*does not match|required kind cta-data-policy/, (dir) => setupProductionCollectingPolicyEvidence(dir, { policyKind: 'cta-reference' }));
});

test('P1 production collecting CTA rejects AI self-review in policy evidence', (t) => {
  expectBlockMatching(t, productionCollectingPolicyMutations(), /independent reviewer.*AI|must be independent|self-review/i, (dir) => setupProductionCollectingPolicyEvidence(dir, { policyReviewer: 'AI Reviewer' }));
});

test('P1 production collecting CTA rejects HTTP 200 without a post-deletion unreadable result', (t) => {
  expectBlockMatching(t, productionCollectingPolicyMutations(), /HTTP 200 alone|must prove deletion completed/, (dir) => setupProductionCollectingPolicyEvidence(dir, {
    deletionObservedResult: 'The deletion endpoint returned HTTP 200.',
    deletionCapabilityAcceptance: 'accepted HTTP 200 response',
  }));
});

test('P1 production collecting CTA rejects delete-then-still-readable evidence', (t) => {
  expectBlockMatching(t, productionCollectingPolicyMutations(), /must prove deletion completed and the deleted test record was no longer readable/, (dir) => setupProductionCollectingPolicyEvidence(dir, {
    deletionObservedResult: 'The test record was deleted, but the post-deletion read still returned the full record.',
    deletionCapabilityAcceptance: 'accepted deletion request only',
  }));
});

function replaceEvidenceSnapshotField(dir, file, field, value) {
  const target = join(dir, file);
  const content = readFileSync(target, 'utf8');
  const pattern = new RegExp(`^${field}:.*$`, 'm');
  assert.match(content, pattern, `${file} must contain ${field}`);
  writeFileSync(target, content.replace(pattern, `${field}: ${value}`));
}

function mutateSnapshotJson(dir, file, mutate) {
  const target = join(dir, file);
  const current = JSON.parse(readFileSync(target, 'utf8'));
  const next = mutate(current) || current;
  const content = `${JSON.stringify(next, null, 2)}\n`;
  writeFileSync(target, content);
  return `sha256:${createHash('sha256').update(content).digest('hex')}`;
}

for (const [label, value] of [
  ['URL', 'https://www.fluxpedal-motors.com/evidence/gsc.json'],
  ['absolute path', '/' + ['tmp', 'gsc.json'].join('/')],
  ['backslash', 'evidence\\gsc.json'],
  ['fragment', 'gsc-export-2026-07-31.json#rows'],
  ['query string', 'gsc-export-2026-07-31.json?download=1'],
  ['parent traversal', '../gsc-export-2026-07-31.json'],
  ['missing file', 'missing-gsc-export.json'],
]) {
  test(`P1 production snapshot binding rejects ${label} snapshot_ref`, (t) => {
    expectBlockMatching(t, completeProductionLearnMutations(), /production search-demand snapshot_ref/, (dir) => {
      setupCompleteProductionLearnEvidence(dir);
      replaceEvidenceSnapshotField(dir, 'production-search-demand-evidence.md', 'snapshot_ref', value);
    });
  });
}

test('P1 production snapshot binding rejects a direct symlink', (t) => {
  expectBlockMatching(t, completeProductionLearnMutations(), /must not traverse a symlink|regular non-symlink file/, (dir) => {
    setupCompleteProductionLearnEvidence(dir);
    symlinkSync(join(dir, 'gsc-export-2026-07-31.json'), join(dir, 'gsc-link.json'));
    replaceEvidenceSnapshotField(dir, 'production-search-demand-evidence.md', 'snapshot_ref', 'gsc-link.json');
  });
});

test('P1 production snapshot binding rejects digest drift', (t) => {
  expectBlockMatching(t, completeProductionLearnMutations(), /snapshot_digest does not match raw artifact bytes/, (dir) => {
    setupCompleteProductionLearnEvidence(dir);
    replaceEvidenceSnapshotField(dir, 'production-search-demand-evidence.md', 'snapshot_digest', `sha256:${'0'.repeat(64)}`);
  });
});

test('P1 production snapshot binding rejects invalid JSON bytes', (t) => {
  expectBlockMatching(t, completeProductionLearnMutations(), /snapshot artifact must be valid JSON/, (dir) => {
    setupCompleteProductionLearnEvidence(dir);
    const target = join(dir, 'gsc-export-2026-07-31.json');
    const content = '{not-json}\n';
    writeFileSync(target, content);
    replaceEvidenceSnapshotField(dir, 'production-search-demand-evidence.md', 'snapshot_digest', `sha256:${createHash('sha256').update(content).digest('hex')}`);
  });
});

for (const [label, mutate, pattern] of [
  ['JSON array', () => [], /snapshot artifact must be a JSON object/],
  ['wrong schema', (value) => ({ ...value, schema_version: 'website-content-ops.snapshot.v0' }), /schema_version must be website-content-ops.snapshot.v1/],
  ['wrong artifact kind', (value) => ({ ...value, artifact_kind: 'serp-format' }), /artifact_kind must be search-demand/],
  ['synthetic evidence scope', (value) => ({ ...value, evidence_scope: 'synthetic-fixture' }), /snapshot artifact evidence_scope must be production/],
  ['future captured_at', (value) => ({ ...value, captured_at: '2026-08-04T00:00:00Z' }), /snapshot captured_at must not be in the future|snapshot captured_at must not be later than reviewed_at/],
]) {
  test(`P1 production snapshot binding rejects ${label}`, (t) => {
    expectBlockMatching(t, completeProductionLearnMutations(), pattern, (dir) => {
      setupCompleteProductionLearnEvidence(dir);
      const digest = mutateSnapshotJson(dir, 'gsc-export-2026-07-31.json', mutate);
      replaceEvidenceSnapshotField(dir, 'production-search-demand-evidence.md', 'snapshot_digest', digest);
    });
  });
}

test('P1 production snapshot axes cannot reuse the same artifact path and digest', (t) => {
  expectBlockMatching(t, completeProductionLearnMutations(), /snapshot artifacts must be independent across axes/, (dir) => {
    setupCompleteProductionLearnEvidence(dir);
    const searchEvidence = readFileSync(join(dir, 'production-search-demand-evidence.md'), 'utf8');
    const ref = /^snapshot_ref:\s*(.+)$/m.exec(searchEvidence)?.[1];
    const digest = /^snapshot_digest:\s*(.+)$/m.exec(searchEvidence)?.[1];
    assert.ok(ref && digest);
    replaceEvidenceSnapshotField(dir, 'production-serp-format-evidence.md', 'snapshot_ref', ref);
    replaceEvidenceSnapshotField(dir, 'production-serp-format-evidence.md', 'snapshot_digest', digest);
  });
});

test('P1 production owner_page rejects reserved, credential, IP, port, and localhost URLs', (t) => {
  for (const ownerPage of [
    'https://example.test/article',
    'https://user:pass' + '@www.fluxpedal-motors.com/article',
    'https://127.0.0.1/article',
    'https://www.fluxpedal-motors.com:8443/article',
    'https://localhost/article',
  ]) {
    expectBlockMatching(t, overrideMutationFields(completeProductionLearnMutations(), { owner_page: ownerPage }), /owner_page must be a public absolute HTTPS URL/, setupCompleteProductionLearnEvidence);
  }
});

// Agent C high-risk mutation matrix: production snapshot schema, stable actor
// separation, CTA transmission discovery, body-order enforcement, and the
// ready-for-cms-draft lifecycle. Keep these tests mutation-only; validator
// implementation changes require a separate producer decision.

function refreshProductionEvidenceRecordDigest(dir, file) {
  const target = join(dir, file);
  const content = readFileSync(target, 'utf8');
  const closing = content.indexOf('\n---\n', 4);
  assert.notEqual(closing, -1, `${file} must contain a closing frontmatter delimiter`);
  const bodyStart = closing + 5;
  const body = content.slice(bodyStart);
  const digest = `sha256:${createHash('sha256').update(body).digest('hex')}`;
  assert.match(content.slice(0, closing), /^digest:.*$/m, `${file} must contain a frontmatter digest`);
  writeFileSync(target, `${content.slice(0, bodyStart).replace(/^digest:.*$/m, `digest: ${digest}`)}${body}`);
}

function mutateProductionEvidenceRecordBody(dir, file, mutate) {
  const target = join(dir, file);
  const content = readFileSync(target, 'utf8');
  const closing = content.indexOf('\n---\n', 4);
  assert.notEqual(closing, -1, `${file} must contain a closing frontmatter delimiter`);
  const bodyStart = closing + 5;
  const body = content.slice(bodyStart);
  const mutatedBody = mutate(body);
  assert.notEqual(mutatedBody, body, `${file} evidence-body mutation must change bytes`);
  writeFileSync(target, `${content.slice(0, bodyStart)}${mutatedBody}`);
  refreshProductionEvidenceRecordDigest(dir, file);
}

function mutateSearchDemandSnapshotAndRebind(dir, mutate) {
  const digest = mutateSnapshotJson(dir, 'gsc-export-2026-07-31.json', mutate);
  replaceEvidenceSnapshotField(dir, 'production-search-demand-evidence.md', 'snapshot_digest', digest);
  refreshProductionEvidenceRecordDigest(dir, 'production-search-demand-evidence.md');
}

for (const [label, mutate] of [
  ['missing common-envelope field', (artifact) => { delete artifact.capture_method; return artifact; }],
  ['extra common-envelope field', (artifact) => ({ ...artifact, undocumented_rows: 4 })],
]) {
  test(`P1 production snapshot closed common envelope rejects ${label}`, (t) => {
    expectBlockMatching(t, completeProductionLearnMutations(), /snapshot artifact must use the closed common envelope/, (dir) => {
      setupCompleteProductionLearnEvidence(dir);
      mutateSearchDemandSnapshotAndRebind(dir, mutate);
    });
  });
}

for (const [label, mutate, pattern] of [
  ['missing payload field', (artifact) => { delete artifact.payload.metric_type; return artifact; }, /snapshot payload must use the closed search-demand schema/],
  ['extra payload field', (artifact) => { artifact.payload.rows = []; return artifact; }, /snapshot payload must use the closed search-demand schema/],
  ['empty scalar payload value', (artifact) => { artifact.payload.metric_type = '   '; return artifact; }, /snapshot payload\.metric_type must be a non-empty string/],
  ['scalar payload type drift', (artifact) => { artifact.payload.metric_type = ['search impressions']; return artifact; }, /snapshot payload\.metric_type must be a non-empty string/],
  ['array payload type drift', (artifact) => { artifact.payload.query_set = productionLearnQueries.join('; '); return artifact; }, /snapshot payload\.query_set must be a non-empty string array/],
  ['integer payload type drift', (artifact) => { artifact.payload = { query: productionLearnQueries[0], candidate_count: '0', retrieval_dimensions: ['url'] }; artifact.artifact_kind = 'content-inventory'; return artifact; }, /snapshot payload\.candidate_count must be a non-negative integer/],
]) {
  test(`P1 production snapshot payload rejects ${label}`, (t) => {
    expectBlockMatching(t, completeProductionLearnMutations(), pattern, (dir) => {
      setupCompleteProductionLearnEvidence(dir);
      if (label === 'integer payload type drift') {
        const digest = mutateSnapshotJson(dir, 'production-content-inventory-2026-08-02.json', (artifact) => {
          artifact.payload.candidate_count = '0';
          return artifact;
        });
        replaceEvidenceSnapshotField(dir, 'production-inventory-evidence.md', 'snapshot_digest', digest);
        refreshProductionEvidenceRecordDigest(dir, 'production-inventory-evidence.md');
        return;
      }
      mutateSearchDemandSnapshotAndRebind(dir, mutate);
    });
  });
}

test('P1 production snapshot payload must match its evidence Markdown projection', (t) => {
  expectBlockMatching(t, completeProductionLearnMutations(), /metric_type must match snapshot payload\.metric_type/, (dir) => {
    setupCompleteProductionLearnEvidence(dir);
    mutateSearchDemandSnapshotAndRebind(dir, (artifact) => {
      artifact.payload.metric_type = 'organic clicks';
      return artifact;
    });
  });
});

test('P1 production snapshot producer and independent reviewer cannot share one stable ID', (t) => {
  expectBlockMatching(t, completeProductionLearnMutations(), /snapshot producer_id and independent_reviewer_id must be different/, (dir) => {
    setupCompleteProductionLearnEvidence(dir);
    const sharedId = 'wco-search-demand-snapshot-reviewer-001';
    mutateSearchDemandSnapshotAndRebind(dir, (artifact) => {
      artifact.producer_id = sharedId;
      return artifact;
    });
    replaceEvidenceSnapshotField(dir, 'production-search-demand-evidence.md', 'snapshot_producer_id', sharedId);
    refreshProductionEvidenceRecordDigest(dir, 'production-search-demand-evidence.md');
  });
});

test('P1 production identity provenance rejects a missing required field', (t) => {
  expectBlockMatching(t, completeProductionLearnMutations(), /identity provenance .* requires verification_method/, (dir) => {
    setupCompleteProductionLearnEvidence(dir);
    mutateProductionEvidenceRecordBody(dir, 'production-identity-provenance.md', (body) => replaceRequiredLiteral(
      body,
      'verification_method: independent identity registry and task-assignment record comparison\n',
      '',
      'identity provenance verification_method removal',
    ));
  });
});

test('P1 production identity provenance rejects stable actor ID drift', (t) => {
  expectBlockMatching(t, completeProductionLearnMutations(), /identity provenance .* producer_id must exactly match the canonical package identity/, (dir) => {
    setupCompleteProductionLearnEvidence(dir);
    mutateProductionEvidenceRecordBody(dir, 'production-identity-provenance.md', (body) => replaceRequiredLiteral(
      body,
      'producer_id: wco-evidence-producer-001',
      'producer_id: wco-evidence-producer-drift-002',
      'identity provenance producer ID drift',
    ));
  });
});

test('P1 canonical producer and independent reviewer cannot share one stable ID', (t) => {
  const sharedId = 'wco-independent-reviewer-001';
  const mutations = overrideMutationFields(completeProductionLearnMutations(), { producer_id: sharedId });
  expectBlockMatching(t, mutations, /independent_reviewer_id must differ from author_id, producer_id|stable actor IDs must be unique/, (dir) => {
    setupCompleteProductionLearnEvidence(dir);
    mutateProductionEvidenceRecordBody(dir, 'production-identity-provenance.md', (body) => replaceRequiredLiteral(
      body,
      'producer_id: wco-evidence-producer-001',
      `producer_id: ${sharedId}`,
      'canonical producer and reviewer shared stable ID',
    ));
  });
});

test('P1 remediation participant cannot reuse the independent reviewer stable ID', (t) => {
  const reviewerId = 'wco-independent-reviewer-001';
  const mutations = overrideMutationFields(completeProductionLearnMutations(), { remediation_participant_ids: [reviewerId] });
  expectBlockMatching(t, mutations, /independent_reviewer_id must differ from .*remediation_participant_id|stable actor IDs must be unique/, (dir) => {
    setupCompleteProductionLearnEvidence(dir);
    mutateProductionEvidenceRecordBody(dir, 'production-identity-provenance.md', (body) => replaceRequiredLiteral(
      body,
      'remediation_participant_ids: []',
      `remediation_participant_ids: ["${reviewerId}"]`,
      'remediation participant reviewer ID reuse',
    ));
  });
});

for (const owner of ['Marketing team', 'Product content department']) {
  test(`P1 stable owner identity rejects pure organization label ${owner}`, (t) => {
    expectBlockMatching(t, allRecords('technical_qualification_owner', JSON.stringify(owner)), /stable owner ID or person name plus role; pure role\/team\/department/);
  });
}

test('P1 production acceptance evidence rejects accountable_owner drift', (t) => {
  expectBlockMatching(t, completeProductionValidateMutations(), /accountable_owner must exactly match the declared accountable owner/, (dir) => {
    setupCompleteProductionValidateEvidence(dir);
    mutateProductionEvidenceRecordBody(dir, 'production-role-handoff-acceptance-evidence.md', (body) => replaceRequiredLiteral(
      body,
      `accountable_owner: ${productionCtaDataContract.owner}`,
      'accountable_owner: Casey Reed, Unassigned Content Observer',
      'role-handoff acceptance accountable owner drift',
    ));
  });
});

for (const [verb, instruction] of [
  ['talk with', 'Talk with Applications Engineering about this five-input readiness packet.'],
  ['reach', 'Reach Applications Engineering with this five-input readiness packet.'],
  ['arrange', 'Arrange an engineering-readiness review for this five-input packet.'],
  ['discuss', 'Discuss this five-input readiness packet with Applications Engineering.'],
]) {
  test(`P1 CTA inventory blocks an unregistered ${verb} buyer instruction`, (t) => {
    expectBlockMatching(t, {
      draftPath: (content) => transformBody(content, (body) => replaceRequiredLiteral(
        body,
        '## Why wattage-first selection may create avoidable rework',
        `${instruction}\n\n## Why wattage-first selection may create avoidable rework`,
        `unregistered ${verb} CTA insertion`,
      )),
    }, /buyer-visible CTA instruction is missing from buyer_visible_cta_inventory/);
  });
}

test('P1 cta_route_transmission_verdict=block is fatal to forged production readiness', (t) => {
  expectBlockMatching(t, {
    ...completeProductionLearnMutations(),
    reviewPath: (content) => {
      let output = completeProductionLearnMutations().reviewPath(content);
      output = replaceField(output, 'cta_route_transmission_verdict', '"block"');
      return output;
    },
  }, /fatal_gate_verdict=pass cannot coexist|production_readiness=ready cannot coexist|overall_verdict=pass cannot coexist|requires applicable fatal cta_route_transmission_verdict=pass/, setupCompleteProductionLearnEvidence);
});

test('P1 publishable body rejects Diagnose and Decide section order swap while the map stays unchanged', (t) => {
  expectBlockMatching(t, {
    draftPath: (content) => transformBody(content, (body) => {
      const diagnoseHeading = '## Why wattage-first selection may create avoidable rework';
      const decideHeading = '## Use five decision blocks before the first review';
      const deRiskHeading = '## What Applications Engineering requests in round two';
      const diagnoseStart = body.indexOf(diagnoseHeading);
      const decideStart = body.indexOf(decideHeading);
      const deRiskStart = body.indexOf(deRiskHeading);
      assert.ok(diagnoseStart >= 0 && decideStart > diagnoseStart && deRiskStart > decideStart, 'canonical body must preserve Diagnose -> Decide -> De-risk sections before mutation');
      return `${body.slice(0, diagnoseStart)}${body.slice(decideStart, deRiskStart)}${body.slice(diagnoseStart, decideStart)}${body.slice(deRiskStart)}`;
    }),
  }, /publishable body must implement Hook -> Diagnose -> Decide -> De-risk -> Act in declared order/);
});

test('P1 publishable body rejects a buyer-visible Act CTA moved before Diagnose', (t) => {
  const earlyActCta = '[Request the bounded engineering-readiness review](https://example.test/contact/engineering-readiness-review).';
  expectBlockMatching(t, {
    draftPath: (content) => transformBody(content, (body) => replaceRequiredLiteral(
      body,
      '## Why wattage-first selection may create avoidable rework',
      `${earlyActCta}\n\n## Why wattage-first selection may create avoidable rework`,
      'early Act CTA relocation',
    )),
  }, /buyer-visible human-handoff or commercial CTA appears before the declared Act location/);
});

test('P1 publishable body rejects a missing De-risk section while the decision map stays unchanged', (t) => {
  expectBlockMatching(t, {
    draftPath: (content) => transformBody(content, (body) => {
      const deRiskStart = body.indexOf('## What Applications Engineering requests in round two');
      const actStart = body.indexOf('## Request a bounded engineering-readiness review');
      assert.ok(deRiskStart >= 0 && actStart > deRiskStart, 'canonical body must contain a De-risk section before Act');
      let mutated = `${body.slice(0, deRiskStart)}${body.slice(actStart)}`;
      const finalBoundaryStart = mutated.lastIndexOf('### Validation boundary');
      if (finalBoundaryStart >= 0) mutated = mutated.slice(0, finalBoundaryStart);
      return mutated;
    }),
  }, /article_decision_sequence_map de-risk location does not resolve/);
});

for (const [field, drift, expected] of [
  ['operation_mode', 'draft', 'dry-run'],
  ['publication_status', 'published', 'not-published'],
  ['api_write_status', 'pass', 'not-run'],
  ['authorization_status', 'pass', 'not-run'],
  ['cms_action_status', 'pass', 'not-run'],
  ['cms_mutation_status', 'pass', 'not-run'],
  ['backend_readback_status', 'pass', 'not-run'],
  ['editor_reopen_status', 'pass', 'not-run'],
  ['anonymous_frontend_status', 'pass', 'not-run'],
  ['desktop_acceptance_status', 'pass', 'not-run'],
  ['mobile_acceptance_status', 'pass', 'not-run'],
  ['image_fetch_decode_status', 'pass', 'not-run'],
  ['frontend_acceptance_status', 'pass', 'not-run'],
  ['final_dom_image_alt_renderer_status', 'pass', 'block'],
  ['html_lang_status', 'pass', 'deferred-block'],
  ['canonical_status', 'pass', 'deferred-block'],
  ['article_json_ld_status', 'pass', 'deferred-block'],
]) {
  test(`P1 ready-for-cms-draft lifecycle rejects ${field} drift`, (t) => {
    const mutations = overrideMutationFields(completeProductionLearnMutations(), { [field]: drift }, ['publishPath']);
    expectBlockMatching(t, mutations, new RegExp(`ready-for-cms-draft production package requires ${field}=${expected}`), setupCompleteProductionLearnEvidence);
  });
}

test('P1 ready-for-cms-draft lifecycle rejects rollback_ready=true drift', (t) => {
  const mutations = overrideMutationFields(completeProductionLearnMutations(), { rollback_ready: true }, ['publishPath']);
  expectBlockMatching(t, mutations, /ready-for-cms-draft production package requires rollback_ready=false/, setupCompleteProductionLearnEvidence);
});

// F13 remediation: every previously reviewer-visible P1 gets a branch-specific mutation oracle.
test('F13 content_action rejects values outside the closed enum', (t) => {
  expectBlockMatching(t, {
    briefPath: (content) => replaceField(content, 'content_action', 'create-synthetic-fixture-only'),
    draftPath: (content) => replaceField(content, 'content_action', 'create-synthetic-fixture-only'),
  }, /content_action must use create\|update\|merge\|redirect\|do-not-write/);
});

test('F13 content_action cannot drift between Brief and Draft', (t) => {
  expectBlockMatching(t, { draftPath: (content) => replaceField(content, 'content_action', 'update') }, /article-draft.*content_action must (?:exactly )?match (?:the )?Brief(?: projection)?/i);
});

test('F13 content_family_matches rejects zero families', (t) => {
  expectBlockMatching(t, {
    briefPath: (content) => replaceField(content, 'content_family_matches', '[]'),
    publishPath: (content) => replaceField(content, 'content_family_matches', '[]'),
  }, /content_family_matches must contain exactly one family/);
});

test('F13 content_family_matches rejects multiple families', (t) => {
  expectBlockMatching(t, {
    briefPath: (content) => replaceField(content, 'content_family_matches', '["checklist","comparison"]'),
    publishPath: (content) => replaceField(content, 'content_family_matches', '["checklist","comparison"]'),
  }, /content_family_matches must contain exactly one family/);
});

test('F13 content_family_matches must equal expected_content_type computation', (t) => {
  expectBlockMatching(t, {
    briefPath: (content) => replaceField(content, 'content_family_matches', '["comparison"]'),
    publishPath: (content) => replaceField(content, 'content_family_matches', '["comparison"]'),
  }, /content_family_matches must equal the computed expected_content_type family/);
});

test('F13 content_family_singleton_verdict=block is consumed', (t) => {
  expectBlockMatching(t, {
    briefPath: (content) => replaceField(content, 'content_family_singleton_verdict', 'block'),
    publishPath: (content) => replaceField(content, 'content_family_singleton_verdict', 'block'),
  }, /content_family_singleton_verdict must be pass/);
});

test('F13 in-scope and out-of-scope questions cannot overlap', (t) => {
  const overlap = '["Which five engineering inputs are required before a cargo e-bike hub-motor candidate-readiness review?"]';
  expectBlockMatching(t, Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => replaceField(content, 'out_of_scope_questions', overlap)])), /in_scope_questions and out_of_scope_questions materially overlap/);
});

test('F13 intent closure fields require four-record exact projection', (t) => {
  expectBlockMatching(t, { reviewPath: (content) => mutateJsonArrayField(content, 'in_scope_questions', (rows) => [rows[0], 'Which supplier should receive an award?']) }, /in_scope_questions must match the canonical Brief projection/);
});

test('F13 non-Buy intent_completion_test cannot end in supplier award', (t) => {
  const value = 'the engineer submits an RFQ, places an order, and awards the supplier after reading the article';
  expectBlockMatching(t, Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => replaceField(content, 'intent_completion_test', JSON.stringify(value))])), /non-Buy intent_completion_test must not end in quote, RFQ, order, supplier nomination, supplier award/);
});

test('F13 secondary_intent_contracts must map supporting queries one-to-one', (t) => {
  expectBlockMatching(t, Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => mutateJsonArrayField(content, 'secondary_intent_contracts', (rows) => rows.slice(1))])), /secondary_intent_contracts must map supporting_query_variants one-to-one/);
});

test('F13 FAQ not-applicable contract rejects hidden FAQ items', (t) => {
  expectBlockMatching(t, Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => replaceField(content, 'faq_items', '["Can I order now?|No; this validate-stage article does not accept an order."]')])), /not-applicable FAQ requires trigger=none and empty evidence refs\/items/);
});

test('F13 applicable FAQ requires trigger evidence and items', (t) => {
  const mutations = Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => {
    let output = replaceField(content, 'faq_applicability', 'applicable');
    output = replaceField(output, 'faq_trigger_type', 'buyer-objection');
    output = replaceField(output, 'faq_absence_reason', 'not-applicable');
    output = replaceField(output, 'faq_items', '["What if one input is missing?|Hold the candidate and request only the missing input."]');
    return output;
  }]));
  expectBlockMatching(t, mutations, /applicable FAQ requires a concrete trigger, evidence refs, and FAQ items/);
});

test('F13 synthetic package cannot self-certify SERP parity', (t) => {
  expectBlockMatching(t, {
    reviewPath: (content) => replaceField(content, 'serp_content_type_parity_verdict', 'pass'),
    publishPath: (content) => replaceField(content, 'serp_content_type_parity_verdict', 'pass'),
  }, /serp_content_type_parity_verdict must be not-applicable/);
});

test('F13 body content-family implementation verdict is independently consumed', (t) => {
  expectBlockMatching(t, {
    reviewPath: (content) => replaceField(content, 'body_content_family_implementation_verdict', 'block'),
    publishPath: (content) => replaceField(content, 'body_content_family_implementation_verdict', 'block'),
  }, /body_content_family_implementation_verdict must be pass/);
});

test('F13 non-Buy terminal_action_contract cannot drift to supplier award', (t) => {
  const value = JSON.stringify('validate|cargo e-bike hub-motor candidate readiness|supplier award and purchase order|award supplier|none');
  expectBlockMatching(t, {
    briefPath: (content) => replaceField(content, 'terminal_action_contract', value),
    publishPath: (content) => replaceField(content, 'terminal_action_contract', value),
  }, /non-Buy terminal_action_contract must not end in quote, RFQ, order, supplier nomination, or supplier award/);
});

test('F13 visible_pain_chain_sequence_verdict=block is fatal', (t) => {
  expectBlockMatching(t, {
    briefPath: (content) => replaceField(content, 'visible_pain_chain_sequence_verdict', 'block'),
    publishPath: (content) => replaceField(content, 'visible_pain_chain_sequence_verdict', 'block'),
  }, /visible_pain_chain_sequence_verdict must be pass/);
});

test('F13 visual decision asset type fails closed on decision-list', (t) => {
  const mutate = (content) => mutateJsonArrayField(content, 'visual_decision_assets', (rows) => rows.map((row) => row.replace(/^decision-table\|/, 'decision-list|')));
  expectBlockMatching(t, { briefPath: mutate, draftPath: mutate, reviewPath: mutate, publishPath: mutate }, /visual_decision_assets asset type must use the closed enum/);
});

test('F13 decision-table semantic asset rejects five empty decision blocks in its declared H2', (t) => {
  expectBlockMatching(t, {
    draftPath: (content) => transformBody(content, (body) => body.replace(/(^### (?:Establish|Define|Describe|Separate|Summarize).+$)\n[^\n]+/gm, '$1\n')),
  }, /decision-table asset requires five non-repeated decision blocks|decision block .* concrete buyer-visible decision guidance|condition or evidence gap and a next action/);
});

test('F13 review cannot claim buyer-visible links PASS while link gates block', (t) => {
  expectBlockMatching(t, {
    reviewPath: (content) => transformDocumentBody(content, (body) => `${body}\nBuyer-visible internal links are visible: PASS.\n`),
  }, /must not claim buyer-visible internal links PASS while internal-link gates are blocked/);
});

test('F13 author judgment cannot masquerade as an unattributed blockquote', (t) => {
  expectBlockMatching(t, {
    draftPath: (content) => transformBody(content, (body) => replaceRequiredLiteral(body, '**The first decision is packet completeness—not candidate selection.**', '> The first decision is packet completeness—not candidate selection.', 'author judgment')),
  }, /author judgment must not be formatted as an unattributed blockquote/);
});

test('F13 synthetic disclosure must remain inside publishable markers', (t) => {
  expectBlockMatching(t, {
    draftPath: (content) => transformBody(content, (body) => body.replace(/^Illustrative example:[^\n]*\n+/m, '')),
  }, /synthetic publishable body requires a buyer-visible fictional or demonstration disclosure/);
});

const canonicalSecondRoundRelationshipTable = `| Second-round input | How it builds on round one | Why it is needed |
|---|---|---|
| Target speed, controller speed limit, and controller strategy | New input; it does not refine a first-round field | Confirms the speed boundary and control approach required before candidate-or-stop review |
| Detailed duty-cycle, ambient, repetition, and thermal test method | Refines: route grade and repeated-duty profile | Turns the first-round route summary into a reviewable duty and thermal method |
| Exact axle and dropout drawing plus connector, sensor, cable, and controller-interface details | Refines: axle, dropout, and brake interface summary | Turns the first-round interface summary into an exact fit and integration review |
| Target market and vehicle category | New input; it does not refine a first-round field | Defines the regulatory and vehicle-context evidence still required |
| Sample timeline and acceptance criteria | New input; it does not refine a first-round field | Defines the next validation sequence and decision threshold |`;
const canonicalSecondRoundRefinesRow = '| Detailed duty-cycle, ambient, repetition, and thermal test method | Refines: route grade and repeated-duty profile | Turns the first-round route summary into a reviewable duty and thermal method |';
const canonicalSecondRoundNewRow = '| Target speed, controller speed limit, and controller strategy | New input; it does not refine a first-round field | Confirms the speed boundary and control approach required before candidate-or-stop review |';

for (const [label, mutate, pattern] of [
  ['missing entire relationship table', (body) => replaceRequiredLiteral(body, canonicalSecondRoundRelationshipTable, '', 'second-round relationship table'), /buyer-visible Relationship and First-round source must exactly project second_round_input_relationships/],
  ['missing one relationship row', (body) => replaceRequiredLiteral(body, `${canonicalSecondRoundRefinesRow}\n`, '', 'second-round relationship row'), /buyer-visible Relationship and First-round source must exactly project second_round_input_relationships/],
  ['duplicated relationship row', (body) => replaceRequiredLiteral(body, canonicalSecondRoundRefinesRow, `${canonicalSecondRoundRefinesRow}\n${canonicalSecondRoundRefinesRow}`, 'duplicated second-round relationship row'), /buyer-visible second-round item is duplicated/],
  ['illegal relationship enum', (body) => replaceRequiredLiteral(body, 'Refines: route grade and repeated-duty profile', 'Verifies: route grade and repeated-duty profile', 'second-round relationship enum'), /buyer-visible Relationship must be exact New input or Refines/],
  ['new input changed to refines', (body) => replaceRequiredLiteral(body, canonicalSecondRoundNewRow, '| Target speed, controller speed limit, and controller strategy | Refines: route grade and repeated-duty profile | Confirms the speed boundary and control approach required before candidate-or-stop review |', 'new-to-refines relationship drift'), /buyer-visible Relationship and First-round source must exactly project second_round_input_relationships/],
  ['wrong first-round source', (body) => replaceRequiredLiteral(body, 'Refines: route grade and repeated-duty profile', 'Refines: battery voltage and controller current limits', 'second-round first source'), /buyer-visible Relationship and First-round source must exactly project second_round_input_relationships/],
  ['missing buyer-facing reason', (body) => replaceRequiredLiteral(body, canonicalSecondRoundRefinesRow, '| Detailed duty-cycle, ambient, repetition, and thermal test method | Refines: route grade and repeated-duty profile | |', 'second-round missing buyer reason'), /requires a non-empty Why it is needed buyer reason/],
  ['drifted buyer-facing reason', (body) => replaceRequiredLiteral(body, 'Turns the first-round route summary into a reviewable duty and thermal method', 'Provides generic information for later use', 'second-round buyer reason drift'), /buyer-visible Relationship and First-round source must exactly project second_round_input_relationships/],
]) {
  test(`F15 buyer-visible second-round table blocks ${label}`, (t) => {
    expectBlockMatching(t, { draftPath: (content) => transformBody(content, mutate) }, pattern);
  });
}

test('F14 unverified human-handoff policy sentinel is a valid fail-closed canonical state', (t) => {
  const result = expectPass(makeFixture(t));
  assert.equal(result.evidenceScope, 'synthetic-fixture');
  assert.equal(result.releaseDecision, 'blocked');
});

test('F14 unverified human handoff blocks an invented supplier-side retention period', (t) => {
  expectBlockMatching(t, overrideMutationFields({}, {
    cta_data_retention_period: '30 days',
  }), /unverified handoff CTA requires cta_data_retention_period=not-applicable rather than an invented supplier-side policy/);
});

test('F14 unverified human handoff blocks confirmed policy status without a verified route', (t) => {
  expectBlockMatching(t, overrideMutationFields({}, {
    cta_data_policy_status: 'confirmed',
  }), /unverified handoff CTA requires cta_data_policy_status=missing/);
});

test('F14 unverified human handoff blocks policy and deletion evidence refs while route gates remain blocked', (t) => {
  expectBlockMatching(t, overrideMutationFields({}, {
    cta_data_policy_evidence_refs: ['search-evidence.md#reserved-targets-and-acceptance-contracts'],
    cta_data_deletion_capability_evidence_refs: ['search-evidence.md#reserved-targets-and-acceptance-contracts'],
  }), /cta_data_(?:policy_evidence_refs|deletion_capability_evidence_refs) must be empty while no verified collection route exists/);
});

for (const [label, values] of [
  ['concrete destination with one failed capability gate', {
    cta_destination: 'https://example.test/contact/engineering-readiness-review',
    cta_reference_gate_verdict: 'pass',
    cta_reachability_gate_verdict: 'pass',
    cta_capability_gate_verdict: 'block',
    cta_data_retention_period: '30 days',
  }],
  ['all three route gates passing without a destination', {
    cta_destination: 'not-applicable',
    cta_reference_gate_verdict: 'pass',
    cta_reachability_gate_verdict: 'pass',
    cta_capability_gate_verdict: 'pass',
    cta_data_retention_period: '30 days',
  }],
]) {
  test(`F14 incomplete verified-collection state stays fail-closed: ${label}`, (t) => {
    expectBlockMatching(t, overrideMutationFields({}, values), /unverified handoff CTA requires cta_data_retention_period=not-applicable rather than an invented supplier-side policy/);
  });
}

// F15 remediation sentinels: freeze every F14 P1 semantic bypass before the next immutable candidate.
function projectedSecondaryIntentMutation(mutate) {
  return mutateProjectedArray({}, 'secondary_intent_contracts', (rows) => rows.map((row, index) => {
    const parts = row.split('|');
    const next = mutate([...parts], index);
    return next.join('|');
  }));
}

function setupProductionEvidenceMutation(mutator) {
  return (dir, paths) => {
    setupCompleteProductionLearnEvidence(dir, paths);
    mutator(dir, paths);
  };
}

function replaceEvidenceLiteral(dir, file, search, replacement) {
  const path = join(dir, file);
  let output = replaceRequiredLiteral(readFileSync(path, 'utf8'), search, replacement, `${file} evidence mutation`);
  const closing = output.indexOf('\n---\n', 4);
  assert.notEqual(closing, -1, `${file} evidence mutation requires closing front matter`);
  const digestPattern = /^digest: sha256:[a-f0-9]{64}$/m;
  assert.match(output, digestPattern, `${file} evidence mutation requires a canonical digest field`);
  const digest = createHash('sha256').update(output.slice(closing + 5)).digest('hex');
  output = output.replace(digestPattern, `digest: sha256:${digest}`);
  writeFileSync(path, output);
}

function projectedFaq(values) {
  return setProjectedFields({}, values);
}

const applicableFaqValues = {
  faq_applicability: 'applicable',
  faq_trigger_type: 'documented-buyer-objection',
  faq_trigger_evidence_refs: ['search-evidence.md#fixture-buyer-task-evidence'],
  faq_absence_reason: 'not-applicable',
  faq_items: ['What if one first-round input is missing?|decide whether the packet is reviewable|the buyer is uncertain whether a partial packet can advance|search-evidence.md#fixture-buyer-task-evidence|hold the candidate and request only the missing input without creating a quote or order'],
  faq_decision_verdict: 'pass',
};

const fullPacketNearSynonyms = [
  'total loaded bike and cargo range',
  'installed wheel and tire size envelope',
  'repeated hill grade and duty pattern',
  'battery voltage plus controller current ceiling',
  'axle, dropout, and brake mounting summary',
];

test('F15 content_action blocks Review-only drift', (t) => {
  expectBlockMatching(t, { reviewPath: (content) => replaceField(content, 'content_action', 'update') }, /article-quality-review.*content_action.*(?:match|Brief|projection)/i);
});

test('F15 content_action blocks Publish-only drift', (t) => {
  expectBlockMatching(t, { publishPath: (content) => replaceField(content, 'content_action', 'update') }, /publish-record.*content_action.*(?:match|Brief|projection)/i);
});

test('F15 content_action blocks a synchronized illegal enum across all four records', (t) => {
  expectBlockMatching(t, setProjectedFields({}, { content_action: 'refresh-and-rank' }), /content_action must use create\|update\|merge\|redirect\|do-not-write/);
});

for (const [label, key, mutation, pattern] of [
  ['Review missing', 'reviewPath', (content) => removeField(content, 'dominant_search_intent'), /article-quality-review.*missing.*dominant_search_intent/i],
  ['Publish missing', 'publishPath', (content) => removeField(content, 'dominant_search_intent'), /publish-record.*missing.*dominant_search_intent/i],
  ['Review drift', 'reviewPath', (content) => replaceField(content, 'dominant_search_intent', 'compare unrelated decorative lighting vendors'), /article-quality-review.*dominant_search_intent.*(?:match|Brief|projection)/i],
  ['Publish drift', 'publishPath', (content) => replaceField(content, 'dominant_search_intent', 'buy an unrelated warehouse lighting contract'), /publish-record.*dominant_search_intent.*(?:match|Brief|projection)/i],
]) {
  test(`F15 dominant_search_intent blocks ${label}`, (t) => expectBlockMatching(t, { [key]: mutation }, pattern));
}

for (const [label, mutate, pattern] of [
  ['stage expansion', (parts, index) => { if (index === 0) parts[2] = 'buy'; return parts; }, /secondary_intent_contracts.*stage.*(?:canonical|article|exact|expand)/i],
  ['commitment illegal enum', (parts, index) => { if (index === 0) parts[3] = 'enterprise-contract'; return parts; }, /secondary_intent_contracts.*commercial.commitment.*(?:enum|none|commercial)/i],
  ['commitment expansion', (parts, index) => { if (index === 0) parts[3] = 'commercial'; return parts; }, /non-Buy secondary intent|commercial commitment.*expand/i],
  ['supports owner drift', (parts, index) => { if (index === 0) parts[4] = 'solution-page'; return parts; }, /supports.*owner.*this-article|this-article.*supports/i],
  ['delegated owner=this-article', (parts, index) => { if (index === 0) parts[5] = 'delegated'; return parts; }, /delegated.*owner.*(?:different|this-article)/i],
  ['unrelated supporting task', (parts, index) => { if (index === 0) parts[1] = 'choose decorative orchid wallpaper for a kitchen'; return parts; }, /secondary intent.*(?:task|query).*(?:dominant|semantic|related|overlap)/i],
  ['non-Buy terminal commercial action', (parts, index) => { if (index === 0) parts[1] = 'request a binding quotation and place the supplier order'; return parts; }, /non-Buy secondary intent must not promise a commercial terminal action/i],
]) {
  test(`F15 secondary intent blocks ${label}`, (t) => expectBlockMatching(t, projectedSecondaryIntentMutation(mutate), pattern));
}

test('F15 secondary intent blocks an unrelated synchronized supporting query', (t) => {
  const unrelated = 'best orchid wallpaper for apartment kitchens';
  let mutations = mutateProjectedArray({}, 'supporting_query_variants', (rows) => rows.map((row, index) => index === 0 ? unrelated : row));
  mutations = mutateProjectedArray(mutations, 'secondary_intent_contracts', (rows) => rows.map((row, index) => index === 0 ? `${unrelated}|choose decorative orchid wallpaper for a kitchen|validate|none|this-article|supports` : row));
  expectBlockMatching(t, mutations, /secondary intent.*(?:task|query).*(?:dominant|semantic|related|overlap)/i);
});

test('F15 applicable FAQ new enum and five-slot grammar is a clean structural positive', (t) => {
  expectPass(makeFixture(t, projectedFaq(applicableFaqValues)));
});

for (const [label, values, pattern] of [
  ['legacy trigger alias', { ...applicableFaqValues, faq_trigger_type: 'buyer-objection' }, /faq_trigger_type.*dated-serp-pattern\|documented-buyer-objection\|documented-buyer-uncertainty\|none/i],
  ['legacy two-slot row', { ...applicableFaqValues, faq_items: ['What if one input is missing?|Hold and request the missing input.'] }, /faq_items row must use question\|buyer_job\|objection_or_uncertainty\|evidence_ref_or_explicit_inferred_boundary\|article_owned_answer/i],
  ['missing evidence boundary', { ...applicableFaqValues, faq_items: ['What if one input is missing?|decide whether the packet is reviewable|uncertain whether a partial packet can advance||hold and request the missing input'] }, /faq_items.*evidence.*boundary|five non-empty/i],
  ['article-owned commercial expansion', { ...applicableFaqValues, faq_items: ['What if one input is missing?|decide whether the packet is reviewable|uncertain whether a partial packet can advance|search-evidence.md#fixture-buyer-task-evidence|request a binding quote and place the order now'] }, /FAQ.*commercial terminal action|article-owned answer.*commercial/i],
]) {
  test(`F15 FAQ blocks ${label}`, (t) => expectBlockMatching(t, projectedFaq(values), pattern));
}

test('F15 production-shaped fixture blocks inferred customer language and pain with empty refs', (t) => {
  const mutations = setProjectedFields(completeProductionLearnMutations(), {
    customer_language_status: 'inferred', customer_language_refs: [], customer_language_gate_verdict: 'block',
    pain_evidence_status: 'inferred', pain_evidence_refs: [], pain_evidence_gate_verdict: 'block',
  });
  expectBlockMatching(t, mutations, /production.*(?:customer.language|pain.evidence).*(?:confirmed|non-empty|gate.*pass)/i, setupCompleteProductionLearnEvidence);
});

for (const [label, values, pattern] of [
  ['missing customer-language refs', { customer_language_refs: [] }, /production.*customer.language.*non-empty/i],
  ['missing pain refs', { pain_evidence_refs: [] }, /production.*pain.evidence.*non-empty/i],
]) {
  test(`F15 production evidence blocks ${label}`, (t) => {
    expectBlockMatching(t, setProjectedFields(completeProductionLearnMutations(), values), pattern, setupCompleteProductionLearnEvidence);
  });
}

test('F15 customer-language gate drift in Review is blocked', (t) => {
  const base = completeProductionLearnMutations();
  const original = base.reviewPath;
  base.reviewPath = (content) => replaceField(original(content), 'customer_language_gate_verdict', 'block');
  expectBlockMatching(t, base, /article-quality-review.*customer_language_gate_verdict.*(?:match|projection)|customer_language_gate_verdict.*pass/i, setupCompleteProductionLearnEvidence);
});

test('F15 customer-language evidence wrong kind is blocked', (t) => {
  expectBlockMatching(t, completeProductionLearnMutations(), /customer.language.*evidence_kind.*customer-language/i, setupProductionEvidenceMutation((dir) => {
    replaceEvidenceLiteral(dir, 'production-customer-language-evidence.md', 'evidence_kind: customer-language', 'evidence_kind: pain-evidence');
  }));
});

test('F15 pain evidence wrong target is blocked', (t) => {
  expectBlockMatching(t, completeProductionLearnMutations(), /pain.evidence.*target_url.*(?:owner_page|exact|match)/i, setupProductionEvidenceMutation((dir) => {
    replaceEvidenceLiteral(dir, 'production-pain-evidence.md', `target_url: ${productionLearnOwnerPage}`, 'target_url: https://www.fluxpedal-motors.com/unrelated-target');
  }));
});

test('F15 customer-language evidence producer and reviewer must remain independent', (t) => {
  expectBlockMatching(t, completeProductionLearnMutations(), /customer.language.*producer_id.*independent_reviewer_id.*different|stable actor IDs must be unique/i, setupProductionEvidenceMutation((dir) => {
    replaceEvidenceLiteral(dir, 'production-customer-language-evidence.md', 'independent_reviewer_id: wco-independent-reviewer-001', 'independent_reviewer_id: wco-production-evidence-producer-001');
  }));
});

test('F15 synthetic inferred/block package remains structurally valid but cannot become production proof', (t) => {
  const result = expectPass(makeFixture(t));
  assert.equal(result.evidenceScope, 'synthetic-fixture');
  assert.equal(result.releaseDecision, 'blocked');
});

for (const [label, mutations, pattern, setup] of [
  ['missing fixture label', Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => removeField(content, 'fixture_identity')])), /missing required field fixture_identity/i, null],
  ['test fixture falsely production eligible', setProjectedFields(completeProductionLearnMutations(), { evidence_origin: 'test-fixture', fixture_identity: 'validator-branch-only', production_proof_eligible: true }), /test-fixture.*production_proof_eligible=false|production.*requires.*live-production/i, setupCompleteProductionLearnEvidence],
  ['live production carrying fixture id', setProjectedFields(completeProductionLearnMutations(), { evidence_origin: 'live-production', fixture_identity: 'validator-branch-only', production_proof_eligible: true }), /live-production.*fixture_identity=not-applicable/i, setupCompleteProductionLearnEvidence],
  ['synthetic fixture falsely production eligible', setProjectedFields({}, { production_proof_eligible: true }), /synthetic-fixture.*production_proof_eligible=false/i, null],
]) {
  test(`F15 evidence-origin boundary blocks ${label}`, (t) => expectBlockMatching(t, mutations, pattern, setup));
}

function collectionPolicyMutation(mutateRows) {
  return mutateProjectedArray(completeProductionValidateMutations(), 'cta_collection_route_policy_contracts', mutateRows);
}

test('F15 primary/fallback different endpoints block missing fallback policy evidence', (t) => {
  expectBlockMatching(t, collectionPolicyMutation((rows) => rows.map((row) => row.startsWith('fallback|') ? row.replace(productionValidateFallbackPolicyRef, 'not-applicable') : row)), /fallback.*policy.*evidence.*(?:required|missing|non-empty)/i, setupCompleteProductionValidateEvidence);
});

test('F15 fallback policy bound to primary endpoint is blocked', (t) => {
  expectBlockMatching(t, collectionPolicyMutation((rows) => rows.map((row) => row.startsWith('fallback|') ? row.replace(productionValidateFallbackUrl, productionCtaDataContract.destination) : row)), /fallback.*endpoint.*(?:exact|match|binding)/i, setupCompleteProductionValidateEvidence);
});

test('F15 fallback-only collection with complete endpoint policy is a clean positive', (t) => {
  const mutations = setProjectedFields(completeProductionValidateMutations(), {
    cta_collection_route_policy_contracts: productionCollectionPolicyRows({ primaryRequiredInputsMode: 'none' }),
  });
  expectPass(makeFixture(t, mutations, setupCompleteProductionValidateEvidence));
});

test('F15 fallback requiredInputsMode=none does not require a collection-policy row', (t) => {
  const mutations = setProjectedFields(completeProductionValidateMutations(), {
    cta_collection_route_policy_contracts: productionCollectionPolicyRows({ fallbackRequiredInputsMode: 'none' }),
    cta_fallback_route_contract: replaceRequiredLiteral(verifiedFallbackContract({ endpoint: productionValidateFallbackUrl }), '|same-as-cta-required-inputs|', '|none|', 'F15 fallback no-input route-contract mutation'),
  });
  expectPass(makeFixture(t, mutations, setupCompleteProductionValidateEvidence));
});

for (const [label, mutate, pattern] of [
  ['duplicate route row', (rows) => [...rows, rows[0]], /cta_collection_route_policy_contracts.*duplicate.*route/i],
  ['missing collecting route row', (rows) => rows.filter((row) => !row.startsWith('fallback|')), /fallback.*collection.*policy.*row.*(?:exactly one|required|missing)/i],
  ['endpoint drift', (rows) => rows.map((row) => row.startsWith('primary|') ? row.replace(productionCtaDataContract.destination, `${productionCtaDataContract.destination}-drift`) : row), /primary.*endpoint.*(?:exact|match|binding)/i],
  ['deletion ref drift', (rows) => rows.map((row) => row.startsWith('fallback|') ? row.replace(productionValidateFallbackDeletionRef, 'production-fallback-deletion-capability.md#missing') : row), /fallback.*deletion.*(?:ref|fragment).*(?:missing|match|evidence)/i],
]) {
  test(`F15 collection route policy blocks ${label}`, (t) => expectBlockMatching(t, collectionPolicyMutation(mutate), pattern, setupCompleteProductionValidateEvidence));
}

for (const [label, mutate] of [
  ['opening prose near-synonym packet', (body) => replaceRequiredLiteral(body, '## Why wattage-first selection may create avoidable rework', `Before review, collect ${fullPacketNearSynonyms.join(', ')}.\n\n## Why wattage-first selection may create avoidable rework`, 'F15 opening redundancy insertion anchor')],
  ['decision-block list packet', (body) => replaceRequiredLiteral(body, '### Define the rolling geometry', `${fullPacketNearSynonyms.map((item) => `- ${item}`).join('\n')}\n\n### Define the rolling geometry`, 'F15 decision-block redundancy insertion anchor')],
  ['final CTA table packet', (body) => replaceRequiredLiteral(body, '### Copyable route-request fallback', `| Intake field | Ready |\n|---|---|\n${fullPacketNearSynonyms.map((item) => `| ${item} | [ ] |`).join('\n')}\n\n### Copyable route-request fallback`, 'F15 final CTA redundancy insertion anchor')],
]) {
  test(`F15 normalized field-set redundancy blocks ${label}`, (t) => {
    expectBlockMatching(t, { draftPath: (content) => transformBody(content, mutate) }, /normalized.*field.set.*redundan|full.*packet.*(?:repeat|surface)/i);
  });
}

test('F15 canonical de-duplicated article remains a clean structural positive', (t) => expectPass(makeFixture(t)));

test('F15 unverified route blocks copy/send/paste full-packet instruction even after route-only verification wording', (t) => {
  expectBlockMatching(t, { draftPath: (content) => transformBody(content, (body) => replaceRequiredLiteral(
    body,
    '### Copyable route-request fallback',
    '### Copyable route-request fallback\n\nAfter a verified route is returned, paste and send the full packet through that route.',
    'F15 unverified-route transmission insertion anchor',
  )) }, /unverified.*(?:copy|send|paste).*packet|route.*policy.*before.*transmission/i);
});

test('F15 unverified route may request only verified route plus data-policy details', (t) => expectPass(makeFixture(t)));

test('F15 applicable internal-link requirement with zero visible links cannot use not-applicable verdict', (t) => {
  const mutations = setProjectedFields(completeProductionValidateMutations(), {
    buyer_visible_internal_link_count: 0,
    buyer_visible_internal_links_verdict: 'not-applicable',
  });
  expectBlockMatching(t, mutations, /applicable.*internal.link.*(?:zero|0).*not-applicable|buyer_visible_internal_links_verdict.*block/i, setupCompleteProductionValidateEvidence);
});

test('F15 verified test-fixture Markdown links with three-axis and target-acceptance gates pass without becoming production proof', (t) => {
  const result = expectPass(makeFixture(t, completeProductionValidateMutations(), setupCompleteProductionValidateEvidence));
  assert.notEqual(result.releaseDecision, 'published');
});

// F16 remediation sentinels: close the F15 action-slot drift and open-class CTA bypasses.
test('F16 CTA inventory blocks an unregistered complete-this-worksheet imperative', (t) => {
  expectBlockMatching(t, {
    draftPath: (content) => transformBody(content, (body) => replaceRequiredLiteral(
      body,
      '## Why wattage-first selection may create avoidable rework',
      'Complete this worksheet before the review.\n\n## Why wattage-first selection may create avoidable rework',
      'F16 complete worksheet CTA insertion anchor',
    )),
  }, /buyer-visible CTA instruction is missing from buyer_visible_cta_inventory/);
});

test('F16 unverified approved-portal imperative cannot bypass inventory or route safety', (t) => {
  expectBlockSatisfying(t, {
    draftPath: (content) => transformBody(content, (body) => replaceRequiredLiteral(
      body,
      '## Why wattage-first selection may create avoidable rework',
      'Proceed through the approved supplier portal to complete your handoff.\n\n## Why wattage-first selection may create avoidable rework',
      'F16 approved portal CTA insertion anchor',
    )),
  }, (problems) => {
    const joined = problems.join('\n');
    assert.match(joined, /buyer-visible CTA instruction is missing from buyer_visible_cta_inventory/);
    assert.match(joined, /unverified.*route|approved.*portal|route.*safety/i);
  });
});

test('F16 direct-answer action must match the dominant task action family', (t) => {
  expectBlockMatching(t, allRecords('direct_answer_action', '"validate"'), /direct_answer_action must match dominant_task_contract action/);
});

test('F16 dominant search intent leading action must match the dominant task action family', (t) => {
  expectBlockMatching(t, allRecords('dominant_search_intent', '"validate cargo e-bike hub-motor candidate readiness from a bounded engineering input packet"'), /dominant_search_intent leading action must match dominant_task_contract action/);
});

test('F16 terminal action must match the dominant task action family', (t) => {
  const mutations = setProjectedFields({}, {
    terminal_action_contract: 'validate|cargo e-bike hub-motor readiness packet|packet completeness, missing-evidence list, and next review step|validate|none',
  }, ['briefPath', 'publishPath']);
  expectBlockMatching(t, mutations, /terminal_action_contract action must match dominant_task_contract action/);
});


test('F16 first-round candidate gate verdict is required in all four canonical records', (t) => {
  expectBlockMatching(t, v12RemoveAllFields(['first_round_output_candidate_gate_verdict']), /field first_round_output_candidate_gate_verdict is required/);
});

test('F16 first-round candidate gate verdict cannot drift between canonical records', (t) => {
  expectBlockMatching(t, {
    reviewPath: (content) => replaceField(content, 'first_round_output_candidate_gate_verdict', 'pass'),
  }, /first_round_output_candidate_gate_verdict.*exactly match|must be block/);
});

test('F16 first-round candidate gate verdict must remain block', (t) => {
  expectBlockMatching(t, allRecords('first_round_output_candidate_gate_verdict', 'pass'), /first_round_output_candidate_gate_verdict must be block/);
});

test('F16 validate-stage candidate gates must preserve complete-package then named-owner order', (t) => {
  expectBlockMatching(t, allRecords('candidate_decision_required_gates', '["named-technical-owner-review","complete-second-round-package"]'), /candidate_decision_required_gates must be exactly complete-second-round-package then named-technical-owner-review/);
});

test('F16 first-round output cannot promise candidate-or-stop before both decision gates pass', (t) => {
  const mutations = setProjectedFields({}, {
    stage_primary_outcome: 'packet completeness, missing evidence, next review step, and candidate-or-stop direction',
  }, ['briefPath', 'draftPath']);
  expectBlockMatching(t, mutations, /first-round stage_primary_outcome must not promise candidate-or-stop before candidate_decision_required_gates pass/);
});

test('F16 route BLOCK cannot expose a send-or-submit instruction', (t) => {
  expectBlockSatisfying(t, {
    draftPath: (content) => transformBody(content, (body) => replaceRequiredLiteral(
      body,
      '## Why wattage-first selection may create avoidable rework',
      'Send or submit the complete packet now for engineering review.\n\n## Why wattage-first selection may create avoidable rework',
      'F16 route-block transmission insertion anchor',
    )),
  }, (problems) => {
    const joined = problems.join('\n');
    assert.match(joined, /buyer-visible CTA instruction is missing from buyer_visible_cta_inventory/);
    assert.match(joined, /unverified.*(?:send|submit)|route.*policy.*before.*transmission|transmission.*block/i);
  });
});

test('F16 title leading action must match the dominant task action family', (t) => {
  const mutations = {
    briefPath: (content) => replaceField(content, 'working_article_title', '"Validate a Cargo E-Bike Hub-Motor Readiness Packet"'),
    draftPath: (content) => replaceField(content, 'article_title', '"Validate a Cargo E-Bike Hub-Motor Readiness Packet"'),
  };
  expectBlockMatching(t, mutations, /article_title leading action must match dominant_task_contract action/);
});

// F17 remediation regressions for the immutable F16 finding ledger.
// These tests intentionally exercise the future fail-closed contract; each mutation
// asserts a concrete non-noop change before the validator is invoked.

const f17FirstRoundExpectedOutput = 'packet completeness, missing-evidence list, and next review step';
const f17Stale396DaysAtReviewCeiling = '2025-07-02T16:00:00Z';
const f17LaterThanReviewCeiling = '2026-08-02T16:00:01Z';

function frontMatterScalar(content, field) {
  const raw = flatFrontMatter(content).fields.get(field);
  assert.notEqual(raw, undefined, `canonical fixture must contain ${field}`);
  return decodeSequenceItem(raw.trim());
}

function mutatePublishSearchFieldTableValue(content, label, replacement) {
  const escapedLabel = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const pattern = new RegExp(`^(\\| ${escapedLabel} \\| )([^|]+?)( \\| Fixture-only \\|)$`, 'm');
  const match = pattern.exec(content);
  assert.ok(match, `Publish Record must contain exactly one ${label} search-field row`);
  assert.notEqual(match[2].trim(), replacement, `${label} table mutation must not be a no-op`);
  const output = content.replace(pattern, `$1${replacement}$3`);
  assert.notEqual(output, content, `${label} table mutation must change the Publish Record`);
  return output;
}

function mutateCtaInstructionProjection(surfaceId, replacement) {
  const current = canonicalCtaInstruction(surfaceId);
  assert.notEqual(current, replacement, `${surfaceId} instruction mutation must not be a no-op`);
  return Object.fromEntries(Object.keys(fixtureNames).map((key) => [key, (content) => {
    let output = mutateJsonArrayField(content, 'buyer_visible_cta_inventory', (rows) => rows.map((row) => {
      if (!row.startsWith(`${surfaceId}|`)) return row;
      const parts = row.split('|');
      assert.equal(parts[3], current, `${surfaceId} inventory instruction must match the canonical body surface`);
      parts[3] = replacement;
      return parts.join('|');
    }));
    if (key === 'draftPath') {
      output = transformBody(output, (body) => replaceRequiredLiteral(body, current, replacement, `${surfaceId} buyer-visible instruction`));
    }
    return output;
  }]));
}

function rewriteEvidenceRecord(dir, file, transform, { recomputeDigest = true } = {}) {
  const path = join(dir, file);
  const current = readFileSync(path, 'utf8');
  let output = transform(current);
  assert.notEqual(output, current, `${file} mutation must not be a no-op`);
  if (recomputeDigest) {
    const closing = output.indexOf('\n---\n', 4);
    assert.notEqual(closing, -1, `${file} must retain evidence-record front matter`);
    const body = output.slice(closing + 5);
    const digest = `sha256:${createHash('sha256').update(body).digest('hex')}`;
    assert.match(output, /^digest:\s*sha256:[a-f0-9]{64}$/m, `${file} must contain a canonical digest field`);
    output = output.replace(/^digest:\s*sha256:[a-f0-9]{64}$/m, `digest: ${digest}`);
  }
  writeFileSync(path, output);
}

function rewriteSnapshotAndEvidenceDigest(dir, snapshotFile, evidenceFile, mutateSnapshot) {
  const snapshotPath = join(dir, snapshotFile);
  const current = JSON.parse(readFileSync(snapshotPath, 'utf8'));
  const next = mutateSnapshot(structuredClone(current));
  assert.notDeepEqual(next, current, `${snapshotFile} mutation must not be a no-op`);
  const bytes = `${JSON.stringify(next, null, 2)}\n`;
  writeFileSync(snapshotPath, bytes);
  const digest = `sha256:${createHash('sha256').update(bytes).digest('hex')}`;
  rewriteEvidenceRecord(dir, evidenceFile, (content) => replaceRequiredLiteral(
    content,
    /^snapshot_digest:\s*sha256:[a-f0-9]{64}$/m,
    `snapshot_digest: ${digest}`,
    `${evidenceFile} snapshot digest binding`,
  ));
}

for (const key of Object.keys(fixtureNames)) {
  test(`F17 page_h1 is required in ${key}`, (t) => {
    expectBlockMatching(t, { [key]: (content) => removeField(content, 'page_h1') }, /page_h1.*required|required field page_h1/i);
  });

  test(`F17 page_h1 exact parity rejects drift in ${key}`, (t) => {
    expectBlockMatching(t, { [key]: (content) => replaceField(content, 'page_h1', '"Drifted Page Shell Heading"') }, /page_h1.*(?:exactly match|mismatch|canonical)/i);
  });
}

for (const [label, field] of [
  ['SEO title', 'published_article_title'],
  ['Meta description', 'published_meta_description'],
  ['H1', 'page_h1'],
  ['Excerpt', 'published_excerpt'],
]) {
  test(`F17 Publish search-fields table rejects ${label} drift from ${field}`, (t) => {
    expectBlockMatching(t, {
      publishPath: (content) => mutatePublishSearchFieldTableValue(content, label, `Drifted ${label} projection`),
    }, new RegExp(`(?:Publish Record|search.fields|Proposed search fields).*${field}|${label}.*(?:exactly match|drift|mismatch)`, 'i'));
  });
}

test('F17 Validate first_round_expected_output rejects a shared free-form drift across all four records', (t) => {
  expectBlockMatching(t, allRecords('first_round_expected_output', '"packet status, evidence gaps, and an engineering follow-up"'), /first_round_expected_output.*(?:exactly|fixed|must be).*packet completeness.*missing-evidence list.*next review step/i);
});

test('F17 Validate first_round_expected_output rejects a shared value missing one required component', (t) => {
  expectBlockMatching(t, allRecords('first_round_expected_output', '"packet completeness and next review step"'), /first_round_expected_output.*(?:exactly|fixed|must be).*missing-evidence list/i);
});

test('F17 Validate first_round_expected_output rejects a three-choice grammar', (t) => {
  expectBlockMatching(t, allRecords('first_round_expected_output', '"packet completeness | missing-evidence list | next review step"'), /first_round_expected_output.*(?:exactly|fixed|must be).*packet completeness.*missing-evidence list.*next review step/i);
});

test('F17 Validate first_round_expected_output rejects one-record exact-parity drift', (t) => {
  expectBlockMatching(t, { reviewPath: (content) => replaceField(content, 'first_round_expected_output', '"packet completeness, missing evidence, and next review step"') }, /first_round_expected_output.*(?:exactly match|mismatch|canonical|must be)/i);
});

for (const [label, decisionText] of [
  ['U+2011 non-breaking hyphen', 'candidate‑or‑stop'],
  ['U+2013 en dash', 'candidate–or–stop'],
  ['slash separator', 'candidate/stop'],
  ['advance-or-reject synonym', 'advance-or-reject'],
]) {
  test(`F17 first-round candidate gate blocks ${label}`, (t) => {
    const mutations = setProjectedFields({}, {
      stage_primary_outcome: `packet completeness, missing evidence, next review step, and ${decisionText} direction`,
    }, ['briefPath', 'draftPath']);
    expectBlockMatching(t, mutations, /first-round.*(?:candidate|decision|advance|reject).*before.*gate|must not promise.*(?:candidate|decision)/i);
  });
}

for (const [label, boundary] of [
  ['do-not-before-gates boundary', `the engineer can assemble the five minimum inputs, mark packet completeness, list missing evidence, and define the next review step; do not return candidate-or-stop before both declared gates pass`],
  ['remains-prohibited-pending-gates boundary', `the engineer can assemble the five minimum inputs, mark packet completeness, list missing evidence, and define the next review step; candidate-or-stop remains prohibited pending both declared gates`],
]) {
  test(`F17 explicit candidate-gate negative remains allowed: ${label}`, (t) => {
    expectPass(makeFixture(t, allRecords('intent_completion_test', JSON.stringify(boundary))));
  });
}

test('F17 mixed candidate polarity cannot hide a positive candidate promise after a denial', (t) => {
  expectBlockMatching(
    t,
    allRecords(
      'intent_completion_test',
      JSON.stringify('Candidate-or-stop remains blocked, but return a candidate now.'),
    ),
    /must not promise.*candidate|before both declared gates pass/i,
  );
});

for (const verb of ['Relay', 'Convey', 'Furnish', 'Pass the complete packet along']) {
  const sentence = verb === 'Pass the complete packet along'
    ? `${verb} now for engineering review.`
    : `${verb} the complete packet now for engineering review.`;
  test(`F17 route BLOCK rejects open-class transmission imperative: ${verb}`, (t) => {
    expectBlockSatisfying(t, {
      draftPath: (content) => transformBody(content, (body) => replaceRequiredLiteral(
        body,
        '## Why wattage-first selection may create avoidable rework',
        `${sentence}\n\n## Why wattage-first selection may create avoidable rework`,
        `${verb} route-block insertion anchor`,
      )),
    }, (problems) => {
      assert.match(problems.join('\n'), /unverified.*(?:relay|convey|furnish|pass)|route.*policy.*before.*transmission|transmission.*block/i);
    });
  });
}

test('F17 local-only packet instruction remains allowed under route BLOCK', (t) => {
  const replacement = 'Keep the complete packet local until a verified collection route and all seven endpoint gates pass.';
  expectPass(makeFixture(t, mutateCtaInstructionProjection('primary-bounded-review-01', replacement)));
});

test('F17 mixed transmission polarity cannot hide an immediate send after a denial', (t) => {
  const sentence = 'Do not send the complete packet, but send it now for engineering review.';
  expectBlockSatisfying(t, {
    draftPath: (content) => transformBody(content, (body) => replaceRequiredLiteral(
      body,
      '## Why wattage-first selection may create avoidable rework',
      `${sentence}\n\n## Why wattage-first selection may create avoidable rework`,
      'mixed transmission polarity insertion anchor',
    )),
  }, (problems) => {
    assert.match(problems.join('\n'), /unverified.*(?:send|transmission)|route.*policy.*before.*transmission|transmission.*block/i);
  });
});

test('F17 route-only conditional send remains blocked without endpoint policy gates', (t) => {
  const sentence = 'After a verified route is returned, send the complete packet through that route.';
  expectBlockSatisfying(t, {
    draftPath: (content) => transformBody(content, (body) => replaceRequiredLiteral(
      body,
      '## Why wattage-first selection may create avoidable rework',
      `${sentence}\n\n## Why wattage-first selection may create avoidable rework`,
      'route-only conditional send insertion anchor',
    )),
  }, (problems) => {
    assert.match(problems.join('\n'), /route.*policy.*before.*transmission|unverified.*(?:send|transmission)|transmission.*block/i);
  });
});

test('F17 explicitly negated relay instruction remains allowed under route BLOCK', (t) => {
  const sentence = 'Do not relay the complete packet before a verified collection route and all seven endpoint gates pass.';
  expectAxisHasNoFocusedProblem(t, {
    draftPath: (content) => transformBody(content, (body) => replaceRequiredLiteral(
      body,
      '## Why wattage-first selection may create avoidable rework',
      `${sentence}\n\n## Why wattage-first selection may create avoidable rework`,
      'explicitly negated relay control insertion anchor',
    )),
  }, /unverified.*(?:relay|convey|furnish|pass)|route.*policy.*before.*transmission|transmission.*block/i);
});

test('F17 production scope rejects test-fixture origin even when readiness fields claim ready', (t) => {
  const mutations = setProjectedFields(completeProductionLearnMutations(), {
    evidence_origin: 'test-fixture',
    fixture_identity: 'validator-branch-only',
    production_proof_eligible: false,
    production_readiness: 'ready',
    release_decision: 'ready-for-cms-draft',
  });
  expectBlockMatching(t, mutations, /production.*(?:requires|must use).*live-production|test-fixture.*(?:cannot|must not).*(?:ready|production)/i, setupCompleteProductionLearnEvidence);
});

test('F17 production scope rejects live-production with a fixture identity', (t) => {
  const mutations = setProjectedFields(completeProductionLearnMutations(), { fixture_identity: 'validator-branch-only' });
  expectBlockMatching(t, mutations, /live-production.*fixture_identity.*not-applicable/i, setupCompleteProductionLearnEvidence);
});

test('F17 production scope rejects live-production when production_proof_eligible is false', (t) => {
  const mutations = setProjectedFields(completeProductionLearnMutations(), { production_proof_eligible: false });
  expectBlockMatching(t, mutations, /live-production.*production_proof_eligible.*true|production.*eligible.*true/i, setupCompleteProductionLearnEvidence);
});

for (const [label, date] of [
  ['stale by 396 days', f17Stale396DaysAtReviewCeiling],
  ['later than reviewed_at', f17LaterThanReviewCeiling],
]) {
  test(`F17 production inventory checked_at is blocked when ${label}`, (t) => {
    expectBlockMatching(t, completeProductionValidateMutations(), /inventory.*checked_at.*(?:stale|reviewed_at|later|no more than 395)/i, (dir, paths) => {
      setupCompleteProductionValidateEvidence(dir, paths);
      rewriteEvidenceRecord(dir, 'production-inventory-evidence.md', (content) => replaceRequiredLiteral(content, 'checked_at: 2026-08-02T00:00:00Z', `checked_at: ${date}`, `inventory checked_at ${label}`));
    });
  });

  test(`F17 production content-inventory snapshot captured_at is blocked when ${label}`, (t) => {
    expectBlockMatching(t, completeProductionValidateMutations(), /content-inventory.*captured_at.*(?:stale|reviewed_at|later|no more than 395)|snapshot.*captured_at.*(?:stale|reviewed_at|later)/i, (dir, paths) => {
      setupCompleteProductionValidateEvidence(dir, paths);
      rewriteSnapshotAndEvidenceDigest(dir, 'production-content-inventory-2026-08-02.json', 'production-inventory-evidence.md', (snapshot) => {
        snapshot.captured_at = date;
        return snapshot;
      });
    });
  });

  test(`F17 production market evidence observed_at is blocked when ${label}`, (t) => {
    expectBlockMatching(t, completeProductionValidateMutations(), /market.*observed_at.*(?:stale|reviewed_at|later|no more than 395)|information.gain.*(?:stale|later)/i, (dir, paths) => {
      setupCompleteProductionValidateEvidence(dir, paths);
      rewriteEvidenceRecord(dir, 'production-information-gain-market.md', (content) => content.replaceAll('2026-08-02T00:00:00Z', date));
    });
  });

  test(`F17 production market snapshot captured_at is blocked when ${label}`, (t) => {
    expectBlockMatching(t, completeProductionValidateMutations(), /market-comparison.*captured_at.*(?:stale|reviewed_at|later|no more than 395)|snapshot.*captured_at.*(?:stale|reviewed_at|later)/i, (dir, paths) => {
      setupCompleteProductionValidateEvidence(dir, paths);
      rewriteSnapshotAndEvidenceDigest(dir, 'independent-serp-corpus-2026-08-02.json', 'production-information-gain-market.md', (snapshot) => {
        snapshot.captured_at = date;
        return snapshot;
      });
    });
  });

  test(`F17 production ICP evidence observed_at is blocked when ${label}`, (t) => {
    expectBlockMatching(t, completeProductionValidateMutations(), /ICP.*observed_at.*(?:stale|reviewed_at|later|no more than 395)|icp-evidence.*(?:stale|later)/i, (dir, paths) => {
      setupCompleteProductionValidateEvidence(dir, paths);
      rewriteEvidenceRecord(dir, 'production-icp-evidence.md', (content) => content.replaceAll('2026-08-02T00:00:00Z', date));
    });
  });
}

test('F17 production ICP evidence rejects a bad record digest', (t) => {
  expectBlockMatching(t, completeProductionValidateMutations(), /production-icp-evidence.*digest.*(?:mismatch|does not match|invalid)|digest.*production-icp-evidence/i, (dir, paths) => {
    setupCompleteProductionValidateEvidence(dir, paths);
    rewriteEvidenceRecord(dir, 'production-icp-evidence.md', (content) => replaceRequiredLiteral(content, /^digest:\s*sha256:[a-f0-9]{64}$/m, `digest: sha256:${'0'.repeat(64)}`, 'ICP bad digest'), { recomputeDigest: false });
  });
});

test('F17 production ICP evidence rejects the same stable producer and reviewer identity', (t) => {
  expectBlockMatching(t, completeProductionValidateMutations(), /ICP.*producer.*reviewer.*(?:different|separate)|producer_id.*independent_reviewer_id/i, (dir, paths) => {
    setupCompleteProductionValidateEvidence(dir, paths);
    rewriteEvidenceRecord(dir, 'production-icp-evidence.md', (content) => replaceRequiredLiteral(
      content,
      'independent_reviewer_id: wco-independent-reviewer-001',
      'independent_reviewer_id: wco-production-evidence-producer-001',
      'ICP producer reviewer identity collision',
    ));
  });
});

test('F17 production ICP refs reject a plain local fragment pretending to be confirmed evidence', (t) => {
  expectBlockMatching(t, completeProductionValidateMutations(), /production-icp-evidence.*(?:evidence-record|front matter|production evidence|structured)|ICP.*(?:record_type|digest|provenance)/i, (dir, paths) => {
    setupCompleteProductionValidateEvidence(dir, paths);
    const target = join(dir, 'production-icp-evidence.md');
    const current = readFileSync(target, 'utf8');
    const plain = '# Production ICP evidence\n\n## ICP evidence\n\nMid-market cargo OEMs are the target and consumer replacement buyers are excluded.\n';
    assert.notEqual(plain, current, 'plain ICP fragment mutation must not be a no-op');
    writeFileSync(target, plain);
  });
});


// Worker A P1 exact non-noop regressions. These pure contract probes remain independent
// from the live canonical example so a concurrent documentation edit cannot turn a
// validator regression into a false positive.
function p1Record(source, attributes, body = '') { return { source, attributes, body }; }

for (const [label, text] of [
  ['unrelated blocked clause', 'The route is blocked. Name a candidate or terminate.'],
  ['comma punctuation', 'The route is blocked, name a candidate or terminate.'],
  ['candidate-or-stop comma', 'Return a candidate, or stop now.'],
]) test(`P1 clause-local candidate gate blocks ${label}`, () => {
  const safe = 'Do not return candidate-or-stop before both declared gates pass.';
  assert.notEqual(text, safe, 'mutation must be exact and non-noop');
  assert.equal(articlePackageValidatorTestHooks.hasPrematureDecisionPromise(text), true);
  assert.equal(articlePackageValidatorTestHooks.hasPrematureDecisionPromise(safe), false);
});

test('P1 candidate-or-stop opens only after complete second-round package and named technical-owner review', () => {
  const blocked = 'Only after the complete second-round package, return candidate-or-stop.';
  const allowed = 'Only after the complete second-round package and named technical-owner review, return candidate-or-stop.';
  assert.notEqual(blocked, allowed, 'gate mutation must be non-noop');
  assert.equal(articlePackageValidatorTestHooks.hasPrematureDecisionPromise(blocked), true);
  assert.equal(articlePackageValidatorTestHooks.hasPrematureDecisionPromise(allowed), false);
});

test('P1 candidate scan consumes CTA inventory capability proof evidence handoff and endpoint task surfaces', () => {
  const attributes = {
    buyer_visible_cta_inventory: ['cta|Name a candidate or terminate.'],
    cta_buyer_visible_capability_proofs: ['proof|Return candidate-or-stop.'],
    capability_evidence_observable_output: 'Advance or reject now.',
    role_handoff_contracts: ['Engineer|Name a candidate or terminate.'],
    endpoint_target_task: 'Select a candidate or stop.',
  };
  const surfaces = articlePackageValidatorTestHooks.collectCandidateDecisionSurfaces(p1Record('surface-record', attributes));
  assert.equal(surfaces.length, 5);
  for (const [field, value] of surfaces) {
    const values = Array.isArray(value) ? value : [value];
    assert.equal(values.some(articlePackageValidatorTestHooks.hasPrematureDecisionPromise), true, `${field} must be consumed`);
  }
});

for (const phrase of [
  'Hand off the packet to engineering review.',
  'Give the packet to engineering review.',
  'Supply the packet to engineering review.',
  'Present the packet to engineering review.',
  'Turn in the packet to engineering review.',
  'Pass the packet to engineering review.',
  'Let engineering have the packet.',
  'Grant engineering access to the packet.',
  'Give engineering control of the packet.',
  'Make the packet available to engineering.',
  'Place the packet at the disposal of engineering.',
  'Once your worksheet is complete, the packet may be couriered to engineering review.',
]) test(`P1 open-class transfer blocks: ${phrase}`, () => {
  const safe = 'Save the packet locally.';
  assert.notEqual(phrase, safe, 'transfer mutation must be non-noop');
  assert.equal(articlePackageValidatorTestHooks.hasPacketTransferIntent(phrase), true);
  assert.equal(articlePackageValidatorTestHooks.isClauseLocalSafeTransfer(phrase), false);
});

for (const safe of [
  'Do not send the packet.',
  'Save the packet locally.',
  'Only after the verified route and endpoint policy pass may the packet be sent.',
]) test(`P1 clause-local transmission safety allows: ${safe}`, () => {
  assert.equal(articlePackageValidatorTestHooks.isClauseLocalSafeTransfer(safe), true);
});

test('P1 unrelated local-only clause does not exempt later transfer clause', () => {
  const text = 'Save the packet locally. Hand off the packet to engineering review.';
  const clauses = text.split('.').map((value) => value.trim()).filter(Boolean);
  assert.equal(articlePackageValidatorTestHooks.isClauseLocalSafeTransfer(clauses[0]), true);
  assert.equal(articlePackageValidatorTestHooks.isClauseLocalSafeTransfer(clauses[1]), false);
});

for (const [field, canonical, drift] of [
  ['page_h1 case', 'Cargo Hub-Motor Readiness', 'cargo Hub-Motor Readiness'],
  ['page_h1 spacing', 'Cargo Hub-Motor Readiness', 'Cargo  Hub-Motor Readiness'],
  ['page_h1 trim', 'Cargo Hub-Motor Readiness', ' Cargo Hub-Motor Readiness'],
  ['page_h1 NFKC', 'Cargo Hub-Motor Readiness', 'Ｃargo Hub-Motor Readiness'],
  ['page_h1 punctuation', 'Cargo Hub-Motor Readiness', 'Cargo Hub Motor Readiness'],
  ['first-round punctuation', 'packet completeness, missing-evidence list, and next review step', 'packet completeness; missing-evidence list; and next review step'],
]) test(`P1 raw exact scalar comparator blocks ${field}`, () => {
  assert.notEqual(canonical, drift, 'raw scalar mutation must be non-noop');
  assert.notEqual(articlePackageValidatorTestHooks.canonicalComparable(canonical, 'exact-raw-scalar'), articlePackageValidatorTestHooks.canonicalComparable(drift, 'exact-raw-scalar'));
});

test('P1 buyer-visible opening ICP fit and exclusion are required independently of frontmatter', () => {
  const brief = p1Record('brief', {
    primary_icp: 'cargo e-bike systems engineer',
    explicit_icp_exclusions: ['consumer replacement shoppers'],
    icp_fit_contract: 'cargo e-bike systems engineers preparing a technical review',
    icp_exclusion_contract: 'consumer replacement shoppers are outside scope',
  });
  const good = p1Record('draft', {}, '');
  good.body = 'For cargo e-bike systems engineers preparing a technical review. This is not for consumer replacement shoppers.\n\n## Decision';
  const bad = { ...good, source: 'draft-bad', body: 'Prepare a technical review packet.\n\n## Decision' };
  assert.notEqual(good.body, bad.body, 'opening deletion must be non-noop');
  const goodProblems = [];
  articlePackageValidatorTestHooks.validateBuyerVisibleOpeningIcp(brief, good, goodProblems);
  assert.deepEqual(goodProblems, []);
  const badProblems = [];
  articlePackageValidatorTestHooks.validateBuyerVisibleOpeningIcp(brief, bad, badProblems);
  assert.match(badProblems.join('\n'), /opening before the first H2.*ICP fit|opening before the first H2.*exclusion/i);
});

test('P1 section information-gain and field-set redundancy verdicts are four-record raw projections and fatal', () => {
  const attrs = { section_information_gain_verdict: 'pass', normalized_field_set_redundancy_verdict: 'pass', fatal_gate_verdict: 'pass' };
  const records = ['brief','draft','review','publish'].map((name) => p1Record(name, { ...attrs }));
  const review = records[2];
  const passProblems = [];
  articlePackageValidatorTestHooks.validateInformationGainAndRedundancyVerdicts(records, records[0], review, passProblems);
  assert.deepEqual(passProblems, []);
  const mutated = records.map((record) => p1Record(record.source, { ...record.attributes }));
  mutated[2].attributes.normalized_field_set_redundancy_verdict = 'block';
  assert.notEqual(mutated[2].attributes.normalized_field_set_redundancy_verdict, records[2].attributes.normalized_field_set_redundancy_verdict, 'decision-table verdict mutation must be non-noop');
  const problems = [];
  articlePackageValidatorTestHooks.validateInformationGainAndRedundancyVerdicts(mutated, mutated[0], mutated[2], problems);
  assert.match(problems.join('\n'), /normalized_field_set_redundancy_verdict.*match|fatal_gate_verdict=pass/i);
});

test('P1 published lifecycle evidence rows require all eight closed axes and byte-bound artifacts', (t) => {
  const root = mkdtempSync(join(tmpdir(), 'published-lifecycle-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const axes = ['authorization', 'cms-mutation', 'backend-readback', 'editor-reopen', 'anonymous-frontend', 'desktop', 'mobile', 'image-fetch-decode'];
  const now = new Date(Date.now() - 60_000).toISOString();
  const rows = axes.map((axis) => {
    const name = `${axis}.txt`;
    const body = `${axis} independently verified production acceptance evidence\n`;
    writeFileSync(join(root, name), body);
    const digest = `sha256:${createHash('sha256').update(body).digest('hex')}`;
    const url = ['anonymous-frontend','desktop','mobile','image-fetch-decode'].includes(axis) ? `https://www.cloudflare.com/${axis}` : 'not-applicable';
    return `${axis}|pass|${name}|${digest}|site-123|record-456|${url}|producer-123|reviewer-456|${now}|${now}|${now}`;
  });
  const publish = p1Record('publish', { publication_lifecycle_evidence_verdict: 'pass' });
  const passProblems = [];
  articlePackageValidatorTestHooks.validatePublishedLifecycleEvidenceRefs(rows, publish, root, now, passProblems);
  assert.deepEqual(passProblems, []);
  const missing = rows.slice(0, -1);
  assert.notDeepEqual(missing, rows, 'missing-axis mutation must be non-noop');
  const problems = [];
  articlePackageValidatorTestHooks.validatePublishedLifecycleEvidenceRefs(missing, publish, root, now, problems);
  assert.match(problems.join('\n'), /exactly eight|missing axis image-fetch-decode/i);
});

// Repair Worker A P1 fail-closed regressions. Each mutation is asserted non-noop
// before the validator hook is invoked so fixture drift cannot create a false pass.
function workerAP1StructuredSection(root, overrides = {}) {
  const artifactRef = 'structured-evidence.txt';
  const artifactBytes = 'independently reviewed structured evidence bytes\n';
  writeFileSync(join(root, artifactRef), artifactBytes);
  const values = {
    check_id: 'capability-proof',
    target_url: 'https://www.example.com/engineering-review',
    target_role: 'technical-review',
    target_task: 'Return packet completeness and the next review step in round one; only after the complete second-round package and named technical-owner review may the owner return candidate-or-stop.',
    observed_at: '2026-08-02T00:00:00Z',
    method: 'Independent endpoint-bound capability review.',
    observed_result: 'Packet completeness and the next bounded review step were observable; only after the complete second-round package and named technical-owner review may candidate-or-stop be observable.',
    artifact_digest: `sha256:${createHash('sha256').update(artifactBytes).digest('hex')}`,
    producer: 'Evidence Producer',
    producer_id: 'worker-a-producer-001',
    independent_reviewer: 'Independent Reviewer',
    independent_reviewer_id: 'worker-a-reviewer-001',
    capability_acceptance: 'Accepted round-one completeness output; only after the complete second-round package and named technical-owner review may candidate-or-stop be returned.',
    observable_output: 'Packet completeness and bounded next step in round one; only after the complete second-round package and named technical-owner review may candidate-or-stop be returned.',
    screenshot_or_trace_ref: artifactRef,
    ...overrides,
  };
  return `## Capability proof\n${Object.entries(values).map(([key, value]) => `${key}: ${value}`).join('\n')}\n`;
}

for (const field of ['target_task', 'observed_result', 'capability_acceptance', 'observable_output']) test(`Worker A P1 structured evidence candidate gate consumes ${field}`, (t) => {
  const root = mkdtempSync(join(tmpdir(), 'worker-a-structured-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const positive = workerAP1StructuredSection(root);
  const positiveProblems = [];
  articlePackageValidatorTestHooks.validateStructuredEvidenceSection(positive, 'evidence.md', 'capability_refs', '#capability-proof', positiveProblems, {
    evidenceRoot: root,
    expectedCheckId: 'capability-proof',
    requiredExtraFields: ['capability_acceptance', 'observable_output'],
    latestAllowedAt: '2026-08-02T16:00:00Z',
  });
  assert.deepEqual(positiveProblems, []);
  const mutation = workerAP1StructuredSection(root, { [field]: 'Name a candidate or terminate.' });
  assert.notEqual(mutation, positive, `${field} mutation must be non-noop`);
  const problems = [];
  articlePackageValidatorTestHooks.validateStructuredEvidenceSection(mutation, 'evidence.md', 'capability_refs', '#capability-proof', problems, {
    evidenceRoot: root,
    expectedCheckId: 'capability-proof',
    requiredExtraFields: ['capability_acceptance', 'observable_output'],
    latestAllowedAt: '2026-08-02T16:00:00Z',
  });
  assert.match(problems.join('\n'), new RegExp(`${field}.*complete second-round package.*named technical-owner review`, 'i'));
});

function workerATransmissionRecords(rows) {
  return ['brief', 'draft', 'review', 'publish'].map((source) => p1Record(source, { cta_transmission_action_inventory: [...rows] }));
}

test('Worker A P1 transmission inventory exact projection schema enum and buyer-visible registration', async (t) => {
  const canonical = ['final-cta|hand off|five-input packet|conditional-after-verification|primary|verified|route-evidence.md#route'];
  const positiveRecords = workerATransmissionRecords(canonical);
  const positiveDraft = { ...positiveRecords[1], body: 'Only after the verified route and endpoint policy pass may you hand off the five-input packet.' };
  const positiveProblems = [];
  articlePackageValidatorTestHooks.validateTransmissionActionInventory(positiveRecords, positiveRecords[0], positiveDraft, positiveProblems);
  assert.deepEqual(positiveProblems, []);
  const cases = [
    ['four-record projection', () => { const r = workerATransmissionRecords(canonical); r[3].attributes.cta_transmission_action_inventory = []; return [r, positiveDraft]; }, /must match|projection/i],
    ['seven-slot schema', () => [workerATransmissionRecords([canonical[0].replace('|route-evidence.md#route', '')]), positiveDraft], /exactly seven slots/i],
    ['closed instruction enum', () => [workerATransmissionRecords([canonical[0].replace('conditional-after-verification', 'send-whenever')]), positiveDraft], /instruction-mode.*closed allowlist/i],
    ['raw sequence drift', () => { const r = workerATransmissionRecords(canonical); r[2].attributes.cta_transmission_action_inventory = [canonical[0].replace('hand off', 'Hand off')]; return [r, positiveDraft]; }, /must match|projection/i],
    ['unregistered transfer', () => [workerATransmissionRecords(['local-save|save locally|five-input packet|local-only|not-applicable|not-applicable|not-applicable']), { ...positiveDraft, body: 'Hand off the five-input packet to engineering review.' }], /missing from cta_transmission_action_inventory/i],
  ];
  for (const [label, build, pattern] of cases) await t.test(label, () => {
    const [records, draft] = build();
    assert.notDeepEqual(records.map((r) => r.attributes.cta_transmission_action_inventory), positiveRecords.map((r) => r.attributes.cta_transmission_action_inventory), `${label} mutation must be non-noop`);
    const problems = [];
    articlePackageValidatorTestHooks.validateTransmissionActionInventory(records, records[0], draft, problems);
    assert.match(problems.join('\n'), pattern);
  });
});

test('Worker A P1 transmission capability statement is not a transfer but passive couriering is', () => {
  const capability = 'The buyer must be able to provide bounded engineering inputs.';
  const transfer = 'Once your worksheet is complete, the packet may be couriered to engineering review.';
  assert.notEqual(capability, transfer);
  assert.equal(articlePackageValidatorTestHooks.hasPacketTransferIntent(capability), false);
  assert.equal(articlePackageValidatorTestHooks.hasPacketTransferIntent(transfer), true);
});

test('Worker A P1 normalized packet redundancy keeps the complete field set in one local worksheet only', () => {
  const inputs = ['wheel diameter', 'loaded mass', 'grade target', 'duty cycle', 'battery voltage'];
  const brief = p1Record('brief', { stage_intake_contract: 'validate-technical', first_round_inquiry_inputs: inputs });
  const worksheet = inputs.map((value) => `- ${value}: [fill locally]`).join('\n');
  const positive = { source: 'draft', attributes: {}, body: `For engineering teams.\n\n## Five-input readiness check\nUse the decision table to identify missing assumptions without repeating the packet.\n\n## Assemble the worksheet locally\n${worksheet}\n\n## Request an engineering-readiness review\nUse the single worksheet prepared above through a verified route only.\n\n### Copyable local fallback\nKeep the worksheet local and request only the verified route.` };
  const passProblems = [];
  articlePackageValidatorTestHooks.validateNormalizedPacketRedundancy(brief, positive, passProblems);
  assert.deepEqual(passProblems, []);
  const repeated = `\n\n| Field | Value |\n|---|---|\n${inputs.map((value) => `| ${value} | review |`).join('\n')}`;
  const mutated = { ...positive, body: positive.body.replace('Use the decision table to identify missing assumptions without repeating the packet.', `Use this table.${repeated}`) };
  assert.notEqual(mutated.body, positive.body, 'decision-table mutation must be non-noop');
  const problems = [];
  articlePackageValidatorTestHooks.validateNormalizedPacketRedundancy(brief, mutated, problems);
  assert.match(problems.join('\n'), /normalized field-set redundancy.*decision table/i);
});

test('Worker A P1 search-demand observation end is bounded by evidence observation snapshot capture and canonical review', (t) => {
  const root = mkdtempSync(join(tmpdir(), 'worker-a-search-demand-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const query = 'cargo hub motor engineering readiness';
  const supportingQuery = 'cargo hub motor readiness inputs';
  const start = '2026-07-01T00:00:00Z';
  const end = '2026-07-31T23:59:59Z';
  const evidenceRef = 'search-demand.md#search-demand';
  const snapshotRef = 'search-demand.json';
  const write = ({ observedAt = '2026-08-01T00:00:00Z', capturedAt = '2026-08-01T00:00:00Z', observationEnd = end } = {}) => {
    const snapshotBytes = `${JSON.stringify({ captured_at: capturedAt })}\n`;
    writeFileSync(join(root, snapshotRef), snapshotBytes);
    const snapshotDigest = `sha256:${createHash('sha256').update(snapshotBytes).digest('hex')}`;
    writeFileSync(join(root, 'search-demand.md'), `---\nobserved_at: ${observedAt}\n---\n# Demand\n\n## Search demand\nexact_query_set: ${query}; ${supportingQuery}\nsource_or_platform: Google Search Console immutable export\nmarket: United States\nlanguage: en\ndevice: desktop\nobservation_window: 2026-07-01 to 2026-07-31\nobservation_window_start: ${start}\nobservation_window_end: ${observationEnd}\nmetric_type: search impressions\nbrand_non_brand_boundary: branded queries excluded and non-brand queries measured\nzero_or_low_demand_decision: keep the target because measured demand was non-zero\nseasonality_or_trend_note: trend was stable and no seasonal distortion was observed\nanalyst_conclusion: measured search impressions support the bounded query\nindependent_reviewer: Taylor Morgan\nsnapshot_ref: ${snapshotRef}\nsnapshot_digest: ${snapshotDigest}\nobserved_value_per_query:\n  - ${query}|25|impressions\n  - ${supportingQuery}|15|impressions\n`);
  };
  const attrs = { search_demand_observation_start_at: start, search_demand_observation_end_at: end };
  const records = ['brief','draft','review','publish'].map((source) => p1Record(source, { ...attrs }));
  Object.assign(records[0].attributes, { search_demand_evidence_status: 'confirmed', search_demand_evidence_refs: [evidenceRef], primary_query: query, supporting_query_variants: [supportingQuery], target_market: 'United States', target_content_language: 'en' });
  records[2].attributes.reviewed_at = '2026-08-02T16:00:00Z';
  write();
  const passProblems = [];
  articlePackageValidatorTestHooks.validateProductionSearchDemandEvidence(records, records[0], records[2], 'production', root, passProblems);
  assert.deepEqual(passProblems, []);
  const cases = [
    ['post-observation', { observedAt: '2026-07-31T12:00:00Z' }, records[2], /observation_window_end.*evidence observed_at|later/i],
    ['post-capture', { capturedAt: '2026-07-31T12:00:00Z' }, records[2], /observation_window_end.*snapshot captured_at|later/i],
  ];
  for (const [label, mutation, review, pattern] of cases) {
    write(mutation);
    const problems = [];
    articlePackageValidatorTestHooks.validateProductionSearchDemandEvidence(records, records[0], review, 'production', root, problems);
    assert.match(problems.join('\n'), pattern, label);
  }
  write();
  const earlyReview = p1Record('review', { ...attrs, reviewed_at: '2026-07-31T12:00:00Z' });
  assert.notEqual(earlyReview.attributes.reviewed_at, records[2].attributes.reviewed_at, 'post-review mutation must be non-noop');
  const reviewProblems = [];
  articlePackageValidatorTestHooks.validateProductionSearchDemandEvidence(records, records[0], earlyReview, 'production', root, reviewProblems);
  assert.match(reviewProblems.join('\n'), /search_demand_observation_end_at.*reviewed_at|observation_window_end.*reviewed_at|later/i);
});

test('Worker A P1 identity provenance timestamp chain is fresh exact and record-bound', (t) => {
  const root = mkdtempSync(join(tmpdir(), 'worker-a-identity-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const attrs = {
    package_id: 'PKG-WORKER-A-001', author_id: 'worker-a-author-001', producer_id: 'worker-a-producer-001', independent_reviewer_id: 'worker-a-reviewer-001', remediation_participant_ids: [],
    identity_provenance_evidence_refs: ['identity.md#identity-provenance'], identity_provenance_observed_at: '2026-08-02T00:00:00Z', identity_provenance_reviewed_at: '2026-08-02T12:00:00Z', identity_provenance_review_ceiling: '2026-08-02T16:00:00Z', reviewer_separation_verdict: 'pass',
  };
  const write = ({ sectionObserved = attrs.identity_provenance_observed_at, recordObserved = sectionObserved, captured = sectionObserved } = {}) => writeFileSync(join(root, 'identity.md'), `---\nobserved_at: ${recordObserved}\ncaptured_at: ${captured}\n---\n# Identity\n\n## Identity provenance\npackage_id: ${attrs.package_id}\nauthor_id: ${attrs.author_id}\nproducer_id: ${attrs.producer_id}\nindependent_reviewer_id: ${attrs.independent_reviewer_id}\nremediation_participant_ids: []\nverification_method: independent identity registry comparison\nobserved_at: ${sectionObserved}\n`);
  const records = ['brief','draft','review','publish'].map((source) => p1Record(source, { ...attrs }));
  records[2].attributes.reviewed_at = '2026-08-03T00:00:00+08:00';
  write();
  const passProblems = [];
  articlePackageValidatorTestHooks.validateStableActorIdentityContract(records, records[0], records[2], 'production', root, passProblems);
  assert.deepEqual(passProblems, []);
  const cases = [
    ['stale', { sectionObserved: '2024-01-01T00:00:00Z', recordObserved: '2024-01-01T00:00:00Z', captured: '2024-01-01T00:00:00Z' }, /stale|fresh/i],
    ['post-review', { sectionObserved: '2026-08-02T17:00:00Z', recordObserved: '2026-08-02T17:00:00Z', captured: '2026-08-02T17:00:00Z' }, /observed_at.*reviewed_at|later/i],
    ['record observed drift', { recordObserved: '2026-08-02T01:00:00Z' }, /section observed_at.*record observed_at/i],
    ['record capture drift', { captured: '2026-08-02T01:00:00Z' }, /captured_at.*section observed_at/i],
  ];
  for (const [label, mutation, pattern] of cases) {
    write(mutation);
    const problems = [];
    articlePackageValidatorTestHooks.validateStableActorIdentityContract(records, records[0], records[2], 'production', root, problems);
    assert.match(problems.join('\n'), pattern, label);
  }
});

test('Worker A P1 CTA policy time version digest and 18-slot collection row fail closed', () => {
  const canonical = { source: 'brief', policyEffectiveAt: '2026-08-01T00:00:00Z', policyCheckedAt: '2026-08-02T00:00:00Z', policyObservedAt: '2026-08-02T00:00:00Z', policyReviewedAt: '2026-08-02T12:00:00Z', policyReviewCeiling: '2026-08-02T16:00:00Z', canonicalReviewedAt: '2026-08-03T00:00:00+08:00' };
  const passProblems = [];
  articlePackageValidatorTestHooks.validateCtaPolicyTemporalContract({ ...canonical, problems: passProblems });
  assert.deepEqual(passProblems, []);
  for (const [label, patch, pattern] of [
    ['stale checked-at', { policyCheckedAt: '2024-01-01T00:00:00Z' }, /checked_at.*stale|fresh/i],
    ['checked after observed', { policyCheckedAt: '2026-08-02T10:00:00Z', policyObservedAt: '2026-08-02T00:00:00Z' }, /checked_at.*observed_at|later/i],
    ['post-review ceiling', { policyReviewCeiling: '2026-08-02T17:00:00Z' }, /review_ceiling.*reviewed_at|later/i],
  ]) {
    const problems = [];
    const mutated = { ...canonical, ...patch };
    assert.notDeepEqual(mutated, canonical, `${label} mutation must be non-noop`);
    articlePackageValidatorTestHooks.validateCtaPolicyTemporalContract({ ...mutated, problems });
    assert.match(problems.join('\n'), pattern, label);
  }
  const expected = { policy_contract_id: 'POLICY-001', policy_version: '2026.08.01', policy_digest: `sha256:${'a'.repeat(64)}` };
  for (const field of ['policy_version', 'policy_digest']) {
    const map = new Map(Object.entries(expected));
    map.set(field, `${map.get(field)}-drift`);
    const problems = [];
    articlePackageValidatorTestHooks.validateCtaPolicyEvidenceProjection(map, expected, 'brief', 'policy.md#policy', problems);
    assert.match(problems.join('\n'), new RegExp(`${field}.*exactly bind`, 'i'));
  }
  const row = ['primary','https://www.example.com/review','same-as-cta-required-inputs','Use inputs for bounded technical review','Retain until review closes or 30 days','Delete through the verified request path','Avery Chen, Data Policy Owner','POLICY-001','2026.08.01',`sha256:${'a'.repeat(64)}`,'2026-08-02T00:00:00Z','2026-08-02T00:00:00Z','2026-08-02T12:00:00Z','2026-08-02T16:00:00Z','confirmed','accepted','policy.md#policy','deletion.md#deletion'].join('|');
  const rowProblems = [];
  const parsed = articlePackageValidatorTestHooks.parseCollectionPolicyRows(p1Record('brief', { cta_collection_route_policy_contracts: [row] }), rowProblems);
  assert.deepEqual(rowProblems, []);
  assert.equal(parsed.length, 1);
  const short = row.split('|').slice(0, -1).join('|');
  assert.notEqual(short, row, '18-slot row mutation must be non-noop');
  const shortProblems = [];
  articlePackageValidatorTestHooks.parseCollectionPolicyRows(p1Record('brief', { cta_collection_route_policy_contracts: [short] }), shortProblems);
  assert.match(shortProblems.join('\n'), /row must use route-id.*deletion-capability-evidence-refs/i);
});

test('Worker A P1 published lifecycle rejects every missing axis unknown status digest drift and post-review ceiling', (t) => {
  const root = mkdtempSync(join(tmpdir(), 'worker-a-published-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const axes = ['authorization', 'cms-mutation', 'backend-readback', 'editor-reopen', 'anonymous-frontend', 'desktop', 'mobile', 'image-fetch-decode'];
  const rowFor = (axis) => {
    const ref = `${axis}.txt`; const bytes = `${axis} lifecycle evidence\n`; writeFileSync(join(root, ref), bytes);
    const digest = `sha256:${createHash('sha256').update(bytes).digest('hex')}`;
    const url = ['anonymous-frontend','desktop','mobile','image-fetch-decode'].includes(axis) ? `https://www.cloudflare.com/${axis}` : 'not-applicable';
    return `${axis}|pass|${ref}|${digest}|site-001|record-001|${url}|producer-001|reviewer-001|2026-08-02T00:00:00Z|2026-08-02T12:00:00Z|2026-08-02T16:00:00Z`;
  };
  const rows = axes.map(rowFor);
  const publish = p1Record('publish', { publication_lifecycle_evidence_verdict: 'pass' });
  const reviewAt = '2026-08-03T00:00:00+08:00';
  const passProblems = [];
  articlePackageValidatorTestHooks.validatePublishedLifecycleEvidenceRefs(rows, publish, root, reviewAt, passProblems);
  assert.deepEqual(passProblems, []);
  for (const axis of axes) {
    const missing = rows.filter((row) => !row.startsWith(`${axis}|`));
    assert.notDeepEqual(missing, rows, `${axis} deletion must be non-noop`);
    const problems = [];
    articlePackageValidatorTestHooks.validatePublishedLifecycleEvidenceRefs(missing, publish, root, reviewAt, problems);
    assert.match(problems.join('\n'), /exactly eight|missing axis/i);
  }
  for (const [label, mutate, pattern] of [
    ['unknown status', (row) => row.replace('|pass|', '|unknown|'), /requires status=pass/i],
    ['digest byte drift', (row) => row.replace(/sha256:[a-f0-9]{64}/, `sha256:${'f'.repeat(64)}`), /digest must exactly match artifact-ref bytes/i],
    ['post-review ceiling', (row) => row.replace('2026-08-02T16:00:00Z', '2026-08-02T17:00:00Z'), /review-ceiling.*canonical reviewed_at|later/i],
  ]) {
    const changed = [mutate(rows[0]), ...rows.slice(1)];
    assert.notDeepEqual(changed, rows, `${label} mutation must be non-noop`);
    const problems = [];
    articlePackageValidatorTestHooks.validatePublishedLifecycleEvidenceRefs(changed, publish, root, reviewAt, problems);
    assert.match(problems.join('\n'), pattern, label);
  }
});

// F22 integration gates: consume the full four-record validator path, bind CTA
// measurement evidence row-by-row, and mutation-kill the two lifecycle call sites.

function rewriteCtaMeasurementEvidence(dir, mutateBody) {
  const target = join(dir, 'cta-measurement-evidence.md');
  const content = readFileSync(target, 'utf8');
  const closing = content.indexOf('\n---\n', 4);
  assert.notEqual(closing, -1, 'CTA measurement evidence must contain front matter');
  const bodyStart = closing + 5;
  const originalBody = content.slice(bodyStart);
  const body = mutateBody(originalBody);
  assert.notEqual(body, originalBody, 'CTA measurement evidence mutation must be non-noop');
  const digest = `sha256:${createHash('sha256').update(body).digest('hex')}`;
  const output = replaceField(`${content.slice(0, bodyStart)}${body}`, 'digest', digest);
  writeFileSync(target, output);
}

function mutateMeasurementRowAcrossAll(base, rowIndex, mutateParts) {
  return mutateProjectedArray(base, 'cta_measurement_map', (rows) => rows.map((row, index) => {
    if (index !== rowIndex) return row;
    const parts = row.split('|');
    const before = [...parts];
    mutateParts(parts);
    assert.notDeepEqual(parts, before, `CTA measurement row ${rowIndex + 1} mutation must be non-noop`);
    return parts.join('|');
  }));
}

function mutateConversionRowAcrossAll(base, rowIndex, mutateParts) {
  return mutateProjectedArray(base, 'conversion_surface_map', (rows) => rows.map((row, index) => {
    if (index !== rowIndex) return row;
    const parts = row.split('|');
    const before = [...parts];
    mutateParts(parts);
    assert.notDeepEqual(parts, before, `conversion row ${rowIndex + 1} mutation must be non-noop`);
    return parts.join('|');
  }));
}

const publishedLifecycleAxes = ['authorization', 'cms-mutation', 'backend-readback', 'editor-reopen', 'anonymous-frontend', 'desktop', 'mobile', 'image-fetch-decode'];

function publishedLifecycleArtifactBytes(axis) {
  return `fixture-only lifecycle evidence for ${axis}; this exercises validator binding and is not a real publication claim.\n`;
}

function canonicalPublishedLifecycleRows() {
  return publishedLifecycleAxes.map((axis) => {
    const bytes = publishedLifecycleArtifactBytes(axis);
    const digest = `sha256:${createHash('sha256').update(bytes).digest('hex')}`;
    const url = ['anonymous-frontend', 'desktop', 'mobile', 'image-fetch-decode'].includes(axis)
      ? `https://www.cloudflare.com/cargo-motor-readiness-${axis}`
      : 'not-applicable';
    return `${axis}|pass|published-${axis}.txt|${digest}|site-fixture-001|record-fixture-001|${url}|wco-lifecycle-producer-001|wco-lifecycle-reviewer-001|2026-08-02T00:00:00Z|2026-08-02T12:00:00Z|2026-08-02T16:00:00Z`;
  });
}

function completePublishedProductionValidateMutations() {
  const output = setProjectedFields(completeProductionValidateMutations(), {
    release_decision: 'published',
    operation_mode: 'publish',
  });
  const basePublish = output.publishPath;
  output.publishPath = (content) => {
    let result = basePublish(content);
    for (const field of [
      'cms_mutation_status', 'backend_readback_status', 'editor_reopen_status', 'anonymous_frontend_status',
      'desktop_acceptance_status', 'mobile_acceptance_status', 'image_fetch_decode_status', 'html_lang_status',
      'canonical_status', 'article_json_ld_status', 'final_dom_image_alt_renderer_status', 'api_write_status',
      'authorization_status', 'frontend_acceptance_status', 'cms_action_status',
    ]) result = setField(result, field, JSON.stringify('pass'));
    result = setField(result, 'publication_status', JSON.stringify('published'));
    result = setField(result, 'rollback_ready', 'true');
    result = setField(result, 'publication_lifecycle_evidence_rows', JSON.stringify(canonicalPublishedLifecycleRows()));
    result = setField(result, 'publication_lifecycle_evidence_verdict', JSON.stringify('pass'));
    return result;
  };
  return output;
}

function setupCompletePublishedProductionValidateEvidence(dir, paths) {
  setupCompleteProductionValidateEvidence(dir, paths);
  for (const axis of publishedLifecycleAxes) writeFileSync(join(dir, `published-${axis}.txt`), publishedLifecycleArtifactBytes(axis));
}

function runValidatorMutantWithout(t, exactCall, label, paths) {
  const validatorUrl = new URL('./validate-article-package.mjs', import.meta.url);
  const source = readFileSync(validatorUrl, 'utf8');
  const occurrences = source.split(exactCall).length - 1;
  assert.equal(occurrences, 1, `${label} mutation-kill must remove exactly one active call site`);
  const mutated = source.replace(exactCall, `/* mutation-kill removed ${label} */`);
  assert.notEqual(mutated, source, `${label} validator mutant must differ from the canonical validator`);
  const nonce = `${label}-${process.pid}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const mutantUrl = new URL(`./.article-package-mutant-${nonce}.mjs`, import.meta.url);
  const runnerUrl = new URL(`./.article-package-mutant-runner-${nonce}.mjs`, import.meta.url);
  writeFileSync(mutantUrl, mutated);
  writeFileSync(runnerUrl, [
    `import { validateArticlePackage } from ${JSON.stringify(mutantUrl.href)};`,
    `const paths = JSON.parse(Buffer.from(process.argv[2], 'base64url').toString('utf8'));`,
    `process.stdout.write(JSON.stringify(validateArticlePackage(paths)));`,
    '',
  ].join('\n'));
  t.after(() => {
    rmSync(mutantUrl, { force: true });
    rmSync(runnerUrl, { force: true });
  });
  const result = spawnSync(process.execPath, [
    fileURLToPath(runnerUrl),
    Buffer.from(JSON.stringify(paths)).toString('base64url'),
  ], { encoding: 'utf8' });
  assert.equal(result.status, 0, `${label} mutant runner failed: ${result.stderr || result.stdout}`);
  return JSON.parse(result.stdout);
}

test('F22 CTA measurement and conversion maps reject inventory identity location interaction and owner drift through the full package validator', async (t) => {
  const cases = [
    ['ghost measurement surface ID', mutateMeasurementRowAcrossAll(completeProductionValidateMutations(), 0, (parts) => { parts[0] = 'primary-ghost-surface-01'; }), /surface-id and role must exactly bind conversion_surface_map|must exist in buyer_visible_cta_inventory/i],
    ['measurement surface role drift', mutateMeasurementRowAcrossAll(completeProductionValidateMutations(), 1, (parts) => { parts[1] = 'fallback'; }), /row 2 surface-role must exactly be soft|surface-id and role must exactly bind conversion_surface_map/i],
    ['conversion surface ID absent from inventory', mutateConversionRowAcrossAll(completeProductionValidateMutations(), 0, (parts) => { parts[0] = 'primary-ghost-conversion-01'; }), /conversion_surface_map surface-id .* must exist in buyer_visible_cta_inventory/i],
    ['conversion locator drift', mutateConversionRowAcrossAll(completeProductionValidateMutations(), 0, (parts) => { parts[3] = 'drifted final CTA locator'; }), /location must exactly match buyer_visible_cta_inventory locator/i],
    ['conversion interaction drift', mutateConversionRowAcrossAll(completeProductionValidateMutations(), 0, (parts) => { parts[4] = 'content-navigation'; }), /interaction must exactly match buyer_visible_cta_inventory interaction-type/i],
    ['measurement owner drift', mutateMeasurementRowAcrossAll(completeProductionValidateMutations(), 0, (parts) => { parts[14] = 'Jordan Rivera, Drifted Analytics Owner'; }), /accountable-owner must exactly bind buyer_visible_cta_inventory owner/i],
  ];
  for (const [label, mutations, pattern] of cases) await t.test(label, () => {
    expectBlockMatching(t, mutations, pattern, setupCompleteProductionValidateEvidence);
  });
});

test('F22 CTA measurement evidence rejects unrelated fragment and exact digest-set stale missing duplicate and ghost attacks through the full package validator', async (t) => {
  const unrelatedRefMutations = mutateMeasurementRowAcrossAll(completeProductionValidateMutations(), 0, (parts) => { parts[15] = 'cta-measurement-evidence.md#unrelated-notes'; });
  const unrelatedProjected = setProjectedFields(unrelatedRefMutations, {
    cta_abandonment_measurement_refs: ['cta-measurement-evidence.md#unrelated-notes'],
  });
  await t.test('unrelated Markdown fragment', () => {
    expectBlockMatching(t, unrelatedProjected, /evidence-refs do not bind its exact measurement_row_sha256|expected measurement-plan|fragment/i, (dir, paths) => {
      setupCompleteProductionValidateEvidence(dir, paths);
      rewriteCtaMeasurementEvidence(dir, (body) => `${body}\n## Unrelated notes\nThis unrelated section records editorial scheduling only and does not bind any CTA measurement row digest.\n`);
    });
  });
  for (const [label, mutateBody] of [
    ['stale row digest', (body) => body.replace(/measurement_row_sha256: sha256:[a-f0-9]{64}/i, `measurement_row_sha256: sha256:${'a'.repeat(64)}`)],
    ['missing row digest', (body) => body.replace(/^measurement_row_sha256: sha256:[a-f0-9]{64}\n?/im, '')],
    ['duplicate row digest', (body) => {
      const first = body.match(/^measurement_row_sha256: sha256:[a-f0-9]{64}$/im)?.[0];
      assert.ok(first, 'canonical evidence must expose a row digest');
      return `${body.trimEnd()}\n${first}\n`;
    }],
    ['ghost row digest', (body) => `${body.trimEnd()}\nmeasurement_row_sha256: sha256:${'f'.repeat(64)}\n`],
  ]) await t.test(label, () => {
    expectBlockMatching(t, completeProductionValidateMutations(), /exact current measurement_row_sha256 set once each, with no ghost, missing, stale, or duplicate row digest/i, (dir, paths) => {
      setupCompleteProductionValidateEvidence(dir, paths);
      rewriteCtaMeasurementEvidence(dir, mutateBody);
    });
  });
});

test('F22 stage-specific CTA measurement qualification and commercial acceptance events fail closed through the full package validator', async (t) => {
  await t.test('Learn cannot inherit technical-qualified', () => {
    const mutations = mutateMeasurementRowAcrossAll(completeProductionLearnMutations(), 0, (parts) => { parts[9] = 'cta_learn_primary_technical_qualified'; });
    expectBlockMatching(t, mutations, /qualification-event must be not-applicable for stage=learn/i, setupCompleteProductionLearnEvidence);
  });
  await t.test('Validate cannot inherit sales-accepted', () => {
    const mutations = mutateMeasurementRowAcrossAll(completeProductionValidateMutations(), 0, (parts) => { parts[10] = 'cta_validate_primary_sales_accepted'; });
    expectBlockMatching(t, mutations, /commercial-acceptance-event must be not-applicable for stage=validate/i, setupCompleteProductionValidateEvidence);
  });
  await t.test('Buy without commercial conditions cannot declare sales accepted', () => {
    let mutations = overrideMutationFields(completeBuyCommercialMutations(), {
      sales_commercial_inputs: [],
    });
    mutations = mutateMeasurementRowAcrossAll(mutations, 0, (parts) => { parts[10] = 'cta_buy_primary_sales_accepted_without_conditions'; });
    expectBlockMatching(t, mutations, /commercial-acceptance-event must be not-applicable for stage=buy|buy-commercial intake requires a commercial\/RFQ packet/i);
  });
});

test('F22 transmission inventory closed-enum attack is blocked by the full validator and kills the active integration call', async (t) => {
  const mutations = mutateProjectedArray({}, 'cta_transmission_action_inventory', (rows) => rows.map((row, index) => {
    if (index !== 2) return row;
    const parts = row.split('|');
    assert.equal(parts[3], 'prohibited-until-verified');
    parts[3] = 'send-whenever';
    return parts.join('|');
  }));
  const paths = makeFixture(t, mutations);
  const official = validateArticlePackage(paths);
  assert.equal(official.ok, false, 'official validator must block the transmission inventory attack');
  assert.match(official.problems.join('\n'), /instruction-mode must use the closed allowlist/i);
  const escaped = runValidatorMutantWithout(t, '  validateTransmissionActionInventory(records, brief, draft, problems);', 'transmission-main-call', paths);
  assert.doesNotMatch(escaped.problems.join('\n'), /cta_transmission_action_inventory instruction-mode must use the closed allowlist/i, 'removing the active main-path call must let this exact attack evade the transmission rule');
});

test('F22 published lifecycle has a full production-shaped positive and main-path negative matrix', async (t) => {
  const baselinePaths = makeFixture(t, completePublishedProductionValidateMutations(), setupCompletePublishedProductionValidateEvidence);
  const baseline = validateArticlePackage(baselinePaths);
  assert.equal(baseline.ok, true, baseline.problems.join('\n'));
  assert.equal(baseline.releaseDecision, 'published');
  for (const [label, mutate, pattern] of [
    ['missing axis', (rows) => rows.slice(0, -1), /exactly eight lifecycle evidence rows|missing axis/i],
    ['unknown status', (rows) => rows.map((row, index) => index === 0 ? row.replace('|pass|', '|unknown|') : row), /requires status=pass/i],
    ['artifact digest drift', (rows) => rows.map((row, index) => index === 0 ? row.replace(/sha256:[a-f0-9]{64}/, `sha256:${'e'.repeat(64)}`) : row), /digest must exactly match artifact-ref bytes/i],
    ['post-review ceiling', (rows) => rows.map((row, index) => index === 0 ? row.replace('2026-08-02T16:00:00Z', '2026-08-03T01:00:00+08:00') : row), /review-ceiling.*canonical reviewed_at|later/i],
  ]) await t.test(label, () => {
    const mutations = mutateProjectedArray(completePublishedProductionValidateMutations(), 'publication_lifecycle_evidence_rows', mutate, ['publishPath']);
    expectBlockMatching(t, mutations, pattern, setupCompletePublishedProductionValidateEvidence);
  });
});

test('F22 published lifecycle attack kills the active integration call', async (t) => {
  const mutations = mutateProjectedArray(completePublishedProductionValidateMutations(), 'publication_lifecycle_evidence_rows', (rows) => rows.slice(0, -1), ['publishPath']);
  const paths = makeFixture(t, mutations, setupCompletePublishedProductionValidateEvidence);
  const official = validateArticlePackage(paths);
  assert.equal(official.ok, false, 'official validator must block a published package missing a lifecycle axis');
  assert.match(official.problems.join('\n'), /exactly eight lifecycle evidence rows|missing axis/i);
  const escaped = runValidatorMutantWithout(t, "      validatePublishedLifecycleEvidenceRefs(publish.attributes.publication_lifecycle_evidence_rows, publish, packageRoot, string(review, 'reviewed_at', problems), problems);", 'published-lifecycle-main-call', paths);
  assert.equal(escaped.ok, true, escaped.problems.join('\n'));
  assert.equal(escaped.releaseDecision, 'published');
});
