## Obiettivo

Preparare e provare localmente una prima variante ispirata alle note 5–6: trasferimento degli stessi bersagli, affidabilità n/(n+100), sottrazione del 75% della risposta comune e confronto fra media CPM e profilo aggregato. Consegnare codice eseguito e candidati congelati; distinguere prova funzionale ed efficacia biologica. Massimo 90 minuti.

## Contesto

Il proprietario ha scritto: «Io direi di provare le strategie nelle note». Le note 5–6 descrivono K562 x3, HCT116 x1, HEK293T x1, H1 2025 x2, pesi B/C 2:2:1:2, CD4 0,5, affidabilità n/(n+100), sottrazione comune 0,75, ampiezze CPM 1,2 e pseudobulk 0,375. Non possediamo il codice originale: questa è una variante ispirata, non una replica esatta. La nota non specifica tutti i pesi di A né l'algoritmo dei due momenti.

Main a0ab5fb contiene pipeline e dati di riferimento. Trial-01 è il migliore ufficiale (+0,045929), t03 +0,019692, t07 −0,016004. Le suite locali hanno un errore preesistente: cell_eval2.config non importabile. Non usare un altro scorer silenziosamente. I nuovi documenti non committati del lead potrebbero non essere nel worktree: questo foglio è autosufficiente.

## Passi

1. Verificare manifest locali e file piccoli disponibili. Elencare quali sorgenti della nota esistono realmente e quali mancano, con copertura per bersaglio/gene e identità dello studio. Leggere i grezzi solo a blocchi entro il budget; nessuna acquisizione di atlanti in questa sessione. Non contare mirror come sorgenti indipendenti.
2. Implementare `src/vcc2026/atlas_transfer.py`, funzione `mix_effects(effects, observed, n_cells, source_weights, common, gamma=0.75, reliability_scale=100.0)` -> dizionario con `effects`, `observed`, `weight_sum`. Array: effects e observed S×T×G, n_cells S×T, source_weights S, common S×G. Unità degli effetti lnFC. Peso w_st = source_weights_s*n_st/(n_st+reliability_scale); normalizzare su sorgenti osservate per ogni coppia t,g. Risposta = media pesata di effects_stg − gamma*common_sg. Dove nessuna sorgente è disponibile restituire valore 0 e maschera falsa. Non usare il valore 0 per rappresentare evidenza di assenza. Rifiutare pesi/cellule negativi, non finiti, scale non positive e forme errate. Le celle non osservate possono contenere NaN e non devono contaminare il risultato. La componente comune arriva dall'esterno: stimarla solo su bersagli di sviluppo elencati nel manifest, senza etichette del contesto di test.
3. Nello stesso modulo implementare `count_moments(counts)` per conteggi interi non negativi, densi o CSR. Restituire `mean_fraction`, `pooled_fraction`, `zero_fraction`, `n_cells`. Escludere cellule a profondità zero dalla media delle frazioni, contandole nel rapporto; se tutte sono vuote, rifiutare. Queste quantità descrivono la realizzazione, non garantiscono la calibrazione.
4. Aggiungere il prossimo script numerato libero per produrre effetti nel formato NPZ accettato dai banchi (`targets`, `genes`, `lfc`), maschere e manifest separati. Congelare due candidati sul medesimo input: gamma 0 e 0,75; affidabilità 100, stessi pesi e supporto. Usare sorgenti verificate disponibili; con sola K562 chiamare il risultato ablation a singola sorgente, non trasferimento multisorgente completo. Per la prova con più sorgenti usare pesi espliciti registrati, mai inventare che siano quelli mancanti della nota. Tenere distinti affidabilità e shrinkage EB già applicato.
5. Eseguire un pilot reale piccolo (massimo 8 bersagli, 300 controlli di adattamento e 400 cellule generate per bersaglio), se i dati locali bastano, confrontando stessa sorgente e stesso generatore senza/con centratura. Riportare scarto fra i momenti desiderati e realizzati, zeri e profondità. Fissare target e semi prima della lettura dei risultati, salvare hash e selezione. Verificare input/output sui conteggi finali. Non proclamare effetto nullo sui geni senza firma se la normalizzazione li muove.
6. Se lo scorer fissato è utilizzabile senza alterare l'ambiente condiviso, riportare i sei membri grezzi. Altrimenti registrare il blocco e completare effetti, momenti e pilot senza un punteggio sostitutivo. Separare effetti di centratura da correzione del generatore: questa sessione misura la discrepanza dei due momenti, non implementa un ottimizzatore non specificato dalla nota. Documentare cosa serve per la prova successiva della generazione a due vincoli.

## Regola di accettazione

Collaudo superato; maschere e pesi corretti; output deterministico a input fissati; almeno una esecuzione su dati reali documentata, oppure impedimento preciso con file mancanti. Il successo funzionale non promuove un modello. Un risultato biologico richiede confronti successivi su dati separati da selezione e taratura. Il pilot non sceglie ampiezze né soglie e non sostituisce il riferimento trial-01. Non assegnare un voto ufficiale mediante il rapporto del t03.

## Vincoli

Lavorare su main tramite il worktree del ciclo, conservando tutti i riferimenti. Solo dati già accessibili in lettura; niente GPU o modifiche all'ambiente Python condiviso. Budget RAM addizionale 1 GiB, elaborazione a blocchi. Nuove uscite in destinazioni univoche, mai sui report esistenti. Semi 2026 e 2027. Ogni scelta non determinata dalle note va etichettata come nostra ipotesi. Le note 1–4 non vanno presentate come riprodotte: mancano definizioni operative per B32/PRE/JOINT/consA.

## Consegna

Modulo, script numerato, test; manifest e tabella del pilot in una nuova destinazione consentita; `04_esito_claude.md` con sorgenti disponibili/mancanti, comandi effettivamente eseguiti, controlli passati/falliti, risultati e limiti, righe proposte per registro e lista precisa degli input necessari alla fase multisorgente completa. Nessuna promessa sul punteggio.
