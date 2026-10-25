#!/usr/bin/env python3
"""Opt-in real-provider smoke for the SWA, COCO and eCOCO MATLAB tools.

Set DEEPSEEK_API_KEY in the launching process. This script never stores a key
and never substitutes numerical Python calculations or canned tool results.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from acycle_deepseek.deepseek import run_conversation
from acycle_deepseek.tools import dispatch, tool_schemas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', default='.')
    parser.add_argument('--swa-input', default='benchmarks/data/weedon_2020_lavernock_0_13_17m.csv')
    parser.add_argument('--newark-input', required=True)
    parser.add_argument('--output', default='validation/deepseek-v03-live.json')
    parser.add_argument('--model', default='deepseek-flash')
    parser.add_argument('--max-rounds', type=int, default=10)
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    output = Path(args.output)
    if not output.is_absolute():
        output = workspace/output
    output.parent.mkdir(parents=True, exist_ok=True)
    requests = [
        {'tool': 'acycle_swa', 'arguments': {'input_path': args.swa_input,
         'parameters': {'method': 'lomb', 'coordinate_unit': 'm'},
         'label': 'DeepSeek v0.3 Lavernock SWA tool smoke'}},
        {'tool': 'acycle_coco', 'arguments': {'input_path': args.newark_input,
         'parameters': {'depth_unit': 'm', 'middle_age_ma': 210,
                        'sedimentation_rate_min': 8, 'sedimentation_rate_max': 16,
                        'sedimentation_rate_step': 1, 'nsim': 19, 'seed': 1,
                        'method': 'adaptive'},
         'label': 'DeepSeek v0.3 Newark COCO diagnostic smoke'}},
        {'tool': 'acycle_ecoco', 'arguments': {'input_path': args.newark_input,
         'parameters': {'depth_unit': 'm', 'middle_age_ma': 210,
                        'sedimentation_rate_min': 8, 'sedimentation_rate_max': 16,
                        'sedimentation_rate_step': 1, 'nsim': 19, 'seed': 1,
                        'window': 500, 'step': 500, 'method': 'adaptive'},
         'label': 'DeepSeek v0.3 Newark eCOCO diagnostic smoke'}},
    ]
    prompt = (
        'Run this bounded tool integration smoke. First call acycle_capabilities and '
        'inspect both input files. Then execute each of the following three exact '
        'requests once, in order. Do not change the parameters and do not repeat '
        'failed computations. After success, call acycle_get_run on the eCOCO run. '
        'The GitHub backend runs MATLAB remotely; absent local MATLAB does not '
        'mean that backend is unavailable. All computations and figures must be '
        'from the MATLAB tools. Finally state the three run IDs, original-source '
        'provenance, output paths and limitations. The 19 Monte Carlo draws are '
        'diagnostics only; these parameter examples do not reproduce a published '
        'Newark chronology. Do not claim any paper feature has been reproduced '
        'unless the returned evidence explicitly establishes it. Use MATLAB '
        'summary.input_rows for raw counts and do not confuse structural line '
        'counts with processed samples. Requests:\n' + json.dumps(requests)
    )
    events = []

    def observed_dispatch(name, arguments, target_workspace):
        print(json.dumps({'event': 'tool_started', 'name': name}), flush=True)
        try:
            value = dispatch(name, arguments, target_workspace)
            events.append({'name': name, 'arguments': arguments, 'ok': True, 'result': value})
            output.write_text(json.dumps({'status': 'running', 'events': events},
                              ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
            print(json.dumps({'event': 'tool_completed', 'name': name,
                              'run_id': value.get('run_id') if isinstance(value, dict) else None}), flush=True)
            return value
        except Exception as error:
            # The common transport sanitizes signed URLs; no environment is logged.
            events.append({'name': name, 'arguments': arguments, 'ok': False,
                           'error': type(error).__name__, 'message': str(error)})
            output.write_text(json.dumps({'status': 'running', 'events': events},
                              ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
            print(json.dumps({'event': 'tool_failed', 'name': name,
                              'error': type(error).__name__}), flush=True)
            raise

    result = run_conversation(prompt, workspace, model=args.model,
                              max_rounds=args.max_rounds, dispatch_fn=observed_dispatch)
    required = {'acycle_capabilities', 'acycle_inspect', 'acycle_swa',
                'acycle_coco', 'acycle_ecoco', 'acycle_get_run'}
    successful = {call['name'] for call in result['tool_calls'] if call['ok']}
    scientific = [call for call in result['tool_calls']
                  if call['name'] in {'acycle_swa', 'acycle_coco', 'acycle_ecoco'}]
    science_valid = len(scientific) == 3 and all(
        call['ok'] and call['result'].get('status') == 'completed'
        and call['result'].get('result', {}).get('backend') == 'matlab'
        and call['result'].get('operation') == call['name'].removeprefix('acycle_')
        and call['result'].get('artifacts')
        and all(Path(path).is_file() for path in call['result']['artifacts'].values())
        for call in scientific)
    result['acceptance'] = {
        'scope': 'Real DeepSeek API plus shared dispatcher and original MATLAB tools; not a full Harness desktop UI or publication-significance test.',
        'advertised_tools': len(tool_schemas()),
        'required_tools': sorted(required),
        'missing_successful_tools': sorted(required-successful),
        'three_real_matlab_operations_and_files': bool(science_valid),
        'passed': result['status'] == 'completed' and required <= successful and bool(science_valid),
    }
    result['requested_smoke_tasks'] = requests
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'acceptance': result['acceptance'],
                      'returned_models': result['returned_models'], 'receipt': str(output)}), flush=True)
    return 0 if result['acceptance']['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
