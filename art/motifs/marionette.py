"""marionette: the edge pillar, worked like a puppet.

The card's stone pillar is held like a marionette. Four fine strings, two to its crown and two to its
shoulders, run up to a slim wooden control that hangs from a hand out of frame, tipped a little as if the
pillar were mid-step. By day the strings are dark silk against the sky; by night they catch the moon.
"""

from __future__ import annotations

import math

from inter import num
from scene import Pt, Svg, mix
from stage import Box, Layers, Stage

from . import _pillar

HEAD, HANDS = 0.27, 0.27  # where the strings hold the stone: either side of its crown, and how far down its sides
                          # (a share of its width, and of its height above the horizon)
CONTROL_Y = 30.0          # the control's bar, below the panel's top edge (by night it hides a star that would
                          # otherwise sit on its end like a speck of dust)
TILT = 5.0                # degrees: the hand tips the control, its outer end down
THREAD = 1.4              # the strings' width, in card units
BAR, STICK = 5.2, 3.0     # the control's bar and the stick it hangs from
LEAN = 2.0                # degrees: the pillar leans with it, as a puppet does when its control is tipped


def turn(p: Pt, c: Pt, deg: float) -> Pt:
    a = math.radians(deg)
    dx, dy = p[0] - c[0], p[1] - c[1]
    return c[0] + dx * math.cos(a) - dy * math.sin(a), c[1] + dx * math.sin(a) + dy * math.cos(a)


def control(s: Stage, bx: float, by: float, half: float, tilt: float) -> tuple[str, list[Pt]]:
    """The puppeteer's control: a slim wooden bar on a stick that rises out of the frame, its underside and
    the stick's inner side catching the low light. Returns its markup and the four points its strings hang
    from: the head pair either side of the middle, the hand pair at the ends."""
    t = s.theme
    sky = s.sky_at(by)
    if s.dark:
        wood, edge = mix(t.rock_top, t.rim, 0.12), mix(t.rim, t.rock_top, 0.3)
    else:
        wood, edge = mix(t.bark, sky, 0.28), mix(t.rock_lit, sky, 0.2)
    lit_x = bx + STICK / 2 - 1.2 if s.light[0] > bx else bx - STICK / 2
    above = s.panel.y0 - 24
    parts = [
        f'<rect x="{num(bx - STICK / 2)}" y="{num(above)}" width="{num(STICK)}" height="{num(by - above)}" '
        f'fill="{wood}"/>',
        f'<rect x="{num(lit_x)}" y="{num(above)}" width="1.2" height="{num(by - above - 4)}" fill="{edge}" '
        f'opacity="0.5"/>',
        f'<rect x="{num(bx - half)}" y="{num(by - BAR / 2)}" width="{num(2 * half)}" height="{num(BAR)}" '
        f'rx="{num(BAR / 2)}" fill="{wood}"/>',
        f'<rect x="{num(bx - half + 2.5)}" y="{num(by + 0.6)}" width="{num(2 * half - 5)}" height="1.4" '
        f'rx="0.7" fill="{edge}" opacity="0.75"/>',
        f'<circle cx="{num(bx)}" cy="{num(by)}" r="{num(BAR * 0.75)}" fill="{wood}"/>',
    ]
    low = by + BAR / 2 - 1
    hang = [turn(p, (bx, by), tilt) for p in ((bx - 7, low), (bx + 7, low), (bx - half + 3, low),
                                                 (bx + half - 3, low))]
    return f'<g transform="rotate({num(tilt)} {num(bx)} {num(by)})">{"".join(parts)}</g>', hang


def draw(stage: Stage, svg: Svg) -> Layers:
    t = stage.theme
    p = _pillar.edge_pillars(stage)
    near = p.near
    rock = _pillar.pillar_layers(stage, svg, p)

    crown = near.canopy or near.cap
    top = min(y for _, y in crown)
    xl, xr = near.summit[0][0], near.summit[-1][0]
    cx, w = (xl + xr) / 2, xr - xl
    hand_y = top + HANDS * (stage.horizon - top)

    def crown_y(x: float) -> float:
        return min((y for px, y in crown if abs(px - x) < 4), default=top) + 1.5

    def side_x(y: float, left: bool) -> float:
        xs = [px for px, py in near.outline if abs(py - y) < 6]
        return min(xs) + 1.0 if left else max(xs) - 1.0

    holds: list[Pt] = [(cx - w * HEAD, crown_y(cx - w * HEAD)), (cx + w * HEAD, crown_y(cx + w * HEAD)),
                       (side_x(hand_y, True), hand_y), (side_x(hand_y, False), hand_y)]
    pivot = (cx, stage.horizon)
    lean = LEAN * stage.side
    holds = [turn(h, pivot, lean) for h in holds]
    half = (holds[3][0] - holds[2][0]) / 2 + 5
    by = stage.panel.y0 + CONTROL_Y
    rig, hangs = control(stage, cx, by, half, TILT * stage.side)
    assert stage.clear(Box(cx - half - 4, stage.panel.y0, cx + half + 4, by + 8)), "the control meets the type"

    lines = []
    for (tx, ty), (ax, ay) in zip(hangs, holds):
        for i in range(21):  # every string keeps its air from the type, all the way down
            x, y = tx + (ax - tx) * i / 20, ty + (ay - ty) * i / 20
            assert stage.clear(Box(x - 1, y - 1, x + 1, y + 1)), f"a string meets the type at ({x:.0f}, {y:.0f})"
        lines.append(f"M{num(tx)} {num(ty)}L{num(ax)} {num(ay)}")
    thread = mix(t.rim, t.ink, 0.3) if stage.dark else mix(t.ink_soft, stage.sky_at(top), 0.25)
    strings = (f'<path fill="none" stroke="{thread}" stroke-opacity="{0.7 if stage.dark else 0.8}" '
               f'stroke-width="{THREAD:g}" stroke-linecap="round" d="{"".join(lines)}"/>')
    # the pillar leans about the point where it meets the cloud, so its hidden foot stays hidden
    body = f'<g transform="rotate({num(lean)} {num(pivot[0])} {num(pivot[1])})">{rock.mid}</g>'
    return Layers(far=rock.far, mid=body + strings + rig)
