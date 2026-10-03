# Campioni annidati 32/64/128: quante cellule tenere per contesto e bersaglio

**Stato: congelato** con il commit che contiene questo testo, la notte fra il 3 e il 4 ottobre 2026, prima di lanciare
il kernel dello studio e prima di leggere qualunque suo numero. Scritto da Claude Code, sessione `d0100a`, binario dati
di [R-LEAD](../../../docs/piani/strategia-scientifica.md) e passo 3 di [R-DATI](../../../docs/piani/dati-affidabilita.md)
(«le soglie di sufficienza si fissano prima di leggere i numeri»). Dopo il commit la regola del §4 non cambia; un
difetto si corregge con un emendamento datato, scritto prima di leggere i risultati che tocca.

## 0. Che cosa è e che cosa non è

È uno **studio statistico** sulle copie di training, non sull'archivio: l'acquisizione resta completa
([strategia inoltrata dal proprietario](../../sorgenti/ingestione_completa_2026-10-03/STRATEGIA_DATI_TRAINING.md), punto 1).
Misura che cosa perde un campione di al più 32, 64 o 128 cellule perturbate per coppia (contesto, bersaglio) rispetto a
tutte le cellule della coppia, e propone un livello per unità.

- **Corpus:** quello del pilot v4, 8 gruppi di linea, 365 shard, 33 chiavi `studio|contesto`, 5.603.629 cellule nello
  stato del pre-passo H1 (`rcell-prepass-h1-r1`, sha256 nel [protocollo v4](PROTOCOLLO.md) §2). Entrano tutte le cellule
  perturbate a bersaglio singolo ammesse dal controllo di qualità, di ogni classe (training, linea esclusa, bersagli
  nascosti): qui non si addestra niente.
- **Lacune dichiarate (D-053):** CD4T, HCT116, HEK293T, KOLF pan-genome e le altre voci del catalogo non hanno ancora
  gemelli compatti né uno stato del pre-passo. Lo stesso studio, con lo stesso codice e la stessa regola, si ripete
  quando entrano; fino ad allora per loro non c'è un livello proposto.
- **Non è** il confronto fra livelli in training (sei metriche, a parità di aggiornamenti del modello): quello ha un
  protocollo suo e resta la prova. Questa regola sceglie da dove partire e dove allargare prima il tetto.
- Non è verificato qui che i tre stati del pre-passo (H1, HepG2, RPE1) ammettano le stesse cellule; lo studio usa lo
  stato H1.

## 1. Domanda

Tenendo al più *c* cellule perturbate per (contesto, bersaglio), ripartite fra librerie e guide, quanto dell'effetto
specifico del bersaglio misurabile con tutte le cellule si ritrova nel campione? Qual è il livello più piccolo che
basta, unità per unità?

## 2. Campionamento (regola di `nested_samples.py`)

- **Gruppo:** le cellule ammesse, non di controllo, a bersaglio singolo, di una chiave e di un bersaglio.
- **Strati:** (libreria, guida), dalle colonne `library` e `guides` degli shard.
- **Ordine:** dentro lo strato per sha256(seme | chiave della cellula), quindi stabile se gli shard vengono ritagliati;
  gli strati serviti a turno, così le prime *k* cellule coprono quanti più strati possibile. Nessuna cellula è scelta
  in base all'effetto osservato.
- **Livelli annidati:** le prime min(n, c) cellule dell'ordine; il 32 sta nel 64, il 64 nel 128. Un gruppo con n ≤ c
  resta intero. Oltre ai tre livelli della strategia si calcolano 256 e 512, per dimensionare le eccezioni al tetto.
- **Probabilità d'inclusione** di una cellula al livello c: cellule del suo strato tenute su cellule del suo strato;
  salvata per ogni cellula.
- **Controlli:** non campionati qui; entrano in un training dal suo serbatoio, riportato a parte.

## 3. Misure, per gruppo e per livello

Dai conteggi dei gemelli compatti, sui geni misurati della chiave, con lo spostamento = log della media delle
proporzioni del gruppo meno quello dei controlli ammessi della chiave (geni con entrambe le medie sopra 10⁻⁵):

- **Spostamento specifico:** lo spostamento meno la risposta generica della chiave, cioè la media degli spostamenti dei
  gruppi interi degli *altri* bersagli della chiave, gene per gene. Le cellule perturbate differiscono dai controlli
  anche per ragioni comuni a tutti i bersagli; un campione che conservasse solo quella parte comune resterebbe
  correlato al gruppo intero sullo spostamento totale (test `SpecificShift`). Per questo la regola legge lo specifico.
- `r_spec_c`: correlazione di Pearson fra lo spostamento specifico del campione e quello del gruppo intero;
  `sign_top_spec_c`: accordo di segno sui 200 spostamenti specifici più grandi del gruppo intero.
- **Pavimento di rumore:** le stesse misure fra due metà disgiunte del gruppo intero (parità dell'hash),
  `r_spec_halves`.
- **Copertura:** strati, librerie e guide presenti nel campione su quelli del gruppo.
- Le stesse misure sullo spostamento totale (`r_c`, `sign_top_c`, `overlap_top_c`, `rmse_c`) sono riportate.

## 4. Regola di sufficienza (si congela con il commit; costanti in `nested_rule.py`)

Per ogni unità (gruppo di linea::studio) e livello c:

1. **Gruppi interi** (n ≤ c): nessuna perdita per costruzione; si contano.
2. **Popolazione di lettura:** i gruppi troncati (n > c), in una chiave con almeno **10** bersagli, il cui effetto
   specifico è misurabile nel gruppo intero: `r_spec_halves` ≥ **0,5**. Dove nemmeno tutte le cellule danno un effetto
   specifico riproducibile, nessun livello è giudicabile: quei gruppi si contano a parte.
3. **Stato del livello:**
   - «senza perdita» se nessun gruppo dell'unità è troncato;
   - «non giudicabile» se la popolazione di lettura ha meno di **20** gruppi;
   - «sufficiente» se sulla popolazione di lettura la mediana di `r_spec_c` è ≥ **0,90**, il suo 10° percentile è
     ≥ **0,75** e la mediana di `sign_top_spec_c` è ≥ **0,90**;
   - altrimenti «insufficiente».
4. **Guardia di copertura**, su tutti i gruppi dell'unità: guide tenute al livello c su guide presenti ≥ **0,99**.
5. **Livello proposto per l'unità:** il più piccolo «sufficiente» o «senza perdita» che passa la guardia. Se non ce
   n'è: «oltre» quando il livello più grande calcolato è insufficiente o non passa la guardia (eccezione al tetto per
   quell'unità, punto 3 della strategia); altrimenti il livello più grande, segnato «non giudicabile» (scelta
   prudente).

**Perché queste soglie.** Sono soglie operative, non intervalli statistici. Non vengono da dati dello studio: la sola
base è un calcolo, fatto prima, di che cosa darebbe un campione casuale di c cellule di un gruppo omogeneo di n cellule
contro il gruppo intero, noto l'accordo ρ fra le sue due metà (κ = (1/ρ − 1)·n/2; r atteso = √((1 + κ/n)/(1 + κ/c))):

| n | ρ fra le metà | r atteso a 32 | a 64 | a 128 | a 256 | a 512 |
|---:|---:|---:|---:|---:|---:|---:|
| 200 | 0,5 | 0,60 | 0,77 | 0,92 | intero | intero |
| 200 | 0,8 | 0,80 | 0,90 | 0,97 | intero | intero |
| 200 | 0,9 | 0,89 | 0,95 | 0,99 | intero | intero |
| 1.000 | 0,5 | 0,30 | 0,41 | 0,55 | 0,71 | 0,87 |
| 1.000 | 0,8 | 0,48 | 0,62 | 0,75 | 0,87 | 0,95 |
| 1.000 | 0,9 | 0,62 | 0,75 | 0,86 | 0,93 | 0,98 |

Con 0,90 di mediana la regola non passa da sola (a 32 serve un effetto molto riproducibile) e non è impossibile (a
128 passa per gruppi di circa 200 cellule con accordo 0,5). Un'unità con molte cellule per bersaglio ed effetti deboli
può risultare «oltre»: è l'esito onesto, perché lì il gruppo intero sa più di qualunque campione piccolo. Che la
soglia giusta per il training sia proprio 0,90 non è dimostrato: lo dirà il confronto fra livelli sulle sei metriche.

## 5. Riportato senza soglia

Dimensioni reali per unità e livello (cellule tenute, quota, gruppi interi); gruppi non misurabili; le misure sullo
spostamento totale; `overlap_top_spec`; la differenza fra `r_spec_c` misurato e r atteso dal calcolo sopra (sotto zero:
il campione stratificato perde più di quanto spieghi il numero di cellule); guide e strati persi per gruppo.

## 6. Esito e passo dopo

- Il livello proposto per unità entra nel protocollo del corpus ampliato come livello di partenza delle copie di
  training; le unità «oltre» ricevono un'eccezione dimensionata sui livelli 256 e 512 o tutte le loro cellule.
- Qualunque esito non tocca l'archivio e non sostituisce il confronto in training fra livelli.
- Le unità «non giudicabili» restano tali: non si abbassa una soglia per farle rientrare.

## 7. Esecuzione

Kernel Kaggle CPU `rcell-v4-nested-h1-r1` ([kaggle_nested.py](kaggle_nested.py), nessuna quota GPU), `--caps 32 64 128
256 512`. Monta gli 11 dataset del corpus (gli shard, letti solo per `cell_key`, `library`, `guides`), i tre kernel dei
gemelli, il pre-passo H1 e il dataset del codice dei training. Prima dello studio ricontrolla sul proprio runtime i
moduli del codice, lo stato del pre-passo, ogni shard e ogni gemello (byte e sha256): se un controllo fallisce non
calcola niente. Uscite: `verify.json`, `nested/summary.json`, `nested/groups.csv.gz`, `nested/selection/<shard>.npz`
(livello e probabilità d'inclusione di ogni cellula), `nested/manifest.json`. La regola si applica in locale con
`nested_rule.py` alla tabella dei gruppi.

Test prima della spinta (20, tutti superati il 3/10 alle 23:51 sul portatile): `test_nested_samples` (6),
`test_nested_rule` (10), `test_kaggle_nested` (4: il `run.py` del kernel su un albero di input finto dà la stessa
tabella dell'esecuzione diretta; un gemello alterato, uno stato diverso o un modulo cambiato fermano il kernel prima
dello studio).

## 9. Emendamento del 4/10, 00:08 CEST, prima di leggere qualunque risultato

Il kernel `rcell-v4-nested-h1-r1` è in corsa e nessuna sua uscita è stata scaricata. Rileggendo la
[proposta di Codex](../../analisi/candidato_ibrido_2026-10-03/README.md) (§3) su richiesta del proprietario: per
scegliere la taglia chiede di confrontare, oltre a medie ed effetti e alla copertura delle guide, anche **varianza e
zeri**. Il kernel r1 non li calcola. Si aggiungono come misure **riportate senza soglia** in una seconda corsa (r2,
stesso seme e quindi stessa selezione delle cellule): per gruppo e livello, varianza per gene delle proporzioni e
frazione di zeri del campione contro quelle del gruppo intero. La regola del §4 non cambia e si applica alla tabella
della prima corsa. Gli «stati osservabili» della stessa lista (donatori, stimoli) in questo corpus sono chiavi distinte:
il campionamento è per chiave e bersaglio, quindi nessuno stato viene perso per costruzione.

## 8. Che cosa si sapeva al congelamento

- Nessun numero di questo studio: il kernel non era stato lanciato.
- Di un'altra sorgente, fuori da questo corpus (misurato, [consegna dell'ingestione](../../sorgenti/ingestione_completa_2026-10-03/HANDOFF_CLAUDE2.md)):
  KOLF pan-genome ha mediana 218 cellule per bersaglio, 3 guide e 30 librerie per bersaglio; i tetti 32, 64 e 128
  tengono 365.813, 716.099 e 1.376.068 cellule bersagliate su 2.512.462.
- Dello stato H1 (misurato, `splits.json`): 33 chiavi in 13 unità di training più H1; l'unità più grande è K562 GWPS
  con 1.616.514 cellule di training.
