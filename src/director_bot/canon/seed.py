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
    {
        "work": {
            "slug": "heist-elevator",
            "title": "Heist Elevator (synthetic S-tier)",
            "year": 2001,
            "directors": ["Steven Soderbergh"],
            "genres": ["heist", "crime", "thriller"],
            "medium": "short",
            "tier": "S",
            "theme": "Competence as romance; time as the antagonist",
            "logline": "Three thieves share an elevator ride that is also a clock.",
            "plot_summary": (
                "Cross-cut fragments and cool color blocks turn a simple "
                "elevator beat into a temporal puzzle."
            ),
            "source": "seed:hand-labeled",
        },
        "scene_cards": [
            {
                "idx": 0,
                "slugline": "INT. HOTEL ELEVATOR - DAY",
                "title": "Three strangers",
                "what_happens": (
                    "THREE THIEVES stand in an elevator, pretending not to know "
                    "each other. Floors tick. A suitcase between feet."
                ),
                "relationship_delta": "Team bonded by silence and timing.",
                "plot_function": "Plant the crew's discipline before the score.",
                "emotional_spine": "Cool tension.",
                "characters": ["THIEF A", "THIEF B", "THIEF C"],
                "structural_beat": "Fun and Games",
                "act": 2,
                "tags": ["elevator", "crew", "time pressure"],
            },
        ],
        "shot_moments": [
            {
                "idx": 0,
                "scene_idx": 0,
                "scale": "INSERT",
                "subject": "FLOOR NUMBERS",
                "angle": "EYE LEVEL",
                "move": "STATIC",
                "int_ext": "INT.",
                "location": "HOTEL ELEVATOR",
                "time_of_day": "DAY",
                "action_text": "Digital floor counter climbs. Cut on change.",
                "characters": [],
                "mood": "graphic, cool teal",
                "dialogue": [],
            },
            {
                "idx": 1,
                "scene_idx": 0,
                "scale": "CU",
                "subject": "SUITCASE HANDLE",
                "angle": "HIGH ANGLE",
                "move": "STATIC",
                "int_ext": "INT.",
                "location": "HOTEL ELEVATOR",
                "time_of_day": "DAY",
                "action_text": "Knuckles white on the handle; ring camera glint.",
                "characters": ["THIEF B"],
                "mood": "detail as character",
                "dialogue": [],
            },
        ],
        "decision_digests": [
            {
                "scene_idx": 0,
                "shot_idx": 0,
                "situation": "Need to make waiting feel like a countdown without score.",
                "decision": "Insert floor counter; cut on number change; no faces yet.",
                "rationale": "Time becomes the antagonist before dialogue admits it.",
                "director": "Steven Soderbergh",
                "tags": ["insert", "time", "graphic"],
                "phase": "shotlist",
            },
        ],
    },
    {
        "work": {
            "slug": "comedy-button",
            "title": "Comedy Button (synthetic A-tier)",
            "year": 2014,
            "directors": ["Edgar Wright"],
            "genres": ["comedy", "action"],
            "medium": "short",
            "tier": "A",
            "theme": "Rhythm is character",
            "logline": "A hero prepares to leave the apartment; every object gets a smash-cut button.",
            "plot_summary": "Match-cut comedy build through prop punctuation.",
            "source": "seed:hand-labeled",
        },
        "scene_cards": [
            {
                "idx": 0,
                "slugline": "INT. FLAT - DAY",
                "title": "Get ready",
                "what_happens": (
                    "HERO grabs keys, jacket, sunglasses in rhythmic smash cuts. "
                    "Door slam is the button."
                ),
                "relationship_delta": "Hero vs their own OCD competence.",
                "plot_function": "Establish visual grammar of the comedy.",
                "emotional_spine": "Caffeinated confidence.",
                "characters": ["HERO"],
                "structural_beat": "Set-Up",
                "act": 1,
                "tags": ["smash cut", "prop rhythm", "button"],
            },
        ],
        "shot_moments": [
            {
                "idx": 0,
                "scene_idx": 0,
                "scale": "CU",
                "subject": "KEYS",
                "angle": "EYE LEVEL",
                "move": "STATIC",
                "int_ext": "INT.",
                "location": "FLAT",
                "time_of_day": "DAY",
                "action_text": "Keys snatch from bowl — smash cut.",
                "characters": ["HERO"],
                "mood": "punchy, high contrast",
                "dialogue": [],
            },
            {
                "idx": 1,
                "scene_idx": 0,
                "scale": "MS",
                "subject": "DOOR SLAM",
                "angle": "EYE LEVEL",
                "move": "STATIC",
                "int_ext": "INT.",
                "location": "FLAT",
                "time_of_day": "DAY",
                "action_text": "Door fills frame and SLAMS — cut to black beat.",
                "characters": ["HERO"],
                "mood": "comic period",
                "dialogue": [],
            },
        ],
        "decision_digests": [
            {
                "scene_idx": 0,
                "shot_idx": 1,
                "situation": "Comedy exit; need a hard button not a fade.",
                "decision": "MS door slam as period; smash-cut rhythm on props before it.",
                "rationale": "Comedy is cutting; the door is the punchline.",
                "director": "Edgar Wright",
                "tags": ["smash cut", "button", "prop"],
                "phase": "shotlist",
            },
        ],
    },
    {
        "work": {
            "slug": "horror-threshold",
            "title": "Horror Threshold (synthetic S-tier)",
            "year": 2018,
            "directors": ["Ari Aster"],
            "genres": ["horror", "drama"],
            "medium": "short",
            "tier": "S",
            "theme": "Dread lives in architecture and delayed reveal",
            "logline": "A character opens a door they should not; the frame refuses to enter first.",
            "plot_summary": "Sound and negative space deliver horror before the monster.",
            "source": "seed:hand-labeled",
        },
        "scene_cards": [
            {
                "idx": 0,
                "slugline": "INT. BASEMENT STAIR - NIGHT",
                "title": "Don't",
                "what_happens": (
                    "THEY stand at the top of the stairs. Light switch fails. "
                    "Something shifts below. They still go down."
                ),
                "relationship_delta": "Curiosity overrules self-preservation.",
                "plot_function": "Commit to the nightmare.",
                "emotional_spine": "Slow dread.",
                "characters": ["THEY"],
                "structural_beat": "Break into Two",
                "act": 1,
                "tags": ["stairs", "threshold", "sound design"],
            },
        ],
        "shot_moments": [
            {
                "idx": 0,
                "scene_idx": 0,
                "scale": "WS",
                "subject": "STAIRWELL",
                "angle": "HIGH ANGLE",
                "move": "STATIC",
                "int_ext": "INT.",
                "location": "BASEMENT STAIR",
                "time_of_day": "NIGHT",
                "action_text": "Hold wide; subject small at top. Darkness below.",
                "characters": ["THEY"],
                "mood": "architectural dread",
                "dialogue": [],
            },
            {
                "idx": 1,
                "scene_idx": 0,
                "scale": "POV",
                "subject": "DESCENDING",
                "angle": "HIGH ANGLE",
                "move": "TRACKING",
                "int_ext": "INT.",
                "location": "BASEMENT STAIR",
                "time_of_day": "NIGHT",
                "action_text": "Slow track down with footsteps; withhold the landing.",
                "characters": ["THEY"],
                "mood": "subjective dread",
                "dialogue": [],
            },
        ],
        "decision_digests": [
            {
                "scene_idx": 0,
                "shot_idx": 0,
                "situation": "Horror entry; audience wants the scare early.",
                "decision": "Wide hold of architecture first; delay the reveal and the reverse.",
                "rationale": "Dread is spatial. Let the house be the antagonist.",
                "director": "Ari Aster",
                "tags": ["wide hold", "architecture", "delay"],
                "phase": "shotlist",
            },
        ],
    },
]


def seed_demo_canon(
    db: CanonDB,
    *,
    include_extra: bool = True,
    include_scale: bool = True,
) -> list[int]:
    """Load SEED_BUNDLES (+ extras + scale pockets); returns work ids.

    Rebuilds embedding index once at the end.
    """
    from director_bot.canon.index import reindex
    from director_bot.canon.seed_extra import EXTRA_BUNDLES
    from director_bot.canon.seed_scale import SCALE_BUNDLES

    ids: list[int] = []
    bundles = list(SEED_BUNDLES)
    if include_extra:
        bundles.extend(EXTRA_BUNDLES)
    if include_scale:
        bundles.extend(SCALE_BUNDLES)
    for bundle in bundles:
        ids.append(import_work_bundle(
            db, bundle, replace_children=True, reindex_after=False,
        ))
    reindex(db)
    return ids
