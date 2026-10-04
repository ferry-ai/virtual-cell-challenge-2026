# Vincitori 2025: implicazioni verificabili per il prossimo confronto

4 ottobre 2026, Codex. Fonti primarie riaperte in questa sessione; ricerca mirata di nuove implementazioni senza trovare una replica completa verificabile dei primi tre. Questo è un limite della ricerca, non prova di assenza. Nessun dataset o peso scaricato.

## Evidenza esterna

Secondo il [resoconto ufficiale Arc](https://arcinstitute.org/news/virtual-cell-challenge-2025-wrap-up), BioMap combinava rete, statistiche esplicite e training pseudobulk; X usava controlli aggregati, ESM2, indicatore UMI e apprendimento residuo; TransPert aggregava riassunti di perturbazione e risultati Wilcoxon, con calibrazione. Altos ricevette il premio Generalist con un generatore flow. La classifica principale 2025 premiava compromessi fra metriche e non stabilisce quale metodo sia migliore sui sei membri 2026. Queste descrizioni non specificano una correzione del nostro transfer multi-sorgente né certificano il trasferimento a contesti mai visti perturbati.

Il [codice pubblico PRiMeFlow](https://github.com/altoslabs/primeflow) espone inferenza condizionata su covariate di training, parametri di guidance e una ricetta di fine-tuning che include perturbazioni H1 ammesse. È una base concreta da studiare, non una prova pronta di trasferimento dai soli controlli a una nuova linea. Il [paper v2](https://arxiv.org/html/2604.13986v2) documenta il modello generativo e l'esperimento VCC; la ricetta di gara va distinta da un'architettura valida in ogni regime.

## Inferenze per il nostro progetto, da provare

1. **Correggere il riferimento a X.** “Ispirato a X” non significa replica: il nostro modello ha loss cellulare e ancora multi-sorgente. Il confronto utile riguarda cosa apprendiamo dagli aggregati e cosa aggiungono le cellule.
2. **Pseudobulk come segnale e supervisione.** Calcolare stime precise sull'archivio ammesso e conservare strati biologici/tecnici, incertezza e supporti. Affiancare una loss sulle medie alla loss cellulare può insegnare il residuo specifico con meno rumore: è un'ipotesi, non un vantaggio già dimostrato.
3. **Affidabilità statistica.** Provare riassunti di riproducibilità fra guide/repliche e incertezza, evitando che “spesso DEG” sia solo profondità o numerosità. Stimarli entro il fold, confrontandoli con il solo livello di espressione. Non eliminare sorgenti perché discordano biologicamente.
4. **ESM2 con confronto corretto.** Confrontarlo con i descrittori già presenti, controllando mapping/isoforme, geni mancanti, dimensione e provenienza; non “embedding contro niente”. Priorità al regime J, dove l'identità del target non basta.
5. **Distribuzioni solo quando motivate.** Confrontare prima medie, varianze, zeri e sottostati su dati reali e generati. Se domina l'errore dell'effetto, un flow più grande non risolve automaticamente il problema. Un ingresso categorico della linea non sostituisce un descrittore ricavabile dai nuovi controlli.

## Revisione delle conclusioni precedenti

I fallimenti S-007 restano validi per quei modelli e quei confronti; non dimostrano che gli aggregati siano inutili. Riutilizzarli come supervisione affidabile o stratificata non è lo stesso esperimento della sola media basale. Il ruolo delle cellule va misurato contro un modello aggregato riaddestrato e contro controlli scambiati, con basale e generatore fissi.

Il passo proposto è una serie di ablation nel [piano](PIANO_TRAINING.md), non l'adozione di un vincitore. Per una riproduzione più profonda restano da verificare codice/config/versioni delle singole soluzioni, licenze, costi e trasferibilità C/J; in assenza di specifiche complete usare “adattamento”, non “replica”.
