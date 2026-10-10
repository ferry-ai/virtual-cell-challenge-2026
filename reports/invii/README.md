# invii — gli invii della squadra alla classifica di validazione

**Nomi dal 10 ottobre 2026 (D-058):** `td XX` = Davide, `ta XX` = Alfredo, obbligatori nei nuovi
riferimenti ([regola](../../docs/PROCEDURE.md#2-le-regole-dellinvio)). Le cartelle di questo indice sono
tutte di Davide e conservano il nome storico: `prediction_t36_2026-10-06/` è td 36. Gli invii di Alfredo
stanno sul branch `codex/teammate-rlead` e si citano per branch e commit. I numeri 30, 31 e 36–39 esistono
in entrambi i namespace con candidati diversi: la [mappa td/ta](#nomi-td-e-ta-mappa-dei-candidati) li
separa con entry ID, stato verificato e provenienza.

Due tipi di cartella, più due riepiloghi:
- **`prediction_t<NN>_<data>/`**: la previsione e la regola di lettura, **registrate prima**
  di generare (`prediction.json`). Dopo il punteggio c'è `comparison.json`, con l'esito letto
  secondo quella regola. Nessuno di questi file si modifica dopo la registrazione. Per i candidati
  nuovi il nome porta l'autore: `prediction_td<NN>_<data>/` o `prediction_ta<NN>_<data>/` (D-058).
- **`trial_<data>/`**: una per giorno di lavoro sugli invii. Contiene i testi scritti prima, i
  manifesti degli stadi 45 e 48 e l'output di `vcc` salvato così com'è (`submit_*`, `status_*`).

Procedura e regole: [PROCEDURE §1–2](../../docs/PROCEDURE.md). Indice generale: [../README.md](../README.md).

**Stato, letto il 10/10 alle 16:00 dalle ricevute dei due branch:** il massimo osservato fra gli invii
valutati della squadra resta [td 38](prediction_t38_2026-10-09/comparison.json), **0,148922**, +0,001673
contro td 36: dentro la soglia ±0,005 registrata prima, quindi **non conclusivo**; un solo invio, stabilità
non dimostrata ([CP-0074](../../docs/checkpoints/0074-t38-crispri-piu-ko-punteggio-ufficiale.md)). Il più
alto di Alfredo è ta 36, 0,141392. Dopo td 38, **td 39** (entry `C49E3QzIDZk0LGmXPCPP`) è caricato dal 10/10
alle 01:29 ed era in `scoring` all'ultima lettura salvata, alle 01:33
([ricevuta](../modelli/dati_transfer_2026-10-08_01a11c34/CONSEGNA_T39_RICEVUTA_r1.md)): nessun punteggio
registrato, la lettura resta da fare (PROCEDURE §2, punto 7). **ta 39** è valutato 0,140816. Il confronto fra
previsioni registrate e punteggi degli invii di Davide fino a td 38 si rigenera con un comando:
[rapporto](../analisi/validazione_banco_eace4d03_2026-10-09/invii/RAPPORTO_INVII_r1.md).

## I punteggi ufficiali in una tabella

Fonte: i `comparison.json` e gli stati salvati; per le righe `ta`, quelli del branch di Alfredo al commit
indicato nella [mappa](#nomi-td-e-ta-mappa-dei-candidati), riletti il 10/10 (stato `published`, media dei
sei scalati uguale al punteggio, ramo della regola ricontrollato sul delta). **Questa tabella è la sede unica
dei punteggi ufficiali** (`docs/CLAUDE.md`): si aggiorna dopo ogni punteggio, e il §0 di
[PROGETTO](../../docs/PROGETTO.md) ne riporta solo il massimo osservato e il riferimento. I sei
membri di ogni invio sono nel suo `comparison.json`. Le righe sono in ordine d'invio.

| Invio | Punteggio | Rango | Esito della regola registrata |
|---|---|---|---|
| td 01 (trial-01) | +0,045929 | 446 | primo invio; conferma il percorso d'impacchettamento |
| td 02 | −0,092774 | 764 | ControlModel ×1 + cis: troppe chiamate; serve a risolvere le ancore |
| td 03 | +0,019692 | 576 | verifica storica delle ancore/stadio 84; la pretesa conversione esatta è smentita da CP-0050, non validata da questo invio |
| td 07 | −0,016004 | 671 | modello lineare condizionato: la previsione del banco non regge per una famiglia nuova |
| td 08 | +0,060370 | 547 | K562 + CD4, nuovo migliore |
| td 10 | +0,050191 | 570 | td 08 senza CD4: non attribuibile per 0,0002 |
| td 11 | +0,070777 | 560 | + Orion HCT116: aggiunge informazione, ma sono cambiati anche i pesi |
| td 14 | +0,064892 | 564 | ControlModel ×2,5: non attribuibile; la fedeltà scende |
| td 15 | +0,107533 | 436 | ampiezza ×2: sopra la banda; D-006 si riapre (D-042) |
| td 16 | +0,137627 | 336 | ampiezza ×4: la curva sale ancora |
| td 17 | +0,108774 | 448 | + HEK293T sul td 15: non attribuibile (R-016) |
| td 20 | +0,139676 | 346 | effetti ristretti a 1,576 + cis: non conclusivo contro il td 16 |
| **td 22** | **+0,141250** | 337 | + HEK293T: non conclusivo contro il td 20; **ricetta di riferimento** |
| td 24 | +0,142897 | 347 | td 22 con un altro seme: D = 0,0016, una sola coppia; il riferimento del td 22 diventa 0,14207 |
| td 25 | +0,140238 | 361 | td 22 con lo stimatore corretto: −0,0010, non conclusivo; la correzione resta |
| td 23 | +0,141868 | 366 | td 22 con la quota condivisa (conta l'esclusione): +0,0006, non conclusivo; PDS su, membri DE giù (CP-0042) |
| td 26 | +0,138721 | 384 | td 25 senza effetti sui geni sotto 5 CPM: −0,0015, non conclusivo; il PDS non sale, i geni poco espressi pesano poco (CP-0045) |
| **td 28** | **+0,144845** | 359 | effetti td 25 ×1,5 e dispersione per gene ×1: nuovo massimo osservato; +0,004607 contro td 25, sotto +0,005: non conclusivo ([CP-0052](../../docs/checkpoints/0052-t28-punteggio-ufficiale.md)) |
| td 29 | −0,029625 | 893 | la rete addestrata sulle singole cellule (R-LAB, secondo training, braccio `desc`) al posto degli effetti della ricetta, generatore del td 22: sotto la banda, ramo c della regola; PDS grezzo 0,50 contro 0,79 del td 22, la rete distingue poco i bersagli ([CP-0055](../../docs/checkpoints/0055-t29-rete-cellulare-punteggio.md)) |
| ta 30 | +0,027878 | 781 | Alfredo: rete di attenzione sulle sorgenti r1 (`ckpt_best`) con il generatore del td 22: ramo c della sua regola (sotto 0,06), nessun nuovo invio della rete senza un banco a sei membri al livello del transfer ([confronto][ta30-c]) |
| ta 31 | +0,078749 | 652 | Alfredo: media a pesi uguali delle linee pubbliche (`net0`) ×2 con il generatore del td 22: ramo c (0,06–0,10), al livello del transfer semplice ([confronto][ta31-c]) |
| td 30 | +0,135249 | 460 | ibrido selettivo D-056: effetti td 25 + w · R della rete del fold HepG2, generazione del td 25: −0,004989 contro il td 25, ramo b della regola (non conclusivo, a 0,00001 dalla soglia del ramo c); PDS scalato −0,042, fedeltà +0,014, Jaccard +0,002; nessuna promozione ([CP-0064](../../docs/checkpoints/0064-t30-ibrido-selettivo-punteggio-ufficiale.md)) |
| ta 34 | +0,076732 | 674 | Alfredo: rete contrastiva sugli effetti, sul transfer K562 di ta 31, generatore del td 22: ramo b, ta 34 − ta 31 = −0,0020, non conclusivo ([confronto][ta34-c]) |
| ta 35 | +0,089314 | 647 | Alfredo: ta 34 con i conteggi spostati fra le cellule verso le magnitudini della rete L1, a bulk invariato: ramo a, ta 35 − ta 34 = +0,0126 ([confronto][ta35-c]) |
| **td 36** | **+0,147249** | 432 | Transfer td 25 con l'emissione del td 28, banca estesa parziale; +0,002404 contro td 28, nuovo massimo osservato. Nessuna soglia numerica preregistrata; confronto descrittivo, nessuna promozione robusta ([CP-0067](../../docs/checkpoints/0067-t36-banca-estesa-punteggio-ufficiale.md)) |
| ta 36 | +0,141392 | 446 | Alfredo: base `all` del cubo più w · R del td 30, emissione del td 28: ramo b (entro ±0,01), ta 36 − td 28 = −0,0035, non conclusivo ([confronto][ta36-c]) |
| ta 38 | +0,131078 | 555 | Alfredo: ta 36 con ampiezza 1,0 invece di 1,5: ramo c, ta 38 − ta 36 = −0,0103; l'ampiezza 1,5 resta ([confronto][ta38-c]) |
| **td 38** | **+0,148922** | 477 | T3 = transfer CRISPRi di T1 più cinque voti KO a peso 0,25 su 34 bersagli, emissione del td 36: +0,001673 contro td 36, ramo «entro ±0,005» della regola registrata prima del fit: non conclusivo, nuovo massimo osservato; PDS scalato +0,008, fedeltà −0,004; nessuna attribuzione a una fonte ([CP-0074](../../docs/checkpoints/0074-t38-crispri-piu-ko-punteggio-ufficiale.md)) |
| ta 39 | +0,140816 | 528 | Alfredo: rete ponte (JEPA con SIGReg), insieme di 10 semi, norma di `all`, emissione del td 28: ramo b, ta 39 − td 28 = −0,0040, non conclusivo ([confronto][ta39-c]) |

Non inviati, di Davide: td 04, td 06, td 12, td 18, td 19, td 27 (generato e impacchettato il 29/09, tenuto
pronto dal proprietario), td 09 e td 13 (fermati dalle loro regole), td 21 (la sua previsione è citata ma non è nel repository: vedi la
[revisione critica](../analisi/revisione_criticita_2026-09-28/REVISIONE.md), §4), td 31 (bozza del 6/10 con
gli stessi byte poi inviati come td 36) e td 37, preparato nella notte fra l'8 e il 9 ottobre e superato
prima di ogni generazione; il td 38, fermato quella notte, è stato ripreso e inviato il 9 ottobre sera
([CP-0071](../../docs/checkpoints/0071-corsia-rapida-senza-invio-priorita-alle-reti.md),
[CP-0074](../../docs/checkpoints/0074-t38-crispri-piu-ko-punteggio-ufficiale.md)). Di Alfredo: ta 37,
generato e impacchettato il 6/10 e mai caricato. Inviato e non ancora letto: td 39.

## Nomi td e ta: mappa dei candidati

**Perimetro:** la corrispondenza fra nomi storici e nomi D-058 dei candidati registrati dal 1° ottobre,
quando il lavoro di Alfredo si separa da main; è la sede di questa informazione
([docs/CLAUDE.md](../../docs/CLAUDE.md)). **Fonti:** previsioni, pacchetti, ricevute e stati salvati dei due
branch, letti il 10/10 alle 16:00; le righe di Alfredo citano il branch `codex/teammate-rlead` al commit
`e52adac1`, senza copiarne i file. **Si aggiorna** quando un candidato è registrato, generato, inviato o
valutato, e quando il branch di un autore viene riletto o integrato.

- **Fino al td 29 una sola storia.** Il branch di Alfredo parte da main al commit `1f086cb2` (1/10, 16:01)
  e ne eredita i file: `trial-01` e `t02`–`t29` sono di Davide e si leggono td 01–td 29.
- **Nei testi di main scritti prima del 10/10, `tXX` senza autore è di Davide.** Verificato il 10/10:
  nessun file di main contiene entry ID o punteggi di Alfredo, e l'unico testo che cita suoi numeri li
  attribuisce a lui ([risposta del 4/10](../modelli/ibrido_pseudobulk_2026-10-04/RISPOSTA_ALFREDO.md)).
- **L'attribuzione ad Alfredo non viene dal numero né dall'autore dei commit.** Il branch è quello della
  [consegna al teammate](../../docs/CONSEGNA_TEAMMATE.md); le sue previsioni lo dichiarano («on
  codex/teammate-rlead t30 and t31 are Alfredo's submissions», nota di numerazione di [ta 34][ta34-p]); il
  kernel di ta 30 gira sull'account Kaggle `alfredo2003bit`; D-058 nomina come suoi ta 36, ta 38 e ta 39.
  Gli altri branch remoti di Alfredo, `alfredo` e `PPI-approach`, non contengono invii.
- **Stato verificato:** *proposto* = previsione registrata, mai generato; *generato* = cellule e
  pacchetto, mai caricato; *inviato* = caricato, nessun punteggio letto; *valutato* = stato `published`
  salvato, punteggio nella tabella sopra (qui non si ripete).
- **Confronti fra namespace:** ta 36 usa la correzione R del td 30, e le regole di ta 36 e ta 39 si
  leggono contro il td 28; in questi confronti i due nomi si scrivono per intero.

| Autore | Nome | Nome storico | Che cosa è | Entry | Stato verificato | Evidenza | Provenienza |
|---|---|---|---|---|---|---|---|
| Davide | td 29 | t29 | rete sulle singole cellule (R-LAB r2, braccio `desc`) con il generatore del td 22 | `K6Q36uGCaEwQ1wRLmBLp` | valutato | [previsione](prediction_t29_2026-10-01/prediction.json), [stato](trial_2026-10-01/status_K6Q36uGCaEwQ1wRLmBLp_final.json) | main: `b2dc838e`, prima della divergenza; punteggio in `9e040bd0`. Sul branch di Alfredo resta «in attesa del punteggio» |
| Alfredo | ta 30 | t30 | rete di attenzione sulle sorgenti r1 (`ckpt_best`) con il generatore del td 22 | `0GRBdx7CEwnmE6dH9AYa` | valutato | [previsione][ta30-p], [stato][ta30-s], [CP-0056 del branch][ta30-cp] | `codex/teammate-rlead`: `1f0041c9` → `0bd3682c` |
| Alfredo | ta 31 | t31 | media a pesi uguali delle linee pubbliche (`net0`) ×2, generatore del td 22 | `iJRHcbswOtopr8kDLJuP` | valutato | [previsione][ta31-p], [stato][ta31-s], [CP-0057][ta31-cp] e [CP-0058][ta31-cp2] del branch | `codex/teammate-rlead`: `b2c7e94f` → `e212957d` |
| Davide | td 30 | t30 | ibrido selettivo D-056: effetti del td 25 + w · R della rete del fold HepG2 | `lDMSYUZU5cFYHcRqI0lq` | valutato | [previsione](prediction_t30_2026-10-04/prediction.json), [stato](trial_2026-10-04/status_lDMSYUZU5cFYHcRqI0lq.json), [CP-0064](../../docs/checkpoints/0064-t30-ibrido-selettivo-punteggio-ufficiale.md) | main: `18407dcd` → `0898ba27` |
| Alfredo | ta 32, ta 33 | — | nessun candidato: numeri detti «riservati» nella nota di numerazione di ta 36, nati dalla proposta, mai applicata, di rinominare ta 30 e ta 31 | — | nessun candidato | [nota][ta36-p] (`number_note`), [proposta del 4/10](../modelli/ibrido_pseudobulk_2026-10-04/RISPOSTA_ALFREDO.md), §5 | `codex/teammate-rlead`: `093d48f6` |
| Alfredo | ta 34 | t34 | rete contrastiva sugli effetti, sul transfer K562 di ta 31, generatore del td 22 | `SjJp6tuHoMRL7VlQEvFY` | valutato | [previsione][ta34-p], [stato][ta34-s], [CP-0059 del branch][ta34-cp] | `codex/teammate-rlead`: `b37dedc7` → `6c494300` |
| Alfredo | ta 35 | t35 | ta 34 con i conteggi spostati fra le cellule verso le magnitudini della rete L1, a bulk invariato | `2amQBkbhdjqEj52vDA5C`; annullata `lqLrMpd2BRmZ7m3w52x2` | valutato, dopo un caricamento rifiutato dalla quota e uno annullato | [previsione][ta35-p], [stato][ta35-s], [annullamento][ta35-x] | `codex/teammate-rlead`: `31e1d806` → `5aeff942` |
| Davide | td 31 | t31 | banca estesa parziale con l'emissione del td 28: etichetta della bozza, cambiata in td 36 prima dell'upload | — | stesso candidato di td 36: archivio identico, sha256 `ea41ddf1…` in [t31](trial_2026-10-06/t31_packaging.json) e [t36](trial_2026-10-06/t36_packaging.json) | [bozza](prediction_t31_2026-10-06/prediction.json) | main: `b90c6797` |
| Davide | td 36 | t36 | transfer td 25 con l'emissione del td 28, banca estesa parziale | `JLcMRGExhXKk77XVds7x` | valutato | [record](prediction_t36_2026-10-06/README.md), [stato](trial_2026-10-06/status_JLcMRGExhXKk77XVds7x_0138.json), [CP-0067](../../docs/checkpoints/0067-t36-banca-estesa-punteggio-ufficiale.md) | main: `b90c6797` → `bb166fbe` |
| Alfredo | ta 36 | t36 | base `all` del cubo r2 più w · R del td 30, emissione del td 28 | `LgakrSXj3X2nAtN5P4Yk` | valutato | [previsione][ta36-p] (**stesso percorso del record di td 36, file diversi**), [stato][ta36-s] | `codex/teammate-rlead`: `093d48f6` → `24698cab` |
| Alfredo | ta 37 | t37 | base `all` senza R, emissione del td 28: braccio di confronto di ta 36 | — | generato, mai caricato (`uploaded: false`, sha256 `d83b7b6b…`) | [pacchetto][ta37-k]; registrato come `comparison_arm_t37` nella [previsione di ta 36][ta36-p] | `codex/teammate-rlead`: `093d48f6` → `e6c3a830` |
| Alfredo | ta 38 | t38 | ta 36 con `--effects-scale` 1,0 invece di 1,5 | `5GhXxaCDRuPnHv4UwU8S` | valutato | [previsione][ta38-p], [stato][ta38-s] | `codex/teammate-rlead`: `0e7cc8e4` → `be5ad0c0` |
| Davide | td 37 | t37 | T1 (release r1 senza il voto RFK di Tian 2019) con l'emissione del td 36 | — | proposto: superato alle 23:55 dell'8/10, prima di ogni generazione | [previsione](prediction_t37_2026-10-08/prediction.json), [blocco](trial_2026-10-08/NO_SUBMIT_T1_r1.json), [CP-0071](../../docs/checkpoints/0071-corsia-rapida-senza-invio-priorita-alle-reti.md) | main: `fb275797` |
| Davide | td 38 | t38 | T3: T1 più cinque voti KO a peso 0,25 su 34 bersagli, emissione del td 36 | `LJmnhqqh1WTrx1JcoRlr` | valutato | [previsione](prediction_t38_2026-10-09/prediction.json), [confronto](prediction_t38_2026-10-09/comparison.json), [stato](../analisi/validazione_banco_eace4d03_2026-10-09/invii/stati/status_LJmnhqqh1WTrx1JcoRlr_20261009T190948Z.json), [CP-0074](../../docs/checkpoints/0074-t38-crispri-piu-ko-punteggio-ufficiale.md) | main: `7a431f68` → `2e6d801a` |
| Alfredo | ta 39 | t39 | rete ponte (JEPA con SIGReg), insieme di 10 semi, norma di `all`, emissione del td 28 | `oeRXw89O1hefFsdCwifD` | valutato | [previsione][ta39-p], [stato][ta39-s] | `codex/teammate-rlead`: `eaba48e7` → `e52adac1` |
| Davide | td 39 | t39 | T3 del td 38 conservato più il ridge ESM2 congelato sulle coppie mancanti; la prima registrazione, td 36 più ESM2, è stata [superata](prediction_t39_2026-10-10/README.md) prima della generazione | `C49E3QzIDZk0LGmXPCPP` | inviato: upload verificato il 10/10 alle 01:29, `scoring` alle 01:33; nessun punteggio salvato | [previsione](prediction_t39_t3_2026-10-10/prediction.json), [stato](trial_2026-10-10/status_C49E3QzIDZk0LGmXPCPP_delivery_check_r2.json), [ricevuta](../modelli/dati_transfer_2026-10-08_01a11c34/CONSEGNA_T39_RICEVUTA_r1.md) | main: `e80424b3` → `786a56b8` |

Numeri senza candidato: td 32–td 35 non compaiono su main; ta 32 e ta 33 sono nella riga sopra. T1, T2 e T3
sono etichette degli effetti nella validazione di Davide dell'8–9/10, non numeri d'invio: T3 è stato inviato
come td 38, T1 era il candidato di td 37, T2 non è stato inviato.

### Collisioni e contraddizioni aperte

1. **Stesso percorso, file diversi.** `reports/invii/prediction_t36_2026-10-06/` è il record di td 36 su
   main e la previsione di ta 36 sul [branch][ta36-dir]: `prediction.json` e `comparison.json` hanno lo
   stesso nome e contenuti diversi. Un merge integrale del branch li metterebbe in conflitto: ta 36 entra
   su main solo con un percorso nuovo (PROCEDURE §2), da concordare con Alfredo; fino ad allora si cita
   per branch e commit.
2. **Stessi numeri di checkpoint.** CP-0056, CP-0057 e CP-0058 hanno contenuti diversi sui due branch:
   su main il banco C/J, P4 e la copertura D-053; sul branch ta 30, ta 31 e la correzione di ta 31.
   CP-0059 esiste solo sul branch (ta 34) e su main è un numero saltato. Un checkpoint del branch si cita
   con branch e commit, mai col solo numero. I numeri definitivi si assegnano all'integrazione senza
   riscrivere quelli pubblicati (proposta della [risposta del 4/10](../modelli/ibrido_pseudobulk_2026-10-04/RISPOSTA_ALFREDO.md), §5): decisione aperta.
3. **Numeri provvisori.** Le previsioni di ta 34–ta 39 dichiarano il numero provvisorio, da confermare
   con Davide (campo `number_note`). Con D-058 il numero storico resta e prende il prefisso; resta aperto se ta 32 e ta 33,
   riservati senza candidato, contino come numeri già assegnati (PROCEDURE §2): lo decide il proprietario.
4. **Indice del branch contro la sua ricevuta.** Nell'[indice del branch][ta-index] la riga della cartella
   `prediction_t35_2026-10-04/` dice «Non inviato», mentre la sua tabella dei punteggi e lo
   [stato salvato][ta35-s] dicono pubblicato: fa fede la ricevuta, la riga va corretta sul branch.
5. **td 39 senza lettura.** Lo stato salvato più recente è `scoring`, alle 01:33 del 10/10: manca la
   lettura dello stato con la regola registrata (±0,005 contro td 38), secondo PROCEDURE §2, punto 7.
6. **Cartelle del giorno.** `trial_<data>/` è per giorno, non per autore: Alfredo ha usato
   `trial_rlead_<data>/` per non collidere con `trial_2026-10-04/` di main, ma la sua `trial_2026-10-03/`
   porta il nome semplice. D-058 nomina i candidati, non le cartelle del giorno: se due autori inviano lo
   stesso giorno, il nome della cartella va deciso.
7. **Strade non registrate.** Gli esiti del branch (ta 30–ta 39 e i loro banchi) non hanno voci in
   [STRADE](../../docs/STRADE.md) su main.

[ta-index]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/README.md
[ta30-p]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/prediction_t30_2026-10-03/prediction.json
[ta30-c]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/prediction_t30_2026-10-03/comparison.json
[ta30-s]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/trial_2026-10-03/status_0GRBdx7CEwnmE6dH9AYa.json
[ta30-cp]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/docs/checkpoints/0056-t30-punteggio-ufficiale.md
[ta31-p]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/prediction_t31_2026-10-03/prediction.json
[ta31-c]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/prediction_t31_2026-10-03/comparison.json
[ta31-s]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/trial_2026-10-03/status_iJRHcbswOtopr8kDLJuP.json
[ta31-cp]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/docs/checkpoints/0057-t31-punteggio-ufficiale.md
[ta31-cp2]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/docs/checkpoints/0058-t31-solo-k562.md
[ta34-p]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/prediction_t34_2026-10-04/prediction.json
[ta34-c]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/prediction_t34_2026-10-04/comparison.json
[ta34-s]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/trial_rlead_2026-10-04/status_SjJp6tuHoMRL7VlQEvFY.json
[ta34-cp]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/docs/checkpoints/0059-t34-contrastiva-punteggio.md
[ta35-p]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/prediction_t35_2026-10-04/prediction.json
[ta35-c]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/prediction_t35_2026-10-04/comparison.json
[ta35-s]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/trial_rlead_2026-10-05/status_2amQBkbhdjqEj52vDA5C.json
[ta35-x]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/trial_rlead_2026-10-05/cancel_t35_raw.json
[ta36-dir]: https://github.com/ferry-ai/virtual-cell-challenge-2026/tree/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/prediction_t36_2026-10-06
[ta36-p]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/prediction_t36_2026-10-06/prediction.json
[ta36-c]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/prediction_t36_2026-10-06/comparison.json
[ta36-s]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/trial_rlead_2026-10-06/status_LgakrSXj3X2nAtN5P4Yk.json
[ta37-k]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/trial_rlead_2026-10-06/t37_packaging.json
[ta38-p]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/prediction_t38_2026-10-07/prediction.json
[ta38-c]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/prediction_t38_2026-10-07/comparison.json
[ta38-s]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/trial_rlead_2026-10-07/status_5GhXxaCDRuPnHv4UwU8S.json
[ta39-p]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/prediction_t39_2026-10-09/prediction.json
[ta39-c]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/prediction_t39_2026-10-09/comparison.json
[ta39-s]: https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/e52adac19010c18cb2cec0793ab24cf143dc5c71/reports/invii/trial_rlead_2026-10-09/status_oeRXw89O1hefFsdCwifD.json

## Le cartelle, dalla più recente

Le cartelle di Alfredo non sono su main: la [mappa td/ta](#nomi-td-e-ta-mappa-dei-candidati) le cita per branch e commit.

| Data | Cartella | Nocciolo | Vale? | Peso oggi |
|---|---|---|---|---|
| 2026-10-10 | [prediction_t39_t3](prediction_t39_t3_2026-10-10/) | Nuova previsione prima della generazione: T38/T3 preservato e ridge ESM2 sulle 380.820 coppie mancanti; banda soggettiva 0,125–0,170, regola ±0,005 contro t38 | attuale | Sostituisce il candidato T0 prima di qualsiasi generazione; nessun nuovo fit, beneficio ufficiale ancora da misurare |
| 2026-10-10 | [prediction_t39](prediction_t39_2026-10-10/) | Previsione iniziale t36 più ESM2, conservata senza modificarla | superato | Mai generato né inviato; sostituito da [T38/T3 più ESM2](prediction_t39_t3_2026-10-10/README.md) dopo il richiamo del proprietario alla base aggiornata |
| 2026-10-10 | [trial](trial_2026-10-10/) | Testi del t39 registrati prima della generazione: per l'esecuzione valgono i nuovi testi T3; manifest e ricevute dall'unico uploader DATI-TRANSFER: upload di td 39 verificato alle 01:29 del 10/10 (entry `C49E3QzIDZk0LGmXPCPP`), stato `scoring` alle 01:33 | attuale | Inviato, nessun punteggio salvato; nessuna promozione scientifica anticipata |
| 2026-10-09 | [prediction_t38](prediction_t38_2026-10-09/) | Previsione del t38 = T3 (nucleo CRISPRi di T1 più cinque voti KO a peso 0,25 su 34 bersagli), registrata da DATI-TRANSFER alle 00:19 prima del fit e della generazione; delta atteso zero, regola ±0,005 contro t36. **Ufficiale 0,148922, +0,001673: ramo «entro ±0,005», non conclusivo**; [confronto](prediction_t38_2026-10-09/comparison.json) scritto da VALIDAZIONE dallo stato letto alle 21:09 del 9/10 | attuale | Inviato il 9/10 sera dopo la ripresa disposta dal proprietario; nuovo massimo osservato su un invio ([CP-0074](../../docs/checkpoints/0074-t38-crispri-piu-ko-punteggio-ufficiale.md)) |
| 2026-10-09 | [trial](trial_2026-10-09/) | Testi del t38 scritti prima del fit e della generazione, precisazione sulla segnalazione DT-5, preflight del client; dal 9/10 sera manifesti degli stadi 45 e 48, ricevute dell'upload (entry `LJmnhqqh1WTrx1JcoRlr`, concluso alle 20:04) e stati salvati da DATI-TRANSFER fino a `scoring`; lo stato `published` è in `reports/analisi/validazione_banco_eace4d03_2026-10-09/invii/stati/` | attuale | Invio fatto e valutato |
| 2026-10-08 | [prediction_t37](prediction_t37_2026-10-08/) | Previsione del t37 = T1 con l'emissione del t36, registrata dal Lead alle 23:47 prima di ogni generazione; regola ±0,005 contro t36 | attuale | **Mai generato né inviato:** superato alle 23:55 dalla richiesta del proprietario di un refit su tutte le fonti |
| 2026-10-08 | [trial](trial_2026-10-08/) | Testi e launcher del t37, più il blocco `NO_SUBMIT_T1_r1.json` | attuale | Nessun invio: la corsia rapida è passata al t38 |
| 2026-10-06 | [prediction_t36](prediction_t36_2026-10-06/) | Record runtime originale e correzione nome richiesta dall'utente; nessuna banda numerica inventata. Ufficiale 0,147249, [confronto](prediction_t36_2026-10-06/comparison.json). Sul branch di Alfredo lo stesso percorso contiene la previsione di ta 36, con file diversi ([collisioni](#collisioni-e-contraddizioni-aperte)) | attuale | Invio esplorativo della release estesa parziale, td 36 |
| 2026-10-06 | [trial](trial_2026-10-06/) | Manifest packaging, testi e trasferimento del candidato; ricevuta pubblicabile e stati ufficiali, `launching` e poi [`published`](trial_2026-10-06/status_JLcMRGExhXKk77XVds7x_0138.json) | attuale | Invio fatto e valutato ([CP-0067](../../docs/checkpoints/0067-t36-banca-estesa-punteggio-ufficiale.md)) |
| 2026-10-06 | [prediction_t31](prediction_t31_2026-10-06/) | Bozza locale con record runtime, mai inviata con questo nome (td 31) | storico | Sostituita solo l'etichetta da t36; stessi byte |
| 04/10 | [prediction_t30_2026-10-04/](prediction_t30_2026-10-04/) | Ibrido selettivo D-056: effetti t25 + w · R della rete del fold HepG2 con il selettore congelato; cambia solo la fonte degli effetti rispetto al t25. Registrata alle 08:14 UTC prima della lettura degli effetti ibridi e della generazione; banda 0,125…0,160, regola a ±0,005 contro il t25. Ufficiale 0,135248602, delta −0,004989459: ramo b, non conclusivo; [confronto](prediction_t30_2026-10-04/comparison.json), catena e diagnosi in [diagnosi_t30](../modelli/diagnosi_t30_2026-10-04/README.md) | sì; non conclusivo, nessuna promozione | ★★★ |
| 04/10 | [trial_2026-10-04/](trial_2026-10-04/) | Testi del t30 scritti prima della generazione; effetti t25 rigenerati (stesso sha256 del t25), esportazione `export_abc_r2`, manifesti degli stadi 45 e 48, upload 09:13–09:30 UTC (entry lDMSYUZU5cFYHcRqI0lq, MD5 verificato), status pubblicato e lettore scritto prima; registro in [INVIO_T30.md](trial_2026-10-04/INVIO_T30.md) | sì | ★★★ |
| 01/10 | [prediction_t29_2026-10-01/](prediction_t29_2026-10-01/) | La rete addestrata sulle singole cellule (R-LAB, secondo training, braccio `desc`) con il generatore del t22: cambia solo la fonte degli effetti. Registrata alle 12:06 UTC prima dell'esportazione e della generazione; banda −0,02…+0,10, regola a 0,06 e 0,137. Ufficiale −0,029625, ramo c; [confronto](prediction_t29_2026-10-01/comparison.json) | sì | ★★ |
| 01/10 | [trial_2026-10-01/](trial_2026-10-01/) | Testi del t29 scritti prima della generazione; esportazione, manifesti degli stadi 45 e 48, upload sul Wi-Fi di casa (13:28-15:16 UTC, entry K6Q36uGCaEwQ1wRLmBLp), status pubblicato e lettore del punteggio scritto prima | sì | ★★ |
| 29/09 | [prediction_t28_2026-09-29/](prediction_t28_2026-09-29/) | Effetti t25 ×1,5 e dispersione per gene ×1. Ufficiale 0,144845205, delta t25 +0,004607144: nuovo massimo, sotto la soglia congelata +0,005. Sei membri e media verificati; [confronto](prediction_t28_2026-09-29/comparison.json). Il delta locale +0,028918 non era calibrato, 95/96 target già valutati | pubblicato; non conclusivo | ★★★ |
| 29/09 | [prediction_t27_2026-09-29/](prediction_t27_2026-09-29/) | t25 con l'esclusione del t23 (i 8.247 geni che meno di due universi stimano) senza pesatura né riscalatura; registrato alle 15:45 UTC prima di generare; banda +0,128…+0,150, regola a ±0,005 contro il t25; `esclusione.csv` è la lista 0/1. Generato e impacchettato il 29/09 (sha256 `b4eb8b75…`, manifest in `trial_2026-09-29/`); **non inviato**: il proprietario lo tiene pronto | registrazione; pronto | ★★ |
| 29/09 | [prediction_t26_2026-09-29/](prediction_t26_2026-09-29/) | t25 con effetto 0 sui geni sotto 5 CPM nei controlli del contesto (circa il 70 % dell'energia prevista): registrato alle 12:24 UTC prima di generare; banda +0,134…+0,156, regola a ±0,005 contro il t25. **Esito:** +0,138721, t26 − t25 = −0,0015, non conclusivo; `pds_cosine` −0,0020 grezzo: l'ipotesi registrata (il PDS del t23 dai geni poco espressi) non regge (CP-0045) | sì | ★★ |
| 29/09 | [trial_2026-09-29/](trial_2026-09-29/) | t26 pubblicato dopo ripresa; t27 pronto. t28 caricato alle 22:46 UTC, MD5 verificato e status originale finale published conservato: 0,144845205. Ricevute e cancellazione autorizzata del solo intermedio t26 in INVIO_T28.md; esito in CP-0052, seguito concluso | sì; t28 pubblicato | ★★★ |
| 28/09 | [prova_generale_2026-09-28/](prova_generale_2026-09-28/) | La prova generale del 22 ottobre (azione 3 di R-REV): A/B/C trattati come nuovi, 300 bersagli finti, fino al `.vcc` verificato, senza invio. Protocollo, sei previsioni e 13 difetti attesi dalla lettura del codice, fissati alle 20:00 prima di girare. **Esito (29/09, forma ridotta):** `.vcc` di D/E/F verificato; previsioni 1, 3–6 vere; D1 corretto (CP-0044). D4 (cache sbagliata in silenzio), D9 (riferimento di γ) e gli altri difetti di codice sono corretti il 29/09 pomeriggio con i loro test (RISULTATI, «Correzioni dei difetti»); resta la forma piena | sì; copie di A/B/C, forma ridotta | ★★★ |
| 28/09 | [lezioni_invii_2026-09-28/](lezioni_invii_2026-09-28/) | I nostri invii valutati e la classifica pubblica in soli aggregati: dal t16 nessun cambio supera il rumore del seme; contro la mediana dei primi 100 perdiamo soprattutto sull'MSE (tosato a 0 in tutti i nostri invii) | in parte: l'[audit del 29/09](../analisi/lead_scientist_2026-09-29/AUDIT_SCIENTIFICO.md) ne corregge due letture, il rumore stimato da una sola coppia di semi (§2.2) e il peso della risposta comune sull'MSE (§2.4) | ★★★ |
| 27/09 | [prediction_t25_2026-09-27/](prediction_t25_2026-09-27/) | t22 sulla cache r9 (stimatore senza l'artefatto del pseudoconteggio): +0,140238, −0,0010, non conclusivo | sì | ★★ |
| 27/09 | [prediction_t24_2026-09-27/](prediction_t24_2026-09-27/) | t22 con un altro seme del generatore: D = 0,0016 su una coppia; la soglia ±0,005 resta | sì, come stima grezza di una coppia | ★★★ (il solo dato sul rumore ufficiale) |
| 27/09 | [prediction_t23_2026-09-27/](prediction_t23_2026-09-27/) | t22 con la quota condivisa per gene; inviato il 28/09 con il via del proprietario: +0,141868, t23 − t22 = +0,0006, non conclusivo; `pds_cosine` +0,0109 grezzo, `nmae`, `reach` e Jaccard giù (CP-0042) | sì come registrazione; l'ablazione dice che conta l'esclusione dei geni, non la quota | ★★ |
| 27/09 | [trial_2026-09-27/](trial_2026-09-27/) | Testi, manifesti e pacchetti di t23, t24 e t25; invii di t24, t25 e (il 28/09 sera) t23 | sì | ★★ |
| 26/09 | [prediction_t22_2026-09-26/](prediction_t22_2026-09-26/) | t20 + HEK293T a peso uguale: +0,141250, il migliore; +0,0016 sul t20, non conclusivo | sì | ★★★ (ricetta di riferimento) |
| 26/09 | [prediction_t20_2026-09-26/](prediction_t20_2026-09-26/) | t19 + modulo cis: +0,139676; contro il t16 non si separano restrizione e cis | sì | ★★ |
| 26/09 | [trial_2026-09-26/](trial_2026-09-26/) | Testi, manifesti e invii di t20 e t22 | sì | ★★ |
| 25/09 | [prediction_t19_2026-09-25/](prediction_t19_2026-09-25/) | t16 con gli effetti ristretti a 1,576: registrato, non inviato | storico | ★ |
| 25/09 | [prediction_t18_2026-09-25/](prediction_t18_2026-09-25/) | t16 ad ampiezza 1,576: registrato, non inviato | storico | ★ |
| 25/09 | [trial_2026-09-25/](trial_2026-09-25/) | Testi e pacchetti di t18 e t19, mai inviati | storico | ★ |
| 24/09 | [prediction_t17_2026-09-24/](prediction_t17_2026-09-24/) | t15 + HEK293T a q99 uguale: +0,108774, non attribuibile | in parte: la lettura causale ha i limiti di R-016 | ★ |
| 24/09 | [prediction_t16_2026-09-24/](prediction_t16_2026-09-24/) | t15 ad ampiezza 0,788: +0,137627; grezzi derivati dalle ancore | sì | ★★ |
| 24/09 | [trial_2026-09-24/](trial_2026-09-24/) | t15 inviato; t16 e t17 generati e inviati il 25 dalla catena d'invio | sì | ★ |
| 23/09 | [prediction_t15_2026-09-23/](prediction_t15_2026-09-23/) | t11 ad ampiezza 0,394: +0,107533, sopra la banda; riapre D-006 | sì | ★★ |
| 23/09 | [prediction_t14_2026-09-23/](prediction_t14_2026-09-23/) | ControlModel con gli effetti del t08 × 2,5: non attribuibile, fedeltà in calo | sì | ★ |
| 23/09 | [prediction_t12_2026-09-23/](prediction_t12_2026-09-23/) | t11 + HEK293T: registrato, non generato | storico | ★ |
| 23/09 | [prediction_t11_2026-09-23/](prediction_t11_2026-09-23/) | t08 + Orion HCT116 a pesi uguali: +0,070777 | sì | ★ |
| 23/09 | [prediction_t10_2026-09-23/](prediction_t10_2026-09-23/) | t08 senza CD4: +0,0502; CD4 vale circa +0,010 | sì | ★ |
| 23/09 | [trial_2026-09-23/](trial_2026-09-23/) | t10 inviato; t11 dopo tre tentativi falliti e la ripresa dell'upload; t14 | sì | ★ (lezioni pratiche sull'upload, PROCEDURE §2) |
| 22/09 | [prediction_t08_2026-09-22/](prediction_t08_2026-09-22/) | K562 + CD4, γ = 1: +0,0604, sul bordo superiore della banda | sì | ★ |
| 22/09 | [trial_2026-09-22/](trial_2026-09-22/) | t08 e **le autorizzazioni del proprietario** (`autorizzazioni.md`: invii, Orion, disco) | sì | ★★ (le autorizzazioni vanno riconfermate in chat) |
| 19/09 | [prediction_t07_2026-09-19/](prediction_t07_2026-09-19/) | Previsione dello stadio 84 per il t07: +0,0101 contro un ufficiale −0,0160 | sì | ★ |
| 19/09 | [trial_2026-09-19/](trial_2026-09-19/) | t06 generato e non inviato; t07 inviato | storico | ★ |
| 17/09 | [prediction_t03_2026-09-17/](prediction_t03_2026-09-17/) | Prima previsione registrata (stadio 84) contro il t03 | sì | ★ |
| 17/09 | [trial02_decision_2026-09-17/](trial02_decision_2026-09-17/) | Applicazione meccanica della regola del t02; deviazione dichiarata per il t03 | storico | ★ |
| 17/09 | [trial_2026-09-17/](trial_2026-09-17/) | t02 e t03: gli stati contengono i grezzi che hanno risolto le ancore; t04 mai inviato | sì | ★★ |
| 13/09 | [trial_2026-09-13/](trial_2026-09-13/) | Primo invio (trial-01) e impacchettamento a memoria limitata, con l'istantanea del codice | sì | ★ |
| 12/09 | [trial_2026-09-12/](trial_2026-09-12/) | Primo trial locale: calibrazione annidata dell'ampiezza (0,1974), risorse, convalide | in parte (un file superato, R-011) | ★ |

## Che cosa non si ricava da qui

- **Un intervallo per il singolo invio.** Ogni punteggio è una sola estrazione del generatore;
  il rumore fra due semi è misurato una volta sola (t24 − t22).
- **L'effetto di una scelta su D/E/F.** Ampiezza e sorgenti sono state scelte su A/B/C con
  circa 15 invii: sul set finale, con contesti e bersagli nuovi, vanno ricontrollate.
