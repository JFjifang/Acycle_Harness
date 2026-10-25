"""Registered-file transport and MCP protocol checks, with no science backend."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from acycle_deepseek import artifacts
from acycle_deepseek.mcp import handle
from acycle_deepseek.tools import RunError


RUN = "20261025T000000Z-aaaaaaaaaaaa"
OTHER = "20261025T000000Z-bbbbbbbbbbbb"
SCHEMAS = [{"type": "function", "function": {
    "name": "acycle_get_run", "description": "Read saved run",
    "parameters": {"type": "object", "properties": {"run_id": {"type": "string"}}},
}}]


def make_run(workspace, run_id=RUN, *, files=None, status="completed"):
    files = files or {"table": ("table.csv", b"coordinate,value\r0,1\r1,2\r"),
                      "figure": ("figure.png", b"\x89PNG\r\n\x1a\nfixture bytes")}
    run = workspace / ".acycle" / "runs" / run_id
    output = run / "outputs"
    output.mkdir(parents=True)
    record = {"run_id": run_id, "status": status, "operation": "analyze",
              "artifacts": {}, "artifact_sha256": {}, "output_dir": str(output)}
    for key, (filename, content) in files.items():
        path = output / filename
        path.write_bytes(content)
        record["artifacts"][key] = str(path)
        record["artifact_sha256"][key] = hashlib.sha256(content).hexdigest()
    save_record(workspace, record)
    return record


def save_record(workspace, record):
    target = workspace / ".acycle" / "runs" / record["run_id"] / "result.json"
    target.write_text(json.dumps(record), encoding="utf-8")


def uri(key, run_id=RUN):
    return f"acycle://runs/{run_id}/{key}"


def rpc(workspace, method, params=None, dispatcher=None):
    return handle({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}, workspace,
                  schemas=SCHEMAS, dispatcher=dispatcher or (lambda *_: {}))


def test_initialize_advertises_resources_without_subscription(tmp_path):
    response = rpc(tmp_path, "initialize")["result"]
    assert response["capabilities"]["resources"] == {"subscribe": False, "listChanged": False}
    assert response["serverInfo"]["version"] == "0.5.0"
    assert rpc(tmp_path, "resources/list")["result"] == {"resources": []}


def test_list_and_read_exact_registered_text_and_binary_bytes(tmp_path):
    record = make_run(tmp_path)
    output = Path(record["output_dir"])
    (output / "unregistered-secret.csv").write_text("not registered")
    resources = rpc(tmp_path, "resources/list")["result"]["resources"]
    assert {r["uri"] for r in resources} == {uri("table"), uri("figure")}
    for item in resources:
        key = item["_meta"]["artifact_key"]
        content = Path(record["artifacts"][key]).read_bytes()
        assert item["size"] == len(content)
        assert item["_meta"]["sha256"] == hashlib.sha256(content).hexdigest()
        assert item["_meta"]["checksum_status"] == "matches_recorded"
        assert item["_meta"]["readable"]
    text = rpc(tmp_path, "resources/read", {"uri": uri("table")})["result"]["contents"][0]
    assert text["mimeType"] == "text/csv"
    assert text["text"].encode() == Path(record["artifacts"]["table"]).read_bytes()
    assert "blob" not in text
    image = rpc(tmp_path, "resources/read", {"uri": uri("figure")})["result"]["contents"][0]
    assert image["mimeType"] == "image/png"
    assert base64.b64decode(image["blob"]) == Path(record["artifacts"]["figure"]).read_bytes()
    assert "text" not in image and image.get("type") != "image"
    assert "error" in rpc(tmp_path, "resources/read", {"uri": uri("unregistered-secret.csv")})


def test_json_text_and_mat_blob_are_not_scientifically_decoded(tmp_path):
    make_run(tmp_path, files={"summary": ("summary.json", b'{"source":"MATLAB"}'),
                              "mat": ("analysis.mat", b"opaque MATLAB container\x00")})
    text = artifacts.read_resource(tmp_path, uri("summary"))["contents"][0]
    assert json.loads(text["text"]) == {"source": "MATLAB"}
    mat = artifacts.read_resource(tmp_path, uri("mat"))["contents"][0]
    assert base64.b64decode(mat["blob"]) == b"opaque MATLAB container\x00"
    assert mat["mimeType"] == "application/x-matlab-data"


@pytest.mark.parametrize("bad_uri", [
    "file:///etc/passwd", uri("../result.json"), uri("%2e%2e%2fresult.json"),
    uri("table") + "?path=/etc/passwd", uri("table") + "#fragment",
    "acycle://runs/other/table", uri("table") + "/extra", None,
])
def test_uri_does_not_accept_paths_queries_or_other_schemes(tmp_path, bad_uri):
    make_run(tmp_path)
    with pytest.raises(artifacts.ArtifactError):
        artifacts.read_resource(tmp_path, bad_uri)
    assert "error" in rpc(tmp_path, "resources/read", {"uri": bad_uri})


@pytest.mark.parametrize("escape", ["outside_workspace", "another_run", "input_snapshot", "symlink"])
def test_registered_path_must_remain_in_its_own_outputs(tmp_path, escape):
    record = make_run(tmp_path)
    run = Path(record["output_dir"]).parent
    if escape == "outside_workspace":
        target = tmp_path.parent / (tmp_path.name + "-outside.csv")
        target.write_text("outside")
    elif escape == "another_run":
        other = make_run(tmp_path, OTHER)
        target = Path(other["artifacts"]["table"])
    elif escape == "input_snapshot":
        target = run / "input.csv"
        target.write_text("frozen input is not an output resource")
    else:
        target = Path(record["output_dir"]) / "linked.csv"
        outside = tmp_path / "private.csv"
        outside.write_text("outside output directory")
        target.symlink_to(outside)
    record["artifacts"]["escape"] = str(target)
    save_record(tmp_path, record)
    with pytest.raises(artifacts.ArtifactError, match="inside this run"):
        artifacts.read_resource(tmp_path, uri("escape"))
    catalog = artifacts.list_resources(tmp_path)
    assert uri("escape") not in {entry["uri"] for entry in catalog["resources"]}
    assert any(entry.get("artifact_key") == "escape" for entry in catalog["_meta"]["skipped_resources"])


def test_in_output_symlink_is_allowed_but_output_directory_alias_is_not(tmp_path):
    record = make_run(tmp_path)
    output = Path(record["output_dir"])
    link = output / "alias.csv"
    link.symlink_to(output / "table.csv")
    record["artifacts"]["alias"] = str(link)
    save_record(tmp_path, record)
    assert artifacts.read_resource(tmp_path, uri("alias"))["contents"][0]["text"]
    moved = output.parent / "other-output-location"
    output.rename(moved)
    output.symlink_to(moved, target_is_directory=True)
    with pytest.raises(artifacts.ArtifactError, match="symbolic-link alias"):
        artifacts.read_resource(tmp_path, uri("table"))


def test_result_record_alias_cannot_borrow_registration(tmp_path):
    record = make_run(tmp_path)
    result = Path(record["output_dir"]).parent / "result.json"
    moved = result.parent / "borrowed.json"
    result.rename(moved)
    result.symlink_to(moved)
    with pytest.raises(artifacts.ArtifactError, match="symbolic-link alias"):
        artifacts.read_resource(tmp_path, uri("table"))


def test_registered_checksum_change_is_rejected_without_hiding_run(tmp_path):
    record = make_run(tmp_path)
    Path(record["artifacts"]["table"]).write_bytes(b"changed")
    with pytest.raises(artifacts.ArtifactError, match="checksum changed"):
        artifacts.read_resource(tmp_path, uri("table"))
    decorated = artifacts.with_artifact_resources(record, tmp_path)
    assert decorated["status"] == "completed"
    assert any(item["artifact_key"] == "table" for item in decorated["artifact_resource_errors"])
    assert {item["uri"] for item in decorated["artifact_resources"]} == {uri("figure")}


def test_read_size_limit_lists_metadata_but_never_returns_oversize_payload(tmp_path, monkeypatch):
    monkeypatch.setattr(artifacts, "MAX_READ_BYTES", 8)
    make_run(tmp_path, files={"small": ("small.csv", b"1,2\n"), "large": ("large.mat", b"012345678")})
    resources = artifacts.list_resources(tmp_path)["resources"]
    large = next(item for item in resources if item["_meta"]["artifact_key"] == "large")
    assert large["size"] == 9 and large["_meta"]["readable"] is False
    assert "text" in artifacts.read_resource(tmp_path, uri("small"))["contents"][0]
    with pytest.raises(artifacts.ArtifactError, match="read limit"):
        artifacts.read_resource(tmp_path, uri("large"))
    assert "error" in rpc(tmp_path, "resources/read", {"uri": uri("large")})


def test_catalog_pagination_only_traverses_registered_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(artifacts, "PAGE_SIZE", 1)
    make_run(tmp_path)
    first = artifacts.list_resources(tmp_path)
    second = artifacts.list_resources(tmp_path, first["nextCursor"])
    assert len(first["resources"]) == len(second["resources"]) == 1
    assert "nextCursor" not in second
    assert first["resources"][0]["uri"] != second["resources"][0]["uri"]
    with pytest.raises(artifacts.ArtifactError):
        artifacts.list_resources(tmp_path, "../result")


def test_tools_call_resource_metadata_is_text_only_and_does_not_mutate_run(tmp_path):
    record = make_run(tmp_path)
    path = Path(record["output_dir"]).parent / "result.json"
    before = path.read_bytes()
    response = rpc(tmp_path, "tools/call", {"name": "acycle_get_run", "arguments": {"run_id": RUN}},
                   dispatcher=lambda *_: record)["result"]
    assert [item["type"] for item in response["content"]] == ["text"]
    value = json.loads(response["content"][0]["text"])
    assert len(value["artifact_resources"]) == 2
    assert "does not guarantee" in value["artifact_resource_note"]
    assert "artifact_resources" not in record
    assert path.read_bytes() == before
    assert "isError" not in response


def test_runerror_retains_structured_diagnostics_and_readable_response(tmp_path):
    record = make_run(tmp_path, status="failed")
    record["artifacts"] = {}
    output = Path(record["output_dir"])
    response_file = output / "response.json"
    response_file.write_text('{"error":{"identifier":"Harness:COCOUnresolved"}}')
    record.update(error="MATLAB unresolved", parent_run_id=OTHER,
                  matlab_error={"identifier": "Harness:COCOUnresolved"},
                  diagnostics={"response.json": str(response_file)}, parameters={"window": 8})
    save_record(tmp_path, record)
    def failed_dispatch(*_):
        raise RunError(record)
    response = rpc(tmp_path, "tools/call", {"name": "acycle_get_run"}, dispatcher=failed_dispatch)["result"]
    value = json.loads(response["content"][0]["text"])
    assert response["isError"] is True
    assert value["status"] == "failed" and value["run_id"] == RUN
    assert value["parent_run_id"] == OTHER
    assert value["diagnostics"] == record["diagnostics"]
    assert value["matlab_error"]["identifier"] == "Harness:COCOUnresolved"
    resource = value["artifact_resources"][0]
    assert resource["uri"] == uri("diagnostic.response.json")
    assert resource["_meta"]["kind"] == "diagnostic"
    content = artifacts.read_resource(tmp_path, resource["uri"])["contents"][0]
    assert json.loads(content["text"])["error"]["identifier"] == "Harness:COCOUnresolved"


def test_cancelled_run_keeps_registered_diagnostics_accessible(tmp_path):
    record = make_run(tmp_path, status="cancelled")
    record["artifacts"] = {}
    log = Path(record["output_dir"]) / "matlab.log"
    content = b"MATLAB launch recorded before interrupt\n"
    log.write_bytes(content)
    record.update(error="KeyboardInterrupt: ", diagnostics={"matlab.log": str(log)})
    save_record(tmp_path, record)
    catalog = rpc(tmp_path, "resources/list")["result"]["resources"]
    assert [item["uri"] for item in catalog] == [uri("diagnostic.matlab.log")]
    loaded = rpc(tmp_path, "resources/read", {"uri": catalog[0]["uri"]})["result"]["contents"][0]
    assert base64.b64decode(loaded["blob"]) == content
    response = rpc(tmp_path, "tools/call", {"name": "acycle_get_run"}, dispatcher=lambda *_: record)["result"]
    saved = json.loads(response["content"][0]["text"])
    assert response["isError"] is True
    assert saved["status"] == "cancelled" and saved["diagnostics"] == record["diagnostics"]
    assert saved["artifact_resources"][0]["uri"] == catalog[0]["uri"]


def test_real_stdio_exposes_registered_resources_without_api_or_matlab(tmp_path):
    make_run(tmp_path)
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "resources/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "resources/read", "params": {"uri": uri("table")}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
            "name": "acycle_get_run", "arguments": {"run_id": RUN}}},
    ]
    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    proc = subprocess.run([sys.executable, "-m", "acycle_deepseek.mcp", "--workspace", str(tmp_path)],
                          input="\n".join(json.dumps(item) for item in requests) + "\n",
                          text=True, capture_output=True, env=env, timeout=30, check=True)
    responses = [json.loads(line) for line in proc.stdout.splitlines()]
    assert [item["id"] for item in responses] == [1, 2, 3, 4]
    assert len(responses[1]["result"]["resources"]) == 2
    assert "text" in responses[2]["result"]["contents"][0]
    assert len(json.loads(responses[3]["result"]["content"][0]["text"])["artifact_resources"]) == 2
