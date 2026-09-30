# S-INVII — validazione e set finale

- **Stato:** in corso. Al 28/09: il migliore è il t22 (+0,141250; con la replica t24 il riferimento
  della ricetta è 0,14207); t25 −0,0010 sul t22, non conclusivo; t23 impacchettato, aspetta il via.
  La tabella completa è in [reports/invii/README.md](../../reports/invii/README.md).
- **Aggiornato:** 28 settembre 2026 (nota della riorganizzazione D-046; il testo sotto «Esiti del
  25 settembre» e «Esito del 26 settembre» è com'era il 26/09).
- **Assegnazione:** lettura di t16/t17 (fatta), t18 e candidato successivo: Claude (app,
  sessione `f4f38e58`), 25/09. Non assumere che lo slot sia libero.
- **Scopo:** mantenere visibili le scadenze e le prove operative mentre procede la ricerca.

## Esiti del 25 settembre

- **t16** +0,137627, rango 336, nuovo migliore; regola: la curva sale, il prossimo passo è
  l'ampiezza 1,576 ([CP-0037](../checkpoints/0037-t16-ampiezza-quadrupla.md)).
- **t17** +0,108774: non attribuibile per la sua regola; HEK293T resta fuori dalla ricetta di
  riferimento ([CP-0038](../checkpoints/0038-t17-hek293t-non-attribuibile.md)).
- **t18** = t16 × 2 in ampiezza: registrato alle 01:30 UTC
  (`reports/invii/prediction_t18_2026-09-25/prediction.json`), impacchettato alle 02:25 UTC.
- **t19** = t16 con gli effetti ristretti (k 4) a 1,576: registrato alle 01:37 UTC
  (`reports/invii/prediction_t19_2026-09-25/prediction.json`), impacchettato alle 03:05 UTC.
- **t20** = t19 + modulo cis CRISPRi: registrato alle 22:04 UTC del 25
  (`reports/invii/prediction_t20_2026-09-26/prediction.json`), impacchettato alle 22:55 UTC.
- Il proprietario ha scelto di inviare **solo il t20** con la quota del 26 (00:05 UTC):
  [autorizzazioni](../../reports/invii/trial_2026-09-22/autorizzazioni.md). La catena `submit_chain3.py` è partita alle
  22:58 UTC e aspetta la quota. Senza il t19, la regola registrata legge t20 − t16, che somma
  restrizione e modulo cis senza separarli.

## Esito del 26 settembre

**t20** +0,139676, rango 346 all'invio (`reports/invii/trial_2026-09-26/status_I8FX2yQabjKjPPDTYnaW.json`).
Sul t16 +0,0020: dentro ±0,005, non conclusivo per la regola registrata, che senza il t19 legge
restrizione e modulo cis insieme ([confronto](../../reports/invii/prediction_t20_2026-09-26/comparison.json)).
PDS e reach salgono, `nmae` peggiora. La ricetta del t20 è il nuovo riferimento.

## Nota del 28 settembre: che cosa è cambiato dal 26

- **t22** (t20 + HEK293T) +0,141250, non conclusivo sul t20; **t24** (seme) +0,142897, D = 0,0016;
  **t25** (stimatore corretto) +0,140238, −0,0010: dal t16 nessun cambio supera il rumore del seme
  ([lezioni](../../reports/invii/lezioni_invii_2026-09-28/RISULTATI.md)).
- **t23** è pronto; l'[ablazione](../../reports/trasferimento/ablazione_t23_2026-09-27/RISULTATI.md)
  dice che ne conta l'esclusione dei geni, non la pesatura.
- **Le proposte** della [revisione critica](../../reports/analisi/revisione_criticita_2026-09-28/REVISIONE.md)
  §6 sono, dalle 12:30 del 28/09 e su richiesta del proprietario, la scheda [R-REV](revisione-critica.md).
  Toccano questa scheda:
  - la regola per chi propone un invio (sotto 0,005 non si legge);
  - la taratura del proxy sulle differenze ufficiali (azione 2);
  - la prova generale del 22/10 con la scelta scritta su γ e sulla cache, e l'ampiezza di D/E/F da
    una regola dei controlli (azioni 3 e 4);
  - una ricetta di riserva senza Orion finché la licenza non è verificata (azione 7).

## Prossima azione

Il prossimo invio porta il modello di [R-V2](modello-v2.md) quando il suo banco lo giustifica,
con previsione e regola registrate prima; il t19 resta pronto per separare restrizione e modulo
cis se serve. [PROCEDURE](../PROCEDURE.md) §2 conserva procedura e autorizzazioni.

| Ordine | Lavoro aperto | Dipendenza / risultato atteso |
|---|---|---|
| 1 | Lettura t16 e t17 | **Fatta** il 25 settembre: CP-0037 e CP-0038 |
| 2 | Curva dell'ampiezza | t18 (1,576) registrato; la sua regola decide il passo dopo |
| 3 | Attribuzione dei pesi/sorgenti | Ablazione dei pesi t11 e sorgenti ad ampiezza scelta; isolare ciò che il confronto permette |
| 4 | Set finale | Preparazione secondo PROCEDURE §7; nuovi controlli, assi e bersagli al rilascio previsto del 22 ottobre; chiusura invii il 5 novembre |

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

- [Preregistrazione t16](../../reports/invii/prediction_t16_2026-09-24/prediction.json).
- [Preregistrazione t17](../../reports/invii/prediction_t17_2026-09-24/prediction.json),
  con [CP-0034](../checkpoints/0034-audit-segni-e-ampiezza.md) e R-016 nel [registro](../REGISTRO.md).
- D-042 in [DECISIONI](../DECISIONI.md), [CP-0033](../checkpoints/0033-t15-ampiezza-doppia.md).

**Passaggio di consegne:** nessun invio, stato server o nuova autorizzazione verificati
con l'introduzione di questo indice; consultare le fonti operative aggiornate.
