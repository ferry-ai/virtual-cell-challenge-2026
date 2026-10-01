# Consegna del programma R-LEAD al teammate

1 ottobre 2026. Richiesta del proprietario: pubblicare lo stato versionato e trasferire
l'esecuzione del piano, inclusi i controlli sulla macchina del teammate. Questa pagina spiega
come partire; stato e assegnazione del programma restano nella [scheda R-LEAD](piani/strategia-scientifica.md).
Il prompt da dare a Claude è in [PROMPT_CLAUDE_TEAMMATE.md](PROMPT_CLAUDE_TEAMMATE.md).

## Brief da inoltrare

Riprendi il programma R-LEAD: prima rendi affidabili split, controlli, pesi della loss e miscela
della rete; poi costruisci il banco a più contesti e confronta transfer, generico, bilineare e
transfer con residuo biologico. Il training r3 è concluso: successo tecnico, ramo identity
collassato, descrittori ancora sotto transfer su HepG2. Le diagnosi sono esplorative e le
correzioni sono da implementare e verificare. Non partire aumentando la rete o sommando dati.

La repo contiene codice, protocolli e risultati leggeri. I dati e i pesi stanno fuori da Git.
Fai eseguire al tuo Claude il prompt di consegna: deve verificare il suo ambiente, inventariare
gli input realmente disponibili e riprodurre le diagnosi applicabili prima di correggere.
Il teammate prende R-LEAD; gli invii e le ingestioni già seguite da R-LAB restano coordinati
con il proprietario. T29 è gestito dall'altra sessione: controllarne lo stato corrente,
senza duplicare generazione o invio.

## Organizzazione e percorso di lettura

| Dove | Che cosa cercare |
|---|---|
| `CLAUDE.md`, `AGENTS.md` | Accordo e instradamento; leggere prima di lavorare |
| `docs/PROGETTO.md` §0 | Stato e direzione attuali |
| `docs/PIANI.md` §2–3, scheda R-LEAD | Priorità, presa in carico, prossimo passo e dipendenze |
| `docs/GENERALIZZAZIONE.md`, D-050 in `docs/DECISIONI.md` | C/T/J, leakage, criterio competitivo e dichiarazioni scientifiche |
| `reports/analisi/lead_audit_2026-10-01/` | Revisione, nota tecnica, aggiornamento r3, sei script con risultati e hash |
| `reports/modelli/risposta_biologica_2026-09-30/` | Codice cellnet originale, test sintetici, descrittori e launcher |
| `reports/modelli/cellnet_esteso_2026-10-01/`, `cellnet_completo_2026-10-01/` | Protocolli e risultati r2/r3; i manifest dichiarano anche i file pesanti non copiati |
| `reports/sorgenti/corpus_cellulare_2026-09-30/` | Corpus, adattatori, inventario, job e verifica del runtime |
| `src/vcc2026/`, `scripts/`, `configs/`, `tests/` | Pipeline di produzione, ricette e test. Leggere la guida della cartella prima di modificarla |
| `docs/PROCEDURE.md`, `docs/ERRORI.md` | Esecuzione, preflight e lezioni; leggere le sezioni del proprio compito |
| `docs/REGISTRO.md`, indici delle categorie | Validità per percorso, senza leggere tutta la storia |

La memoria privata degli agenti, `.claude/`, `agent-hub`, worktree locali e processi del
computer del proprietario non sono dipendenze trasferite. Il piano è eseguibile partendo
dalle fonti versionate; gli accessi e gli input esterni devono essere ricostruiti esplicitamente.

## Git e macchina nuova

Repository: [ferry-ai/virtual-cell-challenge-2026](https://github.com/ferry-ai/virtual-cell-challenge-2026).
Clonare oppure aggiornare senza sovrascrivere lavoro locale (`git pull --ff-only` su checkout
pulito). Verificare che `53d17fe` sia un antenato di HEAD e che questi due documenti di consegna
siano presenti. Quel commit identifica l'audit, non il punto finale del push. La verifica
conclusiva del push confronta l'hash di `main` locale e remoto.

Usare un branch di lavoro `codex/teammate-rlead` sul clone del teammate per evitare interferenze
con il `main` usato dalla sessione R-LAB. Prima di prendere file condivisi, verificare con il
proprietario gli incarichi correnti. Registrare branch, commit base, sessione e perimetro.

Configurare `VCC2026_DATA_ROOT` in una cartella propria, esterna alla repo. Non ricreare
`C:/Users/ferra`, il mount `G:` o un account cloud del proprietario. I wrapper `.cmd` sono
Windows e cercano `<data-root>/.venv/Scripts/python.exe`; su Linux/macOS usare l'interprete
`<data-root>/.venv/bin/python` ed esporre `src/` su `PYTHONPATH` nella sessione.
Un venv non si copia fra sistemi: si ricrea dai requisiti, registrando le versioni risolte.
`requirements.txt` contiene intervalli, non un lock esatto; il training usa anche PyTorch.

Il [preflight portabile](../../../../reports/analisi/handoff_teammate_2026-10-01/preflight_handoff.py)
funziona con la sola libreria standard e registra revisione Git, interprete, dipendenze,
percorsi, spazio, input minimi e codice rispetto a r2. Non installa, scarica o avvia job.
Il suo exit code 0 significa «inventario scritto»: leggere le singole voci di readiness.
Per GPU, RAM, round trip H5AD e scorer usare anche `validate_runtime.py` del corpus; verificare
separatamente `cell_eval2.config` e `vcc2026.config.paths()` nell'interprete effettivo.

## Che cosa arriva con il clone e che cosa richiede accesso

| Materiale | Disponibilità dal clone | Azione |
|---|---|---|
| Codice, ricette, protocolli, eval r2/r3, diagnostiche dell'audit | Versionati | Verificare revisione, percorsi e hash; possibili differenze LF/CRLF dei file di testo |
| Conteggi HepG2 originali | Esterni: 850.590.740 byte; SHA256 nel manifest `data_r1` dell'audit | Mappare la propria copia e verificarla prima delle analisi cellulari; se manca, procedere con output versionati e fixture CPU |
| Controlli ufficiali, asse e pannello | Esterni, sotto `raw/controls/` | Richiedere accesso lecito; verificare nomi, ordine dei 18.533 geni, 300 target e controlli per contesto |
| Shard del corpus e descrittori | Parte su Drive/Kaggle privati; inventari e manifest versionati | Verificare accesso del proprio account, revisioni e checksum; ricostruire un manifest nuovo con percorsi della propria macchina |
| `model.pt`, checkpoint e prepass pesanti | Ignorati da Git; i manifest r3 li dichiarano non copiati | Recupero autorizzato dal kernel/dalla radice dati oppure training futuro; non dedurre disponibilità da `eval.json` |
| H1 test | Riserva | Verificare soltanto ruolo e provenienza nei manifest; non aprire per onboarding o debug |
| Credenziali, sessioni Colab, quota e notebook vivi | Non trasferiti | Usare accessi propri o condivisione autorizzata; verificare i job prima di nuovi lanci |

Le versioni precedenti dell'inventario descrivono fotografie datate: verificare la disponibilità
attuale. Mancanza di GPU non impedisce correzioni e fixture CPU. Mancanza di dati reali limita
le dichiarazioni scientifiche; va dichiarata e risolta prima del benchmark corrispondente.

## Prima consegna richiesta al teammate

Un report nuovo con ambiente, input/accessi, matrice di applicabilità dei difetti, riproduzioni
CPU e versione candidata corretta; test di accettazione e confronto col codice originale.
Poi protocollo del banco congelato con baseline addestrate, C/T/J dopo QC, sei metriche e
riserva. Il programma successivo è nella scheda R-LEAD: questa pagina non lo duplica.
Ogni blocco indica quale passo impedisce e quale lavoro resta possibile.

Download, installazioni che richiedono download, quota cloud, invii, agenti aggiuntivi e push
successivi seguono le autorizzazioni della chat del teammate. La richiesta del 1/10 autorizza
il push di questa consegna dal computer del proprietario; non concede credenziali o spesa futura.
