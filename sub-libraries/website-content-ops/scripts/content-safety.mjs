// Content scanning is defense in depth only. The primary publication boundary
// remains the explicit MANIFEST include allowlist plus human review.
// Reviewed allowlist: content-safety.allowlist.tsv（code<TAB>相对路径<TAB>原因，人工双审后登记）
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ALLOWED = new Set();
try {
  const tsvPath = join(dirname(fileURLToPath(import.meta.url)), '..', 'content-safety.allowlist.tsv');
  for (const line of readFileSync(tsvPath, 'utf8').split('\n')) {
    if (!line.trim() || line.startsWith('#') || line.startsWith('code\t')) continue;
    const [code, rel, ...rest] = line.split('\t');
    if (code && rel) ALLOWED.add(`${code}|${rel.trim()}`);
  }
} catch { /* 无清单 = 最严格模式 */ }

const pathChecks = [
  ['local-path-macos-home', /\/Users\/[A-Za-z0-9._-]+\//],
  ['local-path-linux-home', /\/home\/[A-Za-z0-9._-]+\//],
  ['local-path-macos-volume', /\/Volumes\/[A-Za-z0-9._ -]+\//],
  ['local-path-macos-temp', /\/(?:private\/)?var\/folders\/[A-Za-z0-9._-]+\//],
  ['local-path-temp', /\/tmp\/(?=[A-Za-z0-9_-]*[A-Za-z0-9])[A-Za-z0-9._-]+\//], // 至少含一个字母数字，'...' 占位不命中
  ['local-path-windows-drive', /(?:^|[\s"'`(])(?:[A-Za-z]:[\\/](?:[^\s"'`<>|]+[\\/])+[^\s"'`<>|]*)/m],
  ['local-path-windows-unc', /(?:^|[\s"'`(])(?:\\\\[A-Za-z0-9._-]+\\[A-Za-z0-9$._ -]+(?:\\[^\s"'`<>|]+)*)/m],
  ['local-path-file-uri', /\bfile:\/\/(?:\/[A-Za-z0-9._~-]+|[A-Za-z]:[\\/])/i],
];

const credentialPattern = /(?:api[_ -]?key|access[_ -]?token|secret|password|cookie|authorization|session)\s*[:=]\s*["']?([A-Za-z0-9_./+=-]{12,})/i;
const emailPattern = /\b[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})\b/gi;
const plusPhonePattern = /(?:^|[^A-Za-z0-9])\+\d[\d ()-]{7,}\d(?:$|[^A-Za-z0-9])/gm;
const labeledPhonePattern = /(?:phone|mobile|telephone|tel|电话|手机)\s*[:=：]\s*["']?\+?\d[\d ()-]{7,}\d/i;
const customerIdentifierPattern = /(?:customer|client|account)[_\s-]?(?:id|identifier)|客户(?:编号|标识|ID)/gi;
const assignedIdentifierPattern = /\s*[:=：]\s*["']?([A-Za-z0-9][A-Za-z0-9._-]{5,})/y;

function isReservedExampleDomain(domain) {
  const lower = domain.toLowerCase();
  return lower === 'example.com' || lower === 'example.org' || lower === 'example.net'
    || lower.endsWith('.example') || lower.endsWith('.invalid');
}

function addIssue(issues, code, match) {
  if (!issues.some((issue) => issue.code === code)) issues.push({ code, match: match.slice(0, 160) });
}

export function scanPublishableContent(content, relPath = '') {
  const issues = [];
  for (const [code, pattern] of pathChecks) {
    const match = content.match(pattern);
    if (match) addIssue(issues, code, match[0]);
  }

  const credential = content.match(credentialPattern);
  const credentialValue = (credential?.[1] ?? '').replace(/[=._-]+$/, ''); // 剥尾部 =/-/.（捕获类含之；base64 垫符不影响 safe-form 判定）
  const credentialSafe = [
    /^[A-Za-z_$][A-Za-z0-9_$]*\.[A-Za-z_$][A-Za-z0-9_$]*$/, // foo.bar 代码表达式
    /^\$[A-Za-z_][A-Za-z0-9_]*$/,                             // $TOKEN shell 变量
    /^[a-z]+(?:-[a-z]+)+$/,                                    // 连字符散文词组（无数字）。已知限制：低熵纯小写连字符口令（password: hunter-twosecret）会放行——本层是 defense-in-depth，首边界仍是 MANIFEST include+人审（TERRA 2026-08-31）
    /^(?:[a-z][a-z-]*-)?(?:key|token|cookie|secret|password|authorization)$/i, // 全值锚定且仅小写连字符词：payload-token 等 header 名误当值；含数字/大写随机串不豁免
  ].some((re) => re.test(credentialValue));
  if (credential && !credentialSafe) addIssue(issues, 'possible-credential-assignment', credential[0]);

  for (const match of content.matchAll(emailPattern)) {
    if (!isReservedExampleDomain(match[1])) addIssue(issues, 'possible-non-example-email', match[0]);
  }

  const plusPhone = content.match(plusPhonePattern);
  if (plusPhone) addIssue(issues, 'possible-phone-number', plusPhone[0].trim());
  const labeledPhone = content.match(labeledPhonePattern);
  if (labeledPhone) addIssue(issues, 'possible-phone-number', labeledPhone[0]);

  for (const match of content.matchAll(customerIdentifierPattern)) {
    assignedIdentifierPattern.lastIndex = match.index + match[0].length;
    const assigned = assignedIdentifierPattern.exec(content);
    const assignedValue = assigned?.[1] ?? '';
    const assignedLooksLikeCodeExpression = /^[A-Za-z_$][A-Za-z0-9_$]*\.[A-Za-z_$][A-Za-z0-9_$]*$/.test(assignedValue);
    if (assigned && !assignedLooksLikeCodeExpression && !/^(?:example|sample|synthetic|placeholder|missing|redacted)[._-]?/i.test(assignedValue) && !/[._-]synthetic$/i.test(assignedValue)) {
      addIssue(issues, 'possible-customer-identifier', `${match[0]}:${assignedValue}`);
    }
  }

  return issues.filter((issue) => !ALLOWED.has(`${issue.code}|${relPath}`));
}
