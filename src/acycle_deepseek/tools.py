"""Small, auditable orchestration layer; all scientific work belongs to MATLAB."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid
from datetime import datetime, timezone


def _write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def _root(workspace):
    root = Path(workspace).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _input_path(root, path):
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    allowed = [root]
    if os.environ.get('ACYCLE_ROOT'):
        allowed.append(Path(os.environ['ACYCLE_ROOT']).resolve())
    if not any(candidate.is_relative_to(base) for base in allowed):
        raise ValueError('Input must be inside workspace or ACYCLE_ROOT')
    if not candidate.is_file():
        raise ValueError(f'Input file does not exist: {candidate}')
    if candidate.suffix.lower() not in {'.csv', '.txt', '.dat', '.tsv'}:
        raise ValueError('Use a two-column numeric CSV, TXT, DAT or TSV file')
    return candidate


def _run_path(root, run_id):
    if not isinstance(run_id, str) or not re.fullmatch(r'[0-9]{8}T[0-9]{6}Z-[a-f0-9]{12}', run_id):
        raise ValueError('Invalid run_id')
    candidate = root / '.acycle' / 'runs' / run_id
    if not candidate.resolve().is_relative_to(root):
        raise ValueError('Run storage must remain inside workspace')
    return candidate


def _get(root, run_id):
    path = _run_path(root, run_id) / 'result.json'
    if not path.resolve().is_relative_to(root):
        raise ValueError('Saved result must remain inside workspace')
    if not path.is_file():
        raise ValueError(f'Unknown run: {run_id}')
    return json.loads(path.read_text(encoding='utf-8'))


def _matlab_dir():
    bundled = Path(__file__).parent / 'matlab'
    if bundled.is_dir():
        return bundled
    source = Path(__file__).resolve().parents[2] / 'matlab'
    if source.is_dir():
        return source
    raise RuntimeError('MATLAB bridge is missing from installation')


def _matlab_string(value):
    return "'" + str(value).replace("'", "''") + "'"


def _execute(request):
    backend = os.environ.get('ACYCLE_BACKEND', 'local')
    if backend == 'github':
        from .github_backend import run
        return run(request)
    if backend != 'local':
        raise ValueError('ACYCLE_BACKEND must be local or github; no Python science fallback exists')
    executable = os.environ.get('MATLAB_EXECUTABLE', 'matlab')
    if not shutil.which(executable):
        raise RuntimeError('MATLAB is required. Set MATLAB_EXECUTABLE or ACYCLE_BACKEND=github. No Python numerical fallback is used.')
    if not request.get('acycle_root'):
        raise RuntimeError('Set ACYCLE_ROOT to an Acycle source checkout')
    output = Path(request['output_dir'])
    request_path, response_path = output / 'matlab-request.json', output / 'response.json'
    _write(request_path, request)
    expression = f"addpath({_matlab_string(_matlab_dir())}); acycle_batch({_matlab_string(request_path)},{_matlab_string(response_path)});"
    with (output / 'matlab.log').open('w', encoding='utf-8') as log:
        completed = subprocess.run([executable, '-batch', expression], stdout=log, stderr=subprocess.STDOUT,
                                   timeout=int(os.environ.get('ACYCLE_MATLAB_TIMEOUT', '1800')), check=False)
    if not response_path.is_file():
        raise RuntimeError(f'MATLAB returned {completed.returncode} without a response; see {output / "matlab.log"}')
    response = json.loads(response_path.read_text(encoding='utf-8'))
    if completed.returncode or response.get('status') not in {'ok', 'success', 'completed'}:
        raise RuntimeError(f'MATLAB analysis failed: {response.get("error", response.get("message", "see matlab.log"))}')
    return response


def _analyze(root, arguments, operation='analyze'):
    source = _input_path(root, arguments['input_path'])
    parameters = arguments.get('parameters', {})
    if not isinstance(parameters, dict):
        raise ValueError('parameters must be an object')
    schema = next(t for t in tool_schemas() if t['function']['name']=='acycle_'+operation)['function']['parameters']['properties']['parameters']
    unknown = set(parameters) - set(schema['properties'])
    if unknown:
        raise ValueError(f'Unknown MATLAB parameters: {sorted(unknown)}')
    missing = set(schema.get('required', [])) - set(parameters)
    if missing:
        raise ValueError(f'Missing MATLAB parameters: {sorted(missing)}')
    parent = arguments.get('parent_run_id')
    if parent:
        previous = _get(root, parent)
        if previous.get('status') != 'completed':
            raise ValueError('Parent run must be completed')
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:12]
    run_dir = _run_path(root, run_id)
    run_dir.mkdir(parents=True)
    # Freeze exact bytes so later edits to user input do not change a steering run.
    frozen = run_dir / ('input' + source.suffix.lower())
    shutil.copyfile(source, frozen)
    output = run_dir / 'outputs'
    output.mkdir()
    record = {'run_id':run_id, 'status':'running', 'label':arguments.get('label',''),
              'parent_run_id':parent, 'input_path':str(frozen), 'original_input_path':str(source),
              'input_sha256':hashlib.sha256(frozen.read_bytes()).hexdigest(),
              'operation':operation, 'parameters':parameters, 'created_at':datetime.now(timezone.utc).isoformat(),
              'backend':os.environ.get('ACYCLE_BACKEND','local'), 'output_dir':str(output)}
    _write(run_dir / 'request.json', record)
    try:
        response = _execute({'input_path':str(frozen), 'output_dir':str(output),
                             'acycle_root':os.environ.get('ACYCLE_ROOT',''),
                             'operation':operation, 'parameters':parameters})
        record.update({'status':'completed', 'result':response})
        record['summary'] = response.get('summary', {})
        record['effective_parameters'] = response.get('parameters', parameters)
        record['artifacts'] = response.get('artifacts', {})
        record['provenance'] = response.get('provenance', {})
    except Exception as exc:
        record.update({'status':'failed', 'error':str(exc)})
        _write(run_dir / 'result.json', record)
        raise RuntimeError(f'Run {run_id} failed: {exc}') from exc
    _write(run_dir / 'result.json', record)
    return record


def dispatch(name, args, workspace='.'):
    """Execute a tool. Python handles files/metadata and delegates analysis to MATLAB."""
    if not isinstance(args, dict):
        raise ValueError('Tool arguments must be an object')
    known = {entry['function']['name']:entry['function']['parameters'] for entry in tool_schemas()}
    if name not in known:
        raise ValueError(f'Unknown tool: {name}')
    spec = known[name]
    extras = set(args) - set(spec['properties'])
    missing = set(spec.get('required', [])) - set(args)
    if extras or missing:
        raise ValueError(f'Invalid arguments: unknown={sorted(extras)}, missing={sorted(missing)}')
    root = _root(workspace)
    if name == 'acycle_capabilities':
        remote = os.environ.get('ACYCLE_BACKEND','local') == 'github'
        return {'version':'0.3.0', 'scientific_backend':'MATLAB/Acycle',
                'backend':os.environ.get('ACYCLE_BACKEND','local'),
                'matlab_available':bool(shutil.which(os.environ.get('MATLAB_EXECUTABLE','matlab'))),
                'acycle_root':os.environ.get('ACYCLE_ROOT'),
                'github_repository':os.environ.get('ACYCLE_GITHUB_REPO'),
                'remote_backend_configured':remote and bool(os.environ.get('ACYCLE_GITHUB_REPO')),
                'execution_note':('GitHub backend runs MATLAB remotely; local matlab_available does not indicate remote readiness. A dispatched run verifies execution.' if remote else 'Local backend requires MATLAB_EXECUTABLE and ACYCLE_ROOT.'),
                'python_numerical_fallback':False,
                'operations':['mini_robot','mtm_rednoise','evolution','filter_envelope','age_model','swa','coco','ecoco'],
                'limits':['pointwise significance is not proof of astronomical forcing',
                          'Acycle GUI-only methods outside this core require a sourced MATLAB extension']}
    if name == 'acycle_inspect':
        path = _input_path(root,args['input_path'])
        content = path.read_bytes()
        lines = content.decode('utf-8-sig').splitlines()
        return {'input_path':str(path), 'bytes':len(content), 'sha256':hashlib.sha256(content).hexdigest(),
                'line_count':len(lines), 'preview':lines[:8],
                'note':'Structural preview only; scientific QA, duplicate handling, interpolation and plots run in MATLAB.'}
    if name in {'acycle_analyze','acycle_swa','acycle_coco','acycle_ecoco'}:
        return _analyze(root,args,name.removeprefix('acycle_'))
    if name == 'acycle_get_run':
        return _get(root,args['run_id'])
    if name == 'acycle_sensitivity':
        baseline = _get(root,args['run_id'])
        if baseline['status'] != 'completed':
            raise ValueError('Baseline must be completed')
        parameter = args['parameter']
        operation = baseline.get('operation','analyze')
        allowed = {
            'analyze': {'span','mtm_nw','smooth_fraction','dt','evolution_window','evolution_step','filter_band','sedimentation_rate'},
            'swa': {'mtm_nw','pad_factor','fmax','detrend'},
            'coco': {'sedimentation_rate_min','sedimentation_rate_max','sedimentation_rate_step','middle_age_ma','orbital_periods_kyr','nsim','seed','correlation','red_noise','nfft','max_frequency','slices','dt','detrend','span','detrend_window','method'},
            'ecoco': {'sedimentation_rate_min','sedimentation_rate_max','sedimentation_rate_step','middle_age_ma','orbital_periods_kyr','nsim','seed','correlation','red_noise','nfft','max_frequency','window','step','method','detrend','span','detrend_window'},
        }.get(operation,set())
        if parameter not in allowed:
            raise ValueError(f'Unsupported sensitivity parameter: {parameter}')
        values = args['values']
        if not isinstance(values,list) or not 1 <= len(values) <= 12:
            raise ValueError('Provide 1–12 parameter values')
        runs = []
        for value in values:
            params = dict(baseline['parameters'])
            if operation in {'coco','ecoco'}:
                alternatives={'middle_age_ma':'orbital_periods_kyr','orbital_periods_kyr':'middle_age_ma',
                              'span':'detrend_window','detrend_window':'span'}
                if parameter in alternatives:
                    params.pop(alternatives[parameter],None)
            params[parameter] = value
            run = _analyze(root,{'input_path':baseline['input_path'], 'parameters':params,
                                'parent_run_id':baseline['run_id'], 'label':f'{parameter}={value}'},operation)
            runs.append({'run_id':run['run_id'], 'parameters':run['parameters'], 'summary':run['summary']})
        return {'baseline_run_id':baseline['run_id'], 'operation':operation, 'parameter':parameter, 'runs':runs}
    if name == 'acycle_compare':
        ids = args['run_ids']
        if not isinstance(ids,list) or not 2 <= len(ids) <= 20:
            raise ValueError('Provide 2–20 run IDs')
        records = [_get(root,r) for r in ids]
        return {'runs':[{k:r.get(k) for k in ['run_id','status','operation','label','parent_run_id','input_sha256','parameters','effective_parameters','summary','artifacts','provenance']} for r in records],
                'note':'Comparison reports existing MATLAB results and metadata; infer robustness with sampling, chronology and independent geological constraints.'}
    raise AssertionError('Unreachable tool dispatch')


def tool_schemas():
    string = {'type':'string'}
    parameter_schema = {'type':'object','description':'MATLAB parameters. Defaults follow pinned Acycle mini robot: LOWESS span .35, NW 2. Frequencies follow input coordinate units (or kyr after age conversion).',
        'properties':{
            'detrend':{'type':'string','enum':['lowess','rlowess','loess','rloess','linear','mean','none']},
            'span':{'type':'number','minimum':0.01,'maximum':1},
            'dt':{'type':'number','exclusiveMinimum':0},
            'mtm_nw':{'type':'number','minimum':1,'maximum':8},
            'nfft':{'type':'integer','minimum':8},
            'smooth_fraction':{'type':'number','exclusiveMinimum':0,'maximum':0.25},
            'fmax':{'type':'number','exclusiveMinimum':0},
            'fit_fmax':{'type':'number','exclusiveMinimum':0},
            'coordinate_unit':{'type':'string'},
            'rolloff_exponent':{'type':'number','exclusiveMinimum':0,'maximum':20},
            'evolution':{'type':'boolean'},
            'evolution_window':{'type':'number','exclusiveMinimum':0},
            'evolution_step':{'type':'number','exclusiveMinimum':0},
            'filter_band':{'type':'array','items':{'type':'number'},'minItems':2,'maxItems':2},
            'filter_method':{'type':'string','enum':['gaussian','taner_hilbert']},
            'sedimentation_rate':{'type':'number','exclusiveMinimum':0,'description':'cm/kyr; requires depth_unit'},
            'depth_unit':{'type':'string','enum':['m','dm','cm','mm','ft','km']},
            'first_age_kyr':{'type':'number'},
            'age_model':{'type':'array','items':{'type':'array','items':{'type':'number'},'minItems':2,'maxItems':2}}
        },'additionalProperties':False}
    swa_schema = {'type':'object','additionalProperties':False,
        'description':'Original Acycle Smoothed Window Averages with FDR. Lomb accepts irregular sampling; MTM requires uniform samples. Both require at least66 samples; legacy window-selection failures are reported explicitly. Lomb always applies its original detrending/taper settings; MTM-only settings must be omitted for Lomb.',
        'properties':{
            'method':{'type':'string','enum':['lomb','mtm']},
            'coordinate_unit':string,
            'fmax':{'type':'number','exclusiveMinimum':0},
            'mtm_nw':{'type':'number','minimum':1,'maximum':8},
            'pad_factor':{'type':'number','minimum':1,'maximum':10},
            'detrend':{'type':'string','enum':['mean','linear','none']},
        }}
    coco_properties = {
        'depth_unit':{'type':'string','enum':['m','dm','cm','mm','ft','km']},
        'middle_age_ma':{'type':'number','minimum':0,'description':'Astronomical target age (Ma); supply this OR explicit orbital_periods_kyr.'},
        'orbital_periods_kyr':{'type':'array','items':{'type':'number','exclusiveMinimum':0},'minItems':2,'maxItems':9,'description':'Distinct orbital target periods in kyr; COCO supports 2–9, eCOCO requires exactly 9.'},
        'sedimentation_rate_min':{'type':'number','exclusiveMinimum':0,'description':'cm/kyr'},
        'sedimentation_rate_max':{'type':'number','exclusiveMinimum':0,'description':'cm/kyr'},
        'sedimentation_rate_step':{'type':'number','exclusiveMinimum':0,'description':'cm/kyr'},
        'nsim':{'type':'integer','minimum':1,'maximum':10000,'description':'Monte Carlo simulations; default199. Small counts are diagnostics only; use999+ for substantive significance checks.'},
        'seed':{'type':'integer','minimum':0,'maximum':4294967295},
        'correlation':{'type':'string','enum':['Pearson','Spearman']},
        'red_noise':{'type':'integer','minimum':0,'maximum':3,'description':'Spectral background subtraction:0 none,1 classical AR(1),2 robust AR(1),3 SWA. This does not disable the original Monte Carlo null.'},
        'nfft':{'type':'integer','minimum':16},
        'max_frequency':{'type':'number','exclusiveMinimum':0,'description':'cycles/kyr for the astronomical target'},
        'detrend':{'type':'string','enum':['linear','lowess','loess'],'description':'Default linear. Nonlinear full-record detrending is disabled for blocked/interleaved eCOCO to prevent validation leakage.'},
        'span':{'type':'number','exclusiveMinimum':0,'maximum':1,'description':'Fraction for lowess/loess; supply this OR detrend_window.'},
        'detrend_window':{'type':'number','exclusiveMinimum':0,'description':'Physical window in input depth_unit, converted to Acycle span fraction; requires lowess/loess.'},
    }
    coco_required=['depth_unit','sedimentation_rate_min','sedimentation_rate_max','sedimentation_rate_step']
    coco_schema={'type':'object','additionalProperties':False,'required':coco_required,
        'description':'Original COCO 2.0. adaptive uses the coherent-nine target (requires9 periods); phase_averaged supports2–9. Requires units, rate grid and exactly one target definition (middle_age_ma or orbital_periods_kyr).',
        'properties':{**coco_properties,'method':{'type':'string','enum':['adaptive','phase_averaged']},'slices':{'type':'integer','minimum':1,'maximum':20},'dt':{'type':'number','exclusiveMinimum':0,'description':'Optional explicit regular-grid sampling interval in depth_unit, applied in MATLAB after detrending; default is the original median spacing.'}}}
    ecoco_schema={'type':'object','additionalProperties':False,'required':[*coco_required,'window','step'],
        'description':'Original evolutionary COCO 2.0, physical windows without edge padding. Target requires exactly9 periods, or middle_age_ma. Monte Carlo settings and target are preserved.',
        'properties':{**coco_properties,'orbital_periods_kyr':{**coco_properties['orbital_periods_kyr'],'minItems':9,'maxItems':9},
            'method':{'type':'string','enum':['adaptive','blocked','interleaved']},
            'window':{'type':'number','exclusiveMinimum':0,'description':'Window length in the declared input depth_unit'},
            'step':{'type':'number','exclusiveMinimum':0,'description':'Window step in the declared input depth_unit'}}}
    specs = [
        ('acycle_capabilities','Inspect configured MATLAB backend and supported Acycle core. No numerical Python fallback.',{},[]),
        ('acycle_inspect','Preview a two-column input file and its checksum. MATLAB performs scientific QA.',{'input_path':string},['input_path']),
        ('acycle_analyze','Run Acycle original MATLAB computation and MATLAB plots. Creates immutable run with source provenance.',
         {'input_path':string,'parameters':parameter_schema,'label':string,'parent_run_id':string},['input_path']),
        ('acycle_swa','Run original MATLAB SWA (Smoothed Window Averages) and FDR; save original tables and MATLAB figures.',
         {'input_path':string,'parameters':swa_schema,'label':string,'parent_run_id':string},['input_path']),
        ('acycle_coco','Run Acycle adaptive COCO in MATLAB to evaluate sedimentation rates with explicit orbital targets and Monte Carlo settings.',
         {'input_path':string,'parameters':coco_schema,'label':string,'parent_run_id':string},['input_path','parameters']),
        ('acycle_ecoco','Run Acycle evolutionary COCO in MATLAB; retain window-wise rates, uncertainty and original statistical outputs.',
         {'input_path':string,'parameters':ecoco_schema,'label':string,'parent_run_id':string},['input_path','parameters']),
        ('acycle_sensitivity','Branch a completed run, varying one parameter in MATLAB; preserve baseline.',
         {'run_id':string,'parameter':string,'values':{'type':'array','items':{},'minItems':1,'maxItems':12}},['run_id','parameter','values']),
        ('acycle_compare','Read existing MATLAB results and parameters side by side without recomputing.',
         {'run_ids':{'type':'array','items':string,'minItems':2,'maxItems':20}},['run_ids']),
        ('acycle_get_run','Retrieve a saved run with outputs, parameters and provenance.',{'run_id':string},['run_id'])]
    return [{'type':'function','function':{'name':name,'description':description,
             'parameters':{'type':'object','properties':properties,'required':required,'additionalProperties':False}}}
            for name,description,properties,required in specs]
