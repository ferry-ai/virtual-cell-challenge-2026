# sorgenti — i dati di perturbazione, come si stimano e quanto valgono

Da qui vengono gli effetti che il trasferimento media e che i modelli imparano: estrazioni per il
pannello (stadi 97, 102, 98), **universi** con tutti i bersagli di ogni sorgente, correzioni dello
stimatore, ricerche e schede di sorgenti candidate, corpora di profili basali. I dati pesanti
stanno fuori dal repository (`C:/Users/ferra/vcc2026-data`): qui ci sono script, manifest,
indici e misure. Indice generale: [../README.md](../README.md).

**Da sapere prima di usarle:**
- **Tutte le sorgenti tranne VIPerturb-seq sono in 3'**; la gara è letta in 10x Flex
  ([ponte Flex](ponte_flex_2026-09-28/RISULTATI.md)).
- **Gli universi del 26/09 di CD4, HCT116 e HEK293T hanno l'artefatto del pseudoconteggio**: per i
  banchi dal 27/09 si usano quelli ricostruiti (`*_me1`, [universo_corretto](universo_corretto_2026-09-27/RISULTATI.md)).
  K562 passa per un altro stimatore e non ne soffre.
- **I profili basali in CPM sono normalizzati sui geni di ogni sorgente**, cioè su insiemi diversi
  (le sorgenti 3' contengono RPL/RPS, l'asse Flex no). Il confronto dei livelli basali fra sorgenti
  e contesti ha quindi uno scarto sistematico non misurato
  ([revisione critica](../analisi/revisione_criticita_2026-09-28/REVISIONE.md), §2).
- Orion (HCT116, HEK293T) ha licenza **CC-BY-NC-SA-4.0**: ammessa negli invii per decisione del
  proprietario (`../invii/trial_2026-09-22/autorizzazioni.md`), non per verifica presso gli organizzatori.

| Data | Cartella | Nocciolo | Vale? | Peso oggi |
|---|---|---|---|---|
| 28/09 | [ponte_flex_2026-09-28/](ponte_flex_2026-09-28/) | Gli stessi knockdown K562 in Flex (VIPerturb-seq) e in 3': metà contro metà di VIPerturb 0,110 di coseno, verso il 3' 0,030; il rumore spiega una parte del divario, non tutto | sì; un solo schermo Flex, esplorativo | ★★★ (la gara è in Flex) |
| 28/09 | [corpus_basale_2026-09-28/](corpus_basale_2026-09-28/) | Profili basali per l'encoder: controlli delle nostre sorgenti (con 19 linee HIPSCI), A/B/C, DepMap, Tahoe DMSO; una decisione per sorgente in `SORGENTI.md` | sì come dati; piattaforme diverse mescolate | ★ |
| 28/09 | [tahoe_dmso_2026-09-28/](tahoe_dmso_2026-09-28/) | Estrattori dei controlli DMSO di Tahoe-100M (tutti i frammenti, o uno ogni k); contratti del dataset in `LAYOUT.md` | sì | ★ |
| 27/09 | [pseudoconteggio_2026-09-27/](pseudoconteggio_2026-09-27/) | Con il pseudoconteggio costante un gene senza conteggi valeva ln(L_c/L_t): i geni Y delle donatrici CD4 risultavano indotti dal 99–100 % dei knockdown. Correzione `min_expected` 1 (cache r9, t25); tre alternative misurate e scartate | sì | ★★★ |
| 27/09 | [universo_corretto_2026-09-27/](universo_corretto_2026-09-27/) | CD4, HCT116 e HEK293T ricostruiti con lo stimatore corretto, parità esatta sul pannello con la cache r9 | sì; sostituisce gli universi del 26/09 per queste tre sorgenti | ★★★ |
| 27/09 | [universo_kolf_2026-09-27/](universo_kolf_2026-09-27/) | KOLF2.1J (iPSC) letto a intervalli di byte dal file di 189 GB: 10.985 bersagli con effetti; `kolf_effects.py` è lo stimatore di tutti gli universi nuovi | sì; test in `tests/test_kolf_sums.py` | ★★ |
| 27/09 | [universo_hipsci_2026-09-27/](universo_hipsci_2026-09-27/) | HIPSCI: schermo mirato di 444 bersagli in 19 linee iPSC (il gene bersaglio scende in 15); lo schermo genome-wide ha solo 12–36 cellule non mirate, quindi i suoi universi usano come controlli anche le cellule senza guida assegnata (`_ua1`, come gli autori), che entrano nella rete r2 | in parte: le quattro linee con silenziamento debole vanno trattate a parte; gli universi `_ua1` possono tirare gli effetti verso zero | ★★ (la prova più pulita dell'interazione bersaglio × linea) |
| 27/09 | [universo_nuovi_2026-09-27/](universo_nuovi_2026-09-27/) | Ingestione generica di h5ad scaricati (A549 knockout, Southard CRISPRa, VIPerturb-seq) e controllo sul bersaglio di sei universi: il gene scende ovunque, da −1,81 (K562) a −0,62 (HEK293T) | sì | ★★ |
| 27/09 | [profondita_silenziamento_2026-09-27/](profondita_silenziamento_2026-09-27/) | Bersaglio per bersaglio, un silenziamento più profondo va con una risposta più grande in tutte le coppie di linee, ma debolmente (pendenze 0,09–0,46); fra sorgenti la relazione non tiene | sì, esplorativo | ★ |
| 27/09 | [ricerca_sorgenti_2026-09-27/](ricerca_sorgenti_2026-09-27/) | Nessun dataset pubblico con gli stessi bersagli in cinque o più tipi cellulari; struttura di KOLF2.1J; piano d'ingestione | sì, catalogo | ★ |
| 26/09 | [universo_2026-09-26/](universo_2026-09-26/) | Gli universi genome-wide sull'asse ufficiale: K562 (9.866 bersagli), CD4 (12.238), Orion HCT116 (16.438) e HEK293T (17.270), K562 essential e RPE1; parità esatta con le cache del pannello | in parte: CD4 e le due Orion sono superati da `universo_corretto_2026-09-27/`; K562, K562 essential e RPE1 valgono | ★★★ (i dati per i bersagli nuovi del 22/10) |
| 26/09 | [ricerca_sorgenti_2026-09-26/](ricerca_sorgenti_2026-09-26/) | HIPSCI CRISPRi a catalogo; che cosa dicono le pagine pubbliche della gara (lo zero della `mse` è la risposta media del contesto) | sì, catalogo | ★ |
| 25/09 | [ricerca_sorgenti_2026-09-25/](ricerca_sorgenti_2026-09-25/) | Ricerca multi-agente: provenienza dei log2FC Mixscale, microglia, K562 in Flex, catalogo delle sorgenti nuove; il rapporto di antigravity ha errori di metodo segnalati | sì, catalogo di candidati | ★ |
| 24/09 | [schede_sorgenti_2026-09-24/](schede_sorgenti_2026-09-24/) | Schede di 17 sorgenti candidate nel formato di GENERALIZZAZIONE §2, con seconda verifica di grok | sì, candidati | ★ |
| 24/09 | [pattern_mixscale_2026-09-24/](pattern_mixscale_2026-09-24/) | Rianalisi dei 1.626 confronti Mixscale: eterogeneità per bersaglio e stimolo, specificità dei segni | sì, esplorativo | ★ |
| 24/09 | [dld1_ceiling_2026-09-24/](dld1_ceiling_2026-09-24/) | Tetto di riproducibilità dentro DLD-1 (0,070 di correlazione per bersaglio) contro 0,014–0,027 verso le nostre sorgenti | sì, esplorativo | ★ |
| 24/09 | [dld1_audit_2026-09-24/](dld1_audit_2026-09-24/) | DLD-1 e inventario Mixscale: 67/300 bersagli, 2.587 geni ufficiali; non adottata | sì | ★ |
| 23/09 | [orion_2026-09-23/](orion_2026-09-23/) | Stadio 102 (Orion per lotto GEM), la regola del t11 scritta prima, e la cache r5 dello stadio 98 con HCT116 e HEK293T | sì | ★★ (produzione) |
| 22/09 | [multisource_2026-09-22/](multisource_2026-09-22/) | Stadio 98 e regola del t08. Alla radice il **primo run difettoso** (SE di CD4 sbagliato): non usarlo; `r2/` e `r3/` sono corretti | in parte: usare solo `r2/` e `r3/` | ★★ |
| 22/09 | [cd4_rows_2026-09-22/](cd4_rows_2026-09-22/) | Stadio 97: righe pseudobulk CD4 del pannello lette per intervalli di byte da S3 (297/300 bersagli) | sì | ★★ (produzione) |
| 17/09 | [k562_sc_2026-09-17/](k562_sc_2026-09-17/) | Stadio 71 su Colab: prima lettura completa del K562 genome-wide a singola cellula (1.989.578 cellule), md5 verificato; `x001` è un segnaposto fallito | storico | ★ |
