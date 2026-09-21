"""Scientific functions from the release analysis. No archived result files are loaded.
Input tables must be generated or supplied by the caller. No plotting code.
"""
from pathlib import Path
import itertools,json
import numpy as np,pandas as pd
FACTORS=['RE','CF','TL','CQ','CAP','COP']

def peak(g,tol=1000.):
 g=g.sort_values('year');y=g.year.to_numpy();e=g.emissions_t.to_numpy()
 if not np.array_equal(y,np.arange(2020,2036)):raise ValueError('A complete 16-year path is required')
 slope=np.polyfit(np.arange(5),e[-5:],1)[0]
 return dict(peak_year=int(y[e.argmax()]),peak_emissions_t=float(e.max()),emissions_2035_t=float(e[-1]),cumulative_emissions_t=float(e.sum()),last5_slope_t_per_year=float(slope),agreed_peak_success=bool(e[11:].max()<e[:11].max()-tol and slope<0),peak_to_2035_decline=float(1-e[-1]/e.max()))

def factorial(df,metric):
 assert len(df)==288 and len(df[FACTORS].drop_duplicates())==288
 v=df[metric].to_numpy();mean=v.mean();variance=np.mean((v-mean)**2);parts={};rows=[]
 for order in range(1,7):
  for subset in itertools.combinations(FACTORS,order):
   e=df.groupby(list(subset),observed=True)[metric].transform('mean').to_numpy()-mean
   for k in range(1,order):
    for low in itertools.combinations(subset,k):e-=parts[low]
   parts[subset]=e;rows.append(dict(metric=metric,factors='*'.join(subset),order=order,variance_share=float(np.mean(e**2)/variance)))
 assert np.isclose(sum(r['variance_share'] for r in rows),1,atol=1e-10)
 return rows

def contrast(d,c,t):
 keys=[x for x in FACTORS if x!='CQ'];m=d[d.CQ==c].merge(d[d.CQ==t],on=keys,suffixes=('_control','_treatment'),validate='one_to_one');assert len(m)==48
 out=m[keys+['profile_id_control','profile_id_treatment']].copy()
 for col in ['emissions_t','reported_generation_cost_cny','coal_mwh','gas_mwh','wind_mwh','solar_mwh','hydro_mwh']:
  out['delta_'+col]=m[col+'_treatment']-m[col+'_control']
 out['emissions_change_pct']=100*out.delta_emissions_t/m.emissions_t_control
 out['reported_cost_change_pct']=100*out.delta_reported_generation_cost_cny/m.reported_generation_cost_cny_control
 return out

