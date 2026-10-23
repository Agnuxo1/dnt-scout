import argparse, importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd
from rdkit import Chem,DataStructs
from rdkit.Chem import rdFingerprintGenerator
from independent_audit import balanced_groups, blind_groups, SEED
from calibrated_readacross import fit,predict,summary,self_test

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
    root,out=Path(a.root),Path(a.out); self_test()
    df=pd.read_parquet(out/'inputs/chemicals_labelled.parquet')
    df=df[df.y.notna() & df.structure_ok & df.smiles.notna()].reset_index(drop=True)
    y=df.y.to_numpy(int); g=pd.factorize(df.scaffold,sort=False)[0]
    gen=rdFingerprintGenerator.GetMorganGenerator(radius=2,fpSize=2048)
    fps=[gen.GetFingerprint(Chem.MolFromSmiles(s)) for s in df.smiles]
    sim=np.array([DataStructs.BulkTanimotoSimilarity(f,fps) for f in fps]); np.fill_diagonal(sim,0.)
    spec=importlib.util.spec_from_file_location('original_export',root/'scripts/score_candidates.py')
    export=importlib.util.module_from_spec(spec); spec.loader.exec_module(export)
    rep={'scope':'Retrospective exterior validation, original 102-chemical endpoint; original ranking result unchanged',
         'original_export':'k=3 LOO quantiles within each outer training set, not forest coverage',
         'candidate':'scaffold-disjoint fit/calibration before hyperparameter selection, conservative small-sample quantiles, same reference for domain'}
    rows=[]
    for seed in [SEED]+list(range(714001,714021)):
        for name in ('original_export','corrected_candidate'):
            sets=[set() for _ in y]; dom=np.zeros(len(y),bool); details=[]
            for f,(tr,te) in enumerate(balanced_groups(g,y,5,seed)):
                if name=='original_export':
                    train=sim[np.ix_(tr,tr)].copy(); np.fill_diagonal(train,1.)
                    q,_=export.conformal_quantiles(train,y[tr],3,.1)
                    threshold=float(np.percentile(np.sort(train,axis=1)[:,-2],10))
                    sq=sim[np.ix_(te,tr)]; idx=np.argsort(-sq,axis=1)[:,:3]; w=np.take_along_axis(sq,idx,axis=1)
                    p=(w*y[tr][idx]).sum(axis=1)/w.sum(axis=1)
                    ss=[{c for c in (0,1) if (1-z if c else z)<=q[c]} for z in p]
                    dd=sq.max(axis=1)>=threshold
                else:
                    state=fit(sim[np.ix_(tr,tr)],y[tr],g[tr],seed=seed+f+110)
                    result=predict(state,sim[np.ix_(te,tr)],y[tr]); ss,dd=result['prediction_sets'],result['in_domain']
                    details.append({'fold':f,'q':state['q'],'n_calibration_by_class':state['n_calibration_by_class']})
                    # Changing calibration labels must not change selected k or the proper-fit score.
                    yp=y[tr].copy(); yp[state['calibration']]=1-yp[state['calibration']]
                    s2=fit(sim[np.ix_(tr,tr)],yp,g[tr],seed=seed+f+110)
                    assert s2['choice']==state['choice']
                    r2=predict(s2,sim[np.ix_(te,tr)],yp)
                    assert np.array_equal(result['uncertainty_score'],r2['uncertainty_score'])
                for i,s in zip(te,ss): sets[i]=s
                dom[te]=dd
            row={'seed':seed,'method':name,**summary(sets,dom,y)}; rows.append(row)
            if seed==SEED: rep[name+'_original_outer_split']={**row,'fold_calibration':details}
    rep['repeat_20_new_seeds']={}
    for name in ('original_export','corrected_candidate'):
        z=[r for r in rows if r['method']==name and r['seed']!=SEED]
        rep['repeat_20_new_seeds'][name]={k:{'median':float(np.median([r[k] for r in z])),
            'min':float(min(r[k] for r in z)),'max':float(max(r[k] for r in z))} for k in ('coverage','coverage_0','coverage_1','uninformative','out_of_domain')}
    rep['checks']=['finite-sample boundary m=0,1,9','calibration labels do not select hyperparameters or affect proper-fit confidence scores','all proper-fit/calibration scaffold groups disjoint']
    (out/'calibration_results.json').write_text(json.dumps(rep,indent=2)); pd.DataFrame(rows).to_csv(out/'calibration_repeats.csv',index=False)
    print(json.dumps(rep,indent=2))

if __name__=='__main__': main()
