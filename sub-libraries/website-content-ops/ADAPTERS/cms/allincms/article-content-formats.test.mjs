import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PUBLISHABLE_BODY_END_MARKER,
  PUBLISHABLE_BODY_START_MARKER,
  extractPublishableArticleMarkdown,
  markdownToAllinCmsSlate,
  publishableArticleMarkdownToAllinCmsSlate,
} from './article-content-formats.mjs';

function bounded(body, { before = '', after = '' } = {}) {
  return [before, PUBLISHABLE_BODY_START_MARKER, body, PUBLISHABLE_BODY_END_MARKER, after]
    .filter((part) => part !== '')
    .join('\n');
}

function slateText(nodes) {
  const values = [];
  const visit = (value) => {
    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }
    if (!value || typeof value !== 'object') return;
    if (typeof value.text === 'string') values.push(value.text);
    if (value.children) visit(value.children);
  };
  visit(nodes);
  return values.join(' ');
}

test('extracts the unique bounded body and trims only its outer whitespace', () => {
  const source = bounded('\n## Buyer checklist\n\nUse **verified inputs**.\n', {
    before: '# Article Draft\n\nschema parity: internal-only',
    after: 'release status: BLOCK',
  });
  assert.equal(
    extractPublishableArticleMarkdown(source),
    '## Buyer checklist\n\nUse **verified inputs**.',
  );
});

test('safe wrapper converts only the bounded body and never emits markers or outside control content', () => {
  const source = bounded('## Decision path\n\nSubmit the operating inputs.', {
    before: '# Article Draft\ncontrol snapshot: private',
    after: 'renderer status: BLOCK',
  });
  const nodes = publishableArticleMarkdownToAllinCmsSlate(source, { idPrefix: 'publishable' });
  assert.deepEqual(nodes.map((node) => node.type), ['h2', 'p']);
  const serialized = JSON.stringify(nodes);
  assert.doesNotMatch(serialized, /PUBLISHABLE_BODY_(?:START|END)/);
  assert.doesNotMatch(serialized, /Article Draft|control snapshot|renderer status/);
  assert.match(slateText(nodes), /Decision path/);
  assert.match(slateText(nodes), /Submit the operating inputs/);
});

test('strips only source-only empty anchors before Slate conversion', () => {
  const source = bounded([
    '<a id="stable-decision-section"></a>',
    '',
    '## Decision path',
    '',
    'Submit the operating inputs.',
  ].join('\n'));
  const markdown = extractPublishableArticleMarkdown(source);
  assert.doesNotMatch(markdown, /<a\b|stable-decision-section/);
  assert.match(markdown, /^## Decision path/m);
  const nodes = publishableArticleMarkdownToAllinCmsSlate(source, { idPrefix: 'source-anchor' });
  assert.deepEqual(nodes.map((node) => node.type), ['h2', 'p']);
  assert.doesNotMatch(JSON.stringify(nodes), /stable-decision-section|<a/);
});

test('source-only anchors fail closed on duplicates or additional HTML attributes', () => {
  assert.throws(
    () => extractPublishableArticleMarkdown(bounded([
      '<a id="stable-section"></a>',
      '<a id="stable-section"></a>',
      '## Stable section',
    ].join('\n'))),
    /anchor ids must be unique/,
  );
  assert.throws(
    () => publishableArticleMarkdownToAllinCmsSlate(bounded([
      '<a id="stable-section" class="hidden"></a>',
      '## Stable section',
    ].join('\n'))),
    /Raw HTML is unsupported/,
  );
  assert.throws(
    () => publishableArticleMarkdownToAllinCmsSlate(bounded([
      '<a href="https:\/\/example.test\/"></a>',
      '## Stable section',
    ].join('\n'))),
    /Raw HTML is unsupported/,
  );
});

test('default converter remains unchanged and refuses a full bounded draft instead of converting marker-external content', () => {
  const source = bounded('Safe body', { before: 'private control content' });
  assert.throws(() => markdownToAllinCmsSlate(source), /Raw HTML is unsupported/);
  assert.equal(publishableArticleMarkdownToAllinCmsSlate(source)[0].children[0].text, 'Safe body');
});

test('fails closed when either marker is missing', () => {
  assert.throws(
    () => extractPublishableArticleMarkdown('body only'),
    /exactly one start marker and one end marker; found start=0, end=0/,
  );
  assert.throws(
    () => extractPublishableArticleMarkdown(`${PUBLISHABLE_BODY_START_MARKER}\nbody`),
    /found start=1, end=0/,
  );
  assert.throws(
    () => extractPublishableArticleMarkdown(`body\n${PUBLISHABLE_BODY_END_MARKER}`),
    /found start=0, end=1/,
  );
});

test('fails closed on duplicate start or end markers', () => {
  assert.throws(
    () => extractPublishableArticleMarkdown(
      `${PUBLISHABLE_BODY_START_MARKER}\n${PUBLISHABLE_BODY_START_MARKER}\nbody\n${PUBLISHABLE_BODY_END_MARKER}`,
    ),
    /found start=2, end=1/,
  );
  assert.throws(
    () => extractPublishableArticleMarkdown(
      `${PUBLISHABLE_BODY_START_MARKER}\nbody\n${PUBLISHABLE_BODY_END_MARKER}\n${PUBLISHABLE_BODY_END_MARKER}`,
    ),
    /found start=1, end=2/,
  );
});

test('fails closed on reversed markers and empty bounded bodies', () => {
  assert.throws(
    () => extractPublishableArticleMarkdown(
      `${PUBLISHABLE_BODY_END_MARKER}\nbody\n${PUBLISHABLE_BODY_START_MARKER}`,
    ),
    /markers are reversed/,
  );
  for (const body of ['', '   ', '\n\t\n']) {
    assert.throws(() => extractPublishableArticleMarkdown(bounded(body)), /must not be empty/);
  }
});

test('blocks internal draft headings and control-record vocabulary inside the bounded body', () => {
  assert.throws(
    () => extractPublishableArticleMarkdown(bounded('# Article Draft\n\nBuyer-facing copy.')),
    /internal "# Article Draft" heading/,
  );
  for (const phrase of [
    'schema parity: pass',
    'schema_parity=pass',
    'control snapshot: frozen',
    'contract_snapshot: internal',
    'evidence-gate: BLOCK',
    'renderer status: pending',
    'release_status: BLOCK',
  ]) {
    assert.throws(
      () => extractPublishableArticleMarkdown(bounded(`Buyer-facing copy.\n\n${phrase}`)),
      /must not contain internal .* control data/,
      phrase,
    );
  }
});

test('blocks unresolved replace-with and bracketed heading placeholders', () => {
  for (const placeholder of ['replace-with-product-url', 'REPLACE-WITH-*']) {
    assert.throws(
      () => extractPublishableArticleMarkdown(bounded(`Use ${placeholder} before publishing.`)),
      /replace-with-\* placeholders/,
    );
  }
  for (const placeholder of ['[H2: Buyer pain]', '[ h3 : Proof section ]']) {
    assert.throws(
      () => extractPublishableArticleMarkdown(bounded(`${placeholder}\nBuyer-facing copy.`)),
      /bracketed heading placeholders/,
    );
  }
});

test('blocks Markdown H1 when the CMS title is supplied separately', () => {
  assert.throws(
    () => extractPublishableArticleMarkdown(bounded('# Duplicate CMS title\n\nBody.'), {
      cmsTitleSeparatelySupplied: true,
    }),
    /H1 is not allowed when the CMS title is supplied separately/,
  );
  assert.throws(
    () => publishableArticleMarkdownToAllinCmsSlate(bounded('# Duplicate CMS title\n\nBody.')),
    /H1 is not allowed when the CMS title is supplied separately/,
  );
});

test('legal bounded Markdown converts deterministically through the explicit wrapper', () => {
  const source = bounded([
    '## Selection criteria',
    '',
    '### Required inputs',
    '',
    '- Duty cycle',
    '- Interface dimensions',
    '',
    '> Stop if a required value is unknown.',
  ].join('\n'));
  const first = publishableArticleMarkdownToAllinCmsSlate(source, { idPrefix: 'bounded' });
  const second = publishableArticleMarkdownToAllinCmsSlate(source, { idPrefix: 'bounded' });
  assert.deepEqual(first, second);
  assert.deepEqual(first.map((node) => node.type), ['h2', 'h3', 'p', 'p', 'blockquote']);
});

test('rejects invalid source and title-boundary option types', () => {
  assert.throws(() => extractPublishableArticleMarkdown(null), /must be a string/);
  assert.throws(
    () => extractPublishableArticleMarkdown(bounded('Body.'), { cmsTitleSeparatelySupplied: 'yes' }),
    /must be a boolean/,
  );
});
