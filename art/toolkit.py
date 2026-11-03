"""The toolkit: one small pill per tool, its logo and its name in Inter, for the light and the dark page.

Each pill is its own image, set inline in the README, so the row wraps like text on any width of page. A pill
is drawn at two units to the pixel and shown 34 px tall. Logos come from icons.py; the few tools without one
(XGBoost, RAG, LoRA, SQL and AWS) get a plain glyph drawn here on the same 24 x 24 grid.
"""

from __future__ import annotations

from dataclasses import dataclass

from icons import SIMPLE_ICONS
from inter import Face, Ink, num

H = 68                 # the image height in units (34 px shown)
PILL_Y, PILL_H = 6, 56
ICON = 30              # the logo's size
PAD, GAP, PAD_END = 20, 12, 24
SIDE = 4               # transparent room at each end, so neighbouring pills keep apart
TEXT_SIZE = 27
BASELINE = PILL_Y + PILL_H / 2 + 0.364 * TEXT_SIZE  # Inter's capitals centred in the pill
SHOWN = 34


@dataclass(frozen=True)
class Palette:
    key: str
    fill: str     # the pill
    edge: str     # its hairline
    icon: str
    text: str


# the page's own greys for the pill, with the banner's jade for the logos
LIGHT = Palette("day", "#f6f8fa", "#d8dee4", "#33555a", "#1f2328")
DARK = Palette("evening", "#151b23", "#30363d", "#9cc3b9", "#e6edf3")


@dataclass(frozen=True)
class Tool:
    key: str    # file name
    name: str
    icon: str   # a key in icons.SIMPLE_ICONS, or one of the glyphs drawn here


TOOLS = (
    Tool("python", "Python", "python"),
    Tool("pytorch", "PyTorch", "pytorch"),
    Tool("transformers", "Hugging Face Transformers", "huggingface"),
    Tool("scikit-learn", "scikit-learn", "scikitlearn"),
    Tool("xgboost", "XGBoost", "tree"),
    Tool("langgraph", "LangGraph", "langgraph"),
    Tool("rag", "RAG", "lookup"),
    Tool("mcp", "MCP", "modelcontextprotocol"),
    Tool("lora", "LoRA", "low-rank"),
    Tool("sql", "SQL", "database"),
    Tool("duckdb", "DuckDB", "duckdb"),
    Tool("fastapi", "FastAPI", "fastapi"),
    Tool("docker", "Docker", "docker"),
    Tool("aws", "AWS", "cloud"),
    Tool("typescript", "TypeScript", "typescript"),
    Tool("go", "Go", "go"),
    Tool("rust", "Rust", "rust"),
)


def line(c: str, d: str, w: float = 1.8) -> str:
    return (f'<path d="{d}" fill="none" stroke="{c}" stroke-width="{w}" stroke-linecap="round" '
            f'stroke-linejoin="round"/>')


def glyph(name: str, p: Palette) -> str:
    """A tool's logo or glyph on the 24 x 24 grid, in the palette's icon colour."""
    c = p.icon
    if name in SIMPLE_ICONS:
        return f'<path fill="{c}" d="{SIMPLE_ICONS[name]}"/>'
    if name == "tree":  # gradient-boosted trees: one small decision tree
        nodes = [(12, 4, 2.6), (6.5, 12, 2.3), (17.5, 12, 2.3), (3.5, 20, 1.9), (9.5, 20, 1.9), (14.5, 20, 1.9),
                 (20.5, 20, 1.9)]
        edges = "M12 4L6.5 12M12 4L17.5 12M6.5 12L3.5 20M6.5 12L9.5 20M17.5 12L14.5 20M17.5 12L20.5 20"
        return line(c, edges, 1.5) + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c}"/>' for x, y, r in nodes)
    if name == "lookup":  # retrieval: a page under a lens
        return (f'<rect x="2.5" y="2" width="12.5" height="17" rx="1.8" fill="none" stroke="{c}" stroke-width="1.8"/>'
                + line(c, "M6 7H11.5M6 10.5H11.5M6 14H9")
                + f'<circle cx="16.2" cy="15.6" r="4.4" fill="{p.fill}" stroke="{c}" stroke-width="1.9"/>'
                + line(c, "M19.4 18.8L22 21.4", 2.2))
    if name == "low-rank":  # a frozen weight beside its two thin trainable factors
        return (f'<rect x="3" y="3" width="4.6" height="18" rx="1.3" fill="{c}"/>'
                f'<rect x="10" y="3" width="11" height="4.6" rx="1.3" fill="{c}"/>'
                f'<rect x="10.9" y="10.9" width="9.2" height="9.2" rx="1.3" fill="none" stroke="{c}" '
                f'stroke-width="1.8" opacity="0.5"/>')
    if name == "database":
        return (f'<ellipse cx="12" cy="5.5" rx="8" ry="3" fill="none" stroke="{c}" stroke-width="1.8"/>'
                + line(c, "M4 5.5V18.5A8 3 0 0 0 20 18.5V5.5") + line(c, "M4 12A8 3 0 0 0 20 12"))
    if name == "cloud":
        return f'<path fill="{c}" d="M7 19.5H17.6A4.4 4.4 0 0 0 18.3 10.75A6.2 6.2 0 0 0 6.4 9.6A5 5 0 0 0 7 19.5Z"/>'
    raise KeyError(name)


def pill(t: Tool, p: Palette, face: Face) -> str:
    ink = Ink(fine=0)
    tw = face.width(t.name, TEXT_SIZE)
    w = SIDE + PAD + ICON + GAP + tw + PAD_END + SIDE
    x_text = SIDE + PAD + ICON + GAP
    k = ICON / 24
    words = ink.text(face, t.name, TEXT_SIZE, x_text + tw / 2, BASELINE)
    body = (f'<rect x="{SIDE + 0.75}" y="{PILL_Y + 0.75}" width="{num(w - 2 * SIDE - 1.5)}" height="{PILL_H - 1.5}" '
            f'rx="{(PILL_H - 1.5) / 2}" fill="{p.fill}" stroke="{p.edge}" stroke-width="1.5"/>'
            f'<g transform="translate({SIDE + PAD} {num(PILL_Y + (PILL_H - ICON) / 2)}) scale({num(k)})">'
            f'{glyph(t.icon, p)}</g><g fill="{p.text}">{words}</g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{num(w)}" height="{H}" viewBox="0 0 {num(w)} {H}" '
            f'role="img" aria-label="{t.name}"><title>{t.name}</title><defs>{ink.library()}</defs>{body}</svg>\n')


def readme_html() -> str:
    """The toolkit as README markup: one centred paragraph of pills, each its own image."""
    pics = (f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/toolkit/{t.key}-evening.svg">'
            f'<img src="assets/toolkit/{t.key}-day.svg" height="{SHOWN}" alt="{t.name}"></picture>' for t in TOOLS)
    return '<p align="center">\n' + "\n".join(pics) + "\n</p>"
