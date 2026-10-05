# Stime avviate, copertura finale ancora aperta — 5 ottobre

Cinque stime di effetti per fonte sono state accettate e osservate RUNNING:
Orion HCT116, Orion HEK293T, RPE1 e Jurkat su davideferrante11;
K562 essential su davidmaisterx. Ricevute individuali e pacchetti effettivi:
`sourcefits_launch_r1/`. Non sono un modello esteso completo.
Il preflight dei tre account è `preflight_sourcefits_r1.json`;
K562 GWPS originale era ancora RUNNING. Nessuna ingestion ripetuta.

Primo controllo dopo il lancio: Jurkat, RPE1 e K562 essential sono COMPLETE
e le ricevute scientifiche recuperate indicano `derived`,72split e6statistiche,
senza split bloccati per budget. HCT116 e HEK293T sono ancora RUNNING.
Prove: `sourcefits_status_r1/verification.json`, soli piccoli status/resource.
RAM libera misurata circa32,6–32,7GB,4CPU,20,94GBdisco per runtime.
Restano217/217/203righe con token non risolti rispettivamente Jurkat/RPE1/K562:
non sono esclusioni definitive o copertura completa. Grok deve risolvere identità
biologiche indipendentemente dall'asse di espressione prima del corpus finale.

Le sette fixture della consegna Grok r4 passano anche alla verifica del parent.
Sono adottati soltanto i cinque frammenti indipendenti elencati sopra.
Il mixer r4 non è adottato: carica soltanto la prima tabella BIO, e la media
CD4 separata per donatore/condizione differisce dall'originale stage98.
Lo stage originale stima insieme i donatori della stessa condizione e mescola
le condizioni con affidabilità e gamma0; il mix finale mantiene gamma1.

Grok continua nella stessa sessione in `agenti/grok_transfer_esteso_r5/`,
PID9888, per tre stime CD4 congiunte, caricamento di tutte le tabelle BIO,
mix esatto, esportazione e adattatori delle fonti ancora aperte.
La cartella r4 è congelata. Il parent esegue i push e segue banca/accessi.

## Non confondere disponibilità e uso

L'indice storage rimane [r10](cloud_catalog_r10/README.md): 395,75GB grezzi
e43unità storage, senza certificazione di corpus finale ammesso.
Il contratto congelato [training_coverage_r1/expected.json](training_coverage_r1/expected.json)
conserva TUTTE le unità, i riferimenti storici, i record del catalogo e i pin;
[launches_frozen.json](training_coverage_r1/launches_frozen.json) conserva i cinque
lanci senza vincolare ledger operativi modificabili. Non è una ricevuta d'uso.

Ogni unità/contesto ammesso dovrà comparire nella ricevuta del consumatore,
con asse, input hash, split, target/componenti, controlli e contributo al mix.
Le voci non risolte restano aperte, senza diventare esclusioni per comodità.
HIPSCI, SCP, Tian/Norman e le aggiunte al catalogo richiedono integrazione:
non dichiarare usate tutte le decine di linee dai soli cinque push o dal volume
grezzo archiviato. Nessun fallback al pilot rlead-bench-cube-r2.

Confronto richiesto: stesso transfer/emissione t28, sola banca variabile;
banco vecchio/nuovo400cellule×5semi appaiati. Nessun invio VCC.
