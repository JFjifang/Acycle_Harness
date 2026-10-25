function tests=test_acycle_tune
% The original peak and time-conversion routines are independent references.
% No astronomical detection is inferred from an assumed periodic age model.
tests=functiontests(localfunctions);
end

function setupOnce(testCase)
root=getenv('ACYCLE_ROOT');assert(isfolder(root),'ACYCLE_ROOT is required.');
testCase.TestData.root=root;
testCase.TestData.output=getenv('ACYCLE_VALIDATION_DIR');
testCase.TestData.oldPath=path;
addpath(fullfile(root,'code','seriesanalysis'));
end

function teardownOnce(testCase)
path(testCase.TestData.oldPath);
end

function testSingleExtremaUseOriginalPeakAndTimeFunctions(testCase)
[data,p]=fixture();
% Exercise original cleaning without changing any peak location.
data=[flipud(data);data(11,:);NaN,1;5,Inf];
for mode={'peaks','troughs'}
    p.extrema=mode{1};
    if strcmp(p.extrema,'peaks'),p.anchor_phase='peak';signum=1;
    else,p.anchor_phase='trough';signum=-1;end
    % This anchor reproduces the GUI's historical (1:n)*period age column.
    p.anchor_age_kyr=p.period_kyr;
    [r,s]=runFixture(testCase,['tune-original-' p.extrema],data,p);
    finite=s.raw(all(isfinite(s.raw(:,1:2)),2),1:2);
    reference=findduplicate(sortrows(finite));
    [selected,~]=getpks([reference(:,1),signum*reference(:,2)]);
    expectedAge=(1:size(selected,1))'*p.period_kyr;
    model=[selected(:,1),expectedAge];
    keep=reference(:,1)>=model(1,1)&reference(:,1)<=model(end,1);
    [expectedTime,expectedRate]=depthtotime(reference(keep,1),model);
    verifyEqual(testCase,s.clean,reference,'AbsTol',1e-13);
    verifyEqual(testCase,s.controlPoints(:,1),selected(:,1));
    verifyEqual(testCase,s.controlPoints(:,2),signum*selected(:,2));
    verifyEqual(testCase,s.controlPoints(:,3),repmat(signum,size(selected,1),1));
    verifyEqual(testCase,s.controlPoints(:,4),(0:size(selected,1)-1)');
    verifyEqual(testCase,s.controlPoints(:,5),expectedAge,'AbsTol',1e-12);
    verifyEqual(testCase,s.ageModel,model,'AbsTol',1e-12);
    verifyEqual(testCase,s.depthAge,[reference(keep,1),expectedTime],'AbsTol',1e-12);
    verifyEqual(testCase,s.tuned,[expectedTime,reference(keep,2)],'AbsTol',1e-12);
    verifyEqual(testCase,s.sedimentationRates, ...
        [model(1:end-1,1),model(2:end,1),100*expectedRate(:)],'AbsTol',1e-12);
    verifyEqual(testCase,r.parameters.endpoint_policy,'trim');
    verifyEqual(testCase,r.summary.age_model,s.ageModel,'AbsTol',1e-12);
    verifyEqual(testCase,r.summary.valid_depth_range,model([1,end],1)');
    verifyEqual(testCase,r.summary.input_curve,'bandpassed');
    verifyTrue(testCase,all(diff(s.tuned(:,1))>0));
    verifyTrue(testCase,any(contains(lower(string(r.warnings)),'assum')));
    verifyTrue(testCase,any(contains(lower(string(r.warnings)),'independent')));
    assertArtifacts(testCase,r,s);
end
end

function testBothExtremaUseHalfCyclesAndFirstMatchingAnchor(testCase)
[data,p]=fixture();data(:,2)=-data(:,2);
p.extrema='both';p.anchor_phase='peak';p.anchor_age_kyr=100;
[r,s]=runFixture(testCase,'tune-both-half-period',data,p);
[peaks,~]=getpks(s.clean);
[troughs,~]=getpks([s.clean(:,1),-s.clean(:,2)]);
expected=sortrows([peaks,ones(size(peaks,1),1); ...
    troughs(:,1),-troughs(:,2),-ones(size(troughs,1),1)],1);
anchor=find(expected(:,3)==1,1);
cycles=((1:size(expected,1))'-anchor)/2;
ages=p.anchor_age_kyr+p.period_kyr*cycles;
verifyEqual(testCase,s.controlPoints(:,1:3),expected,'AbsTol',1e-12);
verifyEqual(testCase,s.controlPoints(:,4),cycles,'AbsTol',1e-12);
verifyEqual(testCase,s.controlPoints(:,5),ages,'AbsTol',1e-12);
verifyEqual(testCase,anchor,2);
verifyEqual(testCase,r.summary.anchor_control_index,anchor);
verifyEqual(testCase,r.summary.anchor_depth,expected(anchor,1));
verifyEqual(testCase,s.controlPoints(1,5),p.anchor_age_kyr-p.period_kyr/2);
verifyEqual(testCase,diff(s.controlPoints(:,5)), ...
    repmat(p.period_kyr/2,size(expected,1)-1,1),'AbsTol',1e-12);
verifyEqual(testCase,s.controlPoints(1:end-1,3).*s.controlPoints(2:end,3), ...
    -ones(size(expected,1)-1,1));
[time,~]=depthtotime(s.depthAge(:,1),s.ageModel);
verifyEqual(testCase,s.depthAge(:,2),time,'AbsTol',1e-12);
verifyEqual(testCase,r.summary.age_model,s.ageModel,'AbsTol',1e-12);
end

function testExplicitExtrapolationUsesOriginalRatesAndUnits(testCase)
[data,p]=fixture();p.endpoint_policy='linear_extrapolate';p.depth_unit='ft';
[r,s]=runFixture(testCase,'tune-explicit-extrapolation',data,p);
controls=s.controlPoints(:,[1,5]);
[time,~]=depthtotime(s.clean(:,1),controls);
verifyEqual(testCase,s.depthAge,[s.clean(:,1),time],'AbsTol',1e-12);
verifyEqual(testCase,s.tuned,[time,s.clean(:,2)],'AbsTol',1e-12);
% Exported model covers the record for the existing no-extrapolation analyze
% interface. These added endpoints are not additional observed extrema.
verifyEqual(testCase,s.ageModel([1,end],1),s.clean([1,end],1));
verifyEqual(testCase,s.ageModel([1,end],2),time([1,end]),'AbsTol',1e-12);
[~,rate]=depthtotime(s.clean(:,1),s.ageModel);
verifyEqual(testCase,s.sedimentationRates, ...
    [s.ageModel(1:end-1,1),s.ageModel(2:end,1),30.48*rate(:)],'AbsTol',1e-12);
verifyEqual(testCase,r.summary.valid_depth_range,s.clean([1,end],1)');
verifyEqual(testCase,r.summary.depth_unit,'ft');
verifyLessThan(testCase,s.depthAge(1,2),controls(1,2));
verifyGreaterThan(testCase,s.depthAge(end,2),controls(end,2));
verifyTrue(testCase,any(contains(lower(string(r.warnings)),'extrapolat')));
end

function testFilterCsvEnvelopeDoesNotChangeTuning(testCase)
[data,p]=fixture();
[~,two]=runFixture(testCase,'tune-filter-two-columns',data,p);
% The genuine filter CSV has a third envelope column. Its NaNs are irrelevant
% to peak selection from the first two columns and must not remove rows.
withEnvelope=[data,NaN(size(data,1),1)];
[r,three]=runFixture(testCase,'tune-filter-three-columns',withEnvelope,p);
verifyEqual(testCase,size(three.raw,2),3);
verifyEqual(testCase,three.clean,two.clean);
verifyEqual(testCase,three.controlPoints,two.controlPoints,'AbsTol',1e-12);
verifyEqual(testCase,three.ageModel,two.ageModel,'AbsTol',1e-12);
verifyEqual(testCase,three.tuned,two.tuned,'AbsTol',1e-12);
verifyEqual(testCase,r.summary.ignored_input_columns,3);
end

function testRejectsSelectedPlateausWithoutChangingDetector(testCase)
[data,p]=fixture();data(4,2)=data(3,2);
request=prepareFixture(testCase,'tune-selected-peak-plateau',data,p);
verifyError(testCase,@()acycle_tune(request),'Harness:TunePlateau');
% A plateau of the unselected phase does not alter peak-only control points.
[data,p]=fixture();data(8,2)=data(7,2);
[~,s]=runFixture(testCase,'tune-unselected-trough-plateau',data,p);
[expected,~]=getpks(s.clean);
verifyEqual(testCase,s.controlPoints(:,1:2),expected);
p.extrema='both';
request=prepareFixture(testCase,'tune-both-plateau',data,p);
verifyError(testCase,@()acycle_tune(request),'Harness:TunePlateau');
end

function testRejectsIncompatibleAnchorAndImplicitExtrapolation(testCase)
[data,p]=fixture();p.anchor_phase='trough';
request=prepareFixture(testCase,'tune-incompatible-phase',data,p);
verifyError(testCase,@()acycle_tune(request),'Harness:TunePhase');
[data,p]=fixture();p.endpoint_policy='error';
request=prepareFixture(testCase,'tune-uncovered-endpoints',data,p);
verifyError(testCase,@()acycle_tune(request),'Harness:TuneCoverage');
end

function testRejectsInsufficientControlPoints(testCase)
[data,p]=fixture();data(:,2)=data(:,1);
request=prepareFixture(testCase,'tune-no-extrema',data,p);
verifyError(testCase,@()acycle_tune(request),'Harness:TuneControlPoints');
end

function testPreventsCompletedOutputOverwrite(testCase)
[data,p]=fixture();
request=prepareFixture(testCase,'tune-immutable-result',data,p);
r=acycle_tune(request);
original=readBytes(r.artifacts.analysis_mat);
verifyError(testCase,@()acycle_tune(request),'Harness:OutputExists');
verifyEqual(testCase,readBytes(r.artifacts.analysis_mat),original);
end

function [data,p]=fixture()
% Deliberately discrete/asymmetric extrema avoid floating-point sine plateaus.
x=(0:40)';pattern=[0;1;3;2;0;-2;-3;-1];
y=pattern(mod((0:numel(x)-1)',numel(pattern))+1);
data=[x,y];
p=struct('period_kyr',20,'anchor_age_kyr',100,'anchor_phase','peak', ...
    'extrema','peaks','depth_unit','m');
end

function [result,saved]=runFixture(testCase,name,data,p)
request=prepareFixture(testCase,name,data,p);
result=acycle_tune(request);
fid=fopen(fullfile(request.output_dir,'response.json'),'w');
cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s\n',jsonencode(result,'PrettyPrint',true));
saved=load(result.artifacts.analysis_mat);
end

function request=prepareFixture(testCase,name,data,p)
out=fullfile(testCase.TestData.output,name);if ~isfolder(out),mkdir(out);end
input=fullfile(out,'input.csv');writematrix(data,input);
request=struct('input_path',input,'output_dir',out, ...
    'acycle_root',testCase.TestData.root,'operation','tune','parameters',p);
fid=fopen(fullfile(out,'request.json'),'w');cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s',jsonencode(request));
end

function assertArtifacts(testCase,r,s)
required={'control_points_csv','age_model_csv','tuned_csv','depth_age_csv', ...
    'sedimentation_rate_csv','diagnostic_png','diagnostic_fig','diagnostic_pdf', ...
    'analysis_mat','provenance_json'};
for k=1:numel(required)
    verifyTrue(testCase,isfield(r.artifacts,required{k}));
    verifyTrue(testCase,isfile(r.artifacts.(required{k})));
end
verifyEqual(testCase,readmatrix(r.artifacts.age_model_csv),s.ageModel,'AbsTol',1e-12);
verifyEqual(testCase,readmatrix(r.artifacts.tuned_csv),s.tuned,'AbsTol',1e-12);
verifyEqual(testCase,readmatrix(r.artifacts.depth_age_csv),s.depthAge,'AbsTol',1e-12);
info=imfinfo(r.artifacts.diagnostic_png);verifyGreaterThan(testCase,info.Width,400);
pixels=imread(r.artifacts.diagnostic_png);
verifyGreaterThan(testCase,numel(unique(pixels)),20);
figureHandle=openfig(r.artifacts.diagnostic_fig,'invisible');
cleanup=onCleanup(@()close(figureHandle)); %#ok<NASGU>
verifyGreaterThanOrEqual(testCase,numel(findall(figureHandle,'Type','axes')),3);
end

function bytes=readBytes(file)
fid=fopen(file,'rb');assert(fid>=0);
cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
bytes=fread(fid,Inf,'*uint8');
end
