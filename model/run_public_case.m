function summary=run_public_case(repo,profile,year,out,opts)
% New public I/O adapter to the unchanged archived pcv3_build_lp constructor.
% Requires the complete numeric-input export and a locally licensed Gurobi.
% No archived results or plotting files are needed. FIXED requires a locally
% solved same-profile OBA reference. Full-size acceptance remains to be tested.
arguments
 repo (1,:) char
 profile (1,1) double {mustBeInteger,mustBeInRange(profile,1,288)}
 year (1,1) double {mustBeInteger,mustBeInRange(year,2020,2035)}
 out (1,:) char
 opts.Kappa (1,1) double {mustBeGreaterThanOrEqual(opts.Kappa,1)}=1
 opts.Gamma (1,1) double {mustBePositive}=1
 opts.Allocation (1,1) string {mustBeMember(opts.Allocation,["OBA","FIXED"])}="OBA"
 opts.Alpha (1,1) double {mustBeInRange(opts.Alpha,0,1)}=1
 opts.DemandScale (1,1) double {mustBePositive}=1
 opts.DRFraction (1,1) double {mustBeMember(opts.DRFraction,[0,.05])}=0
 opts.FixedReferenceDir (1,:) char=''
 opts.Threads (1,1) double {mustBeInteger,mustBePositive}=8
end
assert(~isfolder(out)&&~isfile(out),'Output must be a new directory');
assert(isfile(fullfile(repo,'data/INPUTS_SHA256SUMS.txt')),'Numerical input manifest missing.');
assert(exist('gurobi','file')>0,'Configure your own licensed Gurobi MATLAB installation');
T=readtable(fullfile(repo,'data/scenarios/tasks_full288.csv'),'TextType','string');
t=T(T.profile_id==profile & T.year==year,:);assert(height(t)==1);
U=readgz(fullfile(repo,'data/model_inputs/thermal',sprintf('%d_%s_%s.csv.gz',year,t.CQ,t.COP)));
assert(isequal(U.record_id,(1:height(U))'));
I=struct('prvc_num',31,'prvcstr',compose("P%02d",(1:31)'));
I.units_generation_VC=[U.capacity_mw,U.quota_t_per_mwh,U.fuel_kg_per_mwh,U.fuel_cny_per_mwh,U.emissions_t_per_mwh];
I.provinceUnitRanges=zeros(31,2);I.volume=zeros(31,1);
for i=1:31
 ix=find(U.province_id==i);assert(~isempty(ix)&&all(diff(ix)==1));
 I.provinceUnitRanges(i,:)=[ix(1),ix(end)];I.volume(i)=sum(U.capacity_mw(ix));
end
fields={'wind','solar','hydro','nuclear','load'};dest={'wind_power','photo_power','hydro_power','nuclear_power','load_power'};
for j=1:5
 if j==5,re='COMMON';else,re=char(t.RE);end
 X=readgz(fullfile(repo,'data/model_inputs/hourly',sprintf('%d_%s_%s.csv.gz',year,re,fields{j})));
 assert(isequal(size(X),[8760,31]));I.(dest{j})=table2array(X)';
 assert(all(isfinite(I.(dest{j})),'all')&&all(I.(dest{j})>=0,'all'));
end
I.load_power=I.load_power*opts.DemandScale;I.minvolume=zeros(31,8760);
C=table2array(readtable(fullfile(repo,'data/network/capacity_mw',sprintf('%d_%s.csv',year,t.TL)),'ReadRowNames',true));
assert(isequal(size(C),[31,31])&&isequal(C,C')&&all(C>=0,'all')&&all(diag(C)==0));
[ii,jj]=find(triu(C,1)>0);E=numel(ii);
network=struct('A',sparse([ii;jj],[(1:E)';(1:E)'],[ones(E,1);-ones(E,1)],31,E), ...
 'Acapacity',C(sub2ind([31,31],ii,jj)));
% Public matrices already include the actual year/TL multiplier. Set this
% constructor's multiplier to one, rather than multiplying effective limits twice.
price=double(t.CarbonPrice);if year>=2023,price=price*opts.Gamma;end
cfg=struct('profileID',profile,'year',year,'variant','public_adapter','CQ',char(t.CQ), ...
 'FL_SC',double(t.FL_SC),'ATCrate',1,'CarbonPrice',price,'etsActive',logical(t.ets_active), ...
 'carbonMode','BUY_PREMIUM_NATIONAL_ANNUAL','settlementScope','national_annual', ...
 'buyMultiplier',opts.Kappa,'annualDeficitPremium',opts.Kappa-1,'variableOmAdder',0, ...
 'carbonInternalization',opts.Alpha,'drFraction',opts.DRFraction,'useRamping',true, ...
 'timeStepHours',1,'slackMode','SI_LINEAR_SLACK','slackFreeBandFraction',0,'networkMode','BIDIR_AGGREGATED_31');
P=struct('time_num',24,'lambda',1.5,'rampRate',.6,'penalty',1e6);
runSettings=struct('adapter_version','MODEL_INPUTS_ONLY_R1','profile_id',profile,'year',year, ...
 'kappa',opts.Kappa,'gamma',opts.Gamma,'allocation',char(opts.Allocation), ...
 'alpha',opts.Alpha,'demand_scale',opts.DemandScale,'dr_fraction',opts.DRFraction, ...
 'input_manifest_text',fileread(fullfile(repo,'data/INPUTS_SHA256SUMS.txt')));
fixedMode=opts.Allocation=="FIXED"&&year>=2023;Afix=0;quota=U.quota_t_per_mwh;
if fixedMode
 assert(~isempty(opts.FixedReferenceDir), ...
  'First solve OBA at Gamma=1,Kappa=1,Alpha=1; pass that output as FixedReferenceDir.');
 Afix=read_fixed_reference(opts.FixedReferenceDir,U,runSettings);
 I.units_generation_VC(:,2)=0;
end
[model,L,recipe]=pcv3_build_lp(I,P,network,cfg,8760);
if fixedMode
 model.objcon=-cfg.carbonInternalization*cfg.CarbonPrice*Afix;
 if L.carbonAnnualRow>0,model.rhs(L.carbonAnnualRow)=Afix;end
end
params=struct('Threads',opts.Threads,'Method',1,'TimeLimit',10800);
result=gurobi(model,params);assert(strcmp(result.status,'OPTIMAL'),'Run not accepted: solver status is not OPTIMAL');
x=result.x;V=reshape(x(1:L.dispatchColumns),L.K,8760);g=sum(V(L.hourWithinBlock.thermal,:),2);
emission=sum(U.emissions_t_per_mwh.*g);if fixedMode,a=Afix;else,a=sum(quota.*g);end
D=emission-a;if cfg.etsActive,carbon=price*(D+(opts.Kappa-1)*max(D,0));else,carbon=0;end
fuel=sum(U.fuel_cny_per_mwh.*g);fixedOm=308845*sum(U.capacity_mw);
slack=sum(V(L.hourWithinBlock.svg,:),'all')+sum(V(L.hourWithinBlock.dvg,:),'all');
obj=fuel+opts.Alpha*carbon+P.penalty*slack;
assert(abs(obj-result.objval)/max(1,abs(result.objval))<1e-7,'Objective reconciliation failed');
r=model.A*x-model.rhs;sg=char(model.sense);
viol=max([abs(r(sg=='='));max(r(sg=='<'),0);max(-r(sg=='>'),0)]);assert(viol<1e-3,'Constraint residual check failed');
summary=struct('profile_id',profile,'year',year,'kappa',opts.Kappa,'gamma',opts.Gamma,'allocation',opts.Allocation, ...
 'emissions_t',emission,'free_quota_t',a,'net_deficit_t',D,'fuel_cost_cny',fuel,'fixed_thermal_om_cny',fixedOm, ...
 'net_carbon_cost_cny',carbon,'reported_generation_cost_cny',fuel+fixedOm+carbon,'objective_cny',result.objval, ...
 'max_constraint_residual',viol,'not_automatically_a_published_result',true);
mkdir(out);f=fopen(fullfile(out,'summary.json'),'w');fprintf(f,'%s',jsonencode(summary));fclose(f);
U.generation_mwh=g;writetable(U,fullfile(out,'annual_unit_records.csv'));save(fullfile(out,'dispatch_numeric.mat'),'V','recipe','-v7.3');
f=fopen(fullfile(out,'run_settings.json'),'w');assert(f>=0);fprintf(f,'%s',jsonencode(runSettings));fclose(f);
f=fopen(fullfile(out,'RUN_COMPLETE.json'),'w');assert(f>=0);fprintf(f,'%s',jsonencode(struct('accepted',true,'adapter_version','MODEL_INPUTS_ONLY_R1')));fclose(f);
end
function T=readgz(file)
assert(isfile(file),'Missing numerical input: %s',file);tmp=tempname;mkdir(tmp);c=onCleanup(@() rmdir(tmp,'s')); %#ok<NASGU>
f=gunzip(file,tmp);T=readtable(f{1},'TextType','string');
end
