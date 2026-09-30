# Diagnostica additiva della rete, prima della lettura degli esiti

29 settembre 2026, preparazione alle 18:56 UTC. **Proposta e implementazione**.
L'autore non ha letto punteggi reali della rete né risultati parziali della conferma
del generatore. La revisione Grok è `C:/Users/ferra/agent-hub/runs/20260929-202639-vcc-lead-neural-review/grok/result.md`.
Il training, i checkpoint, il lettore e le soglie congelate restano identici.
Questa analisi è una sensibilità aggiuntiva: non modifica un fallimento in successo
e non autorizza un invio. Si conserva accanto al verdetto registrato.

## Riscontri e limiti di interpretazione

**Misurato nel codice:** `neural_sources.py`, `_profile`, riduce a 0,1 il valore
del fallback STRING e a 0,01 la sua varianza; la successiva affidabilità non riceve
il fattore 0,1. La baseline può quindi attribuire massa a token attenuati. Questo
non invalida il confronto appaiato, ma un guadagno può derivare dalla loro
soppressione. Non basta dire che il fallback riduce la norma: il rango coseno è
invariante alla scala di un intero vettore. È rilevante se cambia la direzione,
per disponibilità e contenuto diversi fra sorgenti/geni.

**Diagnostica proposta, non ancora implementata:** con ogni checkpoint esterno,
ricostruire una baseline `direct_only`, azzerando la reliability dei token con
`features[...,17]` vero; rinormalizzare la massa di famiglia con la medesima regola
del batch originale dopo tale esclusione. Il bersaglio senza alcuna sorgente
diretta resta zero nel rango. Non cambiare modello o feature della rete. Riportare
net meno direct_only, transfer meno direct_only, frazione di peso fallback per
bersaglio e famiglia, copertura e norma. Occorre un forward remoto con SourceView;
gli export attuali non contengono i token. Nessuna ricerca del coefficiente 0,1
sul test, né promozione della variante diagnostica senza una prova propria.

**Misurato:** `fixed_rows` esclude i 300 bersagli `in_panel` dal test e dalla
validazione interna; il refit C può usarli nelle sorgenti consentite. Il proxy dei
cinque fold è dunque **fuori pannello**, come già dichiarato in ADATTATORE_T25.md.
Questo è regime C, non un risultato su nuovi bersagli J.

**Misurato:** il lettore originale ricampiona PDS per bersaglio già calcolati su
tutti i concorrenti, indipendentemente entro ciascun contesto. Non preserva la
dipendenza di uno stesso bersaglio presente in più contesti e famiglie. **Ipotesi:**
può sottostimare l'incertezza; la direzione e l'entità della differenza fra CI non
sono note prima del calcolo. Non si presume che il nuovo CI sia necessariamente
più ampio. Le famiglie osservate restano cinque: nessuno dei due bootstrap stima
un universo arbitrario di futuri tipi cellulari.

## Bootstrap fissato qui

`cluster_pds.py` richiede tutti i cinque fold completi e passa prima
`verify_neural_runs.verify`. Controlla gli hash dei quattro file congelati, dati
piccoli e dimensioni registrate dei grandi array. Come nel run originale, questi
ultimi non sono nuovamente hashati integralmente: il limite resta esplicito.

Per ogni contesto legge solo `net`, `transfer`, `blind` da `pred_<contesto>.npz`
e le righe r2 di verità designate dal manifest. Ricostruisce esattamente la
centratura float32 dei raw e il supporto comune di verità/SE/asse modellato,
incluse le esclusioni own/cis. La maschera dell'export deve coincidere nei tre
bracci; assi e ordine dei target devono coincidere col dataset e col manifest.
Tutti i PDS per bersaglio e `common_genes` devono riprodurre i CSV originali
(tolleranza assoluta 1e-12); in caso contrario si interrompe prima di scrivere.

Si campionano 2.000 volte, seed 20260929, tanti bersagli quanti sono i **nomi unici
nell'unione** dei test. Lo stesso conteggio multinomiale di un bersaglio si usa in
ogni contesto e famiglia in cui esso compare. La cardinalità ricampionata di un
contesto può variare; con meno di due copie il programma rifiuta la diagnostica.
Le famiglie e poi i loro contesti mantengono peso uguale, come nella primaria.

In ciascun draw si ricalcola il PDS sulla matrice cosinica ristretta e ripetuta
secondo i conteggi. Le copie dello stesso bersaglio sono concorrenti a pari merito;
solo il proprio elemento viene tolto. L'algebra usa `wᵀ(L_ref−L_net)w / N(N−1)`
e coincide con l'espansione esplicita della matrice, verificata con un test.
Il calcolo mantiene fissi predizioni, supporto genico e centro della verità del
pannello originale. Non è un bootstrap dell'intera procedura di training o della
stima del centro.

Si riportano **entrambi** net−transfer e net−blind: punto macro, CI percentile 95
del PDS ricostruito e, per separare le due dipendenze, CI con gli stessi cluster
ma ranghi originali fissi. Si registrano sovrapposizioni dei bersagli fra contesti,
hash degli NPZ e tutti i draw. Nessun nuovo flag di promozione è prodotto.

## Esecuzione e verifiche

**Misurato:** cinque test sintetici passano (0,402 s): equivalenza alla matrice
espansa con duplicati, effetto nullo a PDS 0,5, conteggi condivisi fra contesti,
rifiuto dei campioni invalidi, ricostruzione da NPZ sintetico con nome `NA` e
maschere verificate. Nessun effetto reale o risultato è stato letto.

```text
python reports/analisi/lead_scientist_2026-09-29/neural_external_validation/cluster_pds.py --runs FOLD_K562 FOLD_CD4 FOLD_ORION FOLD_IPSC FOLD_RPE1 --data DATASET_R2 --out NUOVA_DIAGNOSTICA
```

Il runner deve avere i cinque `pred_*.npz` per le rispettive famiglie (12 contesti
complessivi), non soltanto i report piccoli. Non serve caricare i checkpoint.
Una matrice di confronto 512×512 float64 pesa 2 MiB; tre per 12 contesti circa 72
MiB. Un export di un braccio 512×18533 float32 pesa circa 36,2 MiB non compresso.
Le moltiplicazioni bootstrap costano O(2000×somma N_contesto²) per contrasto;
qui non viene fornita una promessa di tempo o di picco RAM. Eseguire sul runner.
