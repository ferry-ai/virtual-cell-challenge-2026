# Pacchetto privato Kaggle del banco generatore

**Tipo:** implementato e verificato localmente; la presenza del notebook non prova un'esecuzione.
Lo stato remoto viene comunicato separatamente dopo la risposta del servizio.

Destinazioni nuove: dataset privato `davideferante/vcc-lead-generator-inputs-r1` e notebook
privato `davideferante/vcc-lead-generator-r1`. Le risorse precedenti non vengono modificate.
Lo staging è `C:/Users/ferra/vcc2026-data/interim/kaggle_lead_generator_r1/dataset`.

## Lista autorizzata degli input

| Origine relativa alla radice dati | Byte |
|---|---:|
| `raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad` | 850590740 |
| `external/K562_gwps_raw_bulk_01.h5ad` | 374587922 |
| `processed/banco_hepg2_v2_2026-09-26/t19like.npz` | 10704635 |
| `processed/banco_hepg2_v2_2026-09-26/targets.txt` | 2148 |

Totale dati: 1235885445 byte. Sono hardlink ai quattro originali, mai aperti in scrittura;
non richiedono una seconda copia da 1,15 GiB. I 104 file del codice e protocolli sono enumerati
uno per uno, con SHA256, in `input_manifest.json` nello staging. Comprendono `src/vcc2026`,
gli script e configurazioni testuali, codice/protocolli di questo report e ancore ufficiali.
Nessuna credenziale, controllo privato della gara o audit privato delle identità entra nel pacchetto.

Il solo archivio del codice è `code_snapshot.tar.gz`, 269663 byte, SHA256
`d58da4136a244d98aff7796e258c652cf07b7bebcc60df22a79ce50f69c02053`.
Colab e Kaggle devono usare questo stesso archivio. Gli script Kaggle aggiunti dopo il freeze
sono incorporati nel notebook; non modificano il banco congelato.

## Conferma dopo sviluppo

Il notebook non avvia lo sviluppo e non rigenera il manifest dei bersagli. La prima versione
del dataset, da sola, non consente il calcolo: manca deliberatamente lo sviluppo concluso.
La versione successiva aggiunge `development_bundle.tar.gz` e `development_bundle_manifest.json`.
Il tar contiene soltanto file regolari sotto `generator_r1/`, almeno:

- `target_manifest.json`, immutato dalla preparazione Colab;
- `prepared_effects.npz`;
- `development/selection.json` e gli altri risultati di sviluppo;
- possibilmente `development_environment.json`, con chiave `versions`, per riprodurre anche
  le versioni delle dipendenze non registrate dalla preparazione originale.

Il manifest del bundle ha `code_archive_sha256`, `archive` (`upload_name`, `sha256`) e `files`
(lista di `relative_path`, `sha256`). I percorsi iniziano con `generator_r1/`.
Il notebook verifica ogni hash; ricostruisce il layout dei quattro dati mediante symlink al
mount Kaggle; conserva la selezione e avvia soltanto il riferimento più uno o due finalisti,
semi 1/2/3, split di conferma congelato. Se non esistono finalisti termina senza scoring.

Le versioni note da Colab vengono richieste esattamente all'installazione. Lo scorer deve
essere `cell-eval2==0.16.0`; differenze rimanenti sono registrate in un report d'ambiente.
Un nuovo lancio usa una nuova cartella output, mai un risultato già esistente.

La creazione del dataset usa la CLI senza `--public`; il parametro di richiesta è quindi
`is_private=true`, verificato nel client installato. Anche `kernel-metadata.json` dichiara
`is_private=true`, GPU/TPU disattivate. `kernels push` avvia il notebook: non è un semplice
salvataggio, e resta separato dalla preparazione locale e dall'upload degli input.
