#!/usr/bin/env node
import { readFileSync } from 'node:fs';

function fail(message) {
  console.error(`BLOCK: ${message}`);
  process.exit(1);
}

function parseArgs(argv) {
  const values = {};
  for (let index = 0; index < argv.length; index += 2) {
    const flag = argv[index];
    const value = argv[index + 1];
    if (!flag?.startsWith('--') || value === undefined) fail('Node test summary arguments must use --name value pairs');
    values[flag.slice(2)] = value;
  }
  return values;
}

const args = parseArgs(process.argv.slice(2));
const expected = Number(args['expected-tests']);
if (!Number.isInteger(expected) || expected < 1) fail('expected-tests must be a positive integer');
if (!args.log) fail('log is required');

let content;
try {
  content = readFileSync(args.log, 'utf8');
} catch {
  fail(`cannot read trusted Node test log: ${args.log}`);
}
const lines = content.split(/\r?\n/).map((line) => line.trim());
let planIndex = -1;
let planned = null;
for (let index = 0; index < lines.length; index += 1) {
  const match = lines[index].match(/^1\.\.(\d+)$/);
  if (match) {
    planIndex = index;
    planned = Number(match[1]);
  }
}
if (planIndex < 0 || planned !== expected) fail(`trusted Node test plan expected ${expected} tests but found ${planned ?? 'none'}`);

const summary = new Map();
for (const line of lines.slice(planIndex + 1)) {
  const match = line.match(/^# (tests|pass|fail|cancelled|skipped|todo) (\d+)$/);
  if (match) summary.set(match[1], Number(match[2]));
}
const required = {
  tests: expected,
  pass: expected,
  fail: 0,
  cancelled: 0,
  skipped: 0,
  todo: 0,
};
for (const [key, value] of Object.entries(required)) {
  if (summary.get(key) !== value) fail(`trusted Node test summary expected ${key}=${value} but found ${summary.get(key) ?? 'missing'}`);
}
console.log(`NODE_TEST_SUMMARY_PASS: tests=${expected} pass=${expected} fail=0 skipped=0`);
