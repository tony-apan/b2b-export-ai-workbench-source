#!/usr/bin/env node
const SHA_PATTERN = /^[a-f0-9]{40}(?:[a-f0-9]{24})?$/;

function fail(message) {
  console.error(`BLOCK: ${message}`);
  process.exit(1);
}

function parseArgs(argv) {
  const values = {};
  for (let index = 0; index < argv.length; index += 2) {
    const flag = argv[index];
    const value = argv[index + 1];
    if (!flag?.startsWith('--') || value === undefined) fail('candidate identity arguments must use --name value pairs');
    values[flag.slice(2)] = value;
  }
  return values;
}

const args = parseArgs(process.argv.slice(2));
const fields = ['expected-commit', 'expected-tag-object', 'actual-commit', 'actual-tag-object'];
for (const field of fields) {
  if (!SHA_PATTERN.test(args[field] ?? '')) fail(`${field} must be a 40- or 64-character lowercase hexadecimal object id`);
}
if (args['actual-tag-object'] !== args['expected-tag-object'] || args['actual-commit'] !== args['expected-commit']) {
  fail('qualification candidate does not match the exact tag object and commit tested in the isolated job');
}
console.log(`TESTED_CANDIDATE_IDENTITY_PASS: commit=${args['actual-commit']} tag_object=${args['actual-tag-object']}`);
