# reports — l'evidenza del progetto, per argomento

Ogni cartella è la prova di ciò che si è visto in una data: misure, regole registrate prima,
uscite dei comandi, rapporti degli agenti e il codice che li ha prodotti. **Qui non si
corregge nulla**: una nuova esecuzione va in una cartella nuova, e una conclusione sbagliata
si corregge con un checkpoint o una scheda del registro. Le regole per chi scrive sono in
[CLAUDE.md](../../../../reports/CLAUDE.md).

Dal 28 settembre 2026 le cartelle stanno in otto categorie (D-046): 141 il 30 settembre, più due
file sciolti in `storico/`. Ogni
categoria ha un README con una riga per cartella: **data, nocciolo, se vale ancora e quanto pesa
oggi**. Per ambito di lavoro (gara, invii, generatore, dati, modelli, set finale, operazioni,
metodo) la mappa che instrada verso queste cartelle è [docs/AMBITI.md](../../../AMBITI.md).

## Da leggere per primi (stato al 30 settembre)

| # | Evidenza | Perché conta |
|---|---|---|
| 1 | [Revisione lead del 29–30/09](../../../../reports/analisi/lead_scientist_2026-09-29/README.md), a partire da [SCOPERTE_R1](../../../../reports/analisi/lead_scientist_2026-09-29/SCOPERTE_R1.md) e [R2](../../../../reports/analisi/lead_scientist_2026-09-29/SCOPERTE_R2.md) | CD4 è già Flex; il plateau non è saturazione; ampiezza e dispersione interagiscono; la rete sulle sorgenti e Stack perdono |
| 2 | [t28 in gara](../../../checkpoints/0052-t28-punteggio-ufficiale.md), dalla tabella degli [invii](../../../../reports/invii/README.md) | Massimo osservato, non conclusivo: fedeltà e reach salgono, NMAE e Jaccard scendono |
| 3 | [Audit scientifico del 29/09](../../../../reports/analisi/lead_scientist_2026-09-29/AUDIT_SCIENTIFICO.md) | 17 invii ricostruiti; cinque inferenze del progetto corrette |
| 4 | [Credibilità degli score](../../../../reports/analisi/lead_scientist_2026-09-29/SCORE_CREDIBILITA.md) | Le ancore aggregate non convertono esattamente; la riserva del banco era già stata valutata |
| 5 | [Lezioni dai nostri invii](../../../../reports/invii/lezioni_invii_2026-09-28/RISULTATI.md) | Il divario con i primi 100 sta soprattutto nell'MSE. La lettura «dal t16 nessun cambio si distingue dal rumore» è corretta dall'audit del 29/09 |
| 6 | [La `mse` ufficiale = 1 + E/4786](../../../../reports/trasferimento/risposta_comune_2026-09-26/RISULTATI.md) | Più energia, più errore. L'ortogonalità quasi completa agli effetti veri è un'inferenza condizionata (audit del 29/09, §2.5) |
| 7 | [Banco HepG2 con lo scorer vero](../../../../reports/generatore_e_banchi/banco_hepg2_v2_2026-09-26/RISULTATI.md) | Sei membri veri fuori dalla classifica, un contesto e bersagli essenziali: dà il verso dei cambi ufficiali, non la loro entità |
| 8 | [Artefatto del pseudoconteggio](../../../../reports/sorgenti/pseudoconteggio_2026-09-27/RISULTATI.md) | Uno stimatore leggeva un gene senza conteggi come indotto; cache r9 e t25 |
| 9 | [Modelli su molti contesti](modelli/README.md) | Nessun modello appreso passa la sua regola; il contesto letto dai controlli non aiuta ancora |
| 10 | [Revisione critica del 28/09](../../../../reports/analisi/revisione_criticita_2026-09-28/REVISIONE.md) | Criticità, bias, evidenze citate ma assenti. Le azioni che ne seguono sono la scheda [R-REV](../docs/piani/revisione-critica.md) |

Nel primo elenco del 28/09 c'erano anche l'[ablazione del t23](../../../../reports/trasferimento/ablazione_t23_2026-09-27/RISULTATI.md),
l'[atlante](../../../../reports/trasferimento/atlante_2026-09-26/RISULTATI.md) e il [ponte Flex–3'](../../../../reports/sorgenti/ponte_flex_2026-09-28/RISULTATI.md),
che vale per la coppia K562 VIPerturb–Replogle e non per tutte le sorgenti.

## Le categorie

| Categoria | Che cosa contiene | Cartelle | Periodo | Indice |
|---|---|---|---|---|
| `gara/` | Le regole del gioco: contratto dello scorer, ancore ufficiali, classifica, identità dei contesti A/B/C | 8 | 11–22/09 | [gara](../../../../reports/gara/README.md) |
| `invii/` | I nostri invii: previsione registrata prima, file inviati, punteggi, confronti, lezioni | 34 | 12–29/09 | [invii](../../../../reports/invii/README.md) |
| `sorgenti/` | I dati: estrazioni, universi genome-wide, stimatori e loro difetti, ricerche e schede di sorgenti, corpora basali | 22 | 17–29/09 | [sorgenti](sorgenti/README.md) |
| `trasferimento/` | La ricetta di produzione (media di sorgenti per lo stesso bersaglio) e le sue varianti, provate su sorgenti tenute fuori | 16 | 17–28/09 | [trasferimento](../../../../reports/trasferimento/README.md) |
| `modelli/` | Modelli appresi su molti contesti per bersagli e contesti nuovi (R-V2, F9–F10) | 8 | 27–28/09 | [modelli](modelli/README.md) |
| `generatore_e_banchi/` | Dagli effetti alle cellule: chiamate spurie del generatore, DE dello scorer, banchi a sei metriche | 10 | 17–29/09 | [generatore e banchi](../../../../reports/generatore_e_banchi/README.md) |
| `analisi/` | Analisi dello stato, revisioni esterne, ipotesi di ricerca, la revisione lead del 29/09 e il riordino del 30/09 | 11 | 19–30/09 | [analisi](../../../../reports/analisi/README.md) |
| `storico/` | Linee chiuse dell'11–19 settembre (codice archiviato), sonde dei dati, infrastruttura ritirata | 34 | 11–19/09 | [storico](../../../../reports/storico/README.md) |

## Come si leggono le colonne

- **Vale?**
  - **sì**: misure ancora valide, usate nelle scelte di oggi;
  - **in parte**: vale con la correzione o la scheda indicata accanto;
  - **superato**: sostituito dal materiale indicato;
  - **storico**: registrazione datata di che cosa si vedeva o si faceva, non una guida.
- **Peso oggi:** ★★★ decide la ricetta o le scelte in corso; ★★ contesto utile o esito
  negativo che chiude una linea; ★ prova di processo, sonda o logistica.
- **Proxy:** quasi tutti i banchi dal 25/09 misurano Δ = 0,36 ΔPDS − 0,27 ΔnMAE contro una
  sorgente pubblica tenuta fuori. Non è un punteggio VCC e non vede fedeltà, reach, Jaccard
  e MSE (vedi la [revisione critica](../../../../reports/analisi/revisione_criticita_2026-09-28/REVISIONE.md), §2).

## Percorsi scritti prima del 28 settembre

Checkpoint e report non si modificano, quindi citano i percorsi com'erano. La regola è una:
**`reports/<cartella>/…` oggi è `reports/<categoria>/<cartella>/…`**, con il nome della
cartella invariato; le otto analisi dell'11–15 settembre sono passate da `docs/` a
`docs/storico/`. Per trovarla: `ls -d reports/*/<cartella>`. Seguono la stessa regola il
controllo documentale (`scripts/31_check_docs.py`) e le ricette (`config.repo_file` nello
stadio 100), e un test fallisce se due categorie avessero una cartella con lo stesso nome.

## Il codice di ricerca che sta qui

Nelle cartelle ci sono circa 60.000 righe di Python al 30 settembre, di cui circa 28.000 della sola
revisione lead del 29/09: parecchie volte il codice «vivo» di `scripts/` e `src/`. Sono la registrazione di come sono stati ottenuti i risultati, ma alcuni file fanno
da libreria per altri banchi, che li importano per percorso. **Cambiare uno di questi file cambia
i banchi che lo importano**: una versione nuova va in una cartella nuova.

| File che altri importano | Che cosa offre | Chi lo importa |
|---|---|---|
| `trasferimento/modulo_cis_2026-09-26/cis_bench.py` | bootstrap, proxy di PDS, reach e fedeltà, lettura della cache | atlante, quota condivisa, trasferimento appreso e gerarchico, quattro sorgenti, contesti, programmi, rete, bersagli nuovi |
| `trasferimento/banco_varianti_2026-09-25/noise_sim.py`, `noise_sim2.py` | `rank_pds`; `realise`, il passo di profilo del trial-01 con lo pseudobulk di 400 cellule: la «gen» dei proxy | atlante, quota condivisa, trasferimento appreso, gerarchico, quattro sorgenti, risposta comune, modulo cis |
| `trasferimento/trasferimento_appreso_2026-09-26/lct_bench.py`, `lct_bench2.py`, `basal_profiles.py` | `precision_at`, `cd4_mix_se`, variabili per gene, profili basali | atlante, quota condivisa, gerarchico, quattro sorgenti, contesti, corpus basale, universi nuovi |
| `trasferimento/atlante_2026-09-26/atlas_bench.py` | `Universe`, il lettore degli universi | quota condivisa, profondità, ponte Flex, universi nuovi, rete |
| `trasferimento/quota_condivisa_2026-09-27/share_panel_bench.py` | il banco sul pannello | ablazione del t23, modello a cancelli, rete |
| `modelli/modello_contesto_2026-09-27/gated_bench.py` | contrasti E1/E2 e permutazioni | rete |
| `modelli/rete_contesti_2026-09-27/` (`pool.py`, `train.py`, …) | la rete e il suo dataset | rete r2, encoder |
| `sorgenti/universo_kolf_2026-09-27/kolf_effects.py`, `kolf_sums.py` | lo stimatore degli universi nuovi (KOLF2.1J, A549, VIPerturb-seq, HIPSCI) | universi nuovi, ponte Flex, corpus basale; test in `tests/test_kolf_sums.py` |
| `sorgenti/universo_2026-09-26/orion_universe.py` e simili | costruzione degli universi | universi corretti |
| gli stadi 98, 100, 102 e 104 di `scripts/`, importati per percorso | stima delle sorgenti, effetti per contesto, canale di magnitudine | universi, banchi del 25–27/09 |
| `analisi/lead_scientist_2026-09-29/learning/preflight.py`, `ledger.py` | il controllo del manifest di un job e il registro degli incidenti in sola aggiunta; hanno i loro test accanto | i job nuovi, secondo `docs/ERRORI.md` |

Hanno un test `kolf_sums.py` (`tests/test_kolf_sums.py`) e, dal 28 settembre, i proxy dei banchi
(`tests/test_proxy_banchi.py`: `pds_proxy`, `rank_pds`, `fidelity_proxy`, `realise`, e la parità di
`realise` con il passo di profilo che lo stadio 45 applica davvero). Nelle cartelle ci sono
inoltre test propri, accanto al codice che provano: 54 file `test_*.py` il 30 settembre, 50 nella
revisione lead, fra cui quelli di `preflight.py` e `ledger.py`; non girano con la suite. Il resto
non è coperto. Il
28 settembre sono cambiate soltanto le righe che calcolano la radice del repository e i percorsi
fra cartelle (+1 livello): tutti i 95 script che rispondevano a `--help` prima dello spostamento
rispondono anche dopo.
