#!/usr/bin/env node
/**
 * Scan concatenated client-chunk text for AllinCMS Server Action references.
 * Usage: node scripts/scan-server-action-ids.mjs <path-to-chunks.txt>
 * Expected input: one or more raw JS chunk texts (concatenated, any order).
 * Emits JSON: {"name": "hexid"} for every 5th-argument-verified reference.
 * This is the canonical discovery helper (discovered 2026-08-27, dpl 83eddf…).
 * Reject any name-adjacent-only heuristics: the ONLY reliable pattern is
 *   createServerReference)("hex", … ,findSourceMapURL,"NAME")
 */
import { readFileSync } from 'node:fs';

const input = process.argv[2];
if (!input) {
  console.error('usage: node scripts/scan-server-action-ids.mjs <chunks-text-file>');
  process.exit(2);
}
const joined = readFileSync(input, 'utf8');
const pattern = /createServerReference\)\("([0-9a-f]{32,64})"[^"]{0,300}"([A-Za-z][A-Za-z0-9_]*)"\)/g;
const map = {};
let match;
while ((match = pattern.exec(joined)) !== null) {
  if (!map[match[2]]) map[match[2]] = match[1];
}
console.log(JSON.stringify(map, null, 1));
