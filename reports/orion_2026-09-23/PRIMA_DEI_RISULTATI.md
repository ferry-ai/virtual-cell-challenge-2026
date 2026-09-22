# Regola del t11 (t08 + Orion), scritta prima dei numeri di Orion — 23 settembre 2026

Scritta intorno alle 00:58 locali del 23 settembre. Lo streaming di Orion HCT116 era a 59 file
su 109, e nessuna misura su Orion esisteva. Autore: agente (Claude). Il proprietario ha ammesso
Orion negli invii (`reports/trial_2026-09-22/autorizzazioni.md`).

## Che cosa cambia rispetto al t08

Un solo fattore: si **aggiungono** le sorgenti Orion (HCT116 e HEK293T, pseudobulk per lotto
GEM dello stadio 102). Tutto il resto resta uguale al t08:
- cache e stimatore dello stadio 98 (effetti grezzi);
- γ = 1, ampiezza 0,197, affidabilità n/(n+100);
- generatore di trial-01 (stadio 45, `trial-ext-profile`), seme 20260912.

## Regola

1. **Sorgenti:** `k562`, `cd4_mix`, `orion_hct116`, `orion_hek293t`. Se HEK293T non è
   finalizzato quando HCT116 è pronto, il t11 usa le prime tre, e HEK293T entra in un t12 a
   parte.
2. **Pesi uguali** per tutte le sorgenti presenti (1 ciascuna), identici per A, B e C. Non si
   usa `shared_signal` per i pesi: il suo difetto di unità è documentato in CP-0028.
3. **Arresto:** se lo stadio 98 dà `pds_proxy_mean` < 0,55 fra Orion e K562 e fra Orion e CD4
   (nessun accordo specifico del bersaglio), il t11 non si costruisce. Prima si cerca un
   errore di dati: nomi dei token genici, filtro delle guide, abbinamento dei lotti.

## Che cosa si impara

- Rispetto al t08 cambia solo l'insieme delle sorgenti. Se il t11 migliora, Orion porta
  informazione nuova sui contesti ufficiali. Se peggiora, a pesi uguali Orion diluisce
  K562 e CD4.
- I pesi per lignaggio (A più vicino a CD4, B e C a linee epiteliali) sono un fattore
  successivo, da provare da solo.

La banda numerica attesa si scrive in `reports/prediction_t11_*` prima dell'invio, dopo le
misure nello spazio degli effetti e prima di qualunque punteggio ufficiale del t11.
