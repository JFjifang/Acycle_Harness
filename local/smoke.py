#!/usr/bin/env python3
"""Run a bounded local MATLAB smoke through the public tool dispatcher."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid


def requests(input_path: Path, nsim: int) -> dict:
    shared = {'depth_unit': 'm', 'middle_age_ma': 210,
              'sedimentation_rate_min': 8, 'sedimentation_rate_max': 16,
              'sedimentation_rate_step': 1, 'nsim': nsim, 'seed': 1}
    return {
        'analyze': {'tool': 'acycle_analyze', 'arguments': {'input_path': str(input_path),
                    'parameters': {'detrend': 'lowess', 'span': 0.35, 'evolution': True, 'coordinate_unit': 'm'},
                    'label': 'local Newark mini robot smoke'}},
        'swa': {'tool': 'acycle_swa', 'arguments': {'input_path': str(input_path),
                'parameters': {'method': 'mtm', 'mtm_nw': 2, 'pad_factor': 1, 'detrend': 'mean', 'coordinate_unit': 'm'},
                'label': 'local Newark MTM SWA smoke'}},
        'coco': {'tool': 'acycle_coco', 'arguments': {'input_path': str(input_path),
                 'parameters': dict(shared), 'label': f'local Newark COCO diagnostic nsim={nsim}'}},
        'ecoco': {'tool': 'acycle_ecoco', 'arguments': {'input_path': str(input_path),
                  'parameters': {**shared, 'window': 500, 'step': 500},
                  'label': f'local Newark eCOCO diagnostic nsim={nsim}'}},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', default='.')
    parser.add_argument('--case', choices=['analyze', 'swa', 'coco', 'ecoco', 'all'], default='analyze')
    parser.add_argument('--nsim', type=int, default=19, help='Diagnostic Monte Carlo count; not a publication setting')
    parser.add_argument('--receipt', help='Optional receipt path; otherwise creates a unique file under workspace/local-validation')
    parser.add_argument('--dry-run', action='store_true', help='Print exact requests without launching MATLAB')
    args = parser.parse_args()
    if not 1 <= args.nsim <= 10000:
        parser.error('--nsim must be between 1 and 10000')
    if not os.environ.get('ACYCLE_ROOT'):
        parser.error('Set ACYCLE_ROOT to the validated Acycle checkout')
    workspace = Path(args.workspace).expanduser().resolve()
    source = Path(os.environ['ACYCLE_ROOT']).expanduser().resolve()/'data'/'Examples'/'Example-LateTriassicNewarkDepthRank.txt'
    if not source.is_file():
        parser.error(f'Official Newark fixture not found: {source}')
    tasks = requests(source, args.nsim)
    selected = list(tasks) if args.case == 'all' else [args.case]
    receipt = {'scope': 'Local diagnostic smoke; parameter examples are not a published chronology reproduction',
               'created_at_utc': datetime.now(timezone.utc).isoformat(),
               'input_path': str(source), 'input_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
               'diagnostic_monte_carlo_count': args.nsim,
               'minimum_nominal_mc_resolution': f'1/({args.nsim}+1); read original method output for its exact p-value definition',
               'requests': [tasks[name] for name in selected], 'runs': []}
    if args.dry_run:
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0
    if os.environ.get('ACYCLE_BACKEND', 'local') != 'local':
        parser.error('This smoke is for local MATLAB; set ACYCLE_BACKEND=local')
    from acycle_deepseek.tools import dispatch, tool_schemas
    registered = {entry['function']['name'] for entry in tool_schemas()}
    missing = {tasks[name]['tool'] for name in selected} - registered
    if missing:
        parser.error(f'Installed package lacks {sorted(missing)}; install the matching release wheel')
    destination = Path(args.receipt).expanduser().resolve() if args.receipt else workspace/'local-validation'/(
        datetime.now(timezone.utc).strftime('smoke-%Y%m%dT%H%M%SZ-')+uuid.uuid4().hex[:8]+'.json')
    if destination.exists():
        parser.error(f'Refusing to overwrite receipt: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    failed = False
    for name in selected:
        task = tasks[name]
        try:
            result = dispatch(task['tool'], task['arguments'], workspace)
            if result.get('status') != 'completed' or result.get('result', {}).get('backend') != 'matlab':
                raise RuntimeError('Expected a completed real MATLAB response')
            artifacts = result.get('artifacts', {})
            if not artifacts or not all(Path(path).is_file() for path in artifacts.values()):
                raise RuntimeError('One or more MATLAB artifacts are missing')
            receipt['runs'].append({'case': name, 'status': 'passed', 'result': result})
            print(json.dumps({'case': name, 'run_id': result['run_id'], 'status': 'passed'}, ensure_ascii=False), flush=True)
        except Exception as error:
            failed = True
            receipt['runs'].append({'case': name, 'status': 'failed', 'error': str(error)})
            print(json.dumps({'case': name, 'status': 'failed', 'error': str(error)}, ensure_ascii=False), flush=True)
        receipt['status'] = 'failed' if failed else 'passed'
        destination.write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        if failed:
            break
    print(json.dumps({'receipt': str(destination), 'status': receipt['status']}, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
