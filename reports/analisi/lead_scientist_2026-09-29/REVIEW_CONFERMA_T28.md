# Revisione indipendente della conferma e della registrazione t28

29 settembre 2026, dopo la disponibilità della conferma completa. **Misurato e
revisione documentale**, senza nuovi esperimenti né modifica dei report originari.

Non sono emerse incongruenze numeriche o conclusioni presentate come fatti senza
supporto in `RISULTATI_GENERATORE_CONFERMA.md` e nella registrazione
`reports/invii/prediction_t28_2026-09-29/prediction.json`.

Verificati nuovamente gli hash dei 41 file in `generator_confirmation_r3/` e
l'hash di `confirmation_analysis/results_r1/analysis.json` registrato per t28.
I delta per seme sono stati ricostruiti dai grezzi aggregati e dalle pendenze delle
ancore, indipendentemente dal lettore della conferma. I quantili 1,25% e 98,75%
sono stati ricalcolati dai 2.000 draw salvati: coincidono ai limiti numerici.

| Controllo | Ampiezza 1,5 / dispersione 1 |
|---|---:|
| Delta della proiezione, somma dei cinque membri / sei | +0,028917710507 |
| Delta dei tre semi | +0,034250048; +0,023373019; +0,029130064 |
| IC appaiato 97,5% | [0,019525635; 0,039341896] |
| Deviazione standard fra i tre semi | 0,005441623 |
| Bersagli con contributo positivo | 73/96 |
| Quota netta dei primi cinque | 26,6637% |
| MSE grezza media sui semi | 1,214243 → 1,595799 |
| Precisione direzionale pooled, media sui semi | 0,548782 → 0,580152 |
| Variazione media delle chiamate / accordi | +28,8837% / +36,2515% |

Anche il secondo finalista ricostruisce i valori registrati: delta +0,023031414,
IC97,5% [0,013353814; 0,033183479], tre semi positivi. Le due promozioni seguono
le soglie congelate. Il primo era già primo nello sviluppo: nessuna nuova
combinazione viene ricavata dalla conferma.

**Interpretazione:** il guadagno è prevalentemente di fedeltà direzionale e reach,
con peggioramento di NMAE, Jaccard e MSE; il PDS medio è sostanzialmente invariato.
La primaria pone MSE a zero per costruzione. Non dimostra quindi un miglioramento
uniforme delle sei metriche, né l'attribuzione separata ad ampiezza o dispersione.
Il testo conserva entrambe le distinzioni.

**Limite correttamente dichiarato:** HepG2 è un singolo studio pubblico, i target
non sono quelli della gara e gli effetti vengono da K562; t28 amplifica invece
l'intero vettore multisorgente t25, compresi own/cis incorporati. La validazione
locale seleziona una combinazione promettente, non misura l'intera pipeline t28
nei contesti A/B/C. La banda ufficiale [0,135; 0,180] e il centro 0,155 sono
esplicitamente soggettivi, senza calibrazione empirica; non vanno trasformati
in intervalli statistici o garanzie di guadagno. Nessun invio è autorizzato dal banco.

**Difetto editoriale segnalato al lead:** nella versione letta di
`reports/invii/trial_2026-09-29/submission_texts.md` compaiono due blocchi t28
identici, alle righe 3 e 16. Non cambiano la specifica scientifica; questa nota
non modifica il documento storico.
