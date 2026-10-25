function result = acycle_batch(requestPath,responsePath)
%ACYCLE_BATCH Headless JSON adapter: all scientific calculations and graphics
% run in MATLAB, primarily through the installed Acycle source checkout.
% See SOURCES.md for the small GUI callback extraction and exact provenance.
try
    request = jsondecode(fileread(requestPath));
    operation = getDefault(request,'operation','analyze');
    switch operation
        case 'swa'
            result = acycle_swa(request);
        case {'coco','ecoco'}
            result = acycle_coco(request);
        case 'interpolate_pro'
            result = acycle_interpolate_pro(request);
        case 'tune'
            result = acycle_tune(request);
        case 'analyze'
            result = runRequest(request);
        otherwise
            error('Harness:Operation','Unsupported operation: %s',operation);
    end
    writeJson(responsePath,result);
catch err
    result = struct('status','error','backend','matlab','error', ...
        struct('identifier',err.identifier,'message',err.message));
    % An accidental repeat must not replace an earlier successful receipt.
    if ~isfile(responsePath), writeJson(responsePath,result); end
    rethrow(err);
end
end

function result = runRequest(request)
required = {'input_path','output_dir','acycle_root'};
for k=1:numel(required)
    assert(isfield(request,required{k}), 'Harness:MissingField', ...
        'Missing request field: %s',required{k});
end
operation = getDefault(request,'operation','analyze');
assert(strcmp(operation,'analyze'),'Harness:Operation','Only analyze is supported.');
root = char(request.acycle_root);
seriesPath = fullfile(root,'code','seriesanalysis');
assert(isfolder(seriesPath),'Harness:AcycleMissing','Acycle source directory is missing.');
oldPath = path; restorePath = onCleanup(@()path(oldPath)); %#ok<NASGU>
addpath(seriesPath,'-begin');
% Only the scientific directory is added; GUI and third-party package folders
% are deliberately not recursively placed ahead of MATLAB toolbox functions.
requiredFunctions = {'interpolate','findduplicate','redconfML','evofft', ...
    'zeropad2','acycleSamplingIsUneven','acycleMtmTaperCount'};
for k=1:numel(requiredFunctions)
    assert(isfile(fullfile(seriesPath,[requiredFunctions{k} '.m'])), ...
        'Harness:AcycleFunctionMissing','Missing Acycle function: %s',requiredFunctions{k});
    assert(strcmp(which(requiredFunctions{k}),fullfile(seriesPath,[requiredFunctions{k} '.m'])), ...
        'Harness:FunctionShadowed','Acycle function is shadowed: %s',requiredFunctions{k});
end
oldVisible = get(groot,'defaultFigureVisible');
set(groot,'defaultFigureVisible','off');
restoreVisible = onCleanup(@()set(groot,'defaultFigureVisible',oldVisible)); %#ok<NASGU>
oldFigures = findall(groot,'Type','figure');
closeFigures = onCleanup(@()closeNewFigures(oldFigures)); %#ok<NASGU>
outputDir = char(request.output_dir);
if ~isfolder(outputDir), mkdir(outputDir); end
assert(~isfile(fullfile(outputDir,'analysis.mat')), ...
    'Harness:OutputExists','Refusing to overwrite an existing completed analysis.');
p = getDefault(request,'parameters',struct());
assert(isstruct(p)&&isscalar(p),'Harness:Parameters','parameters must be a JSON object.');
allowed = {'detrend','span','dt','mtm_nw','nfft','smooth_fraction','fmax', ...
    'evolution','evolution_window','evolution_step','filter_band','filter_method', ...
    'sedimentation_rate','depth_unit','first_age_kyr','age_model', ...
    'coordinate_unit','fit_fmax','rolloff_exponent','coordinate_range'};
unknown = setdiff(fieldnames(p),allowed);
assert(isempty(unknown),'Harness:UnknownParameter','Unknown parameters: %s',strjoin(unknown,', '));
p.detrend = getDefault(p,'detrend','lowess');
p.span = getDefault(p,'span',0.35);
p.mtm_nw = getDefault(p,'mtm_nw',2);
p.smooth_fraction = getDefault(p,'smooth_fraction',0.25);
p.evolution = getDefault(p,'evolution',true);
p.coordinate_unit = getDefault(p,'coordinate_unit','input unit');
assert(islogical(p.evolution)&&isscalar(p.evolution), ...
    'Harness:Evolution','evolution must be a boolean.');
validateattributes(p.span,{'numeric'},{'scalar','real','finite','>',0,'<=',1});
validateattributes(p.mtm_nw,{'numeric'},{'scalar','real','finite','>=',1,'<=',8});
validateattributes(p.smooth_fraction,{'numeric'},{'scalar','real','finite','>',0,'<=',0.25});
assert(any(strcmp(p.detrend,{'none','mean','linear','lowess','rlowess','loess','rloess'})), ...
    'Harness:Detrend','Unsupported detrending method.');
raw = readmatrix(request.input_path);
assert(isnumeric(raw)&&isreal(raw)&&size(raw,2)==2, ...
    'Harness:Columns','Input must contain exactly two numeric columns: coordinate,value.');
inputRows = size(raw,1);
clean = raw(all(isfinite(raw),2),:);
removedRows = inputRows-size(clean,1);
assert(size(clean,1)>=16,'Harness:TooFewRows','At least 16 finite data rows are required.');
% Extracted RobotGUI preparation: remove non-finite, sort, merge duplicate
% coordinates using the ORIGINAL findduplicate implementation (mean values).
clean = sortrows(clean);
uniqueRowsBefore = size(clean,1);
clean = findduplicate(clean);
duplicateRows = uniqueRowsBefore-size(clean,1);
if isfield(p,'coordinate_range')
    range=p.coordinate_range(:);
    assert(numel(range)==2 && all(isfinite(range)) && range(2)>range(1), ...
        'Harness:CoordinateRange','coordinate_range requires two increasing finite input-coordinate bounds.');
    % Explicit adapter selection occurs in MATLAB before depth-to-time conversion.
    % This retains the original proxy only inside the saved tuning control interval.
    clean=clean(clean(:,1)>=range(1) & clean(:,1)<=range(2),:);
end
selectedRows=size(clean,1);
assert(size(clean,1)>=16 && all(diff(clean(:,1))>0), ...
    'Harness:Coordinates','At least 16 unique increasing coordinates are required.');
sourceNames = {'RobotGUI','findduplicate','interpolate','acycleSamplingIsUneven', ...
    'redconfML','rhoAR1','moveMedian','minirhos0','acycleMtmTaperCount'};
notes = {'Pointwise robust AR(1) levels do not control multiple testing and are not proof of orbital forcing.'};
ageModel = []; ageRates = []; ageMeta = struct();
if isfield(p,'sedimentation_rate')
    assert(~isfield(p,'age_model'),'Harness:AgeConflict','Choose rate or age_model, not both.');
    assert(isfield(p,'depth_unit'),'Harness:DepthUnit','sedimentation_rate requires depth_unit.');
    validateattributes(p.sedimentation_rate,{'numeric'},{'real','finite','scalar','positive'});
    p.first_age_kyr = getDefault(p,'first_age_kyr',0);
    [ageModel,ageMeta] = acycleSedimentationRateAgeModel( ...
        [clean(:,1),repmat(p.sedimentation_rate,size(clean,1),1)], ...
        p.depth_unit,p.first_age_kyr);
    [time,ageRates] = depthtotime(clean(:,1),ageModel);
    clean(:,1) = time;
    p.coordinate_unit = 'kyr';
    sourceNames = [sourceNames,{'acycleSedimentationRateAgeModel','depthtotime'}];
    notes{end+1} = 'Age conversion uses an assumed rate in cm/kyr; it does not independently validate orbital tuning.';
elseif isfield(p,'age_model')
    ageModel = p.age_model;
    assert(isnumeric(ageModel)&&isreal(ageModel)&&size(ageModel,2)==2 && ...
        size(ageModel,1)>=2 && all(isfinite(ageModel),'all') && ...
        all(diff(ageModel(:,1))>0) && all(diff(ageModel(:,2))>0), ...
        'Harness:AgeModel','age_model requires increasing finite [depth,age_kyr] tie points.');
    assert(ageModel(1,1)<=clean(1,1)&&ageModel(end,1)>=clean(end,1), ...
        'Harness:AgeCoverage','Age tie points must cover all data; extrapolation is disabled.');
    [time,ageRates] = depthtotime(clean(:,1),ageModel);
    clean(:,1) = time;
    p.coordinate_unit = 'kyr';
    sourceNames{end+1} = 'depthtotime';
end
p.dt = getDefault(p,'dt',mean(diff(clean(:,1))));
validateattributes(p.dt,{'numeric'},{'real','finite','scalar','positive'});
assert((clean(end,1)-clean(1,1))/p.dt <= 200000, ...
    'Harness:GridLimit','Requested interpolation grid exceeds 200000 rows.');
[uneven,samplingInfo] = acycleSamplingIsUneven(clean(:,1));
interpolated = uneven || abs(p.dt-samplingInfo.MedianSpacing)>samplingInfo.AbsoluteTolerance;
if interpolated
    prepared = interpolate(clean,p.dt);
else
    prepared = clean;
end
assert(size(prepared,1)>=16 && all(isfinite(prepared),'all'), ...
    'Harness:PreparedData','Interpolation must produce at least 16 finite rows.');
dt = median(diff(prepared(:,1)));
p.dt = dt;
x = prepared(:,1); y = prepared(:,2);
% Extracted exactly from RobotGUI.m detrending callback, with explicit none.
switch p.detrend
    case 'none'
        trend = zeros(size(y));
    case 'mean'
        trend = repmat(mean(y),size(y));
    case 'linear'
        coefficients = polyfit(x,y,1);
        trend = x*coefficients(1)+coefficients(2);
    otherwise
        trend = smooth(x,y,p.span,p.detrend);
end
processed = [x,y-trend];
assert(var(processed(:,2))>0 && all(isfinite(processed),'all'), ...
    'Harness:Variance','Processed series must have finite nonzero variance.');
p.nfft = getDefault(p,'nfft',5*size(processed,1));
validateattributes(p.nfft,{'numeric'},{'scalar','real','finite','integer','>=',size(processed,1),'<=',2000000});
assert(p.mtm_nw < size(processed,1)/2,'Harness:Tapers','MTM bandwidth is too large for the record.');
nyquist = 1/(2*dt);
p.fmax = getDefault(p,'fmax',nyquist);
validateattributes(p.fmax,{'numeric'},{'scalar','real','finite','positive','<=',nyquist});
p.fit_fmax = getDefault(p,'fit_fmax',nyquist);
validateattributes(p.fit_fmax,{'numeric'},{'scalar','real','finite','positive','<=',nyquist});
artifacts = struct();
artifacts.cleaned_csv = fullfile(outputDir,'cleaned.csv');
artifacts.prepared_csv = fullfile(outputDir,'prepared.csv');
artifacts.processed_csv = fullfile(outputDir,'processed.csv');
writematrix(clean,artifacts.cleaned_csv);
writematrix(prepared,artifacts.prepared_csv);
writematrix([processed,trend],artifacts.processed_csv);
fig = figure('Color','white','Position',[50 50 1000 600]);
subplot(2,1,1); plot(x,y,'Color',[0.35 0.35 0.35]); hold on;
plot(x,trend,'r'); legend('Prepared data','Trend'); ylabel('Proxy value'); grid on;
subplot(2,1,2); plot(x,processed(:,2),'k'); ylabel('Detrended value');
xlabel(p.coordinate_unit,'Interpreter','none'); grid on;
artifacts.preprocess_png = savePlot(fig,outputDir,'preprocessing');
% Original Acycle numerical algorithm AND original redconfML figure.
if nargin('redconfML')>=9
    [rho,s0,classic,robust] = redconfML(processed(:,2),dt,p.mtm_nw, ...
        p.nfft,2,p.smooth_fraction,p.fmax,1,p.fit_fmax);
else
    assert(p.fit_fmax==nyquist,'Harness:UnsupportedFitRange', ...
        'Installed Acycle does not support explicit fit_fmax.');
    [rho,s0,classic,robust] = redconfML(processed(:,2),dt,p.mtm_nw, ...
        p.nfft,2,p.smooth_fraction,p.fmax,1);
end
fitMethod='original_redconfML';
if ~validRobustFit(rho,s0,robust)
    % Upstream's unconstrained lsqcurvefit can return complex/nonstationary
    % parameters without throwing. Use the upstream grid-search alternative
    % and confidence expressions explicitly, rather than exporting them.
    close(gcf);
    [rho,s0,robust]=originalGridFallback(classic,p,nyquist);
    fitMethod='original_minirhos0_after_invalid_optimizer_fit';
    notes{end+1}=['Original redconfML returned a nonphysical optimizer fit; ', ...
        'Acycle minirhos0 grid search was used with the same median spectrum.'];
end
assert(validRobustFit(rho,s0,robust), ...
    'Harness:InvalidSpectrum','Acycle returned invalid AR(1) spectrum or confidence levels.');
artifacts.spectrum_png = savePlot(gcf,outputDir,'spectrum');
artifacts.robust_spectrum_csv = fullfile(outputDir,'spectrum_robust.csv');
artifacts.classic_spectrum_csv = fullfile(outputDir,'spectrum_classic.csv');
writematrix(robust,artifacts.robust_spectrum_csv); writematrix(classic,artifacts.classic_spectrum_csv);
% Return local maxima only, retaining pointwise thresholds as descriptive data.
power = robust(:,2); peakIndex = find(power(2:end-1)>power(1:end-2) & ...
    power(2:end-1)>=power(3:end))+1;
peakIndex = peakIndex(robust(peakIndex,1)<=p.fmax & robust(peakIndex,1)>0);
[~,order] = sort(power(peakIndex),'descend');
peakIndex = peakIndex(order(1:min(10,numel(order))));
peaks = struct('frequency',{},'period',{},'power',{},'pointwise_above_95',{});
for k=1:numel(peakIndex)
    j=peakIndex(k);
    peaks(k)=struct('frequency',robust(j,1),'period',1/robust(j,1), ...
        'power',power(j),'pointwise_above_95',power(j)>robust(j,5));
end
evolution = struct();
if p.evolution
    p.evolution_window = getDefault(p,'evolution_window',0.35*(x(end)-x(1)));
    validateattributes(p.evolution_window,{'numeric'}, ...
        {'scalar','real','finite','>=',8*dt,'<',x(end)-x(1)});
    padded = zeropad2(processed,p.evolution_window);
    defaultStep = max(1,round(size(padded,1)/300))*dt;
    p.evolution_step = getDefault(p,'evolution_step',defaultStep);
    validateattributes(p.evolution_step,{'numeric'}, ...
        {'scalar','real','finite','>=',dt,'<=',p.evolution_window/2});
    p.evolution_step = max(1,round(p.evolution_step/dt))*dt;
    % evofft has historical grid indexing. Pass full physical Nyquist as the
    % mini-robot does; apply requested fmax only to the displayed figure.
    [amplitude,frequency,coordinate] = evofft(padded,p.evolution_window, ...
        p.evolution_step,dt,0,nyquist,1);
    assert(all(isfinite(amplitude),'all'),'Harness:EvoNonfinite', ...
        'Acycle evofft returned non-finite amplitudes.');
    evolution = struct('amplitude',amplitude,'frequency',frequency, ...
        'coordinate',coordinate,'padding','zero','normalization','row maximum');
    fig = figure('Color','white','Position',[50 50 1000 600]);
    % Plot adapted from RobotGUI.m: pcolor(y_grid,x_grid,s'), jet, interp.
    pcolor(coordinate,frequency,amplitude'); shading interp; colormap(jet); colorbar;
    ylim([0 p.fmax]); xlim([x(1) x(end)]); xlabel(p.coordinate_unit,'Interpreter','none');
    ylabel('Frequency (cycles / coordinate unit)');
    title(sprintf('Acycle EvoFFT: window %.6g, step %.6g',p.evolution_window,p.evolution_step));
    artifacts.evolution_png = savePlot(fig,outputDir,'evolution');
    artifacts.evolution_csv = fullfile(outputDir,'evolution.csv');
    writematrix([NaN,frequency;coordinate(:),amplitude],artifacts.evolution_csv);
    sourceNames = [sourceNames,{'zeropad2','evofft'}];
    notes{end+1} = 'EvoFFT retains Acycle mini-robot zero padding and normalized amplitude; edge windows contain synthetic zeros.';
end
filtered = struct(); filterMeta = struct();
if isfield(p,'filter_band')
    band = p.filter_band(:);
    assert(numel(band)==2&&all(isfinite(band))&&band(1)>0&& ...
        band(2)>band(1)&&band(2)<nyquist,'Harness:FilterBand', ...
        'filter_band must satisfy 0 < lower < upper < Nyquist.');
    p.filter_method = getDefault(p,'filter_method','gaussian');
    filterOptions = struct('method',p.filter_method, ...
        'lower_frequency',band(1),'upper_frequency',band(2));
    if strcmp(p.filter_method,'taner_hilbert')
        p.rolloff_exponent = getDefault(p,'rolloff_exponent',12);
        filterOptions.rolloff_exponent = p.rolloff_exponent;
    end
    assert(isfile(fullfile(seriesPath,'acycleBandpassFilter.m')), ...
        'Harness:FilterCapability','This Acycle version does not provide acycleBandpassFilter.');
    [filtered,filterMeta] = acycleBandpassFilter(processed,filterOptions);
    artifacts.filtered_csv = fullfile(outputDir,'filtered.csv');
    writematrix([filtered.coordinate,filtered.filtered,filtered.envelope],artifacts.filtered_csv);
    fig = figure('Color','white','Position',[50 50 1000 600]);
    plot(filtered.coordinate,filtered.filtered,'k'); hold on;
    plot(filtered.coordinate,filtered.envelope,'r');
    xlabel(p.coordinate_unit,'Interpreter','none'); ylabel('Proxy value');
    legend('Acycle filtered series','Hilbert envelope'); grid on;
    artifacts.filter_png = savePlot(fig,outputDir,'filter');
    sourceNames{end+1}='acycleBandpassFilter';
    notes{end+1}='Band selection is user supplied; Hilbert envelopes near endpoints are susceptible to edge effects.';
end
if ~isempty(ageModel)
    artifacts.age_model_csv = fullfile(outputDir,'age_model.csv');
    writematrix(ageModel,artifacts.age_model_csv);
end
plotFields=fieldnames(artifacts);
for k=1:numel(plotFields)
    field=plotFields{k};
    if endsWith(field,'_png')
        artifacts.([field(1:end-4) '_fig'])=strrep(artifacts.(field),'.png','.fig');
    end
end
provenance = sourceProvenance(root,sourceNames);
provenance.matlab_version = version;
provenance.matlab_release = version('-release');
provenance.toolboxes = ver;
provenance.robust_fit_method = fitMethod;
provenance.input_sha256 = fileSha256(request.input_path);
summary = struct('input_rows',inputRows,'removed_nonfinite_rows',removedRows, ...
    'merged_duplicate_rows',duplicateRows,'selected_rows',selectedRows,'processed_rows',size(processed,1), ...
    'interpolated',interpolated,'sample_interval',dt,'nyquist',nyquist, ...
    'coordinate_unit',p.coordinate_unit,'robust_ar1_rho',rho, ...
    'robust_ar1_s0',s0,'robust_fit_method',fitMethod,'peaks',peaks);
artifacts.analysis_mat = fullfile(outputDir,'analysis.mat');
artifacts.provenance_json = fullfile(outputDir,'provenance.json');
writeJson(artifacts.provenance_json,provenance);
parameters = p; %#ok<NASGU>
save(artifacts.analysis_mat,'raw','clean','prepared','processed','trend', ...
    'classic','robust','evolution','filtered','filterMeta','ageModel', ...
    'ageRates','ageMeta','parameters','provenance','summary','-v7');
result = struct('status','success','backend','matlab','operation','analyze', ...
    'parameters',p,'summary',summary,'artifacts',artifacts, ...
    'provenance',provenance,'warnings',{notes});
end

function value = getDefault(s,name,defaultValue)
if isfield(s,name), value=s.(name); else, value=defaultValue; end
end

function valid = validRobustFit(rho,s0,robust)
valid=isreal(rho)&&isreal(s0)&&isscalar(rho)&&isscalar(s0)&& ...
    isfinite(rho)&&isfinite(s0)&&abs(rho)<1&&s0>0&& ...
    isreal(robust)&&all(isfinite(robust),'all')&&all(robust(:,3:end)>0,'all');
end

function [rho,s0,robust] = originalGridFallback(classic,p,nyquist)
% Extracted from redconfML.m, commit documented in source_registry.json:
% fit-support/median lines 124-145, minirhos0 call 176-177,
% transfer function and chi-square levels 188-197, plot 199-215.
frequency=classic(:,1); power=classic(:,2);
fitMask=frequency<=p.fit_fmax;
smoothCount=round(p.smooth_fraction*nnz(fitMask));
fitMedian=moveMedian(power(fitMask),smoothCount);
[rho,s0]=minirhos0(mean(fitMedian),nyquist,frequency(fitMask),fitMedian,2);
background=s0*(1-rho^2)./(1-2*rho*cos(pi*frequency/nyquist)+rho^2);
dof=2*acycleMtmTaperCount(p.mtm_nw);
levels=background*(chi2inv([0.90,0.95,0.99,0.999],dof)/dof);
robust=[frequency,power,background,levels];
fig=figure('Color','white','Position',[50 50 1000 600]); %#ok<NASGU>
semilogy(frequency,power,'k'); hold on;
semilogy(frequency,classic(:,3),'m-.');
semilogy(frequency,background,'k-','LineWidth',2);
semilogy(frequency,levels(:,1),'r-');
semilogy(frequency,levels(:,2),'r--','LineWidth',2);
semilogy(frequency,levels(:,3),'b-.');
semilogy(frequency,levels(:,4),'g--');
xlabel('Frequency'); ylabel('Power'); xlim([0,p.fmax]);
legend('Power','Median-smoothed','Robust AR(1) median', ...
    'Robust AR(1) 90%','Robust AR(1) 95%','Robust AR(1) 99%', ...
    'Robust AR(1) 99.9%');
title('Acycle robust AR(1): original grid-search fallback');
end

function pngPath = savePlot(fig,outputDir,name)
set(fig,'Visible','off');
pngPath = fullfile(outputDir,[name '.png']);
exportgraphics(fig,pngPath,'Resolution',150);
savefig(fig,fullfile(outputDir,[name '.fig']));
close(fig);
end

function writeJson(path,value)
payload=jsonencode(value,'PrettyPrint',true);
fid=fopen(path,'w');
assert(fid~=-1,'Harness:WriteFailed','Cannot open response file: %s',path);
cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s\n',payload);
end

function closeNewFigures(oldFigures)
newFigures=setdiff(findall(groot,'Type','figure'),oldFigures);
for k=1:numel(newFigures), if isgraphics(newFigures(k)), close(newFigures(k)); end, end
end

function hash = fileSha256(path)
fid=fopen(path,'rb'); assert(fid~=-1,'Harness:ReadFailed','Cannot read: %s',path);
cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
bytes=fread(fid,Inf,'*uint8');
digest=java.security.MessageDigest.getInstance('SHA-256');
digest.update(bytes);
hash=lower(reshape(dec2hex(typecast(digest.digest(),'uint8'),2)',1,[]));
end

function result = sourceProvenance(root,names)
known=jsondecode(fileread(fullfile(fileparts(mfilename('fullpath')),'source_registry.json')));
files=struct('function',{},'relative_path',{},'sha256',{},'matches_reference',{});
names=unique(names,'stable');
for k=1:numel(names)
    if strcmp(names{k},'RobotGUI')
        relative='code/guicode/RobotGUI.m';
    else
        relative=['code/seriesanalysis/' names{k} '.m'];
    end
    actualHash=fileSha256(fullfile(root,relative));
    match=false;
    for j=1:numel(known.files)
        if strcmp(known.files(j).relative_path,relative)
            match=strcmp(actualHash,known.files(j).sha256);
            break;
        end
    end
    files(k)=struct('function',names{k},'relative_path',relative, ...
        'sha256',actualHash,'matches_reference',match);
end
result=struct('source_repository','https://github.com/mingsongli/acycle', ...
    'reference_commit',known.commit,'installed_commit',readGitCommit(root), ...
    'source_root',root,'files',files, ...
    'all_used_sources_match_reference',all([files.matches_reference]), ...
    'adapter','matlab-first-v1','numerical_backend','MATLAB/Acycle', ...
    'plot_backend','MATLAB (original redconfML plot; other GUI plots adapted)');
end

function commit = readGitCommit(root)
commit='unknown';
headPath=fullfile(root,'.git','HEAD');
if ~isfile(headPath), return; end
head=strtrim(fileread(headPath));
if ~startsWith(head,'ref: '), commit=head; return; end
ref=head(6:end);
refPath=fullfile(root,'.git',ref);
if isfile(refPath), commit=strtrim(fileread(refPath)); return; end
packedPath=fullfile(root,'.git','packed-refs');
if isfile(packedPath)
    rows=splitlines(string(fileread(packedPath)));
    for k=1:numel(rows)
        parts=split(strtrim(rows(k)));
        if numel(parts)==2 && strcmp(parts(2),ref), commit=char(parts(1)); return; end
    end
end
end
