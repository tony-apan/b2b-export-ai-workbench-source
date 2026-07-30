#!/usr/bin/env node
/**
 * Validate local Markdown links for the current release scope.
 *
 * External URLs are intentionally not fetched. This gate proves that inline,
 * full/collapsed/shortcut reference-style, and image Markdown links resolve
 * inside the same scope. Reference definitions are validated even if unused so
 * a dormant broken target cannot bypass release review.
 */
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { extname, join, relative, resolve } from 'node:path';
import { extractMarkdownLinks } from './lib/markdown-links.mjs';

const args = process.argv.slice(2);
const rootArg = args.find((arg) => !arg.startsWith('--')) ?? '.';
const root = resolve(rootArg);
const releaseMode = args.includes('--release') || args.includes('--strict');
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

function isExternal(target) {
  return target.startsWith('#') || target.startsWith('//') || /^(?:https?:|mailto:|tel:|data:|obsidian:)/i.test(target);
}

function checkLink(source, target) {
  if (!target || isExternal(target)) return;
  const rawPath = target.split('#', 1)[0].split('?', 1)[0];
  if (!rawPath) return;
  let withoutAnchor;
  try { withoutAnchor = decodeURIComponent(rawPath); }
  catch (error) {
    failures.push(`${relative(root, source)} has an unreadable link target: ${target} (${error.message})`);
    return;
  }
  const resolved = resolve(source, '..', withoutAnchor);
  const rel = relative(root, resolved);
  if (rel.startsWith('..') || rel === '..') {
    failures.push(`${relative(root, source)} links outside release scope: ${target}`);
    return;
  }
  if (!existsSync(resolved)) failures.push(`${relative(root, source)} links to missing path: ${target}`);
}

const markdownFiles = walk(root);
let linkCount = 0;
for (const file of markdownFiles) {
  const parsed = extractMarkdownLinks(readFileSync(file, 'utf8'));
  for (const error of parsed.errors) failures.push(`${relative(root, file)} has invalid Markdown link syntax: ${error.message}${error.line ? ` (line ${error.line})` : ''}`);
  for (const link of parsed.links) {
    linkCount += 1;
    checkLink(file, link.target);
  }
}

if (!releaseMode && failures.length) warnings.push(...failures);
const issues = releaseMode ? failures : warnings;
if (issues.length) {
  console.error(`${releaseMode ? 'LINK_VALIDATION_FAILURES' : 'LINK_VALIDATION_WARNINGS'}: ${issues.length}`);
  for (const issue of issues) console.error(`${releaseMode ? 'BLOCK' : 'WARN'}: ${issue}`);
  if (releaseMode) process.exitCode = 1;
} else {
  console.log(`LINK_VALIDATION_PASS: markdown=${markdownFiles.length} links=${linkCount}`);
}
