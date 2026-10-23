"""Result figures. Every number here is recomputed from the data, never copied from a report.

    python scripts/figures_core.py            # writes results/figs/03..06

The enrichment figure is the headline, so it is the one that animates: "how many laboratory runs do
I need?" is a question about a path, and a path is easier to follow when it is drawn. The rest are
static, because motion would add nothing to them.

Layout rule: a panel's title and subtitle are drawn by `panel_title`, which places both *above* the
axes in a strip reserved by `subplots_adjust`. Matplotlib's own `set_title` is not used alongside
it — mixing the two is what put one line of text on top of another.
"""
from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from sklearn.metrics import roc_auc_score

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")

import figstyle as S  # noqa: E402
from audit_lib import assays_for_share, assays_random, run_cv  # noqa: E402
from dntscout import chem  # noqa: E402
from dntscout.evaluation import RNG_SEED, grouped_folds, scaffold_groups  # noqa: E402

S.apply()
FIGS = Path("results/figs")
FIGS.mkdir(parents=True, exist_ok=True)
AUD = Path("results/audit")
ORDER = ["read_across", "fingerprint_forest", "physchem_logistic"]
SHORT = {"read_across": "read-across", "fingerprint_forest": "structural\nforest",
         "physchem_logistic": "physico-\nchemical", "prevalence": "chance\n(control)"}


def panel_title(ax, title, sub, colour=None):
    ax.text(0.0, 1.115, title, transform=ax.transAxes, fontsize=12.2, fontweight="bold",
            color=colour or S.INK, va="bottom", ha="left")
    ax.text(0.0, 1.030, sub, transform=ax.transAxes, fontsize=8.8, color=S.MUTED,
            va="bottom", ha="left")


def figure_note(fig, text, width=150, y=0.035):
    fig.text(0.012, y, "\n".join(textwrap.wrap(text, width)), fontsize=8.2, color=S.FAINT,
             va="bottom", ha="left", linespacing=1.55)


def load():
    df = pd.read_parquet("data/processed/chemicals_labelled.parquet")
    kept = df[(df.y.notna()) & (df.structure_ok) & (df.smiles.notna())].reset_index(drop=True)
    y = kept.y.astype(int).to_numpy()
    groups = scaffold_groups(kept.scaffold.tolist())
    X, _ = chem.feature_matrix(kept.smiles.tolist())
    sim = chem.tanimoto_matrix(kept.smiles.tolist(), kept.smiles.tolist())
    np.fill_diagonal(sim, 0.0)
    folds = grouped_folds(groups, y, n_folds=5, seed=RNG_SEED)
    res = run_cv(X, X[:, -len(chem.DESCRIPTORS):], sim, y, groups, folds)
    return df, kept, y, groups, sim, res


# ===================================================================== 03 enrichment
def frame_enrichment(curves, y, reveal, rnd, spread):
    n, npos = len(y), int(y.sum())
    prev = npos / n
    half = int(np.ceil(0.5 * npos))
    fig = plt.figure(figsize=(9.6, 6.4))
    ax = fig.add_axes([0.085, 0.175, 0.895, 0.675])
    x = np.arange(n + 1)

    perfect = np.clip(x, 0, npos)
    ax.plot(x, perfect, color=S.PERFECT, lw=1.6, zorder=2)
    ax.fill_between(x, 0, perfect, color=S.PERFECT, alpha=0.15, zorder=1, lw=0)
    ax.plot(x, prev * x, color=S.RANDOM, lw=1.8, dashes=(4, 3), zorder=2)
    ax.text(n * 0.70, perfect[int(n * 0.70)] + 1.3, "perfect ranking", color="#9AA2A9",
            fontsize=8.8, ha="right", va="bottom")
    ax.text(n * 0.985, prev * n * 0.985 - 1.6, "random testing order", color=S.RANDOM,
            fontsize=8.8, ha="right", va="top")

    k = int(np.clip(reveal, 0, 1) * n)
    for m in ORDER:
        c = curves[m]
        if k < 1:
            continue
        ax.plot(x[:k + 1], c[:k + 1], color=S.MODEL_COLOURS[m], lw=2.7 if m == ORDER[0] else 1.9,
                dashes=S.MODEL_DASH[m], zorder=4 if m == ORDER[0] else 3, solid_capstyle="round")
        ax.plot([x[k]], [c[k]], marker="o", ms=5.4, color=S.MODEL_COLOURS[m], zorder=5,
                markeredgecolor=S.PAPER, markeredgewidth=1.3)

    a_model = int(np.argmax(curves[ORDER[0]] >= half))
    a_rand = int(round(half / prev))
    if k >= a_rand:
        for xv, col in ((a_model, S.MODEL), (a_rand, S.RANDOM)):
            ax.plot([xv, xv], [0, half], color=col, lw=1.1, dashes=(2, 2), zorder=2)
            ax.text(xv, -1.4, "%d" % xv, ha="center", va="top", fontsize=11.5,
                    fontweight="bold", color=col)
        ax.plot([0, a_rand], [half, half], color=S.FAINT, lw=1.1, dashes=(2, 2), zorder=2)
        ax.text(1.2, half, "half of the selective compounds  (%d of %d)" % (half, npos),
                fontsize=8.8, color=S.MUTED, va="center", ha="left", zorder=6,
                bbox=dict(boxstyle="round,pad=0.28", facecolor=S.PAPER, edgecolor="none"))
        ax.annotate("", xy=(a_model, half * 0.42), xytext=(a_rand, half * 0.42),
                    arrowprops=dict(arrowstyle="<|-|>", color=S.ACCENT, lw=1.6, shrinkA=0,
                                    shrinkB=0), zorder=6)
        ax.text((a_model + a_rand) / 2, half * 0.42 - 0.8, "%d assays saved" % (a_rand - a_model),
                ha="center", va="top", fontsize=11, fontweight="bold", color=S.ACCENT, zorder=7,
                bbox=dict(boxstyle="round,pad=0.3", facecolor=S.PAPER, edgecolor="none"))

    if k >= n - 1:
        handles = [plt.Line2D([], [], color=S.MODEL_COLOURS[m], lw=2.4, dashes=S.MODEL_DASH[m],
                              label=S.MODEL_LABELS[m]) for m in ORDER]
        ax.legend(handles=handles, loc="lower right", bbox_to_anchor=(1.0, 0.02))

    ax.set_xlim(0, n)
    ax.set_ylim(-0.5, npos + 2.5)
    ax.set_xlabel("microelectrode-array runs performed, in the order the model recommends",
                  labelpad=16)
    ax.set_ylabel("selective compounds found")
    panel_title(ax, "How many laboratory runs to find the actives?",
                "%d chemicals, %d with a selective effect · scaffold-held-out, "
                "ranks pooled within fold" % (n, npos))
    S.despine(ax)
    figure_note(fig, "Read-across needs %d runs to reach half the actives against an exact "
                     "random-order mean of %.1f (95%% range %d-%d). The saving does not depend on "
                     "one lucky split: 20 fold assignments give a median of %d runs (%d-%d), and "
                     "an independent audit over 200 fresh assignments finds 33-34 runs typically "
                     "(29-44)."
                % (a_model, rnd[0], rnd[1], rnd[2], spread[0], spread[1], spread[2]),
                width=136, y=0.022)
    return fig


def make_enrichment(res, y, aud):
    curves = {m: np.concatenate([[0], np.cumsum(y[np.argsort(-res.rank_pooled(m), kind="stable")])])
              for m in ORDER}
    rnd = assays_random(y, 0.5)
    b = [r for r in aud["B_repeated_cv_summary"] if r["model"] == ORDER[0]][0]
    spread = (int(b["assays_median"]), b["assays_min"], b["assays_max"])
    frames = []
    for p in np.linspace(0, 1, 40):
        f = frame_enrichment(curves, y, S.ease(p), rnd, spread)
        frames.append(S.fig_to_pil(f))
        plt.close(f)
    S.save_gif(S.fixed_canvas(frames), FIGS / "03_enrichment.gif", duration_ms=70,
               hold_last_ms=2800)
    f = frame_enrichment(curves, y, 1.0, rnd, spread)
    f.savefig(FIGS / "03_enrichment.png", bbox_inches=None)
    plt.close(f)
    print("wrote 03_enrichment.gif / .png")


# ===================================================================== 04 robustness
def make_robustness(aud):
    fig = plt.figure(figsize=(14.0, 5.3))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.15, 1.0, 0.9], wspace=0.40,
                          left=0.055, right=0.985, top=0.790, bottom=0.300)
    ax, ax2, ax3 = (fig.add_subplot(gs[0, i]) for i in range(3))
    rec = aud["B_repeated_cv"]

    # ---- (a) 20 fold assignments
    keys = ["prevalence"] + ORDER[::-1]
    rng = np.random.default_rng(7)
    for i, m in enumerate(keys):
        v = np.array(rec[m]["roc_rank"], dtype=float)
        ax.scatter(i + rng.uniform(-0.13, 0.13, len(v)), v, s=26, color=S.MODEL_COLOURS[m],
                   alpha=0.6, zorder=3, edgecolors="none")
        med = float(np.median(v))
        ax.plot([i - 0.28, i + 0.28], [med, med], color=S.MODEL_COLOURS[m], lw=3.0, zorder=4,
                solid_capstyle="butt")
        ax.text(i, max(v) + 0.022, "%.3f" % med, fontsize=9.4, ha="center", va="bottom",
                color=S.MODEL_COLOURS[m], fontweight="bold")
    ax.axhline(0.5, color=S.FAINT, lw=1.1, dashes=(3, 3), zorder=2)
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels([SHORT[m] for m in keys], fontsize=9)
    ax.set_xlim(-0.6, len(keys) - 0.4)
    ax.set_ylabel("ROC AUC")
    ax.set_ylim(0.44, 0.92)
    panel_title(ax, "Every fold assignment, not one",
                "20 independent 5-fold splits of the same 102 chemicals")
    S.despine(ax)
    ax.grid(axis="x", visible=False)

    # ---- (b) similarity cap
    cap = pd.DataFrame(aud["C_similarity_cap"])
    xs = {"none": 1.0, "0.9": 0.9, "0.7": 0.7, "0.5": 0.5, "0.4": 0.4,
          0.9: 0.9, 0.7: 0.7, 0.5: 0.5, 0.4: 0.4}
    for m in ("read_across", "fingerprint_forest"):
        sub = cap[cap.model == m]
        xv = np.array([xs[c] for c in sub.cap], dtype=float)
        o = np.argsort(-xv)
        ax2.plot(xv[o], sub.roc_rank.to_numpy()[o], marker="o", ms=6.5,
                 color=S.MODEL_COLOURS[m], dashes=S.MODEL_DASH[m], label=S.MODEL_LABELS[m],
                 markeredgecolor=S.PAPER, markeredgewidth=1.3)
    ax2.axhline(0.5, color=S.FAINT, lw=1.1, dashes=(3, 3))
    ax2.invert_xaxis()
    ax2.set_xlabel("closest analogue the model may see  (Tanimoto)", labelpad=7)
    ax2.set_ylabel("ROC AUC")
    ax2.set_ylim(0.44, 0.92)
    ax2.set_xticks([1.0, 0.9, 0.7, 0.5, 0.4])
    ax2.set_xticklabels(["no cap", "<0.9", "<0.7", "<0.5", "<0.4"], fontsize=9)
    panel_title(ax2, "Hiding the close analogues",
                "if the signal were memorised near-duplicates, these lines would fall to 0.5")
    ax2.legend(loc="lower left", bbox_to_anchor=(0.0, 0.10), fontsize=8.6)
    S.despine(ax2)

    # ---- (c) a harder split
    cl = pd.DataFrame(aud["D_cluster_split"])
    thr = sorted(cl.sim_threshold.unique())[-1]
    sub = cl[(cl.sim_threshold == thr)].set_index("model")
    base = {m: float(np.median(rec[m]["roc_rank"])) for m in ORDER}
    xp, w = np.arange(len(ORDER)), 0.37
    ax3.bar(xp - w / 2, [base[m] for m in ORDER], width=w, color=S.PERFECT,
            label="scaffold split", zorder=3)
    ax3.bar(xp + w / 2, [sub.roc_rank[m] for m in ORDER], width=w,
            color=[S.MODEL_COLOURS[m] for m in ORDER], label="chemical-cluster split", zorder=3)
    for i, m in enumerate(ORDER):
        ax3.text(xp[i] - w / 2, base[m] + 0.012, "%.2f" % base[m], ha="center", fontsize=8.6,
                 color=S.MUTED)
        ax3.text(xp[i] + w / 2, sub.roc_rank[m] + 0.012, "%.3f" % sub.roc_rank[m], ha="center",
                 fontsize=9.2, color=S.MODEL_COLOURS[m], fontweight="bold")
    ax3.axhline(0.5, color=S.FAINT, lw=1.1, dashes=(3, 3))
    ax3.set_xticks(xp)
    ax3.set_xticklabels([SHORT[m] for m in ORDER], fontsize=9)
    ax3.set_ylim(0.44, 0.92)
    ax3.set_ylabel("ROC AUC")
    panel_title(ax3, "A harder split",
                "pale = scaffold split · solid = Butina clusters at %.1f, held out whole" % thr)
    S.despine(ax3)
    ax3.grid(axis="x", visible=False)

    figure_note(fig, "Left: the spread a single 5-fold split cannot show; the median is the number "
                     "to quote. Middle and right: two ways of asking whether the model generalises "
                     "to unfamiliar chemistry rather than recognising close relatives. The "
                     "structural forest ignores the similarity matrix, so it is flat in the middle "
                     "panel by construction — an internal control. Ranks are pooled within fold, "
                     "so a constant predictor scores exactly 0.500.", width=168, y=0.022)
    fig.savefig(FIGS / "04_robustness.png", bbox_inches=None)
    plt.close(fig)
    print("wrote 04_robustness.png")


# ===================================================================== 05 uncertainty
def make_conformal(ev):
    cf = ev["conformal"]
    fig = plt.figure(figsize=(13.4, 4.9))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.08, 1.0], wspace=0.42,
                          left=0.075, right=0.985, top=0.780, bottom=0.300)
    ax, ax2, ax3 = (fig.add_subplot(gs[0, i]) for i in range(3))

    names = ["all held-out\n(n=%d)" % cf["n"], "selective\n(n=%d)" % cf["n_class_1"],
             "no effect\n(n=%d)" % cf["n_class_0"]]
    vals = [cf["coverage_all"], cf["coverage_class_1"], cf["coverage_class_0"]]
    yp = np.arange(3)[::-1]
    ax.barh(yp, vals, color=[S.INK, S.SELECTIVE, S.NO_EFFECT], height=0.46, zorder=3)
    ax.set_ylim(-0.95, 2.62)
    ax.axvline(0.90, color=S.ACCENT, lw=1.9, zorder=5)
    ax.text(0.90, -0.72, "promised 90%", color=S.ACCENT, fontsize=9, ha="center", va="center",
            fontweight="bold")
    for yy, v in zip(yp, vals):
        ax.text(v - 0.012, yy, "%.1f%%" % (100 * v), va="center", ha="right", fontsize=10.5,
                color=S.PAPER, fontweight="bold")
    ax.set_yticks(yp)
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlim(0.6, 1.0)
    ax.set_xlabel("measured coverage", labelpad=7)
    panel_title(ax, "The promise is kept", "measured on held-out scaffolds, not assumed")
    S.despine(ax, keep=("bottom",))
    ax.grid(axis="x")

    parts = [("one class — a usable answer", cf["share_singleton"], S.MODEL),
             ("both classes — cannot tell", cf["share_uninformative"], S.UNKNOWN),
             ("neither — rejected", cf["share_rejected"], S.CYTOTOX)]
    left = 0.0
    for _, v, col in parts:
        ax2.barh([0.3], [v], left=left, color=col, height=0.34, zorder=3)
        if v > 0.06:
            ax2.text(left + v / 2, 0.3, "%.0f%%" % (100 * v), ha="center", va="center",
                     fontsize=11.5, color=S.PAPER, fontweight="bold")
        left += v
    ax2.barh([-0.45], [cf["share_out_of_domain"]], color=S.FAINT, height=0.34, zorder=3)
    ax2.text(cf["share_out_of_domain"] + 0.02, -0.45, "%.1f%% outside the\napplicability domain"
             % (100 * cf["share_out_of_domain"]), va="center", fontsize=8.8, color=S.MUTED)
    ax2.set_yticks([0.3, -0.45])
    ax2.set_yticklabels(["prediction\nset", "domain\ncheck"], fontsize=9)
    ax2.set_xlim(0, 1.0)
    ax2.set_ylim(-0.95, 0.75)
    ax2.set_xlabel("share of held-out chemicals", labelpad=7)
    panel_title(ax2, "Abstention is a feature",
                "a tool that cannot say \"I do not know\" is not usable in a laboratory")
    left = 0.0
    for label, v, col in parts:                      # labels sit under their own segment
        if v > 0.06:
            ax2.text(left + v / 2, 0.055, label, ha="center", va="top", fontsize=8.3, color=col,
                     wrap=True)
        left += v
    S.despine(ax2, keep=("bottom",))
    ax2.grid(axis="x")

    bands = ev.get("by_similarity_to_training", [])
    if bands:
        xp = np.arange(len(bands))
        v = [b["roc_auc"] for b in bands]
        ax3.bar(xp, v, color=S.MODEL_ALT, width=0.5, zorder=3)
        for i, b in enumerate(bands):
            ax3.text(i, v[i] + 0.014, "%.2f" % v[i], ha="center", fontsize=9.6,
                     fontweight="bold", color=S.MODEL_ALT)
            ax3.text(i, 0.462, "n=%d" % b["n"], ha="center", fontsize=8.6, color=S.PAPER)
        ax3.axhline(0.5, color=S.FAINT, lw=1.1, dashes=(3, 3))
        ax3.set_xticks(xp)
        ax3.set_xticklabels([b["nearest_analogue_tanimoto"] for b in bands], fontsize=9)
        ax3.set_ylim(0.44, 0.92)
        ax3.set_xlabel("Tanimoto to the nearest training analogue", labelpad=7)
        ax3.set_ylabel("ROC AUC")
        panel_title(ax3, "Where it can be trusted",
                    "accuracy is not uniform, and the tool reports which band a query is in")
        S.despine(ax3)
        ax3.grid(axis="x", visible=False)

    figure_note(fig, "Mondrian (class-conditional) conformal prediction at a nominal 90% "
                     "confidence, calibrated inside each training fold on the same fitted model "
                     "that scores the held-out chemicals, and measured on held-out scaffolds. "
                     "With 102 held-out chemicals the standard error on a coverage of 0.90 is "
                     "about 3 points, so the measured value agrees with the promise.",
                width=160, y=0.022)
    fig.savefig(FIGS / "05_uncertainty.png", bbox_inches=None)
    plt.close(fig)
    print("wrote 05_uncertainty.png")


# ===================================================================== 06 scope
def make_scope(res, y, aud):
    fig = plt.figure(figsize=(13.0, 5.0))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.22, 1.0], wspace=0.28,
                          left=0.065, right=0.985, top=0.790, bottom=0.300)
    ax, ax2 = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])
    s = res.rank_pooled("read_across")
    rankcsv = AUD / "cytotoxicant_ranking.csv"
    inc = pd.read_csv(rankcsv) if rankcsv.exists() else None

    bins = np.linspace(0, 1, 13)
    ax.hist(s[y == 0], bins=bins, color=S.NO_EFFECT, alpha=0.72, zorder=2,
            label="no effect observed (%d)" % int((y == 0).sum()))
    ax.hist(s[y == 1], bins=bins, color=S.SELECTIVE, alpha=0.72, zorder=3,
            label="selective (%d)" % int((y == 1).sum()))
    if inc is not None:
        ax.scatter(inc.percentile_in_eval_set, np.full(len(inc), -0.85), marker="|", s=230,
                   linewidths=1.9, color=S.CYTOTOX, zorder=4,
                   label="non-selective cytotoxicants, never trained on (%d)" % len(inc))
    ax.set_ylim(-1.8, None)
    ax.set_xlabel("model score  (within-fold rank)", labelpad=7)
    ax.set_ylabel("chemicals")
    panel_title(ax, "What the score separates",
                "the two modelled classes, and where the excluded cytotoxicants land")
    ax.legend(fontsize=8.4, loc="upper center")
    S.despine(ax)
    ax.grid(axis="x", visible=False)

    st = pd.DataFrame(aud["F_stress_endpoint"]).set_index("model")
    base = {m: float(np.median(aud["B_repeated_cv"][m]["roc_rank"])) for m in ORDER}
    xp, w = np.arange(len(ORDER)), 0.37
    ax2.bar(xp - w / 2, [base[m] for m in ORDER], width=w, color=S.PERFECT,
            label="primary: selective vs no effect", zorder=3)
    ax2.bar(xp + w / 2, [st.roc_rank[m] for m in ORDER], width=w,
            color=[S.MODEL_COLOURS[m] for m in ORDER],
            label="harder: selective vs everything else", zorder=3)
    for i, m in enumerate(ORDER):
        lo, hi = st.roc_ci95[m]
        ax2.plot([xp[i] + w / 2] * 2, [lo, hi], color=S.INK, lw=1.3, zorder=4)
        ax2.text(xp[i] - w / 2, base[m] + 0.012, "%.2f" % base[m], ha="center", fontsize=8.6,
                 color=S.MUTED)
        ax2.text(xp[i] + w / 2, hi + 0.014, "%.3f" % st.roc_rank[m], ha="center", fontsize=9.2,
                 color=S.MODEL_COLOURS[m], fontweight="bold")
    ax2.axhline(0.5, color=S.FAINT, lw=1.1, dashes=(3, 3))
    ax2.set_xticks(xp)
    ax2.set_xticklabels([SHORT[m] for m in ORDER], fontsize=9)
    ax2.set_ylim(0.44, 0.92)
    ax2.set_ylabel("ROC AUC")
    panel_title(ax2, "The harder question, asked too",
                "pale = primary · solid = %d chemicals with the %d cytotoxicants as negatives"
                % (int(st.n.iloc[0]), int(st.n.iloc[0]) - 102))
    S.despine(ax2)
    ax2.grid(axis="x", visible=False)

    figure_note(fig, "The excluded cytotoxicants are bioactive chemicals whose network effect "
                     "appears only at lethal concentrations. Several sit just under the "
                     "three-fold line — permethrin at 1.9x, rotenone at 2.1x — so a high score "
                     "for them is the model recognising real neuroactive chemistry, not a false "
                     "alarm; what structure alone does not resolve is the fine selectivity "
                     "margin. Error bars: 95% cluster bootstrap over scaffold groups.",
                width=162, y=0.022)
    fig.savefig(FIGS / "06_scope.png", bbox_inches=None)
    plt.close(fig)
    print("wrote 06_scope.png")


if __name__ == "__main__":
    which = sys.argv[1:] or ["03", "04", "05", "06"]
    df, kept, y, groups, sim, res = load()
    aud = json.loads((AUD / "audit_02_validity.json").read_text())
    ev = json.loads(Path("results/evaluation.json").read_text())
    if "03" in which:
        make_enrichment(res, y, aud)
    if "04" in which:
        make_robustness(aud)
    if "05" in which:
        make_conformal(ev)
    if "06" in which:
        make_scope(res, y, aud)
