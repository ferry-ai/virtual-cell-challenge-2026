# Revisione lead del 1 ottobre 2026

Codex, chat `01a0f724-6a42-7dd0-bd2f-3496d9195695`. Mandato e limiti in
[PROTOCOLLO](PROTOCOLLO.md). Risultati esplorativi nuovi; nessun training, invio o dataset scaricato.

**Leggere [REVISIONE](REVISIONE.md)** per diagnosi, evidenze e conseguenze. Il programma operativo
è [R-LEAD](../../../docs/piani/strategia-scientifica.md); per l'agente del training c'è una
[nota tecnica](NOTA_TRAINING.md) con file, difetti e verifiche richieste.
**Arrivato durante la revisione:** [R3 completato e diagnosi del collasso](AGGIORNAMENTO_R3.md),
con un nuovo controesempio sul gradiente del gate.

| Materiale | Che cosa prova |
|---|---|
| `analyze_outputs.py`, `r1/` | Ricalcolo dei 1.026 gruppi di valutazione per ciascuno dei due bracci r2; composizione r5/r7, output per target e hash |
| `replay_sampler.py`, `sampler_r1/` | Riproduzione di tutti i 50.172 batch; esposizioni per studio identiche al log; coefficienti effettivi della loss |
| `reproduce_findings.py`, `counterexamples_r1/` | Controesempi con il codice originale: confronto unknown non supervisionato, gradiente della baseline dalle perturbate, classe C errata dopo QC |
| `analyze_hepg2.py`, `data_r1/` | Lettura delle 145.473 cellule locali HepG2, asse nativo di 9.624 geni; riproducibilità metà/metà, cis, numerosità e cambi degli split |
| `analyze_design.py`, `design_r1/` | Ricostruzione del serbatoio controlli HepG2 e confronto oracolare di complementarità rete/transfer |
| `analyze_r3.py`, `r3_followup_r1/` | Rianalisi degli output appena arrivati di r3; intersezioni C/T/J e controesempio del clamp che ostacola il recupero del gate |
| `VERIFICHE.md` | Comandi, controlli completati, stato remoto letto e limiti |

I tre file della rete letti hanno gli stessi SHA256 registrati dal training r2. Gli script
qui importano il codice esistente senza modificarlo. Per riprodurre in futuro controllare gli
hash: i file di R-LAB sono ancora in sviluppo. Ogni esecuzione deve usare una nuova directory
di output. I CSV sono statistiche derivate, non copie dei dataset.
