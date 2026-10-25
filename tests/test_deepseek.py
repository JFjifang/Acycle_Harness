import json
import os
from unittest.mock import patch

from acycle_deepseek.deepseek import run_conversation, DeepSeekError, _request
from acycle_deepseek.mcp import handle

SCHEMAS = [{"type": "function", "function": {"name": "acycle_capabilities", "description": "Capabilities",
             "parameters": {"type": "object", "properties": {}}}}]


def test_tool_protocol_preserves_reasoning_and_result():
    requests = []
    def transport(request):
        requests.append(json.loads(json.dumps(request)))
        if len(requests) == 1:
            return {"model": "deepseek-v4.1-flash", "choices": [{"message": {"role": "assistant", "content": None,
                "reasoning_content": "Need capabilities", "tool_calls": [{"id": "call-1", "type": "function",
                "function": {"name": "acycle_capabilities", "arguments": "{}"}}]}}]}
        assert request["messages"][-2]["reasoning_content"] == "Need capabilities"
        assert request["messages"][-1]["tool_call_id"] == "call-1"
        return {"model": "deepseek-v4.1-flash", "choices": [{"message": {"role": "assistant", "content": "MATLAB available"}}]}
    result = run_conversation("Check", "/tmp", transport=transport, schemas=SCHEMAS,
        dispatch_fn=lambda name, args, ws: {"backend": "matlab"})
    assert result["status"] == "completed"
    assert result["tool_calls"][0]["ok"]
    assert result["returned_models"] == ["deepseek-v4.1-flash"] * 2


def test_unknown_tool_never_executes_and_round_limit_is_explicit():
    def transport(request):
        return {"choices": [{"message": {"tool_calls": [{"id": "bad", "function": {
            "name": "shell", "arguments": "{}"}}]}}]}
    result = run_conversation("Check", "/tmp", transport=transport, schemas=SCHEMAS, max_rounds=1,
        dispatch_fn=lambda *_: (_ for _ in ()).throw(AssertionError("must not run")))
    assert result["status"] == "round_limit"
    assert not result["tool_calls"][0]["ok"]
    assert "allowlist" in result["tool_calls"][0]["result"]["message"]


def test_non_json_tool_args_recover_as_tool_error():
    def transport(request):
        return {"choices": [{"message": {"tool_calls": [{"id": "bad", "function": {
            "name": "acycle_capabilities", "arguments": "not json"}}]}}]}
    result = run_conversation("Check", "/tmp", transport=transport, schemas=SCHEMAS, max_rounds=1,
        dispatch_fn=lambda *_: {})
    assert result["tool_calls"][0]["result"]["error"] == "JSONDecodeError"


def test_missing_credentials_fail_before_network():
    with patch.dict(os.environ, {}, clear=True):
        try:
            _request(None, endpoint="models")
        except DeepSeekError as error:
            assert str(error) == "DEEPSEEK_API_KEY is not set"
        else:
            raise AssertionError("expected missing credential")


def test_mcp_protocol_and_errors():
    kwargs = {"schemas": SCHEMAS, "dispatcher": lambda *_: {"backend": "matlab"}}
    assert handle({"method": "notifications/initialized"}, "/tmp", **kwargs) is None
    result = handle({"id": 1, "method": "tools/list"}, "/tmp", **kwargs)
    assert result["result"]["tools"][0]["inputSchema"]["type"] == "object"
    result = handle({"id": 2, "method": "tools/call", "params": {"name": "unknown"}}, "/tmp", **kwargs)
    assert result["result"]["isError"]
    result = handle({"id": 3, "method": "tools/call", "params": {"name": "acycle_capabilities"}}, "/tmp", **kwargs)
    assert json.loads(result["result"]["content"][0]["text"])["backend"] == "matlab"
