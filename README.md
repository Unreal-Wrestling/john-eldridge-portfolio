# John S. Eldridge, Jr. — Portfolio

Static portfolio site. No framework, no npm toolchain. The only build
dependency is Pillow, used to resize project images.

Project root: `d:\Work\Portfolio` — an independent repo, unrelated to the
UnrealWrestling project it used to sit inside.

## 🔴 Live Site

**https://john-eldridge-portfolio.pages.dev/**

**Hosted on Cloudflare Pages.** Not GitHub Pages. Not Vercel. Not Netlify.

### ⚠️ Pushing to GitHub does NOT deploy the site

The Pages project is **direct upload** — it is *not* connected to the Git
repo (`wrangler pages project list` shows `Git Provider: No`). GitHub is
only a code backup. Deploying is a separate, manual step.

### Deploy

```powershell
npm run deploy            # publish to the live site
npm run deploy:preview    # throwaway preview URL, live site untouched
```

That runs `deploy.ps1`, which builds the site with `build.py`, uploads
`dist/` to the `main` production branch, and verifies the result.

Only `dist/` is uploaded, so `serve.py`, `package.json`, the `projects/`
sources, and the `.mp4` masters never reach the CDN.

<details>
<summary>Equivalent manual commands</summary>

```powershell
python build.py
npx wrangler pages deploy dist `
  --project-name=john-eldridge-portfolio `
  --branch=main
```

`--branch=main` is required — that is the production branch. Any other
value produces a preview URL instead of updating the live site.

</details>

- Live URL: https://john-eldridge-portfolio.pages.dev/
- Cloudflare account ID: `bcec09abf1e749ac5cf7b7417983a073`
- Dashboard: Workers & Pages → `john-eldridge-portfolio`
- Git remote: `https://github.com/Unreal-Wrestling/john-eldridge-portfolio.git`
- Branches `main` and `master` are both kept in sync (history is shared)

## Run locally

```bash
python serve.py          # http://localhost:8000
python serve.py 3000     # or pick a port
```

Runs from any folder, including a USB stick. Plain
`http.server` — no install needed.

## Files

| File | Purpose |
|------|---------|
| `build.py` | Static site generator — writes `dist/` |
| `deploy.ps1` | Builds, uploads to Cloudflare, verifies |
| `projects/` | Project sources: images + `project.md` per project |
| `index.html` | Home page copy and structure |
| `styles.css` | Dark theme. Accent colors in `:root` at the top |
| `work.css` | Styles for the generated `/work/` pages |
| `script.js` | Legacy gallery data, filters, lightbox, nav |
| `serve.py` | Local dev server |
| `Artboard *.png` | Legacy slide images (committed) |
| `dist/` | Build output — **gitignored**, never edit by hand |
| `*.mp4` | Source video masters — **gitignored**, too large |

## Adding a project

Projects are generated into real pages at `/work/<slug>/` with selectable,
indexable text — unlike the legacy artboards, which bake their copy into
pixels.

Create `projects/<slug>/` containing the chosen images and a `project.md`:

```
---
title: Label & Package Design
client: Rain City Brew
year: 2013
category: Packaging
tags: packaging, label, print
featured: true
summary: One line, shown on the index card.
images:
  01-packaging.jpg: Caption for this image
---

Body copy. `## ` makes a heading, `- ` makes a bullet.
```

Then `npm run deploy`. No Illustrator, no site code. Add `status: draft`
to keep a project out of the build until it's ready.

The build resizes every image to full (1800px) and thumb (800px) variants,
and **fails** if any file exceeds 25 MiB or the site exceeds 20,000 files —
the two Cloudflare Pages limits.

Source assets for the back catalog live in
`d:\Work\Inkboard Design\Client Folder` (82 clients). Those folders mix
finished deliverables with stock and working files, so picking images is a
manual curation step.

## Editing the gallery

Gallery content is the `galleryImages` array at the top of `script.js`.
Each entry:

```js
{
  file: 'Artboard 3.png',
  client: 'Asphalt Clothing',
  title: 'T-Shirt Merch Collection',
  category: 'merch',              // merch | ad | marketing
  desc: 'Shown in the lightbox.',
}
```

Categories are defined in `CATEGORIES` directly above it and mirror the
three sections of the source portfolio deck. Counts on the filter
buttons are calculated automatically.

**Deliberately excluded** from the gallery: `Artboard 1` (deck title
slide), `Artboard 2` / `10` / `18` (section dividers), and
`Artboard Closer` (thank-you slide). The website's hero, filter bar, and
contact section already serve those purposes. The files are still in the
repo if they're ever wanted back.

## Videos — YouTube embeds only

The video section does **not** play the local `.mp4` files. Nothing in
the site references them. Videos are **YouTube iframe embeds**, driven
by the `videos` array in `script.js`:

```js
{ ytId: 'gyg35mU7aus', title: '...', tag: 'Show Opener', desc: '...' }
```

To add a video: upload to YouTube, then add its ID to that array. The
`.mp4` files are kept locally as masters only — they are gitignored and
never deployed (one is 160 MB, far over Cloudflare's 25 MiB file limit).

## Notes

- Last name is **Eldridge** — with the `d`. Easy to typo as "Eldrige".
- Site accent is emerald (`--accent` in `styles.css`); the artboards
  themselves use orange. Known cosmetic mismatch, not yet resolved.
- Copy is intentionally **industry-agnostic** so the site can go to any
  employer or client. It was previously tailored to a single cannabis
  retailer — don't narrow it again without a reason.
