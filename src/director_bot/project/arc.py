"""Multi-episode arc planner: motifs, plants/payoffs, episode spine."""
from __future__ import annotations

from typing import Any, Optional

from director_bot.canon.db import CanonDB
from director_bot.soul.brain import TextBrain, get_brain


# Classic web/TV motif kinds the director tracks.
MOTIF_KINDS = (
    "visual",       # recurring image / object
    "audio",        # sting, theme, silence pattern
    "character",    # relationship pattern
    "thematic",     # idea restated
    "structural",   # cold open form, button, etc.
)


def add_motif(
    db: CanonDB,
    series_project_id: int,
    *,
    name: str,
    kind: str = "visual",
    description: str = "",
    first_episode: Optional[int] = 1,
    payoff_episode: Optional[int] = None,
    tags: Optional[list[str]] = None,
) -> int:
    kind_v = kind if kind in MOTIF_KINDS else "visual"
    return db.add_motif(series_project_id, {
        "name": name,
        "kind": kind_v,
        "description": description,
        "first_episode": first_episode,
        "payoff_episode": payoff_episode,
        "status": "planted",
        "tags": list(tags or []),
    })


def record_beat(
    db: CanonDB,
    motif_id: int,
    episode_number: int,
    beat: str,
    notes: str = "",
) -> int:
    mid = db.add_motif_beat(motif_id, episode_number, beat, notes=notes)
    motif = db.get_motif(motif_id)
    if motif and motif.get("status") == "planted" and episode_number > int(
        motif.get("first_episode") or 1
    ):
        db.update_motif(motif_id, status="developing")
    return mid


def mark_payoff(db: CanonDB, motif_id: int, episode_number: int,
                notes: str = "") -> None:
    db.update_motif(motif_id, status="paid_off", payoff_episode=episode_number)
    db.add_motif_beat(motif_id, episode_number, "PAYOFF", notes=notes)


def arc_report(db: CanonDB, series_project_id: int) -> dict[str, Any]:
    """Snapshot of series spine: episodes + motifs + open loops."""
    series = db.get_project(series_project_id)
    episodes = db.episodes_for_series(series_project_id)
    motifs = db.motifs_for_series(series_project_id)
    detailed = []
    open_loops = []
    for m in motifs:
        beats = db.motif_beats(int(m["id"]))
        entry = {**m, "beats": beats}
        detailed.append(entry)
        if m.get("status") != "paid_off":
            open_loops.append({
                "id": m.get("id"),
                "name": m.get("name"),
                "kind": m.get("kind"),
                "status": m.get("status"),
                "first_episode": m.get("first_episode"),
                "planned_payoff": m.get("payoff_episode"),
                "beat_count": len(beats),
            })
    return {
        "series": {
            "id": series_project_id,
            "title": (series or {}).get("title"),
            "slug": (series or {}).get("slug"),
            "genre": (series or {}).get("genre"),
            "logline": (series or {}).get("logline"),
        },
        "episodes": episodes,
        "motifs": detailed,
        "open_loops": open_loops,
        "stats": {
            "episode_count": len(episodes),
            "motif_count": len(motifs),
            "open_loops": len(open_loops),
            "paid_off": sum(1 for m in motifs if m.get("status") == "paid_off"),
        },
    }


def plan_episode_spine(
    db: CanonDB,
    series_project_id: int,
    episode_number: int,
    *,
    brain: Optional[TextBrain] = None,
    logline_hint: str = "",
) -> dict[str, Any]:
    """Propose what this episode should plant/payoff based on open motifs.

    Offline-safe: deterministic plan when brain is mock.
    """
    report = arc_report(db, series_project_id)
    episodes = report["episodes"]
    ep = next((e for e in episodes if int(e.get("number", -1)) == episode_number), None)
    open_loops = report["open_loops"]
    due_payoffs = [
        m for m in open_loops
        if m.get("planned_payoff") is not None
        and int(m["planned_payoff"]) == episode_number
    ]
    active = [
        m for m in open_loops
        if m not in due_payoffs
        and int(m.get("first_episode") or 1) <= episode_number
    ]
    plant_slots = max(0, 2 - len(due_payoffs))

    plan = {
        "episode_number": episode_number,
        "episode_title": (ep or {}).get("title") or f"Episode {episode_number}",
        "logline_hint": logline_hint or (ep or {}).get("logline") or "",
        "must_payoff": due_payoffs,
        "develop": active[:4],
        "plant_budget": plant_slots,
        "suggested_cards": [],
        "brain_notes": "",
    }

    # Deterministic card suggestions
    cards = []
    for i, m in enumerate(due_payoffs):
        cards.append({
            "idx": i,
            "title": f"Payoff: {m['name']}",
            "what_happens": f"Resolve motif '{m['name']}' ({m['kind']}).",
            "structural_beat": "Midpoint" if episode_number > 1 else "Catalyst",
            "tags": ["payoff", m.get("kind") or "motif"],
            "plot_function": f"Pay off {m['name']}",
        })
    for j, m in enumerate(active[:2]):
        cards.append({
            "idx": len(cards),
            "title": f"Develop: {m['name']}",
            "what_happens": f"Advance motif '{m['name']}' without resolving it.",
            "structural_beat": "Fun and Games",
            "tags": ["develop", m.get("kind") or "motif"],
            "plot_function": f"Develop {m['name']}",
        })
    if plant_slots:
        cards.append({
            "idx": len(cards),
            "title": "Plant new motif",
            "what_happens": "Introduce a fresh visual/audio/character seed for later payoff.",
            "structural_beat": "Set-Up",
            "tags": ["plant"],
            "plot_function": "New series seed",
        })
    plan["suggested_cards"] = cards

    b = brain or get_brain(project_id=series_project_id)
    if hasattr(b, "with_context"):
        b = b.with_context(kind="arc", project_id=series_project_id)
    system = (
        "You are a showrunner planning one episode of a series. "
        "Be concrete. Return short prose (not JSON): 1) A-plot, 2) motif moves, "
        "3) cold open idea, 4) button."
    )
    user = (
        f"Series: {report['series']}\n"
        f"Episode #{episode_number} title={plan['episode_title']}\n"
        f"Hint: {plan['logline_hint']}\n"
        f"Must payoff: {due_payoffs}\n"
        f"Develop: {active[:4]}\n"
        f"Plant budget: {plant_slots}\n"
    )
    plan["model_view"] = {
        "kind": "arc",
        "system": system,
        "user": user,
        "brain": b.name,
        "would_call_llm": b.name != "mock",
    }
    if b.name != "mock":
        try:
            plan["brain_notes"] = b.complete(system, user)
        except Exception as exc:
            plan["brain_notes"] = f"(brain error: {exc})"
    else:
        plan["brain_notes"] = (
            f"[mock] Ep{episode_number}: pay off {len(due_payoffs)} motif(s), "
            f"develop {min(2, len(active))}, plant up to {plant_slots}. "
            "Cut on emotion; track open loops."
        )


    # Persist arc notes on the episode row if it exists
    if ep is not None:
        note = (
            f"payoffs={len(due_payoffs)}; develop={min(2, len(active))}; "
            f"plant={plant_slots}"
        )
        db.update_episode(
            series_project_id, episode_number,
            arc_notes=note,
            logline=logline_hint or ep.get("logline") or "",
        )

    return plan


def apply_plan_cards(
    db: CanonDB,
    child_project_id: int,
    plan: dict[str, Any],
    *,
    replace: bool = True,
) -> list[int]:
    """Write suggested cards from a plan onto an episode's child project board."""
    cards = []
    for c in plan.get("suggested_cards") or []:
        cards.append({
            "idx": int(c.get("idx", len(cards))),
            "slugline": c.get("slugline") or "INT. LOCATION - DAY",
            "title": c.get("title") or "",
            "what_happens": c.get("what_happens") or "",
            "relationship_delta": c.get("relationship_delta") or "",
            "plot_function": c.get("plot_function") or "",
            "emotional_spine": c.get("emotional_spine") or "",
            "characters": c.get("characters") or [],
            "structural_beat": c.get("structural_beat") or "",
            "act": c.get("act"),
            "tags": c.get("tags") or [],
            "meta": {"from_arc_plan": True},
        })
    if replace:
        return db.replace_project_cards(child_project_id, cards)
    return [db.add_project_card(child_project_id, c) for c in cards]
