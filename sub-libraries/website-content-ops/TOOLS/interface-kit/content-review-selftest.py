#!/usr/bin/env python3
"""Offline adversarial self-test for ISS-102 review context and mutation boundary."""
import copy, datetime, hashlib, json, os, tempfile
from allincms_api import AllinCMS
import allincms_api as api_contract
import content_review_gate as gate


def write(path, value):
    with open(path, "w", encoding="utf-8") as f: json.dump(value, f, ensure_ascii=False)


def main():
    with tempfile.TemporaryDirectory() as td:
        source = os.path.join(td, "source.md")
        open(source, "w", encoding="utf-8").write("confirmed synthetic fact\n")
        payload = {
            "name": "Synthetic Product", "slug": "synthetic-product", "description": "confirmed synthetic fact",
            "order": 0, "media": {"name":"m","type":"image","source":"oss","path":"s/m.jpg"},
            "mediaList": [], "categories": ["category-id"], "tags": [],
            "specifications": [{"key":"Frequency","value":"1 GHz"}],
            "content": [{"type":"h2","id":"x","children":[{"text":"Confirmed"}]},
                        {"type":"p","id":"y","children":[{"text":"confirmed synthetic fact"}]}],
        }
        checks = {key: True for key in gate.REQUIRED_CHECKS}
        record = {
            "schema_version": gate.SCHEMA_VERSION, "canonicalization": gate.CANONICALIZATION,
            "object_type":"product", "business_operation":"update", "mutation_phase":"publish_update",
            "site_key":"synthetic-site", "site_id":"synthetic-site-id", "target_id":"synthetic-target-id",
            "runtime_scope_root":td, "client_id":"synthetic-client", "task_id":"synthetic-task",
            "slug":payload["slug"], "business_payload_digest":gate.payload_digest(payload),
            "producer_id":"actor:producer", "reviewer_id":"actor:reviewer", "reviewer_identity_status":"not_verified",
            "independence_evidence_ref":"independent-review-task:agent_synthetic-review", "reviewed_at":"2026-09-02T00:00:00+08:00",
            "verdict":"READY", "findings":[],
            "fact_source_refs":[{"ref":"source.md","digest":"sha256:"+hashlib.sha256(open(source,"rb").read()).hexdigest()}],
            "checks":checks,
        }
        record_path = os.path.join(td, "review.json"); write(record_path, record)
        now = datetime.datetime.now(datetime.timezone.utc)
        observed_at = (now-datetime.timedelta(minutes=1)).isoformat()
        def make_capability(name, operations, action_ids):
            evidence = {
                "deployment_id": api_contract.DEPLOY,
                "site_key":"synthetic-site", "site_id":"synthetic-site-id",
                "verified_operations":operations, "action_ids":action_ids,
                "observed_at":observed_at,
            }
            evidence_path = os.path.join(td, f"{name}-capability-evidence.json")
            write(evidence_path, evidence)
            context = {
                "status":"live_verified_current_deployment", "deployment_id":api_contract.DEPLOY,
                "site_key":"synthetic-site", "site_id":"synthetic-site-id", "operations":operations,
                "evidence_ref":os.path.basename(evidence_path), "runtime_scope_root":td,
                "client_id":"synthetic-client", "task_id":"synthetic-task",
                "evidence_digest":"sha256:"+hashlib.sha256(open(evidence_path,"rb").read()).hexdigest(),
                "observed_at":observed_at, "expires_at":(now+datetime.timedelta(minutes=10)).isoformat(),
            }
            return evidence, evidence_path, context

        product_update_operations = ["allincms.product.update", "allincms.product.publish"]
        product_update_actions = {
            "allincms.product.update": api_contract.UPSERT_PRODUCT,
            "allincms.product.publish": api_contract.UPSERT_PRODUCT,
        }
        capability_evidence, capability_evidence_path, capability = make_capability(
            "product-update", product_update_operations, product_update_actions)
        _, _, product_create_capability = make_capability(
            "product-create", ["allincms.product.create", "allincms.product.publish"],
            {"allincms.product.create":api_contract.CREATE_PRODUCT,
             "allincms.product.publish":api_contract.UPSERT_PRODUCT})
        _, _, article_capability = make_capability(
            "article-update", ["allincms.article.update", "allincms.article.publish"],
            {"allincms.article.update":api_contract.UPSERT_POST,
             "allincms.article.publish":api_contract.UPSERT_POST})

        def verify(pp, rr, **overrides):
            rp = os.path.join(td, "case.json"); write(rp, rr)
            return gate.verify_payload_record(
                pp, rp, expected_object_type=overrides.get("object_type","product"),
                expected_operation=overrides.get("operation","update"), expected_site_key=overrides.get("site_key","synthetic-site"),
                expected_site_id=overrides.get("site_id","synthetic-site-id"), expected_target_id=overrides.get("target_id","synthetic-target-id"))[0]

        assert verify(payload, record) == 0
        cases = []
        def case(name, payload_mut=None, record_mut=None, **overrides):
            pp, rr = copy.deepcopy(payload), copy.deepcopy(record)
            if payload_mut: payload_mut(pp)
            if record_mut: record_mut(rr)
            assert verify(pp, rr, **overrides) == 1, name
            cases.append(name)
        case("payload drift", payload_mut=lambda p: p.update(description="changed"))
        case("wrong object", record_mut=lambda r: r.update(object_type="article"))
        case("wrong operation", record_mut=lambda r: r.update(business_operation="create"))
        case("wrong site", record_mut=lambda r: r.update(site_key="other"))
        case("wrong target", record_mut=lambda r: r.update(target_id="other"))
        case("same actor", record_mut=lambda r: r.update(reviewer_id=r["producer_id"]))
        case("invalid actor format", record_mut=lambda r: r.update(reviewer_id={"not":"string"}))
        case("invalid independence pointer", record_mut=lambda r: r.update(independence_evidence_ref="free-text"))
        case("false check", record_mut=lambda r: r["checks"].update(facts_confirmed_only=False))
        case("unresolved P1", record_mut=lambda r: r.update(findings=[{"severity":"P1","location":"x","evidence":"x","status":"accepted_warn"}]))
        case("finding extra field", record_mut=lambda r: r.update(findings=[{"severity":"P2","location":"x","evidence":"x","status":"accepted_warn","extra":True}]))
        case("finding empty evidence", record_mut=lambda r: r.update(findings=[{"severity":"P2","location":"x","evidence":"","status":"accepted_warn"}]))
        case("source drift", record_mut=lambda r: r["fact_source_refs"][0].update(digest="sha256:"+"0"*64))
        case("hybrid payload", payload_mut=lambda p: p.update(title="article"))
        case("wire field injection", payload_mut=lambda p: p.update(siteId="attacker-site", mode="publish", productId="attacker-id"))
        case("unknown business field", payload_mut=lambda p: p.update(unexpectedServerField=True))
        case("unknown record field", record_mut=lambda r: r.update(extra=True))
        case("malformed children", payload_mut=lambda p: p["content"][0].update(children={"text":"bad"}))
        case("missing block id", payload_mut=lambda p: p["content"][0].pop("id"))
        case("flat blockquote", payload_mut=lambda p: p["content"].append({"type":"blockquote","id":"q","children":[{"text":"flat"}]}))
        case("nested p missing id", payload_mut=lambda p: p["content"].append({"type":"blockquote","id":"q","children":[{"type":"p","children":[{"text":"quote"}]}]}))
        case("unknown leaf key", payload_mut=lambda p: p["content"][0]["children"][0].update(url="bad"))
        case("duplicate top-level id", payload_mut=lambda p: p["content"][1].update(id=p["content"][0]["id"]))
        case("duplicate nested id", payload_mut=lambda p: p["content"].append({"type":"blockquote","id":"q","children":[{"type":"p","id":p["content"][0]["id"],"children":[{"text":"quote"}]}]}))
        # Actual source-byte drift (not merely a forged digest) invalidates the record.
        open(source, "a", encoding="utf-8").write("drift\n")
        assert verify(payload, record) == 1
        open(source, "w", encoding="utf-8").write("confirmed synthetic fact\n")
        assert verify(payload, record) == 0

        # Fresh capability contract rejects wrong deployment/operations/expiry.
        cap_bad = copy.deepcopy(capability); cap_bad["deployment_id"] = "wrong"
        assert gate.verify_live_capability(cap_bad, deployment_id=__import__('allincms_api').DEPLOY,
                                           site_key="synthetic-site", site_id="synthetic-site-id",
                                           required_operations=set(product_update_operations), expected_action_ids=product_update_actions, expected_runtime_scope_root=td, expected_client_id="synthetic-client", expected_task_id="synthetic-task")[0] == 1
        cap_bad = copy.deepcopy(capability); cap_bad["operations"] = []
        assert gate.verify_live_capability(cap_bad, deployment_id=__import__('allincms_api').DEPLOY,
                                           site_key="synthetic-site", site_id="synthetic-site-id",
                                           required_operations=set(product_update_operations), expected_action_ids=product_update_actions, expected_runtime_scope_root=td, expected_client_id="synthetic-client", expected_task_id="synthetic-task")[0] == 1
        cap_bad = copy.deepcopy(capability)
        cap_bad["operations"].append("forged.extra.operation")
        forged_evidence = copy.deepcopy(capability_evidence)
        forged_evidence["verified_operations"].append("forged.extra.operation")
        forged_evidence["action_ids"]["forged.extra.operation"] = "f" * 42
        forged_path = os.path.join(td, "forged-capability-evidence.json")
        write(forged_path, forged_evidence)
        cap_bad["evidence_ref"] = os.path.basename(forged_path)
        cap_bad["evidence_digest"] = "sha256:" + hashlib.sha256(open(forged_path, "rb").read()).hexdigest()
        assert gate.verify_live_capability(cap_bad, deployment_id=api_contract.DEPLOY,
                                           site_key="synthetic-site", site_id="synthetic-site-id",
                                           required_operations={"allincms.product.update", "allincms.product.publish"},
                                           expected_action_ids=product_update_actions, expected_runtime_scope_root=td,
                                           expected_client_id="synthetic-client", expected_task_id="synthetic-task")[0] == 1
        cap_bad = copy.deepcopy(capability); cap_bad["expires_at"] = (now-datetime.timedelta(seconds=1)).isoformat()
        assert gate.verify_live_capability(cap_bad, deployment_id=__import__('allincms_api').DEPLOY,
                                           site_key="synthetic-site", site_id="synthetic-site-id",
                                           required_operations=set(product_update_operations), expected_action_ids=product_update_actions, expected_runtime_scope_root=td, expected_client_id="synthetic-client", expected_task_id="synthetic-task")[0] == 1
        for key, value in (("runtime_scope_root", ""), ("runtime_scope_root", "relative/path"),
                           ("client_id", "other-client"), ("task_id", "other-task")):
            cap_bad = copy.deepcopy(capability); cap_bad[key] = value
            assert gate.verify_live_capability(cap_bad, deployment_id=__import__('allincms_api').DEPLOY,
                                               site_key="synthetic-site", site_id="synthetic-site-id",
                                               required_operations=set(product_update_operations), expected_action_ids=product_update_actions, expected_runtime_scope_root=td,
                                               expected_client_id="synthetic-client", expected_task_id="synthetic-task")[0] == 1
        original_evidence = copy.deepcopy(capability_evidence)
        capability_evidence["action_ids"]["allincms.product.update"] = api_contract.CREATE_PRODUCT
        write(capability_evidence_path, capability_evidence)
        cap_bad = copy.deepcopy(capability)
        cap_bad["evidence_digest"] = "sha256:" + hashlib.sha256(open(capability_evidence_path, "rb").read()).hexdigest()
        assert gate.verify_live_capability(cap_bad, deployment_id=api_contract.DEPLOY,
                                           site_key="synthetic-site", site_id="synthetic-site-id",
                                           required_operations={"allincms.product.update"},
                                           expected_action_ids={"allincms.product.update": api_contract.UPSERT_PRODUCT},
                                           expected_runtime_scope_root=td, expected_client_id="synthetic-client",
                                           expected_task_id="synthetic-task")[0] == 1
        write(capability_evidence_path, original_evidence)

        api = AllinCMS(token="synthetic")
        api._authoritative_content_readback = lambda site, target, business, object_type: (
            True, {"target_id":target, "business_exact_match":True, "list_status":"published"})
        for method, args in (
            ("create_product", ("s","sid",payload)), ("publish_product", ("s","sid","id",payload)),
            ("create_post", ("s","sid",{})), ("publish_post", ("s","sid","id",{}))):
            try: getattr(api, method)(*args); raise AssertionError(f"{method} bypassed")
            except RuntimeError: pass
        api._publish_product_transport = lambda s, si, target, business: (
            {"data":{"status":"published"}}, {"request_body_digest":"sha256:"+"3"*64, "response_status":200,
                                                 "endpoint":f"/{s}/products/{target}/update"})
        out = api.mutate_reviewed_product("synthetic-site", "synthetic-site-id", payload, record_path, capability,
                                          target_id="synthetic-target-id")
        assert out["result"]["data"]["status"] == "published"
        assert out["evidence"]["publish_request"]["request_body_digest"].startswith("sha256:")
        # Product business create: reviewed first, then draft+publish; both request evidence retained.
        create_record = copy.deepcopy(record)
        create_record.update({"business_operation":"create", "mutation_phase":"create_and_publish", "target_id":None})
        create_record_path = os.path.join(td, "create-review.json"); write(create_record_path, create_record)
        api._create_product_transport = lambda s, si, business: ({"data":{"id":"new-product-id"}}, {"request_body_digest":"sha256:"+"1"*64, "response_status":200})
        api._publish_product_transport = lambda s, si, target, business: ({"data":{"status":"published"}}, {"request_body_digest":"sha256:"+"2"*64, "response_status":200})
        created_out = api.mutate_reviewed_product("synthetic-site", "synthetic-site-id", payload,
                                                  create_record_path, product_create_capability, target_id=None)
        assert created_out["result"]["data"]["status"] == "published"
        assert created_out["evidence"]["target_id"] == "new-product-id"
        # Draft succeeded but publish ambiguous: expose orphan ID and force reconciliation/no retry.
        api._publish_product_transport = lambda s, si, target, business: (
            None, {"request_body_digest":"sha256:"+"5"*64, "response_status":None})
        ambiguous = api.mutate_reviewed_product("synthetic-site", "synthetic-site-id", payload,
                                                create_record_path, product_create_capability, target_id=None)
        assert ambiguous["reconcile_required"] is True
        assert ambiguous["reconcile"]["target_id"] == "new-product-id"
        assert ambiguous["evidence"]["automatic_retry"] is False

        article = {
            "title":"Synthetic Guide", "slug":"synthetic-guide", "excerpt":"Confirmed synthetic guide.", "order":0,
            "coverImage":{"name":"cover","type":"image","source":"oss","path":"s/cover.jpg"},
            "categories":["article-category"], "tags":[],
            "content":[{"type":"h2","id":"a","children":[{"text":"Confirmed"}]},
                       {"type":"p","id":"b","children":[{"text":"confirmed synthetic fact"}]}],
        }
        # Request spy: evidence digest is computed from the exact raw bytes passed to _req.
        captured = {}
        api_spy = AllinCMS(token="synthetic")
        def spy_req(path, action=None, **kwargs):
            captured.update({"path":path, "action":action, "raw_data":kwargs.get("raw_data")})
            return 200, '1:{"data":{"status":"published"}}'
        api_spy._req = spy_req
        result, request_ev = api_spy._send_content_transport("/synthetic-site/products/id/update", "action-id", {"x":[1,2]})
        assert result["data"]["status"] == "published"
        assert captured["path"] == request_ev["endpoint"] and captured["action"] == request_ev["action_id"]
        assert request_ev["request_body_digest"] == "sha256:" + hashlib.sha256(captured["raw_data"]).hexdigest()
        # Actual private transports must bind the correct endpoint/action and send the digested bytes.
        import allincms_api as _api_constants
        captured.clear(); api_spy._create_product_transport("synthetic-site", "synthetic-site-id", payload)
        assert captured["path"] == "/synthetic-site/products" and captured["action"] == _api_constants.CREATE_PRODUCT
        captured.clear(); api_spy._publish_product_transport("synthetic-site", "synthetic-site-id", "pid", payload)
        assert captured["path"] == "/synthetic-site/products/pid/update" and captured["action"] == _api_constants.UPSERT_PRODUCT
        captured.clear(); api_spy._publish_post_transport("synthetic-site", "synthetic-site-id", "postid", article)
        assert captured["path"] == "/synthetic-site/posts/postid/update" and captured["action"] == _api_constants.UPSERT_POST
        try:
            api_spy._create_post_transport("synthetic-site", "synthetic-site-id", article)
            raise AssertionError("private article create transport bypassed Registry BLOCK")
        except RuntimeError as exc:
            assert "ARTICLE_CREATE_BLOCKED" in str(exc)

        # Article update wrapper uses the same strict boundary with a complete article payload.
        article_record = copy.deepcopy(record)
        article_record.update({"object_type":"article", "slug":article["slug"],
                               "business_payload_digest":gate.payload_digest(article), "target_id":"synthetic-post-id"})
        article_record_path = os.path.join(td, "article-review.json"); write(article_record_path, article_record)
        api._publish_post_transport = lambda s, si, target, business: (
            {"data":{"status":"published"}}, {"request_body_digest":"sha256:"+"4"*64, "response_status":200,
                                                 "endpoint":f"/{s}/posts/{target}/update"})
        article_out = api.mutate_reviewed_post("synthetic-site", "synthetic-site-id", article,
                                               article_record_path, article_capability, target_id="synthetic-post-id")
        assert article_out["result"]["data"]["status"] == "published"
        assert article_out["evidence"]["publish_request"]["request_body_digest"].startswith("sha256:")

        # Integration-style wrappers: real private transport + real authoritative-readback parser;
        # only network I/O and read source are faked.
        def integration_api(business, object_type, target, responses, readback_business=None, list_status="published"):
            test_api = AllinCMS(token="synthetic")
            calls = []
            queue = list(responses)
            def fake_req(path, action=None, **kwargs):
                calls.append({"path":path, "action":action, "raw_data":kwargs.get("raw_data")})
                return 200, queue.pop(0)
            test_api._req = fake_req
            rb = business if readback_business is None else readback_business
            test_api.get_page = lambda path: (200, '1:' + json.dumps({"defaultValues": rb}, ensure_ascii=False))
            resource = "products" if object_type == "product" else "posts"
            test_api.read_lists = lambda site, requested: {"status":200, "data":[{"id":target, "slug":business["slug"], "_status":list_status}]}
            return test_api, calls
        api_int, int_calls = integration_api(payload, "product", "synthetic-target-id",
                                              ['1:{"data":{"status":"published"}}'])
        int_out = api_int.mutate_reviewed_product("synthetic-site", "synthetic-site-id", payload,
                                                  record_path, capability, target_id="synthetic-target-id")
        assert int_out["reconcile_required"] is False
        assert int_out["evidence"]["authoritative_readback"]["business_exact_match"] is True
        assert int_calls[0]["path"] == "/synthetic-site/products/synthetic-target-id/update"
        api_int, _ = integration_api(payload, "product", "synthetic-target-id",
                                     ['1:{"data":{"status":"published"}}'],
                                     readback_business={**payload, "description":"stale"})
        mismatch = api_int.mutate_reviewed_product("synthetic-site", "synthetic-site-id", payload,
                                                   record_path, capability, target_id="synthetic-target-id")
        assert mismatch["reconcile_required"] is True
        api_readback_error, _ = integration_api(payload, "product", "synthetic-target-id",
                                                 ['1:{"data":{"status":"published"}}'])
        api_readback_error.get_page = lambda path: (_ for _ in ()).throw(OSError("readback lost"))
        readback_error = api_readback_error.mutate_reviewed_product(
            "synthetic-site", "synthetic-site-id", payload, record_path, capability,
            target_id="synthetic-target-id")
        assert readback_error["reconcile_required"] is True
        assert "readback_error" in readback_error["evidence"]["authoritative_readback"]
        api_false_success, _ = integration_api(payload, "product", "synthetic-target-id",
                                               ['1:{"data":{"status":"published"}}'])
        api_false_success._req = lambda *a, **k: (500, '1:{"data":{"status":"published"}}')
        false_success = api_false_success.mutate_reviewed_product(
            "synthetic-site", "synthetic-site-id", payload, record_path, capability,
            target_id="synthetic-target-id")
        assert false_success["reconcile_required"] is True
        assert false_success["evidence"]["publish_request"]["response_status"] == 500
        api_malformed, _ = integration_api(payload, "product", "synthetic-target-id",
                                           ['1:{"data":"published"}'])
        malformed = api_malformed.mutate_reviewed_product(
            "synthetic-site", "synthetic-site-id", payload, record_path, capability,
            target_id="synthetic-target-id")
        assert malformed["reconcile_required"] is True
        api_create_malformed, _ = integration_api(payload, "product", "new-product-id",
                                                   ['1:{"data":"new-product-id"}'])
        malformed_create = api_create_malformed.mutate_reviewed_product(
            "synthetic-site", "synthetic-site-id", payload, create_record_path, product_create_capability,
            target_id=None)
        assert malformed_create["reconcile_required"] is True
        assert malformed_create["reconcile"]["natural_key"] == {"slug":"synthetic-product"}
        api_object_id, object_id_calls = integration_api(payload, "product", "new-product-id",
                                                         ['1:{"data":{"id":{"forged":"id"}}}'])
        object_id_create = api_object_id.mutate_reviewed_product(
            "synthetic-site", "synthetic-site-id", payload, create_record_path,
            product_create_capability, target_id=None)
        assert object_id_create["reconcile_required"] is True
        assert len(object_id_calls) == 1
        for bad_site, bad_target in (("bad/site", "synthetic-target-id"),
                                     ("synthetic-site", "bad?target"),
                                     ("../synthetic-site", "synthetic-target-id")):
            try:
                api_int.mutate_reviewed_product(bad_site, "synthetic-site-id", payload,
                                                record_path, capability, target_id=bad_target)
                raise AssertionError("unsafe route segment reached product transport")
            except ValueError as exc:
                assert "safe route segment" in str(exc)
        try:
            api_int.mutate_reviewed_post("synthetic-site", "synthetic-site-id", article,
                                             article_record_path, article_capability, target_id="bad#target")
            raise AssertionError("unsafe route segment reached article transport")
        except ValueError as exc:
            assert "safe route segment" in str(exc)
        # Product create: draft then publish then exact readback.
        api_create, create_calls = integration_api(payload, "product", "new-product-id",
            ['1:{"data":{"id":"new-product-id"}}', '1:{"data":{"status":"published"}}'])
        created_real = api_create.mutate_reviewed_product("synthetic-site", "synthetic-site-id", payload,
                                                          create_record_path, product_create_capability, target_id=None)
        assert created_real["reconcile_required"] is False and len(create_calls) == 2
        # Article update uses posts endpoint/action and exact readback.
        api_article, article_calls = integration_api(article, "article", "synthetic-post-id",
                                                     ['1:{"data":{"status":"published"}}'])
        article_real = api_article.mutate_reviewed_post("synthetic-site", "synthetic-site-id", article,
                                                        article_record_path, article_capability, target_id="synthetic-post-id")
        assert article_real["reconcile_required"] is False
        assert article_calls[0]["path"] == "/synthetic-site/posts/synthetic-post-id/update"
        # Transport exception is ambiguous and forces reconciliation.
        api_error, _ = integration_api(payload, "product", "synthetic-target-id", [])
        api_error._req = lambda *a, **k: (_ for _ in ()).throw(OSError("network lost"))
        transport_error = api_error.mutate_reviewed_product("synthetic-site", "synthetic-site-id", payload,
                                                             record_path, capability, target_id="synthetic-target-id")
        assert transport_error["reconcile_required"] is True
        assert transport_error["evidence"]["automatic_retry"] is False

        # Canonical Registry blocks article.create regardless of local review/capability.
        try:
            api.mutate_reviewed_post("synthetic-site", "synthetic-site-id", article,
                                     article_record_path, capability, target_id=None)
            raise AssertionError("article.create bypassed Registry BLOCK")
        except RuntimeError as exc:
            assert "ARTICLE_CREATE_BLOCKED" in str(exc)

        duplicate = os.path.join(td, "duplicate.json"); open(duplicate,"w").write('{"a":1,"a":2}')
        nonfinite = os.path.join(td, "nan.json"); open(nonfinite,"w").write('{"a":NaN}')
        for path in (duplicate, nonfinite):
            try: gate.load_json_strict(path); raise AssertionError(f"accepted invalid JSON: {path}")
            except ValueError: pass
        assert gate.payload_digest({"x":"é"}) == gate.payload_digest({"x":"e\u0301"})
        assert gate.payload_digest({"x":[1,2]}) != gate.payload_digest({"x":[2,1]})
        for invalid in ({"x": 9007199254740992}, {"x": "\ud800"}, {"x": 1.25}):
            try: gate.payload_digest(invalid); raise AssertionError(f"accepted invalid canonical value: {invalid!r}")
            except (ValueError, UnicodeError): pass
        from unittest.mock import patch
        with patch("content_review_gate.os.path.commonpath", side_effect=ValueError("different drives")):
            assert gate._is_within("C:\\runtime", "D:\\evidence") is False
        print("CONTENT_REVIEW_SELFTEST PASS: supported paths + adversarial negative cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
