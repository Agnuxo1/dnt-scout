"""Independent audit. Does not import the project's CV, models, or audit engine.

Run from any directory: python independent_audit.py --root PATH --out PATH.
Observed results are never used to select the seeds or the model grid below.
"""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import time
import zipfile

os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
os.environ.setdefault('MKL_NUM_THREADS', '2')
import numpy as np
import pandas as pd
import scipy
from scipy.stats import rankdata, hypergeom, binomtest
from sklearn.metrics import roc_auc_score, average_precision_score
import sklearn
from rdkit import Chem, DataStructs, rdBase
from rdkit.Chem import rdFingerprintGenerator

SEED = 20261023
GRID = [(k, s) for k in (3, 5, 10, 20) for s in (0., .2, .3)]

def digest(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b)
    return h.hexdigest()

def balanced_groups(g, y, n=5, seed=SEED):
    """Independent implementation of the declared two-pass grouping rule."""
    ids = np.unique(g); np.random.default_rng(seed).shuffle(ids)
    counts = {v: (int(y[g == v].sum()), int((g == v).sum())) for v in ids}
    pos, size, assignment = [0]*n, [0]*n, {}
    for v in sorted((v for v in ids if counts[v][0]), key=lambda v: (-counts[v][0], -counts[v][1])):
        f = min(range(n), key=lambda j: (pos[j], size[j], j))
        assignment[v] = f; pos[f] += counts[v][0]; size[f] += counts[v][1]
    for v in sorted((v for v in ids if not counts[v][0]), key=lambda v: -counts[v][1]):
        f = min(range(n), key=lambda j: (size[j], pos[j], j))
        assignment[v] = f; size[f] += counts[v][1]
    return [(np.flatnonzero(np.array([assignment[v] for v in g]) != f),
             np.flatnonzero(np.array([assignment[v] for v in g]) == f)) for f in range(n)]

def blind_groups(g, y, n=5, seed=SEED):
    """Greedy group-size balance; never inspect labels to construct a split."""
    rng = np.random.default_rng(seed)
    ids = np.unique(g); rng.shuffle(ids)
    ids = sorted(ids, key=lambda v: -int((g == v).sum()))
    sizes, fo = np.zeros(n, int), np.zeros(len(g), int)
    for v in ids:
        j = int(np.argmin(sizes)); m = g == v; fo[m] = j; sizes[j] += m.sum()
    return [(np.flatnonzero(fo != f), np.flatnonzero(fo == f)) for f in range(n)]

def predict_many(s, y):
    """All 12 analogue choices, vectorised independently from ReadAcross."""
    order = np.argsort(-s, axis=1)
    outputs = []
    for k, floor in GRID:
        idx = order[:, :k]; w = np.take_along_axis(s, idx, axis=1)
        w = np.where(w >= floor, w, 0.)
        den = w.sum(axis=1, dtype=np.float64)
        num = (w * np.asarray(y, float)[idx]).sum(axis=1)
        outputs.append(np.divide(num, den, out=np.full(len(s), float(y.mean())), where=den > 0))
    return np.asarray(outputs)

def percentile_pool(p, fo):
    r = np.zeros(len(p))
    for f in np.unique(fo):
        m = fo == f; r[m] = rankdata(p[m], method='average') / (m.sum()+1)
    return r

def stats(y, p, fo):
    r = percentile_pool(p, fo)
    hits = y[np.argsort(-r, kind='stable')]
    need = int(np.ceil(y.sum()/2))
    pf = [roc_auc_score(y[fo == f], p[fo == f]) for f in np.unique(fo) if len(np.unique(y[fo == f])) == 2]
    return {'roc_rank': float(roc_auc_score(y,r)), 'roc_raw': float(roc_auc_score(y,p)),
            'roc_fold_mean': float(np.mean(pf)), 'ap_rank': float(average_precision_score(y,r)),
            'assays50': int(np.flatnonzero(np.cumsum(hits)>=need)[0]+1)}

def nested(sim, y, g, seed=SEED, split=balanced_groups):
    p, fo, choices = np.zeros(len(y)), np.full(len(y),-1), []
    for f, (tr,te) in enumerate(split(g,y,5,seed)):
        assert not set(g[tr]) & set(g[te])
        inner = np.zeros((len(GRID),len(tr)))
        for it,iv in split(g[tr],y[tr],3,SEED+1):
            inner[:,iv] = predict_many(sim[np.ix_(tr[iv],tr[it])], y[tr[it]])
        ap = [average_precision_score(y[tr], z) for z in inner]
        best = int(np.argmax(ap)); choices.append(GRID[best])
        p[te] = predict_many(sim[np.ix_(te,tr)],y[tr])[best]; fo[te] = f
    assert np.all(fo>=0)
    return p, fo, choices

def distribution(rows, key):
    v = np.array([r[key] for r in rows],float)
    return {'median':float(np.median(v)), 'p2.5':float(np.percentile(v,2.5)),
            'p97.5':float(np.percentile(v,97.5)), 'min':float(v.min()), 'max':float(v.max())}

def load_module(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--out',required=True)
    ap.add_argument('--permutations',type=int,default=999); a=ap.parse_args()
    root,out=Path(a.root),Path(a.out); out.mkdir(parents=True,exist_ok=True)
    t=time.time(); rep={'protocol':{'seed':SEED,'permutations':a.permutations,'new_split_seeds':list(range(714001,714101)),
        'permutation':'permute whole label vectors among scaffold groups of identical size; rerun outer split and all inner selection',
        'scope':'retrospective prioritisation of selective network activity within the declared 102-chemical endpoint'},
        'versions':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,
                    'sklearn':sklearn.__version__,'rdkit':rdBase.rdkitVersion}}
    # Fingerprints are rebuilt from structures, independently of the original feature code.
    df=pd.read_parquet(out/'inputs/chemicals_labelled.parquet')
    kept=df[df.y.notna() & df.structure_ok & df.smiles.notna()].reset_index(drop=True)
    y=kept.y.to_numpy(dtype=int); g=pd.factorize(kept.scaffold,sort=False)[0]
    gen=rdFingerprintGenerator.GetMorganGenerator(radius=2,fpSize=2048)
    fps=[gen.GetFingerprint(Chem.MolFromSmiles(s)) for s in kept.smiles]
    sim=np.array([DataStructs.BulkTanimotoSimilarity(f,fps) for f in fps],dtype=np.float32)
    np.fill_diagonal(sim,0)
    rep['data']={'n':len(y),'positive':int(y.sum()),'scaffold_groups':len(np.unique(g)),
        'singleton_groups':int(sum((g==v).sum()==1 for v in np.unique(g))),
        'duplicates_smiles':int(kept.smiles.duplicated().sum()),'duplicates_inchikey':int(kept.inchikey.duplicated().sum())}
    # Verify labels from the original Excel values, without invoking labels.py.
    raw=root/'data/raw'; manifest=json.loads((root/'docs/provenance.json').read_text())
    # Reuse the project's optional Excel reader without replacing installed NumPy/pandas.
    import sys
    sys.path.append(str(root/'.pylibs'))
    rep['input_hashes']={name:{'expected':r['sha256'],'observed':digest(raw/name)} for name,r in manifest['inputs'].items()}
    assert all(v['expected']==v['observed'] for v in rep['input_hashes'].values())
    params=('MFR','BR','ISI','%SiB','BD','IBI','#AE','#ABE','#NS','NSP','NSD','%SiNS','NS-ISI','NSDsd','#SiNS','r','MI')
    with zipfile.ZipFile(raw/'epa-shafer-2019-pasteur/NTP_TC_Analysis.zip') as z:
        fn=next(v for v in z.namelist() if v.endswith('All Compound Summary_correct names_updated_20181010.xlsx'))
        xl=pd.ExcelFile(io.BytesIO(z.read(fn))); rows=[]
        for en,vn in [('Tab 2-NTP AUC_EC50_summary','Tab 4-NTP Viability_EC50'),('Tab 3-TC AUC_EC50_summary','Tab 5-TC Viability_EC50')]:
            ec=xl.parse(en).dropna(subset=['Casrn']).drop_duplicates('Casrn')
            vi=xl.parse(vn).dropna(subset=['Casrn']).drop_duplicates('Casrn')
            rows.append(ec[['Casrn',*params]].merge(vi[['Casrn','AB cytotox','LDH cytotox']],on='Casrn',how='left'))
    v=pd.concat(rows).groupby('Casrn')[[*params,'AB cytotox','LDH cytotox']].min()
    v=v.apply(pd.to_numeric,errors='coerce'); net=v[list(params)].min(axis=1); cy=v[['AB cytotox','LDH cytotox']].min(axis=1)
    labels=np.where(net.isna(),'no_effect_observed',np.where(cy.isna() | (cy/net>=3),'selective','inconclusive_cytotox'))
    labs=dict(zip(v.index.astype(str),labels)); mismatch=[]
    for _,r in df.iterrows():
        want='inconclusive_other' if not r.structure_ok else labs[str(r.Casrn)]
        if r.label != want: mismatch.append(str(r.Casrn))
    rep['raw_label_rebuild']={'n':len(df),'mismatches':mismatch}; assert not mismatch
    p,fo,ch=nested(sim,y,g); rep['independent_original_split']={**stats(y,p,fo),'selected':ch}
    old=pd.read_csv(root/'results/out_of_fold_predictions.csv')
    assert kept.Casrn.astype(str).tolist()==old.Casrn.astype(str).tolist()
    rep['independent_original_split']['max_abs_prediction_difference']=float(np.max(np.abs(p-old.score_read_across)))
    assert rep['independent_original_split']['max_abs_prediction_difference'] < 1e-12, 'Independent reproduction must agree before further experiments'
    print('original',json.dumps(rep['independent_original_split']),flush=True)
    # Published 20 assignments are rerun; new 100 assignments address additional split variation.
    audit=json.loads((root/'results/audit/audit_02_validity.json').read_text())
    published=[]
    for s in [SEED+1000*i for i in range(20)]:
        pp,ff,_=nested(sim,y,g,s); published.append(stats(y,pp,ff))
    rep['published_20_reproduction']={k:distribution(published,k) for k in published[0]}
    rep['published_20_original_roc_values']=audit['B_repeated_cv']['read_across']['roc_rank']
    rep['published_20_max_auc_difference']=float(np.max(np.abs(np.array([r['roc_rank'] for r in published])-np.array(rep['published_20_original_roc_values']))))
    repeats={}; detail=[]
    for name,split in [('declared_group_balance',balanced_groups),('label_blind_group_balance',blind_groups)]:
        rows=[]
        for s in range(714001,714101):
            pp,ff,_=nested(sim,y,g,s,split); row=stats(y,pp,ff); rows.append(row)
            detail.append({'split':name,'seed':s,**row})
        repeats[name]={k:distribution(rows,k) for k in rows[0]}
        print(name,json.dumps(repeats[name]),flush=True)
    rep['new_100_splits_per_protocol']=repeats
    pd.DataFrame(detail).to_csv(out/'split_results.csv',index=False)
    (out/'partial.json').write_text(json.dumps(rep,indent=2))
    # Full refitting permutation test; group sizes preserved, no shuffling of a frozen prediction vector.
    rng=np.random.default_rng(800923); blocks={}
    for gg in np.unique(g): blocks.setdefault(int((g==gg).sum()),[]).append(np.flatnonzero(g==gg))
    null=[]
    for b in range(a.permutations):
        yp=y.copy()
        for size,inds in blocks.items():
            for target,source in zip(inds,rng.permutation(len(inds))): yp[target]=y[inds[source]]
        pp,ff,_=nested(sim,yp,g); null.append(stats(yp,pp,ff))
        if (b+1)%100==0: print('permutations',b+1,'elapsed',round(time.time()-t),flush=True)
    obs=rep['independent_original_split']
    rep['permutation_test']={'B':len(null),'n_at_least_observed_auc':int(sum(v['roc_rank']>=obs['roc_rank'] for v in null)),
        'auc_p_one_sided':float((1+sum(v['roc_rank']>=obs['roc_rank'] for v in null))/(1+len(null))),
        'assay_p_one_sided':float((1+sum(v['assays50']<=obs['assays50'] for v in null))/(1+len(null))),
        'null_auc':distribution(null,'roc_rank'),'null_assays':distribution(null,'assays50')}
    pd.DataFrame(null).to_csv(out/'permutation_results.csv',index=False)
    # Analytical random-order null is negative-hypergeometric: position of the 25th positive.
    need=int(np.ceil(y.sum()/2)); n=len(y); npos=int(y.sum())
    positions=np.arange(need,n+1); cdf=hypergeom.sf(need-1,n,npos,positions)
    rep['random_order_exact']={'mean_assays':need*(n+1)/(npos+1),'central95':[int(positions[np.argmax(cdf>=q)]) for q in (.025,.975)],
        'p_find_25_by_32':float(hypergeom.sf(need-1,n,npos,obs['assays50'])),
        'saving_fraction':float(1-obs['assays50']/(need*(n+1)/(npos+1)))}
    # Ties and row order: the pooled assay count must not depend materially on storage order.
    r=percentile_pool(p,fo); tie_counts=[]
    for _ in range(10000):
        order=np.lexsort((rng.random(n),-r)); tie_counts.append(int(np.flatnonzero(np.cumsum(y[order])>=need)[0]+1))
    rep['rank_tie_randomisation']={'min':min(tie_counts),'max':max(tie_counts),'median':float(np.median(tie_counts))}
    # Finite calibration sample boundary: ceil((m+1)*(1-alpha)) can exceed m.
    import sys
    sys.path.insert(0,str(root/'src'))
    from dntscout.evaluation import MondrianConformal
    cp= MondrianConformal(alpha=.1).fit(np.array([.2,.8]),np.array([0,1]))
    sets,_=cp.predict_set(np.array([.3])); correct={0,1}
    rep['conformal_small_sample_counterexample']={'calibration_n_each_class':1,'alpha':.1,'implemented_q':cp.q,
        'implemented_set':sorted(sets[0]),'required_conservative_set':sorted(correct),
        'explanation':'With one calibration observation per class, the required second order statistic is infinity; clipping it to the sole observed score is anti-conservative.'}
    # Coverage interval for the ACTUALLY evaluated forest; never transfer it to the export scorer.
    covered=np.array([str(int(yy)) in str(s) for yy,s in zip(y,old.conformal_set)])
    ci=binomtest(int(covered.sum()),n).proportion_ci()
    rep['observed_forest_coverage']={'covered':int(covered.sum()),'n':n,'fraction':float(covered.mean()),
        'binomial95_descriptive':[ci.low,ci.high], 'caveat':'Descriptive binomial interval ignores scaffold dependence; not a guarantee for exported read-across.'}
    # Data and code manifests allow future reproduction and drift detection.
    inputs=[Path(__file__),out/'inputs/chemicals_labelled.parquet',root/'results/out_of_fold_predictions.csv',root/'results/evaluation.json']
    inputs += list((root/'src/dntscout').glob('*.py'))+list((root/'scripts').glob('*.py'))
    rep['manifest']={str(f):digest(f) for f in inputs}
    rep['elapsed_s']=time.time()-t
    (out/'audit_results.json').write_text(json.dumps(rep,indent=2),encoding='utf-8')
    print('COMPLETE',json.dumps({'permutation':rep['permutation_test'],'random':rep['random_order_exact'],'elapsed_s':rep['elapsed_s']}),flush=True)

if __name__=='__main__': main()
