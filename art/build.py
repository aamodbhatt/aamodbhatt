# /// script
# requires-python = ">=3.11"
# dependencies = ["fonttools==4.68.0", "uharfbuzz==0.57.0"]
# ///
"""Rebuild every image in ../assets with one command: `uv run art/build.py`."""

from __future__ import annotations

from pathlib import Path

from cards import ROWS, card, faces
from inter import Face
from motifs import source
from scene import DAY, EVENING, hero, make_vista, type_clear
from toolkit import DARK, LIGHT, TOOLS, pill

ASSETS = Path(__file__).resolve().parent.parent / "assets"


def write(out: Path, svg: str, note: str = "") -> None:
    out.write_text(svg, encoding="utf-8")
    print(f"{out.relative_to(ASSETS).as_posix()}: {out.stat().st_size / 1024:.1f} KB{note}")


def main() -> None:
    (ASSETS / "cards").mkdir(parents=True, exist_ok=True)
    name_face = Face(opsz=32, wght=600)  # Inter Display
    role_face = Face(opsz=18, wght=500)
    vista = make_vista(type_clear(name_face, role_face))
    card_faces = faces()
    for theme in (DAY, EVENING):
        write(ASSETS / f"hero-{theme.key}.svg", hero(theme, name_face, role_face, vista))
    for index, (c, row) in enumerate(ROWS):
        write(ASSETS / "cards" / f"{c.key}.svg", card(c, card_faces, index, row), f"  (motif: {source(c.key)})")
    (ASSETS / "toolkit").mkdir(exist_ok=True)
    tool_face = Face(opsz=18, wght=500)
    for palette in (LIGHT, DARK):
        for t in TOOLS:
            write(ASSETS / "toolkit" / f"{t.key}-{palette.key}.svg", pill(t, palette, tool_face))


if __name__ == "__main__":
    main()
