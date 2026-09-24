# DLD-1 (GSE337988): tetto dentro il contesto e trasferimento fra contesti

Claude, 24 settembre 2026, sera. **Esplorativo**: non è uno stadio, non è un punteggio VCC e
non adotta una sorgente. Completa [CP-0035](../../docs/checkpoints/0035-dld1-mixscale-audit.md) e
`reports/dld1_audit_2026-09-24/`, che misurano copertura e confronto con K562: qui si aggiungono
il tetto di riproducibilità dentro DLD-1 e il confronto con tutte le sorgenti della cache r5.

## Dati

Nella cartella dati, `external/dld1_gse337988/`, con `manifest.json` e
`manifest_20260924_222426.json` (URL, byte, sha256): le matrici lfc e se di Low1, la lfc di
Low2, la libreria delle guide e il samplesheet di GSE337988. Nessun file originale modificato.

## Che cosa sono i file, dai metodi del preprint

Letti da un agente il 24/09 (bioRxiv 10.64898/2026.07.10.737863; run di agent-hub
`20260924-212855-ingest-a-dld1-methods`), tranne dove si dice altro:
- **Colonne:** perturbazioni a livello di promotore (`GENE_P1`, `GENE_P2`, …); 6.451 colonne nella
  matrice Low1, di cui 496 `NTC_*`. *Misurato* sull'intestazione del file.
- **Righe:** 2.827 geni di risposta, 2.587 sull'asse ufficiale. Il preprint fa la DE sui circa
  3.000 geni più variabili per devianza binomiale. *Misurato* (2.827) e *verificato* (3.000).
- **Modello:** limma-voom adattato alla singola cellula, un modello per perturbazione; controlli
  = cellule con guide non-targeting; covariate log UMI, frazioni mitocondriale e ribosomiale, e il
  numero di guide per cellula nei dati con più guide. *Verificato* sul preprint.
- **Base del logaritmo:** non scritta; log2 è la convenzione di voom. *Da verificare*. Le
  correlazioni e i segni qui sotto non ne dipendono.
- **Low1 e Low2:** le due metà dei dati a bassa MOI, divise per corsia 10x, non repliche
  biologiche. *Dedotto* dal preprint ("reference" e "holdout" da corsie diverse).

## Misure

Su 2.587 geni. Effetto di un bersaglio = media delle colonne dei suoi promotori. Correlazione di
Pearson per bersaglio; mediana con intervallo bootstrap al 95% sui bersagli (2.000 ricampioni,
seme 20260924). Sorgenti: cache `processed/multisource_2026-09-23_r5`, colonna `raw`.

| Confronto | Mediana [IC95] | n bersagli |
|---|---|---|
| Dentro DLD-1, Low1 contro Low2, tutti i bersagli | 0,0698 [0,0681; 0,0721] | 4.954 |
| Stesso confronto, bersaglio rimescolato | 0,0010 [−0,0002; 0,0023] | 4.954 |
| Dentro DLD-1, 10% dei bersagli con l'effetto più ampio | 0,1032 [0,0851; 0,1231] | 496 |
| DLD-1 contro HCT116 (Orion) | 0,0267 [0,0159; 0,0368] | 59 |
| DLD-1 contro K562 | 0,0207 [0,0076; 0,0405] | 61 |
| DLD-1 contro CD4 a riposo | 0,0208 [0,0081; 0,0299] | 65 |
| DLD-1 contro HEK293T (Orion) | 0,0143 [0,0089; 0,0277] | 62 |
| Dentro DLD-1, sugli stessi bersagli delle righe sopra | fra 0,093 e 0,101 | 59–65 |

Differenze appaiate per bersaglio:
- HCT116 − K562 = +0,0049 [−0,0156; +0,0176], n 53;
- HCT116 − HEK293T = +0,0143 [+0,0002; +0,0231], n 58;
- HCT116 − CD4 a riposo = +0,0005 [−0,0109; +0,0180], n 58.

Tutte le sorgenti della cache, con controlli rimescolati e accordo di segno: `compare_low1.json`
e `ceiling_low1_low2.json`.

**Misurato:** fra contesti arriva circa un quarto-un quinto della correlazione che si riproduce
fra le due metà di DLD-1 sugli stessi bersagli. **Misurato:** HCT116, colorettale come DLD-1, non
si distingue da K562 né da CD4; supera HEK293T con un margine al limite. **Interpretazione, non
dimostrata:** se la vicinanza di tessuto aiuta, con circa 60 bersagli qui non si vede.

## Limiti

- La correlazione fra metà sottostima l'affidabilità di tutti i dati; nessuna correzione
  Spearman-Brown.
- I circa 60 bersagli condivisi sono quelli del pannello attuale. Per D-044 non sono un criterio
  di ammissione, e non rappresentano i 4.954 bersagli di DLD-1.
- Nessuna separazione C/T/J di [GENERALIZZAZIONE.md](../../docs/GENERALIZZAZIONE.md) §3: è una
  descrizione dello spazio degli effetti, non il test di un predittore. Una metrica VCC richiede
  cellule e controlli.

## Comandi

Con `C:/Users/ferra/vcc2026-data/.venv`; ogni script rifiuta di sovrascrivere.

```
python fetch_dld1.py <data_root>/external/dld1_gse337988 [file ...]
python explore_dld1.py <dld1_dir> <data_root> <out.json> --log-base 2
python compare_sources.py <lfc_Low1.csv.gz> <data_root> <cache_dir> <out.json>
python ceiling_dld1.py <dld1_dir> <data_root> <cache_dir> <out.json>
```
