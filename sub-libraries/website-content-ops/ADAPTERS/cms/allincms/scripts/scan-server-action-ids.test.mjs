import test from 'node:test';
import assert from 'node:assert/strict';
import { tmpdir } from 'node:os';
import { execFileSync } from 'node:child_process';
import { writeFileSync, rmSync } from 'node:fs';

test('scan-server-action-ids captures 5th-arg references verbatim', () => {
  const fixture = join(tmpdir(), 'scan-fixture-test.txt');
  writeFileSync(fixture, 'let A=(0,o.createServerReference)("7f6253b19d9facfe55ee722dee48a3e834b665b6a6",o.callServer,void 0,o.findSourceMapURL,"createCategoryAction");let B=(0,o.createServerReference)("7fe79a7564f05c77c813a34b52949a44f98704ef8d",o.callServer,void 0,o.findSourceMapURL,"createTagAction");');
  const out = execFileSync(process.execPath, ['scripts/scan-server-action-ids.mjs', fixture], { encoding: 'utf8' });
  const map = JSON.parse(out);
  assert.equal(map.createCategoryAction, '7f6253b19d9facfe55ee722dee48a3e834b665b6a6');
  assert.equal(map.createTagAction, '7fe79a7564f05c77c813a34b52949a44f98704ef8d');
  rmSync(fixture, { force: true });
});
