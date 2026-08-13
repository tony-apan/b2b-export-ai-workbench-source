#!/usr/bin/env node
import { createHash, randomBytes } from 'node:crypto';
import {
  chmodSync,
  copyFileSync,
  existsSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  realpathSync,
  renameSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { basename, dirname, extname, isAbsolute, join, relative, resolve, sep } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const SCRIPT_PATH = fileURLToPath(import.meta.url);
const SCRIPT_DIR = dirname(SCRIPT_PATH);
const CANONICAL_SCOPE = realpathSync(resolve(SCRIPT_DIR, '..'));
const REPOSITORY_ROOT = realpathSync(resolve(SCRIPT_DIR, '../../..'));
const CANONICAL_SCOPE_RELATIVE = toRepoRelative(CANONICAL_SCOPE);
const SUPPORTED_CODE_EXTENSIONS = new Set(['.mjs', '.js']);
const UNSCANNED_EXECUTABLE_RESOURCE_EXTENSIONS = new Set(['.cjs', '.jsx', '.ts', '.tsx', '.mts', '.cts', '.wasm', '.node']);
const KNOWN_UNSUPPORTED_LOCAL_EXTENSIONS = new Set(['.cjs', '.json', '.jsx', '.ts', '.tsx', '.mts', '.cts', '.wasm', '.node']);
const FORBIDDEN_RUNTIME_LOADER_IDENTIFIERS = new Map([
  ['eval', 'eval runtime loader'],
  ['Function', 'Function runtime loader'],
  ['createRequire', 'createRequire runtime loader'],
  ['getBuiltinModule', 'process.getBuiltinModule runtime loader'],
  ['Worker', 'Worker URL dependency'],
  ['SharedWorker', 'SharedWorker URL dependency'],
  ['ServiceWorker', 'ServiceWorker URL dependency'],
  ['serviceWorker', 'ServiceWorker URL dependency'],
]);
const STRING_RUNTIME_LOADER_IDENTIFIERS = new Set(['setTimeout', 'setInterval']);
const SENSITIVE_COMPUTED_RUNTIME_RECEIVERS = new Set(['global', 'globalThis', 'module', 'process', 'require', 'self', 'window']);
const FORBIDDEN_COMPUTED_RUNTIME_PROPERTIES = new Map([
  ...FORBIDDEN_RUNTIME_LOADER_IDENTIFIERS,
  ['require', 'require runtime loader'],
]);

function fail(message) {
  throw new Error(message);
}

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function isWithin(parent, child) {
  const rel = relative(parent, child);
  return rel === '' || (!rel.startsWith(`..${sep}`) && rel !== '..' && !isAbsolute(rel));
}

function toPosix(value) {
  return value.split(sep).join('/');
}

function toRepoRelative(absolutePath) {
  if (!isWithin(REPOSITORY_ROOT, absolutePath)) fail(`path escapes repository root: ${absolutePath}`);
  const rel = toPosix(relative(REPOSITORY_ROOT, absolutePath));
  if (!rel || rel === '.') fail(`repository root cannot be frozen as a file: ${absolutePath}`);
  return rel;
}

function assertAbsolutePath(value, option) {
  if (!value || !isAbsolute(value)) fail(`${option} must be an explicit absolute path`);
  return resolve(value);
}

function assertControlFile(path, option) {
  const absolute = assertAbsolutePath(path, option);
  if (!existsSync(absolute)) fail(`${option} does not exist: ${absolute}`);
  const stat = lstatSync(absolute);
  if (stat.isSymbolicLink()) fail(`${option} must not be a symlink: ${absolute}`);
  if (!stat.isFile()) fail(`${option} must be a regular file: ${absolute}`);
  return realpathSync(absolute);
}

function parseRepoRelativePath(raw, origin) {
  const value = raw.trim();
  if (!value || value.startsWith('#')) return null;
  if (isAbsolute(value) || /^[A-Za-z]:[\\/]/u.test(value) || value.includes('\\')) {
    fail(`${origin} must contain repository-relative POSIX paths: ${value}`);
  }
  const parts = value.split('/');
  if (parts.some((part) => part === '' || part === '.' || part === '..')) {
    fail(`${origin} contains a non-canonical repository-relative path: ${value}`);
  }
  const absolute = resolve(REPOSITORY_ROOT, ...parts);
  if (!isWithin(REPOSITORY_ROOT, absolute)) fail(`${origin} escapes repository root: ${value}`);
  const canonical = toRepoRelative(absolute);
  if (canonical !== value) fail(`${origin} path is not canonical: ${value}; expected ${canonical}`);
  return value;
}

function readPathList(path, option) {
  const absolute = assertControlFile(path, option);
  const seen = new Set();
  const values = [];
  for (const [index, raw] of readFileSync(absolute, 'utf8').split(/\r?\n/u).entries()) {
    const value = parseRepoRelativePath(raw, `${option}:${index + 1}`);
    if (!value || seen.has(value)) continue;
    seen.add(value);
    values.push(value);
  }
  return values;
}

function assertNoSymlinkBelowRepo(absolutePath, repoRelativePath) {
  let cursor = REPOSITORY_ROOT;
  for (const part of repoRelativePath.split('/')) {
    cursor = join(cursor, part);
    let stat;
    try {
      stat = lstatSync(cursor);
    } catch (error) {
      if (error?.code === 'ENOENT') fail(`missing path: ${repoRelativePath}`);
      throw error;
    }
    if (stat.isSymbolicLink()) fail(`symlink is not allowed: ${toRepoRelative(cursor)}`);
  }
  if (resolve(cursor) !== resolve(absolutePath)) fail(`path normalization mismatch: ${repoRelativePath}`);
}

function assertNoDistPath(repoRelativePath, role) {
  if (repoRelativePath.split('/').includes('dist')) {
    fail(`${role} contains forbidden dist path: ${repoRelativePath}`);
  }
}

function assertRepoRegularFile(repoRelativePath, role) {
  assertNoDistPath(repoRelativePath, role);
  const absolute = resolve(REPOSITORY_ROOT, ...repoRelativePath.split('/'));
  if (!isWithin(REPOSITORY_ROOT, absolute)) fail(`${role} escapes repository root: ${repoRelativePath}`);
  assertNoSymlinkBelowRepo(absolute, repoRelativePath);
  const stat = lstatSync(absolute);
  if (stat.isSymbolicLink()) fail(`${role} must not be a symlink: ${repoRelativePath}`);
  if (!stat.isFile()) fail(`${role} must be a regular file: ${repoRelativePath}`);
  return absolute;
}

function parseArgs(argv) {
  const singleton = new Set(['--freeze-id', '--generated-at', '--manifest', '--freeze-root', '--file-list', '--sha-file', '--roots-file', '--resources-file']);
  const values = new Map();
  const directResources = [];
  for (let index = 0; index < argv.length; index += 1) {
    const option = argv[index];
    if (option === '--resource-file') {
      const value = argv[index + 1];
      if (!value || value.startsWith('--')) fail(`${option} requires a repository-relative path`);
      directResources.push(value);
      index += 1;
      continue;
    }
    if (!singleton.has(option)) fail(`unknown option: ${option}`);
    if (values.has(option)) fail(`duplicate option: ${option}`);
    const value = argv[index + 1];
    if (!value || value.startsWith('--')) fail(`${option} requires a value`);
    values.set(option, value);
    index += 1;
  }
  for (const required of ['--freeze-id', '--generated-at', '--manifest', '--freeze-root', '--file-list', '--roots-file']) {
    if (!values.has(required)) fail(`missing required option: ${required}`);
  }
  const freezeId = values.get('--freeze-id');
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/u.test(freezeId)) fail(`invalid --freeze-id: ${freezeId}`);
  const generatedAt = values.get('--generated-at');
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/u.test(generatedAt)
    || new Date(generatedAt).toISOString() !== generatedAt) {
    fail('--generated-at must be a controller-supplied canonical UTC timestamp such as 2026-08-02T00:00:00.000Z');
  }
  return {
    freezeId,
    generatedAt,
    manifestPath: assertAbsolutePath(values.get('--manifest'), '--manifest'),
    freezeRoot: assertAbsolutePath(values.get('--freeze-root'), '--freeze-root'),
    fileListPath: assertAbsolutePath(values.get('--file-list'), '--file-list'),
    shaFilePath: values.has('--sha-file') ? assertAbsolutePath(values.get('--sha-file'), '--sha-file') : null,
    rootsFile: assertControlFile(values.get('--roots-file'), '--roots-file'),
    resourcesFile: values.has('--resources-file') ? assertControlFile(values.get('--resources-file'), '--resources-file') : null,
    directResources,
  };
}

function canonicalOutputPath(path, option) {
  if (existsSync(path)) fail(`${option} already exists; refusing to overwrite: ${path}`);
  const parent = dirname(path);
  if (!existsSync(parent)) fail(`${option} parent directory does not exist: ${parent}`);
  const resolvedParent = realpathSync(parent);
  const parentStat = lstatSync(resolvedParent);
  if (!parentStat.isDirectory()) fail(`${option} parent is not a directory: ${parent}`);
  const output = join(resolvedParent, basename(path));
  if (isWithin(REPOSITORY_ROOT, output) || isWithin(output, REPOSITORY_ROOT)) {
    fail(`${option} must be outside and must not contain the repository root: ${path}`);
  }
  return output;
}

function validateOutputLayout(options) {
  options.manifestPath = canonicalOutputPath(options.manifestPath, '--manifest');
  options.freezeRoot = canonicalOutputPath(options.freezeRoot, '--freeze-root');
  options.fileListPath = canonicalOutputPath(options.fileListPath, '--file-list');
  if (options.shaFilePath) options.shaFilePath = canonicalOutputPath(options.shaFilePath, '--sha-file');
  const entries = [
    ['--manifest', options.manifestPath],
    ['--freeze-root', options.freezeRoot],
    ['--file-list', options.fileListPath],
    ...(options.shaFilePath ? [['--sha-file', options.shaFilePath]] : []),
  ];
  for (let left = 0; left < entries.length; left += 1) {
    for (let right = left + 1; right < entries.length; right += 1) {
      const [leftOption, leftPath] = entries[left];
      const [rightOption, rightPath] = entries[right];
      if (leftPath === rightPath || isWithin(leftPath, rightPath) || isWithin(rightPath, leftPath)) {
        fail(`${leftOption} and ${rightOption} must not overlap`);
      }
    }
  }
}

function isLocalSpecifier(specifier) {
  return specifier.startsWith('./')
    || specifier.startsWith('../')
    || specifier.startsWith('/')
    || specifier.startsWith('file:')
    || /^[A-Za-z]:[\\/]/u.test(specifier)
    || specifier.startsWith('\\\\');
}

function skipTrivia(source, start) {
  let index = start;
  while (index < source.length) {
    if (/\s/u.test(source[index])) {
      index += 1;
      continue;
    }
    if (source.startsWith('//', index)) {
      index = source.indexOf('\n', index + 2);
      if (index === -1) return source.length;
      continue;
    }
    if (source.startsWith('/*', index)) {
      const end = source.indexOf('*/', index + 2);
      if (end === -1) fail('unterminated block comment while scanning dynamic imports');
      index = end + 2;
      continue;
    }
    break;
  }
  return index;
}

function readQuotedToken(source, start) {
  const quote = source[start];
  let index = start + 1;
  while (index < source.length) {
    if (source[index] === '\\') {
      index += 2;
      continue;
    }
    if (source[index] === quote) {
      const end = index + 1;
      let value;
      try {
        value = vm.runInNewContext(source.slice(start, end), Object.create(null), { timeout: 50 });
      } catch (error) {
        fail(`invalid string literal in dynamic import: ${error.message}`);
      }
      if (typeof value !== 'string') fail('dynamic import literal did not parse as a string');
      return { end, value };
    }
    if (source[index] === '\n' || source[index] === '\r') fail('unterminated string literal while scanning dynamic imports');
    index += 1;
  }
  fail('unterminated string literal while scanning dynamic imports');
}

function skipRegexLiteral(source, start) {
  let index = start + 1;
  let inClass = false;
  while (index < source.length) {
    const char = source[index];
    if (char === '\\') {
      index += 2;
      continue;
    }
    if (char === '[') inClass = true;
    else if (char === ']') inClass = false;
    else if (char === '/' && !inClass) {
      index += 1;
      while (/[A-Za-z]/u.test(source[index] ?? '')) index += 1;
      return index;
    } else if (char === '\n' || char === '\r') {
      return start + 1;
    }
    index += 1;
  }
  return source.length;
}

const REGEX_PREFIX_KEYWORDS = new Set([
  'await', 'case', 'delete', 'do', 'else', 'in', 'instanceof', 'new', 'of', 'return', 'throw', 'typeof', 'void', 'yield',
]);

function readConstantComputedProperty(source, start) {
  let index = skipTrivia(source, start);
  let value = '';
  let literals = 0;
  while (index < source.length) {
    if (source[index] !== '"' && source[index] !== "'") return { constant: false };
    const literal = readQuotedToken(source, index);
    value += literal.value;
    literals += 1;
    index = skipTrivia(source, literal.end);
    if (source[index] === ']') return { constant: true, end: index + 1, literals, value };
    if (source[index] !== '+') return { constant: false };
    index = skipTrivia(source, index + 1);
  }
  return { constant: false };
}

function scanDynamicImports(source, fileLabel) {
  const found = [];

  function scanSegment(start, stopOnClosingBrace = false) {
    let index = start;
    let braceDepth = 0;
    let canEndExpression = false;
    let previousIdentifier = null;
    while (index < source.length) {
      const triviaEnd = skipTrivia(source, index);
      if (triviaEnd !== index) {
        index = triviaEnd;
        continue;
      }
      const char = source[index];
      if (stopOnClosingBrace && char === '}' && braceDepth === 0) return index + 1;
      if (char === '}' && braceDepth > 0) {
        braceDepth -= 1;
        canEndExpression = true;
        index += 1;
        continue;
      }
      if (char === '{') {
        braceDepth += 1;
        canEndExpression = false;
        previousIdentifier = null;
        index += 1;
        continue;
      }
      if (char === '[' && canEndExpression) {
        const property = readConstantComputedProperty(source, index + 1);
        if (property.constant) {
          const forbiddenReason = FORBIDDEN_COMPUTED_RUNTIME_PROPERTIES.get(property.value);
          if (forbiddenReason) {
            fail(`${forbiddenReason} is not allowed via computed property in ${fileLabel} at offset ${index}`);
          }
          if (property.value === 'resolve' && previousIdentifier === 'require') {
            fail(`require.resolve runtime loader via computed property is not allowed in ${fileLabel} at offset ${index}`);
          }
          if (property.value === 'getBuiltinModule' && previousIdentifier === 'process') {
            fail(`process.getBuiltinModule runtime loader via computed property is not allowed in ${fileLabel} at offset ${index}`);
          }
          if (STRING_RUNTIME_LOADER_IDENTIFIERS.has(property.value)) {
            const afterProperty = skipTrivia(source, property.end);
            if (source[afterProperty] === '(') {
              const argumentStart = skipTrivia(source, afterProperty + 1);
              if (source[argumentStart] === '"' || source[argumentStart] === "'" || source[argumentStart] === '`') {
                fail(`string runtime loader ${property.value} is not allowed in ${fileLabel} at offset ${index}`);
              }
            }
          }
          index = property.end;
          canEndExpression = true;
          previousIdentifier = property.value;
          continue;
        }
        if (SENSITIVE_COMPUTED_RUNTIME_RECEIVERS.has(previousIdentifier)) {
          fail(`computed runtime loader target cannot be statically proven safe in ${fileLabel} at offset ${index}`);
        }
      }
      if (char === '"' || char === "'") {
        const literal = readQuotedToken(source, index);
        const afterLiteral = skipTrivia(source, literal.end);
        if (source[afterLiteral] === ']') {
          const afterBracket = skipTrivia(source, afterLiteral + 1);
          if (FORBIDDEN_RUNTIME_LOADER_IDENTIFIERS.has(literal.value) && source[afterBracket] === '(') {
            fail(`${FORBIDDEN_RUNTIME_LOADER_IDENTIFIERS.get(literal.value)} is not allowed in ${fileLabel} at offset ${index}`);
          }
          if (STRING_RUNTIME_LOADER_IDENTIFIERS.has(literal.value) && source[afterBracket] === '(') {
            const argumentStart = skipTrivia(source, afterBracket + 1);
            if (source[argumentStart] === '"' || source[argumentStart] === "'" || source[argumentStart] === '`') {
              fail(`string runtime loader ${literal.value} is not allowed in ${fileLabel} at offset ${index}`);
            }
          }
        }
        index = literal.end;
        canEndExpression = true;
        previousIdentifier = null;
        continue;
      }
      if (char === '`') {
        index += 1;
        while (index < source.length) {
          if (source[index] === '\\') {
            index += 2;
            continue;
          }
          if (source[index] === '`') {
            index += 1;
            break;
          }
          if (source.startsWith('${', index)) {
            index = scanSegment(index + 2, true);
            continue;
          }
          index += 1;
        }
        canEndExpression = true;
        previousIdentifier = null;
        continue;
      }
      if (char === '/' && source[index + 1] !== '/' && source[index + 1] !== '*' && !canEndExpression) {
        index = skipRegexLiteral(source, index);
        canEndExpression = true;
        continue;
      }
      if (/[A-Za-z_$]/u.test(char)) {
        const startToken = index;
        index += 1;
        while (/[A-Za-z0-9_$]/u.test(source[index] ?? '')) index += 1;
        const token = source.slice(startToken, index);
        const receiverIdentifier = previousIdentifier;
        const afterToken = skipTrivia(source, index);
        if (token === 'require' && (source[afterToken] === '(' || receiverIdentifier === 'module')) {
          fail(`require runtime loader is not allowed in ${fileLabel} at offset ${startToken}`);
        }
        if (token === 'resolve' && receiverIdentifier === 'require') {
          fail(`require.resolve runtime loader is not allowed in ${fileLabel} at offset ${startToken}`);
        }
        if (FORBIDDEN_RUNTIME_LOADER_IDENTIFIERS.has(token)) {
          fail(`${FORBIDDEN_RUNTIME_LOADER_IDENTIFIERS.get(token)} is not allowed in ${fileLabel} at offset ${startToken}`);
        }
        if (STRING_RUNTIME_LOADER_IDENTIFIERS.has(token)) {
          const afterLoader = skipTrivia(source, index);
          if (source[afterLoader] === '(') {
            const argumentStart = skipTrivia(source, afterLoader + 1);
            if (source[argumentStart] === '"' || source[argumentStart] === "'" || source[argumentStart] === '`') {
              fail(`string runtime loader ${token} is not allowed in ${fileLabel} at offset ${startToken}`);
            }
          }
        }
        if (token === 'import') {
          const afterImport = skipTrivia(source, index);
          if (source[afterImport] === '(') {
            const argumentStart = skipTrivia(source, afterImport + 1);
            const argumentChar = source[argumentStart];
            if (argumentChar !== '"' && argumentChar !== "'") {
              fail(`non-literal dynamic import is not allowed in ${fileLabel} at offset ${startToken}`);
            }
            const literal = readQuotedToken(source, argumentStart);
            const afterLiteral = skipTrivia(source, literal.end);
            if (source[afterLiteral] !== ')' && source[afterLiteral] !== ',') {
              fail(`dynamic import must use a single literal first argument in ${fileLabel} at offset ${startToken}`);
            }
            if (isLocalSpecifier(literal.value)) found.push(literal.value);
            index = literal.end;
            canEndExpression = false;
            previousIdentifier = null;
            continue;
          }
        }
        canEndExpression = !REGEX_PREFIX_KEYWORDS.has(token);
        previousIdentifier = token;
        continue;
      }
      if (/[0-9]/u.test(char)) {
        index += 1;
        while (/[A-Za-z0-9_.]/u.test(source[index] ?? '')) index += 1;
        canEndExpression = true;
        previousIdentifier = null;
        continue;
      }
      if (char === ')' || char === ']') {
        canEndExpression = true;
        previousIdentifier = null;
      }
      else if (char === '+' && source[index + 1] === '+') {
        index += 2;
        canEndExpression = true;
        continue;
      } else if (char === '-' && source[index + 1] === '-') {
        index += 2;
        canEndExpression = true;
        continue;
      } else if ('([,;:?=!*%&|^~<>+-'.includes(char)) {
        canEndExpression = false;
        previousIdentifier = null;
      } else if (char === '/') {
        canEndExpression = false;
        previousIdentifier = null;
      } else if (char !== '.') {
        previousIdentifier = null;
      }
      index += 1;
    }
    if (stopOnClosingBrace) fail(`unterminated template expression in ${fileLabel}`);
    return index;
  }

  scanSegment(0, false);
  return found;
}

function parseModuleRequests(source, repoRelativePath) {
  let module;
  try {
    module = new vm.SourceTextModule(source, { identifier: repoRelativePath });
  } catch (error) {
    fail(`JavaScript syntax parse failed for ${repoRelativePath}: ${error.message}`);
  }
  const staticSpecifiers = module.moduleRequests
    ? module.moduleRequests.map((request) => request.specifier)
    : [...(module.dependencySpecifiers ?? [])];
  const dynamicSpecifiers = scanDynamicImports(source, repoRelativePath);
  return { staticSpecifiers, dynamicSpecifiers };
}

function existingCandidate(path) {
  try {
    return lstatSync(path);
  } catch (error) {
    if (error?.code === 'ENOENT') return null;
    throw error;
  }
}

function resolveLocalDependency(importerPath, specifier, explicitRootSet) {
  if (specifier.includes('?') || specifier.includes('#')) fail(`unsupported local specifier suffix in ${importerPath}: ${specifier}`);
  if (specifier.startsWith('file:') || specifier.startsWith('/') || /^[A-Za-z]:[\\/]/u.test(specifier) || specifier.startsWith('\\\\')) {
    fail(`scope escape via absolute local specifier in ${importerPath}: ${specifier}`);
  }
  const importerAbsolute = resolve(REPOSITORY_ROOT, ...importerPath.split('/'));
  const base = resolve(dirname(importerAbsolute), specifier);
  if (!isWithin(REPOSITORY_ROOT, base)) fail(`dependency escapes repository root in ${importerPath}: ${specifier}`);

  const extension = extname(base);
  let target;
  if (extension) {
    if (!SUPPORTED_CODE_EXTENSIONS.has(extension)) {
      fail(`unsupported local dependency type in ${importerPath}: ${specifier}`);
    }
    const exact = existingCandidate(base);
    if (!exact) fail(`missing local dependency in ${importerPath}: ${specifier}`);
    if (exact.isSymbolicLink()) fail(`symlink local dependency in ${importerPath}: ${specifier}`);
    if (!exact.isFile()) fail(`non-regular local dependency in ${importerPath}: ${specifier}`);
    target = base;
  } else {
    const candidates = [
      `${base}.mjs`,
      `${base}.js`,
      join(base, 'index.mjs'),
      join(base, 'index.js'),
    ].filter((candidate) => existingCandidate(candidate));
    for (const candidate of candidates) {
      const stat = existingCandidate(candidate);
      if (stat.isSymbolicLink()) fail(`symlink local dependency in ${importerPath}: ${specifier}`);
      if (!stat.isFile()) fail(`non-regular local dependency in ${importerPath}: ${specifier}`);
    }
    const exact = existingCandidate(base);
    if (exact?.isSymbolicLink()) fail(`symlink local dependency in ${importerPath}: ${specifier}`);
    if (exact && !exact.isDirectory()) {
      fail(`unsupported extensionless local dependency in ${importerPath}: ${specifier}`);
    }
    if (candidates.length > 1) {
      fail(`ambiguous local dependency in ${importerPath}: ${specifier} -> ${candidates.map(toRepoRelative).join(', ')}`);
    }
    if (candidates.length === 0) {
      const parent = dirname(base);
      const prefix = `${base.slice(parent.length + 1)}.`;
      const unsupported = existsSync(parent)
        ? readdirSync(parent).filter((name) => name.startsWith(prefix) && KNOWN_UNSUPPORTED_LOCAL_EXTENSIONS.has(extname(name)))
        : [];
      if (unsupported.length > 0) fail(`unsupported local dependency type in ${importerPath}: ${specifier}`);
      if (exact && !exact.isFile()) fail(`non-regular local dependency in ${importerPath}: ${specifier}`);
      fail(`missing local dependency in ${importerPath}: ${specifier}`);
    }
    target = candidates[0];
  }

  const targetRelative = toRepoRelative(target);
  assertNoSymlinkBelowRepo(target, targetRelative);
  const stat = lstatSync(target);
  if (stat.isSymbolicLink()) fail(`symlink local dependency in ${importerPath}: ${specifier}`);
  if (!stat.isFile()) fail(`non-regular local dependency in ${importerPath}: ${specifier}`);
  if (!SUPPORTED_CODE_EXTENSIONS.has(extname(target))) fail(`unsupported local dependency type in ${importerPath}: ${specifier}`);
  if (!isWithin(CANONICAL_SCOPE, target) && !explicitRootSet.has(targetRelative)) {
    fail(`dependency escapes canonical scope and is not an explicit root in ${importerPath}: ${specifier} -> ${targetRelative}`);
  }
  return targetRelative;
}

function discoverDependencyClosure(rootPaths) {
  const explicitRootSet = new Set(rootPaths);
  const discovered = new Set(rootPaths);
  const queue = [...rootPaths];
  const edges = [];
  while (queue.length > 0) {
    const importerPath = queue.shift();
    const importerAbsolute = assertRepoRegularFile(importerPath, 'code root or dependency');
    if (!SUPPORTED_CODE_EXTENSIONS.has(extname(importerAbsolute))) {
      fail(`unsupported code root type: ${importerPath}`);
    }
    const source = readFileSync(importerAbsolute, 'utf8');
    const { staticSpecifiers, dynamicSpecifiers } = parseModuleRequests(source, importerPath);
    for (const [kind, specifiers] of [['static', staticSpecifiers], ['dynamic-literal', dynamicSpecifiers]]) {
      for (const specifier of specifiers) {
        if (!isLocalSpecifier(specifier)) continue;
        const target = resolveLocalDependency(importerPath, specifier, explicitRootSet);
        edges.push({ importer: importerPath, specifier, target, kind });
        if (!discovered.has(target)) {
          discovered.add(target);
          queue.push(target);
        }
      }
    }
  }
  edges.sort((left, right) => JSON.stringify(left).localeCompare(JSON.stringify(right)));
  const duplicate = edges.find((edge, index) => index > 0 && JSON.stringify(edge) === JSON.stringify(edges[index - 1]));
  if (duplicate) fail(`duplicate dependency edge is not allowed: ${JSON.stringify(duplicate)}`);
  return { codeFiles: [...discovered].sort(), edges };
}

function collectResources(options, codeFileSet) {
  const resourceFileEntries = options.resourcesFile ? readPathList(options.resourcesFile, '--resources-file') : [];
  const directResources = [];
  const values = [...resourceFileEntries];
  for (const [index, raw] of options.directResources.entries()) {
    const value = parseRepoRelativePath(raw, `--resource-file[${index + 1}]`);
    if (value) {
      directResources.push(value);
      values.push(value);
    }
  }
  const resources = [...new Set(values)].sort();
  for (const resource of resources) {
    const absolute = assertRepoRegularFile(resource, 'runtime resource');
    const extension = extname(absolute);
    if (UNSCANNED_EXECUTABLE_RESOURCE_EXTENSIONS.has(extension)) {
      fail(`unsupported unscanned executable resource type is not allowed: ${resource}`);
    }
    if (SUPPORTED_CODE_EXTENSIONS.has(extension) && !codeFileSet.has(resource)) {
      fail(`code resource must be listed in --roots-file so its dependencies are scanned: ${resource}`);
    }
  }
  return { resources, resourceFileEntries, directResources };
}

function walkExactFiles(root) {
  const files = [];
  function walk(directory, prefix = '') {
    const entries = readdirSync(directory, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name));
    for (const entry of entries) {
      const absolute = join(directory, entry.name);
      const rel = prefix ? `${prefix}/${entry.name}` : entry.name;
      const stat = lstatSync(absolute);
      if (stat.isSymbolicLink()) fail(`freeze root contains symlink: ${rel}`);
      if (stat.isDirectory()) walk(absolute, rel);
      else if (stat.isFile()) files.push(rel);
      else fail(`freeze root contains non-regular entry: ${rel}`);
    }
  }
  walk(root);
  return files.sort();
}

function verifyFreezeRoot(freezeRoot, expectedRecords) {
  const expectedPaths = expectedRecords.map((record) => record.path).sort();
  const actualPaths = walkExactFiles(freezeRoot);
  if (JSON.stringify(actualPaths) !== JSON.stringify(expectedPaths)) {
    fail(`freeze root exact-set mismatch; expected=${JSON.stringify(expectedPaths)} actual=${JSON.stringify(actualPaths)}`);
  }
  for (const record of expectedRecords) {
    const absolute = resolve(freezeRoot, ...record.path.split('/'));
    const stat = lstatSync(absolute);
    if (!stat.isFile() || stat.isSymbolicLink()) fail(`freeze root path is not a regular non-symlink file: ${record.path}`);
    const bytes = readFileSync(absolute);
    if (bytes.length !== record.bytes) fail(`freeze root byte-count mismatch: ${record.path}`);
    if (sha256(bytes) !== record.sha256) fail(`freeze root SHA-256 mismatch: ${record.path}`);
  }
}

function writeExclusive(path, content) {
  if (existsSync(path)) fail(`refusing to overwrite output: ${path}`);
  writeFileSync(path, content, { flag: 'wx' });
}

function controlFileRecord(path, entries) {
  const bytes = readFileSync(path);
  return {
    bytes: bytes.length,
    sha256: sha256(bytes),
    mode: '0444',
    entries,
  };
}

function makeFreezeTreeReadOnly(root) {
  const directories = [];
  function walk(directory) {
    directories.push(directory);
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const absolute = join(directory, entry.name);
      const stat = lstatSync(absolute);
      if (stat.isSymbolicLink()) fail(`freeze root contains symlink while applying read-only modes: ${absolute}`);
      if (stat.isDirectory()) walk(absolute);
      else if (stat.isFile()) chmodSync(absolute, 0o444);
      else fail(`freeze root contains non-regular entry while applying read-only modes: ${absolute}`);
    }
  }
  walk(root);
  for (const directory of directories.reverse()) chmodSync(directory, 0o555);
}

function assertMode(path, expected, label) {
  const actual = lstatSync(path).mode & 0o777;
  if (actual !== expected) fail(`${label} mode mismatch: expected ${expected.toString(8)}, received ${actual.toString(8)}`);
}

function verifyFreezeTreeModes(root) {
  function walk(directory) {
    assertMode(directory, 0o555, `freeze directory ${directory}`);
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const absolute = join(directory, entry.name);
      if (entry.isDirectory()) walk(absolute);
      else assertMode(absolute, 0o444, `freeze file ${absolute}`);
    }
  }
  walk(root);
}

function makeWritableForCleanup(path) {
  if (!existsSync(path)) return;
  const stat = lstatSync(path);
  if (stat.isSymbolicLink() || stat.isFile()) {
    if (!stat.isSymbolicLink()) chmodSync(path, 0o644);
    return;
  }
  if (stat.isDirectory()) {
    chmodSync(path, 0o755);
    for (const entry of readdirSync(path)) makeWritableForCleanup(join(path, entry));
  }
}

function buildReviewFreeze(options) {
  validateOutputLayout(options);
  const roots = readPathList(options.rootsFile, '--roots-file');
  if (roots.length === 0) fail('--roots-file must contain at least one code root');
  for (const root of roots) {
    const absolute = assertRepoRegularFile(root, 'code root');
    if (!SUPPORTED_CODE_EXTENSIONS.has(extname(absolute))) fail(`unsupported code root type: ${root}`);
  }

  const { codeFiles, edges } = discoverDependencyClosure(roots);
  const codeFileSet = new Set(codeFiles);
  const { resources, resourceFileEntries, directResources } = collectResources(options, codeFileSet);
  const resourceSet = new Set(resources);
  const exactOverlap = codeFiles.filter((codeFile) => resourceSet.has(codeFile));
  if (exactOverlap.length > 0) {
    fail(`code dependency closure/resources exact overlap is not allowed: ${exactOverlap.join(', ')}`);
  }
  const allFiles = [...new Set([...codeFiles, ...resources])].sort();
  const records = allFiles.map((path) => {
    const bytes = readFileSync(assertRepoRegularFile(path, 'frozen file'));
    return { path, bytes: bytes.length, sha256: sha256(bytes) };
  });
  const fileListBytes = Buffer.from(`${records.map((record) => record.path).join('\n')}\n`);
  const inputModeSnapshots = new Map([
    [options.rootsFile, lstatSync(options.rootsFile).mode & 0o777],
    ...(options.resourcesFile ? [[options.resourcesFile, lstatSync(options.resourcesFile).mode & 0o777]] : []),
  ]);

  const stagingRoot = `${options.freezeRoot}.staging-${process.pid}-${randomBytes(6).toString('hex')}`;
  let activated = false;
  const outputsWritten = [];
  try {
    mkdirSync(stagingRoot, { recursive: false });
    for (const record of records) {
      const source = resolve(REPOSITORY_ROOT, ...record.path.split('/'));
      const destination = resolve(stagingRoot, ...record.path.split('/'));
      mkdirSync(dirname(destination), { recursive: true });
      copyFileSync(source, destination);
    }
    verifyFreezeRoot(stagingRoot, records);
    renameSync(stagingRoot, options.freezeRoot);
    activated = true;
    verifyFreezeRoot(options.freezeRoot, records);

    const manifest = {
      schema_version: 2,
      freeze_id: options.freezeId,
      generated_at: options.generatedAt,
      repository_root: '.',
      canonical_scope: CANONICAL_SCOPE_RELATIVE,
      builder: toRepoRelative(SCRIPT_PATH),
      roots,
      resources,
      source_controls: {
        roots_file: controlFileRecord(options.rootsFile, roots),
        resources_file: options.resourcesFile ? controlFileRecord(options.resourcesFile, resourceFileEntries) : null,
        direct_resources: directResources,
      },
      dependency_closure: {
        parser: 'node:vm.SourceTextModule plus token-aware dynamic-import scanner',
        scanned_code_files: codeFiles.length,
        local_dependency_edges: edges.length,
        edges,
      },
      verification: {
        exact_file_set: true,
        bytes_verified: records.length,
        sha256_verified: records.length,
        symlinks: 0,
        nonregular: 0,
      },
      artifact_controls: {
        freeze_file_mode: '0444',
        freeze_directory_mode: '0555',
        manifest_mode: '0444',
        file_list: {
          bytes: fileListBytes.length,
          sha256: sha256(fileListBytes),
          mode: '0444',
          derivation: 'manifest.files[].path joined by LF with one terminal LF',
        },
        sha_sidecar: {
          present: Boolean(options.shaFilePath),
          mode: options.shaFilePath ? '0444' : null,
          derivation: 'controller-verified manifest SHA-256, two spaces, manifest basename, terminal LF',
        },
      },
      files: records,
    };
    const manifestBytes = `${JSON.stringify(manifest, null, 2)}\n`;
    writeExclusive(options.manifestPath, manifestBytes);
    outputsWritten.push(options.manifestPath);
    writeExclusive(options.fileListPath, fileListBytes);
    outputsWritten.push(options.fileListPath);
    if (options.shaFilePath) {
      writeExclusive(options.shaFilePath, `${sha256(Buffer.from(manifestBytes))}  ${options.manifestPath.split(sep).at(-1)}\n`);
      outputsWritten.push(options.shaFilePath);
    }
    makeFreezeTreeReadOnly(options.freezeRoot);
    chmodSync(options.rootsFile, 0o444);
    if (options.resourcesFile) chmodSync(options.resourcesFile, 0o444);
    chmodSync(options.manifestPath, 0o444);
    chmodSync(options.fileListPath, 0o444);
    if (options.shaFilePath) chmodSync(options.shaFilePath, 0o444);
    verifyFreezeTreeModes(options.freezeRoot);
    assertMode(options.rootsFile, 0o444, 'roots file');
    if (options.resourcesFile) assertMode(options.resourcesFile, 0o444, 'resources file');
    assertMode(options.manifestPath, 0o444, 'manifest');
    assertMode(options.fileListPath, 0o444, 'file list');
    if (options.shaFilePath) assertMode(options.shaFilePath, 0o444, 'SHA sidecar');
    return { manifest, manifestSha256: sha256(Buffer.from(manifestBytes)) };
  } catch (error) {
    makeWritableForCleanup(stagingRoot);
    rmSync(stagingRoot, { recursive: true, force: true });
    for (const path of outputsWritten) {
      makeWritableForCleanup(path);
      rmSync(path, { force: true });
    }
    if (activated) {
      makeWritableForCleanup(options.freezeRoot);
      rmSync(options.freezeRoot, { recursive: true, force: true });
    }
    for (const [path, mode] of inputModeSnapshots) {
      if (existsSync(path)) chmodSync(path, mode);
    }
    throw error;
  }
}

function runCli() {
  try {
    const options = parseArgs(process.argv.slice(2));
    const result = buildReviewFreeze(options);
    process.stdout.write(`REVIEW_FREEZE_PASS freeze_id=${result.manifest.freeze_id} files=${result.manifest.files.length} edges=${result.manifest.dependency_closure.local_dependency_edges} manifest_sha256=${result.manifestSha256}\n`);
  } catch (error) {
    process.stderr.write(`REVIEW_FREEZE_BLOCK: ${error.message}\n`);
    process.exitCode = 1;
  }
}

const isMain = process.argv[1] && realpathSync(process.argv[1]) === realpathSync(SCRIPT_PATH);
if (isMain) {
  if (typeof vm.SourceTextModule !== 'function') {
    const child = spawnSync(process.execPath, ['--experimental-vm-modules', '--no-warnings', SCRIPT_PATH, ...process.argv.slice(2)], {
      stdio: 'inherit',
      env: process.env,
    });
    if (child.error) {
      process.stderr.write(`REVIEW_FREEZE_BLOCK: unable to start Node syntax parser: ${child.error.message}\n`);
      process.exitCode = 1;
    } else {
      process.exitCode = child.status ?? 1;
    }
  } else {
    runCli();
  }
}
