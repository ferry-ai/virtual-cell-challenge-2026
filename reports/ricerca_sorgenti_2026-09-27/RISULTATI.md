# Sorgenti del 27 settembre: dati multi-contesto, la struttura di KOLF2.1J e il piano d'ingestione

27 settembre 2026, pomeriggio. Nella scheda [R-V2](../../docs/piani/modello-v2.md). Catalogo e verifiche, come
chiede la regola di conservare ogni dataset trovato; nessun dato scaricato oltre ai metadati.

## Il via del proprietario (trascritto dalla chat)

- Nel pomeriggio del 27/09 (l'ora del messaggio non è registrata) il proprietario ha chiesto di far entrare in
  pipeline tutti i candidati catalogati, citando la
  tabella: HIPSCI CRISPRi, VIPerturb-seq, KOLF2.1J, knockout in A549 (GSE345058), CRISPRa di Southard, Jurkat
  (lettura mirata), X-Atlas/Pisces. È il via ai download di quelli pubblici.
- Nota di progetto dello stesso pomeriggio: «sei sempre autorizzato ad usare colab e kaggle, per runpod chiedi».
- Nello stesso pomeriggio: per ora niente invii al server e niente push.

## Ricerca di altri dati multi-contesto (misurato: due agenti, due famiglie)

La domanda: dati pubblici in cui gli stessi geni perturbati sono misurati in molti tipi cellulari (almeno cinque),
per imparare come cambia la risposta con il tipo cellulare. antigravity ha cercato solo nei risultati di ricerca
([rapporto](agenti/ricerca_antigravity.md)); grok ha verificato sulle pagine primarie
([rapporto](agenti/verifica_grok.md)). Esito di grok:

| Pista | Che cos'è davvero | Stessi geni in ≥ 5 tipi cellulari? | Dimensione, licenza |
|---|---|---|---|
| VIPerturb-seq (Zenodo 18460279) | CRISPRi letto con Flex; il braccio genome-wide è solo K562 (6.724 perturbazioni nell'oggetto filtrato); un pilota di 100 guide in K562, HEK293 e HAP1 | no | 17,3 GB in tutto (pilota 1,6 GB), CC BY 4.0 |
| Echoes of Silenced Genes (Kaggle, Myllia) | CRISPRi in una sola linea tumorale non nominata; 80 perturbazioni di training | no | 845 MB, non commerciale; l'uso richiede di accettare le regole della gara (decisione del proprietario) |
| HyperMapDB | profili **previsti** da un modello, 2.500 geni, 18 contesti; non misure | no | 16,9 GB, CC BY 4.0 |
| scPerturb, PerturBase | raccolte armonizzate di studi già noti | nessuno trovato | — |

Unica pista che corrisponde alla domanda: un set CROP-seq di Myllia con gli stessi 218 geni in THP-1, Jurkat, K562,
A549 e U2OS, **proprietario** (solo su richiesta). **Conclusione:** nessun dataset pubblico misura gli stessi geni
in cinque o più tipi cellulari.

## KOLF2.1J: la struttura del file (misurato, sonde a intervalli di byte)

`kolf_probe.py` e `kolf_probe2.py` leggono solo la struttura dell'h5ad (6 MB trasferiti ciascuna) attraverso
`vcc2026.remote_ranges`. Record Figshare+ 27261219, CC BY 4.0: `KOLF_Pan_Genome_QC_Filtered.h5ad` 189,4 GB, un
sottoinsieme «perturbazioni forti» di 46,7 GB (scelto sull'effetto, quindi selezione sull'esito: non adatto come
sorgente), due sottolibrerie di 4,6 e 7,0 GB; nessun file aggregato.

- 2.659.209 cellule × 37.567 geni; `layers/counts` sono conteggi grezzi (float32) in formato **CSC**, cioè per
  gene, **senza compressione**, a blocchi di 120.120 valori: ogni gene è un tratto contiguo del file.
- `obs`: `gene_target` (11.688 bersagli; controlli `NTC`), `channel` (90), `batch` (3), `total_counts`.

**Conseguenza (implementata in parte):** si possono sommare i conteggi per (bersaglio, gruppo di canali) leggendo
il file per blocchi di geni, in più sessioni in parallelo (Colab, Kaggle o locale), senza scaricarlo: circa 85 GB
di letture per i geni dell'asse ufficiale, poi lo stimatore corretto in locale. Il codice è affidato a codex
(base di lancio, run `20260927-142516-v2-kolf-ingest`).

## Piano d'ingestione per dataset

| Dataset | Come entra | Dove |
|---|---|---|
| KOLF2.1J | somme per blocchi di geni dall'h5ad remoto, poi stima con `min_expected` | Colab/Kaggle o locale |
| HIPSCI CRISPRi | tabelle LFC degli autori (2,7 GB) come sorgente separata; conteggi (7,9 GB) per la stima nostra | locale |
| VIPerturb-seq | `genome_wide_filtered.rds` (3,6 GB) convertito con R (4.5.3 installato), poi stima | locale |
| GSE345058 (knockout, A549) | h5ad 23 GB, per il confronto fra modalità, non come sorgente dello stesso intervento | Colab/Kaggle |
| Southard (CRISPRa) | quattro h5ad da 8–30 GB, uno alla volta; attivazione, non knockdown | Colab/Kaggle |
| Jurkat | già in locale; lettura mirata di 374 geni | locale |
| X-Atlas/Pisces | non ancora pubblicato | — |
