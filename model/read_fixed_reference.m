function Afix=read_fixed_reference(referenceDir,U,current)
% Build fixed annual allocation from a locally re-solved OBA reference.
% This function needs no archived model-result table in the repository.
% The reference is the same profile/year, OBA, gamma=1, kappa=1, alpha=1,
% with the same demand scale and demand-response setting.
assert(isfolder(referenceDir),'FixedReferenceDir must be an existing OBA output directory.');
for name=["RUN_COMPLETE.json","run_settings.json","summary.json","annual_unit_records.csv"]
 assert(isfile(fullfile(referenceDir,name)),'Incomplete reference output: %s',name);
end
marker=jsondecode(fileread(fullfile(referenceDir,'RUN_COMPLETE.json')));
assert(marker.accepted && strcmp(marker.adapter_version,'MODEL_INPUTS_ONLY_R1'),'Reference must be accepted by this public adapter.');
r=jsondecode(fileread(fullfile(referenceDir,'run_settings.json')));
s=jsondecode(fileread(fullfile(referenceDir,'summary.json')));
assert(r.profile_id==current.profile_id && r.year==current.year,'Reference profile/year mismatch.');
assert(strcmp(r.allocation,'OBA') && r.gamma==1 && r.kappa==1 && r.alpha==1, ...
 'Reference must use OBA, Gamma=1, Kappa=1 and Alpha=1.');
assert(r.demand_scale==current.demand_scale && r.dr_fraction==current.dr_fraction, ...
 'Reference demand or demand-response treatment mismatch.');
assert(strcmp(r.input_manifest_text,current.input_manifest_text), ...
 'Reference and target must use the same versioned numerical-input bank.');
assert(s.profile_id==current.profile_id && s.year==current.year && strcmp(s.allocation,'OBA'));
Q=readtable(fullfile(referenceDir,'annual_unit_records.csv'),'TextType','string');
assert(height(Q)==height(U) && isequal(Q.record_id,U.record_id));
assert(isequal(Q.unit_id,U.unit_id) && isequal(Q.province_id,U.province_id));
fields={'year','is_gas','capacity_mw','quota_t_per_mwh','fuel_kg_per_mwh','fuel_cny_per_mwh','emissions_t_per_mwh'};
for i=1:numel(fields)
 x=double(Q.(fields{i}));y=double(U.(fields{i}));
 assert(all(isfinite(x))&&all(abs(x-y)<=1e-9.*max(1,abs(y))), ...
     'Reference coefficient mismatch: %s',fields{i});
end
g=double(Q.generation_mwh);
assert(all(isfinite(g)) && all(g>=-1e-6) && all(g<=U.capacity_mw*8760+1e-3));
Afix=sum(U.quota_t_per_mwh.*g);
assert(isfinite(Afix) && Afix>=0);
assert(abs(Afix-s.free_quota_t)<=1e-8*max(1,abs(Afix)), ...
 'Reference generation and allowance account disagree.');
end
