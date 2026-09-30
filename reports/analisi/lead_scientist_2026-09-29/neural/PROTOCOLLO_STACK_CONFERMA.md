# Stack: conferma prospettica su dodici bersagli distinti

29 settembre 2026. **Protocollo congelato prima di leggere risultati di scoring
del pilot Stack e prima dell'inferenza di questa conferma.** La selezione dei
bersagli era già congelata con soli metadati in `expansion_metadata_r1.json` e
`PROPOSTA_STACK_ESTENSIONE.md`. Questo documento rende definitiva la proposta di
lettura di quella scheda; non modifica il pilot `PROTOCOLLO_STACK.md`.

Stato al momento della redazione: nessuno score Stack letto dall'autore; il pilot
ha incontrato un errore di serializzazione H5AD dopo l'inferenza. Un errore di
formato non costituisce evidenza a favore o contro il modello. Le eventuali
correzioni meccaniche hanno una provenienza separata, senza cambiare questo
protocollo. Il runtime della conferma deve essere verificato e congelato prima
di leggere gli outcome di questa conferma.

## Domanda, candidato e unità indipendente

Una sola alternativa: la previsione **ibrida Stack/transfer** fissata nel pilot,
con effetto stimato una volta dal modello, contro il transfer congelato. Non si
ottimizzano ampiezza, dispersione, prompt, pseudoconteggio, supporto o miscela su
questi dodici bersagli. Il regime è C, stesso bersaglio disponibile in K562 e
destinazione HepG2. Non si dichiara HepG2 esclusa dal pretraining Stack.

I bersagli sono distinti da tutti i 48 development e 96 confirmation del banco
generatore e dai dodici del pilot. I controlli sono riutilizzati esattamente:
**indipendenza dei bersagli non significa indipendenza del controllo, del
contesto, del pretraining o del modello**. La variabilità di tre semi riguarda
solo le cellule finali Poisson, non tre inferenze indipendenti di Stack.

La candidatura può proseguire dal pilot secondo la sua regola già fissata. È
consentito anticipare la preparazione degli input; l'eventuale esecuzione della
conferma richiede la decisione operativa del lead. Se eseguita, si riportano tutti
i risultati indipendentemente dall'esito. Non si uniscono pilot e conferma per
ottenere il verdetto.

## Bersagli e dati fissati

Ordine dei dodici bersagli:

`PCBP1, CDC20, RNF31, KIF11, C7orf26, RPS24, GINS2, YRDC, DESI1, MRPL38, RSL1D1, MYBBP1A`.

La regola è SHA256 di `StackConfirm:20260929:<target>` sui target eleggibili residui
del manifest generatore, con almeno 64 cellule K562 originali; primi dodici.
Si escludono sviluppo, conferma generatore e pilot. Nessuna sostituzione o
esclusione successiva. La selezione è verificata nuovamente da
`stack_confirmation_pack.py` contro la lista e i manifest congelati.

- Sorgente: min(128, n) cellule K562 per bersaglio, almeno 64, tutte le guide
  aggregate per simbolo. La selezione conserva gli indici originali e lo stesso
  `rng_for('source:<target>')` del pilot. 1.421 righe complessive per questi target.
- Controlli: `source_00.h5ad`, 512 NTC K562, e `destination_controls.h5ad`,
  2.000 NTC HepG2, copiati **byte per byte** dal bundle del job 064. Hash controllati
  prima della preparazione e dell'inferenza. Nessun ricampionamento dei controlli
  sperimentali fra bracci o semi.
- Stack usa lo stesso sottoinsieme deterministico di 512 dei 2.000 NTC HepG2 e
  controlli sorgente appaiati alla dimensione del prompt, come il pilot.
- L'inferenza vede soltanto prompt K562, controlli HepG2 e transfer congelato.
  Tutte le cellule perturbate HepG2 dei dodici bersagli sono riservate al processo
  successivo di scoring. Il numero di righe è riportato, senza tagli a 400 o metà.
- Asse HepG2 e regola duplicati identici al pilot: prima colonna per simbolo.
  L'assenza di misura nel transfer è la mask `observed`, non `lfc != 0`.

## Effetti statici e generazione finale

Modello Arc commit `cacc2e4b09435c3e536d46237d10b50f222dd144`, checkpoint
`arcinstitute/Stack-Large-Aligned` revision `b09f085dac03d170b078a5c72f550ae93686e544`.
Pesi SHA256 `f93cf6f42f36c8a85dc570d92e801c1fc3e1f45d55741e6bb250d178a6b6ad36`;
lista geni `d8761dfda955b9897d3251798b72361ddd0171ef707119eaf65381bed2d85dcc`.
`ICL_FinetunedModel`, eval/no-grad, cinque passi mdm, prompt ratio 0,25, context
ratio 0,4, minimo 0,2, mask rate 1, worker 0. **Seed Stack 20260929**, identico al
pilot, per prompt e relativo controllo sintetico; controllo in cache per
cardinalità del prompt. Batch e ambiente registrati; nessun fine-tuning.

Si conserva la formula esatta di `stack_pilot.py` congelato,
SHA256 `b259371df3d0d515003597c4d9ce5755c25840f0d36fc96d8ac390ffe1275508`:

1. `q0 = predicted_profile(basal_sum, lfc_ln/log(2), observed)[0]`, con gli stessi
   effetti transfer preparati per questa destinazione.
2. S è l'intersezione dei geni misurati K562/HepG2 e dei geni Stack; sull'asse
   completo del modello gli altri geni sono zero in entrambi gli input.
3. I conteggi decodificati perturbati e controllo sintetico sono sommati e
   normalizzati separatamente su S. `d = clip(log((p+1e-6)/(c+1e-6)), ±6log(2))`.
4. Su S, `qStack` è il basale HepG2 inclinato da `exp(d)` e normalizzato alla massa
   `sum(q0[S])`; fuori S è **esattamente q0**. La massa totale è conservata.

La formula con d nullo non rende qStack uguale al basale completo se la massa
q0(S) differisce da quella basale: mantiene la composizione basale **entro S** e
la massa del transfer su S. Questo comportamento composizionale già congelato
non viene corretto sulla base dei risultati.

**Esportare q0 e qStack esatti in float64, insieme ad asse, target e supporto,
prima del campionamento finale.** Nessun arrotondamento a conteggi e nessuna stima
dei profili ricavata dalle 400 cellule del pilot. L'archivio NPZ deve aprirsi con
`allow_pickle=False`, avere tutti i dodici target e registrare il proprio SHA256.
Lo scorer rigenera le cellule da questo archivio e non rilancia il modello GPU.

Per ciascuno dei semi finali **1, 2, 3**, ciascun bersaglio e ciascuno dei due
bracci, creare un nuovo RNG con la stessa funzione del banco generatore:
`default_rng(SeedSequence([seed, u0, u1]))`, dove u0/u1 sono i primi otto byte di
SHA256 del nome target UTF-8, letti come due uint32 little-endian. Il seed non
include il nome del braccio, né dipende dall'ordine dei bersagli.

`resample_library_sizes` campiona 400 library size dai 2.000 NTC. Quindi
`sample_counts` con il profilo statico, **Poisson, phi=None**, massimo 12.000
valori memorizzati e 1.000.000 conteggi per cellula. I cap sono quelli del pilot
e del banco; registrarne eventuali interventi. Le cellule sono nuove, i totali
per gruppo non sono bloccati. Si riinizializza il medesimo flusso per l'altro
braccio: le library sono appaiate, senza presumere che il Poisson consumi un
numero identico di variabili casuali con intensità diverse.

## Scoring e aggregazione

Scorer vero del banco, `FrozenTruthBench` full truth come nel pilot:
backend Scanpy CPU, stessi 2.000 controlli, tutte le cellule perturbate dei dodici
target. Salvare versione `cell-eval2`, configurazione completa, assi, hash degli
input/profili/codice, conteggi di cellule e sei risultati aggregati per ogni
braccio/seme. Non si costruiscono ancore locali da repliche non indipendenti.

I cinque membri della primaria sono, per nome:

- `pds_cosine`;
- `de_wilcoxon_lfc_nmae`;
- `de_wilcoxon_direction_fidelity_yield_raw`;
- `de_wilcoxon_direction_reach_raw`;
- `de_wilcoxon_sig_jaccard`.

Per ogni membro m, usare la pendenza
`w_m = 1/(replicate_m - baseline_m)` dalle ancore ufficiali congelate in
`reports/gara/anchors_2026-09-17/anchors.json`, SHA256
`1821f7af101034a83361577051fe686858602b212becd64548d3ff7517e4f52e`.
La pendenza NMAE ha segno negativo. Il contributo MSE alla primaria è zero.

Per ciascun seme s, `D_s = sum_m(w_m * mean_t(delta_raw_s,t,m))/6`;
la media usa i soli target eleggibili di quel membro. Il risultato primario
`D = mean_s(D_s)`. Usare gli stessi dodici target per tutti i bracci e semi,
con **identico pattern di eleggibilità per membro**. La perdita di un target,
un valore non finito PDS o un cambiamento di eleggibilità invalida il confronto:
non si elimina il caso sfavorevole. Se un membro non ha target eleggibili,
la primaria non è definita.

Verificare che la media per-target dei cinque membri ricostruisca gli aggregati
del comparatore. Per `expr_mse_unbiased_capped_norm` si mantiene invece il
**rapporto di somme** del numeratore capped e della distanza reale eleggibile,
verificandolo quando i componenti sono disponibili. Si riportano MSE grezza e
variazione per ogni seme, non la media ingenua dei rapporti per-target.

Il PDS qui è quello prodotto dal comparatore sul pannello fisso di dodici
bersagli; non è un semplice coseno medio e non è confrontabile direttamente
con PDS di pannelli da 48, 96 o 300 bersagli.

## Bootstrap e regola definitiva

Bootstrap appaiato sui target: **2.000 estrazioni**, RNG NumPy seed **20260929**,
ciascuna di dodici indici con rimpiazzo. La stessa matrice di indici si applica
a entrambi i bracci, a tutti i membri e ai tre semi. Ogni estrazione ricalcola
i denominatori eleggibili di ciascun membro e poi media sui tre semi. Intervallo
bilaterale percentile **95%**, quantili NumPy 0,025 e 0,975, metodo lineare.
Una sola alternativa fissata: nessuna correzione per altri candidati selezionati
su questi target, perché non ne sono ammessi.

Se anche una sola estrazione non contiene alcun target eleggibile per un membro,
non si elimina né sostituisce quell'estrazione: intervallo non definito,
conferma **inconclusiva e non promuovibile**. Salvare la frazione completa.
I semi non sono ricampionati e non si sceglie quello migliore. Riportare i tre
delta e la loro deviazione standard separatamente.

La conferma passa soltanto se sono soddisfatte **tutte** le condizioni:

1. D **>= +0,005**.
2. Ognuno dei tre D_s è **strettamente positivo**.
3. Il limite inferiore dell'IC95% bootstrap è **strettamente maggiore di zero**.
4. La media sui tre semi della variazione grezza PDS è **>= 0**.
5. Provenienza, assi, target, conteggi, eleggibilità e ricostruzioni dello scorer
   hanno superato tutte le verifiche.

Il bootstrap è condizionale ai controlli, ai profili Stack statici, ai tre semi
osservati e ai ranghi PDS del pannello completo; non ricalcola una nuova matrice
PDS su ogni campione di target duplicati. Quindi non rappresenta tutta
l'incertezza del modello, delle cellule reali, dei confronti fra bersagli o
delle famiglie nuove. Con soli dodici bersagli l'intervallo può essere fragile.
Questo limite viene riportato anche se il gate passa e non modifica le soglie.

## Output, lettura e conseguenze

Lo scorer scrive manifest prima di caricare gli outcome, file grezzi e per-target
per tutti i sei bracci/semi, diagnostica dei conteggi, contributi di ciascun
membro, tutte le 2.000 repliche bootstrap e un verdetto finale **solo dopo** la
conclusione di tutti i confronti. Nessuna lettura dei risultati parziali per
decidere se fermare, alterare o estendere il candidato. Output nuovi, senza
overwrite; una correzione puramente meccanica conserva il tentativo precedente
e specifica se qualche score era già visibile.

Se la regola fallisce, il candidato non supera questa conferma. Se passa,
supporta soltanto un confronto cellulare locale di questo ibrido sopra il
transfer K562 congelato. Non prova un miglioramento sopra t25 multisorgente o
t28, né generalizzazione a nuovi contesti/pretraining esclusi. Una produzione
A/B/C conserva l'estensione di regime già dichiarata nella proposta e richiede
una decisione distinta; nessun invio VCC è autorizzato da questo file.

Prima di eseguire, congelare gli hash di questo protocollo, degli script
`stack_confirmation_infer.py`, `stack_confirmation_score.py` e delle dipendenze
nel manifest remoto. Test sintetici necessari: esportazione/ricaricamento dei
profili senza pickle, loro parità con la formula del pilot, flussi per target
stabili e appaiati, identità dei controlli, cardinalità dei sei bracci, bootstrap
con denominatori diversi/mancanti e bordi esatti delle cinque condizioni.
