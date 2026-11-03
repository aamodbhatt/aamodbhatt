"""The default motif: one plain stone pillar toward the card's outer edge, whole, with sky on both sides of it,
so a pair of cards is framed the way the banner is. On a few cards a second, slender pillar stands far off in
the haze, just inside it. Every card draws this until its own motif lands.

Its geometry is public, so a motif that transforms the pillar (carves it, crowns it, hangs it on strings) can
start from exactly this one:

    p = edge_pillars(stage)              # p.near and p.far, in card coordinates
    layers = pillar_layers(stage, svg, p)
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from scene import Pillar, Pt, Svg, draw_pillars, make_pillar
from stage import Layers, Stage, drawn

EDGE_AIR, FIG_AIR = 36, 30  # the least sky between the pillar and the panel's edge, and the pillar and the number
FAR_PILLAR = frozenset({"dreamcade", "bitgolf", "parameter-golf"})  # cards with a slender pillar far off


@dataclass(frozen=True)
class EdgePillars:
    near: Pillar         # the pillar at the outer edge: its foot sinks into the near cloud
    far: Pillar | None   # the slender one far off in the haze, standing in the far cloud (on a few cards)


def thin(pts: list[Pt], keep: int = 2) -> list[Pt]:
    """Every `keep`-th point and the last: the banner's outlines are finer than a card can show. An empty list
    (a bare summit's canopy) stays empty."""
    return pts[::keep] + ([pts[-1]] if pts and (len(pts) - 1) % keep else [])


def thinned(p: Pillar) -> Pillar:
    return replace(p, outline=thin(p.outline), edge=thin(p.edge), face=thin(p.face), glint=thin(p.glint),
                   shade=thin(p.shade), cap=thin(p.cap), canopy=thin(p.canopy))


def extent(p: Pillar, cx: float, above: float) -> tuple[float, float]:
    """How far the pillar reaches left and right of its centre cx, over the part above y = above."""
    xs = [x - cx for x, y in p.outline + p.cap + p.canopy if y < above]
    return min(xs), max(xs)


def edge_pillars(s: Stage) -> EdgePillars:
    """The pillar's outer edge keeps EDGE_AIR (and a little more) inside the panel and its inner edge keeps
    FIG_AIR from the number; it is narrowed if it must be, and it never rises up beside a line of type."""
    mid, side, lx = s.width / 2, s.side, s.light[0]
    fig_half = s.number.w / 2
    text = [(b.w / 2, b.y1) for b in (s.title, *s.lines)]  # half width and lowest y of each line above it
    rng = s.rng(1)
    w, rise = rng.uniform(56, 84), rng.uniform(120, 210)
    air = EDGE_AIR + rng.uniform(0, 10)
    taper, flare, cap = rng.uniform(0.22, 0.36), rng.uniform(0.35, 0.55), rng.uniform(0.1, 0.26)
    trees, dome = rng.uniform(6, 14), rng.uniform(0.04, 0.12)

    def build(cx: float) -> Pillar:
        return make_pillar(s.rng(2), cx, s.horizon - rise, w, s.base + 60, lean=-side * 0.006, rough=0.045,
                           taper=taper, flare=flare, cap=cap, trees=trees, lump=4.0, bulge=0.1, tiers=1, dome=dome,
                           light_x=lx)

    def place() -> tuple[float, float, float]:
        """Its centre with the outer edge `air` inside the panel, and its reach left and right of that."""
        probe = mid + side * 300
        lo, hi = extent(build(probe), probe, s.base + 2)
        return (s.panel.x0 + air - lo if side < 0 else s.panel.x1 - air - hi), lo, hi

    for _ in range(5):
        ex, lo, hi = place()
        inner = mid - (ex + hi) if side < 0 else ex + lo - mid  # from the centre to the pillar's inner edge
        if inner < fig_half + FIG_AIR - 0.5:
            w *= (mid - s.panel.x0 - air - fig_half - FIG_AIR) / (hi - lo) * 0.98
            continue
        tallest = min([s.horizon - bottom - 18 for half, bottom in text if inner < half + 24], default=rise)
        if rise > tallest + 0.5:
            rise = tallest
            continue
        break
    ex, lo, hi = place()
    near = build(ex)

    far = None
    if s.key in FAR_PILLAR:  # a slender pillar far off in the haze, just inside the near one
        rng = s.rng(6)
        w2, rise2 = rng.uniform(20, 26), rng.uniform(78, 104)
        x2 = (ex + hi if side < 0 else ex + lo) - side * (w2 * 0.5 + rng.uniform(6, 12))
        p2 = make_pillar(s.rng(8), x2, s.horizon - rise2, w2, s.horizon + 30, lean=side * 0.01, rough=0.05,
                         taper=0.25, flare=0.4, cap=0.2, trees=rng.uniform(4, 6), lump=3.0, bulge=0.1, dome=0.08,
                         light_x=lx)
        lo2, hi2 = extent(p2, x2, s.horizon)
        if (mid - (x2 + hi2) if side < 0 else x2 + lo2 - mid) >= fig_half + FIG_AIR:
            far = thinned(p2)
    return EdgePillars(thinned(near), far)


def pillar_layers(s: Stage, svg: Svg, p: EdgePillars) -> Layers:
    """The far pillar behind the far cloud, softened by the haze; the near one standing in the sea of cloud."""
    t = s.theme
    far = drawn(svg, lambda: draw_pillars(svg, [p.far], t, 0.62, 1.0, t.rim_far, 0.9, 0.0)) if p.far else ""
    near = drawn(svg, lambda: draw_pillars(svg, [p.near], t, 0.34, 0.6, 0.6, 1.0, 0.6))
    return Layers(far=far, mid=near)


def draw(s: Stage, svg: Svg) -> Layers:
    return pillar_layers(s, svg, edge_pillars(s))
