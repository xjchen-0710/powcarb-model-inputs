#!/usr/bin/env python3
"""Apply non-plotting scientific calculations to caller-supplied output tables.
No archived results are required or loaded implicitly. The output directory must be
new and outside the repository. See docs/ANALYSIS_INTERFACE.md for table schemas.
"""
from pathlib import Path
import argparse,json
import pandas as pd
from national_metrics import peak,factorial,contrast,FACTORS
from gamma_metrics import compute_outputs

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('mode',choices=['national','gamma'])
 p.add_argument('--input',required=True);p.add_argument('--out',required=True)
 a=p.parse_args();repo=Path(__file__).resolve().parents[1]
 src=Path(a.input).resolve();out=Path(a.out).resolve()
 if out.exists() or out==repo or repo in out.parents:raise ValueError('Choose a new output directory outside the repository.')
 d=pd.read_csv(src,float_precision='round_trip');tables={}
 if a.mode=='gamma':
  tables={k:pd.DataFrame(v) for k,v in compute_outputs(d.to_dict('records')).items()}
 else:
  need={'profile_id','year','emissions_t','reported_generation_cost_cny','average_generation_cost_cny_per_mwh',
        'coal_mwh','gas_mwh','wind_mwh','solar_mwh','hydro_mwh',*FACTORS}
  if need-set(d):raise ValueError('Missing columns: '+str(sorted(need-set(d))))
  if len(d)!=4608 or d.duplicated(['profile_id','year']).any():raise ValueError('Supply one complete 288-profile by 16-year treatment, not mixed treatments.')
  rows=[]
  for pid,g in d.groupby('profile_id'):
   if len(g[FACTORS].drop_duplicates())!=1:raise ValueError('Profile factors changed across years.')
   rows.append(dict(profile_id=int(pid),**peak(g),**{k:g.iloc[0][k] for k in FACTORS}))
  year=d[d.year==2035]
  tables['profile_metrics.csv']=pd.DataFrame(rows)
  tables['factorial_shares.csv']=pd.DataFrame(factorial(year,'emissions_t')+factorial(year,'average_generation_cost_cny_per_mwh'))
  tables['CQ3_CQ6_2035.csv']=contrast(year,'CQ3','CQ6')
  tables['CQ1_CQ2_2035.csv']=contrast(year,'CQ1','CQ2')
 out.mkdir(parents=True)
 for name,t in tables.items():t.to_csv(out/name,index=False)
 print(json.dumps({'tables':{n:len(t) for n,t in tables.items()},'solver_called':False,'published_archived_outputs_loaded':False},indent=2))
if __name__=='__main__':main()
