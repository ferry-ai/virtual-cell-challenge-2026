# R-LAB — corpus e artefatti cellulari disponibili

- **Stato:** in corso: esecuzione del binario dati di [R-LEAD](strategia-scientifica.md) per il mandato D-053
  (tutte le linee e i contesti idonei) e per l'acquisizione completa chiesta dal proprietario il 3/10. Piano, sorgenti
  e misure: [ingestione completa](../../reports/sorgenti/ingestione_completa_2026-10-03/README.md). Che cosa entra in un
  training lo decide R-LEAD con ruoli e fold registrati.
- **Aggiornato:** 3 ottobre 2026, 23:20 CEST (ora letta con `date`). La pausa delle 19:51 è stata tolta dal messaggio
  del proprietario della sera, che autorizza i job necessari al piano senza riavviare per intero la vecchia coda.
  Stato dettagliato fino alle 19:55 nella [consegna](../../reports/sorgenti/ingestione_completa_2026-10-03/HANDOFF_CLAUDE2.md);
  la versione precedente di questa scheda è nello [storico](../storico/consolidamento_2026-10-03/docs/piani/piano-giorno-2026-09-30.md).
- **Assegnazione:** regia dei job dal 3/10 23:08: Claude Code, sessione `5eacdf` (R-LEAD); claude2 (`c7c07a`) e
  `22d21f` inattive. Gli adattatori consegnati da Codex restano nella sua cartella `adattatori_codex/`, non
  tracciata e non toccata.
- **Aggiornamento del 4/10, 00:09 CEST (sessione `d0100a`, subentrata alla `5eacdf`):** HEK293T chiusa dalla verifica
  di linea (223 shard, 4.534.299 cellule, 63,12 GB,
  [ricevute](../../reports/sorgenti/ingestione_completa_2026-10-03/orion/esito_verifica_hek293t_r1/line_complete.json));
  HCT116 con le quattro parti concluse e la verifica in corsa dalle 23:59; CD4 `D1_Rest` in verifica per file dalle
  00:04 e `D1_Stim8hr` 0/2 e 1/2 in corsa dalle 23:35 (20 parti in coda); Southard vivo su `queue2` (battito 23:51).
  Le righe sotto descrivono lo stato delle 23:15.
- **Job verificati alle 23:15 CEST:**
  - Kaggle CPU (`davideferrante11`): parti Orion `vcc-orion-hct116-p3of4-r3` e `vcc-orion-hek293t-p{0,1,2}of8-r3` in
    esecuzione dalle 23:08 ([log di lancio](../../reports/sorgenti/ingestione_completa_2026-10-03/kaggle_cpu/lancio_orion_r2.jsonl)),
    scelte prima delle parti CD4 perché completano due linee. Concluse dopo la pausa: HCT116 1/4 r3, CD4 `D1_Rest` 0/2,
    il kernel KOLF lento.
  - Colab: `queue2` vivo (battito alle 21:11 UTC) con Southard r3 (job 132); `queue` muto dalle 19:57 UTC e senza job.
- **Prossimo passo:**
  1. A parti Orion finite: le loro ricevute, poi la verifica di linea di HCT116 e HEK293T
     (`kaggle_cpu/build_orion_verify.py`), che chiude le due linee se l'unione coincide con la lista congelata.
  2. Le parti CD4 rimaste, nell'ordine di `kaggle_cpu/fill_sessions.py`, una chiamata per volta e mai da un ciclo
     automatico (E-20261003-001), lasciando sessioni CPU libere per i job di R-LEAD.
  3. DLD-1 (adattatore dalle matrici h5 per canale, prima la MOI bassa), Mixscale e VIPerturb (sonda RDS r2 già
     committata), microglia e PerturbFate, secondo la consegna.
  4. Per ogni linea chiusa: pubblicazione o montaggio come output di kernel, gemelli compatti e riga
     nell'inventario riconciliato di [R-DATI](dati-affidabilita.md).

## Ingestione completa: filoni

Per ogni dataset, completo vuol dire tre cose:
- **conteggi riconciliati:** cellule grezze = idonee + esclusioni per motivo, e idonee = righe negli shard;
- **ricevute:** sha256 di ogni shard su Drive;
- **verifica indipendente:** una rilettura da un altro runtime.

Il dettaglio di sorgenti e misure è nel [README](../../reports/sorgenti/ingestione_completa_2026-10-03/README.md).

| Filone | Stato al 3/10 23:15 | Prossimo passo | Output |
|---|---|---|---|
| Southard RPE1 + Hs27 (CRISPRa), 850.225 + 447.301 cellule | job 132 in corsa su `queue2` | ricevute alla fine; verifica da un altro runtime | `j09_southard_r3` su Drive |
| Verifica dell'archivio (816 + 4.334 file) | conclusa (133–134, codice 0) | — | `archivio_verify_2026-10-03_r2/out_*_r2` |
| KOLF pan-genome, 2.659.209 cellule | chiuso: due parti verificate da un altro kernel, 133 shard, 18,39 GB | gemelli compatti e campioni annidati quando entra in un corpus | output dei kernel `vcc-kolf-pan-*` |
| Orion HCT116 3.409.169 + HEK293T 4.534.299 | HCT116 0/4–2/4 e HEK293T 3/8–7/8 concluse (r3); HCT116 3/4 e HEK293T 0/8–2/8 in corsa | verifica di linea (`build_orion_verify.py`) | output dei kernel `vcc-orion-*-r3` |
| CD4 completo, 12 file, 33,6 milioni di cellule | `D1_Rest` 0/2 e 1/2 concluse; 22 parti in coda | `fill_sessions.py`, una chiamata per volta | 24 parti da 7–9 GB, verifica per file |
| Mixscale (5 RDS) e VIPerturb | sonda RDS r2 committata, non lanciata | sonda, poi conversione | shard di contratto |
| DLD-1, microglia, PerturbFate | struttura di DLD-1 letta (MOI bassa 1.196.592 cellule); metadati degli altri | adattatori | shard di contratto |
- **Dipendenze:** [R-LEAD](strategia-scientifica.md), [sorgenti](../../reports/sorgenti/README.md)
  e [modelli](../../reports/modelli/README.md). Dati pesanti esterni a Git.

## Che cosa esiste

| Materiale | Evidenza e limite |
|---|---|
| Corpus, adattatori, QC, inventari e job | [Indice del corpus](../../reports/sorgenti/corpus_cellulare_2026-09-30/README.md). Le versioni descrivono acquisizioni successive: disponibilità e checksum si verificano sulla macchina destinataria |
| Modello, prepass, split, descrittori ed export originali | [risposta_biologica](../../reports/modelli/risposta_biologica_2026-09-30/). Codice usato nei training; preservarlo e correggere una copia nuova |
| R1, primo training | [ESITO](../../reports/modelli/cellnet_tecnico_2026-10-01/ESITO.md): verifica tecnica non interamente passata |
| R2, corpus esteso | [ESITO](../../reports/modelli/cellnet_esteso_2026-10-01/ESITO.md): verifica tecnica con misure; braccio `desc` usato in t29, non promosso |
| R3, seconda ondata | [ESITO](../../reports/modelli/cellnet_completo_2026-10-01/ESITO.md): training completato, collasso `ident`; [diagnosi](../../reports/analisi/lead_audit_2026-10-01/AGGIORNAMENTO_R3.md) |
| Quarto training, terza ondata + floor | [Protocollo](../../reports/modelli/cellnet_terza_ondata_2026-10-01/PROTOCOLLO.md): nessun esito registrato; verifica tecnica che non comprende il banco richiesto dopo t29 |
| Archivio e copie remote (2–3/10) | [Archivio cloud](../../reports/sorgenti/archivio_cloud_2026-10-02/README.md): inventario per file, specchio su Drive in corso, Kaggle verificato; [riconciliazione e ingestione](../../reports/sorgenti/archivio_cloud_2026-10-02/INGESTIONE.md): Jiang 2025 e Mixscale sono un'unica sorgente, Southard incompleto, campioni CD4/Orion e ruoli registrati prima dell'integrazione |

H1 train/val e HIPSCI sono già stati usati nel corpus; non riaprire acquisizioni sulla base
di vecchie liste d'attesa. H1 test resta riserva chiusa e non è un contesto nuovo per un
modello che vede H1 train/val. Presenza nel catalogo e uso nel fit sono cose diverse:
il replay dopo QC di P1 determina che cosa ogni modello ha visto davvero.

## Chiusura e alternative

Questa scheda si aggiorna quando cambia l'inventario o termina un'esecuzione di R-LEAD.
Una consegna si chiude con manifest, hash, esito e dipendenze mancanti espliciti. Dal 3/10 il mandato del
proprietario è acquisire per intero tutte le sorgenti di INGESTIONE §5, e supera la regola precedente («non deve
acquisire ogni sorgente possibile»). L'uso nel training resta legato a una lacuna P0/P1 o a un confronto
preregistrato. Un altro training tecnico non soddisfa il ramo c di t29.

[Cronologia integrale e incarichi precedenti](../storico/rinnovo_2026-10-01/docs/piani/piano-giorno-2026-09-30.md).
