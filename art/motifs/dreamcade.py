"""dreamcade: a playable dungeon dreamed by a diffusion model.

The edge pillar keeps its place, and a round-headed doorway is cut into its foot where it meets the cloud: a
passage running back into the rock to a softly lit far end, the way into the dungeon. Its light spills on the
rock and the cloud, and over the arch it breaks into a few square motes on a pixel grid, crisp near the door
and smaller, fainter and softer further out, like an image resolving out of noise.
"""

from __future__ import annotations

import math

from inter import num
from scene import Svg, falloff, mix, smooth
from stage import Box, Layers, Stage

from . import _pillar

Pt = tuple[float, float]
GRID = 4.6        # the motes' pixel grid
REACH = 30.0      # how far from the arch the motes reach
DENSITY = 0.75    # how many of the grid's cells right by the arch hold a mote
SOFT = 0.5        # beyond this far out (0..1 of REACH), a mote is soft


def span(outline: list[Pt], y: float) -> tuple[float, float]:
    """The left and right x of a closed outline where the line at height y crosses it."""
    xs = []
    for (x0, y0), (x1, y1) in zip(outline, outline[1:] + outline[:1]):
        if (y0 - y) * (y1 - y) <= 0 and y0 != y1:
            xs.append(x0 + (x1 - x0) * (y - y0) / (y1 - y0))
    return min(xs), max(xs)


def arch(x0: float, x1: float, top: float, sill: float) -> str:
    """A round-headed opening: its sides rise from the sill and close in a half circle at `top`."""
    r = (x1 - x0) / 2
    spring = top + r
    return (f"M{num(x0)} {num(sill)}V{num(spring)}A{num(r)} {num(r)} 0 0 1 {num(x1)} {num(spring)}"
            f"V{num(sill)}Z")


def motes(stage: Stage, x0: float, x1: float, top: float, sill: float) -> list[tuple[float, float, float, float]]:
    """The edge of the doorway's glow breaking into pixels: cells of a grid round the arch, more of them close
    to it and over it (light rises) and fewer, smaller and fainter further out, never two side by side, so
    each reads as one pixel. Each is (x, y, size, u), u from 0 at the arch to 1 at REACH."""
    rng = stage.rng(20)
    r = (x1 - x0) / 2
    cx, spring = (x0 + x1) / 2, top + r
    out = []
    taken: set[tuple[int, int]] = set()
    for gy in range(int((sill - top + REACH) / GRID) + 1):
        y = sill - (gy + 0.5) * GRID
        for gx in range(-int((r + REACH) / GRID) - 1, int((r + REACH) / GRID) + 2):
            x = cx + gx * GRID
            d = math.hypot(x - cx, y - spring) - r if y < spring else abs(x - cx) - r
            if d < GRID * 0.5 or d > REACH or y > stage.horizon + 4:
                continue
            u = d / REACH
            up = min(1.0, max(0.0, (spring + r * 0.6 - y) / (r * 1.6))) ** 1.2
            if rng.random() >= DENSITY * (1 - u) ** 1.4 * up:
                continue
            if any((gx + a, gy + b) in taken for a in (-1, 0, 1) for b in (-1, 0, 1)):
                continue
            taken.add((gx, gy))
            out.append((x, y, GRID * (0.78 - 0.28 * u), u))
    return out


def draw(stage: Stage, svg: Svg) -> Layers:
    t, m = stage.theme, stage.moment
    p = _pillar.edge_pillars(stage)
    base = _pillar.pillar_layers(stage, svg, p)
    outline = p.near.outline

    # the doorway: two fifths of the pillar's width, its sill sunk in the near cloud, so it opens onto the sea
    sill = stage.base + 14
    left, right = span(outline, stage.horizon - 10)
    w = (right - left) * 0.4
    h = w * 1.85
    cx = (left + right) / 2
    x0, x1, top = cx - w / 2, cx + w / 2, sill - h
    assert stage.clear(Box(x0 - w, top - 4, x1 + w, sill)), "the doorway strays near the type"

    rock = mix(t.rock, t.haze, 0.34)
    if stage.dark:  # lamplight by night: a soft cream, never the gold of the horizon
        heart, lamp = mix(m.core, "#f7e2bf", 0.5), mix(m.glow, "#e8cfa6", 0.4)
        walls, jamb = mix(lamp, rock, 0.24), mix(lamp, rock, 0.45)
    else:  # by day the passage is in shade, and only its far end glows
        heart, lamp = m.core, mix(m.core, m.glow, 0.35)
        walls, jamb = mix(rock, "#0e1b22", 0.32), mix(rock, lamp, 0.3)

    # seen from the light, the doorway shows a sliver of its far jamb; through it the passage runs back to
    # its far end, smaller and brighter, round the level of the eye
    j = w * 0.16
    ix0, ix1 = (x0, x1 - j) if stage.side > 0 else (x0 + j, x1)
    k = 0.5
    fx = (ix0 + ix1) / 2 + stage.side * w * 0.08
    fw = (ix1 - ix0) * k
    ftop = stage.horizon - (stage.horizon - top) * k
    end = svg.linear([(0, lamp, 1), (1, heart, 1)], 0, ftop, 0, stage.horizon + 8, user=True)
    halo = svg.soft_spot(cx, sill - h * 0.45, w * 2.3, h * 1.1, falloff(lamp, 0.6 if stage.dark else 0.42, 2.4, 6))
    door = (f'<g clip-path="url(#{svg.clip(smooth(outline))})">{halo}'
            f'<path fill="{jamb}" d="{arch(x0, x1, top, sill)}"/>'
            f'<path fill="{walls}" d="{arch(ix0, ix1, top + j * 0.35, sill)}"/>'
            f'<path fill="url(#{end})" d="{arch(fx - fw / 2, fx + fw / 2, ftop, sill)}"/></g>')
    # the light the doorway throws on the cloud at its foot
    pool = svg.soft_spot(cx, stage.base - 3, w * 2.2, 9, falloff(heart, 0.7 if stage.dark else 0.55, 2.4, 6))

    # the motes: crisp by the arch, softer further out, where the image has not yet come out of the noise
    crisp, soft = [], []
    for x, y, z, u in motes(stage, x0, x1, top, sill):
        assert stage.clear(Box(x - z, y - z, x + z, y + z)), "a mote strays near the type"
        cell = (f'<rect x="{num(x - z / 2)}" y="{num(y - z / 2)}" width="{num(z)}" height="{num(z)}" '
                f'fill-opacity="{0.85 * (1 - u) ** 0.8:.2f}"/>')
        (soft if u > SOFT else crisp).append(cell)
    pixels = (f'<g fill="{lamp}">{"".join(crisp)}'
              + (f'<g filter="url(#{svg.blur(0.6)})">{"".join(soft)}</g>' if soft else "") + "</g>")
    return Layers(far=base.far, mid=base.mid + door + pixels, near=pool)
