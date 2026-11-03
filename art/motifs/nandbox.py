"""nandbox: a pixel snake of jade swimming through the sea of cloud toward one small round stone.

nandbox is a CPU built from NAND gates that plays Snake, so in place of the plain pillar the card has the game's
snake: square blocks on a grid, a few units apart, that rise out of the cloud, arch over in one hump with
right-angle turns and come back down toward the one round stone the head is about to reach. Its feet sink into
the near cloud tops, and each block catches the low light on the side that faces it, as the pillars do.
"""

from __future__ import annotations

from inter import num
from scene import Svg, light_dir, lit_mass, mix
from stage import Box, Layers, Stage

CELL, GAP = 26.0, 4.0          # a block, and the sky between two blocks
PITCH = CELL + GAP
EDGE_AIR = 32.0                # sky between the outer column and the panel's edge
RADIUS = 3.0                   # the blocks' corners: cut stone, barely worn
ROW0 = 12.0                    # row 0's centre, below the number's baseline: it is lost in the near cloud,
                               # and row 1 stands in it, its foot veiled by the cloud tops
DEPTH = 0.3                    # how far the haze reaches into the jade
SHIFT, SOFT = 4.4, 0.8         # the lit edge on each block: how wide, how soft
SOFTEN = 0.5                   # the whole snake is as soft as the pillars

# the snake, tail first, as (column, row): column 0 at the outer edge. The tail rises out of the cloud, the
# body arches over a hump, and the head, back down at the cloud tops, faces the round stone.
BODY = ((5, 0), (5, 1), (4, 1), (4, 2), (3, 2), (2, 2), (2, 1), (1, 1))
FOOD = (-0.1, 1)

# jade: lit edge, body, deep; by day and by night
JADE = {"day": ("#e2f4e4", "#4f8e7d", "#335f58"), "evening": ("#a9d2c4", "#2b5a57", "#1a3a3d")}


def draw(s: Stage, svg: Svg) -> Layers:
    t = s.theme
    inward = -s.side  # +1 when the columns run to the right, from a left card's outer edge
    x_out = s.outer_x - s.side * (EDGE_AIR + CELL / 2)
    y0 = s.base + ROW0

    def centre(c: float, r: float) -> tuple[float, float]:
        return x_out + inward * c * PITCH, y0 - r * PITCH

    lit, body, deep = (mix(c, t.haze, DEPTH * k) for c, k in zip(JADE[t.key], (0.4, 1.0, 1.0)))
    top, bottom = y0 - max(r for _, r in BODY) * PITCH - CELL / 2, y0 + CELL / 2
    g = svg.linear([(0, mix(body, lit, 0.15), 1), (0.55, body, 1), (1, deep, 1)], 0, top, 0, bottom, user=True)
    fill = f"url(#{g})"

    floor = s.label.y0 - s.air - 0.5  # a sunk block ends here, out of sight under the near cloud
    parts = []
    for c, r in BODY:
        x, y = centre(c, r)
        b = Box(x - CELL / 2, y - CELL / 2, x + CELL / 2, min(y + CELL / 2, floor))
        assert s.clear(b), f"the block at {c, r} comes too near the type"
        # each block is lit on its own, so a neighbour's shade never falls across its lit edge
        shape = (f'<rect x="{num(b.x0)}" y="{num(b.y0)}" width="{num(CELL)}" height="{num(b.h)}" '
                 f'rx="{num(RADIUS)}"/>')
        parts.append(lit_mass(svg, shape, lit, fill, light_dir(t, x, y, 0.12), SHIFT, SOFT))

    fx, fy = centre(*FOOD)
    fr = CELL * 0.42
    assert s.clear(Box(fx - fr, fy - fr, fx + fr, fy + fr)), "the round stone comes too near the type"
    stone = f'<circle cx="{num(fx)}" cy="{num(fy)}" r="{num(fr)}"/>'
    parts.append(lit_mass(svg, stone, lit, fill, light_dir(t, fx, fy, 0.12), SHIFT * 0.8, SOFT))
    return Layers(mid=f'<g filter="url(#{svg.blur(SOFTEN)})">{"".join(parts)}</g>')
