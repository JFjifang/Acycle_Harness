"""The audit checks metadata/bytes, never reimplements scientific calculations."""
import importlib.util
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('newark_audit', SCRIPTS / 'evaluate_newark_demo.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class LocalEvidence:
    @staticmethod
    def path(value):
        return Path(value)


def fixture_records(tmp_path):
    manifest = audit.read_json(audit.ROOT / 'demo/newark-0.5.0/manifest.json')
    presets = manifest['workflow_presets']
    roles = {
        'pro': ['interpolated_csv', 'diagnostic_png', 'diagnostic_fig', 'analysis_mat'],
        'depth': ['processed_csv', 'spectrum_png', 'robust_spectrum_csv', 'evolution_png', 'evolution_csv', 'analysis_mat', 'filtered_csv'],
        'coco': ['coco_csv', 'null_max_csv', 'details_json', 'analysis_mat', 'coco_figure_1_png'],
        'ecoco': ['ecoco_csv', 'tracked_rate_csv', 'details_json', 'analysis_mat', 'ecoco_figure_1_png'],
        'tune': ['age_model_csv', 'control_points_csv', 'tuned_csv', 'diagnostic_png', 'diagnostic_fig', 'analysis_mat'],
        'time': ['processed_csv', 'spectrum_png', 'robust_spectrum_csv', 'evolution_png', 'evolution_csv', 'analysis_mat'],
    }
    operations = {'pro': 'interpolate_pro', 'depth': 'analyze', 'coco': 'coco', 'ecoco': 'ecoco', 'tune': 'tune', 'time': 'analyze'}
    parameters = {'pro': presets['interpolate_pro'], 'depth': presets['depth_diagnostics_and_filter'],
                  'coco': presets['coco'], 'ecoco': presets['ecoco'], 'tune': presets['tune'],
                  'time': presets['time_diagnostics']['parameters']}
    runs = {}
    for name in roles:
        artifacts = {}
        for role in roles[name]:
            path = tmp_path / (name + '-' + role)
            path.write_text('metadata-test-only: ' + name + '/' + role)
            artifacts[role] = str(path)
        runs[name] = {'run_id': name, 'status': 'completed', 'operation': operations[name],
                      'parameters': dict(parameters[name]), 'artifacts': artifacts}
    raw_hash = manifest['input']['sha256']
    pro_hash = audit.digest(runs['pro']['artifacts']['interpolated_csv'])
    runs['pro']['input_sha256'] = raw_hash
    for name in ('depth', 'coco', 'ecoco'):
        runs[name].update(input_sha256=pro_hash, input_lineage={'run_id': 'pro'})
    runs['tune'].update(input_sha256=audit.digest(runs['depth']['artifacts']['filtered_csv']), input_lineage={'run_id': 'depth'},
                        summary={'age_model': [[0, 0], [1, 405]], 'valid_depth_range': [0, 1]})
    runs['time'].update(input_sha256=raw_hash, tuning_reference={'run_id': 'tune',
                        'age_model_sha256': audit.digest(runs['tune']['artifacts']['age_model_csv'])})
    runs['time']['parameters'].update(age_model=[[0, 0], [1, 405]], coordinate_range=[0, 1])
    return runs, manifest


def test_complete_metadata_chain_requires_each_actual_stage(tmp_path):
    runs, manifest = fixture_records(tmp_path)
    result = audit.first_stage_checks(list(runs.values()), manifest, LocalEvidence())
    assert result['required_products_and_lineage'] == 'passed'
    without_coco = audit.first_stage_checks([run for key, run in runs.items() if key != 'coco'], manifest, LocalEvidence())
    assert without_coco['required_products_and_lineage'] == 'failed'


def test_time_proxy_cannot_be_substituted_with_the_filtered_signal(tmp_path):
    runs, manifest = fixture_records(tmp_path)
    runs['time']['input_sha256'] = audit.digest(runs['depth']['artifacts']['filtered_csv'])
    result = audit.first_stage_checks(list(runs.values()), manifest, LocalEvidence())
    assert next(check for check in result['checks'] if check['id'] == 'time_diagnostic_uses_original_proxy')['status'] == 'failed'


def test_old_retrieval_is_not_a_new_scientific_run_and_structured_failures_remain():
    turn = {'tool_calls': [{'callId': 'old', 'name': 'acycle_get_run'}, {'callId': 'failed', 'name': 'acycle_tune'}],
            'tool_results': [
                {'message': {'toolCallId': 'old', 'content': [{'type': 'text', 'text': '{"status":"completed","run_id":"old"}'}]}},
                {'message': {'toolCallId': 'failed', 'isError': True, 'content': [{'type': 'text', 'text': 'Error: Acycle bridge exited 1: {"status":"failed","run_id":"new","error":"Insufficient extrema"}'}]}},
            ]}
    runs, errors = audit.called_runs(turn)
    assert [run['run_id'] for run in runs] == ['new']
    assert runs[0]['status'] == 'failed'
    assert len(errors) == 1


def test_unreturned_scientific_request_is_not_silently_ignored():
    turn = {'tool_calls': [{'callId': 'read', 'name': 'acycle_get_run'},
                           {'callId': 'first', 'name': 'acycle_tune'},
                           {'callId': 'pending', 'name': 'acycle_tune'}],
            'tool_results': [{'message': {'toolCallId': 'first', 'content': []}}]}
    assert audit.unreturned_scientific_calls(turn) == [{'callId': 'pending', 'name': 'acycle_tune'}]


def test_transport_projection_does_not_pretend_the_original_file_hash_matches(tmp_path):
    runs, manifest = fixture_records(tmp_path)
    source = Path(runs['depth']['artifacts']['filtered_csv'])
    source.write_bytes(b'1,2,9\n3,4,9\n')
    projected = tmp_path / 'projected.csv'
    projected.write_bytes(b'1,2\n3,4\n')
    runs['tune'].update(input_path=str(projected), input_sha256=audit.digest(projected), input_lineage={})
    result = audit.first_stage_checks(list(runs.values()), manifest, LocalEvidence())
    assert result['required_products'] == 'passed'
    assert result['required_products_and_lineage'] == 'failed'
    assert result['transport_projection']['status'] == 'exact_two_column_tokens_preserved'
    assert result['transport_projection']['direct_file_hash_and_automatic_lineage_preserved'] is False


def test_followup_preserves_all_parameters_except_requested_windows(tmp_path):
    import copy
    runs, manifest = fixture_records(tmp_path)
    branch = copy.deepcopy(runs['ecoco'])
    branch.update(run_id='ecoco-followup', parent_run_id='ecoco',
                  steering={'parameter_patch': {'window': 800, 'step': 200}})
    branch['parameters'].update(window=800, step=200)
    witnesses = {branch['run_id']: {'artifact_sha256': {role: audit.digest(path) for role, path in branch['artifacts'].items()}}}
    result = audit.followup_checks(1, [branch], list(runs.values()), manifest, LocalEvidence(), witnesses)
    assert result['status'] == 'passed'
    branch['parameters']['seed'] = 999
    result = audit.followup_checks(1, [branch], list(runs.values()), manifest, LocalEvidence(), witnesses)
    assert result['status'] == 'failed'
    assert next(item for item in result['checks'] if item['id'] == 'only_declared_changes_or_recorded_derived_defaults')['status'] == 'failed'


def test_artifact_integrity_uses_original_live_message_not_mutated_result_record(tmp_path):
    original = tmp_path / 'spectrum.csv'
    original.write_bytes(b'original MATLAB output bytes\n')
    frozen = tmp_path / 'input.csv'
    frozen.write_bytes(b'unchanged input bytes\n')
    witness = {'artifact_sha256': {'spectrum_csv': audit.digest(original)}}
    run = {'run_id': 'run', 'operation': 'analyze', 'status': 'completed',
           'input_path': str(frozen), 'input_sha256': audit.digest(frozen),
           'artifacts': {'spectrum_csv': str(original)}}
    assert audit.check_record(run, witness, LocalEvidence())['all_artifact_bytes_preserved'] == 'passed'
    original.write_bytes(b'changed output after the conversation\n')
    run['artifact_sha256'] = {'spectrum_csv': audit.digest(original)}
    assert audit.check_record(run, witness, LocalEvidence())['all_artifact_bytes_preserved'] == 'failed'
