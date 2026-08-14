# John S. Eldridge, Jr. — Portfolio

Static portfolio site. No build step, no framework, no dependencies.

## 🔴 Live Site

**https://john-eldridge-portfolio.pages.dev/**

**Hosted on Cloudflare Pages.** Not GitHub Pages. Not Vercel. Not Netlify.

### ⚠️ Pushing to GitHub does NOT deploy the site

The Pages project is **direct upload** — it is *not* connected to the Git
repo (`wrangler pages project list` shows `Git Provider: No`). GitHub is
only a code backup. Deploying is a separate, manual step.

### Deploy

The `.mp4` files exceed Cloudflare's 25 MiB per-file limit, so **do not
deploy the project folder directly** — stage the web files first:

```powershell
$out = Join-Path $env:TEMP 'portfolio-deploy'
Remove-Item $out -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $out | Out-Null
Copy-Item index.html,styles.css,script.js $out
Copy-Item *.png $out

npx wrangler pages deploy $out `
  --project-name=john-eldridge-portfolio `
  --branch=main
```

`--branch=main` is required — that is the production branch, and any
other value produces a preview URL instead of updating the live site.

The staged folder holds 33 files / ~20 MB: `index.html`, `styles.css`,
`script.js`, and the 30 `Artboard *.png` images. Nothing else is needed;
`serve.py` and `package.json` are local-only.

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
| `index.html` | All page copy and structure |
| `styles.css` | Dark theme. Accent colors in `:root` at the top |
| `script.js` | Gallery data, category filters, lightbox, nav |
| `serve.py` | Local dev server |
| `Artboard *.png` | Design work images (committed) |
| `*.mp4` | Source video files — **gitignored**, too large |

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
