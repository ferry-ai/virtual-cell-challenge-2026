# HepG2 in locale: le analisi dell'audit e i controlli corretti sui dati reali

2 ottobre 2026, Claude Code per Alfredo, sessione `42343bb9-c8d1-4b93-a9cc-2008dd008900`, branch
`codex/teammate-rlead`. Segue la [presa in carico](../presa_rlead_2026-10-01/README.md), dove queste analisi
erano «non eseguibili: manca il file grezzo HepG2».

**In breve.**
- *Misurato:* il file pubblico è identico a quello dell'audit.
- *Misurato:* le due analisi HepG2 dell'audit, rieseguite, danno gli stessi valori.
- *Misurato:* sui controlli veri di HepG2 il serbatoio corretto del passo A dà a ogni libreria con
  almeno 64 controlli i suoi 64 controlli. Col serbatoio vecchio, ricostruito dall'audit, nessuna
  libreria li aveva.
- *Misurato:* la scelta non dipende dall'ordine di lettura.

Nessun training, nessun confronto di modelli, nessuno score.

## Il file

`NadigOConner2024_hepg2.h5ad` da Zenodo 13350497 (scPerturb, CC BY 4.0):
- **dove sta:** `D:\databases_vcc\scperturb_zenodo13350497\`, su un disco esterno del teammate, fuori
  dal repository;
- **dimensione:** 850.590.740 byte;
- **MD5:** quello pubblicato da Zenodo;
- **SHA256:** `1af2f7b3e692ad3d077e6027d68a1f800619e29aa3f7a0efa70146fb7223a4bf`, lo stesso di
  `lead_audit_2026-10-01/data_r1/manifest.json`.

## Le analisi dell'audit, rieseguite

Il codice è lo stesso: `lead_audit_2026-10-01/analyze_hepg2.py` e `analyze_design.py`, al commit
`aa762c6`, con `--raw` sul file sopra. `compare.py` confronta valore per valore con le uscite
dell'audit e scrive `comparison.json`.

| Uscita | Valori | Diversi |
|---|---|---|
| `data_r1/data_diagnostics.json` | 450 | 0 |
| `data_r1/hepg2_targets.csv` | 5.634 | 0 |
| `design_r1/design.json` | 101 | 0 |

Cambiano solo i percorsi scritti nei `manifest.json`.

## I controlli corretti sui dati reali

`pool_corrected.py` applica `allocate_pool`, `priority` e `bottom_k` di
[cellnet_rlead](../../modelli/cellnet_rlead_2026-10-01/README.md). Il confronto con la ricostruzione del
serbatoio vecchio in `design_r1` è alla pari:
- stessi 4.976 controlli;
- stesse 56 librerie (`obs/batch`);
- pool di 2048;
- `ctrl_k` 64;
- nessun QC.

| Misura | Serbatoio vecchio (audit) | Corretto |
|---|---|---|
| Librerie con almeno 64 controlli propri nel pool | 0 su 52 possibili | 52 su 52 |
| Quota delle cellule perturbate la cui libreria ha 64 controlli nel pool | 0 | 0,976 (il massimo possibile: quattro librerie ne hanno meno di 64 in origine) |
| Dimensione del pool | 2048 | 3426 |
| Stesse righe leggendo in ordine di file, al contrario, in 8 shard rimescolati | — | sì, tutte e tre |

**Il prezzo della correzione** (lettura del codice e del risultato):
- il pool cresce da 2048 a 3426 righe, perché i minimi per libreria (52 × 64, più le 98 righe delle
  quattro librerie piccole) superano il pool chiesto. In memoria il pool di HepG2 è circa 1,7 volte
  quello vecchio;
- le librerie 21, 36, 51 e 56 hanno 5, 7, 63 e 23 controlli. Le loro cellule restano sul pool comune,
  e `config.json` del training lo riporta (`control_fallback`).

**Limiti:**
- è la sola HepG2, senza il QC del prepass;
- le librerie qui sono `obs/batch` del file grezzo. Che coincidano con le librerie degli shard
  `rlab-hepg2-nadig` lo dice il prepass sul corpus, non questa misura.

## File

| Percorso | Contenuto |
|---|---|
| `data_r1/`, `design_r1/` | uscite delle analisi dell'audit, rieseguite; i log in `analyze_*.log` |
| `compare.py`, `comparison.json` | confronto valore per valore con l'audit |
| `pool_corrected.py`, `pool_r1/` | serbatoio corretto sui controlli reali (`pool.json`, `manifest.json`), log in `pool_r1.log` |
