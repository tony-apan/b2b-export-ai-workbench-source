---
doc_id: allincms-official-docs-alignment
title: AllinCMS 官方教程对齐
description: 按 AllinCMS 官方教程执行建站、内容、首页模块和上线检查的主流程
layer: ops
status: draft
created: 2026-07-01
updated: 2026-07-03
page_type: reference
sources: ["https://www.allincms.com/docs", "https://www.allincms.com/docs/quickstart/create-site", "https://www.allincms.com/docs/quickstart/site-build-flow", "https://www.allincms.com/docs/quickstart/site-settings", "https://www.allincms.com/docs/content/product-categories", "https://www.allincms.com/docs/content/add-products", "https://www.allincms.com/docs/content/add-posts", "https://www.allincms.com/docs/pages/homepage-basics", "https://www.allincms.com/docs/pages/create-page", "https://www.allincms.com/docs/content/product-module", "https://www.allincms.com/docs/content/homepage-featured-products", "https://www.allincms.com/docs/launch/launch-checklist"]
confidence: high
---

# Official Docs Alignment

Use this reference before from-scratch site builds, broad feature walkthroughs, homepage/module work, launch QA, or any discussion about whether JSON/Server Action submission should replace UI operation.

## Current Docs Refresh

When the user asks to follow or correct against the official tutorial, refresh the relevant pages before changing the skill or mutating the backend. As of 2026-07-01, the checked docs HTML was fetched directly from `www.allincms.com/docs` and the checked pages state this core route:

```text
docs home -> create site -> open frontend -> check default content -> product categories -> products -> posts -> homepage modules -> extra pages -> site settings/domain/form/media as needed -> launch checklist
```

Do not use old memory, prior probe evidence, or a captured Server Action as a substitute for this refresh when the user explicitly points at the docs.

Verified docs pages in this refresh:

```text
/docs/quickstart/create-site
/docs/quickstart/site-build-flow
/docs/content/product-categories
/docs/content/add-products
/docs/content/add-posts
/docs/pages/homepage-basics
/docs/pages/create-page
/docs/quickstart/site-settings
/docs/content/product-module
/docs/content/homepage-featured-products
/docs/launch/launch-checklist
```

## Authority Rule

Official docs are the operating path. Browser probing, request capture, and JSON replay are supporting tools for verification and acceleration only.

```text
Do not start by randomly exploring backend controls.
Do not create duplicate themes, pages, categories, products, or posts when default content can be edited.
Do not use a captured JSON action unless it belongs to the current docs-required step.
Do not claim success from backend save alone; public frontend click-through is required.
```

If docs and live backend differ, record both: docs define the intended sequence, live browser defines the current implementation details and payload shape.

## Tutorial Stop Gates

These gates come directly from the current official tutorial and must override exploratory momentum:

```text
after creating a site: open the public site from the site card before entering deep backend work
normal template page: stop theme creation; edit existing pages/content
404 or blank: inspect dashboard, themes, homepage selection, enabled state, page count, and routes before content expansion
existing theme with page count: do not create another theme; open Pages or Design
theme missing or pages = 0: create a theme with preset 默认, not 空白, unless the user asked for a blank build
theme created: enable it, then open the public frontend again
homepage work: do only after categories, products, and posts are sufficient
product module work: check default `Category Showcase` and `Featured Product List` before deleting/replacing; use `Recommended Products` only when a grid/uniform image display is needed
new static page: create route first, create page second, bind route, enable page, then verify the public URL
launch claim: backend save/publish is insufficient; open public pages, click links, and check mobile when public quality is claimed
```

If any stop gate fails, record it as the current blocker and do not move to the next tutorial stage just to keep exploring.

## First-Build Sequence

Follow this order unless the user explicitly narrows the task:

```text
1. Create or select the site.
2. Open the public frontend first.
3. If a normal template page renders, edit the existing theme/pages/content.
4. If frontend is 404 or blank, inspect theme, enable state, Home page, homepage selection, and route state before content expansion.
5. Product categories: keep or edit default categories; create only when missing or insufficient.
6. Products: keep or edit default products; create only what is needed to reach the first content target.
7. Posts: keep or edit default posts; create only what is needed to reach the first content target.
8. Homepage modules: Header, dropdowns, banner, category showcase, featured products, featured news, footer.
9. Extra pages: create only for real needs such as Cases, OEM, Services, or Solutions.
10. Domain, tracking, forms, contact details, media, mobile, and launch QA.
```

## Page-To-Action Map

Use this map to decide which reference and browser stage applies:

```text
/docs/quickstart/create-site:
  login, create site, open frontend, normal-template stop, 404/blank recovery, default theme, enable theme, reopen site
/docs/quickstart/site-build-flow:
  default-content-first rule, first-launch counts, content-before-homepage rule
/docs/content/product-categories:
  inspect/edit categories first, 2-3 main categories, clean slug, cover policy, copy real frontend category links
/docs/content/add-products:
  inspect/edit template products first, at least 2 per main category, clean slug, media policy, save/publish, frontend detail check
/docs/content/add-posts:
  inspect/edit template posts first, 3 posts, title/slug/excerpt/body/cover, Markdown paste verification, frontend list/detail check
/docs/pages/homepage-basics:
  Header, Dropdown, Banner, Category Showcase, Featured Product List, Featured News List, Footer
/docs/content/product-module:
  check default Category Showcase and Featured Product List; Recommended Products can replace Featured Product List for uniform grids; Detail Page must be /products
/docs/content/homepage-featured-products:
  sorting is not enough; product must be published and clickable on desktop/mobile
/docs/pages/create-page:
  route -> page -> bind route -> enable page -> public URL; default pages should be edited, not duplicated
/docs/quickstart/site-settings:
  favicon and notification email; test form email when forms are in scope
/docs/launch/launch-checklist:
  content, navigation, products/posts, forms/contact, domains/HTTPS, images, mobile
```

## First Content Targets

Use these as the default "good enough for first launch" targets:

```text
product categories: 2-3 main categories
products: at least 2 representative products per main category
posts/articles: at least 3 basic posts
homepage: header, banner, category showcase, featured products, featured news, footer all click through
routes: Home, Products, Posts/News, About Us, Contact Us open without unexpected 404s
```

If the temporary site is intentionally smaller, mark the omitted target as a demo-scope deferral. Do not silently treat a smaller site as complete.

## Content Checks

Categories:

```text
Inspect existing categories first.
Prefer editing existing 2-3 categories.
Slug must be meaningful English, not numeric/test/pinyin placeholders.
If categories are used on homepage, cover images should be provided or explicitly deferred.
Copy real frontend category links from /products after clicking the category; do not guess.
If /products is a static marketing page and does not expose CMS category filters, backend categories are only setup progress; the frontend category-link acceptance item is still incomplete.
```

Products:

```text
Check categories before products.
Inspect template products before creating new ones; edit usable template products first.
First launch target is at least 2 products per main category.
Each first-launch product should have name, slug, short description, category, image/media policy, status, and frontend detail proof.
Refresh or normalize slug after changing product name; do not leave numeric/random slug values.
Product body/specs/media are separate proof points; one does not prove the others.
The product module Detail Page must point to /products before product cards can be considered clickable.
Click public product cards or detail URLs after publish; a backend published row alone is not enough.
Remove or replace Untitled Product, test, and template-test content before launch.
```

Posts:

```text
Check existing posts first.
Inspect template posts before creating new ones; edit usable template posts first.
First launch should have 3 posts with title, slug, excerpt, non-empty body, cover-image policy, and published status.
The docs allow pasting Markdown into the editor, but Markdown source is not proof of rendered bold/list/table/code support; verify the editor result and public DOM for the structures used.
If cover images are omitted on a temporary demo, record an explicit no-cover acceptance.
The article/news module Detail Page must point to /posts before post cards can be considered clickable.
Click public post list and detail links after publish; a backend published row alone is not enough.
Remove or replace Untitled Post, test, and template-test content before launch.
```

Homepage modules:

```text
Do not rebuild the homepage from scratch when default modules exist.
Header links must open real pages.
Dropdown category links should be copied from real frontend category URLs.
Banner text must say what the business sells, not generic welcome copy.
Category Showcase depends on categories and category covers.
Featured Product List or Recommended Products depends on published products and Detail Page = /products.
Featured News List depends on published posts and Detail Page = /posts.
Footer contact details must be real or explicitly deferred.
Do not confuse product-list page blocks with homepage product modules: `Full Product List (Filtered)` can make `/products` render CMS product cards, but the docs homepage path still expects Category Showcase plus Featured Product List or Recommended Products on Home.
```

Extra pages:

```text
Do not create duplicate Home, Products, Posts, About Us, or Contact Us pages when default pages exist.
Create new pages only for real needs such as Cases, OEM, Services, or Solutions.
Route must be meaningful English, not Chinese/random/test.
Public completion requires route exists, page exists, route bound, page enabled, non-empty design or accepted placeholder, and frontend URL not 404.
Add menu/button links only after the public URL works.
```

Site settings, forms, media, and domains:

```text
Favicon/logo/media need real image proof or explicit deferral.
Notification email and public contact channels are user-confirmed fields unless an accepted source document provides them.
If forms are in scope, submit a test form and verify notification behavior; do not mark forms complete from field presence alone.
Real custom domains require AllinCMS domain row, DNS/CNAME, HTTPS, and expected DNS/SSL wait; demo subdomains can be accepted as out of scope.
```

## JSON Acceleration Gate

JSON/Server Action submission is useful only after these are all true:

```text
the action is part of the official-docs step currently being executed
the exact module/action was captured from the current site/version
payload shape and required IDs are known
volatile headers are handled or the UI fallback is safer
backend state changed as expected
frontend state proves the public effect when the action is public
rollback/cleanup or explicit deferral is recorded
```

Examples:

```text
Captured create blank theme != permission to create a default theme.
Captured create page != proof of design save, publish, enable, route bind, or menu link.
Captured product save != proof of post save.
Captured post publish != proof that detail route immediately renders; verify with retry.
```

## Launch QA

Run final QA like a visitor:

```text
open homepage
click navigation and footer links
open /products and product detail pages
open /posts and post detail pages
open About and Contact
check forms/contact paths
submit or explicitly defer test forms when forms/contact are in scope
check product/post images or accepted no-image/no-cover deferrals
check desktop and mobile when public launch quality is claimed
check no Untitled/test/测试 records appear
check domain/DNS/SSL only when a real domain is in scope
```

Backend "saved" or "published" is never enough by itself.
