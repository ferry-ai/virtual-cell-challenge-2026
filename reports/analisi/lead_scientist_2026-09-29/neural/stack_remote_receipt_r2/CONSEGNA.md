# Payload pronto per la review, 29 settembre 2026

**Implementato, non eseguito:** inferenza Stack su 12 target del pilot congelato,
nessuno scoring o invio VCC. Il launcher della coda è `071_lead_stack_infer_r1.sh`.
Il root gestisce copia, verifica e avvio; nessun job è stato avviato dal builder.

Destinazione dei due file `colab_stack_infer_r1.py` e `review_manifest.json`:
`/content/drive/MyDrive/vcc2026/runs/lead_stack_infer_setup_2026-09-29_r1/`.
Input: `runs/lead_stack_2026-09-29_r2/bundle.tar.gz` sullo stesso Drive.
Output nuovo: `runs/lead_stack_infer_2026-09-29_r1/`.
Scratch nuovo: `/content/lead_stack_scratch_r1`.

Il freeze locale di questa variante usa la ricevuta della preparazione. Il runner
verifica tutti i byte del bundle e del codice prima di scaricare i pesi. Il primo
builder integrale, conservato in `../stack_remote_r1/`, ha nel frattempo terminato
con lo stesso SHA del bundle; quella versione non contiene la successiva guardia
RAM al caricamento e non è il payload da eseguire.

**Misurato nel preflight 068:** CPython gestito 3.11.13; risoluzione dei requisiti
riuscita, non ancora prova di importazione. Il runner conserva i pin originali e
prova import Stack/scvi prima dei pesi. RAM disponibile nel preflight circa
11,13 GiB, non una garanzia sul valore al momento dell'inferenza. La stima prudente
del processo è circa 4,5–5 GiB CPU; non è una misura. Guardie: disco iniziale
16 GiB; spazio per i due pesi più 2 GiB prima del download; RAM disponibile
almeno 6 GiB e disco residuo 2 GiB immediatamente prima del loader. Le misure sono
salvate prima dell'installazione, prima dei pesi e prima del caricamento.

Il modello da 217 milioni di parametri non è stato ancora caricato qui. Il pilot
deve misurare tempo e memoria GPU effettivi; nessuna dichiarazione di holdout
HepG2 rispetto al pretraining.
