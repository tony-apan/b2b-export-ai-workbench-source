const KEY_PATTERN = /^[A-Za-z_][A-Za-z0-9_-]*$/;

function parseSingleQuoted(text, source, lineNumber) {
  if (!text.endsWith("'")) throw new Error(`${source}:${lineNumber} unterminated single-quoted scalar`);
  const inner = text.slice(1, -1);
  if (inner.includes("'") && !inner.includes("''")) throw new Error(`${source}:${lineNumber} invalid single-quoted scalar`);
  return inner.replace(/''/g, "'");
}

function parseDoubleQuoted(text, source, lineNumber) {
  try {
    const value = JSON.parse(text);
    if (typeof value !== 'string') throw new Error('not a string');
    return value;
  } catch {
    throw new Error(`${source}:${lineNumber} invalid double-quoted scalar`);
  }
}

function splitInlineArray(inner, source, lineNumber) {
  const values = [];
  let current = '';
  let quote = null;
  let escaped = false;
  for (let index = 0; index < inner.length; index += 1) {
    const char = inner[index];
    if (quote === '"') {
      current += char;
      if (escaped) escaped = false;
      else if (char === '\\') escaped = true;
      else if (char === '"') quote = null;
      continue;
    }
    if (quote === "'") {
      current += char;
      if (char === "'" && inner[index + 1] === "'") {
        current += inner[index + 1];
        index += 1;
      } else if (char === "'") quote = null;
      continue;
    }
    if (char === '"' || char === "'") {
      quote = char;
      current += char;
    } else if (char === ',') {
      if (!current.trim()) throw new Error(`${source}:${lineNumber} inline array contains an empty item`);
      values.push(current.trim());
      current = '';
    } else {
      current += char;
    }
  }
  if (quote) throw new Error(`${source}:${lineNumber} unterminated quoted value in inline array`);
  if (current.trim()) values.push(current.trim());
  else if (inner.trim()) throw new Error(`${source}:${lineNumber} inline array has a trailing comma`);
  return values;
}

function parseScalar(text, source, lineNumber, { arrayItem = false } = {}) {
  const value = text.trim();
  if (!value) throw new Error(`${source}:${lineNumber} empty YAML value is not supported`);
  if (/^[>|][+-]?$/.test(value)) throw new Error(`${source}:${lineNumber} multiline YAML is not supported by this portable front matter contract`);
  if (value.startsWith('"')) return parseDoubleQuoted(value, source, lineNumber);
  if (value.startsWith("'")) return parseSingleQuoted(value, source, lineNumber);
  if (value === 'true') return true;
  if (value === 'false') return false;
  if (value === 'null' || value === '~') return null;
  if (/^-?(?:0|[1-9]\d*)$/.test(value)) return Number(value);
  if (/^(?:yes|no|on|off|y|n|\.nan|[-+]?\.inf)$/i.test(value)) {
    throw new Error(`${source}:${lineNumber} ambiguous YAML scalar must be explicitly quoted: ${value}`);
  }
  if (arrayItem && /[\[\]{}]/.test(value)) throw new Error(`${source}:${lineNumber} nested YAML collections are not supported`);
  if (!arrayItem && (value.startsWith('{') || value.startsWith('['))) throw new Error(`${source}:${lineNumber} unsupported YAML collection syntax`);
  return value;
}

function parseValue(text, source, lineNumber) {
  const value = text.trim();
  if (value.startsWith('[')) {
    if (!value.endsWith(']')) throw new Error(`${source}:${lineNumber} unterminated inline array`);
    const inner = value.slice(1, -1);
    if (!inner.trim()) return [];
    return splitInlineArray(inner, source, lineNumber)
      .map((item) => parseScalar(item, source, lineNumber, { arrayItem: true }));
  }
  return parseScalar(value, source, lineNumber);
}

export function parseMarkdownFrontMatter(content, { source = '<markdown>' } = {}) {
  if (typeof content !== 'string') throw new TypeError(`${source} content must be a string`);
  const normalized = content.replace(/\r\n?/g, '\n');
  if (!normalized.startsWith('---\n')) throw new Error(`${source}:1 missing opening front matter delimiter`);
  const lines = normalized.split('\n');
  let closing = -1;
  for (let index = 1; index < lines.length; index += 1) {
    if (lines[index] === '---') { closing = index; break; }
  }
  if (closing < 0) throw new Error(`${source}: missing closing front matter delimiter`);
  const attributes = Object.create(null);
  const seen = new Map();
  for (let index = 1; index < closing; index += 1) {
    const line = lines[index];
    const lineNumber = index + 1;
    if (!line.trim() || line.trimStart().startsWith('#')) continue;
    if (/^[ \t]/.test(line)) throw new Error(`${source}:${lineNumber} nested or multiline YAML is not supported`);
    const colon = line.indexOf(':');
    if (colon <= 0) throw new Error(`${source}:${lineNumber} expected a top-level key/value pair`);
    const key = line.slice(0, colon).trim();
    if (!KEY_PATTERN.test(key)) throw new Error(`${source}:${lineNumber} invalid front matter key: ${key}`);
    if (seen.has(key)) throw new Error(`${source}:${lineNumber} duplicate front matter key ${key}; first declared on line ${seen.get(key)}`);
    seen.set(key, lineNumber);
    attributes[key] = parseValue(line.slice(colon + 1), source, lineNumber);
  }
  return {
    attributes,
    raw: lines.slice(1, closing).join('\n'),
    body: lines.slice(closing + 1).join('\n'),
    closingLine: closing + 1,
  };
}

export function requireStringField(attributes, field, { source = '<front matter>', nullable = false } = {}) {
  const value = attributes?.[field];
  if (nullable && value === null) return null;
  if (typeof value !== 'string' || !value.trim()) throw new Error(`${source} field ${field} must be a non-empty string`);
  return value.trim();
}

export function requireStringArrayField(attributes, field, { source = '<front matter>', allowEmpty = false } = {}) {
  const value = attributes?.[field];
  if (!Array.isArray(value) || (!allowEmpty && value.length === 0) || value.some((item) => typeof item !== 'string' || !item.trim())) {
    throw new Error(`${source} field ${field} must be ${allowEmpty ? 'an' : 'a non-empty'} array of strings`);
  }
  return value.map((item) => item.trim());
}
