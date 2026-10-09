# CP-0075 — Fallback ESM2: la misura primaria non vedeva il riempimento; dove il banco lo vede, più copertura e nessuna accuratezza specifica

- **Data:** 2026-10-09
- **Tipo:** esperimento
- **Redatto da:** Claude Code (sessione eace4d03, VALIDAZIONE)
- **Revisione umana:** no
- **Stato:** immutabile
- **Strade:** S-013, S-015

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

MODELLI-ESTERNI ha chiuso il ridge ESM2 senza contesto nel regime C e ha misurato che usarlo per riempire le
coppie bersaglio-gene che il transfer T0 non prevede sposta `disc95` di +0,000244 [−0,000278; +0,000796] in macro.
Quel numero dice qualcosa sul riempimento? Quante coppie riempite entrano nella misura, e sono migliori di zero, di
un riempimento generico e di uno a bersagli scambiati? Nessun nuovo training.

## 2. Cosa è stato fatto

[Contratto v3](../../reports/analisi/validazione_banco_eace4d03_2026-10-09/PROTOCOLLO_v3.md), §1–2, congelato alle
20:50 prima di ogni conteggio; [aggiunta](../../reports/analisi/validazione_banco_eace4d03_2026-10-09/ADDENDUM_v3_1.md)
delle 20:56, scritta dopo i numeri di C-K562 e prima di quelli di C-iPSC.
Codice: `reports/analisi/validazione_banco_eace4d03_2026-10-09/esm2/supporto_fallback.py`, con quattro prove su
fixture che includono la parità contro `bench_core.measure` del banco congelato.
File usati, ciascuno verificato per sha256 contro la ricevuta di chi lo ha prodotto: effetti dei fold dei bracci del
manifest, `E2`, `E2g` e fallback di MODELLI-ESTERNI (`esm2_closure_conversion_r1.json`), tabelle di verità della
release r1, `results.json` della corsa di chiusura.
Esecuzione: C-K562 sul portatile (32 s, file già locali); i due fold in un kernel CPU privato,
`davideferrante11/vcc-validazione-supporto-eace4d03-r1`, lanciato alle 21:02 e concluso in 45 s, con gli input già
montati. Il fold C-K562 del kernel coincide con quello locale a meno di 7e-18.

## 3. Cosa si è osservato

Misure nello spazio degli effetti su due lignaggi di sviluppo: non sono punteggi VCC.

**Controlli superati, su entrambi i fold:** `disc95` di T0 e del fallback ricalcolato coincide con quello
pubblicato (differenza 0); il fallback è T0 bit per bit dove T0 prevede e 1,576 × `E2` altrove (scarto massimo
2,4e-7); le coppie riempite sono quelle della ricevuta
([C-K562](../../reports/analisi/validazione_banco_eace4d03_2026-10-09/esm2/cloud_r1/completion/supporto_C-K562.json),
[C-iPSC](../../reports/analisi/validazione_banco_eace4d03_2026-10-09/esm2/cloud_r1/completion/supporto_C-iPSC.json)).

**Supporto.**

| | C-K562 | C-iPSC |
|---|---:|---:|
| Coppie riempite nei bersagli confrontati | 382.775 | 452.268 |
| Non giudicabili: la verità non misura il gene | 344.695 | 263.196 |
| Giudicabili | 38.076 | 189.003 |
| Di cui dentro il rango di `disc95` | 345 (0,9 %) | 6.647 (3,5 %) |
| Quota delle entrate del rango che sono riempite | 0,017 % | 0,20 % |
| Coppie riempite dentro il rango, mediana per bersaglio | 0 | 0 |

**Vista del generatore** (supporto definito dalla verità, coppia non prevista = zero), fallback meno T0:

| Misura | C-K562 | C-iPSC | Lo stesso riempimento a bersagli scambiati dà |
|---|---|---|---|
| `mse_ratio` (meno è meglio) | +0,0050 [+0,0044; +0,0057] | +0,0149 [+0,0139; +0,0160] | +0,0053 e +0,0155 |
| `nmae_conf` (meno è meglio) | +0,0008, non risolto | −0,0015 [−0,0024; −0,0007] | +0,0013 n.r. e −0,0014 |
| `sign50` | +0,0226 [+0,0182; +0,0272] | +0,0058 [+0,0013; +0,0103] | +0,0200 e +0,0055 |
| `disc95g` | +0,0002, non risolto | non leggibile: il suo controllo non passa | — |

`esm2` − `scambiato`: nessuna misura risolta su C-iPSC; su C-K562 solo `sign50`, +0,0026 [+0,00002; +0,0052].

**Solo le coppie riempite giudicabili.** Errore quadratico rispetto alla previsione zero: 1,24 (C-K562) e 1,11
(C-iPSC) per `esm2`, 1,25 e 1,11 a bersagli scambiati, 1,14 e 1,02 per il riempimento generico. Coseno con la
verità: +0,010 [−0,004; +0,024] su C-K562; **+0,0077 [+0,0025; +0,0131] su C-iPSC**, dove il generico dà +0,0073 e
la differenza `esm2` − `scambiato` è +0,0051 [−0,0012; +0,0116], non risolta. Il moltiplicatore che adatterebbe il
riempimento alla verità è 0,02–0,05.

**Segno separato dalla copertura.** I geni confidenti della verità coperti passano dal 91,1 % al 96,5 % (C-K562) e
dal 92,3 % al 98,7 % (C-iPSC). L'accordo di segno fra i previsti cambia di +0,001 (non risolto) e +0,002 [+0,0004;
+0,0033], uguale a bersagli scambiati.

**Sul supporto proprio di ciascun braccio**, come nel banco congelato, su C-iPSC lo stesso contrasto dava
`mse_ratio` −0,0071 e `nmae_conf` −0,0021, risolti a favore: nella vista del generatore il primo cambia segno.

**Dalla corsa di chiusura di MODELLI-ESTERNI**, non ricalcolato qui oltre la parità dei due bracci
(`C:/Users/ferra/vcc2026-data/external_models/01a11c35/esm2_closure_readout_r1/results.json`, sha256 `5ef9d48c…c8d4`):
ESM2 nativo contro T0 su C-K562 `disc95` −0,239 [−0,284; −0,193]; nel regime J su iPSC il ridge senza il lignaggio
vale 0,524 contro 0,627 del fit che lo conteneva, differenza −0,103 [−0,173; −0,036].

## 4. Interpretazione e incertezza

**Misura.** Sui due fold il rango di `disc95` conteneva meno del 4 % delle coppie riempite giudicabili: il delta
pubblicato del fallback è piccolo per costruzione e non descrive la qualità del riempimento.
**Per le parole fissate prima dei numeri:** non si scrive che il fallback riduce l'errore, né che il guadagno è
specifico del bersaglio, né che discrimina meglio. Su C-iPSC si scrive che il riempimento ha una direzione giusta
(coseno risolto sopra zero), non che è specifica del bersaglio.
**Interpretazione.** Il riempimento porta una risposta comune debole e copertura: `sign50` e l'errore assoluto
migliorano quanto con i bersagli scambiati, cioè per avere una previsione al posto di uno zero. L'errore quadratico
peggiora perché l'ampiezza 1,576 applicata al ridge è molto più grande di quella che la verità sosterrebbe.
**Che cosa non si può dire.** Se questa copertura in più aiuti o costi nei sei membri: il livello B per il fallback
non è stato eseguito, e l'esito del §8 resta **inconcludente**. Dal 58 % al 90 % delle coppie riempite cade su geni
che la verità del fold non misura: lì non c'è né un successo né un errore, c'è assenza di giudizio. Due lignaggi di
sviluppo, uno dei quali (iPSC) è quello su cui il ridge senza contesto aveva segnale quando lo vedeva.
**Lettura del sintomo di S-013.** Tolto il lignaggio iPSC dal training, il segnale del regime T scende di 0,10 e
non si distingue più dal braccio scambiato: è compatibile con memoria del lignaggio più rappresentato; il
meccanismo resta ipotizzato.

## 5. Spiegazione semplice

Il transfer lascia vuote alcune caselle; il ridge le riempie. La misura con cui si era giudicato il riempimento
guardava quasi solo le caselle che erano già piene: non poteva dire niente. Guardando le caselle riempite, il
ridge scrive più o meno la stessa cosa per ogni gene bersaglio, leggermente nella direzione giusta e con valori
troppo grandi: ha più risposte, non risposte migliori per quel bersaglio.

## 6. Conseguenze

- «Non adottare il fallback adesso» resta una decisione di priorità sensata; «il fallback non può aiutare» **non**
  è dimostrato: manca il giudizio a sei membri, e quattro bracci (zero, ESM2, generico, scambiato) lo renderebbero
  leggibile.
- Errore di metodo corretto nel banco: bracci con copertura diversa non si confrontano ciascuno sul proprio
  supporto. Riga nuova in ERRORI; dal contratto v3 ogni contrasto con maschere diverse riporta copertura e vista del
  generatore.
- Per AMMI e per ogni export futuro: la maschera `observed` resta «coppia prevista», la copertura si conta a parte.

## 7. Cosa corregge

Non corregge un checkpoint. Precisa la lettura di `RISULTATI_CHIUSURA_ESM2_r1.md` di MODELLI-ESTERNI, già corretta
dal suo autore nella `PRECISAZIONE_VERDETTO_ESM2_r1.md`: il delta di `disc95` del fallback non è evidenza né a
favore né contro, e i contrasti favorevoli su C-iPSC delle misure d'errore dipendevano dal supporto.

## 8. Domanda di comprensione

Perché `sign50` sale anche quando le caselle vuote si riempiono con la previsione di un altro bersaglio?
