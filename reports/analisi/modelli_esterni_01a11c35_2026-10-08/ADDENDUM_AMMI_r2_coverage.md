# Copertura e responsabilità del pilot AMMI r2

9 ottobre 2026, prima di qualsiasi fit AMMI. Evidenza metadata di DATI:
`../../modelli/dati_transfer_2026-10-08_01a11c34/panel_anchor_requests_r1.json`.
Il limite previsto dalla scelta panel-only è ora nominato per contesto:
HepG2, Jurkat e RPE1 non hanno target del pannello nelle viste congelate;
in C-iPSC anche k562_essential non ne ha, mentre K562 GWPS rimane disponibile.
Questi contesti non sono dichiarati supervisione e non ricevono massa della loss.
Le esclusioni outer/inner si applicano comunque prima di calcolare i pesi.

I controlli dei 47 contesti biologici restano pianificati. La loro presenza non
equivale a contributo al training. L'accettazione tecnica del pilot riconcilia
i contesti con supervisione panel ammessa; non afferma copertura del corpus
principale. Il percorso D-053 fuori pannello resta aperto e richiede un'ancora
coerente dentro e fuori pannello, con nuova specifica prima dei numeri.

La selezione NTC è nuova: fino a64 per strato, come r2, solo da metadata.
Non coincide con il vecchio NestedSampler level64, che ripartiva64 per unità
biologica fra strati. Campioni e viste precedenti restano intatti.

Responsabilità confermate con DATI: DATI possiede loader, input, maschere e
ancore; MODELLI-ESTERNI modello, trainer AMMI isolato e preparazione/lancio
del relativo esperimento. La frase di r2 sul trainer principale indica che
non si modifica il trainer condiviso della pipeline, non una delega a DATI
dell'implementazione del nuovo trainer AMMI.
