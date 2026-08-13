function sameValue(left, right) {
  return JSON.stringify(left) === JSON.stringify(right);
}

function valueType(value) {
  if (Array.isArray(value)) return 'array';
  if (value === null) return 'null';
  if (Number.isInteger(value)) return 'integer';
  return typeof value;
}

function decodePointerToken(token) {
  return token.replaceAll('~1', '/').replaceAll('~0', '~');
}

function resolveLocalRef(rootSchema, ref) {
  if (ref === '#') return rootSchema;
  if (!ref.startsWith('#/')) throw new Error(`unsupported non-local $ref: ${ref}`);
  let current = rootSchema;
  for (const token of ref.slice(2).split('/').map(decodePointerToken)) {
    if (!current || typeof current !== 'object' || !(token in current)) throw new Error(`unresolved $ref: ${ref}`);
    current = current[token];
  }
  return current;
}

function isDateTime(value) {
  if (typeof value !== 'string') return false;
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value)) return false;
  return Number.isFinite(Date.parse(value));
}

const supportedSchemaKeywords = new Set([
  '$schema', '$id', '$ref', '$defs', 'title', 'description',
  'type', 'const', 'enum', 'allOf', 'format', 'pattern', 'minLength',
  'minItems', 'uniqueItems', 'items', 'contains', 'minContains',
  'required', 'properties', 'additionalProperties',
]);
const supportedTypes = new Set(['object', 'array', 'string', 'number', 'integer', 'boolean', 'null']);

export function validateJsonSchemaDefinition(schema) {
  const issues = [];
  const seen = new Set();

  function inspect(rule, path) {
    if (typeof rule === 'boolean') return;
    if (!rule || typeof rule !== 'object' || Array.isArray(rule)) { issues.push(`${path} must be a schema object or boolean`); return; }
    if (seen.has(rule)) return;
    seen.add(rule);
    for (const key of Object.keys(rule)) if (!supportedSchemaKeywords.has(key)) issues.push(`${path}.${key} uses an unsupported schema keyword`);
    if (rule.$ref) {
      try { resolveLocalRef(schema, rule.$ref); }
      catch (error) { issues.push(`${path} ${error.message}`); }
    }
    if (rule.type) {
      const types = Array.isArray(rule.type) ? rule.type : [rule.type];
      if (types.length === 0 || types.some((type) => !supportedTypes.has(type))) issues.push(`${path}.type contains an unsupported type`);
    }
    if (rule.format && rule.format !== 'date-time') issues.push(`${path}.format uses unsupported format ${rule.format}`);
    for (const [key, child] of Object.entries(rule.$defs ?? {})) inspect(child, `${path}.$defs.${key}`);
    for (const [key, child] of Object.entries(rule.properties ?? {})) inspect(child, `${path}.properties.${key}`);
    if (rule.additionalProperties && typeof rule.additionalProperties === 'object') inspect(rule.additionalProperties, `${path}.additionalProperties`);
    if (rule.items) inspect(rule.items, `${path}.items`);
    if (rule.contains) inspect(rule.contains, `${path}.contains`);
    for (const [index, child] of (rule.allOf ?? []).entries()) inspect(child, `${path}.allOf[${index}]`);
  }

  inspect(schema, '$');
  return issues;
}

export function validateJsonSchema(instance, schema) {
  const issues = [];

  function check(value, rule, path) {
    if (typeof rule === 'boolean') {
      if (!rule) issues.push(`${path} is disallowed by schema`);
      return;
    }
    if (!rule || typeof rule !== 'object' || Array.isArray(rule)) {
      issues.push(`${path} has an invalid schema rule`);
      return;
    }

    if (rule.$ref) {
      try { check(value, resolveLocalRef(schema, rule.$ref), path); }
      catch (error) { issues.push(`${path} schema reference error: ${error.message}`); }
    }
    if (rule.allOf) for (const child of rule.allOf) check(value, child, path);
    if (rule.const !== undefined && !sameValue(value, rule.const)) issues.push(`${path} must equal ${JSON.stringify(rule.const)}`);
    if (rule.enum && !rule.enum.some((item) => sameValue(value, item))) issues.push(`${path} is not in the allowed enum`);

    if (rule.type) {
      const allowedTypes = Array.isArray(rule.type) ? rule.type : [rule.type];
      const actual = valueType(value);
      if (!allowedTypes.includes(actual)) {
        issues.push(`${path} must be ${allowedTypes.join(' or ')}, got ${actual}`);
        return;
      }
    }

    if (typeof value === 'string') {
      if (rule.minLength !== undefined && value.trim().length < rule.minLength) issues.push(`${path} must contain at least ${rule.minLength} non-whitespace characters`);
      if (rule.pattern && !new RegExp(rule.pattern).test(value)) issues.push(`${path} does not match required pattern`);
      if (rule.format === 'date-time' && !isDateTime(value)) issues.push(`${path} must be a valid RFC3339 date-time`);
    }

    if (Array.isArray(value)) {
      if (rule.minItems !== undefined && value.length < rule.minItems) issues.push(`${path} must contain at least ${rule.minItems} item(s)`);
      if (rule.uniqueItems) {
        const seen = new Set(value.map((item) => JSON.stringify(item)));
        if (seen.size !== value.length) issues.push(`${path} must contain unique items`);
      }
      if (rule.items) value.forEach((item, index) => check(item, rule.items, `${path}[${index}]`));
      if (rule.contains) {
        let matches = 0;
        for (const item of value) {
          const before = issues.length;
          check(item, rule.contains, `${path}[contains]`);
          if (issues.length === before) matches += 1;
          else issues.splice(before);
        }
        const required = rule.minContains ?? 1;
        if (matches < required) issues.push(`${path} must contain at least ${required} required item(s)`);
      }
    }

    if (value && typeof value === 'object' && !Array.isArray(value)) {
      for (const key of rule.required ?? []) if (!(key in value)) issues.push(`${path}.${key} is required`);
      const declared = rule.properties ?? {};
      for (const [key, child] of Object.entries(declared)) if (key in value) check(value[key], child, `${path}.${key}`);
      const extras = Object.keys(value).filter((key) => !(key in declared));
      if (rule.additionalProperties === false) {
        for (const key of extras) issues.push(`${path}.${key} is not allowed`);
      } else if (rule.additionalProperties && typeof rule.additionalProperties === 'object') {
        for (const key of extras) check(value[key], rule.additionalProperties, `${path}.${key}`);
      }
    }
  }

  check(instance, schema, '$');
  return issues;
}
