#!/usr/bin/env node
import { readFile, access } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import Ajv2020 from 'ajv/dist/2020.js';
import { parse } from 'acorn';

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
export const ADAPTER_ROOT = resolve(SCRIPT_DIR, '..');
export const REGISTRY_PATH = resolve(ADAPTER_ROOT, 'interface-registry.json');
export const SCHEMA_PATH = resolve(ADAPTER_ROOT, 'interface-registry.schema.json');
const VERIFICATION_CONTRACT_PATH = resolve(ADAPTER_ROOT, 'verification-evidence-contract.json');
const REQUIRED_CLI_COMMANDS = [
  'node verify-media.mjs',
  'npm run interfaces:validate',
  'npm run interfaces:index',
  'npm run interfaces:index:check',
  'npm run scan:actions -- <chunks-text-file>',
];
const REQUIRED_PACKAGE_FILES = [
  'AI-START-HERE.md', 'README.md',
  'interface-registry.json', 'interface-registry.schema.json', 'INTERFACE-INDEX.md',
  'scripts/build-interface-index.mjs', 'scripts/validate-interface-registry.mjs',
  'media-metadata-and-ai-vision-sop.md',
  'verification-evidence-contract.json',
];

function exportedIdentifiers(declaration) {
  if (!declaration) return [];
  if ((declaration.type === 'FunctionDeclaration' || declaration.type === 'ClassDeclaration') && declaration.id) {
    return [declaration.id.name];
  }
  if (declaration.type === 'VariableDeclaration') {
    return declaration.declarations.flatMap((item) => item.id.type === 'Identifier' ? [item.id.name] : []);
  }
  return [];
}

export async function extractEsmExportBindings({ includeSourceOnly = true } = {}) {
  const pkg = JSON.parse(await readFile(resolve(ADAPTER_ROOT, 'package.json'), 'utf8'));
  const sourceModules = [...new Set([
    ...(pkg.files || []),
    ...(includeSourceOnly ? (pkg.source_only_modules || []) : []),
  ])]
    .filter((file) => file.endsWith('.mjs') && !file.endsWith('.test.mjs'))
    .sort();
  const bindings = [];
  for (const module of sourceModules) {
    const source = await readFile(resolve(ADAPTER_ROOT, module), 'utf8');
    const ast = parse(source, { ecmaVersion: 'latest', sourceType: 'module' });
    for (const node of ast.body) {
      if (node.type === 'ExportDefaultDeclaration') {
        bindings.push({ module, export_name: 'default', role: 'definition' });
        continue;
      }
      if (node.type !== 'ExportNamedDeclaration') continue;
      for (const name of exportedIdentifiers(node.declaration)) {
        bindings.push({ module, export_name: name, role: 'definition' });
      }
      for (const specifier of node.specifiers || []) {
        bindings.push({
          module,
          export_name: specifier.exported.name ?? specifier.exported.value,
          role: node.source ? 'reexport' : 'definition',
        });
      }
    }
  }
  return bindings.sort((a, b) => `${a.module}:${a.export_name}`.localeCompare(`${b.module}:${b.export_name}`));
}

function decodePointerToken(token) {
  return token.replace(/~1/g, '/').replace(/~0/g, '~');
}

async function referenceExists(ref) {
  try {
    await access(resolve(ADAPTER_ROOT, ref.path));
    return true;
  } catch {
    return false;
  }
}

async function assertReference(ref, errors, { requireSourceOnly }) {
  const absolute = resolve(ADAPTER_ROOT, ref.path);
  if (!absolute.startsWith(`${ADAPTER_ROOT}/`) && absolute !== ADAPTER_ROOT) {
    errors.push(`reference escapes adapter root: ${ref.path}`);
    return;
  }
  if (!await referenceExists(ref)) {
    if (ref.availability === 'source_only' && !requireSourceOnly) return;
    errors.push(`missing reference: ${ref.path}`);
    return;
  }
  if (ref.pointer === undefined) return;
  let value;
  try {
    value = JSON.parse(await readFile(absolute, 'utf8'));
  } catch {
    errors.push(`JSON Pointer targets a non-JSON file: ${ref.path}${ref.pointer}`);
    return;
  }
  if (ref.pointer === '') return;
  for (const token of ref.pointer.slice(1).split('/').map(decodePointerToken)) {
    if (value === null || typeof value !== 'object' || !Object.hasOwn(value, token)) {
      errors.push(`unresolved JSON Pointer: ${ref.path}${ref.pointer}`);
      return;
    }
    value = value[token];
  }
}

function packageNameForSpecifier(specifier) {
  if (typeof specifier !== 'string' || !specifier || specifier.startsWith('.')
      || specifier.startsWith('node:')) return null;
  const parts = specifier.split('/');
  return specifier.startsWith('@') ? parts.slice(0, 2).join('/') : parts[0];
}

function collectModuleSpecifiers(node, state) {
  if (!node || typeof node !== 'object') return;
  if (['ImportDeclaration', 'ExportNamedDeclaration', 'ExportAllDeclaration'].includes(node.type)
      && typeof node.source?.value === 'string') state.specifiers.add(node.source.value);
  if (node.type === 'ImportExpression') {
    if (typeof node.source?.value === 'string') state.specifiers.add(node.source.value);
    else if (node.source?.type === 'TemplateLiteral' && node.source.expressions.length === 0) {
      state.specifiers.add(node.source.quasis[0]?.value?.cooked ?? node.source.quasis[0]?.value?.raw);
    } else state.nonLiteralDynamicImports += 1;
  }
  for (const value of Object.values(node)) {
    if (Array.isArray(value)) value.forEach((child) => collectModuleSpecifiers(child, state));
    else if (value && typeof value === 'object') collectModuleSpecifiers(value, state);
  }
}

async function validateRuntimeDependencyClosure(pkg, errors) {
  const packageFiles = new Set(pkg.files || []);
  const runtimeDependencies = new Set(Object.keys(pkg.dependencies || {}));
  const runtimeImports = new Map();
  for (const module of (pkg.files || []).filter((file) => file.endsWith('.mjs')).sort()) {
    const source = await readFile(resolve(ADAPTER_ROOT, module), 'utf8');
    const ast = parse(source, { ecmaVersion: 'latest', sourceType: 'module' });
    const state = { specifiers: new Set(), nonLiteralDynamicImports: 0 };
    collectModuleSpecifiers(ast, state);
    if (state.nonLiteralDynamicImports) {
      errors.push(`packaged module ${module} contains ${state.nonLiteralDynamicImports} non-literal dynamic import(s); runtime closure cannot be proven`);
    }
    for (const specifier of state.specifiers) {
      if (specifier.startsWith('.')) {
        const target = resolve(ADAPTER_ROOT, dirname(module), specifier);
        const relativeTarget = target.slice(`${ADAPTER_ROOT}/`.length);
        if (!target.startsWith(`${ADAPTER_ROOT}/`) || !packageFiles.has(relativeTarget)) {
          errors.push(`packaged module ${module} imports local module not present in package files: ${specifier}`);
        }
        continue;
      }
      if (specifier.startsWith('/') || specifier.startsWith('file:') || specifier.startsWith('data:')) {
        errors.push(`packaged module ${module} uses non-portable runtime import: ${specifier}`);
        continue;
      }
      const packageName = packageNameForSpecifier(specifier);
      if (!packageName) continue;
      const modules = runtimeImports.get(packageName) ?? new Set();
      modules.add(module);
      runtimeImports.set(packageName, modules);
    }
  }
  for (const [packageName, modules] of runtimeImports) {
    if (!runtimeDependencies.has(packageName)) {
      errors.push(`packaged runtime import ${packageName} is not declared in dependencies: ${[...modules].join(', ')}`);
    }
  }
}

function findCycles(registry, errors) {
  const byId = new Map(registry.interfaces.map((item) => [item.interface_id, item]));
  for (const item of registry.interfaces) {
    const next = item.alias_of || item.deprecated_by;
    if (!next) continue;
    if (!byId.has(next)) errors.push(`${item.interface_id} points to missing interface ${next}`);
    if (next === item.interface_id) errors.push(`${item.interface_id} points to itself`);
    const seen = new Set([item.interface_id]);
    let cursor = next;
    while (cursor && byId.has(cursor)) {
      if (seen.has(cursor)) {
        errors.push(`interface relationship cycle includes ${cursor}`);
        break;
      }
      seen.add(cursor);
      const target = byId.get(cursor);
      cursor = target.alias_of || target.deprecated_by;
    }
  }
}

function scanForbiddenDynamicValues(registry, errors) {
  const text = JSON.stringify(registry);
  const patterns = [
    [/\bBearer\s+[A-Za-z0-9._~-]+/i, 'Bearer credential'],
    [/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i, 'email address'],
    [/\b[0-9a-f]{24}\b/i, '24-character runtime object ID'],
    [/\b[0-9a-f]{40,64}\b/i, 'runtime action/deployment/hash value'],
    [/\/Users\/[A-Za-z0-9._-]+\//, 'private absolute user path'],
    [/\b(cookie|session_token|access_token)\s*[:=]\s*["'][^"']+/i, 'credential value'],
  ];
  for (const [pattern, label] of patterns) {
    if (pattern.test(text)) errors.push(`forbidden dynamic/private value detected: ${label}`);
  }
}

export async function validateInterfaceRegistry({ requireSourceOnly } = {}) {
  const [registry, schema, pkg, verificationContract] = await Promise.all([
    readFile(REGISTRY_PATH, 'utf8').then(JSON.parse),
    readFile(SCHEMA_PATH, 'utf8').then(JSON.parse),
    readFile(resolve(ADAPTER_ROOT, 'package.json'), 'utf8').then(JSON.parse),
    readFile(VERIFICATION_CONTRACT_PATH, 'utf8').then(JSON.parse),
  ]);
  const errors = [];
  const packageFiles = new Set(pkg.files || []);
  const sourceOnlyModules = new Set(registry.source_only_modules || []);
  const sourceCheckoutMarker = await referenceExists({ path: 'package-lock.json' });
  if (requireSourceOnly === undefined) requireSourceOnly = sourceCheckoutMarker;
  if (!requireSourceOnly && sourceCheckoutMarker) errors.push('package reference scope cannot be selected while source checkout marker package-lock.json exists');
  if (requireSourceOnly && !sourceCheckoutMarker) errors.push('source reference scope requires package-lock.json source checkout marker');
  const ajv = new Ajv2020({ allErrors: true, strict: true, strictRequired: false });
  ajv.addFormat('date', /^\d{4}-\d{2}-\d{2}$/);
  const validate = ajv.compile(schema);
  if (!validate(registry)) {
    for (const error of validate.errors || []) errors.push(`schema ${error.instancePath || '/'} ${error.message}`);
  }

  const ids = new Set();
  const registryBindings = new Map();
  const cliBindings = new Map();
  for (const item of registry.interfaces) {
    if (ids.has(item.interface_id)) errors.push(`duplicate interface_id: ${item.interface_id}`);
    ids.add(item.interface_id);
    if (item.exposure === 'blocked' && !item.blocked_reason) errors.push(`${item.interface_id} is blocked without blocked_reason`);
    if (item.exposure !== 'blocked' && item.blocked_reason) errors.push(`${item.interface_id} has blocked_reason but exposure is ${item.exposure}`);
    if (item.lifecycle === 'deprecated' && !item.deprecated_by) errors.push(`${item.interface_id} is deprecated without deprecated_by`);
    if (item.lifecycle === 'removed' && item.bindings.length) errors.push(`${item.interface_id} is removed but still has bindings`);
    if (item.alias_of && !item.bindings.every((binding) => binding.role === 'reexport')) errors.push(`${item.interface_id} alias_of must use only reexport bindings`);
    if (item.bindings.some((binding) => binding.export_name === '_internal') && item.exposure !== 'internal') errors.push(`${item.interface_id} exposes _internal outside internal`);
    if (item.safety.mutation && item.safety.network_access === 'mutation' && item.safety.authorization.required !== true) {
      errors.push(`${item.interface_id} remote mutation does not require authorization`);
    }
    if (item.safety.mutation && item.safety.readback === 'not_applicable') errors.push(`${item.interface_id} mutation does not declare readback semantics`);
    if (item.safety.mutation && item.safety.network_access === 'none' && item.safety.request_may_have_succeeded !== 'false') {
      errors.push(`${item.interface_id} local mutation must declare request_may_have_succeeded=false`);
    }
    const esmModules = item.bindings
      .filter((binding) => binding.type === 'esm_export')
      .map((binding) => binding.module);
    const usesSourceOnlyModule = esmModules.some((module) => sourceOnlyModules.has(module));
    const usesPackagedModule = esmModules.some((module) => !sourceOnlyModules.has(module));
    if (usesSourceOnlyModule && usesPackagedModule) {
      errors.push(`${item.interface_id} mixes packaged and source-only ESM bindings`);
    }
    const expectedRuntimeAvailability = usesSourceOnlyModule ? 'source_only' : 'packaged';
    if (item.runtime_availability !== expectedRuntimeAvailability) {
      errors.push(`${item.interface_id} runtime_availability=${item.runtime_availability}; expected ${expectedRuntimeAvailability}`);
    }
    for (const binding of item.bindings) {
      if (binding.type === 'esm_export') {
        const key = `${binding.module}:${binding.export_name}`;
        if (registryBindings.has(key)) errors.push(`duplicate source binding ${key}: ${registryBindings.get(key)} and ${item.interface_id}`);
        registryBindings.set(key, item.interface_id);
      }
      if (binding.type === 'cli') {
        if (cliBindings.has(binding.command)) errors.push(`duplicate CLI binding ${binding.command}: ${cliBindings.get(binding.command)} and ${item.interface_id}`);
        cliBindings.set(binding.command, item.interface_id);
      }
    }
    if (!item.contract_refs.some((ref) => ref.availability === 'packaged')) {
      errors.push(`${item.interface_id} must expose at least one packaged portable contract_ref`);
    }
    for (const ref of item.test_refs) {
      if (ref.availability !== 'source_only') errors.push(`${item.interface_id} test_ref must declare availability=source_only: ${ref.path}`);
    }
    for (const ref of [...item.contract_refs, ...item.test_refs, ...item.evidence.refs]) {
      await assertReference(ref, errors, { requireSourceOnly });
      if (ref.availability === 'packaged' && !packageFiles.has(ref.path)) {
        errors.push(`package.json files missing packaged reference ${ref.path} for ${item.interface_id}`);
      }
      if (ref.availability === 'source_only' && packageFiles.has(ref.path)) {
        errors.push(`source_only reference is unexpectedly packaged: ${ref.path} for ${item.interface_id}`);
      }
    }
  }
  findCycles(registry, errors);
  scanForbiddenDynamicValues(registry, errors);

  for (const module of sourceOnlyModules) {
    if (packageFiles.has(module)) errors.push(`source_only module is unexpectedly packaged: ${module}`);
    await assertReference({ path: module, availability: 'source_only' }, errors, { requireSourceOnly });
  }
  const allowedEvidenceKinds = new Set();
  for (const kind of verificationContract.evidence_kinds || []) {
    if (allowedEvidenceKinds.has(kind)) errors.push(`duplicate verification evidence kind: ${kind}`);
    allowedEvidenceKinds.add(kind);
  }
  const verificationCheckIds = new Set();
  for (const definition of verificationContract.check_definitions || []) {
    if (verificationCheckIds.has(definition.check_id)) errors.push(`duplicate verification check_id: ${definition.check_id}`);
    verificationCheckIds.add(definition.check_id);
    if (!allowedEvidenceKinds.has(definition.evidence_kind)) {
      errors.push(`verification check ${definition.check_id} uses unknown evidence kind ${definition.evidence_kind}`);
    }
  }
  const verificationProfiles = new Map();
  for (const profile of verificationContract.profiles || []) {
    if (verificationProfiles.has(profile.capability_id)) errors.push(`duplicate verification profile capability_id: ${profile.capability_id}`);
    verificationProfiles.set(profile.capability_id, profile);
    for (const checkId of profile.required_check_ids || []) {
      if (!verificationCheckIds.has(checkId)) errors.push(`verification profile ${profile.capability_id} references unknown check ${checkId}`);
    }
  }

  const readOnlyVerificationProfiles = new Map();
  for (const profile of verificationContract.read_only_profiles || []) {
    if (!['noop', 'explore'].includes(profile.intent)) errors.push(`unknown read-only verification intent: ${profile.intent}`);
    if (readOnlyVerificationProfiles.has(profile.intent)) errors.push(`duplicate read-only verification profile intent: ${profile.intent}`);
    readOnlyVerificationProfiles.set(profile.intent, profile);
    for (const checkId of profile.required_check_ids || []) {
      if (!verificationCheckIds.has(checkId)) errors.push(`read-only verification profile ${profile.intent} references unknown check ${checkId}`);
    }
  }
  for (const intent of ['noop', 'explore']) {
    const profile = readOnlyVerificationProfiles.get(intent);
    if (!profile) errors.push(`missing read-only verification profile: ${intent}`);
    else if (!Array.isArray(profile.required_check_ids) || profile.required_check_ids.length === 0 || new Set(profile.required_check_ids).size !== profile.required_check_ids.length) {
      errors.push(`read-only verification profile ${intent} must contain unique required checks`);
    }
  }

  const routeKeys = new Set();
  const interfaceById = new Map(registry.interfaces.map((item) => [item.interface_id, item]));
  for (const route of registry.capability_routes || []) {
    const routeKey = `${route.entity_type}:${route.action}`;
    if (routeKeys.has(routeKey)) errors.push(`duplicate capability route: ${routeKey}`);
    routeKeys.add(routeKey);
    if (route.capability_id !== `allincms.${route.entity_type}.${route.action}`) {
      errors.push(`${route.capability_id} does not match ${routeKey}`);
    }
    for (const field of ['default_interface_id', 'controller_interface_id']) {
      const interfaceId = route[field];
      if (interfaceId === null) continue;
      const target = interfaceById.get(interfaceId);
      if (!target) {
        errors.push(`${route.capability_id} points to missing ${field} ${interfaceId}`);
        continue;
      }
      if (field === 'default_interface_id') {
        if (route.availability === 'canonical' && target.exposure !== 'canonical') {
          errors.push(`${route.capability_id} canonical route targets non-canonical interface ${interfaceId}`);
        }
        if (route.availability === 'blocked' && target.exposure !== 'blocked') {
          errors.push(`${route.capability_id} blocked route targets non-blocked interface ${interfaceId}`);
        }
      }
    }
    if (route.availability === 'exploration_only') {
      if (route.execution_gate !== 'exploration_only') errors.push(`${route.capability_id} exploration_only route has execution_gate=${route.execution_gate}`);
      if (route.default_interface_id !== null || route.controller_interface_id !== null) errors.push(`${route.capability_id} exploration_only route must not bind an execution interface`);
    }
    if (route.availability === 'blocked') {
      if (route.execution_gate !== 'blocked') errors.push(`${route.capability_id} blocked route has execution_gate=${route.execution_gate}`);
      if (route.controller_interface_id !== null) errors.push(`${route.capability_id} blocked route must not bind a controller`);
    }
    if (['canonical', 'supported'].includes(route.availability)
        && !['current_session_read_only', 'fresh_live_verified_current_deployment'].includes(route.execution_gate)) {
      errors.push(`${route.capability_id} ${route.availability} route has non-executable execution_gate=${route.execution_gate}`);
    }
    if (route.execution_gate === 'fresh_live_verified_current_deployment' && route.controller_interface_id === null) {
      errors.push(`${route.capability_id} executable mutation route has no serial controller`);
    }
    const expectedExecutionSurface = {
      current_session_read_only: 'minimal_adapter',
      fresh_live_verified_current_deployment: 'full_source_checkout',
      exploration_only: 'none',
      blocked: 'none',
    }[route.execution_gate];
    if (route.execution_surface !== expectedExecutionSurface) {
      errors.push(`${route.capability_id} execution_surface=${route.execution_surface}; expected ${expectedExecutionSurface} for ${route.execution_gate}`);
    }
    if (route.execution_surface === 'minimal_adapter') {
      const target = interfaceById.get(route.default_interface_id);
      if (!target || target.runtime_availability !== 'packaged') {
        errors.push(`${route.capability_id} minimal_adapter route must target a packaged default interface`);
      }
      if (target?.safety.mutation || !['read_only', 'none'].includes(target?.safety.network_access)) {
        errors.push(`${route.capability_id} minimal_adapter route must remain read-only`);
      }
      if (route.controller_interface_id !== null) errors.push(`${route.capability_id} minimal_adapter route must not bind the source-only controller`);
    }
    if (route.execution_surface === 'full_source_checkout') {
      const defaultTarget = interfaceById.get(route.default_interface_id);
      const controllerTarget = interfaceById.get(route.controller_interface_id);
      if (!defaultTarget || defaultTarget.runtime_availability !== 'packaged') {
        errors.push(`${route.capability_id} full_source_checkout route must target a packaged mutation primitive`);
      }
      if (!controllerTarget || controllerTarget.runtime_availability !== 'source_only') {
        errors.push(`${route.capability_id} full_source_checkout route must bind a source-only controller`);
      }
      if (!defaultTarget?.safety.mutation || defaultTarget?.safety.network_access !== 'mutation') {
        errors.push(`${route.capability_id} full_source_checkout route must target a remote mutation interface`);
      }
      if (route.controller_interface_id !== 'allincms.content-run-controller.run-allin-cms-content-plan') {
        errors.push(`${route.capability_id} executable mutation route must use the canonical serial content controller`);
      }
    }
    if (route.execution_surface === 'none' && route.controller_interface_id !== null) {
      errors.push(`${route.capability_id} execution_surface=none must not bind a controller`);
    }
    const verificationProfile = verificationProfiles.get(route.capability_id);
    if (route.execution_surface === 'full_source_checkout') {
      if (!verificationProfile) {
        errors.push(`${route.capability_id} full_source_checkout mutation route has no verification profile`);
      } else {
        const routeChecks = [...(route.verification_requirements || [])].sort();
        const profileChecks = [...(verificationProfile.required_check_ids || [])].sort();
        if (JSON.stringify(routeChecks) !== JSON.stringify(profileChecks)) {
          errors.push(`${route.capability_id} verification requirements must exactly match its verification profile`);
        }
      }
    } else if (verificationProfile) {
      errors.push(`${route.capability_id} non-full-source route must not bind a mutation verification profile`);
    }
  }
  for (const capabilityId of verificationProfiles.keys()) {
    if (!(registry.capability_routes || []).some((route) => route.capability_id === capabilityId)) {
      errors.push(`verification profile points to missing capability route: ${capabilityId}`);
    }
  }
  const requiredCapabilityRoutes = [
    'site:discover', 'site:create', 'site:delete',
    'category:create', 'category:update', 'category:delete',
    'tag:create', 'tag:update', 'tag:delete',
    'media:create', 'media:update', 'media:delete',
    'article:create', 'article:update', 'article:publish', 'article:unpublish', 'article:delete',
    'product:discover', 'product:create', 'product:update', 'product:publish', 'product:delete',
  ];
  for (const routeKey of requiredCapabilityRoutes) if (!routeKeys.has(routeKey)) errors.push(`missing capability route: ${routeKey}`);
  const allowedCapabilityRoutes = new Set(requiredCapabilityRoutes);
  for (const routeKey of routeKeys) if (!allowedCapabilityRoutes.has(routeKey)) errors.push(`unexpected capability route: ${routeKey}`);

  const sourceBindings = await extractEsmExportBindings({ includeSourceOnly: requireSourceOnly });
  const sourceMap = new Map(sourceBindings.map((binding) => [`${binding.module}:${binding.export_name}`, binding]));
  for (const [key, id] of registryBindings) {
    const module = key.slice(0, key.indexOf(':'));
    if (!requireSourceOnly && sourceOnlyModules.has(module)) continue;
    if (!sourceMap.has(key)) errors.push(`registry binding not found in source: ${key} (${id})`);
  }
  for (const [key, binding] of sourceMap) {
    if (!registryBindings.has(key)) errors.push(`source export missing from registry: ${key}`);
    const item = registry.interfaces.find((candidate) => candidate.bindings.some((entry) => entry.type === 'esm_export' && `${entry.module}:${entry.export_name}` === key));
    const registered = item?.bindings.find((entry) => entry.type === 'esm_export' && `${entry.module}:${entry.export_name}` === key);
    if (registered && registered.role !== binding.role) errors.push(`binding role drift for ${key}: source=${binding.role}, registry=${registered.role}`);
  }

  const registeredCliCommands = [...cliBindings.keys()].sort();
  if (JSON.stringify(registeredCliCommands) !== JSON.stringify([...REQUIRED_CLI_COMMANDS].sort())) {
    errors.push(`CLI binding set drift: expected ${REQUIRED_CLI_COMMANDS.join(' | ')}, got ${registeredCliCommands.join(' | ')}`);
  }
  const expectedPackageScripts = {
    'interfaces:validate': 'node scripts/validate-interface-registry.mjs',
    'interfaces:index': 'node scripts/build-interface-index.mjs',
    'interfaces:index:check': 'node scripts/build-interface-index.mjs --check',
  };
  for (const [name, command] of Object.entries(expectedPackageScripts)) {
    if (pkg.scripts?.[name] !== command) errors.push(`package.json script ${name} must remain ${command}`);
  }

  await validateRuntimeDependencyClosure(pkg, errors);
  for (const [name, expected] of Object.entries({ acorn: '8.15.0', ajv: '8.20.0', sharp: '0.35.3' })) {
    if (pkg.dependencies?.[name] !== expected) errors.push(`package.json runtime dependency ${name} must remain exactly ${expected}`);
    if (pkg.devDependencies?.[name]) errors.push(`package.json runtime dependency ${name} must not be dev-only`);
  }

  for (const file of REQUIRED_PACKAGE_FILES) if (!packageFiles.has(file)) errors.push(`package.json files missing ${file}`);
  if (JSON.stringify([...(pkg.source_only_modules || [])].sort()) !== JSON.stringify([...(registry.source_only_modules || [])].sort())) {
    errors.push('package.json source_only_modules must exactly match Registry source_only_modules');
  }
  if (registry.adapter.package_version !== pkg.version) errors.push(`registry package_version ${registry.adapter.package_version} does not match package.json ${pkg.version}`);
  if (registry.adapter.release_scope === 'stable') errors.push('current adapter may not be declared stable while the sub-library release remains blocked');

  return {
    ok: errors.length === 0,
    errors,
    summary: {
      interfaces: registry.interfaces.length,
      esmBindings: sourceBindings.length,
      cliBindings: cliBindings.size,
      canonical: registry.interfaces.filter((item) => item.exposure === 'canonical').length,
      blocked: registry.interfaces.filter((item) => item.exposure === 'blocked').length,
      referenceScope: requireSourceOnly ? 'source' : 'package',
    },
    registry,
  };
}

async function main() {
  const result = await validateInterfaceRegistry();
  if (!result.ok) {
    console.error(JSON.stringify({ ok: false, errors: result.errors, summary: result.summary }, null, 2));
    process.exitCode = 1;
    return;
  }
  console.log(JSON.stringify({ ok: true, summary: result.summary }, null, 2));
}

if (import.meta.url === pathToFileURL(process.argv[1] || '').href) await main();
