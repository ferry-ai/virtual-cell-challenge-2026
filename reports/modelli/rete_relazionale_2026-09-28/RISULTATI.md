# La rete relazionale: regola della prima tornata

28 settembre 2026. Scrive Claude (app desktop, sessione `f2abd9a6`); orari letti da `date`. Scheda
[R-V2](../../../docs/piani/modello-v2.md), ripresa dal proprietario alle 19:22. Disegno in [DISEGNO.md](DISEGNO.md).

Etichette: **misurato**, **interpretazione**, **ipotesi**, **proposta**. Nessun numero qui è un punteggio VCC.

## Regola della prima tornata, fissata alle 19:58 del 28/09 (prima di scrivere ed eseguire il codice sui dati veri)

**Quando parte.** Solo se la misura decisiva ([covariazione](../covariazione_2026-09-28/RISULTATI.md)) dice «sì»,
oppure «mappa sì, uso no» nella forma ridotta che quella regola prevede. Il codice si scrive e si autoverifica sui dati
sintetici nel frattempo. Le modifiche al codice dopo questa regola sono solo quelle necessarie a farlo girare sui dati
veri, dichiarate qui con l'ora, senza guardare risultati sui dati veri.

**Che cosa gira.**
- **Dati:** il dataset r2 (`processed/rete_contesti_r2`: 109.586 righe, 13.248 geni, 12 contesti CRISPRi; A549 fuori
  per modalità), invariato. Nessun farmaco e nessuna sorgente in più: le carte dei geni vengono dai soli profili
  visibili di ogni disegno.
- **Disegni** (famiglie intere fuori, come r1 e r2):
  - E1: `k562` (fuori anche `k562ess` e `viperturb`) e `cd4_Rest`;
  - E2 Orion: `orion_hct116` + `orion_hek293t`; le due verità contano anche come verità E1;
  - J: `k562` e `orion_hct116`, con `--regime J`;
  - E2 di laboratorio, descrittivo: `k562` + `viperturb` (stessa linea, laboratorio e chimica diversi).
- **Bersagli di prova:** per E1 ed E2 Orion i `test_targets.txt` della tornata r2 (`--test-targets`), così il
  confronto con r2 è appaiato; per J e per l'E2 di laboratorio quelli estratti da `train.py` con `--test-seed 0`.
- **Condizioni**, tutte con `train_rel.py` e lo stesso calendario (valutazione al passo 0 e poi ogni 25 passi,
  pazienza 12, riaddestramento come in r1):
  - `none`: la rete di r1 (`--arch r1`), argomenti di default;
  - `rel0`: la rete relazionale con le carte fisse (SVD dei profili visibili, K = 32, rotazione varimax);
  - `rel1`, esplorativa: le stesse carte più un residuo imparato; solo seme 0, solo E1 ed E2 Orion. Non decide nulla.
- **Semi:** 0, 1 e 2 per `none` e `rel0`. La regola si legge sulla media delle previsioni dei tre semi.

**Misure.**
- **Decide:** Δ = 0,36 ΔPDS_gen − 0,27 ΔnMAE_gen di `score_pred.py`, bootstrap appaiato al 95 %, su tutti i bersagli;
  per `rel0` − `none` lo stesso proxy con `score_pair.py`. Lo strato forte si riporta e da solo non decide.
- **Diagnostica, nello spazio degli effetti** (`compare.py`, `metrics.json`): skill, coseno, discriminazione fra i
  bersagli di prova, i bracci `tperm`, `norel` e `cardnb`, la curva di validazione. Non decide.

**Letture.** Le verità E1 sono quattro: K562, CD4 a riposo, HCT116 e HEK293T. Le ultime due vengono dallo stesso
laboratorio e dallo stesso disegno.
- **A. Contro la rete di r1:** `rel0` − `none`.
  - Passa se Δ è positivo su almeno 3 verità su 4, con l'intervallo sopra zero su almeno 2, di cui almeno una fuori da
    Orion, e nessun intervallo interamente sotto −0,002.
  - Vale solo se il segno di `rel0` − `none` (skill, `seeds.csv`) è lo stesso nei tre semi su almeno 3 verità su 4.
- **B. Candidato:** `rel0` − `excl`, stessa regola.
- **C. Uso del contesto:** `rel0` − cieca, stessa regola. In più, `rel0` − scambio positivo su almeno 3 verità su 4,
  con l'intervallo sopra zero su almeno una. Se passa la prima e non la seconda, il guadagno viene dalla forma, non dal
  contesto giusto.
- **D. E2 Orion:** la correlazione media di `rel0` ha l'intervallo sopra zero e supera il quantile 97,5 % delle
  permutazioni.
- **E. J:** `rel0` − ripiego (0,1 × partner STRING + testa cis). Passa se è positivo su entrambe le verità, con
  l'intervallo sopra zero su almeno una. Accanto, senza decidere: `cardnb` − ripiego (i vicini per carta, senza
  parametri imparati).

**Aspettative scritte prima (interpretazione).**
- In C il guadagno atteso è piccolo: il trasferimento resta a rango pieno e i termini nuovi partono da zero.
- J è dove la forma relazionale può servire di più.
- E2 probabilmente non passa: nessun modello pubblicato recupera l'interazione dai soli controlli.
- La discriminazione di `rel0` fra i bersagli di prova resta entro 0,01 da quella del suo braccio di trasferimento.
  La rete di r1 su r2, al seme 0, scende a 0,50–0,51 contro 0,55–0,64.

**Che cosa ne segue.**
- **A e B passano:** candidato per il banco sul pannello con lo scorer vero (azione 4 di R-REV), con una regola sua.
  Dopo [CP-0041](../../../docs/checkpoints/0041-proxy-contro-ufficiale.md) un «passa» sul proxy non basta per un invio:
  nessun invio senza lo scorer vero, una previsione registrata e il via del proprietario.
- **Passa A e non B:** migliore della rete di r1, non del trasferimento; nessun uso negli invii.
- **E passa:** candidato a sostituire il ripiego dello stadio 100 per i bersagli che nessuna sorgente misura, dopo una
  prova sul pannello (i 300 bersagli come J) con una regola sua.
- **C e D passano:** prima prova interna che una parte dell'interazione bersaglio × contesto si legge dai controlli
  attraverso i moduli; da replicare sulle linee HIPSCI.
- **Nulla passa:** esito negativo per `rel0` su r2. `rel1` non si legge come candidato.

**Falsificazione.** Ognuno di questi punti toglie alla rete il valore corrispondente:
1. `rel0` − `none` ≤ 0, o con l'intervallo che contiene zero, su almeno due verità E1;
2. `rel0` − `excl` ≤ 0 su almeno due verità: non vale la forma semplice;
3. il passo migliore è lo 0 in almeno 3 disegni su 5 al seme 0: niente di ciò che la rete impara si porta su una
   famiglia nuova;
4. `rel0` e `tperm` alla pari (intervallo della differenza di skill che contiene zero) su tutte le verità E1: il
   termine relazionale non dipende dal bersaglio;
5. l'E2 di laboratorio passa e l'E2 Orion no: il contesto che la rete legge è laboratorio e chimica, non la linea;
6. la discriminazione di `rel0` sta sotto quella del suo trasferimento di più di 0,01 su almeno 3 verità: il disegno
   non conserva la base;
7. segni diversi fra i tre semi.

**Limiti dichiarati prima.**
- Sono proxy su due membri su sei, contro verità pubbliche: non sono punteggi VCC, e il proxy non passa la taratura
  sulle differenze ufficiali (CP-0041).
- Quattro verità da tre laboratori: l'n efficace è vicino a 3.
- Il bootstrap è sui bersagli: non contiene la varianza fra semi né la correlazione fra bersagli dello stesso
  complesso.
- `none` e `rel0` non condividono l'ordine dei batch.
- La regola non cambia dopo un risultato: una variante nuova è una tornata nuova, con la sua regola.

## Modifiche dichiarate prima di girare sui dati veri (29/09, 00:50)

Emerse dall'autoverifica sintetica del codice (`train_rel.py --selftest`: 12 controlli su 12), senza nessuna corsa sui
dati veri. Il codice è di un sottoagente della sessione `f2abd9a6`.

1. **Validazione nei disegni J** (`--val-m as-train`, per tutte le condizioni dei due disegni J).
   - In J `train.py` toglie `m` alle righe di addestramento ma lo lascia a quelle di validazione. L'arresto anticipato
     sceglie allora sempre il punto di partenza calibrato.
   - Sul mondo relazionale sintetico: con la validazione di `train.py` il passo migliore è lo 0 e `rel0` ha skill
     0,004; con la validazione senza `m`, come le righe J che deve imitare, il passo migliore è il 350 e la skill 0,520.
   - La lettura E si fa con questa impostazione. La rete di r1 in J (lettura di r1) usava quella di `train.py`.
2. **Penalità dei parametri di contesto e della carta del bersaglio:** θ₀ 1e-5, θ_k 1e-4, w_self 1e-5, W_p 1e-5.
   - Resta il rapporto 1:10 fra θ₀ e θ_k scritto nel disegno.
   - I valori della mappa (1e-3 e 1e-2) sul mondo sintetico tenevano il guadagno di modulo vicino a zero: la linea
     tenuta fuori non batteva lo scambio (−0,0025) nemmeno dove il guadagno era piantato apposta. Con questi valori lo
     batte (+0,027 e +0,045, intervalli sopra zero) e l'E2 sintetica sale da 0,101 a 0,173.
   - Nel mondo nullo il guadagno sul cieco resta +0,0001 e 0,0000.

Niente altro cambia. Deviazioni minori dichiarate dal codice:
- i bracci in più stanno in `predrel_<ctx>.npz`;
- due mappe d'ampiezza, per `m` e `q`, come nella formula del disegno;
- SVD a blocchi con generatore fisso (`--rel-card-seed 0`);
- un passo migliore 0 riceve comunque un passo di riaddestramento, come in `train.py`.

## Esito: la tornata non parte (29/09)

La misura decisiva ([covariazione](../covariazione_2026-09-28/RISULTATI.md), [CP-0043](../../../docs/checkpoints/0043-misura-decisiva-relazioni.md))
dice «inconclusivo» per W1, con la lettura «uso» a no. La via delle relazioni non prevede la risposta a un knockdown,
né fra linee né nella stessa linea. Per la regola qui sopra la tornata parte solo con «sì» oppure con «mappa sì, uso
no»: **non parte**. I kernel sono costruiti e non lanciati. Il proprietario, alle 11:25, ha scelto di puntare sulla
prova generale e sul banco con lo scorer vero. Il codice (autoverifica 12 su 12) resta qui per chi volesse riaprire la
linea con una regola nuova.
