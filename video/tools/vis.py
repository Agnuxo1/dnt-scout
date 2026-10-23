"""Scene renderers for the DNT-Scout film. 1920x1080, 30 fps.

Two rules carried over from the earlier film in this series, because both are about honesty rather
than looks:

1. **Every scene declares what it is showing.** A chip in the top-right corner says whether the
   frame holds MEASURED data, a RESULT of the evaluation, an ILLUSTRATION that is schematic, or a
   LIVE APP capture of the real system. A viewer should never have to guess whether a curve is data
   or decoration.
2. **No number is typed into a frame by hand.** Everything on screen goes through `N()`, which
   reads it out of a results JSON and records what was shown, where it came from and where it
   appeared, into `video/numbers_onscreen.json`. If a result changes, the film is wrong until it is
   re-rendered, and the log says so.

The palette is Okabe-Ito on a dark ground, so the scenes stay readable for the common forms of
colour-vision deficiency and on a projector.
"""
from __future__ import annotations

import json
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

VIDEO = Path(__file__).resolve().parents[1]
ROOT = VIDEO.parent
RES = ROOT / "results"
AUD = RES / "audit"
FIGS = RES / "figs"
CAP = VIDEO / "captures"

W, H, FPS = 1920, 1080, 30
BG, BG2 = (11, 18, 32), (22, 33, 54)
INK, MUTED, FAINT = (236, 240, 246), (150, 164, 184), (104, 118, 138)

# Okabe-Ito, colour-vision safe
OI = {"blue": (0, 114, 178), "sky": (86, 180, 233), "green": (0, 158, 115),
      "amber": (230, 159, 0), "vermillion": (213, 94, 0), "purple": (204, 121, 167),
      "grey": (140, 150, 160)}
SELECTIVE, NO_EFFECT, CYTOTOX = OI["vermillion"], OI["blue"], OI["purple"]
MODEL, RANDOM = OI["green"], OI["grey"]

TAGS = {"MEASURED": OI["green"], "RESULTS": OI["amber"], "ILLUSTRATION": OI["purple"],
        "LIVE APP": OI["sky"], "PREDICTED": OI["blue"]}

#: kept clear of the burned-in subtitles at the foot of the frame
CONTENT = (70, 136, 1850, 880)


def _font_path(bold: bool) -> str:
    import matplotlib
    d = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    return str(d / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"))


@lru_cache(maxsize=None)
def font(size: int, bold: bool = False):
    return ImageFont.truetype(_font_path(bold), size)


# ------------------------------------------------------------------ numbers, never typed by hand
_NUM_LOG: dict[str, dict] = {}


@lru_cache(maxsize=None)
def J(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _dig(obj, path: str):
    for part in path.split("."):
        obj = obj[int(part)] if isinstance(obj, list) else obj[part]
    return obj


def N(rel: str, path: str, fmt: str = "", where: str = "") -> str:
    """Read a number out of a results file, format it, and record that it was shown."""
    raw = _dig(J(rel), path)
    s = format(raw, fmt) if fmt else str(raw)
    _NUM_LOG[f"{rel}:{path}:{fmt}"] = {"shown": s, "source": rel, "path": path, "raw": raw,
                                       "where": where}
    return s


def quoted(value: str, source: str, where: str = "") -> str:
    """A figure quoted from the independent audit report rather than from our own results.

    Kept in the same log, flagged, so the distinction survives into `numbers_onscreen.json`.
    """
    _NUM_LOG[f"quoted:{source}:{value}:{where}"] = {"shown": value, "source": source,
                                                    "quoted_not_recomputed": True, "where": where}
    return value


def dump_numbers(path: Path):
    path.write_text(json.dumps(_NUM_LOG, indent=1), encoding="utf-8")


# ------------------------------------------------------------------------------- drawing helpers
def ease(u: float) -> float:
    u = min(max(u, 0.0), 1.0)
    return u * u * (3.0 - 2.0 * u)


def ramp(t: float, t0: float, dur: float = 0.55) -> float:
    return ease((t - t0) / dur) if dur > 0 else float(t >= t0)


def canvas() -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    for y in range(0, H, 4):                       # a very slight vertical lift, not a gradient show
        u = y / H
        d.rectangle([0, y, W, y + 4], fill=tuple(int(a + (b - a) * u * 0.55)
                                                 for a, b in zip(BG, BG2)))
    return img


def text(d, xy, s, size=32, bold=False, fill=INK, anchor="la", alpha=1.0, spacing=10):
    if alpha <= 0.02:
        return
    c = tuple(int(BG[i] + (fill[i] - BG[i]) * min(alpha, 1.0)) for i in range(3))
    d.multiline_text(xy, s, font=font(size, bold), fill=c, anchor=anchor, spacing=spacing)


def text_w(s, size, bold=False) -> int:
    return int(font(size, bold).getlength(s))


def rrect(img, box, r=18, fill=None, outline=None, width=2, alpha=1.0):
    if alpha <= 0.02:
        return
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * min(alpha, 1.0))
    d.rounded_rectangle(box, radius=r, fill=(fill + (a,)) if fill else None,
                        outline=(outline + (a,)) if outline else None, width=width)
    img.paste(Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB"), (0, 0))


def chip(img, x, y, label, colour, alpha=1.0, size=22):
    """The tag that tells the viewer what kind of thing the frame is showing."""
    pad, h = 16, 38
    w = text_w(label, size, True) + 2 * pad
    rrect(img, [x - w, y, x, y + h], r=h // 2, fill=tuple(int(c * 0.30) for c in colour),
          outline=colour, width=2, alpha=alpha)
    text(ImageDraw.Draw(img), (x - w / 2, y + h / 2), label, size, True, colour, "mm", alpha)
    return w


def header(img, title: str, tag: str, t: float, sub: str = "", t0: float = 0.0):
    d = ImageDraw.Draw(img)
    a = ramp(t, t0, 0.5)
    text(d, (70, 58), title, 46, True, INK, "la", a)
    if sub:
        text(d, (70, 112), sub, 25, False, MUTED, "la", ramp(t, t0 + 0.12, 0.5))
    chip(img, 1850, 62, tag, TAGS[tag], ramp(t, t0 + 0.2, 0.5))
    d.line([70, 100 if not sub else 100, 70 + int(640 * a), 100], fill=FAINT, width=1)


def fade(img: Image.Image, t: float, dur: float, fin=0.4, fout=0.4) -> Image.Image:
    u = 1.0
    if t < fin:
        u = ease(t / fin)
    elif t > dur - fout:
        u = ease((dur - t) / fout)
    if u >= 0.999:
        return img
    return Image.blend(Image.new("RGB", img.size, BG), img, u)


def plot(figsize, draw_fn, dpi=100, transparent=True) -> Image.Image:
    """Render a matplotlib figure onto the dark ground and return it as a PIL image."""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    fig = plt.figure(figsize=figsize, dpi=dpi)
    fig.patch.set_alpha(0.0 if transparent else 1.0)
    draw_fn(fig)
    from io import BytesIO
    buf = BytesIO()
    fig.savefig(buf, format="png", transparent=transparent, dpi=dpi,
                bbox_inches=None, facecolor="none")
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGBA")


def paste(img, sprite, xy, alpha=1.0):
    if alpha <= 0.02:
        return
    s = sprite
    if alpha < 0.999:
        s = sprite.copy()
        al = s.getchannel("A").point(lambda v: int(v * alpha))
        s.putalpha(al)
    img.paste(s, (int(xy[0]), int(xy[1])), s)


def mpl_style():
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    rgb = lambda c: tuple(v / 255 for v in c)  # noqa: E731
    plt.rcParams.update({
        "axes.facecolor": "none", "figure.facecolor": "none", "savefig.facecolor": "none",
        "text.color": rgb(INK), "axes.labelcolor": rgb(MUTED), "axes.edgecolor": rgb(FAINT),
        "xtick.color": rgb(MUTED), "ytick.color": rgb(MUTED), "grid.color": (1, 1, 1, 0.08),
        "font.size": 15, "axes.labelsize": 16, "xtick.labelsize": 14, "ytick.labelsize": 14,
        "axes.linewidth": 1.2, "lines.linewidth": 3.0, "legend.frameon": False,
        "legend.labelcolor": rgb(INK), "legend.fontsize": 15,
    })


def despine(ax, keep=("left", "bottom")):
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(s in keep)


# ================================================================================ S1 · the problem
def scene_s1(t: float, dur: float) -> Image.Image:
    """Scale mismatch: a commerce-sized field of chemicals, a handful of them tested."""
    img = canvas()
    header(img, "Which chemical goes on the plate first?", "ILLUSTRATION",
           t, "developmental neurotoxicity · the testing gap")
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(7)
    n = 1400
    xs = rng.uniform(110, 1180, n)
    ys = rng.uniform(210, 840, n)
    a_field = ramp(t, 0.6, 1.4)
    k = int(a_field * n)
    for i in range(k):
        v = int(60 + 40 * rng.random())
        d.ellipse([xs[i] - 3, ys[i] - 3, xs[i] + 3, ys[i] + 3], fill=(v, v + 8, v + 20))
    a_tested = ramp(t, 2.4, 1.2)
    if a_tested > 0.02:
        for i in range(0, int(a_tested * 26)):
            x, y = xs[i * 7 % n], ys[i * 7 % n]
            col = tuple(int(c * a_tested) for c in OI["green"])
            d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=col)
    text(d, (110, 832), "every dot: a chemical in commerce", 24, False, MUTED, "la", a_field)
    text(d, (110, 868), "green: tested on the developing nervous system", 24, False,
         OI["green"], "la", a_tested)

    a_q = ramp(t, 4.6, 0.9)
    if a_q > 0.02:
        rrect(img, [1240, 240, 1850, 600], 20, fill=(18, 28, 46), outline=FAINT, width=2,
              alpha=a_q)
        text(d, (1270, 286), "The microelectrode array", 30, True, INK, "la", a_q)
        for i, line in enumerate(["cortical neurons grown on a chip",
                                  "a firing network forms over days",
                                  "faster than an animal study —",
                                  "still days of culture per compound"]):
            text(d, (1270, 346 + i * 44), line, 25, False, MUTED, "la",
                 ramp(t, 4.9 + i * 0.22, 0.6))
    a_punch = ramp(t, 7.2, 0.9)
    if a_punch > 0.02:
        text(d, (1545, 690), "so the real question is\nnot \"is it neurotoxic\"",
             28, False, MUTED, "mm", a_punch, spacing=14)
        text(d, (1545, 790), "which ones first?", 40, True, OI["amber"], "mm",
             ramp(t, 8.1, 0.8))
    return fade(img, t, dur)


# ========================================================== S2 · what counts as a hit
def scene_s2(t: float, dur: float) -> Image.Image:
    img = canvas()
    header(img, "A chemical that kills the culture flattens everything", "MEASURED",
           t, "so the outcome is defined against viability")
    d = ImageDraw.Draw(img)

    rows = [(372, "Selective effect", SELECTIVE, 0.5, 9.0, "counts as a positive"),
            (576, "Only at lethal doses", CYTOTOX, 1.4, 2.0, "inconclusive — published as such"),
            (780, "No effect in range", NO_EFFECT, None, None, "counts as a negative")]
    x0, x1 = 150, 1180

    def xpos(c):
        return x0 + (math.log10(c) - math.log10(0.05)) / (math.log10(400) - math.log10(0.05)) * (x1 - x0)

    for i, (y, label, col, net, viab, note) in enumerate(rows):
        a = ramp(t, 0.5 + i * 0.75, 0.7)
        if a <= 0.02:
            continue
        text(d, (150, y - 86), label, 30, True, col, "la", a)
        text(d, (150, y - 50), note, 22, False, MUTED, "la", a)
        d.line([x0, y, x1, y], fill=tuple(int(c * a) for c in (46, 58, 78)), width=12)
        if net is not None:
            a2 = ramp(t, 0.9 + i * 0.75, 0.6)
            xn, xv = xpos(net), xpos(viab)
            d.ellipse([xn - 13, y - 13, xn + 13, y + 13], fill=tuple(int(c * a2) for c in col))
            d.rectangle([xv - 10, y - 10, xv + 10, y + 10],
                        fill=tuple(int(c * a2) for c in INK))
            # pushed apart, one left one right, so the two labels cannot collide however close
            # the two concentrations happen to be
            text(d, (xn - 16, y + 30), "network", 20, False, col, "ra", a2)
            text(d, (xv + 16, y + 30), "viability", 20, False, INK, "la", a2)
            a3 = ramp(t, 1.3 + i * 0.75, 0.6)
            if a3 > 0.02:
                d.line([xn, y - 30, xv, y - 30], fill=tuple(int(c * a3) for c in col), width=3)
                text(d, (max(xv + 24, xn + 70), y - 30), "%.0f x" % (viab / net), 26, True, col,
                     "lm", a3)
        else:
            text(d, ((x0 + x1) / 2, y + 34), "nothing responded below the top dose",
                 21, False, FAINT, "ma", a)
    text(d, (x0, 862), "concentration  →", 24, False, MUTED, "la", ramp(t, 1.0))

    a_rule = ramp(t, 4.0, 0.8)
    rrect(img, [1240, 240, 1850, 430], 18, fill=(18, 28, 46), outline=OI["amber"], width=2,
          alpha=a_rule)
    text(d, (1270, 274), "The rule", 27, True, OI["amber"], "la", a_rule)
    text(d, (1270, 322), "a network effect counts only when\nit is at least three-fold more potent\n"
                         "than the dose that kills the cells",
         24, False, INK, "la", a_rule, spacing=12)

    a_counts = ramp(t, 5.4, 0.9)
    if a_counts > 0.02:
        counts = [(N("results/audit/audit_01_data.json", "selective_total", "", "S2 counts"),
                   "selective", SELECTIVE),
                  (str(J("results/evaluation.json")["n"] - int(J("results/evaluation.json")["n_positive"])),
                   "no effect observed", NO_EFFECT),
                  (N("results/audit/audit_01_data.json", "inconclusive_cytotox", "", "S2 counts"),
                   "inconclusive", CYTOTOX)]
        for i, (v, lab, col) in enumerate(counts):
            y = 500 + i * 110
            a = ramp(t, 5.4 + i * 0.3, 0.7)
            text(d, (1300, y), v, 54, True, col, "la", a)
            text(d, (1400, y + 18), lab, 26, False, MUTED, "la", a)
        text(d, (1300, 826), "the inconclusive ones are published,\nnever counted as negatives",
             22, False, FAINT, "la", ramp(t, 6.6, 0.8), spacing=10)
    return fade(img, t, dur)


# ============================================================ S3 · how it works
def scene_s3(t: float, dur: float) -> Image.Image:
    img = canvas()
    header(img, "From a structure to a decision", "ILLUSTRATION",
           t, "standardise · fingerprint · find the measured relatives · state the confidence")
    d = ImageDraw.Draw(img)

    # the fingerprint, lighting up
    a_fp = ramp(t, 0.8, 1.2)
    bx, by, cell = 150, 300, 26
    rng = np.random.default_rng(11)
    bits = rng.random((12, 24)) < 0.17
    for r in range(12):
        for c in range(24):
            x, y = bx + c * cell, by + r * cell
            lit = bits[r, c] and (c / 24) < a_fp
            col = OI["sky"] if lit else (34, 46, 66)
            d.rounded_rectangle([x, y, x + cell - 5, y + cell - 5], radius=4, fill=col)
    text(d, (bx, by - 44), "Morgan fingerprint · 2048 bits", 26, True, OI["sky"], "la", a_fp)
    text(d, (bx, by + 12 * cell + 14), "a structure, written as the substructures it contains",
         22, False, MUTED, "la", a_fp)

    # the measured relatives
    a_an = ramp(t, 2.6, 1.0)
    if a_an > 0.02:
        text(d, (780, by - 44), "nearest measured relatives", 26, True, OI["green"], "la", a_an)
        rel = [("T = 0.37", "selective", SELECTIVE), ("T = 0.33", "selective", SELECTIVE),
               ("T = 0.25", "selective", SELECTIVE)]
        for i, (sim, out, col) in enumerate(rel):
            a = ramp(t, 2.8 + i * 0.35, 0.6)
            y = by + i * 92
            rrect(img, [780, y, 1230, y + 72], 14, fill=(20, 30, 50), outline=col, width=2,
                  alpha=a)
            text(d, (806, y + 36), sim, 26, True, INK, "lm", a)
            text(d, (1204, y + 36), out, 24, False, col, "rm", a)
        text(d, (780, by + 300), "their outcomes, weighted by similarity", 22, False, MUTED,
             "la", ramp(t, 3.9, 0.7))

    # the verdict
    a_v = ramp(t, 4.6, 1.0)
    if a_v > 0.02:
        rrect(img, [1330, 280, 1850, 640], 20, fill=(18, 28, 46), outline=FAINT, width=2,
              alpha=a_v)
        text(d, (1590, 330), "score", 24, False, MUTED, "mm", a_v)
        text(d, (1590, 392), "1.00", 68, True, MODEL, "mm", ramp(t, 4.9, 0.7))
        text(d, (1590, 476), "90% conformal set", 22, False, MUTED, "mm", ramp(t, 5.3, 0.7))
        text(d, (1590, 524), "{ selective }", 34, True, SELECTIVE, "mm", ramp(t, 5.5, 0.7))
        text(d, (1590, 586), "inside the applicability domain", 20, False, OI["green"], "mm",
             ramp(t, 5.8, 0.7))
    a_ab = ramp(t, 6.6, 0.9)
    if a_ab > 0.02:
        text(d, (1590, 724), "and when the nearest relative\nis too distant to say anything —",
             24, False, MUTED, "mm", a_ab, spacing=12)
        text(d, (1590, 816), "it says nothing", 34, True, OI["amber"], "mm", ramp(t, 7.4, 0.7))
    return fade(img, t, dur)


# ================================================================ S4 · the result
@lru_cache(maxsize=None)
def _curve():
    import csv
    p = RES / "out_of_fold_predictions.csv"
    rows = list(csv.DictReader(p.open(encoding="utf-8")))
    key = "rank_read_across" if "rank_read_across" in rows[0] else "score_read_across"
    pairs = sorted(((float(r[key]), int(float(r["y"]))) for r in rows), key=lambda z: -z[0])
    return np.concatenate([[0], np.cumsum([y for _s, y in pairs])])


def scene_s4(t: float, dur: float) -> Image.Image:
    img = canvas()
    header(img, "How many laboratory runs to find the actives?", "RESULTS",
           t, "102 chemicals, scaffold-held-out · retrospective, on a cohort enriched with suspects")
    d = ImageDraw.Draw(img)
    cum = _curve()
    n, npos = len(cum) - 1, int(cum[-1])
    a_model = int(np.argmax(cum >= math.ceil(0.5 * npos)))
    rnd = float(N("results/audit/audit_02_validity.json", "G_random_baseline.0.mean_assays",
                  ".1f", "S4 random mean"))
    reveal = ease(min(1.0, max(0.0, (t - 0.8) / 4.2)))

    mpl_style()

    def draw(fig):
        ax = fig.add_axes([0.085, 0.14, 0.9, 0.82])
        x = np.arange(n + 1)
        ax.plot(x, np.clip(x, 0, npos), color=(0.45, 0.5, 0.56), lw=1.6)
        ax.plot(x, npos / n * x, color=tuple(v / 255 for v in RANDOM), lw=2.2, ls=(0, (5, 4)))
        k = max(1, int(reveal * n))
        ax.plot(x[:k + 1], cum[:k + 1], color=tuple(v / 255 for v in MODEL), lw=4.0)
        ax.set_xlim(0, n)
        ax.set_ylim(0, npos + 2)
        ax.set_xlabel("microelectrode-array runs, in the order the model recommends")
        ax.set_ylabel("actives found")
        ax.grid(axis="y")
        despine(ax)

    paste(img, plot((13.2, 6.6), draw), (120, 210))

    a_call = ramp(t, 5.2, 0.9)
    if a_call > 0.02:
        for i, (big, small, col) in enumerate(
                [(str(a_model), "assays, ranked", MODEL),
                 ("%.1f" % rnd, "assays, at random", RANDOM)]):
            x = 1430 + 0
            y = 250 + i * 150
            text(d, (x, y), big, 72, True, col, "la", ramp(t, 5.2 + i * 0.4, 0.7))
            text(d, (x, y + 92), small, 24, False, MUTED, "la", ramp(t, 5.3 + i * 0.4, 0.7))
    a_roc = ramp(t, 6.6, 0.9)
    if a_roc > 0.02:
        rrect(img, [1420, 570, 1850, 790], 16, fill=(18, 28, 46), outline=OI["amber"], width=2,
              alpha=a_roc)
        text(d, (1450, 604), "area under the curve", 22, False, MUTED, "la", a_roc)
        text(d, (1450, 646), N("results/evaluation.json", "models.read_across.roc_auc", ".3f",
                               "S4 ROC"), 46, True, OI["amber"], "la", a_roc)
        text(d, (1450, 712), "%s median over 20 other splits"
             % N("results/audit/audit_02_validity.json",
                 "B_repeated_cv_summary.2.roc_rank_median", ".3f", "S4 median of 20"),
             21, False, MUTED, "la",
             ramp(t, 7.1, 0.7))
    text(d, (120, 866), "retrospective evaluation · 33–34 assays typical across 200 independent splits",
         23, False, FAINT, "la", ramp(t, 7.6, 0.8))
    return fade(img, t, dur)


# ============================================================ S5 · is it real
def scene_s5(t: float, dur: float) -> Image.Image:
    img = canvas()
    header(img, "Then somebody else tried to break it", "RESULTS",
           t, "an independent agent that never saw our code")
    d = ImageDraw.Draw(img)

    checks = [(quoted("185 / 185", "independent audit, 2026-10-23", "S5 reproduction"), "numeric fields reproduced"),
              (quoted("5.55 x 10⁻¹⁷", "independent audit, 2026-10-23", "S5 rebuild"),
               "agreement of a from-scratch rebuild"),
              (quoted("136 / 136", "independent audit, 2026-10-23", "S5 labels"),
               "labels rebuilt from the agency spreadsheet")]
    for i, (big, small) in enumerate(checks):
        a = ramp(t, 0.6 + i * 0.5, 0.7)
        y = 230 + i * 128
        text(d, (120, y), big, 46, True, OI["sky"], "la", a)
        text(d, (120, y + 62), small, 23, False, MUTED, "la", a)

    a_h = ramp(t, 2.8, 1.0)
    if a_h > 0.02:
        import csv
        vals = np.array([float(r["roc_rank"]) for r in
                         csv.DictReader((AUD / "permutation_null.csv").open(encoding="utf-8"))])
        obs = float(N("results/evaluation.json", "models.read_across.roc_auc", ".3f", "S5 observed"))
        grow = ease(min(1.0, (t - 2.8) / 2.2))
        mpl_style()

        def draw(fig):
            ax = fig.add_axes([0.10, 0.19, 0.87, 0.75])
            ax.hist(vals, bins=36, color=(0.42, 0.47, 0.54),
                    weights=np.full(len(vals), grow))
            ax.axvline(obs, color=tuple(v / 255 for v in OI["amber"]), lw=3.4)
            ax.set_xlim(0.28, 0.88)
            ax.set_xlabel("ROC AUC under 999 label permutations, everything refitted each time")
            ax.set_ylabel("permutations")
            ax.grid(axis="y")
            despine(ax)

        paste(img, plot((11.6, 4.5), draw), (640, 352), a_h)
        a_p = ramp(t, 5.4, 0.9)
        if a_p > 0.02:
            text(d, (1455, 300), "observed", 22, False, OI["amber"], "ma", a_p)
            text(d, (1455, 334), N("results/evaluation.json", "models.read_across.roc_auc",
                                   ".3f", "S5 observed label"), 40, True, OI["amber"], "ma", a_p)
            text(d, (700, 790), "the best of 999 shuffles reached %s" %
                 N("results/audit/permutation_null.json", "roc_rank.null_max", ".3f", "S5 null max"),
                 24, False, MUTED, "la", a_p)
    a_pv = ramp(t, 6.6, 0.9)
    if a_pv > 0.02:
        text(d, (120, 700), "not one of them\nreached our result", 30, False, INK, "la", a_pv,
             spacing=14)
        text(d, (120, 812), "p = " + N("results/audit/permutation_null.json", "roc_rank.p_value",
                                       ".3f", "S5 p"), 62, True, OI["amber"], "la",
             ramp(t, 7.2, 0.8))
    return fade(img, t, dur)


# ============================================================ S6 · SciencePal
def _shots():
    return sorted(CAP.glob("sciencepal_*.png"))


def scene_s6(t: float, dur: float) -> Image.Image:
    img = canvas()
    header(img, "The decision runs inside SciencePal", "LIVE APP",
           t, "20 chemicals withheld from fitting, selection and calibration — and our answer withheld too")
    d = ImageDraw.Draw(img)
    shots = _shots()
    if shots:
        idx = min(len(shots) - 1, int(max(0.0, (t - 0.5)) / max(0.1, (dur - 1.2) / len(shots))))
        # cropped at native resolution rather than scaled down: the point of a LIVE APP frame is
        # that the viewer can read the commands the agent actually ran
        im = Image.open(shots[idx]).convert("RGBA")
        bw, bh = 1180, 620
        u = ease(min(1.0, max(0.0, (t - 0.5) / max(dur - 1.5, 0.1))))
        x = int((im.width - bw) * 0.02)
        y = int((im.height - bh) * (0.08 + 0.72 * u))        # a slow drift down the transcript
        im = im.crop((x, max(0, y), x + bw, max(0, y) + bh))
        rrect(img, [116, 206, 124 + bw, 214 + im.height], 14, fill=(8, 12, 22),
              outline=FAINT, width=2, alpha=ramp(t, 0.3))
        paste(img, im, (120, 210), ramp(t, 0.4, 0.6))
    else:
        text(d, (720, 480), "[ SciencePal capture ]", 30, False, FAINT, "mm", ramp(t, 0.4))

    ABL = "results/sciencepal/ABLATION.md"
    items = [(quoted("19 / 20", ABL, "S6 resolved"), "structures resolved", OI["green"]),
             (quoted("1", ABL, "S6 decisive"), "confident call — the only one", OI["amber"]),
             (quoted("6", ABL, "S6 refusals"), "refused, in three distinct categories",
              OI["purple"])]
    for i, (big, small, col) in enumerate(items):
        a = ramp(t, 2.0 + i * 0.5, 0.7)
        y = 250 + i * 150
        text(d, (1400, y), big, 52, True, col, "la", a)
        text(d, (1400, y + 68), small, 22, False, MUTED, "la", a)

    a_story = ramp(t, 4.6, 1.0)
    if a_story > 0.02:
        rrect(img, [120, 726, 1850, 866], 16, fill=(18, 28, 46), outline=OI["sky"], width=2,
              alpha=a_story)
        text(d, (150, 756), "Its chemical database was blocked. It said so, found another route, "
                            "and recovered a salt", 25, False, INK, "la", a_story)
        text(d, (150, 800), "our own pipeline had thrown away — the only one of the twenty it "
                            "could call with confidence.", 25, False, INK, "la",
             ramp(t, 5.2, 0.8))
    return fade(img, t, dur)


# ============================================================ S7 · what it is not, and next
def scene_s7(t: float, dur: float) -> Image.Image:
    img = canvas()
    header(img, "What it tells you, and what it does not", "ILLUSTRATION", t)
    d = ImageDraw.Draw(img)
    a1 = ramp(t, 0.5, 0.9)
    text(d, (960, 300), "This does not tell you a chemical is safe.", 40, True, INK, "mm", a1)
    text(d, (960, 364), "a negative result in a dish does not exclude harm in development",
         26, False, MUTED, "mm", ramp(t, 0.9, 0.8))
    a2 = ramp(t, 2.4, 0.9)
    text(d, (960, 500), "It tells you which plate to run on Monday.", 40, True, OI["amber"],
         "mm", a2)

    a3 = ramp(t, 4.0, 0.9)
    if a3 > 0.02:
        names = ["Doxylamine", "Atorvastatin", "Mifepristone", "Haloperidol", "Trichlorfon"]
        for i, nm in enumerate(names):
            a = ramp(t, 4.0 + i * 0.22, 0.6)
            x = 360 + i * 250
            rrect(img, [x - 108, 596, x + 108, 668], 14, fill=(20, 30, 50),
                  outline=SELECTIVE, width=2, alpha=a)
            text(d, (x, 632), nm, 23, True, SELECTIVE, "mm", a)
        text(d, (960, 706), "the five it chose are a prediction — one experiment would settle them",
             25, False, MUTED, "mm", ramp(t, 5.4, 0.8))

    a4 = ramp(t, 6.4, 0.9)
    if a4 > 0.02:
        d.line([560, 764, 1360, 764], fill=FAINT, width=1)
        text(d, (960, 798), "github.com/Agnuxo1/dnt-scout", 30, True, INK, "mm", a4)
        text(d, (960, 846), "data, code and every number in this film are public and reproducible",
             22, False, MUTED, "mm", ramp(t, 6.8, 0.8))
    return fade(img, t, dur, fout=0.9)


SCENES = [("S1", scene_s1, 35.0), ("S2", scene_s2, 30.0), ("S3", scene_s3, 30.0),
          ("S4", scene_s4, 35.0), ("S5", scene_s5, 35.0), ("S6", scene_s6, 30.0),
          ("S7", scene_s7, 20.0)]
