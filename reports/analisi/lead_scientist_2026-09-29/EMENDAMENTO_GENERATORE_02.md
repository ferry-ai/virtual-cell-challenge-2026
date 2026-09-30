# Emendamento prospettico: un solo confronto con 14 bracci

29 settembre 2026. Scritto dopo l'analisi dei soli controlli A/B/C e prima di qualunque
score reale dei candidati di questa sessione. I test dello script hanno usato soltanto
cellule sintetiche. Responsabile operativo: Codex, sessione principale e sottoagente
`audit_scientifico`.

## Che cosa cambia e perché

`PROTOCOLLO_GENERATORE.md` prevedeva 12 bracci ampiezza × dispersione.
`generatore/PROTOCOLLO_BANCO_BINS.md` proponeva altri quattro confronti, due dei quali
duplicavano il generatore pooled già presente. Le misure sui controlli hanno motivato
il generatore condizionato sulla profondità; non hanno misurato uno score perturbativo.
Si consolida quindi il disegno **prima** degli score: ai 12 bracci originali si aggiungono
soltanto `bins_a1` e `bins_a2`, entrambi con dispersione residua zero.

I controlli pooled ad ampiezza 1 e 2 sono quelli già nella griglia: non si generano copie
con semi diversi e non si contano come repliche. I nomi CLI sono `1:0`, `2:0`, `bins:1`
e `bins:2`. In totale sono **14 bracci**, inclusa una sola istanza del riferimento `1:0`.

Il generatore bins è `DepthCandidate`: sceglie 8 quantili uniformi oppure la griglia
di coda già fissata usando esclusivamente l'errore dei CPM medi per cellula attesi sui
controlli. Smoothing 1%, stesso profilo pooled target, nessun aggiustamento delle somme
realizzate, nessuna dispersione residua aggiunta. Si registrano scelta, errori sui
controlli e convergenza. Non si aggiungono griglie o iperparametri dopo aver visto gli score.

## Selezione e conferma congiunte

Restano: 48 bersagli di sviluppo, 96 disgiunti di conferma, selezione seed 20260929,
2.000 controlli, 400 cellule previste, tutta la verità HepG2 disponibile secondo
`EMENDAMENTO_GENERATORE_01.md`, seme generativo 1 in sviluppo e 1/2/3 in conferma.

La graduatoria è unica sui **13 cambi rispetto al riferimento**. Usa la proiezione
dei cinque membri con pendenze ufficiali divisa per sei, MSE posta a zero, dichiarata
come proiezione locale. I sei grezzi sono sempre conservati. Passano al massimo **due
finalisti complessivi**, non due per famiglia.

Vale il criterio di spareggio già fissato per differenze inferiori a 0,002: prima la
modifica minore dell'ampiezza, poi la dispersione minore. I bins hanno dispersione residua
zero; a parità anche di questi due valori precede pooled, per rendere deterministico
il confronto fra due famiglie che il protocollo originale non distingueva.

Conferma: almeno +0,005 di proiezione, vantaggio in tutti e tre i semi, intervallo bootstrap
appaiato per bersaglio sopra zero. Con due finalisti si usano intervalli bilaterali al
97,5% per ciascuno (Bonferroni su due confronti), con uno al 95%; 2.000 ricampionamenti
condivisi fra semi e membri. La variabilità fra semi resta riportata separatamente.

I confronti bins meno pooled alla stessa ampiezza e quelli che separano ampiezza da
dispersione sono diagnostici. Non selezionano ulteriori finalisti e non costituiscono
un secondo test indipendente. Se manca l'ampiezza di controllo nella conferma, il suo
contrasto resta quello dello sviluppo e viene indicato come tale.

Questo emendamento **sostituisce** la selezione separata proposta in
`generatore/PROTOCOLLO_BANCO_BINS.md` e amplia da 12 a 14 la griglia di
`PROTOCOLLO_GENERATORE.md`. I documenti precedenti restano immutati. Non modifica la
suddivisione dei bersagli né la regola di promozione, eccetto la gestione congiunta
dei finalisti e lo spareggio finale fra famiglie.

## Esecuzione riproducibile

Il manifest si scrive prima dello scoring e include gli hash di tutti i protocolli
applicabili, dello script, dei due moduli bins, degli effetti e dei dati. La preparazione
può avvenire sul portatile o sul runner remoto; il run può rilocare i dati con
`--data-root`, mantenendo i file identificati dagli hash. Cambiare macchina non cambia
target, controlli, maschere o semi. Il walltime non è noto senza una misura sul runner.
