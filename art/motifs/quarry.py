"""quarry: the edge pillar, quarried. Its summit is left whole, with its grass and its trees, but low on the side
that faces the light the rock has been cut back in two clean benches of pale, fresh stone, down to a flat floor
where the cut blocks wait, stacked three, two and one."""

from __future__ import annotations

from dataclasses import replace

from inter import num
from scene import Noise, Pillar, Pt, Svg, draw_pillars, make_pillar, mix, poly
from stage import Box, Layers, Stage, drawn

DEPTH, BLUR = 0.34, 0.6           # as the default edge pillar: standing in the sea of cloud
TREADS, FLOOR = (204.0, 246.0), 286.0  # the y of each bench's tread, and of the quarry floor
BENCH = 4.5                       # how far each bench steps out from the one above
FACE = 14.0                       # the width of the pale cut face behind each wall


def split(p: Pillar) -> tuple[list[Pt], list[Pt], list[Pt]]:
    """The outline as its left side (bottom to top), its summit and its right side (top to bottom)."""
    i = p.outline.index(p.summit[0])
    return p.outline[:i], p.outline[i:i + len(p.summit)], p.outline[i + len(p.summit):]


def clear_of_type(s: Stage, pts: list[Pt]) -> bool:
    """Whether every point keeps the stage's air from all type (a dense outline cannot then cross a line)."""
    return all(s.clear(Box(x, y, x, y)) for x, y in pts)


def draw(s: Stage, svg: Svg) -> Layers:
    t = s.theme
    out = -s.side                   # +1 when the side that faces the light is the right one
    foot = s.outer_x - s.side * 22  # the pillar's outer foot keeps this much sky from the panel's edge
    # the floor stops short of the number, leaving room for the old rock under it to ease out a little
    limit = s.number.x0 - s.air - 4 if s.side < 0 else s.number.x1 + s.air + 4

    w, top = 58.0, 120.0
    base = s.base + 60
    p = make_pillar(s.rng(21), foot + out * w * 0.55, top, w, base, lean=out * 0.004, rough=0.04, taper=0.14,
                    flare=0.2, cap=0.22, trees=11, lump=3.2, bulge=0.07, dome=0.08, light_x=s.light[0])
    left, summit, right = split(p)
    lit = right if out > 0 else left[::-1]  # the side that faces the light, top to bottom

    # the lit side: whole down to the first tread, then each bench a sheer wall a little further out, then the
    # floor runs out to the limit, and under it the old rock falls away into the cloud
    x_edge = min(lit, key=lambda q: abs(q[1] - TREADS[0]))[0]
    walls = [x_edge + out * BENCH * (k + 1) for k in range(len(TREADS))]
    benches = list(zip(TREADS, walls, (*TREADS[1:], FLOOR)))
    side: list[Pt] = [q for q in lit if q[1] < TREADS[0] - 1]
    prev = x_edge
    for y, x, y_next in benches:
        side += [(prev, y - 0.7), (prev + out * 0.7, y), (x - out * 0.7, y)]
        side += [(x, y + 0.7 + (y_next - y - 0.7) * k / 4) for k in range(5)]
        prev = x
    x_wall = walls[-1]
    side += [(x_wall + out * 0.8, FLOOR), (limit - out * 2.0, FLOOR)]
    noise = Noise(s.rng(22))
    side += [(limit + out * (2.5 * (k / 10) ** 0.6 - 1.0 + 1.2 * noise(k * 0.5)),
              FLOOR + 1.8 + (base - FLOOR) * (k / 10) ** 1.4) for k in range(11)]
    edge = [q for q in side if q[1] <= s.base + 10]

    outline = (left + summit + side) if out > 0 else (side[::-1] + summit + right)
    tip = summit[-1] if out > 0 else summit[0]
    q = replace(p, outline=outline, edge=edge, strata=[], flutes=[], tufts=[],
                face=[tip] + edge + [(x - out * w * 0.1, y) for x, y in edge][::-1],
                glint=[tip] + edge + [(x - out * w * 0.035, y) for x, y in edge][::-1])
    body = drawn(svg, lambda: draw_pillars(svg, [q], t, DEPTH, BLUR, 0.6, 1.0, 0.6))

    # the fresh stone: behind each wall a pale face, brightest at the cut, and a crisp line along each tread
    fresh = mix(mix(t.rock_top, t.rock_lit, 0.6), t.haze, DEPTH * 0.5)
    bright = mix(fresh, "#ffffff", 0.55)
    faces, lines = [], []
    prev = x_edge
    for y, x, y_next in benches:
        g = svg.linear([(0, fresh, 0.0), (0.5, fresh, 0.7), (1, fresh, 0.95)], x - out * FACE, 0, x, 0, user=True)
        d = poly([(x - out * FACE, y), (x, y), (x, y_next), (x - out * FACE, y_next)])
        faces.append(f'<path fill="url(#{g})" d="{d}"/>')
        lines.append(f"M{num(prev - out * 3)} {num(y + 0.8)}H{num(x)}")
        prev = x
    lines.append(f"M{num(x_wall)} {num(FLOOR + 0.9)}H{num(limit)}")
    cuts = (f'<g filter="url(#{svg.blur(0.45)})">{"".join(faces)}<path fill="none" stroke="{bright}" '
            f'stroke-width="1.8" stroke-linecap="round" d="{"".join(lines)}"/></g>')

    # the cut blocks on the floor, three, two and one: pale stone, a bright top, a lit side toward the light
    gap = 1.4
    bw = (abs(limit - x_wall) - 0.5 - 2 * gap) / 3  # the bottom row stands a little out in front of the wall
    bh = bw * 0.8
    stone = mix(fresh, t.rock, 0.05)
    lit_face = mix(fresh, "#ffffff", 0.3)
    shade = mix(mix(t.rock, t.haze, DEPTH), fresh, 0.4)
    blocks, corners = [], []
    for row, count in enumerate((3, 2, 1)):
        y = FLOOR - (row + 1) * bh - row * gap
        for k in range(count):
            xa = x_wall + out * (-2.0 + (k + row * 0.5) * (bw + gap))
            xl = min(xa, xa + out * bw)
            blocks.append(f'<rect x="{num(xl)}" y="{num(y)}" width="{num(bw)}" height="{num(bh)}" fill="{stone}"/>'
                          f'<rect x="{num(xl)}" y="{num(y + bh * 0.6)}" width="{num(bw)}" height="{num(bh * 0.4)}" '
                          f'fill="{shade}" fill-opacity="0.45"/>'
                          f'<rect x="{num(xl + bw - 2.2 if out > 0 else xl)}" y="{num(y)}" width="2.2" '
                          f'height="{num(bh)}" fill="{lit_face}" fill-opacity="0.8"/>'
                          f'<rect x="{num(xl)}" y="{num(y)}" width="{num(bw)}" height="1.5" fill="{bright}"/>')
            corners += [(xl, y), (xl + bw, y)]
    stack = f'<g filter="url(#{svg.blur(0.35)})">{"".join(blocks)}</g>'

    canopy = [(x, y - 2) for x, y in p.canopy]
    assert clear_of_type(s, outline + canopy + corners), \
        [q for q in outline + canopy + corners if not clear_of_type(s, [q])]
    return Layers(mid=body + cuts + stack)
