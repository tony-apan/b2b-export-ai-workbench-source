#!/usr/bin/env python3
"""Build a post-create browser evidence brief for created-site verification."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


REQUIRED_MODULES = (
    "dashboard",
    "products",
    "posts",
    "media",
    "themes",
    "routes",
    "forms",
    "site-info",
    "tracking",
    "domains",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output path must be outside the skill package")


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: {label} not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid {label}: {exc}") from None
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {label} root must be an object")
    return data


def site_proposal(handoff: dict[str, Any]) -> dict[str, str]:
    site = handoff.get("siteProposal") if isinstance(handoff.get("siteProposal"), dict) else {}
    return {
        "siteName": str(site.get("siteName", "")).strip(),
        "siteDescription": str(site.get("siteDescription", "")).strip(),
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    output = Path(args.output).expanduser().resolve()
    ensure_output_outside_skill(output)
    handoff = load_json(Path(args.create_site_handoff), "create-site handoff")
    if handoff.get("kind") != "allincms_confirmed_create_site_handoff":
        raise SystemExit("ERROR: create-site handoff kind must be allincms_confirmed_create_site_handoff")
    if handoff.get("isUserAuthorization") is not False:
        raise SystemExit("ERROR: create-site handoff must not be user authorization")
    preflight = handoff.get("preflight")
    if not isinstance(preflight, str) or not preflight:
        raise SystemExit("ERROR: create-site handoff must reference preflight")
    created_site_output = args.created_site_evidence_output or str(output.with_name("created-site-evidence.json"))
    module_route_template = ",".join(f"/<created-site-key>/{module}" for module in REQUIRED_MODULES)
    site = site_proposal(handoff)
    brief = {
        "kind": "allincms_created_site_evidence_brief",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "preparedOnly": True,
        "isUserAuthorization": False,
        "createSiteHandoff": args.create_site_handoff,
        "preflight": preflight,
        "createdSiteEvidenceOutput": created_site_output,
        "siteProposal": site,
        "target": "https://workspace.laicms.com/sites",
        "postSubmitBrowserTasks": [
            "after the gated create-site submit, identify the new site key that was not in existingSiteKeysBeforeCreate",
            "verify the new site card links to the backend dashboard",
            "open the backend dashboard for the created site",
            "open the public frontend base URL for the created site",
            "open or verify backend module routes for dashboard, products, posts, media, themes, routes, forms, site-info, tracking, and domains",
            "record setup-page evidence for site-info, domains, media, themes, routes, forms, and tracking",
            "inspect one content type list/edit surface, preferably products first, and record list columns plus edit fields",
            "stop before creating probes, saving content, publishing, uploading media, editing theme/routes/forms/settings, binding domains, or adding tracking",
        ],
        "requiredEvidence": {
            "createdSiteKey": "new lowercase site key absent from preflight existingSiteKeysBeforeCreate",
            "siteCardEvidence": "site card href or route containing the new site key",
            "backendEvidence": "backend dashboard URL https://workspace.laicms.com/<siteKey>/dashboard loaded",
            "frontendEvidence": "frontend URL https://<siteKey>.web.allincms.com loaded",
            "moduleRoutes": list(REQUIRED_MODULES),
            "setupPages": ["site-info", "domains", "media", "themes", "routes", "forms", "tracking"],
            "contentInspection": "content type plus list columns and edit fields observed read-only",
            "submittedFields": ["name", "description"],
            "submittedValues": {
                "name": site["siteName"],
                "description": site["siteDescription"],
            },
            "authorizationSource": "the current user instruction that authorized create_site for https://workspace.laicms.com/sites",
        },
        "makeCreatedSiteEvidenceCommandTemplate": (
            "python3 skills/allincms-bulk-content-upload/scripts/make_created_site_evidence.py "
            f"--preflight {preflight} "
            "--created-site-key <created-site-key> "
            "--content-type products "
            "--list-columns '<comma-separated-products-list-columns>' "
            "--edit-fields '<comma-separated-products-edit-fields>' "
            "--site-card-evidence '<site card href/route evidence>' "
            "--backend-evidence 'backend URL https://workspace.laicms.com/<created-site-key>/dashboard loaded' "
            "--frontend-evidence 'frontend URL https://<created-site-key>.web.allincms.com loaded' "
            "--site-info-evidence '<site-info controls visible>' "
            "--domains-evidence '<domains controls visible>' "
            "--media-evidence '<media controls visible>' "
            "--themes-evidence '<themes controls visible>' "
            "--routes-evidence '<routes controls visible>' "
            "--forms-evidence '<forms controls visible>' "
            "--tracking-evidence '<tracking controls visible>' "
            f"--module-routes '{module_route_template}' "
            "--submitted-fields name,description "
            f"--submitted-values '{{\"name\":\"{site['siteName']}\",\"description\":\"{site['siteDescription']}\"}}' "
            "--authorization-source '<current user create_site authorization text>' "
            f"--output {created_site_output}"
        ),
        "nextCommandAfterCreatedEvidence": (
            "python3 skills/allincms-bulk-content-upload/scripts/prepare_created_site_schema_capture.py "
            "--artifact-readiness <artifact-readiness.json> "
            f"--created-site-evidence {created_site_output} "
            "--package <source-site-package.json> "
            "--confirmation <confirmation-record.json> "
            "--execution-plan <confirmed-site-execution-plan.json> "
            f"--output-dir {Path(created_site_output).with_name('created-site-schema-capture')}"
        ),
        "forbiddenActions": [
            "do not create products/posts/media probes",
            "do not save, publish, upload, edit themes/routes/forms/settings, bind domains, or add tracking",
            "do not use this brief as proof that the site exists; only created_verified evidence can do that",
            "do not infer site key or module routes from memory",
        ],
        "nextAction": "after gated create-site submit, collect created-site evidence and run make_created_site_evidence.py",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return brief


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a post-create created-site evidence brief.")
    parser.add_argument("--create-site-handoff", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--created-site-evidence-output", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    brief = build(args)
    print(f"Wrote created-site evidence brief: {args.output}")
    print(f"createdSiteEvidenceOutput={brief['createdSiteEvidenceOutput']}")
    if args.json:
        print(json.dumps(brief, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
