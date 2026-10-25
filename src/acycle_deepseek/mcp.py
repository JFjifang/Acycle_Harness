"""MCP stdio JSON-RPC adapter using the same MATLAB-only dispatcher."""
import json
import sys

from .artifacts import ArtifactError, list_resources, read_resource, with_artifact_resources
from .tools import RunError

PROTOCOL_VERSION = "2024-11-05"


def handle(message, workspace, *, schemas=None, dispatcher=None):
    if schemas is None or dispatcher is None:
        from .tools import dispatch, tool_schemas
        schemas = schemas if schemas is not None else tool_schemas()
        dispatcher = dispatcher or dispatch
    request_id = message.get("id")
    if "id" not in message:
        return None
    method = message.get("method")
    params = message.get("params") or {}
    if not isinstance(params, dict):
        return {"jsonrpc": "2.0", "id": request_id,
                "error": {"code": -32602, "message": "params must be an object"}}
    if method == "initialize":
        result = {"protocolVersion": PROTOCOL_VERSION,
                  "capabilities": {"tools": {"listChanged": False},
                                   "resources": {"subscribe": False, "listChanged": False}},
                  "serverInfo": {"name": "acycle-matlab", "version": "0.5.1"}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [{"name": t["function"]["name"],
                              "description": t["function"]["description"],
                              "inputSchema": t["function"]["parameters"]} for t in schemas]}
    elif method in {"resources/list", "resources/read"}:
        try:
            if method == "resources/list":
                result = list_resources(workspace, params.get("cursor"))
            else:
                result = read_resource(workspace, params.get("uri"))
        except (ArtifactError, OSError) as exc:
            return {"jsonrpc": "2.0", "id": request_id,
                    "error": {"code": -32002, "message": str(exc)}}
    elif method == "tools/call":
        try:
            name = params["name"]
            if name not in {t["function"]["name"] for t in schemas}:
                raise ValueError("Unknown tool")
            value = with_artifact_resources(dispatcher(name, params.get("arguments", {}), workspace), workspace)
            result = {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False, allow_nan=False)}]}
            if isinstance(value, dict) and (value.get("error") or value.get("status") in {"failed", "error"}):
                result["isError"] = True
        except RunError as exc:
            value = with_artifact_resources(exc.as_result(), workspace)
            result = {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False, allow_nan=False)}],
                      "isError": True}
        except Exception as exc:
            result = {"content": [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}], "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": request_id,
                "error": {"code": -32601, "message": "Method not found"}}
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def serve(workspace):
    for line in sys.stdin:
        try:
            message = json.loads(line)
            if not isinstance(message, dict):
                raise ValueError("Request must be an object")
            response = handle(message, workspace)
        except (ValueError, TypeError) as exc:
            response = {"jsonrpc": "2.0", "id": None,
                        "error": {"code": -32700, "message": "Invalid JSON-RPC request"}}
        if response is not None:
            print(json.dumps(response, ensure_ascii=False, allow_nan=False), flush=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    serve(parser.parse_args().workspace)
