import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createAllinCmsChromeAppleScriptTransport } from './host-run-template.mjs';

test('transport bridge is UTF-8 safe and never uses eval(atob)', async () => {
  const calls = [];
  const exec = async (cmd, args, opts) => { calls.push({ cmd, args }); return '::T::ok'; };
  const t = createAllinCmsChromeAppleScriptTransport({ siteKey: 'synthetic-site', exec });
  const bridge = t.buildBridgeJs('var x="中文";');
  assert.match(bridge, /new TextDecoder\(\)\.decode/);
  assert.doesNotMatch(bridge, /eval\(atob\(/);
  await t.runInTab('1+1');
  assert.equal(calls.length, 1);
  const scriptFile = readFileSync('/tmp/allincms-host-drive.applescript', 'utf8');
  assert.match(scriptFile, /synthetic-site/);
  assert.match(scriptFile, /new TextDecoder\(\)\.decode/);
});

test('template run requires real authoritative hooks', async () => {
  const { runAllinCmsHostPlanTemplate } = await import('./host-run-template.mjs');
  await assert.rejects(() => runAllinCmsHostPlanTemplate({ plan: {}, runtime: {}, hooks: {}, transport: {} }), /requires hook readbackProvider/);
});
