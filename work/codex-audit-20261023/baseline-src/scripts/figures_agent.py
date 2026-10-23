"""The decision the agent actually makes, on chemicals nothing in this project has ever seen.

Twenty chemicals are drawn from the wider US EPA screen and withheld from every step — fitting,
selection, calibration. The agent must name the five to send to the microelectrode array, and say
plainly which ones it cannot judge. The figure animates that triage in the order it happens:
the candidates arrive, they sort by evidence, the ones outside the model's competence step aside,
and five are chosen.

Abstention is the part worth watching. Nine of the twenty are returned undecided, and that is the
designed behaviour, not a shortfall: four have no single resolvable structure (salts, mixtures, a
botanical extract) and five sit outside the applicability domain.

    python scripts/figures_agent.py            # writes results/figs/07_agent
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")

import figstyle as S  # noqa: E402
from figures_core import figure_note, panel_title  # noqa: E402

S.apply()
FIGS = Path("results/figs")
FIGS.mkdir(parents=True, exist_ok=True)

# how each decision reads on the page
STATE = {
    "assay": ("Run the assay", S.SELECTIVE),
    "uninformative": ("Evidence does not separate the two outcomes", S.MUTED),
    "deprioritise": ("Deprioritise — 90% set says \"no effect\"", S.NO_EFFECT),
    "undecidable": ("Cannot judge — outside competence", S.UNKNOWN),
}


def load():
    df = pd.read_csv("results/agent_package/scores.csv")
    df["score_f"] = pd.to_numeric(df.score, errors="coerce")
    df["state"] = np.where(df.recommended_for_assay.astype(str) == "True", "assay", df.decision)
    # undecidable chemicals have no score to rank on; park them at the foot of the list
    df["sort_key"] = df.score_f.fillna(-1.0)
    return df.sort_values("sort_key", ascending=False).reset_index(drop=True)


def frame(df, phase):
    """phase 0->1 sorts and reveals; 1->2 greys the abstentions; 2->3 lights the chosen five."""
    fig = plt.figure(figsize=(12.6, 7.4))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 0.56], wspace=0.06,
                          left=0.185, right=0.985, top=0.845, bottom=0.215)
    ax, ax2 = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])
    n = len(df)
    yp = np.arange(n)[::-1]

    reveal = S.ease(min(phase, 1.0))
    grey = S.ease(np.clip(phase - 1.0, 0, 1))
    light = S.ease(np.clip(phase - 2.0, 0, 1))

    for i, (yy, r) in enumerate(zip(yp, df.itertuples())):
        if i > reveal * n:
            continue
        chosen = r.state == "assay"
        abstain = r.state == "undecidable"
        base = STATE[r.state][1] if r.state != "assay" else S.SELECTIVE
        col = base
        alpha = 1.0
        if abstain:
            alpha = 1.0 - 0.55 * grey
        if chosen:
            alpha = 0.45 + 0.55 * light
        v = r.score_f if np.isfinite(r.score_f) else 0.0
        ax.barh([yy], [v], color=col, height=0.62, zorder=3, alpha=alpha)
        if np.isfinite(r.score_f) and v < 0.012:      # "no analogue voted positive" is a result
            ax.plot([0.004], [yy], marker="o", ms=6, markerfacecolor="none",
                    markeredgecolor=col, markeredgewidth=1.6, alpha=alpha, zorder=4)
        if chosen and light > 0.2:
            ax.add_patch(FancyBboxPatch((0.0, yy - 0.44), max(v, 0.02), 0.88,
                                        boxstyle="round,pad=0.004,rounding_size=0.03",
                                        facecolor="none", edgecolor=S.SELECTIVE,
                                        linewidth=1.8 * light, zorder=5))
            ax.text(v + 0.018, yy, "→ assay", va="center", fontsize=9, fontweight="bold",
                    color=S.SELECTIVE, alpha=light, zorder=6)
        if not np.isfinite(r.score_f):
            ax.text(0.012, yy, "no single resolvable structure", va="center", fontsize=8.2,
                    color=S.UNKNOWN, alpha=alpha, style="italic", zorder=6)
        elif not chosen:
            ax.text(v + 0.014, yy, "T=%.2f" % r.nearest_analogue_tanimoto, va="center",
                    fontsize=7.8, color=S.FAINT, alpha=alpha, zorder=6)

    ax.set_yticks(yp)
    ax.set_yticklabels([str(x)[:26] for x in df.name], fontsize=8.8)
    for tick, st in zip(ax.get_yticklabels(), df.state):
        tick.set_color(S.INK if st == "assay" else S.MUTED)
        if st == "assay":
            tick.set_fontweight("bold")
    ax.set_xlim(0, 0.92)
    ax.set_ylim(-0.9, n - 0.1)
    ax.set_xlabel("evidence from measured analogues  (read-across score)", labelpad=7)
    panel_title(ax, "Twenty chemicals the model has never seen",
                "drawn from the wider EPA screen, withheld from fitting, selection and calibration")
    S.despine(ax, keep=("bottom",))
    ax.grid(axis="x")

    # ------------------------------------------------- right: what the twenty became
    counts = df.state.value_counts()
    STATE["assay"] = ("Run the assay first — ranked on analogue evidence", S.SELECTIVE)
    rows = [("assay", counts.get("assay", 0)),
            ("deprioritise", counts.get("deprioritise", 0)),
            ("uninformative", counts.get("uninformative", 0)),
            ("undecidable", counts.get("undecidable", 0))]
    ax2.axis("off")
    ax2.grid(False)
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    panel_title(ax2, "What it decided", "and what it refused to decide")
    y0 = 0.86
    for key, cnt in rows:
        label, col = STATE[key]
        a = light if key == "assay" else (grey if key == "undecidable" else reveal)
        a = max(a, 0.12)
        ax2.add_patch(FancyBboxPatch((0.02, y0 - 0.135), 0.96, 0.125,
                                     boxstyle="round,pad=0.008,rounding_size=0.03",
                                     facecolor=col, edgecolor="none", alpha=0.12 * a, zorder=2))
        ax2.text(0.06, y0 - 0.0725, "%d" % cnt, fontsize=21, fontweight="bold", color=col,
                 va="center", ha="left", alpha=a, zorder=3)
        ax2.text(0.20, y0 - 0.0725, label, fontsize=9.2, color=col, va="center", ha="left",
                 alpha=a, zorder=3, wrap=True)
        y0 -= 0.142
    ax2.text(0.03, y0 - 0.045, "Nine of the twenty come back undecided: four have no\n"
             "single resolvable structure (salts, mixtures, a botanical\n"
             "extract) and five fall outside the applicability domain.\n\n"
             "None of the five recommended carries a confident positive\n"
             "call either — the 90% set is uninformative for all of them.\n"
             "They are simply the chemicals with the strongest analogue\n"
             "evidence, which is what a triage list is; the tool says so\n"
             "rather than dressing a ranking up as a prediction.",
             fontsize=8.7, color=S.INK, va="top", ha="left", linespacing=1.6, alpha=reveal,
             bbox=dict(boxstyle="round,pad=0.6", facecolor=S.CANVAS, edgecolor=S.GRID))

    figure_note(fig, "The five recommended are the highest-evidence chemicals that pass the "
                     "applicability-domain check; the ranking, the three nearest measured "
                     "analogues behind each score and the 90% conformal set are written out for "
                     "every candidate in results/agent_package/scores.csv, so the recommendation "
                     "can be audited rather than trusted.", width=152, y=0.022)
    return fig


if __name__ == "__main__":
    df = load()
    frames = []
    for p in np.concatenate([np.linspace(0, 1, 18), np.linspace(1, 2, 10),
                             np.linspace(2, 3, 12)]):
        f = frame(df, float(p))
        frames.append(S.fig_to_pil(f))
        plt.close(f)
    S.save_gif(S.fixed_canvas(frames), FIGS / "07_agent.gif", duration_ms=85, hold_last_ms=2800)
    f = frame(df, 3.0)
    f.savefig(FIGS / "07_agent.png", bbox_inches=None)
    plt.close(f)
    print("wrote 07_agent.gif / .png")
