from pathlib import Path
import json, os
import pandas as pd

ROOT=Path(os.environ.get('PROJECT_ROOT',Path(__file__).resolve().parents[2]))

def test_processed_panel_exists_and_is_frozen():
    p=pd.read_csv(ROOT/'03_DATA'/'processed'/'model_panel_leakage_frozen.csv')
    assert len(p)==224
    assert p['year'].min()==1994 and p['year'].max()==2025
    assert p[['lag1','mean3','temp_lag1','temp_mean3']].notna().all().all()

def test_split_sizes_and_nonoverlap():
    files={n:pd.read_csv(ROOT/'03_DATA'/'processed'/f'split_{n}.csv') for n in ['development','calibration','future','spatial']}
    assert {k:len(v) for k,v in files.items()}=={'development':105,'calibration':20,'future':35,'spatial':14}
    assert set(files['future']['region']).isdisjoint(set(files['spatial']['region']))
    assert files['development']['year'].max()<files['calibration']['year'].min()<files['future']['year'].min()

def test_frozen_threshold_and_predictions():
    s=json.loads((ROOT/'05_RESULTS'/'main'/'analysis_summary.json').read_text())
    assert 0.5 < s['frozen_threshold'] < 3.0
    metrics=pd.read_csv(ROOT/'05_RESULTS'/'main'/'model_metrics.csv')
    pooled=metrics[metrics['split']=='pooled_external'].set_index('model')
    assert pooled.loc['CAFR','mae'] < pooled.loc['Persistence','mae']
    assert pooled.loc['Random forest','mae'] <= pooled.loc['CAFR','mae'] + 0.25

def test_all_holdout_pairs_present():
    s=pd.read_csv(ROOT/'05_RESULTS'/'supplementary'/'all_21_spatial_holdouts.csv')
    assert len(s)==21
    assert s[['Persistence_mae','CAFR_mae']].notna().all().all()

def test_no_target_year_climate_feature():
    p=pd.read_csv(ROOT/'03_DATA'/'processed'/'model_panel_leakage_frozen.csv')
    forbidden={'temp_anomaly_c','yield_current','target_temp'}
    assert forbidden.isdisjoint(set(p.columns))

def test_random_split_optimism_audit():
    a=pd.read_csv(ROOT/'05_RESULTS'/'main'/'random_vs_future_summary.csv').set_index('model')
    assert set(a.index)=={'Persistence','Ridge','Random forest','Gradient boosting','CAFR'}
    assert a.loc['CAFR','future_to_random_ratio'] > 1.15
    assert a['random_seeds'].eq(10).all()

def test_capacity_constrained_review_policy():
    a=pd.read_csv(ROOT/'05_RESULTS'/'main'/'capacity_constrained_review_audit.csv')
    c=a[(a['model']=='CAFR') & (a['review_capacity_per_year']==1)].iloc[0]
    assert c['review_n']==7
    assert abs(c['automatic_coverage'] - 6/7) < 1e-9
    assert c['absolute_error_capture_share'] > c['review_rate']

def test_exact_small_cluster_inference_and_review_randomization():
    y=pd.read_csv(ROOT/'05_RESULTS'/'main'/'exact_year_signflip_tests.csv').set_index('comparison')
    c=y.loc['CAFR minus Persistence']
    assert c['year_clusters']==7
    assert c['years_with_lower_mae']==4
    assert c['years_with_equal_mae']==3
    assert abs(c['exact_one_sided_p_lower']-0.0625)<1e-12
    r=pd.read_csv(ROOT/'05_RESULTS'/'main'/'exact_random_review_audit.csv').iloc[0]
    assert r['enumerated_random_policies']==7**7
    assert r['observed_capture_lift']>2.0
    assert r['exact_p_random_capture_at_least_observed']<1e-4

def test_review_sensitivity_across_spatial_holdouts():
    s=pd.read_csv(ROOT/'05_RESULTS'/'supplementary'/'all_21_spatial_holdouts.csv')
    assert (s['review_capture_lift']>1.0).all()
    assert s['review_capture_lift'].min()>2.0
    assert s['maximum_selected_region_share'].between(0,1).all()
