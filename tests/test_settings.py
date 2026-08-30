import json
import pytest
from pathlib import Path
from unittest.mock import patch


def test_load_returns_defaults_when_no_file(tmp_path):
    with patch("daemon.settings.SETTINGS_PATH", tmp_path / "settings.json"):
        from daemon import settings
        result = settings.load()
    assert result["whisper_model"] == "small.en"
    assert result["tone_mappings"] == {}
    assert result["history_enabled"] is True
    assert result["openai_api_key"] == ""


def test_save_and_load_roundtrip(tmp_path):
    settings_path = tmp_path / "settings.json"
    with patch("daemon.settings.SETTINGS_PATH", settings_path), \
         patch("daemon.settings.APP_SUPPORT", tmp_path):
        from daemon import settings
        settings.save({"openai_api_key": "sk-test", "whisper_model": "medium.en",
                       "tone_mappings": {}, "history_enabled": False})
        result = settings.load()
    assert result["openai_api_key"] == "sk-test"
    assert result["whisper_model"] == "medium.en"
    assert result["history_enabled"] is False


def test_get_tone_returns_casual_for_unknown_app(tmp_path):
    with patch("daemon.settings.SETTINGS_PATH", tmp_path / "settings.json"):
        from daemon import settings
        tone_name, instructions = settings.get_tone("UnknownApp")
    assert tone_name == "Casual"
    assert "conversational" in instructions.lower()


def test_get_tone_returns_mapped_builtin(tmp_path):
    settings_path = tmp_path / "settings.json"
    with patch("daemon.settings.SETTINGS_PATH", settings_path), \
         patch("daemon.settings.APP_SUPPORT", tmp_path):
        from daemon import settings
        settings.save({
            "openai_api_key": "",
            "whisper_model": "small.en",
            "tone_mappings": {"Mail": {"tone": "Formal", "custom_instruction": ""}},
            "history_enabled": True,
        })
        tone_name, instructions = settings.get_tone("Mail")
    assert tone_name == "Formal"
    assert "professional" in instructions.lower()


def test_get_tone_returns_custom_instruction(tmp_path):
    settings_path = tmp_path / "settings.json"
    with patch("daemon.settings.SETTINGS_PATH", settings_path), \
         patch("daemon.settings.APP_SUPPORT", tmp_path):
        from daemon import settings
        settings.save({
            "openai_api_key": "",
            "whisper_model": "small.en",
            "tone_mappings": {"Cursor": {"tone": "Custom",
                                          "custom_instruction": "Be concise and technical."}},
            "history_enabled": True,
        })
        tone_name, instructions = settings.get_tone("Cursor")
    assert tone_name == "Custom"
    assert instructions == "Be concise and technical."
