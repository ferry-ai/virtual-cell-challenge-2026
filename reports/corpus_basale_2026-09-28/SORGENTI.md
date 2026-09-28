# Le sorgenti dell'encoder di contesto: una decisione per ciascuna

28 settembre 2026, notte. Richiesta del proprietario (27/09 sera):
- per ogni sorgente il ruolo, il sottoinsieme, il modo d'integrazione, che cosa è stato davvero eseguito e l'eventuale
  ostacolo;
- se una sorgente non si riesce a provare, resta un esperimento esplicito e motivato, e non si presenta come usata.

Scrive il lead (Claude, sessione del proprietario); orari letti da `date`. Etichette: **misurato**, **interpretazione**,
**ipotesi**, **proposta**. Il disegno dell'encoder e della prova è in
[`../encoder_contesto_2026-09-28/DISEGNO.md`](../encoder_contesto_2026-09-28/DISEGNO.md); la regola, fissata prima delle
corse, in [`../encoder_contesto_2026-09-28/RISULTATI.md`](../encoder_contesto_2026-09-28/RISULTATI.md).

**Stato del documento:** bozza scritta durante la notte. Le righe «eseguito» si aggiornano man mano che le corse
finiscono; quello che non è scritto qui come misurato non è stato eseguito.

## Tabella

| Sorgente | Ruolo | Sottoinsieme | Integrazione | Eseguito (misurato) | Ostacolo o passo seguente |
|---|---|---|---|---|---|
| Controlli delle nostre sorgenti CRISPRi | pre-addestramento dell'encoder; per K562, CD4, HCT116, HEK293T e KOLF2.1J anche contesti della rete | solo controlli: guide non miranti di Replogle (K562 genome-wide ed essenziale, RPE1), righe non miranti CD4 per donatore e condizione, pool NTC di HCT116, HEK293T, KOLF2.1J, A549, VIPerturb-seq (Flex), Southard Hs27, HIPSCI (in pool, e 19 linee dello schermo mirato) | corpus `ours`, condizione `ours`; nei disegni la famiglia tenuta fuori esce da tutti i corpora (liste esplicite) | corpus costruito alle 03:18: 3.326 profili in 32 contesti (`corpus_ours.py --group ours`) | vedi sotto per le corse |
| Controlli di A, B, C (gara) | pre-addestramento e, in produzione, l'embedding dei contesti di gara | 46 sottoinsiemi casuali disgiunti di 400 cellule per contesto (18.400 cellule ciascuno) | nel corpus di `ours`; mai contesti di prova dei disegni E1/E2 | corpus costruito: 138 profili | nessuno |
| DepMap 24Q4 (bulk) | ampiezza: molte linee per le direzioni di variazione basale | 1.667 linee; escluse alla costruzione A549, HCT116, HEK TE, HepG2, Jurkat e K562; poi le liste di ogni disegno (per CD4 le linee T, per K562 anche P2URK562) | nel corpus di `ours` (piattaforma `bulk`) | corpus costruito: 1.667 profili | bulk, un profilo per linea: nessuna replica dentro il contesto |
| Tahoe-100M, controlli DMSO | ampiezza a cellula singola: 50 linee tumorali con piastra | `drug == DMSO_TF`, somme per linea × piastra; stanotte da un sottoinsieme sistematico dei frammenti (uno ogni cinque) | corpus `tahoe`, condizione `ours+tahoe` contro `ours` | in corso (vedi sotto) | l'estrazione completa di tutti i 3.388 frammenti gira su Kaggle, ma il suo piano legge un frammento alla volta |
| Tahoe-100M, bracci farmacologici | ruolo distinto: molte linee per la stessa perturbazione, per misurare se il contesto modula la risposta a una scala che il CRISPRi non ha | proposta: farmaci con un solo bersaglio genico che gli schermi CRISPRi silenziano, più controlli positivi forti | proposta: banco T1 (differenze fra linee tenute fuori, come E2) e T2 (ponte con il knockdown dello stesso gene) | nulla estratto; codice e disegno affidati a codex (esecuzione `20260928-032819-v2-tahoe-arms`) | da leggere e provare; non è usato |
| scBaseCount | ampiezza di contesti umani a cellula singola (primari e linee) | proposta: umano, 10x, campioni non trattati con provenienza verificabile, tetto per studio | condizioni `ours+scbasecount` e `ours+both` | **nulla**: non è stato scaricato niente | accesso solo da un progetto Google Cloud abbonato al dataset sul Marketplace; serve il proprietario |

## Note per sorgente

(Da completare con i risultati della notte.)
