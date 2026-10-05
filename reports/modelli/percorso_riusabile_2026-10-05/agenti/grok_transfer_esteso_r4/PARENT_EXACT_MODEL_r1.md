# Nuova precisazione umana: SOLO banca, stesso modello t28

Proprietario: «vorrei ritrainare esattamento il modello di transfer più performante
(quello che era quasi a0.15) cambiando solo la banca dati sulla quale è trained e
vedere se ci sono miglioramenti». Leggi ../../TRANSFER_IDENTICO_r1.md prima di
consegnare ready. Riferimento identificato t28=0,14484520500645978 ufficiale,
effetti t25(cache r9,configs/recipes/t25.json) ed emissione t28. Freeze originale
codice/pipeline/hyperparam/aggregazioni/NaN/cis/emitter: cambia SOLO banca ammessa.
Nessun nuovo ibrido o redesign del modello dentro l'esperimento. Tutte fonti
possibili, non solo Norman/iPSC, no pilot ridotto.

Difetto concreto da verificare del codice già scritto: _one_target chiama
effects_from_pseudobulk coi soli donatori con target>=10. L'originale usa TUTTI
controlli disponibili nel pool ctrl_frac della condizione anche se quel donatore
non ha il target. A parità di matrice questo può cambiare il mask min_control_frac;
non attribuire alla banca un cambio d'algoritmo. Usa snapshot effettivo della
funzione originale/vendored identico + adapter metadata/split/mask, prova piccola
di equivalenza su stesso input compatibile. Non riesaminare il design completo.
Mantieni cis head configurata t25 (pairs,max_distance5000,scale2) nel modello
complessivo. Nuovo/vecchio sullo stesso banco C/J, emissione t28,400cells*5pairedseeds;
score sito0,144845 non baseline diretta di uno score locale. Ora primo pacchetto
lanciabile per questo ESATTO esperimento, poi parentpush/training reale.
