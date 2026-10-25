function result = acycle_interpolate_pro(request)
%ACYCLE_INTERPOLATE_PRO Source-linked extraction of Interpolation Pro GUI.
% Acycle interpolationGUI.m:34, 103-108, 152-218 supplies the nine methods,
% colon grid, interp1 call, and optional zero-gap rule. There is no public
% headless Pro core upstream; acycleInterpolateSeries is LINEAR ONLY and is
% deliberately not substituted. See INTERPOLATION_TUNING_SOURCES.md.
for name={'input_path','output_dir','acycle_root'}
    assert(isfield(request,name{1}),'Harness:InterpolationRequest','Missing %s.',name{1});
end
out=char(request.output_dir); root=char(request.acycle_root);
assert(isfile(fullfile(root,'code','guicode','interpolationGUI.m')), ...
    'Harness:InterpolationSource','Original Acycle interpolationGUI.m is required.');
if ~isfolder(out),mkdir(out);end
assert(~isfile(fullfile(out,'analysis.mat')),'Harness:OutputExists', ...
    'Refusing to overwrite a completed Interpolation Pro result.');
p=fieldOr(request,'parameters',struct());
assert(isstruct(p)&&isscalar(p),'Harness:InterpolationParameters','parameters must be an object.');
allowed={'method','dt','coordinate_unit','gap_policy','gap_multiplier','endpoint_policy'};
unknown=setdiff(fieldnames(p),allowed);
assert(isempty(unknown),'Harness:UnknownParameter','Unknown Interpolation Pro parameters: %s',strjoin(unknown,', '));
p.method=char(fieldOr(p,'method','linear'));
p.coordinate_unit=char(fieldOr(p,'coordinate_unit','input unit'));
p.gap_policy=char(fieldOr(p,'gap_policy','interpolate'));
p.gap_multiplier=fieldOr(p,'gap_multiplier',10);
p.endpoint_policy=char(fieldOr(p,'endpoint_policy','gui'));
methods={'linear','nearest','next','previous','pchip','cubic','v5cubic','makima','spline'};
assert(any(strcmp(p.method,methods)),'Harness:InterpolationMethod','Unsupported Interpolation Pro method.');
assert(any(strcmp(p.gap_policy,{'interpolate','zero'})), ...
    'Harness:InterpolationGap','gap_policy must be interpolate or zero.');
assert(any(strcmp(p.endpoint_policy,{'gui','strict_grid'})), ...
    'Harness:InterpolationEndpoint','endpoint_policy must be gui or strict_grid.');
validateattributes(p.gap_multiplier,{'numeric'},{'scalar','real','finite','positive'});
raw=readmatrix(request.input_path);
assert(isnumeric(raw)&&isreal(raw)&&size(raw,2)==2&&size(raw,1)>=2, ...
    'Harness:InterpolationColumns','Interpolation Pro requires at least two real numeric coordinate/value rows.');
% The original Pro GUI sorts only. Reject ambiguity instead of silently
% importing the different mini-robot duplicate/nonfinite cleanup policy.
assert(all(isfinite(raw),'all'),'Harness:InterpolationNonfinite', ...
    'Interpolation Pro requires finite data; explicitly preprocess nonfinite rows first.');
clean=sortrows(raw,1);
assert(all(diff(clean(:,1))>0),'Harness:InterpolationDuplicates', ...
    'Interpolation Pro requires unique coordinates; resolve duplicate measurements explicitly.');
span=clean(end,1)-clean(1,1);
assert(isfinite(span)&&span>0,'Harness:InterpolationSpan','Coordinate span must be finite and positive.');
inputMedian=median(diff(clean(:,1)));
defaultDt=str2double(num2str(inputMedian,'%.10g')); % original GUI edit-box precision
p.dt=fieldOr(p,'dt',defaultDt);
validateattributes(p.dt,{'numeric'},{'scalar','real','finite','positive'});
gapThreshold=p.dt*p.gap_multiplier;
assert(isfinite(gapThreshold)&&gapThreshold>0,'Harness:InterpolationGap', ...
    'The requested gap threshold must be representable as a finite positive value.');
assert(span/p.dt<200000,'Harness:InterpolationGridLimit', ...
    'Interpolation Pro output is limited to 200000 points.');
if strcmp(p.endpoint_policy,'strict_grid')
    assert(p.dt<=span,'Harness:InterpolationEndpoint', ...
        'strict_grid requires dt no greater than the record span; no two-endpoint fallback is allowed.');
end
% Exact original GUI grid and method dispatch (no extrapolation argument).
xq=clean(1,1):p.dt:clean(end,1);
usedFallback=numel(xq)<2;
if usedFallback,xq=linspace(clean(1,1),clean(end,1),2);end
assert(numel(xq)<=200000&&all(isfinite(xq))&&all(diff(xq)>0), ...
    'Harness:InterpolationGrid','Requested grid is not representable or exceeds the point limit.');
vq=interp1(clean(:,1),clean(:,2),xq,p.method);
gaps=zeros(0,2); gapMask=false(size(xq));
if strcmp(p.gap_policy,'zero')
    spacing=diff(clean(:,1));
    for k=1:numel(spacing)
        if spacing(k)>gapThreshold
            gaps(end+1,:)=[clean(k,1),clean(k+1,1)]; %#ok<AGROW>
            inside=xq>clean(k,1)&xq<clean(k+1,1);
            vq(inside)=0; gapMask=gapMask|inside;
        end
    end
end
interpolated=[xq(:),vq(:)];
assert(isreal(interpolated)&&all(isfinite(interpolated),'all'), ...
    'Harness:InterpolationOutput','Original GUI interpolation produced nonfinite or complex values.');
actualSpacing=diff(xq);
summary=struct('input_rows',size(raw,1),'processed_rows',size(interpolated,1), ...
    'sorted',~isequal(raw,clean),'removed_nonfinite_rows',0,'merged_duplicate_rows',0, ...
    'method',p.method,'coordinate_unit',p.coordinate_unit,'requested_dt',p.dt, ...
    'input_median_spacing',inputMedian,'sample_interval',median(actualSpacing), ...
    'minimum_output_spacing',min(actualSpacing),'maximum_output_spacing',max(actualSpacing), ...
    'input_range',clean([1,end],1)','output_range',xq([1,end]), ...
    'endpoint_included',xq(end)==clean(end,1),'unfilled_tail',clean(end,1)-xq(end), ...
    'endpoint_policy',p.endpoint_policy,'gui_two_endpoint_fallback',usedFallback, ...
    'extrapolated',false,'gap_policy',p.gap_policy, ...
    'gap_threshold',gapThreshold,'gap_threshold_basis','requested dt times gap_multiplier', ...
    'gap_count',size(gaps,1),'zero_filled_rows',sum(gapMask), ...
    'downsampling',p.dt>inputMedian,'anti_alias_filter','none');
warnings={'Interpolation changes sampling, not information content; no anti-alias filter is applied.', ...
    'Pro GUI gap threshold is requested dt times multiplier, despite its historical median-spacing label.', ...
    'Interpolation Pro uses a source-linked MATLAB GUI extraction, not the separate linear-only interpolation core.'};
if strcmp(p.gap_policy,'zero')
    warnings{end+1}='Gap zero filling is an explicit original GUI option; synthetic zeros can introduce spectral artifacts and are not observed proxy values.';
end
if usedFallback
    warnings{end+1}='The original GUI replaced a one-point colon grid with both record endpoints; actual spacing differs from requested dt.';
end
provenance=sourceProvenance(root,request.input_path,{'code/guicode/interpolationGUI.m'});
if ~provenance.all_used_sources_match_reference
    warnings{end+1}='Installed Acycle source differs from the reference used for the GUI extraction; numerical compatibility requires review.';
end
artifacts=struct('raw_csv',fullfile(out,'raw.csv'),'cleaned_csv',fullfile(out,'cleaned.csv'), ...
    'interpolated_csv',fullfile(out,'interpolated.csv'),'gap_csv',fullfile(out,'gaps.csv'), ...
    'diagnostic_png',fullfile(out,'interpolation.png'),'diagnostic_fig',fullfile(out,'interpolation.fig'), ...
    'diagnostic_pdf',fullfile(out,'interpolation.pdf'),'analysis_mat',fullfile(out,'analysis.mat'), ...
    'provenance_json',fullfile(out,'provenance.json'));
writematrix(raw,artifacts.raw_csv);writematrix(clean,artifacts.cleaned_csv);
writematrix(interpolated,artifacts.interpolated_csv);writematrix(gaps,artifacts.gap_csv);
fig=figure('Visible','off','Color','white','Position',[50 50 1100 650]);
cleanupFigure=onCleanup(@()close(fig)); %#ok<NASGU>
plot(clean(:,1),clean(:,2),'o','Color',[0 .447 .741]);hold on;
plot(xq,vq,':.','Color',[.85 .325 .098]);
if any(gapMask),plot(xq(gapMask),vq(gapMask),'rx','MarkerSize',8);end
xlabel(p.coordinate_unit,'Interpreter','none');ylabel('Proxy value');grid on;
title(sprintf('Acycle Interpolation Pro: %s, requested dt %.6g',p.method,p.dt),'Interpreter','none');
legend('Input observations',p.method,'Location','best');
exportgraphics(fig,artifacts.diagnostic_png,'Resolution',150);
exportgraphics(fig,artifacts.diagnostic_pdf,'ContentType','vector');savefig(fig,artifacts.diagnostic_fig);
parameters=p; %#ok<NASGU>
save(artifacts.analysis_mat,'raw','clean','interpolated','gaps','gapMask','parameters','summary','provenance','-v7');
writeJson(artifacts.provenance_json,provenance);
result=struct('status','success','backend','matlab','operation','interpolate_pro', ...
    'parameters',p,'summary',summary,'artifacts',artifacts,'provenance',provenance,'warnings',{warnings});
end

function value=fieldOr(s,name,fallback)
if isfield(s,name),value=s.(name);else,value=fallback;end
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
    'numerical_backend','MATLAB interp1 via sourced Acycle Interpolation Pro GUI extraction', ...
    'plot_backend','MATLAB','extraction_source','code/guicode/interpolationGUI.m:34,103-108,152-218', ...
    'adapter_extensions','strict input/size validation; optional strict_grid rejects GUI fallback; explicit metadata; no algorithm substitution');
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
