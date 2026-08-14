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

```powershell
npm run deploy            # publish to the live site
npm run deploy:preview    # throwaway preview URL, live site untouched
```

That runs `deploy.ps1`, which stages the web files to a temp folder,
aborts if any file exceeds Cloudflare's 25 MiB limit, deploys to the
`main` production branch, and verifies the live HTML matches local.

It stages 33 files / ~20 MB: `index.html`, `styles.css`, `script.js`,
and the 30 `Artboard *.png` images. `serve.py`, `package.json`, and the
`.mp4` masters are local-only and never deployed.

<details>
<summary>Equivalent manual command</summary>

```powershell
npx wrangler pages deploy <staged-folder> `
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
