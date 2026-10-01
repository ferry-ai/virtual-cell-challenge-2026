# Scostamenti dal protocollo del terzo training, decisi prima di ogni suo numero

1 ottobre 2026, 07:24 CEST (ora letta con `date`), Claude Code (sessione `07ebf08b`). Il [protocollo](PROTOCOLLO.md)
resta com'è. Quando questi scostamenti sono scritti, del terzo training esiste solo il pre-passo r6. Il secondo
training è ancora in corso, e nessun suo numero di valutazione è noto.

1. **Tian 2019 fuori, pre-passo r7 al posto di r6.** Il pre-passo
   [r6](esito/prepass_r6_scartato/manifest.json) mostra che i due file di Tian 2019 di scPerturb (iPSC e neuroni al
   giorno 7) non sono filtrati. I controlli hanno una mediana di 9 e 11 conteggi sui geni del modello, contro migliaia
   in ogni altra chiave (`qc.json`, `control_quantiles`). Le soglie relative, ricavate dai controlli, degenerano a 1.
   Il pre-passo scarta 93.380 e 62.759 cellule con meno di 10 conteggi, ma ammette le altre, per lo più gocce quasi
   vuote. La misura remota lo conferma: `ncounts` va da 0 a 105.247 (`p1_r4/remote/scp_TianKampmann2019_iPSC.json`),
   mentre Tian 2021 parte da 506. Con il peso uguale per studio, due studi su circa quindici sarebbero gocce vuote.
   - **Cosa cambia:** il pre-passo `rlab-prepass-r7` legge `rlab-tian-norman` con
     `--glob "rlab-tian-norman=norman2019__*.h5ad|tian2021_*.h5ad"`. Entrano Norman 2019 e Tian 2021, Tian 2019 resta
     fuori finché non esiste un filtro delle cellule dichiarato, per esempio quello degli autori.
   - **Codice:** il pattern con alternative separate da `|` in `kaggle_train.py`. Il dataset del codice non cambia,
     perché quel pattern sta nel `run.py` del kernel.
   - **Il resto resta com'è:** argomenti del pre-passo, regole dei dati, bracci, budget e regola di lettura sono quelli
     del protocollo. r6 resta come diagnosi e non alimenta nessun training.
2. **La terza ondata resta fuori**, come i dataset non pubblicati al lancio (protocollo §2). I job 127-129 sono in
   corso su Colab.
