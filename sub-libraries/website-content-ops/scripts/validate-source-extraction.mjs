#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { validateJsonSchema, validateJsonSchemaDefinition } from './json-schema-lite.mjs';
import { validateRuntimeScopeBinding, validateTaskRuntimePath } from './runtime-scope.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const schema = JSON.parse(readFileSync(join(here, '..', 'SCHEMAS', 'source-extraction.schema.json'), 'utf8'));
const schemaDefinitionProblems = validateJsonSchemaDefinition(schema);
const forbiddenKeys = new Set(['cookie','cookies','authorization_header','access_token','refresh_token','session_token','bearer_token','jwt']);
const usableClearances = new Set(['approved', 'not-applicable']);

function object(value) { return value && typeof value === 'object' && !Array.isArray(value); }
function unique(values) { return new Set(values).size === values.length; }

export function validateSourceExtractionSchema() { return [...schemaDefinitionProblems]; }

export function validateSourceExtraction(artifact, { now = new Date() } = {}) {
  const problems = schemaDefinitionProblems.map((issue) => `schema definition: ${issue}`);
  const nowMs = now instanceof Date ? now.getTime() : Date.parse(now);
  if (!Number.isFinite(nowMs)) return { ok: false, problems: ['validation now must be a valid date-time'] };
  if (!object(artifact)) return { ok: false, problems: ['source extraction must be a JSON object'] };
  for (const issue of validateJsonSchema(artifact, schema)) problems.push(`schema: ${issue}`);

  function scan(value, path = '$') {
    if (Array.isArray(value)) return value.forEach((item, index) => scan(item, `${path}[${index}]`));
    if (!object(value)) {
      if (typeof value === 'string') {
        if (/\bBearer\s+[A-Za-z0-9._~-]+/i.test(value)) problems.push(`${path} contains a bearer credential`);
        if (/\b(?:cookie|set-cookie)\s*:/i.test(value)) problems.push(`${path} contains a cookie header`);
      }
      return;
    }
    for (const [key, child] of Object.entries(value)) {
      if (forbiddenKeys.has(key.toLowerCase())) problems.push(`${path}.${key} is forbidden`);
      scan(child, `${path}.${key}`);
    }
  }
  scan(artifact);

  const runtimeBinding = validateRuntimeScopeBinding(artifact);
  problems.push(...runtimeBinding.problems);
  problems.push(...validateTaskRuntimePath(artifact.source_location, runtimeBinding.expected?.task_root, '$.source_location'));
  if (artifact.source_scope !== `${artifact.client_id}/${artifact.company_id}/${artifact.task_id}`) problems.push('$.source_scope must exactly match client_id/company_id/task_id');

  if (Date.parse(artifact.captured_at) > nowMs) problems.push('$.captured_at cannot be in the future');
  if (artifact.source_date !== null && Date.parse(artifact.source_date) > nowMs) problems.push('$.source_date cannot be in the future');
  if (artifact.review_after !== null && Date.parse(artifact.review_after) <= nowMs) problems.push('$.review_after is due or expired; refresh or explicitly reconfirm the source before consuming it');
  if (!usableClearances.has(artifact.method_use_clearance)) problems.push(`$.method_use_clearance=${artifact.method_use_clearance ?? 'missing'} blocks extraction consumption`);
  if (artifact.publication_clearance === 'approved' && !['owned','authorized','public'].includes(artifact.rights_status)) problems.push('$.publication_clearance=approved requires rights_status owned, authorized, or public');
  const units = Array.isArray(artifact.units) ? artifact.units : [];
  if (['complete','partial'].includes(artifact.status) && units.length === 0) problems.push(`${artifact.status} extraction requires at least one extracted unit`);
  if (artifact.status === 'blocked' && units.length > 0) problems.push('blocked extraction must not expose units as usable evidence; use partial with warnings when some units are usable');
  const ids = units.map((unit) => unit?.unit_id);
  if (!unique(ids)) problems.push('unit_id values must be unique');
  for (const [index, unit] of units.entries()) {
    if (unit?.confidence === 'low' && (!Array.isArray(unit.warnings) || unit.warnings.length === 0)) problems.push(`$.units[${index}] low-confidence extraction requires a warning`);
  }
  if (artifact.status === 'partial' && (!Array.isArray(artifact.warnings) || artifact.warnings.length === 0)) problems.push('partial extraction requires at least one artifact-level warning');
  if (artifact.status === 'blocked' && (!Array.isArray(artifact.warnings) || artifact.warnings.length === 0)) problems.push('blocked extraction requires at least one artifact-level warning');
  return { ok: problems.length === 0, problems };
}

export function loadAndValidateSourceExtraction(path) {
  return validateSourceExtraction(JSON.parse(readFileSync(resolve(path), 'utf8')));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const path = process.argv[2];
  if (!path) { console.error('usage: node scripts/validate-source-extraction.mjs path/to/source-extraction.json'); process.exit(2); }
  let result;
  try { result = loadAndValidateSourceExtraction(path); }
  catch (error) { console.error(`SOURCE_EXTRACTION_BLOCK: ${error.message}`); process.exit(1); }
  if (!result.ok) {
    console.error('SOURCE_EXTRACTION_BLOCK');
    for (const problem of result.problems) console.error(`- ${problem}`);
    process.exit(1);
  }
  console.log('SOURCE_EXTRACTION_STRUCTURE_PASS');
}
