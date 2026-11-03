"""The stage a card's motif is drawn on: the card's geometry, its light and its palette, in card coordinates.

Every card is one view of the banner's world. Its motif (art/motifs/<key>.py) is the one quiet detail that
makes it its project's own. The card hands the motif a Stage and an Svg, and the motif returns its markup as
Layers, one string per layer of the scene.

Coordinates are card units: x to the right, y down, the origin at the top-left of the SVG's viewBox, which is
800 x 480. The visible panel is inset by a transparent margin (12 at the sides, 10 at the top and bottom) and
has rounded corners; everything a motif draws is clipped to it. A card is shown 392 px wide on a wide page, so
one unit is about half a pixel there; _preview/card.py renders a card 800 px wide, one unit to one pixel.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass

from scene import Pt, Svg, Theme, mix

# ---------------------------------------------------------------- the light over a card


@dataclass(frozen=True)
class Moment:
    sky: tuple[str, ...]        # at SKY_AT, from the top of the panel down to the horizon
    glow: str                   # the light at the horizon: the card's one touch of gold
    glow_peak: float
    core: str                   # the white heart of the light, hidden behind the number
    sea: tuple[str, str, str]   # cloud: glowing edge, body, shade
    sea_warm: str
    glade: str
    haze: str
    reach: float                # how strongly the far cloud fades into the haze: more at night
    stars: float


SKY_AT = (0.0, 0.48, 0.8, 1.0)


# ---------------------------------------------------------------- geometry


@dataclass(frozen=True)
class Box:
    """An axis-aligned box in card units: left, top, right, bottom."""
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def w(self) -> float:
        return self.x1 - self.x0

    @property
    def h(self) -> float:
        return self.y1 - self.y0

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2

    def grow(self, d: float) -> Box:
        return Box(self.x0 - d, self.y0 - d, self.x1 + d, self.y1 + d)

    def hits(self, o: Box) -> bool:
        """Whether the two boxes overlap (touching edges do not count)."""
        return self.x0 < o.x1 and o.x0 < self.x1 and self.y0 < o.y1 and o.y0 < self.y1

    def holds(self, o: Box) -> bool:
        """Whether `o` lies wholly inside this box."""
        return self.x0 <= o.x0 and o.x1 <= self.x1 and self.y0 <= o.y0 and o.y1 <= self.y1


def flank(panel: Box, keep_out: tuple[Box, ...], y0: float, y1: float, left: bool) -> Box:
    """The widest box from the panel's left (or right) edge across y0..y1 that touches none of `keep_out`."""
    near = [k for k in keep_out if k.y0 < y1 and y0 < k.y1]
    if left:
        return Box(panel.x0, y0, min([k.x0 for k in near], default=panel.x1), y1)
    return Box(max([k.x1 for k in near], default=panel.x0), y0, panel.x1, y1)


@dataclass(frozen=True)
class Zones:
    """Where a motif may live: boxes inside the panel that keep the stage's `air` from every line of type.
    "Outer" is the card's outer edge (left on a left card, right on a right card), "inner" the side toward
    its neighbour. A band with no room has h <= 0."""
    outer: Box          # the outer flank, top to bottom
    inner: Box          # the inner flank, top to bottom
    outer_horizon: Box  # the outer flank from under the short line to over the label: the horizon runs
                        # through it, and the default pillar stands in it
    inner_horizon: Box  # the same on the inner side
    top: Box            # full width, above the title
    gap: Box            # full width, between the short line and the number (often too thin to use)
    ground: Box         # full width, under the label: the front row of cloud


def zones_for(panel: Box, title: Box, lines: tuple[Box, ...], number: Box, label: Box, side: int,
              air: float) -> Zones:
    keep = tuple(b.grow(air) for b in (title, *lines, number, label))
    outer_left = side < 0
    lo, hi = lines[-1].y1 + air, label.y0 - air
    return Zones(
        outer=flank(panel, keep, panel.y0, panel.y1, outer_left),
        inner=flank(panel, keep, panel.y0, panel.y1, not outer_left),
        outer_horizon=flank(panel, keep, lo, hi, outer_left),
        inner_horizon=flank(panel, keep, lo, hi, not outer_left),
        top=Box(panel.x0, panel.y0, panel.x1, title.y0 - air),
        gap=Box(panel.x0, lo, panel.x1, number.y0 - air),
        ground=Box(panel.x0, label.y1 + air, panel.x1, panel.y1),
    )


# ---------------------------------------------------------------- the stage


@dataclass(frozen=True)
class Stage:
    """Everything a motif may know about its card. All positions are card units (see the module notes)."""
    key: str             # the card's key, e.g. "marionette" or "parameter-golf"
    index: int           # its place among the nine cards, 0..8, in page order: one day passes across them
    row: int             # its row of two cards on a wide page, 0..4
    side: int            # -1 on a left card (its outer edge is the left one), +1 on a right card
    dark: bool           # True from dusk on: a dark sky, light type and the banner's moonlit palette
    theme: Theme         # the card's palette: the banner's theme under this card's light. Its light_pos is
                         # `light`, so the scene's helpers light things from the right side
    moment: Moment       # this card's light: the sky stops, the glow, the cloud colours, the haze, the stars
    width: float         # the viewBox: 800
    height: float        # 480
    panel: Box           # the visible panel, (12, 10)-(788, 470); everything is clipped to it
    radius: float        # the panel's corner radius: 28
    horizon: float       # y where the far cloud plane meets the sky: 306
    base: float          # y of the number's baseline, on the near cloud tops: 322
    light: Pt            # the centre of the low light, right behind the number: (400, 306)
    title: Box           # the title (with its arrow on a linked card)
    lines: tuple[Box, ...]  # the short line, one box per line of type
    number: Box          # the number, with its unit
    label: Box           # the label under the number
    air: float           # the least room a motif keeps from any type: 24
    zones: Zones         # where a motif may live

    @property
    def type(self) -> tuple[Box, ...]:
        """Every box of type on the card."""
        return (self.title, *self.lines, self.number, self.label)

    @property
    def outer_x(self) -> float:
        """The x of the panel's outer edge."""
        return self.panel.x0 if self.side < 0 else self.panel.x1

    def clear(self, box: Box, air: float | None = None) -> bool:
        """Whether `box` lies inside the panel and keeps `air` (the stage's, by default) from all type."""
        a = self.air if air is None else air
        return self.panel.holds(box) and not any(box.hits(t.grow(a)) for t in self.type)

    def flank(self, y0: float, y1: float, outer: bool = True, air: float | None = None) -> Box:
        """The widest box from the panel's outer (or inner) edge across y0..y1 that keeps `air` from all type."""
        a = self.air if air is None else air
        return flank(self.panel, tuple(t.grow(a) for t in self.type), y0, y1, (self.side < 0) == outer)

    def rng(self, k: int) -> random.Random:
        """The card's own seeded random stream number k. The scene and the default pillar use 1..8: start a
        motif's streams at 20, one per element, so tuning one element never reshuffles another."""
        return random.Random(9000 + self.index * 100 + k)

    def sky_at(self, y: float) -> str:
        """The colour of the sky (before the glow) at height y: the colour a distant thing fades into."""
        t = min(max((y - self.panel.y0) / (self.horizon - self.panel.y0), 0.0), 1.0)
        stops = list(zip(SKY_AT, self.moment.sky))
        for (a, ca), (b, cb) in zip(stops, stops[1:]):
            if t <= b:
                return mix(ca, cb, (t - a) / (b - a))
        return stops[-1][1]


# ---------------------------------------------------------------- what a motif returns


@dataclass(frozen=True)
class Layers:
    """A motif's markup, in card coordinates, one string per layer. From back to front the card is drawn:

        the sky gradient and the stars
        sky     faint, far things high in the air: the light's glow washes over them
        the light's glow, low on the horizon behind the number
        far     things far off at the horizon: their feet sink into the far cloud plane
        the far cloud plane, out to the horizon
        mid     things standing in the sea of cloud, behind the number (the default pillar is here)
        the number
        the near cloud tops the number stands on
        near    things resting on the near cloud, in front of the number's foot but behind its marks
        the number's comma, point or slash, and its unit
        the front row of cloud, which parts around the label
        front   the very foreground: in front of all cloud, still under the type
        the title, the short line and the label

    Leave a layer empty to draw nothing there. Nothing may draw over the type."""
    sky: str = ""
    far: str = ""
    mid: str = ""
    near: str = ""
    front: str = ""


Motif = Callable[[Stage, Svg], Layers]


def drawn(svg: Svg, draw: Callable[[], object]) -> str:
    """Run one of the scene's drawing helpers, which add their markup to svg.body (draw_pillars, draw_pine,
    draw_cloud ...), and return that markup instead, for a Layers field. Their defs stay in svg.defs."""
    start = len(svg.body)
    draw()
    out = "".join(svg.body[start:])
    del svg.body[start:]
    return out
