"""Regression witnesses for evaluator false-passes; no scientific computation."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location('newark_integrity_audit', SCRIPTS / 'evaluate_newark_demo.py')
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class LocalEvidence:
    @staticmethod
    def path(value):
        return Path(value)


def recorded_run(tmp_path):
    frozen = tmp_path / 'input.txt'
    frozen.write_bytes(b'original input bytes\n')
    artifacts = {}
    for role in ('spectrum_csv', 'evolution_csv'):
        path = tmp_path / (role + '.csv')
        path.write_bytes(('original artifact ' + role + '\n').encode())
        artifacts[role] = str(path)
    record = {
        'run_id': 'original-run', 'operation': 'analyze', 'status': 'completed',
        'input_path': str(frozen), 'input_sha256': audit.digest(frozen),
        'artifacts': artifacts,
        'artifact_sha256': {role: audit.digest(path) for role, path in artifacts.items()},
    }
    return record, copy.deepcopy(record)


def test_removed_historical_artifact_role_cannot_pass_preservation(tmp_path):
    current, first_tool_witness = recorded_run(tmp_path)
    removed = current['artifacts'].pop('evolution_csv')
    current['artifact_sha256'].pop('evolution_csv')
    Path(removed).unlink()
    checked = audit.check_record(current, first_tool_witness, LocalEvidence())
    assert checked['all_artifact_bytes_preserved'] != 'passed'


def test_changed_frozen_input_and_current_hash_cannot_replace_first_tool_witness(tmp_path):
    current, first_tool_witness = recorded_run(tmp_path)
    frozen = Path(current['input_path'])
    frozen.write_bytes(b'changed after the first live tool return\n')
    current['input_sha256'] = audit.digest(frozen)
    checked = audit.check_record(current, first_tool_witness, LocalEvidence())
    assert checked['frozen_input_matches_record'] != 'passed'


def test_repeated_run_id_retains_first_actual_tool_hash_witness():
    def message(call_id, digest):
        return {'message': {'toolCallId': call_id, 'content': [{
            'type': 'text', 'text': json.dumps({
                'run_id': 'same-run', 'status': 'completed',
                'artifact_sha256': {'spectrum_csv': digest},
            }),
        }]}}
    turn = {
        'tool_calls': [
            {'callId': 'first', 'name': 'acycle_analyze'},
            {'callId': 'later', 'name': 'acycle_sensitivity'},
        ],
        'tool_results': [message('first', 'first-live-hash'), message('later', 'later-reported-hash')],
    }
    records, errors = audit.called_runs(turn)
    assert not errors
    assert len(records) == 1
    assert records[0]['artifact_sha256']['spectrum_csv'] == 'first-live-hash'


def test_followup_parameter_success_is_not_product_success_with_no_artifacts(tmp_path):
    manifest = audit.read_json(audit.ROOT / 'demo/newark-0.5.0/manifest.json')
    parameters = dict(manifest['workflow_presets']['ecoco'])
    source = tmp_path / 'pro-output.csv'
    source.write_bytes(b'exact shared Pro artifact bytes\n')
    pro = {'run_id': 'pro', 'operation': 'interpolate_pro', 'status': 'completed',
           'input_sha256': manifest['input']['sha256'],
           'artifacts': {'interpolated_csv': str(source)},
           'artifact_sha256': {'interpolated_csv': audit.digest(source)}}
    baseline = {
        'run_id': 'baseline-ecoco', 'operation': 'ecoco', 'status': 'completed',
        'input_path': str(source), 'input_sha256': audit.digest(source),
        'input_lineage': {'run_id': 'pro'}, 'parameters': parameters,
        'effective_parameters': dict(parameters),
    }
    branch = copy.deepcopy(baseline)
    branch.update(run_id='followup-ecoco', parent_run_id='baseline-ecoco',
                  steering={'parameter_patch': {'window': 800, 'step': 200}},
                  artifacts={}, artifact_sha256={})
    branch['parameters'].update(window=800, step=200)
    branch['effective_parameters'].update(window=800, step=200)
    checked = audit.followup_checks(1, [branch], [pro, baseline], manifest, LocalEvidence())
    assert checked['status'] != 'passed'
