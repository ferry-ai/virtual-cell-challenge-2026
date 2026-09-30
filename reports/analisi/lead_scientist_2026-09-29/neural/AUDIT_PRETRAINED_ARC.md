# Modelli Arc pretrained: fattibilità per il pannello di oggi

29 settembre 2026. **Audit tecnico misurato, proposta non eseguita.** Nessun peso
neurale scaricato, nessun job remoto, nessuna inferenza. Consultati file pubblici e
piccoli metadati; la mappa one-hot da 16,7 MB è stata analizzata staticamente in
memoria con `pickletools`, senza eseguire pickle o importare torch.

## State: il checkpoint genetico verificato non copre nessuno dei 300 bersagli

**Misurato:** `arcinstitute/ST-HVG-Replogle/zeroshot/hepg2/pert_onehot_map.pt`
contiene 2.023 nomi genetici riconosciuti più il controllo. L'intersezione con il
pannello è **0/300**. SHA256 della mappa:
`f5621cab243a5135014af3867f63f8bf75cff19aee06d0f29a1bdecd2dbf47d0`.
La prova riproducibile e i nomi sono in `metadata_r3.json`; le precedenti r1/r2 non
decodificavano le chiavi numpy UTF-32 e sono estrazioni incomplete.

Il [codice ufficiale di inferenza](https://github.com/ArcInstitute/state/blob/main/src/state/_cli/_tx/_infer.py)
assegna alle perturbazioni fuori vocabolario il vettore di controllo. Non è quindi
possibile ottenere da questo checkpoint risposte specifiche ai nostri 300 bersagli
mediante la sola inferenza. Rinominare i target o aggiungere vettori casuali non
fornisce un significato biologico a pesi mai addestrati.

| Artefatto pubblico | Misura verificata | Conseguenza |
|---|---|---|
| [ST-HVG-Replogle](https://huggingface.co/arcinstitute/ST-HVG-Replogle/tree/main/zeroshot/hepg2) | best.ckpt 471.699.039 byte; input/output 2.000 HVG; pert_dim 2.024 | Oltre al vocabolario, output parziale rispetto all'asse VCC |
| [st-x-replogle-full](https://huggingface.co/arcinstitute/st-x-replogle-full/tree/main/hepg2_0.99) | best.ckpt 664.162.239 byte; one-hot, output_space all, set 64 cellule | La configurazione hepg2_0.99 è downsample 0,99, non una dichiarazione di holdout al 99% |
| [Split Replogle](https://github.com/ArcInstitute/state/blob/main/state_preprint_toml_files/replogle_tomls/hepg2.toml) | il file `hepg2.toml` ha split few-shot HepG2 e nessuno zeroshot | Il checkpoint corrispondente non può certificare un test su famiglia HepG2 mai vista |

Il repository ST-HVG ha anche checkpoint `zeroshot/hepg2`, distinti da quelli
few-shot. L'audit della mappa riguarda precisamente quello zeroshot. Non è stata
verificata l'uguaglianza delle mappe di tutti gli altri checkpoint: nessuna
generalizzazione automatica a tutti i modelli pubblici Arc.

**Decisione proposta:** non scaricare ST-HVG-Replogle per una candidatura diretta
stanotte. Può essere un backbone da adattare o una fonte di embedding, ma necessita
training e validazione nuovi. I grandi numeri aggregati di cellule dei diversi
modelli State non dimostrano l'esistenza di un unico predittore genetico universale.
Il [repository State](https://github.com/ArcInstitute/state) distingue embedding SE,
transizione ST, training genetico e inferenza del modello farmacologico Tahoe.

## Stack: tecnicamente pertinente al regime C, non ancora un candidato pronto

La [model card Stack-Large-Aligned](https://huggingface.co/arcinstitute/Stack-Large-Aligned)
riporta 217 milioni di parametri, pretraining scBaseCount su circa 150 milioni di
cellule e allineamento CellxGene/Parse. Il checkpoint pubblico è 2.613.863.242 byte;
il file di geni è 925.039 byte. Non trovato alcun checkpoint State/Stack nel data
root locale cercando `.ckpt`, `.safetensors`, `.pt`, `.pth`, `.torch`.

Il [tutorial ufficiale](https://github.com/ArcInstitute/stack/blob/main/notebooks/tutorial-predict.ipynb)
usa cellule perturbate di un tipo come prompt e controlli di un altro tipo come
destinazione. Produce anche un controllo sintetico per correggere gli artefatti
di trasferimento. L'esempio è farmacologico, non una prova di prestazione CRISPRi.
Il vocabolario genetico non è un elenco chiuso di target: il prompt porta la risposta
osservata. Questo rende plausibile usare le nostre sorgenti nel regime C.

Il [codice del modello](https://github.com/ArcInstitute/stack/blob/main/src/stack/models/core/base.py)
trasforma internamente gli input con log1p e usa un decoder negative-binomial con
composizione softmax. Il [percorso di generazione](https://github.com/ArcInstitute/stack/blob/main/src/stack/models/core/inference.py)
restituisce campioni di conteggi. Non va passato un input già log-normalizzato senza
verificarne il contratto. La [CLI](https://github.com/ArcInstitute/stack/blob/main/src/stack/cli/generation.py)
allinea l'asse, imputa a zero i geni assenti e permette batch ridotti, seed fissato e
generazione iterativa. Default batch 32, cinque passi: non è un requisito minimo.

**Proposta concreta per un eventuale braccio separato:**

1. Pilot preregistrato su un piccolo insieme di target C già coperti da una sorgente,
   con sorgente perturbata, suo controllo e solo controlli della destinazione.
2. Eseguire due prompt appaiati: perturbato e controllo della stessa sorgente.
   Estrarre la differenza fra le previsioni e ricomporla sul basale destinatario;
   conservare mask e copertura. Lasciare i geni non coperti alla baseline.
3. Confrontare col trasferimento semplice sullo stesso supporto e verificare prima
   direzione, norma, diversità cellulare e drift al nullo; poi scorer completo.
   Non usare esiti dei target destinatari come prompt o per aggiustare la scala.

Questo è più vicino a un trasferimento condizionato su uno stato cellulare
preaddestrato che a una nuova rete allenata da zero su dodici contesti. Non è però
un sostituto immediato: serve preparare veri prompt cellulari, verificare lo spazio
dei geni e l'assenza di contaminazione del test, misurare VRAM e stabilità sul device
disponibile. Il [repository](https://github.com/ArcInstitute/stack) dichiara test su
H100 80 GB; non fornisce un minimo VRAM garantito. Nessun benchmark locale è stato
eseguito e non viene promessa compatibilità con T4.

## Licenze e conclusione operativa

La [licenza State](https://github.com/ArcInstitute/state/blob/main/MODEL_LICENSE.md)
e quella di [Stack](https://github.com/ArcInstitute/stack/blob/main/MODEL_LICENSE.md)
sono non-commerciali e coprono pesi e output. La loro definizione di scopo
non-commerciale menziona la compensazione finanziaria. Questo audit non stabilisce
che la partecipazione al VCC sia vietata: il sito ha una FAQ specifica su State,
ma la risposta corrente non era disponibile nel contenuto testuale letto. Le
regole del 2025 trovate in ricerca non sono una prova delle regole 2026. Prima di
usare un modello nella candidatura va verificata l'autorizzazione pertinente,
senza trasformare un'incertezza in un divieto inventato.

**Raccomandazione:** procedere con il nuovo modello source-attention sui dati già
pronti. State verificato è bloccato dal vocabolario per il pannello; Stack è una
linea sperimentale concreta, ma richiede un adapter e una prova prima di essere
competitivo. Nessuna architettura viene scartata in base al solo numero di parametri.
