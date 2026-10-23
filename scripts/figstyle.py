"""One visual language for every figure in this project.

Figures in a README are read in both GitHub themes, so everything here sits on an opaque near-white
canvas and relies on value contrast rather than hue: the same figure stays legible whether the page
around it is light or dark. Colour is used for one job only — telling the four outcome classes and
the model families apart — and never for decoration.

The palette is checked for the two most common forms of colour-vision deficiency by keeping the
positive/negative pair separated in lightness as well as hue (orange-red vs steel blue), and by
giving every coloured series a distinct marker or dash pattern as well.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import numpy as np
from matplotlib import font_manager  # noqa: F401  (registers system fonts)

# ----------------------------------------------------------------------- palette
PAPER = "#FFFFFF"
CANVAS = "#F7F8FA"
INK = "#131A22"
MUTED = "#5E6A76"
FAINT = "#9AA4AE"
GRID = "#E3E7EB"

SELECTIVE = "#C03A1D"      # the positive class: a selective effect on network formation
NO_EFFECT = "#2B6C93"      # the negative class: nothing in the tested range
CYTOTOX = "#7A6C9A"        # non-selective cytotoxicity: excluded, and that exclusion matters
UNKNOWN = "#98A1AA"        # inconclusive / not modellable

MODEL = "#0E6F63"          # the read-across model, the one the result rests on
MODEL_ALT = "#1D4E89"      # the structural forest
MODEL_WEAK = "#8C7B52"     # the physicochemical baseline
RANDOM = "#A8B0B8"         # random testing order
PERFECT = "#C7CDD3"        # the unreachable ceiling

ACCENT = "#B8860B"         # callouts and annotations

CLASS_COLOURS = {"selective": SELECTIVE, "no_effect_observed": NO_EFFECT,
                 "inconclusive_cytotox": CYTOTOX, "inconclusive_other": UNKNOWN}
MODEL_COLOURS = {"read_across": MODEL, "fingerprint_forest": MODEL_ALT,
                 "physchem_logistic": MODEL_WEAK, "prevalence": RANDOM}
MODEL_LABELS = {"read_across": "Read-across (analogues)", "fingerprint_forest": "Structural forest",
                "physchem_logistic": "Physicochemical", "prevalence": "Chance (control)"}
MODEL_DASH = {"read_across": (None, None), "fingerprint_forest": (5, 2),
              "physchem_logistic": (2, 2), "prevalence": (1, 2)}


def _pick_font():
    want = ["Source Sans 3", "Source Sans Pro", "Inter", "IBM Plex Sans", "Lato",
            "DejaVu Sans", "Liberation Sans"]
    have = {f.name for f in font_manager.fontManager.ttflist}
    return [w for w in want if w in have] + ["sans-serif"]


def apply():
    mpl.rcParams.update({
        "figure.facecolor": PAPER, "axes.facecolor": PAPER, "savefig.facecolor": PAPER,
        "font.family": "sans-serif", "font.sans-serif": _pick_font(),
        "font.size": 10.5, "axes.titlesize": 12.5, "axes.labelsize": 10.5,
        "axes.titleweight": "bold", "axes.titlepad": 11,
        "axes.edgecolor": FAINT, "axes.labelcolor": INK, "text.color": INK,
        "axes.linewidth": 0.9, "axes.grid": True, "axes.axisbelow": True,
        "grid.color": GRID, "grid.linewidth": 0.8, "grid.alpha": 1.0,
        "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5, "xtick.direction": "out", "ytick.direction": "out",
        "legend.frameon": False, "legend.fontsize": 9.5, "legend.handlelength": 2.4,
        "lines.linewidth": 2.2, "lines.solid_capstyle": "round",
        "figure.dpi": 150, "savefig.dpi": 150, "savefig.bbox": "tight",
        "savefig.pad_inches": 0.28, "pdf.fonttype": 42, "svg.fonttype": "none",
    })


def despine(ax, keep=("left", "bottom")):
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(s in keep)
    ax.tick_params(length=3.5, width=0.9)


def caption(fig, text, y=-0.01):
    """A one-line source note, so a figure lifted out of the README still says where it came from."""
    fig.text(0.0, y, text, ha="left", va="top", fontsize=8.2, color=FAINT, wrap=True)


def label_panel(ax, letter, dx=-0.085, dy=1.045):
    ax.text(dx, dy, letter, transform=ax.transAxes, fontsize=12.5, fontweight="bold",
            color=INK, ha="left", va="bottom")


def save_gif(frames, path, duration_ms=90, loop=0, hold_last_ms=1400):
    """Write a list of PIL images as an animated GIF, holding the final frame so it can be read.

    GitHub autoplays README GIFs once they are in view and gives the reader no controls, so the
    last frame — the one carrying the conclusion — is held for over a second before the loop.
    """
    from PIL import Image
    assert frames, "no frames"
    durations = [duration_ms] * len(frames)
    durations[-1] = hold_last_ms
    frames = [f.convert("P", palette=Image.ADAPTIVE, colors=200) for f in frames]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations,
                   loop=loop, optimize=True, disposal=2)
    return path


def fig_to_pil(fig):
    from io import BytesIO

    from PIL import Image
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=110, facecolor=PAPER,
                bbox_inches="tight", pad_inches=0.28)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def ease(t):
    """Smooth-in-out easing on [0,1], so animated reveals do not jerk."""
    t = np.clip(t, 0.0, 1.0)
    return float(t * t * (3.0 - 2.0 * t))


def fixed_canvas(frames):
    """Pad every frame to the largest size so the GIF does not jitter between frames."""
    from PIL import Image
    w = max(f.width for f in frames)
    h = max(f.height for f in frames)
    out = []
    for f in frames:
        if f.size == (w, h):
            out.append(f)
            continue
        bg = Image.new("RGB", (w, h), PAPER)
        bg.paste(f, ((w - f.width) // 2, (h - f.height) // 2))
        out.append(bg)
    return out
