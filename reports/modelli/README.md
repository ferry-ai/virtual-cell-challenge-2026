# modelli — protocolli, training e risultati

Il programma operativo è [R-LEAD](../../docs/piani/strategia-scientifica.md); gli input
cellulari sono indicizzati da [R-LAB](../../docs/piani/piano-giorno-2026-09-30.md).
Il t29 boccia il candidato r2 `desc` con generatore t22 (CP-0055), non tutte le reti.
Esito tecnico, segnale esplorativo e promozione scientifica sono distinti.

Prima di riusare cellnet leggere [NOTA_TRAINING](../analisi/lead_audit_2026-10-01/NOTA_TRAINING.md)
e [AGGIORNAMENTO_R3](../analisi/lead_audit_2026-10-01/AGGIORNAMENTO_R3.md).
Le comparazioni r2/r3 hanno split differenti; il collasso identity r3 non spiega da solo t29.
K562 già nel training non vale come contesto neurale nuovo; H1 train/val è nel corpus.

Le prove E1/E2, scambio di contesto e curve dei primi 50–100 passi appartengono ai
modelli del 27–28/09 sotto indicizzati. Non descrivono indistintamente le reti cellulari.
La rete sulle sorgenti e Stack hanno [esiti propri](../analisi/lead_scientist_2026-09-29/README.md#rete-sulle-sorgenti),
CP-0049 e CP-0051. [Indice generale](../README.md).

| Data | Cartella | Nocciolo | Vale? | Peso oggi |
|---|---|---|---|---|
| 03/10 | [rete_cellulare_2026-10-03/](rete_cellulare_2026-10-03/) | Rete cellulare v2: le correzioni dell'audit dell'1/10 con i test, e il protocollo del pilot su H1, HepG2 e RPE1 escluse intere (stato contro media dei controlli, rete contro transfer, generico) | codice di ricerca e protocollo; risultati da aggiungere | ★★ |
| 02/10 | [risposta_contesto_2026-10-02/](risposta_contesto_2026-10-02/) | Codice e test di R-LEAD P0–P3: universo HepG2, cubo, split stabili, bracci semplici con gemelli senza contesto, scambi e nulli permutati; misure in `reports/analisi/generalizzazione_contesti_2026-10-02/` | codice di ricerca con controllo sintetico; nessuna adozione | ★★ |
| 01/10 | [cellnet_terza_ondata_2026-10-01/](cellnet_terza_ondata_2026-10-01/) | Quarto training: terza ondata più floor su pi; protocollo tecnico conservato, non prossimo job automatico | protocollo; nessun esito registrato, non soddisfa da solo il banco richiesto dopo t29 | ★ |
| 01/10 | [cellnet_completo_2026-10-01/](cellnet_completo_2026-10-01/) | R3: seconda ondata CRISPRi/a/KO; lettura in ESITO.md e diagnosi del gate identity nell'audit del 1/10 | misure tecniche/esplorative; nessuna promozione; split diversi da r2 | ★★ |
| 01/10 | [cellnet_esteso_2026-10-01/](cellnet_esteso_2026-10-01/) | R2: corpus esteso, ESITO.md; braccio desc usato nel t29 ufficiale, esito negativo CP-0055 | training misurato; candidato non promosso, cause da isolare | ★★ |
| 01/10 | [cellnet_tecnico_2026-10-01/](cellnet_tecnico_2026-10-01/) | R1: primo training reale; protocollo, lanci ed ESITO.md, con incidente E-20261001-001 | misure tecniche; parte A non interamente passata, non promozione | ★★ |
| 30/09 | [risposta_biologica_2026-09-30/](risposta_biologica_2026-09-30/) | Codice cellnet, descrittori, export e registri di holdout usati nei training r1–r3; H1 test riservata, train/val ammesse nel fit | codice ed evidenza originali; diagnosi del 1/10 da leggere prima di riusare, correggere copie nuove | ★★ |
| 28/09 | [covariazione_2026-09-28/](covariazione_2026-09-28/) | Azione 6 di R-REV, la misura decisiva per la rete relazionale: la covariazione fra geni è più conservata fra linee dell'effetto del singolo bersaglio, e serve a prevedere una linea nuova? Protocollo e regola fissati alle 19:56, prima di calcolare. **Esito: inconclusivo per W1; «uso» no**: la via delle relazioni non prevede la risposta a un knockdown, nemmeno nella stessa linea, e sommata al trasferimento lo peggiora (CP-0043) | sì, esito negativo per la base della rete relazionale | ★★★ |
| 28/09 | [rete_relazionale_2026-09-28/](rete_relazionale_2026-09-28/) | La rete relazionale: carte dei geni da tutti i knockdown, vicini per carta, guadagni di modulo dai controlli, sopra il trasferimento calibrato; poche centinaia di parametri contro i 450.402 di r1. Disegno e regola della prima tornata (19:58), prima del codice; codice e autoverifica (12 su 12). **Non parte**: la misura decisiva non lo consente | proposta chiusa senza corsa | ★ |
| 28/09 | [rete_r1_lettura_2026-09-28/](rete_r1_lettura_2026-09-28/) | La regola di r1 letta sulle previsioni mediate dei tre semi (`leggi_r1.py`): uso del contesto ed E2 non passano; la rete **perde** contro il trasferimento `excl` su K562, HCT116 e HEK293T; passa solo J (+0,0015 K562, +0,0010 HCT116 contro il ripiego) | sì; proxy, non scorer vero (CP-0041) | ★★ |
| 28/09 | [encoder_contesto_2026-09-28/](encoder_contesto_2026-09-28/) | Encoder dei profili basali innestato nella rete; autoverifica 17 su 17. Prima tornata, parte Orion: nessuna condizione passa, guadagni di un millesimo, con l'embedding di un'altra linea la rete va meglio; parte K562/CD4 letta il 28/09 pomeriggio: **nessuna condizione passa** su tre verità E1 (su CD4 ogni condizione sta sotto −0,002 contro `none`) | sì, esito negativo; seme 0 solo | ★★ |
| 28/09 | [rete_contesti_r2_2026-09-28/](rete_contesti_r2_2026-09-28/) | Dataset r2 con 12 contesti CRISPRi (in più K562 essential, VIPerturb-seq, RPE1, due schermi HIPSCI) e la regola della tornata r2 fissata prima; varianti descrittive di r1: il minimo sulla famiglia tenuta fuori è entro i primi 100 passi Esito, seme 0: l'encoder su r2 crolla (`ours` − `none` −0,66 su HCT116); la curva non cambia; la lettura A (r2 contro r1 sugli stessi bersagli) **passa, provvisoria**: +0,0036 su K562, +0,0018 su HCT116, −0,0015 su CD4 a riposo | sì; un seme; A misura «il dataset r2», non i soli contesti | ★★ |
| 28/09 | [tahoe_bracci_2026-09-28/](tahoe_bracci_2026-09-28/) | I farmaci di Tahoe-100M come perturbazioni in 48 linee: T1 ridotto non passa. I vicini giusti battono quelli sbagliati (+0,06), ma copiarli perde contro la media di tutte le linee (−0,14) | sì; farmaci, non knockdown; effetto di piastra non separabile | ★★ |
| 27/09 | [rete_contesti_2026-09-27/](rete_contesti_2026-09-27/) | La rete su molti contesti (disegno di claude2, autoverifica 14 su 14): la corsa di produzione si ferma al passo 250; la perdita sulla famiglia tenuta fuori sale appena la rete impara oltre il trasferimento. I tre semi di r1 sono finiti; la regola è letta in `rete_r1_lettura_2026-09-28/` (riga qui sopra): passa solo J | sì | ★★ |
| 27/09 | [modello_contesto_2026-09-27/](modello_contesto_2026-09-27/) | Modello a cancelli a quattro parametri, con la letteratura verificata da grok. r1: E1 non passa, E2 parziale (coppia Orion sì, r ≈ 0,002; CD4 no); dove batte il cieco non batte lo scambio | sì, esito negativo per l'adozione | ★★ |
