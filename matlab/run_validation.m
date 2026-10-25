function results = run_validation(acycleRoot,outputDir)
%RUN_VALIDATION Original-function parity, official fixtures, and figure checks.
% run_validation('/path/to/acycle','/path/to/new/validation-output')
if nargin<1, acycleRoot=getenv('ACYCLE_ROOT'); end
if nargin<2, outputDir=fullfile(pwd,'validation','matlab'); end
if ~isfolder(outputDir),mkdir(outputDir);end
oldRoot=getenv('ACYCLE_ROOT'); oldOutput=getenv('ACYCLE_VALIDATION_DIR');
restore=onCleanup(@()restoreEnvironment(oldRoot,oldOutput)); %#ok<NASGU>
setenv('ACYCLE_ROOT',acycleRoot); setenv('ACYCLE_VALIDATION_DIR',outputDir);
folder=fileparts(mfilename('fullpath'));
suite=matlab.unittest.TestSuite.fromFolder(fullfile(folder,'tests'));
runner=matlab.unittest.TestRunner.withTextOutput;
runner.addPlugin(matlab.unittest.plugins.XMLPlugin.producingJUnitFormat( ...
    fullfile(outputDir,'junit.xml')));
results=runner.run(suite);
receipt=struct('matlab_version',version,'release',version('-release'), ...
    'acycle_root',acycleRoot,'passed',sum([results.Passed]), ...
    'failed',sum([results.Failed]),'incomplete',sum([results.Incomplete]), ...
    'tests',struct('name',{results.Name},'passed',num2cell([results.Passed]), ...
        'failed',num2cell([results.Failed]),'duration_seconds',num2cell([results.Duration])));
fid=fopen(fullfile(outputDir,'validation-summary.json'),'w');
cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s\n',jsonencode(receipt,'PrettyPrint',true));
assert(all([results.Passed]),'Harness:ValidationFailed','MATLAB validation failed; inspect junit.xml.');
end

function restoreEnvironment(root,output)
setenv('ACYCLE_ROOT',root); setenv('ACYCLE_VALIDATION_DIR',output);
end
