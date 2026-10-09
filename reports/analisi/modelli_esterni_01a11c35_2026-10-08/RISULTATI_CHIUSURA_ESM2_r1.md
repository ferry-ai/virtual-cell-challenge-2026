# ESM2: chiusura C/J e componente di produzione

9 ottobre 2026. Misurato con il banco congelato di VALIDAZIONE, eseguito da
MODELLI-ESTERNI nel job privato
`davideferrante11/vcc-validazione-logo-01a11c35-esm2closure-r1`.
Nessun nuovo ridge, nessuna selezione sul test, nessun invio VCC.
Il giudizio comparativo indipendente finale resta di VALIDAZIONE.

**Verdetto: non adottare questa versione target-only come sostituto di T0 o
come miglioramento dimostrato.** Il componente funziona; il beneficio richiesto
non emerge. Gli embedding rimangono input dell'esperimento AMMI già dichiarato.
Non si apre una nuova griglia per correggere questi risultati.

## Lettura intuitiva

ESM2 descrive le proteine dei geni colpiti. Il ridge cerca di associare quelle
descrizioni alle risposte osservate. Non riceve informazioni sul tipo di cellula
in cui dovrà prevedere la risposta: produce la stessa risposta del bersaglio
qualunque sia il contesto.

La prova più chiara riguarda iPSC. Quando il training comprendeva quel
lignaggio, pur nascondendo i bersagli di test, la discriminazione era 0,627.
Togliendo anche il lignaggio, scende a 0,524. La differenza è risolta nel
bootstrap; il vantaggio del nuovo risultato rispetto a predizioni scambiate
non lo è. Il risultato favorevole precedente non dimostrava quindi capacità
di trasferimento a un tipo cellulare nuovo.

Usare ESM2 per riempire soltanto i buchi di T0 cambia realmente le predizioni,
ma il vantaggio nella discriminazione è troppo piccolo per distinguerlo
dall'incertezza in entrambi i fold. Più copertura non equivale a più accuratezza.

## Misure congelate

`disc95` è una misura di discriminazione nello spazio degli effetti, non
accuratezza percentuale e non punteggio VCC. Intervalli da 10.000 bootstrap
appaiati sui bersagli, seme20261008, come nel banco originale.

| Prova primaria | Bersagli | Geni disc95 | T0 | ESM2 nativo | T0 + fallback ESM2 |
|---|---:|---:|---:|---:|---:|
| C-K562, k562 | 272 | 7.260 | 0,77211 | 0,53283 | 0,77243 |
| C-iPSC, kolf_pan_genome | 282 | 11.598 | 0,56367 | 0,52132 | 0,56384 |

Fallback meno T0: K562 +0,000312 [−0,000244; +0,000936]; iPSC +0,000177
[−0,000719; +0,001098]. Macro dei due fold +0,000244
[−0,000278; +0,000796]. Nessun miglioramento risolto della misura primaria.
La libreria secondaria kolf_strong dà +0,002020 [−0,000673; +0,004714], anch'esso
non risolto; non sostituisce la lettura primaria.

ESM2 nativo in C-K562 è inferiore a T0 di −0,23928
[−0,28442; −0,19253]. In C-iPSC il delta −0,04234
[−0,09212; +0,00854] non è risolto. ESM2 contro il proprio controllo permutato
ha un piccolo segnale su K562 (+0,03804 [0,00640; 0,06964]), mentre in iPSC
il +0,00660 [−0,01609; +0,02934] non è risolto. Non è corretto concludere che
ESM2 non contenga alcuna informazione; non basta però a battere il transfer.

In **J-iPSC**, 59 bersagli hanno verità primaria: ESM2 0,52425, generico0,50058,
T0 0,54822. ESM2−generico +0,02367 [−0,01520; +0,06108];
ESM2−permutato +0,02075 [−0,04033; +0,08212]. ESM2 J−ESM2 T
−0,10316 [−0,17301; −0,03594]. T0 copre15bersagli, ESM2 tutti59;
il banco J conserva anche le predizioni nulle e usa supporto derivato dalla
verità come prescritto. Il confronto non viene rinormalizzato sui soli15.

I dati sono lignaggi di sviluppo; non costituiscono conferma indipendente sui
contesti finali. Non sono stati eseguiti nuovi confronti a sei membri: non si
promuove una versione che non migliora la misura primaria congelata.
Il risultato J-K562 precedente resta nella consegna dei sei fit e non viene
ricalcolato per cercare un esito diverso.

## Consegna tecnica

`completed_fits_handoff_r1.json` conserva i sei checkpoint e le predizioni
native. `esm2_closure_conversion_r1.json` registra la conversione sul pannello
e sull'asse ufficiale. Il fallback rispetta ogni coppia bersaglio-gene già
osservata da T0; riempie soltanto quelle mancanti con ESM2 ×1,576, senza
riapplicare cis o scala del generatore. Cambia428.137coppie in C-K562,
484.195in C-iPSC e390.819nella produzione.

`esm2_production_delivery_r1.json` punta all'export di produzione fuoriGit,
al checkpoint e al contratto `esm2_production_inference_r1.json`.
La verifica di ricaricamento su8bersagli ×8geni riproduce esattamente valori
e maschere salvati, incluso il bersaglio senza feature. È un test d'interfaccia
piccolo, non un nuovo fit o una valutazione locale completa.

Inferenza completa sul runtime cloud, dopo aver materializzato i pin del
contratto nei percorsi del runtime:

```text
python esm2_inference_v1.py --spec esm2_production_inference_r1.json --out E2.npz
```

`E2.npz` è un effetto nativo non scalato. Il ponte
`esm2_closure_adapter_v1.fallback` produce il file consumabile dallo stadio100;
il generatore resta invariato. Questa consegna resta sperimentale, senza
autorizzazione implicita a sostituire t36 o a inviare una nuova submission.

## Evidenze e precedenti

`esm2_closure_retrieval_r1.json` elenca hash e percorsi dei risultati completi,
parità, consumo e statistiche per bersaglio. `esm2_closure_verified_r1.json`
registra il controllo di codice remoto, release, manifest, predizioni consumate
ed esclusioni; metriche e driver restano copie invariate di VALIDAZIONE.

S-013: la perdita del segnale iPSC dopo esclusione del lignaggio è misurata;
l'attribuzione alla composizione del training resta un'interpretazione e non
si deduce dal solo conteggio dei contesti. S-009: conversione e ampiezza unica
verificate. Il fallback non è un no-op, ma non mostra il beneficio primario.
Richiesta a VALIDAZIONE: registrare questo esito senza promuovere il componente.
