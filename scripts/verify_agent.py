"""Check the agent's headline claim instead of taking its word for it.

The SciencePal Biology Agent reported that doxylamine - a candidate our own external run threw
away as an unresolvable salt - scores 1.000 with a decisive {1} conformal set, and that its three
nearest measured analogues are diphenhydramine, tamoxifen and methadone, all selective. If that is
right it is the strongest single result of the ablation, so it gets verified here from the parent
structure, with our own code, before it goes anywhere near a report.

Also re-checks the swap the agent made on its own initiative: that oxytetracycline's nearest
measured analogue is tetracycline at T = 0.50 and shows no effect.
"""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "src")
from dntscout import chem  # noqa: E402

# parent structures, written out here so the check does not depend on any resolver
PARENTS = {
    "Doxylamine (parent of the succinate salt)": "CN(C)CCOC(C)(c1ccccc1)c1ccccn1",
    "Oxytetracycline (parent of the dihydrate)":
        "CN(C)[C@H]1[C@@H]2[C@@H](O)[C@H]3C(=C(O)[C@]2(O)C(=O)C(C(N)=O)=C1O)"
        "C(=O)c1c(O)cccc1[C@@]3(C)O",
    "Atorvastatin (parent of the calcium salt)":
        "CC(C)c1c(C(=O)Nc2ccccc2)c(-c2ccccc2)c(-c2ccc(F)cc2)n1CC[C@@H](O)C[C@@H](O)CC(=O)O",
}

df = pd.read_parquet("data/processed/chemicals_labelled.parquet")
kept = df[(df.y.notna()) & (df.structure_ok) & (df.smiles.notna())].reset_index(drop=True)
NM = "PREFERRED_NAME" if "PREFERRED_NAME" in kept.columns else "Compound"
y = kept.y.astype(int).to_numpy()
print("analogue table: %d chemicals, %d selective" % (len(kept), y.sum()))

for label, smi in PARENTS.items():
    from rdkit import Chem
    m = Chem.MolFromSmiles(smi)
    if m is None:
        print("\n%s: SMILES DID NOT PARSE - cannot verify" % label)
        continue
    std = chem.standardise(smi)
    sim = chem.tanimoto_matrix([std.smiles], kept.smiles.tolist())[0]
    order = np.argsort(-sim)[:3]
    w, lab = sim[order], y[order]
    score = float(np.average(lab, weights=w)) if w.sum() > 0 else float("nan")
    print("\n%s" % label)
    print("  formula %s | nearest-analogue Tanimoto %.3f" % (
        Chem.rdMolDescriptors.CalcMolFormula(std.smiles and Chem.MolFromSmiles(std.smiles)),
        sim.max()))
    for i in order:
        print("    %-36s T=%.3f  %s" % (str(kept[NM][i])[:36], sim[i],
                                        "selective" if y[i] else "no effect"))
    print("  read-across score (k=3, similarity-weighted) = %.4f" % score)
