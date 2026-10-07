# Che cosa proporrei di eliminare (niente è stato eliminato)

7 ottobre 2026, sessione `6cf149d8`. Richiesta del proprietario in chat: non eliminare dati vecchi,
segnare a fine lavoro ciò che si vorrebbe togliere. Tipo: **proposta**. Ogni voce dice perché è
rigenerabile o inutile; nessuna riguarda grezzi, banche, campioni o ricevute.

## Kaggle

| Che cosa | Perché | Rischio |
|---|---|---|
| `davideferante/vcc-fonte-tian2019-ipsc-r1`, `davideferante/vcc-fonte-norman2019-r1` | job in ERROR sulla guardia d'identità, nessuna stima; sostituiti da r3 e r2. Log e stato sono già in `derivazioni/<fonte>/r1/failure/` | nullo |
| `davideferrante11/vcc-fit-banca-canonica-r1` **oppure** `-r2` | due fit identici byte per byte; ne basta uno montabile. Tenerne due serve solo come prova del riuso, già in `fit/riuso_r2.json` | nullo, ma toglierei r2 e terrei r1 |
| I kernel in ERROR delle campagne precedenti (originali sostituiti da `retry`, `resume`, `access`) | i registri `supersedes_failed` dicono già quale versione vale | **prima serve un inventario**: non l'ho fatto in questa sessione, non proporrei cancellazioni alla cieca |

## Radice dati locale

| Che cosa | Perché |
|---|---|
| `processed/banca_canonica_2026-10-07/dataset_derivati_r1/` (38 MB) | copia di stage delle tabelle di `derivati_r1/`, già caricata come dataset |
| `processed/banca_canonica_2026-10-07/rows_r1/*/samples/**/bank_rows.csv` | doppioni delle `rows.csv`, scaricati dal filtro per nome; non sono nel manifest |

## Repository (file non tracciati di sessioni precedenti)

Non li ho toccati né committati: non sono miei e non so se servono ancora ai loro autori.

| Che cosa | Perché li toglierei |
|---|---|
| `reports/modelli/percorso_riusabile_2026-10-05/generation_successors_r1/heartbeat_*_r1/` (8 cartelle) | battiti del polling del t36, concluso; lo stato finale è in `ESECUZIONE_r19.md` |
| `reports/analisi/riconciliazione_banca_2026-10-05/docs_check_r1…r7.txt`, `stage_paths_freeze*.txt` | uscite intermedie del controllo documenti |
| `…/agenti/grok_transfer_esteso_r2/_ids.txt`, `_paths.py`, `_paths.txt` | file di appoggio di un worker terminato |
| Le cartelle `__pycache__/` dentro `reports/` | rigenerabili; già ignorate da git |
| `derivazioni/tian2019_ipsc/r2/` di questa cartella | pacchetto preparato e mai lanciato |

## Windows

| Che cosa | Perché |
|---|---|
| Attività pianificate «VCC2026 Ciclo giornaliero» e «VCC2026 Guardiano» | chiamano `scripts\ciclo.cmd`, che non esiste più dal ritiro dell'orchestratore (23/09); la prima parte ogni giorno alle 08:30 e fallisce. È un'impostazione di sistema: la toglie il proprietario |

## Che cosa **non** proporrei di eliminare

I 189 GB di campioni cellulari su Kaggle non sono consumati da nessun trainer di questo percorso, ma
servono alle reti sulle cellule: restano. Lo stesso vale per i derivati dei bracci KO e CRISPRa.
