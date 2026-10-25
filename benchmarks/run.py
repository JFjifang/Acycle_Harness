"""Run selected manifest tasks via the public tool interface and real MATLAB."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

from acycle_deepseek.tools import dispatch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', default='.')
    parser.add_argument('--case', action='append', help='Repeat to select cases; default runs all runnable cases')
    parser.add_argument('--receipt', default='validation/benchmark-runs.json')
    args = parser.parse_args()
    bench = Path(__file__).resolve().parent
    manifest = json.loads((bench / 'manifest.json').read_text())
    cases = [c for c in manifest['cases'] if c.get('runnable')]
    if args.case:
        unknown = set(args.case) - {c['id'] for c in cases}
        if unknown:
            raise SystemExit(f'Unknown or non-runnable cases: {sorted(unknown)}')
        cases = [c for c in cases if c['id'] in args.case]
    workspace = Path(args.workspace).resolve()
    inputs = workspace / 'benchmark-inputs'
    inputs.mkdir(parents=True, exist_ok=True)
    receipt_path = Path(args.receipt)
    if not receipt_path.is_absolute():
        receipt_path = workspace / receipt_path
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt = {'schema_version': 1, 'claim': 'MATLAB workflow execution; paper-data cases are not full reproductions', 'cases': []}
    failed = False
    for case in cases:
        item = {'id': case['id'], 'scope': case['scope']}
        try:
            if case['input']['root'] == 'acycle':
                if not os.environ.get('ACYCLE_ROOT'):
                    raise RuntimeError('Set ACYCLE_ROOT to the pinned upstream checkout for official fixtures')
                source = Path(os.environ['ACYCLE_ROOT']) / case['input']['path']
            else:
                source = bench / case['input']['path']
            data = source.read_bytes()
            actual = hashlib.sha256(data).hexdigest()
            if actual != case['input']['sha256']:
                raise RuntimeError(f'Input checksum mismatch for {case["id"]}')
            target = inputs / (case['id'] + source.suffix)
            shutil.copyfile(source, target)
            result = dispatch('acycle_analyze', {'input_path': str(target),
                              'parameters': case['parameters'], 'label': case['id']}, workspace)
            item.update(status=result['status'], run_id=result['run_id'],
                        input_sha256=actual, provenance=result.get('provenance'),
                        artifacts=result.get('artifacts'), summary=result.get('summary'))
            if result['status'] != 'completed':
                failed = True
        except Exception as error:
            failed = True
            item.update(status='failed', error=str(error))
        receipt['cases'].append(item)
        receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(json.dumps({'id': item['id'], 'status': item['status'], 'run_id': item.get('run_id')}, ensure_ascii=False), flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
