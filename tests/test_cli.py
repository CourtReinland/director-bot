"""CLI smoke (typer invoke)."""
from pathlib import Path

from typer.testing import CliRunner

from director_bot.cli import app

runner = CliRunner()


def test_demo_cli(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIRECTOR_BOT_HOME", str(tmp_path / "home"))
    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 0, result.output
    assert "chain ok: True" in result.output


def test_doctor_cli(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIRECTOR_BOT_HOME", str(tmp_path / "home"))
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "DIRECTOR_BOT_HOME" in result.output
