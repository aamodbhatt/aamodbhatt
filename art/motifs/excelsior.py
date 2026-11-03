"""excelsior: a spreadsheet engine; the name means "ever upward".

In place of the edge pillar, a floating stair of the pillars' stone rises out of the sea of cloud and climbs
into the sky. It bends ever more steeply upward, its steps growing smaller as it goes, until it fades into the
air. Like everything in the scene it is backlit: one cool silhouette whose risers and treads catch the light.
Its side is laid in courses that run on from every tread and riser, so the stone under the steps is ruled
into cells, the way a spreadsheet is.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from inter import num
from scene import Svg, lit_mass, mix
from stage import Box, Layers, Stage

Pt = tuple[float, float]
STEPS = 14
RISE = 18.5            # the first step's rise
SHRINK = 0.5           # the last step's size, against the first
TURN = (38.0, 84.0)    # the climb's angle at the foot and at the top, degrees above level
EASE = 0.8             # how soon the climb steepens
THICK = 14.0           # the stair's depth under its steps, at the foot
FADE = (0.45, 1.0)     # where, up the flight, the stair starts to fade into the sky, and where it is gone
NIGHT_FADE = 0.7       # by night the sky is dark, so the stone keeps its colour further up before it fades
NIGHT_SHIFT = 4.2      # by night the moonlit edge on each tread and riser is a little wider, so the flight reads


@dataclass(frozen=True)
class Flight:
    top: list[Pt]          # the stepped top, from the foot up: riser, then tread, step by step
    under: list[Pt]        # the smooth underside, from the top back down to the foot
    risers: list[float]    # the x of each riser
    treads: list[float]    # the y of each tread
    foot: float
    summit: float


def catmull(pts: list[Pt]) -> str:
    """Cubic Bezier segments (C commands only) through the points, for an open run already started at pts[0]."""
    out = []
    n = len(pts)
    for i in range(n - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, n - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        out.append(f"C{num(c1[0])} {num(c1[1])} {num(c2[0])} {num(c2[1])} {num(p2[0])} {num(p2[1])}")
    return "".join(out)


def flight(stage: Stage) -> Flight:
    s = stage.side
    z = stage.zones.outer_horizon
    x = z.x0 + 10 if s > 0 else z.x1 - 10
    foot = y = stage.base + 12  # the foot stands in the near cloud
    top: list[Pt] = [(x, y)]
    under: list[Pt] = []
    risers, treads = [], []
    for k in range(STEPS):
        u = k / (STEPS - 1)
        size = 1 - (1 - SHRINK) * u
        a = math.radians(TURN[0] + (TURN[1] - TURN[0]) * u ** EASE)
        rise, run = RISE * size, RISE * size / math.tan(a)
        t = THICK * size
        under.append((x + s * t * math.sin(a), y + t * math.cos(a)))
        risers.append(x)
        y -= rise
        treads.append(y)
        top.append((x, y))
        x += s * run
        top.append((x, y))
    under.append((x + s * THICK * SHRINK * 0.4, y + THICK * SHRINK))
    return Flight(top, under[::-1], risers, treads, foot, y)


def draw(stage: Stage, svg: Svg) -> Layers:
    t = stage.theme
    f = flight(stage)
    xs = [x for x, _ in f.top + f.under]
    assert stage.clear(Box(min(xs), f.summit, max(xs), stage.label.y0 - stage.air - 1), air=14), \
        "the stair strays near the type"
    d = ("M" + "L".join(f"{num(x)} {num(y)}" for x, y in f.top) + f"L{num(f.under[0][0])} {num(f.under[0][1])}"
         + catmull(f.under) + "Z")

    # the stone fades into the air toward the top of the flight
    h = f.foot - f.summit
    gone = f.foot - h * FADE[1]
    sky = stage.sky_at(gone)
    if stage.dark:  # by night a dark silhouette, every tread and riser picked out by the moon, as the pillars are
        body0 = mix(mix(t.rock_top, t.rock, 0.5), t.haze, 0.2)
        lit0, shift, fade = mix(t.rim, t.rock_lit, 0.35), NIGHT_SHIFT, NIGHT_FADE
    else:
        body0 = mix(mix(t.rock_top, t.rock, 0.5), t.haze, 0.3)
        lit0, shift, fade = mix(t.rock_lit, t.haze, 0.15), 3.0, FADE[0]

    def fading(c: str) -> str:
        return svg.linear([(0, sky, 1), (0.08, mix(c, sky, 0.85), 1), (1 - fade, c, 1), (1, c, 1)],
                          0, gone, 0, f.foot, user=True)

    # the courses: joints running on from every riser and tread, ruling the stone under the steps into cells
    lo = f.foot + 20
    rule = "".join(f"M{num(x)} {num(y)}V{num(lo)}" for x, y in zip(f.risers[1:], f.treads))
    far = max(xs) + 4 if stage.side > 0 else min(xs) - 4
    rule += "".join(f"M{num(x)} {num(y)}H{num(far)}" for x, y in zip(f.risers, f.treads))
    joint = mix(body0, "#0b1820", 0.45)
    cells = (f'<path fill="none" stroke="url(#{fading(joint)})" stroke-width="0.9" stroke-opacity="0.5" '
             f'd="{rule}"/>')
    toward = (-stage.side * 0.72, -0.69)  # the risers catch the low light, the treads the sky
    stair = lit_mass(svg, f'<path d="{d}"/>', f"url(#{fading(lit0)})", f"url(#{fading(body0)})", toward, shift, 0.7,
                     cells)
    return Layers(mid=stair)
