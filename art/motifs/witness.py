"""witness: a lighthouse keeps watch from the edge pillar.

A small white lighthouse stands on the summit of the card's stone pillar, where its trees would be, and sends
its beam out over the sea of cloud, with a fainter one back toward the card that fades out well clear of the
type. By night the beams are the brightest thing at the card's edge; by day they are only a faint wash, and
the lamp glints.
"""

from __future__ import annotations

import math

from inter import num
from scene import Pillar, Pt, Svg, falloff, make_pillar, mix, poly
from stage import Box, Layers, Stage

from . import _pillar

RISE = 150.0     # how far the pillar's summit stands above the horizon
TOWER = 44.0     # the tower's height, from the grass to the gallery
FOOT_W = 16.0    # its width at the foot; it tapers to TOP_W under the gallery
TOP_W = 11.0
SPREAD = 8.0     # degrees either side of a beam's axis
DIP = 2.5        # degrees: the beams dip a little toward the cloud
INNER = 0.5      # the inward beam's strength against the outward one
HALO = (26.0, 22.0)  # the glow around the lamp


def sea_stack(s: Stage) -> Pillar:
    """Today's edge pillar, a little lower and slimmer and without its trees: a sea stack for the lighthouse."""
    side, lx = s.side, s.light[0]
    rng = s.rng(1)
    w = rng.uniform(56, 84)
    rng.uniform(120, 210)  # the default's rise: drawn and set aside, so the shape keeps its own proportions
    air = _pillar.EDGE_AIR + rng.uniform(0, 10)
    taper, flare, cap = rng.uniform(0.22, 0.36), rng.uniform(0.35, 0.55), rng.uniform(0.1, 0.26)
    rng.uniform(6, 14)  # the default's trees: none here
    dome = rng.uniform(0.04, 0.12)

    def build(cx: float) -> Pillar:
        return make_pillar(s.rng(2), cx, s.horizon - RISE, w * 0.9, s.base + 60, lean=-side * 0.006, rough=0.045,
                           taper=taper, flare=flare, cap=cap, trees=0, lump=4.0, bulge=0.1, tiers=1, dome=dome,
                           light_x=lx)

    probe = s.width / 2 + side * 300
    lo, hi = _pillar.extent(build(probe), probe, s.base + 2)
    cx = s.panel.x0 + air - lo if side < 0 else s.panel.x1 - air - hi
    return _pillar.thinned(build(cx))  # thinned as the default pillar is


def lighthouse(s: Stage, svg: Svg, gx: float, gy: float) -> tuple[str, Pt]:
    """The tower standing on the ground at (gx, gy): a tapering white tower, a dark gallery, the lamp room and
    its cap. Lit on the side that faces the light, like everything else. Returns its markup and the lamp."""
    t = s.theme
    lit_left = s.light[0] < gx
    if s.dark:
        lit, shade = mix(t.rim, t.rock_top, 0.42), mix(t.rock_top, t.rock, 0.2)
        dark, glass = mix(t.rock, "#000000", 0.25), "#f6f8f2"
    else:
        lit, shade = mix("#fffaf0", t.sea[0], 0.4), mix(t.sea[1], t.sea[2], 0.35)
        dark, glass = mix(t.rock, t.ink, 0.45), mix("#fffdf5", t.glow, 0.25)
    h, b, a = TOWER, FOOT_W / 2, TOP_W / 2
    top = gy - h
    # the classic tower: its sides curve in a little as they rise, so it flares at the foot
    bow = (b - a) * 0.3
    tower = (f"M{num(gx - b)} {num(gy + 3)}Q{num(gx - a - bow)} {num(gy - h * 0.3)} {num(gx - a)} {num(top)}"
             f"H{num(gx + a)}Q{num(gx + a + bow)} {num(gy - h * 0.3)} {num(gx + b)} {num(gy + 3)}Z")
    # cel shading: a hard step from the lit side to the shaded one, just past the middle
    x0, x1 = gx - b, gx + b
    step = 0.58 if lit_left else 0.42
    left_c, right_c = (lit, shade) if lit_left else (shade, lit)
    g = svg.linear([(0, left_c, 1), (step - 0.02, left_c, 1), (step + 0.02, right_c, 1), (1, right_c, 1)],
                   x0, 0, x1, 0, user=True)
    gal_w, gal_h = a + 2.6, 2.4
    lan_w, lan_h = a - 0.6, 7.5
    lan_y = top - gal_h - lan_h
    roof = lan_y - 0.2
    parts = [
        f'<path fill="url(#{g})" d="{tower}"/>',
        f'<rect x="{num(gx - gal_w)}" y="{num(top - gal_h)}" width="{num(2 * gal_w)}" height="{num(gal_h)}" '
        f'rx="0.6" fill="{dark}"/>',
        f'<rect x="{num(gx - lan_w)}" y="{num(lan_y)}" width="{num(2 * lan_w)}" height="{num(lan_h)}" '
        f'fill="{glass}"/>',
        f'<path fill="{dark}" d="M{num(gx - lan_w - 1.4)} {num(roof)}Q{num(gx)} {num(roof - 9)} '
        f'{num(gx + lan_w + 1.4)} {num(roof)}Z"/>',
        f'<rect x="{num(gx - 0.7)}" y="{num(roof - 9.5)}" width="1.4" height="4" fill="{dark}"/>',
    ]
    # as soft at the edge as the rock it stands on
    return f'<g filter="url(#{svg.blur(0.4)})">{"".join(parts)}</g>', (gx, lan_y + lan_h / 2)


def ray(svg: Svg, lamp: Pt, out: float, reach: float, strength: float, colour: str) -> str:
    """One soft beam from the lamp: a narrow wedge that widens and fades as it goes, dipping a little toward
    the cloud."""
    lx, ly = lamp
    spread, dip = math.radians(SPREAD), math.radians(DIP)
    ends = [(lx + out * reach * math.cos(dip + k * spread), ly + reach * math.sin(dip + k * spread))
            for k in (-1, 1)]
    g = svg.linear([(0, colour, strength), (0.3, colour, strength * 0.6), (1, colour, 0)],
                   lx, ly, lx + out * reach, ly + reach * math.sin(dip), user=True)
    d = poly([(lx, ly - 2.2), *ends, (lx, ly + 2.2)])
    return f'<path fill="url(#{g})" filter="url(#{svg.blur(1.5)})" d="{d}"/>'


def beam(s: Stage, svg: Svg, lamp: Pt) -> str:
    """The lamp's soft beams: the main one out over the cloud past the card's outer edge, a shorter, fainter
    one inward that fades out well clear of the type, and the glow around the lamp."""
    lx, ly = lamp
    out = 1.0 if s.side > 0 else -1.0
    colour = "#f4f7f2" if s.dark else "#fffdf4"
    strength = 0.55 if s.dark else 0.5
    parts = [ray(svg, lamp, out, abs(s.outer_x - lx) + 90, strength, colour)]
    reach = 10.0
    while reach < 400:  # the inward beam ends where its spread would come within the air of any type
        x = lx - out * (reach + 6)
        half = (reach + 6) * math.tan(math.radians(SPREAD)) + 3
        yc = ly + (reach + 6) * math.sin(math.radians(DIP))
        if not s.clear(Box(x - 2, yc - half, x + 2, yc + half)):
            break
        reach += 4
    parts.append(ray(svg, lamp, -out, reach, strength * INNER, colour))
    parts.append(svg.soft_spot(lx, ly, HALO[0], HALO[1], falloff(colour, 0.9 if s.dark else 0.6, 3.0, 7)))
    return "".join(parts)


def draw(stage: Stage, svg: Svg) -> Layers:
    p = sea_stack(stage)
    rock = _pillar.pillar_layers(stage, svg, _pillar.EdgePillars(p, None)).mid
    xl, xr = p.summit[0][0], p.summit[-1][0]
    gx = (xl + xr) / 2
    gy = min(y for x, y in p.summit if abs(x - gx) < 8) + 2.5
    tower, lamp = lighthouse(stage, svg, gx, gy)
    assert stage.clear(Box(gx - HALO[0], lamp[1] - HALO[1], gx + HALO[0], gy)), "the lighthouse meets the type"
    return Layers(mid=rock + tower + beam(stage, svg, lamp))
