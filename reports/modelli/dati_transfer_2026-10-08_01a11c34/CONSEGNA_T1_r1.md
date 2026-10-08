# T1 pronta per il banco — 8 ottobre 2026

**Misurato:** fit concluso e verificato nel job pubblico
`davideferrante11/vcc-fit-banca-canonica-dt1-01a11c34-r1`, versione 1.
Nessun beneficio predittivo misurato e nessuna promozione. t36 resta riserva.

- Release: [release_t1_r1.json](release_t1_r1.json), SHA256
  `277ae3441b78c9a1ebf79149cff914fb494d8fff09529b367e9f42cb6a76ffd8`.
- [Verifica indipendente di codice e output](fit/dt1-01a11c34-r1/verification.json).
- [Consumo](fit/dt1-01a11c34-r1/consumo.json): 16 fonti attese = verificate = lette;
  16 target con nuovi voti rispetto a t36, nessun cambiamento fuori da questi target.
- Effetti di produzione: `C:/Users/ferra/vcc2026-data/processed/dati_transfer_2026-10-08_01a11c34/t1_r1/effects/`.
  I file `effects_A.npz`, `effects_B.npz`, `effects_C.npz` sono identici, ciascuno
  18.826.719 byte, SHA256 `28f15de7418fdab741bd0bc61049d6f4c8e843cafd016027101697e11c28a6f5`.
- Stesso stage 100 e driver della banca canonica; ampiezza e cis già applicati,
  scala emissione t28 ancora da applicare. Release di produzione, **non fold C/T/J**.
- Risorse misurate all'avvio: 4 CPU, RAM disponibile 30,45 GiB, disco 19,50 GiB.

## Per VALIDAZIONE

La vostra cartella `reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/`
è stata individuata; letti protocollo v1 e split J-HEK293 con alias HEK293T → HEK293.
Il nuovo consumer accetta lo schema `id/regime/held_groups/hidden_targets/protected_units/group_aliases`.
Per T1 i fold vanno ricalcolati dalla release come da vostro §3; gli effetti di
produzione non sostituiscono i fold. Non ho modificato il vostro banco o documenti condivisi.

La derivazione tutti-target è implementata in `fold_bank.py`, con test su
contaminazione di risposte e maschere escluse, controllo positivo, parità a blocchi,
modalità, controlli mancanti e protezione H1 test. Pacchetti di derivazione in
preparazione; nessun loro job ancora autorizzato o avviato. Il primo split è di
produzione; produrrò pacchetti con i vostri split separati per le statistiche T/J.

## Incidente di recupero, circoscritto

Il CLI Kaggle ha scaricato tutti gli artefatti richiesti e poi terminato con errore
di codifica cp1252 del log. [Ricevuta preservata](fit/dt1-01a11c34-r1/retrieval.json).
Ho separato recupero e verifica: nessun nuovo fit o download per aggirare l'errore.
Codice remoto, release, consumo e tutti gli SHA degli effetti hanno superato la
verifica successiva. La correzione è `cloud_fit.py verify`.

## Stato e limiti

Nessun runtime ora occupato da DATI-TRANSFER. Colab non verificato come attivo:
l'ultimo heartbeat nel log accessibile è del 3 ottobre. Kaggle disponibile sui tre
account nel preflight r2; la quota residua non è esposta da quel controllo.
Le 45 unità della banca sono riconciliate a livello metadati in `audit_r1.json`;
39.973.948 cellule includono i 38.176 controlli H1 duplicati noti. Nessun campione
cellulare letto per apprendimento da questi fit: D-053 rimane aperto.

Per registri/indici: questa è una consegna tecnica T1 e un riconto verificato,
non un esito di confronto da promuovere. Gli aggiornamenti condivisi restano a
VALIDAZIONE per mandato del proprietario.
