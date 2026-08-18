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
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("Pillow is required:  pip install Pillow")

ROOT = Path(__file__).parent
PROJECTS_DIR = ROOT / "projects"
DIST = ROOT / "dist"

SITE_URL = "https://john-eldridge-portfolio.pages.dev"
OWNER = "John S. Eldridge, Jr."

# Files copied verbatim from the project root into dist/.
LEGACY_FILES = ["index.html", "styles.css", "script.js", "work.css", "theme.js"]
LEGACY_GLOBS: list[str] = []

# Replaced in index.html at build time with generated project cards.
HOME_CARDS_MARKER = "<!--CASE_STUDIES-->"

# Cloudflare Pages reads dist/_headers on deploy. Two jobs here.
#
# Caching: generated images under /work/*/img/ are rewritten only when the
# source art changes, and a changed image gets redeployed anyway, so they are
# safe to cache hard. HTML is not - it has to revalidate or a visitor keeps
# seeing yesterday's write-up.
#
# NOTE: image filenames are NOT content-hashed. If an image is replaced under
# the same filename, a visitor who already has it cached will keep the old one
# for up to a year. Rename the file when replacing art, or drop this to a
# shorter max-age.
#
# Security: this is a static site with no forms, cookies, or auth, so these are
# cheap hardening rather than anything load-bearing.
HEADERS = """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: SAMEORIGIN

/work/:project/img/*
  Cache-Control: public, max-age=31536000, immutable

/fonts/*
  Cache-Control: public, max-age=31536000, immutable

/*.css
  Cache-Control: public, max-age=3600, must-revalidate

/*.js
  Cache-Control: public, max-age=3600, must-revalidate

/*.html
  Cache-Control: public, max-age=0, must-revalidate
"""

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
# Copied through untouched - there is no transcoding step, so source files
# need to be web-ready and within the 25 MiB per-asset limit already.
VIDEO_EXTS = {".mp4", ".webm"}

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
    is_video: bool = False
    matte: bool = False  # white-background mark, safe to pad with white
    width: int = 0
    height: int = 0
    # Width of the thumb actually written to disk. Needed for srcset: the
    # browser can only pick the right candidate if it knows how wide each
    # one really is, and a narrow source is never upscaled to THUMB_MAX_W.
    thumb_w: int = 0
    shape: str = "wide"  # wide | tall | small - drives display width
    shape_hint: str = ""  # explicit override from project.md, if given
    thumb_only: bool = False  # used as card thumbnail only, not shown in body


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
    "internship": "Internship",
    "student": "Student Project",
    "competition": "Design Competition",
    "self": "Self-Initiated",
    "volunteer": "Volunteer / Pro Bono",
}

# Work that was actually commissioned - by a client, an employer, or an
# internship host. Real briefs with real stakeholders, so no disclaimer.
COMMISSIONED = {"client", "internship"}

# The top-level split on /work/, by the context the work was made in rather
# than what kind of design it is. A creative director wants to separate
# professional practice from coursework immediately.
#
# Self-initiated sits under Professional because it is professional-grade work
# made outside school - and every card keeps its own "Self-Initiated" badge, so
# grouping it here never implies it was commissioned.
WORK_GROUPS = {
    "professional": "Professional",
    "student": "School",
    "competition": "Competition",
}

WORK_GROUP_OF = {
    "client": "professional",
    "internship": "professional",
    "self": "professional",
    "volunteer": "professional",
    "student": "student",
    "competition": "competition",
}

# Opens here on load. Leading with 11 student projects undersells the
# professional work, so the default is the tab a hiring reader wants first.
DEFAULT_WORK_GROUP = "professional"


@dataclass
class Project:
    slug: str
    title: str
    client: str = ""
    year: str = ""
    # Sorting only, never displayed: YYYY-MM or YYYY-MM-DD. `year` is the
    # label a reader sees and is often a range, which is too coarse to
    # order a year's worth of work. Taken from the dates on the source
    # files when the project's own records don't say.
    date: str = ""
    category: str = "Uncategorized"
    division: str = "business"
    work_type: str = "client"
    role: str = ""  # e.g. "Creative Director" - state it, don't imply it
    context: str = ""  # e.g. "Everett Community College, 2015"
    outcome: str = ""  # e.g. "1st place, 200 entries"
    summary: str = ""
    quote: str = ""  # client testimonial, in their words
    quote_by: str = ""  # attribution - name and title
    team: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    featured: bool = False
    # Filename to use on index cards. Defaults to the first still, which is
    # usually right, but a project that opens on sketches or a wide layout
    # is better represented by its logo.
    thumb: str = ""
    body_html: str = ""
    images: list[ProjectImage] = field(default_factory=list)
    # Event/documentary photography, kept separate from the design work so
    # a reel of 20 frames never competes with the pieces being shown.
    # Lives in a photos/ subfolder and renders as one slideshow.
    photos: list[ProjectImage] = field(default_factory=list)
    # Named photo blocks for sectioned projects, keyed by the suffix in
    # `photos-name:`. Each block renders as its own slideshow.
    photo_blocks: dict[str, list[ProjectImage]] = field(default_factory=dict)
    # Tab labels for sectioned projects. When non-empty the body is split
    # at matching ## headings and each section renders in its own tab.
    sections: list[str] = field(default_factory=list)

    @property
    def url(self) -> str:
        return f"/work/{self.slug}/"

    @property
    def card_image(self) -> "ProjectImage | None":
        """The still a card should lead with. Video has no thumbnail, so it
        can never be the card image."""
        stills = [im for im in self.images if not im.is_video]
        if self.thumb:
            chosen = next((im for im in stills if im.src.name == self.thumb), None)
            if chosen:
                return chosen
            print(f"  WARN {self.slug}: thumb '{self.thumb}' not found")
        return stills[0] if stills else None

    @property
    def heading(self) -> str:
        return f"{self.client} - {self.title}" if self.client else self.title

    @property
    def sort_year(self) -> int:
        """First four-digit year in the year field, for ordering.

        Tolerates ranges like '2012-2013' and anything non-numeric, which
        sorts last instead of crashing the build or landing in 1970.
        """
        m = re.search(r"\d{4}", self.year or "")
        return int(m.group()) if m else 9999

    @property
    def sort_key(self) -> tuple:
        """Chronological position, to the month where it is known.

        A year alone can't order a body of work produced at pace, so an
        explicit `date` wins when present. Projects dated only by year fall
        back to month 0 and lead that year, which is the honest position
        for a date we don't actually know.
        """
        m = re.match(r"(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?$", (self.date or "").strip())
        if m:
            year, month, day = m.group(1), m.group(2), m.group(3)
            return (int(year), int(month or 0), int(day or 0), self.title.lower())
        if self.date:
            print(f"  WARN {self.slug}: unreadable date '{self.date}', using year")
        # No date given: order by the year label, and let a project confined
        # to one year lead one that runs on past it.
        return (self.sort_year, 0, 0, self.title.lower())

    @property
    def sort_end_year(self) -> int:
        """Last four-digit year in the field, for breaking ties.

        A project confined to 2012 should sort ahead of one running
        2012-2013, so a range never jumps in front of the work that led
        to it.
        """
        years = re.findall(r"\d{4}", self.year or "")
        return int(years[-1]) if years else 9999

    @property
    def division_label(self) -> str:
        return DIVISIONS.get(self.division, DIVISIONS["business"])

    @property
    def type_label(self) -> str:
        return WORK_TYPES.get(self.work_type, "")

    @property
    def work_group(self) -> str:
        """Which /work/ tab this project belongs in."""
        return WORK_GROUP_OF.get(self.work_type, "professional")

    @property
    def disclaimer(self) -> str:
        """Generated, not hand-written, so it can never be forgotten.

        Any project that was not commissioned says so plainly, on the page
        itself, near the top.
        """
        if self.work_type in COMMISSIONED:
            return ""

        who = self.client or "The brand shown"
        base = {
            # Not "self-directed" - most of these are set briefs, some are
            # team assignments, and the word contradicted the context line
            # sitting right next to it. `self` is the work type for work
            # that genuinely was self-initiated.
            "student": (
                f"Student project. {who} was not a client and "
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
    lines plus nested `images:` and `photos:` blocks of `filename: caption`
    pairs.
    """
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    raw_meta, body = parts[1], parts[2]
    meta: dict = {}
    blocks: dict[str, dict[str, str]] = {"images": {}, "photos": {}}
    photo_blocks: dict[str, dict[str, str]] = {}
    current = ""

    for line in raw_meta.splitlines():
        if not line.strip():
            continue

        indented = line[0] in " \t"
        if current and indented:
            if ":" in line:
                fname, _, caption = line.strip().partition(":")
                if current.startswith("photos-"):
                    photo_blocks[current[7:]][fname.strip()] = caption.strip()
                else:
                    blocks[current][fname.strip()] = caption.strip()
            continue

        current = ""
        if ":" not in line:
            continue

        key, _, value = line.partition(":")
        key, value = key.strip().lower(), value.strip()

        if key in blocks:
            current = key
            continue
        if key.startswith("photos-"):
            photo_blocks[key[7:]] = {}
            current = key
            continue
        meta[key] = value

    meta["_images"] = blocks["images"]
    meta["_photos"] = blocks["photos"]
    meta["_photo_blocks"] = photo_blocks
    return meta, body.strip()


def render_web_embed(url: str, caption: str) -> str:
    """Embed a live web page, used for Internet Archive captures.

    Wayback serves the same snapshot without its own toolbar when `if_` is
    appended to the timestamp, so the frame shows the archived page and
    nothing else. The visible link keeps the plain URL, which does include
    the toolbar - useful once you are actually over there.
    """
    framed = re.sub(r"/web/(\d{14})/", r"/web/\1if_/", url)
    label = caption or "Archived page"
    return (
        '<figure class="web-embed">\n'
        '  <div class="web-frame">\n'
        f'    <iframe src="{esc(framed)}" title="{esc(label)}" loading="lazy"\n'
        '            referrerpolicy="no-referrer"></iframe>\n'
        "  </div>\n"
        f'  <figcaption>{esc(label)} '
        f'<a href="{esc(url)}" target="_blank" rel="noopener">Open the capture &rarr;</a>'
        "</figcaption>\n"
        "</figure>"
    )


def render_youtube_embed(url: str, caption: str) -> str:
    """Embed a YouTube video via its privacy-enhanced nocookie domain."""
    m = re.search(r"(?:youtu\.be/|v=)([\w-]{11})", url)
    video_id = m.group(1) if m else ""
    label = caption or "Video"
    return (
        '<figure class="video-embed">\n'
        '  <div class="video-frame">\n'
        f'    <iframe src="https://www.youtube.com/embed/{video_id}" '
        f'title="{esc(label)}" loading="lazy" allowfullscreen\n'
        '            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"\n'
        '            referrerpolicy="strict-origin-when-cross-origin"></iframe>\n'
        "  </div>\n"
        f'  <figcaption>{esc(label)} '
        f'<a href="{esc(url)}" target="_blank" rel="noopener">Watch on YouTube &rarr;</a>'
        "</figcaption>\n"
        "</figure>"
    )


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
        # [text](url). Escaped first, so a URL's ampersands are already
        # entities by the time they land in the attribute.
        s = re.sub(
            r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
            r'<a href="\2" target="_blank" rel="noopener">\1</a>',
            s,
        )
        return s

    out: list[str] = []
    for block in re.split(r"\n\s*\n", text.strip()):
        block = block.strip()
        if not block:
            continue

        if block.startswith("### "):
            out.append(f"<h3>{inline(block[4:].strip())}</h3>")
        elif block.startswith("## "):
            out.append(f"<h2>{inline(block[3:].strip())}</h2>")
        elif block.startswith("[[web:") and block.endswith("]]"):
            url, _, cap = block[6:-2].partition("|")
            out.append(render_web_embed(url.strip(), cap.strip()))
        elif block.startswith("[[youtube:") and block.endswith("]]"):
            url, _, cap = block[10:-2].partition("|")
            out.append(render_youtube_embed(url.strip(), cap.strip()))
        elif re.fullmatch(r"\[\[[^\[\]]+\]\]", block):
            # Image or slideshow placed inline in the write-up. Resolved
            # after the images are processed, since dimensions aren't
            # known yet.
            ref = block[2:-2].strip()
            if ref == "photos":
                out.append("<!--PHOTOS-->")
            elif ref.startswith("photos:"):
                out.append(f"<!--PHOTOS:{ref[7:]}-->")
            elif ref.startswith("grid:"):
                grid_spec = ref[5:]
                if ":wide" in grid_spec:
                    name, _, _ = grid_spec.partition(":")
                    out.append(f"<!--GRID:{name}:wide-->")
                else:
                    out.append(f"<!--GRID:{grid_spec}-->")
            else:
                out.append(f"<!--IMG:{ref}-->")
        elif all(ln.strip().startswith(">") for ln in block.splitlines()):
            quote = " ".join(ln.strip().lstrip(">").strip() for ln in block.splitlines())
            out.append(f"<blockquote>{inline(quote)}</blockquote>")
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
    team = [t.strip() for t in meta.get("team", "").split(",") if t.strip()]

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
    elif work_type in ("intern", "internship"):
        work_type = "internship"
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
        date=meta.get("date", ""),
        category=meta.get("category", "Uncategorized"),
        division=division,
        work_type=work_type,
        role=meta.get("role", ""),
        context=meta.get("context", ""),
        outcome=meta.get("outcome", ""),
        summary=meta.get("summary", ""),
        quote=meta.get("quote", ""),
        quote_by=meta.get("quote_by", ""),
        team=team,
        tags=tags,
        featured=meta.get("featured", "").lower() in ("true", "yes", "1"),
        thumb=meta.get("thumb", ""),
        body_html=render_body(body),
    )

    captions = meta.get("_images", {})
    for img in sorted(folder.iterdir()):
        suffix = img.suffix.lower()
        if suffix not in IMAGE_EXTS and suffix not in VIDEO_EXTS:
            continue
        stem = img.stem
        # A caption may carry a display hint: `logo.jpg [small]: Primary mark`.
        # Resolution and display width are separate decisions - a 1600px
        # logo should be sharp, not a metre wide.
        caption = captions.get(img.name, "")
        hint = ""
        for key, val in captions.items():
            m = re.match(rf"^{re.escape(img.name)}\s*\[([\w-]+)\]$", key)
            if m:
                hint, caption = m.group(1).lower(), val
                break
        thumb_only = False
        if hint and hint not in ("wide", "medium", "tall", "small", "thumb-only"):
            print(f"  WARN {folder.name}: unknown shape '{hint}' on {img.name}")
            hint = ""
        if hint == "thumb-only":
            thumb_only = True
            hint = "small"

        if suffix in VIDEO_EXTS:
            # Copied through as-is; there is no transcoding step here.
            proj.images.append(
                ProjectImage(
                    src=img,
                    full_rel=f"img/{stem}{suffix}",
                    thumb_rel="",
                    caption=caption,
                    is_video=True,
                    shape_hint=hint,
                )
            )
            continue

        # A PNG source only stays a PNG when its pixels need one. Everything
        # else - including every photograph saved as a PNG - ships as JPEG.
        ext = png_delivery_ext(img) if suffix == ".png" else ".jpg"

        proj.images.append(
            ProjectImage(
                src=img,
                full_rel=f"img/{stem}{ext}",
                thumb_rel=f"img/{stem}-thumb{ext}",
                caption=caption,
                shape_hint=hint,
                thumb_only=thumb_only,
            )
        )

    if not proj.images:
        print(f"  WARN {folder.name}: no images found")

    # `[thumb-only]` means "use as the card thumbnail, keep it out of the
    # body". It earns that only if `thumb:` actually points at the file.
    # When it does not, and the image is not placed inline either, the
    # image renders nowhere at all - which is how a commissioner report
    # stayed invisible while the copy claimed it had been designed.
    placed = set(re.findall(r"\[\[([^\]]+)\]\]", body))
    for img in proj.images:
        if not img.thumb_only:
            continue
        name = img.src.name
        if name != proj.thumb and name not in placed:
            print(
                f"  WARN {folder.name}: {name} is marked thumb-only but "
                f"`thumb:` is {proj.thumb or 'unset'} - renders nowhere"
            )

    photo_captions = meta.get("_photos", {})
    photo_dir = folder / "photos"
    photo_blocks_meta = meta.get("_photo_blocks", {})

    # When named photo blocks are used (photos-sb:, photos-boa:, etc.),
    # skip the default auto-load — those photos are handled by the blocks.
    if not photo_blocks_meta and photo_dir.is_dir():
        for img in sorted(photo_dir.iterdir()):
            if img.suffix.lower() not in IMAGE_EXTS:
                continue
            proj.photos.append(
                ProjectImage(
                    src=img,
                    full_rel=f"img/photos/{img.stem}.jpg",
                    thumb_rel=f"img/photos/{img.stem}-thumb.jpg",
                    caption=photo_captions.get(img.name, ""),
                )
            )

    # Named photo blocks for tabbed/sectioned projects
    photo_blocks_meta = meta.get("_photo_blocks", {})
    for block_name, captions in photo_blocks_meta.items():
        block_photos: list[ProjectImage] = []
        for fname in captions:
            img_path = photo_dir / fname
            if not img_path.exists():
                print(f"  WARN {folder.name}: photo '{fname}' not found in photos/")
                continue
            block_photos.append(
                ProjectImage(
                    src=img_path,
                    full_rel=f"img/photos/{img_path.stem}.jpg",
                    thumb_rel=f"img/photos/{img_path.stem}-thumb.jpg",
                    caption=captions[fname],
                )
            )
        proj.photo_blocks[block_name] = block_photos

    # Section labels for tabbed projects
    sections_raw = meta.get("sections", "")
    if sections_raw:
        proj.sections = [s.strip() for s in sections_raw.split(",") if s.strip()]

    return proj


# ── Images ────────────────────────────────────────────────────────────

# Modes that can carry an alpha channel. "P" is handled separately, since a
# palette image only has transparency when it declares one.
ALPHA_MODES = ("RGBA", "LA", "PA")

# Above this many distinct colours an image is treated as photographic. Flat
# vector art, logos, and screenshots of type sit far below it; photographs and
# gradient meshes blow past it immediately.
FLAT_COLOR_CEILING = 4096


def png_delivery_ext(src: Path) -> str:
    """Decide whether a PNG source should ship as PNG or JPEG.

    PNG is the correct container for flat art and anything with real
    transparency. It is the wrong one for photographs, where it routinely
    costs ten times what an equivalent JPEG would - a 1 MB thumbnail is
    always a PNG holding a photograph.

    Converting blindly would wreck both edge cases, so this inspects the
    actual pixels and keeps PNG when:

    * any pixel is genuinely transparent - converting would flatten it
    * the image has few distinct colours, meaning vector art or a logo,
      where JPEG would ring visibly around every hard edge

    Everything else is photographic and becomes a JPEG.
    """
    try:
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)

            if im.mode == "P":
                im = im.convert("RGBA" if "transparency" in im.info else "RGB")

            if im.mode in ALPHA_MODES:
                # Present but fully opaque is common in exported art. Only
                # actual transparency forces PNG.
                if im.getchannel("A").getextrema()[0] < 255:
                    return ".png"
                im = im.convert("RGB")

            # Counted at full resolution deliberately. Downscaling first is
            # faster, but it collapses the very signal being measured: a dark
            # photograph subsampled to 400px can fall under the ceiling and
            # get misread as flat art. getcolors bails out as soon as it
            # passes maxcolors, so the full-size scan is cheap anyway.
            #
            # None means the image blew past the cap, which is exactly the
            # signal that it is photographic.
            return (
                ".png"
                if im.convert("RGB").getcolors(maxcolors=FLAT_COLOR_CEILING)
                else ".jpg"
            )
    except OSError as exc:
        print(f"  WARN could not inspect {src.name} ({exc}); keeping PNG")
        return ".png"


def resize_to(src: Path, dest: Path, max_w: int) -> tuple[int, int]:
    """Downscale to fit max_w and return the written size.

    Only ever shrinks. Aspect ratio is preserved exactly, and images
    narrower than max_w are left at their native size - upscaling a small
    logo to poster width would just make it blurry.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        # Apply camera orientation before anything else. Without this, a
        # portrait photo tagged orientation=8 ships sideways - the pixels
        # are landscape, the EXIF flag says rotate, and we were ignoring it.
        im = ImageOps.exif_transpose(im)
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


def probe_mp4_size(path: Path) -> tuple[int, int]:
    """Read display dimensions out of an MP4's track header.

    ffmpeg isn't a dependency here, and without dimensions the page would
    reflow as the video loads. Width and height are the last eight bytes
    of a tkhd box, stored as 16.16 fixed point.
    """

    def walk(f, end: int) -> tuple[int, int]:
        while f.tell() < end - 8:
            start = f.tell()
            header = f.read(8)
            if len(header) < 8:
                break
            size = int.from_bytes(header[:4], "big")
            kind = header[4:8]
            if size == 1:  # 64-bit extended size
                size = int.from_bytes(f.read(8), "big")
            if size < 8:
                break
            stop = start + size

            if kind in (b"moov", b"trak", b"mdia"):
                found = walk(f, stop)
                if found != (0, 0):
                    return found
            elif kind == b"tkhd":
                payload = f.read(stop - f.tell())
                if len(payload) >= 8:
                    w = int.from_bytes(payload[-8:-4], "big") >> 16
                    h = int.from_bytes(payload[-4:], "big") >> 16
                    if w and h:
                        return w, h
            f.seek(stop)
        return 0, 0

    try:
        with path.open("rb") as f:
            return walk(f, path.stat().st_size)
    except OSError:
        return 0, 0


def has_white_background(path: Path) -> bool:
    """True if all four corners are effectively white.

    Used to decide whether padding a figure with white will blend into
    the artwork or just frame it in a border it was never meant to have.
    """
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            w, h = im.size
            if w < 6 or h < 6:
                return False
            corners = [(2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)]
            return all(min(im.getpixel(c)) >= 242 for c in corners)
    except OSError:
        return False


def build_images(proj: Project, out_dir: Path) -> None:
    for image in proj.images:
        if image.is_video:
            dest = out_dir / image.full_rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image.src, dest)
            w, h = probe_mp4_size(image.src)
            image.width, image.height = w, h
            image.shape = image.shape_hint or (classify_shape(w, h) if w else "wide")
            continue

        w, h = resize_to(image.src, out_dir / image.full_rel, FULL_MAX_W)
        tw, _th = resize_to(image.src, out_dir / image.thumb_rel, THUMB_MAX_W)
        image.width, image.height = w, h
        image.thumb_w = tw
        image.shape = image.shape_hint or classify_shape(w, h)
        # Marks are usually supplied on white and look cramped against the
        # frame edge. Full-bleed artwork is not, and would just get a white
        # border it was never designed to have.
        image.matte = image.shape == "small" and has_white_background(
            out_dir / image.full_rel
        )

    for photo in proj.photos:
        w, h = resize_to(photo.src, out_dir / photo.full_rel, FULL_MAX_W)
        tw, _th = resize_to(photo.src, out_dir / photo.thumb_rel, THUMB_MAX_W)
        photo.width, photo.height = w, h
        photo.thumb_w = tw
        photo.shape = classify_shape(w, h)

    for block_photos in proj.photo_blocks.values():
        for photo in block_photos:
            w, h = resize_to(photo.src, out_dir / photo.full_rel, FULL_MAX_W)
            tw, _th = resize_to(photo.src, out_dir / photo.thumb_rel, THUMB_MAX_W)
            photo.width, photo.height = w, h
            photo.thumb_w = tw
            photo.shape = classify_shape(w, h)


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
  <!-- Same-origin fonts: no preconnect, no third-party render block. -->
  <link rel="preload" href="/fonts/inter-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="preload" href="/fonts/archivo-latin-standard-normal.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="{css_prefix}styles.css">
  <link rel="stylesheet" href="{css_prefix}work.css">
  <meta name="theme-color" content="#0b0b0c" media="(prefers-color-scheme: dark)">
  <meta name="theme-color" content="#fafaf8" media="(prefers-color-scheme: light)">
  <!-- Before first paint, or a stored light preference flashes dark. -->
  <script>
    (function () {{
      try {{
        var t = localStorage.getItem('theme');
        if (t === 'light' || t === 'dark') {{
          document.documentElement.setAttribute('data-theme', t);
        }}
      }} catch (e) {{}}
    }})();
  </script>
</head>
<body>
  <a href="#main" class="skip-link">Skip to content</a>
"""

FOOTER = """
  <footer>
    <p>&copy; {year} {owner} &mdash; Design, Marketing &amp; Content Production</p>
  </footer>
  <button id="back-to-top" aria-label="Back to top">&uarr;</button>
  <button id="theme-toggle" class="theme-toggle" aria-label="Switch theme">
    <span class="icon-light" aria-hidden="true">&#9728;</span>
    <span class="icon-dark" aria-hidden="true">&#9790;</span>
  </button>
  <div id="lightbox" class="lightbox" hidden>
    <button class="lightbox-close" aria-label="Close">&times;</button>
    <img id="lightbox-img" alt="">
  </div>
  <script>
    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    function scrollBehavior() {{ return reduceMotion.matches ? 'auto' : 'smooth'; }}
    var btt = document.getElementById('back-to-top');
    window.addEventListener('scroll', function () {{
      btt.classList.toggle('visible', window.scrollY > 400);
    }}, {{ passive: true }});
    btt.addEventListener('click', function () {{
      window.scrollTo({{ top: 0, behavior: scrollBehavior() }});
    }});
    (function() {{
      var lb = document.getElementById('lightbox');
      var lbImg = document.getElementById('lightbox-img');
      var lbClose = lb.querySelector('.lightbox-close');
      // Remembers what opened the lightbox so focus can go back there on
      // close - otherwise a keyboard user is dumped at the top of the page.
      var lastTrigger = null;
      function open(src, alt, trigger) {{
        lastTrigger = trigger || null;
        lbImg.src = src;
        lbImg.alt = alt || '';
        lb.hidden = false;
        document.body.style.overflow = 'hidden';
        lbClose.focus();
      }}
      function close() {{
        lb.hidden = true;
        lbImg.src = '';
        document.body.style.overflow = '';
        if (lastTrigger) {{ lastTrigger.focus(); lastTrigger = null; }}
      }}
      document.querySelectorAll('a.lightbox-trigger').forEach(function(a) {{
        a.addEventListener('click', function(e) {{
          e.preventDefault();
          var img = a.querySelector('img');
          open(a.getAttribute('href'), img ? img.getAttribute('alt') : '', a);
        }});
      }});
      lb.addEventListener('click', function(e) {{
        if (e.target === lb || e.target === lbClose) close();
      }});
      document.addEventListener('keydown', function(e) {{
        if (e.key === 'Escape' && !lb.hidden) close();
      }});
    }})();
  </script>
  <!-- Absolute, so one path is correct from /work/ and /work/slug/ alike. -->
  <script src="/theme.js"></script>
</body>
</html>
"""


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def render_work_card(p: Project, href: str, tile: str = "") -> str:
    """One project card. Shared by /work/ and the home page, so the two
    can never drift apart or show a different set of projects.

    `tile` adds a bento size class on the home page. The index stays
    uniform: a dense, filterable record is easier to scan when every row
    is the same height, and varied tiles would fight the filters.
    """
    still = p.card_image
    thumb = f"{href}{still.thumb_rel}" if still else ""
    # A logo cropped to fill a 4:3 card loses its ends. Marks get contained
    # and centred on white instead, which is how a logo is meant to sit.
    mark_cls = " is-mark" if still and still.shape_hint == "small" else ""
    haystack = " ".join(
        [p.title, p.client, p.category, p.year, " ".join(p.tags), p.summary]
    ).lower()
    # Half of a cross-document view transition. The project page gives its
    # first figure this same name, so the browser morphs the thumbnail into
    # the full image instead of cutting to a new page. Names have to be
    # unique per document, and a slug appears once per grid, so this holds.
    vt = f' style="view-transition-name:shot-{p.slug}"'
    img = (
        f'<img src="{thumb}" alt="{esc(p.heading)}" loading="lazy"{vt}>'
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
    return f"""      <a class="work-card{tile}" href="{href}"
         data-cat="{esc(p.category)}" data-div="{p.division}"
         data-work="{p.work_group}"
         data-search="{esc(haystack)}">
        <div class="work-card-img{mark_cls}">{img}{card_badge}</div>
        <div class="work-card-info">
          {f'<span class="work-card-client">{esc(p.client)}</span>' if p.client else ''}
          <h2 class="work-card-title">{esc(p.title)}</h2>
          {f'<p class="work-card-summary">{esc(p.summary)}</p>' if p.summary else ''}
          <div class="work-card-meta">
            <span>{esc(p.category)}</span>{f'<span>{esc(p.year)}</span>' if p.year else ''}
          </div>
        </div>
      </a>"""


def render_404() -> str:
    """Without this, Cloudflare Pages answers every unmatched path with the
    home page at HTTP 200, so a mistyped project link looks like it worked
    and search engines index junk URLs as real pages."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Page not found &mdash; {esc(OWNER)}</title>
  <meta name="robots" content="noindex">
  <link rel="preload" href="/fonts/inter-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="preload" href="/fonts/archivo-latin-standard-normal.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="/styles.css">
  <link rel="stylesheet" href="/work.css">
</head>
<body>
  <header class="work-header">
    <div class="container">
      <h1 class="work-title">Page not found</h1>
      <p class="work-sub">That page doesn't exist, or it moved.</p>
      <div class="gallery-filters">
        <a class="filter-btn" href="/">Home</a>
        <a class="filter-btn" href="/work/">All work</a>
      </div>
    </div>
  </header>
</body>
</html>
"""


def render_home_cards(projects: list[Project]) -> str:
    """Project cards for the home page work section.

    Only `featured: true` projects appear here - the home page is a
    highlights reel, and /work/ is the complete record. They keep the same
    most-recent-first order as the index so moving between the two never
    feels like moving between two different sites.

    If nothing is flagged featured, everything shows: a silently empty work
    section on the home page would be far worse than an unfiltered one.
    """
    if not projects:
        return '<p class="section-desc">No projects published yet.</p>'

    picked = [p for p in projects if p.featured]
    if not picked:
        print("  WARN no featured projects; home page is showing all of them")
        picked = projects

    # Bento rhythm, deterministic rather than random so the build is
    # reproducible and a rebuild never reshuffles the page. Every fifth
    # tile is double width, which walks the wide tile across the rows and
    # keeps a four-column grid exactly full: 2+1+1, then 1+2+1, then
    # 1+1+2. No gaps to fill and no masonry needed.
    cards = "\n".join(
        render_work_card(
            p, f"work/{p.slug}/", tile=" bento-lg" if i % 5 == 0 else ""
        )
        for i, p in enumerate(picked)
    )
    return f'<div class="work-grid bento">\n{cards}\n      </div>'


# Display cap per shape tier, in CSS pixels. Mirrors the tiers in work.css -
# the two have to agree or `sizes` lies to the browser and it picks the wrong
# candidate. Kept here as the single source of truth for both.
SHAPE_CAP = {"wide": 960, "tall": 640, "medium": 560, "small": 400}


def srcset_attrs(image: ProjectImage, cap: int | None = None) -> str:
    """Responsive candidates for one image, as ` srcset="..." sizes="..."`.

    The thumb alone is enough at 1x, but a 760-1180px figure on a 2x display
    needs roughly double that in real pixels, and the full-size render is
    already on disk for the lightbox. Offering both lets the browser take the
    small file on a phone and the large one on a retina laptop.

    Returns an empty string when there is no second candidate to offer, so a
    narrow source never advertises a width it does not have.
    """
    if not image.thumb_w or not image.width or image.width <= image.thumb_w:
        return ""

    box = cap if cap is not None else SHAPE_CAP.get(image.shape, 760)
    srcset = f"{image.thumb_rel} {image.thumb_w}w, {image.full_rel} {image.width}w"
    # Below the breakpoint the figure is fluid to the viewport; above it, the
    # tier caps it. Stated in that order because the browser takes the first
    # matching clause.
    sizes = f"(min-width: {box + 80}px) {box}px, 100vw"
    return f' srcset="{srcset}" sizes="{sizes}"'


def render_figure(image: ProjectImage, proj: Project, eager: bool) -> str:
    """One gallery figure. Shared by inline placement and the trailing set."""
    cap = f"<figcaption>{esc(image.caption)}</figcaption>" if image.caption else ""
    # The figure's own native width, handed to CSS as a custom property so
    # the shape tiers can compose with it - `min(native, tier)` - instead of
    # having to out-specify an inline style with !important.
    cap_px = f' style="--native-w:{image.width}px"' if image.width else ""
    dims = (
        f' width="{image.width}" height="{image.height}"'
        if image.width and image.height
        else ""
    )

    if image.is_video:
        # Muted and looping so it behaves like a motion sample rather
        # than something that ambushes you with sound.
        return f"""      <figure class="proj-figure is-{image.shape}"{cap_px}>
        <video src="{image.full_rel}"{dims} controls loop muted playsinline
               preload="metadata" aria-label="{esc(image.caption or proj.heading)}"></video>
        {cap}
      </figure>"""

    matte = " has-matte" if image.matte else ""
    loading = "eager" if eager else "lazy"
    # The other half of the view transition, and it pairs on the card image
    # specifically - that is the exact still the thumbnail was showing, so
    # the morph lands on the same picture rather than cross-fading into a
    # different one.
    #
    # Identity, not `eager`. Two duplicate names in one document make the
    # transition invalid and the browser silently drops it, and `eager` is
    # computed separately by the inline and trailing render paths, so both
    # can believe they are first. Only one image object can be the card
    # image, so this is unique by construction.
    vt = (
        f' style="view-transition-name:shot-{proj.slug}"'
        if image is proj.card_image
        else ""
    )
    return f"""      <figure class="proj-figure is-{image.shape}{matte}"{cap_px}>
        <a href="{image.full_rel}" class="lightbox-trigger">
          <img src="{image.thumb_rel}"{srcset_attrs(image)} alt="{esc(image.caption or proj.heading)}"{dims} loading="{loading}" decoding="async"{vt}>
        </a>
        {cap}
      </figure>"""


def render_slideshow(proj: Project, photos: list[ProjectImage] | None = None,
                     id_suffix: str = "") -> str:
    """One slideshow for a project's event photography.

    Every slide ships in the HTML so the set is crawlable and works with
    JavaScript disabled - without JS it degrades to a plain vertical run
    of photos, which is a worse experience but never a broken one.
    """
    if photos is None:
        photos = proj.photos
    if not photos:
        return ""

    elem_id = f"shots-{id_suffix}" if id_suffix else "shots"

    slides = []
    for i, photo in enumerate(photos):
        cap = (
            f'<figcaption class="slide-cap">{esc(photo.caption)}</figcaption>'
            if photo.caption
            else ""
        )
        dims = (
            f' width="{photo.width}" height="{photo.height}"'
            if photo.width and photo.height
            else ""
        )
        slides.append(
            f'        <figure class="slide" data-i="{i}">\n'
            f'          <div class="slide-frame">\n'
            f'            <a href="{photo.full_rel}" class="lightbox-trigger"><img src="{photo.thumb_rel}" alt="{esc(photo.caption or proj.heading)}"'
            f'{dims} loading="{"eager" if i == 0 else "lazy"}"></a>\n'
            f"          </div>\n"
            f"          {cap}\n"
            f"        </figure>"
        )

    dots = "".join(
        f'<button class="slide-dot" data-go="{i}" aria-label="Photo {i + 1}"></button>'
        for i in range(len(photos))
    )

    return f"""    <div class="proj-slideshow" id="{elem_id}" data-count="{len(photos)}">
      <div class="slide-track">
{chr(10).join(slides)}
      </div>
      <div class="slide-controls">
        <button class="slide-btn" data-step="-1" aria-label="Previous photo">&larr;</button>
        <p class="slide-count"><span class="slide-now">1</span> / {len(photos)}</p>
        <button class="slide-btn" data-step="1" aria-label="Next photo">&rarr;</button>
      </div>
      <div class="slide-dots">{dots}</div>
    </div>

    <script>
      (function () {{
        var box = document.getElementById('{elem_id}');
        if (!box) return;
        var slides = box.querySelectorAll('.slide');
        var dots = box.querySelectorAll('.slide-dot');
        var now = box.querySelector('.slide-now');
        var at = 0;

        box.classList.add('is-live');

        function show(i) {{
          at = (i + slides.length) % slides.length;
          for (var s = 0; s < slides.length; s++) {{
            slides[s].classList.toggle('is-on', s === at);
            if (dots[s]) dots[s].classList.toggle('is-on', s === at);
          }}
          now.textContent = at + 1;
        }}

        box.querySelectorAll('.slide-btn').forEach(function (b) {{
          b.addEventListener('click', function () {{
            show(at + parseInt(b.dataset.step, 10));
          }});
        }});
        dots.forEach(function (d) {{
          d.addEventListener('click', function () {{
            show(parseInt(d.dataset.go, 10));
          }});
        }});
        document.addEventListener('keydown', function (e) {{
          if (e.key === 'ArrowLeft') show(at - 1);
          if (e.key === 'ArrowRight') show(at + 1);
        }});

        show(0);
      }})();
    </script>
"""


def render_grid(proj: Project, photos: list[ProjectImage],
                 id_suffix: str = "", grid_cls: str = "") -> str:
    """A tiled grid for collections of small marks (logos, badges).

    Each item is a self-contained figure with object-fit: contain so
    logos aren't cropped. Degrades gracefully without JavaScript.
    """
    if not photos:
        return ""

    tiles = []
    for i, photo in enumerate(photos):
        cap = (
            f'<figcaption class="grid-cap">{esc(photo.caption)}</figcaption>'
            if photo.caption
            else ""
        )
        dims = (
            f' width="{photo.width}" height="{photo.height}"'
            if photo.width and photo.height
            else ""
        )
        tiles.append(
            f'        <figure class="grid-tile">\n'
            f'          <div class="grid-tile-img">\n'
            f'            <a href="{photo.full_rel}" class="lightbox-trigger"><img src="{photo.thumb_rel}" alt="{esc(photo.caption or proj.heading)}"'
            f'{dims} loading="{"eager" if i < 4 else "lazy"}"></a>\n'
            f"          </div>\n"
            f"          {cap}\n"
            f"        </figure>"
        )

    cls = f"proj-grid {grid_cls}" if grid_cls else "proj-grid"
    elem_id = f"grid-{id_suffix}" if id_suffix else "grid"
    return f"""    <div class="{cls}" id="{elem_id}">
{chr(10).join(tiles)}
    </div>
"""


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

    # Role is not repeated here - it leads the credits block below, which
    # states it alongside the team rather than as a bare label.
    meta_bits = [b for b in (proj.category, proj.year) if b]
    # For commissioned work there's no disclaimer to carry it, so the
    # context (studio, contract, employer) belongs in the meta row.
    if proj.context and proj.work_type in COMMISSIONED:
        meta_bits.append(proj.context)

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

    # Credits lead the write-up rather than trailing it. On directed work
    # the reader should know who ran it and who executed before reading
    # the story, and naming the team makes the direction claim credible
    # instead of looking like ownership of other people's work.
    credits = ""
    if proj.role or proj.team:
        rows = []
        if proj.role:
            rows.append(
                '<div class="proj-credit-row is-lead">'
                f'<span class="proj-credits-label">{esc(proj.role)}</span>'
                f'<span class="proj-credit-name">{esc(OWNER)}</span></div>'
            )
        if proj.team:
            names = ", ".join(esc(n) for n in proj.team)
            rows.append(
                '<div class="proj-credit-row">'
                '<span class="proj-credits-label">Design team</span>'
                f'<span class="proj-credit-name">{names}</span></div>'
            )
        credits = f'<div class="proj-credits">{"".join(rows)}</div>'

    # The client's verdict closes the write-up. Attribution is required -
    # an unattributed testimonial is worth nothing to a reader.
    testimonial = ""
    if proj.quote and proj.quote_by:
        testimonial = (
            '<figure class="proj-testimonial">'
            f'<blockquote>{esc(proj.quote)}</blockquote>'
            f'<figcaption>{esc(proj.quote_by)}</figcaption>'
            "</figure>"
        )
    elif proj.quote:
        print(f"  WARN {proj.slug}: quote has no quote_by, omitting")

    parts.append(f"""
  <header class="proj-header">
    <div class="container">
      <nav class="crumbs">
        <a href="../../">Home</a>
        <span>/</span>
        <a href="../">Portfolio</a>
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

  <main id="main" class="container proj-main">""")

    # The write-up is split at any inline image reference so figures sit
    # between blocks of copy at full container width. Text keeps its
    # reading measure; images are not squeezed into it.
    by_name = {im.src.name: im for im in proj.images}
    placed: set[str] = set()
    shown = 0
    lead = f"{disclaimer}\n      {credits}"

    def render_segments(body_html: str, lead_html: str) -> tuple[list[str], bool, str]:
        """Split body HTML at image/photo markers and return rendered
        parts, whether photos were placed, and the consumed lead."""
        seg_parts: list[str] = []
        seg_photos_placed = False
        seg_lead = lead_html
        seg_shown = 0

        segments = re.split(
            r"<!--IMG:(.+?)-->|<!--PHOTOS(?::([a-z0-9_-]+))?-->|<!--GRID:([a-z0-9_-]+)(?::([a-z]+))?-->",
            body_html,
        )
        for i, segment in enumerate(segments):
            if i % 5 == 1:  # IMG capture group
                if segment is None:  # PHOTOS or GRID branch matched
                    continue
                image = by_name.get(segment)
                if image is None:
                    print(f"  WARN {proj.slug}: no image named '{segment}'")
                    continue
                placed.add(segment)
                seg_parts.append(
                    f'    <div class="proj-gallery">\n'
                    f"{render_figure(image, proj, eager=shown + seg_shown == 0)}\n    </div>\n"
                )
                seg_shown += 1
                continue
            if i % 5 == 2:  # PHOTOS capture group (named or default)
                block_name = segment
                if block_name:
                    photos = proj.photo_blocks.get(block_name, [])
                    seg_parts.append(render_slideshow(proj, photos, block_name))
                    seg_photos_placed = True
                else:
                    seg_parts.append(render_slideshow(proj))
                    seg_photos_placed = True
                continue
            if i % 5 == 3:  # GRID name capture group
                block_name = segment
                if block_name:
                    photos = proj.photo_blocks.get(block_name, [])
                    mod = segments[i + 1]
                    if mod == "wide":
                        grid_cls = "proj-grid-wide"
                    elif mod == "med":
                        grid_cls = "proj-grid-med"
                    elif mod == "large":
                        grid_cls = "proj-grid-large"
                    elif mod == "xl":
                        grid_cls = "proj-grid-xl"
                    elif mod == "feature":
                        grid_cls = "proj-grid-feature"
                    else:
                        grid_cls = ""
                    seg_parts.append(render_grid(proj, photos, block_name, grid_cls=grid_cls))
                    seg_photos_placed = True
                continue
            if i % 5 == 4:  # GRID modifier capture group (wide, etc.)
                continue

            body = segment.strip()
            if not body and not seg_lead:
                continue
            seg_parts.append(
                f'    <div class="proj-body">\n      {seg_lead}\n      {body}\n    </div>\n'
            )
            seg_lead = ""

        return seg_parts, seg_photos_placed, seg_lead

    photos_placed = False

    if proj.sections:
        # Tabbed project: split the body at <h2> tags matching section names.
        # The intro (everything before the first section heading) renders
        # as a lead block above the tabs.
        section_set = set(html.escape(s) for s in proj.sections)
        # Split on <h2>Section name</h2> boundaries
        h2_pattern = r'<h2>([^<]+)</h2>'
        h2_matches = list(re.finditer(h2_pattern, proj.body_html))

        # Find which h2s match our section names
        section_starts = []
        for m in h2_matches:
            heading_text = m.group(1).strip()
            if heading_text in section_set:
                section_starts.append(m)

        if section_starts:
            # Intro is everything before the first section heading
            intro_html = proj.body_html[:section_starts[0].start()].strip()
            if intro_html:
                intro_parts, intro_photos, _ = render_segments(intro_html, lead)
                parts.extend(intro_parts)
                if intro_photos:
                    photos_placed = True
                lead = ""

            # Tab bar
            tab_buttons = []
            for idx, sec_name in enumerate(proj.sections):
                active = " active" if idx == 0 else ""
                tab_buttons.append(
                    f'<button class="proj-tab-btn{active}" data-tab="{idx}" '
                    f'type="button">{esc(sec_name)}</button>'
                )
            parts.append(
                f'    <div class="proj-tabs">\n'
                f'      <div class="proj-tab-bar">{" ".join(tab_buttons)}</div>\n'
            )

            # Each section pane
            for idx, sec_name in enumerate(proj.sections):
                # Find the matching h2
                sec_escaped = html.escape(sec_name)
                start_match = None
                for m in section_starts:
                    if m.group(1).strip() == sec_escaped:
                        start_match = m
                        break
                if not start_match:
                    continue

                # Section content goes from after this h2 to the start of
                # the next section h2 (or end of body)
                content_start = start_match.end()
                content_end = len(proj.body_html)
                for m in section_starts:
                    if m.start() > start_match.start():
                        content_end = m.start()
                        break

                section_html = proj.body_html[content_start:content_end].strip()
                pane_parts, pane_photos, _ = render_segments(section_html, "")
                pane_hidden = "" if idx == 0 else ' style="display:none"'
                parts.append(
                    f'      <div class="proj-tab-pane" data-pane="{idx}"{pane_hidden}>\n'
                )
                parts.extend(pane_parts)
                if pane_photos:
                    photos_placed = True
                parts.append('      </div>\n')

            # Tab switching script
            parts.append("""    </div>
    <script>
      (function () {
        var bar = document.querySelector('.proj-tab-bar');
        if (!bar) return;
        var btns = bar.querySelectorAll('.proj-tab-btn');
        var panes = document.querySelectorAll('.proj-tab-pane');
        btns.forEach(function (btn) {
          btn.addEventListener('click', function () {
            var idx = btn.dataset.tab;
            btns.forEach(function (b) { b.classList.toggle('active', b === btn); });
            panes.forEach(function (p) {
              p.style.display = p.dataset.pane === idx ? '' : 'none';
            });
          });
        });
      })();
    </script>
""")
        else:
            # No matching h2s found, fall through to normal rendering
            body_parts, body_photos, _ = render_segments(proj.body_html, lead)
            parts.extend(body_parts)
            if body_photos:
                photos_placed = True
            lead = ""
    else:
        body_parts, body_photos, _ = render_segments(proj.body_html, lead)
        parts.extend(body_parts)
        if body_photos:
            photos_placed = True
        lead = ""

    if proj.photos and not photos_placed:
        parts.append(render_slideshow(proj))

    remaining = [im for im in proj.images if im.src.name not in placed and not im.thumb_only]
    if remaining:
        parts.append('    <div class="proj-gallery">')
        for image in remaining:
            parts.append(render_figure(image, proj, eager=shown == 0))
            shown += 1
        parts.append("    </div>")

    tags_html = (
        '<div class="proj-tags">'
        + "".join(f'<span class="proj-tag">{esc(t)}</span>' for t in proj.tags)
        + "</div>"
        if proj.tags
        else ""
    )
    if testimonial or tags_html:
        parts.append(
            f'    <div class="proj-body proj-body-close">\n'
            f"      {testimonial}\n      {tags_html}\n    </div>\n"
        )

    parts.append("""
    <div class="proj-nav">
      <a href="../" class="proj-nav-btn">&larr; Full Portfolio</a>
      <a href="../../#contact" class="proj-nav-btn proj-nav-cta">Get In Touch</a>
    </div>
  </main>
""")
    parts.append(FOOTER.format(year=date.today().year, owner=esc(OWNER)))
    return "".join(parts)


def render_work_index(projects: list[Project]) -> str:
    cats = sorted({p.category for p in projects})
    desc = (
        f"Every published project by {OWNER}, in order from most recent to "
        "earliest - design, branding, packaging, marketing and photography."
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

    # Top-level tabs: the context the work was made in. A group with nothing
    # in it is skipped entirely rather than rendered empty, so the Competition
    # tab appears on its own the first time a competition project is added.
    groups = [g for g in WORK_GROUPS if any(p.work_group == g for p in projects)]
    if len(groups) > 1:
        tabs = []
        for g in groups:
            n = sum(1 for p in projects if p.work_group == g)
            active = " active" if g == DEFAULT_WORK_GROUP else ""
            tabs.append(
                f'<button type="button" role="tab" class="work-tab{active}"'
                f' data-work="{g}"'
                f' aria-selected="{"true" if active else "false"}">'
                f'{WORK_GROUPS[g]} <span class="filter-count">{n}</span></button>'
            )
        # "All Work" last, so the three contexts read as the primary choice
        # rather than an afterthought next to a catch-all.
        tabs.append(
            '<button type="button" role="tab" class="work-tab" data-work="all"'
            f' aria-selected="false">All Work <span class="filter-count">{len(projects)}</span></button>'
        )
        work_tabs = (
            '<div class="work-tabs" role="tablist" aria-label="Work context">'
            f'{"".join(tabs)}</div>'
        )
    else:
        work_tabs = ""

    # Secondary split, above the category filters. Only rendered once both
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
        <span class="crumb-current">Portfolio</span>
      </nav>
      <h1 class="work-title">Full Portfolio</h1>
      <p class="work-sub">{esc(desc)}</p>
      {work_tabs}
      {division_ui}
      <input type="search" id="work-search" class="work-search"
             placeholder="Search by client, project, or tag..."
             aria-label="Search projects">
      <div class="gallery-filters">{''.join(filters)}</div>
      <p class="work-count" id="work-count"></p>
    </div>
  </header>

  <main id="main" class="container work-main">
    <div class="work-grid" id="work-grid">
""")

    for p in projects:
        parts.append(render_work_card(p, f"{p.slug}/"))

    parts.append("""    </div>
    <p class="work-empty" id="work-empty" hidden>No projects match that search.</p>
  </main>
""")
    # Injected rather than hardcoded in the script, so the Python constant
    # stays the single source of truth for which tab opens first.
    parts.append(f"""
  <script>
    var WORK_DEFAULT = "{DEFAULT_WORK_GROUP}";
""")
    parts.append("""    (function () {
      var cards    = Array.prototype.slice.call(document.querySelectorAll('.work-card'));
      var buttons  = Array.prototype.slice.call(document.querySelectorAll('.filter-btn'));
      var divBtns  = Array.prototype.slice.call(document.querySelectorAll('.div-btn'));
      var workTabs = Array.prototype.slice.call(document.querySelectorAll('.work-tab'));
      var search   = document.getElementById('work-search');
      var countEl  = document.getElementById('work-count');
      var emptyEl  = document.getElementById('work-empty');
      var activeCat = 'all';
      var activeDiv = 'all';
      var activeWork = WORK_DEFAULT;

      // Scope is cumulative: the tab picks the context, the division narrows
      // it, the category narrows that, and search narrows whatever is left.
      function inWork(card) {
        return activeWork === 'all' || card.dataset.work === activeWork;
      }

      function inDiv(card) {
        return activeDiv === 'all' || card.dataset.div === activeDiv;
      }

      function inScope(card) {
        return inWork(card) && inDiv(card);
      }

      function apply() {
        var q = search.value.trim().toLowerCase();
        var shown = 0;
        cards.forEach(function (card) {
          var okCat = activeCat === 'all' || card.dataset.cat === activeCat;
          var okQ   = !q || card.dataset.search.indexOf(q) !== -1;
          var show  = inScope(card) && okCat && okQ;
          card.hidden = !show;
          if (show) shown++;
        });

        // Category filters are scoped to the active tab and division, so
        // switching context never leaves dead categories on screen.
        buttons.forEach(function (btn) {
          var cat = btn.dataset.cat;
          if (cat === 'all') { btn.hidden = false; return; }
          var n = cards.filter(function (c) {
            return inScope(c) && c.dataset.cat === cat;
          }).length;
          btn.hidden = n === 0;
          var badge = btn.querySelector('.filter-count');
          if (badge) badge.textContent = n;
        });

        // Same for the division toggle: a side with nothing in the current
        // tab would filter to an empty grid.
        divBtns.forEach(function (btn) {
          var d = btn.dataset.div;
          if (d === 'all') { btn.hidden = false; return; }
          btn.hidden = !cards.some(function (c) {
            return inWork(c) && c.dataset.div === d;
          });
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

      function setWork(name, push) {
        activeWork = name;
        workTabs.forEach(function (b) {
          var on = b.dataset.work === name;
          b.classList.toggle('active', on);
          b.setAttribute('aria-selected', on ? 'true' : 'false');
        });
        // Reset the narrower filters - the previous division or category may
        // hold nothing in this context.
        activeDiv = 'all';
        activeCat = 'all';
        divBtns.forEach(function (b) {
          b.classList.toggle('active', b.dataset.div === 'all');
        });
        buttons.forEach(function (b) {
          b.classList.toggle('active', b.dataset.cat === 'all');
        });
        if (push && window.history.replaceState) {
          var url = name === WORK_DEFAULT ? location.pathname
                                          : location.pathname + '?work=' + name;
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
      workTabs.forEach(function (btn) {
        btn.addEventListener('click', function () {
          setWork(btn.dataset.work, true);
        });
      });
      search.addEventListener('input', apply);

      // Deep links: ?work= opens a context tab, ?type= opens a division.
      // Both are honoured, so existing ?type= links keep working - but a
      // ?type= link has to widen the tab out of the default first, or it
      // would filter inside Professional and look broken.
      var params = new URLSearchParams(location.search);
      var wantWork = params.get('work');
      var wantDiv = params.get('type');

      if (wantWork && workTabs.some(function (b) { return b.dataset.work === wantWork; })) {
        setWork(wantWork, false);
      } else if (wantDiv && divBtns.some(function (b) { return b.dataset.div === wantDiv; })) {
        setWork('all', false);
        setDivision(wantDiv, false);
      } else {
        setWork(WORK_DEFAULT, false);
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


def copy_legacy(projects: list[Project]) -> None:
    for name in LEGACY_FILES:
        src = ROOT / name
        if not src.exists():
            print(f"  WARN missing {name}")
            continue
        if name == "index.html":
            # The home page is hand-written, but its work section is
            # generated, so the two can't fall out of step.
            text = src.read_text(encoding="utf-8")
            if HOME_CARDS_MARKER in text:
                text = text.replace(HOME_CARDS_MARKER, render_home_cards(projects))
            else:
                print(f"  WARN {name}: {HOME_CARDS_MARKER} not found")
            (DIST / name).write_text(text, encoding="utf-8")
            continue
        shutil.copy2(src, DIST / name)
    for pattern in LEGACY_GLOBS:
        for src in ROOT.glob(pattern):
            shutil.copy2(src, DIST / src.name)

    # Fonts keep their directory, unlike LEGACY_GLOBS which flattens into
    # the dist root - the @font-face and preload URLs both say /fonts/.
    fonts = ROOT / "fonts"
    if not fonts.is_dir():
        print("  WARN missing fonts/ - headings will fall back to system-ui")
    else:
        shutil.copytree(fonts, DIST / "fonts", dirs_exist_ok=True)
        print(f"  OK   fonts/ ({len(list(fonts.glob('*.woff2')))} files)")


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

    projects: list[Project] = []
    if PROJECTS_DIR.exists():
        for folder in sorted(PROJECTS_DIR.iterdir()):
            if not folder.is_dir():
                continue
            proj = load_project(folder)
            if proj:
                projects.append(proj)

    # Chronological, most recent first. A hiring reader sees the strongest,
    # current work before anything older. Undated work sorts last rather than
    # silently landing in 1970.
    projects.sort(key=lambda p: p.sort_key, reverse=True)

    work_dir = DIST / "work"
    work_dir.mkdir(parents=True, exist_ok=True)

    for proj in projects:
        out = work_dir / proj.slug
        out.mkdir(parents=True, exist_ok=True)
        build_images(proj, out)
        (out / "index.html").write_text(render_project_page(proj), encoding="utf-8")
        reel = f", {len(proj.photos)} photos" if proj.photos else ""
        if proj.photo_blocks:
            reel += f", {sum(len(v) for v in proj.photo_blocks.values())} photos in {len(proj.photo_blocks)} blocks"
        print(f"  OK   /work/{proj.slug}/  ({len(proj.images)} images{reel})")

    # After the projects, since the home page embeds their cards.
    copy_legacy(projects)

    (work_dir / "index.html").write_text(render_work_index(projects), encoding="utf-8")
    (DIST / "404.html").write_text(render_404(), encoding="utf-8")
    (DIST / "sitemap.xml").write_text(render_sitemap(projects), encoding="utf-8")
    (DIST / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8"
    )
    (DIST / "_headers").write_text(HEADERS, encoding="utf-8")

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
