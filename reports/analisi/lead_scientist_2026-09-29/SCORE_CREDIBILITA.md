# Credibilità dei punteggi: calcolo, confronto e previsione

29 settembre 2026. Audit indipendente sui file e sul codice, richiesto dal proprietario dopo il dubbio sulla verosimiglianza degli score. **Misurato:** ricostruzione dei nove risultati della conferma generatore e confronto con quattro JSON ufficiali già completi. **Interpretazione:** portata delle misure. Nessun nuovo scoring, training, inferenza, accesso a outcome della riserva Stack, upload o cambiamento di soglie.

**Conclusione:** non emerge un errore aritmetico che annulli il superamento del criterio locale di t28. Emergono invece due limiti sostanziali: la conversione storica mediante cinque ancore aggregate non è esatta; la conferma96 è disgiunta dal dev48 odierno, ma 95 target erano già stati valutati nel progetto. Il numero **+0,028918 è una variazione di un indice locale**, non un guadagno ufficiale previsto né una validazione indipendente di tutto il percorso di ricerca.

## 1. Quali numeri si possono usare

| Numero | Tipo di affermazione sostenuta | Uso non sostenuto |
|---|---|---|
| `score_avg` e sei `score_*` di uno status ufficiale completo | Misura ufficiale di quel preciso invio e pannello; media dei sei pubblicati verificabile | Score di un altro pannello, contesto o modello ancora non inviato |
| Sei `raw` locali, ottenuti con `cell-eval2` e DE del banco | Confronto fra bracci sugli stessi dati, assi, controlli, versione, semi e popolazioni eleggibili | Score VCC; confronto numerico diretto fra pannelli12/48/96/300 |
| Proiezione cinque membri / sei | Indice di selezione congelato, con MSE omessa e pesi storici espliciti | Ricostruzione esatta di sei membri normalizzati del servizio |
| CI del bootstrap target della conferma | Intervallo condizionato a questo pannello, queste cellule/controlli e questi tre semi | Probabilità di migliorare A/B/C o D/E/F, o correzione di tutta la selezione storica |
| PDS/coseno del prescreen neurale sui profili | Misura del compito e trasformazione dichiarati | Sei metriche cellulari; prova che tutte le reti complesse siano inutili |

Il risultato ufficiale t25 **0,14023806091483554** è coerente con la media dei suoi sei membri pubblicati. Il membro FID negativo viene mantenuto, MSE è zero: non si eliminano membri sfavorevoli per alzare la media.

## 2. Errore concreto nella descrizione delle ancore

`reports/gara/anchors_2026-09-17/anchors.json` contiene una soluzione affine ottenuta da due coppie di valori aggregati. La sua etichetta dice «exact algebraic solution» valida per pannello/versione; `reports/gara/README.md` dichiara verifica fuori campione sul terzo invio; `docs/LAVORO.md` §2 dice che i grezzi si convertono con queste ancore. **Queste formulazioni sono troppo forti e smentite dai JSON conservati.** Nessuno di questi file storici è stato modificato in questo audit.

La ricostruzione applica `(raw-baseline)/(replicate-baseline)` ai cinque membri e mantiene il MSE pubblicato, quindi la discrepanza seguente non viene da un MSE inventato:

| Invio | Score pubblicato | Ricostruzione con ancore aggregate | Errore |
|---|---:|---:|---:|
| t01, punto usato nel fit | 0,0459293964 | 0,0459293964 | circa −7e−18 |
| t02, punto usato nel fit | −0,0927743894 | −0,0927743894 | 0 |
| t03, presunta verifica esterna | 0,0196924079 | 0,0204226230 | **+0,0007302151** |
| t25 | 0,1402380609 | 0,1410636230 | **+0,0008255620** |

Per t25, PDS ricostruita **0,6258305003** contro **0,6235621757** pubblicata; NMAE **0,1203714022** contro **0,1179848412**. Tutti i file riportano lo stesso `panel_id` e `anchor_version`. Anche il file `three_points/anchors.json` conserva il valore ricostruito t03, ma non dimostra che sia identico al valore ufficiale.

**Interpretazione matematica:** la gara valuta separatamente i contesti. In generale `media_c[(u_c-b_c)/(r_c-b_c)]` non è determinata dalla sola `media_c[u_c]`: le pendenze possono essere diverse. Due invii identificano una retta fra due punti aggregati, non le ancore specifiche dei contesti. La documentazione primaria descrive la separazione dei contesti e le scale dei membri: [Arc, metriche VCC2026](https://github.com/ArcInstitute/cell-eval2/blob/main/docs/vcc2026_metrics/vcc2026-metrics.md). Senza i componenti per contesto non attribuisco tutta la discrepanza osservata a un singolo meccanismo o versione; la non esattezza è già provata direttamente.

**Conseguenza:** i pesi congelati restano una definizione riproducibile dell'indice locale. Il bias di +0,000826 su t25 non è una correzione da sottrarre ad altri modelli e non misura l'errore della previsione t28. Il lettore t28 appena preparato usa infatti i sei scalati **pubblicati**, senza ricostruirli da queste ancore. Le soglie già registrate non cambiano.

## 3. Conferma generatore: verifica indipendente del calcolo

Sono stati riletti `generator_bench.py` (costruzione, generazione, scoring e bootstrap), `src/vcc2026/bench.py`, `src/vcc2026/de_tools.py`, protocollo ed emendamento alla verità intera, manifest ed effettivi CSV/JSON della conferma. La versione remota registrata è `cell-eval2 0.16.0`; i nove bracci hanno le stesse versioni e il launcher della conferma le confronta con quelle dello sviluppo.

Ricostruzione nuova da CSV tramite `audit_score_credibility.py`, senza importare il banco:

- Tutti i nove CSV hanno esattamente i 96 target congelati, nessuna coppia target/metrica duplicata e nessun infinito. PDS presente e finita per tutti.
- Le cinque medie macro coincidono con i `raw` dello scorer entro **1e−12**; MSE coincide con il rapporto delle somme entro la stessa tolleranza.
- Coorti identiche fra bracci e semi: **PDS96, NMAE70, FID96, REACH87, JAC96**. Un target escluso da NMAE non viene trasformato in zero né escluso anche dagli altri membri.
- Sviluppo48 e conferma96 sono disgiunti nel manifest odierno. I finalisti sono quelli registrati dallo sviluppo completo.
- Bootstrap ricostruito con **frequenze dei target** invece dell'indicizzazione del banco: stessi2000 draw, stesso accoppiamento fra cinque membri e tre semi, denominatori eleggibili ricalcolati in ciascun draw; nessun draw scartato o riempito artificialmente.

| Candidato | Delta indice | Delta nei tre semi | CI97,5% ricostruito | Criterio congelato |
|---|---:|---|---|---|
| ampiezza1,5; dispersione1, t28 | **+0,0289177105** | +0,0342500; +0,0233730; +0,0291301 | **[+0,0195256; +0,0393419]** | superato |
| ampiezza1,5; dispersione0,5 | **+0,0230314140** | +0,0287877; +0,0163292; +0,0239774 | **[+0,0133538; +0,0331835]** | superato |

Per t28 i contributi sono: PDS **−0,0000136**, NMAE **−0,0032740**, FID **+0,0283016**, REACH **+0,0076700**, JAC **−0,0037663**. È plausibile un miglioramento dell'indice guidato dalla precisione/copertura delle chiamate, senza miglioramento sostanziale della discriminazione. Non equivale a migliorare tutti i membri o la biologia in ogni senso.

**Confine storico misurato:** `score_bias_dati_r1/historical_overlap.json` documenta un banco completato il27/09 su299target e11CSV effettivi: **48/48** sviluppo e **95/96** conferma già presenti; solo RPS15 non compare. Ho verificato che il report di overlap riguarda esattamente i96target odierni. Questa evidenza, prodotta dall'audit dati sulle liste senza leggere i valori, non prova quali numeri fossero stati consultati da una persona; prova però che la riserva non era intatta rispetto all'intero progetto. La correzione per due finalisti non corregge questa precedente storia di sperimentazione.

Ulteriori limiti reali: un solo contesto pubblico; pannello e asse diversi dalla gara; tutti i dati disponibili per target ma profondità limitata; gli stessi2000controlli costruiscono il basale, la dispersione e il riferimento dello scorer. Il banco non misura lo scarto fra controlli pubblici per predire e controlli tenuti fuori per valutare. Il bootstrap non ricampiona controlli, cellule vere, famiglie biologiche o contesti; non ricostruisce i ranghi PDS per ciascun nuovo pannello estratto.

## 4. MSE, clipping e valori mancanti

Lo scorer installato (`cell_eval2/run.py:1809`, `1936`) aggrega il membro MSE come **somma dei numeratori / somma dei denominatori** su coppie finite. Non è la media dei rapporti per target. Esempio misurato, riferimento seme1: ratio **1,2143174**, media dei rapporti **1,1085200**; t28 seme1: **1,5959306** contro **1,1842177**. Confonderli cambia la lettura. Il controllo errato iniziale di Stack è stato corretto prima dei suoi score; gli scorer congelati verificano ora l'identità corretta.

MSE peggiora nel generatore: riferimento **1,21421–1,21432**, t28 **1,59480–1,59666**. È un peggioramento misurato della distanza di espressione, non un miglioramento nascosto dalla metrica. Il criterio congelato assegna contributoMSE0 a entrambi: è un'assunzione di saturazione della scala, motivata dalla famiglia di invii, non un'ancora HepG2 stimata. Il banco full-truth rifiuta correttamente una replica della verità contro se stessa; dunque non possiede ancore locali indipendenti per affermare uno score completo.

Il codice ufficiale applica MSE in[0,1], NMAE con limite inferiore−6, e lascia gli altri quattro membri senza queste tosature. MSEgrezzo>1 non significa da solo una soglia universale di score0: la scala usa il proprio basale. Per t25 scoreMSE0 è direttamente pubblicato. Il MSEdi t28 ufficiale resta da misurare e il lettore non lo forza a zero.

**Limite implementativo circoscritto:** `Bench.scale` applica il clampMSE ma non il floorNMAE−6; un suo `scaled_local` estremo non sarebbe la stessa politica ufficiale. Questo percorso **non è usato** dalla conferma full-truth né dalla proiezione congelata; non invalida i numeri qui ricostruiti. Nei nove grezzi NMAE non compare comunque un caso vicino a quel limite. Nessuna modifica retroattiva proposta.

La DE locale usa `fast_scorer_de` fornita al vero scorer: i test di parità del progetto supportano il percorso CPU, ma l'audit di oggi non ha rieseguito la DE completa né provato parità bitwise con il server GPU. Versione e backend restano parte della definizione del risultato. La differenza11ULP nel transfer A/B è un esempio di perché vanno conservati i dettagli numerici; non è evidenza di un cambiamento biologico. Il job085 ricontrolla una sola volta entrambi gli score con un thread e gli stessi input, mantenendo il selettore esatto.

## 5. PDS12, PDS96 e modelli neurali

Il codice installato `metrics/discrimination.py` usa il pannello della **verità** per due operazioni: concorrenti del rango e geni target rimossi dalla distanza. Un pannello12 non cambia soltanto il denominatore11 rispetto a95 o299: cambia anche lo spazio genico escluso. Il profilo è ottenuto da conteggi sommati per gruppo, normalizzati a50000 e trasformati log1p; non dalla media dei logCPM individuali. Un punteggio PDS alto in un pannello piccolo non è una previsione dello stesso valore su300.

La diagnosi post hoc StackA misura una perdita di specificità e un deltaPDS−0,333333 sul suo pilot12: è un confronto appaiato credibile entro quel pilot. Non va confrontata numericamente con il PDS96 del generatore. Stack non ha una prova che HepG2 fosse assente dal pretraining. L'analisi geometrica `STACK_A_POSTHOC.md` dichiara una trasformazione diagnostica diversa da quella dello scorer e non assegna etichette biologiche alla componente comune senza annotazioni.

Il prescreen NN con soglia+0,01PDS verifica una specifica ipotesi di discriminazione. Il fallimento registrato resta tale, ma non dimostra assenza di vantaggio su tutti i sei membri. `NN_PRESCREEN_AUDIT.md` descrive un eventuale esperimento distinto; **l'overlap storico appena misurato restringe la sua proposta**: il solo inventario degli split odierni non basta a trovare nuovi target HepG2 mai valutati. Servirebbe una riserva documentata davvero intatta o un nuovo contesto, senza chiamare indipendente il riuso dei vecchi outcome.

## Evidenza riproducibile e decisione

Codice nuovo `audit_score_credibility.py`; uscita completa `score_credibility_r1/arithmetic.json`, con impronteSHA degli input piccoli. Comando eseguito:

```powershell
.\scripts\py.cmd reports/analisi/lead_scientist_2026-09-29/audit_score_credibility.py --out reports/analisi/lead_scientist_2026-09-29/score_credibility_r1
```

**rc0.** L'avvisoNumPy `Mean of empty slice` riguarda esclusioni real-side già verificate identiche fra semi; iNaN rimangono nelle celle non eleggibili e i denominatori per membro sono ricostruiti esplicitamente. Non è stata scartata una metrica. Le conclusioni aritmetiche sono verificabili anche da `confirmation_analysis/results_r1/analysis.json`, prodotto indipendentemente prima di questo audit.

Non considero questi limiti un errore di file o un bug che renda illegittimo un esperimento ufficiale t28 già registrato. Considero scorretto presentarlo come miglioramento ufficiale già dimostrato o come conferma indipendente dell'intera ricerca. L'invio è un test empirico della trasferibilità, con ricetta, previsione e soglie congelate; il giudizio finale deve leggere lo status ufficiale completo.
