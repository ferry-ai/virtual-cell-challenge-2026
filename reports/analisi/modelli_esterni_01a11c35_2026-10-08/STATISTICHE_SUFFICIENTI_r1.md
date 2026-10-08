# Riduzione esatta per target — contratto e fixture

**Implementato e verificato su fixture.** Richiesta DATI-TRANSFER: confermare
riduzione e parità prima del fit sulla release di produzione. Nessun array
biologico letto, asset acquisito, fit reale o job cloud avviato. I componenti
precedenti dei commit `10a2849` e `39748f0` restano invariati.

Verifica del risultato letta alle **21:16:55 Europe/Rome dell'8 ottobre 2026**.
La release ricevuta dichiara 203.975 righe, 18.533 geni, 47 contesti CRISPRi e
18.562 simboli target distinti. Gli SHA dei suoi manifest view/input/split sono
stati verificati; i 1.712 chunk biologici non sono stati letti e hanno ancora path
da risolvere. È produzione, non C/J e non corpus D-053 completo.

Riferimento fissato: `reports/modelli/dati_transfer_2026-10-08_01a11c34/training_release_production_r1.json`;
SHA256 della view esterna: `ce8c1ff7b008a4554daa5dbf7a5baaf5e11e515eaebefb511924e5d328018683`.

## Quale equivalenza preserva

Per un gene di risposta g, il modello precedente minimizza:

`L_g = sum_i(w_i m_ig (y_ig - a_g - z_t(i) beta_g)^2) / W_g + alpha ||beta_g||²`

con `W_g = sum_i(w_i m_ig)`. Ogni riga i conserva il peso positivo w_i del
proprietario, la maschera m_ig e l'effetto nativo già stimato y_ig. La feature
standardizzata z_t è **identica per tutte le righe dello stesso target**.

Sono sufficienti per i coefficienti:

- `Q_tg = sum_{i: t(i)=t}(w_i m_ig)`, peso osservato del target per quel gene;
- `S_tg = sum_{i: t(i)=t}(w_i m_ig y_ig)`, somma pesata delle risposte osservate.

Espandendo il quadrato, i termini che dipendono dai parametri diventano
`sum_t[Q_tg f_tg² - 2 S_tg f_tg] / W_g`, con `f_tg = a_g + z_t beta_g`.
Il termine restante è costante rispetto ai parametri. La penalità, l'intercetta
e il minimo quindi restano gli stessi. La media del generico è `sum_t S_tg / W_g`.
Q nullo non produce uno zero osservato: il gene non supportato conserva maschera
falsa. Non serve la somma dei quadrati delle risposte per i coefficienti; servirebbe
invece per ricostruire il valore completo della loss, varianze o altre statistiche
non restituite da questo componente.

La centratura/scalatura delle feature resta quella delle **righe originali**:
usa il peso totale `sum_{i:t(i)=t} w_i` per ogni feature target. Non assegna uguale
peso ai target distinti e non riequilibra automaticamente studi, donatori o cloni.
I contesti e i pesi restano responsabilità di DATI-TRANSFER.

**Questa è un'identità della loss dopo l'ammissione delle righe.** Non è il pooling
biologico dei conteggi richiesto da T2, non crea nuove sorgenti, non ricalcola lo
shrinkage, non applica ampiezza/cis e non permette di ricostruire la banca da medie.
Non è applicabile se lo stesso target ha feature diverse per contesto, se cambia
la loss o se si introducono pesi per gene non rappresentati dal contratto corrente.

## File e interfaccia

- `target_sufficient_ridge.py`: `TargetSufficientRidge.fit` riceve feature U×D,
  nomi unici dei target e mappa intera riga→target, risposte/maschere indicizzabili
  R×G, metadati delle R righe e pesi. La mappa viene controllata contro i simboli;
  feature non consumate, righe escluse e valori osservati non finiti sono rifiutati.
- `run_sufficient_probe.py`: stesso manifest del runner streaming, stessi
  controlli di hash/assi/identità/modalità/regime/release/split e query senza verità.
  Carica le feature una volta per target distinto; default `gene_block=64`,
  `row_block=128`, `factor_cache=2`. Il primo probe resta **alpha=1.0** fissato.
- `test_target_sufficient.py`: fixture con target ripetuti in tre studi, pesi
  non uniformi, maschere diverse, gene privo di supporto e gene con una sola riga.
- `sufficient_tests_r1.txt`: quattro test passati in **1,126 s**; differenza massima
  nelle predizioni della fixture rispetto al denso **9,992007221626409e-16**.

```powershell
.\scripts\py.cmd reports/analisi/modelli_esterni_01a11c35_2026-10-08/run_sufficient_probe.py --manifest <fit_manifest.json> --out <nuovo_output_fuori_repo>
```

I file `native_predictions.npz`, `ridge.npz` e `manifest.json` conservano il
contratto precedente; la ricevuta aggiunge numero di target distinti, blocchi
letti, pesi/contesti/righe osservati e dichiarazione che le feature non sono state
espanse R×D. Le predizioni restano native e `not_scored`; nessuna ammissione al
generatore è implicita. Una valutazione comparativa pendente non impedisce un fit
di sviluppo tecnicamente ammesso e autorizzato dal proprietario.

## Cosa dimostrano i test

Parità dei coefficienti, intercette, generico, normalizzazione e predizioni con
il fit denso, più confronto con least squares aumentati indipendenti sulle righe
originali. Il confronto include un caso dove la riduzione cambia il ramo di
soluzione da primale a duale. Tolleranza fissata nel test: rtol 1e-10, atol 1e-11.

Cambiare ordine delle righe o dimensione dei blocchi non cambia il risultato
oltre la tolleranza. Cambiare valori mascherati non influenza il fit; cambiare una
risposta osservata o sostituire i pesi con pesi uniformi invece cambia i coefficienti
(controlli positivi). Un reader solleva errore se si tenta di convertire l'intera
matrice o superare i limiti di righe/colonne: la fixture passa. Roundtrip da chunk
NPZ a store mmap e runner confrontato contro il runner denso. Queste prove non
dimostrano accuratezza biologica o identità bit per bit sul corpus reale.

## Memoria e condizioni prima del fit reale

Per U=18.562 e D=1.280, una matrice feature float64 occupa **190.074.880 byte**,
contro **2.088.704.000 byte** per R=203.975 righe: circa undici volte meno.
I due sufficienti U×64 float64 occupano **19.007.488 byte** complessivi;
un blocco di risposte 128×64 float64 occupa **65.536 byte**. Restano coefficienti,
temporanei su U×D, fattorizzazioni, query, metadati, librerie e pagine mmap.
Sono dimensioni calcolate, non un picco RAM misurato né una promessa di runtime.

Il consumo di disco dello store precedente resta **18.901.343.375 byte**.
Questa modifica non elimina `observed.npy`. Una futura maschera da finitezza può
risparmiare 3.780.268.675 byte soltanto verificando equivalenza esatta con le maschere
originali per ogni chunk; qui non è stata implementata. Serve quindi preflight
di disco/RAM effettivi e risoluzione dei mount privati nel corretto account.

Resta la richiesta pendente al proprietario per asset ESM2/PIE e compute di questa
sessione. I consensi dati alla campagna DATI-TRANSFER non vengono estesi al fit.
Le esclusioni di fold precedono statistiche, generici e shrinkage upstream; questa
riduzione non sana leakage già presente. **Verdetto: approfondire**, invariato.

## Ricevute finali

- `combined_tests_r3.txt`: **21 test del componente passati** in 9,305 s.
- `docs_check_r5.txt`: controllo documentale passato, 67 checkpoint e 11 strade;
  controlla struttura e riferimenti, non verità scientifica.
- `repo_tests_r3.txt`: 290 test generali in 541,980 s; persistono tre errori per
  `cell_eval2.config` mancante nel runtime locale. Gli indici/cartelle passano.
  Nessuna dipendenza condivisa installata o modificata da questa sessione.
