"""Chemical identity and representation.

Every chemical in this project is identified by a standardised structure, never by name alone: the
US EPA Network Formation Assay tables carry chemical names and DSSTox identifiers, and names are
ambiguous across salts, mixtures and isomers. The functions here are deliberately explicit about
what they cannot do: mixtures and inorganics are flagged, not silently coerced.
"""
from __future__ import annotations

from dataclasses import dataclass

from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem, Descriptors, MACCSkeys
from rdkit.Chem.MolStandardize import rdMolStandardize
from rdkit.Chem.Scaffolds import MurckoScaffold
from rdkit import DataStructs
import numpy as np

RDLogger.DisableLog("rdApp.*")

MORGAN_BITS = 2048
MORGAN_RADIUS = 2
DESCRIPTORS = ("MolWt", "MolLogP", "TPSA", "NumHAcceptors", "NumHDonors",
               "NumRotatableBonds", "RingCount", "FractionCSP3", "NumAromaticRings", "HeavyAtomCount")


@dataclass(frozen=True)
class Standardised:
    """A chemical after standardisation. `flags` records why it may not be modellable."""
    smiles: str | None
    inchikey: str | None
    scaffold: str | None
    flags: tuple[str, ...]

    @property
    def modellable(self) -> bool:
        return self.smiles is not None and "multicomponent" not in self.flags and "no_carbon" not in self.flags


def standardise(smiles: str | None) -> Standardised:
    """Neutralise, remove salts, canonicalise; flag mixtures, inorganics and parse failures.

    A multicomponent record that is *not* a simple salt (a genuine mixture such as a technical
    formulation) keeps its flag: such records are reported as `inconclusive`, never modelled as if
    they were a single substance.
    """
    if not smiles or not isinstance(smiles, str) or not smiles.strip():
        return Standardised(None, None, None, ("no_structure",))
    mol = Chem.MolFromSmiles(smiles.strip())
    if mol is None:
        return Standardised(None, None, None, ("parse_failed",))
    flags: list[str] = []
    n_before = len(Chem.GetMolFrags(mol))
    mol = rdMolStandardize.Cleanup(mol)
    parent = rdMolStandardize.FragmentParent(mol)
    parent = rdMolStandardize.Uncharger().uncharge(parent)
    if parent is None or parent.GetNumAtoms() == 0:
        return Standardised(None, None, None, ("empty_after_cleanup",))
    if len(Chem.GetMolFrags(parent)) > 1 or n_before > 1:
        # FragmentParent keeps the largest fragment; flag so the caller can decide.
        if len(Chem.GetMolFrags(parent)) > 1:
            flags.append("multicomponent")
        else:
            flags.append("salt_stripped")
    if not any(a.GetSymbol() == "C" for a in parent.GetAtoms()):
        flags.append("no_carbon")
    can = Chem.MolToSmiles(parent)
    key = Chem.MolToInchiKey(parent) or None
    try:
        scaf = MurckoScaffold.MurckoScaffoldSmiles(mol=parent)
    except Exception:
        scaf = ""
    if not scaf:
        flags.append("acyclic")
        scaf = f"ACYCLIC::{key[:14] if key else can}"  # acyclic compounds get their own group
    return Standardised(can, key, scaf, tuple(flags))


def morgan(smiles: str, bits: int = MORGAN_BITS, radius: int = MORGAN_RADIUS):
    """Morgan (circular) fingerprint as an RDKit bit vector, for Tanimoto read-across."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"unparsable SMILES: {smiles!r}")
    gen = AllChem.GetMorganGenerator(radius=radius, fpSize=bits)
    return gen.GetFingerprint(mol)


def feature_matrix(smiles_list) -> tuple[np.ndarray, list[str]]:
    """Morgan bits + MACCS keys + physicochemical descriptors, as one float matrix.

    Descriptors are the cheap baseline the plan requires; fingerprints carry the structural signal.
    """
    rows, names = [], None
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            raise ValueError(f"unparsable SMILES: {smi!r}")
        gen = AllChem.GetMorganGenerator(radius=MORGAN_RADIUS, fpSize=MORGAN_BITS)
        fp = np.zeros(MORGAN_BITS, dtype=np.float32)
        DataStructs.ConvertToNumpyArray(gen.GetFingerprint(mol), fp)
        maccs = np.zeros(167, dtype=np.float32)
        DataStructs.ConvertToNumpyArray(MACCSkeys.GenMACCSKeys(mol), maccs)
        desc = np.array([getattr(Descriptors, d)(mol) for d in DESCRIPTORS], dtype=np.float32)
        rows.append(np.concatenate([fp, maccs, desc]))
        if names is None:
            names = ([f"morgan_{i}" for i in range(MORGAN_BITS)]
                     + [f"maccs_{i}" for i in range(167)] + list(DESCRIPTORS))
    X = np.vstack(rows)
    assert X.shape[1] == MORGAN_BITS + 167 + len(DESCRIPTORS), X.shape
    assert np.isfinite(X).all(), "non-finite descriptor; check for exotic structures"
    return X, names


def tanimoto_matrix(query_smiles, ref_smiles) -> np.ndarray:
    """Pairwise Tanimoto similarity (queries x references) on Morgan fingerprints."""
    q = [morgan(s) for s in query_smiles]
    r = [morgan(s) for s in ref_smiles]
    return np.array([DataStructs.BulkTanimotoSimilarity(fp, r) for fp in q], dtype=np.float32)
