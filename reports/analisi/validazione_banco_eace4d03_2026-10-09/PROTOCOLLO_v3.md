# Contratto sperimentale della validazione — v3 (emendamento)

**Stato: congelato** con il commit che contiene questo testo, il 9 ottobre 2026 (orologio letto con `date`: 20:48
Europe/Rome all'inizio della stesura). Autore: VALIDAZIONE, Claude Code, sessione `eace4d03`, che riprende per
incarico del proprietario in chat il ruolo tenuto dalla sessione `8a8ca58a`. Tipo: protocollo; nessun risultato.

Sostituisce il [contratto v2](../validazione_indipendente_8a8ca58a_2026-10-08/PROTOCOLLO_v2.md) **solo nei punti
sotto**. v1 e v2 non sono riscritti. Fold, bracci, scorer, emissione, semi e **le soglie del §8 di v1 non cambiano**;
il manifest dei fold resta `manifest_fold_v2.json` (sha256 `a54ff614…ac3da`). I confronti già letti con v1 e v2 non
si rileggono con questo testo.

**Che cosa era già noto quando è stato scritto.**
- Letti: i punteggi ufficiali fino al t36; la chiusura ESM2 di MODELLI-ESTERNI nel livello A, compreso il suo
  `results.json` per intero (tutte le misure del contrasto fallback − T0, non solo `disc95`); l'audit del Lead; la
  precisazione di MODELLI-ESTERNI delle 20:31; le ricevute dei due fit AMMI `none`.
- Non esistevano: nessun conteggio di quante coppie riempite dal fallback entrano nelle misure; nessun numero a sei
  membri per ESM2 o AMMI; nessuna misura su fold nuovi; il punteggio del t38 (stato `scoring` alle 20:20, letto da
  DATI-TRANSFER).

## 1. Il difetto: bracci con copertura diversa sono misurati su supporti diversi

**Misurato sul codice** (`bench_core.measure`, sha256 `ffbc0dba…95ee`): ogni braccio è giudicato sulle **proprie**
coppie bersaglio-gene previste (`valid[a]`); una coppia che il braccio non prevede esce dal suo supporto. Per il
generatore e per lo scorer quella coppia è invece un effetto **zero**. Finché i bracci avevano la stessa copertura
(T0, T1, R1, P4, T2) la differenza non contava. Con un braccio che riempie i buchi di un altro conta:

- `r_spec`, `sign50`, `reach`, `nmae_conf` e `mse_ratio` del contrasto mescolano l'accuratezza sulle coppie nuove
  con il cambio di denominatore: T0 non paga le coppie che lascia a zero, il braccio che le riempie sì;
- `disc95` usa le colonne valide per almeno il 95 % dei bersagli **nei bracci del manifest**: una coppia che T0 non
  prevede entra nel rango solo se sta in una colonna che T0 prevede per quasi tutti gli altri bersagli.

Non è un errore di calcolo: è una misura definita per un caso che ora non basta. Nel regime J il banco usa già
l'altra convenzione (una verità per tutti i bracci, la coppia non prevista conta zero).

**Aggiunta (non sostituzione).** Per ogni contrasto fra bracci con maschere diverse si riportano, accanto alle
misure del §6 di v1 così come sono:

1. **la vista del generatore**: supporto definito dalla sola verità (coppie con verità valida, colonne dei geni
   bersaglio escluse come sempre), identico per tutti i bracci; una coppia non prevista vale zero. Stesse sei
   misure, più `disc95g`: il rango sulle colonne valide nella verità per almeno il 95 % dei bersagli;
2. **la copertura, separata dall'accuratezza**: per braccio e fold, coppie previste, coppie giudicabili (verità
   valida) e coppie nel rango; per il contrasto, coppie cambiate, quante sono giudicabili, quante entrano nel rango
   congelato, e quale quota delle entrate del rango rappresentano. Un gene non misurato dalla verità non è uno zero
   biologico: resta fuori da ogni conteggio di accuratezza e si conta a parte.

**Regola.** Il §8 non cambia: la lettera (c) e il segnale d'arresto si leggono ancora su `disc95` del supporto
congelato. La vista del generatore è **diagnostica**: può spiegare un risultato o chiedere una diagnosi prima del
livello B; non promuove e non boccia. Se meno della metà delle coppie cambiate giudicabili entra nel rango
congelato, accanto a `disc95` si scrive «la misura non copre il cambiamento» e si legge anche `disc95g`.
`disc95g` vale su un fold solo se lì il controllo a bersagli permutati (T0 contro T0 a righe scambiate, stessa
vista) è risolto positivo.

## 2. Diagnosi del fallback ESM2, senza nuovo training

Sui file già esistenti: effetti dei fold dei bracci del manifest (livello A), `E2`, `E2g` e il fallback consegnato
da MODELLI-ESTERNI (`esm2_closure_conversion_r1.json`), tabella di verità del fold. Ogni file si verifica per sha256
contro la sua ricevuta prima di leggerlo. Sequenza:

1. **Parità.** `disc95` medio di T0 e del fallback, ricalcolato, deve coincidere entro 1e-6 con il `results.json`
   della corsa di chiusura. Altrimenti ci si ferma: i conteggi non descriverebbero la misura pubblicata.
2. **Adattatore.** Il fallback deve essere T0 bit per bit dove T0 prevede, e 1,576 × `E2` dove riempie (scarto
   assoluto massimo 1e-6). Altrimenti segnalazione a MODELLI-ESTERNI, e ci si ferma.
3. **Conteggi di supporto** come al §1.
4. **Quattro bracci con maschera e scala identiche** sulle coppie riempite: `zero` (T0 visto dal generatore), `esm2`
   (il fallback consegnato), `generico` (stesso riempimento con `E2g` × 1,576), `scambiato` (stesso riempimento con
   `E2` di un altro bersaglio × 1,576, permutazione senza punti fissi fra i bersagli che `E2` prevede, seme
   20261008). Misure nella vista del generatore sul fold intero, e sul solo supporto riempito (errore quadratico e
   assoluto rapportati alla previsione zero, accordo di segno sui geni confidenti), per bersaglio, con bootstrap
   appaiato sui bersagli (10.000, seme 20261008).

**Parole fissate ora, prima dei numeri:**

| Affermazione | Si scrive solo se |
|---|---|
| «il fallback riduce l'errore» | `mse_ratio` di `esm2` − `zero` risolto negativo nella vista del generatore, su quel fold |
| «il guadagno è specifico del bersaglio» | la stessa misura, `esm2` − `scambiato`, risolta a favore di `esm2` |
| «basta la parte generica» | `generico` − `zero` risolto a favore e `esm2` − `generico` non risolto |
| «il fallback discrimina meglio i bersagli» | `disc95g` di `esm2` − `zero` risolto positivo, con il suo controllo superato |

Sono diagnosi aggiuntive: **non sono soglie nuove e non si applicano a ritroso**. L'esito del §8 per il fallback
resta INCONCLUDENTE finché manca il livello B; per ESM2 nativo resta la regressione risolta di `disc95` su C-K562.
«Non adottarlo adesso» è una decisione di priorità del Lead; «non può aiutare» sarebbe una conclusione scientifica,
che queste diagnosi da sole non sostengono né escludono.

## 3. Estensione del banco

I sei fold C del manifest v2 restano com'è scritto. Si aggiunge, senza riassegnare nulla:

1. **Livello B su altri lignaggi del pannello**, quando esistono le cellule vere: C-HCT116, C-HEK293 e C-CD4T, con
   la stessa regola dei due fold esistenti (bersagli del pannello su cui vota la tabella di verità del fold, fino a
   128 cellule per bersaglio, 2.048 controlli, seme 2026, estrazione che non legge alcun effetto). Per CD4T la
   verità primaria è la condizione `Rest` con i quattro donatori insieme, come nella tabella; `Stim8hr` e `Stim48hr`
   sono **strati** riportati a parte. Donatori, condizioni e librerie della stessa linea non sono mai fold né
   lignaggi in più.
2. **C-iPSC con la libreria pan-genome** (282 bersagli) come verità a sei membri quando le sue cellule sono
   estratte; la libreria `strong` (55) resta la seconda lettura dello stesso lignaggio.
3. **Macro del livello B a peso uguale per lignaggio**, non per fold, strato o libreria. Un candidato nuovo si legge
   su tutti i lignaggi di livello B disponibili quando il suo confronto è congelato, e dichiara quali mancano.
4. **Letture descrittive, mai nella macro e mai nel §8:** un secondo studio dello stesso lignaggio (`xu2023` per
   HEK293, 5 bersagli), lignaggi con pochi bersagli del pannello (neuroni di Tian 2021, 6), e le verità **KO**
   (A549 21 bersagli, melanoma 5, Calu-3 6) in una tabella a parte. CRISPRi, KO e CRISPRa restano separati. Una
   verità KO si collega alla valutazione CRISPRi solo dopo aver misurato, in un lignaggio che ha entrambe le
   modalità sugli stessi bersagli (K562: Dixit contro Replogle; CD4T: Shifrut contro Marson), che l'accordo
   specifico KO–CRISPRi è risolto positivo, riportato accanto all'accordo CRISPRi–CRISPRi fra due studi dello stesso
   lignaggio.
5. **Registro di esposizione.** Per ogni lignaggio: da quando è fonte di una ricetta, in quali statistiche,
   calibrazioni, selezioni e decisioni è entrato, quali checkpoint lo hanno visto. Un checkpoint si legge come
   regime C su un lignaggio solo se le risposte perturbate di quel lignaggio (tutti gli studi e gli stimoli) non
   sono entrate nel suo training né nella scelta dei suoi iperparametri; altrimenti la lettura è T o «visto», e lo
   si scrive. **Tutti i lignaggi oggi in banca sono sviluppo**: nessuno è conferma indipendente. H1 test e le
   riserve protette restano chiuse.

Pannello e ricerca restano distinti: i fold del pannello valutano la **consegna**; una fonte senza bersagli del
pannello può valutare la capacità di generalizzare a bersagli nuovi (T, J, bersagli fuori pannello) ma non dice
nulla, da sola, sul file che si invia.

## 4. Registro previsione → punteggio

**Unità:** una previsione scritta in un file prima dell'invio a cui si riferisce (`reports/invii/prediction_*/`).
Quattro tipi, tenuti distinti: banda del punteggio; banda del delta contro un riferimento; previsione puntuale di
un banco (delta o punteggio, con i membri e l'incertezza se registrati); attese per membro. **Una previsione
assente resta assente**: il registro la riporta come tale e non la ricostruisce.

Il registro è scritto da un comando ([invii/registro.py](invii/registro.py)) che legge i file committati e lo stato
ufficiale salvato; nessun numero è ricopiato a mano. Le previsioni puntuali di banco stanno in un elenco con
percorso e chiave del file da cui vengono, e il comando rilegge il numero dalla fonte.

**Tre errori, per ogni previsione con un esito ufficiale:**

| Errore | Come si legge |
|---|---|
| Direzione | segno del delta previsto contro segno del delta ufficiale, solo dove la previsione ha un segno. Un delta ufficiale in valore assoluto sotto 0,005 è «indistinto» e non conta né giusto né sbagliato (soglia operativa della procedura degli invii, non un intervallo) |
| Ampiezza | delta ufficiale meno delta previsto, e loro rapporto, per la media e per ogni membro dove il banco aveva un membro |
| Incertezza | l'esito sta nella banda o nell'intervallo registrato? Per una previsione di banco con più semi: l'esito sta entro due deviazioni standard dei semi? |

Ogni spiegazione di un errore porta un'etichetta: **verificata** (un test la isola, citato), **ipotizzata**,
**ignota**. I sei membri ufficiali si leggono dallo stato pubblicato, con pannello, versione delle ancore e versione
dello scorer locale usato dal banco; non si ricostruisce un membro mancante.

**Versioni del banco.** Ogni previsione porta la versione del banco che l'ha prodotta. Una correzione del banco ha
una causa verificabile e una versione nuova; vecchia e nuova versione si confrontano solo (a) su invii successivi al
congelamento della nuova, oppure (b) su fold o lignaggi che non hanno contribuito a scegliere la correzione,
dichiarati prima. Rifare a posteriori la previsione di un invio già valutato si chiama **postdizione**, si riporta a
parte e non entra in nessuna taratura.

**Taratura numerica.** Un fattore di conversione fra delta di banco e delta ufficiale si stima solo con almeno otto
previsioni puntuali con segno della stessa versione del banco e della stessa famiglia di candidati: con meno,
nemmeno un accordo perfetto dei segni esclude il caso all'1 % (test dei segni a due code). Finché non ci sono, il
registro scrive «taratura non sostenuta» e il banco consegna una **previsione prudente**: il verso atteso per
membro (o «indistinto»), e una banda del delta non più stretta di ±0,005. Pesi dei membri e soglie non si adattano
ai punteggi disponibili.

## 5. Precedenti

- **S-009** (banco diverso dall'esportazione; media che copre il PDS; guardie non applicate all'inferenza): il §1
  nasce dallo stesso tipo di scarto, qui fra il supporto della misura e quello che il generatore emette; la vista
  del generatore lo chiude nel livello A, il livello B resta il giudice.
- **S-013** (ridge ESM2 senza contesto): le diagnosi del §2 separano «riempie» da «riempie bene» e da «riempie in
  modo specifico», che il solo `disc95` non distingue; si legge per lignaggio, come chiesto allora.
- **S-010**, **S-011** (più fonti non è monotono; tabelle lette non sono voti): la copertura si riporta sempre
  separata dall'accuratezza, e i lignaggi nuovi di livello B servono a provare su dati non usati per formularla
  l'ipotesi sulla composizione delle fonti.
- **S-006**, **S-001**, **S-002** (parte comune scambiata per segnale; reti senza discriminazione): i bracci
  `generico` e `scambiato` con maschere identiche sono lo stesso controllo, applicato al riempimento.
- ERRORI, «Errori di metodo»: misura di guardia su un supporto che può svuotarsi (v2 §1); indice locale letto come
  guadagno in gara (CP-0052); candidato inviato diverso dal braccio del banco (CP-0064); differenze sotto il rumore
  (CP-0065); riserva già valutata chiamata indipendente (CP-0050).

**Segnale precoce e arresto:** parità o controllo dell'adattatore falliti fermano la diagnosi del §2 prima di ogni
lettura. Una misura della vista del generatore si legge su un fold solo dove il suo controllo a bersagli permutati
è risolto positivo. Un fold nuovo di livello B il cui controllo (T0 contro T0 a righe scambiate) non abbassa il PDS
locale è invalido e non entra nella macro. Nel registro degli invii, una previsione il cui file non precede
l'invio è marcata «non preregistrata» ed esce da ogni conteggio di taratura.
