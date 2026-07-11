"""Tests for isolated application configuration loading."""

import sys
from types import ModuleType

from app import _load_config_mapping


def test_config_loader_does_not_mutate_global_import_state(monkeypatch):
    foreign_config = ModuleType("config")
    monkeypatch.setitem(sys.modules, "config", foreign_config)
    monkeypatch.setattr(sys, "path", ["/tmp/OntServe", *sys.path])
    original_path = list(sys.path)

    config_mapping = _load_config_mapping()

    assert config_mapping["testing"].TESTING is True
    assert sys.modules["config"] is foreign_config
    assert sys.path == original_path


def test_llm_config_import_does_not_depend_on_top_level_config(monkeypatch):
    foreign_config = ModuleType("config")
    monkeypatch.setitem(sys.modules, "config", foreign_config)

    from app.llm_config import LLMTaskType, get_llm_config

    assert LLMTaskType.EXTRACTION == "extraction"
    assert get_llm_config() is not None
