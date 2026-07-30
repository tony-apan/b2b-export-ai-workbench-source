function maskText(text) {
  return text.replace(/[^\n]/gu, ' ');
}

export function withoutMarkdownCode(text) {
  const lines = text.replaceAll('\r\n', '\n').replaceAll('\r', '\n').split('\n');
  let fence = null;
  const masked = lines.map((line) => {
    const marker = line.match(/^[ \t]{0,3}(`{3,}|~{3,})/u)?.[1];
    if (!fence && marker) { fence = { char: marker[0], length: marker.length }; return maskText(line); }
    if (fence) {
      if (new RegExp(`^[ \\t]{0,3}${fence.char}{${fence.length},}[ \\t]*$`, 'u').test(line)) fence = null;
      return maskText(line);
    }
    return line;
  }).join('\n');

  const chars = [...masked];
  for (let index = 0; index < chars.length;) {
    if (chars[index] !== '`') { index += 1; continue; }
    let width = 1;
    while (chars[index + width] === '`') width += 1;
    let cursor = index + width;
    let close = -1;
    while (cursor < chars.length) {
      if (chars[cursor] !== '`') { cursor += 1; continue; }
      let closeWidth = 1;
      while (chars[cursor + closeWidth] === '`') closeWidth += 1;
      if (closeWidth === width) { close = cursor; break; }
      cursor += closeWidth;
    }
    if (close < 0) { index += width; continue; }
    for (let cursorIndex = index; cursorIndex < close + width; cursorIndex += 1) if (chars[cursorIndex] !== '\n') chars[cursorIndex] = ' ';
    index = close + width;
  }
  return chars.join('');
}

function normalizeLabel(label) {
  return label.replace(/\\([\\\[\]])/gu, '$1').trim().replace(/\s+/gu, ' ').toLowerCase();
}

function parseDestination(raw) {
  const value = raw.trim();
  if (!value) return '';
  if (value.startsWith('<')) {
    let escaped = false;
    for (let index = 1; index < value.length; index += 1) {
      const char = value[index];
      if (escaped) { escaped = false; continue; }
      if (char === '\\') { escaped = true; continue; }
      if (char === '>') return value.slice(1, index).replace(/\\([<>\\])/gu, '$1');
    }
    return '';
  }
  let depth = 0;
  let escaped = false;
  for (let index = 0; index < value.length; index += 1) {
    const char = value[index];
    if (escaped) { escaped = false; continue; }
    if (char === '\\') { escaped = true; continue; }
    if (char === '(') { depth += 1; continue; }
    if (char === ')' && depth > 0) { depth -= 1; continue; }
    if (/\s/u.test(char) && depth === 0) return value.slice(0, index).replace(/\\([()\\ ])/gu, '$1');
  }
  return value.replace(/\\([()\\ ])/gu, '$1');
}

function findClosingBracket(text, start) {
  let depth = 1;
  let escaped = false;
  for (let index = start; index < text.length; index += 1) {
    const char = text[index];
    if (escaped) { escaped = false; continue; }
    if (char === '\\') { escaped = true; continue; }
    if (char === '[') depth += 1;
    else if (char === ']') {
      depth -= 1;
      if (depth === 0) return index;
    }
  }
  return -1;
}

function findClosingParenthesis(text, start) {
  let depth = 1;
  let escaped = false;
  let angle = false;
  for (let index = start; index < text.length; index += 1) {
    const char = text[index];
    if (escaped) { escaped = false; continue; }
    if (char === '\\') { escaped = true; continue; }
    if (char === '<' && depth === 1) { angle = true; continue; }
    if (char === '>' && angle) { angle = false; continue; }
    if (angle) continue;
    if (char === '(') depth += 1;
    else if (char === ')') {
      depth -= 1;
      if (depth === 0) return index;
    }
  }
  return -1;
}

function lineNumberAt(text, offset) {
  let line = 1;
  for (let index = 0; index < offset; index += 1) if (text[index] === '\n') line += 1;
  return line;
}

function collectDefinitions(text) {
  const definitions = new Map();
  const duplicateLabels = [];
  const ranges = [];
  const lines = text.split('\n');
  let offset = 0;
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const match = line.match(/^[ \t]{0,3}\[([^\]]+)\]:[ \t]*(.*)$/u);
    if (!match) { offset += line.length + 1; continue; }
    let raw = match[2];
    let endLine = index;
    if (!raw.trim() && lines[index + 1] && /^[ \t]+\S/u.test(lines[index + 1])) {
      endLine = index + 1;
      raw = lines[endLine].trim();
    }
    const label = normalizeLabel(match[1]);
    const destination = parseDestination(raw);
    if (definitions.has(label)) duplicateLabels.push(label);
    else definitions.set(label, { label, destination, raw, line: index + 1 });
    let endOffset = offset;
    for (let cursor = index; cursor <= endLine; cursor += 1) endOffset += lines[cursor].length + 1;
    ranges.push([offset, Math.min(endOffset, text.length)]);
    if (endLine > index) {
      offset = endOffset;
      index = endLine;
    } else offset += line.length + 1;
  }
  const chars = [...text];
  for (const [start, end] of ranges) for (let index = start; index < end; index += 1) if (chars[index] !== '\n') chars[index] = ' ';
  return { definitions, duplicateLabels: [...new Set(duplicateLabels)], textWithoutDefinitions: chars.join('') };
}

export function extractMarkdownLinks(markdown, options = {}) {
  const sanitized = withoutMarkdownCode(markdown);
  const { definitions, duplicateLabels, textWithoutDefinitions } = collectDefinitions(sanitized);
  const links = [];
  const errors = duplicateLabels.map((label) => ({ kind: 'duplicate-reference-definition', label, message: `duplicate reference definition: ${label}` }));
  if (options.includeDefinitions !== false) {
    for (const definition of definitions.values()) {
      if (!definition.destination) errors.push({ kind: 'invalid-reference-definition', label: definition.label, line: definition.line, message: `reference definition has no readable destination: ${definition.label}` });
      else links.push({ kind: 'reference-definition', target: definition.destination, label: definition.label, line: definition.line });
    }
  }

  const text = textWithoutDefinitions;
  for (let index = 0; index < text.length;) {
    const image = text[index] === '!' && text[index + 1] === '[';
    if (text[index] !== '[' && !image) { index += 1; continue; }
    const open = image ? index + 1 : index;
    const close = findClosingBracket(text, open + 1);
    if (close < 0) { index = open + 1; continue; }
    const labelText = text.slice(open + 1, close);
    const next = text[close + 1];
    if (next === '(') {
      const end = findClosingParenthesis(text, close + 2);
      if (end < 0) { errors.push({ kind: 'unclosed-inline-link', line: lineNumberAt(text, open), message: 'unclosed inline Markdown link' }); index = close + 1; continue; }
      const raw = text.slice(close + 2, end);
      const target = parseDestination(raw);
      if (!target) errors.push({ kind: 'invalid-inline-link', line: lineNumberAt(text, open), message: 'inline Markdown link has no readable destination' });
      else links.push({ kind: image ? 'inline-image' : 'inline', target, line: lineNumberAt(text, open) });
      index = end + 1;
      continue;
    }
    if (next === '[') {
      const refClose = findClosingBracket(text, close + 2);
      if (refClose < 0) { errors.push({ kind: 'unclosed-reference-link', line: lineNumberAt(text, open), message: 'unclosed reference-style Markdown link' }); index = close + 1; continue; }
      const explicit = text.slice(close + 2, refClose);
      const label = normalizeLabel(explicit || labelText);
      const definition = definitions.get(label);
      if (!definition) errors.push({ kind: 'undefined-reference', label, line: lineNumberAt(text, open), message: `undefined Markdown reference: ${label}` });
      else if (definition.destination) links.push({ kind: image ? 'reference-image' : 'reference', target: definition.destination, label, line: lineNumberAt(text, open) });
      index = refClose + 1;
      continue;
    }
    const shortcutLabel = normalizeLabel(labelText);
    const definition = definitions.get(shortcutLabel);
    if (definition?.destination) links.push({ kind: image ? 'shortcut-image' : 'shortcut-reference', target: definition.destination, label: shortcutLabel, line: lineNumberAt(text, open) });
    index = close + 1;
  }
  return { links, errors, definitions };
}

export function markdownLinkDestination(raw) {
  return parseDestination(raw);
}
