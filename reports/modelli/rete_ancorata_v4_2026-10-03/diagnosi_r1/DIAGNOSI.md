# Diagnosi tecnica dei training v3 r1 (H1, HepG2)

3 ottobre 2026, dalle 21:22 CEST (ora letta con `date`), Claude Code, sessione «Integrazione Codex e piano operativo»
(`5eacdf`). Fonti: le ricevute tecniche scaricate di nuovo con [fetch_r1_logs.py](fetch_r1_logs.py) in
[log_r1/](log_r1/) (senza le righe di valutazione: `fetch_receipt.json` ne conta 2 tolte per log), il codice v3 in
`reports/modelli/rete_ancorata_2026-10-03/`, due shard di contratto locali. **Nessun risultato scientifico dei due
training è stato aperto.** Questo documento non boccia la famiglia di modelli: descrive perché i training non
soddisfano le regole tecniche che si erano dati.

## 1. Le ricevute di Codex sono esatte

Gli sha256 di `coverage.json` riscaricati coincidono con quelli di
[training_receipts.json](../../../analisi/candidato_ibrido_2026-10-03/training_receipts.json)
(H1 `e081ec4a…`, HepG2 `b16c691b…`). Misurato:

| | H1 esclusa | HepG2 esclusa |
|---|---:|---:|
| Passi, epoche | 10.740, 0,714 | 23.810, 1,535 |
| Arresto | «time budget» al secondo 4.177 del processo | «time budget» al secondo 9.911 |
| Celle ammesse viste almeno una volta | 71,4% | 100% |
| Attesa dei batch (intera corsa) | 81,4% | 83,9% |
| Quota della loss di Neuron (attesa 1/7 = 14,3%) | 0,717% | 14,208% |
| `tian2021_crispri` (26.218 ammesse): estratte | 0 | 26.218 |
| Bilanciamento ±0,02 (regola v3) | non passa (6 gruppi su 7 fuori) | passa |
| Valutazione: riserva stimata contro durata reale | 6.323 s contro circa 1.066 s | 613 s contro circa 692 s |

La durata reale della valutazione è ricavata dagli orari: messaggio «trained» e `done.json` (H1 15:21:48 → 15:39:34
UTC; HepG2 16:57:30 → 17:09:02 UTC).

## 2. Perché H1 non ha letto i neuroni CRISPRi

**Meccanismo (codice):** ogni ruolo dei loader possiede una parte degli shard (`roles_of`) e li legge con
`cell_data.EpochSampler`: a ogni epoca un ordine casuale degli shard, un buffer di 4 shard alla volta. Le celle di uno
shard non ancora caricato non possono essere estratte. I pesi gerarchici danno a ogni gruppo 1/7 dell'obiettivo **solo
sull'epoca intera**; un training interrotto prima dipende dall'ordine in cui gli shard sono arrivati. I pesi non
recuperano celle mai lette.

**Simulazione (misurata, `test_balanced.H1Layout`):** sulle celle ammesse delle 31 chiavi della ricevuta H1, tagliate in
shard della taglia media del corpus, tre ruoli e buffer 4, il campionatore della v3 fermato a 0,714 epoche viola la
regola ±0,02 in più di 10 semi su 20; il campionatore bilanciato della v4 in nessuno e con scarti sotto 0,002. È il
meccanismo, non la ricostruzione degli shard reali.

**Ricostruzione sugli shard reali:** il kernel `rcell-v4-fast-a-r1` ripete il campionatore della v3 sullo stato del
pre-passo H1 fino al passo 10.740 e confronta le estrazioni per chiave con quelle della ricevuta. Esito nella sezione
datata in fondo, quando il kernel finisce.

## 3. Perché H1 si è fermato a 0,714 epoche

Il training finiva al budget (180 minuti) meno una riserva per la valutazione stimata da una sonda prima del training
(`evaluation priced` nel log). Nel run H1 la sonda ha letto 23 shard, 22 riga per riga, in 161,5 s per 1.787 cellule:
0,9 MB/s «prezzati». Estrapolati ai 6.756 MB prezzati della valutazione intera, hanno dato una riserva di 6.323 s; la
valutazione vera, con tre processi, è durata circa 1.066 s. Il training si è quindi fermato alle 15:21:47 UTC, circa
88 minuti prima del necessario. Con la stessa velocità media (2,6 passi/s) quei minuti valevano circa 13.700 passi in
più, cioè più di un'epoca intera: tutti gli shard sarebbero stati letti almeno una volta (interpretazione aritmetica,
non misura). In HepG2 la sonda ha letto uno shard intero e la stima era giusta.

## 4. Perché la GPU aspettava

**Calcolo (misurato nelle finestre del piano):** H1 4,976 passi/s con attesa 0,673, HepG2 3,39 passi/s con attesa
0,776: il calcolo dei due bracci costa 65,7 e 66,1 ms per passo da 256 cellule, cioè circa 15 passi/s se i dati non
mancassero. Fra un checkpoint e l'altro le corse hanno fatto 2,0–2,9 passi/s (520–760 cellule/s).

**Lettura e decompressione (misurato):** gli shard di contratto sono h5ad con `data` e `indices` compressi gzip livello
4 a blocchi di circa 8.200–8.400 valori (due shard locali di `processed/corpus_cellulare_2026-09-30/`). Nella sonda HepG2
la lettura e decompressione di uno shard intero da 177 MB ha impiegato 24,9 s nel processo principale (7,1 MB/s). Sul
portatile, con poca memoria libera, 10,4 MB in 0,94 s.

**Non il disco (misurato, interpretazione):** il controllo degli hash in parallelo ha letto 53 GB in circa 2.370 s
mentre il training leggeva; quando è finito (HepG2, verso le 14:52 UTC) il training non ha accelerato: 755 cellule/s
prima, 519–739 dopo. Il limite è quindi nel lavoro di CPU dei tre processi loader (decompressione dell'intero shard,
rimappatura, assemblaggio) su una macchina a 4 CPU virtuali, non nella velocità dello storage.

**Non ancora separato:** il peso di assemblaggio dei batch e del passaggio fra processi. La v4 lo misura in ogni
training (`coverage.json`, `timing`: secondi per batch di campionamento, lettura/decodifica e assemblaggio; calcolo
GPU sincronizzato ogni 50 passi), e i kernel dei gemelli misurano per ogni shard lettura grezza, decompressione h5py,
codifica e decodifica (`fast_manifest.json`, `profile`).

## 5. Verifica delle analisi di Codex che decidono la prossima azione

| Affermazione | Esito | Prova |
|---|---|---|
| Training H1/HepG2 conclusi, uscita 0, hash senza differenze | confermato | ricevute riscaricate |
| Neuron 0,717% in H1, `tian2021_crispri` mai letta, bilanciamento non passato | confermato | §1 |
| Attesa 81–84%, non attribuibile tutta al disco | confermato e precisato: decompressione, non storage | §4 |
| La riserva della valutazione può fermare prima delle due epoche | confermato e quantificato: 6.323 s contro circa 1.066 s | §3 |
| Lo streaming bilancia solo sull'epoca intera | confermato dal codice e da una simulazione; ricostruzione esatta in corso | §2 |
| Ancore della v3 e ricetta di produzione: insiemi di fonti diversi | confermato: le ancore usano H1, HepG2, RPE1, K562 (GWPS ed essenziali, senza VIPerturb), iPSC, Jurkat, Neuron; t22/t25 usa K562 GWPS, CD4 (tre stati), HCT116, HEK293T. In comune solo K562 GWPS | `anchors.py` v3; `p1_splits.py` |
| A549 «nel training ma non nella lista» delle ancore | precisato: il cubo del banco non ha tabelle A549, e le cellule A549 sono KO, che non ricevono ancore; aggiungerla alla lista non cambierebbe nulla | manifest del cubo r2 |
| Aggregati di CD4T, HCT116, HEK293T utilizzabili prima delle cellule | confermato: sono già tabelle del cubo r2 | manifest del cubo r2 |
| 8 gruppi nel pilot, 21 nella proposta | confermato come conteggio; la proposta resta da verificare (identità, alias, duplicati) | `audit.json` |
| Dipendenza delle ancore dai bersagli nascosti | confermato (sonda di Codex) e corretto nella v4 con un test di invarianza | `test_anchors_v4` |
| Probabilità di non vedere una popolazione all'1% con 64 cellule: 0,526 | aritmetica corretta (0,99^64), ipotesi di campionamento indipendente | `audit.json` |

## Ricostruzione e profilo dai kernel dei gemelli

Da compilare quando finiscono `rcell-v4-fast-{a,b,c}-r1` (sezione aggiunta con data e ora, il resto del documento non
cambia).
