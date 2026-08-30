---
doc_id: allincms-site-content-and-aesthetics-spec
title: 新建网站信息完整性与美观规范
description: 从用户资料建一个 AllinCMS 站点前，必须收齐哪些信息、每类内容的字段与质量下限、以及贯穿主题/图片/排版的美观标准
layer: ops
page_type: reference
status: draft
created: 2026-07-03
updated: 2026-07-03
sources: []
confidence: medium
owner: Tony
---

# Site Content & Aesthetics Spec

This is the upstream standard for building a new AllinCMS site from user materials: what information a
complete site needs, the field and quality floor for each content type, and the aesthetics rules that make
the result look professional rather than a data dump. Use it before authoring the source wiki (to know what
to collect and what to fill), during theme/beautification, and at launch QA.

It sits above two existing references and does not duplicate them:

- `official-docs-alignment.md` owns the tutorial-first build sequence, homepage module set, and first content targets.
- `launch-acceptance.md` owns the completion definition, beautification gate, and final visitor QA checklist.

This spec owns: the information-intake completeness checklist, per-type content floors, image/media aesthetics,
and the pre-fill and pre-launch aesthetics gates. When they overlap, those two references win on their topics;
this spec references them rather than restating.

## How To Use

1. Before authoring content, run the **Information Intake Checklist**: mark each item present / derivable-from-source / needs-user-input / deferred. Do not silently skip a required item — either fill it from the source, confirm it with the user, or record an explicit deferral in the source wiki policy fields.
2. While authoring the source wiki, meet the **Per-Type Content Floors** (they are stricter, more editorial versions of the publication-ready validator minimums, not a replacement for them).
3. For images, follow the **Image & Media Aesthetics** rules — this is where most "looks cheap" problems come from and the user has flagged aesthetics as high priority.
4. Before theme/beautification and before launch, run the **Aesthetics Gate** checklist and fold the visual items into `launch-acceptance.md` final QA.

## Information Intake Checklist

A complete B2B product site needs the following. Each row lists the field(s) it maps to in the source
wiki / package, whether it is required, and how to source it.

### Brand & identity (required)

- **Site name** — `site.siteName`. Use the real company/brand name.
- **Site description / value proposition** — `site.siteDescription` (≥ 40 chars). One or two sentences on what the company makes and for whom.
- **Language & industry** — `site.language`, `site.industry`. Set language to the audience's language (English for international B2B), not the source file's incidental language.
- **Logo** — `siteInfo.logoPolicy`. A real logo (wordmark or mark) is required for a polished site. If the source has a logo (e.g. a catalog wordmark), record that it will be extracted and uploaded via PicGo; if none exists, flag `needs-user-input`. Never leave the default theme logo.
- **Brand color / palette** — recommended. Capture 1 primary + 1 accent color for theme accents and CTAs. If the source has brand colors (logo, catalog), derive from them; otherwise pick an on-industry palette and record it for user confirmation.
- **Tagline** — recommended. A short positioning line for the hero.

### SEO & metadata (required)

- **SEO title** — `siteInfo.draftSeoTitle`. Brand + primary keyword, aim ≤ 60 characters.
- **SEO description** — `siteInfo.draftSeoDescription` (≥ 40 chars, aim ≤ 160). Keyword-bearing, human, not stuffed.
- **Per-item titles & slugs** — every product/post/page has a descriptive title and a kebab-case, keyword-bearing slug.

### Navigation & information architecture (required)

- **Primary navigation** — `navigation.items`. Home, Products, Articles (`/posts` is required when posts exist), About, Contact at minimum.
- **Footer** — recommended: contact, product links, legal, copyright. Handled at theme/beautification.
- **Taxonomy** — `taxonomyPlan`. 2–3 product categories, each with ≥ 2 products (per `official-docs-alignment.md` first content targets); a small set of consistent tags.

### Homepage modules (required — see `official-docs-alignment.md`)

Header / Banner(hero) / category / product / news / footer. This spec adds the aesthetic requirements for each (below); the module set and order are owned by `official-docs-alignment.md`.

### Products (required, ≥ 2 per category)

Per product (`contentPlan.products[*]`):

- **name, slug, short description** (≥ 40 chars) — required.
- **body** — ≥ 100 chars, and editorially ≥ 2–3 short paragraphs covering what it is, how it is built / key differentiators, and applications / how to buy.
- **specs** — a structured spec list/table (frequency, impedance, material, options, part-number scheme for RF-type catalogs; adapt fields to the domain).
- **categories** (≥ 1) and **tags**.
- **cover image** — required for a polished catalog; plus optional gallery. See Image aesthetics.
- **ordering / CTA** — how to buy or request a quote (inquiry form link).

### Articles / posts (required, ≥ 3 for first launch)

Per post (`contentPlan.posts[*]`):

- **title, slug, excerpt** (≥ 40 chars).
- **body** — ≥ 140 chars, editorially ≥ 3 short paragraphs; genuinely useful, source-backed, not filler.
- **category, tags**; optional cover image, author, date.

### Static pages (required)

- **Home** — hero + value prop + featured categories/products + article teaser + CTA.
- **About** — company story, capabilities/R&D, trust signals (years, certifications, scale).
- **Contact** — location, inquiry form, response expectation. **Do not put real emails/phones in the local wiki** (PII); they are entered on the live site or captured in `siteInfo`/form config.
- **Legal (recommended for a public site)** — privacy policy, terms. Flag `needs-user-input` if not provided.

### Lead capture & contact (required)

- **Inquiry/contact form** — `contentPlan.forms`. Fields sized to the domain (name, company, email, product of interest, requirement, message). Form creation on AllinCMS is a later captured browser action.
- **Sales contact channels & PII** — real address may appear in copy; real email/phone/social are PII: confirm with the user and enter on the live site, never store in the local wiki.

### Media (required for a catalog site)

- **Product cover images**, **homepage hero**, optional **category thumbnails** and **product galleries**.
- **Sourcing & hosting** — images come from source files (or user-provided/public URLs after confirmation), are uploaded via PicGo to an image host, and body/product references use the hosted URL, never a local path. See Image aesthetics and `source-files-to-site-package.md` (Media Images Via PicGo).

### Trust & conversion (recommended)

Certifications, years in business, capability list, notable clients/industries, and clear CTAs. Pulls conversion up and is cheap to add from an About/company section.

## Per-Type Content Floors

These are editorial floors on top of the `validate_source_site_package.py` publication minimums
(page body ≥ 120, product desc ≥ 40 / body ≥ 100, post excerpt ≥ 40 / body ≥ 140). Meeting only the
validator minimum is not the same as a good site.

- **No placeholders, no lorem, no "TBD/TODO/requires review".** Every string is real, source-backed copy.
- **Products:** 3-paragraph body (what / how-built / applications-and-buying) + a real spec list + ≥ 1 category + a cover image need.
- **Posts:** 3-paragraph, genuinely useful article; not a product ad restated.
- **Pages:** each section has a meaningful heading and a scannable paragraph; homepage leads with a value proposition and a CTA.
- **Consistency:** one name per concept across the whole site; consistent product-name and slug patterns; consistent tag vocabulary.

## Professional Copy Standard (products & articles)

> Upstream: `source-material-norms.md` organizes the per-product/article norms by the visitor's decision journey (relevance → fit → differentiate → trust → act) and gives the acceptance checklists + input-hygiene rules for turning a raw blob into conforming records. This section is the writing structure that implements those norms.

The floors above are the minimum. To reach **professional grade** — copy an expert in the buyer's field would respect, not marketing filler — follow the editorial structure below. This pattern was authored and verified live on a from-PDF RF-catalog build (products + 3 articles rendered professionally on the public frontend), so it is a proven default, not a proposal. Voice = the global 客户面写作标准: natural, expert-to-expert, specific numbers over adjectives, no greasy marketing-speak ("赋能/打通/闭环", "world-class", "cutting-edge"), no "Hope this finds you well" filler.

### Product description (professional structure)

- **Name** — descriptive + the one key differentiator (e.g. "P-TEST High-Performance Phase-Stable RF Test Cable Assembly"), not a bare SKU.
- **Short description (≥ 40 chars)** — one line: what it is + who it's for + the headline spec/benefit.
- **Body (3 paragraphs):**
  1. **What it is & who it's for** — the product in one positioning sentence, the target user/use, and the frequency/grade envelope. Lead with the buyer's need, not the company.
  2. **Construction & differentiators** — materials, build, and the 2–3 things that actually make it better, each tied to a real, measurable property (phase stability, VSWR, mating-cycle life, bend radius). Concrete numbers, not "high quality".
  3. **Applications & how to order** — where it's used (production/metrology/R&D, specific test scenarios) and the ordering/part-number scheme or a quote CTA.
- **Specs** — a structured key/value list (frequency, impedance, conductor/shell material, connector series, armor/options, part-number scheme). Adapt fields to the domain.

### Article / post (professional structure)

- **Title** — specific and insight-bearing, promising one useful idea ("Phase Stability in RF Test Cables: Why It Quietly Decides Your Measurement Uncertainty"), not "Our Products" or a keyword stuff.
- **Excerpt (≥ 40 chars)** — the single sharp insight in one sentence.
- **Body (≥ 3 paragraphs, genuinely useful — teach, don't sell):**
  1. **Concrete pain hook** — open on the reader's real, recognizable problem/scene (the drift they see on the bench), not on the company.
  2. **Mechanism / tradeoffs** — explain *why* it happens and the tradeoffs the reader must weigh; teach something they can use even if they never buy.
  3. **How the range maps** — connect the ideas to the product series *by name*, as the natural answer, without a hard sell.
  4. **Payoff + soft CTA** — what they gain, then a low-friction next step ("send us your instrument ports and test conditions and we'll recommend a configuration").
- Every claim is source-backed; no fabricated specs, benchmarks, customers, or numbers. An article is a buying-decision aid, not a product ad restated.

### Professional-copy adversarial checks

- Would a specialist in this field find it credible and specific, or does it read as generic marketing? Cut any sentence that could appear on any competitor's site unchanged.
- Every number, spec, and claim traces to the source material — no invented figures.
- Product body answers what / how-built / where-used; article body teaches before it sells.
- No placeholder, no restated product ad masquerading as an article, no marketing clichés.

## Image & Media Aesthetics (high priority)

Most "looks cheap" outcomes come from images. Treat image quality as a first-class gate, not an afterthought.

### Product & catalog images

- **Clean subject, clean background.** Product shots use a white or neutral, consistent background. When cropping from a catalog/scanned PDF, crop tight to the product and remove page text, borders, part-number tables, and page numbers so the image is the product, not a screenshot of a page.
- **Consistent aspect ratio & size.** Pick one ratio for product covers (1:1 or 4:3 recommended) and use it for every product so cards line up. Target ≥ 800 px on the long edge; upscale carefully if the source is small, and prefer a cleaner re-shot/vector if available.
- **Consistent style family.** Same background, camera angle and finish across products so the product set reads as one coherent brand, not a mismatched mix.
- **No clutter or watermarks.** No overlaid catalog text, no competitor marks, no low-quality JPEG artifacts where avoidable.
- **Alt text for every image.** Descriptive, keyword-aware alt text (accessibility + SEO).
- **Hosted, never local.** Every published image is a PicGo-hosted URL; a local path on a live page is a defect.

### Hero & homepage imagery

- **Hero image** is high-quality, on-brand, correctly sized to the banner (no stretching/pixelation), with legible headline overlay contrast.
- **Category thumbnails** (if used) share one style and ratio.

### Cropping-from-PDF workflow (for image-only catalogs)

1. Render pages at sufficient DPI; identify the product region on each page.
2. Crop tightly to the product; remove surrounding page chrome (text, tables, borders, page numbers).
3. Normalize: consistent background where feasible, consistent aspect ratio, adequate resolution.
4. Name files by product slug; upload via `upload_media_via_picgo.py`; wire hosted URLs into the product cover/gallery.
5. Visually verify each cropped image before publish — a bad crop is worse than no image.

## Typography, Color & Layout Aesthetics

- **Type:** 1–2 font families; a clear hierarchy (H1 > H2 > body); comfortable line length and line-height; short, scannable paragraphs. No walls of text.
- **Color:** brand primary + accent used consistently for CTAs and highlights; neutral body text; sufficient contrast (target WCAG AA).
- **Spacing & grid:** generous whitespace; aligned elements; consistent section rhythm; a uniform product-card design (image + name + one-line desc + key spec + CTA, equal heights).
- **Consistency:** consistent button, link, and spacing styles site-wide; consistent header/footer on every page.
- **Responsive:** verify layout on a narrow (mobile) viewport, not just desktop; images and nav must adapt.
- **No starter residue:** remove all default-theme sample pages/products/blocks; nothing shipped should be template filler.

## Aesthetics Gate (run before beautification and before launch)

Pre-fill (before authoring): intake checklist complete or every gap explicitly resolved; brand assets (logo, palette) sourced or flagged; image plan defined per product.

Pre-launch (fold into `launch-acceptance.md` final QA):

- [ ] Logo present (not default); favicon set if supported.
- [ ] Consistent header/footer on every page; footer has contact + legal + copyright.
- [ ] Homepage above-the-fold shows value prop + CTA; all required modules present and populated (no empty module).
- [ ] Every product card uses the same ratio image, same layout, equal height; no broken/local images; alt text present.
- [ ] Product detail: hero/gallery, styled spec table, applications, related products, inquiry CTA.
- [ ] Typography hierarchy and brand color consistent; adequate contrast; no walls of text.
- [ ] Mobile viewport verified for home, one product detail, one article, contact.
- [ ] No placeholder/lorem/starter content anywhere; visitor-style click-through of every nav item passes.
- [ ] Every image is a hosted URL; no local paths; images are clean crops, not page screenshots.

## Mapping To Skill Artifacts

- Information intake → author into the `allincms_source_wiki` (`site`, `siteInfo`, `navigation`, `taxonomyPlan`, `pages`, `products`, `posts`, `forms`, `media`, `mediaPolicy`, `contactFormPolicy`, `contentGoals`), then `build_source_site_package.py` + `validate_source_site_package.py --require-publication-ready`.
- Missing/uncertain items → `needs_user_confirmation` in the relevant policy field, or an accepted deferral at confirmation; never a fabricated fact.
- Images → crop from source, `upload_media_via_picgo.py` (dry-run then `--confirm-upload` after approval), wire hosted URLs into products; body/product references must be hosted URLs.
- Aesthetics enforcement points → content authoring (this spec), theme/beautification (`launch-acceptance.md` Beautification Gate + `official-docs-alignment.md` modules), and final visitor QA (`launch-acceptance.md` Final QA + the Aesthetics Gate above).

## Adversarial Checks

- A site that passes the publication-ready validator can still be ugly or incomplete; the validator floors are necessary, not sufficient — run the intake and aesthetics gates too.
- Do not treat a cropped page screenshot as a product image; it must be a clean, consistent crop of the product.
- Do not store real emails/phones/social handles or images bytes in the local wiki; PII and media stay out of the skill and out of the local wiki.
- Do not leave any default-theme starter content; a nonblank frontend full of template products is not a completed site.
