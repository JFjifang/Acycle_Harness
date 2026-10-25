function result = acycle_swa(request)
%ACYCLE_SWA Headless Smoothed Window Averages using original Acycle code.
% The Lomb path is SWAgui -> specswafdr; MTM is spectralswafdr. Scientific
% calculations, FDR thresholds, figures and data exports remain in MATLAB.
% See docs/SWA.md and swa_sources.json for source attribution and constraints.
for name={'input_path','output_dir','acycle_root'}
    assert(isfield(request,name{1}),'Harness:SwaRequest','Missing %s.',name{1});
end
inputPath=char(java.io.File(char(request.input_path)).getCanonicalPath());
outputDir=char(java.io.File(char(request.output_dir)).getCanonicalPath());
root=char(java.io.File(char(request.acycle_root)).getCanonicalPath());
if ~isfolder(outputDir),mkdir(outputDir);end
assert(~isfile(fullfile(outputDir,'swa.mat')),'Harness:OutputExists', ...
    'Refusing to overwrite a completed SWA result.');
p=fieldOr(request,'parameters',struct());
assert(isstruct(p)&&isscalar(p),'Harness:SwaParameters','parameters must be an object.');
allowed={'method','coordinate_unit','fmax','mtm_nw','pad_factor','detrend'};
unknown=setdiff(fieldnames(p),allowed);
assert(isempty(unknown),'Harness:SwaParameter','Unknown SWA parameters: %s',strjoin(unknown,', '));
p.method=fieldOr(p,'method','lomb');
p.coordinate_unit=fieldOr(p,'coordinate_unit','input unit');
assert(any(strcmp(p.method,{'lomb','mtm'})),'Harness:SwaMethod','method must be lomb or mtm.');
assert(ischar(p.coordinate_unit)||(isstring(p.coordinate_unit)&&isscalar(p.coordinate_unit)), ...
    'Harness:SwaUnit','coordinate_unit must be text.');
if strcmp(p.method,'lomb')
    assert(~any(isfield(p,{'mtm_nw','pad_factor','detrend'})), ...
        'Harness:SwaLombParameters', ...
        'Lomb SWA uses its original internal detrending/tapering; MTM parameters do not apply.');
else
    p.mtm_nw=fieldOr(p,'mtm_nw',2);
    p.pad_factor=fieldOr(p,'pad_factor',1);
    p.detrend=fieldOr(p,'detrend','mean');
    validateattributes(p.mtm_nw,{'numeric'},{'scalar','real','finite','>=',1,'<=',8});
    validateattributes(p.pad_factor,{'numeric'},{'scalar','real','finite','>=',1,'<=',10});
    assert(any(strcmp(p.detrend,{'mean','linear','none'})), ...
        'Harness:SwaDetrend','MTM SWA supports mean, linear or none.');
end
raw=readmatrix(inputPath);
assert(isnumeric(raw)&&isreal(raw)&&size(raw,2)==2, ...
    'Harness:SwaColumns','SWA input must have exactly two real numeric columns.');
clean=sortrows(raw(all(isfinite(raw),2),:),1);
assert(all(diff(clean(:,1))>0),'Harness:SwaDuplicates', ...
    'SWA requires unique coordinates; resolve duplicate measurements explicitly.');
minimum=66;
assert(size(clean,1)>=minimum && size(clean,1)<=300000, ...
    'Harness:SwaRows','This %s path requires %d to 300000 finite unique samples.',p.method,minimum);
assert(var(clean(:,2))>0,'Harness:SwaVariance','SWA requires a nonconstant series.');
spacing=diff(clean(:,1));
assert(max(spacing)<=0.3*(clean(end,1)-clean(1,1)), ...
    'Harness:SwaGap','A gap exceeds 30%% of the record span; analyze appropriate shorter segments.');
oldPath=path; oldPwd=pwd; oldVisible=get(groot,'defaultFigureVisible');
oldFigures=findall(groot,'Type','figure');
global unit2fid
oldUnit2fid=unit2fid;unit2fid=[];
baseNames={'freq','pow','pow1','swa','alphob','alphsort','VarRatio','chi2invalue','clfdr'};
baseExists=false(size(baseNames)); baseValues=cell(size(baseNames));
for k=1:numel(baseNames)
    baseExists(k)=evalin('base',sprintf('exist(''%s'',''var'')',baseNames{k}))~=0;
    if baseExists(k),baseValues{k}=evalin('base',baseNames{k});end
end
cleanup=onCleanup(@()restoreRuntime(oldPath,oldPwd,oldVisible,oldFigures,baseNames,baseExists,baseValues,oldUnit2fid)); %#ok<NASGU>
seriesPath=fullfile(root,'code','seriesanalysis'); swaPath=fullfile(root,'code','package','swa');
assert(isfolder(seriesPath)&&isfolder(swaPath),'Harness:SwaSources','Acycle SWA sources are missing.');
addpath(seriesPath,'-begin');addpath(swaPath,'-begin');
for name={'specswafdr','spectralswafdr','specswa','rho','period','hpsort'}
    assert(strcmp(which(name{1}),fullfile(swaPath,[name{1} '.m'])), ...
        'Harness:SwaShadow','Unexpected shadowing of Acycle SWA function %s.',name{1});
end
set(groot,'defaultFigureVisible','off');
% Both original entry points write fixed-name DAT files. A unique run output
% directory contains these side effects instead of overwriting the user's cwd.
cd(outputDir);
prepared=clean;
warnings={'SWA means Smoothed Window Averages. It is intended for red-noise backgrounds, not white/power-law noise or high-pass-filtered data.', ...
    'FDR control is conditional on the spectral/background model; an FDR exceedance alone does not establish astronomical forcing.', ...
    'Upstream NaN FDR columns mean no separately returned threshold (no rejection or coalesced levels); they are not zero thresholds or p-values.'};
if strcmp(p.method,'lomb')
    try
        [frequency,power,background,observedAlpha,varianceRatio,fdr,chiMultipliers]=specswafdr(prepared,0);
    catch err
        if strcmp(err.identifier,'MATLAB:badsubscript')
            error('Harness:SwaWindowSupport', ...
                ['Original specswafdr could not fit its candidate windows to this record. ', ...
                 'No alternative algorithm was substituted. Use a scientifically appropriate longer record ', ...
                 'or explicitly choose the separate MTM SWA method. Original error: %s'],err.message);
        end
        rethrow(err);
    end
    frequency=frequency(:);power=power(:);background=background(:);
    chiLevels=background*chiMultipliers(:)';
    spectrum=[frequency,power,background,chiLevels,fdr];
    observedAlpha=observedAlpha(1:numel(frequency));
    varianceRatio=varianceRatio(1:numel(frequency));
    preprocessing='Original specswafdr linear detrend, split 5% cosine taper and three Hanning smoothings; no interpolation';
    sources={'code/guicode/SWAgui.m','code/package/swa/specswafdr.m', ...
        'code/package/swa/rho.m','code/package/swa/lfitls.m','code/package/swa/ctaper.m', ...
        'code/package/swa/period.m','code/package/swa/solve.m','code/package/swa/hpsort.m', ...
        'code/package/swa/getchi2.m','code/package/swa/gammp.m','code/package/swa/gammln.m', ...
        'code/package/swa/gamser.m','code/package/swa/gammcf.m', ...
        'code/package/swa/writeFmt.m','code/package/swa/strAssign.m'};
    warnings{end+1}='Legacy Lomb SWA can fail for records too short for its selected averaging windows. Original numerical errors are reported without substituting a different method.';
else
    [uneven,~]=acycleSamplingIsUneven(prepared(:,1));
    assert(~uneven,'Harness:SwaMtmSpacing', ...
        'MTM SWA requires uniform spacing. Explicitly preprocess data or choose native Lomb SWA.');
    assert(p.mtm_nw<size(prepared,1)/2,'Harness:SwaTapers','MTM bandwidth is too large.');
    assert(size(prepared,1)*p.pad_factor<=2000000,'Harness:SwaNfft','Requested NFFT exceeds 2000000.');
    switch p.detrend
        case 'mean'
            prepared(:,2)=prepared(:,2)-mean(prepared(:,2));
        case 'linear'
            coefficients=polyfit(prepared(:,1),prepared(:,2),1);
            prepared(:,2)=prepared(:,2)-polyval(coefficients,prepared(:,1));
    end
    assert(var(prepared(:,2))>0,'Harness:SwaVariance','Detrending removed all variance.');
    spectrum=spectralswafdr(prepared,'mtm',p.mtm_nw,p.pad_factor,0);
    frequency=spectrum(:,1);power=spectrum(:,2);background=spectrum(:,3);
    chiLevels=spectrum(:,4:8);fdr=spectrum(:,9:13);
    observedAlpha=[];varianceRatio=power./background;
    preprocessing=['MATLAB ' char(p.detrend) ' detrending; original spectralswafdr MTM; no interpolation'];
    sources={'code/package/swa/spectralswafdr.m','code/package/swa/specswa.m', ...
        'code/package/swa/solve.m','code/package/swa/hpsort.m', ...
        'code/seriesanalysis/acycleMtmTaperCount.m','code/seriesanalysis/acycleSamplingIsUneven.m'};
end
assert(size(spectrum,2)==13 && numel(frequency)>=33 && isreal(spectrum) && ...
    all(isfinite(spectrum(:,1:8)),'all') && all(diff(frequency)>0) && ...
    all(power>=0) && all(background>0) && ...
    all(isnan(fdr)|isfinite(fdr)&fdr>0,'all'), ...
    'Harness:SwaOutput','Original Acycle returned invalid SWA output.');
p.fmax=fieldOr(p,'fmax',max(frequency));
validateattributes(p.fmax,{'numeric'},{'scalar','real','finite','>',min(frequency),'<=',max(frequency)});
available=all(isfinite(fdr),1);
fdrLevels=[0.10,0.05,0.01,0.001,0.0001];
fdrExceedances=NaN(1,5);
for k=1:5
    if available(k),fdrExceedances(k)=sum(power>fdr(:,k));end
end
indices=find(power(2:end-1)>power(1:end-2) & power(2:end-1)>=power(3:end))+1;
indices=indices(frequency(indices)>0 & frequency(indices)<=p.fmax);
[~,order]=sort(power(indices),'descend');indices=indices(order(1:min(10,numel(order))));
peaks=struct('frequency',{},'period',{},'power',{},'above_pointwise_95',{},'above_fdr_5',{});
for k=1:numel(indices)
    j=indices(k);aboveFdr=NaN;
    if available(2),aboveFdr=double(power(j)>fdr(j,2));end
    peaks(k)=struct('frequency',frequency(j),'period',1/frequency(j),'power',power(j), ...
        'above_pointwise_95',power(j)>chiLevels(j,2),'above_fdr_5',aboveFdr);
end
artifacts=struct('cleaned_csv',fullfile(outputDir,'swa-cleaned.csv'), ...
    'prepared_csv',fullfile(outputDir,'swa-prepared.csv'), ...
    'spectrum_csv',fullfile(outputDir,'swa-spectrum.csv'), ...
    'spectrum_png',fullfile(outputDir,'swa-spectrum.png'), ...
    'spectrum_fig',fullfile(outputDir,'swa-spectrum.fig'), ...
    'analysis_mat',fullfile(outputDir,'swa.mat'), ...
    'provenance_json',fullfile(outputDir,'swa-provenance.json'));
writematrix(clean,artifacts.cleaned_csv);writematrix(prepared,artifacts.prepared_csv);
columnNames={'frequency','power','swa_background','chi90','chi95','chi99','chi999','chi9999', ...
    'fdr10','fdr5','fdr1','fdr01','fdr001'};
writetable(array2table(spectrum,'VariableNames',columnNames),artifacts.spectrum_csv);
% Presentation adapted from SWAgui refreshSWAfigure / spectralswafdr plot.
% Original threshold arrays are plotted unchanged; no Python rendering.
fig=figure('Color','white','Position',[50 50 1100 650]);
semilogy(frequency,power,'k','DisplayName','Power');hold on;
semilogy(frequency,background,'Color',[0.2 0.5 0.2],'LineWidth',2,'DisplayName','SWA background');
semilogy(frequency,chiLevels(:,2),'r--','DisplayName','95% pointwise chi-square');
colors=lines(5);
for k=1:5
    if available(k)
        semilogy(frequency,fdr(:,k),'Color',colors(k,:),'LineWidth',1.3, ...
            'DisplayName',sprintf('%g%% FDR',100*fdrLevels(k)));
    end
end
xlim([max(0,min(frequency)),p.fmax]);grid on;legend('Location','best');
xlabel(['Frequency (cycles / ' char(p.coordinate_unit) ')'],'Interpreter','none');ylabel('Power');
title(['Acycle SWA: ' upper(char(p.method))],'Interpreter','none');
exportgraphics(fig,artifacts.spectrum_png,'Resolution',150);savefig(fig,artifacts.spectrum_fig);
originalDat=dir(fullfile(outputDir,'SWA-*.dat'));
for k=1:numel(originalDat)
    artifacts.(sprintf('original_dat_%d',k))=fullfile(outputDir,originalDat(k).name);
end
provenance=sourceProvenance(root,sources);
provenance.input_sha256=fileHash(inputPath);
provenance.matlab_version=version;provenance.matlab_release=version('-release');
provenance.toolboxes=ver;provenance.adapter_sha256=fileHash([mfilename('fullpath') '.m']);
provenance.preprocessing=preprocessing;
summary=struct('input_rows',size(raw,1),'removed_nonfinite_rows',size(raw,1)-size(clean,1), ...
    'processed_rows',size(prepared,1),'interpolated',false,'method',p.method, ...
    'coordinate_unit',p.coordinate_unit,'frequency_count',numel(frequency), ...
    'fdr_levels',fdrLevels,'fdr_threshold_available',available, ...
    'fdr_exceeding_frequency_bins',fdrExceedances,'peaks',peaks);
parameters=p; %#ok<NASGU>
save(artifacts.analysis_mat,'raw','clean','prepared','spectrum','frequency','power', ...
    'background','chiLevels','fdr','observedAlpha','varianceRatio','columnNames', ...
    'parameters','summary','provenance','-v7');
writeJson(artifacts.provenance_json,provenance);
result=struct('status','success','backend','matlab','operation','swa','parameters',p, ...
    'summary',summary,'artifacts',artifacts,'provenance',provenance,'warnings',{warnings});
end

function value=fieldOr(s,name,fallback)
if isfield(s,name),value=s.(name);else,value=fallback;end
end

function restoreRuntime(oldPath,oldPwd,visible,oldFigures,names,existed,values,oldUnit2fid)
global unit2fid
unit2fid=oldUnit2fid;
cd(oldPwd);path(oldPath);set(groot,'defaultFigureVisible',visible);
newFigures=setdiff(findall(groot,'Type','figure'),oldFigures);
for k=1:numel(newFigures),if isgraphics(newFigures(k)),close(newFigures(k));end,end
for k=1:numel(names)
    if existed(k),assignin('base',names{k},values{k});else,evalin('base',['clear ' names{k}]);end
end
end

function result=sourceProvenance(root,paths)
registry=jsondecode(fileread(fullfile(fileparts(mfilename('fullpath')),'swa_sources.json')));
files=struct('relative_path',{},'sha256',{},'matches_reference',{});
for k=1:numel(paths)
    actual=fileHash(fullfile(root,paths{k}));match=false;
    for j=1:numel(registry.files)
        if strcmp(paths{k},registry.files(j).relative_path)
            match=strcmp(actual,registry.files(j).sha256);break;
        end
    end
    files(k)=struct('relative_path',paths{k},'sha256',actual,'matches_reference',match);
end
result=struct('source_repository','https://github.com/mingsongli/acycle', ...
    'reference_commit',registry.commit,'source_root',root,'files',files, ...
    'all_used_sources_match_reference',all([files.matches_reference]), ...
    'numerical_backend','MATLAB/Acycle original SWA functions','plot_backend','MATLAB', ...
    'method_name','Smoothed Window Averages','adapter','acycle-swa-v1');
end

function hash=fileHash(path)
fid=fopen(path,'rb');assert(fid~=-1,'Harness:SwaRead','Cannot read %s.',path);
cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
bytes=fread(fid,Inf,'*uint8');digest=java.security.MessageDigest.getInstance('SHA-256');digest.update(bytes);
hash=lower(reshape(dec2hex(typecast(digest.digest(),'uint8'),2)',1,[]));
end

function writeJson(path,value)
fid=fopen(path,'w');assert(fid~=-1,'Harness:SwaWrite','Cannot write %s.',path);
cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s\n',jsonencode(value,'PrettyPrint',true));
end
