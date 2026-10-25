"""Decode a bounded workflow request. Only transport/I/O, never scientific math."""
from __future__ import annotations
import base64
import gzip
import io
import json
import os
import re
from pathlib import Path


def prepare() -> None:
    token = os.environ.get('ACYCLE_TOKEN', '')
    if not re.fullmatch(r'acycle-[a-f0-9]{32}', token):
        raise ValueError('Invalid remote request token')
    encoded = os.environ['ACYCLE_REQUEST']
    if len(encoded) > 60000:
        raise ValueError('Remote request exceeds 60000-byte encoded limit')
    payload = json.loads(base64.b64decode(encoded, validate=True))
    operation=payload.get('operation','analyze')
    if operation not in {'analyze','swa','coco','ecoco'}:
        raise ValueError('Unsupported MATLAB operation')
    parameters = payload.get('parameters', {})
    if not isinstance(parameters, dict):
        raise ValueError('parameters must be an object')
    suffix = payload.get('input_suffix', '.csv').lower()
    if suffix not in {'.csv', '.txt', '.dat', '.tsv'}:
        raise ValueError('Remote inputs must be CSV/TXT/DAT/TSV')
    root = Path.cwd()
    output = root / 'ci-output'
    output.mkdir(exist_ok=True)
    input_path = root / ('ci-input' + suffix)
    compressed = base64.b64decode(payload['input_bytes_b64'], validate=True)
    if payload.get('input_compression') != 'gzip':
        raise ValueError('Input compression must be gzip')
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
        data = stream.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise ValueError('Decompressed input exceeds 1 MiB limit')
    input_path.write_bytes(data)
    request = {
        'input_path': str(input_path),
        'output_dir': str(output),
        'acycle_root': str(root / 'upstream' / 'acycle'),
        'operation': operation,
        'parameters': parameters,
    }
    (root / 'ci-request.json').write_text(json.dumps(request), encoding='utf-8')
    (output / 'transport.json').write_text(json.dumps({
        'token': token,
        'remote_output_dir': str(output),
        'source_commit': os.environ.get('GITHUB_SHA'),
        'acycle_revision': os.environ.get('ACYCLE_UPSTREAM_REVISION'),
    }), encoding='utf-8')


if __name__ == '__main__':
    prepare()
