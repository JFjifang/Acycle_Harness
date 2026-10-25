"""Run the MATLAB adapter on GitHub Actions; Python only transports files/JSON.

The Actions credential is supplied to the standard ``gh`` CLI by the runtime.
No DeepSeek credential is sent to GitHub. Scientific results never fall back to
Python when an Actions request fails.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tempfile
import time
import uuid
import zipfile
from typing import Any

MAX_ENCODED_REQUEST = 60000
MAX_INPUT_BYTES = 1024 * 1024
TEXT_INPUT_SUFFIXES = {'.csv', '.txt', '.dat', '.tsv'}


class GitHubBackendError(RuntimeError):
    """A remote request could not be completed or its receipt was invalid."""


def _transient_http_error(message: str) -> bool:
    return re.search(r'HTTP (?:429|502|503|504)\b', message) is not None


def _gh(arguments: list[str], *, payload: dict | None = None, timeout: float = 60) -> str:
    # Only default GET API reads are retried. In particular, a dispatch POST is
    # sent exactly once even if its response is lost or reports a server error.
    mutations = {'--method', '-X', '--input', '--field', '-F', '--raw-field', '-f'}
    read_only = (arguments[:1] == ['api'] and payload is None
                 and not mutations.intersection(arguments))
    attempts = 3 if read_only else 1
    for attempt in range(attempts):
        process = subprocess.run(
            ['gh', *arguments],
            input=None if payload is None else json.dumps(payload),
            capture_output=True, text=True, timeout=timeout, check=False,
        )
        if not process.returncode:
            return process.stdout
        message = _safe_error(process.stderr)
        if attempt + 1 == attempts or not _transient_http_error(message):
            raise GitHubBackendError('GitHub CLI failed: ' + message)
        time.sleep(2**attempt)
    raise AssertionError('unreachable')


def _safe_error(message: str) -> str:
    # gh can include temporary signed artifact URLs in errors. Their query
    # strings are bearer credentials and must never enter tool receipts/logs.
    message = re.sub(r"https?://[^\s\"']+", '[redacted-url]', message)
    return message.strip()[-2000:]


def _download_artifact(repository: str, artifact: dict[str, Any], archive: Path,
                       token: str, remote_run: dict[str, Any]) -> tuple[str, str]:
    cache_value = os.environ.get('ACYCLE_ARTIFACT_CACHE')
    if cache_value:
        # Explicit connector mode: an authorized host service fulfills this
        # request using GitHub's connector and atomically places the ZIP here.
        # No request is sent to the cloud policy-blocked storage destination.
        cache = Path(cache_value).resolve()
        pending_dir = cache / 'pending'
        pending_dir.mkdir(parents=True, exist_ok=True)
        cached = cache / f'{artifact["id"]}.zip'
        pending = pending_dir / f'{token}.json'
        pending_tmp = pending.with_suffix('.tmp')
        pending_tmp.write_text(json.dumps({
            'repo': repository, 'artifact_id': artifact['id'],
            'run_id': remote_run['id'], 'run_url': remote_run['html_url'],
            'token': token, 'destination': str(cached),
        }, indent=2), encoding='utf-8')
        pending_tmp.replace(pending)
        deadline = time.monotonic() + float(os.environ.get('ACYCLE_ARTIFACT_CACHE_TIMEOUT', '300'))
        while not cached.is_file():
            if time.monotonic() >= deadline:
                raise GitHubBackendError(
                    f'Waiting for authorized GitHub connector artifact {artifact["id"]} timed out; '
                    f'fulfill {pending}. MATLAB run already completed; do not rerun the analysis.')
            time.sleep(min(1, max(0, deadline - time.monotonic())))
        if cached.is_symlink():
            raise GitHubBackendError('Connector cache must contain a regular ZIP, not a symlink')
        shutil.copyfile(cached, archive)
        transport = 'github_connector_cache'
    else:
        with archive.open('wb') as stream:
            process = subprocess.run(
                ['gh', 'api', f'repos/{repository}/actions/artifacts/{artifact["id"]}/zip'],
                stdout=stream, stderr=subprocess.PIPE, timeout=120, check=False,
            )
        if process.returncode:
            raise GitHubBackendError('Cannot download MATLAB artifact: ' +
                                     _safe_error(process.stderr.decode(errors='replace')))
        transport = 'gh'
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    expected = artifact.get('digest')
    if expected and expected != 'sha256:' + digest:
        raise GitHubBackendError('Artifact SHA-256 does not match GitHub receipt')
    if cache_value:
        pending.unlink(missing_ok=True)
    return transport, digest


def _validate_artifact_reference(reference: dict[str, Any], repository: str) -> dict[str, Any]:
    """Validate only transport provenance; this does not interpret numeric data."""
    if not isinstance(reference, dict):
        raise ValueError('input_artifact_reference must be an object')
    keys = {'repository', 'artifact_id', 'member', 'input_sha256',
            'artifact_sha256', 'source_workflow_run_id'}
    if not keys <= reference.keys():
        raise ValueError('Artifact reference lacks required provenance')
    source_repository = reference['repository']
    if (not isinstance(source_repository, str)
            or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', source_repository)
            or not isinstance(repository, str)
            or source_repository.lower() != repository.lower()):
        raise ValueError('Input artifact must belong to the configured repository')
    for key in ('artifact_id', 'source_workflow_run_id'):
        if type(reference[key]) is not int or not 0 < reference[key] < 2**63:
            raise ValueError(f'{key} must be a positive integer')
    member = reference['member']
    if not isinstance(member, str) or not member or len(member) > 1024:
        raise ValueError('Invalid artifact member path')
    path = PurePosixPath(member)
    if (path.is_absolute() or '..' in path.parts or '\\' in member or ':' in member
            or not path.parts or path.as_posix() != member or member.endswith('/')
            or path.suffix.lower() not in TEXT_INPUT_SUFFIXES):
        raise ValueError('Artifact member must be a canonical relative text-file path')
    for key in ('input_sha256', 'artifact_sha256'):
        if not isinstance(reference[key], str) or not re.fullmatch(r'[a-f0-9]{64}', reference[key]):
            raise ValueError(f'{key} must be a SHA-256 digest')
    return {key: reference[key] for key in sorted(keys)}


def _payload(request: dict[str, Any], repository: str | None = None) -> str:
    source = Path(request['input_path']).resolve(strict=True)
    if source.suffix.lower() not in TEXT_INPUT_SUFFIXES:
        raise ValueError('GitHub backend accepts CSV/TXT/DAT/TSV inputs only')
    if source.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError('Dataset exceeds GitHub workflow input limit; use local MATLAB')
    parameters = request.get('parameters', {})
    if not isinstance(parameters, dict):
        raise ValueError('parameters must be an object')
    data = source.read_bytes()
    input_sha256 = hashlib.sha256(data).hexdigest()
    body = {
        'input_sha256': input_sha256,
        'input_suffix': source.suffix.lower(),
        'operation': request.get('operation', 'analyze'),
        'parameters': parameters,
    }
    reference = request.get('input_artifact_reference')
    if reference is not None:
        reference = _validate_artifact_reference(
            reference, repository or os.environ.get('ACYCLE_GITHUB_REPO', ''))
        if reference['input_sha256'] != input_sha256:
            raise ValueError('Input artifact reference does not match frozen input bytes')
        if PurePosixPath(reference['member']).suffix.lower() != source.suffix.lower():
            raise ValueError('Input artifact suffix does not match frozen input')
        # Prefer registered exact-byte references even when inline data would
        # fit: chained MATLAB outputs need not be uploaded for every stage.
        body['input_artifact_reference'] = reference
    else:
        body['input_bytes_b64'] = base64.b64encode(gzip.compress(data, mtime=0)).decode('ascii')
        body['input_compression'] = 'gzip'
    encoded = base64.b64encode(json.dumps(body, allow_nan=False).encode()).decode('ascii')
    if len(encoded) > MAX_ENCODED_REQUEST:
        raise ValueError('Request exceeds GitHub workflow input limit; use local MATLAB')
    return encoded


def _extract_safely(archive: Path, destination: Path) -> None:
    """Reject traversal, symlinks, duplicate names and unreasonable archives."""
    with zipfile.ZipFile(archive) as zipped:
        entries = zipped.infolist()
        if len(entries) > 5000 or sum(e.file_size for e in entries) > 512 * 1024 * 1024:
            raise GitHubBackendError('Artifact exceeds extraction limits')
        seen: set[str] = set()
        for entry in entries:
            name = entry.filename
            path = PurePosixPath(name)
            if (path.is_absolute() or '..' in path.parts or '\\' in name
                    or not path.parts or ':' in path.parts[0] or name in seen):
                raise GitHubBackendError('Unsafe or duplicate artifact path')
            seen.add(name)
            mode = entry.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise GitHubBackendError('Artifact symlinks are not supported')
        zipped.extractall(destination)


def _relocate(value: Any, remote: str, local: Path) -> Any:
    if isinstance(value, dict):
        return {key: _relocate(item, remote, local) for key, item in value.items()}
    if isinstance(value, list):
        return [_relocate(item, remote, local) for item in value]
    if isinstance(value, str):
        prefix = remote.rstrip('/') + '/'
        if value == remote:
            return str(local)
        if value.startswith(prefix):
            relative = PurePosixPath(value[len(prefix):])
            if relative.is_absolute() or '..' in relative.parts or '\\' in str(relative):
                raise GitHubBackendError('Unsafe output path in MATLAB response')
            return str(local.joinpath(*relative.parts))
    return value


class GitHubBackend:
    def __init__(self, repository: str | None = None, ref: str | None = None,
                 timeout: float | None = None, poll_interval: float = 10):
        self.repository = repository or os.environ.get('ACYCLE_GITHUB_REPO', '')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', self.repository):
            raise ValueError('Set ACYCLE_GITHUB_REPO to owner/repository')
        self.ref = ref or os.environ.get('ACYCLE_GITHUB_REF', 'main')
        self.timeout = float(timeout or os.environ.get('ACYCLE_GITHUB_TIMEOUT', '1800'))
        self.poll_interval = max(0.01, float(poll_interval))
        self.workflow = 'matlab.yml'

    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        encoded = _payload(request, self.repository)
        output_dir = Path(request['output_dir']).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        token = 'acycle-' + uuid.uuid4().hex
        endpoint = f'repos/{self.repository}/actions/workflows/{self.workflow}'
        request_receipt = output_dir / 'remote-request.json'
        dispatch_receipt = {
            'request_token': token, 'repository': self.repository, 'ref': self.ref,
            'input_sha256': hashlib.sha256(Path(request['input_path']).read_bytes()).hexdigest(),
            'operation': request.get('operation', 'analyze'), 'dispatch_state': 'prepared',
            'input_artifact_reference': request.get('input_artifact_reference'),
        }
        request_receipt.write_text(json.dumps(dispatch_receipt, indent=2), encoding='utf-8')
        dispatch_error = None
        try:
            _gh(['api', '--method', 'POST', endpoint + '/dispatches', '--input', '-'],
                payload={'ref': self.ref, 'inputs': {'token': token, 'request': encoded}})
            dispatch_receipt['dispatch_state'] = 'sent'
        except GitHubBackendError as exc:
            dispatch_receipt['dispatch_error'] = _safe_error(str(exc))
            if not _transient_http_error(str(exc)):
                dispatch_receipt['dispatch_state'] = 'rejected'
                request_receipt.write_text(json.dumps(dispatch_receipt, indent=2), encoding='utf-8')
                raise
            dispatch_error = _safe_error(str(exc))
            dispatch_receipt['dispatch_state'] = 'ambiguous'
        request_receipt.write_text(json.dumps(dispatch_receipt, indent=2), encoding='utf-8')
        deadline = time.monotonic() + self.timeout
        recovery_deadline = min(deadline, time.monotonic() + float(
            os.environ.get('ACYCLE_GITHUB_DISPATCH_RECOVERY_TIMEOUT', '90')))
        remote_run: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            if remote_run is None:
                runs = json.loads(_gh(['api', endpoint + '/runs?event=workflow_dispatch&per_page=100']))
                matching = [r for r in runs['workflow_runs'] if r.get('display_title') == token]
                if len(matching) > 1:
                    raise GitHubBackendError('Ambiguous workflow request token')
                remote_run = matching[0] if matching else None
                if remote_run is not None:
                    dispatch_receipt.update({
                        'dispatch_state': 'observed', 'run_id': remote_run['id'],
                        'run_url': remote_run['html_url'],
                        'recovered_after_ambiguous_response': dispatch_error is not None,
                    })
                    request_receipt.write_text(json.dumps(dispatch_receipt, indent=2), encoding='utf-8')
                elif dispatch_error and time.monotonic() >= recovery_deadline:
                    raise GitHubBackendError(
                        'Dispatch response was ambiguous and no matching run was observed; '
                        f'POST was not repeated. Inspect {request_receipt}. ' + dispatch_error)
            else:
                remote_run = json.loads(_gh(['api', f'repos/{self.repository}/actions/runs/{remote_run["id"]}']))
            if remote_run is not None and remote_run.get('status') == 'completed':
                break
            time.sleep(min(self.poll_interval, max(0, deadline - time.monotonic())))
        else:
            url = remote_run.get('html_url') if remote_run else 'run not yet listed'
            raise GitHubBackendError(f'MATLAB workflow timed out ({url}); it may still be running')
        assert remote_run is not None
        run_id = remote_run['id']
        run_url = remote_run['html_url']
        artifact_listing = json.loads(_gh(['api', f'repos/{self.repository}/actions/runs/{run_id}/artifacts?per_page=100']))
        artifacts = [a for a in artifact_listing['artifacts']
                     if a['name'] == 'acycle-output-' + token and not a.get('expired')]
        if len(artifacts) != 1:
            raise GitHubBackendError(f'MATLAB workflow has no unique output artifact ({remote_run.get("conclusion")}; {run_url})')
        with tempfile.TemporaryDirectory(prefix='acycle-gh-', dir=output_dir.parent) as temp:
            staging = Path(temp)
            archive = staging / 'artifact.zip'
            artifact_transport, artifact_sha256 = _download_artifact(
                self.repository, artifacts[0], archive, token, remote_run)
            extracted = staging / 'files'
            _extract_safely(archive, extracted)
            responses = list(extracted.rglob('response.json'))
            if len(responses) != 1:
                raise GitHubBackendError(f'MATLAB output lacks one response.json ({run_url})')
            root = responses[0].parent
            transport = json.loads((root / 'transport.json').read_text())
            if transport.get('token') != token:
                raise GitHubBackendError('MATLAB output token does not match dispatched request')
            response = json.loads(responses[0].read_text())
            shutil.copytree(root, output_dir, dirs_exist_ok=True)
            response = _relocate(response, transport['remote_output_dir'], output_dir)
            expected_input_sha256 = hashlib.sha256(Path(request['input_path']).read_bytes()).hexdigest()
            if transport.get('input_sha256', expected_input_sha256) != expected_input_sha256:
                raise GitHubBackendError('MATLAB transport input checksum differs from frozen input')
            references = {}
            for key, value in response.get('artifacts', {}).items():
                if not isinstance(value, str):
                    continue
                local_file = Path(value).resolve()
                if (not local_file.is_relative_to(output_dir) or not local_file.is_file()
                        or local_file.suffix.lower() not in TEXT_INPUT_SUFFIXES
                        or local_file.stat().st_size > MAX_INPUT_BYTES):
                    continue
                relative_file = local_file.relative_to(output_dir)
                original_file = root / relative_file
                if not original_file.is_file():
                    continue
                member = original_file.relative_to(extracted).as_posix()
                references[key] = _validate_artifact_reference({
                    'repository': self.repository, 'artifact_id': artifacts[0]['id'],
                    'member': member, 'input_sha256': hashlib.sha256(local_file.read_bytes()).hexdigest(),
                    'artifact_sha256': artifact_sha256, 'source_workflow_run_id': run_id,
                }, self.repository)
            response['artifact_references'] = references
        response['remote_execution'] = {
            'backend': 'github-actions-matlab', 'repository': self.repository,
            'artifact_id': artifacts[0]['id'], 'run_id': run_id, 'run_url': run_url,
            'head_sha': remote_run.get('head_sha'), 'conclusion': remote_run.get('conclusion'),
            'request_token': token, 'acycle_revision': transport.get('acycle_revision'),
            'artifact_transport': artifact_transport, 'artifact_sha256': artifact_sha256,
            'input_transport': transport.get('input_transport', 'inline_gzip'),
            'input_sha256': expected_input_sha256,
            'input_artifact_reference': transport.get('input_artifact_reference'),
            'dispatch_recovered_after_ambiguous_response': dispatch_error is not None,
        }
        (output_dir / 'response.json').write_text(json.dumps(response, indent=2), encoding='utf-8')
        if remote_run.get('conclusion') != 'success':
            raise GitHubBackendError(f'MATLAB workflow failed ({run_url}); inspect {output_dir / "response.json"}')
        return response


def run(request: dict[str, Any]) -> dict[str, Any]:
    """Convenience entry point used by the common backend dispatcher."""
    return GitHubBackend().run(request)
