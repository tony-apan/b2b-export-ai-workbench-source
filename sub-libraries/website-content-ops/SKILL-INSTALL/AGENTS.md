# AGENTS.md — allincms-bulk-content-upload

This directory (`SKILL-INSTALL/`) is the installable **portable router** merged into the mother library on 2026-08-30 (standalone repository archived); it is not the editable canonical Website Content Operations source — the sibling library root is.

## Read before acting

1. Read [`SKILL.md`](SKILL.md).
2. Resolve the runtime with `scripts/resolve_website_content_ops_root.py`.
3. Read the current step's SOP, Schema, validator, and AllinCMS Adapter from the resolved `<SUB_LIBRARY_ROOT>`.

Resolution precedence is: explicit full source checkout, environment full source checkout, upward/sibling full source discovery. The digest-verified `vendor/website-content-ops-runtime` snapshot tier is **retired pending the dist pipeline** and is no longer distributed; if no full source checkout validates, stop with `CANONICAL_WEBSITE_CONTENT_OPS_ROOT_REQUIRED`. Never fall back to historical payloads, routes, UI workflows, or retired helpers.

## Authority

```text
validated full canonical source checkout, when supplied
> immutable bundled runtime generated from a recorded canonical commit
> this host-routing Skill
> supplemental/historical references and scripts
```

The canonical package owns field contracts, interface discovery, mutation semantics, exact authorization validation, tests, and evidence boundaries. The bundle distributes allowlisted committed bytes, including the locked Node dependency descriptors and local self-test closure; maintainers must rebuild it with `scripts/build_bundled_runtime.py`, never hand-edit it or create a second source of truth. `install.sh` must finish dependency installation and self-tests before it creates any Skill link.

## Non-negotiable boundaries

- User sources and current CMS snapshots are run inputs; examples are never current facts.
- Bind source bytes/snapshots, rights/clearance/freshness, extraction artifacts/units, claims, desired fields, exact identity, current fingerprint, and diff before mutation.
- Customer values and deployment interfaces are dynamic. Schema meanings, Plan A/Plan B, authorization binding, maximum TTL, strict serial execution, no-blind-retry, publication effects, and qualification evidence remain canonical invariants.
- Default to read-only. One unchanged ordered plan may be authorized once; the controller revalidates the same context immediately before every request. Any drift or ambiguity stops mutation.
- Remote mutations require current-deployment `live_verified_current_deployment` capability. Do not upgrade create-site or product maturity from bundle integrity.
- Customer facts and live evidence belong only in the bound `customer-runtime/`; credentials never belong in plans, repositories, bundles, or logs.
- Do not create a second source of truth by restoring retired `Operating Rule`, `Workflow`, `Browser Paths`, `Probe Rules`, or `Payload Rules` sections to `SKILL.md`.
- Bundle PASS proves local byte integrity only; dependency/self-test PASS additionally proves the installed local runtime can load its locked tools. Neither proves login, authorization, remote CMS truth, release, SEO, inquiry, conversion, Stable, or production readiness.

When maintaining this repository, keep changes narrow, validate full-source and bundled-runtime routes, and distinguish local PASS from public availability. Commit, push, tag, or publication still require explicit owner authorization.
