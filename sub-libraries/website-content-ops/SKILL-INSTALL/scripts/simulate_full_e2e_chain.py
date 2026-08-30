#!/usr/bin/env python3
"""Run the full local-only AllinCMS create-site plus probe lifecycle simulation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import simulate_probe_lifecycle
import simulate_manifest_rehearsal
import simulate_site_creation_chain
from plan_module_capture import build_plan as build_module_capture_plan
from summarize_module_scan import module_items_from_object, summarize as summarize_module_scan
from summarize_module_scan import validate_redaction as validate_module_scan_redaction


MODULE_SCAN_TABLES = {
    "dashboard": [],
    "products": ["媒体", "名称", "Slug", "描述", "排序", "状态", "分类", "标签", "创建时间"],
    "posts": ["标题", "Slug", "摘要", "排序", "状态", "分类", "标签", "创建时间"],
    "media": ["文件", "类型", "大小", "创建时间"],
    "themes": ["主题", "状态", "页面", "操作"],
    "routes": ["路径", "绑定页面", "绑定状态", "备注", "更新时间"],
    "forms": ["名称", "Slug", "描述", "字段", "状态", "更新时间"],
    "site-info": [],
    "tracking": [],
    "domains": ["域名", "状态", "CNAME"],
}
MODULE_SCAN_BUTTONS = {
    "dashboard": [],
    "products": ["创建产品"],
    "posts": ["创建文章"],
    "media": ["上传"],
    "themes": ["创建主题"],
    "routes": ["创建", "绑定"],
    "forms": ["创建表单"],
    "site-info": ["保存"],
    "tracking": ["添加"],
    "domains": ["添加域名"],
}


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def simulated_module_scan(site_key: str, content_type: str) -> dict:
    modules = {}
    for module_name in simulate_site_creation_chain.MODULES:
        modules[module_name] = {
            "url": f"https://workspace.laicms.com/{site_key}/{module_name}",
            "headings": [module_name],
            "tableHeads": MODULE_SCAN_TABLES.get(module_name, []),
            "buttons": MODULE_SCAN_BUTTONS.get(module_name, []),
            "inputs": [],
        }
    return {
        "siteKey": site_key,
        "contentType": content_type,
        "modules": modules,
    }


def run_simulation(args: argparse.Namespace) -> dict[str, Path]:
    output_dir = Path(args.output_dir)
    site_dir = output_dir / "01-site-creation"
    probe_dir = output_dir / "02-probe-lifecycle"
    module_dir = output_dir / "03-module-interface-plan"
    manifest_dir = output_dir / "04-manifest-rehearsal"

    site_args = SimpleNamespace(
        no_existing_sites=args.no_existing_sites,
        existing_site_keys=args.existing_site_keys,
        site_key_evidence=args.site_key_evidence,
        empty_site_list_evidence=args.empty_site_list_evidence,
        simulated_created_site_key=args.simulated_created_site_key,
        content_type=args.content_type,
        observed_create_fields=args.observed_create_fields,
        list_columns=args.list_columns,
        edit_fields=args.edit_fields,
        include_simulated_static_launch=True,
        authorization_source=args.create_authorization_source,
        max_age_minutes=args.max_age_minutes,
        sedimentation=args.sedimentation,
        closeout_note=args.closeout_note,
        changed_files=args.changed_files,
        output_dir=str(site_dir),
    )
    site_paths = simulate_site_creation_chain.run_simulation(site_args)

    module_scan = simulated_module_scan(args.simulated_created_site_key, args.content_type)
    module_items = module_items_from_object(module_scan)
    module_errors = validate_module_scan_redaction(module_items)
    if module_errors:
        raise ValueError("module scan redaction failed:\n" + "\n".join(f"- {error}" for error in module_errors))
    module_summary = summarize_module_scan(module_items)
    module_capture_plan = build_module_capture_plan(module_summary, args.simulated_created_site_key, None)
    module_scan_path = module_dir / "module-scan.redacted.json"
    module_summary_path = module_dir / "module-scan-summary.json"
    module_capture_plan_path = module_dir / "module-capture-plan.json"
    write_json(module_scan_path, module_scan)
    write_json(module_summary_path, module_summary)
    write_json(module_capture_plan_path, module_capture_plan)

    probe_args = SimpleNamespace(
        base=str(site_paths["created"]),
        output_dir=str(probe_dir),
        simulated_content_id=args.simulated_content_id,
        simulated_slug=args.simulated_slug,
        require_created_site=True,
        max_age_minutes=args.max_age_minutes,
        sedimentation=args.sedimentation,
        closeout_note=args.closeout_note,
        changed_files=args.changed_files,
    )
    probe_paths = simulate_probe_lifecycle.run_simulation(probe_args)
    manifest_args = SimpleNamespace(
        site_key=args.simulated_created_site_key,
        content_type=args.content_type if args.content_type in {"posts", "products"} else "products",
        frontend_base_url="",
        output_dir=str(manifest_dir),
    )
    manifest_paths = simulate_manifest_rehearsal.run_rehearsal(manifest_args)

    site_summary = load_json(site_paths["summary"])
    probe_summary = load_json(probe_paths["summary"])
    manifest_summary = load_json(manifest_paths["summary"])
    full_summary = {
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "siteCreationDir": str(site_dir),
        "probeLifecycleDir": str(probe_dir),
        "moduleInterfaceDir": str(module_dir),
        "manifestRehearsalDir": str(manifest_dir),
        "siteSummary": {
            "valid": site_summary.get("valid"),
            "complete": site_summary.get("complete"),
            "proven": site_summary.get("proven", []),
            "completionGaps": site_summary.get("completionGaps", []),
        },
        "probeSummary": {
            "valid": probe_summary.get("valid"),
            "complete": probe_summary.get("complete"),
            "proven": probe_summary.get("proven", []),
            "missing": probe_summary.get("missing", []),
            "completionGaps": probe_summary.get("completionGaps", []),
        },
        "moduleInterface": {
            "jsonReplayReady": module_summary.get("jsonReplayReady"),
            "captureStageCount": len(module_capture_plan.get("stages", [])),
            "captureGroups": sorted({stage.get("group", "") for stage in module_capture_plan.get("stages", [])}),
        },
        "manifestRehearsal": {
            "contentType": manifest_summary.get("contentType"),
            "sourceInputRequirementsStatus": manifest_summary.get("sourceInputRequirements", {}).get("overallStatus"),
            "sourceInputRequirementsBlockedUntilCount": manifest_summary.get("sourceInputRequirements", {}).get("blockedUntilCount"),
            "draftValidationPassed": manifest_summary.get("draftValidation", {}).get("passed"),
            "schemaGateExpectedFailure": manifest_summary.get("schemaGate", {}).get("expectedFailure"),
            "schemaGateErrorCount": manifest_summary.get("schemaGate", {}).get("errorCount"),
        },
        "warning": "This is a local-only simulation. It proves helper compatibility and evidence-state modeling, not real LAICMS persistence.",
    }
    full_summary_path = output_dir / "full-e2e-summary.json"
    write_json(full_summary_path, full_summary)
    return {
        "siteCreatedEvidence": site_paths["created"],
        "probeCleanupEvidence": probe_paths["cleanupCompleted"],
        "moduleScan": module_scan_path,
        "moduleScanSummary": module_summary_path,
        "moduleCapturePlan": module_capture_plan_path,
        "draftManifest": manifest_paths["draftManifest"],
        "sourceInputRequirements": manifest_paths["sourceInputRequirements"],
        "manifestSummary": manifest_paths["summary"],
        "siteSummary": site_paths["summary"],
        "probeSummary": probe_paths["summary"],
        "fullSummary": full_summary_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full local-only AllinCMS E2E simulation.")
    site_keys = parser.add_mutually_exclusive_group(required=True)
    site_keys.add_argument("--existing-site-keys", help="Comma-separated site keys observed before create")
    site_keys.add_argument("--no-existing-sites", action="store_true")
    parser.add_argument("--site-key-evidence", default="")
    parser.add_argument("--empty-site-list-evidence", default="verified empty /sites list")
    parser.add_argument("--simulated-created-site-key", default="simsite01")
    parser.add_argument("--content-type", choices=["posts", "products", "forms"], default="products")
    parser.add_argument("--observed-create-fields", default=simulate_site_creation_chain.DEFAULT_OBSERVED_CREATE_FIELDS)
    parser.add_argument("--list-columns", default=simulate_site_creation_chain.DEFAULT_LIST_COLUMNS)
    parser.add_argument("--edit-fields", default=simulate_site_creation_chain.DEFAULT_EDIT_FIELDS)
    parser.add_argument(
        "--create-authorization-source",
        default="current user explicitly authorizes create site at https://workspace.laicms.com/sites for local simulation only",
    )
    parser.add_argument("--simulated-content-id", default="codex-probe-id")
    parser.add_argument("--simulated-slug", default="codex-probe-delete-me")
    parser.add_argument("--max-age-minutes", type=int, default=30)
    parser.add_argument("--sedimentation", choices=["updated", "none"], default="none")
    parser.add_argument("--closeout-note", default="no reusable skill update needed after checking")
    parser.add_argument("--changed-files", default="")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    try:
        paths = run_simulation(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for label, path in paths.items():
        print(f"{label}: {path}")
    print("Full local-only AllinCMS E2E simulation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
