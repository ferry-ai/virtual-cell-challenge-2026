# Ricerca di sorgenti del 26 settembre: HIPSCI e resoconti pubblici della gara

26 settembre 2026, pomeriggio. Catalogo di ciò che è stato trovato, come chiede la regola di conservare
ogni dataset trovato (anche lontano dai contesti), con il rapporto integrale di grok in
[agenti/hipsci_e_approcci_grok.md](agenti/hipsci_e_approcci_grok.md). Nato dall'[audit di codex](../audit_piani_dati_2026-09-26/RISULTATI.md),
che indicava HIPSCI come la sorgente dimenticata più concreta. **Nessun download.**

## HIPSCI CRISPRi a singola cellula (Feng et al., Cell Genomics 2025)

| Voce | Valore | Verifica |
|---|---|---|
| Studio | CRISPRi dCas9-KRAB-MeCP2 genome-scale in iPSC: 7.226 geni bersaglio, 34 linee da 26 donatori; braccio mirato di 444 geni in 19 linee | grok da testo primario (PMC12903452) |
| Cellule | 219.206 cellule con guida nel genome-scale (mediana 25 per gene); 635.022 nel braccio mirato (mediana 74 per bersaglio per linea) | grok, dal testo; non ricontato |
| Chimica | 10x Single Cell 5′ v2 con cattura diretta delle guide: né Flex né 3′ | grok, dai metodi |
| Geni di risposta | 6.471 (genome-scale) e 6.517 (mirato) dopo il filtro di espressione degli autori | grok, dal testo |
| File elaborati | Figshare 26819743, 9.119.437.506 byte: `GenomeWideScreen_LFC_byGene.tsv.gz` 794.610.300, `TargetedScreen_LFC_byGene-perLine.tsv.gz` 1.919.661.029 e altri | **verificato da Claude** sull'API Figshare il 26/09: pubblico, MIT, stessi byte |
| Conteggi | Figshare 27989294, 7.925.882.368 byte: UMI RNA per schermo e metadati delle cellule | **verificato da Claude** sull'API Figshare: pubblico, MIT |
| Letture grezze | ENA PRJEB81502 (ERP165335), CRAM pubblici da 26–43 GB l'uno | grok |
| Bersagli del pannello | 197/300 secondo i metadati locali dell'11 settembre (`reports/data_audit/hipsci_coverage.json`); non ricontato sulle tabelle S1/S6 | audit di codex |

**Ruolo possibile:** (1) una quinta sorgente per i bersagli del pannello, rumorosa per linea ma con 34
linee; (2) la sola sorgente con molte linee dello stesso tipo cellulare e donatori diversi: misura quanto
la risposta a un knockdown cambia con il solo sfondo genetico, cioè la varianza di linea che il modello
gerarchico non riesce a stimare con tre o quattro linee ([EB](../trasferimento_gerarchico_2026-09-26/RISULTATI.md)).
**Stato:** candidato verificato nei metadati, non acquisito. Il download (circa 2,7 GB per le due tabelle
LFC per gene, 17 GB tutto) aspetta il via del proprietario.

## Che cosa dicono le pagine pubbliche della gara (grok, con URL nel rapporto)

- Il riferimento zero ufficiale di ogni membro è la **risposta media del contesto** copiata su ogni
  perturbazione; per la `mse` vale 0,986–0,992 sui tre pannelli di riferimento, la replica 0,028–0,045
  (specifica delle metriche di Arc, 19 agosto). Coerente con la stima locale (PROGETTO §4, punto 1) e
  con l'[analisi di claude2](../risposta_comune_2026-09-26/agenti/membro_mse_claude2.md).
- Asse di valutazione: 18.533 geni, 300 costrutti, 400 cellule e mediana di 20.000 UMI per perturbazione.
- Nessuna pagina pubblica di partecipanti trovata che descriva la calibrazione dell'ampiezza, il corpus di
  Perturb-seq usato o l'identificazione delle linee.
