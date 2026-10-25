function tests=test_acycle_interpolate_pro
tests=functiontests(localfunctions);
end

function setupOnce(testCase)
testCase.TestData.root=getenv('ACYCLE_ROOT');
assert(isfolder(testCase.TestData.root),'ACYCLE_ROOT is required.');
testCase.TestData.output=getenv('ACYCLE_VALIDATION_DIR');
end

function testAllNineOriginalGuiMethods(testCase)
% A nonuniform series distinguishes shape-preserving, nearest and cubic
% methods; compare each exported result with the actual GUI's interp1 call.
x=[0;.3;.9;1.2;2;2.6;3.4;4.1;5];
y=[0;2;1;-1;.5;3;1;-2;0];
data=flipud([x,y]);
methods={'linear','nearest','next','previous','pchip','cubic','v5cubic','makima','spline'};
for k=1:numel(methods)
    p=struct('method',methods{k},'dt',.2,'coordinate_unit','m');
    [r,s]=runFixture(testCase,['interpolation-pro-method-' methods{k}],data,p);
    clean=sortrows(s.raw,1);
    grid=clean(1,1):p.dt:clean(end,1);
    expected=interp1(clean(:,1),clean(:,2),grid,methods{k});
    verifyEqual(testCase,s.clean,clean);
    verifyEqual(testCase,s.interpolated,[grid(:),expected(:)],'AbsTol',1e-12);
    verifyEqual(testCase,r.summary.method,methods{k});
    verifyTrue(testCase,r.summary.sorted);
    verifyFalse(testCase,r.summary.extrapolated);
    verifyEqual(testCase,r.summary.removed_nonfinite_rows,0);
    verifyTrue(testCase,r.provenance.all_used_sources_match_reference);
    verifyEqual(testCase,readmatrix(r.artifacts.interpolated_csv),s.interpolated,'AbsTol',1e-12);
    verifyTrue(testCase,isfile(r.artifacts.diagnostic_fig));
    verifyTrue(testCase,isfile(r.artifacts.diagnostic_pdf));
    info=imfinfo(r.artifacts.diagnostic_png);verifyGreaterThan(testCase,info.Width,400);
end
end

function testOriginalGapThresholdAndStrictInteriorZeroing(testCase)
data=[0,1;1,2;2,3;10,4;11,5;12,6];
% Requested dt is .5 while median input spacing is 1. The original GUI
% threshold must therefore be 5, not the GUI label's apparent 10.
p=struct('dt',.5,'method','pchip','gap_policy','zero','gap_multiplier',10);
[r,s]=runFixture(testCase,'interpolation-pro-original-gaps',data,p);
grid=data(1,1):p.dt:data(end,1);
expected=interp1(data(:,1),data(:,2),grid,p.method);
inside=grid>2&grid<10;expected(inside)=0;
verifyEqual(testCase,s.interpolated,[grid(:),expected(:)],'AbsTol',1e-12);
verifyEqual(testCase,s.gaps,[2,10]);
verifyEqual(testCase,r.summary.gap_threshold,5);
verifyEqual(testCase,r.summary.zero_filled_rows,sum(inside));
verifyEqual(testCase,s.interpolated(s.interpolated(:,1)==2,2),3);
verifyEqual(testCase,s.interpolated(s.interpolated(:,1)==10,2),4);
verifyTrue(testCase,any(contains(string(r.warnings),'synthetic zeros')));
end

function testDefaultDoesNotZeroFillAndPreservesGuiTail(testCase)
data=[0,1;1,2;2,3;10,4;11,5;12,6];
p=struct('dt',.7,'method','linear');
[r,s]=runFixture(testCase,'interpolation-pro-no-gap-fill',data,p);
grid=data(1,1):p.dt:data(end,1);
verifyEqual(testCase,s.interpolated(:,1),grid');
verifyEqual(testCase,s.interpolated(:,2),interp1(data(:,1),data(:,2),grid,'linear')','AbsTol',1e-12);
verifyFalse(testCase,r.summary.endpoint_included);
verifyEqual(testCase,r.summary.unfilled_tail,data(end,1)-grid(end),'AbsTol',1e-12);
verifyEqual(testCase,r.summary.gap_policy,'interpolate');
verifyEqual(testCase,r.summary.zero_filled_rows,0);
verifyEmpty(testCase,s.gaps);
end

function testGuiFallbackVersusExplicitStrictGrid(testCase)
data=[0,1;1,3;2,2;3,4];p=struct('dt',5);
[r,s]=runFixture(testCase,'interpolation-pro-gui-endpoints',data,p);
verifyTrue(testCase,r.summary.gui_two_endpoint_fallback);
verifyEqual(testCase,r.summary.requested_dt,5);
verifyEqual(testCase,r.summary.sample_interval,3);
verifyEqual(testCase,s.interpolated,data([1,end],:));
p.endpoint_policy='strict_grid';
request=prepareFixture(testCase,'interpolation-pro-strict-no-fallback',data,p);
verifyError(testCase,@()acycle_interpolate_pro(request),'Harness:InterpolationEndpoint');
end

function testDefaultMedianPrecisionMatchesGuiEditbox(testCase)
x=[0;1.123456789123;2.246913578246;3.370370367369];data=[x,[0;1;3;2]];
[r,~]=runFixture(testCase,'interpolation-pro-default-dt',data,struct());
expected=str2double(num2str(median(diff(data(:,1))),'%.10g'));
verifyEqual(testCase,r.parameters.dt,expected,'AbsTol',1e-14);
verifyEqual(testCase,r.parameters.method,'linear');
end

function testRejectsAmbiguousInputAndUnsafeAllocation(testCase)
data=[0,1;1,2;2,4;3,3];
request=prepareFixture(testCase,'interpolation-pro-duplicate',[data;1,7],struct());
verifyError(testCase,@()acycle_interpolate_pro(request),'Harness:InterpolationDuplicates');
request=prepareFixture(testCase,'interpolation-pro-nonfinite',[data;4,NaN],struct());
verifyError(testCase,@()acycle_interpolate_pro(request),'Harness:InterpolationNonfinite');
request=prepareFixture(testCase,'interpolation-pro-grid-budget',data,struct('dt',1e-9));
verifyError(testCase,@()acycle_interpolate_pro(request),'Harness:InterpolationGridLimit');
request=prepareFixture(testCase,'interpolation-pro-unknown-field',data,struct('extrapolate',true));
verifyError(testCase,@()acycle_interpolate_pro(request),'Harness:UnknownParameter');
end

function testPreventsCompletedOutputOverwrite(testCase)
request=prepareFixture(testCase,'interpolation-pro-immutable',[0,1;1,3;2,2],struct());
r=acycle_interpolate_pro(request);
fid=fopen(r.artifacts.analysis_mat,'rb');before=fread(fid,Inf,'*uint8');fclose(fid);
verifyError(testCase,@()acycle_interpolate_pro(request),'Harness:OutputExists');
fid=fopen(r.artifacts.analysis_mat,'rb');after=fread(fid,Inf,'*uint8');fclose(fid);
verifyEqual(testCase,after,before);
end

function [result,saved]=runFixture(testCase,name,data,p)
request=prepareFixture(testCase,name,data,p);result=acycle_interpolate_pro(request);
saved=load(result.artifacts.analysis_mat);
fid=fopen(fullfile(request.output_dir,'response.json'),'w');
cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s\n',jsonencode(result,'PrettyPrint',true));
end

function request=prepareFixture(testCase,name,data,p)
out=fullfile(testCase.TestData.output,name);if ~isfolder(out),mkdir(out);end
input=fullfile(out,'input.csv');writematrix(data,input);
request=struct('input_path',input,'output_dir',out,'acycle_root',testCase.TestData.root, ...
    'operation','interpolate_pro','parameters',p);
fid=fopen(fullfile(out,'request.json'),'w');cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s',jsonencode(request));
end
