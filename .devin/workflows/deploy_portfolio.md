---
description: Deploy the John Eldridge portfolio site to Cloudflare Pages
---

# Workflow — Deploy Portfolio

Project root: `d:\Work\Portfolio` (its own git repo, independent of the
UnrealWrestling project).

**Live URL:** https://john-eldridge-portfolio.pages.dev/

## ⚠️ Read this before doing anything

**Pushing to GitHub does NOT deploy this site.**

The Cloudflare Pages project is **direct upload** — it is not connected to
the git repo. Confirm any time with:

```powershell
npx wrangler pages project list
```

It reports `Git Provider: No` for `john-eldridge-portfolio`. GitHub is only
a code backup. Deploying is always a separate, manual step.

Do **not** look for this on GitHub Pages, Vercel, or Netlify. It is on
**Cloudflare Pages**.

## Facts

| Thing | Value |
|-------|-------|
| Host | Cloudflare Pages (direct upload) |
| Project name | `john-eldridge-portfolio` |
| Production branch | `main` — any other value gives a preview URL |
| Cloudflare account ID | `bcec09abf1e749ac5cf7b7417983a073` |
| Git remote | `github.com/Unreal-Wrestling/john-eldridge-portfolio` |
| Local branches | `main` and `master` both exist; keep them in sync |

## Deploy

// turbo
1. Run from `d:\Work\Portfolio`:

```powershell
npm run deploy
```

`deploy.ps1` runs `build.py`, then uploads `dist/` to the `main` production
branch and verifies the live site with ASCII sentinel checks.

For a preview URL that leaves the live site alone: `npm run deploy:preview`

## What the build does

`build.py` generates `dist/` from source:

- Copies the legacy single-page site (`index.html`, `styles.css`,
  `script.js`, `Artboard *.png`) verbatim
- Generates `/work/` (searchable project index) and `/work/<slug>/` pages
  from `projects/<slug>/project.md` plus that folder's images
- Resizes every image to full (1800px) and thumb (800px) variants
- Writes `sitemap.xml` and `robots.txt`
- **Fails the build** if any file exceeds 25 MiB or the site exceeds 20,000
  files — the two Cloudflare Pages limits

Only `dist/` is uploaded, so the `.mp4` masters in the project root (one is
160 MB) can never reach the CDN. Videos on the site are **YouTube embeds**,
driven by `ytId` values in `script.js`.

## Adding a project

Create `projects/<slug>/` containing the chosen images and a `project.md`:

```
---
title: Label & Package Design
client: Rain City Brew
year: 2013
category: Packaging
tags: packaging, label, print
featured: true
summary: One line for the index card.
images:
  01-packaging.jpg: Caption for this image
---

Body copy. `## ` makes a heading, `- ` makes a bullet.
```

Add `status: draft` to hold a project back from the build. Then deploy.

## Commit and back up

// turbo
2. Push to both branches so the repo matches what is live:

```powershell
git add -A
git commit -m "<message>"
git push origin master
git push origin master:main
```

This push is backup only. Step 1 is what makes it live.

## Verify

// turbo
3. Confirm the live site changed (Cloudflare's edge cache can lag):

```powershell
$c = (Invoke-WebRequest "https://john-eldridge-portfolio.pages.dev/?cb=$(Get-Random)" -UseBasicParsing).Content
if ($c -match '<title>(.*?)</title>') { $Matches[1] }
```

Always append a cache-busting query string.

## Gotchas

- Last name is **Eldridge**, with the `d`. Frequently mistyped "Eldrige".
- Keep `deploy.ps1` **ASCII-only**. Windows PowerShell 5.1 reads `.ps1` as
  ANSI and non-ASCII characters break string parsing outright.
- Verify with **sentinels, not full-text compare**. PS 5.1 decodes files and
  HTTP responses differently, giving false mismatches on em dashes.
- Site copy is deliberately **industry-agnostic** so it suits any employer.
  It was once tailored to a single cannabis retailer; do not narrow it again
  without being asked.
- Source assets for the back catalog live in
  `d:\Work\Inkboard Design\Client Folder` (82 clients). Those folders mix
  deliverables with stock/source files, so image selection is a manual
  curation step.
- See `README.md` for full project detail.
