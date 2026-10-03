# R-DATI — inventario riconciliato e lacune dei dati

- **Stato:** in corso dal 3/10 sera come parte del binario dati di [R-LEAD](strategia-scientifica.md): il mandato
  non negoziabile D-053 chiede un inventario riconciliato col catalogo prima di congelare il prossimo corpus
  principale ([GENERALIZZAZIONE §2.1](../GENERALIZZAZIONE.md#21-copertura-integrale-vincolo-non-negoziabile)).
- **Aggiornato:** 4 ottobre 2026, 00:04 CEST. Testo precedente nello
  [storico del consolidamento](../storico/consolidamento_2026-10-03/docs/piani/dati-affidabilita.md).
- **Assegnazione:** regia nella sessione `d0100a` (R-LEAD, subentrata alla `5eacdf` il 3/10 alle 23:34); le
  sottoattività già consegnate restano a chi le ha fatte (sotto). Un agente che prende una voce la registra qui con
  sessione, file e output.
- **Fatto dalla sessione `d0100a`:** prima stesura dell'[inventario riconciliato](../../reports/sorgenti/inventario_riconciliato_2026-10-04/README.md)
  (passo 1: 8 gruppi su 21 nelle cellule del pilot, 10 nelle ancore, lacune e lavoro per voce; gruppi e ruoli ancora
  da adottare); studio dei campioni annidati con regola congelata prima dei numeri
  ([protocollo](../../reports/modelli/rete_ancorata_v4_2026-10-03/CAMPIONI_ANNIDATI.md), kernel
  `rcell-v4-nested-h1-r1` in corsa dal 3/10 alle 23:52; passo 3, solo per il corpus del pilot). Il passo 2 (aggregati
  per le voci senza tabella) non è iniziato.
- **Prossimo passo:**
  1. **Inventario riconciliato:** per ogni voce del catalogo (gli 8 gruppi del pilot, le 13 voci in più della
     [proposta di gruppi](../../reports/sorgenti/ingestione_completa_2026-10-03/orion/line_groups_expanded_v1.json),
     le risorse ancora in ricognizione) fonte e versione, gruppo biologico, linea, donatori, stati, studi, modalità
     CRISPRi/a/KO, ruolo (cellule, aggregati, entrambi), numeri attesi e ammessi, stato d'integrazione, lacuna e
     azione. Distinguere gruppo biologico, linea clonale, donatore, stimolo e studio; alias e famiglie correlate si
     escludono insieme nei fold.
  2. **Aggregati per le voci senza tabella nel cubo** (oggi 10 gruppi), calcolati in streaming sulle cellule
     ammesse e rispettando le esclusioni dei fold.
  3. **Campioni annidati 32/64/128** per contesto e bersaglio, letti dai gemelli compatti: copertura di guide,
     librerie, donatori e stati, perdita d'informazione contro i riassunti completi, probabilità di campionamento.
     Le soglie di sufficienza si fissano prima di leggere i numeri.
- **Dipendenze:** [R-LAB](piano-giorno-2026-09-30.md) per le cellule verificate; R-LEAD per ruoli e fold.
- **Chiusura:** inventario riconciliato e verificato per ogni voce, con ogni assenza motivata secondo §2.1
  (validazione, duplicazione, qualità, incompatibilità verificata, accesso) e le lacune rimediabili ancora aperte
  come lavori assegnati. Per D-053 l'acquisizione e l'integrazione non si fermano a un sottoinsieme comodo.

## Consegna utile

**Sottoattività di archivio, richiesta in chat il 3 ottobre:** Codex, sessione
`01a10114-058a-7342-9f0e-7942cc43ad6c`, portatile Windows, presa in carico alle 12:43 CEST.
File e nuove prove in [libera_spazio_2026-10-03](../../reports/sorgenti/libera_spazio_2026-10-03/README.md):
prima rimozione conclusa alle 12:49 CEST (14,517 GiB di copie già verificate su Kaggle).
I job Colab 130–131 sono partiti il 3/10 alle 14:00 CEST; alla verifica delle 14:40
non erano ancora visibili ricevute degli hash. Il proprietario affida ora la regia a Claude1;
il monitor periodico Codex è sospeso. Stato, consegna Claude2 e correzioni nella
[revisione ingestion](../../reports/sorgenti/revisione_ingestion_2026-10-03/README.md).

**Ingestion, precisazione del proprietario del 3/10:** Drive ha 5 TB di capacità dichiarata;
l'obiettivo CD4 è l'acquisizione completa delle cellule idonee, senza tetto definitivo di
10 cellule per guida. Spazio libero, copie già presenti e dimensione degli output vanno
misurati. Campioni iniziali e bilanciamento del training sono scelte distinte dall'archivio.
Codex termina la revisione locale e consegna a Claude1 la prosecuzione; nessun nuovo job
o seguito Claude2 è stato avviato durante il passaggio. La revisione conserva i dettagli
e le condizioni di adozione; non cambia i ruoli e gli split di R-LEAD.

Una tabella di lacune con domanda, file necessario, ruolo C/T/J, unità e maschere,
controlli/repliche/guide, accesso, byte e limite che risolve. Distinguere overlap dei target
e copertura dei geni di risposta; zero overlap con i 300 non esclude una sorgente.
Non ripetere l'inventario sulla base delle liste d'attesa del 25/09.

CD4 è già Flex; H1 train/val e HIPSCI sono nel corpus. I risultati e le limitazioni
sono nell'[indice delle sorgenti](../../reports/sorgenti/README.md); presenza e uso reale
si verificano nei manifest e nel replay del training. H1 test resta chiusa.

## Chiusura e alternative

Una lacuna si chiude con file/QC verificati e ablation a split fisso, oppure con la prova
che quei dati non permettono il confronto. Se il problema è campionamento o qualità,
correggerlo prima di aggiungere cellule. Dal 3/10 (D-053) tutte le sorgenti e i contesti idonei
vanno integrati nel ruolo che i loro dati consentono; il testo precedente («nessun obbligo di
acquisire tutte le sorgenti») è superato ed è conservato nello storico.

[Audit e ipotesi H7–H10 del 24–26/09](../storico/rinnovo_2026-10-01/docs/piani/dati-affidabilita.md).
