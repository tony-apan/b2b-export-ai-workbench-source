/**
 * AllinCMS article-body format profile and deterministic Markdown converter.
 *
 * The profile records only the generalized node shapes proven on the current
 * deployment family. It intentionally contains no site key, object ID, action
 * ID, deployment fingerprint, URL, cookie, or private run evidence.
 */

export const ARTICLE_FORMAT_PROFILE_DATE = '2026-07-30';
export const ARTICLE_FORMAT_PROFILE = 'current-deployment-tested-shapes';

function deepFreeze(value) {
  if (!value || typeof value !== 'object' || Object.isFrozen(value)) return value;
  for (const child of Object.values(value)) deepFreeze(child);
  return Object.freeze(value);
}

export const ALLINCMS_ARTICLE_FORMAT_SUPPORT = deepFreeze({
  profile: ARTICLE_FORMAT_PROFILE,
  verifiedAt: ARTICLE_FORMAT_PROFILE_DATE,
  sourceFormat: 'Slate JSON node[]',
  verified: [
    'h3',
    'bold',
    'italic',
    'underline',
    'strikethrough',
    'inline-code',
    'link',
    'bulleted-list',
    'numbered-list',
    'blockquote',
    'divider',
    'table',
  ],
  unsupportedCurrentShape: [
    {
      key: 'code-block',
      reason: 'The tested pre/code Slate shape persisted and read back through the API, but reopening the editor failed.',
      policy: 'Recover to the previous last-known-good content before publish. Do not publish this shape.',
    },
  ],
  notTested: [],
  baselineAlsoVerified: ['p', 'h2', 'img'],
});

function assertIdPrefix(idPrefix) {
  if (typeof idPrefix !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(idPrefix)) {
    throw new Error('idPrefix must be a non-empty safe identifier prefix');
  }
  return idPrefix;
}

function makeIdFactory(idPrefix) {
  const prefix = assertIdPrefix(idPrefix);
  let index = 0;
  return (role) => {
    index += 1;
    return `${prefix}-${String(index).padStart(3, '0')}-${role}`;
  };
}

function textLeaf(text, marks = {}) {
  return { text, ...marks };
}

function paragraph(id, children, extra = {}) {
  return { type: 'p', children, id, ...extra };
}

function canonicalExamples(idPrefix) {
  const nextId = makeIdFactory(idPrefix);
  return {
    h3: { type: 'h3', children: [textLeaf('Heading 3')], id: nextId('h3') },
    bold: paragraph(nextId('bold'), [textLeaf('Bold text', { bold: true })]),
    italic: paragraph(nextId('italic'), [textLeaf('Italic text', { italic: true })]),
    underline: paragraph(nextId('underline'), [textLeaf('Underlined text', { underline: true })]),
    strikethrough: paragraph(nextId('strikethrough'), [textLeaf('Struck text', { strikethrough: true })]),
    'inline-code': paragraph(nextId('inline-code'), [textLeaf('inline code', { code: true })]),
    link: paragraph(nextId('link-paragraph'), [
      textLeaf('Read '),
      { type: 'a', url: 'https://example.com/', children: [textLeaf('the reference')], id: nextId('link') },
      textLeaf('.'),
    ]),
    'bulleted-list': paragraph(nextId('bullet'), [textLeaf('Bulleted item')], { indent: 1, listStyleType: 'disc' }),
    'numbered-list': paragraph(nextId('number'), [textLeaf('Numbered item')], { indent: 1, listStyleType: 'decimal' }),
    blockquote: { type: 'blockquote', children: [textLeaf('Quoted text')], id: nextId('blockquote') },
    divider: { type: 'hr', children: [textLeaf('')], id: nextId('divider') },
    table: {
      type: 'table',
      id: nextId('table'),
      children: [
        {
          type: 'tr',
          id: nextId('table-head-row'),
          children: [
            { type: 'th', id: nextId('table-head-cell-1'), children: [paragraph(nextId('table-head-cell-1-p'), [textLeaf('Field')])] },
            { type: 'th', id: nextId('table-head-cell-2'), children: [paragraph(nextId('table-head-cell-2-p'), [textLeaf('Value')])] },
          ],
        },
        {
          type: 'tr',
          id: nextId('table-body-row'),
          children: [
            { type: 'td', id: nextId('table-body-cell-1'), children: [paragraph(nextId('table-body-cell-1-p'), [textLeaf('Format')])] },
            { type: 'td', id: nextId('table-body-cell-2'), children: [paragraph(nextId('table-body-cell-2-p'), [textLeaf('Verified')])] },
          ],
        },
      ],
    },
  };
}

export function createCanonicalAllinCmsSlateExamples({ idPrefix = 'format-example' } = {}) {
  return canonicalExamples(idPrefix);
}

function validateHttpUrl(value) {
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new Error(`Markdown link URL must be an absolute http(s) URL: ${value}`);
  }
  if (!['http:', 'https:'].includes(url.protocol)) {
    throw new Error(`Markdown link URL must use http(s): ${value}`);
  }
  return url.href;
}

function parseInlineMarkdown(source, nextId) {
  const patterns = [
    { kind: 'bold', regex: /\*\*([^*\n]+)\*\*/g },
    { kind: 'strikethrough', regex: /~~([^~\n]+)~~/g },
    { kind: 'inline-code', regex: /`([^`\n]+)`/g },
    { kind: 'underline', regex: /<u>([^<\n]+)<\/u>/gi },
    { kind: 'link', regex: /\[([^\]\n]+)\]\(([^)\s]+)\)/g },
    { kind: 'italic', regex: /\*([^*\n]+)\*/g },
  ];
  const children = [];
  let cursor = 0;
  while (cursor < source.length) {
    let winner = null;
    for (const pattern of patterns) {
      pattern.regex.lastIndex = cursor;
      const match = pattern.regex.exec(source);
      if (!match) continue;
      if (!winner || match.index < winner.match.index || (match.index === winner.match.index && patterns.indexOf(pattern) < patterns.indexOf(winner.pattern))) {
        winner = { pattern, match };
      }
    }
    if (!winner) {
      children.push(textLeaf(source.slice(cursor)));
      break;
    }
    if (winner.match.index > cursor) children.push(textLeaf(source.slice(cursor, winner.match.index)));
    const [raw, label, destination] = winner.match;
    switch (winner.pattern.kind) {
      case 'bold': children.push(textLeaf(label, { bold: true })); break;
      case 'italic': children.push(textLeaf(label, { italic: true })); break;
      case 'underline': children.push(textLeaf(label, { underline: true })); break;
      case 'strikethrough': children.push(textLeaf(label, { strikethrough: true })); break;
      case 'inline-code': children.push(textLeaf(label, { code: true })); break;
      case 'link': children.push({ type: 'a', url: validateHttpUrl(destination), children: [textLeaf(label)], id: nextId('link') }); break;
      default: throw new Error(`Unsupported inline Markdown token: ${winner.pattern.kind}`);
    }
    cursor = winner.match.index + raw.length;
  }
  return children.length ? children : [textLeaf('')];
}

function splitTableRow(line) {
  let value = line.trim();
  if (value.startsWith('|')) value = value.slice(1);
  if (value.endsWith('|')) value = value.slice(0, -1);
  return value.split('|').map((cell) => cell.trim());
}

function isTableSeparator(line) {
  const cells = splitTableRow(line);
  return cells.length >= 2 && cells.every((cell) => /^:?-{3,}:?$/.test(cell));
}

function createTableNode(lines, nextId) {
  const rows = lines.map(splitTableRow);
  const width = rows[0].length;
  if (width < 2 || rows.some((row) => row.length !== width)) {
    throw new Error('Markdown table rows must have the same number of cells');
  }
  const [header, , ...body] = rows;
  const makeRow = (cells, cellType, role) => ({
    type: 'tr',
    id: nextId(`${role}-row`),
    children: cells.map((cell, column) => ({
      type: cellType,
      id: nextId(`${role}-cell-${column + 1}`),
      children: [paragraph(nextId(`${role}-cell-${column + 1}-p`), parseInlineMarkdown(cell, nextId))],
    })),
  });
  return {
    type: 'table',
    id: nextId('table'),
    children: [makeRow(header, 'th', 'table-head'), ...body.map((row, index) => makeRow(row, 'td', `table-body-${index + 1}`))],
  };
}

/**
 * Convert a deliberately small, deterministic Markdown profile to the Slate
 * shapes verified by the AllinCMS adapter. Dangerous or structurally
 * ambiguous unsupported syntax fails closed; undeclared plain-text syntax is
 * preserved literally rather than being guessed into a Slate shape.
 *
 * Supported block syntax: paragraphs, ##, ###, bullets, numbered items,
 * blockquotes, thematic dividers and simple GFM tables.
 * Supported inline syntax: **bold**, *italic*, <u>underline</u>, ~~strike~~,
 * `inline code` and absolute http(s) links.
 */
export function markdownToAllinCmsSlate(markdown, { idPrefix = 'md' } = {}) {
  if (typeof markdown !== 'string') throw new Error('Markdown source must be a string');
  if (markdown.includes('\0')) throw new Error('Markdown source must not contain NUL bytes');
  if (/(^|[^\\])!\[[^\]\n]*\](?:\([^\n)]*\)|\[[^\]\n]*\])?/m.test(markdown)) {
    throw new Error('Markdown images must be handled by article-image-binding.mjs, not the article format converter');
  }
  if (/(^|[^\\])\[[^\]\n]+\]\[[^\]\n]*\]/m.test(markdown)
      || /^\s{0,3}\[[^\]\n]+\]:\s+\S+/m.test(markdown)) {
    throw new Error('Reference-style Markdown links are unsupported; use an inline absolute http(s) link');
  }
  if (/<!--|<![A-Z]|<\?/i.test(markdown)) {
    throw new Error('Raw HTML is unsupported; only the <u>text</u> underline extension is allowed');
  }
  const nextId = makeIdFactory(idPrefix);
  const lines = markdown.replace(/\r\n?/g, '\n').split('\n');
  const nodes = [];
  let paragraphLines = [];
  const flushParagraph = () => {
    if (!paragraphLines.length) return;
    const text = paragraphLines.map((line) => line.trim()).join(' ');
    nodes.push(paragraph(nextId('paragraph'), parseInlineMarkdown(text, nextId)));
    paragraphLines = [];
  };

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const trimmed = line.trim();
    if (/^(```|~~~)/.test(trimmed) || /^(?: {4,}|\t)\S/.test(line)) {
      throw new Error('Markdown code blocks are unsupported-current-shape; use inline code or attach the code as a file');
    }
    if (/^#\s+/.test(trimmed)) {
      throw new Error('Markdown H1 is not allowed inside an article body; use the article title field');
    }
    if (/^#{4,6}\s+/.test(trimmed)) {
      throw new Error('Markdown H4-H6 are unsupported; keep the AllinCMS article body hierarchy to H2 and H3');
    }
    if (/^(?:=+|-+)\s*$/.test(trimmed) && paragraphLines.length > 0) {
      throw new Error('Setext headings are unsupported; use explicit ## or ### headings');
    }
    const htmlResidue = trimmed.replace(/<u>[^<\n]+<\/u>/gi, '');
    if (/<\/?[A-Za-z][^>]*>/.test(htmlResidue)) {
      throw new Error('Raw HTML is unsupported; only the <u>text</u> underline extension is allowed');
    }
    if (!trimmed) {
      flushParagraph();
      continue;
    }
    if (line.includes('|') && index + 1 < lines.length && isTableSeparator(lines[index + 1])) {
      flushParagraph();
      const tableLines = [line, lines[index + 1]];
      if (splitTableRow(lines[index + 1]).some((cell) => cell.includes(':'))) {
        throw new Error('Markdown table alignment markers are unsupported because the verified Slate shape has no alignment field');
      }
      index += 2;
      while (index < lines.length && lines[index].includes('|') && lines[index].trim()) {
        tableLines.push(lines[index]);
        index += 1;
      }
      index -= 1;
      if (tableLines.length < 3) {
        throw new Error('Markdown tables must include at least one body row to match the verified Slate shape');
      }
      nodes.push(createTableNode(tableLines, nextId));
      continue;
    }
    const h3 = /^###\s+(.+)$/.exec(trimmed);
    if (h3) {
      flushParagraph();
      nodes.push({ type: 'h3', children: parseInlineMarkdown(h3[1], nextId), id: nextId('h3') });
      continue;
    }
    const h2 = /^##\s+(.+)$/.exec(trimmed);
    if (h2) {
      flushParagraph();
      nodes.push({ type: 'h2', children: parseInlineMarkdown(h2[1], nextId), id: nextId('h2') });
      continue;
    }
    if (/^(---+|\*\*\*+|___+)\s*$/.test(trimmed)) {
      flushParagraph();
      nodes.push({ type: 'hr', children: [textLeaf('')], id: nextId('divider') });
      continue;
    }
    const quote = /^>\s?(.+)$/.exec(trimmed);
    if (quote) {
      flushParagraph();
      nodes.push({ type: 'blockquote', children: parseInlineMarkdown(quote[1], nextId), id: nextId('blockquote') });
      continue;
    }
    const bullet = /^[-*+]\s+(.+)$/.exec(trimmed);
    if (bullet) {
      flushParagraph();
      nodes.push(paragraph(nextId('bullet'), parseInlineMarkdown(bullet[1], nextId), { indent: 1, listStyleType: 'disc' }));
      continue;
    }
    const numbered = /^\d+[.)]\s+(.+)$/.exec(trimmed);
    if (numbered) {
      flushParagraph();
      nodes.push(paragraph(nextId('number'), parseInlineMarkdown(numbered[1], nextId), { indent: 1, listStyleType: 'decimal' }));
      continue;
    }
    paragraphLines.push(line);
  }
  flushParagraph();
  return nodes;
}

export const PUBLISHABLE_BODY_START_MARKER = '<!-- PUBLISHABLE_BODY_START -->';
export const PUBLISHABLE_BODY_END_MARKER = '<!-- PUBLISHABLE_BODY_END -->';

const PUBLISHABLE_BODY_CONTROL_PATTERNS = Object.freeze([
  { label: 'schema parity', pattern: /\bschema[\s_-]+parity\b/i },
  { label: 'control snapshot', pattern: /\bcontrol[\s_-]+snapshot\b/i },
  { label: 'contract snapshot', pattern: /\bcontract[\s_-]+snapshot\b/i },
  { label: 'evidence gate', pattern: /\bevidence[\s_-]+gate\b/i },
  { label: 'renderer status', pattern: /\brenderer[\s_-]+status\b/i },
  { label: 'release status', pattern: /\brelease[\s_-]+status\b/i },
]);

function countExactOccurrences(source, token) {
  let count = 0;
  let cursor = 0;
  while (cursor <= source.length - token.length) {
    const index = source.indexOf(token, cursor);
    if (index === -1) break;
    count += 1;
    cursor = index + token.length;
  }
  return count;
}

/**
 * Extract the only Markdown region that may be converted into an AllinCMS
 * article body. Control records may live outside the markers, but they are
 * never returned to the caller or passed to the Slate converter.
 */
export function extractPublishableArticleMarkdown(
  source,
  { cmsTitleSeparatelySupplied = true } = {},
) {
  if (typeof source !== 'string') throw new Error('Publishable article source must be a string');
  if (typeof cmsTitleSeparatelySupplied !== 'boolean') {
    throw new Error('cmsTitleSeparatelySupplied must be a boolean');
  }

  const startCount = countExactOccurrences(source, PUBLISHABLE_BODY_START_MARKER);
  const endCount = countExactOccurrences(source, PUBLISHABLE_BODY_END_MARKER);
  if (startCount !== 1 || endCount !== 1) {
    throw new Error(
      `Publishable article source must contain exactly one start marker and one end marker; found start=${startCount}, end=${endCount}`,
    );
  }

  const startIndex = source.indexOf(PUBLISHABLE_BODY_START_MARKER);
  const bodyStartIndex = startIndex + PUBLISHABLE_BODY_START_MARKER.length;
  const endIndex = source.indexOf(PUBLISHABLE_BODY_END_MARKER);
  if (endIndex < bodyStartIndex) {
    throw new Error('Publishable article body markers are reversed');
  }

  const sourceBody = source.slice(bodyStartIndex, endIndex).trim();
  if (!sourceBody) throw new Error('Publishable article body must not be empty');

  // Source-only empty anchors provide stable local evidence fragments without
  // leaking raw HTML into the AllinCMS Markdown-to-Slate path. Keep this
  // allowlist intentionally narrow: one safe id attribute, no text, no other
  // attributes, and one anchor per line. All other HTML remains fail-closed.
  const sourceOnlyAnchorPattern = /^[ \t]*<a[ \t]+id="([A-Za-z][A-Za-z0-9:_-]*)"[ \t]*><\/a>[ \t]*$/gim;
  const anchorIds = [...sourceBody.matchAll(sourceOnlyAnchorPattern)].map((match) => match[1].toLowerCase());
  if (new Set(anchorIds).size !== anchorIds.length) {
    throw new Error('Publishable article source-only anchor ids must be unique');
  }
  const body = sourceBody.replace(sourceOnlyAnchorPattern, '').replace(/\n{3,}/g, '\n\n').trim();
  if (!body) throw new Error('Publishable article body must contain buyer-visible content after source-only anchors are removed');

  if (/^[ \t]{0,3}#\s+Article Draft[ \t]*$/im.test(body)) {
    throw new Error('Publishable article body must not contain the internal "# Article Draft" heading');
  }
  for (const { label, pattern } of PUBLISHABLE_BODY_CONTROL_PATTERNS) {
    if (pattern.test(body)) {
      throw new Error(`Publishable article body must not contain internal ${label} control data`);
    }
  }
  if (/\breplace-with-(?:\*|[a-z0-9][a-z0-9_-]*)/i.test(body)) {
    throw new Error('Publishable article body must not contain replace-with-* placeholders');
  }
  if (/\[\s*H[1-6]\s*:[^\]\n]*\]/i.test(body)) {
    throw new Error('Publishable article body must not contain bracketed heading placeholders such as [H2: ...]');
  }
  if (cmsTitleSeparatelySupplied && /^[ \t]{0,3}#(?!#)\s+\S/m.test(body)) {
    throw new Error('Markdown H1 is not allowed when the CMS title is supplied separately');
  }

  return body;
}

/**
 * Explicit safe conversion path for draft files that contain control records
 * around one bounded publishable body.
 */
export function publishableArticleMarkdownToAllinCmsSlate(
  source,
  { idPrefix = 'md', cmsTitleSeparatelySupplied = true } = {},
) {
  const markdown = extractPublishableArticleMarkdown(source, { cmsTitleSeparatelySupplied });
  return markdownToAllinCmsSlate(markdown, { idPrefix });
}
