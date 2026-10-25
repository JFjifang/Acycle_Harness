function tests = test_acycle_batch
tests = functiontests(localfunctions);
end

function setupOnce(testCase)
root=getenv('ACYCLE_ROOT');
assert(isfolder(root),'Harness:TestAcycleRoot','ACYCLE_ROOT must name an Acycle checkout.');
testCase.TestData.acycleRoot=root;
testCase.TestData.outputRoot=getenv('ACYCLE_VALIDATION_DIR');
testCase.TestData.oldPath=path;
addpath(fullfile(root,'code','seriesanalysis'));
end

function teardownOnce(testCase)
path(testCase.TestData.oldPath);
end

function testOriginalNumericalParity(testCase)
% Deterministic two-period positive control with a trend and irregular input.
x=(0:0.5:160)';
y=sin(2*pi*x/20)+0.4*sin(2*pi*x/8)+0.003*x;
raw=[x,y];
raw(70,:)=[];
raw=[raw;20,raw(41,2)+0.2;NaN,1;30,Inf];
raw=flipud(raw);
p=struct('detrend','linear','dt',0.5,'evolution',true, ...
    'filter_band',[0.04,0.06],'filter_method','taner_hilbert');
[r,s]=runFixture(testCase,'synthetic-parity',raw,p);
reference=findduplicate(sortrows(raw(all(isfinite(raw),2),:)));
reference=interpolate(reference,0.5);
line=polyfit(reference(:,1),reference(:,2),1);
reference(:,2)=reference(:,2)-(reference(:,1)*line(1)+line(2));
verifyEqual(testCase,s.processed,reference,'AbsTol',1e-13);
[rho,s0,classic,robust]=redconfML(reference(:,2),0.5,2, ...
    5*size(reference,1),2,0.25,1,0,1);
verifyEqual(testCase,s.robust,robust,'RelTol',1e-11,'AbsTol',1e-12);
verifyEqual(testCase,s.classic,classic,'RelTol',1e-11,'AbsTol',1e-12);
verifyEqual(testCase,r.summary.robust_ar1_rho,rho,'AbsTol',1e-11);
verifyEqual(testCase,r.summary.robust_ar1_s0,s0,'AbsTol',1e-11);
[filtered,~]=acycleBandpassFilter(reference,struct('method','taner_hilbert', ...
    'lower_frequency',0.04,'upper_frequency',0.06,'rolloff_exponent',12));
verifyEqual(testCase,s.filtered.filtered,filtered.filtered,'AbsTol',1e-12);
verifyEqual(testCase,s.filtered.envelope,filtered.envelope,'AbsTol',1e-12);
padded=zeropad2(reference,r.parameters.evolution_window);
[a,f,c]=evofft(padded,r.parameters.evolution_window, ...
    r.parameters.evolution_step,0.5,0,1,1);
verifyEqual(testCase,s.evolution.amplitude,a,'AbsTol',1e-12);
verifyEqual(testCase,s.evolution.frequency,f,'AbsTol',1e-12);
verifyEqual(testCase,s.evolution.coordinate,c,'AbsTol',1e-12);
[~,j]=max(robust(:,2));
verifyLessThan(testCase,abs(robust(j,1)-1/20),0.005);
verifyTrue(testCase,r.provenance.all_used_sources_match_reference);
verifyEqual(testCase,r.summary.removed_nonfinite_rows,2);
verifyEqual(testCase,r.summary.merged_duplicate_rows,1);
verifyTrue(testCase,r.summary.interpolated);
assertFigures(testCase,r);
end

function testOriginalLowessAndOfficialExamples(testCase)
% These are official Acycle fixtures, not claims of full paper reproduction.
files={'Example-La2004-1E.5T-1P-0-2000.txt', ...
    'Example-Guandao2AnisianGR.txt','Example-WayaoCarnianGR0.txt', ...
    'Example-SvalbardPETM-logFe.txt'};
for k=1:numel(files)
    input=fullfile(testCase.TestData.acycleRoot,'data','Examples',files{k});
    [~,name]=fileparts(input);
    [r,s]=runFixture(testCase,name,input,struct('evolution',true));
    trend=smooth(s.prepared(:,1),s.prepared(:,2),0.35,'lowess');
    verifyEqual(testCase,s.trend,trend,'AbsTol',1e-12);
    verifyEqual(testCase,s.processed(:,2),s.prepared(:,2)-trend,'AbsTol',1e-12);
    verifyEqual(testCase,r.status,'success');
    verifyTrue(testCase,all(isfinite(s.robust),'all'));
    verifyGreaterThan(testCase,r.summary.processed_rows,100);
    assertFigures(testCase,r);
end
end

function testAgeModelAndGaussianFilter(testCase)
x=(0:0.1:30)';
y=sin(2*pi*x/3)+0.3*sin(2*pi*x/0.8);
p=struct('detrend','mean','evolution',false,'sedimentation_rate',10, ...
    'depth_unit','m','first_age_kyr',100,'dt',1,'filter_band',[0.025,0.045]);
[r,s]=runFixture(testCase,'rate-age-conversion',[x,y],p);
[model,meta]=acycleSedimentationRateAgeModel([x,repmat(10,size(x))],'m',100);
verifyEqual(testCase,s.ageModel,model,'AbsTol',1e-12);
verifyEqual(testCase,s.ageMeta,meta);
[time,~]=depthtotime(x,model);
verifyEqual(testCase,s.clean(:,1),time,'AbsTol',1e-12);
verifyEqual(testCase,r.summary.coordinate_unit,'kyr');
verifyEqual(testCase,r.summary.sample_interval,1,'AbsTol',1e-12);
[g,~]=acycleBandpassFilter(s.processed,struct('method','gaussian', ...
    'lower_frequency',0.025,'upper_frequency',0.045));
verifyEqual(testCase,s.filtered.filtered,g.filtered,'AbsTol',1e-12);
assertFigures(testCase,r);
end

function testTiePointAgeModel(testCase)
x=(0:0.5:100)'; y=sin(2*pi*x/10);
p=struct('detrend','mean','evolution',false, ...
    'age_model',[0,100;50,300;100,500]);
[r,s]=runFixture(testCase,'tiepoint-age-conversion',[x,y],p);
[time,~]=depthtotime(x,p.age_model);
verifyEqual(testCase,s.clean(:,1),time,'AbsTol',1e-12);
verifyEqual(testCase,r.summary.coordinate_unit,'kyr');
end

function testNegativeControlUsesPointwiseLanguage(testCase)
input=fullfile(testCase.TestData.acycleRoot,'data','Examples','Example-Rednoise0.7-2000.txt');
[r,s]=runFixture(testCase,'rednoise-negative-control',input,struct('detrend','mean','evolution',false));
verifyTrue(testCase,all(isfinite(s.robust),'all'));
verifyTrue(testCase,any(contains(string(r.warnings),'not proof of orbital forcing')));
verifyFalse(testCase,isfield(r.summary,'orbital_detection'));
end

function testRejectsNonScientificParameters(testCase)
x=(0:30)'; y=sin(x);
[requestPath,responsePath]=prepareFixture(testCase,'invalid-parameter',[x,y],struct('unknown_setting',1));
verifyError(testCase,@()acycle_batch(requestPath,responsePath),'Harness:UnknownParameter');
response=jsondecode(fileread(responsePath));
verifyEqual(testCase,response.status,'error');
end

function testPreventsOutputOverwrite(testCase)
x=(0:0.5:40)'; y=sin(x);
[requestPath,responsePath]=prepareFixture(testCase,'immutable-result',[x,y],struct('detrend','mean','evolution',false));
r=acycle_batch(requestPath,responsePath);
info=dir(r.artifacts.analysis_mat);
originalResponse=fileread(responsePath);
verifyError(testCase,@()acycle_batch(requestPath,responsePath),'Harness:OutputExists');
after=dir(r.artifacts.analysis_mat);
verifyEqual(testCase,after.bytes,info.bytes);
verifyEqual(testCase,fileread(responsePath),originalResponse);
end

function [result,saved] = runFixture(testCase,name,input,parameters)
[requestPath,responsePath]=prepareFixture(testCase,name,input,parameters);
result=acycle_batch(requestPath,responsePath);
saved=load(result.artifacts.analysis_mat);
end

function [requestPath,responsePath]=prepareFixture(testCase,name,input,parameters)
out=fullfile(testCase.TestData.outputRoot,name);
if ~isfolder(out),mkdir(out);end
if isnumeric(input)
    inputPath=fullfile(out,'input.csv'); writematrix(input,inputPath);
else
    inputPath=input;
end
request=struct('operation','analyze','input_path',inputPath, ...
    'output_dir',out,'acycle_root',testCase.TestData.acycleRoot,'parameters',parameters);
requestPath=fullfile(out,'request.json'); responsePath=fullfile(out,'response.json');
fid=fopen(requestPath,'w'); cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s',jsonencode(request));
end

function assertFigures(testCase,result)
fields=fieldnames(result.artifacts);
for k=1:numel(fields)
    path=result.artifacts.(fields{k});
    verifyTrue(testCase,isfile(path),sprintf('Missing artifact %s',path));
    if endsWith(path,'.png')
        info=imfinfo(path);
        verifyGreaterThan(testCase,info.Width,400);
        verifyGreaterThan(testCase,info.Height,200);
        pixels=imread(path);
        verifyGreaterThan(testCase,numel(unique(pixels(:))),20,'Figure appears blank.');
        verifyTrue(testCase,isfile(strrep(path,'.png','.fig')));
    end
end
end
