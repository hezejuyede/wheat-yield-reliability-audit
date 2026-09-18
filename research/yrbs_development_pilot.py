"""Real-data DEVELOPMENT audit: SADC-2019 national records, 2017/2019 only.

This is a disclosed development pilot, NOT a 2023 confirmation and NOT an
accepted Registered Report. No later cycle is read. Fixed decisions are saved
before fitting. Public-use survey-design inference is approximate.
"""
from __future__ import annotations
import argparse, hashlib, io, json, os, platform, re, time, warnings
from pathlib import Path
import numpy as np
import pandas as pd
import scipy, sklearn, statsmodels.api as sm
from scipy.optimize import brentq
from scipy.special import expit, logit
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.exceptions import ConvergenceWarning
from joblib import Parallel, delayed

SEED=20260918
EPS=1e-7
MAP={'age':'age','sex':'sex','grade':'grade','race':'race7',
     'sleep':'qn88','bullied':'qn23','cyberbullied':'qn24','unsafe':'qn15',
     'fight':'qn17','activity':'qn78','pe':'qn81','sport':'qn82','y':'qn25'}
LABELS={'qn88':'8 or more hours of sleep','qn23':'bullied on school property',
'qn24':'electronically bullied','qn15':'felt unsafe','qn17':'physical fight',
'qn78':'60 minutes per day on 5 or more days','qn81':'classes on 1 or more days',
'qn82':'at least one sports team','qn25':'sad or hopeless'}
BLOCKS={'P0':[],'B0':['age','sex','grade','race']}
BLOCKS['B1']=BLOCKS['B0']+['sleep','bullied','cyberbullied','unsafe','fight']
BLOCKS['B2']=BLOCKS['B1']+['activity','pe']
BLOCKS['B3']=BLOCKS['B2']+['sport']
ALLOWED={'age':list(range(1,8)),'sex':[1,2],'grade':[1,2,3,4],'race':list(range(1,8))}
ALLOWED.update({x:[0,1] for x in ['sleep','bullied','cyberbullied','unsafe','fight','activity','pe','sport']})
RAW_RULES={'y':('q25',lambda a:a==1),'bullied':('q23',lambda a:a==1),
'cyberbullied':('q24',lambda a:a==1),'unsafe':('q15',lambda a:a>=2),
'fight':('q17',lambda a:a>=2),'activity':('q78',lambda a:a>=6),
'pe':('q81',lambda a:a>=2),'sport':('q82',lambda a:a>=2),
'sleep':('q88',lambda a:a>=5)}

def clean(o):
    if isinstance(o,dict):return {str(k):clean(v) for k,v in o.items()}
    if isinstance(o,(list,tuple)):return [clean(v) for v in o]
    if isinstance(o,(np.integer,)):return int(o)
    if isinstance(o,(np.floating,float)):return float(o) if np.isfinite(o) else None
    if isinstance(o,(np.bool_,)):return bool(o)
    return o

def write_json(p,o):p.write_text(json.dumps(clean(o),indent=2,allow_nan=False),encoding='utf-8')
def sh(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def avg(x,w):return float(np.average(x,weights=w))
def individual_loss(y,p):
    p=np.clip(np.asarray(p),EPS,1-EPS)
    return -(y*np.log(p)+(1-y)*np.log1p(-p))
def scores(y,p,w):
    ok=w>0;y=y[ok];p=p[ok];w=w[ok]
    return dict(n=len(y),events=int(y.sum()),weighted_prevalence=avg(y,w),
      predicted_mean=avg(p,w),log_loss=avg(individual_loss(y,p),w),
      brier=avg((y-p)**2,w),auroc=float(roc_auc_score(y,p,sample_weight=w)),
      average_precision=float(average_precision_score(y,p,sample_weight=w)))
def calibration(y,p,w):
    lp=logit(np.clip(p,EPS,1-EPS))
    ans={'calibration_in_large':None,'calibration_slope':None,'calibration_joint_intercept':None,'calibration_error':None}
    try:
        a=brentq(lambda x:avg(expit(lp+x),w)-avg(y,w),-40,40)
        ans['calibration_in_large']=a
        if np.ptp(lp)>1e-9:
            z=sm.GLM(y,sm.add_constant(lp),family=sm.families.Binomial(),freq_weights=w/w.mean()).fit(maxiter=100)
            if not z.converged:raise ValueError('Calibration failed')
            ans.update(calibration_joint_intercept=float(z.params[0]),calibration_slope=float(z.params[1]))
    except Exception as e:
        ans['calibration_error']=type(e).__name__+': '+str(e)
    return ans

def load_sources(root,out):
    receipt=json.loads((root/'source_receipt.json').read_text())
    assert receipt['complete'] and receipt['confirmation_2023_accessed'] is False
    layoutpath=root/'SADC2019_combined_layout.sps'
    assert sh(layoutpath)==receipt['layout_sha256']
    s=layoutpath.read_text(encoding='utf-8-sig')
    h=re.split(r'\bEXECUTE\s*\.',s,flags=re.I)[0]
    pairs=re.findall(r'\b([A-Za-z]\w*)\s+(\d+)\s*-\s*(\d+)\s*(\(A\))?',h)
    pos={v.lower():(int(a)-1,int(b)) for v,a,b,_ in pairs}
    labs=s.split('VARIABLE LABELS',1)[1].split('VALUE LABELS',1)[0]
    labels={v.lower():lab for v,lab in re.findall(r'(?m)^\s*(\w+)\s+"([^"]+)"',labs)}
    for v,fragment in LABELS.items():assert fragment.lower() in labels[v].lower(),(v,labels.get(v))
    allraw=list(dict.fromkeys(list(MAP.values())+['year','weight','stratum','psu','record','sitetypenum']+[v[0] for v in RAW_RULES.values()]))
    chunks=[];mapping=[];raw_checks=[]
    for year,n in [(2017,14765),(2019,13677)]:
        path=root/f'{year}_records_from_SADC2019.dat';b=path.read_bytes()
        assert sh(path)==receipt['selected_sha256'][str(year)]
        lines=b.splitlines();assert len(lines)==n and all(len(l)==859 for l in lines)
        raw=pd.DataFrame({v:[line[pos[v][0]:pos[v][1]].decode('ascii').strip() for line in lines] for v in allraw})
        raw=raw.replace('',np.nan).apply(pd.to_numeric,errors='raise')
        assert raw.year.eq(year).all() and raw.sitetypenum.eq(3).all()
        assert (raw.weight>0).all() and raw[['stratum','psu','record']].notna().all().all()
        d=pd.DataFrame({'year':year,'weight':raw.weight,'stratum':raw.stratum.astype(int),'psu':raw.psu.astype(int),'source_record':raw.record.astype(int)})
        d['record_id']=[f'{year}:{i}' for i in range(n)]
        for dest,v in MAP.items():
            x=raw[v]
            if v.startswith('qn'):
                assert set(x.dropna().unique())<=set([1,2]),(year,v,x.unique())
                d[dest]=x.map({1:1.0,2:0.0})
            else:
                assert set(x.dropna().unique())<=set(ALLOWED[dest]),(year,dest,x.unique())
                d[dest]=x
        for dest,(rv,rule) in RAW_RULES.items():
            mask=d[dest].notna() & raw[rv].notna()
            mismatch=int((d.loc[mask,dest].astype(int).to_numpy()!=rule(raw.loc[mask,rv]).astype(int).to_numpy()).sum())
            raw_checks.append({'year':year,'construct':dest,'paired_nonmissing':int(mask.sum()),'mismatches':mismatch})
            assert mismatch==0,(year,dest,mismatch)
        chunks.append(d)
    for k,v in MAP.items():mapping.append({'construct':k,'combined_field':v,'start_1based':pos[v][0]+1,'end_1based':pos[v][1],'official_label':labels[v]})
    pd.DataFrame(mapping).to_csv(out/'combined_mapping.csv',index=False)
    pd.DataFrame(raw_checks).to_csv(out/'raw_binary_concordance.csv',index=False)
    d=pd.concat(chunks,ignore_index=True)
    assert not d.record_id.duplicated().any()
    d.to_csv(out/'canonical_development.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    return d,receipt

def design_cells(g):
    cells=[]
    for _,part in g.groupby('stratum',sort=True):
        ids=part.index.to_numpy();u=part.psu.to_numpy();levels,inv=np.unique(u,return_inverse=True)
        if len(levels)<2:raise ValueError('Singleton public stratum')
        cells.append((ids,inv,len(levels)))
    return cells

def rw(cells,n,rng):
    m=np.zeros(n)
    for ids,inv,k in cells:
        ct=np.bincount(rng.integers(k,size=k-1),minlength=k)
        m[ids]=ct[inv]*k/(k-1)
    return m

def model(family):
    if family=='logistic':return LogisticRegression(penalty=None,solver='lbfgs',tol=1e-8,max_iter=4000)
    if family=='elastic_net':return LogisticRegression(penalty='elasticnet',l1_ratio=.5,C=.5,solver='saga',tol=1e-5,max_iter=5000,random_state=SEED)
    return HistGradientBoostingClassifier(max_iter=100,learning_rate=.05,max_leaf_nodes=15,min_samples_leaf=40,l2_regularization=1,early_stopping=False,random_state=SEED)

def fit_predict(x,y,w,xt,family='logistic'):
    if np.unique(y[w>0]).size!=2:raise ValueError('Outcome degeneracy')
    est=model(family)
    with warnings.catch_warnings():
        warnings.simplefilter('error',ConvergenceWarning)
        est.fit(x,y,sample_weight=w/w.mean())
    return est.predict_proba(xt)[:,1],est

def main(root,out,reps):
    start=time.time();out.mkdir(exist_ok=False,parents=True)
    plan={'type':'disclosed DEVELOPMENT pilot, not confirmatory','train':2017,'test':2019,
     'no_2021_or_2023_access':True,'source':'official national SADC2019 combined archive',
     'race_coding':'official seven-category race7; not annual eight-category raceeth',
     'categories':'fixed official codebook levels, not learned from evaluation outcomes',
     'primary_family':'unpenalized logistic','sensitivity_families':['elastic_net','hist_gradient_boosting'],
     'domains':{'activity':BLOCKS['B2'],'sport':BLOCKS['B3']},'bootstrap_reps':reps,'seed':SEED,
     'CI':'developmental full-refit rescaled-PSU percentile interval; not final 3999-run confirmation',
     'bootstrap_failures':'retained; >5% within contrast withholds that interval',
     'cross_validation':'5-fold stratified-group OOF inside each development year, logistic only',
     'exploratory_subgroup':'sex-specific 2019 paired scores, no hypothesis tests or model selection'}
    write_json(out/'PILOT_PLAN.json',plan)
    df,receipt=load_sources(root,out)
    flow=[];missing=[];excluded=[];all_metrics=[];contrasts=[];boots=[];failures=[];predictions=[];cvrows=[];subgroups=[];agreement=[];binrows=[]
    for year,g in df.groupby('year'):
        for col in list(MAP):
            ok=g[col].notna();w=g.loc[ok,'weight'].to_numpy();x=g.loc[ok,col].to_numpy()
            missing.append({'year':year,'variable':col,'n_valid':int(ok.sum()),'n_missing':int((~ok).sum()),'mean_among_valid':avg(x,w) if len(x) else None})
    universes={year:g.reset_index(drop=True) for year,g in df.groupby('year')}
    cells={year:design_cells(g) for year,g in universes.items()}
    for dom,features in [('activity',BLOCKS['B2']),('sport',BLOCKS['B3'])]:
        masks={year:g[['y']+features].notna().all(axis=1).to_numpy() for year,g in universes.items()}
        for year,g in universes.items():
            mask=masks[year];q=g.loc[mask];h=g[['stratum','psu']].drop_duplicates()
            flow.append(dict(domain=dom,year=year,raw_n=len(g),complete_n=len(q),events=int(q.y.sum()),
              weighted_prevalence=avg(q.y,q.weight),unweighted_retention=len(q)/len(g),weighted_retention=float(q.weight.sum()/g.weight.sum()),
              raw_strata=int(g.stratum.nunique()),raw_psus=len(h),domain_psus=len(q[['stratum','psu']].drop_duplicates()),
              kish_weight_n=float(q.weight.sum()**2/np.square(q.weight).sum())))
            for variable in ['y','sex','age','race']:
                for retained in [True,False]:
                    k=g.loc[(mask==retained)&g[variable].notna()]
                    if len(k):
                        for category in sorted(k[variable].unique()):
                            excluded.append({'domain':dom,'year':year,'variable':variable,'category':category,'included':retained,'n':len(k),'weighted_fraction':avg(k[variable].eq(category),k.weight)})
        tr=universes[2017].loc[masks[2017]];te=universes[2019].loc[masks[2019]]
        yr=tr.y.to_numpy(dtype=int);yt=te.y.to_numpy(dtype=int);wr=tr.weight.to_numpy();wt=te.weight.to_numpy()
        names=['B0','B1','B2']+(['B3'] if dom=='sport' else [])
        matrices={};models={};pp={}
        p0=np.repeat(avg(yr,wr),len(te));pp['P0']=p0
        metric={'domain':dom,'model':'P0','family':'prevalence','evaluation':'2017_to_2019',**scores(yt,p0,wt),**calibration(yt,p0,wt)};all_metrics.append(metric)
        for name in names:
            fs=BLOCKS[name];enc=OneHotEncoder(categories=[ALLOWED[v] for v in fs],drop='first',handle_unknown='error',sparse_output=False)
            xr=enc.fit_transform(tr[fs]);xt=enc.transform(te[fs]);matrices[name]=(xr,xt)
            p,est=fit_predict(xr,yr,wr,xt);pp[name]=p;models[name]=est
            all_metrics.append({'domain':dom,'model':name,'family':'logistic','evaluation':'2017_to_2019',**scores(yt,p,wt),**calibration(yt,p,wt)})
            predictions.append(pd.DataFrame({'record_id':te.record_id,'domain':dom,'model':name,'family':'logistic','year':2019,'y':yt,'weight':wt,'probability':p}))
            if name in ['B1','B2'] or (dom=='sport' and name=='B3'):
                for fam in ['elastic_net','hist_gradient_boosting']:
                    p2,_=fit_predict(xr,yr,wr,xt,fam)
                    all_metrics.append({'domain':dom,'model':name,'family':fam,'evaluation':'2017_to_2019',**scores(yt,p2,wt),**calibration(yt,p2,wt)})
            if dom=='activity' and name in ['B1','B2']:
                independent=sm.GLM(yr,sm.add_constant(xr,has_constant='add'),family=sm.families.Binomial(),freq_weights=wr/wr.mean()).fit(maxiter=150,tol=1e-10)
                ip=independent.predict(sm.add_constant(xt,has_constant='add'))
                diff=float(np.max(np.abs(ip-p)))
                agreement.append({'domain':dom,'model':name,'max_abs_prediction_difference':diff,'independent_converged':bool(independent.converged)})
                assert diff<2e-4 and independent.converged
        pairs=[('activity_increment','B2','B1')] if dom=='activity' else [('sport_increment','B3','B2')]
        for contrast,aug,base in pairs:
            contrasts.append({'domain':dom,'contrast':contrast,'estimate':avg(individual_loss(yt,pp[aug])-individual_loss(yt,pp[base]),wt),
              'delta_auroc':scores(yt,pp[aug],wt)['auroc']-scores(yt,pp[base],wt)['auroc'],
              'delta_brier':avg((yt-pp[aug])**2-(yt-pp[base])**2,wt)})
            for sex in [1,2]:
                k=te.sex.to_numpy()==sex
                subgroups.append({'domain':dom,'contrast':contrast,'sex_code':sex,'n':int(k.sum()),'delta_log_loss':avg(individual_loss(yt[k],pp[aug][k])-individual_loss(yt[k],pp[base][k]),wt[k])})
            ar,at=matrices[aug];br,bt=matrices[base]
            def replicate(b):
                rng=np.random.default_rng(SEED+b)
                wbr=wr*rw(cells[2017],len(universes[2017]),rng)[masks[2017]]
                wbt=wt*rw(cells[2019],len(universes[2019]),rng)[masks[2019]]
                try:
                    pa,_=fit_predict(ar,yr,wbr,at);pb,_=fit_predict(br,yr,wbr,bt)
                    return {'domain':dom,'contrast':contrast,'replicate':b,'estimate':avg(individual_loss(yt,pa)-individual_loss(yt,pb),wbt),'error':None}
                except Exception as e:return {'domain':dom,'contrast':contrast,'replicate':b,'estimate':None,'error':type(e).__name__+': '+str(e)}
            result=Parallel(n_jobs=2)(delayed(replicate)(i) for i in range(reps));boots.extend(result)
            valid=[r['estimate'] for r in result if r['error'] is None];bad=[r for r in result if r['error'] is not None];failures.extend(bad)
            c=contrasts[-1];c.update(replicates_requested=reps,replicates_valid=len(valid),failures=len(bad))
            if len(bad)/reps<=.05:
                c.update(ci95_low=float(np.quantile(valid,.025)),ci95_high=float(np.quantile(valid,.975)),bootstrap_sd=float(np.std(valid,ddof=1)))
            else:c.update(ci95_low=None,ci95_high=None,bootstrap_sd=None)
        # OOF evidence remains internal developmental validation; all learners fixed.
        for year,g in [(2017,tr),(2019,te)]:
            y=g.y.to_numpy(dtype=int);w=g.weight.to_numpy();group=g.stratum.astype(str)+'::'+g.psu.astype(str)
            folds=list(StratifiedGroupKFold(5,shuffle=True,random_state=SEED).split(np.zeros(len(g)),y,group))
            for name in (['B1','B2'] if dom=='activity' else ['B2','B3']):
                fs=BLOCKS[name];pc=np.full(len(g),np.nan)
                for idx,jdx in folds:
                    assert set(group.iloc[idx]).isdisjoint(set(group.iloc[jdx]))
                    enc=OneHotEncoder(categories=[ALLOWED[v] for v in fs],drop='first',handle_unknown='error',sparse_output=False)
                    x=enc.fit_transform(g.iloc[idx][fs]);xt=enc.transform(g.iloc[jdx][fs]);pc[jdx],_=fit_predict(x,y[idx],w[idx],xt)
                cvrows.append({'domain':dom,'year':year,'model':name,'method':'5_fold_PSU_OOF',**scores(y,pc,w)})
        for name,p in pp.items():
            labels=np.minimum((p*10).astype(int),9)
            for binid in range(10):
                k=labels==binid
                if k.any():binrows.append({'domain':dom,'model':name,'bin':binid,'n':int(k.sum()),'weighted_predicted':avg(p[k],wt[k]),'weighted_observed':avg(yt[k],wt[k])})
        print('DOMAIN_DONE',dom,'seconds',round(time.time()-start,2),flush=True)
    tables={'sample_flow':flow,'item_availability':missing,'included_excluded':excluded,'model_metrics':all_metrics,'paired_contrasts':contrasts,'bootstrap_draws':boots,'bootstrap_failures':failures,'group_cv_metrics':cvrows,'subgroup_exploratory':subgroups,'numerical_crosscheck':agreement,'calibration_bins':binrows}
    for name,rows in tables.items():pd.DataFrame(rows).to_csv(out/(name+'.csv'),index=False)
    pd.concat(predictions).to_csv(out/'predictions.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    status={'status':'COMPLETED_DEVELOPMENT_ONLY','synthetic':False,'train_year':2017,'evaluation_year':2019,'raw_record_count':len(df),
            'source':'official SADC2019 NATIONAL archive; extracted full 2017/2019 records','confirmation_2023_accessed':False,
            'nsch_run':False,'bootstrap_replicates_per_contrast':reps,'seconds':time.time()-start,
            'versions':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__,'sklearn':sklearn.__version__},
            'script_sha256':sh(Path(__file__))}
    write_json(out/'RUN_STATUS.json',status)
    summary={**status,'sample_flow':flow,'paired_contrasts':contrasts,'model_metrics':all_metrics,'group_cv_metrics':cvrows,'numerical_crosscheck':agreement,'subgroup_exploratory':subgroups,'calibration_bins':binrows,'item_availability':missing,'included_excluded':excluded}
    write_json(out/'RESULT_SUMMARY.json',summary)
    print('BEGIN_DEVELOPMENT_RESULT_SUMMARY',flush=True);print(json.dumps(clean(summary),allow_nan=False),flush=True);print('END_DEVELOPMENT_RESULT_SUMMARY',flush=True)
    print('BEGIN_ITEM_AVAILABILITY',flush=True);print(pd.DataFrame(missing).to_csv(index=False),flush=True);print('END_ITEM_AVAILABILITY',flush=True)
    for label in ['paired_contrasts','sample_flow','calibration_bins','group_cv_metrics','numerical_crosscheck','model_metrics','item_availability','included_excluded','subgroup_exploratory']:
        b=(out/(label+'.csv')).read_bytes();print('RESULT_FILE_SHA256',label+'.csv',hashlib.sha256(b).hexdigest())
        print('BEGIN_RESULT_CSV '+label,flush=True);print(b.decode(),end='',flush=True);print('END_RESULT_CSV '+label,flush=True)
    manifest=[{'path':str(p.relative_to(out)),'bytes':p.stat().st_size,'sha256':sh(p)} for p in sorted(out.rglob('*')) if p.is_file()]
    write_json(out/'MANIFEST.json',manifest)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--source',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--bootstrap',type=int,default=399)
    ns=a.parse_args();assert ns.bootstrap>=99
    main(ns.source,ns.out,ns.bootstrap)
