# Art

Every image in `../assets` is drawn in code. Rebuild them all from the repo root with one command:

```sh
uv run art/build.py
```

## The banner

Stone pillars rising from a sea of cloud toward a low golden sun (`hero-day.svg`, light theme), and the same
vista under the moon (`hero-evening.svg`, dark theme).

## The cards

`cards/<name>.svg`: eight project cards and one research card, each a small view of the banner's world, and
each the same image in the light and the dark theme. The headline number rises out of the sea of cloud like one of the pillars: it
stands on the near cloud tops, with the far cloud running out to the horizon behind its foot and the low light
right behind it. Every digit, comma, decimal point, slash and unit stays whole.

- One day passes across the cards, in page order: sunrise, morning, midday, afternoon, golden hour, sunset,
  dusk, moonrise and a moonlit night. From dusk on the sky is dark, so the type turns light and the stone takes
  the banner's moonlit palette. The light behind the number is the sun by day and a moon-white halo by night.
- Each card has one motif of its own toward its outer edge (see below), so a pair of cards is framed the way the
  banner is, and no two cards are alike.
- The card text, its numbers and its order live in one list at the top of `cards.py`; a `|` in a short line
  marks where it breaks. `cards.readme_html()` writes the matching README markup (each card 392 px wide, so two
  fit side by side in any column of 788 px or more), with the full meaning of each card in its alt text.
- Each card links to its repository (Parameter Golf to its pull request), and its title says so: the name and
  a small arrow (U+2197, which Inter sets at x-height), in a link blue: `#174d91` on a light sky and `#7db3f2`
  on a dark one, each taken further from the sky where it must be to keep 4.5:1 contrast.

## Motifs

Every card shares the world (the sky, the light, the sea of cloud and the number on the horizon) and gets one
quiet motif of its own, drawn in the banner's flat, backlit style under its card's light, always clear of the type:

| card | motif |
|---|---|
| marionette | the edge pillar held like a puppet: four fine strings run up to a wooden control in a hand out of frame |
| dreamcade | a round-headed doorway glows in the pillar's foot, its light breaking into a few square pixels above it |
| quarry | the pillar cut back in two benches of pale fresh stone, with cut blocks stacked three, two, one on the floor |
| witness | a small lighthouse on a slimmer pillar, its beam out over the cloud |
| bitgolf | the pillar's summit mown into a green, with a flag whose pennant catches the light |
| persuadables | twin pillars from one base; the lifted one is crowned with a pine in blossom (the uplift) |
| nandbox | a jade pixel snake arching through the cloud toward one round stone |
| excelsior | a floating stair of the pillars' stone that climbs ever more steeply into the sky, its side ruled into cells |
| parameter-golf | a ball's dotted flight over the pillar onto a tiny green on a far summit |

A card's motif lives in `motifs/<key>.py` (`parameter-golf` becomes `parameter_golf.py`) as one function,
`draw(stage: Stage, svg: Svg) -> Layers`, found by its file name. A card with no module of its own draws the
default, the plain pillar at its outer edge with at least 36 units of sky between it and the panel's edge and
30 between it and the number (`motifs/_pillar.py`); several motifs start from that pillar
(`_pillar.edge_pillars(stage)`) and carve, crown or replace it.

- `stage.py` defines what a motif gets and returns. The `Stage` holds, in card coordinates (800 x 480, x right,
  y down): the panel, the horizon and the number's baseline, the light, a box for the title, each line of the
  short line, the number and the label, the free zones, the card's palette and light, whether its sky
  is dark, its index and row, and its own random streams. `Layers` holds the motif's markup for five layers of the scene:
  `sky`, `far`, `mid`, `near` and `front`, back to front. Nothing is drawn over the type.
- A motif uses `svg` only for defs (gradients, blurs, clips), so ids stay unique within a card, and may reuse
  the scene's helpers: `make_pillar(..., light_x=stage.light[0])`, then `drawn(svg, lambda: draw_pillars(...))`.
- Each motif checks, at build time, that what it draws keeps `stage.air` (24 units) from every line of type
  (`stage.clear`), so the build stops rather than draw near a title, a line or a number.

## The code

- `build.py` writes the SVGs.
- `scene.py` draws the sky, the sun or moon, one cloud, the distant hills, the pillars with their trees and
  the sea of cloud for each theme.
- `cards.py` reuses those helpers and colours for the cards: the shared world in the banner's own
  coordinates, shifted onto the card, with each card's motif drawn into it.
- `stage.py` and `motifs/` hold the motif hook and the motifs.
- `inter.py` turns all text into SVG outlines, so the images need no font at runtime. On the cards each glyph
  is stored once and reused.

Every element has its own seeded random stream, so the two banners show exactly the same place and a rebuild is
byte-for-byte stable.

The first run downloads Inter from the Google Fonts repository, checks its SHA-256 and keeps it in `art/.cache/`
(gitignored), along with the static instances made from it, so later runs take about a second. Font files are
never committed.

Typeface: [Inter](https://github.com/rsms/inter) by Rasmus Andersson, licensed under the SIL Open Font License 1.1.
