"""Preserve previous guides whole, then replace their operational entry points."""
import hashlib,json,shutil
from pathlib import Path
REPO=Path(__file__).resolve().parents[3]
HISTORY=REPO/'docs/storico/consolidamento_banca_2026-10-05'
STUDY='../../reports/modelli/percorso_riusabile_2026-10-05/'
REVIEW='../../reports/analisi/riconciliazione_banca_2026-10-05/'

def main():
    HISTORY.mkdir(exist_ok=False)
    files=['docs/piani/strategia-scientifica.md','docs/piani/dati-affidabilita.md',
           'docs/piani/piano-giorno-2026-09-30.md','docs/PROGETTO.md']
    originals={}
    for name in files:
        source=REPO/name;dest=HISTORY/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,dest)
        originals[name]={'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'copy':dest.relative_to(REPO).as_posix()}
    (HISTORY/'manifest.json').write_text(json.dumps(originals,indent=2),encoding='utf-8')
    (HISTORY/'INDICE.md').write_text('''# Guide prima del consolidamento banca, 5 ottobre 2026

Copie complete e identiche al byte, con hash nel [manifest](manifest.json).
Le istruzioni, assegnazioni e stati datati qui conservati sono storici.
I link interni delle copie conservano la posizione originale e non sono una coda operativa.
Per agire usare [R-LEAD corrente](../../piani/strategia-scientifica.md).

- [R-LEAD precedente](docs/piani/strategia-scientifica.md)
- [R-DATI precedente](docs/piani/dati-affidabilita.md)
- [R-LAB precedente](docs/piani/piano-giorno-2026-09-30.md)
- [PROGETTO precedente](docs/PROGETTO.md)
''',encoding='utf-8')
    lead=f'''# R-LEAD — archivio, banca riusabile e transfer esteso

- **Aggiornato:** 5 ottobre 2026, consolidamento delle prove; stato **in corso**.
- **Assegnazione:** Codex nella chat del subentro, sessione `01a107a9-9c9c-76c2-9161-258f22bd57b1`, workspace `vcc2026`. Grok r8 terminato; nessun worker attivo dichiarato. Non ricavare lanci o PID dalle consegne precedenti.
- **Mandato attuale:** ritrainare il transfer t28 (effetti t25, stessa emissione), cambiando la banca; tutte le linee/contesti idonei D-053. Nessun redesign dentro questo confronto. [Identità del modello]({STUDY}TRANSFER_IDENTICO_r1.md).
- **Autorizzazione:** [generazione e invio diretto]({STUDY}INVIO_DIRETTO_r1.md) senza attendere banco comparativo; supera i precedenti no-VCC. Upload privato dei tre controlli ufficiali resta bloccato dall'auto-review, in attesa di autorizzazione specifica. Nessun push Git implicito o servizio a pagamento.
- **Dati e selezione:** [ingresso unico riconciliato]({REVIEW}README.md); storage r10 e coverage congelata distinti dalla release del fit. Non usare `latest`, titoli, pilot o dataset omonimi come fallback.
- **Misurato:** [primo rifit parziale concluso]({STUDY}ESECUZIONE_r12.md), export utilizzabile e codice/versione verificati. 12 fonti registrate, 8 con target sul pannello; K562 GWPS manca, quindi non è ancora la vecchia banca completa più aggiunte. Non sono tutte le linee archiviate e non è dimostrato un miglioramento.
- **Prossimo passo:** completare/riusare K562 senza duplicare il producer `davideferrante11/vcc-derivatives-rlab-k562-gwps-r3`; nessuna ETA dalla sola etichetta RUNNING. Montare statistiche K562 con provenienza e stessa ricetta in una nuova release. Per la generazione predisposta: autorizzazione controlli, mount privato, correzioni del driver e hash runtime descritti in ESECUZIONE r12; poi un solo candidato VCC.
- **Percorso completo ancora aperto:** HIPSCI, Tian/Norman, SCP/KO/A549 e altre voci del catalogo richiedono ruoli/adapter/QC documentati. Non sono esclusioni definitive. Campioni cellulari persistenti non sono automaticamente consumati dal lineare. H1 test protetta; produzione non è validazione C/J.
- **Chiusura:** banca, campioni, release e consumo verificati per tutto il catalogo pertinente, training esteso, generazione e valutazione. Un export o invio riuscito non chiude da solo D-053.

## Riuso e verifiche

[Procedura del prossimo training]({STUDY}RIUSO_r1.md): riusare derivati compatibili; nuova fonte richiede solo i propri derivati e una nuova release globale. [Riconciliazione e limiti]({REVIEW}README.md), [R-DATI](dati-affidabilita.md), [R-LAB](piano-giorno-2026-09-30.md).

La [cronologia precedente completa](../storico/consolidamento_banca_2026-10-05/INDICE.md) conserva esiti, P0–P6 e ipotesi del filone neurale: non è la coda corrente. Design neurale e banco appaiato successivo non devono bloccare l'invio autorizzato. Regole scientifiche in [GENERALIZZAZIONE](../GENERALIZZAZIONE.md#21-copertura-integrale-vincolo-non-negoziabile), procedure di lancio/invio in [PROCEDURE](../PROCEDURE.md).
'''
    (REPO/'docs/piani/strategia-scientifica.md').write_text(lead,encoding='utf-8')
    data=f'''# R-DATI — identità, copertura e riuso della banca

- **Stato:** in corso; aggiornato il 5 ottobre 2026. Regia nella chat Codex del subentro; lanci e priorità solo in [R-LEAD](strategia-scientifica.md).
- **Ingresso:** [indice riconciliato]({REVIEW}README.md), con storage immutabile, copertura e selezione del rifit separati.
- **Verificato:** 43 unità storage corrispondono alle 43 attese; nessun fallback del pilot nei mount del mix. Byte/hash delle ricevute locali e alias di retry controllati. Questo non prova consumo integrale né assenza di sovrapposizione biologica.
- **Correzioni:** preservare byte Git dei file congelati; un ledger operativo era cresciuto dopo il vincolo hash. La versione originale è recuperata a hash identico e referenziata da una nuova coverage, senza alterare originale o ledger vivo.
- **Aperto:** ruolo/QC/adapter di tutte le aggiunte del catalogo, lineage cellulare e contributo effettivo per contesto. Poco overlap, dimensione e accesso tecnico non autorizzano esclusioni scientifiche.
- **Prossimo passo:** per ogni voce registrare versione, ruolo, BIO/donatore/stato/modalità, atteso/ammesso/usato e lacuna; il rifit corrente è parziale, K562 GWPS manca. Integrare nelle release successive le voci compatibili, senza reingestione dei derivati invariati.
- **Chiusura:** riconciliazione completa e ricevute runtime dell'uso, incluse le esclusioni di validazione [D-053](../GENERALIZZAZIONE.md#21-copertura-integrale-vincolo-non-negoziabile).

Le precedenti assegnazioni e cifre del pilot sono [storiche](../storico/consolidamento_banca_2026-10-05/INDICE.md), non comandi correnti.
'''
    (REPO/'docs/piani/dati-affidabilita.md').write_text(data,encoding='utf-8')
    lab=f'''# R-LAB — persistenza e riuso degli archivi

- **Stato:** in corso; aggiornato il 5 ottobre 2026. Regia dei job nella chat Codex del subentro; ordine e assegnazioni in [R-LEAD](strategia-scientifica.md).
- **Identità operative:** [indice riconciliato]({REVIEW}README.md), [manifest storage r10]({STUDY}cloud_catalog_r10/manifest.json). Account/versione/hash prevalgono su nome o data del dataset.
- **Conservato:** 395,75 GB grezzi perturbazionali censiti; CD4 tutte 12 unità, KOLF/HCT116/HEK293T, HIPSCI genome-wide e mirato19 e le chiusure ulteriori hanno prove nel manifest. Non contare questi GB come consumo del rifit.
- **Producer aperto all'ultimo controllo:** `davideferrante11/vcc-derivatives-rlab-k562-gwps-r3`. Verificare stato e avanzamento prima di agire; 50/50 riguarda soltanto il primo blocco. Nessun rilancio/kill o doppio job dalla sola attesa.
- **Prossimo passo:** riusare piccoli manifest e output già salvati; alla nuova chiusura K562 verificare le due unità, salvare ricevuta distinta, predisporre statistiche del transfer. Montaggio cloud preferito; copia locale solo per limite di accesso dimostrato.
- **Altre lacune:** Southard parziale su Drive, riuso shard e resume; fonti storiche restano nel catalogo con provenienza. Quattro Colab mai avviati sono sostituiti da Kaggle. Nessuna nuova ingestion Tahoe autorizzata dalla sola discussione.
- **Chiusura:** archivio completo verificato, derivati riusabili e accesso/hash provati nel consumer; il fit e la copertura scientifica si verificano separatamente in R-DATI/R-LEAD.

[Procedura di riuso]({STUDY}RIUSO_r1.md), [PROCEDURE §3](../PROCEDURE.md#3-job-su-colab-e-kaggle). Le code e sessioni precedenti sono [storiche](../storico/consolidamento_banca_2026-10-05/INDICE.md).
'''
    (REPO/'docs/piani/piano-giorno-2026-09-30.md').write_text(lab,encoding='utf-8')
    project=REPO/'docs/PROGETTO.md';old=project.read_text(encoding='utf-8')
    start=old.index('## 0.');end=old.index('## 1.',start)
    section='''## 0. Oggi — 5 ottobre 2026, banca persistente e primo rifit parziale concluso

**Riferimento ufficiale:** transfer t25 con emissione t28, massimo osservato **0,144845**, non conclusivo ([CP-0052](checkpoints/0052-t28-punteggio-ufficiale.md)). Il proprietario chiede lo stesso modello su banca ampliata; design neurale successivo distinto. Stato, assegnazioni e autorizzazioni correnti solo in [R-LEAD](piani/strategia-scientifica.md).

**Dati:** circa 395,75 GB grezzi conservati, 43 unità storage censite. [Ingresso unico riconciliato](../reports/analisi/riconciliazione_banca_2026-10-05/README.md) distingue archivio, banca, campioni, ammissione e consumo. Campioni persistenti non significano training cellulare: il transfer usa pseudobulk. Il vincolo [D-053](GENERALIZZAZIONE.md#21-copertura-integrale-vincolo-non-negoziabile) resta aperto per catalogo completo, adapter/QC e uso effettivo.

**Rifit:** [prima release estesa parziale conclusa](../reports/modelli/percorso_riusabile_2026-10-05/ESECUZIONE_r12.md), export utilizzabile, codice/versione verificati. 12 fonti registrate, 8 con bersagli sul pannello. **K562 GWPS del riferimento manca ancora:** non è la vecchia banca completa più nuovi dati. HIPSCI e altre fonti archiviate non sono ancora collegate. Nessun miglioramento dimostrato.

**Consegna:** generazione .vcc preparata, non avviata; il caricamento privato dei tre controlli ufficiali è bloccato dall'auto-review in attesa di autorizzazione specifica. L'invio esplorativo dopo generazione è già autorizzato senza attendere il banco comparativo. Nessun nuovo candidato inviato da questa campagna.

**Esiti precedenti:** l'ibrido D-056 aveva un guadagno locale più piccolo a rumore ridotto e un danno PDS sul fold esportato ([CP-0065](checkpoints/0065-d056-confronti-e-rumore-del-banco.md), [CP-0066](checkpoints/0066-banco-v2-t28-cinque-linee.md)); t30 non migliora t25 sul sito ([CP-0064](checkpoints/0064-t30-ibrido-selettivo-punteggio-ufficiale.md)). Il rifit corrente non è un nuovo ibrido. Tutti i punteggi stanno nell'[indice degli invii](../reports/invii/README.md).

H1 test resta protetta; gli split C/J escludono contesto e target/componenti prima delle statistiche. Produzione con hidden vuoto non è validazione. Il traguardo D/E/F resta distinto dall'invio esplorativo.

Le guide precedenti e il §0 completo sono conservati nello [storico del consolidamento banca](storico/consolidamento_banca_2026-10-05/INDICE.md). Nessun dato o evidenza eliminato.

'''
    project.write_text(old[:start]+section+old[end:],encoding='utf-8')

if __name__=='__main__':main()
