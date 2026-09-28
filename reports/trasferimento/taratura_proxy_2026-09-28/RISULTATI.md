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
