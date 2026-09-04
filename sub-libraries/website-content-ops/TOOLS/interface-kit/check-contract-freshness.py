#!/usr/bin/env python3
"""AllinCMS 合同新鲜度机器闸（ISS-111/119）。

对照四层：
1. canonical Registry capability route；
2. canonical JavaScript interface implementation + host driver handler；
3. host interface-kit Python transport（article.create 必须 fail-closed：P0-3.1 起 Python 不得成为
   第二执行面，`_create_post_transport`、`_send_content_transport+CREATE_POST`、
   `mutate_reviewed_post(target_id=None)` 三道 canonical-controller-required guard 缺一即 DRIFT；
   不再要求 Python 能发送 create）；
4. 可选当前部署 action 实扫。

任一层声称 canonical、另一层仍 BLOCK/缺 handler 时直接 DRIFT；不得继续走降级。
用法：python3 check-contract-freshness.py [--live --site-key KEY --token-file FILE]
"""
import json
import hashlib
import datetime
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ADAPTER = os.path.abspath(os.path.join(HERE, "..", "..", "ADAPTERS", "cms", "allincms"))
API_PY = os.path.join(HERE, "allincms_api.py")
ARTICLE_JS = os.path.join(ADAPTER, "article-operations.mjs")
PRODUCT_JS = os.path.join(ADAPTER, "product-operations.mjs")
HOST_DRIVER = os.path.join(ADAPTER, "content-plan-host-driver.mjs")
READ_CONTRACT = os.path.join(HERE, "templates", "onepass-read-contract.json")

CAP_TO_CONST = {
    "article.create": "CREATE_POST",
    "article.update": "UPSERT_POST",
    "article.publish": "UPSERT_POST",
    "product.create": "CREATE_PRODUCT",
    "product.update": "UPSERT_PRODUCT",
    "product.publish": "UPSERT_PRODUCT",
    "site.create": "CREATE_SITE_A",
}
CANONICAL_HANDLER_KEYS = {
    "article.create": "article:create",
    "article.update": "article:update",
    "article.publish": "article:publish",
    "product.create": "product:create",
    "product.update": "product:update",
    "product.publish": "product:publish",
}
IMPLEMENTATION_EXPORTS = {
    "article.create": (ARTICLE_JS, "createPostDraft"),
    "article.update": (ARTICLE_JS, "savePostDraft"),
    "article.publish": (ARTICLE_JS, "publishPost"),
    "product.create": (PRODUCT_JS, "createProductDraft"),
    "product.update": (PRODUCT_JS, "saveProductDraft"),
    "product.publish": (PRODUCT_JS, "publishProduct"),
}


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def function_body(source, name):
    match = re.search(rf"(?:export\s+)?(?:async\s+)?function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", source)
    if not match:
        return None
    start = match.end()
    depth = 1
    for pos in range(start, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start:pos]
    return None


def python_method_body(source, name):
    """Return the source slice of one class method `def name(...):` up to the next member."""
    match = re.search(rf"^    def {re.escape(name)}\(.*?\):\n", source, re.M | re.S)
    if not match:
        return None
    start = match.end()
    nxt = re.search(r"\n    def |\n    @|\n\nclass |\n# ", source[start:])
    return source[start:start + (nxt.start() if nxt else 0)]


PYTHON_ARTICLE_CREATE_GUARD_ERROR = "ARTICLE_CREATE_CANONICAL_CONTROLLER_REQUIRED"
PYTHON_ARTICLE_CREATE_GUARDS = (
    ("_create_post_transport", r"raise\s+RuntimeError", "refuse before any payload projection/network"),
    ("_send_content_transport", r"action\s*==\s*CREATE_POST", "refuse CREATE_POST before any request"),
    ("mutate_reviewed_post", r"target_id\s+is\s+None", "refuse create before review/capability/network"),
)


def parse_args():
    args = {"live": False, "site_key": None, "token_file": None, "write_receipt": None, "verify_receipt": None}
    raw = sys.argv[1:]
    index = 0
    while index < len(raw):
        arg = raw[index]
        if arg == "--live":
            args["live"] = True
        elif arg == "--site-key":
            index += 1
            if index >= len(raw):
                raise SystemExit("--site-key requires a value")
            args["site_key"] = raw[index]
        elif arg == "--token-file":
            index += 1
            if index >= len(raw):
                raise SystemExit("--token-file requires a value")
            args["token_file"] = raw[index]
        elif arg == "--write-receipt":
            index += 1
            if index >= len(raw):
                raise SystemExit("--write-receipt requires a task-root-relative or absolute JSON path")
            args["write_receipt"] = raw[index]
        elif arg == "--verify-receipt":
            index += 1
            if index >= len(raw):
                raise SystemExit("--verify-receipt requires a JSON path")
            args["verify_receipt"] = raw[index]
        else:
            raise SystemExit(f"unknown argument: {arg}")
        index += 1
    return args


def sha256_file(path):
    with open(path, "rb") as handle:
        return "sha256:" + hashlib.sha256(handle.read()).hexdigest()


def verify_read_contract(problems):
    documents = []
    if not os.path.isfile(READ_CONTRACT):
        problems.append("onepass-read-contract.json missing")
        return documents
    contract = load_json(READ_CONTRACT)
    for item in sorted(contract.get("required_reading", []), key=lambda value: value.get("order", 0)):
        path = os.path.abspath(os.path.join(HERE, "..", "..", item["path"]))
        if not os.path.isfile(path):
            problems.append(f"required reading missing: {item['path']}")
            continue
        text = read(path)
        for marker in item.get("required_markers", []):
            if marker not in text:
                problems.append(f"required reading marker missing: {item['path']} -> {marker}")
        documents.append({"order": item.get("order"), "path": item["path"], "digest": sha256_file(path)})
    return documents


def write_or_verify_receipt(args, documents, problems):
    contract_digest = sha256_file(READ_CONTRACT) if os.path.isfile(READ_CONTRACT) else None
    if args["write_receipt"]:
        receipt = {
            "schema_version": "1.0",
            "contract_digest": contract_digest,
            "documents": documents,
            "acknowledged_at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "acknowledgement": "AI read each required document and will follow the gate sequence; receipt binds exact bytes, not only filenames."
        }
        path = os.path.abspath(args["write_receipt"])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(receipt, handle, ensure_ascii=False, indent=2)
        print(f"READ_RECEIPT_WRITTEN: {path}")
    if args["verify_receipt"]:
        path = os.path.abspath(args["verify_receipt"])
        if not os.path.isfile(path):
            problems.append("read receipt missing")
            return
        receipt = load_json(path)
        if receipt.get("contract_digest") != contract_digest:
            problems.append("read receipt contract digest is stale")
        got = {(item.get("path"), item.get("digest")) for item in receipt.get("documents", [])}
        want = {(item["path"], item["digest"]) for item in documents}
        if got != want:
            problems.append("read receipt document digests are stale or incomplete")


def main():
    args = parse_args()
    registry = load_json(os.path.join(ADAPTER, "interface-registry.json"))
    python_source = read(API_PY)
    driver_source = read(HOST_DRIVER)
    python_consts = dict(re.findall(r'^([A-Z_]+)\s*=\s*"([0-9a-f]{42})"', python_source, re.M))
    interfaces = {item["interface_id"]: item for item in registry["interfaces"]}
    problems = []
    warnings = []

    documents = verify_read_contract(problems)
    write_or_verify_receipt(args, documents, problems)

    for route in registry["capability_routes"]:
        capability_id = route["capability_id"]
        short = capability_id.removeprefix("allincms.")
        availability = route.get("availability")
        gate = route.get("execution_gate")
        default_interface = interfaces.get(route.get("default_interface_id"))

        if availability == "canonical":
            if route.get("execution_surface") == "full_source_checkout" and not route.get("controller_interface_id"):
                problems.append(f"{capability_id}: canonical full-source route has no controller")
            if default_interface is None:
                problems.append(f"{capability_id}: canonical route default interface missing")
            elif default_interface.get("exposure") != "canonical":
                problems.append(f"{capability_id}: Registry canonical but default interface exposure={default_interface.get('exposure')}")

            implementation = IMPLEMENTATION_EXPORTS.get(short)
            if implementation:
                path, export_name = implementation
                source = read(path)
                body = function_body(source, export_name)
                if body is None:
                    problems.append(f"{capability_id}: canonical export {export_name} missing")
                elif "BLOCKED_BY_CANONICAL_REGISTRY" in body or re.search(r"throw new Error\([^)]*BLOCK", body):
                    problems.append(f"{capability_id}: canonical export {export_name} still hard-BLOCKs")

            handler_key = CANONICAL_HANDLER_KEYS.get(short)
            if handler_key and re.search(rf"['\"]{re.escape(handler_key)}['\"]\s*:", driver_source) is None:
                problems.append(f"{capability_id}: canonical host driver handler {handler_key} missing")

            const_name = CAP_TO_CONST.get(short)
            if gate == "fresh_live_verified_current_deployment" and const_name and const_name not in python_consts:
                problems.append(f"{capability_id}: host helper missing action constant {const_name}")

            if short == "product.create":
                if re.search(r"['\"]product:create['\"]\s*:[\s\S]{0,1800}beforeProductIds:\s*\[\s*\]", driver_source):
                    problems.append("allincms.product.create: host driver fabricates an empty beforeProductIds snapshot")
                if re.search(r"['\"]product:create['\"]\s*:[\s\S]{0,2200}getCreatedProductId:\s*\(\)\s*=>\s*operation\.identity\.id", driver_source):
                    problems.append("allincms.product.create: host driver fabricates the created ID from plan identity")

            if short == "article.create":
                js_source = read(ARTICLE_JS)
                for blocker in (
                    "if (actionName === 'postCreate') throw new Error('ARTICLE_CREATE_BLOCKED_BY_CANONICAL_REGISTRY')",
                    "export async function createPostDraft()",
                ):
                    if blocker in js_source:
                        problems.append(f"{capability_id}: canonical JS contains stale create blocker: {blocker}")
                # P0-3.1: Python must stay fail-closed for article create (canonical is the
                # full-source JS Controller); a missing/tampered guard is drift, and Python
                # create sendability is never required again.
                for method_name, required_pattern, meaning in PYTHON_ARTICLE_CREATE_GUARDS:
                    body = python_method_body(python_source, method_name)
                    if body is None:
                        problems.append(f"{capability_id}: Python host helper method {method_name} missing")
                    elif PYTHON_ARTICLE_CREATE_GUARD_ERROR not in body or re.search(required_pattern, body) is None:
                        problems.append(f"{capability_id}: Python {method_name} lacks canonical-controller-required guard ({meaning})")
                mutate_body = python_method_body(python_source, "mutate_reviewed_post")
                if (mutate_body is not None and PYTHON_ARTICLE_CREATE_GUARD_ERROR in mutate_body
                        and "verify_payload_record" in mutate_body
                        and mutate_body.index(PYTHON_ARTICLE_CREATE_GUARD_ERROR) > mutate_body.index("verify_payload_record")):
                    problems.append(f"{capability_id}: Python mutate_reviewed_post guard fires after review verification")

        if availability == "blocked":
            const_name = CAP_TO_CONST.get(short)
            hint = ""
            if const_name and const_name in python_consts:
                hint = f" action constant {const_name} exists; run deployment qualification before accepting fallback"
            warnings.append(f"{capability_id}: blocked.{hint}")

    if args["live"]:
        token = os.environ.get("WS_TOKEN", "")
        if args["token_file"]:
            token = read(args["token_file"]).strip()
        if not token or not args["site_key"]:
            problems.append("--live requires --site-key and WS_TOKEN/--token-file")
        else:
            env = dict(os.environ, WS_TOKEN=token)
            path = f"/{args['site_key']}/posts"
            result = subprocess.run(
                [sys.executable, os.path.join(HERE, "scan", "scan-actions.py"), "-", path],
                env=env, capture_output=True, text=True, check=False,
            )
            if result.returncode != 0:
                problems.append(f"live action scan failed: {result.stderr.strip()[:180]}")
            else:
                live_ids = set(re.findall(r"= ([0-9a-f]{42})", result.stdout))
                for short, const_name in CAP_TO_CONST.items():
                    action_id = python_consts.get(const_name)
                    if action_id and action_id in live_ids:
                        route = next((item for item in registry["capability_routes"] if item["capability_id"] == f"allincms.{short}"), None)
                        if route and route.get("availability") == "blocked":
                            problems.append(f"LIVE: allincms.{short} blocked but current deployment action {const_name} exists")

    print(f"registry routes: {len(registry['capability_routes'])} | interfaces: {len(registry['interfaces'])} | host constants: {len(python_consts)}")
    for warning in warnings:
        print("WARN:", warning)
    for problem in problems:
        print("DRIFT:", problem)
    if problems:
        print("CONTRACT_FRESHNESS_DRIFT")
        raise SystemExit(1)
    print("CONTRACT_FRESHNESS_PASS (Registry/canonical JS/host driver/Python fail-closed guards/read-contract aligned)")


if __name__ == "__main__":
    main()
