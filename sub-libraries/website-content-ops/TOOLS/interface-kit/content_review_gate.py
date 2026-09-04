#!/usr/bin/env python3
"""Digest-bound review context shared by CLI and AllinCMS mutation wrappers (ISS-102).

Identity boundary: validates stable actor IDs and evidence pointers, not human identity or true independence.
Canonicalization profile: python-json-nfc-v1 (string NFC, string object keys, finite integers only,
object keys sorted, list order preserved, duplicate JSON keys rejected).
"""
import datetime as _dt
import hashlib
import json
import math
import os
import re
import unicodedata

SCHEMA_VERSION = "1.0"
CANONICALIZATION = "python-json-nfc-v1"
PROJECTION_VERSION = "allincms-content-wire-v1"
OBJECTS = {"product", "article"}
OPERATIONS = {"create", "update"}
PHASES = {"create": "create_and_publish", "update": "publish_update"}
ALLOWED_TYPES = {"p", "h2", "h3", "blockquote"}
BUSINESS_KEYS = {
    "product": {"name", "slug", "description", "order", "media", "mediaList", "content", "categories", "tags", "specifications"},
    "article": {"title", "slug", "excerpt", "order", "coverImage", "content", "categories", "tags"},
}
REQUIRED_CHECKS = {
    "facts_confirmed_only",
    "no_invented_price_moq_certification_case",
    "object_specs_not_crossed",
    "slate_shape_valid",
    "cta_bounded",
    "links_use_page_modules",
    "all_business_fields_reviewed",
    "update_diff_reviewed_or_not_applicable",
}


def _pairs_no_duplicates(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate JSON key: {k}")
        out[k] = v
    return out


def load_json_strict(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f, object_pairs_hook=_pairs_no_duplicates,
                         parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"non-finite number: {x}")))


def _normalize(value):
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        if any(0xD800 <= ord(ch) <= 0xDFFF for ch in value):
            raise ValueError("Unicode surrogate code points are not allowed")
        return unicodedata.normalize("NFC", value)
    if isinstance(value, int):
        if abs(value) > 9007199254740991:
            raise ValueError("integer exceeds cross-language safe range")
        return value
    if isinstance(value, float):
        raise ValueError("floats are not allowed; use integer or decimal string")
    if isinstance(value, list):
        return [_normalize(x) for x in value]
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("object keys must be strings")
            nk = unicodedata.normalize("NFC", key)
            if nk in out:
                raise ValueError(f"duplicate normalized key: {nk}")
            out[nk] = _normalize(item)
        return out
    raise ValueError(f"unsupported JSON value: {type(value).__name__}")


def canonical_bytes(payload):
    normalized = _normalize(payload)
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def payload_digest(payload):
    return "sha256:" + hashlib.sha256(canonical_bytes(payload)).hexdigest()


def wire_digest(envelope, *, endpoint=None, action_id=None):
    """Object-level projection digest (not a claim about transmitted bytes)."""
    return payload_digest({"projection_version": PROJECTION_VERSION, "endpoint": endpoint,
                           "action_id": action_id, "payload": envelope})


def request_evidence(endpoint, action_id, request_body, status=None, response_text=None):
    body_digest = "sha256:" + hashlib.sha256(request_body).hexdigest()
    evidence = {"projection_version": PROJECTION_VERSION, "endpoint": endpoint, "action_id": action_id,
                "request_body_digest": body_digest}
    if status is not None: evidence["response_status"] = status
    if response_text is not None: evidence["decoded_response_text_digest"] = "sha256:" + hashlib.sha256(response_text.encode("utf-8")).hexdigest()
    evidence["request_evidence_digest"] = payload_digest(evidence)
    return evidence


def verify_live_capability(context, *, deployment_id, site_key, site_id, required_operations,
                           expected_action_ids, expected_runtime_scope_root, expected_client_id,
                           expected_task_id, now=None):
    """Cooperative supported-flow gate; does not stop a token holder from constructing raw HTTP."""
    problems = []
    if not isinstance(context, dict):
        return 1, ["capability context missing"]
    context_fields = {"status", "deployment_id", "site_key", "site_id", "operations", "evidence_ref",
                      "observed_at", "expires_at", "runtime_scope_root", "evidence_digest", "client_id", "task_id"}
    unknown_context = sorted(set(context) - context_fields)
    if unknown_context: problems.append(f"capability context unknown fields: {unknown_context}")
    if context.get("status") != "live_verified_current_deployment": problems.append("capability status not live_verified_current_deployment")
    if context.get("deployment_id") != deployment_id: problems.append("capability deployment mismatch")
    if context.get("site_key") != site_key or context.get("site_id") != site_id: problems.append("capability site mismatch")
    raw_ops = context.get("operations")
    if (not isinstance(raw_ops, list) or any(not isinstance(operation, str) or not operation for operation in raw_ops)
            or len(raw_ops) != len(set(raw_ops))):
        problems.append("capability operations invalid")
        raw_ops = []
    ops = set(raw_ops)
    if ops != set(required_operations):
        problems.append(f"capability operations must exactly match required operations: {sorted(required_operations)}")
    evidence_ref = str(context.get("evidence_ref", "")).strip()
    raw_root = context.get("runtime_scope_root")
    expected_root_raw = expected_runtime_scope_root
    if (not isinstance(raw_root, str) or not raw_root.strip() or not os.path.isabs(raw_root)
            or not isinstance(expected_root_raw, str) or not expected_root_raw.strip() or not os.path.isabs(expected_root_raw)):
        problems.append("capability runtime_scope_root must be non-empty absolute path")
        runtime_root = ""
    else:
        runtime_root = os.path.realpath(raw_root)
        if runtime_root != os.path.realpath(expected_root_raw): problems.append("capability runtime scope mismatch")
    if context.get("client_id") != expected_client_id or context.get("task_id") != expected_task_id:
        problems.append("capability client/task mismatch")
    if not evidence_ref or not runtime_root or not os.path.isdir(runtime_root):
        problems.append("capability evidence_ref/runtime_scope_root missing")
    else:
        evidence_path = os.path.realpath(evidence_ref if os.path.isabs(evidence_ref) else os.path.join(runtime_root, evidence_ref))
        if not _is_within(runtime_root, evidence_path) or not os.path.isfile(evidence_path):
            problems.append("capability evidence outside/missing runtime scope")
        else:
            with open(evidence_path, "rb") as evidence_file:
                evidence_bytes = evidence_file.read()
            actual = "sha256:" + hashlib.sha256(evidence_bytes).hexdigest()
            if context.get("evidence_digest") != actual:
                problems.append("capability evidence digest mismatch")
            else:
                try:
                    capability_evidence = load_json_strict(evidence_path)
                    if not isinstance(capability_evidence, dict):
                        raise ValueError("root must be object")
                    evidence_fields = {"deployment_id", "site_key", "site_id", "verified_operations", "action_ids", "observed_at"}
                    unknown_evidence = sorted(set(capability_evidence) - evidence_fields)
                    if unknown_evidence: problems.append(f"capability evidence unknown fields: {unknown_evidence}")
                    if set(capability_evidence) != evidence_fields:
                        problems.append("capability evidence required fields mismatch")
                    if capability_evidence.get("deployment_id") != deployment_id: problems.append("capability evidence deployment mismatch")
                    if capability_evidence.get("site_key") != site_key or capability_evidence.get("site_id") != site_id:
                        problems.append("capability evidence site mismatch")
                    raw_verified_ops = capability_evidence.get("verified_operations")
                    if (not isinstance(raw_verified_ops, list)
                            or any(not isinstance(operation, str) or not operation for operation in raw_verified_ops)
                            or len(raw_verified_ops) != len(set(raw_verified_ops))):
                        problems.append("capability evidence verified_operations invalid")
                        raw_verified_ops = []
                    verified_ops = set(raw_verified_ops)
                    if verified_ops != set(required_operations):
                        problems.append("capability evidence operations must exactly match required operations")
                    if verified_ops != ops: problems.append("capability context/evidence operations mismatch")
                    action_ids = capability_evidence.get("action_ids")
                    if not isinstance(action_ids, dict) or set(action_ids) != verified_ops:
                        problems.append("capability evidence action_ids keys mismatch")
                        action_ids = {}
                    for operation in required_operations:
                        action_id = action_ids.get(operation)
                        if not re.fullmatch(r"[0-9a-f]{42}", str(action_id or "")):
                            problems.append(f"capability evidence action missing/invalid: {operation}")
                        elif action_id != expected_action_ids.get(operation):
                            problems.append(f"capability evidence action mismatch: {operation}")
                    if capability_evidence.get("observed_at") != context.get("observed_at"):
                        problems.append("capability evidence observed_at mismatch")
                except Exception as exc:
                    problems.append(f"capability evidence schema invalid: {exc}")
    try:
        observed = _dt.datetime.fromisoformat(str(context.get("observed_at", "")).replace("Z", "+00:00"))
        expires = _dt.datetime.fromisoformat(str(context.get("expires_at", "")).replace("Z", "+00:00"))
        current = now or _dt.datetime.now(_dt.timezone.utc)
        if observed.tzinfo is None or expires.tzinfo is None: problems.append("capability timestamps require timezone")
        else:
            if observed > current: problems.append("capability observed_at is future")
            if current >= expires: problems.append("capability expired")
            if expires <= observed: problems.append("capability invalid interval")
            if expires - observed > _dt.timedelta(minutes=30): problems.append("capability interval exceeds 30 minutes")
            if current - observed > _dt.timedelta(minutes=30): problems.append("capability observation is stale")
    except ValueError:
        problems.append("capability timestamps invalid")
    return (1 if problems else 0), problems


def project_wire_payload(business_payload, *, object_type, site_id, target_id, wire_phase):
    """Pure allowlisted business→wire projection. Review covers business payload; evidence covers envelope."""
    if object_type not in OBJECTS:
        raise ValueError("object_type invalid")
    if wire_phase not in {"create_draft", "publish_update"}:
        raise ValueError("wire_phase invalid")
    allowed = BUSINESS_KEYS[object_type]
    unknown = sorted(set(business_payload) - allowed)
    if unknown:
        raise ValueError(f"unknown/wire-only business fields: {unknown}")
    normalized = _normalize(business_payload)
    envelope = {key: normalized[key] for key in allowed if key in normalized}
    envelope["siteId"] = site_id
    if wire_phase == "publish_update":
        if not target_id:
            raise ValueError("target_id required for publish_update")
        envelope["productId" if object_type == "product" else "postId"] = target_id
        envelope["mode"] = "publish"
    return envelope


def _is_within(root, path):
    try:
        return os.path.commonpath([root, path]) == root
    except ValueError:
        return False


def _validate_text_leaves(children, path, problems):
    if not isinstance(children, list) or not children:
        problems.append(f"{path}.children must be non-empty list"); return ""
    out = []
    for i, leaf in enumerate(children):
        if not isinstance(leaf, dict):
            problems.append(f"{path}.children[{i}] not object"); continue
        unknown = sorted(set(leaf) - {"text", "bold", "italic", "underline"})
        if unknown: problems.append(f"{path}.children[{i}] unknown keys: {unknown}")
        if not isinstance(leaf.get("text"), str):
            problems.append(f"{path}.children[{i}].text not string"); continue
        for mark in ("bold", "italic", "underline"):
            if mark in leaf and not isinstance(leaf[mark], bool): problems.append(f"{path}.children[{i}].{mark} not bool")
        out.append(leaf["text"])
    return "".join(out)


def payload_checks(payload, object_type):
    problems = []
    unknown_business = sorted(set(payload) - BUSINESS_KEYS[object_type])
    if unknown_business: problems.append(f"{object_type} payload unknown/wire-only fields: {unknown_business}")
    product_keys = ("name", "slug", "description", "media", "content", "specifications", "categories", "tags")
    article_keys = ("title", "slug", "excerpt", "coverImage", "content", "categories", "tags")
    for key in (product_keys if object_type == "product" else article_keys):
        if key not in payload or payload.get(key) in (None, ""):
            problems.append(f"{object_type}.{key} missing")
    if not payload.get("categories"):
        problems.append(f"{object_type}.categories empty")
    if object_type == "article" and len(str(payload.get("excerpt", ""))) > 200:
        problems.append("article.excerpt > 200")
    if object_type == "product":
        forbidden = sorted(set(payload) & {"title", "excerpt", "coverImage", "postId"})
        if forbidden: problems.append(f"product payload contains article fields: {forbidden}")
        if not payload.get("content"): problems.append("product.content empty")
        if not payload.get("specifications"): problems.append("product.specifications empty")
        for i, item in enumerate(payload.get("specifications") or []):
            if not isinstance(item, dict) or not str(item.get("key", "")).strip() or not str(item.get("value", "")).strip():
                problems.append(f"product.specifications[{i}] invalid")
    else:
        forbidden = sorted(set(payload) & {"name", "description", "specifications", "media", "mediaList", "productId"})
        if forbidden: problems.append(f"article payload contains product fields: {forbidden}")
    content = payload.get("content") or []
    seen_ids = set()
    def add_id(value, path):
        if not isinstance(value, str) or not value:
            problems.append(f"{path}.id missing"); return
        if value in seen_ids: problems.append(f"duplicate Slate id: {value}")
        seen_ids.add(value)
    for i, block in enumerate(content):
        path = f"content[{i}]"
        if not isinstance(block, dict):
            problems.append(f"{path} not object"); continue
        block_type = block.get("type")
        if block_type not in ALLOWED_TYPES:
            problems.append(f"{path}.type unsupported"); continue
        add_id(block.get("id"), path)
        if block_type == "blockquote":
            unknown_block = sorted(set(block) - {"type", "id", "children"})
            if unknown_block: problems.append(f"{path} unknown keys: {unknown_block}")
            children = block.get("children")
            if not isinstance(children, list) or not children:
                problems.append(f"{path}.children must wrap non-empty p blocks"); text = ""
            else:
                pieces = []
                for j, inner in enumerate(children):
                    if not isinstance(inner, dict) or inner.get("type") != "p":
                        problems.append(f"{path}.children[{j}] must be p block"); continue
                    unknown_inner = sorted(set(inner) - {"type", "id", "children"})
                    if unknown_inner: problems.append(f"{path}.children[{j}] unknown keys: {unknown_inner}")
                    add_id(inner.get("id"), f"{path}.children[{j}]")
                    pieces.append(_validate_text_leaves(inner.get("children"), f"{path}.children[{j}]", problems))
                text = "".join(pieces)
        else:
            unknown_block = sorted(set(block) - {"type", "id", "children"})
            if unknown_block: problems.append(f"{path} unknown keys: {unknown_block}")
            text = _validate_text_leaves(block.get("children"), path, problems)
        if not text.strip(): problems.append(f"{path} empty")
        if any(x in text for x in ("**", "](", "```")): problems.append(f"{path} markdown residue")
        internal_terms = []
        if re.search(r"\bUNIT-\d+\b", text, re.I): internal_terms.append("UNIT-ID")
        for term in ("source-extraction", "claim ledger", "review record", "payload digest"):
            if term in text.lower(): internal_terms.append(term)
        if internal_terms: problems.append(f"{path} exposes internal evidence vocabulary: {sorted(set(internal_terms))}")
    return problems


def _valid_rfc3339(value):
    if not isinstance(value, str) or not re.search(r"(?:Z|[+-]\d\d:\d\d)$", value):
        return False
    try:
        _dt.datetime.fromisoformat(value.replace("Z", "+00:00")); return True
    except ValueError:
        return False


def verify_payload_record(payload, record_path, *, expected_object_type, expected_operation,
                          expected_site_key, expected_site_id, expected_target_id):
    record = load_json_strict(record_path)
    problems = []
    phase = PHASES.get(expected_operation)
    required_fields = {
        "schema_version", "canonicalization", "object_type", "business_operation", "mutation_phase",
        "site_key", "site_id", "target_id", "slug", "runtime_scope_root", "client_id", "task_id",
        "business_payload_digest", "producer_id",
        "reviewer_id", "reviewer_identity_status", "independence_evidence_ref", "reviewed_at",
        "verdict", "findings", "fact_source_refs", "checks",
    }
    missing = sorted(required_fields - set(record))
    if missing: problems.append(f"record missing fields: {missing}")
    unknown = sorted(set(record) - required_fields - {"note"})
    if unknown: problems.append(f"record unknown fields: {unknown}")
    if record.get("schema_version") != SCHEMA_VERSION: problems.append("schema_version mismatch")
    if record.get("canonicalization") != CANONICALIZATION: problems.append("canonicalization mismatch")
    if expected_object_type not in OBJECTS or record.get("object_type") != expected_object_type: problems.append("object_type mismatch")
    if expected_operation not in OPERATIONS or record.get("business_operation") != expected_operation: problems.append("business_operation mismatch")
    if record.get("mutation_phase") != phase: problems.append("mutation_phase mismatch")
    if record.get("site_key") != expected_site_key: problems.append("site_key mismatch")
    if record.get("site_id") != expected_site_id: problems.append("site_id mismatch")
    raw_runtime_root = record.get("runtime_scope_root")
    if not isinstance(raw_runtime_root, str) or not raw_runtime_root.strip() or not os.path.isabs(raw_runtime_root):
        runtime_root = ""
        problems.append("runtime_scope_root must be non-empty absolute path")
    else:
        runtime_root = os.path.realpath(raw_runtime_root)
    review_real = os.path.realpath(record_path)
    if not runtime_root or not os.path.isdir(runtime_root): problems.append("runtime_scope_root invalid")
    elif not _is_within(runtime_root, review_real): problems.append("review record outside runtime scope")
    if not str(record.get("client_id", "")).strip() or not str(record.get("task_id", "")).strip():
        problems.append("client_id/task_id missing")
    if record.get("target_id") != expected_target_id: problems.append("target_id mismatch")
    if record.get("slug") != payload.get("slug"): problems.append("slug mismatch")
    try:
        actual_digest = payload_digest(payload)
    except ValueError as exc:
        problems.append(f"payload canonicalization failed: {exc}"); actual_digest = None
    if record.get("business_payload_digest") != actual_digest: problems.append("business_payload_digest mismatch")
    producer_raw, reviewer_raw = record.get("producer_id"), record.get("reviewer_id")
    actor_pattern = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._-]{2,200}$")
    producer = producer_raw if isinstance(producer_raw, str) else ""
    reviewer = reviewer_raw if isinstance(reviewer_raw, str) else ""
    if not actor_pattern.fullmatch(producer) or not actor_pattern.fullmatch(reviewer) or producer == reviewer:
        problems.append("producer/reviewer IDs invalid or equal")
    if record.get("reviewer_identity_status") != "not_verified": problems.append("reviewer_identity_status must be not_verified")
    independence_ref = record.get("independence_evidence_ref")
    if not isinstance(independence_ref, str) or not re.fullmatch(r"independent-review-task:agent_[A-Za-z0-9._-]+", independence_ref):
        problems.append("independence_evidence_ref invalid unverified task pointer")
    if not _valid_rfc3339(record.get("reviewed_at")): problems.append("reviewed_at invalid")
    refs = record.get("fact_source_refs")
    if not isinstance(refs, list) or not refs:
        problems.append("fact_source_refs invalid")
    else:
        review_dir = os.path.dirname(os.path.abspath(record_path))
        for i, ref in enumerate(refs):
            if (not isinstance(ref, dict) or not str(ref.get("ref", "")).strip()
                    or not re.fullmatch(r"sha256:[0-9a-f]{64}", str(ref.get("digest", "")))):
                problems.append(f"fact_source_refs[{i}] invalid"); continue
            source_ref = str(ref["ref"])
            source_path = os.path.realpath(os.path.abspath(os.path.expanduser(source_ref)) if os.path.isabs(source_ref)
                                           else os.path.abspath(os.path.join(review_dir, source_ref)))
            if not os.path.isfile(source_path):
                problems.append(f"fact_source_refs[{i}] missing: {source_path}"); continue
            if runtime_root and os.path.isdir(runtime_root) and not _is_within(runtime_root, source_path):
                problems.append(f"fact_source_refs[{i}] outside runtime scope"); continue
            with open(source_path, "rb") as source_file:
                actual_source_digest = "sha256:" + hashlib.sha256(source_file.read()).hexdigest()
            if actual_source_digest != ref["digest"]:
                problems.append(f"fact_source_refs[{i}] digest mismatch")
    checks = record.get("checks")
    if not isinstance(checks, dict) or set(checks) != REQUIRED_CHECKS or any(checks.get(k) is not True for k in REQUIRED_CHECKS):
        problems.append("checks incomplete/not all true")
    findings = record.get("findings")
    if not isinstance(findings, list):
        problems.append("findings invalid")
    else:
        for i, finding in enumerate(findings):
            required_finding = {"severity", "location", "evidence", "status"}
            if not isinstance(finding, dict) or set(finding) != required_finding:
                problems.append(f"finding[{i}] invalid fields"); continue
            if finding.get("severity") not in {"P0", "P1", "P2", "WARN"}: problems.append(f"finding[{i}].severity invalid")
            if finding.get("status") not in {"resolved", "accepted_warn"}: problems.append(f"finding[{i}].status invalid")
            if not isinstance(finding.get("location"), str) or not finding["location"].strip(): problems.append(f"finding[{i}].location invalid")
            if not isinstance(finding.get("evidence"), str) or not finding["evidence"].strip(): problems.append(f"finding[{i}].evidence invalid")
            if finding.get("severity") in {"P0", "P1"} and finding.get("status") != "resolved": problems.append(f"finding[{i}] unresolved blocker")
    if record.get("verdict") != "READY": problems.append("verdict is not READY")
    problems += payload_checks(payload, expected_object_type)
    if problems:
        print("CONTENT_REVIEW FAIL:")
        for item in problems: print("  -", item)
        return 1, None
    context = {
        "schema_version": SCHEMA_VERSION,
        "canonicalization": CANONICALIZATION,
        "projection_version": PROJECTION_VERSION,
        "business_payload_digest": actual_digest,
        "object_type": expected_object_type,
        "business_operation": expected_operation,
        "mutation_phase": phase,
        "site_key": expected_site_key,
        "site_id": expected_site_id,
        "runtime_scope_root": runtime_root,
        "client_id": record.get("client_id"),
        "task_id": record.get("task_id"),
        "target_id": expected_target_id,
        "slug": payload.get("slug"),
        "review_record_path": record_path,
        "reviewer_identity_status": "not_verified",
    }
    print(f"CONTENT_REVIEW PASS: {expected_object_type}/{expected_operation} {payload.get('slug')} {actual_digest}")
    return 0, context
