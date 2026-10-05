# Urgenza del proprietario: avvio del primo training esteso, design in parallelo

MESSAGGIO UMANO nuovo: «Grok deve iniziare il training il prima possibile, anche
subito, e deve essere un training esteso sulla nostra banca dati. Non abbiamo tempo
da perdere, puoi continuare a perfezionare il design mentre grok traina, altrimenti
non chiudiamo entro le 2». Priorità: lancio effettivo, non altri cicli di design.
Ora circa18:35 Europe/Rome del5ottobre; obiettivo dell'utente entro02:00 locali.
Nessuna promessa temporale senza misure. Il mandato nuovo consente avviare una
prima RELEASE ESTESA dei dati già scientificamente utilizzabili mentre prosegue
il perfezionamento. Non dichiararla catalogo completo se restano voci aperte;
non omettere dati per comodità, tutte le voci/aggiunte mantengono percorso e motivi.

Stessa sessione, r1/r2/r3 immutabili; lavora solo agenti/grok_transfer_esteso_r4.
R3 fermata dal parent esclusivamente per consegnare questa nuova priorità, nessun
job tuo era stato lanciato. Riparti dai moduli r3 GIÀ SCRITTI (cloud_job.py,
split_rule.py,pins.py,estimator_core.py,observed_units.json), non ristudiare da zero.
CLAUDE.md e guide pertinenti restano applicabili. Nessun altro worker/subagente.

Consegna SUBITO primo pacchetto e ready_dispatch.json con comandi precisi, input
cloud già montabili e hash, fold/assi/mask verificati, pesi/ricetta t25 congelati:
parent esegue push, tu continui trainer e altre fonti, NON PUSH per evitare collisioni.
Prepara entro le prossime azioni un runtime che ESEGUA E SALVI il rifit lineare
esteso t25 sulla banca corrente: fonti originali più fonti aggiuntive ammesse,
non pilot rlead-bench-cube-r2. Derivazioni possono essere fase1 del medesimo
runtime, poi effettivo modello/effetti/manifest/esposizione, non solo checkers.
Se un prerequisito vero blocca, nome/file/azione esatta immediata. Non lasciare
la consegna solo '34record open' o training_ready=False. Risolvi lancio concreto.

Indice storage r10 SHA7134c13c741e04b1bb90b15f42afd2a50e653454aca17e49005edcad6f2e7fdf.
HIPSCI entrambe genome-wide+mirato19 complete; Norman banca/campioni publicv1,
iPSC statistica publicv3. K562 GWPS ancora parent RUNNING, non duplicarlo né
aspettarlo per avviare fonti chiuse. Parent avvia access/reader proof
davidmaisterx/vcc-reuse-runtime-norman-ipsc-r1, non è training; controlla receipt
access_runtime_r1/verified quando disponibile. Ultimo preflight16:24UTC1df11,
aggiunto1mx: preflight fresco prima lancio, altri slot disponibili.

Per la prima release estesa, inventario preciso di tutte le fonti attese vs
effettive/bloccate e ragione, separata dalla release completa finale D-053.
Includi tutte le fonti già ammesse tecnicamente compatibili; banche oggi già chiuse
per HepG2,Jurkat,RPE1,H1 train/val,KOLF,HCT/HEK,CD4,K562essential,SCP,Tian/HIPSCI.
QC Tian2019,assenza guide GSE249595,compound,UNASSIGNED,controlliHIPSCI non risolti
non vanno inventati: conservare e completare dopo con release distinta.
Split C/J e hidden globali/componenti prima di statistiche; asse gene_names.csv
hash25bfa66715e186bebabce7ac788bbcea47e2bf59ca70be1f8f3a06f2f0e47201,
count_sum pseudobulk BIO/donatore, controlli leciti. Non pubblicare effetti di
valutazione come modello ammesso. Campioni e popolazioni con lineage nel modello
che li usa; linear transfer e nuovo ibrido non confusi. Esecuzione CPU per rifit
lineare; GPU mx solo se CUDA effettivamente utilizzata. File modello/optimizer
quando applicabile, ricevute consumo/loss e checkpoint dopo resume.
Confronto t25 originale vs nuova banca, emissione t28 identica400cells*5semi
appaiati/split/preregistrazione, nessuna promozione dalla loss. Valutazione segue
fit; il design successivo non deve bloccare il primo fit corretto e verificabile.
CPU3account entro quote/accessi, nessun duplicato, nessun acquisto/Runpod/invioVCC/
cancellazione/pushGit/pubblicazione modelli. Stato con UTC misurata e job refs reali.
