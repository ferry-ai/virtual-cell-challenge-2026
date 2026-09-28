# La rete relazionale: disegno (R-V2)

28 settembre 2026. Scrive Claude (app desktop, sessione `f2abd9a6`), dal disegno di un sottoagente della stessa
sessione, rivisto qui. Etichette: **misurato**, **interpretazione**, **ipotesi**, **proposta**. La regola della prima
tornata è in [RISULTATI.md](RISULTATI.md).

**Richiesta del proprietario** (scheda [R-V2](../../../docs/piani/modello-v2.md), 28/09 mattina e 19:22): usare tutti
i dati e imparare relazioni, non copiare comportamenti. «Spengo x, y si muove perché è legato a x»; i geni che si
muovono insieme in molti knockdown formano gruppi che si ritrovano nel contesto successivo. I farmaci non devono
prevalere, almeno all'inizio.

## 1. Perché la rete di r1 non basta

| # | Osservazione | Tipo | Evidenza |
|---|---|---|---|
| 1 | La perdita sulla famiglia tenuta fuori è minima alla prima valutazione e poi sale dell'11–22 %, in r1 e in r2 | misurato | [r2](../rete_contesti_r2_2026-09-28/RISULTATI.md), `r2_shard*/per_run.csv` |
| 2 | Le varianti che non possono imparare oltre il punto di partenza restano piatte; il poco che si porta su una famiglia nuova si impara nei primi 50 passi | misurato; interpretazione | stesso |
| 3 | **La discriminazione fra bersagli crolla.** r2, seme 0, `pds` nello spazio degli effetti fra 1.000 bersagli di prova: rete 0,502–0,508, il suo braccio di trasferimento 0,552–0,644 | misurato | `r2_shard0/arms.csv`, `r2_shard1/arms.csv` |
| 4 | La rete scambia la discriminazione con un piccolo guadagno di errore quadratico, con una parte comune a tutti i bersagli: il difetto che il disegno di r1 temeva per le proiezioni su programmi | interpretazione | [DISEGNO di r1](../rete_contesti_2026-09-27/DISEGNO.md); [programmi](../../trasferimento/programmi_2026-09-26/RISULTATI.md) |
| 5 | La capacità sta dove l'identificabilità è minima: 399.264 parametri liberi di embedding dei geni e una rete per (contesto, gene), su 450.402 | misurato (conteggi); interpretazione | `prod_r1/config.json`; `net.py` |
| 6 | L'E2 non passa in nessun seme di r1 né in r2 | misurato | [r1](../rete_contesti_2026-09-27/RISULTATI.md), r2 |

**Interpretazione in una riga.** La rete mette la capacità in funzioni per (contesto, gene), identificate da poche
famiglie, e in un termine a basso rango che impara un disegno comune: riproduce il laboratorio e cancella ciò che
distingue i bersagli. Il segnale dello stesso bersaglio che si trasferisce è piccolo e vive nel termine a rango pieno,
che la rete poi annacqua.

## 2. L'architettura (proposta)

Per la riga i = (contesto c, bersaglio t), famiglia f = fam(c), gene g:

```
ŷ[i,g] = h[c,g] · ( A·s_i·m[i,g]  +  A_q·s^q_i·q[i,g]  +  a_c·qc[i,g] )        rango pieno: base + vicini per carta
       + Σ_k ρ[g,k] · ( (γ[c,k] − 1)·z[i,k]  +  u[t,k] )                       basso rango K: guadagni di contesto + carta del bersaglio
```

1. **`m`, `q`: come in r1.** `m` è il profilo centrato dello stesso bersaglio dalle famiglie diverse da f; `q` la
   media dei profili dei partner STRING. Il punto di partenza è il trasferimento calibrato di r1, a rango pieno.
2. **Carte dei geni ρ (G × K, K = 32)**, comuni a tutti i contesti e fisse dentro una fase.
   - Si calcolano dai soli profili visibili del disegno: nessuna perdita per costruzione.
   - Pesi per riga: ogni famiglia conta uguale; entrano solo i profili di bersagli rispondenti nella famiglia (almeno
     10 geni con |Z| ≥ 3).
   - Il gene del bersaglio e la sua finestra cis si azzerano in ogni profilo. **È essenziale:** altrimenti la carta
     di un bersaglio porterebbe la direzione del suo stesso knockdown, disponibile in addestramento ma non per un
     bersaglio nuovo.
   - SVD e rotazione varimax: la rotazione rende le componenti simili a moduli. **Sono i moduli morbidi.**
3. **Vicini per carta `qc`,** a rango pieno e senza parametri imparati: la media dei profili dei 16 bersagli visibili
   con la carta più simile, esclusi sé stesso e il suo gruppo cis. È «spengo x, y si muove perché è legato a x» nella
   forma che si può falsificare: geni che si muovono insieme come risposte hanno profili di knockdown simili. `a_c`
   parte da 0.
4. **Guadagno di contesto γ, per modulo.** L'attività basale del modulo k nel contesto c è una media pesata dei ranghi
   dei suoi geni nei controlli. log γ[c,k] = 0,5·tanh((θ₀ + θ_k)·a[c,k]), con θ₀ comune e ogni θ_k penalizzato dieci
   volte di più. La versione cieca dà a = 0, quindi γ = 1 esatto; lo scambio usa i controlli di un'altra linea.
5. **Coordinate di modulo z:** la proiezione della base della riga sulle carte. Il guadagno agisce solo sulla parte di
   modulo della base, mai sul suo residuo specifico del bersaglio.
6. **Carta del bersaglio u[t]:** diag(w_self)·ρ[gene di t] + W_p·prior(t). «Il bersaglio è un gene, e la sua carta
   muove il suo modulo»: K parametri, niente mappa libera K × K. Il modello lineare con embedding del gene bersaglio
   non discriminava nemmeno i bersagli di addestramento (misurato:
   [bersagli nuovi](../../trasferimento/bersagli_nuovi_2026-09-26/RISULTATI.md)).
7. **Cancello per gene h = 2σ(β₁·gref),** un parametro, e **ampiezza per bersaglio s** da 8 caratteristiche della
   riga, come nel modello a cancelli.

**Inizializzazione:** tutti i termini nuovi a zero, quindi ŷ = A·m + A_q·q esatto, il punto di partenza calibrato di
r1. Ogni differenza dal trasferimento è imparata.

**Parametri.** `rel0` (carte fisse): circa 300–550 parametri imparati, tutti comuni; nessun parametro per contesto.
`rel1` (carte con un residuo imparato, penalizzato verso le carte fisse): più 13.248 × 32 = 423.936. La rete di r1 ne
aveva 450.402.

**Addestramento:** l'obiettivo di r1 invariato (errore quadratico pesato per 1 / (k·SE² + τ²)), più penalità L2 sui
parametri nuovi. Valutazione al passo 0 e poi ogni 25 passi, pazienza 12, al massimo 3.000 passi; poi il
riaddestramento sulle righe visibili per il numero di passi migliore, come in r1. Solo perturbazioni genetiche nella
prima tornata; i farmaci, dopo, solo nella stima delle carte e con peso limitato.

## 3. Codice (proposta)

Tutto in questa cartella; i file di r1 si importano per percorso, invariati, come fa l'encoder:
- `relphase.py`: `RelPhase(pool.Phase)`, carte, tabella dei vicini, `qc`;
- `relnet.py`: `RelConfig`, `RelNet`, fabbriche per `fit` e per i bracci;
- `train_rel.py`: involucro che esegue `train.run_design` di r1 con quattro nomi sostituiti; `--arch r1|rel`;
- `selftest_rel.py`: mondi sintetici relazionale e nullo, canarino delle perdite, identità all'inizio, parità con r1;
- `make_runs_rel.py`, `score_pair.py`: le corse di Kaggle e il confronto `rel0` − `none` sul proxy combinato.

Bracci in più, gratis alla previsione: `tperm` (ingressi relazionali permutati fra i bersagli di prova), `norel`
(termini relazionali spenti), `cardnb` (solo i vicini per carta, con un'ampiezza ai minimi quadrati).

## 4. Rischi e ablazioni economiche

- **Programma generico:** la prima componente è probabilmente un programma di crescita o stress, e la via dei prior
  può appiattire la discriminazione come in r1. Guardia: falsificazione 6 della regola.
- **Covarianza tecnica nelle carte** (dimensione della libreria, ciclo cellulare): attenuata dalle sole righe
  rispondenti e dal centraggio per contesto. Ablazione: carte permutate fra geni dentro fasce d'espressione.
- **Laboratorio:** l'E2 di laboratorio (K562 contro VIPerturb, stessa linea) lo rivela; carte da una sola famiglia
  contro un'altra.
- **Piattaforma:** carte da sorgenti 3' applicate a contesti Flex; solo VIPerturb è Flex.
- **Salti di calibrazione al riaddestramento,** come nell'encoder su r2: si registra A in entrambe le fasi.

## 5. Dipende dalla misura decisiva

La misura dell'azione 6 di R-REV ([covariazione](../covariazione_2026-09-28/RISULTATI.md)) decide se la prima tornata
parte:
- **conservata fra laboratori:** la tornata come descritta; poi `rel1` e carte da più dati (HIPSCI, Southard, A549,
  farmaci con peso limitato), con i bersagli di prova tolti da ogni sorgente delle carte;
- **conservata solo dentro un laboratorio o una chimica:** carte di consenso (solo le componenti che almeno due
  laboratori riproducono), senza guadagni di contesto, K = 16; `rel0` si legge come denoiser e come predittore per
  bersagli nuovi, non come modello del contesto;
- **non conservata:** la parte carte e moduli non ha base; resta solo `cardnb` come candidato per i bersagli nuovi, se
  la somiglianza fra bersagli è conservata.
