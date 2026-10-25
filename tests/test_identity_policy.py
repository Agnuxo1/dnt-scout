"""Behavioural parity of core and portable scorer on salts and real mixtures."""
import importlib.util
from pathlib import Path
import pytest
from dntscout import chem

spec=importlib.util.spec_from_file_location("portable_score",Path(__file__).parents[1]/"scripts/score_candidates.py")
portable=importlib.util.module_from_spec(spec)
spec.loader.exec_module(portable)

@pytest.mark.parametrize("smiles,accepted",[
    ("CC(=O)[O-].[Na+]",True),
    ("O=C([O-])c1ccccc1.[Na+]",True),
    ("CCO.CCCCC",False),
    ("CN(C)CCOC(C)(c1ccccc1)c1ccccn1.O=C(O)CCC(=O)O",False),
    ("c1ccccc1O",True),
    ("[Na+].[Cl-]",False),
    ("not a molecule",False),
    (None,False),
])
def test_identity_policy_parity(smiles,accepted):
    core=chem.standardise(smiles)
    smi,flags=portable.standardise(smiles)
    portable_ok=smi is not None and not ({"multicomponent","no_carbon"}&set(flags))
    assert core.modellable==accepted
    assert portable_ok==accepted
    if accepted:
        assert core.smiles==smi
