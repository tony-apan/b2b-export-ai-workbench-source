#!/usr/bin/env python3
"""Create an action-specific authorization record for AllinCMS mutations."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


SITE_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,62}[a-z0-9]$")
WORKSPACE_ORIGIN = "https://workspace.laicms.com"
MUTATING_ACTIONS = {
    "create_site",
    "create_draft",
    "create_post_probe",
    "create_product_probe",
    "create_form_probe",
    "save_probe",
    "publish_probe",
    "cleanup_probe",
    "save_product",
    "publish_product",
    "save_post",
    "publish_post",
    "publish",
    "unpublish",
    "upload_media",
    "delete_or_cleanup",
    "batch_upload",
    "batch_publish",
    "save_site_settings",
    "save_design",
    "publish_design",
    "create_theme_page",
    "set_homepage",
    "enable_theme_page",
    "bind_route",
    "create_route",
    "create_theme",
    "activate_theme",
    "create_form",
    "add_domain",
    "add_tracking_tag",
    "create_or_map_products_category",
    "create_or_map_products_tag",
    "create_or_map_posts_category",
    "create_or_map_posts_tag",
}
FUZZY_AUTH_TERMS = (
    "continue",
    "go ahead",
    "proceed",
    "ok",
    "yes",
    "\u7ee7\u7eed",
    "\u53ef\u4ee5",
    "\u597d\u7684",
    "\u884c",
    "\u9010\u4e2a\u9a8c\u8bc1",
)
SESSION_CONTINUATION_AUTH_TERMS = (
    "\u540e\u7eed\u9700\u8981\u64cd\u4f5c\u7684",
    "\u76f4\u63a5\u8fdb\u884c",
    "\u65e0\u9700\u6211\u6388\u6743",
)
SESSION_CONTINUATION_RESULT_TERMS = (
    "\u6700\u7ec8\u7ed9\u6211\u7ed3\u679c",
    "\u6700\u7ec8\u4f60\u7ed9\u6211\u7ed3\u679c",
)
PROBE_ACTION_REQUIREMENTS = {
    "create_post_probe": (
        ("post", "posts", "article", "articles", "\u6587\u7ae0"),
        "post/article",
    ),
    "create_product_probe": (
        ("product", "products", "\u4ea7\u54c1"),
        "product",
    ),
    "create_form_probe": (
        ("form", "forms", "\u8868\u5355"),
        "form",
    ),
    "save_probe": (
        ("post", "posts", "article", "articles", "product", "products", "form", "forms", "\u6587\u7ae0", "\u4ea7\u54c1", "\u8868\u5355"),
        "content type",
    ),
    "publish_probe": (
        ("post", "posts", "article", "articles", "product", "products", "\u6587\u7ae0", "\u4ea7\u54c1"),
        "publishable content type",
    ),
    "cleanup_probe": (
        ("post", "posts", "article", "articles", "product", "products", "form", "forms", "\u6587\u7ae0", "\u4ea7\u54c1", "\u8868\u5355"),
        "content type",
    ),
}
PROBE_INTENT_TERMS = ("probe", "draft", "test", "\u63a2\u9488", "\u63a2\u6d4b", "\u6d4b\u8bd5", "\u8349\u7a3f")
SAVE_INTENT_TERMS = ("capture", "request", "persist", "\u6355\u83b7", "\u8bf7\u6c42", "\u6301\u4e45")
PUBLISH_INTENT_TERMS = ("publish", "public", "\u53d1\u5e03", "\u4e0a\u7ebf", "\u516c\u5f00")
CLEANUP_INTENT_TERMS = ("cleanup", "clean", "delete", "unpublish", "\u6e05\u7406", "\u5220\u9664", "\u53d6\u6d88\u53d1\u5e03")
EXISTING_SAVE_INTENT_TERMS = ("save", "update", "persist", "\u4fdd\u5b58", "\u66f4\u65b0", "\u6301\u4e45")
EXISTING_CONTENT_ACTION_REQUIREMENTS = {
    "save_product": (("product", "products", "\u4ea7\u54c1"), "product", EXISTING_SAVE_INTENT_TERMS),
    "publish_product": (("product", "products", "\u4ea7\u54c1"), "product", PUBLISH_INTENT_TERMS),
    "save_post": (("post", "posts", "article", "articles", "\u6587\u7ae0"), "post/article", EXISTING_SAVE_INTENT_TERMS),
    "publish_post": (("post", "posts", "article", "articles", "\u6587\u7ae0"), "post/article", PUBLISH_INTENT_TERMS),
}
ACTION_TERMS = {
    "create_site": ("create", "\u521b\u5efa"),
    "create_draft": ("create", "\u521b\u5efa"),
    "create_post_probe": ("create", "\u521b\u5efa"),
    "create_product_probe": ("create", "\u521b\u5efa"),
    "create_form_probe": ("create", "\u521b\u5efa"),
    "save_probe": ("save", "\u4fdd\u5b58"),
    "publish_probe": ("publish", "\u53d1\u5e03", "\u4e0a\u7ebf"),
    "cleanup_probe": ("cleanup", "clean", "delete", "unpublish", "\u6e05\u7406", "\u5220\u9664", "\u53d6\u6d88\u53d1\u5e03"),
    "save_product": ("save", "update", "\u4fdd\u5b58", "\u66f4\u65b0"),
    "publish_product": ("publish", "\u53d1\u5e03", "\u4e0a\u7ebf"),
    "save_post": ("save", "update", "\u4fdd\u5b58", "\u66f4\u65b0"),
    "publish_post": ("publish", "\u53d1\u5e03", "\u4e0a\u7ebf"),
    "publish": ("publish", "\u53d1\u5e03", "\u4e0a\u7ebf"),
    "unpublish": ("unpublish", "\u53d6\u6d88\u53d1\u5e03"),
    "upload_media": ("upload", "\u4e0a\u4f20"),
    "delete_or_cleanup": ("delete", "cleanup", "\u5220\u9664", "\u6e05\u7406"),
    "batch_upload": ("upload", "\u4e0a\u4f20"),
    "batch_publish": ("publish", "\u53d1\u5e03", "\u4e0a\u7ebf"),
    "save_site_settings": ("save", "\u4fdd\u5b58"),
    "save_design": ("save", "\u4fdd\u5b58"),
    "publish_design": ("publish", "\u53d1\u5e03", "\u4e0a\u7ebf"),
    "create_theme_page": ("create", "\u521b\u5efa"),
    "set_homepage": ("set", "\u8bbe\u4e3a", "\u8bbe\u7f6e"),
    "enable_theme_page": ("enable", "\u542f\u7528"),
    "bind_route": ("bind", "\u7ed1\u5b9a"),
    "create_route": ("create", "\u521b\u5efa"),
    "create_theme": ("create", "\u521b\u5efa"),
    "activate_theme": ("activate", "apply", "enable", "\u542f\u7528", "\u5e94\u7528"),
    "create_form": ("create", "\u521b\u5efa"),
    "add_domain": ("add", "\u6dfb\u52a0"),
    "add_tracking_tag": ("add", "\u6dfb\u52a0"),
    "create_or_map_products_category": ("create", "map", "\u521b\u5efa", "\u6620\u5c04"),
    "create_or_map_products_tag": ("create", "map", "\u521b\u5efa", "\u6620\u5c04"),
    "create_or_map_posts_category": ("create", "map", "\u521b\u5efa", "\u6620\u5c04"),
    "create_or_map_posts_tag": ("create", "map", "\u521b\u5efa", "\u6620\u5c04"),
}


def require_text(value: str, label: str) -> str:
    if not value.strip():
        raise ValueError(f"{label} is required")
    return value.strip()


def validate_site_key(value: str) -> str:
    value = value.strip()
    if value and not SITE_KEY_RE.fullmatch(value):
        raise ValueError("site key must be lowercase letters, digits, or hyphens")
    return value


def validate_target(action: str, target: str, site_key: str) -> str:
    target = require_text(target, "target")
    parsed = urlparse(target)
    if parsed.scheme and parsed.netloc:
        if parsed.scheme != "https" or parsed.netloc != "workspace.laicms.com":
            raise ValueError("target must be under https://workspace.laicms.com")
        path = parsed.path
    else:
        path = target

    if action == "create_site":
        if path.rstrip("/") != "/sites":
            raise ValueError("create_site target must be https://workspace.laicms.com/sites")
        return target

    if not site_key:
        raise ValueError("site key is required for this action")
    if not path.startswith(f"/{site_key}/"):
        raise ValueError("target path must belong to the provided site key")
    return target


RUN_SCOPED_SOURCE_PREFIX = "run_scoped_authorization:"


def validate_authorization_source(action: str, source: str, target: str) -> str:
    source = require_text(source, "authorization source")
    lowered = source.lower()
    # Run-scoped authorization: a per-action authorization derived from a single user run-scoped
    # grant (see run_authorization.py). It is accepted here for the same in-scope content-build
    # actions, still bound to the exact target, but without the human-typed content requirements
    # below — the run-scoped grant already carried the user's intent and the package binding.
    # Carve-out actions never receive a run-scoped source (run_authorization refuses to emit one),
    # so this branch cannot broaden authorization beyond the allowlisted content build.
    if lowered.startswith(RUN_SCOPED_SOURCE_PREFIX):
        from run_authorization import COVERED_ACTIONS  # lazy import to avoid a load-time cycle
        if action not in COVERED_ACTIONS:
            raise ValueError(
                "run-scoped authorization source is only valid for allowlisted content-build actions, "
                f"not the carve-out {action!r}; get an explicit per-action authorization"
            )
        if target not in source:
            raise ValueError("run-scoped authorization source must still name the exact target")
        return source
    if lowered.strip() in FUZZY_AUTH_TERMS or any(term == lowered.strip() for term in FUZZY_AUTH_TERMS):
        raise ValueError("authorization source is too generic; it must name the exact action and target")
    has_session_continuation = (
        all(term in source for term in SESSION_CONTINUATION_AUTH_TERMS)
        and any(term in source for term in SESSION_CONTINUATION_RESULT_TERMS)
    )
    action_terms = ACTION_TERMS.get(action, (action.replace("_", " ").split()[0],))
    if not has_session_continuation and not any(term in lowered or term in source for term in action_terms):
        raise ValueError("authorization source must mention the action")
    if action == "create_site":
        if "site" not in lowered and "\u7ad9\u70b9" not in source:
            raise ValueError("create_site authorization source must mention site creation")
        if "/sites" not in source and "workspace.laicms.com/sites" not in source:
            raise ValueError("create_site authorization source must mention /sites")
    elif target not in source:
        raise ValueError("authorization source must mention the exact target")
    if action in PROBE_ACTION_REQUIREMENTS:
        type_terms, type_label = PROBE_ACTION_REQUIREMENTS[action]
        source_without_target = source.replace(target, "")
        lowered_without_target = source_without_target.lower()
        if not any(term in lowered_without_target or term in source_without_target for term in type_terms):
            raise ValueError(f"{action} authorization source must mention {type_label}")
        if not has_session_continuation and not any(term in lowered or term in source for term in PROBE_INTENT_TERMS):
            raise ValueError(f"{action} authorization source must mention probe or draft intent")
        if action == "save_probe" and not has_session_continuation and not any(term in lowered or term in source for term in SAVE_INTENT_TERMS):
            raise ValueError("save_probe authorization source must mention save/capture intent")
        if action == "publish_probe" and not has_session_continuation and not any(term in lowered or term in source for term in PUBLISH_INTENT_TERMS):
            raise ValueError("publish_probe authorization source must mention publish intent")
        if action == "cleanup_probe" and not has_session_continuation and not any(term in lowered or term in source for term in CLEANUP_INTENT_TERMS):
            raise ValueError("cleanup_probe authorization source must mention cleanup/delete/unpublish intent")
    if action in EXISTING_CONTENT_ACTION_REQUIREMENTS:
        type_terms, type_label, intent_terms = EXISTING_CONTENT_ACTION_REQUIREMENTS[action]
        source_without_target = source.replace(target, "")
        lowered_without_target = source_without_target.lower()
        if not any(term in lowered_without_target or term in source_without_target for term in type_terms):
            raise ValueError(f"{action} authorization source must mention {type_label}")
        if not has_session_continuation and not any(term in lowered or term in source for term in intent_terms):
            raise ValueError(f"{action} authorization source must mention save/update or publish intent")
    return source


def split_values(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def validate_record(record: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["authorization record must be a JSON object"]
    if record.get("workspace") != WORKSPACE_ORIGIN:
        errors.append(f"workspace must be {WORKSPACE_ORIGIN}")
    generated_at = record.get("generatedAt")
    if not isinstance(generated_at, str) or not generated_at.strip():
        errors.append("generatedAt is required")
    else:
        try:
            datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        except ValueError:
            errors.append("generatedAt must be an ISO 8601 timestamp")
    action = record.get("action")
    if action not in MUTATING_ACTIONS:
        errors.append(f"action must be one of {sorted(MUTATING_ACTIONS)}")
        action = ""
    site_key = record.get("siteKey", "")
    if not isinstance(site_key, str):
        errors.append("siteKey must be a string")
        site_key = ""
    else:
        try:
            validate_site_key(site_key)
        except ValueError as exc:
            errors.append(str(exc))
    target = record.get("target")
    if not isinstance(target, str):
        errors.append("target must be a string")
        target = ""
    elif action:
        try:
            validate_target(action, target, site_key)
        except ValueError as exc:
            errors.append(str(exc))

    for key in ("targetType", "targetIdentifier", "expectedResult", "verificationPlan", "cleanupPlan"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            errors.append(f"{key} is required")
    if not isinstance(record.get("fieldsOrFiles"), list):
        errors.append("fieldsOrFiles must be an array")

    auth = record.get("authorization")
    if not isinstance(auth, dict):
        errors.append("authorization must be an object")
        return errors
    if auth.get("userAuthorized") is not True:
        errors.append("authorization.userAuthorized must be true")
    if auth.get("authorizedAction") != action:
        errors.append("authorization.authorizedAction must match action")
    if auth.get("target") != target:
        errors.append("authorization.target must match target")
    source = auth.get("authorizationSource")
    if not isinstance(source, str):
        errors.append("authorization.authorizationSource must be a string")
    elif action and isinstance(target, str):
        try:
            validate_authorization_source(action, source, target)
        except ValueError as exc:
            errors.append(str(exc))
    if not isinstance(auth.get("verificationPlan"), str) or not auth["verificationPlan"].strip():
        errors.append("authorization.verificationPlan is required")
    return errors


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("authorization record must be a JSON object")
    return data


def build_record(args: argparse.Namespace) -> dict:
    action = args.action
    if action not in MUTATING_ACTIONS:
        raise ValueError(f"action must be one of {sorted(MUTATING_ACTIONS)}")
    site_key = validate_site_key(args.site_key or "")
    target = validate_target(action, args.target, site_key)
    source = validate_authorization_source(action, args.authorization_source, target)

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "workspace": WORKSPACE_ORIGIN,
        "siteKey": site_key,
        "action": action,
        "targetType": require_text(args.target_type, "target type"),
        "target": target,
        "targetIdentifier": require_text(args.target_identifier, "target identifier"),
        "fieldsOrFiles": split_values(args.fields_or_files),
        "expectedResult": require_text(args.expected_result, "expected result"),
        "verificationPlan": require_text(args.verification_plan, "verification plan"),
        "cleanupPlan": require_text(args.cleanup_plan, "cleanup plan"),
        "authorization": {
            "userAuthorized": True,
            "authorizedAction": action,
            "target": target,
            "authorizationSource": source,
            "verificationPlan": require_text(args.verification_plan, "verification plan"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an AllinCMS action-specific authorization record.")
    parser.add_argument("--validate-only", help="Validate an existing authorization JSON instead of writing one")
    parser.add_argument("--action", choices=sorted(MUTATING_ACTIONS))
    parser.add_argument("--site-key", default="")
    parser.add_argument("--target")
    parser.add_argument("--target-type")
    parser.add_argument("--target-identifier")
    parser.add_argument("--fields-or-files", default="")
    parser.add_argument("--expected-result")
    parser.add_argument("--verification-plan")
    parser.add_argument("--cleanup-plan")
    parser.add_argument("--authorization-source")
    parser.add_argument("--output")
    args = parser.parse_args()

    try:
        if args.validate_only:
            errors = validate_record(load_json(Path(args.validate_only)))
            if errors:
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print("Authorization record validation passed.")
            return 0
        for key in (
            "action",
            "target",
            "target_type",
            "target_identifier",
            "expected_result",
            "verification_plan",
            "cleanup_plan",
            "authorization_source",
            "output",
        ):
            if getattr(args, key) is None:
                raise ValueError(f"--{key.replace('_', '-')} is required unless --validate-only is used")
        record = build_record(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    output = Path(args.output).expanduser()
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
