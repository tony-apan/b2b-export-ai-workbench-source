import { readdirSync } from 'node:fs';
import { join } from 'node:path';
import { parseMarkdownFrontMatter, requireStringArrayField } from './front-matter.mjs';

export const AUTO_IGNORED_DIRS = new Set([
  '.git', '.obsidian', 'node_modules', 'dist', 'credentials', 'workspace',
]);

export const GENERATED_ARTIFACT_FILES = new Set(['MANIFEST.json', 'SHA256SUMS']);

export function parseManifestFrontMatter(manifestText, { source = 'MANIFEST.md' } = {}) {
  return parseMarkdownFrontMatter(manifestText, { source }).attributes;
}

export function manifestArray(manifestOrText, field, { source = 'MANIFEST.md', allowEmpty = false } = {}) {
  const manifest = typeof manifestOrText === 'string'
    ? parseManifestFrontMatter(manifestOrText, { source })
    : manifestOrText;
  return requireStringArrayField(manifest, field, { source, allowEmpty });
}

export function toPosix(value) {
  return value.split('\\').join('/');
}

export function matchesManifestPattern(value, pattern, { basename = false } = {}) {
  const candidatePath = toPosix(value);
  const rule = toPosix(pattern);
  const candidate = basename && !rule.includes('/') ? candidatePath.split('/').at(-1) : candidatePath;
  let source = '';
  for (let index = 0; index < rule.length; index += 1) {
    if (rule.startsWith('**', index)) { source += '.*'; index += 1; continue; }
    if (rule[index] === '*') { source += '[^/]*'; continue; }
    source += rule[index].replace(/[.+^${}()|[\]\\]/g, '\\$&');
  }
  return new RegExp(`^${source}$`).test(candidate);
}

export function isManifestExcluded(path, patterns) {
  return patterns.some((pattern) => matchesManifestPattern(path, pattern, { basename: !pattern.includes('/') }));
}

export function isManifestIncluded(path, patterns) {
  // Include rules are always package-root relative. A basename glob such as
  // *.md must never authorize nested files such as clients/acme.md.
  return patterns.some((pattern) => matchesManifestPattern(path, pattern));
}

export function mayContainManifestInclude(path, patterns) {
  if (!path) return true;
  return patterns.some((pattern) => {
    const rule = toPosix(pattern);
    if (rule.endsWith('/**')) {
      const base = rule.slice(0, -3);
      return path === base || path.startsWith(`${base}/`);
    }
    return rule.startsWith(`${path}/`);
  });
}

export function collectManifestSourceFiles(source, prefix = '') {
  const result = [];
  for (const entry of readdirSync(source, { withFileTypes: true })) {
    const rel = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isSymbolicLink()) {
      result.push({ path: rel, kind: 'symlink' });
    } else if (entry.isDirectory()) {
      if (!AUTO_IGNORED_DIRS.has(entry.name)) result.push(...collectManifestSourceFiles(join(source, entry.name), rel));
    } else {
      result.push({ path: rel, kind: 'file' });
    }
  }
  return result;
}

export function findUncoveredManifestFiles(root, includePatterns, excludePatterns, { allowGenerated = false } = {}) {
  const uncovered = [];
  for (const entry of collectManifestSourceFiles(root)) {
    if (entry.kind === 'symlink') {
      uncovered.push(entry.path);
      continue;
    }
    if (allowGenerated && GENERATED_ARTIFACT_FILES.has(entry.path)) continue;
    if (isManifestExcluded(entry.path, excludePatterns) || isManifestIncluded(entry.path, includePatterns)) continue;
    uncovered.push(entry.path);
  }
  return uncovered;
}
