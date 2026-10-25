import importlib.util
import json
from pathlib import Path


path = Path(__file__).resolve().parents[1] / 'scripts/export_public_harness_trace.py'
spec = importlib.util.spec_from_file_location('public_trace_export', path)
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


def test_nested_private_fields_and_stream_blocks_are_removed_without_touching_science():
    scientific = {'input_rows': 2344, 'minimum_rate_global_p': .95,
                  'reasoning': 'Public scientific explanation, not provider reasoning.'}
    fixture = {'runtime': {'reasoningEffort': 'high'}, 'turns': [{
        'tool_results': [{'message': {'role': 'tool', 'summary': scientific,
                                    'content': [{'type': 'text', 'text': '{"summary":{"input_rows":2344}}'}]}}],
        'nested': {'choices': [{'message': {'reasoning_content': 'PRIVATE', 'reasoningContent': 'PRIVATE',
                                            'reasoning_summary': 'PRIVATE', 'thinkingSignature': 'PRIVATE',
                                            'content': 'Visible answer'}}]},
        'events': [{'type': 'assistant/message', 'data': {'message': {'content': [
            {'type': 'reasoning', 'text': 'PRIVATE'}, {'type': 'text', 'text': 'Visible answer'},
            {'type': 'tool-call', 'name': 'acycle_analyze', 'arguments': '{}'}]}}},
                   {'type': 'reasoning-delta', 'text': 'PRIVATE'},
                   {'method': 'response.reasoning_summary.delta', 'text': 'PRIVATE'}],
        'final_response': 'A visible answer that can mention the word reasoning.',
    }]}
    clean = exporter.clean(fixture)
    assert clean['runtime']['reasoningEffort'] == 'high'
    assert clean['turns'][0]['tool_results'][0]['message']['summary'] == scientific
    assert 'reasoning_content' not in clean['turns'][0]['nested']['choices'][0]['message']
    assert clean['turns'][0]['nested']['choices'][0]['message'] == {'content': 'Visible answer'}
    assert [block['type'] for block in clean['turns'][0]['events'][0]['data']['message']['content']] == ['text', 'tool-call']
    assert len(clean['turns'][0]['events']) == 1
    assert clean['turns'][0]['final_response'] == fixture['turns'][0]['final_response']


def test_export_keeps_original_bytes_and_records_both_hashes(tmp_path):
    source, public = tmp_path / 'original', tmp_path / 'public'
    source.mkdir()
    raw = b'{"status":"completed","content":[{"type":"reasoning","text":"PRIVATE"},{"type":"text","text":"Visible"}]}\n'
    (source / 'receipt.json').write_bytes(raw)
    (source / 'events.jsonl').write_bytes(raw)
    index = exporter.export(source, public, ['*.json', '*.jsonl'])
    assert (source / 'receipt.json').read_bytes() == raw
    assert (source / 'events.jsonl').read_bytes() == raw
    for row in index['files']:
        assert row['original_sha256'] == exporter.sha256(raw)
        assert row['public_sha256'] == exporter.sha256((public / row['path']).read_bytes())
        assert row['structural_removals'] == {'removed_block:reasoning': 1}
        assert b'PRIVATE' not in (public / row['path']).read_bytes()
    assert json.loads((public / 'receipt.json').read_text())['content'] == [{'type': 'text', 'text': 'Visible'}]
