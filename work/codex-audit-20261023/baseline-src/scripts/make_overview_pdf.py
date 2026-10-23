"""The five-page project overview, built rather than typed.

The hackathon allows at most five pages, which is a hard constraint, so the document is generated
from the same figures and the same numbers as the repository and then *checked*: the script fails
if the result runs over five pages. That way the limit cannot be broken by an edit nobody re-counted.

    python scripts/make_overview_pdf.py     # writes docs/DNT-Scout_overview.pdf
"""
from __future__ import annotations

import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, NextPageTemplate,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")

FIGS = Path("results/figs")
OUT = Path("docs/DNT-Scout_overview.pdf")
OUT.parent.mkdir(parents=True, exist_ok=True)

INK = colors.HexColor("#131A22")
MUTED = colors.HexColor("#5E6A76")
FAINT = colors.HexColor("#9AA4AE")
RULE = colors.HexColor("#DFE4E9")
CANVAS = colors.HexColor("#F7F8FA")
SELECTIVE = colors.HexColor("#C03A1D")
MODEL = colors.HexColor("#0E6F63")
ACCENT = colors.HexColor("#B8860B")

PAGE_W, PAGE_H = A4
MARGIN = 16 * mm
BODY_W = PAGE_W - 2 * MARGIN


def register_fonts() -> tuple[str, str]:
    """Use DejaVu where it exists so the document matches the figures; else fall back."""
    import matplotlib
    root = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    pairs = [("DejaVuSans.ttf", "DJV"), ("DejaVuSans-Bold.ttf", "DJV-B")]
    try:
        for fn, name in pairs:
            pdfmetrics.registerFont(TTFont(name, str(root / fn)))
        pdfmetrics.registerFontFamily("DJV", normal="DJV", bold="DJV-B")
        return "DJV", "DJV-B"
    except Exception:
        return "Helvetica", "Helvetica-Bold"


F, FB = register_fonts()

S = {
    "h1": ParagraphStyle("h1", fontName=FB, fontSize=19, leading=22.5, textColor=INK,
                         spaceAfter=2),
    "sub": ParagraphStyle("sub", fontName=F, fontSize=10.6, leading=14, textColor=MUTED,
                          spaceAfter=7),
    "meta": ParagraphStyle("meta", fontName=F, fontSize=7.6, leading=10.6, textColor=FAINT,
                           spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName=FB, fontSize=11.4, leading=13.6, textColor=INK,
                         spaceBefore=9, spaceAfter=3.5),
    "body": ParagraphStyle("body", fontName=F, fontSize=8.5, leading=11.6, textColor=INK,
                           alignment=TA_JUSTIFY, spaceAfter=4.5),
    "lead": ParagraphStyle("lead", fontName=F, fontSize=9.3, leading=12.8, textColor=INK,
                           alignment=TA_JUSTIFY, spaceAfter=5),
    "cap": ParagraphStyle("cap", fontName=F, fontSize=7.1, leading=9.4, textColor=FAINT,
                          alignment=TA_LEFT, spaceAfter=6, spaceBefore=1.5),
    "cell": ParagraphStyle("cell", fontName=F, fontSize=7.6, leading=9.8, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName=FB, fontSize=7.6, leading=9.8, textColor=INK),
    "cellh": ParagraphStyle("cellh", fontName=FB, fontSize=7.4, leading=9.4, textColor=MUTED),
}


def P(t, s="body"):
    return Paragraph(t, S[s])


def fig(name, width_frac=1.0, caption=None):
    from PIL import Image as PILImage
    p = FIGS / name
    w, h = PILImage.open(p).size
    target_w = BODY_W * width_frac
    img = Image(str(p), width=target_w, height=target_w * h / w)
    img.hAlign = "LEFT"
    return KeepTogether([img, P(caption, "cap")]) if caption else img


def table(rows, widths, header=True, highlight_row=None):
    data = []
    for i, r in enumerate(rows):
        style = "cellh" if (header and i == 0) else ("cellb" if i == highlight_row else "cell")
        data.append([Paragraph(str(c), S[style]) for c in r])
    t = Table(data, colWidths=widths, hAlign="LEFT")
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, RULE),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, colors.HexColor("#EEF1F4")),
    ]
    if highlight_row is not None:
        cmds.append(("BACKGROUND", (0, highlight_row), (-1, highlight_row), CANVAS))
    t.setStyle(TableStyle(cmds))
    return t


def callout(title, body, colour=MODEL):
    inner = [[Paragraph("<b>%s</b>" % title, ParagraphStyle(
        "ct", fontName=FB, fontSize=9.2, leading=12, textColor=colour)),],
        [Paragraph(body, ParagraphStyle(
            "cb", fontName=F, fontSize=8.4, leading=11.4, textColor=INK, alignment=TA_JUSTIFY))]]
    t = Table(inner, colWidths=[BODY_W - 10 * mm], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CANVAS),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 7), ("BOTTOMPADDING", (0, -1), (-1, -1), 7),
        ("TOPPADDING", (0, 1), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
        ("LINEBEFORE", (0, 0), (0, -1), 2.2, colour),
    ]))
    return t


def footer(canv, doc):
    canv.saveState()
    canv.setFont(F, 7)
    canv.setFillColor(FAINT)
    canv.drawString(MARGIN, 9.5 * mm, "DNT-Scout · 2026 Global AI4Science Hackathon · "
                                      "github.com/Agnuxo1/dnt-scout")
    canv.drawRightString(PAGE_W - MARGIN, 9.5 * mm, "%d / 5" % canv.getPageNumber())
    canv.setStrokeColor(RULE)
    canv.setLineWidth(0.5)
    canv.line(MARGIN, 13 * mm, PAGE_W - MARGIN, 13 * mm)
    canv.restoreState()


def build():
    doc = BaseDocTemplate(str(OUT), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=14 * mm, bottomMargin=17 * mm,
                          title="DNT-Scout — project overview",
                          author="Francisco Angulo de Lafuente")
    frame = Frame(MARGIN, 17 * mm, BODY_W, PAGE_H - 14 * mm - 17 * mm, id="f",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=footer)])
    st = []

    # ------------------------------------------------------------------ page 1
    st += [
        P("DNT-Scout", "h1"),
        P("Structure-based triage for developmental neurotoxicity screening, "
          "with calibrated abstention", "sub"),
        P("2026 Global AI4Science Hackathon · AI + Biology / AI Agent · Team NeuroChip Twin (solo) · "
          "Francisco Angulo de Lafuente<br/>"
          "Code and data: <b>github.com/Agnuxo1/dnt-scout</b> (public, MIT) · "
          "SciencePal project: see §5", "meta"),
        callout("Which untested chemicals deserve a microelectrode-array run — and when is the "
                "structural evidence too thin to say?",
                "From a chemical structure alone, DNT-Scout ranks compounds by how likely they are "
                "to <i>selectively</i> disrupt the formation of neuronal networks, attaches a "
                "calibrated statement of confidence, and refuses to answer when the chemistry lies "
                "outside what it has evidence for. <b>32 microelectrode-array runs instead of 52</b> "
                "to find half the active compounds — about a third of the laboratory work removed, "
                "and stable at 31–37 runs across 20 independent splits. It is a triage tool for a "
                "laboratory queue, not a safety verdict.", SELECTIVE),
        Spacer(1, 7),
        P("1 · The problem, and why it is a scheduling problem", "h2"),
        P("Developmental neurotoxicity is among the most expensive endpoints in regulatory "
          "toxicology and one of the least covered: tens of thousands of chemicals are in commerce, "
          "and a few hundred have been through a full battery. The <i>in vitro</i> alternative "
          "adopted by the OECD DNT-IVB guidance (2023) — growing cortical neurons on a "
          "<b>microelectrode array</b> and watching whether they organise into a firing network — "
          "is far faster than an animal study, but still costs days of culture per compound. With "
          "the US EPA moving to phase out mammalian testing, the binding constraint stops being "
          "<i>is this chemical neurotoxic?</i> and becomes: <b>of the compounds nobody has tested, "
          "which ones go on the plate first?</b>", "lead"),
        P("That phrasing matters, because it makes the question measurable. The answer is not an "
          "accuracy figure; it is <b>how many assays you have to run to find the actives</b>. "
          "Every claim here is validated against that number.", "lead"),
        P("<b>The gap.</b> Strickland (2018) and Kosnik (2020) associate ToxPrint features with MEA "
          "activity, but without a validated predictive model. Zhang (2021) and Morger (2021) apply "
          "conformal prediction to Tox21, but to no neuronal endpoint. We found no published work "
          "doing scaffold-held-out prediction of <i>selective</i> network-formation activity "
          "together with calibrated uncertainty and an explicit applicability domain."),
        Spacer(1, 3),
        fig("01_pipeline.png", 1.0,
            "Four steps. Structures are resolved and standardised; mixtures and inorganics are "
            "flagged and excluded rather than coerced. The decision returned is one of three, and "
            "never a safety verdict."),
    ]

    # ------------------------------------------------------------------ page 2
    st += [
        NextPageTemplate("all"),
        P("2 · What counts as a hit — the trap this endpoint avoids", "h2"),
        P("A chemical that kills the culture flattens every electrophysiological parameter. "
          "Counting that as neuroactive is the main way a developmental-neurotoxicity screen fools "
          "itself, so the primary outcome is defined <b>against viability</b>: at least one of the "
          "17 network parameters must respond at a concentration at least three-fold below any "
          "cytotoxic concentration. Ambiguous chemicals keep their own classes and are "
          "<b>never silently turned into negatives</b>.", "lead"),
        Spacer(1, 2),
        KeepTogether(table([["Class", "n", "Role in the analysis"],
               ["Selective effect on network formation", "49", "positive"],
               ["No effect observed in the tested range", "53", "negative"],
               ["Network effect only at cytotoxic concentrations", "28",
                "reported, excluded, analysed separately (§4)"],
               ["Structure not modellable (mixture, inorganic, unresolved)", "6",
                "reported, excluded"]],
              [BODY_W * 0.47, BODY_W * 0.07, BODY_W * 0.46])),
        Spacer(1, 5),
        P("Two things are stated openly rather than buried. The 3× threshold is a choice, so the "
          "class counts at 1×, 3× and 10× are published together (70 · 49 · 35). And <b>27 of the "
          "49 positives have no fitted cytotoxicity EC50 at all</b>, so for them the 3× rule was "
          "never the binding test — they are \"the network responded and nothing toxic was seen in "
          "range\". The model finds both kinds about equally well (ROC 0.854 for the 22 with a "
          "measured separation, 0.806 for the 27 without), so this is one endpoint, not two in "
          "disguise."),
        fig("02_endpoint.png", 1.0,
            "Left: the three archetypes on a concentration axis. Right: the four classes as "
            "measured, with the hatched 27 marking the positives the ≥3× rule never actually "
            "bound. Source: Shafer et al. 2019, US EPA ScienceHub, DOI 10.23719/1503191 "
            "(public domain). A missing EC50 is the source table's own convention for \"no "
            "concentration-response fitted inside the tested range\", not a missing measurement."),
        P("3 · Method", "h2"),
        P("<b>Data.</b> 136 chemicals with per-parameter EC50 values across 17 network parameters "
          "and two viability assays, re-downloaded from the original EPA source and pinned by "
          "SHA256; structures resolved from PubChem (132/136) and standardised with RDKit. "
          "<b>Models.</b> A prevalence control; L2 logistic regression on ten physicochemical "
          "descriptors; a similarity-weighted k-nearest-analogue <b>read-across</b> of the kind US "
          "EPA GenRA is built on; and a random forest over Morgan fingerprints, MACCS keys and "
          "descriptors. Hyperparameters and the conformal calibration split are chosen by grouped "
          "cross-validation <b>inside each training fold</b>; the test fold is touched once, to "
          "predict. Confidence intervals resample whole scaffold groups, never individual "
          "chemicals. <b>Uncertainty.</b> Mondrian conformal prediction at a nominal 90% with an "
          "applicability-domain check; the conformal quantiles and the test scores they are applied "
          "to come from the same fitted model, which is what makes the guarantee follow."),
    ]

    # ------------------------------------------------------------------ page 3
    st += [
        KeepTogether([P("4 · Result", "h2"), fig("03_enrichment.png", 0.88)]),
        Spacer(1, 1),
        table([["Model", "ROC AUC<br/>pre-declared split", "ROC AUC<br/>median of 20 splits",
                "PR AUC", "Assays for<br/>half the actives"],
               ["Chance (control)", "<b>0.500</b>", "0.500", "0.480", "52"],
               ["Physicochemical descriptors", "0.750", "0.746", "0.635", "36"],
               ["Read-across from measured analogues", "<b>0.828</b>",
                "<b>0.776 (0.703–0.828)</b>", "<b>0.780</b>", "<b>32 (31–37)</b>"],
               ["Structural random forest", "0.766", "0.756", "0.674", "36"]],
              [BODY_W * 0.30, BODY_W * 0.17, BODY_W * 0.21, BODY_W * 0.11, BODY_W * 0.21],
              highlight_row=3),
        P("Half the selective compounds are found after <b>32</b> MEA runs against <b>52</b> at "
          "random (51.4 on average, 95% range 41–61). A perfect oracle would need 25, so the "
          "ranking captures about three quarters of the gain available at all. The chance control "
          "landing at exactly 0.500 is not cosmetic — see below.", "cap"),
        P("5 · Validation, and four attempts to break the result", "h2"),
        callout("A defect we found in our own evaluation, and fixed",
                "Cross-validation produces one model per fold, and nothing makes five models' "
                "probabilities comparable. Pooling raw scores into one ranking mixes five scales: "
                "our prevalence baseline — a constant per fold, which <i>must</i> score chance — "
                "came out at ROC 0.473, and every ranking metric inherited the bias. Ranking each "
                "score within its own fold puts the control at exactly 0.500 and raises read-across "
                "from 0.803 to 0.828. Both numbers are published side by side and a regression test "
                "prevents the raw version returning. We also found and fixed a conformal procedure "
                "calibrated on a different model from the one making the predictions, and an "
                "operating threshold taken from the evaluation set's own labels.", ACCENT),
        Spacer(1, 4),
        fig("04_robustness.png", 1.0),
    ]

    # ------------------------------------------------------------------ page 4
    st += [
        P("<b>One split is not evidence.</b> Repeating the whole evaluation over 20 fold "
          "assignments gives a median ROC of <b>0.776 (0.703–0.828)</b>. The pre-declared split "
          "landed at the optimistic end, so 0.776 is the number to quote for accuracy. The "
          "practical figure barely moves: <b>32 assays, range 31–37</b>, against 52 for every "
          "split."),
        P("<b>Is it memorising close relatives?</b> Read-across votes on measured analogues, so "
          "this is the obvious worry. Hiding every training analogue above a similarity cap answers "
          "it: at a cap of 0.7, ROC 0.820; at 0.5, ROC 0.799. There was little to memorise anyway — "
          "the median nearest-analogue Tanimoto is 0.36 and only 4% of chemicals have an analogue "
          "above 0.9. The structural forest ignores the similarity matrix and is flat across the "
          "cap: the internal control this test needs."),
        P("<b>A harder split.</b> 72% of Bemis-Murcko scaffold groups hold a single chemical, so "
          "scaffold-held-out is close to leave-one-out. Holding out whole Butina clusters at 0.6 "
          "similarity drops performance to 0.74–0.77 — still far above chance, but the three model "
          "families converge. <b>Read-across being the best model is specific to the scaffold "
          "split; structure carrying real signal is not.</b>"),
        KeepTogether([P("6 · Saying \"I don't know\"", "h2"),
        P("A triage tool that answers every question is not calibrated, it is guessing. Coverage is "
          "<b>measured on held-out scaffolds, not assumed</b>: 89.2% against the 90% promised "
          "(87.8% and 90.6% by class). With 102 held-out chemicals the standard error on a coverage "
          "of 0.90 is about 3 points, so these agree. The honest cost: the prediction set is "
          "uninformative for 63% of chemicals and 7.8% fall outside the applicability domain. "
          "Those are the queries where the right answer is a shrug, and the tool gives one."),
        fig("05_uncertainty.png", 1.0)]),
        P("7 · Scope, and what lies outside it", "h2"),
        P("The 28 chemicals whose network effect appears only at lethal concentrations are excluded "
          "from the primary comparison, and they are not a random 28: they carry 22 scaffolds that "
          "then appear nowhere in the modelled set, and they form a coherent mechanistic family — "
          "rotenone, valinomycin, tributyltin, five strobilurins, two statins, chlordane, "
          "endosulfan, MPP⁺. So the harder question is asked as well: <b>selective activity against "
          "everything else, cytotoxicants included.</b> Read-across scores <b>0.696 (0.595–0.784)</b> "
          "there, 44 assays against 65.5 at random — lower, as it should be, with the interval "
          "still excluding chance. The model does rank several of those cytotoxicants highly, and "
          "that is worth reading carefully: permethrin sits at a selectivity ratio of 1.9×, "
          "rotenone at 2.1×, just under the three-fold line. A high score is the model correctly "
          "recognising real neuroactive chemistry; what structure alone does not resolve is the "
          "fine selectivity margin. In the EPA protocol viability is read from the same plate, so "
          "such an assay still returns a usable answer."),
    ]

    # ------------------------------------------------------------------ page 5
    st += [
        P("8 · SciencePal in the core step", "h2"),
        P("The central decision of this project does not happen in our repository — it happens "
          "inside SciencePal. The platform's <b>Biology Agent</b> is given the 102 measured "
          "analogues with their outcomes, 20 chemicals from the wider EPA screen withheld from "
          "every stage of fitting, selection and calibration, the project's scoring script and a "
          "task specification. Inside the SciencePal sandbox it executes that code, resolves each "
          "candidate structure, applies the model and the conformal rule, consults the literature "
          "on the nearest analogues, and returns a structured triage report: five chemicals to "
          "assay, with evidence, uncertainty, reason and the next assay to run. "
          "<b>Pre-declared ablation:</b> automatic ranking alone versus ranking + agent on the same "
          "20 withheld chemicals, so the platform's contribution is measured rather than asserted.", "lead"),
        fig("07_agent.png", 1.0,
            "Nine of the twenty come back undecided — four have no single resolvable structure, "
            "five are outside the applicability domain — and none of the five recommended carries "
            "a confident positive call either. They are the chemicals with the strongest analogue "
            "evidence, which is what a triage list is, and the agent reports it that way rather "
            "than dressing a ranking up as a prediction."),
        P("9 · Limitations", "h2"),
        P("<b>102 chemicals.</b> Every interval is wide; the per-fold standard deviation of ROC is "
          "0.108. This is a small-data problem and is reported as one. &nbsp;<b>Cohort prevalence "
          "is 48%</b> because the EPA enriched it with suspected actives, so the assay saving does "
          "not transfer unchanged to an unselected library, and we do not claim it does. "
          "&nbsp;<b>Concordance, not external validation:</b> all 136 labelled chemicals sit inside "
          "the wider EPA screen of 460, so the second dataset is a cohort concordance check. "
          "&nbsp;<b>One assay, one laboratory, one developmental window.</b> &nbsp;<b>Not a safety "
          "verdict:</b> a negative <i>in vitro</i> result does not exclude developmental "
          "neurotoxicity — the OECD guidance says so directly."),
        P("10 · Next steps", "h2"),
        P("<b>(1)</b> Extend to the 324 chemicals of the wider screen that have network data but no "
          "viability measurement — a weaker label, requiring an explicit statement of why, and a "
          "natural test of whether the ranking survives a noisier outcome. &nbsp;<b>(2)</b> "
          "Prospective validation: the five recommendations in §8 are a falsifiable prediction, and "
          "one MEA plate would settle them. &nbsp;<b>(3)</b> A pre-declared graph-neural-network "
          "comparison, deliberately left out at n = 102, once there is enough data to make it "
          "meaningful. &nbsp;<b>(4)</b> Cross-laboratory concordance between the NTP and ToxCast "
          "cohorts inside the EPA screen."),
        P("Originality and resources", "h2"),
        P("<b>All code, figures, results and text were created during the event.</b> The author has "
          "a separate, unrelated project (NeuroChip Twin) entered in another competition; "
          "<b>no code, model, preprocessing, text, figure or video from it is used here</b> — "
          "DNT-Scout is a clean-room project with a new question, a new repository and new code. "
          "Data: US EPA network-formation assay (Shafer et al. 2019, DOI 10.23719/1503191) and "
          "PubChem, both public domain, re-downloaded from source and pinned by SHA256; raw data "
          "are not redistributed. Software: RDKit, scikit-learn, NumPy, pandas, Matplotlib — all "
          "open-source and permissively licensed. <b>No pretrained models, no proprietary models, "
          "no paid APIs.</b> Claude (Anthropic) was used as a programming and writing assistant "
          "under the author's direction; every scientific claim was checked against executed code, "
          "and every number in this document is produced by a script in the public repository. "
          "Where a result turned out weaker than first reported, the weaker number is the one "
          "published. Solo entry; full declaration in <b>docs/resource_declaration.md</b>.", "body"),
        Spacer(1, 3),
        P("Reproducibility: <b>pip install -e .</b> then four scripts regenerate every number and "
          "figure above; <b>pytest</b> runs 21 tests, four of which exist specifically to stop the "
          "defects described in §5 from coming back.", "cap"),
    ]

    doc.build(st)
    return doc.page


if __name__ == "__main__":
    pages = build()
    print("wrote %s — %d pages" % (OUT, pages))
    if pages > 5:
        raise SystemExit("OVER THE LIMIT: the hackathon allows 5 pages, this is %d" % pages)
