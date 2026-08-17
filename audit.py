#!/usr/bin/env python3
"""Check that every project's captions and image references are honest.

Run before a deploy. Errors abort; warnings are advisory.

The distinction matters. An error means the page will make a claim the
files cannot support - a caption attached to a file that is not there,
or a `[[placement]]` pointing at nothing. Those produce broken figures
or silently missing work, and neither should ever reach the live site.

A warning means something is worth a look but may be entirely
deliberate: a photo held back from a slideshow, a caption that repeats
its neighbour. Curation is a judgement call and the build does not get
a vote, so warnings never fail the run.

This exists because a page once described a "digital companion" that
was three promotional slides, another claimed a commissioner report
that rendered nowhere, and a hand-made thumbnail quietly overwrote the
one the build generated. All three were invisible from the source and
obvious from the files.

    python audit.py          # check every project
    python audit.py fwa      # check one
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent / "projects"

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
VIDEO_EXTS = {".mp4", ".webm", ".mov"}
MEDIA_EXTS = IMAGE_EXTS | VIDEO_EXTS

# `[[youtube:...]]`, `[[web:...]]` and friends embed something remote.
# There is no local file to check, so they are not our business here.
REMOTE_PREFIXES = ("youtube:", "web:", "video:", "vimeo:")


class Report:
    """Collects findings so one project prints as one block."""

    def __init__(self) -> None:
        self.errors: list[tuple[str, str]] = []
        self.warnings: list[tuple[str, str]] = []

    def error(self, project: str, message: str) -> None:
        self.errors.append((project, message))

    def warn(self, project: str, message: str) -> None:
        self.warnings.append((project, message))


def parse(text: str) -> tuple[dict[str, dict[str, str]], str, str]:
    """Return ({block: {filename: caption}}, thumb, body).

    Mirrors build.py's front-matter reader rather than importing it, so
    that a change to one is caught by disagreement with the other
    instead of being silently shared.
    """
    if not text.startswith("---"):
        return {}, "", text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, "", text

    meta, body = parts[1], parts[2]
    blocks: dict[str, dict[str, str]] = {}
    thumb = ""
    current = ""

    for line in meta.splitlines():
        if not line.strip():
            continue

        if current and line[0] in " \t":
            name, _, caption = line.strip().partition(":")
            # A declaration may carry a display hint: `logo.jpg [small]`.
            # The hint is a rendering instruction, not part of the name.
            name = re.sub(r"\s*\[[^\]]*\]\s*$", "", name.strip())
            blocks[current][name] = caption.strip()
            continue

        key, _, value = line.partition(":")
        key = key.strip().lower()

        if key == "images" or key.startswith("photos"):
            current = key
            blocks.setdefault(current, {})
            continue

        current = ""
        if key == "thumb":
            thumb = value.strip()

    return blocks, thumb, body


def check(folder: Path, report: Report) -> None:
    md = folder / "project.md"
    if not md.exists():
        report.error(folder.name, "no project.md")
        return

    name = folder.name
    blocks, thumb, body = parse(md.read_text(encoding="utf-8"))
    declared = blocks.get("images", {})

    root_files = {
        f.name
        for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in MEDIA_EXTS
    }
    photo_dir = folder / "photos"
    photo_files = (
        {
            f.name
            for f in photo_dir.iterdir()
            if f.is_file() and f.suffix.lower() in MEDIA_EXTS
        }
        if photo_dir.is_dir()
        else set()
    )

    # -- Declarations must point at files that exist -------------------
    for fname in declared:
        if fname not in root_files:
            report.error(name, f"caption for missing file: {fname}")

    for block, entries in blocks.items():
        if block == "images":
            continue
        for fname in entries:
            if fname not in photo_files:
                report.error(name, f"{block} references missing file: {fname}")

    # -- Placements must resolve ---------------------------------------
    photo_blocks = {b[7:] for b in blocks if b.startswith("photos-")}
    stems = {Path(f).stem for f in root_files} | {Path(f).stem for f in photo_files}

    for ref in re.findall(r"\[\[([^\]]+)\]\]", body):
        if ref.startswith(REMOTE_PREFIXES):
            continue

        if ref.startswith(("grid:", "photos:")):
            target = ref.split(":")[1]
            # A grid may name a photo block or a single image; a photos
            # slideshow must name a block.
            if target in photo_blocks:
                continue
            if ref.startswith("grid:") and target in stems:
                continue
            report.error(name, f"placement resolves to nothing: [[{ref}]]")
            continue

        if ref not in root_files:
            report.error(name, f"placement resolves to nothing: [[{ref}]]")

    # -- The card thumbnail must exist ---------------------------------
    if thumb and thumb not in root_files:
        report.error(name, f"thumb: {thumb} is not in the project folder")

    # -- Advisory ------------------------------------------------------
    for fname in sorted(root_files):
        if fname not in declared:
            report.warn(name, f"no caption declared: {fname}")
        elif not declared[fname]:
            report.warn(name, f"empty caption: {fname}")

    for block, entries in blocks.items():
        if block == "images":
            continue
        for fname, caption in entries.items():
            if not caption:
                report.warn(name, f"empty caption: {block}/{fname}")

    # Two pieces sharing one caption in the curated set means one of them
    # is unlabelled in practice. Slideshow blocks are exempt: a run of
    # convention photographs or "Tier 1 / Tier 2 / Tier 3" is a sequence,
    # and numbering it is the correct answer rather than a lazy one.
    seen: dict[str, str] = {}
    for fname, caption in declared.items():
        if not caption:
            continue
        key = caption.lower().strip()
        if key in seen:
            report.warn(name, f"caption identical to {seen[key]}: {fname}")
        seen[key] = fname

    # Photos in the folder that no block claims never render. That is
    # often deliberate, so it is only ever a warning.
    claimed = {f for b, e in blocks.items() if b != "images" for f in e}
    for fname in sorted(photo_files - claimed):
        report.warn(name, f"photo never displayed: {fname}")


def main() -> int:
    wanted = sys.argv[1:]
    folders = sorted(p for p in ROOT.iterdir() if p.is_dir())
    if wanted:
        folders = [p for p in folders if p.name in wanted]
        if not folders:
            print(f"No such project: {', '.join(wanted)}")
            return 2

    report = Report()
    for folder in folders:
        check(folder, report)

    by_project: dict[str, list[str]] = {}
    for project, message in report.errors:
        by_project.setdefault(project, []).append(f"  ERROR  {message}")
    for project, message in report.warnings:
        by_project.setdefault(project, []).append(f"  warn   {message}")

    for project in sorted(by_project):
        print(f"\n{project}")
        for line in sorted(by_project[project]):
            print(line)

    total = len(folders)
    print(
        f"\n{total} project(s) checked: "
        f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)"
    )

    if report.errors:
        print("\nDeploy blocked. Every error above is a claim the files "
              "cannot support.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
