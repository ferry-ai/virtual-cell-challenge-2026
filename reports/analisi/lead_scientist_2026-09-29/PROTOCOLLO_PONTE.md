# Ponte predittivo K562 3′ → Flex: protocollo prima della corsa

29 settembre 2026, Codex `audit_dati`. **Preparato, non eseguito sui dati.**
L'avvio del calcolo compete al lead della sessione. Nessun nuovo dato, rete, cloud o modello neurale.

## Domanda e novità

Una mappa diagonale, appresa su knockdown diversi da quelli valutati, rende gli effetti
Replogle K562 più predittivi degli effetti VIPerturb K562 misurati in una metà indipendente?
Questo è un ponte fra **studi, stimatori e piattaforme insieme**, non un effetto puro della chimica.

La ricerca del codice esistente ha trovato soltanto `ponte_flex_2026-09-28/bridge.py`, con
pendenze descrittive calcolate sui bersagli forti, e `split_half.py`, con coseni sugli stessi
bersagli selezionati. Nessuno dei due applica una mappa a bersagli tenuti fuori. Il nuovo test
non corregge quei risultati: risponde a una domanda predittiva che non avevano misurato.
La correzione CD4=Flex in `AUDIT_DATI.md` impedisce di attribuire a VIPerturb l'esclusiva del saggio.

## Split e input congelati

- Input X: effetti **shrunk** dell'universo Replogle K562 del 26/09, come nella produzione.
- Esiti Y_A/Y_B: effetti **raw** degli universi VIPerturb metà A e metà B del 28/09. Usare gli
  esiti non ristretti riduce il vantaggio artificiale di prevedere lo stesso shrinkage della verità.
- Tutti i 300 bersagli ufficiali sono esclusi da apprendimento, centrature, affidabilità e scelta.
- Tra i non-pannello con righe presenti in tutti e tre gli universi, permutazione deterministica
  con seme **20260929**, su elenco prima ordinato. Primi **1.200** training, successivi **400**
  validation, successivi **400** test. Gli altri restano riserva, non vengono letti per il modello.
  Un universo troppo piccolo causa errore, non una modifica silenziosa dello split.
  Il formato NPZ richiede di decomprimere chunk che possono contenere righe di altri split:
  il lettore restituisce soltanto le righe richieste, e le statistiche non usano le altre righe.
- Tutti i **123** bersagli del pannello con effetto VIPerturb completo sono inventariati per il
  test finale. Non si filtrano per significatività, energia, correlazione o disponibilità K562.
  Quando manca K562 la previsione esplicita è zero e il vantaggio della mappa è zero; quando
  manca una metà Flex la metrica di quella metà non è calcolabile, e la copertura è riportata.
  Non si deve chiamare «123 bersagli valutati» un insieme con meno verità disponibili.
- Mai usare il VIPerturb completo per fitting o verità: contiene entrambe le metà.

L'asse dei geni è quello ufficiale. La maschera di valutazione esclude tutti i geni del pannello
e, per ogni bersaglio, la finestra di 5 kb dal TSS, fissata dalle coordinate esterne. I geni
richiedono almeno 20 osservazioni congiunte nel training, varianza positiva e CPM basale VIPerturb
≥5. Non c'è filtro su z o p-value. Le maschere finite del singolo esito sono applicate ugualmente
a ogni braccio; una risposta non misurata non diventa zero.

## Mappa, affidabilità e controlli

Per gene, sul solo training, si stimano le medie di X, Y_A e Y_B e le covarianze con maschera
congiunta. Gli effetti del test sono centrati con queste medie, mai con la media del test.

Si costruiscono due direzioni: regressione X→Y_A valutata verso Y_B e regressione X→Y_B
valutata verso Y_A. La reliability è la correlazione positiva fra Y_A e Y_B sui **soli bersagli
di training**, limitata a [0,1]. Il fitting quindi usa entrambi i gruppi di misure del training,
ma nessun esito dei bersagli validation/test. L'indipendenza rilevante è quella delle cellule
e dei bersagli di valutazione; i controlli condivisi dentro lo studio restano una dipendenza.

Per ciascuna direzione la pendenza OLS per gene è limitata a [0,2]. Quattro bracci preregistrati:

`beta = q * beta_OLS + (1-q) * prior`, con `q = reliability * n/(n+k)`,
`prior ∈ {0,1}`, `k ∈ {50,200}`.

Controlli: identità (`beta=1`), scalare globale non negativo stimato nel training e zero.
Lo scalare usa gli stessi geni e pesi del modello. Uno scalare positivo lascia il coseno
invariato; serve soprattutto a evitare di attribuire alla mappa un miglioramento MSE dovuto
soltanto all'ampiezza. Non si cambiano segni per gene e non si aggiunge un'intercetta comune.

I pesi per gene sono `x/(1+x)`, `x=0,05 CPM`, dai controlli VIPerturb; la prima metrica è il
coseno per bersaglio fra effetti così pesati. È una proxy geometrica, **non PDS né score VCC**.
Si riportano inoltre energia, errore quadratico e rapporto aggregato sul predittore zero.

## Scelta e regola di lettura

1. Calcolare i quattro bracci soltanto sui 400 bersagli validation, in entrambe le direzioni.
   Scegliere il miglior incremento medio appaiato di coseno rispetto all'identità, mediando
   prima le due direzioni dello stesso bersaglio. Il pareggio entro 0,001 favorisce prior=1,
   poi k=200. Se nessun braccio migliora di almeno 0,005, si mantiene l'identità; l'esito è
   «nessun candidato scelto» e non si apre il test degli altri bracci per cercarne uno migliore.
   Il braccio deve anche avere coseno medio positivo ed energia prevista non nulla: una
   previsione zero non vince perché il riferimento aveva coseno negativo.
2. Solo il braccio scelto, identità, scalare e zero sono letti sui 400 non-pannello di test e
   sul pannello. Bootstrap appaiato sui bersagli, 2.000 repliche, seme 20260930; le due metà
   restano nello stesso blocco di bootstrap, non sono repliche indipendenti.
3. **Passa come mappa interna fra studi:** sul test non-pannello incremento medio del coseno
   ≥0,005, limite inferiore IC95 >0, ed incremento medio positivo in ciascuna direzione.
4. **Compatibilità col pannello:** incremento medio non negativo, riportando IC95 e copertura;
   una perdita sul pannello impedisce di promuovere direttamente il braccio per un invio.
5. Il miglioramento MSE da solo, una regressione che spegne quasi tutti i geni, o un risultato
   sul validation non promuovono la mappa. Anche un «passa» non prova trasferimento a una linea
   nuova e non sceglie una ricetta di submission senza verificarne geometria e generatore.

La mappa riguarda esclusivamente il componente Replogle K562: non si applica automaticamente
alle fonti Orion con altro protocollo, né al CD4 che è già Flex. Sui geni privi di supporto di
training i coefficienti restano il prior e non costituiscono una stima di trasferimento.

Un eventuale secondo test, **da preregistrare separatamente**, trasferirà la mappa congelata
da K562 verso CD4 Flex, con CD4 completamente escluso da apprendimento e scelta. Non va
chiamata verifica indipendente una mappa riadattata usando risposte CD4. Questo passaggio non
è necessario per decidere se il vecchio ponte descrittivo aveva chiuso prematuramente una possibilità.

## Codice, memoria e avvio

`ponte_predittivo.py` usa il lettore `Universe` esistente con una sola cache chunk per
sorgente, batch di 32 bersagli, statistiche sufficienti per gene e nessuna matrice universo
completa. I tre chunk cached hanno tipicamente circa 400 MiB; il codice controlla RSS e rifiuta
di proseguire oltre **700 MiB**. Non scrive grandi array di dati nella repository.
`--plan-only` legge soltanto gli indici e scrive split/provenienza; `--self-test` usa dati sintetici.
L'avvio normale scrive in una destinazione nuova e rifiuta di sovrascrivere:

```powershell
.\scripts\py.cmd reports/analisi/lead_scientist_2026-09-29/ponte_predittivo.py --self-test
.\scripts\py.cmd reports/analisi/lead_scientist_2026-09-29/ponte_predittivo.py --out reports/analisi/lead_scientist_2026-09-29/ponte_plan_r1 --plan-only
# Solo quando il lead dispone l'avvio:
.\scripts\py.cmd reports/analisi/lead_scientist_2026-09-29/ponte_predittivo.py --out reports/analisi/lead_scientist_2026-09-29/ponte_run_r1
```

Output: split e provenienza, coefficienti, lettura validation, braccio scelto, misure per
bersaglio, bootstrap appaiato e picco memoria. Nessun file di produzione viene cambiato.
