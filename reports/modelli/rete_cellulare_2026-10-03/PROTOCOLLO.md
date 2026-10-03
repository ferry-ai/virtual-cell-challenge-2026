# Pilot della rete cellulare v2: protocollo e regola, scritti prima di ogni training

3 ottobre 2026, notte (ora del commit che congela questo file), Claude Code, sessione `22d21f`, programma
[R-LEAD](../../../docs/piani/strategia-scientifica.md) dopo P3/P4 ([CP-0056](../../../docs/checkpoints/0056-banco-contesto-c-j.md)).
Mandato del proprietario in chat (3/10): rete addestrata sulle cellule, non sul pseudobulk; correzioni dei difetti
dell'audit e test subito; poi un **pilot** su più linee escluse intere, con un confronto senza informazione sullo stato
e una valutazione diretta delle cellule; espansione secondo una regola fissata prima. Nessun numero di questo pilot
esiste mentre scrivo.

## 1. Domande

1. **Stato (Q1).** I controlli della linea nuova, letti cellula per cellula, aggiungono qualcosa rispetto al loro
   profilo medio? Il confronto è con un gemello identico che vede solo la media delle stesse cellule di controllo.
2. **Rete contro transfer (Q2).** Sui bersagli già visti altrove (classe C), la rete prevede l'effetto medio meglio
   del transfer del t25 calcolato con le stesse informazioni?
3. **Bersaglio (Q3, controllo di sanità).** La rete usa l'informazione sul bersaglio? Il confronto è con un braccio
   generico che non ne riceve nessuna.

Che cosa **non** dice una risposta positiva a Q1: che la rete abbia imparato la risposta di uno stato cellulare.
L'architettura codifica ogni controllo e poi media gli embedding; il decoder non ha un percorso che trasformi lo stato
di una cellula nella sua risposta, e controlli e perturbate sono popolazioni non appaiate. Q1 dice soltanto se la
distribuzione dei controlli porta informazione oltre la media. Un percorso esplicito stato → risposta sarebbe un'altra
architettura con una verifica dedicata. `pi` resta un parametro statistico della miscela, non una quota di knockdown
falliti.

## 2. Codice e correzioni

Codice: questa cartella, versione 2 di `train_cellnet.py`, `cellnet.py`, `cell_data.py` (copie di
`risposta_biologica_2026-09-30`, originali intatti). Le correzioni dell'audit dell'1/10 e i loro test sono in
[DIFETTI.md](DIFETTI.md); al commit di questo protocollo passano 18 test unitari, 8 end-to-end della versione 2 e i 51
della versione 1.

## 3. Dati

- **Corpus:** i dataset `rlab-*` del terzo training (pre-passo r7), letti dall'account `davidmaisterx` e condivisi in
  lettura con `davideferrante11`: HepG2 e Jurkat (Nadig), H1 train e validation (gara 2025, un solo studio), K562 GW e
  essential (Replogle), RPE1 (Replogle), A549 (KO), Norman 2019 (CRISPRa, K562) e Tian 2021 (neuroni, CRISPRi e CRISPRa),
  KOLF2.1J (tre schermi), HipSci mirato. Restano fuori, come in r7: HipSci genome-wide (1–5 NTC per linea), Tian 2019
  (droplet non filtrati), Southard (non pubblicato), lo split di test di H1 (riserva chiusa), Tahoe, KOLF pan-genome.
- **Gruppi di linea:** [line_groups.json](line_groups.json). iPSC unisce KOLF2.1J e le linee HipSci, come il banco.
- **Linee escluse intere, una per training:** **H1** (saggio Flex della gara), **HepG2** (sviluppo, confrontabile con
  r1–r3) e **RPE1** (linea immortalizzata non tumorale). K562 resta nel training: escluderla toglierebbe GW, cioè metà del
  corpus, e la sua valutazione sarebbe la più costosa.
- **Bersagli nascosti (J):** fold 0 di 5 dell'hash R-LEAD sulla chiave riconciliata (`target_keys.py`, stesso sale del
  banco).

## 4. Bracci e training

Un processo per linea esclusa; i tre bracci vedono gli stessi batch e partono dagli stessi pesi:

| Braccio | Codice del bersaglio | Contesto | Ruolo |
|---|---|---|---|
| `cells` | `both` (identità, a zero per i bersagli mai addestrati, più descrittori) | cellule | il candidato |
| `mean` | `both` | profilo medio delle stesse cellule di controllo | gemello senza informazione di stato (Q1) |
| `generic` | `generic` (nessuna informazione sul bersaglio) | cellule | risposta generica addestrata (Q3) |

Argomenti comuni: `--epochs 2 --budget-minutes 180 --batch 256 --ctrl-k 64 --min-own 8 --dim 128 --rank 128 --lr 1e-3
--pi-floor 0.01 --seed 0 --workers 3 --eval-workers 3`. Pre-passo: `--pool-size 2048 --ctrl-k 64 --input-genes 2048
--eval-min-cells 20 --eval-max-cells 150 --eval-max-groups-t 300 --hidden-fold 0 --same-experiment
h1_vcc2025=h1_vcc2025_train,h1_vcc2025_val`. Pre-passo su CPU, training su GPU T4×2 (`davideferrante11`). Nessun ciclo
di ripresa: la ripresa è provata dai test locali.

## 5. Misure

**Corsia A: effetti medi.** Per ogni linea esclusa, i bersagli C e J con almeno 20 cellule ammesse, sulle righe del
cubo del banco (`cube_r2`) della stessa linea (H1: `h1_train`, `h1_val`; HepG2: `hepg2_nadig`; RPE1: `replogle_rpe1`).
La verità è il fold change logaritmico del cubo, la stessa per ogni braccio. Le previsioni sono:

- lo spostamento previsto di ogni braccio (`eval_shifts.npz`, stimatore `cell_data.shift`);
- per le righe C, il transfer del t25 dal cubo con le **stesse informazioni** (sorgenti: i gruppi del corpus cellulare
  meno quello escluso) e con **tutte le sorgenti** del banco;
- la risposta generica pseudobulk.

Indici: `metrics.score_table` del banco (PDS a blocchi, coseno pesato, coseno specifico, MSE relativo, segno sui geni
significativi).

**Corsia B: cellule.** Le cellule generate da ciascun braccio (miscela NB con baseline dai controlli della linea
esclusa) e quelle del transfer passato per il generatore dello stadio 45, contro le cellule vere, con lo scorer a sei
membri. Va implementata dopo questo protocollo; la regola è fissata ora e si applica dove la corsia è calcolata
(prima HepG2, le cui cellule sono in locale).

## 6. Regola, fissata ora

**Accettazione tecnica di ogni training** (altrimenti il training è da ripetere, non una prova):
- codice di uscita 0;
- `verify.json` senza shard diversi;
- `coverage.json` con la non-contaminazione passata;
- quote della loss per gruppo entro ±0,02 da 1/G;
- valutazione completa entro il budget.

Un braccio è **collassato** se `pi_q50` delle perturbate vale meno di 10⁻³ nell'ultimo passo registrato. Un confronto
che coinvolge un braccio collassato è un fallimento tecnico, non un risultato negativo.

**Q1 (stato), primaria:** Δ = `cells` − `mean` sul PDS della corsia A, righe C. Passa se la media delle tre linee è
> 0 e Δ > 0 in almeno 2 linee su 3. Riportati anche coseno specifico, coseno, MSE relativo, segno e le righe J.

**Q2 (transfer):** Δ = `cells` − transfer con le stesse informazioni, sul PDS della corsia A, righe C. Stessa soglia:
media > 0 e almeno 2 su 3. Il confronto con tutte le sorgenti è riportato.

**Q3 (bersaglio):** Δ = `cells` − `generic` sul PDS, righe C: deve essere > 0 in media. Se non lo è, la rete non usa il
bersaglio e Q1 e Q2 si leggono come non interpretabili.

**Corsia B:** gli stessi confronti sul punteggio locale a sei membri, dove calcolato, con la stessa soglia.

**Espansione** ai sette gruppi del banco con cellule (H1, HepG2, RPE1, K562, iPSC, Jurkat, Neuron), con gli stessi
bracci, se passa Q1, oppure Q2, oppure la corsia B con `cells` sopra il transfer in almeno 2 linee su 3. Altrimenti
niente espansione: il passo giustificato diventa più linee collegate (ingestione cellulare di CD4 e Orion), non altro
training sullo stesso corpus.

**Attese scritte ora, ipotesi e non prove:** Q3 passa. Q2 non passa: r3 aveva un coseno di 0,30 contro 0,41 del
transfer su HepG2 C, e P3 non ha trovato beneficio dai controlli. Su Q1 nessuna attesa.

Con tre linee e un seme nessun esito è una conferma: il pilot decide solo se espandere. La riserva (test H1 2025) resta
chiusa.
