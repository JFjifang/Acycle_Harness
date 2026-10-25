"""Command-line JSON interface shared by users and automation."""
import argparse
import json
import sys
from .tools import dispatch, tool_schemas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', default='.')
    subs = parser.add_subparsers(dest='command', required=True)
    subs.add_parser('tools')
    call = subs.add_parser('call')
    call.add_argument('tool')
    inputs = call.add_mutually_exclusive_group()
    inputs.add_argument('--arguments-json', default='{}')
    inputs.add_argument('--arguments-file')
    args = parser.parse_args()
    try:
        if args.command == 'tools':
            result = tool_schemas()
        else:
            if args.arguments_file:
                with open(args.arguments_file, encoding='utf-8') as f:
                    arguments = json.load(f)
            else:
                arguments = json.loads(args.arguments_json)
            result = dispatch(args.tool, arguments, args.workspace)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    except Exception as exc:
        print(json.dumps({'status':'error','error':str(exc)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == '__main__':
    main()
