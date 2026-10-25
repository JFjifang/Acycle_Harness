"""Preparation-tool transport and lineage tests, with no MATLAB/science execution.

The fake backend writes fixed opaque artifacts to exercise the file contract. Its
control points are fixture values, not a numerical reference or a tuning result.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from acycle_deepseek import tools


RAW = b'0,11\r10,13\r20,12\r30,14\r40,11\r'
FILTERED = b'0,0,1\n10,1,1\n20,-1,1\n30,1,1\n40,0,1\n'
CONTROLS = [[10, 100], [20, 505], [30, 910]]
CONTROL_BYTES = b'10,100\n20,505\n30,910\n'
TUNE = {'period_kyr': 405, 'anchor_age_kyr': 100, 'anchor_phase': 'peak',
        'extrema': 'peaks', 'depth_unit': 'cm', 'endpoint_policy': 'trim'}


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / 'proxy.txt').write_bytes(RAW)
    state = SimpleNamespace(root=tmp_path, calls=[], defaults={}, fail_operation=None)

    def execute(request):
        state.calls.append(deepcopy(request))
        output = Path(request['output_dir'])
        if request['operation'] == state.fail_operation:
            (output / 'matlab.log').write_text('Fixture MATLAB stage failed.\n')
            (output / 'response.json').write_text(json.dumps({
                'status': 'error', 'error': 'Fixture:InsufficientExtrema'}))
            (output / 'stderr.txt').write_text('Fixture diagnostic stderr.\n')
            raise RuntimeError('Fixture MATLAB operation failed')
        parameters = {**state.defaults, **request['parameters']}
        summary, artifacts = {}, {}
        if request['operation'] == 'analyze':
            artifact = output / 'filtered.csv'
            artifact.write_bytes(FILTERED)
            artifacts['filtered_csv'] = str(artifact)
        elif request['operation'] == 'interpolate_pro':
            artifact = output / 'interpolated.csv'
            artifact.write_bytes(b'0,11\n10,13\n20,12\n30,14\n40,11\n')
            artifacts['interpolated_csv'] = str(artifact)
        elif request['operation'] == 'tune':
            artifact = output / 'age_model.csv'
            artifact.write_bytes(CONTROL_BYTES)
            artifacts['age_model_csv'] = str(artifact)
            summary = {'age_model': deepcopy(CONTROLS),
                       'valid_depth_range': [10, 30],
                       'depth_unit': parameters['depth_unit']}
        return {'status': 'success', 'backend': 'matlab',
                'operation': request['operation'], 'parameters': parameters,
                'summary': summary, 'artifacts': artifacts,
                'provenance': {'fixture_only': True}}

    monkeypatch.setattr(tools, '_execute', execute)
    monkeypatch.delenv('ACYCLE_ROOT', raising=False)
    return state


def call(project, operation, **arguments):
    return tools.dispatch('acycle_' + operation, arguments, project.root)


def tune_run(project, **arguments):
    return call(project, 'tune', input_path=arguments.pop('input_path', 'proxy.txt'),
                parameters=arguments.pop('parameters', deepcopy(TUNE)), **arguments)


def saved_path(run):
    return Path(run['input_path']).parent / 'result.json'


def test_public_schemas_expose_preparation_contract_and_scoped_tuning_link():
    schemas = {entry['function']['name']: entry['function']['parameters']
               for entry in tools.tool_schemas()}
    interpolation = schemas['acycle_interpolate_pro']['properties']['parameters']
    assert set(interpolation['properties']['method']['enum']) == {
        'linear', 'nearest', 'next', 'previous', 'pchip', 'cubic', 'v5cubic',
        'makima', 'spline'}
    assert set(interpolation['properties']['gap_policy']['enum']) == {'interpolate', 'zero'}
    tuning = schemas['acycle_tune']['properties']['parameters']
    assert set(tuning['required']) >= {
        'period_kyr', 'anchor_age_kyr', 'anchor_phase', 'extrema', 'depth_unit'}
    assert set(tuning['properties']['extrema']['enum']) == {'peaks', 'troughs', 'both'}
    assert 'tuning_run_id' in schemas['acycle_analyze']['properties']
    for operation in ('interpolate_pro', 'tune', 'coco', 'ecoco', 'swa'):
        assert 'tuning_run_id' not in schemas['acycle_' + operation]['properties']


@pytest.mark.parametrize('operation,parameters,artifact_key', [
    ('interpolate_pro', {'method': 'makima', 'dt': 1, 'coordinate_unit': 'cm',
                         'gap_policy': 'zero', 'gap_multiplier': 10,
                         'endpoint_policy': 'strict_grid'}, 'interpolated_csv'),
    ('tune', TUNE, 'age_model_csv'),
])
def test_preparation_dispatch_freezes_original_bytes_and_hashes_matlab_artifact(
        project, operation, parameters, artifact_key):
    run = call(project, operation, input_path='proxy.txt', parameters=deepcopy(parameters))
    request = project.calls[0]
    assert request['operation'] == run['operation'] == operation
    assert request['parameters'] == parameters
    assert Path(request['input_path']).read_bytes() == RAW
    assert Path(request['input_path']) != project.root / 'proxy.txt'
    assert (project.root / 'proxy.txt').read_bytes() == RAW
    assert run['input_sha256'] == hashlib.sha256(RAW).hexdigest()
    artifact = Path(run['artifacts'][artifact_key])
    assert artifact.is_relative_to(Path(run['output_dir']))
    assert run['artifact_sha256'][artifact_key] == hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert json.loads(saved_path(run).read_text())['operation'] == operation


def test_interpolation_adjustment_preserves_method_gap_policy_and_frozen_input(project):
    settings = {'method': 'pchip', 'dt': 2, 'coordinate_unit': 'cm',
                'gap_policy': 'zero', 'gap_multiplier': 8, 'endpoint_policy': 'strict_grid'}
    base = call(project, 'interpolate_pro', input_path='proxy.txt', parameters=settings)
    before = saved_path(base).read_bytes()
    (project.root / 'proxy.txt').write_text('0,999\n')
    child = call(project, 'rerun', run_id=base['run_id'], parameter_patch={'dt': 1})
    assert child['operation'] == 'interpolate_pro'
    assert child['parameters'] == {**settings, 'dt': 1}
    assert child['parent_run_id'] == base['run_id']
    assert child['input_sha256'] == base['input_sha256']
    assert project.calls[-1]['operation'] == 'interpolate_pro'
    assert Path(child['input_path']).read_bytes() == RAW
    assert saved_path(base).read_bytes() == before


def test_tuning_phase_branch_preserves_period_anchor_units_and_boundary_policy(project):
    base = tune_run(project)
    before = saved_path(base).read_bytes()
    child = call(project, 'rerun', run_id=base['run_id'],
                 parameter_patch={'anchor_phase': 'trough', 'extrema': 'troughs'})
    assert child['operation'] == project.calls[-1]['operation'] == 'tune'
    assert child['parameters'] == {**TUNE, 'anchor_phase': 'trough', 'extrema': 'troughs'}
    assert child['parent_run_id'] == base['run_id']
    assert child['input_sha256'] == base['input_sha256']
    assert child['steering']['parameter_patch'] == {'anchor_phase': 'trough', 'extrema': 'troughs'}
    assert saved_path(base).read_bytes() == before


def test_phase_conflict_is_rejected_before_starting_another_matlab_job(project):
    base = tune_run(project)
    with pytest.raises(ValueError, match='anchor_phase'):
        call(project, 'rerun', run_id=base['run_id'], parameter_patch={'extrema': 'troughs'})
    assert len(project.calls) == 1


@pytest.mark.parametrize('missing', ['period_kyr', 'anchor_age_kyr', 'depth_unit'])
def test_tuning_cannot_invent_required_scientific_context(project, missing):
    parameters = deepcopy(TUNE)
    del parameters[missing]
    with pytest.raises(ValueError, match='Missing MATLAB parameters'):
        tune_run(project, parameters=parameters)
    assert not project.calls


def test_tuning_reference_applies_matlab_controls_and_trim_to_original_proxy(project):
    tuning = tune_run(project)
    parameters = {'coordinate_unit': 'kyr', 'dt': 5, 'detrend': 'lowess', 'span': .35}
    initial_parameters = deepcopy(parameters)
    analysis = call(project, 'analyze', input_path='proxy.txt', parameters=parameters,
                    tuning_run_id=tuning['run_id'])
    request = project.calls[-1]
    assert request['operation'] == 'analyze'
    assert request['parameters'] == {**initial_parameters, 'age_model': CONTROLS,
                                     'coordinate_range': [10, 30], 'depth_unit': 'cm'}
    assert parameters == initial_parameters
    assert Path(request['input_path']).read_bytes() == RAW
    assert analysis['input_sha256'] == hashlib.sha256(RAW).hexdigest()
    reference = analysis['tuning_reference']
    assert reference['run_id'] == tuning['run_id']
    assert reference['age_model_sha256'] == hashlib.sha256(CONTROL_BYTES).hexdigest()
    assert reference['endpoint_policy'] == 'trim'
    assert json.loads(saved_path(analysis).read_text())['tuning_reference'] == reference


@pytest.mark.parametrize('conflict', [
    {'age_model': [[10, 1], [30, 2]]},
    {'sedimentation_rate': 10},
    {'coordinate_range': [0, 40]},
    {'depth_unit': 'm'},
])
def test_tuning_reference_rejects_competing_model_range_or_unit(project, conflict):
    tuning = tune_run(project)
    with pytest.raises(ValueError):
        call(project, 'analyze', input_path='proxy.txt', parameters=conflict,
             tuning_run_id=tuning['run_id'])
    assert len(project.calls) == 1


def test_modified_tuning_control_artifact_is_rejected_before_dispatch(project):
    tuning = tune_run(project)
    Path(tuning['artifacts']['age_model_csv']).write_text('10,0\n30,1\n')
    with pytest.raises(ValueError, match='checksum changed'):
        call(project, 'analyze', input_path='proxy.txt', tuning_run_id=tuning['run_id'])
    assert len(project.calls) == 1


@pytest.mark.parametrize('corruption', ['missing', 'outside_run'])
def test_tuning_reference_requires_original_in_run_control_artifact(project, corruption):
    tuning = tune_run(project)
    artifact = Path(tuning['artifacts']['age_model_csv'])
    if corruption == 'missing':
        artifact.unlink()
    else:
        outside = project.root / 'untracked-controls.csv'
        outside.write_bytes(CONTROL_BYTES)
        record = json.loads(saved_path(tuning).read_text())
        record['artifacts']['age_model_csv'] = str(outside)
        saved_path(tuning).write_text(json.dumps(record))
    with pytest.raises(ValueError, match='missing or outside'):
        call(project, 'analyze', input_path='proxy.txt', tuning_run_id=tuning['run_id'])
    assert len(project.calls) == 1


@pytest.mark.parametrize('missing', ['age_model', 'valid_depth_range'])
def test_incomplete_tuning_summary_is_not_reconstructed_in_python(project, missing):
    tuning = tune_run(project)
    record = json.loads(saved_path(tuning).read_text())
    del record['summary'][missing]
    saved_path(tuning).write_text(json.dumps(record))
    with pytest.raises(ValueError, match='machine-readable'):
        call(project, 'analyze', input_path='proxy.txt', tuning_run_id=tuning['run_id'])
    assert len(project.calls) == 1


def test_non_tuning_run_cannot_be_used_as_age_model(project):
    other = call(project, 'analyze', input_path='proxy.txt')
    with pytest.raises(ValueError, match='completed tune run'):
        call(project, 'analyze', input_path='proxy.txt', tuning_run_id=other['run_id'])
    assert len(project.calls) == 1


def test_lineage_distinguishes_filtered_input_from_original_proxy(project):
    depth = call(project, 'analyze', input_path='proxy.txt',
                 parameters={'coordinate_unit': 'cm', 'filter_band': [.01, .02]})
    tuning = tune_run(project, input_path=depth['artifacts']['filtered_csv'])
    analysis = call(project, 'analyze', input_path='proxy.txt', tuning_run_id=tuning['run_id'])
    lineage = tuning['input_lineage']
    assert lineage == {'run_id': depth['run_id'], 'operation': 'analyze',
                       'artifact_path': depth['artifacts']['filtered_csv'],
                       'sha256': hashlib.sha256(FILTERED).hexdigest()}
    assert tuning['input_sha256'] != depth['input_sha256']
    assert analysis['input_sha256'] == depth['input_sha256']
    assert analysis['tuning_reference']['run_id'] == tuning['run_id']
    restored = call(project, 'get_run', run_id=tuning['run_id'])
    assert restored['input_lineage'] == lineage
    assert restored['artifact_sha256']['age_model_csv'] == analysis['tuning_reference']['age_model_sha256']


def test_time_diagnostic_rerun_preserves_applied_controls_and_trimmable_range(project):
    tuning = tune_run(project)
    original = call(project, 'analyze', input_path='proxy.txt', tuning_run_id=tuning['run_id'],
                    parameters={'coordinate_unit': 'kyr', 'span': .35})
    child = call(project, 'rerun', run_id=original['run_id'], parameter_patch={'span': .25})
    assert child['parameters'] == {**original['parameters'], 'span': .25}
    assert child['input_sha256'] == original['input_sha256']
    assert child['parent_run_id'] == original['run_id']
    assert call(project, 'get_run', run_id=child['parent_run_id'])['tuning_reference']['run_id'] == tuning['run_id']


def test_failed_tune_persists_diagnostics_and_cannot_supply_controls(project):
    project.fail_operation = 'tune'
    with pytest.raises(tools.RunError) as caught:
        tune_run(project)
    failure = caught.value.as_result()
    assert failure['status'] == 'failed'
    assert failure['operation'] == 'tune'
    assert failure['run_id']
    assert failure['input_sha256'] == hashlib.sha256(RAW).hexdigest()
    assert failure['parameters'] == TUNE
    assert failure['matlab_error'] == 'Fixture:InsufficientExtrema'
    assert set(failure['diagnostics']) >= {'matlab.log', 'response.json', 'stderr.txt'}
    assert all(Path(path).is_file() for path in failure['diagnostics'].values())
    restored = call(project, 'get_run', run_id=failure['run_id'])
    assert restored['status'] == 'failed'
    assert restored['diagnostics'] == failure['diagnostics']
    assert (Path(failure['output_dir']).parent / 'request.json').is_file()
    assert json.loads(json.dumps(failure, allow_nan=False)) == failure
    with pytest.raises(ValueError, match='completed tune run'):
        call(project, 'analyze', input_path='proxy.txt', tuning_run_id=failure['run_id'])
    assert len(project.calls) == 1


def test_failed_preparation_branch_retains_failed_parent_link_and_baseline(project):
    baseline = tune_run(project)
    before = saved_path(baseline).read_bytes()
    project.fail_operation = 'tune'
    with pytest.raises(tools.RunError) as caught:
        call(project, 'rerun', run_id=baseline['run_id'],
             parameter_patch={'anchor_phase': 'trough', 'extrema': 'troughs'})
    failed = caught.value.as_result()
    assert failed['parent_run_id'] == baseline['run_id']
    assert failed['input_sha256'] == baseline['input_sha256']
    assert failed['run_id'] != baseline['run_id']
    assert failed['parameters']['anchor_phase'] == 'trough'
    assert saved_path(baseline).read_bytes() == before


def test_cancelled_run_retains_retrievable_diagnostics_before_propagating(project, monkeypatch):
    def interrupted(request):
        (Path(request['output_dir']) / 'matlab.log').write_text('Interrupted process fixture\n')
        raise SystemExit(143)
    monkeypatch.setattr(tools, '_execute', interrupted)
    with pytest.raises(SystemExit) as caught:
        tune_run(project)
    assert caught.value.code == 143
    records = list((project.root / '.acycle' / 'runs').glob('*/result.json'))
    assert len(records) == 1
    saved = json.loads(records[0].read_text())
    restored = call(project, 'get_run', run_id=saved['run_id'])
    assert restored['status'] == 'cancelled'
    assert Path(restored['diagnostics']['matlab.log']).read_text() == 'Interrupted process fixture\n'


def test_registered_unchanged_output_propagates_verified_transport_reference(project):
    upstream = call(project, 'analyze', input_path='proxy.txt')
    reference = {'repository': 'owner/project', 'artifact_id': 123,
                 'member': 'filtered.csv', 'input_sha256': hashlib.sha256(FILTERED).hexdigest(),
                 'artifact_sha256': 'a' * 64, 'source_workflow_run_id': 456}
    upstream['result']['artifact_references'] = {'filtered_csv': reference}
    saved_path(upstream).write_text(json.dumps(upstream))
    downstream = tune_run(project, input_path=upstream['artifacts']['filtered_csv'])
    assert project.calls[-1]['input_artifact_reference'] == reference
    assert downstream['input_artifact_reference'] == reference
    assert downstream['input_sha256'] == reference['input_sha256']

    # A conversational branch reads the parent's frozen input, not its original
    # output path. It must retain the reference so a large three-column curve
    # does not fall back into the bounded workflow argument on every rerun.
    branch = call(project, 'rerun', run_id=downstream['run_id'],
                  parameter_patch={'anchor_phase': 'trough', 'extrema': 'troughs'})
    assert project.calls[-1]['input_artifact_reference'] == reference
    assert branch['input_artifact_reference'] == reference
    assert branch['input_sha256'] == downstream['input_sha256']
    assert branch['parent_run_id'] == downstream['run_id']

    # A modified output remains a local input; it cannot point at old remote bytes.
    Path(upstream['artifacts']['filtered_csv']).write_bytes(FILTERED + b'50,0,1\n')
    modified = tune_run(project, input_path=upstream['artifacts']['filtered_csv'])
    assert 'input_artifact_reference' not in project.calls[-1]
    assert 'input_artifact_reference' not in modified
