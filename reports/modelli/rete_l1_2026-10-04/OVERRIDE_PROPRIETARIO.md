# Decisione del proprietario: invio della `rete_anti` nonostante la regola

4 ottobre 2026, sera, dopo l'[ESITO](ESITO.md). Trascrizione della chat.

- **Il fatto:** la `rete_anti` non passa la regola dell'addendum 1, perché H1 vale 1,121.
- **La risposta dell'agente al proprietario:** il meccanismo è valido, ma la magnitudine è tarata su linee rumorose.
  Se A, B, C si comportano come H1, l'nMAE del t35 può peggiorare.
- **Il proprietario** («ti assicuro che è una variante validissima») ha scelto l'opzione **«Invia rete_anti,
  override»**: generare e inviare la `rete_anti` così com'è nel primo slot del 5/10 UTC.
- **La regola di lettura del punteggio** resta quella registrata in
  `reports/invii/prediction_t35_2026-10-04/prediction.json`.
  - La previsione registrata è stata scritta per la rete prima del banco. Dopo H1, l'agente la ritiene ottimista: la
    sua stima è da −0,01 a +0,02.
  - La banda non si sposta.
- **Prima di generare** si esegue `verifica_slide.py` su blocchi reali, e il suo esito si riporta.
- **Modello finale:** `rete_anti` su tutti i gruppi, 3.500 passi (mediana dei passi scelti nelle pieghe).
