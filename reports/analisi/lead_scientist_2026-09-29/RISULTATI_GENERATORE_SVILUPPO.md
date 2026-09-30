# Sviluppo HepG2: ampiezza e dispersione interagiscono, il guadagno è direzionale

29 settembre 2026. **Tipo di evidenza: misurato nello sviluppo locale; interpretazioni
ed analisi di sensibilità esplorative. Non è un punteggio VCC né una conferma.**

I finalisti già congelati sono **ampiezza 1,5 / dispersione 1** e **ampiezza 1,5 /
dispersione 0,5**. La proiezione rispetto a 1/0 aumenta rispettivamente di **0,0190934**
e **0,0152998**. Il generatore bins ad ampiezza 1 è terzo, **0,0112874**, e non viene
aggiunto alla conferma. Questo rapporto non cambia selezione, soglie o candidati.

## Evidenza conservata e ricostruzione

La copia in `generator_development_r3/` contiene **62 file, 1.044.662 byte**: tutti i
report JSON/CSV completi di `development`, il manifest dei bersagli e l'ambiente.
`generator_development_r3/COPY_MANIFEST.json` registra percorso originale, dimensione e
SHA256, con copia alle **18:13:26 UTC**. Nessun NPZ, NPY o dato cellulare è stato copiato.
**Nessun output della conferma è stato letto**; il manifest dei bersagli è quello
preregistrato e contiene entrambi gli split, senza risultati.

`analyze_generator_development.py` verifica tutti gli hash prima di analizzare e scrive
in `generator_development_r3/analysis/`. Sono stati ricostruiti i **13 delta** di
`development/selection.json` entro 1e-12, la fedeltà per bersaglio come
`k / max(n_pred, n_conf)`, e la MSE aggregata come rapporto fra somme di
`expr_mse_unbiased_capped` e `expr_distance_unbiased` entro 1e-10. La MSE non è la media
dei rapporti per bersaglio. Maschere di eleggibilità identiche fra tutti i bracci.

Fonti primarie: `generator_development_r3/development/{run_manifest,bench,selection}.json`,
i 14 file `result_*.json`, `per_pert_*.csv`, `components_*.csv` e `diagnostics_*.json`.
Derivati: `analysis/all_arms.csv`, `member_contributions.csv`, `target_contributions.csv`,
`interactions.csv`, `development_target_metadata.csv`, `analysis.json`.

## Disegno effettivamente valutato

48 bersagli di sviluppo scelti fra **274 eleggibili** del pannello congelato; un solo
seme generativo, 1. **4.659 cellule perturbate reali**, tutte disponibili per quei
bersagli, più **2.000 controlli**. Cellule reali per bersaglio: minimo 50, quartili
61 / **72,5** / 103,5, massimo 459; le previste sono **400 per bersaglio** in ogni braccio.
Asse di 9.624 geni; supporto K562 ricostruito di **7.681 geni** per bersaglio.
Ambiente registrato: Python 3.13.15, `cell-eval2` 0.16.0; memoria di picco misurata dal
run 3.844.837.376 byte. Non si stimano tempi futuri da questa misura.

La proiezione somma le variazioni di **cinque** metriche moltiplicate per le pendenze
delle ancore ufficiali, poi divide per sei; MSE contribuisce zero per protocollo.
PDS, fedeltà e Jaccard hanno 48 bersagli eleggibili; NMAE **38**; reach **45**.
Ogni membro mantiene il proprio denominatore. Non ci sono ancore locali, perché non
esiste una replica indipendente dell'intera verità (`bench.json.reason`).

Il `n_conf` delle componenti direzionali ha mediana **333,5**, quartili 20,5 / 1.674,
massimo 5.122. Tre bersagli hanno zero: CA5A, LTBP3 e PC; dieci hanno meno di dieci
geni confidenti. La statistica `bench.json.real_n_conf` riporta invece mediana 469:
è un conteggio generico di righe DE significative sui soli bersagli con chiamate,
prima del trattamento specifico del membro direzionale. Per interpretare fedeltà e
reach qui si usano esclusivamente i **48 `n_conf` di `components_*.csv`**.

## Griglia: l'ampiezza migliore dipende dalla dispersione

Variazione della proiezione rispetto a pooled 1/0:

| Ampiezza | phi 0 | phi 0,25 | phi 0,5 | phi 1 |
|---|---:|---:|---:|---:|
| 1 | 0 | +0,001699 | +0,001430 | −0,003752 |
| 1,5 | +0,005133 | +0,010203 | **+0,015300** | **+0,019093** |
| 2 | −0,000752 | −0,002744 | −0,000345 | +0,002563 |

Bins, senza dispersione residua: ampiezza 1 **+0,011287**; ampiezza 2 **+0,000710**.

**Misurato:** passare da phi 0 a 1 ad ampiezza 1 perde 0,003752; ad ampiezza 1,5
guadagna 0,013960. La differenza delle differenze è **+0,017713**. Per phi 0,5 la stessa
interazione è +0,008737. Non sono intervalli di confidenza né test aggiuntivi.

**Interpretazione:** la dispersione non è valutabile come correzione universalmente
buona o cattiva. Nello sviluppo recupera valore quando l'ampiezza aumenta le chiamate;
un confronto a sola ampiezza 1 avrebbe scartato il miglior braccio osservato. La griglia
non identifica un ottimo continuo e non valuta bins ad ampiezza 1,5 o bins con phi > 0.

## Che cosa migliora e che cosa peggiora

I sei valori grezzi, tutti conservati:

| Membro | Pooled 1/0 | Pooled 1,5/0,5 | Pooled 1,5/1 | Bins 1 |
|---|---:|---:|---:|---:|
| PDS, maggiore meglio | 0,897163 | 0,893174 | 0,894947 | 0,895390 |
| MSE, minore meglio | 1,279250 | 1,843963 | 1,841339 | 1,279266 |
| NMAE, minore meglio | 0,948760 | 0,974223 | 0,976017 | 0,933358 |
| Fedeltà, maggiore meglio | 0,499232 | 0,533697 | 0,545204 | 0,512784 |
| Reach, maggiore meglio | 0,149785 | 0,189072 | 0,184716 | 0,157618 |
| Jaccard, maggiore meglio | 0,092801 | 0,086487 | 0,082107 | 0,089895 |

Contributi già divisi per sei alla proiezione:

| Braccio | PDS | NMAE | Fedeltà | Reach | Jaccard | Totale |
|---|---:|---:|---:|---:|---:|---:|
| 1,5/1 | −0,000826 | −0,007472 | +0,025731 | +0,006544 | −0,004884 | +0,019093 |
| 1,5/0,5 | −0,001486 | −0,006981 | +0,019290 | +0,007359 | −0,002883 | +0,015300 |
| Bins 1 | −0,000661 | +0,004222 | +0,007585 | +0,001467 | −0,001327 | +0,011287 |

Il primo finalista guadagna dunque dalla **fedeltà direzionale**, sostenuta da reach;
perde sugli altri tre membri della proiezione. La MSE peggiora di **43,94%**; ad
ampiezza 2 arriva a circa 2,69. A parità di ampiezza la dispersione cambia pochissimo
la MSE: il deterioramento è soprattutto associato all'ampiezza. PDS non beneficia
dell'amplificazione in nessuno dei finalisti. Non è un miglioramento uniforme della
previsione, e il vantaggio netto dipende dalla scelta preregistrata di porre MSE a zero.
Non si trasporta la MSE grezza HepG2 nella scala ufficiale senza le sue ancore.

### La fedeltà non è soltanto riduzione delle chiamate

| Braccio | n_pred medio | n_pred mediano | k medio | somma(k)/somma(n_pred) |
|---|---:|---:|---:|---:|
| 1/0 | 1.452,23 | 1.223 | 822,35 | 0,56627 |
| 1,5/0 | 2.117,04 | 1.844 | 1.181,54 | 0,55811 |
| 1,5/0,5 | 1.897,23 | 1.565 | 1.096,85 | 0,57814 |
| 1,5/1 | 1.815,25 | 1.445,5 | 1.069,92 | 0,58940 |

Rispetto al riferimento, 1,5/1 produce **25,00% più chiamate** e **30,10% più accordi
di segno**. Rispetto alla stessa ampiezza senza dispersione, riduce invece le chiamate
del 14,26% e gli accordi del 9,45%: aumenta la frazione concorde. Fedeltà coincide con
la precisione direzionale quando `n_pred >= n_conf`: ciò vale per 35/45 bersagli con
`n_conf > 0` nel riferimento e 40/45 nel finalista.

Qui `k` conta accordi di segno nei geni predetti significativi con direzione reale
definita; **non è il numero di veri positivi DE** e può superare `n_conf`. La precisione
direzionale non va confusa con precisione delle chiamate significative. Jaccard scende
del **11,52%** nel primo finalista: la sovrapposizione degli insiemi significativi peggiora
anche mentre gli accordi direzionali aumentano.

## Quali bersagli sostengono il risultato

Si attribuisce a ogni bersaglio la somma dei suoi delta pesati, divisi per il numero
di bersagli eleggibili del rispettivo membro. Questi contributi sommano esattamente
al delta totale; non sono punteggi VCC per bersaglio.

Per 1,5/1, **34/48** contributi sono positivi e 14 negativi. I cinque maggiori valgono
il **59,85%** del guadagno netto:

| Bersaglio | Cellule reali | n_conf | Contributo netto |
|---|---:|---:|---:|
| CSE1L | 240 | 5.122 | +0,003681 |
| WBP11 | 62 | 160 | +0,002567 |
| SETD1A | 81 | 2.282 | +0,002121 |
| CCDC130 | 145 | 8 | +0,001581 |
| SLC7A6OS | 51 | 1.441 | +0,001477 |

CSE1L passa da 3.188 a 5.119 chiamate, quasi il suo budget reale di 5.122, e da
2.361 a 3.614 accordi; la fedeltà dà +0,002853 del suo contributo. SETD1A passa da
879 a 1.271 accordi e contribuisce soprattutto per fedeltà (+0,002003). WBP11 divide
il vantaggio fra fedeltà (+0,001113) e reach (+0,001301). Per CCDC130, con otto geni
confidenti, non esiste contributo NMAE: il vantaggio è PDS e fedeltà. Questi sono
meccanismi numerici osservati, non spiegazioni biologiche dedotte dai nomi.

Le perdite maggiori sono DCTN1 **−0,002918**, CHMP6 **−0,002112** e OGFOD1
**−0,002004**. Per DCTN1 pesa soprattutto PDS; per CHMP6 e OGFOD1 NMAE.

Togliendo esplorativamente il miglior bersaglio e ricalcolando tutti i denominatori,
il delta resta +0,015709; togliendo i migliori tre +0,011323; togliendo i migliori
cinque **+0,008589**. Per il secondo finalista i contributi positivi sono 28/48 e il
delta senza i migliori cinque è +0,004934. Sono sensibilità selezionate dopo il risultato,
**non nuovi criteri di promozione**. I contributi dei due finalisti sono correlati
(Pearson 0,883): non costituiscono due repliche indipendenti.

Il 76,82% del guadagno netto del primo finalista viene dai 22 bersagli con almeno
500 geni confidenti. Non è quindi sostenuto solo dai pochi geni con denominatori
minimi; tuttavia reach rimane sensibile a questi ultimi. Per esempio BRD2 (`n_conf=9`)
apporta +0,001388 al membro reach. Nei bins, RPL41 (`n_conf=4`) da solo apporta
+0,003122 a reach, maggiore del guadagno netto aggregato di quel membro (+0,001467)
perché altri bersagli perdono. La correlazione descrittiva fra cellule reali e `n_conf`
è 0,249; fra cellule reali e contributo di 1,5/1 è 0,073. Non provano assenza di
effetti di potenza: profondità, risposta e campionamento non sono separati da queste correlazioni.

## Bins: evidenza distinta, graduatoria invariata

Il fit sui soli controlli sceglie **uniform8**: RMSE del CPM medio atteso 0,5714 contro
0,9932 di tail8; smoothing 0,01. Bins ad ampiezza 1 migliora sia NMAE sia fedeltà,
lasciando MSE praticamente invariata. È un diverso compromesso rispetto ai finalisti.
Il suo delta senza i cinque bersagli più favorevoli diventa +0,004149. La conservazione
del profilo pooled atteso non garantisce da sola robustezza delle metriche perturbative.
Non si aggiunge alla conferma e non si propone come vincitore sulla base di questa lettura.

## Limiti e decisione congelata

- **Selezione:** 14 bracci, 48 bersagli, un solo seme. Gli intervalli bootstrap al 95%
  dello sviluppo sono descrittivi dopo selezione, non corrette prove di superiorità:
  1,5/1 [0,003121; 0,033566], 1,5/0,5 [0,000729; 0,030343], bins 1
  [0,002149; 0,021496]. Non sostituiscono la verifica separata.
- **Generalizzazione:** un solo contesto HepG2 e soli effetti K562 t19like. Non viene
  verificata la ricetta multisorgente t25 né la sua ampiezza assoluta. L'ampiezza 1,5
  qui è relativa agli effetti congelati di questo banco.
- **Potenza e popolazione:** i controlli sono 2.000 e le cellule reali mediane 72,5,
  contro 400 predette; dieci bersagli non partecipano a NMAE. Il bootstrap dei bersagli
  non ricampiona controlli, cellule reali, contesti o semi. Le soglie DE amplificano
  tali differenze; il confronto appaiato le mantiene costanti ma non le elimina.
- **Obiettivo:** MSE esclusa dalla selezione e cinque denominatori non identici;
  pendenze ufficiali applicate a dati locali. Non si afferma un miglioramento del
  punteggio VCC. I sei grezzi e il costo sulla MSE restano parte della conclusione.
- **Diagnostica:** le attribuzioni e gli strati sono descrittivi, non ipotesi biologiche
  confermate. Il clipping dei profili coinvolge 4 coppie gene-bersaglio ad ampiezza 1,
  41 ad ampiezza 1,5 e 88 ad ampiezza 2; il fattoriale mantiene lo stesso trattamento.

Restano **solo** i due finalisti preregistrati 1,5/1 e 1,5/0,5. La regola di conferma
rimane: 96 bersagli disgiunti, semi 1/2/3, delta medio almeno +0,005, positivo in ogni
seme e limite inferiore bootstrap appaiato al **97,5%** sopra zero per ciascuno dei due
confronti. Questo rapporto non legge né anticipa l'esito di quella verifica.
