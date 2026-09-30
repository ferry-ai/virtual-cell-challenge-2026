# Stack A: pilot negativo, nessuna promozione

Misurato il 29 settembre 2026. Il job 082 termina con codice 0 alle 20:53:18 UTC;
gli originali completi sono in `stack_a_scoring_r2/`. Il calcolo riuscito non
implica un modello migliore: la regola scientifica del pilot è fallita.

Sui dodici bersagli pubblici HepG2 congelati, Stack A contro il trasferimento:

| Misura | Trasferimento | Stack A |
|---|---:|---:|
| PDS del pannello locale | 0,871212 | 0,537879 |
| MSE normalizzata grezza | 1,448774 | 1,303689 |
| nMAE degli effetti DE | 0,970208 | 0,994376 |
| Fedeltà direzionale | 0,481182 | 0,450569 |
| Reach direzionale | 0,108484 | 0,061073 |
| Jaccard DE | 0,047506 | 0,044218 |

La proiezione su cinque membri vale **−0,158321**, IC95% appaiato descrittivo
[−0,236758; −0,082083]; delta PDS **−0,333333**. Tutti e cinque i contributi
sono negativi. La MSE migliora, ma resta distinta dalla proiezione come previsto
prima del calcolo. La verifica del rapporto di somme della MSE passa per
entrambi i bracci. Nessun target o membro è stato eliminato dopo il risultato.

**Decisione:** A non passa alla conferma né alla produzione. Questo esperimento
misura la specifica combinazione di prompt, filtro e correzione A; non dimostra
che tutte le applicazioni di Stack siano inutili. Il PDS dipende dal pannello
locale di dodici target e non è confrontabile direttamente con quello VCC.
Non è verificata l'esclusione di HepG2 dal pretraining del modello.

La variante B era stata definita, testata e avviata prima della lettura di
questo esito. Si mantiene invariato `PROTOCOLLO_STACK_AB.md`: B deve completare
lo stesso confronto e superare la propria regola prima di una sola eventuale
conferma separata. Non si corregge A a posteriori chiamandola la stessa prova.
