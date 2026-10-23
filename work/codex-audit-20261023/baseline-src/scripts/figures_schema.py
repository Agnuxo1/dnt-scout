"""Explanatory figures: what the tool does, and what the label means.

Two figures that carry no results, only definitions. They exist because both things are routinely
misread: a triage tool is mistaken for a safety verdict, and "neuroactive" is mistaken for
"selectively neuroactive".

Layout rule used throughout: nothing is positioned by eye. Every block of text either owns an axes
of its own in the grid, or is anchored to a data point with an offset in *points* and pushed away
from its neighbour, so two labels cannot collide however close their data values are.

    python scripts/figures_schema.py            # writes results/figs/01, 02
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import gridspec
from matplotlib import pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")

import figstyle as S  # noqa: E402

S.apply()
FIGS = Path("results/figs")
FIGS.mkdir(parents=True, exist_ok=True)


def header(fig, title, subtitle, x=0.0, y=1.0, fs=14, sub_fs=9.6):
    """A title block that owns its own space above the grid, so no axes title can run into it."""
    fig.text(x, y, title, fontsize=fs, fontweight="bold", color=S.INK, va="top", ha="left")
    fig.text(x, y - 0.052 * (fs / 14), subtitle, fontsize=sub_fs, color=S.MUTED, va="top",
             ha="left")


def notebox(ax, text, face=S.CANVAS, edge=S.GRID, fs=8.7):
    """A note that occupies a cell of the grid rather than floating over a plot."""
    ax.axis("off")
    ax.grid(False)
    ax.text(0.0, 1.0, text, transform=ax.transAxes, fontsize=fs, color=S.INK, va="top",
            ha="left", linespacing=1.5,
            bbox=dict(boxstyle="round,pad=0.6", facecolor=face, edgecolor=edge))


# =========================================================== 1. the pipeline, animated
STEPS = [
    ("1 · Structure", ["SMILES resolved from PubChem", "standardised, salts stripped",
                       "mixtures flagged, never modelled"], S.INK),
    ("2 · Representation", ["Morgan fingerprint, 2048 bits", "MACCS keys + 10 descriptors",
                            "no test chemistry in training"], S.MODEL_ALT),
    ("3 · Measured analogues", ["Tanimoto neighbours among the", "102 chemicals with an MEA",
                                "outcome · similarity-weighted"], S.MODEL),
    ("4 · Calibrated decision", ["conformal prediction set, 90%", "applicability domain checked",
                                 "abstains when it cannot tell"], S.SELECTIVE),
]
VERDICTS = [("Run the MEA assay", S.SELECTIVE), ("Deprioritise", S.NO_EFFECT),
            ("Cannot decide — abstain", S.UNKNOWN)]

BOX_Y, BOX_H, CHIP_Y, CHIP_H = 0.425, 0.475, 0.065, 0.175


def _box(ax, x, y, w, h, title, lines, colour, alpha):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.010,rounding_size=0.030",
                                facecolor=S.CANVAS, edgecolor=colour, linewidth=1.5,
                                alpha=alpha, zorder=3))
    ax.text(x + w / 2, y + h - 0.072, title, ha="center", va="top", fontsize=10.5,
            fontweight="bold", color=colour, alpha=alpha, zorder=4)
    for i, t in enumerate(lines):
        ax.text(x + w / 2, y + h - 0.168 - i * 0.090, t, ha="center", va="top", fontsize=8.5,
                color=S.MUTED, alpha=alpha, zorder=4)


def frame_pipeline(progress: float):
    fig = plt.figure(figsize=(11.8, 3.45))
    ax = fig.add_axes([0.0, 0.0, 1.0, 0.845])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.grid(False)
    header(fig, "DNT-Scout · from a chemical structure to a laboratory decision",
           "Which untested compounds deserve a microelectrode-array run — and when is the "
           "structural evidence too thin to say?", x=0.012, y=0.985)

    w, gap = 0.2105, 0.0420
    for i, (title, lines, colour) in enumerate(STEPS):
        x = 0.012 + i * (w + gap)
        a = S.ease((progress * len(STEPS) * 1.25) - i)
        if a <= 0.015:
            continue
        if i:
            ax.add_patch(FancyArrowPatch((x - gap + 0.005, BOX_Y + BOX_H / 2),
                                         (x - 0.007, BOX_Y + BOX_H / 2), arrowstyle="-|>",
                                         mutation_scale=14, color=S.FAINT, linewidth=1.6,
                                         alpha=a, zorder=2, shrinkA=0, shrinkB=0))
        _box(ax, x, BOX_Y, w, BOX_H, title, lines, colour, a)

    a_v = S.ease(progress * 3.8 - 2.8)
    if a_v > 0.015:
        ax.text(0.012, CHIP_Y + CHIP_H / 2, "Returns", fontsize=9.2, color=S.FAINT,
                va="center", ha="left", alpha=a_v)
        for j, (txt, col) in enumerate(VERDICTS):
            x0 = 0.100 + j * 0.3035
            ax.add_patch(FancyBboxPatch((x0, CHIP_Y), 0.277, CHIP_H,
                                        boxstyle="round,pad=0.006,rounding_size=0.045",
                                        facecolor=col, edgecolor="none", alpha=0.13 * a_v,
                                        zorder=3))
            ax.text(x0 + 0.1385, CHIP_Y + CHIP_H / 2, txt, ha="center", va="center",
                    fontsize=10, fontweight="bold", color=col, alpha=a_v, zorder=4)
        ax.text(0.988, CHIP_Y - 0.055, "one of three outcomes — never a safety verdict",
                ha="right", va="top", fontsize=8.4, color=S.FAINT, alpha=a_v)
    return fig


def make_pipeline_gif():
    frames = []
    for p in np.linspace(0.0, 1.0, 34):
        f = frame_pipeline(p)
        frames.append(S.fig_to_pil(f))
        plt.close(f)
    S.save_gif(S.fixed_canvas(frames), FIGS / "01_pipeline.gif", duration_ms=78, hold_last_ms=2400)
    f = frame_pipeline(1.0)
    f.savefig(FIGS / "01_pipeline.png")
    plt.close(f)
    print("wrote 01_pipeline.gif / .png")


# ================================================ 2. what "selective" means, and what it does not
CASES = [
    dict(net=0.5, viab=9.0, col=S.SELECTIVE,
         title="Selective effect on network formation",
         sub="the network responds far below the concentration that kills the culture",
         tag="modelled as a positive"),
    dict(net=1.4, viab=2.0, col=S.CYTOTOX,
         title="Network effect only at cytotoxic concentrations",
         sub="the network falls as the culture dies — this is not neuroactivity",
         tag="inconclusive · reported, never counted as a negative"),
    dict(net=None, viab=None, col=S.NO_EFFECT,
         title="No effect observed in the tested range",
         sub="no network parameter gave a concentration-response below the top dose",
         tag="modelled as a negative"),
]
XLO, XHI = 0.05, 400.0


def _case_axes(ax, c, show_x):
    ax.set_xscale("log")
    ax.set_xlim(XLO, XHI)
    ax.set_ylim(-1.0, 1.0)
    ax.set_yticks([])
    ax.grid(axis="x")
    S.despine(ax, keep=("bottom",) if show_x else ())
    if show_x:
        ax.set_xlabel("concentration tested   (µM, log scale)")
    else:
        ax.set_xticklabels([])
    ax.tick_params(axis="x", which="minor", length=0)
    if not show_x:
        ax.tick_params(axis="x", which="major", length=0)
    ax.set_title(c["title"], loc="left", color=c["col"], fontsize=10.4, pad=17)
    ax.text(0.0, 1.03, c["sub"], transform=ax.transAxes, fontsize=8.4, color=S.MUTED,
            va="bottom", ha="left")

    ax.plot([XLO * 1.08, XHI * 0.96], [0, 0], color=S.GRID, lw=9, solid_capstyle="butt", zorder=1)
    if c["net"] is None:
        ax.annotate("no concentration-response fitted for any of the 17 parameters",
                    xy=(np.sqrt(XLO * XHI), 0), xytext=(0, 17), textcoords="offset points",
                    ha="center", va="bottom", fontsize=8.0, color=S.FAINT)
    else:
        ax.plot([c["net"]], [0], marker="o", ms=11.5, color=c["col"], zorder=4,
                markeredgecolor=S.PAPER, markeredgewidth=1.8)
        ax.plot([c["viab"]], [0], marker="D", ms=9.5, color=S.INK, zorder=4,
                markeredgecolor=S.PAPER, markeredgewidth=1.8)
        # pushed apart in POINTS, so they cannot collide however close the two EC50s are
        ax.annotate("network EC50", xy=(c["net"], 0), xytext=(-9, -20),
                    textcoords="offset points", ha="right", va="top", fontsize=8.0, color=c["col"])
        ax.annotate("viability EC50", xy=(c["viab"], 0), xytext=(9, -20),
                    textcoords="offset points", ha="left", va="top", fontsize=8.0, color=S.INK)
        ax.annotate("", xy=(c["viab"], 0.30), xytext=(c["net"], 0.30),
                    arrowprops=dict(arrowstyle="<|-|>", color=c["col"], lw=1.4, shrinkA=0,
                                    shrinkB=0))
        ax.text(np.sqrt(c["net"] * c["viab"]), 0.40, "%.0f×" % (c["viab"] / c["net"]),
                ha="center", va="bottom", fontsize=9.4, color=c["col"], fontweight="bold")
    ax.text(0.998, 0.97, c["tag"], transform=ax.transAxes, ha="right", va="top",
            fontsize=8.1, color=c["col"], style="italic")


def make_endpoint_figure(df):
    fig = plt.figure(figsize=(13.6, 7.0))
    gs = gridspec.GridSpec(4, 2, width_ratios=[1.52, 1.0], height_ratios=[1, 1, 1, 0.62],
                           hspace=0.95, wspace=0.26, figure=fig,
                           left=0.055, right=0.985, top=0.845, bottom=0.145)
    header(fig, "The primary outcome is defined against viability",
           "a chemical that kills the culture flattens every electrophysiological parameter; "
           "calling that neuroactive is how a screen fools itself", x=0.012, y=0.985)

    for i, c in enumerate(CASES):
        _case_axes(fig.add_subplot(gs[i, 0]), c, show_x=(i == len(CASES) - 1))

    # -------------------------------------------- right: the four classes as measured
    ax2 = fig.add_subplot(gs[0:3, 1])
    counts = df.label.value_counts()
    order = ["selective", "no_effect_observed", "inconclusive_cytotox", "inconclusive_other"]
    names = ["Selective effect\nmodelled as 1", "No effect observed\nmodelled as 0",
             "Network effect only at\ncytotoxic doses · reported",
             "Structure not modellable\nreported"]
    vals = [int(counts.get(k, 0)) for k in order]
    yp = np.arange(len(order))[::-1]
    ax2.barh(yp, vals, color=[S.CLASS_COLOURS[k] for k in order], height=0.46, zorder=3)
    sel = df[df.label == "selective"]
    n_inf = int((~np.isfinite(sel.selectivity_fold.astype(float))).sum())
    ax2.barh([yp[0]], [n_inf], height=0.46, zorder=4, facecolor="none", edgecolor=S.PAPER,
             hatch="////", linewidth=0.0)
    for yy, v in zip(yp, vals):
        ax2.text(v + 1.5, yy, str(v), va="center", fontsize=11, fontweight="bold", color=S.INK)
    ax2.annotate("%d" % n_inf, xy=(n_inf / 2, yp[0]), ha="center", va="center", fontsize=9.6,
                 fontweight="bold", color=S.SELECTIVE, zorder=5,
                 bbox=dict(boxstyle="round,pad=0.25", facecolor=S.PAPER, edgecolor="none"))
    ax2.set_yticks(yp)
    ax2.set_yticklabels(names, fontsize=9)
    ax2.set_xlim(0, max(vals) * 1.24)
    ax2.set_xlabel("chemicals")
    ax2.set_title("136 chemicals, four classes", loc="left", pad=17)
    ax2.text(0.0, 1.02, "the inconclusive classes are published, never silently turned into "
             "negatives", transform=ax2.transAxes, fontsize=8.4, color=S.MUTED, va="bottom")
    S.despine(ax2, keep=("bottom",))
    ax2.grid(axis="x")

    notebox(fig.add_subplot(gs[3, 0]),
            "The ≥3× rule:  a network effect counts as selective only when it is at least\n"
            "three-fold more potent than the concentration that kills the culture.\n"
            "Sensitivity at 1× and 10× is published alongside it (70 · 49 · 35 positives).")
    notebox(fig.add_subplot(gs[3, 1]),
            "The hatched %d are positives for which no cytotoxicity EC50 was fitted\n"
            "at all, so the ≥3× rule was never the binding test. The other %d clear\n"
            "the threshold by a measured margin (median 6.5×)." % (n_inf, len(sel) - n_inf),
            face="#FDF7EA", edge="#E7D9B4")

    S.caption(fig, "Effect concentrations: Shafer et al. 2019, US EPA ScienceHub, DOI "
                   "10.23719/1503191 (public domain, US Government work).  A missing EC50 is the\n"
                   "source table's own convention for \"no concentration-response fitted inside "
                   "the tested range\" — not a missing measurement.", y=0.052)
    fig.savefig(FIGS / "02_endpoint.png", bbox_inches=None)
    plt.close(fig)
    print("wrote 02_endpoint.png")


if __name__ == "__main__":
    df = pd.read_parquet("data/processed/chemicals_labelled.parquet")
    make_pipeline_gif()
    make_endpoint_figure(df)
