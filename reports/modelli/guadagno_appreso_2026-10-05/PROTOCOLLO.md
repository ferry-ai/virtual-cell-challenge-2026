# Guadagno appreso sul transfer `all`: alza la direzione del profilo aggregato?

5 ottobre 2026, Claude Code per Alfredo (sessione `42343bb9`). Mandato in chat: «scarica il necessario e procedi», dopo
la [revisione del 5/10](../../analisi/letteratura_strade_2026-10-05/README.md) (strada 1).

**Registrato prima di ogni numero:** nessun effetto del cubo è stato letto come esito prima del commit di questo file.
Le soglie non si spostano dopo i risultati.

## 1. Domanda

Un guadagno appreso g ≥ 0 per coppia bersaglio × gene, moltiplicato sul transfer `all` di Davide (g · T, segno
conservato), migliora la **direzione** del profilo aggregato della linea tenuta fuori **senza perdere
discriminazione**? La misura è nella geometria della MSE dello scorer.

Perché ora:
- la MSE scalata è 0 in tutti i nostri invii e nel banco v2;
- per uscire da zero serve un coseno aggregato di almeno 0,22 circa, e il nostro è 0,11–0,13
  ([margini_orizzonte](../../analisi/margini_orizzonte_2026-10-04/)).

**Precedente da non ripetere** ([CP-0057](../../../docs/checkpoints/0057-p4-dieci-gruppi-pseudobulk.md)): i guadagni
`m1` e `tm0` con il **termine comune** hanno fatto crollare il PDS (0,44 contro 0,95) e le chiamate (8–9 per bersaglio
contro 101). Il coseno sugli effetti premiava la calibrazione verso la risposta comune. Qui quindi:
- **niente termine comune:** l'uscita è solo g · T;
- **le caratteristiche sono per coppia** (accordo fra gruppi, SE, supporto), non solo per gene;
- **la norma è riportata a quella di T per bersaglio,** così l'ampiezza non entra nel confronto;
- **la discriminazione è una condizione della regola,** non una lettura secondaria.

## 2. Dati

- **Cubo:** `davideferrante11/rlead-bench-cube-r2`, scaricato intero il 5/10 con l'ok in chat. Contiene 34 tabelle,
  10 gruppi, 4.212 chiavi e 13.425 geni, con effetti raw, SE e shrunk in ln fold change e i profili basali dei
  controlli. Lo sha256 del manifest è registrato da ogni corsa.
- **Linee tenute fuori:** H1, HepG2, RPE1, Jurkat e K562, le cinque del banco v2. Il gruppo intero è tenuto fuori:
  tutte le sue tabelle e i suoi studi.
- **Regime C:**
  - le medie comuni delle tabelle sorgente sono `j_table_means(cube, held, forbidden=∅)`;
  - le chiavi J del prepasso di Davide non sono leggibili da noi e non si nascondono;
  - il bersaglio può essere misurato in altre linee, come nel pannello di gara.
- **Verità della linea L:** la media pesata n/(n+100) degli effetti **raw** delle tabelle di L, senza termine comune.
  La sua varianza è Σw²·SE²/(Σw)².
- **Bersagli valutati per L:**
  - chiavi utilizzabili di L con almeno 30 cellule nella somma delle sue tabelle;
  - supporto `all` da almeno un gruppo sorgente;
  - al massimo 400, scelte con hash stabile (`sha256(key + "|guadagno")`).

  Si riportano a parte il sottoinsieme del pannello A/B/C (strato `panel`) e quello `essential`.
- **Geni:** quelli del cubo con profilo basale finito in L. Il gene del bersaglio è escluso dalle misure e dalla
  perdita, e lasciato invariato.

## 3. Geometria dello scorer

- **Profilo aggregato.** Lo scorer confronta log1p dei conteggi normalizzati a 5·10⁴. Per un gene con CPM c nei
  controlli di L, x = 0,05·c, e un effetto ln f diventa Δ = log1p(x·eᶠ) − log1p(x).
- **Coseno con la verità (misura primaria)**, per bersaglio, nello spazio Δ:
  - verità Δ_y e previsione Δ_p;
  - il termine incrociato Δ_p·Δ_y non ha distorsione dal rumore della verità;
  - la norma della verità è corretta per il rumore: ‖Δ_y‖² − Σ(∂Δ/∂f)²·var. Se il valore corretto è ≤ 0 il bersaglio
    esce dalla misura, e quanti escono si riporta.

  Si riporta la media sui bersagli.
- **Discriminazione (indice del PDS):**
  - per ogni bersaglio i, si conta la quota di bersagli j ≠ i con distanza coseno d(Δ_p,i, Δ_y,j) minore di
    d(Δ_p,i, Δ_y,i);
  - indice = 1 − 2·quota, media sui bersagli: 1 è perfetto, 0 è il caso.
- **MSE normalizzata alla norma di T:**
  - ‖Δ_p − Δ_y‖² / ‖Δ_y‖²_corretta, mediana sui bersagli, con la previsione riportata alla norma di T × 1,576 per
    bersaglio (l'ampiezza della ricetta);
  - lettura secondaria, perché l'ampiezza finale si sceglie dopo.

## 4. Bracci

Tutti con T calcolato dalle stesse funzioni di Davide (`arms.group_mean` e `combine_groups`, copiate dal cubo:
`code__arms.py`, `code__fitting.py`). La parità con `transfer_for` si verifica su 20 chiavi prima di ogni lettura.

| Braccio | Che cosa è | Ruolo |
|---|---|---|
| `prod` | transfer con le sole tabelle di produzione (K562 gwps, CD4 ×3, HCT116, HEK293T) | baseline |
| `all` | transfer con tutte le tabelle | baseline e base del modello |
| `centrato` | `all` meno la sua media sui bersagli valutati della linea (la «componente comune tolta» del rango 154) | diagnostica, non candidato: dipende dal pannello |
| **`guadagno`** | g · T_all, con g = softplus(MLP(caratteristiche)), poi la norma riportata a quella di T_all per bersaglio | **candidato appreso** |

### Il modello `guadagno`

- **Caratteristiche per coppia (bersaglio k, gene j),** calcolate solo dalle sorgenti e dai controlli di L:
  1. |T|;
  2. il numero di gruppi che misurano la coppia;
  3. l'accordo |Σ_g T_g| / Σ_g |T_g|;
  4. log della deviazione fra gruppi / (|T| + 0,01);
  5. log(|T| / SE_T), con SE_T = √(Σ_g SE_g²) / n_g, dove SE_g è l'SE della media del gruppo g;
  6. log1p della CPM del gene nei controlli di L;
  7. la stessa cosa media fra le tabelle sorgente;
  8. la media |comune| del gene fra le tabelle sorgente;
  9. log della norma di T_k su tutti i geni (forza del bersaglio);
  10. log1p delle cellule del bersaglio nelle sorgenti.
- **Rete:** 10 → 32 → 32 → 1, ReLU, uscita softplus con bias iniziale tale che g = 1.
- **Perdita:** Σ w_j·(g·T − y)², con w_j = (∂Δ/∂f)² ai controlli della linea. È la MSE dello scorer al primo
  ordine. Sono escluse le coppie con T non finito e il gene bersaglio.
- **Addestramento, per ogni linea tenuta fuori L:**
  - righe dei gruppi h ≠ L con almeno 50 chiavi;
  - per una riga di h, T è calcolato **senza L e senza h**; y è il raw di h; i controlli sono quelli di h;
  - per ogni h, al massimo 300 chiavi (hash stabile) e 4.000 geni a caso per chiave (seme 0);
  - Adam, lr 1e-3, decadimento 1e-4, batch 65.536, 4 epoche, seme 0;
  - nessuna scelta di iperparametri: valori fissati qui, non provati.
- **Applicazione a L:** T senza L, caratteristiche dei controlli di L, poi la norma riportata a quella di T_all.

## 5. Regola

**Il `guadagno` passa al banco v2 (sei membri, 400 cellule, 5 semi) solo se, sulle cinque linee:**
- il coseno medio supera quello di `all` di almeno **+0,02** su almeno **4 linee su 5**;
- la media delle cinque differenze è almeno **+0,03**;
- l'indice di discriminazione non scende sotto quello di `all` di più di **0,01** su **nessuna** linea.

Gli intervalli si calcolano con bootstrap sui bersagli (2.000 ricampionamenti, seme 0); una linea conta come «sopra»
solo se il limite inferiore al 90% della differenza è sopra 0.

**Altrimenti:**
- il `guadagno` in questa forma si chiude;
- si annota che la direzione non si muove con caratteristiche per coppia, cioè che il limite è l'informazione e non
  il restringimento.

**Si riportano senza che decidano:**
- `all − prod`;
- `centrato − all`;
- le tre misure sui sottoinsiemi `panel` ed `essential`;
- la distribuzione di g.

## 6. Previsione (soggettiva, registrata ora)

| Grandezza | Previsione |
|---|---|
| Coseno di `all` | 0,10–0,25 per linea; K562 più alto (tre tabelle K562 nella verità, molte sorgenti affini) |
| `all − prod`, coseno | positivo su 4/5 linee |
| `guadagno − all`, coseno | da +0,00 a +0,04; fiducia 0,35 che la regola passi |
| `centrato − all` | coseno su, discriminazione giù |

## 7. Limiti

- Sono effetti di pseudobulk, non cellule: lo scorer vero resta il banco v2.
- La verità della linea è l'intera popolazione delle sue tabelle, non la metà A del banco v2.
- I 10 gruppi sono stati letti più volte da R-LEAD: è sviluppo, non conferma.
- Regime C senza le chiavi J di Davide.
- I geni sono i 13.425 del cubo, non i 18.533 dell'asse ufficiale.
