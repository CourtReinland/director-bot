"""Typer CLI: `director-bot` / `dbot`."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from director_bot import envload as _envload  # noqa: F401 — load .env first
from director_bot import config
from director_bot.canon.db import CanonDB

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Director-bot — embodied AI film director (canon + soul + decisions).",
)
canon_app = typer.Typer(no_args_is_help=True, help="Canon corpus commands.")
project_app = typer.Typer(no_args_is_help=True, help="Live production projects.")
decide_app = typer.Typer(no_args_is_help=True, help="Decision engine.")
soul_app = typer.Typer(no_args_is_help=True, help="Soul / embodiment.")
app.add_typer(canon_app, name="canon")
app.add_typer(project_app, name="project")
app.add_typer(decide_app, name="decide")
app.add_typer(soul_app, name="soul")


def _db() -> CanonDB:
    return CanonDB(config.db_path())


def _fail(msg: str) -> typer.Exit:
    typer.echo(f"error: {msg}", err=True)
    return typer.Exit(code=1)


# --------------------------------------------------------------------------- #
# canon
# --------------------------------------------------------------------------- #

@canon_app.command("seed")
def canon_seed() -> None:
    """Load the built-in multi-genre pocket corpus and reindex embeddings."""
    from director_bot.canon.seed import seed_demo_canon

    db = _db()
    ids = seed_demo_canon(db)
    typer.echo(f"seeded {len(ids)} work(s): {ids}")
    typer.echo(f"db: {config.db_path()}")


@canon_app.command("import")
def canon_import(
    path: Path = typer.Argument(..., help="JSON work bundle or scripty export-canon file"),
) -> None:
    """Import a work bundle into the canon DB."""
    from director_bot.adapters.scripty import import_scripty_bundle_file
    from director_bot.canon.import_export import import_bundle_file

    db = _db()
    try:
        raw = json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise _fail(str(exc))
    try:
        if "project" in raw and "pass" in raw:
            wid = import_scripty_bundle_file(db, path)
        else:
            wid = import_bundle_file(db, path)
    except (ValueError, OSError) as exc:
        raise _fail(str(exc))
    work = db.get_work(wid)
    typer.echo(f"imported work {wid}: {work and work.get('title')}")


@canon_app.command("import-dir")
def canon_import_dir(
    directory: Path = typer.Argument(..., help="Directory of *.json bundles"),
) -> None:
    """Bulk-import all JSON work bundles in a directory."""
    from director_bot.adapters.scripty import import_scripty_bundle_file
    from director_bot.canon.import_export import import_bundle_file

    d = directory.expanduser().resolve()
    if not d.is_dir():
        raise _fail(f"not a directory: {d}")
    db = _db()
    paths = sorted(d.glob("*.json"))
    if not paths:
        raise _fail(f"no .json files in {d}")
    for p in paths:
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            if "project" in raw and "pass" in raw:
                wid = import_scripty_bundle_file(db, p)
            else:
                wid = import_bundle_file(db, p)
            work = db.get_work(wid)
            typer.echo(f"  {p.name} → work {wid} ({work and work.get('title')})")
        except Exception as exc:
            typer.echo(f"  {p.name} FAIL: {exc}", err=True)
    typer.echo(f"done ({len(paths)} files)")


@canon_app.command("tier")
def canon_tier(
    work_id: int,
    tier: str = typer.Argument(..., help="S|A|B|C|UNRANKED"),
) -> None:
    """Set a work's tier ranking."""
    tier_u = tier.strip().upper()
    if tier_u not in ("S", "A", "B", "C", "UNRANKED"):
        raise _fail("tier must be S|A|B|C|UNRANKED")
    db = _db()
    if db.get_work(work_id) is None:
        raise _fail(f"no work {work_id}")
    db.update_work(work_id, tier=tier_u)
    typer.echo(f"work {work_id} tier → {tier_u}")


@canon_app.command("annotate")
def canon_annotate(
    work_id: int,
    theme: Optional[str] = typer.Option(None, "--theme"),
    logline: Optional[str] = typer.Option(None, "--logline"),
    plot_summary: Optional[str] = typer.Option(None, "--plot-summary"),
    director: Optional[list[str]] = typer.Option(None, "--director"),
    genre: Optional[list[str]] = typer.Option(None, "--genre"),
) -> None:
    """Patch high-level work metadata (theme, directors, genres, …)."""
    db = _db()
    work = db.get_work(work_id)
    if work is None:
        raise _fail(f"no work {work_id}")
    fields: dict = {}
    if theme is not None:
        fields["theme"] = theme
    if logline is not None:
        fields["logline"] = logline
    if plot_summary is not None:
        fields["plot_summary"] = plot_summary
    if director is not None:
        fields["directors"] = list(director)
    if genre is not None:
        fields["genres"] = list(genre)
    if not fields:
        raise _fail("nothing to update — pass --theme/--logline/…")
    db.update_work(work_id, **fields)
    typer.echo(f"updated work {work_id}: {', '.join(fields)}")


@canon_app.command("digest")
def canon_digest(
    work_id: int,
    situation: str = typer.Option(..., "--situation"),
    decision: str = typer.Option(..., "--decision"),
    rationale: str = typer.Option("", "--rationale"),
    director: str = typer.Option("", "--director"),
    phase: str = typer.Option("shotlist", "--phase"),
    tag: Optional[list[str]] = typer.Option(None, "--tag"),
) -> None:
    """Add a hand-authored decision digest to a work."""
    from director_bot.canon.index import reindex

    db = _db()
    if db.get_work(work_id) is None:
        raise _fail(f"no work {work_id}")
    did = db.add_digest({
        "work_id": work_id,
        "situation": situation,
        "decision": decision,
        "rationale": rationale,
        "director": director,
        "phase": phase,
        "tags": list(tag or []),
    })
    reindex(db)
    typer.echo(f"digest {did} on work {work_id}")


@canon_app.command("reindex")
def canon_reindex() -> None:
    """Rebuild hashed embedding index for hybrid lookup."""
    from director_bot.canon.index import reindex

    counts = reindex(_db())
    typer.echo(f"reindexed: {counts}")


@canon_app.command("export")
def canon_export(
    work_id: int,
    out: Path = typer.Option(..., "--out", "-o", help="Output JSON path"),
) -> None:
    """Export a work bundle to JSON."""
    from director_bot.canon.import_export import export_work_bundle, save_bundle_file

    db = _db()
    try:
        bundle = export_work_bundle(db, work_id)
    except ValueError as exc:
        raise _fail(str(exc))
    path = save_bundle_file(bundle, out)
    typer.echo(f"wrote {path}")


@canon_app.command("list")
def canon_list(
    tier: Optional[str] = typer.Option(None, "--tier"),
    genre: Optional[str] = typer.Option(None, "--genre"),
) -> None:
    """List works in the canon."""
    db = _db()
    works = db.list_works(tier=tier, genre=genre)
    if not works:
        typer.echo("no works yet — try: director-bot canon seed")
        return
    for w in works:
        directors = ", ".join(w.get("directors") or []) or "—"
        genres = ", ".join(w.get("genres") or []) or "—"
        typer.echo(
            f"[{w['id']:>3}] {w.get('tier', '?')}  {w.get('title')}  "
            f"({directors})  [{genres}]"
        )


@canon_app.command("lookup")
def canon_lookup(
    query: str = typer.Argument(..., help="Situation text to search"),
    k: int = typer.Option(5, "--k"),
    kind: str = typer.Option("digest", "--kind", help="digest|moment|card"),
) -> None:
    """Semantic-ish lookup over digests, moments, or cards."""
    from director_bot.canon.query import lookup_cards, lookup_digests, lookup_moments

    db = _db()
    kind = kind.lower()
    if kind == "moment":
        hits = lookup_moments(db, query, k=k)
    elif kind == "card":
        hits = lookup_cards(db, query, k=k)
    else:
        hits = lookup_digests(db, query, k=k)
    if not hits:
        typer.echo("no hits")
        return
    for h in hits:
        score = h.get("score", 0)
        if kind == "digest":
            typer.echo(f"{score:.2f}  {h.get('decision')}")
            if h.get("rationale"):
                typer.echo(f"       {h.get('rationale')}")
        elif kind == "moment":
            typer.echo(
                f"{score:.2f}  {h.get('scale')} {h.get('subject')} — {h.get('action_text')}"
            )
        else:
            typer.echo(f"{score:.2f}  {h.get('slugline')} — {h.get('what_happens')[:80]}")


# --------------------------------------------------------------------------- #
# project
# --------------------------------------------------------------------------- #

@project_app.command("create")
def project_create(
    title: str = typer.Argument(...),
    genre: str = typer.Option("", "--genre"),
    logline: str = typer.Option("", "--logline"),
    slug: Optional[str] = typer.Option(None, "--slug"),
    medium: str = typer.Option("film", "--medium", help="film|series|episode|short"),
) -> None:
    """Create a live production project."""
    db = _db()
    pid = db.create_project(
        title, slug=slug, genre=genre, logline=logline, medium=medium,
    )
    proj = db.get_project(pid)
    typer.echo(
        f"created project {pid} ({proj and proj.get('slug')}) "
        f"phase=intake medium={medium}"
    )


@project_app.command("series")
def project_series(
    title: str = typer.Argument(..., help="Series title"),
    episode: Optional[list[str]] = typer.Option(
        None, "--episode", "-e", help="Episode title (repeatable)"),
    genre: str = typer.Option("", "--genre"),
    logline: str = typer.Option("", "--logline"),
) -> None:
    """Create a series project plus child episode projects."""
    from director_bot.project.workspace import create_series_with_episodes

    eps = list(episode or [])
    if not eps:
        eps = [f"{title} — Ep{i}" for i in range(1, 4)]
    db = _db()
    result = create_series_with_episodes(
        db, title, eps, genre=genre, logline=logline,
    )
    typer.echo(json.dumps(result, indent=2))


@project_app.command("cards-import")
def project_cards_import(
    project_id: int,
    path: Path = typer.Argument(..., help="LightWriter-style cards JSON"),
) -> None:
    """Import scene cards into a project board."""
    from director_bot.project.workspace import import_cards_file

    db = _db()
    if db.get_project(project_id) is None:
        raise _fail(f"no project {project_id}")
    try:
        ids = import_cards_file(db, project_id, path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise _fail(str(exc))
    typer.echo(f"imported {len(ids)} card(s) into project {project_id}")


@project_app.command("cards")
def project_cards_list(project_id: int) -> None:
    """List scene cards on a project board."""
    db = _db()
    cards = db.project_cards(project_id)
    if not cards:
        typer.echo("no cards — import with: project cards-import")
        return
    for c in cards:
        typer.echo(
            f"[{c.get('idx')}] {c.get('slugline') or c.get('title')} — "
            f"{str(c.get('what_happens') or '')[:70]}"
        )


@project_app.command("export")
def project_export(
    project_id: int,
    out: Optional[Path] = typer.Option(None, "--out", help="Output directory"),
) -> None:
    """Export LightWriter + Script2Screen handoff packages."""
    from director_bot.project.workspace import export_project_handoffs

    db = _db()
    try:
        paths = export_project_handoffs(db, project_id, out_dir=out)
    except ValueError as exc:
        raise _fail(str(exc))
    for k, v in paths.items():
        typer.echo(f"{k}: {v}")


@project_app.command("episodes")
def project_episodes(series_project_id: int) -> None:
    """List episodes for a series project."""
    db = _db()
    rows = db.episodes_for_series(series_project_id)
    if not rows:
        typer.echo("no episodes")
        return
    for e in rows:
        typer.echo(
            f"Ep{e.get('number')}: {e.get('title')}  "
            f"child_project={e.get('child_project_id')}"
        )


@project_app.command("motif")
def project_motif(
    series_id: int,
    name: str = typer.Argument(...),
    kind: str = typer.Option("visual", "--kind"),
    description: str = typer.Option("", "--description"),
    first: int = typer.Option(1, "--first"),
    payoff: Optional[int] = typer.Option(None, "--payoff"),
) -> None:
    """Add a series motif (plant/payoff tracking)."""
    from director_bot.project.arc import add_motif

    db = _db()
    mid = add_motif(
        db, series_id, name=name, kind=kind, description=description,
        first_episode=first, payoff_episode=payoff,
    )
    typer.echo(f"motif {mid}: {name} ({kind})")


@project_app.command("motif-beat")
def project_motif_beat(
    motif_id: int,
    episode: int = typer.Option(..., "--episode"),
    beat: str = typer.Argument(...),
    notes: str = typer.Option("", "--notes"),
    payoff: bool = typer.Option(False, "--payoff"),
) -> None:
    """Record a motif beat (or mark payoff)."""
    from director_bot.project.arc import mark_payoff, record_beat

    db = _db()
    if db.get_motif(motif_id) is None:
        raise _fail(f"no motif {motif_id}")
    if payoff:
        mark_payoff(db, motif_id, episode, notes=notes or beat)
        typer.echo(f"motif {motif_id} paid off in ep{episode}")
    else:
        bid = record_beat(db, motif_id, episode, beat, notes=notes)
        typer.echo(f"beat {bid} on motif {motif_id} ep{episode}")


@project_app.command("arc")
def project_arc(series_id: int) -> None:
    """Print series arc report (episodes + motifs + open loops)."""
    from director_bot.project.arc import arc_report

    db = _db()
    typer.echo(json.dumps(arc_report(db, series_id), indent=2, default=str))


@project_app.command("plan-ep")
def project_plan_ep(
    series_id: int,
    episode: int = typer.Argument(..., help="Episode number"),
    hint: str = typer.Option("", "--hint"),
    apply: bool = typer.Option(
        False, "--apply",
        help="Write suggested cards onto the episode child project"),
) -> None:
    """Plan one episode's spine from open motifs."""
    from director_bot.project.arc import apply_plan_cards, plan_episode_spine

    db = _db()
    plan = plan_episode_spine(db, series_id, episode, logline_hint=hint)
    if apply:
        eps = db.episodes_for_series(series_id)
        ep = next((e for e in eps if int(e.get("number", -1)) == episode), None)
        child = ep and ep.get("child_project_id")
        if not child:
            raise _fail("episode has no child_project_id — create series with project series")
        ids = apply_plan_cards(db, int(child), plan, replace=True)
        plan["applied_card_ids"] = ids
        plan["child_project_id"] = child
    typer.echo(json.dumps(plan, indent=2, default=str))


@project_app.command("list")
def project_list() -> None:
    db = _db()
    rows = db.list_projects()
    if not rows:
        typer.echo("no projects")
        return
    for p in rows:
        typer.echo(
            f"[{p['id']:>3}] {p.get('slug')}  phase={p.get('phase')}  "
            f"{p.get('title')}"
        )


@project_app.command("phase")
def project_phase(
    project_id: int,
    target: str = typer.Argument(..., help="Target phase name"),
) -> None:
    """Transition project mental process (enforces legal transitions)."""
    from director_bot.soul.steps import DirectorMind

    db = _db()
    if db.get_project(project_id) is None:
        raise _fail(f"no project {project_id}")
    mind = DirectorMind.create(db, project_id=project_id)
    try:
        new = mind.set_phase(target)
    except ValueError as exc:
        raise _fail(str(exc))
    typer.echo(f"project {project_id} → phase {new}")
    typer.echo(f"allowed next: {', '.join(mind.process.allowed())}")


@project_app.command("show")
def project_show(project_id: int) -> None:
    db = _db()
    p = db.get_project(project_id)
    if p is None:
        raise _fail(f"no project {project_id}")
    typer.echo(json.dumps(p, indent=2, default=str))


# --------------------------------------------------------------------------- #
# decide
# --------------------------------------------------------------------------- #

@decide_app.command("run")
def decide_run(
    summary: str = typer.Argument(..., help="Situation the director faces"),
    project_id: Optional[int] = typer.Option(None, "--project"),
    genre: str = typer.Option("", "--genre"),
    phase: Optional[str] = typer.Option(None, "--phase"),
    alpha: Optional[float] = typer.Option(None, "--alpha", help="Creativity blend 0..1"),
    no_commit: bool = typer.Option(False, "--no-commit"),
) -> None:
    """Run retrieve → propose → equilibrate → (optional) merkle commit."""
    from director_bot.contracts.schemas import ProjectPhase, SituationContext
    from director_bot.decisions.engine import decide

    db = _db()
    phase_name = phase or "shotlist"
    if project_id is not None:
        proj = db.get_project(project_id)
        if proj is None:
            raise _fail(f"no project {project_id}")
        phase_name = phase or str(proj.get("phase") or "shotlist")
        genre = genre or str(proj.get("genre") or "")
    try:
        p = ProjectPhase(phase_name)
    except ValueError:
        raise _fail(f"unknown phase {phase_name!r}")
    situation = SituationContext(
        phase=p, genre=genre, summary=summary,
    )
    result = decide(
        db, situation, project_id=project_id,
        creativity_alpha=alpha, commit=not no_commit,
    )
    chosen = result["chosen"]
    typer.echo(f"phase: {result['phase']}  α={result['creativity_alpha']:.2f}")
    typer.echo(f"chosen [{chosen.id}] ({chosen.style_source})")
    typer.echo(f"  {chosen.action}")
    if chosen.notes:
        typer.echo(f"  notes: {chosen.notes}")
    eq = result["equilibrium"]
    typer.echo(
        f"equilibrium: score={eq.get('chosen_score', 0):.3f}  "
        f"pareto={eq.get('n_pareto')}/{eq.get('n_candidates')}"
    )
    rec = result.get("decision")
    if rec is not None:
        typer.echo(f"ledger id={rec.id} hash={rec.content_hash[:16]}…")


@decide_app.command("chain")
def decide_chain(project_id: int) -> None:
    """Verify merkle chain for a project."""
    from director_bot.decisions.ledger import verify_chain

    db = _db()
    report = verify_chain(db, project_id)
    typer.echo(json.dumps(report, indent=2))


@decide_app.command("history")
def decide_history(project_id: int) -> None:
    db = _db()
    rows = db.decisions_for_project(project_id)
    if not rows:
        typer.echo("no decisions")
        return
    for r in rows:
        typer.echo(
            f"[{r['id']}] {r.get('phase')}  {str(r.get('chosen_action', ''))[:80]}  "
            f"#{str(r.get('content_hash', ''))[:12]}"
        )


@decide_app.command("agreement")
def decide_agreement(project_id: int) -> None:
    """Measure whether later auto-decisions honor human overrides."""
    from director_bot.decisions.agreement import agreement_metrics

    db = _db()
    report = agreement_metrics(db, project_id)
    typer.echo(json.dumps(report, indent=2))


@decide_app.command("override")
def decide_override(
    project_id: int,
    action: str = typer.Argument(..., help="The human-chosen action / coverage"),
    situation: str = typer.Option("", "--situation"),
    rationale: str = typer.Option("", "--rationale"),
    mint_digest: bool = typer.Option(
        False, "--mint-digest",
        help="Also add a DecisionDigest so future lookups can learn"),
    work_id: Optional[int] = typer.Option(None, "--work"),
    director: str = typer.Option("human", "--director"),
) -> None:
    """Record a human override on the merkle ledger (optionally mint digest)."""
    from director_bot.decisions.override import human_override
    from director_bot.decisions.ledger import verify_chain

    db = _db()
    try:
        result = human_override(
            db,
            project_id=project_id,
            action=action,
            situation=situation,
            rationale=rationale,
            mint_digest=mint_digest,
            work_id=work_id,
            director=director,
        )
    except ValueError as exc:
        raise _fail(str(exc))
    rec = result["decision"]
    typer.echo(f"override committed id={rec.id} hash={rec.content_hash[:16]}…")
    if result.get("digest_id") is not None:
        typer.echo(f"minted digest {result['digest_id']}")
    typer.echo(json.dumps(verify_chain(db, project_id), indent=2))


# --------------------------------------------------------------------------- #
# soul
# --------------------------------------------------------------------------- #

@soul_app.command("show")
def soul_show() -> None:
    """Print the loaded soul preamble."""
    from director_bot.soul.loader import load_soul

    soul = load_soul()
    typer.echo(soul.system_preamble())


@soul_app.command("meet")
def soul_meet(
    message: str = typer.Argument(..., help="What you say to the director"),
    project_id: Optional[int] = typer.Option(None, "--project"),
) -> None:
    """Creative meeting: speak with the director soul (mock brain offline)."""
    from director_bot.soul.steps import DirectorMind

    db = _db()
    mind = DirectorMind.create(db, project_id=project_id)
    mind.perceive(message)
    reply = mind.speak_about(message)
    typer.echo(f"[phase: {mind.process.phase}]")
    typer.echo(reply)


@soul_app.command("cycle")
def soul_cycle(
    summary: str = typer.Argument(...),
    project_id: Optional[int] = typer.Option(None, "--project"),
    genre: str = typer.Option("", "--genre"),
) -> None:
    """Full cognitive cycle: perceive → decide → remember."""
    from director_bot.soul.steps import DirectorMind, run_cognitive_cycle

    db = _db()
    mind = DirectorMind.create(db, project_id=project_id)
    result = run_cognitive_cycle(mind, summary=summary, genre=genre)
    chosen = result["chosen"]
    typer.echo(f"phase: {result['phase']}")
    typer.echo(f"chose: {chosen.action}")
    rec = result.get("decision")
    if rec is not None:
        typer.echo(f"hash: {rec.content_hash[:20]}…")


@app.command("demo")
def demo() -> None:
    """Seed canon, create a project, run one decision cycle (fully offline)."""
    from director_bot.canon.seed import seed_demo_canon
    from director_bot.contracts.schemas import ProjectPhase, SituationContext
    from director_bot.decisions.engine import decide
    from director_bot.decisions.ledger import verify_chain
    from director_bot.project.workspace import export_project_handoffs
    from director_bot.soul.steps import DirectorMind

    db = _db()
    ids = seed_demo_canon(db)
    pid = db.create_project(
        "Demo Short — The File",
        genre="thriller",
        logline="A detective and a suspect trade silence for control.",
    )
    # board cards
    db.replace_project_cards(pid, [
        {
            "idx": 0,
            "slugline": "INT. INTERROGATION ROOM - NIGHT",
            "title": "The file",
            "what_happens": "Detective and suspect. Silence. Closed file.",
            "relationship_delta": "Power vacuum.",
            "plot_function": "Catalyst",
            "emotional_spine": "Controlled menace",
            "characters": ["DETECTIVE", "SUSPECT"],
            "structural_beat": "Catalyst",
            "act": 1,
            "tags": ["interrogation"],
        },
    ])
    mind = DirectorMind.create(db, project_id=pid)
    # advance to shotlist legally
    for step in ("break_story", "write", "shotlist"):
        mind.set_phase(step)

    situation = SituationContext(
        phase=ProjectPhase.SHOTLIST,
        genre="thriller",
        summary=(
            "Interrogation room. Need to show power without dialogue. "
            "Suspect is silent; detective has a closed file."
        ),
        style_refs=["David Fincher"],
    )
    result = decide(db, situation, project_id=pid, commit=True)
    chain = verify_chain(db, pid)
    paths = export_project_handoffs(db, pid)
    typer.echo(f"seeded works: {ids}")
    typer.echo(f"project: {pid}")
    typer.echo(f"chose: {result['chosen'].action}")
    typer.echo(f"chain ok: {chain.get('ok')} length={chain.get('length')}")
    typer.echo(f"handoffs: {paths.get('root')}")
    typer.echo(f"db: {config.db_path()}")
    typer.echo("next: director-bot soul meet \"pitch me the opening\" --project "
               f"{pid}")


@app.command("serve")
def serve(
    port: int = typer.Option(8790, "--port"),
    host: str = typer.Option("127.0.0.1", "--host"),
) -> None:
    """Start the local dashboard (requires pip install -e '.[web]')."""
    try:
        import uvicorn
    except ImportError as exc:
        raise _fail("uvicorn missing — pip install -e '.[web]'") from exc
    from director_bot.server.app import create_app

    typer.echo(f"dashboard http://{host}:{port}/")
    uvicorn.run(create_app(), host=host, port=port)


@app.command("short")
def short_pipeline(
    title: str = typer.Option("Untitled Short", "--title"),
    genre: str = typer.Option("thriller", "--genre"),
    logline: str = typer.Option("", "--logline"),
    situation: str = typer.Option(
        "", "--situation",
        help="Decision situation for shotlist pass"),
    style: Optional[list[str]] = typer.Option(None, "--style", help="Director style ref"),
    no_seed: bool = typer.Option(False, "--no-seed"),
) -> None:
    """Vertical slice: seed/board/decide/export handoffs for a short."""
    from director_bot.pipeline import run_short_pipeline

    db = _db()
    sit = situation or (
        f"{genre} film. {logline or title}. "
        f"Opening scene decision: coverage, power, and subtext without wasting cuts."
    )
    result = run_short_pipeline(
        db,
        title=title,
        genre=genre,
        logline=logline or f"A {genre} short: {title}",
        situation=sit,
        style_refs=list(style or []),
        seed=not no_seed,
    )
    typer.echo(json.dumps({
        "project_id": result["project_id"],
        "cards": result["cards"],
        "chosen": result["chosen"],
        "decision_hash": result["decision_hash"],
        "chain_ok": result["chain"].get("ok"),
        "handoffs": result["handoffs"],
        "brain": result["brain"],
    }, indent=2))


@app.command("doctor")
def doctor() -> None:
    """Print paths and basic health."""
    from director_bot import __version__

    db_p = config.db_path()
    typer.echo(f"version={__version__}")
    typer.echo(f"DIRECTOR_BOT_HOME={config.home()}")
    typer.echo(f"db={db_p} exists={db_p.is_file()}")
    soul_dir = config.soul_static_dir()
    typer.echo(f"soul_dir={soul_dir} exists={soul_dir.is_dir()}")
    typer.echo(f"provider={config.default_provider()}")
    db = _db()
    n_emb = len(db.embeddings_of_type("digest")) + len(db.embeddings_of_type("moment"))
    from director_bot.canon.embed import get_embedder
    emb = get_embedder()
    typer.echo(
        f"works={len(db.list_works())} projects={len(db.list_projects())} "
        f"embedding_rows≈{n_emb} embedder={emb.name}"
    )
    # Show which key names are present without values
    keys = [k for k in ("XAI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                        "DIRECTOR_BOT_PROVIDER") if __import__("os").environ.get(k)]
    typer.echo(f"env_keys_present={keys}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
