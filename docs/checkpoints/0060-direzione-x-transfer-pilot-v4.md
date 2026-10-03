# CP-0060 — Direzione X + transfer, diagnosi dei training v3 e pilot v4 lanciato

- **Data:** 2026-10-03
- **Tipo:** cambio-di-strategia
- **Redatto da:** Claude Code, sessione 5eacdf (Integrazione Codex e piano operativo)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Il 3/10 sera il proprietario chiede di integrare le analisi di Codex, verificarne le conclusioni decisive, consolidare
un piano operativo unico e avviare il primo training tecnicamente valido della rete ispirata a X (basale dai controlli
\+ effetto trasferito + correzione appresa), con documenti che non perdano risultati e prossimi passi.

## 2. Cosa è stato fatto

- Ricevute tecniche dei training v3 r1 riscaricate senza le righe di valutazione
  ([fetch_r1_logs.py](../../reports/modelli/rete_ancorata_v4_2026-10-03/diagnosi_r1/fetch_r1_logs.py)); codice v3 letto;
  campionatore v3 rigiocato sullo stato reale del pre-passo H1 nel kernel `rcell-v4-fast-a-r1`.
- Versione 4 nella cartella [rete_ancorata_v4](../../reports/modelli/rete_ancorata_v4_2026-10-03/README.md): batch
  bilanciati (`balanced.py`), gemelli compatti degli shard (`fastshard.py`, `build_fast.py`), budget separati, ricevute
  di esposizione e copertura, ancore a medie del regime J con regole di fonti (`anchors.py`), corsie e regola, pacchetto
  di generazione; 36 test.
- Protocollo del pilot congelato al commit `ec580c6`, emendamento §10 al commit `953eb1e` dopo la revisione di Codex
  inoltrata dal proprietario, entrambi prima di ogni training v4.
- Kaggle CPU: gemelli dei 365 shard (`rcell-v4-fast-{a,b,c}-r1`), ancore (`rcell-v4-anchors-r1`), quattro parti Orion
  per HCT116 e HEK293T. Kaggle GPU: `rcell-v4-train-h1-r1` e `rcell-v4-train-hepg2-r1` dalle 23:06.
- Guide riscritte (PROGETTO §0, PIANI, AMBITI §4–5, schede R-LEAD, R-DATI, R-LAB); i testi precedenti nello
  [storico del consolidamento](../storico/consolidamento_2026-10-03/INDICE.md).

## 3. Cosa si è osservato

Misurato ([diagnosi](../../reports/modelli/rete_ancorata_v4_2026-10-03/diagnosi_r1/DIAGNOSI.md)):
- le ricevute di Codex sono esatte: H1 0,714 epoche, 71,4% delle celle viste, Neuron 0,717% della loss,
  `tian2021_crispri` (26.218 celle) mai estratta, attesa dei batch 81,4%; HepG2 1,535 epoche, bilanciamento passato;
- il campionatore v3 rigiocato riproduce le estrazioni per chiave della corsa H1 senza differenze; i due shard di
  `tian2021_crispri` non erano mai stati caricati all'arresto, come 81 dei 300 shard con celle di training;
- la riserva di valutazione di H1 era stimata 6.323 s contro circa 1.066 s reali; il training si è fermato circa
  88 minuti prima del necessario;
- il calcolo GPU costa circa 66 ms per passo in entrambe le corse; la decompressione h5py va a circa 27 MB/s per
  processo contro circa 66 MB/s della lettura grezza: il limite era la CPU, non lo storage;
- i gemelli dei 365 shard sono verificati per decodifica esatta e occupano 21,25 GB contro 53,32
  ([manifest](../../reports/modelli/rete_ancorata_v4_2026-10-03/esito/));
- ancore e ricetta di produzione usano fonti diverse: in comune solo K562 GWPS; il cubo ha già gli aggregati di CD4T,
  HCT116 e HEK293T; nel pilot r3, `transfer_all` supera `transfer_cells` in PDS su 3 linee su 3 ma sta sotto nella
  media locale a sei membri (−0,007, −0,035, −0,007), quindi l'effetto delle fonti in più non è scontato.

## 4. Interpretazione e incertezza

- **Interpretazione.** I training v3 non dicono nulla sulla bontà del candidato: non soddisfacevano le loro regole
  tecniche per difetti ora dimostrati. La v4 corregge esposizione, budget e ancore senza cambiare modello, corpus,
  generatore o metriche; i test mostrano gli stessi batch e parametri da shard e gemelli.
- **Incertezza.** Le velocità dei training v4 sono attese, non misurate, fino alle loro ricevute. Il pilot usa 8 gruppi
  e tre linee di sviluppo già lette; anche un esito positivo vale per il corpus del pilot. La regola confronta la rete
  con la propria ancora: la promozione richiede anche di battere la ricetta di produzione (§10.4).

## 5. Spiegazione semplice

La rete parte dalla previsione che otteniamo copiando la risposta dello stesso gene in altre cellule e impara solo come
correggerla. Nei primi tentativi il programma, fermato troppo presto, non aveva mai fatto vedere alla rete le cellule
dei neuroni: era un errore di distribuzione dei dati, non una prova che l'idea non funzioni. Ora ogni lotto di
addestramento contiene la sua parte di ogni tipo cellulare, e i dati si leggono abbastanza in fretta da non lasciare la
GPU ad aspettare.

## 6. Conseguenze

- D-054: la rete ancorata al transfer è il candidato operativo di R-LEAD, provato nel pilot v4; il transfer t22/t25
  resta il riferimento di produzione.
- Il binario dati (D-053) prosegue qualunque sia l'esito: prima le parti che completano HCT116 e HEK293T, poi CD4 e
  le altre voci del catalogo, con inventario riconciliato in R-DATI.
- Prossimo passo nella scheda R-LEAD: ricevute dei training, RPE1, generazione, corsie A e B, regola.

## 7. Cosa corregge

Nessun checkpoint. Precisa lo stato della rete ancorata v3 (registro, scheda R-023: superata dalla v4) e la chiusura di
R-DATI scritta prima di D-053. Non corregge misure o protocolli congelati.

## 8. Domanda di comprensione

Perché il training H1 della v3 non è una prova contro la rete ancorata? Perché non ha mai letto le cellule di un gruppo
che la sua regola richiedeva, per come erano ordinati gli shard: il difetto è nel percorso dei dati, ricostruito
esattamente, non nel modello.
