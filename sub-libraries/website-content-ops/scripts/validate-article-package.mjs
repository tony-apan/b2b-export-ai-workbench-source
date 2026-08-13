#!/usr/bin/env node
import { existsSync, lstatSync, readFileSync, realpathSync, statSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, isAbsolute, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  parseMarkdownFrontMatter,
  requireStringArrayField,
  requireStringField,
} from './front-matter.mjs';
import {
  ALLINCMS_ARTICLE_FORMAT_SUPPORT,
  extractPublishableArticleMarkdown,
  markdownToAllinCmsSlate,
} from '../ADAPTERS/cms/allincms/article-content-formats.mjs';

const PASS = 'pass';
const CANONICAL_VERDICTS = new Set(['pass', 'block', 'not-applicable']);
const ARTICLE_DECISION_SEQUENCE_ROLES = ['hook', 'diagnose', 'decide', 'de-risk', 'act'];
const CONVERSION_SURFACE_ROLES = ['primary', 'soft', 'fallback'];
const CTA_INVENTORY_LOCATION_KINDS = new Set(['pre-h2', 'paragraph', 'list', 'table', 'strong-label', 'link', 'button', 'heading', 'blockquote']);
const CTA_INVENTORY_INTERACTION_TYPES = new Set(['content-navigation', 'inline-no-input', 'local-tool', 'input-collecting', 'human-handoff', 'commercial']);
const PRODUCTION_READINESS_SCOPES = new Set(['cms-draft-content-contract']);
const TRANSMISSION_VERB_SOURCE = 'submit|send|share|upload|email|forward|transfer|transmit|deliver|provide|dispatch|relay|convey|furnish|supply|present|courier(?:ed|ing)?|pass|post|paste|attach|fill(?:\\s+(?:in|out))?|enter|import|drag|drop(?:\\s+off)?|hand\\s+(?:over|off)|turn\\s+in|give';
const TRANSFER_OF_CONTROL_PATTERN = /\b(?:take\s+possession\s+of|make\s+(?:the\s+)?(?:packet|worksheet|file|data|inputs?|it|them)\s+available\s+to|place\s+(?:the\s+)?(?:packet|worksheet|file|data|inputs?|it|them)\s+at\s+(?:the\s+)?disposal\s+of|let\s+[a-z0-9._ -]{1,60}\s+have|grant\s+[a-z0-9._ -]{1,60}\s+access\s+to|give\s+[a-z0-9._ -]{1,60}\s+control\s+of)\b/i;
const BUYER_ROUTE_ACTION_PATTERN = new RegExp(`\\b(?:${TRANSMISSION_VERB_SOURCE}|contact|book|download|request|route|start|apply|register|join|call|schedule|get|order|buy|visit|message|use\\s+(?:the|this|a)\\s+(?:form|portal|channel|route))\\b`, 'i');
const DIRECT_TRANSMISSION_ACTION_PATTERN = new RegExp(`\\b(?:${TRANSMISSION_VERB_SOURCE})\\b`, 'i');
const DIRECT_COPY_ACTION_PATTERN = /\bcopy\b[^.!?]{0,40}\b(?:packet|message|file|drawing|data|request|details?|inputs?|it|them|this|that)\b/i;
const EVIDENCE_MAX_AGE_DAYS = 395;
const SEARCH_EVIDENCE_MAX_AGE_DAYS = 180;
const CTA_POLICY_MAX_AGE_DAYS = 180;
const IDENTITY_PROVENANCE_MAX_AGE_DAYS = 395;
const DEPRECATED_ARTICLE_PACKAGE_FIELDS = new Map([
  ['dominant_buyer_task', 'dominant_task_contract'],
  ['information_gain_status', 'information_gain_artifact_status plus market_information_gain_status'],
  ['frontend_seo_status', 'production_evidence_review_verdict plus explicit frontend acceptance status fields'],
  ['total_score', 'structure_score plus production_evidence_score'],
  ['routing_owner', 'technical_qualification_owner or the applicable canonical owner field'],
  ['inventory_zero_result_evidence_ref', 'inventory_zero_result_evidence_refs'],
  ['primary_query_cluster', 'primary_query plus supporting_query_variants'],
  ['qualified_inquiry_definition', 'technical_qualification_definition'],
  ['minimum_completeness_threshold', 'technical_qualification_definition plus cta_required_inputs'],
  ['qualified_inquiry_contract_status', 'technical_qualification_contract_status'],
  ['project_stage', 'stage'],
  ['technical_review_owner', 'technical_qualification_owner'],
  ['sales_owner', 'sales_acceptance_owner'],
  ['commercial_intent_signals', 'sales_commercial_intent_status plus sales_commercial_inputs_status'],
  ['commercial_next_step', 'sales_acceptance_next_step'],
  ['sales_acceptance_reason_codes', 'qualification_reason_codes or the canonical sales acceptance fields'],
  ['internal_link_reference_parity_status', 'internal_link_reference_check_execution_status plus internal_link_reference_evidence_result plus internal_link_reference_gate_verdict'],
  ['internal_link_reachability_status', 'internal_link_reachability_check_execution_status plus internal_link_reachability_evidence_result plus internal_link_reachability_gate_verdict'],
  ['internal_link_task_acceptance_status', 'internal_link_capability check/evidence/gate fields and role handoff contracts'],
  ['cta_capability_proof_status', 'cta_capability_check_execution_status plus cta_capability_evidence_result plus cta_capability_gate_verdict'],
  ['cta_capability_proof_refs', 'cta_capability_evidence_refs'],
  ['cta_destination_reference_parity_status', 'cta_reference_check_execution_status plus cta_reference_evidence_result plus cta_reference_gate_verdict'],
  ['cta_destination_reachability_status', 'cta_reachability_check_execution_status plus cta_reachability_evidence_result plus cta_reachability_gate_verdict'],
  ['cta_destination_reachability_refs', 'cta_reachability_evidence_refs'],
  ['fabricated_claims', 'unsupported_outcome_claims_status or unsupported_outcome_claims_verdict'],
  ['unsupported_performance_claims', 'unsupported_outcome_claims_status or unsupported_outcome_claims_verdict'],
  ['buyer_role_matrix', 'secondary_buyer_role_contracts'],
  ['reviewer', 'reviewer_identity'],
  ['five_node_causal_chain_verdict', 'six_node_causal_chain_verdict'],
  ['direct_answer_verdict', 'direct_answer_six_slot_verdict'],
  ['title_task_stage_parity_verdict', 'the four canonical title and H1 parity verdicts'],
]);

function decodeTopLevelSequenceItem(raw, source, lineNumber) {
  const value = raw.trim();
  if (!value) throw new Error(`${source}:${lineNumber} empty YAML sequence item is not supported`);
  if (value.startsWith('"')) {
    try {
      const parsed = JSON.parse(value);
      if (typeof parsed !== 'string') throw new Error('not a string');
      return parsed;
    } catch {
      throw new Error(`${source}:${lineNumber} invalid double-quoted YAML sequence item`);
    }
  }
  if (value.startsWith("'")) {
    if (!value.endsWith("'")) throw new Error(`${source}:${lineNumber} unterminated single-quoted YAML sequence item`);
    return value.slice(1, -1).replace(/''/g, "'");
  }
  if (/^[>|][+-]?$/.test(value) || /^[\[{]/.test(value)) {
    throw new Error(`${source}:${lineNumber} nested or multiline YAML sequence items are not supported`);
  }
  return value;
}

function normalizeTopLevelSequenceFrontMatter(content, source) {
  const normalized = content.replace(/\r\n?/g, '\n');
  if (!normalized.startsWith('---\n')) return normalized;
  const lines = normalized.split('\n');
  const closing = lines.indexOf('---', 1);
  if (closing < 0) return normalized;
  const output = [lines[0]];
  const sequenceAnchors = new Map();
  for (let index = 1; index < closing; index += 1) {
    const line = lines[index];
    const aliasMatch = line.match(/^([A-Za-z_][A-Za-z0-9_-]*):\s*\*([A-Za-z_][A-Za-z0-9_-]*)\s*$/);
    if (aliasMatch) {
      if (!sequenceAnchors.has(aliasMatch[2])) throw new Error(`${source}:${index + 1} unknown top-level YAML sequence alias ${aliasMatch[2]}`);
      output.push(`${aliasMatch[1]}: ${JSON.stringify(sequenceAnchors.get(aliasMatch[2]))}`);
      continue;
    }
    const match = line.match(/^([A-Za-z_][A-Za-z0-9_-]*):(?:\s*&([A-Za-z_][A-Za-z0-9_-]*))?\s*$/);
    if (!match || !/^  -\s+/.test(lines[index + 1] || '')) {
      output.push(line);
      continue;
    }
    const items = [];
    while (index + 1 < closing && /^  -\s+/.test(lines[index + 1])) {
      index += 1;
      items.push(decodeTopLevelSequenceItem(lines[index].replace(/^  -\s+/, ''), source, index + 1));
    }
    if (match[2]) sequenceAnchors.set(match[2], items);
    output.push(`${match[1]}: ${JSON.stringify(items)}`);
  }
  output.push(...lines.slice(closing));
  return output.join('\n');
}

function parseArticleMarkdownFrontMatter(content, { source = '<markdown>' } = {}) {
  return parseMarkdownFrontMatter(normalizeTopLevelSequenceFrontMatter(content, source), { source });
}
const PRODUCTION_RELEASE_DECISIONS = new Set(['ready-for-cms-draft', 'published']);
const SYNTHETIC_RELEASE_DECISION = 'blocked';
const INDEXING_INTENTS = new Set(['index', 'noindex', 'index-after-production-evidence-gates']);
const PRODUCTION_OPERATION_MODES = new Set(['dry-run', 'draft', 'publish', 'update']);
const SYNTHETIC_OPERATION_MODE = 'not-run';
const CONTENT_PURPOSES = new Set(['buyer-article', 'qa-format-lab']);
const FACT_STATUSES = new Set(['confirmed', 'inferred', 'missing', 'conflicting', 'expired']);
const DECISION_STAGES = new Set(['learn', 'compare', 'validate', 'buy', 'troubleshoot']);
const STAGE_INTAKE_CONTRACTS = new Set(['none', 'troubleshoot-support', 'compare-handoff', 'validate-technical', 'buy-commercial']);
const STAGE_DEFAULT_INTAKE_CONTRACT = new Map([
  ['learn', 'none'],
  ['validate', 'validate-technical'],
  ['buy', 'buy-commercial'],
]);
const SECOND_ROUND_RELATIONSHIP_MODES = new Set(['new', 'refines']);
const CONTENT_ACTIONS = new Set(['create', 'update', 'merge', 'redirect', 'do-not-write']);
const CANNIBALIZATION_STATUSES = new Set(['clear', 'resolved', 'unresolved']);
const INTERNAL_LINK_ROLES = new Set(['hub', 'product', 'solution', 'educational', 'comparison', 'diagnostic', 'support', 'technical-review', 'conversion', 'commercial']);
const PRODUCT_LINK_EVIDENCE_LEVELS = new Set(['none', 'family-level', 'sku-level']);
const VISUAL_DECISION_ASSET_TYPES = new Set(['diagram', 'decision-tree', 'decision-table', 'worksheet', 'annotated-product', 'process-flow']);
const VISUAL_DECISION_ASSET_STATUSES = new Set(['required', 'optional', 'not-applicable']);
const BUYER_VISIBLE_INTERNAL_CONTROL_PATTERN = /\b(?:needs[ _-]?follow[ _-]?up|first[ _-]?round[ _-]?complete|engineering[ _-]?review[ _-]?ready|technical[ _-]?qualified|commercial[ _-]?qualification[ _-]?required|sales[ _-]?accepted|fatal[ _-]?gate|block[ _-]?for[ _-]?production|soft[ _-]?cta|final[ _-]?cta|stage[ _-]?intake[ _-]?contract|product[ _-]?link[ _-]?evidence[ _-]?level|synthetic(?:[ _-]?fixture)?|reference[ _-]?parity|network[ _-]?reachability|target[ _-]?page[ _-]?buyer[ _-]?task[ _-]?acceptance|task[ _-]?acceptance|capability[ _-]?acceptance)\b|`(?:canonical|synthetic)`/i;

const PRODUCTION_AXIS_EVIDENCE_KINDS = new Map([
  ['internal_link_reference', 'internal-link-reference'],
  ['internal_link_reachability', 'internal-link-reachability'],
  ['internal_link_capability', 'internal-link-capability'],
  ['cta_reference', 'cta-reference'],
  ['cta_reachability', 'cta-reachability'],
  ['cta_capability', 'cta-capability'],
]);
const PRODUCTION_SEARCH_EVIDENCE_KINDS = new Map([
  ['query_evidence_refs', 'query-evidence'],
  ['buyer_task_evidence_refs', 'buyer-task'],
  ['search_demand_evidence_refs', 'search-demand'],
  ['serp_format_evidence_refs', 'serp-format'],
  ['serp_gap_refs', 'serp-gap'],
  ['inventory_zero_result_evidence_refs', 'inventory-zero-result'],
]);
const REQUIRED_STRUCTURED_EVIDENCE_FIELDS = [
  'check_id', 'target_url', 'target_role', 'target_task', 'observed_at', 'method',
  'observed_result', 'artifact_digest', 'producer', 'producer_id',
  'independent_reviewer', 'independent_reviewer_id',
];
const STRUCTURED_EVIDENCE_FIELDS = new Map([
  ['checkid', 'check_id'],
  ['targeturl', 'target_url'],
  ['targetrole', 'target_role'],
  ['targettask', 'target_task'],
  ['accountableowner', 'accountable_owner'],
  ['policycontractid', 'policy_contract_id'],
  ['policyversion', 'policy_version'],
  ['policydigest', 'policy_digest'],
  ['policyartifactref', 'policy_artifact_ref'],
  ['policyartifactdigest', 'policy_artifact_digest'],
  ['ctamode', 'cta_mode'],
  ['datapurpose', 'data_purpose'],
  ['retentionperiod', 'retention_period'],
  ['deletionpath', 'deletion_path'],
  ['policyeffectiveat', 'policy_effective_at'],
  ['policycheckedat', 'policy_checked_at'],
  ['observedat', 'observed_at'],
  ['method', 'method'],
  ['process', 'rejected_alias_process'],
  ['observedresult', 'observed_result'],
  ['capabilityacceptance', 'capability_acceptance'],
  ['acceptancecriteria', 'acceptance_criteria'],
  ['viewportwidth', 'rejected_alias_viewport_width'],
  ['viewportwidthpx', 'viewport_width_px'],
  ['task', 'rejected_alias_task'],
  ['owner', 'rejected_alias_owner'],
  ['rendertarget', 'render_target'],
  ['readabilityresult', 'readability_result'],
  ['screenshotortraceref', 'screenshot_or_trace_ref'],
  ['artifactref', 'artifact_ref'],
  ['artifactdigest', 'artifact_digest'],
  ['producer', 'producer'],
  ['producerid', 'producer_id'],
  ['independentreviewer', 'independent_reviewer'],
  ['independentreviewerid', 'independent_reviewer_id'],
  ['observableoutput', 'observable_output'],
]);

const STABLE_ACTOR_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{5,127}$/;
const SNAPSHOT_PAYLOAD_FIELDS = new Map([
  ['search-demand', new Map([['query_set', 'string-array'], ['metric_type', 'string'], ['observation_window', 'string']])],
  ['serp-format', new Map([['query_set', 'string-array'], ['market', 'string'], ['language', 'string'], ['device', 'string'], ['result_types', 'string-array']])],
  ['market-comparison', new Map([
    ['query_set', 'string-array'], ['market', 'string'], ['language', 'string'], ['device', 'string'], ['checked_at', 'string'],
    ['comparison_corpus_ids', 'string-array'], ['comparison_corpus_rows', 'string-array'], ['difference_dimensions', 'string-array'],
    ['accepted_information_gain', 'string'], ['boundary', 'string'],
  ])],
  ['content-inventory', new Map([['query', 'string'], ['candidate_count', 'nonnegative-integer'], ['retrieval_dimensions', 'string-array']])],
]);
const SNAPSHOT_ENVELOPE_FIELDS = new Set([
  'schema_version', 'artifact_kind', 'evidence_scope', 'captured_at', 'subject_id', 'scope_id',
  'capture_method', 'producer_id', 'independent_reviewer_id', 'payload',
]);

function requireStableActorId(value, source, field, problems) {
  const normalized = String(value || '').trim();
  if (!STABLE_ACTOR_ID_PATTERN.test(normalized) || PLACEHOLDER_PATTERN.test(normalized) || /\s/u.test(normalized)) {
    fail(problems, `${source} ${field} must be a stable non-placeholder actor ID without display-name spaces`);
  }
  return normalized;
}

function exactSnapshotArrayFromEvidence(value) {
  const raw = String(value || '').trim();
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) return parsed.map((item) => String(item).trim());
  } catch {}
  return raw.split(';').map((item) => item.trim()).filter(Boolean);
}

function validateSnapshotPayload({ artifact, expectedKind, fields, source, axis, ref, expectedScope, problems }) {
  const allowed = SNAPSHOT_PAYLOAD_FIELDS.get(expectedKind);
  if (!allowed) return;
  if (!artifact.payload || typeof artifact.payload !== 'object' || Array.isArray(artifact.payload)) {
    fail(problems, `${source} production ${axis} snapshot artifact requires one non-empty object payload`);
    return;
  }
  const keys = Object.keys(artifact.payload).sort();
  const expectedKeys = [...allowed.keys()].sort();
  if (keys.length !== expectedKeys.length || expectedKeys.some((key, index) => key !== keys[index])) {
    fail(problems, `${source} production ${axis} snapshot payload must use the closed ${expectedKind} schema: ${expectedKeys.join(', ')}`);
  }
  for (const [key, type] of allowed) {
    const value = artifact.payload[key];
    if (type === 'string' && (typeof value !== 'string' || !value.trim())) fail(problems, `${source} production ${axis} snapshot payload.${key} must be a non-empty string`);
    if (type === 'string-array' && (!Array.isArray(value) || !value.length || value.some((item) => typeof item !== 'string' || !item.trim()))) fail(problems, `${source} production ${axis} snapshot payload.${key} must be a non-empty string array`);
    if (type === 'nonnegative-integer' && (!Number.isInteger(value) || value < 0)) fail(problems, `${source} production ${axis} snapshot payload.${key} must be a non-negative integer`);
  }
  const exactScalar = (evidenceKey, payloadKey = evidenceKey) => {
    if (!fields.has(evidenceKey)) return;
    if (normalizeText(fields.get(evidenceKey)) !== normalizeText(String(artifact.payload[payloadKey] ?? ''))) fail(problems, `${source} production ${axis} evidence ${ref} ${evidenceKey} must match snapshot payload.${payloadKey}`);
  };
  const exactArray = (evidenceKey, payloadKey = evidenceKey) => {
    if (!fields.has(evidenceKey)) return;
    const payloadValue = artifact.payload[payloadKey];
    if (!Array.isArray(payloadValue)) return;
    const evidenceValues = exactSnapshotArrayFromEvidence(fields.get(evidenceKey)).map(normalizeText);
    const payloadValues = payloadValue.map((item) => normalizeText(String(item)));
    if (evidenceValues.length !== payloadValues.length || evidenceValues.some((item, index) => item !== payloadValues[index])) fail(problems, `${source} production ${axis} evidence ${ref} ${evidenceKey} must exactly match snapshot payload.${payloadKey}`);
  };
  if (expectedKind === 'search-demand') { exactArray('exact_query_set', 'query_set'); exactScalar('metric_type'); exactScalar('observation_window'); }
  if (expectedKind === 'serp-format') { exactArray('query_set'); exactScalar('market'); exactScalar('language'); exactScalar('device'); exactArray('result_types'); }
  if (expectedKind === 'market-comparison') {
    const requiredProjectionFields = ['query_set', 'market', 'language', 'device', 'checked_at', 'comparison_corpus_ids', 'comparison_corpus_rows', 'difference_dimensions', 'accepted_information_gain', 'boundary'];
    for (const key of requiredProjectionFields) if (!fields.has(key) || !String(fields.get(key) || '').trim()) fail(problems, `${source} production ${axis} evidence ${ref} requires exact non-empty ${key} projection from the market-comparison snapshot`);
    for (const key of ['query_set', 'comparison_corpus_ids', 'comparison_corpus_rows', 'difference_dimensions']) exactArray(key);
    for (const key of ['market', 'language', 'device', 'checked_at', 'accepted_information_gain', 'boundary']) exactScalar(key);
    const payload = artifact.payload;
    const ids = payload.comparison_corpus_ids || [];
    const rows = payload.comparison_corpus_rows || [];
    const seenIds = new Set();
    const rowIds = [];
    for (const [index, row] of rows.entries()) {
      const parts = String(row).split('|').map((part) => part.trim());
      if (parts.length !== 4 || parts.some((part) => !part)) {
        fail(problems, `${source} production ${axis} snapshot payload.comparison_corpus_rows row ${index + 1} must use stable-id|https-url|content-family|existing-topic-or-decision-artifact`);
        continue;
      }
      const [id, url, family, artifactDescription] = parts;
      if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$/.test(id) || PLACEHOLDER_PATTERN.test(id)) fail(problems, `${source} production ${axis} snapshot comparison corpus row ${index + 1} requires a stable non-placeholder ID`);
      if (seenIds.has(id)) fail(problems, `${source} production ${axis} snapshot comparison corpus must not duplicate stable ID ${id}`);
      seenIds.add(id);
      rowIds.push(id);
      if (!/^https:\/\/[^\s]+$/i.test(url)) fail(problems, `${source} production ${axis} snapshot comparison corpus row ${index + 1} requires one stable HTTPS URL`);
      if (PLACEHOLDER_PATTERN.test(family) || PLACEHOLDER_PATTERN.test(artifactDescription) || normalizeText(artifactDescription).split(' ').length < 3) {
        fail(problems, `${source} production ${axis} snapshot comparison corpus row ${index + 1} requires a concrete content family and existing topic or decision artifact`);
      }
    }
    if (!sameNormalizedSet(ids, rowIds) || ids.length !== rowIds.length) fail(problems, `${source} production ${axis} snapshot comparison_corpus_ids must exactly equal row IDs with no missing, extra, or duplicate ID`);
    if (new Set((payload.difference_dimensions || []).map(normalizeText)).size !== (payload.difference_dimensions || []).length
      || (payload.difference_dimensions || []).some((item) => PLACEHOLDER_PATTERN.test(item) || normalizeText(item).split(' ').length < 2)) {
      fail(problems, `${source} production ${axis} snapshot difference_dimensions must be unique, concrete, and non-placeholder`);
    }
    for (const key of ['accepted_information_gain', 'boundary']) if (PLACEHOLDER_PATTERN.test(payload[key]) || normalizeText(payload[key]).split(' ').length < 5) {
      fail(problems, `${source} production ${axis} snapshot payload.${key} must be concrete and bounded rather than self-reported or generic`);
    }
    if (expectedScope) {
      if (!sameNormalizedSet(payload.query_set || [], expectedScope.querySet || []) || (payload.query_set || []).length !== (expectedScope.querySet || []).length) fail(problems, `${source} production ${axis} snapshot query_set must exactly match the article primary and supporting query set`);
      for (const key of ['market', 'language', 'device']) if (payload[key] !== expectedScope[key]) fail(problems, `${source} production ${axis} snapshot payload.${key} must exactly match the article evidence scope`);
    }
    requireFreshIsoDate(payload.checked_at, source, `${axis} snapshot payload.checked_at`, problems);
  }
  if (expectedKind === 'content-inventory') {
    exactScalar('query'); exactScalar('candidate_count'); exactArray('retrieval_dimensions');
  }
}

const TRANSACTIONAL_QUERY_PATTERN = /\b(?:buy|cost(?:\s+estimate)?|estimate|proposal|request\s+for\s+proposal|rfp|price|pricing|quote|quotation|rfq|order|wholesale|supplier(?:s| selection)?|vendor(?:s| shortlist)?|source\s+vendors?|solicit\s+bids?|tender|bid\s+award|moq|lead[ _-]?time|delivery|availability|procure(?:ment)?|purchase|contract award)\b/i;
const COMMERCIAL_TASK_PATTERN = /\b(?:cost(?:\s+estimate)?|estimate|proposal|request\s+for\s+proposal|rfp|price|pricing|quote|quotation|rfq|order|purchase|procure(?:ment)?|source\s+vendors?|solicit\s+bids?|tender|bid\s+award|vendor\s+shortlist|supplier selection|commercial|moq|lead[ _-]?time|delivery|availability|contract|award|budget)\b/i;
const TECHNICAL_TASK_PATTERN = /\b(?:engineer|engineering|technical|specification|interface|load|duty|thermal|electrical|mechanical|controller|validation|test|evidence|sample|candidate|compatibility)\w*\b/i;
const COMMERCIAL_OWNER_PATTERN = /\b(?:sales|commercial|account(?:\s+executive|\s+manager)?|business development|revenue|quotation|rfq|procurement liaison)\b/i;
const TECHNICAL_OWNER_PATTERN = /\b(?:engineer|engineering|technical|application(?:s)?|quality|validation|test)\b/i;
const EXPLICIT_COMMERCIAL_INTENT_PATTERN = /\b(?:cost(?:\s+estimate)?|estimate|proposal|request\s+for\s+proposal|rfp|rfq|request(?:ing)? (?:a )?(?:quote|quotation)|price|pricing|moq|lead[ _-]?time|delivery|sample order|purchase order|supplier selection|supplier award|contract award|source\s+vendors?|solicit\s+bids?|tender|bid\s+award|vendor\s+shortlist|procure(?:ment)?|buy|purchase|order)\b/i;
const EXPLICIT_NO_FIT_PATTERN = /\b(?:incompatib(?:le|ility)|unsupported(?: scope)?|outside (?:the )?(?:supported )?(?:envelope|boundary|scope)|out of (?:the )?(?:supported )?(?:envelope|boundary|scope)|fails? (?:a )?(?:hard|mandatory) (?:limit|requirement)|cannot meet (?:a )?(?:hard|mandatory) (?:limit|requirement))\b/i;
const QUALIFICATION_PROGRESS_STATES = new Set(['first-round-complete', 'engineering-review-ready', 'technical-qualified', 'commercial-qualification-required', 'sales-accepted', 'needs-follow-up', 'disqualified']);
const STAGE_CONTRACTS = new Map([
  ['learn', { cta: /^(?:education|self-check)$/, links: new Set(['educational', 'hub']), sales: new Set(['not-applicable', 'not-applicable-without-commercial-intent']) }],
  ['troubleshoot', { cta: /^(?:diagnosis-support|technical-support|self-check)$/, links: new Set(['diagnostic', 'support', 'solution', 'educational', 'technical-review', 'product']), sales: new Set(['not-applicable', 'not-applicable-without-commercial-intent', 'optional']) }],
  ['compare', { cta: /^(?:comparison|self-check|commercial-qualification)$/, links: new Set(['comparison', 'solution', 'product', 'hub']), sales: new Set(['not-applicable', 'not-applicable-without-commercial-intent', 'optional', 'required']) }],
  ['validate', { cta: /^(?:bounded-engineering-review|technical-review|self-check)$/, links: new Set(['technical-review', 'solution', 'product', 'educational']), sales: new Set(['not-applicable', 'not-applicable-without-commercial-intent']) }],
  ['buy', { cta: /^(?:rfq|commercial-qualification)$/, links: new Set(['conversion', 'product', 'solution', 'commercial']), sales: new Set(['required']) }],
]);
const EVIDENCE_SCOPES = new Set(['synthetic-fixture', 'production']);
const GENERIC_ANCHORS = new Set([
  'click here', 'learn more', 'read more', 'more', 'view details', 'details', 'see more',
  'go here', 'go here now', 'visit page', 'open page', 'check it out', 'continue',
  'explore', 'view', 'discover', 'learn about', 'see products', 'browse solutions',
]);
const PROMOTIONAL_NAVIGATION_ANCHOR_PATTERN = /^(?:explore|view|discover|learn about|see|browse|check out|visit|open)(?:\s+(?:our|the|more|all|available))?\s+(?:products?|solutions?|offerings?|portfolio|catalog|range|options?)\b/i;
const CANONICAL_BUYER_ROLES = new Map([['engineer', 'Engineer'], ['quality', 'Quality'], ['procurement', 'Procurement'], ['management', 'Management']]);
const CTA_INPUT_COLLECTION_MODES = new Set(['complete', 'progressive-profiling']);
const INTERNAL_LINK_PLACEMENTS = new Set(['opening', 'decision-path', 'evidence', 'comparison', 'faq', 'cta']);
const CANNIBALIZATION_ACTIONS = new Set([...CONTENT_ACTIONS, 'delegate']);
const ROLE_SEMANTIC_PATTERNS = new Map([
  ['Engineer', /\b(?:engineer|engineering|system|technical|interface|load|duty|electrical|mechanical|controller|specification|assumption|input|readiness|candidate)\w*\b/i],
  ['Quality', /\b(?:quality|evidence|test|validation|acceptance|threshold|defect|compliance|inspection|sample|duty)\w*\b/i],
  ['Procurement', /\b(?:procurement|purchas|supplier|quotation|quote|rfq|price|cost|moq|lead[ _-]?time|commercial|comparison)\w*\b/i],
  ['Management', /\b(?:management|approval|risk|budget|spend|investment|uncertainty|roi|decision|portfolio|business)\w*\b/i],
]);
const NO_FIT_PATTERN = /\b(?:no[ -]?fit|not (?:a )?fit|unfit|unsuitable|incompatib(?:le|ility)|unsupported|outside (?:the )?(?:supported )?(?:envelope|boundary|scope)|out of (?:the )?(?:supported )?(?:envelope|boundary|scope)|reject|stop|block|cannot|must not|do not|exclude|disqualif|fail(?:s|ed|ure)?|unresolved)\w*\b/i;
const NAVIGATION_CANDIDATE_PATTERN = /\b(?:catalog(?:ue)?|overview|finder|selector|directory|collection|index|navigation|landing page|guide page|category hub|resource hub|product hub|hub(?![- ]?motor)\s+page)\b/i;
const LIFECYCLE_EVIDENCE_KINDS = new Map([
  ['authorization', /\b(?:authorization|approval|approved|actor|operation|scope)\w*\b/i],
  ['cms-mutation', /\b(?:cms|mutation|write|publish|saved|article|record)\w*\b/i],
  ['backend-readback', /\b(?:backend|readback|cms|record|saved|persisted)\w*\b/i],
  ['editor-reopen', /\b(?:editor|reopen|reload|saved|persisted|article)\w*\b/i],
  ['anonymous-frontend', /\b(?:anonymous|logged[- ]?out|public|frontend|page|url|render)\w*\b/i],
  ['desktop-acceptance', /\b(?:desktop|viewport|frontend|render|readability|acceptance)\w*\b/i],
  ['mobile-acceptance', /\b(?:mobile|320px|viewport|frontend|render|readability|acceptance)\w*\b/i],
  ['image-decode', /\b(?:image|decode|fetch|load|render|alt|asset)\w*\b/i],
]);
const PLACEHOLDER_PATTERN = /^(?:a|b|c|na|n\/?a|none|unknown|tbd|todo|test|sample|placeholder|replace(?:-|\b)|select-before-|not-set|lorem(?: ipsum)?|xxx+)$/i;
const ENUMERATION_VOCABULARIES = [
  ['learn', 'compare', 'validate', 'buy', 'troubleshoot'],
  ['informational', 'commercial', 'transactional', 'navigational'],
];
const BUYER_TASK_FAMILY_PATTERNS = new Map([
  ['learn', /\b(?:learn|understand|explain|definition|terminology|what is|how does)\b/i],
  ['compare', /\b(?:compare|comparison|select|selection|shortlist|evaluate|choose|candidate direction|input contract|decision sheet)\w*\b/i],
  ['validate', /\b(?:validate|validation|verify|verification|test|testing|acceptance|approve sample|sample approval)\w*\b/i],
  ['buy', /\b(?:buy|purchase|procurement|rfq|quotation|quote request|order|commercial inquiry)\w*\b/i],
  ['troubleshoot', /\b(?:troubleshoot|diagnose|diagnosis|fix|repair|failure analysis|root cause)\w*\b/i],
]);
const GENERIC_PAIN_ONLY_PATTERN = /^(?:general\s+)?(?:(?:improve|increase|enhance|optimi[sz]e|reduce|lower|save|ensure|support|address)\s+)?(?:efficien(?:cy|t)|productiv(?:ity|e)|perform(?:ance|ant)|qualit(?:y|ative)|costs?|time|communication|collaboration|coordination|visibility|operations?|business|workflow|process)(?:\s+(?:issues?|problems?|challenges?|concerns?|risks?|difficult(?:y|ies)))?$/i;
const GENERIC_PAIN_TERMS_PATTERN = /\b(?:improve|increase|enhance|optimi[sz]e|reduce|lower|save|ensure|support|address|efficient|efficiency|productivity|performance|quality|cost|time|communication|collaboration|coordination|visibility|operations?|business|workflow|process|challenge|difficulty|concern|confidence)\w*\b/gi;
const PAIN_ROLE_PATTERNS = new Map([
  ['pain_trigger', /\b(?:when|after|before|during|once|must|needs?(?:\s+to|\s+an?\b)|is asked to|receives?|orders?|requests?|starts?|changes?|uses?)\b/i],
  ['surface_problem', /\b(?:cannot|can't|does not|do not|missing|mismatch|misleading|obscures?|inconsistent|incomplete|unclear|unknown|hidden|conflict|fails?|doesn't reveal|not comparable|appear(?:s)? directly comparable|looks? equivalent|seems? equivalent|different assumptions?)\b/i],
  ['operational_friction', /\b(?:rework|repeat|retest|chase|delay|wait|manual|compare|reconcile|handoff|cycle|review|back[- ]?and[- ]?forth|cannot|can't|trust|shortlist|quotation|quote)\w*\b/i],
  ['business_consequence', /\b(?:cost|budget|schedule|lead[ _-]?time|sample|order|approval|launch|waste|risk|delay|rework|validation cycle|supplier review|miss|force|lose)\w*\b/i],
  ['desired_decision', /\b(?:decide|define|choose|select|shortlist|compare|approve|reject|request|stop|qualify|complete|hold)\w*\b/i],
]);
const CONCRETE_BUYER_CONTEXT_PATTERN = /\b(?:buyer|engineer|engineering|quality|procurement|management|supplier|quotation|quote|rfq|sample|product|model|candidate|motor|controller|vehicle|route|grade|load|duty|thermal|interface|voltage|current|market|evidence|test|input|assumption|budget|schedule)\w*\b/i;
const UNSUPPORTED_OUTCOME_ACTION_PATTERN = /\b(?:guarantee|ensure|establish|prove|increase|boost|improve|raise|grow|double|triple|drive|generate|deliver|create|produce|secure|win|lift|yield|bring|gain|achieve)\w*\b/i;
const UNSUPPORTED_OUTCOME_OBJECT_PATTERN = /\b(?:rank(?:ing)?s?|first[ -]page|top \d+|number one|#1|qualified inquir(?:y|ies)|leads?|conversion(?: rate)?s?|revenue|sales|sales pipeline|ready[- ]to[- ]buy prospects?|paying customers?|customer acquisition)\b/i;
const UNSUPPORTED_OUTCOME_CLAIM_PATTERNS = [
  /\b(?:will|shall|always|certain(?:ly)? to|proven to)\b.{0,100}\b(?:rank(?:ing)?s?|first[ -]page|top \d+|qualified inquir(?:y|ies)|leads?|conversion(?: rate)?s?|revenue|sales)\b/i,
  /\b(?:guarantee|ensure|establish|prove|increase|boost|improve|raise|grow|double|triple|drive|generate|deliver|create|produce|secure|win|lift|yield|bring|gain|achieve)\w*\b.{0,100}\b(?:rank(?:ing)?s?|first[ -]page|top \d+|number one|#1|qualified inquir(?:y|ies)|leads?|conversion(?: rate)?s?|revenue|sales|sales pipeline|ready[- ]to[- ]buy prospects?|paying customers?|customer acquisition)\b/i,
  /\bfills?\s+the\s+sales\s+pipeline\s+with\s+ready[- ]to[- ]buy\s+prospects?\b/i,
  /\bturns?\s+more\s+visitors?\s+into\s+paying\s+customers?\b/i,
  /\b(?:accelerates?|improves?|drives?|guarantees?|ensures?|delivers?)\s+customer\s+acquisition\b/i,
  /\brank(?:s|ed|ing)?\b.{0,60}\b(?:first[ -]page|number one|#1|top \d+)\b/i,
];
const DIRECT_ANSWER_JUDGMENT_PATTERN = /\b(?:must|should|ought to|need(?:s)? to|is required to|are required to|cannot|can not|do not|does not|requires?|choose|select|compare|define|complete|reject|validate|diagnose|troubleshoot|hold|stop|assemble|build|provide|submit|route)\b/i;
const NON_PRODUCT_CANDIDATE_PATTERN = /\b(?:questions?|checklists?|review topics?|discussion topics?|criteria list|worksheet|reading list|audit prompts?|research prompts?)\b/i;
const PRODUCT_OR_STOP_CANDIDATE_PATTERN = /\b(?:product|model|configuration|motor|controller|system|solution|candidate|option|direction|architecture|platform|component|stop|hold|reject|no[ -]?fit|do not proceed)\w*\b/i;
const EXPLICIT_HANDOFF_PATTERN = /\b(?:handoff|hand off|delegate|route from|route .* to|owner transfer|escalate)\w*\b/i;
const SCORE_FIELDS = new Map([
  ['score_search_intent', 15],
  ['score_opening_hook', 15],
  ['score_evidence_claims', 20],
  ['score_buyer_decision', 15],
  ['score_hierarchy', 10],
  ['score_decision_tool', 10],
  ['score_cta', 10],
  ['score_internal_links', 5],
]);
const ALLINCMS_FORMATS = new Set([
  ...ALLINCMS_ARTICLE_FORMAT_SUPPORT.verified,
  ...ALLINCMS_ARTICLE_FORMAT_SUPPORT.baselineAlsoVerified,
]);
const ALLINCMS_UNSUPPORTED = new Set(
  ALLINCMS_ARTICLE_FORMAT_SUPPORT.unsupportedCurrentShape.map((item) => item.key),
);

function fail(problems, message) {
  problems.push(message);
}

function rejectDeprecatedArticlePackageFields(record, problems) {
  const normalizedDeprecated = new Map([...DEPRECATED_ARTICLE_PACKAGE_FIELDS].map(([field, replacement]) => [normalizeFieldIdentifier(field), { field, replacement }]));
  for (const field of Object.keys(record.attributes)) {
    const deprecated = normalizedDeprecated.get(normalizeFieldIdentifier(field));
    if (deprecated) {
      fail(problems, `${record.source} field ${field} is a normalized deprecated alias of ${deprecated.field} and is rejected; use ${deprecated.replacement}`);
    }
  }
}

function requireNumber(attributes, field, source, problems) {
  const value = attributes[field];
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    fail(problems, `${source} field ${field} must be a finite number`);
    return Number.NaN;
  }
  return value;
}

function validatePackageRecordPath(filePath, expectedType, packageRoot, realPackageRoot, problems) {
  const source = resolve(filePath);
  if (!isWithinRoot(packageRoot, source)) {
    fail(problems, `${source} ${expectedType} path must remain inside package root ${packageRoot}`);
    return false;
  }
  if (!existsSync(source)) {
    fail(problems, `${source} ${expectedType} record does not exist`);
    return false;
  }
  let stats;
  try { stats = lstatSync(source); }
  catch (error) { fail(problems, `${source} ${expectedType} record cannot be inspected: ${error.message}`); return false; }
  if (stats.isSymbolicLink() || !stats.isFile()) {
    fail(problems, `${source} ${expectedType} record must be a regular non-symlink file`);
    return false;
  }
  let realSource;
  try { realSource = realpathSync(source); }
  catch (error) { fail(problems, `${source} ${expectedType} record realpath cannot be resolved: ${error.message}`); return false; }
  if (!isWithinRoot(realPackageRoot, realSource)) {
    fail(problems, `${source} ${expectedType} record resolves outside package root ${realPackageRoot}`);
    return false;
  }
  return true;
}

function scanRawTopLevelFrontMatterIdentifiers(content, source, problems) {
  const normalized = content.replace(/\r\n?/g, '\n');
  if (!normalized.startsWith('---\n')) return;
  const lines = normalized.split('\n');
  const closing = lines.indexOf('---', 1);
  if (closing < 0) return;
  const normalizedDeprecated = new Map([...DEPRECATED_ARTICLE_PACKAGE_FIELDS].map(([field, replacement]) => [normalizeFieldIdentifier(field), { field, replacement }]));
  const observed = new Map();
  for (let index = 1; index < closing; index += 1) {
    const match = /^([^\s#][^:]*?):(?:\s|$)/u.exec(lines[index]);
    if (!match) continue;
    const field = match[1].trim();
    const normalizedField = normalizeFieldIdentifier(field);
    if (!normalizedField) continue;
    const previous = observed.get(normalizedField);
    if (previous && previous.field !== field && (!previous.parserSafe || !/^[A-Za-z_][A-Za-z0-9_-]*$/.test(field))) {
      fail(problems, `${source} contains confusable or separator/case-equivalent fields ${previous.field} and ${field}`);
    }
    const parserSafe = /^[A-Za-z_][A-Za-z0-9_-]*$/.test(field);
    observed.set(normalizedField, { field, parserSafe });
    if (parserSafe) continue;
    const deprecated = normalizedDeprecated.get(normalizedField);
    if (deprecated) {
      fail(problems, `${source}:${index + 1} field ${field} is a normalized deprecated alias of ${deprecated.field} and is rejected; use ${deprecated.replacement}`);
    }
  }
}

function readRecord(filePath, expectedType, problems, packageRoot, realPackageRoot) {
  const source = resolve(filePath);
  if (!validatePackageRecordPath(source, expectedType, packageRoot, realPackageRoot, problems)) {
    return { source, recordRole: expectedType, attributes: Object.create(null), body: '' };
  }
  const content = readFileSync(source, 'utf8');
  scanRawTopLevelFrontMatterIdentifiers(content, source, problems);
  let parsed;
  try {
    parsed = parseArticleMarkdownFrontMatter(content, { source });
  } catch (error) {
    fail(problems, error.message);
    return { source, recordRole: expectedType, attributes: Object.create(null), body: '' };
  }
  let recordType = '';
  try { recordType = requireStringField(parsed.attributes, 'record_type', { source }); }
  catch (error) { fail(problems, error.message); }
  const recordTypeAliases = new Map([
    ['article-quality-review', new Set(['article-quality-review', 'article-review'])],
    ['article-publish-record', new Set(['article-publish-record', 'publish-record'])],
  ]);
  const allowedRecordTypes = recordTypeAliases.get(expectedType) || new Set([expectedType]);
  if (recordType && !allowedRecordTypes.has(recordType)) {
    fail(problems, `${source} record_type must be ${[...allowedRecordTypes].join(' or ')}; received ${recordType}`);
  }
  return { source, recordRole: expectedType, ...parsed };
}

function recordLabel(record) {
  return `${record.recordRole || 'record'} (${record.source})`;
}

function string(record, field, problems) {
  try { return requireStringField(record.attributes, field, { source: record.source }); }
  catch (error) { fail(problems, error.message); return ''; }
}

function strings(record, field, problems, { allowEmpty = false } = {}) {
  try { return requireStringArrayField(record.attributes, field, { source: record.source, allowEmpty }); }
  catch (error) { fail(problems, error.message); return []; }
}

function checkHeadingStructure(draft, problems) {
  const headings = [...draft.body.matchAll(/^(#{1,6})\s+\S.*$/gm)].map((match) => match[1].length);
  const h1Count = headings.filter((level) => level === 1).length;
  const h2Count = headings.filter((level) => level === 2).length;
  if (h1Count !== 0) {
    fail(problems, `${draft.source} AllinCMS article body must not contain H1; the page H1 comes from the independent page_h1 page-shell field`);
  }
  if (h2Count < 1) fail(problems, `${draft.source} must contain at least one H2 section; received ${h2Count}`);
  if (headings.length > 0 && headings[0] !== 2) {
    fail(problems, `${draft.source} first body heading must be H2; received H${headings[0]}`);
  }
  for (let index = 1; index < headings.length; index += 1) {
    if (headings[index] - headings[index - 1] > 1) {
      fail(problems, `${draft.source} heading hierarchy skips from H${headings[index - 1]} to H${headings[index]}`);
      break;
    }
  }
}

function requireAbsoluteHttpsUrl(value, source, field, problems) {
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || !url.hostname) throw new Error('not absolute HTTPS');
  } catch {
    fail(problems, `${source} field ${field} must be an absolute HTTPS URL for a published package`);
  }
}

function requireProductionPublicHttpsUrl(value, source, field, problems) {
  try {
    const url = new URL(value);
    const hostname = url.hostname.toLowerCase().replace(/\.$/, '');
    if (url.protocol !== 'https:' || !hostname) throw new Error('not absolute HTTPS');
    if (url.username || url.password) throw new Error('credentials are forbidden');
    if (url.port && url.port !== '443') throw new Error('non-default port is forbidden');
    if (hostname === 'localhost' || hostname.endsWith('.localhost')) throw new Error('localhost is forbidden');
    if (/^(?:\d{1,3}\.){3}\d{1,3}$/.test(hostname) || hostname.includes(':')) throw new Error('IP literals are forbidden');
    if (/\.(?:local|internal|test|invalid|example)$/.test(hostname)) throw new Error('reserved private or test suffix is forbidden');
    if (/^(?:www\.)?example\.(?:com|net|org)$/.test(hostname)) throw new Error('reserved example host is forbidden');
    if (/^(?:placeholder|dummy|fake|test)(?:[.-]|$)/.test(hostname) || /(?:^|[.-])placeholder(?:[.-]|$)/.test(hostname)) throw new Error('placeholder host is forbidden');
  } catch (error) {
    fail(problems, `${source} field ${field} must be a public absolute HTTPS URL without credentials, IP literals, private/test suffixes, placeholder hosts, or non-default ports: ${error.message}`);
  }
}

function requireIsoDate(value, source, field, problems) {
  const match = /^(\d{4})-(\d{2})-(\d{2})(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2}))?$/.exec(value);
  const year = Number(match?.[1]);
  const month = Number(match?.[2]);
  const day = Number(match?.[3]);
  const calendarDate = match ? new Date(Date.UTC(year, month - 1, day)) : null;
  const validCalendarDate = calendarDate
    && calendarDate.getUTCFullYear() === year
    && calendarDate.getUTCMonth() === month - 1
    && calendarDate.getUTCDate() === day;
  const timestamp = Date.parse(value);
  if (!match || !validCalendarDate || Number.isNaN(timestamp)) {
    fail(problems, `${source} field ${field} must be an ISO date or timestamp`);
  } else if (timestamp > Date.now() + (5 * 60 * 1000)) {
    fail(problems, `${source} field ${field} must not be in the future`);
  }
}

function requireFreshIsoDate(value, source, field, problems, maxAgeDays = EVIDENCE_MAX_AGE_DAYS) {
  requireIsoDate(value, source, field, problems);
  const timestamp = Date.parse(value);
  if (Number.isFinite(timestamp) && timestamp <= Date.now() && Date.now() - timestamp > maxAgeDays * 24 * 60 * 60 * 1000) {
    fail(problems, `${source} field ${field} is stale; it must be no more than ${maxAgeDays} days old`);
  }
}

function requireDateNoLaterThan(value, ceilingValue, source, field, ceilingField, problems) {
  const timestamp = Date.parse(value);
  const ceilingTimestamp = Date.parse(ceilingValue);
  if (Number.isFinite(timestamp) && Number.isFinite(ceilingTimestamp) && timestamp > ceilingTimestamp) {
    fail(problems, `${source} field ${field} must not be later than ${ceilingField}`);
  }
}

function rejectTemplatePlaceholder(value, source, field, problems) {
  if (/^(?:replace-|select-before-|not-set$)/i.test(value)) {
    fail(problems, `${source} field ${field} still contains a template placeholder`);
  }
}

function rejectTemplatePlaceholders(values, source, field, problems) {
  for (const value of values) rejectTemplatePlaceholder(value, source, field, problems);
}

function stripSecurityIgnorables(value) {
  return String(value ?? '')
    .normalize('NFKC')
    .replace(/[\p{Cf}\p{Default_Ignorable_Code_Point}]/gu, '');
}

function securityCanonicalText(value) {
  const confusables = new Map([
    ['а', 'a'], ['А', 'A'], ['е', 'e'], ['Е', 'E'], ['і', 'i'], ['І', 'I'],
    ['о', 'o'], ['О', 'O'], ['р', 'p'], ['Р', 'P'], ['с', 'c'], ['С', 'C'],
    ['х', 'x'], ['Х', 'X'], ['у', 'y'], ['У', 'Y'], ['κ', 'k'], ['ο', 'o'], ['ι', 'i'], ['ո', 'n'],
    ['г', 'r'], ['Г', 'R'], ['ɑ', 'a'], ['Α', 'A'], ['Β', 'B'], ['Ε', 'E'], ['Ζ', 'Z'], ['Η', 'H'], ['Ι', 'I'], ['Κ', 'K'], ['Μ', 'M'], ['Ν', 'N'], ['Ο', 'O'], ['Ρ', 'P'], ['Τ', 'T'], ['Χ', 'X'],
  ]);
  return stripSecurityIgnorables(value)
    .replace(/[аАеЕіІоОрРсСхХуУгГκοɑΑΒΕΖΗΙΚΜΝΟΡΤΧ]/g, (character) => confusables.get(character) || character);
}

function unicodeScriptProfile(token) {
  return {
    latin: /\p{Script=Latin}/u.test(token),
    greek: /\p{Script=Greek}/u.test(token),
    cyrillic: /\p{Script=Cyrillic}/u.test(token),
    armenian: /\p{Script=Armenian}/u.test(token),
  };
}

function findMixedScriptTokens(value) {
  const tokens = stripSecurityIgnorables(value).match(/[\p{L}\p{M}\p{N}_-]+/gu) || [];
  return [...new Set(tokens.filter((token) => {
    const scripts = unicodeScriptProfile(token);
    return scripts.latin && (scripts.greek || scripts.cyrillic || scripts.armenian);
  }))];
}

function rejectMixedScriptValue(value, source, field, problems) {
  const mixed = findMixedScriptTokens(value);
  if (mixed.length) fail(problems, `${source} field ${field} contains mixed-script Latin plus Greek/Cyrillic/Armenian token(s): ${mixed.join(', ')}`);
}

function rejectMixedScriptPackage(records, draft, problems) {
  for (const record of records) {
    for (const [field, value] of Object.entries(record.attributes)) {
      if (typeof value === 'string') rejectMixedScriptValue(value, record.source, field, problems);
      else if (Array.isArray(value)) value.forEach((item, index) => rejectMixedScriptValue(item, record.source, `${field}[${index}]`, problems));
    }
  }
  rejectMixedScriptValue(draft.body, draft.source, 'body', problems);
}

function securityLexicalText(value) {
  return normalizeText(value)
    .replace(/(?<=[\p{L}\p{N}])[\p{P}\p{S}_]+(?=[\p{L}\p{N}])/gu, '')
    .replace(/[\s_-]+/g, ' ')
    .trim();
}

function commercialClassification(value) {
  const canonical = securityLexicalText(value);
  return {
    canonical,
    commercial: TRANSACTIONAL_QUERY_PATTERN.test(canonical) || EXPLICIT_COMMERCIAL_INTENT_PATTERN.test(canonical) || COMMERCIAL_TASK_PATTERN.test(canonical) || COMMERCIAL_TERMINAL_ACTION_PATTERN.test(canonical),
    terminal: COMMERCIAL_TERMINAL_ACTION_PATTERN.test(canonical),
  };
}

function normalizeFieldIdentifier(value) {
  return securityCanonicalText(value)
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '');
}

function normalizeText(value) {
  return securityCanonicalText(value).replace(/\s+/g, ' ').trim().toLowerCase();
}

function normalizeDecisionGateText(value) {
  return String(value ?? '')
    .normalize('NFKC')
    .replace(/[\p{Dash_Punctuation}\/_]+/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

function decisionGateClauses(value) {
  return String(value ?? '')
    .normalize('NFKC')
    .replace(/[\p{Dash_Punctuation}\/_]+/gu, ' ')
    .split(/(?:[.!?;。！？；]+|\n+|\s*,?\s*\b(?:but|however|although|yet|instead|then)\b\s*)/iu)
    .map((clause) => clause.replace(/\s+/g, ' ').trim().toLowerCase())
    .filter(Boolean);
}

function hasDecisionOutcomeLanguage(value) {
  const text = normalizeDecisionGateText(value);
  return /\b(?:candidate\s*,?\s*(?:or\s+)?(?:stop|terminate|reject|drop|end)|candidate\s+(?:decision|direction|recommendation)|advance\s*,?\s*(?:or\s+)?reject|approve\s*,?\s*(?:or\s+)?reject|go\s*,?\s*(?:or\s+)?no\s+go|(?:name|nominate|identify|select|advance|approve|recommend|return|give|provide)\b[^.!?;]{0,100}\b(?:a\s+)?candidate\b(?:[^.!?;]{0,80}\b(?:or|versus)\b[^.!?;]{0,40}\b(?:stop|reject|terminate|drop|end)\b)?|(?:recommend|select)(?:ation|ing)?\s*,?\s*(?:or\s+)?(?:stop|reject|terminate|drop|end))\b/i.test(text);
}

function decisionOutcomeIsExplicitlyDenied(clause) {
  const normalized = normalizeDecisionGateText(clause);
  return /\b(?:do\s+not|does\s+not|must\s+not|may\s+not|cannot|can\s+not|never|not\s+yet)\b[^,]{0,80}\b(?:name|nominate|identify|select|advance|approve|recommend|return|give|provide)?\s*(?:a\s+)?candidate(?:\s+or\s+(?:stop|terminate|reject|drop|end))?\b/i.test(normalized)
    || /\b(?:candidate(?:\s+or\s+(?:stop|terminate|reject|drop|end))?|candidate\s+(?:decision|direction))\b[^,]{0,80}\b(?:remain(?:s|ed)?\s+(?:blocked|prohibited|deferred)|stay(?:s|ed)?\s+(?:blocked|prohibited|deferred)|is\s+(?:blocked|prohibited|deferred)|must\s+remain\s+(?:blocked|prohibited|deferred)|is\s+not\s+yet\s+allowed|remains?\s+prohibited)\b/i.test(normalized);
}

function hasExplicitDecisionGateBoundary(value) {
  return decisionGateClauses(value).some((clause) => {
    if (!hasDecisionOutcomeLanguage(clause)) return false;
    if (decisionOutcomeIsExplicitlyDenied(clause)) return true;
    const hasSecondRoundGate = /\bcomplete(?:d)?\b[^.!?;]{0,70}\bsecond\s+round\b|\bsecond\s+round\b[^.!?;]{0,70}\bcomplete(?:d)?\b|\bboth\s+rounds?\b[^.!?;]{0,50}\bcomplete(?:d)?\b/i.test(clause);
    const hasNamedOwnerGate = /\bnamed\b[^.!?;]{0,60}\btechnical\b[^.!?;]{0,40}\bowner\b[^.!?;]{0,50}\breview(?:ed)?\b|\bnamed\s+technical\s+owner\s+review(?:ed)?\b/i.test(clause);
    const conditionalBoundary = /\b(?:only\s+after|not\s+before|until|provided\s+that|if\s+and\s+only\s+if|requires?|required)\b/i.test(clause);
    return conditionalBoundary && hasSecondRoundGate && hasNamedOwnerGate;
  });
}

function hasPrematureDecisionPromise(value) {
  return decisionGateClauses(value).some((clause) => hasDecisionOutcomeLanguage(clause) && !hasExplicitDecisionGateBoundary(clause));
}

function normalizeAnchorText(value) {
  const visible = String(value ?? '')
    .replace(/<\/?u\b[^>]*>/gi, '')
    .replace(/\*\*([^*\n]+)\*\*/g, '$1')
    .replace(/__([^_\n]+)__/g, '$1')
    .replace(/~~([^~\n]+)~~/g, '$1')
    .replace(/`([^`\n]+)`/g, '$1')
    .replace(/[\*_~`]+/g, ' ');
  return normalizeText(visible)
    .replace(/^[\s.,:;!?()\[\]{}'"]+|[\s.,:;!?()\[\]{}'"]+$/g, '')
    .replace(/\s+/g, ' ');
}


function semanticTokens(value) {
  const stop = new Set(['the', 'and', 'for', 'with', 'from', 'that', 'this', 'one', 'before', 'after', 'into', 'when', 'your', 'their', 'must', 'should', 'can', 'will']);
  return normalizeText(value)
    .split(/[^\p{L}\p{N}]+/u)
    .filter((token) => token.length >= 4 && !stop.has(token))
    .map((token) => token.length > 5 ? token.replace(/(?:ies|ing|ed|es|s)$/i, (suffix) => suffix === 'ies' ? 'y' : '') : token)
    .filter((token) => token.length >= 4);
}

function taskConcepts(value) {
  const normalized = normalizeText(value);
  const concepts = new Set();
  const conceptPatterns = new Map([
    ['complete', /\b(?:complete|finali[sz]e|prepare|fill|finish|define|standardi[sz]e|compile)\w*\b/i],
    ['input-contract', /\b(?:input|data|project)\s+(?:sheet|form|contract|worksheet|brief|record)|\b(?:requirements?|specification)\s+(?:sheet|form|contract)\b/i],
    ['shortlist', /\b(?:shortlist|candidate direction|supplier selection|supplier motor|compare candidates?|evaluate options?)\w*\b/i],
    ['sample-validation', /\b(?:sample|prototype)\s+(?:test|validation|approval|acceptance)|\bvalidate\s+(?:a\s+)?sample\b/i],
    ['commercial-buy', /\b(?:rfq|quotation|quote request|purchase|order|commercial inquiry)\w*\b/i],
    ['navigation', /\b(?:route|browse|navigate|category|catalog|overview|hub)\w*\b/i],
    ['troubleshoot', /\b(?:diagnose|troubleshoot|root cause|repair|fix failure)\w*\b/i],
  ]);
  for (const [concept, pattern] of conceptPatterns) if (pattern.test(normalized)) concepts.add(concept);
  return concepts;
}

function taskFamilies(value) {
  return [...BUYER_TASK_FAMILY_PATTERNS.entries()]
    .filter(([, pattern]) => pattern.test(normalizeText(value)))
    .map(([family]) => family);
}

function semanticOverlap(left, right) {
  const rightTokens = new Set(semanticTokens(right));
  return [...new Set(semanticTokens(left))].filter((token) => rightTokens.has(token));
}

function requireCanonicalBuyerRole(value, source, field, problems, { canonicalOnly = false } = {}) {
  const role = String(value || '').trim();
  const normalized = normalizeText(role);
  if (normalized.length < 3 || PLACEHOLDER_PATTERN.test(normalized) || hasLowEntropy(role)) {
    fail(problems, `${source} field ${field} must name a concrete active buyer role; received ${value || 'missing'}`);
    return '';
  }
  const canonicalRole = CANONICAL_BUYER_ROLES.get(normalized);
  if (!canonicalRole && canonicalOnly) {
    fail(problems, `${source} field ${field} must be Engineer, Quality, Procurement, or Management; received ${role}`);
    return '';
  }
  return canonicalRole || role;
}

function rejectOwnerPlaceholder(value, source, field, problems) {
  const normalized = normalizeText(value);
  if (/^(?:owner|content owner|page owner|link owner|routing owner|team|staff|department|group|function|sales|marketing|engineering|(?:sales|marketing|engineering|product|content|commercial|technical|quality|procurement|operations)(?:\s+(?:team|staff|department|group|function))?)$/i.test(normalized)) {
    fail(problems, `${source} field ${field} must name a concrete accountable owner, not a role placeholder: ${value}`);
  }
}

function hasLowEntropy(value) {
  const compact = normalizeText(value).replace(/[^\p{L}\p{N}]+/gu, '');
  if (compact.length < 8) return false;
  const uniqueCharacters = new Set(compact).size;
  if (uniqueCharacters <= 2) return true;
  const tokens = normalizeText(value).split(/[^\p{L}\p{N}]+/u).filter(Boolean);
  if (tokens.length >= 3 && new Set(tokens).size === 1) return true;
  return false;
}

function meaningfulScalar(value, source, field, problems, { minLength = 4 } = {}) {
  rejectTemplatePlaceholder(value, source, field, problems);
  const normalized = normalizeText(value);
  if (normalized.length < minLength || PLACEHOLDER_PATTERN.test(normalized)
    || /(?:placeholder|lorem ipsum|replace-with|fill[- ]?in)/i.test(normalized) || hasLowEntropy(normalized)) {
    fail(problems, `${source} field ${field} must be a concrete non-placeholder value and must not be low entropy`);
  }
  return value;
}

function markdownHeadingSlug(value) {
  return normalizeText(value)
    .replace(/[^\p{L}\p{N}\s-]/gu, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .replace(/^\d+-/, '');
}

function markdownFragmentTargets(body) {
  const targets = new Map();
  const add = (raw, kind, line) => {
    const slug = markdownHeadingSlug(raw);
    if (!slug) return;
    const entries = targets.get(slug) || [];
    entries.push({ kind, line });
    targets.set(slug, entries);
  };
  const lines = String(body || '').split('\n');
  for (let index = 0; index < lines.length; index += 1) {
    const heading = /^(#{1,6})\s+(.+)$/.exec(lines[index]);
    if (heading) add(heading[2], 'heading', index);
    const anchor = /^[ \t]*<a[ \t]+id="([A-Za-z][A-Za-z0-9:_-]*)"[ \t]*><\/a>[ \t]*$/i.exec(lines[index]);
    if (anchor) add(anchor[1], 'source-anchor', index);
  }
  for (const [slug, entries] of targets) {
    if (entries.length !== 2) continue;
    const anchor = entries.find((entry) => entry.kind === 'source-anchor');
    const heading = entries.find((entry) => entry.kind === 'heading');
    if (!anchor || !heading || anchor.line >= heading.line) continue;
    if (lines.slice(anchor.line + 1, heading.line).some((line) => line.trim())) continue;
    targets.set(slug, [{ kind: 'source-anchor-heading', line: heading.line, anchorLine: anchor.line }]);
  }
  return { lines, targets };
}

function splitLocalRef(value) {
  const hashIndex = value.indexOf('#');
  return {
    pathPart: (hashIndex < 0 ? value : value.slice(0, hashIndex)).trim(),
    fragment: (hashIndex < 0 ? '' : value.slice(hashIndex + 1)).trim(),
  };
}

function requireMeaningfulString(record, field, problems, { minLength = 4 } = {}) {
  const value = string(record, field, problems);
  meaningfulScalar(value, record.source, field, problems, { minLength });
  return value;
}

function requireDistinctMeaningfulArray(record, field, problems, { minItems = 1, minLength = 4 } = {}) {
  const values = strings(record, field, problems);
  const normalized = [];
  for (const value of values) {
    rejectTemplatePlaceholder(value, record.source, field, problems);
    const item = normalizeText(value);
    if (item.length < minLength || PLACEHOLDER_PATTERN.test(item)
      || /(?:placeholder|lorem ipsum|replace-with|fill[- ]?in)/i.test(item) || hasLowEntropy(item)) {
      fail(problems, `${record.source} field ${field} contains a non-concrete item or low-entropy value: ${value}`);
    }
    normalized.push(item);
  }
  if (values.length < minItems) fail(problems, `${record.source} field ${field} requires at least ${minItems} item(s)`);
  if (new Set(normalized).size !== normalized.length) fail(problems, `${record.source} field ${field} must not contain duplicate items`);
  return values;
}

function rejectPackedEnumeration(value, source, field, problems) {
  const normalized = normalizeText(value);
  for (const vocabulary of ENUMERATION_VOCABULARIES) {
    const words = vocabulary.filter((word) => new RegExp(`\\b${word}\\b`, 'i').test(normalized));
    if (words.length < 2) continue;
    const packed = new RegExp(`\\b(?:${vocabulary.join('|')})\\b\\s*(?:[,/|;+]|\\band\\b|\\bor\\b|、|，)\\s*\\b(?:${vocabulary.join('|')})\\b`, 'i');
    if (packed.test(normalized)) {
      fail(problems, `${source} field ${field} must declare one dominant intent/stage, not a packed enumeration`);
      return;
    }
  }
}

function validateSingleDominantTask(value, source, field, problems) {
  const families = taskFamilies(value);
  if (families.length > 1) {
    fail(problems, `${source} field ${field} must own one dominant buyer task; detected competing task families: ${families.join(', ')}`);
  }
}

function validateThreeLayerPain(record, dominantTask, queryCluster, problems) {
  const fields = ['pain_trigger', 'surface_problem', 'operational_friction', 'business_consequence', 'desired_decision'];
  const values = fields.map((field) => [field, requireMeaningfulString(record, field, problems, { minLength: 12 })]);
  for (const [field, value] of values) {
    const normalized = normalizeText(value);
    const genericTerms = normalized.match(GENERIC_PAIN_TERMS_PATTERN) || [];
    const semanticTerms = semanticTokens(normalized);
    const genericRatio = semanticTerms.length ? genericTerms.length / semanticTerms.length : 1;
    if (GENERIC_PAIN_ONLY_PATTERN.test(normalized) || (genericRatio >= 0.45 && !CONCRETE_BUYER_CONTEXT_PATTERN.test(normalized))) {
      fail(problems, `${record.source} field ${field} is a generic business benefit/problem without a concrete buyer scene, friction, or consequence: ${value}`);
    }
    if (!PAIN_ROLE_PATTERNS.get(field)?.test(normalized)) {
      fail(problems, `${record.source} field ${field} does not perform its required pain-chain role with an observable event, failure, friction, consequence, or decision: ${value}`);
    }
    if (!CONCRETE_BUYER_CONTEXT_PATTERN.test(normalized)) {
      fail(problems, `${record.source} field ${field} must name a concrete buyer actor, object, evidence item, or operating condition: ${value}`);
    }
  }
  const taskContext = [dominantTask, ...queryCluster].join(' ');
  const contextualFields = values.filter(([, value]) => semanticOverlap(value, taskContext).length > 0);
  if (contextualFields.length < 3) {
    fail(problems, `${record.source} three-layer pain must connect at least three fields to the dominant buyer task or query context; found ${contextualFields.length}`);
  }
  const painVocabulary = semanticTokens(values.map(([, value]) => value).join(' '));
  if (new Set(painVocabulary).size < 12) {
    fail(problems, `${record.source} three-layer pain lacks enough concrete, distinct buyer-context terms`);
  }
  const byField = new Map(values);
  if (!/\b(?:label|specification|assumption|input|evidence|measurement|drawing|limit|threshold|interface|load|duty|route|controller|voltage|current|sample|candidate)\w*\b/i.test(byField.get('surface_problem'))) {
    fail(problems, `${record.source} surface_problem must name the concrete information, evidence, interface, or operating variable that is unclear or conflicting`);
  }
  if (!/\b(?:reconcil|rework|retest|manual|back[- ]?and[- ]?forth|repeat|chase|wait|delay|review cycle|handoff)\w*\b/i.test(byField.get('operational_friction'))) {
    fail(problems, `${record.source} operational_friction must state the repeatable work mechanism, not merely say that a delay exists`);
  }
  if (!/\b(?:sample validation|supplier review|approval|launch|schedule|budget|order|technical rework|scrap|field failure|program risk)\b/i.test(byField.get('business_consequence'))) {
    fail(problems, `${record.source} business_consequence must name a downstream program, approval, sample, supplier, schedule, budget, or field consequence`);
  }
  if (!/\b(?:before|when|if|unless|until|only|otherwise|subject to|within|under)\b/i.test(byField.get('desired_decision'))) {
    fail(problems, `${record.source} desired_decision must include a decision boundary or trigger, not only a generic selection verb`);
  }
}

function isWithinRoot(root, target) {
  const rel = relative(root, target);
  return rel === '' || (!rel.startsWith(`..${sep}`) && rel !== '..' && !rel.startsWith(sep));
}

function validateLocalEvidenceRefs(values, source, field, evidenceRoot, problems, { requireFragment = false, regularNonSymlink = false, verifyFragment = true } = {}) {
  const resolvedRefs = [];
  for (const value of values) {
    rejectTemplatePlaceholder(value, source, field, problems);
    const { pathPart, fragment } = splitLocalRef(value);
    if (!pathPart || pathPart.startsWith('/') || /^[A-Za-z][A-Za-z0-9+.-]*:/.test(pathPart)) {
      fail(problems, `${source} field ${field} must contain local relative evidence paths: ${value}`);
      continue;
    }
    if (requireFragment && !fragment) {
      fail(problems, `${source} field ${field} evidence ref must include a specific #section fragment: ${value}`);
      continue;
    }
    const target = resolve(evidenceRoot, pathPart);
    if (!isWithinRoot(evidenceRoot, target)) {
      fail(problems, `${source} field ${field} evidence path escapes package evidence root: ${value}`);
      continue;
    }
    if (!existsSync(target) || !statSync(target).isFile()) {
      fail(problems, `${source} field ${field} evidence path does not exist as a file: ${value}`);
      continue;
    }
    if (regularNonSymlink && (lstatSync(target).isSymbolicLink() || !lstatSync(target).isFile())) {
      fail(problems, `${source} field ${field} evidence path must be a regular non-symlink file: ${value}`);
      continue;
    }
    const realRoot = realpathSync(evidenceRoot);
    const realTarget = realpathSync(target);
    if (!isWithinRoot(realRoot, realTarget)) {
      fail(problems, `${source} field ${field} evidence path resolves outside package evidence root: ${value}`);
      continue;
    }
    if (fragment && verifyFragment) {
      let parsed;
      try { parsed = parseArticleMarkdownFrontMatter(readFileSync(realTarget, 'utf8'), { source: realTarget }); }
      catch (error) { fail(problems, `${source} field ${field} evidence record is invalid: ${error.message}`); continue; }
      const fragmentSlug = markdownHeadingSlug(fragment);
      const matches = markdownFragmentTargets(parsed.body).targets.get(fragmentSlug) || [];
      if (!fragmentSlug || matches.length === 0) {
        fail(problems, `${source} field ${field} fragment #${fragment} does not match an evidence section or source-only anchor`);
        continue;
      }
      if (matches.length !== 1) {
        fail(problems, `${source} field ${field} fragment #${fragment} is ambiguous because it resolves to ${matches.length} targets`);
        continue;
      }
    }
    resolvedRefs.push(realTarget);
  }
  return resolvedRefs;
}

function rejectSyntheticEvidenceFiles(paths, source, field, problems) {
  for (const path of paths) {
    const content = readFileSync(path, 'utf8');
    if (/\bsynthetic(?:-fixture)?\b|虚构|虚拟/i.test(content)) {
      fail(problems, `${source} field ${field} references synthetic evidence and cannot support evidence_scope=production: ${path}`);
    }
  }
}

function markdownSectionBody(body, fragment) {
  const targetSlug = markdownHeadingSlug(fragment);
  const { lines, targets } = markdownFragmentTargets(body);
  const matches = targets.get(targetSlug) || [];
  if (matches.length !== 1) return '';
  const target = matches[0];
  let start = target.line;
  let level = 7;
  if (target.kind === 'source-anchor') {
    for (let index = target.line + 1; index < lines.length; index += 1) {
      const heading = /^(#{1,6})\s+(.+)$/.exec(lines[index]);
      if (!heading) continue;
      start = index;
      level = heading[1].length;
      break;
    }
  } else {
    const heading = /^(#{1,6})\s+(.+)$/.exec(lines[start]);
    level = heading ? heading[1].length : 7;
  }
  let end = lines.length;
  for (let index = start + 1; index < lines.length; index += 1) {
    const match = /^(#{1,6})\s+/.exec(lines[index]);
    if (match && match[1].length <= level) { end = index; break; }
  }
  return lines.slice(start, end).join('\n');
}

function parseStructuredEvidenceSection(sectionMarkdown) {
  const fields = new Map();
  for (const line of sectionMarkdown.split('\n').slice(1)) {
    const bullet = /^\s*(?:[-*]\s*)?([A-Za-z][A-Za-z0-9 _-]{1,40})\s*:\s*(.+?)\s*$/.exec(line);
    const table = /^\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$/.exec(line);
    const match = bullet || table;
    if (!match || /^:?-{3,}:?$/.test(match[1].trim()) || /^:?-{3,}:?$/.test(match[2].trim())) continue;
    const canonical = STRUCTURED_EVIDENCE_FIELDS.get(normalizeFieldIdentifier(match[1]));
    if (!canonical) continue;
    if (fields.has(canonical)) fields.set(canonical, '');
    else fields.set(canonical, match[2].trim().replace(/^`|`$/g, ''));
  }
  return fields;
}

function validateStructuredEvidenceSection(sectionMarkdown, source, field, ref, problems, {
  evidenceRoot = '',
  expectedCheckId = '',
  expectedTargets = [],
  expectedOwner = '',
  requiredExtraFields = [],
  latestAllowedAt = '',
} = {}) {
  const fields = parseStructuredEvidenceSection(sectionMarkdown);
  for (const canonical of [...REQUIRED_STRUCTURED_EVIDENCE_FIELDS, ...requiredExtraFields]) {
    const value = fields.get(canonical) || '';
    if (!value) fail(problems, `${source} field ${field} evidence section ${ref} requires one non-empty ${canonical}`);
  }
  const checkId = fields.get('check_id') || '';
  if (expectedCheckId && normalizeFieldIdentifier(checkId) !== normalizeFieldIdentifier(expectedCheckId)) {
    fail(problems, `${source} field ${field} evidence section ${ref} check_id must be ${expectedCheckId}`);
  }
  const targetUrl = fields.get('target_url') || '';
  const targetRole = fields.get('target_role') || '';
  const targetTask = fields.get('target_task') || '';
  if (targetUrl) requireAbsoluteHttpsUrl(targetUrl, source, `${field} target_url`, problems);
  if (fields.get('observed_at')) {
    requireFreshIsoDate(fields.get('observed_at'), source, `${field} observed_at`, problems);
    if (latestAllowedAt) requireDateNoLaterThan(fields.get('observed_at'), latestAllowedAt, source, `${field} observed_at`, 'reviewed_at', problems);
  }
  if (fields.get('artifact_digest') && !/^sha256:[a-f0-9]{64}$/i.test(fields.get('artifact_digest'))) {
    fail(problems, `${source} field ${field} evidence section ${ref} artifact_digest must use sha256:<64 hex>`);
  }
  for (const name of ['method', 'observed_result', 'acceptance_criteria', 'capability_acceptance', 'render_target', 'readability_result', 'producer', 'independent_reviewer']) {
    if (fields.get(name)) meaningfulScalar(fields.get(name), source, `${field} ${name}`, problems, { minLength: ['method', 'observed_result', 'acceptance_criteria', 'capability_acceptance', 'readability_result'].includes(name) ? 12 : 4 });
  }
  for (const name of ['target_task', 'observed_result', 'capability_acceptance', 'observable_output']) {
    const value = fields.get(name) || '';
    if (value && hasPrematureDecisionPromise(value)) {
      fail(problems, `${source} field ${field} evidence section ${ref} ${name} must not promise candidate-or-stop before a complete second-round package and named technical-owner review`);
    }
  }
  if (fields.get('accountable_owner')) requireStableOwnerIdentity(fields.get('accountable_owner'), source, `${field} accountable_owner`, problems);
  if (expectedOwner && normalizeText(fields.get('accountable_owner') || '') !== normalizeText(expectedOwner)) {
    fail(problems, `${source} field ${field} evidence section ${ref} accountable_owner must exactly match the declared accountable owner ${expectedOwner}`);
  }
  for (const [aliasKey, aliasName, replacement] of [
    ['rejected_alias_task', 'task', 'target_task'],
    ['rejected_alias_owner', 'owner', 'accountable_owner'],
    ['rejected_alias_process', 'process', 'method'],
    ['rejected_alias_viewport_width', 'viewport_width', 'viewport_width_px=320'],
  ]) {
    if (fields.has(aliasKey)) fail(problems, `${source} field ${field} evidence section ${ref} ${aliasName} is a rejected alias; use ${replacement}`);
  }
  const artifactRef = fields.get('artifact_ref') || fields.get('screenshot_or_trace_ref') || '';
  const artifactDigest = fields.get('artifact_digest') || '';
  if (!artifactRef) fail(problems, `${source} field ${field} evidence section ${ref} artifact_digest requires a real artifact_ref or screenshot_or_trace_ref`);
  const producerId = fields.get('producer_id') || '';
  const reviewerId = fields.get('independent_reviewer_id') || '';
  const stableIdentityPattern = /^[A-Za-z0-9][A-Za-z0-9._:-]{5,127}$/;
  if (producerId && (!stableIdentityPattern.test(producerId) || PLACEHOLDER_PATTERN.test(producerId))) {
    fail(problems, `${source} field ${field} evidence section ${ref} producer_id must be a stable non-placeholder identifier without display-name spaces`);
  }
  if (reviewerId && (!stableIdentityPattern.test(reviewerId) || PLACEHOLDER_PATTERN.test(reviewerId))) {
    fail(problems, `${source} field ${field} evidence section ${ref} independent_reviewer_id must be a stable non-placeholder identifier without display-name spaces`);
  }
  if (producerId && reviewerId && normalizeText(producerId) === normalizeText(reviewerId)) {
    fail(problems, `${source} field ${field} evidence section ${ref} producer_id and independent_reviewer_id must be different stable identities`);
  }
  if (artifactRef && evidenceRoot) {
    const resolvedArtifacts = validateLocalEvidenceRefs([artifactRef], source, `${field} artifact_ref`, evidenceRoot, problems, {
      regularNonSymlink: true,
      verifyFragment: false,
    });
    if (resolvedArtifacts.length === 1 && /^sha256:[a-f0-9]{64}$/i.test(artifactDigest)) {
      const actualDigest = `sha256:${createHash('sha256').update(readFileSync(resolvedArtifacts[0])).digest('hex')}`;
      if (actualDigest !== artifactDigest.toLowerCase()) {
        fail(problems, `${source} field ${field} evidence section ${ref} artifact_digest must exactly match artifact_ref bytes; expected ${actualDigest}`);
      }
    }
  }
  const policyArtifactRef = fields.get('policy_artifact_ref') || '';
  const policyArtifactDigest = fields.get('policy_artifact_digest') || '';
  if ((policyArtifactRef && !policyArtifactDigest) || (!policyArtifactRef && policyArtifactDigest)) {
    fail(problems, `${source} field ${field} evidence section ${ref} policy_artifact_ref and policy_artifact_digest must be supplied together`);
  }
  if (policyArtifactDigest && !/^sha256:[a-f0-9]{64}$/i.test(policyArtifactDigest)) {
    fail(problems, `${source} field ${field} evidence section ${ref} policy_artifact_digest must use sha256:<64 hex>`);
  }
  if (policyArtifactRef && evidenceRoot) {
    const resolvedPolicyArtifacts = validateLocalEvidenceRefs([policyArtifactRef], source, `${field} policy_artifact_ref`, evidenceRoot, problems, {
      regularNonSymlink: true,
      verifyFragment: false,
    });
    if (resolvedPolicyArtifacts.length === 1 && /^sha256:[a-f0-9]{64}$/i.test(policyArtifactDigest)) {
      const actualPolicyDigest = `sha256:${createHash('sha256').update(readFileSync(resolvedPolicyArtifacts[0])).digest('hex')}`;
      if (actualPolicyDigest !== policyArtifactDigest.toLowerCase()) {
        fail(problems, `${source} field ${field} evidence section ${ref} policy_artifact_digest must exactly match policy_artifact_ref bytes; expected ${actualPolicyDigest}`);
      }
    }
  }
  if (fields.get('viewport_width_px') && !/^320$/.test(fields.get('viewport_width_px'))) {
    fail(problems, `${source} field ${field} evidence section ${ref} viewport_width_px must be exactly 320`);
  }
  if (fields.get('capability_acceptance') && /\b(?:not[- ]?run|missing|unverified|unconfirmed|rejected|failed|not accepted)\b/i.test(fields.get('capability_acceptance'))) {
    fail(problems, `${source} field ${field} evidence section ${ref} capability_acceptance must be a concrete affirmative endpoint-specific acceptance`);
  }
  const independentReviewer = fields.get('independent_reviewer') || '';
  if (independentReviewer && /\b(?:ai|assistant|bot|automated|self[- ]?review|same author|same producer)\b/i.test(normalizeText(independentReviewer))) {
    fail(problems, `${source} field ${field} evidence section ${ref} independent_reviewer must identify a distinct human reviewer, not AI or self-review`);
  }
  if (fields.get('producer') && independentReviewer
    && normalizeText(fields.get('producer')) === normalizeText(independentReviewer)) {
    fail(problems, `${source} field ${field} evidence section ${ref} producer and independent_reviewer must be different`);
  }
  if (producerId && reviewerId && normalizeText(producerId) === normalizeText(reviewerId)) {
    fail(problems, `${source} field ${field} evidence section ${ref} producer/reviewer stable IDs prove self-review rather than independent review`);
  }
  if (/\b(?:not[- ]?run|not verified|unverified|unconfirmed|missing|placeholder|synthetic-only|everything is fine)\b/i.test(fields.get('observed_result') || '')) {
    fail(problems, `${source} field ${field} evidence section ${ref} observed_result must be a concrete confirmed observation`);
  }
  let matchedTarget = -1;
  if (expectedTargets.length && targetUrl && targetRole && targetTask) {
    const accountableOwner = fields.get('accountable_owner') || '';
    const urlMatches = expectedTargets.filter((target) => normalizeText(target.url) === normalizeText(targetUrl));
    if (!urlMatches.length) {
      fail(problems, `${source} field ${field} evidence section ${ref} target_url must exactly match one declared target URL`);
    }
    const roleMatches = urlMatches.filter((target) => normalizeText(target.role) === normalizeText(targetRole));
    if (urlMatches.length && !roleMatches.length) {
      fail(problems, `${source} field ${field} evidence section ${ref} target_role must exactly match the role declared for target_url`);
    }
    const taskMatches = roleMatches.filter((target) => {
      if (!String(target.task || '').trim()) return true;
      return semanticOverlap(target.task, targetTask).length >= Math.min(2, new Set(semanticTokens(target.task)).size || 1);
    });
    if (roleMatches.length && !taskMatches.length) {
      fail(problems, `${source} field ${field} evidence section ${ref} target_task must semantically match the task declared for target_url and target_role`);
    }
    const ownerMatches = taskMatches.filter((target) => !target.owner || normalizeText(target.owner) === normalizeText(accountableOwner));
    if (taskMatches.length && !ownerMatches.length) {
      fail(problems, `${source} field ${field} evidence section ${ref} accountable_owner must exactly match the owner declared for the target contract`);
    }
    if (ownerMatches.length) matchedTarget = expectedTargets.indexOf(ownerMatches[0]);
  }
  return { fields, matchedTarget };
}

function validateReferencedSectionQuality(values, source, field, evidenceRoot, problems, { expectedTerms = [] } = {}) {
  for (const value of values) {
    const { pathPart, fragment } = splitLocalRef(value);
    if (!pathPart || !fragment) continue;
    const target = resolve(evidenceRoot, pathPart);
    if (!existsSync(target) || !statSync(target).isFile()) continue;
    let parsed;
    try { parsed = parseArticleMarkdownFrontMatter(readFileSync(target, 'utf8'), { source: target }); }
    catch { continue; }
    const section = markdownSectionBody(parsed.body, fragment);
    const sectionWithoutHeading = section.replace(/^#{1,6}\s+.*$/m, '');
    const plain = normalizeText(markdownPlainText(sectionWithoutHeading));
    if (plain.length < 32 || hasLowEntropy(plain)
      || /^(?:todo|tbd|placeholder|replace|fill in|everything is fine)\b/i.test(plain)
      || /\b(?:todo|tbd|replace with real evidence|placeholder evidence|lorem ipsum)\b/i.test(plain)) {
      fail(problems, `${source} field ${field} evidence section must contain concrete non-placeholder evidence, not an empty, TODO, or low-information section: ${value}`);
      continue;
    }
    if (expectedTerms.length && !expectedTerms.some((term) => plain.includes(normalizeText(term)))) {
      fail(problems, `${source} field ${field} evidence section must contain check-specific evidence language for ${expectedTerms.join(', ')}: ${value}`);
    }
  }
}

function validateProductionEvidenceRefs(values, source, field, evidenceRoot, problems, {
  expectedKinds = [],
  expectedCheckId = '',
  expectedTargets = [],
  expectedOwner = '',
  requiredExtraFields = [],
  requireStructuredSection = false,
  latestAllowedAt = '',
} = {}) {
  const allowedKinds = new Set(Array.isArray(expectedKinds) ? expectedKinds : [expectedKinds]);
  const inspections = [];
  for (const value of values) {
    const { pathPart, fragment } = splitLocalRef(value);
    if (!pathPart || !fragment) {
      fail(problems, `${source} field ${field} production evidence ref must include an existing #section fragment: ${value}`);
      continue;
    }
    const target = resolve(evidenceRoot, pathPart);
    if (!existsSync(target) || !statSync(target).isFile()) continue;
    const realRoot = realpathSync(evidenceRoot);
    const realTarget = realpathSync(target);
    if (!isWithinRoot(realRoot, realTarget)) continue;
    let parsed;
    try { parsed = parseArticleMarkdownFrontMatter(readFileSync(realTarget, 'utf8'), { source: realTarget }); }
    catch (error) { fail(problems, `${source} field ${field} production evidence record is invalid: ${error.message}`); continue; }
    const getEvidenceString = (name) => {
      try { return requireStringField(parsed.attributes, name, { source: realTarget }); }
      catch (error) { fail(problems, `${source} field ${field} production evidence metadata: ${error.message}`); return ''; }
    };
    const recordType = getEvidenceString('record_type');
    const evidenceScope = getEvidenceString('evidence_scope');
    const evidenceSource = getEvidenceString('source');
    const observedAt = parsed.attributes.observed_at || parsed.attributes.date;
    const digest = getEvidenceString('digest');
    const evidenceKind = getEvidenceString('evidence_kind');
    if (recordType !== 'evidence-record') fail(problems, `${realTarget} record_type must be evidence-record for production evidence`);
    if (evidenceScope !== 'production') fail(problems, `${realTarget} evidence_scope must be production`);
    meaningfulScalar(evidenceSource, realTarget, 'source', problems, { minLength: 4 });
    if (typeof observedAt !== 'string' || !observedAt.trim()) fail(problems, `${realTarget} production evidence requires observed_at or date`);
    else {
      requireFreshIsoDate(observedAt, realTarget, 'observed_at/date', problems);
      if (latestAllowedAt) requireDateNoLaterThan(observedAt, latestAllowedAt, realTarget, 'observed_at/date', 'reviewed_at', problems);
    }
    if (!/^sha256:[a-f0-9]{64}$/i.test(digest)) {
      fail(problems, `${realTarget} digest must use sha256:<64 hex>`);
    } else {
      const actualDigest = createHash('sha256').update(parsed.body).digest('hex');
      if (digest.slice(7).toLowerCase() !== actualDigest) fail(problems, `${realTarget} digest does not match the evidence record body`);
    }
    if (allowedKinds.size && !allowedKinds.has(evidenceKind)) {
      fail(problems, `${source} field ${field} evidence_kind=${evidenceKind || 'missing'} does not match required kind ${[...allowedKinds].join(' or ')}`);
    }
    const plainEvidenceBody = markdownPlainText(parsed.body);
    if (plainEvidenceBody.length < 40 || hasLowEntropy(plainEvidenceBody)) {
      fail(problems, `${realTarget} production evidence body must be concrete, non-low-entropy, and independently reviewable`);
    }
    const fragmentSlug = markdownHeadingSlug(fragment);
    const headingSlugs = new Set([...parsed.body.matchAll(/^#{1,6}\s+(.+)$/gm)].map((match) => markdownHeadingSlug(match[1])));
    if (!fragmentSlug || !headingSlugs.has(fragmentSlug)) {
      fail(problems, `${source} field ${field} fragment #${fragment} does not match an evidence-record section`);
      continue;
    }
    const sectionMarkdown = markdownSectionBody(parsed.body, fragment);
    const sectionBody = markdownPlainText(sectionMarkdown.replace(/^#{1,6}\s+.*(?:\n|$)/, ''));
    if (sectionBody.length < 24 || hasLowEntropy(sectionBody)) {
      fail(problems, `${source} field ${field} fragment #${fragment} must contain concrete non-low-entropy evidence`);
    }
    validateReferencedSectionQuality([value], source, field, evidenceRoot, problems, {
      expectedTerms: [expectedCheckId, ...expectedKinds].filter(Boolean),
    });
    if (requireStructuredSection || expectedCheckId || expectedTargets.length) inspections.push({
      ref: value,
      ...validateStructuredEvidenceSection(sectionMarkdown, source, field, value, problems, {
        evidenceRoot, expectedCheckId, expectedTargets, expectedOwner, requiredExtraFields, latestAllowedAt,
      }),
    });
    const lifecyclePattern = LIFECYCLE_EVIDENCE_KINDS.get(evidenceKind);
    if (lifecyclePattern && !lifecyclePattern.test(sectionBody)) {
      fail(problems, `${source} field ${field} evidence metadata kind ${evidenceKind} is inconsistent with fragment body #${fragment}`);
    }
  }
  return inspections;
}

function validatePublishedLifecycleEvidenceRefs(rows, publish, evidenceRoot, reviewedAt, problems) {
  const field = 'publication_lifecycle_evidence_rows';
  if (!Array.isArray(rows) || rows.length !== 8) {
    fail(problems, `${publish.source} published ${field} must contain exactly eight lifecycle evidence rows`);
    return;
  }
  const requiredAxes = ['authorization', 'cms-mutation', 'backend-readback', 'editor-reopen', 'anonymous-frontend', 'desktop', 'mobile', 'image-fetch-decode'];
  const seen = new Set();
  for (const row of rows) {
    const parts = String(row).split('|').map((part) => part.trim());
    if (parts.length !== 12 || parts.some((part) => !part)) {
      fail(problems, `${publish.source} ${field} row must use axis|status|artifact-ref|sha256|site-id|record-id|url-or-not-applicable|producer-id|independent-reviewer-id|observed-at|reviewed-at|review-ceiling`);
      continue;
    }
    const [axis, status, artifactRef, digest, siteId, recordId, url, producerId, reviewerId, observedAt, rowReviewedAt, reviewCeiling] = parts;
    if (!requiredAxes.includes(axis)) { fail(problems, `${publish.source} ${field} uses unknown lifecycle axis ${axis}`); continue; }
    if (seen.has(axis)) fail(problems, `${publish.source} ${field} duplicates lifecycle axis ${axis}`);
    seen.add(axis);
    if (status !== 'pass') fail(problems, `${publish.source} published lifecycle axis ${axis} requires status=pass`);
    if (!/^sha256:[a-f0-9]{64}$/i.test(digest)) fail(problems, `${publish.source} published lifecycle axis ${axis} requires sha256:<64 hex>`);
    requireStableActorId(producerId, publish.source, `${field} ${axis} producer-id`, problems);
    requireStableActorId(reviewerId, publish.source, `${field} ${axis} independent-reviewer-id`, problems);
    if (normalizeText(producerId) === normalizeText(reviewerId)) fail(problems, `${publish.source} published lifecycle axis ${axis} producer and independent reviewer must differ`);
    for (const [name, value] of [['site-id', siteId], ['record-id', recordId]]) meaningfulScalar(value, publish.source, `${field} ${axis} ${name}`, problems, { minLength: 3 });
    if (['anonymous-frontend', 'desktop', 'mobile', 'image-fetch-decode'].includes(axis)) requireProductionPublicHttpsUrl(url, publish.source, `${field} ${axis} url`, problems);
    requireFreshIsoDate(observedAt, publish.source, `${field} ${axis} observed-at`, problems);
    requireIsoDate(rowReviewedAt, publish.source, `${field} ${axis} reviewed-at`, problems);
    requireIsoDate(reviewCeiling, publish.source, `${field} ${axis} review-ceiling`, problems);
    requireDateNoLaterThan(observedAt, rowReviewedAt, publish.source, `${field} ${axis} observed-at`, 'reviewed-at', problems);
    requireDateNoLaterThan(rowReviewedAt, reviewCeiling, publish.source, `${field} ${axis} reviewed-at`, 'review-ceiling', problems);
    requireDateNoLaterThan(rowReviewedAt, reviewedAt, publish.source, `${field} ${axis} reviewed-at`, 'canonical reviewed_at', problems);
    requireDateNoLaterThan(reviewCeiling, reviewedAt, publish.source, `${field} ${axis} review-ceiling`, 'canonical reviewed_at', problems);
    const resolved = validateLocalEvidenceRefs([artifactRef], publish.source, `${field} ${axis} artifact-ref`, evidenceRoot, problems, { regularNonSymlink: true, verifyFragment: false });
    if (resolved.length === 1 && /^sha256:[a-f0-9]{64}$/i.test(digest)) {
      const actual = `sha256:${createHash('sha256').update(readFileSync(resolved[0])).digest('hex')}`;
      if (actual !== digest.toLowerCase()) fail(problems, `${publish.source} published lifecycle axis ${axis} digest must exactly match artifact-ref bytes`);
    }
  }
  for (const axis of requiredAxes) if (!seen.has(axis)) fail(problems, `${publish.source} published lifecycle evidence is missing axis ${axis}`);
  if (normalizeText(string(publish, 'publication_lifecycle_evidence_verdict', problems)) !== 'pass') fail(problems, `${publish.source} published lifecycle requires publication_lifecycle_evidence_verdict=pass`);
}

function statusWithLocalRefs(record, statusField, refsField, evidenceRoot, problems, { requiredStatus = '', productionEvidence = false, expectedKinds = [] } = {}) {
  const status = string(record, statusField, problems);
  const refs = strings(record, refsField, problems);
  if (!FACT_STATUSES.has(status)) {
    fail(problems, `${record.source} ${statusField} must use the canonical fact-status vocabulary`);
  }
  if (requiredStatus && status !== requiredStatus) {
    fail(problems, `${record.source} requires ${statusField}=${requiredStatus}`);
  }
  if (refs.length < 1) fail(problems, `${record.source} ${statusField} requires at least one ${refsField} entry`);
  const resolvedRefs = validateLocalEvidenceRefs(refs, record.source, refsField, evidenceRoot, problems);
  if (productionEvidence) {
    rejectSyntheticEvidenceFiles(resolvedRefs, record.source, refsField, problems);
    validateProductionEvidenceRefs(refs, record.source, refsField, evidenceRoot, problems, { expectedKinds });
  }
  return { status, refs, resolvedRefs };
}

function confirmedStatusWithRefs(record, statusField, refsField, evidenceRoot, problems, { productionEvidence = false, expectedKinds = [] } = {}) {
  const status = string(record, statusField, problems);
  const refs = strings(record, refsField, problems);
  rejectTemplatePlaceholders(refs, record.source, refsField, problems);
  const resolvedRefs = validateLocalEvidenceRefs(refs, record.source, refsField, evidenceRoot, problems);
  if (!FACT_STATUSES.has(status)) {
    fail(problems, `${record.source} ${statusField} must use the canonical fact-status vocabulary`);
  }
  if (status !== 'confirmed') {
    fail(problems, `${record.source} index buyer article requires ${statusField}=confirmed`);
  }
  if (refs.length < 1) {
    fail(problems, `${record.source} confirmed ${statusField} requires at least one ${refsField} entry`);
  }
  if (productionEvidence) {
    rejectSyntheticEvidenceFiles(resolvedRefs, record.source, refsField, problems);
    validateProductionEvidenceRefs(refs, record.source, refsField, evidenceRoot, problems, { expectedKinds });
  }
  return { status, refs, resolvedRefs };
}

function parseInternalLinkTargets(values, source, evidenceRoot, problems, {
  productionEvidence = false,
  contractValues = [],
  dominantTask = '',
  buyerRoles = new Map(),
} = {}) {
  const basicTargets = [];
  const legacyContracts = [];
  for (const value of values) {
    rejectTemplatePlaceholder(value, source, 'internal_link_targets', problems);
    const parts = value.split('|').map((part) => part.trim());
    if (![3, 9].includes(parts.length) || parts.some((part) => !part)) {
      fail(problems, `${source} internal_link_targets entry must use role|URL|anchor; legacy nine-part rows remain supported: ${value}`);
      continue;
    }
    const [role, url, anchor] = parts;
    if (!INTERNAL_LINK_ROLES.has(role)) {
      fail(problems, `${source} internal-link role must be hub, product, educational, or conversion; received ${role}`);
    }
    requireAbsoluteHttpsUrl(url, source, 'internal_link_targets URL', problems);
    const normalizedAnchor = normalizeAnchorText(anchor);
    if (GENERIC_ANCHORS.has(normalizedAnchor) || PROMOTIONAL_NAVIGATION_ANCHOR_PATTERN.test(normalizedAnchor)) {
      fail(problems, `${source} internal-link anchor must describe the buyer task, evidence, decision, or expected output; promotional navigation text is rejected: ${anchor}`);
    }
    if (normalizedAnchor.length < 4 || PLACEHOLDER_PATTERN.test(normalizedAnchor) || hasLowEntropy(normalizedAnchor)) {
      fail(problems, `${source} internal-link anchor must be concrete and non-low-entropy; received ${anchor}`);
    }
    basicTargets.push({ role, url, anchor, normalizedAnchor });
    if (parts.length === 9) legacyContracts.push(value);
  }
  if (new Set(basicTargets.map((target) => `${target.role}|${target.url}`)).size !== basicTargets.length) {
    fail(problems, `${source} internal_link_targets must not repeat the same role and URL`);
  }

  const contractsToParse = contractValues.length ? contractValues : legacyContracts;
  if (!contractsToParse.length) {
    fail(problems, `${source} internal_link_buyer_task_contracts requires one nine-part contract for every internal_link_target`);
    return basicTargets;
  }
  const contracts = [];
  for (const value of contractsToParse) {
    rejectTemplatePlaceholder(value, source, 'internal_link_buyer_task_contracts', problems);
    const parts = value.split('|').map((part) => part.trim());
    if (parts.length !== 9 || parts.some((part) => !part)) {
      fail(problems, `${source} internal_link_buyer_task_contracts entry must use role|URL|anchor|buyer_need|target_buyer_role|placement|target_status|owner|acceptance_evidence_ref: ${value}`);
      continue;
    }
    const [role, url, anchor, buyerNeed, targetBuyerRole, placement, targetStatus, owner, acceptanceEvidenceRef] = parts;
    if (!INTERNAL_LINK_ROLES.has(role)) {
      fail(problems, `${source} internal-link role must be hub, product, educational, or conversion; received ${role}`);
    }
    requireAbsoluteHttpsUrl(url, source, 'internal_link_buyer_task_contracts URL', problems);
    const normalizedAnchor = normalizeAnchorText(anchor);
    if (GENERIC_ANCHORS.has(normalizedAnchor) || PROMOTIONAL_NAVIGATION_ANCHOR_PATTERN.test(normalizedAnchor)) fail(problems, `${source} internal-link anchor must describe the buyer task, evidence, decision, or expected output; promotional navigation text is rejected: ${anchor}`);
    meaningfulScalar(buyerNeed, source, 'internal_link_buyer_task_contracts buyer_need', problems, { minLength: 8 });
    const anchorTaskOverlap = semanticOverlap(anchor, `${buyerNeed} ${dominantTask}`).length;
    const anchorDecisionSignal = /\b(?:review|compare|validate|evidence|input|output|decision|candidate|stop|qualification|specification|fit|boundary|test|sample|diagnos|troubleshoot|readiness)\w*\b/i.test(normalizedAnchor);
    if (anchorTaskOverlap < 2 || !anchorDecisionSignal) fail(problems, `${source} internal-link anchor must semantically match the declared buyer_need or dominant task and name a buyer task, evidence, decision, or output: ${anchor}`);
    const canonicalTargetRole = requireCanonicalBuyerRole(targetBuyerRole, source, 'internal_link_buyer_task_contracts target_buyer_role', problems);
    const normalizedPlacement = normalizeText(placement).replace(/\s+section$/, '').replace(/\s+/g, '-');
    if (!INTERNAL_LINK_PLACEMENTS.has(normalizedPlacement) && !['candidate-or-stop', 'next-validation', 'direct-answer'].includes(normalizedPlacement)) {
      fail(problems, `${source} internal-link placement must name a locatable opening, direct-answer, decision-path, candidate-or-stop, next-validation, evidence, comparison, faq, or cta section; received ${placement}`);
    }
    if (!FACT_STATUSES.has(targetStatus) && !(productionEvidence === false && targetStatus === 'reserved-synthetic-target')) fail(problems, `${source} internal-link target_status must use the canonical fact-status vocabulary or reserved-synthetic-target for a synthetic fixture`);
    if (productionEvidence && targetStatus !== 'confirmed') fail(problems, `${source} production internal-link target_status must be confirmed`);
    meaningfulScalar(owner, source, 'internal_link_buyer_task_contracts owner', problems, { minLength: 4 });
    rejectOwnerPlaceholder(owner, source, 'internal_link_buyer_task_contracts owner', problems);
    const refs = [acceptanceEvidenceRef];
    const resolved = validateLocalEvidenceRefs(refs, source, 'internal_link_buyer_task_contracts acceptance_evidence_ref', evidenceRoot, problems);
    if (productionEvidence) {
      rejectSyntheticEvidenceFiles(resolved, source, 'internal_link_buyer_task_contracts acceptance_evidence_ref', problems);
      validateProductionEvidenceRefs(refs, source, 'internal_link_buyer_task_contracts acceptance_evidence_ref', evidenceRoot, problems, {
        expectedKinds: ['internal-link-acceptance'],
      });
    }
    const roleObjection = canonicalTargetRole ? buyerRoles.get(canonicalTargetRole)?.objection || '' : '';
    const legitimateTechnicalHandoff = ['technical-review', 'diagnostic'].includes(normalizeText(role))
      && canonicalTargetRole === 'Quality'
      && /\b(?:bench|vehicle|test|validation|evidence|acceptance|quality|next task)\b/i.test(buyerNeed);
    if (!semanticOverlap(buyerNeed, dominantTask).length && !semanticOverlap(buyerNeed, roleObjection).length && !legitimateTechnicalHandoff) {
      fail(problems, `${source} internal-link buyer_need must share a concrete decision term with dominant_task_contract or the ${canonicalTargetRole || targetBuyerRole} objection: ${buyerNeed}`);
    }
    const inferredNeedRoles = [...ROLE_SEMANTIC_PATTERNS.entries()]
      .filter(([, pattern]) => pattern.test(buyerNeed))
      .map(([roleName]) => roleName);
    const conflictingRoles = inferredNeedRoles.filter((roleName) => roleName !== canonicalTargetRole);
    if (conflictingRoles.length && !inferredNeedRoles.includes(canonicalTargetRole)) {
      const handoffNamesTarget = EXPLICIT_HANDOFF_PATTERN.test(buyerNeed)
        && new RegExp(`\\b${canonicalTargetRole}\\b`, 'i').test(buyerNeed)
        && conflictingRoles.some((roleName) => new RegExp(`\\b${roleName}\\b`, 'i').test(buyerNeed));
      if (!handoffNamesTarget) {
        fail(problems, `${source} internal-link buyer_need semantically belongs to ${conflictingRoles.join(', ')} but targets ${canonicalTargetRole || targetBuyerRole}; declare an explicit cross-role handoff or use the matching target buyer role: ${buyerNeed}`);
      }
    }
    contracts.push({
      role, url, anchor, normalizedAnchor, buyerNeed, targetBuyerRole: canonicalTargetRole || targetBuyerRole,
      placement, targetStatus, owner, acceptanceEvidenceRef,
    });
  }
  const needKeys = contracts.map((target) => normalizeText(target.buyerNeed));
  if (new Set(needKeys).size !== needKeys.length) {
    fail(problems, `${source} internal-link buyer_need values must be normalized-distinct across link roles`);
  }
  if (new Set(contracts.map((target) => `${target.role}|${target.url}`)).size !== contracts.length) {
    fail(problems, `${source} internal_link_buyer_task_contracts must not repeat the same role and URL`);
  }
  for (const target of basicTargets) {
    const contract = contracts.find((item) => item.role === target.role && item.url === target.url);
    if (!contract) {
      fail(problems, `${source} internal_link_target ${target.role}|${target.url} is missing its buyer-task contract`);
      continue;
    }
    if (contract.normalizedAnchor !== target.normalizedAnchor) {
      fail(problems, `${source} internal link anchor parity mismatch for ${target.url}`);
    }
    Object.assign(target, contract);
  }
  for (const contract of contracts) {
    if (!basicTargets.some((target) => target.role === contract.role && target.url === contract.url)) {
      fail(problems, `${source} internal_link_buyer_task_contract ${contract.role}|${contract.url} has no matching internal_link_target`);
    }
  }
  return basicTargets;
}

function parseBuyerRoleMatrix(values, source, problems, activeRoles = []) {
  const roles = new Map();
  const normalizedValues = { objection: [], answer: [], reason: [] };
  for (const value of values) {
    const parts = value.split('|').map((part) => part.trim());
    if (parts.length !== 5 || parts.some((part) => !part)) {
      fail(problems, `${source} buyer_role_matrix entry must use role|concrete objection|article-owned answer|delegated owner/page or N/A|delegation reason: ${value}`);
      continue;
    }
    const [rawRole, objection, articleAnswer, delegatedOwner, delegationReason] = parts;
    const role = requireCanonicalBuyerRole(rawRole, source, 'buyer_role_matrix role', problems, { canonicalOnly: true });
    const key = normalizeText(role);
    if (!key) continue;
    if (roles.has(key)) { fail(problems, `${source} buyer_role_matrix must contain active role ${role} exactly once`); continue; }
    meaningfulScalar(objection, source, `buyer_role_matrix ${role} objection`, problems, { minLength: 12 });
    meaningfulScalar(articleAnswer, source, `buyer_role_matrix ${role} article-owned answer`, problems, { minLength: 12 });
    meaningfulScalar(delegationReason, source, `buyer_role_matrix ${role} delegation reason`, problems, { minLength: 8 });
    if (!['n/a', 'na', 'none'].includes(normalizeText(delegatedOwner))) meaningfulScalar(delegatedOwner, source, `buyer_role_matrix ${role} delegated owner/page`, problems, { minLength: 4 });
    const semanticPattern = ROLE_SEMANTIC_PATTERNS.get(CANONICAL_BUYER_ROLES.get(key));
    if (semanticPattern && !semanticPattern.test(`${objection} ${articleAnswer} ${delegationReason}`)) fail(problems, `${source} buyer_role_matrix ${role} row lacks minimum role-related semantics`);
    normalizedValues.objection.push(normalizeText(objection)); normalizedValues.answer.push(normalizeText(articleAnswer)); normalizedValues.reason.push(normalizeText(delegationReason));
    roles.set(key, { role, objection, articleAnswer, delegatedOwner, delegationReason });
  }
  if (activeRoles.length) {
    const active = activeRoles.map(normalizeText);
    for (const role of active) if (!roles.has(role)) fail(problems, `${source} buyer_role_matrix must contain active role ${role} exactly once`);
    for (const role of roles.keys()) if (!active.includes(role)) fail(problems, `${source} buyer_role_matrix must cover only active primary/secondary roles; unexpected ${role}`);
  }
  for (const [label, valuesToCheck] of Object.entries(normalizedValues)) if (new Set(valuesToCheck).size !== valuesToCheck.length) fail(problems, `${source} buyer_role_matrix ${label} values must be normalized-distinct across active roles`);
  return roles;
}

function parseProductDecisionMap(values, source, evidenceRoot, problems, { productionEvidence = false, targetRoleByUrl = new Map() } = {}) {
  const rows = [];
  const placeholder = /\b(?:pending|tbd|todo|placeholder|to be supplied|stakeholder discussion|product discussion remains unresolved|candidate direction|product candidate direction)\b/i;
  for (const value of values) {
    const parts = value.split('|').map((part) => part.trim());
    if (parts.length !== 9 || parts.some((part) => !part)) {
      fail(problems, `${source} product_decision_map entry must use condition|variable|evidence|no-fit|remaining-inputs|candidate-or-stop|candidate-target-url-or-N/A|next-validation-target-url|placement: ${value}`);
      continue;
    }
    const [buyerCondition, decisionVariable, supportingEvidence, noFitCondition, remainingInputs, candidate, candidateTarget, nextValidationTarget, placement] = parts;
    for (const [label,val,min] of [['condition',buyerCondition,10],['variable',decisionVariable,6],['no-fit',noFitCondition,10],['remaining-inputs',remainingInputs,8],['candidate-or-stop',candidate,6]]) meaningfulScalar(val, source, `product_decision_map ${label}`, problems, { minLength:min });
    if (!NO_FIT_PATTERN.test(noFitCondition) || placeholder.test(noFitCondition)) fail(problems, `${source} product_decision_map no-fit condition requires a concrete observable stop/no-fit condition: ${noFitCondition}`);
    const isStop = /^(?:stop|no-fit|no fit|reject|disqualified)$/i.test(candidate);
    if (!isStop) {
      const deferredToTargetAndDraft = /^candidate$/i.test(candidate);
      if (!deferredToTargetAndDraft && NAVIGATION_CANDIDATE_PATTERN.test(candidate)) {
        fail(problems, `${source} product_decision_map candidate must be a conditional product or solution direction, not a navigation page: ${candidate}`);
      } else if (!deferredToTargetAndDraft && (placeholder.test(candidate) || !/(?:\b[A-Z]{2,}[A-Z0-9-]*\d[A-Z0-9-]*\b|\b(?:model|sku|assembly|system|motor|drive|solution|controller|platform|module)\b)/i.test(candidate) || !/\b(?:under|when|for|within|if|subject to|provided)\b/i.test(candidate))) {
        fail(problems, `${source} product_decision_map candidate must name a concrete SKU/model or assembly/system class plus a condition: ${candidate}`);
      }
      requireAbsoluteHttpsUrl(candidateTarget, source, 'product_decision_map candidate target', problems);
      if (!/\/(?:products?|solutions?|systems?|hub)(?:\/|$)/i.test(candidateTarget) || /\/(?:guides?|blog|articles?|resources?)(?:\/|$)/i.test(candidateTarget)) fail(problems, `${source} product_decision_map candidate target must be a product/solution/hub HTTPS destination, not a guide: ${candidateTarget}`);
    } else if (!/^N\/?A$/i.test(candidateTarget)) fail(problems, `${source} product_decision_map stop row requires candidate-target-url-or-N/A=N/A`);
    requireAbsoluteHttpsUrl(nextValidationTarget, source, 'product_decision_map next validation target', problems);
    const placementParts = placement.split(/\s*(?:,|;|\band\b)\s*/i).filter(Boolean);
    if (!placementParts.length || placementParts.some((part) => !/\b(?:opening|direct[- ]?answer|decision(?:[- ]?path)?|candidate(?:[- ]?or[- ]?stop)?|evidence|comparison|faq|cta|call to action|section)\b/i.test(part))) {
      fail(problems, `${source} product_decision_map placement must name locatable opening, direct-answer, decision, candidate-or-stop, evidence, comparison, FAQ, or CTA section(s); received ${placement}`);
    }
    const evidenceRefs = supportingEvidence.split(',').map((part) => part.trim()).filter((part) => /(?:^|\/)\.?[^#\s]+\.(?:md|markdown)#.+$/i.test(part));
    const resolvedEvidence = evidenceRefs.length
      ? validateLocalEvidenceRefs(evidenceRefs, source, 'product_decision_map evidence', evidenceRoot, problems)
      : [];
    if (evidenceRefs.length) validateReferencedSectionQuality(evidenceRefs, source, 'product_decision_map evidence', evidenceRoot, problems, {
      expectedTerms: [decisionVariable, buyerCondition, noFitCondition],
    });
    if (productionEvidence) {
      if (!evidenceRefs.length) fail(problems, `${source} production product_decision_map requires local section-bound evidence refs in its evidence column`);
      rejectSyntheticEvidenceFiles(resolvedEvidence, source, 'product_decision_map evidence', problems);
      validateProductionEvidenceRefs(evidenceRefs, source, 'product_decision_map evidence', evidenceRoot, problems, {
        expectedKinds:['product-decision'],
        expectedCheckId: 'product-decision',
        expectedTargets: [{
          url: isStop ? nextValidationTarget : candidateTarget,
          role: targetRoleByUrl.get(normalizeText(isStop ? nextValidationTarget : candidateTarget)) || (isStop ? 'technical-review' : 'product'),
          task: `${buyerCondition} ${decisionVariable} ${candidate}`,
        }],
        requireStructuredSection: true,
      });
    }
    rows.push({ buyerCondition, decisionVariable, supportingEvidence, noFitCondition, remainingInputs, candidate, candidateTarget, nextValidationTarget, placement, isStop });
  }
  return rows;
}

function sameNormalizedSet(left, right) {
  const leftSet = new Set(left.map((value) => normalizeText(value)));
  const rightSet = new Set(right.map((value) => normalizeText(value)));
  return leftSet.size === rightSet.size && [...leftSet].every((value) => rightSet.has(value));
}

function parseCannibalizationConflicts(conflictValues, separationValues, source, ownerPage, ownerTaskContract, problems) {
  const conflicts = new Map();
  for (const value of conflictValues) {
    const parts = value.split('|').map((part) => part.trim());
    if (parts.length !== 3 || parts.some((part) => !part)) { fail(problems, `${source} conflict_candidates entry must use candidate_url|overlap_basis|candidate_action: ${value}`); continue; }
    const [url, overlapBasis, action] = parts;
    requireAbsoluteHttpsUrl(url, source, 'conflict_candidates URL', problems);
    meaningfulScalar(overlapBasis, source, 'conflict_candidates overlap basis', problems, { minLength: 8 });
    if (!['update','merge','redirect','do-not-write','delegate'].includes(action)) fail(problems, `${source} conflict_candidates action must be update, merge, redirect, do-not-write, or delegate; received ${action}`);
    if (normalizeText(url) === normalizeText(ownerPage)) fail(problems, `${source} owner_page must not also appear in conflict_candidates: ${url}`);
    if (conflicts.has(normalizeText(url))) fail(problems, `${source} conflict_candidates URLs must be distinct`);
    conflicts.set(normalizeText(url), { url, overlapBasis, action });
  }
  const separations = new Map();
  for (const value of separationValues) {
    const parts = value.split('|').map((part) => part.trim());
    if (parts.length !== 8 || parts.some((part) => !part)) {
      fail(problems, `${source} intent_separation entry must use candidate_url|action|decision_object|expected_output|stage|commitment|candidate_task|non_overlap_boundary: ${value}`);
      continue;
    }
    const [url, action, decisionObject, expectedOutput, stage, commitment, candidateTask, boundary] = parts;
    requireAbsoluteHttpsUrl(url, source, 'intent_separation URL', problems);
    for (const [field, valuePart, min] of [
      ['action', action, 4], ['decision object', decisionObject, 8], ['expected output', expectedOutput, 8],
      ['candidate task', candidateTask, 12], ['non-overlap boundary', boundary, 12],
    ]) meaningfulScalar(valuePart, source, `intent_separation ${field}`, problems, { minLength: min });
    const parity = [
      ['action', action, ownerTaskContract.action],
      ['decision_object', decisionObject, ownerTaskContract.decisionObject],
      ['expected_output', expectedOutput, ownerTaskContract.expectedOutput],
      ['stage', stage, ownerTaskContract.stage],
      ['commitment', commitment, ownerTaskContract.commitment],
    ];
    for (const [field, actual, expected] of parity) {
      if (normalizeText(actual) !== normalizeText(expected)) fail(problems, `${source} intent_separation ${field} must match dominant_task_contract`);
    }
    if (!TASK_STAGES.has(normalizeText(stage))) fail(problems, `${source} intent_separation stage is invalid: ${stage}`);
    if (!COMMERCIAL_COMMITMENTS.has(normalizeText(commitment))) fail(problems, `${source} intent_separation commitment is invalid: ${commitment}`);
    if (normalizeText(commitment) === 'none' && COMMERCIAL_ACTION_PATTERN.test(`${action} ${decisionObject} ${expectedOutput} ${candidateTask}`)) {
      fail(problems, `${source} intent_separation mixes a commercial action with commitment=none`);
    }
    const ownerTask = `${action} ${decisionObject} ${expectedOutput}`;
    const ownerTokens = new Set(semanticTokens(ownerTask));
    const candidateTokens = new Set(semanticTokens(candidateTask));
    const sharedTaskTokens = [...ownerTokens].filter((token) => candidateTokens.has(token));
    const taskUnionSize = new Set([...ownerTokens, ...candidateTokens]).size;
    const taskOverlapRatio = taskUnionSize ? sharedTaskTokens.length / taskUnionSize : 1;
    const ownerConcepts = taskConcepts(ownerTask);
    const candidateConcepts = taskConcepts(candidateTask);
    const sharedConcepts = [...ownerConcepts].filter((concept) => candidateConcepts.has(concept));
    const sameTaskFamily = taskFamilies(ownerTask).some((family) => taskFamilies(candidateTask).includes(family));
    if (normalizeText(ownerTask) === normalizeText(candidateTask) || taskOverlapRatio >= 0.6
      || (sameTaskFamily && sharedConcepts.length >= 2)
      || (sharedConcepts.includes('complete') && sharedConcepts.includes('input-contract'))) {
      fail(problems, `${source} intent_separation candidate_task materially duplicates owner task; merge, redirect, or do-not-write instead`);
    }
    const boundaryTokens = new Set(semanticTokens(boundary));
    const ownerBoundaryOverlap = [...ownerTokens].filter((token) => boundaryTokens.has(token));
    const candidateBoundaryOverlap = [...candidateTokens].filter((token) => boundaryTokens.has(token));
    if (!ownerBoundaryOverlap.length || !candidateBoundaryOverlap.length) {
      fail(problems, `${source} intent_separation non_overlap_boundary must visibly name both the owner task and candidate task boundary`);
    }
    if (!/\b(?:owner|article)\b/i.test(boundary) || !/\b(?:candidate|target|hub|page|article)\b/i.test(boundary)
      || !/\b(?:input|output|stage|before|after|while|only|owns?|routes?|completes?|validates?|compares?|readiness|exploration)\b/i.test(boundary)) {
      fail(problems, `${source} intent_separation non_overlap_boundary must explicitly name the owner/article, candidate/target page, and their different stage/input/output responsibility`);
    }
    if (separations.has(normalizeText(url))) fail(problems, `${source} intent_separation URLs must be distinct`);
    separations.set(normalizeText(url), { url, action, decisionObject, expectedOutput, stage, commitment, candidateTask, boundary });
  }
  if (!sameNormalizedSet([...conflicts.keys()], [...separations.keys()])) fail(problems, `${source} conflict_candidates and intent_separation candidate URLs must match one-to-one`);
  return { conflicts, separations };
}

function parsePipeRows(record, field, problems, { parts, minItems = 1, exactItems = 0, minPartLength = 3 } = {}) {
  const values = requireDistinctMeaningfulArray(record, field, problems, {
    minItems: exactItems || minItems,
    minLength: Math.max(8, parts * minPartLength),
  });
  if (exactItems && values.length !== exactItems) {
    fail(problems, `${record.source} field ${field} requires exactly ${exactItems} item(s)`);
  }
  const rows = values.map((value) => {
    const row = value.split('|').map((part) => part.trim());
    if (row.length !== parts || row.some((part) => !part)) {
      fail(problems, `${record.source} field ${field} entry must contain exactly ${parts} non-empty pipe-delimited parts: ${value}`);
      return row;
    }
    for (const part of row) {
      rejectTemplatePlaceholder(part, record.source, field, problems);
      meaningfulScalar(part, record.source, field, problems, { minLength: minPartLength });
    }
    return row;
  });
  return { values, rows };
}

function parsePipeScalar(record, field, problems, { parts, minPartLength = 3 } = {}) {
  const value = requireMeaningfulString(record, field, problems, { minLength: Math.max(8, parts * minPartLength) });
  const row = value.split('|').map((part) => part.trim());
  if (row.length !== parts || row.some((part) => !part)) {
    fail(problems, `${record.source} field ${field} must contain exactly ${parts} non-empty pipe-delimited parts`);
    return { value, row };
  }
  for (const part of row) {
    rejectTemplatePlaceholder(part, record.source, field, problems);
    meaningfulScalar(part, record.source, field, problems, { minLength: minPartLength });
  }
  return { value, row };
}

function validateCtaInputCoverage(record, ctaInputs, inquiryInputs, problems) {
  for (const legacyField of [
    'cta_progressive_omitted_inputs',
    'cta_progressive_followup_action',
    'cta_progressive_followup_owner',
  ]) {
    if (legacyField in record.attributes) {
      fail(problems, `${record.source} legacy ${legacyField} is not allowed; use cta_progressive_profiling_* fields only`);
    }
  }
  const mode = string(record, 'cta_input_collection_mode', problems);
  if (!CTA_INPUT_COLLECTION_MODES.has(mode)) {
    fail(problems, `${record.source} cta_input_collection_mode must be complete or progressive-profiling`);
  }
  const missing = inquiryInputs.filter((input) => !ctaInputs.map(normalizeText).includes(normalizeText(input)));
  const extra = ctaInputs.filter((input) => !inquiryInputs.map(normalizeText).includes(normalizeText(input)));
  const status = string(record, 'cta_progressive_profiling_status', problems);
  const omitted = strings(record, 'cta_progressive_profiling_omitted_inputs', problems, { allowEmpty: true });
  const followupAction = requireMeaningfulString(record, 'cta_progressive_profiling_followup_action', problems, { minLength: 4 });
  const followupOwner = requireMeaningfulString(record, 'cta_progressive_profiling_followup_owner', problems, { minLength: 4 });
  if (mode === 'complete') {
    if (!sameNormalizedSet(ctaInputs, inquiryInputs)) {
      fail(problems, `${record.source} complete CTA requires cta_required_inputs to exactly match required_inquiry_inputs`);
    }
    if (status !== 'not-used') fail(problems, `${record.source} complete CTA requires cta_progressive_profiling_status=not-used`);
    if (omitted.length) fail(problems, `${record.source} complete CTA requires cta_progressive_profiling_omitted_inputs=[]`);
    if (normalizeText(followupAction) !== 'not-applicable') {
      fail(problems, `${record.source} complete CTA requires cta_progressive_profiling_followup_action=not-applicable`);
    }
    if (normalizeText(followupOwner) !== 'not-applicable') {
      fail(problems, `${record.source} complete CTA requires cta_progressive_profiling_followup_owner=not-applicable`);
    }
  } else if (mode === 'progressive-profiling') {
    if (status !== 'used') fail(problems, `${record.source} progressive CTA requires cta_progressive_profiling_status=used`);
    const normalizedOmitted = validateInquiryInputs(omitted, record.source, 'cta_progressive_profiling_omitted_inputs', problems, { minItems: 1 });
    if (!missing.length || extra.length || !sameNormalizedSet(missing, omitted)) {
      fail(problems, `${record.source} progressive profiling must declare exactly the omitted required inquiry inputs and no extra CTA inputs`);
    }
    rejectTemplatePlaceholder(followupAction, record.source, 'cta_progressive_profiling_followup_action', problems);
    rejectOwnerPlaceholder(followupOwner, record.source, 'cta_progressive_profiling_followup_owner', problems);
    if (!normalizedOmitted.length) fail(problems, `${record.source} progressive profiling requires at least one omitted input`);
  }
  return { mode, status, omitted, followupAction, followupOwner };
}

function validateInquiryInputs(values, source, field, problems, { minItems = 3 } = {}) {
  const normalized = [];
  for (const value of values) {
    const item = normalizeText(value);
    if (item.length < 4 || /^\d+$/.test(item) || PLACEHOLDER_PATTERN.test(item) || hasLowEntropy(item)
      || /^(?:input|field|value|item|parameter|details?)(?:\s*\d+)?$/i.test(item)) {
      fail(problems, `${source} field ${field} contains a filler, numeric, or too-short inquiry input: ${value}`);
    }
    normalized.push(item);
  }
  if (values.length < minItems || new Set(normalized).size < minItems) {
    const minimumLabel = minItems === 3 ? 'three distinct concrete inputs' : `${minItems} distinct concrete input`;
    fail(problems, `${source} ${field} must contain at least ${minimumLabel}`);
  }
  return normalized;
}

function collectAllinCmsFormatFeatures(nodes) {
  const features = new Set();
  const visit = (value) => {
    if (Array.isArray(value)) {
      for (const item of value) visit(item);
      return;
    }
    if (!value || typeof value !== 'object') return;
    if (['h2', 'h3', 'p', 'blockquote', 'table', 'img'].includes(value.type)) features.add(value.type);
    if (value.type === 'hr') features.add('divider');
    if (value.type === 'a') features.add('link');
    if (value.listStyleType === 'disc') features.add('bulleted-list');
    if (value.listStyleType === 'decimal') features.add('numbered-list');
    for (const mark of ['bold', 'italic', 'underline', 'strikethrough']) {
      if (value[mark] === true) features.add(mark);
    }
    if (value.code === true) features.add('inline-code');
    visit(value.children);
  };
  visit(nodes);
  return features;
}

function collectAllinCmsLinks(nodes) {
  const links = [];
  const textContent = (value) => {
    if (Array.isArray(value)) return value.map(textContent).join('');
    if (!value || typeof value !== 'object') return '';
    const ownText = typeof value.text === 'string' ? value.text : '';
    return ownText + textContent(value.children);
  };
  let currentH2 = 'opening';
  let currentH3 = '';
  const visit = (value, context) => {
    if (Array.isArray(value)) {
      for (const item of value) visit(item, context);
      return;
    }
    if (!value || typeof value !== 'object') return;
    if (value.type === 'a' && typeof value.url === 'string') {
      const anchorText = textContent(value.children);
      links.push({
        url: value.url,
        anchorText,
        normalizedAnchor: normalizeAnchorText(anchorText),
        sectionH2: context.sectionH2,
        sectionH3: context.sectionH3,
        sectionText: context.sectionText,
      });
    }
    visit(value.children, context);
  };
  for (const node of Array.isArray(nodes) ? nodes : []) {
    const nodeText = textContent(node);
    if (node?.type === 'h2') { currentH2 = nodeText; currentH3 = ''; }
    else if (node?.type === 'h3') currentH3 = nodeText;
    visit(node, { sectionH2: currentH2, sectionH3: currentH3, sectionText: `${currentH2} ${currentH3}`.trim() });
  }
  return links;
}

function significantTokens(value) {
  return semanticTokens(value);
}

function markdownPlainText(body) {
  return securityCanonicalText(body)
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, ' ')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/<\/?[A-Za-z][^>]*>/g, '')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/[*_~`]/g, '')
    .replace(/^[>|-]+\s*/gm, ' ')
    .replace(/[|]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function validateNoRepeatedFullSentences(draft, problems) {
  const sentences = draft.body.split('\n').flatMap((line) => {
    const trimmed = line.trim();
    if (!trimmed || /^(?:[-*+]\s+|\d+[.)]\s+|\|)/.test(trimmed)) return [];
    return markdownPlainText(trimmed).match(/[^.!?。！？]+[.!?。！？]/g) || [];
  }).map((sentence) => normalizeText(sentence)).filter((sentence) => sentence.length >= 48)
    .filter((sentence) => !/^do not (?:attach|paste|send|submit|share|upload|transmit|hand off)\b/.test(sentence));
  const boldStatements = [...draft.body.matchAll(/\*\*([^*\n]{32,})\*\*/g)].map((match) => normalizeText(match[1]));
  for (const [label, values] of [['full sentence', sentences], ['bold risk/judgment sentence', boldStatements]]) {
    const counts = new Map();
    for (const value of values) counts.set(value, (counts.get(value) || 0) + 1);
    const duplicate = [...counts.entries()].find(([, count]) => count > 1);
    if (duplicate) fail(problems, `${draft.source} repeats the same ${label} ${duplicate[1]} times: ${duplicate[0]}`);
  }
}

function normalizedPhraseCount(haystack, needle) {
  const body = normalizeText(haystack).replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
  const phrase = normalizeText(needle).replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
  if (!phrase) return 0;
  return body.split(phrase).length - 1;
}

function validateObviousSearchStuffing(brief, draft, problems) {
  const primaryQuery = string(brief, 'primary_query', problems);
  const publishable = markdownPlainText(draft.body);
  const exactCount = normalizedPhraseCount(publishable, primaryQuery);
  if (exactCount >= 7) {
    fail(problems, `${draft.source} obvious exact-query stuffing: primary_query appears ${exactCount} times in the publishable body`);
  }
  for (const paragraph of String(draft.body || '').split(/\n\s*\n/u)) {
    const paragraphCount = normalizedPhraseCount(markdownPlainText(paragraph), primaryQuery);
    if (paragraphCount >= 3) {
      fail(problems, `${draft.source} obvious paragraph-level exact-query stuffing: primary_query appears ${paragraphCount} times in one paragraph`);
      break;
    }
  }
  const tokens = semanticTokens(publishable);
  const contractPhrases = [
    ...strings(brief, 'first_round_inquiry_inputs', problems, { allowEmpty: true }),
    ...strings(brief, 'second_round_inquiry_inputs', problems, { allowEmpty: true }),
    ...strings(brief, 'direct_answer_required_inputs_or_evidence', problems, { allowEmpty: true }),
    ...strings(brief, 'cta_required_inputs', problems, { allowEmpty: true }),
  ].map((value) => semanticTokens(value).join(' ')).filter(Boolean);
  for (const width of [4, 5]) {
    const counts = new Map();
    for (let index = 0; index <= tokens.length - width; index += 1) {
      const gram = tokens.slice(index, index + width).join(' ');
      counts.set(gram, (counts.get(gram) || 0) + 1);
    }
    const abusive = [...counts.entries()].find(([gram, count]) => count >= 7
      && new Set(gram.split(' ')).size >= Math.min(3, width)
      && !contractPhrases.some((phrase) => phrase.includes(gram)));
    if (abusive) {
      fail(problems, `${draft.source} obvious repeated ${width}-gram stuffing appears ${abusive[1]} times: ${abusive[0]}`);
      break;
    }
  }
}

const HIGH_RISK_PRODUCT_CLAIM_PATTERN = /\b(?:CE|UL|ETL|FCC|RoHS|ISO)\s*[- ]?(?:certified|compliant)\b|\b(?:certified|compliant)\s+(?:to|with|under)\b|\b(?:fits?|compatible with|works? with)\s+(?:every|all|any|[A-Z0-9][A-Za-z0-9._-]*)\b|\buniversal(?:ly)?\s+(?:fit|compatible)\b|\b(?:provides?|delivers?|produces?|supports?|rated(?:\s+for)?|achieves?)\b[^.!?]{0,60}\b\d+(?:\.\d+)?\s*(?:N\s*m|Nm|kW|W|V|A|Ah|Wh|%|hours?|cycles?|units?\s*(?:\/|per)\s*(?:day|month|year))\b|\b\d+(?:\.\d+)?\s*(?:N\s*m|Nm|kW|W|V|A|Ah|Wh|%|hours?|cycles?)\b[^.!?]{0,55}\b(?:continuous(?:ly)?|guaranteed|durability|lifetime|performance|capacity)\b|\b(?:continuous rating|rated continuous|service life|design life|durability|lifetime)\b[^.!?]{0,70}\b(?:\d+|guaranteed|rated|supports?|delivers?)\b|\b(?:production capacity|manufacturing capacity)\b[^.!?]{0,55}\b(?:\d+|units?|per day|per month|available)\b|\b(?:in stock|inventory available|available from stock|ships? within|lead time (?:is|of)|delivery within)\b|\b(?:SKU|model)\s+[A-Za-z0-9._-]+\b[^.!?]{0,70}\b(?:fits?|suitable|ideal|recommended|qualified|approved)\b/i;
const PRODUCT_CLAIM_NEGATION_PATTERN = /\b(?:does not|do not|cannot|can not|not|no|without|unverified|unknown|requires evidence|no evidence|not proven|not confirmed|not certified|not claimed|is not made|are not made)\b/i;
const PRODUCT_CLAIM_TYPES = new Set([
  'certification', 'compliance', 'universal-fit', 'compatibility', 'performance', 'continuous-rating',
  'durability', 'capacity', 'production-capability', 'inventory', 'lead-time', 'sku-suitability',
]);
const PRODUCT_CLAIM_PRODUCTION_STATUSES = new Set(['production-supported', 'synthetic-only', 'not-applicable-for-production']);

const DIRECT_HIGH_RISK_PRODUCT_CLAIM_PATTERN = /\b(?:CE|UL|ETL|FCC|RoHS|ISO)\s*[- ]?(?:certified|compliant)\b|\b(?:certified|compliant)\s+(?:to|with|under)\b|\b(?:fits?|compatible with|works? with)\s+(?:every|all|any)\b|\buniversal(?:ly)?\s+(?:fit|compatible)\b|\b(?:in stock|inventory available|available from stock|ships? within|lead time (?:is|of)|delivery within)\b/i;
const PRODUCT_CLAIM_SUBJECT_PATTERN = /\b(?:product|motor|drive|system|candidate|unit|sku|model|series|solution|equipment|machine|assembly|component)\b/i;

function buyerVisibleHighRiskProductClaims(draft) {
  // Preserve line/table-row boundaries before sentence matching. Flattening the
  // whole Markdown body can join a numeric input example in one table row to a
  // product subject in the following row/prose and fabricate a claim that no
  // buyer can actually read as one statement.
  return String(draft.body || '').split(/\n+/u)
    .flatMap((line) => (line.includes('|')
      ? line.trim().replace(/^\||\|$/g, '').split('|')
      : [line]))
    .flatMap((segment) => markdownPlainText(segment).match(/[^.!?。！？]+[.!?。！？]?/g) || [])
    .map((sentence) => sentence.trim())
    .filter(Boolean)
    .filter((sentence) => !PRODUCT_CLAIM_NEGATION_PATTERN.test(sentence)
      && (DIRECT_HIGH_RISK_PRODUCT_CLAIM_PATTERN.test(sentence)
        || (PRODUCT_CLAIM_SUBJECT_PATTERN.test(sentence) && HIGH_RISK_PRODUCT_CLAIM_PATTERN.test(sentence))));
}

function validateBuyerVisibleProductClaimLedger(brief, draft, publish, evidenceScope, evidenceRoot, problems) {
  for (const field of ['product_claim_ledger_applicability', 'product_claim_ledger_not_applicable_reason', 'product_claim_ledger', 'product_claim_ledger_verdict']) {
    requireCanonicalMatch([brief, publish], field, problems, field, field === 'product_claim_ledger' ? 'exact-sequence' : '');
  }
  const claims = buyerVisibleHighRiskProductClaims(draft);
  const applicability = normalizeText(string(brief, 'product_claim_ledger_applicability', problems));
  const reason = string(brief, 'product_claim_ledger_not_applicable_reason', problems);
  const rows = strings(brief, 'product_claim_ledger', problems, { allowEmpty: true });
  const verdict = normalizeText(string(brief, 'product_claim_ledger_verdict', problems));

  if (!['applicable', 'not-applicable'].includes(applicability)) {
    fail(problems, `${brief.source} product_claim_ledger_applicability must be applicable or not-applicable`);
  }
  if (!['pass', 'block', 'not-applicable'].includes(verdict)) {
    fail(problems, `${brief.source} product_claim_ledger_verdict must be pass, block, or not-applicable`);
  }

  if (applicability === 'not-applicable') {
    if (rows.length) fail(problems, `${brief.source} not-applicable product_claim_ledger must be empty`);
    if (verdict !== 'not-applicable') fail(problems, `${brief.source} not-applicable product_claim_ledger requires product_claim_ledger_verdict=not-applicable`);
    meaningfulScalar(reason, brief.source, 'product_claim_ledger_not_applicable_reason', problems, { minLength: 24 });
    if (normalizeText(reason) === 'not-applicable') fail(problems, `${brief.source} not-applicable product_claim_ledger requires a concrete non-empty reason`);
    if (claims.length) fail(problems, `${draft.source} buyer-visible certification, compliance, universal-fit, compatibility, performance, continuous-rating, durability, capacity, production-capability, inventory, lead-time, or SKU-suitability claim makes product_claim_ledger applicable`);
    return;
  }

  if (normalizeText(reason) !== 'not-applicable') fail(problems, `${brief.source} applicable product_claim_ledger requires product_claim_ledger_not_applicable_reason=not-applicable`);
  if (!rows.length) fail(problems, `${brief.source} applicable product_claim_ledger must contain at least one claim row`);
  if (verdict !== 'pass') fail(problems, `${brief.source} applicable product_claim_ledger requires product_claim_ledger_verdict=pass`);

  const coveredClaims = [];
  const claimIds = new Set();
  for (const row of rows) {
    const parts = String(row).split('|').map((part) => part.trim());
    if (parts.length !== 8 || parts.some((part) => !part)) {
      fail(problems, `${brief.source} product_claim_ledger row must use claim-id|buyer-visible-claim|claim-type|evidence-ref|applicability-boundary|target-url-or-not-applicable|target-page-parity-status|production-use-status: ${row}`);
      continue;
    }
    const [claimId, claimText, claimTypeRaw, evidenceRef, applicabilityBoundary, targetPage, targetPageParityRaw, productionUseStatusRaw] = parts;
    const normalizedClaimId = normalizeText(claimId);
    const claimType = normalizeText(claimTypeRaw);
    const targetPageParity = normalizeText(targetPageParityRaw);
    const productionUseStatus = normalizeText(productionUseStatusRaw);
    if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{5,127}$/.test(claimId) || PLACEHOLDER_PATTERN.test(claimId)) fail(problems, `${brief.source} product_claim_ledger claim-id must be stable and non-placeholder: ${claimId}`);
    if (claimIds.has(normalizedClaimId)) fail(problems, `${brief.source} product_claim_ledger contains duplicate claim-id ${claimId}`);
    claimIds.add(normalizedClaimId);
    meaningfulScalar(claimText, brief.source, `product_claim_ledger ${claimId} buyer-visible-claim`, problems, { minLength: 16 });
    if (!PRODUCT_CLAIM_TYPES.has(claimType)) fail(problems, `${brief.source} product_claim_ledger ${claimId} claim-type is unsupported: ${claimTypeRaw}`);
    meaningfulScalar(applicabilityBoundary, brief.source, `product_claim_ledger ${claimId} applicability-boundary`, problems, { minLength: 16 });
    if (!PRODUCT_CLAIM_PRODUCTION_STATUSES.has(productionUseStatus)) fail(problems, `${brief.source} product_claim_ledger ${claimId} production-use-status must be production-supported, synthetic-only, or not-applicable-for-production`);
    if (evidenceScope === 'production' && productionUseStatus !== 'production-supported') fail(problems, `${brief.source} production product_claim_ledger ${claimId} requires production-use-status=production-supported`);

    const resolved = validateLocalEvidenceRefs([evidenceRef], brief.source, `product_claim_ledger ${claimId} evidence-ref`, evidenceRoot, problems, { requireFragment: true, regularNonSymlink: true, verifyFragment: true });
    if (evidenceScope === 'production') rejectSyntheticEvidenceFiles(resolved, brief.source, `product_claim_ledger ${claimId} evidence-ref`, problems);
    const section = loadReferencedSection(evidenceRef, evidenceRoot);
    if (!section || semanticOverlap(`${claimText} ${applicabilityBoundary}`, markdownPlainText(section)).length < 3) fail(problems, `${brief.source} product_claim_ledger ${claimId} evidence-ref must materially support the claim and applicability boundary`);

    if (normalizeText(targetPage) === 'not-applicable') {
      if (targetPageParity !== 'not-applicable') fail(problems, `${brief.source} product_claim_ledger ${claimId} without a target URL requires target-page-parity-status=not-applicable`);
    } else {
      requireAbsoluteHttpsUrl(targetPage, brief.source, `product_claim_ledger ${claimId} target-url`, problems);
      if (targetPageParity !== 'pass') fail(problems, `${brief.source} product_claim_ledger ${claimId} with a target URL requires target-page-parity-status=pass`);
      if (!section || !normalizeText(markdownPlainText(section)).includes(normalizeText(targetPage))) fail(problems, `${brief.source} product_claim_ledger ${claimId} target-page parity must be bound in the referenced evidence section`);
    }

    if (!normalizeText(markdownPlainText(draft.body)).includes(normalizeText(claimText))) fail(problems, `${draft.source} product_claim_ledger buyer-visible-claim must appear exactly in the publishable body: ${claimId}`);
    coveredClaims.push(claimText);
  }
  for (const claim of claims) {
    const claimTokens = new Set(semanticTokens(claim));
    const covered = coveredClaims.some((ledgerClaim) => normalizeText(claim).includes(normalizeText(ledgerClaim))
      || normalizeText(ledgerClaim).includes(normalizeText(claim))
      || semanticOverlap(claim, ledgerClaim).length >= Math.min(4, Math.max(2, claimTokens.size)));
    if (!covered) fail(problems, `${draft.source} buyer-visible high-risk product claim lacks product_claim_ledger evidence, applicability boundary, target-page parity, and production-use status: ${claim}`);
  }
}

function validateUnsupportedOutcomeClaims(draft, problems) {
  const surfaces = [
    ['body', markdownPlainText(draft.body)],
    ['article_title', string(draft, 'article_title', problems)],
    ['meta_description', string(draft, 'meta_description', problems)],
    ['excerpt', string(draft, 'excerpt', problems)],
  ];
  for (const [surface, text] of surfaces) for (const rawSentence of (String(text || '').match(/[^.!?。！？]+[.!?。！？]?/g) || []).map((value) => value.trim()).filter(Boolean)) {
    const sentence = securityCanonicalText(rawSentence);
    const clauses = sentence.split(/\s*(?:;|—|–|\bbut\b|\byet\b|\bhowever\b|\bwhereas\b|\balthough\b|\bwhile\b|\bplus\b|\band\b(?=\s+(?:will|shall|guarantee|ensure|establish|prove|increase|boost|improve|raise|grow|double|triple|drive|generate|deliver|create|produce|secure|win|lift|yield|bring|gain|achieve|rank)))\s*/i);
    for (const clause of clauses.map((value) => value.trim()).filter(Boolean)) {
      if (!UNSUPPORTED_OUTCOME_CLAIM_PATTERNS.some((pattern) => pattern.test(clause))) continue;
      const directlyNegated = /\b(?:does not|do not|cannot|can't|will not|won't|never|not|no)\s+(?:\w+\s+){0,3}(?:guarantee|ensure|establish|prove|increase|boost|improve|raise|grow|double|triple|drive|generate|deliver|create|produce|secure|win|lift|yield|bring|gain|achieve|rank)\w*\b/i.test(clause)
        || /\b(?:no guarantee|not guaranteed|remains? unverified|not verified|has not been verified|cannot be inferred)\b.{0,70}\b(?:rank|first[ -]page|qualified inquir|lead|conversion|revenue|sales)\w*\b/i.test(clause)
        || /\bno\b.{0,100}\b(?:rank(?:ing)?s?|first[ -]page|qualified inquir(?:y|ies)|leads?|conversion(?: rate)?s?|revenue|sales)\b.{0,80}\b(?:has|have|is|are|remains?)\s+(?:not\s+)?verified\b/i.test(clause)
;
      if (!directlyNegated) {
        fail(problems, `${draft.source} ${surface} contains an unsupported ranking, inquiry, or conversion outcome claim: ${clause}`);
      }
    }
  }
}

function parseDecisionTable(table) {
  const lines = String(table || '').split('\n').filter((line) => /^\s*\|/.test(line));
  if (lines.length < 3) return null;
  const parseCells = (line) => line.trim().replace(/^\||\|$/g, '').split('|').map((cell) => normalizeText(cell.replace(/[*`]/g, '')));
  const headers = parseCells(lines[0]);
  const rows = lines.slice(2).map(parseCells).filter((cells) => cells.length === headers.length);
  return { headers, rows };
}

function validateMaterialDecisionTable(table, source, problems, label = 'comparison/decision table') {
  const parsed = parseDecisionTable(table);
  if (!parsed || parsed.headers.length < 3) {
    fail(problems, `${source} ${label} must contain one criterion column and at least two candidate columns`);
    return false;
  }
  const { headers, rows } = parsed;
  const candidateIndexes = headers.slice(1).map((_, index) => index + 1);
  const placeholder = /^(?:to be supplied|not supplied|tbd|todo|unknown|n\/?a|none|placeholder|fill in|buyer to supply|same|identical|pending)$/i;
  let valid = true;
  for (let leftOffset = 0; leftOffset < candidateIndexes.length - 1; leftOffset += 1) {
    for (let rightOffset = leftOffset + 1; rightOffset < candidateIndexes.length; rightOffset += 1) {
      const leftIndex = candidateIndexes[leftOffset];
      const rightIndex = candidateIndexes[rightOffset];
      const usable = rows.filter((row) => {
        const left = row[leftIndex] || '';
        const right = row[rightIndex] || '';
        return left.length >= 2 && right.length >= 2 && !placeholder.test(left) && !placeholder.test(right) && left !== right;
      });
      if (rows.length < 2 || usable.length < Math.max(2, Math.ceil(rows.length * 0.6))) {
        fail(problems, `${source} ${label} candidate columns ${headers[leftIndex] || leftIndex} and ${headers[rightIndex] || rightIndex} must contain enough materially different non-placeholder evidence; use a separately labeled buyer-input worksheet when evidence is unavailable`);
        valid = false;
      }
    }
  }
  return valid;
}

function validateDecisionTables(draft, problems) {
  const lines = draft.body.split('\n');
  for (let index = 0; index < lines.length - 2; index += 1) {
    if (!/^\s*\|/.test(lines[index]) || !/^\s*\|?\s*:?-{3,}/.test(lines[index + 1])) continue;
    let cursor = index + 2;
    while (cursor < lines.length && /^\s*\|/.test(lines[cursor])) cursor += 1;
    const table = lines.slice(index, cursor).join('\n');
    const parsed = parseDecisionTable(table);
    if (!parsed || parsed.headers.length < 3) { index = cursor - 1; continue; }
    const firstHeader = parsed.headers[0] || '';
    const precedingHeading = [...lines.slice(0, index)].reverse().find((line) => /^#{1,6}\s+/.test(line)) || '';
    const candidateHeaders = parsed.headers.slice(1);
    const looksLikeDecisionTable = /\b(?:criterion|criteria|factor|dimension|requirement|attribute|condition|decision|evidence|buyer input|input)\b/i.test(firstHeader)
      || candidateHeaders.filter((header) => /\b(?:candidate|option|product|solution|model)\b/i.test(header)).length >= 2
      || /\b(?:compare|comparison|decision table|selection matrix|versus|\bvs\b)\b/i.test(precedingHeading);
    if (looksLikeDecisionTable) validateMaterialDecisionTable(table, draft.source, problems);
    index = cursor - 1;
  }
}

function validateVisibleProductDecisionMap(rows, draft, problems) {
  const bodyText = markdownPlainText(draft.body);
  if (!/\b(?:evidence|proof|source|test|validation|measured|record|data|assumption|boundary)\w*\b/i.test(bodyText)) {
    fail(problems, `${draft.source} Draft must visibly state product-decision evidence or its validation boundary`);
  }
  for (const row of rows) {
    for (const [label, value] of [
      ['prerequisite/buyer condition', row.buyerCondition],
      ['decision variable', row.decisionVariable],
      ['candidate direction', row.candidate],
      ['no-fit condition', row.noFitCondition],
      ['remaining inputs', row.remainingInputs],
    ]) {
      const tokens = [...new Set(significantTokens(value))];
      const overlap = semanticOverlap(value, bodyText);
      const requiredOverlap = Math.max(2, Math.ceil(tokens.length * 0.6));
      if (overlap.length < Math.min(tokens.length, requiredOverlap)) {
        fail(problems, `${draft.source} Draft does not visibly implement product decision map ${label}: ${value}`);
      }
    }
  }
  validateDecisionTables(draft, problems);
}

function validateBuyerArticleSemanticStructure(brief, draft, ctaDestination, ctaContract, problems) {
  const dominantTask = parseDominantTaskContract(brief, problems).value;
  const dominantSearchIntent = string(brief, 'dominant_search_intent', problems);
  const directAnswer = requireMeaningfulString(draft, 'direct_answer', problems, { minLength: 18 });
  const bodyText = markdownPlainText(draft.body);
  if (!bodyText || hasLowEntropy(bodyText)) {
    fail(problems, `${draft.source} buyer article body must contain non-low-entropy semantic content`);
    return;
  }
  const directAnswerTokens = [...new Set(significantTokens(directAnswer))];
  const directTaskOverlap = semanticOverlap(directAnswer, `${dominantTask} ${dominantSearchIntent}`);
  if (!/[.!?。！？]$/.test(directAnswer.trim())
    || !DIRECT_ANSWER_JUDGMENT_PATTERN.test(directAnswer)
    || directAnswerTokens.length < 4
    || directTaskOverlap.length < 2) {
    fail(problems, `${draft.source} direct_answer must be a concrete bounded judgment sentence`);
  }
  const normalizedAnswer = normalizeText(directAnswer).replace(/[.!?。！？]+$/u, '');
  const materiallyRestates = (text) => {
    if (normalizeText(text).includes(normalizedAnswer)) return true;
    const answerTokens = [...new Set(significantTokens(directAnswer))];
    return (text.match(/[^.!?。！？]+[.!?。！？]?/g) || []).some((sentence) => {
      const overlap = semanticOverlap(directAnswer, sentence).length;
      const required = Math.max(4, Math.ceil(answerTokens.length * 0.4));
      return overlap >= Math.min(answerTokens.length, required)
        && DIRECT_ANSWER_JUDGMENT_PATTERN.test(sentence)
        && /\b(?:before|when|if|unless|under|within|without|only|after|otherwise)\b/i.test(sentence);
    });
  };
  if (!materiallyRestates(bodyText)) fail(problems, `${draft.source} direct_answer must be visibly stated or strongly restated in the Draft body`);
  const completeOpeningBlock = markdownPlainText(draft.body.split(/^##\s+/m)[0]);
  if (!materiallyRestates(completeOpeningBlock)) fail(problems, `${draft.source} direct_answer must appear, or be materially restated, within the complete opening block before the first H2; a keyword bag is not a material restatement`);
  const taskTokens = new Set(significantTokens(dominantTask));
  const answerTokens = new Set(significantTokens(directAnswer));
  const overlap = [...taskTokens].filter((token) => answerTokens.has(token));
  if (taskTokens.size && overlap.length < Math.min(2, taskTokens.size)) {
    fail(problems, `${draft.source} direct answer must materially address dominant_task_contract; terms elsewhere in the body cannot substitute for the answer`);
  }
  const sections = draft.body.split(/^##\s+/m).slice(1);
  const hasCompleteDecisionSection = sections.some((section) => {
    const plain = markdownPlainText(section);
    return /\b(?:if|when|before|after|unless|under|once|until|without)\b/i.test(plain)
      && /\b(?:choose|select|shortlist|compare|validate|reject|qualify|request|decide|define|complete)\w*\b/i.test(plain)
      && /\b(?:evidence|proof|test|validation|boundary|assumption|unresolved|cannot|does not prove|must verify)\w*\b/i.test(plain);
  });
  if (!hasCompleteDecisionSection) {
    fail(problems, `${draft.source} buyer article requires at least one H2 decision path with condition + action + evidence/boundary`);
  }
  const destinationVerified = ctaDestination !== 'not-applicable';
  const escapedDestination = ctaDestination.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const ctaLink = destinationVerified ? new RegExp(`\\[[^\\]]+\\]\\(${escapedDestination}\\)`, 'i').exec(draft.body) : null;
  if (destinationVerified && !ctaLink) {
    fail(problems, `${draft.source} CTA block must contain the declared destination link`);
    return;
  }
  const preparationIndex = Math.max(draft.body.lastIndexOf('## Prepare the engineering packet'), draft.body.lastIndexOf('### What to send'), 0);
  const ctaAnchor = ctaLink?.index ?? preparationIndex;
  const beforeLink = draft.body.slice(0, ctaAnchor);
  const precedingH2s = [...beforeLink.matchAll(/^##\s+/gm)];
  const ctaSectionStart = precedingH2s.length ? precedingH2s.at(-1).index : Math.max(0, ctaAnchor - 1200);
  const afterLink = draft.body.slice(ctaAnchor + (ctaLink?.[0].length || 0));
  const nextH2 = /^##\s+/m.exec(afterLink);
  const ctaSectionEnd = nextH2 ? ctaAnchor + (ctaLink?.[0].length || 0) + nextH2.index : draft.body.length;
  const fallbackCtaSection = primaryCtaSectionForStage(
    draft.body,
    normalizeText(string(brief, 'stage', problems)),
    ['inline-no-input', 'local-tool'].includes(normalizeText(string(brief, 'cta_interaction_type', problems))),
  );
  const ctaSectionMarkdown = destinationVerified ? draft.body.slice(ctaSectionStart, ctaSectionEnd) : fallbackCtaSection;
  const nearby = markdownPlainText(ctaSectionMarkdown);
  const visibleCtaLabels = [
    ['trigger', /(?:^|\n)(?:[-*]\s*)?(?:(?:\*\*)?trigger\s*:(?:\*\*)?|(?:use (?:this|the final) CTA|request review) only when\b|#{3,6}\s+when to request(?: the review)?\b)|\bwhen (?:the )?(?:local )?worksheet is complete\b/im],
    ['required inputs', /(?:^|\n)(?:(?:[-*]\s*)?(?:\*\*)?required inputs\s*:(?:\*\*)?|#{3,6}\s+what to send\b)|\b(?:local|readiness) worksheet\b/im],
    ['expected output', /(?:^|\n)(?:(?:[-*]\s*)?(?:\*\*)?expected output\s*:(?:\*\*)?|#{3,6}\s+what (?:the )?(?:(?:technical owner|applications engineering) )?(?:should )?return\b)|\b(?:expected engineering output|requested review output)\b/im],
    ['validation boundary', /(?:^|\n)(?:(?:[-*]\s*)?(?:\*\*)?validation boundary\s*:(?:\*\*)?|#{3,6}\s+validation boundary\b)/im],
  ];
  for (const [label, pattern] of visibleCtaLabels) {
    if (!pattern.test(ctaSectionMarkdown)) {
      fail(problems, `${draft.source} visible CTA must include an explicit ${label} label`);
    }
  }
  if (!/\b(?:when|if|once|ready|send|provide|complete|request)\w*\b/i.test(nearby)) {
    fail(problems, `${draft.source} CTA block must state a concrete trigger or next action, not only render a link`);
  }
  for (const [label, value, minimum] of [
    ['trigger', ctaContract.trigger, 2],
    ['expected output', ctaContract.expectedOutput, 2],
    ['validation boundary', ctaContract.boundary, 2],
  ]) {
    if (semanticOverlap(value, nearby).length < minimum) {
      fail(problems, `${draft.source} visible CTA must cover its ${label}`);
    }
  }
  const visibleInputs = ctaContract.inputs.filter((input) => semanticOverlap(input, nearby).length > 0);
  const fallbackTemplate = string(brief, 'cta_fallback_message_template', problems);
  const exactFallbackPacket = ctaContract.inputs.every((input) => normalizeText(fallbackTemplate).includes(normalizeText(input))) || /\b(?:single|completed|prepared|local|readiness)\s+worksheet\b/i.test(fallbackTemplate);
  const referencesPreparedWorksheet = /\b(?:local|readiness) worksheet\b/i.test(nearby);
  if (visibleInputs.length < Math.max(3, Math.ceil(ctaContract.inputs.length * 0.6)) && !(exactFallbackPacket && referencesPreparedWorksheet)) {
    fail(problems, `${draft.source} visible CTA must cover the required inquiry inputs directly or reference the prepared worksheet while the sole copyable fallback carries the exact packet`);
  }
  validateNoRepeatedFullSentences(draft, problems);
}

function checkAllinCmsFormats(draft, review, problems) {
  const profile = { features: new Set(), links: [] };
  try {
    // AllinCMS image binding is a separate adapter operation. Strip only
    // syntactically valid Markdown images for text-format conversion, then
    // validate their asset binding, alt, source, and semantics fail-closed.
    const converterMarkdown = draft.body.replace(/!\[([^\]\n]*)\]\((https:\/\/[^)\s]+)(?:\s+["'][^"']*["'])?\)/g, '$1');
    const nodes = markdownToAllinCmsSlate(converterMarkdown, { idPrefix: 'article-package-check' });
    profile.features = collectAllinCmsFormatFeatures(nodes);
    profile.links = collectAllinCmsLinks(nodes);
    for (const feature of profile.features) {
      if (ALLINCMS_UNSUPPORTED.has(feature) || !ALLINCMS_FORMATS.has(feature)) {
        fail(problems, `${draft.source} actual Markdown feature ${feature} is not supported by the canonical AllinCMS tested-format profile`);
      }
    }
  } catch (error) {
    fail(problems, `${draft.source} AllinCMS Markdown-to-Slate validation failed: ${error.message}`);
  }
  return profile;
}

const INTENT_CLASSES = new Set(['informational', 'troubleshooting', 'commercial-investigation', 'mixed-commercial', 'transactional']);
const TASK_STAGES = new Set(['learn', 'compare', 'validate', 'buy', 'troubleshoot']);
const COMMERCIAL_COMMITMENTS = new Set(['none', 'soft', 'commercial']);
const COMMERCIAL_ACTION_PATTERN = /\b(?:authori[sz]e|award|nominate|appoint|contract|allocate(?:\s+the)?\s+spend|approve(?:\s+the)?\s+(?:budget|spend)|issue(?:\s+an?)?\s+(?:rfq|purchase order)|place(?:\s+an?)?\s+order|select(?:\s+the)?\s+supplier|commit(?:\s+the)?\s+budget|buy|purchase)\w*\b/i;
const COMMERCIAL_TERMINAL_ACTION_PATTERN = /\b(?:nominate|appoint|award|authorize|contract|select\s+(?:the\s+)?supplier|issue\s+(?:an?\s+)?(?:rfq|purchase order)|place\s+(?:(?:an?|the)\s+)?(?:(?:supplier|purchase)\s+)?order|request\s+(?:(?:an?|the)\s+)?binding\s+(?:quote|quotation)|approve\s+(?:the\s+)?(?:budget|spend)|commit\s+(?:the\s+)?budget|buy|purchase|program\s+nomination|manufacturing\s+partner|supply\s+partner|preferred\s+source)\b/i;
const CANONICAL_EVIDENCE_EXECUTIONS = new Set(['not-run', 'executed', 'not-applicable']);
const CANONICAL_EVIDENCE_RESULTS = new Set(['missing', 'synthetic-only', 'confirmed', 'failed', 'not-applicable']);
const CANONICAL_GATE_VERDICTS = new Set(['pass', 'block', 'not-applicable']);
const CTA_FALLBACK_ROUTE_STATUSES = new Set(['verified', 'unverified-unavailable', 'not-applicable']);
const CTA_FALLBACK_REQUIRED_INPUT_MODES = new Set(['same-as-cta-required-inputs', 'none']);
const CONTENT_TYPE_FAMILY_PATTERNS = [
  ['calculator', /\b(?:calculator|estimator|calculation|sizing tool|roi tool|cost model)\b/i],
  ['diagnostic', /\b(?:diagnostic|diagnosis|troubleshoot(?:ing)?|root[- ]cause|fault[- ]isolation|failure analysis)\b/i],
  ['checklist', /\b(?:checklist|check list|readiness check|audit checklist|inspection checklist)\b/i],
  ['comparison', /\b(?:comparison|compare|versus|vs\.?|matrix|decision table|selection table)\b/i],
  ['case-study', /\b(?:case study|customer story|success story|implementation story|project story)\b/i],
  ['product-landing', /\b(?:product(?: page)?|category(?: page| hub)?|landing page|solution page|product hub|collection page)\b/i],
  ['guide', /\b(?:guide|how[- ]to|tutorial|playbook|step[- ]by[- ]step|handbook|explainer)\b/i],
];

function normalizedRoleList(record, problems) {
  const primary = requireCanonicalBuyerRole(string(record, 'primary_buyer_role', problems), record.source, 'primary_buyer_role', problems, { canonicalOnly: true });
  const secondary = strings(record, 'secondary_buyer_roles', problems, { allowEmpty: true }).map((role) => requireCanonicalBuyerRole(role, record.source, 'secondary_buyer_roles', problems, { canonicalOnly: true }));
  const all = [primary, ...secondary].filter(Boolean);
  const normalized = all.map(normalizeText);
  if (!primary) fail(problems, `${record.source} primary_buyer_role is required`);
  if (new Set(normalized).size !== normalized.length) fail(problems, `${record.source} primary and secondary buyer roles must be distinct`);
  return { primary, secondary, all };
}

function parseDominantTaskContract(record, problems) {
  const value = requireMeaningfulString(record, 'dominant_task_contract', problems, { minLength: 16 });
  const parts = value.split('|').map((part) => part.trim());
  if (parts.length !== 5 || parts.some((part) => !part)) {
    fail(problems, `${record.source} dominant_task_contract must use action|decision_object|expected_output|stage|commercial_commitment`);
    return { value, action: '', decisionObject: '', expectedOutput: '', stage: '', commitment: '' };
  }
  const [action, decisionObject, expectedOutput, stage, commitment] = parts;
  meaningfulScalar(action, record.source, 'dominant_task_contract action', problems, { minLength: 4 });
  meaningfulScalar(decisionObject, record.source, 'dominant_task_contract decision_object', problems, { minLength: 8 });
  meaningfulScalar(expectedOutput, record.source, 'dominant_task_contract expected_output', problems, { minLength: 8 });
  const rawStage = stage.trim();
  const rawCommitment = commitment.trim();
  if (!TASK_STAGES.has(rawStage)) fail(problems, `${record.source} dominant_task_contract stage must be exact lowercase learn|troubleshoot|compare|validate|buy`);
  if (!COMMERCIAL_COMMITMENTS.has(rawCommitment)) fail(problems, `${record.source} dominant_task_contract commercial_commitment must be exact lowercase none|soft|commercial`);
  if (rawStage !== string(record, 'stage', problems)) fail(problems, `${record.source} dominant_task_contract stage must exactly match stage`);
  if (rawCommitment !== string(record, 'commercial_commitment', problems)) fail(problems, `${record.source} dominant_task_contract commercial_commitment must exactly match commercial_commitment`);
  const taskCommercial = commercialClassification(`${action} ${decisionObject} ${expectedOutput}`);
  if (rawCommitment === 'none' && taskCommercial.commercial) fail(problems, `${record.source} dominant_task_contract mixes commercial vocabulary with commercial_commitment=none`);
  if (rawStage !== 'buy' && taskCommercial.terminal) fail(problems, `${record.source} noncommercial-stage dominant_task_contract must not contain a terminal commercial action, partner appointment, preferred-source decision, or program nomination`);
  return { value, action, decisionObject, expectedOutput, stage, commitment };
}

function validateLanguageQueryIntent(records, problems) {
  for (const record of records) {
    const languages = strings(record, 'supported_content_languages', problems);
    if (languages.length !== 1 || normalizeText(languages[0]) !== 'en') fail(problems, `${record.source} English-only package requires supported_content_languages=[en]`);
    if (normalizeText(string(record, 'target_content_language', problems)) !== 'en') fail(problems, `${record.source} English-only package requires target_content_language=en`);
    requireMeaningfulString(record, 'primary_query', problems, { minLength: 8 });
  }
  const primary = normalizeText(string(records[0], 'primary_query', problems));
  for (const record of records.slice(1)) if (normalizeText(string(record, 'primary_query', problems)) !== primary) fail(problems, `${record.source} primary_query must match the Brief`);
  const supporting = requireDistinctMeaningfulArray(records[0], 'supporting_query_variants', problems, { minItems: 1, minLength: 8 });
  const excluded = requireDistinctMeaningfulArray(records[0], 'excluded_query_modifiers', problems, { minItems: 1, minLength: 2 });
  if (supporting.some((query) => normalizeText(query) === primary)) fail(problems, `${records[0].source} supporting_query_variants must not duplicate primary_query`);
  const intent = string(records[0], 'intent_class', problems);
  if (!INTENT_CLASSES.has(intent)) fail(problems, `${records[0].source} intent_class must be exact lowercase informational|troubleshooting|commercial-investigation|mixed-commercial|transactional`);
  for (const record of records.slice(1)) if (string(record, 'intent_class', problems) !== intent) fail(problems, `${record.source} intent_class must exactly match the Brief`);
  for (const record of records) {
    const stage = string(record, 'stage', problems);
    const commitment = string(record, 'commercial_commitment', problems);
    if (!TASK_STAGES.has(stage)) fail(problems, `${record.source} stage must be exact lowercase learn|troubleshoot|compare|validate|buy`);
    if (!COMMERCIAL_COMMITMENTS.has(commitment)) fail(problems, `${record.source} commercial_commitment must be exact lowercase none|soft|commercial`);
  }
  for (const query of [primary, ...supporting]) for (const modifier of excluded) if (normalizeText(query).includes(normalizeText(modifier))) fail(problems, `${records[0].source} query contract mixes excluded modifier ${modifier}`);
  const contract = parseDominantTaskContract(records[0], problems);
  const dominantSearchIntent = requireMeaningfulString(records[0], 'dominant_search_intent', problems, { minLength: 16 });
  rejectPackedEnumeration(dominantSearchIntent, records[0].source, 'dominant_search_intent', problems);
  validateSingleDominantTask(dominantSearchIntent, records[0].source, 'dominant_search_intent', problems);
  const canonicalStage = string(records[0], 'stage', problems);
  const canonicalCommitment = string(records[0], 'commercial_commitment', problems);
  const classifiedIntent = commercialClassification(dominantSearchIntent);
  if (canonicalCommitment === 'none' && classifiedIntent.commercial) {
    fail(problems, `${records[0].source} noncommercial dominant_search_intent with commercial_commitment=none must not contain sourcing, bid, tender, proposal, quotation, pricing, procurement, purchase, partner appointment, preferred-source, nomination, or award actions`);
  }
  if (canonicalStage !== 'buy' && classifiedIntent.terminal) {
    fail(problems, `${records[0].source} noncommercial-stage dominant_search_intent must not contain a terminal commercial action or output`);
  }
  for (const record of records.slice(1)) {
    const other = parseDominantTaskContract(record, problems);
    if (normalizeText(other.value) !== normalizeText(contract.value)) fail(problems, `${record.source} dominant_task_contract must match the Brief`);
    if ('dominant_search_intent' in record.attributes) {
      const otherIntent = requireMeaningfulString(record, 'dominant_search_intent', problems, { minLength: 16 });
      rejectPackedEnumeration(otherIntent, record.source, 'dominant_search_intent', problems);
      validateSingleDominantTask(otherIntent, record.source, 'dominant_search_intent', problems);
      if (normalizeText(otherIntent) !== normalizeText(dominantSearchIntent)) fail(problems, `${record.source} dominant_search_intent must exactly match the Brief`);
    }
  }
  for (const field of ['market_information_gain_status', 'information_gain_artifact_status']) {
    const canonicalValue = normalizeText(string(records[0], field, problems));
    for (const record of records.slice(1)) {
      if (normalizeText(string(record, field, problems)) !== canonicalValue) fail(problems, `${record.source} ${field} must match the Brief`);
    }
  }
  for (const field of ['role_handoff_contracts', 'inventory_zero_result_evidence_refs']) {
    const canonicalValues = strings(records[0], field, problems, { allowEmpty: true });
    for (const record of records.slice(1)) {
      if (!sameNormalizedSet(strings(record, field, problems, { allowEmpty: true }), canonicalValues)) fail(problems, `${record.source} ${field} must match the Brief`);
    }
  }
  return contract;
}

function expectedStageIntakeContract(stage, intent) {
  if (stage === 'compare') return intent === 'mixed-commercial' ? 'compare-handoff' : 'none';
  if (stage === 'troubleshoot') return '';
  return STAGE_DEFAULT_INTAKE_CONTRACT.get(stage) || '';
}

function validateSecondRoundInputRelationships(record, firstRound, secondRound, problems) {
  const rows = strings(record, 'second_round_input_relationships', problems, { allowEmpty: true });
  if (!secondRound.length) {
    if (rows.length) fail(problems, `${record.source} second_round_input_relationships must be empty when second_round_inquiry_inputs is empty`);
    return;
  }
  const parsed = [];
  for (const row of rows) {
    const parts = row.split('|').map((part) => part.trim());
    if (parts.length !== 4 || parts.some((part) => !part)) {
      fail(problems, `${record.source} second_round_input_relationships row must use second_round_item|new-or-refines|first_round_item-or-not-applicable|additional_decision_purpose: ${row}`);
      continue;
    }
    const [secondItem, relationship, firstItem, purpose] = parts;
    const normalizedRelationship = normalizeText(relationship);
    if (!SECOND_ROUND_RELATIONSHIP_MODES.has(normalizedRelationship)) fail(problems, `${record.source} second-round relationship must be exact new or refines: ${relationship}`);
    if (normalizeText(secondItem) === normalizeText(firstItem)) fail(problems, `${record.source} second-round intake must not request the same value again: ${secondItem}`);
    if (normalizedRelationship === 'new' && normalizeText(firstItem) !== 'not-applicable') fail(problems, `${record.source} new second-round item requires first_round_item-or-not-applicable=not-applicable`);
    if (normalizedRelationship === 'refines') {
      if (!firstRound.some((value) => normalizeText(value) === normalizeText(firstItem))) fail(problems, `${record.source} refines relationship must point to one exact first_round_inquiry_inputs item: ${firstItem}`);
      if (semanticOverlap(secondItem, firstItem).length < 1) fail(problems, `${record.source} refines relationship must show a real summary-to-detail semantic connection: ${secondItem}`);
    }
    meaningfulScalar(purpose, record.source, 'second_round_input_relationships additional_decision_purpose', problems, { minLength: 12 });
    parsed.push(secondItem);
  }
  if (!sameNormalizedSet(parsed, secondRound) || parsed.length !== secondRound.length) fail(problems, `${record.source} second_round_input_relationships must contain exactly one row for every second_round_inquiry_inputs item`);
}

function validateStageSpecificIntake(records, problems) {
  const brief = records[0];
  const stage = normalizeText(string(brief, 'stage', problems));
  const intent = normalizeText(string(brief, 'intent_class', problems));
  const intake = normalizeText(string(brief, 'stage_intake_contract', problems));
  if (!STAGE_INTAKE_CONTRACTS.has(intake)) fail(problems, `${brief.source} stage_intake_contract must be none|troubleshoot-support|compare-handoff|validate-technical|buy-commercial`);
  requireCanonicalMatch(records, 'stage_intake_contract', problems);
  requireCanonicalMatch(records, 'second_round_input_relationships', problems);
  const expected = expectedStageIntakeContract(stage, intent);
  if (expected && intake !== expected) fail(problems, `${brief.source} stage=${stage} intent_class=${intent} requires stage_intake_contract=${expected}; received ${intake}`);
  if (stage === 'troubleshoot' && !['none', 'troubleshoot-support'].includes(intake)) {
    fail(problems, `${brief.source} stage=troubleshoot requires stage_intake_contract=none or troubleshoot-support; received ${intake}`);
  }

  const firstRound = strings(brief, 'first_round_inquiry_inputs', problems, { allowEmpty: true });
  const secondRound = strings(brief, 'second_round_inquiry_inputs', problems, { allowEmpty: true });
  const requiredInputs = strings(brief, 'required_inquiry_inputs', problems, { allowEmpty: true });
  const ctaInputs = strings(brief, 'cta_required_inputs', problems, { allowEmpty: true });
  const omittedInputs = strings(brief, 'cta_progressive_profiling_omitted_inputs', problems, { allowEmpty: true });
  const technicalGates = strings(brief, 'technical_qualification_gates', problems, { allowEmpty: true });
  const salesGates = strings(brief, 'sales_acceptance_gates', problems, { allowEmpty: true });
  const recordWithField = (field) => records.find((record) => field in record.attributes);
  const arrayFromAnyRecord = (field) => {
    const record = recordWithField(field);
    return record ? strings(record, field, problems, { allowEmpty: true }) : [];
  };
  const salesInputs = arrayFromAnyRecord('sales_commercial_inputs');
  const reasonCodes = strings(brief, 'qualification_reason_codes', problems, { allowEmpty: true });
  const applicability = normalizeText(string(brief, 'cta_input_collection_applicability', problems));
  const technicalScalars = ['technical_qualification_requirement', 'technical_qualification_contract_status', 'technical_qualification_definition', 'technical_qualification_owner', 'technical_qualification_next_step'];
  const salesScalars = ['sales_acceptance_requirement', 'sales_acceptance_contract_status', 'sales_acceptance_definition', 'sales_acceptance_owner', 'sales_acceptance_next_step', 'sales_commercial_intent_required', 'sales_commercial_intent_status', 'sales_commercial_inputs_status'];
  const requireNotApplicableScalars = (fields, label) => {
    for (const field of fields) for (const record of records.filter((candidate) => field in candidate.attributes)) {
      if (normalizeText(string(record, field, problems)) !== 'not-applicable') fail(problems, `${record.source} stage_intake_contract=${intake} requires ${field}=not-applicable; ${label} lifecycle must remain separate`);
    }
  };
  const requireActiveScalars = (fields, label) => {
    for (const field of fields) for (const record of records.filter((candidate) => field in candidate.attributes)) {
      if (normalizeText(string(record, field, problems)) === 'not-applicable') fail(problems, `${record.source} stage_intake_contract=${intake} requires active ${field}; ${label} lifecycle is applicable`);
    }
  };
  const forbidTechnicalQualifiedLifecycle = () => {
    if (reasonCodes.some((row) => normalizeText(row).startsWith('technical-qualified|'))) fail(problems, `${brief.source} stage_intake_contract=${intake} must not use the Validate technical-qualified lifecycle`);
  };

  if (intake === 'none') {
    if (applicability !== 'not-applicable') fail(problems, `${brief.source} stage_intake_contract=none requires cta_input_collection_applicability=not-applicable`);
    for (const [field, values] of [
      ['required_inquiry_inputs', requiredInputs], ['first_round_inquiry_inputs', firstRound], ['second_round_inquiry_inputs', secondRound],
      ['cta_required_inputs', ctaInputs], ['cta_progressive_profiling_omitted_inputs', omittedInputs],
      ['technical_qualification_gates', technicalGates], ['sales_acceptance_gates', salesGates], ['sales_commercial_inputs', salesInputs],
    ]) if (values.length) fail(problems, `${brief.source} stage_intake_contract=none requires empty ${field}`);
    requireNotApplicableScalars(technicalScalars, 'technical qualification');
    requireNotApplicableScalars(salesScalars, 'sales acceptance');
    forbidTechnicalQualifiedLifecycle();
  } else {
    if (applicability !== 'applicable') fail(problems, `${brief.source} stage_intake_contract=${intake} requires cta_input_collection_applicability=applicable`);
    validateInquiryInputs(firstRound, brief.source, 'first_round_inquiry_inputs', problems, { minItems: intake === 'validate-technical' ? 4 : (intake === 'buy-commercial' ? 3 : 1) });
    if (firstRound.length > 6) fail(problems, `${brief.source} first-round intake must remain at most six low-friction fields`);
    const requiredMatchesFirst = sameNormalizedSet(requiredInputs, firstRound) && requiredInputs.length === firstRound.length;
    const fullTechnicalPacket = [...firstRound, ...secondRound];
    const requiredMatchesFullTechnical = intake === 'validate-technical' && sameNormalizedSet(requiredInputs, fullTechnicalPacket) && requiredInputs.length === fullTechnicalPacket.length;
    if (!requiredMatchesFirst && !requiredMatchesFullTechnical) fail(problems, `${brief.source} required_inquiry_inputs must equal the stage-specific first round or, for validate-technical only, the full first-plus-second technical packet`);
    if (!sameNormalizedSet(ctaInputs, firstRound) || ctaInputs.length !== firstRound.length) fail(problems, `${brief.source} cta_required_inputs must exactly equal the stage-specific first_round_inquiry_inputs`);
  }

  if (intake === 'validate-technical') {
    validateInquiryInputs(secondRound, brief.source, 'second_round_inquiry_inputs', problems, { minItems: 1 });
    validateSecondRoundInputRelationships(brief, firstRound, secondRound, problems);
    if (technicalGates.length < 4) fail(problems, `${brief.source} validate-technical intake requires the complete technical qualification gates`);
    requireActiveScalars(technicalScalars, 'technical qualification');
  } else {
    if (secondRound.length) fail(problems, `${brief.source} only stage_intake_contract=validate-technical may use second_round_inquiry_inputs`);
    validateSecondRoundInputRelationships(brief, firstRound, secondRound, problems);
  }

  if (intake === 'troubleshoot-support' || intake === 'compare-handoff') {
    if (technicalGates.length) fail(problems, `${brief.source} ${intake} must not inherit Validate technical qualification gates`);
    requireNotApplicableScalars(technicalScalars, 'technical qualification');
    forbidTechnicalQualifiedLifecycle();
    if (intake === 'compare-handoff' && intent !== 'mixed-commercial') fail(problems, `${brief.source} compare-handoff may be used only with intent_class=mixed-commercial`);
  }

  if (intake === 'buy-commercial') {
    if (technicalGates.length) fail(problems, `${brief.source} buy-commercial intake must not inherit technical qualification gates`);
    requireNotApplicableScalars(technicalScalars, 'technical qualification');
    forbidTechnicalQualifiedLifecycle();
    if (!salesGates.length) fail(problems, `${brief.source} buy-commercial intake requires commercial/RFQ sales acceptance gates`);
    if (!salesInputs.length) fail(problems, `${brief.source} buy-commercial intake requires a commercial/RFQ packet in sales_commercial_inputs`);
    requireActiveScalars(salesScalars, 'sales acceptance');
  }
}

function validateTitleHierarchyAndReviewGates(brief, draft, review, problems) {
  const workingTitle = requireMeaningfulString(brief, 'working_article_title', problems, { minLength: 18 });
  const articleTitle = requireMeaningfulString(draft, 'article_title', problems, { minLength: 18 });
  const pageH1 = requireMeaningfulString(draft, 'page_h1', problems, { minLength: 18 });
  if (normalizeText(workingTitle) !== normalizeText(articleTitle)) fail(problems, `${draft.source} article_title must exactly match the approved Brief working_article_title`);

  const primaryQuery = string(brief, 'primary_query', problems);
  const task = parseDominantTaskContract(brief, problems);
  const stage = normalizeText(string(brief, 'stage', problems));
  const intent = normalizeText(string(brief, 'intent_class', problems));
  const commitment = normalizeText(string(brief, 'commercial_commitment', problems));
  const stageCues = new Map([
    ['learn', /\b(?:guide|basics?|explained|how|what|overview|principles?|concepts?|understand)\b/i],
    ['troubleshoot', /\b(?:troubleshoot|diagnos(?:e|is|tic)|root cause|failure|fix|repair|fault)\b/i],
    ['compare', /\b(?:compare|comparison|versus|vs\.?|selection|shortlist|evaluate|choose|decision matrix)\b/i],
    ['validate', /\b(?:validat(?:e|ion)|verify|readiness|review|checklist|test|acceptance|evidence|candidate)\b/i],
    ['buy', /\b(?:buy|purchase|quote|quotation|rfq|pricing|price|order|supplier|moq|lead[ _-]?time)\b/i],
  ]);
  for (const [field, value] of [['article_title', articleTitle], ['page_h1', pageH1]]) {
    const normalized = normalizeText(value);
    const queryOverlap = semanticOverlap(value, primaryQuery);
    if (queryOverlap.length < Math.min(3, new Set(semanticTokens(primaryQuery)).size || 1)) fail(problems, `${draft.source} ${field} lacks semantic parity with primary_query`);
    if (!actionSlotsAlign(value, task.action)) fail(problems, `${draft.source} ${field} leading action must match dominant_task_contract action`);
    if (semanticOverlap(value, task.decisionObject).length < 2) fail(problems, `${draft.source} ${field} lacks the dominant task decision object`);
    if (semanticOverlap(value, task.expectedOutput).length < 1) fail(problems, `${draft.source} ${field} lacks the dominant task observable output`);
    if (!stageCues.get(stage)?.test(value)) fail(problems, `${draft.source} ${field} does not express the declared ${stage} stage or its dominant action`);
    if (stage !== 'buy' && commercialClassification(value).commercial) fail(problems, `${draft.source} non-Buy ${field} must not use transactional or commercial modifiers`);
    if (stage === 'buy' && intent !== 'transactional' && commitment !== 'commercial') fail(problems, `${draft.source} Buy ${field} requires transactional intent or commercial commitment`);
    if (/\b(?:banana|lantern|wallpaper|applaud|random|unrelated)\b/i.test(normalized)) fail(problems, `${draft.source} ${field} contains unrelated word-salad terms`);
    const counts = new Map();
    for (const token of semanticTokens(value)) counts.set(token, (counts.get(token) || 0) + 1);
    const stuffed = [...counts.entries()].filter(([, count]) => count > 2).map(([token]) => token);
    if (stuffed.length || /\b([a-z][a-z0-9-]{3,})(?:\s+\1){1,}\b/i.test(normalized)) fail(problems, `${draft.source} ${field} contains query stuffing or repeated keyword tokens: ${stuffed.join(', ') || value}`);
  }

  const bodyText = markdownPlainText(draft.body);
  const dominantSearchIntent = string(brief, 'dominant_search_intent', problems);
  for (const field of ['meta_description', 'excerpt']) {
    const value = requireMeaningfulString(draft, field, problems, { minLength: 40 });
    if (semanticOverlap(value, primaryQuery).length < 2) fail(problems, `${draft.source} ${field} lacks semantic parity with primary_query`);
    if (semanticOverlap(value, `${task.decisionObject} ${task.expectedOutput}`).length < 2) fail(problems, `${draft.source} ${field} lacks semantic parity with the dominant buyer task`);
    if (semanticOverlap(value, dominantSearchIntent).length < 2) fail(problems, `${draft.source} ${field} lacks semantic parity with dominant_search_intent`);
    if (semanticOverlap(value, articleTitle).length < 2) fail(problems, `${draft.source} ${field} lacks semantic parity with article_title`);
    if (semanticOverlap(value, pageH1).length < 2) fail(problems, `${draft.source} ${field} lacks semantic parity with page_h1`);
    if (semanticOverlap(value, bodyText).length < 3) fail(problems, `${draft.source} ${field} is not materially represented in the publishable body`);
  }

  for (const field of [
    'title_primary_query_parity_verdict', 'title_dominant_task_parity_verdict', 'title_stage_parity_verdict',
    'h1_title_task_parity_verdict', 'hierarchy_scan_verdict', 'six_node_causal_chain_verdict',
  ]) {
    if (normalizeText(string(review, field, problems)) !== PASS) fail(problems, `${review.source} ${field} must be pass and is a fatal article-structure gate`);
  }
}

function validateBoundedPainLanguage(brief, draft, evidenceScope, problems) {
  const painStatus = normalizeText(string(brief, 'pain_evidence_status', problems));
  if (evidenceScope === 'production' && painStatus === 'confirmed') return;
  const visibleFields = ['pain_trigger', 'surface_problem', 'operational_friction', 'business_consequence', 'desired_decision']
    .map((field) => string(brief, field, problems));
  const painSection = markdownSectionByHeading(draft.body, /pain chain|avoidable rework|wattage-first|buyer pain|why .* may/);
  const boundedModal = /\b(?:may|might|can|could|risks?|is at risk of|has the potential to)\b/i;
  const deterministic = /\b(?:creates?|causes?|will|guarantees?|ensures?|always|inevitably|certainly)\b/i;
  const claims = [...visibleFields, ...String(painSection || '').split(/(?<=[.!?])\s+|\n+/)].map((value) => String(value).trim()).filter(Boolean);
  for (const claim of claims) {
    if (deterministic.test(claim) && !boundedModal.test(claim)) fail(problems, `${draft.source} inferred or synthetic pain language must use a bounded modal such as may/can/could/risks; deterministic claim is blocked: ${claim.slice(0, 180)}`);
  }
}

function validateCanonicalStageMatrix(records, problems) {
  const brief = records[0];
  const stage = normalizeText(string(brief, 'stage', problems));
  const contract = STAGE_CONTRACTS.get(stage);
  if (!contract) return;
  const ctaMode = normalizeText(string(brief, 'stage_cta_mode', problems));
  const linkRoles = strings(brief, 'stage_required_link_roles', problems, { allowEmpty: true }).map(normalizeText);
  const linkApplicability = normalizeText(string(brief, 'stage_link_requirement_status', problems));
  const salesRequirement = normalizeText(string(brief, 'stage_sales_qualification_requirement', problems));
  const commitment = normalizeText(string(brief, 'commercial_commitment', problems));
  const intent = normalizeText(string(brief, 'intent_class', problems));
  const queryText = [string(brief, 'primary_query', problems), ...strings(brief, 'supporting_query_variants', problems)].join(' ');
  const outcome = requireMeaningfulString(brief, 'stage_primary_outcome', problems, { minLength: 12 });
  if (!contract.cta.test(ctaMode)) fail(problems, `${brief.source} stage=${stage} is incompatible with stage_cta_mode=${ctaMode}`);
  if (linkApplicability === 'applicable' && (!linkRoles.length || linkRoles.some((role) => !contract.links.has(role)))) {
    fail(problems, `${brief.source} stage=${stage} has incompatible stage_required_link_roles=${linkRoles.join(',') || 'missing'}`);
  }
  if (linkApplicability === 'not-applicable' && linkRoles.length) fail(problems, `${brief.source} not-applicable stage link must not declare stage_required_link_roles`);
  if (!contract.sales.has(salesRequirement)) fail(problems, `${brief.source} stage=${stage} is incompatible with stage_sales_qualification_requirement=${salesRequirement}`);
  for (const field of ['stage_primary_outcome', 'stage_cta_mode', 'stage_required_link_roles', 'stage_sales_qualification_requirement']) {
    requireCanonicalMatch(records, field, problems);
  }
  if (stage === 'validate') {
    if (commitment !== 'none') fail(problems, `${brief.source} Validate stage requires commercial_commitment=none; bounded engineering review belongs to CTA/action/output`);
    if (commercialClassification(queryText).commercial) fail(problems, `${brief.source} transactional query modifiers cannot masquerade as non-commercial Validate intent`);
    if (!/\b(?:engineering|technical|candidate|input|readiness|validation|evidence|boundary|fit|stop)\w*\b/i.test(outcome)) fail(problems, `${brief.source} Validate stage_primary_outcome must be a bounded technical decision output`);
  }
  if (stage === 'buy') {
    if (!['commercial', 'commercial-investigation', 'transactional'].includes(intent)) fail(problems, `${brief.source} Buy stage requires commercial or transactional intent_class`);
    if (!commercialClassification(queryText).commercial && !commercialClassification(string(brief, 'sales_commercial_intent_required', problems)).commercial) fail(problems, `${brief.source} Buy stage requires explicit transactional query or commercial-intent contract`);
    if (commitment === 'none' || commitment === 'technical-review') fail(problems, `${brief.source} Buy stage requires a commercial commitment, not ${commitment}`);
    if (salesRequirement !== 'required') fail(problems, `${brief.source} Buy stage requires sales qualification`);
  }
  if (['learn', 'troubleshoot'].includes(stage) && commitment !== 'none') fail(problems, `${brief.source} ${stage} stage requires commercial_commitment=none`);
  const declaredTargetRoles = strings(brief, 'internal_link_targets', problems, { allowEmpty: true }).map((row) => normalizeText(row.split('|')[0] || ''));
  if (linkApplicability === 'applicable') for (const role of linkRoles) if (!declaredTargetRoles.includes(role)) fail(problems, `${brief.source} stage-required link role ${role} has no matching internal_link_target`);
  if (stage === 'buy' && !declaredTargetRoles.some((role) => role === 'commercial' || role === 'conversion')) {
    fail(problems, `${brief.source} Buy stage requires a commercial or conversion internal-link target for the concrete next step; solution/product links may only supplement it`);
  }
}

function validateCanonicalCannibalization(brief, evidenceScope, evidenceRoot, problems) {
  const status = normalizeText(string(brief, 'cannibalization_status', problems));
  if (!CANNIBALIZATION_STATUSES.has(status)) fail(problems, `${brief.source} cannibalization_status must be clear, resolved, or unresolved`);
  const ownerPage = string(brief, 'owner_page', problems);
  requireAbsoluteHttpsUrl(ownerPage, brief.source, 'owner_page', problems);
  if (evidenceScope === 'production') requireProductionPublicHttpsUrl(ownerPage, brief.source, 'owner_page', problems);
  const task = parseDominantTaskContract(brief, problems);
  const conflicts = strings(brief, 'conflict_candidates', problems, { allowEmpty: true });
  const separations = strings(brief, 'intent_separation', problems, { allowEmpty: true });
  const parsed = parseCannibalizationConflicts(conflicts, separations, brief.source, ownerPage, task, problems);
  if (status === 'unresolved') fail(problems, `${brief.source} unresolved cannibalization is a fatal production/content gate`);
  if (status === 'clear' && (parsed.conflicts.size || parsed.separations.size)) fail(problems, `${brief.source} cannibalization_status=clear requires empty conflict_candidates and intent_separation`);
  if (status === 'resolved' && (!parsed.conflicts.size || !parsed.separations.size)) fail(problems, `${brief.source} cannibalization_status=resolved requires candidate/separation URL parity`);
  const inventoryStatus = normalizeText(string(brief, 'content_inventory_status', problems));
  if (evidenceScope === 'production' && inventoryStatus !== 'confirmed') fail(problems, `${brief.source} production cannibalization requires content_inventory_status=confirmed`);
  if (evidenceScope === 'synthetic-fixture' && !['confirmed-for-fixture-structure', 'confirmed'].includes(inventoryStatus)) fail(problems, `${brief.source} synthetic cannibalization fixture requires a structural inventory status`);
  requireIsoDate(string(brief, 'inventory_checked_at', problems), brief.source, 'inventory_checked_at', problems);
  const snapshot = string(brief, 'inventory_snapshot_ref', problems);
  const zeroRefs = strings(brief, 'inventory_zero_result_evidence_refs', problems, { allowEmpty: true });
  if (status === 'clear' && !zeroRefs.length) fail(problems, `${brief.source} cannibalization_status=clear requires independent inventory_zero_result_evidence_refs`);
  const refs = [...new Set([snapshot, ...zeroRefs].filter((value) => value && !/^not-applicable$/i.test(value)))];
  validateLocalEvidenceRefs(refs, brief.source, 'cannibalization inventory evidence', evidenceRoot, problems, { requireFragment: true, regularNonSymlink: evidenceScope === 'production', verifyFragment: true });
  validateReferencedSectionQuality(refs, brief.source, 'cannibalization inventory evidence', evidenceRoot, problems, {
    expectedTerms: evidenceScope === 'production' ? [string(brief, 'primary_query', problems), string(brief, 'target_market', problems), 'inventory', 'zero'] : [],
  });
  if (evidenceScope === 'synthetic-fixture' && status === 'clear') {
    for (const ref of zeroRefs) {
      const { pathPart } = splitLocalRef(ref);
      const target = pathPart ? resolve(evidenceRoot, pathPart) : '';
      if (!target || !existsSync(target) || !statSync(target).isFile()) continue;
      const documentBody = parseArticleMarkdownFrontMatter(readFileSync(target, 'utf8'), { source: target }).body;
      const normalizedDocumentBody = normalizeText(documentBody);
      if (!/inventory zero[- ]result evidence/.test(normalizedDocumentBody)
        || !/(?:^|\n)\s*candidate_count\s*:\s*0(?:\s|$)/im.test(securityCanonicalText(documentBody))
        || !normalizedDocumentBody.includes(normalizeText(string(brief, 'target_market', problems)))
        || !normalizedDocumentBody.includes(normalizeText(string(brief, 'inventory_checked_at', problems)))) {
        fail(problems, `${brief.source} synthetic cannibalization clear requires a dated, scoped zero-result evidence section in the referenced fixture register`);
      }
    }
  }
  if (evidenceScope === 'production') {
    validateProductionEvidenceRefs(zeroRefs, brief.source, 'inventory_zero_result_evidence_refs', evidenceRoot, problems, {
      expectedKinds: ['inventory-zero-result'],
      expectedCheckId: 'inventory-zero-result',
      expectedTargets: [{ url: ownerPage, role: 'owner-page', task: `${string(brief, 'primary_query', problems)} inventory zero-result check` }],
      requireStructuredSection: true,
    });
  }
}

function materiallySameInput(left, right) {
  const a = new Set(semanticTokens(left));
  const b = new Set(semanticTokens(right));
  const shared = [...a].filter((token) => b.has(token));
  const denominator = Math.max(1, Math.min(a.size, b.size));
  return normalizeText(left) === normalizeText(right) || shared.length / denominator >= 0.75;
}

function validateCanonicalProgressiveQualification(records, brief, draft, publish, problems) {
  if (normalizeText(string(brief, 'stage_intake_contract', problems)) !== 'validate-technical') return;
  const requiredFields = ['first_round_inquiry_inputs', 'second_round_inquiry_inputs'];
  if (records.some((record) => requiredFields.some((field) => !(field in record.attributes)))) {
    for (const record of records) for (const field of requiredFields) if (!(field in record.attributes)) fail(problems, `${record.source} V9 canonical Templates require explicit ${field}`);
    return;
  }
  for (const field of requiredFields) requireCanonicalMatch(records, field, problems);
  const first = strings(brief, 'first_round_inquiry_inputs', problems);
  const second = strings(brief, 'second_round_inquiry_inputs', problems);
  validateInquiryInputs(first, brief.source, 'first_round_inquiry_inputs', problems, { minItems: 4 });
  if (first.length > 6) fail(problems, `${brief.source} first_round_inquiry_inputs must contain 4-6 items`);
  validateInquiryInputs(second, brief.source, 'second_round_inquiry_inputs', problems, { minItems: 1 });
  validateSecondRoundInputRelationships(brief, first, second, problems);
  const required = strings(brief, 'required_inquiry_inputs', problems);
  if (!sameNormalizedSet(required, first) && !sameNormalizedSet(required, [...first, ...second])) fail(problems, `${brief.source} required_inquiry_inputs must equal the canonical first round or the full first-plus-second technical packet`);
  const ctaInputs = strings(brief, 'cta_required_inputs', problems);
  if (!sameNormalizedSet(ctaInputs, first)) fail(problems, `${brief.source} cta_required_inputs must exactly equal first_round_inquiry_inputs`);
  const omitted = strings(brief, 'cta_progressive_profiling_omitted_inputs', problems, { allowEmpty: true });
  if (!sameNormalizedSet(omitted, second)) fail(problems, `${brief.source} cta_progressive_profiling_omitted_inputs must exactly equal second_round_inquiry_inputs`);
  const fallback = string(brief, 'cta_fallback_message_template', problems);
  const fallbackUsesCanonicalWorksheet = /\b(?:single|completed|prepared|local|readiness)\s+worksheet\b/i.test(fallback);
  if (!fallbackUsesCanonicalWorksheet) for (const input of first) if (!semanticOverlap(input, fallback).length) fail(problems, `${brief.source} CTA fallback must mechanically cover first-round input: ${input}`);
  const fallbackParityText = `${fallback} ${markdownPlainText(draft.body)}`;
  if (!/\b(?:second[- ]round|follow[- ]?up|after (?:the )?(?:first|engineering) review|later technical packet|exact second[- ]round request)\b/i.test(fallbackParityText)) fail(problems, `${brief.source} copyable CTA fallback must preserve the second-round follow-up contract`);
  const body = markdownPlainText(draft.body);
  for (const [round, inputs] of [['first-round', first], ['second-round', second]]) for (const input of inputs) if (!semanticOverlap(input, body).length) fail(problems, `${draft.source} Draft must visibly cover ${round} input: ${input}`);
  if (!/\bfirst[- ]round\b/i.test(body) || !/\bsecond[- ]round\b/i.test(body)) fail(problems, `${draft.source} Draft must visibly distinguish first-round and second-round input collection`);

  const definition = normalizeText(string(brief, 'technical_qualification_definition', problems));
  const owner = string(brief, 'technical_qualification_owner', problems);
  if (/technical[- ]qualified/.test(definition) && (!/second[- ]round/.test(definition) || !/\b(?:reviewed|approved|accepted|signed off)\b/.test(definition))) {
    fail(problems, `${brief.source} technical-qualified requires a complete second-round packet plus technical-owner review`);
  }
  if (/\b(?:first[- ]round|four|five|six)\b/.test(definition) && /\btechnical[- ]qualified\b/.test(definition) && !/second[- ]round/.test(definition)) fail(problems, `${brief.source} first-round inputs cannot directly produce technical-qualified`);
  if (!TECHNICAL_OWNER_PATTERN.test(owner)) fail(problems, `${brief.source} technical_qualification_owner must be a technical owner`);

  const reasonRows = strings(brief, 'qualification_reason_codes', problems).map((row) => row.split('|').map((part) => part.trim()));
  for (const row of reasonRows) {
    const text = normalizeText(row.join(' '));
    const state = normalizeText(row[0] || '');
    if (state && ![...QUALIFICATION_PROGRESS_STATES].some((value) => state.includes(value)) && !/not-applicable/.test(state)) fail(problems, `${brief.source} qualification reason code uses an unknown lifecycle state: ${row[0]}`);
    if (/\b(?:missing|incomplete|not supplied|required input)\b/.test(text) && /disqual/.test(text)) fail(problems, `${brief.source} missing first/second-round inputs must route to needs-follow-up, never disqualified`);
    if (EXPLICIT_COMMERCIAL_INTENT_PATTERN.test(text) && /disqual/.test(text)) fail(problems, `${brief.source} RFQ/price/timeline/order/supplier-selection intent must route to commercial-owner qualification, never disqualified`);
    if (/disqual/.test(state) && !EXPLICIT_NO_FIT_PATTERN.test(text)) fail(problems, `${brief.source} disqualified is reserved for explicit incompatibility, out-of-envelope, or unsupported scope`);
  }
  for (const row of strings(brief, 'disqualifiers', problems, { allowEmpty: true })) {
    if (!EXPLICIT_NO_FIT_PATTERN.test(row)) fail(problems, `${brief.source} disqualifiers may contain only explicit incompatibility/out-of-envelope/unsupported-scope conditions: ${row}`);
  }

  const salesRequirement = normalizeText(string(brief, 'sales_acceptance_requirement', problems));
  const stageSalesRequirement = normalizeText(string(brief, 'stage_sales_qualification_requirement', problems));
  const salesOwner = string(brief, 'sales_acceptance_owner', problems);
  const salesDefinition = string(brief, 'sales_acceptance_definition', problems);
  const salesNextStep = string(brief, 'sales_acceptance_next_step', problems);
  const salesIntent = string(brief, 'sales_commercial_intent_required', problems);
  const salesInputs = 'sales_commercial_inputs' in draft.attributes ? strings(draft, 'sales_commercial_inputs', problems, { allowEmpty: true }) : [];
  const salesRequired = salesRequirement === 'required' || stageSalesRequirement === 'required';
  if (salesRequired) {
    if (!EXPLICIT_COMMERCIAL_INTENT_PATTERN.test(salesIntent)) fail(problems, `${brief.source} required sales acceptance requires explicit commercial intent`);
    if (!salesInputs.length) fail(problems, `${draft.source} required sales acceptance requires commercial inputs`);
    if (!COMMERCIAL_OWNER_PATTERN.test(salesOwner) || (TECHNICAL_OWNER_PATTERN.test(salesOwner) && !COMMERCIAL_OWNER_PATTERN.test(salesOwner))) fail(problems, `${brief.source} technical owner cannot be the sole sales_acceptance_owner`);
    for (const [field, value] of [['sales_acceptance_definition', salesDefinition], ['sales_acceptance_next_step', salesNextStep]]) if (/^not-applicable$/i.test(value) || value.length < 10) fail(problems, `${brief.source} required sales acceptance requires a concrete ${field}`);
  } else if (/^not-applicable$/i.test(salesRequirement)) {
    if (!/^not-applicable$/i.test(salesOwner) || !/^not-applicable$/i.test(salesDefinition) || !/^not-applicable$/i.test(salesNextStep) || salesInputs.length) fail(problems, `${brief.source} true not-applicable sales acceptance must not fabricate owner, definition, next step, or commercial inputs`);
  } else if (/^not-applicable-without-(?:explicit-)?commercial-intent$/i.test(salesRequirement)) {
    if (!EXPLICIT_COMMERCIAL_INTENT_PATTERN.test(salesIntent)) fail(problems, `${brief.source} conditional sales routing must define explicit commercial intent`);
    if (!COMMERCIAL_OWNER_PATTERN.test(salesOwner)) fail(problems, `${brief.source} conditional commercial-intent routing requires a named commercial owner`);
    if (salesDefinition.length < 10 || salesNextStep.length < 10) fail(problems, `${brief.source} conditional commercial-intent routing requires a definition and next step`);
  }
  requireCanonicalMatch([brief, draft, publish], 'cta_fallback_message_template', problems);
}

function parseRoleHandoffContracts(record, activeRoles, evidenceRoot, problems, productionEvidence = false) {
  const values = strings(record, 'role_handoff_contracts', problems, { allowEmpty: true });
  const rows = [];
  for (const value of values) {
    const parts = value.split('|').map((part) => part.trim());
    if (parts.length !== 7 || parts.some((part) => !part)) { fail(problems, `${record.source} role_handoff_contracts entry must use from_role|to_role|url|retained_task|receiving_task|receiving_owner|acceptance_evidence_ref`); continue; }
    const [fromRole, toRole, url, retainedTask, receivingTask, receivingOwner, evidenceRef] = parts;
    requireCanonicalBuyerRole(fromRole, record.source, 'role_handoff_contracts from_role', problems);
    requireCanonicalBuyerRole(toRole, record.source, 'role_handoff_contracts to_role', problems);
    requireAbsoluteHttpsUrl(url, record.source, 'role_handoff_contracts url', problems);
    meaningfulScalar(retainedTask, record.source, 'role_handoff_contracts retained_task', problems, { minLength: 10 });
    meaningfulScalar(receivingTask, record.source, 'role_handoff_contracts receiving_task', problems, { minLength: 10 });
    requireStableOwnerIdentity(receivingOwner, record.source, 'role_handoff_contracts receiving_owner', problems);
    const canonicalFrom = CANONICAL_BUYER_ROLES.get(normalizeText(fromRole));
    const canonicalTo = CANONICAL_BUYER_ROLES.get(normalizeText(toRole));
    if (canonicalFrom && !ROLE_SEMANTIC_PATTERNS.get(canonicalFrom)?.test(retainedTask)) {
      fail(problems, `${record.source} role_handoff_contracts retained_task does not match ${canonicalFrom} responsibility`);
    }
    if (canonicalTo && !ROLE_SEMANTIC_PATTERNS.get(canonicalTo)?.test(receivingTask)) {
      fail(problems, `${record.source} role_handoff_contracts receiving_task does not match ${canonicalTo} responsibility`);
    }
    const receivingCommercial = commercialClassification(receivingTask).commercial;
    if (canonicalTo === 'Quality' && receivingCommercial) {
      fail(problems, `${record.source} Quality cannot receive procurement, cost, proposal, RFQ, quotation, price-approval, purchase, or supplier-selection work`);
    }
    if (canonicalTo !== 'Procurement' && receivingCommercial) {
      fail(problems, `${record.source} commercial receiving_task must route to Procurement, not ${canonicalTo || toRole}`);
    }
    if (canonicalTo === 'Procurement' && !receivingCommercial) {
      fail(problems, `${record.source} Procurement handoff must name a commercial/RFQ/price/MOQ/lead-time/purchase task`);
    }
    const resolved = validateLocalEvidenceRefs([evidenceRef], record.source, 'role_handoff_contracts acceptance_evidence_ref', evidenceRoot, problems, { requireFragment: true });
    if (productionEvidence) {
      rejectSyntheticEvidenceFiles(resolved, record.source, 'role_handoff_contracts acceptance_evidence_ref', problems);
      validateProductionEvidenceRefs([evidenceRef], record.source, 'role_handoff_contracts acceptance_evidence_ref', evidenceRoot, problems, {
        expectedKinds: ['target-acceptance'],
        expectedCheckId: 'target-acceptance',
        expectedTargets: [{ url, role: canonicalTo || toRole, task: receivingTask, owner: receivingOwner }],
        expectedOwner: receivingOwner,
        requireStructuredSection: true,
      });
    }
    rows.push({ fromRole, toRole, url, retainedTask, receivingTask, receivingOwner, evidenceRef });
  }
  const active = new Set(activeRoles.map(normalizeText));
  for (const row of rows) if (!active.has(normalizeText(row.fromRole)) && !active.has(normalizeText(row.toRole))) fail(problems, `${record.source} role handoff must include at least one active buyer role`);
  return rows;
}

const SEMANTIC_EMPHASIS_ROLES = new Set([
  'condition', 'risk', 'evidence', 'no-fit', 'boundary', 'action', 'decision',
]);


function locateDecisionSequenceRows(body, decisionRows, source, problems) {
  const markdown = String(body || '');
  const candidates = [];
  const blockPattern = /^(#{2,6})\s+(.+)$|^([^\n][^\n]{11,})$/gm;
  for (const match of markdown.matchAll(blockPattern)) {
    const raw = match[2] || match[3] || '';
    const plain = normalizeText(markdownPlainText(raw));
    if (plain) candidates.push({ index: match.index || 0, plain, heading: Boolean(match[2]) });
  }
  const rolePatterns = new Map([
    ['diagnose', /\b(?:why|pain|problem|failure|cause|gap|friction|rework|diagnos)\w*\b/i],
    ['decide', /\b(?:check|candidate|decision|compare|choose|shortlist|stop|readiness|matrix)\w*\b/i],
    ['de-risk', /\b(?:risk|boundary|assumption|no[- ]?fit|validation|evidence|round two|acceptance)\w*\b/i],
    ['act', /\b(?:prepare|request|next|action|review|handoff|packet|contact|self[- ]?check)\w*\b/i],
  ]);
  const positions = [];
  const usedIndexes = new Set();
  for (const row of decisionRows) {
    const [rawRole, , rawLocation] = row.split('|').map((part) => part.trim());
    const role = normalizeText(rawRole);
    let location = normalizeText(rawLocation);
    const fiveInputDecisionAlias = role === 'decide' && /five input readiness check/.test(location);
    if (fiveInputDecisionAlias) {
      const headingMatch = [...markdown.matchAll(/^##\s+(.+)$/gm)]
        .map((match) => ({ index: match.index || 0, plain: normalizeText(markdownPlainText(match[1])), heading: true }))
        .find((candidate) => /^use five decision blocks before (?:the )?first review$/.test(candidate.plain)
          || /five decision blocks|five input readiness|readiness check/.test(candidate.plain));
      if (headingMatch && !usedIndexes.has(headingMatch.index)) {
        positions.push({ role, location, index: headingMatch.index, plain: headingMatch.plain });
        usedIndexes.add(headingMatch.index);
        continue;
      }
      location = `${location} five decision blocks first review`;
    }
    if (role === 'hook' && /\b(?:opening|preamble|direct answer|before the first section)\b/i.test(location)) {
      positions.push({ role, location, index: 0 });
      usedIndexes.add(0);
      continue;
    }
    const decisionTokens = (value) => [...new Set([
      ...semanticTokens(value),
      ...normalizeText(value).split(/[^\p{L}\p{N}]+/u).filter((token) => ['two', 'fit', 'rfq'].includes(token)),
    ])];
    const locationTokens = decisionTokens(location).filter((token) => !['section', 'sections', 'opening', 'location'].includes(token));
    const scoreCandidate = (candidate) => {
      const candidateTokens = new Set(decisionTokens(candidate.plain));
      const overlap = locationTokens.filter((token) => candidateTokens.has(token)).length;
      const coverage = locationTokens.length ? overlap / locationTokens.length : 0;
      const exactLocation = location.length >= 6 && (candidate.plain.includes(location)
        || (location.includes(candidate.plain) && coverage >= 0.75));
      const roleMatch = rolePatterns.get(role)?.test(candidate.plain) || false;
      return { ...candidate, overlap, coverage, exactLocation, roleMatch };
    };
    const scored = candidates
      .filter((candidate) => !usedIndexes.has(candidate.index))
      .map(scoreCandidate)
      .filter((candidate) => candidate.exactLocation
        || (candidate.heading && candidate.overlap >= Math.min(2, Math.max(1, locationTokens.length)))
        || (!candidate.heading && candidate.coverage >= 0.75 && candidate.overlap >= 2));
    scored.sort((left, right) => (Number(right.exactLocation) - Number(left.exactLocation))
      || (Number(right.heading) - Number(left.heading))
      || (right.coverage - left.coverage)
      || (right.overlap - left.overlap)
      || (left.index - right.index));
    let located = scored[0];
    if (!located && locationTokens.length <= 3) {
      const roleFallbacks = candidates
        .filter((candidate) => candidate.heading && !usedIndexes.has(candidate.index))
        .map(scoreCandidate)
        .filter((candidate) => candidate.roleMatch && candidate.overlap >= 1)
        .sort((left, right) => (right.overlap - left.overlap) || (left.index - right.index));
      located = roleFallbacks[0];
    }
    if (!located) {
      fail(problems, `${source} article_decision_sequence_map ${role} location does not resolve to a distinct publishable-body heading or block: ${rawLocation}`);
      positions.push({ role, location, index: -1 });
    } else {
      usedIndexes.add(located.index);
      positions.push({ role, location, index: located.index, plain: located.plain });
    }
  }
  const resolved = positions.filter((entry) => entry.index >= 0);
  for (let index = 1; index < resolved.length; index += 1) {
    if (resolved[index].index <= resolved[index - 1].index) {
      const trace = resolved.map((entry) => `${entry.role}@${entry.index}:${String(entry.plain || entry.location).slice(0, 72)}`).join(' -> ');
      fail(problems, `${source} publishable body must implement Hook -> Diagnose -> Decide -> De-risk -> Act in declared order; ${resolved[index].role} resolves before or at ${resolved[index - 1].role}; resolved=${trace}`);
      break;
    }
  }
  const act = positions.find((entry) => entry.role === 'act');
  if (act?.index >= 0) {
    const premature = buyerVisibleCtaCandidateBlocks(markdown).find((candidate) => candidate.index < act.index
      && (candidate.links.some((link) => BUYER_ROUTE_ACTION_PATTERN.test(link.anchor))
        || /\b(?:submit|send|upload|email|contact|book|call|schedule|talk\s+with|speak\s+with|reach(?:\s+out)?|arrange|discuss|request|proceed|continue|move)\b/i.test(candidate.plain)
        || sectionHasUnsafeUnverifiedRoute(candidate.raw))
      && !/^do not\b/i.test(candidate.plain));
    if (premature) fail(problems, `${source} buyer-visible human-handoff or commercial CTA appears before the declared Act location: ${premature.plain.slice(0, 160)}`);
  }
  return positions;
}

function validateCanonicalDecisionAndConversionMaps(records, brief, draft, problems) {
  for (const field of ['article_decision_sequence_map', 'article_decision_sequence_verdict', 'conversion_surface_map', 'conversion_surface_map_verdict']) {
    requireCanonicalMatch(records, field, problems, field, field.endsWith('_map') ? 'exact-sequence' : 'exact-scalar');
  }

  const decisionRows = strings(brief, 'article_decision_sequence_map', problems, { allowEmpty: true });
  if (decisionRows.length !== ARTICLE_DECISION_SEQUENCE_ROLES.length) {
    fail(problems, `${brief.source} article_decision_sequence_map must contain exactly five rows in hook, diagnose, decide, de-risk, act order`);
  }
  decisionRows.forEach((row, index) => {
    const parts = row.split('|').map((part) => part.trim());
    if (parts.length !== 3 || parts.some((part) => !part)) {
      fail(problems, `${brief.source} article_decision_sequence_map row ${index + 1} must use role|buyer purpose|location`);
      return;
    }
    const [role, purpose, location] = parts;
    const expectedRole = ARTICLE_DECISION_SEQUENCE_ROLES[index];
    if (normalizeText(role) !== expectedRole) fail(problems, `${brief.source} article_decision_sequence_map row ${index + 1} role must be ${expectedRole}`);
    meaningfulScalar(purpose, brief.source, `article_decision_sequence_map ${role} buyer purpose`, problems, { minLength: 18 });
    meaningfulScalar(location, brief.source, `article_decision_sequence_map ${role} location`, problems, { minLength: 6 });
  });
  locateDecisionSequenceRows(draft.body, decisionRows, draft.source, problems);

  const surfaceRows = strings(brief, 'conversion_surface_map', problems, { allowEmpty: true });
  if (surfaceRows.length !== CONVERSION_SURFACE_ROLES.length) {
    fail(problems, `${brief.source} conversion_surface_map must contain exactly three rows in primary, soft, fallback order`);
  }
  const stageContext = [
    string(brief, 'stage', problems),
    string(brief, 'stage_primary_outcome', problems),
    string(brief, 'stage_cta_mode', problems),
    string(brief, 'dominant_task_contract', problems),
    string(brief, 'cta_trigger', problems),
    string(brief, 'cta_expected_output', problems),
    string(brief, 'cta_soft_path', problems),
    string(brief, 'cta_fallback_message_template', problems),
    ...strings(brief, 'first_round_inquiry_inputs', problems, { allowEmpty: true }),
  ].join(' ');
  const inventoryRows = strings(brief, 'buyer_visible_cta_inventory', problems, { allowEmpty: true });
  const inventoryById = new Map();
  for (const inventoryRow of inventoryRows) {
    const inventoryParts = inventoryRow.split('|').map((part) => part.trim());
    if (inventoryParts.length !== 10) continue;
    const [surfaceId, , locator, , , owner, interaction] = inventoryParts;
    if (!inventoryById.has(surfaceId)) inventoryById.set(surfaceId, { locator, owner, interaction });
  }
  const conversionIds = new Set();
  surfaceRows.forEach((row, index) => {
    const parts = row.split('|').map((part) => part.trim());
    if (parts.length !== 6 || parts.some((part) => !part)) {
      fail(problems, `${brief.source} conversion_surface_map row ${index + 1} must use surface-id|role|outcome|location-or-locator|interaction|route-id-or-not-applicable`);
      return;
    }
    const [surfaceId, role, outcome, location, interaction, routeId] = parts;
    const expectedRole = CONVERSION_SURFACE_ROLES[index];
    if (!/^(?:primary|soft|fallback)-[a-z0-9][a-z0-9-]{2,}$/i.test(surfaceId)) fail(problems, `${brief.source} conversion_surface_map row ${index + 1} requires a stable buyer-visible surface-id`);
    if (conversionIds.has(surfaceId)) fail(problems, `${brief.source} conversion_surface_map surface-id must be unique: ${surfaceId}`);
    conversionIds.add(surfaceId);
    if (normalizeText(role) !== expectedRole) fail(problems, `${brief.source} conversion_surface_map row ${index + 1} role must be ${expectedRole}`);
    if (!normalizeText(surfaceId).startsWith(`${expectedRole}-`)) fail(problems, `${brief.source} conversion_surface_map ${surfaceId} surface-id must bind role ${expectedRole}`);
    meaningfulScalar(outcome, brief.source, `conversion_surface_map ${role} outcome`, problems, { minLength: 16 });
    meaningfulScalar(location, brief.source, `conversion_surface_map ${role} location`, problems, { minLength: 6 });
    meaningfulScalar(interaction, brief.source, `conversion_surface_map ${role} interaction`, problems, { minLength: 4 });
    const inventory = inventoryById.get(surfaceId);
    if (!inventory) {
      fail(problems, `${brief.source} conversion_surface_map surface-id ${surfaceId} must exist in buyer_visible_cta_inventory`);
    } else {
      if (location !== inventory.locator) fail(problems, `${brief.source} conversion_surface_map ${surfaceId} location must exactly match buyer_visible_cta_inventory locator`);
      if (interaction !== inventory.interaction) fail(problems, `${brief.source} conversion_surface_map ${surfaceId} interaction must exactly match buyer_visible_cta_inventory interaction-type`);
    }
    if (normalizeText(routeId) === 'not-applicable') {
      if (semanticOverlap(`${outcome} ${location} ${interaction}`, stageContext).length < 2) {
        fail(problems, `${brief.source} conversion_surface_map ${role} route not-applicable requires a concrete stage-specific rationale in outcome, location, and interaction`);
      }
    } else if (!/^[a-z0-9][a-z0-9._:/-]{2,}$/i.test(routeId) || /^(?:tbd|todo|unknown|placeholder|replace)/i.test(routeId)) {
      fail(problems, `${brief.source} conversion_surface_map ${role} route must be a stable route id or not-applicable`);
    }
  });

  for (const field of ['article_decision_sequence_verdict', 'conversion_surface_map_verdict']) {
    const rawValue = brief.attributes[field];
    const value = typeof rawValue === 'string' ? rawValue.trim() : '';
    if (!['pass', 'block'].includes(value)) fail(problems, `${brief.source} ${field} must be pass or block`);
  }
}

function markdownStrongSpans(markdown) {
  const source = String(markdown || '');
  const spans = [];
  // The canonical AllinCMS converter supports only exact **...** strong.
  // Triple-star text renders literal outer stars and therefore cannot count.
  const pattern = /(?<!\*)\*\*([^*\n]+?)\*\*(?!\*)/g;
  for (const match of source.matchAll(pattern)) {
    const judgment = (match[1] || '').trim();
    const start = match.index;
    const end = start + match[0].length;
    const lineStart = source.lastIndexOf('\n', start) + 1;
    const nextNewline = source.indexOf('\n', end);
    const lineEnd = nextNewline < 0 ? source.length : nextNewline;
    const line = source.slice(lineStart, lineEnd).trim().replace(/^>\s*/, '').trim();
    spans.push({ judgment, raw: match[0], start, end, lineStart, lineEnd, line, wholeParagraph: line === match[0] });
  }
  return spans;
}

const CANONICAL_PAIN_LABELS = ['Actor', 'Trigger', 'Evidence gap', 'Rework', 'Consequence', 'Decision'];

function canonicalPainLabelStrongSpanKeys(markdown) {
  const section = markdownSectionRangeByHeading(markdown, /wattage-first|pain chain|avoidable rework|buyer pain/);
  if (!section) return new Set();

  const nodes = [];
  let lineStart = section.start;
  for (const line of section.text.split('\n')) {
    const match = /^\s*(\d+)[.)]\s+(\*\*(Actor|Trigger|Evidence\s+gap|Rework|Consequence|Decision):\*\*|(?:Actor|Trigger|Evidence\s+gap|Rework|Consequence|Decision):)\s+(.+?)\s*$/i.exec(line);
    if (match) {
      const strongRaw = match[2].startsWith('**') ? match[2] : '';
      const strongStart = strongRaw ? lineStart + line.indexOf(strongRaw) : -1;
      nodes.push({
        number: Number(match[1]),
        label: match[3] || match[2].replace(/[:*]/g, '').trim(),
        strongStart,
        strongEnd: strongStart < 0 ? -1 : strongStart + strongRaw.length,
      });
    }
    lineStart += line.length + 1;
  }

  const valid = nodes.length === CANONICAL_PAIN_LABELS.length
    && nodes.every((node, index) => node.number === index + 1
      && normalizeText(node.label) === normalizeText(CANONICAL_PAIN_LABELS[index]));
  if (!valid) return new Set();
  return new Set(nodes
    .filter((node) => node.strongStart >= 0)
    .map((node) => `${node.strongStart}:${node.strongEnd}`));
}

function validateCanonicalSemanticEmphasis(brief, draft, review, problems) {
  const briefPlan = strings(brief, 'semantic_emphasis_plan', problems);
  const draftPlan = strings(draft, 'semantic_emphasis_plan', problems);
  if (JSON.stringify(briefPlan.map(normalizeText)) !== JSON.stringify(draftPlan.map(normalizeText))) {
    fail(problems, 'semantic_emphasis_plan must match exactly between Brief and Draft');
  }

  const judgments = [];
  for (const [index, value] of briefPlan.entries()) {
    const parts = value.split('|').map((part) => part.trim());
    if (parts.length !== 3 || parts.some((part) => !part)) {
      fail(problems, `${brief.source} semantic_emphasis_plan entry ${index + 1} must use role|complete_judgment|placement`);
      continue;
    }
    const [role, judgment, placement] = parts;
    if (!SEMANTIC_EMPHASIS_ROLES.has(normalizeText(role))) {
      fail(problems, `${brief.source} semantic_emphasis_plan entry ${index + 1} role must be condition, risk, evidence, no-fit, boundary, action, or decision`);
    }
    meaningfulScalar(judgment, brief.source, `semantic_emphasis_plan entry ${index + 1} judgment`, problems, { minLength: 18 });
    meaningfulScalar(placement, brief.source, `semantic_emphasis_plan entry ${index + 1} placement`, problems, { minLength: 4 });
    if (!/[.!?。！？][\s"'”’）)\]]*$/.test(judgment)) {
      fail(problems, `${brief.source} semantic_emphasis_plan entry ${index + 1} judgment must be a complete sentence`);
    }
    if (semanticOverlap(judgment, draft.body).length < 2) {
      fail(problems, `${draft.source} must materially implement semantic_emphasis_plan judgment ${index + 1}`);
    }
    judgments.push(judgment);
  }

  const plannedByNormalizedJudgment = new Map(judgments.map((judgment) => [normalizeText(judgment), judgment]));
  if (/(?:^|[^_])___?[^_\n]+___?(?!_)/m.test(String(draft.body || ''))) {
    fail(problems, `${draft.source} underscore emphasis is unsupported by the canonical AllinCMS converter and cannot satisfy semantic strong; use exact **...** syntax`);
  }
  if (/(?:^|[^*])\*\*\*[^*\n]+\*\*\*(?!\*)/m.test(String(draft.body || ''))) {
    fail(problems, `${draft.source} triple-star emphasis renders literal outer stars in the canonical AllinCMS converter; use exact **...** syntax`);
  }
  const strongSpans = markdownStrongSpans(draft.body);
  const canonicalPainLabelStrongKeys = canonicalPainLabelStrongSpanKeys(draft.body);
  if (!strongSpans.length) fail(problems, `${draft.source} must visibly strong-emphasize every planned decision-scanning judgment`);
  for (const span of strongSpans) {
    if (/^(?:Actor|Trigger|Evidence gap|Rework|Consequence|Decision):$/i.test(span.judgment)
      && canonicalPainLabelStrongKeys.has(`${span.start}:${span.end}`)) continue;
    const plannedJudgment = plannedByNormalizedJudgment.has(normalizeText(span.judgment));
    const sentenceCount = (span.judgment.match(/[.!?。！？](?=[\s"'”’）)\]]|$)/g) || []).length;
    if (span.wholeParagraph && (!plannedJudgment || sentenceCount > 2 || span.judgment.length > 320)) {
      fail(problems, `${draft.source} Markdown strong must not bold an entire prose paragraph: ${span.judgment}`);
    }
    if (!plannedJudgment) {
      fail(problems, `${draft.source} every Markdown strong span must exactly match one complete semantic_emphasis_plan judgment; unplanned or decorative strong is blocked: ${span.judgment}`);
    }
    if (!/[.!?。！？][\s"'”’）)\]]*$/.test(span.judgment) || span.judgment.length < 18) {
      fail(problems, `${draft.source} Markdown strong must contain one complete planned judgment rather than a keyword, label, or fragment: ${span.judgment}`);
    }
  }
  for (const judgment of judgments) {
    if (!strongSpans.some((span) => normalizeText(span.judgment) === normalizeText(judgment))) {
      fail(problems, `${draft.source} every semantic_emphasis_plan judgment must be implemented as an exact Markdown strong span: ${judgment}`);
    }
  }
  if (normalizeText(string(review, 'semantic_emphasis_verdict', problems)) !== PASS) {
    fail(problems, `${review.source} semantic_emphasis_verdict must be pass`);
  }
}

function validatePainContinuity(record, problems) {
  const values = ['pain_trigger', 'surface_problem', 'operational_friction', 'business_consequence', 'desired_decision'].map((field) => string(record, field, problems));
  const broadTokens = new Set(['buyer', 'engineer', 'engineering', 'motor', 'product', 'candidate', 'process', 'review', 'risk', 'delay', 'sample']);
  for (let index = 0; index < values.length - 1; index += 1) {
    const overlap = semanticOverlap(values[index], values[index + 1]).filter((token) => !broadTokens.has(token));
    const causalBridge = /\b(?:because|therefore|which|caus|forces?|leads? to|results? in|instead of|before|after|when|otherwise|so that|needs?|cannot|unclear|conflict|send|create|reconcil|missing|incomplete|incompatib|unsuitable)\w*\b/i.test(`${values[index]} ${values[index + 1]}`);
    if (!overlap.length || !causalBridge) fail(problems, `${record.source} pain chain lacks concrete causal continuity between ${index + 1} and ${index + 2}; repeating a broad buyer/product token is insufficient`);
  }
}

function validateDirectAnswerContract(draft, taskContract, problems) {
  const answer = requireMeaningfulString(draft, 'direct_answer', problems, { minLength: 18 });
  const action = /^(?:start with|begin by|the first decision is|use\b|define\b|validate\b|diagnose\b|troubleshoot\b|compare\b|choose\b|confirm\b|check\b|assemble\b|build\b|complete\b|submit\b|decide\b|(?:an?\s+)?(?:buyer|engineer)s?\s+ought to\b)/i.test(answer.trim());
  const objectOverlap = semanticOverlap(answer, `${taskContract.decisionObject} ${taskContract.expectedOutput}`).length >= 2;
  const boundary = /\b(?:before|when|if|unless|under|within|without|only|after|subject to|rather than)\b/i.test(answer);
  if (!action || !objectOverlap || !boundary) fail(problems, `${draft.source} direct_answer must contain an action, decision object, and condition or boundary`);
}

const ARTICLE_TEMPLATE_EXPLANATION_FIELDS = new Set(['template_usage', 'when_to_read', 'keywords']);
const ARTICLE_TEMPLATE_FILES = new Map([
  ['article-brief', 'article-brief.md'],
  ['article-draft', 'article-draft.md'],
  ['article-quality-review', 'article-quality-review.md'],
  ['article-publish-record', 'publish-record.md'],
]);
const ARTICLE_CODE_REQUIRED_FIELDS = new Map([
  ['article-brief', new Map([
    ['icp_evidence_status', 'replace-with-inferred-confirmed-or-confirmed-for-fixture-structure'],
    ['icp_evidence_refs', ['replace-with-local-icp-evidence-ref']],
    ['icp_fit_contract', 'replace-with-specific-company-application-and-purchase-fit-contract'],
    ['icp_exclusion_contract', 'replace-with-specific-out-of-scope-company-application-or-purchase-contract'],
    ['cta_data_purpose', 'replace-with-buyer-visible-data-purpose-or-not-applicable'],
    ['cta_data_retention_period', 'replace-with-buyer-visible-retention-period-or-not-applicable'],
    ['cta_data_deletion_path', 'replace-with-buyer-visible-deletion-path-or-not-applicable'],
    ['cta_data_retention_owner', 'replace-with-accountable-retention-owner-or-not-applicable'],
  ])],
  ['article-draft', new Map([
    ['icp_evidence_status_snapshot', 'replace-with-brief-status-snapshot'],
    ['icp_evidence_refs_snapshot', ['replace-with-brief-ref-snapshot']],
    ['icp_fit_contract_snapshot', 'replace-with-brief-fit-contract-snapshot'],
    ['icp_exclusion_contract_snapshot', 'replace-with-brief-exclusion-contract-snapshot'],
    ['cta_data_purpose', 'replace-with-buyer-visible-data-purpose-or-not-applicable'],
    ['cta_data_retention_period', 'replace-with-buyer-visible-retention-period-or-not-applicable'],
    ['cta_data_deletion_path', 'replace-with-buyer-visible-deletion-path-or-not-applicable'],
    ['cta_data_retention_owner', 'replace-with-accountable-retention-owner-or-not-applicable'],
  ])],
  ['article-quality-review', new Map([
    ['icp_evidence_status_snapshot', 'replace-with-brief-status-snapshot'],
    ['icp_evidence_refs_snapshot', ['replace-with-brief-ref-snapshot']],
    ['icp_fit_contract_snapshot', 'replace-with-brief-fit-contract-snapshot'],
    ['icp_exclusion_contract_snapshot', 'replace-with-brief-exclusion-contract-snapshot'],
    ['cta_data_purpose', 'replace-with-buyer-visible-data-purpose-or-not-applicable'],
    ['cta_data_retention_period', 'replace-with-buyer-visible-retention-period-or-not-applicable'],
    ['cta_data_deletion_path', 'replace-with-buyer-visible-deletion-path-or-not-applicable'],
    ['cta_data_retention_owner', 'replace-with-accountable-retention-owner-or-not-applicable'],
  ])],
  ['article-publish-record', new Map([
    ['icp_evidence_status_snapshot', 'replace-with-brief-status-snapshot'],
    ['icp_evidence_refs_snapshot', ['replace-with-brief-ref-snapshot']],
    ['icp_fit_contract_snapshot', 'replace-with-brief-fit-contract-snapshot'],
    ['icp_exclusion_contract_snapshot', 'replace-with-brief-exclusion-contract-snapshot'],
    ['cta_data_purpose', 'replace-with-buyer-visible-data-purpose-or-not-applicable'],
    ['cta_data_retention_period', 'replace-with-buyer-visible-retention-period-or-not-applicable'],
    ['cta_data_deletion_path', 'replace-with-buyer-visible-deletion-path-or-not-applicable'],
    ['cta_data_retention_owner', 'replace-with-accountable-retention-owner-or-not-applicable'],
  ])],
]);
const templateSchemaCache = new Map();

function canonicalTemplateSchema(recordType) {
  if (templateSchemaCache.has(recordType)) return templateSchemaCache.get(recordType);
  const filename = ARTICLE_TEMPLATE_FILES.get(recordType);
  const parsed = parseArticleMarkdownFrontMatter(readFileSync(new URL(`../TEMPLATES/${filename}`, import.meta.url), 'utf8'), { source: `TEMPLATES/${filename}` });
  const schema = new Map(Object.entries(parsed.attributes).filter(([field]) => !ARTICLE_TEMPLATE_EXPLANATION_FIELDS.has(field)));
  for (const [field, templateValue] of ARTICLE_CODE_REQUIRED_FIELDS.get(recordType) || []) {
    if (!schema.has(field)) schema.set(field, templateValue);
  }
  const explanation = new Map(Object.entries(parsed.attributes).filter(([field]) => ARTICLE_TEMPLATE_EXPLANATION_FIELDS.has(field)));
  const result = { schema, explanation };
  templateSchemaCache.set(recordType, result);
  return result;
}

function validateCanonicalTemplateProjection(record, recordType, problems) {
  const { schema, explanation } = canonicalTemplateSchema(recordType);
  const canonicalByNormalized = new Map([...schema.keys()].map((field) => [normalizeFieldIdentifier(field), field]));
  const observedByNormalized = new Map();
  for (const field of Object.keys(record.attributes)) {
    const normalized = normalizeFieldIdentifier(field);
    if (observedByNormalized.has(normalized)) {
      fail(problems, `${record.source} contains confusable or separator/case-equivalent fields ${observedByNormalized.get(normalized)} and ${field}`);
    }
    observedByNormalized.set(normalized, field);
    if (ARTICLE_TEMPLATE_EXPLANATION_FIELDS.has(field)) {
      const exampleMetadata = record.attributes.type === 'example' && (
        (field === 'template_usage' && normalizeText(record.attributes[field]) === 'canonical-example')
        || (field === 'when_to_read' && /canonical synthetic/i.test(String(record.attributes[field] || '')))
        || (field === 'keywords' && Array.isArray(record.attributes[field]) && record.attributes[field].map(normalizeText).includes('canonical example'))
      );
      if (!exampleMetadata) fail(problems, `${record.source} field ${field} is Template explanation metadata and must not become an article-record control field`);
      continue;
    }
    const canonical = canonicalByNormalized.get(normalized);
    if (!canonical) {
      fail(problems, `${record.source} unknown top-level field ${field} is rejected by closed schema TEMPLATES/${ARTICLE_TEMPLATE_FILES.get(recordType)}`);
    } else if (canonical !== field) {
      fail(problems, `${record.source} field ${field} must use exact canonical spelling ${canonical}`);
    }
  }
  for (const [field, templateValue] of schema) {
    if (!(field in record.attributes)) {
      fail(problems, `${record.source} field ${field} is required by TEMPLATES/${ARTICLE_TEMPLATE_FILES.get(recordType)}`);
      continue;
    }
    const actual = record.attributes[field];
    if (Array.isArray(templateValue)) {
      if (!Array.isArray(actual) || actual.some((value) => typeof value !== 'string')) fail(problems, `${record.source} field ${field} must be an array of strings`);
    } else if (typeof templateValue === 'boolean') {
      if (typeof actual !== 'boolean') fail(problems, `${record.source} field ${field} must be true or false`);
    } else if (typeof templateValue === 'number') {
      if (typeof actual !== 'number' && typeof actual !== 'string') fail(problems, `${record.source} field ${field} must be a number or an explicit not-applicable string`);
    } else if (typeof actual !== 'string' || actual.trim() === '') {
      fail(problems, `${record.source} field ${field} must be a non-empty string`);
    }
  }
}

const ARTICLE_COMPARATOR_REGISTRY = new Map([
  ['page_h1', 'exact-raw-scalar'],
  ['first_round_expected_output', 'exact-raw-scalar'],
  ['first_round_output_candidate_gate_verdict', 'exact-raw-scalar'],
  ['section_information_gain_verdict', 'exact-raw-scalar'],
  ['normalized_field_set_redundancy_verdict', 'exact-raw-scalar'],
  ['cta_transmission_action_inventory', 'exact-raw-sequence'],
  ['supported_content_languages', 'normalized-set'],
  ['excluded_query_modifiers', 'normalized-set'],
  ['secondary_buyer_roles', 'normalized-set'],
  ['stage_required_link_roles', 'normalized-set'],
  ['supporting_query_variants', 'exact-sequence'],
  ['buyer_language_seeds', 'exact-sequence'],
  ['first_round_inquiry_inputs', 'exact-sequence'],
  ['first_round_input_specifications', 'exact-sequence'],
  ['first_round_input_specifications_snapshot', 'exact-sequence'],
  ['second_round_inquiry_inputs', 'exact-sequence'],
  ['second_round_input_relationships', 'exact-sequence'],
  ['cta_required_inputs', 'exact-sequence'],
  ['cta_required_inputs_snapshot', 'exact-sequence'],
  ['product_decision_map', 'keyed-row-map'],
  ['product_decision_map_snapshot', 'keyed-row-map'],
  ['internal_link_targets', 'keyed-row-map'],
  ['internal_link_targets_snapshot', 'keyed-row-map'],
  ['internal_link_buyer_task_contracts', 'keyed-row-map'],
  ['internal_link_buyer_task_contracts_snapshot', 'keyed-row-map'],
  ['role_handoff_contracts', 'keyed-row-map'],
  ['secondary_buyer_role_contracts', 'keyed-row-map'],
  ['qualification_reason_codes', 'keyed-row-map'],
  ['cta_buyer_visible_capability_proofs', 'keyed-row-map'],
  ['cta_buyer_visible_capability_proofs_snapshot', 'keyed-row-map'],
  ['buyer_visible_cta_inventory', 'exact-sequence'],
  ['visual_decision_assets', 'keyed-row-map'],
]);

function comparatorStrategyForField(field, value) {
  if (ARTICLE_COMPARATOR_REGISTRY.has(field)) return ARTICLE_COMPARATOR_REGISTRY.get(field);
  if (Array.isArray(value) && /(?:_refs|_evidence_refs)$/.test(field)) return 'normalized-set';
  return Array.isArray(value) ? 'exact-sequence' : 'exact-scalar';
}

function keyedRowComparable(values) {
  return values.map((value) => {
    const slots = String(value).split('|').map((part) => normalizeText(part));
    return { key: slots.slice(0, 2).join('|'), row: slots.join('|') };
  }).sort((left, right) => left.key.localeCompare(right.key) || left.row.localeCompare(right.row));
}

function canonicalComparable(value, strategy = comparatorStrategyForField('', value)) {
  if (!Array.isArray(value)) {
    if (strategy === 'exact-raw-scalar') return String(value ?? '');
    return normalizeText(String(value ?? ''));
  }
  if (strategy === 'exact-raw-sequence') return JSON.stringify(value.map((item) => String(item)));
  const normalized = value.map((item) => normalizeText(item));
  if (strategy === 'normalized-set') return JSON.stringify([...normalized].sort());
  if (strategy === 'keyed-row-map') return JSON.stringify(keyedRowComparable(value));
  return JSON.stringify(normalized);
}

function duplicateKeyedRowKeys(value) {
  if (!Array.isArray(value)) return [];
  const keys = value.map((row) => String(row).split('|').slice(0, 2).map(normalizeText).join('|'));
  return [...new Set(keys.filter((key, index) => key && keys.indexOf(key) !== index))];
}

function requireCanonicalMatch(records, field, problems, label = field, strategy = '') {
  const present = records.filter((record) => field in record.attributes);
  if (present.length < 2) return;
  const effective = strategy || comparatorStrategyForField(field, present[0].attributes[field]);
  if (effective === 'keyed-row-map') {
    for (const record of present) {
      const duplicates = duplicateKeyedRowKeys(record.attributes[field]);
      if (duplicates.length) fail(problems, `${record.source} field ${field} contains duplicate keyed rows: ${duplicates.join(', ')}`);
    }
  }
  const expected = canonicalComparable(present[0].attributes[field], effective);
  const drifted = present.slice(1).filter((record) => canonicalComparable(record.attributes[field], effective) !== expected);
  for (const record of drifted) {
    fail(problems, `${recordLabel(record)} field ${field} must match the canonical Brief projection using ${effective}`);
  }
  if (drifted.length) fail(problems, `${label} must match the canonical Brief projection across all records using ${effective}`);
}

function requireProjectionMatch(sourceRecord, sourceField, targetRecord, targetField, problems, strategy = '') {
  if (!(sourceField in sourceRecord.attributes) || !(targetField in targetRecord.attributes)) return;
  const effective = strategy || comparatorStrategyForField(sourceField, sourceRecord.attributes[sourceField]);
  const sourceValue = sourceRecord.attributes[sourceField];
  const targetValue = targetRecord.attributes[targetField];
  if (Array.isArray(targetValue)) {
    if (Array.isArray(sourceValue) && sourceValue.length && !targetValue.length) {
      fail(problems, `${targetRecord.source} projection ${targetField} must not be empty when ${sourceRecord.source} ${sourceField} is applicable`);
    }
    for (const value of targetValue) meaningfulScalar(String(value), targetRecord.source, targetField, problems, { minLength: 4 });
  } else {
    meaningfulScalar(String(targetValue ?? ''), targetRecord.source, targetField, problems, { minLength: 4 });
  }
  if (effective === 'keyed-row-map') {
    const duplicates = duplicateKeyedRowKeys(targetValue);
    if (duplicates.length) fail(problems, `${targetRecord.source} projection ${targetField} contains duplicate keyed rows: ${duplicates.join(', ')}`);
  }
  if (canonicalComparable(sourceValue, effective) !== canonicalComparable(targetValue, effective)) {
    fail(problems, `${targetRecord.source} projection ${targetField} must exactly match ${sourceRecord.source} ${sourceField} using ${effective}`);
  }
}

function internalLinkPublicationGatesPass(brief, problems) {
  return ['internal_link_reference_gate_verdict', 'internal_link_reachability_gate_verdict', 'internal_link_capability_gate_verdict']
    .every((field) => normalizeText(string(brief, field, problems)) === PASS);
}

function validateCtaPolicyTemporalContract({ source, policyEffectiveAt, policyCheckedAt, policyObservedAt, policyReviewedAt, policyReviewCeiling, canonicalReviewedAt, problems }) {
  requireIsoDate(policyEffectiveAt, source, 'cta_data_policy_effective_at', problems);
  requireFreshIsoDate(policyCheckedAt, source, 'cta_data_policy_checked_at', problems, CTA_POLICY_MAX_AGE_DAYS);
  requireFreshIsoDate(policyObservedAt, source, 'cta_data_policy_observed_at', problems, CTA_POLICY_MAX_AGE_DAYS);
  requireIsoDate(policyReviewedAt, source, 'cta_data_policy_reviewed_at', problems);
  requireIsoDate(policyReviewCeiling, source, 'cta_data_policy_review_ceiling', problems);
  requireDateNoLaterThan(policyEffectiveAt, policyCheckedAt, source, 'cta_data_policy_effective_at', 'cta_data_policy_checked_at', problems);
  requireDateNoLaterThan(policyCheckedAt, policyObservedAt, source, 'cta_data_policy_checked_at', 'cta_data_policy_observed_at', problems);
  requireDateNoLaterThan(policyObservedAt, policyReviewedAt, source, 'cta_data_policy_observed_at', 'cta_data_policy_reviewed_at', problems);
  requireDateNoLaterThan(policyReviewedAt, policyReviewCeiling, source, 'cta_data_policy_reviewed_at', 'cta_data_policy_review_ceiling', problems);
  requireDateNoLaterThan(policyReviewCeiling, canonicalReviewedAt, source, 'cta_data_policy_review_ceiling', 'reviewed_at', problems);
}

function validateCtaPolicyEvidenceProjection(fields, expected, source, ref, problems) {
  for (const [field, value] of Object.entries(expected)) {
    const actual = fields.get(field) || '';
    if (actual !== value) fail(problems, `${source} ${ref} ${field} must exactly bind the canonical CTA data-policy contract`);
  }
}

function validateIcpAndCtaDataContracts(records, brief, draft, review, publish, evidenceScope, evidenceRoot, problems) {
  for (const [briefField, snapshotField, strategy] of [
    ['icp_evidence_status', 'icp_evidence_status_snapshot', 'exact-scalar'],
    ['icp_evidence_refs', 'icp_evidence_refs_snapshot', 'exact-sequence'],
    ['icp_fit_contract', 'icp_fit_contract_snapshot', 'exact-scalar'],
    ['icp_exclusion_contract', 'icp_exclusion_contract_snapshot', 'exact-scalar'],
  ]) {
    for (const record of [draft, review, publish]) requireProjectionMatch(brief, briefField, record, snapshotField, problems, strategy);
  }

  const icpStatus = normalizeText(string(brief, 'icp_evidence_status', problems));
  const allowedSyntheticStatuses = new Set(['inferred', 'confirmed-for-fixture-structure']);
  if (evidenceScope === 'production' && icpStatus !== 'confirmed') {
    fail(problems, `${brief.source} production requires icp_evidence_status=confirmed`);
  } else if (evidenceScope === 'synthetic-fixture' && !allowedSyntheticStatuses.has(icpStatus)) {
    fail(problems, `${brief.source} synthetic fixture icp_evidence_status must be inferred or confirmed-for-fixture-structure`);
  }
  const icpRefs = strings(brief, 'icp_evidence_refs', problems, { allowEmpty: true });
  if (!icpRefs.length) fail(problems, `${brief.source} icp_evidence_refs must contain at least one local evidence reference`);
  const resolvedIcpRefs = validateLocalEvidenceRefs(icpRefs, brief.source, 'icp_evidence_refs', evidenceRoot, problems, {
    requireFragment: true,
    regularNonSymlink: true,
    verifyFragment: true,
  });
  if (evidenceScope === 'production') rejectSyntheticEvidenceFiles(resolvedIcpRefs, brief.source, 'icp_evidence_refs', problems);

  const fit = requireMeaningfulString(brief, 'icp_fit_contract', problems, { minLength: 32 });
  const exclusion = requireMeaningfulString(brief, 'icp_exclusion_contract', problems, { minLength: 28 });
  if (evidenceScope === 'production') {
    const reviewedAt = string(review, 'reviewed_at', problems);
    validateProductionEvidenceRefs(icpRefs, brief.source, 'icp_evidence_refs', evidenceRoot, problems, {
      expectedKinds: ['icp-evidence'],
      expectedCheckId: 'icp-evidence',
      expectedTargets: [{
        url: string(brief, 'owner_page', problems),
        role: 'icp-evidence',
        task: `${fit} ${exclusion}`,
      }],
      requireStructuredSection: true,
      latestAllowedAt: reviewedAt,
    });
  }
  if (!/\b(?:company|manufacturer|brand|integrator|distributor|supplier|team|organization|business|buyer)\b/i.test(fit)
    || !/\b(?:application|use case|project|program|product|purchase|procurement|engineering|commercial)\b/i.test(fit)) {
    fail(problems, `${brief.source} icp_fit_contract must specify both company fit and application or purchase fit`);
  }
  if (!/\b(?:exclude|excluded|not fit|out of scope|not intended|consumer|retail|unsupported|without)\b/i.test(exclusion)) {
    fail(problems, `${brief.source} icp_exclusion_contract must state a specific out-of-scope buyer, company, application, or purchase boundary`);
  }
  if (!/\b(?:before|after|when|while|during|evaluat(?:e|es|ing)|validat(?:e|es|ing|ion)|select(?:s|ing|ion)?|shortlist(?:s|ing)?|sourc(?:e|es|ing)|procur(?:e|es|ing|ement)|purchas(?:e|es|ing)|project|program|sample|rfq|quotation)\b/i.test(fit)) {
    fail(problems, `${brief.source} icp_fit_contract must name a buying stage or observable trigger condition`);
  }
  if (!/\b(?:able to|can\s+(?:supply|provide|share|confirm|complete)|has|have|with\s+(?:an?|the)|ready to|equipped to|authorized to|records?\s+(?:is|are|already)\s+available|path\s+to\s+complete)\b/i.test(fit)) {
    fail(problems, `${brief.source} icp_fit_contract must state the buyer capability or prerequisite needed to act on the next step`);
  }
  const fitContradiction = /\b(?:same|those|these|that)\b.{0,100}\b(?:also\s+)?(?:unsuitable|not fit|outside|out of scope|excluded)\b/i.test(fit)
    || /\b(?:suitable|fit|included|in scope|intended)\b.{0,100}\b(?:unsuitable|not fit|outside|out of scope|excluded)\b/i.test(fit);
  if (fitContradiction || /\b(?:unsuitable|not fit|outside (?:the )?scope|out of scope|excluded)\b/i.test(fit)) {
    fail(problems, `${brief.source} icp_fit_contract must contain only positive fit conditions and must not contradict or embed exclusion claims`);
  }
  const exclusionContradiction = /\b(?:same|those|these|that|every)\b.{0,120}\b(?:included|suitable|fit|in scope|intended)\b/i.test(exclusion)
    || /\b(?:excluded|not fit|out of scope|not intended|unsupported)\b.{0,120}\b(?:included|suitable|in scope|intended for)\b/i.test(exclusion);
  if (exclusionContradiction) {
    fail(problems, `${brief.source} icp_exclusion_contract contradicts its own out-of-scope boundary`);
  }
  const evidenceSections = icpRefs.map((ref) => {
    const { pathPart, fragment } = splitLocalRef(ref);
    if (!pathPart || !fragment) return '';
    try {
      const target = resolve(evidenceRoot, pathPart);
      return markdownPlainText(markdownSectionBody(parseArticleMarkdownFrontMatter(readFileSync(target, 'utf8'), { source: target }).body, fragment));
    } catch { return ''; }
  }).join(' ');
  if (semanticOverlap(`${fit} ${exclusion}`, evidenceSections).length < 3) {
    fail(problems, `${brief.source} icp_evidence_refs fragments must materially support the declared fit and exclusion contract`);
  }

  const ctaDataScalarFields = [
    'cta_data_purpose',
    'cta_data_retention_period',
    'cta_data_deletion_path',
    'cta_data_retention_owner',
    'cta_data_policy_contract_id',
    'cta_data_policy_status',
    'cta_data_policy_effective_at',
    'cta_data_policy_checked_at',
    'cta_data_policy_version',
    'cta_data_policy_digest',
    'cta_data_policy_observed_at',
    'cta_data_policy_reviewed_at',
    'cta_data_policy_review_ceiling',
    'cta_data_policy_owner_acceptance',
  ];
  const ctaDataRefFields = ['cta_data_policy_evidence_refs', 'cta_data_deletion_capability_evidence_refs'];
  for (const field of ctaDataScalarFields) requireCanonicalMatch(records, field, problems, field, 'exact-raw-scalar');
  for (const field of ctaDataRefFields) requireCanonicalMatch(records, field, problems, field, 'exact-sequence');
  const inventoryInteractions = strings(brief, 'buyer_visible_cta_inventory', problems, { allowEmpty: true })
    .map((row) => normalizeText(row.split('|')[6] || ''));
  const hasCollectingInteraction = ['input-collecting', 'human-handoff', 'commercial'].includes(normalizeText(string(brief, 'cta_interaction_type', problems)))
    || inventoryInteractions.some((value) => ['input-collecting', 'human-handoff', 'commercial'].includes(value));
  const verifiedCollectionRoute = normalizeText(string(brief, 'cta_destination', problems)) !== 'not-applicable'
    && ['cta_reference_gate_verdict', 'cta_reachability_gate_verdict', 'cta_capability_gate_verdict']
      .every((field) => normalizeText(string(brief, field, problems)) === 'pass');
  const collecting = hasCollectingInteraction && verifiedCollectionRoute;
  if (!collecting) {
    const purpose = string(brief, 'cta_data_purpose', problems);
    const unverifiedHandoff = hasCollectingInteraction && !verifiedCollectionRoute;
    if (unverifiedHandoff) {
      if (normalizeText(purpose) === 'not-applicable' || purpose.trim().length < 18) {
        fail(problems, `${brief.source} unverified handoff CTA must still state the bounded local preparation purpose`);
      }
      for (const field of ['cta_data_retention_period', 'cta_data_deletion_path', 'cta_data_retention_owner', 'cta_data_policy_contract_id', 'cta_data_policy_effective_at', 'cta_data_policy_checked_at', 'cta_data_policy_version', 'cta_data_policy_digest', 'cta_data_policy_observed_at', 'cta_data_policy_reviewed_at', 'cta_data_policy_review_ceiling']) {
        if (normalizeText(string(brief, field, problems)) !== 'not-applicable') fail(problems, `${brief.source} unverified handoff CTA requires ${field}=not-applicable rather than an invented supplier-side policy`);
      }
      if (normalizeText(string(brief, 'cta_data_policy_status', problems)) !== 'missing') fail(problems, `${brief.source} unverified handoff CTA requires cta_data_policy_status=missing`);
      if (normalizeText(string(brief, 'cta_data_policy_owner_acceptance', problems)) !== 'pending') fail(problems, `${brief.source} unverified handoff CTA requires cta_data_policy_owner_acceptance=pending`);
    } else {
      for (const field of ctaDataScalarFields) if (normalizeText(string(brief, field, problems)) !== 'not-applicable') {
        fail(problems, `${brief.source} ${field} must be not-applicable for inline-no-input or local-tool-only CTA packages`);
      }
    }
    for (const field of ctaDataRefFields) if (strings(brief, field, problems, { allowEmpty: true }).length) {
      fail(problems, `${brief.source} ${field} must be empty while no verified collection route exists`);
    }
    return;
  }

  const dataValues = new Map();
  for (const field of ['cta_data_purpose', 'cta_data_retention_period', 'cta_data_deletion_path', 'cta_data_retention_owner']) {
    const value = requireMeaningfulString(brief, field, problems, { minLength: field === 'cta_data_retention_owner' ? 4 : 18 });
    if (normalizeText(value) === 'not-applicable') fail(problems, `${brief.source} collecting CTA requires a concrete ${field}`);
    dataValues.set(field, value);
  }
  if (!/\b(?:retain|retention|delete|deletion|remove|purge|archive|days?|months?|years?|until|duration|review closes?)\b/i.test(dataValues.get('cta_data_retention_period'))) {
    fail(problems, `${brief.source} cta_data_retention_period must state a concrete duration or retention event`);
  }
  if (/\b(?:permanent(?:ly)?|indefinite(?:ly)?|forever|999\s*years?)\b/i.test(dataValues.get('cta_data_retention_period'))) {
    fail(problems, `${brief.source} cta_data_retention_period must be bounded and cannot use permanent, indefinite, forever, or 999-year retention`);
  }
  if (!/\b(?:delete|deletion|remove|removal|request|contact|portal|process|path|local copy)\b/i.test(dataValues.get('cta_data_deletion_path'))) {
    fail(problems, `${brief.source} cta_data_deletion_path must state how the buyer can request or trigger deletion`);
  }
  rejectOwnerPlaceholder(dataValues.get('cta_data_retention_owner'), brief.source, 'cta_data_retention_owner', problems);

  const policyContractId = requireMeaningfulString(brief, 'cta_data_policy_contract_id', problems, { minLength: 8 });
  if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$/.test(policyContractId) || /(?:replace|placeholder|example|test|dummy|todo|tbd)/i.test(policyContractId)) {
    fail(problems, `${brief.source} cta_data_policy_contract_id must be a stable non-placeholder identifier`);
  }
  const policyStatus = normalizeText(string(brief, 'cta_data_policy_status', problems));
  const policyEffectiveAt = string(brief, 'cta_data_policy_effective_at', problems);
  const policyCheckedAt = string(brief, 'cta_data_policy_checked_at', problems);
  const policyVersion = string(brief, 'cta_data_policy_version', problems);
  const policyDigest = string(brief, 'cta_data_policy_digest', problems);
  const policyObservedAt = string(brief, 'cta_data_policy_observed_at', problems);
  const policyReviewedAt = string(brief, 'cta_data_policy_reviewed_at', problems);
  const policyReviewCeiling = string(brief, 'cta_data_policy_review_ceiling', problems);
  const ownerAcceptance = normalizeText(string(brief, 'cta_data_policy_owner_acceptance', problems));
  if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/.test(policyVersion) || PLACEHOLDER_PATTERN.test(policyVersion)) fail(problems, `${brief.source} cta_data_policy_version must be a stable non-placeholder version`);
  if (!/^sha256:[a-f0-9]{64}$/i.test(policyDigest)) fail(problems, `${brief.source} cta_data_policy_digest must use sha256:<64 hex>`);
  const reviewedAt = string(review, 'reviewed_at', problems);
  validateCtaPolicyTemporalContract({ source: brief.source, policyEffectiveAt, policyCheckedAt, policyObservedAt, policyReviewedAt, policyReviewCeiling, canonicalReviewedAt: reviewedAt, problems });
  const policyRefs = strings(brief, 'cta_data_policy_evidence_refs', problems, { allowEmpty: true });
  const deletionRefs = strings(brief, 'cta_data_deletion_capability_evidence_refs', problems, { allowEmpty: true });
  if (!policyRefs.length || !deletionRefs.length) {
    fail(problems, `${brief.source} collecting CTA requires non-empty policy and deletion-capability evidence refs`);
  }
  for (const [field, refs] of [['cta_data_policy_evidence_refs', policyRefs], ['cta_data_deletion_capability_evidence_refs', deletionRefs]]) {
    if (new Set(refs.map(normalizeText)).size !== refs.length) fail(problems, `${brief.source} ${field} must not contain duplicate refs`);
    validateLocalEvidenceRefs(refs, brief.source, field, evidenceRoot, problems, {
      requireFragment: true,
      regularNonSymlink: evidenceScope === 'production',
      verifyFragment: true,
    });
  }

  if (evidenceScope === 'synthetic-fixture') {
    if (policyStatus !== 'synthetic-structure-only') fail(problems, `${brief.source} synthetic collecting CTA requires cta_data_policy_status=synthetic-structure-only`);
    if (ownerAcceptance !== 'synthetic-structure-only') fail(problems, `${brief.source} synthetic collecting CTA requires cta_data_policy_owner_acceptance=synthetic-structure-only`);
  } else if (evidenceScope === 'production') {
    if (policyStatus !== 'confirmed') fail(problems, `${brief.source} production collecting CTA requires cta_data_policy_status=confirmed`);
    if (ownerAcceptance !== 'accepted') fail(problems, `${brief.source} production collecting CTA requires cta_data_policy_owner_acceptance=accepted`);
    const destination = string(brief, 'cta_destination', problems);
    requireProductionPublicHttpsUrl(destination, brief.source, 'cta_destination', problems);
    const expectedTargets = [{
      url: destination,
      role: string(brief, 'stage_cta_mode', problems),
      task: `${string(brief, 'cta_trigger', problems)} ${string(brief, 'cta_expected_output', problems)}`,
    }];
    const requiredExtraFields = [
      'policy_contract_id', 'cta_mode', 'data_purpose', 'retention_period', 'deletion_path',
      'accountable_owner', 'policy_effective_at', 'policy_checked_at', 'capability_acceptance',
      'policy_version', 'policy_digest', 'policy_artifact_ref', 'policy_artifact_digest', 'screenshot_or_trace_ref',
    ];
    const policyInspections = validateProductionEvidenceRefs(policyRefs, brief.source, 'cta_data_policy_evidence_refs', evidenceRoot, problems, {
      expectedKinds: ['cta-data-policy'],
      expectedCheckId: 'cta-data-policy',
      expectedTargets,
      expectedOwner: dataValues.get('cta_data_retention_owner'),
      requiredExtraFields,
      requireStructuredSection: true,
      latestAllowedAt: reviewedAt,
    });
    const deletionInspections = validateProductionEvidenceRefs(deletionRefs, brief.source, 'cta_data_deletion_capability_evidence_refs', evidenceRoot, problems, {
      expectedKinds: ['cta-deletion-capability'],
      expectedCheckId: 'cta-deletion-capability',
      expectedTargets,
      expectedOwner: dataValues.get('cta_data_retention_owner'),
      requiredExtraFields,
      requireStructuredSection: true,
      latestAllowedAt: reviewedAt,
    });
    for (const inspection of [...policyInspections, ...deletionInspections]) {
      const fields = inspection.fields || new Map();
      validateCtaPolicyEvidenceProjection(fields, {
        policy_contract_id: policyContractId,
        policy_version: policyVersion,
        policy_digest: policyDigest,
        cta_mode: string(brief, 'stage_cta_mode', problems),
        data_purpose: dataValues.get('cta_data_purpose'),
        retention_period: dataValues.get('cta_data_retention_period'),
        deletion_path: dataValues.get('cta_data_deletion_path'),
        accountable_owner: dataValues.get('cta_data_retention_owner'),
        policy_effective_at: policyEffectiveAt,
        policy_checked_at: policyCheckedAt,
      }, brief.source, inspection.ref, problems);
      if (!/\b(?:accepted|confirmed|verified|pass(?:ed)?)\b/i.test(fields.get('capability_acceptance') || '')) {
        fail(problems, `${brief.source} ${inspection.ref} capability_acceptance must record affirmative owner or capability acceptance`);
      }
    }
    for (const inspection of deletionInspections) {
      const result = `${inspection.fields?.get('observed_result') || ''} ${inspection.fields?.get('capability_acceptance') || ''}`;
      if (!/\b(?:delete|deleted|deletion|remove|removed|purge|purged)\b/i.test(result)
        || !/\b(?:no longer readable|not readable|cannot be read|unreadable|read returns? not found|post[- ]deletion read (?:failed|blocked))\b/i.test(result)) {
        fail(problems, `${brief.source} ${inspection.ref} deletion-capability evidence must prove deletion completed and the deleted test record was no longer readable; HTTP 200 alone is insufficient`);
      }
      if (/\bhttp\s*200\b/i.test(result) && !/\b(?:no longer readable|not readable|cannot be read|unreadable|not found)\b/i.test(result)) {
        fail(problems, `${brief.source} ${inspection.ref} deletion-capability evidence cannot rely on HTTP 200 alone`);
      }
    }
  }

  const stage = normalizeText(string(brief, 'stage', problems));
  const sections = ctaSectionsForStage(draft.body, stage, false);
  const visible = normalizeText(markdownPlainText(sections.join('\n')));
  const labels = new Map([
    ['cta_data_purpose', /\bdata purpose\s*:/i],
    ['cta_data_retention_period', /\b(?:data )?retention period\s*:/i],
    ['cta_data_deletion_path', /\b(?:data )?deletion path\s*:/i],
    ['cta_data_retention_owner', /\b(?:data )?retention owner\s*:/i],
  ]);
  const visibleMarkdown = sections.join('\n');
  for (const field of dataValues.keys()) {
    if (!labels.get(field).test(markdownPlainText(visibleMarkdown)) || !visible.includes(normalizeText(dataValues.get(field)))) {
      fail(problems, `${draft.source} buyer-visible CTA must display an explicit ${field} label and the exact canonical value`);
    }
  }
}

function validateCanonicalEvidenceAxes(record, evidenceScope, evidenceRoot, problems) {
  const seenProductionRefs = new Map();
  const linkContractField = 'internal_link_buyer_task_contracts' in record.attributes
    ? 'internal_link_buyer_task_contracts'
    : ('internal_link_buyer_task_contracts_snapshot' in record.attributes ? 'internal_link_buyer_task_contracts_snapshot' : '');
  const linkContracts = linkContractField ? strings(record, linkContractField, problems, { allowEmpty: true }).map((row) => {
    const parts = row.split('|').map((part) => part.trim());
    return { role: parts[0] || '', url: parts[1] || '', task: parts[3] || '', owner: parts[7] || '' };
  }).filter((target) => target.url && target.role && target.task) : [];
  const linkApplicable = !('stage_link_requirement_status' in record.attributes) || normalizeText(string(record, 'stage_link_requirement_status', problems)) === 'applicable';
  const ctaApplicable = !('cta_input_collection_applicability' in record.attributes) || normalizeText(string(record, 'cta_input_collection_applicability', problems)) === 'applicable';
  const hasCtaTarget = ctaApplicable && ['stage_cta_mode', 'cta_destination', 'cta_trigger', 'cta_expected_output'].every((field) => field in record.attributes);
  const ctaTargets = hasCtaTarget ? [{
    role: normalizeText(string(record, 'stage_cta_mode', problems)),
    url: string(record, 'cta_destination', problems),
    task: `${string(record, 'cta_trigger', problems)} ${string(record, 'cta_expected_output', problems)}`,
    owner: string(record, 'cta_owner', problems),
  }] : [];
  for (const prefix of ['internal_link_reference', 'internal_link_reachability', 'internal_link_capability', 'cta_reference', 'cta_reachability', 'cta_capability']) {
    const executionField = `${prefix}_check_execution_status`;
    const resultField = `${prefix}_evidence_result`;
    const gateField = `${prefix}_gate_verdict`;
    const refsField = `${prefix}_evidence_refs`;
    if (!(executionField in record.attributes) || !(resultField in record.attributes) || !(gateField in record.attributes)) continue;
    const execution = string(record, executionField, problems);
    const result = string(record, resultField, problems);
    const gate = string(record, gateField, problems);
    const refs = refsField in record.attributes ? strings(record, refsField, problems, { allowEmpty: true }) : [];
    const applicable = prefix.startsWith('internal_link_') ? linkApplicable : ctaApplicable;
    if (!applicable) {
      if (![execution, result, gate].every((value) => normalizeText(value) === 'not-applicable')) fail(problems, `${record.source} ${prefix} axis must be not-applicable when its contract is not applicable`);
      if (refs.length) fail(problems, `${record.source} ${refsField} must be empty when ${prefix} is not applicable`);
      continue;
    }
    if (evidenceScope === 'synthetic-fixture') {
      const isCtaAxis = prefix.startsWith('cta_');
      const referenceAxis = prefix.endsWith('_reference');
      const expected = isCtaAxis ? ['not-run', 'missing', 'block']
        : (referenceAxis ? ['executed', 'synthetic-only', 'pass'] : ['not-run', 'missing', 'block']);
      if (execution !== expected[0] || result !== expected[1] || gate !== expected[2]) fail(problems, `${record.source} synthetic ${prefix} axis must be ${expected.join(' + ')}`);
      if (refsField in record.attributes && !isCtaAxis && referenceAxis && refs.length < 1) fail(problems, `${record.source} synthetic ${refsField} requires fixture evidence`);
      if (refsField in record.attributes && (isCtaAxis || !referenceAxis) && refs.length) fail(problems, `${record.source} synthetic non-executed ${refsField} must be empty`);
      continue;
    }
    if (execution !== 'executed' || result !== 'confirmed' || gate !== 'pass') fail(problems, `${record.source} production ${prefix} axis requires executed + confirmed + pass`);
    if (!(refsField in record.attributes)) continue;
    if (refs.length < 1) fail(problems, `${record.source} production ${refsField} requires axis-specific evidence declared by its Template`);
    const expectedKind = PRODUCTION_AXIS_EVIDENCE_KINDS.get(prefix);
    const expectedTargets = prefix.startsWith('internal_link_') ? linkContracts : ctaTargets;
    validateLocalEvidenceRefs(refs, record.source, refsField, evidenceRoot, problems, { requireFragment: true, regularNonSymlink: true, verifyFragment: true });
    const isCtaAxis = prefix.startsWith('cta_');
    const inspections = validateProductionEvidenceRefs(refs, record.source, refsField, evidenceRoot, problems, {
      expectedKinds: [expectedKind],
      expectedCheckId: prefix,
      expectedTargets,
      expectedOwner: isCtaAxis ? string(record, 'cta_owner', problems) : '',
      requiredExtraFields: isCtaAxis ? (prefix === 'cta_capability' ? ['accountable_owner', 'capability_acceptance'] : ['accountable_owner']) : [],
      requireStructuredSection: true,
    });
    const covered = new Set(inspections.map((inspection) => inspection.matchedTarget).filter((index) => index >= 0));
    if (expectedTargets.length && covered.size !== expectedTargets.length) fail(problems, `${record.source} production ${refsField} must cover every declared target with target-bound evidence`);
    for (const ref of refs) {
      const key = normalizeText(ref);
      const previous = seenProductionRefs.get(key);
      if (previous && previous !== prefix) fail(problems, `${record.source} generic one-section-for-all evidence is forbidden: ${ref} is reused for ${previous} and ${prefix}`);
      seenProductionRefs.set(key, prefix);
    }
  }
}

function validateCanonicalLocalEvidence(record, evidenceScope, evidenceRoot, problems) {
  for (const [field, raw] of Object.entries(record.attributes)) {
    if (!(field.endsWith('_refs') || field.endsWith('_ref'))) continue;
    if (field.endsWith('_evidence_refs') && /^(?:internal_link|cta)_(?:reference|reachability|capability)_/.test(field)) continue;
    const values = Array.isArray(raw) ? raw : [raw];
    const local = values.filter((value) => typeof value === 'string' && value.trim() && !/^https:/i.test(value) && !/^(?:none|not-applicable)$/i.test(value));
    if (!local.length) continue;
    const resolved = validateLocalEvidenceRefs(local, record.source, field, evidenceRoot, problems, { verifyFragment: evidenceScope === 'production', regularNonSymlink: evidenceScope === 'production' });
    if (evidenceScope === 'production') {
      rejectSyntheticEvidenceFiles(resolved, record.source, field, problems);
      validateProductionEvidenceRefs(local, record.source, field, evidenceRoot, problems);
    }
  }
  for (const field of ['role_handoff_contracts', 'internal_link_buyer_task_contracts', 'internal_link_buyer_task_contracts_snapshot']) {
    if (!(field in record.attributes)) continue;
    const refs = strings(record, field, problems, { allowEmpty: true }).map((row) => row.split('|').at(-1)?.trim() || '').filter((value) => value && !/^https:/i.test(value));
    if (!refs.length) continue;
    const resolved = validateLocalEvidenceRefs(refs, record.source, `${field} evidence ref`, evidenceRoot, problems, { verifyFragment: evidenceScope === 'production' });
    if (evidenceScope === 'production') {
      rejectSyntheticEvidenceFiles(resolved, record.source, `${field} evidence ref`, problems);
      validateProductionEvidenceRefs(refs, record.source, `${field} evidence ref`, evidenceRoot, problems);
    }
  }
}

function validateCanonicalBuyerContracts(brief, draft, evidenceScope, evidenceRoot, problems) {
  const taskContract = parseDominantTaskContract(brief, problems);
  validateSingleDominantTask(taskContract.action, brief.source, 'dominant_task_contract action', problems);
  const queryCluster = [string(brief, 'primary_query', problems), ...strings(brief, 'supporting_query_variants', problems)];
  validateThreeLayerPain(brief, taskContract.value, queryCluster, problems);
  validateThreeLayerPain(draft, taskContract.value, queryCluster, problems);
  validatePainContinuity(brief, problems);
  validatePainContinuity(draft, problems);
  validateDirectAnswerContract(draft, taskContract, problems);

  const activeRoles = [string(brief, 'primary_buyer_role', problems), ...strings(brief, 'secondary_buyer_roles', problems, { allowEmpty: true })];
  const ctaApplicable = normalizeText(string(brief, 'cta_input_collection_applicability', problems)) === 'applicable';
  const linkApplicable = normalizeText(string(brief, 'stage_link_requirement_status', problems)) === 'applicable';
  const handoffs = parseRoleHandoffContracts(brief, activeRoles, evidenceRoot, problems, evidenceScope === 'production');

  const productValues = strings(brief, 'product_decision_map', problems, { allowEmpty: true });
  const targetValues = strings(brief, 'internal_link_targets', problems, { allowEmpty: true });
  const contractValues = strings(brief, 'internal_link_buyer_task_contracts', problems, { allowEmpty: true });
  if (!linkApplicable) {
    if (productValues.length || targetValues.length || contractValues.length) fail(problems, `${brief.source} not-applicable stage link must not fabricate product or internal-link targets`);
    return;
  }
  const targetRoleByUrl = new Map(targetValues.map((value) => {
    const [role = '', url = ''] = value.split('|').map((part) => part.trim());
    return [normalizeText(url), normalizeText(role)];
  }).filter(([url]) => url));
  const productRows = parseProductDecisionMap(productValues, brief.source, evidenceRoot, problems, {
    productionEvidence: evidenceScope === 'production',
    targetRoleByUrl,
  });
  validateVisibleProductDecisionMap(productRows, draft, problems);

  const linkTargets = parseInternalLinkTargets(targetValues, brief.source, evidenceRoot, problems, {
    productionEvidence: evidenceScope === 'production',
    contractValues,
    dominantTask: taskContract.value,
  });
  const linkByRoleUrl = new Map(linkTargets.map((target) => [`${normalizeText(target.role)}|${normalizeText(target.url)}`, target]));
  for (const row of productRows) {
    if (!row.isStop) {
      const productEvidenceLevel = normalizeText(string(brief, 'product_link_evidence_level', problems));
      const requiredCandidateRole = productEvidenceLevel === 'family-level' ? 'solution' : 'product';
      if (!linkByRoleUrl.has(`${requiredCandidateRole}|${normalizeText(row.candidateTarget)}`)) fail(problems, `${brief.source} product_decision_map candidate target must bind to a declared ${requiredCandidateRole} internal-link contract: ${row.candidateTarget}`);
      if (internalLinkPublicationGatesPass(brief, problems)) {
        if (!draft.body.includes(`](${row.candidateTarget})`)) fail(problems, `${draft.source} product_decision_map candidate URL requires an actual Markdown link when all internal-link gates pass: ${row.candidateTarget}`);
      } else if (draft.body.includes(row.candidateTarget)) fail(problems, `${draft.source} blocked internal-link candidate URL must not be buyer-visible in Draft: ${row.candidateTarget}`);
    }
    const intakeContract = normalizeText(string(brief, 'stage_intake_contract', problems));
    const allowedNextRoles = intakeContract === 'buy-commercial'
      ? ['commercial', 'conversion']
      : ['technical-review', 'diagnostic', 'educational'];
    const validationTarget = [...linkTargets].find((target) => normalizeText(target.url) === normalizeText(row.nextValidationTarget)
      && allowedNextRoles.includes(normalizeText(target.role)));
    if (!validationTarget) fail(problems, `${brief.source} product_decision_map next validation target must bind to a declared ${allowedNextRoles.join('/')} internal-link contract for stage_intake_contract=${intakeContract}: ${row.nextValidationTarget}`);
    if (internalLinkPublicationGatesPass(brief, problems)) {
      if (!draft.body.includes(`](${row.nextValidationTarget})`)) fail(problems, `${draft.source} product_decision_map next-validation URL requires an actual Markdown link when all internal-link gates pass: ${row.nextValidationTarget}`);
    } else if (draft.body.includes(row.nextValidationTarget)) fail(problems, `${draft.source} blocked internal-link next-validation URL must not be buyer-visible in Draft: ${row.nextValidationTarget}`);
  }

  if (ctaApplicable) {
    const ctaContract = {
      trigger: string(brief, 'cta_trigger', problems),
      inputs: strings(brief, 'cta_required_inputs', problems),
      expectedOutput: string(brief, 'cta_expected_output', problems),
      boundary: string(brief, 'cta_validation_boundary', problems),
    };
    validateBuyerArticleSemanticStructure(brief, draft, string(brief, 'cta_destination', problems), ctaContract, problems);
  }
}

function validateCanonicalQualificationAndCta(brief, draft, review, publish, problems) {
  const ctaApplicable = normalizeText(string(brief, 'cta_input_collection_applicability', problems)) === 'applicable';
  if (!ctaApplicable) {
    for (const field of ['required_inquiry_inputs', 'cta_required_inputs', 'first_round_inquiry_inputs', 'second_round_inquiry_inputs', 'technical_qualification_gates', 'sales_acceptance_gates', 'qualification_reason_codes']) {
      if (strings(brief, field, problems, { allowEmpty: true }).length) fail(problems, `${brief.source} not-applicable input collection must not fabricate ${field}`);
    }
    for (const field of ['cta_trigger', 'cta_expected_output', 'cta_validation_boundary', 'cta_destination', 'cta_owner', 'technical_qualification_requirement', 'technical_qualification_contract_status', 'technical_qualification_definition', 'technical_qualification_owner', 'technical_qualification_next_step', 'sales_acceptance_requirement', 'sales_acceptance_contract_status', 'sales_acceptance_owner', 'sales_acceptance_next_step']) {
      if (!/^not-applicable$/i.test(string(brief, field, problems))) fail(problems, `${brief.source} not-applicable input collection requires ${field}=not-applicable`);
    }
    return;
  }
  const intake = normalizeText(string(brief, 'stage_intake_contract', problems));
  const requiredInputs = strings(brief, 'required_inquiry_inputs', problems);
  const ctaInputs = strings(brief, 'cta_required_inputs', problems);
  const minimumInputs = intake === 'validate-technical' ? 4 : (intake === 'buy-commercial' ? 3 : 1);
  validateInquiryInputs(requiredInputs, brief.source, 'required_inquiry_inputs', problems, { minItems: minimumInputs });
  validateInquiryInputs(ctaInputs, brief.source, 'cta_required_inputs', problems, { minItems: minimumInputs });
  if (ctaInputs.length > 6) fail(problems, `${brief.source} cta_required_inputs must remain a stage-appropriate 1-6 item first-round intake`);
  for (const field of ['cta_trigger', 'cta_expected_output', 'cta_validation_boundary', 'cta_destination', 'cta_owner']) {
    requireMeaningfulString(brief, field, problems, { minLength: field === 'cta_destination' ? 8 : 6 });
    rejectTemplatePlaceholder(string(brief, field, problems), brief.source, field, problems);
  }
  if (string(brief, 'cta_destination', problems) !== 'not-applicable') requireAbsoluteHttpsUrl(string(brief, 'cta_destination', problems), brief.source, 'cta_destination', problems);
  rejectOwnerPlaceholder(string(brief, 'cta_owner', problems), brief.source, 'cta_owner', problems);
  const canonicalFirstRound = strings(brief, 'first_round_inquiry_inputs', problems, { allowEmpty: true });
  const canonicalSecondRound = strings(brief, 'second_round_inquiry_inputs', problems, { allowEmpty: true });
  validateCtaInputCoverage(brief, ctaInputs, [...canonicalFirstRound, ...canonicalSecondRound], problems);
  for (const field of [
    'technical_qualification_definition', 'technical_qualification_owner', 'technical_qualification_next_step',
    'sales_acceptance_requirement', 'sales_acceptance_contract_status', 'sales_acceptance_next_step',
  ]) rejectTemplatePlaceholder(string(brief, field, problems), brief.source, field, problems);
  rejectOwnerPlaceholder(string(brief, 'technical_qualification_owner', problems), brief.source, 'technical_qualification_owner', problems);

  const reasonCodes = strings(brief, 'qualification_reason_codes', problems, { allowEmpty: true });
  const parsedCodes = reasonCodes.map((row) => row.split('|').map((part) => part.trim()));
  if (parsedCodes.some((parts) => parts.length !== 5 || parts.some((part) => part.length < 4))) {
    fail(problems, `${brief.source} qualification_reason_codes requires exact state|cause-category|evidence-rule|owner|next-step rows for the selected stage branch`);
  }
  const normalizedRows = parsedCodes.map((parts) => parts.map(normalizeText));
  const states = normalizedRows.map((parts) => parts[0]);
  if (new Set(states).size !== states.length) fail(problems, `${brief.source} qualification_reason_codes must contain each selected-branch state at most once`);

  const technicalStates = new Set(['first-round-complete', 'engineering-review-ready', 'technical-qualified', 'disqualified']);
  const commercialStates = new Set(['commercial-qualification-required', 'sales-accepted']);
  if (intake === 'validate-technical') {
    for (const state of ['needs-follow-up', 'first-round-complete', 'engineering-review-ready', 'technical-qualified', 'disqualified', 'commercial-qualification-required', 'sales-accepted']) {
      if (!states.includes(state)) fail(problems, `${brief.source} qualification_reason_codes requires exact lifecycle state ${state}`);
    }
    if (!normalizedRows.some((parts) => parts[0] === 'disqualified' && parts[1] === 'evidenced-technical-no-fit' && EXPLICIT_NO_FIT_PATTERN.test(parts.join(' ')))) {
      fail(problems, `${brief.source} qualification_reason_codes requires an explicit technical no-fit disqualified route`);
    }
  } else if (intake === 'troubleshoot-support') {
    if (!states.length) fail(problems, `${brief.source} troubleshoot-support requires diagnostic follow-up or evidenced-stop routing`);
    if (states.some((state) => technicalStates.has(state) || commercialStates.has(state))) fail(problems, `${brief.source} troubleshoot-support qualification_reason_codes may contain only diagnostic follow-up or evidenced-stop states`);
    if (!normalizedRows.some((parts) => /(?:follow-up|support-ready|diagnostic-stop)/.test(parts[0]))) fail(problems, `${brief.source} troubleshoot-support requires a diagnostic follow-up, support-ready, or diagnostic-stop state`);
  } else if (intake === 'compare-handoff') {
    if (states.some((state) => technicalStates.has(state) || state === 'sales-accepted')) fail(problems, `${brief.source} compare-handoff qualification_reason_codes must not inherit technical qualification or sales acceptance states`);
  } else if (intake === 'buy-commercial') {
    if (states.some((state) => technicalStates.has(state))) fail(problems, `${brief.source} buy-commercial qualification_reason_codes must not inherit technical qualification states`);
    for (const state of ['commercial-qualification-required', 'sales-accepted']) if (!states.includes(state)) {
      fail(problems, `${brief.source} buy-commercial qualification_reason_codes requires exact commercial state ${state}`);
    }
  }

  for (const field of [
    'technical_qualification_requirement', 'technical_qualification_contract_status', 'technical_qualification_definition',
    'technical_qualification_owner', 'technical_qualification_next_step', 'sales_acceptance_requirement',
    'sales_acceptance_contract_status', 'sales_acceptance_owner', 'sales_acceptance_next_step',
  ]) requireCanonicalMatch([brief, draft, publish], field, problems);
  requireCanonicalMatch([brief, draft, review, publish], 'qualification_reason_codes', problems);
}

function validateCanonicalStatusAndReviewContracts(records, brief, draft, review, publish, evidenceScope, evidenceRoot, problems) {
  const contentPurpose = string(brief, 'content_purpose', problems);
  const indexingIntent = string(brief, 'indexing_intent', problems);
  if (!CONTENT_PURPOSES.has(contentPurpose)) fail(problems, `${brief.source} content_purpose must be buyer-article or qa-format-lab`);
  if (!INDEXING_INTENTS.has(indexingIntent)) fail(problems, `${brief.source} indexing_intent is invalid`);
  if (contentPurpose === 'qa-format-lab' && indexingIntent !== 'noindex') fail(problems, 'QA / Format Lab content must be noindex');

  for (const record of records) {
    for (const field of ['package_id', 'brief_id', 'stage', 'dominant_task_contract']) rejectTemplatePlaceholder(string(record, field, problems), record.source, field, problems);
  }
  for (const [statusField, refsField] of [
    ['query_evidence_status', 'query_evidence_refs'], ['buyer_task_evidence_status', 'buyer_task_evidence_refs'], ['search_demand_evidence_status', 'search_demand_evidence_refs'],
    ['serp_format_evidence_status', 'serp_format_evidence_refs'], ['serp_gap_status', 'serp_gap_refs'],
    ['customer_language_status', 'customer_language_refs'], ['pain_evidence_status', 'pain_evidence_refs'],
    ['first_party_proof_status', 'first_party_proof_refs'],
  ]) {
    const status = string(brief, statusField, problems);
    if (!FACT_STATUSES.has(status)) fail(problems, `${brief.source} ${statusField} must use the canonical fact-status vocabulary`);
    const refs = strings(brief, refsField, problems, { allowEmpty: true });
    if (status === 'confirmed' && refs.length < 1) fail(problems, `${brief.source} confirmed ${statusField} requires ${refsField}`);
  }
  if (evidenceScope === 'synthetic-fixture') {
    if (string(brief, 'information_gain_artifact_status', problems) !== 'confirmed-for-fixture-structure') fail(problems, `${brief.source} synthetic information_gain_artifact_status must be confirmed-for-fixture-structure`);
    if (string(brief, 'market_information_gain_status', problems) !== 'missing') fail(problems, `${brief.source} synthetic market_information_gain_status must remain missing`);
    for (const field of ['production_evidence_score']) {
      for (const record of [review, publish]) if (field in record.attributes && normalizeText(string(record, field, problems)) !== 'not-applicable') fail(problems, `${record.source} synthetic ${field} must be not-applicable`);
    }
  } else {
    if (string(brief, 'information_gain_artifact_status', problems) !== 'confirmed') fail(problems, `${brief.source} production information_gain_artifact_status must be confirmed`);
    if (string(brief, 'market_information_gain_status', problems) !== 'confirmed') fail(problems, `${brief.source} production market_information_gain_status must be confirmed`);
    const ownerPage = string(brief, 'owner_page', problems);
    const targetMarket = string(brief, 'target_market', problems);
    const primaryQuery = string(brief, 'primary_query', problems);
    const seenSearchRefs = new Map();
    for (const [statusField, refsField] of [
      ['query_evidence_status', 'query_evidence_refs'],
      ['buyer_task_evidence_status', 'buyer_task_evidence_refs'],
      ['search_demand_evidence_status', 'search_demand_evidence_refs'],
      ['serp_format_evidence_status', 'serp_format_evidence_refs'],
      ['serp_gap_status', 'serp_gap_refs'],
    ]) {
      if (normalizeText(string(brief, statusField, problems)) !== 'confirmed') fail(problems, `${brief.source} production requires ${statusField}=confirmed`);
      const refs = strings(brief, refsField, problems, { allowEmpty: true });
      if (!refs.length) fail(problems, `${brief.source} production requires non-empty ${refsField}`);
      const kind = PRODUCTION_SEARCH_EVIDENCE_KINDS.get(refsField);
      validateProductionEvidenceRefs(refs, brief.source, refsField, evidenceRoot, problems, {
        expectedKinds: [kind],
        expectedCheckId: kind,
        expectedTargets: [{ url: ownerPage, role: kind, task: `${primaryQuery} | ${targetMarket} | ${kind}` }],
        requireStructuredSection: true,
        latestAllowedAt: string(review, 'reviewed_at', problems),
      });
      for (const ref of refs) {
        const key = normalizeText(ref);
        const previous = seenSearchRefs.get(key);
        if (previous && previous !== refsField) fail(problems, `${brief.source} generic one-section-for-all search evidence is forbidden: ${ref} is reused for ${previous} and ${refsField}`);
        seenSearchRefs.set(key, refsField);
      }
    }
  }
  const reviewerIdentity = requireMeaningfulString(review, 'reviewer_identity', problems, { minLength: 8 });
  rejectTemplatePlaceholder(reviewerIdentity, review.source, 'reviewer_identity', problems);
  requireIsoDate(string(review, 'reviewed_at', problems), review.source, 'reviewed_at', problems);
  if (normalizeText(reviewerIdentity) === normalizeText(string(draft, 'owner', problems))) {
    fail(problems, `${review.source} reviewer_identity must be independent from the Draft owner`);
  }
  if (string(review, 'unsupported_outcome_claims_verdict', problems) !== 'pass') fail(problems, `${review.source} unsupported_outcome_claims_verdict must be pass`);
  if (string(brief, 'unsupported_outcome_claims_status', problems) !== 'pass' || string(publish, 'unsupported_outcome_claims_status', problems) !== 'pass') {
    fail(problems, 'unsupported_outcome_claims_status must be pass across canonical package records');
  }
}


function exactNormalizedSet(values) {
  return new Set(values.map((value) => normalizeText(value)));
}

function requireExactSet(values, expected, source, field, problems) {
  const actualSet = exactNormalizedSet(values);
  const expectedSet = exactNormalizedSet(expected);
  if (values.length !== expected.length || actualSet.size !== expectedSet.size
    || [...expectedSet].some((value) => !actualSet.has(value))) {
    fail(problems, `${source} ${field} must exactly equal [${expected.join(', ')}]`);
  }
}

function markdownSectionRangeByHeading(body, headingPattern) {
  const source = String(body || '');
  const lines = source.split('\n');
  const offsets = [];
  let offset = 0;
  for (const line of lines) {
    offsets.push(offset);
    offset += line.length + 1;
  }
  let start = -1;
  let level = 7;
  for (let index = 0; index < lines.length; index += 1) {
    const match = /^(#{1,6})\s+(.+)$/.exec(lines[index]);
    headingPattern.lastIndex = 0;
    if (match && headingPattern.test(normalizeText(match[2]))) { start = index; level = match[1].length; break; }
  }
  if (start < 0) return null;
  let end = lines.length;
  for (let index = start + 1; index < lines.length; index += 1) {
    const match = /^(#{1,6})\s+/.exec(lines[index]);
    if (match && match[1].length <= level) { end = index; break; }
  }
  const startOffset = offsets[start];
  const endOffset = end < lines.length ? offsets[end] : source.length;
  return { text: source.slice(startOffset, endOffset).replace(/\n$/, ''), start: startOffset, end: endOffset, level };
}

function markdownSectionByHeading(body, headingPattern) {
  return markdownSectionRangeByHeading(body, headingPattern)?.text || '';
}

const CANONICAL_DECISION_H2_PATTERN = /^(?:use five decision blocks before (?:the )?first review|five[- ]input readiness check(?:list)?|first[- ]round readiness check(?:list)?|decision map)$/i;

function canonicalDecisionH2Sections(body) {
  return h2SectionRanges(body).filter((section) => CANONICAL_DECISION_H2_PATTERN.test(normalizeText(section.heading)));
}

function canonicalDecisionSection(body) {
  const sections = canonicalDecisionH2Sections(body);
  return sections.length === 1 ? sections[0].markdown : '';
}

function h3DecisionBlocks(sectionMarkdown) {
  const source = String(sectionMarkdown || '');
  const matches = [...source.matchAll(/^###\s+(.+)$/gm)];
  return matches.map((match, index) => {
    const start = (match.index || 0) + match[0].length;
    const end = matches[index + 1]?.index ?? source.length;
    return {
      heading: match[1].trim(),
      body: source.slice(start, end).trim(),
    };
  });
}

function validateFiveDecisionBlocks(sectionMarkdown, inputs, buyerTask, claim, source, problems) {
  const blocks = h3DecisionBlocks(sectionMarkdown);
  if (blocks.length !== 5) {
    fail(problems, `${source} decision-table asset requires exactly five distinct decision blocks inside its declared H2 section`);
    return false;
  }
  const headings = blocks.map((block) => normalizeText(block.heading));
  const bodies = blocks.map((block) => normalizeText(markdownPlainText(block.body)));
  if (new Set(headings).size !== blocks.length || new Set(bodies).size !== blocks.length) {
    fail(problems, `${source} decision-table asset requires five non-repeated decision blocks`);
    return false;
  }
  let valid = true;
  blocks.forEach((block, index) => {
    const plain = markdownPlainText(block.body);
    const normalized = normalizeText(plain);
    if (normalized.length < 35 || /^(?:generic|placeholder|note|continue)(?:\s+\w+){0,8}$/i.test(normalized)) {
      fail(problems, `${source} decision block ${index + 1} must contain concrete buyer-visible decision guidance`);
      valid = false;
    }
    if (!/\b(?:if|when|unless|missing|gap|without|incomplete|unknown|conflict|outside|limit|boundary)\b/i.test(plain)
      || !/\b(?:request|hold|separate|record|show|define|describe|summarize|explain|keep|stop|continue|review|check)\b/i.test(plain)) {
      fail(problems, `${source} decision block ${index + 1} must state a condition or evidence gap and a next action`);
      valid = false;
    }
    const input = inputs[index] || '';
    if (input && semanticOverlap(input, `${block.heading} ${plain}`).length < 1) {
      fail(problems, `${source} decision block ${index + 1} must bind the corresponding first-round input: ${input}`);
      valid = false;
    }
  });
  const sectionPlain = markdownPlainText(sectionMarkdown);
  if (semanticOverlap(buyerTask, sectionPlain).length < 2 || semanticOverlap(claim, sectionPlain).length < 2) {
    fail(problems, `${source} five decision blocks must collectively support the declared buyer task and claim`);
    valid = false;
  }
  return valid;
}

function expectedPlacementMatches(placement, link) {
  const expected = normalizeText(placement).replace(/\s+section$/, '');
  const actual = normalizeText(`${link.sectionH2} ${link.sectionH3}`);
  if (expected === 'opening' || expected === 'direct-answer') return link.sectionH2 === 'opening' || /direct answer/.test(actual);
  if (expected === 'candidate-or-stop' || expected === 'decision-path') return /candidate|stop|decision/.test(actual);
  if (expected === 'next-validation' || expected === 'evidence') return /next validation|validation|evidence/.test(actual);
  if (expected === 'comparison') return /compar/.test(actual);
  if (expected === 'faq') return /faq|question/.test(actual);
  if (expected === 'cta') return /cta|call to action|request|submit|send|prepare .*packet|engineering-readiness review|contact/.test(actual);
  return actual.includes(expected.replace(/-/g, ' '));
}

function internalLinkAnchorParity(url, canonicalAnchor, visibleAnchor, buyerTask) {
  const canonicalTokens = new Set(semanticTokens(`${canonicalAnchor} ${buyerTask}`));
  const visibleTokens = new Set(semanticTokens(visibleAnchor));
  const urlTokens = new Set(semanticTokens(new URL(url).pathname.replace(/[\/_-]+/g, ' ')));
  const contractOverlap = [...visibleTokens].filter((token) => canonicalTokens.has(token));
  const targetOverlap = [...visibleTokens].filter((token) => urlTokens.has(token));
  const canonicalConcepts = taskConcepts(`${canonicalAnchor} ${buyerTask}`);
  const visibleConcepts = taskConcepts(visibleAnchor);
  const conceptOverlap = [...visibleConcepts].filter((concept) => canonicalConcepts.has(concept));
  return contractOverlap.length >= 2
    || (contractOverlap.length >= 1 && targetOverlap.length >= 2)
    || (conceptOverlap.length >= 1 && targetOverlap.length >= 2);
}

const ACTION_FAMILY_PATTERNS = new Map([
  ['prepare', /\b(?:assemble|prepare|compile|complete|finali[sz]e|build|create|fill|organize|draft|document)\w*\b/i],
  ['validate', /\b(?:check|review|validate|assess|evaluate|inspect|verify|screen|test|audit)\w*\b/i],
  ['diagnose', /\b(?:diagnose|troubleshoot|isolate|investigate|debug|find\s+(?:the\s+)?root\s+cause)\w*\b/i],
  ['compare', /\b(?:compare|contrast|benchmark|weigh|evaluate\s+(?:the\s+)?options?)\w*\b/i],
  ['decide', /\b(?:choose|select|decide|qualify|reject|shortlist|advance|stop)\w*\b/i],
  ['transmit', /\b(?:submit|send|share|upload|email|forward|transfer|transmit|deliver|provide|dispatch|post|paste|attach|hand\s+over)\w*\b/i],
  ['navigate', /\b(?:proceed|continue|visit|open|use|follow|route|move)\w*\b/i],
]);

function leadingActionFamilies(value) {
  const full = normalizeText(value);
  const firstColon = full.indexOf(':');
  const hasShortPrefix = firstColon > 0
    && firstColon <= 80
    && !/[.!?;]/.test(full.slice(0, firstColon));
  const actionClause = hasShortPrefix ? full.slice(firstColon + 1).trim() : full;
  const normalized = actionClause.replace(/^(?:how\s+to|a\s+guide\s+to|guide\s+to|steps?\s+to)\s+/i, '');
  const matches = [];
  for (const [family, pattern] of ACTION_FAMILY_PATTERNS) {
    const match = pattern.exec(normalized);
    if (match) matches.push({ family, index: match.index });
  }
  if (!matches.length) return new Set();
  const firstIndex = Math.min(...matches.map((entry) => entry.index));
  return new Set(matches.filter((entry) => entry.index === firstIndex).map((entry) => entry.family));
}

function actionSlotsAlign(left, right) {
  const leftFamilies = leadingActionFamilies(left);
  const rightFamilies = leadingActionFamilies(right);
  return leftFamilies.size > 0 && rightFamilies.size > 0
    && [...leftFamilies].some((family) => rightFamilies.has(family));
}

function actionSlotParity(action, opening) {
  return actionSlotsAlign(action, opening);
}

function painSlotParity(label, contractSlot, visibleSlot) {
  if (semanticOverlap(contractSlot, visibleSlot).length >= 2) return true;
  const concepts = new Map([
    ['operating event', [
      /\b(?:choose|select|candidate|direction|program|project|route|duty|application)\w*\b/i,
      /\b(?:motor|product|supplier|system|component|solution)\w*\b/i,
    ]],
    ['evidence gap', [
      /\b(?:omit|missing|lack|unclear|incomplete|not comparable|cannot compare)\w*\b/i,
      /\b(?:evidence|input|assumption|label|data|specification|load|route|interface)\w*\b/i,
    ]],
    ['rework mechanism', [
      /\b(?:inconsistent|incompatible|different|missing|hidden|conflict|ambigu|repeat|rebuild|reconcil)\w*\b/i,
      /\b(?:recommend|assumption|clarif|comparison|reconcil|rework|review cycle|repeat|resolve|interface|duty)\w*\b/i,
    ]],
    ['program consequence', [
      /\b(?:sample validation|program|schedule|cycle|rework|delay|cost|risk)\w*\b/i,
      /\b(?:weak|wrong|unsuitable|avoidable|consume|enter|create|cause)\w*\b/i,
    ]],
    ['bounded decision', [
      /\b(?:assemble|prepare|complete|packet|input)\w*\b/i,
      /\b(?:candidate-or-stop|candidate|stop|bounded|decide|decision|review)\w*\b/i,
    ]],
  ]);
  const patterns = concepts.get(label) || [];
  return patterns.length > 0 && patterns.every((pattern) => pattern.test(contractSlot) && pattern.test(visibleSlot));
}

function structurallyVerifiedFallbackEndpoint(record) {
  const value = record?.attributes?.cta_fallback_route_contract;
  if (typeof value !== 'string') return null;
  const parts = value.split('|').map((part) => part.trim());
  if (parts.length !== 17 || parts.some((part) => !part)) return null;
  const [status, endpoint, , , ,
    referenceExecution, referenceResult, referenceVerdict, referenceRefsRaw,
    reachabilityExecution, reachabilityResult, reachabilityVerdict, reachabilityRefsRaw,
    capabilityExecution, capabilityResult, capabilityVerdict, capabilityRefsRaw] = parts;
  if (status !== 'verified' || !isConcreteFallbackEndpoint(endpoint)) return null;
  const axes = [
    [referenceExecution, referenceResult, referenceVerdict, referenceRefsRaw],
    [reachabilityExecution, reachabilityResult, reachabilityVerdict, reachabilityRefsRaw],
    [capabilityExecution, capabilityResult, capabilityVerdict, capabilityRefsRaw],
  ];
  if (!axes.every(([execution, result, verdict, refs]) => execution === 'executed'
    && result === 'confirmed'
    && verdict === 'pass'
    && refs !== 'not-applicable'
    && refs.split(',').map((ref) => ref.trim()).filter(Boolean).length > 0)) return null;
  return endpoint;
}

function validateV10SlateLinks(brief, draft, formatProfile, problems) {
  const links = formatProfile.links || [];
  const linkApplicable = normalizeText(string(brief, 'stage_link_requirement_status', problems)) === 'applicable';
  const ctaApplicable = normalizeText(string(brief, 'cta_input_collection_applicability', problems)) === 'applicable';
  const contracts = strings(brief, 'internal_link_buyer_task_contracts', problems, { allowEmpty: true });
  const publicationGatesPass = internalLinkPublicationGatesPass(brief, problems);
  const contractUrls = new Set(contracts.map((row) => row.split('|')[1]?.trim()).filter(Boolean));
  const ctaDestination = ctaApplicable ? string(brief, 'cta_destination', problems) : 'not-applicable';
  const verifiedFallbackEndpoint = ctaApplicable ? structurallyVerifiedFallbackEndpoint(brief) : null;
  const allowedVisibleUrls = new Set([
    ...(publicationGatesPass && linkApplicable ? contractUrls : []),
    ...(ctaDestination !== 'not-applicable' ? [ctaDestination] : []),
    ...(verifiedFallbackEndpoint ? [verifiedFallbackEndpoint] : []),
  ]);
  for (const link of links) {
    if (!allowedVisibleUrls.has(link.url)) {
      fail(problems, `${draft.source} buyer-visible link URL is undeclared or has not passed its applicable internal-link/CTA gates: ${link.url}`);
    }
    if (contractUrls.has(link.url) && !publicationGatesPass) {
      fail(problems, `${draft.source} internal-link URL must not be buyer-visible until reference, reachability, and capability gates all pass: ${link.url}`);
    }
  }
  const bodyWithoutImages = String(draft.body || '').replace(/!\[[^\]\n]*\]\(https:\/\/[^)\s]+(?:\s+["'][^"']*["'])?\)/g, '');
  const visibleAbsoluteUrls = bodyWithoutImages.match(/https:\/\/[^\s)\]}>]+/gi) || [];
  for (const rawUrl of visibleAbsoluteUrls) {
    const url = rawUrl.replace(/[.,;:!?]+$/, '');
    if (!allowedVisibleUrls.has(url)) fail(problems, `${draft.source} buyer-visible plain or linked URL is undeclared or has not passed its applicable gates: ${url}`);
  }
  if (linkApplicable) for (const row of contracts) {
    const parts = row.split('|').map((part) => part.trim());
    if (parts.length !== 9) continue;
    const [, url, anchor, buyerTask, , placement] = parts;
    const matches = links.filter((link) => link.url === url);
    if (!publicationGatesPass) {
      if (matches.length || String(draft.body || '').includes(url)) {
        fail(problems, `${draft.source} internal-link URL must not be buyer-visible until reference, reachability, and capability gates all pass: ${url}`);
      }
      continue;
    }
    if (!matches.length) {
      fail(problems, `${draft.source} internal-link URL must be a real Markdown-to-Slate link node, not plain text: ${url}`);
      continue;
    }
    const anchorMatches = matches.filter((link) => internalLinkAnchorParity(url, anchor, link.anchorText, buyerTask));
    if (!anchorMatches.length) fail(problems, `${draft.source} internal-link anchor must preserve target identity and buyer-task parity for ${url}: ${anchor}`);
    else if (!anchorMatches.some((link) => expectedPlacementMatches(placement, link))) {
      fail(problems, `${draft.source} internal-link ${url} must appear in its canonical placement section ${placement}`);
    }
  }
  if (!ctaApplicable) return;
  const ctaLinks = links.filter((link) => link.url === ctaDestination);
  if (ctaDestination !== 'not-applicable' && !ctaLinks.length) fail(problems, `${draft.source} CTA destination must be a real Markdown-to-Slate link node, not plain text: ${ctaDestination}`);
  for (const link of ctaLinks) {
    if (GENERIC_ANCHORS.has(link.normalizedAnchor)) fail(problems, `${draft.source} CTA link anchor must be action/output specific, not generic: ${link.anchorText}`);
    if (!/\b(?:request|submit|send|open|prepare|download|build|start|compare|check|review|receive|get|book|schedule|define|create|assemble)\w*\b/i.test(link.anchorText)) {
      fail(problems, `${draft.source} CTA link anchor must name an action or expected output: ${link.anchorText}`);
    }
    if (!expectedPlacementMatches('cta', link)) fail(problems, `${draft.source} CTA link must appear in a CTA section`);
  }
}

function requireExactGateClaims(evidenceRule, expected, source, state, problems) {
  const normalized = normalizeText(evidenceRule);
  const gateLike = [...new Set((normalized.match(/\b[a-z]+(?:-[a-z]+)+\b/g) || [])
    .filter((gate) => expected.includes(gate) || /(?:complete|accepted|required|intent|no-fit|approved|reviewed|satisfied)$/.test(gate)))];
  const expectedSet = exactNormalizedSet(expected);
  if (gateLike.length !== expected.length || gateLike.some((gate) => !expectedSet.has(gate))) {
    fail(problems, `${source} ${state} evidence-rule must contain exactly [${expected.join(', ')}] and no extra gate`);
  }
}

function validateV10Qualification(brief, draft, publish, problems) {
  if (normalizeText(string(brief, 'stage_intake_contract', problems)) !== 'validate-technical') return;
  const first = strings(brief, 'first_round_inquiry_inputs', problems);
  const second = strings(brief, 'second_round_inquiry_inputs', problems);
  const technicalGates = strings(brief, 'technical_qualification_gates', problems);
  const salesGates = strings(brief, 'sales_acceptance_gates', problems);
  const expectedTechnical = ['first-round-complete', 'second-round-complete', 'no-evidenced-no-fit', 'named-technical-owner-accepted'];
  const expectedSales = ['explicit-commercial-intent', 'commercial-qualification-required', 'commercial-inputs-complete', 'named-commercial-owner-reviewed-and-accepted'];
  requireExactSet(technicalGates, expectedTechnical, brief.source, 'technical_qualification_gates', problems);
  requireExactSet(salesGates, expectedSales, brief.source, 'sales_acceptance_gates', problems);
  requireCanonicalMatch([brief, draft, publish], 'technical_qualification_gates', problems);
  requireCanonicalMatch([brief, draft, publish], 'sales_acceptance_gates', problems);

  const rows = strings(brief, 'qualification_reason_codes', problems);
  const byState = new Map();
  for (const row of rows) {
    const parts = row.split('|').map((part) => part.trim());
    if (parts.length !== 5 || parts.some((part) => part.length < 4)) {
      fail(problems, `${brief.source} qualification_reason_codes row must use exact five-part cause-first grammar state|cause-category|evidence-rule|owner|next-step: ${row}`);
      continue;
    }
    const [state, cause, evidenceRule, owner, nextStep] = parts.map(normalizeText);
    if (!QUALIFICATION_PROGRESS_STATES.has(state)) fail(problems, `${brief.source} qualification_reason_codes uses unknown exact state ${parts[0]}`);
    if (byState.has(state)) fail(problems, `${brief.source} qualification_reason_codes must contain each lifecycle state exactly once: ${state}`);
    byState.set(state, { state, cause, evidenceRule, owner, nextStep, raw: row });
  }
  for (const state of QUALIFICATION_PROGRESS_STATES) if (!byState.has(state)) fail(problems, `${brief.source} qualification_reason_codes requires exact lifecycle state ${state}`);
  const causeByState = new Map([
    ['needs-follow-up', 'missing-input'],
    ['first-round-complete', 'first-round-inputs-complete'],
    ['engineering-review-ready', 'technical-owner-first-round-acceptance'],
    ['technical-qualified', 'technical-gates-satisfied'],
    ['disqualified', 'evidenced-technical-no-fit'],
    ['commercial-qualification-required', 'explicit-commercial-intent'],
    ['sales-accepted', 'commercial-gates-satisfied'],
  ]);
  for (const [state, expectedCause] of causeByState) {
    const row = byState.get(state);
    if (row && row.cause !== expectedCause) fail(problems, `${brief.source} ${state} must use cause-category=${expectedCause}`);
  }
  for (const row of byState.values()) {
    const text = `${row.cause} ${row.evidenceRule} ${row.nextStep}`;
    const missing = /\b(?:missing|incomplete|not supplied|required input)\b/.test(text);
    const commercial = commercialClassification(text).commercial;
    if (missing && row.state !== 'needs-follow-up') fail(problems, `${brief.source} missing inputs may route only to needs-follow-up, not ${row.state}`);
    if (commercial && row.state === 'disqualified') fail(problems, `${brief.source} commercial intent may route only to commercial-qualification-required, never disqualified`);
    if (row.state === 'disqualified' && !EXPLICIT_NO_FIT_PATTERN.test(text)) fail(problems, `${brief.source} disqualified requires evidenced technical incompatibility/out-of-envelope/unsupported scope`);
  }
  const technical = byState.get('technical-qualified');
  if (technical) requireExactGateClaims(technical.evidenceRule, expectedTechnical, brief.source, 'technical-qualified', problems);
  const sales = byState.get('sales-accepted');
  if (sales) requireExactGateClaims(sales.evidenceRule, expectedSales, brief.source, 'sales-accepted', problems);
  const commercialRoute = byState.get('commercial-qualification-required');
  if (commercialRoute && (!COMMERCIAL_OWNER_PATTERN.test(commercialRoute.owner) || TECHNICAL_OWNER_PATTERN.test(commercialRoute.owner) && !COMMERCIAL_OWNER_PATTERN.test(commercialRoute.owner))) {
    fail(problems, `${brief.source} commercial-qualification-required requires a named commercial/sales owner, not a sole technical owner`);
  }
  validateSecondRoundInputRelationships(brief, first, second, problems);
}

function validateV10Applicability(records, brief, draft, problems) {
  const interaction = string(brief, 'cta_interaction_type', problems);
  const applicability = string(brief, 'cta_input_collection_applicability', problems);
  const reason = string(brief, 'cta_input_collection_not_applicable_reason', problems);
  const collecting = new Set(['input-collecting', 'human-handoff', 'commercial']);
  const allowed = new Set(['inline-no-input', 'local-tool', ...collecting]);
  if (!allowed.has(interaction)) fail(problems, `${brief.source} cta_interaction_type must be exact lowercase inline-no-input|local-tool|input-collecting|human-handoff|commercial`);
  if (!['applicable', 'not-applicable'].includes(applicability)) fail(problems, `${brief.source} cta_input_collection_applicability must be applicable or not-applicable`);
  requireCanonicalMatch(records, 'cta_interaction_type', problems);
  requireCanonicalMatch(records, 'cta_input_collection_applicability', problems);
  requireCanonicalMatch(records, 'cta_input_collection_not_applicable_reason', problems);
  const ctaInputs = strings(brief, 'cta_required_inputs', problems, { allowEmpty: true });
  if (applicability === 'applicable') {
    if (!collecting.has(interaction)) fail(problems, `${brief.source} applicable input collection requires input-collecting, human-handoff, or commercial interaction`);
    if (normalizeText(reason) !== 'not-applicable') fail(problems, `${brief.source} applicable input collection requires not-applicable reason sentinel`);
    const intake = normalizeText(string(brief, 'stage_intake_contract', problems));
    const minimumInputs = intake === 'validate-technical' ? 4 : (intake === 'buy-commercial' ? 3 : 1);
    if (ctaInputs.length < minimumInputs || ctaInputs.length > 6) fail(problems, `${brief.source} applicable input collection requires a stage-appropriate ${minimumInputs}-6 item first-round exact set`);
  } else {
    if (collecting.has(interaction)) fail(problems, `${brief.source} ${interaction} cannot declare cta_input_collection_applicability=not-applicable`);
    meaningfulScalar(reason, brief.source, 'cta_input_collection_not_applicable_reason', problems, { minLength: 12 });
    if (/^not-applicable$/i.test(reason)) fail(problems, `${brief.source} not-applicable input collection requires a concrete reason`);
    if (ctaInputs.length) fail(problems, `${brief.source} not-applicable input collection must not fabricate cta_required_inputs`);
    const forbiddenArrayFields = [
      'required_inquiry_inputs', 'cta_required_inputs', 'first_round_inquiry_inputs', 'second_round_inquiry_inputs',
      'cta_progressive_profiling_omitted_inputs', 'technical_qualification_gates',
      'sales_acceptance_gates', 'qualification_reason_codes', 'sales_commercial_inputs', 'disqualifiers',
    ];
    const notApplicableScalarFields = [
      'cta_contract_status', 'cta_input_collection_mode', 'cta_input_alignment_status', 'cta_progressive_profiling_status',
      'cta_progressive_profiling_followup_action', 'cta_progressive_profiling_followup_owner',
      'cta_complete_over_six_justification', 'cta_soft_path',
      'cta_trigger', 'cta_expected_output', 'cta_validation_boundary', 'cta_destination', 'cta_owner',
      'cta_fallback_message_template', 'technical_qualification_requirement', 'technical_qualification_contract_status',
      'technical_qualification_definition', 'technical_qualification_owner', 'technical_qualification_next_step',
      'sales_acceptance_requirement', 'sales_acceptance_contract_status', 'sales_acceptance_definition',
      'sales_commercial_intent_required', 'sales_commercial_intent_status', 'sales_commercial_inputs_status',
      'sales_acceptance_owner', 'sales_acceptance_next_step', 'cta_stage_contract_verdict',
      'technical_qualification_verdict', 'sales_acceptance_verdict',
    ];
    for (const record of records) {
      for (const field of forbiddenArrayFields) {
        if (field in record.attributes && strings(record, field, problems, { allowEmpty: true }).length) {
          fail(problems, `${record.source} not-applicable input collection must not fabricate ${field}`);
        }
      }
      for (const field of notApplicableScalarFields) {
        if (field in record.attributes && normalizeText(string(record, field, problems)) !== 'not-applicable') {
          fail(problems, `${record.source} not-applicable input collection requires ${field}=not-applicable`);
        }
      }
    }
  }
  const linkStatus = string(brief, 'stage_link_requirement_status', problems);
  const linkReason = string(brief, 'stage_link_not_applicable_reason', problems);
  requireCanonicalMatch(records, 'stage_link_requirement_status', problems);
  requireCanonicalMatch(records, 'stage_link_not_applicable_reason', problems);
  if (!['applicable', 'not-applicable'].includes(linkStatus)) fail(problems, `${brief.source} stage_link_requirement_status must be applicable or not-applicable`);
  if (linkStatus === 'applicable') {
    if (normalizeText(linkReason) !== 'not-applicable') fail(problems, `${brief.source} applicable stage link requires not-applicable reason sentinel`);
    if (!strings(brief, 'stage_required_link_roles', problems, { allowEmpty: true }).length) fail(problems, `${brief.source} applicable stage link requires stage_required_link_roles`);
  } else {
    meaningfulScalar(linkReason, brief.source, 'stage_link_not_applicable_reason', problems, { minLength: 12 });
    if (/^not-applicable$/i.test(linkReason)) fail(problems, `${brief.source} not-applicable stage link requires a concrete reason`);
    const forbiddenLinkArrays = [
      'stage_required_link_roles', 'internal_link_targets', 'internal_link_buyer_task_contracts',
      'internal_link_buyer_task_contracts_snapshot', 'product_decision_map', 'product_decision_map_snapshot',
    ];
    const notApplicableLinkScalars = [
      'internal_link_plan_status', 'product_decision_map_status', 'product_decision_map_verdict',
      'internal_link_stage_contract_verdict',
    ];
    for (const record of records) {
      for (const field of forbiddenLinkArrays) {
        if (field in record.attributes && strings(record, field, problems, { allowEmpty: true }).length) {
          fail(problems, `${record.source} not-applicable stage link must not fabricate ${field}`);
        }
      }
      for (const field of notApplicableLinkScalars) {
        if (field in record.attributes && normalizeText(string(record, field, problems)) !== 'not-applicable') {
          fail(problems, `${record.source} not-applicable stage link requires ${field}=not-applicable`);
        }
      }
    }
  }
}

function sectionContainsExactInputs(section, inputs) {
  const normalized = normalizeText(markdownPlainText(section));
  const visibleTokens = new Set(semanticTokens(normalized));
  return inputs.every((input) => {
    const exact = normalizeText(input);
    if (normalized.includes(exact)) return true;
    const requiredTokens = semanticTokens(exact);
    const matched = requiredTokens.filter((token) => visibleTokens.has(token));
    return requiredTokens.length >= 2 && matched.length / requiredTokens.length >= 0.8;
  });
}

function validateV10ProgressiveCta(brief, draft, problems) {
  if (normalizeText(string(brief, 'stage_intake_contract', problems)) !== 'validate-technical') return;
  const first = strings(brief, 'first_round_inquiry_inputs', problems);
  const second = strings(brief, 'second_round_inquiry_inputs', problems);
  requireExactSet(strings(brief, 'cta_required_inputs', problems), first, brief.source, 'cta_required_inputs', problems);
  const fallback = string(brief, 'cta_fallback_message_template', problems);
  if (!/\b(?:single|completed|prepared|local|readiness)\s+worksheet\b/i.test(fallback) && !first.every((input) => normalizeText(fallback).includes(normalizeText(input)))) fail(problems, `${brief.source} copyable CTA fallback must contain the first-round exact set or reference the canonical prepared worksheet`);
  if (second.some((input) => normalizeText(fallback).includes(normalizeText(input)))) fail(problems, `${brief.source} copyable CTA fallback must not collect second-round inputs`);
  const roundTwo = markdownSectionByHeading(draft.body, /round two|second-round/);
  if (!roundTwo || !sectionContainsExactInputs(roundTwo, second)) fail(problems, `${draft.source} technical-owner round-two prose must visibly contain the second-round exact set`);
  const checklist = canonicalDecisionSection(draft.body);
  const preparation = markdownSectionByHeading(draft.body, /prepare .*locally|local preparation|readiness worksheet/i);
  let finalCta = markdownSectionByHeading(draft.body, /request .*engineering-readiness review|final cta|submit .*review|send .*review/i);
  finalCta = finalCta.split(/^###\s+Copyable (?:local|route-request) fallback\s*$/mi)[0];
  for (const [label, section] of [['first-round checklist', checklist], ['soft CTA', preparation], ['final CTA', finalCta]]) {
    const normalizedSection = normalizeText(markdownPlainText(section));
    if (second.some((input) => normalizedSection.includes(normalizeText(input)))) {
      fail(problems, `${draft.source} ${label} must not collect second-round inputs`);
    }
  }
  validateSecondRoundInputRelationships(brief, first, second, problems);
}

function validateV10DirectAnswer(records, brief, draft, problems) {
  for (const field of ['direct_answer_action', 'direct_answer_object', 'direct_answer_required_inputs_or_evidence', 'direct_answer_condition_or_boundary', 'direct_answer_expected_output_or_route', 'direct_answer_evidence_boundary']) requireCanonicalMatch(records, field, problems);
  const action = string(brief, 'direct_answer_action', problems);
  const object = string(brief, 'direct_answer_object', problems);
  const inputs = strings(brief, 'direct_answer_required_inputs_or_evidence', problems);
  const condition = string(brief, 'direct_answer_condition_or_boundary', problems);
  const output = string(brief, 'direct_answer_expected_output_or_route', problems);
  const boundary = string(brief, 'direct_answer_evidence_boundary', problems);
  const openingBlockText = markdownPlainText(draft.body.split(/^##\s/m)[0]);
  const opening = normalizeText(openingBlockText);
  const openingBlock = opening;
  const task = parseDominantTaskContract(brief, problems);
  const dominantSearchIntent = string(brief, 'dominant_search_intent', problems);
  if (!actionSlotsAlign(action, task.action)) fail(problems, `${brief.source} direct_answer_action must match dominant_task_contract action`);
  if (!actionSlotsAlign(task.action, dominantSearchIntent)) fail(problems, `${brief.source} dominant_search_intent leading action must match dominant_task_contract action`);
  if (!DIRECT_ANSWER_JUDGMENT_PATTERN.test(action) || !actionSlotParity(action, opening)) fail(problems, `${draft.source} complete opening block must implement the direct-answer action slot`);
  if (semanticOverlap(object, opening).length < 2 || semanticOverlap(object, task.decisionObject).length < 2) fail(problems, `${draft.source} complete opening block must implement the decision-object slot`);
  if (!inputs.length) fail(problems, `${brief.source} direct_answer_required_inputs_or_evidence must contain at least one bounded input or evidence slot`);
  if (/\b(?:banana|lantern|wallpaper|applaud|random|unrelated)\b/i.test(openingBlock)) fail(problems, `${draft.source} visible opening block contains unrelated word-salad terms`);
  if (!/\b(?:when|if|only|unless|otherwise|missing|without|until|boundary|stop|no-fit|incompatib|unsupported|out-of-envelope)\b/i.test(opening)
    || semanticOverlap(condition, opening).length < 2) fail(problems, `${draft.source} opening direct answer must state the condition/boundary slot`);
  if (!/\b(?:output|result|route|return|candidate|stop|review|decision|readiness|follow-up)\b/i.test(opening)
    || semanticOverlap(output, opening).length < 2) fail(problems, `${draft.source} opening direct answer must state the expected output/route slot`);
  if (!/\b(?:does not|do not|cannot|not prove|missing|synthetic|unverified|deferred|measured|evidence)\b/i.test(opening)
    || semanticOverlap(boundary, opening).length < 2) fail(problems, `${draft.source} opening direct answer must state the evidence boundary slot`);
}

function validateV10PainChain(brief, draft, problems) {
  requireCanonicalMatch([brief, draft], 'pain_chain_contract', problems);
  const parts = string(brief, 'pain_chain_contract', problems).split('|').map((part) => part.trim());
  if (parts.length !== 6 || parts.some((part) => part.length < 8)) {
    fail(problems, `${brief.source} pain_chain_contract must use actor|operating-event|evidence-gap|rework-mechanism|program-consequence|bounded-decision`);
    return;
  }
  const [actor, event, gap, rework, consequence, decision] = parts;
  const primaryRole = string(brief, 'primary_buyer_role', problems);
  const canonicalRole = requireCanonicalBuyerRole(primaryRole, brief.source, 'primary_buyer_role', problems, { canonicalOnly: true });
  if (semanticOverlap(actor, primaryRole).length < 1 && !ROLE_SEMANTIC_PATTERNS.get(canonicalRole)?.test(actor)) {
    fail(problems, `${brief.source} pain_chain_contract actor must bind to the primary buyer role`);
  }
  const pairs = [
    ['Trigger', 'operating event', event, string(brief, 'pain_trigger', problems), PAIN_ROLE_PATTERNS.get('pain_trigger')],
    ['Evidence gap', 'evidence gap', gap, string(brief, 'surface_problem', problems), PAIN_ROLE_PATTERNS.get('surface_problem')],
    ['Rework', 'rework mechanism', rework, string(brief, 'operational_friction', problems), PAIN_ROLE_PATTERNS.get('operational_friction')],
    ['Consequence', 'program consequence', consequence, string(brief, 'business_consequence', problems), PAIN_ROLE_PATTERNS.get('business_consequence')],
    ['Decision', 'bounded decision', decision, string(brief, 'desired_decision', problems), PAIN_ROLE_PATTERNS.get('desired_decision')],
  ];
  for (const [, parityLabel, contractSlot, visibleSlot, pattern] of pairs) {
    if (!pattern.test(visibleSlot) || !painSlotParity(parityLabel, contractSlot, visibleSlot)) {
      fail(problems, `${brief.source} pain chain ${parityLabel} lacks structured parity with its visible field`);
    }
  }
  const chainText = pairs.map(([, , , visible]) => visible).join(' ');
  if (/\b(?:banana|lantern|wallpaper|applaud|random|unrelated)\b/i.test(chainText)) fail(problems, `${brief.source} pain chain contains unrelated word-salad terms`);

  const expectedLabels = ['Actor', 'Trigger', 'Evidence gap', 'Rework', 'Consequence', 'Decision'];
  const controlRows = strings(brief, 'visible_pain_chain', problems, { allowEmpty: true });
  const controlNodes = controlRows.map((row, index) => {
    const [label, ...valueParts] = row.split('|');
    const value = valueParts.join('|').trim();
    if (label !== expectedLabels[index] || !value) fail(problems, `${brief.source} visible_pain_chain row ${index + 1} must use ${expectedLabels[index]}|machine-control-value in canonical order`);
    return { label, value };
  });
  if (controlNodes.length !== 6) {
    fail(problems, `${brief.source} visible_pain_chain must contain exactly six machine-control rows`);
    return;
  }

  const candidateRuns = [];
  for (const section of h2SectionRanges(draft.body).map((entry) => entry.markdown)) {
    const numbered = [...section.matchAll(/^\s*(\d+)\.\s+(.+)$/gm)]
      .map((match) => ({ number: Number(match[1]), value: markdownPlainText(match[2]).trim() }));
    if (numbered.length !== 6 || !numbered.every((node, index) => node.number === index + 1 && node.value)) continue;
    const values = numbered.map((node) => node.value);
    const slotParity = values.every((value, index) => {
      if (index === 0) return ROLE_SEMANTIC_PATTERNS.get(canonicalRole)?.test(value)
        && semanticOverlap(actor, value).length >= 1
        && semanticOverlap(controlNodes[index].value, value).length >= 1;
      const parityLabel = pairs[index - 1][1];
      return painSlotParity(parityLabel, parts[index], value)
        && semanticOverlap(controlNodes[index].value, value).length >= 1;
    });
    if (slotParity) candidateRuns.push({ section, values });
  }
  if (candidateRuns.length !== 1) {
    fail(problems, `${draft.source} visible pain chain requires exactly one buyer-visible H2 section with six ordered natural-language nodes that semantically bind the canonical control slots; found ${candidateRuns.length}`);
    return;
  }
  const { section: painSection, values: visibleValues } = candidateRuns[0];
  if (/^\s*\d+\.\s+(?:\*\*)?(?:Actor|Trigger|Evidence\s+gap|Rework|Consequence|Decision)(?::|\*\*:)/mi.test(painSection)) {
    fail(problems, `${draft.source} buyer-visible pain chain must use natural buyer language and must not expose internal Actor/Trigger/Evidence gap/Rework/Consequence/Decision audit labels`);
  }
  const slotChecks = [
    ['Actor', actor, visibleValues[0], 'actor'],
    ...pairs.map(([visibleLabel, parityLabel, contractSlot], index) => [visibleLabel, contractSlot, visibleValues[index + 1], parityLabel]),
  ];
  if (!ROLE_SEMANTIC_PATTERNS.get(canonicalRole)?.test(visibleValues[0]) || semanticOverlap(actor, visibleValues[0]).length < 1) {
    fail(problems, `${draft.source} visible pain chain Actor slot must bind the contract actor and primary buyer role`);
  }
  for (const [label, contractSlot, visibleValue, parityLabel] of slotChecks.slice(1)) {
    if (!painSlotParity(parityLabel, contractSlot, visibleValue)) fail(problems, `${draft.source} visible pain chain ${label} node lacks contract parity`);
  }
  const bridgePattern = /\b(?:when|after|before|because|therefore|thus|as a result|which forces?|leads? to|results? in|so that|otherwise|that (?:gap|evidence gap|rework|delay|failure)|the (?:gap|evidence gap|rework|repeated review|consequence))\b/i;
  for (let index = 0; index < visibleValues.length - 1; index += 1) {
    const left = visibleValues[index];
    const right = visibleValues[index + 1];
    const overlap = semanticOverlap(left, right).filter((token) => !new Set(['buyer', 'engineer', 'engineering', 'motor', 'product', 'candidate', 'review']).has(token));
    if (!overlap.length && !bridgePattern.test(`${left} ${right}`)) {
      fail(problems, `${draft.source} visible pain chain lacks adjacent causality between ${expectedLabels[index]} and ${expectedLabels[index + 1]}`);
    }
  }
  if (/\b(?:banana|lantern|wallpaper|applaud|random|unrelated)\b/i.test(markdownPlainText(painSection))) fail(problems, `${draft.source} visible pain chain contains unrelated word-salad terms`);
}
function loadReferencedSection(ref, evidenceRoot) {
  const { pathPart, fragment } = splitLocalRef(ref);
  if (!pathPart || !fragment) return '';
  const target = resolve(evidenceRoot, pathPart);
  if (!existsSync(target) || !statSync(target).isFile()) return '';
  try { return markdownSectionBody(parseArticleMarkdownFrontMatter(readFileSync(target, 'utf8'), { source: target }).body, fragment); }
  catch { return ''; }
}

function validateV10ZeroResult(brief, review, evidenceScope, evidenceRoot, problems) {
  const reviewedAt = string(review, 'reviewed_at', problems);
  for (const ref of strings(brief, 'inventory_zero_result_evidence_refs', problems, { allowEmpty: true })) {
    const section = loadReferencedSection(ref, evidenceRoot);
    if (!section) continue;
    const canonical = securityCanonicalText(section);
    const normalized = normalizeText(section);
    const candidateCounts = [...canonical.matchAll(/(?:^|\n)\s*(?:[-*]\s*)?candidate_count\s*:\s*(\d+)\b/gim)].map((match) => Number(match[1]));
    if (candidateCounts.length !== 1 || candidateCounts[0] !== 0) fail(problems, `${brief.source} zero-result evidence ${ref} requires candidate_count uniquely equal to 0 within the referenced fragment`);
    for (const [label, pattern] of [
      ['scope', /\bscope\s*:/i], ['checked_at', /\bchecked_at\s*:/i], ['retrieval_dimensions', /\bretrieval_dimensions\s*:/i],
      ['snapshot', /\bsnapshot_(?:ref|url|path)\s*:/i], ['digest', /\bsnapshot_digest\s*:/i], ['observed no-match', /\bno matching|no-match|no match\b/i],
      ['empty conflict_candidates', /\bconflict_candidates\s*:\s*\[\s*\]/i],
    ]) if (!pattern.test(canonical)) fail(problems, `${brief.source} zero-result evidence ${ref} requires fragment-bound ${label}`);
    const scope = /(?:^|\n)\s*(?:[-*]\s*)?scope\s*:\s*['"]?([^'"\n]+)['"]?/im.exec(canonical)?.[1]?.trim() || '';
    const checkedAt = /(?:^|\n)\s*(?:[-*]\s*)?checked_at\s*:\s*['"]?([^'"\n]+)['"]?/im.exec(canonical)?.[1]?.trim() || '';
    const market = normalizeText(string(brief, 'target_market', problems));
    const language = normalizeText(string(brief, 'target_content_language', problems));
    const languagePattern = language === 'en' ? /\b(?:en|english)\b/i : new RegExp(`\\b${language.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
    if (!scope || !normalizeText(scope).includes(market) || !languagePattern.test(scope)) {
      fail(problems, `${brief.source} zero-result evidence ${ref} scope must bind target market and content language within the referenced fragment`);
    }
    if (evidenceScope === 'production') {
      requireFreshIsoDate(checkedAt, brief.source, `zero-result evidence ${ref} checked_at`, problems);
      requireDateNoLaterThan(checkedAt, reviewedAt, brief.source, `zero-result evidence ${ref} checked_at`, 'reviewed_at', problems);
    } else {
      requireIsoDate(checkedAt, brief.source, `zero-result evidence ${ref} checked_at`, problems);
    }
    const retrievalBlock = /(?:^|\n)\s*(?:[-*]\s*)?retrieval_dimensions\s*:\s*([^\n]*(?:\n(?:\s{2,}|\s*[-*]\s+)[^\n]+)*)/im.exec(canonical)?.[1] || '';
    for (const [label, pattern] of [
      ['URL/slug', /\b(?:url|slug)\b/i], ['title', /\btitle\b/i], ['query', /\bquery\b/i],
      ['buyer task', /\b(?:buyer task|dominant task|task)\b/i], ['stage', /\bstage\b/i],
      ['taxonomy', /\b(?:taxonomy|category|tag|label)\b/i],
    ]) if (!pattern.test(retrievalBlock)) fail(problems, `${brief.source} zero-result evidence ${ref} retrieval_dimensions requires ${label}`);
    if (/\b(?:found|observed|identified|detected|returned)\s+[1-9]\d*\b.{0,80}\b(?:overlap|conflict|duplicate|candidate|owner page)/i.test(normalized)
      || /\b(?:non-zero|overlapping owner pages?|duplicate owner|conflict candidates? (?:were|are|exist))\b/i.test(normalized)) {
      fail(problems, `${brief.source} zero-result evidence ${ref} contains a contradictory non-zero/overlap/conflict/duplicate-owner conclusion`);
    }
  }
}


function searchDemandScalar(section, field) {
  const escaped = field.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(`(?:^|\\n)\\s*(?:[-*]\\s*)?${escaped}\\s*:\\s*['\"]?([^'\"\\n]+)['\"]?`, 'im').exec(section)?.[1]?.trim() || '';
}

function parseEvidenceScalarFields(sectionMarkdown) {
  const fields = new Map();
  for (const line of String(sectionMarkdown || '').split('\n').slice(1)) {
    const match = /^\s*(?:[-*]\s*)?([A-Za-z][A-Za-z0-9 _-]{1,64})\s*:\s*(.+?)\s*$/.exec(line);
    if (!match) continue;
    const key = match[1].trim().toLowerCase().replace(/[ -]+/g, '_');
    if (fields.has(key)) fields.set(key, '');
    else fields.set(key, match[2].trim().replace(/^`|`$/g, ''));
  }
  return fields;
}

function validateBoundSnapshotArtifact({ axis, ref, expectedKind, evidenceRoot, registry, source, reviewedAt, expectedScope, problems }) {
  const { pathPart, fragment } = splitLocalRef(ref);
  if (!pathPart || !fragment) {
    fail(problems, `${source} production ${axis} evidence ref must include a local #fragment before snapshot binding can be checked: ${ref}`);
    return;
  }
  const evidencePath = resolve(evidenceRoot, pathPart);
  if (!existsSync(evidencePath) || !statSync(evidencePath).isFile()) return;
  let section = '';
  try {
    const parsed = parseArticleMarkdownFrontMatter(readFileSync(evidencePath, 'utf8'), { source: evidencePath });
    section = markdownSectionBody(parsed.body, fragment);
  } catch (error) {
    fail(problems, `${source} production ${axis} evidence ${ref} cannot be parsed for snapshot binding: ${error.message}`);
    return;
  }
  const fields = parseEvidenceScalarFields(section);
  const snapshotRef = fields.get('snapshot_ref') || '';
  const snapshotDigest = fields.get('snapshot_digest') || '';
  if (!snapshotRef) fail(problems, `${source} production ${axis} evidence ${ref} requires snapshot_ref`);
  if (!snapshotDigest) fail(problems, `${source} production ${axis} evidence ${ref} requires snapshot_digest`);
  if (!snapshotRef || !snapshotDigest) return;
  if (/^[a-z][a-z0-9+.-]*:\/\//i.test(snapshotRef) || isAbsolute(snapshotRef) || snapshotRef.includes('\\')
    || snapshotRef.includes('#') || snapshotRef.includes('?') || snapshotRef.includes('\0')
    || snapshotRef.split('/').includes('..')) {
    fail(problems, `${source} production ${axis} snapshot_ref must be a package-root-relative local file path without URL syntax, fragments, query strings, backslashes, or traversal: ${snapshotRef}`);
    return;
  }
  if (!/^sha256:[a-f0-9]{64}$/.test(snapshotDigest)) {
    fail(problems, `${source} production ${axis} snapshot_digest must use lowercase sha256:<64 hex>`);
    return;
  }
  const absolute = resolve(evidenceRoot, snapshotRef);
  const relativePath = relative(evidenceRoot, absolute);
  if (!relativePath || relativePath.startsWith(`..${sep}`) || relativePath === '..' || isAbsolute(relativePath)) {
    fail(problems, `${source} production ${axis} snapshot_ref escapes or aliases the package root: ${snapshotRef}`);
    return;
  }
  let cursor = evidenceRoot;
  for (const part of relativePath.split(sep)) {
    cursor = resolve(cursor, part);
    if (!existsSync(cursor)) break;
    try {
      if (lstatSync(cursor).isSymbolicLink()) {
        fail(problems, `${source} production ${axis} snapshot_ref must not traverse a symlink: ${snapshotRef}`);
        return;
      }
    } catch (error) {
      fail(problems, `${source} production ${axis} snapshot_ref cannot be inspected: ${error.message}`);
      return;
    }
  }
  if (!existsSync(absolute)) {
    fail(problems, `${source} production ${axis} snapshot_ref does not exist: ${snapshotRef}`);
    return;
  }
  let stats;
  try { stats = lstatSync(absolute); }
  catch (error) { fail(problems, `${source} production ${axis} snapshot_ref cannot be inspected: ${error.message}`); return; }
  if (stats.isSymbolicLink() || !stats.isFile()) {
    fail(problems, `${source} production ${axis} snapshot_ref must resolve to a regular non-symlink file: ${snapshotRef}`);
    return;
  }
  let realRoot;
  let realTarget;
  try {
    realRoot = realpathSync(evidenceRoot);
    realTarget = realpathSync(absolute);
  } catch (error) {
    fail(problems, `${source} production ${axis} snapshot_ref realpath cannot be resolved: ${error.message}`);
    return;
  }
  if (!isWithinRoot(realRoot, realTarget)) {
    fail(problems, `${source} production ${axis} snapshot_ref realpath escapes the package root: ${snapshotRef}`);
    return;
  }
  const bytes = readFileSync(realTarget);
  const actualDigest = `sha256:${createHash('sha256').update(bytes).digest('hex')}`;
  if (actualDigest !== snapshotDigest) {
    fail(problems, `${source} production ${axis} snapshot_digest does not match raw artifact bytes; expected ${actualDigest}`);
  }
  let artifact;
  try { artifact = JSON.parse(bytes.toString('utf8')); }
  catch (error) { fail(problems, `${source} production ${axis} snapshot artifact must be valid JSON: ${error.message}`); return; }
  if (!artifact || typeof artifact !== 'object' || Array.isArray(artifact)) {
    fail(problems, `${source} production ${axis} snapshot artifact must be a JSON object`);
    return;
  }
  if (artifact.schema_version !== 'website-content-ops.snapshot.v1') {
    fail(problems, `${source} production ${axis} snapshot artifact schema_version must be website-content-ops.snapshot.v1`);
  }
  if (artifact.artifact_kind !== expectedKind) {
    fail(problems, `${source} production ${axis} snapshot artifact_kind must be ${expectedKind}`);
  }
  if (artifact.evidence_scope !== 'production') {
    fail(problems, `${source} production ${axis} snapshot artifact evidence_scope must be production`);
  }
  const envelopeKeys = Object.keys(artifact).sort();
  const expectedEnvelopeKeys = [...SNAPSHOT_ENVELOPE_FIELDS].sort();
  if (envelopeKeys.length !== expectedEnvelopeKeys.length || expectedEnvelopeKeys.some((key, index) => key !== envelopeKeys[index])) {
    fail(problems, `${source} production ${axis} snapshot artifact must use the closed common envelope: ${expectedEnvelopeKeys.join(', ')}`);
  }
  for (const field of ['subject_id', 'scope_id', 'capture_method', 'producer_id', 'independent_reviewer_id']) {
    if (typeof artifact[field] !== 'string' || !artifact[field].trim()) fail(problems, `${source} production ${axis} snapshot artifact requires non-empty ${field}`);
  }
  requireStableActorId(artifact.producer_id, source, `${axis} snapshot producer_id`, problems);
  requireStableActorId(artifact.independent_reviewer_id, source, `${axis} snapshot independent_reviewer_id`, problems);
  if (normalizeText(artifact.producer_id) === normalizeText(artifact.independent_reviewer_id)) fail(problems, `${source} production ${axis} snapshot producer_id and independent_reviewer_id must be different`);
  for (const [evidenceField, artifactField] of [
    ['snapshot_subject_id', 'subject_id'], ['snapshot_scope_id', 'scope_id'], ['snapshot_capture_method', 'capture_method'],
    ['snapshot_producer_id', 'producer_id'], ['snapshot_independent_reviewer_id', 'independent_reviewer_id'],
  ]) {
    const value = fields.get(evidenceField) || '';
    if (!value) fail(problems, `${source} production ${axis} evidence ${ref} requires ${evidenceField}`);
    else if (normalizeText(value) !== normalizeText(artifact[artifactField])) fail(problems, `${source} production ${axis} evidence ${ref} ${evidenceField} must match snapshot ${artifactField}`);
  }
  validateSnapshotPayload({ artifact, expectedKind, fields, source, axis, ref, expectedScope, problems });
  if (typeof artifact.captured_at !== 'string' || !artifact.captured_at.trim()) {
    fail(problems, `${source} production ${axis} snapshot artifact requires captured_at`);
  } else {
    requireFreshIsoDate(artifact.captured_at, source, `${axis} snapshot captured_at`, problems);
    requireDateNoLaterThan(artifact.captured_at, reviewedAt, source, `${axis} snapshot captured_at`, 'reviewed_at', problems);
  }
  const identities = [
    ['path', snapshotRef],
    ['realpath', realTarget],
    ['inode', `${stats.dev}:${stats.ino}`],
    ['digest', actualDigest],
  ];
  for (const [identityKind, identity] of identities) {
    const prior = registry.get(`${identityKind}:${identity}`);
    if (prior && prior.axis !== axis) {
      fail(problems, `${source} production snapshot artifacts must be independent across axes; ${axis} reuses ${identityKind} from ${prior.axis}`);
    } else if (!prior) {
      registry.set(`${identityKind}:${identity}`, { axis, ref, snapshotRef });
    }
  }
}

function validateProductionSnapshotArtifacts(brief, review, evidenceScope, evidenceRoot, problems) {
  if (evidenceScope !== 'production') return;
  const reviewedAt = string(review, 'reviewed_at', problems);
  const registry = new Map();
  const serpRef = strings(brief, 'serp_format_evidence_refs', problems, { allowEmpty: true })[0] || '';
  const sharedDevice = serpRef ? searchDemandScalar(loadReferencedSection(serpRef, evidenceRoot), 'device') : '';
  for (const [axis, refsField, artifactKind] of [
    ['search-demand', 'search_demand_evidence_refs', 'search-demand'],
    ['serp-format', 'serp_format_evidence_refs', 'serp-format'],
    ['market-comparison', 'information_gain_market_refs', 'market-comparison'],
    ['content-inventory', 'inventory_zero_result_evidence_refs', 'content-inventory'],
  ]) {
    const refs = strings(brief, refsField, problems, { allowEmpty: true });
    if (!refs.length) {
      fail(problems, `${brief.source} production ${axis} requires at least one ${refsField} fragment with a bound snapshot artifact`);
      continue;
    }
    for (const ref of refs) validateBoundSnapshotArtifact({
      axis,
      ref,
      expectedKind: artifactKind,
      evidenceRoot,
      registry,
      source: brief.source,
      reviewedAt,
      expectedScope: {
        querySet: [string(brief, 'primary_query', problems), ...strings(brief, 'supporting_query_variants', problems)],
        market: string(brief, 'target_market', problems),
        language: string(brief, 'target_content_language', problems),
        device: sharedDevice,
      },
      problems,
    });
  }
}

function validateProductionSearchDemandEvidence(records, brief, review, evidenceScope, evidenceRoot, problems) {
  if (evidenceScope !== 'production') return;
  for (const field of ['search_demand_observation_start_at', 'search_demand_observation_end_at']) requireCanonicalMatch(records, field, problems, field, 'exact-raw-scalar');
  const canonicalObservationStart = string(brief, 'search_demand_observation_start_at', problems);
  const canonicalObservationEnd = string(brief, 'search_demand_observation_end_at', problems);
  for (const [field, value] of [['search_demand_observation_start_at', canonicalObservationStart], ['search_demand_observation_end_at', canonicalObservationEnd]]) {
    requireIsoDate(value, brief.source, field, problems);
    if (!/T\d{2}:\d{2}:\d{2}/.test(value)) fail(problems, `${brief.source} ${field} must be an explicit ISO timestamp; a date-only value is insufficient`);
  }
  requireDateNoLaterThan(canonicalObservationStart, canonicalObservationEnd, brief.source, 'search_demand_observation_start_at', 'search_demand_observation_end_at', problems);
  requireDateNoLaterThan(canonicalObservationEnd, string(review, 'reviewed_at', problems), brief.source, 'search_demand_observation_end_at', 'reviewed_at', problems);
  const status = normalizeText(string(brief, 'search_demand_evidence_status', problems));
  const refs = strings(brief, 'search_demand_evidence_refs', problems, { allowEmpty: true });
  if (status !== 'confirmed') fail(problems, `${brief.source} production requires search_demand_evidence_status=confirmed`);
  if (!refs.length) fail(problems, `${brief.source} production requires fragment-bound search_demand_evidence_refs`);
  const expectedQueries = [string(brief, 'primary_query', problems), ...strings(brief, 'supporting_query_variants', problems)];
  for (const ref of refs) {
    const section = loadReferencedSection(ref, evidenceRoot);
    if (!section) { fail(problems, `${brief.source} search-demand evidence ${ref} must resolve to a valid non-empty fragment`); continue; }
    const exactQueries = parseExactStringSet(searchDemandScalar(section, 'exact_query_set'), brief.source, `search-demand evidence ${ref} exact_query_set`, problems);
    if (!sameNormalizedSet(exactQueries, expectedQueries) || exactQueries.length !== expectedQueries.length) fail(problems, `${brief.source} search-demand evidence ${ref} wrong-query: exact_query_set must equal primary_query plus every supporting_query_variant`);

    const source = searchDemandScalar(section, 'source_or_platform');
    const market = searchDemandScalar(section, 'market');
    const language = searchDemandScalar(section, 'language');
    const device = searchDemandScalar(section, 'device');
    const window = searchDemandScalar(section, 'observation_window');
    const metricType = searchDemandScalar(section, 'metric_type');
    const brandBoundary = searchDemandScalar(section, 'brand_non_brand_boundary');
    const zeroDecision = searchDemandScalar(section, 'zero_or_low_demand_decision');
    const trend = searchDemandScalar(section, 'seasonality_or_trend_note');
    const conclusion = searchDemandScalar(section, 'analyst_conclusion');
    const reviewer = searchDemandScalar(section, 'independent_reviewer');
    const snapshot = searchDemandScalar(section, 'snapshot_ref');
    const digest = searchDemandScalar(section, 'snapshot_digest');
    for (const [field, value] of [
      ['source_or_platform', source], ['market', market], ['language', language], ['device', device], ['observation_window', window],
      ['metric_type', metricType], ['brand_non_brand_boundary', brandBoundary], ['zero_or_low_demand_decision', zeroDecision],
      ['seasonality_or_trend_note', trend], ['analyst_conclusion', conclusion], ['independent_reviewer', reviewer], ['snapshot_ref', snapshot], ['snapshot_digest', digest],
    ]) {
      const minimumLength = field === 'language' ? 2 : 3;
      if (normalizeText(value).length < minimumLength || PLACEHOLDER_PATTERN.test(normalizeText(value)) || /replace-with|placeholder|opinion only/i.test(value)) {
        fail(problems, `${brief.source} search-demand evidence ${ref} requires non-placeholder ${field}`);
      }
    }
    if (/\b(?:buyer opinion|sales opinion|analyst opinion|gut feeling|assumption only)\b/i.test(source)) fail(problems, `${brief.source} search-demand evidence ${ref} opinion-only source cannot confirm demand`);
    if (market !== string(brief, 'target_market', problems)) fail(problems, `${brief.source} search-demand evidence ${ref} wrong-market: market must exactly match target_market`);
    if (language !== string(brief, 'target_content_language', problems)) fail(problems, `${brief.source} search-demand evidence ${ref} language must exactly match target_content_language`);
    if (!/^(?:desktop|mobile|tablet|all-devices)$/i.test(device)) fail(problems, `${brief.source} search-demand evidence ${ref} device must be one exact declared device`);

    const dates = [...window.matchAll(/\b\d{4}-\d{2}-\d{2}\b/g)].map((match) => match[0]);
    if (dates.length !== 2) fail(problems, `${brief.source} search-demand evidence ${ref} observation_window must contain exact start and end ISO dates`);
    else {
      const [start, end] = dates.map((value) => Date.parse(`${value}T23:59:59Z`));
      if (!Number.isFinite(start) || !Number.isFinite(end) || start > end || end > Date.now()) fail(problems, `${brief.source} search-demand evidence ${ref} observation_window is invalid or future-dated`);
      else if (Date.now() - end > 395 * 24 * 60 * 60 * 1000) fail(problems, `${brief.source} search-demand evidence ${ref} stale-window: observation_window ended more than 395 days ago`);
    }
    const explicitWindowStart = searchDemandScalar(section, 'observation_window_start') || searchDemandScalar(section, 'observation_start_at');
    const explicitWindowEnd = searchDemandScalar(section, 'observation_window_end') || searchDemandScalar(section, 'observation_end_at');
    const observationStart = explicitWindowStart || canonicalObservationStart;
    const observationEnd = explicitWindowEnd || canonicalObservationEnd;
    if (observationStart !== canonicalObservationStart) fail(problems, `${brief.source} search-demand evidence ${ref} observation_window_start must exactly match search_demand_observation_start_at`);
    if (observationEnd !== canonicalObservationEnd) fail(problems, `${brief.source} search-demand evidence ${ref} observation_window_end must exactly match search_demand_observation_end_at`);
    if (observationEnd) {
      requireIsoDate(observationEnd, brief.source, `search-demand evidence ${ref} observation_window_end`, problems);
      requireDateNoLaterThan(observationEnd, string(review, 'reviewed_at', problems), brief.source, `search-demand evidence ${ref} observation_window_end`, 'reviewed_at', problems);
      const { pathPart } = splitLocalRef(ref);
      const evidenceTarget = resolve(evidenceRoot, pathPart);
      let observedAt = '';
      if (existsSync(evidenceTarget)) try {
        const parsedEvidence = parseArticleMarkdownFrontMatter(readFileSync(realpathSync(evidenceTarget), 'utf8'), { source: evidenceTarget });
        observedAt = parsedEvidence.attributes.observed_at || parsedEvidence.attributes.date || searchDemandScalar(section, 'observed_at');
      } catch (error) {
        fail(problems, `${brief.source} search-demand evidence ${ref} record timestamp could not be read: ${error.message}`);
      }
      if (!observedAt) fail(problems, `${brief.source} search-demand evidence ${ref} requires evidence-record observed_at`);
      else requireDateNoLaterThan(observationEnd, observedAt, brief.source, `search-demand evidence ${ref} observation_window_end`, 'evidence observed_at', problems);
      let snapshotCapturedAt = searchDemandScalar(section, 'snapshot_captured_at') || searchDemandScalar(section, 'captured_at');
      const snapshotTarget = resolve(evidenceRoot, splitLocalRef(snapshot).pathPart);
      if (existsSync(snapshotTarget)) try {
        const snapshotArtifact = JSON.parse(readFileSync(realpathSync(snapshotTarget), 'utf8'));
        if (typeof snapshotArtifact.captured_at === 'string' && snapshotArtifact.captured_at.trim()) snapshotCapturedAt = snapshotArtifact.captured_at.trim();
      } catch (error) {
        fail(problems, `${brief.source} search-demand evidence ${ref} snapshot captured_at could not be read: ${error.message}`);
      }
      if (!snapshotCapturedAt) fail(problems, `${brief.source} search-demand evidence ${ref} requires snapshot captured_at`);
      else requireDateNoLaterThan(observationEnd, snapshotCapturedAt, brief.source, `search-demand evidence ${ref} observation_window_end`, 'snapshot captured_at', problems);
    }
    if (!/\b(?:impressions?|clicks?|search volume|queries|sessions?|rank-tracked demand|keyword volume)\b/i.test(metricType)) fail(problems, `${brief.source} search-demand evidence ${ref} no-metric: metric_type must name an objective observed metric`);

    const observedBlock = /(?:^|\n)\s*observed_value_per_query\s*:\s*\n((?:\s*-\s*[^\n]+\n?)+)/im.exec(section)?.[1] || '';
    const rows = [...observedBlock.matchAll(/^\s*-\s*['\"]?(.+?)['\"]?\s*$/gm)].map((match) => match[1].trim());
    const seenQueries = [];
    const values = [];
    for (const row of rows) {
      const parts = row.split('|').map((part) => part.trim());
      if (parts.length !== 3 || !parts.every(Boolean) || !/^-?\d+(?:\.\d+)?$/.test(parts[1]) || Number(parts[1]) < 0) {
        fail(problems, `${brief.source} search-demand evidence ${ref} observed_value_per_query row must use query|non-negative-numeric-value|unit: ${row}`);
        continue;
      }
      seenQueries.push(parts[0]); values.push(Number(parts[1]));
      if (normalizeText(parts[2]).length < 2) fail(problems, `${brief.source} search-demand evidence ${ref} observed_value_per_query row requires a unit`);
    }
    if (!rows.length) fail(problems, `${brief.source} search-demand evidence ${ref} no-metric: observed_value_per_query is empty`);
    if (!sameNormalizedSet(seenQueries, expectedQueries) || seenQueries.length !== expectedQueries.length) fail(problems, `${brief.source} search-demand evidence ${ref} observed_value_per_query must cover every exact query once`);
    if (values.length && values.every((value) => value === 0) && !/\b(?:do not target|stop|merge|reframe|hold|no-target)\b/i.test(zeroDecision)) fail(problems, `${brief.source} search-demand evidence ${ref} zero-demand falsely confirmed without a stop, merge, reframe, or do-not-target decision`);
    if (!/\b(?:brand|branded)\b/i.test(brandBoundary) || !/\b(?:non-brand|nonbranded|unbranded)\b/i.test(brandBoundary)) fail(problems, `${brief.source} search-demand evidence ${ref} brand_non_brand_boundary must define both brand and non-brand treatment`);
    if (!/\b(?:season|trend|none observed|stable|rising|falling|flat)\b/i.test(trend)) fail(problems, `${brief.source} search-demand evidence ${ref} seasonality omitted or not explicitly assessed`);
    if (semanticOverlap(conclusion, `${metricType} ${expectedQueries.join(' ')}`).length < 2 && !/\b(?:observed|recorded|measured|value|impression|click|volume)\b/i.test(conclusion)) fail(problems, `${brief.source} search-demand evidence ${ref} analyst_conclusion is opinion-only and not derived from observed values`);
    if (/\b(?:ai|assistant|bot|same author|self-review)\b/i.test(reviewer)) fail(problems, `${brief.source} search-demand evidence ${ref} requires a distinct independent_reviewer`);
    if (!/^sha256:[a-f0-9]{64}$/i.test(digest)) fail(problems, `${brief.source} search-demand evidence ${ref} digest must be sha256:<64-hex>`);
  }
}

function validateV10ProductionAxes(records, brief, review, evidenceScope, evidenceRoot, problems) {
  if (evidenceScope !== 'production') return;
  const reviewedAt = string(review, 'reviewed_at', problems);
  if (string(brief, 'query_evidence_status', problems) !== 'confirmed') fail(problems, `${brief.source} production requires query_evidence_status=confirmed`);
  const queryRefs = strings(brief, 'query_evidence_refs', problems, { allowEmpty: true });
  if (!queryRefs.length) fail(problems, `${brief.source} production requires non-empty query_evidence_refs independent from buyer-task evidence`);
  if (queryRefs.some((ref) => strings(brief, 'buyer_task_evidence_refs', problems, { allowEmpty: true }).map(normalizeText).includes(normalizeText(ref)))) fail(problems, `${brief.source} buyer-task evidence cannot substitute for independent query evidence`);
  for (const ref of queryRefs) {
    const section = loadReferencedSection(ref, evidenceRoot);
    if (!section) { fail(problems, `${brief.source} query evidence ${ref} must resolve to a valid non-empty fragment`); continue; }
    const normalized = normalizeText(section);
    for (const term of [string(brief, 'primary_query', problems), string(brief, 'target_market', problems), string(brief, 'target_content_language', problems), string(brief, 'stage', problems), string(brief, 'commercial_commitment', problems)]) {
      if (!normalized.includes(normalizeText(term))) fail(problems, `${brief.source} query evidence ${ref} must bind query/task/stage/commitment/market/language`);
    }
    const observed = /\b(?:checked_at|observed_at)\s*:\s*['\"]?([^'\"\n]+)['\"]?/i.exec(section)?.[1]?.trim() || '';
    if (!/\b(?:device|desktop|mobile)\b/i.test(normalized) || !observed) fail(problems, `${brief.source} query evidence ${ref} requires device and a datetime observation`);
    requireFreshIsoDate(observed, brief.source, `query evidence ${ref} observed_at`, problems);
    requireDateNoLaterThan(observed, reviewedAt, brief.source, `query evidence ${ref} observed_at`, 'reviewed_at', problems);
  }
  const artifactRefs = strings(brief, 'information_gain_artifact_refs', problems, { allowEmpty: true });
  const marketRefs = strings(brief, 'information_gain_market_refs', problems, { allowEmpty: true });
  if (!artifactRefs.length || !marketRefs.length) fail(problems, `${brief.source} production information gain requires non-empty artifact and market refs`);
  if (artifactRefs.some((ref) => marketRefs.map(normalizeText).includes(normalizeText(ref)))) fail(problems, `${brief.source} production artifact and market information-gain refs must use different fragments`);
  for (const ref of artifactRefs) {
    const rawSection = loadReferencedSection(ref, evidenceRoot);
    if (!rawSection) {
      fail(problems, `${brief.source} artifact information-gain ref ${ref} must resolve to a valid non-empty fragment`);
      continue;
    }
    const section = normalizeText(rawSection);
    if (!/\b(?:decision artifact|checklist|matrix|calculator|worksheet|candidate-or-stop|decision table)\b/i.test(section)) fail(problems, `${brief.source} artifact information-gain ref ${ref} must prove a decision artifact`);
  }
  for (const ref of marketRefs) {
    const section = loadReferencedSection(ref, evidenceRoot);
    if (!section) {
      fail(problems, `${brief.source} market information-gain ref ${ref} must resolve to a valid non-empty fragment`);
      continue;
    }
    const normalized = normalizeText(section);
    for (const [label, pattern] of [
      ['date', /\b(?:checked_at|observed_at|reviewed_at)\s*:/i], ['market', /\bmarket\s*:/i], ['language', /\blanguage\s*:/i],
      ['query set', /\bquery(?:_set| set)\s*:/i], ['snapshot/corpus', /\b(?:snapshot|corpus)\b/i], ['difference', /\b(?:difference|compared|comparison)\b/i], ['reviewer', /\breviewer\s*:/i],
    ]) if (!pattern.test(section)) fail(problems, `${brief.source} market information-gain ref ${ref} requires ${label}`);
    const observed = /\b(?:checked_at|observed_at|reviewed_at)\s*:\s*['"]?([^'"\n]+)['"]?/i.exec(section)?.[1]?.trim() || '';
    requireFreshIsoDate(observed, brief.source, `market information-gain ref ${ref} date`, problems);
    requireDateNoLaterThan(observed, reviewedAt, brief.source, `market information-gain ref ${ref} date`, 'reviewed_at', problems);
    const marketValue = /(?:^|\n)\s*(?:[-*]\s*)?market\s*:\s*['"]?([^'"\n]+)['"]?/im.exec(section)?.[1]?.trim() || '';
    const languageValue = /(?:^|\n)\s*(?:[-*]\s*)?language\s*:\s*['"]?([^'"\n]+)['"]?/im.exec(section)?.[1]?.trim() || '';
    const querySetValue = /(?:^|\n)\s*(?:[-*]\s*)?query(?:_set| set)\s*:\s*['"]?([^'"\n]+)['"]?/im.exec(section)?.[1]?.trim() || '';
    const snapshotValue = /(?:^|\n)\s*(?:[-*]\s*)?(?:snapshot|corpus)(?:_ref|_url|_path)?\s*:\s*['"]?([^'"\n]+)['"]?/im.exec(section)?.[1]?.trim() || '';
    const differenceValue = /(?:^|\n)\s*(?:[-*]\s*)?(?:difference|comparison)\s*:\s*['"]?([^'"\n]+)['"]?/im.exec(section)?.[1]?.trim() || '';
    const reviewerValue = /(?:^|\n)\s*(?:[-*]\s*)?(?:independent_)?reviewer\s*:\s*['"]?([^'"\n]+)['"]?/im.exec(section)?.[1]?.trim() || '';
    for (const [label, value] of [
      ['market', marketValue], ['language', languageValue], ['query set', querySetValue],
      ['snapshot/corpus', snapshotValue], ['difference', differenceValue], ['reviewer', reviewerValue],
    ]) {
      if (normalizeText(value).length < 2 || /^(?:not-applicable|none|unknown|tbd|todo|placeholder)$/i.test(normalizeText(value))) {
        fail(problems, `${brief.source} market information-gain ref ${ref} requires a non-empty non-placeholder ${label}`);
      }
    }
    if (marketValue && !normalizeText(marketValue).includes(normalizeText(string(brief, 'target_market', problems)))) {
      fail(problems, `${brief.source} market information-gain ref ${ref} market must bind target_market`);
    }
    if (languageValue) {
      const targetLanguage = normalizeText(string(brief, 'target_content_language', problems));
      const languageMatches = targetLanguage === 'en' ? /\b(?:en|english)\b/i.test(languageValue) : normalizeText(languageValue).includes(targetLanguage);
      if (!languageMatches) fail(problems, `${brief.source} market information-gain ref ${ref} language must bind target_content_language`);
    }
    if (querySetValue && semanticOverlap(querySetValue, string(brief, 'primary_query', problems)).length < 2) {
      fail(problems, `${brief.source} market information-gain ref ${ref} query set must bind the primary query family`);
    }
    if (!normalized) fail(problems, `${brief.source} market information-gain ref ${ref} must resolve to a non-empty fragment`);
  }
}

const V11_OUTCOME_STATUSES = new Set(['unverified', 'not-applicable', 'observed-no-improvement', 'observed-improvement']);
const V11_SALES_OUTCOME_STATUSES = new Set(['unverified', 'not-applicable', 'not-accepted', 'sales-accepted']);
const V11_TECHNICAL_GATES = ['first-round-complete', 'second-round-complete', 'no-evidenced-no-fit', 'named-technical-owner-accepted'];
const V11_SALES_GATES = ['explicit-commercial-intent', 'commercial-qualification-required', 'commercial-inputs-complete', 'named-commercial-owner-reviewed-and-accepted'];
const V11_NEGATIVE_EVIDENCE_PATTERN = /(?:\b(?:false|failed|missing|absent|unavailable|omitted|unmet|unsatisfied|unsubstantiated|unverified|self[ _-]?(?:declared|asserted|certified))\b|\b(?:not|never)\s+(?:(?:yet|been|independently)\s+){0,3}(?:provided|received|present|available|complete|completed|accepted|approved|reviewed|evidenced|satisfied|met|submitted|substantiated|verified|confirmed)\b|\bwithout\s+(?:independent\s+)?(?:evidence|substantiation|verification|confirmation|review|acceptance)\b|(?:=|:)\s*(?:false|no|missing|absent|failed)\b)/i;
const V11_QUERY_HEADER = ['query', 'action', 'object', 'observable-output', 'stage', 'commercial-commitment', 'market', 'language', 'device', 'checked_at', 'evidence_ref'];

function isStableOwnerIdentity(value) {
  const raw = String(value ?? '').trim();
  const normalized = normalizeText(raw);
  if (!raw || /^(?:not-applicable|none|unknown|tbd|todo|ai|assistant|bot|team|department|staff|quality|engineering|sales|commercial|procurement|marketing|management)$/i.test(normalized)) return false;
  if (/^(?:owner|person|user|employee|staff|technical|commercial|sales)[-_:][a-z0-9][a-z0-9._:-]{2,}$/i.test(raw) || /^[A-Z]{2,12}-\d{2,}$/.test(raw)) return true;
  const parts = raw.split(',').map((part) => part.trim());
  if (parts.length < 2) return false;
  const person = parts.shift();
  const role = parts.join(', ');
  const nameTokens = person.match(/\p{L}[\p{L}'’.-]+/gu) || [];
  return nameTokens.length >= 2
    && /\p{L}{3,}/u.test(role)
    && !/^(?:team|department|staff|quality|engineering|sales|commercial|procurement|marketing|management|ai|tbd)(?:\s+team|\s+department)?(?:\s*\(synthetic\))?$/i.test(normalizeText(role));
}

function requireStableOwnerIdentity(value, source, field, problems) {
  if (!isStableOwnerIdentity(value)) fail(problems, `${source} field ${field} must be a stable owner ID or person name plus role; pure role/team/department/AI/TBD is not allowed: ${value}`);
}

function isConcreteFallbackEndpoint(value) {
  const raw = String(value ?? '').trim();
  if (/^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i.test(raw)) return true;
  if (/^mailto:[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i.test(raw)) return true;
  try {
    const url = new URL(raw);
    return url.protocol === 'https:' && Boolean(url.hostname);
  } catch { return false; }
}

function parseFallbackLocalRefs(value, source, field, problems, { allowNotApplicable = false } = {}) {
  const raw = String(value ?? '').trim();
  if (raw === 'not-applicable') return allowNotApplicable ? [] : (fail(problems, `${source} ${field} is missing; one or more comma-separated local evidence refs are required`), []);
  const refs = raw.split(',').map((ref) => ref.trim()).filter(Boolean);
  if (!refs.length || refs.join(',') !== raw.replace(/\s*,\s*/g, ',')) {
    fail(problems, `${source} ${field} must be a non-empty comma-separated list of local refs or exact not-applicable`);
  }
  if (new Set(refs.map(normalizeText)).size !== refs.length) fail(problems, `${source} ${field} must not contain duplicate refs`);
  return refs;
}

function validateCtaFallbackRouteContract(records, brief, evidenceRoot, evidenceScope, problems) {
  const field = 'cta_fallback_route_contract';
  for (const record of records) {
    if (!(field in record.attributes)) fail(problems, `${record.source} closed fallback-route schema requires ${field}`);
    else if (typeof record.attributes[field] !== 'string') fail(problems, `${record.source} ${field} must be one exact scalar pipe row`);
  }
  requireCanonicalMatch(records, field, problems, field, 'exact-scalar');
  if (!(field in brief.attributes) || typeof brief.attributes[field] !== 'string') return null;
  const value = string(brief, field, problems);
  const parts = value.split('|').map((part) => part.trim());
  if (parts.length !== 17 || parts.some((part) => !part)) {
    fail(problems, `${brief.source} ${field} must contain exactly 17 non-empty pipe-delimited slots: route-status|endpoint|owner|required-inputs-mode|commitment-boundary|reference-execution|reference-result|reference-verdict|reference-refs|reachability-execution|reachability-result|reachability-verdict|reachability-refs|capability-execution|capability-result|capability-verdict|capability-refs`);
    return null;
  }
  const [status, endpoint, owner, requiredInputsMode, commitmentBoundary,
    referenceExecution, referenceResult, referenceVerdict, referenceRefsRaw,
    reachabilityExecution, reachabilityResult, reachabilityVerdict, reachabilityRefsRaw,
    capabilityExecution, capabilityResult, capabilityVerdict, capabilityRefsRaw] = parts;
  if (!CTA_FALLBACK_ROUTE_STATUSES.has(status)) fail(problems, `${brief.source} ${field} route-status must be verified|unverified-unavailable|not-applicable`);
  if (status === 'not-applicable') {
    if (parts.some((part) => part !== 'not-applicable')) fail(problems, `${brief.source} ${field} route-status=not-applicable requires all 17 slots to be exact not-applicable`);
    return { status, endpoint, owner, requiredInputsMode, commitmentBoundary, axes: [] };
  }
  requireStableOwnerIdentity(owner, brief.source, `${field} owner`, problems);
  if (!CTA_FALLBACK_REQUIRED_INPUT_MODES.has(requiredInputsMode)) fail(problems, `${brief.source} ${field} required-inputs-mode must be same-as-cta-required-inputs|none`);
  meaningfulScalar(commitmentBoundary, brief.source, `${field} commitment-boundary`, problems, { minLength: 18 });
  const axes = [
    { name: 'reference', execution: referenceExecution, result: referenceResult, verdict: referenceVerdict, refsRaw: referenceRefsRaw },
    { name: 'reachability', execution: reachabilityExecution, result: reachabilityResult, verdict: reachabilityVerdict, refsRaw: reachabilityRefsRaw },
    { name: 'capability', execution: capabilityExecution, result: capabilityResult, verdict: capabilityVerdict, refsRaw: capabilityRefsRaw },
  ];
  for (const axis of axes) {
    if (!CANONICAL_EVIDENCE_EXECUTIONS.has(axis.execution)) fail(problems, `${brief.source} ${field} ${axis.name}-execution must use the closed execution enum`);
    if (!CANONICAL_EVIDENCE_RESULTS.has(axis.result)) fail(problems, `${brief.source} ${field} ${axis.name}-result must use the closed result enum`);
    if (!CANONICAL_GATE_VERDICTS.has(axis.verdict)) fail(problems, `${brief.source} ${field} ${axis.name}-verdict must use the closed verdict enum`);
  }
  if (status === 'unverified-unavailable') {
    if (endpoint !== 'not-applicable') fail(problems, `${brief.source} ${field} unverified-unavailable requires endpoint=not-applicable`);
    for (const axis of axes) {
      if (axis.execution !== 'not-run' || axis.result !== 'missing' || axis.verdict !== 'block' || axis.refsRaw !== 'not-applicable') {
        fail(problems, `${brief.source} ${field} unverified-unavailable ${axis.name} axis must be not-run|missing|block|not-applicable`);
      }
    }
    return { status, endpoint, owner, requiredInputsMode, commitmentBoundary, axes };
  }
  if (status !== 'verified') return { status, endpoint, owner, requiredInputsMode, commitmentBoundary, axes };
  if (!isConcreteFallbackEndpoint(endpoint)) fail(problems, `${brief.source} ${field} verified endpoint must be one concrete HTTPS URL, email address, or mailto endpoint`);
  const primaryRefs = new Set();
  for (const record of records) for (const primaryField of ['cta_reference_evidence_refs', 'cta_reachability_evidence_refs', 'cta_capability_evidence_refs']) {
    if (!(primaryField in record.attributes) || !Array.isArray(record.attributes[primaryField])) continue;
    for (const ref of record.attributes[primaryField]) primaryRefs.add(normalizeText(ref));
  }
  for (const axis of axes) {
    if (axis.execution !== 'executed' || axis.result !== 'confirmed' || axis.verdict !== 'pass') {
      fail(problems, `${brief.source} ${field} verified ${axis.name} axis must be executed|confirmed|pass`);
    }
    const refs = parseFallbackLocalRefs(axis.refsRaw, brief.source, `${field} ${axis.name}-refs`, problems);
    validateLocalEvidenceRefs(refs, brief.source, `${field} ${axis.name}-refs`, evidenceRoot, problems, {
      requireFragment: true, regularNonSymlink: true, verifyFragment: true,
    });
    validateProductionEvidenceRefs(refs, brief.source, `${field} ${axis.name}-refs`, evidenceRoot, problems, {
      expectedKinds: ['fallback-route'],
      expectedCheckId: `fallback-${axis.name}`,
      expectedTargets: [{
        url: endpoint,
        role: 'fallback-route',
        task: `verify fallback ${axis.name} for bounded technical review`,
      }],
      expectedOwner: owner,
      requiredExtraFields: ['acceptance_criteria', 'capability_acceptance'],
      requireStructuredSection: true,
    });
    for (const ref of refs) {
      if (primaryRefs.has(normalizeText(ref))) fail(problems, `${brief.source} ${field} verified ${axis.name} evidence ref must be independent from primary CTA evidence: ${ref}`);
      const section = loadReferencedSection(ref, evidenceRoot);
      if (!section || !normalizeText(section).includes(normalizeText(endpoint))) {
        fail(problems, `${brief.source} ${field} verified ${axis.name} evidence fragment ${ref} must contain the exact fallback endpoint ${endpoint}`);
      }
    }
    axis.refs = refs;
  }
  return { status, endpoint, owner, requiredInputsMode, commitmentBoundary, axes };
}

function evidenceIsAffirmative(value) {
  const normalized = normalizeText(value);
  return !V11_NEGATIVE_EVIDENCE_PATTERN.test(normalized)
    && !/\b(?:but|although|however|despite)\b.{0,100}\b(?:complete|completed|accepted|approved|evidenced|satisfied|met|confirmed)\b/i.test(normalized)
    && /\b(?:all|every|complete|completed|present|provided|received|available|accepts?|accepted|approves?|approved|reviews?|reviewed|evidences?|evidenced|substantiated|verified|satisfied|met|confirms?|confirmed)\b/i.test(normalized);
}

function exactAffirmativeGateDefinition(value, gates) {
  const normalized = normalizeText(value);
  const gateList = `${gates.slice(0, -1).join(', ')}, and ${gates.at(-1)}`;
  return normalized === `${gateList} are all evidenced`
    || normalized === `${gateList} are all independently substantiated`
    || normalized === `${gateList} are all independently verified`
    || normalized === `${gateList} are all independently confirmed`;
}

function validateV11Qualification(brief, draft, publish, problems) {
  if (normalizeText(string(brief, 'stage_intake_contract', problems)) !== 'validate-technical') return;
  const technicalOwner = string(brief, 'technical_qualification_owner', problems);
  const salesOwner = string(brief, 'sales_acceptance_owner', problems);
  requireStableOwnerIdentity(technicalOwner, brief.source, 'technical_qualification_owner', problems);
  requireStableOwnerIdentity(salesOwner, brief.source, 'sales_acceptance_owner', problems);
  const rows = strings(brief, 'qualification_reason_codes', problems);
  for (const raw of rows) {
    const parts = raw.split('|').map((part) => part.trim());
    if (parts.length !== 5) continue;
    const [rawState, , evidenceRule, owner] = parts;
    const state = normalizeText(rawState);
    const expectedOwner = ['commercial-qualification-required', 'sales-accepted'].includes(state) ? salesOwner : technicalOwner;
    if (owner !== expectedOwner) fail(problems, `${brief.source} qualification_reason_codes ${state} owner must exactly equal canonical ${expectedOwner === salesOwner ? 'sales_acceptance_owner' : 'technical_qualification_owner'}`);
    if (['first-round-complete', 'engineering-review-ready', 'technical-qualified', 'sales-accepted'].includes(state) && !evidenceIsAffirmative(evidenceRule)) {
      fail(problems, `${brief.source} ${state} evidence-rule must affirm that required evidence is present and satisfied; negative or missing states fail closed`);
    }
    if (state === 'first-round-complete') {
      if (!/\b(?:all|every)\b.{0,40}\b(?:first[- ]round|five canonical first[- ]round)\b.{0,80}\b(?:present|provided|received|available|complete|completed)\b/i.test(evidenceRule)
        || V11_NEGATIVE_EVIDENCE_PATTERN.test(evidenceRule)) {
        fail(problems, `${brief.source} first-round-complete evidence must affirm all canonical first-round inputs are present`);
      }
    }
    if (state === 'technical-qualified') {
      requireExactGateClaims(evidenceRule, V11_TECHNICAL_GATES, brief.source, state, problems);
      if (!evidenceIsAffirmative(evidenceRule) || !exactAffirmativeGateDefinition(evidenceRule, V11_TECHNICAL_GATES)) fail(problems, `${brief.source} technical-qualified evidence-rule must use the exact affirmative canonical gate definition and cannot rely on self-declared, negated, failed, missing, absent, or unsubstantiated evidence`);
    }
    if (state === 'sales-accepted') {
      requireExactGateClaims(evidenceRule, V11_SALES_GATES, brief.source, state, problems);
      if (!evidenceIsAffirmative(evidenceRule) || !exactAffirmativeGateDefinition(evidenceRule, V11_SALES_GATES)) fail(problems, `${brief.source} sales-accepted evidence-rule must use the exact affirmative canonical gate definition and cannot rely on self-declared, negated, failed, missing, absent, or unsubstantiated evidence`);
    }
  }
  for (const [field, expected] of [['technical_qualification_gates', V11_TECHNICAL_GATES], ['sales_acceptance_gates', V11_SALES_GATES]]) {
    for (const gate of strings(brief, field, problems)) if (V11_NEGATIVE_EVIDENCE_PATTERN.test(gate)) fail(problems, `${brief.source} ${field} gate ${gate} is not affirmative`);
    requireExactSet(strings(brief, field, problems), expected, brief.source, field, problems);
  }
  const exactDefinitions = [
    ['technical_qualification_definition', `technical-qualified requires ${V11_TECHNICAL_GATES.slice(0, -1).join(', ')}, and ${V11_TECHNICAL_GATES.at(-1)}`],
    ['sales_acceptance_definition', `sales-accepted requires ${V11_SALES_GATES.slice(0, -1).join(', ')}, and ${V11_SALES_GATES.at(-1)}`],
  ];
  for (const [field, expected] of exactDefinitions) {
    const actual = normalizeText(string(brief, field, problems));
    if (actual !== expected) fail(problems, `${brief.source} ${field} must use the exact canonical gate definition: ${expected}`);
  }
}

function parseObservationWindow(value, source, problems) {
  const matches = String(value ?? '').match(/\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?Z)?/g) || [];
  if (matches.length < 2) {
    fail(problems, `${source} actual_outcome_observation_window must contain a dated start and end`);
    return;
  }
  for (const valuePart of matches.slice(0, 2)) requireIsoDate(valuePart, source, 'actual_outcome_observation_window', problems);
  if (Date.parse(matches[0]) > Date.parse(matches[1])) fail(problems, `${source} actual_outcome_observation_window start must not be after end`);
}

function validateV11ActualOutcomes(review, publish, evidenceRoot, problems) {
  const parityFields = [
    'actual_ranking_status', 'actual_inquiry_status', 'actual_conversion_status', 'actual_sales_acceptance_status',
    'actual_outcome_observation_window', 'actual_outcome_metric_or_event_definition', 'actual_outcome_observed_result',
    'actual_outcome_evidence_refs', 'actual_outcome_accountable_reviewer', 'actual_sales_acceptance_evidence_refs',
  ];
  for (const field of parityFields) requireCanonicalMatch([review, publish], field, problems);
  for (const field of ['actual_ranking_status', 'actual_inquiry_status', 'actual_conversion_status']) {
    const status = string(review, field, problems);
    if (!V11_OUTCOME_STATUSES.has(status)) fail(problems, `${review.source} ${field} must be exact lowercase unverified|not-applicable|observed-no-improvement|observed-improvement`);
  }
  const salesStatus = string(review, 'actual_sales_acceptance_status', problems);
  if (!V11_SALES_OUTCOME_STATUSES.has(salesStatus)) fail(problems, `${review.source} actual_sales_acceptance_status must be exact lowercase unverified|not-applicable|not-accepted|sales-accepted`);
  const statuses = ['actual_ranking_status', 'actual_inquiry_status', 'actual_conversion_status', 'actual_sales_acceptance_status'].map((field) => string(review, field, problems));
  const active = statuses.some((status) => ['observed-no-improvement', 'observed-improvement', 'not-accepted', 'sales-accepted'].includes(status));
  const window = string(review, 'actual_outcome_observation_window', problems);
  const definition = string(review, 'actual_outcome_metric_or_event_definition', problems);
  const result = string(review, 'actual_outcome_observed_result', problems);
  const reviewer = string(review, 'actual_outcome_accountable_reviewer', problems);
  const refs = strings(review, 'actual_outcome_evidence_refs', problems, { allowEmpty: true });
  const salesRefs = strings(review, 'actual_sales_acceptance_evidence_refs', problems, { allowEmpty: true });
  if (!active) {
    for (const [field, value] of [['actual_outcome_observation_window', window], ['actual_outcome_metric_or_event_definition', definition], ['actual_outcome_observed_result', result], ['actual_outcome_accountable_reviewer', reviewer]]) {
      if (value !== 'not-applicable') fail(problems, `${review.source} fail-closed outcome defaults require ${field}=not-applicable`);
    }
    if (refs.length || salesRefs.length) fail(problems, `${review.source} fail-closed outcome defaults require empty evidence refs`);
    return;
  }
  parseObservationWindow(window, review.source, problems);
  for (const [field, value] of [['actual_outcome_metric_or_event_definition', definition], ['actual_outcome_observed_result', result]]) {
    if (normalizeText(value).length < 12 || /^(?:not-applicable|unknown|tbd|todo|placeholder|unverified)$/i.test(normalizeText(value))) fail(problems, `${review.source} ${field} must be concrete for an observed outcome`);
  }
  if (!/\b(?:observed|measured|recorded|received|accepted|rejected|no|zero|\d)\b/i.test(result)) fail(problems, `${review.source} actual_outcome_observed_result must state a factual observed result`);
  if (!refs.length) fail(problems, `${review.source} observed outcome requires non-empty actual_outcome_evidence_refs`);
  else validateLocalEvidenceRefs(refs, review.source, 'actual_outcome_evidence_refs', evidenceRoot, problems, { requireFragment: true });
  requireStableOwnerIdentity(reviewer, review.source, 'actual_outcome_accountable_reviewer', problems);
  if (salesStatus === 'sales-accepted') {
    if (!salesRefs.length) fail(problems, `${review.source} sales-accepted requires non-empty actual_sales_acceptance_evidence_refs`);
    else validateLocalEvidenceRefs(salesRefs, review.source, 'actual_sales_acceptance_evidence_refs', evidenceRoot, problems, { requireFragment: true });
    const salesOwner = string(publish, 'sales_acceptance_owner', problems);
    requireStableOwnerIdentity(salesOwner, publish.source, 'sales_acceptance_owner', problems);
    if (string(publish, 'sales_commercial_inputs_status', problems) !== 'complete') fail(problems, `${publish.source} sales-accepted requires sales_commercial_inputs_status=complete`);
    if (!strings(publish, 'sales_acceptance_gates', problems).every((gate) => V11_SALES_GATES.includes(gate)) || !sameNormalizedSet(strings(publish, 'sales_acceptance_gates', problems), V11_SALES_GATES)) fail(problems, `${publish.source} sales-accepted requires all exact commercial gates`);
    const salesRow = strings(publish, 'qualification_reason_codes', problems).find((row) => row.startsWith('sales-accepted|')) || '';
    const parts = salesRow.split('|').map((part) => part.trim());
    if (parts.length !== 5 || parts[3] !== salesOwner || !evidenceIsAffirmative(parts[2])) fail(problems, `${publish.source} sales-accepted must bind affirmative exact commercial gates to the named commercial owner`);
  } else if (salesRefs.length) {
    fail(problems, `${review.source} actual_sales_acceptance_evidence_refs are allowed only for sales-accepted`);
  }
}

function englishNumberPattern() {
  const units = 'one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen';
  const tens = '(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?';
  return `(?:${units}|${tens})`;
}

function validateV11ZeroResultWords(brief, evidenceRoot, problems) {
  const numberWord = englishNumberPattern();
  const contradiction = new RegExp(`\\b(?:found|observed|identified|detected|returned|overlap(?:ped)? across|conflict(?:ed)? across|duplicate(?:d)? across)\\s+(?:${numberWord})\\b.{0,100}\\b(?:overlap|overlapping|conflict|duplicate|candidate|owner pages?)\\b|\\b(?:overlap|conflict|duplicate)\\w*\\s+across\\s+(?:${numberWord})\\s+owner pages?\\b`, 'i');
  for (const ref of strings(brief, 'inventory_zero_result_evidence_refs', problems, { allowEmpty: true })) {
    const section = loadReferencedSection(ref, evidenceRoot);
    if (section && contradiction.test(normalizeText(section))) fail(problems, `${brief.source} zero-result evidence ${ref} contains a contradictory non-zero English-number overlap/conflict/duplicate-owner conclusion`);
  }
}

function parseV11QueryRows(section) {
  const lines = section.split('\n').map((line) => line.trim()).filter(Boolean);
  const rows = [];
  const errors = [];
  let headerCount = 0;
  for (const line of lines) {
    if (!line.includes('|')) continue;
    const cells = line.replace(/^\||\|$/g, '').split('|').map((cell) => cell.trim());
    if (cells.every((cell) => /^:?-{3,}:?$/.test(cell))) continue;
    if (cells.length === 11 && cells.every((cell, index) => cell === V11_QUERY_HEADER[index])) {
      headerCount += 1;
      if (headerCount > 1) errors.push('duplicate exact canonical header');
      continue;
    }
    const headerLike = cells.some((cell) => ['query', 'action', 'object', 'observable-output', 'stage', 'commercial-commitment', 'market', 'language', 'device', 'checked_at', 'evidence_ref'].includes(normalizeText(cell).replace(/[ _]+/g, '-')));
    if (!headerCount) {
      errors.push(headerLike
        ? `non-canonical or aliased header: ${line}`
        : `data row appears before the exact canonical header: ${line}`);
      continue;
    }
    if (cells.length !== 11) {
      errors.push(`data row must contain exactly 11 slots, observed ${cells.length}: ${line}`);
      continue;
    }
    if (cells.some((cell) => !cell)) {
      errors.push(`data row contains an empty slot: ${line}`);
      continue;
    }
    if (headerLike) {
      errors.push(`duplicate or aliased header row: ${line}`);
      continue;
    }
    rows.push(cells);
  }
  return { headerSeen: headerCount === 1, rows, errors };
}

function validateV11ProductionQueryRows(brief, evidenceScope, evidenceRoot, problems) {
  if (evidenceScope !== 'production') return { rows: [], sharedDevice: '' };
  if (string(brief, 'query_evidence_status', problems) !== 'confirmed') {
    fail(problems, `${brief.source} production exact query-row contract requires query_evidence_status=confirmed`);
    return { rows: [], sharedDevice: '' };
  }
  const refs = strings(brief, 'query_evidence_refs', problems, { allowEmpty: true });
  if (!refs.length) { fail(problems, `${brief.source} production exact query-row contract requires non-empty query_evidence_refs`); return { rows: [], sharedDevice: '' }; }
  const allRows = [];
  for (const ref of refs) {
    const section = loadReferencedSection(ref, evidenceRoot);
    if (!section) { fail(problems, `${brief.source} production query evidence ref ${ref} must resolve to a valid fragment`); continue; }
    const parsed = parseV11QueryRows(section);
    if (!parsed.headerSeen) fail(problems, `${brief.source} production query evidence ref ${ref} requires exact 11-slot query row header`);
    for (const error of parsed.errors) fail(problems, `${brief.source} production query evidence ref ${ref} ${error}`);
    for (const cells of parsed.rows) allRows.push({ cells, ref });
  }
  const expectedQueries = [string(brief, 'primary_query', problems), ...strings(brief, 'supporting_query_variants', problems)];
  const observedQueries = allRows.map(({ cells }) => cells[0]);
  if (observedQueries.length !== expectedQueries.length || new Set(observedQueries).size !== observedQueries.length || !expectedQueries.every((query) => observedQueries.includes(query)) || observedQueries.some((query) => !expectedQueries.includes(query))) {
    fail(problems, `${brief.source} production query evidence row query set must exactly equal primary_query plus supporting_query_variants with no missing, extra, or duplicate row`);
  }
  const task = parseDominantTaskContract(brief, problems);
  let sharedDevice = '';
  for (const { cells, ref } of allRows) {
    const [query, action, object, output, stage, commitment, market, language, device, checkedAt, evidenceRef] = cells;
    for (const [label, actual, expected] of [['action', action, task.action], ['object', object, task.decisionObject], ['observable-output', output, task.expectedOutput], ['stage', stage, string(brief, 'stage', problems)], ['commercial-commitment', commitment, string(brief, 'commercial_commitment', problems)], ['market', market, string(brief, 'target_market', problems)], ['language', language, string(brief, 'target_content_language', problems)]]) {
      if (actual !== expected) fail(problems, `${brief.source} production query row ${query} ${label} must exactly match canonical contract`);
    }
    if (!device || /(?:synthetic|placeholder|unknown|tbd)/i.test(device)) fail(problems, `${brief.source} production query row ${query} requires a real device value`);
    if (!sharedDevice) sharedDevice = device;
    else if (device !== sharedDevice) fail(problems, `${brief.source} production query rows must use one exact device value`);
    requireFreshIsoDate(checkedAt, brief.source, `production query row ${query} checked_at`, problems);
    if (evidenceRef !== ref) fail(problems, `${brief.source} production query row ${query} evidence_ref must exactly equal the containing query_evidence_ref fragment`);
  }
  return { rows: allRows, sharedDevice };
}

function inferCrossRoleDelegation(brief) {
  const ctaFrom = normalizeText(string(brief, 'cta_from_role', []));
  const ctaTo = normalizeText(string(brief, 'cta_to_role', []));
  if (ctaFrom && ctaTo && ctaFrom !== 'not-applicable' && ctaTo !== 'not-applicable' && ctaFrom !== ctaTo) return true;
  const primary = normalizeText(string(brief, 'primary_buyer_role', []));
  for (const row of strings(brief, 'internal_link_buyer_task_contracts', [], { allowEmpty: true })) {
    const parts = row.split('|').map((part) => part.trim());
    if (parts.length === 9 && normalizeText(parts[4]) && normalizeText(parts[4]) !== primary) return true;
  }
  return false;
}

const V12_CTA_ROLE_FIELDS = ['cta_from_role', 'cta_to_role', 'cta_receiving_task', 'cta_receiving_owner'];

function validateV12CtaRoleHandoffParity(records, brief, problems) {
  for (const record of records) for (const field of V12_CTA_ROLE_FIELDS) {
    if (!(field in record.attributes)) fail(problems, `${record.source} V12 CTA role schema requires ${field} in all four records`);
  }
  for (const field of V12_CTA_ROLE_FIELDS) requireCanonicalMatch(records, field, problems);
  if (records.some((record) => V12_CTA_ROLE_FIELDS.some((field) => !(field in record.attributes)))) return;
  const interaction = string(brief, 'cta_interaction_type', problems);
  const fromRole = string(brief, 'cta_from_role', problems);
  const toRole = string(brief, 'cta_to_role', problems);
  const receivingTask = string(brief, 'cta_receiving_task', problems);
  const receivingOwner = string(brief, 'cta_receiving_owner', problems);
  const crossRoleCta = interaction === 'human-handoff' || interaction === 'commercial';
  if (!crossRoleCta) {
    for (const [field, value] of [['cta_from_role', fromRole], ['cta_to_role', toRole], ['cta_receiving_task', receivingTask], ['cta_receiving_owner', receivingOwner]]) {
      if (value !== 'not-applicable') fail(problems, `${brief.source} ${interaction} CTA requires ${field}=not-applicable because it is not a cross-role CTA`);
    }
    return;
  }
  const stage = string(brief, 'stage', problems);
  const commitment = string(brief, 'commercial_commitment', problems);
  if (interaction === 'commercial' && (stage !== 'buy' || commitment !== 'commercial')) fail(problems, `${brief.source} commercial CTA role handoff requires stage=buy and commercial_commitment=commercial`);
  if (interaction === 'human-handoff' && stage === 'learn') fail(problems, `${brief.source} human-handoff CTA is not valid for stage=learn`);
  for (const [field, value] of [['cta_from_role', fromRole], ['cta_to_role', toRole], ['cta_receiving_task', receivingTask], ['cta_receiving_owner', receivingOwner]]) {
    if (!value || value === 'not-applicable') fail(problems, `${brief.source} ${interaction} CTA requires a concrete ${field}`);
  }
  if (normalizeText(fromRole) === normalizeText(toRole)) fail(problems, `${brief.source} ${interaction} CTA requires distinct cta_from_role and cta_to_role`);
  requireStableOwnerIdentity(receivingOwner, brief.source, 'cta_receiving_owner', problems);
  const destination = string(brief, 'cta_destination', problems);
  const owner = string(brief, 'cta_owner', problems);
  if (semanticOverlap(toRole, receivingOwner).length < 1) fail(problems, `${brief.source} cta_receiving_owner must visibly identify the buyer-side receiving role`);
  if (interaction === 'commercial') {
    if (normalizeText(receivingOwner) === normalizeText(owner)) fail(problems, `${brief.source} commercial CTA must separate the buyer-side receiving owner from the external route owner`);
    let destinationPath = '';
    try { destinationPath = new URL(destination).pathname; } catch { /* URL validity is reported by requireAbsoluteHttpsUrl. */ }
    const technicalOnlyPath = /(?:engineering|technical|readiness|support|diagnostic)/i.test(destinationPath)
      && !/(?:commercial|rfq|quote|quotation|pricing|procurement)/i.test(destinationPath);
    if (technicalOnlyPath) fail(problems, `${brief.source} commercial CTA destination must not use a technical-only or engineering-only route`);
  }
  const matches = strings(brief, 'role_handoff_contracts', problems, { allowEmpty: true }).filter((row) => {
    const parts = row.split('|').map((part) => part.trim());
    return parts.length === 7
      && parts[0] === fromRole
      && parts[1] === toRole
      && (destination === 'not-applicable' || parts[2] === destination)
      && parts[4] === receivingTask
      && parts[5] === receivingOwner;
  });
  if (matches.length !== 1) fail(problems, `${brief.source} ${interaction} CTA must match exactly one role_handoff_contracts row on from_role, to_role, url, receiving_task, and buyer-side receiving_owner; deleting or duplicating the handoff is blocked`);
}

function validateV12SecondaryBuyerRoleContracts(records, brief, publish, evidenceScope, evidenceRoot, problems) {
  const field = 'secondary_buyer_role_contracts';
  for (const record of records) if (!(field in record.attributes)) fail(problems, `${record.source} V12 secondary buyer schema requires ${field} in all four records`);
  requireCanonicalMatch(records, field, problems);
  if (records.some((record) => !(field in record.attributes))) return;
  const secondaryRoles = strings(brief, 'secondary_buyer_roles', problems, { allowEmpty: true });
  if (new Set(secondaryRoles.map(normalizeText)).size !== secondaryRoles.length) fail(problems, `${brief.source} secondary_buyer_roles must not contain duplicates`);
  if ('secondary_buyer_roles_snapshot' in publish.attributes && !sameNormalizedSet(secondaryRoles, strings(publish, 'secondary_buyer_roles_snapshot', problems, { allowEmpty: true }))) {
    fail(problems, `${publish.source} secondary_buyer_roles_snapshot must exactly match Brief secondary_buyer_roles`);
  }
  const expected = new Map(secondaryRoles.map((role) => [normalizeText(requireCanonicalBuyerRole(role, brief.source, 'secondary_buyer_roles', problems, { canonicalOnly: true })), role]));
  const rows = strings(brief, field, problems, { allowEmpty: true });
  if (!expected.size && rows.length) fail(problems, `${brief.source} ${field} must be empty when secondary_buyer_roles is empty`);
  const seen = new Set();
  for (const row of rows) {
    const parts = row.split('|').map((part) => part.trim());
    if (parts.length !== 4 || parts.some((part) => !part)) {
      fail(problems, `${brief.source} ${field} entry must use role|evidence_ref|concrete_objection|article_owned_answer: ${row}`);
      continue;
    }
    const [rawRole, evidenceRef, objection, articleAnswer] = parts;
    const role = requireCanonicalBuyerRole(rawRole, brief.source, `${field} role`, problems, { canonicalOnly: true });
    const key = normalizeText(role);
    if (seen.has(key)) fail(problems, `${brief.source} ${field} must contain secondary role ${role} exactly once`);
    seen.add(key);
    if (!expected.has(key)) fail(problems, `${brief.source} ${field} contains unexpected role ${role}`);
    meaningfulScalar(objection, brief.source, `${field} ${role} concrete_objection`, problems, { minLength: 12 });
    meaningfulScalar(articleAnswer, brief.source, `${field} ${role} article_owned_answer`, problems, { minLength: 12 });
    const rolePattern = ROLE_SEMANTIC_PATTERNS.get(role);
    if (rolePattern && !rolePattern.test(`${objection} ${articleAnswer}`)) fail(problems, `${brief.source} ${field} ${role} must contain role-specific objection/answer semantics`);
    const resolved = validateLocalEvidenceRefs([evidenceRef], brief.source, `${field} ${role} evidence_ref`, evidenceRoot, problems, { requireFragment: true, verifyFragment: true });
    if (evidenceScope === 'production') {
      rejectSyntheticEvidenceFiles(resolved, brief.source, `${field} ${role} evidence_ref`, problems);
      const section = loadReferencedSection(evidenceRef, evidenceRoot) || '';
      const checkedAt = /(?:^|\n)\s*(?:[-*]\s*)?(?:checked_at|observed_at|reviewed_at)\s*:\s*['"]?([^'"\n]+)['"]?/im.exec(section)?.[1]?.trim() || '';
      if (!checkedAt) fail(problems, `${brief.source} production ${field} ${role} evidence fragment requires checked_at, observed_at, or reviewed_at`);
      else requireIsoDate(checkedAt, brief.source, `${field} ${role} evidence date`, problems);
      if (/\bsynthetic(?:-fixture)?\b|虚构|虚拟/i.test(section)) fail(problems, `${brief.source} production ${field} ${role} evidence fragment must be non-synthetic`);
    }
  }
  for (const [key, role] of expected) if (!seen.has(key)) fail(problems, `${brief.source} ${field} is missing secondary role ${role}`);
}

function parseV12SerpFields(section, source, ref, problems) {
  const allowed = new Set(['query_set', 'market', 'language', 'device', 'checked_at', 'result_types', 'primary_query', 'primary_query_sample_size', 'primary_query_result_type_counts', 'primary_query_dominant_result_type', 'primary_query_dominant_result_count', 'primary_query_dominance_threshold', 'primary_query_dominance_verdict', 'supporting_query_result_type_rows']);
  const fields = new Map();
  for (const line of section.split('\n').slice(1)) {
    const match = /^\s*(?:[-*]\s*)?([A-Za-z][A-Za-z0-9_-]{1,40})\s*:\s*(.*?)\s*$/.exec(line);
    if (!match) continue;
    const key = match[1];
    if (!allowed.has(key)) continue;
    if (fields.has(key)) fail(problems, `${source} SERP-format evidence ${ref} contains duplicate ${key}`);
    fields.set(key, match[2].trim().replace(/^['"]|['"]$/g, ''));
  }
  for (const key of allowed) if (!fields.get(key)) fail(problems, `${source} SERP-format evidence ${ref} requires one non-empty exact ${key}`);
  return fields;
}

function resultTypeCountMap(rows, source, field, problems) {
  const counts = new Map();
  for (const [index, row] of rows.entries()) {
    const parts = String(row).split('|').map((part) => part.trim());
    if (parts.length !== 2 || parts.some((part) => !part)) {
      fail(problems, `${source} ${field} row ${index + 1} must use normalized-result-type|positive-integer`);
      continue;
    }
    const [rawType, rawCount] = parts;
    const type = normalizeText(rawType);
    const count = Number(rawCount);
    if (!type || type !== rawType || PLACEHOLDER_PATTERN.test(type)) fail(problems, `${source} ${field} row ${index + 1} result type must already be normalized and concrete`);
    if (!Number.isInteger(count) || count < 1 || String(count) !== rawCount) fail(problems, `${source} ${field} row ${index + 1} count must be a canonical positive integer`);
    if (counts.has(type)) fail(problems, `${source} ${field} must not duplicate result type ${type}`);
    counts.set(type, count);
  }
  return counts;
}

function parseExactStringSequence(value, source, field, problems) {
  const raw = String(value ?? '').trim();
  let values = [];
  if (raw.startsWith('[')) {
    try {
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed) || parsed.some((item) => typeof item !== 'string' || !item.trim())) throw new Error('not a non-empty string array');
      values = parsed.map((item) => item.trim());
    } catch {
      fail(problems, `${source} ${field} must be a JSON string array or semicolon-delimited exact sequence`);
    }
  } else {
    values = raw.split(';').map((item) => item.trim()).filter(Boolean);
  }
  return values;
}

function parseCanonicalResultTypeCounts(record, problems) {
  const rows = strings(record, 'serp_primary_query_result_type_counts', problems, { allowEmpty: true });
  return resultTypeCountMap(rows, record.source, 'serp_primary_query_result_type_counts', problems);
}

const CANONICAL_SERP_RESULT_TYPES = new Set(CONTENT_TYPE_FAMILY_PATTERNS.map(([family]) => family));

function validateCanonicalSerpResultTypes(resultTypes, source, field, problems) {
  for (const [index, rawType] of resultTypes.entries()) {
    const normalized = normalizeText(rawType);
    if (!normalized || rawType !== normalized || PLACEHOLDER_PATTERN.test(rawType) || !CANONICAL_SERP_RESULT_TYPES.has(normalized)) {
      fail(problems, `${source} ${field} item ${index + 1} must be an exact canonical SERP result type: ${[...CANONICAL_SERP_RESULT_TYPES].join('|')}`);
    }
  }
}

function recomputeResultTypeEvidence(resultTypes) {
  const counts = new Map();
  for (const resultType of resultTypes) {
    const normalizedType = normalizeText(resultType);
    counts.set(normalizedType, (counts.get(normalizedType) || 0) + 1);
  }
  const sorted = [...counts.entries()].sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]));
  return { counts, dominantType: sorted[0]?.[0] || '', dominantCount: sorted[0]?.[1] || 0 };
}

function validateSupportingSerpRows({ brief, rows, evidenceRoot, market, language, device, checkedAt, primaryFamily, expectedFamily, problems }) {
  const expectedQueries = strings(brief, 'supporting_query_variants', problems);
  const seenQueries = new Set();
  for (const [index, row] of rows.entries()) {
    const parts = row.split('|').map((part) => part.trim());
    if (parts.length !== 7 || parts.some((part) => !part)) {
      fail(problems, `${brief.source} supporting SERP row ${index + 1} must use exact-query|sample-size|dominant-result-type|dominant-result-count|threshold|verdict|fragment-bound-evidence-ref`);
      continue;
    }
    const [query, rawSampleSize, dominantType, rawDominantCount, rawThreshold, verdict, evidenceRef] = parts;
    if (seenQueries.has(query)) fail(problems, `${brief.source} supporting SERP rows must not duplicate query ${query}`);
    seenQueries.add(query);
    if (!expectedQueries.includes(query)) fail(problems, `${brief.source} supporting SERP row ${index + 1} query must exactly match one supporting_query_variants value`);
    const sampleSize = Number(rawSampleSize);
    const dominantCount = Number(rawDominantCount);
    const threshold = Number(rawThreshold);
    if (!Number.isInteger(sampleSize) || sampleSize < 5) fail(problems, `${brief.source} supporting SERP row ${index + 1} sample size must be an integer >= 5`);
    if (!Number.isInteger(dominantCount) || dominantCount < 1 || dominantCount > sampleSize) fail(problems, `${brief.source} supporting SERP row ${index + 1} dominant count must be within sample size`);
    if (!Number.isFinite(threshold) || threshold <= 0.5 || threshold > 1) fail(problems, `${brief.source} supporting SERP row ${index + 1} threshold must be > 0.50 and <= 1`);
    if (Number.isFinite(sampleSize) && Number.isFinite(dominantCount) && Number.isFinite(threshold) && (dominantCount / sampleSize < threshold || dominantCount * 2 <= sampleSize)) fail(problems, `${brief.source} supporting SERP row ${index + 1} dominant count must satisfy the frozen threshold and strict majority`);
    if (!dominantType || PLACEHOLDER_PATTERN.test(dominantType)) fail(problems, `${brief.source} supporting SERP row ${index + 1} dominant result type must be concrete`);
    const supportingFamilyMatches = contentTypeFamilies(dominantType);
    const supportingFamily = supportingFamilyMatches.length === 1 ? supportingFamilyMatches[0] : '';
    if (!supportingFamily) {
      fail(problems, `${brief.source} supporting SERP row ${index + 1} dominant result type must map to exactly one supported content family; matched ${supportingFamilyMatches.length ? supportingFamilyMatches.join(', ') : 'none'} for ${dominantType}`);
    } else {
      if (primaryFamily && supportingFamily !== primaryFamily) fail(problems, `${brief.source} supporting SERP row ${index + 1} family ${supportingFamily} conflicts with primary query dominant SERP family ${primaryFamily}`);
      if (expectedFamily && supportingFamily !== expectedFamily) fail(problems, `${brief.source} supporting SERP row ${index + 1} family ${supportingFamily} conflicts with expected_content_type family ${expectedFamily}`);
    }
    if (normalizeText(verdict) !== 'pass') fail(problems, `${brief.source} supporting SERP row ${index + 1} dominance verdict must be pass`);
    const resolved = validateLocalEvidenceRefs([evidenceRef], brief.source, `supporting SERP row ${index + 1} evidence_ref`, evidenceRoot, problems, { requireFragment: true, verifyFragment: true });
    rejectSyntheticEvidenceFiles(resolved, brief.source, `supporting SERP row ${index + 1} evidence_ref`, problems);
    const fragment = loadReferencedSection(evidenceRef, evidenceRoot);
    if (!fragment) continue;
    const fields = parseEvidenceScalarFields(fragment);
    for (const key of ['query', 'market', 'language', 'device', 'checked_at', 'result_types', 'sample_size', 'dominant_result_type', 'dominant_result_count', 'dominance_threshold', 'dominance_verdict']) if (!fields.get(key)) fail(problems, `${brief.source} supporting SERP evidence ${evidenceRef} requires one non-empty ${key}`);
    for (const [key, expected] of [['query', query], ['market', market], ['language', language], ['device', device], ['checked_at', checkedAt], ['sample_size', rawSampleSize], ['dominant_result_type', dominantType], ['dominant_result_count', rawDominantCount], ['dominance_threshold', rawThreshold], ['dominance_verdict', verdict]]) if ((fields.get(key) || '') !== expected) fail(problems, `${brief.source} supporting SERP evidence ${evidenceRef} ${key} must exactly project its declared row and shared scope`);
    requireFreshIsoDate(fields.get('checked_at') || '', brief.source, `supporting SERP evidence ${evidenceRef} checked_at`, problems);
    const resultTypes = parseExactStringSequence(fields.get('result_types') || '', brief.source, `supporting SERP evidence ${evidenceRef} result_types`, problems);
    validateCanonicalSerpResultTypes(resultTypes, brief.source, `supporting SERP evidence ${evidenceRef} result_types`, problems);
    const recomputed = recomputeResultTypeEvidence(resultTypes);
    if (resultTypes.length !== sampleSize) fail(problems, `${brief.source} supporting SERP evidence ${evidenceRef} result_types count must equal sample_size`);
    if (recomputed.dominantType !== normalizeText(dominantType) || recomputed.dominantCount !== dominantCount) fail(problems, `${brief.source} supporting SERP evidence ${evidenceRef} dominant type and count must equal values recomputed from raw result_types`);
  }
  if (!sameNormalizedSet([...seenQueries], expectedQueries) || seenQueries.size !== expectedQueries.length) fail(problems, `${brief.source} supporting SERP rows must cover supporting_query_variants exactly once with no missing, extra, or duplicate query`);
}

function parseExactStringSet(value, source, field, problems) {
  const raw = String(value ?? '').trim();
  let values = [];
  if (raw.startsWith('[')) {
    try {
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed) || parsed.some((item) => typeof item !== 'string' || !item.trim())) throw new Error('not a non-empty string array');
      values = parsed.map((item) => item.trim());
    } catch {
      fail(problems, `${source} ${field} must be a JSON string array or semicolon-delimited exact set`);
    }
  } else {
    values = raw.split(';').map((item) => item.trim()).filter(Boolean);
  }
  if (new Set(values).size !== values.length) fail(problems, `${source} ${field} must not contain duplicates`);
  return values;
}

function validateV12SerpFormatEvidence(brief, evidenceScope, evidenceRoot, sharedQueryDevice, problems) {
  if (evidenceScope !== 'production') return;
  const refs = strings(brief, 'serp_format_evidence_refs', problems, { allowEmpty: true });
  const expectedQueries = [string(brief, 'primary_query', problems), ...strings(brief, 'supporting_query_variants', problems)];
  for (const ref of refs) {
    const section = loadReferencedSection(ref, evidenceRoot);
    if (!section) { fail(problems, `${brief.source} SERP-format evidence ref ${ref} must resolve to a valid fragment`); continue; }
    const fields = parseV12SerpFields(section, brief.source, ref, problems);
    const queries = parseExactStringSet(fields.get('query_set') || '', brief.source, `SERP-format evidence ${ref} query_set`, problems);
    if (!sameNormalizedSet(queries, expectedQueries) || queries.length !== expectedQueries.length) fail(problems, `${brief.source} SERP-format evidence ${ref} query_set must exactly equal primary_query plus supporting_query_variants with no missing, extra, or duplicate query`);
    for (const [field, expected] of [['market', string(brief, 'target_market', problems)], ['language', string(brief, 'target_content_language', problems)]]) {
      if ((fields.get(field) || '') !== expected) fail(problems, `${brief.source} SERP-format evidence ${ref} ${field} must exactly match Brief ${field === 'market' ? 'target_market' : 'target_content_language'}`);
    }
    const device = fields.get('device') || '';
    if (!device || /[/,]|\b(?:desktop\s*(?:and|\/|,)|mobile\s*(?:and|\/|,)|unknown|tbd|placeholder)\b/i.test(device)) fail(problems, `${brief.source} SERP-format evidence ${ref} device must be one exact non-placeholder device`);
    if (sharedQueryDevice && device !== sharedQueryDevice) fail(problems, `${brief.source} SERP-format evidence ${ref} device must exactly match the 11-slot query evidence rows`);
    const checkedAt = fields.get('checked_at') || '';
    if (!checkedAt) fail(problems, `${brief.source} SERP-format evidence ${ref} checked_at is required`);
    else requireFreshIsoDate(checkedAt, brief.source, `SERP-format evidence ${ref} checked_at`, problems);
    const resultTypes = parseExactStringSequence(fields.get('result_types') || '', brief.source, `SERP-format evidence ${ref} result_types`, problems);
    validateCanonicalSerpResultTypes(resultTypes, brief.source, `SERP-format evidence ${ref} result_types`, problems);
    if (!resultTypes.length || resultTypes.some((value) => /^(?:unknown|tbd|todo|placeholder|not-applicable)$/i.test(normalizeText(value)))) fail(problems, `${brief.source} SERP-format evidence ${ref} result_types must be a non-empty non-placeholder observation sequence`);
    const primaryQuery = fields.get('primary_query') || '';
    const sampleSize = Number(fields.get('primary_query_sample_size'));
    const dominantType = fields.get('primary_query_dominant_result_type') || '';
    const dominantCount = Number(fields.get('primary_query_dominant_result_count'));
    const threshold = Number(fields.get('primary_query_dominance_threshold'));
    const dominanceVerdict = normalizeText(fields.get('primary_query_dominance_verdict') || '');
    if (primaryQuery !== string(brief, 'primary_query', problems)) fail(problems, `${brief.source} SERP-format evidence ${ref} primary_query must exactly match Brief primary_query; supporting queries cannot substitute`);
    if (!Number.isInteger(sampleSize) || sampleSize < 5) fail(problems, `${brief.source} SERP-format evidence ${ref} primary_query_sample_size must be an integer >= 5`);
    if (!Number.isInteger(dominantCount) || dominantCount < 1 || dominantCount > sampleSize) fail(problems, `${brief.source} SERP-format evidence ${ref} primary_query_dominant_result_count must be within sample size`);
    if (!Number.isFinite(threshold) || threshold <= 0.5 || threshold > 1) fail(problems, `${brief.source} SERP-format evidence ${ref} primary_query_dominance_threshold must be > 0.50 and <= 1`);
    if (Number.isFinite(sampleSize) && Number.isFinite(dominantCount) && Number.isFinite(threshold) && (dominantCount / sampleSize < threshold || dominantCount * 2 <= sampleSize)) fail(problems, `${brief.source} SERP-format evidence ${ref} primary-query dominant count must satisfy the frozen threshold and strict majority`);
    if (!dominantType || /^(?:unknown|tbd|todo|placeholder|not-applicable)$/i.test(normalizeText(dominantType))) fail(problems, `${brief.source} SERP-format evidence ${ref} primary_query_dominant_result_type must be concrete`);
    if (dominanceVerdict !== 'pass') fail(problems, `${brief.source} SERP-format evidence ${ref} primary_query_dominance_verdict must be pass`);

    const { counts: observedCounts, dominantType: recomputedDominantType, dominantCount: recomputedDominantCount } = recomputeResultTypeEvidence(resultTypes);
    const evidenceCountRows = parseExactStringSequence(fields.get('primary_query_result_type_counts') || '', brief.source, `SERP-format evidence ${ref} primary_query_result_type_counts`, problems);
    const evidenceCounts = resultTypeCountMap(evidenceCountRows, brief.source, `SERP-format evidence ${ref} primary_query_result_type_counts`, problems);
    const declaredCounts = parseCanonicalResultTypeCounts(brief, problems);
    if (resultTypes.length !== sampleSize) fail(problems, `${brief.source} SERP-format evidence ${ref} result_types observation count must exactly equal primary_query_sample_size`);
    if (declaredCounts.size !== observedCounts.size || [...observedCounts].some(([type, count]) => declaredCounts.get(type) !== count)) {
      fail(problems, `${brief.source} serp_primary_query_result_type_counts must exactly equal counts recomputed from SERP-format evidence ${ref} result_types`);
    }
    if (evidenceCounts.size !== observedCounts.size || [...observedCounts].some(([type, count]) => evidenceCounts.get(type) !== count)) fail(problems, `${brief.source} SERP-format evidence ${ref} primary_query_result_type_counts must exactly equal counts recomputed from raw result_types`);
    const canonicalCountRows = strings(brief, 'serp_primary_query_result_type_counts', problems, { allowEmpty: true });
    if (JSON.stringify(canonicalCountRows) !== JSON.stringify(evidenceCountRows)) fail(problems, `${brief.source} serp_primary_query_result_type_counts must exactly project SERP-format evidence ${ref}`);
    if (normalizeText(dominantType) !== recomputedDominantType) fail(problems, `${brief.source} SERP-format evidence ${ref} primary_query_dominant_result_type must equal the recomputed dominant result type ${recomputedDominantType || 'missing'}`);
    if (dominantCount !== recomputedDominantCount) fail(problems, `${brief.source} SERP-format evidence ${ref} primary_query_dominant_result_count must equal the recomputed dominant count ${recomputedDominantCount}`);
    for (const [recordField, observed] of [['serp_primary_query', primaryQuery], ['serp_primary_query_sample_size', String(fields.get('primary_query_sample_size') || '')], ['serp_primary_query_dominant_result_type', dominantType], ['serp_primary_query_dominant_result_count', String(fields.get('primary_query_dominant_result_count') || '')], ['serp_primary_query_dominance_threshold', String(fields.get('primary_query_dominance_threshold') || '')], ['serp_primary_query_dominance_verdict', dominanceVerdict]]) if (String(brief.attributes[recordField] ?? '') !== observed) fail(problems, `${brief.source} ${recordField} must exactly project primary-query SERP evidence ${ref}`);
    const supportingRows = parseExactStringSequence(fields.get('supporting_query_result_type_rows') || '', brief.source, `SERP-format evidence ${ref} supporting_query_result_type_rows`, problems);
    const canonicalSupportingRows = strings(brief, 'serp_supporting_query_result_type_rows', problems, { allowEmpty: true });
    if (JSON.stringify(canonicalSupportingRows) !== JSON.stringify(supportingRows)) fail(problems, `${brief.source} serp_supporting_query_result_type_rows must exactly project SERP-format evidence ${ref}`);
    const primaryFamily = contentTypeFamily(dominantType);
    const expectedFamily = contentTypeFamily(string(brief, 'expected_content_type', problems));
    validateSupportingSerpRows({ brief, rows: supportingRows, evidenceRoot, market: fields.get('market') || '', language: fields.get('language') || '', device, checkedAt, primaryFamily, expectedFamily, problems });
  }
}

function validateV11RoleHandoffTrigger(brief, problems) {
  const handoffs = strings(brief, 'role_handoff_contracts', problems, { allowEmpty: true });
  const delegated = inferCrossRoleDelegation(brief);
  if (delegated && !handoffs.length) fail(problems, `${brief.source} real cross-role delegation requires role_handoff_contracts even when CTA input collection is not applicable`);
  if (!delegated && handoffs.length) fail(problems, `${brief.source} role_handoff_contracts must be empty when all targets remain same-role and no delegation exists`);
  for (const row of handoffs) {
    const parts = row.split('|').map((part) => part.trim());
    if (parts.length === 7 && normalizeText(parts[0]) === normalizeText(parts[1])) fail(problems, `${brief.source} role_handoff_contracts requires a real cross-role from_role to_role delegation`);
    if (parts.length === 7) requireStableOwnerIdentity(parts[5], brief.source, 'role_handoff_contracts receiving_owner', problems);
  }
}

function validateV11CanonicalVocabulary(records, problems) {
  const enums = [
    ['stage', TASK_STAGES, 'learn|troubleshoot|compare|validate|buy'],
    ['intent_class', INTENT_CLASSES, 'informational|troubleshooting|commercial-investigation|mixed-commercial|transactional'],
    ['commercial_commitment', COMMERCIAL_COMMITMENTS, 'none|soft|commercial'],
    ['cta_interaction_type', new Set(['inline-no-input', 'local-tool', 'input-collecting', 'human-handoff', 'commercial']), 'inline-no-input|local-tool|input-collecting|human-handoff|commercial'],
  ];
  for (const record of records) for (const [field, allowed, display] of enums) {
    const value = string(record, field, problems);
    if (!allowed.has(value)) fail(problems, `${record.source} ${field} must use exact lowercase canonical enum ${display}; legacy aliases and placeholders are blocked`);
  }
}

function validateV11Contracts({ records, brief, draft, review, publish, evidenceScope, evidenceRoot, problems }) {
  validateV11CanonicalVocabulary(records, problems);
  validateV11Qualification(brief, draft, publish, problems);
  validateV11ActualOutcomes(review, publish, evidenceRoot, problems);
  validateV11ZeroResultWords(brief, evidenceRoot, problems);
  const queryRows = validateV11ProductionQueryRows(brief, evidenceScope, evidenceRoot, problems);
  validateV11RoleHandoffTrigger(brief, problems);
  validateV12CtaRoleHandoffParity(records, brief, problems);
  validateV12SecondaryBuyerRoleContracts(records, brief, publish, evidenceScope, evidenceRoot, problems);
  validateV12SerpFormatEvidence(brief, evidenceScope, evidenceRoot, queryRows.sharedDevice, problems);
}

function validateV10Contracts({ records, brief, draft, review, publish, evidenceScope, evidenceRoot, formatProfile, problems }) {
  rejectMixedScriptPackage(records, draft, problems);
  validateV10Applicability(records, brief, draft, problems);
  validateV10SlateLinks(brief, draft, formatProfile, problems);
  validateV10Qualification(brief, draft, publish, problems);
  validateV10ProgressiveCta(brief, draft, problems);
  validateV10DirectAnswer(records, brief, draft, problems);
  validateV10PainChain(brief, draft, problems);
  validateV10ZeroResult(brief, review, evidenceScope, evidenceRoot, problems);
  validateV10ProductionAxes(records, brief, review, evidenceScope, evidenceRoot, problems);
  validateProductionSearchDemandEvidence(records, brief, review, evidenceScope, evidenceRoot, problems);
}

function skuShapedUrl(value) {
  try {
    const path = new URL(value).pathname;
    return /\/(?:products?|skus?|models?)\//i.test(path) || /(?:^|[-_/])[a-z]{1,8}-?\d{2,}[a-z0-9-]*(?:[-_/]|$)/i.test(path);
  } catch { return false; }
}

function primaryCtaSectionForStage(body, stage, selfServe) {
  const headingPattern = selfServe
    ? /self-check|local check|diagnostic check|decision worksheet/
    : stage === 'buy'
      ? /final cta|request .*quot(?:e|ation)|submit .*rfq|commercial request|contact .*sales/
      : /final cta|request .*engineering-readiness review|submit .*review|send .*review/;
  return markdownSectionByHeading(body, headingPattern)
    || ctaSectionsForStage(body, stage, selfServe).at(-1)
    || '';
}

function ctaSectionsForStage(body, stage, selfServe) {
  const headingPattern = selfServe
    ? /self-check|local check|diagnostic check|summary|decision worksheet/
    : stage === 'buy'
      ? /rfq|quote|commercial|request|submit|contact/
      : /request|submit|send|prepare .*packet|support|review|contact/;
  const lines = body.split('\n');
  const sections = [];
  const firstH2 = lines.findIndex((line) => /^##\s+/.test(line));
  const preamble = lines.slice(0, firstH2 < 0 ? lines.length : firstH2).join('\n');
  if (BUYER_ROUTE_ACTION_PATTERN.test(markdownPlainText(preamble)) || /\[[^\]]+\]\((?:https:\/\/|mailto:)/i.test(preamble)) sections.push(preamble);
  for (const paragraph of body.split(/\n\s*\n/u)) {
    if (BUYER_ROUTE_ACTION_PATTERN.test(markdownPlainText(paragraph))) sections.push(paragraph);
  }
  for (let index = 0; index < lines.length; index += 1) {
    const heading = /^(#{1,6})\s+(.+)$/.exec(lines[index]);
    if (!heading || heading[1].length !== 2) continue;
    let end = lines.length;
    for (let cursor = index + 1; cursor < lines.length; cursor += 1) {
      const nextHeading = /^(#{1,6})\s+/.exec(lines[cursor]);
      if (nextHeading && nextHeading[1].length <= heading[1].length) { end = cursor; break; }
    }
    const markdown = lines.slice(index, end).join('\n');
    const buyerVisibleCtaShape = headingPattern.test(normalizeText(heading[2]))
      || /\*\*(?:trigger|required inputs|expected output|validation boundary|if [^*]{0,80}(?:unavailable|fails?|does not work)):\*\*/i.test(markdown)
      || /\[[^\]]+\]\((?:https:\/\/|mailto:)/i.test(markdown) && BUYER_ROUTE_ACTION_PATTERN.test(markdownPlainText(markdown));
    if (buyerVisibleCtaShape) sections.push(markdown);
  }
  return [...new Set(sections.filter(Boolean))];
}


function countNormalizedSubstring(haystack, needle) {
  if (!needle) return 0;
  let count = 0;
  let cursor = 0;
  while ((cursor = haystack.indexOf(needle, cursor)) >= 0) {
    count += 1;
    cursor += Math.max(1, needle.length);
  }
  return count;
}

function buyerVisibleCtaCandidateBlocks(body) {
  const blocks = [];
  // CTA discovery is intentionally grammar-aware: an imperative must lead a
  // sentence/list/table cell (or follow one narrow buyer condition). This keeps
  // diagnostic prose such as "route grade" and "if missing: request evidence"
  // out of the inventory without weakening pre-H2, paragraph, list, table,
  // strong, link, request, book, download, or unsafe-route attack coverage.
  const buyerActionLead = /(?:^|[.!?]\s+)(?:(?:if|when|before|after|once|until)\b[^.!?]{0,140},\s*)?(?:please\s+)?(?:do not\s+)?(?:request|submit|send|share|upload|contact|book|download|email|forward|transfer|route|use|review|create|build|save|copy|prepare|assemble|complete|finali[sz]e|proceed|continue|move|follow|open|start|apply|register|join|call|schedule|get|order|buy|visit|message|talk\s+with|speak\s+with|reach(?:\s+out)?(?:\s+to)?|arrange|discuss)\b/i;
  const routeOrToolObject = /\b(?:verified route|approved route|secure route|channel|form|portal|endpoint|email|packet|worksheet|guide|solution family)\b/i;
  let offset = 0;
  for (const raw of String(body || '').split(/\n\s*\n/u)) {
    const start = String(body || '').indexOf(raw, offset);
    offset = start < 0 ? offset : start + raw.length;
    const plain = markdownPlainText(raw).trim();
    if (!plain || /^#{1,6}\s+/m.test(raw.trim())) continue;
    const links = [...raw.matchAll(/\[([^\]]+)\]\((https:\/\/[^)\s]+)\)/gi)].map((match) => ({ anchor: match[1], destination: match[2] }));
    const actionLead = buyerActionLead.test(plain);
    const linkAction = links.some((link) => buyerActionLead.test(markdownPlainText(link.anchor).trim()));
    const routeOrTool = routeOrToolObject.test(plain);
    const explicitRouteBoundary = /\b(?:verified|approved|secure|unverified|unavailable)\b.{0,80}\b(?:route|channel|form|portal|endpoint|email)\b|\b(?:route|channel|form|portal|endpoint|email)\b.{0,80}\b(?:verified|approved|secure|unverified|unavailable)\b/i.test(plain);
    const genericRouteImperative = /^(?:(?:if|when|before|after|once|until)\b[^.!?]{0,140},\s*)?(?:please\s+)?(?!the\b|a\b|an\b|this\b|that\b|these\b|those\b|we\b|our\b|it\b|there\b|no\b|not\b|without\b|do\s+not\b)[a-z][a-z-]*(?:\s+[^.!?]{0,100})?\b(?:through|via|using|into|to|on)\b[^.!?]{0,100}\b(?:verified|approved|secure|existing)\b[^.!?]{0,80}\b(?:route|channel|form|portal|endpoint|email|inbox)\b/i.test(plain);
    if ((links.length && (actionLead || linkAction)) || (actionLead && routeOrTool) || (actionLead && explicitRouteBoundary) || genericRouteImperative) {
      blocks.push({ raw, plain, links, index: Math.max(0, start) });
    }
  }
  return blocks;
}

function validateBuyerVisibleCtaInventory(records, brief, draft, evidenceRoot, evidenceScope, fallbackContract, problems) {
  requireCanonicalMatch(records, 'buyer_visible_cta_inventory', problems, 'buyer_visible_cta_inventory', 'exact-sequence');
  const { rows } = parsePipeRows(brief, 'buyer_visible_cta_inventory', problems, { parts: 10, minItems: 3, minPartLength: 2 });
  const canonicalOwner = string(brief, 'cta_owner', problems);
  const canonicalDestination = string(brief, 'cta_destination', problems);
  const normalizedBody = normalizeText(markdownPlainText(draft.body));
  const ids = new Set();
  const roles = new Set();
  const observedPositions = [];
  const parsedRows = [];

  for (const [index, parts] of rows.entries()) {
    if (parts.length !== 10) continue;
    const [surfaceId, locationKind, locator, instruction, destination, owner, interactionType, routeStatus, evidenceBundleRef, fallbackContractRef] = parts;
    const role = normalizeText(surfaceId).split('-')[0];
    if (!CONVERSION_SURFACE_ROLES.includes(role)) fail(problems, `${brief.source} buyer_visible_cta_inventory row ${index + 1} surface-id must start with primary-, soft-, or fallback-`);
    else roles.add(role);
    if (!/^(?:primary|soft|fallback)-[a-z0-9][a-z0-9-]{2,}$/i.test(surfaceId)) fail(problems, `${brief.source} buyer_visible_cta_inventory row ${index + 1} has an invalid stable surface-id: ${surfaceId}`);
    const normalizedId = normalizeText(surfaceId);
    if (ids.has(normalizedId)) fail(problems, `${brief.source} buyer_visible_cta_inventory duplicates surface-id ${surfaceId}`);
    ids.add(normalizedId);
    if (!CTA_INVENTORY_LOCATION_KINDS.has(normalizeText(locationKind))) fail(problems, `${brief.source} buyer_visible_cta_inventory ${surfaceId} location-kind is unsupported: ${locationKind}`);
    if (!CTA_INVENTORY_INTERACTION_TYPES.has(normalizeText(interactionType))) fail(problems, `${brief.source} buyer_visible_cta_inventory ${surfaceId} interaction-type is unsupported: ${interactionType}`);
    if (!CTA_FALLBACK_ROUTE_STATUSES.has(normalizeText(routeStatus))) fail(problems, `${brief.source} buyer_visible_cta_inventory ${surfaceId} route-status must be verified, unverified-unavailable, or not-applicable`);
    meaningfulScalar(locator, brief.source, `buyer_visible_cta_inventory ${surfaceId} locator`, problems, { minLength: 6 });
    meaningfulScalar(instruction, brief.source, `buyer_visible_cta_inventory ${surfaceId} instruction`, problems, { minLength: 16 });
    rejectOwnerPlaceholder(owner, brief.source, `buyer_visible_cta_inventory ${surfaceId} owner`, problems);

    const normalizedInstruction = normalizeText(instruction);
    const occurrences = countNormalizedSubstring(normalizedBody, normalizedInstruction);
    if (occurrences !== 1) fail(problems, `${draft.source} buyer_visible_cta_inventory ${surfaceId} instruction must resolve exactly once in the publishable body; observed ${occurrences}`);
    const position = normalizedBody.indexOf(normalizedInstruction);
    observedPositions.push({ surfaceId, position });

    const normalizedInteraction = normalizeText(interactionType);
    const normalizedRoute = normalizeText(routeStatus);
    const isFallbackRouteSurface = normalizedId.startsWith('fallback-') && fallbackContractRef === 'cta_fallback_route_contract';
    const expectedRouteContract = isFallbackRouteSurface ? fallbackContract : null;
    if (normalizedInteraction === 'content-navigation') {
      requireAbsoluteHttpsUrl(destination, brief.source, `buyer_visible_cta_inventory ${surfaceId} destination`, problems);
      const internalGatesPass = internalLinkPublicationGatesPass(brief, problems);
      const actualLinkPresent = draft.body.includes(`](${destination})`);
      const destinationVisible = String(draft.body || '').includes(destination);
      if (internalGatesPass && !actualLinkPresent) fail(problems, `${draft.source} buyer_visible_cta_inventory ${surfaceId} content-navigation destination is not present as an actual Markdown link after all internal-link gates pass`);
      if (!internalGatesPass && destinationVisible) fail(problems, `${draft.source} buyer_visible_cta_inventory ${surfaceId} destination must not be buyer-visible until all internal-link gates pass`);
      if (normalizedRoute !== 'not-applicable') fail(problems, `${brief.source} buyer_visible_cta_inventory ${surfaceId} content-navigation route-status must be not-applicable; internal-link evidence is governed separately`);
      if (fallbackContractRef !== 'not-applicable') fail(problems, `${brief.source} buyer_visible_cta_inventory ${surfaceId} content-navigation fallback-contract-ref must be not-applicable`);
      if (evidenceBundleRef === 'not-applicable') fail(problems, `${brief.source} buyer_visible_cta_inventory ${surfaceId} content-navigation requires an evidence-bundle-ref`);
      else validateLocalEvidenceRefs([evidenceBundleRef], brief.source, `buyer_visible_cta_inventory ${surfaceId} evidence-bundle-ref`, evidenceRoot, problems, { requireFragment: true, regularNonSymlink: true, verifyFragment: true });
    } else if (normalizedInteraction === 'local-tool' || normalizedInteraction === 'inline-no-input') {
      if (destination !== 'not-applicable' || normalizedRoute !== 'not-applicable' || evidenceBundleRef !== 'not-applicable' || fallbackContractRef !== 'not-applicable') {
        fail(problems, `${brief.source} buyer_visible_cta_inventory ${surfaceId} local/no-input surface requires destination, route-status, evidence-bundle-ref, and fallback-contract-ref all not-applicable`);
      }
    } else if (normalizedRoute === 'unverified-unavailable') {
      if (destination !== 'not-applicable') fail(problems, `${brief.source} buyer_visible_cta_inventory ${surfaceId} unverified-unavailable destination must be not-applicable`);
      const expectedOwner = expectedRouteContract?.owner || canonicalOwner;
      if (owner !== expectedOwner) fail(problems, `${brief.source} buyer_visible_cta_inventory ${surfaceId} owner must exactly match ${isFallbackRouteSurface ? 'cta_fallback_route_contract owner' : 'canonical cta_owner'}`);
      if (evidenceBundleRef !== 'not-applicable') fail(problems, `${brief.source} buyer_visible_cta_inventory ${surfaceId} unverified-unavailable evidence-bundle-ref must be not-applicable`);
      if (fallbackContractRef !== 'cta_fallback_route_contract') fail(problems, `${brief.source} buyer_visible_cta_inventory ${surfaceId} unverified-unavailable fallback-contract-ref must be cta_fallback_route_contract`);
      if (isFallbackRouteSurface && normalizeText(expectedRouteContract?.status) !== normalizedRoute) fail(problems, `${brief.source} buyer_visible_cta_inventory ${surfaceId} route-status must exactly match cta_fallback_route_contract`);
      const isRouteRecoveryInstruction = isFallbackRouteSurface
        && /\b(?:ask|request|contact|obtain)\b/i.test(instruction);
      if (isRouteRecoveryInstruction && !hasExistingApprovedSupplierContactProcess(instruction)) {
        fail(problems, `${brief.source} every buyer-visible fallback instruction must use the buyer's existing approved supplier-contact process`);
      }
      if (isRouteRecoveryInstruction && !hasVerifiedRouteMetadataRequest(instruction)) {
        fail(problems, `${brief.source} every buyer-visible fallback instruction must request a verified route`);
      }
      const explicitUnavailableLocalBoundary = hasExplicitUnavailableRouteDisclosure(instruction)
        && /\b(?:do not|never|cannot|must not)\b[^.!?]{0,160}\b(?:send|submit|upload|share|attach|paste|copy|transmit|hand\s*off)\b/i.test(instruction)
        && /\b(?:keep|save|retain)\b[^.!?]{0,100}\b(?:local|locally|on your device)\b/i.test(instruction);
      if (/do-not-send/i.test(surfaceId) && !/\b(?:do not|never|cannot|must not)\b[^.!?]{0,160}\b(?:send|submit|upload|share|attach|paste|copy|transmit|hand\s*off)\b/i.test(instruction)) {
        fail(problems, `${brief.source} buyer_visible_cta_inventory ${surfaceId} unverified route instruction must visibly preserve the do-not-send or verified-route boundary`);
      }
      if (!isSafeUnverifiedRouteBoundary(instruction) && !isClauseLocalSafeTransfer(instruction) && !explicitUnavailableLocalBoundary) fail(problems, `${brief.source} buyer_visible_cta_inventory ${surfaceId} unverified route instruction must visibly preserve the do-not-send or verified-route boundary`);
    } else if (normalizedRoute === 'verified') {
      const expectedDestination = expectedRouteContract?.endpoint || canonicalDestination;
      const expectedOwner = expectedRouteContract?.owner || canonicalOwner;
      if (expectedDestination === 'not-applicable' || destination !== expectedDestination) fail(problems, `${brief.source} buyer_visible_cta_inventory ${surfaceId} verified destination must exactly match ${isFallbackRouteSurface ? 'cta_fallback_route_contract endpoint' : 'canonical cta_destination'}`);
      if (owner !== expectedOwner) fail(problems, `${brief.source} buyer_visible_cta_inventory ${surfaceId} verified owner must exactly match ${isFallbackRouteSurface ? 'cta_fallback_route_contract owner' : 'canonical cta_owner'}`);
      if (isFallbackRouteSurface && normalizeText(expectedRouteContract?.status) !== normalizedRoute) fail(problems, `${brief.source} buyer_visible_cta_inventory ${surfaceId} route-status must exactly match cta_fallback_route_contract`);
      if (evidenceBundleRef === 'not-applicable') fail(problems, `${brief.source} buyer_visible_cta_inventory ${surfaceId} verified route requires endpoint-specific evidence-bundle-ref`);
      else validateLocalEvidenceRefs([evidenceBundleRef], brief.source, `buyer_visible_cta_inventory ${surfaceId} evidence-bundle-ref`, evidenceRoot, problems, { requireFragment: true, regularNonSymlink: true, verifyFragment: true });
      if (fallbackContractRef !== 'cta_fallback_route_contract') fail(problems, `${brief.source} buyer_visible_cta_inventory ${surfaceId} verified route must bind cta_fallback_route_contract`);
    } else if (normalizedRoute === 'not-applicable' && !['content-navigation', 'local-tool', 'inline-no-input'].includes(normalizedInteraction)) {
      fail(problems, `${brief.source} buyer_visible_cta_inventory ${surfaceId} collecting/handoff/commercial surface cannot use route-status=not-applicable`);
    }
    parsedRows.push({ surfaceId, instruction: normalizedInstruction, destination, interactionType: normalizedInteraction, routeStatus: normalizedRoute });
  }

  for (const requiredRole of CONVERSION_SURFACE_ROLES) if (!roles.has(requiredRole)) fail(problems, `${brief.source} buyer_visible_cta_inventory must include at least one ${requiredRole} surface`);
  const located = observedPositions.filter((entry) => entry.position >= 0);
  for (let index = 1; index < located.length; index += 1) if (located[index].position <= located[index - 1].position) {
    fail(problems, `${brief.source} buyer_visible_cta_inventory rows must follow publishable-body order; ${located[index].surfaceId} is reordered or duplicated`);
    break;
  }

  for (const candidate of buyerVisibleCtaCandidateBlocks(draft.body)) {
    const candidatePlain = normalizeText(candidate.plain);
    const covered = parsedRows.some((row) => {
      if (!row.instruction) return false;
      return candidatePlain === row.instruction || row.instruction.includes(candidatePlain) || candidatePlain.includes(row.instruction);
    });
    if (!covered) {
      fail(problems, `${draft.source} buyer-visible CTA instruction is missing from buyer_visible_cta_inventory: ${candidate.plain.slice(0, 180)}`);
    }
  }

  // A synthetic fixture can prove the inventory shape, not endpoint capability.
  if (evidenceScope === 'synthetic-fixture' && parsedRows.some((row) => row.routeStatus === 'verified')) {
    fail(problems, `${brief.source} synthetic fixture buyer_visible_cta_inventory must not claim a verified CTA route`);
  }
}

function transmissionClauses(value) {
  return markdownPlainText(String(value || ''))
    .split(/(?<=[.!?;。！？；])\s+|\n+|\s*,?\s*\b(?:but|however|although|yet|instead|then)\b\s*/iu)
    .map((clause) => clause.trim())
    .filter(Boolean);
}

function hasPacketTransferIntent(clause) {
  const value = String(clause || '').replace(/\b(?:endpoint\s+)?(?:gates?|checks?|conditions?|polic(?:y|ies)|evidence)\s+(?:all\s+)?pass(?:es|ed)?\b/gi, '');
  const object = /\b(?:packet|worksheet|file|drawing|data|request|handoff|inputs?|details?|message|it|them|this|that)\b/i.test(value);
  if (!object) return false;
  const capabilityOnly = /\b(?:able|capacity|capable)\s+to\s+(?:provide|supply|present)\b/i.test(value)
    && !/\b(?:to|via|through|into)\s+(?:engineering|technical|sales|commercial|support|review|a\s+route|the\s+route|an\s+endpoint|a\s+recipient|the\s+recipient)\b/i.test(value)
    && !/\b(?:may|must|should|will|shall|can)\s+be\s+(?:submitted|sent|shared|uploaded|emailed|forwarded|transferred|transmitted|delivered|provided|dispatched|relayed|conveyed|furnished|supplied|presented|couriered|passed|posted|pasted|attached|handed|turned|given|granted|made|placed)\b/i.test(value);
  if (capabilityOnly) return false;
  return hasDirectTransmissionAction(value) || TRANSFER_OF_CONTROL_PATTERN.test(value);
}

function isClauseLocalSafeTransfer(clause) {
  const value = String(clause || '');
  if (!hasPacketTransferIntent(value)) return true;
  const directNegation = /\b(?:do\s+not|don't|must\s+not|may\s+not|cannot|can't|never)\b[^.!?;]{0,100}(?:submit|send|share|upload|email|forward|transfer|transmit|deliver|provide|dispatch|relay|convey|furnish|supply|present|courier|pass|post|paste|attach|hand|turn|give|grant|make|place|let)\b/i.test(value);
  const localOnly = /\b(?:keep|save|prepare|assemble|complete|review|check|store)\b[^.!?;]{0,120}\b(?:local|locally|offline|on\s+your\s+device|in\s+your\s+local\s+workspace)\b/i.test(value)
    && !/\b(?:to|for|via|through|into)\s+(?:engineering|technical|sales|commercial|support|review|a\s+route|the\s+route|an\s+endpoint)\b/i.test(value);
  const explicitNoData = /\b(?:submit|send|share|upload|email|forward|transfer|transmit|deliver|provide|post|paste|attach)\s+no\s+(?:project\s+)?(?:data|details?|inputs?|files?)\b/i.test(value);
  const explicitlyBlockedActions = /\b(?:upload|share|attach|paste|copy(?:-into)?|transmit|handoff|hand\s+off|send|submit|transfer)(?:\s*,?\s*(?:and|or)?\s*)+(?:actions?\s+)?(?:remain\s+)?(?:blocked|prohibited)\b/i.test(value)
    || /\b(?:actions?|transmission|transfer|handoff)\b[^.!?;]{0,50}\b(?:remain\s+)?(?:blocked|prohibited)\b/i.test(value);
  const keepBlocked = /\bkeep\b[^.!?;]{0,180}\b(?:actions?|upload|share|attach|paste|copy|transmit|handoff|hand\s+off|send|submit|transfer)\b[^.!?;]{0,120}\bblocked\b/i.test(value);
  return directNegation || localOnly || explicitNoData || explicitlyBlockedActions || keepBlocked;
}

function routeSafetySentences(markdown) {
  return transmissionClauses(markdown);
}

function hasDirectTransmissionAction(value) {
  return DIRECT_TRANSMISSION_ACTION_PATTERN.test(String(value || ''))
    || DIRECT_COPY_ACTION_PATTERN.test(String(value || ''));
}

function isSafeUnverifiedRouteBoundary(sentence) {
  const value = String(sentence || '');
  const postVerificationAction = /\bafter\s+(?:a|the)\s+(?:verified|approved|secure)(?:\s+[a-z0-9-]+){0,3}\s+(?:route|channel|form|portal|endpoint|email|inbox)\s+(?:(?:is|has\s+been)\s+(?:returned|confirmed|provided)|exists)\b[^.!?]{0,120}\b(?:submit|send|share|upload|contact|book|download|email|forward|transfer|copy|request|route|use|message|paste|attach|fill(?:\s+(?:in|out))?|enter|import|drag|drop(?:\s+off)?|post|provide|deliver|transmit|hand\s+over)\b/i.test(value);
  const withoutExplicitlySafeTransmission = value
    .replace(/\bdo not\b[^.!?]{0,40}\b(?:submit|send|share|upload|email|forward|transfer|copy|message|paste|attach|fill(?:\s+(?:in|out))?|enter|import|drag|drop(?:\s+off)?|post|provide|deliver|transmit|hand\s+over)(?:\s+or\s+(?:submit|send|share|upload|email|forward|transfer|copy|message|paste|attach|fill(?:\s+(?:in|out))?|enter|import|drag|drop(?:\s+off)?|post|provide|deliver|transmit|hand\s+over))*\b/gi, '')
    .replace(/\bafter\s+(?:a|the)\s+(?:verified|approved|secure)(?:\s+[a-z0-9-]+){0,3}\s+(?:route|channel|form|portal|endpoint|email|inbox)\s+(?:(?:is|has\s+been)\s+(?:returned|confirmed|provided)|exists)\b[^.!?]{0,160}\b(?:submit|send|share|upload|email|forward|transfer|copy|request|route|message|contact|use)\b/gi, '');
  if (hasDirectTransmissionAction(withoutExplicitlySafeTransmission)) return false;
  return /\b(?:no|not|never|without)\b.{0,60}\b(?:verified|approved|secure)\b.{0,60}\b(?:channel|route|form|portal|endpoint|email|inbox)\b/i.test(value)
    || /\b(?:no|not|never|without)\b.{0,60}\b(?:channel|route|form|portal|endpoint|email|inbox)\b.{0,40}\b(?:is|are|has been|have been)?\s*(?:verified|approved|secure)\b/i.test(value)
    || /\b(?:verified|approved|secure)\b.{0,60}\b(?:channel|route|form|portal|endpoint|email|inbox)\b.{0,40}\b(?:unavailable|not available|not configured|missing|unverified)\b/i.test(value)
    || /\b(?:request|ask for|obtain|confirm|verify)\b.{0,120}\b(?:a )?(?:production[- ]verified|verified|approved|secure)\b.{0,80}\b(?:destination|channel|route|form|portal|endpoint|email|inbox)\b/i.test(value)
    || /\bconfirm\b.{0,100}\b(?:route|channel|form|portal|endpoint|email|inbox)\b.{0,100}\b(?:active|available|identified|confirmed)\b/i.test(value)
    || /\bwhen\b.{0,120}\b(?:route|channel|form|portal|endpoint|email|inbox)\b.{0,120}\b(?:confirmed|verified|available)\b.{0,120}\b(?:use|send|submit|share|upload|attach|paste|copy|transmit|hand\s*off)\b/i.test(value)
    || postVerificationAction
    || /\buntil\b.{0,80}\b(?:verified|approved|secure|confirmed)\b/i.test(value)
    || /\b(?:do not\b.{0,80}|(?:upload|share|attach|paste|copy|transmit|handoff|hand off)[^.!?]{0,100}\b(?:blocked|prohibited)\b[^.!?]{0,80})\b(?:submit|send|share|upload|contact|book|download|email|forward|transfer|copy|route|paste|attach|fill(?:\s+(?:in|out))?|enter|import|drag|drop(?:\s+off)?|post|provide|deliver|transmit|hand\s+over|message|paste|attach|fill(?:\s+(?:in|out))?|enter|import|drag|drop(?:\s+off)?|post|provide|deliver|transmit|hand\s+over)\b/i.test(value);
}

function sectionHasUnsafeUnverifiedRoute(markdown) {
  const sentences = routeSafetySentences(markdown);
  let affirmativeRouteSeen = false;
  for (const sentence of sentences) {
    const safeBoundary = isSafeUnverifiedRouteBoundary(sentence);
    if (hasPacketTransferIntent(sentence) && !safeBoundary && !isClauseLocalSafeTransfer(sentence)) return true;
    const affirmativeRoute = /\b(?:verified|approved|secure)(?:\s+[a-z0-9-]+){0,5}\s+(?:channel|route|form|portal|endpoint|email|inbox)\b.{0,50}\b(?:is\s+available|is\s+ready|is\s+active|is\s+open|is\s+configured|exists|has\s+been\s+(?:verified|approved)|remains\s+available)\b/i.test(sentence)
      || /\b(?:channel|route|form|portal|endpoint|email|inbox)\b.{0,40}\b(?:is|has been|remains)\b.{0,20}\b(?:verified|approved|secure|available|ready|active|open|configured)\b/i.test(sentence);
    const imperativeAffirmativeRouteInstruction = /^(?:please\s+)?(?!do\s+not\b|do\s+not\b|no\b|not\b|without\b|through\s+your\s+organization'?s\s+existing\s+approved\s+supplier-contact\s+process\b)[a-z][a-z-]*(?:\s+[^.!?]{0,120})?\b(?:through|via|using|into|to|on)\b[^.!?]{0,100}\b(?:existing|verified|approved|secure)\b[^.!?]{0,80}\b(?:channel|route|form|portal|endpoint|email|inbox)\b/i.test(sentence);
    const directExistingChannelInstruction = /\b(?:submit|send|share|upload|contact|book|download|email|forward|transfer|copy|route|paste|attach|fill(?:\s+(?:in|out))?|enter|import|drag|drop(?:\s+off)?|post|provide|deliver|transmit|hand\s+over|proceed|continue|complete|finali[sz]e|move)\b.{0,120}\b(?:packet|message|file|drawing|data|request|handoff|it|them|this|that)\b.{0,100}\b(?:to|through|via|into|over)\b.{0,60}\b(?:existing|verified|approved|secure)\b.{0,60}\b(?:channel|route|form|portal|endpoint|email|inbox)\b/i.test(sentence)
      || /\b(?:submit|send|share|upload|contact|book|download|email|forward|transfer|copy|route|paste|attach|fill(?:\s+(?:in|out))?|enter|import|drag|drop(?:\s+off)?|post|provide|deliver|transmit|hand\s+over|proceed|continue|complete|finali[sz]e|move)\b.{0,100}\b(?:packet|message|file|drawing|data|request|handoff|it|them|this|that)\b.{0,30}\bthere\b/i.test(sentence);
    const followOnRouteInstruction = affirmativeRouteSeen
      && /\b(?:submit|send|share|upload|contact|book|download|email|forward|transfer|copy|route|paste|attach|fill(?:\s+(?:in|out))?|enter|import|drag|drop(?:\s+off)?|post|provide|deliver|transmit|hand\s+over)\b.{0,80}\b(?:there|that (?:channel|route|form|portal|endpoint))\b/i.test(sentence);
    if ((affirmativeRoute || imperativeAffirmativeRouteInstruction || directExistingChannelInstruction || followOnRouteInstruction) && !safeBoundary) return true;
    if (affirmativeRoute && !safeBoundary) affirmativeRouteSeen = true;
  }
  return false;
}

function sectionHasDirectUnverifiedEndpointInstruction(markdown) {
  const endpointPattern = /(?:https:\/\/|mailto:)?[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|https:\/\/[^\s)\]}>]+/gi;
  for (const paragraph of String(markdown || '').split(/\n\s*\n/u)) {
    const concreteEndpoint = /(?:https:\/\/|mailto:|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})/i.test(paragraph);
    if (!concreteEndpoint) continue;
    const visible = markdownPlainText(paragraph);
    const protectedPlain = visible.replace(endpointPattern, ' ENDPOINT ');
    const strongRouteAction = BUYER_ROUTE_ACTION_PATTERN.test(protectedPlain);
    if (!strongRouteAction) continue;
    const sentences = routeSafetySentences(protectedPlain);
    const endpointActionSentences = sentences.filter((sentence) => /\bENDPOINT\b/.test(sentence) && BUYER_ROUTE_ACTION_PATTERN.test(sentence));
    if (endpointActionSentences.some((sentence) => !isSafeUnverifiedRouteBoundary(sentence))) return true;
    if (!endpointActionSentences.length && !sentences.some((sentence) => BUYER_ROUTE_ACTION_PATTERN.test(sentence) && isSafeUnverifiedRouteBoundary(sentence))) return true;
  }
  return false;
}

function fallbackInstructionMarker(text) {
  return String(text || '').search(/if .{0,100}(?:unavailable|cannot|can't|does not work|doesn't work|fails?)|(?:route status:\s*)?no (?:production-)?verified (?:primary or fallback |submission )?(?:collection )?(?:[a-z0-9-]+\s+){0,2}(?:channel|route|form|portal|endpoint|email|inbox)(?: or endpoint-bound policy)? (?:is )?available/i);
}

function hasExplicitUnavailableRouteDisclosure(text) {
  return /\bno (?:production-)?verified (?:(?:primary or fallback|fallback or primary|primary|fallback|submission|alternate)\s+)?(?:collection )?(?:[a-z0-9-]+\s+){0,2}(?:channel|route|form|portal|endpoint|email|inbox)(?: or endpoint-bound policy)? (?:is )?available\b|\bverified (?:(?:primary or fallback|fallback or primary|primary|fallback|submission|alternate)\s+)?(?:channel|route|form|portal|endpoint|email|inbox) (?:is )?(?:unavailable|not available|not configured|missing)\b/i.test(String(text || ''));
}

function hasExistingApprovedSupplierContactProcess(text) {
  return /\b(?:existing|established)\b.{0,70}\bapproved\b.{0,80}\bsupplier[- ]contact process\b/i.test(String(text || ''))
    || /\b(?:your|the)\s+organization(?:'s|’s)\s+approved\s+supplier[- ]contact process\b/i.test(String(text || ''));
}

function hasVerifiedRouteMetadataRequest(text) {
  const value = String(text || '');
  const request = /\b(?:request|ask(?:\s+[^.!?]{0,50}\s+for)?|ask for|obtain)\b[^.!?]{0,130}\b(?:verified|approved|secure)\b[^.!?]{0,70}\b(?:collection\s+)?(?:route|destination|channel|form|portal|endpoint|email|inbox)\b/i.test(value);
  const positivePacketTransmission = /\b(?:send|submit|share|upload|paste|attach|provide|deliver|transmit|copy)\b[^.!?]{0,100}\b(?:packet|worksheet|file|drawing|data|inputs?)\b/i.test(value)
    && !/\bdo not\b[^.!?]{0,80}\b(?:send|submit|share|upload|paste|attach|provide|deliver|transmit|copy)\b/i.test(value);
  return request && !positivePacketTransmission;
}

function fallbackChunksForCtaSections(sections) {
  const chunks = [];
  for (const section of sections) {
    const marker = fallbackInstructionMarker(section);
    if (marker >= 0) chunks.push(section.slice(marker));
  }
  return chunks;
}

function decodeUnreservedPercentEncoding(value) {
  return String(value || '').replace(/%([0-9a-f]{2})/gi, (match, hex) => {
    const char = String.fromCharCode(Number.parseInt(hex, 16));
    return /^[A-Za-z0-9._~-]$/.test(char) ? char : `%${hex.toUpperCase()}`;
  });
}

function normalizeEndpointForComparison(value) {
  const raw = String(value ?? '').trim().replace(/[)>.,;:]+$/g, '');
  if (!raw) return '';
  if (/^(?:mailto:)?[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i.test(raw)) {
    return raw.replace(/^mailto:/i, 'mailto:').toLowerCase();
  }
  if (/^https:\/\//i.test(raw)) {
    try {
      const parsed = new URL(raw);
      parsed.protocol = 'https:';
      parsed.hostname = parsed.hostname.toLowerCase().replace(/\.+$/g, '');
      if (parsed.port === '443') parsed.port = '';
      parsed.pathname = decodeUnreservedPercentEncoding(parsed.pathname);
      return parsed.href;
    } catch {
      // Preserve fail-closed string comparison for malformed endpoint-like text.
    }
  }
  return raw.toLowerCase();
}

function buyerVisibleEndpoints(markdown) {
  return [...String(markdown || '').matchAll(/(?:mailto:)?[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|https:\/\/[^\s)\]}>|]+/gi)]
    .map((match) => normalizeEndpointForComparison(match[0]))
    .filter(Boolean);
}

function validateAllBuyerVisibleCtaRouteSafety(sections, fallbackContract, draft, problems) {
  if (!fallbackContract) return;
  const fallbackChunks = fallbackChunksForCtaSections(sections);
  if (fallbackContract.status === 'unverified-unavailable') {
    for (const section of sections) if (sectionHasUnsafeUnverifiedRoute(section)) {
      fail(problems, `${draft.source} unverified fallback contract is contradicted by an unsafe buyer-visible CTA section that asserts or instructs use of a verified, approved, secure, or existing route: ${markdownPlainText(section).slice(0, 240)}`);
    }
    for (const section of sections) {
      const marker = fallbackInstructionMarker(section);
      if (marker < 0) continue;
      const chunk = section.slice(marker);
      const visible = markdownPlainText(section);
      const instructionMarkdown = chunk.split(/\n\s*>/u, 1)[0];
      const instruction = markdownPlainText(instructionMarkdown);
      if (!hasExplicitUnavailableRouteDisclosure(visible)) {
        fail(problems, `${draft.source} every buyer-visible fallback instruction must explicitly disclose that no verified route is available`);
      }
      if (!/do not (?:submit|send|share|upload|contact|book|download|email|forward|transfer|copy|route)/i.test(instruction)) fail(problems, `${draft.source} every buyer-visible fallback instruction must prohibit transmitting the packet while the route is unverified`);
      if (!/(?:save|keep|retain).{0,40}(?:packet|copy|message|file).{0,35}(?:local|locally)|(?:save|keep|retain).{0,25}(?:local|locally)/i.test(instruction)) fail(problems, `${draft.source} every buyer-visible fallback instruction must keep the packet local`);
      const requestsRouteMetadata = /\b(?:request|ask|obtain)\b[^.!?]{0,180}\b(?:route|channel|form|portal|endpoint|email|inbox)\b/i.test(instruction);
      if (requestsRouteMetadata && !hasExistingApprovedSupplierContactProcess(instruction)) fail(problems, `${draft.source} route-recovery fallback instruction must use the buyer's existing approved supplier-contact process`);
      if (requestsRouteMetadata && !hasVerifiedRouteMetadataRequest(instruction)) fail(problems, `${draft.source} route-recovery fallback instruction must request a verified route`);
    }
    return;
  }
  if (fallbackContract.status === 'not-applicable') {
    if (fallbackChunks.length) fail(problems, `${draft.source} fallback route is not-applicable but buyer-visible CTA copy still contains a fallback-route instruction`);
    return;
  }
  if (fallbackContract.status !== 'verified') return;
  const endpoint = normalizeEndpointForComparison(fallbackContract.endpoint);
  if (!fallbackChunks.length) fail(problems, `${draft.source} verified fallback contract requires at least one buyer-visible fallback instruction`);
  for (const chunk of fallbackChunks) {
    if (!normalizeText(chunk).includes(normalizeText(fallbackContract.endpoint))) {
      fail(problems, `${draft.source} every buyer-visible fallback instruction must display the exact verified contract endpoint ${fallbackContract.endpoint}`);
    }
    if (!/(?:verified|approved).{0,70}(?:channel|route|form|portal|endpoint|email|inbox)|(?:channel|route|form|portal|endpoint|email|inbox).{0,70}(?:verified|approved)/i.test(markdownPlainText(chunk))) {
      fail(problems, `${draft.source} every buyer-visible fallback instruction must identify the concrete route as verified or approved`);
    }
    const observed = new Set();
    for (const match of chunk.matchAll(/(?:mailto:)?[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|https:\/\/[^\s)\]}>]+/gi)) observed.add(normalizeEndpointForComparison(match[0]));
    for (const candidate of observed) if (candidate && candidate !== endpoint) {
      fail(problems, `${draft.source} buyer-visible verified fallback endpoint ${candidate} must exactly match cta_fallback_route_contract endpoint ${fallbackContract.endpoint}`);
    }
  }
}

function markdownHttpsUrls(value) {
  return [...String(value || '').matchAll(/https:\/\/[^\s)\]}>|]+/gi)]
    .map((match) => normalizeEndpointForComparison(match[0]));
}

const IMAGE_LIKE_VISUAL_DECISION_ASSET_TYPES = new Set(['diagram', 'decision-tree', 'worksheet', 'annotated-product', 'process-flow']);
const GENERIC_IMAGE_ALT_PATTERN = /^(?:(?:the|a|an)\s+)?(?:image|photo|picture|figure|graphic|illustration|diagram|decision[- ]?tree|worksheet|annotated product|process[- ]?flow|chart)(?:\s+\d+)?$/i;
const RESERVED_IMAGE_HOST_PATTERN = /^(?:localhost|127(?:\.\d{1,3}){3}|0\.0\.0\.0|::1|(?:[^.]+\.)*example\.(?:com|net|org)|(?:[^.]+\.)*(?:example|invalid|localhost|test))$/i;
const PLACEHOLDER_IMAGE_SOURCE_PATTERN = /(?:^|[\s/_.-])(?:placeholder|placehold|replace[-_ ]?me|dummy[-_ ]?image|fake[-_ ]?image|synthetic[-_ ]?fixture|fixture[-_ ]?image|test[-_ ]?image)(?:$|[\s/_.-])/i;

function markdownImages(markdown) {
  const images = [];
  const pattern = /!\[([^\]\n]*)\]\(\s*(?:<([^>\n]+)>|([^\s)\n]+))(?:\s+(?:\"[^\"\n]*\"|'[^'\n]*'|\([^\)\n]*\)))?\s*\)/g;
  for (const match of String(markdown || '').matchAll(pattern)) {
    images.push({
      alt: match[1].trim(),
      source: (match[2] || match[3] || '').trim(),
      raw: match[0],
      index: match.index ?? -1,
    });
  }
  return images;
}

function canonicalMarkdownImageSource(source) {
  try { return new URL(source).href; }
  catch { return normalizeText(source); }
}

function validateRequiredDecisionAssetImage({ draft, assetType, buyerTask, claim, altIntent, placementSection, allBodyImages, boundImageSources, problems }) {
  const sectionBody = String(placementSection || '').split('\n').slice(1).join('\n');
  const sectionImages = markdownImages(sectionBody);
  if (sectionImages.length !== 1) {
    fail(problems, `${draft.source} required ${assetType} asset must bind to exactly one Markdown image inside its declared H2 section; found ${sectionImages.length}`);
    return;
  }

  const [image] = sectionImages;
  const normalizedAlt = normalizeText(image.alt);
  const altTokens = [...new Set(semanticTokens(image.alt))];
  if (!normalizedAlt
    || normalizedAlt.length < 16
    || altTokens.length < 4
    || GENERIC_IMAGE_ALT_PATTERN.test(normalizedAlt)
    || PLACEHOLDER_PATTERN.test(normalizedAlt)
    || /\b(?:placeholder|lorem ipsum|replace[- ]?me|synthetic fixture|test image)\b/i.test(normalizedAlt)
    || hasLowEntropy(image.alt)) {
    fail(problems, `${draft.source} required ${assetType} Markdown image alt must be non-empty, specific, non-placeholder, and information-bearing`);
  }
  if (semanticOverlap(image.alt, altIntent).length < 2) {
    fail(problems, `${draft.source} required ${assetType} Markdown image alt must materially match visual_decision_assets alt_intent`);
  }
  if (semanticOverlap(image.alt, `${buyerTask} ${claim}`).length < 2) {
    fail(problems, `${draft.source} required ${assetType} Markdown image alt must materially support the declared buyer task and claim`);
  }

  let parsedSource;
  try { parsedSource = new URL(image.source); }
  catch {
    fail(problems, `${draft.source} required ${assetType} Markdown image source must be an absolute HTTPS URL`);
  }
  if (parsedSource) {
    if (parsedSource.protocol !== 'https:' || !parsedSource.hostname) {
      fail(problems, `${draft.source} required ${assetType} Markdown image source must use HTTPS`);
    }
    const normalizedHost = parsedSource.hostname.replace(/^\[|\]$/g, '');
    let sourceMarker = `${normalizedHost}${parsedSource.pathname}${parsedSource.search}`;
    try { sourceMarker = decodeURIComponent(sourceMarker); } catch { /* Invalid escaping remains visible to the raw marker check. */ }
    if (RESERVED_IMAGE_HOST_PATTERN.test(normalizedHost)
      || PLACEHOLDER_IMAGE_SOURCE_PATTERN.test(sourceMarker)
      || parsedSource.username
      || parsedSource.password) {
      fail(problems, `${draft.source} required ${assetType} Markdown image source cannot use a placeholder, reserved synthetic fixture, loopback, or credential-bearing URL`);
    }
  }

  const sourceKey = canonicalMarkdownImageSource(image.source);
  const bodyOccurrences = allBodyImages.filter((candidate) => canonicalMarkdownImageSource(candidate.source) === sourceKey);
  if (bodyOccurrences.length !== 1) {
    fail(problems, `${draft.source} required ${assetType} Markdown image must occur exactly once in the publishable body and only inside its declared H2 section; found ${bodyOccurrences.length} uses of ${image.source}`);
  }
  if (boundImageSources.has(sourceKey)) {
    fail(problems, `${draft.source} required visual decision asset rows cannot reuse the same Markdown image source ${image.source}`);
  } else {
    boundImageSources.add(sourceKey);
  }
}

function controlRecordInternalLinkSection(record) {
  return markdownSectionByHeading(record.body, /internal[- ]link (?:task contracts|targets)/i);
}

function validateControlNarrativeRouteSafety({ brief, draft, publish, fallbackContract, problems }) {
  if (!fallbackContract || fallbackContract.status === 'not-applicable') return;
  const fallback = string(brief, 'cta_fallback_message_template', problems);
  const internalTargets = strings(brief, 'internal_link_targets', problems, { allowEmpty: true })
    .map((row) => row.split('|').map((part) => part.trim())[1])
    .filter(Boolean)
    .map(normalizeEndpointForComparison);
  const allowedTargets = new Set(internalTargets);
  const ctaFrom = normalizeText(string(brief, 'cta_from_role', problems));
  const ctaTo = normalizeText(string(brief, 'cta_to_role', problems));
  const reservedEndpoints = strings(brief, 'role_handoff_contracts', problems, { allowEmpty: true })
    .map((row) => row.split('|').map((part) => part.trim()))
    .filter((parts) => parts.length === 7
      && normalizeText(parts[0]) === ctaFrom
      && normalizeText(parts[1]) === ctaTo)
    .map((parts) => normalizeEndpointForComparison(parts[2]));
  const ctaRouteGatesPass = ['cta_reference_gate_verdict', 'cta_reachability_gate_verdict', 'cta_capability_gate_verdict']
    .every((field) => normalizeText(string(brief, field, problems)) === PASS);
  const draftEndpoints = new Set(buyerVisibleEndpoints(draft.body));
  if (fallbackContract.status === 'unverified-unavailable' || !ctaRouteGatesPass) for (const endpoint of reservedEndpoints) {
    if (endpoint && draftEndpoints.has(endpoint)) {
      fail(problems, `${draft.source} buyer-visible Draft cannot expose an unverified reserved CTA endpoint: ${endpoint}`);
    }
  }

  const internalGatesPass = internalLinkPublicationGatesPass(brief, problems);
  for (const record of [brief, publish]) {
    if (!String(record.body || '').includes(fallback)) {
      fail(problems, `${record.source} control-record narrative must include the exact cta_fallback_message_template`);
    }
    const internalSection = controlRecordInternalLinkSection(record);
    if (!internalSection) {
      fail(problems, `${record.source} control-record narrative requires a distinct internal-link/content-navigation section`);
      continue;
    }
    if (!/content[- ]navigation/i.test(markdownPlainText(internalSection))) {
      fail(problems, `${record.source} internal-link narrative must identify content-navigation separately from CTA submission routing`);
    }
    const observedUrls = markdownHttpsUrls(internalSection);
    for (const url of observedUrls) if (!allowedTargets.has(url)) {
      fail(problems, `${record.source} internal-link narrative URL must belong to internal_link_targets and must not mix worksheet or conversion endpoints: ${url}`);
    }
    if (internalGatesPass) {
      for (const target of allowedTargets) if (!observedUrls.includes(target)) {
        fail(problems, `${record.source} internal-link narrative must include every canonical internal_link_targets URL after all internal-link gates pass: ${target}`);
      }
    } else if (observedUrls.length) {
      fail(problems, `${record.source} internal-link narrative must keep blocked targets non-clickable and must not expose their URLs before all internal-link gates pass`);
    }
    if (!/(?:governed|recorded|handled) separately|separate(?:ly)? from|not (?:a|the) submission endpoint|neither is a submission endpoint/i.test(markdownPlainText(internalSection))) {
      fail(problems, `${record.source} content-navigation links and CTA submission routes must be recorded as separate areas`);
    }
    const narrativeEndpoints = new Set(buyerVisibleEndpoints(record.body));
    if (fallbackContract.status === 'unverified-unavailable') for (const endpoint of reservedEndpoints) {
      if (endpoint && narrativeEndpoints.has(endpoint)) {
        fail(problems, `${record.source} narrative cannot expose an unverified reserved CTA endpoint: ${endpoint}`);
      }
    }
  }
}

function validateDecisionAssetNarrativeParity(brief, draft, problems) {
  const assetRows = strings(brief, 'visual_decision_assets', problems, { allowEmpty: true })
    .map((row) => row.split('|').map((part) => part.trim()))
    .filter((parts) => parts.length === 9 && normalizeText(parts[8]) !== 'not-applicable');
  const articleStructure = markdownSectionByHeading(brief.body, /article structure/i);
  const readiness = markdownSectionByHeading(draft.body, /five[- ]input readiness/i);
  for (const [assetType] of assetRows) {
    const normalizedType = normalizeText(assetType);
    if (normalizedType === 'decision-list') {
      if (/five[- ]input table/i.test(markdownPlainText(articleStructure))) {
        fail(problems, `${brief.source} decision-list cannot be described as a five-input table in the article structure narrative`);
      }
      if (!/(?:stacked|checklist|list)/i.test(markdownPlainText(articleStructure))) {
        fail(problems, `${brief.source} decision-list requires a visible list, checklist, or stacked-checklist structure description`);
      }
      if (/^\s*\|.+\|\s*$/m.test(readiness)) {
        fail(problems, `${draft.source} decision-list readiness section must not drift into a Markdown table`);
      }
      if (!/^\s*(?:[-*+] |\d+[.)] )/m.test(readiness)) {
        fail(problems, `${draft.source} decision-list readiness section requires visible list or stacked-checklist items`);
      }
    }
  }
}

function validateV14StageBodyIsolation(brief, draft, problems) {
  const stage = normalizeText(string(brief, 'stage', problems));
  const body = normalizeText(markdownPlainText(draft.body));
  const incompatible = new Map([
    ['learn', /\b(?:second round|round two|technical qualification|candidate(?:\s+or\s+|-or-)stop|engineering readiness review|rfq|quotation|supplier award)\b/i],
    ['troubleshoot', /\b(?:second round|round two|technical qualification|technical qualified|sales accepted|supplier award)\b/i],
    ['compare', /\b(?:second round|round two|technical qualification|technical qualified|engineering readiness review)\b/i],
    ['buy', /\b(?:second round|round two|technical qualification|technical qualified|engineering readiness review)\b/i],
  ]);
  const match = incompatible.get(stage)?.exec(body);
  if (match) fail(problems, `${draft.source} ${stage} metadata cannot relabel body/lifecycle copy from another stage: ${match[0]}`);
}

function validateV14BuyerFacingConversionContracts(records, brief, draft, review, evidenceRoot, evidenceScope, problems) {
  const fallbackContract = validateCtaFallbackRouteContract(records, brief, evidenceRoot, evidenceScope, problems);
  const primaryRouteVerified = evidenceScope === 'production' && [
    ['cta_reference_check_execution_status', 'executed'],
    ['cta_reference_evidence_result', 'confirmed'],
    ['cta_reference_gate_verdict', 'pass'],
    ['cta_reachability_check_execution_status', 'executed'],
    ['cta_reachability_evidence_result', 'confirmed'],
    ['cta_reachability_gate_verdict', 'pass'],
    ['cta_capability_check_execution_status', 'executed'],
    ['cta_capability_evidence_result', 'confirmed'],
    ['cta_capability_gate_verdict', 'pass'],
  ].every(([field, expected]) => normalizeText(string(brief, field, problems)) === expected)
    && ['cta_reference_evidence_refs', 'cta_reachability_evidence_refs', 'cta_capability_evidence_refs']
      .every((field) => strings(brief, field, problems, { allowEmpty: true }).length > 0);
  for (const field of [
    'buyer_language_seeds', 'query_language_transformation_reason', 'product_link_evidence_level', 'visual_decision_assets',
    'cta_value_exchange', 'cta_response_expectation', 'cta_submission_method', 'cta_confidentiality_or_data_boundary',
    'cta_commitment_boundary', 'cta_buyer_visible_owner',
  ]) requireCanonicalMatch(records, field, problems);

  const seeds = strings(brief, 'buyer_language_seeds', problems);
  if (seeds.length < 2 || seeds.some((seed) => seed.trim().length < 8)) fail(problems, `${brief.source} buyer_language_seeds requires at least two concrete buyer phrases`);
  const transformationReason = requireMeaningfulString(brief, 'query_language_transformation_reason', problems, { minLength: 24 });
  const primaryQuery = string(brief, 'primary_query', problems);
  const task = parseDominantTaskContract(brief, problems);
  if (semanticOverlap(seeds.join(' '), `${primaryQuery} ${task.decisionObject}`).length < 2) fail(problems, `${brief.source} buyer_language_seeds must preserve the buyer query object or dominant decision task`);
  if (!/preserv|normaliz|translate|map|retain|buyer/i.test(transformationReason)
    || semanticOverlap(transformationReason, `${seeds.join(' ')} ${primaryQuery}`).length < 2) fail(problems, `${brief.source} query_language_transformation_reason must explain which buyer wording was preserved or normalized`);

  const level = normalizeText(string(brief, 'product_link_evidence_level', problems));
  if (!PRODUCT_LINK_EVIDENCE_LEVELS.has(level)) fail(problems, `${brief.source} product_link_evidence_level must be none, family-level, or sku-level`);
  const targets = strings(brief, 'internal_link_targets', problems, { allowEmpty: true });
  const parsedTargets = targets.map((row) => {
    const [role = '', url = '', anchor = ''] = row.split('|').map((part) => part.trim());
    return { role: normalizeText(role), url, anchor };
  });
  const targetRoles = parsedTargets.map((target) => target.role);
  if (level === 'none' && targetRoles.some((role) => role === 'product' || role === 'solution')) fail(problems, `${brief.source} product_link_evidence_level=none cannot link a product or solution target`);
  if (level === 'family-level' && targetRoles.includes('product')) fail(problems, `${brief.source} family-level evidence must link a solution/category target rather than a specific product target`);
  if (level === 'family-level' && !targetRoles.includes('solution')) fail(problems, `${brief.source} family-level evidence requires a solution target`);
  if (level === 'sku-level' && !targetRoles.includes('product')) fail(problems, `${brief.source} sku-level evidence requires a product target`);
  if (level === 'family-level') for (const target of parsedTargets.filter(({ role }) => role === 'solution')) {
    if (skuShapedUrl(target.url)) fail(problems, `${brief.source} family-level solution target cannot use a SKU-shaped product URL: ${target.url}`);
    if (/\b(?:sku|model|fits?|qualified|approved|recommended|production-ready)\b/i.test(target.anchor)) fail(problems, `${brief.source} family-level anchor cannot claim a specific model or evidenced fit: ${target.anchor}`);
  }
  if (level === 'sku-level') for (const target of parsedTargets.filter(({ role }) => role === 'product')) {
    if (!skuShapedUrl(target.url)) fail(problems, `${brief.source} sku-level product target requires a SKU/model-shaped product URL: ${target.url}`);
    if (!/\b(?:sku|model|[a-z]{1,8}-?\d{2,})\b/i.test(target.anchor)) fail(problems, `${brief.source} sku-level product anchor must name the specific SKU/model`);
  }
  if (level === 'sku-level') {
    const productRows = strings(brief, 'product_decision_map', problems, { allowEmpty: true });
    const hasConditionToSpecEvidence = productRows.some((row) => {
      const parts = row.split('|').map((part) => part.trim());
      return parts.length === 9 && parts[2].split(/\s*;\s*/).some((ref) => ref.includes('#'));
    });
    if (!hasConditionToSpecEvidence) fail(problems, `${brief.source} sku-level evidence requires condition-to-spec evidence_ref in product_decision_map`);
    if (evidenceScope === 'synthetic-fixture' && parsedTargets.some(({ anchor }) => /\b(?:production-qualified|production-ready|verified fit)\b/i.test(anchor))) fail(problems, `${brief.source} synthetic fixture cannot claim production sku-level qualification`);
  }

  const assetRows = strings(brief, 'visual_decision_assets', problems, { allowEmpty: true });
  if (!assetRows.length) fail(problems, `${brief.source} visual_decision_assets requires a decision asset or an explicit not-applicable row`);
  const allBodyImages = markdownImages(draft.body);
  const boundImageSources = new Set();
  let hasApplicableAsset = false;
  for (const row of assetRows) {
    const parts = row.split('|').map((part) => part.trim());
    if (parts.length !== 9 || parts.some((part) => part.length < 3)) {
      fail(problems, `${brief.source} visual_decision_assets requires exact asset_type|buyer_task_supported|claim_supported|evidence_ref|placement_after_section|caption|alt_intent|mobile_readability_requirement|status rows`);
      continue;
    }
    const [assetType, buyerTask, claim, evidenceRef, placement, caption, altIntent, mobile, status] = parts;
    if (!VISUAL_DECISION_ASSET_TYPES.has(normalizeText(assetType))) fail(problems, `${brief.source} visual_decision_assets uses unsupported asset_type ${assetType}`);
    if (!VISUAL_DECISION_ASSET_STATUSES.has(normalizeText(status))) fail(problems, `${brief.source} visual_decision_assets uses unsupported status ${status}`);
    const normalizedStatus = normalizeText(status);
    if (normalizedStatus !== 'not-applicable') hasApplicableAsset = true;
    if (!/mobile|320|viewport|responsive|stack|scroll/i.test(mobile)) fail(problems, `${brief.source} visual_decision_assets must declare a concrete mobile readability requirement`);
    const semanticAsset = ['decision-table', 'decision-list'].includes(normalizeText(assetType));
    if (semanticAsset && !new RegExp(`not-applicable-for-semantic-${normalizeText(assetType).replace('decision-', '')}`).test(normalizeText(altIntent))) {
      fail(problems, `${brief.source} semantic ${assetType} requires its exact not-applicable-for-semantic-${normalizeText(assetType).replace('decision-', '')} alt intent`);
    }
    if (normalizedStatus !== 'not-applicable') {
      validateLocalEvidenceRefs([evidenceRef], brief.source, 'visual_decision_assets evidence_ref', evidenceRoot, problems, { requireFragment: true, verifyFragment: true });
      let placementText = normalizeText(placement).replace(/\b(?:after|before|the|inside|section)\b/g, ' ');
      const h2Sections = h2SectionRanges(draft.body);
      const explicitFiveInputSection = /five input readiness|five decision blocks/.test(placementText)
        ? canonicalDecisionH2Sections(draft.body)
        : [];
      if (/five input readiness/.test(placementText)) placementText += ' five decision blocks first review';
      const scoredPlacementSections = explicitFiveInputSection.length
        ? explicitFiveInputSection.map((section) => ({ ...section, score: Number.MAX_SAFE_INTEGER }))
        : h2Sections
          .map((section) => ({ ...section, score: semanticOverlap(placementText, section.heading).length }))
          .filter((section) => section.score >= 2)
          .sort((left, right) => right.score - left.score);
      const topScore = scoredPlacementSections[0]?.score || 0;
      const placementSections = scoredPlacementSections.filter((section) => section.score === topScore);
      if (placementSections.length !== 1) fail(problems, `${brief.source} visual decision asset placement_after_section must resolve uniquely to the best-matching existing H2 section`);
      const placementSection = placementSections[0]?.markdown || '';
      if (semanticOverlap(`${buyerTask} ${claim}`, task.value).length < 2) fail(problems, `${brief.source} visual decision asset buyer task and claim must match the dominant task`);
      if (!semanticAsset && (normalizeText(altIntent).length < 12 || /not-applicable/i.test(altIntent))) fail(problems, `${brief.source} image-like visual decision asset requires meaningful alt intent`);
      if (normalizeText(assetType) === 'decision-table') {
        const tables = markdownTableBlocks(placementSection);
        const boundTables = tables.filter((table) => semanticOverlap(buyerTask, markdownPlainText(table)).length >= 1
          && semanticOverlap(claim, markdownPlainText(table)).length >= 2);
        const firstRoundInputs = strings(brief, 'first_round_inquiry_inputs', problems, { allowEmpty: true });
        let validDecisionBlocks = false;
        if (boundTables.length !== 1) {
          validDecisionBlocks = validateFiveDecisionBlocks(placementSection, firstRoundInputs, buyerTask, claim, draft.source, problems);
        }
        if (boundTables.length !== 1 && !validDecisionBlocks) fail(problems, `${draft.source} decision-table asset must be bound to exactly one semantic table or five valid decision blocks inside its declared H2 section`);
      } else if (normalizeText(assetType) === 'decision-list') {
        const listText = placementSection.split('\n').filter((line) => /^\s*(?:[-*+]\s+|\d+[.)]\s+)/.test(line)).join(' ');
        if (!listText || semanticOverlap(`${buyerTask} ${claim} ${caption}`, markdownPlainText(listText)).length < 2) {
          fail(problems, `${draft.source} decision-list asset must be bound to a visible list inside its declared H2 section that supports the buyer task and claim`);
        }
      } else if (normalizedStatus === 'required' && IMAGE_LIKE_VISUAL_DECISION_ASSET_TYPES.has(normalizeText(assetType))) {
        validateRequiredDecisionAssetImage({
          draft, assetType, buyerTask, claim, altIntent, placementSection,
          allBodyImages, boundImageSources, problems,
        });
      } else if (placementSection && semanticOverlap(`${caption} ${altIntent}`, markdownPlainText(placementSection)).length < 2) {
        fail(problems, `${draft.source} image-like visual decision asset caption or alt intent must be represented inside its declared H2 section`);
      }
      if (placementSection && semanticOverlap(caption, markdownPlainText(placementSection)).length < 2) fail(problems, `${draft.source} visual decision asset caption/task must be represented inside its declared H2 section`);
    } else if (!/not-applicable|no visual|self-contained|stage/i.test(`${buyerTask} ${claim} ${evidenceRef} ${placement} ${caption}`)) {
      fail(problems, `${brief.source} not-applicable visual decision asset requires an explicit stage reason`);
    }
    if (semanticOverlap(caption, markdownPlainText(draft.body)).length < 2) fail(problems, `${draft.source} visual decision asset caption/task must be represented in the publishable body`);
  }
  for (const image of allBodyImages) {
    const sourceKey = canonicalMarkdownImageSource(image.source);
    if (!boundImageSources.has(sourceKey)) {
      fail(problems, `${draft.source} Markdown image must be declared by and bound to exactly one required image-like visual_decision_assets row inside that row's declared H2 section: ${image.raw}`);
    }
  }

  const buyerFields = [
    ['cta_value_exchange', 24], ['cta_response_expectation', 18], ['cta_submission_method', 18],
    ['cta_confidentiality_or_data_boundary', 24], ['cta_commitment_boundary', 18], ['cta_buyer_visible_owner', 4],
  ];
  const interaction = normalizeText(string(brief, 'cta_interaction_type', problems));
  const selfServe = interaction === 'inline-no-input' || interaction === 'local-tool';
  const stage = normalizeText(string(brief, 'stage', problems));
  const ctaSections = ctaSectionsForStage(draft.body, stage, selfServe);
  const ctaSection = primaryCtaSectionForStage(draft.body, stage, selfServe);
  if (!ctaSection) fail(problems, `${draft.source} publishable body requires a locatable buyer-visible CTA or self-service section`);
  for (const [field, minLength] of buyerFields) {
    const value = requireMeaningfulString(brief, field, problems, { minLength: selfServe && field !== 'cta_value_exchange' ? 4 : minLength });
    if (semanticOverlap(value, markdownPlainText(ctaSection)).length < (selfServe ? 1 : 2)) fail(problems, `${draft.source} publishable body must visibly communicate ${field} within the actual CTA section`);
  }
  const response = string(brief, 'cta_response_expectation', problems);
  if (/\b(?:within|in)\s+\d+\s*(?:hours?|business days?|days?)\b|\bsame[- ]day\b/i.test(response) && !/unverified|not evidenced|confirm/i.test(response)) fail(problems, `${brief.source} cta_response_expectation cannot fabricate an SLA without evidence`);
  if (selfServe && !/no (?:human )?response|self[- ]service|immediate self-check|not-applicable/i.test(response)) fail(problems, `${brief.source} self-service CTA must not imply an unproved human response`);
  const destination = string(brief, 'cta_destination', problems);
  if (!selfServe && destination !== 'not-applicable' && !primaryRouteVerified) {
    fail(problems, `${brief.source} unverified primary CTA route must use cta_destination=not-applicable until endpoint-specific reference, reachability, and capability evidence all pass`);
  }
  if (!selfServe && destination !== 'not-applicable' && !ctaSection.includes(destination)) fail(problems, `${draft.source} actual CTA section must use the canonical visible CTA channel`);
  if (!selfServe) {
    const fallback = string(brief, 'cta_fallback_message_template', problems);
    const visibleCtaText = markdownPlainText(ctaSection);
    const visibleCta = normalizeText(visibleCtaText);
    const normalizedFallback = normalizeText(fallback);
    if (!visibleCta.includes(normalizedFallback)) fail(problems, `${draft.source} actual CTA section must display the exact copyable fallback message instead of hiding it only in frontmatter`);
    const fallbackMarker = fallbackInstructionMarker(visibleCtaText);
    if (fallbackMarker < 0) fail(problems, `${draft.source} buyer-visible fallback requires an explicit action for an unavailable primary route`);
    const fallbackText = fallbackMarker < 0 ? visibleCtaText : visibleCtaText.slice(fallbackMarker);
    const rawFallbackMarker = fallbackInstructionMarker(ctaSection);
    const fallbackMarkdown = rawFallbackMarker < 0 ? ctaSection : ctaSection.slice(rawFallbackMarker);
    if (semanticOverlap(string(brief, 'cta_owner', problems), fallbackText).length < 1) fail(problems, `${draft.source} buyer-visible fallback must identify the accountable external route owner`);

    if (fallbackContract?.status === 'verified') {
      const endpointVisible = normalizeText(fallbackMarkdown).includes(normalizeText(fallbackContract.endpoint));
      if (!endpointVisible) fail(problems, `${draft.source} verified fallback branch must display the exact contract endpoint ${fallbackContract.endpoint}`);
      if (!/(?:verified|approved).{0,70}(?:channel|route|form|portal|endpoint|email)|(?:channel|route|form|portal|endpoint|email).{0,70}(?:verified|approved)/i.test(fallbackText)) fail(problems, `${draft.source} verified fallback branch must identify the concrete route as verified or approved`);
    } else if (fallbackContract?.status === 'unverified-unavailable') {
      if (!hasExplicitUnavailableRouteDisclosure(visibleCtaText)) fail(problems, `${draft.source} unverified fallback branch must explicitly state that no verified fallback route is available`);
      if (!/do not send|do not submit/i.test(fallbackText)) fail(problems, `${draft.source} unverified fallback branch must tell the buyer not to send the packet`);
      if (!/(?:save|keep|retain).{0,40}(?:packet|copy|file).{0,30}(?:local|locally)|(?:save|keep|retain).{0,20}(?:local|locally)/i.test(fallbackText)) fail(problems, `${draft.source} unverified fallback branch must tell the buyer to save the packet locally`);
      if (!hasExistingApprovedSupplierContactProcess(fallbackText)) fail(problems, `${draft.source} unverified fallback branch must route through the buyer's existing approved supplier-contact process`);
      if (!hasVerifiedRouteMetadataRequest(fallbackText)) fail(problems, `${draft.source} unverified fallback branch must tell the buyer to request a verified route`);
    } else if (fallbackContract?.status === 'not-applicable') {
      fail(problems, `${draft.source} input-collecting CTA cannot declare cta_fallback_route_contract=not-applicable while rendering fallback copy`);
    }
  }
  if (!selfServe && !primaryRouteVerified) for (const section of ctaSections) {
    const fallbackMarker = fallbackInstructionMarker(section);
    const primaryOnly = fallbackMarker >= 0 ? section.slice(0, fallbackMarker) : section;
    const concreteEndpoints = markdownPlainText(primaryOnly).match(/(?:https:\/\/|mailto:)?[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|https:\/\/[^\s)\]}>]+/gi) || [];
    if (concreteEndpoints.length) {
      fail(problems, `${draft.source} unverified primary CTA route must not directly link or instruct through, or expose, any concrete URL or email endpoint: ${[...new Set(concreteEndpoints)].join(', ')}`);
    } else if (sectionHasDirectUnverifiedEndpointInstruction(primaryOnly)) {
      fail(problems, `${draft.source} unverified primary CTA route must not directly link or instruct the buyer to transmit, deliver, provide, dispatch, post, hand over, submit, send, email, share, upload, contact, forward, or transfer through a concrete endpoint`);
    }
  }
  validateAllBuyerVisibleCtaRouteSafety(ctaSections, fallbackContract, draft, problems);
  if (!/confidential|credential|personal data|secure|do not submit|do not send/i.test(string(brief, 'cta_confidentiality_or_data_boundary', problems))) fail(problems, `${brief.source} CTA confidentiality boundary must state what not to submit or the secure route`);
  const automaticCommercialCommitment = (value) => String(value).split(/(?<=[.!?。！？])\s+|\n+/u).some((sentence) => {
    const hasSubmission = /\b(?:submitt(?:ing|ed|al)|send(?:ing)?|request(?:ing)?|complet(?:ing|ion))\b/i.test(sentence);
    const hasAutomaticLink = /\b(?:automatically|immediately|guarantees?|creates?|constitutes?|equals?|means?|confirms?|accepts?)\b/i.test(sentence);
    const hasOutcome = /\b(?:quote|quotation|purchase order|order acceptance|supplier award|delivery promise|sales acceptance)\b/i.test(sentence);
    const hasNegation = /\b(?:does not|do not|cannot|will not|is not|no)\b/i.test(sentence);
    return hasSubmission && hasAutomaticLink && hasOutcome && !hasNegation;
  });
  if (automaticCommercialCommitment(string(brief, 'cta_commitment_boundary', problems)) || automaticCommercialCommitment(markdownPlainText(ctaSection))) {
    fail(problems, `${draft.source} CTA must not claim that submission automatically creates a quote, order, supplier award, delivery promise, or sales acceptance`);
  }
  if (!selfServe && semanticOverlap(string(brief, 'cta_buyer_visible_owner', problems), `${string(brief, 'cta_to_role', problems)} ${string(brief, 'cta_owner', problems)}`).length < 1) fail(problems, `${brief.source} cta_buyer_visible_owner must match the receiving role or accountable owner`);
  const controlledBody = normalizeText(markdownPlainText(draft.body)).replace(/[\s_-]+/g, ' ');
  if (BUYER_VISIBLE_INTERNAL_CONTROL_PATTERN.test(controlledBody)) fail(problems, `${draft.source} publishable body leaks internal workflow/control terminology into buyer-visible editorial copy`);
  validateV14StageBodyIsolation(brief, draft, problems);

  const slug = normalizeText(string(draft, 'slug', problems)).replace(/[-_]+/g, ' ');
  if (semanticOverlap(slug, primaryQuery).length < 3 || semanticOverlap(slug, `${task.decisionObject} ${task.expectedOutput}`).length < 2) fail(problems, `${draft.source} slug must preserve primary-query, decision-object, and observable-output parity`);
  const slugStage = normalizeText(string(brief, 'stage', problems));
  const slugStageCues = new Map([
    ['learn', /\b(?:guide|basics?|explained|how|what|overview|principles?|concepts?|understand)\b/i],
    ['troubleshoot', /\b(?:troubleshoot|diagnos(?:e|is|tic)|root cause|failure|fix|repair|fault)\b/i],
    ['compare', /\b(?:compare|comparison|versus|vs|selection|shortlist|evaluate|choose|decision matrix)\b/i],
    ['validate', /\b(?:validat(?:e|ion)|verify|readiness|review|test|evidence|candidate|acceptance)\b/i],
    ['buy', /\b(?:buy|purchase|quote|quotation|rfq|pricing|price|order|supplier|moq|lead time)\b/i],
  ]);
  if (!slugStageCues.get(slugStage)?.test(slug)) fail(problems, `${draft.source} slug does not express the declared ${slugStage} stage or its dominant action`);
  const competingSlugStages = [...slugStageCues].filter(([candidate, pattern]) => candidate !== slugStage && pattern.test(slug)).map(([candidate]) => candidate);
  if (competingSlugStages.length) fail(problems, `${draft.source} slug mixes declared ${slugStage} cues with competing stage cues: ${competingSlugStages.join(', ')}`);
  if (slugStage !== 'buy' && commercialClassification(slug).commercial) fail(problems, `${draft.source} non-Buy slug must not use transactional modifiers`);

  const requiredReviewPasses = [
    'direct_answer_six_slot_verdict', 'publishable_body_boundary_verdict', 'stage_intake_contract_verdict',
    'title_slug_stage_parity_verdict', 'buyer_visible_editorial_language_verdict', 'internal_control_term_leakage_verdict',
    'cta_value_exchange_verdict', 'product_link_claim_parity_verdict',
  ];
  for (const field of requiredReviewPasses) if (normalizeText(string(review, field, problems)) !== PASS) fail(problems, `${review.source} ${field} must be pass and is a fatal article-structure gate`);
  const visualVerdict = normalizeText(string(review, 'visual_decision_assets_verdict', problems));
  const mobileGate = normalizeText(string(review, 'mobile_visual_gate_verdict', problems));
  const productionReady = normalizeText(string(review, 'production_readiness', problems)) === 'ready';
  if (hasApplicableAsset && productionReady && (visualVerdict !== PASS || mobileGate !== PASS)) fail(problems, `${review.source} production-ready applicable visual assets require visual_decision_assets_verdict=pass and mobile_visual_gate_verdict=pass`);
  if (hasApplicableAsset && !productionReady && !['pass', 'block'].includes(visualVerdict)) fail(problems, `${review.source} non-ready applicable visual assets require visual_decision_assets_verdict=pass or block`);
  if (!hasApplicableAsset && !['pass', 'not-applicable'].includes(visualVerdict)) fail(problems, `${review.source} visual_decision_assets_verdict must be pass or not-applicable`);
  return fallbackContract;
}


function normalizeDisplayComparable(value) {
  return normalizeText(value)
    .replace(/[×✕]/g, 'x')
    .replace(/[–—−]/g, '-')
    .replace(/°\s*/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function numericTokens(value) {
  return String(value).match(/\d+(?:\.\d+)?/g) || [];
}

function validateFirstRoundInputSpecifications({ records, brief, draft, publish, evidenceRoot, problems }) {
  const inputs = strings(brief, 'first_round_inquiry_inputs', problems, { allowEmpty: true });
  const specifications = strings(brief, 'first_round_input_specifications', problems, { allowEmpty: true });
  const applicable = normalizeText(string(brief, 'cta_input_collection_applicability', problems)) === 'applicable';
  if (inputs.length !== specifications.length || (applicable && !inputs.length)) {
    fail(problems, `${brief.source} first_round_input_specifications must contain exactly one row for every first_round_inquiry_inputs item when input collection is applicable`);
  }
  const seenInputs = new Set();
  for (let index = 0; index < specifications.length; index += 1) {
    const row = specifications[index];
    const parts = row.split('|').map((part) => part.trim());
    if (parts.length !== 6 || parts.some((part) => !part)) {
      fail(problems, `${brief.source} first_round_input_specifications requires exact input|why-needed|accepted-unit-or-format|example|required-or-conditional|confidentiality-boundary rows`);
      continue;
    }
    const [input, whyNeeded, unitOrFormat, example, requirement, boundary] = parts;
    meaningfulScalar(input, brief.source, 'first_round_input_specifications input', problems, { minLength: 8 });
    meaningfulScalar(whyNeeded, brief.source, 'first_round_input_specifications why-needed', problems, { minLength: 16 });
    meaningfulScalar(unitOrFormat, brief.source, 'first_round_input_specifications accepted-unit-or-format', problems, { minLength: 6 });
    meaningfulScalar(example, brief.source, 'first_round_input_specifications example', problems, { minLength: 6 });
    meaningfulScalar(boundary, brief.source, 'first_round_input_specifications confidentiality-boundary', problems, { minLength: 16 });
    const normalizedInput = normalizeText(input);
    if (seenInputs.has(normalizedInput)) fail(problems, `${brief.source} first_round_input_specifications contains duplicate input ${input}`);
    seenInputs.add(normalizedInput);
    if (normalizeText(inputs[index] || '') !== normalizedInput) fail(problems, `${brief.source} first_round_input_specifications input order must exactly follow first_round_inquiry_inputs`);
    if (!/\b(?:kg|kilograms?|lb|pounds?|mm|millimeters?|inch|inches|volts?|amps?|percent|%|iso|etrto|duration|format|drawing|dimensions?|range|continuous|peak|nominal)\b/i.test(unitOrFormat)) {
      fail(problems, `${brief.source} first_round_input_specifications accepted-unit-or-format must name a concrete unit or format for ${input}`);
    }
    if (!numericTokens(example).length && semanticTokens(example).length < 3) fail(problems, `${brief.source} first_round_input_specifications example must be concrete for ${input}`);
    if (!/^(?:required|conditional(?:[- ][a-z0-9 ]+)?)$/i.test(requirement)) fail(problems, `${brief.source} first_round_input_specifications required-or-conditional must be required or a concrete conditional rule`);
    if (!/\b(?:do not|remove|redact|secure|approved|confidential|personal|credential|identifier|controlled|private|without[^.;]*addresses|without[^.;]*gps)\b/i.test(boundary)) {
      fail(problems, `${brief.source} first_round_input_specifications confidentiality-boundary must state an explicit safe-data boundary for ${input}`);
    }
  }

  if (!applicable) return;
  const interaction = normalizeText(string(brief, 'cta_interaction_type', problems));
  const selfServe = interaction === 'inline-no-input' || interaction === 'local-tool';
  const ctaSections = ctaSectionsForStage(draft.body, normalizeText(string(brief, 'stage', problems)), selfServe);
  const ctaSection = primaryCtaSectionForStage(draft.body, normalizeText(string(brief, 'stage', problems)), selfServe);
  const decisionAsset = markdownSectionByHeading(draft.body, /assemble the readiness worksheet locally|complete the readiness worksheet|readiness worksheet/i)
    || markdownSectionByHeading(draft.body, /five[- ]input readiness check|readiness checklist|decision map/i)
    || ctaSection;
  const visible = normalizeDisplayComparable(markdownPlainText(decisionAsset));
  const decisionRows = markdownTableBlocks(decisionAsset)
    .flatMap((table) => {
      const lines = table.split('\n');
      return lines.slice(2).map((line) => ({
        cells: parseMarkdownTableCells(line),
        visible: normalizeDisplayComparable(markdownPlainText(line)),
      }));
    });
  for (const row of specifications) {
    const [input = '', , unitOrFormat = '', example = ''] = row.split('|').map((part) => part.trim());
    if (!visible.includes(normalizeDisplayComparable(input))) fail(problems, `${draft.source} CTA section must visibly show input specification row ${input}`);
    const inputComparable = normalizeDisplayComparable(input);
    const matchingRows = decisionRows.filter(({ visible: rowVisible }) => rowVisible.includes(inputComparable));
    if (matchingRows.length !== 1) {
      fail(problems, `${draft.source} decision asset must bind ${input} to exactly one matching input row`);
      continue;
    }
    const rowVisible = matchingRows[0].visible;
    const unitTokens = semanticTokens(unitOrFormat).filter((token) => token.length >= 4);
    if (unitTokens.length && !unitTokens.some((token) => rowVisible.includes(token))) fail(problems, `${draft.source} decision asset matching input row must visibly show an accepted unit or format for ${input}`);
    const numbers = numericTokens(example);
    if (numbers.length && !numbers.every((number) => rowVisible.includes(number))) fail(problems, `${draft.source} decision asset matching input row must visibly show the concrete example for ${input}`);
  }
}

function validateBuyerVisibleCapabilityProofs({ brief, draft, publish, evidenceScope, evidenceRoot, problems }) {
  const proofs = strings(brief, 'cta_buyer_visible_capability_proofs', problems, { allowEmpty: true });
  const interaction = normalizeText(string(brief, 'cta_interaction_type', problems));
  const collecting = ['input-collecting', 'human-handoff', 'commercial'].includes(interaction)
    || normalizeText(string(brief, 'cta_input_collection_applicability', problems)) === 'applicable';
  if (collecting && !proofs.length) fail(problems, `${brief.source} collecting, handoff, or commercial CTA requires at least one buyer-visible capability proof`);
  const task = parseDominantTaskContract(brief, problems);
  const ctaValue = string(brief, 'cta_value_exchange', problems);
  const selfServe = interaction === 'inline-no-input' || interaction === 'local-tool';
  const ctaSections = ctaSectionsForStage(draft.body, normalizeText(string(brief, 'stage', problems)), selfServe);
  const ctaSection = primaryCtaSectionForStage(draft.body, normalizeText(string(brief, 'stage', problems)), selfServe);
  const visible = markdownPlainText(ctaSection);
  let applicableProofs = 0;
  for (const row of proofs) {
    const parts = row.split('|').map((part) => part.trim());
    if (parts.length !== 6 || parts.some((part) => !part)) {
      fail(problems, `${brief.source} cta_buyer_visible_capability_proofs requires exact proof-type|buyer-task-supported|claim-or-boundary|evidence-ref|buyer-visible-copy|required-or-not-applicable rows`);
      continue;
    }
    const [proofType, buyerTask, claim, evidenceRef, buyerCopy, requirement] = parts;
    for (const [field, value, minLength] of [
      ['proof-type', proofType, 4], ['buyer-task-supported', buyerTask, 12], ['claim-or-boundary', claim, 24], ['buyer-visible-copy', buyerCopy, 24],
    ]) meaningfulScalar(value, brief.source, `cta_buyer_visible_capability_proofs ${field}`, problems, { minLength });
    if (!/^(?:required|not-applicable)$/i.test(requirement)) fail(problems, `${brief.source} capability proof required-or-not-applicable must be required or not-applicable`);
    if (/^not-applicable$/i.test(requirement)) continue;
    applicableProofs += 1;
    if (semanticOverlap(buyerTask, `${task.value} ${ctaValue}`).length < 2) fail(problems, `${brief.source} capability proof buyer task must match the dominant task and CTA value exchange`);
    if (!/\b(?:review|compare|return|show|demonstrate|method|sample|artifact|test|check|result|assumption|gap|evidence|boundary|owner)\b/i.test(`${claim} ${buyerCopy}`)) {
      fail(problems, `${brief.source} capability proof cannot be a generic brand slogan; it must name a review method, artifact, sample, output, or boundary`);
    }
    const resolved = validateLocalEvidenceRefs([evidenceRef], brief.source, 'cta_buyer_visible_capability_proofs evidence-ref', evidenceRoot, problems, { requireFragment: true, verifyFragment: true });
    if (evidenceScope === 'production') rejectSyntheticEvidenceFiles(resolved, brief.source, 'cta_buyer_visible_capability_proofs evidence-ref', problems);
    const section = markdownSectionBody(parseArticleMarkdownFrontMatter(readFileSync(resolve(evidenceRoot, splitLocalRef(evidenceRef).pathPart), 'utf8'), { source: evidenceRef }).body, splitLocalRef(evidenceRef).fragment);
    if (section && semanticOverlap(`${claim} ${buyerTask}`, markdownPlainText(section)).length < 2) fail(problems, `${brief.source} capability proof evidence must locally support the claimed buyer task or boundary`);
    const buyerCopyTokenCount = new Set(semanticTokens(buyerCopy)).size;
    const requiredBuyerCopyOverlap = Math.min(buyerCopyTokenCount, Math.max(4, Math.ceil(buyerCopyTokenCount * 0.55)));
    if (semanticOverlap(buyerCopy, visible).length < requiredBuyerCopyOverlap) fail(problems, `${draft.source} buyer-visible capability proof copy must be materially present in the actual CTA section`);
  }
  if (collecting && applicableProofs < 1) fail(problems, `${brief.source} collecting, handoff, or commercial CTA requires at least one applicable capability proof`);
}

function contentTypeFamilies(value) {
  const normalized = normalizeText(value);
  return CONTENT_TYPE_FAMILY_PATTERNS.filter(([, pattern]) => pattern.test(normalized)).map(([family]) => family);
}

function contentTypeFamily(value) {
  const matches = contentTypeFamilies(value);
  return matches.length === 1 ? matches[0] : '';
}

function draftImplementsContentType(family, body) {
  const raw = String(body || '');
  const plain = markdownPlainText(raw);
  const h2s = h2SectionRanges(raw).map((section) => normalizeText(section.heading));
  const tables = markdownTableBlocks(raw);
  if (family === 'checklist') {
    const checkboxCount = (raw.match(/\[[ xX]\]/g) || []).length;
    const checklistSection = markdownSectionByHeading(raw, /checklist|check list|readiness check|audit check|inspection check/);
    const structuredChecklistItems = checklistSection
      ? (checklistSection.match(/^###\s+.+$/gm) || []).length >= 3
        && (checklistSection.match(/^[-*]\s+(?:Record|Required|Check|Decision effect|If missing):/gmi) || []).length >= 6
      : false;
    const checklistHeading = h2s.some((heading) => /\b(?:checklist|check list|readiness check|audit check|inspection check)\b/i.test(heading));
    const decisionBlockChecklist = (raw.match(/^###\s+(?:Establish|Define|Describe|Separate|Summarize)\b/gmi) || []).length >= 5;
    return (checklistHeading || decisionBlockChecklist) && (checkboxCount >= 3 || structuredChecklistItems || decisionBlockChecklist || /\b(?:complete|missing|required)\b/i.test(plain) && tables.length >= 1);
  }
  if (family === 'comparison') {
    const comparisonHeading = h2s.some((heading) => /\b(?:compare|comparison|versus|vs\.?|matrix|candidate|selection|shortlist)\b/i.test(heading));
    const comparisonTable = tables.some((table) => /\b(?:candidate|option|criterion|criteria|comparison|decision|stop)\b/i.test(markdownPlainText(table)));
    return comparisonHeading && comparisonTable;
  }
  if (family === 'calculator') {
    const calculatorHeading = h2s.some((heading) => /\b(?:calculator|estimate|calculation|sizing|roi|cost model)\b/i.test(heading));
    const inputOutput = /\binputs?\b/i.test(plain) && /\b(?:output|result|estimate|calculation)\b/i.test(plain);
    const formulaShape = /(?:=|×|÷|\*|\/).{0,80}(?:unit|kg|mm|volt|amp|percent|%|cost|price)/i.test(raw) || tables.length >= 1;
    return calculatorHeading && inputOutput && formulaShape;
  }
  if (family === 'diagnostic') {
    const diagnosticHeading = h2s.some((heading) => /\b(?:diagnos|troubleshoot|root cause|fault|failure|symptom)\b/i.test(heading));
    const branchShape = /\b(?:if|then|otherwise|cause|check|isolate|stop|next check)\b/i.test(plain);
    const steps = (raw.match(/^\s*(?:\d+\.|[-*])\s+/gm) || []).length >= 3;
    return diagnosticHeading && branchShape && steps;
  }
  if (family === 'guide') {
    const guideHeading = h2s.some((heading) => /\b(?:guide|how to|steps?|process|workflow|prepare|implement)\b/i.test(heading));
    const stepShape = (raw.match(/^\s*\d+\.\s+/gm) || []).length >= 3 || h2s.length >= 3;
    return guideHeading && stepShape;
  }
  if (family === 'case-study') {
    const headings = h2s.join(' ');
    const context = /\b(?:challenge|context|problem|starting point)\b/i.test(headings);
    const action = /\b(?:approach|implementation|method|what changed|solution)\b/i.test(headings);
    const result = /\b(?:result|outcome|lesson|finding|what happened)\b/i.test(headings);
    return context && action && result;
  }
  if (family === 'product-landing') {
    const landingHeading = h2s.some((heading) => /\b(?:product|category|solution|models?|portfolio|applications?)\b/i.test(heading));
    const decisionShape = /\b(?:specification|features?|applications?|use cases?|models?|options?|request|contact)\b/i.test(plain);
    return landingHeading && decisionShape && (tables.length >= 1 || /https:\/\//i.test(raw));
  }
  return false;
}


function normalizedQuestion(value) {
  return securityLexicalText(value).replace(/[^\p{L}\p{N}\s]/gu, ' ').replace(/\s+/g, ' ').trim();
}

function questionsMateriallyOverlap(left, right) {
  const a = normalizedQuestion(left);
  const b = normalizedQuestion(right);
  if (!a || !b) return false;
  if (a === b || a.includes(b) || b.includes(a)) return true;
  const leftTokens = new Set(semanticTokens(a));
  const rightTokens = new Set(semanticTokens(b));
  const denominator = Math.min(leftTokens.size, rightTokens.size);
  return denominator >= 3 && semanticOverlap(a, b).length / denominator >= 0.75;
}

function validateIntentClosureContracts(records, brief, problems) {
  for (const field of ['in_scope_questions', 'out_of_scope_questions', 'intent_completion_test', 'secondary_intent_contracts']) {
    requireCanonicalMatch(records, field, problems, field, Array.isArray(brief.attributes[field]) ? 'exact-sequence' : 'exact-scalar');
  }
  const inScope = strings(brief, 'in_scope_questions', problems);
  const outOfScope = strings(brief, 'out_of_scope_questions', problems);
  for (const included of inScope) for (const excluded of outOfScope) {
    if (questionsMateriallyOverlap(included, excluded)) fail(problems, `${brief.source} in_scope_questions and out_of_scope_questions materially overlap: ${included} <> ${excluded}`);
  }
  const completion = requireMeaningfulString(brief, 'intent_completion_test', problems, { minLength: 24 });
  const stage = normalizeText(string(brief, 'stage', problems));
  const canonicalCommitment = normalizeText(string(brief, 'commercial_commitment', problems));
  const dominantIntent = string(brief, 'dominant_search_intent', problems);
  const primaryQuery = string(brief, 'primary_query', problems);
  const dominantTask = string(brief, 'dominant_task_contract', problems);
  if (stage !== 'buy' && commercialClassification(completion).commercial) {
    fail(problems, `${brief.source} non-Buy intent_completion_test must not end in quote, RFQ, order, supplier nomination, supplier award, or another commercial commitment`);
  }

  const supporting = strings(brief, 'supporting_query_variants', problems, { allowEmpty: true });
  const rows = strings(brief, 'secondary_intent_contracts', problems, { allowEmpty: supporting.length === 0 });
  const seen = new Set();
  for (const row of rows) {
    const parts = row.split('|').map((part) => part.trim());
    if (parts.length !== 6 || parts.some((part) => !part)) {
      fail(problems, `${brief.source} secondary_intent_contracts row must use supporting-query|buyer-task|stage|commercial-commitment|owner|supports-or-delegated: ${row}`);
      continue;
    }
    const [query, task, rowStage, commitment, owner, relation] = parts;
    const key = normalizeText(query);
    const normalizedStage = normalizeText(rowStage);
    const normalizedCommitment = normalizeText(commitment);
    const normalizedOwner = normalizeText(owner);
    const normalizedRelation = normalizeText(relation);
    if (seen.has(key)) fail(problems, `${brief.source} secondary_intent_contracts contains duplicate supporting query: ${query}`);
    seen.add(key);
    meaningfulScalar(task, brief.source, 'secondary_intent_contracts buyer-task', problems, { minLength: 8 });
    meaningfulScalar(owner, brief.source, 'secondary_intent_contracts owner', problems, { minLength: 4 });
    if (!DECISION_STAGES.has(normalizedStage)) fail(problems, `${brief.source} secondary_intent_contracts stage must use learn|compare|validate|buy|troubleshoot: ${rowStage}`);
    else if (normalizedStage !== stage) fail(problems, `${brief.source} secondary_intent_contracts stage must exactly match the canonical article stage and cannot expand it: ${row}`);
    if (!COMMERCIAL_COMMITMENTS.has(normalizedCommitment)) fail(problems, `${brief.source} secondary_intent_contracts commercial-commitment must use the closed enum none|soft|commercial: ${commitment}`);
    else if (normalizedCommitment !== canonicalCommitment) fail(problems, `${brief.source} secondary_intent_contracts commercial commitment cannot expand beyond the canonical article commitment: ${row}`);
    if (!['supports', 'delegated'].includes(normalizedRelation)) fail(problems, `${brief.source} secondary_intent_contracts relation must be supports or delegated: ${relation}`);
    if (normalizedRelation === 'supports' && normalizedOwner !== 'this-article') fail(problems, `${brief.source} secondary_intent_contracts supports relation requires owner=this-article: ${row}`);
    if (normalizedRelation === 'delegated' && normalizedOwner === 'this-article') fail(problems, `${brief.source} secondary_intent_contracts delegated relation requires an owner different from this-article: ${row}`);
    if (semanticOverlap(query, `${primaryQuery} ${dominantIntent}`).length < 2) fail(problems, `${brief.source} secondary intent query must remain semantically related to the dominant intent and primary query: ${row}`);
    if (semanticOverlap(task, `${dominantIntent} ${dominantTask}`).length < 2) fail(problems, `${brief.source} secondary intent task must remain semantically related to the dominant intent and dominant task contract: ${row}`);
    if (normalizedStage !== 'buy' && commercialClassification(`${task} ${commitment}`).terminal) fail(problems, `${brief.source} non-Buy secondary intent must not promise a commercial terminal action: ${row}`);
  }
  if (!sameNormalizedSet([...seen], supporting) || seen.size !== supporting.length) fail(problems, `${brief.source} secondary_intent_contracts must map supporting_query_variants one-to-one`);
}

function validateFaqContract(records, brief, problems) {
  for (const field of ['faq_applicability', 'faq_trigger_type', 'faq_trigger_evidence_refs', 'faq_absence_reason', 'faq_items', 'faq_decision_verdict']) {
    requireCanonicalMatch(records, field, problems, field, Array.isArray(brief.attributes[field]) ? 'exact-sequence' : 'exact-scalar');
  }
  const applicability = normalizeText(string(brief, 'faq_applicability', problems));
  const trigger = normalizeText(string(brief, 'faq_trigger_type', problems));
  const refs = strings(brief, 'faq_trigger_evidence_refs', problems, { allowEmpty: true });
  const items = strings(brief, 'faq_items', problems, { allowEmpty: true });
  const reason = string(brief, 'faq_absence_reason', problems);
  const allowedTriggers = ['dated-serp-pattern', 'documented-buyer-objection', 'documented-buyer-uncertainty', 'none'];
  if (!['applicable', 'not-applicable'].includes(applicability)) fail(problems, `${brief.source} faq_applicability must be applicable or not-applicable`);
  if (!allowedTriggers.includes(trigger)) fail(problems, `${brief.source} faq_trigger_type must use dated-serp-pattern|documented-buyer-objection|documented-buyer-uncertainty|none`);
  if (normalizeText(string(brief, 'faq_decision_verdict', problems)) !== 'pass') fail(problems, `${brief.source} faq_decision_verdict must be pass`);
  if (applicability === 'applicable') {
    if (trigger === 'none' || !refs.length || !items.length) fail(problems, `${brief.source} applicable FAQ requires a concrete trigger, evidence refs, and FAQ items`);
    if (normalizeText(reason) !== 'not-applicable') fail(problems, `${brief.source} applicable FAQ requires faq_absence_reason=not-applicable`);
    for (const item of items) {
      const parts = item.split('|').map((part) => part.trim());
      if (parts.length !== 5 || parts.some((part) => !part)) {
        fail(problems, `${brief.source} faq_items row must use question|buyer_job|objection_or_uncertainty|evidence_ref_or_explicit_inferred_boundary|article_owned_answer: ${item}`);
        continue;
      }
      const [question, buyerJob, uncertainty, evidenceBoundary, answer] = parts;
      meaningfulScalar(question, brief.source, 'faq_items question', problems, { minLength: 8 });
      meaningfulScalar(buyerJob, brief.source, 'faq_items buyer_job', problems, { minLength: 8 });
      meaningfulScalar(uncertainty, brief.source, 'faq_items objection_or_uncertainty', problems, { minLength: 8 });
      meaningfulScalar(evidenceBoundary, brief.source, 'faq_items evidence_ref_or_explicit_inferred_boundary', problems, { minLength: 8 });
      meaningfulScalar(answer, brief.source, 'faq_items article_owned_answer', problems, { minLength: 12 });
      if (commercialClassification(answer).terminal && normalizeText(string(brief, 'stage', problems)) !== 'buy') fail(problems, `${brief.source} FAQ must not expand a non-Buy article into a commercial terminal action: ${item}`);
    }
  } else {
    if (trigger !== 'none' || refs.length || items.length) fail(problems, `${brief.source} not-applicable FAQ requires trigger=none and empty evidence refs/items`);
    meaningfulScalar(reason, brief.source, 'faq_absence_reason', problems, { minLength: 20 });
    if (normalizeText(reason) === 'not-applicable') fail(problems, `${brief.source} not-applicable FAQ requires a specific absence reason`);
  }
}

function parseTerminalActionContract(record, problems) {
  const value = string(record, 'terminal_action_contract', problems);
  const parts = value.split('|').map((part) => part.trim());
  if (parts.length !== 5 || parts.some((part) => !part)) {
    fail(problems, `${record.source} terminal_action_contract must use action|decision-object|observable-output|stage|commercial-commitment`);
    return ['', '', '', '', ''];
  }
  const [action, decisionObject, expectedOutput, stage, commitment] = parts;
  return [stage, decisionObject, expectedOutput, action, commitment];
}

function collectCandidateDecisionSurfaces(record) {
  const fields = new Set(['stage_primary_outcome', 'intent_completion_test', 'direct_answer_expected_output_or_route', 'cta_expected_output', 'buyer_visible_cta_inventory', 'cta_transmission_action_inventory', 'cta_buyer_visible_capability_proofs', 'role_handoff_contracts', 'cta_receiving_task', 'capability_proof_evidence_refs', 'cta_capability_evidence_refs', 'handoff_evidence_refs']);
  const out = [];
  for (const [field, value] of Object.entries(record.attributes)) {
    if (fields.has(field) || /(?:observable_output|target_task|receiving_task|expected_output|capability_proof|handoff|endpoint)/i.test(field)) out.push([field, value]);
  }
  return out;
}

function validateRoundDecisionGateContract(records, brief, problems) {
  requireCanonicalMatch(records, 'first_round_expected_output', problems, 'first_round_expected_output', 'exact-raw-scalar');
  requireCanonicalMatch(records, 'candidate_decision_required_gates', problems, 'candidate_decision_required_gates', 'exact-sequence');
  requireCanonicalMatch(records, 'first_round_output_candidate_gate_verdict', problems, 'first_round_output_candidate_gate_verdict', 'exact-scalar');
  for (const record of records) {
    if (normalizeText(string(record, 'first_round_output_candidate_gate_verdict', problems)) !== 'block') {
      fail(problems, `${record.source} first_round_output_candidate_gate_verdict must be block`);
    }
  }
  const stageIntake = normalizeText(string(brief, 'stage_intake_contract', problems));
  const firstRoundOutput = normalizeText(string(brief, 'first_round_expected_output', problems));
  const candidateGates = strings(brief, 'candidate_decision_required_gates', problems).map(normalizeText);
  if (stageIntake === 'validate-technical') {
    const task = parseDominantTaskContract(brief, problems);
    const requiredFirstRoundOutput = 'packet completeness, missing-evidence list, and next review step';
    if (firstRoundOutput !== requiredFirstRoundOutput) fail(problems, `${brief.source} validate-technical first_round_expected_output must be exactly ${requiredFirstRoundOutput}`);
    if (normalizeText(task.expectedOutput) !== requiredFirstRoundOutput) fail(problems, `${brief.source} validate-technical dominant_task_contract expected_output must be exactly ${requiredFirstRoundOutput}`);
    const expectedGates = ['complete-second-round-package', 'named-technical-owner-review'];
    if (candidateGates.length !== expectedGates.length || candidateGates.some((value, index) => value !== expectedGates[index])) {
      fail(problems, `${brief.source} validate-technical candidate_decision_required_gates must be exactly complete-second-round-package then named-technical-owner-review`);
    }
    for (const record of records) for (const [field, value] of collectCandidateDecisionSurfaces(record)) {
      const values = Array.isArray(value) ? value : [value];
      for (const rawCandidate of values) {
        let candidate = rawCandidate;
        if (field === 'buyer_visible_cta_inventory') {
          const parts = String(rawCandidate).split('|').map((part) => part.trim());
          if (parts.length === 10 && /technical|engineering/i.test(parts[5] || '')) candidate = `${parts[3]} named technical-owner review`;
        }
        if (hasPrematureDecisionPromise(candidate)) fail(problems, `${record.source} ${field} must not promise candidate-or-stop before a complete second-round package and named technical-owner review`);
      }
    }
    const outcome = normalizeText(string(brief, 'stage_primary_outcome', problems));
    if (hasPrematureDecisionPromise(outcome)) {
      fail(problems, `${brief.source} first-round stage_primary_outcome must not promise candidate-or-stop before candidate_decision_required_gates pass`);
    }
    const intentCompletion = normalizeText(string(brief, 'intent_completion_test', problems));
    if (!/(?:packet completeness|completeness)/.test(intentCompletion) || !/missing evidence/.test(intentCompletion) || !/next review step/.test(intentCompletion)) {
      fail(problems, `${brief.source} validate-technical intent_completion_test must close first round with packet completeness, missing evidence, and next review step`);
    }
    if (hasPrematureDecisionPromise(intentCompletion)) {
      fail(problems, `${brief.source} validate-technical intent_completion_test must block candidate-or-stop until the declared gates pass`);
    }
    for (const field of ['direct_answer_expected_output_or_route']) {
      if (hasPrematureDecisionPromise(string(brief, field, problems))) fail(problems, `${brief.source} ${field} must not promise a candidate decision before both declared gates pass`);
    }
    const reasonRows = strings(brief, 'qualification_reason_codes', problems, { allowEmpty: true }).map((row) => row.split('|').map((part) => part.trim()));
    const firstRound = reasonRows.find((parts) => normalizeText(parts[0] || '') === 'first-round-complete');
    const engineeringReady = reasonRows.find((parts) => normalizeText(parts[0] || '') === 'engineering-review-ready');
    if (!firstRound || firstRound.length !== 5) fail(problems, `${brief.source} validate-technical qualification_reason_codes requires a five-slot first-round-complete row`);
    else if (/\b(?:submit|send|upload|share|copy|paste)\b/i.test(firstRound[4])) fail(problems, `${brief.source} first-round-complete next step must stay local while the route is unverified`);
    if (!engineeringReady || engineeringReady.length !== 5) fail(problems, `${brief.source} validate-technical qualification_reason_codes requires a five-slot engineering-review-ready row`);
    else if (hasPrematureDecisionPromise(engineeringReady[4])) {
      fail(problems, `${brief.source} engineering-review-ready must not return candidate-or-stop before the declared gates pass`);
    }
  } else {
    if (firstRoundOutput !== 'not-applicable') fail(problems, `${brief.source} non-validate-technical package requires first_round_expected_output=not-applicable`);
    if (candidateGates.length !== 1 || candidateGates[0] !== 'not-applicable') fail(problems, `${brief.source} non-validate-technical package requires candidate_decision_required_gates=[not-applicable]`);
  }
}


const CTA_MEASUREMENT_ROLES = ['primary', 'soft', 'fallback'];
const CTA_MEASUREMENT_CORE_EVENT_SLOTS = [4, 5, 6, 7];

function ctaMeasurementRowDigest(row) {
  return `sha256:${createHash('sha256').update(String(row).trim()).digest('hex')}`;
}

function validateCtaMeasurementEvidence(rows, rowRefs, abandonmentRefs, source, evidenceRoot, problems) {
  const allRefs = [...new Set(rowRefs.flat())];
  const abandonmentSet = new Set(abandonmentRefs);
  const allRefSet = new Set(allRefs);
  if (abandonmentSet.size !== allRefSet.size || [...abandonmentSet].some((ref) => !allRefSet.has(ref))) {
    fail(problems, `${source} cta_abandonment_measurement_refs must exactly reference the same measurement-plan evidence sections used by cta_measurement_map`);
  }
  validateLocalEvidenceRefs(allRefs, source, 'cta_measurement_map evidence-refs', evidenceRoot, problems, { requireFragment: true, regularNonSymlink: true, verifyFragment: true });
  validateProductionEvidenceRefs(allRefs, source, 'cta_measurement_map evidence-refs', evidenceRoot, problems, { expectedKinds: ['measurement-plan'] });
  const expected = rows.map(ctaMeasurementRowDigest);
  const observed = [];
  const hashesByRef = new Map();
  for (const ref of allRefs) {
    const section = loadReferencedSection(ref, evidenceRoot);
    const hashes = [...section.matchAll(/(?:^|\n)\s*measurement_row_sha256\s*:\s*(sha256:[a-f0-9]{64})\s*(?=\n|$)/gi)]
      .map((match) => match[1].toLowerCase());
    hashesByRef.set(ref, new Set(hashes));
    observed.push(...hashes);
  }
  const expectedCounts = new Map(expected.map((hash) => [hash, (expected.filter((value) => value === hash).length)]));
  const observedCounts = new Map(observed.map((hash) => [hash, (observed.filter((value) => value === hash).length)]));
  if (observed.length !== expected.length
    || [...expectedCounts].some(([hash, count]) => observedCounts.get(hash) !== count)
    || [...observedCounts].some(([hash, count]) => expectedCounts.get(hash) !== count)) {
    fail(problems, `${source} CTA measurement evidence must contain the exact current measurement_row_sha256 set once each, with no ghost, missing, stale, or duplicate row digest`);
  }
  rows.forEach((row, index) => {
    const digest = ctaMeasurementRowDigest(row);
    if (!rowRefs[index]?.some((ref) => hashesByRef.get(ref)?.has(digest))) {
      fail(problems, `${source} cta_measurement_map row ${index + 1} evidence-refs do not bind its exact measurement_row_sha256`);
    }
  });
}

function validateCtaMeasurementPlan(records, brief, review, publish, evidenceRoot, problems) {
  for (const field of ['cta_measurement_map', 'conversion_measurement_plan_status', 'measurement_window', 'cta_abandonment_measurement_status', 'cta_abandonment_measurement_refs', 'cta_measurement_plan_verdict']) {
    const missing = records.filter((record) => !(field in record.attributes));
    for (const record of missing) fail(problems, `${record.source} missing required CTA measurement field ${field}`);
  }
  requireCanonicalMatch(records, 'cta_measurement_map', problems, 'cta_measurement_map', 'exact-raw-sequence');
  for (const field of ['conversion_measurement_plan_status', 'measurement_window', 'cta_abandonment_measurement_status', 'cta_measurement_plan_verdict']) {
    requireCanonicalMatch(records, field, problems, field, 'exact-raw-scalar');
  }
  requireCanonicalMatch(records, 'cta_abandonment_measurement_refs', problems, 'cta_abandonment_measurement_refs', 'exact-raw-sequence');
  const planStatus = normalizeText(string(brief, 'conversion_measurement_plan_status', problems));
  if (!['planned', 'active'].includes(planStatus)) fail(problems, `${brief.source} applicable CTA surfaces require conversion_measurement_plan_status=planned or active; not-applicable is blocked`);
  const measurementWindow = string(brief, 'measurement_window', problems);
  meaningfulScalar(measurementWindow, brief.source, 'measurement_window', problems, { minLength: 8 });
  if (/^not-applicable$/i.test(measurementWindow)) fail(problems, `${brief.source} applicable CTA surfaces require a concrete measurement_window`);
  const abandonmentStatus = normalizeText(string(brief, 'cta_abandonment_measurement_status', problems));
  if (!['planned', 'active'].includes(abandonmentStatus)) fail(problems, `${brief.source} applicable CTA surfaces require cta_abandonment_measurement_status=planned or active`);
  const refs = strings(brief, 'cta_abandonment_measurement_refs', problems, { allowEmpty: true });
  if (!refs.length) fail(problems, `${brief.source} CTA measurement plan requires local evidence refs`);
  for (const record of records) if (normalizeText(string(record, 'cta_measurement_plan_verdict', problems)) !== 'pass') fail(problems, `${record.source} cta_measurement_plan_verdict must be pass`);

  const rows = strings(brief, 'cta_measurement_map', problems, { allowEmpty: true });
  if (rows.length !== 3) fail(problems, `${brief.source} cta_measurement_map must contain exactly three rows in primary, soft, fallback order`);
  const conversionRows = strings(brief, 'conversion_surface_map', problems, { allowEmpty: true });
  const conversions = conversionRows.map((row) => row.split('|').map((part) => part.trim()));
  const inventory = new Map(strings(brief, 'buyer_visible_cta_inventory', problems, { allowEmpty: true }).map((row) => {
    const parts = row.split('|').map((part) => part.trim());
    return [parts[0], { locator: parts[2], owner: parts[5], interaction: parts[6] }];
  }));
  const stage = normalizeText(string(brief, 'stage', problems));
  const intake = normalizeText(string(brief, 'stage_intake_contract', problems));
  const technicalQualificationApplicable = stage === 'validate' && intake === 'validate-technical';
  const commercialInputsRecord = records.find((record) => Object.prototype.hasOwnProperty.call(record.attributes, 'sales_commercial_inputs'));
  const commercialInputs = commercialInputsRecord ? strings(commercialInputsRecord, 'sales_commercial_inputs', problems, { allowEmpty: true }) : [];
  const commercialAcceptanceApplicable = stage === 'buy'
    && intake === 'buy-commercial'
    && normalizeText(string(brief, 'sales_acceptance_requirement', problems)) === 'required'
    && commercialInputs.length > 0
    && normalizeText(string(brief, 'sales_acceptance_owner', problems)) !== 'not-applicable';
  const seenSurfaceIds = new Set();
  const seenCtaVersions = new Set();
  const seenEvents = new Set();
  const rowRefs = [];
  let pageVersion = '';
  rows.forEach((row, index) => {
    const parts = row.split('|').map((part) => part.trim());
    if (parts.length !== 16 || parts.some((part) => !part)) {
      fail(problems, `${brief.source} cta_measurement_map row ${index + 1} must contain exactly 16 non-empty slots: surface-id|surface-role|page-version|cta-version|start-event|submit-event|success-event|failure-event|abandonment-definition|qualification-event-or-not-applicable|commercial-acceptance-event-or-not-applicable|data-source|baseline-window|observation-window|accountable-owner|evidence-refs`);
      rowRefs.push([]);
      return;
    }
    const [surfaceId, role, rowPageVersion, ctaVersion, , , , , abandonmentDefinition, qualificationEvent, commercialAcceptanceEvent, dataSource, baselineWindow, observationWindow, owner, evidenceRefs] = parts;
    if (role !== CTA_MEASUREMENT_ROLES[index]) fail(problems, `${brief.source} cta_measurement_map row ${index + 1} surface-role must exactly be ${CTA_MEASUREMENT_ROLES[index]}`);
    const conversion = conversions[index] || [];
    if (conversion[0] !== surfaceId || conversion[1] !== role) fail(problems, `${brief.source} cta_measurement_map row ${index + 1} surface-id and role must exactly bind conversion_surface_map row ${index + 1}`);
    const inventorySurface = inventory.get(surfaceId);
    if (!inventorySurface) fail(problems, `${brief.source} cta_measurement_map surface-id ${surfaceId} must exist in buyer_visible_cta_inventory`);
    else {
      if (conversion[3] !== inventorySurface.locator) fail(problems, `${brief.source} cta_measurement_map ${surfaceId} conversion location must exactly bind buyer_visible_cta_inventory locator`);
      if (conversion[4] !== inventorySurface.interaction) fail(problems, `${brief.source} cta_measurement_map ${surfaceId} conversion interaction must exactly bind buyer_visible_cta_inventory interaction-type`);
      if (owner !== inventorySurface.owner) fail(problems, `${brief.source} cta_measurement_map ${surfaceId} accountable-owner must exactly bind buyer_visible_cta_inventory owner`);
    }
    for (const [field, value] of [['surface-id', surfaceId], ['page-version', rowPageVersion], ['cta-version', ctaVersion], ['data-source', dataSource]]) {
      if (!/^[a-z0-9][a-z0-9._-]{2,}$/i.test(value) || /^(?:not-applicable|tbd|todo|unknown|replace|placeholder)/i.test(value)) fail(problems, `${brief.source} cta_measurement_map ${role} ${field} must be a stable non-placeholder identifier`);
    }
    if (seenSurfaceIds.has(surfaceId)) fail(problems, `${brief.source} cta_measurement_map surface-id must be unique: ${surfaceId}`);
    seenSurfaceIds.add(surfaceId);
    if (seenCtaVersions.has(ctaVersion)) fail(problems, `${brief.source} cta_measurement_map cta-version must be unique per surface: ${ctaVersion}`);
    seenCtaVersions.add(ctaVersion);
    if (!pageVersion) pageVersion = rowPageVersion;
    else if (rowPageVersion !== pageVersion) fail(problems, `${brief.source} cta_measurement_map page-version must be identical across all surfaces`);
    for (const slot of CTA_MEASUREMENT_CORE_EVENT_SLOTS) {
      const eventName = parts[slot];
      if (!/^[a-z][a-z0-9_]{3,}$/i.test(eventName) || /^(?:not_applicable|tbd|todo|unknown|replace|placeholder)/i.test(eventName)) fail(problems, `${brief.source} cta_measurement_map ${role} event slot ${slot + 1} must be a stable event name`);
      if (seenEvents.has(eventName)) fail(problems, `${brief.source} cta_measurement_map event names must not be reused across surfaces or lifecycle slots: ${eventName}`);
      seenEvents.add(eventName);
    }
    for (const [field, value, applicable] of [
      ['qualification-event', qualificationEvent, technicalQualificationApplicable && role === 'primary'],
      ['commercial-acceptance-event', commercialAcceptanceEvent, commercialAcceptanceApplicable && role === 'primary'],
    ]) {
      if (!applicable) {
        if (value !== 'not-applicable') fail(problems, `${brief.source} cta_measurement_map ${role} ${field} must be not-applicable for stage=${stage} and intake=${intake}`);
      } else {
        if (!/^[a-z][a-z0-9_]{3,}$/i.test(value) || /^(?:not_applicable|tbd|todo|unknown|replace|placeholder)/i.test(value)) fail(problems, `${brief.source} cta_measurement_map ${role} ${field} must be a stable event name for the applicable stage`);
        if (seenEvents.has(value)) fail(problems, `${brief.source} cta_measurement_map event names must not be reused across surfaces or lifecycle slots: ${value}`);
        seenEvents.add(value);
      }
    }
    meaningfulScalar(abandonmentDefinition, brief.source, `cta_measurement_map ${role} abandonment-definition`, problems, { minLength: 20 });
    if (!/\b(?:without|within|after|before|no\s+success|no\s+completion)\b/i.test(abandonmentDefinition)) fail(problems, `${brief.source} cta_measurement_map ${role} abandonment-definition must state an observable start-to-outcome boundary`);
    for (const [field, value] of [['baseline-window', baselineWindow], ['observation-window', observationWindow]]) {
      meaningfulScalar(value, brief.source, `cta_measurement_map ${role} ${field}`, problems, { minLength: 8 });
      if (/^not-applicable$/i.test(value)) fail(problems, `${brief.source} cta_measurement_map ${role} ${field} cannot be not-applicable`);
    }
    requireStableOwnerIdentity(owner, brief.source, `cta_measurement_map ${role} accountable-owner`, problems);
    const currentRowRefs = evidenceRefs.split(',').map((value) => value.trim()).filter(Boolean);
    rowRefs.push(currentRowRefs);
    if (!currentRowRefs.length) fail(problems, `${brief.source} cta_measurement_map ${role} evidence-refs must be non-empty`);
  });
  if (conversions.length !== CTA_MEASUREMENT_ROLES.length) fail(problems, `${brief.source} conversion_surface_map must expose exactly three measurable surfaces`);
  validateCtaMeasurementEvidence(rows, rowRefs, refs, brief.source, evidenceRoot, problems);
}

function validateTerminalAndPainClosure(records, brief, publish, problems) {
  requireCanonicalMatch(records, 'terminal_action_contract', problems, 'terminal_action_contract', 'exact-scalar');
  requireCanonicalMatch(records, 'visible_pain_chain', problems, 'visible_pain_chain', 'exact-raw-sequence');
  requireCanonicalMatch(records, 'visible_pain_chain_sequence_verdict', problems, 'visible_pain_chain_sequence_verdict', 'exact-raw-scalar');
  for (const record of records) {
    const rows = strings(record, 'visible_pain_chain', problems, { allowEmpty: true });
    if (rows.length !== 6) fail(problems, `${record.source} visible_pain_chain must contain exactly six rows`);
    if (normalizeText(string(record, 'visible_pain_chain_sequence_verdict', problems)) !== 'pass') fail(problems, `${record.source} visible_pain_chain_sequence_verdict must be pass`);
  }
  const [contractStage, decisionObject, expectedOutput, action, commitment] = parseTerminalActionContract(brief, problems);
  const stage = normalizeText(string(brief, 'stage', problems));
  if (normalizeText(contractStage) !== stage) fail(problems, `${brief.source} terminal_action_contract stage must exactly match stage`);
  const task = parseDominantTaskContract(brief, problems);
  if (!actionSlotsAlign(action, task.action)) fail(problems, `${brief.source} terminal_action_contract action must match dominant_task_contract action`);
  if (!actionSlotsAlign(task.action, string(brief, 'dominant_search_intent', problems))) fail(problems, `${brief.source} dominant_search_intent leading action must match dominant_task_contract action`);
  if (semanticOverlap(`${decisionObject} ${expectedOutput}`, `${task.value} ${task.decisionObject} ${task.expectedOutput}`).length < 2) fail(problems, `${brief.source} terminal_action_contract must materially match dominant_task_contract`);
  if (normalizeText(commitment) !== normalizeText(string(brief, 'commercial_commitment', problems))) fail(problems, `${brief.source} terminal_action_contract commercial commitment must match commercial_commitment`);
  if (stage !== 'buy' && commercialClassification(`${action} ${expectedOutput} ${commitment}`).commercial) fail(problems, `${brief.source} non-Buy terminal_action_contract must not end in quote, RFQ, order, supplier nomination, or supplier award`);
  if (normalizeText(string(publish, 'visible_pain_chain_sequence_verdict', problems)) !== 'pass') fail(problems, `${publish.source} visible_pain_chain_sequence_verdict=block is fatal`);
}

function validateBodyEditorialTruth(brief, draft, review, evidenceScope, problems) {
  const blockquotes = draft.body.split('\n').filter((line) => /^\s*>\s*\S/.test(line));
  const allowedQuoteCopy = strings(brief, 'buyer_visible_cta_inventory', problems, { allowEmpty: true })
    .map((row) => row.split('|').map((part) => part.trim()))
    .filter((parts) => normalizeText(parts[1]) === 'blockquote')
    .map((parts) => normalizeText(markdownPlainText(parts[3] || '')));
  for (const line of blockquotes) {
    const text = normalizeText(markdownPlainText(line.replace(/^\s*>\s*/, '')));
    const attributed = /\b(?:source|quoted from|according to)\b/i.test(text) && /https?:\/\/|\[[^\]]+\]\([^)]+\)/.test(line);
    if (!attributed && !allowedQuoteCopy.some((copy) => copy && (copy.includes(text) || text.includes(copy)))) fail(problems, `${draft.source} author judgment must not be formatted as an unattributed blockquote`);
  }
  if (evidenceScope === 'synthetic-fixture' && !/(?:demonstration|fictional|illustrative example|synthetic (?:fixture|example)).{0,200}(?:fictional|not real|example|test-only|does not represent|does not prove)/is.test(markdownPlainText(draft.body))) {
    fail(problems, `${draft.source} synthetic publishable body requires a buyer-visible fictional or demonstration disclosure inside the publishable markers`);
  }
  const relationships = strings(brief, 'second_round_input_relationships', problems, { allowEmpty: true });
  const expected = new Map(relationships.map((row) => {
    const [item, relationship, firstSource, reason] = row.split('|').map((part) => part.trim());
    return [normalizeText(item), {
      relationship: normalizeText(relationship),
      firstSource: normalizeText(firstSource),
      reason: normalizeText(reason),
    }];
  }));
  const observed = new Map();
  const roundTwoSections = h2SectionRanges(draft.body)
    .filter(({ heading }) => /\b(?:round two|second[- ]round)\b/i.test(heading));
  for (const section of roundTwoSections) for (const table of markdownTableBlocks(section.markdown)) {
    const lines = table.split('\n');
    const headers = parseMarkdownTableCells(lines[0]).map((header) => header.replace(/[ _-]+/g, ' '));
    const itemIndex = headers.findIndex((header) => /second round input|input requested in round two/.test(header));
    const relationshipIndex = headers.findIndex((header) => /how it builds on round one|relationship to round one|round one relationship/.test(header));
    const reasonIndex = headers.findIndex((header) => /why it is needed|buyer reason|decision reason/.test(header));
    if (itemIndex < 0 && relationshipIndex < 0 && reasonIndex < 0) continue;
    if (itemIndex < 0 || relationshipIndex < 0 || reasonIndex < 0) {
      fail(problems, `${draft.source} buyer-visible second-round relationship table requires Second-round input, How it builds on round one, and Why it is needed columns`);
      continue;
    }
    for (const line of lines.slice(2)) {
      const cells = parseMarkdownTableCells(line);
      const item = cells[itemIndex] || '';
      const relationshipCell = cells[relationshipIndex] || '';
      const reason = cells[reasonIndex] || '';
      let relationship = '';
      let firstSource = '';
      if (/^new input(?:;\s*it does not refine a first-round field)?$/i.test(relationshipCell)) {
        relationship = 'new';
        firstSource = 'not-applicable';
      } else {
        const refines = /^refines\s*:\s*(.+)$/i.exec(relationshipCell);
        if (refines) {
          relationship = 'refines';
          firstSource = normalizeText(refines[1]);
        }
      }
      if (!SECOND_ROUND_RELATIONSHIP_MODES.has(relationship)) fail(problems, `${draft.source} buyer-visible Relationship must be exact New input or Refines: <first-round source>: ${relationshipCell || 'missing'}`);
      if (!String(reason).trim()) fail(problems, `${draft.source} buyer-visible second-round row requires a non-empty Why it is needed buyer reason: ${item || 'missing item'}`);
      const normalizedItem = normalizeText(item);
      if (observed.has(normalizedItem)) fail(problems, `${draft.source} buyer-visible second-round item is duplicated: ${item}`);
      observed.set(normalizedItem, { relationship, firstSource, reason: normalizeText(reason) });
    }
  }
  for (const section of draft.body.split(/(?=^###\s+)/gm)) {
    const heading = /^###\s+(.+)$/m.exec(section)?.[1]?.trim();
    const relationship = /^-\s*Relationship:\s*([^\n.]+)\.?\s*$/mi.exec(section)?.[1]?.trim();
    const firstSource = /^-\s*First-round source:\s*([^\n.]+)\.?\s*$/mi.exec(section)?.[1]?.trim();
    if (!heading || (!relationship && !firstSource)) continue;
    if (!relationship || !firstSource) fail(problems, `${draft.source} second-round item ${heading} requires both Relationship and First-round source`);
    else {
      if (!SECOND_ROUND_RELATIONSHIP_MODES.has(normalizeText(relationship))) fail(problems, `${draft.source} buyer-visible Relationship must be exact new or refines: ${relationship}`);
      const normalizedHeading = normalizeText(heading);
      if (observed.has(normalizedHeading)) fail(problems, `${draft.source} buyer-visible second-round item is duplicated: ${heading}`);
      observed.set(normalizedHeading, { relationship: normalizeText(relationship), firstSource: normalizeText(firstSource), reason: '' });
    }
  }
  if (expected.size || observed.size) {
    if (expected.size !== observed.size || [...expected].some(([item, contract]) => {
      const body = observed.get(item);
      return !body || body.relationship !== contract.relationship || body.firstSource !== contract.firstSource
        || !body.reason || semanticOverlap(contract.reason, body.reason).length < 3;
    })) fail(problems, `${draft.source} buyer-visible Relationship and First-round source must exactly project second_round_input_relationships`);
  }
  const internalLinksPass = internalLinkPublicationGatesPass(brief, problems);
  const links = [...draft.body.matchAll(/\[[^\]]+\]\((https:\/\/[^)]+)\)/g)].map((match) => match[1]);
  if (!internalLinksPass && /(?:buyer[- ]visible )?(?:internal )?links? (?:are )?visible.{0,80}\bpass\b/is.test(review.body)) fail(problems, `${review.source} must not claim buyer-visible internal links PASS while internal-link gates are blocked`);
  if (!internalLinksPass && links.some((url) => strings(brief, 'internal_link_targets', problems, { allowEmpty: true }).some((row) => row.includes(url)))) fail(problems, `${draft.source} blocked internal-link target must not be buyer-visible`);
}


function validateEvidenceOriginAndBuyerProof(records, brief, review, evidenceScope, evidenceRoot, problems) {
  for (const field of [
    'evidence_origin', 'fixture_identity', 'production_proof_eligible',
    'customer_language_status', 'customer_language_refs', 'customer_language_gate_verdict',
    'pain_evidence_status', 'pain_evidence_refs', 'pain_evidence_gate_verdict',
  ]) requireCanonicalMatch(records, field, problems, field, Array.isArray(brief.attributes[field]) ? 'exact-sequence' : 'exact-scalar');

  const origin = normalizeText(string(brief, 'evidence_origin', problems));
  if (typeof brief.attributes.fixture_identity !== 'string' || !brief.attributes.fixture_identity.trim()) fail(problems, `${brief.source} missing required field fixture_identity`);
  const fixtureIdentity = normalizeText(typeof brief.attributes.fixture_identity === 'string' ? brief.attributes.fixture_identity : '');
  const eligible = brief.attributes.production_proof_eligible;
  if (!['synthetic-fixture', 'test-fixture', 'live-production'].includes(origin)) fail(problems, `${brief.source} evidence_origin must use synthetic-fixture|test-fixture|live-production`);
  if (typeof eligible !== 'boolean') fail(problems, `${brief.source} production_proof_eligible must be boolean`);
  if (origin === 'synthetic-fixture' || origin === 'test-fixture') {
    if (!fixtureIdentity || fixtureIdentity === 'not-applicable') fail(problems, `${brief.source} ${origin} requires a concrete fixture_identity`);
    if (eligible !== false) fail(problems, `${brief.source} ${origin} requires production_proof_eligible=false`);
  }
  if (origin === 'live-production') {
    if (fixtureIdentity !== 'not-applicable') fail(problems, `${brief.source} live-production requires fixture_identity=not-applicable`);
    if (eligible !== true) fail(problems, `${brief.source} live-production requires production_proof_eligible=true`);
  }
  if (evidenceScope === 'synthetic-fixture' && origin !== 'synthetic-fixture') fail(problems, `${brief.source} evidence_scope=synthetic-fixture requires evidence_origin=synthetic-fixture`);
  if (evidenceScope === 'production') {
    if (origin !== 'live-production') fail(problems, `${brief.source} evidence_scope=production requires evidence_origin=live-production`);
    if (fixtureIdentity !== 'not-applicable') fail(problems, `${brief.source} evidence_scope=production requires fixture_identity=not-applicable`);
    if (eligible !== true) fail(problems, `${brief.source} evidence_scope=production requires production_proof_eligible=true`);
  }

  const ownerPage = string(brief, 'owner_page', problems);
  for (const contract of [
    { label: 'customer-language', statusField: 'customer_language_status', refsField: 'customer_language_refs', gateField: 'customer_language_gate_verdict', kind: 'customer-language', checkId: 'customer-language', role: 'customer-language' },
    { label: 'pain-evidence', statusField: 'pain_evidence_status', refsField: 'pain_evidence_refs', gateField: 'pain_evidence_gate_verdict', kind: 'pain-evidence', checkId: 'pain-evidence', role: 'pain-evidence' },
  ]) {
    const status = normalizeText(string(brief, contract.statusField, problems));
    const refs = strings(brief, contract.refsField, problems, { allowEmpty: true });
    const gate = normalizeText(string(brief, contract.gateField, problems));
    if (!['pass', 'block'].includes(gate)) fail(problems, `${brief.source} ${contract.gateField} must be pass or block`);
    if (evidenceScope === 'production') {
      if (status !== 'confirmed') fail(problems, `${brief.source} production ${contract.label} requires ${contract.statusField}=confirmed`);
      if (refs.length < 1) fail(problems, `${brief.source} production ${contract.label} requires a non-empty ${contract.refsField} list`);
      if (gate !== 'pass') fail(problems, `${brief.source} production ${contract.label} requires ${contract.gateField}=pass`);
      validateLocalEvidenceRefs(refs, brief.source, contract.refsField, evidenceRoot, problems, { requireFragment: true, regularNonSymlink: true, verifyFragment: true });
      validateProductionEvidenceRefs(refs, brief.source, contract.refsField, evidenceRoot, problems, {
        expectedKinds: [contract.kind], expectedCheckId: contract.checkId,
        expectedTargets: [{ url: ownerPage, role: contract.role, task: '' }],
        requireStructuredSection: true,
        latestAllowedAt: string(review, 'reviewed_at', problems),
      });
    } else if (gate !== 'block') {
      fail(problems, `${brief.source} synthetic fixture requires ${contract.gateField}=block`);
    }
  }
}

function parseCollectionPolicyRows(brief, problems) {
  const rows = strings(brief, 'cta_collection_route_policy_contracts', problems, { allowEmpty: true });
  const parsed = [];
  const seen = new Set();
  for (const raw of rows) {
    const parts = raw.split('|').map((part) => part.trim());
    if (parts.length !== 18 || parts.some((part) => !part)) {
      fail(problems, `${brief.source} cta_collection_route_policy_contracts row must use route-id|endpoint|required-inputs-mode|data-purpose|retention-period|deletion-path|retention-owner|policy-contract-id|policy-version|policy-digest|policy-checked-at|policy-observed-at|policy-reviewed-at|policy-review-ceiling|policy-status|policy-owner-acceptance|policy-evidence-refs|deletion-capability-evidence-refs: ${raw}`);
      continue;
    }
    const [routeId, endpoint, requiredInputsMode, dataPurpose, retentionPeriod, deletionPath, retentionOwner, policyContractId, policyVersion, policyDigest, policyCheckedAt, policyObservedAt, policyReviewedAt, policyReviewCeiling, policyStatus, policyOwnerAcceptance, policyRefsRaw, deletionRefsRaw] = parts;
    const key = normalizeText(routeId);
    if (!['primary', 'fallback'].includes(key)) fail(problems, `${brief.source} cta_collection_route_policy_contracts route-id must be primary or fallback: ${routeId}`);
    if (seen.has(key)) fail(problems, `${brief.source} cta_collection_route_policy_contracts contains duplicate route row: ${routeId}`);
    seen.add(key);
    if (!['same-as-cta-required-inputs', 'none'].includes(normalizeText(requiredInputsMode))) fail(problems, `${brief.source} cta_collection_route_policy_contracts required-inputs-mode must be same-as-cta-required-inputs or none: ${raw}`);
    if (normalizeText(requiredInputsMode) === 'none') fail(problems, `${brief.source} cta_collection_route_policy_contracts must omit a route row when required-inputs-mode=none: ${routeId}`);
    requireAbsoluteHttpsUrl(endpoint, brief.source, `cta_collection_route_policy_contracts ${routeId} endpoint`, problems);
    requireStableOwnerIdentity(retentionOwner, brief.source, `cta_collection_route_policy_contracts ${routeId} retention-owner`, problems);
    for (const [field, value] of [['data-purpose', dataPurpose], ['retention-period', retentionPeriod], ['deletion-path', deletionPath], ['policy-contract-id', policyContractId]]) meaningfulScalar(value, brief.source, `cta_collection_route_policy_contracts ${routeId} ${field}`, problems, { minLength: field === 'policy-contract-id' ? 6 : 12 });
    if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/.test(policyVersion) || PLACEHOLDER_PATTERN.test(policyVersion)) fail(problems, `${brief.source} cta_collection_route_policy_contracts ${routeId} policy-version must be a stable non-placeholder version`);
    if (!/^sha256:[a-f0-9]{64}$/i.test(policyDigest)) fail(problems, `${brief.source} cta_collection_route_policy_contracts ${routeId} policy-digest must use sha256:<64 hex>`);
    if (normalizeText(policyStatus) !== 'confirmed') fail(problems, `${brief.source} cta_collection_route_policy_contracts ${routeId} policy-status must be confirmed`);
    if (normalizeText(policyOwnerAcceptance) !== 'accepted') fail(problems, `${brief.source} cta_collection_route_policy_contracts ${routeId} policy-owner-acceptance must be accepted`);
    const policyRefs = parseFallbackLocalRefs(policyRefsRaw, brief.source, `cta_collection_route_policy_contracts ${routeId} policy evidence`, problems);
    const deletionRefs = parseFallbackLocalRefs(deletionRefsRaw, brief.source, `cta_collection_route_policy_contracts ${routeId} deletion evidence`, problems);
    parsed.push({ routeId: key, endpoint, requiredInputsMode: normalizeText(requiredInputsMode), dataPurpose, retentionPeriod, deletionPath, retentionOwner, policyContractId, policyVersion, policyDigest, policyCheckedAt, policyObservedAt, policyReviewedAt, policyReviewCeiling, policyRefs, deletionRefs });
  }
  return parsed;
}

function validateCollectionRoutePolicyContracts(records, brief, review, evidenceScope, evidenceRoot, fallbackContract, problems) {
  requireCanonicalMatch(records, 'cta_collection_route_policy_contracts', problems, 'cta_collection_route_policy_contracts', 'exact-sequence');
  const rows = parseCollectionPolicyRows(brief, problems);
  const byRoute = new Map(rows.map((row) => [row.routeId, row]));
  const primary = byRoute.get('primary');
  const fallback = byRoute.get('fallback');
  const primaryEndpoint = string(brief, 'cta_destination', problems);
  if (primary && normalizeEndpointForComparison(primary.endpoint) !== normalizeEndpointForComparison(primaryEndpoint)) fail(problems, `${brief.source} primary collection policy endpoint must exactly match the canonical cta_destination binding`);
  if (fallbackContract?.status === 'verified' && normalizeText(fallbackContract.requiredInputsMode) !== 'none') {
    if (!fallback) fail(problems, `${brief.source} fallback collection policy row is missing; exactly one complete row is required for a verified collecting fallback route`);
    else if (normalizeEndpointForComparison(fallback.endpoint) !== normalizeEndpointForComparison(fallbackContract.endpoint)) fail(problems, `${brief.source} fallback collection policy endpoint must exactly match the cta_fallback_route_contract endpoint binding`);
  } else if (fallback) {
    fail(problems, `${brief.source} fallback collection policy row is not allowed unless the fallback route is verified and collects inputs`);
  }
  if (evidenceScope !== 'production' && rows.length) fail(problems, `${brief.source} synthetic fixture must not fabricate collection route policy rows`);
  if (evidenceScope === 'production') for (const row of rows) {
    const canonicalReviewedAt = string(review, 'reviewed_at', problems);
    validateCtaPolicyTemporalContract({
      source: brief.source,
      policyEffectiveAt: row.policyCheckedAt,
      policyCheckedAt: row.policyCheckedAt,
      policyObservedAt: row.policyObservedAt,
      policyReviewedAt: row.policyReviewedAt,
      policyReviewCeiling: row.policyReviewCeiling,
      canonicalReviewedAt,
      problems,
    });
    validateLocalEvidenceRefs(row.policyRefs, brief.source, `${row.routeId} policy evidence refs`, evidenceRoot, problems, { requireFragment: true, regularNonSymlink: true, verifyFragment: true });
    validateLocalEvidenceRefs(row.deletionRefs, brief.source, `${row.routeId} deletion capability evidence refs`, evidenceRoot, problems, { requireFragment: true, regularNonSymlink: true, verifyFragment: true });
    const requiredExtraFields = ['policy_contract_id', 'policy_version', 'policy_digest', 'policy_artifact_ref', 'policy_artifact_digest', 'policy_checked_at', 'capability_acceptance'];
    const policyInspections = validateProductionEvidenceRefs(row.policyRefs, brief.source, `${row.routeId} policy evidence refs`, evidenceRoot, problems, {
      expectedKinds: ['cta-data-policy'], expectedTargets: [{ url: row.endpoint, role: row.routeId === 'fallback' ? 'fallback-route' : string(brief, 'stage_cta_mode', problems), task: '' }], requiredExtraFields, requireStructuredSection: true, latestAllowedAt: canonicalReviewedAt,
    });
    const deletionInspections = validateProductionEvidenceRefs(row.deletionRefs, brief.source, `${row.routeId} deletion capability evidence refs`, evidenceRoot, problems, {
      expectedKinds: ['cta-deletion-capability'], expectedTargets: [{ url: row.endpoint, role: row.routeId === 'fallback' ? 'fallback-route' : string(brief, 'stage_cta_mode', problems), task: '' }], requiredExtraFields, requireStructuredSection: true, latestAllowedAt: canonicalReviewedAt,
    });
    for (const inspection of [...policyInspections, ...deletionInspections]) validateCtaPolicyEvidenceProjection(inspection.fields || new Map(), {
      policy_contract_id: row.policyContractId,
      policy_version: row.policyVersion,
      policy_digest: row.policyDigest,
      policy_checked_at: row.policyCheckedAt,
    }, brief.source, inspection.ref, problems);
  }
  return rows;
}

function normalizedInputFieldMatches(text, input) {
  const normalized = normalizeText(markdownPlainText(text));
  const exact = normalizeText(input);
  if (normalized.includes(exact)) return true;
  const tokens = [...new Set(semanticTokens(input))];
  const overlap = semanticOverlap(input, normalized);
  return overlap.length >= 2 && overlap.length / Math.max(tokens.length, 1) >= 0.4;
}

function validateTransmissionActionInventory(records, brief, draft, problems) {
  for (const record of records) if (!Object.prototype.hasOwnProperty.call(record.attributes, 'cta_transmission_action_inventory')) {
    fail(problems, `${record.source} field cta_transmission_action_inventory is required in all four canonical records`);
  }
  requireCanonicalMatch(records, 'cta_transmission_action_inventory', problems, 'cta_transmission_action_inventory', 'exact-raw-sequence');
  const allowedModes = new Set(['local-only', 'prohibited-until-verified', 'conditional-after-verification', 'prohibited-until-route-and-policy-gates-pass', 'approved-existing-process']);
  const rows = strings(brief, 'cta_transmission_action_inventory', problems, { allowEmpty: true });
  if (!rows.length) fail(problems, `${brief.source} cta_transmission_action_inventory requires at least one exact seven-slot row`);
  const actions = new Set();
  for (const row of rows) {
    const parts = String(row).split('|').map((part) => part.trim());
    if (parts.length !== 7 || parts.some((part) => !part)) { fail(problems, `${brief.source} cta_transmission_action_inventory row must use exactly seven slots`); continue; }
    const [surfaceId, action, object, mode, routeId, routeStatus, evidenceRef] = parts;
    meaningfulScalar(surfaceId, brief.source, 'cta_transmission_action_inventory surface-id', problems, { minLength: 4 });
    meaningfulScalar(action, brief.source, 'cta_transmission_action_inventory normalized-action', problems, { minLength: 3 });
    meaningfulScalar(object, brief.source, 'cta_transmission_action_inventory object', problems, { minLength: 4 });
    if (!allowedModes.has(mode)) fail(problems, `${brief.source} cta_transmission_action_inventory instruction-mode must use the closed allowlist`);
    if (/^unverified|unavailable|not-applicable/.test(routeStatus) && !['local-only', 'prohibited-until-verified', 'conditional-after-verification', 'prohibited-until-route-and-policy-gates-pass', 'approved-existing-process'].includes(mode)) fail(problems, `${brief.source} cta_transmission_action_inventory unverified route action must remain local, prohibited, or conditional after verification`);
    if (mode === 'conditional-after-verification' && hasPacketTransferIntent(`${action} ${object}`) && (routeId === 'not-applicable' || routeStatus === 'not-applicable')) fail(problems, `${brief.source} conditional-after-verification packet-transfer inventory row must bind a route and route status`);
    if (routeStatus === 'verified' && evidenceRef === 'not-applicable') fail(problems, `${brief.source} verified transmission inventory row requires evidence-bundle-ref`);
    actions.add(normalizeText(action));
  }
  for (const clause of transmissionClauses(draft.body)) {
    if (!hasPacketTransferIntent(clause)) continue;
    const normalized = normalizeText(clause);
    const represented = [...actions].some((action) => normalized.includes(action) || semanticOverlap(action, normalized).length >= 1);
    if (!represented) fail(problems, `${draft.source} buyer-visible transmission or transfer-of-control action is missing from cta_transmission_action_inventory: ${clause}`);
  }
}

function validateBuyerVisibleOpeningIcp(brief, draft, problems) {
  const opening = draft.body.split(/^##\s+/m)[0];
  const plain = normalizeText(markdownPlainText(opening));
  const fitTerms = semanticTokens(string(brief, 'icp_fit_contract', problems));
  const exclusionTerms = semanticTokens(string(brief, 'icp_exclusion_contract', problems));
  const fit = fitTerms.length >= 2 && fitTerms.filter((token) => plain.includes(token)).length >= Math.min(3, fitTerms.length);
  const exclusion = (exclusionTerms.length >= 2 && exclusionTerms.filter((token) => plain.includes(token)).length >= Math.min(3, exclusionTerms.length))
    || /\b(?:not\s+for|outside\s+(?:the\s+)?scope|exclude[sd]?|does\s+not\s+cover|not\s+a\s+fit)\b/i.test(opening);
  if (!fit) fail(problems, `${draft.source} buyer-visible opening before the first H2 must state who the article is for using the canonical ICP fit`);
  if (!exclusion) fail(problems, `${draft.source} buyer-visible opening before the first H2 must state at least one canonical ICP exclusion`);
}

function validateInformationGainAndRedundancyVerdicts(records, brief, review, problems) {
  for (const field of ['section_information_gain_verdict', 'normalized_field_set_redundancy_verdict']) {
    requireCanonicalMatch(records, field, problems, field, 'exact-raw-scalar');
    for (const record of records) {
      const value = record.attributes[field];
      if (value !== 'pass' && value !== 'block') fail(problems, `${record.source} ${field} must use exact closed enum pass or block`);
    }
    if (brief.attributes[field] === 'block' && normalizeText(string(review, 'fatal_gate_verdict', problems)) === 'pass') fail(problems, `${review.source} fatal_gate_verdict=pass cannot coexist with ${field}=block`);
  }
}

function validateNormalizedPacketRedundancy(brief, draft, problems) {
  if (normalizeText(string(brief, 'stage_intake_contract', problems)) !== 'validate-technical') return;
  const inputs = strings(brief, 'first_round_inquiry_inputs', problems);
  if (inputs.length < 4) return;
  const opening = draft.body.split(/^##\s/m)[0];
  const decisionTable = canonicalDecisionSection(draft.body);
  const preparation = markdownSectionByHeading(draft.body, /assemble .*locally|prepare .*locally|local preparation|readiness worksheet/i);
  const finalCtaWithFallback = markdownSectionByHeading(draft.body, /request .*engineering-readiness review|final cta|submit .*review|send .*review/i);
  const fallbackMarker = finalCtaWithFallback.search(/^###\s+Copyable (?:local|route-request) fallback\s*$/mi);
  const finalCta = fallbackMarker >= 0 ? finalCtaWithFallback.slice(0, fallbackMarker) : finalCtaWithFallback;
  const fallback = fallbackMarker >= 0 ? finalCtaWithFallback.slice(fallbackMarker) : '';
  const preparationMatches = inputs.filter((input) => normalizedInputFieldMatches(preparation, input));
  if (preparationMatches.length < inputs.length) fail(problems, `${draft.source} the single local worksheet must retain the complete first-round field set`);
  for (const [label, section] of [['opening', opening], ['decision table', decisionTable], ['final CTA', finalCta], ['copyable fallback', fallback]]) {
    const surfaces = [
      ...markdownTableBlocks(section),
      ...String(section || '').split(/\n\s*\n/u).map((surface) => surface.trim()).filter(Boolean),
    ];
    for (const surface of surfaces) {
      const matched = inputs.filter((input) => normalizedInputFieldMatches(surface, input));
      const structuredIntake = /^\s*(?:[-*+]\s+|\d+[.)]\s+)/m.test(surface)
        || /^\s*\|/m.test(surface)
        || /\b(?:collect|provide|fill|submit|prepare|record|complete|intake|fields?|packet|worksheet)\b/i.test(markdownPlainText(surface));
      if (structuredIntake && matched.length >= Math.max(4, inputs.length - 1)) {
        fail(problems, `${draft.source} normalized field-set redundancy blocks a repeated full or near-full packet surface in the ${label}; only the single local worksheet may carry the complete packet field set`);
        break;
      }
    }
  }
}

function validateUnverifiedTransmissionGate(brief, draft, collectionRows, fallbackContract, problems) {
  const primaryRoutePass = ['cta_reference_gate_verdict', 'cta_reachability_gate_verdict', 'cta_capability_gate_verdict']
    .every((field) => normalizeText(string(brief, field, problems)) === 'pass');
  const primaryPolicyPass = collectionRows.some((row) => row.routeId === 'primary');
  const fallbackRoutePass = fallbackContract?.status === 'verified';
  const fallbackPolicyPass = collectionRows.some((row) => row.routeId === 'fallback');
  if ((primaryRoutePass && primaryPolicyPass) || (fallbackRoutePass && fallbackPolicyPass)) return;
  for (const clause of transmissionClauses(draft.body)) {
    if (!hasPacketTransferIntent(clause) || isClauseLocalSafeTransfer(clause)) continue;
    fail(problems, `${draft.source} unverified route or policy blocks positive packet transmission or transfer-of-control before route and endpoint-bound policy verification: ${clause}`);
  }
}

function validateApplicableInternalLinkZeroVerdict(records, brief, problems) {
  const applicable = normalizeText(string(brief, 'stage_link_requirement_status', problems)) === 'applicable';
  const rawCount = brief.attributes.buyer_visible_internal_link_count;
  const count = Number(rawCount);
  if (!Number.isInteger(count) || count < 0) fail(problems, `${brief.source} buyer_visible_internal_link_count must be a non-negative integer`);
  const verdict = normalizeText(string(brief, 'buyer_visible_internal_links_verdict', problems));
  requireCanonicalMatch(records, 'buyer_visible_internal_link_count', problems);
  requireCanonicalMatch(records, 'buyer_visible_internal_links_verdict', problems);
  if (applicable && count === 0 && verdict !== 'block') fail(problems, `${brief.source} applicable internal-link requirement with zero buyer-visible links requires buyer_visible_internal_links_verdict=block and cannot be not-applicable or pass`);
}

function validateF13ArticleContracts({ records, brief, draft, review, publish, evidenceScope, evidenceRoot, fallbackContract, problems }) {
  for (const record of records.slice(1)) {
    const value = record.attributes.content_action;
    if (typeof value !== 'string' || !value.trim()) fail(problems, `${recordLabel(record)} missing required field content_action`);
    else if (normalizeText(value) !== normalizeText(brief.attributes.content_action)) fail(problems, `${recordLabel(record)} content_action must match Brief projection`);
  }
  const action = normalizeText(string(brief, 'content_action', problems));
  if (!CONTENT_ACTIONS.has(action)) fail(problems, `${brief.source} content_action must use create|update|merge|redirect|do-not-write`);
  for (const record of records.slice(1)) {
    const value = record.attributes.dominant_search_intent;
    if (typeof value !== 'string' || !value.trim()) fail(problems, `${recordLabel(record)} missing required field dominant_search_intent`);
    else if (normalizeText(value) !== normalizeText(brief.attributes.dominant_search_intent)) fail(problems, `${recordLabel(record)} dominant_search_intent must match Brief projection`);
  }
  const dominantIntent = requireMeaningfulString(brief, 'dominant_search_intent', problems, { minLength: 18 });
  if (semanticOverlap(dominantIntent, `${string(brief, 'primary_query', problems)} ${string(brief, 'dominant_task_contract', problems)}`).length < 2) fail(problems, `${brief.source} dominant_search_intent must materially match the primary query and dominant task contract`);

  requireCanonicalMatch([brief, publish], 'content_family_matches', problems, 'content_family_matches', 'exact-sequence');
  requireCanonicalMatch([brief, publish], 'content_family_singleton_verdict', problems, 'content_family_singleton_verdict', 'exact-scalar');
  const expectedFamilies = contentTypeFamilies(string(brief, 'expected_content_type', problems));
  for (const row of strings(brief, 'visual_decision_assets', problems, { allowEmpty: true })) {
    const assetType = normalizeText(row.split('|')[0] || '');
    if (!VISUAL_DECISION_ASSET_TYPES.has(assetType)) fail(problems, `${brief.source} visual_decision_assets asset type must use the closed enum diagram|decision-tree|decision-table|worksheet|annotated-product|process-flow: ${assetType || 'missing'}`);
  }

  for (const record of [brief, publish]) {
    const families = strings(record, 'content_family_matches', problems);
    if (families.length !== 1) fail(problems, `${record.source} content_family_matches must contain exactly one family`);
    if (families.length === 1 && (expectedFamilies.length !== 1 || normalizeText(families[0]) !== normalizeText(expectedFamilies[0]))) fail(problems, `${record.source} content_family_matches must equal the computed expected_content_type family`);
    if (normalizeText(string(record, 'content_family_singleton_verdict', problems)) !== 'pass') fail(problems, `${record.source} content_family_singleton_verdict must be pass`);
  }

  validateIntentClosureContracts(records, brief, problems);
  validateFaqContract(records, brief, problems);
  validateEvidenceOriginAndBuyerProof(records, brief, review, evidenceScope, evidenceRoot, problems);
  const collectionRows = validateCollectionRoutePolicyContracts(records, brief, review, evidenceScope, evidenceRoot, fallbackContract, problems);
  validateNormalizedPacketRedundancy(brief, draft, problems);
  validateUnverifiedTransmissionGate(brief, draft, collectionRows, fallbackContract, problems);
  validateApplicableInternalLinkZeroVerdict(records, brief, problems);
  validateRoundDecisionGateContract(records, brief, problems);
  validateTerminalAndPainClosure(records, brief, publish, problems);
  validateBodyEditorialTruth(brief, draft, review, evidenceScope, problems);
}

function validateExpectedContentType({ brief, draft, review, publish, evidenceScope, evidenceRoot, problems }) {
  requireCanonicalMatch([brief, draft], 'expected_content_type', problems, 'expected_content_type', 'exact-scalar');
  requireProjectionMatch(brief, 'expected_content_type', review, 'expected_content_type_snapshot', problems, 'exact-scalar');
  requireProjectionMatch(brief, 'expected_content_type', publish, 'expected_content_type_snapshot', problems, 'exact-scalar');
  const expected = requireMeaningfulString(brief, 'expected_content_type', problems, { minLength: 8 });
  const familyMatches = contentTypeFamilies(expected);
  const family = familyMatches.length === 1 ? familyMatches[0] : '';
  if (familyMatches.length !== 1) fail(problems, `${brief.source} expected_content_type must map to exactly one content family; matched ${familyMatches.length ? familyMatches.join(', ') : 'none'}`);
  else if (!draftImplementsContentType(family, draft.body)) fail(problems, `${draft.source} publishable body does not observably implement declared expected_content_type family ${family}`);

  for (const field of ['soft_path_route_safety_verdict', 'all_buyer_visible_cta_sections_evidence_parity_verdict', 'cross_cta_instruction_consistency_verdict']) {
    requireCanonicalMatch([review, publish], field, problems, field, 'exact-scalar');
    for (const record of [review, publish]) if (string(record, field, problems) !== 'pass') fail(problems, `${record.source} applicable article requires fatal ${field}=pass`);
  }
  requireCanonicalMatch([review, publish], 'serp_content_type_parity_verdict', problems, 'serp_content_type_parity_verdict', 'exact-scalar');
  requireCanonicalMatch([review, publish], 'body_content_family_implementation_verdict', problems, 'body_content_family_implementation_verdict', 'exact-scalar');
  for (const record of [review, publish]) if (string(record, 'body_content_family_implementation_verdict', problems) !== 'pass') fail(problems, `${record.source} body_content_family_implementation_verdict must be pass`);
  const serpParity = normalizeText(string(review, 'serp_content_type_parity_verdict', problems));
  const serpRefs = strings(brief, 'serp_format_evidence_refs', problems, { allowEmpty: true });
  const serpStatus = normalizeText(string(brief, 'serp_format_evidence_status', problems));
  const hasCompleteSerpEvidence = evidenceScope === 'production' && serpRefs.length > 0 && ['confirmed', 'inferred'].includes(serpStatus);
  const requiredSerpParity = hasCompleteSerpEvidence ? 'pass' : 'not-applicable';
  if (serpParity !== requiredSerpParity || normalizeText(string(publish, 'serp_content_type_parity_verdict', problems)) !== requiredSerpParity) fail(problems, `${review.source} serp_content_type_parity_verdict must be ${requiredSerpParity} for the available SERP evidence scope`);

  if (evidenceScope !== 'production' || !family) return;
  const refs = strings(brief, 'serp_format_evidence_refs', problems, { allowEmpty: true });
  const observedFamilies = new Set();
  for (const ref of refs) {
    const section = loadReferencedSection(ref, evidenceRoot);
    if (!section) continue;
    const fields = parseV12SerpFields(section, brief.source, ref, problems);
    const dominantType = fields.get('primary_query_dominant_result_type') || '';
    const observedMatches = contentTypeFamilies(dominantType);
    const observedFamily = observedMatches.length === 1 ? observedMatches[0] : '';
    if (!observedFamily) fail(problems, `${brief.source} SERP-format evidence ${ref} primary_query_dominant_result_type must map to exactly one supported content family; matched ${observedMatches.length ? observedMatches.join(', ') : 'none'} for ${dominantType}`);
    else observedFamilies.add(observedFamily);
  }
  if (refs.length && observedFamilies.size && !observedFamilies.has(family)) {
    fail(problems, `${brief.source} expected_content_type family ${family} conflicts with primary query dominant SERP family ${[...observedFamilies].join(', ')}`);
  }
}

function parseMarkdownTableCells(line) {
  return String(line).trim().replace(/^\||\|$/g, '').split('|').map((cell) => normalizeText(cell.replace(/[*_`]/g, ' ')));
}

function validateReviewEvidenceAxisVocabulary(review, problems) {
  for (const table of markdownTableBlocks(review.body)) {
    const lines = table.split('\n');
    const headers = parseMarkdownTableCells(lines[0]).map((header) => header.replace(/[ _-]+/g, ' '));
    const executionIndex = headers.indexOf('check execution status');
    const resultIndex = headers.indexOf('evidence result');
    const verdictIndex = headers.indexOf('gate verdict');
    if (executionIndex < 0 && resultIndex < 0 && verdictIndex < 0) continue;
    if (executionIndex < 0 || resultIndex < 0 || verdictIndex < 0) {
      fail(problems, `${review.source} evidence-axis table must include Check execution status, Evidence result, and Gate verdict columns together`);
      continue;
    }
    for (const line of lines.slice(2)) {
      const cells = parseMarkdownTableCells(line);
      for (const [label, index, allowed] of [
        ['execution', executionIndex, CANONICAL_EVIDENCE_EXECUTIONS],
        ['result', resultIndex, CANONICAL_EVIDENCE_RESULTS],
        ['verdict', verdictIndex, CANONICAL_GATE_VERDICTS],
      ]) {
        const value = cells[index] || '';
        if (!allowed.has(value)) fail(problems, `${review.source} evidence-axis table ${label} value must use the closed canonical allowlist; received ${value || 'missing'}`);
      }
    }
  }
  for (const match of review.body.matchAll(/`([^`\n]+)`/g)) {
    const assignment = /^([a-z0-9_-]+)\s*[:=]\s*([a-z0-9-]+)$/i.exec(match[1].trim());
    if (!assignment) continue;
    const field = assignment[1].toLowerCase().replace(/-/g, '_');
    const value = normalizeText(assignment[2]);
    const allowed = field.endsWith('check_execution_status') ? CANONICAL_EVIDENCE_EXECUTIONS
      : field.endsWith('evidence_result') ? CANONICAL_EVIDENCE_RESULTS
        : field.endsWith('gate_verdict') ? CANONICAL_GATE_VERDICTS : null;
    if (allowed && !allowed.has(value)) fail(problems, `${review.source} inline-code ${field} must use the closed canonical allowlist; received ${value}`);
  }
}

function validateArticleProjectionMatrix({ records, brief, draft, review, publish, evidenceScope, problems }) {
  requireCanonicalMatch(records, 'page_h1', problems, 'page_h1', 'exact-raw-scalar');
  for (const field of ['serp_primary_query', 'serp_primary_query_sample_size', 'serp_primary_query_dominant_result_type', 'serp_primary_query_dominant_result_count', 'serp_primary_query_dominance_threshold', 'serp_primary_query_dominance_verdict', 'serp_primary_query_result_type_counts', 'serp_supporting_query_result_type_rows', 'production_readiness_scope', 'cta_destination', 'cta_owner', 'cta_reference_check_execution_status', 'cta_reference_evidence_result', 'cta_reference_gate_verdict', 'cta_reference_evidence_refs', 'cta_reachability_check_execution_status', 'cta_reachability_evidence_result', 'cta_reachability_gate_verdict', 'cta_reachability_evidence_refs', 'cta_capability_check_execution_status', 'cta_capability_evidence_result', 'cta_capability_gate_verdict', 'cta_capability_evidence_refs', 'cta_fallback_route_contract', 'mobile_visual_check_execution_status', 'mobile_visual_evidence_result', 'mobile_visual_gate_verdict', 'mobile_visual_evidence_refs']) requireCanonicalMatch(records, field, problems);
  const deferredExpected = ['article-json-ld', 'canonical', 'html-lang'];
  for (const record of records) {
    const actual = strings(record, 'frontend_deferred_blocks', problems, { allowEmpty: true }).map(normalizeText).sort();
    if (JSON.stringify(actual) !== JSON.stringify(deferredExpected)) fail(problems, `${record.source} frontend_deferred_blocks must be the exact set html-lang, canonical, article-json-ld`);
  }

  for (const field of ['query_evidence_refs', 'buyer_task_evidence_refs', 'search_demand_evidence_refs', 'serp_format_evidence_refs']) {
    requireCanonicalMatch([brief, draft], field, problems, field, 'normalized-set');
    requireCanonicalMatch([review, publish], field, problems, field, 'normalized-set');
  }
  for (const record of records) {
    const gate = normalizeText(string(record, 'production_search_evidence_gate_verdict', problems));
    if (evidenceScope === 'synthetic-fixture' && gate !== 'block') fail(problems, `${record.source} synthetic fixture requires production_search_evidence_gate_verdict=block`);
    if (evidenceScope === 'production' && gate !== 'pass') fail(problems, `${record.source} production requires production_search_evidence_gate_verdict=pass`);
    for (const field of ['query_evidence_status', 'buyer_task_evidence_status', 'search_demand_evidence_status', 'serp_format_evidence_status']) {
      const status = normalizeText(string(record, field, problems));
      if (!FACT_STATUSES.has(status) && !(evidenceScope === 'synthetic-fixture' && status === 'confirmed-for-fixture-structure')) fail(problems, `${record.source} ${field} must use canonical fact-status vocabulary`);
    }
  }

  for (const field of ['pain_trigger', 'surface_problem', 'operational_friction', 'business_consequence', 'desired_decision']) {
    requireCanonicalMatch([brief, draft], field, problems);
    requireProjectionMatch(brief, field, review, `${field}_snapshot`, problems, 'exact-scalar');
    requireProjectionMatch(brief, field, publish, `${field}_snapshot`, problems, 'exact-scalar');
  }
  requireCanonicalMatch(records, 'pain_chain_contract', problems);
  requireCanonicalMatch([brief, draft], 'product_decision_map', problems, 'product_decision_map', 'keyed-row-map');
  requireProjectionMatch(brief, 'product_decision_map', review, 'product_decision_map_snapshot', problems, 'keyed-row-map');
  requireProjectionMatch(brief, 'product_decision_map', publish, 'product_decision_map_snapshot', problems, 'keyed-row-map');
  requireCanonicalMatch([brief, draft], 'internal_link_targets', problems, 'internal_link_targets', 'keyed-row-map');
  requireProjectionMatch(brief, 'internal_link_targets', review, 'internal_link_targets_snapshot', problems, 'keyed-row-map');
  requireProjectionMatch(brief, 'internal_link_targets', publish, 'internal_link_targets_snapshot', problems, 'keyed-row-map');
  requireCanonicalMatch([brief, draft], 'internal_link_buyer_task_contracts', problems, 'internal_link_buyer_task_contracts', 'keyed-row-map');
  requireProjectionMatch(brief, 'internal_link_buyer_task_contracts', review, 'internal_link_buyer_task_contracts_snapshot', problems, 'keyed-row-map');
  requireProjectionMatch(brief, 'internal_link_buyer_task_contracts', publish, 'internal_link_buyer_task_contracts_snapshot', problems, 'keyed-row-map');
  requireCanonicalMatch([brief, draft], 'cta_required_inputs', problems, 'cta_required_inputs', 'exact-sequence');
  requireProjectionMatch(brief, 'cta_required_inputs', review, 'cta_required_inputs_snapshot', problems, 'exact-sequence');
  requireProjectionMatch(brief, 'cta_required_inputs', publish, 'cta_required_inputs_snapshot', problems, 'exact-sequence');
  requireCanonicalMatch([brief, draft, review], 'first_round_input_specifications', problems, 'first_round_input_specifications', 'exact-sequence');
  requireProjectionMatch(brief, 'first_round_input_specifications', publish, 'first_round_input_specifications_snapshot', problems, 'exact-sequence');
  requireCanonicalMatch([brief, draft, review], 'cta_buyer_visible_capability_proofs', problems, 'cta_buyer_visible_capability_proofs', 'keyed-row-map');
  requireProjectionMatch(brief, 'cta_buyer_visible_capability_proofs', publish, 'cta_buyer_visible_capability_proofs_snapshot', problems, 'keyed-row-map');

  for (const [draftField, publishField] of [
    ['article_title', 'published_article_title'], ['slug', 'published_slug'], ['meta_description', 'published_meta_description'], ['excerpt', 'published_excerpt'],
  ]) requireProjectionMatch(draft, draftField, publish, publishField, problems, 'exact-scalar');
  validatePublishSearchFieldTable(publish, problems);
}

function validatePublishSearchFieldTable(publish, problems) {
  const section = markdownSectionByHeading(publish.body, /proposed search fields|approved search fields/i);
  if (!section) {
    fail(problems, `${publish.source} must contain a Proposed/Approved search fields section whose table projects the canonical search fields`);
    return;
  }
  const rows = new Map();
  for (const line of section.split('\n')) {
    if (!/^\s*\|/.test(line) || /^\s*\|?\s*:?-{3,}/.test(line)) continue;
    const cells = line.trim().replace(/^\||\|$/g, '').split('|').map((cell) => cell.trim().replace(/^`|`$/g, ''));
    if (cells.length < 2) continue;
    const label = normalizeText(cells[0]);
    if (label === 'field') continue;
    if (rows.has(label)) fail(problems, `${publish.source} search-fields table contains duplicate row ${cells[0]}`);
    rows.set(label, cells[1]);
  }
  for (const [label, field] of [
    ['seo title', 'published_article_title'],
    ['meta description', 'published_meta_description'],
    ['h1', 'page_h1'],
    ['excerpt', 'published_excerpt'],
  ]) {
    const actual = rows.get(label);
    const expected = string(publish, field, problems);
    if (actual === undefined) fail(problems, `${publish.source} search-fields table must contain ${label}`);
    else if (actual !== expected) fail(problems, `${publish.source} search-fields table ${label} must exactly match frontmatter ${field}`);
  }
}

function h2SectionRanges(body) {
  const lines = String(body || '').split('\n');
  const sections = [];
  for (let index = 0; index < lines.length; index += 1) {
    const match = /^##\s+(.+)$/.exec(lines[index]);
    if (!match) continue;
    let end = lines.length;
    for (let cursor = index + 1; cursor < lines.length; cursor += 1) {
      if (/^##\s+/.test(lines[cursor])) { end = cursor; break; }
    }
    sections.push({ heading: match[1], markdown: lines.slice(index, end).join('\n') });
  }
  return sections;
}

function markdownTableBlocks(section) {
  const lines = String(section || '').split('\n');
  const tables = [];
  for (let index = 0; index + 2 < lines.length; index += 1) {
    if (!lines[index].includes('|') || !/^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$/.test(lines[index + 1])) continue;
    const table = [lines[index], lines[index + 1]];
    let cursor = index + 2;
    while (cursor < lines.length && lines[cursor].includes('|') && lines[cursor].trim()) { table.push(lines[cursor]); cursor += 1; }
    tables.push(table.join('\n'));
    index = cursor - 1;
  }
  return tables;
}

function validateFatalVerdictConsistency(records, brief, draft, review, evidenceScope, evidenceRoot, problems) {
  for (const [field, rawValue] of Object.entries(review.attributes)) {
    if (!field.endsWith('_verdict')) continue;
    const value = typeof rawValue === 'string' ? rawValue.trim() : '';
    if (!CANONICAL_VERDICTS.has(value)) {
      fail(problems, `${review.source} ${field} must use the closed verdict enum pass, block, or not-applicable`);
    }
  }

  const fatalFields = [
    'query_contract_verdict', 'dominant_task_verdict', 'stage_contract_verdict', 'buyer_role_scope_verdict',
    'cross_role_delegation_verdict', 'cannibalization_verdict', 'information_gain_artifact_verdict',
    'information_gain_market_verdict', 'article_decision_sequence_verdict', 'conversion_surface_map_verdict',
    'hierarchy_scan_verdict', 'semantic_emphasis_verdict', 'cta_route_transmission_verdict', 'section_information_gain_verdict', 'normalized_field_set_redundancy_verdict', 'reviewer_separation_verdict', 'overall_verdict',
  ];
  const values = fatalFields.map((field) => [field, normalizeText(string(review, field, problems))]);
  const hasBlock = values.some(([, value]) => value === 'block');
  if (hasBlock) {
    for (const record of records) {
      if (normalizeText(string(record, 'fatal_gate_verdict', problems)) === 'pass') fail(problems, `${record.source} fatal_gate_verdict=pass cannot coexist with a fatal review block`);
      if (normalizeText(string(record, 'production_readiness', problems)) === 'ready') fail(problems, `${record.source} production_readiness=ready cannot coexist with a fatal review block`);
    }
    if (normalizeText(string(review, 'overall_verdict', problems)) === 'pass') fail(problems, `${review.source} overall_verdict=pass cannot coexist with a fatal review block`);
  }
  const claimsFatalPass = records.some((record) => normalizeText(string(record, 'fatal_gate_verdict', problems)) === 'pass');
  const claimsProductionReady = records.some((record) => normalizeText(string(record, 'production_readiness', problems)) === 'ready');
  if (evidenceScope === 'production' && (claimsFatalPass || claimsProductionReady)) {
    for (const [field, value] of values) if (value !== 'pass' && value !== 'not-applicable') fail(problems, `${review.source} production-ready or fatal-pass package requires applicable fatal ${field}=pass`);
  }

  const mobileExecution = string(review, 'mobile_visual_check_execution_status', problems);
  const mobileResult = string(review, 'mobile_visual_evidence_result', problems);
  const mobileGate = string(review, 'mobile_visual_gate_verdict', problems);
  const mobileRefs = strings(review, 'mobile_visual_evidence_refs', problems, { allowEmpty: true });
  const ready = records.some((record) => normalizeText(string(record, 'production_readiness', problems)) === 'ready');
  if (evidenceScope === 'synthetic-fixture') {
    if (mobileExecution !== 'not-run' || mobileResult !== 'missing' || mobileGate !== 'block' || mobileRefs.length) fail(problems, `${review.source} synthetic mobile visual axis must be not-run + missing + block + empty refs`);
  } else if (ready) {
    if (mobileExecution !== 'executed' || mobileResult !== 'confirmed' || mobileGate !== 'pass' || !mobileRefs.length) fail(problems, `${review.source} production-ready mobile visual axis requires executed + confirmed + pass + evidence refs`);
    const ownerPage = string(brief, 'owner_page', problems);
    const expectedOwner = string(review, 'reviewer_identity', problems);
    const articleTitle = string(draft, 'article_title', problems);
    validateLocalEvidenceRefs(mobileRefs, review.source, 'mobile_visual_evidence_refs', evidenceRoot, problems, { requireFragment: true, regularNonSymlink: true, verifyFragment: true });
    validateProductionEvidenceRefs(mobileRefs, review.source, 'mobile_visual_evidence_refs', evidenceRoot, problems, {
      expectedKinds: ['mobile-readability'],
      expectedCheckId: 'mobile-readability',
      expectedOwner,
      expectedTargets: [{ url: ownerPage, role: 'article-page', task: `320px mobile readability review for ${articleTitle}` }],
      requiredExtraFields: ['accountable_owner', 'acceptance_criteria', 'capability_acceptance', 'viewport_width_px', 'render_target', 'readability_result', 'screenshot_or_trace_ref'],
      requireStructuredSection: true,
    });
    for (const ref of mobileRefs) {
      const section = loadReferencedSection(ref, evidenceRoot) || '';
      const fields = parseStructuredEvidenceSection(section);
      if (fields.get('render_target') && normalizeEndpointForComparison(fields.get('render_target')) !== normalizeEndpointForComparison(ownerPage)) {
        fail(problems, `${review.source} mobile_visual_evidence_refs evidence section ${ref} render_target must exactly match canonical owner_page ${ownerPage}`);
      }
    }
  }
}


function validateStableActorIdentityContract(records, brief, review, evidenceScope, evidenceRoot, problems) {
  for (const field of ['author_id', 'producer_id', 'independent_reviewer_id', 'remediation_participant_ids', 'identity_provenance_evidence_refs', 'identity_provenance_observed_at', 'identity_provenance_reviewed_at', 'identity_provenance_review_ceiling', 'reviewer_separation_verdict']) {
    requireCanonicalMatch(records, field, problems, field, field.endsWith('_ids') || field.endsWith('_refs') ? 'exact-sequence' : 'exact-scalar');
  }
  const authorId = string(brief, 'author_id', problems);
  const producerId = string(brief, 'producer_id', problems);
  const reviewerId = string(brief, 'independent_reviewer_id', problems);
  const remediationIds = strings(brief, 'remediation_participant_ids', problems, { allowEmpty: true });
  const refs = strings(brief, 'identity_provenance_evidence_refs', problems, { allowEmpty: true });
  const separation = normalizeText(string(review, 'reviewer_separation_verdict', problems));
  for (const [field, value] of [['author_id', authorId], ['producer_id', producerId], ['independent_reviewer_id', reviewerId]]) requireStableActorId(value, brief.source, field, problems);
  for (const [index, value] of remediationIds.entries()) requireStableActorId(value, brief.source, `remediation_participant_ids[${index}]`, problems);
  const participantIds = [authorId, producerId, ...remediationIds].map(normalizeText);
  if (participantIds.includes(normalizeText(reviewerId))) fail(problems, `${brief.source} independent_reviewer_id must differ from author_id, producer_id, and every remediation_participant_id`);
  if (new Set([authorId, producerId, reviewerId, ...remediationIds].map(normalizeText)).size !== 3 + remediationIds.length) fail(problems, `${brief.source} stable actor IDs must be unique across author, producer, reviewer, and remediation participants`);
  if (evidenceScope === 'synthetic-fixture') {
    if (refs.length) fail(problems, `${brief.source} synthetic fixture identity_provenance_evidence_refs must be empty`);
    if (separation !== 'block') fail(problems, `${review.source} synthetic fixture reviewer_separation_verdict must remain block`);
    return;
  }
  if (separation !== 'pass') fail(problems, `${review.source} production reviewer_separation_verdict must be pass`);
  const identityObservedAt = string(brief, 'identity_provenance_observed_at', problems);
  const identityReviewedAt = string(brief, 'identity_provenance_reviewed_at', problems);
  const identityReviewCeiling = string(brief, 'identity_provenance_review_ceiling', problems);
  requireFreshIsoDate(identityObservedAt, brief.source, 'identity_provenance_observed_at', problems, IDENTITY_PROVENANCE_MAX_AGE_DAYS);
  if (!/T\d{2}:\d{2}:\d{2}/.test(identityObservedAt)) fail(problems, `${brief.source} identity_provenance_observed_at must be an explicit ISO timestamp`);
  requireIsoDate(identityReviewedAt, brief.source, 'identity_provenance_reviewed_at', problems);
  requireIsoDate(identityReviewCeiling, brief.source, 'identity_provenance_review_ceiling', problems);
  requireDateNoLaterThan(identityObservedAt, identityReviewedAt, brief.source, 'identity_provenance_observed_at', 'identity_provenance_reviewed_at', problems);
  requireDateNoLaterThan(identityReviewedAt, identityReviewCeiling, brief.source, 'identity_provenance_reviewed_at', 'identity_provenance_review_ceiling', problems);
  requireDateNoLaterThan(identityReviewedAt, string(review, 'reviewed_at', problems), brief.source, 'identity_provenance_reviewed_at', 'reviewed_at', problems);
  requireDateNoLaterThan(identityReviewCeiling, string(review, 'reviewed_at', problems), brief.source, 'identity_provenance_review_ceiling', 'reviewed_at', problems);
  if (!refs.length) fail(problems, `${brief.source} production identity_provenance_evidence_refs requires at least one fragment-bound record`);
  validateLocalEvidenceRefs(refs, brief.source, 'identity_provenance_evidence_refs', evidenceRoot, problems, { requireFragment: true, regularNonSymlink: true, verifyFragment: true });
  for (const ref of refs) {
    const section = loadReferencedSection(ref, evidenceRoot);
    if (!section) continue;
    const fields = parseEvidenceScalarFields(section);
    for (const [field, expected] of [
      ['package_id', string(brief, 'package_id', problems)], ['author_id', authorId], ['producer_id', producerId], ['independent_reviewer_id', reviewerId],
    ]) {
      if (!fields.get(field)) fail(problems, `${brief.source} identity provenance ${ref} requires ${field}`);
      else if (normalizeText(fields.get(field)) !== normalizeText(expected)) fail(problems, `${brief.source} identity provenance ${ref} ${field} must exactly match the canonical package identity`);
    }
    for (const field of ['verification_method', 'observed_at']) if (!fields.get(field)) fail(problems, `${brief.source} identity provenance ${ref} requires ${field}`);
    if (fields.get('observed_at')) {
      requireFreshIsoDate(fields.get('observed_at'), brief.source, `identity provenance ${ref} observed_at`, problems, IDENTITY_PROVENANCE_MAX_AGE_DAYS);
      requireDateNoLaterThan(fields.get('observed_at'), string(review, 'reviewed_at', problems), brief.source, `identity provenance ${ref} observed_at`, 'reviewed_at', problems);
      if (fields.get('observed_at') !== identityObservedAt) fail(problems, `${brief.source} identity provenance ${ref} observed_at must exactly match identity_provenance_observed_at`);
      const { pathPart } = splitLocalRef(ref);
      const target = resolve(evidenceRoot, pathPart);
      if (existsSync(target)) {
        try {
          const parsed = parseArticleMarkdownFrontMatter(readFileSync(realpathSync(target), 'utf8'), { source: target });
          const recordObservedAt = parsed.attributes.observed_at || parsed.attributes.date || '';
          const recordCapturedAt = parsed.attributes.captured_at || '';
          if (!recordObservedAt) fail(problems, `${brief.source} identity provenance ${ref} evidence record requires observed_at`);
          else if (recordObservedAt !== fields.get('observed_at')) fail(problems, `${brief.source} identity provenance ${ref} section observed_at must exactly match evidence-record observed_at/date`);
          if (!recordCapturedAt) fail(problems, `${brief.source} identity provenance ${ref} evidence record requires captured_at`);
          else if (recordCapturedAt !== fields.get('observed_at')) fail(problems, `${brief.source} identity provenance ${ref} evidence-record captured_at must exactly match section observed_at`);
        } catch {}
      }
    }
    const evidenceRemediation = exactSnapshotArrayFromEvidence(fields.get('remediation_participant_ids') || '[]').map(normalizeText);
    const canonicalRemediation = remediationIds.map(normalizeText);
    if (evidenceRemediation.length !== canonicalRemediation.length || evidenceRemediation.some((id, index) => id !== canonicalRemediation[index])) fail(problems, `${brief.source} identity provenance ${ref} remediation_participant_ids must exactly match the canonical package`);
  }
}

function validateCanonicalArticlePackageRecords({ records, brief, draft, review, publish, packageRoot, problems }) {
  const recordTypes = ['article-brief', 'article-draft', 'article-quality-review', 'article-publish-record'];
  records.forEach((record, index) => {
    rejectDeprecatedArticlePackageFields(record, problems);
    validateCanonicalTemplateProjection(record, recordTypes[index], problems);
  });
  validateReviewEvidenceAxisVocabulary(review, problems);
  validateStableActorIdentityContract(records, brief, review, string(brief, 'evidence_scope', problems), packageRoot, problems);
  validateInformationGainAndRedundancyVerdicts(records, brief, review, problems);
  validateFatalVerdictConsistency(records, brief, draft, review, string(brief, 'evidence_scope', problems), packageRoot, problems);

  for (const field of ['package_id', 'brief_id']) requireCanonicalMatch(records, field, problems);
  for (const field of ['draft_id']) requireCanonicalMatch([draft, review, publish], field, problems);
  for (const field of ['review_id']) requireCanonicalMatch([review, publish], field, problems);
  for (const field of [
    'evidence_scope', 'supported_content_languages', 'target_content_language', 'target_market', 'language_gate_verdict',
    'primary_query', 'supporting_query_variants', 'excluded_query_modifiers', 'intent_class', 'stage', 'dominant_task_contract',
    'commercial_commitment', 'stage_intake_contract', 'first_round_inquiry_inputs', 'second_round_inquiry_inputs', 'second_round_input_relationships', 'stage_primary_outcome', 'stage_cta_mode',
    'stage_required_link_roles', 'stage_sales_qualification_requirement', 'role_handoff_contracts', 'inventory_zero_result_evidence_refs',
    'information_gain_artifact_status', 'information_gain_artifact_refs', 'market_information_gain_status', 'information_gain_market_refs',
    'serp_primary_query_result_type_counts', 'article_decision_sequence_map', 'article_decision_sequence_verdict',
    'conversion_surface_map', 'conversion_surface_map_verdict', 'buyer_visible_cta_inventory', 'production_readiness_scope',
    'structure_review_verdict', 'production_evidence_review_verdict', 'fatal_gate_verdict', 'production_readiness', 'release_decision', 'operation_mode',
  ]) requireCanonicalMatch(records, field, problems);
  requireCanonicalMatch([brief, draft], 'content_purpose', problems);
  requireCanonicalMatch([brief, draft], 'indexing_intent', problems);
  validateCanonicalDecisionAndConversionMaps(records, brief, draft, problems);
  validateCtaMeasurementPlan(records, brief, review, publish, packageRoot, problems);
  const productionReadinessScope = normalizeText(string(brief, 'production_readiness_scope', problems));
  if (!PRODUCTION_READINESS_SCOPES.has(productionReadinessScope)) fail(problems, `${brief.source} production_readiness_scope must be cms-draft-content-contract`);

  const packageId = string(brief, 'package_id', problems);
  const briefId = string(brief, 'brief_id', problems);
  const evidenceScope = string(brief, 'evidence_scope', problems);
  if (!EVIDENCE_SCOPES.has(evidenceScope)) fail(problems, `${brief.source} evidence_scope must be synthetic-fixture or production`);
  if (/^SYNTH(?:ETIC)?[-_]/i.test(packageId) && evidenceScope !== 'synthetic-fixture') fail(problems, `${brief.source} synthetic package_id requires evidence_scope=synthetic-fixture`);
  if (records.some((record) => string(record, 'evidence_scope', problems) !== evidenceScope)) fail(problems, 'evidence_scope must match across all records');

  validateLanguageQueryIntent(records, problems);
  validateObviousSearchStuffing(brief, draft, problems);
  validateStageSpecificIntake(records, problems);
  validateTitleHierarchyAndReviewGates(brief, draft, review, problems);
  validateBoundedPainLanguage(brief, draft, evidenceScope, problems);
  validateCanonicalStageMatrix(records, problems);
  validateCanonicalStatusAndReviewContracts(records, brief, draft, review, publish, evidenceScope, packageRoot, problems);
  validateCanonicalCannibalization(brief, evidenceScope, packageRoot, problems);
  validateProductionSnapshotArtifacts(brief, review, evidenceScope, packageRoot, problems);
  checkHeadingStructure(draft, problems);
  const formatProfile = checkAllinCmsFormats(draft, review, problems);
  validateNoRepeatedFullSentences(draft, problems);
  validateUnsupportedOutcomeClaims(draft, problems);
  validateBuyerVisibleProductClaimLedger(brief, draft, publish, evidenceScope, packageRoot, problems);
  validateIcpAndCtaDataContracts(records, brief, draft, review, publish, evidenceScope, packageRoot, problems);
  validateBuyerVisibleOpeningIcp(brief, draft, problems);
  validateTransmissionActionInventory(records, brief, draft, problems);
  validateV10Contracts({ records, brief, draft, review, publish, evidenceScope, evidenceRoot: packageRoot, formatProfile, problems });
  validateV11Contracts({ records, brief, draft, review, publish, evidenceScope, evidenceRoot: packageRoot, problems });
  validateCanonicalBuyerContracts(brief, draft, evidenceScope, packageRoot, problems);
  validateCanonicalQualificationAndCta(brief, draft, review, publish, problems);
  validateCanonicalProgressiveQualification(records, brief, draft, publish, problems);
  validateCanonicalSemanticEmphasis(brief, draft, review, problems);
  const fallbackContract = validateV14BuyerFacingConversionContracts(records, brief, draft, review, packageRoot, evidenceScope, problems);
  validateBuyerVisibleCtaInventory(records, brief, draft, packageRoot, evidenceScope, fallbackContract, problems);
  validateControlNarrativeRouteSafety({ brief, draft, publish, fallbackContract, problems });
  validateDecisionAssetNarrativeParity(brief, draft, problems);
  validateExpectedContentType({ brief, draft, review, publish, evidenceScope, evidenceRoot: packageRoot, problems });
  validateF13ArticleContracts({ records, brief, draft, review, publish, evidenceScope, evidenceRoot: packageRoot, fallbackContract, problems });
  validateArticleProjectionMatrix({ records, brief, draft, review, publish, evidenceScope, problems });
  validateFirstRoundInputSpecifications({ records, brief, draft, publish, evidenceRoot: packageRoot, problems });
  validateBuyerVisibleCapabilityProofs({ brief, draft, publish, evidenceScope, evidenceRoot: packageRoot, problems });

  const articleTitle = string(draft, 'article_title', problems);
  rejectTemplatePlaceholder(articleTitle, draft.source, 'article_title', problems);
  const directAnswer = requireMeaningfulString(draft, 'direct_answer', problems, { minLength: 18 });
  const opening = markdownPlainText(draft.body.split(/^##\s+/m)[0]);
  if (semanticOverlap(opening, `${directAnswer} ${string(draft, 'direct_answer_object', problems)}`).length < 2) fail(problems, `${draft.source} direct_answer must be visibly placed within the complete opening block before the first H2`);
  const ctaApplicable = normalizeText(string(brief, 'cta_input_collection_applicability', problems)) === 'applicable';
  const linkApplicable = normalizeText(string(brief, 'stage_link_requirement_status', problems)) === 'applicable';
  const stageIntake = normalizeText(string(brief, 'stage_intake_contract', problems));
  const minimumCtaInputs = stageIntake === 'validate-technical' ? 4 : (stageIntake === 'buy-commercial' ? 3 : 1);
  if (ctaApplicable && strings(brief, 'cta_required_inputs', problems).length < minimumCtaInputs) fail(problems, `${brief.source} cta_required_inputs requires at least ${minimumCtaInputs} concrete input${minimumCtaInputs === 1 ? '' : 's'} for ${stageIntake}`);
  if (ctaApplicable) {
    const ctaDestination = string(brief, 'cta_destination', problems);
    if (ctaDestination !== 'not-applicable' && !draft.body.includes(ctaDestination)) fail(problems, `${draft.source} visible CTA must include the canonical cta_destination`);
  }
  const internalLinkGatesPass = internalLinkPublicationGatesPass(brief, problems);
  for (const target of linkApplicable ? strings(brief, 'internal_link_targets', problems) : []) {
    const [, url, anchor] = target.split('|').map((part) => part.trim());
    if (!url || !anchor) fail(problems, `${brief.source} planned internal-link target requires a URL and anchor: ${target}`);
    else if (internalLinkGatesPass && !draft.body.includes(`](${url})`)) fail(problems, `${draft.source} planned internal-link target must appear as an actual Markdown link when all gates pass: ${url}`);
    else if (!internalLinkGatesPass && draft.body.includes(url)) fail(problems, `${draft.source} planned internal-link target must not be buyer-visible while any internal-link gate is not pass: ${url}`);
    if (GENERIC_ANCHORS.has(normalizeText(anchor))) fail(problems, `${brief.source} internal-link anchor must not be generic: ${anchor}`);
  }

  for (const record of records) {
    validateCanonicalLocalEvidence(record, evidenceScope, packageRoot, problems);
    validateCanonicalEvidenceAxes(record, evidenceScope, packageRoot, problems);
  }

  const releaseDecision = string(publish, 'release_decision', problems);
  const operationMode = string(publish, 'operation_mode', problems);
  if (evidenceScope === 'synthetic-fixture') {
    const expected = new Map([
      ['fixture_contract_status', 'confirmed'], ['structure_review_verdict', 'pass'], ['production_evidence_review_verdict', 'block'],
      ['fatal_gate_verdict', 'block'], ['production_readiness', 'block'], ['release_decision', 'blocked'], ['operation_mode', 'not-run'],
    ]);
    for (const record of records) for (const [field, value] of expected) if (field in record.attributes && string(record, field, problems) !== value) fail(problems, `${record.source} synthetic fixture requires ${field}=${value}`);
    for (const [field, value] of [
      ['cms_mutation_status', 'not-run'], ['backend_readback_status', 'not-run'], ['editor_reopen_status', 'not-run'],
      ['anonymous_frontend_status', 'not-run'], ['desktop_acceptance_status', 'not-run'], ['mobile_acceptance_status', 'not-run'], ['image_fetch_decode_status', 'not-run'],
      ['html_lang_status', 'deferred-block'], ['canonical_status', 'deferred-block'], ['article_json_ld_status', 'deferred-block'],
      ['final_dom_image_alt_renderer_status', 'block'], ['publication_status', 'not-published'], ['api_write_status', 'not-run'],
      ['authorization_status', 'not-run'], ['frontend_acceptance_status', 'not-run'], ['cms_action_status', 'not-run'],
    ]) if (string(publish, field, problems) !== value) fail(problems, `${publish.source} synthetic fixture requires ${field}=${value}`);
    if (publish.attributes.rollback_ready !== false) fail(problems, `${publish.source} synthetic fixture requires rollback_ready=false`);
  } else {
    for (const record of records) {
      if (string(record, 'structure_review_verdict', problems) !== 'pass') fail(problems, `${record.source} production requires structure_review_verdict=pass`);
      if (string(record, 'production_evidence_review_verdict', problems) !== 'pass') fail(problems, `${record.source} production requires production_evidence_review_verdict=pass`);
      if (string(record, 'fatal_gate_verdict', problems) !== 'pass') fail(problems, `${record.source} production requires fatal_gate_verdict=pass`);
      if (string(record, 'production_readiness', problems) !== 'ready') fail(problems, `${record.source} production requires production_readiness=ready`);
    }
    if (!PRODUCTION_RELEASE_DECISIONS.has(releaseDecision)) fail(problems, `${publish.source} production release_decision must be ready-for-cms-draft or published`);
    if (!PRODUCTION_OPERATION_MODES.has(operationMode)) fail(problems, `${publish.source} production operation_mode must be dry-run, draft, publish, or update`);
    if (releaseDecision === 'ready-for-cms-draft') {
      if (operationMode !== 'dry-run') fail(problems, `${publish.source} ready-for-cms-draft production package requires operation_mode=dry-run`);
      for (const [field, expected] of [
        ['publication_status', 'not-published'], ['api_write_status', 'not-run'], ['authorization_status', 'not-run'],
        ['cms_action_status', 'not-run'], ['cms_mutation_status', 'not-run'], ['backend_readback_status', 'not-run'],
        ['editor_reopen_status', 'not-run'], ['anonymous_frontend_status', 'not-run'], ['desktop_acceptance_status', 'not-run'],
        ['mobile_acceptance_status', 'not-run'], ['image_fetch_decode_status', 'not-run'], ['frontend_acceptance_status', 'not-run'],
        ['final_dom_image_alt_renderer_status', 'block'], ['html_lang_status', 'deferred-block'],
        ['canonical_status', 'deferred-block'], ['article_json_ld_status', 'deferred-block'],
      ]) if (string(publish, field, problems) !== expected) fail(problems, `${publish.source} ready-for-cms-draft production package requires ${field}=${expected}`);
      if (publish.attributes.rollback_ready !== false) fail(problems, `${publish.source} ready-for-cms-draft production package requires rollback_ready=false`);
    }
    if (releaseDecision === 'published') {
      if (operationMode !== 'publish') fail(problems, `${publish.source} published production package requires operation_mode=publish`);
      for (const field of ['cms_mutation_status', 'backend_readback_status', 'editor_reopen_status', 'anonymous_frontend_status', 'desktop_acceptance_status', 'mobile_acceptance_status', 'image_fetch_decode_status', 'html_lang_status', 'canonical_status', 'article_json_ld_status', 'final_dom_image_alt_renderer_status', 'api_write_status', 'authorization_status', 'frontend_acceptance_status', 'cms_action_status']) if (string(publish, field, problems) !== 'pass') fail(problems, `${publish.source} published production package requires ${field}=pass`);
      if (string(publish, 'publication_status', problems) !== 'published') fail(problems, `${publish.source} published production package requires publication_status=published`);
      if (publish.attributes.rollback_ready !== true) fail(problems, `${publish.source} published production package requires rollback_ready=true`);
      validatePublishedLifecycleEvidenceRefs(publish.attributes.publication_lifecycle_evidence_rows, publish, packageRoot, string(review, 'reviewed_at', problems), problems);
    }
  }

  return { ok: problems.length === 0, problems, packageId, briefId, releaseDecision, evidenceScope, formatProfile: ALLINCMS_ARTICLE_FORMAT_SUPPORT.profile };
}

export const articlePackageValidatorTestHooks = Object.freeze({
  hasPrematureDecisionPromise,
  hasDecisionOutcomeLanguage,
  hasPacketTransferIntent,
  isClauseLocalSafeTransfer,
  canonicalComparable,
  collectCandidateDecisionSurfaces,
  validateTransmissionActionInventory,
  validateStructuredEvidenceSection,
  validateBuyerVisibleOpeningIcp,
  validateInformationGainAndRedundancyVerdicts,
  validateNormalizedPacketRedundancy,
  validatePublishedLifecycleEvidenceRefs,
  validateProductionSearchDemandEvidence,
  validateStableActorIdentityContract,
  validateCtaPolicyTemporalContract,
  validateCtaPolicyEvidenceProjection,
  parseCollectionPolicyRows,
});

export function validateArticlePackage({ briefPath, draftPath, reviewPath, publishPath }) {
  const problems = [];
  const packageRoot = dirname(resolve(briefPath));
  let realPackageRoot = packageRoot;
  try { realPackageRoot = realpathSync(packageRoot); }
  catch (error) { fail(problems, `${packageRoot} package root realpath cannot be resolved: ${error.message}`); }
  const brief = readRecord(briefPath, 'article-brief', problems, packageRoot, realPackageRoot);
  const rawDraft = readRecord(draftPath, 'article-draft', problems, packageRoot, realPackageRoot);
  const review = readRecord(reviewPath, 'article-quality-review', problems, packageRoot, realPackageRoot);
  const publish = readRecord(publishPath, 'article-publish-record', problems, packageRoot, realPackageRoot);
  let publishableBody = '';
  try {
    publishableBody = extractPublishableArticleMarkdown(rawDraft.body, { cmsTitleSeparatelySupplied: true });
  } catch (error) {
    fail(problems, `${rawDraft.source} publishable-body extraction failed closed: ${error.message}`);
  }
  const draft = { ...rawDraft, body: publishableBody };
  const records = [brief, rawDraft, review, publish];
  return validateCanonicalArticlePackageRecords({ records, brief, draft, review, publish, packageRoot, problems });
}
function cliArgs(argv) {
  const get = (name) => {
    const index = argv.indexOf(`--${name}`);
    return index < 0 ? '' : argv[index + 1] || '';
  };
  return {
    briefPath: get('brief'),
    draftPath: get('draft'),
    reviewPath: get('review'),
    publishPath: get('publish'),
  };
}

function canonicalExecutablePath(value) {
  if (!value) return '';
  const absolute = resolve(value);
  try { return realpathSync(absolute); }
  catch { return absolute; }
}

const isMain = canonicalExecutablePath(fileURLToPath(import.meta.url)) === canonicalExecutablePath(process.argv[1] || '');
if (isMain) {
  try {
    const paths = cliArgs(process.argv.slice(2));
    if (Object.values(paths).some((value) => !value)) {
      throw new Error('Usage: node scripts/validate-article-package.mjs --brief <brief.md> --draft <draft.md> --review <review.md> --publish <publish-record.md>');
    }
    const result = validateArticlePackage(paths);
    if (!result.ok) {
      for (const problem of result.problems) console.error(`BLOCK: ${problem}`);
      console.error(`ARTICLE_PACKAGE_BLOCK: ${result.problems.length} problem(s)`);
      process.exitCode = 1;
    } else {
      console.log(`ARTICLE_PACKAGE_STRUCTURE_PASS: package=${result.packageId} brief=${result.briefId} decision=${result.releaseDecision} format_profile=${result.formatProfile} factual_evidence=not_verified`);
    }
  } catch (error) {
    console.error(`BLOCK: article-package validator CLI failed closed: ${error instanceof Error ? error.message : String(error)}`);
    console.error('ARTICLE_PACKAGE_BLOCK: CLI execution failed');
    process.exitCode = 1;
  }
}
