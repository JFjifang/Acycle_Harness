"""One JSON request per subprocess; no shell or scientific computation here."""
import json
import sys


def main():
    from .tools import dispatch, tool_schemas, RunError
    request = json.load(sys.stdin)
    if request.get("action") == "schemas":
        result = tool_schemas()
    elif request.get("action") == "call":
        try:
            result = dispatch(request["name"], request.get("arguments", {}), request["workspace"])
        except RunError as error:
            print(json.dumps(error.as_result(), ensure_ascii=False, allow_nan=False), flush=True)
            raise SystemExit(1)
    else:
        raise ValueError("Unknown bridge action")
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
