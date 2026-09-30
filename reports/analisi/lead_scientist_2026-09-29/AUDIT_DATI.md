# Audit dei dati e delle premesse di piattaforma

29 settembre 2026, Codex, sottoattività `audit_dati` della revisione lead scientist.
Letture e calcoli locali; nessun download, nessuna modifica ai dati grezzi o ai risultati precedenti.
Le nuove misure sono descrittive ed esplorative, non punteggi VCC e non una selezione confermativa.

## 1. Correzione decisiva: CD4 è già Flex

**Misurato su fonte primaria locale.** Tutte le 12 righe della tabella degli autori
`reports/storico/candidate_verification/annotations/cd4_sample_metadata.csv` riportano
`library_prep_kit = GEMX_flex_v1`: quattro campioni Rest, quattro Stim8hr e quattro Stim48hr.
Lo sha256 locale coincide con quello del manifest di acquisizione:
`766134d11dabb5d63388e00b4d687a809c0254eb3c19d77f439a6bf9dad7abd4`.
La provenienza è il
[CSV degli autori](https://raw.githubusercontent.com/emdann/GWT_perturbseq_analysis_2025/master/metadata/suppl_tables/sample_metadata.suppl_table.csv),
salvato e identificato nel `manifest.json` accanto; non è stato necessario un nuovo accesso di rete.
Ricalcolo e provenienza sono in `cd4_r1/summary.json`.

È quindi falsa la premessa «tutte le sorgenti tranne VIPerturb-seq sono in 3'», ripetuta in
`reports/sorgenti/README.md`, nella premessa del ponte Flex e nelle sintesi successive.
Il ponte K562 VIPerturb–Replogle resta una misura valida di quella coppia; **non rappresenta
tutte le sorgenti della ricetta**. Inoltre `reports/sorgenti/schede_sorgenti_2026-09-24/SCHEDE.md`
indica Orion come GEM-X 5′: questa è un'ulteriore contraddizione interna della sintesi «tutte 3′»,
qui non risolta riesaminando il protocollo primario di Orion.

**Conseguenza di ricerca.** La baseline usa già una sorgente Flex per 293 dei 300 bersagli.
VIPerturb aggiunge un'altra linea e un altro studio Flex, non il primo accesso alla piattaforma.
L'ipotesi «manca Flex» va sostituita da domande su stato, laboratorio, qualità della stima e
contesto. Questa correzione non dimostra che aumentare il peso CD4 migliori il punteggio.

## 2. Che cosa cambia tra gli stati CD4

**Misurato**, cache corretta `processed/multisource_2026-09-27_r9`, script
`audit_cd4_states.py`, uscita `cd4_r1/`:

| Sorgente | Bersagli | Cellule mediane | Geni risposta osservati, mediana | LFC naturale del gene proprio, mediana |
|---|---:|---:|---:|---:|
| Rest | 293 | 504 | 10.530 | −1,98 |
| Stim8hr | 292 | 485,5 | 10.430 | −2,03 |
| Stim48hr | 292 | 487 | 10.775 | −1,85 |
| mix | 293 | 1.484 | 11.132 | −1,94 |
| metà donatori A, Stim48hr | 287 | 243 | 10.732 | −1,72 |
| metà donatori B, Stim48hr | 287 | 221 | 10.773 | −1,85 |

Per confronto K562 copre 272 bersagli, 171,5 cellule mediane e 7.681 geni risposta. I valori sul
gene proprio escludono le coppie non misurate; le numerosità esatte sono nel JSON.

Le seguenti misure usano gli effetti ristretti centrati per sorgente come γ=1, supporto finito
comune a ciascuna coppia e peso `x/(1+x)`, `x=0,05 CPM`, dai controlli A/B/C. Escludono tutti
i 300 geni del pannello come geni risposta. Non includono generazione di cellule o scorer.

- **Rest contro mix:** coseno mediano 0,756–0,768, ma rapporto mediano delle energie
  1,99–2,04. La differenza fra le due previsioni ha energia pari al 78–82% di quella del mix.
  Sostituire mix con Rest alla stessa ampiezza non isola lo stato: cambia anche molto l'energia.
- **Stati diversi, stessi donatori:** coseno mediano 0,263–0,328.
- **Donatori disgiunti, stesso stato Stim48hr:** solo 0,046–0,060; energia della metà A circa
  0,53–0,56 volte quella della metà B. Sono 282 bersagli comuni. Non c'è una cache analoga
  per Rest: la sua riproducibilità tra donatori non è stata misurata in questo audit.
- **K562 contro CD4:** coseni 0,015–0,022; il mix è debolmente più concorde delle singole
  condizioni, senza che questo stabilisca quale predice meglio i contesti ufficiali.

**Interpretazione.** L'accordo fra condizioni CD4 non è un tetto indipendente: condividono
donatori e guide. La differenza con l'accordo fra donatori rende concreta una componente di
donatore o batch, oltre al rumore. Favorire Rest perché «più simile allo stato della gara» non
è sostenuto dai soli basali: la correlazione Spearman di A con Rest/8h/48h vale
0,861/0,858/0,864; B 0,755/0,765/0,767; C 0,765/0,770/0,783. Una correlazione basale non
è comunque una misura di trasferimento causale.

**Altro fattore da controllare.** La ricetta detta «a pesi uguali» moltiplica ogni peso per
`n/(n+100)`. La mediana è 0,937 nel mix, 0,834 in Rest e 0,632 in K562. Il mix somma cellule
dei tre stati: ciò aumenta la sua affidabilità convenzionale, senza misurare l'indipendenza
fra gli effetti. Per attribuire una prova a Rest bisogna dichiarare anche questo cambiamento.

**Proposta.** Confrontare mix, Rest e mix con maggior peso CD4 su un test indipendente
appartenente al saggio Flex, tenendo fissi supporto, energia e codice di generazione; affiancare
la prova a energia invariata alla ricetta produttiva. La verifica tra donatori deve tenere
fuori lo stesso donatore in tutti gli stati, senza usare lo stato corrispondente del donatore
di test per pesi, normalizzazione o selezione dei geni. Nessun braccio è promosso da questo audit.

## 3. VIPerturb-seq: opportunità reale, copertura e misura incomplete

**Misurato dagli indici locali**, `dati_r1/flex_panel_coverage.csv`:

- 123 dei 300 bersagli hanno un effetto nello schermo completo; cellule per bersaglio:
  mediana 45, quartili 34–60,5. Sono 71 sotto 50 cellule e tutti sotto 100.
- La sorgente ha 18.111 geni sull'asse nella tabella basale; questo non significa altrettante
  risposte stimabili per ciascun bersaglio dopo i filtri di conteggi attesi.
- Nei risultati già salvati del ponte, 113 bersagli del pannello sono confrontati con K562:
  coseno mediano 0,0136, quartili −0,00043–0,0493. Il rapporto mediano energia Flex/K562
  vale 1,53: la sorgente Flex non è semplicemente una versione di minore ampiezza del 3′.
- Il vecchio split-half misura solo i bersagli selezionati perché hanno ≥30 geni significativi
  in entrambi gli schermi completi. Sul pannello sono 46, e solo 44 hanno tutte le coppie.
  Su questi 44: metà Flex contro metà Flex 0,09075; ciascuna metà contro K562 3′
  0,03053 e 0,02338; Flex completo contro K562 0,04665.

**Interpretazione.** La riproducibilità interna è superiore all'accordo fra studi, anche sul
pannello. Tuttavia scegliere i 44 sugli outcome favorisce effetti forti; il confronto non
dimostra la qualità sui 123 coperti né sui 177 mancanti. Un basso coseno verso 3′ non
dimostra che la sorgente Flex sia inutile per un altro contesto Flex.

**Proposta verificabile con file già presenti.** Valutare tutti i bersagli condivisi fra le
due metà, senza filtro sulla significatività; separare bersagli di scelta e valutazione.
Confrontare la previsione da una metà con K562, CD4 e la loro miscela verso l'altra metà,
poi scambiare le metà. Confronti per gene o selezioni devono essere stimati fuori dai
bersagli di valutazione. Questo isola l'utilità dello studio meglio di una mediana di coseni.
Resta una prova K562/Flex e non una misura di generalizzazione a una linea ufficiale nuova.

## 4. Normalizzazione: difetto misurato, senza promessa di guadagno

**Misurato**, `dati_r1/basal_scale.csv`, sui basali del 28/09. Fattore necessario a portare
a 10⁶ la somma dei CPM sui soli geni ufficiali misurati dalla sorgente:

| Sorgente | Fattore | Geni che superano 5 CPM dopo la riscalatura |
|---|---:|---:|
| K562 | 1,467 | 0 |
| CD4 mix | 1,021 | 21 |
| HCT116 | 1,407 | 460 |
| HEK293T | 1,357 | 420 |
| KOLF2.1J | 1,353 | 556 |
| A549 | 1,377 | 529 |
| VIPerturb | 1,027 | 21 |
| A/B/C | 1,000 | 0 |

Questo quantifica il difetto dell'azione 5 di R-REV. Una riscalatura uniforme conserva
le correlazioni Spearman, ma cambia le soglie e i pesi dipendenti dal livello assoluto.
Non ricostruisce risposte mancanti: K562 ha solo 7.681 geni misurati nel basale. Portare ogni
colonna a 10⁶ sui geni disponibili non equivale a un asse completo comune se i supporti
misurati differiscono. Un confronto su intersezione deve dichiarare l'intersezione e
ricalcolare il denominatore su quella; un modello con supporto più ampio deve mantenere le
maschere. La ricetta t25 non usa questi basali come pesi di sorgente: non si prevede un
guadagno diretto correggendo solo questo CSV.

## 5. Le sorgenti disponibili non sono repliche intercambiabili

L'inventario `dati_r1/universe_coverage.csv` conta le righe con chunk valido, non la semplice
esistenza del file. Fra le sorgenti aggiuntive:

| Sorgente | Bersagli validi | Bersagli del pannello | Cellule mediane sul pannello |
|---|---:|---:|---:|
| KOLF2.1J | 10.985 | 281 | 237 |
| A549 | 1.000 | 21 | 631 |
| Southard Hs27 | 1.836 | 80 | 106 |
| HIPSCI genome-wide fitness, controlli ampliati | 2.147 | 31 | 50 |
| HIPSCI genome-wide nonfitness, controlli ampliati | 4.515 | 151 | 23 |

A549 è knockout, Southard è CRISPRa: non sono osservazioni dello stesso intervento CRISPRi.
HIPSCI usa anche cellule senza guida assegnata nei controlli degli universi `_ua1`;
gli universi precedenti `_me1` con pochi controlli sono dichiarati inaffidabili e non vanno
riammessi soltanto perché presenti. Le 19 linee HIPSCI mirate condividono studio e tipo
cellulare: non valgono come 19 tipi cellulari indipendenti. Fonti:
`reports/sorgenti/universo_nuovi_2026-09-27/RISULTATI.md` e
`reports/sorgenti/universo_hipsci_2026-09-27/RISULTATI.md`, controllati contro REGISTRO.

## 6. Evidenza privata e limiti delle conclusioni precedenti

**Verificato localmente.** Un confronto dei controlli con DepMap e un controllo genomico
indipendente erano già stati svolti il 24/09 e conservati fuori dalla repository pubblica.
La frase pubblica «non da un confronto con DepMap/CCLE» non descrive tutta l'evidenza locale.
Le identità e le associazioni con A/B/C non sono riprodotte qui; sono state riferite al lead
separatamente. Le ipotesi di identità non diventano conferme ufficiali.

È presente anche un esperimento privato già concluso su un dataset mirato ad alto MOI. La
lettura del suo codice conferma che il tetto dopo centratura misura la parte specifica del
bersaglio, mentre quello prima della centratura è dominato da una componente comune.
Il cutoff operativo scelto allora non è una prova universale d'inutilità di dati della stessa
linea. D'altra parte il forte accordo comune non identifica l'effetto di un singolo knockdown:
non giustifica il trasferimento automatico di quella componente nella ricetta.

## Riproduzione e limiti operativi

```powershell
.\scripts\py.cmd reports/analisi/lead_scientist_2026-09-29/audit_data_light.py --out <nuova-cartella>
.\scripts\py.cmd reports/analisi/lead_scientist_2026-09-29/audit_cd4_states.py --out <altra-nuova-cartella>
```

Entrambi rifiutano di sovrascrivere. La prima analisi legge tabelle e risultati preesistenti;
la seconda legge soltanto matrici cache del pannello. Nessuna matrice grezza grande, nuovo
training, invio o download. L'esecuzione dei due script è riuscita; i risultati e la fonte
primaria della correzione di piattaforma sono conservati nelle rispettive uscite.
