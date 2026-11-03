"""Inter, fetched once and turned into SVG outlines, so the banner needs no font at runtime."""

from __future__ import annotations

import hashlib
import io
import os
import re
import urllib.request
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

CACHE = Path(__file__).resolve().parent / ".cache"
INTER_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/inter/Inter%5Bopsz,wght%5D.ttf"
INTER_SHA256 = "29160a80ff49ddcab2c97711247e08b1fab27a484a329ce8b813d820dc559031"
INTER_FILE = CACHE / "Inter[opsz,wght].ttf"


def num(v: float) -> str:
    """One decimal place, no trailing '.0' and no negative zero."""
    s = f"{v:.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    return "0" if s == "-0" else s


def inter() -> Path:
    """Return the cached Inter variable font, downloading and verifying it on first use."""
    if not INTER_FILE.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(INTER_URL, timeout=60) as r:
            data = r.read()
        digest = hashlib.sha256(data).hexdigest()
        if digest != INTER_SHA256:
            raise SystemExit(f"Inter checksum mismatch: expected {INTER_SHA256}, got {digest}")
        INTER_FILE.write_bytes(data)
    digest = hashlib.sha256(INTER_FILE.read_bytes()).hexdigest()
    if digest != INTER_SHA256:
        raise SystemExit(f"cached Inter is corrupt ({digest}); delete {INTER_FILE} and run again")
    return INTER_FILE


def instance(opsz: float, wght: float) -> bytes:
    """One static instance of Inter as font bytes. Making one takes a few seconds, so each is kept in the
    cache next to the font it was made from; it is written whole, then renamed, so a reader never sees half."""
    path = CACHE / f"Inter-{INTER_SHA256[:12]}-opsz{opsz:g}-wght{wght:g}.ttf"
    if path.exists():
        return path.read_bytes()
    font = instancer.instantiateVariableFont(TTFont(inter()), {"opsz": opsz, "wght": wght})
    buf = io.BytesIO()
    font.save(buf)
    data = buf.getvalue()
    part = path.with_name(f"{path.name}.{os.getpid()}.part")
    part.write_bytes(data)
    os.replace(part, path)
    return data


class Face:
    """One static instance of Inter (for example opsz=32, wght=600), shaped with HarfBuzz."""

    def __init__(self, opsz: float, wght: float) -> None:
        data = instance(opsz, wght)
        self.font = TTFont(io.BytesIO(data))
        self.hb = hb.Font(hb.Face(hb.Blob(data)))
        self.upem: int = self.font["head"].unitsPerEm
        self.glyphs = self.font.getGlyphSet()
        self.order: list[str] = self.font.getGlyphOrder()

    def _shape(self, text: str, size: float) -> list[tuple[str, float, float, float]]:
        """(glyph name, x offset, y offset, advance) for each glyph, in pixels."""
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf, {"kern": True, "liga": True, "calt": True})
        k = size / self.upem
        return [(self.order[i.codepoint], p.x_offset * k, p.y_offset * k, p.x_advance * k)
                for i, p in zip(buf.glyph_infos, buf.glyph_positions)]

    def width(self, text: str, size: float, tracking: float = 0.0) -> float:
        """Advance width of `text` in pixels; `tracking` is in em."""
        glyphs = self._shape(text, size)
        return sum(g[3] for g in glyphs) + tracking * size * (len(glyphs) - 1)

    def path(self, text: str, size: float, x: float, y: float, tracking: float = 0.0) -> str:
        """SVG path data for `text`, centred on x, with its baseline at y."""
        glyphs = self._shape(text, size)
        pen_x = x - self.width(text, size, tracking) / 2
        k = size / self.upem
        pen = SVGPathPen(self.glyphs, ntos=num)
        for name, dx, dy, advance in glyphs:
            self.glyphs[name].draw(TransformPen(pen, (k, 0, 0, -k, pen_x + dx, y - dy)))
            pen_x += advance + tracking * size
        return pen.getCommands()


# ---------------------------------------------------------------- compact outlines, for the small cards

_ARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "Q": 4, "C": 6, "Z": 0}
_TOKEN = re.compile(r"[MLHVQCZ]|-?\d*\.?\d+")


def _short(tenths: int) -> str:
    """Tenths of a unit as the shortest SVG number: 5 -> .5, -5 -> -.5, 120 -> 12."""
    s = num(tenths / 10)
    if s.startswith("0."):
        return s[1:]
    return "-" + s[2:] if s.startswith("-0.") else s


def _join(vals: list[int]) -> str:
    out, prev = "", ""
    for v in vals:
        t = _short(v)
        # a separator is needed unless a sign or a second decimal point already splits the numbers
        if prev and not (t.startswith("-") or (t.startswith(".") and "." in prev)):
            out += " "
        out += t
        prev = t
    return out


def relative(d: str) -> str:
    """Rewrite absolute path data with one decimal place as relative commands: the same outline exactly, in
    fewer bytes."""
    toks = _TOKEN.findall(d)
    out: list[str] = []
    cx = cy = sx = sy = 0
    i, cmd = 0, ""
    while i < len(toks):
        if toks[i] in _ARGS:
            cmd = toks[i]
            i += 1
            if cmd == "Z":
                out.append("z")
                cx, cy = sx, sy
                continue
        elif cmd == "M":
            cmd = "L"  # extra pairs after a moveto are linetos
        n = _ARGS[cmd]
        vals = [round(float(v) * 10) for v in toks[i:i + n]]
        i += n
        if cmd == "H":
            out.append("h" + _short(vals[0] - cx))
            cx = vals[0]
        elif cmd == "V":
            out.append("v" + _short(vals[0] - cy))
            cy = vals[0]
        else:
            rel: list[int] = []
            for k in range(0, n, 2):
                rel += [vals[k] - cx, vals[k + 1] - cy]
            out.append(cmd.lower() + _join(rel))
            cx, cy = vals[-2], vals[-1]
            if cmd == "M":
                sx, sy = cx, cy
    return "".join(out)


class Ink:
    """The text of one image: each glyph outline is stored once and placed with <use>. Text below `fine`
    pixels is outlined on whole units (half a pixel at the size it is shown), larger text to a tenth."""

    def __init__(self, fine: float = 32.0) -> None:
        self.ids: dict[tuple[int, str, float], str] = {}
        self.paths: list[str] = []
        self.blank: set[str] = set()
        self.fine = fine

    def _glyph(self, face: Face, name: str, size: float) -> str:
        key = (id(face), name, size)
        if key not in self.ids:
            gid = f"t{len(self.ids)}"
            self.ids[key] = gid
            k = size / face.upem
            pen = SVGPathPen(face.glyphs, ntos=num if size >= self.fine else lambda v: str(round(v)))
            face.glyphs[name].draw(TransformPen(pen, (k, 0, 0, -k, 0, 0)))
            d = pen.getCommands()
            if d:
                self.paths.append(f'<path id="{gid}" d="{relative(d)}"/>')
            else:
                self.blank.add(gid)
        return self.ids[key]

    def glyphs(self, face: Face, text: str, size: float, x: float, y: float, tracking: float = 0.0,
               spread: tuple[frozenset[str], float] = (frozenset(), 0.0)) -> list[tuple[str, str, float, float]]:
        """(glyph name, <use> markup, left, right) for each glyph of `text` set from x on the baseline y.
        `spread` names glyphs that get extra room (in em) on each side."""
        out = []
        pen_x = x
        wide, room = spread
        for name, dx, dy, advance in face._shape(text, size):
            extra = room * size if name in wide else 0.0
            pen_x += extra
            gid = self._glyph(face, name, size)
            use = "" if gid in self.blank else f'<use href="#{gid}" x="{num(pen_x + dx)}" y="{num(y - dy)}"/>'
            out.append((name, use, pen_x + dx, pen_x + dx + advance))
            pen_x += advance + tracking * size + extra
        return out

    def text(self, face: Face, text: str, size: float, x: float, y: float, tracking: float = 0.0) -> str:
        """`text` centred on x, with its baseline at y."""
        x0 = x - face.width(text, size, tracking) / 2
        return "".join(g[1] for g in self.glyphs(face, text, size, x0, y, tracking))

    def library(self) -> str:
        return "".join(self.paths)
