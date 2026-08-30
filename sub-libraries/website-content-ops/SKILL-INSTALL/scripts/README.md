# Scripts authority boundary

Runtime routing entry:

- `resolve_website_content_ops_root.py` — prefers a validated full canonical checkout, then verifies the bundled runtime manifest, every immutable file digest, internal symlink absence, and installer-produced dependency-ready marker.

Bundle maintenance and local checks:

- `build_bundled_runtime.py` — maintainer-only generator; reads allowlisted bytes from an exact committed canonical Git revision and atomically rebuilds `vendor/website-content-ops-runtime`, including locked Node dependency descriptors, Registry validators and the local test closure but never `node_modules`.
- `test_resolve_website_content_ops_root.py`
- `audit_skill_hygiene.py`
- `audit_test_entrypoints.py`

The resolver imports no local legacy helper. The bundle builder never executes CMS operations and must not read dirty working-tree bytes. Maintenance checks do not execute CMS operations. All other scripts in this directory are legacy host helpers, validators, simulations, or historical workflow tooling retained for compatibility and evidence review. They are non-authoritative and inactive unless the resolved runtime explicitly delegates to one by exact path and contract. Their existence does not prove that a current AllinCMS interface is supported.

Do not execute a legacy mutation helper merely because its filename matches a requested action. A real CMS mutation must first pass the resolved Source Extraction and Content Operation Plan contracts, current-deployment capability discovery, exact authorization binding, and the current AllinCMS Adapter entry. If current routing does not explicitly delegate to a helper, treat it as non-authoritative.
