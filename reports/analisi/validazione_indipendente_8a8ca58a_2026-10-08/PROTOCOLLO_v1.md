# Contratto sperimentale della validazione indipendente — v1

**Stato: congelato** con il commit che contiene questo testo, l'8 ottobre 2026 (orologio letto con `date`:
18:09 Europe/Rome alla generazione del manifest), **prima di qualunque numero comparativo**. Autore: VALIDAZIONE,
Claude Code, sessione `8a8ca58a`, incarico del proprietario in chat sul binario
[R-LEAD](../../../docs/piani/strategia-scientifica.md). Tipo: protocollo; nessun risultato.

La parte leggibile da macchina è [manifest_fold_v1.json](manifest_fold_v1.json) (sha256 `add35198…371cf7`,
scritto da [build_manifest.py](build_manifest.py) dai soli metadati committati). Dove questo testo e il manifest
differiscono vale il manifest, e la differenza è un difetto da segnalare. **Una modifica è una versione nuova**
(`PROTOCOLLO_v2.md`, `manifest_fold_v2.json`) che elenca i confronti da rieseguire; v1 non si riscrive.

Risponde alle richieste di [DATI-TRANSFER](../../modelli/dati_transfer_2026-10-08_01a11c34/HANDOFF.md) (manifest C/T/J
con alias, componenti dei bersagli, riserve e assi) e di
[MODELLI-ESTERNI](../modelli_esterni_01a11c35_2026-10-08/PROTOCOLLO_r1.md) (release, fold, liste, controlli, baseline,
asse, semi, generatore, aggregazione, unità di bootstrap e soglie).

## 1. Identità di dati, release e baseline

| Oggetto | Identità | Fonte |
|---|---|---|
| Asse dei geni | 18.533 geni, sha256 `25bfa667…47201`, ordine ufficiale | `release_r1.json` |
| Pannello | 300 bersagli, `panel_sha256` `c9c4c9a6…bea5ca`; file `pert_counts.csv` sha256 `f57edd7b…3276` | `release_r1.json`, pacchetto del fit r1 |
| **T0**, riferimento e riserva | t36: 13 fonti a peso 1, effetti `shrunk`, gamma 1, centratura `panel`, ampiezza 1,576, testa cis ×2 entro 5 kb; ricetta sha256 `3109a6d9…3226`; effetti di produzione sha256 `08fdfd28…4c57` (uguali per A, B, C) | [ricetta](../../invii/trial_2026-10-06/t36_recipe_extbank.json), [consumo r1](../../modelli/banca_canonica_2026-10-07/fit/r1/completion/consumo.json) |
| Punteggio ufficiale di T0 | 0,147249 (entry `JLcMRGExhXKk77XVds7x`), un invio | [comparison.json](../../invii/prediction_t36_2026-10-06/comparison.json) |
| **R1** | release canonica r1 del 7/10, 17 fonti, sha256 `0650d1d6…1c8c`; effetti `d7a8cb14…30ea` | [release_r1.json](../../modelli/banca_canonica_2026-10-07/fit/release_r1.json) |
| **T1** | release di DATI-TRANSFER: r1 senza il voto Tian 2019 neuroni su RFK, 16 fonti, sha256 `277ae344…ffd8` | [release_t1_r1.json](../../modelli/dati_transfer_2026-10-08_01a11c34/release_t1_r1.json) |
| **P4** | le quattro linee della ricetta t22/t25/t28 (K562, CD4T, HCT116, HEK293T) sulle tabelle del t36 | manifest, `arms` |
| Emettitore | t28: stadio 45, `trial-ext-profile`, effetti ×1,5, dispersione per gene dai soli controlli (scala 1), 400 cellule per bersaglio, seme 20260912 | [prediction.json del t36](../../invii/prediction_t36_2026-10-06/prediction.json) |
| Scorer | `cell-eval2` 0.16.0, configurazione `vcc2026`; la 0.18.0 non è provata equivalente da un'esecuzione | [verifica del 4/10](../../gara/scorer_0_18_2026-10-04/README.md) |

T0 è un riferimento storico con un solo punteggio ufficiale: nessuna stabilità dimostrata (CP-0067). P4 **non è il
t28**: usa le tabelle del t36, che per Orion sono derivazioni successive; serve a misurare l'ampliamento delle linee
a tabelle fisse. Il confronto ufficiale t36 − t28 contiene anche il cambio delle tabelle.

## 2. Fold C/T/J e dati consentiti

**Unità tenuta fuori: il lignaggio**, cioè la linea in tutti gli studi, stimoli e modalità (GENERALIZZAZIONE §3,
punto 2). È più largo del `line_group` del registro dove due gruppi sono la stessa linea e una sua derivata: HEK293T
è HEK293 con l'antigene T di SV40, quindi il fold che dichiara nuova HEK293T toglie anche Xu 2023 (HEK293).

| Fold | Lignaggio escluso | Tabelle escluse da ogni braccio | Verità primaria | Bersagli del pannello nella verità |
|---|---|---|---|---:|
| C-K562 | K562 | `k562`, `k562_essential`, `k562_gwps_sc`, `dixit2016`, `norman2019` | `k562` (BULK) | 272 |
| C-CD4T | CD4 T primarie, 4 donatori, 3 condizioni | `cd4_mix`, `cd4_Rest`, `cd4_Stim8hr`, `cd4_Stim48hr`, `shifrut2018` | `cd4_Rest`; le due stimolazioni come strati | ≤ 293 |
| C-HCT116 | HCT116 | `orion_hct116` | `orion_hct116` | 293 |
| C-HEK293 | HEK293 e HEK293T | `orion_hek293t`, `xu2023` | `orion_hek293t` | 299 |
| C-iPSC | iPSC: KOLF2.1J, cloni HIPSCI, iPSC di Tian | le quattro `kolf_*`, `hipsci_targeted_19`, `tian2019_ipsc` | `kolf_pan_genome`; `kolf_strong` come seconda libreria | 282 |
| C-H1 | H1 | `h1` (train e val) | `h1` | 17 |

- I neuroni derivati da iPSC (Tian) sono un lignaggio distinto nel registro e restano fra le fonti del fold C-iPSC;
  in C-H1 restano le iPSC. Sono tipi cellulari vicini: il fold misura una linea nuova, non un tipo cellulare
  lontano. Lo dichiara ogni tabella dei risultati.
- HepG2, Jurkat, RPE1 e K562 essential non hanno bersagli del pannello nelle tabelle di produzione: non sono fold
  del pannello. Restano linee di **sviluppo** per i banchi a sei membri su tutti i bersagli (cubo r2), insieme a H1
  e K562: lette più volte, non sono mai una conferma indipendente (CP-0066).
- **T e J.** Ogni simbolo di bersaglio appartiene al gruppo `sha256(simbolo) mod 5`: non cambia quando il corpus
  cresce. Gruppo 0 = test, gruppi 1–4 = validazione interna. T nasconde il gruppo 0 in ogni fonte tenendo il
  lignaggio; J combina un fold C con il gruppo 0 nascosto. Un'etichetta è nascosta se **una qualunque** delle sue
  componenti (guide, repliche, combinazioni, alias riconciliati al simbolo ufficiale) è nel gruppo, in tutte le
  fonti e in ogni derivato, prima che una statistica sia calcolata.
- Il transfer dello stesso bersaglio non ha previsione T/J oltre la testa cis: in J il suo braccio è quel ripiego,
  dichiarato. T/J discrimina solo i candidati con una componente che generalizza sui bersagli.
- **H1 test resta chiusa**: nessun fold, braccio, statistica, calibrazione o checkpoint valutato la legge. D, E, F
  non sono validazione.

| Fase | Che cosa può leggere |
|---|---|
| Stima di tabelle, medie comuni, pooling, shrinkage, maschere apprese, embedding dalle risposte | tutte le risposte **tranne** quelle del lignaggio escluso (C, J) e dei bersagli nascosti con le loro componenti (T, J) |
| Scelta di iperparametri, scala, pesi di miscela, arresto | solo fold interni: gli altri lignaggi (C) e i gruppi 1–4 (T/J), mai la verità del fold valutato |
| Inferenza sul fold | i **controlli non perturbati** del lignaggio escluso, annotazioni e sequenze esterne; nessuna sua risposta perturbata |
| Valutazione | la verità del fold, una volta, con questo protocollo |

Ampiezza 1,576, scala cis 2 ed emissione ×1,5 sono costanti nate su punteggi ufficiali di A/B/C e su banchi di
K562 e HepG2: sono comuni a tutti i bracci, quindi non entrano nei contrasti appaiati, ma i **livelli assoluti**
dei fold non sono stime pulite. La testa cis è stimata su coppie di K562 genome-wide (bersagli del pannello
esclusi): nel fold C-K562 usa risposte del lignaggio escluso, e il fold lo riporta con e senza cis.

## 3. Assi, scale, maschere e interfaccia di una previsione

Un braccio è, per ogni fold, un file nel formato dello stadio 100: `targets`, `genes` (l'asse ufficiale, nello
stesso ordine, senza duplicati), `lfc` float32 in **logaritmo naturale** con ampiezza e testa cis già applicate e
**senza** la scala dell'emissione, `observed` booleana della stessa forma. Una coppia non misurata o non prevista è
`observed = False` ed esattamente 0: non è un voto per zero (D-009). Un ingresso in log2 si moltiplica per ln 2 e
lo si dichiara; `p_de` e `delta_p` sono diagnostiche, mai effetti; nessun doppio cis, doppio guadagno o seconda
centratura.

**Che cosa consegna un candidato** (cartella del proprietario del candidato, mai modificata da VALIDAZIONE):

1. `candidate.json`: nome, sessione, base (T0 o T1), **l'unico fattore che cambia**, release con sha256, ricetta
   dello stadio 100 o codice equivalente con sha256, emettitore (t28, altrimenti è un contrasto a parte);
2. per ogni fold del manifest un file di effetti con sha256, l'elenco con hash delle tabelle **realmente lette**,
   le statistiche apprese con le righe da cui vengono, la prova di parità del ramo nullo;
3. gli effetti di produzione (hidden vuoto) con manifest, ottenuti dallo stesso codice dei fold tolte le esclusioni;
4. per pesi o memorie esterne una **scheda di esposizione**: dataset di training, validazione, selezione e
   calibrazione, linee e bersagli visti, rapporto con H1 e con ogni lignaggio dei fold. Ignoto vale non ammissibile.

Per i bracci dello stadio 100 VALIDAZIONE **ricalcola i fold dalla release** con il proprio banco e confronta gli
hash con quelli consegnati: la previsione valutata è quella prodotta dal codice di produzione, non una copia.

## 4. Controlli disponibili in inferenza

Solo cellule non perturbate del contesto di destinazione: profilo basale, profondità, dispersione. Il transfer
T0/T1/T2 **non usa il contesto negli effetti** (gli effetti di A, B e C hanno lo stesso sha256): i controlli
entrano solo nel generatore. Un candidato che usa i controlli negli effetti lo dichiara e passa il controllo di
dipendenza dal contesto (§7).

## 5. Emettitore, campionamento e semi

Livello B: [bench_v2.py](../../generatore_e_banchi/banco_v2_2026-10-04/bench_v2.py) senza modifiche, emissione
`t28`, 400 cellule previste per bersaglio, cinque semi (20260912, indici 0–4), un flusso casuale per (seme,
bersaglio) condiviso fra i bracci, metà verità e replicato al seme 2026. Un cambio di generatore si misura a parte,
a effetti fissi.

## 6. Metriche, aggregazioni, risultati per contesto

**Livello B, sei membri con lo scorer vero:** PDS (`pds_cosine`), MSE (`expr_mse_unbiased_capped_norm`), NMAE
(`de_wilcoxon_lfc_nmae`), FID (`de_wilcoxon_direction_fidelity_yield_raw`), REACH
(`de_wilcoxon_direction_reach_raw`), JAC (`de_wilcoxon_sig_jaccard`). Si riportano grezzi, scalati locali e
denominatori; media dei sei e dei cinque senza JAC; un risultato per fold e la macro-media a peso uguale sui fold.
Sono punteggi **locali**, su ancore locali e verità a metà profondità: non sono punteggi VCC e danno il verso, non
l'entità (CP-0052).

**Livello A, spazio degli effetti, per bersaglio** (proxy; previsione contro la tabella di verità del fold, colonne
dei 300 geni bersaglio escluse come in `multisource.transfer_report`):

| Misura | Definizione | Ruolo |
|---|---|---|
| `disc` | 1 − rango normalizzato della propria verità fra tutte le verità, per coseno, sui geni validi per tutti i bersagli confrontati | **primaria**: discriminazione fra bersagli |
| `r_spec` | correlazione di Pearson dopo aver tolto la media sui bersagli a previsione e verità | **primaria**: componente specifica |
| `sign50`, `reach` | accordo di segno nei primi 50 geni previsti e profondità a purezza 0,9, fra i geni con \|z\| ≥ 3 nella verità | secondarie |
| `nmae_conf`, `mse_ratio` | errore assoluto sui geni con \|z\| ≥ 3 e errore quadratico, rapportati alla previsione nulla (< 1 è meglio di zero) | secondarie, dipendono dall'ampiezza |
| per braccio | quota comune ‖media sui bersagli‖² / media ‖riga‖², ampiezza ottima, coseno fra medie, effetto sul proprio gene | diagnostiche |

Intervalli del livello A: bootstrap appaiato **sui bersagli** (10.000 ricampionamenti, seme 20261008, percentili
2,5–97,5), per fold; macro = media a peso uguale dei delta medi per fold, con ricampionamento stratificato per
fold. «Risolto» = l'intervallo esclude 0. Si riporta anche il sottoinsieme dei **bersagli cambiati** fra i due
bracci, accanto a tutto il fold. Livello B: «risolto» = \|media\| > 2·sd/√5 sui delta appaiati per seme (CP-0065).

Tre fonti di variabilità restano distinte: i semi misurano il **generatore** a verità e modello fissi; il bootstrap
misura la variabilità **fra bersagli** dentro i contesti osservati; l'incertezza della **generalizzazione** a
contesti nuovi ha come unità il lignaggio (sei fold, non indipendenti da ogni scelta passata) e nessun intervallo
qui la copre. Una cellula non è mai una replica biologica.

## 7. Matrice dei confronti e controlli

| Contrasto | Bracci | Che cosa isola |
|---|---|---|
| K0 | T0 − P4 | più linee a tabelle e modello fissi; si legge accanto al delta ufficiale t36 − t28, che non è lo stesso contrasto |
| K1 | T1 − T0 (e R1 − T0) | banca ampliata a modello invariato |
| K2 | T2 − T1 | centratura sui bersagli del training, stessa banca |
| K3 | (T0 + E) − T0, oppure (T1 + E) − T1 | componente esterna sulla stessa base, con ripiego fuori supporto |
| K4 | (T2 + E) − T2 contro K3 | combinazione: interazione fra centratura e componente esterna |
| G | stessi effetti, emissione nuova − t28 | il generatore, solo se un candidato lo cambia |

Controlli eseguiti dal banco, scelti sul meccanismo dei fallimenti di STRADE: **bersagli permutati** (le righe
della previsione scambiate: `disc` deve andare a 0,5, altrimenti il banco non vede la specificità ed è invalido);
**previsione nulla** e **sola media** (ogni bersaglio riceve la media del braccio: quanto dei membri d'ampiezza
viene dalla parte comune, S-006); **gamma 0** (nessuna sottrazione della risposta comune) e **senza cis** su T0;
**assenza fisica** delle tabelle escluse dalla cache di ogni fold, verificata sull'elenco dei file letti dallo
stadio 100; **parità**: gli effetti senza esclusioni devono riprodurre gli sha256 registrati di T0 e R1. Per una
componente esterna: dipendenza dal contesto (controlli di un altro lignaggio al posto di quelli del fold),
ampiezza, quota comune e comportamento del ripiego, sul supporto comune e sul pannello intero.

## 8. Criteri di confronto, adozione e interruzione

Fissati qui, prima dei numeri; non si applicano a ritroso a t36 o t30.

- **INVALIDO:** manifest o hash mancanti o diversi; una tabella o una statistica del lignaggio escluso letta nel
  fold; bersagli nascosti presenti in una fonte o in un derivato (T/J); parità del ramo nullo fallita; previsione
  valutata diversa da quella esportata; esposizione dei pesi ignota; H1 test letta.
- **VALIDO E FAVOREVOLE**, tutte insieme: (a) livello B eseguito su almeno due fold, macro-media del delta dei sei
  membri > 0 e risolta, stesso segno senza JAC; (b) nessun fold con delta dei sei membri o del PDS risolto
  negativo; (c) livello A: nessun fold con `disc` risolto negativo e macro di `disc` non risolta negativa.
- **VALIDO E SFAVOREVOLE:** macro dei sei membri risolta negativa, oppure un fold con regressione risolta della
  media o del PDS nel livello B, oppure macro di `disc` risolta negativa nel livello A.
- **INCONCLUDENTE:** ogni altro caso, compreso il livello B mancante o non risolto alla scadenza.

**Solo un esito favorevole promuove un candidato rispetto a T0.** Con esito inconcludente o sfavorevole la consegna
resta t36. Il livello A da solo può fermare, non promuovere (CP-0041). C e J si leggono separati (D-050): un
guadagno in C si adotta per C solo se il ramo J resta quello del riferimento. Una raccomandazione scientifica non è
un'autorizzazione all'invio.

## 9. Precedenti

- **S-010** (fonti del transfer): l'ampliamento è stato letto finora su un invio e su banchi non ammessi. Qui K0 e
  K1 separano le linee aggiunte dal resto, a modello e tabelle fissi, su fold con esclusione fisica.
- **S-006** e **S-009** (parte comune che copre lo specifico; banco diverso dall'esportazione; media che nasconde
  il PDS): le misure primarie sono la discriminazione e la componente specifica per bersaglio; la quota comune è
  riportata per ogni braccio; il banco ricalcola la previsione con il codice di produzione; la guardia sul PDS
  vale per ogni fold.
- **S-001**, **S-002** (reti senza discriminazione): il controllo a bersagli permutati e la sola media dicono se un
  guadagno è specifico prima di guardare la media dei membri.
- **S-003** (miscele a posteriori): nessun peso di miscela si sceglie sulla verità del fold valutato.
- ERRORI, «Errori di metodo»: proxy a due membri (CP-0041), indice locale letto come guadagno in gara (CP-0052),
  riserva già valutata chiamata indipendente (CP-0050), differenze sotto il rumore (CP-0065).

**Segnale precoce e arresto:** se la parità di T0 o R1 fallisce, o il controllo a bersagli permutati non porta
`disc` a 0,5, il banco è invalido e nessun confronto si legge. Una tabella esclusa trovata fra i file letti ferma
il fold. Un candidato con `disc` risolto negativo su un fold non passa al livello B senza una diagnosi.

## 10. Copertura D-053 e limiti

Questo banco usa le tabelle di effetti della release (28 unità di banca su 45 dietro le fonti lette): non è il
corpus completo e non misura l'uso dei campioni cellulari. I fold coprono sei lignaggi con bersagli del pannello;
gli altri restano fonti. Le sei linee sono fonti di ogni ricetta dal 22 settembre: il banco è **sviluppo**, non
conferma indipendente. La verità del livello A è una tabella di effetti aggregati, con il suo rumore; il livello B
esiste solo dove ci sono cellule vere verificate per i bersagli del pannello.
