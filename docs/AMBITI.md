# Ambiti: dove sta che cosa

**Perimetro:** una sezione per ogni area del progetto VCC, più un rimando per gli strumenti di
esecuzione, l'infrastruttura degli agenti e l'archivio. Ogni sezione dà lo stato in poche righe,
con il tipo di affermazione, i due o tre documenti da leggere prima, la scheda del piano e gli
errori da non ripetere. **Si legge solo la sezione del proprio compito.** **Fonti:** i checkpoint e
i report citati; questa pagina instrada e non è evidenza, e i numeri completi stanno nelle fonti.
**Si aggiorna** nello stesso commit dell'evidenza che cambia una sezione (D-048). Scritta il 30/09.

Lo stato generale e la direzione sono nel §0 di [PROGETTO](PROGETTO.md); le priorità in
[PIANI](PIANI.md). La revisione lead del 29–30/09 ha corretto premesse che reggevano molte scelte
(CD4 è già Flex; il plateau non è saturazione): le sue scoperte sono riportate nelle sezioni 1–5 e
indicizzate in [lead_scientist_2026-09-29](../reports/analisi/lead_scientist_2026-09-29/README.md).

## Progetto VCC

### 1. Gara e lettura dei punteggi

- **Misurato.** Il punteggio è la media dei sei membri scalati. Un invio si legge dai sei scalati
  pubblicati nello status: le ancore aggregate hanno errori misurati ([CP-0050](checkpoints/0050-credibilita-score-e-riserva.md)).
- **Misurato.** In tutti i nostri invii la `mse` scalata vale 0 (tosata); tutte le prime 100
  squadre l'hanno positiva ([PROGETTO §3](PROGETTO.md#3-che-cosa-sappiamo-e-guida-le-scelte)).
- **Regola.** A, B e C sono 10x Flex; le loro identità di linea sono ipotesi e non si scrivono
  mai accanto ai contesti nella repo (regola globale di [CLAUDE.md](../CLAUDE.md)).

Leggi prima: [PROCEDURE §2](PROCEDURE.md#2-le-regole-dellinvio), punto 7, per leggere un punteggio;
[credibilità degli score](../reports/analisi/lead_scientist_2026-09-29/SCORE_CREDIBILITA.md);
[gara](../reports/gara/README.md).

### 2. Invii e ricetta di produzione

- **Misurato.** Massimo osservato: t28, +0,144845, contro il t25 +0,0046, non conclusivo per la sua
  regola; la ricetta di riferimento resta quella del t22 ([CP-0052](checkpoints/0052-t28-punteggio-ufficiale.md)).
  Tutti i punteggi: [invii](../reports/invii/README.md).
- **Misurato.** Il t28 alza fedeltà (+0,051 scalato) e reach (+0,055), perde NMAE (−0,069) e
  Jaccard (−0,008): l'intervento sull'emissione sposta i membri DE, con costi.
- **Interpretazione.** Dal t16 i cambi della media sono piccoli, ma diversi membri si compensano
  ([audit scientifico](../reports/analisi/lead_scientist_2026-09-29/AUDIT_SCIENTIFICO.md)).

Leggi prima: [che cosa lascia un invio](../reports/CLAUDE.md), [PROCEDURE §1–2](PROCEDURE.md#1-il-percorso-di-un-invio).
Piano: [R-COMP](piani/modello-competitivo.md); [S-INVII](piani/invii-finale.md) è ferma al 28/09.

### 3. Generatore e banchi con lo scorer vero

- **Misurato.** Sul banco HepG2 ampiezza e dispersione interagiscono (+0,0177 d'indice
  nello sviluppo); la conferma su 96 bersagli dà +0,0289, ma 95 erano già stati valutati
  ([CP-0047](checkpoints/0047-conferma-generatore-t28.md), [CP-0050](checkpoints/0050-credibilita-score-e-riserva.md)).
- **Interpretazione.** Il banco HepG2 ha preso il verso dei cambi ufficiali e ne ha sovrastimato
  l'entità ([errori di metodo](ERRORI.md#errori-di-metodo-già-commessi)).
- **In attesa.** Il banco con lo scorer vero sui bersagli del pannello K562 ha il codice e i bracci
  pronti; il job Colab aspetta di girare da solo ([banco K562](../reports/generatore_e_banchi/banco_k562_pannello_2026-09-29/RISULTATI.md),
  azione 4 di [R-REV](piani/revisione-critica.md)).

Leggi prima: [generatore e banchi](../reports/generatore_e_banchi/README.md), la sezione
«Generatore e t28» dell'[indice lead](../reports/analisi/lead_scientist_2026-09-29/README.md),
[audit del generatore](../reports/analisi/lead_scientist_2026-09-29/AUDIT_GENERATORE.md). Per
cambiare il codice: `scripts/CLAUDE.md` e `src/vcc2026/CLAUDE.md`.

### 4. Dati e sorgenti

- **Verificato.** CD4 è Flex e K562 Replogle è 3'. Per Orion le schede indicano GEM-X 5′, da
  riverificare sul protocollo primario ([audit dei dati](../reports/analisi/lead_scientist_2026-09-29/AUDIT_DATI.md)).
- **Misurato.** I profili basali sono normalizzati su supporti genici diversi: riscalarli non
  ricrea i geni mancanti (K562 ne misura 7.681 nel basale) ([audit dei dati](../reports/analisi/lead_scientist_2026-09-29/AUDIT_DATI.md), §4).
  Il ricalcolo dell'azione 5 di R-REV ha il protocollo ma non ancora i risultati
  ([basali sull'asse](../reports/sorgenti/basali_asse_2026-09-29/RISULTATI.md)).
- **Misurato.** La produzione usa quattro sorgenti, la rete r2 dodici contesti; diciannove linee
  HIPSCI già pronte non sono mai entrate in un training
  ([copertura del training](../reports/analisi/lead_scientist_2026-09-29/TRAINING_COPERTURA.md)).
- **Regola.** Una sorgente non si scarta per scarsa sovrapposizione con i 300 bersagli (D-044); un
  gene non misurato resta mascherato, non vale zero (D-009).

Leggi prima: [GENERALIZZAZIONE](GENERALIZZAZIONE.md), [sorgenti](../reports/sorgenti/README.md).
Piano: [R-COMP](piani/modello-competitivo.md); [R-DATI](piani/dati-affidabilita.md) è ferma al
28/09, con il lavoro proseguito in R-V2 e R-COMP.

### 5. Modelli appresi e generalizzazione

- **Misurato.** Nessun modello appreso ha passato la sua regola: encoder, modello a cancelli, rete
  dei contesti, rete relazionale ([CP-0043](checkpoints/0043-misura-decisiva-relazioni.md)), rete
  sulle sorgenti (+0,0022 e +0,0025 contro la soglia +0,01), Stack A e B
  ([CP-0049](checkpoints/0049-rete-sorgenti-replica.md), [CP-0051](checkpoints/0051-stack-ab-negativi.md)).
- **Interpretazione.** Il contesto letto dai controlli non ha dato finora un beneficio robusto;
  questo non dimostra che nessuna rete possa funzionare ([CP-0049](checkpoints/0049-rete-sorgenti-replica.md)).
- **Regola proposta.** Una rete nuova si prova sui sei membri, con una riserva mai valutata
  ([audit del prescreen](../reports/analisi/lead_scientist_2026-09-29/neural/NN_PRESCREEN_AUDIT.md)).

Leggi prima: [GENERALIZZAZIONE](GENERALIZZAZIONE.md), [modelli](../reports/modelli/README.md), la
sezione «Rete sulle sorgenti» dell'[indice lead](../reports/analisi/lead_scientist_2026-09-29/README.md).
Piano: [R-COMP](piani/modello-competitivo.md), [R-V2](piani/modello-v2.md).

### 6. Set finale D, E, F

- **Fatto.** La classifica finale dipende solo da D/E/F, rilasciati il 22 ottobre; gli invii
  chiudono il 5 novembre.
- **Misurato.** La prova generale in forma ridotta produce un `.vcc` valido
  ([CP-0044](checkpoints/0044-prova-generale-22-ottobre.md)); D1–D5 e D9–D11 sono corretti con i
  loro test. La forma piena chiede circa 17 GB liberi: il 30/09 alle 02:30 su C: ce n'erano 3,8.

Leggi prima: [PROCEDURE §7](PROCEDURE.md#7-il-set-finale-22-ottobre), [la prova generale](../reports/invii/prova_generale_2026-09-28/RISULTATI.md).
Piano: azione 3 di [R-REV](piani/revisione-critica.md).

## Strumenti di esecuzione

### 7. Calcolo, job, disco

Le procedure stanno in [PROCEDURE](PROCEDURE.md): §1–2 per generare, impacchettare e inviare, §3 per i
job su Colab e Kaggle, §7 per il set finale. Ogni job nuovo supera il preflight di
[ERRORI](ERRORI.md), dove sono anche le [trappole operative](ERRORI.md#lezioni-operative-da-non-ripetere)
già incontrate. Chi autorizza la quota, i download e i push: [CLAUDE.md](../CLAUDE.md).

## Infrastruttura degli agenti

La base di lancio `agent-hub` (fuori dalla repo), l'orchestratore e la catena di cicli ritirati il
23/09 e il coordinamento fra sessioni stanno in [AGENTI](AGENTI.md). Chi lavora su dati, modelli o
invii non ne ha bisogno.

## Archivio e storia

### 8. Metodo, evidenza e memoria del progetto

La sede di ogni tipo di informazione è in [docs/CLAUDE.md](CLAUDE.md). Per ricostruire una decisione
o un risultato: la tabella in cima a [DECISIONI](DECISIONI.md), poi la sua sezione; il checkpoint che
cita, dall'[indice](checkpoints/INDICE.md) con la colonna «Corretto da»; lo stato di un documento con
`python scripts/31_check_docs.py --status <percorso>`. Il codice ritirato e come riportarlo:
[ARCHIVIO](ARCHIVIO.md). I due riordini della repo del 30/09:
[notte](../reports/analisi/riordino_repo_2026-09-30/RIORDINO.md) e
[pomeriggio](../reports/analisi/ingresso_agenti_2026-09-30/RIORDINO.md).

Una previsione si registra prima dell'invio, con la regola di lettura
([CP-0030](checkpoints/0030-t10-attribuzione-cd4.md)); un numero locale non diventa un punteggio VCC.
