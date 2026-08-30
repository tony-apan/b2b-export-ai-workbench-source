#!/usr/bin/env node
import { assertDisplayText, nowIso, parseArgs, defaultRuntimePath, getClient, loadEntities, assertEntityId, CHANNEL_TYPES, SECRET_REF_RE, withRuntimeWriteLock, writeJsonAtomic } from './runtime-lib.mjs';

try {
  const args = parseArgs();
  const type = args.type;
  if (!['company','product','channel','account'].includes(type)) throw new Error('--type must be company, product, channel, or account');
  const id = assertEntityId(type, args.id);
  const name = assertDisplayText(args.name, '--name');
  const runtime = defaultRuntimePath(args);

  withRuntimeWriteLock(runtime, `register-entity:${args.client}/${type}/${id}`, () => {
    const { path: clientRoot } = getClient(runtime, args.client);
    const { path, entities } = loadEntities(clientRoot);
    const config = { company: ['companies','company_id'], product: ['products','product_id'], channel: ['channels','channel_id'], account: ['accounts','account_id'] }[type];
    const [collection, idField] = config;
    if (entities[collection].some((entry) => entry[idField] === id)) throw new Error(`duplicate ${idField}: ${id}`);
    const occurredAt = nowIso();
    const record = { [idField]: id, display_name: name, status: 'active', created_at: occurredAt, updated_at: occurredAt };
    if (type !== 'company') {
      const companyId = assertEntityId('company', args.company);
      if (!entities.companies.some((entry) => entry.company_id === companyId)) throw new Error(`unregistered company_id: ${companyId}`);
      record.company_id = companyId;
    }
    if (type === 'channel') {
      if (!CHANNEL_TYPES.has(args['channel-type'])) throw new Error('--channel-type must be website, social, laifaxin, or email');
      record.channel_type = args['channel-type'];
    }
    if (type === 'account') {
      const channelId = assertEntityId('channel', args.channel);
      const channel = entities.channels.find((entry) => entry.channel_id === channelId);
      if (!channel) throw new Error(`unregistered channel_id: ${channelId}`);
      if (channel.company_id !== record.company_id) throw new Error('account company_id must match its channel company_id');
      const secretRef = args['secret-ref'] ?? null;
      if (secretRef !== null && !SECRET_REF_RE.test(secretRef)) throw new Error('--secret-ref must be an opaque keychain://, 1password://, secret-manager://, env-ref://, or manual-login:// reference');
      record.channel_id = channelId;
      record.secret_ref = secretRef;
      record.external_actions_default = 'deny';
    }
    entities[collection].push(record);
    writeJsonAtomic(path, entities);
  });
  console.log(`ENTITY_REGISTER_PASS:${args.client}/${type}/${id}`);
  console.error('NEXT: run sync-runtime-indexes.mjs before relying on generated search');
} catch (error) {
  console.error(`ENTITY_REGISTER_BLOCK:${error.message}`);
  process.exit(error.exitCode ?? 1);
}
