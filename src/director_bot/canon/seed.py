"""Seed a small S-tier pocket corpus for offline demos and tests."""
from __future__ import annotations

from director_bot.canon.db import CanonDB
from director_bot.canon.import_export import import_work_bundle

# Hand-curated thriller micro-scenes — enough to prove lookup + decide.
SEED_BUNDLES: list[dict] = [
    {
        "work": {
            "slug": "interrogation-prototype",
            "title": "Interrogation Prototype (synthetic S-tier)",
            "year": 1995,
            "directors": ["David Fincher"],
            "genres": ["thriller", "crime"],
            "medium": "short",
            "tier": "S",
            "theme": "Power, confession, and the architecture of doubt",
            "logline": "A detective and a suspect trade silence for control under cold light.",
            "plot_summary": (
                "A two-hander interrogation that tightens through shot size "
                "and withheld reverse angles rather than exposition."
            ),
            "source": "seed:hand-labeled",
        },
        "scene_cards": [
            {
                "idx": 0,
                "slugline": "INT. INTERROGATION ROOM - NIGHT",
                "title": "The first silence",
                "what_happens": (
                    "DETECTIVE sits across from SUSPECT. File folder closed. "
                    "Neither speaks for a long beat."
                ),
                "relationship_delta": (
                    "Professional predator/prey; respect is still negotiable."
                ),
                "plot_function": "Establish power vacuum before accusation.",
                "emotional_spine": "Controlled menace under fluorescent calm.",
                "characters": ["DETECTIVE", "SUSPECT"],
                "structural_beat": "Catalyst",
                "act": 1,
                "tags": ["interrogation", "silence", "two-hander"],
            },
            {
                "idx": 1,
                "slugline": "INT. INTERROGATION ROOM - NIGHT",
                "title": "The reverse that never comes",
                "what_happens": (
                    "Detective opens the file. Suspect's eyes flick to it. "
                    "Camera stays on suspect — no reverse for three lines."
                ),
                "relationship_delta": "Suspect loses composure; detective gains leverage.",
                "plot_function": "First crack in the alibi without stating it.",
                "emotional_spine": "Claustrophobic exposure.",
                "characters": ["DETECTIVE", "SUSPECT"],
                "structural_beat": "Debate",
                "act": 1,
                "tags": ["withheld reverse", "pressure"],
            },
        ],
        "shot_moments": [
            {
                "idx": 0,
                "scene_idx": 0,
                "start_s": 0.0,
                "end_s": 8.0,
                "scale": "WS",
                "subject": "INTERROGATION ROOM",
                "angle": "HIGH ANGLE",
                "move": "STATIC",
                "int_ext": "INT.",
                "location": "INTERROGATION ROOM",
                "time_of_day": "NIGHT",
                "action_text": "Wide of the table. Two figures. File between them.",
                "characters": ["DETECTIVE", "SUSPECT"],
                "mood": "clinical, cold fluorescent",
                "dialogue": [],
            },
            {
                "idx": 1,
                "scene_idx": 0,
                "start_s": 8.0,
                "end_s": 16.0,
                "scale": "MCU",
                "subject": "SUSPECT",
                "angle": "EYE LEVEL",
                "move": "STATIC",
                "int_ext": "INT.",
                "location": "INTERROGATION ROOM",
                "time_of_day": "NIGHT",
                "action_text": "Hold on suspect's face through the silence.",
                "characters": ["SUSPECT"],
                "mood": "tight, observational",
                "dialogue": [],
            },
            {
                "idx": 2,
                "scene_idx": 1,
                "start_s": 16.0,
                "end_s": 24.0,
                "scale": "CU",
                "subject": "SUSPECT EYES",
                "angle": "EYE LEVEL",
                "move": "PUSH IN",
                "int_ext": "INT.",
                "location": "INTERROGATION ROOM",
                "time_of_day": "NIGHT",
                "action_text": "Slow push as detective speaks off-camera.",
                "characters": ["SUSPECT"],
                "mood": "invasive",
                "dialogue": [
                    {
                        "character": "DETECTIVE",
                        "text": "You left something out.",
                        "parenthetical": "quiet",
                    }
                ],
            },
        ],
        "decision_digests": [
            {
                "scene_idx": 0,
                "shot_idx": 1,
                "situation": (
                    "Two-hander interrogation; need to show power without dialogue."
                ),
                "decision": (
                    "Hold MCU on the silent party; withhold reverse angle on the speaker."
                ),
                "rationale": (
                    "The audience reads guilt/resistance in micro-expression; "
                    "coverage would dilute pressure."
                ),
                "director": "David Fincher",
                "tags": ["silence", "withheld reverse", "MCU hold"],
                "phase": "shotlist",
            },
            {
                "scene_idx": 1,
                "shot_idx": 2,
                "situation": (
                    "Accusation lands; suspect's composure begins to fracture."
                ),
                "decision": "CU push-in on eyes while detective remains off-screen.",
                "rationale": (
                    "Off-screen voice + optical pressure = psychological dominance."
                ),
                "director": "David Fincher",
                "tags": ["CU", "push in", "off-screen dialogue"],
                "phase": "shotlist",
            },
        ],
    },
    {
        "work": {
            "slug": "doorway-goodbye",
            "title": "Doorway Goodbye (synthetic S-tier)",
            "year": 2003,
            "directors": ["Sofia Coppola"],
            "genres": ["drama", "romance"],
            "medium": "short",
            "tier": "S",
            "theme": "Almost-connections and the poetry of near-misses",
            "logline": "Two people say everything by almost leaving.",
            "plot_summary": (
                "A quiet departure scene built from negative space, "
                "medium wides, and unfinished sentences."
            ),
            "source": "seed:hand-labeled",
        },
        "scene_cards": [
            {
                "idx": 0,
                "slugline": "INT. HOTEL CORRIDOR - DAWN",
                "title": "Almost",
                "what_happens": (
                    "SHE stands in the doorway. HE is already half-turned away. "
                    "Neither closes the distance."
                ),
                "relationship_delta": "Desire acknowledged; commitment refused.",
                "plot_function": "Emotional climax without plot explosion.",
                "emotional_spine": "Bittersweet restraint.",
                "characters": ["SHE", "HE"],
                "structural_beat": "Finale",
                "act": 3,
                "tags": ["doorway", "departure", "negative space"],
            },
        ],
        "shot_moments": [
            {
                "idx": 0,
                "scene_idx": 0,
                "scale": "MWS",
                "subject": "DOORWAY",
                "angle": "EYE LEVEL",
                "move": "STATIC",
                "int_ext": "INT.",
                "location": "HOTEL CORRIDOR",
                "time_of_day": "DAWN",
                "action_text": "Both in frame, separated by the threshold.",
                "characters": ["SHE", "HE"],
                "mood": "soft, pastel, lonely",
                "dialogue": [
                    {"character": "SHE", "text": "Will I see you?", "parenthetical": ""},
                    {"character": "HE", "text": "Maybe.", "parenthetical": "after a beat"},
                ],
            },
            {
                "idx": 1,
                "scene_idx": 0,
                "scale": "MS",
                "subject": "SHE",
                "angle": "EYE LEVEL",
                "move": "STATIC",
                "int_ext": "INT.",
                "location": "HOTEL CORRIDOR",
                "time_of_day": "DAWN",
                "action_text": "Hold on her after he exits frame. Empty corridor hum.",
                "characters": ["SHE"],
                "mood": "afterimage of intimacy",
                "dialogue": [],
            },
        ],
        "decision_digests": [
            {
                "scene_idx": 0,
                "shot_idx": 1,
                "situation": "Farewell; words would over-explain the subtext.",
                "decision": "Stay on the left-behind character after exit; no music swell.",
                "rationale": "The empty frame is the emotion; scoring would lie.",
                "director": "Sofia Coppola",
                "tags": ["hold after exit", "negative space", "quiet ending"],
                "phase": "shotlist",
            },
        ],
    },
]


def seed_demo_canon(db: CanonDB) -> list[int]:
    """Load SEED_BUNDLES; returns work ids."""
    ids: list[int] = []
    for bundle in SEED_BUNDLES:
        ids.append(import_work_bundle(db, bundle, replace_children=True))
    return ids
