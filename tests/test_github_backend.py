"""Remote transport limits and untrusted artifact boundaries."""
import base64
import gzip
import importlib.util
import json
from pathlib import Path
import stat
import zipfile

import pytest

from acycle_deepseek.github_backend import (
    GitHubBackend, GitHubBackendError, _extract_safely, _payload, _relocate,
)


def test_request_roundtrip_and_no_credential_transport(tmp_path, monkeypatch):
    source = tmp_path / 'stratigraphy.csv'
    content = b'depth,proxy\n0,1\n1,0.5\n'
    source.write_bytes(content)
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'private-test-token')
    encoded = _payload({'input_path': str(source), 'parameters': {'span': 0.3}})
    decoded = json.loads(base64.b64decode(encoded))
    assert gzip.decompress(base64.b64decode(decoded['input_bytes_b64'])) == content
    assert decoded['parameters'] == {'span': 0.3}
    assert 'private-test-token' not in json.dumps(decoded)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('ACYCLE_REQUEST', encoded)
    monkeypatch.setenv('ACYCLE_TOKEN', 'acycle-' + 'a' * 32)
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'ci_request.py'
    spec = importlib.util.spec_from_file_location('ci_request', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.prepare()
    request = json.loads((tmp_path / 'ci-request.json').read_text())
    assert Path(request['input_path']).read_bytes() == content
    assert Path(request['output_dir']) == tmp_path / 'ci-output'


@pytest.mark.parametrize('path', ['../escape.txt', '/absolute.txt', 'C:/absolute.txt', 'back\\slash.txt'])
def test_rejects_artifact_path_escape(tmp_path, path):
    archive = tmp_path / 'bad.zip'
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr(path, 'bad')
    with pytest.raises(GitHubBackendError, match='Unsafe'):
        _extract_safely(archive, tmp_path / 'out')
    assert not (tmp_path / 'out').exists()


def test_rejects_artifact_symlink(tmp_path):
    archive = tmp_path / 'symlink.zip'
    entry = zipfile.ZipInfo('outside')
    entry.create_system = 3
    entry.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr(entry, '/etc/passwd')
    with pytest.raises(GitHubBackendError, match='symlinks'):
        _extract_safely(archive, tmp_path / 'out')


def test_relocation_nested_and_path_escape(tmp_path):
    result = {'artifacts': [{'path': '/runner/ci-output/plots/spectrum.png'}], 'backend': 'matlab'}
    local = _relocate(result, '/runner/ci-output', tmp_path)
    assert local['artifacts'][0]['path'] == str(tmp_path / 'plots/spectrum.png')
    assert local['backend'] == 'matlab'
    with pytest.raises(GitHubBackendError, match='Unsafe output'):
        _relocate('/runner/ci-output/../../escape', '/runner/ci-output', tmp_path)


def test_oversized_input_rejected_before_dispatch(tmp_path):
    source = tmp_path / 'large.csv'
    source.write_bytes(b'0' * (1024 * 1024 + 1))
    with pytest.raises(ValueError, match='limit'):
        _payload({'input_path': str(source)})


def test_failure_does_not_fallback_to_local_math(tmp_path, monkeypatch):
    source = tmp_path / 'data.csv'
    source.write_text('0,1\n1,2\n')
    def fail(*args, **kwargs):
        raise GitHubBackendError('permission denied')
    monkeypatch.setattr('acycle_deepseek.github_backend._gh', fail)
    with pytest.raises(GitHubBackendError, match='permission denied'):
        GitHubBackend('owner/repo').run({'input_path': str(source), 'output_dir': str(tmp_path / 'result')})


def test_remote_run_correlated_by_token_and_output_relocated(tmp_path, monkeypatch):
    import io
    from types import SimpleNamespace
    from acycle_deepseek import github_backend as backend
    source = tmp_path / 'data.csv'
    source.write_text('0,1\n1,2\n')
    token = 'acycle-' + 'b' * 32
    monkeypatch.setattr(backend.uuid, 'uuid4', lambda: SimpleNamespace(hex='b' * 32))
    dispatches = []
    requests = []
    def gh(args, **kwargs):
        requests.append(args)
        if 'POST' in args:
            dispatches.append(kwargs['payload'])
            return ''
        if '/runs?' in args[-1]:
            return json.dumps({'workflow_runs': [
                {'id': 99, 'display_title': 'another-user', 'status': 'completed'},
                {'id': 123, 'display_title': token, 'status': 'in_progress', 'html_url': 'https://github.com/owner/repo/actions/runs/123'},
            ]})
        if args[-1].endswith('/runs/123'):
            return json.dumps({'id': 123, 'status': 'completed', 'conclusion': 'success', 'html_url': 'https://github.com/owner/repo/actions/runs/123', 'head_sha': 'abc'})
        if '/runs/123/artifacts?' in args[-1]:
            return json.dumps({'artifacts': [{'id': 456, 'name': 'acycle-output-' + token, 'expired': False}]})
        raise AssertionError(args)
    monkeypatch.setattr(backend, '_gh', gh)
    artifact = io.BytesIO()
    with zipfile.ZipFile(artifact, 'w') as zipped:
        zipped.writestr('ci-output/transport.json', json.dumps({'token': token, 'remote_output_dir': '/runner/ci-output', 'acycle_revision': 'pinned'}))
        zipped.writestr('ci-output/response.json', json.dumps({'status': 'success', 'backend': 'matlab', 'artifacts': {'spectrum': '/runner/ci-output/spectrum.csv'}}))
        zipped.writestr('ci-output/spectrum.csv', 'frequency,power\n0.1,2\n')
    def download(args, **kwargs):
        assert args[-1].endswith('/artifacts/456/zip')
        kwargs['stdout'].write(artifact.getvalue())
        return SimpleNamespace(returncode=0, stderr=b'')
    monkeypatch.setattr(backend.subprocess, 'run', download)
    output = tmp_path / 'output'
    result = GitHubBackend('owner/repo', ref='feature', poll_interval=0.01).run({'input_path': str(source), 'output_dir': str(output)})
    assert dispatches[0]['ref'] == 'feature'
    assert dispatches[0]['inputs']['token'] == token
    assert result['remote_execution']['run_id'] == 123
    assert result['artifacts']['spectrum'] == str(output / 'spectrum.csv')
    assert (output / 'spectrum.csv').exists()
    assert not any('/runs/99' in ' '.join(args) for args in requests)


def test_connector_cache_checks_digest_and_emits_no_signed_urls(tmp_path, monkeypatch):
    import hashlib
    from acycle_deepseek.github_backend import _download_artifact, _safe_error
    cache = tmp_path / 'connector-cache'
    cache.mkdir()
    data = b'archive-content'
    (cache / '42.zip').write_bytes(data)
    monkeypatch.setenv('ACYCLE_ARTIFACT_CACHE', str(cache))
    artifact = {'id': 42, 'digest': 'sha256:' + hashlib.sha256(data).hexdigest()}
    transport, digest = _download_artifact('owner/repo', artifact, tmp_path / 'out.zip', 'acycle-test', {'id': 1, 'html_url': 'https://github.com/owner/repo/actions/runs/1'})
    assert transport == 'github_connector_cache'
    assert digest == hashlib.sha256(data).hexdigest()
    assert not (cache / 'pending' / 'acycle-test.json').exists()
    assert (tmp_path / 'out.zip').read_bytes() == data
    assert _safe_error('Get "https://blob.example/file.zip?sig=secret": Forbidden') == 'Get "[redacted-url]": Forbidden'
    artifact['digest'] = 'sha256:' + '0' * 64
    with pytest.raises(GitHubBackendError, match='SHA-256'):
        _download_artifact('owner/repo', artifact, tmp_path / 'bad.zip', 'acycle-test2', {'id': 1, 'html_url': 'url'})


def test_connector_wait_has_bounded_actionable_failure(tmp_path, monkeypatch):
    from acycle_deepseek.github_backend import _download_artifact
    cache = tmp_path / 'cache'
    monkeypatch.setenv('ACYCLE_ARTIFACT_CACHE', str(cache))
    monkeypatch.setenv('ACYCLE_ARTIFACT_CACHE_TIMEOUT', '0')
    with pytest.raises(GitHubBackendError, match='do not rerun'):
        _download_artifact('owner/repo', {'id': 42}, tmp_path / 'out.zip', 'acycle-test', {'id': 1, 'html_url': 'url'})
    pending = json.loads((cache / 'pending' / 'acycle-test.json').read_text())
    assert pending['repo'] == 'owner/repo'
    assert pending['artifact_id'] == 42
