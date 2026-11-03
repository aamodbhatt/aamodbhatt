"""bitgolf: the edge pillar's summit is a green, and a golf flag stands on it, its pennant catching the light.

Golf is won in the fewest strokes and bitgolf in the fewest bits, so the card's pillar becomes the world's most
remote hole: its trees are cleared to a smooth green, and a slim flagstick rises from it with a small pennant
streaming in toward the light. The far slender pillar stays, as on the plain card.
"""

from __future__ import annotations

from dataclasses import replace

from inter import num
from scene import Pillar, Pt, Svg, draw_pillars, mix
from stage import Box, Layers, Stage, drawn

from . import _pillar

POLE_H, POLE_W = 68.0, 2.8    # the flagstick, from the green to its tip
FLAG_L, FLAG_H = 36.0, 22.0   # the pennant: its reach from the pole and its height at the pole
SOFT = 0.5                    # the flag is as soft as the pillar it stands on
DRAPE = (8.0, 13.0)           # how far the green reaches below the summit: on the shaded side, on the lit side
LIP = 0.6                     # how far the green stands proud of the rock

# the pennant: in shade, catching the light; the pole: lit, in shade; a putting green: lit, shaded. By day and
# by night (the green replaces the theme's grass for the cap, so it is lit and hazed as the cap is)
CLOTH = {"day": ("#d4523f", "#f27b5d"), "evening": ("#8a4a52", "#c27a77")}
POLE = {"day": ("#fbf7ef", "#bdb7ae"), "evening": ("#cdd7dc", "#7d8f9b")}
GREEN = {"day": ("#d3e892", "#62a05c"), "evening": ("#5f8f84", "#1d3a3b")}


def spline(pts: list[Pt], n: int = 6) -> list[Pt]:
    """Points along the closed curve that scene.smooth draws through `pts`, n to each span."""
    out: list[Pt] = []
    k = len(pts)
    for i in range(k):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % k], pts[(i + 2) % k]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        for j in range(n):
            u = j / n
            w = ((1 - u) ** 3, 3 * u * (1 - u) ** 2, 3 * u * u * (1 - u), u ** 3)
            out.append((sum(a * q[0] for a, q in zip(w, (p1, c1, c2, p2))),
                        sum(a * q[1] for a, q in zip(w, (p1, c1, c2, p2)))))
    return out


def green_cap(p: Pillar) -> list[Pt]:
    """The green: the pillar's own top band, a little proud of the rock, its lower edge draping a touch
    further down on the side that faces the light. With the trees cleared, it covers the whole summit."""
    edge = spline(p.outline)
    low = max(y for _, y in p.summit)
    xs = [x for x, y in edge if y < low + DRAPE[1]]
    a, b = min(xs), max(xs)
    cx = (a + b) / 2

    def cut(x: float) -> float:
        u = (x - a) / (b - a)
        return low + DRAPE[0] + (DRAPE[1] - DRAPE[0]) * (u if p.lit_right else 1 - u) ** 2

    def above(i: int) -> bool:
        x, y = edge[i % len(edge)]
        return y <= cut(x)

    # the outline runs up the pillar's left side, over the summit and down its right side: walk out both
    # ways from the summit's highest point to where the band ends
    first = last = min(range(len(edge)), key=lambda i: edge[i][1])
    while above(first - 1):
        first -= 1
    while above(last + 1):
        last += 1
    band = [edge[i % len(edge)] for i in range(first, last + 1)]
    band = [(x + (LIP if x > cx else -LIP), y - 0.6) for x, y in band]
    x0, x1 = band[-1][0], band[0][0]  # the lower edge runs back from the band's right end to its left end
    under = [x0 + (x1 - x0) * i / 6 for i in range(1, 6)]
    return band + [(x, cut(x) + (0.7 if i % 2 else -0.3)) for i, x in enumerate(under)]


def summit_top(pts: list[Pt]) -> Pt:
    """The middle of the summit, at the height of its ground there."""
    xs = [x for x, _ in pts]
    cx = (min(xs) + max(xs)) / 2
    return min(pts, key=lambda p: abs(p[0] - cx))


def pennant(s: Stage, svg: Svg, px: float, ty: float) -> tuple[str, Box]:
    """A pennant from the pole at (px, ty), streaming toward the light: one crease across it, the panel by
    the pole in shade and the panel at the tip turned to the light. Returns its markup and its box."""
    d = 1.0 if s.light[0] > px else -1.0
    L, H = FLAG_L * d, FLAG_H

    def at(u: float, v: float) -> str:
        return f"{num(px + L * u)} {num(ty + H * v)}"

    shape = (f"M{at(0, 0)}C{at(0.3, -0.1)} {at(0.62, 0.22)} {at(1, 0.6)}"  # a gentle belly to the tip
             f"C{at(0.66, 0.82)} {at(0.34, 1.06)} {at(0, 1)}Z")
    outer = f"M{at(0.5, -0.4)}L{at(1.4, -0.4)}L{at(1.4, 1.4)}L{at(0.44, 1.4)}Z"  # beyond the crease
    shade, lit = (mix(c, s.theme.haze, 0.14) for c in CLOTH[s.theme.key])
    box = Box(min(px, px + L), ty - H * 0.1, max(px, px + L), ty + H * 1.06)
    return (f'<path fill="{shade}" d="{shape}"/>'
            f'<path fill="{lit}" clip-path="url(#{svg.clip(shape)})" d="{outer}"/>'), box


def draw(s: Stage, svg: Svg) -> Layers:
    t = s.theme
    p = _pillar.edge_pillars(s)
    near = replace(p.near, canopy=[])  # the trees are cleared ...
    near = replace(near, cap=green_cap(near))  # ... and the summit is a green
    far = drawn(svg, lambda: draw_pillars(svg, [p.far], t, 0.62, 1.0, t.rim_far, 0.9, 0.0)) if p.far else ""
    rock = drawn(svg, lambda: draw_pillars(svg, [near], replace(t, grass=GREEN[t.key]), 0.34, 0.6, 0.6, 1.0, 0.6))

    px, gy = summit_top(near.summit)
    foot = gy + 2.0  # the pin stands in the green
    top = foot - POLE_H
    cloth, box = pennant(s, svg, px + POLE_W * 0.5, top + 0.6)
    flag = Box(min(box.x0, px - 2), top - 2, max(box.x1, px + 2), foot)
    assert s.clear(flag), "the flag comes too near the type"
    lit, shade = POLE[t.key]
    pole = (f'<path stroke="{shade}" stroke-width="{num(POLE_W)}" stroke-linecap="round" '
            f'd="M{num(px)} {num(foot)}V{num(top)}"/>'
            f'<path stroke="{lit}" stroke-width="{num(POLE_W * 0.45)}" stroke-linecap="round" '
            f'd="M{num(px + POLE_W * 0.22)} {num(foot - 1)}V{num(top + 0.6)}"/>')
    return Layers(far=far, mid=rock + f'<g filter="url(#{svg.blur(SOFT)})">{pole}{cloth}</g>')
