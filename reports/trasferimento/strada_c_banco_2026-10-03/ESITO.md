# Strada C, corsa r1: esito secondo la regola registrata

3 ottobre 2026, ore 15:40 circa (ora del PC). Kernel `alfredo2003bit/strada-c-banco-r1`, versione 1:
- lanciato da Alfredo alle 14:01;
- finito COMPLETE alle 13:19:45 UTC (`kernel_done.json`);
- codice al commit 43db335, 358 shard letti, nessun errore di lettura.

Uscite piccole in [esito_r1/](esito_r1/). Le tabelle per bersaglio stanno nella cartella dati, con gli hash in
`esito_r1/manifest_output.json`. Gli effetti sull'asse ufficiale (`effetti_<gruppo>.npz`) sono rimasti su Kaggle.

**Tutti i numeri qui sono di un banco locale:** scala (u − b)/(r − b) sulle linee pubbliche, non punteggi VCC.

## 1. Esito secondo la regola originale

| Regola | Esito |
|---|---|
| Cancello tecnico | **passa su tutte e quattro le linee:** la replica batte la baseline in 6 membri su 6; pannelli di 53 (H1), 150, 150 e 150 bersagli |
| **Strada C** | **non passa.** Su H1 `same − cross` = −0,023 [−0,070; +0,023], n = 53: il limite basso non è sopra 0 |
| Bracci B: `alloc` | **non passa.** HepG2 −0,083 [−0,142; −0,025] (peggiora); Jurkat +0,006 [−0,041; +0,061] |
| Bracci B: `normrest` | **non passa.** HepG2 −0,029 [−0,077; +0,020]; Jurkat +0,027 [−0,003; +0,061] |

**Le altre due condizioni della strada C, lette per completezza:**
- `same − same_shuf` su H1: +0,128 [+0,078; +0,183];
- `same − cross` su KOLF: +0,090 [+0,018; +0,162].

**Ipotesi smentita, e solo questa.** Su H1 2025, le sorgenti di altre linee pluripotenti di questo corpus, mediate per
gruppo con la regola d'ampiezza registrata, non battono le sorgenti di tipo diverso nella media dei sei membri. Non è
smentito che il tipo cellulare conti in generale: su KOLF il segno è opposto, e c'è l'errore descritto al §2.

Secondo il protocollo la ricetta del t22 resta il riferimento, e questi bracci non si rigirano con altre costanti.

### Media dei sei membri per braccio (scala locale; replica = 1, baseline = 0)

| Braccio | H1 | KOLF | HepG2 | Jurkat |
|---|---|---|---|---|
| `null` | −0,062 | −0,003 | −0,063 | −0,031 |
| `k562` | 0,179 | 0,129 | 0,130 | **0,252** |
| `cross` | 0,167 | 0,157 | **0,249** | 0,189 |
| `same` | 0,145 | **0,247** | — | — |
| `all` | 0,160 | 0,212 | (= `cross`) | (= `cross`) |
| `same_shuf` / `cross_shuf` | 0,016 | 0,014 | −0,166 | −0,097 |
| `alloc` | 0,156 | 0,236 | 0,166 | 0,195 |
| `normrest` | 0,152 | 0,210 | 0,220 | 0,216 |
| `same_a2` | 0,185 | 0,233 | — | — |
| `cross_a2` | **0,200** | 0,189 | 0,236 | 0,174 |

- **La MSE scalata vale 0 in ogni braccio e su ogni linea:** coerente con la legge 1 + E/4786, come nei nostri invii.
- **I sei membri per braccio** sono in `esito_r1/scaled_local_<linea>.csv`.

### Confronti descrittivi (non decidono)

| Confronto | H1 | KOLF | HepG2 | Jurkat |
|---|---|---|---|---|
| `all − cross` | −0,007 | +0,055 [−0,002; +0,114] | — | — |
| `cross − k562` | −0,011 | +0,028 | **+0,119 [+0,052; +0,181]** | **−0,062 [−0,133; −0,005]** |
| `same_a2 − same` | **+0,041 [+0,018; +0,062]** | −0,014 | — | — |
| `cross_a2 − cross` | **+0,032 [+0,010; +0,056]** | +0,031 | −0,013 | −0,015 |

Il segnale del bersaglio è reale in ogni linea: ogni braccio batte il suo controllo a bersagli scambiati da +0,13 a
+0,42. Aggiungere linee aiuta su HepG2 e peggiora su Jurkat. Nessuna leva è costante sulle quattro linee.

## 2. Limiti che restringono la lettura

1. **Errore di attuazione, misurato dopo la corsa.**
   - `group_of` controllava «ipsc» prima di «neuron». Le chiavi `tian2019_neuron_day7` («iPSC-induced neuron day 7»)
     e `tian2021_crispri` («iPSC-induced neuron») sono finite nel gruppo `tian_ipsc`, quindi nel braccio `same` di
     H1 e KOLF, contro la tabella registrata, che li mette in `tian_neuron`.
   - Nel gruppo pluripotente di Tian restava una sola chiave vera, `tian2019_ipsc`, con 24 bersagli. Le due di
     neuroni ne portano 24 e 176.
   - **L'esito qui sopra è quello della corsa com'è stata eseguita,** non una misura pulita del protocollo. La
     correzione (test `Groups` in `test_banco.py`) è nel commit di questo esito; rigirare con il solo errore corretto è
     la corsa r2 proposta al §3.
2. **Che cosa vuol dire `same`:** altre linee dello stesso tipo, mai la stessa linea in un altro studio.
   - **Le esclusioni sono verificate in `bench_*.json`:**
     - per H1 escono `h1_vcc2025_train` e `h1_vcc2025_val`;
     - per KOLF escono le tre chiavi KOLF2.1J e le linee HipSci `kolf_2` e `kolf_3`.
   - **Altri derivati non sono esclusi,** perché nessuna regola li riconosce: le linee Tian derivano da altre iPSC e non
     coincidono con H1 né con KOLF.
3. **La linea primaria è la più debole.**
   - **H1 ha solo 53 bersagli ammessi:** il pannello chiede copertura in ogni braccio, e le sorgenti pluripotenti
     coprono pochi bersagli di H1. Contro i 150 delle altre linee, l'intervallo è più largo.
   - **H1 è molto più profondo:** la replica ha 1.827 geni significativi per bersaglio, contro 95–280 delle altre
     linee.
4. **La regola d'ampiezza pesa le chiavi, non i gruppi.**
   - La mediana delle norme singole è dominata dalle 19 linee HipSci, che hanno da 86 a 668 controlli ciascuna:
     effetti rumorosi, ristretti dallo z-shrink, quindi piccoli.
   - Su H1 `same` è stato quindi riscalato a 0,66, mentre `cross` è stato portato a 1,15.
   - Il guadagno di `same_a2` (+0,041) dice che `same` era sotto-dimensionato. Parte dello svantaggio su H1 può venire
     da qui (interpretazione).
5. **Sorgenti diverse per numerosità, studio e assay:**
   - le chiavi K562, RPE1, HepG2 e Jurkat misurano 7.700–9.000 geni (pannelli Replogle/Nadig);
   - le pluripotenti ne misurano 17.700–18.500.
   - Lo spazio dei geni su cui un braccio dà effetti cambia quindi fra bracci. Il banco non ha registrato la copertura
     dei geni per braccio, e qui non è ricostruita.
6. **Ripieghi:**
   - un bersaglio che nessun gruppo di un braccio confrontato copre esce dal pannello, quindi non viene mai previsto a
     zero e contato;
   - dentro un braccio, un gene che nessuna sorgente misura riceve effetto 0. È un ripiego per gene, e pesa di più nei
     bracci con sorgenti a 8.000 geni.
7. **Il bootstrap è sui bersagli di una linea:** misura l'incertezza dentro quella linea, non fra contesti. Una
   differenza media ≥ 0 su KOLF non dimostra non inferiorità.
8. **`same > same_shuf` controlla la specificità del bersaglio,** non l'utilità del tipo cellulare.
9. **Le linee del banco non sono D, E, F:** nessun esito qui dice qualcosa di garantito sul set finale.

## 3. Prossimo confronto complementare (proposta, da registrare prima)

**r2 = la stessa corsa con il solo errore del §2.1 corretto.**
- Stessi bracci, costanti, semi e regola: è la misura che il protocollo intendeva.
- **Bracci descrittivi in più, che non decidono:** uno per ciascun gruppo pluripotente da solo (`hipsci`, `kolf`,
  `h1`, `tian_ipsc`), per sapere da dove viene il +0,090 di KOLF.
- **La regola d'ampiezza per gruppi** sarebbe un cambio di disegno: va in un protocollo separato, non in r2.

Può girare nello stesso kernel che costruisce i dati della [rete sulle sorgenti](../../modelli/rete_sorgenti_2026-10-03/).

## 4. Input mancanti

- **Strada B vera** (ricetta t22, sorgenti K562, CD4, HCT116 e HEK293T):
  - cache r9 dello stadio 98 sul PC di Davide;
  - coordinate dei geni dello stadio 74;
  - il file HepG2 di Nadig: su questo PC è sul disco D:, non collegato; su Kaggle c'è come shard rlab.

  I nomi esatti richiesti dal loader dello stadio 100 non sono ancora elencati qui: lo farò leggendo `scripts/98_*` e
  `scripts/100_*`, separando cache del pannello attuale e universi per i bersagli finali.
- **Strada C r2:** nessun dato nuovo; serve un altro lancio Kaggle fatto da Alfredo.

## 5. Provenienza

- **Protocollo:** commit 9a5e20d, registrato alle 12:14 prima di ogni numero.
- **Codice della corsa:** commit 43db335. Dataset `alfredo2003bit/strada-c-code` con `code_manifest.json` (sha256 per
  file), verificato dal kernel prima di partire.
- **Scorer:** `cell_eval2` 0.16.0 dalla wheel, sha256 `c78428ba…`.
- **Uscite:** 95 file, elencati con byte e sha256 in `esito_r1/manifest_output.json`.
- **Chiavi usate,** con controlli, bersagli e geni misurati: `esito_r1/sorgenti.json`.
