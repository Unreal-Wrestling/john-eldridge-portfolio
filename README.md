# John S. Eldridge, Jr. — Portfolio

Static portfolio site. No build step, no framework, no dependencies.

## 🔴 Live Site

**https://john-eldridge-portfolio.pages.dev/**

**Hosted on Cloudflare Pages.** Not GitHub Pages. Not Vercel. Not Netlify.

Deploys **automatically** on every push to `master`. There is no deploy
command to run — push and wait ~30 seconds.

- Git remote: `https://github.com/Unreal-Wrestling/john-eldridge-portfolio.git`
- Branch: `master` (not `main`)
- Cloudflare dashboard: Workers & Pages → `john-eldridge-portfolio`

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

## Videos

The `.mp4` files are gitignored because of size (one is 160 MB). The
video section embeds **YouTube** instead — IDs live in the `videos`
array in `script.js`. To add a video, upload to YouTube and add its ID
there; don't commit the source file.

## Notes

- Last name is **Eldridge** — with the `d`. Easy to typo as "Eldrige".
- Site accent is emerald (`--accent` in `styles.css`); the artboards
  themselves use orange. Known cosmetic mismatch, not yet resolved.
- Copy is intentionally **industry-agnostic** so the site can go to any
  employer or client. It was previously tailored to a single cannabis
  retailer — don't narrow it again without a reason.
