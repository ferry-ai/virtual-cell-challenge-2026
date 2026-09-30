# Ambiti: dove sta che cosa

Una sezione per ambito del lavoro. Ognuna ha lo stato in poche righe, con il tipo di
affermazione, i due o tre documenti da leggere prima, dove sta l'evidenza, la scheda del piano
e gli errori da non ripetere. Qui si instrada e basta: i numeri completi stanno nelle fonti
citate. Lo stato generale e la direzione sono nel §0 di [PROGETTO.md](PROGETTO.md); i lavori
aperti in [PIANI.md](PIANI.md). Se l'evidenza chiave di un ambito cambia, si aggiorna la sua
sezione nello stesso commit (D-048). Scritto il 30/09.

## Le scoperte del 29–30 settembre, da tenere presenti

La sessione lead di Codex ha corretto premesse che reggevano molte scelte. Indice della cartella:
[lead_scientist_2026-09-29](../reports/analisi/lead_scientist_2026-09-29/README.md); scoperte in
[SCOPERTE_R1](../reports/analisi/lead_scientist_2026-09-29/SCOPERTE_R1.md) e
[SCOPERTE_R2](../reports/analisi/lead_scientist_2026-09-29/SCOPERTE_R2.md).

- **Verificato:** CD4 è GEM-X Flex v1, come la gara. La premessa «tutte le sorgenti tranne
  VIPerturb sono in 3'» era falsa ([CP-0046](checkpoints/0046-audit-lead-e-due-vie-neurali.md)).
- **Ricostruito:** la media quasi ferma dal t16 nasconde compensazioni fra i membri. Il plateau non
  dimostra che ampiezza e generatore siano ottimizzati (stesso checkpoint).
- **Misurato:** ampiezza e dispersione del generatore interagiscono. Il t28 le combina: +0,144845,
  nuovo massimo osservato, ma solo +0,0046 sul t25, sotto la soglia registrata
  ([CP-0052](checkpoints/0052-t28-punteggio-ufficiale.md)).
- **Misurato:** la rete che pesa le sorgenti e il modello preaddestrato Stack non battono il
  trasferimento ([CP-0049](checkpoints/0049-rete-sorgenti-replica.md),
  [CP-0051](checkpoints/0051-stack-ab-negativi.md)).
- **Misurato:** le ancore aggregate non convertono esattamente in punti VCC, e la «riserva» della
  conferma era già stata valutata ([CP-0050](checkpoints/0050-credibilita-score-e-riserva.md)).

## 1. Gara e lettura dei punteggi

- **Misurato.** Il punteggio è la media dei sei membri scalati. Un invio si legge dai sei scalati
  pubblicati nello status: le ancore aggregate hanno errori misurati ([CP-0050](checkpoints/0050-credibilita-score-e-riserva.md)).
- **Misurato.** In tutti i nostri invii la `mse` scalata vale 0 (tosata); tutte le prime 100
  squadre l'hanno positiva ([PROGETTO §3](PROGETTO.md#3-che-cosa-sappiamo-e-guida-le-scelte)).
- **Regola.** A, B e C sono 10x Flex; le loro identità di linea sono ipotesi e non si scrivono
  mai accanto ai contesti nella repo.

Leggi prima: [gara](../reports/gara/README.md), [LAVORO §2](LAVORO.md#2-le-regole-dellinvio)
(il punto 7 dice come leggere un punteggio),
[credibilità degli score](../reports/analisi/lead_scientist_2026-09-29/SCORE_CREDIBILITA.md).

## 2. Invii e ricetta di produzione

- **Misurato.** Massimo osservato: t28, +0,144845, rango 359. Contro il t25 fa +0,0046, non
  conclusivo per la sua regola. La ricetta di riferimento resta quella del t22 (media t22/t24
  0,14207) ([CP-0052](checkpoints/0052-t28-punteggio-ufficiale.md)).
- **Misurato.** Il t28 alza fedeltà (+0,051 scalato) e reach (+0,055), perde NMAE (−0,069) e
  Jaccard (−0,008): l'intervento sull'emissione sposta i membri DE, con costi.
- **Interpretazione.** Dal t16 i cambi della media sono piccoli, ma diversi membri si compensano
  ([audit scientifico](../reports/analisi/lead_scientist_2026-09-29/AUDIT_SCIENTIFICO.md)).

Leggi prima: la tabella dei punteggi nel §0 di [PROGETTO](PROGETTO.md), [invii](../reports/invii/README.md),
[che cosa lascia un invio](../reports/CLAUDE.md). Piano: [S-INVII](piani/invii-finale.md),
[R-COMP](piani/modello-competitivo.md).

## 3. Generatore e banchi con lo scorer vero

- **Misurato.** Sul banco HepG2 ampiezza e dispersione interagiscono (+0,0177 d'indice
  nello sviluppo); la conferma su 96 bersagli dà +0,0289, ma 95 erano già stati valutati
  ([CP-0047](checkpoints/0047-conferma-generatore-t28.md), [CP-0050](checkpoints/0050-credibilita-score-e-riserva.md)).
- **Interpretazione.** Il banco HepG2 ha preso il verso dei cambi ufficiali e ne ha sovrastimato
  l'entità ([errori di metodo](ERRORI.md#errori-di-metodo-già-commessi)).
- **In attesa.** Il banco con lo scorer vero sui bersagli del pannello K562 ha il codice pronto; il
  job Colab lo avvia il proprietario ([banco K562](../reports/generatore_e_banchi/banco_k562_pannello_2026-09-29/RISULTATI.md),
  azione 4 di [R-REV](piani/revisione-critica.md)).

Leggi prima: [generatore e banchi](../reports/generatore_e_banchi/README.md), la sezione
«Generatore e t28» dell'[indice lead](../reports/analisi/lead_scientist_2026-09-29/README.md),
[audit del generatore](../reports/analisi/lead_scientist_2026-09-29/AUDIT_GENERATORE.md).

## 4. Dati e sorgenti

- **Verificato.** CD4 è Flex e K562 Replogle è 3'. Per Orion le schede indicano GEM-X 5′, da
  riverificare sul protocollo primario ([audit dei dati](../reports/analisi/lead_scientist_2026-09-29/AUDIT_DATI.md)).
- **Misurato.** I profili basali sono normalizzati su supporti genici diversi: rinormalizzare non
  ricrea i geni mancanti ([basali sull'asse](../reports/sorgenti/basali_asse_2026-09-29/RISULTATI.md)).
- **Misurato.** La produzione usa quattro sorgenti, la rete r2 dodici contesti; diciannove linee
  HIPSCI già pronte non sono mai entrate in un training
  ([copertura del training](../reports/analisi/lead_scientist_2026-09-29/TRAINING_COPERTURA.md)).
- **Regola.** Una sorgente non si scarta per scarsa sovrapposizione con i 300 bersagli (D-044); un
  gene non misurato resta mascherato, non vale zero (D-009).

Leggi prima: [sorgenti](../reports/sorgenti/README.md), [GENERALIZZAZIONE](GENERALIZZAZIONE.md).
Piano: [R-DATI](piani/dati-affidabilita.md), [R-COMP](piani/modello-competitivo.md).

## 5. Modelli appresi e generalizzazione

- **Misurato.** Nessun modello appreso ha passato la sua regola: encoder, modello a cancelli, rete
  dei contesti, rete relazionale ([CP-0043](checkpoints/0043-misura-decisiva-relazioni.md)), rete
  sulle sorgenti (+0,0022 e +0,0025 contro la soglia +0,01), Stack A e B.
- **Interpretazione.** Il contesto letto dai controlli non ha dato finora un beneficio robusto;
  questo non dimostra che nessuna rete possa funzionare ([CP-0049](checkpoints/0049-rete-sorgenti-replica.md)).
- **Regola proposta.** Una rete nuova si prova sui sei membri, con una riserva mai valutata
  ([audit del prescreen](../reports/analisi/lead_scientist_2026-09-29/neural/NN_PRESCREEN_AUDIT.md)).

Leggi prima: [modelli](../reports/modelli/README.md), la sezione «Rete sulle sorgenti» dell'[indice lead](../reports/analisi/lead_scientist_2026-09-29/README.md),
[GENERALIZZAZIONE](GENERALIZZAZIONE.md). Piano: [R-COMP](piani/modello-competitivo.md),
[R-V2](piani/modello-v2.md).

## 6. Set finale D, E, F

- **Fatto.** La classifica finale dipende solo da D/E/F, rilasciati il 22 ottobre; gli invii
  chiudono il 5 novembre.
- **Misurato.** La prova generale in forma ridotta produce un `.vcc` valido
  ([CP-0044](checkpoints/0044-prova-generale-22-ottobre.md)); D1–D5 e D9–D11 sono corretti con i
  loro test. La forma piena chiede circa 17 GB liberi: il 30/09 alle 02:30 su C: ce n'erano 3,8.

Leggi prima: [LAVORO §7](LAVORO.md#7-il-set-finale-22-ottobre), [la prova generale](../reports/invii/prova_generale_2026-09-28/RISULTATI.md).
Piano: azione 3 di [R-REV](piani/revisione-critica.md), [S-INVII](piani/invii-finale.md).

## 7. Operazioni: calcolo, job, disco, cartella condivisa

- **Procedura.** Colab passa dal dispatcher ([LAVORO §3](LAVORO.md#3-colab-generatore-controlmodel-e-banchi));
  Kaggle da notebook privati ([calcolo del 29/09](../reports/analisi/lead_scientist_2026-09-29/CALCOLO.md)).
  Ogni job nuovo supera il preflight ([ERRORI](ERRORI.md)); i guasti vanno nel
  [registro degli incidenti](../reports/analisi/lead_scientist_2026-09-29/learning/README.md).
- **Regola.** L'uso della quota, i download e i push li autorizza il proprietario (CLAUDE.md).

Leggi prima: [lezioni operative](ERRORI.md#lezioni-operative-da-non-ripetere).

## 8. Metodo, evidenza e memoria del progetto

| Domanda | Dove |
|---|---|
| Quanto fidarsi di un documento | [REGISTRO](REGISTRO.md) |
| Perché si è deciso qualcosa | [DECISIONI](DECISIONI.md), la tabella in cima |
| Che cosa è successo e quando | [indice dei checkpoint](checkpoints/INDICE.md) |
| Quali ragionamenti sono già stati smentiti | [errori di metodo](ERRORI.md#errori-di-metodo-già-commessi) |
| Dove sta l'evidenza, per categoria | [reports](../reports/README.md) |
| Codice ritirato e come riportarlo | [ARCHIVIO](ARCHIVIO.md) |
| Come è stata riordinata la repo il 30/09 | [riordino](../reports/analisi/riordino_repo_2026-09-30/RIORDINO.md) |

Una previsione si registra prima dell'invio, con la regola di lettura
([CP-0030](checkpoints/0030-t10-attribuzione-cd4.md)); un numero locale non diventa un punteggio VCC.
