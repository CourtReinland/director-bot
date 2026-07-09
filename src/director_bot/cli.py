"""Typer CLI: `director-bot` / `dbot`."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

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
    """Load the built-in S-tier pocket corpus (thriller + drama micro-scenes)."""
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
) -> None:
    """Create a live production project."""
    db = _db()
    pid = db.create_project(title, slug=slug, genre=genre, logline=logline)
    proj = db.get_project(pid)
    typer.echo(f"created project {pid} ({proj and proj.get('slug')}) phase=intake")


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
    from director_bot.soul.steps import DirectorMind

    db = _db()
    ids = seed_demo_canon(db)
    pid = db.create_project(
        "Demo Short — The File",
        genre="thriller",
        logline="A detective and a suspect trade silence for control.",
    )
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
    typer.echo(f"seeded works: {ids}")
    typer.echo(f"project: {pid}")
    typer.echo(f"chose: {result['chosen'].action}")
    typer.echo(f"chain ok: {chain.get('ok')} length={chain.get('length')}")
    typer.echo(f"db: {config.db_path()}")
    typer.echo("next: director-bot soul meet \"pitch me the opening\" --project "
               f"{pid}")


@app.command("doctor")
def doctor() -> None:
    """Print paths and basic health."""
    db_p = config.db_path()
    typer.echo(f"DIRECTOR_BOT_HOME={config.home()}")
    typer.echo(f"db={db_p} exists={db_p.is_file()}")
    typer.echo(f"soul_dir={config.SOUL_STATIC_DIR} exists={config.SOUL_STATIC_DIR.is_dir()}")
    typer.echo(f"provider={config.default_provider()}")
    db = _db()
    typer.echo(f"works={len(db.list_works())} projects={len(db.list_projects())}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
