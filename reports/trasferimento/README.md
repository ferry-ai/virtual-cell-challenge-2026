# trasferimento — la ricetta di produzione e le sue varianti

La ricetta d'invio (stadio 100, `configs/recipes/t22.json`) media, per ogni bersaglio, gli
effetti misurati in altre linee: K562, CD4, Orion HCT116 e HEK293T a pesi uguali, effetti
ristretti, γ = 1 (a ogni sorgente si toglie la sua risposta media), affidabilità n/(n+100) fra
sorgenti, ampiezza 1,576, più la testa cis CRISPRi. Qui stanno i banchi che l'hanno costruita e
quelli che ne hanno provato le varianti. Indice generale: [../README.md](../README.md).

**Come leggerli.** Quasi tutti tengono fuori una sorgente pubblica alla volta e la usano come
verità: Δ = 0,36 ΔPDS_gen − 0,27 ΔnMAE_gen dopo il passo di profilo del trial-01 e uno
pseudobulk di 400 cellule, con bootstrap appaiato sui bersagli. **Sono proxy**: la verità è una
sorgente rumorosa, i bersagli sono i suoi, e fedeltà, reach, Jaccard e MSE non entrano. Il solo
confronto con lo scorer vero è il [banco HepG2](../generatore_e_banchi/banco_hepg2_v2_2026-09-26/RISULTATI.md).

**Dal 29/09** l'[audit scientifico](../analisi/lead_scientist_2026-09-29/AUDIT_SCIENTIFICO.md)
corregge la lettura «ricetta satura»: le ultime modifiche hanno un guadagno netto piccolo, ma
ampiezza e generatore non sono confinati, e diversi confronti cambiavano più fattori insieme.

**Da dove viene la ricetta di oggi:** t08 (K562 + CD4) → t11 (+ HCT116) → t15 e t16
(ampiezza × 2 e × 4, sul punteggio ufficiale) → t19/t20 (effetti ristretti a 1,576 + cis,
[banco varianti](banco_varianti_2026-09-25/CORREZIONE.md) e [modulo cis](modulo_cis_2026-09-26/RISULTATI.md))
→ t22 (+ HEK293T, [quattro sorgenti](quattro_sorgenti_2026-09-26/RISULTATI.md)) → t25 (stimatore
corretto). Il t23 (quota condivisa) è stato inviato il 28/09: +0,141868, non conclusivo ([CP-0042](../../docs/checkpoints/0042-t23-esclusione-pds.md)); [l'ablazione](ablazione_t23_2026-09-27/RISULTATI.md)
dice che del t23 conta l'esclusione dei geni stimati da una sola sorgente.

**La lezione che tiene insieme i risultati negativi (interpretazione):** riponderare sorgenti,
bersagli o programmi con ciò che le sorgenti dicono di sé non batte la media a pesi uguali; le
risposte di linee diverse si somigliano poco (coseno mediano 0,02–0,07 fra linee), e la parte
che si trasferisce è piccola e concentrata in pochi macchinari cellulari.

| Data | Cartella | Nocciolo | Vale? | Peso oggi |
|---|---|---|---|---|
| 04/10 | [fonti_transfer_2026-10-04/](fonti_transfer_2026-10-04/) | Transfer con più tabelle aggregate (regole `cells`, `all`) contro le fonti della ricetta (`production`), sei membri, su Jurkat e K562 (linee nuove); regola congelata prima delle uscite; condizioni per un invio di solo transfer | protocollo; esito nella scheda R-LEAD | ★★ |
| 28/09 | [taratura_proxy_2026-09-28/](taratura_proxy_2026-09-28/) | Il proxy dei banchi contro le differenze ufficiali già misurate: le quattro coppie a un fattore sopra il rumore (t10 − t08, t11 − t08, t15 − t11, t16 − t15), ricette ricostruite esatte, verità HEK293T; regola fissata prima di girare (azione 2 di R-REV). **Esito: non passa**, legge due coppie su quattro (non la via di CD4, non il secondo raddoppio); da qui nessun candidato si sceglie sul solo proxy (CP-0041) | sì, esito negativo per il proxy | ★★★ |
| 27/09 | [ablazione_t23_2026-09-27/](ablazione_t23_2026-09-27/) | Il t23 smontato: togliere gli 8.247 geni che meno di due universi stimano passa la regola su quattro sorgenti (e regge sulla cache corretta, r2); la pesatura oltre l'esclusione no; riscalare peggiora il proxy | sì (proxy; la riscalatura va provata sui membri DE) | ★★★ (dice come fare il prossimo candidato) |
| 27/09 | [quota_condivisa_2026-09-27/](quota_condivisa_2026-09-27/) | La quota condivisa per gene σ²/(σ²+τ²) sul pannello: passa la regola (Δ +0,012 e +0,013 con intervallo sopra zero); origine del t23. Ipotesi scelta dopo l'atlante r1 | in parte: l'ablazione attribuisce il guadagno all'esclusione, non alla quota; contiene `t23/share.csv`, letto dalla ricetta t23 | ★★ |
| 26/09 | [atlante_2026-09-26/](atlante_2026-09-26/) | Trasferimento su 1.000 bersagli fuori pannello per linea tenuta fuori: nessun braccio passa (r1), r2 replica. Misure descrittive importanti: coseno fra linee 0,02–0,07, fra stati della stessa cellula 0,20–0,25; il pannello ha knockdown di forza tipica; lo SE di Replogle è calibrato | sì (proxy, regime C: non prova bersagli nuovi) | ★★★ |
| 26/09 | [quattro_sorgenti_2026-09-26/](quattro_sorgenti_2026-09-26/) | HEK293T come quarta sorgente a peso uguale: +0,011 con K562 fuori, +0,001 con CD4 fuori; passa la regola, origine del t22 (ufficiale +0,0016, nel rumore) | sì | ★★ |
| 26/09 | [trasferimento_gerarchico_2026-09-26/](trasferimento_gerarchico_2026-09-26/) | Bayes empirico (risposta condivisa + deviazione di linea + rumore): nessun braccio passa; con 2–3 linee la varianza condivisa è mal stimata | sì, esito negativo | ★★ |
| 26/09 | [trasferimento_appreso_2026-09-26/](trasferimento_appreso_2026-09-26/) | Gradient boosting per coppia bersaglio–gene (stadio 104): r1 con perdite; r3–r4 con centri calcolati prima degli split; r5, isolato, +0,004…+0,008 con l'nMAE peggiore: niente t21 | in parte: vale solo r5. L'audit di codex sui centri calcolati prima degli split è in [analisi/audit_piani_dati_2026-09-26/](../analisi/audit_piani_dati_2026-09-26/RISULTATI.md), recuperato il 28/09 (R-019, R-020); la revisione di r1 è in `agenti/` | ★★ |
| 26/09 | [risposta_comune_2026-09-26/](risposta_comune_2026-09-26/) | La risposta comune a tutti i knockdown pesa l'1–14 % e non si trasferisce fra linee. **r2: la `mse` ufficiale dei nostri invii segue 1 + E/4786**: le previsioni sono quasi ortogonali agli effetti veri | sì (sei punti, un generatore) | ★★★ |
| 26/09 | [contesti_2026-09-26/](contesti_2026-09-26/) | Pesare le sorgenti per somiglianza basale (H6, Mixscale) o per stato di p53 non aiuta in modo coerente | sì, esito negativo | ★★ |
| 26/09 | [rete_2026-09-26/](rete_2026-09-26/) | Lisciare con i partner STRING i bersagli misurati: effetto piccolo (+0,0002…+0,003) | sì | ★ |
| 26/09 | [bersagli_nuovi_2026-09-26/](bersagli_nuovi_2026-09-26/) | I 300 del pannello trattati da bersagli mai misurati: cis da solo 0,56–0,58 di PDS proxy, 0,1 × STRING + cis fino a +0,035, lo stesso bersaglio misurato in K562 0,71–0,76. Da qui il ripiego `association` dello stadio 100 | sì | ★★ (serve ai bersagli scoperti del 22/10) |
| 26/09 | [programmi_2026-09-26/](programmi_2026-09-26/) | Proiettare l'effetto trasferito su programmi di risposta perde PDS a ogni rango (−0,02…−0,22) | sì, esito negativo | ★★ |
| 26/09 | [modulo_cis_2026-09-26/](modulo_cis_2026-09-26/) | La testa cis CRISPRi (repressione dei geni con il TSS entro 5 kb): +0,001…+0,006 di PDS proxy; entra nel t20. Su HepG2 con lo scorer vero non si vede. `cis_bench.py` fa da libreria dei proxy | sì | ★★ |
| 25/09 | [banco_varianti_2026-09-25/](banco_varianti_2026-09-25/) | Varianti della ricetta del t15 su sorgenti tenute fuori: effetti ristretti +0,01…+0,04 di PDS proxy; γ e consenso non contano; filtro dei bersagli difficili respinto; `MSE.md`: l'ampiezza ottima per l'errore quadratico è 0,02–0,16 e guadagna meno dello 0,11 % | in parte: `RISULTATI.md` ha tabelle sbagliate (R-017), leggere `CORREZIONE.md`; `noise_sim2.py` fa da libreria dei proxy | ★★ |
| 24/09 | [direzione_2026-09-24/](direzione_2026-09-24/) | Stadio 103: il segno della miscela delle altre sorgenti coincide con quello della sorgente tenuta fuori nel 51–56 % dei geni più mossi; il consenso aggiunge poco; va letto contro i bersagli scambiati (CP-0034) | sì | ★★ |
| 17/09 | [cis_2026-09-17/](cis_2026-09-17/) | Stadio 77: curva effetto–distanza dal TSS sul K562; **`k562_neighbour_pairs.csv` è letto dalle ricette t20–t25** | sì | ★★★ (ingresso di produzione: non spostare né modificare) |
