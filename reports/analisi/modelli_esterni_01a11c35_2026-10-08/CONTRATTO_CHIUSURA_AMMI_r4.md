# Chiusura AMMI: quattro fit iniziali e produzione distinta

9 ottobre 2026. Applicazione del mandato umano verificato nella chat Lead:
messaggio `01a1213f-11e7-73a0-8712-a848c64f8c4d`, «portare a termine ESM2 e AMMI
il prima possibile». Sequenza del Lead: `../lead_piano_2026-10-08/MANDATO_CHIUSURA_ESM2_AMMI_r1.md`.
Decisioni prima dei risultati AMMI; nessun fit AMMI ancora eseguito.

## Sequenza eseguibile

`run_ammi_v4.py` ammette soltanto quattro fit iniziali: C-K562/C-iPSC × cells/none,
seme17. Sono quattro condizioni della stessa architettura. Le inferenze swapped
non addestrano modelli; mean e semi29/43 sono differiti. R2 conserva dati, split,
ancore, pesi, riferimento ESM2, loss, due epoche, batch32 e guardie. Un risultato
a un seme è preliminare e non dimostra stabilità del training.

Il wrapper salva un checkpoint a ogni epoca, prima della guardia, marcato non
ancora validato. Il checkpoint finale è ricaricato e le predizioni ricontrollate.
Una guardia fallita non rende valido il checkpoint: conserva materiale per la
diagnosi. Se fallisce soltanto swapped, il checkpoint e gli export nativi validi
restano utilizzabili; la ricevuta dello scambio fallito non richiede un rifit.

## Routing: applicazione del contratto già accettato

Fonti indipendenti: `PROTOCOLLO_v1.md` §2 nomina esplicitamente `k562 (BULK)`
come verità primaria, e `MESSAGGI.md` delle02:44, punto3, fissa K562 come
validation interna di C-iPSC. Il punto1 richiede coerenza dell'ancora, il punto6
risultati per lignaggio. V2 fissa disc95 con controllo a bersagli permutati.

Di conseguenza la tabella resta k562 BULK: nessuna nuova verità da scegliere.
Il confronto con NTC GWPS è fra studi, non tra campioni abbinati. Essential ha
zero target del pannello nella vista: mantiene NTC, export e guardie strutturali;
il suo disc95 è descrittivo, non una nuova verità primaria o replica. GWPS ha il
ruolo primario della lettura interna del pannello. Per CD4T ogni donatore Rest
è letto contro cd4_Rest, gli stimoli contro le rispettive tabelle secondarie.
La stessa verità riusata non crea repliche e non si fa una macro sui donatori.

Questa è un'applicazione dichiarata del contratto esistente, concordata con
DATI, non una nuova approvazione attribuita a VALIDAZIONE. Sostituisce lo stato
procedurale pending dei nostri r3/r4 quando il routing eseguibile verifica i
pin di queste fonti. Una contraddizione esplicita del proprietario del banco
resterebbe da risolvere; non sono stati letti risultati per scegliere il routing.

Prima del fit si verifica il controllo positivo dell'ancora annidata, con codice
metrics.py invariato. A ogni epoca restano le guardie strutturali; il delta
predizione–ancora è riportato senza selezione di epoca. Le decisioni successive
leggono cells–T0 e cells–none su entrambi i lignaggi. PASS tecnico non significa
beneficio: resta necessaria la regola comparativa congelata, inclusi i sei membri.

## Memoria e parti recuperate

DATI ha misurato237140candidati NTC nelle tre parti D4: la materializzazione
densa del r3 era inadatta. `ammi_controls_v4.py` verifica le parti, conserva CSR
su mmap e applica lo stesso bottom-hash64 per strato con SQLite. Ogni blocco è
normalizzato dal lettore DATI fissato per hash. `ammi_encoder_v4.py` somma le
rappresentazioni di tutte le cellule selezionate, ricomputando i blocchi nel
backward. Nessun nuovo campionamento; il batch del training resta32 righe.
La dimensione256 del blocco cellulare controlla memoria, non cambia gli esempi.

Una parte COMPLETE può essere riusata da un job ERROR dopo verifica indipendente
di piano, payload e codice produttore. Ogni parte conserva il proprio pin del
produttore; il pin del lettore di normalizzazione/merge è distinto. Le matrici
dense non sono salvate, e lo staging temporaneo non è nell'output Kaggle.
I contesti senza supervisione panel restano lacune nominate, non D-053 completo.

## Produzione

Il fit di produzione è distinto e predefinito: cells, seme17, stessa architettura
e iperparametri. Vista production ammessa con riferimenti/pesi ricalcolati dopo
le sue esclusioni dichiarate; nessuna verità di fold è chiamata indipendente
quando rientra nel training. Ogni ancora di training esclude il lignaggio della
riga; l'ancora di query è T0 piena con parità alla ricetta originale.
Le ancore annidate del pilot non sono rinominate come ancore di produzione.

Destinazioni: controlli ufficiali A/B/C, pannello300 attuale; nessuna lettura
di D/E/F o H1 test. Per le NTC di training il denominatore è obs.depth_native.
Per gli input ufficiali, che non lo forniscono, è la somma dell'intera riga X
fornita prima di allineamento: la profondità originale oltre l'asse disponibile
è ignota. Provenienza distinta per parte, stessa formula log1p(CP10k) e maschera.
L'estrattore verifica conteggi grezzi e strati ntc_id; non modifica il training.

La produzione può iniziare solo dopo lettura documentata dei due contrasti su
entrambi i fold e decisione esplicita sul fit tecnico. Non richiede un nuovo
consenso umano per l'azione già autorizzata. La guardia di produzione usa le
query e i loro soli controlli: valori finiti, ampiezza, quota comune e supporto;
nessuna verità destinazione è inventata o usata. Nessuna promozione automatica.

## Precedenti

S-006: residuo e quota comune; S-007: senza mean il primo risultato non isola
singole cellule contro semplice media; S-009: ancora e scala identiche fra fit
ed export; S-013: massa esplicita e risultati per lignaggio. Leakage, input non
verificati, checkpoint alterato o guardia nativa fallita fermano la relativa
corsa, senza clipping o rifit automatico per superare il controllo.
