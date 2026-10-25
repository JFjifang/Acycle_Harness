#!/usr/bin/env python3
"""Read-only evaluation of the public Newark demo's actual Harness run lineage.

No spectra, numerical QA, controls, interpolation or plots are recalculated.
Checks use saved MATLAB metadata, original file hashes and official Session events.
Human interpretation and client pixel rendering remain separate evaluations.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from evaluate_harness_conversations import (Evidence, archive_evidence, audit_commands,
                                            digest, load_events, read_json)


ROOT = Path(__file__).resolve().parents[1]
SCIENCE = {'acycle_analyze', 'acycle_swa', 'acycle_coco', 'acycle_ecoco',
           'acycle_interpolate_pro', 'acycle_tune', 'acycle_rerun', 'acycle_sensitivity'}


def status(condition):
    return 'passed' if condition else 'failed'


def values(message):
    for block in message.get('content', []):
        if block.get('type') != 'text':
            continue
        text = block.get('text', '').strip()
        candidates = [text]
        if '{' in text and text.endswith('}'):
            candidates.append(text[text.index('{'):])
        for candidate in candidates:
            try:
                value = json.loads(candidate)
            except ValueError:
                continue
            if isinstance(value, dict):
                yield value
            break


def called_runs(turn):
    science_calls = {call['callId']: call for call in turn.get('tool_calls', []) if call['name'] in SCIENCE}
    runs = {}

    def visit(value):
        if isinstance(value, dict):
            if value.get('run_id') and value.get('status') in {'completed', 'failed'}:
                runs[value['run_id']] = value
            for key in ('run', 'runs', 'result'):
                visit(value.get(key))
        elif isinstance(value, list):
            for child in value:
                visit(child)

    errors = []
    for result in turn.get('tool_results', []):
        message = result.get('message', {})
        call_id = message.get('toolCallId', message.get('callId', message.get('source', {}).get('callId')))
        if call_id not in science_calls:
            continue
        parsed = list(values(message))
        for value in parsed:
            visit(value)
        if message.get('isError') or any(value.get('status') == 'failed' or value.get('error') for value in parsed):
            errors.append({'call': science_calls[call_id], 'structured_results': parsed,
                           'text': '\n'.join(block.get('text', '') for block in message.get('content', []) if block.get('type') == 'text')})
    return list(runs.values()), errors


def check_record(run, first_message_record, evidence):
    artifacts = []
    # These hashes were returned by the live tool at run completion. A later
    # edited result.json cannot replace that historical tool-message witness.
    historic = first_message_record.get('artifact_sha256', {})
    for role, path in run.get('artifacts', {}).items():
        resolved = evidence.path(path)
        observed = digest(resolved) if resolved.is_file() else None
        expected = historic.get(role)
        artifacts.append({'role': role, 'name': Path(path).name, 'source_path': path,
                          'tool_return_sha256': expected, 'observed_sha256': observed,
                          'status': 'unverifiable' if expected is None else status(observed == expected)})
    input_path = evidence.path(run['input_path'])
    remote = run.get('result', {}).get('remote_execution', {})
    return {'run_id': run['run_id'], 'operation': run.get('operation'), 'status': run.get('status'),
            'parent_run_id': run.get('parent_run_id'), 'input_lineage': run.get('input_lineage'),
            'tuning_reference': run.get('tuning_reference'), 'requested_parameters': run.get('parameters'),
            'effective_parameters': run.get('effective_parameters'), 'matlab_summary': run.get('summary'),
            'frozen_input_matches_record': status(input_path.is_file() and digest(input_path) == run.get('input_sha256')),
            'remote_matlab_execution': status(remote.get('backend') == 'github-actions-matlab' and remote.get('conclusion') == 'success'),
            'remote_execution': remote, 'artifacts': artifacts,
            'all_artifact_bytes_preserved': 'passed' if artifacts and all(item['status'] == 'passed' for item in artifacts) else 'failed' if any(item['status'] == 'failed' for item in artifacts) else 'unverifiable',
            'saved_error': run.get('error'), 'saved_matlab_error': run.get('matlab_error'), 'diagnostics': run.get('diagnostics')}


def first_stage_checks(runs, manifest, evidence):
    completed = [run for run in runs if run.get('status') == 'completed']
    presets = manifest['workflow_presets']
    raw_hash = manifest['input']['sha256']

    def find(operation, predicate=lambda run: True):
        return next((run for run in completed if run.get('operation') == operation and predicate(run)), None)

    pro = find('interpolate_pro')
    depth = find('analyze', lambda run: not run.get('tuning_reference') and 'evolution_png' in run.get('artifacts', {}))
    filtering = find('analyze', lambda run: not run.get('tuning_reference') and 'filtered_csv' in run.get('artifacts', {}))
    coco, ecoco, tuning = find('coco'), find('ecoco'), find('tune')
    time_run = find('analyze', lambda run: bool(run.get('tuning_reference')))
    stages = {'interpolate_pro': pro, 'depth_diagnostics': depth, 'depth_filter': filtering,
              'coco': coco, 'ecoco': ecoco, 'tune': tuning, 'time_diagnostics': time_run}
    checks = []

    def check(name, okay, detail=None):
        checks.append({'id': name, 'status': status(okay), **({'detail': detail} if detail is not None else {})})

    roles = {
        'interpolate_pro': ['interpolated_csv', 'diagnostic_png', 'diagnostic_fig', 'analysis_mat'],
        'depth_diagnostics': ['processed_csv', 'spectrum_png', 'robust_spectrum_csv', 'evolution_png', 'evolution_csv', 'analysis_mat'],
        'depth_filter': ['filtered_csv'],
        'coco': ['coco_csv', 'null_max_csv', 'details_json', 'analysis_mat'],
        'ecoco': ['ecoco_csv', 'tracked_rate_csv', 'details_json', 'analysis_mat'],
        'tune': ['age_model_csv', 'control_points_csv', 'tuned_csv', 'diagnostic_png', 'diagnostic_fig', 'analysis_mat'],
        'time_diagnostics': ['processed_csv', 'spectrum_png', 'robust_spectrum_csv', 'evolution_png', 'evolution_csv', 'analysis_mat'],
    }
    expected_presets = {'interpolate_pro': presets['interpolate_pro'], 'depth_diagnostics': presets['depth_diagnostics_and_filter'],
                        'depth_filter': {key: presets['depth_diagnostics_and_filter'][key] for key in ('filter_method', 'filter_band')},
                        'coco': presets['coco'], 'ecoco': presets['ecoco'], 'tune': presets['tune'],
                        'time_diagnostics': presets['time_diagnostics']['parameters']}
    for name, run in stages.items():
        check(name + '_completed', run is not None, run.get('run_id') if run else None)
        if not run:
            continue
        required = list(roles[name])
        if name in {'coco', 'ecoco'}:
            check(name + '_matlab_figure_present', any(key.endswith('_png') and evidence.path(path).is_file() for key, path in run['artifacts'].items()))
        check(name + '_required_saved_products', all(role in run['artifacts'] and evidence.path(run['artifacts'][role]).is_file() for role in required), required)
        expected = expected_presets[name]
        # Acycle may snap a requested evolution step to sampling intervals.
        # Compare the declared request here, and retain actual effective values
        # separately; do not pretend the two are numerically identical.
        if name == 'depth_diagnostics' and filtering and filtering['run_id'] != run['run_id']:
            expected = {key: value for key, value in expected.items() if key not in {'filter_method', 'filter_band'}}
        mismatches = {key: {'declared': value, 'requested': run['parameters'].get(key)} for key, value in expected.items() if run['parameters'].get(key) != value}
        check(name + '_public_preset_requested', not mismatches, mismatches)
    if pro:
        check('pro_consumes_original_raw_bytes', pro['input_sha256'] == raw_hash)
        pro_output = pro.get('artifacts', {}).get('interpolated_csv')
        pro_hash = digest(evidence.path(pro_output)) if pro_output and evidence.path(pro_output).is_file() else None
        for name in ('depth_diagnostics', 'depth_filter', 'coco', 'ecoco'):
            run = stages[name]
            if run:
                check(name + '_uses_this_pro_artifact', run['input_sha256'] == pro_hash and run.get('input_lineage', {}).get('run_id') == pro['run_id'])
    if filtering and tuning:
        filtered_hash = digest(evidence.path(filtering['artifacts']['filtered_csv']))
        check('tune_consumes_actual_filtered_file', tuning['input_sha256'] == filtered_hash and tuning.get('input_lineage', {}).get('run_id') == filtering['run_id'])
    if time_run and tuning:
        controls_hash = digest(evidence.path(tuning['artifacts']['age_model_csv']))
        reference = time_run.get('tuning_reference', {})
        check('time_diagnostic_uses_original_proxy', time_run['input_sha256'] == raw_hash)
        check('time_diagnostic_uses_this_tuning_control_hash', reference.get('run_id') == tuning['run_id'] and reference.get('age_model_sha256') == controls_hash)
        check('time_model_matches_saved_matlab_controls', time_run['parameters'].get('age_model') == tuning['summary'].get('age_model'))
        check('time_trim_matches_saved_valid_range', time_run['parameters'].get('coordinate_range') == tuning['summary'].get('valid_depth_range'))
    selected = {run['run_id'] for run in stages.values() if run}
    return {'stage_run_ids': {key: run['run_id'] if run else None for key, run in stages.items()},
            'checks': checks, 'required_products_and_lineage': status(all(check['status'] == 'passed' for check in checks)),
            'additional_completed_runs_for_review': [run['run_id'] for run in completed if run['run_id'] not in selected]}


def evaluate(receipt, receipt_path, manifest, evidence_root, review):
    evidence = Evidence(receipt, evidence_root)
    turns = receipt.get('turns', [])
    report = {'schema_version': 1, 'generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'receipt': str(receipt_path), 'transport_status': receipt['status'],
              'scope': 'Preset-assisted demo, not blind method selection or published chronology reproduction. No scientific calculations in this evaluator.',
              'session_id': receipt.get('session_id'), 'autonomy_class': receipt.get('autonomy_class'),
              'actual_tool_names': receipt.get('runtime', {}).get('model_visible_tool_names', []),
              'actual_skill_names': receipt.get('runtime', {}).get('model_visible_skill_names', []),
              'turns': [], 'interpretation_review': review or {'status': 'needs_human_review'},
              'client_pixel_rendering': 'not_established_by_headless_SDK; use separate Web live receipt'}
    all_records = {}
    for turn in turns:
        captured, errors = called_runs(turn)
        records = [evidence.record(value['run_id']) or value for value in captured]
        all_records.update({run['run_id']: run for run in records})
        events, session_id = load_events(turn, receipt_path.parent)
        users = [event for event in events if event['type'] == 'user/message' and event['data'].get('source', {}).get('kind') == 'user']
        presentations = [event['data'] for event in events if event['type'] == 'deliverables/presented']
        row = {'index': turn['index'], 'scenario_turn_index': turn.get('scenario_turn_index', turn['index']),
               'user_prompt': turn['user_prompt'], 'same_session': status(session_id == receipt.get('session_id')),
               'independent_user_message_ids': [event['data'].get('id') for event in users],
               'scientific_errors': errors,
               'runs': [check_record(run, captured[index], evidence) for index, run in enumerate(records)],
               'shell_commands_for_review': audit_commands(turn), 'present_events': presentations,
               'original_file_refs': turn.get('emitted_files', []), 'image_refs': turn.get('emitted_images', []),
               'final_response': turn.get('final_response')}
        if row['scenario_turn_index'] == 0:
            row['workflow'] = first_stage_checks(records, manifest, evidence)
        else:
            row['steering'] = []
            for run in records:
                parent = all_records.get(run.get('parent_run_id')) or (evidence.record(run['parent_run_id']) if run.get('parent_run_id') else None)
                if not parent:
                    continue
                prior = parent.get('effective_parameters', parent.get('parameters', {}))
                current = run.get('effective_parameters', run.get('parameters', {}))
                differences = {key: {'before': prior.get(key), 'after': current.get(key)} for key in set(prior) | set(current) if prior.get(key) != current.get(key)}
                row['steering'].append({'run_id': run['run_id'], 'parent_run_id': parent['run_id'],
                                        'operation_preserved': status(run['operation'] == parent['operation']),
                                        'method_preserved': status(current.get('method') == prior.get('method')),
                                        'same_frozen_input': status(run['input_sha256'] == parent['input_sha256']),
                                        'actual_parameter_differences': differences, 'recorded_steering': run.get('steering'),
                                        'effective_or_request_scope': 'effective' if run.get('status') == 'completed' else 'request_only'})
        report['turns'].append(row)
    report['original_attachment_sha256'] = status(receipt['attachment']['sha256'] == manifest['input']['sha256'])
    report['model_visible_catalog'] = {'acycle_tools': len([name for name in report['actual_tool_names'] if name.startswith('acycle_')]),
                                       'acycle_skills': len([name for name in report['actual_skill_names'] if name.startswith('acycle-')]),
                                       'public_demo_skill': 'newark-relative-time-demo' in report['actual_skill_names']}
    report['all_run_ids'] = list(all_records)
    report['no_overall_pass_inferred'] = True
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', required=True, type=Path)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'demo/newark-0.5.0/manifest.json')
    parser.add_argument('--review', type=Path)
    parser.add_argument('--evidence-root', type=Path)
    parser.add_argument('--archive-evidence', type=Path)
    parser.add_argument('--artifact-cache', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    receipt = read_json(args.receipt)
    if args.archive_evidence:
        archive_evidence([receipt], args.archive_evidence, args.artifact_cache)
    report = evaluate(receipt, args.receipt, read_json(args.manifest), args.evidence_root or args.archive_evidence,
                      read_json(args.review) if args.review else None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'transport_status': report['transport_status'], 'run_count': len(report['all_run_ids']),
                      'report': str(args.output)}))


if __name__ == '__main__':
    main()
