# Primo training effettivamente avviato

4 ottobre, circa 23:00 CEST. [Stato remoto](status_r1.json).

- Sei job della banca CD4 RUNNING; dodici unità previste, non ancora complete.
- Tre preparazioni CPU COMPLETE sul terzo account: H1, HepG2, Jurkat escluse intere.
- `davidmaisterx/vcc-hybrid-train-h1-r1` RUNNING: Tesla T4, CUDA 12.8;
  nel [log vivo](live_train_h1_r1.txt) il primo braccio raggiunge 3.000 passi.
  Input: 39.001 righe, 13.425 geni, 32 tabelle, nove famiglie di training.
- HepG2 e Jurkat: trasferimento privato e avvio automatico affidati a
  `dispatch_training_r2.py`, processo locale già in esecuzione. R2 corregge soltanto
  la decodifica UTF-8 del CLI; il dataset H1 era già stato creato correttamente.

È il primo cohort aggregato: banca nuova per donatore, campionamento cellulare e
catalogo integrale non sono ancora incorporati nel fit. Nessun risultato di banco
o miglioramento scientifico dichiarato. Nessun dato o modello reso pubblico.
