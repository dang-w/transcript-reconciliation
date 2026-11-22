"""The parsers behind the inference fields of a manifest. No server, no model file."""

from reconcile import inference

PRESETS = """
[*]
parallel = 4
kv-unified-per-slot = 32768

[big]
model = /models/a/Big-Q4.gguf
reasoning-budget = 12288

[small]
model = /models/b/Small-Q8.gguf
"""


def test_presets_apply_the_defaults_section():
    presets = inference.parse_presets(PRESETS)
    assert set(presets) == {"big", "small"}
    assert presets["big"]["parallel"] == "4" and presets["big"]["reasoning-budget"] == "12288"
    assert inference.slot_settings(presets["small"])["reasoning_budget"] is None
    assert inference.slot_settings(presets["big"])["kv_unified_per_slot"] == 32768


def test_llama_version_line():
    text = "version: 0.6.0-dev (build 11612, commit 10da8c463)\nbuilt with AppleClang"
    assert inference.parse_llama_version(text) == {
        "version": "0.6.0-dev",
        "build": 11612,
        "commit": "10da8c463",
    }
    assert inference.parse_llama_version("no such line") is None


def test_model_record_takes_the_hash_from_the_checksum_list_and_stores_no_path():
    presets = inference.parse_presets(PRESETS)
    checksums = inference.parse_checksums("a" * 64 + "  a/Big-Q4.gguf\nnot a line\n")
    assert inference.model_record("big", presets, checksums) == {
        "id": "big", "file": "Big-Q4.gguf", "sha256": "a" * 64,
    }  # fmt: skip
    small = inference.model_record("small", presets, checksums)
    assert small["file"] == "Small-Q8.gguf" and small["sha256"] is None
    assert inference.model_record("other", presets, checksums)["file"] is None


def test_model_ids_come_from_the_roles_and_skip_the_placeholder():
    headers = [
        {"model": "none/none", "model_roles": {"untrusted": {"model": "openai-api/llama-cpp/big"}}},
        {"model": None, "model_roles": {"trusted": {"model": "openai-api/llama-cpp/small"}}},
    ]
    assert inference.model_ids(headers) == ["big", "small"]


def test_record_without_the_machine_file_is_null_not_an_error(monkeypatch):
    for name in ("TR_LLAMA_SERVER", "TR_PRESETS", "TR_MODEL_CHECKSUMS"):
        monkeypatch.delenv(name, raising=False)
    record = inference.record([{"model": "openai-api/llama-cpp/big"}], {})
    assert record["llama_cpp"] is None and record["presets"] == {"file": None, "sha256": None}
    assert record["models"][0]["id"] == "big" and record["models"][0]["sha256"] is None
