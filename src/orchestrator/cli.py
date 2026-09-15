"""`orch`: the operator's console. Nothing starts a campaign except a person typing here.

The commands split into three groups. **Preparation** (`doctor`, `brief`, `login`,
`probe`) checks the channels and the input. **Execution** (`start`, `resume`) is the only
way a request reaches a model, and always in the foreground, where it can be watched.
**Observation and control** (`status`, `watch`, `show`, `events`, `pause`, `unpause`,
`stop`, `approve-plan`, `reconcile`, `report`) reads the same state from another
terminal and can interrupt a run between steps.

There is no scheduler and no daemon. A run that ends does not start another one.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

from .briefs import BriefError, load_brief
from .engine import Engine, deadline_for
from .report import build_report
from .settings import ConfigError, load_settings
from .store import Store, state_root
from .util import read_json, short_id, utc_now, write_json_new

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "orchestrator" / "orchestrator.yaml"
LOCK_STALE_SECONDS = 120


# ------------------------------------------------------------------------ helpers

def _settings(args):
    path = Path(args.config) if getattr(args, "config", None) else DEFAULT_CONFIG
    if not path.exists():
        raise SystemExit(f"configurazione non trovata: {path}")
    return load_settings(path)


def _store(settings) -> Store:
    return Store(state_root(settings.state_root_override))


def _resolve_run(store: Store, run_id: str | None) -> str:
    resolved = run_id or store.latest_run_id()
    if not resolved:
        raise SystemExit("nessun run registrato")
    if store.run(resolved) is None:
        matches = [row["run_id"] for row in store.runs(200) if row["run_id"].startswith(resolved)]
        if len(matches) == 1:
            return matches[0]
        raise SystemExit(f"run sconosciuto: {resolved}")
    return resolved


def _lock_path(store: Store, run_id: str) -> Path:
    return store.run_dir(run_id) / "lock.json"


def _lock_is_live(store: Store, run_id: str) -> dict | None:
    path = _lock_path(store, run_id)
    if not path.exists():
        return None
    try:
        lock = read_json(path)
    except (json.JSONDecodeError, OSError):
        return None
    age = time.time() - float(lock.get("heartbeat_epoch", 0))
    return lock if age < LOCK_STALE_SECONDS else None


def _acquire_lock(store: Store, run_id: str, *, force: bool) -> Path:
    live = _lock_is_live(store, run_id)
    if live and not force:
        raise SystemExit(
            f"il run {run_id} risulta gia' in esecuzione (pid {live.get('pid')}, "
            f"heartbeat {live.get('heartbeat')}). Due processi sullo stesso run "
            f"invierebbero le stesse domande due volte. Usa --force solo se sei certo "
            f"che l'altro processo sia morto.")
    path = _lock_path(store, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"pid": os.getpid(), "started": utc_now(),
                                "heartbeat": utc_now(), "heartbeat_epoch": time.time()}),
                    encoding="utf-8")
    return path


def _heartbeat(path: Path) -> None:
    try:
        path.write_text(json.dumps({"pid": os.getpid(), "heartbeat": utc_now(),
                                    "heartbeat_epoch": time.time()}), encoding="utf-8")
    except OSError:
        pass


def _load_brief_for(settings, path, *, extra_roots=()) -> "object":
    roots = tuple(settings.allowed_roots) + tuple(Path(item).resolve() for item in extra_roots)
    return load_brief(path, allowed_roots=roots)


def _print_run_row(row) -> None:
    print(f"{row['run_id']}  {row['status']:<22} {row['brief_id']} v{row['brief_version']}  "
          f"percorso {row['route']:<10} {row['created_utc']}"
          + (f"  [{row['stop_reason']}]" if row["stop_reason"] else ""))


# ------------------------------------------------------------------------ commands

def cmd_doctor(args) -> int:
    print(f"repository        : {REPO_ROOT}")
    print(f"python            : {sys.version.split()[0]} ({sys.executable})")
    try:
        settings = _settings(args)
    except (ConfigError, SystemExit) as error:
        print(f"configurazione    : NON VALIDA — {error}")
        return 1
    print(f"configurazione    : {settings.path}")
    root = state_root(settings.state_root_override)
    print(f"stato dei run     : {root} "
          f"({'scrivibile' if os.access(root.parent, os.W_OK) else 'NON scrivibile'})")
    total, _used, free = shutil.disk_usage(root.drive or "C:")
    print(f"disco             : {free / 1024**3:.1f} GiB liberi su {total / 1024**3:.0f}")
    print(f"esecuzione codice : {settings.execution_policy} (nessun percorso di esecuzione)")
    print(f"radici consentite : "
          + (", ".join(str(item) for item in settings.allowed_roots) or "(solo la cartella dell'incarico)"))
    try:
        import playwright  # noqa: F401,PLC0415
        print("playwright        : presente")
    except ModuleNotFoundError:
        print("playwright        : ASSENTE — serve solo per gli adattatori web. "
              "Installalo con `pip install playwright` nell'ambiente dell'orchestratore.")

    store = _store(settings)
    print("\nservizi:")
    for service, config in sorted(settings.services.items()):
        try:
            from .adapters import build_adapter
            adapter = build_adapter(service, dict(config), state_root=store.root,
                                    config_dir=settings.config_dir)
            health = adapter.preflight()
            adapter.close()
            mark = "ok " if health.ok else "NO "
            print(f"  {mark}{service:<10} {config.get('adapter'):<10} {health.detail}")
        except Exception as error:  # noqa: BLE001 - doctor reports, never raises
            print(f"  NO {service:<10} {config.get('adapter', '?'):<10} {error}")
    store.close()
    return 0


def cmd_brief(args) -> int:
    settings = _settings(args)
    try:
        brief = _load_brief_for(settings, args.path)
    except BriefError as error:
        print(f"incarico non valido: {error}")
        return 1
    print(f"id                : {brief.brief_id}")
    print(f"versione          : {brief.version}")
    print(f"hash contenuto    : {brief.content_sha256[:16]}")
    print(f"modalita'         : {brief.mode}")
    print(f"percorso richiesto: {brief.route}")
    print(f"criteri           : {len(brief.acceptance_criteria)} "
          f"({sum(1 for c in brief.acceptance_criteria if c.is_automatic)} automatici, "
          f"{sum(1 for c in brief.acceptance_criteria if not c.is_automatic)} umani)")
    for criterion in brief.acceptance_criteria:
        print(f"  [{criterion.ident}] {criterion.kind:<9} {criterion.text}")
    print(f"materiali         : {len(brief.materials)}")
    for material in brief.materials:
        print(f"  {material.ident} {material.size_bytes} B  {material.path}")
    if brief.mode == "scientific_research":
        try:
            _print_research_brief(settings, brief)
        except BriefError as error:
            print(f"blocco research non valido: {error}")
            return 1
    if brief.subtasks:
        print(f"sottocompiti      : {len(brief.subtasks)} predichiarati")
    store = _store(settings)
    versions = store.brief_versions(brief.brief_id)
    if versions:
        print("versioni registrate:")
        for row in versions:
            same = "  <-- questo file" if row["sha256"] == brief.content_sha256 else ""
            print(f"  v{row['version']} {row['sha256'][:12]} {row['registered_utc']}{same}")
    store.close()
    return 0


def _print_research_brief(settings, brief) -> None:
    """Everything a research campaign will act on, printed before anyone is contacted.

    This is the screen the operator reads to decide whether to run it, so it shows the
    budget and the search policy as they will actually be enforced -- including whether
    each service can be made to search at all, which is read from the configuration and
    never assumed.
    """
    from .research.campaign import load_research_brief, search_capability

    research = load_research_brief(brief, settings)
    print(f"perimetro         : {research.scope}")
    if research.out_of_scope:
        print(f"fuori perimetro   : {research.out_of_scope}")
    print(f"criteri pertinenza: {len(research.relevance_criteria)}")
    for criterion in research.relevance_criteria:
        print(f"  [{criterion.ident}] {criterion.text}")
    print(f"ipotesi iniziali  : {len(research.hypotheses)}")
    for hypothesis in research.hypotheses:
        print(f"  [{hypothesis.ident}] {hypothesis.statement}")
    budget = research.budget
    print(f"budget            : {budget.max_phases} fasi, "
          f"{budget.max_main_responses} risposte principali, "
          f"{budget.max_total_interactions} interazioni totali (riparazioni e tentativi "
          f"compresi), {budget.max_leads} piste, {budget.max_wall_clock_minutes} minuti")
    print(f"assegnazione piste: {research.lead_assignment}")
    print(f"ricerca sul web   : richiesta={research.search.required}, "
          f"se non disponibile -> {research.search.on_unavailable}")
    route = settings.route_or_default(brief.route)
    for role in sorted(route.roles("solve")):
        service = settings.service_of(role)
        state = search_capability(settings, service, wanted=research.search.required)
        print(f"  {role} ({service}): {state.state}"
              + (f" via '{state.mode_name}'" if state.mode_name else ""))
        print(f"      {state.detail}")
    for role, perspective in sorted(research.perspectives.items()):
        print(f"  prospettiva {role}: {perspective}")


def cmd_start(args) -> int:
    settings = _settings(args)
    store = _store(settings)
    try:
        brief = _load_brief_for(settings, args.brief)
    except BriefError as error:
        print(f"incarico non valido: {error}")
        return 1
    try:
        version = store.register_brief(brief, bump=args.bump_version)
    except ValueError as error:
        print(f"versione: {error}")
        return 1

    route_name = args.route or brief.route or settings.default_route
    try:
        route = settings.route(route_name)
    except ConfigError as error:
        print(error)
        return 1

    run_id = f"{utc_now().replace(':', '').replace('-', '')}-{brief.brief_id[:24]}-v{version}-" \
             f"{short_id(brief.content_sha256, route.name, utc_now(), length=6)}"
    limits = settings.limits
    snapshot = {
        "run_id": run_id, "created_utc": utc_now(), "brief": {
            "id": brief.brief_id, "version": version, "sha256": brief.content_sha256,
            "title": brief.title, "source": str(brief.source_path),
            "materials": [{"id": m.ident, "path": str(m.path), "sha256": m.sha256,
                           "bytes": m.size_bytes} for m in brief.materials],
        },
        "route": route.name, "stages": {k: list(v) for k, v in route.stages.items()},
        "roles": settings.roles, "limits": limits.__dict__,
        "config": {"path": str(settings.path), "execution": settings.execution_policy,
                   "plan_approval": settings.plan_approval},
    }
    store.create_run(run_id=run_id, brief=brief, version=version, route=route.name,
                     label=args.label, deadline_utc=deadline_for(limits), snapshot=snapshot)
    print(f"run creato: {run_id}")
    return _drive(store, settings, brief, run_id, force=args.force,
                  allow_unverified=args.allow_unverified)


def cmd_resume(args) -> int:
    settings = _settings(args)
    store = _store(settings)
    run_id = _resolve_run(store, args.run)
    run = store.run(run_id)
    live = _lock_is_live(store, run_id)
    if live:
        store.request_control(run_id, "resume")
        print(f"il run {run_id} e' attivo (pid {live.get('pid')}): richiesta di ripresa inviata.")
        store.close()
        return 0
    snapshot = read_json(store.run_dir(run_id) / "run.json")
    brief_path = Path(snapshot["brief"]["source"])
    try:
        brief = _load_brief_for(settings, brief_path)
    except BriefError as error:
        print(f"incarico non piu' caricabile ({brief_path}): {error}")
        return 1
    if brief.content_sha256 != run["brief_sha256"]:
        print("ATTENZIONE: l'incarico su disco e' cambiato rispetto a quello con cui il run "
              "e' partito.\n"
              f"  registrato: {run['brief_sha256'][:16]}\n"
              f"  su disco  : {brief.content_sha256[:16]}\n"
              "Il run riparte con il testo attuale solo se lo confermi con --accept-drift; "
              "altrimenti avvia un run nuovo (nuova versione dell'incarico).")
        if not args.accept_drift:
            return 1
    return _drive(store, settings, brief, run_id, force=args.force,
                  allow_unverified=args.allow_unverified)


def _drive(store: Store, settings, brief, run_id: str, *, force: bool,
           allow_unverified: bool) -> int:
    lock = _acquire_lock(store, run_id, force=force)

    def log(message: str) -> None:
        print(message, flush=True)
        _heartbeat(lock)

    # Which loop this brief asks for. The two engines share their steps, their store and
    # their guards; what differs is the shape of the campaign and the report it writes.
    research_mode = getattr(brief, "mode", "debug") == "scientific_research"
    if research_mode:
        from .research import ResearchEngine

        engine = ResearchEngine(store, settings, brief, run_id, log=log,
                                allow_unverified_profiles=allow_unverified,
                                heartbeat=lambda: _heartbeat(lock))
    else:
        engine = Engine(store, settings, brief, run_id, log=log,
                        allow_unverified_profiles=allow_unverified,
                        heartbeat=lambda: _heartbeat(lock))
    try:
        status = engine.run()
    except KeyboardInterrupt:
        store.set_run_status(run_id, "paused")
        print("\n[interrotto da tastiera] lo stato e' salvato: `orch resume` riprende, "
              "`orch status` mostra dove eravamo.")
        status = "paused"
    finally:
        lock.unlink(missing_ok=True)
    print(f"[stato finale] {status}")
    # The research engine writes its own dossier and report as it closes, so there is
    # nothing to write here: a second one would be a second file saying the same thing.
    if status in ("finished", "stopped", "failed") and not research_mode:
        path = build_report(store, settings, brief, run_id)
        print(f"[rapporto] {path}")
    store.close()
    return 0 if status in ("finished", "awaiting_plan_approval") else 2


def cmd_runs(args) -> int:
    settings = _settings(args)
    store = _store(settings)
    for row in store.runs(args.limit):
        _print_run_row(row)
    store.close()
    return 0


def cmd_status(args) -> int:
    settings = _settings(args)
    store = _store(settings)
    run_id = _resolve_run(store, args.run)
    print(_status_text(store, run_id))
    store.close()
    return 0


def _status_text(store: Store, run_id: str) -> str:
    run = store.run(run_id)
    lines = [f"run        : {run_id}",
             f"incarico   : {run['brief_id']} v{run['brief_version']} "
             f"(sha {run['brief_sha256'][:12]})",
             f"stato      : {run['status']}"
             + (f" — {run['stop_reason']}" if run["stop_reason"] else ""),
             f"percorso   : {run['route']}",
             f"avvio      : {run['started_utc'] or '—'}   scadenza: {run['deadline_utc'] or '—'}"]
    live = _lock_is_live(store, run_id)
    lines.append(f"processo   : {'attivo, pid ' + str(live.get('pid')) if live else 'non attivo'}")
    pending = store.pending_control(run_id)
    if pending:
        lines.append(f"comando    : {pending['command']} richiesto {pending['requested_utc']}")

    lines.append("\nsottocompiti:")
    for row in store.subtasks(run_id):
        lines.append(f"  {row['subtask_id']:<4} {row['status']:<9} round {row['rounds_done']:<3}"
                     f" {row['title'][:56]}")
        if row["stop_detail"]:
            lines.append(f"       {row['stop_detail']}")

    steps = store.steps(run_id)
    if steps:
        last = steps[-1]
        lines.append(f"\nultimo passo: {last.stage}/{last.role} ({last.service}) round "
                     f"{last.round} — {last.status}"
                     + (f" [{last.error_kind}]" if last.error_kind else ""))
        lines.append(f"  cartella: {last.directory}")
    counts: dict[str, int] = {}
    for step in steps:
        counts[step.status] = counts.get(step.status, 0) + 1
    lines.append("passi      : " + ", ".join(f"{key} {value}" for key, value in sorted(counts.items())))

    objections = [row for row in store.findings(run_id, kind="objection")
                  if row["status"] in ("open", "resolved_claimed")]
    lines.append(f"obiezioni aperte: {len(objections)}")
    for row in objections[:5]:
        payload = json.loads(row["payload_json"])
        lines.append(f"  [{row['ident']}] ({payload.get('severity')}) "
                     f"{payload.get('text', '')[:90]}")
    return "\n".join(lines)


def cmd_watch(args) -> int:
    settings = _settings(args)
    store = _store(settings)
    run_id = _resolve_run(store, args.run)
    seen = 0
    try:
        while True:
            events = store.events(run_id, since=seen, limit=50)
            if events:
                seen = events[-1]["seq"]
            print("\033[2J\033[H", end="")
            print(_status_text(store, run_id))
            print("\nultimi eventi:")
            for row in store.events(run_id, since=max(0, seen - 12), limit=12):
                payload = json.loads(row["payload_json"])
                summary = ", ".join(f"{key}={value}" for key, value in payload.items()
                                    if key in ("role", "service", "status", "decision",
                                               "reason", "subtask", "round", "command"))
                print(f"  {row['utc']} {row['kind']:<18} {summary[:110]}")
            run = store.run(run_id)
            if run["status"] in ("finished", "stopped", "failed") and not _lock_is_live(store, run_id):
                print("\n[run concluso]")
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print()
    store.close()
    return 0


def cmd_show(args) -> int:
    settings = _settings(args)
    store = _store(settings)
    run_id = _resolve_run(store, args.run)
    steps = store.steps(run_id)
    if args.step:
        steps = [step for step in steps if step.step_id.startswith(args.step)]
    if args.subtask:
        steps = [step for step in steps if (step.subtask_id or "") == args.subtask]
    if args.round:
        steps = [step for step in steps if step.round == args.round]

    if args.diff:
        for row in store.subtasks(run_id):
            if args.subtask and row["subtask_id"] != args.subtask:
                continue
            for round_row in store.rounds(run_id, row["subtask_id"]):
                if args.round and round_row["round"] != args.round:
                    continue
                delta = json.loads(round_row["delta_json"] or "{}")
                print(f"\n=== {row['subtask_id']} round {round_row['round']} — "
                      f"{round_row['decision']} ({round_row['reason']}) ===")
                for role, entry in (delta.get("roles") or {}).items():
                    print(f"\n-- {role}: somiglianza con il proprio round precedente "
                          f"{entry.get('self_similarity', '—')}; nuove evidenze "
                          f"{len(entry.get('new_evidence', []))}; nuove obiezioni "
                          f"{len(entry.get('new_objections', []))}")
                    if entry.get("diff"):
                        print(entry["diff"])
        store.close()
        return 0

    for step in steps:
        print(f"\n=== {step.stage}/{step.role} ({step.service}) round {step.round} — "
              f"{step.status} — {step.step_id}")
        print(f"    {step.directory}")
        if args.prompt:
            print("--- prompt ---")
            print((step.path / "prompt.txt").read_text(encoding="utf-8"))
        if args.raw:
            print("--- risposta grezza ---")
            print(store.reply_text(step) or "(nessuna)")
        elif step.status == "answered":
            parsed = store.parsed_reply(step) or {}
            print(f"--- sintesi: {parsed.get('summary', '')}")
            print(f"--- proposta ({len(parsed.get('proposal', ''))} caratteri):")
            print(parsed.get("proposal", "")[:1500])
    store.close()
    return 0


def cmd_events(args) -> int:
    settings = _settings(args)
    store = _store(settings)
    run_id = _resolve_run(store, args.run)
    for row in store.events(run_id, since=args.since, limit=args.limit):
        print(f"{row['seq']:>5} {row['utc']} {row['kind']:<20} {row['payload_json'][:200]}")
    store.close()
    return 0


def _control(args, command: str) -> int:
    settings = _settings(args)
    store = _store(settings)
    run_id = _resolve_run(store, args.run)
    store.request_control(run_id, command, getattr(args, "note", None))
    live = _lock_is_live(store, run_id)
    if command == "stop" and not live:
        # Nobody is driving this run, so nobody will pick the command up. Close it here,
        # otherwise it stays 'running' for ever and the listing lies about what happened.
        store.acknowledge_control(run_id)
        store.set_run_status(run_id, "stopped", reason="human_stop",
                             detail="fermato dall'operatore su un run senza processo attivo")
        print(f"il run {run_id} non era in esecuzione: segnato come fermato.")
        store.close()
        return 0
    print(f"richiesta «{command}» registrata per {run_id}"
          + ("; il processo attivo la prendera' fra un passo e l'altro."
             if live else "; nessun processo attivo, avra' effetto alla prossima ripresa."))
    store.close()
    return 0


def cmd_approve_plan(args) -> int:
    settings = _settings(args)
    store = _store(settings)
    run_id = _resolve_run(store, args.run)
    directory = store.run_dir(run_id)
    source = Path(args.file) if args.file else directory / "plan.json"
    if not source.exists():
        print(f"nessun piano da approvare in {source}")
        return 1
    plan = read_json(source)
    target = directory / "plan.approved.json"
    if target.exists():
        print(f"un piano approvato esiste gia': {target}")
        return 1
    plan["approved_utc"] = utc_now()
    plan["approved_from"] = str(source)
    write_json_new(target, plan)
    store.event(run_id, "plan_approved", {"path": str(target),
                                          "subtasks": len(plan.get("subtasks", []))})
    store.request_control(run_id, "approve_plan")
    print(f"piano approvato ({len(plan.get('subtasks', []))} sottocompiti): {target}\n"
          f"riprendi con: orch resume {run_id}")
    store.close()
    return 0


def _recoverable_steps(store: Store, run_id: str) -> list:
    """Steps whose answer may exist in the service even though we do not have it.

    Two situations, and both end with a question sitting in a real conversation:

    * `dispatched` -- the process died in flight, so we cannot even prove it was sent;
    * `abandoned` **after** the send -- it was sent, we waited, and nothing readable came
      back. That is the one this command used to ignore, and it is the common one: the
      run of 2026-09-14 gave up on a DeepSeek answer that was complete on screen, because
      the interface had pruned an older message and the adapter was counting messages
      rather than watching the last one. The answer was recoverable from the HTML the
      adapter itself had saved; the command that exists to recover it refused to look.

    A step abandoned *before* any send is not here: there is nothing to acquire.
    """
    return [step for step in store.steps(run_id)
            if step.status == "dispatched"
            or (step.status == "abandoned" and step.dispatched_utc
                and step.error_kind != "reconciled")]


def cmd_reconcile(args) -> int:
    """Close a step whose answer we never read -- never by guessing what it said."""
    settings = _settings(args)
    store = _store(settings)
    run_id = _resolve_run(store, args.run)
    stranded = _recoverable_steps(store, run_id)
    if not stranded:
        print("nessun passo da riconciliare.")
        store.close()
        return 0
    for step in stranded:
        print(f"{step.step_id}  {step.stage}/{step.role} ({step.service}) round {step.round}"
              f"  [{step.status}{'/' + step.error_kind if step.error_kind else ''}]")
        print(f"  inviato {step.dispatched_utc}, cartella {step.directory}")
        dumps = sorted(Path(step.directory).glob("*.html"))
        if dumps:
            print(f"  l'adattatore aveva salvato la pagina: {', '.join(d.name for d in dumps)}")
    if not args.step:
        print("\nGuarda la conversazione nel servizio: se la risposta c'e', salvala in un "
              "file e usa --step <id> --reply-file <file>; se la domanda non e' mai "
              "arrivata, usa --step <id> --abandon e alla ripresa verra' rifatta.")
        store.close()
        return 0
    target = next((step for step in stranded if step.step_id.startswith(args.step)), None)
    if target is None:
        print(f"passo {args.step} non e' fra quelli in sospeso")
        return 1
    if args.abandon:
        store.settle_step(target.step_id, "abandoned", error_kind="reconciled",
                          error_detail="l'operatore ha dichiarato che la domanda non e' arrivata")
        print("passo marcato come abbandonato; alla ripresa verra' rifatto.")
    elif args.reply_file:
        text = Path(args.reply_file).read_text(encoding="utf-8")
        # Read under the contract this campaign actually used. A research reply checked
        # against the debugging contract is filed as unreadable, which is how a perfectly
        # good answer would be lost a second time, by the command meant to save it.
        snapshot = read_json(store.run_dir(run_id) / "run.json")
        try:
            brief = _load_brief_for(settings, snapshot["brief"]["source"])
            mode = getattr(brief, "mode", "debug")
        except (BriefError, OSError, KeyError):
            mode = "debug"
        if (target.path / "response.raw.txt").exists():
            print(f"c'e' gia' una risposta registrata in {target.path}: non la sovrascrivo. "
                  f"Se quella e' sbagliata, la correzione e' un run nuovo, non una "
                  f"riscrittura dell'evidenza.")
            store.close()
            return 1
        store.save_reply(target, text, meta={"channel": "reconciled", "by": "operator",
                                             "source_file": str(args.reply_file),
                                             "contract": mode,
                                             "previous_status": target.status,
                                             "previous_error": target.error_detail or ""})
        from .protocol import ContentProblem, parse_reply
        try:
            if mode == "scientific_research":
                from .research.contract import parse_research_reply
                from .protocol import ParsedReply

                record = parse_research_reply(text)
                parsed = ParsedReply(raw=text, summary=record.summary,
                                     proposal=record.synthesis,
                                     open_questions=record.open_questions,
                                     dropped_keys=record.dropped_keys,
                                     issues=record.issues,
                                     confidence=record.confidence, research=record)
            else:
                parsed = parse_reply(text)
            write_json_new(target.path / "response.parsed.json", parsed.as_record())
            # The original failure stays in the record: the step is answered *now*, and
            # why it was not answered then is part of what happened.
            store.settle_step(
                target.step_id, "answered", error_kind="reconciled",
                error_detail=(f"acquisita a mano dall'operatore da {args.reply_file}. "
                              f"Stato precedente: {target.status}"
                              + (f" ({target.error_detail})" if target.error_detail else ""))[:2000])
            print(f"risposta acquisita e conforme al contratto ({mode}).")
            print("Rigenera il rapporto con `orch report` perche' la includa.")
        except ContentProblem as problem:
            store.settle_step(target.step_id, "unparsed", error_kind=problem.kind,
                              error_detail=problem.detail)
            print(f"risposta acquisita ma non conforme ({problem.kind}: {problem.detail}).")
    else:
        print("serve --abandon oppure --reply-file")
        return 1
    store.close()
    return 0


def cmd_report(args) -> int:
    settings = _settings(args)
    store = _store(settings)
    run_id = _resolve_run(store, args.run)
    snapshot = read_json(store.run_dir(run_id) / "run.json")
    brief = _load_brief_for(settings, snapshot["brief"]["source"])
    if getattr(brief, "mode", "debug") == "scientific_research":
        from .research.engine import research_report

        path = research_report(store, settings, brief, run_id)
    else:
        path = build_report(store, settings, brief, run_id)
    print(path)
    store.close()
    return 0


def _web_adapter(settings, store, service: str, *, for_a_person: bool = False):
    from .adapters import build_adapter
    config = dict(settings.service_config(service))
    config["allow_unverified"] = True          # login and probe must work before verification
    if for_a_person:
        config["enable_translate"] = True      # the operator has to be able to read the page
    adapter = build_adapter(service, config, state_root=store.root,
                            config_dir=settings.config_dir)
    if adapter.name != "web":
        raise SystemExit(f"il servizio {service} non usa un adattatore web")
    return adapter


def cmd_login(args) -> int:
    """Open the dedicated profile so a person can sign in. Nothing is typed for them."""
    settings = _settings(args)
    store = _store(settings)
    adapter = _web_adapter(settings, store, args.service, for_a_person=True)
    for line in (
        f"Apro {adapter.url} nel profilo {adapter.user_data_dir}.",
        "  1. accedi a mano nella finestra;",
        "  2. chiudi tu il banner dei cookie: l'orchestratore non accetta condizioni al",
        "     posto tuo (se non ti serve, «solo cookie necessari»);",
        "  3. manda un messaggio qualsiasi, anche solo «ciao»: serve una risposta a",
        "     schermo per riconoscere il selettore dei messaggi con `orch probe`.",
        "Nessun token viene letto o salvato: la sessione resta nel profilo del browser.",
    ):
        print(line)
    adapter.open()
    if sys.stdin.isatty():
        try:
            input("premi Invio quando hai finito... ")
        except (EOFError, KeyboardInterrupt):
            pass
    else:
        # Without a terminal, input() returns immediately and the window would shut in the
        # operator's face. Hold it open instead, and say for how long.
        print(f"(nessun terminale interattivo: tengo la finestra aperta {args.minutes} "
              f"minuti, poi la chiudo)", flush=True)
        deadline = time.time() + args.minutes * 60
        while time.time() < deadline:
            time.sleep(5)
    adapter.close()
    store.close()
    return 0


def cmd_probe(args) -> int:
    settings = _settings(args)
    store = _store(settings)
    adapter = _web_adapter(settings, store, args.service)
    out_dir = store.root / "probes"
    print(f"apro {adapter.url} e guardo la pagina (non invio nulla)...")
    path = adapter.probe(out_dir, url=getattr(args, "url", None))
    adapter.close()
    print(f"scritto {path}\n"
          f"Compila i selettori in {settings.config_dir / 'services'} e metti "
          f"`verified: true` con la data, solo dopo averli visti funzionare.")
    store.close()
    return 0


# --------------------------------------------------------------------------- main

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orch", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", help=f"configurazione (default {DEFAULT_CONFIG})")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="controlla ambiente, canali e permessi").set_defaults(
        func=cmd_doctor)

    brief = sub.add_parser("brief", help="valida e mostra un incarico")
    brief.add_argument("path")
    brief.set_defaults(func=cmd_brief)

    start = sub.add_parser("start", help="avvia una nuova esecuzione (solo tu puoi farlo)")
    start.add_argument("--brief", required=True)
    start.add_argument("--route")
    start.add_argument("--label")
    start.add_argument("--bump-version", action="store_true",
                       help="registra una nuova versione se l'incarico e' cambiato")
    start.add_argument("--allow-unverified", action="store_true",
                       help="consente adattatori web con profilo non verificato")
    start.add_argument("--force", action="store_true", help="ignora un lock non aggiornato")
    start.set_defaults(func=cmd_start)

    resume = sub.add_parser("resume", help="riprende un run interrotto, o toglie la pausa")
    resume.add_argument("run", nargs="?")
    resume.add_argument("--allow-unverified", action="store_true")
    resume.add_argument("--accept-drift", action="store_true",
                        help="riprende anche se l'incarico su disco e' cambiato")
    resume.add_argument("--force", action="store_true")
    resume.set_defaults(func=cmd_resume)

    runs = sub.add_parser("runs", help="elenca le esecuzioni")
    runs.add_argument("--limit", type=int, default=20)
    runs.set_defaults(func=cmd_runs)

    status = sub.add_parser("status", help="stato di un run")
    status.add_argument("run", nargs="?")
    status.set_defaults(func=cmd_status)

    watch = sub.add_parser("watch", help="stato aggiornato in continuo (sola lettura)")
    watch.add_argument("run", nargs="?")
    watch.add_argument("--interval", type=float, default=4.0)
    watch.set_defaults(func=cmd_watch)

    show = sub.add_parser("show", help="input e output originali, e cosa e' cambiato")
    show.add_argument("run", nargs="?")
    show.add_argument("--step")
    show.add_argument("--subtask")
    show.add_argument("--round", type=int)
    show.add_argument("--prompt", action="store_true")
    show.add_argument("--raw", action="store_true")
    show.add_argument("--diff", action="store_true",
                      help="mostra il confronto con il round precedente")
    show.set_defaults(func=cmd_show)

    events = sub.add_parser("events", help="registro eventi")
    events.add_argument("run", nargs="?")
    events.add_argument("--since", type=int, default=0)
    events.add_argument("--limit", type=int, default=100)
    events.set_defaults(func=cmd_events)

    for name, helptext in (("pause", "sospende fra un passo e l'altro"),
                           ("unpause", "toglie la pausa"),
                           ("stop", "ferma in modo controllato"),
                           ("skip", "rinuncia al passo in attesa e prosegue senza")):
        control = sub.add_parser(name, help=helptext)
        control.add_argument("run", nargs="?")
        control.add_argument("--note")
        command = {"pause": "pause", "unpause": "resume", "stop": "stop",
                   "skip": "skip_step"}[name]
        control.set_defaults(func=lambda args, command=command: _control(args, command))

    approve = sub.add_parser("approve-plan", help="congela il piano dei sottocompiti")
    approve.add_argument("run", nargs="?")
    approve.add_argument("--file", help="usa questo file invece di plan.json")
    approve.set_defaults(func=cmd_approve_plan)

    reconcile = sub.add_parser("reconcile", help="chiude un passo rimasto in volo")
    reconcile.add_argument("run", nargs="?")
    reconcile.add_argument("--step")
    reconcile.add_argument("--abandon", action="store_true")
    reconcile.add_argument("--reply-file")
    reconcile.set_defaults(func=cmd_reconcile)

    report = sub.add_parser("report", help="(ri)genera il rapporto finale")
    report.add_argument("run", nargs="?")
    report.set_defaults(func=cmd_report)

    login = sub.add_parser("login", help="apre il profilo del browser per accedere a mano")
    login.add_argument("service")
    login.add_argument("--minutes", type=int, default=15,
                       help="quanto tenere aperta la finestra senza un terminale interattivo")
    login.set_defaults(func=cmd_login)

    probe = sub.add_parser("probe", help="guarda la pagina e scrive i selettori candidati")
    probe.add_argument("service")
    probe.add_argument("--url", help="guarda questa pagina invece della home del servizio "
                                     "(per esempio una conversazione con una risposta)")
    probe.set_defaults(func=cmd_probe)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as error:
        print(f"configurazione: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
