"""The three questions a research campaign asks, and the contract it asks them under.

Written in Italian because a person reads them before they are sent. Assembled from the
same parts as the debugging prompts (`protocol.assemble`, `protocol.data_block`), which
is what keeps one rule in one place: the operator's brief is an instruction and is never
wrapped in data delimiters, while everything untrusted -- attached material, the other
worker's answer, a worker's own earlier answer -- always is.

Two things in here are deliberate and cost something:

* the contract asks a worker to say **which searches it actually ran** and **what level
  it reached each source at**, separately from what it concluded. It is more to write and
  it is the whole point: a bibliography is cheap, a search log is not;
* when search is not available, the prompt says so, forbids dressing prior knowledge as a
  result, and asks for a plan instead. The failure being designed against is a literature
  review written from memory, which arrives looking exactly like the real thing.
"""

from __future__ import annotations

from typing import Sequence

from ..protocol import assemble, data_block
from .campaign import ResearchBrief, SearchCapability
from .contract import RESEARCH_SENTINEL
from .leads import SelectedLead

_CONTRACT = f"""\
FORMATO DELLA RISPOSTA (obbligatorio)
Scrivi prima il ragionamento in chiaro, quanto vuoi. Poi chiudi la risposta con questa
riga da sola:

{RESEARCH_SENTINEL}

e subito dopo un unico blocco ```json``` con questo oggetto:

{{
  "summary": "una frase su cosa hai concluso",
  "synthesis": "la tua sintesi, completa e autonoma: cosa hai cercato, cosa hai trovato, cosa sostiene o contraddice le ipotesi, cosa resta da verificare",
  "searches": [{{"query": "la stringa che hai cercato", "service": "dove (PubMed, Google Scholar, il motore integrato, ...)", "filters": "anni, tipo di studio, lingua, ...", "status": "executed|not_executed|failed|blocked", "note": "quante cose ha restituito, o perche' non e' andata"}}],
  "sources": [{{"id": "F1", "title": "", "authors": "", "year": "", "doi": "", "url": "", "consulted": "found|abstract|full_text_or_section|not_accessible", "access_note": "paywall, solo abstract, PDF aperto, ...", "found_via": "quale delle tue query l'ha restituita"}}],
  "claims": [{{"text": "l'affermazione", "nature": "reported_by_authors|worker_interpretation|new_hypothesis", "supported_by": ["F1"], "contradicted_by": ["F2"], "about_hypothesis": "H1", "locator": "dove nel documento: sezione, figura, tabella, pagina", "limits": "su cosa non si puo' estendere"}}],
  "hypotheses": [{{"id": "H1", "statement": "", "initial_evidence": [""], "alternatives": ["una spiegazione diversa degli stessi dati"], "proposed_tests": ["la ricerca o l'esperimento che le distingue"], "status": "open|supported_declared|contradicted_declared|undecided"}}],
  "gaps": [{{"missing": "cosa manca", "search_that_would_close_it": "quale ricerca lo colmerebbe"}}],
  "open_questions": ["cio' che resta incerto"],
  "saturation_claim": "se ritieni di aver esaurito la letteratura utile, dillo qui e motivalo",
  "operator_requests": ["cose che chiederesti all'operatore: piu' round, un accesso, un file"],
  "confidence": "low|medium|high"
}}

REGOLE DEL CONTRATTO, e non sono formalita':

1. `searches` e' un registro di cosa hai *fatto*, non di cosa faresti. Metti `executed`
   solo per una query che hai davvero eseguito in questa sessione; tutto il resto e'
   `not_executed`, e va bene: una ricerca proposta e dichiarata tale vale piu' di una
   ricerca immaginata e spacciata per fatta.
2. `consulted` dice fin dove sei arrivato su quella fonte. `found` vuol dire che l'hai
   vista in un elenco di risultati e nient'altro. Non scrivere `full_text_or_section` se
   non hai letto il testo. Se non riesci ad accedere, `not_accessible` con la ragione.
3. Attribuire un risultato agli autori (`reported_by_authors`) richiede di dire **dove**
   nel documento sta, in `locator`. Se non puoi indicarlo, non e' un risultato riferito
   dagli autori: e' una tua interpretazione o una tua ipotesi, e va marcata cosi'.
4. Distingui sempre: risultato riferito dagli autori, tua interpretazione, ipotesi nuova.
   Una tua idea presentata come conclusione di un paper e' l'errore piu' costoso qui.
5. Un riferimento formalmente corretto non dimostra che la fonte esista. Se un DOI o un
   URL non li hai aperti, dillo in `access_note`.
6. Non c'e' un campo per cambiare i limiti della sessione. Se ti serve altro, scrivilo in
   `operator_requests`: viene mostrato all'operatore e non cambia nulla da solo.
7. Concordare con l'altro worker non e' l'obiettivo e non rende niente verificato."""

_NO_EXECUTION = """\
LIMITI OPERATIVI, validi in tutte le fasi:
  - non eseguire codice e non chiedere di eseguirne; se scrivi codice, e' materiale da
    leggere, non da far girare;
  - niente scaricamenti massivi: poche fonti mirate, non interi archivi;
  - se una pagina chiede un accesso, un pagamento o una verifica anti-bot, fermati e
    registra la fonte come `not_accessible` con la ragione. Non aggirare nulla."""


def _search_note(capability: dict[str, SearchCapability], role: str, service: str,
                 plan_only: bool) -> str:
    """What this worker is told about **its own** channel. Never optimistic, never averaged.

    Per service, not per campaign, and that distinction is worth the extra branch. Today
    DeepSeek has a search control we have set and read back, and Kimi has none anybody
    here has observed. Telling both of them the same thing would either forbid a real
    search that was available, or invite one that is not: each worker is told the truth
    about the channel it is actually sitting on, and the report says who had what.
    """
    state = capability.get(service)
    if state is None or not state.can_search:
        return (
            "RICERCA SUL WEB: in questa sessione **non hai** uno strumento di ricerca "
            "attivo e verificato dal nostro lato.\n"
            "  - Non presentare conoscenza pregressa come se fosse il risultato di una "
            "ricerca. E' la cosa che rende inutile tutto il resto.\n"
            "  - Metti in `searches` le query che *andrebbero* eseguite, con "
            "`status: not_executed`, dicendo per ciascuna dove e con quali filtri.\n"
            "  - In `sources` metti solo cio' che hai davvero davanti in questa sessione. "
            "Se ricordi un lavoro ma non puoi aprirlo, mettilo come affermazione con "
            "`nature: worker_interpretation` e dichiara che e' un ricordo, non una fonte "
            "consultata.")
    return (
        f"RICERCA SUL WEB: in questa sessione lo strumento di ricerca dell'interfaccia e' "
        f"stato acceso e verificato dal nostro lato ('{state.mode_name}'). Usalo davvero.\n"
        "  - Sappiamo che l'interruttore era acceso; **non** vediamo quali query hai "
        "eseguito. Quello che scrivi in `searches` resta una tua dichiarazione, e verra' "
        "registrato come tale. Scrivila accurata.\n"
        "  - Poche query mirate e riportate per intero valgono piu' di molte accennate.")


def _brief_block(research: ResearchBrief) -> str:
    """The operator's instructions, in plain text: they are the work, not the data."""
    brief = research.brief
    parts = [
        f"INCARICO DELL'OPERATORE ({brief.brief_id} v{brief.version})",
        f"Titolo: {brief.title}",
        f"Domanda di ricerca: {brief.question}",
        f"Perimetro: {research.scope}",
    ]
    if research.out_of_scope:
        parts.append(f"Fuori perimetro (non cercarlo): {research.out_of_scope}")
    if brief.context.strip():
        parts.append(f"Contesto:\n{brief.context.strip()}")
    parts.append("Criteri di pertinenza -- una fonte conta se soddisfa almeno uno:\n"
                 + "\n".join(f"  [{item.ident}] {item.text}"
                             for item in research.relevance_criteria))
    if research.hypotheses:
        lines = []
        for item in research.hypotheses:
            lines.append(f"  [{item.ident}] {item.statement}")
            for evidence in item.initial_evidence:
                lines.append(f"      evidenza di partenza: {evidence}")
            for alternative in item.alternatives:
                lines.append(f"      spiegazione alternativa gia' nota: {alternative}")
        parts.append("Ipotesi di partenza dell'operatore -- riferisciti a questi id:\n"
                     + "\n".join(lines))
    parts.append(f"Risultato atteso: {brief.expected_result}")
    return "\n".join(parts)


def _materials_block(research: ResearchBrief) -> str:
    materials = research.brief.materials
    if not materials:
        return ""
    return "\n\n".join(
        data_block("MATERIALE", f"{item.ident} sha256={item.sha256[:12]}", item.text)
        for item in materials)


def _budget_block(research: ResearchBrief, phase: int) -> str:
    budget = research.budget
    return (
        f"BUDGET DELLA CAMPAGNA, deciso prima di contattarti e non negoziabile qui: "
        f"{budget.max_phases} fasi, al massimo {budget.max_main_responses} risposte "
        f"principali in tutto, al massimo {budget.max_leads} piste di approfondimento, "
        f"{budget.max_wall_clock_minutes} minuti. Questa e' la fase {phase}. "
        f"Non ci sara' una fase in piu': quello che resta da fare va scritto come lacuna "
        f"o come ricerca proposta, non rimandato a un round che non esiste.")


# ------------------------------------------------------------------------- phase 1

def phase1_prompt(research: ResearchBrief, *, role: str, service: str,
                  capability: dict[str, SearchCapability], plan_only: bool) -> str:
    perspective = research.perspective_for(role)
    header = (
        f"Sei {role} in una campagna di ricerca scientifica coordinata da un orchestratore "
        f"locale. Fase 1 di {research.budget.max_phases}: ricerca indipendente. Un altro "
        f"worker sta ricevendo la stessa domanda e gli stessi vincoli, in parallelo. Non "
        f"vedi la sua risposta e lui non vede la tua: in questa fase non deve esserci "
        f"nessun coordinamento.")
    perspective_block = (
        f"LA TUA PROSPETTIVA IN QUESTA CAMPAGNA: {perspective}\n"
        "Non e' un divieto di guardare altrove: e' la parte di cui rispondi tu, e su cui "
        "l'altro contera'. Se esci dalla tua prospettiva, dillo." if perspective else "")
    task = (
        "COMPITO DELLA FASE 1, e rispondi su tutti e quattro i punti:\n"
        "  1. **Ricerche effettivamente svolte.** Ogni query per intero, dove l'hai "
        "eseguita, con quali filtri, con quale esito. Vanno in `searches`.\n"
        "  2. **Fonti trovate e consultate.** Per ciascuna: titolo, autori e anno se li "
        "hai, DOI o URL, e fin dove sei arrivato (`consulted`). Vanno in `sources`.\n"
        "  3. **Evidenze pertinenti**, cioe' cosa dicono quelle fonti rispetto alla "
        "domanda e alle ipotesi, con il localizzatore nel documento. Vanno in `claims`, "
        "ciascuna con la sua natura.\n"
        "  4. **Limiti e domande aperte.** Cosa non hai potuto verificare, cosa non hai "
        "trovato, cosa resta incerto. Vanno in `gaps` e `open_questions`.\n"
        "Se una ricerca non ha prodotto nulla, e' un risultato: registrala con il suo "
        "esito. «Non ho trovato evidenze nelle ricerche che ho registrato» e' una frase "
        "onesta; «non esistono evidenze» non lo e', e non e' quello che hai misurato.")
    return assemble(header, [
        _brief_block(research),
        _materials_block(research),
        perspective_block,
        _search_note(capability, role, service, plan_only),
        _NO_EXECUTION,
        _budget_block(research, 1),
        task,
        _CONTRACT,
    ])


# ------------------------------------------------------------------------- phase 2

def peer_block(role: str, synthesis: str, digest: str, usable: bool, note: str) -> str:
    if not usable:
        return (f"NOTA: {role} non ha consegnato una risposta utilizzabile nella fase "
                f"precedente" + (f" ({note})" if note else "") + ". Non ti viene inoltrato "
                "nulla di suo, nemmeno in parte: non dedurne che sia d'accordo con te, e "
                "non attribuirgli posizioni.")
    return data_block("RISULTATI-ALTRUI", role, f"{synthesis}\n\n{digest}")


def phase2_prompt(research: ResearchBrief, *, role: str, service: str,
                  capability: dict[str, SearchCapability], plan_only: bool,
                  own_digest: str, peer_blocks: Sequence[str]) -> str:
    header = (
        f"Sei {role}. Fase 2 di {research.budget.max_phases}: confronto e piano di "
        f"approfondimento. Hai davanti i risultati completi della fase 1, i tuoi e quelli "
        f"dell'altro worker. Nessuno dei due ha visto la risposta dell'altro per questa "
        f"fase: quello che leggi e' solo la fase 1.")
    task = (
        "COMPITO DELLA FASE 2, nell'ordine:\n"
        "  1. **Accordi.** Su cosa i due risultati concordano, e su quale evidenza. In "
        "`agreements`. L'accordo fra noi due non e' una verifica: dillo dove serve.\n"
        "  2. **Contributi complementari.** Cosa ha trovato l'altro che tu non avevi, e "
        "viceversa. In `complementary`.\n"
        "  3. **Contraddizioni.** Dove i due risultati si contraddicono, citando le fonti "
        "esatte di entrambi. In `contradictions`. Non risolverle per simpatia: se non hai "
        "l'evidenza per chiuderne una, deve restare aperta.\n"
        "  4. **Assunzioni prive di sostegno.** Affermazioni -- tue o sue -- che nessuna "
        "fonte consultata sostiene. In `unsupported_assumptions`.\n"
        "  5. **Lacune nella ricerca.** Cosa non e' stato cercato affatto, e dove. In "
        "`search_gaps` e `gaps`.\n"
        "  6. **Piste di approfondimento: poche, al massimo due, in ordine di priorita'.** "
        "Ogni pista, in `leads`, deve avere tutte e quattro le parti:\n"
        "       ipotesi -> evidenze di partenza -> spiegazione alternativa -> ricerca che "
        "sappia distinguerle.\n"
        "     Una pista senza la spiegazione alternativa o senza la ricerca che le "
        "distingue viene scartata dal programma: e' una preferenza, non una pista.\n"
        "  7. **Come cambiare la ricerca**, in `strategy_change` dentro ogni pista: quali "
        "termini cambiare, quale fonte o banca dati usare invece, quali filtri togliere o "
        "stringere, quale disciplina guardare, se cercare risultati negativi, se risalire "
        "ai riferimenti precedenti o ai lavori che citano, se guardare i supplementi o i "
        "repository di dati. Se la fase 1 ha cercato male, e' qui che si dice.\n"
        "Aggiorna anche `hypotheses` con lo stato di ciascuna alla luce di entrambe le "
        "ricerche, e `synthesis` con la tua lettura complessiva.\n"
        "Il programma sceglie le piste con una regola fissa: la tua prima pista ben "
        "formata, la sua prima pista ben formata, deduplicate, al massimo due. Mettere per "
        "prima la meno importante la penalizza.")
    return assemble(header, [
        _brief_block(research),
        _materials_block(research),
        data_block("TUOI-RISULTATI-FASE-1", role, own_digest) if own_digest else "",
        *peer_blocks,
        _search_note(capability, role, service, plan_only),
        _NO_EXECUTION,
        _budget_block(research, 2),
        task,
        _CONTRACT,
    ])


# ------------------------------------------------------------------------- phase 3

def _leads_block(leads: Sequence[SelectedLead]) -> str:
    if not leads:
        return ("PISTE ASSEGNATE: nessuna. Nella fase 2 non e' stata prodotta nessuna "
                "pista completa nelle sue quattro parti. Usa questa fase per consolidare "
                "le evidenze che hai gia' e per dire, con precisione, quale ricerca "
                "servirebbe: sara' il punto di partenza di una campagna successiva.")
    lines = ["PISTE ASSEGNATE A QUESTA FASE, decise da una regola del programma e non da "
             "un modello:"]
    for item in leads:
        lead = item.lead
        lines.append(
            f"\n  [{item.ident}] proposta da {', '.join(item.proposed_by)}\n"
            f"    ipotesi: {lead.hypothesis}\n"
            f"    evidenze di partenza: {lead.starting_evidence}\n"
            f"    spiegazione alternativa: {lead.alternative_explanation}\n"
            f"    ricerca che le distingue: {lead.distinguishing_search}"
            + (f"\n    cambio di strategia proposto: {lead.strategy_change}"
               if lead.strategy_change else ""))
    return "\n".join(lines)


def phase3_prompt(research: ResearchBrief, *, role: str, service: str,
                  capability: dict[str, SearchCapability], plan_only: bool,
                  leads: Sequence[SelectedLead], own_digest: str,
                  open_contradictions: Sequence[str]) -> str:
    header = (
        f"Sei {role}. Fase 3 di {research.budget.max_phases}, l'ultima: ricerca mirata "
        f"sulle piste assegnate e sintesi. Dopo questa non ci sono altre fasi, e non "
        f"verra' prodotta una sintesi comune da un terzo modello: il dossier finale "
        f"conserva la tua sintesi e quella dell'altro **separate**, con i disaccordi. "
        f"Scrivi quindi qualcosa che regga da solo.")
    contradictions = (
        "CONTRADDIZIONI ANCORA APERTE dalla fase 2:\n"
        + "\n".join(f"  - {item}" for item in open_contradictions)
        + "\nSe la ricerca di questa fase ne chiude una, dillo citando la fonte che lo fa. "
          "Se non la chiude, lasciala aperta: una contraddizione archiviata senza evidenza "
          "e' peggio di una contraddizione." if open_contradictions else "")
    task = (
        "COMPITO DELLA FASE 3:\n"
        "  1. Approfondisci **le piste assegnate**, eseguendo la ricerca che le distingue "
        "(o, se non puoi eseguirla, dichiarandola `not_executed` e dicendo perche').\n"
        "  2. Aggiorna le evidenze: nuove fonti in `sources`, nuove affermazioni in "
        "`claims` con la loro natura e il loro localizzatore.\n"
        "  3. Aggiorna lo stato delle ipotesi in `hypotheses`, usando gli id gia' in uso. "
        "Usa `supported_declared` / `contradicted_declared` -- sono dichiarazioni tue, e "
        "il rapporto le presentera' come tali, mai come verifiche.\n"
        "  4. Se questa fase non ha prodotto evidenze nuove, **scrivilo esplicitamente** "
        "in `synthesis` e lascia `sources` e `claims` vuoti invece di ripetere la fase "
        "precedente. Una fase senza novita' e' un'informazione; una ripetizione travestita "
        "da novita' e' rumore.\n"
        "  5. In `synthesis`: cosa e' stato cercato e dove, le evidenze principali e quelle "
        "contrarie, come sono cambiate le ipotesi, cosa resta contraddittorio, cosa "
        "proporresti come prossimo approfondimento o esperimento.")
    return assemble(header, [
        _brief_block(research),
        _materials_block(research),
        _leads_block(leads),
        data_block("TUOI-RISULTATI-PRECEDENTI", role, own_digest) if own_digest else "",
        contradictions,
        _search_note(capability, role, service, plan_only),
        _NO_EXECUTION,
        _budget_block(research, 3),
        task,
        _CONTRACT,
    ])


def repair_prompt(problem) -> str:
    """One deterministic retry that asks for the block and nothing else."""
    return (
        "La tua ultima risposta non contiene un blocco di risultato leggibile "
        f"({problem.kind}: {problem.detail}). Non ripetere il ragionamento e non rifare "
        f"le ricerche. Rispondi soltanto con la riga {RESEARCH_SENTINEL} seguita da un "
        "unico blocco ```json``` valido, con almeno i campi 'summary' e 'synthesis', e "
        "con `searches` e `sources` se ne avevi."
    )
