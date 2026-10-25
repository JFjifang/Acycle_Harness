function result = acycle_coco(request)
%ACYCLE_COCO MATLAB-only bridge to original Acycle COCO/eCOCO v2 cores.
% Numerical procedures and plots remain in the external Acycle checkout.
% Units and bounded requests are adapted here; no Python calculations occur.
operation = char(getDefault(request,'operation','coco'));
assert(any(strcmp(operation,{'coco','ecoco'})), ...
    'Harness:COCOOperation','operation must be coco or ecoco.');
root = char(request.acycle_root);
out = char(request.output_dir);
if ~isfolder(out), mkdir(out); end
assert(~isfile(fullfile(out,'analysis.mat')), ...
    'Harness:OutputExists','Refusing to overwrite a completed analysis.');
oldPath = path; restorePath = onCleanup(@()path(oldPath)); %#ok<NASGU>
directories = {'code/corrcoef','code/seriesanalysis','code/package/swa', ...
    'code/package/secular_periods'};
for k=1:numel(directories)
    folder=fullfile(root,directories{k});
    assert(isfolder(folder),'Harness:AcycleMissing','Missing Acycle directory: %s',folder);
    addpath(folder,'-begin');
end
required = {'corrcoefslices_rankNew','ecoco','cocoPrepareRegularData', ...
    'cocoAdaptivePublicationReport','plotAdaptiveCocoPublication','ecocoplot'};
for k=1:numel(required)
    expected=fullfile(root,'code','corrcoef',[required{k},'.m']);
    assert(strcmp(which(required{k}),expected), ...
        'Harness:FunctionShadowed','Missing or shadowed Acycle function: %s',required{k});
end
oldVisible=get(groot,'defaultFigureVisible');
set(groot,'defaultFigureVisible','off');
restoreVisible=onCleanup(@()set(groot,'defaultFigureVisible',oldVisible)); %#ok<NASGU>
previousFigures=findall(groot,'Type','figure');
figureCleanup=onCleanup(@()closeNewFigures(previousFigures)); %#ok<NASGU>
p=getDefault(request,'parameters',struct());
assert(isstruct(p)&&isscalar(p),'Harness:COCOParameters','parameters must be an object.');
common={'depth_unit','middle_age_ma','orbital_periods_kyr','sedimentation_rate_min', ...
    'sedimentation_rate_max','sedimentation_rate_step','nsim','seed', ...
    'correlation','red_noise','nfft','max_frequency','method','detrend','span','detrend_window'};
if strcmp(operation,'coco'), allowed=[common,{'slices','dt'}];
else, allowed=[common,{'window','step'}]; end
unknown=setdiff(fieldnames(p),allowed);
assert(isempty(unknown),'Harness:UnknownParameter','Unknown COCO parameters: %s',strjoin(unknown,', '));
for field={'depth_unit','sedimentation_rate_min','sedimentation_rate_max','sedimentation_rate_step'}
    assert(isfield(p,field{1}),'Harness:COCOMissingParameter','Required parameter: %s',field{1});
end
p.method=char(getDefault(p,'method','adaptive'));
if strcmp(operation,'coco'), modes={'adaptive','phase_averaged'};
else, modes={'adaptive','blocked','interleaved'}; end
assert(any(strcmp(p.method,modes)),'Harness:COCOMethod','Unsupported %s method: %s',operation,p.method);
p.nsim=getDefault(p,'nsim',199);
p.seed=getDefault(p,'seed',1);
p.correlation=char(getDefault(p,'correlation','Spearman'));
p.red_noise=getDefault(p,'red_noise',0);
p.detrend=char(getDefault(p,'detrend','linear'));
assert(any(strcmp(p.detrend,{'linear','lowess','loess'})), ...
    'Harness:COCODetrend','detrend must be linear, lowess or loess.');
if strcmp(operation,'ecoco')&&any(strcmp(p.method,{'blocked','interleaved'}))
    assert(strcmp(p.detrend,'linear'),'Harness:COCOPreprocessLeakage', ...
        'Global nonlinear smoothing is disabled for held-out blocked/interleaved eCOCO.');
end
if strcmp(p.detrend,'linear')
    assert(~isfield(p,'span')&&~isfield(p,'detrend_window'), ...
        'Harness:COCODetrend','span/detrend_window require lowess or loess.');
else
    assert(xor(isfield(p,'span'),isfield(p,'detrend_window')), ...
        'Harness:COCODetrend','lowess/loess requires exactly one of span or detrend_window.');
end
validateattributes(p.nsim,{'numeric'},{'scalar','real','finite','integer','>=',1,'<=',10000});
validateattributes(p.seed,{'numeric'},{'scalar','real','finite','integer','>=',0,'<=',2^32-1});
validateattributes(p.red_noise,{'numeric'},{'scalar','real','finite','integer','>=',0,'<=',3});
assert(any(strcmp(p.correlation,{'Pearson','Spearman'})), ...
    'Harness:COCOCorrelation','correlation must be Pearson or Spearman.');
factor=depthFactor(p.depth_unit);
hasAge=isfield(p,'middle_age_ma'); hasPeriods=isfield(p,'orbital_periods_kyr');
assert(xor(hasAge,hasPeriods),'Harness:COCOTarget', ...
    'Specify exactly one of middle_age_ma or orbital_periods_kyr; geological age is never guessed.');
if hasAge
    validateattributes(p.middle_age_ma,{'numeric'},{'scalar','real','finite','>=',0,'<=',4500});
    orbit=calculate_orbit9(p.middle_age_ma);
    periods=orbit(:,2)/1000;
    targetSource='Acycle calculate_orbit9; age rounded to nearest integer Ma';
else
    periods=p.orbital_periods_kyr(:);
    targetSource='explicit user-supplied periods in kyr';
end
validateattributes(periods,{'numeric'},{'vector','real','finite','positive','nonempty'});
assert(numel(unique(periods))==numel(periods), ...
    'Harness:COCODuplicatePeriods','Orbital periods must be distinct.');
if strcmp(operation,'ecoco')||strcmp(p.method,'adaptive')
    assert(numel(periods)==9,'Harness:COCONinePeriods', ...
        'Modern coherent/four-group Adaptive COCO and eCOCO require exactly nine periods.');
else
    assert(numel(periods)>=2&&numel(periods)<=9,'Harness:COCOPeriodCount', ...
        'phase_averaged COCO supports 2 to 9 distinct periods; the original publication audit cannot accept more than 9.');
end
p.max_frequency=getDefault(p,'max_frequency',1.2/min(periods));
validateattributes(p.max_frequency,{'numeric'},{'scalar','real','finite','positive','>=',max(1./periods)});
validateattributes(p.sedimentation_rate_min,{'numeric'},{'scalar','real','finite','positive'});
validateattributes(p.sedimentation_rate_max,{'numeric'}, ...
    {'scalar','real','finite','>',p.sedimentation_rate_min});
validateattributes(p.sedimentation_rate_step,{'numeric'},{'scalar','real','finite','positive'});
rateGrid=(p.sedimentation_rate_min:p.sedimentation_rate_step:p.sedimentation_rate_max)';
assert(numel(rateGrid)>=2&&numel(rateGrid)<=2001,'Harness:COCORateGrid', ...
    'The sedimentation-rate grid must contain 2 to 2001 points.');
raw=readmatrix(request.input_path);
assert(isnumeric(raw)&&isreal(raw)&&size(raw,2)==2, ...
    'Harness:Columns','Input must contain exactly two numeric depth/value columns.');
rawMetres=raw; rawMetres(:,1)=rawMetres(:,1)*factor;
% The original preparation is used only for full-record methods. Interleaved
% eCOCO must split cleaned raw observations before any interpolation.
if strcmp(operation,'ecoco')&&strcmp(p.method,'interleaved')
    inputData=rawMetres;
    finite=rawMetres(all(isfinite(rawMetres),2),:);
    finite=sortrows(finite,1);
    [u,~,group]=unique(finite(:,1),'sorted');
    clean=[u,accumarray(group,finite(:,2),[],@mean)];
    assert(size(clean,1)>=16,'Harness:TooFewRows','At least 16 distinct finite observations required.');
    dt=median(diff(clean(:,1)));
    prepared=[];
    preparation=struct('method','interleaved raw split before fold-specific interpolation', ...
        'fullRecordInterpolation',false,'originalRowCount',size(raw,1),'uniqueDepthCount',size(clean,1));
else
    [prepared,preparation,clean]=cocoPrepareRegularData(rawMetres,'Harness COCO/eCOCO', ...
        'MaximumPoints',200000,'MinimumPoints',16,'Verbose',false);
    inputData=rawMetres;
    dt=preparation.outputSpacing;
end
assert(isfinite(dt)&&dt>0,'Harness:COCOGrid','Invalid median depth spacing.');
preprocessTrend=[];
if ~strcmp(p.detrend,'linear')
    if isfield(p,'detrend_window')
        validateattributes(p.detrend_window,{'numeric'}, ...
            {'scalar','real','finite','positive','<=',(clean(end,1)-clean(1,1))/factor});
        smoothSpan=p.detrend_window*factor/(clean(end,1)-clean(1,1));
    else
        smoothSpan=p.span;
    end
    validateattributes(smoothSpan,{'numeric'},{'scalar','real','finite','>',0,'<=',1});
    % Extracted detrending.m callback: LOWESS/LOESS via MATLAB smooth, then
    % subtract fitted trend. A physical width is expressed as record-span
    % fraction, as in Acycle; it is not a new distance-kernel estimator.
    preprocessTrend=smooth(clean(:,1),clean(:,2),smoothSpan,p.detrend);
    inputData=[clean(:,1),clean(:,2)-preprocessTrend];
    [prepared,postDetrendPreparation]=cocoPrepareRegularData(inputData, ...
        'Harness detrended input','MaximumPoints',200000,'MinimumPoints',16,'Verbose',false);
    preparation.nonlinearDetrend=struct('method',p.detrend,'spanFraction',smoothSpan, ...
        'source','code/guicode/detrending.m smooth callback', ...
        'order','clean; nonlinear smooth subtraction; original median-grid interpolation; original internal linear detrending', ...
        'nullConditioning','Monte Carlo conditional on preprocessed record; global nonlinear trend is not re-estimated in each null');
    preparation.afterDetrend=postDetrendPreparation;
end
if isfield(p,'dt')
    validateattributes(p.dt,{'numeric'},{'scalar','real','finite','positive'});
    requestedDt=p.dt*factor;
    requestedCount=floor((clean(end,1)-clean(1,1))/requestedDt)+1;
    assert(requestedCount>=16&&requestedCount<=200000,'Harness:COCOGrid', ...
        'Explicit dt must generate 16 to 200000 points.');
    assert(strcmp(which('interpolate'),fullfile(root,'code','seriesanalysis','interpolate.m')), ...
        'Harness:FunctionShadowed','Missing or shadowed Acycle interpolate function.');
    if strcmp(p.detrend,'linear'), interpolationInput=clean;
    else, interpolationInput=inputData;end
    % The modern core derives dt from its input and overrides caller dt.
    % Therefore run the original Acycle interpolation function first, after
    % optional nonlinear detrending, to honor an explicitly requested grid.
    inputData=interpolate(interpolationInput,requestedDt);
    [prepared,resampledPreparation]=cocoPrepareRegularData(inputData, ...
        'Harness explicit interpolation','MaximumPoints',200000,'MinimumPoints',16,'Verbose',false);
    dt=resampledPreparation.outputSpacing;
    preparation.requestedInterpolation=struct('function','interpolate', ...
        'source','code/seriesanalysis/interpolate.m','requestedIntervalInputUnit',p.dt, ...
        'requestedIntervalMetres',requestedDt,'afterNonlinearDetrending',~strcmp(p.detrend,'linear'));
    preparation.afterRequestedInterpolation=resampledPreparation;
end
windowCount=1;
if strcmp(operation,'coco')
    p.slices=getDefault(p,'slices',1);
    validateattributes(p.slices,{'numeric'}, ...
        {'scalar','real','finite','integer','>=',1,'<=',min(20,floor(size(prepared,1)/16))});
    defaultNfft=2^nextpow2(size(prepared,1));
else
    assert(isfield(p,'window')&&isfield(p,'step'),'Harness:COCOWindow', ...
        'eCOCO requires window and step in the declared input depth unit.');
    span=clean(end,1)-clean(1,1);
    validateattributes(p.window,{'numeric'}, ...
        {'scalar','real','finite','positive','<=',span/factor});
    validateattributes(p.step,{'numeric'},{'scalar','real','finite','positive'});
    windowMetres=p.window*factor; stepMetres=p.step*factor;
    assert(windowMetres>=16*dt,'Harness:COCOWindow','Window must span at least 16 median sample intervals.');
    windowCount=floor((span-windowMetres)/stepMetres)+1;
    assert(windowCount>=2&&windowCount<=2001,'Harness:COCOWindowCount', ...
        'eCOCO requires 2 to 2001 complete windows; reduce window or step.');
    defaultNfft=2^nextpow2(ceil(windowMetres/dt)+2);
end
p.nfft=getDefault(p,'nfft',defaultNfft);
validateattributes(p.nfft,{'numeric'},{'scalar','real','finite','integer','>=',16,'<=',262144});
assert(numel(rateGrid)*windowCount*(p.nsim+1)<=1e7,'Harness:COCOBudget', ...
    'Requested rate-by-window-by-simulation workload exceeds 10 million evaluations.');
artifacts=struct();
artifacts.input_metres_csv=fullfile(out,'input_metres.csv'); writematrix(rawMetres,artifacts.input_metres_csv);
artifacts.cleaned_metres_csv=fullfile(out,'cleaned_metres.csv'); writematrix(clean,artifacts.cleaned_metres_csv);
if ~isempty(prepared)
    artifacts.prepared_metres_csv=fullfile(out,'prepared_metres.csv'); writematrix(prepared,artifacts.prepared_metres_csv);
end
if ~isempty(preprocessTrend)
    artifacts.detrended_input_csv=fullfile(out,'detrended_input.csv'); writematrix(inputData,artifacts.detrended_input_csv);
    artifacts.preprocessing_trend_csv=fullfile(out,'preprocessing_trend.csv'); writematrix([clean(:,1),preprocessTrend],artifacts.preprocessing_trend_csv);
end
artifacts.orbital_periods_csv=fullfile(out,'orbital_periods_kyr.csv'); writematrix(periods,artifacts.orbital_periods_csv);
warnings={'The tested age/periods and rate grid are assumptions; COCO does not independently establish astronomical forcing.', ...
    'Monte Carlo inference conditions on the input/preprocessing and chosen search; trying multiple settings adds selection not covered by a single run.'};
if ~strcmp(p.detrend,'linear')
    warnings{end+1}='LOWESS/LOESS is a global preprocessing assumption. Monte Carlo conditions on that transformed record; it does not repeat trend estimation in every surrogate.';
end
if p.nsim<999
    warnings{end+1}='Fewer than 999 Monte Carlo draws: use as exploratory/testing evidence; inspect p resolution and precision before scientific inference.';
end
summary=struct('input_rows',size(raw,1),'depth_unit_input',char(p.depth_unit), ...
    'depth_unit_analysis','m','depth_to_metres_factor',factor,'sampling_interval_m',dt, ...
    'method',p.method,'orbital_periods_kyr',periods(:)', ...
    'target_source',targetSource,'rate_unit','cm/kyr','rate_count',numel(rateGrid), ...
    'nsim_requested',p.nsim,'seed',p.seed,'minimum_resolvable_p',1/(p.nsim+1), ...
    'preparation',preparation);
if hasAge, summary.target_age_rounded_ma=round(p.middle_age_ma); end
figures=gobjects(0,1); numerical=struct();
if strcmp(operation,'coco')
    if strcmp(p.method,'adaptive'), targetMode='adaptive9b'; else, targetMode='adaptive'; end
    [corrCI,corrH0,nullCorrelation,details]=corrcoefslices_rankNew(inputData,periods,dt, ...
        p.nfft,p.sedimentation_rate_min,p.sedimentation_rate_max,p.sedimentation_rate_step, ...
        0,p.red_noise,p.nsim,0,p.slices,p.correlation,1/(2*dt),0,false,targetMode, ...
        'MaxFrequency',p.max_frequency,'Seed',p.seed,'ShowPeriodograms',false);
    report=cocoAdaptivePublicationReport(corrCI,corrH0,details);
    figures=plotAdaptiveCocoPublication(corrCI,corrH0,details,report, ...
        'Visible','off','TitlePrefix',sprintf('Acycle COCO (%s)',strrep(p.method,'_',' ')));
    % Display-only adaptation: the original default figure is too short for
    % its dense logarithmic p ticks. Preserve all original plots and axes.
    set(figures(1),'Units','pixels','Position',[50 50 1100 1000]);
    numerical=struct('corrCI',corrCI,'corrH0',corrH0,'nullCorrelation',nullCorrelation, ...
        'details',details,'report',report);
    artifacts.coco_csv=fullfile(out,'coco.csv');
    writetable(array2table([corrCI,corrH0], ...
        'VariableNames',{'rate_cm_kyr','rho','descriptive_parametric_p','missing_orbits', ...
        'rate_global_mc_p','contributing_orbits','local_mc_p'}),artifacts.coco_csv);
    artifacts.null_max_csv=fullfile(out,'null_max.csv'); writematrix(details.nullMax,artifacts.null_max_csv);
    summary.best_rate_cm_kyr=report.bestRate;
    summary.best_correlation=report.bestCorrelation;
    summary.minimum_rate_global_p=report.minimumGlobalP;
    summary.global_p_confidence_interval=report.globalPConfidenceInterval;
    summary.mc_threshold_resolved=report.monteCarloThresholdResolved;
    summary.nsim_completed=details.nSimCompleted;
    summary.target_mode=targetMode;
    summary.target_model=details.targetModel;
    summary.target_construction=details.targetConstruction;
    summary.null_conditioning=details.nullConditioning;
    summary.requested_period_count=numel(periods);
    summary.resolved_period_count_at_best=report.periodCountAtBest;
    summary.all_requested_periods_resolved=report.periodCountAtBest==numel(periods);
    summary.all_period_rate_range_cm_kyr=details.allNineRateRange;
    summary.interpretation=report.conclusion;
    if strcmp(p.method,'phase_averaged')
        % The original audit's statistics apply here, but its explanatory
        % prose hardcodes nine periods and can misidentify noncoherent mode
        % as coherent-nine. Preserve the original report and fix only the
        % public interpretation using original numerical metadata.
        if report.globalPass
            decision=['A sedimentation rate passes the original rate-search-corrected global p < 0.05 criterion; ', ...
                'this full-record association is exploratory, not held-out confirmation.'];
        else
            decision='No sedimentation rate passes the original rate-search-corrected global p < 0.05 criterion.';
        end
        summary.interpretation=sprintf( ...
            '%s The best rate uses %d of %d requested frequency-resolved orbital periods in a phase-averaged noncoherent target.', ...
            decision,report.periodCountAtBest,numel(periods));
        numerical.report_scope=['Original publication audit retained unchanged. Its nine-period/coherent wording ', ...
            'does not describe phase_averaged mode; summary and details give the actual target and participation counts.'];
        warnings{end+1}=['Original publication-report prose assumes nine periods/coherent synthesis. ', ...
            'The public summary corrects those labels using original numerical metadata; all statistics and figures are unchanged.'];
    end
    warnings{end+1}=report.monteCarloPrecisionQualification;
else
    calcMode=p.method; if strcmp(calcMode,'blocked'), calcMode='crossfit'; end
    consensus='supported'; if strcmp(calcMode,'crossfit'), consensus='strict'; end
    [rates,depth,rho,pLocal,pGlobal,pCOCO,score,nOrbit,tracked,details]= ...
        ecoco(inputData,[],periods,windowMetres,dt,1,0,p.red_noise,p.nfft, ...
        p.sedimentation_rate_min,p.sedimentation_rate_max,p.sedimentation_rate_step, ...
        p.nsim,0,1,0,p.correlation,1/(2*dt),0,calcMode,p.max_frequency,p.seed,0.5, ...
        'ECOCOWindowMode','physical-depth','ECOCOStepDepth',stepMetres, ...
        'BlockedConsensusPolicy',consensus,'Verbose',false);
    assert(any(isfinite(rho),'all'),'Harness:COCOUnresolved', ...
        'No resolved eCOCO correlation cells; increase window or revise physically justified target/rate grid.');
    [~,figures]=ecocoplot(rates,depth,rho,pLocal,pGlobal,pCOCO,score,nOrbit,1,details);
    numerical=struct('rates',rates,'depth',depth,'rho',rho,'pLocal',pLocal, ...
        'pGlobal',pGlobal,'pCOCO',pCOCO,'score',score,'nOrbit',nOrbit, ...
        'tracked',tracked,'details',details);
    [rateMesh,depthMesh]=ndgrid(rates,depth);
    artifacts.ecoco_csv=fullfile(out,'ecoco.csv');
    writetable(array2table([depthMesh(:),rateMesh(:),rho(:),pLocal(:),pGlobal(:),pCOCO(:),score(:),nOrbit(:)], ...
        'VariableNames',{'depth_m','rate_cm_kyr','rho','local_mc_p','rate_global_mc_p','pcoco','ridge_score','contributing_orbits'}),artifacts.ecoco_csv);
    artifacts.tracked_rate_csv=fullfile(out,'tracked_rate.csv'); writematrix(tracked,artifacts.tracked_rate_csv);
    summary.window_count=numel(depth); summary.window_m=windowMetres; summary.step_m=stepMetres;
    summary.depth_centres_m=depth(:)'; summary.edge_padding=false;
    summary.rate_global_p_scope='maximum across sedimentation-rate grid within each window only; no correction across windows';
    summary.map_global_applied=false; summary.finite_correlation_cells=sum(isfinite(rho),'all');
    summary.unresolved_correlation_cells=sum(~isfinite(rho),'all');
    summary.tracked_rate_cm_kyr=tracked(:,2)';
    summary.nsim_completed=getDefault(details,'nsimCompleted',[]);
    summary.target_mode='coherent-nine / four-group-area';
    summary.blocked_consensus_policy=consensus;
    warnings{end+1}='eCOCO rate-global p-values are not corrected across overlapping windows; ridge selection is descriptive, not an independent significance test.';
    warnings{end+1}='The tracked-rate local score range is not a confidence interval. Unresolved cells remain NaN in MAT/CSV and null in JSON.';
end
for k=1:numel(figures)
    name=sprintf('%s_figure_%d',operation,k);
    artifacts.([name,'_png'])=fullfile(out,[name,'.png']);
    artifacts.([name,'_fig'])=fullfile(out,[name,'.fig']);
    artifacts.([name,'_pdf'])=fullfile(out,[name,'.pdf']);
    % Preserve the original publication layout and panel-specific dimensions.
    set(figures(k),'Visible','off');
    exportgraphics(figures(k),artifacts.([name,'_png']),'Resolution',150);
    exportgraphics(figures(k),artifacts.([name,'_pdf']),'ContentType','vector');
    savefig(figures(k),artifacts.([name,'_fig']));
end
provenance=sourceProvenance(root,request.input_path,operation,p,hasAge);
if ~provenance.all_sources_match_reference
    warnings{end+1}=['The installed Acycle source differs from the validated reference snapshot. ', ...
        'The original entrypoints executed, but numerical compatibility of this revision is not established.'];
end
artifacts.provenance_json=fullfile(out,'provenance.json'); writeJson(artifacts.provenance_json,provenance);
artifacts.details_json=fullfile(out,'details.json'); writeJson(artifacts.details_json,numerical.details);
artifacts.analysis_mat=fullfile(out,'analysis.mat');
parameters=p;
save(artifacts.analysis_mat,'raw','rawMetres','clean','prepared','inputData','preprocessTrend', ...
    'periods','numerical','parameters','summary','provenance','-v7');
result=struct('status','success','backend','matlab','operation',operation, ...
    'parameters',p,'summary',summary,'artifacts',artifacts,'provenance',provenance, ...
    'warnings',{warnings});
end

function value=getDefault(s,key,fallback)
if isfield(s,key),value=s.(key);else,value=fallback;end
end

function value=depthFactor(unit)
units={'m','cm','mm','dm','km','ft'}; factors=[1,.01,.001,.1,1000,.3048];
index=find(strcmp(char(unit),units),1);
assert(~isempty(index),'Harness:DepthUnit','depth_unit must be m,cm,mm,dm,km or ft.');
value=factors(index);
end

function writeJson(file,data)
fid=fopen(file,'w'); assert(fid>=0,'Harness:WriteFailed','Cannot open %s',file);
cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s\n',jsonencode(data,'PrettyPrint',true));
end

function closeNewFigures(previous)
created=setdiff(findall(groot,'Type','figure'),previous);
for k=1:numel(created),if isgraphics(created(k)),close(created(k));end,end
end

function hash=sha256(file)
fid=fopen(file,'rb');assert(fid>=0,'Harness:ReadFailed','Cannot read %s',file);
cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
digest=java.security.MessageDigest.getInstance('SHA-256');digest.update(fread(fid,Inf,'*uint8'));
hash=lower(reshape(dec2hex(typecast(digest.digest(),'uint8'),2)',1,[]));
end

function provenance=sourceProvenance(root,input,operation,p,hasAge)
reference=jsondecode(fileread(fullfile(fileparts(mfilename('fullpath')),'coco_sources.json')));
files=reference.files;
for k=1:numel(files)
    sourceFile=fullfile(root,files(k).relative_path);
    files(k).exists=isfile(sourceFile);
    % A conservative snapshot includes helpers not used by every operation.
    % A removed unused helper in a future release must not invalidate an
    % otherwise completed analysis; record the mismatch instead.
    actual='';if files(k).exists,actual=sha256(sourceFile);end
    files(k).matches_reference=strcmp(actual,files(k).sha256);
    files(k).sha256=actual;
end
provenance=struct('source_repository','https://github.com/mingsongli/acycle', ...
    'reference_commit',reference.commit,'source_root',root,'files',files, ...
    'all_sources_match_reference',all([files.matches_reference]), ...
    'source_scope','Conservative dependency snapshot, including COCO family helpers; not every listed function executes in each mode.', ...
    'adapter_sha256',sha256([mfilename('fullpath'),'.m']), ...
    'input_sha256',sha256(input),'matlab_version',version,'matlab_release',version('-release'), ...
    'numerical_backend','MATLAB/Acycle original functions','plot_backend','MATLAB/Acycle original publication plotting functions', ...
    'operation',operation,'method',p.method,'orbital_target_from_age',hasAge, ...
    'upstream_api','Acycle v3.1.1 modern programmatic COCO/eCOCO; not historical legacy-paper implementation');
end
