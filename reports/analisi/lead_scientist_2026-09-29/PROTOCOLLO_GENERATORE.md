# Ampiezza e dispersione: confronto separato dal banco K562 in corso

**Registrazione:** 29 settembre 2026, prima dell'esecuzione del banco.
**Tipo:** esperimento locale su un contesto pubblico escluso dalle sorgenti; non punteggio VCC.

## Perché

Il generatore Poisson riduce la variabilità biologica e produce chiamate anche a effetto nullo.
La dispersione per gene fu esclusa nel t13 in base alla pulizia del nullo; il t14 cambiò insieme
generatore e ampiezza, su effetti diversi dagli attuali. Nessuna delle due prove identifica
l'ottimo congiunto per la ricetta corrente. La sola riduzione delle chiamate spurie non sarà
criterio di promozione in questo esperimento.

## Disegno prima di misurare

- Verità: cellule HepG2 pubbliche in `raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad`.
- Sorgente: effetti K562 congelati in `processed/banco_hepg2_v2_2026-09-26/t19like.npz`;
  nessuna risposta HepG2 entra nel predittore. Il pannello eleggibile è quello già congelato
  in quella cartella, ristretto ai bersagli presenti nominalmente nell'asse di risposta.
- Il mascheramento dei geni non misurati da K562 viene ricostruito dal suo asse originale;
  uno zero ristretto non è trattato come gene assente.
- Split dei bersagli con seme 20260929, scritto in un manifest prima dello scoring:
  primi 48 per sviluppo, successivi 96 per verifica separata. Una disponibilità inferiore
  si riporta, senza sostituire bersagli dopo averne visto le metriche.
- Controlli: campione fisso di 2.000 cellule, per memoria. Verità e replica: metà disgiunte
  per bersaglio, seme 2026. Nessun campione si cambia fra bracci.
- Ogni previsione contiene 400 cellule per bersaglio, come in gara. È diverso dai precedenti
  banchi che generavano tante cellule quante la metà di verità. La verità rimane meno profonda
  di quella ufficiale: il limite è esplicito.
- Griglia sviluppo: ampiezza relativa {1; 1,5; 2} × scala della dispersione {0; 0,25; 0,5; 1}.
  La scala 0 coincide con Poisson; 1 usa la dispersione che riproduce gli zeri dei controlli.
  Profilo e spostamento composizionale seguono lo stadio 45. Le librerie sono estratte dalla
  distribuzione osservata; RNG separati per bersaglio e seme rendono l'ordine dei bracci irrilevante.
- Seme generativo sviluppo: 1. Verifica separata: 1, 2, 3, solo riferimento e al massimo due
  finalisti selezionati sullo sviluppo. Si confrontano anche ampiezza e dispersione separatamente.

## Metriche e selezione

Tutti i sei membri sono calcolati dallo scorer installato. Si conservano aggregati, valori
per bersaglio e componenti della fedeltà (`n_pred`, `n_conf`, `k`). Versione del software,
hash degli input e semi accompagnano ogni risultato.

Per ordinare lo sviluppo si usa la variazione di cinque membri con le pendenze delle
ancore ufficiali in `reports/gara/anchors_2026-09-17/anchors.json`, divisa per sei;
il contributo MSE è posto a zero come negli invii della famiglia corrente. Questa è una
**proiezione locale**, non il punteggio ufficiale. La MSE grezza e il punteggio con ancore
locali si riportano separatamente; una MSE locale che guadagna non viene ignorata nella lettura.

Il riferimento è ampiezza 1, dispersione 0. Passano allo split separato i due migliori
bracci distinti con differenza positiva, oppure uno se gli altri non migliorano. In caso
di differenza inferiore a 0,002, precede la modifica più piccola dell'ampiezza, poi della
dispersione. Non si aggiungono valori intermedi sulla base dei risultati.

Per sostenere una proposta di candidato dal banco, nella verifica separata si richiede:

1. differenza media almeno +0,005 nella proiezione locale;
2. differenza positiva in ciascuno dei tre semi;
3. limite inferiore sopra zero nel bootstrap appaiato per bersaglio (2.000 campioni), con
   intervallo al 97,5% se si verificano due finalisti, al 95% se uno;
4. nessun errore di allineamento, cambio dei bersagli valutati o artificio di generazione.

Si riporta a parte la variabilità fra semi: il bootstrap sui bersagli non la sostituisce.
Un fallimento chiude questa promozione dal banco, non ogni possibile generatore. La scelta
di un esperimento ufficiale basata su altra evidenza deve dichiarare il motivo e registrare
una previsione nuova; non può essere descritta come superamento di questa regola.

## Limiti e prove aggiuntive

HepG2 è un solo contesto e il pannello contiene bersagli essenziali. I 2.000 controlli hanno
meno potenza del riferimento ufficiale. La maschera dello stadio 45 differisce dal vecchio
percorso `g0:` dello stadio 75: il nuovo riferimento va ricalcolato. La verifica separata
impedisce di scegliere sulla stessa lista che giudica, ma non è uno studio indipendente.

Una eventuale variante che preserva la dipendenza fra profondità e composizione dei controlli
è un'altra ipotesi: prima di valutarla riceve un protocollo separato. Non si inserisce nella
griglia dopo aver visto il suo esito.
