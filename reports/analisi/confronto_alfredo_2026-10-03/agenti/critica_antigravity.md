# Revisione integrale — antigravity

Run: 20261003-142026-alfredo-critique. Modalità: read. Modello: default della CLI, non fissato né verificato nei metadati dell’hub. Brief: ../brief_antigravity.md. Il testo sotto è il rapporto originale integrale; la verifica del coordinatore è in ../AGENTI.md.

---

Le diagnosi tecniche e scientifiche del teammate contengono estrapolazioni non supportate dall'evidenza locale, e la sua "Strada C" confonde l'identità biologica di linea con gli effetti tecnici di studio, rendendo necessari due pacchetti di lavoro sulle baseline e sui confondenti.

Ho usato il tool `view_file` per leggere `CLAUDE.md`, `docs/PROGETTO.md`, `reports/modelli/rete_cellulare_2026-10-03/PROTOCOLLO.md`, `esito/decision_r3/decision.json`, i report P3 e P4 in `generalizzazione_contesti_2026-10-02`, `INGESTIONE.md` e `GENERALIZZAZIONE.md`.

**Diagnosi della miscela e salvaguardie:**
*   Il fallimento della miscela non è risolvibile con un pavimento per `pi` a 0.05. **Misurato**: in H1 r1 (`PROTOCOLLO.md` §7, righe 128-131), `pi` si è fermato al pavimento di 0.01 ma il gradiente è andato perso perché la responsabilità è andata a zero.
*   **Misurato**: nello smoke test 2.1 con `pi` fisso a 0.5 (`PROTOCOLLO.md` §9, righe 178-182), la responsabilità crolla a zero perché lo spostamento prodotto diventa peggiore della baseline, azzerando l'apprendimento utile.
*   **Inferred**: La rimozione totale della miscela in r3 (`pi=1`) è l'unica salvaguardia adeguata perché costringe la componente di risposta a ricevere il gradiente pieno indipendentemente dalla baseline.
*   Il presunto incremento dei gradienti di 50.000 volte tramite il pavimento è **unverified**.

**Critica di Strada C:**
*   **Inferred**: Valutare "stesso tipo" contro "stessa linea" sarà gravemente ambiguo. **Misurato**: gli effetti di studio/laboratorio introducono confondenti massicci (coseno mediano 0.02-0.03 fra linee diverse, ma solo 0.07 fra linee dello stesso lab e 0.16 fra esperimenti della stessa linea; `PROGETTO.md` §3, righe 128-131). Strada C non ha un meccanismo per separare l'identità della linea dal batch tecnico.
*   **Inferred**: La regola `mean >= 0` basata sul rapporto di somme MSE per KOLF è fragile; il rapporto di somme non garantisce robustezza campionaria e maschera la varianza. Non equivale al rigido limite di confidenza inferiore imposto su H1.

**Sulle metriche e le leaderboard:**
*   La relazione empirica grezza `MSE = 1 + E/4786` è **measured** (`PROGETTO.md` §3, righe 105-106).
*   **Inferred**: Deriva dall'errore quadratico ordinario ($\lVert y - \hat{y} \rVert^2 = \lVert y \rVert^2 + \lVert \hat{y} \rVert^2 - 2y\cdot\hat{y}$); se le previsioni sono quasi ortogonali alla verità, il termine incrociato svanisce e la MSE scala linearmente con l'energia della predizione.
*   Che un coseno aggregato di 0.12 sia necessario per una MSE positiva o che la leaderboard sia affetta da un "exploit di layout" sono speculazioni **unverified**. L'equivalenza degli output di scorer su `cell_eval2` 0.16/0.18 è anch'essa **unverified**.
*   L'ipotesi che i contesti D/E/F finali siano stem-like è **unverified**.

**Pacchetti di lavoro (Work Packages) raccomandati per Alfredo:**
1.  **Isolamento biologia vs studio:** Misurare il transfer incrociato *cross-studio sulla stessa linea* (es. K562 Replogle vs VIPerturb) contro il transfer *cross-linea nello stesso studio*, per pesare l'impatto della chimica rispetto all'identità cellulare. Nessun nuovo dato richiesto. **Decisione di fallback:** se il gap tecnico domina, abbandonare l'inferenza del contesto dai controlli e usare solo la baseline transfer.
2.  **Baseline ufficiali sui bersagli di Strada C:** Valutare la baseline semplice `m2_0` (calibrazione senza contesto) e il transfer standard su Jurkat, KOLF e H1 usando lo scorer ufficiale a sei membri completo, estendendo il lavoro fatto su HepG2 (`p3_six_member_r2/LETTURA.md`, dove il transfer resta vincente). **Decisione di fallback:** se nessuna baseline adattativa batte il transfer, fermare i tentativi di adattamento contestuale per queste linee.

**Non eseguito e domande aperte per Claude1:**
*   Non ho eseguito comandi di scrittura, alterato file o avviato kernel, lavorando in stretto read-only.
*   Non ho verificato l'implementazione del codice di Alfredo poiché risiede su macchine esterne non accessibili.
*   *Domanda aperta per Claude1:* Per Strada C, in che modo il verdetto per "same exact line" deve guidare l'adozione in modo diverso rispetto al successo su "same broad cell type" (come iPSC/KOLF), considerata l'ambiguità ammessa?
*   *Domanda aperta per Claude1:* Vogliamo tollerare l'asimmetria delle regole di espansione (la debole media `>= 0` su KOLF contro l'intervallo di confidenza `> 0` su H1), o allineare tutte le valutazioni allo standard di incertezza di H1?
