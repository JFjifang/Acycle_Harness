#!/usr/bin/env python3
"""Audit real Harness receipts using JSON, byte hashes and parameter comparisons only.

This does not fit spectra, perform statistics, run MATLAB, call a model, or turn
transport completion into a scientific pass. Interpretation is a separate human
review. Original file attachment IDs provide hashes captured at delivery time;
image-preview IDs must never substitute for original PNG hashes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile


REPO = Path(__file__).resolve().parents[1]
SCIENCE = {'acycle_analyze', 'acycle_swa', 'acycle_coco', 'acycle_ecoco',
           'acycle_rerun', 'acycle_sensitivity'}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def text_blocks(content):
    return '\n'.join(block.get('text', '') for block in content if block.get('type') == 'text')


def parsed_results(turn):
    for result in turn.get('tool_results', []):
        message = result.get('message', {})
        for block in message.get('content', []):
            if block.get('type') != 'text':
                continue
            try:
                value = json.loads(block['text'])
            except (ValueError, KeyError):
                continue
            if isinstance(value, dict):
                yield message, value


def result_runs(turn):
    calls = {call['callId']: call['name'] for call in turn.get('tool_calls', [])}
    found = {}
    for message, value in parsed_results(turn):
        if calls.get(message.get('toolCallId')) not in SCIENCE:
            continue
        if value.get('run_id') and value.get('status') == 'completed':
            found[value['run_id']] = value
    for result in turn.get('tool_results', []):
        message = result.get('message', {})
        if calls.get(message.get('toolCallId')) not in SCIENCE or not message.get('isError'):
            continue
        for run_id in re.findall(r'Run (\d{8}T\d{6}Z-[a-f0-9]+) failed', text_blocks(message.get('content', []))):
            found[run_id] = {'run_id': run_id, 'status': 'failed'}
    return list(found.values())


def load_events(turn, receipts_dir):
    path = receipts_dir / Path(turn.get('events_file', 'missing')).name
    if path.is_file():
        value = read_json(path)
        return value.get('events', []), value.get('sessionId')
    stream = receipts_dir / Path(turn.get('event_log', 'missing')).name
    if stream.is_file():
        events, ids = [], set()
        for line in stream.read_text().splitlines():
            item = json.loads(line)
            if item.get('method') == 'session.event':
                events.append(item['params']['event'])
                if item['params'].get('sessionId'):
                    ids.add(item['params']['sessionId'])
        return events, next(iter(ids)) if len(ids) == 1 else None
    return [], None


def archive_evidence(receipts, root, artifact_cache=None):
    """Copy existing evidence; never replace a different archived byte stream."""
    root.mkdir(parents=True, exist_ok=True)
    index_path = root / 'evidence-index.json'
    index = read_json(index_path) if index_path.exists() else {
        'schema_version': 1, 'purpose': 'Portable copies of existing run records; no scientific recomputation.',
        'cases': {},
    }
    for receipt in receipts:
        case_id = receipt['case_id']
        source = Path(receipt['workspace']) / '.acycle' / 'runs'
        target = root / case_id
        target.mkdir(exist_ok=True)
        files = []
        if source.exists():
            for original in sorted(source.rglob('*')):
                if not original.is_file():
                    continue
                relative = original.relative_to(source)
                copied = target / relative
                copied.parent.mkdir(parents=True, exist_ok=True)
                before = digest(original)
                if copied.exists() and digest(copied) != before:
                    raise ValueError(f'Refusing to overwrite changed archived evidence: {copied}')
                if not copied.exists():
                    shutil.copy2(original, copied)
                files.append({'path': str(relative), 'sha256': before, 'bytes': original.stat().st_size})
            if artifact_cache:
                for record_path in source.glob('*/result.json'):
                    record = read_json(record_path)
                    remote = record.get('result', {}).get('remote_execution', {})
                    token = remote.get('request_token')
                    transfer_path = artifact_cache / 'transfers' / f'{token}.json'
                    if not token or not transfer_path.is_file():
                        continue
                    transfer = read_json(transfer_path)
                    archive = artifact_cache / f"{transfer['artifact_id']}.zip"
                    expected = remote['artifact_sha256']
                    if not archive.is_file() or digest(archive) != expected or transfer.get('github_digest') != 'sha256:' + expected:
                        raise ValueError('Original GitHub ZIP failed its recorded digest check')
                    with zipfile.ZipFile(archive) as zipped:
                        entries = [{'path': name, 'sha256': hashlib.sha256(zipped.read(name)).hexdigest(),
                                    'bytes': zipped.getinfo(name).file_size} for name in zipped.namelist() if not name.endswith('/')]
                    witness = {'source': 'Original GitHub Actions artifact ZIP, uploaded before conversational steering; digest checked against the independent transfer receipt.',
                               'run_id': remote['run_id'], 'artifact_id': transfer['artifact_id'],
                               'artifact_created_at': transfer.get('artifact_created_at'), 'zip_sha256': expected,
                               'github_digest': transfer['github_digest'], 'files': entries}
                    (target / record['run_id'] / 'artifact-original-hashes.json').write_text(json.dumps(witness, indent=2) + '\n')
        uploads = Path(receipt['dsh_home']) / 'llm-deepseek' / 'files-v3.json'
        if uploads.is_file():
            records = read_json(uploads).get('records', [])
            sanitized = [{key: record[key] for key in ('attachmentId', 'variantId', 'bytes', 'createdAt')
                          if key in record} | {'remote_file_id_observed': bool(record.get('fileId'))}
                         for record in records]
            (target / 'image-upload-evidence.json').write_text(json.dumps({
                'source': 'Official provider Files API cache captured after the conversation; scope and remote handles omitted.',
                'records': sanitized,
            }, indent=2) + '\n')
        index['cases'][case_id] = {
            'original_workspace': receipt['workspace'], 'archived_runs': case_id,
            'receipt_status_at_archival': receipt.get('status'),
            'original_run_files': files,
            'hash_time': 'At archival; historical baseline hashes are separately preserved in first-turn file attachment refs.',
        }
    index['updated_at_utc'] = datetime.now(timezone.utc).isoformat()
    index_path.write_text(json.dumps(index, indent=2) + '\n')


class Evidence:
    def __init__(self, receipt, root, live_files=False):
        self.receipt = receipt
        self.root = root
        self.live_files = live_files
        self.row = None
        if root:
            index = read_json(root / 'evidence-index.json')
            self.row = index['cases'].get(receipt['case_id'])

    def path(self, original):
        path = Path(original)
        prefix = Path(self.receipt['workspace']) / '.acycle' / 'runs'
        if self.root and self.row and path.is_relative_to(prefix) and (not self.live_files or path.name == 'artifact-original-hashes.json'):
            return self.root / self.row['archived_runs'] / path.relative_to(prefix)
        return path

    def record(self, run_id):
        original = Path(self.receipt['workspace']) / '.acycle' / 'runs' / run_id / 'result.json'
        path = self.path(original)
        return read_json(path) if path.is_file() else None

    def upload_records(self):
        if self.root and self.row:
            path = self.root / self.row['archived_runs'] / 'image-upload-evidence.json'
        else:
            path = Path(self.receipt['dsh_home']) / 'llm-deepseek' / 'files-v3.json'
        return read_json(path).get('records', []) if path.is_file() else []


def state(condition):
    return 'passed' if condition else 'failed'


def original_file_checks(run, turn, evidence):
    """Compare current originals with historical file refs emitted in this turn."""
    refs = {block['attachment']['name']: block['attachment'] for block in turn.get('emitted_files', [])}
    witness_path = evidence.path(Path(run['output_dir']).parent / 'artifact-original-hashes.json')
    witness = read_json(witness_path) if witness_path.is_file() else None
    checks = []
    for role, original in run.get('artifacts', {}).items():
        if not isinstance(original, str):
            continue
        expected = refs.get(f"{run['run_id']}-{Path(original).name}")
        path = evidence.path(original)
        observed = digest(path) if path.is_file() else None
        expected_hash = expected.get('attachmentId', '').removeprefix('sha256:') if expected else None
        expected_bytes = expected.get('bytes') if expected else None
        source = 'first-turn original file attachment' if expected else None
        if not expected and witness:
            matches = [item for item in witness['files'] if Path(item['path']).name == Path(original).name]
            if len(matches) == 1:
                expected_hash, expected_bytes = matches[0]['sha256'], matches[0]['bytes']
                source = 'independently verified original GitHub artifact ZIP'
        checks.append({'role': role, 'file': Path(original).name,
                       'delivery_time_sha256': expected_hash, 'observed_sha256': observed,
                       'historical_hash_source': source,
                       'status': 'unverifiable' if not expected_hash else state(observed == expected_hash and path.stat().st_size == expected_bytes)})
    return checks


def audit_commands(turn):
    rows = []
    for call in turn.get('tool_calls', []):
        if call['name'] != 'bash':
            continue
        try:
            command = json.loads(call['arguments']).get('command', '')
        except (ValueError, TypeError):
            command = str(call.get('arguments'))
        if re.search(r'\bgh\s+auth\b|\benv\b|printenv|DEEPSEEK_API_KEY|GH_TOKEN', command):
            classification = 'credential_or_backend_debugging'
        elif re.search(r'\bpython\d?\b|\bawk\b|\bnumpy\b|\bscipy\b|\bstatistics\b', command):
            classification = 'requires_manual_review_for_numerical_processing'
        elif re.search(r'\b(head|tail|cat|sha256sum|ls|wc|cmp|diff)\b', command):
            classification = 'read_or_byte_metadata_only'
        else:
            classification = 'requires_manual_review'
        rows.append({'classification': classification, 'command': command, 'call_id': call['callId']})
    return rows


def evaluate(receipt, scenario, receipts_dir, root, review, live_files=False):
    evidence = Evidence(receipt, root, live_files)
    checks = []
    report = {'case_id': receipt['case_id'], 'transport_status': receipt['status'],
              'session_id': receipt.get('session_id'), 'checks': checks, 'turns': [],
              'interpretation': review or {'status': 'needs_review', 'note': 'Not inferred by this metadata-only evaluator.'}}
    turns = receipt.get('turns', [])
    expected_hash = scenario['attachment']['sha256']
    checks.append({'id': 'declared_original_attachment_sha256', 'status': state(receipt['attachment']['sha256'] == expected_hash),
                   'expected': expected_hash, 'observed': receipt['attachment']['sha256']})
    all_users, all_runs, commands, errors = [], [], [], []
    for turn in turns:
        events, session_id = load_events(turn, receipts_dir)
        users = [event for event in events if event['type'] == 'user/message' and event['data'].get('source', {}).get('kind') == 'user']
        all_users.extend(users)
        present = [event for event in events if event['type'] == 'deliverables/presented']
        run_values = result_runs(turn)
        records = [evidence.record(value['run_id']) or value for value in run_values]
        all_runs.extend(records)
        errors.extend(result for result in turn.get('tool_results', []) if result.get('message', {}).get('isError'))
        command_rows = audit_commands(turn)
        commands.extend(command_rows)
        number = turn.get('scenario_turn_index', turn['index'])
        wanted = scenario['turns'][number]['acceptance']
        row = {'index': turn['index'], 'scenario_turn_index': number, 'tool_names': [call['name'] for call in turn.get('tool_calls', [])],
               'session_identity': state(session_id == receipt.get('session_id')),
               'actual_user_message_ids': [user['data']['id'] for user in users],
               'runs': [], 'shell_commands': command_rows,
               'presented_files': [file for event in present for file in event['data'].get('files', [])]}
        if users:
            row['user_prompt_matches_recorded_input'] = state(any(text_blocks(user['data']['content']) == turn['user_prompt'] for user in users))
        unique_images = {block['attachment']['attachmentId'] for block in turn.get('emitted_images', [])}
        original_refs = {block['attachment']['attachmentId'] for block in turn.get('emitted_files', [])}
        row['image_reference_count'] = len(unique_images)
        row['file_reference_count'] = len(original_refs)
        row['image_delivery'] = state(len(unique_images) >= wanted.get('minimum_delivered_images', 0))
        row['present_event'] = 'not_required' if wanted.get('no_new_images_required') else state(bool(present))
        if records and all(run.get('status') == 'failed' for run in records) and not unique_images:
            row['image_delivery'] = 'not_produced_due_to_scientific_error'
            row['present_event'] = 'not_produced_due_to_scientific_error'
        if not scenario.get('stop_after_expected_clarification'):
            row['required_operation'] = state(any(run.get('operation') == wanted.get('required_completed_operation') and run.get('status') == 'completed' for run in records))
        for run in records:
            params = run.get('effective_parameters', run.get('parameters', {}))
            expected = wanted.get('required_effective_parameters', {})
            remote = run.get('result', {}).get('remote_execution', {})
            input_path = evidence.path(run['input_path'])
            files = original_file_checks(run, turn, evidence)
            row['runs'].append({'run_id': run['run_id'], 'operation': run.get('operation'), 'status': run.get('status'),
                                'effective_parameters': params if run.get('status') == 'completed' else None,
                                'requested_parameters': run.get('parameters'),
                                'required_parameters': state(all(params.get(k) == v for k, v in expected.items())) if run.get('status') == 'completed' else 'not_established_execution_failed',
                                'allowed_method': state(not wanted.get('allowed_methods') or params.get('method') in wanted['allowed_methods']),
                                'frozen_input_sha256': digest(input_path) if input_path.is_file() else None,
                                'original_input_preserved': state(input_path.is_file() and digest(input_path) == expected_hash == run.get('input_sha256')),
                                'remote_matlab_execution': state(remote.get('backend') == 'github-actions-matlab' and remote.get('conclusion') == 'success'),
                                'remote_execution': remote, 'delivered_original_files': files,
                                'all_delivered_original_hashes_match': ('failed' if any(file['status'] == 'failed' for file in files) else 'unverifiable' if not files or any(file['status'] == 'unverifiable' for file in files) else 'passed')})
        report['turns'].append(row)
    user_ids = [user['data']['id'] for user in all_users]
    report['separate_user_turns_same_session'] = {
        'status': state(len(set(user_ids)) == len(turns) == len(user_ids) and len(turns) >= len(scenario['turns'])
                        and all(turn['session_identity'] == 'passed' for turn in report['turns'])),
        'actual_user_messages': len(user_ids), 'planned_user_messages': len(scenario['turns']),
        'source_filter': "user/message where source.kind == 'user'; skill/runtime messages excluded",
    }
    if not scenario.get('stop_after_expected_clarification'):
        report['requested_scientific_goal'] = {
            'status': state(len(turns) >= len(scenario['turns']) and all(row.get('required_operation') == 'passed' and row['image_delivery'] == 'passed' for row in report['turns'])),
            'note': 'A failed MATLAB branch may preserve method/parameters and be handled honestly while leaving the requested two-result goal incomplete.',
        }
    first_files = [block['attachment'] for event in all_users[:1] for block in event['data']['content'] if block.get('type') == 'file']
    report['uploaded_file_message'] = {'status': state(any(ref.get('attachmentId') == 'sha256:' + expected_hash and ref.get('name') == scenario['attachment']['name'] for ref in first_files))}
    report['tool_errors'] = {'count': len(errors), 'status': 'recovered_errors_observed' if errors else 'none',
                             'messages': [text_blocks(item['message'].get('content', []))[:1000] for item in errors]}
    imported = [value for turn in turns for _, value in parsed_results(turn) if value.get('status') == 'imported']
    report['attachment_import'] = {
        'status': state(any(value.get('sha256') == expected_hash and value.get('source_session_id') == receipt.get('session_id') for value in imported)) if imported else 'not_observed',
        'note': 'Successful acycle_import_attachment receipts only. Reading an existing official attachment file is not treated as a copied import.',
    }
    report['matlab_only_tool_behavior'] = {
        'status': review.get('behavior_status') if review and review.get('behavior_status') else ('needs_review' if any(row['classification'] != 'read_or_byte_metadata_only' for row in commands) else 'passed'),
        'note': 'Shell classifiers only flag review candidates; they do not infer semantic correctness from command names.',
    }
    report['prior_test_artifact_access'] = {
        'status': 'observed' if any('/validation/' in row['command'] for row in commands) else 'not_observed',
        'note': 'The runner never injects acceptance or prior outcomes, but a model may inspect accessible repository files. Such access limits a claim of fully blinded interpretation.',
    }
    if scenario.get('stop_after_expected_clarification'):
        scientific_calls = [call for turn in turns for call in turn.get('tool_calls', []) if call['name'] in SCIENCE]
        report['no_premature_scientific_computation'] = {'status': state(not scientific_calls), 'calls': scientific_calls}
        report['required_clarification'] = {'status': review.get('clarification_status', 'needs_review') if review else 'needs_review',
                                           'note': 'Missing coordinate units, age/target and justified search range must be checked in the actual response.'}
    if len(all_runs) >= 2:
        baseline, branch = all_runs[0], all_runs[-1]
        before = baseline.get('effective_parameters', baseline.get('parameters', {}))
        after = branch.get('effective_parameters', branch.get('parameters', {}))
        changed = {key: {'before': before.get(key), 'after': after.get(key)} for key in set(before) | set(after) if before.get(key) != after.get(key)}
        wanted = scenario['turns'][-1]['acceptance']
        allowed = set(wanted.get('allowed_explicit_parameter_changes', []))
        reset = branch.get('steering', {}).get('removed_or_reset_parameters', {})
        for key in reset:
            if key == 'nfft' and key not in baseline.get('explicit_parameter_names', []) and 'window' in allowed:
                allowed.add(key)
        report['steering'] = {'scope': 'effective completed MATLAB parameters' if branch.get('status') == 'completed' else 'requested branch parameters only; final MATLAB execution failed',
                              'parent_preserved': state(branch.get('parent_run_id') == baseline['run_id']),
                              'operation_preserved': state(branch.get('operation') == baseline.get('operation')),
                              'method_preserved': state(after.get('method') == before.get('method')),
                              'same_frozen_input': state(branch.get('input_sha256') == baseline.get('input_sha256') == expected_hash),
                              'only_permitted_parameter_changes': state(set(changed) <= allowed), 'actual_changes': changed,
                              'recorded_steering': branch.get('steering')}
        baseline_row = next(row for row in report['turns'] if row['runs'])
        report['baseline_unchanged'] = {'status': baseline_row['runs'][0]['all_delivered_original_hashes_match'],
                                       'evidence': 'Original file attachment hashes captured in the first turn, with original GitHub artifact ZIP hashes where an original .dat was not attached, compared with current/archived bytes. Preview image hashes and post-hoc filesystem snapshots are excluded.'}
        numeric = []
        for role in wanted.get('unchanged_numeric_artifacts', []):
            if role not in branch.get('artifacts', {}):
                numeric.append({'role': role, 'status': 'not_established_execution_failed'})
                continue
            left = evidence.path(baseline['artifacts'][role])
            right = evidence.path(branch['artifacts'][role])
            numeric.append({'role': role, 'baseline_sha256': digest(left), 'branch_sha256': digest(right),
                            'status': state(left.read_bytes() == right.read_bytes())})
        if numeric:
            report['full_spectrum_bytes_unchanged'] = numeric
    uploads = evidence.upload_records()
    unoffloaded = {block['attachment']['attachmentId'] for turn in turns for block in turn.get('emitted_images', []) if not block.get('offloaded')}
    uploaded = {row['attachmentId'] for row in uploads if row.get('fileId') or row.get('remote_file_id_observed')}
    report['model_image_transport'] = {
        'status': 'image_upload_observed' if unoffloaded & uploaded else 'not_established',
        'unoffloaded_image_ids': sorted(unoffloaded), 'uploaded_matching_ids': sorted(unoffloaded & uploaded),
        'note': 'Official read_image outputs and provider Files API cache establish image transport, not correctness of visual interpretation or desktop UI rendering.',
    }
    report['overall'] = 'dimension_results_only; transport_completed_does_not_mean_all_passed'
    return report


def markdown_report(report):
    lines = ['# Harness conversation evidence review', '',
             'This review reads JSON, compares parameters and verifies file bytes. It performs no scientific recomputation. Each dimension is reported separately; successful transport is not an overall scientific pass.', '']
    for case in report['cases']:
        lines += [f"## {case['case_id']}", '',
                  f"Transport: **{case['transport_status']}**. Separate user turns in one Session: **{case['separate_user_turns_same_session']['status']}**. Original uploaded SHA: **{case['checks'][0]['status']}**.", '',
                  f"Tool errors: {case['tool_errors']['count']}; MATLAB-only tool behavior: **{case['matlab_only_tool_behavior']['status']}**.", '']
        for turn in case['turns']:
            lines.append(f"- User turn {turn['index'] + 1}: operations {[run['operation'] for run in turn['runs']]}; {turn['image_reference_count']} distinct image refs, {turn['file_reference_count']} distinct original file refs; present event {turn['present_event']}.")
        if 'steering' in case:
            lines += ['', f"Steering checks: `{json.dumps({key: value for key, value in case['steering'].items() if isinstance(value, str)}, ensure_ascii=False)}`.",
                      f"Baseline bytes unchanged: **{case['baseline_unchanged']['status']}**, proved against the first-turn original file attachment hashes."]
        if 'no_premature_scientific_computation' in case:
            lines += ['', f"No premature scientific computation: **{case['no_premature_scientific_computation']['status']}**; required clarification: **{case['required_clarification']['status']}**."]
        if case.get('full_spectrum_bytes_unchanged'):
            lines += ['', f"Full spectrum CSV byte comparison: **{case['full_spectrum_bytes_unchanged'][0]['status']}**."]
        lines += ['', f"Model image transport: **{case['model_image_transport']['status']}**. Desktop UI rendering was not tested.", '',
                  f"Interpretation review: **{case['interpretation'].get('status', 'needs_review')}**.", '']
        lines.extend('- ' + finding for finding in case['interpretation'].get('findings', []))
        lines.append('')
    lines += ['Prior attempts remain preserved and are not replaced by this iteration. See the JSON report for individual hashes, run IDs, parameter deltas, tool errors and evidence paths.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipts', type=Path, default=REPO / 'validation/v0.4/harness/iteration2')
    parser.add_argument('--scenarios', type=Path, default=REPO / 'tests/fixtures/conversation_scenarios.json')
    parser.add_argument('--review', type=Path, help='Separate human interpretation-review JSON keyed by case ID')
    parser.add_argument('--evidence-root', type=Path, help='Portable archive with evidence-index.json; takes precedence over live paths')
    parser.add_argument('--live-files', action='store_true', help='Compare live workspace files against the same historical witnesses, for checking archive parity')
    parser.add_argument('--archive-evidence', type=Path, help='Copy existing run records, including failed runs, to this portable evidence root before evaluation')
    parser.add_argument('--artifact-cache', type=Path, help='Optional verified GitHub ZIP cache and transfers directory, used when archiving historical hash witnesses')
    parser.add_argument('--output', type=Path, default=REPO / 'validation/v0.4/conversation-evaluation.json')
    parser.add_argument('--markdown', type=Path, default=REPO / 'validation/v0.4/conversation-evaluation.md')
    args = parser.parse_args()
    scenarios = {case['id']: case for case in read_json(args.scenarios)['cases']}
    receipts = [read_json(path) for path in sorted(args.receipts.glob('*.json')) if '.turn-' not in path.name]
    receipts = [receipt for receipt in receipts if receipt.get('case_id') in scenarios]
    if args.archive_evidence:
        archive_evidence(receipts, args.archive_evidence, args.artifact_cache)
    evidence_root = args.evidence_root or args.archive_evidence
    reviews = read_json(args.review) if args.review else {}
    report = {'schema_version': 1, 'generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'scope': 'Official Harness conversations; metadata and byte-integrity audit plus separate human interpretation review.',
              'receipts_directory': str(args.receipts), 'evidence_root': str(evidence_root) if evidence_root else None,
              'file_resolution': 'live' if args.live_files else 'archive_preferred',
              'cases': [evaluate(receipt, scenarios[receipt['case_id']], args.receipts, evidence_root, reviews.get(receipt['case_id']), args.live_files) for receipt in receipts]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown_report(report))
    print(json.dumps({'cases': len(report['cases']), 'report': str(args.output), 'markdown': str(args.markdown)}))


if __name__ == '__main__':
    main()
