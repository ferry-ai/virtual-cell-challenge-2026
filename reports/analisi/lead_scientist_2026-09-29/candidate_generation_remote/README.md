# Generazione e packaging remoto: preflight, non esecuzione

**Implementato e preparato per revisione.** Non è stato accodato né eseguito un job.
Il launcher richiede la conferma completata e la previsione registrata; non sceglie il
numero del trial e non contiene comandi di invio VCC.

`input_manifest_r1.json` misura dimensioni, forme e SHA256 completi. I tre controlli
Drive sono identici alle copie locali dopo lettura integrale, 18.400 × 18.533 ciascuno.
Anche `gene_names.csv` e `pert_counts.csv` sono identici. L'archivio r3, già su Drive in
`runs/lead_generator_setup_2026-09-29_r3/code_snapshot.tar.gz`, ha SHA256
`f7324778e5d7225552734e2c7303353f46dee6c01e9d455703adce3b9b105860`.

**Mancanza misurata:** `data/processed/effects_t25_2026-09-27` non era presente su Drive.
La ricerca nelle directory pertinenti trova soltanto gli effetti t08 storici in `runs`;
non vengono usati come sostituti. Il percorso t25 nel manifest è una destinazione
proposta; l'esecuzione verifica presenza e hash, quindi fallisce finché mancano i file.

## Allowlist del trasferimento proposto

Gli unici nuovi dati da copiare dal data root locale al medesimo percorso relativo
su Drive sono:

| File in `processed/effects_t25_2026-09-27/` | Byte |
|---|---:|
| `effects_A.npz` | 17.629.146 |
| `effects_B.npz` | 17.629.146 |
| `effects_C.npz` | 17.629.146 |
| `manifest.json` | 5.162 |

Totale 52.892.600 byte. Sono gli effetti t25 originali, 300 × 18.533 con maschera di
osservazione; ogni hash è nel manifest. Non è stato effettuato questo trasferimento.
I piccoli file aggiuntivi necessari al job sono `generate_candidate.py`, il manifest
degli input, una copia della `confirmation/selection.json` completata, la previsione
registrata e il template `.sh` concretizzato. Nessun token o file di autenticazione.

## Esecuzione che sarà revisionata

`generate_candidate.py` senza `--execute` fa soltanto preflight in lettura. La modalità
di esecuzione richiede hash espliciti di manifest, conferma e preregistrazione. Accetta
`phi_scale=0.5` oppure `1` soltanto se la conferma contiene esattamente quel candidato
pooled, ampiezza 1,5, tre semi positivi, guadagno almeno 0,005 e limite inferiore positivo.
Il file deve dichiarare anche `passes_confirmation=true` e truth `full`.

Richiede `vcc-cli==0.2.0` già installata. Registra Python, NumPy, SciPy, pandas, h5py,
AnnData, PyYAML e zstandard. L'eventuale installazione preparatoria, da revisionare
insieme al job, è `python -m pip install vcc-cli==0.2.0`; il launcher non installa nulla.

Estrae il solo archivio congelato r3 in una nuova directory `/content`, rifiutando
percorsi esterni e link. Copia gli input nel disco locale di Colab, verifica di nuovo
gli hash e invoca gli stadi 45 e 48 dello snapshot. Parametri di generazione: tre
contesti A/B/C, tutti i 300 target, 400 cellule, seme 20260912, effetti t25 originali
moltiplicati per 1,5, dispersione per gene alla scala selezionata. Restano attivi i
controlli di memoria/disco degli stadi; nessun controllo di quota sostituisce la
convalida dei dati. Non si usa `--skip-verify`.

Il packaging rilegge il contenitore con il validatore ufficiale e confronta il payload
array per array con la predizione. Soltanto dopo il successo copia il `.vcc` su Drive
con suffisso `.partial`, ne ricalcola SHA256 completo e lo rinomina finale. Output e
scratch devono essere nuovi; nessun file viene sovrascritto. Le diagnostiche e i log
sono preservati anche in caso di errore, il grande `.h5ad` rimane su `/content`.

`job_template.sh` non è eseguibile senza valori concreti, hash, trial e flag di
approvazione della lead. Nessun upload di submission segue il packaging.
