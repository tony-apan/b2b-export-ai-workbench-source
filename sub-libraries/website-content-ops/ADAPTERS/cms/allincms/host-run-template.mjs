/**
 * SAFE canonical AllinCMS host-run template (2026-08-27).
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
 */
import { tmpdir } from 'node:os';
import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';

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

export async function runAllinCmsHostPlanTemplate({
  plan, runtime, hooks, transport, evidencePath,
}) {
  const required = ['readbackProvider', 'fingerprintProvider', 'backendReadback', 'preflight', 'writeEvidence', 'readEvidenceArtifact'];
  for (const key of required) {
    if (!hooks || typeof hooks[key] !== 'function') throw new Error(`runAllinCmsHostPlanTemplate requires hook ${key} (implement real authoritative comparisons; never hardcode passed)`);
  }
  const { runAllinCmsContentPlan } = await import('./content-run-controller.mjs');
  const { createAllinCmsPlanHandlerSet } = await import('./content-plan-host-driver.mjs');
  const handlers = createAllinCmsPlanHandlerSet({ siteKey: plan.site_selector.site_key, siteId: plan.site_selector.site_id, runtime, request: transport.request, ...hooks });
  return runAllinCmsContentPlan({ plan, handlers, preflight: hooks.preflight, writeEvidence: hooks.writeEvidence, readEvidenceArtifact: hooks.readEvidenceArtifact, evidencePath });
}
