# Revisione lead del 29–30 settembre (Codex): indice per ambito

Cartella di evidenza della sessione lead di Codex (`01a0ee03-b357-7012-81a9-e8d7de767478`), dal
29/09 alle 18:33 al 30/09 alle 01:13. Contiene circa 1.070 file: questo indice dice che cosa
leggere per ambito. L'ha scritto Claude (sessione `dcf3a1b9`) il 30/09, senza toccare gli altri
file della cartella, che restano la registrazione di quella sessione.

**Leggi prima:** [SCOPERTE_R1](SCOPERTE_R1.md) e [SCOPERTE_R2](SCOPERTE_R2.md), le scoperte con il
loro tipo di affermazione e le prove; poi [CP-0052](../../../docs/checkpoints/0052-t28-punteggio-ufficiale.md),
il punteggio ufficiale del t28.

| Checkpoint | In una riga |
|---|---|
| [CP-0046](../../../docs/checkpoints/0046-audit-lead-e-due-vie-neurali.md) | Revisione: il plateau non prova saturazione; CD4 è già Flex; due vie neurali registrate |
| [CP-0047](../../../docs/checkpoints/0047-conferma-generatore-t28.md) | Il banco ampiezza × dispersione passa la sua conferma; t28 registrato prima di generare |
| [CP-0048](../../../docs/checkpoints/0048-rete-sorgenti-primo-seme.md), [CP-0049](../../../docs/checkpoints/0049-rete-sorgenti-replica.md) | La rete che pesa le sorgenti resta sotto la soglia in due semi |
| [CP-0050](../../../docs/checkpoints/0050-credibilita-score-e-riserva.md) | Le ancore aggregate non sono esatte; 95/96 bersagli della conferma erano già stati valutati |
| [CP-0051](../../../docs/checkpoints/0051-stack-ab-negativi.md) | Stack A e B perdono contro il trasferimento |
| [CP-0052](../../../docs/checkpoints/0052-t28-punteggio-ufficiale.md) | t28 = +0,144845, nuovo massimo osservato, non conclusivo per la sua regola |

## Sintesi e mandato

| File | Che cosa |
|---|---|
| [SCOPERTE_R1.md](SCOPERTE_R1.md) | Scoperte e conseguenze pratiche, prima dell'invio t28 |
| [SCOPERTE_R2.md](SCOPERTE_R2.md) | Correzioni successive: riserva già valutata, ancore non esatte, copertura del training |
| [PROTOCOLLO.md](PROTOCOLLO.md) | Mandato del proprietario e ipotesi della sessione, scritti prima degli esperimenti |
| [VERIFICA_FINALE.md](VERIFICA_FINALE.md) | Checker e suite di test del 29/09 sera |
| [CALCOLO.md](CALCOLO.md) | Colab, Kaggle e le autorizzazioni ricevute |

## Audit

| File | Che cosa |
|---|---|
| [AUDIT_SCIENTIFICO.md](AUDIT_SCIENTIFICO.md) | 17 invii ricostruiti; compensazioni fra membri; cinque inferenze corrette (plateau, semi, t26, risposta comune, ortogonalità) |
| [AUDIT_DATI.md](AUDIT_DATI.md) | CD4 è GEM-X Flex v1; stati CD4; VIPerturb-seq; normalizzazione dei basali; sorgenti non intercambiabili |
| [AUDIT_GENERATORE.md](AUDIT_GENERATORE.md) | Dal profilo alle cellule: media dei CPM per cellula contro composizione aggregata |
| [SCORE_CREDIBILITA.md](SCORE_CREDIBILITA.md) | Ricostruzione degli score del banco; le ancore aggregate non convertono esattamente |
| [SCORE_BIAS_DATI.md](SCORE_BIAS_DATI.md), [precisazione](SCORE_BIAS_DATI_PRECISAZIONE.md) | Separazioni e riuso dei bersagli: la conferma non era una riserva mai valutata |
| [TRAINING_COPERTURA.md](TRAINING_COPERTURA.md) | Dataset acquisiti, trasformati e davvero usati dai modelli |

## Generatore e t28

| File o cartella | Che cosa |
|---|---|
| [PROTOCOLLO_GENERATORE.md](PROTOCOLLO_GENERATORE.md), [emendamento 1](EMENDAMENTO_GENERATORE_01.md), [emendamento 2](EMENDAMENTO_GENERATORE_02.md) | Banco a 14 bracci registrato prima degli score |
| [RISULTATI_GENERATORE_SVILUPPO.md](RISULTATI_GENERATORE_SVILUPPO.md) | 48 bersagli: ampiezza e dispersione interagiscono |
| [RISULTATI_GENERATORE_CONFERMA.md](RISULTATI_GENERATORE_CONFERMA.md), [revisione](REVIEW_CONFERMA_T28.md) | 96 bersagli e tre semi: +0,028918 di indice locale, non un punteggio VCC |
| `confirmation_analysis/`, `confirmation_biology/` | Ricostruzione indipendente e diagnostica biologica post hoc |
| `generator_development_r3/`, `generator_confirmation_r3/` | I report originali dei job, copiati con manifest |
| `generatore/` | Generatore per classi di profondità, nullo, parità con la produzione |
| [VERIFICA_CODICE.md](VERIFICA_CODICE.md) | Test delle modifiche allo stadio 45 |
| `candidate_generation_remote/` | Generazione e recupero del t28, con ricevute |

L'invio e il punteggio stanno in `reports/invii/trial_2026-09-29/` (`INVIO_T28.md`,
`DECISIONE_INVIO_T28.md`) e in `reports/invii/prediction_t28_2026-09-29/`.

## Rete sulle sorgenti

| File o cartella | Che cosa |
|---|---|
| [PROTOCOLLO_NEURALE.md](PROTOCOLLO_NEURALE.md), [VALIDAZIONE_NEURALE.md](VALIDAZIONE_NEURALE.md) | Protocollo prospettico e verifiche su dati sintetici |
| [lettore](EMENDAMENTO_LETTORE_NEURALE_01.md), [calendario](EMENDAMENTO_NEURALE_SCHEDULING_01.md) | Emendamenti scritti prima di leggere gli esiti |
| [RISULTATI_NEURALE_SEED0.md](RISULTATI_NEURALE_SEED0.md), [REVIEW_CP0048.md](REVIEW_CP0048.md), [RISULTATI_NEURALE_SEED1.md](RISULTATI_NEURALE_SEED1.md) | Due semi: +0,0022 e +0,0025 contro la soglia +0,01 |
| [ADATTATORE_T25.md](ADATTATORE_T25.md) | Riapplicazione alla ricetta t25: proposta, non usata in produzione |
| `kaggle_neural_r1/`, `kaggle_neural_seed1_r1/`, `neural_two_seeds_r1/` | Le corse Kaggle e il confronto dei semi |
| `neural_descriptive_r1/`, `neural_external_validation/`, `kaggle_neural_postgate/`, `kaggle_neural_cluster0_r1/`, `neural_reader/`, `neural_adapter_r1/` | Letture descrittive, diagnostiche e prove collaterali |

## Stack, il modello preaddestrato

| File o cartella | Che cosa |
|---|---|
| [PROTOCOLLO_STACK.md](neural/PROTOCOLLO_STACK.md), [PROTOCOLLO_STACK_AB.md](neural/PROTOCOLLO_STACK_AB.md) | Pilot con prompt di cellule reali, varianti A e B |
| [RISULTATI_STACK_A.md](neural/RISULTATI_STACK_A.md), [STACK_A_POSTHOC.md](neural/STACK_A_POSTHOC.md), [RISULTATI_STACK_AB.md](neural/RISULTATI_STACK_AB.md) | A e B negativi; A perde il 32,6 % della componente specifica dei bersagli |
| [NN_PRESCREEN_AUDIT.md](neural/NN_PRESCREEN_AUDIT.md) | Il prescreen PDS non è un test dei sei membri |
| [AUDIT_BIOLOGICO.md](neural/AUDIT_BIOLOGICO.md), [AUDIT_PRETRAINED_ARC.md](neural/AUDIT_PRETRAINED_ARC.md) | Che cosa fanno davvero le reti precedenti e Stack |
| `neural/` (il resto), `kaggle_stack_inputs_r1/`, `kaggle_stack_variant_b_r1/` | Codice, ingressi, corse, riparazioni e i loro test |

## Dati e piattaforma

| File o cartella | Che cosa |
|---|---|
| `dati_r1/`, `cd4_r1/` | Le misure dell'audit dei dati |
| [PROTOCOLLO_PONTE.md](PROTOCOLLO_PONTE.md), `ponte_plan_r1/`, `ponte_plan_r2/` | Ponte predittivo K562 3′ → Flex: protocollo, non eseguito |
| `same_context_predictive_r1/` | Verifica di uno screening mirato già locale: protocollo; il manifest completo sta fuori dalla repo |
| `rules_2026/` | Lettura delle regole pubbliche della gara |

## Operazioni e apprendimento dagli errori

| File o cartella | Che cosa |
|---|---|
| [learning/README.md](learning/README.md) | Registro degli incidenti E-20260929-001…007, con `preflight.py` e `ledger.py`, usati da `docs/ERRORI.md` |
| [KAGGLE_REMOTO.md](KAGGLE_REMOTO.md), `kaggle_remote/`, `kaggle_lead_monitor/`, `kaggle_neural_monitor/` | Notebook Kaggle e monitor delle corse |
| [external_reviews/STATO.md](external_reviews/STATO.md) | Revisioni di Grok e Claude2 tramite l'hub |

## Come usare questa cartella

- **Non si modifica**: una nuova corsa va in una cartella nuova (`reports/CLAUDE.md`).
- **Codice riusabile:** solo `learning/preflight.py` e `learning/ledger.py`, che `docs/ERRORI.md`
  indica per i job nuovi. Gli script con suffisso `_r1`…`_r5` (`build_*`, `prepare_*`,
  `repair_*`, `resume_*`, `monitor_*`) sono tentativi operativi datati, non una libreria.
- **I numeri dei banchi sono indici locali**, non punteggi VCC ([CP-0050](../../../docs/checkpoints/0050-credibilita-score-e-riserva.md)):
  sul t28 l'indice diceva +0,0289, la gara ha dato +0,0046.
