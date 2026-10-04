# Esito dei confronti controllati e della taratura del rumore

4 ottobre 2026, 17:55 CEST (ora letta con `date`), sessione `ba9b8bcb`. Via del proprietario in chat alle 14:53
(corsie diagnostiche) e, più tardi, «puoi anticipare tutto quello che vuoi». Kaggle CPU su due account
(`davideferrante11`: HepG2, H1, RPE1; `davidmaisterx`: Jurkat, K562); nessuna GPU. Letture con
[PROTOCOLLO_CONFRONTI.md](PROTOCOLLO_CONFRONTI.md) §4, §8 e §9, scritte prima delle uscite. Scala locale, linee già
lette: **non sono score VCC e non promuovono niente.**

Ricevute: [esito/read_diag_r1.json](esito/read_diag_r1.json), [esito/read_noise_r1.json](esito/read_noise_r1.json),
per linea `esito/diag_<linea>_r1/` e `esito/noise_<linea>_r1/`; lanci in `lancio_diag_r1.jsonl`; uscite complete in
`processed/diagnosi_t30_2026-10-04/`.

## 1. Validità

- Arresto registrato su HepG2 superato prima di lanciare le altre linee (`esito/arresto_hepg2_r1.json`).
- Cinque linee su cinque: parità `all_w0` vera; `all`, `all_wR`, `prod` riproducono con scarto 0 i membri archiviati
  di `transfer`, `ibrido_selettivo`, `transfer_prod_J`. Nella taratura il seme 0 alla numerosità del banco riproduce
  le corsie r1 su cinque linee.

## 2. Taratura del rumore (§9): va letta per prima

Guadagno appaiato g = media dei sei membri di `X_wR` − `X` allo stesso seme del generatore; media ± deviazione
standard su 5 semi. «32» è la numerosità del banco (metà delle cellule vere, mediana 32 per bersaglio), «400» quella
dell'invio.

| Linea | Archiviato (un seme) | `all`, 32 cellule | `all`, 400 cellule | `prod`, 32 | `prod`, 400 | PDS `all`, 400 |
|---|---|---|---|---|---|---|
| HepG2 | +0,063 | +0,064 ± 0,020 | **+0,031 ± 0,006** | +0,059 ± 0,019 | **+0,049 ± 0,003** | **−0,129 ± 0,005** |
| H1 | +0,006 | +0,002 ± 0,007 | +0,004 ± 0,004 | +0,003 ± 0,006 | +0,003 ± 0,006 | +0,020 ± 0,008 |
| RPE1 | +0,040 | +0,014 ± 0,018 | **+0,013 ± 0,003** | −0,003 ± 0,027 | −0,001 ± 0,010 | +0,061 ± 0,022 |
| Jurkat | +0,037 | +0,021 ± 0,017 | **+0,013 ± 0,006** | −0,002 ± 0,021 | **+0,020 ± 0,011** | +0,042 ± 0,009 |
| K562 | +0,074 | +0,023 ± 0,045 | +0,005 ± 0,015 | +0,029 ± 0,062 | **+0,026 ± 0,010** | +0,008 ± 0,017 |

In grassetto i guadagni «risolti» (|media| > 2 · ds / √5).

**Letture registrate:**
- «Il banco a un seme non risolve il guadagno» (ds a 32 cellule ≥ metà del guadagno archiviato): per `all` in 2 linee
  su 5 (H1, K562), quindi **non stabilito** con la soglia di 3; per `prod` in 4 su 5, **stabilito**.
- Guadagni risolti a 400 cellule: `all` 3 linee su 5, tutte positive (HepG2, RPE1, Jurkat); `prod` 3 su 5, tutte
  positive (HepG2, Jurkat, K562). A 32 cellule: 2 e 1.
- 400 cellule tolgono rumore: la deviazione standard del guadagno scende a 0,17–0,61 volte quella a 32 cellule
  (`all`) e a 0,15–0,93 (`prod`).

**Che cosa ne segue (misurato):**
- I guadagni di CP-0062 erano letture a un seme. Rifatti su 5 semi, già a 32 cellule sono più piccoli in quattro
  linee su cinque (RPE1 0,014 contro 0,040; Jurkat 0,021 contro 0,037; K562 0,023 contro 0,074). A 400 cellule la
  media delle cinque linee è **+0,013** per `all`, contro +0,044 archiviato.
- Il guadagno esiste, piccolo: è risolto e positivo in tre linee su cinque su ciascuna baseline, mai risolto negativo.
- **La perdita di PDS sul fold esportato è reale:** −0,129 ± 0,005 su HepG2 a 400 cellule (−0,102 ± 0,020 a 32). Sulle
  altre quattro linee il PDS sale o non si muove. La rete inviata col t30 è quella di HepG2.
- Su HepG2 il guadagno medio si dimezza passando da 32 a 400 cellule: una parte dei guadagni dei membri DE era un
  effetto della numerosità del banco.

## 3. Corsie diagnostiche (§4 e §8), un seme: verdetti registrati e loro tenuta

| Causa | Quantità (media su 5 linee) | Verdetto registrato | Tenuta alla luce del §2 |
|---|---|---|---|
| C1, baseline incoerente | D = −0,001; negativa in 4 linee, K562 +0,055 | **non distinta** | confermata dalla taratura: a 400 cellule il guadagno su `prod` è risolto in 3 linee, come su `all` |
| C2, parte comune | P (PDS con quota comune a 0,65) = −0,027; negativa in 4 linee; HepG2 −0,111 | **sostenuta** | un seme: fuori da HepG2 P sta entro una deviazione standard del PDS a 32 cellule; solida solo su HepG2 |
| C3, natura del guadagno | parte specifica S = +0,024, positiva in 5 linee; parte comune K = +0,007 | **guadagno specifico** | un seme; stesso ordine di grandezza del rumore del guadagno a 32 cellule |
| C4, procedura dell'invio | E = −0,025 (5 linee negative); F (PDS) = +0,016 | **sostenuta sul banco** (per E) | **non regge come causa:** vedi sotto |
| Ampiezza ×1,5 | guadagno +0,032 a ×1,5 contro +0,043 a ×1 | descrittivo | un seme |

**Sul braccio fedele (C4).** La correzione calcolata con la procedura dell'invio è quasi identica a quella del banco
sugli stessi bersagli: coseno medio per bersaglio 0,9998–1,0000 su quattro linee e 0,977 su RPE1, stessa quota comune
(HepG2 0,209 contro 0,207; Jurkat 0,125 e 0,125; K562 0,086 e 0,086; RPE1 0,137 contro 0,154), stessa RMS. Due effetti
quasi uguali hanno dato medie diverse di 0,008–0,060: è la grandezza del rumore misurato nel §2, non un effetto della
procedura. Il verdetto «sostenuta» esce dalla regola scritta, che non prevedeva questo caso; **la lettura corretta è
che la procedura dell'invio non cambia la correzione**, e che la quota comune alta dell'invio (0,62–0,69) viene dai
bersagli del pannello (transfer più debole, meno fonti), non dal modo di calcolare R. Questo separa i due fattori che
nel controllo locale del §7 cambiavano insieme.

## 4. Che cosa resta in piedi

**Misurato:**
1. Il banco D-056 a un seme e 32 cellule aveva un rumore sul guadagno di 0,007–0,045 per linea: dello stesso ordine
   dei guadagni su cui si è deciso l'invio.
2. La correzione D-056 dà un guadagno medio piccolo e positivo quando il rumore è ridotto, su entrambe le baseline.
3. Sul fold HepG2 la correzione toglie discriminazione in modo netto; sugli altri no.
4. La procedura di esportazione è fedele al banco; la differenza dell'invio sta nei bersagli.

**Ipotesi, non misurate:** che la perdita ufficiale del t30 venga dalla scelta del fold HepG2; che un'altra rete (per
esempio il fold Jurkat o RPE1, dove il PDS sale) avrebbe dato un esito diverso sul sito; che sui bersagli del pannello
la parte comune costi PDS come nel braccio a dose alzata.

## 5. Vincoli per il prossimo banco e il prossimo training

- **Numerosità e semi:** 400 cellule previste per bersaglio e almeno 5 semi del generatore; guadagno letto in forma
  appaiata, con media e deviazione standard; una differenza conta solo se risolta. Costo misurato: 54–99 minuti per
  linea su una sessione Kaggle CPU per 40 valutazioni.
- **Guardia sul PDS per linea e per fold**, letta su più semi: il fold che si esporta non può avere un PDS risolto
  negativo.
- **Scelta della rete da esportare** con una regola che guarda la discriminazione del fold sulla sua linea esclusa,
  non il numero di cellule di training.
- **Bersagli nel regime del pannello** (transfer debole, poche fonti) fra quelli valutati.
- Le soglie di CP-0062 (media ≥ 0,100, guadagno > 0 a un seme) non sono più utilizzabili così come sono.
