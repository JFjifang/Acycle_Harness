"""Regression tests for operation routing and steering across MATLAB methods."""
import json
from pathlib import Path
import pytest
from acycle_deepseek import tools


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path/'series.csv').write_text('0,1\n1,2\n2,1\n')
    calls=[]
    def execute(request):
        calls.append(request)
        return {'status':'success','operation':request['operation'],'backend':'matlab',
                'parameters':request['parameters'],'summary':{},'artifacts':{},'provenance':{}}
    monkeypatch.setattr(tools,'_execute',execute)
    return tmp_path,calls


def coco_parameters():
    return {'depth_unit':'m','middle_age_ma':200,'sedimentation_rate_min':1,
            'sedimentation_rate_max':20,'sedimentation_rate_step':1,'nsim':19,'seed':42}


@pytest.mark.parametrize('operation,parameters',[
    ('swa',{'method':'lomb'}),('coco',coco_parameters()),
    ('ecoco',{**coco_parameters(),'window':100,'step':50}),
])
def test_new_tools_route_distinct_matlab_operations(project,operation,parameters):
    root,calls=project
    run=tools.dispatch('acycle_'+operation,{'input_path':'series.csv','parameters':parameters},root)
    assert calls[0]['operation']==operation
    assert calls[0]['parameters']==parameters
    assert run['operation']==operation
    assert run['result']['backend']=='matlab'
    saved=json.loads((Path(run['input_path']).parent/'result.json').read_text())
    assert saved['operation']==operation


def test_ecoco_sensitivity_preserves_method_target_and_seed(project):
    root,calls=project
    params={**coco_parameters(),'window':100,'step':50,'method':'blocked'}
    base=tools.dispatch('acycle_ecoco',{'input_path':'series.csv','parameters':params},root)
    before=(Path(base['input_path']).parent/'result.json').read_bytes()
    sweep=tools.dispatch('acycle_sensitivity',{'run_id':base['run_id'],'parameter':'window','values':[150,200]},root)
    assert all(c['operation']=='ecoco' for c in calls)
    assert [c['parameters']['window'] for c in calls]==[100,150,200]
    assert all(c['parameters']['seed']==42 and c['parameters']['method']=='blocked' for c in calls)
    assert sweep['operation']=='ecoco'
    assert (Path(base['input_path']).parent/'result.json').read_bytes()==before


def test_missing_coco_units_prevents_remote_dispatch(project):
    root,calls=project
    params=coco_parameters();del params['depth_unit']
    with pytest.raises(ValueError,match='Missing MATLAB parameters'):
        tools.dispatch('acycle_coco',{'input_path':'series.csv','parameters':params},root)
    assert calls==[]


def test_swa_cannot_accept_minirobot_span(project):
    root,calls=project
    with pytest.raises(ValueError,match='Unknown MATLAB parameters'):
        tools.dispatch('acycle_swa',{'input_path':'series.csv','parameters':{'span':0.35}},root)
    assert calls==[]


def test_old_runs_without_operation_still_branch_as_analyze(project):
    root,calls=project
    base=tools.dispatch('acycle_analyze',{'input_path':'series.csv'},root)
    record=Path(base['input_path']).parent/'result.json'
    value=json.loads(record.read_text());del value['operation'];record.write_text(json.dumps(value))
    tools.dispatch('acycle_sensitivity',{'run_id':base['run_id'],'parameter':'span','values':[0.25]},root)
    assert calls[-1]['operation']=='analyze'


def test_schemas_expose_explicit_units_and_distinct_target_modes():
    schemas={x['function']['name']:x['function']['parameters'] for x in tools.tool_schemas()}
    assert len(schemas)==12
    for name in ['acycle_coco','acycle_ecoco']:
        assert 'depth_unit' in schemas[name]['properties']['parameters']['required']
    assert schemas['acycle_ecoco']['properties']['parameters']['properties']['orbital_periods_kyr']['minItems']==9
