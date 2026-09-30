# Replica neurale: entrambi i semi falliscono la soglia registrata

**Misurato il 29 settembre 2026; proxy PDS, non punteggio VCC.** Il seed 1
completa tutti e cinque i fold con codice di ritorno zero, alle 20:43:45 UTC;
la lettura verificata termina alle 20:43:47 e la diagnostica cluster alle
20:44:09. Il kernel è `COMPLETE`. Sono stati recuperati 68 report piccoli,
18.773.512 byte; checkpoint e predizioni NPZ restano conservati sul kernel.

La guardia locale di `read_neural_verified.py` passa su tutti i cinque fold.
`compare_neural_seeds_r1.py` verifica che i due semi hanno esattamente gli stessi
indici target–contesto–braccio e numeri di geni comuni: **6.144 coppie
target–contesto, 12 contesti, cinque famiglie e 5.049 target distinti** per seme.
Il confronto riguarda il regime C fuori pannello; non misura un regime di target
mai osservati in ogni sorgente. Nessun fold né seme è stato selezionato dopo
aver visto il risultato.

## Regola e risultato primario

La regola congelata richiede rete−transfer macro almeno `+0,01`, limite inferiore
del CI95 positivo e nessuna famiglia sotto `−0,01`. Le famiglie hanno peso uguale;
entro una famiglia i contesti hanno peso uguale.

| Contrasto macro | Seed 0 | CI95 seed 0 | Seed 1 | CI95 seed 1 |
|---|---:|---|---:|---|
| Rete − transfer | +0,00222233 | [+0,00055605; +0,00390661] | +0,00245854 | [+0,00068125; +0,00439651] |
| Rete − cieca | −0,00041611 | [−0,00104444; +0,00021331] | +0,00074226 | [−0,00004817; +0,00155537] |
| Rete − contesto scambiato | −0,00022283 | [−0,00043760; −0,00001679] | +0,00020041 | [−0,00008246; +0,00045321] |
| Rete − prior permutato | −0,00023188 | [−0,00050340; +0,00003096] | +0,00034425 | [−0,00006412; +0,00074155] |

**Entrambi i semi falliscono la soglia di utilità `+0,01`.** I piccoli guadagni
sul transfer hanno CI positivi, ma questo non modifica la regola. Non viene
proposto fit di produzione, adattamento ABC o scoring cellulare di questa rete.
Non è stato costruito un CI aggregato sui due semi trattandoli come esperimenti
biologici indipendenti.

Il JSON seed 1 contiene `evidence_for_context_use=true`: nel reader congelato
la definizione è soltanto `macro(net−blind)>0`, senza controllo del CI. Qui il CI
include zero e il seed 0 ha punto negativo. Quel booleano **non è una prova
statistica né replicata dell'utilità del contesto**. Il reader e gli esiti
originali restano immutati; il significato esatto del campo è documentato.

## Famiglie e contesti: eterogeneità replicata

| Famiglia | Rete−transfer s0 | Rete−transfer s1 | Rete−cieca s0 | Rete−cieca s1 |
|---|---:|---:|---:|---:|
| K562 | −0,007229 | −0,007058 | −0,003101 | +0,002293 |
| CD4 | +0,005157 | +0,005306 | +0,000889 | +0,000085 |
| Orion | −0,001313 | −0,002238 | −0,000042 | −0,003027 |
| iPSC | +0,003278 | +0,003207 | −0,001203 | −0,000303 |
| RPE1 | +0,011218 | +0,013076 | +0,001376 | +0,004663 |

| Contesto | Rete−transfer s0 | Rete−transfer s1 |
|---|---:|---:|
| K562 | −0,006467 | −0,006689 |
| K562 essential | −0,016412 | −0,015862 |
| VIPerturb | +0,001193 | +0,001376 |
| CD4 Rest | +0,004380 | +0,004468 |
| CD4 Stim8hr | +0,005374 | +0,005661 |
| CD4 Stim48hr | +0,005718 | +0,005791 |
| KOLF | +0,000325 | +0,000279 |
| HipSci fit | +0,006876 | +0,006796 |
| HipSci nonfit | +0,002633 | +0,002546 |
| Orion HCT116 | +0,000015 | −0,001223 |
| Orion HEK293T | −0,002641 | −0,003253 |
| RPE1 | +0,011218 | +0,013076 |

La forma del confronto col transfer è stabile: perdita K562, beneficio CD4/iPSC,
beneficio maggiore RPE1. Nel seed 1 il contributo pesato RPE1 è `+0,00261512`,
maggiore dell'intero macro `+0,00245854`; tutte le altre famiglie insieme danno
`−0,00015658`. Non è una ragione per scegliere RPE1 dopo il test. K562 essential
perde oltre `0,015` in entrambi i semi: il vincolo registrato riguarda la media
di famiglia, quindi tale sottocontesto non crea un nuovo criterio retroattivo.

L'utilità rispetto alla rete cieca cambia segno in K562 fra semi e resta piccola
in CD4, pur essendo il guadagno sul transfer stabile. **Interpretazione:** è
replicato un piccolo aggiustamento della miscela di sorgenti, non un beneficio
utile e robusto dimostrato dell'abbinamento biologico del contesto. Non si deduce
che la rete ignori materialmente le feature di contesto, né che ogni architettura
neurale sia inutile. L'ipotesi diretti/fallback di
`neural_descriptive_r1/LETTURA.md` resta un'ipotesi per una prova distinta.

## Sensibilità cluster del seed 1

Il codice congelato `cluster_pds.py` riproduce i ranghi originali in tutti i 12
contesti prima del bootstrap. Usa 2.000 ricampionamenti, seed 20260929, e lo
stesso conteggio di ciascun target in tutti i contesti/famiglie in cui appare.
936 dei 5.049 target sono presenti in più contesti. Ricalcola anche il PDS sul
pannello ricampionato, con maschere e centratura originali fisse.

| Contrasto seed 1 | Punto macro | CI95 cluster, PDS ricalcolato | CI95 cluster, ranghi fissi |
|---|---:|---|---|
| Rete − transfer | +0,00245854 | [+0,00056367; +0,00429408] | [+0,00044940; +0,00438618] |
| Rete − cieca | +0,00074226 | [−0,00008976; +0,00153003] | [−0,00007371; +0,00153420] |

La sensibilità non cambia la conclusione. I CI restano condizionati alle predizioni
apprese, alla centratura/supporto osservati e a queste cinque famiglie; non sono
un bootstrap dell'intero addestramento o di futuri tipi cellulari. Per seed 0 la
diagnostica separata non è disponibile a causa del fallimento operativo del mount
Kaggle, già documentato; non si presenta il risultato seed 1 come sostituzione.

## Evidenza riproducibile

- Download e stato: `kaggle_lead_monitor/r6/` e relativo `download_manifest.json`.
- Lettura primaria locale: `kaggle_neural_seed1_r1/readout_verified_r1/`.
- Diagnostica: `kaggle_lead_monitor/r6/seed1/neural_seed1_r1/cluster_diagnostic/`.
- Confronto completo: `neural_two_seeds_r1/comparison.json`, `families.csv`,
  `contexts.csv`; generato da `compare_neural_seeds_r1.py`.
- Seed 0: `RISULTATI_NEURALE_SEED0.md` e
  `kaggle_neural_r1/readout_verified_r1/`.

Questa lettura chiude la replica prevista nell'emendamento di scheduling.
Nessuna modifica di soglie, nessun nuovo training, nessuna submission.
