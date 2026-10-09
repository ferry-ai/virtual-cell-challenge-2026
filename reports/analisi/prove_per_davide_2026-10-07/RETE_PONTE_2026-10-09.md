# Per Davide: la rete ponte del 9 ottobre

La rete addestrata sul cubo r2 (JEPA + SIGReg di LeJEPA, attenzione sulle sorgenti, residuo a basso rango, InfoNCE
fra i bersagli) e il suo esito sul banco sono in
[reports/modelli/rete_ponte_jepa_2026-10-09/ESITO.md](../../modelli/rete_ponte_jepa_2026-10-09/ESITO.md).

**I numeri** (insieme di cinque reti contro `all`, una linea tenuta fuori alla volta, misura dello stadio 1):

| | r3 (semi 2–6) | r4 (semi 7–11) | Linee con l'IC del coseno sopra 0 |
|---|---|---|---|
| Coseno | +0,050 | +0,046 | 5/5 in entrambe |
| PDS | +0,021 | +0,013 | |
| PDS di H1 | −0,044 | −0,053 | |

La regola registrata **non passa** per la guardia di H1.

**Che cosa ti serve:**
- **Gli effetti esportati per A/B/C** stanno in `vcc2026-data/processed/effects_rete_ponte_2026-10-09`, con
  `export.json`; gli hash sono in [esito/export_rete.json](../../modelli/rete_ponte_jepa_2026-10-09/esito/export_rete.json).
- **Lo script è [esporta_rete.py](../../modelli/rete_ponte_jepa_2026-10-09/esporta_rete.py):** gira in circa un
  minuto su GPU e si può rifare sopra la banca estesa, se il cubo viene ricostruito con le linee in più.
- **Il t39 provvisorio** (rete + emissione del t28) è registrato e in preparazione, ma non è inviato: decide Alfredo.
