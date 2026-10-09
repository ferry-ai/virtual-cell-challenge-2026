# CP-0072 — ESM2 + ridge nel regime T: un segnale specifico del bersaglio solo sul lignaggio iPSC

- **Data:** 2026-10-09
- **Tipo:** esperimento
- **Redatto da:** Claude Code (Opus 5.5), sessione 8a8ca58a
- **Revisione umana:** no
- **Stato:** immutabile
- **Strade:** S-013

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Il ridge sugli embedding ESM2 del bersaglio, addestrato da MODELLI-ESTERNI senza alcun ingresso di contesto,
predice la risposta di bersagli mai visti (regime T) meglio della sua sola parte generica e di ciò che il transfer
sa fare lì?

## 2. Cosa è stato fatto

Tutto in [validazione_indipendente_8a8ca58a_2026-10-08](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/README.md); orari letti con `date`, dai commit
o dai `launch.json`, Europe/Rome.

1. **Lettura del file nativo** del fit T (`davideferrante11/esm2-t-01a11c35-r3`, terminato alle 01:56 del 9/10),
   senza modificarlo: sha256 `06935074…93fd`, uguale alla ricevuta del suo proprietario.
2. **Correttezza tecnica**, prima di leggere qualunque verità ([esame](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco/esm2_t_r2/esame.json)).
3. **Piano prima dei numeri:** [LETTURA_ESM2_T.md](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/LETTURA_ESM2_T.md), commit `234ba7d3` delle 02:12:43.
4. **Conversione dichiarata** nel formato dello stadio 100: bracci `E2` (nativo), `E2g` (sola parte generica),
   `E2c` (ampiezza 1,576 e testa cis del transfer) ([conversione](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco/esm2_t_r2/conversione.json)).
5. **Corsa r6 del livello A** (02:16–02:30): i 66 bersagli nascosti del pannello contro la verità di sei lignaggi,
   bootstrap appaiato sui bersagli, controllo a previsioni scambiate fra i 66 bersagli.

## 3. Cosa si è osservato

- **Il file è ciò che dichiara:** asse ufficiale, 66 bersagli = gruppo nascosto del manifest, 47 contesti, valori
  finiti, stessa previsione per lo stesso bersaglio in ogni contesto a meno di 2,2e-16; la parte specifica vale in
  mediana il 69 % della norma di una previsione.
- **Livelli di `disc95`** ([tabella](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/TABELLE_ESM2_T_livelli_r6.md)): contro la verità iPSC il ridge vale
  0,627 (parte generica 0,501, ridge a previsioni scambiate 0,541, testa cis 0,548); contro CD4T, HCT116, HEK293 e
  K562 vale 0,507–0,525 (scambiato 0,490–0,506, testa cis 0,543–0,575).
- **Contrasti** ([tabella](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/TABELLE_ESM2_T_contrasti_r6.md)): `E2 − E2g`, macro `disc95` +0,031 [+0,004;
  +0,059], risolto; per lignaggio risolto solo su iPSC, +0,126 [+0,064; +0,193]. Controllo a previsioni scambiate:
  macro +0,043 [−0,009; +0,109], **non risolto**; risolto solo su iPSC, +0,086 [+0,013; +0,161]. `E2 − T0`: macro
  −0,032 [−0,084; +0,024]; iPSC +0,079 [+0,004; +0,151].
- **Scala:** l'ampiezza che adatterebbe meglio il ridge alla verità è 0,80 su CD4T e 0,58 su iPSC, e fra −0,03 e
  +0,04 su HCT116, HEK293 e K562.
- **Esito della regola scritta prima:** servivano insieme la macro risolta di `E2 − E2g` e il controllo risolto;
  il secondo manca. Non si afferma che il ridge abbia imparato qualcosa del bersaglio in generale.

## 4. Interpretazione e incertezza

- **Misura:** un segnale specifico del bersaglio è riconoscibile contro una sola verità, quella iPSC; sui quattro
  lignaggi non staminali niente è risolto e il ridge resta sotto la testa cis.
- **Interpretazione:** un modello senza contesto dà una sola risposta per bersaglio, e quella risposta somiglia al
  lignaggio che pesa di più nel training (24 contesti iPSC su 47); la parte generica somiglia a CD4T, che ha il
  63 % delle righe. **Ipotesi**, non isolata da un contrasto.
- **Perché potrebbe non essere così.** Sessantasei bersagli e una sola partizione; sei verità di lignaggi che il
  modello ha visto con altri bersagli; il livello A è un proxy. La differenza fra iPSC e gli altri potrebbe venire
  anche dalla qualità della verità di ciascun lignaggio, non solo dal peso nel training.
- **Che cosa non dice:** nulla sui contesti nuovi. Il regime T da solo non lo può dire.

## 5. Spiegazione semplice

Si è insegnato a un modello a indovinare che cosa succede quando si spegne un gene guardando solo la forma della
sua proteina, senza dirgli in quale cellula. Messo alla prova su geni mai visti, ci riesce un poco quando la
risposta vera è quella di una staminale, e non ci riesce nelle altre cellule: ha imparato come rispondono le
staminali, che nei dati sono le più rappresentate, e dà quella risposta a tutti.

## 6. Conseguenze

- Nessuna promozione e nessun effetto sulla consegna: è un regime T.
- Per il ramo contestuale indicato dal Lead è un argomento a favore di far entrare il contesto, e una regola di
  lettura: ogni rete si legge **per lignaggio**, non solo in macro.
- Prossima lettura: i fit a lignaggio escluso di K562 e iPSC, con il §8 del contratto e il banco a sei membri. Va
  scritto prima come il ridge si combina con il transfer quando entrambi predicono.
- Nuova strada S-013.

## 7. Cosa corregge

Nessun checkpoint.

## 8. Domanda di comprensione

Perché una macro risolta su sei lignaggi non basta a dire che il modello ha imparato qualcosa del bersaglio?
