#!/usr/bin/env node
// Dev-suite runner: executes the exact test files declared in runtime-test-plan.json
// so npm test, installers and governance never drift from the single machine truth.
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const plan = JSON.parse(
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), '..', 'runtime-test-plan.json'), 'utf8'),
);
const files = [...(plan.devSuite?.files ?? [])];
if (!files.length) {
  console.error('BLOCK: runtime-test-plan.json devSuite.files is empty');
  process.exit(1);
}
const result = spawnSync(process.execPath, ['--test', ...files], { cwd: join(dirname(fileURLToPath(import.meta.url)), '..'), stdio: 'inherit' });
if (result.error) throw result.error;
process.exit(result.status ?? 1);
