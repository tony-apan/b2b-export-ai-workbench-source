// Content scanning is defense in depth only. The primary publication boundary
// remains the explicit MANIFEST include allowlist plus human review.

const pathChecks = [
  ['local-path-macos-home', /\/Users\/[A-Za-z0-9._-]+\//],
  ['local-path-linux-home', /\/home\/[A-Za-z0-9._-]+\//],
  ['local-path-macos-volume', /\/Volumes\/[A-Za-z0-9._ -]+\//],
  ['local-path-macos-temp', /\/(?:private\/)?var\/folders\/[A-Za-z0-9._-]+\//],
  ['local-path-temp', /\/tmp\/[A-Za-z0-9._-]+\//],
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

export function scanPublishableContent(content) {
  const issues = [];
  for (const [code, pattern] of pathChecks) {
    const match = content.match(pattern);
    if (match) addIssue(issues, code, match[0]);
  }

  const credential = content.match(credentialPattern);
  const credentialValue = credential?.[1] ?? '';
  const credentialLooksLikeCodeExpression = /^[A-Za-z_$][A-Za-z0-9_$]*\.[A-Za-z_$][A-Za-z0-9_$]*$/.test(credentialValue);
  if (credential && !credentialLooksLikeCodeExpression) addIssue(issues, 'possible-credential-assignment', credential[0]);

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
    if (assigned && !assignedLooksLikeCodeExpression && !/^(?:example|sample|synthetic|placeholder|missing|redacted)[._-]?/i.test(assignedValue)) {
      addIssue(issues, 'possible-customer-identifier', `${match[0]}:${assignedValue}`);
    }
  }

  return issues;
}
