# Bootstrap separato per gli stadi 45 e 48

**Preparato, non accodato o eseguito su Colab.** `bootstrap_candidate_env.py` non genera
cellule e non impacchetta predizioni. La modalità predefinita `plan` legge soltanto;
`create` richiede una nuova directory e prepara una venv usando l'interprete Python
3.13 del runtime corrente, con `system_site_packages=True`.

La metadata locale di `vcc-cli==0.2.0` dichiara `Requires-Python >=3.11` e una classifier
esplicita per 3.13. Richiede AnnData≥0.10, NumPy≥1.24, pandas≥2, SciPy≥1.10,
zstandard≥0.22, click≥8.1, httpx≥0.27, keyring≥24 e google-crc32c≥1.5.
Il runtime del banco registrato in `generator_development_r3/development_environment.json`
è Python 3.13.15, NumPy 2.1.3, SciPy 1.16.3, pandas 3.0.6, h5py 3.16.0 e AnnData
0.13.4: le versioni soddisfano i vincoli dichiarati della CLI. Questo non è ancora
una misura di compatibilità ABI della nuova venv.

Il bootstrap controlla prima che le versioni scientifiche siano quelle del banco
completato, inclusi PyYAML e cell-eval2. Salva l'inventario completo della base e lo
usa come file di vincoli. Installa la sola CLI 0.2.0 dentro la venv, poi risolve le sue
dipendenze mantenendo ferme tutte le versioni ereditate. Usa il PyPI pubblico,
`pip --isolated`, solo wheel e l'interprete esplicito della venv; non installa nella
base, non cambia interprete e non forza build o pacchetti incompatibili. Le eventuali
dipendenze mancanti vengono aggiunte soltanto alla venv.

Prima di dichiararsi pronto verifica:

- inventario della base invariato;
- versione e origine della CLI dentro la nuova venv;
- versioni scientifiche ancora identiche e import di NumPy/SciPy/pandas/h5py/AnnData,
  PyYAML e cell-eval2 riusciti;
- piccolo roundtrip AnnData/CSR/HDF5 con conteggi interi identici;
- requisiti attivi della CLI soddisfatti e contesti ufficiali A/B/C;
- import e parsing `--help` di entrambi gli stadi estratti dal medesimo archivio r3.

La preparazione si ferma con log preservati se la base è cambiata, un import o un
vincolo fallisce, o la directory esiste. Non corregge il runtime usato dai banchi.
Il controllo non equivale a un test dell'intera generazione o del packaging.

`bootstrap_template.sh` contiene i percorsi Drive verificati e resta privo di numero
di job e directory finale fino alla revisione. Dopo `ready.json`, il comando concreto
del candidato deve usare **`$ENVROOT/venv/bin/python generate_candidate.py ...`**:
il launcher già revisionato costruisce entrambi i comandi con `sys.executable`, quindi
stadi 45 e 48 usano esattamente quella venv. Conferma e preregistrazione restano
obbligatorie; bootstrap e generazione sono azioni distinte.

## Aggiornamento della sessione principale

Il bootstrap SHA256 `6138753a7a654f5359194807530acaef2d52b0ef8f06b09208d7d25e19e8e5e6`
è stato revisionato e il job `067_lead_candidate_environment_r1.sh` è stato accodato
dalla lead. La directory prevista è `/content/lead_candidate_environment_r1`; il report
su Drive è `runs/lead_candidate_environment_2026-09-29_r1`. Il wrapper
`colab_candidate_environment_r1.sh` conserva i soli file al primo livello anche in caso
di errore. Accodamento riferito dalla sessione principale: qui non è ancora registrata
una verifica riuscita della venv e non è stata avviata la generazione.
