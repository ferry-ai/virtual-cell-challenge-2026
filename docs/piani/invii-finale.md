# S-INVII — validazione e set finale

- **Stato:** in attesa dei risultati delle prove preparate e delle dipendenze sotto.
- **Aggiornato:** 25 settembre 2026, 00:45 (ora italiana). La catena di invio del 24
  (`submit_chain.py`, processo vivo alle 00:12) invia il t16 dalle 00:05 UTC e poi il t17.
- **Assegnazione:** lettura di t16/t17 e preparazione del candidato successivo: Claude (app,
  sessione `f4f38e58`), 25/09. Non assumere che lo slot sia libero.
- **Scopo:** mantenere visibili le scadenze e le prove operative mentre procede la ricerca.

## Prossima azione

Verificare stato effettivo di t16/t17 con l'agente che li segue, poi leggere i
risultati con le regole registrate. [PROGETTO](../PROGETTO.md) §0 conserva lo stato
e i punteggi; [LAVORO](../LAVORO.md) §2 conserva procedura e autorizzazioni.
Questa scheda non invia, non pianifica automazioni e non cambia le preregistrazioni.

| Ordine | Lavoro aperto | Dipendenza / risultato atteso |
|---|---|---|
| 1 | Lettura t16 e t17 | Risultati ufficiali; confronto con le rispettive regole, con il limite causale del t17 |
| 2 | Curva dell'ampiezza | Esito t16; registrare il prossimo confronto prima di generare |
| 3 | Attribuzione dei pesi/sorgenti | Ablazione dei pesi t11 e sorgenti ad ampiezza scelta; isolare ciò che il confronto permette |
| 4 | Set finale | Preparazione secondo LAVORO §7; nuovi controlli, assi e bersagli al rilascio previsto del 22 ottobre; chiusura invii il 5 novembre |

**Candidato dal banco del 25 settembre** ([banco a sorgente esclusa](../../reports/banco_varianti_2026-09-25/RISULTATI.md)):
effetti ristretti (grezzo × z²/(z² + 64)) al posto dei grezzi, ampiezza con la regola del q99,
sulla ricetta migliore dopo t16/t17. Nei proxy batte il t15 in tutte e quattro le sorgenti
escluse, anche con un modello del rumore del generatore; non è un punteggio VCC. Serve
un'opzione nuova dello stadio 100. Il filtro dei bersagli difficili è stato respinto.

## Criterio di chiusura per ciascuna prova

Confronto registrato, evidenza ufficiale e checkpoint; aggiornare PROGETTO quando
il punteggio è noto. Per il finale, evidenza di convalida e stato dell'invio, senza
trasferire automaticamente parametri di A/B/C a D/E/F come se fossero validati.
Ogni sottoattività si chiude separatamente; la ricerca su bersagli nuovi resta
in [R-MODELLI](trasferimento-modelli.md), non si confonde con same-target transfer.

## Riferimenti

- [Preregistrazione t16](../../reports/prediction_t16_2026-09-24/prediction.json).
- [Preregistrazione t17](../../reports/prediction_t17_2026-09-24/prediction.json),
  con [CP-0034](../checkpoints/0034-audit-segni-e-ampiezza.md) e R-016 nel [registro](../REGISTRO.md).
- D-042 in [DECISIONI](../DECISIONI.md), [CP-0033](../checkpoints/0033-t15-ampiezza-doppia.md).

**Passaggio di consegne:** nessun invio, stato server o nuova autorizzazione verificati
con l'introduzione di questo indice; consultare le fonti operative aggiornate.
