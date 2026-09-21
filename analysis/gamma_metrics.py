"""Predeclared peak, crowding, cumulative and allocation comparisons. No fitting to outcomes."""
from __future__ import annotations
import math
from collections import defaultdict
from common import require,close
METRICS=('emissions_t','free_quota_t','raw_net_deficit_t','coal_mwh','gas_mwh','wind_mwh','solar_mwh','hydro_mwh','wsh_mwh','wsh_utilization_fraction',
 'wind_curtailment_mwh','solar_curtailment_mwh','hydro_curtailment_mwh','fuel_cost_cny','fixed_thermal_om_cny','net_carbon_cost_cny','reported_generation_cost_cny','svg_mwh','dvg_mwh')

def slope(ys,v):
    x=math.fsum(ys)/len(ys);m=math.fsum(v)/len(v)
    return math.fsum((a-x)*(b-m) for a,b in zip(ys,v))/math.fsum((a-x)**2 for a in ys)

def peak_metrics(rr,epsilon_t=1000.):
    rr=sorted(rr,key=lambda x:int(x['year']));ys=[int(x['year']) for x in rr]
    require(ys==list(range(2020,2036)),'必须16个连续年度，不能从端点插值或缺年判达峰')
    e=[float(x['emissions_t']) for x in rr];require(all(math.isfinite(x) and x>0 for x in e),'排放应为有限正数')
    pre=max(e[:11]);post=max(e[11:]);m=max(e);first=ys[e.index(m)];depth=1-e[-1]/m
    last=max(y for y,z in zip(ys,e) if m-z<=epsilon_t)
    final5=slope(ys[-5:],e[-5:]); final3=slope(ys[-3:],e[-3:])
    time_ok=post<pre-epsilon_t;trend_ok=final5<0
    failures=[]
    if not time_ok:failures.append('post2030_reaches_or_exceeds_pre2031_peak')
    if not trend_ok:failures.append('final_five_year_trend_not_negative')
    return dict(peak_success=time_ok and trend_ok,peak_rule_not_met=not(time_ok and trend_ok),failure_components=';'.join(failures),
      peak_year_first_exact_max=first,peak_year_last_within_tolerance=last,peak_emissions_t=m,pre2031_peak_t=pre,post2030_max_t=post,
      post_minus_pre_peak_t=post-pre,emissions_2030_t=e[10],emissions_2035_t=e[-1],terminal_decline_fraction=depth,
      terminal_decline_ge_1pct=depth>=.01,terminal_decline_ge_5pct=depth>=.05,terminal_decline_ge_10pct=depth>=.10,
      peak_to_2035_compound_annual_decline=1-(e[-1]/m)**(1/(2035-first)) if first<2035 else None,
      last3_slope_t_per_year=final3,last5_slope_t_per_year=final5,
      post2030_all_below_2030=max(e[11:])<e[10]-epsilon_t,
      post2030_nonincreasing=all(e[i]<=e[i-1]+epsilon_t for i in range(11,16)),
      cumulative_emissions_2020_2035_t=math.fsum(e),cumulative_emissions_2023_2035_t=math.fsum(e[3:]),
      tolerance_t=epsilon_t,observation_window='2020-2035',proof_of_2060_failure=False)

def strict_delta(a,b):return {k:float(a[k])-float(b[k]) for k in METRICS}

def compute_outputs(cells):
    require(len(cells)==192,'不是完整192单元')
    by={(int(r['profile_id']),int(r['year']),r['path_nominal_allocation'],int(r['path_nominal_gamma'])):r for r in cells}
    require(len(by)==192,'存在重复路径单元')
    groups=defaultdict(list)
    for r in cells:groups[(int(r['profile_id']),r['path_nominal_allocation'],int(r['path_nominal_gamma']))].append(r)
    require(len(groups)==12,'不是预先定义12路径')
    peaks=[];epsrows=[];deltas=[];inter=[];cumulative=[];coincidence=[];comparison=[]
    for (p,m,g),rs in sorted(groups.items()):
        info={'profile_id':p,'allocation_mode_from_2023':m,'gamma_from_2023':g}
        primary={**info,**peak_metrics(rs,1000)};peaks.append(primary)
        for eps in (0.,1.,1000.):epsrows.append({**info,**peak_metrics(rs,eps)})
        baseline=groups[p,'OBA',1]
        fixed=groups[p,'FIXED',g]
        basepeak=peak_metrics(baseline);fixpeak=peak_metrics(fixed)
        comparison.append({**info,'reference_oba1_peak_success':basepeak['peak_success'],'this_peak_success':primary['peak_success'],
            'sameprice_fixed_peak_success':fixpeak['peak_success'],'incremental_failure_vs_oba1':basepeak['peak_success'] and not primary['peak_success'],
            'oba_only_failure_at_same_price':m=='OBA' and not primary['peak_success'] and fixpeak['peak_success'],
            'not_a_causal_mediation_proof':True})
    for p in (15,42):
      for y in range(2020,2036):
       for g in (1,5,10):
        o,f=by[p,y,'OBA',g],by[p,y,'FIXED',g];o1,f1=by[p,y,'OBA',1],by[p,y,'FIXED',1]
        deltas.append({'contrast':'OBA_minus_FIXED_same_price','profile_id':p,'year':y,'gamma':g,**strict_delta(o,f)})
        for mode,a,b in [('OBA',o,o1),('FIXED',f,f1)]:
            d=strict_delta(a,b);deltas.append({'contrast':mode+'_minus_same_rule_gamma1','profile_id':p,'year':y,'gamma':g,**d})
            coincidence.append({'profile_id':p,'year':y,'allocation':mode,'gamma':g,
                'coal_change_mwh':d['coal_mwh'],'gas_change_mwh':d['gas_mwh'],'wsh_change_mwh':d['wsh_mwh'],
                'emissions_change_t':d['emissions_t'],'coal_up_and_wsh_down_annual':d['coal_mwh']>1000 and d['wsh_mwh']<-1000,
                'screen_tolerance_mwh':1000,'proof_of_exclusive_clean_displacement_mediation':False})
        inter.append({'profile_id':p,'year':y,'gamma':g,'definition':'(OBA_g-OBA_1)-(FIXED_g-FIXED_1)',
                      **{k:(float(o[k])-float(o1[k]))-(float(f[k])-float(f1[k])) for k in METRICS}})
    dd=defaultdict(list)
    for r in deltas:dd[(r['contrast'],r['profile_id'],r['gamma'])].append(r)
    for key,rr in sorted(dd.items()):
        require(len(rr)==16,'严格配对缺年')
        for start in (2020,2023):
            q=[x for x in rr if x['year']>=start]
            sums={k:math.fsum(x[k] for x in q) for k in METRICS if k!='wsh_utilization_fraction'}
            cumulative.append({'contrast':key[0],'profile_id':key[1],'gamma':key[2],'from_year':start,'through_year':2035,
              **sums,'gross_wsh_loss_mwh':math.fsum(max(0,-x['wsh_mwh']) for x in q),
              'gross_wsh_gain_mwh':math.fsum(max(0,x['wsh_mwh']) for x in q),
              'positive_emissions_change_t':math.fsum(max(0,x['emissions_t']) for x in q),
              'negative_emissions_change_t':math.fsum(min(0,x['emissions_t']) for x in q),
              'years_coal_up_wsh_down':sum(x['coal_mwh']>1000 and x['wsh_mwh']<-1000 for x in q)})
    return {'peak_metrics_12_paths.csv':peaks,'peak_tolerance_sensitivity.csv':epsrows,'peak_matched_controls.csv':comparison,
      'annual_strict_differences.csv':deltas,'cumulative_strict_differences.csv':cumulative,
      'price_allocation_interactions.csv':inter,'annual_coal_clean_displacement_flags.csv':coincidence}
