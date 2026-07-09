"""Soul: memory, process machine, cognitive cycle."""
from pathlib import Path

from director_bot.canon.db import CanonDB
from director_bot.canon.seed import seed_demo_canon
from director_bot.soul.loader import load_soul
from director_bot.soul.memory import WorkingMemory
from director_bot.soul.processes import ProcessMachine
from director_bot.soul.steps import DirectorMind, run_cognitive_cycle
import pytest


def test_process_transitions():
    m = ProcessMachine("intake")
    assert m.can_transition("break_story")
    assert not m.can_transition("previs")
    m.transition("break_story")
    with pytest.raises(ValueError):
        m.transition("dailies")


def test_working_memory_append():
    wm = WorkingMemory()
    wm.append("note", "hello")
    assert len(wm.entries) == 1
    assert "hello" in wm.format_for_prompt()
    restored = WorkingMemory.from_list(wm.to_list())
    assert restored.entries[0].content == "hello"


def test_load_soul():
    soul = load_soul()
    assert "Director" in soul.system_preamble() or "director" in soul.core.lower()
    assert soul.core.strip()


def test_cognitive_cycle(tmp_path: Path):
    db = CanonDB(tmp_path / "t.db")
    seed_demo_canon(db)
    pid = db.create_project("Soul Test", genre="thriller")
    mind = DirectorMind.create(db, project_id=pid)
    for step in ("break_story", "write", "shotlist"):
        mind.set_phase(step)
    result = run_cognitive_cycle(
        mind,
        summary="Interrogation; silence; power without dialogue",
        genre="thriller",
    )
    assert result["chosen"].action
    assert result["decision"] is not None
    proj = db.get_project(pid)
    assert proj["phase"] == "shotlist"
    assert proj["working_memory"]
