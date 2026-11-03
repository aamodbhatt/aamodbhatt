"""One motif per card: the single quiet detail that makes a card its project's own.

A card's motif lives in art/motifs/<key>.py, with any "-" in the key written "_" (parameter-golf ->
parameter_golf.py), and exposes one function:

    def draw(stage: Stage, svg: Svg) -> Layers

`stage` (stage.py) is everything the motif may know about its card, in card coordinates: its size, the
horizon, the boxes of its type, the free zones, its palette and light, day or evening, its index and row, and
its own random streams. `svg` is the card's Svg: use it only for defs (svg.linear, svg.ellipse, svg.soft_spot,
svg.blur, svg.clip, svg.clip_shapes, svg.id), so ids stay unique within the card; never add to svg.body. Return
the markup in Layers, one string per layer of the scene (see Layers for the order). To use a scene helper
that adds to svg.body, such as draw_pillars, wrap it: drawn(svg, lambda: draw_pillars(svg, ...)).

Rules of the house: plain SVG shapes, no <text>, <style>, <image>, scripts or external references; ids come
from svg.id(prefix) with any prefix but "t" (the glyphs use t0, t1 ...), and "panel" is taken. Absolute paths
made of M, L, H, V, Q, C and Z are rewritten in relative form at 0.1 unit; other paths are kept as written.

A card with no module of its own draws the default: today's plain edge pillar (_pillar.py). A minimal motif:

    from scene import Svg
    from stage import Box, Layers, Stage

    def draw(stage: Stage, svg: Svg) -> Layers:
        z = stage.zones.outer_horizon
        x, y = z.cx, stage.horizon - 30
        assert stage.clear(Box(x - 6, y - 6, x + 6, y + 6))
        return Layers(far=f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{stage.theme.rock}"/>')
"""

from __future__ import annotations

import importlib
import importlib.util
from collections.abc import Iterable

from stage import Motif

from . import _pillar


def module_name(key: str) -> str:
    return key.replace("-", "_")


def motif(key: str) -> Motif:
    """The motif for the card `key`: its own module's draw(), or the default edge pillar."""
    name = f"{__name__}.{module_name(key)}"
    if importlib.util.find_spec(name) is None:
        return _pillar.draw
    return importlib.import_module(name).draw


def registry(keys: Iterable[str]) -> dict[str, Motif]:
    """Card key -> motif, for every key."""
    return {k: motif(k) for k in keys}


def source(key: str) -> str:
    """Where a card's motif comes from: its own module, or the default."""
    m = motif(key)
    return m.__module__.rsplit(".", 1)[-1] if m is not _pillar.draw else "_pillar (default)"
