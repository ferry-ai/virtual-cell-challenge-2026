# Replica anticipata seed 1, senza lettura parziale

**Decisione della lead e preparazione prima degli esiti, 29 settembre 2026.**
Alle 19:16 UTC l'ultima verifica dell'esperimento seed 0 riportava RUNNING e nessun
output disponibile. La lead ha deciso di preparare la replica seed 1 in parallelo
per usare il tempo prima della scadenza. Cambia soltanto il calendario: il nuovo
notebook privato usa i cinque fold, lo stesso dataset r2 e lo stesso training.

`seed=1` sostituisce `seed=0`. `selection_seed=20260929`, split, iperparametri,
architettura, numero massimo di passi e regola di scelta restano quelli originali.
I quattro file di training, protocollo e Pool sono estratti byte per byte dal
payload seed 0 approvato. Il reader incorpora la correzione meccanica già
documentata per il valore letterale `null` e la guardia completa dei cinque fold.

La replica viene letta integralmente anche se seed 0 fallisce. Non si sceglie il
seme favorevole. Non si inferisce una promozione da fold parziali, dal solo seed 1
o dal completamento del job: i due esiti completi rimangono entrambi visibili e
la decisione congiunta segue le soglie congelate. Il fit di produzione conserva
il requisito del gate positivo verificato; non è autorizzato da questa modifica.

Solo dopo tutti i fold e il readout verificato si esegue la sensibilità
`neural_external_validation/cluster_pds.py`, congelata prima degli esiti. Il
processo diagnostico usa predizioni già prodotte, non modifica training o gate.
Il suo fallimento viene salvato separatamente, senza riscrivere la lettura primaria
né trasformare un insuccesso scientifico in successo. Nessuna diagnostica sugli
ABC o sulle predizioni di produzione prive di verità viene proposta.

L'inventario Kaggle conferma i 19 file del dataset r2 esistente, con le dimensioni
locali, escluso `dataset-metadata.json` che è solo metadata di upload. Gli hash
completi dei 16 file piccoli sono congelati dalla copia locale; il manifest remoto
già scaricato ha lo stesso hash. Il runtime li confronta prima di addestrare;
gli array grandi conservano la verifica di dimensioni, forma, dtype e manifest.
Non si caricano nuovi dati o credenziali.

**Quota osservata:** 7,59 ore GPU residue su 30, reset il 3 ottobre. La API espone
quota temporale ma non slot batch liberi: la possibilità effettiva di concorrenza
resta da confermare alla risposta del push autorizzato, senza tentativi di avvio
preventivi. Risorsa richiesta: T4 gratuita, GPU0; nessuna risorsa a pagamento.

Questa preparazione non esegue il push. Metadata, notebook e hash del payload
devono essere revisionati dalla lead prima dell'avvio remoto.
