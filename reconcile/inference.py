"""What served the model in a run: the llama.cpp build, the model files and the server's settings.

Two runs at temperature 0 and one seed can still differ when the inference build or a model file
differs. A manifest records both, so that a difference between runs can be put on the right cause.

The facts come from three places, each named by an environment variable (scripts/run reads them from
a file outside the repository, so the repository holds no path of the machine):

    TR_LLAMA_SERVER      the `llama-server` binary; its `--version` gives the build and the commit
    TR_PRESETS           the server's preset file (ini): one section per model id
    TR_MODEL_CHECKSUMS   a `shasum -a 256` list of the model files

and from the server itself (`/props`), read while the model is loaded. A manifest stores file names
and hashes, never a path. A value that cannot be read is recorded as null, with a note.
"""

from __future__ import annotations

import configparser
import hashlib
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

MODEL_PREFIX = "openai-api/llama-cpp/"
LLAMA_VERSION = re.compile(
    r"version: (?P<version>\S+) \(build (?P<build>\d+), commit (?P<commit>[0-9a-f]+)\)"
)
# Server-side defaults that decide sampling when a request does not set them.
SAMPLING_KEYS = ("temperature", "top_k", "top_p", "min_p", "repeat_penalty", "n_predict", "seed")


def env_path(variable: str) -> Path | None:
    value = os.environ.get(variable)
    return Path(value).expanduser() if value else None


# ---------------------------------------------------------------- pure parsers


def parse_presets(text: str) -> dict[str, dict[str, str]]:
    """llama-server preset file -> {model id: {key: value}}, with the `[*]` defaults applied."""
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.read_string("[__top__]\n" + text)
    defaults = dict(parser["*"]) if parser.has_section("*") else {}
    return {
        section: defaults | dict(parser[section])
        for section in parser.sections()
        if section not in ("__top__", "*")
    }


def parse_checksums(text: str) -> dict[str, str]:
    """`shasum -a 256` list -> {relative path: sha256}."""
    checksums: dict[str, str] = {}
    for line in text.splitlines():
        digest, _, name = line.partition(" ")
        name = name.strip().lstrip("*")
        if len(digest) == 64 and name:
            checksums[name] = digest
    return checksums


def parse_llama_version(text: str) -> dict[str, Any] | None:
    match = LLAMA_VERSION.search(text)
    if not match:
        return None
    return {"version": match["version"], "build": int(match["build"]), "commit": match["commit"]}


def model_ids(log_headers: list[dict[str, Any]]) -> list[str]:
    """Server model ids that the logs name, as the main model or in a model role."""
    names: set[str] = set()
    for header in log_headers:
        names.add(header.get("model") or "")
        names.update(role["model"] for role in (header.get("model_roles") or {}).values())
    # "none/none" is Inspect's placeholder when a task names its models only through roles.
    return sorted(name.removeprefix(MODEL_PREFIX) for name in names if name and name != "none/none")


def model_record(
    model_id: str, presets: dict[str, dict[str, str]], checksums: dict[str, str]
) -> dict[str, Any]:
    """File name and sha256 of a model's weights. The sha256 comes from the checksum list."""
    preset = presets.get(model_id)
    if preset is None or "model" not in preset:
        return {"id": model_id, "file": None, "sha256": None, "note": "no preset with this id"}
    path = preset["model"]
    for relative, digest in checksums.items():
        if path.endswith("/" + relative) or path == relative:
            return {"id": model_id, "file": Path(relative).name, "sha256": digest}
    return {"id": model_id, "file": Path(path).name, "sha256": None, "note": "not in the checksum list"}


def slot_settings(preset: dict[str, str]) -> dict[str, int | None]:
    def number(key: str) -> int | None:
        value = preset.get(key)
        return int(value) if value is not None and value.isdigit() else None

    return {
        "parallel": number("parallel"),
        "kv_unified_per_slot": number("kv-unified-per-slot"),
        "ctx_size": number("c"),
        "n_predict": number("n-predict"),
        "reasoning_budget": number("reasoning-budget"),
    }


# ---------------------------------------------------------------- facts from the machine


def _get(url: str, key: str | None, timeout: float) -> Any:
    request = urllib.request.Request(url)
    if key:
        request.add_header("Authorization", f"Bearer {key}")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except (OSError, ValueError):
        return None


def loaded_models(base_url: str, key: str | None) -> list[str]:
    """Ids of the models that the server has in memory now. Best effort."""
    data = (_get(f"{base_url}/models", key, 5) or {}).get("data", [])
    return [m["id"] for m in data if (m.get("status") or {}).get("value") == "loaded"]


def server_settings(base_url: str, key: str | None, model_id: str) -> dict[str, Any] | None:
    """Slot count, context, build and sampling defaults of a loaded model, from the server. Best effort."""
    props = _get(f"{base_url.removesuffix('/v1')}/props?model={model_id}&autoload=false", key, 10)
    if not isinstance(props, dict):
        return None
    settings = props.get("default_generation_settings", {})
    params = settings.get("params", {})
    return {
        "total_slots": props.get("total_slots"),
        "n_ctx": settings.get("n_ctx"),
        "build_info": props.get("build_info"),
        "sampling_defaults": {k: params.get(k) for k in SAMPLING_KEYS},
    }


def llama_cpp() -> dict[str, Any] | None:
    """Version, build and commit of the llama-server binary. It prints them on stderr."""
    binary = env_path("TR_LLAMA_SERVER")
    if binary is None:
        return None
    try:
        result = subprocess.run([str(binary), "--version"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return parse_llama_version(result.stdout + result.stderr)


def record(log_headers: list[dict[str, Any]], servers: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """The `llama_cpp`, `presets` and `models` fields of a manifest.

    `servers` holds the settings that were read from the server while each model was loaded.
    """
    presets_file, checksums_file = env_path("TR_PRESETS"), env_path("TR_MODEL_CHECKSUMS")
    presets_text = presets_file.read_text() if presets_file and presets_file.exists() else None
    presets = parse_presets(presets_text) if presets_text is not None else {}
    checksums = (
        parse_checksums(checksums_file.read_text()) if checksums_file and checksums_file.exists() else {}
    )
    return {
        "llama_cpp": llama_cpp(),
        "presets": {
            "file": presets_file.name if presets_file else None,
            "sha256": hashlib.sha256(presets_text.encode()).hexdigest() if presets_text is not None else None,
        },
        "models": [
            model_record(model_id, presets, checksums)
            | {"slots": slot_settings(presets.get(model_id, {}))}
            | {"server": servers.get(model_id)}
            for model_id in model_ids(log_headers)
        ],
    }
