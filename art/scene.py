"""The vista: stone pillars rising out of a sea of cloud toward a low golden sun (day), or under the moon
(evening).

The light is the subject. It sits low in the valley on the same centre line as the name, with a soft bloom
that falls off smoothly and a bright glade on the cloud right under it. The scene is backlit: every mass
(cloud, rock, canopy, pine) is one silhouette in a cool body colour with a soft glowing edge on the side that
faces the light, and nothing is built from visible discs. Far layers fade into the colour of the air, near ones
stay crisp. The geometry is seeded, so both themes show exactly the same place and a rebuild is byte-for-byte
stable.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from inter import Face, num

W, H = 1600, 600
LIGHT_X = 800.0  # the sun and the moon hang on the same centre line as the name

NAME, ROLE = "Aamod Bhatt", "Machine Learning Engineer · Researcher"
NAME_SIZE, NAME_Y, NAME_TRACK = 112.0, 150.0, -0.025
ROLE_SIZE, ROLE_Y, ROLE_TRACK = 54.0, 228.0, 0.0

Pt = tuple[float, float]
Circle = tuple[float, float, float]
Quad = tuple[float, float, float, float]
Stops = list[tuple[float, str, float]]


# ---------------------------------------------------------------- helpers


def rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def mix(a: str, b: str, t: float) -> str:
    """Blend colour a toward colour b by t (0..1)."""
    t = min(max(t, 0.0), 1.0)
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(rgb(a), rgb(b)))


class Noise:
    """Smooth 1-D value noise summed over a few octaves, roughly in -1..1."""

    def __init__(self, rng: random.Random) -> None:
        self.v = [rng.uniform(-1.0, 1.0) for _ in range(64)]
        self.off = rng.uniform(0.0, 32.0)

    def _at(self, x: float) -> float:
        x += self.off
        i = math.floor(x)
        f = x - i
        a, b = self.v[i % 64], self.v[(i + 1) % 64]
        return a + (b - a) * f * f * (3 - 2 * f)

    def __call__(self, x: float, octaves: int = 3) -> float:
        total = norm = 0.0
        amp = freq = 1.0
        for o in range(octaves):
            total += amp * self._at(x * freq + o * 7.31)
            norm += amp
            amp *= 0.5
            freq *= 2.1
        return total / norm


def smooth(pts: list[Pt], closed: bool = True) -> str:
    """Catmull-Rom spline through the points, as cubic Bezier path data."""
    n = len(pts)

    def p(i: int) -> Pt:
        return pts[i % n] if closed else pts[min(max(i, 0), n - 1)]

    out = [f"M{num(pts[0][0])} {num(pts[0][1])}"]
    for i in range(n if closed else n - 1):
        p0, p1, p2, p3 = p(i - 1), p(i), p(i + 1), p(i + 2)
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        out.append(f"C{num(c1[0])} {num(c1[1])} {num(c2[0])} {num(c2[1])} {num(p2[0])} {num(p2[1])}")
    return "".join(out) + ("Z" if closed else "")


def poly(pts: list[Pt], closed: bool = True) -> str:
    return "M" + "L".join(f"{num(x)} {num(y)}" for x, y in pts) + ("Z" if closed else "")


def unit(dx: float, dy: float) -> Pt:
    d = math.hypot(dx, dy) or 1.0
    return dx / d, dy / d


def bump(t: float, at: float, width: float) -> float:
    return math.exp(-(((t - at) / width) ** 2))


def step(t: float, at: float, k: float = 0.004) -> float:
    """A soft step from 0 to 1 around `at`."""
    z = (t - at) / k
    return 1.0 if z > 40 else 0.0 if z < -40 else 1 / (1 + math.exp(-z))


def skyline(lumps: list[Circle], x: float) -> float:
    """The highest point of any lump above x (inf when no lump covers x)."""
    hi = math.inf
    for cx, cy, r in lumps:
        dx = x - cx
        if abs(dx) < r:
            hi = min(hi, cy - math.sqrt(r * r - dx * dx))
    return hi


def cushion(lumps: list[Circle], floor: float, spacing: float) -> list[Pt]:
    """One flat-based silhouette over a set of lumps: their merged top, a flat underside at `floor`, and
    rounded ends. It reads as a single soft mass with no inner arcs."""
    x0 = min(cx - r for cx, _, r in lumps) + 0.5
    x1 = max(cx + r for cx, _, r in lumps) - 0.5
    n = max(4, round((x1 - x0) / spacing))
    tops = [(x0 + (x1 - x0) * i / n, skyline(lumps, x0 + (x1 - x0) * i / n)) for i in range(n + 1)]
    tops = [(x, y) for x, y in tops if y < math.inf]
    depth = floor - sum(y for _, y in tops) / len(tops)
    rr = max(1.0, depth * 0.55)
    bottom: list[Pt] = []
    for x, y in tops[::-1]:
        e = min(x - x0, x1 - x)
        lift = rr - math.sqrt(max(0.0, rr * rr - (rr - e) ** 2)) if e < rr else 0.0
        bottom.append((x, max(y + 0.5, floor - lift)))
    return tops + bottom


# ---------------------------------------------------------------- themes


@dataclass(frozen=True)
class Theme:
    key: str
    sky: tuple[tuple[float, str], ...]
    light: str  # the sun or moon disc
    light_pos: Pt
    light_r: float
    glow: str  # air glowing around the light
    bloom: tuple[float, float, float]  # peak strength of the tight bloom, the wide bloom and the sky glow
    haze: str  # colour distant things fade into
    sea: tuple[str, str, str]  # sea of cloud: glowing edge, body, shade
    sea_warm: str  # edges near the light
    glade: str  # the bright path on the cloud right under the light
    cloud: tuple[str, str, str]  # the sky cloud: top, body, underside
    cloud_lit: str  # the soft light on its lumps that face the light
    cloud_rim: str  # its edge that faces the light
    cloud_rim_width: float
    rock: str  # shadowed stone
    rock_top: str  # stone near the summits, catching sky light
    rock_lit: str  # stone facing the light
    rim: str
    rim_far: float  # rim strength on the far pillars
    grass: tuple[str, str]  # lit, shadow
    leaf: tuple[str, str, str]  # lit edge, body, base
    bark: str
    ink: str  # the name
    ink_soft: str  # the role line
    foot: tuple[str, float, float]  # the panel's bottom edge: colour, strength, height
    stars: bool = False


DAY = Theme(
    key="day",
    sky=((0.0, "#6699ca"), (0.2, "#8fb7dc"), (0.4, "#c8dbe6"), (0.55, "#f0e2c8"), (0.64, "#fcd9a2"),
         (0.76, "#f9dcb6"), (1.0, "#f1e0cb")),
    light="#fffef8",
    light_pos=(LIGHT_X, 384.0),
    light_r=28.0,
    glow="#ffe2a0",
    bloom=(1.0, 0.62, 0.62),
    haze="#d3dae6",
    sea=("#fff3dc", "#b9c3db", "#939fbe"),
    sea_warm="#ffd99c",
    glade="#fff6df",
    cloud=("#dfe5f0", "#cfd6e4", "#efd5b6"),
    cloud_lit="#fff3de",
    cloud_rim="#ffd9a0",
    cloud_rim_width=9.0,
    rock="#33555a",
    rock_top="#6f8b80",
    rock_lit="#ffd89a",
    rim="#fff1c8",
    rim_far=0.55,
    grass=("#cbdc86", "#5d8d57"),
    leaf=("#cfe08a", "#6c9957", "#3a6546"),
    bark="#463e35",
    ink="#16242f",
    ink_soft="#344b5b",
    foot=("#c3cddb", 0.5, 44.0),
)

EVENING = Theme(
    key="evening",
    sky=((0.0, "#07101d"), (0.28, "#0e1d34"), (0.48, "#1a3049"), (0.6, "#2b465e"), (0.7, "#3a5768"),
         (1.0, "#33495a")),
    light="#f8f6ec",
    light_pos=(LIGHT_X, 330.0),
    light_r=17.0,
    glow="#c4d7e0",
    bloom=(0.62, 0.26, 0.34),
    haze="#3d5668",
    sea=("#a9bfcc", "#4f6982", "#2f4258"),
    sea_warm="#c6d6de",
    glade="#e4edf1",
    cloud=("#273d56", "#243950", "#34506b"),
    cloud_lit="#5e7a92",
    cloud_rim="#bccdd8",
    cloud_rim_width=4.0,
    rock="#132430",
    rock_top="#23384a",
    rock_lit="#7d97a7",
    rim="#cfdee6",
    rim_far=0.0,
    grass=("#56807d", "#1a3336"),
    leaf=("#6f9690", "#1f3c40", "#10252b"),
    bark="#0a1115",
    ink="#f3f5f1",
    ink_soft="#c0d0d6",
    foot=("#0d1117", 0.55, 80.0),
    stars=True,
)


def type_clear(name_face: Face, role_face: Face, margin: float = 14.0) -> tuple[Quad, Quad]:
    """The open sky kept clear behind the name and the role line (x0, y0, x1, y1), with a margin."""
    wn = name_face.width(NAME, NAME_SIZE, NAME_TRACK) / 2
    wr = role_face.width(ROLE, ROLE_SIZE, ROLE_TRACK) / 2
    return ((W / 2 - wn - margin, NAME_Y - 0.76 * NAME_SIZE - margin, W / 2 + wn + margin, NAME_Y + margin),
            (W / 2 - wr - margin, ROLE_Y - 0.76 * ROLE_SIZE - margin, W / 2 + wr + margin,
             ROLE_Y + 0.22 * ROLE_SIZE + margin))


# ---------------------------------------------------------------- geometry


@dataclass
class Pillar:
    outline: list[Pt]
    edge: list[Pt]  # the light-facing silhouette, for the rim light
    face: list[Pt]  # the plane turned toward the light
    glint: list[Pt]  # the narrow brightest plane right at the lit edge
    shade: list[Pt]  # the plane turned away
    lit_right: bool
    strata: list[list[Pt]]  # the soft shadow under each bed of rock
    flutes: list[tuple[list[Pt], float, bool]]  # soft vertical weathering: line, width, light?
    cap: list[Pt]  # grass over the summit
    canopy: list[Pt]  # the trees on the summit, as one silhouette
    tufts: list[list[Pt]]  # small shrubs on the ledges: they give the rock its scale
    summit: list[Pt]


def make_pillar(rng: random.Random, cx: float, top: float, w: float, base: float, *, lean: float = 0.0,
                flare: float = 0.4, taper: float = 0.1, rough: float = 0.03, dome: float = 0.03,
                bulge: float = 0.08, strata: int = 0, flutes: int = 0, cap: float = 0.16,
                trees: float = 0.0, lump: float = 0.0, tufts: int = 0, tiers: int = 0,
                light_x: float = LIGHT_X) -> Pillar:
    """A stone pillar centred on cx, its summit at `top` and its foot at `base`, lit from the side that faces
    the light at x = light_x (the banner's light by default; a card passes its own)."""
    nl, nr, nc, nf, ng = Noise(rng), Noise(rng), Noise(rng), Noise(rng), Noise(rng)
    dome_h = w * dome
    shoulder = top + dome_h
    h = base - shoulder
    amp = rough * w + 0.6
    # broad bulges and waists, then the beds of rock: each sticks out a little between its lip and its foot
    bl = [(rng.uniform(0.08, 0.7), rng.uniform(0.05, 0.12), rng.uniform(-bulge, bulge)) for _ in range(3)]
    br = [(at + rng.uniform(-0.04, 0.04), s, a * rng.uniform(0.3, 1.2)) for at, s, a in bl]
    lit_right = cx < light_x
    beds: list[tuple[float, float, float, float, float, float]] = []  # lip t, foot t, u0, u1, out-left, out-right
    t = rng.uniform(0.03, 0.09)
    for _ in range(strata):
        t1 = t + rng.uniform(3.0, 7.0) * min(1.0, w / 160) / h
        reach = rng.uniform(0.35, 0.7)  # beds run in from the lit edge and thin out: a full ring reads as a can
        u0, u1 = (1 - reach, 1.0) if lit_right else (0.0, reach)
        out = rng.uniform(0.012, 0.028)
        beds.append((t, t1, u0, u1, out if u0 == 0 else 0.0, out * rng.uniform(0.6, 1.3) if u1 == 1 else 0.0))
        t += rng.uniform(0.05, 0.16)
    # tiers: above a tier the pillar is set back on one side, leaving a ledge where shrubs take hold
    steps_in: list[tuple[float, bool, float]] = []  # t, on the right?, how far it is set back (fraction of w)
    for i in range(tiers):
        at = rng.uniform(0.06, 0.16) + i * rng.uniform(0.12, 0.2)
        steps_in.append((at, lit_right if i % 2 == 0 else not lit_right, rng.uniform(0.07, 0.13)))

    def centre(t: float) -> float:
        return cx + lean * h * (1 - t)

    def half(t: float, right: bool) -> float:
        rounding = 0.88 + 0.12 * min(1.0, t * h / (w * 0.14)) ** 0.5
        shape = 1 + sum(a * bump(t, at, s) for at, s, a in (br if right else bl))
        shape += sum((b[5] if right else b[4]) * (step(t, b[0], 0.002) - step(t, b[1], 0.002)) for b in beds)
        shape -= sum(a * (1 - step(t, at, 0.0025)) for at, r, a in steps_in if r == right)
        return w / 2 * rounding * shape * (1 - taper * (1 - t)) * (1 + flare * t * t)

    steps = max(16, int(h / 9))
    ts = {(i / steps) ** 1.1 for i in range(steps + 1)}
    for b in beds:
        ts |= {b[0] - 0.004, b[0] + 0.003, b[1] - 0.003, b[1] + 0.004}
    for at, _, _ in steps_in:
        ts |= {at - 0.006, at - 0.002, at + 0.004, at + 0.01}
    tl = sorted(t for t in ts if 0.0 <= t <= 1.0)
    left = [(centre(t) - half(t, False) + amp * nl(t * h / 60), shoulder + t * h) for t in tl]
    right = [(centre(t) + half(t, True) + amp * nr(t * h / 60), shoulder + t * h) for t in tl]

    k = max(4, int(w / 12))
    xl, xr = left[0][0], right[0][0]

    def summit_y(u: float) -> float:
        return top + dome_h * abs(2 * u - 1) ** 2.2 + nc(u * 4) * w * 0.012

    summit = [(xl + (xr - xl) * j / k, summit_y(j / k)) for j in range(1, k)]
    outline = left[::-1] + summit + right

    side, other = (right, left) if lit_right else (left, right)
    sign = -1 if lit_right else 1
    edge = [p for p, t in zip(side, tl) if t <= 0.92]
    # the lit planes are cut with straight facets, like broken rock, not wavy lines: offsets are picked at a few
    # heights and joined with straight runs
    knots = max(4, int(h / 30))
    fo = [0.11 + 0.05 * nf(i * 1.7) for i in range(knots + 1)]
    go = [0.035 + 0.015 * ng(i * 2.3) for i in range(knots + 1)]

    def facet(vals: list[float], t: float) -> float:
        f = t * knots
        i = min(int(f), knots - 1)
        return vals[i] + (vals[i + 1] - vals[i]) * (f - i)

    top_pt = [summit[-1] if lit_right else summit[0]]
    face = top_pt + edge + [(x + sign * w * facet(fo, t), y) for (x, y), t in zip(edge, tl)][::-1]
    glint = top_pt + edge + [(x + sign * w * facet(go, t), y) for (x, y), t in zip(edge, tl)][::-1]
    back = [p for p, t in zip(other, tl) if t <= 0.95]
    inner_b = [(x - sign * w * (0.12 + 0.05 * ng(t * h / 45)), y) for (x, y), t in zip(back, tl)]
    shade_plane = [summit[0] if lit_right else summit[-1]] + back + inner_b[::-1]

    def across(t: float, u: float) -> float:
        return centre(t) - half(t, False) + (half(t, False) + half(t, True)) * u

    layers: list[list[Pt]] = []
    eye = 410.0  # the horizon: beds above it bow up a touch, as rings seen from below do
    for _, t1, u0, u1, _, _ in beds:
        y1 = shoulder + t1 * h
        bow = w * 0.02 * max(-1.0, min(1.0, (eye - y1) / 400))
        wn = Noise(rng)
        us = [u0 + (u1 - u0) * i / 12 for i in range(13)]
        th = rng.uniform(2.5, 5.0) * min(1.0, w / 150)
        # thickest at the edge it runs in from, thinning out toward its inner end
        thin = [((u - u0) / (u1 - u0)) ** 0.7 if u0 > 0 else ((u1 - u) / (u1 - u0)) ** 0.7 for u in us]
        foot = [(across(t1, u), y1 - bow * math.sin(math.pi * u) + wn(u * 5 + 3) * 1.0) for u in us]
        layers.append(foot + [(x, y + th * (0.3 + 0.7 * k)) for (x, y), k in zip(foot, thin)][::-1])

    painted: list[tuple[list[Pt], float, bool]] = []
    for _ in range(flutes):
        u = rng.uniform(0.08, 0.92)
        t0 = rng.uniform(0.0, 0.35)
        t1 = min(0.98, t0 + rng.uniform(0.25, 0.6))
        wn = Noise(rng)
        line = [(across(t, u) + wn(t * 5) * w * 0.025, shoulder + t * h)
                for t in (t0 + (t1 - t0) * i / 10 for i in range(11))]
        painted.append((line, w * rng.uniform(0.03, 0.07), (u > 0.55) == lit_right))

    depth = max(3.0, min(26.0, cap * w))
    o = w * 0.03 + 1.0
    cap_pts: list[Pt] = [(xl - o, shoulder + depth * 0.15)]
    cap_pts += [(x, y - 1.0) for x, y in summit]
    cap_pts.append((xr + o, shoulder + depth * 0.15))
    m = max(4, int(w / 11))
    dn = Noise(rng)
    for j in range(m, -1, -1):
        u = j / m
        x = xl - o + (xr - xl + 2 * o) * u
        drape = 1.0 + 1.3 * max(0.0, abs(2 * u - 1) - 0.55) / 0.45 * (1.0 if (u > 0.5) == lit_right else 0.4)
        y = summit_y(min(max(u, 0.0), 1.0)) + depth * (0.5 + 0.5 * max(0.0, dn(u * 5, 2))) * drape
        cap_pts.append((x, y))

    crown: list[Pt] = []
    if trees:
        ground = [(xl, summit_y(0.0))] + summit + [(xr, summit_y(1.0))]
        lumps = canopy(rng, ground, trees, lump)
        x0, x1 = xl + lump * 0.2, xr - lump * 0.2
        n = max(8, round((x1 - x0) / max(1.0, lump * 0.35)))
        tops = [(x0 + (x1 - x0) * i / n, skyline(lumps, x0 + (x1 - x0) * i / n)) for i in range(n + 1)]
        crown = [(x, y) for x, y in tops if y < math.inf]
        crown += [(x, summit_y((x - xl) / (xr - xl)) + 3.0) for x, _ in crown[::-1]]

    shrubs: list[list[Pt]] = []
    ledges = [(at + 0.002, r) for at, r, _ in steps_in]
    ledges += [(b[0], lit_right) for b in beds if (b[3] == 1.0 if lit_right else b[2] == 0.0)]
    for t0, on_right in ledges[:tufts]:
        y = shoulder + t0 * h
        out = 1.0 if on_right else -1.0
        ex = centre(t0) + (half(t0 + 0.004, True) if on_right else -half(t0 + 0.004, False))
        sx = ex - out * rng.uniform(2.0, 6.0)
        span = rng.uniform(12.0, 22.0)
        lumps = [(sx - out * span * j / 5 + rng.uniform(-1.0, 1.0),
                  y - rng.uniform(2.5, 5.0) * (1.4 - abs(j / 5 - 0.4)), rng.uniform(2.6, 4.2)) for j in range(6)]
        shrubs.append(cushion(lumps, y + 1.5, 1.0))

    return Pillar(outline, edge, face, glint, shade_plane, lit_right, layers, painted, cap_pts, crown, shrubs,
                  summit)


def canopy(rng: random.Random, ground: list[Pt], height: float, lump: float) -> list[Circle]:
    """Trees on a summit, as one mass: a dome of small lumps with a few taller crowns, every lump a little
    different in size."""
    x0, x1 = ground[0][0] + lump * 0.2, ground[-1][0] - lump * 0.2
    width = x1 - x0
    crowns = [(rng.uniform(0.12, 0.88), rng.uniform(0.7, 1.0), rng.uniform(0.1, 0.22)) for _ in range(4)]

    def ground_y(x: float) -> float:
        return min(ground, key=lambda p: abs(p[0] - x))[1]

    out: list[Circle] = []
    n = max(4, int(width / (lump * 0.7)))
    for i in range(n + 1):
        u = i / n
        x = x0 + width * u + rng.uniform(-0.2, 0.2) * lump
        reach = max(c_h * max(0.0, 1 - ((u - c_u) / c_s) ** 2) for c_u, c_h, c_s in crowns)
        reach = max(reach, 0.45 * math.sin(math.pi * u) ** 0.6)
        r = lump * rng.uniform(0.75, 1.15)
        out.append((x, ground_y(x) - height * reach + r * rng.uniform(0.9, 1.2), r))
    return out


def mountain(rng: random.Random, x0: float, x1: float, peaks: list[tuple[float, float, float]],
             base: float) -> tuple[list[Pt], list[list[Pt]]]:
    """A distant massif: concave flanks rising to several rounded peaks. Also returns, for each peak, the
    facet that faces the light: the flank down from the summit, bounded by a curving spur."""
    n = Noise(rng)

    def fall(u: float) -> float:
        u = min(1.0, u)
        return (u * u * (3 - 2 * u)) ** 0.8  # rounded on top, easing out at the foot

    def ridge(x: float) -> float:
        return min(py + (base - py) * fall(abs(x - px) / spread) for px, py, spread in peaks) + n(x / 50, 4) * 5

    pts = [(x0, base + 30)] + [(x0 + (x1 - x0) * i / 40, ridge(x0 + (x1 - x0) * i / 40)) for i in range(41)]
    pts.append((x1, base + 30))
    facets: list[list[Pt]] = []
    for px, py, spread in peaks:
        s = 1.0 if px < LIGHT_X else -1.0
        xe = min(max(px + s * spread * 0.9, x0), x1)
        flank = [(px + (xe - px) * i / 12, ridge(px + (xe - px) * i / 12)) for i in range(13)]
        top_y = flank[0][1]
        spur = [(px + s * spread * (0.42 * u ** 1.3) + s * 3, top_y + (base + 30 - top_y) * u) for u in
                (i / 8 for i in range(1, 9))]
        facets.append(flank + [(xe, base + 30)] + spur[::-1])
    return pts, facets


@dataclass
class SeaRow:
    top: list[Pt]  # the silhouette's top edge, left to right
    domes: list[Quad]  # the big domes: cx, half-width, height, base y
    riders: list[Quad]  # smaller domes riding on their shoulders
    billows: list[Quad]  # soft swells drawn on the surface of the base plane: cx, cy, rx, ry
    floor: list[Pt]  # the row's body under its domes


def dome_y(x: float, d: Quad) -> float:
    cx, hw, hh, by = d
    u = (x - cx) / hw
    return by - hh * math.sqrt(1 - u * u) if abs(u) < 1 else math.inf


def make_sea(rng: random.Random, y: float, x0: float, x1: float, hw: tuple[float, float],
             hh: tuple[float, float], *, riders: float = 0.5,
             banks: list[tuple[float, float, float]] | None = None, dip: float = 0.0, billows: int = 0,
             spacing: float = 5.0) -> SeaRow:
    """Part of the sea of cloud: broad domes of different sizes, a few with a smaller dome riding on a
    shoulder, merged into one silhouette. Without `banks` the domes run evenly across the width (the base
    plane). With them (centre x, width, strength), the domes swell where a bank stands and the row sinks
    gently by up to `dip` in between, so the rows gather into banks without ever reading as terraces, and the
    sea stays open toward the light."""

    def env(x: float) -> float:
        if not banks:
            return 1.0
        return min(1.0, sum(k * math.exp(-((x - c) / (wd / 2)) ** 2) for c, wd, k in banks))

    domes: list[Quad] = []
    x = x0
    while x < x1:
        w, h = rng.uniform(*hw), rng.uniform(*hh)
        cx = x + w * 0.85
        e = env(cx)
        h *= 0.2 + 0.8 * e
        domes.append((cx, w * (0.7 + 0.3 * e), h, y + dip * (1 - e) + rng.uniform(-0.1, 0.25) * h))
        x = cx + w * (0.7 + 0.3 * e) * rng.uniform(0.3, 0.55)
    extra: list[Quad] = []
    for d in domes:
        if rng.random() < riders * env(d[0]):
            cx, w, h, _ = d
            rx = cx + rng.choice((-1, 1)) * w * rng.uniform(0.3, 0.55)
            rh = h * rng.uniform(0.28, 0.42)
            extra.append((rx, w * rng.uniform(0.26, 0.38), rh, dome_y(rx, d) + rh * 0.6))
    top: list[Pt] = []
    floor: list[Pt] = []
    n = int((x1 - x0) / spacing)
    for i in range(n + 1):
        xx = x0 + (x1 - x0) * i / n
        fy = y + dip * (1 - env(xx)) + 6
        floor.append((xx, fy))
        top.append((xx, min([fy] + [dome_y(xx, d) for d in domes + extra])))
    swells: list[Quad] = []
    for _ in range(billows):
        p = rng.random() ** 1.4  # more, smaller swells toward the horizon
        by = y + 10 + (H - y - 10) * p
        swells.append((rng.uniform(-40, W + 40), by, 26 + 170 * p * rng.uniform(0.7, 1.2),
                       2.4 + 13 * p * rng.uniform(0.7, 1.2)))
    return SeaRow(top, domes, extra, swells, floor[::4] + [floor[-1]])


@dataclass
class Cloud:
    outline: list[Pt]  # an approximate outline, for its extent and centre
    lumps: list[Circle]
    base: float


# one cumulus, as twelve lumps (x, y, r) around the middle of its flat base: a crown that peaks left of centre,
# toward the sun, and steps down to the right
CUMULUS: list[Circle] = [(-138, -14, 18), (-108, -28, 30), (-68, -52, 42), (-18, -82, 52), (38, -92, 56),
                         (92, -66, 44), (132, -38, 32), (160, -18, 20), (0, -40, 50), (64, -38, 46),
                         (-34, -124, 34), (24, -136, 36)]


def make_cloud(rng: random.Random, cx: float, base: float, scale: float) -> Cloud:
    """The sky cloud: twelve lumps of different sizes, a little jittered, merged into one flat-based
    silhouette."""
    lumps = [(cx + (x + rng.uniform(-4, 4)) * scale, base + (y + rng.uniform(-3, 3)) * scale,
              r * scale * rng.uniform(0.94, 1.06)) for x, y, r in CUMULUS]
    return Cloud(cushion(lumps, base, 4.0), lumps, base)


@dataclass
class Pine:
    trunk: list[Pt]
    branches: list[list[Pt]]
    pads: list[list[Pt]]
    s: float


def make_pine(rng: random.Random, gx: float, gy: float, s: float, lean: float) -> Pine:
    """A wind-shaped pine on the outer edge of a summit, leaning out over the drop (lean = +1 right, -1 left)."""

    def at(dx: float, dy: float) -> Pt:
        return gx + lean * dx * s, gy - dy * s

    trunk = [at(0, 0), at(6, 30), at(20, 60), at(42, 84), at(68, 98)]
    branches = [[at(7, 38), at(-12, 50), at(-34, 54)], [at(23, 64), at(48, 66), at(76, 60)],
                [at(40, 82), at(34, 100), at(28, 116)]]
    pads: list[list[Pt]] = []
    for dx, dy, size in ((-32, 58, 28), (80, 64, 32), (72, 102, 40), (28, 121, 30), (-2, 82, 18)):
        px, py = at(dx, dy)
        rx = size * s
        lump = max(2.4, rx * 0.2)
        lumps = []
        m = max(4, int(2 * rx / (lump * 0.8)))
        for i in range(m + 1):
            u = i / m
            x = px - rx + 2 * rx * u
            lumps.append((x + rng.uniform(-0.3, 0.3) * lump,
                          py - rx * 0.42 * math.sin(math.pi * u) ** 0.8 + lump * 0.6, lump * rng.uniform(0.75, 1.1)))
        pads.append(cushion(lumps, py + 1.5, 1.0))
    return Pine(trunk, branches, pads, s)


@dataclass
class Vista:
    clear: tuple[Quad, ...]
    mountains: list[list[Pt]]
    facets: list[list[Pt]]
    ridge: list[Pt]
    far: list[Pillar]
    mid: list[Pillar]
    near: list[Pillar]
    cloud: Cloud
    seas: list[SeaRow]
    stars: list[Quad]
    pine: Pine


def make_vista(clear: tuple[Quad, ...], seed: int = 11) -> Vista:
    def part(k: int) -> random.Random:
        """Each element draws from its own stream, so tuning one never reshuffles the others."""
        return random.Random(seed * 1000 + k)

    rng = part(1)
    nr = Noise(rng)
    ridge = [(-20.0, 540.0)]
    for i in range(0, 50):
        x = -20 + i * 34
        lift = sum(a * math.exp(-((x - c) / s) ** 2) for c, s, a in ((300, 220, 22), (1220, 180, 18), (800, 90, -6)))
        ridge.append((x, 456 - lift - 7 * nr(x / 110, 4)))
    ridge.append((1660.0, 540.0))

    rng = part(2)
    massifs = [
        mountain(rng, 280, 900, [(500, 266, 240), (642, 306, 170), (372, 322, 120)], 466),
        mountain(rng, 720, 1480, [(1110, 278, 250), (968, 354, 130), (1318, 318, 150)], 466),
    ]
    mountains = [m for m, _ in massifs]
    facets = [f for _, fs in massifs for f in fs]

    rng = part(3)
    far = [make_pillar(rng, x, t, w, 520, lean=ln, rough=0.06, taper=0.42, flare=0.5, cap=0.14, bulge=0.1,
                       dome=0.16) for x, t, w, ln in ((540, 370, 24, 0.012), (590, 326, 40, -0.01),
                                                      (650, 392, 20, 0.02), (1006, 350, 34, 0.004),
                                                      (1052, 388, 22, -0.016))]

    rng = part(4)
    mid = [make_pillar(rng, x, t, w, 600, lean=ln, rough=0.045, taper=0.32, flare=0.5, cap=0.18, strata=1,
                       flutes=3, trees=tr, lump=2.4, bulge=0.1, tiers=1, dome=0.08)
           for x, t, w, tr, ln in
           ((436, 284, 58, 11, 0.008), (1192, 286, 64, 11, -0.006), (1290, 380, 40, 7, 0.0))]

    near = [
        make_pillar(part(5), 84, -90, 222, 760, lean=-0.008, rough=0.03, cap=0.12, strata=3,
                    flutes=7, tufts=3, flare=0.35, bulge=0.07, tiers=2),
        make_pillar(part(6), 262, 338, 98, 760, lean=0.012, rough=0.035, cap=0.18, strata=2, flutes=4,
                    trees=15, lump=3.6, tufts=1, flare=0.45, taper=0.16, bulge=0.1, tiers=1),
        make_pillar(part(7), 1446, 326, 168, 760, lean=0.006, rough=0.03, cap=0.14, strata=2,
                    flutes=6, trees=22, lump=4.0, tufts=2, flare=0.4, taper=0.14, bulge=0.08, tiers=1),
    ]

    cloud = make_cloud(part(8), 1494, 204, 0.92)

    seas = [make_sea(part(10), 476, -60, 1660, (140, 220), (4, 9), riders=0.2, billows=34, spacing=8),
            make_sea(part(11), 506, -70, 1670, (40, 70), (20, 32), riders=0.4, spacing=4, dip=30,
                     banks=[(300, 420, 1.0), (620, 220, 0.6), (1050, 320, 0.9), (1400, 440, 1.0)]),
            make_sea(part(12), 552, -80, 1680, (60, 100), (34, 54), riders=0.5, spacing=4, dip=60,
                     banks=[(110, 560, 1.0), (470, 360, 0.8), (1180, 420, 1.0), (1530, 460, 1.0)]),
            make_sea(part(15), 610, -100, 1700, (90, 140), (56, 88), riders=0.6, dip=100,
                     banks=[(270, 640, 1.0), (1340, 620, 1.0)]),
            make_sea(part(16), 624, -120, 1720, (90, 150), (100, 160), riders=0.8, dip=220,
                     banks=[(10, 760, 1.0), (1650, 700, 1.0)])]

    srng = part(13)
    stars: list[Quad] = []
    for _ in range(140):
        sx, sy = srng.uniform(20, 1580), srng.uniform(8, 330)
        sr = srng.uniform(0.5, 1.15) if srng.random() < 0.93 else 1.6
        sa = srng.uniform(0.25, 0.85)
        # no star sits by the type: a speck next to a letter reads as dust
        if any(x0 - 12 < sx < x1 + 12 and y0 - 12 < sy < y1 + 12 for x0, y0, x1, y1 in clear):
            continue
        stars.append((sx, sy, sr, sa))

    gx, gy = near[2].summit[-2]
    pine = make_pine(part(14), gx, gy + 2, 0.66, 1.0)
    return Vista(clear, mountains, facets, ridge, far, mid, near, cloud, seas, stars, pine)


# ---------------------------------------------------------------- drawing


class Svg:
    def __init__(self) -> None:
        self.defs: list[str] = []
        self.body: list[str] = []
        self._ids = 0
        self._grads: dict[str, str] = {}

    def id(self, prefix: str) -> str:
        self._ids += 1
        return f"{prefix}{self._ids}"

    def blur(self, sd: float) -> str:
        fid = "f" + f"{sd:g}".replace(".", "_")
        tag = f'<filter id="{fid}"'
        if not any(d.startswith(tag) for d in self.defs):
            self.defs.append(f'{tag} x="-20%" y="-20%" width="140%" height="140%" '
                             f'color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="{sd:g}"/></filter>')
        return fid

    def clip(self, d: str) -> str:
        return self.clip_shapes(f'<path d="{d}"/>')

    def clip_shapes(self, shapes: str) -> str:
        """A clip path from shape markup; several shapes clip to their union."""
        cid = self.id("c")
        self.defs.append(f'<clipPath id="{cid}">{shapes}</clipPath>')
        return cid

    @staticmethod
    def _stops(stops: Stops) -> str:
        def op(a: float) -> str:
            return "" if a >= 1 else f' stop-opacity="{max(a, 0.0):.3g}"'

        return "".join(f'<stop offset="{num(o * 100)}%" stop-color="{c}"{op(a)}/>' for o, c, a in stops)

    def _grad(self, kind: str, attrs: str, stops: Stops) -> str:
        body = f"{attrs}>{self._stops(stops)}"
        key = kind + body
        if key not in self._grads:  # identical gradients are shared
            gid = self.id("g")
            self._grads[key] = gid
            self.defs.append(f'<{kind} id="{gid}" {body}</{kind}>')
        return self._grads[key]

    def linear(self, stops: Stops, x1: float = 0, y1: float = 0, x2: float = 0, y2: float = 1,
               user: bool = False) -> str:
        if user:
            return self._grad("linearGradient", f'x1="{num(x1)}" y1="{num(y1)}" x2="{num(x2)}" y2="{num(y2)}" '
                              f'gradientUnits="userSpaceOnUse"', stops)
        return self._grad("linearGradient", f'x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}"', stops)

    def soft_spot(self, cx: float, cy: float, rx: float, ry: float, stops: Stops) -> str:
        """A rect filling the ellipse's bounding box with a bounding-box radial gradient: the same soft
        elliptical spot as `ellipse`, but every spot with the same stops shares one gradient."""
        gid = self._grad("radialGradient", 'cx="0.5" cy="0.5" r="0.5"', stops)
        return (f'<rect x="{num(cx - rx)}" y="{num(cy - ry)}" width="{num(2 * rx)}" height="{num(2 * ry)}" '
                f'fill="url(#{gid})"/>')

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, stops: Stops) -> str:
        """A radial gradient stretched into an ellipse, in user space."""
        return self._grad("radialGradient", f'cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" '
                          f'gradientTransform="translate({num(cx)} {num(cy)}) scale({num(rx)} {num(ry)})"', stops)

    def add(self, s: str) -> None:
        self.body.append(s)


def falloff(colour: str, peak: float, k: float = 4.0, n: int = 9, core: str | None = None) -> Stops:
    """Eased stops for a glow: dense near the centre, exponential falloff, reaching zero at the edge."""
    out: Stops = []
    for i in range(n):
        t = (i / (n - 1)) ** 1.6
        a = peak * (math.exp(-k * t) - math.exp(-k)) / (1 - math.exp(-k))
        out.append((t, mix(core, colour, min(1.0, t * 6)) if core else colour, a))
    return out


def light_dir(theme: Theme, x: float, y: float, up: float = 0.3) -> Pt:
    """Unit vector from (x, y) toward the light, tilted up a little for the light of the open sky (or down,
    with a negative `up`, for a mass lit from beneath by a low sun)."""
    lx, ly = theme.light_pos
    dx, dy = unit(lx - x, ly - y)
    return unit(dx * (1 - abs(up)), dy * (1 - abs(up)) - up)


def lit_mass(svg: Svg, shape: str, lit: str, body: str, toward: Pt, shift: float, soft: float,
             inner: str = "") -> str:
    """A shape lit from one side. It is filled with the lit colour, then covered by a soft copy of itself in
    the body colour, pushed away from the light, so one soft lit edge stays uncovered on the side facing it.
    `shape` is SVG shape markup with no fill: one path, or several circles that merge into one mass."""
    cid = svg.clip_shapes(shape)
    tx, ty = -toward[0] * shift, -toward[1] * shift
    return (f'<g clip-path="url(#{cid})"><g fill="{lit}">{shape}</g>'
            f'<g fill="{body}" stroke="{body}" stroke-width="{num(soft * 4)}" filter="url(#{svg.blur(soft)})" '
            f'transform="translate({num(tx)} {num(ty)})">{shape}</g>{inner}</g>')


def mass_centre(pts: list[Pt]) -> Pt:
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def draw_leaves(svg: Svg, pts: list[Pt], theme: Theme, depth: float, shift: float, soft: float) -> str:
    lit, body, base = (mix(c, theme.haze, min(1.0, depth * 1.1)) for c in theme.leaf)
    g = svg.linear([(0, body, 1), (1, base, 1)])
    cx, cy = mass_centre(pts)
    return lit_mass(svg, f'<path d="{poly(pts)}"/>', lit, f"url(#{g})", light_dir(theme, cx, cy, 0.4), shift, soft)


def draw_glare(svg: Svg, theme: Theme, r: float, strength: float, squash: float = 1.0) -> None:
    lx, ly = theme.light_pos
    g = svg.ellipse(lx, ly, r, r * squash, falloff(theme.glow, strength, k=3.2))
    svg.add(f'<rect width="{W}" height="{H}" fill="url(#{g})"/>')


def draw_bloom(svg: Svg, theme: Theme) -> None:
    """The wide bloom around the light, behind the hills."""
    lx, ly = theme.light_pos
    tight, wide, _ = theme.bloom
    for r, peak, k in ((440, wide, 4.2), (190, tight * 0.7, 3.0)):
        g = svg.ellipse(lx, ly, r, r, falloff(theme.glow, peak, k=k, core=theme.light))
        svg.add(f'<circle cx="{num(lx)}" cy="{num(ly)}" r="{num(r)}" fill="url(#{g})"/>')


def draw_light(svg: Svg, theme: Theme) -> None:
    """The disc and its bright core, drawn over the haze: a white centre that melts into the glow."""
    lx, ly = theme.light_pos
    r = theme.light_r * 2.8
    g = svg.ellipse(lx, ly, r, r, falloff(theme.glow, theme.bloom[0], k=1.8, core=theme.light))
    svg.add(f'<circle cx="{num(lx)}" cy="{num(ly)}" r="{num(r)}" fill="url(#{g})"/>')
    svg.add(f'<circle cx="{num(lx)}" cy="{num(ly)}" r="{num(theme.light_r)}" fill="{theme.light}" '
            f'filter="url(#{svg.blur(1.6)})"/>')


def draw_cloud(svg: Svg, cloud: Cloud, theme: Theme) -> None:
    """The one sky cloud: cool on top, warm underneath (a low sun lights it from below), soft light on the
    lumps that face the sun and a bright rim along its sunward underside."""
    top, body, under = theme.cloud
    y0 = min(y - r for _, y, r in cloud.lumps)
    g = svg.linear([(0, top, 1), (0.6, body, 1), (1, under, 1)], 0, y0, 0, cloud.base, user=True)
    cx, cy = mass_centre(cloud.outline)
    shape = "".join(f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(r)}"/>' for x, y, r in cloud.lumps)
    reach = [(x - math.sqrt(r * r - (cloud.base - y) ** 2), x + math.sqrt(r * r - (cloud.base - y) ** 2))
             for x, y, r in cloud.lumps if y + r > cloud.base]
    bl, br = min(a for a, _ in reach), max(b for _, b in reach)
    shape += f'<path d="{poly([(bl, cloud.base + 2), (bl + 14, cloud.base - 30), (br - 14, cloud.base - 30), (br, cloud.base + 2)])}"/>'
    toward = light_dir(theme, cx, cy, -0.2)
    # the side that faces the light glows softly; the far side stays cool
    xs = [x for x, _ in cloud.outline]
    ys = [y for _, y in cloud.outline]
    rx, ry = (max(xs) - min(xs)) * 0.6, (max(ys) - min(ys)) * 0.75
    gx, gy = cx + toward[0] * rx * 0.55, cy + toward[1] * ry * 0.7
    e = svg.ellipse(gx, gy, rx, ry, falloff(theme.cloud_lit, 0.85, k=2.0))
    inner = (f'<rect x="{num(gx - rx)}" y="{num(gy - ry)}" width="{num(2 * rx)}" height="{num(2 * ry)}" '
             f'fill="url(#{e})"/>')
    flat = svg.clip(f"M0 0H{W}V{num(cloud.base)}H0Z")
    svg.add(f'<g filter="url(#{svg.blur(1.1)})"><g clip-path="url(#{flat})">'
            + lit_mass(svg, shape, theme.cloud_rim, f"url(#{g})", toward, theme.cloud_rim_width, 3.0, inner)
            + "</g></g>")


def draw_mountains(svg: Svg, v: Vista, theme: Theme, depth: float) -> None:
    col = mix(theme.rock_top, theme.haze, depth)
    body = svg.linear([(0, col, 1), (0.6, mix(col, theme.sea[1], 0.35), 1), (1, mix(col, theme.sea[1], 0.7), 1)])
    lit = mix(theme.rock_lit, theme.haze, depth * 0.45)
    parts = []
    for pts in v.mountains:
        lit_right = pts[0][0] < LIGHT_X - 200
        g = svg.linear([(0, lit, 0.7), (0.25, lit, 0.35), (0.55, lit, 0)], 1 if lit_right else 0, 0,
                       0 if lit_right else 1, 0)
        d = smooth(pts)
        parts.append(f'<path fill="url(#{body})" d="{d}"/><path fill="url(#{g})" d="{d}"/>')
    fg = svg.linear([(0, lit, 0.4), (0.5, lit, 0.14), (1, lit, 0)])
    parts.append(f'<path fill="url(#{fg})" d="{"".join(smooth(f) for f in v.facets)}"/>')
    svg.add(f'<g filter="url(#{svg.blur(1.4)})">{"".join(parts)}</g>')


def draw_pillars(svg: Svg, pillars: list[Pillar], theme: Theme, depth: float, blur: float, rim: float,
                 rim_w: float, leaf_soft: float) -> None:
    rock = mix(theme.rock, theme.haze, depth)
    top = mix(theme.rock_top, theme.haze, depth)
    base = mix(rock, theme.sea[1], 0.7)
    body = svg.linear([(0, top, 1), (0.16, mix(top, rock, 0.6), 1), (0.55, rock, 1), (1, base, 1)])
    lit = mix(mix(theme.rock_top, theme.rock_lit, 0.5), theme.haze, depth * 0.5)
    bright = mix(mix(theme.rock_top, theme.rock_lit, 0.85), theme.haze, depth * 0.5)
    face = svg.linear([(0, lit, 0.7), (0.3, lit, 0.5), (0.75, lit, 0.15), (1, lit, 0)])
    glint = svg.linear([(0, bright, 0.95), (0.3, bright, 0.7), (0.75, bright, 0.2), (1, bright, 0)])
    dark = mix(rock, "#08121a", 0.4)
    shade_g = svg.linear([(0, dark, 0.0), (0.12, dark, 0.42), (1, dark, 0.12)])
    rim_g = svg.linear([(0, theme.rim, rim), (0.45, theme.rim, rim * 0.45), (0.9, theme.rim, 0)])
    grass_lit, grass = (mix(c, theme.haze, min(1.0, depth * 0.95)) for c in theme.grass)
    cap = svg.linear([(0, grass_lit, 1), (0.45, mix(grass_lit, grass, 0.45), 1), (1, grass, 1)])
    under = mix(rock, "#050b10", 0.45)
    fl_dark, fl_lit = mix(rock, "#050b10", 0.3), mix(top, lit, 0.4)

    parts = [f'<g filter="url(#{svg.blur(blur)})">' if blur else "<g>"]
    for p in pillars:
        d = smooth(p.outline)
        parts.append(f'<path fill="url(#{body})" d="{d}"/>')
        parts.append(f'<path fill="url(#{shade_g})" d="{smooth(p.shade)}"/>')
        parts.append(f'<path fill="url(#{face})" d="{poly(p.face)}"/><path fill="url(#{glint})" d="{poly(p.glint)}"/>')
        inner = ""
        if p.flutes:
            strokes = "".join(f'<path stroke="{fl_lit if light else fl_dark}" stroke-width="{num(width)}" '
                              f'd="{smooth(line, closed=False)}"/>' for line, width, light in p.flutes)
            inner += (f'<g fill="none" stroke-opacity="0.22" stroke-linecap="round" '
                      f'filter="url(#{svg.blur(round(max(1.2, p.flutes[0][1] * 0.35), 1))})">{strokes}</g>')
        if p.strata:
            inner += (f'<path fill="{under}" fill-opacity="0.34" filter="url(#{svg.blur(1.2)})" '
                      f'd="{"".join(smooth(u) for u in p.strata)}"/>')
        if inner:
            parts.append(f'<g clip-path="url(#{svg.clip(d)})">{inner}</g>')
        if rim > 0:
            parts.append(f'<path fill="none" stroke="url(#{rim_g})" stroke-width="{rim_w:g}" '
                         f'stroke-linecap="round" d="{smooth(p.edge, closed=False)}"/>')
        parts.append(f'<path fill="url(#{cap})" d="{smooth(p.cap)}"/>')
        for tuft in p.tufts:
            parts.append(draw_leaves(svg, tuft, theme, depth, 1.8, 0.8))
        if p.canopy:
            parts.append(draw_leaves(svg, p.canopy, theme, depth, 2.6 if depth < 0.2 else 1.6, leaf_soft))
    parts.append("</g>")
    svg.add("".join(parts))


def draw_pine(svg: Svg, v: Vista, theme: Theme) -> None:
    pine = v.pine
    s = pine.s
    wood = [f'<path stroke-width="{num(7 * s)}" d="{smooth(pine.trunk[:3], closed=False)}"/>',
            f'<path stroke-width="{num(4.6 * s)}" d="{smooth(pine.trunk[2:], closed=False)}"/>']
    wood += [f'<path stroke-width="{num(2.8 * s)}" d="{smooth(b, closed=False)}"/>' for b in pine.branches]
    svg.add(f'<g fill="none" stroke="{theme.bark}" stroke-linecap="round">{"".join(wood)}</g>')
    svg.add("".join(draw_leaves(svg, pad, theme, 0.0, 2.2, 0.9) for pad in pine.pads))


def draw_sea(svg: Svg, row: SeaRow, theme: Theme, depth: float, below: float, *, glade: float = 0.0,
             edge: float = 8.0) -> None:
    """One row of the sea of cloud, backlit: one silhouette with a cool body that darkens toward the row in
    front, a soft glowing band that follows every dome's top, a brighter, warmer shoulder on the side of each
    dome that faces the light, and a glade right under the light."""
    lit, body, shade = (mix(c, theme.haze, depth) for c in theme.sea)
    warm = mix(theme.sea_warm, theme.haze, depth * 0.5)
    lx, _ = theme.light_pos
    x0, x1 = row.top[0][0], row.top[-1][0]
    shape = "".join(f'<ellipse cx="{num(cx)}" cy="{num(by)}" rx="{num(hw)}" ry="{num(hh)}"/>'
                    for cx, hw, hh, by in row.domes + row.riders)
    shape += f'<path d="{poly(row.floor + [(x1, H + 40), (x0, H + 40)])}"/>'
    ytop = min(y for _, y in row.top)
    g = svg.linear([(0, mix(body, lit, 0.25), 1), (0.45, body, 1), (1, shade, 1)], 0, ytop, 0, below, user=True)
    span = max(40.0, below - ytop)
    w_g = svg.ellipse(lx, ytop, 380 + 320 * (1 - depth), span * 1.2, falloff(warm, 0.8, k=2.4))
    rect = f'x="-20" y="{num(ytop - 2)}" width="{W + 40}" height="{num(H - ytop + 4)}"'
    parts = [f'<rect {rect} fill="url(#{g})"/>', f'<rect {rect} fill="url(#{w_g})"/>']

    # swells on the base plane: a soft shadow with a soft lit crest just above it
    for bx, by, brx, bry in row.billows:
        sgn = math.copysign(1.0, lx - bx)
        parts.append(svg.soft_spot(bx, by, brx, bry, falloff(shade, 0.45, k=2.4)))
        parts.append(svg.soft_spot(bx + sgn * brx * 0.15, by - bry * 1.05, brx * 0.85, bry * 0.7,
                                   falloff(lit, 0.65, k=2.4)))

    # each big dome turns away from the light on one side: a soft cool shadow there gives it volume
    for cx, hw, hh, by in row.domes:
        s = 0.0 if abs(lx - cx) < hw * 0.3 else math.copysign(1.0, lx - cx)
        sx, sy = cx - s * hw * 0.42, by - hh * 0.35
        parts.append(svg.soft_spot(sx, sy, hw * 0.62, hh * 0.75, falloff(shade, 0.55, k=2.2)))

    # a soft glowing band along the whole top edge, bright and warm near the light, faint away from it
    f0 = (lx - x0) / (x1 - x0)
    band_g = svg.linear([(0, lit, 0.35), (max(0.0, f0 - 0.3), lit, 0.45), (f0, mix(lit, warm, 0.7), 1),
                         (min(1.0, f0 + 0.3), lit, 0.45), (1, lit, 0.35)], x0, 0, x1, 0, user=True)
    parts.append(f'<path fill="none" stroke="url(#{band_g})" stroke-width="{num(edge * 3)}" '
                 f'stroke-linejoin="round" transform="translate(0 {num(edge * 1.1)})" '
                 f'filter="url(#{svg.blur(round(edge * 1.1, 1))})" d="{edge_path(row.top, spacing_of(row))}"/>')

    # brighter shoulders: the stretch of each dome's top that faces the light
    hi_lines: list[str] = []
    for dm in row.domes + row.riders:
        cx, hw, _, _ = dm
        s = 0.0 if abs(lx - cx) < hw * 0.35 else math.copysign(1.0, lx - cx)
        a, b = sorted((cx - s * 0.2 * hw - (1 - abs(s)) * 0.7 * hw, cx + s * 0.9 * hw + (1 - abs(s)) * 0.7 * hw))
        run: list[Pt] = []
        for x, y in row.top + [(math.inf, 0.0)]:
            if a <= x <= b and abs(dome_y(x, dm) - y) < 0.6:
                run.append((x, y))
            elif run:
                if len(run) > 3:
                    t = math.exp(-((cx - lx) / 480) ** 2)
                    hi = mix(mix(lit, "#ffffff", 0.5), mix(warm, "#ffffff", 0.45), t)
                    hi_lines.append(f'<path stroke="{hi}" d="{poly(run, closed=False)}"/>')
                run = []
    parts.append(f'<g fill="none" stroke-width="{num(edge * 0.75)}" stroke-linecap="round" '
                 f'transform="translate(0 {num(edge * 0.3)})" filter="url(#{svg.blur(round(edge * 0.3, 1))})">'
                 + "".join(hi_lines) + "</g>")
    if glade:
        gy = min(y for x, y in row.top if abs(x - lx) < 60) + edge * 0.5
        reach = H - gy
        for rx, ry, peak, c in ((360, 30.0, glade * 0.7, theme.glade), (130, 11.0, glade, theme.glade),
                                (130, reach, glade * 0.7, mix(theme.glade, warm, 0.5))):
            parts.append(svg.soft_spot(lx, gy, rx, ry, falloff(c, peak, k=3.0)))
    svg.add(f'<g clip-path="url(#{svg.clip_shapes(shape)})">{"".join(parts)}</g>')


def spacing_of(row: SeaRow) -> float:
    return row.top[1][0] - row.top[0][0]


def edge_path(top: list[Pt], spacing: float) -> str:
    """The top edge as open runs, broken wherever it jumps (where one dome rises in front of another), so a
    stroke along it never draws a vertical seam."""
    runs: list[list[Pt]] = [[top[0]]]
    for a, b in zip(top, top[1:]):
        if abs(b[1] - a[1]) > spacing * 2.5:
            runs.append([])
        runs[-1].append(b)
    return "".join(poly(r, closed=False) for r in runs if len(r) > 1)


def hero(theme: Theme, name_face: Face, role_face: Face, v: Vista) -> str:
    svg = Svg()
    lx, ly = theme.light_pos

    sky = svg.linear([(o, c, 1) for o, c in theme.sky])
    svg.add(f'<rect width="{W}" height="{H}" fill="url(#{sky})"/>')

    if theme.stars:
        dots = []
        for x, y, r, a in v.stars:
            fade = min(1.0, math.hypot(x - lx, y - ly) / 260) ** 1.5 * (1 - y / 360)
            if a * fade > 0.06:
                dots.append(f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(r)}" opacity="{a * fade:.2f}"/>')
        svg.add(f'<g fill="#f4f1e4">{"".join(dots)}</g>')

    draw_glare(svg, theme, 980, theme.bloom[2], squash=0.62)
    draw_cloud(svg, v.cloud, theme)
    draw_bloom(svg, theme)

    draw_mountains(svg, v, theme, 0.78)
    col = mix(theme.rock, theme.haze, 0.74)
    g = svg.linear([(0, col, 1), (1, mix(col, theme.sea[1], 0.6), 1)])
    svg.add(f'<path fill="url(#{g})" filter="url(#{svg.blur(1.2)})" d="{smooth(v.ridge)}"/>')
    draw_glare(svg, theme, 620, theme.bloom[1] * 0.8, squash=0.55)

    draw_pillars(svg, v.far, theme, 0.64, 1.0, theme.rim_far, 0.9, 0.0)
    draw_sea(svg, v.seas[0], theme, 0.3, 560, glade=1.0, edge=2.2)
    draw_sea(svg, v.seas[1], theme, 0.34, 560, glade=0.55, edge=3.0)
    draw_glare(svg, theme, 520, theme.bloom[1] * 0.35, squash=0.5)

    draw_pillars(svg, v.mid, theme, 0.38, 0.7, 0.75, 1.0, 0.6)
    draw_sea(svg, v.seas[2], theme, 0.22, 600, glade=0.35, edge=4.2)
    draw_sea(svg, v.seas[3], theme, 0.1, 640, edge=6.0)
    draw_glare(svg, theme, 460, theme.bloom[1] * 0.12, squash=0.45)
    draw_light(svg, theme)

    draw_pillars(svg, v.near, theme, 0.03, 0.0, 0.9, 1.2, 0.9)
    draw_pine(svg, v, theme)
    draw_sea(svg, v.seas[4], theme, 0.0, H, edge=9.0)

    colour, strength, height = theme.foot
    fg = svg.linear([(0, colour, 0), (0.5, colour, strength * 0.4), (1, colour, strength)], 0, H - height, 0, H,
                    user=True)
    svg.add(f'<rect y="{num(H - height)}" width="{W}" height="{num(height)}" fill="url(#{fg})"/>')

    svg.add(f'<path fill="{theme.ink}" d="{name_face.path(NAME, NAME_SIZE, W / 2, NAME_Y, NAME_TRACK)}"/>')
    svg.add(f'<path fill="{theme.ink_soft}" d="{role_face.path(ROLE, ROLE_SIZE, W / 2, ROLE_Y, ROLE_TRACK)}"/>')

    label = f"{NAME}, {ROLE}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="{label}">'
            f"<title>{label}</title>"
            f'<defs><clipPath id="panel"><rect width="{W}" height="{H}" rx="28"/></clipPath>{"".join(svg.defs)}'
            f'</defs><g clip-path="url(#panel)">{"".join(svg.body)}</g></svg>\n')
