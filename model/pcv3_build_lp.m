function [model, layout, recipe] = pcv3_build_lp(I, P, network, cfg, H)
%BUY_PREMIUM_NATIONAL_ANNUAL -- price r*p for net annual purchases,
% market price p for net annual surplus sales. r is TOTAL purchase multiplier.
% D = sum_j,t (e_j-b_j)*g_jt. Cost = p*D+(r-1)*p*epsilon.
% epsilon>=D, epsilon>=0. Annual NATIONAL netting follows SI eq16's scalar.
% No per-unit penalties, no per-hour penalties, no cross-year banking.
% Base physical equations follow the audited model with the approved network
% voltage-column correction. Predeclared physical sensitivities are explicit.
% Nonfuel variable O&M is zero in every approved variant. No optional adder.
% Fixed nuclear and six input paths retained; v3 loader sets province minimum to zero.
% No original source or old result is changed. No solver called here.

assert(isstruct(I) && isstruct(P) && isstruct(network) && isstruct(cfg));
validateattributes(H,{'double'},{'scalar','integer','positive','finite'});
assert(H<=8760,'This input cache contains at most 8760 hours.');
assert(strcmp(cfg.carbonMode,'BUY_PREMIUM_NATIONAL_ANNUAL'));
assert(strcmp(cfg.settlementScope,'national_annual'));
assert(P.time_num==24); % source metadata only, NEVER a carbon multiplier
assert(cfg.buyMultiplier>=1 && cfg.annualDeficitPremium==cfg.buyMultiplier-1);
assert(cfg.variableOmAdder==0,'Nonfuel variable O&M is excluded by approved protocol.');
assert(cfg.carbonInternalization>=0&&cfg.carbonInternalization<=1);
assert(cfg.drFraction==0||cfg.drFraction==0.05);
assert(isfinite(cfg.CarbonPrice) && cfg.CarbonPrice>=0 && P.lambda>0);
assert(isfield(cfg,'etsActive') && cfg.etsActive==(cfg.CarbonPrice>0));
assert(cfg.etsActive || strcmp(cfg.CQ,'CQ1'),'Only CQ1 disables the carbon market.');
assert(islogical(cfg.useRamping) && isscalar(cfg.useRamping));
assert(isfinite(cfg.FL_SC) && cfg.FL_SC>=0 && cfg.FL_SC<=1);
assert(isfinite(cfg.ATCrate) && cfg.ATCrate>0);
assert(isfinite(P.rampRate) && P.rampRate>=0);
assert(strcmp(cfg.slackMode,'SI_LINEAR_SLACK'),'Unapproved slack mode.');
assert(isfield(P,'penalty') && isscalar(P.penalty) && isfinite(P.penalty) && P.penalty>0);
assert(cfg.slackFreeBandFraction==0 && cfg.timeStepHours==1, ...
    'This pilot implements full linear slack cost at one-hour resolution.');

U=double(I.units_generation_VC); N=size(U,1); B=I.prvc_num;
assert(B==numel(I.prvcstr) && size(U,2)==5 && all(isfinite(U(:))));
assert(all(U(:,1)>0),'Nonpositive unit capacity: stop, do not fabricate a bound.');
A=sparse(double(network.A)); E=size(A,2);
assert(size(A,1)==B && E==numel(network.Acapacity));
assert(all(full(sum(A~=0,1))==2) && all(full(sum(A,1))==0));
assert(all(full(sum(A==1,1))==1) && all(full(sum(A==-1,1))==1));
cap=double(network.Acapacity(:))*cfg.ATCrate;
assert(all(isfinite(cap)) && all(cap>0));
fields={'load_power','wind_power','photo_power','hydro_power','nuclear_power','minvolume'};
for k=1:numel(fields)
    V=I.(fields{k});
    assert(size(V,1)==B && size(V,2)>=H && all(isfinite(V(:))), ...
        'Invalid hourly input: %s.',fields{k});
end
for k=2:5
    V=I.(fields{k});
    assert(all(V(:)>=0),'Negative available output in %s; no clipping performed.',fields{k});
end
assert(numel(I.volume)==B && all(isfinite(I.volume(:))));

ranges=double(I.provinceUnitRanges);
assert(isequal(size(ranges),[B,2]));
unitProvince=zeros(N,1);
last=0;
for i=1:B
    a=ranges(i,1); b=ranges(i,2);
    assert(a==last+1 && a==floor(a) && b==floor(b) && b>=a && b<=N, ...
        'Province/record ranges must form an unbroken partition.');
    unitProvince(a:b)=i; last=b;
end
assert(last==N && all(unitProvince>0));
T=sparse(unitProvince,(1:N)',ones(N,1),B,N);
assert(max(abs(T*U(:,1)-I.volume(:)))<=1e-6, ...
    'Provincial capacities differ from sums of record capacities.');

hasDR=cfg.drFraction>0; assert(~hasDR||mod(H,24)==0);
K=N+5*B+E+B*double(hasDR);
ix=struct('thermal',1:N,'wind',N+(1:B),'solar',N+B+(1:B), ...
    'hydro',N+2*B+(1:B),'corridor',N+3*B+(1:E), ...
    'svg',N+3*B+E+(1:B),'dvg',N+4*B+E+(1:B));
ix.dr=[];
if hasDR, ix.dr=N+5*B+E+(1:B); end
% Keep provincial upper bounds too; do not rely on their redundancy.
B0=[T,speye(B),speye(B),speye(B),-A,speye(B),-speye(B); ...
    T,sparse(B,5*B+E); T,sparse(B,5*B+E)];
if hasDR, B0=[B0,[-speye(B);sparse(2*B,B)]]; end
R0=[speye(N),sparse(N,K-N)];
baseRows=3*B*H;
% If static unit bounds already imply the ramp limit, omit only redundant
% rows. For CF1: max possible change=(1-0.4)*capacity=0.6*capacity.
% Physical post-checks still evaluate every adjacent hour, including day cuts.
rampRedundant=cfg.useRamping && P.rampRate>=(1-cfg.FL_SC);
rampOne=N*max(H-1,0)*double(cfg.useRamping && ~rampRedundant);
fprintf('RAMP_ROWS_REDUNDANT_BY_UNIT_BOUNDS=%d\nRAMP_PHYSICS_STILL_CHECKED=1\n',rampRedundant);
layout=struct('version','POWCARB_V3_BIDIR_IDENTIFIED_FIXEDCAP_R1', ...
    'N',N,'B',B,'E',E,'H',H,'K',K,'hourColumns',1:H, ...
    'hourWithinBlock',ix,'unitProvince',unitProvince,'T',T, ...
    'rowsPerHour',3*B,'staticRows',baseRows,'rampRowsOneDirection',rampOne, ...
    'rampUpRowStart',baseRows+1,'rampDownRowStart',baseRows+rampOne+1, ...
    'rows',baseRows+2*rampOne,'columns',K*H, ...
    'columnRule','(hour-1)*K + local_index', ...
    'staticRowRule','(hour-1)*3*B + [balance; provincial_lower; provincial_upper]', ...
    'rampRowRule','offset + (hour-2)*N + record_id, hour=2..H');
layout.rampRowsOmittedAsRedundant=rampRedundant;
layout.drRows=0; layout.drRowStart=0;
layout.dispatchColumns=K*H;
layout.carbonEpsilonColumn=0;layout.carbonAnnualRow=0;
recipe=struct('version',layout.version,'configuration',cfg,'H',H, ...
    'singleHourMatrix',B0,'thermalSelector',R0,'layout',layout, ...
    'buyMultiplier',cfg.buyMultiplier,'baseCarbonMultiplier',1, ...
    'annualPremiumMultiplier',cfg.annualDeficitPremium, ...
    'settlementScope','national_annual','quotaNettingPeriod','one_model_year', ...
    'compensationNonnegative',true, ...
    'compensationRule','epsilon=max(sum_all_records_all_hours_net_deficit,0)', ...
    'initialThermalOutput','free within first-hour bounds', ...
    'cyclicBoundary',false,'fullHorizonJointOptimization',true, ...
    'noRollingHorizon',true,'noAnnualExtrapolation',true, ...
    'slackMode',cfg.slackMode,'slackPenaltyCNYperMWh',P.penalty, ...
    'slackBounds',[0 Inf],'freeSlackBand',false, ...
    'slackIsPhysicalGeneration',false);

fprintf('SPARSE_BUILD_START\nHOURS=%d\nVARIABLES_EXPECTED=%d\nROWS_EXPECTED=%d\n', ...
    H,layout.columns,layout.rows); drawnow;
t0=tic;
staticA=kron(speye(H),B0);
fprintf('SPARSE_STATIC_NNZ=%d\n',nnz(staticA)); drawnow;
if rampOne>0
    t=(1:H-1)';
    Dt=sparse([t;t],[t;t+1],[-ones(H-1,1);ones(H-1,1)],H-1,H);
    Ramp=kron(Dt,R0); % uses ALL consecutive hours, including 24 -> 25
    fprintf('SPARSE_RAMP_ONE_DIRECTION_NNZ=%d\n',nnz(Ramp)); drawnow;
    model=struct();
    model.A=[staticA;Ramp;-Ramp];
    clear staticA Ramp Dt;
else
    model=struct('A',staticA); clear staticA;
end

qdiff=U(:,5)-U(:,2);
if cfg.etsActive
    unitCost=U(:,4)+cfg.variableOmAdder+cfg.carbonInternalization*cfg.CarbonPrice*qdiff;
else
    % CQ1: no ETS cost or cap. A free signed epsilon would not constrain dispatch.
    unitCost=U(:,4)+cfg.variableOmAdder;
    recipe.compensationRule='CQ1: no carbon objective or compensation constraint';
end
localObj=[unitCost;zeros(3*B+E,1);P.penalty*ones(2*B,1)];
if hasDR, localObj=[localObj;zeros(B,1)]; end
model.obj=repmat(localObj,H,1);
model.objcon=0;
lo=[repmat(cfg.FL_SC*U(:,1),1,H);zeros(3*B,H);repmat(-cap,1,H);zeros(2*B,H)];
if hasDR, lo=[lo;-cfg.drFraction*I.load_power(:,1:H)]; end
model.lb=lo(:);clear lo;
upper=[repmat(U(:,1),1,H);I.wind_power(:,1:H);I.photo_power(:,1:H); ...
    I.hydro_power(:,1:H);repmat(cap,1,H);Inf(2*B,H)];
if hasDR, upper=[upper;cfg.drFraction*I.load_power(:,1:H)]; end
model.ub=upper(:); clear upper;
staticRHS=[I.load_power(:,1:H)-I.nuclear_power(:,1:H); ...
    I.minvolume(:,1:H);repmat(I.volume(:),1,H)];
staticSense=[repmat('=',B,1);repmat('>',B,1);repmat('<',B,1)];
if rampOne>0
    rampRHS=repmat(P.rampRate*U(:,1),H-1,1);
    model.rhs=[staticRHS(:);rampRHS;rampRHS];
    model.sense=[repmat(staticSense,H,1);repmat('<',2*rampOne,1)];
else
    model.rhs=staticRHS(:);
    model.sense=repmat(staticSense,H,1);
end
clear staticRHS rampRHS;
if hasDR
    selectDR=sparse(1:B,ix.dr,ones(1,B),B,K);
    group=sparse(ceil((1:H)/24),1:H,ones(1,H),H/24,H);
    Daily=kron(group,selectDR);
    layout.drRowStart=layout.rows+1;layout.drRows=B*(H/24);
    model.A=[model.A;Daily];model.rhs=[model.rhs;zeros(layout.drRows,1)];
    model.sense=[model.sense;repmat('=',layout.drRows,1)];
    layout.rows=layout.rows+layout.drRows;clear Daily group selectDR;
end
% A single annual net-deficit epigraph. For r=1 the extra variable/row
% is omitted exactly (zero premium); physical constraints remain unchanged.
if cfg.etsActive && cfg.annualDeficitPremium>0 && cfg.carbonInternalization>0
    annualRow=kron(ones(1,H),sparse([qdiff;zeros(K-N,1)]'));
    model.A=[model.A,sparse(layout.rows,1);annualRow,sparse(-1)];
    model.obj=[model.obj;cfg.carbonInternalization*cfg.annualDeficitPremium*cfg.CarbonPrice];
    model.lb=[model.lb;0];model.ub=[model.ub;Inf];
    model.rhs=[model.rhs;0];model.sense=[model.sense;'<'];
    layout.carbonEpsilonColumn=layout.dispatchColumns+1;
    layout.carbonAnnualRow=layout.rows+1;
    layout.columns=layout.columns+1;layout.rows=layout.rows+1;
    clear annualRow;
end
recipe.layout=layout;
recipe.variableOmAdder=cfg.variableOmAdder;
recipe.redundantRampProof='If rampRate>=1-FL_SC, static per-unit bounds imply all adjacent ramp inequalities; no initial/cyclic constraints exist. All adjacent ramp differences checked after solve.';
model.modelsense='min'; model.vtype='C';
model.modelname=sprintf('P%03d_%d_H%d_K%g_%s',cfg.profileID,cfg.year,H,cfg.buyMultiplier,cfg.variant);
recipe.networkMode=cfg.networkMode;recipe.fixedOmExcludedFromOptimization=true;
recipe.slackPenaltyExcludedFromEconomicReports=true;recipe.carbonInternalization=cfg.carbonInternalization;
fprintf('CARBON_MODE=BUY_PREMIUM_NATIONAL_ANNUAL\n');
fprintf('TOTAL_BUY_MULTIPLIER=%.12g\nSURPLUS_SALE_MULTIPLIER=1\n',cfg.buyMultiplier);
fprintf('INCREMENTAL_PREMIUM=%.12g\nANNUAL_QUOTA_ROWS=%d\n',cfg.annualDeficitPremium,double(layout.carbonAnnualRow>0));
fprintf('PHYSICAL_DISPATCH_COLUMNS=%d\nTOTAL_COLUMNS=%d\n',layout.dispatchColumns,layout.columns);
assert(issparse(model.A) && isa(model.A,'double') && ...
    isequal(size(model.A),[layout.rows,layout.columns]));
assert(numel(model.obj)==layout.columns && numel(model.rhs)==layout.rows);
assert(all(model.lb<=model.ub),'Inconsistent variable bounds.');
assert(all(isfinite(model.obj)) && all(isfinite(model.rhs)));
recipe.buildSeconds=toc(t0); recipe.nnz=nnz(model.A);
info=whos('model'); recipe.matlabModelBytes=info.bytes;
fprintf('SPARSE_BUILD_DONE\nSPARSE_BUILD_SECONDS=%.3f\nMODEL_NNZ=%d\n', ...
    recipe.buildSeconds,recipe.nnz);
fprintf('MATLAB_MODEL_BYTES=%d\n',info.bytes);
fprintf('MODEL_BYTES_ARE_NOT_SOLVER_PEAK_MEMORY=1\n'); drawnow;
end
