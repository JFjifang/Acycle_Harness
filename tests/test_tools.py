"""Orchestration invariants, independent of numerical MATLAB implementation."""
import hashlib
import json
from pathlib import Path

import pytest

from acycle_deepseek import tools


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    root = tmp_path / 'project'
    root.mkdir()
    (root / 'proxy.csv').write_bytes(b'0,1\n1,3\n2,2\n')
    monkeypatch.delenv('ACYCLE_ROOT', raising=False)
    monkeypatch.delenv('ACYCLE_BACKEND', raising=False)
    return root


@pytest.fixture
def matlab_stub(monkeypatch):
    """Stub transport, not science: tests do not invent numerical reference data."""
    requests = []
    def execute(request):
        frozen = Path(request['input_path'])
        requests.append({**request, 'input_bytes': frozen.read_bytes()})
        return {'status': 'completed', 'backend': 'matlab',
                'summary': {'source_rows': 3},
                'artifacts': {'analysis_mat': str(Path(request['output_dir']) / 'analysis.mat')},
                'provenance': {'engine': 'MATLAB', 'source': 'Acycle'}}
    monkeypatch.setattr(tools, '_execute', execute)
    return requests


def analyze(workspace, **kwargs):
    return tools.dispatch('acycle_analyze', {'input_path': 'proxy.csv', **kwargs}, workspace)


def test_analysis_freezes_original_bytes_and_records_matlab_outputs(workspace, matlab_stub):
    original = (workspace / 'proxy.csv').read_bytes()
    result = analyze(workspace, parameters={'span': 0.35}, label='baseline')
    (workspace / 'proxy.csv').write_text('0,999\n')
    assert Path(result['input_path']).read_bytes() == original
    assert result['input_sha256'] == hashlib.sha256(original).hexdigest()
    assert matlab_stub[0]['input_bytes'] == original
    assert matlab_stub[0]['operation'] == 'analyze'
    assert result['status'] == 'completed'
    assert result['provenance']['engine'] == 'MATLAB'
    assert result['artifacts'] == result['result']['artifacts']
    assert tools.dispatch('acycle_get_run', {'run_id': result['run_id']}, workspace) == result


def test_sensitivity_uses_frozen_input_and_preserves_baseline(workspace, matlab_stub):
    baseline = analyze(workspace, parameters={'span': 0.35, 'mtm_nw': 2})
    saved = Path(baseline['input_path']).parent / 'result.json'
    before = saved.read_bytes()
    (workspace / 'proxy.csv').write_text('0,999\n')
    sweep = tools.dispatch('acycle_sensitivity', {
        'run_id': baseline['run_id'], 'parameter': 'span', 'values': [0.2, 0.5]}, workspace)
    assert saved.read_bytes() == before
    assert len({baseline['run_id'], *(r['run_id'] for r in sweep['runs'])}) == 3
    for variant, span in zip(sweep['runs'], [0.2, 0.5]):
        child = tools.dispatch('acycle_get_run', {'run_id': variant['run_id']}, workspace)
        assert child['parent_run_id'] == baseline['run_id']
        assert child['input_sha256'] == baseline['input_sha256']
        assert child['parameters'] == {'span': span, 'mtm_nw': 2}
    assert all(r['input_bytes'] == matlab_stub[0]['input_bytes'] for r in matlab_stub)


def test_compare_reads_existing_results_without_reexecution(workspace, matlab_stub):
    baseline = analyze(workspace, label='baseline')
    branch = analyze(workspace, parameters={'span': 0.5}, parent_run_id=baseline['run_id'])
    count = len(matlab_stub)
    comparison = tools.dispatch('acycle_compare', {'run_ids': [branch['run_id'], baseline['run_id']]}, workspace)
    assert len(matlab_stub) == count
    assert [r['run_id'] for r in comparison['runs']] == [branch['run_id'], baseline['run_id']]
    assert comparison['runs'][0]['parent_run_id'] == baseline['run_id']
    assert comparison['runs'][1]['label'] == 'baseline'


@pytest.mark.parametrize('name,args', [
    ('acycle_unrecognized', {}),
    ('acycle_capabilities', {'shell': 'ignored'}),
    ('acycle_analyze', {'input_path': 'proxy.csv', 'backend': 'python'}),
    ('acycle_analyze', {}),
    ('acycle_get_run', {}),
    ('acycle_inspect', []),
])
def test_bad_tool_arguments_fail_before_execution(workspace, matlab_stub, name, args):
    with pytest.raises(ValueError):
        tools.dispatch(name, args, workspace)
    assert not matlab_stub


@pytest.mark.parametrize('parameters', [{'unknown_algorithm': 'python'}, [], None])
def test_invalid_parameter_object_rejected_before_matlab_dispatch(workspace, matlab_stub, parameters):
    with pytest.raises(ValueError):
        analyze(workspace, parameters=parameters)
    assert not matlab_stub
    assert not (workspace / '.acycle').exists()


@pytest.mark.parametrize('input_form', ['relative', 'absolute', 'symlink'])
def test_input_cannot_escape_workspace(workspace, matlab_stub, input_form):
    outside = workspace.parent / 'outside.csv'
    outside.write_text('0,1\n1,2\n')
    if input_form == 'relative':
        path = '../outside.csv'
    elif input_form == 'absolute':
        path = str(outside)
    else:
        (workspace / 'linked.csv').symlink_to(outside)
        path = 'linked.csv'
    with pytest.raises(ValueError, match='inside workspace'):
        tools.dispatch('acycle_analyze', {'input_path': path}, workspace)
    assert not matlab_stub


def test_acycle_root_allows_official_sample_snapshot(workspace, matlab_stub, monkeypatch):
    upstream = workspace.parent / 'acycle'
    upstream.mkdir()
    sample = upstream / 'official.txt'
    sample.write_text('0 1\n1 2\n')
    monkeypatch.setenv('ACYCLE_ROOT', str(upstream))
    run = tools.dispatch('acycle_analyze', {'input_path': str(sample)}, workspace)
    assert Path(run['input_path']).is_relative_to(workspace)
    assert matlab_stub[0]['acycle_root'] == str(upstream)


@pytest.mark.parametrize('run_id', ['../outside', '/tmp/result', '20261025T000000Z-' + 'a'*12 + '/../x', None, 42])
def test_run_id_cannot_address_arbitrary_files(workspace, run_id):
    with pytest.raises(ValueError, match='Invalid run_id'):
        tools.dispatch('acycle_get_run', {'run_id': run_id}, workspace)


def test_run_storage_cannot_follow_symlink_outside_workspace(workspace, matlab_stub):
    outside = workspace.parent / 'outside-storage'
    outside.mkdir()
    (workspace / '.acycle').symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        analyze(workspace)
    assert not list(outside.iterdir())
    assert not matlab_stub


def test_saved_result_symlink_cannot_expose_external_json(workspace):
    outside = workspace.parent / 'external.json'
    outside.write_text('{"private": true}')
    run_id = '20261025T000000Z-' + 'a' * 12
    run = workspace / '.acycle' / 'runs' / run_id
    run.mkdir(parents=True)
    (run / 'result.json').symlink_to(outside)
    with pytest.raises(ValueError):
        tools.dispatch('acycle_get_run', {'run_id': run_id}, workspace)


@pytest.mark.parametrize('parameter,values', [('unknown', [1]), ('span', []), ('span', [0.2]*13), ('span', '0.3')])
def test_bad_sensitivity_does_not_create_partial_runs(workspace, matlab_stub, parameter, values):
    baseline = analyze(workspace)
    with pytest.raises(ValueError):
        tools.dispatch('acycle_sensitivity', {'run_id': baseline['run_id'],
                       'parameter': parameter, 'values': values}, workspace)
    assert len(matlab_stub) == 1


def test_missing_matlab_fails_visibly_and_keeps_failed_record(workspace, monkeypatch):
    monkeypatch.setenv('MATLAB_EXECUTABLE', str(workspace / 'definitely-no-matlab'))
    with pytest.raises(RuntimeError, match='MATLAB is required'):
        analyze(workspace)
    runs = list((workspace / '.acycle' / 'runs').glob('*/result.json'))
    assert len(runs) == 1
    failed = json.loads(runs[0].read_text())
    assert failed['status'] == 'failed'
    assert 'No Python numerical fallback' in failed['error']
    assert not list(Path(failed['output_dir']).iterdir())
    with pytest.raises(ValueError, match='Baseline must be completed'):
        tools.dispatch('acycle_sensitivity', {'run_id': failed['run_id'],
                       'parameter': 'span', 'values': [0.2]}, workspace)
    assert len(list((workspace / '.acycle' / 'runs').iterdir())) == 1


def test_python_backend_never_silently_replaces_matlab(workspace, monkeypatch):
    monkeypatch.setenv('ACYCLE_BACKEND', 'python')
    with pytest.raises(RuntimeError, match='no Python science fallback'):
        analyze(workspace)
    capabilities = tools.dispatch('acycle_capabilities', {}, workspace)
    assert capabilities['python_numerical_fallback'] is False


def test_matlab_expression_escapes_quoted_paths_without_shell_interpolation(workspace, monkeypatch):
    output = workspace / "results'quoted"
    output.mkdir()
    request = {'input_path': str(workspace / 'proxy.csv'), 'output_dir': str(output),
               'acycle_root': str(workspace), 'parameters': {}}
    monkeypatch.setattr(tools.shutil, 'which', lambda _: '/fake/matlab')
    monkeypatch.setenv('MATLAB_EXECUTABLE', '/fake/matlab')
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        (output / 'response.json').write_text(json.dumps({'status': 'completed'}))
        return type('Completed', (), {'returncode': 0})()
    monkeypatch.setattr(tools.subprocess, 'run', run)
    assert tools._execute(request)['status'] == 'completed'
    command, kwargs = calls[0]
    assert isinstance(command, list) and command[:2] == ['/fake/matlab', '-batch']
    assert "results''quoted" in command[2]
    assert not kwargs.get('shell', False)
