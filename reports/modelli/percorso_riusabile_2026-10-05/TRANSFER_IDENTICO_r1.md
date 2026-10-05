# Esperimento richiesto: stesso transfer t28, cambia solo la banca

Mandato umano del5ottobre: ritrainare esattamente il transfer con massimo osservato
vicino0,15, cambiando solo banca dati, per misurare l'effetto dell'espansione.
Identificato da CP-0052/status originale: **t28,0,14484520500645978**. È il modello
di effetti t25 con generazione t28; ricetta configs/recipes/t25.json, cache r9,
emissione effects_scale1.5,gene_dispersion=true,gene_dispersion_scale1.0,
400cellule,target,seed20260912. Il massimo osservato non era una promozione conclusiva.

Congelare modello/algoritmo/statistica e regole di aggregazione, preprocesso,
shrinkage,min_expected1,pseudocount0.5,phi0.2,min_control_frac1e-6,min_cells10,
gamma1,reliability_scale100,ampiezza1.576,regola pesi originali,cis head distanza
5000bp scala2 e stesso file coppie, emettitore/controlli/assi. I pesi di fonti nuove
applicano la stessa politica congelata, senza tuning sui risultati. Unica variabile
del confronto: banca di dati ammissibili, con tutte le fonti possibili e blocchi
nominati. Nessuna correzione neurale/ibrido o cambio ricetta dentro questo confronto.

Gli adapter necessari al nuovo storage devono riprodurre le stesse uscite a parità
di input compatibile. Il codice derivativo nuovo non è automaticamente lo stesso
modello: r3 _one_target seleziona controlli dai soli donatori con target, mentre
effects_from_pseudobulk originale calcola ctrl_frac dal pool di tutti i controlli
nella condizione. Verificare equivalenza/risolvere differenza prima di lanciarlo
come rifit identico. Anche grouping/condizioni,pesi donor/condizione,NaN vs0,
maschere e testa cis devono essere legati alla ricetta originale, non ridisegnati.

Confronto vecchia banca/nuova banca sugli stessi fold C/J e target/componenti
nascosti globalmente prima di statistiche. Emissione t28 identica in entrambi,
400cellule*5semi appaiati, soglie preregistrate. Il punteggio locale non si confronta
direttamente col0,144845 del sito: vecchio/nuovo sul medesimo banco, nessun invio
VCC autorizzato da questa richiesta. Conservare manifest/hash/codice/output e uso
effettivo delle fonti; training esteso reale prima di dichiararlo avviato.
