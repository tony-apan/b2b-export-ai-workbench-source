import { realpathSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, relative, sep } from 'node:path';

function canonicalPath(path) {
  return realpathSync(path);
}

function pathPartsInside(parent, child) {
  const rel = relative(parent, child);
  if (!rel || rel === '..' || rel.startsWith(`..${sep}`) || rel.startsWith(sep)) return null;
  return rel.split(sep);
}

export function classifyGovernanceFixtureRoot(libraryRoot, { tempRoot = tmpdir(), env = process.env } = {}) {
  let resolvedRoot;
  let resolvedTemp;
  try {
    resolvedRoot = canonicalPath(libraryRoot);
    resolvedTemp = canonicalPath(tempRoot);
  } catch {
    return null;
  }

  const parts = pathPartsInside(resolvedTemp, resolvedRoot);
  if (!parts) return null;

  if (parts[0].startsWith('wco-governance-')) return 'direct';

  // The mother governance fixture materializes the child either as the source
  // subtree (<tmp>/701-governance-*/repo/sub-libraries/website-content-ops) or
  // inside the packaged staging artifact (<tmp>/701-governance-*/repo/dist/
  // mother/latest/sub-libraries/website-content-ops). Both must select fast
  // mode; the embedded mother validator runs against the staging root and its
  // `root` no longer ends with `/repo`.
  const motherSuffix = ['sub-libraries', 'website-content-ops'];
  if (
    env.GOVERNANCE_TEST_FIXTURE === '1'
    && parts[0].startsWith('701-governance-')
    && parts.includes('repo')
    && parts.length >= motherSuffix.length + 1
    && motherSuffix.every((part, index) => parts[parts.length - motherSuffix.length + index] === part)
  ) {
    return 'mother';
  }

  return null;
}

export function shouldUseGovernanceFixtureFastMode({
  libraryRoot,
  tempRoot = tmpdir(),
  env = process.env,
  releaseMode = false,
  prepareMode = false,
}) {
  if (env.WCO_GOVERNANCE_FIXTURE_FAST !== '1' || releaseMode || prepareMode) return false;
  return classifyGovernanceFixtureRoot(libraryRoot, { tempRoot, env }) !== null;
}
