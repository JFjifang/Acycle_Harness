function tests=test_acycle_swa
tests=functiontests(localfunctions);
end

function setupOnce(testCase)
root=getenv('ACYCLE_ROOT');assert(isfolder(root),'Set ACYCLE_ROOT.');
testCase.TestData.root=root;
testCase.TestData.output=getenv('ACYCLE_VALIDATION_DIR');
testCase.TestData.oldPath=path;
testCase.TestData.oldVisible=get(groot,'defaultFigureVisible');
addpath(fullfile(root,'code','seriesanalysis'));
addpath(fullfile(root,'code','package','swa'));
set(groot,'defaultFigureVisible','off');
end

function teardownOnce(testCase)
path(testCase.TestData.oldPath);set(groot,'defaultFigureVisible',testCase.TestData.oldVisible);
end

function testPublishedLavernockLombParityAndPeak(testCase)
repo=fileparts(fileparts(fileparts(mfilename('fullpath'))));
input=fullfile(repo,'benchmarks','data','weedon_2020_lavernock_0_13_17m.csv');
p=struct('method','lomb','coordinate_unit','m');
request=requestFor(testCase,'swa-lavernock-publication',input,p);
% The original SWA routine writes into base workspace. The bridge restores it.
oldPwd=pwd;oldPath=path;existed=evalin('base','exist(''freq'',''var'')')~=0;
if existed,previous=evalin('base','freq');else,previous=[];end
cleanup=onCleanup(@()restoreSentinel(existed,previous)); %#ok<NASGU>
assignin('base','freq','swa-test-sentinel');
r=acycle_swa(request);s=load(r.artifacts.analysis_mat);
verifyEqual(testCase,pwd,oldPwd);verifyEqual(testCase,path,oldPath);
verifyEqual(testCase,evalin('base','freq'),'swa-test-sentinel');
referenceDir=fullfile(request.output_dir,'direct-original');mkdir(referenceDir);
cd(referenceDir);restore=onCleanup(@()cd(oldPwd)); %#ok<NASGU>
[f,power,bg,~,~,fdr,chi]=specswafdr(s.clean,0);
reference=[f(:),power(:),bg(:),bg(:)*chi(:)',fdr];
verifyEqual(testCase,s.spectrum,reference,'AbsTol',1e-11,'RelTol',1e-12);
verifyEqual(testCase,r.summary.input_rows,439);
verifyFalse(testCase,r.summary.interpolated);
verifyTrue(testCase,r.provenance.all_used_sources_match_reference);
% Weedon (2020) reports an approximately 0.81 m wavelength above 5% FDR.
% At this 13.14 m span, the native Fourier grid is ~0.076 cycles/m; 0.07 m
% tolerance admits the neighboring representable wavelength without tuning.
power=s.power;f=s.frequency;
peak=find(power(2:end-1)>power(1:end-2)&power(2:end-1)>=power(3:end))+1;
selected=peak(abs(1./f(peak)-0.81)<=0.07);
verifyNotEmpty(testCase,selected,'Published ~0.81 m peak is missing.');
verifyTrue(testCase,any(isfinite(s.fdr(selected,2)) & power(selected)>s.fdr(selected,2)), ...
    'Published ~0.81 m peak does not exceed the original 5% FDR threshold.');
assertFigure(testCase,r);
end

function testNewarkMtmOriginalParity(testCase)
input=fullfile(testCase.TestData.root,'data','Examples','Example-LateTriassicNewarkDepthRank.txt');
p=struct('method','mtm','coordinate_unit','m','detrend','mean','mtm_nw',2,'pad_factor',1);
request=requestFor(testCase,'swa-newark-mtm',input,p);
r=acycle_swa(request);s=load(r.artifacts.analysis_mat);
oldPwd=pwd;referenceDir=fullfile(request.output_dir,'direct-original');mkdir(referenceDir);
cd(referenceDir);restore=onCleanup(@()cd(oldPwd)); %#ok<NASGU>
reference=spectralswafdr(s.prepared,'mtm',2,1,0);
verifyEqual(testCase,s.spectrum,reference,'AbsTol',1e-12,'RelTol',1e-12);
verifyEqual(testCase,s.prepared(:,2),s.clean(:,2)-mean(s.clean(:,2)),'AbsTol',1e-12);
verifyFalse(testCase,r.summary.interpolated);
verifyTrue(testCase,r.provenance.all_used_sources_match_reference);
verifyEqual(testCase,r.summary.method,'mtm');
assertFigure(testCase,r);
end

function testRejectsAmbiguousPreprocessing(testCase)
input=fullfile(testCase.TestData.root,'data','Examples','Example-LateTriassicNewarkDepthRank.txt');
request=requestFor(testCase,'swa-invalid-lomb',input,struct('method','lomb','detrend','mean'));
verifyError(testCase,@()acycle_swa(request),'Harness:SwaLombParameters');
request=requestFor(testCase,'swa-invalid-dt',input,struct('method','lomb','dt',1));
verifyError(testCase,@()acycle_swa(request),'Harness:SwaParameter');
end

function testRejectsDuplicateCoordinates(testCase)
out=fullfile(testCase.TestData.output,'swa-duplicates');if ~isfolder(out),mkdir(out);end
input=fullfile(out,'input.csv');x=(0:99)';data=[x,sin(x/10)];data(50,1)=data(49,1);
writematrix(data,input);
request=requestFor(testCase,'swa-duplicates',input,struct('method','mtm'));
verifyError(testCase,@()acycle_swa(request),'Harness:SwaDuplicates');
end

function request=requestFor(testCase,name,input,p)
out=fullfile(testCase.TestData.output,name);if ~isfolder(out),mkdir(out);end
request=struct('operation','swa','input_path',input,'output_dir',out, ...
    'acycle_root',testCase.TestData.root,'parameters',p);
end

function assertFigure(testCase,r)
for name=fieldnames(r.artifacts)'
    verifyTrue(testCase,isfile(r.artifacts.(name{1})));
end
info=imfinfo(r.artifacts.spectrum_png);verifyGreaterThan(testCase,info.Width,500);
pixels=imread(r.artifacts.spectrum_png);verifyGreaterThan(testCase,numel(unique(pixels(:))),20);
fig=openfig(r.artifacts.spectrum_fig,'invisible');clean=onCleanup(@()close(fig)); %#ok<NASGU>
lines=findall(fig,'Type','line');verifyGreaterThanOrEqual(testCase,numel(lines),3);
end

function restoreSentinel(existed,value)
if existed,assignin('base','freq',value);else,evalin('base','clear freq');end
end
