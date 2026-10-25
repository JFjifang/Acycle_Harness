"""Conversation steering keeps the MATLAB operation, data and parameter meaning."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from acycle_deepseek import tools


COCO = {'depth_unit': 'm', 'middle_age_ma': 200,
        'sedimentation_rate_min': 1, 'sedimentation_rate_max': 20,
        'sedimentation_rate_step': 1}
PERIODS = [405, 125, 95, 53, 39.8, 28, 23.3, 22, 18.7]


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path/'input.csv').write_text('0,1\n1,3\n2,2\n')
    calls = []
    defaults = {}

    def execute(request):
        calls.append(deepcopy(request))
        # Transport fixture only: no scientific values or reference curves.
        return {'status': 'success', 'backend': 'matlab', 'operation': request['operation'],
                'parameters': {**defaults, **request['parameters']},
                'summary': {}, 'artifacts': {}, 'provenance': {}}

    monkeypatch.setattr(tools, '_execute', execute)
    monkeypatch.delenv('ACYCLE_ROOT', raising=False)
    return tmp_path, calls, defaults


def baseline(project, operation, parameters):
    return tools.dispatch('acycle_'+operation,
                          {'input_path': 'input.csv', 'parameters': parameters}, project[0])


def rerun(project, parent, patch):
    return tools.dispatch('acycle_rerun', {'run_id': parent['run_id'],
                          'parameter_patch': patch, 'label': 'User adjustment'}, project[0])


@pytest.mark.parametrize('operation,parameters,patch', [
    ('analyze', {'span': .35, 'mtm_nw': 2}, {'span': .25, 'evolution': False}),
    ('swa', {'method': 'mtm', 'mtm_nw': 2, 'pad_factor': 1}, {'mtm_nw': 3, 'pad_factor': 2}),
    ('coco', {**COCO, 'method': 'adaptive'}, {'nsim': 39, 'red_noise': 1}),
    ('ecoco', {**COCO, 'method': 'blocked', 'window': 100, 'step': 50}, {'window': 120, 'step': 60}),
])
def test_multi_parameter_adjustment_keeps_operation_frozen_data_and_parent(project, operation, parameters, patch):
    root, calls, _ = project
    parent = baseline(project, operation, parameters)
    run_dir = Path(parent['input_path']).parent
    before = {p.name: p.read_bytes() for p in run_dir.iterdir() if p.is_file()}
    (root/'input.csv').write_text('0,999\n')
    child = rerun(project, parent, patch)
    assert calls[-1]['operation'] == operation == child['operation']
    assert child['parameters'] == {**parameters, **patch}
    assert child['input_sha256'] == parent['input_sha256']
    assert Path(child['input_path']).read_bytes() == Path(parent['input_path']).read_bytes()
    assert child['parent_run_id'] == parent['run_id']
    assert child['steering']['parameter_patch'] == patch
    assert child['steering']['operation_preserved'] == operation
    assert child['label'] == 'User adjustment'
    assert before == {p.name: p.read_bytes() for p in run_dir.iterdir() if p.is_file()}
    assert json.loads((Path(child['input_path']).parent/'request.json').read_text())['steering'] == child['steering']


def test_implicit_backend_method_seed_and_other_defaults_are_frozen(project):
    project[2].update(method='blocked', seed=47, nsim=199, correlation='Pearson', detrend='linear')
    parent = baseline(project, 'ecoco', {**COCO, 'window': 100, 'step': 50})
    # A changed backend default must not change unrelated settings on a branch.
    project[2].update(method='adaptive', seed=1, correlation='Spearman')
    child = rerun(project, parent, {'window': 120, 'step': 60})
    assert child['parameters']['method'] == 'blocked'
    assert child['parameters']['seed'] == 47
    assert child['parameters']['correlation'] == 'Pearson'
    assert child['parameters']['nsim'] == 199
    assert 'method' not in child['explicit_parameter_names']


@pytest.mark.parametrize('patch', [
    {'operation': 'analyze'}, {'unknown': 3}, {'method': None}, {'detrend': None},
    {'method': 'mtm'}, {'nsim': 0}, {'nsim': True}, {'seed': '1'}, {'seed': float('nan')},
    {'depth_unit': None}, {'middle_age_ma': 200, 'orbital_periods_kyr': PERIODS},
])
def test_invalid_or_ambiguous_patch_never_starts_another_matlab_job(project, patch):
    parent = baseline(project, 'coco', COCO)
    with pytest.raises(ValueError):
        rerun(project, parent, patch)
    assert len(project[1]) == 1
    assert len(list((project[0]/'.acycle/runs').iterdir())) == 1


def test_explicit_target_and_detrending_window_replacements_are_recorded(project):
    parent = baseline(project, 'coco', {**COCO, 'detrend': 'loess', 'detrend_window': 20})
    child = rerun(project, parent, {'orbital_periods_kyr': PERIODS, 'span': .3})
    assert 'middle_age_ma' not in child['parameters']
    assert 'detrend_window' not in child['parameters']
    assert child['parameters']['orbital_periods_kyr'] == PERIODS
    assert child['parameters']['span'] == .3
    removed = child['steering']['removed_or_reset_parameters']
    assert removed['middle_age_ma']['previous_value'] == 200
    assert removed['detrend_window']['previous_value'] == 20


def test_explicit_linear_detrend_removes_stale_span_without_switching_ecoco(project):
    parent = baseline(project, 'ecoco', {**COCO, 'detrend': 'loess', 'span': .3,
                                      'window': 100, 'step': 50})
    child = rerun(project, parent, {'method': 'blocked', 'detrend': 'linear'})
    assert child['operation'] == 'ecoco'
    assert child['parameters']['method'] == 'blocked'
    assert 'span' not in child['parameters']
    assert child['steering']['removed_or_reset_parameters']['span']['reason'] == 'explicit switch to linear detrending'


def test_held_out_method_change_does_not_silently_remove_nonlinear_preprocessing(project):
    parent = baseline(project, 'ecoco', {**COCO, 'detrend': 'loess', 'span': .3,
                                      'window': 100, 'step': 50})
    with pytest.raises(ValueError, match='held-out'):
        rerun(project, parent, {'method': 'blocked'})
    assert len(project[1]) == 1


def test_swa_explicit_method_change_removes_only_inapplicable_options(project):
    parent = baseline(project, 'swa', {'method': 'mtm', 'mtm_nw': 3, 'pad_factor': 2,
                                     'detrend': 'mean', 'coordinate_unit': 'm'})
    child = rerun(project, parent, {'method': 'lomb'})
    assert child['operation'] == 'swa'
    assert child['parameters'] == {'method': 'lomb', 'coordinate_unit': 'm'}
    assert set(child['steering']['removed_or_reset_parameters']) == {'mtm_nw', 'pad_factor', 'detrend'}
    with pytest.raises(ValueError, match='MTM-only'):
        rerun(project, parent, {'method': 'lomb', 'mtm_nw': 2})
    assert len(project[1]) == 2


def test_dependent_defaults_reset_but_user_choices_stay_fixed_across_generations(project):
    project[2].update(dt=.5, nfft=4096, fmax=1, fit_fmax=1, evolution_step=1)
    parent = baseline(project, 'analyze', {'span': .35, 'fmax': .3})
    first = rerun(project, parent, {'span': .25})
    second = rerun(project, first, {'dt': 1})
    assert second['parameters']['fmax'] == .3  # User-specified, not inferred.
    for key in ('nfft', 'fit_fmax', 'evolution_step'):
        assert key not in project[1][-1]['parameters']
        assert key in second['steering']['removed_or_reset_parameters']
    assert second['parameters']['span'] == .25


def test_coco_target_change_recomputes_only_implicit_frequency_default(project):
    project[2].update(max_frequency=.08, method='adaptive', seed=1)
    parent = baseline(project, 'coco', COCO)
    child = rerun(project, parent, {'middle_age_ma': 300})
    assert 'max_frequency' not in project[1][-1]['parameters']
    assert child['parameters']['seed'] == 1
    assert 'max_frequency' in child['steering']['removed_or_reset_parameters']


def test_restating_unchanged_target_does_not_recalculate_other_defaults(project):
    project[2].update(max_frequency=.08, method='adaptive', seed=1)
    parent = baseline(project, 'coco', COCO)
    project[2]['max_frequency'] = .1
    child = rerun(project, parent, {'middle_age_ma': 200, 'nsim': 19})
    assert child['parameters']['max_frequency'] == .08
    assert child['steering']['removed_or_reset_parameters'] == {}


def test_input_units_are_not_replaced_with_converted_output_units(project):
    parent = baseline(project, 'analyze', {'coordinate_unit': 'm', 'sedimentation_rate': 10, 'depth_unit': 'm'})
    saved = Path(parent['input_path']).parent/'result.json'
    record = json.loads(saved.read_text())
    record['effective_parameters']['coordinate_unit'] = 'kyr'
    saved.write_text(json.dumps(record))
    child = rerun(project, parent, {'span': .25})
    assert child['parameters']['coordinate_unit'] == 'm'
    assert child['parameters']['sedimentation_rate'] == 10


def test_tampered_frozen_input_is_not_accepted_as_same_data(project):
    parent = baseline(project, 'swa', {'method': 'lomb'})
    Path(parent['input_path']).write_text('0,999\n')
    with pytest.raises(ValueError, match='checksum changed'):
        rerun(project, parent, {'fmax': 1})
    assert len(project[1]) == 1


def test_unknown_saved_parameters_require_compatibility_review(project):
    project[2]['future_parameter'] = 1
    parent = baseline(project, 'swa', {'method': 'lomb'})
    with pytest.raises(ValueError, match='version compatibility'):
        rerun(project, parent, {'fmax': 1})
    assert len(project[1]) == 1


def test_sensitivity_preflights_every_patch_and_reuses_method_preserving_branch(project):
    parent = baseline(project, 'ecoco', {**COCO, 'method': 'blocked', 'window': 100, 'step': 50})
    with pytest.raises(ValueError):
        tools.dispatch('acycle_sensitivity', {'run_id': parent['run_id'],
                       'parameter': 'window', 'values': [120, -1]}, project[0])
    assert len(project[1]) == 1
    result = tools.dispatch('acycle_sensitivity', {'run_id': parent['run_id'],
                            'parameter': 'window', 'values': [120, 140]}, project[0])
    for child in result['runs']:
        assert child['operation'] == 'ecoco'
        assert child['parameters']['method'] == 'blocked'
        assert child['parent_run_id'] == parent['run_id']
        assert child['input_sha256'] == parent['input_sha256']
        assert child['steering']['operation_preserved'] == 'ecoco'


def test_patch_schema_disallows_operation_and_null_method():
    spec = next(x['function'] for x in tools.tool_schemas() if x['function']['name'] == 'acycle_rerun')
    patch = spec['parameters']['properties']['parameter_patch']
    assert patch['additionalProperties'] is False
    assert 'operation' not in patch['properties']
    assert {'type': 'null'} not in patch['properties']['method']['anyOf']


@pytest.mark.parametrize('operation,parameters', [
    ('swa', {'method': 'lomb'}), ('coco', COCO),
    ('ecoco', {**COCO, 'window': 100, 'step': 50}),
])
def test_direct_tool_cannot_bypass_operation_preservation_with_parent(project, operation, parameters):
    parent = baseline(project, operation, parameters)
    with pytest.raises(ValueError, match='Parent operation'):
        tools.dispatch('acycle_analyze', {'input_path': 'input.csv', 'parameters': {'span': .25},
                       'parent_run_id': parent['run_id']}, project[0])
    assert len(project[1]) == 1
    # An explicit independent analysis is still available; no false lineage.
    separate = tools.dispatch('acycle_analyze', {'input_path': 'input.csv'}, project[0])
    assert separate['operation'] == 'analyze' and separate['parent_run_id'] is None


def test_direct_partial_request_cannot_reset_saved_ecoco_method(project):
    parameters = {**COCO, 'window': 100, 'step': 50, 'method': 'blocked'}
    parent = baseline(project, 'ecoco', parameters)
    del parameters['method']
    with pytest.raises(ValueError, match='Omitted method'):
        tools.dispatch('acycle_ecoco', {'input_path': 'input.csv', 'parameters': parameters,
                       'parent_run_id': parent['run_id']}, project[0])
    assert len(project[1]) == 1


def test_direct_partial_request_cannot_reset_saved_detrending_method(project):
    parent = baseline(project, 'analyze', {'detrend': 'linear'})
    with pytest.raises(ValueError, match='Omitted detrend'):
        tools.dispatch('acycle_analyze', {'input_path': 'input.csv', 'parameters': {'span': .25},
                       'parent_run_id': parent['run_id']}, project[0])
    assert len(project[1]) == 1
