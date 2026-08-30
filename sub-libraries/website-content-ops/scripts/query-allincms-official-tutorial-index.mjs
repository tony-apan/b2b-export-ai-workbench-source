#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const indexPath = join(scriptDir, '..', 'REFERENCES', 'ALLINCMS-OFFICIAL-TUTORIAL-INDEX.json');
const index = JSON.parse(readFileSync(indexPath, 'utf8'));
const args = process.argv.slice(2);
const jsonMode = args.includes('--json');
const query = args.filter((value) => value !== '--json').join(' ').trim();

function normalize(value) {
  return String(value ?? '').toLowerCase().replace(/[\s\p{P}\p{S}]+/gu, '');
}
function bigrams(value) {
  const text = normalize(value);
  if (text.length < 2) return new Set(text ? [text] : []);
  return new Set(Array.from({ length: text.length - 1 }, (_, i) => text.slice(i, i + 2)));
}
function overlapScore(left, right) {
  const a = bigrams(left);
  const b = bigrams(right);
  if (!a.size || !b.size) return 0;
  let shared = 0;
  for (const token of a) if (b.has(token)) shared += 1;
  return shared / Math.max(a.size, b.size);
}
function weightedScore(groups) {
  const q = normalize(query);
  let total = 0;
  for (const [values, weight] of groups) {
    for (const value of values.flat().filter(Boolean)) {
      const candidate = normalize(value);
      if (candidate.includes(q) || q.includes(candidate)) total += weight * 3;
      total += overlapScore(query, value) * weight;
    }
  }
  return total;
}
function tutorialScore(entry) {
  return weightedScore([
    [entry.problem_intents, 12],
    [[entry.title, entry.h1], 9],
    [entry.keywords, 7],
    [[entry.topic], 5],
    [[entry.content_scope], 3],
  ]);
}
function gapScore(gap) {
  return weightedScore([
    [gap.problem_intents, 18],
    [gap.keywords, 12],
    [[gap.topic], 6],
  ]);
}
function containsMarker(value, marker) {
  return normalize(value).includes(normalize(marker));
}

if (!query) {
  const result = {
    index_id: index.index_id,
    last_verified_at: index.last_verified_at,
    docs_urls_indexed: index.discovery_summary.docs_urls_indexed,
    topics: [...new Set(index.entries.map((entry) => entry.topic))].sort(),
    lookup_protocol: index.lookup_protocol,
    contract_question_markers: index.contract_question_markers,
    not_found_in_current_public_docs_inventory: index.not_found_in_current_public_docs_inventory,
  };
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  process.exit(0);
}

const isContractQuestion = index.contract_question_markers.some((marker) => containsMarker(query, marker));
const directGapMatches = index.not_found_in_current_public_docs_inventory
  .filter((gap) => gap.trigger_markers.some((marker) => containsMarker(query, marker)))
  .filter((gap) => isContractQuestion ? gap.gap_type === 'api_contract' : gap.gap_type === 'tutorial_coverage');
if (isContractQuestion && directGapMatches.length === 0) {
  const generalApiGap = index.not_found_in_current_public_docs_inventory.find((gap) => gap.gap_id === 'ALLINCMS-GAP-001');
  if (generalApiGap) directGapMatches.push(generalApiGap);
}
const gapMatches = directGapMatches
  .map((gap) => ({ score: Number(gapScore(gap).toFixed(3)), gap }))
  .sort((a, b) => b.score - a.score || a.gap.gap_id.localeCompare(b.gap.gap_id))
  .slice(0, 3);
const hasTutorialCoverageGap = !isContractQuestion && gapMatches.length > 0;
const tutorialMatches = index.entries
  .map((entry) => ({ score: Number(tutorialScore(entry).toFixed(3)), entry }))
  .filter(({ score }) => score >= (isContractQuestion ? 10 : 0.001))
  .sort((a, b) => b.score - a.score || a.entry.tutorial_id.localeCompare(b.entry.tutorial_id))
  .slice(0, 5);

const result = {
  query,
  intent_classification: isContractQuestion ? 'api_or_internal_contract' : (hasTutorialCoverageGap ? 'official_tutorial_gap' : 'official_tutorial_discovery'),
  index_last_verified_at: index.last_verified_at,
  decision: isContractQuestion
    ? '当前公开教程索引没有证明该 API/字段合同；先查 canonical Adapter 和当前部署证据。'
    : (hasTutorialCoverageGap
      ? '当前公开教程索引没有发现该主题的独立教程；可阅读相关 UI 教程，但必须按 next_route 继续查本地合同。'
      : '打开命中的 official_url 实时核验；如后续涉及真实写入，再转 canonical Adapter。'),
  official_docs_gaps: gapMatches.map(({ score, gap }) => ({ score, ...gap })),
  related_ui_tutorials: tutorialMatches.map(({ score, entry }) => ({
    score,
    tutorial_id: entry.tutorial_id,
    topic: entry.topic,
    title: entry.title,
    official_url: entry.official_url,
    content_scope: entry.content_scope,
    canonical_adapter_routes: entry.canonical_adapter_routes,
  })),
};

if (jsonMode) {
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
} else {
  process.stdout.write(`Query: ${query}\nIntent: ${result.intent_classification}\nIndex verified: ${index.last_verified_at}\n\nDecision: ${result.decision}\n`);
  if (gapMatches.length) {
    process.stdout.write('\nOfficial-doc gap (checked before tutorial matches):\n');
    for (const { score, gap } of gapMatches) {
      process.stdout.write(`- [${score}] ${gap.topic}; route: ${gap.next_route}\n`);
    }
  }
  if (!tutorialMatches.length) process.stdout.write('\nNo related tutorial match. Re-open the docs root and sitemap, then check the canonical Adapter.\n');
  else {
    process.stdout.write(`\n${isContractQuestion ? 'Related UI tutorials only (not API evidence)' : (hasTutorialCoverageGap ? 'Related tutorials only (no dedicated tutorial was discovered)' : 'Official tutorial matches')}:\n`);
    for (const { score, entry } of tutorialMatches) {
      process.stdout.write(`\n[${score}] ${entry.title} (${entry.tutorial_id})\n${entry.official_url}\n${entry.content_scope}\n`);
      if (entry.canonical_adapter_routes.length) process.stdout.write(`Adapter: ${entry.canonical_adapter_routes.join(', ')}\n`);
    }
  }
  process.stdout.write('\nBoundary: official tutorials explain UI/product workflows; they do not prove a public API or the current deployment contract.\n');
}
