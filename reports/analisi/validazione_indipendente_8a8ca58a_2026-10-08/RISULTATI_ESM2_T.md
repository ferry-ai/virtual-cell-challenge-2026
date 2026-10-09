# Risultati: ESM2 + ridge nel regime T

9 ottobre 2026, VALIDAZIONE (Claude Code `8a8ca58a`). [Piano scritto prima](LETTURA_ESM2_T.md): commit `234ba7d3`
delle 02:12:43; corsa r6 del livello A (`davideferrante11/vcc-validazione-logo-8a8ca58a-r6`) lanciata alle
02:16:34 e conclusa alle 02:30, 754 secondi; parità di produzione di T0, R1 e T1 e codice salvato uguale al
pacchetto ([verifica](banco/r6/completion/verification.json)).

**Che cosa sono questi numeri.** Proxy nello spazio degli effetti, su 66 bersagli nascosti e sei lignaggi di
sviluppo. **Regime T:** il modello non ha mai visto questi bersagli, ma ha visto gli altri bersagli di ogni
lignaggio. Non sono punteggi VCC e non dicono nulla sui contesti nuovi. Il modello è di MODELLI-ESTERNI; il file
nativo è letto senza modifiche, la conversione nel formato del banco è mia e dichiarata.

Tabelle scritte dai lettori: [livelli](TABELLE_ESM2_T_livelli_r6.md), [contrasti](TABELLE_ESM2_T_contrasti_r6.md).

## 1. Correttezza tecnica

Superata prima di leggere qualunque verità: stesso sha256 della ricevuta, asse ufficiale, i 66 bersagli nascosti
del manifest, valori finiti, stessa previsione per lo stesso bersaglio in tutti i 47 contesti a meno di 2,2e-16
([esame](banco/esm2_t_r2/esame.json); dettaglio nel piano).

## 2. Livelli di `disc95` per lignaggio (0,5 = nessuna capacità di riconoscere il bersaglio)

| Verità | Bersagli | Transfer: sola testa cis | Parte generica (`E2g`) | Ridge (`E2`) | Ridge a previsioni scambiate | Ridge con ampiezza e cis (`E2c`) | `r_spec` del ridge |
|---|---:|---:|---:|---:|---:|---:|---:|
| CD4T | 64 | 0,562 | 0,503 | 0,525 | 0,490 | 0,531 | +0,001 |
| HCT116 | 66 | 0,575 | 0,504 | 0,515 | 0,499 | 0,519 | +0,000 |
| HEK293 | 66 | 0,574 | 0,500 | 0,507 | 0,503 | 0,510 | +0,003 |
| K562 | 62 | 0,543 | 0,500 | 0,521 | 0,506 | 0,535 | −0,002 |
| **iPSC** | 59 | 0,548 | 0,501 | **0,627** | 0,541 | 0,629 | **+0,053** |
| H1 | 6 | 0,583 | 0,500 | 0,500 | 0,400 | 0,500 | +0,025 |

La testa cis predice un solo gene vicino per 15–20 bersagli su una sessantina e nulla per gli altri: il suo
livello è alto dove predice e dice poco altrove.

## 3. Contrasti (bootstrap appaiato sui bersagli, intervallo al 95 %; in grassetto se esclude zero)

| Contrasto, `disc95` | Macro su sei verità | iPSC | Gli altri cinque |
|---|---|---|---|
| `E2 − E2g`: la sequenza oltre la parte generica | **+0,031** [+0,004; +0,059] | **+0,126** [+0,064; +0,193] | da +0,000 a +0,022, nessuno risolto |
| `E2` contro `E2` a previsioni scambiate | +0,043 [−0,009; +0,109] | **+0,086** [+0,013; +0,161] | da +0,005 a +0,100, nessuno risolto |
| `E2 − T0`: contro la sola testa cis | −0,032 [−0,084; +0,024] | **+0,079** [+0,004; +0,151] | da −0,022 a −0,083, nessuno risolto |
| `E2c − T0` | −0,027 [−0,079; +0,028] | **+0,080** [+0,006; +0,152] | da −0,008 a −0,083, nessuno risolto |
| `E2c − E2`: ampiezza e testa cis sopra il ridge | **+0,005** [+0,002; +0,008] | +0,001 | risolto e piccolo su CD4T, HCT116, HEK293, K562 |

Altre misure di `E2 − E2g`, in macro: `sign50` −0,002 [−0,029; +0,022]; `nmae_conf` **−0,005** (meglio);
errore quadratico **+0,011** (peggio). Il controllo a previsioni scambiate è risolto in macro su `r_spec`
(**+0,019** [+0,009; +0,030]) e su `sign50` (**+0,040**), per effetto di iPSC (+0,044 e +0,114) e, su `r_spec`, di H1
(+0,068, con sei bersagli).

**Il ponte di scala, misurato.** L'ampiezza che adatterebbe meglio `E2` alla verità vale 0,80 su CD4T e 0,58 su
iPSC, ma 0,04 su HCT116, −0,02 su HEK293 e −0,03 su K562: lì la previsione non è allineata alla verità, non è
solo fuori scala. La parte generica da sola ha ampiezza ottima 1,13 su CD4T e fra −0,12 e +0,08 su HCT116, HEK293
e K562.

## 4. Lettura con la regola scritta prima

La regola chiedeva **due** cose per dire che il ridge ha imparato qualcosa del bersaglio: macro di `disc95`
positiva e risolta per `E2 − E2g`, e controllo a previsioni scambiate risolto. La prima c'è; la seconda, su
`disc95`, no. **Quindi non lo affermo in generale.**

**Misurato.** Un segnale specifico del bersaglio si riconosce contro **una** verità, quella del lignaggio iPSC,
dove tutti i contrasti sono risolti e il ridge supera anche la testa cis. Sui quattro lignaggi non staminali
(CD4T, HCT116, HEK293, K562) niente è risolto: il ridge sta a 0,51–0,53, contro 0,49–0,51 dello stesso ridge con
le previsioni scambiate, e sotto la testa cis.

**Interpretazione (ipotesi, non isolata).** Un modello senza ingresso di contesto dà a ogni bersaglio una sola
risposta, e quella risposta somiglia al lignaggio che pesa di più nel training: 24 dei 47 contesti della vista
sono iPSC, mentre la parte generica somiglia a CD4T, che ha il 63 % delle righe. È lo stesso disegno visto oggi
nel transfer: fonti staminali numerose spostano la previsione verso le staminali
([livello A](RISULTATI_LIVELLO_A.md), §5).

**Che cosa non dice.** Nulla sul regime che conta per D, E, F (bersagli visti altrove, contesto nuovo): per
quello servono i fit a lignaggio escluso, in corsa per K562 e iPSC. Sessantasei bersagli, una sola partizione di
bersagli nascosti, lignaggi di sviluppo. Che il segnale su iPSC venga dal peso dei contesti è un'ipotesi: la
verifica è un fit con massa uguale per lignaggio, o la lettura di J-iPSC, dove iPSC esce dal training.

**Conseguenze.** (1) Per il ramo contestuale deciso dal Lead questa è un'indicazione a favore di far entrare il
contesto: senza, la specificità che si impara è quella di un lignaggio. (2) Ogni prossima lettura di una rete va
fatta **per lignaggio**, non solo in macro: qui la macro di `E2 − E2g` è risolta e la sostiene un lignaggio solo.
(3) Nessuna promozione e nessuna decisione sulla consegna seguono da un regime T.

## 5. Il fit senza K562: regime J su K562 (corsa r7, letta alle 02:55)

[Aggiunta al piano](LETTURA_ESM2_T.md) committata alle 02:39:20 (`f8990eeb`), prima della corsa; kernel
`davideferrante11/vcc-validazione-logo-8a8ca58a-r7`, lanciato alle 02:43 e concluso alle 02:54, 639 secondi; parità
e codice salvato verificati. [Livelli](TABELLE_ESM2_JK562_livelli_r7.md),
[contrasti](TABELLE_ESM2_JK562_contrasti_r7.md).

| Verità K562, 62 bersagli nascosti | `disc95` |
|---|---:|
| Transfer: sola testa cis | 0,543 |
| Parte generica del fit senza K562 | 0,500 |
| Ridge del fit senza K562 (`E2jk`) | 0,516 |
| Lo stesso a previsioni scambiate | 0,531 |
| Ridge del fit T (`E2`), per confronto | 0,521 |

| Contrasto sul fold K562, `disc95` | Valore |
|---|---|
| `E2jk − E2jkg` | +0,016 [−0,046; +0,080] |
| `E2jk` contro `E2jk` a previsioni scambiate | −0,015 [−0,087; +0,062] |
| `E2jk − T0` | −0,027 [−0,118; +0,060] |
| `E2jk − E2`: togliere K562 dal training | −0,005 [−0,029; +0,020] |

**Misurato.** Nel regime J, sul solo lignaggio che questo fit tiene fuori, il ridge non riconosce i bersagli:
nessun contrasto è risolto e il braccio a previsioni scambiate vale più di quello vero. Sulle altre cinque verità i
numeri sono quelli del fit T (iPSC 0,628; CD4T 0,530; HCT116 0,514; HEK293 0,505), e `E2jk − E2` non è risolto
in nessun lignaggio.

**Lettura con la regola scritta prima.** Le due condizioni non sono soddisfatte sul fold K562: nessun segnale
specifico. È l'esito che l'aggiunta al piano prevedeva dopo aver visto, senza verità, che le previsioni dei due
fit sono quasi le stesse (correlazione 0,996).

**Interpretazione.** Togliere K562 non cambia nulla perché K562 pesa poco in questo modello, non perché il modello
generalizzi: il test che manca è il simmetrico, cioè il fit senza iPSC letto contro la verità iPSC. Se il 0,63 di
iPSC scendesse verso 0,5, la specificità vista nel regime T sarebbe memoria del lignaggio; se restasse, sarebbe
una proprietà dei bersagli. Quel fit (J-iPSC) non è ancora riuscito a partire.
