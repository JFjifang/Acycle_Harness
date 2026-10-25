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
receipt.validation_scope=['Engineering, original-function numerical parity and executable examples. ', ...
    'A passed test suite does not imply that independent publication criteria were reproduced.'];
comparisons=dir(fullfile(outputDir,'**','*comparison.json'));
publicationChecks=cell(1,numel(comparisons));
for k=1:numel(comparisons)
    comparison=jsondecode(fileread(fullfile(comparisons(k).folder,comparisons(k).name)));
    state='not_claimed';
    if isfield(comparison,'publication_reproduction_passed')
        if comparison.publication_reproduction_passed, state='passed'; else, state='failed'; end
    elseif isfield(comparison,'within_predeclared_published_range')
        if comparison.within_predeclared_published_range, state='passed'; else, state='failed'; end
    end
    [~,caseName]=fileparts(comparisons(k).folder);
    publicationChecks{k}=struct('case',caseName,'publication_criterion',state, ...
        'evidence_file',fullfile(caseName,comparisons(k).name));
end
receipt.publication_checks=publicationChecks;
fid=fopen(fullfile(outputDir,'validation-summary.json'),'w');
cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s\n',jsonencode(receipt,'PrettyPrint',true));
assert(all([results.Passed]),'Harness:ValidationFailed','MATLAB validation failed; inspect junit.xml.');
end

function restoreEnvironment(root,output)
setenv('ACYCLE_ROOT',root); setenv('ACYCLE_VALIDATION_DIR',output);
end
