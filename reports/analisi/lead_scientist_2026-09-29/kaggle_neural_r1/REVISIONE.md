# Notebook neurale privato: materiale per revisione

**Implementato, non ancora eseguito.** Nuovo notebook
`davidmaisterx/vcc-lead-neural-sources-r1`; nessun notebook precedente viene modificato.
Il dataset esistente `davidmaisterx/vcc-rete-contesti-r2` è stato verificato privato e
`ready`, versione 1, ID 12242239. Nessun dato viene caricato di nuovo.

`review/` contiene notebook, metadati, manifest dell'allowlist e hash. Nel notebook è
incorporato un tar base64 di esattamente cinque file: i tre script neurali di questo
report, `PROTOCOLLO_NEURALE.md` e il solo `pool.py` storico. L'archivio è disponibile
separatamente per l'ispezione. SHA256:
`283d4f592f87fcd969a4dec80d2138ce1568eeef1ac2c4dd0485e641185780bf`.

Il launcher leggibile è `neural_kaggle_runner.py`. Verifica hash dell'archivio e di ogni
file sorgente, SHA256 del manifest dati, dimensioni dei file, header e apertura mmap
in sola lettura delle matrici. Non legge tutte le matrici in memoria e non ricopia i dati.
Registra hardware CUDA, versioni e manifest prima del training. Richiede GPU e non degrada
silenziosamente su CPU. Internet è disabilitato e non installa pacchetti.

Esegue in processi separati K562, CD4, Orion, iPSC e RPE1, regime C e seed 0, con tutte
le opzioni del protocollo esplicite. Un fold fallito lascia codice di uscita e log,
mentre gli altri vengono comunque tentati. La lettura macro-famiglia si avvia solo
se tutti e cinque completano. Nessun risultato parziale diventa un verdetto complessivo,
nessun fit di produzione e nessun invio VCC seguono automaticamente.

Acceleratore richiesto: `NvidiaTeslaT4`, con `CUDA_VISIBLE_DEVICES=0` per usare una sola
GPU. La documentazione ufficiale descrive la risorsa Kaggle T4 come T4×2 e indica che
P100 è ritirato e sostituito dal default: non si promette una macchina P100.
[Documentazione ufficiale Kaggle](https://github.com/Kaggle/kaggle-cli/blob/main/skills/references/kernels.md).
La quota gratuita osservata era 8,92 ore GPU residue; non vengono acquistate risorse.

Prima del push, la sessione principale revisiona notebook e metadati. La presenza dei
file non prova che l'esecuzione sia stata autorizzata o avviata; lo stato remoto sarà
registrato separatamente dopo la risposta del servizio.
