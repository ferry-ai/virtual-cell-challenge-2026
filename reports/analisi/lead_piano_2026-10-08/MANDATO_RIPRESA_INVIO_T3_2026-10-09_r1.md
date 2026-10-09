# Ripresa del singolo invio T3 e prosecuzione AMMI

9 ottobre 2026, registrazione dopo lettura dell'orologio alle 19:24 Europe/Rome.
Lead Codex, sessione `01a11c05-970e-7af2-a07e-3860bd74acbd`.
Tipo: decisione operativa; nessun nuovo punteggio o beneficio dichiarato.

## Mandato umano corrente

Il proprietario scrive nella chat Lead:

> ok allora direi che se vuoi intanto possiamo pushare il transfer semplice su
> tutte le banche e linee (il refit di t36) e poi un modello più complesso AMMI
> oppure ESM2 ampliato oppure un nuovo modello che colga l'idea di embedding
> proteico ma che non sia perforza esm2 o qualcosa legato a pie. Vedi tu

Nel contesto della domanda precedente sull'invio al server, «pushare» autorizza
il singolo invio VCC del refit. Non è un'autorizzazione al push Git o alla
pubblicazione dei dataset. Questa istruzione riapre la consegna fermata nella
notte: lo stop storico resta documentato, ma non blocca più questa operazione.

## Assegnazione unica e riuso

**DATI-TRANSFER `01a11c34` è l'unico submitter**, dalla verifica del recupero al
confezionamento, upload e ricevuta server. Il Lead non avvia upload concorrenti.
Il messaggio è stato consegnato alla chat DATI; il percorso non deve fermarsi a
un rapporto di preparazione quando i passi successivi sono eseguibili.

Candidato: T3-CRISPRi-KO, invio pianificato t38, mai inviato secondo le ricevute
disponibili. Effetti SHA256
`b8c61f6da684f6c28107199469ac42ef030a4644176371b9723ae6e3f863f6a6`.
Riferimenti:

- [Candidato e pin](../../modelli/dati_transfer_2026-10-08_01a11c34/candidate_t3_r1.json).
- [Recupero conservato](../../modelli/dati_transfer_2026-10-08_01a11c34/t3_preserved_handoff_r1.json).
- [Copertura T3](../../modelli/dati_transfer_2026-10-08_01a11c34/coverage_t3_r1.json).
- [Previsione congelata](../../invii/prediction_t38_2026-10-09/prediction.json).
- [Testi](../../invii/trial_2026-10-09/submission_texts.md) e
  [precisazione KO](../../invii/trial_2026-10-09/submission_texts_addendum_DT5.md).

Riutilizzare `recovery_prediction.h5ad` se verifica integrale, dimensioni e
provenienza sono conformi. Il digest campionato dello stadio45 non è un hash
integrale. Nuova generazione solo se il recupero risulta impossibile o invalido,
con stessa ricetta e nuovi output. Nessun nuovo fit senza una differenza di input
ammissibili effettivamente verificata. t36 non viene reinviato; t37 resta chiuso.

L'invio resta esplorativo con la previsione già registrata (delta atteso zero,
soglia assoluta 0,005 contro t36); la mancata validazione T3 non diventa un PASS.
Nessun ritocco a effetti o regola dopo i risultati. Le 6.722 coppie solo KO
mantengono la stima normalizzata intera: il peso 0,25 non è un tetto all'effetto.

## Copertura da dichiarare

Il ledger distingue 12 tabelle CRISPRi con voto e 5 voti KO per studio/lignaggio,
derivati da 7 unità e 12 contesti. Non sono 17 linee indipendenti. Nessuna nuova
fonte perturbata ammessa è attestata dagli aggiornamenti successivi sugli NTC.

T3 è un refit ampliato sulle fonti compatibili ammesse, non tutto il catalogo:
assenza di overlap sul pannello, rappresentazione K562 senza duplicazione,
mapping incompleto, QC e controlli insufficienti, precedenti esclusioni Tian2019
e meccanismo CRISPRa sono nominati nel ledger. Nessuna inversione automatica
CRISPRa o chiusura D-053. I nuovi chunk fuori pannello restano per i consumatori
che possono usarli; conservare il pooling T3 non significa averli consumati.

## Esecuzione e continuità

CPU cloud per recupero/confezionamento; risorse e disco misurati prima del lavoro.
Non interrompere NTC o training AMMI, né occupare per packaging una GPU non usata.
Verifiche essenziali: hash e provenienza, assi, 360.000 cellule, conteggi/CSR,
contratto ufficiale, stadio48 e identità del payload. Conservare le ricevute.

Verificare quota VCC e upload pendenti, usare un solo uploader resiliente con
lock. Un errore di trasporto si riprende sulla stessa entry quando consentito;
non creare invii duplicati. Nessun acquisto, pubblicazione o bypass di quote.
Il consenso corrente copre i normali trasferimenti privati e calcoli necessari
alla consegna, senza domande ripetute per passi già autorizzati.

MODELLI-ESTERNI `01a11c35` continua AMMI secondo il
[mandato di chiusura](MANDATO_CHIUSURA_ESM2_AMMI_r1.md): quattro fit iniziali e
produzione coerente, GPU davidmaisterx. Prima scelta del Lead è concludere questo
esperimento contestuale. Altri embedding o PIE sono una successiva decisione
guidata dal suo limite misurato, non una nuova ricerca che ritardi i due percorsi.

## Precedenti

CP-0071: fallimento della consegna, non del fit. Si recupera e completa il
percorso senza ricominciare indiscriminatamente. S-010/S-011: più fonti non
garantisce beneficio; distinguere unità lette e voti effettivi. S-012: nessun
ritorno alla centratura T2 sfavorevole. S-009: stessa ricetta ed emissione del
candidato registrato, nessuna trasformazione nascosta nel confezionamento.

**Segnale precoce e arresto:** hash/provenienza/formato errati fermano quel
recupero e richiedono correzione, non l'upload di un candidato diverso. Un errore
operativo non si presenta come invio riuscito; la ricevuta server è necessaria.
