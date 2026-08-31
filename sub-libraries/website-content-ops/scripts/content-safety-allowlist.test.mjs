import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

// content-safety.allowlist.tsv 治理锁：digest 钉死——任何增删行都必须同步改此处的期望 digest（双审后），
// 防止未审计的豁免行静默进入发布安全出口。
const ALLOWLIST = join(dirname(fileURLToPath(import.meta.url)), '..', 'content-safety.allowlist.tsv');
const EXPECTED_DIGEST_PREFIX = '451cca9d1e8cffb8';

test('content-safety allowlist digest is pinned and audited', () => {
  assert.ok(existsSync(ALLOWLIST), 'allowlist 文件必须存在且 tracked');
  const raw = readFileSync(ALLOWLIST, 'utf8');
  const digest = createHash('sha256').update(raw).digest('hex').slice(0, 16);
  assert.equal(digest, EXPECTED_DIGEST_PREFIX, 'allowlist 内容变化：须经 flash+TERRA 双审并更新本测试的期望 digest');
  for (const line of raw.split('\n')) {
    if (!line.trim() || line.startsWith('#')) continue;
    if (line.startsWith('code\t')) continue; // 表头
    const cols = line.split('\t');
    assert.ok(cols.length >= 3 && cols[2].trim().length >= 8, `豁免行必须含原因（≥8 字符）: ${line}`);
    assert.ok(['possible-phone-number','possible-non-example-email','possible-credential-assignment','possible-customer-identifier','local-path-temp','local-path-macos-home','local-path-linux-home','local-path-macos-volume','local-path-macos-temp','local-path-windows-drive','local-path-windows-unc','local-path-file-uri'].includes(cols[0]), `未知类别: ${cols[0]}`);
  }
});
