import { readFileSync } from 'node:fs';

export class FrontMatterSyntaxError extends Error {
  constructor(message, line = 0) {
    super(line ? `${message} (line ${line})` : message);
    this.name = 'FrontMatterSyntaxError';
    this.line = line;
  }
}

function normalizeNewlines(text) {
  return text.replace(/^\uFEFF/u, '').replaceAll('\r\n', '\n').replaceAll('\r', '\n');
}

function extractBlock(text) {
  const normalized = normalizeNewlines(text);
  if (normalized.startsWith('---\n')) {
    const lines = normalized.split('\n');
    const end = lines.findIndex((line, index) => index > 0 && /^---[ \t]*$/u.test(line));
    if (end < 0) throw new FrontMatterSyntaxError('unclosed YAML front matter');
    return { format: 'yaml', body: lines.slice(1, end).join('\n'), startLine: 2 };
  }
  if (normalized.startsWith('<!--')) {
    const end = normalized.indexOf('-->');
    if (end < 0) throw new FrontMatterSyntaxError('unclosed HTML metadata block');
    let body = normalized.slice(4, end).replace(/^\n/u, '');
    body = body.replace(/^Repository metadata:[ \t]*\n/u, '');
    return { format: 'html', body: body.trimEnd(), startLine: 2 };
  }
  return null;
}

function stripPlainComment(raw) {
  for (let index = 0; index < raw.length; index += 1) {
    if (raw[index] === '#' && (index === 0 || /\s/u.test(raw[index - 1]))) return raw.slice(0, index).trimEnd();
  }
  return raw.trimEnd();
}

function parseDoubleQuoted(raw, line) {
  if (!raw.endsWith('"') || raw.length < 2) throw new FrontMatterSyntaxError('unterminated double-quoted scalar', line);
  let value = '';
  for (let index = 1; index < raw.length - 1; index += 1) {
    const char = raw[index];
    if (char !== '\\') { value += char; continue; }
    index += 1;
    if (index >= raw.length - 1) throw new FrontMatterSyntaxError('unterminated escape sequence', line);
    const escaped = raw[index];
    const simple = { '0': '\0', a: '\x07', b: '\b', t: '\t', n: '\n', v: '\v', f: '\f', r: '\r', e: '\x1b', ' ': ' ', '"': '"', '/': '/', '\\': '\\', N: '\u0085', _: '\u00a0', L: '\u2028', P: '\u2029' };
    if (Object.hasOwn(simple, escaped)) { value += simple[escaped]; continue; }
    const widths = { x: 2, u: 4, U: 8 };
    if (Object.hasOwn(widths, escaped)) {
      const width = widths[escaped];
      const hex = raw.slice(index + 1, index + 1 + width);
      if (!new RegExp(`^[0-9a-fA-F]{${width}}$`, 'u').test(hex)) throw new FrontMatterSyntaxError(`invalid \\${escaped} escape`, line);
      const codePoint = Number.parseInt(hex, 16);
      if (codePoint > 0x10ffff) throw new FrontMatterSyntaxError('Unicode escape is outside the valid range', line);
      value += String.fromCodePoint(codePoint);
      index += width;
      continue;
    }
    throw new FrontMatterSyntaxError(`unsupported escape sequence \\${escaped}`, line);
  }
  return value;
}

function parseSingleQuoted(raw, line) {
  if (!raw.endsWith("'") || raw.length < 2) throw new FrontMatterSyntaxError('unterminated single-quoted scalar', line);
  return raw.slice(1, -1).replaceAll("''", "'");
}

function splitFlowSequence(inner, line) {
  const parts = [];
  let start = 0;
  let quote = '';
  let escaped = false;
  for (let index = 0; index < inner.length; index += 1) {
    const char = inner[index];
    if (quote) {
      if (quote === '"' && escaped) { escaped = false; continue; }
      if (quote === '"' && char === '\\') { escaped = true; continue; }
      if (char === quote) {
        if (quote === "'" && inner[index + 1] === "'") { index += 1; continue; }
        quote = '';
      }
      continue;
    }
    if (char === '"' || char === "'") { quote = char; continue; }
    if (char === '[' || char === ']' || char === '{' || char === '}') throw new FrontMatterSyntaxError('nested flow collections are not supported by the repository front matter schema', line);
    if (char === ',') { parts.push(inner.slice(start, index)); start = index + 1; }
  }
  if (quote) throw new FrontMatterSyntaxError('unterminated quoted scalar in inline sequence', line);
  parts.push(inner.slice(start));
  return parts;
}

function parseScalar(rawValue, line) {
  const raw = stripPlainComment(rawValue).trim();
  if (!raw) return '';
  if (raw.startsWith('"')) return parseDoubleQuoted(raw, line);
  if (raw.startsWith("'")) return parseSingleQuoted(raw, line);
  if (raw.startsWith('[')) {
    if (!raw.endsWith(']')) throw new FrontMatterSyntaxError('unterminated inline sequence', line);
    const inner = raw.slice(1, -1).trim();
    if (!inner) return [];
    const parts = splitFlowSequence(inner, line);
    if (parts.some((part) => !part.trim())) throw new FrontMatterSyntaxError('empty or trailing member in inline sequence', line);
    return parts.map((part) => parseScalar(part, line));
  }
  if (raw.startsWith('{')) throw new FrontMatterSyntaxError('flow mappings are not supported by the repository front matter schema', line);
  if (/^(?:null|Null|NULL|~)$/u.test(raw)) return null;
  if (/^(?:true|True|TRUE)$/u.test(raw)) return true;
  if (/^(?:false|False|FALSE)$/u.test(raw)) return false;
  if (/^[-+]?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?$/u.test(raw)) return Number(raw);
  return raw;
}

function leadingSpaces(line) {
  return line.match(/^[ ]*/u)?.[0].length ?? 0;
}

function foldedBlock(lines) {
  let result = '';
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const next = lines[index + 1];
    result += line;
    if (next === undefined) continue;
    result += !line || !next ? '\n' : ' ';
  }
  return result;
}

function applyChomping(value, chomping) {
  if (chomping === '-') return value.replace(/\n+$/u, '');
  if (chomping === '+') return `${value}\n`;
  return `${value.replace(/\n+$/u, '')}\n`;
}

function collectIndented(lines, start, parentIndent) {
  let end = start;
  while (end < lines.length) {
    const line = lines[end];
    if (line.trim() && leadingSpaces(line) <= parentIndent) break;
    end += 1;
  }
  const block = lines.slice(start, end);
  const nonBlank = block.filter((line) => line.trim());
  const indent = nonBlank.length ? Math.min(...nonBlank.map(leadingSpaces)) : parentIndent + 2;
  return { lines: block.map((line) => line.trim() ? line.slice(indent) : ''), end, indent };
}

function parseBlockValue(lines, start, parentIndent, indicator, lineNumber) {
  const collected = collectIndented(lines, start, parentIndent);
  if (collected.end === start) throw new FrontMatterSyntaxError('multiline scalar has no indented content', lineNumber);
  const style = indicator[0];
  const chomping = indicator.slice(1).includes('-') ? '-' : indicator.slice(1).includes('+') ? '+' : '';
  const raw = style === '|' ? collected.lines.join('\n') : foldedBlock(collected.lines);
  return { value: applyChomping(raw, chomping), end: collected.end, style: style === '|' ? 'literal' : 'folded' };
}

function parseIndentedValue(lines, start, parentIndent, lineNumber) {
  const collected = collectIndented(lines, start, parentIndent);
  if (collected.end === start) return { value: null, end: start, style: 'empty' };
  const nonBlank = collected.lines.filter((line) => line.trim());
  if (nonBlank.every((line) => /^-[ \t]+/u.test(line))) {
    return {
      value: nonBlank.map((line, index) => parseScalar(line.replace(/^-[ \t]+/u, ''), lineNumber + index + 1)),
      end: collected.end,
      style: 'block-sequence',
    };
  }
  if (nonBlank.some((line) => /^-[ \t]+/u.test(line))) throw new FrontMatterSyntaxError('mixed block sequence and scalar content', lineNumber);
  return { value: foldedBlock(collected.lines), end: collected.end, style: 'plain-multiline' };
}

export function parseFrontMatterText(text, options = {}) {
  const extracted = extractBlock(text);
  if (!extracted) return null;
  const lines = extracted.body.split('\n');
  const data = new Map();
  const nodes = new Map();
  const duplicateKeys = [];
  for (let index = 0; index < lines.length;) {
    const line = lines[index];
    if (!line.trim() || /^[ \t]*#/u.test(line)) { index += 1; continue; }
    if (/^[ \t]/u.test(line)) throw new FrontMatterSyntaxError('unexpected indentation at top level', extracted.startLine + index);
    const match = line.match(/^([A-Za-z_][A-Za-z0-9_-]*):(?:[ \t]*(.*))?$/u);
    if (!match) throw new FrontMatterSyntaxError('front matter must be a flat YAML mapping', extracted.startLine + index);
    const [, key, rawValue = ''] = match;
    const lineNumber = extracted.startLine + index;
    let value;
    let style = 'plain';
    let end = index + 1;
    const trimmed = rawValue.trim();
    if (/^[|>][+-]?(?:[1-9])?$/u.test(trimmed)) {
      const parsed = parseBlockValue(lines, index + 1, 0, trimmed, lineNumber);
      ({ value, style, end } = parsed);
    } else if (!trimmed) {
      const parsed = parseIndentedValue(lines, index + 1, 0, lineNumber);
      ({ value, style, end } = parsed);
    } else {
      value = parseScalar(rawValue, lineNumber);
      if (Array.isArray(value)) style = 'inline-sequence';
      else if (typeof value === 'string' && (trimmed.startsWith('"') || trimmed.startsWith("'"))) style = 'quoted';
    }
    if (data.has(key)) duplicateKeys.push(key);
    data.set(key, value);
    nodes.set(key, { key, value, style, raw: lines.slice(index, end).join('\n'), line: lineNumber });
    index = end;
  }
  if (options.rejectDuplicates && duplicateKeys.length) {
    throw new FrontMatterSyntaxError(`duplicate metadata key(s): ${[...new Set(duplicateKeys)].join(', ')}`);
  }
  return { ...extracted, data, nodes, duplicateKeys: [...new Set(duplicateKeys)] };
}

export function readFrontMatter(filePath, options = {}) {
  return parseFrontMatterText(readFileSync(filePath, 'utf8'), options);
}

export function stringField(meta, field) {
  const value = meta?.data.get(field);
  return typeof value === 'string' ? value.trim() : '';
}

export function stringListField(meta, field, options = {}) {
  if (!meta?.data.has(field)) return { valid: false, values: [], reason: 'missing field' };
  const value = meta.data.get(field);
  const node = meta.nodes.get(field);
  if (!Array.isArray(value)) return { valid: false, values: [], reason: 'must be an array' };
  if (options.inlineOnly && node?.style !== 'inline-sequence') return { valid: false, values: [], reason: 'must use inline array syntax' };
  if (value.some((item) => typeof item !== 'string' || !item.trim())) return { valid: false, values: [], reason: 'members must be non-empty strings' };
  const values = value.map((item) => item.trim());
  if (new Set(values).size !== values.length) return { valid: false, values, reason: 'duplicate members are not allowed' };
  if (options.quotedMembers && node && values.length) {
    const raw = node.raw.slice(node.raw.indexOf(':') + 1).trim();
    const inner = raw.startsWith('[') && raw.endsWith(']') ? raw.slice(1, -1) : '';
    if (!inner || splitFlowSequence(inner, node.line).some((item) => !/^["'](?:[\s\S]*)["']$/u.test(item.trim()))) {
      return { valid: false, values, reason: 'members must be quoted strings' };
    }
  }
  return { valid: true, values, reason: '' };
}
