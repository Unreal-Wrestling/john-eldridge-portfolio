"""Static site generator for the portfolio.

Reads projects/<slug>/project.md plus the images in that folder, and writes
a complete deployable site to dist/:

    dist/
      index.html          <- existing single-page site, copied as-is
      styles.css, script.js, Artboard *.png
      work.css            <- styles for the generated pages
      work/index.html     <- browsable, searchable project index
      work/<slug>/index.html
      work/<slug>/img/    <- resized full + thumb images
      sitemap.xml

Run directly, or via `npm run deploy` which builds before uploading.

    python build.py

Design notes
------------
* No build dependencies beyond Pillow. No npm, no framework.
* Legacy Artboard slides keep working untouched, so the site can migrate
  project by project instead of all at once.
* All console output is ASCII: the Windows console is cp1252 and non-ASCII
  print() calls raise UnicodeEncodeError.
"""

from __future__ import annotations

import html
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required:  pip install Pillow")

ROOT = Path(__file__).parent
PROJECTS_DIR = ROOT / "projects"
DIST = ROOT / "dist"

SITE_URL = "https://john-eldridge-portfolio.pages.dev"
OWNER = "John S. Eldridge, Jr."

# Files copied verbatim from the project root into dist/.
LEGACY_FILES = ["index.html", "styles.css", "script.js", "work.css"]
LEGACY_GLOBS = ["Artboard *.png"]

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

# Cloudflare Pages rejects any single asset over 25 MiB, and several source
# files in the archive are well over that, so everything gets resized.
FULL_MAX_W = 1800
THUMB_MAX_W = 800
JPEG_QUALITY = 82


# ── Data ──────────────────────────────────────────────────────────────


@dataclass
class ProjectImage:
    src: Path
    full_rel: str
    thumb_rel: str
    caption: str = ""
    width: int = 0
    height: int = 0
    shape: str = "wide"  # wide | tall | small - drives display width


# Primary split. Employers in these two worlds want to see different
# halves of the portfolio, so this is the top-level toggle on /work/.
DIVISIONS = {
    "business": "Business",
    "arts": "Arts &amp; Entertainment",
}

# How the work came about. This is a separate question from what kind of
# design it is, and it must always be stated honestly - overstating spec
# or student work as client work is the fastest way to lose credibility.
WORK_TYPES = {
    "client": "",  # the default; no badge needed
    "student": "Student Project",
    "competition": "Design Competition",
    "self": "Self-Initiated",
    "volunteer": "Volunteer / Pro Bono",
}


@dataclass
class Project:
    slug: str
    title: str
    client: str = ""
    year: str = ""
    category: str = "Uncategorized"
    division: str = "business"
    work_type: str = "client"
    context: str = ""  # e.g. "Everett Community College, 2015"
    outcome: str = ""  # e.g. "1st place, 200 entries"
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    featured: bool = False
    body_html: str = ""
    images: list[ProjectImage] = field(default_factory=list)

    @property
    def url(self) -> str:
        return f"/work/{self.slug}/"

    @property
    def heading(self) -> str:
        return f"{self.client} - {self.title}" if self.client else self.title

    @property
    def division_label(self) -> str:
        return DIVISIONS.get(self.division, DIVISIONS["business"])

    @property
    def type_label(self) -> str:
        return WORK_TYPES.get(self.work_type, "")

    @property
    def disclaimer(self) -> str:
        """Generated, not hand-written, so it can never be forgotten.

        Any project that was not commissioned says so plainly, on the page
        itself, near the top.
        """
        if self.work_type == "client":
            return ""

        who = self.client or "The brand shown"
        base = {
            "student": (
                f"Self-directed student project. {who} was not a client and "
                "did not commission this work."
            ),
            "competition": (
                f"Created as a competition entry. {who} was not a client and "
                "did not commission this work."
            ),
            "self": (
                f"Self-initiated concept work. {who} was not a client and did "
                "not commission this work."
            ),
            "volunteer": "Completed on a volunteer / pro bono basis.",
        }.get(self.work_type, "")

        if self.context:
            base = f"{base} {self.context}." if base else f"{self.context}."
        return base


# ── Parsing ───────────────────────────────────────────────────────────


def parse_front_matter(text: str) -> tuple[dict, str]:
    """Split a project.md into a metadata dict and the body text.

    Deliberately not YAML - avoiding a dependency. Supports `key: value`
    lines plus one nested `images:` block of `filename: caption` pairs.
    """
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    raw_meta, body = parts[1], parts[2]
    meta: dict = {}
    images: dict[str, str] = {}
    in_images = False

    for line in raw_meta.splitlines():
        if not line.strip():
            continue

        indented = line[0] in " \t"
        if in_images and indented:
            if ":" in line:
                fname, _, caption = line.strip().partition(":")
                images[fname.strip()] = caption.strip()
            continue

        in_images = False
        if ":" not in line:
            continue

        key, _, value = line.partition(":")
        key, value = key.strip().lower(), value.strip()

        if key == "images":
            in_images = True
            continue
        meta[key] = value

    meta["_images"] = images
    return meta, body.strip()


def render_body(text: str) -> str:
    """Render a deliberately small Markdown subset.

    Supports `## headings`, `- bullet lists`, blank-line-separated
    paragraphs, and inline **bold** / *italic*. That covers what project
    write-ups actually need without pulling in a Markdown library.
    """

    def inline(s: str) -> str:
        s = html.escape(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", s)
        return s

    out: list[str] = []
    for block in re.split(r"\n\s*\n", text.strip()):
        block = block.strip()
        if not block:
            continue

        if block.startswith("## "):
            out.append(f"<h2>{inline(block[3:].strip())}</h2>")
        elif all(ln.strip().startswith("- ") for ln in block.splitlines()):
            items = "".join(
                f"<li>{inline(ln.strip()[2:])}</li>" for ln in block.splitlines()
            )
            out.append(f"<ul>{items}</ul>")
        else:
            out.append(f"<p>{inline(' '.join(block.split()))}</p>")
    return "\n".join(out)


def load_project(folder: Path) -> Project | None:
    md = folder / "project.md"
    if not md.exists():
        print(f"  SKIP {folder.name}: no project.md")
        return None

    meta, body = parse_front_matter(md.read_text(encoding="utf-8"))

    if meta.get("status", "").lower() == "draft":
        print(f"  SKIP {folder.name}: marked draft")
        return None

    title = meta.get("title") or folder.name.replace("-", " ").title()
    tags = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]

    division = meta.get("division", "").strip().lower()
    if division in ("arts", "art", "entertainment", "arts & entertainment"):
        division = "arts"
    elif division in ("business", "commercial", "corporate"):
        division = "business"
    else:
        if division:
            print(f"  WARN {folder.name}: unknown division '{division}', using business")
        division = "business"

    work_type = meta.get("work_type", meta.get("type", "")).strip().lower()
    if work_type in ("contest", "competition"):
        work_type = "competition"
    elif work_type in ("self", "self-initiated", "spec", "concept"):
        work_type = "self"
    elif work_type in ("volunteer", "probono", "pro bono"):
        work_type = "volunteer"
    elif work_type not in WORK_TYPES:
        if work_type:
            print(f"  WARN {folder.name}: unknown work_type '{work_type}', using client")
        work_type = "client"

    proj = Project(
        slug=folder.name,
        title=title,
        client=meta.get("client", ""),
        year=meta.get("year", ""),
        category=meta.get("category", "Uncategorized"),
        division=division,
        work_type=work_type,
        context=meta.get("context", ""),
        outcome=meta.get("outcome", ""),
        summary=meta.get("summary", ""),
        tags=tags,
        featured=meta.get("featured", "").lower() in ("true", "yes", "1"),
        body_html=render_body(body),
    )

    captions = meta.get("_images", {})
    for img in sorted(folder.iterdir()):
        if img.suffix.lower() not in IMAGE_EXTS:
            continue
        stem = img.stem
        proj.images.append(
            ProjectImage(
                src=img,
                full_rel=f"img/{stem}.jpg" if img.suffix.lower() != ".png" else f"img/{stem}.png",
                thumb_rel=f"img/{stem}-thumb.jpg" if img.suffix.lower() != ".png" else f"img/{stem}-thumb.png",
                caption=captions.get(img.name, ""),
            )
        )

    if not proj.images:
        print(f"  WARN {folder.name}: no images found")

    return proj


# ── Images ────────────────────────────────────────────────────────────


def resize_to(src: Path, dest: Path, max_w: int) -> tuple[int, int]:
    """Downscale to fit max_w and return the written size.

    Only ever shrinks. Aspect ratio is preserved exactly, and images
    narrower than max_w are left at their native size - upscaling a small
    logo to poster width would just make it blurry.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        has_alpha = im.mode in ("RGBA", "LA", "P") and "transparency" in im.info
        if im.width > max_w:
            ratio = max_w / im.width
            im = im.resize((max_w, int(im.height * ratio)), Image.LANCZOS)

        if dest.suffix.lower() == ".png":
            if not has_alpha and im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGBA" if has_alpha else "RGB")
            im.save(dest, "PNG", optimize=True)
        else:
            if im.mode != "RGB":
                im = im.convert("RGB")
            im.save(dest, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)

        return im.size


def classify_shape(w: int, h: int) -> str:
    """Pick a display treatment from the image's real proportions.

    A logo and a tall event poster should not occupy the same width on the
    page just because they are both 'images'.
    """
    if w < 700:
        return "small"
    if h and h / w > 1.35:
        return "tall"
    return "wide"


def build_images(proj: Project, out_dir: Path) -> None:
    for image in proj.images:
        w, h = resize_to(image.src, out_dir / image.full_rel, FULL_MAX_W)
        resize_to(image.src, out_dir / image.thumb_rel, THUMB_MAX_W)
        image.width, image.height = w, h
        image.shape = classify_shape(w, h)


# ── HTML ──────────────────────────────────────────────────────────────

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <link rel="canonical" href="{canonical}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{canonical}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{css_prefix}styles.css">
  <link rel="stylesheet" href="{css_prefix}work.css">
</head>
<body>
"""

FOOTER = """
  <footer>
    <p>&copy; {year} {owner} &mdash; Design, Marketing &amp; Content Production</p>
  </footer>
  <button id="back-to-top" aria-label="Back to top">&uarr;</button>
  <script>
    var btt = document.getElementById('back-to-top');
    window.addEventListener('scroll', function () {{
      btt.classList.toggle('visible', window.scrollY > 400);
    }});
    btt.addEventListener('click', function () {{
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }});
  </script>
</body>
</html>
"""


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def render_project_page(proj: Project) -> str:
    desc = proj.summary or f"{proj.heading} by {OWNER}"
    parts = [
        HEAD.format(
            title=f"{proj.heading} | {OWNER}",
            description=esc(desc),
            canonical=f"{SITE_URL}{proj.url}",
            css_prefix="../../",
        )
    ]

    meta_bits = [b for b in (proj.category, proj.year) if b]

    # Non-client work is badged in the header and disclaimed above the
    # write-up. Both are generated, so they can't be omitted by accident.
    badge = (
        f'<span class="proj-badge proj-badge-{proj.work_type}">'
        f'{esc(proj.type_label)}</span>'
        if proj.type_label
        else ""
    )
    outcome = (
        f'<p class="proj-outcome">{esc(proj.outcome)}</p>' if proj.outcome else ""
    )
    disclaimer = (
        f'<p class="proj-disclaimer">{esc(proj.disclaimer)}</p>'
        if proj.disclaimer
        else ""
    )

    parts.append(f"""
  <header class="proj-header">
    <div class="container">
      <nav class="crumbs">
        <a href="../../">Home</a>
        <span>/</span>
        <a href="../">Work</a>
        <span>/</span>
        <span class="crumb-current">{esc(proj.client or proj.title)}</span>
      </nav>
      {badge}
      {f'<p class="proj-client">{esc(proj.client)}</p>' if proj.client else ''}
      <h1 class="proj-title">{esc(proj.title)}</h1>
      {f'<p class="proj-summary">{esc(proj.summary)}</p>' if proj.summary else ''}
      {outcome}
      <div class="proj-meta">
        {''.join(f'<span class="proj-meta-item">{esc(b)}</span>' for b in meta_bits)}
      </div>
    </div>
  </header>

  <main class="container proj-main">
    <div class="proj-body">
      {disclaimer}
      {proj.body_html}
      {('<div class="proj-tags">' + ''.join(f'<span class="proj-tag">{esc(t)}</span>' for t in proj.tags) + '</div>') if proj.tags else ''}
    </div>
""")

    if proj.images:
        parts.append('    <div class="proj-gallery">')
        for i, image in enumerate(proj.images):
            cap = (
                f'<figcaption>{esc(image.caption)}</figcaption>' if image.caption else ""
            )
            # First image is above the fold; the rest can load lazily.
            loading = "eager" if i == 0 else "lazy"
            # Cap the figure at the image's true width so nothing is ever
            # scaled up past its native resolution.
            cap_px = f' style="max-width:{image.width}px"' if image.width else ""
            dims = (
                f' width="{image.width}" height="{image.height}"'
                if image.width and image.height
                else ""
            )
            parts.append(f"""      <figure class="proj-figure is-{image.shape}"{cap_px}>
        <a href="{image.full_rel}" target="_blank" rel="noopener">
          <img src="{image.thumb_rel}" alt="{esc(image.caption or proj.heading)}"{dims} loading="{loading}">
        </a>
        {cap}
      </figure>""")
        parts.append("    </div>")

    parts.append("""
    <div class="proj-nav">
      <a href="../" class="proj-nav-btn">&larr; All Work</a>
      <a href="../../#contact" class="proj-nav-btn proj-nav-cta">Get In Touch</a>
    </div>
  </main>
""")
    parts.append(FOOTER.format(year=date.today().year, owner=esc(OWNER)))
    return "".join(parts)


def render_work_index(projects: list[Project]) -> str:
    cats = sorted({p.category for p in projects})
    desc = (
        f"Selected design, branding, packaging, and marketing projects by {OWNER}."
    )

    parts = [
        HEAD.format(
            title=f"Work | {OWNER}",
            description=esc(desc),
            canonical=f"{SITE_URL}/work/",
            css_prefix="../",
        )
    ]

    filters = ['<button type="button" class="filter-btn active" data-cat="all">All '
               f'<span class="filter-count">{len(projects)}</span></button>']
    for c in cats:
        n = sum(1 for p in projects if p.category == c)
        filters.append(
            f'<button type="button" class="filter-btn" data-cat="{esc(c)}">'
            f'{esc(c)} <span class="filter-count">{n}</span></button>'
        )

    # Primary split, above the category filters. Only rendered once both
    # halves actually have work in them - a toggle with an empty side
    # just looks broken.
    divs = [d for d in DIVISIONS if any(p.division == d for p in projects)]
    if len(divs) > 1:
        btns = ['<button type="button" class="div-btn active" data-div="all">'
                'All Work</button>']
        for d in divs:
            n = sum(1 for p in projects if p.division == d)
            btns.append(
                f'<button type="button" class="div-btn" data-div="{d}">'
                f'{DIVISIONS[d]} <span class="filter-count">{n}</span></button>'
            )
        division_ui = f'<div class="division-toggle">{"".join(btns)}</div>'
    else:
        division_ui = ""

    parts.append(f"""
  <header class="work-header">
    <div class="container">
      <nav class="crumbs">
        <a href="../">Home</a>
        <span>/</span>
        <span class="crumb-current">Work</span>
      </nav>
      <h1 class="work-title">Work</h1>
      <p class="work-sub">{esc(desc)}</p>
      {division_ui}
      <input type="search" id="work-search" class="work-search"
             placeholder="Search by client, project, or tag..."
             aria-label="Search projects">
      <div class="gallery-filters">{''.join(filters)}</div>
      <p class="work-count" id="work-count"></p>
    </div>
  </header>

  <main class="container work-main">
    <div class="work-grid" id="work-grid">
""")

    for p in projects:
        thumb = f"{p.slug}/{p.images[0].thumb_rel}" if p.images else ""
        haystack = " ".join(
            [p.title, p.client, p.category, p.year, " ".join(p.tags), p.summary]
        ).lower()
        img = (
            f'<img src="{thumb}" alt="{esc(p.heading)}" loading="lazy">'
            if thumb
            else '<div class="work-card-noimg">No image</div>'
        )
        # Badge the card too, so the nature of the work is clear before
        # anyone clicks through.
        card_badge = (
            f'<span class="work-card-badge">{esc(p.type_label)}</span>'
            if p.type_label
            else ""
        )
        parts.append(f"""      <a class="work-card" href="{p.slug}/"
         data-cat="{esc(p.category)}" data-div="{p.division}"
         data-search="{esc(haystack)}">
        <div class="work-card-img">{img}{card_badge}</div>
        <div class="work-card-info">
          {f'<span class="work-card-client">{esc(p.client)}</span>' if p.client else ''}
          <h2 class="work-card-title">{esc(p.title)}</h2>
          {f'<p class="work-card-summary">{esc(p.summary)}</p>' if p.summary else ''}
          <div class="work-card-meta">
            <span>{esc(p.category)}</span>{f'<span>{esc(p.year)}</span>' if p.year else ''}
          </div>
        </div>
      </a>""")

    parts.append("""    </div>
    <p class="work-empty" id="work-empty" hidden>No projects match that search.</p>
  </main>

  <script>
    (function () {
      var cards    = Array.prototype.slice.call(document.querySelectorAll('.work-card'));
      var buttons  = Array.prototype.slice.call(document.querySelectorAll('.filter-btn'));
      var divBtns  = Array.prototype.slice.call(document.querySelectorAll('.div-btn'));
      var search   = document.getElementById('work-search');
      var countEl  = document.getElementById('work-count');
      var emptyEl  = document.getElementById('work-empty');
      var activeCat = 'all';
      var activeDiv = 'all';

      function inDiv(card) {
        return activeDiv === 'all' || card.dataset.div === activeDiv;
      }

      function apply() {
        var q = search.value.trim().toLowerCase();
        var shown = 0;
        cards.forEach(function (card) {
          var okCat = activeCat === 'all' || card.dataset.cat === activeCat;
          var okQ   = !q || card.dataset.search.indexOf(q) !== -1;
          var show  = inDiv(card) && okCat && okQ;
          card.hidden = !show;
          if (show) shown++;
        });

        // Category filters are scoped to the active division, so switching
        // to Arts doesn't leave dead Business-only categories on screen.
        buttons.forEach(function (btn) {
          var cat = btn.dataset.cat;
          if (cat === 'all') { btn.hidden = false; return; }
          var n = cards.filter(function (c) {
            return inDiv(c) && c.dataset.cat === cat;
          }).length;
          btn.hidden = n === 0;
          var badge = btn.querySelector('.filter-count');
          if (badge) badge.textContent = n;
        });

        countEl.textContent = shown + (shown === 1 ? ' project' : ' projects');
        emptyEl.hidden = shown !== 0;
      }

      function setDivision(name, push) {
        activeDiv = name;
        divBtns.forEach(function (b) {
          b.classList.toggle('active', b.dataset.div === name);
        });
        // Reset the category when switching sides; the previous one may
        // not exist over here.
        activeCat = 'all';
        buttons.forEach(function (b) {
          b.classList.toggle('active', b.dataset.cat === 'all');
        });
        if (push && window.history.replaceState) {
          var url = name === 'all' ? location.pathname
                                   : location.pathname + '?type=' + name;
          history.replaceState(null, '', url);
        }
        apply();
      }

      buttons.forEach(function (btn) {
        btn.addEventListener('click', function () {
          activeCat = btn.dataset.cat;
          buttons.forEach(function (b) { b.classList.toggle('active', b === btn); });
          apply();
        });
      });
      divBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
          setDivision(btn.dataset.div, true);
        });
      });
      search.addEventListener('input', apply);

      // Support /work/?type=business so a single link can open straight
      // into the relevant half of the portfolio.
      var wanted = new URLSearchParams(location.search).get('type');
      if (wanted && divBtns.some(function (b) { return b.dataset.div === wanted; })) {
        setDivision(wanted, false);
      } else {
        apply();
      }
    })();
  </script>
""")
    parts.append(FOOTER.format(year=date.today().year, owner=esc(OWNER)))
    return "".join(parts)


def render_sitemap(projects: list[Project]) -> str:
    urls = [f"{SITE_URL}/", f"{SITE_URL}/work/"]
    urls += [f"{SITE_URL}{p.url}" for p in projects]
    today = date.today().isoformat()
    body = "\n".join(
        f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>" for u in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n</urlset>\n"
    )


# ── Build ─────────────────────────────────────────────────────────────


def copy_legacy() -> None:
    for name in LEGACY_FILES:
        src = ROOT / name
        if src.exists():
            shutil.copy2(src, DIST / name)
        else:
            print(f"  WARN missing {name}")
    for pattern in LEGACY_GLOBS:
        for src in ROOT.glob(pattern):
            shutil.copy2(src, DIST / src.name)


def check_sizes() -> int:
    """Cloudflare Pages rejects assets over 25 MiB. Fail loudly, not at upload."""
    limit = 25 * 1024 * 1024
    bad = [p for p in DIST.rglob("*") if p.is_file() and p.stat().st_size > limit]
    for p in bad:
        mb = p.stat().st_size / (1024 * 1024)
        print(f"  ERROR {p.relative_to(DIST)} is {mb:.1f} MB (limit 25 MiB)")
    return len(bad)


def main() -> int:
    print("")
    print("  Building portfolio...")

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    copy_legacy()

    projects: list[Project] = []
    if PROJECTS_DIR.exists():
        for folder in sorted(PROJECTS_DIR.iterdir()):
            if not folder.is_dir():
                continue
            proj = load_project(folder)
            if proj:
                projects.append(proj)

    # Featured first, then newest, then alphabetical by client.
    projects.sort(key=lambda p: (not p.featured, -int(p.year or 0), p.client.lower()))

    work_dir = DIST / "work"
    work_dir.mkdir(parents=True, exist_ok=True)

    for proj in projects:
        out = work_dir / proj.slug
        out.mkdir(parents=True, exist_ok=True)
        build_images(proj, out)
        (out / "index.html").write_text(render_project_page(proj), encoding="utf-8")
        print(f"  OK   /work/{proj.slug}/  ({len(proj.images)} images)")

    (work_dir / "index.html").write_text(render_work_index(projects), encoding="utf-8")
    (DIST / "sitemap.xml").write_text(render_sitemap(projects), encoding="utf-8")
    (DIST / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8"
    )

    files = [p for p in DIST.rglob("*") if p.is_file()]
    total_mb = sum(p.stat().st_size for p in files) / (1024 * 1024)

    print("")
    print(f"  {len(projects)} projects, {len(files)} files, {total_mb:.2f} MB -> dist/")

    if len(files) > 20000:
        print(f"  ERROR {len(files)} files exceeds the Cloudflare free-plan limit of 20,000")
        return 1
    if check_sizes():
        return 1

    print("  Build OK")
    print("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
