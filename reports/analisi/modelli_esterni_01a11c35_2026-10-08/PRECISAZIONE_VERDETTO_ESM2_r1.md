# Precisazione del verdetto ESM2: fallback inconcludente

9 ottobre 2026. Correzione separata di `RISULTATI_CHIUSURA_ESM2_r1.md`,
che resta conservato. Fonti ricontrollate: PROTOCOLLO_v1 §8–9,
PROTOCOLLO_v2 §1 e §3 e codice originale del banco di VALIDAZIONE.

**T0+fallback ESM2 è INCONCLUDENTE.** Il confronto a sei membri (livello B)
non è stato eseguito per questo candidato. La discriminazione del fallback
meno T0 non mostra regressioni risolte nei due fold: K562 +0,000312
[−0,000244; +0,000936], iPSC +0,000177 [−0,000719; +0,001098]; macro
+0,000244 [−0,000278; +0,000796]. Non dimostrano un beneficio, ma neppure
giustificano l'interruzione del livello B per assenza di un guadagno positivo.

La frase precedente «non si promuove una versione che non migliora la misura
primaria congelata», usata per motivare la mancata esecuzione del livello B,
applicava una condizione più restrittiva di quella preregistrata. Era un errore
di lettura. La regola richiede assenza delle regressioni risolte specificate
in disc95 e i risultati del livello B; non richiede un miglioramento positivo
risolto di disc95. La mancata promozione resta corretta per il livello B
assente, ma non equivale a bocciatura del fallback.

**ESM2 nativo è un caso distinto:** su C-K562 perde −0,23928
[−0,28442; −0,19253] rispetto a T0. È una regressione risolta che richiede
diagnosi prima del passaggio al livello B secondo il segnale d'arresto.
Non si trasferisce questo esito al candidato che conserva T0 e riempie
soltanto le coppie mancanti. Neppure si estende a tutta la famiglia degli
embedding proteici. La priorità operativa data ad AMMI non è quel giudizio.

## Audit del supporto: che cosa manca davvero

`common_support.json` della corsa closure contiene `{}`. Nel driver originale
questo file è popolato per le sole `analysis_arms` dotate di `common_support`,
non per le `external_arms` ESM2. La sua vacuità non dimostra, da sola, un errore
della metrica o l'assenza di controlli degli hash: indica che **quel file non
misura la copertura effettiva del fallback**.

`bench_core.measure` definisce bersagli e `cols95` con i bracci originali del
manifest (T0, R1, T1, P4). I bracci esterni sono misurati sullo stesso supporto.
È corretto conservarlo per non spostare il confronto; implica però che il
numero totale di coppie riempite non misura quante siano entrate in disc95.
Non abbiamo ancora contato queste coppie né quelle escluse per gene,
bersaglio o validità della verità. Non si inferisce che il fallback sia
invisibile alla metrica, né che il piccolo delta descriva tutte le coppie nuove.

Il piano aggiuntivo usa i fit già esistenti: audit di supporto senza cambiare
`cols95`, poi T0 contro fallback su sei membri nei due fold congelati. Nessun
nuovo training, cambiamento di soglia/scorer o modifica del ramo J. Il piano
degli accessi e i file sono in `esm2_validation_access_plan_r1.json`;
eventuali nuovi trasferimenti privati restano soggetti al consenso specifico.
