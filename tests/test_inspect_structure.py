"""Inspect reports exact file structure without Python scientific statistics."""
import hashlib
import json
from pathlib import Path

import pytest

from acycle_deepseek import tools


FIXTURE = Path(__file__).parent/'fixtures/newark_first8_cr.txt'


def test_original_newark_cr_bytes_are_eight_lines_without_conversion(tmp_path, monkeypatch):
    original = FIXTURE.read_bytes()
    provenance = json.loads(FIXTURE.with_suffix('.provenance.json').read_text())
    assert hashlib.sha256(original).hexdigest() == provenance['fixture_sha256']
    assert original.count(b'\r') == 8 and original.count(b'\n') == 0
    target = tmp_path/'Newark.txt'
    target.write_bytes(original)

    def no_execution(_request):
        pytest.fail('Structural inspection must not start MATLAB or another numerical backend')

    monkeypatch.setattr(tools, '_execute', no_execution)
    result = tools.dispatch('acycle_inspect', {'input_path': 'Newark.txt'}, tmp_path)
    assert result['line_count'] == result['logical_line_count'] == 8
    assert result['newline_style'] == 'CR'
    assert result['newline_counts'] == {'CRLF': 0, 'LF': 0, 'CR': 8}
    assert result['ends_with_newline'] is True
    assert result['matlab_accepts_original_newlines'] is True
    assert len(result['preview']) == 8
    assert result['sha256'] == provenance['fixture_sha256']
    assert target.read_bytes() == original
    assert sorted(p.name for p in tmp_path.iterdir()) == ['Newark.txt']
    assert not {'sample_spacing', 'mean', 'minimum', 'maximum', 'input_rows'} & result.keys()
    assert 'do not convert' in result['note']
    assert 'wc -l' in result['note']


@pytest.mark.parametrize('separator,style,counts', [
    (b'\n', 'LF', {'CRLF': 0, 'LF': 3, 'CR': 0}),
    (b'\r\n', 'CRLF', {'CRLF': 3, 'LF': 0, 'CR': 0}),
    (b'\r', 'CR', {'CRLF': 0, 'LF': 0, 'CR': 3}),
])
def test_universal_text_lines_include_headers_not_validated_sample_counts(tmp_path, separator, style, counts):
    raw = separator.join([b'depth,proxy', b'0,3', b'1,4'])+separator
    (tmp_path/'data.csv').write_bytes(raw)
    result = tools.dispatch('acycle_inspect', {'input_path': 'data.csv'}, tmp_path)
    assert result['logical_line_count'] == 3
    assert result['newline_style'] == style
    assert result['newline_counts'] == counts
    assert result['preview'] == ['depth,proxy', '0,3', '1,4']
    assert 'not validated sample counts' in result['note']


def test_mixed_endings_and_unterminated_last_line_are_structural_only(tmp_path):
    raw = b'header\r\n0,1\r1,2\n2,3'
    (tmp_path/'mixed.csv').write_bytes(raw)
    result = tools.dispatch('acycle_inspect', {'input_path': 'mixed.csv'}, tmp_path)
    assert result['logical_line_count'] == 4
    assert result['newline_style'] == 'mixed'
    assert result['newline_counts'] == {'CRLF': 1, 'LF': 1, 'CR': 1}
    assert result['ends_with_newline'] is False
    assert (tmp_path/'mixed.csv').read_bytes() == raw
