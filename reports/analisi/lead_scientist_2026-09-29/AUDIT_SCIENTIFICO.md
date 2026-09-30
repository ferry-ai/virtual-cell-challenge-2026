# Audit scientifico e candidati — 29 settembre 2026

**Autore:** Codex, sottoagente `audit_scientifico` della chat
`01a0ee03-b357-7012-81a9-e8d7de767478`. Lettura delle evidenze e del codice dello scorer;
ricostruzione leggera dei punteggi alle 16:43–16:46 UTC circa. Nessun dataset grande letto,
nessun training, nessun job remoto e nessun invio avviato da questo sottoagente.

**Conclusione operativa — interpretazione.** La ricetta attuale ha un problema di direzione
e un compromesso fra metriche. Non abbiamo però dimostrato che ampiezza e generatore siano
ottimizzati: l'ultimo raddoppio isolato ufficiale ha guadagnato **+0,03009**. Per la scadenza
propongo un piccolo confronto incrociato ampiezza × dispersione sulla ricetta t25, conservando
un candidato semplice ad ampiezza 1,5 volte quella corrente. La nuova rete e la sola risposta
comune hanno, oggi, meno evidenza utile per un candidato immediato.

Questa è una proposta falsificabile, non la promessa di un punteggio migliore. La scelta finale
spetta alla lead che integra anche audit dei dati e prove di generazione di questa sessione.

## 1. Evidenza ricostruita, senza aggiornare gli originali

Lo script [reconstruct_scores.py](audit_scientifico/reconstruct_scores.py) legge la raccolta
degli invii e i `comparison.json`, controlla le coincidenze e ricostruisce **17 invii** e
**8 contrasti**. Conserva separatamente i grezzi pubblicati e quelli derivati del t16; non
ricostruisce la MSE del t16 dal suo scalato tosato a zero. Output:

- [scores.csv](audit_scientifico/r1/scores.csv): punteggi e membri;
- [contrasts.csv](audit_scientifico/r1/contrasts.csv): differenze e contributi alla media;
- [evidence.json](audit_scientifico/r1/evidence.json): fonti per campo, ricette, hash degli
  input e analisi di sensibilità della MSE.

**Calcolo retrospettivo:** definiamo movimento lordo = somma dei valori assoluti dei cambi
dei sei membri scalati, ciascuno diviso per sei. La percentuale cancellata è
`1 − |cambio della media| / movimento lordo`. Non è un test statistico: descrive compensazioni.

| Confronto | Cambio della media | Movimento lordo | Cancellazione fra membri |
|---|---:|---:|---:|
| t15 − t11, ampiezza ×2 | +0,03676 | 0,03676 | 0,0% |
| t16 − t15, ampiezza ×2 | +0,03009 | 0,03009 | 0,0% |
| t20 − t16 | +0,00205 | 0,01471 | 86,1% |
| t22 − t20 | +0,00157 | 0,00972 | 83,8% |
| t24 − t22, solo seme | +0,00165 | 0,00238 | 30,7% |
| t25 − t22 | −0,00101 | 0,00531 | 80,9% |
| t23 − t22 | +0,00062 | 0,01119 | 94,5% |
| t26 − t25 | −0,00152 | 0,00220 | 31,1% |

**Interpretazione:** almeno t20, t22 e t23 non sono semplicemente «nessun cambiamento».
La media nasconde movimenti contrari. Questo non dimostra la significatività dei singoli
movimenti, ma rende ingiustificata la deduzione «media piatta, quindi nessuna leva rimasta».
Esempio t23: contributi alla media PDS +0,00416 e fedeltà +0,00174, contro nMAE −0,00287,
reach −0,00163 e Jaccard −0,00078. Recuperare parte del costo DE è una domanda sensata.

## 2. Cinque inferenze da correggere

### 2.1 Il plateau non ha confinato l'ampiezza ottima

**Verificato nelle ricette:** t16 usa effetti `raw`, ampiezza 0,788, senza testa cis;
t20 usa `shrunk`, ampiezza 1,576 e testa cis a scala 2. È un cambio di forma, ampiezza e cis
insieme. t17 contro t15 aggiunge HEK293T ma cambia anche la scala da 0,394 a 0,4285 per
uguagliare il q99. Sono confronti utili, non esperimenti isolati sull'ampiezza corrente.

Fonti: `configs/recipes/t16.json`, `t20.json`, `t17.json`;
`reports/invii/prediction_t20_2026-09-26/comparison.json`, campo `reading_rule_outcome`;
`docs/checkpoints/0037-t16-ampiezza-quadrupla.md`, §§4 e 6.

**Misurato nel banco HepG2:** `t19like ×2 − ×1` = +0,015, intervallo −0,012…+0,039;
`t16like ×2 − ×1` = +0,057, intervallo +0,037…+0,076
(`reports/generatore_e_banchi/banco_hepg2_v2_2026-09-26/RISULTATI.md`, righe 43–44).
Il primo risultato non prova equivalenza né assenza di guadagno. Il t16 originale chiedeva
esplicitamente un altro raddoppio, che non è stato letto da solo sul server.

**Disposizione proposta:** sostituire «ricetta satura; non verranno punti da altre ampiezze»
con «ultime modifiche a guadagno netto piccolo; ampiezza della forma corrente non confinata».

### 2.2 Una differenza fra due semi non è una deviazione standard nota

**Misurato:** t24 − t22 = +0,001646, una sola differenza. La soglia ±0,005 è utilizzabile
come soglia operativa prefissata. Non è automaticamente un intervallo al 95% né dimostra
che cambi inferiori siano rumore. Anche «dodici volte il rumore» del PDS t23 significa
solo dodici volte quella particolare differenza osservata.

La revisione del 28/09 espone già un intervallo molto largo per sigma; la sua seconda stima
mescola cambi reali possibili e differenze dipendenti. Chiamarla «tetto del rumore» è una
lettura euristica, non un limite probabilistico garantito. Fonte:
`reports/analisi/revisione_criticita_2026-09-28/REVISIONE.md`, §2.4.

### 2.3 t26 non localizza causalmente il guadagno di t23

**Verificato:** t23 esclude una lista, pesa continuamente gli altri geni e riscalala; t26
azzera tutti i geni sotto 5 CPM, con un'altra cache. Questi interventi non sono la stessa
ablazione su due strati complementari. L'effetto quasi nullo del secondo non identifica
quale componente del primo abbia aiutato: possono esserci compensazioni e interazioni.

**Misurato:** t26 − t25 dà PDS −0,00201 grezzo e media −0,00152; il risultato non sostiene
l'ipotesi semplice «basta togliere i poco espressi». Non dimostra invece che ogni gene poco
espresso della lista t23 fosse irrilevante. Fonte:
`reports/invii/prediction_t26_2026-09-29/comparison.json`, campi `raw` e `member_reading`.

**Prova identificante:** stessa cache r9, stessa scala, stessa lista di esclusione del t27;
bracci lista intera, soli geni della lista ≥5 CPM, soli geni della lista <5 CPM. La
riscalatura è un ulteriore fattore, esplicito. Non promuovere l'interpretazione del t26 a misura.

### 2.4 La sola risposta comune non può plausibilmente colmare il divario MSE

**Interpretazione numerica con limiti:** dalle ancore ricostruite della classifica, la
baseline che conosce la risposta media del contesto ha MSE grezza circa 0,986–0,992,
contro circa 1 del nulla. Il margine oracolare della sola comune è quindi dell'ordine
di 0,01 grezzo, non dei circa 0,23 scalati che separavano il progetto dai primi 100.
Le ancore sono approssimate e aggregate fra contesti: non è un limite esatto per ogni contesto.

L'analisi originale lo riconosce: «Shared shift»,
`reports/trasferimento/risposta_comune_2026-09-26/agenti/membro_mse_claude2.md`, riga 83.
La sintesi `reports/invii/lezioni_invii_2026-09-28/RISULTATI.md`, §§«Collegamenti» e
«Che cosa ne segue», dà alla comune un ruolo più forte di quanto questa aritmetica sostenga.
HepG2, con baseline circa 0,746, è un regime diverso: trasferire quella priorità ad A/B/C
senza controllare l'ancora introduce un bias di dominio.

**Conseguenza:** il problema MSE richiede prevalentemente risposta specifica del bersaglio
meglio orientata e calibrata, oppure la verifica di un errore concreto di generazione.
Non c'è evidenza per assegnare la scadenza di oggi a imparare soltanto la risposta comune.

### 2.5 L'ortogonalità quasi completa resta un'inferenza condizionata

**Misurato:** la relazione fra energia prevista e MSE pubblicata è forte. È un'evidenza
di eccesso di energia rispetto al segnale allineato, utile per scartare promesse MSE vaghe.
Non identifica da sola l'esatto coseno con la verità.

**Calcolo replicato:** nel modello approssimato `u = u0 + P a² − 2 C a`, t11 e t15 forniscono
due osservazioni per tre incognite. A parità dei due punteggi osservati, assumere `u0=1`
produce coseno 0,039; `u0=1,05` produce 0,124; `u0=1,15` produce 0,264. Queste alternative
non sono dichiarate equiprobabili. Mostrano non-identificabilità, già segnalata nell'analisi
originale alla riga 61 e replicata in `audit_scientifico/r1/evidence.json`.

Il fit energia–MSE usa inoltre più ricette, medie fra contesti e un profilo atteso al posto
di ogni pseudobulk realizzato. Il risultato è un modello empirico locale, non una misura
diretta dei vettori veri. La frase operativa corretta è «lo shrinkage globale da solo ha
poche prospettive per l'MSE», non «nessuna ampiezza di nessuna variante può mai farla salire».

## 3. Il generatore è una linea riapribile con una prova precisa

**Verificato:** il generatore Gamma-Poisson per gene fu fermato perché al nullo produceva
5 / 15 / 31 chiamate mediane in A/B/C, contro una soglia prefissata di 10 in ogni contesto.
Non fu confrontato sulla ricetta t25 ad ampiezza alta. Fonti:
`reports/generatore_e_banchi/dispersion_2026-09-23/PRIMA_DEI_RISULTATI.md`, punto 2;
`RISULTATO_NULLO.md`, tabella e applicazione della regola.

**Interpretazione:** rispettare quella regola era corretto per il t13 registrato. Estenderla
alla chiusura del filone è scorretto: il passaggio da centinaia di chiamate artefatte a poche
decine è un cambiamento forte, e «meno di 10 al nullo» non è la funzione obiettivo ufficiale.
Il t14 non chiude il caso: ha cambiato famiglia di generatore, ricetta e calibrazione insieme.

**Verificato nel codice installato dello scorer:**

- la fedeltà valutata è `k / max(n_pred, n_conf)`, con `k` che può contare segni corretti
  anche fuori dai geni significativi veri (`cell_eval2/metrics/direction.py`, riga 776);
- la nMAE vede i logFC sui geni DE veri e scarta i bersagli con meno di 10 geni nel gate
  (`cell_eval2/metrics/de.py`, righe 587–699);
- la nMAE calcola medie dei CPM per cellula, mentre MSE/PDS usano composizioni aggregate:
  la differenza dipende dalla covarianza fra profondità e composizione, non dalla sola
  dispersione delle library size (`de.py`, commento del caso #286).

Percorso letto: `C:/Users/ferra/vcc2026-data/.venv/Lib/site-packages/cell_eval2/`.
L'audit della generazione di questa sessione deve quindi riportare separatamente composizione
aggregata e media dei CPM individuali. Far sparire ogni chiamata nulla non certifica un miglior
modello; aumentare la sola media del punteggio non certifica una migliore biologia.

## 4. Tre esperimenti a valore alto, ordinati

### E1 — Ampiezza × generatore sulla forma corrente

**Proposta prioritaria:** quattro bracci sulla cache r9 e sulla forma t25, con stesso cis,
stesse sorgenti e gamma: ampiezza trasferita 1,576 oppure 2,364; generatore Poisson corrente
oppure Gamma-Poisson con dispersione per gene. Tre semi prefissati; confronto appaiato entro
seme. Aggiungere 3,152 solo se il primo confronto lascia la curva aperta. Non scegliere il
valore dall'obiettivo arbitrario di almeno 60 chiamate.

**Ipotesi:** la dispersione riduce le chiamate causate dal generatore e l'ampiezza più alta
recupera chiamate legate agli effetti; il guadagno netto può dipendere dall'interazione.
Falsificazione: se il braccio disperso perde fedeltà/score senza recupero DE al valore alto,
la correzione della distribuzione non basta a rendere competitivo questo candidato.

**Misure:** sei membri, contributi alla media, chiamate e loro segni, profili attesi/realizzati,
energia nello spazio MSE. Il benchmark predice 400 cellule per bersaglio, come l'invio; il
numero di cellule vere resta quello disponibile. Il confronto al nullo è diagnostico, non un
cancello assoluto. Primo braccio di riserva: t25 con ampiezza **2,364**, un solo fattore cambiato.

### E2 — Esclusione e recupero dei membri DE

**Proposta:** t25, esclusione binaria t27 a scala fissa, stessa esclusione con scala che recupera
la quantità di segnale rilevabile; nelle letture separare i geni espressi e poco espressi della
stessa lista. Il braccio t23 storico non basta perché ha anche pesi continui e vecchia cache.

**Ipotesi:** l'esclusione protegge PDS; la riscalatura recupera parte del costo DE. Falsificazione:
PDS non migliora a cache fissa oppure nMAE/reach peggiorano tanto da annullare il recupero.
La quantità di segnale rilevabile è un modo di fissare la scala dai controlli, non una garanzia
di conservare le vere chiamate DE. Non promuovere sulla sola metrica PDS.

### E3 — Compressione delle code, solo se E1 mostra costo nMAE

**Proposta esplorativa:** dopo aver fissato la scala alta di E1, confrontare la sua forma lineare
con una trasformazione dispari saturante dei soli effetti trasferiti, per esempio
`c * tanh(lfc/c)`, cis invariato. Scegliere un solo `c` prima del confronto, da un quantile
dei valori previsti della ricetta di riferimento; dichiarare quel quantile nel protocollo.

**Ipotesi:** aumentare effetti moderati conservando una coda limitata può recuperare chiamate
senza pagare tutto il costo nMAE dei pochi effetti molto grandi. È meno sostenuta di E1/E2:
non c'è ancora risultato locale o ufficiale. Falsificazione: il costo nMAE non si riduce o
PDS/reach perdono più del recupero. Non aprire una ricerca su molti quantili a posteriori.

## 5. Come usare il banco K562 e decidere il candidato

**Misurato dal suo protocollo, non da un mio nuovo run:** il banco K562 vede 7.681 geni su
18.533, ha mediana di tre DE confidenti, nMAE su 32/224 bersagli e genera una mediana di
88 cellule invece di 400. Solo 586 degli 8.602 geni della lista di esclusione senza K562
sono nell'asse. Fonte:
`reports/generatore_e_banchi/banco_k562_pannello_2026-09-29/RISULTATI.md`, §§«Limiti» e «Lettura».

**Interpretazione:** usare lo scorer vero elimina l'errore di formula, non il cambio di dominio.
Le ancore non restituiscono i geni mancanti né la potenza DE perduta. Il banco è utile per
confronti appaiati e per trovare fallimenti grandi; una bocciatura non localizzata non chiude
il filone. Non cambiare il protocollo storico: un banco con 400 cellule è un run nuovo.

**Graduatoria condizionata dei candidati per questa scadenza:**

1. **Ampiezza 2,364 sulla forma t25**, se il confronto a sei membri non mostra un costo netto:
   candidato più semplice, domanda ancora aperta, produzione già disponibile. In assenza
   di trasferibilità del banco, presentarlo come esperimento ufficiale sull'ampiezza, senza
   chiamarlo miglioramento verificato.
2. **Stessa forma con dispersione per gene e ampiezza scelta da E1**, solo se il confronto
   mostra vantaggio netto robusto fra semi: candidato con più possibilità di cambiare
   sostanzialmente la fedeltà, ma rischio concreto sul PDS.
3. **Esclusione binaria con recupero DE**, se E2 preserva il vantaggio PDS e riduce i costi:
   candidato basato sul movimento osservato del t23, con la causalità separata.

La lead può invertire 1 e 2 quando arrivano i dati della generazione. La soglia ±0,005 resta
una soglia operativa del nuovo invio. Un guadagno netto piccolo può ancora meritare un invio
informativo; va dichiarato, non escluso automaticamente. Un fattoriale e un candidato che
combina fattori sono leciti se l'attribuzione resta onesta: «un fattore alla volta» è utile
per capire la causa, non un limite generale alla costruzione del modello.

**Limiti della consegna:** nessuna nuova evidenza dimostra oggi competitività da top100;
le proposte richiedono risultati della prova o un invio ufficiale. Nessuna prescrizione qui
autorizza invii o sovrascrive il lavoro t27 della sessione concorrente.
