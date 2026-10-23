"""Review candidate: separate ranking from split-conformal uncertainty.

No edits to the original scorer. Consume a query-to-reference Tanimoto matrix.
Choose hyperparameters only on the proper fitting subset, then calibrate on
disjoint scaffold groups. Prediction sets use the SAME fit model and reference
as calibration; ranking may use all reference labels, and is reported separately.
Scaffold shift still prevents an unconditional distribution-free guarantee.
"""
import numpy as np
from independent_audit import GRID, SEED, blind_groups, predict_many
from sklearn.metrics import average_precision_score

def conservative_quantile(scores, alpha=.1):
    s=np.asarray(scores,float)
    k=int(np.ceil((len(s)+1)*(1-alpha)))
    # Nonconformity is bounded by 1; infinity is equivalent to 1 in this setting.
    return 1. if k>len(s) else float(np.sort(s)[k-1])

def fit(sim,y,groups,seed=SEED,alpha=.1):
    sim,y,groups=np.asarray(sim),np.asarray(y,int),np.asarray(groups)
    proper,cal=blind_groups(groups,y,n=4,seed=seed)[0]
    if len(np.unique(y[proper]))<2:
        raise ValueError('Proper fitting subset needs both classes')
    assert set(groups[proper]).isdisjoint(groups[cal])
    # Hyperparameter selection never touches calibration labels.
    ps=np.zeros((len(GRID),len(proper)))
    for tr,va in blind_groups(groups[proper],y[proper],3,SEED+1):
        ps[:,va]=predict_many(sim[np.ix_(proper[va],proper[tr])],y[proper[tr]])
    j=int(np.argmax([average_precision_score(y[proper],p) for p in ps]))
    pcal=predict_many(sim[np.ix_(cal,proper)],y[proper])[j]
    q={c:conservative_quantile((1-pcal if c else pcal)[y[cal]==c],alpha) for c in (0,1)}
    threshold=float(np.percentile(sim[np.ix_(cal,proper)].max(axis=1),10))
    return {'proper':proper,'calibration':cal,'choice':j,'q':q,'domain_threshold':threshold,
            'n_calibration_by_class':{c:int((y[cal]==c).sum()) for c in (0,1)}}

def predict(state,sim_query,y_reference):
    y=np.asarray(y_reference,int); proper=state['proper']; j=state['choice']
    rank_score=predict_many(sim_query,y)[j]
    fit_sim=sim_query[:,proper]
    confidence_score=predict_many(fit_sim,y[proper])[j]
    sets=[{c for c in (0,1) if (1-p if c else p)<=state['q'][c]} for p in confidence_score]
    in_domain=fit_sim.max(axis=1)>=state['domain_threshold']
    return {'ranking_score':rank_score,'uncertainty_score':confidence_score,
            'prediction_sets':sets,'in_domain':in_domain}

def summary(sets,domain,y):
    y=np.asarray(y,int); size=np.array([len(s) for s in sets])
    hit=np.array([v in s for v,s in zip(y,sets)])
    return {'coverage':float(hit.mean()),'coverage_0':float(hit[y==0].mean()),
        'coverage_1':float(hit[y==1].mean()),'uninformative':float((size==2).mean()),
        'empty_set':float((size==0).mean()),'out_of_domain':float(1-np.mean(domain))}

def self_test():
    assert conservative_quantile([], .1)==1.
    assert conservative_quantile([.2], .1)==1.
    assert conservative_quantile([.2]*9,.1)==.2
    assert all(c in {c for c in (0,1) if (1-p if c else p)<=1.} for p in (0.,.3,1.) for c in (0,1))

if __name__=='__main__':
    self_test(); print('calibration boundary checks passed')
