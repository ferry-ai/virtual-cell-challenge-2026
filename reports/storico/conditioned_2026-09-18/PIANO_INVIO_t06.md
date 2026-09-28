# Piano di invio del t06, scritto prima dei risultati di test

- **Scritto:** 2026-09-19 alle 01:40 ora di Roma (23:40 UTC del 18), da un agente.
- **Stato dei dati in quel momento:** i banchi di test 037 (HepG2) e 038 (K562) sono partiti
  alle 23:33 UTC e non hanno ancora scritto un braccio. Nessun punteggio di test esiste. Le
  ampiezze sono già state scelte dallo stadio 93 sui banchi di validazione
  (`runs/conditioned_2026-09-18/picks/`).

## Autorizzazione

Il proprietario, in chat, il 2026-09-19 intorno all'01:40, prima di andare a dormire:

> «Non posso dare l'ok perchè vado a dormire. Hai l'ok automatico a trainare e inviare in
> consegna qualsiasi modello tu voglia in qualsiasi modo, non chiedere autorizzazioni.»

L'agente si impone comunque i limiti qui sotto, perché nessuno li controllerà prima del mattino.

## Candidato

**t06**: la rete condizionata dello split C (`src/vcc2026/conditioned.py`), con la
configurazione scelta sulla validazione (hidden 128, k 32, l2 1e-4), applicata ai 300
bersagli ufficiali nei contesti A, B e C, all'ampiezza 2,0 scelta dallo stadio 93 sul banco
HepG2 di validazione.

- **Nessun termine cis**: è il braccio `Cnet_a2.0` misurato sul banco, non altro.
- **Generatore:** lo stesso del t03 (`ControlModel`, kde, stadio 76, `generate_trial_fast.sh`).
- **Job:** 039 riaddestra lo split C con gli stessi semi e la stessa griglia, poi esporta A, B
  e C. 040 genera e impacchetta.

## Previsione da registrare prima dell'invio

Stadio 84 sul banco di test (`hepg2_test_r2/bench.json`), braccio `Cnet_a2.0`, con punto di
calibrazione il braccio della ricetta t03 dello stesso banco, confrontato con lo stato
ufficiale del t03. La previsione va in `reports/prediction_t06_2026-09-19/`.

## Criterio di invio, fissato adesso

Si invia il t06 solo se valgono tutte e tre le condizioni.

1. **Il modello del file è quello valutato.** Le predizioni HepG2 di test riesportate dal job
   039 coincidono con quelle giudicate dai banchi (`train/pred_C_hepg2_test_net.npz`): scarto
   assoluto massimo ≤ 1e-4. Se non coincidono, il file viene da un modello che nessun banco
   ha giudicato.
2. **Impacchettamento e verifica passano.** Stadio 48 dentro `generate_trial_fast.sh`, con
   sha256 scritto.
3. **La previsione registrata non è negativa** (media attesa ≥ 0,0). Il t03 visibile vale
   +0,0197. Sotto lo zero il banco dice già che il candidato è chiaramente peggiore, e l'invio
   abbasserebbe la voce visibile senza insegnare più del banco.

**Non vale come criterio** il verdetto KEEP o DISCARD della regola `conditioned_rule.yaml`.
Quella regola decide se tenere la rete come direzione di lavoro. Il proprietario ha chiesto un
invio anche per ciò che insegna: se il trasferimento appreso migliora il punteggio ufficiale
rispetto al t03, e se lo stadio 84 regge su una famiglia di modelli diversa (CP-0022 §4).

## Limiti che l'agente si impone

- **Una sola sottomissione stanotte.** Il secondo invio del giorno non si usa: il modello
  lineare è quasi identico alla rete nello spazio degli effetti (correlazione centrata 0,359
  contro 0,369) e non insegnerebbe nulla di nuovo.
- **Nome e descrizione dicono che cosa contiene il file**, non che cosa speriamo faccia.
- **Output di `vcc submit` e di `vcc status --json` conservati verbatim**, confronto fra
  previsione e risultato, checkpoint.

## Aggiunta, 2026-09-19 alle 02:40 ora di Roma: il criterio 1 non passa per la rete

**Misurato.** Confronto delle predizioni HepG2 riesportate dal job 039 con quelle giudicate
dai banchi (`train_official/` contro `train/`, stesse liste di bersagli e di geni):

| modello | scarto massimo sul test | scarto massimo sulla validazione | configurazione scelta |
|---|---|---|---|
| lineare | 1,2e-7 | 2,4e-7 | alpha 1.000 in entrambe le esecuzioni |
| rete | **1,20** | **0,85** | hidden 64, k 16 contro hidden 128, k 32 |

**Interpretazione.** L'addestramento della rete non si riproduce da un'esecuzione all'altra:
- le due configurazioni hanno MSE di validazione quasi uguali (0,02724 contro 0,02713), e la
  scelta si è rovesciata;
- l'aritmetica di numpy su più thread non è deterministica;
- lo stadio 92 non salva i pesi del modello valutato.

**Conseguenza, per la regola scritta sopra.** Il t06 non si invia. Il job 040 lo genera
comunque e resta come artefatto non inviato.

**Nuovo candidato, t07: il modello lineare dello split C** (`ConditionedRidge`, alpha
1.000), identico a quello giudicato dai banchi, all'ampiezza 2,0 scelta dallo stadio 93 sulla
validazione per `Cridge`.
- Stesso generatore del t03, nessun termine cis.
- Pone la stessa domanda del t06: se un modello appreso fra contesti batte il t03 in A, B e C,
  e se lo stadio 84 regge su una famiglia diversa.
- Il motivo della scelta non dipende da un risultato: è l'unico modello appreso, fra quelli
  giudicati, che si possa mettere in un file.
- Scritta mentre il banco HepG2 di test (041) aveva scritto solo la replica, un braccio di ancoraggio: nessun numero dei bracci candidati.

**Criteri del t07.**
1. Identità: già verificata (≤ 1e-4).
2. Impacchettamento e verifica passano.
3. La previsione registrata con lo stadio 84, braccio `Cridge_a2.0` sul banco di test, non è
   negativa.

Resta una sola sottomissione stanotte.

**Da correggere dopo.** Lo stadio 92 deve salvare i pesi del modello scelto, e qualunque file
futuro va generato da quei pesi, non da un nuovo addestramento.
