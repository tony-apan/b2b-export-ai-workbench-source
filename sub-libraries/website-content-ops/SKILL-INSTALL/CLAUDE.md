# CLAUDE.md — allincms-bulk-content-upload

Claude Code entry point:

1. Read [`SKILL.md`](SKILL.md); it is the portable routing and host-orchestration contract.
2. Follow [`AGENTS.md`](AGENTS.md).
3. Resolve `<SUB_LIBRARY_ROOT>` and treat its SOP, Schemas, validators and AllinCMS Adapter as execution truth.

Invoke this Skill as `$allincms-bulk-content-upload`. Prefer a validated full canonical source checkout when supplied; otherwise use the digest-verified bundled runtime. If neither validates, return `CANONICAL_WEBSITE_CONTENT_OPS_ROOT_REQUIRED`; do not use historical references/scripts as an alternate implementation.
