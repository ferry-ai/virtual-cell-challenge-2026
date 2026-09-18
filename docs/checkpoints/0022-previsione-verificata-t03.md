# CP-0022 — La previsione registrata contro il punteggio reale del t03

- **Data:** 2026-09-17
- **Tipo:** osservazione
- **Redatto da:** agente
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Il banco locale, il punto di calibrazione del `t02` e le ancore risolte in
[CP-0021](0021-ancore-ufficiali-e-troppe-chiamate.md) permettono di **prevedere** il
punteggio ufficiale di un file prima di sottometterlo? E la lettura rimasta aperta in
CP-0021 — troppe chiamate o troppo poche — quale delle due era?

## 2. Cosa è stato fatto

1. Previsione registrata **prima** della sottomissione, con `scripts/84_predict_official.py`:
   grezzi del braccio `transfer_a2.0+cismeas_a1.0+cis_a1.0` del banco h002, ratio per membro
   dal punto di calibrazione `t02`, conversione con le ancore →
   `reports/prediction_t03_2026-09-17/prediction.json`, media attesa **+0,0338**.
2. Sottomissione del `t03` (`entry_id` `0TbVAwhVTj6UYpaU2v9d`), output verbatim in
   `reports/trial_2026-09-17/submit_0TbVAwhVTj6UYpaU2v9d.json` e
   `status_0TbVAwhVTj6UYpaU2v9d.json`.
3. Ri-soluzione delle ancore con tre punti, `reports/anchors_2026-09-17/three_points/`.

## 3. Cosa si è osservato

**Misurato — la previsione contro il risultato.** `t03` ha ottenuto media **+0,019692**,
rango 576.

| membro | grezzo previsto | grezzo reale | errore |
|---|---|---|---|
| `de_wilcoxon_direction_fidelity_yield_raw` | 0,4273 | 0,4230 | −1,0% |
| `pds_cosine` | 0,6678 | 0,6486 | −2,9% |
| `de_wilcoxon_lfc_nmae` | 0,9630 | 0,9741 | +1,1% |
| `de_wilcoxon_direction_reach_raw` | 0,1694 | 0,1448 | −14,5% |
| `de_wilcoxon_sig_jaccard` | 0,0134 | 0,0218 | +63,2% |
| `expr_mse_unbiased_capped_norm` | 2,0802 | 2,4123 | +16,0% (tosato a 0 in entrambi) |
| **media scalata** | **+0,0338** | **+0,0197** | **−0,0141** |

**Misurato — le ancore fuori campione.** Le ancore erano state risolte sui due punti
precedenti (trial-01 e `t02`); il `t03` non è stato usato per calcolarle. Applicate ai suoi
grezzi danno +0,3274 / +0,0446 / −0,2999 / +0,0739 / −0,0235 contro i +0,3254 / +0,0432 /
−0,3008 / +0,0738 / −0,0234 pubblicati dal server: scarto massimo **0,002**.

**Misurato — più chiamate, più fedeltà, sui contesti ufficiali.** Il `t02` e il `t03`
differiscono per l'ampiezza di trasferimento (1,0 contro 2,0), che sul banco corrisponde a
126,6 e 523,7 geni dichiarati per bersaglio. La fedeltà grezza ufficiale passa da **0,2534
a 0,4230**, e `reach` da 0,1382 a 0,1448.

**Misurato — dove restiamo indietro.** Rispetto a trial-01 (media +0,045929, rango 446), il
`t03` perde su `pds_cosine` (0,6486 contro 0,6870) e su `de_wilcoxon_sig_jaccard` (0,0218
contro 0,0291), e guadagna su fedeltà, `reach` e `nmae`. La fedeltà resta **sotto la base
ufficiale di 0,5123**: nessuna delle tre sottomissioni la raggiunge.

## 4. Interpretazione e incertezza

**Interpretazione.** Il banco più la calibrazione più le ancore sono uno **strumento
predittivo**: sui due membri che pesano di più ha sbagliato dell'1–3%, e sulla media di
0,014. Da qui in avanti una configurazione si può valutare senza spendere una sottomissione.

**Incertezza, e non è piccola.** La calibrazione è un rapporto per membro da **un solo
punto**, e sui due membri piccoli ha sbagliato molto (`jaccard` +63%, `reach` −14,5%). Il
`t03` era anche vicino al punto di calibrazione nello spazio delle configurazioni: cambia
solo l'ampiezza. Non è dimostrato che lo strumento regga su un modello di famiglia diversa,
ed è lì che andrà rimisurato prima di fidarsene.

**Interpretazione.** La lettura di CP-0021 che sopravvive è la seconda: sui contesti
ufficiali stessi, chiamare **più** geni alza la fedeltà. Il limite `--max-calls` introdotto
quella sera va nella direzione opposta ai dati, e i file `t04` e `t05` che ne sono nati non
hanno un caso a favore.

**Quello che lo strumento non dice.** Nessuna delle tre sottomissioni raggiunge la base
ufficiale sulla fedeltà (0,5123), cioè il livello di chi azzecca le direzioni quanto il
caso. Il guadagno del `t03` viene dall'avvicinarsi a quella soglia, non dal superarla. Lo
strumento misura dove siamo; non produce il segnale che manca.

## 5. Spiegazione semplice

Abbiamo scritto su un foglio, prima di spedire, il voto che ci aspettavamo: 0,034. Il voto
è arrivato: 0,020. Sulle due materie che pesano di più avevamo previsto giusto all'1–3%.
Serve a questo: d'ora in poi possiamo dare i compiti a noi stessi e sapere che voto
prenderebbero, senza consumare una delle due consegne al giorno.

Resta il fatto che il voto è ancora sotto quello di quattro giorni fa, e che sulla materia
principale — indovinare se un gene sale o scende — nessuno dei nostri tre tentativi arriva
al livello di chi tira a caso.

## 6. Conseguenze

- Si itera sul banco e si prevede con lo stadio 84; si sottomette solo ciò che la previsione
  giustifica. Ogni previsione va registrata prima, come questa.
- La calibrazione va allargata: tre punti ufficiali esistono ora, e ogni nuova sottomissione
  ne aggiunge uno. I rapporti per membro vanno ricalcolati su tutti, non su uno.
- `--max-calls` resta implementato ma **non ha sostegno nei dati**; `t04` e `t05` restano
  come controlli non sottomessi.
- Il problema aperto non è la taratura delle ampiezze: è che il trasferimento K562 non
  produce, sui contesti A/B/C, direzioni migliori del caso. È lì che va il lavoro successivo.

## 7. Cosa corregge

- Chiude la domanda lasciata aperta da [CP-0021](0021-ancore-ufficiali-e-troppe-chiamate.md)
  §4 a favore della seconda lettura, con una misura sui contesti ufficiali e non per
  analogia con HepG2.
- Conferma, fuori campione, le ancore di CP-0021 §3, che erano esatte per costruzione ma non
  verificate.
- Non corregge CP-0021 sul resto: la definizione della metrica, i valori grezzi e la
  diagnosi del divario col banco restano come scritti lì.

## 8. Domanda di comprensione

La previsione ha sbagliato del 63% su `jaccard` e dell'1% sulla fedeltà, e la media è
risultata giusta a 0,014. Perché l'errore grande su `jaccard` ha spostato così poco la
media, e in quale caso questo smetterebbe di essere vero?
