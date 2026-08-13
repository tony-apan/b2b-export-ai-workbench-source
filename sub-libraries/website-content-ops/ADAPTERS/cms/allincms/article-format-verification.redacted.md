---
title: "AllinCMS Article Format Verification (Redacted)"
description: "去站点化记录 13 个文章正文格式候选的接口、后台回读、编辑器重开和前台验收结论。"
type: "evidence"
status: "Working"
owner: "AI"
created: "2026-07-30"
last_updated: "2026-07-31"
sources: ["Authorized private runtime experiment 2026-07-30", "Authorized redacted existing-article optimization and publish acceptance 2026-07-31"]
related: ["article-content-formats.mjs", "article-operations-contract.json", "article-operations.md"]
visibility: "public"
redaction_status: "safe-to-publish"
---
# AllinCMS Article Format Verification (Redacted)

## Scope

This report generalizes one authorized, strictly serial current-deployment experiment. Private evidence remains under:

```text
<PRIVATE_RUNTIME_ROOT>/evidence/article-format-test-20260730/
```

The public record intentionally omits the real site key, site/object IDs, action IDs, router tree, deployment fingerprint, cookies, URLs and full request payloads.

## Result matrix

| Candidate | API response | Exact backend Slate readback | Editor reopen | Frontend | Verdict |
|---|---:|---:|---:|---:|---|
| `h3` | PASS | PASS | PASS | PASS | **verified** |
| `bold` | PASS | PASS | PASS | PASS | **verified** |
| `italic` | PASS | PASS | PASS | PASS | **verified** |
| `underline` | PASS | PASS | PASS | PASS | **verified** |
| `strikethrough` | PASS | PASS | PASS | PASS | **verified** |
| `inline-code` | PASS | PASS | PASS | PASS | **verified** |
| `link` | PASS | PASS | PASS | PASS | **verified** |
| `bulleted-list` | PASS | PASS | PASS | PASS | **verified** |
| `numbered-list` | PASS | PASS | PASS | PASS | **verified** |
| `blockquote` | PASS | PASS | PASS | PASS | **verified** |
| `divider` | PASS | PASS | PASS | PASS | **verified** |
| `table` | PASS | PASS | PASS | PASS | **verified** |
| `code-block` tested shape | PASS | PASS | **FAIL** | not published | **unsupported-current-shape** |

Summary: **12 verified, 1 unsupported-current-shape, 0 not-tested**. Paragraph, H2 and body image were retained as verified baseline nodes but were not part of the 13 candidate count.

## Code-block recovery boundary

The tested code-block shape returned the expected Server Action response and matched the exact backend readback. That was not sufficient: reopening the editor failed. The run therefore restored the previous last-known-good Slate content, reopened the editor successfully, and excluded the code block from the published payload.

Policy:

```text
API 200 + backend persistence + editor reopen FAIL
=> restore last-known-good
=> do not publish the tested shape
=> retain unsupported-current-shape until a newly approved isolated shape test passes all gates
```

## Frontend acceptance

The final article passed fresh list and detail navigation. Desktop and a 390 × 844 mobile viewport had no document-level horizontal overflow. The table, images, lists, blockquote and inline code remained within the viewport. Exact inline elements rendered as `strong`, `em`, `u`, `s` and `code`; the image returned anonymous HTTP 200, `image/webp`, valid WebP magic bytes and decoded to its expected dimensions.

## Canonical implementation

- `article-content-formats.mjs` owns the 12 verified canonical Slate examples and deterministic Markdown conversion profile.
- `article-operations.mjs` re-exports that profile so article callers have one Adapter entrypoint.
- `article-operations-contract.json` is the machine-readable matrix and gate contract.
- `article-operations.test.mjs` blocks code fences, all 4+-space/tab indented code, body H1, Markdown images that bypass the image-binding companion, unsupported raw HTML, unsafe links, header-only/aligned/malformed tables and unsafe ID prefixes before any article request.

## Boundary

This is current-deployment and tested-shape evidence. It does not prove every Slate variant, arbitrary nested Markdown, raw HTML, another theme, another deployment, future editor versions, cross-site behavior, or production stability. The code-block tested shape remains a publication BLOCK, not a warning that callers may override.

## Existing-article B2B optimization acceptance (2026-07-31)

A separate authorized run updated one existing English B2B technical article exactly once and published it exactly once. It reused existing taxonomy and media and performed no create, upload, delete, cleanup or cross-site operation. The final article used 59 top-level Slate nodes with 7 H2 headings, 8 H3 headings, one table, one blockquote, two inline images and two internal links. Exact backend readback, editor reopen, published status, desktop rendering and 390 × 844 mobile rendering passed.

The update request became ambiguous after the browser CDP wait timed out. The request was **not resent**. After a bounded wait, a read-only editor/list reconciliation proved the new title, excerpt, taxonomy, 59-node content digest and draft state had persisted; only then did the single authorized publish request proceed. This establishes the recovery rule:

```text
request may have started + client wait timed out
=> do not retry the mutation
=> wait within the frozen plan
=> perform exact read-only reconciliation
=> continue only if the intended state is proven
```

The responsive content layer passed, but formal technical SEO did not. The observed page had an English article with a non-English document `lang`, no canonical link and no Article JSON-LD. In addition, both inline Slate image nodes retained non-empty `alt` strings in the CMS payload while the frontend renderer emitted empty `alt` attributes. That mismatch is a renderer failure, not evidence that the article payload omitted alt text. It requires a separate frontend change and new authorization; repeating the article update is forbidden as a remediation.

Long-page CDP screenshots repeated the sticky header during image stitching. Native viewport captures and DOM geometry showed one document with no horizontal overflow, so the stitched full-page image is retained only as a capture artifact, not as acceptance evidence.

Layered verdict:

- article content optimization: **PASS**;
- backend persistence and publish: **PASS**;
- responsive content rendering: **PASS**;
- formal technical SEO: **BLOCK**;
- inline image alt rendering: **BLOCK**.

This single current-deployment sample proves that verified rich-text nodes and real inline images can coexist in one published article when manually assembled and fully reconciled. It does not prove a generalized Markdown-plus-image composition API, another theme/deployment, search ranking, factual expert approval or Stable production readiness.
