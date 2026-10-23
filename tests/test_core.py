"""Tests for the pieces every claim in the report rests on."""
import numpy as np
import pytest

from dntscout import chem
from dntscout.evaluation import (MondrianConformal, enrichment_curve, grouped_folds,
                                 random_baseline_ef, scaffold_groups)
from dntscout.models import Prevalence, ReadAcross, forest, logistic


def test_standardise_salt_and_mixture():
    salt = chem.standardise("CC(=O)[O-].[Na+]")          # sodium acetate: a salt
    assert salt.modellable and "salt_stripped" in salt.flags
    assert salt.smiles == "CC(=O)O"
    bad = chem.standardise("not a molecule")
    assert not bad.modellable and bad.flags == ("parse_failed",)
    empty = chem.standardise(None)
    assert empty.flags == ("no_structure",)


def test_standardise_is_canonical_and_keyed():
    a = chem.standardise("c1ccccc1O")
    b = chem.standardise("OC1=CC=CC=C1")
    assert a.smiles == b.smiles and a.inchikey == b.inchikey
    assert a.inchikey.startswith("ISWSIDIOOBJBQZ")           # phenol
    assert a.scaffold == "c1ccccc1"


def test_acyclic_gets_its_own_group():
    s = chem.standardise("CCCCO")
    assert "acyclic" in s.flags and s.scaffold.startswith("ACYCLIC::")


def test_features_and_similarity():
    smis = ["c1ccccc1O", "c1ccccc1OC", "CCCCCCO"]
    X, names = chem.feature_matrix(smis)
    assert X.shape == (3, 2048 + 167 + len(chem.DESCRIPTORS)) and len(names) == X.shape[1]
    sim = chem.tanimoto_matrix(smis, smis)
    assert np.allclose(np.diag(sim), 1.0, atol=1e-6)
    # phenol is closer to anisole than to hexanol
    assert sim[0, 1] > sim[0, 2]


def test_grouped_folds_never_split_a_scaffold():
    groups = scaffold_groups(["a", "a", "b", "b", "c", "c", "d", "d", "e", "e"])
    y = np.array([1, 0, 1, 0, 0, 0, 1, 0, 0, 0])
    folds = grouped_folds(groups, y, n_folds=5)
    assert len(folds) == 5
    for tr, te in folds:
        assert set(groups[tr]).isdisjoint(set(groups[te]))
        assert len(tr) + len(te) == len(y)
    # every chemical is tested exactly once
    tested = np.concatenate([te for _, te in folds])
    assert sorted(tested) == list(range(len(y)))


def test_grouped_folds_spread_positives():
    groups = scaffold_groups([f"g{i//2}" for i in range(20)])
    y = np.zeros(20, dtype=int)
    y[[0, 2, 4, 6, 8]] = 1                       # five positives in five different groups
    folds = grouped_folds(groups, y, n_folds=5)
    per_fold = [int(y[te].sum()) for _, te in folds]
    assert min(per_fold) >= 1, per_fold


def test_enrichment_perfect_and_random():
    y = np.array([1] * 10 + [0] * 90)
    perfect = enrichment_curve(np.concatenate([np.ones(10), np.zeros(90)]), y,
                               name="perfect", budgets=(10,), n_boot=200)
    assert perfect.hits_at[10] == 10
    assert perfect.tests_for[100] == 10
    assert perfect.ef_at[10] == pytest.approx(10.0)
    rnd = random_baseline_ef(y, budgets=(10,), n_rep=500)
    mean, lo, hi = rnd[10]
    assert lo <= 1.0 <= hi and mean == pytest.approx(1.0, abs=0.25)


def test_enrichment_no_positives_is_not_an_error():
    e = enrichment_curve(np.random.default_rng(0).random(20), np.zeros(20, dtype=int), n_boot=10)
    assert e.n_pos == 0 and e.tests_for == {}


def test_conformal_coverage_is_near_nominal():
    rng = np.random.default_rng(0)
    n = 4000
    y = rng.binomial(1, 0.25, n)
    # a usable but imperfect probability model
    p = np.clip(np.where(y == 1, rng.beta(6, 3, n), rng.beta(3, 6, n)), 1e-6, 1 - 1e-6)
    cal, test = slice(0, n // 2), slice(n // 2, n)
    cp = MondrianConformal(alpha=0.10).fit(p[cal], y[cal])
    sets, in_dom = cp.predict_set(p[test])
    rep = cp.report(sets, in_dom, y[test])
    assert 0.86 <= rep["coverage_all"] <= 0.96
    assert 0.84 <= rep["coverage_class_1"] <= 0.98
    assert 0.84 <= rep["coverage_class_0"] <= 0.98
    assert rep["share_singleton"] + rep["share_uninformative"] + rep["share_rejected"] == pytest.approx(1.0)


def test_applicability_domain_marks_out_of_domain():
    cp = MondrianConformal(alpha=0.1, ad_threshold=0.4).fit(np.array([0.9, 0.1]), np.array([1, 0]))
    _, in_dom = cp.predict_set(np.array([0.8, 0.8]), similarity=np.array([0.5, 0.2]))
    assert in_dom.tolist() == [True, False]


def test_read_across_recovers_analogue_labels():
    smis = ["c1ccccc1O", "c1ccccc1OC", "c1ccccc1C", "CCCCCCO", "CCCCCCCO", "CCCCCCCCO"]
    y = np.array([1, 1, 1, 0, 0, 0])
    sim = chem.tanimoto_matrix(smis, smis)
    out = []
    for i in range(len(smis)):                      # leave-one-out
        tr = [j for j in range(len(smis)) if j != i]
        ra = ReadAcross(k=3, min_sim=0.1).fit_sim(y[tr])
        out.append(ra.predict_proba1_sim(sim[[i]][:, tr])[0])
    out = np.array(out)
    assert (out[:3] > 0.5).all() and (out[3:] < 0.5).all(), out


def test_read_across_falls_back_without_analogues():
    ra = ReadAcross(k=3, min_sim=0.9).fit_sim(np.array([1, 0, 0, 0]))
    p = ra.predict_proba1_sim(np.array([[0.1, 0.1, 0.1, 0.1]]))
    assert p[0] == pytest.approx(0.25)              # training prevalence


def test_models_share_one_interface():
    rng = np.random.default_rng(0)
    X = rng.random((60, 12))
    y = (X[:, 0] + 0.1 * rng.standard_normal(60) > 0.5).astype(int)
    for m in (Prevalence(), logistic(1.0), forest(50, 2)):
        p = m.fit(X, y).predict_proba1(X)
        assert p.shape == (60,) and np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all()


def test_grouped_folds_balance_size_and_positives():
    """A fold holding most of the data would corrupt every per-fold model (regression test)."""
    rng = np.random.default_rng(0)
    groups = scaffold_groups([f"s{i}" for i in range(81)] * 1)
    groups = np.concatenate([groups, groups[:21]])          # 102 chemicals, 81 groups
    y = np.zeros(len(groups), dtype=int)
    y[rng.choice(len(groups), 49, replace=False)] = 1
    folds = grouped_folds(groups, y, n_folds=5)
    sizes = np.array([len(te) for _, te in folds])
    poss = np.array([int(y[te].sum()) for _, te in folds])
    assert sizes.max() <= 2 * sizes.min(), sizes
    assert sizes.sum() == len(y)
    assert poss.min() >= 1 and poss.max() <= 2 * max(poss.min(), 1), poss
    for tr, te in folds:
        assert set(groups[tr]).isdisjoint(set(groups[te]))


def test_prevalence_baseline_scores_near_chance():
    """With balanced folds, a per-fold prevalence model must sit near ROC 0.5."""
    from sklearn.metrics import roc_auc_score
    from dntscout.models import Prevalence
    rng = np.random.default_rng(1)
    groups = np.repeat(np.arange(80), 2)[:150]
    y = rng.binomial(1, 0.45, len(groups))
    X = rng.random((len(y), 3))
    oof = np.zeros(len(y))
    for tr, te in grouped_folds(groups, y, n_folds=5):
        oof[te] = Prevalence().fit(X[tr], y[tr]).predict_proba1(X[te])
    assert 0.3 <= roc_auc_score(y, oof) <= 0.7, roc_auc_score(y, oof)
