# Stack: sviluppo A/B prima della conferma unica

Congelato il 29 settembre 2026 alle 20:25:56 UTC, tempo letto dall'orologio della
sessione immediatamente prima della redazione. **Protocollo prospettico**: autore
e lead non hanno letto score Stack A o B al momento della decisione. La motivazione
è una diagnostica dei soli input NTC, senza outcome perturbati HepG2.

Questo documento aggiunge una scelta di sviluppo fra due candidati. Conserva
intatti `PROTOCOLLO_STACK.md`, il suo candidato A e i suoi risultati, e
`PROTOCOLLO_STACK_CONFERMA.md` SHA256
`2c2614532d49e35a60735858f150e6bd46f1cb9414ccc8b3914aaf12061245f2`.
Sostituisce soltanto la precedente possibilità di portare automaticamente A
ammissibile alla conferma: prima si completa il confronto A/B e si congela
**un solo candidato**. La riserva di dodici target non serve a scegliere fra A e B.

## Motivazione misurata e ipotesi

In `input_axis_components_r1/analysis.json`, il supporto comune S ha 5.179 geni.
Dei conteggi NTC HepG2, il 41,8556% è fuori dal vocabolario del modello, mentre
l'8,8033% è nel vocabolario ma viene azzerato perché il gene non è misurato
nell'asse K562. Quest'ultima quota è il 15,1404% dei conteggi mappabili al modello
e comprende 1.618 geni. In K562 la perdita aggiuntiva è 2,5827% di tutti i conteggi,
il 5,0240% di quelli mappabili, su 581 geni. Convertire i nomi in maiuscolo non
recupera geni o conteggi in questo bundle e non produce collisioni.

**Ipotesi**: mantenere le misure disponibili in ciascun contesto può aiutare
Stack a condizionare il trasferimento. I conteggi persi non dimostrano una perdita
di accuratezza né che B sia migliore. La modifica cambia anche le library size
viste internamente dal modello; non isola un singolo meccanismo biologico.

## Due candidati e tutto ciò che è fissato

- **A**, originale: ogni input usa soltanto S, intersezione dei geni misurati
  K562, HepG2 e Stack. Helper `stack_pilot.py` SHA256
  `b259371df3d0d515003597c4d9ce5755c25840f0d36fc96d8ac390ffe1275508`.
- **B**, assi propri: ciascun input usa tutti e soli i geni del proprio asse
  misurato presenti nel vocabolario Stack. I prompt e gli NTC K562 mantengono
  5.760 geni; gli NTC HepG2 ne mantengono 6.797. Entrambi rimangono allineati
  all'intero asse ordinato di 15.012 geni Stack. Le altre colonne sono zero.
  Non si fanno imputazioni, conversioni di maiuscole, riscalamenti dei conteggi
  o nuovi filtri. I duplicati conservano la prima colonna, come A.

Per **entrambi**, il supporto della correzione in uscita resta lo stesso S di
5.179 geni. Stessa formula del rapporto perturbato/controllo sintetico normalizzato
su S, pseudoconteggio 1e-6, clipping ±6 log(2), stessa massa transfer q0(S) e
**q0 esatto fuori S**. Il recupero di input non amplia il supporto dell'effetto.
Nessuna modifica di ampiezza, dispersione, prompt o miscela è ammessa.

Stesso checkpoint e lista geni con hash del protocollo A, Arc commit
`cacc2e4b09435c3e536d46237d10b50f222dd144`, eval/no-grad, cinque passi mdm,
prompt ratio 0,25, context ratio 0,4, minimo 0,2, mask rate 1, worker 0,
seed Stack 20260929 e batch registrato. Stesso bundle raw, stessi indici di
cellule sorgente e controlli, stesso sottoinsieme di 512 NTC HepG2 fra i 2.000.
Il controllo sintetico di B viene generato con gli input B e resta in cache per
cardinalità del prompt: non si riusa il controllo sintetico prodotto con input A.
Il numero e il tipo delle chiamate al modello e i seed sono identici.

I target development sono gli stessi dodici del pilot A, nel medesimo ordine:
`CCDC130, NRBP1, MLLT6, WBP11, RPL36A, MBTPS1, RPL41, COG6, EEF2, DCTN1, HAUS8, SETD1A`.
Il manifest `stack_plan_r1.json` ha SHA256
`c5c99faaee2977f5ebe9ed0c297e141684cbf7cf7314eca5f35cea9deb3361d2`.
Il bundle tar originale ha SHA256
`8c693c8457590edca74e626b08d7318a276c44f4b9737f5d4d4c13272814cf3e`.
Nessuna sostituzione di target. Il transfer è lo stesso congelato, con mask observed.

Le cellule finali development seguono esattamente A: 400 per target, Poisson,
library ricampionate dai 2.000 NTC HepG2, `rng_for('output:<target>')` del pilot
inizializzato di nuovo per ogni braccio, cap 12.000 valori e 1.000.000 conteggi.
La baseline transfer deve essere identica fra i due confronti nello stesso
ambiente, altrimenti si identifica la differenza prima di decidere.
Le differenze GPU fra ambienti sono registrate, non trattate come repliche.

## Scoring development e scelta unica

Si usano tutte le cellule vere HepG2 dei dodici target e gli stessi 2.000 NTC,
lo scorer congelato del pilot, i cinque membri per nome, le pendenze delle
ancore ufficiali e il divisore sei. MSE resta separata e aggregata come rapporto
di somme. I controlli di provenienza e asse precedono la lettura della truth.
Il PDS è un rango sul pannello fisso di dodici target, non il coseno medio.
Il bootstrap development è soltanto descrittivo, non entra nella selezione.

Si richiedono risultati completi e validati di **A e B**, medesimi target,
controlli, baseline e pattern di eleggibilità per membro. Valori infiniti,
PDS mancante, provenienza non verificata o confronti incompleti rendono la
selezione non disponibile; un errore tecnico non autorizza a scegliere il
braccio che ha terminato. Le correzioni puramente meccaniche conservano i tentativi.

Per ciascun candidato k si calcolano delta proiezione D_k rispetto al transfer
e variazione PDS grezza P_k. Candidato ammissibile se e solo se **D_k > 0 e P_k >= 0**.

1. Nessuno ammissibile: nessun candidato passa alla conferma.
2. Uno ammissibile: si seleziona quello.
3. Due ammissibili: si seleziona quello con D_k maggiore; **parità numerica esatta
   sui valori float64 non arrotondati: A**. Nessuna tolleranza o ulteriore spareggio.

Si scrive un manifest di selezione con entrambi gli esiti, hash dei report,
input, codice e protocollo, candidato scelto e motivazione, prima di aprire
qualsiasi risultato della riserva. Non si cambia selezione sulla base della
conferma. La scelta fra due sul development non costituisce una prova indipendente.

## Una sola conferma sulla riserva ancora cieca

Riserva invariata: `PCBP1, CDC20, RNF31, KIF11, C7orf26, RPS24, GINS2, YRDC,
DESI1, MRPL38, RSL1D1, MYBBP1A`. Questi target sono distinti dai dodici pilot,
dai 48 development e dai 96 confirmation del banco generatore.

Se è scelto A, resta valido il protocollo originale di conferma con helper A.
Se è scelto B, prima dell'inferenza e dello scoring della riserva si congela
un documento separato che applica le sole differenze di input B qui fissate,
con hash dell'adapter, dello scorer e del manifest di selezione. Non si riscrive
il protocollo A. Nessun risultato della riserva può informare quel documento.

Per il solo scelto: una inferenza Stack seed 20260929; esportazione q0/qStack
float64 esatti prima del sampling; tre semi Poisson finali **1, 2, 3** con la
funzione target_rng del protocollo originale; 400 cellule per target; sei
confronti braccio/seme; primaria cinque pendenze / sei; MSE separata. Conferma
solo se **D >= +0,005**, tutti i tre D_s > 0, limite inferiore IC95% bootstrap
appaiato per target > 0, variazione media PDS >= 0 e tutte le guardie superate.
Bootstrap 2.000 estrazioni seed 20260929, identico fra semi e membri; un'estrazione
senza target eleggibili rende l'intervallo inconclusivo, non viene scartata.

**Nessuna seconda chance sulla stessa riserva**: se il selezionato fallisce o
rimane inconclusivo, non si conferma l'altro né si ritoccano soglie, ampiezze,
supporti o target. I profili e gli outcome dell'altro candidato sulla riserva
non sono richiesti né usati per una nuova selezione. Resta una sola alternativa
valutata sulla riserva, quindi la soglia conferma 95% originale non cambia.

Restano tutti i limiti originari: dodici target, controlli riusati, rumore del
decoder e profili statici fissati, bootstrap condizionale ai ranghi PDS completi,
pretraining HepG2 non escluso. Nessun risultato locale è uno score VCC o una prova
di vantaggio su t25/t28. Nessuna autorizzazione automatica all'invio.

Prima del run B congelare adapter, ambiente e test di parità: A immutato,
allineamento ai propri assi, S in uscita identico, controllo sintetico B coerente,
q0 e fallback fuori S identici, stessi target/prompt/seed/Poisson. I nuovi hash
vanno in un manifest aggiuntivo, senza cambiare questo documento.
