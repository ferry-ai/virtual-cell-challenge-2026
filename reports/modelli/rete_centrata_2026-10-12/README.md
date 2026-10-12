# Rete ponte centrata sul pannello (`ta 40`): piano a tappe del 12 ottobre

Nomi secondo D-058 di `main`: `ta XX` per Alfredo, `td XX` per Davide. Qui il t39 di Alfredo è `ta 39`; il t40
registrato prima di leggere D-058 è `ta 40` ([NOMI.md](../../invii/prediction_ta40_2026-10-12/NOMI.md)).

Claude Code per Alfredo, 12 ottobre 2026, ore 21:30 CEST. Alfredo ha chiesto in chat di sperimentare e di mandare
qualcosa a valutare sul sito entro le 02:00 CEST, cioè la mezzanotte UTC, quando si azzera la quota.

## Perché questa variante

- [ESITO_T39](../../analisi/prove_per_davide_2026-10-07/ESITO_T39.md) ha lasciato aperta una sola verifica.
  `ta 39` ha perso il membro PDS:
  - −0,055 scalato rispetto a `td 28`;
  - −0,023 rispetto a `ta 36`.
- **Ipotesi:** la causa è la risposta comune che il residuo appreso aggiunge a tutti i bersagli. Sul sito vale circa
  l'1% dell'energia; sulle linee del cubo dal 2 al 31%.
- **La rete centrata** toglie al residuo la sua media sui 300 bersagli del pannello, usando solo le previsioni. È il
  braccio `rete_centrata` di
  [EMENDAMENTO_R2](../rete_ponte_jepa_2026-10-09/EMENDAMENTO_R2.md).
- Rispetto a `ta 39` cambia solo il centramento, quindi il confronto `ta 40` − `ta 39` è pulito.
- **Il tetto è piccolo** (criterio d'impatto minimo): al meglio circa +0,01 su `ta 39`, cioè circa 0,151. Lo scegliamo
  perché è l'unico candidato appreso che si costruisce, genera e carica nella finestra di oggi, e che risponde a una
  domanda registrata.

## Codice

[esporta_rete_centrata.py](esporta_rete_centrata.py) è una copia di
[esporta_rete.py](../rete_ponte_jepa_2026-10-09/esporta_rete.py), che resta com'era, con in più l'opzione
`--centrata`.
- La rete ([rete_ponte.py](../rete_ponte_jepa_2026-10-09/rete_ponte.py)) è importata senza modifiche.
- Gli stessi 10 semi (2–11) sono riaddestrati su tutti i gruppi del cubo.
- Il residuo è centrato sul pannello di ciascun contesto, poi ogni bersaglio è riportato alla norma di `all` × 1,576.

## Tappe

| Tappa | Che cosa | Esce |
|---|---|---|
| M1 | Previsione e regola registrate, committate prima di generare | [prediction.json](../../invii/prediction_ta40_2026-10-12/prediction.json) |
| M2 | Esportazione A/B/C della rete centrata | `vcc2026-data/processed/effects_rete_centrata_2026-10-12` |
| M3 | Stadio 45 (emissione di `td 28`) e stadio 48 (validatore ufficiale) | `artifacts/t40gen`, `artifacts/t40pack` |
| M4 | Caricamento del `ta 40`, una sola quota del giorno | ricevute in [trial_rlead_2026-10-12](../../invii/trial_rlead_2026-10-12/) |
| M5 | Lettura con il lettore registrato, esito per Davide, push | `comparison.json`, `ESITO.md` qui |
