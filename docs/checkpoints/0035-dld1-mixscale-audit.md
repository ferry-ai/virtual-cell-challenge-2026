# CP-0035 — DLD-1 e Mixscale: copertura misurata e primi confronti fra contesti

- **Data:** 2026-09-24
- **Tipo:** osservazione
- **Redatto da:** Codex
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Quanto delle nuove sorgenti DLD-1 e Mixscale è utilizzabile e quanto segnale
specifico del bersaglio si trasferisce fra contesti?

## 2. Cosa è stato fatto

Audit dei quattro file DLD-1 già locali e confronto con K562 r5; acquisizione del
solo archivio DE Mixscale da Zenodo, checksum verificato, confronto fra sei linee.
Script, protocolli, comandi e limiti sono in
`reports/dld1_audit_2026-09-24/RISULTATI.md` e negli script della stessa cartella.

## 3. Cosa si è osservato

**Misurato:** DLD-1 Low1 contiene 2.827 geni di risposta, 2.587 sull'asse ufficiale,
67/300 bersagli e 61 condivisi con K562. Su 2.259 geni, Pearson mediana 0,01838 e
accordo di segno sui primi 100 effetti K562 52%, contro 50% a bersagli diversi
(`reports/dld1_audit_2026-09-24/r1/measurements.json`).

**Misurato:** archivio Mixscale: 271 file, 218 bersagli, nove del pannello, sei linee.
Tenendo fuori una linea per stimolo, su 1.626 confronti: Pearson mediana 0,02714
contro 0,01551 del controllo che ignora il bersaglio; segni 61% contro 58%
(`reports/dld1_audit_2026-09-24/mixscale_r1/measurements.json`).

## 4. Interpretazione e incertezza

**Interpretazione:** specificità descrittiva modesta. La copertura della matrice DE
DLD-1 è limitata; Mixscale serve soprattutto a studiare il trasferimento, vista
la piccola intersezione con il pannello. Non sono punteggi VCC né prove di adozione.
Le stime DE Mixscale possono condividere selezioni o parametri fra linee;
la prova non dimostra generalizzazione indipendente di una rete.

## 5. Spiegazione semplice

Un dataset grande può contenere pochi dei geni che dobbiamo prevedere.
Avere sei linee aiuta a fare confronti nuovi, ma non prova da solo che il modello
generalizzerà meglio: deve battere anche una previsione che ignora il bersaglio.

## 6. Conseguenze

Nessuna ricetta o decisione modificata. Conservare i contesti lontani come candidati;
prima di integrarli verificare unità, maschere e separazione di linee/studi.
Piano nel report. Nessuna nuova sorgente adottata e nessun invio.

## 7. Cosa corregge

Nessun checkpoint precedente. Precisa la sintesi esterna incollata dal proprietario:
la matrice pronta DLD-1 non copre l'intero trascrittoma; la prima analisi Mixscale
non richiede decine di GB né Colab; per Jurkat la sottoserie è GSE249595.

## 8. Domanda di comprensione

Perché 218 bersagli in sei linee possono servire alla ricerca anche se soltanto
nove appartengono al pannello attuale?
