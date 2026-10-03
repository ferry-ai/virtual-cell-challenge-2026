# R-DATI — colmare lacune misurate dei dati

- **Stato:** in attesa della fattibilità e matrice di esposizione R-LEAD P0/P1, o di un confronto P4.
- **Aggiornato:** 2 ottobre 2026, dipendenze allineate al nuovo R-LEAD (D-052).
- **Assegnazione:** audit del 25/09 completato da Claude `f4f38e58` e collaboratori;
  nessuna acquisizione nuova assegnata dal rinnovo.
- **Prossimo passo:** identificare quale controllo, replica, guida o sovrapposizione manca
  per risolvere un limite specifico; partire dal corpus già prodotto in [R-LAB](piano-giorno-2026-09-30.md).
- **Dipendenze:** P0/P1 o P4 di [R-LEAD](strategia-scientifica.md), [GENERALIZZAZIONE](../GENERALIZZAZIONE.md),
  disponibilità e autorizzazioni per l'eventuale acquisizione.

## Consegna utile

**Sottoattività di archivio, richiesta in chat il 3 ottobre:** Codex, sessione
`01a10114-058a-7342-9f0e-7942cc43ad6c`, portatile Windows, presa in carico alle 12:43 CEST.
File e nuove prove in [libera_spazio_2026-10-03](../../reports/sorgenti/libera_spazio_2026-10-03/README.md):
prima rimozione conclusa alle 12:49 CEST (14,517 GiB di copie già verificate su Kaggle).
I job Colab 130–131 sono partiti il 3/10 alle 14:00 CEST; alla verifica delle 14:40
non erano ancora visibili ricevute degli hash. Il proprietario affida ora la regia a Claude1;
il monitor periodico Codex è sospeso. Stato, consegna Claude2 e correzioni nella
[revisione ingestion](../../reports/sorgenti/revisione_ingestion_2026-10-03/README.md).

**Ingestion, precisazione del proprietario del 3/10:** Drive ha 5 TB di capacità dichiarata;
l'obiettivo CD4 è l'acquisizione completa delle cellule idonee, senza tetto definitivo di
10 cellule per guida. Spazio libero, copie già presenti e dimensione degli output vanno
misurati. Campioni iniziali e bilanciamento del training sono scelte distinte dall'archivio.
Codex termina la revisione locale e consegna a Claude1 la prosecuzione; nessun nuovo job
o seguito Claude2 è stato avviato durante il passaggio. La revisione conserva i dettagli
e le condizioni di adozione; non cambia i ruoli e gli split di R-LEAD.

Una tabella di lacune con domanda, file necessario, ruolo C/T/J, unità e maschere,
controlli/repliche/guide, accesso, byte e limite che risolve. Distinguere overlap dei target
e copertura dei geni di risposta; zero overlap con i 300 non esclude una sorgente.
Non ripetere l'inventario sulla base delle liste d'attesa del 25/09.

CD4 è già Flex; H1 train/val e HIPSCI sono nel corpus. I risultati e le limitazioni
sono nell'[indice delle sorgenti](../../reports/sorgenti/README.md); presenza e uso reale
si verificano nei manifest e nel replay del training. H1 test resta chiusa.

## Chiusura e alternative

Una lacuna si chiude con file/QC verificati e ablation a split fisso, oppure con la prova
che quei dati non permettono il confronto. Se il problema è campionamento o qualità,
correggerlo prima di aggiungere cellule. Nessun obbligo di acquisire tutte le sorgenti.

[Audit e ipotesi H7–H10 del 24–26/09](../storico/rinnovo_2026-10-01/docs/piani/dati-affidabilita.md).
