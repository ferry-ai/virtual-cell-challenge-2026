# CP-0014 — GO slim scartato dalla sua stessa regola; la GPU non tocca questo codice

- **Data:** 2026-09-15
- **Tipo:** esperimento
- **Redatto da:** agente Claude (Opus 5)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Due, indipendenti fra loro.

**A.** Per un bersaglio **mai perturbato nel training**, un riassunto curato della
sua funzione — i 140 termini del GO slim generico — aggiunge qualcosa al solo
basale? [CP-0012](0012-encoder-inputs-unseen-target.md) l'aveva indicata come
l'unica estensione dei descrittori abbastanza concreta da implementare, e
[ENCODER_INPUTS.md](../ENCODER_INPUTS.md) §6 ne aveva fissato i bracci e la regola
decisionale **prima** che il run esistesse.

**B.** Il codice attuale usa una GPU, e una GPU lo accelererebbe? La domanda nasce
dal fatto che un compagno di squadra ne ha una: averla non è usarla.

## 2. Cosa è stato fatto

```bash
.\scripts\py.cmd scripts/58_build_go_slim_table.py                     # tabella congelata
.\scripts\py.cmd scripts/51_run_modular_pilot.py --run-id g002 --config configs/benchmark_go_slim.yaml --signatures <e001>/signatures <e003>/signatures
.\scripts\py.cmd scripts/59_gpu_readiness.py --out reports/gpu_2026-09-15
.\scripts\py.cmd -m unittest tests.test_modular_benchmark
python scripts/31_check_docs.py
```

La tabella `simbolo → 140 bit + mancante` è costruita dai file già in cache dal 14
settembre (HGNC, GAF, `go-basic.obo`, `goslim_generic`), con i loro sha256 nel
manifesto. Il pilot gira sul **solo** protocollo `new_context_unseen_target`, che
è dove vive il modo B, su due decoder (low-rank e base congelata) e quattro
varianti di descrittori: B0 basale + contesto, B1 con GO slim, B2 senza contesto,
B3 con le righe GO **permutate** fra i simboli a seed fisso. Tre fold, due seed.
Niente è stato scaricato.

## 3. Cosa si è osservato

### 3.1 La tabella GO slim

Fonte: `reports/go_slim_2026-09-15/go_slim_table_summary.json`.

2.693 simboli, 140 termini, 2.647 con almeno un bit, **46 senza**. Risoluzione:
2.615 simboli approvati, 73 via alias univoco, 5 non mappati. Mediana di 8 bit
quando presenti.

**Riproduce esattamente la sonda indipendente del 14 settembre**: gli stessi 5
geni del pannello su 300 restano senza slim (`ANKRD52`, `C5orf22`, `TBC1D19`,
`TMEM104`, `ZC2HC1A`), e `TMEM104` arriva a `SLC38A12`/`Q8NE00` per alias con 4
termini GO diretti che non incontrano lo slim. Due join scritti separatamente
danno lo stesso risultato.

### 3.2 Il pilot, contro la regola fissata prima

Fonte: `reports/go_slim_2026-09-15/comparison_table.csv` e `summary.json`.
48 righe, 160 bersagli su 2.315 condivisi, universo 6.477/18.533 geni.

Differenza appaiata per bersaglio, positivo = **il braccio con lo slim è peggio**:

| Confronto | Decoder | Esiti sui 6 split |
|---|---|---|
| B1 − B0 (slim contro solo basale) | low-rank | peggio in 5 su 6, IC senza zero in 5; l'unico favorevole ha IC che contiene zero |
| B1 − B0 | base congelata | peggio in 5 su 6; l'unico favorevole è −0,005 |
| B3 − B1 (permutato contro reale) | base congelata | |differenza| ≤ 0,023 ovunque; IC contiene zero in 3 su 6 |
| B2 − B1 (senza contesto contro con) | base congelata | **peggio in tutti e 6**, da +0,032 a +0,663, IC senza zero in 5 |

Le due condizioni di scarto scritte in ENCODER_INPUTS §6 scattano entrambe: B1
non batte B0, e B3 è indistinguibile da B1.

### 3.3 Costi del pilot

Orologio: 00:37:00 → 00:40:43, **223 s**. Somma di training e inferenza sui 48
bracci: **166,9 s**. Picco RSS: **345,1 MiB**, identico per ogni braccio.
Parametri: 58.680–59.949 per il low-rank, 110.605–111.733 per la base congelata.

### 3.4 La GPU

Fonte: `reports/gpu_2026-09-15/gpu_readiness.json`.

- In tutto `src/` non esiste un `import torch`, `cupy` o `jax` che tocchi un
  modello. L'unico `import torch` sta in `evaluation.py` e serve a **chiedere se
  esiste CUDA**, per scegliere il backend dello scorer. `torch` non è fra le
  dipendenze del progetto.
- Su questa macchina: `torch`, `cupy`, `jax`, `gpudge`, `pdex` tutti non
  installati; CUDA non disponibile; numpy su `scipy-openblas 0.3.34`.
- Al formato del pilot, il fit dei due decoder costa **1,3 s** su un run di 223 s.
  La costruzione dei descrittori, che sospettavo dominante, costa **0,064 s** per
  320 righe: l'ipotesi era sbagliata e la misura l'ha smentita.
- La SVD è l'unico passo che cresce male. Su rumore gaussiano: 320 righe 0,90 s,
  1.280 righe 6,52 s, 5.120 righe **160,8 s**.
- Su matrici di risposta **reali** (firme HepG2, 9.023 geni), una SVD
  randomizzata di rango 16 contro la completa: **11,9×** più veloce a 320 righe e
  **42,2×** a 1.280, con un errore relativo sui valori singolari dell'**1,6%** e
  dell'**1,3%**. Su rumore gaussiano a 5.120 righe il guadagno è 260× con il 10%
  di errore.
- Sulle stesse matrici reali, il rango 16 cattura il **25–30%** della varianza.

## 4. Interpretazione e incertezza

**Misurato:** tutto il §3.

**Interpretazione (A).** Il GO slim non aggiunge niente qui, e la ragione è più
informativa del verdetto: il braccio con l'annotazione **permutata** fa quanto
quello con l'annotazione vera. Quindi non è che l'annotazione sia debole — è che
il legame gene↔annotazione non porta segnale in questo disegno, e le 140 colonne
si comportano come 140 colonne qualsiasi della stessa sparsità. Se avessimo
guardato solo B1 contro B0 avremmo concluso «non aiuta»; il braccio permutato dice
*perché*, ed è il motivo per cui era stato messo nella regola prima del run.

**Interpretazione (B).** Sul protocollo dei bersagli mai visti il descrittore di
contesto invece **serve**: toglierlo peggiora in tutti e sei gli split. Ha senso:
su un bersaglio nuovo il descrittore del bersaglio si riduce a quattro numeri
basali, quindi il contesto porta proporzionalmente di più. È il contrario di
quanto si vedeva sul protocollo a bersaglio visto in CP-0013, dove il segno
cambiava col fold. Sono due domande diverse e vanno tenute separate.

**Interpretazione (C).** La GPU non è la leva. Non perché sia poco potente, ma
perché il codice non la chiama: ogni modello è numpy scritto a mano. E anche
volendo portarlo, al formato attuale non c'è niente da accelerare — l'aritmetica è
l'1% del run. Quando il formato crescerà, il passo che esploderà è la SVD, e lì la
leva giusta è **algoritmica**: si calcolano tutti i valori singolari per tenerne
16. Sostituirla con una randomizzata vale più di una GPU, su CPU, e costa una
funzione.

**Perché potrebbe non significare questo.** Il pilot ha 160 bersagli su 2.315
disponibili e due decoder su cinque: un effetto piccolo dello slim potrebbe essere
sotto la risoluzione. La regola però era fissata prima e prevedeva questo esito, e
il braccio permutato non lascia molto spazio: se l'annotazione vera contasse,
permutarla avrebbe dovuto peggiorare. L'1,5% di errore della SVD randomizzata è
misurato sui valori singolari, non sull'MSE finale del modello: prima di adottarla
va verificato che le predizioni non cambino oltre la tolleranza dei test di
round-trip.

## 5. Spiegazione semplice

Volevamo sapere se dire a un modello «questo gene fa parte del ribosoma» lo aiuta
a prevedere che cosa succede spegnendolo, quando quel gene non l'ha mai visto
spegnere. Abbiamo aggiunto 140 etichette di funzione — e abbiamo aggiunto anche un
controllo: le stesse 140 etichette **mescolate a caso fra i geni**. Se il modello
va uguale con le etichette vere e con quelle mescolate, allora non sta usando il
significato, sta solo usando «140 colonne in più». È andato uguale. Quindi
l'estensione si butta, come era stato scritto prima di provarla.

Sulla GPU: una scheda video accelera i conti che un programma le manda. Il nostro
non ne manda nessuno — è scritto con una libreria che gira solo sul processore. E
comunque i conti durano un secondo su un lavoro che ne dura duecento: il tempo se
ne va altrove. L'unico punto in cui una GPU servirebbe davvero è il calcolo dei
geni differenzialmente espressi dentro il punteggio, che è un pezzo di un'altra
libreria e che qui gira nella sua versione più lenta perché le altre due non sono
installate.

## 6. Conseguenze

- **D-028**: il GO slim non entra nei descrittori. La riserva (ProtT5, ESM-2,
  gene2vec) non si apre: se l'annotazione curata non batte il permutato, un
  embedding più grande non è la risposta a questa domanda.
- **D-029**: nessun porting a GPU prima di aver sostituito la SVD completa con una
  randomizzata e rimisurato.
- `docs/CONSEGNA_GPU.md` è il pacchetto trasferibile per la macchina del compagno:
  che cosa copiare, che cosa installare, quali comandi, e che cosa la GPU
  accelererà (una cosa sola: il backend DE dello scorer).
- Nessuna migrazione su Kaggle o Colab è stata avviata.
- `configs/benchmark_go_slim.yaml` resta come protocollo eseguito: il codice del
  GO slim resta in `DescriptorBank` dietro `include_go_slim`, spento per
  impostazione predefinita, perché un esperimento negativo va poter rifare.

## 7. Cosa corregge

- **Non corregge CP-0012.** Quel checkpoint diceva che il GO slim era l'unica
  estensione abbastanza concreta da implementare, e aveva ragione: è stata
  implementata e misurata in un giorno. La sua copertura misurata (295/300 sul
  pannello dopo propagazione) è confermata da un join indipendente.
- **Non corregge CP-0013.** Il descrittore di contesto lì era misurato sul
  protocollo a bersaglio già visto, qui su quello a bersaglio mai visto. Le due
  misure non si contraddicono: rispondono a domande diverse.
- Corregge una mia aspettativa, non un documento: avevo previsto che la
  costruzione dei descrittori fosse il costo dominante del run. Sono 0,064 s su
  223. La previsione era sbagliata e la misura l'ha detto.

## 8. Domanda di comprensione

Il braccio B3 usa le stesse 140 colonne di B1, con i valori mescolati fra i geni.
Se B3 fosse andato **peggio** di B1, che cosa avremmo concluso — e perché il fatto
che sia andato uguale è una conclusione più forte del semplice «B1 non batte B0»?
