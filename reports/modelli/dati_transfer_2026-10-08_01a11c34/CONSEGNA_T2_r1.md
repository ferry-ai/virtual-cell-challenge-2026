# T2 — effetti congelati e verificati

**Misurato:** il job CPU privato `davideferrante11/dt-final-t2-01a11c34-r1`
è completato. La ricevuta attesta 16 fonti e 118,72 secondi di calcolo.
Il ramo nullo ha riprodotto gli hash T1 prima di cambiare la centratura.
Gli array T2 scaricati sono stati verificati indipendentemente:
[candidate_t2_r1.json](candidate_t2_r1.json).

Ogni contesto ha un NPZ di 18.821.797 byte, SHA256
`d496a38dad7f597cf586199d3ffe40c430e957ba82c78a8fe8da4bcedd6e0ab2`.
Percorsi assoluti nel manifest, sotto la radice dati `processed/dati_transfer_2026-10-08_01a11c34/t2_r1/effects/`.
Assi identici a T1, matrice 300 × 18.533 float32, maschera booleana invariata:
4.461.086 osservati e 1.098.814 mancanti. I mancanti sono zero soltanto
nell'interfaccia finale, e restano identificati dalla maschera.

Unità: log naturale del fold change. Ampiezza 1,576 e cis già applicati;
emettitore non applicato. A/B/C hanno gli stessi effetti: non è un modello
che apprende una risposta specifica del contesto. La differenza rispetto
a T1 ha norma L2 32,159 e massimo assoluto 0,7734; è una diagnostica,
non una misura di miglioramento predittivo.

Prove: `final_t2/r1/fit/completion_r1/t2_consumption.json` e `verification.json`,
`verify_t2.py`, `final_t2/output_retrieval_r1.json`. Il primo recupero delle
ricevute ha incontrato un errore Windows nella scrittura Unicode del solo log;
le ricevute erano integre e sono state verificate. La modalità UTF-8 è ora
esplicita nel client, e il recupero degli effetti ha codice di uscita zero.
Nessun rilancio del fit è stato necessario.

Per il banco usare le statistiche coerenti con il regime descritte in
[HANDOFF_T2_MEDIE_r2.md](HANDOFF_T2_MEDIE_r2.md). Questi effetti sono di produzione;
non sostituiscono gli effetti dei fold C/T/J. VALIDAZIONE resta responsabile
del confronto e della raccomandazione, senza duplicazione del suo banco.

La consegna è un candidato di effetti, non una generazione cellulare,
un pacchetto VCC o una dimostrazione di beneficio. t36 resta fallback.
La copertura completa D-053 e il primo fit ESM2 esteso restano distinti.
