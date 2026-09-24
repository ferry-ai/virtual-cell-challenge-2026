# Pattern nel trasferimento Mixscale

24 settembre 2026. **Misurato, esplorativo:** rianalisi dei 1.626 confronti già
calcolati in `reports/dld1_audit_2026-09-24/mixscale_r1/per_target_context.csv`.
218 bersagli, sei linee, cinque stimoli. Nessun training o punteggio VCC.

## 1. La media nasconde un gruppo con forte trasferimento

Per ogni coppia bersaglio–stimolo, media sulle sei linee tenute fuori a turno.
Il controllo usa altri bersagli delle sole linee sorgenti, nello stesso stimolo.
Δr è la differenza appaiata fra Pearson della previsione specifica e del controllo.

| Bersaglio | Stimolo | Pearson media | Δr medio | Linee con Δr positivo |
|---|---|---:|---:|---:|
| STAT2 | IFNB | 0,699 | +0,438 | 6/6 |
| TYK2 | IFNB | 0,662 | +0,402 | 6/6 |
| IFNAR2 | IFNB | 0,639 | +0,378 | 6/6 |
| USP18 | IFNB | 0,639 | +0,882 | 6/6 |
| IFNAR1 | IFNB | 0,615 | +0,344 | 6/6 |
| IFNGR2 | IFNG | 0,599 | +0,435 | 6/6 |
| IFNGR1 | IFNG | 0,540 | +0,392 | 6/6 |

La Pearson mediana dell'intero insieme è appena 0,027. Per USP18 il Δr supera
la correlazione specifica perché il controllo è anticorrelato in media.
Le prime dieci coppie ordinate per Δr sono tutte IFNB/IFNG. In totale 63/271
coppie hanno Δr positivo in tutte le sei linee: non significa che abbiano tutte
un effetto grande. Le sei prove condividono sorgenti e non sono indipendenti.

**Interpretazione:** la trasferibilità è eterogenea per bersaglio e stimolo;
un'unica media globale descrive male i casi più informativi. I nomi sopra sono
selezionati dopo l'osservazione, non un pannello validato su un test separato.

## 2. Il vantaggio sui segni è concentrato

Prima si mediano le differenze per identità del bersaglio attraverso linee e
stimoli, poi si dà uguale peso ai 218 bersagli. Intervalli bootstrap al 95%:
5.000 ricampionamenti di bersagli, mantenendo fisse le sei linee.

| Misura specifica meno controllo | Tutti i bersagli | Esclusi i dieci con Δr medio maggiore |
|---|---:|---:|
| Pearson | +0,0412 [0,0294; 0,0548] | +0,0243 [0,0185; 0,0305] |
| Accordo di segno, punti percentuali | +1,69 [0,70; 2,77] | +0,52 [−0,13; 1,22] |
| Coseno | +0,0131 [−0,0021; 0,0284] | +0,0011 [−0,0122; 0,0150] |

Il confronto dei segni usa gli stessi 100 geni selezionati dalla previsione
specifica, come nell'analisi originale. La rimozione dei dieci bersagli è una
sensibilità a posteriori, non una regola di selezione né un nuovo test indipendente.
Resta segnale distribuito nella correlazione, ma il vantaggio direzionale fuori
dai casi più forti è piccolo e il suo intervallo comprende zero.

## 3. Molti segni corretti non significano specificità

Con INS la mediana dell'accordo dei segni è 79% per il trasferimento specifico,
contro 80% per il controllo che ignora il bersaglio. Il Δcoseno medio appaiato è
−0,0519 [−0,0784; −0,0210], pur con ΔPearson +0,0277. La componente comune va
quindi distinta dalla risposta specifica: le metriche rispondono a domande diverse.
Questo non prova che sottrarre la componente comune migliori una previsione VCC.

La graduatoria degli stimoli è sensibile anche alla composizione dei bersagli:
IFNB ha Δr medio +0,0589 e TNFA +0,0496 sui rispettivi pannelli; sui soli dieci
bersagli condivisi, il confronto appaiato IFNB meno TNFA è invece −0,0246
[−0,0368; −0,0129]. Geni di risposta e selezione DE possono differire fra stimoli:
il confronto non identifica un effetto causale dello stimolo.

## 4. Implicazione per il problema

**Proposta:** nel prossimo confronto fra modelli, verificare se descrittori del
bersaglio e dello stato cellulare riconoscono questi gruppi trasferibili,
tenendo i bersagli di test fuori da tutte le sorgenti. Separare la previsione
della componente comune dalla risposta specifica come ablazione da valutare.
Il risultato attuale trasferisce bersagli già osservati: non dimostra ancora
predizione di bersagli nuovi, né giustifica cambiare la ricetta di produzione.

**Limiti:** stime DE e selezione dei geni degli autori possono condividere
informazione fra linee; supporto genico variabile; confronti esplorativi multipli
senza correzione; bootstrap condizionato alle sei linee, non a nuovi studi.
Non sono stati riletti i conteggi grezzi: sono rianalizzate le misure salvate.

Riproduzione: `scripts/py.cmd reports/pattern_mixscale_2026-09-24/analyze.py --out <cartella-nuova>`.
Script: [analyze.py](analyze.py). Evidenza completa, hash dell'input e intervalli:
[misure](r1/measurements.json); [271 coppie bersaglio–stimolo](r1/target_stimulus.csv).
