# DATI-TRANSFER — stato r7 e passaggio a VALIDAZIONE

**Verificato l'8 ottobre 2026 alle 23:13 Europe/Rome**, tramite API Kaggle e
hash dei file locali: [resume_audit_r1.json](resume_audit_r1.json).
Il freeze previsto alle 23:00 è trascorso. Questa nota aggiorna r6 e le
consegne precedenti; non modifica i dati durante i fit.

| Job, account `davideferrante11` | Stato remoto letto | Significato |
|---|---|---|
| `dt-final-t2-01a11c34-r1` | COMPLETE, 23:13:28 | T2 già eseguito, effetti consegnati e verificati |
| `esm2-production-01a11c35-r4` | RUNNING, 23:13:30 | Job attivo; ricevuta finale del consumo non ancora verificata |
| `esm2-t-01a11c35-r3` | RUNNING, 23:13:32 | Job attivo; ricevuta finale del consumo non ancora verificata |

## T2: consenso acquisito e consegna completata

**T2 non attende più il consenso al fit.** Il via umano verificato è in
`final_t2/authorization_r1.json`; il job è completato e gli effetti sono
consegnati in [candidate_t2_r1.json](candidate_t2_r1.json) e
[CONSEGNA_T2_r1.md](CONSEGNA_T2_r1.md). La nuova verifica ha ricalcolato gli
hash dei tre NPZ: sono ancora quelli congelati, SHA256
`d496a38dad7f597cf586199d3ffe40c430e957ba82c78a8fe8da4bcedd6e0ab2`.
Sono invariati anche ricevuta, verifica cloud, release parent e medie usate.

La ricevuta del fit T2 attesta 16 fonti e parità T1 nel ramo nullo. Gli effetti
di produzione sono 300 × 18.533, uguali nei tre contesti, con ampiezza 1,576 e
cis già applicati ed emettitore non applicato. Questa consegna non equivale
a generazione cellulare, promozione scientifica o invio VCC. t36 resta riserva.

I testi storici `STATO_r4.md` e `VALUTAZIONE_T2.md` descrivevano un fit ancora
da autorizzare: quel vincolo operativo è superato dalle prove sopra. Il loro
testo originale resta conservato. Anche i riferimenti ancora presenti in
`docs/PROGETTO.md` §0 a consenso T2 e pesi esterni non acquisiti richiedono
l'aggiornamento del proprietario dei documenti condivisi; non sono stati
modificati da DATI-TRANSFER.

## Viste disponibili e consumo ancora da verificare

L'audit ha verificato di nuovo identità e dimensioni di vista, input e split
per produzione, T, C-K562, C-iPSC, J-K562 e J-iPSC: nessun oggetto cambiato.
Le verifiche scientifiche dei metadata e dei pesi sono già nelle ricevute
`training_contract_*_check_r1.json` / `*_check_r2.json`; le quattro viste C/J
e il limite di supporto TMEM104 sono in [HANDOFF_CJ_r1.md](HANDOFF_CJ_r1.md).

- **Disponibilità:** manifest e accessi sono preparati per tutte e sei le viste.
- **Lettura e verifica degli input nel runtime:** MODELLI-ESTERNI ha comunicato
  risoluzione completa degli input produzione/T e avanzamento al fit; questa
  sessione attende le ricevute nominate per il confronto indipendente.
- **Consumo della loss:** il completamento dei due fit ESM2 non è ancora
  attestato qui. RUNNING, il download o la costruzione dello store non lo provano.
- **Beneficio predittivo:** non valutato da DATI-TRANSFER; resta competenza di
  VALIDAZIONE. Nessuna promozione è implicita nel passaggio di fase.

MODELLI-ESTERNI rimane unico proprietario di esecuzione, monitoraggio e raccolta,
anche per i successivi C/J. Questa ripresa non avvia nuovi job, non duplica
download o fit, non cambia le viste e non apre nuove ingestioni.

## Verifica al ricevimento degli artefatti

Ricevere solo i file nominati dalla raccolta autorizzata, con hash e revisione:
`complete.json`, `resolution_receipt.json`, `fit/manifest.json` e il `prepared`
corrispondente. `verify_external_consumption.py` confronta la ricevuta completa
con la vista congelata: chunk, identità, pesi, esclusioni, contesti, target,
maschere e codice. Non basta un marker COMPLETE privo di ricevuta coerente.

Successivamente verificare gli array di predizione e la loro interfaccia,
tenendo separata l'identità del modello dal beneficio e dall'ammissione della
scala da VALIDAZIONE. La verifica metadata non si presenta come controllo
numerico indipendente delle predizioni. Non recuperare bundle, notebook o
HTML dei job falliti, che possono contenere i riferimenti privati.

D-053 resta aperta: mapping guide Datlinger 2017/2021, ricomposizione e controlli
HIPSCI genome-wide fitness/nonfitness, consumer appreso KO/CRISPRa e lacune
nominate in `coverage_ledger_r2.json`. Copertura della vista CRISPRi congelata
e completamento dell'intero catalogo restano affermazioni distinte.

## Test e aggiornamento pronto per i documenti condivisi

I 24 test DATI-TRANSFER passano in `tests_scientific_r3.txt`; il controllo
documentale più recente prima di questa nota è r10, passato. La suite generale
precedente conserva tre errori per `cell_eval2.config` mancante: non si dichiara
interamente verde. Questa ripresa esegue soltanto verifiche di stato e hash.

Testo pronto da integrare a cura di VALIDAZIONE:

> T2 è completato e gli effetti di produzione sono consegnati e verificati;
> non attende più consenso al fit. I due job ESM2 di produzione e T risultano
> attivi alla verifica delle 23:13 dell'8 ottobre. Le sei viste congelate
> mantengono la propria identità; il consumo finale ESM2 e il beneficio
> predittivo restano da verificare. Sono disponibili anche i quattro contratti
> C/J K562/iPSC, senza modifiche ai dati dei fit già avviati. D-053 resta aperta.
