"""parameter-golf (OpenAI Parameter Golf): a golf shot across the sea of cloud. The ball's flight is a dotted arc
over the edge pillar, falling onto a tiny green on a far summit just inside it. No flag: bitgolf has one."""

from __future__ import annotations

from dataclasses import replace

from inter import num
from scene import Pillar, Pt, Svg, draw_pillars, make_pillar, mix, smooth, unit

from stage import Box, Layers, Stage, drawn

from . import _pillar

# on a right card (a left card mirrors it)
GREEN_X, GREEN_TOP, GREEN_W = 612.0, 216.0, 42.0  # the green's pillar
APEX = (760.0, 40.0)  # the top of the ball's flight
START_X, STEP = 786.0, 12.0  # the first place of the ball shown, and how far it travels between two places
BALL_R = 4.2


def lawn(p: Pillar, depth: float) -> list[Pt]:
    """A close-mown green over the summit: one smooth band of even depth that rounds off at both ends."""
    i = p.outline.index(p.summit[0])
    (xl, yl), (xr, yr) = p.outline[i - 1], p.outline[i + len(p.summit)]
    ridge = [(xl, yl)] + p.summit + [(xr, yr)]
    o = 1.6

    def y_at(x: float) -> float:
        for (x0, y0), (x1, y1) in zip(ridge, ridge[1:]):
            if x0 <= x <= x1:
                return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
        return yl if x < xl else yr

    n = 14
    top: list[Pt] = []
    under: list[Pt] = []
    for j in range(n + 1):
        v = 2 * j / n - 1
        x = xl - o + (xr - xl + 2 * o) * j / n
        mid = y_at(x) - 1.0 + depth / 2 + 2.4 * max(0.0, (abs(v) - 0.6) / 0.4) ** 2  # it rolls over the rim
        half = depth / 2 * max(0.0, 1 - abs(v) ** 4) ** 0.5
        top.append((x, mid - half))
        under.append((x, mid + half))
    return top + under[-2:0:-1]


def ball(x: float, y: float, r: float, body: str, lit: str, toward: Pt) -> str:
    """A small sphere, backlit like everything in this world: cool on the whole, bright on the side that faces
    the light."""
    dx, dy = toward
    return (f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(r)}" fill="{body}"/>'
            f'<circle cx="{num(x + dx * r * 0.24)}" cy="{num(y + dy * r * 0.24)}" r="{num(r * 0.76)}" '
            f'fill="{lit}"/>')


def draw(stage: Stage, svg: Svg) -> Layers:
    s, t = stage, stage.theme
    p = _pillar.edge_pillars(s)
    near = _pillar.pillar_layers(s, svg, replace(p, far=None))

    def fx(x: float) -> float:
        return x if s.side > 0 else s.width - x

    gx = fx(GREEN_X)
    green = make_pillar(s.rng(20), gx, GREEN_TOP, GREEN_W, s.horizon + 30, lean=s.side * 0.01, rough=0.04,
                        taper=0.22, flare=0.4, cap=0.2, trees=0.0, dome=0.09, bulge=0.06, light_x=s.light[0])
    turf = lawn(green, 7.0)
    green = replace(_pillar.thinned(green), cap=turf)
    far = drawn(svg, lambda: draw_pillars(svg, [green], t, 0.45, 0.6, t.rim_far, 0.9, 0.0))
    # the green itself, crisp and fresh over the hazed stone: lit along its top, deeper toward its fringe
    hi, lo = ("#d8eea6", "#86bb68") if not s.dark else ("#8fb7a0", "#3b6458")
    y0 = min(y for _, y in turf)
    g = svg.linear([(0, hi, 1), (0.35, mix(hi, lo, 0.4), 1), (1, lo, 1)], 0, y0, 0, y0 + 9, user=True)
    far += f'<path fill="url(#{g})" d="{smooth(turf)}"/>'

    # the flight: the ball's place at equal steps of time. It crosses the sky at an even pace, so the places are
    # evenly spaced across and open out as it falls; the older a place, the smaller and fainter it is
    lit = "#ffffff" if not s.dark else mix(t.sea[0], "#ffffff", 0.55)
    body = mix(t.sea[2], t.ink_soft, 0.18) if not s.dark else mix(t.sea[1], t.sea[0], 0.6)
    ax, ay = fx(APEX[0]), APEX[1]
    summit = min(y for _, y in green.cap)
    land = (gx + s.side * 2.5, summit - BALL_R + 1.2)
    k = (land[1] - ay) / (land[0] - ax) ** 2
    n = round(abs(fx(START_X) - land[0]) / STEP)
    marks = []
    for i in range(n):
        u = i / n
        x = fx(START_X) + (land[0] - fx(START_X)) * u
        y = ay + k * (x - ax) ** 2
        r = 1.5 + 1.4 * u
        assert s.clear(Box(x - r, y - r, x + r, y + r)), (x, y)
        toward = unit(s.light[0] - x, s.light[1] - y)
        marks.append(f'<g opacity="{0.38 + 0.57 * u ** 1.3:.2f}">{ball(x, y, r, body, lit, toward)}</g>')
    toward = unit(s.light[0] - land[0], s.light[1] - land[1])
    rest = ball(*land, BALL_R, body, lit, toward)
    # the flight stays crisp in front of the glow; the ball rests on the green, all of it behind the cloud
    return Layers(far="".join(marks) + far + rest, mid=near.mid)
