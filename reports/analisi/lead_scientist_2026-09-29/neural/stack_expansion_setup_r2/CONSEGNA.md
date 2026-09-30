# Preparazione conferma Stack, revisione 2

**Implementato e verificato localmente, non eseguito sui dati reali.**
La shell `colab_stack_confirmation_prepare_r1.sh` è il payload per job 075;
legge solo le righe K562 dei dodici target già registrati, riusa i due file
di controlli byte per byte dal bundle 064 e conserva gli effetti congelati.
Non carica modelli e non legge outcome perturbati HepG2.

Destinazione setup su Drive:
`vcc2026/runs/lead_stack_expansion_setup_2026-09-29_r2`.
Output nuovo: `vcc2026/runs/lead_stack_confirmation_prompts_2026-09-29_r1`.
La shell richiede almeno 2 GiB di RAM disponibile; i 1421 nuovi profili
sorgente comportano 46.9 MB di conteggi densi utili, oltre alla lettura dei
metadati dell'originale. Il file originale da 65.8 GB viene letto per righe,
senza copiarlo integralmente. I controlli già preparati sono circa 23 MB.

Il manifest nuovo conserva `destination_size` e lega helper originale,
adapter di esportazione profili, scorer finale e protocollo definitivo.
Lo scorer riproduce esplicitamente la precisione della divisione NumPy
dell'ambiente di inferenza solo per verificare q0; campiona sempre il profilo
float64 esportato, senza ricostruirlo dai 400 conteggi finali.

Il pacchetto conserva anche la preparazione produzione 254+46 fallback,
che resta separata dalla preparazione conferma. Nessuna di queste shell
autorizza inferenza, scoring, upload o promozione del candidato.

Validazione locale: sette test sintetici dei pack passati; due controlli
del contratto sullo snapshot reale; parità dell'exporter con il pilot su
24 profili pre-campionamento; dodici test dello scorer (responsabilità
dell'agente scientifico). Gli hash immutabili sono in `artifact_hashes.json`.
