"""Cards: small views of the banner's world, eight for the projects and one for research.

Each card is a slice of the same vista. The headline number rises out of the sea of cloud like one of the
stone pillars: it stands on the near cloud tops, with the far cloud running out to the horizon behind its foot
and the low light right behind it. One day passes across the cards, in page order: sunrise, morning, midday,
afternoon, golden hour, sunset, dusk, moonrise and a moonlit night. Each card is one image, the same in the
light and the dark theme.

The shared world is drawn with the banner's own helpers, in the banner's coordinates (the light on x = 800),
and shifted onto the card, so the cloud and the light are the same as in the banner. Each card's motif, the one
detail that is its project's own, is drawn in card coordinates by art/motifs/<key>.py, from a Stage that holds
the card's geometry and light (stage.py). A card without a motif of its own keeps the plain edge pillar.
"""

from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass, replace

from inter import Face, Ink, num, relative
from motifs import motif
from scene import (DAY, EVENING, LIGHT_X, Quad, SeaRow, Svg, Theme, dome_y, falloff, lit_mass, make_sea, mix,
                   poly, rgb)
from stage import SKY_AT, Box, Moment, Stage, zones_for

CW = 800                    # card width in user units
SHOWN = 392                 # its width in the README: two cards and a space fit a column of 788 px or more
MX, MY = 12, 10             # transparent margins, so the gaps between cards come out even
PW, PH = CW - 2 * MX, 460   # the panel
CH = PH + 2 * MY
CX = CW / 2
TOP, BOTTOM = MY, MY + PH
RADIUS = 28                 # the banner's corner, at the same display scale
SHIFT = LIGHT_X - CX        # card x + SHIFT = banner x

TITLE_Y, LINE_Y, LINE_GAP = TOP + 76, TOP + 121, 37
HZ = TOP + 296              # the cloud horizon
BASE = HZ + 16              # the number's baseline: it stands on the near cloud tops
LABEL_Y = BASE + 64
TITLE_SIZE, TEXT_SIZE = 46, 30
METRIC_SIZE, UNIT_SIZE = 124, 60
METRIC_MAX = 600            # the widest a figure may run
TITLE_MAX = 440             # the widest a title may run: a long name is set a little smaller
LINK_CONTRAST = 4.5         # the least contrast a link title keeps with the sky behind it
TITLE_TRACK, METRIC_TRACK = -0.02, -0.03
ARROW = "↗"          # the arrow after a linked title; Inter sets it at x-height, small beside the name
POINT_SPACE = 0.03          # extra room (em) each side of a decimal point, so "1.11" does not cluster
TYPE_TOP, TYPE_FOOT = 0.76, 0.25  # how far a line of type may reach above and below its baseline (em)
AIR = 24                    # the least room a motif keeps from any type


def sx(x: float) -> float:
    return x + SHIFT


# ---------------------------------------------------------------- content


@dataclass(frozen=True)
class Card:
    key: str     # file name
    title: str
    line: str    # a "|" marks where the line breaks on the card
    metric: str
    unit: str
    label: str
    url: str

    @property
    def heading(self) -> str:
        """The title as the card sets it: the name and a small arrow, as on a link."""
        return f"{self.title} {ARROW}"

    @property
    def alt(self) -> str:
        """The card's whole meaning in words, escaped for an HTML or SVG attribute."""
        line = self.line.replace(" | ", " ")
        lead = f"{self.title}. " if ":" in line else f"{self.title}: "
        figure = f"{self.metric} {self.unit}" if self.unit else self.metric
        text = f"{lead}{line}. {figure} {self.label.replace(' · ', ', ')}."
        return text.replace("&", "&amp;").replace('"', "&quot;")


def repo(name: str, line: str, metric: str, unit: str, label: str) -> Card:
    return Card(name, name, line, metric, unit, label, f"https://github.com/aamodbhatt/{name}")


PROJECTS = (
    repo("marionette", "A polygraph for LLMs: linear probes | that catch a model lying",
         "0.896", "", "AUROC on held-out spontaneous lies"),
    repo("dreamcade", "A playable 3D dungeon dreamed by a diffusion model, in the browser",
         "21.9", "dB", "PSNR over 48-frame rollouts"),
    repo("quarry", "A LangGraph text-to-SQL agent with an MCP server",
         "162 / 162", "", "red-team cases passed"),
    repo("witness", "A retrieval-augmented fact-checker for any webpage",
         "76.4%", "", "accuracy on 20k FEVER claims"),
    repo("bitgolf", "Neural text compression with a tiny transformer",
         "1.50", "", "bits per byte, 40% smaller than brotli"),
    repo("persuadables", "Uplift modeling on a 64k-customer email A/B test",
         "+7.4", "pp", "visits for women’s-wear buyers"),
    repo("nandbox", "An 8-bit CPU that plays Snake in the browser",
         "1,521", "", "NAND gates, the only logic primitive"),
    repo("excelsior", "A spreadsheet engine that runs a transformer in its formulas",
         "5.8e-15", "", "max difference from PyTorch"),
)

RESEARCH = (
    # the PR's files tab: GitHub gives a link to a pull request itself a hover card with the PR's title
    Card("parameter-golf", "OpenAI Parameter Golf", "Test-time training with Muon on 8× H100",
         "1.1179", "", "bits per byte · merged submission (3-seed mean)",
         "https://github.com/openai/parameter-golf/pull/1148/files"),
)

# every card with its row of two on a wide page; research is the last row
ROWS: tuple[tuple[Card, int], ...] = tuple((c, i // 2) for i, c in enumerate(PROJECTS)) + tuple(
    (c, 4) for c in RESEARCH)


# ---------------------------------------------------------------- the time of day (Moment is in stage.py)


DAWN = Moment(("#9ab6da", "#d0d9e7", "#eedfd2", "#f9dbbe"), "#ffd8ae", 0.85, "#fff9f0",
              ("#fef8f2", "#bdc4da", "#999fbe"), "#ffdbb8", "#fff5ea", "#d6d9e6", 1.0, 0.0)
GOLDEN = Moment(("#a6bad6", "#d2d8e0", "#f4ddba", "#f8cc8c"), DAY.glow, 1.0, DAY.light,
                DAY.sea, DAY.sea_warm, DAY.glade, DAY.haze, 1.0, 0.0)
MORNING = Moment(("#86b6df", "#c3dcee", "#e8eee3", "#f6ebcd"), "#fff0c8", 0.75, "#ffffff",
                 ("#ffffff", "#c4d0e3", "#a2b0cb"), "#fff1d4", "#ffffff", "#d8e3ee", 1.0, 0.0)
# a soft moon-white halo behind the number at night
NIGHT = Moment(("#0b1729", "#13243d", "#22394f", "#2c445a"), "#d6e2e8", 0.45, "#e2eaee",
               ("#8197a8", "#435b74", "#2a3c52"), "#a9b9c4", "#b9c8d0", EVENING.haze, 2.0, 1.0)


def blend(a: Moment, b: Moment, t: float) -> Moment:
    def m(x: str, y: str) -> str:
        return mix(x, y, t)

    def f(x: float, y: float) -> float:
        return x + (y - x) * t

    sea = (m(a.sea[0], b.sea[0]), m(a.sea[1], b.sea[1]), m(a.sea[2], b.sea[2]))
    return Moment(tuple(m(x, y) for x, y in zip(a.sky, b.sky)), m(a.glow, b.glow), f(a.glow_peak, b.glow_peak),
                  m(a.core, b.core), sea, m(a.sea_warm, b.sea_warm), m(a.glade, b.glade), m(a.haze, b.haze),
                  f(a.reach, b.reach), f(a.stars, b.stars))


# the sun coming up: a lavender sky blushing rose toward a peach horizon
SUNRISE = Moment(("#97aad8", "#d5c8de", "#f5d3c8", "#fbcaa8"), "#ffc79e", 0.95, "#fff3e8",
                 ("#fff1ea", "#c3bfd9", "#9f9bbf"), "#ffcfb2", "#fff1e6", "#ddd7e7", 1.0, 0.0)
# the sun going down: a lilac sky over an apricot horizon, the cloud lit peach on its tops and dusky lilac below
SUNSET = Moment(("#93a7d2", "#d3bccf", "#f3bf98", "#f6a777"), "#ffad66", 1.0, "#fff0dc",
                ("#ffe4cc", "#b4a8c6", "#8b80a6"), "#ffb98c", "#ffeedd", "#d9c6d3", 1.0, 0.0)
# just after it: deep indigo overhead, a rose afterglow low in the west and the first stars
DUSK = Moment(("#121a36", "#262c55", "#4b4470", "#7a5a78"), "#f0a27e", 0.62, "#ffd9bc",
              ("#c7a7ba", "#4a4a6e", "#2c2e4c"), "#e3a48e", "#f2d5c8", "#474566", 1.6, 0.55)


@dataclass(frozen=True)
class Hour:
    moment: Moment
    dark: bool  # a dark sky: light type, and the banner's moonlit palette for the stone


# one day across the cards, in page order. From dusk on the sky is dark, so the type turns light.
DAY_PASSES = (
    Hour(SUNRISE, False),                      # sunrise
    Hour(blend(DAWN, MORNING, 0.4), False),    # morning
    Hour(MORNING, False),                      # midday
    Hour(blend(MORNING, GOLDEN, 0.5), False),  # afternoon
    Hour(GOLDEN, False),                       # golden hour, the banner's light
    Hour(SUNSET, False),                       # sunset
    Hour(DUSK, True),                          # dusk
    Hour(blend(DUSK, NIGHT, 0.55), True),      # moonrise
    Hour(NIGHT, True),                         # a moonlit night
)


def hour(index: int) -> tuple[Hour, Theme]:
    """The light over one card, and the banner theme its stone and type are drawn from."""
    h = DAY_PASSES[index]
    return h, EVENING if h.dark else DAY


def card_theme(theme: Theme, m: Moment) -> Theme:
    """The banner's theme under this moment's light. Lit rock turns a cool white here instead of gold, so the
    only gold on a card is the light behind its number."""
    return replace(theme, light_pos=(LIGHT_X, HZ), glow=m.glow, haze=m.haze, sea=m.sea, sea_warm=m.sea_warm,
                   glade=m.glade, rock_lit=mix(theme.rock_lit, m.sea[0], 0.6), rim=mix(theme.rim, m.sea[0], 0.6))


# ---------------------------------------------------------------- type

# the title is set in a link blue: a deep sky blue on a light sky (GitHub's #0969da gives only 2.9:1 on the
# pale sky behind the title) and a moonlit blue on a dark one, each taken further from the sky if it must be
# to keep LINK_CONTRAST
LINK = {False: "#174d91", True: "#7db3f2"}


def luminance(c: str) -> float:
    def lin(v: int) -> float:
        s = v / 255
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(v) for v in rgb(c))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def link_ink(skies: list[str], dark: bool) -> str:
    """The link blue for a title over a sky that runs through `skies`."""
    base, away = LINK[dark], ("#ffffff" if dark else "#0a1f40")
    for k in range(21):
        c = mix(base, away, k / 20)
        if min(contrast(c, sky) for sky in skies) >= LINK_CONTRAST:
            return c
    return away


@dataclass(frozen=True)
class Faces:
    title: Face
    unit: Face
    text: Face


def faces() -> Faces:
    # the title and the number use the banner's own Inter Display 600
    return Faces(title=Face(opsz=32, wght=600), unit=Face(opsz=32, wght=500), text=Face(opsz=18, wght=450))


ARTICLES = frozenset({"a", "an", "the"})


def balanced(text: str, face: Face, size: float) -> list[str]:
    """Split a line in two: where the card marks it with "|", or else into two lines of nearly equal width
    that never leave an article at the end of the first."""
    if "|" in text:
        return [s.strip() for s in text.split("|")]
    words = text.split()
    best: tuple[float, list[str]] = (math.inf, [text])
    for i in range(1, len(words)):
        if words[i - 1].lower() in ARTICLES:
            continue
        a, b = " ".join(words[:i]), " ".join(words[i:])
        w = max(face.width(a, size), face.width(b, size))
        if w < best[0]:
            best = (w, [a, b])
    return best[1]


@dataclass(frozen=True)
class Figure:
    """The number on its baseline. The digits go behind the near cloud, whose tops stay just below the
    baseline under the figure; the marks that reach below the baseline are drawn again over the cloud."""
    body: str     # <use> markup: the digits, standing on the cloud tops with their round feet whole
    marks: str    # the comma, decimal point or slash, drawn again over the cloud
    unit: str
    left: float
    right: float
    size: float   # the size the figure is set at


MARKS = {"comma", "period", "slash"}
POINT = (frozenset({"period"}), POINT_SPACE)


def figure(c: Card, f: Faces, ink: Ink) -> Figure:
    shown = c.metric.replace("-", "−")  # a true minus sign
    # a figure is set tight, with a little room around its point
    track, widest = METRIC_TRACK, METRIC_MAX

    def width(size: float) -> float:
        return f.title.width(shown, size, track) + 2 * POINT_SPACE * size * shown.count(".")

    size = min(METRIC_SIZE, METRIC_SIZE * widest / width(METRIC_SIZE))
    w_big = width(size)
    gap = 0.11 * size if c.unit else 0.0
    unit_size = UNIT_SIZE * size / METRIC_SIZE
    w_unit = f.unit.width(c.unit, unit_size, -0.01) if c.unit else 0.0
    x0 = CX - (w_big + gap + w_unit) / 2
    glyphs = ink.glyphs(f.title, shown, size, x0, BASE, track, POINT)
    unit = "".join(g[1] for g in ink.glyphs(f.unit, c.unit, unit_size, x0 + w_big + gap, BASE, -0.01)) \
        if c.unit else ""
    return Figure("".join(g[1] for g in glyphs), "".join(g[1] for g in glyphs if g[0] in MARKS), unit,
                  x0, x0 + w_big + gap + w_unit, size)


# ---------------------------------------------------------------- the view


@dataclass
class View:
    """The world every card shares; the card's own motif is drawn into it (art/motifs)."""
    rows: list[tuple[SeaRow, float, float, float, float]]  # each row of cloud: depth, shade at y, edge, glade
    stars: list[tuple[float, float, float, float]]


def stand_on(row: SeaRow, a: float, b: float, y: float) -> None:
    """Lower the row under the stretch a..b (banner x) so its top stays at or below y there, and the figure
    stands on it: the domes there are let down just enough to keep their gentle rise and fall."""
    def need(d: Quad) -> float:
        cx, hw, hh, _ = d
        u = (min(max(cx, a), b) - cx) / hw
        return y + hh * math.sqrt(1 - u * u) if abs(u) < 1 else -math.inf

    row.domes = [(d[0], d[1], d[2], max(d[3], need(d))) for d in row.domes]
    row.riders = [d for d in row.riders if need(d) == -math.inf]

    def floor(x: float) -> float:
        """Under the figure the body sits a little below the dome tops; elsewhere it reaches up to the
        baseline between the domes, so nothing behind shows through a gap as a fleck."""
        under = max(0.0, 1 - max(a - x, x - b, 0.0) / 40)  # 1 under the figure, easing to 0 beyond it
        return BASE - 1 + (y + 6 - (BASE - 1)) * under

    row.floor = [(x, floor(x)) for x, _ in row.floor]
    row.top = [(x, min([floor(x)] + [dome_y(x, d) for d in row.domes])) for x, _ in row.top]


def make_view(index: int, fig_half: float, label_half: float) -> View:
    """The world behind this card's motif. The sea of cloud runs in rows, as in the banner: a plane out to the
    horizon, the near cloud tops the number stands on, and a row in front that parts around the label. By
    night a few stars show in the sky beside the type."""
    def part(k: int) -> random.Random:
        return random.Random(9000 + index * 100 + k)

    reach = max(label_half + 120, 330)  # the front row rises only beyond the ends of the label
    plane = make_sea(part(3), HZ, sx(-60), sx(CW + 60), (150, 230), (3, 7), riders=0.0, spacing=12)
    veil = make_sea(part(4), BASE + 3, sx(-70), sx(CW + 70), (56, 90), (8, 14), riders=0.3, spacing=12,
                    banks=[(sx(0), 280, 1.0), (sx(CW), 280, 1.0), (sx(CX), 440, 0.36)], billows=16)
    stand_on(veil, sx(CX - fig_half - 26), sx(CX + fig_half + 26), BASE + 2)
    # keep the swells that fall on the card, above the label, and are big enough to read as cloud, not as a dash
    veil.billows = [(x, y, rx, ry) for x, y, rx, ry in veil.billows
                    if sx(-20) < x < sx(CW + 20) and y < LABEL_Y - 24 and ry > 4.5]
    front = make_sea(part(5), LABEL_Y + 40, sx(-80), sx(CW + 80), (50, 84), (22, 34), riders=0.45,
                     spacing=12, dip=30,
                     banks=[(sx(CX - reach), 300, 1.0), (sx(CX + reach), 300, 1.0), (sx(CX), 300, 0.35)])
    rows = [(plane, 0.3, HZ + 60, 2.4, 1.0), (veil, 0.18, LABEL_Y + 60, 3.6, 0.35),
            (front, 0.06, BOTTOM + 20, 4.6, 0.0)]

    rng = part(7)
    stars: list[tuple[float, float, float, float]] = []
    while len(stars) < 9:
        x, y = rng.uniform(MX + 24, CW - MX - 24), rng.uniform(TOP + 16, HZ - 70)
        clear_of_type = abs(x - CX) > 300 or y > LINE_Y + LINE_GAP + 30
        if clear_of_type and all(math.hypot(x - a, y - b) > 60 for a, b, _, _ in stars):
            stars.append((x, y, rng.uniform(0.6, 1.2), rng.uniform(0.25, 0.7)))
    return View(rows, stars)


# ---------------------------------------------------------------- drawing


def draw_sky(svg: Svg, m: Moment) -> None:
    g = svg.linear([(o, c, 1) for o, c in zip(SKY_AT, m.sky)], 0, TOP, 0, HZ, user=True)
    svg.add(f'<rect x="{sx(0)}" width="{CW}" height="{CH}" fill="url(#{g})"/>')


def draw_stars(svg: Svg, v: View, m: Moment) -> None:
    dots = []
    for x, y, r, a in v.stars:
        fade = m.stars * (1 - (y - TOP) / (HZ - TOP)) ** 0.7
        if a * fade > 0.08:
            dots.append(f'<circle cx="{num(sx(x))}" cy="{num(y)}" r="{num(r)}" opacity="{a * fade:.2f}"/>')
    if dots:
        svg.add(f'<g fill="#f4f1e4">{"".join(dots)}</g>')


def draw_glow(svg: Svg, m: Moment) -> None:
    """The light low on the horizon, right behind the number: a wide warm bloom and a white heart."""
    for rx, ry, peak, k, core in ((470, 230, 0.55, 3.4, None), (200, 64, 1.0, 2.6, m.core)):
        g = svg.ellipse(LIGHT_X, HZ, rx, ry, falloff(m.glow, m.glow_peak * peak, k=k, n=7, core=core))
        svg.add(f'<rect x="{LIGHT_X - rx}" y="{HZ - ry}" width="{2 * rx}" height="{2 * ry}" fill="url(#{g})"/>')


def ellipses(row: SeaRow) -> str:
    """A row's silhouette as one path: each dome a half ellipse standing on a block that reaches down into
    the flat body under them, so no sliver of sky shows between two shallow domes and the body."""
    out = []
    for cx, hw, hh, by in row.domes + row.riders:
        out.append(f"M{num(cx - hw)} {num(by)}a{num(hw)} {num(hh)} 0 1 1 {num(2 * hw)} 0v20h{num(-2 * hw)}Z")
    x0, x1 = row.top[0][0], row.top[-1][0]
    return "".join(out) + poly(row.floor + [(x1, BOTTOM + 40), (x0, BOTTOM + 40)])


def draw_row(svg: Svg, row: SeaRow, t: Theme, depth: float, below: float, edge: float,
             glade: float = 0.0, warmth: float = 1.0, quiet: float = 0.0, front: bool = False) -> None:
    """One row of the sea of cloud, lit the way the banner lights its masses: one silhouette in a cool body
    colour that deepens toward the row in front, a soft glowing edge along its top that warms where it faces
    the light, a few soft swells on its surface and a bright glade under the light. `warmth` (0..1) is how
    much of the light's colour reaches the row: only the rows at the horizon take any. Within `quiet` units of
    the light the glowing edge fades to a trace, so the far horizon draws no line behind the number. The
    `front` row glows: a cool edge (the light's colour stays at the horizon), a body lifted toward it, and a
    soft shadow on the side of each big dome turned from the light, as on the banner's billows."""
    lit, body, shade = (mix(c, t.haze, depth) for c in t.sea)
    if front:
        lit = mix(lit, "#ffffff", 0.7) if t.key == "day" else lit
        body, shade = mix(body, lit, 0.45), mix(shade, lit, 0.25)
    warm = mix(t.sea_warm, t.haze, depth * 0.5)
    x0, x1 = row.top[0][0], row.top[-1][0]
    ytop = min(y for _, y in row.top)
    f0 = (LIGHT_X - x0) / (x1 - x0)
    at_light = mix(lit, warm, 0.75 * warmth)
    if quiet:
        trace = mix(mix(body, lit, 0.3), at_light, 0.3)
        q0, q1 = quiet / (x1 - x0), (quiet + 140) / (x1 - x0)
        rim = svg.linear([(0, lit, 1), (f0 - q1, lit, 1), (f0 - q0, trace, 1), (f0 + q0, trace, 1),
                          (f0 + q1, lit, 1), (1, lit, 1)], x0, 0, x1, 0, user=True)
    else:
        rim = svg.linear([(0, lit, 1), (f0 - 0.3, lit, 1), (f0, at_light, 1), (f0 + 0.3, lit, 1), (1, lit, 1)],
                         x0, 0, x1, 0, user=True)
    fill = svg.linear([(0, mix(body, lit, 0.3), 1), (0.45, body, 1), (1, shade, 1)], 0, ytop, 0, below,
                      user=True)
    sid = svg.id("s")
    svg.defs.append(f'<path id="{sid}" d="{ellipses(row)}"/>')
    inner = [svg.soft_spot(LIGHT_X, ytop, 460, max(40.0, below - ytop) * 1.2,
                           falloff(t.sea_warm, 0.45 * warmth, 2.4, 6))] if warmth else []
    if front:
        for cx, hw, hh, by in row.domes:
            s = 0.0 if abs(LIGHT_X - cx) < hw * 0.3 else math.copysign(1.0, LIGHT_X - cx)
            inner.append(svg.soft_spot(cx - s * hw * 0.42, by - hh * 0.35, hw * 0.62, hh * 0.75,
                                       falloff(shade, 0.5, 2.2, 6)))
    for bx, by, brx, bry in row.billows:
        s = math.copysign(1.0, LIGHT_X - bx)
        inner.append(svg.soft_spot(bx, by, brx, bry, falloff(shade, 0.4, 2.4, 6)))
        inner.append(svg.soft_spot(bx + s * brx * 0.15, by - bry * 1.05, brx * 0.85, bry * 0.7,
                                   falloff(lit, 0.6, 2.4, 6)))
    if glade:
        for rx, ry in ((300, 22.0), (110, 9.0)):
            inner.append(svg.soft_spot(LIGHT_X, ytop + edge, rx, ry, falloff(t.glade, glade * 0.85, 3.0, 6)))
    svg.add(lit_mass(svg, f'<use href="#{sid}"/>', f"url(#{rim})", f"url(#{fill})", (0.0, -1.0), edge * 2.6,
                     edge * 0.5, "".join(inner)))


def compact(markup: str) -> str:
    """Every absolute path made only of M, L, H, V, Q, C and Z in relative form: the same shapes in fewer
    bytes. Any other path (arcs, relative commands, S or T) is left exactly as written."""
    return re.sub(r' d="(M[MLHVQCZ\d .,\-]*)"', lambda m: f' d="{relative(m.group(1))}"', markup)


def title_size(c: Card, f: Faces) -> float:
    """Titles share one size across a row of cards, set by the row's longest title."""
    row = dict((d.key, r) for d, r in ROWS)[c.key]
    widths = [f.title.width(d.heading, TITLE_SIZE, TITLE_TRACK) for d, r in ROWS if r == row]
    return min(TITLE_SIZE, TITLE_SIZE * TITLE_MAX / max(widths))


def type_box(width: float, y: float, size: float, x0: float | None = None) -> Box:
    """The room a line of type takes: its advance across (centred on the card unless x0 is given), and from
    its tallest ascender down to its deepest descender."""
    x0 = CX - width / 2 if x0 is None else x0
    return Box(x0, y - TYPE_TOP * size, x0 + width, y + TYPE_FOOT * size)


def card_stage(c: Card, f: Faces, index: int, row: int) -> Stage:
    """The stage this card's motif is drawn on: where its type sits, its light and its palette."""
    h, theme = hour(index)
    m = h.moment
    fig = figure(c, f, Ink())
    tsize = title_size(c, f)
    title = type_box(f.title.width(c.heading, tsize, TITLE_TRACK), TITLE_Y, tsize)
    lines = tuple(type_box(f.text.width(s, TEXT_SIZE), LINE_Y + i * LINE_GAP, TEXT_SIZE)
                  for i, s in enumerate(balanced(c.line, f.text, TEXT_SIZE)))
    number = type_box(fig.right - fig.left, BASE, fig.size, fig.left)
    label = type_box(f.text.width(c.label, TEXT_SIZE), LABEL_Y, TEXT_SIZE)
    side = -1 if index % 2 == 0 else 1
    panel = Box(MX, TOP, CW - MX, BOTTOM)
    return Stage(key=c.key, index=index, row=row, side=side, dark=h.dark,
                 theme=replace(card_theme(theme, m), light_pos=(CX, HZ)), moment=m, width=CW, height=CH,
                 panel=panel, radius=RADIUS, horizon=HZ, base=BASE, light=(CX, HZ), title=title, lines=lines,
                 number=number, label=label, air=AIR, zones=zones_for(panel, title, lines, number, label, side, AIR))


@dataclass(frozen=True)
class Scene:
    """Markup of the shared world, in the banner's coordinates."""
    markup: str


def compose(parts: list[str | Scene]) -> str:
    """The card's layers, back to front. Runs of the shared world are shifted from the banner's coordinates
    onto the card, one group per run; a motif's layers are in card coordinates already."""
    out: list[str] = []
    run: list[str] = []

    def flush() -> None:
        if run:
            out.append(f'<g transform="translate({num(-SHIFT)} 0)">{"".join(run)}</g>')
            run.clear()

    for p in parts:
        if isinstance(p, Scene):
            run.append(p.markup)
        elif p:  # an empty layer leaves the run of the world unbroken
            flush()
            out.append(p)
    flush()
    return "".join(out)


def card(c: Card, f: Faces, index: int, row: int) -> str:
    h, theme = hour(index)
    m = h.moment
    t = card_theme(theme, m)
    stage = card_stage(c, f, index, row)
    ink = Ink(fine=48)  # only the hero is outlined to a tenth
    fig = figure(c, f, ink)
    tsize = title_size(c, f)
    lines = balanced(c.line, f.text, TEXT_SIZE)
    v = make_view(index, (fig.right - fig.left) / 2, f.text.width(c.label, TEXT_SIZE) / 2)
    svg = Svg()
    own = motif(c.key)(stage, svg)
    if svg.body:
        raise ValueError(f"the {c.key} motif added to svg.body: it must return its markup in Layers")

    def scene() -> Scene:
        """What the scene's helpers have drawn since the last call."""
        out = Scene("".join(svg.body))
        svg.body = []
        return out

    draw_sky(svg, m)
    draw_stars(svg, v, m)
    sky = scene()
    draw_glow(svg, m)
    glow = scene()
    rows: list[Scene] = []
    light = min(1.0, m.glow_peak / 0.8)  # how strong the light is: full by day, fainter at night
    for i, (sea, depth, below, edge, glade) in enumerate(v.rows):
        draw_row(svg, sea, t, min(1.0, depth * m.reach), below, edge, glade * light ** 2, light * (i < 2),
                 quiet=250.0 if i == 0 else 0.0, front=i == 2)
        rows.append(scene())
    plane, veil, front = rows

    dark = h.dark
    label_ink = mix(t.ink_soft, t.ink, 0.7 if dark else 0.3)
    unit_ink = mix(t.ink_soft, t.ink, 0.35) if dark else t.ink_soft
    box = stage.title
    title_ink = link_ink([stage.sky_at(box.y0 + (box.y1 - box.y0) * k / 4) for k in range(5)], dark)
    words = (f'<g fill="{title_ink}">{ink.text(f.title, c.heading, tsize, CX, TITLE_Y, TITLE_TRACK)}</g>'
             f'<g fill="{t.ink_soft}">'
             + "".join(ink.text(f.text, s, TEXT_SIZE, CX, LINE_Y + i * LINE_GAP) for i, s in enumerate(lines))
             + f'</g><g fill="{label_ink}">{ink.text(f.text, c.label, TEXT_SIZE, CX, LABEL_Y)}</g>')

    # back to front: see stage.Layers
    layers = compose([sky, own.sky, glow, own.far, plane, own.mid, f'<g fill="{t.ink}">{fig.body}</g>', veil,
                      own.near, f'<g fill="{t.ink}">{fig.marks}</g><g fill="{unit_ink}">{fig.unit}</g>', front,
                      own.front])
    return compact(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CW} {CH}" role="img" aria-label="{c.alt}">'
        f"<title>{c.alt}</title>"
        f'<defs><clipPath id="panel"><rect x="{MX}" y="{TOP}" width="{PW}" height="{PH}" rx="{RADIUS}"/>'
        f'</clipPath>{"".join(svg.defs)}{ink.library()}</defs>'
        f'<g clip-path="url(#panel)">{layers}</g>{words}</svg>\n')


def readme_html(cards: tuple[Card, ...]) -> str:
    """The README markup for a set of cards: one centred paragraph, one card per line, so two sit side by side
    on a wide page and they stack on a narrow one. Nothing but the image sits inside each link."""
    links = (f'<a href="{c.url}"><img src="assets/cards/{c.key}.svg" width="{SHOWN}" alt="{c.alt}"></a>'
             for c in cards)
    return '<p align="center">\n' + "\n".join(links) + "\n</p>"
