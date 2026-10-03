# Rete ancorata versione 4: pilot tecnicamente valido sul corpus a 8 gruppi

**Stato: congelato** con il commit che contiene questo testo, il 3/10/2026 sera, prima di ogni training v4.
Scritto da Claude Code, sessione «Integrazione Codex e piano operativo» (`5eacdf`), programma
[R-LEAD](../../../docs/piani/strategia-scientifica.md). Da quel commit regola, bracci e soglie non cambiano; un difetto
trovato dopo si corregge con un emendamento datato, scritto prima di leggere i risultati, come nel §9 della v3.

## 0. Che cosa è e che cosa non è

È un **pilot dichiarato** (D-053, [GENERALIZZAZIONE §2.1](../../../docs/GENERALIZZAZIONE.md#21-copertura-integrale-vincolo-non-negoziabile)):
- **sottoinsieme:** le cellule degli 8 gruppi del corpus r3/v3 (A549, H1, HepG2, Jurkat, K562, RPE1, iPSC, neuroni da
  iPSC), con le tre linee escluse intere H1, HepG2 e RPE1;
- **domanda:** la stessa della v3 (§1), su un percorso dei dati corretto;
- **lacune:** le cellule di CD4T, HCT116 e HEK293T (ingestione in parte conclusa, non verificata per intero) e quelle
  delle altre voci del catalogo (DLD-1, Hs27, Calu-3, THP-1, Melanoma_Frangieh2021, PrimaryT_Shifrut2018, MCF7, HT29,
  HAP1, BxPC3) non entrano. Gli aggregati di CD4T, HCT116, HEK293T e della tabella VIPerturb di K562 entrano invece nelle
  ancore, il ruolo consentito ai soli aggregati.

Non è l'addestramento su tutte le linee e non lo sostituisce. Se passa, il passo successivo è lo stesso protocollo sul
corpus ampliato (§7).

## 1. Domanda

Una rete addestrata sui conteggi delle singole cellule, che parte dal transfer delle altre linee (l'ancora) e impara
solo una correzione, prevede meglio della sua ancora sulle linee escluse intere?

## 2. Che cosa cambia dalla versione 3, e perché

Il modello è quello della v3 ([protocollo v3](../rete_ancorata_2026-10-03/PROTOCOLLO.md) §2):
logit = β_k + g_θ · a(L, t) + Δ_θ, con g = 1 + tanh(·) e Δ limitata, entrambe a zero all'inizio. Cambiano cinque cose,
ognuna con la sua prova e i suoi test (README di questa cartella):

| Cambio | Perché | Evidenza |
|---|---|---|
| Batch bilanciati: ogni passo contiene la quota di ogni gruppo di linea (1/G) e di ogni studio nel gruppo; peso della loss 1 per ogni cellula | Il campionatore a epoche della v3 bilancia solo su epoche intere: H1 si è fermato a 0,714 epoche senza leggere `tian2021_crispri` (Neuron 0,7% della loss invece di 14,3%) | [diagnosi_r1/DIAGNOSI.md](diagnosi_r1/DIAGNOSI.md) |
| Budget separati di training (150 min) e valutazione (90 min) | La riserva stimata da una sonda (6.323 s) ha tolto a H1 circa 88 minuti di training per una valutazione di circa 1.066 s | diagnosi, §3 |
| Lettura dai gemelli compatti degli shard (stesse righe e conteggi, zstd invece di gzip-4) | La GPU calcola un passo in circa 66 ms e aspettava i batch per l'81–84% del tempo; la decompressione gzip è il collo di bottiglia misurato | diagnosi, §4; `test_train_v4`: stessi batch e parametri da shard e gemelli |
| Medie delle tabelle del regime J nelle ancore | Le medie del regime C contenevano le risposte dei bersagli nascosti (rilievo P1 di Codex, emendamento §9 della v3) | `test_anchors_v4` |
| Fonti delle ancore: tutte le tabelle aggregate del cubo (regola `all`) | D-053: ogni contesto idoneo nel ruolo consentito dai dati; proposta 1 dell'[analisi Codex](../../analisi/candidato_ibrido_2026-10-03/README.md) | §8 per ciò che già si sapeva |

Non cambiano: corpus, stati dei pre-passi r1 (sha256 sotto), gruppi di linea, fold nascosta (hash fold 0 di 5, 2.079
simboli), serbatoio dei controlli, stimatore dello spostamento, architettura, cubo del banco, generatore trial-01,
cellule vere e bersagli della corsia B, metriche.

| Linea esclusa | Stato del pre-passo (`rcell-prepass-<linea>-r1`) | Cellule di training ammesse | Gruppi di valutazione C/J/T |
|---|---|---:|---|
| H1 | `0e67592be6cb59131e6365614df14f00931de38927172b1d051ab9fbdfe47358` | 3.850.952 | 151 / 49 / 279 |
| HepG2 | `572e74248a1f5d9103a390b815021af84024c2c1c18225f2ea9192d2f2b391df` | 3.970.762 | 1.748 / 412 / 279 |
| RPE1 | `31247004cf926484471a0476ed0272e16a5d708df021c6a1cb8e468a56d372bd` | 3.887.913 | 1.794 / 410 / 279 |

## 3. Ancore

`anchors.py` della v4, regola `all`, rango di proiezione 32, kernel `rcell-v4-anchors-r1`, cartelle
`anchors_<linea>_all/`. Per una cellula di training della linea L le fonti sono i gruppi del cubo tranne L e la linea
esclusa H; per le righe C di H, tutti tranne H (al più 9 gruppi: CD4T, H1, HCT116, HEK293T, HepG2, Jurkat, K562,
Neuron, RPE1, iPSC, meno H). Solo le cellule CRISPRi ricevono l'ancora, come nella v3. Le medie sottratte escludono
ogni riga di un bersaglio nascosto, da ogni tabella. Lo stesso kernel scrive anche le regole `cells` (la v3, con medie
J) e `production` (le tabelle della ricetta t22/t25), che servono solo come riferimenti dei confronti (§6).

## 4. Bracci e argomenti

Un processo per linea esclusa, sugli stessi batch e dagli stessi pesi iniziali:

| Braccio | Contesto | Ruolo |
|---|---|---|
| `ancorata` | `cells`, codice `both` | il candidato |
| `ancorata_mean` | `mean`, codice `both` | gemello senza informazione di stato |
| `ancora_sola` | nessuna correzione (g = 1, Δ = 0), solo in valutazione | l'ancora passata per lo stimatore della rete |

`--epochs 2 --batch 256 --ctrl-k 64 --min-own 8 --dim 128 --rank 128 --lr 1e-3 --pi-floor 0.01 --seed 0 --workers 2
--roles 2 --eval-workers 3 --checkpoint-minutes 15 --delta-bound 6 --gate-mode off --health-check-step 5000
--health-window 5 --sampler balanced --unit-buffer 2 --share-window 500 --share-tolerance 0.02 --time-every 50
--train-budget-minutes 150 --eval-budget-minutes 90 --reserve-export-minutes 5`, con `--fast-roots` sui tre kernel dei
gemelli (`rcell-v4-fast-{a,b,c}-r1`). Con i batch bilanciati `--epochs 2` vuol dire 2 × le cellule ammesse estratte
in tutto (circa 30.000 passi), come i due epoch della v3; le epoche di ogni unità sono nella ricevuta. GPU T4×2 su
`davideferrante11`; un kernel per linea (`rcell-v4-train-<linea>-r1`), H1 e HepG2 insieme, RPE1 appena una sessione
GPU si libera.

## 5. Accettazione tecnica

Una linea è accettata se tutte queste condizioni valgono; altrimenti il confronto è **incompleto**, non fallito:
- codice d'uscita 0; nessun gemello diverso dal manifest (`verify.json`); nessuna cellula di classe diversa da
  `train` estratta;
- `exposure.json` passato: in ogni finestra completa di 500 passi e sull'intera corsa ogni gruppo attivo entro ±0,02
  da 1/G, ogni unità attiva estratta;
- prova di salute al passo 5.000 passata; valutazione completa entro il suo budget;
- manifest delle ancore con regime J, controlli passati, nessuna riga di un bersaglio nascosto.

## 6. Misure

**Corsia A** (`bench_effects.py` di questa cartella): le righe C e J del cubo della linea esclusa, indici del banco
(PDS, coseno, coseno specifico, rapporto MSE, segno). Bracci: `ancorata`, `ancorata_mean`, `ancora_sola`; riferimenti
con medie J: `transfer_all_J` (la definizione dell'ancora), `transfer_cells_J`, `transfer_prod_J`; risposta generica.

**Corsia B** (`lane_b.py` di questa cartella): le stesse cellule vere e gli stessi bersagli della corsia B r3
(`out_gen_<linea>_r3/real_cells.npz`, `targets.json`), i sei membri in scala locale (PDS, MSE, NMAE, FID, REACH,
JAC). Effetti passati per il generatore trial-01: `ancorata_shift`, `ancorata_mean_shift`, `ancora_sola_shift`,
`transfer_all_J`, `transfer_cells_J`, `transfer_prod_J`; più le cellule generate dalle reti `ancorata` e
`ancorata_mean` (`generate_cells.py`, con le ancore).

## 7. Regola (si congela con il commit)

**Primaria, corsia B:** Δ = `ancorata_shift` − `transfer_all_J` sulla media locale dei sei membri. Passa se Δ > 0 in
almeno 2 linee accettate su 3 e la media delle tre è > 0.

**Guardia, corsia A:** la media sulle tre linee del PDS delle righe C, `ancorata` − `transfer_all_J`, è ≥ −0,02. Se la
primaria passa e la guardia no, l'esito è «non concluso».

**Secondarie, riportate senza soglia:** `ancorata` − `ancora_sola` e `ancorata` − `ancorata_mean` in entrambe le
corsie; `ancorata` contro `transfer_cells_J` e `transfer_prod_J` (il riferimento di produzione sulle stesse righe);
`transfer_all_J` − `transfer_cells_J` (il valore delle fonti aggregate aggiunte); cellule generate contro cellule
vere; righe J (ora pulite, comunque secondarie); i membri uno per uno; ricevute di esposizione e tempi.

**Esito e passo dopo:**
- accettazione completa, primaria e guardia passate: lo stesso protocollo sul corpus ampliato (prima CD4T, HCT116,
  HEK293T con cellule verificate), con la stessa regola, poi la conferma del programma (P5);
- primaria non passata: nessuna ritaratura su queste tre linee, che da quel momento sono lette; un nuovo candidato
  richiede un nuovo protocollo. La famiglia di modelli non è per questo bocciata.
- una o più linee non accettate: confronto incompleto; si corregge il difetto tecnico e si ripete soltanto la linea
  non accettata, con slug e output nuovi.

## 8. Che cosa si sapeva al congelamento

- Dei training v3 r1 sono state lette soltanto ricevute tecniche: i log sono stati scaricati senza le righe di
  valutazione ([fetch_r1_logs.py](diagnosi_r1/fetch_r1_logs.py)); `eval.json` e gli spostamenti esportati non sono stati
  aperti. RPE1 v3 non è mai stato lanciato.
- Pilot r3, già letto, corsia A, righe C (misurato): `transfer_all` supera `transfer_cells` nel PDS su tutte e tre le
  linee (+0,032 H1, +0,011 HepG2, +0,020 RPE1) con rapporto MSE più basso. Corsia B a sei membri (misurato):
  `transfer_all` sta sotto `transfer_cells` di 0,007, 0,035 e 0,007 nella media locale, per meno chiamate e meno
  REACH. Allora le medie erano del regime C e il `transfer_cells` della corsia B comprendeva VIPerturb. L'attesa a priori
  su quale ancora renda di più è quindi incerta; la regola confronta la rete con la propria ancora.
- Miscele r3: non promettenti (v3 §8). La correzione appresa partendo dall'ancora resta un'ipotesi diversa.

## 9. Che cosa non si fa

Niente ESM2, niente corpus ampliato, niente generatore diverso in questo pilot. La riserva H1 test resta chiusa. I
risultati della v3 r1 restano non letti fino alla lettura della v4 e non entrano nella regola.
