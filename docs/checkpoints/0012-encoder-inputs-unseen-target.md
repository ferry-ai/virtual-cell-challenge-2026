# CP-0012 — Input degli encoder per bersagli mai perturbati

- **Data:** 2026-09-14
- **Tipo:** osservazione
- **Redatto da:** agente (Grok 4.6)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Con quali descrittori, verificati su file pubblici e senza le risposte
perturbative del gene, si può rappresentare un bersaglio **mai perturbato nel
training** (modo B), e quale unica estensione è abbastanza concreta da
implementare accanto al `DescriptorBank` già esistente.

## 2. Cosa è stato fatto

Letti mappa, registro, benchmark modulare e il bank attuale
(`src/vcc2026/benchmark/descriptors.py`). Nessuna modifica a
`configs/benchmark.yaml`, alle firme e001 o al runner m001.

Probe isolato, destinazione nuova:

```powershell
.\scripts\py.cmd scripts/56_probe_target_descriptors.py --out reports/encoder_inputs_2026-09-14
```

Download in `C:/Users/ferra/vcc2026-data/interim/encoder_inputs_2026-09-14/`:
HGNC complete set, GOA GAF/GPI, GO slim, go-basic.obo, STRING protein.info e
physical.links. Non scaricati: rete STRING combined (83 MB), embeddings ProtT5
(38 MB), ESM-2 (31 MB), gene2vec (GET decompresso > 40 MB, interrotto), CORUM
(HEAD SSL fallito; licenza NC), Reactome (41 MB non compressi dichiarati).
Specifica: `docs/ENCODER_INPUTS.md`.

## 3. Cosa si è osservato

Ogni numero ha un file.

- 300/300 bersagli VCC sono sull'asse ufficiale e protein-coding con ENSG e
  UniProt HGNC. 299 simboli approvati; `TMEM104` è alias univoco di
  `SLC38A12`. `reports/encoder_inputs_2026-09-14/hgnc_vcc300_mapping.csv`.
- 300/300 hanno almeno un termine GOA (GAF 2026-07-28); 295/300 hanno almeno
  un bit dello slim generico (140 termini) dopo chiusura ancestrale.
  Cinque senza slim: ANKRD52, C5orf22, TBC1D19, TMEM104, ZC2HC1A, ciascuno
  con 1–4 termini GO che non cadono nello slim.
  `coverage.json`, `vcc_without_slim.csv`.
- 0/300 VCC sono annotati solo IEA. `coverage.json` campo
  `goa.vcc300.iea_only_among_annotated`.
- K562 GWPS, 2659 bersagli unici nelle firme e001: 2641 con GO, 2616 con slim
  propagato; 4 simboli HGNC ambigui, 1 non mappato. `coverage.json`.
- STRING v12 `preferred_name`: 300/300; grado fisico > 0 per 300/300 (mediana
  143; il file include coppie AB e BA). `coverage.json`.
- DescriptorBank attuale, protocollo unseen K562→RPE1 seed 2026: 41 colonne
  con contesto, 4 senza. Nessun response code. Split in
  `reports/benchmark_2026-09-14/splits/`.
- Basale ufficiale: 300/300 con CPM>0 in A; 3/300 sotto 1 CPM in almeno un
  contesto A/B/C. `reports/data_audit/target_inventory.csv`.
- Download misurati (byte): HGNC 16 913 731, GAF 11 020 779, GPI 604 603,
  slim 125 864, go-basic 32 227 785, STRING info 1 970 090, STRING physical
  8 954 065. `downloads.json`.

## 4. Interpretazione e incertezza

**Misura:** i 300 hanno basale, mapping HGNC e GO; lo slim copre 295/300.
**Interpretazione:** lo slim è l'unica estensione piccola, con licenza
compatibile e senza risposte perturbative del gene, pronta da concatenare a
`e_t`. **Ipotesi, non misura:** geni con lo stesso slim hanno risposte più
simili; va testata con B1 contro B0 e contro il mapping mescolato (B3) in
`docs/ENCODER_INPUTS.md` §6. Non è un punteggio VCC.

STRING fisica è densa: «avere vicini» non discrimina. gene2vec e scGPT/STATE
restano fuori dal confronto rigoroso (espressione / Perturb-seq in
pretraining). ProtT5 STRING e ESM-2 hanno pesi o vettori accessibili (HEAD);
non sono stati letti.

Con un contesto di training `z_c` non varia: non si propone un encoder neurale
di contesto.

## 5. Spiegazione semplice

Se non abbiamo mai spento un gene, non possiamo copiare «quello che è successo
quando l'abbiamo spento». Possiamo chiedere due cose che si sanno comunque:
quanto è acceso a riposo in *questa* cellula, e a quale macchina annotata
appartiene (ribosoma, ciclo, …). La seconda è un vettore di 140 sì/no preso
da Gene Ontology. Se mescolando a caso quelle etichette il modello va uguale,
le etichette non servivano.

## 6. Conseguenze

Nessuna decisione attiva cambiata. D-024 e D-025 restano. Non si adotta GO:
si implementa un confronto. Il passo successivo è di Claude: flag
`include_go_slim` su un `run-id` nuovo, senza toccare m001, seguendo
`docs/ENCODER_INPUTS.md` §7.

## 7. Cosa corregge

Nessuna. Non chiude R-004 (ENSG dei 18 533 output): quel mapping non serve
ai descrittori dei 300. Non adotta la decomposizione modulare (CP-0011 resta
inconcludente).

## 8. Domanda di comprensione

Perché i codici SVD della risposta di K562 di un gene non possono entrare nei
suoi descrittori quando quel gene è nel protocollo «bersaglio mai visto»?
