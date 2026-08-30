export const TRUSTED_EVIDENCE_SCHEMA = 'release-evidence/v2';
export const TRUSTED_RESULT_SCHEMA = 'release-check-result/v2';
export const TRUSTED_EVIDENCE_SOURCE = 'trusted-workflow-generated/v1';
export const EVIDENCE_DIGEST_ALGORITHM = 'sha256-canonical-json-v1';
export const MOTHER_RUNTIME_REASON = 'mother-library-machine-contract-declares-none';
export const SUB_LIBRARY_RUNTIME_REASON = 'trusted-sub-library-runtime-profile';
export const EXPECTED_RUNTIME_TEST_PLAN = [
  'upload-media-browser.test.mjs',
  'article-image-binding.test.mjs',
  'article-content-formats.test.mjs',
  'article-operations.test.mjs',
];
export const EXPECTED_RUNTIME_TESTS = 156;

const motherChecks = [
  ['governance-tests', 'node scripts/run-governance-tests.mjs --timeout-ms 60000'],
  ['index-validation', 'node scripts/validate-indexes.mjs --strict'],
  ['link-validation', 'node scripts/validate-links.mjs --release'],
  ['document-id-validation', 'node scripts/validate-document-ids.mjs'],
  ['log-validation', 'node scripts/validate-logs.mjs --release'],
  ['knowledge-chain-validation', 'node scripts/validate-knowledge-chain.mjs --release'],
  ['mother-structure-validation', 'node scripts/validate-mother-library.mjs --release'],
  ['runtime-applicability', 'node scripts/generate-release-evidence.mjs --internal-check mother-runtime-applicability'],
  ['artifact-validation', 'node $CANDIDATE_ROOT/scripts/validate-artifact.mjs --prepare $CANDIDATE_ROOT'],
  ['commit-provenance', 'node scripts/generate-release-evidence.mjs --internal-check commit-provenance'],
  ['tag-signature', 'git verify-tag --raw $TAG_NAME'],
];

const subChecks = [
  ['governance-tests', 'node scripts/run-governance-tests.mjs --timeout-ms 60000'],
  ['index-validation', 'node scripts/validate-indexes.mjs --strict'],
  ['link-validation', 'node scripts/validate-links.mjs --release'],
  ['document-id-validation', 'node scripts/validate-document-ids.mjs --scope sub-library:$PACKAGE_ID'],
  ['sub-library-structure-validation', 'node $PACKAGE_PATH/scripts/validate-sub-library.mjs --release'],
  ['runtime-tests', 'node --test --test-reporter=tap upload-media-browser.test.mjs article-image-binding.test.mjs article-content-formats.test.mjs article-operations.test.mjs'],
  ['artifact-validation', 'node $CANDIDATE_ROOT/scripts/validate-artifact.mjs --prepare $CANDIDATE_ROOT'],
  ['commit-provenance', 'node scripts/generate-release-evidence.mjs --internal-check commit-provenance'],
  ['tag-signature', 'git verify-tag --raw $TAG_NAME'],
];

export function trustedProfile(scope) {
  if (scope === 'mother-library') return 'mother-release-v2';
  if (scope === 'sub-library') return 'sub-library-release-v2';
  return '';
}

export function trustedCheckContract(scope) {
  return new Map(scope === 'mother-library' ? motherChecks : scope === 'sub-library' ? subChecks : []);
}

export function trustedCheckIds(scope) {
  return [...trustedCheckContract(scope).keys()];
}
