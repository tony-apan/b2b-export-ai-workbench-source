#!/usr/bin/env python3
"""Export an allincms_source_wiki JSON into readable local Markdown wiki files."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from validate_source_wiki import load_json, validate_source_wiki


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_output_dir_outside_skill(path: Path) -> None:
    resolved = path.resolve()
    root = skill_root().resolve()
    if resolved == root or root in resolved.parents:
        raise SystemExit("ERROR: output directory must be outside the skill package")


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def yaml_value(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def frontmatter(doc_id: str, title: str, description: str) -> str:
    today = datetime.now(timezone.utc).date().isoformat()
    return (
        "---\n"
        f"doc_id: {doc_id}\n"
        f"title: {yaml_value(title)}\n"
        f"description: {yaml_value(description)}\n"
        "layer: content\n"
        "status: draft\n"
        f"created: {today}\n"
        f"updated: {today}\n"
        "source: allincms_source_wiki\n"
        "---\n\n"
    )


def bullet_list(items: list[str]) -> str:
    if not items:
        return "- None recorded.\n"
    return "".join(f"- {item}\n" for item in items)


def source_refs(item: dict[str, Any]) -> str:
    refs = [ref for ref in as_list(item.get("sourceRefs")) if isinstance(ref, str) and ref.strip()]
    return ", ".join(refs) if refs else "missing"


def block_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        parts: list[str] = []
        for key in ("heading", "title", "body", "text", "description", "excerpt"):
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                parts.append(item.strip())
        return " ".join(parts)
    if isinstance(value, list):
        return "\n\n".join(item for item in (block_text(entry) for entry in value) if item)
    return ""


def write(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return str(path)


def build_index(wiki: dict[str, Any], files: dict[str, str]) -> str:
    site = wiki.get("site") if isinstance(wiki.get("site"), dict) else {}
    site_name = text(site.get("siteName")) or "AllinCMS Source Wiki"
    lines = [
        frontmatter("allincms-source-wiki-index", f"{site_name} Wiki Index", "Readable source-backed wiki index for an AllinCMS site package."),
        f"# {site_name} Wiki Index\n",
        "## Files\n",
    ]
    for label, path in files.items():
        lines.append(f"- {label}: `{Path(path).name}`\n")
    lines.extend(
        [
            "\n## Review Rules\n",
            "- This wiki is local-only source distillation, not AllinCMS mutation authorization.\n",
            "- Use source refs to trace claims back to the inventory and raw extraction artifacts.\n",
            "- Resolve open questions before package confirmation or record an explicit user deferral.\n",
        ]
    )
    return "".join(lines)


def build_site_page(wiki: dict[str, Any]) -> str:
    site = wiki.get("site") if isinstance(wiki.get("site"), dict) else {}
    site_info = wiki.get("siteInfo") if isinstance(wiki.get("siteInfo"), dict) else {}
    navigation = wiki.get("navigation") if isinstance(wiki.get("navigation"), dict) else {}
    taxonomy = wiki.get("taxonomyPlan") if isinstance(wiki.get("taxonomyPlan"), dict) else {}
    open_questions = [item for item in as_list(wiki.get("openQuestions")) if isinstance(item, str) and item.strip()]
    lines = [
        frontmatter("allincms-source-wiki-site", "Site And Launch Inputs", "Site proposal, SEO, navigation, taxonomy, and unresolved launch inputs."),
        "# Site And Launch Inputs\n\n",
        "## Site Proposal\n",
        f"- Name: {text(site.get('siteName')) or 'missing'}\n",
        f"- Description: {text(site.get('siteDescription')) or text(site.get('description')) or 'missing'}\n",
        f"- Language: {text(site.get('language')) or 'missing'}\n",
        f"- Industry: {text(site.get('industry')) or 'missing'}\n",
        "\n## Site Info\n",
        f"- SEO title: {text(site_info.get('draftSeoTitle')) or 'missing'}\n",
        f"- SEO description: {text(site_info.get('draftSeoDescription')) or 'missing'}\n",
        f"- Public contact: {site_info.get('publicContact', 'requires_user_confirmation')}\n",
        f"- Legal company name: {site_info.get('legalCompanyName', 'requires_user_confirmation')}\n",
        "\n## Navigation\n",
    ]
    nav_items = []
    for item in as_list(navigation.get("items")):
        if isinstance(item, dict):
            nav_items.append(f"{text(item.get('label')) or 'Untitled'} -> {text(item.get('path')) or 'missing'}")
    lines.append(bullet_list(nav_items))
    lines.append("\n## Taxonomy\n")
    taxonomy_lines = []
    for key in ("productCategories", "postCategories", "productTags", "postTags"):
        values = []
        for item in as_list(taxonomy.get(key)):
            if isinstance(item, dict):
                values.append(text(item.get("label")) or text(item.get("slug")) or "Untitled")
            elif isinstance(item, str):
                values.append(item)
        taxonomy_lines.append(f"{key}: {', '.join(values) if values else 'none'}")
    lines.append(bullet_list(taxonomy_lines))
    lines.append("\n## Open Questions\n")
    lines.append(bullet_list(open_questions))
    return "".join(lines)


def build_pages_page(wiki: dict[str, Any]) -> str:
    lines = [
        frontmatter("allincms-source-wiki-pages", "Pages Plan", "Single-page and homepage content plan derived from source files."),
        "# Pages Plan\n\n",
    ]
    for item in as_list(wiki.get("pages")):
        if not isinstance(item, dict):
            continue
        title = text(item.get("title")) or "Untitled Page"
        lines.append(f"## {title}\n")
        lines.append(f"- Path: {text(item.get('path')) or 'missing'}\n")
        lines.append(f"- Purpose: {text(item.get('purpose')) or 'content_page'}\n")
        lines.append(f"- Source refs: {source_refs(item)}\n\n")
        for section in as_list(item.get("sections")):
            heading = text(section.get("heading")) if isinstance(section, dict) else ""
            body = block_text(section)
            if heading:
                lines.append(f"### {heading}\n")
            if body:
                lines.append(body + "\n\n")
    return "".join(lines)


def build_products_page(wiki: dict[str, Any]) -> str:
    lines = [
        frontmatter("allincms-source-wiki-products", "Products Plan", "Product content candidates and source-backed fields for AllinCMS upload planning."),
        "# Products Plan\n\n",
    ]
    for item in as_list(wiki.get("products")):
        if not isinstance(item, dict):
            continue
        name = text(item.get("name")) or text(item.get("title")) or "Untitled Product"
        lines.append(f"## {name}\n")
        lines.append(f"- Slug: {text(item.get('slug')) or 'missing'}\n")
        lines.append(f"- Description: {text(item.get('description')) or 'missing'}\n")
        lines.append(f"- Categories: {', '.join(str(x) for x in as_list(item.get('categories'))) or 'none'}\n")
        lines.append(f"- Tags: {', '.join(str(x) for x in as_list(item.get('tags'))) or 'none'}\n")
        lines.append(f"- Source refs: {source_refs(item)}\n\n")
        body = block_text(item.get("content"))
        if body:
            lines.append(body + "\n\n")
        specs = as_list(item.get("specs"))
        if specs:
            lines.append("### Specs\n")
            for spec in specs:
                if isinstance(spec, dict):
                    key = text(spec.get("name")) or text(spec.get("key")) or "Spec"
                    value = text(spec.get("value")) or json.dumps(spec, ensure_ascii=False)
                    lines.append(f"- {key}: {value}\n")
                else:
                    lines.append(f"- {spec}\n")
            lines.append("\n")
    return "".join(lines)


def build_posts_page(wiki: dict[str, Any]) -> str:
    lines = [
        frontmatter("allincms-source-wiki-posts", "Posts Plan", "Article content candidates and source-backed fields for AllinCMS upload planning."),
        "# Posts Plan\n\n",
    ]
    for item in as_list(wiki.get("posts")):
        if not isinstance(item, dict):
            continue
        title = text(item.get("title")) or "Untitled Post"
        lines.append(f"## {title}\n")
        lines.append(f"- Slug: {text(item.get('slug')) or 'missing'}\n")
        lines.append(f"- Excerpt: {text(item.get('excerpt')) or 'missing'}\n")
        lines.append(f"- Categories: {', '.join(str(x) for x in as_list(item.get('categories'))) or 'none'}\n")
        lines.append(f"- Tags: {', '.join(str(x) for x in as_list(item.get('tags'))) or 'none'}\n")
        lines.append(f"- Source refs: {source_refs(item)}\n\n")
        body = block_text(item.get("content"))
        if body:
            lines.append(body + "\n\n")
    return "".join(lines)


def build(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    ensure_output_dir_outside_skill(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    wiki = load_json(Path(args.source_wiki), "source wiki")
    inventory = load_json(Path(args.inventory), "source inventory") if args.inventory else None
    issues = validate_source_wiki(wiki, inventory)
    if issues and args.fail_on_invalid:
        raise SystemExit("ERROR: source wiki is invalid:\n- " + "\n- ".join(issues))

    paths = {
        "site": write(output_dir / "site.md", build_site_page(wiki)),
        "pages": write(output_dir / "pages.md", build_pages_page(wiki)),
        "products": write(output_dir / "products.md", build_products_page(wiki)),
        "posts": write(output_dir / "posts.md", build_posts_page(wiki)),
    }
    paths["index"] = write(output_dir / "index.md", build_index(wiki, paths))
    manifest = {
        "kind": "allincms_source_wiki_markdown_export",
        "generatedAt": now_iso(),
        "localOnly": True,
        "remoteMutationsPerformed": False,
        "sourceWiki": args.source_wiki,
        "validSourceWiki": not issues,
        "files": paths,
        "issues": issues,
        "rule": "Markdown wiki files are review artifacts only; they do not authorize AllinCMS remote mutation.",
    }
    write(output_dir / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Export allincms_source_wiki JSON into readable Markdown wiki files.")
    parser.add_argument("--source-wiki", required=True)
    parser.add_argument("--inventory", default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--fail-on-invalid", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    manifest = build(args)
    print(f"Wrote source wiki markdown export: {manifest['files']['index']}")
    print(f"validSourceWiki={str(manifest['validSourceWiki']).lower()} files={len(manifest['files'])}")
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    if args.fail_on_invalid and not manifest["validSourceWiki"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
