function result = acycle_tune(request)
%ACYCLE_TUNE Build a declared periodic age model from a bandpassed curve.
% Original Acycle getpks and depthtotime remain the numerical entrypoints.
% Peak/trough selection and whole-period assignment come from AC.m:4613-4633;
% application comes from agescale.m:351-352. Explicit anchoring, both-extrema
% half periods, ambiguity checks and endpoint policies are documented bridge
% extensions, not an independent test of astronomical forcing.
for name={'input_path','output_dir','acycle_root'}
    assert(isfield(request,name{1}),'Harness:TuneRequest','Missing %s.',name{1});
end
out=char(request.output_dir);root=char(request.acycle_root);
if ~isfolder(out),mkdir(out);end
assert(~isfile(fullfile(out,'analysis.mat')),'Harness:OutputExists', ...
    'Refusing to overwrite a completed tuning result.');
oldPath=path;cleanupPath=onCleanup(@()path(oldPath)); %#ok<NASGU>
seriesPath=fullfile(root,'code','seriesanalysis');addpath(seriesPath,'-begin');
for name={'getpks','depthtotime','findduplicate'}
    expected=fullfile(seriesPath,[name{1},'.m']);
    assert(isfile(expected)&&strcmp(which(name{1}),expected), ...
        'Harness:TuneSource','Original Acycle function is missing or shadowed: %s.',name{1});
end
p=fieldOr(request,'parameters',struct());
assert(isstruct(p)&&isscalar(p),'Harness:TuneParameters','parameters must be an object.');
allowed={'period_kyr','anchor_age_kyr','anchor_phase','extrema','depth_unit','endpoint_policy'};
unknown=setdiff(fieldnames(p),allowed);
assert(isempty(unknown),'Harness:UnknownParameter','Unknown tuning parameters: %s',strjoin(unknown,', '));
for name={'period_kyr','anchor_age_kyr','anchor_phase','extrema','depth_unit'}
    assert(isfield(p,name{1}),'Harness:TuneMissingParameter', ...
        'Explicit tuning assumption required: %s.',name{1});
end
validateattributes(p.period_kyr,{'numeric'},{'scalar','real','finite','positive'});
validateattributes(p.anchor_age_kyr,{'numeric'},{'scalar','real','finite'});
p.anchor_phase=char(p.anchor_phase);p.extrema=char(p.extrema);p.depth_unit=char(p.depth_unit);
p.endpoint_policy=char(fieldOr(p,'endpoint_policy','trim'));
assert(any(strcmp(p.anchor_phase,{'peak','trough'})), ...
    'Harness:TunePhase','anchor_phase must be peak or trough.');
assert(any(strcmp(p.extrema,{'peaks','troughs','both'})), ...
    'Harness:TuneExtrema','extrema must be peaks, troughs or both.');
assert(any(strcmp(p.endpoint_policy,{'trim','linear_extrapolate','error'})), ...
    'Harness:TuneCoverage','endpoint_policy must be trim, linear_extrapolate or error.');
assert(~(strcmp(p.extrema,'peaks')&&~strcmp(p.anchor_phase,'peak'))&& ...
    ~(strcmp(p.extrema,'troughs')&&~strcmp(p.anchor_phase,'trough')), ...
    'Harness:TunePhase','Single-kind extrema require the matching explicit anchor_phase.');
depthToCm=depthFactor(p.depth_unit);
raw=readmatrix(request.input_path);
assert(isnumeric(raw)&&isreal(raw)&&any(size(raw,2)==[2,3])&&size(raw,1)>=3, ...
    'Harness:TuneColumns','Tuning requires depth/bandpass-value columns, optionally a third unused envelope column.');
assert(size(raw,1)<=300000,'Harness:TuneRows','Tuning is limited to 300000 input rows.');
% AC.m preparation adapted to the two selected columns, finite rows FIRST.
% GUI removes Inf after duplicate averaging; here an invalid duplicate must
% not destroy a finite observation at the same depth. Record this deviation.
selected=raw(:,1:2);
finite=selected(all(isfinite(selected),2),:);
clean=findduplicate(sortrows(finite));
assert(size(clean,1)>=3&&all(diff(clean(:,1))>0), ...
    'Harness:TuneControlPoints','At least three finite unique observations are required.');
assert(isfinite(var(clean(:,2)))&&var(clean(:,2))>0, ...
    'Harness:TuneControlPoints','The bandpassed curve must have nonzero finite variance.');
extrema=zeros(0,3);
if any(strcmp(p.extrema,{'peaks','both'})),extrema=[extrema;originalExtrema(clean,1)];end %#ok<AGROW>
if any(strcmp(p.extrema,{'troughs','both'})),extrema=[extrema;originalExtrema(clean,-1)];end %#ok<AGROW>
extrema=sortrows(extrema,1);
assert(size(extrema,1)>=2,'Harness:TuneControlPoints', ...
    'At least two selected extrema are required to construct a monotone age model.');
assert(all(diff(extrema(:,1))>0),'Harness:TunePlateau', ...
    'Peak/trough candidates share a coordinate; ambiguous plateaus must be resolved explicitly.');
if strcmp(p.extrema,'both')
    assert(all(diff(extrema(:,3))~=0),'Harness:TunePlateau', ...
        'Both-extrema tuning requires strictly alternating original peaks and troughs.');
    cycleStep=.5;
else
    cycleStep=1;
end
anchorType=1;if strcmp(p.anchor_phase,'trough'),anchorType=-1;end
anchorIndex=find(extrema(:,3)==anchorType,1);
assert(~isempty(anchorIndex),'Harness:TunePhase','The selected curve has no extrema matching anchor_phase.');
cycle=((1:size(extrema,1))'-anchorIndex)*cycleStep;
ages=p.anchor_age_kyr+cycle*p.period_kyr;
assert(all(isfinite(ages))&&all(diff(ages)>0),'Harness:TuneAgePrecision', ...
    'The requested period and anchor do not produce finite strictly increasing representable ages.');
% Columns: depth, bandpass value, type (+1 peak/-1 trough), cycle, age_kyr.
controlPoints=[extrema,cycle,ages];
observedModel=controlPoints(:,[1,5]);
covered=clean(:,1)>=observedModel(1,1)&clean(:,1)<=observedModel(end,1);
outside=~covered;
switch p.endpoint_policy
    case 'trim'
        retained=clean(covered,:);ageModel=observedModel;
    case 'error'
        assert(~any(outside),'Harness:TuneCoverage', ...
            'Selected extrema do not cover the entire input. Explicitly choose trim or linear_extrapolate.');
        retained=clean;ageModel=observedModel;
    case 'linear_extrapolate'
        retained=clean;
        % depthtotime uses the first/last control-point slope. Do not copy
        % AC.m's plot-only agemodelfull multiplication, which has wrong units.
        [endpointAges,~]=depthtotime(clean([1,end],1),observedModel);
        ageModel=observedModel;
        if clean(1,1)<observedModel(1,1),ageModel=[clean(1,1),endpointAges(1);ageModel];end
        if clean(end,1)>observedModel(end,1),ageModel=[ageModel;clean(end,1),endpointAges(2)];end
end
assert(all(isfinite(ageModel),'all')&&all(diff(ageModel(:,1))>0)&&all(diff(ageModel(:,2))>0), ...
    'Harness:TuneAgePrecision','Endpoint policy produced a nonfinite or nonmonotone age model.');
assert(size(retained,1)*(size(ageModel,1)-1)<=2e7,'Harness:TuneBudget', ...
    'Requested sample-by-control workload exceeds 20 million original depthtotime interval checks.');
[time,originalRates]=depthtotime(retained(:,1),ageModel);
assert(numel(time)==size(retained,1)&&all(isfinite(time))&&all(diff(time)>0), ...
    'Harness:TuneAgePrecision','Original depthtotime returned a nonfinite or non-increasing time axis.');
depthAge=[retained(:,1),time(:)];
tuned=[time(:),retained(:,2)];
sedimentationRates=[ageModel(1:end-1,1),ageModel(2:end,1),originalRates(:)*depthToCm];
assert(all(isfinite(sedimentationRates),'all')&&all(sedimentationRates(:,3)>0), ...
    'Harness:TuneRate','Tuning interval rates must be finite and positive.');
ignoredColumns=[];if size(raw,2)==3,ignoredColumns=3;end
extrapolatedRows=0;if strcmp(p.endpoint_policy,'linear_extrapolate'),extrapolatedRows=sum(outside);end
summary=struct('input_rows',size(raw,1),'removed_nonfinite_rows',size(raw,1)-size(finite,1), ...
    'merged_duplicate_rows',size(finite,1)-size(clean,1),'processed_rows',size(retained,1), ...
    'input_curve','bandpassed','bandpass_status','user-declared assumption; not independently verified', ...
    'ignored_input_columns',ignoredColumns,'depth_unit',p.depth_unit,'time_unit','kyr','rate_unit','cm/kyr', ...
    'period_kyr',p.period_kyr,'extrema',p.extrema,'control_point_count',size(controlPoints,1), ...
    'anchor_phase',p.anchor_phase,'anchor_age_kyr',p.anchor_age_kyr, ...
    'anchor_control_index',anchorIndex,'anchor_depth',controlPoints(anchorIndex,1), ...
    'anchor_definition','first selected extremum matching anchor_phase', ...
    'cycle_increment',cycleStep,'endpoint_policy',p.endpoint_policy, ...
    'input_depth_range',clean([1,end],1)','observed_control_depth_range',observedModel([1,end],1)', ...
    'valid_depth_range',ageModel([1,end],1)','recommended_depth_range',ageModel([1,end],1)', ...
    'age_model',ageModel,'time_range_kyr',time([1,end])', ...
    'trimmed_rows',size(clean,1)-size(retained,1),'extrapolated_rows',extrapolatedRows, ...
    'extrapolated_endpoints',size(ageModel,1)-size(observedModel,1), ...
    'time_resampled',false,'independent_astronomical_test',false, ...
    'phase_detection','original getpks sampled extrema; no prominence, minimum-distance or sub-sample fit');
warnings={'The input is assumed to be the scientifically chosen bandpassed curve; this tool does not verify its frequency band or infer an orbital period.', ...
    'Assigning a fixed period to successive extrema is a chronology assumption, not independent evidence of astronomical forcing.', ...
    'A target-period peak in the tuned bandpassed curve is partly imposed by construction; diagnose the original proxy using this age model instead.', ...
    'Original getpks has no prominence or minimum-distance test. Missed or spurious extrema can miscount cycles; inspect the control-point plot.', ...
    'Tuned output preserves sampled values and is not resampled to a uniform time grid; no age uncertainty is propagated.'};
if strcmp(p.extrema,'both')
    warnings{end+1}='Both-extrema tuning assigns a half cycle to every alternating peak/trough pair. This phase assumption and explicit anchoring extend the original single-extremum GUI.';
end
if strcmp(p.endpoint_policy,'linear_extrapolate')
    warnings{end+1}='Explicit endpoint extrapolation assumes the nearest control-point interval rate continues to each record edge; these added endpoints are not observed cycle controls.';
elseif strcmp(p.endpoint_policy,'trim')
    warnings{end+1}='Only the observed control-point range is retained. Applying this model to another series must use the reported valid_depth_range.';
end
paths={'code/guicode/AC.m','code/guicode/agescale.m','code/seriesanalysis/getpks.m', ...
    'code/seriesanalysis/findduplicate.m','code/seriesanalysis/depthtotime.m'};
provenance=sourceProvenance(root,request.input_path,paths);
if ~provenance.all_used_sources_match_reference
    warnings{end+1}='Installed Acycle source differs from the validated reference; the original functions executed but numerical compatibility requires review.';
end
artifacts=struct('cleaned_csv',fullfile(out,'tune-cleaned.csv'), ...
    'control_points_csv',fullfile(out,'control_points.csv'),'age_model_csv',fullfile(out,'age_model.csv'), ...
    'depth_age_csv',fullfile(out,'depth_age.csv'),'tuned_csv',fullfile(out,'tuned.csv'), ...
    'sedimentation_rate_csv',fullfile(out,'sedimentation_rate.csv'), ...
    'diagnostic_png',fullfile(out,'tuning.png'),'diagnostic_fig',fullfile(out,'tuning.fig'), ...
    'diagnostic_pdf',fullfile(out,'tuning.pdf'),'analysis_mat',fullfile(out,'analysis.mat'), ...
    'provenance_json',fullfile(out,'provenance.json'));
writematrix(clean,artifacts.cleaned_csv);
writetable(array2table(controlPoints,'VariableNames', ...
    {'depth','bandpass_value','extremum_type','cycle_from_anchor','age_kyr'}),artifacts.control_points_csv);
writematrix(ageModel,artifacts.age_model_csv);writematrix(depthAge,artifacts.depth_age_csv);
writematrix(tuned,artifacts.tuned_csv);
writetable(array2table(sedimentationRates,'VariableNames', ...
    {'left_depth','right_depth','rate_cm_kyr'}),artifacts.sedimentation_rate_csv);
fig=figure('Visible','off','Color','white','Position',[50 50 1100 1000]);
cleanupFigure=onCleanup(@()close(fig)); %#ok<NASGU>
subplot(3,1,1);plot(clean(:,1),clean(:,2),'k','DisplayName','Input bandpassed curve');hold on;
for kind=[1,-1]
    mask=controlPoints(:,3)==kind;
    if any(mask)
        marker='r^';label='Selected peaks';if kind==-1,marker='bv';label='Selected troughs';end
        plot(controlPoints(mask,1),controlPoints(mask,2),marker,'MarkerFaceColor',marker(1),'DisplayName',label);
    end
end
xline(observedModel(1,1),'--','HandleVisibility','off');xline(observedModel(end,1),'--','HandleVisibility','off');
ylabel('Bandpass value');legend('Location','best');grid on;
title(sprintf('Declared tuning: %.6g kyr, %s; %s endpoints',p.period_kyr,p.extrema,p.endpoint_policy),'Interpreter','none');
subplot(3,1,2);plot(ageModel(:,1),ageModel(:,2),'k-','DisplayName','Applied age model');hold on;
plot(observedModel(:,1),observedModel(:,2),'ro','DisplayName','Observed extrema controls');
plot(controlPoints(anchorIndex,1),controlPoints(anchorIndex,5),'bp','MarkerSize',12,'DisplayName','Explicit anchor');
ylabel('Age (kyr)');legend('Location','best');grid on;
subplot(3,1,3);stairs(ageModel(:,1),[sedimentationRates(:,3);sedimentationRates(end,3)],'k');
xlabel(['Depth (' p.depth_unit ')'],'Interpreter','none');ylabel('Rate (cm/kyr)');grid on;
title('Piecewise rates implied by the declared cycle assignment');
exportgraphics(fig,artifacts.diagnostic_png,'Resolution',150);
exportgraphics(fig,artifacts.diagnostic_pdf,'ContentType','vector');savefig(fig,artifacts.diagnostic_fig);
parameters=p; %#ok<NASGU>
save(artifacts.analysis_mat,'raw','clean','controlPoints','ageModel','depthAge','tuned', ...
    'sedimentationRates','parameters','summary','provenance','-v7');
writeJson(artifacts.provenance_json,provenance);
result=struct('status','success','backend','matlab','operation','tune','parameters',p, ...
    'summary',summary,'artifacts',artifacts,'provenance',provenance,'warnings',{warnings});
end

function selected=originalExtrema(clean,kind)
[found,~]=getpks([clean(:,1),kind*clean(:,2)]);
if isempty(found),selected=zeros(0,3);return;end
[exists,index]=ismember(found(:,1),clean(:,1));
assert(all(exists)&&all(index>1)&&all(index<size(clean,1)), ...
    'Harness:TuneSourceOutput','Original getpks returned unexpected coordinates.');
value=clean(index,2);
assert(~any(value==clean(index-1,2)|value==clean(index+1,2)), ...
    'Harness:TunePlateau','Original getpks selected a flat extremum; resolve the plateau explicitly instead of silently changing the detector.');
selected=[clean(index,1),value,repmat(kind,numel(index),1)];
end

function value=fieldOr(s,name,fallback)
if isfield(s,name),value=s.(name);else,value=fallback;end
end

function factor=depthFactor(unit)
units={'m','dm','cm','mm','ft','km'};factors=[100,10,1,.1,30.48,100000];
j=find(strcmp(unit,units),1);
assert(~isempty(j),'Harness:DepthUnit','depth_unit must be m,dm,cm,mm,ft or km.');
factor=factors(j);
end

function provenance=sourceProvenance(root,input,paths)
registry=jsondecode(fileread(fullfile(fileparts(mfilename('fullpath')),'preparation_sources.json')));
files=struct('relative_path',{},'sha256',{},'matches_reference',{});
for k=1:numel(paths)
    actual=fileHash(fullfile(root,paths{k}));match=false;
    for j=1:numel(registry.files)
        if strcmp(paths{k},registry.files(j).relative_path),match=strcmp(actual,registry.files(j).sha256);break;end
    end
    files(k)=struct('relative_path',paths{k},'sha256',actual,'matches_reference',match);
end
provenance=struct('source_repository',registry.repository,'reference_commit',registry.commit, ...
    'source_root',root,'files',files,'all_used_sources_match_reference',all([files.matches_reference]), ...
    'adapter_sha256',fileHash([mfilename('fullpath') '.m']),'input_sha256',fileHash(input), ...
    'matlab_version',version,'matlab_release',version('-release'),'toolboxes',ver, ...
    'numerical_backend','MATLAB/Acycle original getpks, findduplicate and depthtotime', ...
    'plot_backend','MATLAB','extraction_source','AC.m:4613-4633; agescale.m:351-352', ...
    'adapter_extensions','finite rows before duplicate averaging; explicit anchor; alternating half-cycle controls; plateau rejection; bounded endpoint policies; unit conversion', ...
    'endpoint_source','Original depthtotime, not the dimensionally inconsistent plot-only AC.m agemodelfull expression');
end

function hash=fileHash(file)
fid=fopen(file,'rb');assert(fid>=0,'Harness:ReadFailed','Cannot read %s.',file);
cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
digest=java.security.MessageDigest.getInstance('SHA-256');digest.update(fread(fid,Inf,'*uint8'));
hash=lower(reshape(dec2hex(typecast(digest.digest(),'uint8'),2)',1,[]));
end

function writeJson(file,value)
fid=fopen(file,'w');assert(fid>=0,'Harness:WriteFailed','Cannot write %s.',file);
cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s\n',jsonencode(value,'PrettyPrint',true));
end
