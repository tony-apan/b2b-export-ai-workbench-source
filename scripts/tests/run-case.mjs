#!/usr/bin/env node
import { governanceCases } from './governance-cases.mjs';

const [id, root, timeoutText] = process.argv.slice(2);
const test = governanceCases.get(id);
if (!test) {
  console.error(`UNKNOWN_TEST_CASE: ${id ?? 'missing'}`);
  process.exit(2);
}
if (!root) {
  console.error('MISSING_FIXTURE_ROOT');
  process.exit(2);
}
const timeoutMs = Number(timeoutText);
if (!Number.isInteger(timeoutMs) || timeoutMs < 1000) {
  console.error(`INVALID_COMMAND_TIMEOUT: ${timeoutText}`);
  process.exit(2);
}

try {
  test.run({ root, timeoutMs });
  const result = {
    id,
    status: test.expected === 'known-gap' ? 'KNOWN_GAP' : 'PASS',
    title: test.title,
    gap: test.gap ?? null,
  };
  console.log(`CASE_RESULT:${JSON.stringify(result)}`);
} catch (error) {
  console.error(`CASE_FAILURE: ${id}`);
  console.error(error?.stack ?? String(error));
  process.exit(1);
}
