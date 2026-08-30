#!/usr/bin/env python3
"""Validate a refined source wiki against its refinement brief contract."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from validate_source_wiki import load_json, validate_source_wiki, walk_strings


PLACEHOLDER_TERMS = (
    "Draft Product",
    "Draft Article",
    "requires source extraction",
    "requires review",
    "TODO",
)


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def parse_time(value: Any, label: str, issues: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        issues.append(f"{label} is required")
        return
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        issues.append(f"{label} must be an ISO 8601 timestamp")


def source_refs(wiki: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    source_set = as_dict(wiki.get("sourceSet"))
    for item in as_list(source_set.get("inputFiles")):
        if isinstance(item, dict) and isinstance(item.get("sourceRef"), str) and item["sourceRef"].strip():
            refs.add(item["sourceRef"].strip())
    return refs


def item_refs(wiki: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for key in ("pages", "products", "posts"):
        for item in as_list(wiki.get(key)):
            if isinstance(item, dict):
                for ref in as_list(item.get("sourceRefs")):
                    if isinstance(ref, str) and ref.strip():
                        refs.add(ref.strip())
    return refs


def hydrate_source_fingerprints(wiki: dict[str, Any], inventory: dict[str, Any] | None) -> tuple[dict[str, Any], bool]:
    if not inventory:
        return wiki, False
    entries = inventory.get("entries")
    if not isinstance(entries, list):
        return wiki, False
    by_ref = {
        entry.get("sourceRef"): entry
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("sourceRef"), str)
    }
    source_set = as_dict(wiki.get("sourceSet"))
    input_files = source_set.get("inputFiles")
    if not isinstance(input_files, list):
        return wiki, False
    hydrated_files: list[Any] = []
    changed = False
    for item in input_files:
        if not isinstance(item, dict):
            hydrated_files.append(item)
            continue
        entry = by_ref.get(item.get("sourceRef"))
        if not isinstance(entry, dict):
            hydrated_files.append(item)
            continue
        hydrated = dict(item)
        for key in ("path", "name", "type", "sizeBytes", "sha256"):
            if hydrated.get(key) in (None, "") and entry.get(key) not in (None, ""):
                hydrated[key] = entry[key]
                changed = True
        hydrated_files.append(hydrated)
    if not changed:
        return wiki, False
    result = dict(wiki)
    result["sourceSet"] = dict(source_set)
    result["sourceSet"]["inputFiles"] = hydrated_files
    return result, True


def validate_contract(
    *,
    refined_wiki: dict[str, Any],
    brief: dict[str, Any],
    refined_wiki_path: str,
    inventory: dict[str, Any] | None = None,
) -> list[str]:
    issues: list[str] = []
    refined_wiki, _ = hydrate_source_fingerprints(refined_wiki, inventory)
    if brief.get("kind") != "allincms_source_wiki_refinement_brief":
        issues.append("brief kind must be allincms_source_wiki_refinement_brief")
    parse_time(brief.get("generatedAt"), "brief.generatedAt", issues)
    for key, expected in (
        ("localOnly", True),
        ("remoteMutationsPerformed", False),
        ("preparedOnly", True),
        ("isUserAuthorization", False),
    ):
        if brief.get(key) is not expected:
            issues.append(f"brief.{key} must be {str(expected).lower()}")

    expected_output = brief.get("outputRefinedSourceWiki")
    if isinstance(expected_output, str) and expected_output.strip():
        if Path(expected_output).expanduser().resolve() != Path(refined_wiki_path).expanduser().resolve():
            issues.append("refined source wiki path must match brief.outputRefinedSourceWiki")
    else:
        issues.append("brief.outputRefinedSourceWiki is required")

    wiki_issues = validate_source_wiki(refined_wiki, inventory)
    issues.extend(f"source wiki validation: {issue}" for issue in wiki_issues)
    for key, expected in (
        ("localOnly", True),
        ("remoteMutationsPerformed", False),
    ):
        if refined_wiki.get(key) is not expected:
            issues.append(f"refined wiki {key} must be {str(expected).lower()}")

    original_refs = set(ref for ref in as_list(brief.get("sourceRefs")) if isinstance(ref, str) and ref.strip())
    refined_refs = source_refs(refined_wiki)
    if original_refs and not original_refs.issubset(refined_refs):
        issues.append("refined wiki must preserve brief sourceRefs: " + ", ".join(sorted(original_refs - refined_refs)))
    used_refs = item_refs(refined_wiki)
    if original_refs and not used_refs:
        issues.append("refined wiki pages/products/posts must use sourceRefs")
    if original_refs and not used_refs.issubset(refined_refs):
        issues.append("refined wiki content uses sourceRefs not listed in sourceSet.inputFiles: " + ", ".join(sorted(used_refs - refined_refs)))

    all_text = "\n".join(walk_strings(refined_wiki))
    for term in PLACEHOLDER_TERMS:
        if term.lower() in all_text.lower():
            issues.append(f"refined wiki still contains placeholder/review term: {term}")
            break

    required_edits = as_list(brief.get("requiredEdits"))
    if required_edits and len(as_list(refined_wiki.get("products"))) == 0:
        issues.append("refined wiki must keep product candidates when refinement plan had blockers")
    if required_edits and len(as_list(refined_wiki.get("posts"))) == 0:
        issues.append("refined wiki must keep post candidates when refinement plan had blockers")
    if not as_dict(refined_wiki.get("mediaPolicy")):
        issues.append("refined wiki must include mediaPolicy")
    if not as_dict(refined_wiki.get("contactFormPolicy")):
        issues.append("refined wiki must include contactFormPolicy")
    if not as_dict(refined_wiki.get("taxonomyPlan")):
        issues.append("refined wiki must include taxonomyPlan")
    if not as_dict(refined_wiki.get("navigation")):
        issues.append("refined wiki must include navigation")
    return issues


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    refined_path = Path(args.refined_source_wiki).expanduser().resolve()
    brief_path = Path(args.refinement_brief).expanduser().resolve()
    inventory = load_json(Path(args.inventory).expanduser().resolve(), "source inventory") if args.inventory else None
    refined_wiki = load_json(refined_path, "refined source wiki")
    _, hydrated = hydrate_source_fingerprints(refined_wiki, inventory)
    brief = load_json(brief_path, "source wiki refinement brief")
    issues = validate_contract(
        refined_wiki=refined_wiki,
        brief=brief,
        refined_wiki_path=str(refined_path),
        inventory=inventory,
    )
    return {
        "kind": "allincms_refined_source_wiki_contract_validation",
        "refinedSourceWiki": str(refined_path),
        "refinementBrief": str(brief_path),
        "inventory": str(Path(args.inventory).expanduser().resolve()) if args.inventory else "",
        "sourceFingerprintsHydrated": hydrated,
        "ok": not issues,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a refined source wiki against a refinement brief.")
    parser.add_argument("--refined-source-wiki", required=True)
    parser.add_argument("--refinement-brief", required=True)
    parser.add_argument("--inventory", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_report(args)
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif report["ok"]:
        print("Refined source wiki contract validation passed.")
    else:
        for issue in report["issues"]:
            print(f"- {issue}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
