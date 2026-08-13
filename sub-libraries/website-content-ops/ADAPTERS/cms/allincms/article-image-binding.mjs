/**
 * Stable Markdown image occurrence binding for AllinCMS article drafts.
 *
 * The public adapter stores no account, site, post, media, deployment, or Server
 * Action identifiers. Runtime values are discovered from an already signed-in
 * Browser tab and belong in a private run directory only.
 *
 * Supported Markdown subset for Slate conversion:
 * - UTF-8 Markdown with LF/CRLF line endings;
 * - inline image syntax: ![alt](path-or-url "optional caption");
 * - every image that is converted to a Slate block must occupy its own line;
 * - ordinary non-empty lines become Slate paragraph nodes.
 *
 * Reference images, HTML <img>, unclosed image tokens, images in headings/lists,
 * and inline images mixed with prose are intentionally blocked instead of being
 * guessed. The tokenizer ignores image-looking text inside fenced/inline code.
 */
import { createHash, randomUUID } from 'node:crypto';
import { mkdir, open, readFile, rename, unlink, writeFile } from 'node:fs/promises';
import { dirname, isAbsolute, resolve } from 'node:path';
import {
  reconcileAllinCmsMediaDirect,
  verifyAllinCmsMediaUrl,
} from './upload-media-browser.mjs';
import { ARTICLE_IMAGE_DRAFT_OPERATION, validateAllinCmsMutationAuthorizationContext } from './mutation-authorization.mjs';
import { COVER_IMAGE_PERSISTED_FIELDS, normalizeArticleCoverImage } from './article-operations.mjs';

const WORKSPACE_ORIGIN = 'https://workspace.laicms.com';
const MANIFEST_SCHEMA_VERSION = 2;
const BINDING_PROOF_VERSION = 1;
const BINDING_PROOF_KIND = 'allincms-article-image-binding-proof';
const ARTICLE_OPERATION_GUARD = Symbol('allincms-article-operation-guard');
const PARSER_NAME = 'allincms-conservative-markdown-image-tokenizer';
const PARSER_VERSION = '1.0.0';
const ACTION_EXPORT_NAME = 'upsertPostAction';

function hash(algorithm, value) {
  return createHash(algorithm).update(value).digest('hex');
}

function sha256(value) {
  return hash('sha256', value);
}

function md5(value) {
  return hash('md5', value);
}

function isoNow() {
  return new Date().toISOString();
}

function normalizeMarkdown(source) {
  if (typeof source !== 'string') throw new TypeError('sourceMarkdown must be a string');
  return source.replace(/\r\n?/g, '\n');
}

function stableNodeId(seed) {
  return `kb-${sha256(seed).slice(0, 16)}`;
}

function isEscaped(source, index) {
  let slashes = 0;
  for (let i = index - 1; i >= 0 && source[i] === '\\'; i -= 1) slashes += 1;
  return slashes % 2 === 1;
}

function parseBracketContent(source, openIndex, openChar, closeChar) {
  let depth = 0;
  let value = '';
  for (let i = openIndex; i < source.length; i += 1) {
    const char = source[i];
    if (char === openChar && !isEscaped(source, i)) {
      depth += 1;
      if (depth > 1) value += char;
      continue;
    }
    if (char === closeChar && !isEscaped(source, i)) {
      depth -= 1;
      if (depth === 0) return { value, end: i + 1 };
      value += char;
      continue;
    }
    value += char;
  }
  return null;
}

function unescapeMarkdownValue(value) {
  return value.replace(/\\([\\`*{}\[\]()#+\-.!<>])/g, '$1');
}

function parseDestinationAndTitle(raw) {
  const value = raw.trim();
  if (!value) throw new Error('Markdown image destination is empty');

  let destination = '';
  let rest = '';
  if (value.startsWith('<')) {
    const close = value.indexOf('>');
    if (close < 0) throw new Error('Unclosed angle-bracket image destination');
    destination = value.slice(1, close);
    rest = value.slice(close + 1).trim();
  } else {
    let depth = 0;
    let splitAt = value.length;
    for (let i = 0; i < value.length; i += 1) {
      const char = value[i];
      if (isEscaped(value, i)) continue;
      if (char === '(') depth += 1;
      if (char === ')' && depth > 0) depth -= 1;
      if (/\s/.test(char) && depth === 0) {
        splitAt = i;
        break;
      }
    }
    destination = value.slice(0, splitAt);
    rest = value.slice(splitAt).trim();
  }

  if (!destination) throw new Error('Markdown image destination is empty');
  let title = '';
  if (rest) {
    const first = rest[0];
    const last = rest.at(-1);
    const validPair = (first === '"' && last === '"')
      || (first === "'" && last === "'")
      || (first === '(' && last === ')');
    if (!validPair) throw new Error(`Unsupported Markdown image title syntax: ${rest}`);
    title = rest.slice(1, -1);
  }

  return {
    destination: unescapeMarkdownValue(destination),
    title: unescapeMarkdownValue(title),
  };
}

function parseInlineImageAt(source, start) {
  if (source[start] !== '!' || source[start + 1] !== '[' || isEscaped(source, start)) return null;
  const altPart = parseBracketContent(source, start + 1, '[', ']');
  if (!altPart) throw new Error(`Unclosed Markdown image alt at character ${start}`);
  let cursor = altPart.end;
  while (cursor < source.length && /[ \t]/.test(source[cursor])) cursor += 1;
  if (source[cursor] === '[') {
    throw new Error(`Reference-style Markdown images are not supported at character ${start}`);
  }
  if (source[cursor] !== '(') {
    throw new Error(`Unsupported Markdown image syntax at character ${start}`);
  }
  const targetPart = parseBracketContent(source, cursor, '(', ')');
  if (!targetPart) throw new Error(`Unclosed Markdown image destination at character ${start}`);
  const { destination, title } = parseDestinationAndTitle(targetPart.value);
  return {
    start,
    end: targetPart.end,
    raw: source.slice(start, targetPart.end),
    alt: unescapeMarkdownValue(altPart.value),
    destination,
    title,
  };
}

function lineInfo(source, index) {
  const before = source.slice(0, index);
  const lineIndex = before.split('\n').length - 1;
  const lineStart = before.lastIndexOf('\n') + 1;
  const newline = source.indexOf('\n', index);
  const lineEnd = newline < 0 ? source.length : newline;
  return {
    lineIndex,
    lineStart,
    lineEnd,
    line: source.slice(lineStart, lineEnd),
  };
}

export function tokenizeMarkdownImages(sourceMarkdown) {
  const source = normalizeMarkdown(sourceMarkdown);
  const occurrences = [];
  let fence = null;
  let inlineTicks = 0;

  for (let i = 0; i < source.length;) {
    const atLineStart = i === 0 || source[i - 1] === '\n';
    if (atLineStart) {
      const lineEnd = source.indexOf('\n', i);
      const line = source.slice(i, lineEnd < 0 ? source.length : lineEnd);
      const fenceMatch = line.match(/^\s*(`{3,}|~{3,})/);
      if (fenceMatch) {
        const marker = fenceMatch[1][0];
        if (!fence) fence = marker;
        else if (fence === marker) fence = null;
        i = lineEnd < 0 ? source.length : lineEnd + 1;
        inlineTicks = 0;
        continue;
      }
    }
    if (fence) {
      i += 1;
      continue;
    }

    if (source[i] === '`' && !isEscaped(source, i)) {
      let run = 1;
      while (source[i + run] === '`') run += 1;
      inlineTicks = inlineTicks === run ? 0 : (inlineTicks === 0 ? run : inlineTicks);
      i += run;
      continue;
    }
    if (source[i] === '\n') inlineTicks = 0;

    if (inlineTicks === 0 && source.slice(i, i + 4).toLowerCase() === '<img') {
      throw new Error(`HTML <img> is not supported at character ${i}`);
    }

    if (inlineTicks === 0 && source[i] === '!' && source[i + 1] === '[' && !isEscaped(source, i)) {
      const parsed = parseInlineImageAt(source, i);
      const info = lineInfo(source, i);
      occurrences.push({
        ...parsed,
        lineIndex: info.lineIndex,
        lineStart: info.lineStart,
        lineEnd: info.lineEnd,
        line: info.line,
      });
      i = parsed.end;
      continue;
    }
    i += 1;
  }

  if (fence) throw new Error('Unclosed fenced code block');
  return { source, occurrences };
}

function anchorText(source, start, end, width = 96) {
  return {
    before: source.slice(Math.max(0, start - width), start),
    after: source.slice(end, Math.min(source.length, end + width)),
  };
}

function sourcePathForDestination(destination, sourceFile, baseDir) {
  if (/^[a-z][a-z0-9+.-]*:/i.test(destination) || destination.startsWith('//')) {
    throw new Error(`Remote image source is not supported for asset fingerprinting: ${destination}`);
  }
  const root = baseDir || (sourceFile ? dirname(resolve(sourceFile)) : (globalThis.process?.cwd?.() || globalThis.nodeRepl?.cwd || '.'));
  return isAbsolute(destination) ? destination : resolve(root, destination);
}

export async function createArticleImageBindingManifest({
  sourceMarkdown,
  articleId,
  sourceFile = null,
  baseDir = null,
  occurrenceMetadata = {},
  readAsset = readFile,
  now = isoNow,
}) {
  if (!articleId || typeof articleId !== 'string') throw new Error('articleId is required');
  const { source, occurrences: tokens } = tokenizeMarkdownImages(sourceMarkdown);
  const assetsById = new Map();
  const occurrences = [];

  for (let index = 0; index < tokens.length; index += 1) {
    const token = tokens[index];
    const localFile = sourcePathForDestination(token.destination, sourceFile, baseDir);
    const bytes = await readAsset(localFile);
    const sourceSha256 = sha256(bytes);
    const assetId = `sha256:${sourceSha256}`;
    const occurrenceOrdinal = index + 1;
    const anchors = anchorText(source, token.start, token.end);
    const occurrenceId = `${articleId}:line-${token.lineIndex + 1}:image-${occurrenceOrdinal}:${sha256(`${token.start}:${token.end}:${assetId}`).slice(0, 12)}`;
    const supplied = occurrenceMetadata[occurrenceId] || occurrenceMetadata[String(occurrenceOrdinal)] || {};
    const role = supplied.role || 'inline-detail';
    const alt = supplied.alt ?? token.alt;
    const caption = supplied.caption ?? token.title;

    if (role !== 'decorative' && !String(alt || '').trim()) {
      throw new Error(`Content image ${occurrenceId} requires non-empty alt text`);
    }

    if (!assetsById.has(assetId)) {
      assetsById.set(assetId, {
        assetId,
        sourceFile: localFile,
        sourceFiles: [localFile],
        sourceSha256: `sha256:${sourceSha256}`,
        sourceMd5: `md5:${md5(bytes)}`,
        description: supplied.description || token.alt || '',
        rights: supplied.rights || 'unknown',
        assetType: supplied.assetType || 'image',
      });
    } else {
      const asset = assetsById.get(assetId);
      if (!asset.sourceFiles.includes(localFile)) asset.sourceFiles.push(localFile);
    }

    occurrences.push({
      occurrenceId,
      articleId,
      assetId,
      sourceReference: token.destination,
      sourceFile: localFile,
      sourceSha256: `sha256:${sourceSha256}`,
      sourceMd5: `md5:${md5(bytes)}`,
      sourceToken: token.raw,
      sourceStart: token.start,
      sourceEnd: token.end,
      sourceBlockPath: `root.lines[${token.lineIndex}]`,
      sourceBlockIndex: token.lineIndex,
      beforeAnchor: anchors.before,
      beforeAnchorSha256: `sha256:${sha256(anchors.before)}`,
      afterAnchor: anchors.after,
      afterAnchorSha256: `sha256:${sha256(anchors.after)}`,
      role,
      articleContext: supplied.articleContext || `${anchors.before}${anchors.after}`.trim(),
      description: supplied.description || token.alt || '',
      alt: role === 'decorative' ? '' : String(alt || '').trim(),
      caption: String(caption || '').trim(),
      mediaId: null,
      url: null,
      bindingStatus: 'pending',
    });
  }

  return {
    schemaVersion: MANIFEST_SCHEMA_VERSION,
    kind: 'allincms-article-image-binding-manifest',
    articleId,
    sourceFile: sourceFile ? resolve(sourceFile) : null,
    sourceContentSha256: `sha256:${sha256(source)}`,
    manifestCreatedAt: now(),
    manifestUpdatedAt: now(),
    sourceParser: {
      name: PARSER_NAME,
      version: PARSER_VERSION,
      contract: 'inline Markdown images; Slate conversion requires image-only lines',
    },
    assets: [...assetsById.values()],
    occurrences,
    runtime: {
      allinCmsDeploymentFingerprint: null,
      mediaVerifiedAt: null,
      draftSavedAt: null,
      backendReadback: null,
    },
  };
}

function assertFreshManifest(source, manifest) {
  const actual = `sha256:${sha256(source)}`;
  if (manifest?.sourceContentSha256 !== actual) {
    throw new Error(`Stale article image manifest: expected ${manifest?.sourceContentSha256 || '(missing)'}, received ${actual}`);
  }
}

function mappingForAsset(mappings, assetId) {
  if (mappings instanceof Map) return mappings.get(assetId);
  return mappings?.[assetId];
}

function normalizedSha256Identity(value) {
  const text = String(value || '').trim().toLowerCase();
  if (!text) return null;
  return text.startsWith('sha256:') ? text : `sha256:${text}`;
}

function mappingSourceSha256(mapping) {
  return normalizedSha256Identity(mapping?.sourceSha256 || mapping?.source_sha256);
}

export async function verifyFreshArticleImageOccurrences({
  manifest,
  readAsset = readFile,
  now = isoNow,
  onProgress = null,
  progressStage = 'occurrence_source_verified',
}) {
  if (manifest?.schemaVersion !== MANIFEST_SCHEMA_VERSION) {
    throw new Error(`Article image manifest schema ${manifest?.schemaVersion ?? '(missing)'} is not supported; rebuild with schema ${MANIFEST_SCHEMA_VERSION}`);
  }
  const assets = Array.isArray(manifest?.assets) ? manifest.assets : [];
  const occurrences = Array.isArray(manifest?.occurrences) ? manifest.occurrences : [];
  const assetsById = new Map(assets.map((asset) => [asset.assetId, asset]));
  const verifiedOccurrences = [];
  const occurrenceIds = new Set();

  // Deliberately serial and occurrence-scoped. Two paths with initially identical
  // bytes may reuse one remote asset, but every local path remains independently
  // accountable and must still match that asset identity at the mutation boundary.
  for (let index = 0; index < occurrences.length; index += 1) {
    const occurrence = occurrences[index];
    if (!occurrence.occurrenceId || occurrenceIds.has(occurrence.occurrenceId)) {
      throw new Error(`Occurrence ID is missing or duplicated; rebuild manifest: ${occurrence.occurrenceId || '(missing)'}`);
    }
    occurrenceIds.add(occurrence.occurrenceId);
    const asset = assetsById.get(occurrence.assetId);
    if (!asset) throw new Error(`Manifest occurrence references an unknown asset: ${occurrence.assetId}`);
    if (!occurrence.sourceFile || !isAbsolute(occurrence.sourceFile)) {
      throw new Error(`Occurrence sourceFile is missing or not absolute; rebuild manifest: ${occurrence.occurrenceId}`);
    }
    if (!Array.isArray(asset.sourceFiles) || !asset.sourceFiles.includes(occurrence.sourceFile)) {
      throw new Error(`Asset sourceFiles does not include occurrence sourceFile; rebuild manifest: ${occurrence.occurrenceId}`);
    }
    if (!occurrence.sourceSha256 || !occurrence.sourceMd5 || !asset.sourceSha256 || !asset.sourceMd5) {
      throw new Error(`Occurrence or asset source hashes are incomplete; rebuild manifest: ${occurrence.occurrenceId}`);
    }
    const bytes = await readAsset(occurrence.sourceFile);
    const actualSha256 = `sha256:${sha256(bytes)}`;
    const actualMd5 = `md5:${md5(bytes)}`;
    if (actualSha256 !== occurrence.assetId
        || occurrence.sourceSha256 !== actualSha256
        || asset.sourceSha256 !== actualSha256) {
      throw new Error(`Stale source image occurrence: ${occurrence.sourceFile}`);
    }
    if (occurrence.sourceMd5 !== actualMd5 || asset.sourceMd5 !== actualMd5) {
      throw new Error(`Source image occurrence MD5 mismatch: ${occurrence.sourceFile}`);
    }
    const evidence = {
      occurrenceId: occurrence.occurrenceId,
      assetId: occurrence.assetId,
      sourceFile: occurrence.sourceFile,
      sourceSha256: actualSha256,
      sourceMd5: actualMd5,
      verifiedAt: now(),
    };
    verifiedOccurrences.push(evidence);
    if (onProgress) await onProgress({
      stage: progressStage,
      current: index + 1,
      total: occurrences.length,
      ...evidence,
    });
  }

  return {
    schemaVersion: MANIFEST_SCHEMA_VERSION,
    articleId: manifest.articleId,
    occurrenceCount: occurrences.length,
    verifiedOccurrences,
    verifiedAt: now(),
  };
}

function mappingVerificationGaps(mapping) {
  const verification = mapping?.verification || {};
  const required = [
    ['contractVerified', verification.contractVerified],
    ['mediaRecordPresent', verification.mediaRecordPresent],
    ['anonymousHttpsGet', verification.anonymousHttpsGet],
    ['browserImageDecodes', verification.browserImageDecodes],
  ];
  return required.filter(([, value]) => value !== true).map(([name]) => name);
}

function assertVerifiedMapping(mapping, occurrence) {
  if (!mapping) throw new Error(`Missing media mapping for ${occurrence.assetId}`);
  if (!mapping.mediaId || !mapping.url) throw new Error(`Incomplete media mapping for ${occurrence.assetId}`);
  const status = mapping.status || mapping.bindingStatus || mapping.verificationStatus;
  if (!['verified', 'reconciled_existing'].includes(status)) {
    throw new Error(`Unverified media mapping status for ${occurrence.assetId}`);
  }
  const verificationGaps = mappingVerificationGaps(mapping);
  if (verificationGaps.length) {
    throw new Error(`Incomplete media verification for ${occurrence.assetId}: ${verificationGaps.join(', ')}`);
  }
  const mappedSourceSha256 = mappingSourceSha256(mapping);
  if (mappedSourceSha256 !== occurrence.assetId) {
    throw new Error(`Media mapping source SHA-256 mismatch for ${occurrence.assetId}`);
  }
  const parsed = new URL(mapping.url);
  if (parsed.protocol !== 'https:') throw new Error(`Media URL must be HTTPS for ${occurrence.assetId}`);
}

function markdownImage(occurrence, mapping) {
  const escapedAlt = String(occurrence.alt || '').replaceAll(']', '\\]');
  const escapedCaption = String(occurrence.caption || '').replaceAll('"', '\\"');
  return `![${escapedAlt}](${mapping.url}${escapedCaption ? ` "${escapedCaption}"` : ''})`;
}

export function replaceMarkdownImageOccurrences({ sourceMarkdown, manifest, mappings }) {
  const source = normalizeMarkdown(sourceMarkdown);
  assertFreshManifest(source, manifest);
  const parsed = tokenizeMarkdownImages(source);
  if (parsed.occurrences.length !== manifest.occurrences.length) {
    throw new Error(`Occurrence count mismatch: source=${parsed.occurrences.length}, manifest=${manifest.occurrences.length}`);
  }

  const replacements = [];
  for (let index = 0; index < manifest.occurrences.length; index += 1) {
    const occurrence = manifest.occurrences[index];
    const token = parsed.occurrences[index];
    if (occurrence.sourceStart !== token.start
        || occurrence.sourceEnd !== token.end
        || occurrence.sourceToken !== token.raw) {
      throw new Error(`Occurrence order or position mismatch at ${occurrence.occurrenceId}`);
    }
    const anchors = anchorText(source, token.start, token.end);
    if (`sha256:${sha256(anchors.before)}` !== occurrence.beforeAnchorSha256
        || `sha256:${sha256(anchors.after)}` !== occurrence.afterAnchorSha256) {
      throw new Error(`Occurrence anchor mismatch at ${occurrence.occurrenceId}`);
    }
    const mapping = mappingForAsset(mappings, occurrence.assetId);
    assertVerifiedMapping(mapping, occurrence);
    replacements.push({
      start: token.start,
      end: token.end,
      occurrenceId: occurrence.occurrenceId,
      text: markdownImage(occurrence, mapping),
      mapping,
    });
  }

  let output = source;
  for (const replacement of [...replacements].sort((a, b) => b.start - a.start)) {
    output = `${output.slice(0, replacement.start)}${replacement.text}${output.slice(replacement.end)}`;
  }
  return { markdown: output, replacements };
}

function paragraphNode(text, lineIndex) {
  return {
    type: 'p',
    id: stableNodeId(`paragraph:${lineIndex}:${text}`),
    children: [{ text }],
  };
}

function imageNode(occurrence, mapping) {
  const node = {
    type: 'img',
    url: mapping.url,
    alt: occurrence.alt || '',
    children: [{ text: '' }],
    id: stableNodeId(`image:${occurrence.occurrenceId}`),
  };
  // AllinCMS currently uses Plate's media caption shape. A plain string is
  // persisted by the backend but crashes the article editor during render.
  if (occurrence.caption) node.caption = [{ text: occurrence.caption }];
  return node;
}

function slateText(value) {
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) return value.map(slateText).join('');
  if (!value || typeof value !== 'object') return '';
  if (typeof value.text === 'string') return value.text;
  return slateText(value.children);
}

function validateArticleSlateContent(content) {
  if (!Array.isArray(content)) throw new Error('Article content must be a Slate node array');
  const ids = new Set();
  for (const [index, node] of content.entries()) {
    if (!node || typeof node !== 'object') throw new Error(`Slate node ${index} must be an object`);
    if (!String(node.id || '').trim()) throw new Error(`Slate node ${index} requires a stable id`);
    if (ids.has(node.id)) throw new Error(`Duplicate Slate node id at index ${index}: ${node.id}`);
    ids.add(node.id);
    if (!Array.isArray(node.children)) throw new Error(`Slate node ${index} requires a children array`);
    if (node.type !== 'img') continue;
    if (!/^https:\/\//.test(String(node.url || ''))) throw new Error(`Image node ${index} requires an HTTPS URL`);
    if (typeof node.alt !== 'string') throw new Error(`Image node ${index} alt must be a string`);
    if (JSON.stringify(node.children) !== JSON.stringify([{ text: '' }])) {
      throw new Error(`Image node ${index} must contain children: [{ text: '' }]`);
    }
    if (Object.hasOwn(node, 'caption')) {
      const captionIsTextNodeArray = Array.isArray(node.caption)
        && node.caption.length > 0
        && node.caption.every((item) => item
          && typeof item === 'object'
          && !Array.isArray(item)
          && typeof item.text === 'string');
      if (!captionIsTextNodeArray) {
        throw new Error(`Image node ${index} caption must be a Slate text-node array, not a string`);
      }
      if (!slateText(node.caption).trim()) throw new Error(`Image node ${index} caption must not be empty when present`);
    }
  }
  return content;
}

function contentSha256(content) {
  return `sha256:${sha256(JSON.stringify(content))}`;
}

function assertArticleBindingAuditZero(audit) {
  const failures = Object.entries(audit || {})
    .filter(([, value]) => value !== 0)
    .map(([name, value]) => `${name}=${value}`);
  if (failures.length) throw new Error(`Article image binding audit failed: ${failures.join(', ')}`);
}

function articleImageBindingProofIdentity({ sourceMarkdown, manifest, mappings, content }) {
  const source = normalizeMarkdown(sourceMarkdown);
  assertFreshManifest(source, manifest);
  const occurrences = Array.isArray(manifest?.occurrences) ? manifest.occurrences : [];
  const mediaIds = [];
  const urls = [];
  const mediaIdOwners = new Map();
  const urlOwners = new Map();
  for (const occurrence of occurrences) {
    const mapping = mappingForAsset(mappings, occurrence.assetId);
    assertVerifiedMapping(mapping, occurrence);
    const mediaOwner = mediaIdOwners.get(mapping.mediaId);
    if (mediaOwner && mediaOwner !== occurrence.assetId) {
      throw new Error(`Different source assets cannot share one mediaId: ${mapping.mediaId}`);
    }
    mediaIdOwners.set(mapping.mediaId, occurrence.assetId);
    const urlOwner = urlOwners.get(mapping.url);
    if (urlOwner && urlOwner !== occurrence.assetId) {
      throw new Error(`Different source assets cannot share one media URL: ${mapping.url}`);
    }
    urlOwners.set(mapping.url, occurrence.assetId);
    mediaIds.push(mapping.mediaId);
    urls.push(mapping.url);
  }
  return {
    kind: BINDING_PROOF_KIND,
    version: BINDING_PROOF_VERSION,
    articleId: manifest.articleId,
    sourceContentSha256: `sha256:${sha256(source)}`,
    occurrenceIds: occurrences.map((item) => item.occurrenceId),
    occurrenceSourceFiles: occurrences.map((item) => item.sourceFile),
    occurrenceSourceHashes: occurrences.map((item) => item.sourceSha256),
    assetIds: occurrences.map((item) => item.assetId),
    mediaIds,
    urls,
    contentSha256: contentSha256(content),
  };
}

function createArticleImageBindingProof({ sourceMarkdown, manifest, mappings, content, audit, now = isoNow }) {
  validateArticleSlateContent(content);
  assertArticleBindingAuditZero(audit);
  const identity = articleImageBindingProofIdentity({ sourceMarkdown, manifest, mappings, content });
  return {
    ...identity,
    audit: structuredClone(audit),
    proofSha256: `sha256:${sha256(JSON.stringify({ identity, audit }))}`,
    createdAt: now(),
  };
}

function assertMatchingArticleImageBindingProof({ bindingProof, sourceMarkdown, manifest, mappings, content, audit }) {
  if (!bindingProof || typeof bindingProof !== 'object') {
    throw new Error('Image-bearing article content requires a build-generated bindingProof');
  }
  const expected = createArticleImageBindingProof({
    sourceMarkdown,
    manifest,
    mappings,
    content,
    audit,
    now: () => bindingProof.createdAt || 'proof-validation',
  });
  if (bindingProof.kind !== BINDING_PROOF_KIND || bindingProof.version !== BINDING_PROOF_VERSION) {
    throw new Error('Article image bindingProof kind or version mismatch');
  }
  if (bindingProof.proofSha256 !== expected.proofSha256) {
    throw new Error('Article image bindingProof does not match the exact source, occurrence order, mappings, and Slate content');
  }
  const identityKeys = [
    'articleId',
    'sourceContentSha256',
    'occurrenceIds',
    'occurrenceSourceFiles',
    'occurrenceSourceHashes',
    'assetIds',
    'mediaIds',
    'urls',
    'contentSha256',
    'audit',
  ];
  for (const key of identityKeys) {
    if (JSON.stringify(bindingProof[key]) !== JSON.stringify(expected[key])) {
      throw new Error(`Article image bindingProof field mismatch: ${key}`);
    }
  }
  return expected;
}

export async function buildAllinCmsSlateContent({
  sourceMarkdown,
  manifest,
  mappings,
  readAsset = readFile,
  now = isoNow,
  onProgress = null,
}) {
  assertFreshManifest(sourceMarkdown, manifest);
  const sourceFreshness = await verifyFreshArticleImageOccurrences({ manifest, readAsset, now, onProgress });
  const bound = replaceMarkdownImageOccurrences({ sourceMarkdown, manifest, mappings });
  const lines = bound.markdown.split('\n');
  const occurrenceByLine = new Map();
  for (const occurrence of manifest.occurrences) {
    if (occurrenceByLine.has(occurrence.sourceBlockIndex)) {
      throw new Error(`Multiple images on one line are not supported: line ${occurrence.sourceBlockIndex + 1}`);
    }
    occurrenceByLine.set(occurrence.sourceBlockIndex, occurrence);
  }

  const content = [];
  const boundOccurrences = [];
  let boundCount = 0;
  for (let lineIndex = 0; lineIndex < lines.length; lineIndex += 1) {
    const line = lines[lineIndex];
    const occurrence = occurrenceByLine.get(lineIndex);
    if (occurrence) {
      const tokenized = tokenizeMarkdownImages(line);
      if (tokenized.occurrences.length !== 1
          || line.trim() !== tokenized.occurrences[0].raw) {
        throw new Error(`Slate conversion requires an image-only line at line ${lineIndex + 1}`);
      }
      const mapping = mappingForAsset(mappings, occurrence.assetId);
      assertVerifiedMapping(mapping, occurrence);
      const node = imageNode(occurrence, mapping);
      content.push(node);
      boundOccurrences.push({
        ...occurrence,
        mediaId: mapping.mediaId,
        url: mapping.url,
        bindingStatus: 'verified',
        slateNodeId: node.id,
      });
      boundCount += 1;
      if (onProgress) await onProgress({
        stage: 'occurrence_bound',
        current: boundCount,
        total: manifest.occurrences.length,
        occurrenceId: occurrence.occurrenceId,
        sourceFile: occurrence.sourceFile,
        assetId: occurrence.assetId,
        mediaId: mapping.mediaId,
        url: mapping.url,
      });
      continue;
    }
    if (line.includes('![')) throw new Error(`Unresolved or unexpected image token at line ${lineIndex + 1}`);
    if (line.trim()) content.push(paragraphNode(line, lineIndex));
  }
  if (!content.length) content.push(paragraphNode('', 0));
  if (content.at(-1)?.type === 'img') content.push(paragraphNode('', lines.length));

  validateArticleSlateContent(content);
  const audit = auditArticleImageBinding({ sourceMarkdown, manifest, mappings, content });
  assertArticleBindingAuditZero(audit);
  const bindingProof = createArticleImageBindingProof({
    sourceMarkdown,
    manifest,
    mappings,
    content,
    audit,
    now,
  });

  return {
    markdown: bound.markdown,
    content,
    sourceFreshness,
    bindingProof,
    manifest: {
      ...manifest,
      manifestUpdatedAt: now(),
      occurrences: boundOccurrences,
    },
    audit,
  };
}

export function auditArticleImageBinding({ sourceMarkdown, manifest, mappings, content }) {
  const source = normalizeMarkdown(sourceMarkdown);
  const nodes = Array.isArray(content) ? content : [];
  const imageNodes = nodes.filter((node) => node?.type === 'img');
  const actualImagePositions = nodes
    .map((node, index) => node?.type === 'img' ? index : null)
    .filter((value) => value !== null);
  const occurrenceByLine = new Map(manifest.occurrences.map((occurrence) => [occurrence.sourceBlockIndex, occurrence]));
  const expectedImagePositions = [];
  let expectedNodeIndex = 0;
  for (const [lineIndex, line] of source.split('\n').entries()) {
    if (occurrenceByLine.has(lineIndex)) {
      expectedImagePositions.push(expectedNodeIndex);
      expectedNodeIndex += 1;
    } else if (line.trim()) {
      expectedNodeIndex += 1;
    }
  }
  const uniqueMappings = [...new Set(manifest.occurrences.map((occurrence) => occurrence.assetId))]
    .map((assetId) => mappingForAsset(mappings, assetId));
  const expectedUrls = manifest.occurrences.map((occurrence) => mappingForAsset(mappings, occurrence.assetId)?.url || null);
  const actualUrls = imageNodes.map((node) => node.url || null);
  const missingAlt = manifest.occurrences.filter((occurrence) => occurrence.role !== 'decorative' && !String(occurrence.alt || '').trim()).length;
  const localPaths = imageNodes.filter((node) => node.url && !/^https:\/\//.test(node.url)).length;
  const positionMismatchCount = expectedImagePositions.length === actualImagePositions.length
    ? expectedImagePositions.filter((position, index) => position !== actualImagePositions[index]).length
    : Math.abs(expectedImagePositions.length - actualImagePositions.length) + 1;
  return {
    unresolved_image_placeholders: imageNodes.filter((node) => !node.url || !/^https:\/\//.test(node.url)).length,
    local_file_paths: localPaths,
    missing_asset_mappings: manifest.occurrences.filter((occurrence) => !mappingForAsset(mappings, occurrence.assetId)).length,
    missing_occurrence_bindings: Math.max(0, manifest.occurrences.length - imageNodes.length),
    unexpected_extra_images: Math.max(0, imageNodes.length - manifest.occurrences.length),
    image_order_mismatches: expectedUrls.length === actualUrls.length
      ? expectedUrls.filter((url, index) => url !== actualUrls[index]).length
      : Math.abs(expectedUrls.length - actualUrls.length) + 1,
    image_position_mismatches: positionMismatchCount,
    stale_article_manifest: manifest.sourceContentSha256 === `sha256:${sha256(source)}` ? 0 : 1,
    broken_public_urls: uniqueMappings.filter((mapping) => mapping?.verification?.anonymousHttpsGet !== true).length,
    image_decode_failures: uniqueMappings.filter((mapping) => mapping?.verification?.browserImageDecodes !== true).length,
    missing_required_alt_in_expected_content: missingAlt,
    unreviewed_uncertain_claims: 0,
  };
}

export async function verifyArticleMediaMappings({
  tab,
  expectedSiteKey,
  manifest,
  candidates,
  reconcile = reconcileAllinCmsMediaDirect,
  verifyUrl = verifyAllinCmsMediaUrl,
  now = isoNow,
}) {
  const current = new URL(await tab.url());
  if (current.origin !== WORKSPACE_ORIGIN || current.pathname !== `/${expectedSiteKey}/media`) {
    throw new Error(`Open the exact signed-in media page first: ${WORKSPACE_ORIGIN}/${expectedSiteKey}/media`);
  }
  const verified = {};
  const uniqueAssetIds = [...new Set(manifest.occurrences.map((item) => item.assetId))];

  // Deliberately serial. Do not introduce concurrent aggregation here.
  for (const assetId of uniqueAssetIds) {
    const candidate = mappingForAsset(candidates, assetId);
    if (!candidate?.expectedTitle) throw new Error(`Missing expectedTitle for ${assetId}`);
    if (mappingSourceSha256(candidate) !== assetId) throw new Error(`Candidate source SHA-256 mismatch for ${assetId}`);
    if (!candidate.mediaId || !candidate.url) throw new Error(`Candidate media ID and URL are required for ${assetId}`);
    const result = await reconcile({
      tab,
      expectedSiteKey,
      expectedTitle: candidate.expectedTitle,
      controlledReload: true,
    });
    if (result.status !== 'reconciled_existing') {
      throw new Error(`Media reconciliation stopped for ${assetId}: ${result.status}`);
    }
    if (candidate.mediaId && result.media.mediaId !== candidate.mediaId) {
      throw new Error(`Media ID mismatch for ${assetId}`);
    }
    if (candidate.url && result.media.url !== candidate.url) {
      throw new Error(`Media URL mismatch for ${assetId}`);
    }
    const anonymous = await verifyUrl({
      url: result.media.url,
      expectedSiteKey,
      expectedMimeType: result.media.mimeType,
    });
    if (!anonymous.ok) throw new Error(`Public media verification failed for ${assetId}`);
    if (result.image?.ok !== true) throw new Error(`Browser image decode failed for ${assetId}`);
    verified[assetId] = {
      status: 'verified',
      sourceSha256: assetId,
      expectedTitle: candidate.expectedTitle,
      mediaId: result.media.mediaId,
      url: result.media.url,
      mimeType: result.media.mimeType,
      verification: {
        contractVerified: true,
        mediaRecordPresent: true,
        anonymousHttpsGet: true,
        browserImageDecodes: result.image?.ok === true,
      },
      verifiedAt: now(),
    };
  }
  return verified;
}

function extractBalancedJson(text, marker) {
  const markerIndex = text.indexOf(marker);
  if (markerIndex < 0) return null;
  const start = text.indexOf('{', markerIndex + marker.length);
  if (start < 0) return null;
  let depth = 0;
  let inString = false;
  let escaped = false;
  for (let i = start; i < text.length; i += 1) {
    const char = text[i];
    if (inString) {
      if (escaped) escaped = false;
      else if (char === '\\') escaped = true;
      else if (char === '"') inString = false;
      continue;
    }
    if (char === '"') inString = true;
    else if (char === '{') depth += 1;
    else if (char === '}') {
      depth -= 1;
      if (depth === 0) return text.slice(start, i + 1);
    }
  }
  return null;
}

export async function readAllinCmsArticleDraftFromPage({ tab, expectedSiteKey, expectedPostId }) {
  const current = new URL(await tab.url());
  const expectedPath = `/${expectedSiteKey}/posts/${expectedPostId}/update`;
  if (current.origin !== WORKSPACE_ORIGIN || current.pathname !== expectedPath) {
    throw new Error(`Open the exact signed-in article update page first: ${WORKSPACE_ORIGIN}${expectedPath}`);
  }
  const pageState = await tab.playwright.evaluate(() => ({
    scripts: [...document.scripts]
      .map((script) => script.textContent || '')
      .filter((text) => text.includes('"defaultValues"') || text.includes('\\"defaultValues\\"') || text.includes('"site":{') || text.includes('\\"site\\":{'))
      .slice(0, 8),
    scriptSources: [...document.scripts].map((script) => script.src).filter(Boolean),
    statusBadges: [...document.querySelectorAll('[data-slot="badge"]')]
      .map((badge) => badge.textContent?.trim() || '')
      .filter(Boolean),
  }));
  let defaults = null;
  let siteId = null;
  let observedSiteKey = null;
  for (const raw of pageState.scripts) {
    const text = raw.replaceAll('\\"', '"');
    const json = extractBalancedJson(text, '"defaultValues":');
    if (json && !defaults) {
      try { defaults = JSON.parse(json); } catch { /* continue */ }
    }
    const site = text.match(/"site":\{"id":"([0-9a-f]{24})","name":"[^"]+","slug":"([^"]+)"/);
    if (site) {
      siteId = site[1];
      observedSiteKey = site[2];
    }
  }
  if (!defaults) throw new Error('Could not read article defaultValues from the current RSC state');
  if (!siteId || observedSiteKey !== expectedSiteKey) throw new Error('Could not confirm the current internal site ID');
  const isDraft = pageState.statusBadges.some((value) => /^(草稿|draft)$/i.test(value));
  if (!isDraft) throw new Error('Current article is not confirmed as a draft; publishing-state changes are outside this adapter');
  return {
    siteId,
    postId: expectedPostId,
    isDraft,
    defaults,
    scriptSources: pageState.scriptSources,
  };
}

async function discoverArticleActionContract({ tab, cdp, expectedSiteKey, expectedPostId, readDraft = readAllinCmsArticleDraftFromPage }) {
  const pageState = await readDraft({ tab, expectedSiteKey, expectedPostId });
  const deploymentIds = [...new Set(pageState.scriptSources
    .map((source) => source.match(/[?&]dpl=([0-9a-f]{40})/)?.[1])
    .filter(Boolean))];
  if (deploymentIds.length !== 1) throw new Error(`Expected one deployment fingerprint; observed ${deploymentIds.length}`);

  const actionIds = new Set();
  for (const source of pageState.scriptSources) {
    const response = await fetch(source, { credentials: 'omit' });
    if (!response.ok) throw new Error(`Could not read AllinCMS client chunk: HTTP ${response.status}`);
    const text = await response.text();
    const pattern = new RegExp(`createServerReference\\)\\("([0-9a-f]{32,64})"[\\s\\S]{0,240}"${ACTION_EXPORT_NAME}"\\)`, 'g');
    for (const match of text.matchAll(pattern)) actionIds.add(match[1]);
  }
  if (actionIds.size !== 1) throw new Error(`Expected one ${ACTION_EXPORT_NAME} Server Action reference; observed ${actionIds.size}`);

  const routerResult = await cdp.send('Runtime.evaluate', {
    expression: 'JSON.stringify(history.state?.__PRIVATE_NEXTJS_INTERNALS_TREE?.tree || null)',
    returnByValue: true,
  });
  if (routerResult?.exceptionDetails) throw new Error('Could not read the current Next.js router tree');
  const routerTree = routerResult?.result?.value;
  if (!routerTree || routerTree === 'null') throw new Error('Current Next.js router tree is unavailable');
  const actionId = [...actionIds][0];
  return {
    actionId,
    actionIdLength: actionId.length,
    actionIdSha256: sha256(actionId),
    deploymentId: deploymentIds[0],
    deploymentFingerprint: deploymentIds[0],
    routerTree,
    draft: pageState,
  };
}

function runtimeValue(result) {
  if (result?.exceptionDetails) {
    throw new Error(result.exceptionDetails.exception?.description
      || result.exceptionDetails.text
      || 'CDP Runtime.evaluate failed');
  }
  return result?.result?.value;
}

function summarizeArticleNetwork(events, expectedPath) {
  const requests = new Map();
  const responses = new Map();
  for (const event of events) {
    if (event.method === 'Network.requestWillBeSent') requests.set(event.params.requestId, event.params);
    if (event.method === 'Network.responseReceived') responses.set(event.params.requestId, event.params.response);
  }
  const actions = [...requests.values()].filter((params) => {
    try {
      const url = new URL(params.request.url);
      return params.request.method === 'POST'
        && url.origin === WORKSPACE_ORIGIN
        && url.pathname === expectedPath;
    } catch {
      return false;
    }
  });
  return {
    actionCount: actions.length,
    action: actions.length === 1 ? {
      requestId: actions[0].requestId,
      responseStatus: responses.get(actions[0].requestId)?.status ?? null,
      responseContentType: responses.get(actions[0].requestId)?.mimeType ?? null,
      postDataBytes: Buffer.byteLength(actions[0].request.postData || ''),
    } : null,
  };
}

function normalizedDraftPayload(defaults, overrides, siteId, postId) {
  const payload = {
    title: overrides.title ?? defaults.title,
    slug: overrides.slug ?? defaults.slug,
    excerpt: overrides.excerpt ?? defaults.excerpt ?? '',
    order: overrides.order ?? defaults.order ?? 0,
    coverImage: Object.hasOwn(overrides, 'coverImage') ? overrides.coverImage : (defaults.coverImage ?? null),
    categories: overrides.categories ?? defaults.categories ?? [],
    tags: overrides.tags ?? defaults.tags ?? [],
    content: overrides.content ?? defaults.content,
    siteId,
    postId,
    mode: 'update',
  };
  if (!String(payload.title || '').trim()) throw new Error('Article title is required');
  if (!String(payload.slug || '').trim()) throw new Error('Article slug is required');
  validateArticleSlateContent(payload.content);
  payload.coverImage = normalizeArticleCoverImage(payload.coverImage);
  return payload;
}

function persistedCoverImageShape(value) {
  if (value === null || value === undefined) return value ?? null;
  return Object.fromEntries(COVER_IMAGE_PERSISTED_FIELDS
    .filter((field) => Object.hasOwn(value, field))
    .map((field) => [field, value[field]]));
}

function compareReadback(payload, defaults) {
  const fields = ['title', 'slug', 'excerpt', 'order', 'coverImage', 'categories', 'tags', 'content'];
  const mismatches = [];
  for (const field of fields) {
    const expected = field === 'coverImage' ? persistedCoverImageShape(payload[field]) : payload[field];
    const actual = field === 'coverImage' ? persistedCoverImageShape(defaults[field]) : defaults[field];
    if (JSON.stringify(expected) !== JSON.stringify(actual)) mismatches.push(field);
  }
  return mismatches;
}

async function verifyArticleEditorPage({ tab, expectedContent = [] }) {
  const expectedImages = expectedContent.filter((node) => node?.type === 'img');
  const expectedCaptions = expectedImages
    .map((node) => slateText(node.caption).trim())
    .filter(Boolean);
  const state = await tab.playwright.evaluate(() => {
    const editor = document.querySelector('[data-slate-editor="true"][contenteditable="true"]');
    const articleImages = editor ? [...editor.querySelectorAll('img')] : [];
    return {
      heading: document.querySelector('h1')?.textContent?.trim() || '',
      bodyText: document.body?.innerText?.slice(0, 2_000) || '',
      editorPresent: Boolean(editor),
      articleImageCount: articleImages.length,
      decodedArticleImageCount: articleImages.filter((image) => image.complete && image.naturalWidth > 0).length,
      editorDomAltMissing: articleImages.filter((image) => !String(image.getAttribute('alt') || '').trim()).length,
      visibleCaptions: editor
        ? [...editor.querySelectorAll('figcaption')].map((caption) => caption.textContent?.trim() || '').filter(Boolean)
        : [],
      statusBadges: [...document.querySelectorAll('[data-slot="badge"]')]
        .map((badge) => badge.textContent?.trim() || '')
        .filter(Boolean),
    };
  });
  const error500 = state.heading === '500'
    || state.bodyText.includes("Oops! Something went wrong")
    || state.bodyText.includes('We apologize for the inconvenience.');
  const draftLabelPresent = state.statusBadges.some((value) => /^(草稿|draft)$/i.test(value));
  const captionsMatch = JSON.stringify(state.visibleCaptions) === JSON.stringify(expectedCaptions);
  const errors = [];
  if (error500) errors.push('article editor rendered an error page');
  if (!state.editorPresent) errors.push('Slate editor is missing');
  if (state.articleImageCount !== expectedImages.length) errors.push(`article image count mismatch: expected ${expectedImages.length}, observed ${state.articleImageCount}`);
  if (state.decodedArticleImageCount !== expectedImages.length) errors.push(`article image decode mismatch: expected ${expectedImages.length}, decoded ${state.decodedArticleImageCount}`);
  if (!captionsMatch) errors.push('visible editor captions do not match the saved Slate captions');
  if (!draftLabelPresent) errors.push('draft status badge is missing');
  return {
    ok: errors.length === 0,
    errors,
    error500,
    heading: state.heading,
    editorPresent: state.editorPresent,
    articleImageCount: state.articleImageCount,
    decodedArticleImageCount: state.decodedArticleImageCount,
    expectedImageCount: expectedImages.length,
    visibleCaptions: state.visibleCaptions,
    expectedCaptions,
    captionsMatch,
    draftLabelPresent,
    editorDomAltMissing: state.editorDomAltMissing,
  };
}

export async function saveAllinCmsArticleDraftDirect({
  tab,
  expectedSiteKey,
  expectedPostId,
  overrides,
  bindingProof = null,
  sourceMarkdown = null,
  manifest = null,
  mappings = null,
  readAsset = readFile,
  onProgress = null,
  authorizationContext = null,
  timeoutMs = 30_000,
  _operationGuard = null,
  _internal = {},
}) {
  const authorizationTarget = { post_id: String(expectedPostId || '').trim() };
  validateAllinCmsMutationAuthorizationContext(authorizationContext, {
    expectedSiteKey, operation: ARTICLE_IMAGE_DRAFT_OPERATION, target: authorizationTarget,
  });
  if (Object.hasOwn(overrides || {}, 'content')) validateArticleSlateContent(overrides.content);
  if (!tab?.playwright || !tab?.capabilities) throw new Error('A claimed Browser tab with Playwright and CDP is required');
  const expectedPath = `/${expectedSiteKey}/posts/${expectedPostId}/update`;
  const current = new URL(await tab.url());
  if (current.origin !== WORKSPACE_ORIGIN || current.pathname !== expectedPath) {
    throw new Error(`Open the exact signed-in article update page first: ${WORKSPACE_ORIGIN}${expectedPath}`);
  }

  const cdp = _internal.cdp || await tab.capabilities.get('cdp');
  await cdp.send('Network.enable', {});
  const contract = _internal.contract || await discoverArticleActionContract({
    tab,
    cdp,
    expectedSiteKey,
    expectedPostId,
    readDraft: _internal.readDraft || readAllinCmsArticleDraftFromPage,
  });
  const payload = normalizedDraftPayload(contract.draft.defaults, overrides || {}, contract.draft.siteId, expectedPostId);
  const imageNodes = payload.content.filter((node) => node?.type === 'img');
  let validatedBindingProof = null;
  if (imageNodes.length) {
    if (!bindingProof || typeof bindingProof !== 'object') {
      throw new Error('Image-bearing article content requires a build-generated bindingProof');
    }
    if (typeof sourceMarkdown !== 'string' || !manifest || !mappings) {
      throw new Error('Image-bearing article content requires sourceMarkdown, manifest, and verified mappings at the save boundary');
    }
    const guardMatchesTarget = _operationGuard?.[ARTICLE_OPERATION_GUARD] === true
      && _operationGuard.expectedSiteKey === expectedSiteKey
      && _operationGuard.expectedPostId === expectedPostId;
    if (!guardMatchesTarget) {
      throw new Error('Image-bearing article drafts must use bindAndSaveAllinCmsArticleDraftDirect so one article operation lock covers build, save, readback, and manifest write');
    }
    await verifyFreshArticleImageOccurrences({
      manifest,
      readAsset,
      onProgress,
      progressStage: 'occurrence_source_reverified_before_save',
    });
    const audit = auditArticleImageBinding({ sourceMarkdown, manifest, mappings, content: payload.content });
    assertArticleBindingAuditZero(audit);
    validatedBindingProof = assertMatchingArticleImageBindingProof({
      bindingProof,
      sourceMarkdown,
      manifest,
      mappings,
      content: payload.content,
      audit,
    });
  }
  const cursor = _internal.cursor || await cdp.readEvents({
    methods: ['Network.requestWillBeSent', 'Network.responseReceived'],
    limit: 1,
    timeoutMs: 1,
  });
  const expression = `(async()=>{const response=await window.fetch(location.pathname,{method:'POST',credentials:'include',headers:{Accept:'text/x-component','Content-Type':'text/plain;charset=UTF-8','next-action':${JSON.stringify(contract.actionId)},'next-router-state-tree':${JSON.stringify(contract.routerTree)},'x-deployment-id':${JSON.stringify(contract.deploymentId)}},body:${JSON.stringify(JSON.stringify([payload]))}});const text=await response.text();return {status:response.status,ok:response.ok,contentType:response.headers.get('content-type'),responseBytes:text.length};})()`;

  let requestMayHaveSucceeded = false;
  try {
    validateAllinCmsMutationAuthorizationContext(authorizationContext, {
      expectedSiteKey, operation: ARTICLE_IMAGE_DRAFT_OPERATION, target: authorizationTarget,
    });
    requestMayHaveSucceeded = true;
    const replay = _internal.sendReplay
      ? await _internal.sendReplay({ cdp, expression, timeoutMs, payload })
      : runtimeValue(await cdp.send('Runtime.evaluate', {
        expression,
        awaitPromise: true,
        returnByValue: true,
      }, { timeoutMs }));
    const captured = _internal.readCaptured
      ? await _internal.readCaptured({ cdp, cursor })
      : await cdp.readEvents({
        afterSequence: cursor.cursor,
        methods: ['Network.requestWillBeSent', 'Network.responseReceived'],
        limit: 1000,
        timeoutMs: 1_500,
      });
    const network = summarizeArticleNetwork(captured.events || captured, expectedPath);
    const errors = [];
    if (replay?.status !== 200) errors.push(`direct draft save returned HTTP ${replay?.status ?? 'unknown'}`);
    if (!String(replay?.contentType || '').startsWith('text/x-component')) errors.push(`unexpected response Content-Type ${replay?.contentType || '(missing)'}`);
    if (network.actionCount !== 1) errors.push(`expected one article Server Action request; observed ${network.actionCount}`);
    if (network.action?.responseStatus !== 200) errors.push(`captured Server Action response was ${network.action?.responseStatus ?? 'missing'}`);
    if (errors.length) {
      const error = new Error(`Article draft save is ambiguous: ${errors.join('; ')}`);
      error.result = { status: 'article_save_ambiguous', requestMayHaveSucceeded: true, automaticRetryAllowed: false, errors, replay, network };
      throw error;
    }

    if (_internal.reloadPage) await _internal.reloadPage({ tab, timeoutMs });
    else await tab.reload();
    const readback = _internal.readback
      ? await _internal.readback({ tab, expectedSiteKey, expectedPostId })
      : await readAllinCmsArticleDraftFromPage({ tab, expectedSiteKey, expectedPostId });
    const mismatches = compareReadback(payload, readback.defaults);
    if (mismatches.length) {
      const error = new Error(`Article draft readback mismatch: ${mismatches.join(', ')}`);
      error.result = {
        status: 'article_readback_mismatch',
        requestMayHaveSucceeded: true,
        automaticRetryAllowed: false,
        mismatches,
        network,
      };
      throw error;
    }
    const editorPage = _internal.verifyEditorPage
      ? await _internal.verifyEditorPage({ tab, expectedSiteKey, expectedPostId, expectedContent: payload.content })
      : await verifyArticleEditorPage({ tab, expectedContent: payload.content });
    if (!editorPage?.ok) {
      const error = new Error('Article draft data was saved, but the editor page failed to render after reload');
      error.result = {
        status: 'article_editor_render_failed',
        requestMayHaveSucceeded: true,
        readbackVerified: true,
        automaticRetryAllowed: false,
        published: false,
        editorPage,
        network,
      };
      throw error;
    }
    return {
      status: 'draft_saved_and_readback_verified',
      published: false,
      automaticRetryAllowed: false,
      payload,
      readback: readback.defaults,
      editorPage,
      network,
      contract: {
        actionIdStored: false,
        actionIdLength: contract.actionIdLength,
        actionIdSha256: contract.actionIdSha256,
        deploymentFingerprint: contract.deploymentFingerprint,
      },
      bindingProof: validatedBindingProof ? {
        kind: validatedBindingProof.kind,
        version: validatedBindingProof.version,
        proofSha256: validatedBindingProof.proofSha256,
        contentSha256: validatedBindingProof.contentSha256,
      } : null,
      savedAt: isoNow(),
    };
  } catch (error) {
    if (error.result) throw error;
    const wrapped = new Error(`Article draft save stopped: ${error.message}`);
    wrapped.result = {
      status: requestMayHaveSucceeded ? 'article_save_ambiguous' : 'article_save_blocked_before_request',
      requestMayHaveSucceeded,
      automaticRetryAllowed: false,
      errors: [error.message],
    };
    throw wrapped;
  }
}

async function acquireArticleOperationLock({
  lockPath,
  expectedSiteKey,
  expectedPostId,
  manifestPath,
  _internal = {},
}) {
  await mkdir(dirname(lockPath), { recursive: true });
  let handle;
  try {
    handle = _internal.openOperationLock
      ? await _internal.openOperationLock(lockPath)
      : await open(lockPath, 'wx');
    if (handle?.writeFile) {
      await handle.writeFile(`${JSON.stringify({
        pid: globalThis.process?.pid ?? null,
        acquiredAt: isoNow(),
        expectedSiteKey,
        expectedPostId,
        manifestPath,
      })}\n`, 'utf8');
    }
  } catch (error) {
    if (error.code === 'EEXIST') throw new Error(`Article operation is already locked: ${lockPath}`);
    throw error;
  }
  return handle;
}

async function releaseArticleOperationLock({ lockPath, handle, _internal = {} }) {
  try { if (handle?.close) await handle.close(); } catch { /* unlink still attempted below */ }
  if (_internal.unlinkOperationLock) await _internal.unlinkOperationLock(lockPath);
  else {
    try { await unlink(lockPath); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
}

/**
 * The only supported image-bearing article mutation entry.
 *
 * Images are checked and bound occurrence by occurrence, but the complete Slate
 * draft is sent exactly once. The article-scoped lock stays held across local
 * source verification, binding, the remote save, readback, editor health check,
 * and the final atomic manifest write.
 */
export async function bindAndSaveAllinCmsArticleDraftDirect({
  tab,
  expectedSiteKey,
  expectedPostId,
  sourceMarkdown,
  manifest,
  mappings,
  manifestPath,
  overrides = {},
  authorizationContext = null,
  operationLockPath = null,
  readAsset = readFile,
  onProgress = null,
  timeoutMs = 30_000,
  _internal = {},
}) {
  const authorizationTarget = { post_id: String(expectedPostId || '').trim() };
  validateAllinCmsMutationAuthorizationContext(authorizationContext, {
    expectedSiteKey, operation: ARTICLE_IMAGE_DRAFT_OPERATION, target: authorizationTarget,
  });
  if (!manifestPath) throw new Error('manifestPath is required for an image-bearing article operation');
  if (!isAbsolute(manifestPath)) throw new Error('manifestPath must be absolute');
  if (!/^[A-Za-z0-9_-]+$/.test(String(expectedSiteKey || ''))) throw new Error('expectedSiteKey must be one safe route segment');
  if (!/^[A-Za-z0-9_-]+$/.test(String(expectedPostId || ''))) throw new Error('expectedPostId must be one safe route segment');
  const lockPath = operationLockPath
    || `${manifestPath}.${expectedSiteKey}.${expectedPostId}.operation.lock`;
  if (!isAbsolute(lockPath)) throw new Error('operationLockPath must be absolute');
  if (!tab?.playwright || !tab?.capabilities) throw new Error('A claimed Browser tab with Playwright and CDP is required');
  const expectedPath = `/${expectedSiteKey}/posts/${expectedPostId}/update`;
  const current = new URL(await tab.url());
  if (current.origin !== WORKSPACE_ORIGIN || current.pathname !== expectedPath) {
    throw new Error(`Open the exact signed-in article update page first: ${WORKSPACE_ORIGIN}${expectedPath}`);
  }
  let lockHandle;
  let primaryError = null;
  let remoteSaveCompleted = false;

  try {
    lockHandle = await acquireArticleOperationLock({
      lockPath,
      expectedSiteKey,
      expectedPostId,
      manifestPath,
      _internal,
    });
    const built = await buildAllinCmsSlateContent({
      sourceMarkdown,
      manifest,
      mappings,
      readAsset,
      onProgress,
    });
    if (_internal.afterBuild) await _internal.afterBuild({ built, lockPath });

    const operationGuard = {
      [ARTICLE_OPERATION_GUARD]: true,
      expectedSiteKey,
      expectedPostId,
      lockPath,
    };
    const saveDraft = _internal.saveDraft || saveAllinCmsArticleDraftDirect;
    const saveResult = await saveDraft({
      tab,
      expectedSiteKey,
      expectedPostId,
      overrides: { ...overrides, content: built.content },
      bindingProof: built.bindingProof,
      sourceMarkdown,
      manifest,
      mappings,
      readAsset,
      onProgress,
      authorizationContext,
      timeoutMs,
      _operationGuard: operationGuard,
      _internal: _internal.saveInternal || {},
    });
    remoteSaveCompleted = true;

    const completedManifest = {
      ...built.manifest,
      runtime: {
        ...(built.manifest.runtime || {}),
        allinCmsDeploymentFingerprint: saveResult.contract?.deploymentFingerprint || null,
        draftSavedAt: saveResult.savedAt || isoNow(),
        backendReadback: {
          status: saveResult.status,
          editorVerified: saveResult.editorPage?.ok === true,
          bindingProofSha256: built.bindingProof.proofSha256,
        },
      },
    };
    const writeManifest = _internal.writeManifest || writeArticleImageBindingManifest;
    let manifestWrite;
    try {
      manifestWrite = await writeManifest({ manifestPath, manifest: completedManifest });
    } catch (error) {
      const wrapped = new Error(`Article draft may be saved, but the local binding manifest was not written: ${error.message}`);
      wrapped.result = {
        status: 'article_manifest_write_failed_after_save',
        requestMayHaveSucceeded: true,
        automaticRetryAllowed: false,
        errors: [error.message],
        saveResult,
      };
      throw wrapped;
    }

    return {
      status: 'article_images_bound_draft_saved_and_manifest_written',
      published: false,
      automaticRetryAllowed: false,
      lockPath,
      build: built,
      save: saveResult,
      manifest: completedManifest,
      manifestWrite,
    };
  } catch (error) {
    primaryError = error;
    throw error;
  } finally {
    if (lockHandle) {
      try {
        await releaseArticleOperationLock({ lockPath, handle: lockHandle, _internal });
      } catch (lockError) {
        if (primaryError) {
          primaryError.lockReleaseError = lockError.message;
        } else {
          const wrapped = new Error(`Article operation completed but its lock could not be released: ${lockError.message}`);
          wrapped.result = {
            status: 'article_operation_lock_release_failed',
            requestMayHaveSucceeded: remoteSaveCompleted,
            automaticRetryAllowed: false,
            errors: [lockError.message],
          };
          throw wrapped;
        }
      }
    }
  }
}

export function verifyArticleImageReadback({ expectedContent, actualContent, manifest }) {
  const validationErrors = [];
  try { validateArticleSlateContent(expectedContent); } catch (error) { validationErrors.push(`expected Slate content invalid: ${error.message}`); }
  try { validateArticleSlateContent(actualContent); } catch (error) { validationErrors.push(`actual Slate content invalid: ${error.message}`); }
  const expectedImages = expectedContent.filter((node) => node?.type === 'img');
  const actualImages = actualContent.filter((node) => node?.type === 'img');
  const result = {
    expectedImageCount: expectedImages.length,
    actualImageCount: actualImages.length,
    orderMatches: false,
    positionsMatch: false,
    urlsMatch: false,
    altMatches: false,
    captionMatches: false,
    missingAltCount: 0,
    missing_required_alt_in_backend_data: 0,
    errors: validationErrors,
  };
  if (expectedImages.length !== manifest.occurrences.length) result.errors.push('expected content image count differs from manifest');
  if (actualImages.length !== expectedImages.length) result.errors.push('actual image count differs from expected');
  result.urlsMatch = JSON.stringify(actualImages.map((node) => node.url)) === JSON.stringify(expectedImages.map((node) => node.url));
  result.orderMatches = result.urlsMatch;
  const expectedPositions = expectedContent.map((node, index) => node?.type === 'img' ? index : null).filter((value) => value !== null);
  const actualPositions = actualContent.map((node, index) => node?.type === 'img' ? index : null).filter((value) => value !== null);
  result.positionsMatch = JSON.stringify(expectedPositions) === JSON.stringify(actualPositions);
  result.altMatches = JSON.stringify(actualImages.map((node) => node.alt ?? '')) === JSON.stringify(expectedImages.map((node) => node.alt ?? ''));
  result.captionMatches = JSON.stringify(actualImages.map((node) => slateText(node.caption))) === JSON.stringify(expectedImages.map((node) => slateText(node.caption)));
  result.missingAltCount = actualImages.filter((node, index) => manifest.occurrences[index]?.role !== 'decorative' && !String(node.alt || '').trim()).length;
  result.missing_required_alt_in_backend_data = result.missingAltCount;
  if (!result.urlsMatch) result.errors.push('image URL order mismatch');
  if (!result.positionsMatch) result.errors.push('image node position mismatch');
  if (!result.altMatches) result.errors.push('image alt readback mismatch');
  if (!result.captionMatches) result.errors.push('image caption readback mismatch');
  if (result.missingAltCount) result.errors.push('required image alt missing after readback');
  return { ...result, ok: result.errors.length === 0 };
}

export async function writeArticleImageBindingManifest({
  manifestPath,
  manifest,
  lockPath = `${manifestPath}.lock`,
  _internal = {},
}) {
  if (!manifestPath) throw new Error('manifestPath is required');
  await mkdir(dirname(manifestPath), { recursive: true });
  let lock;
  try {
    lock = _internal.openLock ? await _internal.openLock(lockPath) : await open(lockPath, 'wx');
    if (lock?.writeFile) {
      await lock.writeFile(`${JSON.stringify({ pid: globalThis.process?.pid ?? null, acquiredAt: isoNow(), manifestPath })}\n`, 'utf8');
    }
  } catch (error) {
    if (error.code === 'EEXIST') throw new Error(`Article image manifest is locked: ${lockPath}`);
    throw error;
  }
  const tempPath = `${manifestPath}.${randomUUID()}.tmp`;
  try {
    const value = `${JSON.stringify(manifest, null, 2)}\n`;
    if (_internal.writeTemp) await _internal.writeTemp(tempPath, value);
    else await writeFile(tempPath, value, 'utf8');
    if (_internal.renameTemp) await _internal.renameTemp(tempPath, manifestPath);
    else await rename(tempPath, manifestPath);
    return { status: 'manifest_written_atomically', manifestPath, lockReleased: true };
  } finally {
    try { if (lock?.close) await lock.close(); } catch { /* best effort */ }
    try { await unlink(lockPath); } catch (error) { if (error.code !== 'ENOENT') throw error; }
    try { await unlink(tempPath); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
}

export const _internal = {
  ACTION_EXPORT_NAME,
  MANIFEST_SCHEMA_VERSION,
  PARSER_NAME,
  PARSER_VERSION,
  anchorText,
  compareReadback,
  discoverArticleActionContract,
  extractBalancedJson,
  normalizedDraftPayload,
  parseInlineImageAt,
  summarizeArticleNetwork,
  verifyArticleEditorPage,
};
