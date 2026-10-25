"""DeepSeek tool orchestration. Every scientific operation goes through MATLAB."""
from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

DEFAULT_MODEL = "deepseek-flash"
SYSTEM_PROMPT = """You are an Acycle cyclostratigraphy research assistant. Use the supplied
Acycle tools to inspect data, perform analysis and preserve reproducible runs. All scientific
computations, spectra, filters, significance, age models and plots MUST run through the
MATLAB/Acycle tools. Never silently replace MATLAB with Python or claim an unexecuted run
succeeded. Python is the interface and may provide genuinely missing functionality, but seek
a MATLAB bridge first. Call acycle_capabilities before analysis. Treat an unavailable MATLAB
backend as a reported limitation. Sensitivity runs must retain a parent run ID and never
replace a baseline. Spectral peaks alone do not prove orbital forcing: pointwise thresholds
are not global significance. Distinguish tested numerical reproduction from full paper
reproduction. Read tool errors, correct supported inputs, and cite returned run IDs and
artifact paths in the final answer. Do not invent parameter names; follow tool schemas."""


class DeepSeekError(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _request(payload: dict | None, *, endpoint: str, timeout: float = 180) -> dict:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise DeepSeekError("DEEPSEEK_API_KEY is not set")
    # Credentials are sent only to the official provider and redirects are rejected.
    url = "https://api.deepseek.com/" + endpoint
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=body, headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json",
    })
    opener = urllib.request.build_opener(
        _NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context())
    )
    try:
        with opener.open(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        # Never copy arbitrary response headers or bodies into logs.
        raise DeepSeekError(f"DeepSeek API returned HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError) as exc:
        raise DeepSeekError(f"DeepSeek API transport failure ({type(exc).__name__})") from None


def list_models() -> dict:
    return _request(None, endpoint="models")


def complete(payload: dict) -> dict:
    return _request(payload, endpoint="chat/completions")


def run_conversation(prompt: str, workspace: str | Path, *, model: str = DEFAULT_MODEL,
                     max_rounds: int = 12, transport: Callable | None = None,
                     schemas: list | None = None, dispatch_fn: Callable | None = None,
                     system_prompt: str = SYSTEM_PROMPT) -> dict:
    """Run bounded native function calls, preserving reasoning/tool message protocol.

    The optional transport and dispatcher are test seams. Production imports the same
    tools as MCP and the Harness plugin; it has no independent numerical implementation.
    """
    if max_rounds < 1:
        raise ValueError("max_rounds must be positive")
    if schemas is None or dispatch_fn is None:
        from .tools import dispatch, tool_schemas
        if schemas is None:
            schemas = tool_schemas()
        if dispatch_fn is None:
            dispatch_fn = dispatch
    send = transport or complete
    allowed = {entry["function"]["name"] for entry in schemas}
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
    calls = []
    usage = []
    returned_models = []
    for step in range(max_rounds):
        response = send({"model": model, "messages": messages, "tools": schemas,
                         "max_tokens": 4096, "stream": False})
        if not response.get("choices"):
            raise DeepSeekError("DeepSeek returned no choices")
        raw = response["choices"][0]["message"]
        assistant = {k: raw[k] for k in ("role", "content", "tool_calls", "reasoning_content") if k in raw}
        assistant["role"] = "assistant"
        messages.append(assistant)
        returned_models.append(response.get("model", model))
        usage.append(response.get("usage", {}))
        tool_calls = assistant.get("tool_calls") or []
        if not tool_calls:
            return {"status": "completed", "requested_model": model, "returned_models": returned_models,
                    "rounds": step + 1, "answer": assistant.get("content", ""),
                    "tool_calls": calls, "messages": messages, "usage": usage}
        # Sequential calls preserve run dependency order and avoid simultaneous MATLAB jobs.
        for call in tool_calls:
            function = call["function"]
            name = function["name"]
            args = None
            try:
                if name not in allowed:
                    raise ValueError("Tool is not in the advertised allowlist")
                args = json.loads(function.get("arguments", "{}"))
                if not isinstance(args, dict):
                    raise ValueError("Tool arguments must be an object")
                value = dispatch_fn(name, args, str(workspace))
                # Fail closed for NaN/Infinity rather than emitting invalid protocol JSON.
                encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
                ok = not (isinstance(value, dict) and (value.get("error") or value.get("status") in {"failed", "error"}))
            except Exception as exc:
                # Adapter errors contain paths/validation diagnostics, never credentials.
                value = {"error": type(exc).__name__, "message": str(exc)}
                key = os.environ.get("DEEPSEEK_API_KEY", "")
                if key:
                    value["message"] = value["message"].replace(key, "[REDACTED]")
                encoded = json.dumps(value, ensure_ascii=False)
                ok = False
            calls.append({"name": name, "arguments": args, "ok": ok, "result": value})
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": encoded})
    return {"status": "round_limit", "requested_model": model, "returned_models": returned_models,
            "rounds": max_rounds, "answer": None, "tool_calls": calls,
            "messages": messages, "usage": usage}
