"""Env file loader (export KEY= and KEY=)."""
from pathlib import Path

from director_bot.envload import load_env_file


def test_load_export_style(tmp_path: Path, monkeypatch):
    p = tmp_path / ".env"
    p.write_text(
        "export DIRECTOR_BOT_PROVIDER=xai\n"
        "export FAKE_TEST_KEY=secret-value-not-real\n"
        "# comment\n"
        "OTHER=plain\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("DIRECTOR_BOT_PROVIDER", raising=False)
    monkeypatch.delenv("FAKE_TEST_KEY", raising=False)
    monkeypatch.delenv("OTHER", raising=False)
    keys = load_env_file(p)
    assert "DIRECTOR_BOT_PROVIDER" in keys
    assert "FAKE_TEST_KEY" in keys
    assert "OTHER" in keys
    import os
    assert os.environ["DIRECTOR_BOT_PROVIDER"] == "xai"
    assert os.environ["FAKE_TEST_KEY"] == "secret-value-not-real"
    assert os.environ["OTHER"] == "plain"
