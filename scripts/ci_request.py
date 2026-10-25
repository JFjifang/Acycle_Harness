"""Decode a bounded workflow request. Only transport/I/O, never scientific math."""
from __future__ import annotations
import base64
import gzip
import hashlib
import io
import json
import os
import re
import stat
import subprocess
from pathlib import Path, PurePosixPath
import tempfile
import time
import zipfile

from acycle_deepseek.github_backend import _gh, _safe_error, _validate_artifact_reference

MAX_INPUT_BYTES = 1024 * 1024
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024


def _fetch_artifact(repository: str, artifact_id: int) -> tuple[dict, bytes]:
    """Read an artifact only from the caller-validated current repository."""
    endpoint = f'repos/{repository}/actions/artifacts/{artifact_id}'
    metadata = json.loads(_gh(['api', endpoint]))
    if (type(metadata.get('size_in_bytes')) is not int
            or not 0 < metadata['size_in_bytes'] <= MAX_ARCHIVE_BYTES):
        raise ValueError('Input artifact archive exceeds transport size limits')
    with tempfile.TemporaryFile() as stream:
        for attempt in range(3):
            stream.seek(0)
            stream.truncate()
            process = subprocess.run(['gh', 'api', endpoint + '/zip'], stdout=stream,
                                     stderr=subprocess.PIPE, timeout=120, check=False)
            error = _safe_error(process.stderr.decode(errors='replace'))
            if not process.returncode:
                break
            if attempt == 2 or not re.search(r'HTTP (?:429|502|503|504)', error):
                raise RuntimeError('Cannot download referenced artifact: ' + error)
            time.sleep(2**attempt)
        stream.seek(0)
        archive = stream.read(MAX_ARCHIVE_BYTES + 1)
    if len(archive) > MAX_ARCHIVE_BYTES:
        raise ValueError('Input artifact archive exceeds transport size limits')
    return metadata, archive


def _reference_bytes(reference: dict, repository: str) -> bytes:
    reference = _validate_artifact_reference(reference, repository)
    # Always use the runner's repository in the API path, never an arbitrary URL.
    metadata, archive = _fetch_artifact(repository, reference['artifact_id'])
    if metadata.get('id') != reference['artifact_id'] or metadata.get('expired') is not False:
        raise ValueError('Input artifact is missing, expired, or has the wrong ID')
    if metadata.get('workflow_run', {}).get('id') != reference['source_workflow_run_id']:
        raise ValueError('Input artifact workflow provenance does not match')
    archive_sha256 = hashlib.sha256(archive).hexdigest()
    if (len(archive) > MAX_ARCHIVE_BYTES or archive_sha256 != reference['artifact_sha256']
            or metadata.get('digest') != 'sha256:' + archive_sha256):
        raise ValueError('Input artifact archive checksum does not match provenance')
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        entries = zipped.infolist()
        if len(entries) > 5000 or sum(e.file_size for e in entries) > MAX_ARCHIVE_BYTES:
            raise ValueError('Input artifact archive exceeds extraction limits')
        seen = set()
        selected = None
        for entry in entries:
            name = entry.filename
            path = PurePosixPath(name)
            canonical = path.as_posix()
            if (path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name
                    or not path.parts or canonical != name.rstrip('/') or canonical in seen
                    or stat.S_ISLNK(entry.external_attr >> 16)):
                raise ValueError('Input artifact contains an unsafe or duplicate member')
            seen.add(canonical)
            if name == reference['member']:
                selected = entry
        if selected is None or selected.is_dir():
            raise ValueError('Referenced input artifact member is missing')
        if selected.file_size > MAX_INPUT_BYTES:
            raise ValueError('Referenced input exceeds 1 MiB limit')
        with zipped.open(selected) as stream:
            data = stream.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES or hashlib.sha256(data).hexdigest() != reference['input_sha256']:
        raise ValueError('Referenced input checksum or size does not match provenance')
    return data


def prepare() -> None:
    token = os.environ.get('ACYCLE_TOKEN', '')
    if not re.fullmatch(r'acycle-[a-f0-9]{32}', token):
        raise ValueError('Invalid remote request token')
    encoded = os.environ['ACYCLE_REQUEST']
    if len(encoded) > 60000:
        raise ValueError('Remote request exceeds 60000-byte encoded limit')
    payload = json.loads(base64.b64decode(encoded, validate=True))
    operation = payload.get('operation', 'analyze')
    if operation not in {'analyze', 'swa', 'coco', 'ecoco', 'interpolate_pro', 'tune'}:
        raise ValueError('Unsupported MATLAB operation')
    parameters = payload.get('parameters', {})
    if not isinstance(parameters, dict):
        raise ValueError('parameters must be an object')
    suffix = payload.get('input_suffix', '.csv').lower()
    if suffix not in {'.csv', '.txt', '.dat', '.tsv'}:
        raise ValueError('Remote inputs must be CSV/TXT/DAT/TSV')
    reference = payload.get('input_artifact_reference')
    if reference is not None:
        if 'input_bytes_b64' in payload or 'input_compression' in payload:
            raise ValueError('Choose exactly one input transport')
        reference = _validate_artifact_reference(reference, os.environ.get('GITHUB_REPOSITORY', ''))
        if PurePosixPath(reference['member']).suffix.lower() != suffix:
            raise ValueError('Referenced input suffix does not match request')
        data = _reference_bytes(reference, os.environ['GITHUB_REPOSITORY'])
        input_transport = 'github_artifact_reference'
    else:
        compressed = base64.b64decode(payload['input_bytes_b64'], validate=True)
        if payload.get('input_compression') != 'gzip':
            raise ValueError('Input compression must be gzip')
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
            data = stream.read(MAX_INPUT_BYTES + 1)
        if len(data) > MAX_INPUT_BYTES:
            raise ValueError('Decompressed input exceeds 1 MiB limit')
        input_transport = 'inline_gzip'
    input_sha256 = hashlib.sha256(data).hexdigest()
    if payload.get('input_sha256', input_sha256) != input_sha256:
        raise ValueError('Input checksum differs from frozen request bytes')
    root = Path.cwd()
    output = root / 'ci-output'
    output.mkdir(exist_ok=True)
    input_path = root / ('ci-input' + suffix)
    input_path.write_bytes(data)
    request = {
        'input_path': str(input_path), 'input_sha256': input_sha256,
        'output_dir': str(output),
        'acycle_root': str(root / 'upstream' / 'acycle'),
        'operation': operation, 'parameters': parameters,
    }
    if reference is not None:
        request['input_artifact_reference'] = reference
    (root / 'ci-request.json').write_text(json.dumps(request), encoding='utf-8')
    (output / 'transport.json').write_text(json.dumps({
        'token': token, 'remote_output_dir': str(output),
        'source_commit': os.environ.get('GITHUB_SHA'),
        'acycle_revision': os.environ.get('ACYCLE_UPSTREAM_REVISION'),
        'input_transport': input_transport, 'input_sha256': input_sha256,
        'input_artifact_reference': reference,
    }), encoding='utf-8')


if __name__ == '__main__':
    prepare()
