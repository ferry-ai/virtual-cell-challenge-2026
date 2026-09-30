# Perché il guadagno resta piccolo: lettura descrittiva dopo il gate

**Misurato dopo la lettura di seed 0; non causale, non un nuovo criterio di
promozione.** `analyze_seed0_descriptive.py` legge i piccoli CSV dei cinque fold e
i soli metadati r2 con hash confrontati ai manifest originali. Non legge gli array
di effetti. Le 6.144 coppie target–contesto corrispondono a 5.049 target distinti.
`context_contributions.csv`, `summary.json`, `per_target_descriptive.csv` e
`support_counts.json` conservano tutte le misure, senza scegliere un sottoinsieme
per migliorare il verdetto.

## I dodici contributi

Ogni contributo al macro è la differenza media del contesto divisa per cinque
famiglie e per il numero di contesti della sua famiglia.

| Contesto | Rete − transfer | Contributo al macro | Copertura sorgente mediana |
|---|---:|---:|---:|
| K562 | −0,006467 | −0,000431 | 95,20% |
| K562 essential | −0,016412 | −0,001094 | 95,22% |
| VIPerturb | +0,001193 | +0,000080 | 95,12% |
| CD4 Rest | +0,004380 | +0,000292 | 94,35% |
| CD4 Stim8hr | +0,005374 | +0,000358 | 94,29% |
| CD4 Stim48hr | +0,005718 | +0,000381 | 94,33% |
| KOLF | +0,000325 | +0,000022 | 87,68% |
| HipSci fit | +0,006876 | +0,000458 | 87,69% |
| HipSci nonfit | +0,002633 | +0,000176 | 87,70% |
| Orion HCT116 | +0,000015 | +0,000002 | 86,94% |
| Orion HEK293T | −0,002641 | −0,000264 | 87,17% |
| RPE1 | +0,011218 | +0,002244 | 97,04% |

L'intero incremento macro `+0,00222233` proviene numericamente da RPE1
(`+0,00224361`); la somma dei contributi delle altre quattro famiglie è
`−0,00002128`. Non è una ragione per scegliere RPE1: mostra quanto il guadagno sia
eterogeneo. K562 essential è il maggiore contributo negativo pur avendo alta
copertura e una mediana di sette contesti con misura diretta del target.

La copertura qui è `source_supported_genes / 13248`, sull'asse modellato. Non si
divide per `common_genes`, perché quello è un asse diverso: il supporto comune
della verità usato dal rango varia da 6.530 a 9.115 geni. Confondere i due assi
produrrebbe perfino coperture superiori al 100%.

## Copertura, bersaglio diretto e fallback

La correlazione di Spearman fra copertura e guadagno, calcolata separatamente nei
12 contesti, varia fra `−0,082` e `+0,100`. I quattro quartili di copertura entro
contesto hanno guadagni macro `+0,00367`, `+0,00186`, `+0,00118`, `+0,00207`:
non appare un gradiente monotono forte. Sono descrizioni, senza test post hoc di
significatività o correzione della soglia originale.

230 coppie non hanno alcuna misura diretta del target nelle famiglie sorgente
visibili; per 55 esiste almeno un fallback STRING ammissibile, per 175 neppure
quello. Nei CSV 175 coppie hanno zero geni sorgente supportati, nessuna delle quali
ha una misura diretta. La maggiore concentrazione è Orion: 61/512 HCT116 e 52/512
HEK293T senza supporto. È un limite concreto di un modello che modifica una miscela
di profili esistenti, ma riguarda solo il 2,85% delle coppie totali e non spiega da
solo il degrado di K562 essential.

Un fallback è possibile in almeno un contesto sorgente per 3.563/6.144 coppie,
inclusi 401/512 K562 essential e 411/512 RPE1. **Possibile non significa pesato**:
i report non salvano il peso effettivo dei token o la quota di energia fallback.
La risposta del gene proprio e del cis era esclusa dal protocollo; non è presente
qui un outcome di knockdown proprio da confrontare. I conteggi sopra riguardano
la disponibilità del target perturbativo nelle sorgenti, una cosa diversa.

## Cosa non si può chiamare forza vera

I CSV non contengono la norma assoluta della risposta vera. Non la si sostituisce
con PDS, coseno o NMSE. Come descrizione separata, usando il coseno della baseline
con la verità per costruire quartili entro contesto, i guadagni macro sono
`+0,01162`, `+0,00506`, `−0,00460`, `−0,00341`: la rete tende a recuperare casi in
cui la baseline è meno allineata e a perdere nei più allineati. Questo
condizionamento **usa la verità e ha accoppiamento matematico con il delta**;
regressione verso la media e limiti del rango possono contribuire. Non è una
regola applicabile a predizioni nuove, né prova di una categoria biologica.

La norma mediana rete/transfer va da 0,928 in K562 a 1,120 in K562 essential.
Questa variazione non spiega causalmente un rango basato sul coseno, che non cambia
scalando uniformemente un'intera predizione. Segnala solo che la miscela appresa
modifica anche l'ampiezza; non è una calibrazione da ottimizzare sul test.

## Ipotesi concreta da separare in una prova successiva

**Ipotesi, non dimostrata:** parte del piccolo guadagno è una correzione generica
di miscele dirette/fallback e della loro affidabilità, più che un abbinamento
biologico efficace del contesto. È compatibile con l'assenza di beneficio rispetto
alla rete cieca, con il risultato del contesto scambiato e con l'ampia disponibilità
di token fallback; questi elementi non ne identificano la causa.

Il test discriminante era già proposto prima degli esiti nel protocollo della
diagnostica: stessa rete e stessi checkpoint, baseline `direct_only` che elimina
i token fallback e rinormalizza le famiglie, mantenendo nel rango anche i target
senza previsione. Riportare rete−direct_only, transfer−direct_only, peso fallback,
copertura e norme su **tutti** i target e tutte le famiglie. Nessuna ricerca della
soglia o del coefficiente sui fold appena letti. La prova richiede i token o nuovi
forward su un runner e non è stata eseguita qui.

Un secondo controllo metodologico futuro può confrontare la scelta dei passi
sulla sola famiglia interna mediana con una validazione interna distribuita fra
le famiglie visibili, tenendo fissa la famiglia esterna. L'attuale scelta usa Orion
per tre fold e K562 per due; i passi selezionati variano da 200 a 450. Va definito
prima di nuovi esiti e non costituisce una giustificazione per scegliere a
posteriori il seme o il contesto favorevole. Seed 1 resta una replica completa
dell'esperimento originale, e il gate di seed 0 rimane fallito.
