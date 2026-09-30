# t28: invio diretto dal contenitore su Drive

**Implementato e verificato con test piccoli; nessun invio avviato da questo audit.** Il 29 settembre sono state lette le otto ricevute JSON reali del job079, per circa 251 KB, e la dimensione del contenitore. Il contratto passa: `completion=complete`, generazione SHA256 `123ce93f4d8d21c107215c96f726a6b7121545c1329948f431234eabce80f40e`, 360000 cellule × 18533 geni, 2085425466 elementi CSR, controlli ufficiali passati e payload verificato identico all'input.

Il contenitore finale dichiarato è:

```
G:\Il mio Drive\vcc2026\runs\lead_candidate_t28_2026-09-29_r2\prediction.vcc
4161126400 byte
SHA256 atteso: 0d70ba92d68817b46383b11c53d513a41c85329230b9ff5524ac51f7bd110b32
```

**Lo SHA completo del file visto da Windows deve ancora essere calcolato.** Le ricevute remote e `stat()` non lo sostituiscono. `direct_t28_submission.py` lo calcola prima di invocare il CLI, in blocchi da 8 MiB, controllando dimensione, stabilità del file e almeno 512 MiB liberi su C: durante tutta la lettura. Lo script salva le piccole ricevute in una cartella nuova e non copia né decomprime il `.vcc`. Il precedente `retrieve_t28.py` resta invariato e non è adatto allo spazio attuale: copierebbe altri 4,16 GB su C: oltre all'eventuale cache Drive.

Il CLI installato e letto è `vcc-cli==0.2.0`, build release, endpoint ufficiale `https://virtualcellchallenge.org`. Prove nel codice installato sotto `C:/Users/ferra/vcc2026-data/.venv/Lib/site-packages/vcc/`:

- `submit.py:162–171`: un `.vcc` validato viene restituito sul medesimo percorso; il percorso `.h5ad` con prep implicito è distinto e qui non viene usato.
- `vccfile.py:36`: verifica il membro TAR e non decomprime il payload; legge soltanto il piccolo `meta.json` per `nnz`.
- `upload.py:55`: MD5 locale con blocchi da 1 MiB. `upload.py:151–177`: apertura diretta del file, offset GCS, `seek` e blocchi di upload da 5 MiB. Nessuna copia completa temporanea.
- `submit.py:469–480`: conserva lo stesso `local_path` nello stato di ripresa; `submit.py:390–424` usa quel percorso per `--resume`. Il nostro runner controlla anche che l'entry da riprendere punti esattamente al contenitore appena verificato.

Il runner congela gli SHA dei tre moduli CLI letti, della registrazione t28, dei testi scelti e dell'autorizzazione successiva del proprietario. La vecchia registrazione `submission_authorized:false` viene preservata come documento storico; l'autorizzazione corrente è `reports/invii/trial_2026-09-29/autorizzazione_lead_2026-09-29.md`.

## Avvio riservato al coordinatore

Comando concreto, **da eseguire soltanto dopo review del codice**:

```powershell
& reports/analisi/lead_scientist_2026-09-29/candidate_generation_remote/recovery_r2/launch_direct_t28_submission.ps1 `
  -Out 'C:/Users/ferra/OneDrive/Desktop/vcc2026/reports/invii/trial_2026-09-29/t28_direct_attempt_r1' `
  -Execute
```

Senza `-Execute` stampa soltanto il piano: questa modalità è stata provata e ha riportato `executed:false`. Con il flag crea un **processo Windows separato e nascosto**, senza dipendere dal lifetime del tool dell'agente. Il worker valida e fa lo SHA, poi avvia `python -m vcc --json submit` con i testi t28 già registrati. Non forza la quota, non cambia endpoint, non cancella entry o lucchetti. Il worker mantiene attiva la richiesta Windows di evitare la sospensione durante il CLI e la rilascia alla fine.

Le evidenze sono `t28_direct_attempt_r1.worker_started.json`, `.worker_stdout.log` e `.worker_stderr.log`; dentro la cartella nuova, `validation.json`, copie delle sole ricevute piccole, `submission_started.json`, `submit_raw.json`, `submit_stderr.txt` e `submission_exit.json`. L'output CLI è preservato senza riscrittura. Il ritorno del submit non dimostra che lo score sia pubblicato: il coordinatore deve chiedere e salvare `vcc --json status <entry_id>` prima di un altro invio.

Un tentativo interrotto va ripreso con una cartella nuova e `-ResumeEntry <entry_id>`, conservando il file G: al percorso originale. Il runner rifà lo SHA completo; il CLI interroga l'offset già ricevuto. Nessuna ripresa automatica cieca, né eliminazione di un lock: prima si verifica che il processo precedente sia finito.

## Spazio e limiti

L'invio diretto evita la seconda copia su C:, **non la cache di Google Drive**. La lettura SHA può idratare circa 4,16 GB; con i 5,45 GB liberi comunicati dal coordinatore il margine aritmetico è circa 1,29 GB, prima di altri processi. La politica di cache/evizione Drive e il suo percorso non sono stati misurati da questo audit: il monitor su C: è una guardia operativa, non una garanzia della dimensione finale della cache. Lo stesso file viene letto almeno tre volte (SHA, MD5 e upload); la cache può rendere le letture successive locali, ma non viene assunto come fatto.

Se la riserva scende sotto 512 MiB durante SHA, il runner fallisce prima di creare una submission. Un fallimento di rete durante upload lascia il meccanismo ufficiale di ripresa. Non si elimina alcun dato, vecchio artefatto o tentativo fallito.

Test `test_direct_t28_submission.py`: **4 PASS**. Coprono ricevute/payload falsi, parametri errati, dimensione/SHA/spazio errati, validazione su un TAR sintetico senza copie o chiamate di rete e rifiuto di una ripresa che punti a un file diverso. Il contratto delle ricevute reali079 è stato eseguito separatamente e passa; il test sintetico non sostituisce la verifica scientifica dello stage48.

SHA del codice consegnato:

```
direct_t28_submission.py             adccdd054987dcfeb5e425982d68bb9a149a6d96ce6f3001620583df3ea55ec1
launch_direct_t28_submission.ps1     35dea3efd14049877ee5afb19386888c724a2256836887659e774e80fc3296bd
test_direct_t28_submission.py        914bfd3cf63259a7dc15b5fe5f9ca2a649082fa5427ce6aeb5c5dc589f40da35
```
