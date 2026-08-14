"""Build numbered contact sheets from a folder of photos.

Used to review large shoot archives quickly: every frame gets a stable
number, so a selection can be made by listing numbers rather than
filenames. Writes an index.txt mapping numbers back to source paths.

    python tools/contact_sheet.py "<src folder>" <prefix> <out folder>
                                 [cell_width] [cols] [rows]
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

CELL_W = 320
COLS = 6
ROWS = 4
PAD = 10
LABEL_H = 18
BG = (24, 24, 24)
FG = (240, 240, 240)

EXTS = {".jpg", ".jpeg", ".png"}


def load_thumb(path: Path, box: tuple[int, int]) -> Image.Image | None:
    try:
        im = Image.open(path)
        im.draft("RGB", box)
        im = ImageOps.exif_transpose(im)
        im = im.convert("RGB")
        im.thumbnail(box, Image.LANCZOS)
        return im
    except Exception as exc:  # unreadable or truncated frame
        print(f"  skip {path.name}: {exc}")
        return None


def build(src: Path, prefix: str, out: Path, cell_w: int = CELL_W, cols: int = COLS, rows: int = ROWS) -> None:
    files = sorted(p for p in src.iterdir() if p.suffix.lower() in EXTS)
    if not files:
        print(f"no images in {src}")
        return

    out.mkdir(parents=True, exist_ok=True)
    cell_h = int(cell_w * 0.75)
    per_sheet = cols * rows
    sheet_w = cols * (cell_w + PAD) + PAD
    sheet_h = rows * (cell_h + LABEL_H + PAD) + PAD

    index: list[str] = []
    sheet_no = 0
    sheet = None
    draw = None

    for i, path in enumerate(files):
        slot = i % per_sheet
        if slot == 0:
            if sheet is not None:
                name = f"{prefix}-sheet-{sheet_no:02d}.jpg"
                sheet.save(out / name, quality=82, optimize=True)
                print(f"  {name}")
            sheet_no += 1
            sheet = Image.new("RGB", (sheet_w, sheet_h), BG)
            draw = ImageDraw.Draw(sheet)

        num = f"{prefix}{i + 1:03d}"
        index.append(f"{num}\t{path.name}")

        col, row = slot % cols, slot // cols
        x = PAD + col * (cell_w + PAD)
        y = PAD + row * (cell_h + LABEL_H + PAD)

        thumb = load_thumb(path, (cell_w, cell_h))
        if thumb is not None:
            sheet.paste(thumb, (x + (cell_w - thumb.width) // 2, y + (cell_h - thumb.height) // 2))
        draw.text((x + 2, y + cell_h + 3), num, fill=FG)

    if sheet is not None:
        name = f"{prefix}-sheet-{sheet_no:02d}.jpg"
        sheet.save(out / name, quality=82, optimize=True)
        print(f"  {name}")

    (out / f"{prefix}-index.txt").write_text("\n".join(index), encoding="utf-8")
    print(f"  {len(files)} frames, {sheet_no} sheets, index written")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        raise SystemExit(1)
    args = sys.argv[4:]
    build(
        Path(sys.argv[1]),
        sys.argv[2],
        Path(sys.argv[3]),
        int(args[0]) if len(args) > 0 else CELL_W,
        int(args[1]) if len(args) > 1 else COLS,
        int(args[2]) if len(args) > 2 else ROWS,
    )
