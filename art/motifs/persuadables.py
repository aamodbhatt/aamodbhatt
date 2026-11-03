"""persuadables: an A/B test in stone. Twin pillars rise from one base, the same rock in the same shape, but one
has been lifted higher than its twin, and only it is crowned with a tree in blossom: the uplift. The tree is
the banner's own wind-shaped pine, leaning out over the drop, its pads turned to blossom."""

from __future__ import annotations

import math
from dataclasses import replace

from inter import num
from scene import Pillar, Pt, Svg, cushion, draw_pillars, light_dir, lit_mass, make_pillar, make_pine, mass_centre, \
    mix, poly, smooth
from stage import Box, Layers, Stage, drawn

DEPTH, BLUR = 0.34, 0.6           # as the default edge pillar: standing in the sea of cloud
WIDTH, CLEFT = 44.0, 12.0         # each twin's width, and the sky between them at their summits
TOP_A, TOP_B = 148.0, 206.0       # the lifted twin's summit, and its twin's
SADDLE = (274.0, 270.0)           # where the cleft's round bottom meets the lower twin's side, and the higher's
TREE = 0.37                       # the blossoming pine's scale, against the banner's


def split(p: Pillar) -> tuple[list[Pt], list[Pt], list[Pt]]:
    """The outline as its left side (bottom to top), its summit and its right side (top to bottom)."""
    i = p.outline.index(p.summit[0])
    return p.outline[:i], p.outline[i:i + len(p.summit)], p.outline[i + len(p.summit):]


def at_y(pts: list[Pt], y: float) -> float:
    """The x of a side of a pillar at height y."""
    return min(pts, key=lambda q: abs(q[1] - y))[0]


def clear_of_type(s: Stage, pts: list[Pt]) -> bool:
    """Whether every point keeps the stage's air from all type (a dense outline cannot then cross a line)."""
    return all(s.clear(Box(x, y, x, y)) for x, y in pts)


def blossom(s: Stage) -> tuple[str, str, str]:
    """The blossom's lit edge, body and underside: blush by day, a pale moonlit rose by night (pale enough to
    read as blossom against the night sky, not as a dark cap)."""
    lit, body, low = ("#f7ecf0", "#c6a6b8", "#8a6a80") if s.dark else ("#fff3f2", "#f3c0cd", "#db9bb1")
    return mix(lit, s.theme.haze, 0.12), mix(body, s.theme.haze, 0.12), mix(low, s.theme.haze, 0.12)


def pine_in_bloom(s: Stage, svg: Svg, gx: float, gy: float, size: float) -> tuple[str, list[Pt]]:
    """The banner's wind-shaped pine rooted at (gx, gy), leaning out over the drop, its pads in blossom: fuller and
    rounder than the pine's own. Returns its markup and the points of its outline."""
    t = s.theme
    pine = make_pine(s.rng(23), gx, gy, size, s.side)
    sw = pine.s
    wood = [f'<path stroke-width="{num(7 * sw)}" d="{smooth(pine.trunk[:3], closed=False)}"/>',
            f'<path stroke-width="{num(4.6 * sw)}" d="{smooth(pine.trunk[2:], closed=False)}"/>']
    wood += [f'<path stroke-width="{num(2.8 * sw)}" d="{smooth(b, closed=False)}"/>' for b in pine.branches]
    # by night the wood catches the moon a little, so the blossom stays joined to the rock
    bark = mix(t.bark, t.rim, 0.35) if s.dark else mix(t.bark, t.haze, 0.2)
    out = f'<g fill="none" stroke="{bark}" stroke-linecap="round">{"".join(wood)}</g>'
    lit, body, low = blossom(s)
    g = svg.linear([(0, body, 1), (1, low, 1)])
    rng = s.rng(24)
    pts: list[Pt] = [*pine.trunk, *(p for b in pine.branches for p in b)]
    # the pads sit where make_pine puts them, at the ends of the branches
    for dx, dy, rx in ((-32, 58, 30), (80, 64, 34), (72, 102, 42), (28, 121, 32), (-2, 82, 20)):
        px, py = gx + s.side * dx * size, gy - dy * size
        rx *= size
        lump = max(2.2, rx * 0.17)
        m = max(4, int(2 * rx / (lump * 0.8)))
        lumps = [(px - rx + 2 * rx * i / m + rng.uniform(-0.3, 0.3) * lump,
                  py - rx * 0.72 * max(0.0, math.sin(math.pi * i / m)) ** 0.7 + lump * 0.55,
                  lump * rng.uniform(0.8, 1.12)) for i in range(m + 1)]
        pad = cushion(lumps, py + 2.0, 1.0)
        cx, cy = mass_centre(pad)
        out += lit_mass(svg, f'<path d="{poly(pad)}"/>', lit, f"url(#{g})", light_dir(t, cx, cy, 0.4), 1.6, 0.6)
        pts += pad
    return out, pts


def draw(s: Stage, svg: Svg) -> Layers:
    t = s.theme
    inn = -s.side                   # toward the number and the light
    base = s.base + 16  # deep in the near cloud, yet clear of the label
    edge = s.outer_x - s.side * 58  # the lifted twin's outer foot keeps this much sky from the panel's edge

    # the twins: one seed, so one shape; the outer one (a) is lifted higher than the inner one (b)
    a_cx = edge + inn * WIDTH * 0.66
    b_cx = a_cx + inn * (WIDTH + CLEFT)
    shape = dict(rough=0.04, taper=0.18, flare=0.3, cap=0.2, bulge=0.08, dome=0.08, light_x=s.light[0],
                 lean=s.side * 0.004)
    a = make_pillar(s.rng(21), a_cx, TOP_A, WIDTH, base, **shape)
    b = make_pillar(s.rng(21), b_cx, TOP_B, WIDTH, base, **shape)
    a_l, a_s, a_r = split(a)
    b_l, b_s, b_r = split(b)

    # one base: the cleft between them has a round bottom, and below it they are one rock
    b_in, a_in = (b_r, a_l[::-1]) if inn < 0 else (b_l[::-1], a_r)  # the sides that face each other, top down
    y_b, y_a = SADDLE
    x_b, x_a = at_y(b_in, y_b), at_y(a_in, y_a)
    bottom = [(x_b + (x_a - x_b) * (1 - math.cos(math.pi * u)) / 2, y_b + (y_a - y_b) * u + 9 * math.sin(math.pi * u))
              for u in (i / 12 for i in range(1, 12))]
    b_upper = [q for q in b_in if q[1] < y_b]
    a_upper = [q for q in a_in if q[1] < y_a]
    if inn < 0:  # b stands left of a
        outline = b_l + b_s + b_upper + [(x_b, y_b)] + bottom + [(x_a, y_a)] + a_upper[::-1] + a_s + a_r
    else:
        outline = a_l + a_s + a_upper + [(x_a, y_a)] + bottom[::-1] + [(x_b, y_b)] + b_upper[::-1] + b_s + b_r

    # the fork is b's rock grown into the whole outline: it carries b's lit side, b's cap and the shade in the
    # cleft. a is drawn over it with the same body (both reach from a's summit to the same foot, so the body
    # gradient matches) and carries its own lit side down to the cleft's bottom, its cap and its outer shade
    b_tip = b.summit[-1] if inn < 0 else b.summit[0]
    fork = replace(b, outline=outline, shade=[b_tip] + b_upper + [(x + inn * WIDTH * 0.14, y) for x, y in b_upper][::-1])
    a_lit = [q for q in a.edge if q[1] < y_a]
    a_tip = a.summit[0] if inn < 0 else a.summit[-1]
    a_top = replace(a, edge=a_lit, face=[a_tip] + a_lit + [(x - inn * WIDTH * 0.11, y) for x, y in a_lit][::-1],
                    glint=[a_tip] + a_lit + [(x - inn * WIDTH * 0.035, y) for x, y in a_lit][::-1])
    twins = drawn(svg, lambda: draw_pillars(svg, [fork, a_top], t, DEPTH, BLUR, 0.6, 1.0, 0.6))

    # the uplift: the lifted twin's summit blossoms, at its outer shoulder
    gx, gy = a.summit[-1] if s.side > 0 else a.summit[0]
    tree, tree_pts = pine_in_bloom(s, svg, gx, gy + 2, TREE)

    assert clear_of_type(s, outline + tree_pts), \
        [q for q in outline + tree_pts if not clear_of_type(s, [q])]
    return Layers(mid=twins + tree)
