# Prerequisito indipendente di accesso/reader in corso

Parent ha lanciato davidmaisterx/vcc-reuse-runtime-norman-ipsc-r1, CPU privata,
input dataset pubblici Norman v1 e iPSC v3. All'ultimo controllo è RUNNING.
Non è ingestion né fit: verifica mount cross-account, hash di tutti i file,
layout/alias originali, lineage fra PopulationReader e SampleReader Norman.
Output access_runtime_r1/verified comparirà solo dopo verifica della chiusura.
Non rilanciare/duplicare questo lavoro. Parent preflight fresco access_runtime_r1/preflight.json
alle 16:24:52 UTC vedeva un job df11; con il nuovo job considerare uno mx aggiuntivo.
L'endpoint dataset_status dal consumer dava404, ma metadata GET pubblica funziona:
owner verifica versione, consumer verifica accesso pubblico e runtime verifica byte.
Prosegui pacchetti derivazioni con split/assi/componenti prima delle statistiche.
