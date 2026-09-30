# Stack: esecuzione del pilot congelato

29 settembre 2026. **Implementato e testato con dati sintetici; pesi non ancora
eseguiti al momento di questa nota.** Protocollo e adapter restano quelli congelati
in `stack_setup_r1/code_snapshot.tar.gz`, SHA256
`a2e407961e2aefacd634f17541440bfd1e7035a036658f63cb655a33a9926698`.

Il job 063 ha fallito il confronto dei byte del piano a causa dei fine-riga:
1.110 byte Windows contro 1.069 Linux, stessi campi. La prova è in
`prepare_failure_r1/`. `colab_stack_prepare_r2.sh`, accodato dal coordinatore come
064, confronta tutti i campi JSON e scrive in `runs/lead_stack_2026-09-29_r2`.
Nessuna opzione scientifica è cambiata. La preparazione non scarica pesi.

## Congelamento del runtime dopo la preparazione

Eseguire il builder soltanto quando `bundle.tar.gz`, `bundle/bundle.json` e
`plan.json` sono completi. Questo legge/verifica i piccoli prompt e scrive codice
di avvio; non carica dataset su Kaggle, non scarica pesi e non esegue inferenza:

```powershell
python reports/analisi/lead_scientist_2026-09-29/neural/build_stack_remote.py `
  --prepared "G:/Il mio Drive/vcc2026/runs/lead_stack_2026-09-29_r2" `
  --out reports/analisi/lead_scientist_2026-09-29/neural/stack_remote_r1
```

Per Kaggle, il builder accetta anche `--stage-data <nuova cartella esterna al repo>`.
La cartella contiene soltanto archivio dei prompt, manifest e metadati privati
`davideferante/vcc-stack-prompts-r1`. Il notebook è privato, T4 e internet abilitati;
il codice è incorporato nel notebook, mentre i due file modello sono scaricati
dalla revision pubblica esatta di Hugging Face e verificati per SHA256 e byte.
Nessuna cellula perturbata HepG2 entra nel dataset di inferenza.

Per Colab, lo stesso builder produce `colab_stack_infer_r1.py`: legge il bundle
montato, scrive `runs/lead_stack_infer_2026-09-29_r1`, usa uno scratch nuovo in
`/content/lead_stack_scratch_r1`. Il coordinatore lo può eseguire con
`python -u <percorso_del_launcher.py>` dopo la verifica della disponibilità GPU.
Non ha dipendenze Kaggle. Tutti i log e gli errori restano nel percorso di output.

## Dipendenze, API e memoria

Il [pyproject di Stack congelato](https://github.com/ArcInstitute/stack/blob/cacc2e4b09435c3e536d46237d10b50f222dd144/pyproject.toml)
accetta Torch ≥2, NumPy ≥1,22 e scvi-tools ≥1. La [versione scvi-tools 1.2.2](https://github.com/scverse/scvi-tools/blob/1.2.2/pyproject.toml)
dichiara Python 3.10–3.12; Torch 2.5.1 ha wheel CPython 3.12 Linux. Questo verifica i
vincoli diretti, **non dimostra la risoluzione transitiva o gli import**. Il job
`colab_stack_dependencies_r1.sh` esegue un dry-run pip nell'interprete Colab reale,
scrive `resolution.json` e versione Python, senza scaricare il checkpoint.

Il runner crea una venv isolata, salva `pip freeze`, esegue `pip check`, i sette
test dell'adapter e importa `stack.model_loading`/`scvi.distributions` prima dei
pesi. Non cambia silenziosamente i pin. Torch/NumPy congelati richiedono Python
3.10–3.12; fuori da questa fascia il launcher si ferma esplicitamente.

API primaria verificata: `get_incontext_generation` è decorato `torch.no_grad`;
il ramo mdm restituisce `(result, test_logit)`. I prompt con meno cellule del set
sono ciclicamente indicizzati modulo la loro lunghezza: non è richiesta una
estrazione senza rimpiazzo di 128 cellule da un pool più piccolo. Il modello
riceve copie, perché aggiorna il test AnnData a ogni passo.

Il [loader congelato](https://github.com/ArcInstitute/stack/blob/cacc2e4b09435c3e536d46237d10b50f222dd144/src/stack/model_loading.py)
carica l'intero checkpoint CPU mentre crea il modello. Checkpoint 2,614 GB + pesi
217M float32 ~0,868 GB fanno già ~3,48 GB, prima di import, buffer e dati.
**Stima prudenziale, non misura:** ~4,5–5 GiB RAM del processo nel caricamento.
Con il banco di conferma già a ~4 GiB su Colab 12 GiB, è preferibile completare il
banco prima del load; almeno 6 GiB `MemAvailable` costituiscono un controllo
pratico da verificare nel runtime. Non si promette un limite VRAM T4: batch 1,
dimensioni dei tensori e numero di parametri effettivi sono registrati dal modello.

## Scoring separato

Usare **`stack_scoring_setup_r2`**, che corregge il controllo MSE. r1 resta un
artefatto precedente non eseguito. Il suo archivio misura 44.867 byte e ha SHA256
`166b2d1f05518c70bb52c097509cf5fa255e49e2fdf8bf34517f084e806462c1`.
Il coordinatore porta i tre file di r2 in
`runs/lead_stack_scoring_setup_2026-09-29_r1` (nome del mount, distinto dalla
revisione locale). Accodare lo SH solo dopo `prediction/finished.json`.
Con output Kaggle, prima riportare la cartella `prediction` su Drive; lo SH
accetta `STACK_PREDICTION_DIR` per il percorso verificato.

Lo scorer usa tutte le cellule pubbliche dei 12 target e gli stessi controlli del
bundle. Verifica 400 cellule/target, assi, integralità, cap e hash. La lettura usa
cinque slope delle ancore ufficiali divise per sei, con MSE separato. MSE è un
**rapporto di somme**: i componenti `expr_mse_unbiased_capped` e
`expr_distance_unbiased`, se presenti, ne verificano l'identità. La media di due
rapporti con denominatori diversi non è il punteggio. Il test [1,0]/[1,9] accetta
0,1 e rifiuta la media 0,5. Cinque test del launcher/readout passano.

Il pilot resta esplorativo; il PDS ha un pannello locale di 12 candidati e non si
confronta direttamente con quello di 48/96/300. Il pretraining non è stato
ricostruito per escludere HepG2. Il proprietario ha confermato al coordinatore la
partecipazione personale e non commerciale; la verifica della FAQ 2026 è
registrata separatamente dal gruppo dati. Questa nota non attribuisce una nuova
licenza ai dati originali o a ogni possibile output.
