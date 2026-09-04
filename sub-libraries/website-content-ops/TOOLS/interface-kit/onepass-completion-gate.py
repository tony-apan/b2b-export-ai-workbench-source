#!/usr/bin/env python3
"""新站一条龙完成机器闸。

用法：python3 onepass-completion-gate.py <absolute-task-root>
只验证交付装配与文件级证据；不会把本地 PASS 夸大为远程发布、SEO 或询盘。
"""
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FRESHNESS = os.path.join(HERE, "check-contract-freshness.py")
SUB_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
PLAN_VALIDATOR = os.path.join(SUB_ROOT, "scripts", "validate-content-operation-plan.mjs")
sys.path.insert(0, HERE)
import content_review_gate as review_gate


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def require_file(path, problems, label):
    if not os.path.isfile(path):
        problems.append(f"missing {label}: {path}")
        return False
    if os.path.getsize(path) == 0:
        problems.append(f"empty {label}: {path}")
        return False
    return True


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 onepass-completion-gate.py <absolute-task-root>")
    task = os.path.realpath(sys.argv[1])
    if not os.path.isabs(sys.argv[1]) or not os.path.isdir(task):
        raise SystemExit("task root must be an existing absolute directory")
    problems = []
    evidence = os.path.join(task, "70_evidence")
    work = os.path.join(task, "20_work")

    receipt = os.path.join(work, "onepass-read-receipt.json")
    if require_file(receipt, problems, "read receipt"):
        result = subprocess.run([sys.executable, FRESHNESS, "--verify-receipt", receipt], capture_output=True, text=True)
        if result.returncode != 0:
            problems.append("contract/read receipt gate failed: " + "; ".join(
                line for line in result.stdout.splitlines() if line.startswith("DRIFT:"))[:600])

    plan_a = sorted(glob.glob(os.path.join(task, "content-operation-plan-A*.json")))
    plan_b = sorted(glob.glob(os.path.join(task, "content-operation-plan-B*.json")))
    if not plan_a:
        problems.append("missing Plan A JSON")
    if not plan_b:
        problems.append("missing Plan B JSON")
    for label, plans in (("Plan A", plan_a[-1:] if plan_a else []), ("Plan B", plan_b[-1:] if plan_b else [])):
        for path in plans:
            plan = load(path)
            if plan.get("authorization_scope", {}).get("status") != "approved":
                problems.append(f"{label} authorization is not approved")
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(plan.get("plan_digest", ""))):
                problems.append(f"{label} digest invalid")
            # Completed plans are expected to be expired now. Revalidate at one
            # millisecond after approval to prove they were executable in their
            # archived authorization/capability window, not at delivery time.
            script = """import fs from 'node:fs'; const {validateContentOperationPlan}=await import(process.argv[1]); const p=JSON.parse(fs.readFileSync(process.argv[2],'utf8')); const at=new Date(Date.parse(p.authorization_scope.approved_at)+1); const r=validateContentOperationPlan(p,{now:at}); console.log(JSON.stringify(r)); process.exit(r.ok&&r.executionReady?0:1);"""
            validator_url = "file://" + PLAN_VALIDATOR
            validation = subprocess.run(["node", "--input-type=module", "-e", script, validator_url, path], capture_output=True, text=True)
            if validation.returncode != 0:
                problems.append(f"{label} was not canonically EXECUTION_READY at approval time")

    readbacks = glob.glob(os.path.join(evidence, "*plan-a-readback.json"))
    if not readbacks:
        problems.append("missing Plan A readback")
    elif require_file(readbacks[0], problems, "Plan A readback"):
        rb = load(readbacks[0])
        if rb.get("delta_count") != 1 or not rb.get("site_id") or not rb.get("site_key"):
            problems.append("Plan A readback does not prove exactly-one new site identity")

    for name in ("brief.json", "taxonomy-ids.json", "media-url-map.json", "routes-final.json", "HANDOFF.md"):
        require_file(os.path.join(evidence, name), problems, name)
    delivery = glob.glob(os.path.join(evidence, "DELIVERY-*.md"))
    if not delivery:
        problems.append("missing DELIVERY manifest")

    products = [p for p in glob.glob(os.path.join(evidence, "products", "*.json")) if not p.endswith("-review.json")]
    product_reviews = glob.glob(os.path.join(evidence, "products", "*-review.json"))
    if not products:
        problems.append("no product payloads")
    if len(product_reviews) != len(products):
        problems.append(f"product review count mismatch: payloads={len(products)} reviews={len(product_reviews)}")
    def verify_review_set(payloads, reviews, object_type):
        review_by_slug = {os.path.basename(path).removesuffix("-review.json"): path for path in reviews}
        for payload_path in payloads:
            payload = review_gate.load_json_strict(payload_path)
            slug = payload.get("slug")
            review_path = review_by_slug.get(slug)
            if not review_path:
                problems.append(f"missing {object_type} review for {slug}")
                continue
            record = review_gate.load_json_strict(review_path)
            if record.get("verdict") != "READY":
                problems.append(f"{object_type} review not READY: {os.path.basename(review_path)}")
            try:
                actual_digest = review_gate.payload_digest(payload)
            except Exception as error:
                problems.append(f"{object_type} payload canonicalization failed for {slug}: {error}")
                continue
            if record.get("business_payload_digest") != actual_digest:
                problems.append(f"{object_type} review digest mismatch: {slug}")
            if record.get("object_type") != object_type or record.get("slug") != slug:
                problems.append(f"{object_type} review identity mismatch: {slug}")
            if record.get("business_operation") not in {"create", "update"}:
                problems.append(f"{object_type} review operation invalid: {slug}")
            if not record.get("site_key") or not record.get("site_id"):
                problems.append(f"{object_type} review site binding missing: {slug}")
                continue
            try:
                rc, _ = review_gate.verify_payload_record(
                    payload, review_path,
                    expected_object_type=object_type,
                    expected_operation=record["business_operation"],
                    expected_site_key=record["site_key"],
                    expected_site_id=record["site_id"],
                    expected_target_id=record.get("target_id"),
                )
                if rc != 0:
                    problems.append(f"{object_type} strict review verification failed: {slug}")
            except Exception as error:
                problems.append(f"{object_type} strict review verification error for {slug}: {error}")

    final_product_payloads = [p for p in glob.glob(os.path.join(work, "final-payloads", "*.json")) if not p.endswith("-review.json")]
    if products and len(final_product_payloads) != len(products):
        problems.append(f"final product payload count mismatch: drafts={len(products)} final={len(final_product_payloads)}")
    verify_review_set(final_product_payloads, product_reviews, "product")

    posts = [p for p in glob.glob(os.path.join(evidence, "posts", "*.json")) if not p.endswith("-review.json")]
    final_post_reviews = glob.glob(os.path.join(work, "final-posts", "*-review.json"))
    if posts and len(final_post_reviews) != len(posts):
        problems.append(f"article review count mismatch: payloads={len(posts)} final reviews={len(final_post_reviews)}")
    # final-posts payloads are the exact wire business payloads paired with reviews.
    final_post_payloads = [p for p in glob.glob(os.path.join(work, "final-posts", "*.json")) if not p.endswith("-review.json")]
    if posts and len(final_post_payloads) != len(posts):
        problems.append(f"final article payload count mismatch: drafts={len(posts)} final={len(final_post_payloads)}")
    verify_review_set(final_post_payloads, final_post_reviews, "article")

    audit_configs = glob.glob(os.path.join(evidence, "*-audit-config.json"))
    if not audit_configs:
        problems.append("missing site audit config")
    else:
        config = load(audit_configs[0])
        expected_products = config.get("count", {}).get("products", 0)
        expected_posts = config.get("count", {}).get("posts", 0)
        if expected_products != len(products):
            problems.append(f"product baseline mismatch: audit={expected_products} payloads={len(products)}")
        if expected_posts != len(posts):
            problems.append(f"article baseline mismatch: audit={expected_posts} payloads={len(posts)}")
        if expected_posts > 0 and not require_file(os.path.join(evidence, "article-create-qualification.json"), problems, "article create qualification"):
            pass

    if problems:
        print("ONEPASS_COMPLETION_BLOCK")
        for problem in problems:
            print("-", problem)
        raise SystemExit(1)
    print(f"ONEPASS_COMPLETION_STRUCTURE_PASS: products={len(products)} posts={len(posts)}")
    print("Boundary: file assembly PASS does not replace live CMS, anonymous frontend, SEO, inquiry, or conversion evidence.")


if __name__ == "__main__":
    main()
