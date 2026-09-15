"""The final report: result, evidence, checks actually run, disagreements, and limits.

Two rules shape it. It keeps the **verbatim** answers and points at their files instead
of paraphrasing them again -- a chain of summaries is where a caveat quietly disappears,
which is the documented failure mode of this project. And it never lets a convergence
read as a verification: the two have different headings and different words.

The report is written once per run, to a fresh file. A later run writes a new one.
"""

from __future__ import annotations

import json
from pathlib import Path

from .briefs import Brief
from .convergence import Decision
from .protocol import parse_reply, ContentProblem
from .settings import Settings
from .store import Store
from .util import clip, similarity, unified_diff, utc_now, write_new

_DECISION_WORDS = {
    "verified_complete": "completamento verificato",
    "proposals_converged": "convergenza delle proposte (validazione mancante)",
    "stagnation": "stagnazione",
    "unresolved_disagreement": "disaccordo irrisolto",
    "limit_reached": "limite raggiunto",
    "service_unavailable": "servizio non disponibile",
    "human_stop": "arresto richiesto dall'operatore",
    "continue": "in corso",
}

_EVIDENCE_WORDS = {
    "measured": "misurata", "cited": "citata", "derived": "dedotta", "assumed": "assunta",
}


def _table(header: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_(nessuna)_\n"
    lines = ["| " + " | ".join(header) + " |",
             "|" + "|".join("---" for _ in header) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(cell.replace("|", "\\|").replace("\n", " ")
                                       for cell in row) + " |")
    return "\n".join(lines) + "\n"


def build_report(store: Store, settings: Settings, brief: Brief, run_id: str) -> Path:
    run = store.run(run_id)
    if run is None:
        raise ValueError(f"unknown run {run_id}")
    directory = store.run_dir(run_id)
    subtasks = store.subtasks(run_id)
    steps = store.steps(run_id)
    out: list[str] = []

    out.append(f"# Rapporto — {brief.title}\n")
    out.append(
        f"- **Run:** `{run_id}`\n"
        f"- **Incarico:** `{brief.brief_id}` versione {run['brief_version']} "
        f"(sha256 `{run['brief_sha256'][:16]}`)\n"
        f"- **Percorso:** `{run['route']}`\n"
        f"- **Stato:** {run['status']}"
        + (f" — {run['stop_reason']}" if run["stop_reason"] else "") + "\n"
        f"- **Avvio:** {run['started_utc'] or '—'} · **Fine:** {run['ended_utc'] or '—'}\n"
        f"- **Rapporto generato:** {utc_now()}\n"
        f"- **Risposte originali:** `{directory / 'steps'}` (una cartella per passo, "
        f"con `prompt.txt` e `response.raw.txt`)\n")

    out.append("\n> Questo rapporto conserva le risposte verbatim e ci punta. "
               "Dove dice «convergenza» non dice «corretto»: sono due esiti diversi, "
               "e solo il primo elenco della sezione 3 costituisce verifica.\n")

    # ---------------------------------------------------------------- 1. esito
    out.append("\n## 1. Esito\n")
    for subtask in subtasks:
        decision = subtask["stop_reason"] or "continue"
        out.append(f"\n### {subtask['subtask_id']} — {subtask['title']}\n")
        out.append(f"- **Esito:** {_DECISION_WORDS.get(decision, decision)}\n"
                   f"- **Round eseguiti:** {subtask['rounds_done']}\n"
                   f"- **Percorso:** `{subtask['route']}`\n")
        if subtask["stop_detail"]:
            out.append(f"- **Motivo:** {subtask['stop_detail']}\n")
        finals: dict[str, str] = {}
        final_services: dict[str, str] = {}
        for step in _final_steps(store, run_id, subtask["subtask_id"]):
            raw = store.reply_text(step) or ""
            try:
                parsed = parse_reply(raw)
                proposal, changes = parsed.proposal, parsed.changes
            except ContentProblem:
                proposal, changes = raw, ()
            finals[step.role] = proposal
            final_services[step.role] = step.service
            out.append(f"\n**Proposta finale di {step.role} ({step.service}), round "
                       f"{step.round}** — file: `{step.path / 'response.raw.txt'}`\n")
            out.append("\n" + clip(proposal, 6000) + "\n")
            if changes:
                out.append("\nModifiche che dichiara di aver fatto nell'ultimo round:\n")
                out.append("".join(f"- {clip(item, 300)}\n" for item in changes))

        covered = _stand_in_rounds(store, settings, run_id, subtask["subtask_id"])
        if covered:
            out.append(
                "\n> **Round coperti da una sessione di riserva:** "
                + "; ".join(f"round {number}, il ruolo {role} tenuto da `{used}` "
                            f"al posto di `{missing}`"
                            for number, role, missing, used in covered)
                + ". In quei round hanno risposto due sessioni dello stesso modello: "
                  "un accordo fra loro e' un modello che concorda con se stesso, e non "
                  "vale quanto un accordo fra modelli diversi.\n")

        if len(finals) == 2:
            # What still separates the two answers, shown rather than characterised: the
            # word "convergenza" above is a number, and this is the text behind it.
            (left, left_text), (right, right_text) = sorted(finals.items())
            out.append(f"\n**Differenze fra le due proposte finali** "
                       f"(somiglianza testuale {similarity(left_text, right_text):.3f}; "
                       f"e' una misura sul testo, non sul significato)\n")
            families = {settings.family(final_services.get(role, role)) for role in finals}
            if len(families) == 1:
                out.append(
                    f"\n> Le due proposte finali vengono entrambe da `{families.pop()}`, in "
                    f"due sessioni distinte. Qualunque accordo fra loro e' un modello che "
                    f"concorda con se stesso: non e' il confronto fra modelli diversi che "
                    f"questo ciclo dovrebbe produrre, e non va letto come tale.\n")
            diff = unified_diff(left_text, right_text, before_label=left, after_label=right)
            out.append("\n```diff\n" + (clip(diff, 4000) if diff.strip()
                                        else "(nessuna differenza di testo)") + "\n```\n")

    # ------------------------------------------------------------ 2. evidenze
    out.append("\n## 2. Evidenze dichiarate\n")
    out.append("Il tipo e' quello dichiarato da chi ha risposto, non una verifica nostra.\n\n")
    rows = []
    for row in store.findings(run_id, kind="evidence"):
        payload = json.loads(row["payload_json"])
        rows.append([row["ident"], _EVIDENCE_WORDS.get(row["status"], row["status"]),
                     clip(payload.get("claim", ""), 220),
                     clip(payload.get("support", ""), 180),
                     f"{payload.get('role', '?')} r{payload.get('round', '?')}"])
    out.append(_table(["id", "tipo", "affermazione", "supporto", "chi"], rows))

    # ------------------------------------------------------------ 3. controlli
    out.append("\n## 3. Controlli effettivamente eseguiti\n")
    verified_rows, pending_rows = [], []
    for subtask in subtasks:
        for round_row in store.rounds(run_id, subtask["subtask_id"]):
            delta = json.loads(round_row["delta_json"] or "{}")
            for role, results in sorted((delta.get("checks") or {}).items()):
                for result in results:
                    criterion = brief.criterion(result["criterion"])
                    row = [subtask["subtask_id"], str(round_row["round"]), result["criterion"],
                           clip(criterion.text if criterion else "", 110),
                           result["kind"], role, result["status"],
                           clip(result.get("detail", ""), 130)]
                    (pending_rows if result["status"] == "pending"
                     else verified_rows).append(row)
    header = ["sottocompito", "round", "criterio", "testo", "tipo", "proposta", "esito",
              "dettaglio"]
    out.append("**Controlli automatici**, tutti i round. Il valore atteso era fissato "
               "nell'incarico prima di interrogare i modelli: un `pass` dice che la "
               "risposta corrisponde a un riferimento scelto in anticipo, non che il "
               "ragionamento sia giusto.\n\n")
    out.append(_table(header, verified_rows))

    # One row per criterion, not one per round and proposal: a criterion nobody can check
    # automatically is pending once, and repeating it per round would inflate the count.
    pending_criteria = {row[2]: row for row in pending_rows}
    out.append("\n**Criteri che restano da verificare a mano** (nessun controllo "
               "automatico dichiarato nell'incarico):\n\n")
    out.append(_table(["criterio", "testo"],
                      [[ident, row[3]] for ident, row in sorted(pending_criteria.items())]))

    # --------------------------------------------------------- 4. disaccordi
    out.append("\n## 4. Disaccordi e obiezioni aperte\n")
    rows = []
    for row in store.findings(run_id, kind="objection"):
        if row["status"] not in ("open", "resolved_claimed"):
            continue
        payload = json.loads(row["payload_json"])
        state = ("aperta" if row["status"] == "open"
                 else "risoluzione dichiarata, non accettata da chi ha obiettato")
        target = str(payload.get("target", ""))
        roles = {step.role for step in steps}
        against = ("un altro modello" if any(role.lower() in target.lower() for role in roles)
                   else "il materiale in esame")
        rows.append([row["ident"], payload.get("severity", "?"),
                     payload.get("raised_by", "?"), against,
                     clip(target, 90), clip(payload.get("text", ""), 200), state])
    out.append(_table(["id", "gravita'", "sollevata da", "rivolta a", "bersaglio", "testo",
                       "stato"], rows))
    out.append("\nUn'obiezione rivolta al materiale in esame non e' un disaccordo fra i due "
               "modelli: puo' restare aperta perche' nessuno la contesta. Solo quelle rivolte "
               "a un altro partecipante fermano il ciclo per disaccordo.\n")

    # -------------------------------------------------------------- 5. limiti
    out.append("\n## 5. Perche' si e' fermato\n")
    rows = []
    for subtask in subtasks:
        for round_row in store.rounds(run_id, subtask["subtask_id"]):
            if round_row["decision"] == Decision.CONTINUE.value:
                continue
            numbers = json.loads(round_row["numbers_json"] or "{}")
            rows.append([subtask["subtask_id"], str(round_row["round"]),
                         _DECISION_WORDS.get(round_row["decision"], round_row["decision"]),
                         round_row["reason"],
                         json.dumps(numbers.get("checks", {}), ensure_ascii=False),
                         str(numbers.get("cross_agreement", "—"))])
    out.append(_table(["sottocompito", "round", "esito", "regola", "controlli",
                       "somiglianza testuale"], rows))
    if run["stop_detail"]:
        out.append(f"\nA livello di run: {run['stop_detail']}\n")

    # ------------------------------------------------------------ 6. decisioni
    out.append("\n## 6. Decisioni che restano a te\n")
    decisions: list[str] = []
    if pending_criteria:
        decisions.append(
            f"{len(pending_criteria)} criteri ({', '.join(sorted(pending_criteria))}) hanno "
            f"un controllo umano: il sistema non li ha verificati, e senza quella verifica "
            f"l'esito non e' un completamento verificato.")
    blocking = [row for row in store.findings(run_id, kind="objection")
                if row["status"] in ("open", "resolved_claimed")
                and json.loads(row["payload_json"]).get("severity") == "blocking"]
    if blocking:
        decisions.append(f"{len(blocking)} obiezioni bloccanti restano aperte: "
                         + ", ".join(row["ident"] for row in blocking) + ".")
    unavailable = [step for step in steps if step.status == "transport_error"]
    if unavailable:
        services = sorted({step.service for step in unavailable})
        decisions.append(f"Errori di canale su: {', '.join(services)}. "
                         f"Nessun modello e' stato sostituito da un altro.")
    absent = [step for step in steps if step.status == "abandoned"]
    replaced = [step for step in steps
                if step.status == "answered" and settings.roles.get(step.role)
                and step.service and step.service != settings.roles[step.role]]
    if absent:
        rounds = sorted({f"{step.round} ({step.service})" for step in absent})
        covered_rounds = {step.round for step in replaced}
        alone = sorted({step.round for step in absent} - covered_rounds)
        decisions.append(
            f"{len(absent)} passi senza risposta. Round interessati: {', '.join(rounds)}."
            + (f" Di questi, i round {', '.join(str(number) for number in alone)} sono "
               f"proseguiti con una voce sola: le proposte vanno lette sapendo che mancava "
               f"un interlocutore." if alone else "")
            + (f" I round {', '.join(str(number) for number in sorted(covered_rounds))} "
               f"sono stati coperti da una sessione di riserva." if covered_rounds else ""))
    if replaced:
        pairs = sorted({(step.role, settings.roles[step.role], step.service)
                        for step in replaced})
        decisions.append(
            "Una sessione di riserva ha risposto al posto del titolare: "
            + "; ".join(f"{role}, `{service}` invece di `{seat}`"
                        for role, seat, service in pairs)
            + f". La riserva e' una seconda sessione del servizio che stava rispondendo, "
              f"quindi in quei round il confronto e' fra due istanze dello stesso modello. "
              f"Resta tua la decisione se considerarlo un contraddittorio sufficiente o "
              f"rifare il ciclo quando il servizio mancante torna disponibile.")
    unparsed = [step for step in steps if step.status == "unparsed"]
    if unparsed:
        decisions.append(f"{len(unparsed)} risposte non rispettavano il contratto e sono "
                         f"conservate come testo grezzo.")
    quarantined = sorted(directory.glob("steps/*/quarantine/*"))
    if quarantined:
        decisions.append(f"{len(quarantined)} blocchi di codice prodotti dai modelli sono in "
                         f"quarantena sotto `steps/*/quarantine/`: sono artefatti da "
                         f"revisionare, l'orchestratore non li esegue "
                         f"(policy `{settings.execution_policy}`).")
    if not decisions:
        decisions.append("Nessuna decisione bloccante registrata dal sistema. "
                         "Resta tua la decisione se avviare un'altra esecuzione.")
    out.append("".join(f"- {item}\n" for item in decisions))

    # ------------------------------------------------------------ 7. revisione
    review_steps = [step for step in steps if step.stage == "review" and step.status == "answered"]
    out.append("\n## 7. Revisione finale (verbatim)\n")
    if not review_steps:
        out.append("\n_(nessuna: il percorso di questo run non prevede una revisione "
                   "affidata ad altri modelli)_\n")
    else:
        for step in review_steps:
                raw = store.reply_text(step) or ""
                try:
                    parsed = parse_reply(raw)
                    body = parsed.proposal
                    questions = parsed.open_questions
                except ContentProblem:
                    body, questions = raw, ()
                out.append(f"\n### {step.role} ({step.service}) — `{step.path.name}`\n\n")
                out.append(clip(body, 8000) + "\n")
                if questions:
                    out.append("\n**Domande aperte segnalate dalla revisione:**\n")
                    out.append("".join(f"- {clip(item, 300)}\n" for item in questions))

    # -------------------------------------------------------- 8. tracciabilita'
    out.append("\n## 8. Tracciabilita'\n")
    rows = []
    for step in steps:
        rows.append([step.stage, str(step.round), step.role, step.service, step.status,
                     f"{(step.duration_ms or 0) / 1000:.1f}s",
                     step.error_kind or "—", f"`{Path(step.directory).name}`"])
    out.append(_table(["fase", "round", "ruolo", "servizio", "stato", "durata", "errore",
                       "cartella"], rows))
    out.append(f"\nTutti i percorsi sono relativi a `{directory}`.\n")

    stamp = utc_now().replace(":", "").replace("-", "")
    path = directory / f"report-{stamp}.md"
    serial = 2
    while path.exists():        # two reports in the same second: a new file, never an overwrite
        path = directory / f"report-{stamp}-{serial}.md"
        serial += 1
    write_new(path, "".join(out))
    store.event(run_id, "report_written", {"path": str(path)})
    return path


def _stand_in_rounds(store: Store, settings: Settings, run_id: str, subtask_id: str):
    """Rounds where a seat was answered by someone other than its configured holder.

    Read from the recorded steps, so it says what happened rather than what was planned.
    """
    covered = []
    for step in store.steps(run_id, subtask_id=subtask_id, stage="solve"):
        if step.status != "answered":
            continue
        seat = settings.roles.get(step.role)
        if seat and step.service and step.service != seat:
            covered.append((step.round, step.role, seat, step.service))
    return sorted(set(covered))


def _final_steps(store: Store, run_id: str, subtask_id: str):
    latest: dict[str, object] = {}
    for step in store.steps(run_id, subtask_id=subtask_id, stage="solve"):
        if step.status != "answered":
            continue
        current = latest.get(step.role)
        if current is None or step.round >= current.round:  # type: ignore[union-attr]
            latest[step.role] = step
    return [latest[role] for role in sorted(latest)]
