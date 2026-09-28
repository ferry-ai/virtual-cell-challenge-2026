# Encoder di contesto: autoverifica e regola della prima tornata

Disegno e codice: [DISEGNO.md](DISEGNO.md) (claude2, 28/09 notte; proposta, nulla eseguito da lui). Qui scrive il
lead (Claude, sessione del proprietario), con gli orari letti da `date`.

Etichette: **misurato**, **interpretazione**, **ipotesi**, **proposta**. Nessun numero qui è un punteggio VCC.

## Autoverifica (misurato, Kaggle CPU, 28/09 alle 03:06)

Kernel privato `vcc-enc-selftest`, versione 2 (la versione 1 si è fermata prima dei controlli per un errore del mio
costruttore del kernel, che chiamava `nvidia-smi` su una macchina senza GPU; il codice di claude2 non c'entra).
Torch 2.10.0+cpu, numpy 2.0.2, pandas 2.3.3; i file copiati piatti in una cartella, con sha256 controllato. Esito
completo in [`autoverifica_kaggle_v2.txt`](autoverifica_kaggle_v2.txt):
- `train_emb.py --selftest`: **17 controlli su 17**, in 80 s;
- `train.py --selftest` (la rete, invariata): **14 su 14**, in 75 s.

In breve, sul mondo sintetico:
- **fuga d'informazione:** con i profili esclusi sovrascritti da rumore, geni, statistiche, pesi dell'encoder ed
  embedding degli altri profili restano identici al bit;
- **stato latente ritrovato:**
  - dall'encoder con R² 0,984 sui contesti di validazione ed esclusi;
  - dalla PCA con R² 0,998;
- **mondo piantato:**
  - la rete con l'embedding batte cieco, scambio, `emb_blind` ed `emb_swap` su entrambe le linee tenute fuori;
  - E2: correlazione 0,454 contro 0,033 del 97,5° percentile delle permutazioni;
- **mondo nullo:** nessun guadagno oltre il rumore;
- **confronto:** `compare.py` ricalcola i contrasti di `train.py` con differenza massima 0.

Il codice fa quello che dice sui dati sintetici. **Non dice niente sui dati veri.**

## Regola della prima tornata, fissata alle 03:10 del 28/09

Fissata prima di pre-addestrare sui dati veri e prima di qualunque corsa della rete con embedding.

### Che cosa gira

**Condizioni** (`make_runs.py --seeds 0 --conditions none,pca,ours,ours+tahoe`):

| Condizione | Che cosa è |
|---|---|
| `none` | la rete di `train.py`, come in r1 |
| `pca` | PCA a 32 componenti del corpus `ours` |
| `ours` | encoder pre-addestrato sui tre corpora previsti (vedi sotto) |
| `ours+tahoe` | gli stessi, più i controlli DMSO di Tahoe (linea × piastra); gira solo se l'estrazione arriva prima dell'avvio delle sessioni, altrimenti in questa tornata non gira e lo scrivo |

I tre corpora di `ours`:
1. i controlli delle nostre sorgenti CRISPRi, da `reports/corpus_basale_2026-09-28/`: K562 genome-wide, K562
   essenziale e RPE1 di Replogle, CD4, HCT116 e HEK293T, KOLF2.1J, A549, VIPerturb-seq (Flex), Southard Hs27,
   HIPSCI (in pool dagli schermi genome-wide; e, aggiunte alle 03:16, prima di qualunque corsa, le 19 linee dello
   schermo mirato, 8 pool di controlli ciascuna);
2. i controlli di A, B e C;
3. DepMap, 1.667 linee: K562, HCT116, HEK TE, HepG2, Jurkat e A549 sono già fuori dalla costruzione del corpus.

**Tahoe è arrivato in tempo (nota delle 03:45, prima di qualunque corsa su GPU).** Il corpus `tahoe` viene da
un sottoinsieme sistematico dei frammenti, uno ogni cinque (678 di 3.388). L'estrazione completa di Kaggle, alle
03:21, aveva pianificato 1.032 frammenti in due ore e mezza.

| Voce | Valore (misurato) |
|---|---|
| cellule DMSO lette | 434.966 |
| gruppi linea × piastra | 700 (50 linee, 14 piastre) |
| profili del corpus | 650 in 48 linee: soglia di 50 cellule per gruppo |
| byte letti | 2,69 GB |
| geni dell'asse ufficiale ritrovati | 18.150 su 18.533 |

- Script: `reports/tahoe_dmso_2026-09-28/extract_dmso_subset.py`, poi `reports/corpus_basale_2026-09-28/corpus_tahoe.py`.
- Verifica: sul frammento 1031, identico al bit a un ciclo per cellula sul file scaricato intero.
- HCT116 non è fra le linee di Tahoe-100M (è solo nella tabella dei metadati, che ne elenca 102).
- Ci sono A549 e HepG2/C3A.

`ours+tahoe` quindi gira.

**Non girano:** `ours+scbasecount` e `ours+both`. scBaseCount è accessibile solo da un progetto Google Cloud
abbonato al dataset sul Marketplace ([README ufficiale](https://github.com/ArcInstitute/arc-virtual-cell-atlas/blob/main/scBaseCount/README.md)):
serve il proprietario.

**Disegni:**
- E1 con verità `k562`, `orion_hct116` (famiglia Orion fuori) e `cd4_Rest` (famiglia CD4 fuori);
- E2 sulla coppia Orion.

Le liste di esclusione del §8 di DISEGNO si applicano a tutti i corpora, nostri compresi.

**Seme:** solo 0 in questa tornata. Il limite viene dalle due sessioni GPU di Kaggle, già occupate stanotte dai semi
di r1. Semi 1 e 2 dopo, se la tornata lo giustifica o se il proprietario lo chiede.

**Argomenti:**
- della rete: quelli di default di `train.py` (come r1), identici fra le condizioni;
- dell'encoder e della PCA: quelli di default.

**Misura:** `compare.py`, nello spazio degli effetti, con bootstrap appaiato sui 1.000 bersagli di prova.

### Regola

È quella del §10 di DISEGNO, letta da `readout.csv`. Vale per X in {`pca`, `ours`, `ours+tahoe`} contro `none`; per
attribuire il merito, anche per `ours` contro `pca` e `ours+tahoe` contro `ours`.
1. **E1:** X − `none` positivo su almeno 2 delle 3 verità, con l'intervallo sopra zero su almeno una e nessun
   intervallo interamente sotto −0,002.
2. **L'embedding è ciò che aiuta:**
   - rete − `emb_blind` positivo su almeno 2 verità su 3, con l'intervallo sopra zero su almeno una;
   - lo stesso per rete − `emb_swap`.
3. **E2 (Orion):** l'intervallo della correlazione media sta sopra zero, la media supera il 97,5° percentile delle
   permutazioni, e la differenza appaiata con `none` è positiva.
4. **Semi:** con un solo seme **non si verifica**. La colonna `seed_signs_agree` di `readout.csv` risulta vera per
   costruzione e non va letta.

### Letture

- **Passano 1–3 al seme 0:** «promettente, da confermare», e niente di più:
  - servono i semi 1 e 2, con il punto 4, prima di qualunque affermazione e di qualunque uso in un invio;
  - l'intervallo bootstrap sui bersagli non contiene la varianza fra semi.
- **Non passa 1** (X − `none` ≤ 0, o con l'intervallo che contiene zero, su almeno due verità):
  - è un esito negativo al seme 0 per quella condizione, e lo riporto così;
  - i semi 1 e 2 girano solo se un'altra condizione passa o se il proprietario lo chiede.
- **Il contributo di Tahoe** è `ours+tahoe` contro `ours`, con gli stessi punti 1–3. Se passa solo contro `none` e non
  contro `ours`, il merito non va a Tahoe.
- **Una ricostruzione migliore dei profili basali** (nel `manifest.json` dell'encoder) non conta, da sola: sono le
  parole del proprietario.

**Aspettativa, scritta prima (interpretazione).**
- Il §0 di DISEGNO si aspetta poco o nulla.
- Al seme 0 di r1 la rete senza embedding batte già la sua versione cieca e lo scambio su tutte le verità E1, nello
  spazio degli effetti:
  - rete − cieca da +0,0008 a +0,0138;
  - rete − scambio da +0,0005 a +0,0206;
  - sono i `metrics.json` di `vcc-rete-r1-s0` versione 2, lettura descrittiva, non la regola di r1.
- L'embedding deve quindi aggiungere qualcosa a un contesto che la rete usa già.

## Esito della prima tornata, parte Orion (misurato, 28/09; tabelle in `r1_shard0/`)

La sessione GPU dei disegni Orion (e1_orion con verità HCT116, e2_orion) è finita. Quella dei disegni K562 e CD4 è
finita anch'essa su Kaggle, ma alle 10:35 le sue tabelle non erano ancora scaricate.

**Contrasti con `none` sulla verità HCT116 (skill, bootstrap sui 1.000 bersagli):**

| Condizione | e1_orion | e2_orion |
|---|---|---|
| `pca` | +0,0012 [+0,0007; +0,0017] | +0,0007 [+0,0002; +0,0012] |
| `ours` | +0,0003 [−0,0001; +0,0007] | +0,0001 [−0,0003; +0,0004] |
| `ours+tahoe` | +0,0011 [+0,0007; +0,0015] | +0,0004 [+0,0001; +0,0008] |

Nello stesso disegno E2, su HEK293T l'encoder peggiora: `ours` −0,0022, `pca` −0,0012, `ours+tahoe` −0,0007.

**L'embedding giusto non è ciò che aiuta.** Punto 2 della regola, su HCT116:
- rete − `emb_blind` è positivo per tutte le condizioni: con l'embedding la rete sta meglio che con l'embedding medio;
- rete − `emb_swap` è **negativo** per tutte: `ours` −0,0018 [−0,0025; −0,0011], `ours+tahoe` −0,0007, `pca` −0,0003.
  Con l'embedding di un'altra linea la rete sta meglio che con quello giusto.

**E2 Orion:** nessuna condizione supera il 97,5° percentile delle permutazioni (`ours`: 0,0039 contro 0,0041).

**Lettura per la regola.** Per la parte Orion nessuna condizione passa: il punto 2 fallisce ovunque e l'E2 non
passa. I disegni K562 e CD4 non possono cambiare l'esito del punto 2 per Orion; la regola completa si legge con
tutte e tre le verità E1.

**Interpretazione.** I guadagni contro `none` sono di un millesimo di skill e vengono dalla forma dell'embedding,
non dal contesto giusto. È lo stesso difetto del modello a cancelli di r1 e di CP-0013. Tahoe aggiunge un poco
rispetto a `ours` su HCT116 (+0,0008 [+0,0005; +0,0011]), ma dentro un disegno in cui il contesto giusto non aiuta:
non è un merito attribuibile a Tahoe.

## Esito della prima tornata, parte K562 e CD4, e lettura completa (misurato; tabelle in `r1_shard1/`)

Tabelle scaricate il 28/09 alle 13:05. Contrasti con `none`, skill, bootstrap sui 1.000 bersagli:

| Condizione | K562 | CD4 a riposo |
|---|---|---|
| `pca` | −0,0005 [−0,0007; −0,0003] | −0,0078 [−0,0095; −0,0063] |
| `ours` | +0,0019 [+0,0017; +0,0023] | **−0,0551** [−0,0596; −0,0508] |
| `ours+tahoe` | +0,0000 [−0,0001; +0,0002] | −0,0046 [−0,0062; −0,0030] |

**Punto 2, l'embedding giusto:**
- **K562:** rete − `emb_swap` negativo per ogni condizione (`ours` −0,0038, `ours+tahoe` −0,0058, `pca` −0,0057).
  Anche qui l'embedding di un'altra linea fa meglio di quello giusto.
- **CD4:** con `ours` la rete sta peggio che con l'embedding medio (rete − `emb_blind` −0,045). Con l'embedding
  scambiato peggiora di molto (+0,19 a favore di quello giusto).

**Interpretazione.** Per le cellule T, tenute fuori dal corpus in ogni loro forma, la mappa dall'embedding al contesto
estrapola, e l'uscita diventa instabile.

**Lettura della regola, tre verità E1 (seme 0).** Nessuna condizione passa:

| Condizione | Esito sul punto 1 | Motivo |
|---|---|---|
| `pca` | non passa | su CD4 l'intervallo sta tutto sotto −0,002 |
| `ours` | non passa | positivo solo su K562; CD4 sotto −0,002 |
| `ours+tahoe` | non passa | positivo con intervallo sopra zero solo su HCT116; CD4 sotto −0,002 |

Il punto 2 fallisce ovunque su HCT116 e K562. L'E2 Orion non passa. I semi 1 e 2 non servono: la regola dice di
farli girare solo se una condizione passa.

**Per le sorgenti.** Nemmeno il contributo di Tahoe si attribuisce:
- `ours+tahoe` − `ours` è positivo su HCT116 (+0,0008) e su CD4 (+0,0505, perché `ours` va male);
- su K562 è negativo (−0,0019);
- in nessun caso con il contesto giusto come causa.
