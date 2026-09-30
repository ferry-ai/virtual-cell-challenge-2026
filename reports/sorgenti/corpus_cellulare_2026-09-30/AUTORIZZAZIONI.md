# Autorizzazioni del proprietario per R-LAB

Trascritte da Claude (sessione `a1ec75f0`) dalle risposte del proprietario in chat, ricevute prima
delle 19:38 del 30/09 (ora letta con `date` subito dopo). Valgono per questa sessione e per i job
qui elencati; un agente nuovo le conferma in chat prima di usarle (`CLAUDE.md`).

| Domanda | Risposta del proprietario |
|---|---|
| Dove salvare in modo persistente gli shard delle cellule | **Google Drive** (prima si misura la quota libera dal runtime) |
| Via ai job J01–J03 di `PIANO_JOB.md` | **Sì, J01–J03**: J01 HepG2 dal Drive; J02 HIPSCI scaricato da Figshare sul runtime (7,93 GB, MIT); J03 Jurkat scaricato dal GEO (circa 3,8 GB); su Colab o Kaggle, con preflight |
| Account Colab e Kaggle | **Più account, confermato**: il proprietario conferma che l'uso degli altri account rispetta i termini dei servizi |
| Riserva | **Sì, H1 2025 come riserva**: prima locatore e byte da mostrare al proprietario, poi download congelato con hash, da leggere una volta sola |

Non autorizzati da queste risposte: i job J04–J12 e i loro download, un invio, un push.

**Conferma alla sessione successiva.** La sessione `a1ec75f0` ha esaurito i token dopo aver scritto
questo file. La sessione di Claude Code che l'ha ripresa (`ec2e5b07`) ha chiesto al proprietario di
confermare le autorizzazioni prima di usarle. Risposta in chat, prima delle 20:00 del 30/09 (ora
letta con `date` alle 20:00:21, subito dopo): «Certo confermo, anche la disponibilità di vari account
colab e kaggle». La conferma copre J01–J03 su Colab con shard su Drive, i download sul runtime di
HIPSCI (Figshare) e di Jurkat (GEO), e H1 2025 prima con locatore e byte mostrati, poi scaricato.
Restano esclusi invii e push.

**H1 2025, dopo aver visto locatore e byte** (in chat, prima delle 20:47 del 30/09: ora letta con
`date` quando il job 089 è stato messo in coda, dopo le risposte). Mostrati al proprietario: bucket pubblico
`gs://arc-institute-virtual-cell-atlas/virtual-cell-challenge/2025/`, letto via HTTPS senza costi;
`adata_Training.h5ad` 15,48 GB, `adata_Validation.h5ad` 6,93 GB, `adata_Test.h5ad` 11,95 GB, con i
crc32c del bucket. Risposte:
- **download:** «Sì, dopo J02», su Drive, come dato congelato: job 089, che attende il `.done` di 088;
- **ruolo:** «Parte riserva, parte training», con l'esempio proposto: lo split di test (100
  bersagli) è la riserva, train e validation (200 bersagli) vanno nel training da subito.

**Decisioni della sera del 30/09 (sessione `ec2e5b07`), in chat, prima delle 21:56 (ora letta con `date`):**
- Drive ha 2 TB: il download di H1 si anticipa (job 090, senza attesa di J02).
- Obiettivo: una rete addestrata **direttamente sulle singole cellule**, su tutti i dataset utilizzabili, non
  un'estensione della rete sugli effetti. Inventario completo (scPerturb compreso), ingestione progressiva con
  streaming e shard, adattatori per formato, modalità gestite esplicitamente e mai escluse in automatico. I conteggi
  originali sono la supervisione principale, con maschere, controlli appropriati e QC documentato; il raw resta
  immutabile e le trasformazioni del modello stanno a parte. Niente medie, LFC o valori shrunk al posto delle cellule;
  il pseudobulk solo come baseline o controllo. Le sorgenti solo aggregate si dichiarano e si trattano a parte. Un
  primo training su un sottoinsieme vale come verifica tecnica, non come risultato. Restano escluse le riserve
  concordate. Parole del proprietario trascritte nel README, §8.
- Più notebook e più account per parallelizzare: autorizzato. Colab per la CPU, Kaggle per la GPU (30 ore a settimana).
- Il token dell'account Kaggle `davideferrante11` (creato dal proprietario alle 21:18) è copiato, con il suo via, in
  `MyDrive/vcc2026/runs/rlab_secrets/`: i job Colab lo usano solo per pubblicare gli shard nei dataset privati di
  quell'account, dove gira il training. La chiave non è mai stampata né scritta nella repo.
- Secondo dispatcher Colab su `runs/queue2`: autorizzato; lo avvia il proprietario.
