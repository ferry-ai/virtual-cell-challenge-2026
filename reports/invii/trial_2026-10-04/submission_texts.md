# Testi delle sottomissioni preparate il 4 ottobre

## t30

Scritto il 4 ottobre alle 10:15 (ora italiana), dopo la registrazione della previsione
(`reports/invii/prediction_t30_2026-10-04/prediction.json`, 08:14 UTC). In quel momento l'esportazione degli effetti
ibridi era in corsa e nessuna sua uscita era stata letta; la generazione non era partita. Autorizzazione: mandato del
proprietario del 4/10 notte per gli invii che passano la regola congelata del banco, trascritto in
`reports/invii/trial_2026-09-22/autorizzazioni.md`.

**Model name:** `trial-30 selective hybrid: trial-25 transfer plus a weighted single-cell network correction`

**Description:**

The trial-25 transfer recipe (shrunk effects of public CRISPRi screens, amplitude 1.576, cis head), plus a correction
proposed by a neural network trained on single cells of eight public line groups (one line held out). The network
starts from the transfer of each target as an anchor and learns a regularised deviation; a separate common-response
head absorbs what every target shares and never enters the prediction. A small selector, fitted only on lines the
network never saw, decides per target how much of the correction to keep (weight 0 to 1; about 0.3 on average,
0 for targets outside the network's training regime). On five held-out lines the selective hybrid beat its transfer
in a local six-metric bench. Generation and packaging are exactly those of trial-25: only the effects change.
