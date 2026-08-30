#!/usr/bin/env python3
"""Where is THIS site in the build pipeline, and what's the next step + which gate is still owed.

Stitches the workspace layout (a site folder under clients/<c>/sites/<s>/) to the existing
source→package→build chain and the three quality gates (run-mode, content-quality, residue) into one
readable, resumable line. It does NOT run the build (that's the authorized browser stage) — it reads
the site folder's artifacts and reports progress, so an AI can resume a client's multiple sites
without losing the thread, and the workspace README's status column has a source of truth.

Pipeline stages (in order):
  build_source_wiki    -> site's source-wiki/ has content (distilled from the client wiki, this site's subset)
  build_package        -> site's package/ has the confirmed content package
  content_quality_gate -> run/content-quality-report.json has pass=true (check_content_quality)
  resolve_run_mode     -> run/run-mode.json has a mode (resolve_run_mode; existing site must ask the user)
  build_site_live      -> run/site-live.json has a siteKey (authorized browser build done + verified)
  residue_gate         -> run/residue-report.json pass=true, OR skipped for a confirmed incremental_update
  launch_acceptance    -> run/launch-acceptance.json has pass=true

Convention: each stage writes its artifact/report into the site's run/ folder (pass --output there),
so this helper reads明确 JSON markers, never guesses.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from _common import now_iso

KIND = "allincms_site_build_status"
STAGE_ORDER = [
    "build_source_wiki", "build_package", "content_quality_gate",
    "resolve_run_mode", "build_site_live", "residue_gate", "launch_acceptance",
]
HINTS = {
    "build_source_wiki": "distill the client wiki into this site's source-wiki/ (build_source_wiki.py), scoped to this site's product subset",
    "build_package": "build + validate the confirmed content package into package/ (build_source_site_package.py, then user confirmation)",
    "content_quality_gate": "check_content_quality.py --package <package> --output run/content-quality-report.json (clear all blockers)",
    "resolve_run_mode": "resolve_run_mode.py --site-creation-status <created_verified|existing_site_selected> --output run/run-mode.json; if it's an EXISTING site, ASK the user (conversion vs daily) before proceeding",
    "build_site_live": "authorized browser build: create/select site, upload, publish, verify backend+frontend; record the siteKey into run/site-live.json",
    "residue_gate": "check_template_residue.py --blacklist residue-blacklist.json --frontend <every-route-text> --output run/residue-report.json (from_scratch/template_conversion only)",
    "launch_acceptance": "run launch acceptance (validate_launch_acceptance) and write run/launch-acceptance.json",
}


def _dir_nonempty(path: Path) -> bool:
    return path.is_dir() and any(path.iterdir())


def _report(site_dir: Path, name: str) -> dict | None:
    f = site_dir / "run" / name
    if not f.exists():
        return None
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def site_build_status(site_dir: str) -> dict:
    sdir = Path(site_dir).expanduser()
    if not sdir.is_dir():
        raise SystemExit(f"ERROR: site directory not found: {sdir}")

    run_mode = _report(sdir, "run-mode.json") or {}
    mode = run_mode.get("mode")
    cq = _report(sdir, "content-quality-report.json") or {}
    live = _report(sdir, "site-live.json") or {}
    residue = _report(sdir, "residue-report.json") or {}
    launch = _report(sdir, "launch-acceptance.json") or {}

    done: set[str] = set()
    if _dir_nonempty(sdir / "source-wiki"):
        done.add("build_source_wiki")
    if _dir_nonempty(sdir / "package"):
        done.add("build_package")
    if cq.get("pass") is True:
        done.add("content_quality_gate")
    if mode:
        done.add("resolve_run_mode")
    if live.get("siteKey"):
        done.add("build_site_live")
    # residue gate: done when it passed, OR auto-skipped ONLY for an explicit incremental_update
    # (mirrors resolve_run_mode's safe default — any other/unknown/corrupt mode keeps the gate
    # required); meaningful only after the site is actually live
    if "build_site_live" in done:
        if mode == "incremental_update" or residue.get("pass") is True:
            done.add("residue_gate")
    if launch.get("pass") is True:
        done.add("launch_acceptance")

    pending = [s for s in STAGE_ORDER if s not in done]
    next_stage = pending[0] if pending else None
    gates_pending = [g for g in ("content_quality_gate", "residue_gate") if g not in done and g in pending]

    return {
        "kind": KIND,
        "generatedAt": now_iso(),
        "siteDir": str(sdir),
        "mode": mode,
        "needsUserConfirmation": run_mode.get("needsUserConfirmation") if next_stage == "build_site_live" else None,
        "done": [s for s in STAGE_ORDER if s in done],
        "nextStage": next_stage,
        "nextHint": HINTS.get(next_stage) if next_stage else "site build complete — all stages done",
        "gatesPending": gates_pending,
        "launched": next_stage is None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Report a workspace site's build-pipeline progress and next step.")
    parser.add_argument("--site-dir", required=True, help="Path to a workspace site folder (clients/<c>/sites/<s>)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    status = site_build_status(args.site_dir)
    print(f"site: {status['siteDir']}")
    print(f"done: {', '.join(status['done']) or '(nothing yet)'}")
    if status["launched"]:
        print("→ build complete — all pipeline stages done.")
    else:
        print(f"→ next: {status['nextStage']}")
        print(f"   {status['nextHint']}")
    if status["gatesPending"]:
        print(f"gates still owed: {', '.join(status['gatesPending'])}")
    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
