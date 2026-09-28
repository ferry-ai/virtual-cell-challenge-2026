# La prova generale del 22 ottobre: protocollo e regole (azione 3 di R-REV, F8 di R-V2)

28 settembre 2026. Scrive Claude (app desktop, sessione `f2abd9a6`); orari letti da `date`. Schede:
[R-REV](../../../docs/piani/revisione-critica.md), azione 3; [R-V2](../../../docs/piani/modello-v2.md), F8;
[revisione](../../analisi/revisione_criticita_2026-09-28/REVISIONE.md), §2.4 e §3.4. Il piano viene da un sottoagente
di questa sessione che ha letto il codice senza eseguire nulla; rivisto qui.

**Protocollo fissato alle 20:00 del 28/09, prima di girare.**

Etichette: **misurato**, **interpretazione**, **ipotesi**, **proposta**; **[C]** vuol dire verificato nel codice.
Nessun numero qui è un punteggio VCC, e nessun file di questa prova si carica sul server.

## La domanda

Dal pacchetto del 22/10 (tre contesti con i soli controlli, 300 bersagli nuovi) la ricetta del t22 arriva a un `.vcc`
che lo stadio 48 convalida e verifica? Dove dipende ancora da A/B/C o dal loro pannello? Quanto tempo, disco e memoria
chiede ogni passo?

## Il materiale

- **Contesti finti.** Copie di `raw/controls/context_{A,B,C}.h5ad` in `raw/controls_prova_2026-09-28/` nella radice
  dati, rinominate D, E, F con una permutazione estratta dal seme (scritta in `manifest.json`). Nella copia si riscrive
  solo l'etichetta `obs/context`. Copia vera, mai un collegamento. Gli originali: sha256 prima e dopo, identici.
- **300 bersagli finti.** Seme 20261022, strati estratti in quest'ordine:
  - 30 del pannello di oggi (P3);
  - fuori dal pannello e sull'asse: 120 coperti da tutte e quattro le sorgenti del t22, 50 da tre, 40 da due, 30 da
    una (P1);
  - 30 da nessuna (P0).

  Il pannello finto è volutamente più povero di quello vero (236 su 300 coperti da quattro sorgenti), per provare i
  ripieghi dello stadio 100. Elenco in `bersagli.csv`.
- **Sorgenti.** Le cache del pannello si ricavano dagli universi, non dagli stadi 97/102/98: K562 del 26/09, CD4 e
  Orion `_me1`. È la regola del t25: la correzione entra nelle cache costruite da qui in avanti.
- **Ricetta.** `ricetta_t22_DEF.json`: il t22 con le chiavi D, E, F e nient'altro di diverso.

## Scritto prima di girare

**γ = 1 e la cache [C].** Con γ = 1 lo stadio 100 toglie a ogni sorgente, gene per gene, la media dello `shrunk` su
tutti i bersagli della sua tabella nella cache (`multisource.AxisTable.common`). Con una cache del pannello sono i
bersagli del pannello che quella sorgente misura, quindi con un pannello nuovo il vettore tolto cambia. Misurato per il
solo K562: media sul pannello (272 bersagli) contro media sull'universo (9.866), coseno 0,63.
- Per la prova si usa la cache del pannello nuovo (G-a): è ciò che il §7 di LAVORO farebbe con gli stadi 97/102/98.
- La media congelata di r9 (G-b) e la media sull'universo (G-c) si misurano soltanto, e non entrano negli effetti.

**Ampiezza.** Si genera a 1,576, la ricetta del t22 invariata. La regola candidata, calcolabile dai soli controlli, è
**R-B**: una sola ampiezza per D/E/F tale che la media sui tre contesti della mediana dei geni rilevabili eguagli
quella di A/B/C a 1,576.
- I geni rilevabili si contano come in `match_detectable`: soglia 4/√(400 μ), geni ≥ 5 CPM, testa cis fuori dalla
  scala.
- Si calcola sugli effetti del t22 del pannello di oggi.

Si riportano anche R-C (con gli effetti nuovi), R-D (per contesto) e R-E (con la profondità dei controlli). Quale
adottare lo decide il banco dell'azione 4, non questa prova.

## Previsioni registrate

1. Lo stadio 48 con vcc-cli 0.2.0 rifiuta D/E/F («Unknown context label(s)»): il difetto D1 qui sotto.
2. Lo stadio 45 scrive `pilot: True` per una corsa D/E/F.
3. **Parità:**
   - le cache assemblate per il pannello di oggi coincidono con r5 (dagli universi del 26/09) e con r9 (dagli
     universi `_me1`): 0 differenze in raw, SE, shrunk e cellule per K562 e Orion, al massimo 2e-8 per `cd4_mix`;
   - gli effetti dello stadio 100 su quelle cache coincidono con quelli del t22 e del t25 entro 1e-6, con la stessa
     maschera `observed`.
4. **Copertura:** 270 bersagli su 300 con effetti in almeno una sorgente (P1 e P3), 0 su 30 in P0. In P0 il gene
   bersaglio stesso ha effetto 0.
5. R-B sulle copie di A/B/C restituisce 1,576 ± 0,001.
6. **Controllo negativo:** lo stadio 100 con i bersagli finti sulla cache r9 finisce con codice 0 e circa 30 bersagli
   coperti.

## Che cosa si misura

- **Per ogni stadio** (`tempi.jsonl`):
  - orario UTC di inizio e fine;
  - codice d'uscita;
  - picco di memoria del processo;
  - disco libero prima e dopo;
  - in più, il picco di disco dello stadio 48.
- **Poi:**
  - la copertura per strato e le righe tutte zero;
  - la diagnostica di γ (G-a, G-b, G-c);
  - i valori di R-B, R-C, R-D e R-E;
  - ogni punto in cui la pipeline dipende ancora da A/B/C.

## Difetti attesi dalla lettura del codice

Ciascuno si corregge con il suo test quando la prova ci arriva.

| # | Difetto [C] | Correzione minima | Test |
|---|---|---|---|
| D1 | Lo stadio 48 non ha `--contexts`, e vcc-cli 0.2.0 fissa A/B/C (`vcc/prep.py:54`; `src/vcc2026/packaging.py:457-459`) | `--contexts` nello stadio 48, passato come `required_contexts`; senza, come oggi | un h5ad minuscolo D/E/F fallisce senza e passa con; A/B/C invariato; confronto prima/dopo su un pilota |
| D2 | Stadi 98 e 100 leggono la prima colonna del file del pannello per posizione | un aiuto che legge `target_gene` per nome, senza doppioni | file nudo, con `n_cells`, con `context` e doppioni: stessi 300 bersagli |
| D3 | Chiavi della ricetta e contesti del pacchetto non si controllano fra loro | lo stadio 100 rifiuta una ricetta con chiavi diverse da `--contexts` | la ricetta D/E/F ha le stesse specifiche del t22 |
| D4 | Una cache costruita per un altro pannello dà una previsione quasi nulla senza errore | il manifest della cache registra lo sha256 dei bersagli; lo stadio 100 rifiuta una discrepanza e zero bersagli coperti | cache e bersagli sintetici; il controllo negativo lo mostra |
| D5 | Una corsa D/E/F vera è marcata `pilot` (`45:283-284`) | accettare `contexts_test` | `is_pilot` falso per D/E/F a 300 × 400 |
| D6 | LAVORO §7 scrive `--contexts D,E,F` per lo stadio 76, che vuole valori separati da spazi | correggere il testo | — |
| D7 | Un bersaglio che nessuna sorgente copre non riceve il silenziamento del proprio gene | proposta: un blocco facoltativo `"self"` nella ricetta; non entra nel t22 | un bersaglio sintetico scoperto riceve il prior sul proprio gene |
| D8 | Nessun codice vivo scrive i CPM di D/E/F, e il conteggio dei rilevabili vuole un riferimento sullo stesso pannello | un'opzione che scrive i CPM sull'asse, e `"amplitude_rule"` nella forma R-B | CPM di A/B/C uguali a `interim/basal_cpm_by_context.csv`; R-B su A/B/C dà 1,576 |
| D9 | La media tolta da γ dipende da ciò che la cache contiene, e nulla lo dice | chiave `"common"` nella ricetta | «panel» riproduce l'uscita di oggi |
| D10 | Nessuno stadio vivo costruisce una cache del pannello dagli universi | uno stadio nuovo che la assembla | universi sintetici nei due formati di indice |
| D11 | Provenienza incompleta: lo stadio 98 non scrive un manifest, il 100 non registra il file dei bersagli | aggiungere i campi | le chiavi del manifest ci sono |
| D12 | Le riserve di disco degli stadi 45 e 48 chiedono circa 17 GB liberi, non i 13 del §7 | correggere LAVORO §7 | — |
| D13 | Le uscite degli stadi 85 e 99 vanno sotto `reports/` per default: rischio di identità | una riga di procedura: uscite di D/E/F nella radice dati | — |

## Forma e risorse

- **400 cellule per bersaglio** se all'inizio ci sono almeno 17 GB liberi. Altrimenti 40, con
  `pert_counts_n40.csv` per lo stadio 48. Le durate a forma piena degli stadi 45 e 48 restano quelle misurate sul t22
  (1.309 s e 1.009 s).
- **Misurato alle 19:53:** C: ha 2,7 GB liberi; il file di paging è cresciuto a 20,3 GB. Alle 19:54 sono andati nel
  Cestino 25,3 GB di file rigenerabili (t18, t19, t20: [autorizzazioni](../trial_2026-09-22/autorizzazioni.md)). Lo
  spazio torna quando il proprietario svuota il Cestino.
- Si parte dopo la lettura della regola di r1, che tiene occupata la CPU (LAVORO §2: un lavoro pesante alla volta).

## Regola di chiusura

- La prova **riesce** se un `.vcc` di D/E/F sui bersagli finti passa convalida, impacchettamento e verifica dello
  stadio 48.
- Ogni arresto è un difetto. Si corregge con il suo test, e lo stadio che decide l'invio con un confronto prima/dopo
  su un pilota; poi si riprende dal passo fermo.
- Le previsioni 1–6 si leggono come scritte: una che non si avvera si riporta, non si corregge dopo.
- Nessun invio, nessun download. Il `.h5ad` e il `.vcc` della prova vanno nel Cestino dopo le misure, con sha256 e
  dimensioni nel report. Le uscite degli stadi 85 e 99 restano nella radice dati.

## Limiti

D, E ed F sono copie di A, B e C: la prova non dice nulla sul punteggio né su contesti davvero nuovi. Il pannello
finto non è quello degli organizzatori: la copertura vera si misura il 22/10.
