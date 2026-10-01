# Testi delle sottomissioni preparate il 1 ottobre

## t29

Scritto il 1 ottobre alle 14:07 (ora italiana), subito dopo la registrazione del t29 (12:06 UTC) e prima
dell'esportazione degli effetti e della generazione. Previsione e regola di lettura in
`reports/invii/prediction_t29_2026-10-01/prediction.json`. Il proprietario ha autorizzato l'invio in chat (1/10,
00:29) e ha chiesto alle 12:45 perché il modello non fosse ancora caricato.

**Model name:** `trial-29 single-cell network (descriptors arm) with the trial-22 generator`

**Description:**

A neural network trained directly on the counts of single cells (negative binomial likelihood on the genes each
source measures, a mixture of responding and escaping cells, the context encoded from control cells, the target
encoded from biological descriptors of its gene), on 3.35 million cells of public CRISPR screens: Replogle et al.
2022 (K562 and RPE1), Nadig et al. 2025 (Jurkat; HepG2 held out for evaluation), the H1 training and validation data
of the 2025 Virtual Cell Challenge, and HipSci iPSC CRISPRi screens. One seed, 3.8 epochs. The effects of the 300
targets of each context are exported from 2,048 control cells of that context and turned into cells with the same
generator and settings as trial-22. A technical check of the network path, not tuned on the leaderboard.
