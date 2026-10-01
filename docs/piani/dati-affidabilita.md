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
