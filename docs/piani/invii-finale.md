# S-INVII — validazione e set finale

- **Stato:** in corso: t18 registrato, in generazione; secondo candidato in valutazione.
- **Aggiornato:** 25 settembre 2026, 03:35 (ora italiana).
- **Assegnazione:** lettura di t16/t17 (fatta), t18 e candidato successivo: Claude (app,
  sessione `f4f38e58`), 25/09. Non assumere che lo slot sia libero.

## Esiti del 25 settembre

- **t16** +0,137627, rango 336, nuovo migliore; regola: la curva sale, il prossimo passo è
  l'ampiezza 1,576 ([CP-0037](../checkpoints/0037-t16-ampiezza-quadrupla.md)).
- **t17** +0,108774: non attribuibile per la sua regola; HEK293T resta fuori dalla ricetta di
  riferimento ([CP-0038](../checkpoints/0038-t17-hek293t-non-attribuibile.md)).
- **t18** = t16 × 2 in ampiezza: registrato alle 01:30 UTC
  (`reports/prediction_t18_2026-09-25/prediction.json`); l'invio aspetta il via del proprietario.
- **Scopo:** mantenere visibili le scadenze e le prove operative mentre procede la ricerca.

## Prossima azione

Generare e impacchettare il t18, poi chiedere al proprietario il via per l'invio del 26;
registrare il secondo candidato solo se il confronto col t16 a parità di geni rilevabili lo
giustifica. [PROGETTO](../PROGETTO.md) §0 conserva lo stato e i punteggi; [LAVORO](../LAVORO.md)
§2 conserva procedura e autorizzazioni. Questa scheda non invia, non pianifica automazioni e non
cambia le preregistrazioni.

| Ordine | Lavoro aperto | Dipendenza / risultato atteso |
|---|---|---|
| 1 | Lettura t16 e t17 | **Fatta** il 25 settembre: CP-0037 e CP-0038 |
| 2 | Curva dell'ampiezza | t18 (1,576) registrato; la sua regola decide il passo dopo |
| 3 | Attribuzione dei pesi/sorgenti | Ablazione dei pesi t11 e sorgenti ad ampiezza scelta; isolare ciò che il confronto permette |
| 4 | Set finale | Preparazione secondo LAVORO §7; nuovi controlli, assi e bersagli al rilascio previsto del 22 ottobre; chiusura invii il 5 novembre |

**Candidato dal banco del 25 settembre**, corretto dopo due revisioni indipendenti
([CP-0039](../checkpoints/0039-banco-varianti-restrizione.md)): effetti ristretti prima della
media, sulla ricetta del t16. Il guadagno sul PDS proxy è +0,01…+0,04, non i +0,08…+0,12
scritti prima della revisione, e a parità di ampiezza gli effetti ristretti muovono molti meno
geni: il confronto va fatto col t16 a parità di geni rilevabili. Lo stadio 100 supporta
`"effect": "zshrink"` con `"shrink_k"` e ricostruisce `cd4_mix` dalle condizioni. Il filtro
dei bersagli difficili è stato respinto.

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
