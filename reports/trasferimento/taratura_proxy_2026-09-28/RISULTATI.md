# Il proxy dei banchi contro le differenze ufficiali: protocollo e regola (azione 2 di R-REV)

28 settembre 2026. Scrive Claude (app desktop, sessione `f4f38e58`); orari letti da `date`. Scheda:
[R-REV](../../../docs/piani/revisione-critica.md), azione 2; revisione, §2.1 e §2.3.

Etichette: **misurato**, **interpretazione**, **ipotesi**, **proposta**. Nessun numero qui è un punteggio VCC.

## La domanda

Dal 25/09 i banchi si leggono sul proxy Δ = 0,36 ΔPDS_gen − 0,27 ΔnMAE_gen, contro una sorgente pubblica tenuta
fuori. Il proxy prevede il **segno** delle differenze ufficiali già misurate?

## Protocollo, fissato alle 18:45 del 28/09, prima di girare

**Le coppie.** Le quattro coppie a un fattore sopra il rumore del seme (0,005, misurato dal t24):

| Coppia | Che cosa cambia | Δ ufficiale (scalato) | Membri ufficiali |
|---|---|---|---|
| t10 − t08 | via CD4 (K562 da solo), ampiezza 0,197 | −0,0102 | pds −, nmae −, fedeltà +, reach − |
| t11 − t08 | più HCT116, pesi uguali (anche K562 e CD4 cambiano peso) | +0,0104 | pds +, nmae ≈ 0, fedeltà −, reach + |
| t15 − t11 | ampiezza × 2 (0,197 → 0,394) | +0,0368 | pds +, nmae +, fedeltà +, reach + |
| t16 − t15 | ampiezza × 2 (0,394 → 0,788) | +0,0301 | pds +, nmae +, fedeltà +, reach + |

Le prime tre righe vengono da `reports/invii/lezioni_invii_2026-09-28/coppie.csv`, la quarta da CP-0037 (membri
derivati dagli scalati con le ancore). Nei membri il segno è quello del contributo al punteggio: nmae + vuol dire
nMAE più basso.

**Le ricette** si ricostruiscono esatte da `configs/recipes/`: effetti grezzi, γ 1, affidabilità n / (n + 100),
pesi e ampiezza della ricetta, nessuna testa cis (queste ricette non l'avevano), le stesse cache:
- t08 e t10: stadio 98 r3;
- t11, t15 e t16: stadio 98 r4.

I bersagli non coperti dalle sorgenti non ricevono effetto, come negli invii.

**La verità.**
- **Principale:** HEK293T (cache r5), che non entra in nessuna di queste ricette. Bersagli: quelli del pannello
  misurati in HEK293T.
- **Letture in più** dove la verità non è la sorgente che cambia:
  - t10 − t08: HCT116 (non è fra le sorgenti di nessuna delle due);
  - t15 − t11 e t16 − t15: K562, CD4 e HCT116, ciascuna togliendo sé stessa dalle sorgenti di entrambe le ricette.

**I membri del proxy**, come `reports/trasferimento/quattro_sorgenti_2026-09-26/four_sources_bench.py`, fissati da
`tests/test_proxy_banchi.py`:
- PDS_gen e nMAE_gen dopo il passo di profilo del trial-01 e il rumore di un pseudobulk di 400 cellule, sui basali di
  A, B e C, tre semi;
- il PDS nello spazio degli effetti, come riferimento.

Intervallo: bootstrap sui bersagli, 2.000 ricampionamenti.

### Regola

Proposta dalla scheda R-REV, fissata qui senza cambiarla.
- **Se il proxy combinato sbaglia il segno anche su una sola delle quattro coppie**, sulla verità HEK293T, nessun
  candidato si propone più al proprietario sul solo proxy: serve il banco dell'azione 4 (scorer vero).
- **Segno giusto** vuol dire Δ del proxy con lo stesso segno del Δ ufficiale. Se l'intervallo del proxy contiene lo
  zero, la coppia conta come «non letta», e non come segno giusto: un proxy che non vede la differenza non la
  prevede.
- **Descrittivo, non decide:**
  - i due membri da soli contro `pds` e `nmae` ufficiali;
  - le letture sulle altre verità.

**Chiusura:** questo report e un checkpoint.

## Esito (misurato, 28/09, 19:18–19:28; cartella [`r1/`](r1/))

Girato dalla sessione Claude `f2abd9a6`, che continua la `f4f38e58`, con il codice e il protocollo committati alle
18:46 (`055ecff`), senza modifiche:

```bash
scripts/py.cmd reports/trasferimento/taratura_proxy_2026-09-28/taratura_proxy.py \
    --out reports/trasferimento/taratura_proxy_2026-09-28/r1
```

### La regola: il proxy non passa

Verità HEK293T, 281 bersagli del pannello misurati; Δ del proxy combinato con l'intervallo al 95 %:

| Coppia | Δ ufficiale | Δ proxy combinato | Letta? | Segno giusto? |
|---|---|---|---|---|
| t10 − t08 (via CD4) | −0,0102 | +0,0055 [−0,0048; +0,0152] | no | no (e la stima punta dall'altra parte) |
| t11 − t08 (più HCT116) | +0,0104 | +0,0233 [+0,0160; +0,0303] | sì | sì |
| t15 − t11 (ampiezza × 2) | +0,0368 | +0,0133 [+0,0107; +0,0159] | sì | sì |
| t16 − t15 (ampiezza × 2) | +0,0301 | +0,0018 [−0,0002; +0,0037] | no | no |

Due coppie su quattro non sono lette. **Per la regola fissata alle 18:45: nessun candidato si propone più al
proprietario sul solo proxy; serve il banco dell'azione 4 (scorer vero).**

### Descrittivo, non decide

**Le altre verità** (Δ combinato):

| Coppia | HCT116 | K562 | CD4 |
|---|---|---|---|
| t10 − t08 | +0,0031 [−0,0055; +0,0117], non letta | — | — |
| t15 − t11 | +0,0110, giusto | +0,0169, giusto | +0,0058, giusto |
| t16 − t15 | +0,0030 [+0,0008; +0,0051], giusto | +0,0095, giusto | **−0,0113** [−0,0137; −0,0088], sbagliato |

**I due membri da soli**, contro i membri ufficiali (verità HEK293T):
- **PDS_gen:** va nel verso del `pds` ufficiale su tre coppie su quattro. Su t10 − t08 sale (+0,0145, intervallo sullo
  zero) mentre il `pds` ufficiale scende.
- **nMAE_gen:** raddoppiare l'ampiezza da 0,394 a 0,788 **peggiora** l'nMAE del proxy su HEK293T, HCT116 e CD4
  (+0,0074, +0,0040, +0,0519), mentre il `nmae` ufficiale del t16 migliora (CP-0037). Sul primo raddoppio i due vanno
  d'accordo, tranne su CD4.
- **PDS nello spazio degli effetti:** nelle coppie d'ampiezza vale 0, come deve: il ranking non cambia con un fattore
  comune. Su t10 − t08 sale anch'esso (+0,0378, intervallo sullo zero).

**Grandezze.** Dove il segno è giusto, il proxy vede le coppie d'ampiezza molto più piccole dell'ufficiale: +0,0133
contro +0,0368 al primo raddoppio, +0,0018 contro +0,0301 al secondo. Il t11 − t08 invece lo vede più grande
(+0,0233 contro +0,0104).

### Interpretazione

- Il proxy vede quello che passa dal PDS: aggiungere una sorgente che somiglia alla verità e il primo raddoppio.
- Non vede il guadagno del secondo raddoppio, che nell'ufficiale viene quasi tutto da fedeltà, `nmae`, `reach` e
  Jaccard, mentre `pds_cosine` sale appena (CP-0037). Il proxy ha un suo nMAE e non calcola gli altri tre.
- Il suo nMAE va contro quello ufficiale proprio dove l'ampiezza sale. Una spiegazione possibile (**ipotesi**, non
  verificata): il proxy misura l'errore sui geni con |Z| ≥ 3 nella verità pubblica, lo scorer sui geni DE del
  contesto di gara, che sono molti di più (circa 340 per bersaglio in A, CP-0039).
- La coppia via CD4 non si legge con nessuna delle due verità. Il proxy ha 268–281 bersagli e un rumore di
  pseudobulk simulato: una differenza ufficiale di un centesimo sta sotto quello che vede.
- **Conseguenza pratica (proposta, da confermare con il proprietario):** i banchi a proxy restano utili per scartare
  varianti che peggiorano il PDS. Per scegliere un candidato da inviare, e per ampiezza e sorgenti, serve lo scorer
  vero su un contesto pubblico tenuto fuori: l'azione 4 della scheda R-REV.

**Limiti.** Una verità principale sola, che non è una linea di gara. Quattro coppie. Il rumore di pseudobulk è
simulato su 400 cellule sui basali di A, B e C. Le ricette sono ricostruite dalle cache r3 e r4, non dai file inviati.
