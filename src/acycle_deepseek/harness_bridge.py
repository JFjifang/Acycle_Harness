"""One JSON request per subprocess; no shell or scientific computation here."""
import json
import sys


def main():
    from .tools import dispatch, tool_schemas
    request = json.load(sys.stdin)
    if request.get("action") == "schemas":
        result = tool_schemas()
    elif request.get("action") == "call":
        result = dispatch(request["name"], request.get("arguments", {}), request["workspace"])
    else:
        raise ValueError("Unknown bridge action")
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
