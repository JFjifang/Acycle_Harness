function tests=test_acycle_coco
tests=functiontests(localfunctions);
end

function setupOnce(testCase)
root=getenv('ACYCLE_ROOT'); assert(isfolder(root),'ACYCLE_ROOT is required.');
testCase.TestData.root=root;
testCase.TestData.output=getenv('ACYCLE_VALIDATION_DIR');
testCase.TestData.oldPath=path;
addpath(fullfile(root,'code','corrcoef'),fullfile(root,'code','seriesanalysis'), ...
    fullfile(root,'code','package','swa'),fullfile(root,'code','package','secular_periods'));
end

function teardownOnce(testCase)
path(testCase.TestData.oldPath);
end

function testCocoOriginalParityAndKnownRate(testCase)
[data,p]=synthetic();
[r,s]=runFixture(testCase,'coco-original-parity',data,p,'coco');
[curve,pvalues,null,details]=corrcoefslices_rankNew(s.inputData,s.periods, ...
    r.summary.sampling_interval_m,r.parameters.nfft,8,12,1,0,0,19,0,1, ...
    'Spearman',1/(2*r.summary.sampling_interval_m),0,false,'adaptive9b', ...
    'MaxFrequency',r.parameters.max_frequency,'Seed',17,'ShowPeriodograms',false);
verifyEqual(testCase,s.numerical.corrCI,curve,'AbsTol',1e-12);
verifyEqual(testCase,s.numerical.corrH0,pvalues,'AbsTol',1e-12);
verifyEqual(testCase,s.numerical.nullCorrelation,null,'AbsTol',1e-12);
verifyEqual(testCase,s.numerical.details.nullMax,details.nullMax,'AbsTol',1e-12);
verifyEqual(testCase,r.summary.minimum_resolvable_p,1/20,'AbsTol',1e-15);
verifyLessThanOrEqual(testCase,abs(r.summary.best_rate_cm_kyr-10),1);
verifyTrue(testCase,r.provenance.all_sources_match_reference);
verifyTrue(testCase,all(pvalues(:,1)>=pvalues(:,3)|isnan(pvalues(:,1))));
assertFigures(testCase,r);
curveFigure=imfinfo(r.artifacts.coco_figure_1_png);
verifyGreaterThan(testCase,curveFigure.Height,1000);
end

function testEcocoOriginalParityAndPhysicalWindows(testCase)
[data,p]=synthetic(); p.window=120; p.step=60;
[r,s]=runFixture(testCase,'ecoco-original-parity',data,p,'ecoco');
[rates,depth,rho,pl,pg,pc,score,no,track,details]=ecoco(s.inputData,[],s.periods, ...
    120,r.summary.sampling_interval_m,1,0,0,r.parameters.nfft,8,12,1,19,0,1,0, ...
    'Spearman',1/(2*r.summary.sampling_interval_m),0,'adaptive',r.parameters.max_frequency,17,0.5, ...
    'ECOCOWindowMode','physical-depth','ECOCOStepDepth',60,'Verbose',false);
verifyEqual(testCase,s.numerical.rates,rates,'AbsTol',1e-12);
verifyEqual(testCase,s.numerical.depth,depth,'AbsTol',1e-12);
verifyEqual(testCase,s.numerical.rho,rho,'AbsTol',1e-12);
verifyEqual(testCase,s.numerical.pLocal,pl,'AbsTol',1e-12);
verifyEqual(testCase,s.numerical.pGlobal,pg,'AbsTol',1e-12);
verifyEqual(testCase,s.numerical.pCOCO,pc,'AbsTol',1e-12);
verifyEqual(testCase,s.numerical.score,score,'AbsTol',1e-12);
verifyEqual(testCase,s.numerical.nOrbit,no,'AbsTol',1e-12);
verifyEqual(testCase,s.numerical.tracked,track,'AbsTol',1e-12);
verifyEqual(testCase,r.summary.window_count,3);
verifyEqual(testCase,r.summary.depth_centres_m,[60,120,180],'AbsTol',1e-12);
verifyFalse(testCase,r.summary.map_global_applied);
verifyFalse(testCase,r.summary.edge_padding);
verifyEqual(testCase,s.numerical.details.windows.requestedBounds,details.windows.requestedBounds);
assertFigures(testCase,r);
end

function testExplicitUnitsAndSixPeriodMode(testCase)
[data,p]=synthetic(); data(:,1)=data(:,1)/.3048; p.depth_unit='ft';
p=rmfield(p,'middle_age_ma'); p.orbital_periods_kyr=[125,95,39.8,23.3,22,18.7];
p.method='phase_averaged';p.nsim=9;p.dt=.25/.3048;
[r,s]=runFixture(testCase,'coco-feet-six-periods',data,p,'coco');
[curve,pvalues,null,details]=corrcoefslices_rankNew(s.inputData,s.periods, ...
    r.summary.sampling_interval_m,r.parameters.nfft,8,12,1,0,0,9,0,1, ...
    'Spearman',1/(2*r.summary.sampling_interval_m),0,false,'adaptive', ...
    'MaxFrequency',r.parameters.max_frequency,'Seed',17,'ShowPeriodograms',false);
verifyEqual(testCase,s.numerical.corrCI,curve,'AbsTol',1e-12);
verifyEqual(testCase,s.numerical.corrH0,pvalues,'AbsTol',1e-12);
verifyEqual(testCase,s.numerical.nullCorrelation,null,'AbsTol',1e-12);
verifyEqual(testCase,s.numerical.details.nullMax,details.nullMax,'AbsTol',1e-12);
verifyEqual(testCase,s.rawMetres(:,1),s.raw(:,1)*.3048,'AbsTol',1e-12);
verifyEqual(testCase,s.inputData,interpolate(s.clean,.25),'AbsTol',1e-12);
verifyEqual(testCase,r.summary.sampling_interval_m,.25,'AbsTol',1e-12);
verifyEqual(testCase,size(s.prepared,1),961);
verifyEqual(testCase,r.summary.orbital_periods_kyr,p.orbital_periods_kyr,'AbsTol',1e-12);
verifyEqual(testCase,r.summary.target_mode,'adaptive');
verifyEqual(testCase,r.summary.depth_to_metres_factor,.3048);
verifyEqual(testCase,r.summary.requested_period_count,6);
verifyEqual(testCase,r.summary.resolved_period_count_at_best,s.numerical.report.periodCountAtBest);
verifyEqual(testCase,r.summary.target_model,'phase-averaged');
verifyTrue(testCase,contains(r.summary.interpretation,'of 6 requested'));
verifyFalse(testCase,contains(r.summary.interpretation,'/9'));
verifyEqual(testCase,r.status,'success');
end

function testEcocoBlockedStrictConsensusExecutes(testCase)
[data,p]=synthetic(600,.25);p.method='blocked';p.nsim=9;p.window=120;p.step=120;
[r,s]=runFixture(testCase,'ecoco-blocked-strict',data,p,'ecoco');
verifyEqual(testCase,r.summary.blocked_consensus_policy,'strict');
verifyEqual(testCase,s.numerical.rho,s.numerical.details.strictConsensus.rho);
verifyEqual(testCase,s.numerical.pGlobal,s.numerical.details.strictConsensus.pGlobal);
verifyTrue(testCase,any(isfinite(s.numerical.rho),'all'));
verifyTrue(testCase,all(isnan(s.numerical.rho(:,[1,end])),'all'));
verifyEqual(testCase,s.numerical.details.nsimCompleted,9);
verifyFalse(testCase,r.summary.map_global_applied);
assertFigures(testCase,r);
end

function testEcocoInterleavedSplitBeforeInterpolationExecutes(testCase)
[data,p]=synthetic(240,.25);p.method='interleaved';p.nsim=9;p.window=120;p.step=60;
[r,s]=runFixture(testCase,'ecoco-interleaved',data,p,'ecoco');
verifyFalse(testCase,r.summary.preparation.fullRecordInterpolation);
verifyTrue(testCase,s.numerical.details.inputPreprocessing.splitBeforeInterpolation);
verifyEmpty(testCase,s.prepared);
verifyTrue(testCase,any(isfinite(s.numerical.rho),'all'));
verifyEqual(testCase,s.numerical.details.nsimCompleted,9);
verifyEqual(testCase,r.summary.depth_centres_m,[60,120,180],'AbsTol',1e-12);
assertFigures(testCase,r);
end

function testCocoLoessUsesOriginalCallback(testCase)
[data,p]=synthetic(); p.detrend='loess'; p.detrend_window=120;p.nsim=9;
[r,s]=runFixture(testCase,'coco-loess-callback',data,p,'coco');
trend=smooth(s.clean(:,1),s.clean(:,2),.5,'loess');
verifyEqual(testCase,s.preprocessTrend,trend,'AbsTol',1e-12);
verifyEqual(testCase,s.inputData(:,2),s.clean(:,2)-trend,'AbsTol',1e-12);
verifyEqual(testCase,r.summary.preparation.nonlinearDetrend.spanFraction,.5);
end

function testRejectsUnknownTargetAndHeldoutLeakage(testCase)
[data,p]=synthetic(); p=rmfield(p,'middle_age_ma');
request=prepareFixture(testCase,'coco-missing-target',data,p,'coco');
verifyError(testCase,@()acycle_coco(request),'Harness:COCOTarget');
[data,p]=synthetic();p=rmfield(p,'middle_age_ma');p.method='phase_averaged';
p.orbital_periods_kyr=10:10:100;
request=prepareFixture(testCase,'coco-too-many-periods',data,p,'coco');
verifyError(testCase,@()acycle_coco(request),'Harness:COCOPeriodCount');
[data,p]=synthetic();p.method='interleaved';p.detrend='loess';p.span=.5;p.window=120;p.step=60;
request=prepareFixture(testCase,'ecoco-disallow-leakage',data,p,'ecoco');
verifyError(testCase,@()acycle_coco(request),'Harness:COCOPreprocessLeakage');
end

function [data,p]=synthetic(lastDepth,samplingInterval)
if nargin<1,lastDepth=240;end
if nargin<2,samplingInterval=.5;end
periods=calculate_orbit9(0);periods=periods(:,2)/1000;
x=(0:samplingInterval:lastDepth)';time=x/.1;
weights=[1,.8,.8,.8,.8,.6,.4,.4,.4];
y=sum(sin(2*pi*time./periods(:)').*weights,2)+.04*cos(2*pi*x/13.7)+.001*x;
data=[x,y];
p=struct('depth_unit','m','middle_age_ma',0,'sedimentation_rate_min',8, ...
    'sedimentation_rate_max',12,'sedimentation_rate_step',1,'nsim',19, ...
    'seed',17,'correlation','Spearman','red_noise',0,'method','adaptive');
end

function [result,saved]=runFixture(testCase,name,data,p,operation)
request=prepareFixture(testCase,name,data,p,operation);
result=acycle_coco(request);
fid=fopen(fullfile(request.output_dir,'response.json'),'w');
cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s\n',jsonencode(result,'PrettyPrint',true));
saved=load(result.artifacts.analysis_mat);
end

function request=prepareFixture(testCase,name,data,p,operation)
out=fullfile(testCase.TestData.output,name);if ~isfolder(out),mkdir(out);end
if isnumeric(data)
    input=fullfile(out,'input.csv');writematrix(data,input);
else,input=char(data);end
request=struct('input_path',input,'output_dir',out,'acycle_root',testCase.TestData.root, ...
    'operation',operation,'parameters',p);
fid=fopen(fullfile(out,'request.json'),'w');cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s',jsonencode(request));
end

function assertFigures(testCase,result)
fields=fieldnames(result.artifacts);
for k=1:numel(fields)
    file=result.artifacts.(fields{k});verifyTrue(testCase,isfile(file));
    if endsWith(file,'.png')
        info=imfinfo(file);verifyGreaterThan(testCase,info.Width,400);
        verifyGreaterThan(testCase,numel(unique(imread(file))),20);
    end
end
end
