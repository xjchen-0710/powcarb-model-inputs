#!/usr/bin/env python3
"""Verify the inputs-only repository scope, checksums and numeric input contract.
No plotting libraries, solver, network or archived research outputs are required.
"""
from pathlib import Path,PurePosixPath
import argparse,csv,gzip,hashlib,itertools,json,re,subprocess,sys
import numpy as np
import pandas as pd
THERMAL_COLUMNS=['unit_id','year','record_id','province_id','is_gas','capacity_mw','fuel_kg_per_mwh','fuel_cny_per_mwh','emissions_t_per_mwh','quota_t_per_mwh']
PROVINCES=[f'P{i:02d}' for i in range(1,32)]
IGNORE={'.git','__pycache__'}

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def require(ok,message):
 if not ok:raise ValueError(message)
def manifest(path):
 ret={}
 for line in Path(path).read_text(encoding='utf-8').splitlines():
  if not line.strip():continue
  h,n=line.split('  ',1);q=PurePosixPath(n)
  require(re.fullmatch('[0-9a-f]{64}',h) and not q.is_absolute() and '..' not in q.parts and '\\' not in n and n not in ret,'Invalid checksum entry')
  ret[n]=h
 return ret

def verify_thermal(path,year,targets):
 t=pd.read_csv(path,float_precision='round_trip')
 require(list(t.columns)==THERMAL_COLUMNS,'Unexpected thermal fields: '+str(path.name))
 require(not t.isna().any().any(),'Missing thermal values')
 require(np.isfinite(t[THERMAL_COLUMNS[1:]].to_numpy(float)).all(),'Nonfinite thermal values')
 require(np.array_equal(t.record_id.to_numpy(),np.arange(1,len(t)+1)),'Noncontiguous record IDs')
 require(t.year.eq(year).all() and t.unit_id.is_unique,'Year/ID mismatch')
 require(t.unit_id.tolist()==[f'Y{year}U{i:04d}' for i in range(1,len(t)+1)],'Unexpected unit IDs')
 require(t.is_gas.isin([0,1]).all() and t.province_id.isin(range(1,32)).all(),'Invalid province/fuel flags')
 require(t.province_id.is_monotonic_increasing and t.province_id.nunique()==31,'Province record partition mismatch')
 require((t[['capacity_mw','fuel_kg_per_mwh','fuel_cny_per_mwh','emissions_t_per_mwh']]>0).all().all() and (t.quota_t_per_mwh>=0).all(),'Nonpositive/negative coefficients')
 a=t.groupby('province_id').capacity_mw.sum().reindex(range(1,32)).to_numpy()
 require(np.allclose(a,targets,rtol=1e-10,atol=1e-5),'Province capacity reconciliation failed')
 return len(t)
def verify_hourly(path):
 with gzip.open(path,'rt',encoding='utf-8-sig',newline='') as f:
  head=next(csv.reader(f));require(head==PROVINCES,'Hourly header must be P01..P31')
 rows=0
 for c in pd.read_csv(path,chunksize=2048,float_precision='round_trip'):
  x=c.to_numpy(float);require(x.shape[1]==31 and np.isfinite(x).all() and (x>=0).all(),'Invalid hourly values')
  rows+=len(c)
 require(rows==8760,'Hourly rows must equal 8760')
 return rows

def verify(root,git_index=False):
 root=Path(root).resolve();require((root/'RELEASE_STATUS.json').is_file(),'Not a model-inputs release')
 status=json.loads((root/'RELEASE_STATUS.json').read_text())
 require(status.get('declared_scope')=='model_code_and_inputs_only','Wrong declared release scope')
 require(status.get('precomputed_outputs_included') is False and status.get('plotting_code_included') is False,'Incorrect scope flags')
 signed=manifest(root/'SHA256SUMS.txt');files={p.relative_to(root).as_posix():p for p in root.rglob('*') if p.is_file() and not any(x in IGNORE for x in p.relative_to(root).parts)}
 require(set(files)==set(signed)|{'SHA256SUMS.txt'},'Unexpected/unlisted files in candidate; keep output, reports and environments outside the repo')
 require(not any(p.is_symlink() for p in root.rglob('*') if '.git' not in p.parts),'Symlinks are not accepted')
 blocked={'.png','.svg','.pdf','.jpg','.jpeg','.pptx','.xlsx','.xls','.mat','.npy','.npz','.pkl','.zip','.7z','.ttf','.otf','.woff','.woff2','.log'}
 for rel,p in files.items():
  require(p.stat().st_size<100*1024*1024,'File exceeds 100 MiB: '+rel)
  require(p.suffix.lower() not in blocked,'Excluded binary/plot/output file: '+rel)
  require(rel.split('/')[0] not in ['figures','results','outputs','build','.venv','AUTHOR_ONLY'],'Excluded tree: '+rel)
  if rel in signed:require(sha(p)==signed[rel],'Checksum mismatch: '+rel)
 data_expected=set()
 for year in range(2020,2036):
  data_expected|={f'data/model_inputs/thermal/{year}_CQ{q}_COP{c}.csv.gz' for q in range(1,7) for c in [1,2]}
  data_expected|={f'data/model_inputs/hourly/{year}_{re}_{field}.csv.gz' for re in ['RE1','RE2'] for field in ['wind','solar','hydro','nuclear']}
  data_expected.add(f'data/model_inputs/hourly/{year}_COMMON_load.csv.gz')
  data_expected|={f'data/network/capacity_mw/{year}_TL{tl}.csv' for tl in [1,2]}
 data_expected|={'data/model_inputs/thermal_index.csv','data/model_inputs/hourly_index.csv','data/network/capacity_index.csv','data/scenarios/scenario_registry_288.csv','data/scenarios/tasks_full288.csv','data/scenarios/reference_capacity_2020.csv','data/INPUTS_SHA256SUMS.txt'}
 require({r for r in files if r.startswith('data/')}==data_expected,'Input-only data whitelist mismatch')
 input_hashes=manifest(root/'data/INPUTS_SHA256SUMS.txt')
 require(set(input_hashes)==data_expected-{'data/INPUTS_SHA256SUMS.txt'},'Input hash scope mismatch')
 require(all(signed[p]==h for p,h in input_hashes.items()),'Input/repository hash manifests disagree')
 target=pd.read_csv(root/'data/scenarios/reference_capacity_2020.csv').sort_values('province_id')
 require(target.province_id.tolist()==list(range(1,32)),'Province capacity target index mismatch')
 thermal=0;hourly=0;network=0;record_counts={}
 for rel in sorted(data_expected):
  path=root/rel
  if '/thermal/' in rel:
   y=int(path.name[:4]);n=verify_thermal(path,y,target.reference_capacity_mw.to_numpy());thermal+=1
   if y in record_counts:require(record_counts[y]==n,'Same-year record counts differ across input slices')
   record_counts[y]=n
  elif '/hourly/' in rel:verify_hourly(path);hourly+=1
  elif '/capacity_mw/' in rel:
   a=pd.read_csv(path,index_col=0,float_precision='round_trip');v=a.to_numpy(float)
   require(a.index.tolist()==PROVINCES and list(a.columns)==PROVINCES and v.shape==(31,31),'Network labels/shape mismatch')
   require(np.isfinite(v).all() and (v>=0).all() and np.allclose(v,v.T,atol=0,rtol=0) and (np.diag(v)==0).all(),'Capacity matrix not finite nonnegative symmetric zero-diagonal')
   network+=1
 factors=['RE','CF','TL','CQ','CAP','COP'];registry=pd.read_csv(root/'data/scenarios/scenario_registry_288.csv')
 require(len(registry)==288 and registry.profile_id.nunique()==288,'Registry coverage failure')
 wanted=set(itertools.product(['RE1','RE2'],['CF1','CF2','CF3'],['TL1','TL2'],[f'CQ{i}' for i in range(1,7)],['CAP1','CAP2'],['COP1','COP2']))
 require(set(map(tuple,registry[factors].to_numpy()))==wanted,'Not the complete factorial product')
 tasks=pd.read_csv(root/'data/scenarios/tasks_full288.csv')
 require(len(tasks)==4608 and not tasks.duplicated(['profile_id','year']).any(),'Task identity failure')
 require(all(sorted(g.year.tolist())==list(range(2020,2036)) for _,g in tasks.groupby('profile_id')),'Task years incomplete')
 merged=tasks.merge(registry[['profile_id']+factors],on='profile_id',suffixes=('','_r'),validate='many_to_one')
 require(all(merged[x].eq(merged[x+'_r']).all() for x in factors),'Task factors disagree with registry')
 require(np.isfinite(tasks[['CarbonPrice','FL_SC','ATCrate']].to_numpy()).all(),'Invalid task scalars')
 require((tasks.CarbonPrice>=0).all() and (tasks.ets_active==(tasks.CarbonPrice>0)).all(),'ETS/price mismatch')
 require(tasks.FL_SC.isin([0,.3,.4]).all(),'Unknown minimum-output level')
 for kind,wanted_count in [('thermal',192),('hourly',144)]:
  idx=pd.read_csv(root/f'data/model_inputs/{kind}_index.csv');require(len(idx)==wanted_count and idx.file.nunique()==wanted_count,'Input index coverage failed')
  require(set(idx.file)=={x for x in data_expected if f'/{kind}/' in x},'Input index file list mismatch')
 require(not (root/'model/run_public_case.m').read_text().find('data/gamma')>=0,'Runner still depends on archived fixed-allowance output')
 # Direct sensitive path/secret patterns; input schemas already reject names/coordinates/output columns.
 pattern=re.compile('/lu'+'stre/home/|/ho'+'me/cxj/|'+r'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
 for rel,p in files.items():
  if not rel.startswith('data/') and p.suffix not in ['.gz']:
   require(not pattern.search(p.read_text(encoding='utf-8')),'Potential credential or private path: '+rel)
 if git_index:
  q=subprocess.run(['git','-C',str(root),'ls-files','--cached','-z'],check=True,capture_output=True)
  staged=set(q.stdout.decode().rstrip('\0').split('\0')) if q.stdout else set()
  require(staged==set(files),'Staged Git file set is not exactly the checked release')
 return dict(passed=True,scope='model_code_and_inputs_only',thermal_slices=thermal,hourly_arrays=hourly,capacity_matrices=network,profiles=288,annual_tasks=4608,checked_files=len(files),plotting_files=0,archived_results=0,plant_coordinates=0,full_model_runtime_tested=False,solver_called=False,remote_published=False)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',default=str(Path(__file__).resolve().parents[1]));p.add_argument('--report',required=True);p.add_argument('--git-index',action='store_true');a=p.parse_args()
 root=Path(a.repo).resolve();out=Path(a.report).resolve()
 require(out!=root and root not in out.parents,'Write report outside the public repository')
 try:r=verify(root,a.git_index)
 except Exception as e:
  r={'passed':False,'error':str(e),'solver_called':False};out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));raise SystemExit(1)
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':main()
