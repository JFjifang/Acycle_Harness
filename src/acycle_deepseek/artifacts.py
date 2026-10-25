"""Read registered MATLAB output files as MCP resources; no scientific work.

Resource transport makes original files accessible to a compatible MCP client.
It does not guarantee that a client's main chat renders images or attachments.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import re


MAX_READ_BYTES = 32 * 1024 * 1024
PAGE_SIZE = 100
_RUN_ID = r"[0-9]{8}T[0-9]{6}Z-[a-f0-9]{12}"
_KEY = r"[A-Za-z][A-Za-z0-9_.-]{0,199}"
_URI = re.compile(rf"acycle://runs/({_RUN_ID})/({_KEY})")
PRESENTATION_NOTE = (
    "These are registered original MATLAB files exposed through MCP resources. "
    "Resource availability does not guarantee image or attachment rendering in "
    "the client's main chat. No image content block is added automatically."
)
_MIME = {
    ".csv": "text/csv", ".json": "application/json", ".png": "image/png",
    ".pdf": "application/pdf", ".fig": "application/x-matlab-figure",
    ".mat": "application/x-matlab-data", ".txt": "text/plain",
    ".log": "text/plain", ".tsv": "text/tab-separated-values",
}


class ArtifactError(ValueError):
    """A resource cannot be resolved or read under the registered-run policy."""


def _record(workspace, run_id):
    if not isinstance(run_id, str) or not re.fullmatch(_RUN_ID, run_id):
        raise ArtifactError("Invalid registered run ID")
    root = Path(workspace).resolve()
    run = root / ".acycle" / "runs" / run_id
    result = run / "result.json"
    outputs = run / "outputs"
    # A run must own its actual output directory. Even aliases to another run
    # inside the workspace must not borrow that run's identity or permissions.
    try:
        alias = run.resolve() != run or outputs.resolve() != outputs or result.resolve() != result
    except (OSError, RuntimeError, ValueError) as exc:
        raise ArtifactError("Run storage has an invalid path or symbolic link") from exc
    if alias:
        raise ArtifactError("Run storage or result record uses a symbolic-link alias")
    if not result.is_file() or not outputs.is_dir():
        raise ArtifactError("Unknown run or missing registered output directory")
    try:
        record = json.loads(result.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ArtifactError("Saved run record cannot be read") from exc
    if not isinstance(record, dict) or record.get("run_id") != run_id:
        raise ArtifactError("Saved run identity does not match the requested resource")
    if record.get("status") not in {"completed", "failed", "cancelled"}:
        raise ArtifactError("Resources require a completed, failed or cancelled saved run")
    return run, outputs, record


def _entries(record):
    entries = {}
    artifacts = record.get("artifacts", {})
    if not isinstance(artifacts, dict):
        raise ArtifactError("Saved artifacts registration must be an object")
    for key, path in artifacts.items():
        if isinstance(key, str) and re.fullmatch(_KEY, key):
            entries[key] = (path, "artifact", key)
    # Failed/cancelled-run logs/response JSON are diagnostics, not completed
    # scientific products. Only explicitly registered diagnostics are exposed.
    diagnostics = record.get("diagnostics", {}) if record.get("status") in {"failed", "cancelled"} else {}
    if not isinstance(diagnostics, dict):
        raise ArtifactError("Saved diagnostics registration must be an object")
    for key, path in diagnostics.items():
        alias = f"diagnostic.{key}"
        if isinstance(key, str) and re.fullmatch(_KEY, alias) and alias not in entries:
            entries[alias] = (path, "diagnostic", key)
    return entries


def _registered(workspace, run_id, key):
    if not isinstance(key, str) or not re.fullmatch(_KEY, key):
        raise ArtifactError("Invalid registered artifact key")
    run, outputs, record = _record(workspace, run_id)
    entry = _entries(record).get(key)
    if entry is None:
        raise ArtifactError("Artifact key is not registered in this run")
    registered, kind, original_key = entry
    if not isinstance(registered, str) or not registered:
        raise ArtifactError("Registered artifact path is invalid")
    candidate = Path(registered)
    if not candidate.is_absolute():
        candidate = run / candidate
    try:
        candidate = candidate.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ArtifactError("Registered artifact does not exist or has an invalid link") from exc
    if not candidate.is_relative_to(outputs) or not candidate.is_file():
        raise ArtifactError("Registered artifact must be a file inside this run's outputs")
    hashes = record.get("artifact_sha256", {}) if kind == "artifact" else record.get("diagnostic_sha256", {})
    if not isinstance(hashes, dict):
        raise ArtifactError("Saved artifact checksums must be an object")
    expected = hashes.get(original_key)
    if expected is not None and (not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected)):
        raise ArtifactError("Saved artifact checksum is invalid")
    return candidate, kind, expected


def _check_hash(actual, expected):
    if expected is not None and actual != expected:
        raise ArtifactError("Registered artifact checksum changed; refusing altered output")


def _descriptor(path, run_id, key, kind, digest, size, expected):
    uri = f"acycle://runs/{run_id}/{key}"
    return {
        "uri": uri, "name": f"{run_id}/{key}",
        "description": f"Registered MATLAB {kind}: {path.name}. {PRESENTATION_NOTE}",
        "mimeType": _MIME.get(path.suffix.lower(), "application/octet-stream"),
        "size": size,
        "_meta": {
            "run_id": run_id, "artifact_key": key, "filename": path.name,
            "kind": kind, "sha256": digest, "size": size,
            "checksum_status": "matches_recorded" if expected is not None else "current_bytes_only",
            "readable": size <= MAX_READ_BYTES, "read_limit_bytes": MAX_READ_BYTES,
        },
    }


def resource_metadata(workspace, run_id, key):
    """Hash a registered file without loading scientific arrays or decoding it."""
    path, kind, expected = _registered(workspace, run_id, key)
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
                size += len(block)
    except OSError as exc:
        raise ArtifactError("Registered artifact cannot be read") from exc
    actual = digest.hexdigest()
    _check_hash(actual, expected)
    return _descriptor(path, run_id, key, kind, actual, size, expected)


def list_resources(workspace, cursor=None):
    """List registered resources, never files discovered in output directories."""
    if cursor is not None and (not isinstance(cursor, str) or not re.fullmatch(r"0|[1-9][0-9]{0,11}", cursor)):
        raise ArtifactError("Invalid resource cursor")
    start = int(cursor or "0")
    root = Path(workspace).resolve()
    storage = root / ".acycle" / "runs"
    try:
        storage_alias = storage.resolve() != storage
    except (OSError, RuntimeError, ValueError) as exc:
        raise ArtifactError("Run storage has an invalid path or symbolic link") from exc
    if storage_alias:
        raise ArtifactError("Run storage uses a symbolic-link alias")
    if not storage.is_dir():
        return {"resources": []}
    candidates = []
    skipped = []
    for run in sorted(storage.iterdir(), key=lambda entry: entry.name):
        if not re.fullmatch(_RUN_ID, run.name):
            continue
        try:
            _, _, record = _record(root, run.name)
            candidates.extend((run.name, key) for key in sorted(_entries(record)))
        except (ArtifactError, OSError) as exc:
            skipped.append({"run_id": run.name, "reason": str(exc)})
    resources = []
    page = candidates[start:start + PAGE_SIZE]
    for run_id, key in page:
        try:
            resources.append(resource_metadata(root, run_id, key))
        except (ArtifactError, OSError) as exc:
            skipped.append({"run_id": run_id, "artifact_key": key, "reason": str(exc)})
    result = {"resources": resources}
    if start + PAGE_SIZE < len(candidates):
        result["nextCursor"] = str(start + PAGE_SIZE)
    if skipped:
        result["_meta"] = {"skipped_resources": skipped}
    return result


def read_resource(workspace, uri):
    if not isinstance(uri, str) or not (match := _URI.fullmatch(uri)):
        raise ArtifactError("Expected acycle://runs/<run_id>/<registered_artifact_key>")
    run_id, key = match.groups()
    path, kind, expected = _registered(workspace, run_id, key)
    try:
        if path.stat().st_size > MAX_READ_BYTES:
            raise ArtifactError(f"Resource exceeds the {MAX_READ_BYTES}-byte read limit")
        with path.open("rb") as stream:
            content = stream.read(MAX_READ_BYTES + 1)
    except OSError as exc:
        raise ArtifactError("Registered artifact cannot be read") from exc
    if len(content) > MAX_READ_BYTES:
        raise ArtifactError(f"Resource exceeds the {MAX_READ_BYTES}-byte read limit")
    digest = hashlib.sha256(content).hexdigest()
    _check_hash(digest, expected)
    metadata = _descriptor(path, run_id, key, kind, digest, len(content), expected)
    item = {"uri": uri, "mimeType": metadata["mimeType"], "_meta": metadata["_meta"]}
    if path.suffix.lower() in {".csv", ".json"}:
        try:
            item["text"] = content.decode("utf-8")
        except UnicodeError as exc:
            raise ArtifactError("CSV/JSON resource is not valid UTF-8 text") from exc
    else:
        item["blob"] = base64.b64encode(content).decode("ascii")
    return {"contents": [item]}


def with_artifact_resources(value, workspace):
    """Add resource hints without replacing a scientific result on I/O failure."""
    if not isinstance(value, dict):
        return value
    run_ids = []
    for key in ("run_id", "baseline_run_id"):
        if value.get(key):
            run_ids.append(value[key])
    for run in value.get("runs", []) if isinstance(value.get("runs", []), list) else []:
        if isinstance(run, dict) and run.get("run_id"):
            run_ids.append(run["run_id"])
    resources = []
    errors = []
    seen = set()
    for run_id in run_ids:
        if not isinstance(run_id, str) or run_id in seen:
            continue
        seen.add(run_id)
        try:
            _, _, record = _record(workspace, run_id)
            for key in sorted(_entries(record)):
                try:
                    resources.append(resource_metadata(workspace, run_id, key))
                except (ArtifactError, OSError) as exc:
                    errors.append({"run_id": run_id, "artifact_key": key, "reason": str(exc)})
        except (ArtifactError, OSError) as exc:
            errors.append({"run_id": run_id, "reason": str(exc)})
    result = {**value, "artifact_resources": resources, "artifact_resource_note": PRESENTATION_NOTE}
    if errors:
        result["artifact_resource_errors"] = errors
    return result
