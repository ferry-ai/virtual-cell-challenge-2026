# reports — l'evidenza del progetto, per argomento

Ogni cartella è la prova di ciò che si è visto in una data: misure, regole registrate prima,
uscite dei comandi, rapporti degli agenti e il codice che li ha prodotti. **Qui non si
corregge nulla**: una nuova esecuzione va in una cartella nuova, e una conclusione sbagliata
si corregge con un checkpoint o una scheda del registro. Le regole per chi scrive sono in
[CLAUDE.md](CLAUDE.md).

Dal 28 settembre 2026 le 126 cartelle stanno in otto categorie (D-046). Ogni categoria ha un
README con una riga per cartella: **data, nocciolo, se vale ancora e quanto pesa oggi**.

## Da leggere per primi (stato al 28 settembre)

| # | Evidenza | Perché conta |
|---|---|---|
| 1 | [Lezioni dai nostri invii](invii/lezioni_invii_2026-09-28/RISULTATI.md) | Dal t16 nessun cambio della ricetta si distingue dal rumore del seme; il divario con i primi 100 sta soprattutto nell'MSE |
| 2 | [La `mse` ufficiale = 1 + E/4786](trasferimento/risposta_comune_2026-09-26/RISULTATI.md) | Le nostre previsioni sono quasi ortogonali agli effetti veri: più energia, più errore |
| 3 | [Banco HepG2 con lo scorer vero](generatore_e_banchi/banco_hepg2_v2_2026-09-26/RISULTATI.md) | L'unico confronto sui sei membri veri fuori dalla classifica (un contesto, bersagli essenziali) |
| 4 | [Ablazione del t23](trasferimento/ablazione_t23_2026-09-27/RISULTATI.md) | Aiuta togliere i geni che una sola sorgente stima, non la «quota condivisa» |
| 5 | [Artefatto del pseudoconteggio](sorgenti/pseudoconteggio_2026-09-27/RISULTATI.md) | Uno stimatore leggeva un gene senza conteggi come indotto; cache r9 e t25 |
| 6 | [Atlante](trasferimento/atlante_2026-09-26/RISULTATI.md) | Il trasferimento su migliaia di bersagli; linea e laboratorio pesano più dello stato cellulare |
| 7 | [Modelli su molti contesti](modelli/README.md) | Rete, encoder, modello a cancelli e Tahoe: il contesto letto dai controlli non aiuta ancora; lo scambio vale quanto il contesto giusto |
| 8 | [Ponte Flex–3'](sorgenti/ponte_flex_2026-09-28/RISULTATI.md) | La gara è in Flex, le sorgenti in 3': il divario non è solo rumore |
| 9 | [Revisione critica del 28/09](analisi/revisione_criticita_2026-09-28/REVISIONE.md) | Criticità, bias, evidenze citate ma assenti, e la valutazione delle critiche di Alfredo |

## Le categorie

| Categoria | Che cosa contiene | Cartelle | Periodo | Indice |
|---|---|---|---|---|
| `gara/` | Le regole del gioco: contratto dello scorer, ancore ufficiali, classifica, identità dei contesti A/B/C | 8 | 11–22/09 | [gara](gara/README.md) |
| `invii/` | I nostri invii: previsione registrata prima, file inviati, punteggi, confronti, lezioni | 29 | 12–28/09 | [invii](invii/README.md) |
| `sorgenti/` | I dati: estrazioni, universi genome-wide, stimatori e loro difetti, ricerche e schede di sorgenti, corpora basali | 21 | 17–28/09 | [sorgenti](sorgenti/README.md) |
| `trasferimento/` | La ricetta di produzione (media di sorgenti per lo stesso bersaglio) e le sue varianti, provate su sorgenti tenute fuori | 15 | 17–27/09 | [trasferimento](trasferimento/README.md) |
| `modelli/` | Modelli appresi su molti contesti per bersagli e contesti nuovi (R-V2, F9–F10) | 5 | 27–28/09 | [modelli](modelli/README.md) |
| `generatore_e_banchi/` | Dagli effetti alle cellule: chiamate spurie del generatore, DE dello scorer, banchi a sei metriche | 9 | 17–27/09 | [generatore e banchi](generatore_e_banchi/README.md) |
| `analisi/` | Analisi dello stato, revisioni esterne, ipotesi di ricerca | 7 | 19–28/09 | [analisi](analisi/README.md) |
| `storico/` | Linee chiuse dell'11–19 settembre (codice archiviato), sonde dei dati, infrastruttura ritirata | 34 | 11–19/09 | [storico](storico/README.md) |

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
  e MSE (vedi la [revisione critica](analisi/revisione_criticita_2026-09-28/REVISIONE.md), §2).

## Percorsi scritti prima del 28 settembre

Checkpoint e report non si modificano, quindi citano i percorsi com'erano. La regola è una:
**`reports/<cartella>/…` oggi è `reports/<categoria>/<cartella>/…`**, con il nome della
cartella invariato; le otto analisi dell'11–15 settembre sono passate da `docs/` a
`docs/storico/`. Per trovarla: `ls -d reports/*/<cartella>`. Seguono la stessa regola il
controllo documentale (`scripts/31_check_docs.py`) e le ricette (`config.repo_file` nello
stadio 100), e un test fallisce se due categorie avessero una cartella con lo stesso nome.

## Il codice di ricerca che sta qui

Nelle cartelle ci sono circa 22.000 righe di Python, il doppio del codice «vivo» di `scripts/`
e `src/`. Sono la registrazione di come sono stati ottenuti i risultati, ma alcuni file fanno
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

Solo `kolf_sums.py` ha un test. Gli altri non sono coperti dai test del codice vivo. Il
28 settembre sono cambiate soltanto le righe che calcolano la radice del repository e i
percorsi fra cartelle (+1 livello). Tutti i 95 script che rispondevano a `--help` prima dello
spostamento rispondono anche dopo.
