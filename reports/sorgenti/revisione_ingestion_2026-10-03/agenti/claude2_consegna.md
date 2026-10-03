# Consegna originale di Claude2

Agente: claude2. Run: 20261003-141124-vcc-ingestion-resume. Modalità: edit isolato. Modello: predefinito del registro hub; meta.json non registra un override. Brief: vcc-ingestion-expanded-resume-20261003.md, nel control/briefs dell'hub. Rapporto integrale riportato sotto: affermazioni del worker, da leggere con la revisione del supervisore.

---

Incremento parziale consegnato: codice e manifest scritti, ma **niente è stato eseguito** — né test, né rilettura di metadati remoti, né job cloud, né shard. In questa sessione il confine dell'hub nega Python, la rete e le letture fuori dal worktree; non ho ritentato.

## Che cosa c'è nella cartella

Tutto sta in `reports/sorgenti/ingestione_espansione_2026-10-03/`.

**Terza ondata scPerturb J13–J15 (riconciliata dai file della repo, commit `05504a1`):**
- **Cellule e copie (misurato):** 317.695 + 97.335 + 202.494 = 617.524 (`catalogo_r4/CATALOGO.md`). Le copie Kaggle coincidono per sha256 con le ricevute per 17/17, 6/6 e 11/11 shard (`kaggle_verify/esito_r2.json`).
- **Modalità (misurato):** nove unità su dieci sono KO; l'unica CRISPRi è Xu 2023 (HEK293, 98.315 cellule, 190 bersagli a gene singolo). Nell'istogramma CRISPRi l'ondata aggiunge quindi al più un gruppo per al più 190 bersagli.
- **Fuori dalla supervisione a bersaglio singolo (derivato da `smoke_w3/`):** 53.376 cellule non assegnate, 36.760 combinate (Sunshine), 26.521 con etichetta non risolta.
- **Non verificato:** i `complete.json` su Drive non sono stati riletti oggi. Le liste complete dei bersagli non sono nella repo, quindi la matrice bersaglio × gruppo dell'ondata esce solo eseguendo l'audit sugli shard (handoff, passo A).
- **Inventario e aggiunta proposta al manifest di training:** `inventario_scp_w3.json`. Pilot congelato e H1 test non toccati.

**Audit di copertura (`coverage_audit.py`, scritto, non eseguito):**
- **Che cosa calcola:** conteggi per sorgente, gruppo, studio, modalità e pool di controlli; prima e dopo le esclusioni, con il motivo; matrice sparsa bersaglio × gruppo; istogramma 1/2/3/4+ per tutte le modalità e per il solo CRISPRi.
- **Quando:** dopo aver tolto il gruppo escluso e la fold nascosta, con la stessa regola sha256 e lo stesso sale di R-LEAD.
- **Unità di supporto:** il gruppo di linea. Un contesto senza regola viene rifiutato, non promosso a gruppo nuovo.
- **Limite:** il QC è un'approssimazione dalle colonne `obs`; il prepass del training resta l'autorità.

**Test di fixture (`test_coverage_audit.py`, 16 casi, scritti, non eseguiti):** alias, cellule duplicate, ripubblicazioni, modalità separate, gruppo escluso con tutti i suoi studi e stati, gruppi correlati, bersagli nascosti, parità con `line_groups.json` del pilot. Le fold attese le ho calcolate con `printf | sha256sum`, quindi controllano anche la regola copiata.

**Gruppi di linea (`line_groups_expanded_v1.json`, proposta):** contiene invariato il file del pilot.
- Frangieh: i tre stati (Control, IFNγ, Co-culture) sono un solo gruppo melanoma; con la regola del pilot sarebbero diventati tre gruppi falsi.
- Xu HEK293 nella famiglia HEK293T; Dixit e Norman in K562; Datlinger in Jurkat (per il 2021 la linea va ancora letta negli shard).
- Shifrut: gruppo proprio, correlato a CD4T (sottotipo T non verificato).

**Orion (percorso scritto, non eseguito, senza test):**
- `campionamento_v2.py` risolve la discrepanza della versione 1 dando un nome ai due disegni: `srs_line_target` (il codice v1) e `proportional_gem` (la prosa v1). Stessa probabilità di inclusione min(1, k/n), comportamento congiunto diverso. Entrambi sono annidati in k: il tetto è una tranche, non uno scarto del resto.
- `orion_job.py` ha tre fasi: metadati a intervalli di byte con parità contro il passaggio del 26/09; campione scritto e hashato prima di leggere un conteggio; uno shard per file GEM. La lista dei file è quella congelata il 26/09 con sha256; dopo un runtime perso i file finiti non si riscaricano.
- `specs/orion_v2.json` è la specifica; propone `proportional_gem` con k = 40.

**`common.py`, punti della revisione:**
- `download` rifiuta una destinazione esistente, scrive su un parziale nuovo aperto in esclusiva e rinomina solo dopo dimensione e checksum.
- La lettura è limitata allo span chiesto: un server che ignora Range viene rifiutato prima di leggere il corpo.
- I test chiesti (schema reale delle ricevute di `rlab_job`, Range ignorato, risposta corta, dimensione o ETag cambiati, checksum fallito) **non sono scritti**.

## Che cosa manca

- Test di `common.py`, `campionamento_v2.py`, `orion_job.py`.
- Launcher Orion: manca `build_jobs.py`; i comandi delle tre fasi sono nell'handoff, ma non c'è ancora snapshot, manifest di preflight né file di coda.
- `preflight_metadata.py`: licenze e versioni correnti non sono state riverificate.
- CD4 (c'è solo il controllo della tabella incrociata `guide_group × guide_type`), Mixscale, KOLF pan-genome, VIPerturb, Southard, microglia e PerturbFate.
- README del report e righe in `reports/sorgenti/README.md` e `docs/REGISTRO.md`: senza, `31_check_docs.py` segnalerà la cartella come non coperta.

## Domande aperte per Claude1

1. Quale via del proprietario copre il download Orion (126,3 GB letti sul runtime)? `INGESTIONE.md` §5 lo dà in attesa; la scheda R-LEAD registra un via ai download il 3/10.
2. L'account Kaggle di destinazione va verificato prima di pubblicare: gli shard stanno su `davidmaisterx`, il pilot gira su `davideferrante11`.
3. I byte di `metadata/gene_metadata.parquet` non sono nella repo (lo sha256 sì): il job li legge dall'host.

## Prossimi comandi

```powershell
.\scripts\py.cmd -m unittest discover -s reports/sorgenti/ingestione_espansione_2026-10-03 -p "test_*.py" -v
```
Poi `EXECUTION_HANDOFF.md`: passo A (audit della terza ondata su un kernel CPU Kaggle), passo B (Orion: `meta`, `sample`, `shards` per linea, prima con `--max-files 2`).

## File cambiati (tutti nuovi, nella cartella del report)

- `PROGRESS.md` — stato, comandi, blocchi.
- `EXECUTION_HANDOFF.md` — comandi cloud esatti, prerequisiti, permessi; l'incarico originale resta aperto al punto C.
- `common.py` — sink degli shard nel layout di `rlab_job`, fetch a intervalli, download senza sovrascrittura.
- `coverage_audit.py`, `test_coverage_audit.py` — audit e fixture.
- `line_groups_expanded_v1.json` — gruppi di linea proposti.
- `inventario_scp_w3.json` — riconciliazione J13–J15 e aggiunta proposta al manifest.
- `campionamento_v2.py` — disegni Orion e controllo della tabella CD4.
- `orion_job.py`, `specs/orion_v2.json` — percorso Orion.
- `env_check.py` — inventario del runtime (dal primo turno).
