from unittest.mock import patch, MagicMock


def _mock_openai_response(text: str):
    mock_openai = MagicMock()
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = text
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])
    mock_openai.OpenAI.return_value = mock_client
    return mock_openai, mock_client


def test_rewrite_calls_gpt_with_tone(tmp_path):
    mock_openai, mock_client = _mock_openai_response("I wanted to ask about the meeting.")

    with patch.dict("sys.modules", {"openai": mock_openai}), \
         patch("daemon.settings.SETTINGS_PATH", tmp_path / "settings.json"), \
         patch("daemon.settings.APP_SUPPORT", tmp_path):
        from daemon import settings, intent
        import importlib; importlib.reload(intent)
        settings.save({
            "openai_api_key": "sk-test",
            "whisper_model": "small.en",
            "tone_mappings": {"Slack": {"tone": "Casual", "custom_instruction": ""}},
            "history_enabled": True,
        })
        result = intent.rewrite("um yeah I wanted to ask about the meeting", "Slack")

    assert result == "I wanted to ask about the meeting."
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "gpt-4o-mini"
    system_msg = call_kwargs["messages"][0]["content"]
    assert "Casual" in system_msg


def test_rewrite_falls_back_to_raw_when_no_api_key(tmp_path):
    mock_openai, _ = _mock_openai_response("")

    with patch.dict("sys.modules", {"openai": mock_openai}), \
         patch("daemon.settings.SETTINGS_PATH", tmp_path / "settings.json"), \
         patch("daemon.settings.APP_SUPPORT", tmp_path):
        from daemon import settings, intent
        import importlib; importlib.reload(intent)
        # settings.json doesn't exist → key is ""
        result = intent.rewrite("um hello there", "Mail")

    assert result == "um hello there"
    mock_openai.OpenAI.assert_not_called()


def test_rewrite_uses_formal_tone_for_mail(tmp_path):
    mock_openai, mock_client = _mock_openai_response("Please review the attached document.")

    with patch.dict("sys.modules", {"openai": mock_openai}), \
         patch("daemon.settings.SETTINGS_PATH", tmp_path / "settings.json"), \
         patch("daemon.settings.APP_SUPPORT", tmp_path):
        from daemon import settings, intent
        import importlib; importlib.reload(intent)
        settings.save({
            "openai_api_key": "sk-test",
            "whisper_model": "small.en",
            "tone_mappings": {"Mail": {"tone": "Formal", "custom_instruction": ""}},
            "history_enabled": True,
        })
        result = intent.rewrite("uh please like review the attached document", "Mail")

    system_msg = mock_client.chat.completions.create.call_args[1]["messages"][0]["content"]
    assert "Formal" in system_msg
    assert "professional" in system_msg.lower()
