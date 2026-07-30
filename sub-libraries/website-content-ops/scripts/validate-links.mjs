#!/usr/bin/env node
/**
 * Validate local Markdown links for the current release scope.
 *
 * External URLs are intentionally not fetched. This gate only proves that a
 * packaged/local Markdown link resolves inside the same scope, which catches
 * stale paths and mother/sub-library boundary leaks without network access.
 */
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { extname, join, relative, resolve } from 'node:path';

const args = process.argv.slice(2);
const rootArg = args.find((arg) => !arg.startsWith('--')) ?? '.';
const root = resolve(rootArg);
const releaseMode = args.includes('--release');
const failures = [];
const warnings = [];
const ignoredDirs = new Set(['.git', '.obsidian', 'node_modules', 'dist']);
const markdownExt = '.md';

if (!existsSync(root) || !statSync(root).isDirectory()) {
  console.error(`LINK_VALIDATION_FAILURES: root directory does not exist: ${root}`);
  process.exit(1);
}

function walk(dir) {
  const files = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (ignoredDirs.has(entry.name)) continue;
    const path = join(dir, entry.name);
    if (entry.isDirectory()) files.push(...walk(path));
    else if (entry.isFile() && extname(entry.name).toLowerCase() === markdownExt) files.push(path);
  }
  return files;
}

function withoutFencedCode(text) {
  return text.replace(/(^|\n)\s*(```|~~~)[\s\S]*?(?:\n\s*\2\s*(?=\n|$)|$)/gu, (block) => block.replace(/[^\n]/gu, ' '));
}

function isExternal(target) {
  return target.startsWith('#') || target.startsWith('//') || /^(?:https?:|mailto:|tel:|data:|obsidian:)/i.test(target);
}

function parseDestination(raw) {
  const value = raw.trim();
  if (value.startsWith('<') && value.includes('>')) return value.slice(1, value.indexOf('>'));
  return value.split(/\s+/u)[0];
}

function checkLink(source, rawTarget) {
  const target = parseDestination(rawTarget);
  if (!target || isExternal(target)) return;
  const withoutAnchor = decodeURIComponent(target.split('#', 1)[0]);
  const resolved = resolve(source, '..', withoutAnchor);
  const rel = relative(root, resolved);
  if (rel.startsWith('..') || rel === '..') {
    failures.push(`${relative(root, source)} links outside release scope: ${target}`);
    return;
  }
  if (!existsSync(resolved)) failures.push(`${relative(root, source)} links to missing path: ${target}`);
}

const linkPattern = /!?\[[^\]]*\]\((<[^>]+>|[^)]+)\)/gu;
let linkCount = 0;
for (const file of walk(root)) {
  const text = withoutFencedCode(readFileSync(file, 'utf8'));
  for (const match of text.matchAll(linkPattern)) {
    linkCount += 1;
    try {
      checkLink(file, match[1]);
    } catch (error) {
      failures.push(`${relative(root, file)} has an unreadable link target: ${match[1]} (${error.message})`);
    }
  }
}

if (!releaseMode && failures.length) warnings.push(...failures);
const issues = releaseMode ? failures : warnings;
if (issues.length) {
  console.error(`${releaseMode ? 'LINK_VALIDATION_FAILURES' : 'LINK_VALIDATION_WARNINGS'}: ${issues.length}`);
  for (const issue of issues) console.error(`${releaseMode ? 'BLOCK' : 'WARN'}: ${issue}`);
  if (releaseMode) process.exitCode = 1;
} else {
  console.log(`LINK_VALIDATION_PASS: markdown=${walk(root).length} links=${linkCount}`);
}
