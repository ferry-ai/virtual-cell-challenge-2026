# Biologia, contesti e affidabilità: risultati e limiti

25 settembre 2026. Codex, task `01a0d81b-3495-74d0-9537-eb5254b05002`.
Ricerca svolta inizialmente in sola lettura; il proprietario ha poi autorizzato
la scrittura in chat. **Misure esplorative a posteriori**, non un protocollo
preregistrato, un nuovo modello addestrato o punteggi VCC.

## 1. Provenienza e riproduzione

I tre agenti interni `local_patterns`, `architecture_critique` e `biology_sources`
hanno contribuito rispettivamente ad analisi tabellare, critica architetturale e
ricerca bibliografica. Le misure sotto sono state rieseguite da Codex con
[analyze.py](analyze.py); non dipendono soltanto dai loro riepiloghi.
La revisione MSE è stata ricontrollata sul codice con `review_mse_reconciliation`.
Non è stata avviata la vecchia catena di cicli né una campagna sull'hub esterno.

```powershell
.\scripts\py.cmd -B reports/biologia_architetture_2026-09-25/analyze.py --out reports/biologia_architetture_2026-09-25/r2
```

Il comando è per una nuova esecuzione: `r1` è l'esecuzione conservata; lo script
rifiuta directory di output già esistenti. Input pesanti nella cartella dati,
letti senza modificarli; nessun download. [measurements.json](r1/measurements.json)
registra timestamp UTC, versioni Python/numpy/pandas e SHA256 di script, archivio
Mixscale, CSV precedente, cinque cache CD4, asse genico e pannello.

Tre supporti distinti, da non confondere:

- **Rianalisi delle metriche precedenti:** 1.626 righe di
  [per_target_context.csv](../dld1_audit_2026-09-24/mixscale_r1/per_target_context.csv),
  con le selezioni originarie, descritte nel relativo script/report.
- **Nuova lettura delle matrici DE Mixscale:** log2FC degli autori, non conteggi
  grezzi; tutti i geni misurati sul supporto comune del confronto, esclusi tutti
  i 218 bersagli dell'archivio. Non si limita ai geni dell'asse ufficiale.
- **CD4:** asse ufficiale, esclusi tutti i 300 bersagli; 282 bersagli presenti in
  tutte le cinque cache; per ciascun bersaglio intersezione dei geni finiti nelle
  cinque sorgenti. Mediana: 9.720 geni. Analisi della restrizione anche sul
  supporto delle sole due metà, esplicitamente separata.

La selezione dei casi STAT2 e MCF7/TNF è a posteriori. Non ci sono nuovi test di
significatività, intervalli di confidenza o correzioni per confronti multipli.
Sei confronti con una linea esclusa condividono sorgenti: non sono sei repliche
indipendenti. Dipendenze dei filtri e delle stime Mixscale restano quelle aperte
in [ricerca sorgenti](../ricerca_sorgenti_2026-09-25/RISULTATI.md).

## 2. STAT2: il contrasto fra stimoli persiste sullo stesso supporto

**Misurato.** Per STAT2, gli stessi 3.688 geni sono finiti in tutte le sei linee
in entrambi gli stimoli. Ogni linea è prevista dalla media delle altre cinque.
Fonte: [matched_stimuli.csv](r1/matched_stimuli.csv).

| Linea | Pearson IFNB | Pearson IFNG | log2FC di STAT2, IFNB | log2FC di STAT2, IFNG |
|---|---:|---:|---:|---:|
| A549 | 0,528 | 0,052 | −1,650 | −1,300 |
| BXPC3 | 0,710 | −0,001 | −2,926 | −2,163 |
| HAP1 | 0,600 | −0,010 | −2,558 | −2,132 |
| HT29 | 0,648 | −0,016 | −2,083 | −2,076 |
| K562 | 0,540 | −0,035 | −1,910 | −2,113 |
| MCF7 | 0,602 | −0,030 | −1,728 | −1,081 |

**Interpretazione:** supporto diverso e assenza di riduzione dell'RNA bersaglio
non bastano a spiegare il contrasto. HT29 è il controllo più netto per la seconda
alternativa. Uguale riduzione dell'RNA non garantisce uguale attività proteica,
tempo o distribuzione dell'efficacia. Pearson circa zero non significa effetto
nullo; non identifica soglie, bistabilità o uno switch universale.

**Misurato nelle metriche precedenti:** sui 18 bersagli comuni a IFNB/IFNG,
la differenza media del vantaggio rispetto al controllo che ignora il bersaglio
è +0,01237; escludendo STAT2 diventa −0,01383. STAT1 e JAK1 favoriscono IFNG,
STAT2 e IRF9 IFNB in tutte le sei linee. Fonte:
[stimulus_crossover.csv](r1/stimulus_crossover.csv).
Non segue una graduatoria universale degli stimoli.

## 3. Programmi con segno: candidati, non generalizzazione dimostrata

**Misurato.** Correlazione delle risposte dentro ogni linea sotto IFNB;
supporto comune alle due perturbazioni e alle sei linee, bersagli esclusi.
Fonte: [signed_geometry.csv](r1/signed_geometry.csv).

| Risposta confrontata con STAT2 | Pearson mediana fra sei linee |
|---|---:|
| IFNAR1 | +0,777 |
| IFNAR2 | +0,827 |
| TYK2 | +0,796 |
| STAT1 | +0,570 |
| JAK1 | +0,622 |
| USP18 | −0,484 |

USP18 è anticorrelato in tutte le linee. **Interpretazione biologica:** compatibile
con il ruolo negativo sul programma IFN identificato nello
[studio Mixscale](https://pmc.ncbi.nlm.nih.gov/articles/PMC12083445/).
La vicinanza in una via non equivale a stesso segno dell'effetto.

**Limite:** sono regolatori canonici scelti dopo l'osservazione; un solo asse IFN
può spiegare gran parte della geometria. Predire altri bersagli nascosti deve
battere una risposta comune con ampiezza specifica, senza costruire il programma
dalle risposte di test. Sottrarre lo stesso background stimato a due profili può
introdurre covarianza artificiale: non si usa tale residualizzazione come prova
indipendente. Anche controlli condivisi possono correlare le stime.

## 4. MCF7 e TNF: fallimento concentrato su tre interventi

**Misurato sui confronti precedenti.** Definendo Δr = Pearson specifica meno
Pearson del controllo che ignora il bersaglio:

| Bersaglio | Δr in MCF7 | Media nelle altre cinque linee | Divario |
|---|---:|---:|---:|
| FADD | −0,2132 | +0,0979 | −0,3112 |
| TRAF3 | −0,1213 | +0,1891 | −0,3104 |
| TRAF2 | −0,0955 | +0,0883 | −0,1838 |

Sui 55 bersagli TNFA il divario medio MCF7–altre linee è −0,01758; esclusi questi
tre è −0,00310. Solo 28/55 divari sono negativi. Fonte:
[tnfa_mcf7.csv](r1/tnfa_mcf7.csv). È una sensibilità a posteriori, non una regola
per togliere i casi difficili dalla valutazione.

**Verifica sulle matrici DE**, con il nuovo supporto del §1:
Pearson MCF7 = −0,186 FADD, −0,061 TRAF3, −0,035 TRAF2.
RNA del bersaglio in MCF7: log2FC −2,177, −0,411, −0,659 rispettivamente.
Fonte: [tnfa_raw.csv](r1/tnfa_raw.csv).

**Ipotesi:** interazione circoscritta fra intervento e stato, non scarsa qualità
generale di MCF7. Per TRAF3/TRAF2 l'efficacia resta un'alternativa evidente;
FADD è un candidato per distinguere programmi di risposta, efficacia delle guide
e selezione dei sopravvissuti. Una correlazione negativa non prova un'inversione
causale del programma. Servono guide, repliche e misure di composizione.

## 5. CD4: l'errore standard non certifica la riproducibilità fra donatori

**Misurato.** Le cache `cd4_halfA` e `cd4_halfB` sono Stim48hr diviso in due
gruppi disgiunti di donatori, come documenta
[stadio 98](../../scripts/98_multisource_effects.py); non metà tecniche dello stesso
donatore. Supporto comune alle cinque cache, definito nel §1.

| Confronto | Pearson mediana per bersaglio | Coppie bersaglio–gene con z assoluto ≥ 2 in entrambi | Segni opposti | Frazione aggregata |
|---|---:|---:|---:|---:|
| Rest–Stim8hr | 0,3027 | 144.386 | 20.873 | 14,46% |
| Rest–Stim48hr | 0,2587 | 137.471 | 26.028 | 18,93% |
| Stim8hr–Stim48hr | 0,3048 | 152.747 | 24.365 | 15,95% |
| halfA–halfB | 0,0844 | 96.688 | 33.775 | 34,93% |

Fonte: [cd4_per_target.csv](r1/cd4_per_target.csv) e riepilogo JSON.
z = effetto/SE della cache; non è una chiamata DE ufficiale né una soglia corretta
per test multipli. La percentuale è condizionata al filtro in entrambi i gruppi
e aggrega coppie; la Pearson dà uguale peso ai bersagli. Non sono lo stesso
estimando e non rappresentano un errore del 35% su tutto il trascrittoma.

**Interpretazione:** l'incertezza entro gruppo non basta a descrivere la
trasferibilità del segno. Possibili cause: minore numerosità, donatori, guide,
batch, stima dell'errore o effetti veri deboli. Rest/8h/48h condividono donatori,
halfA/halfB no: non possiamo concludere che il donatore conti più dello stato.
Lo stimatore attuale somma varianze entro donatore, senza un termine empirico
esplicito di eterogeneità fra donatori; vedi
[effects_from_pseudobulk](../../src/vcc2026/multisource.py).

**La restrizione aumenta l'accordo fra le due stime.** Sulle stesse
282 perturbazioni ma sui geni comuni alle sole due metà, la Pearson mediana
passa da 0,08732 grezza a 0,11173 ristretta; mediana delle differenze appaiate
+0,02610. Fonte: [cd4_shrink_pair_support.csv](r1/cd4_shrink_pair_support.csv).
La differenza rispetto a 0,0844 dipende dal supporto. Non è un risultato VCC.
Si restringono **entrambi** i gruppi: cambia anche il riferimento. Questo
guadagno non dimostra una migliore previsione contro una verità fissa. La frase
della precedente chat «la restrizione resta utile» va limitata a questo accordo
descrittivo; una prova predittiva richiede una valutazione indipendente.

**Proposta:** effetti per donatore/guida, confronti entro e fra donatori a uguale
numerosità e supporto, poi validazione del segno su donatori esclusi. Modellare
separatamente SE entro gruppo e variabilità fra donatori/studi; non chiamare
biologica tutta la discordanza e non scartare T19 per questa sola osservazione.

## 6. Riconciliazione con il nuovo banco MSE

Letti [MSE.md](../banco_varianti_2026-09-25/MSE.md),
[codice](../banco_varianti_2026-09-25/mse_tradeoff.py) e
[r10](../banco_varianti_2026-09-25/r10/measurements.json), aggiunti dal commit
`1380924` il 25 settembre alle 12:30 +02:00. Non sono stati modificati.

**Misurato nel banco altrui:** ampiezze ottime circa 0,02–0,16 e guadagno sul
nulla inferiore allo 0,11%; aumentare l'ampiezza grezza peggiora il proxy MSE.
Questo sostiene la separazione fra calibrazione dello score e ricostruzione
degli effetti. Non dimostra che la MSE ufficiale resti zero a ogni ampiezza.

Il proxy pesa effetti con i controlli medi A/B/C, usa sorgenti pubbliche escluse
per famiglia e non genera cellule. I bracci richiamano t16/t18/t19, ma non sono
le loro identiche predizioni di produzione. L'ampiezza ottima è scelta usando
la verità valutata: è una diagnostica oracolare, non una calibrazione imparata
su validation separata.

Per i vettori pesati P e T, l'ottimo è
`a* = <P,T>/<P,P> = cos(P,T) × ||T||/||P||`.
Non dipende dalla sola correlazione: ridurre la norma di P può alzare a* senza
aggiungere informazione. La lettura del rumore come semplice spinta verso 1
richiede ipotesi di errore; differenze sistematiche non garantiscono nemmeno
la conservazione dell'ordinamento.

La restrizione a 1,576 migliora il proxy rispetto al grezzo a 1,576 in tutte
le sorgenti. Rispetto al grezzo a 0,788 peggiora leggermente in tre sorgenti e
migliora CD4. Non è un vantaggio universale su t16. La frase sulla MSE ufficiale
è **non dimostrata**, non un risultato ufficiale smentito da un altro score.
La scheda R-018 nel registro conserva questa distinzione.

## 7. Che cosa cambia nella lettura dei precedenti

- **CP-0026 resta valido nel suo ambito.** Nel
  [verdetto](../conditioned_2026-09-18/verdict/verdict.json) la rete supera il
  lineare nel banco J di +0,06467, ma perde altri confronti, non usa utilmente
  quel descrittore di contesto e ha problemi di riproducibilità. Non dimostra
  l'inutilità delle reti o del contesto biologico; vantaggio di score e migliore
  correlazione degli effetti non sono sinonimi.
- **T19:** affidabilità nella sorgente e trasferibilità sono proprietà diverse.
  La misura CD4 invita a calibrare l'incertezza fuori donatore; non modifica
  ricetta o preregistrazione degli invii.
- **DLD-1:** la correlazione fra metà non è un limite superiore universale della
  previsione con tutti i dati; le metà hanno meno informazione. Nessuna nuova
  misura DLD-1 è stata eseguita qui.
- **Contesto scambiato:** è un controllo utile, ma un peggioramento da solo può
  dipendere da input fuori distribuzione. Serve predire contrasti reali dello
  stesso intervento fra contesti.

## 8. Consegna agli altri agenti

[PROPOSTE.md](PROPOSTE.md) specifica architetture, fonti e prove discriminanti.
Il pannello Mixscale ha 181/218 bersagli in un solo stimolo: numero di linee e
incroci bersaglio–stimolo sono due risorse diverse. Non addestrare un'interazione
libera e chiamarla identificata su questo disegno.

Restano aperti audit dei controlli/guide, validazione indipendente e protocollo
C/T/J. Nessuna nuova architettura adottata, nessun dataset acquisito, nessun
training o invio autorizzato da questo report. I risultati di questa cartella
sono evidenza esplorativa; le priorità aggiornabili restano nelle schede dei piani.
