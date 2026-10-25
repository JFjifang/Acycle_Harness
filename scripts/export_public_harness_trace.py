#!/usr/bin/env python3
"""Export structural public copies of Harness traces without private reasoning.

Original files are never modified. Text strings are not interpreted, summarized
or searched. Private provider fields and typed reasoning blocks/deltas are removed
structurally; user-visible final text, tool messages and scientific records remain.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


DROP = object()
PRIVATE_FIELDS = {'reasoning', 'reasoning_content', 'reasoning_details', 'reasoning_text',
                  'thinking', 'thinking_content', 'thinking_text', 'thinking_signature'}
PRIVATE_TYPE = re.compile(r'(^|[._/-])(reasoning|thinking)([._/-]|$)', re.I)


def clean(value, counts=None, *, scientific=False, tool_context=False):
    """Transform JSON structure only; never inspect the content of text values."""
    if counts is None:
        counts = Counter()
    if scientific:
        return value
    if isinstance(value, list):
        result = []
        for item in value:
            item = clean(item, counts, tool_context=tool_context)
            if item is not DROP:
                result.append(item)
        return result
    if not isinstance(value, dict):
        return value
    for tag in ('type', 'method'):
        label = value.get(tag)
        if isinstance(label, str) and PRIVATE_TYPE.search(label):
            counts['removed_block:' + label] += 1
            return DROP
    tool_context = tool_context or value.get('role') == 'tool'
    result = {}
    for key, item in value.items():
        if key in PRIVATE_FIELDS:
            counts['removed_field:' + key] += 1
            continue
        # Tool-provided scientific summaries are not model reasoning. Tool text
        # often contains JSON, but it remains an opaque string and is not parsed.
        preserve = key == 'matlab_summary' or (key == 'summary' and tool_context)
        item = clean(item, counts, scientific=preserve,
                     tool_context=tool_context or key in {'tool_results', 'structuredContent'})
        if item is not DROP:
            result[key] = item
    return result


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def export(source, output, patterns, allow_running=False):
    source, output = source.resolve(), output.resolve()
    if output == source or output.is_relative_to(source):
        raise ValueError('Public output must be separate from the original trace directory')
    paths = sorted({path for pattern in patterns for path in source.rglob(pattern)
                    if path.is_file() and path.suffix in {'.json', '.jsonl'}})
    if not paths:
        raise ValueError('No selected JSON or JSONL traces found')
    if not allow_running:
        for path in paths:
            if path.suffix == '.json':
                value = json.loads(path.read_bytes())
                if isinstance(value, dict) and value.get('status') == 'running':
                    raise ValueError(f'Running receipt remains unexported: {path}; wait for completion or select completed files')
    output.mkdir(parents=True, exist_ok=True)
    index = {'schema_version': 1, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
             'source_root': str(source), 'public_root': str(output),
             'scope': 'Public user-visible conversation and tool evidence; private reasoning omitted structurally. Originals untouched.',
             'policy': {'typed_reasoning_blocks_and_deltas_removed': True, 'nested_provider_reasoning_fields_removed': True,
                        'strings_not_interpreted': True, 'scientific_tool_summaries_preserved': True,
                        'model_reasoning_effort_configuration_preserved': True},
             'files': []}
    for path in paths:
        raw = path.read_bytes()
        counts = Counter()
        if path.suffix == '.jsonl':
            lines = []
            for line in raw.splitlines():
                if not line.strip():
                    continue
                value = clean(json.loads(line), counts)
                if value is not DROP:
                    lines.append(json.dumps(value, ensure_ascii=False, separators=(',', ':')))
            public = ('\n'.join(lines) + '\n').encode()
        else:
            value = clean(json.loads(raw), counts)
            if value is DROP:
                value = {'private_reasoning_object_omitted': True}
            public = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
        relative = path.relative_to(source)
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + '.tmp')
        temporary.write_bytes(public)
        temporary.replace(destination)
        index['files'].append({'path': str(relative), 'original_sha256': sha256(raw),
                               'public_sha256': sha256(public), 'original_bytes': len(raw), 'public_bytes': len(public),
                               'structural_removals': dict(sorted(counts.items()))})
    index_path = output / 'public-trace-export-index.json'
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n')
    return index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--include', action='append', default=[], help='Recursive filename glob; repeat to select only completed case files')
    parser.add_argument('--allow-running', action='store_true', help='Explicitly allow provisional public copies; normal releases should wait')
    args = parser.parse_args()
    index = export(args.source, args.output, args.include or ['*.json', '*.jsonl'], args.allow_running)
    print(json.dumps({'files': len(index['files']), 'public_index': str(args.output / 'public-trace-export-index.json'),
                      'original_files_modified': False}))


if __name__ == '__main__':
    main()
