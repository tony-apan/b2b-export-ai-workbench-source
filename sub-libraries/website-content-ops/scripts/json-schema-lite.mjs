function sameValue(left, right) {
  return JSON.stringify(left) === JSON.stringify(right);
}

function valueType(value) {
  if (Array.isArray(value)) return 'array';
  if (value === null) return 'null';
  if (Number.isInteger(value)) return 'integer';
  return typeof value;
}

export function validateJsonSchema(instance, schema) {
  const issues = [];

  function check(value, rule, path) {
    if (typeof rule === 'boolean') {
      if (!rule) issues.push(`${path} is disallowed by schema`);
      return;
    }

    if (rule.allOf) for (const child of rule.allOf) check(value, child, path);
    if (rule.const !== undefined && !sameValue(value, rule.const)) issues.push(`${path} must equal ${JSON.stringify(rule.const)}`);
    if (rule.enum && !rule.enum.some((item) => sameValue(value, item))) issues.push(`${path} is not in the allowed enum`);

    if (rule.type) {
      const actual = valueType(value);
      if (actual !== rule.type) {
        issues.push(`${path} must be ${rule.type}, got ${actual}`);
        return;
      }
    }

    if (typeof value === 'string') {
      if (rule.minLength !== undefined && value.trim().length < rule.minLength) issues.push(`${path} must contain at least ${rule.minLength} non-whitespace characters`);
      if (rule.pattern && !new RegExp(rule.pattern).test(value)) issues.push(`${path} does not match required pattern`);
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
      for (const [key, child] of Object.entries(rule.properties ?? {})) if (key in value) check(value[key], child, `${path}.${key}`);
      if (rule.additionalProperties === false) {
        const allowed = new Set(Object.keys(rule.properties ?? {}));
        for (const key of Object.keys(value)) if (!allowed.has(key)) issues.push(`${path}.${key} is not allowed`);
      }
    }
  }

  check(instance, schema, '$');
  return issues;
}
