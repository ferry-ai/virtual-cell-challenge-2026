# Attenzione sulle sorgenti biologiche: protocollo prospettico

29 settembre 2026, sessione lead. **Proposta e implementazione**, nessun risultato su
dati reali ancora letto. Il proprietario ha chiesto anche una rete biologica nuova per
questa sessione. Questo protocollo riapre esplicitamente tale ricerca; non cambia gli
esiti negativi delle reti precedenti.

## Difetto identificato e ipotesi

**Misurato nel codice:** `reports/modelli/rete_contesti_2026-09-27/pool.py`,
`_profiles` e `batch/_mix`, fondono prima i contesti della famiglia e poi le famiglie.
La rete riceve una media: non può scegliere lo stato CD4 o la sorgente migliore quando
i profili si contraddicono. `net.py` aggiunge anche un residuo libero per gene; la
calibrazione ai minimi quadrati produce una scala molto inferiore a quella degli invii.

**Ipotesi:** conservare i profili dei contesti separati, con maschere e affidabilità,
permette di imparare quando trasferire ciascuna sorgente. Un obiettivo direzionale
può preservare la discriminazione fra perturbazioni, che la sola perdita quadratica
non garantisce. Non si presume che più parametri o l'attenzione diano un vantaggio.

## Modello fissato prima del training reale

- Input dal dataset r2 congelato, mmap: effetti shrunk e SE dello stesso bersaglio,
  tenuti separati per contesto. Non si usa A549 knockout nel training CRISPRi.
- Sette prior del bersaglio già nel dataset: media/deviazione/breadth dell'espressione,
  presenza sull'asse, vicini cis entro 5/20 kb e grado STRING. Non sono annotazioni
  GO/CORUM o un embedding funzionale. Si aggiunge la distanza dei ranghi basali fra
  sorgente e destinazione sui partner STRING del bersaglio, calcolata dai soli controlli;
  profili basali del bersaglio e del gene di risposta, ranghi e differenze fra
  contesto di destinazione e sorgente. I CPM sono richiusi sull'asse disponibile e
  la mancanza di misura resta indicata. Nessun embedding libero di identità.
- In J/T, o senza misura diretta, fallback ai partner STRING visibili, massimo otto
  ordinati per peso. Il gene proprio e il cis di ogni partner vengono esclusi dalla
  sua risposta prima di mediare. Nessun outcome del bersaglio nascosto entra da altre
  sorgenti, centri, normalizzazioni o partner.
- Attenzione non lineare condivisa per (bersaglio, sorgente, gene): due strati nascosti
  di 32 unità, prior proiettati in 16 dimensioni. Logit limitato a ±2; cancelli
  moltiplicativi limitati a [0,75;1,25]. La previsione è metà trasferimento congelato
  più metà miscela appresa. All'inizio coincide esattamente con il trasferimento.
- La baseline pesa l'affidabilità cellulare e conserva massa uguale per famiglia,
  ripartita fra i contesti disponibili. Non è la ricetta t25: è il controllo esatto
  per questi ingressi. La compatibilità con t25 si verifica separatamente prima di
  un eventuale invio. Nessuna ampiezza viene ottimizzata sui test esterni.
- Loss: errore coseno per bersaglio più 0,25 volte cross-entropy contrastiva fra
  perturbazioni dello stesso contesto, temperatura 0,2; penalità 0,01 della deviazione
  relativa dalla baseline. Negativi distinti nello stesso contesto e supporto misurato
  comune a tutto il batch impediscono di vincere riconoscendo le maschere.
  Le righe prive di segnale valutabile sono escluse con
  conteggio esplicito. Batch di 16, 1.024 geni campionati, AdamW lr 0,001, decadimento
  0,0001, clip del gradiente 1; 1.000 passi massimi, valutazione ogni 50, pazienza 5.

## Separazione e confronti

Il primo regime per la candidatura di stasera è **C**, stesso bersaglio in famiglia
nuova. Non viene presentato come J. Per ogni famiglia esterna (K562, CD4, Orion,
iPSC, RPE1), tutte le sue righe sono invisibili. Una seconda famiglia, scelta
deterministicamente fra le restanti, è solo validazione per arresto e scelta dei passi;
si riaddestra poi sulle famiglie visibili per quel numero di passi. Si valuta anche
il passo zero, per poter scegliere veramente la baseline. I controlli del contesto
tenuto fuori sono input consentiti; i suoi effetti perturbativi non lo sono.

I bersagli di test (massimo 512 per contesto, seed 20260929) sono congelati prima del
training. Le famiglie pesano uguale, e all'interno i contesti pesano uguale. Il regime
J è una corsa distinta: l'unione dei bersagli esterni e dei loro vicini cis lascia
ogni sorgente e ogni derivato. In J vale il confronto con lo stesso fallback STRING.

Si addestrano due modelli con lo stesso budget e gli stessi ingressi perturbativi: attenzione
con contesto vero e attenzione cieca (descrittori basali di destinazione sostituiti
dal riferimento medio di training). Si riporta inoltre lo scambio dei basali alla
previsione, il trasferimento fisso, effetto nullo e permutation dei prior fra bersagli.
Le ablazioni alla previsione sono diagnostiche; il modello cieco viene addestrato
separatamente, per non confondere distribuzione degli ingressi e uso del contesto.
Ogni modello sceglie i propri passi sullo stesso split interno; la rete vera non
fornisce il punto di arresto ottimale al controllo cieco.

## Lettura fissata

Primaria di questa fase: discriminazione di rango nello spazio degli effetti,
appaiata per bersaglio; secondarie coseno, nMSE e norma rispetto al trasferimento.
Sono proxy descrittivi, **non punteggi VCC**; il proxy precedente combinato ha fallito
la taratura e non viene riutilizzato come certezza di guadagno ufficiale.

Una direzione neurale è candidata a un banco con scorer vero solo se: guadagno medio
macro-contesto di almeno 0,01 di rango sulla baseline, bootstrap stratificato per
contesto al 95% sopra zero, nessuna famiglia sotto −0,01; il vantaggio sul cieco deve
essere positivo per attribuirlo al contesto. Si riportano tutte le famiglie anche
se una fallisce. Nessun invio segue automaticamente da questo proxy.

La soglia è per la prima corsa preregistrata, seed 0. Una replica seed 1 è richiesta
prima di sostenere robustezza ai semi; l'eventuale banca cellulare indipendente resta
la conferma utile alla gara. Un fallimento non autorizza a scegliere a posteriori
il sottoinsieme di famiglie favorevole. Il manifest precede ogni addestramento e
registra split, codice, protocollo, dati e opzioni.

## Precisazione prospettica su copertura e test

Revisione del lead prima di qualsiasi training reale: la maschera della verità
misurata e la copertura delle fonti sono diverse. Il rango usa i geni misurati in
tutte le verità del contesto, stimabili nelle sole sorgenti di training e fuori dai
cis/own esclusi. Una previsione priva di sorgente è zero, non elimina il gene né il
bersaglio dalla prova. Si riportano per bersaglio il numero di geni con fonte, assenza
totale di fonte, norma nulla e rapporto di norme. Anche la loss usa il supporto
comune delle etichette; le righe senza baseline utile non addestrano, senza svuotare
il supporto genico delle altre. Le annotazioni mancanti non diventano outcome nulli.

Questa distinzione evita che un solo bersaglio senza partner renda invalido tutto
un contesto. Il pannello della gara ha spesso pochi partner STRING: il fallback è
un'ipotesi con copertura misurata, non una soluzione presunta. Gli export conservano
NaN solo fuori dallo spazio modellato e sui geni cis/own; all'interno, l'assenza di
fonte è lo zero effettivamente valutato. Un adattatore alla ricetta di produzione
deve dichiarare il proprio fallback e passare il banco cellulare prima dell'invio.
