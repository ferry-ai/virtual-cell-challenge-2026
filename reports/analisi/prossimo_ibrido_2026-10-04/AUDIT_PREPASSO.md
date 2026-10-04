# Prima verifica: che cosa il prepasso esclude davvero

4 ottobre 2026, Codex. **Misurato:** riconto di nove piccoli file già locali e due esecuzioni del prepasso corrente su dati sintetici. Nessun training, scansione del corpus completo o modifica del codice attivo. [Codice](audit_prepass.py), [ricevuta con hash](audit_r1.json).

## 1. Risultato sui tre report QC disponibili

Le ricevute sono dei prepassi H1/HepG2/RPE1 del 3 ottobre sotto `processed/rete_cellulare_2026-10-03/`, relativi al pilot da 365 shard e 5.603.629 cellule. Il trainer D-056 dichiara di mantenere il prepasso v4; qui non è stata ricertificata tutta la catena di hash fra quei prepassi e ogni training successivo.

- Tasso registrato di esclusione delle perturbate uniche: **0,0385002%** in tutti e tre. Il denominatore esclude già duplicati/ripubblicazioni: non è la frazione totale di cellule che non contribuisce al training.
- Esclusioni per controlli mancanti o insufficienti: **una cellula**, chiave `hipsci_targeted_19|MISSING`, `no_controls_in_key`. Nessuna riga `too_few_controls_in_key` in questi tre report.
- Nessuna perdita registrata come `genes_in_some_shard_only` nell'intersezione delle maschere per chiave. Questo non misura geni fuori asse, mapping errati a monte o informazione persa nella selezione degli ingressi.
- **2.048 geni d'ingresso**, selezionati per abbondanza media dei controlli nei contesti ammessi dal fold; gli altri geni di risposta non sono per questo tutti eliminati dalla loss.
- **38.176 cellule H1 marcate duplicate**: la ricevuta documenta il conteggio, non una nuova verifica della loro identità biologica. **8 cellule riammesse** dalla guardia che protegge fenotipi perturbazionali.

Lo split H1 riporta inoltre 526.789 cellule ammesse ma `unlabelled` e 32.758 `combined:train`. Il codice estrae soltanto la classe letterale `train` (`DRAWN = "train"`): quelle classi non costituiscono supervisione del training attuale. Non è corretto sommare tutte le cellule ammesse come cellule addestrate. Senza etichetta non significa controllo; le combinazioni richiedono una rappresentazione esplicita distinta dal bersaglio singolo.

**Conclusione limitata:** questi report non sostengono l'ipotesi di una perdita massiva di contesti del pilot dovuta alla soglia dei controlli. Non descrivono le sorgenti rimaste fuori dal manifest, né certificano il corpus ampliato. Le esclusioni per validazione restano corrette e separate dalle perdite di informazione.

## 2. Regola di esclusione completa riprodotta

Eseguito il prepasso attuale senza modificarlo su due corpus piccoli. Profili identici e sopra i filtri di qualità; una linea esclusa fissa con 40 controlli soddisfa il contratto. Nel contesto di training varia soltanto il numero di controlli; ci sono sempre 20 cellule perturbate G1.

| Controlli nel contesto di training | Perturbate | Cellule di training ammesse | Motivo |
|---:|---:|---:|---|
| 29 | 20 | **0** | tutte le 49 escluse: `too_few_controls_in_key` |
| 30 | 20 | **50** | nessuna esclusione |

Entrambe le esecuzioni terminano con codice 0. Le asserzioni verificano il contenuto dei risultati, non solo l'uscita del processo. Il caso dimostra una discontinuità della policy e la necessità di un controllo di copertura; **non dimostra che 29 controlli reali siano sufficienti né che questa regola abbia causato il t30**.

Riproduzione, usando un nome di output nuovo:

```powershell
.\scripts\py.cmd reports/analisi/prossimo_ibrido_2026-10-04/audit_prepass.py --data-root C:/Users/ferra/vcc2026-data --out reports/analisi/prossimo_ibrido_2026-10-04/audit_r2.json
```

## 3. Modifiche da progettare prima del corpus ampliato

- **Bilancio indipendente dal loader:** confronto con il catalogo atteso, per linea e sottocontesto. Distinguere assente, non riconosciuto, bocciato QC, escluso per validazione, senza etichetta, combinazione, aggregati soltanto, ammesso, campionato e realmente usato. Una sorgente assente non compare nel qc.json e non può essere certificata da esso.
- **Controlli insufficienti:** verificare mapping e partizioni; policy esplicita di basso supporto o abbinamento biologicamente giustificato nello stesso esperimento. Non cancellare il contesto dal catalogo, non equiparare una lacuna tecnica a inutilità scientifica. Nessun prestito indiscriminato di controlli.
- **Identità e strati:** conservare donor/stimolo/libreria/guida e modalità; nessuna deduplica basata soltanto su conteggi uguali fra cellule diverse. Verificare collisioni e repliche con esempi reali.
- **Filtri e ingressi:** misurare selettività del QC, maschere, copertura dei target e stati rari del pool. La selezione dei 2.048 geni è una ipotesi da ablation, non una costante scientifica.
- **Non usare risposte escluse per decidere il fit:** fixture che muta queste risposte lasciando invariati campioni, feature e statistiche di training; consentire solo i cambiamenti delle uscite di valutazione. Le cache globali devono rispettare questo vincolo.

Il primo intervento proposto è rendere visibile e bloccante la scomparsa non giustificata dei contesti. Cambiare una soglia senza ricostruire i casi sarebbe un altro intervento arbitrario. La divisione per sorgente deve preservare prima il comportamento, poi la nuova policy va valutata come modifica separata.

## 4. Un collo di bottiglia da misurare prima di distribuire il lavoro

Il passaggio di Claude1 delle 12:30 richiama la durata della fase centrale. Ricontrollato il log originale HepG2: ultima ricevuta della prima lettura a **2.217 s**, prima ricevuta della seconda a **8.894 s**, ultima a **10.318,1 s**, fine a **10.340,3 s**. Fra le due letture ci sono quindi **6.677 s**. [Codice](audit_timing.py), [ricevuta](timing_audit_r1.json).

È un intervallo di log, non un profiler: comprende i passaggi globali **e l'attesa del primo risultato della seconda lettura**. Non consente di attribuire tutti i 6.677 s a una sola funzione. Basta però a rendere ingiustificata la semplice divisione “tempo totale / shard” come misura del costo per shard.

Prima di scegliere fra prepasso unico ottimizzato e distribuito, strumentare deduplica, QC, classi, gruppi di valutazione, quote, serializzazione e avvio dei worker. Dividere solo le letture può lasciare intatto un costo globale dominante. L'indicizzazione globale e le regole di ammissione devono comunque rimanere coerenti, anche se il calcolo viene partizionato.
