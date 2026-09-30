# Quanto sostengono i dati dei banchi

29 settembre 2026. **Audit indipendente di manifest, separazioni e codice**, non
una nuova lettura degli outcome. Non sono stati letti nuovi score Stack, né
matrici di espressione per questo audit. Le verifiche riproducibili sono in
[`score_bias_dati_r1/population.json`](score_bias_dati_r1/population.json), prodotte
da [`audit_score_population.py`](audit_score_population.py), con hash dei manifest.

I confronti locali sono informativi sulle alternative effettivamente confrontate.
La loro riproducibilità numerica non li rende stime calibrate dello score VCC.
Il limite maggiore è **quale popolazione e quale distribuzione vengono misurate**,
oltre alla dipendenza tra osservazioni e alla copertura dei geni.

| Banco | Ciò che è effettivamente tenuto fuori | Ciò che rimane condiviso | Affermazione sostenibile |
|---|---|---|---|
| Generatore | 96 bersagli distinti dai 48 della scelta odierna; nessuna risposta HepG2 nel transfer K562 | Un solo studio/contesto, stessi 2.000 NTC, pannello selezionato, verità già studiata in precedenza | Confronto appaiato di generatori su quel banco |
| Stack A/B | RNA perturbato HepG2 assente dal bundle di inferenza; eventuale riserva distinta | 12 target development del banco generatore, stessi NTC, stesso checkpoint, pretraining non escluso | Test dell'ibrido e della rappresentazione degli input su quel pilot |
| Source-attention | Famiglia esterna interamente assente da train e refit; famiglia interna separata per scelta passi | Stessi bersagli in altre sorgenti, controlli destinazione, studi/target riusati nei fold e nei semi | Generalizzazione nello spazio degli effetti a famiglia nuova, regime C |

## Generatore: una conferma interna ben separata, su una popolazione selezionata

**Misurato:** i manifest sviluppo e conferma sono byte-identici, SHA256
`7b7459ca86d0bef53d4a53f3b7bcae983189a44f623deb2510d7ed33da07d79f`.
274 bersagli eleggibili; 48 sviluppo e 96 conferma, intersezione zero. Le righe
perturbate sono uniche e non intersecano i 2.000 controlli. Asse: 9.624 geni.
Verità sviluppo: 4.659 cellule, da 50 a 459 per target, mediana 72,5; conferma:
8.249 cellule, da 50 a 430, mediana 67. Ogni previsione contiene 400 cellule.
Il software di scoring registrato è `cell-eval2==0.16.0`.

La truth è intera, non dimezzata: vale l'emendamento 01, scritto prima dello
scoring. Questo evita una perdita di potenza e non aggiunge outcome al predittore.
I controlli sono utilizzati sia per stimare basale/library/dispersione sia come
riferimento dello scorer. È coerente con il problema condizionato sui controlli,
ma il bootstrap dei target **non misura** l'incertezza dovuta a scegliere altri
controlli, un altro esperimento o un'altra linea.

`generator_bench.select_targets` interseca pannello congelato, simboli presenti
nell'asse della truth e almeno due cellule. Il pannello a monte proveniva dal
banco HepG2 essenziale con almeno 50 cellule: lo documenta il report storico
[`banco HepG2 v2`](../../generatore_e_banchi/banco_hepg2_v2_2026-09-26/RISULTATI.md).
Il nuovo minimo osservato di 50 conferma che non stiamo misurando un campione
arbitrario di perturbazioni rare. Non è dimostrato che questa popolazione abbia
gli stessi effetti, sopravvivenza, profondità e rumore del pannello della gara.

**Bias di riuso del benchmark:** quello stesso studio e i suoi bersagli erano
già stati analizzati il 26 settembre. I 96 sono separati dalla selezione della
griglia odierna; non sono una truth mai esaminata nella storia del progetto.
Le ipotesi del 29 possono quindi incorporare apprendimento dal vecchio banco.
Questo non è leakage diretto nel transfer, ma limita la forza della parola
«indipendente» e la generalizzazione dell'intervallo.

La maschera sorgente viene ricostruita dal bulk K562, con gate basale 1e-6;
il manifest registra 7.681 geni osservati sull'asse **prima dell'allineamento**.
Non è corretto chiamarli automaticamente 7.681 dei 9.624 geni della truth.
I geni non supportati restano mascherati nel trasferimento: uno zero misurato
non è assenza. Gli effetti sono t19like congelati, non la miscela t25/t28 completa.

La selezione su 14 bracci è seguita da al massimo due finalisti e intervalli
97,5% se due: attenua la selezione multipla della griglia, non rende 96 target
indipendenti per biologia. Le tre realizzazioni quantificano il sampling del
generatore sulla stessa truth, non tre studi. La primaria cinque pendenze/6,
con MSE posta a zero, resta una **proiezione**: ancore ufficiali non ricreano la
normalizzazione e la distribuzione del test ufficiale.

Fonti: [`PROTOCOLLO_GENERATORE.md`](PROTOCOLLO_GENERATORE.md),
[`emendamento 01`](EMENDAMENTO_GENERATORE_01.md),
[`emendamento 02`](EMENDAMENTO_GENERATORE_02.md),
[`generator_bench.py`](generator_bench.py),
[`manifest conferma`](generator_confirmation_r3/target_manifest.json).

## Stack: isolamento del prompt verificabile, pretraining non escluso

**Misurato:** i 12 target del pilot appartengono tutti ai 48 development del
generatore e nessuno ai 96 confirmation. Si aggiunge il requisito di almeno
64 cellule sorgente K562, con massimo 128 usate: altra selezione per copertura.
Il bundle contiene prompt K562 e soli NTC HepG2; l'inferenza non dispone della
truth perturbata di destinazione. La colonna `pretraining_holdout_verified` nel
manifest di valutazione è esplicitamente `false`: non va trasformata in una
garanzia che Stack non abbia già visto HepG2 o dati pertinenti nel pretraining.
Non implica che li abbia certamente visti; lo stato è **non verificato**.

I 512 NTC di contesto Stack provengono dagli stessi 2.000 usati per sampling e
scoring. I target della riserva sono nuovi rispetto ai due split generatore,
ma controlli, studio, modello e pretraining restano comuni. Tre semi finali
Poisson non sono tre inferenze indipendenti del decoder. La scelta A/B prima
della riserva evita una seconda selezione su quest'ultima se viene rispettata
la regola di una sola conferma e nessuna seconda chance.

Si misura un **ibrido Stack/transfer**: soltanto 5.179 geni ricevono la correzione
Stack, fuori supporto il profilo transfer resta esatto. B amplia gli input ai
geni disponibili per ciascuna sorgente, ma non amplia quel supporto di uscita.
La baseline A/B scaricata è stata verificata byte-identica e identica nelle
matrici; questo rende pulito il confronto locale, non il salto verso tutte le
18.533 risposte ufficiali. Il PDS su dodici target dipende fortemente da quel
pannello di alternative. Il bootstrap che mantiene i ranghi completi fissi
non ricostruisce l'intero problema di ranking per un nuovo pannello.

Fonti: [`protocollo pilot`](neural/PROTOCOLLO_STACK.md),
[`protocollo A/B`](neural/PROTOCOLLO_STACK_AB.md),
[`protocollo conferma`](neural/PROTOCOLLO_STACK_CONFERMA.md),
[`manifest di valutazione A`](neural/stack_a_scoring_r2/evaluation_manifest.json),
[`parità della baseline`](kaggle_stack_variant_b_r1/transfer_cells_comparison_r1.json).
L'audit non usa l'esito dello scoring A/B.

## Source-attention: holdout dei contesti reale, metrica e truth più strette della gara

**Misurato nuovamente dai cinque manifest seed1 e dagli indici di riga:**
6.144 coppie target-contesto, 5.049 bersagli unici, 12 contesti, cinque famiglie.
Zero righe di test nel train o nel refit; zero righe di qualsiasi contesto della
famiglia esterna nel train/refit; zero righe della validation interna nel train.
La successiva inclusione della famiglia di validation nel refit avviene dopo
la scelta dei passi ed è il disegno annidato dichiarato.

Il test seleziona al massimo 512 target per contesto, **escludendo il pannello
ufficiale**; non è quindi una verifica diretta di quei 300. Gli outcome degli
stessi target nelle famiglie visibili sono leciti nel regime C, che è quello
effettivamente eseguito. `hidden_targets` è vuoto in tutti e cinque i fold:
nessuna pretesa di regime T/J. La rete è addestrata qui; non eredita il problema
di pretraining opaco di Stack, ma usa sorgenti pubbliche e prior STRING/basali.

`SourceView` ricalcola centri, disponibilità dei geni, normalizzazione dei prior,
riferimento cieco e fallback solo dalle righe visibili; `read` rifiuta quelle
invisibili. I controlli della destinazione sono input consentiti. Il dataset
memorizza 13.248 geni su 18.533, da un prefiltro globale di disponibilità che
includeva sei famiglie, anche una knockout poi esclusa dal training CRISPRi.
Il successivo filtro di train è nuovamente applicato: non ho trovato nel codice
letto l'uso di valori perturbativi esterni come feature. Il prefiltro globale
va comunque dichiarato come conoscenza della copertura complessiva, senza
presentare l'intera preparazione del dataset come fold-specifica.

La truth è un effetto raw aggregato, con SE finito positivo, gene proprio/cis
esclusi e supporto comune fra le truth del contesto. Viene centrata usando i
target del pannello di valutazione, **soltanto nel lettore**. Questa scelta non
fornisce la media di test al predittore, ma cambia l'estimando: si misura la
distinzione fra perturbazioni dopo aver tolto una componente comune. Non è
fedeltà DE cellulare, potenza, distribuzione di cellule o MSE ufficiale.
Lo zero per assenza di sorgente viene valutato e non elimina quel target;
assenza di misura e assenza di previsione restano distinte.

I target ricompaiono fra contesti e molti dati sono training in altri fold:
il cross-validation non equivale a cinque repliche indipendenti. Seed0/seed1
condividono truth, split e controlli; separano casualità di ottimizzazione,
non quella di popolazione. Il bootstrap primario per contesto era condizionale
ai ranghi; la diagnostica seed1 per target comune tra contesti e ricalcolo PDS
tratta una parte di questa dipendenza, senza riaddestrare o ricampionare studi.

Fonti: [`protocollo neurale`](PROTOCOLLO_NEURALE.md),
[`train_neural_sources.py`](train_neural_sources.py),
[`neural_sources.py`](neural_sources.py),
[`manifest dataset`](kaggle_neural_r1/input_metadata/manifest.json),
[`protocollo cluster`](neural_external_validation/PROTOCOLLO_DIAGNOSTICA.md),
[`verifiche delle separazioni`](score_bias_dati_r1/population.json).

## Giudizio scientifico

**Interpretazione:** i banchi sono abbastanza controllati da scartare ipotesi
che non migliorano neppure questi confronti e da sostenere candidature mirate
quando passa il criterio preregistrato. Non sostengono un numero VCC atteso con
la precisione dei loro intervalli locali. Un vantaggio su un solo contesto,
un supporto genico limitato o un proxy centrato richiede un salto di distribuzione
ancora non misurato. La frase verificabile è «vantaggio nel banco specificato»;
la probabilità di competere in classifica resta un'ipotesi finché non arriva
lo scorer ufficiale su un invio identificato.
