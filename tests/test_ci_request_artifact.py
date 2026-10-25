"""Exact-byte reuse and access boundaries for remote MATLAB artifact inputs."""
from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import warnings
import zipfile

import pytest


@pytest.fixture
def ci_request():
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'ci_request.py'
    spec = importlib.util.spec_from_file_location('ci_request_artifact_test', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def archive_fixture(data=b'0,1,2\n1,2,3\n', *, member='ci-output/filtered.csv', extras=()):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member, data)
        for name, content in extras:
            archive.writestr(name, content)
    zipped = stream.getvalue()
    digest = hashlib.sha256(zipped).hexdigest()
    reference = {
        'repository': 'owner/repository', 'artifact_id': 43,
        'member': member, 'input_sha256': hashlib.sha256(data).hexdigest(),
        'artifact_sha256': digest, 'source_workflow_run_id': 42,
    }
    metadata = {'id': 43, 'expired': False, 'digest': 'sha256:' + digest,
                'size_in_bytes': len(zipped), 'workflow_run': {'id': 42}}
    return reference, metadata, zipped


def serve_archive(monkeypatch, ci_request, metadata, zipped):
    requests = []
    def fetch(repository, artifact_id):
        requests.append((repository, artifact_id))
        return copy.deepcopy(metadata), zipped
    monkeypatch.setattr(ci_request, '_fetch_artifact', fetch)
    return requests


def test_reuses_exact_large_three_column_artifact_without_projection(ci_request, monkeypatch):
    data = b''.join(f'{i},{i / 7:.16f},{i / 11:.16f}\n'.encode() for i in range(3200))
    assert len(data) > 100000
    reference, metadata, zipped = archive_fixture(data)
    requests = serve_archive(monkeypatch, ci_request, metadata, zipped)
    assert ci_request._reference_bytes(reference, 'owner/repository') == data
    assert requests == [('owner/repository', 43)]


@pytest.mark.parametrize('change', [
    {'repository': 'other/private'}, {'artifact_id': True}, {'artifact_id': 0},
    {'artifact_id': '43'}, {'source_workflow_run_id': False},
    {'source_workflow_run_id': -1}, {'input_sha256': 'invalid'},
    {'artifact_sha256': 'invalid'}, {'member': '../filtered.csv'},
    {'member': '/filtered.csv'}, {'member': 'ci-output/../filtered.csv'},
    {'member': 'ci-output//filtered.csv'}, {'member': './ci-output/filtered.csv'},
    {'member': 'ci-output\\filtered.csv'}, {'member': 'C:/filtered.csv'},
])
def test_rejects_bad_reference_before_network(ci_request, monkeypatch, change):
    reference, _, _ = archive_fixture()
    reference.update(change)
    def denied(*args, **kwargs):
        pytest.fail('Invalid artifact reference reached GitHub')
    monkeypatch.setattr(ci_request, '_fetch_artifact', denied)
    with pytest.raises(ValueError):
        ci_request._reference_bytes(reference, 'owner/repository')


@pytest.mark.parametrize('missing', [
    'repository', 'artifact_id', 'member', 'input_sha256',
    'artifact_sha256', 'source_workflow_run_id',
])
def test_reference_requires_complete_source_provenance(ci_request, monkeypatch, missing):
    reference, _, _ = archive_fixture()
    reference.pop(missing)
    def denied(*args, **kwargs):
        pytest.fail('Incomplete artifact reference reached GitHub')
    monkeypatch.setattr(ci_request, '_fetch_artifact', denied)
    with pytest.raises(ValueError):
        ci_request._reference_bytes(reference, 'owner/repository')


@pytest.mark.parametrize('change', [
    {'id': 999}, {'expired': True}, {'workflow_run': {'id': 999}},
    {'workflow_run': {}}, {'digest': 'sha256:' + '0' * 64},
])
def test_rejects_mismatched_github_artifact_receipt(ci_request, monkeypatch, change):
    reference, metadata, zipped = archive_fixture()
    metadata.update(change)
    serve_archive(monkeypatch, ci_request, metadata, zipped)
    with pytest.raises(ValueError):
        ci_request._reference_bytes(reference, 'owner/repository')


@pytest.mark.parametrize('field', ['artifact_sha256', 'input_sha256'])
def test_rejects_changed_archive_or_member_bytes(ci_request, monkeypatch, field):
    reference, metadata, zipped = archive_fixture()
    reference[field] = '0' * 64
    serve_archive(monkeypatch, ci_request, metadata, zipped)
    with pytest.raises(ValueError):
        ci_request._reference_bytes(reference, 'owner/repository')


def test_rejects_missing_member(ci_request, monkeypatch):
    reference, metadata, zipped = archive_fixture()
    reference['member'] = 'ci-output/missing.csv'
    serve_archive(monkeypatch, ci_request, metadata, zipped)
    with pytest.raises(ValueError):
        ci_request._reference_bytes(reference, 'owner/repository')


def test_rejects_symlink_member(ci_request, monkeypatch):
    member = zipfile.ZipInfo('ci-output/filtered.csv')
    member.create_system = 3
    member.external_attr = (stat.S_IFLNK | 0o777) << 16
    reference, metadata, zipped = archive_fixture(member=member)
    reference['member'] = member.filename
    serve_archive(monkeypatch, ci_request, metadata, zipped)
    with pytest.raises(ValueError):
        ci_request._reference_bytes(reference, 'owner/repository')


def test_rejects_duplicate_member(ci_request, monkeypatch):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        reference, metadata, zipped = archive_fixture(extras=[('ci-output/filtered.csv', b'0,1,2\n1,2,3\n')])
    serve_archive(monkeypatch, ci_request, metadata, zipped)
    with pytest.raises(ValueError):
        ci_request._reference_bytes(reference, 'owner/repository')


def test_rejects_oversized_decompressed_member(ci_request, monkeypatch):
    reference, metadata, zipped = archive_fixture(b'0' * (1024 * 1024 + 1))
    serve_archive(monkeypatch, ci_request, metadata, zipped)
    with pytest.raises(ValueError):
        ci_request._reference_bytes(reference, 'owner/repository')


def test_prepare_preserves_input_checksum_reference_and_three_columns(ci_request, monkeypatch, tmp_path):
    data = b'depth,filtered,envelope\r\n0,1.125,2.25\r\n1,3.5,4.75\r\n'
    reference, metadata, zipped = archive_fixture(data)
    serve_archive(monkeypatch, ci_request, metadata, zipped)
    payload = {'input_artifact_reference': reference, 'input_sha256': reference['input_sha256'],
               'input_suffix': '.csv', 'operation': 'tune',
               'parameters': {'extrema': 'peaks'}}
    monkeypatch.setenv('GITHUB_REPOSITORY', 'owner/repository')
    monkeypatch.setenv('ACYCLE_TOKEN', 'acycle-' + 'a' * 32)
    monkeypatch.setenv('ACYCLE_REQUEST', base64.b64encode(json.dumps(payload).encode()).decode())
    monkeypatch.chdir(tmp_path)
    ci_request.prepare()
    request = json.loads((tmp_path / 'ci-request.json').read_text())
    assert Path(request['input_path']).read_bytes() == data
    assert request['input_sha256'] == reference['input_sha256']
    assert request['input_artifact_reference'] == reference
    assert request['operation'] == 'tune'
    assert request['parameters'] == {'extrema': 'peaks'}
    transport = json.loads((tmp_path / 'ci-output' / 'transport.json').read_text())
    assert transport['input_transport'] == 'github_artifact_reference'
    assert transport['input_sha256'] == reference['input_sha256']
    assert transport['input_artifact_reference'] == reference


@pytest.mark.parametrize('change', [
    {'input_bytes_b64': 'unused-inline-bytes', 'input_compression': 'gzip'},
    {'input_sha256': '0' * 64},
])
def test_prepare_rejects_ambiguous_transport_or_input_checksum(ci_request, monkeypatch, tmp_path, change):
    reference, metadata, zipped = archive_fixture()
    serve_archive(monkeypatch, ci_request, metadata, zipped)
    payload = {'input_artifact_reference': reference, 'input_sha256': reference['input_sha256'],
               'input_suffix': '.csv', 'operation': 'analyze', 'parameters': {}}
    payload.update(change)
    monkeypatch.setenv('GITHUB_REPOSITORY', 'owner/repository')
    monkeypatch.setenv('ACYCLE_TOKEN', 'acycle-' + 'a' * 32)
    monkeypatch.setenv('ACYCLE_REQUEST', base64.b64encode(json.dumps(payload).encode()).decode())
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        ci_request.prepare()
    assert not (tmp_path / 'ci-input.csv').exists()
