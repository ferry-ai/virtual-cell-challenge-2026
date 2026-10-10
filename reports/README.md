# reports — evidenze datate, indicizzate per argomento

Le cartelle conservano misure, protocolli, uscite e codice delle esecuzioni. I report non
si riscrivono dopo un risultato: una correzione ha una nuova evidenza e un rimando nel
registro. Le regole sono in [CLAUDE.md](CLAUDE.md). Gli indici di categoria si aggiornano.

**Per scegliere il lavoro:** [PIANI](../docs/PIANI.md) e R-LEAD. Per scegliere cosa leggere:
[AMBITI](../docs/AMBITI.md), solo la sezione pertinente. Non leggere tutti i report né
seguire i «prossimi passi» datati come ordini attuali.

## Evidenze che cambiano il prossimo passo

| Domanda | Fonte |
|---|---|
| Quali invii esistono, di chi sono e come sono andati? | [invii](invii/README.md): punteggi ufficiali di Davide (td) e di Alfredo (ta), e la [mappa dei nomi](invii/README.md#nomi-td-e-ta-mappa-dei-candidati) con entry ID, stato e provenienza (D-058) |
| Che cosa ha bocciato t29? | [CP-0055](../docs/checkpoints/0055-t29-rete-cellulare-punteggio.md) e [invii](invii/README.md): candidato r2 `desc`, banco a sei membri richiesto prima del prossimo invio neurale |
| Quali difetti riprodurre? | [Nota training](analisi/lead_audit_2026-10-01/NOTA_TRAINING.md) e [diagnosi r3](analisi/lead_audit_2026-10-01/AGGIORNAMENTO_R3.md): split, pesi, controlli, baseline e gate |
| Quali risultati e input esistono? | [Modelli](modelli/README.md) e [sorgenti](sorgenti/README.md): esiti tecnici distinti da promozioni; disponibilità pesante da verificare |
| Che cosa non si può chiamare score o conferma? | [Credibilità degli score](analisi/lead_scientist_2026-09-29/SCORE_CREDIBILITA.md), CP-0050: ancore aggregate e riserva già vista |
| Perché il generatore resta un confronto separato? | [t28](../docs/checkpoints/0052-t28-punteggio-ufficiale.md), esito ufficiale non conclusivo, e [banco HepG2](generatore_e_banchi/banco_hepg2_v2_2026-09-26/RISULTATI.md), sviluppo su un contesto |
| Che cosa ha cambiato il rinnovo? | [Registro del rinnovo](analisi/rinnovo_repo_2026-10-01/README.md), con copie e hash della navigazione precedente |

## Le categorie

| Categoria | Domanda | Indice |
|---|---|---|
| `gara/` | Scorer, ancore, controlli e fotografie della classifica | [gara](gara/README.md) |
| `invii/` | Previsione, artefatto, punteggio ufficiale e lettura della regola | [invii](invii/README.md) |
| `sorgenti/` | Dati, estrazioni, stimatori, corpus e QC | [sorgenti](sorgenti/README.md) |
| `trasferimento/` | Ricetta per lo stesso bersaglio e sue varianti | [trasferimento](trasferimento/README.md) |
| `modelli/` | Modelli appresi, protocolli ed esiti | [modelli](modelli/README.md) |
| `generatore_e_banchi/` | Emissione delle cellule e banchi con scorer | [generatore e banchi](generatore_e_banchi/README.md) |
| `analisi/` | Audit, ipotesi, sintesi e riordini | [analisi](analisi/README.md) |
| `storico/` | Linee chiuse e infrastruttura ritirata | [storico](storico/README.md) |

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
