# Che cosa ci insegnano i nostri invii, e quelli degli altri

28 settembre, notte. Su richiesta del proprietario: «continua ad analizzare ed imparare dai nostri invii».

## I nostri 13 invii valutati (misurato; `raccolta.py`, `invii.csv`)

`raccolta.py` raccoglie tutti gli stati e le uscite d'invio salvati in `reports/trial_*/`, una riga per voce valutata
con i sei membri scalati e grezzi. Manca il t16: il suo stato non fu salvato, e CP-0037 ne ricostruisce i membri
dalle ancore; qui non si riempie niente a mano.

**Coppie a un fattore** (`coppie.py`, `coppie.csv`). L'unità di rumore è il t24 contro il t22, cioè il seme del
generatore: D = 0,0016 sulla media, una sola coppia.

| Cambio | Δ media | × rumore | Da dove viene (contributo alla media) |
|---|---|---|---|
| via CD4 (t10 − t08) | −0,0102 | 6,4 | PDS −0,006, reach −0,004 |
| più HCT116 (t11 − t08) | +0,0104 | 6,5 | PDS +0,011 |
| ampiezza × 2 (t15 − t11) | +0,0368 | 23 | PDS +0,013, fedeltà +0,010, nMAE +0,007, reach +0,005 |
| più HEK293T (t17 − t15) | +0,0012 | 0,8 | — |
| più HEK293T (t22 − t20) | +0,0016 | 1,0 | nMAE +0,006, fedeltà −0,003 |
| solo il seme (t24 − t22) | +0,0016 | 1,0 | reach +0,001 |
| generatore `ControlModel` × 2,5 (t14 − t08) | +0,0045 | 2,8 | PDS −0,011, nMAE +0,011, reach +0,014 |

Fuori tabella (CP-0037): t16 − t15, ampiezza × 2 di nuovo, +0,030; t20 − t16 +0,0020.

**Misurato:**
- le fonti, finché l'ampiezza era bassa, valevano circa +0,010 ciascuna, quasi tutto in PDS. L'ampiezza è stata la
  leva più grande: +0,037 e +0,030;
- dal t16 (24/09) in poi nessun cambio si distingue dal rumore del seme: +0,0012, +0,0016, +0,0020 e il seme
  stesso +0,0016;
- nel migliore (t24) PDS porta 0,106 dei 0,143 della media (74 %), reach 0,023, nMAE 0,021, fedeltà −0,009, Jaccard
  0,002, MSE 0.

**Previsioni registrate contro esiti** (i `comparison.json`):
- 8 esiti su 11 dentro la banda registrata;
- t08 sul bordo (+0,0004);
- t15 sopra: il raddoppio d'ampiezza fu sottostimato;
- le bande si sono strette da ±0,05 (t14) a ±0,0045 (t24) e continuano a tenere.

## Gli altri: la classifica pubblica (misurato il 28/09 alle 00:20 circa, solo aggregati)

Letta nel browser dall'API pubblica della classifica, 1.185 squadre, senza salvarla e senza nomi: qui ci sono solo
mediane e conteggi.

| Membro scalato | Noi (t24) | Mediana dei primi 100 | Mediana dei primi 10 |
|---|---|---|---|
| MSE | 0 (grezzo 3,05) | 0,227 (grezzo 0,77) | 0,335 (grezzo 0,67) |
| PDS | 0,636 (grezzo 0,788) | 0,759 (0,842) | 0,805 (0,863) |
| reach | 0,137 | 0,211 | 0,249 |
| fedeltà | −0,054 | 0,001 | 0,051 |
| nMAE | 0,124 | 0,139 | 0,234 |
| Jaccard | 0,014 | 0,003 | 0,018 |
| media | 0,143 (rango 342) | 0,219 | 0,273 |

**Misurato:**
- tutte le prime 100 squadre hanno MSE scalato positivo;
- le prime 25 hanno una mediana di 38 invii (quartili 26 e 53), le prime 100 di 26. Noi siamo a 15;
- solo 2 delle prime 25 descrivono il metodo nella nota pubblica: dalla classifica non si ricavano gli approcci.

**Interpretazione, calcolo approssimato:**
- dalle mediane dei primi 10 e dei primi 100 le ancore dell'MSE risultano circa 0,99 per la risposta media e 0,035
  per la replica. Il nostro 3,05 è quindi circa tre volte la base, ed è tosato a 0;
- contro la mediana dei primi 100 perdiamo circa 0,038 di media sull'MSE, 0,020 su PDS, 0,012 su reach, 0,009 sulla
  fedeltà e 0,003 sull'nMAE; su Jaccard siamo sopra (+0,002).

**Collegamenti con misure nostre:**
- la `mse` ufficiale dei nostri invii segue l'energia prevista, 1 + E/4786, con previsioni quasi ortogonali agli
  effetti veri ([risposta comune, r2](../risposta_comune_2026-09-26/RISULTATI.md));
- nel banco HepG2 con lo scorer vero anche l'ampiezza 0 ha MSE peggiore della risposta media del contesto
  ([banco HepG2](../banco_hepg2_v2_2026-09-26/RISULTATI.md)). Per avere MSE positivo non basta togliere energia:
  serve la risposta comune del contesto con l'ampiezza giusta, più la parte propria del bersaglio.

**Ipotesi, da provare, non verificate:**
1. chi è in testa prevede bene la risposta comune dei contesti di gara e la parte propria con ampiezze giuste;
   noi prendiamo la direzione dalle altre linee e la scala da un moltiplicatore;
2. la spiegazione già scritta nel §0 di PROGETTO: dati pubblici della stessa linea dei contesti. È una decisione del
   proprietario, ammessa solo come esperimento dichiarato e con le identità fuori dalla repo pubblica;
3. il numero di invii: con 26–53 prove sulla validazione si può tarare sullo scorer vero ciò che noi tariamo sui
   proxy.

## Che cosa ne segue (proposta)

- La ricetta a trasferimento medio è satura: altre sorgenti e altre ampiezze non si leggono sopra il rumore. Il
  prossimo guadagno non verrà da lì.
- Il membro con più margine è l'MSE, e dipende dalla risposta comune del contesto. Un esperimento economico: prevedere
  la risposta comune di un contesto dai suoi controlli, sulle linee pubbliche tenute fuori, e misurare sul banco
  HepG2 con lo scorer vero se l'MSE diventa positivo senza perdere i membri DE.
- La rete su molti contesti (F10) va giudicata anche su questo: se non impara ciò che si porta su una linea nuova
  ([rete](../rete_contesti_2026-09-27/RISULTATI.md)), la parte più promettente è quella comune, non l'interazione.
