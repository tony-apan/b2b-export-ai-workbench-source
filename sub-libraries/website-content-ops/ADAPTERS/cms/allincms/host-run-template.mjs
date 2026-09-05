/**
 * SAFE canonical AllinCMS host-run template (2026-08-27; article-create
 * default providers added 2026-09-06, P0-3.3b).
 * Use this instead of historical diagnostic drivers.
 *
 * - UTF-8-safe in-page bridge: `new TextDecoder().decode(Uint8Array.from(atob(...)))` —
 *   never `eval(atob(...))` (Latin-1 mangles UTF-8/CJK payloads; caused a public-page
 *   mojibake incident, now fixed at contract level).
 * - No real IDs embedded: action Ids are discovered at runtime via
 *   `scripts/scan-server-action-ids.mjs` (5th-argument literal capture only).
 * - Authorization: freeze-and-archive the plan window (approved_at/expires_at/digest)
 *   in the same file-write step before any request; request-time validation is not a
 *   substitute for an archived window.
 * - readback `passed` MUST come from real comparisons; never hardcode true.
 *
 * article:create default providers (P0-3.3b): the transport above (macOS
 * AppleScript + Chrome) is only ONE host transport option and does not work
 * on Windows. The three article:create host providers are pure-HTTP RSC
 * readers (Node `fetch` + `Cookie: payload-token=...`, no browser, no
 * AppleScript) and therefore cross-platform: macOS, Windows and Linux. When
 * the caller does NOT supply an article hook explicitly
 * (articleBeforePostIdsProvider / articleCreateReadbackProvider /
 * articleEditorReopenProvider) but injects `authCookie` (a payload-token
 * value), this template assembles the real providers from
 * article-create-providers.mjs (origin defaults to the workspace domain
 * https://workspace.laicms.com — the editor routes live there, NOT on the
 * per-site public domain — and stays injectable via `providerOrigin`;
 * `fetchFn` passes through for tests). Explicit hooks always win per slot;
 * with neither a hook nor an authCookie nothing is wired and the driver
 * keeps its own fail-closed refusal. product:create providers are NOT
 * defaulted here (P0-3.3b covers article only).
 */
import { tmpdir } from 'node:os';
import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { createArticleCreateProviders } from './article-create-providers.mjs';

export function createAllinCmsChromeAppleScriptTransport({ siteKey, exec = execFileSync }) {
  if (!siteKey) throw new Error('siteKey is required');
  const b64 = (s) => Buffer.from(s, 'utf8').toString('base64');
  function runInTab(js) {
    const payload = `eval(new TextDecoder().decode(Uint8Array.from(atob('${b64(js)}'),c=>c.charCodeAt(0))))`;
    const script = `tell application "Google Chrome"
	set jsPayload to "${payload}"
	repeat with w in windows
		repeat with t in tabs of w
			if URL of t starts with "https://workspace.laicms.com/${siteKey}" then
				return execute t javascript jsPayload
			end if
		end repeat
	end repeat
	return "::NO_TAB"
end tell`;
    try {
      writeFileSync(join(tmpdir(), 'allincms-host-drive.applescript'), script);
      return exec('osascript', [join(tmpdir(), 'allincms-host-drive.applescript')], { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 });
    } catch (error) {
      return '::ERR::' + String(error.stdout || error.message).slice(0, 240);
    }
  }
  const request = async (details) => {
    const js = `(function(){try{var d=${JSON.stringify(details)};var r=new XMLHttpRequest();r.open('POST',d.url,false);for(var k in d.headers){r.setRequestHeader(k,d.headers[k]);}r.withCredentials=true;r.send(d.body);return '::R::'+JSON.stringify({status:r.status,text:r.responseText.slice(0,12000)});}catch(e){return '::E::'+e.message}})()`;
    const out = runInTab(js);
    if (out.startsWith('::R::')) return JSON.parse(out.slice(5));
    return { status: 0, ok: false, contentType: null };
  };
  const readRouterTree = () => {
    const out = runInTab(`JSON.stringify(history.state?.__PRIVATE_NEXTJS_INTERNALS_TREE?.tree || null)`);
    return out && out.trim() !== 'null' ? out.trim() : '[]';
  };
  return { runInTab, request, readRouterTree, buildBridgeJs: (js) => `eval(new TextDecoder().decode(Uint8Array.from(atob('${b64(js)}'),c=>c.charCodeAt(0))))` };
}

const ARTICLE_CREATE_PROVIDER_HOOKS = Object.freeze([
  ['articleBeforePostIdsProvider', 'beforePostIds'],
  ['articleCreateReadbackProvider', 'createReadback'],
  ['articleEditorReopenProvider', 'editorReopen'],
]);

// Defaults are assembled only for article:create provider slots the hooks do
// NOT fill, and only when an authCookie is injected; explicit hooks always
// win per slot. With neither, nothing is wired and the driver's own
// fail-closed refusal fires. A mixed set (e.g. a custom beforePostIds plus
// the default createReadback) stays allowed: the default createReadback then
// fails closed at runtime because its before/after delta memo was never
// taken through this provider set.
function assembleDefaultArticleCreateProviders(plan, hooks, { authCookie, providerOrigin, fetchFn }) {
  const missing = ARTICLE_CREATE_PROVIDER_HOOKS
    .filter(([hookName]) => typeof hooks?.[hookName] !== 'function');
  if (missing.length === 0) return {};
  if (authCookie === null || authCookie === undefined || authCookie === '') return {};
  const siteKey = plan?.site_selector?.site_key;
  const siteId = plan?.site_selector?.site_id;
  if (!siteKey || !siteId) {
    throw new Error(`runAllinCmsHostPlanTemplate cannot assemble the default article:create providers: plan.site_selector.site_key/site_id are required (got site_key=${JSON.stringify(siteKey)}, site_id=${JSON.stringify(siteId)})`);
  }
  const providers = createArticleCreateProviders({
    siteKey,
    siteId,
    authCookie,
    ...(providerOrigin === null || providerOrigin === undefined ? {} : { origin: providerOrigin }),
    ...(fetchFn === undefined ? {} : { fetchFn }),
  });
  const defaults = {};
  for (const [hookName, providerName] of missing) defaults[hookName] = providers[providerName];
  return defaults;
}

export async function runAllinCmsHostPlanTemplate({
  plan, runtime, hooks, transport, evidencePath,
  authCookie = null, providerOrigin = null, fetchFn = undefined,
}) {
  const required = ['readbackProvider', 'fingerprintProvider', 'backendReadback', 'preflight', 'writeEvidence', 'readEvidenceArtifact'];
  for (const key of required) {
    if (!hooks || typeof hooks[key] !== 'function') throw new Error(`runAllinCmsHostPlanTemplate requires hook ${key} (implement real authoritative comparisons; never hardcode passed)`);
  }
  const { runAllinCmsContentPlan } = await import('./content-run-controller.mjs');
  const { createAllinCmsPlanHandlerSet } = await import('./content-plan-host-driver.mjs');
  // P0-3.3b: defaults first, explicit hooks spread after, so an explicit
  // hook always overrides the assembled default for its slot.
  const defaultArticleProviders = assembleDefaultArticleCreateProviders(plan, hooks, { authCookie, providerOrigin, fetchFn });
  const handlers = createAllinCmsPlanHandlerSet({ siteKey: plan.site_selector.site_key, siteId: plan.site_selector.site_id, runtime, request: transport.request, ...defaultArticleProviders, ...hooks });
  return runAllinCmsContentPlan({ plan, handlers, preflight: hooks.preflight, writeEvidence: hooks.writeEvidence, readEvidenceArtifact: hooks.readEvidenceArtifact, evidencePath });
}
