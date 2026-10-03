# Testi della sottomissione preparati il 3 ottobre

## t30 (candidato M4, non ancora autorizzato all'invio)

Scritto il 3 ottobre alle 15:55, ora italiana. In quel momento il kernel `rete-sorgenti-r1` stava ancora girando:
- il voto della rete non era noto;
- nessun effetto per A, B e C era stato esportato o generato.

Previsione e regola di lettura in `reports/invii/prediction_t30_2026-10-03/prediction.json`. L'invio richiede l'ok del
proprietario in chat, dato con il pacchetto pronto, e l'accordo con Davide sulla quota della squadra.

**Model name:** `trial-30 source-attention transfer network with the trial-22 generator`

**Description:**

A small network that learns how much to trust each public CRISPRi screen when transferring measured knockdown
effects to a cell context never seen perturbed. The weights come from the control cells' expression profiles only.
Each effect it outputs is a weighted average of effects measured for the same target in other cell lines. It invents
no effect, and it has no parameter per target. At initialisation it is the equal-weight average over line groups.

It was trained by leave-one-line-out on public screens:
- Replogle et al. 2022 (K562 genome-wide and essential, RPE1);
- the HipSci iPSC CRISPRi screens;
- Tian et al. 2019 and 2021 (iPSC and induced neurons).

KOLF2.1J and Jurkat (Nadig et al. 2025) served only for early stopping. The H1 data of the 2025 challenge and HepG2
(Nadig et al. 2025) were held out for evaluation. Here only the training screens serve as sources. The effects are
turned into cells with the same generator and settings as trial-22. One seed, one checkpoint.
