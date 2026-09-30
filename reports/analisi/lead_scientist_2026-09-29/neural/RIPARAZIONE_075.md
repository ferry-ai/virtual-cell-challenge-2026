# Preparazione conferma Stack: effetti mancanti nel job 075

29 settembre 2026. Diagnosi dal log completo
`G:/Il mio Drive/vcc2026/runs/jobs/075_lead_stack_confirmation_prepare_r1.log`
e dal `plan.json` in `runs/lead_stack_confirmation_prompts_2026-09-29_r1`.
Il piano ha selezionato correttamente i dodici target e 1.421 righe K562;
la preparazione si è fermata con `Frozen transfer lacks a confirmation target`.
Il controllo precede creazione del bundle e lettura delle righe di conteggi
perturbati. Nessuno score è stato prodotto dal job.

Il launcher passa `prepared_effects.npz` del banco generatore r3, che conserva
soltanto i 48 development e 96 confirmation. I dodici della riserva Stack sono
per definizione fuori da entrambi. Si tratta di copertura del derivato: non
dimostra che gli effetti manchino nel file sorgente congelato `t19like.npz`.

La correzione prepara un nuovo NPZ dalla stessa sorgente t19like, senza stimare,
ricentrare o cambiare i valori. Ricostruisce soltanto la mask observed con la
funzione originale `generator_bench.source_mask`, stage98 e dipendenze congelate,
poi applica la mappatura originale all'asse HepG2. Richiede parità **esatta** di
valori e mask su tutti i 144 target già preparati e sui dodici del pilot, prima
di salvare i dodici nuovi. Lo zero osservato rimane osservato. Ogni NPZ si apre
con `allow_pickle=False`; i nomi sono esplicitamente stringhe NumPy.

`stack_confirmation_effects.py` controlla SHA256 di t19like, bulk K562, manifest
r3, prepared_effects, helper e dipendenze, e rifiuta duplicati o target mancanti.
Non legge outcome HepG2. `stack_confirmation_pack.py` originale resta invariato:
il nuovo launcher cambia soltanto il suo input effects e i percorsi di output.
Il tentativo 075 e l'archivio 344e204b… rimangono conservati.

`build_stack_confirmation_repair.py` produce un nuovo archivio e un launcher
proposto `080_lead_stack_confirmation_prepare_r2.sh`: **nessuna coda o copia
remota è eseguita dal builder**. L'archivio preserva byte per byte tutti i file
del setup r2 e aggiunge il codice per recuperare gli effetti. Output proposto:
`runs/lead_stack_confirmation_prompts_2026-09-29_r2`.

La preparazione anticipata rimane indipendente dalla scelta A/B. Questo bundle
lega per provenienza gli adapter A congelati, ma **non autorizza inferenza o
scoring**. L'esecuzione attende il manifest di selezione completo del protocollo
AB; se viene selezionato B servono il suo protocollo distinto e una nuova
provenienza degli adapter, senza cambiare cellule, effetti o target preparati.

Test locali sintetici: mappatura su assi permutati, gene non misurato, zero
osservato, parità esatta, round-trip senza pickle, rifiuto di target mancanti e
duplicati. La prima esecuzione del test ha confrontato erroneamente valori
float32 con letterali float64; il fixture ora usa il dtype della sorgente.
Questo difetto del test non ha cambiato codice scientifico o dati reali.

Le misure reali di parità e l'estrazione delle 1.421 righe restano da eseguire
nel job remoto revisionato; l'esistenza del codice non è un esito di preparazione.
