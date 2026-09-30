# Mappa del progetto — VCC 2026

**Prossimi passi:** [modello competitivo — piano operativo](piani/modello-competitivo.md),
dai dati realmente usati al training e alla verifica indipendente sui sei membri. La direzione
generale è nel §0; dove sta che cosa, per ambito, in [AMBITI.md](AMBITI.md).

**Questo è il punto di ingresso per lo stato.** Il §0 dice dove siamo oggi;
[PIANI.md](PIANI.md) indica i lavori aperti e promettenti, le dipendenze e i piani
chiusi. Come si esegue il lavoro sta in [LAVORO.md](LAVORO.md); l'evidenza, per
argomento e con lo stato di ogni cartella, in [reports/README.md](../reports/README.md).

Riorganizzata il 2026-09-28 (D-046):
- §0 è aggiornato al 28 settembre;
- §3 e §4 sono nuovi e corti. Il testo precedente, con la tabella delle misure del 12–17
  settembre e le 21 incertezze numerate, è in
  [storico/PROGETTO_sezioni_3_4_2026-09-28.md](storico/PROGETTO_sezioni_3_4_2026-09-28.md);
- §5 è nuovo: le criticità note. La versione del 23 settembre è nel tag
  `archivio/pre-pulizia-2026-09-23`.

Il §0 si aggiorna a ogni invio valutato; l'ultima volta il 30 settembre, con il t28
([confronto](../reports/invii/prediction_t28_2026-09-29/comparison.json)).

## 0. Oggi — 30 settembre 2026

**Il massimo osservato è t28: +0,144845, rango 359 al controllo; l'esito è non conclusivo.**
Il delta contro t25 è +0,004607, sotto la soglia congelata +0,005. Fedeltà e reach
salgono, NMAE e Jaccard scendono; la MSE grezza peggiora mentre lo scalato resta zero.
Non dimostra generalizzazione ([CP-0052](checkpoints/0052-t28-punteggio-ufficiale.md)).

**La ricetta di riferimento resta quella del t22: +0,141250, rango 337 all'invio.** È il t20 con
Orion HEK293T come quarta sorgente genome-scale a peso uguale
([confronto](../reports/invii/prediction_t22_2026-09-26/comparison.json)). La sua replica con
un altro seme del generatore, il t24, vale +0,142897: per la regola registrata la differenza
D = 0,0016 lascia la soglia ±0,005, e il riferimento della ricetta diventa la media dei due,
**0,14207** ([confronto](../reports/invii/prediction_t24_2026-09-27/comparison.json)). Il t25,
la stessa ricetta con lo stimatore pseudobulk corretto, vale +0,140238: −0,0010, non
conclusivo; la correzione resta nei dati da qui in avanti.

**Dal t16 i cambi della media sono piccoli; il plateau non dimostra che ampiezza e generatore siano ottimizzati.**
Una sola coppia di semi non identifica il rumore, e diversi membri si compensano
([audit del 29/09](../reports/analisi/lead_scientist_2026-09-29/AUDIT_SCIENTIFICO.md)). Il set finale
arriva il **22 ottobre**, con tre contesti nuovi (D, E, F) e 300 perturbazioni nuove; le
sottomissioni chiudono il **5 novembre** (§1).

### Direzione generale

**Proposta di sintesi del 30/09 (Claude), dalle prove citate.** Le priorità le fissa il
proprietario in [PIANI.md](PIANI.md); la mappa per ambito è [AMBITI.md](AMBITI.md).

1. **Il traguardo è il set finale D/E/F**, l'unico che conta per la classifica: tutta la catena
   deve andare dall'input al `.vcc` su contesti e bersagli nuovi. Resta da fare la prova generale
   in forma piena (azione 3 di [R-REV](piani/revisione-critica.md)), che chiede circa 17 GB liberi;
   il 30/09 su C: ce n'erano 3,8.
2. **La leva misurata è l'emissione.** Il t28 conferma in gara il verso del banco, cioè fedeltà e
   reach che salgono, con un guadagno netto piccolo pagato in NMAE, Jaccard e MSE grezza
   ([CP-0052](checkpoints/0052-t28-punteggio-ufficiale.md)). Il passo successivo è separare
   ampiezza e dispersione e cercare varianti che non perdano NMAE, scegliendo con lo scorer vero su
   una riserva mai valutata: il banco K562 dell'azione 4 e il passo 2 di
   [R-COMP](piani/modello-competitivo.md), non il solo banco HepG2.
3. **Il divario con i primi 100 sta soprattutto nella `mse`**, tosata a zero in tutti i nostri
   invii (§3). La sola risposta comune non basta a colmarlo
   ([audit del 29/09](../reports/analisi/lead_scientist_2026-09-29/AUDIT_SCIENTIFICO.md), §2.4),
   e nessun modello appreso ha ancora passato la sua regola: una rete nuova si prova sui sei
   membri, con una riserva nuova.
4. **I dati già pronti ma non usati**, come le diciannove linee HIPSCI e VIPerturb-seq (Flex, fuori
   dalla ricetta), entrano con maschere esplicite e con la copertura tracciata
   ([copertura del training](../reports/analisi/lead_scientist_2026-09-29/TRAINING_COPERTURA.md)).
5. **Metodo:** previsione registrata prima di ogni invio, lettura dai sei membri pubblicati, e
   prima di concludere un controllo degli [errori già commessi](ERRORI.md#errori-di-metodo-già-commessi).

### I punteggi ufficiali

| Invio | Che cosa cambia | Generatore | Media | Rango | Evidenza |
|---|---|---|---|---|---|
| trial-01 | trasferimento K562 (`ShrunkTransfer`) × 0,197 | trial-01 | +0,045929 | 446 | [CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md) |
| t02 | K562 dalla singola cellula × 1 + termine cis | `ControlModel` | −0,092774 | 764 | [CP-0021](checkpoints/0021-ancore-ufficiali-e-troppe-chiamate.md) |
| t03 | come il t02, × 2 | `ControlModel` | +0,019692 | 576 | [CP-0022](checkpoints/0022-previsione-verificata-t03.md) |
| t07 | modello lineare condizionato su bersaglio e contesto | — | −0,016004 | 671 | [CP-0027](checkpoints/0027-t07-punteggio-ufficiale.md) |
| t08 | effetti K562 + CD4, γ = 1, grezzi × 0,197 | trial-01 | +0,060370 | 547 | [CP-0029](checkpoints/0029-t08-punteggio-ufficiale.md) |
| t10 | il t08 senza CD4 | trial-01 | +0,050191 | 570 | [CP-0030](checkpoints/0030-t10-attribuzione-cd4.md) |
| t11 | il t08 + Orion HCT116, le tre sorgenti a pesi uguali | trial-01 | +0,070777 | 560 | [CP-0031](checkpoints/0031-t11-punteggio-orion.md) |
| t14 | effetti del t08 × 2,5 | `ControlModel` | +0,064892 | 564 | [CP-0032](checkpoints/0032-t14-controlmodel-fedelta.md) |
| t15 | il t11 con ampiezza 0,394 invece di 0,197 | trial-01 | +0,107533 | 436 | [CP-0033](checkpoints/0033-t15-ampiezza-doppia.md) |
| t16 | il t15 con ampiezza 0,788 | trial-01 | +0,137627 | 336 | [CP-0037](checkpoints/0037-t16-ampiezza-quadrupla.md) |
| t17 | il t15 + Orion HEK293T, ampiezza 0,4285 (stesso q99 del t15) | trial-01 | +0,108774 | 448 | [CP-0038](checkpoints/0038-t17-hek293t-non-attribuibile.md) |
| t20 | il t16 con effetti ristretti a 1,576 + modulo cis CRISPRi | trial-01 | +0,139676 | 346 | [confronto](../reports/invii/prediction_t20_2026-09-26/comparison.json) |
| **t22** | il t20 + Orion HEK293T a peso uguale (le quattro sorgenti genome-scale) | trial-01 | **+0,141250** | 337 | [confronto](../reports/invii/prediction_t22_2026-09-26/comparison.json) |
| t24 | il t22 con un altro seme del generatore (replica: misura il rumore) | trial-01 | +0,142897 | 347 | [confronto](../reports/invii/prediction_t24_2026-09-27/comparison.json) |
| t25 | il t22 con lo stimatore pseudobulk corretto (`min_expected` 1) | trial-01 | +0,140238 | 361 | [confronto](../reports/invii/prediction_t25_2026-09-27/comparison.json) |
| t23 | il t22 con la parte trasferita pesata per la quota condivisa (conta l'esclusione dei geni); inviato il 28/09 | trial-01 | +0,141868 | 366 | [CP-0042](checkpoints/0042-t23-esclusione-pds.md) |
| t26 | il t25 con effetto 0 sui geni sotto 5 CPM nei controlli del contesto (circa il 70 % dell'energia) | trial-01 | +0,138721 | 384 | [CP-0045](checkpoints/0045-t26-soglia-espressione.md) |
| **t28** | effetti t25 ×1,5 e dispersione per gene ×1 | trial-01 con dispersione | **+0,144845** | 359 | [CP-0052](checkpoints/0052-t28-punteggio-ufficiale.md) |

In tutti gli invii:
- lo scalato della `mse` vale 0 (tosato): la `mse` grezza segue l'energia che mettiamo, 1 + E/4786
  ([risposta comune, r2](../reports/trasferimento/risposta_comune_2026-09-26/RISULTATI.md));
- quello della fedeltà direzionale è negativo (−0,054 nel t24, vicino alla linea di base);
- il membro più grande è `pds_cosine` (0,636 scalato nel t24, il 74 % della media), ma dal t15 al
  t16 il guadagno è venuto quasi tutto dai membri DE.

Le tabelle per membro stanno nei checkpoint e nei confronti citati. I grezzi del t16 sono
derivati dagli scalati con le ancore: il 25 settembre `vcc status` serviva solo l'ultimo invio
(CP-0037).

### Che cosa è in corso o sospeso

Le scoperte della sessione lead, le prove e le conseguenze pratiche sono raccolte
in [SCOPERTE_R1](../reports/analisi/lead_scientist_2026-09-29/SCOPERTE_R1.md).
La fotografia distingue punteggi ufficiali, confronti locali e ipotesi ancora da verificare.
Le correzioni successive sulla portata degli score e sulla copertura del training sono in
[SCOPERTE_R2](../reports/analisi/lead_scientist_2026-09-29/SCOPERTE_R2.md).

- **Rete a sorgenti separate, entrambi i semi conclusi:** i cinque fold C su 12 contesti
  danno +0,002222 e +0,002459 di PDS contro il trasferimento; entrambi sotto la soglia
  registrata +0,01. Il vantaggio sulla rete cieca non è robusto fra semi e il CI del
  secondo include zero. Niente fit di produzione o correzione al t28.
  [Replica conclusa](checkpoints/0049-rete-sorgenti-replica.md),
  [replica e confronto completo](../reports/analisi/lead_scientist_2026-09-29/RISULTATI_NEURALE_SEED1.md).

- **Stack A/B conclusi, nessun candidato alla conferma:** sui dodici target di sviluppo
  A perde −0,158321 nell'indice locale e −0,333333 PDS; B, con gli assi misurati propri
  negli input, perde rispettivamente −0,128512 e −0,234848. Entrambi falliscono la
  regola registrata. Il ricontrollo numerico 085 termina il 29/09 alle 21:52:28 UTC:
  baseline A/B identica, selettore originale superato, stessi delta scientifici.
  Nessuna inferenza sulla riserva e nessuna promozione. Sono confronti locali,
  non punti VCC né un test generale di tutti i modelli pretrained.
  [CP-0051](checkpoints/0051-stack-ab-negativi.md),
  [risultati e limiti](../reports/analisi/lead_scientist_2026-09-29/neural/RISULTATI_STACK_AB.md),
  [protocollo A/B](../reports/analisi/lead_scientist_2026-09-29/neural/PROTOCOLLO_STACK_AB.md).

- **t28 valutato** ([CP-0052](checkpoints/0052-t28-punteggio-ufficiale.md)): effetti t25 ×1,5
  e dispersione per gene alla scala 1, registrato prima di generare (29/09, 18:56 UTC).
  **+0,144845**, rango 359, delta t25 +0,004607: nuovo massimo osservato, **non conclusivo**
  per la regola. Sul banco HepG2 l'indice locale era +0,028918 (96 bersagli, tre semi,
  IC97,5% [0,019526; 0,039342]), ma 95/96 bersagli erano già stati valutati e le ancore
  aggregate sono approssimate ([CP-0050](checkpoints/0050-credibilita-score-e-riserva.md)).
  La cronaca operativa (runtime Colab perso, rigenerazione identica alle 20:41 UTC, packaging
  alle 21:21, errore di I/O di Drive E-20260929-007, recupero locale alle 22:28, upload alle
  22:46 UTC, entry ZvrYZ4UazadAyuq4AsDB) è in [ricevuta dell'upload](../reports/invii/trial_2026-09-29/INVIO_T28.md),
  [decisione con i limiti](../reports/invii/trial_2026-09-29/DECISIONE_INVIO_T28.md),
  [recupero verificato](../reports/analisi/lead_scientist_2026-09-29/candidate_generation_remote/recovery_r2/RISULTATO_STAGE45_R2.md)
  e [autorizzazione](../reports/invii/trial_2026-09-29/autorizzazione_lead_2026-09-29.md).
  Evidenza: [registrazione](../reports/invii/prediction_t28_2026-09-29/prediction.json),
  [confronto](../reports/invii/prediction_t28_2026-09-29/comparison.json),
  [risultati del banco](../reports/analisi/lead_scientist_2026-09-29/RISULTATI_GENERATORE_CONFERMA.md),
  [audit degli score](../reports/analisi/lead_scientist_2026-09-29/SCORE_CREDIBILITA.md).

- **Apprendimento dagli errori applicato ai nuovi job:** [ERRORI.md](ERRORI.md) collega
  gli incidenti con causa, correzione, test e prove locali/remoti al preflight
  obbligatorio. Il job084 ha ricevute distinte PASS locale e runtime; quella remota
  delle 21:21:35 UTC precede lo scoring e non ne anticipa l'esito scientifico.

- **t23 valutato** il 28/09 alle 22:37 UTC ([CP-0042](checkpoints/0042-t23-esclusione-pds.md)): +0,141868,
  t23 − t22 = +0,0006, non conclusivo per la sua regola. Nei membri però `pds_cosine` sale di
  +0,0109 grezzo, mentre `nmae`, `reach` e Jaccard scendono. Il confronto cambia esclusione,
  pesatura e riscalatura insieme: l'attribuzione alla sola esclusione resta un'ipotesi
  ([CP-0046](checkpoints/0046-audit-lead-e-due-vie-neurali.md)).
  Ipotesi per il prossimo candidato: l'esclusione con i membri DE recuperati, da scegliere con lo
  scorer vero (azione 4 di R-REV), non con il proxy ([CP-0041](checkpoints/0041-proxy-contro-ufficiale.md)).
- **t26 valutato** il 29/09 alle 15:39 UTC ([CP-0045](checkpoints/0045-t26-soglia-espressione.md)): il t25 senza
  effetti sui geni sotto 5 CPM nel contesto, +0,138721, −0,0015 dal t25, non conclusivo. Il PDS non sale (−0,0020
  grezzo). Questo non sostiene l'ipotesi semplice che basti togliere i poco espressi;
  non identifica quale parte dell'intervento diverso del t23 abbia aiutato
  ([CP-0046](checkpoints/0046-audit-lead-e-due-vie-neurali.md)).
- **R-V2**, il modello per il set finale ([scheda](piani/modello-v2.md)), **ripresa dal proprietario
  il 28/09 alle 19:22**, in parallelo con R-REV. Letti con le loro regole ([modelli](../reports/modelli/README.md)):
  - l'encoder di contesto non passa su nessuna verità;
  - la rete di r1 sui tre semi non usa il contesto e perde contro il trasferimento su tre linee;
    passa solo J, i bersagli nuovi, di un millesimo;
  - più contesti (r2) aiutano la rete di pochi millesimi, provvisorio con un seme.

  - la misura decisiva per la rete relazionale (azione 6 di R-REV) è inconclusiva per W1, con la
    lettura «uso» a no: le relazioni fra geni non prevedono la risposta a un knockdown, nemmeno nella
    stessa linea ([CP-0043](checkpoints/0043-misura-decisiva-relazioni.md)). La rete relazionale non parte.

  Scelta del proprietario il 29/09 alle 11:25: prova generale del 22 ottobre e banco con lo scorer vero
  (azioni 3 e 4 di R-REV).
- **Direzione del proprietario (28/09 mattina):** usare tutti i dati, anche quelli fermi; una
  rete che impari relazioni fra geni e gruppi di comportamento che si ritrovano da un contesto
  all'altro; i dati farmacologici non devono prevalere, almeno all'inizio.
- **t12, t09 e t13** non si generano: il t17 ha fatto la domanda del t12 all'ampiezza buona, il
  t09 pagherebbe il silenzio (D-035), il t13 si è fermato per la sua regola.

### Che cosa aspetta una decisione del proprietario

- Se e come usare dati pubblici della **stessa linea** dei contesti di gara, identificata dai
  controlli: ammesso finora solo come esperimento dichiarato, con le identità fuori dal repository
  pubblico ([scheda R-V2](piani/modello-v2.md), «Domanda strategica aperta»).
- I download non ancora autorizzati elencati nella scheda R-V2 (DepMap CRISPRGeneEffect, profili
  basali MIX-seq, De Simone 2025, H1 della gara 2025).
- Il recupero dell'evidenza citata ma mai entrata nel repository (§5, punto 6): lo fa la
  sessione locale (azione 1 di R-REV); serve il proprietario per ciò che sta solo nella sessione di
  un altro agente.
- Il push in `main` della riorganizzazione e della revisione del 28/09, e le altre voci del §2 della
  scheda [R-REV](piani/revisione-critica.md). Dal 30/09 anche i commit locali della notte: il
  lavoro di Codex e della sessione `f4f38e58`, e il riordino della repo
  ([riordino](../reports/analisi/riordino_repo_2026-09-30/RIORDINO.md)); nessuno è su GitHub.
- Gli scratchpad temporanei di undici sessioni chiuse, fra cui quello del 26/09 con risultati
  verificati mai trascritti: se spostarli nella cartella dati e se trascriverli
  ([riordino](../reports/analisi/riordino_repo_2026-09-30/RIORDINO.md), §4).
- Lo spazio su C:, 3,8 GB liberi il 30/09: la prova generale in forma piena ne chiede circa 17.

### Il prossimo passo

**Dal 30/09 la direzione è quella del paragrafo [Direzione generale](#direzione-generale)**, e le
priorità correnti sono in [PIANI.md](PIANI.md): R-COMP dal 29/09. Restano validi gli incarichi
della scheda [R-REV](piani/revisione-critica.md), scelta dal proprietario il 28/09 alle 12:30, che
raccoglie in ordine le azioni della [revisione critica del 28/09](../reports/analisi/revisione_criticita_2026-09-28/REVISIONE.md):
le azioni 2 e 6 sono chiuse, la 3 attende la forma piena della prova generale, la 4 il job Colab.
Prima di prendere un'attività verificare nella scheda chi la sta seguendo.

**Ricerca esplorativa del 25 settembre:** [CP-0040](checkpoints/0040-biologia-contesti-donatori.md)
registra pattern con segno e di contesto, limiti della confidenza fra donatori CD4
e proposte architetturali. Misure riproducibili, nessun nuovo training o score;
qualifica anche l'estensione del banco MSE al punteggio ufficiale (R-018).

**Ricerca, decisione del 24 settembre (D-044):** cercare dati e modelli che generalizzino a
bersagli e contesti nuovi. **Non è richiesto avere geni perturbati in comune con i 300 attuali**
per considerare utile una sorgente. La prova principale dei nuovi predittori esclude dal training
sia i bersagli sia i contesti di test ([GENERALIZZAZIONE.md](GENERALIZZAZIONE.md),
[CP-0036](checkpoints/0036-generalizzazione-bersagli-contesti.md)).

Ogni invio consuma quota e passa dall'autorizzazione del proprietario. Il successo del
trasferimento dello stesso bersaglio non dimostra generalizzazione a bersagli mai osservati.

## 1. Il problema

Bisogna prevedere come cambia l'espressione genica di una cellula quando si spegne uno
di 300 geni, in tre tipi cellulari (A, B, C) mai visti prima. Della gara riceviamo solo
le cellule **non perturbate** dei tre contesti: 18.400 cellule ciascuno. Nessun esempio
di perturbazione, in nessuno dei tre. Si chiama previsione *zero-shot*: bisogna
imparare altrove e trasferire qui.

La classifica finale dipende solo dal set finale, su tre contesti diversi (D, E, F) e
300 perturbazioni nuove, rilasciato il 22 ottobre 2026. Le sottomissioni chiudono il
5 novembre 2026. Formato, metriche e setup: `README.md`.

## 2. Dove siamo

| Fase | Stato | Evidenza |
|---|---|---|
| Ambiente, CLI, dati di controllo, contratto di sottomissione e di punteggio | fatto | [SOTTOMISSIONE.md](SOTTOMISSIONE.md), `reports/gara/scorer_2026-09-12/vcc2026_contract.json` |
| Impacchettamento in memoria limitata (stadio 48) | fatto: 0,52 GiB di picco contro i 33,5 di `vcc prep` | [CP-0005](checkpoints/0005-packaging-streaming-trial01.md) |
| Ancore ufficiali di cinque membri su sei | fatto; reggono su tutti gli invii successivi | [CP-0021](checkpoints/0021-ancore-ufficiali-e-troppe-chiamate.md), `reports/gara/anchors_2026-09-17/` |
| Pipeline a singola cellula su Colab: K562 letto per intero, `ControlModel`, DE veloce identico allo scorer, banchi a sei metriche | fatto | [CP-0020](checkpoints/0020-singola-cellula-cis-generatore.md), [CP-0021](checkpoints/0021-ancore-ufficiali-e-troppe-chiamate.md) |
| Trasferimento dello stesso bersaglio da quattro sorgenti genome-scale (K562, CD4, Orion HCT116 e HEK293T) | ricetta del t22; ultimi cambi della media piccoli, ma ampiezza e generatore non confinati | §0, [audit 29/09](../reports/analisi/lead_scientist_2026-09-29/AUDIT_SCIENTIFICO.md) |
| Universi genome-wide: tutti i bersagli di ogni sorgente, non solo i 300 del pannello | fatti per K562, CD4, HCT116, HEK293T (corretti il 27/09), KOLF2.1J, A549, VIPerturb-seq, 19 linee HIPSCI | [sorgenti](../reports/sorgenti/README.md) |
| Banco con lo scorer vero su un contesto pubblico tenuto fuori (HepG2) | r1 fatto il 27/09: descrittivo | [banco HepG2](../reports/generatore_e_banchi/banco_hepg2_v2_2026-09-26/RISULTATI.md) |
| Modelli su molti contesti (modello a cancelli, rete, encoder, Tahoe T1) | nessuno passa la sua regola; R-V2 in pausa | [modelli](../reports/modelli/README.md) |
| Contesti A/B/C: saggio 10x Flex, impronte genetiche | misurato; le identità di linea restano ipotesi | [CP-0028](checkpoints/0028-cd4-sorgente-flex-trasferimento.md) |
| Generatore, cioè la fedeltà direzionale | trial-01 in tutti i migliori invii; `ControlModel` (t14) non attribuibile, la fedeltà scende | `reports/generatore_e_banchi/dispersion_2026-09-23/` |
| Esperimenti in pseudobulk dell'11–19/09 e infrastruttura degli agenti | chiusi; codice archiviato | [storico](../reports/storico/README.md), [ARCHIVIO.md](ARCHIVIO.md) |
| Set finale D/E/F | esce il 22 ottobre; invii fino al 5 novembre; prova generale (F8) non ancora fatta | [LAVORO.md](LAVORO.md) §7 |

## 3. Che cosa sappiamo e guida le scelte

Solo ciò che pesa sulle scelte di oggi, con il tipo di affermazione. La tabella delle misure
del 12–17 settembre è in [storico](storico/PROGETTO_sezioni_3_4_2026-09-28.md).

**Sul punteggio ufficiale**
- **Misurato.** Raddoppiare l'ampiezza vale +0,037 da t11 a t15 e +0,030 da t15 a t16; nel
  secondo passo `pds_cosine` sale appena, mentre fedeltà, `nmae`, `reach` e Jaccard fanno insieme
  +0,171 scalato ([CP-0033](checkpoints/0033-t15-ampiezza-doppia.md),
  [CP-0037](checkpoints/0037-t16-ampiezza-quadrupla.md)). D-006 è superata da D-042.
- **Misurato.** Dal t16 i cambi a un fattore valgono +0,0012 (t17 − t15), +0,0020 (t20 − t16),
  +0,0016 (t22 − t20), −0,0010 (t25 − t22); il solo seme vale +0,0016 (t24 − t22)
  ([lezioni](../reports/invii/lezioni_invii_2026-09-28/RISULTATI.md)).
- **Misurato.** La `mse` ufficiale grezza dei nostri invii segue 1 + E/4786 (scarto massimo 0,048
  su sei invii): le previsioni sono quasi ortogonali agli effetti veri, e nessuna ampiezza porta
  la `mse` sopra il suo zero ([risposta comune](../reports/trasferimento/risposta_comune_2026-09-26/RISULTATI.md)).
  Tutte le prime 100 squadre hanno la `mse` scalata positiva.
- **Misurato.** Aggiungere sorgenti per lo stesso bersaglio alzava `pds_cosine` quando l'ampiezza
  era bassa: CD4 +0,0102 ([CP-0030](checkpoints/0030-t10-attribuzione-cd4.md)), HCT116 +0,0104
  con i pesi cambiati insieme ([CP-0031](checkpoints/0031-t11-punteggio-orion.md)); HEK293T non si
  distingue né sul t15 né sul t20.
- **Misurato dagli organizzatori**, nelle note dello scorer: sul pannello val A circa 340 geni DE
  per bersaglio in media, il 12–30 % dei bersagli con meno di 10; la fedeltà conta il segno giusto
  anche sui geni non significativi nel vero ([CP-0039](checkpoints/0039-banco-varianti-restrizione.md)).
- **Misurato.** Il generatore di trial-01 fa centinaia di chiamate spurie per bersaglio a effetto
  nullo; con `ControlModel` sono quasi zero ma la fedeltà scende (t14,
  [CP-0032](checkpoints/0032-t14-controlmodel-fedelta.md)). Chi non chiama geni prende fedeltà 0
  (D-035).

**Sui dati e sul trasferimento** (proxy su sorgenti pubbliche, non punteggi VCC)
- **Misurato.** I profili di knockdown di linee diverse si somigliano poco: coseno mediano 0,02–0,03
  fra linee e laboratori diversi, circa 0,07 fra linee dello stesso laboratorio, 0,16 fra due
  esperimenti della stessa linea, 0,20–0,25 fra stati delle stesse cellule CD4. Confondono linea,
  laboratorio, protocollo e rumore ([atlante](../reports/trasferimento/atlante_2026-09-26/RISULTATI.md)).
- **Misurato.** Il segno della miscela delle altre sorgenti coincide con quello della sorgente
  tenuta fuori nel 51–56 % dei geni più mossi; con i bersagli scambiati si arriva già al 53,8 %, e
  «sempre su» fa il 63,6 % ([CP-0034](checkpoints/0034-audit-segni-e-ampiezza.md)).
- **Misurato.** Riponderare sorgenti, bersagli o programmi (EB, programmi, accordo per bersaglio,
  somiglianza basale, p53, trasferimento appreso) non batte la media a pesi uguali; aiuta invece
  togliere i geni che una sola sorgente stima ([trasferimento](../reports/trasferimento/README.md)).
- **Misurato.** Lo stimatore pseudobulk leggeva un gene senza conteggi come indotto (geni Y delle
  donatrici CD4): corretto con `min_expected` (cache r9, universi `_me1`)
  ([pseudoconteggio](../reports/sorgenti/pseudoconteggio_2026-09-27/RISULTATI.md)).
- **Misurato.** La gara è letta in 10x Flex, a sonde; **anche CD4 è GEM-X Flex v1**, verificato nelle
  12 righe dei metadati originali. La ricetta usa quindi già una sorgente Flex per 293 bersagli.
  Il ponte K562 VIPerturb–Replogle (metà Flex contro metà 0,110; Flex contro 3' 0,030) riguarda
  quella coppia, non tutte le sorgenti ([audit e fonte](../reports/analisi/lead_scientist_2026-09-29/AUDIT_DATI.md)).
- **Misurato.** I bersagli del pannello sono knockdown di forza tipica (percentile mediano 0,54 nel
  K562) e nessuno è nei pannelli *essential*; i banchi su bersagli essenziali misurano effetti più
  forti e più trasferibili di quelli del pannello ([atlante](../reports/trasferimento/atlante_2026-09-26/RISULTATI.md)).

**Sui modelli per contesti nuovi**
- **Misurato.** Nessun modello appreso passa la sua regola; dove batte la versione cieca non batte
  quella con il contesto scambiato; la perdita sulla famiglia tenuta fuori sale dopo 50–100 passi
  ([modelli](../reports/modelli/README.md)).
- **Misurato**, su HepG2 con lo scorer vero: la forma t19 batte la t16 (+0,026); raddoppiare la t19
  non è distinguibile da zero; la testa cis non si vede; Jaccard negativo in ogni braccio
  ([banco HepG2](../reports/generatore_e_banchi/banco_hepg2_v2_2026-09-26/RISULTATI.md)).
- **Ipotesi.** Le identità di linea di A/B/C sono sostenute da marcatori, impronte genetiche e
  da un confronto con espressione e numero di copie DepMap già svolto il 24/09. Il materiale
  resta fuori dalla repository pubblica; non è una conferma degli organizzatori
  ([audit del 29/09](../reports/analisi/lead_scientist_2026-09-29/AUDIT_DATI.md), §6).

## 4. Che cosa non sappiamo ancora

Le incertezze aperte al 28 settembre. Fra parentesi il numero che avevano nel vecchio §4
([storico](storico/PROGETTO_sezioni_3_4_2026-09-28.md)).

1. **Quanto sono grandi gli effetti da prevedere nei contesti di gara** (3). Le note degli
   organizzatori danno circa 340 geni DE per bersaglio in A; nessuna nostra misura li stima.
   L'essenzialità riguarda la sopravvivenza, non l'ampiezza della risposta (CP-0002).
2. **Se ampiezza e sorgenti scelte su A/B/C valgano per D/E/F** (2). Sono state scelte sul
   punteggio ufficiale di A/B/C con circa 15 invii; l'ottimo dipende dal generatore e dal numero
   di geni DE, che cambiano con contesto e pannello.
3. **Quanto rumore ha il punteggio ufficiale.** Una sola coppia di semi (t24 − t22 = 0,0016): da
   una sola osservazione, l'intervallo al 95 % per la deviazione standard della differenza va da
   circa 0,0007 a circa 0,05 (calcolo nella revisione critica, §3).
4. **Se i proxy dei banchi predicano il punteggio ufficiale.** Δ = 0,36 ΔPDS − 0,27 ΔnMAE non vede
   fedeltà, reach, Jaccard e MSE. **Misurato il 28/09** ([CP-0041](checkpoints/0041-proxy-contro-ufficiale.md)):
   sulle quattro differenze ufficiali sopra il rumore ne legge due con il segno giusto (una sorgente
   in più, il primo raddoppio); non legge la via di CD4 né il secondo raddoppio. Per la regola
   scritta prima, non si sceglie più un candidato sul solo proxy. Resta aperto se un proxy con più
   membri farebbe meglio.
5. **Se il contesto letto dai controlli sia utilizzabile** (nuovo). Ogni prova finora dice di no;
   con 4–13 contesti di poche famiglie, e laboratori e piattaforme confusi con le linee, non è
   ancora una risposta.
6. **Quanto pesino piattaforma e studio**, e se una mappa gene per gene aiuti su bersagli tenuti
   fuori. CD4 è già Flex; il ponte descrittivo VIPerturb–Replogle riguarda due studi K562 e
   non isola l'effetto della chimica ([audit](../reports/analisi/lead_scientist_2026-09-29/AUDIT_DATI.md)).
7. **Quali linee siano D/E/F, e se esistano Perturb-seq pubblici di quelle linee** (5, 7). Per
   A/B/C il percorso «stessa linea» è già stato esplorato in materiale riservato: un dataset
   mirato è stato provato e non adottato per il debole segnale specifico del bersaglio. Questo
   non chiude la ricerca di fonti ulteriori; identità e confronti restano fuori dalla repo pubblica.
8. **Se l'asse genico ufficiale sia ricostruibile in identificatori Ensembl** (4): contraddizione
   aperta, scheda [R-004](REGISTRO.md#r-004--docsrevisione_analisi_2026-09-11md).
9. **L'efficienza di knockdown nei contesti di gara** (8), non disponibile.
10. **Se la licenza CC-BY-NC-SA-4.0 di Orion sia compatibile con le regole della gara** (9).
    Ammessa negli invii per decisione del proprietario, non verificata con gli organizzatori.
11. **Quale backend DE usi il server** (10): localmente il DE veloce coincide con il percorso scanpy
    dello scorer (D-037); lo scarto fra backend non è misurato.
12. **Se un ricampionamento dei controlli sia ammesso** (13): D-017, non risolta e non urgente.
13. **Se la pipeline regga il 22 ottobre** (nuovo): la prova generale F8 non è fatta; con un
    pannello nuovo cambiano la risposta media tolta da γ = 1 e i bersagli coperti.

Le altre incertezze del vecchio elenco sono chiuse o assorbite: (1) le ancore di cinque membri
sono risolte, la `mse` resta stimata dalla classifica; (6) la co-espressione non predice l'effetto
su HepG2; (11), (12) e (21) sono superate dalla scelta dell'ampiezza sul punteggio ufficiale
(D-042); (14) il limite di `vcc prep` è aggirato dallo stadio 48; (15)–(19) sono linee chiuse con
il codice archiviato; (20) le copie su Drive sono state lette.

## 5. Criticità note

Dalla [revisione critica del 28 settembre](../reports/analisi/revisione_criticita_2026-09-28/REVISIONE.md),
che le argomenta con le fonti:

1. **La direzione gene per gene è debole e i membri del punteggio si compensano**. Il fit energia–MSE
   indica eccesso di energia, ma non dimostra saturazione di ogni ampiezza o generatore:
   [correzione del 29/09](../reports/analisi/lead_scientist_2026-09-29/AUDIT_SCIENTIFICO.md).
2. **Le decisioni di ricerca si prendono su un proxy di due membri su sei**, contro verità
   pubbliche rumorose, con regole «positivo su 3 linee su 4» che hanno poca potenza e molti
   confronti in parallelo.
3. **Il rumore del punteggio ufficiale è stimato su una coppia**, e i parametri della ricetta sono
   stati scelti su A/B/C: sul set finale vanno ricontrollati, non trasferiti.
4. **Piattaforma e normalizzazione**: sorgenti di saggi diversi, con CD4 già Flex; i profili basali
   sono normalizzati su insiemi di geni diversi. La media dei CPM per cellula può inoltre differire
   molto dalla composizione aggregata che il generatore Poisson conserva.
5. **Il codice di ricerca sta nei report**: circa 22.000 righe senza test, importate da altri
   banchi per percorso ([reports/README.md](../reports/README.md)).
6. **Evidenza citata ma assente dal repository**: l'audit di codex del 26/09, le schede R-018 e
   R-019, CP-0040, la previsione del t21, il report `biologia_architetture_2026-09-25`
   ([registro, R-020](REGISTRO.md#r-020--evidenza-citata-ma-assente-dal-repository)).

## 6. Percorso di lettura

Per lavorare bastano i primi tre punti. Gli altri servono quando un compito li richiede.

1. Questa pagina, §0 e §5.
2. [LAVORO.md](LAVORO.md): il percorso vivo, i comandi, le regole dell'invio e di Colab.
3. [reports/README.md](../reports/README.md): che cosa leggere per primo, e l'indice di ogni
   categoria con lo stato di ogni cartella.
4. La scheda del lavoro scelto, da [PIANI.md](PIANI.md).
5. [CP-0033](checkpoints/0033-t15-ampiezza-doppia.md), [CP-0037](checkpoints/0037-t16-ampiezza-quadrupla.md)
   e [CP-0039](checkpoints/0039-banco-varianti-restrizione.md): come l'ampiezza e la restrizione
   hanno fatto la ricetta di oggi.
6. [CP-0020](checkpoints/0020-singola-cellula-cis-generatore.md) e
   [CP-0021](checkpoints/0021-ancore-ufficiali-e-troppe-chiamate.md): la pipeline a singola
   cellula, le ancore ufficiali, e perché il numero di chiamate decide la fedeltà.
7. [CP-0001](checkpoints/0001-ricostruzione-stato-2026-09-12.md) e
   [CP-0002](checkpoints/0002-correzioni-dopo-revisione-umana.md): come il progetto ricostruisce
   la propria storia e si corregge. Servono per il metodo, non per lo stato.

I documenti di analisi dell'11–15 settembre sono in [storico/](storico/README.md), con il loro
stato: contengono materiale valido e conclusioni già corrette.

## 7. Come si tiene aggiornato questo sistema

Cinque regole, più i file che le servono: [LAVORO.md](LAVORO.md) si aggiorna quando cambia il
percorso vivo, [ARCHIVIO.md](ARCHIVIO.md) quando un file esce dall'albero (D-040).

1. **Un checkpoint quando succede qualcosa di significativo**, non a ogni modifica.
   Significativo vuol dire: un dataset adottato o scartato, un benchmark completato,
   un'ipotesi contraddetta, un cambio di strategia di modellazione o validazione.

   ```bash
   python scripts/30_new_checkpoint.py --slug benchmark-cd4 --title "Primo benchmark su CD4"
   ```

   Lo script numera da sé, non sovrascrive nulla e aggiorna l'indice. Poi si compila il
   file seguendo le otto sezioni del modello.

2. **I checkpoint non si riscrivono.** Se una conclusione risulta sbagliata si scrive
   un checkpoint nuovo e si compila la colonna "Corretto da" nell'indice. Il
   disaccordo storico resta visibile: serve a capire perché si è cambiata idea.

3. **Questa mappa si aggiorna** quando cambiano lo stato, le incertezze o il prossimo
   passo. Non deve diventare un riassunto di tutto: qui stanno le conclusioni, con un
   link all'evidenza.

4. **Il registro si aggiorna** quando un documento o un dato cambia stato. Se un
   materiale viene contraddetto, si apre una scheda che elenca le affermazioni
   contestate, non si butta via il documento intero.

5. **Un report nuovo va nella sua categoria**, `reports/<categoria>/<tema>_<data>/`, con una riga
   nel README della categoria e una nel registro (D-046, [reports/CLAUDE.md](../reports/CLAUDE.md)).

Controllo di coerenza prima di chiudere una sessione di lavoro:

```bash
python scripts/31_check_docs.py
```

Verifica che i percorsi citati esistano (anche quelli scritti prima del 28/09, seguiti nella
loro categoria), che ogni checkpoint abbia le sue otto sezioni, che l'indice corrisponda ai
file, e che ogni voce del registro segnata `da-verificare` o `superato` abbia una scheda
compilata.
